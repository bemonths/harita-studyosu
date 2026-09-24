import json
import os
import subprocess
import sys

import imageio_ffmpeg
import pytest
from PIL import Image

from engine import assets, cli
from tests.helpers import decode_frame

SAMPLE = os.path.join("projects", "ornek_florida.json")


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "engine.cli", *args], cwd=assets.ROOT, capture_output=True,
                          text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})


def test_still(tmp_path):
    out = tmp_path / "kare.png"
    r = run_cli("still", SAMPLE, "--scene", "0", "--t", "8.6", "--out", str(out), "--dpi", "50")
    assert r.returncode == 0, r.stderr
    assert Image.open(out).size == (960, 540)


def test_bad_project_reports_error_event(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": 1, "name": "x",
                               "scenes": [{"type": "state_map", "params": {"accent": "mavi"}}]}), encoding="utf-8")
    r = run_cli("render", str(bad), "--progress-json")
    assert r.returncode == 1
    last = json.loads(r.stdout.strip().splitlines()[-1])
    assert last["event"] == "error" and "accent" in last["message"]


def test_run_render_combined_only(dummy_scene, tmp_path, monkeypatch):
    monkeypatch.setitem(cli.REGISTRY, "dummy", dummy_scene)
    p = {"name": "t", "transition": 0.5,
         "output": {"separate": False, "combined": True, "transparent": False},
         "scenes": [{"type": "dummy", "enabled": True, "params": dummy_scene.defaults()} for _ in range(2)]}
    events = []
    outs = cli.run_render(p, str(tmp_path), lambda **e: events.append(e))
    assert [os.path.basename(o) for o in outs] == ["birlesik.mp4"]
    assert sorted(os.listdir(tmp_path)) == ["birlesik.mp4"]
    assert events[-1] == {"event": "output", "path": outs[0]}
    assert any(e["event"] == "compose" for e in events)
    assert events[0] == {"event": "progress", "scene": 0, "scenes": 2, "frame": 1, "total": 30}


def test_run_render_single_scene_ignores_combine(dummy_scene, tmp_path, monkeypatch):
    monkeypatch.setitem(cli.REGISTRY, "dummy", dummy_scene)
    p = {"name": "t", "transition": 0.5,
         "output": {"separate": False, "combined": True, "transparent": True},
         "scenes": [{"type": "dummy", "enabled": True, "params": dummy_scene.defaults()},
                    {"type": "dummy", "enabled": False, "params": dummy_scene.defaults()}]}
    outs = cli.run_render(p, str(tmp_path), lambda **e: None)
    assert [os.path.basename(o) for o in outs] == ["01_dummy.mov"]


@pytest.mark.slow
def test_render_sample_matches_original_length(tmp_path):
    r = run_cli("render", SAMPLE, "--out", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert imageio_ffmpeg.count_frames_and_secs(str(tmp_path / "birlesik.mp4")) == (717, 23.9)
    assert (tmp_path / "01_state_map.mp4").exists() and (tmp_path / "02_price_ladder.mp4").exists()


@pytest.mark.slow
def test_render_transparent(tmp_path):
    with open(os.path.join(assets.ROOT, SAMPLE), encoding="utf-8") as f:
        p = json.load(f)
    p["scenes"][0]["params"]["duration"] = 6.5
    p["scenes"][1]["params"]["duration"] = 5.75
    src = tmp_path / "p.json"
    src.write_text(json.dumps(p), encoding="utf-8")
    r = run_cli("render", str(src), "--out", str(tmp_path / "o"), "--transparent")
    assert r.returncode == 0, r.stderr
    f = decode_frame(str(tmp_path / "o" / "birlesik.mov"), 3.0, 1920, 1080)
    assert (f[..., 3] == 0).mean() > 0.2 and f[..., 3].max() == 255
