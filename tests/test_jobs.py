import sys
import textwrap
import time

import pytest

from app.jobs import BusyError, JobManager

FAKE = textwrap.dedent('''
    import json, os, sys, time
    out = sys.argv[sys.argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    for f in (1, 2):
        print(json.dumps({"event": "progress", "scene": 0, "scenes": 1, "frame": f, "total": 2}), flush=True)
    if os.environ.get("FAKE_SLEEP"):
        time.sleep(30)
    if os.environ.get("FAKE_FAIL"):
        print(json.dumps({"event": "error", "message": "bozuldu"}), flush=True)
        sys.exit(1)
    path = os.path.join(out, "01_dummy.mp4")
    open(path, "wb").write(b"x")
    print("düz log satırı", flush=True)
    print(json.dumps({"event": "output", "path": path}), flush=True)
    print(json.dumps({"event": "done"}), flush=True)
''')
PROJECT = {"name": "t", "scenes": [{"type": "dummy", "enabled": True, "params": {}}]}


@pytest.fixture
def manager(tmp_path):
    script = tmp_path / "fake_cli.py"
    script.write_text(FAKE, encoding="utf-8")
    return JobManager(str(tmp_path), command=[sys.executable, str(script)])


def test_job_done(manager, tmp_path):
    job = manager.start(PROJECT, str(tmp_path / "out" / "t" / "1"))
    assert job.finished.wait(15)
    assert job.state == "done"
    d = job.to_dict(str(tmp_path / "out"))
    assert d["outputs"] == ["t/1/01_dummy.mp4"] and d["dir"] == "t/1" and d["percent"] == 100
    assert "düz log satırı" in d["log"]


def test_job_failed(manager, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_FAIL", "1")
    job = manager.start(PROJECT, str(tmp_path / "o"))
    assert job.finished.wait(15)
    assert job.state == "failed" and job.error == "bozuldu"


def test_busy_and_cancel(manager, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_SLEEP", "1")
    out = tmp_path / "o"
    job = manager.start(PROJECT, str(out))
    with pytest.raises(BusyError):
        manager.start(PROJECT, str(tmp_path / "o2"))
    deadline = time.time() + 10
    while job.frame < 2 and time.time() < deadline:
        time.sleep(0.05)
    assert job.state == "running" and job.to_dict(str(tmp_path))["percent"] == 100
    manager.cancel(job.id)
    assert job.finished.wait(15)
    assert job.state == "canceled" and not out.exists()
