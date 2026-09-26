"""Arayüzsüz kullanım.
  python -m engine.cli render projects/ornek_florida.json [--out KLASOR] [--transparent|--opaque]
                                                         [--no-combined] [--no-separate] [--progress-json]
                                                         [--workers N]
  python -m engine.cli still projects/ornek_florida.json --scene 0 --t 8.6 --out kare.png [--dpi 100]
"""
import argparse
import datetime as dt
import json
import os
import sys

from engine import assets, compose, parallel, render
from engine import project as proj
from scenes import REGISTRY


def output_dir(project, out=None):
    return out or os.path.join(assets.ROOT, "out", project["name"], dt.datetime.now().strftime("%Y%m%d-%H%M%S"))


def run_render(project, out_dir, emit, workers=1):
    """Doğrulanmış projeyi render eder, üretilen dosyaların yollarını döndürür.
    workers: aynı anda render edilecek sahne sayısı; 0 otomatik (engine.parallel.auto_workers), 1 sırayla."""
    o = project["output"]
    ext = render.video_ext(o["transparent"])
    os.makedirs(out_dir, exist_ok=True)
    enabled = [s for s in project["scenes"] if s["enabled"]]
    paths = [os.path.join(out_dir, f"{i + 1:02d}_{s['type']}{ext}") for i, s in enumerate(enabled)]
    durations = [float(s["params"]["duration"]) for s in enabled]
    if workers == 0:
        workers = parallel.auto_workers(len(enabled))
    if workers > 1 and len(enabled) > 1:
        emit(event="log", message=f"{len(enabled)} sahne, aynı anda {min(workers, len(enabled))} süreçte render ediliyor")
        jobs = [(i, s["type"], s["params"], paths[i], int(round(durations[i] * render.FPS)))
                for i, s in enumerate(enabled)]
        parallel.render_scenes(jobs, o["transparent"], workers, emit)
    else:
        for i, s in enumerate(enabled):
            render.render_video(REGISTRY[s["type"]], s["params"], paths[i], o["transparent"],
                                on_progress=lambda f, n, i=i: emit(event="progress", scene=i, scenes=len(enabled),
                                                                    frame=f, total=n))
    outputs = []
    if o["combined"] and len(paths) > 1:
        emit(event="compose")
        combined = os.path.join(out_dir, "birlesik" + ext)
        compose.compose(paths, durations, combined, project["transition"], o["transparent"])
        outputs.append(combined)
    if o["separate"] or not outputs:
        outputs = paths + outputs
    else:
        for p in paths:
            os.remove(p)
    for p in outputs:
        emit(event="output", path=p)
    return outputs


def _describe(errors):
    return "Projede hatalı ayarlar var:\n" + "\n".join(
        f"- {'proje' if e['scene'] is None else str(e['scene'] + 1) + '. sahne'} / {e['param']}: {e['message']}"
        for e in errors)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="python -m engine.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="projeyi videoya dönüştürür")
    r.add_argument("project")
    r.add_argument("--out")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--transparent", action="store_true")
    g.add_argument("--opaque", action="store_true")
    r.add_argument("--no-combined", action="store_true")
    r.add_argument("--no-separate", action="store_true")
    r.add_argument("--progress-json", action="store_true")
    r.add_argument("--workers", type=int, default=0,
                   help="aynı anda render edilecek sahne sayısı (0: otomatik, işlemci sayısının yarısı; 1: sırayla)")
    s = sub.add_parser("still", help="tek kare PNG üretir")
    s.add_argument("project")
    s.add_argument("--scene", type=int, default=0)
    s.add_argument("--t", type=float, default=0.0)
    s.add_argument("--out", required=True)
    s.add_argument("--dpi", type=int, default=100)
    s.add_argument("--transparent", action="store_true")
    args = ap.parse_args(argv)
    as_json = getattr(args, "progress_json", False)

    def emit(**ev):
        if as_json:
            print(json.dumps(ev, ensure_ascii=False), flush=True)
        elif ev["event"] == "progress" and "overall" in ev:
            pct = int(ev["overall"] * 100)
            if pct != getattr(emit, "last_pct", -1):
                emit.last_pct = pct
                print(f"%{pct} · {ev['finished']}/{ev['scenes']} sahne bitti", flush=True)
        elif ev["event"] == "progress" and (ev["frame"] % 60 == 0 or ev["frame"] == ev["total"]):
            print(f"sahne {ev['scene'] + 1}/{ev['scenes']}: kare {ev['frame']}/{ev['total']}", flush=True)
        elif ev["event"] == "compose":
            print("sahneler birleştiriliyor...", flush=True)
        elif ev["event"] == "output":
            print("çıktı:", ev["path"], flush=True)
        elif ev["event"] == "log":
            print(ev["message"], flush=True)

    try:
        assets.ensure(log=lambda m: emit(event="log", message=m))
        project, errors = proj.load(args.project)
        if errors:
            raise proj.ProjectError(_describe(errors))
        if args.cmd == "render":
            o = project["output"]
            if args.transparent:
                o["transparent"] = True
            if args.opaque:
                o["transparent"] = False
            if args.no_combined:
                o["combined"] = False
            if args.no_separate:
                o["separate"] = False
            errors = proj.validate(project)[1]  # seçenek değişiklikleri proje kurallarını bozmasın
            if errors:
                raise proj.ProjectError(_describe(errors))
            run_render(project, output_dir(project, args.out), emit, workers=max(args.workers, 0))
            emit(event="done")
            if not as_json:
                print("BİTTİ")
        else:
            sc = project["scenes"][args.scene]
            png = render.still_png(REGISTRY[sc["type"]], sc["params"], args.t, args.transparent, args.dpi)
            with open(args.out, "wb") as f:
                f.write(png)
            print(args.out)
        return 0
    except (proj.ProjectError, assets.AssetError, RuntimeError, IndexError, OSError) as e:
        if as_json:
            print(json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False), flush=True)
        else:
            print("HATA:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
