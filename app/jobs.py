"""Render işlerini ayrı süreçte (engine.cli) çalıştırır ve ilerlemeyi izler."""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid


class BusyError(RuntimeError):
    pass


class Job:
    def __init__(self, job_id, out_dir, scenes):
        self.id = job_id
        self.out_dir = out_dir
        self.state = "running"
        self.phase = "render"
        self.scene, self.scenes, self.frame, self.total = 0, scenes, 0, 0
        self.outputs = []
        self.error = None
        self.log = collections.deque(maxlen=20)
        self.proc = None
        self.finished = threading.Event()

    def percent(self):
        if self.state == "done":
            return 100
        if self.phase == "compose":
            return 99
        if not self.total:
            return 0
        return int(100 * (self.scene + self.frame / self.total) / max(self.scenes, 1))

    def to_dict(self, out_root):
        def rel(p):
            return os.path.relpath(p, out_root).replace(os.sep, "/")

        return {"id": self.id, "state": self.state, "phase": self.phase, "scene": self.scene, "scenes": self.scenes,
                "frame": self.frame, "total": self.total, "percent": self.percent(),
                "outputs": [rel(p) for p in self.outputs], "dir": rel(self.out_dir),
                "error": self.error, "log": list(self.log)}


class JobManager:
    def __init__(self, root, command=None):
        self.root = root
        self.command = command or [sys.executable, "-m", "engine.cli", "render"]
        self.jobs = {}
        self.lock = threading.Lock()

    def start(self, project, out_dir):
        with self.lock:
            if any(j.state == "running" for j in self.jobs.values()):
                raise BusyError("Zaten süren bir render var. Bitmesini bekleyin ya da iptal edin.")
            job = Job(uuid.uuid4().hex[:8], out_dir, sum(1 for s in project["scenes"] if s.get("enabled", True)))
            fd, tmp = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(project, f, ensure_ascii=False)
            job.proc = subprocess.Popen(
                [*self.command, tmp, "--out", out_dir, "--progress-json"], cwd=self.root,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONUTF8": "1"}, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.jobs[job.id] = job
            threading.Thread(target=self._watch, args=(job, tmp), daemon=True).start()
            return job

    def _watch(self, job, tmp):
        for line in job.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                job.log.append(line)
                continue
            kind = ev.get("event")
            if kind == "progress":
                job.phase = "render"
                job.scene, job.scenes, job.frame, job.total = ev["scene"], ev["scenes"], ev["frame"], ev["total"]
            elif kind == "compose":
                job.phase = "compose"
            elif kind == "output":
                job.outputs.append(ev["path"])
            elif kind == "error":
                job.error = ev["message"]
            elif kind == "log":
                job.log.append(ev["message"])
        rc = job.proc.wait()
        try:
            os.remove(tmp)
        except OSError:
            pass
        if job.state == "canceled":
            for _ in range(10):
                shutil.rmtree(job.out_dir, ignore_errors=True)
                if not os.path.exists(job.out_dir):
                    break
                time.sleep(0.3)
        elif rc == 0 and not job.error:
            job.state = "done"
        else:
            job.state = "failed"
            job.error = job.error or f"Render süreci {rc} koduyla bitti."
        job.finished.set()

    def get(self, job_id):
        return self.jobs.get(job_id)

    def cancel(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.state == "running":
            job.state = "canceled"
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(job.proc.pid)], capture_output=True)
            else:
                job.proc.kill()
        return job
