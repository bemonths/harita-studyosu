"""Paralel render: işçi sayısı, hata yayılımı, sıralı render'la aynı çıktı ve toplam ilerleme olayları."""
import os

import numpy as np
import pytest

from engine import cli, parallel
from scenes import REGISTRY
from tests.helpers import decode_frame


def test_auto_workers(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: 32)
    assert parallel.auto_workers(31) == 16
    assert parallel.auto_workers(3) == 3
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    assert parallel.auto_workers(10) == 1


def test_scene_error_is_raised(tmp_path):
    jobs = [(0, "yok_boyle_sahne", {}, str(tmp_path / "a.mp4"), 10), (1, "yok_boyle_sahne", {}, str(tmp_path / "b.mp4"), 10)]
    with pytest.raises(KeyError):
        parallel.render_scenes(jobs, False, 2, lambda **e: None)


def short_project(scene_ids):
    scenes = []
    for sid in scene_ids:
        p = REGISTRY[sid].defaults()
        p["duration"] = REGISTRY[sid].base_duration * 0.5
        scenes.append({"type": sid, "enabled": True, "params": p})
    return {"name": "t", "transition": 0.5, "output": {"separate": True, "combined": True, "transparent": False},
            "scenes": scenes}


@pytest.mark.slow
def test_parallel_matches_sequential(tmp_path):
    project = short_project(["ring", "house_bars", "bar_list"])
    events = []
    par = cli.run_render(project, str(tmp_path / "p"), lambda **e: events.append(e), workers=3)
    seq = cli.run_render(project, str(tmp_path / "s"), lambda **e: None, workers=1)
    assert [os.path.basename(p) for p in par] == [os.path.basename(p) for p in seq] == [
        "01_ring.mp4", "02_house_bars.mp4", "03_bar_list.mp4", "birlesik.mp4"]
    for a, b in zip(par, seq):
        fa, fb = decode_frame(a, 2.5, 1920, 1080), decode_frame(b, 2.5, 1920, 1080)
        assert np.abs(fa.astype(int) - fb.astype(int)).mean() < 1.0   # yalnız kodlayıcı iş parçacığı farkı
    progress = [e for e in events if e["event"] == "progress"]
    assert progress and all("overall" in e for e in progress)
    assert progress[-1]["overall"] == 1.0 and progress[-1]["finished"] == 3
    assert [e["overall"] for e in progress] == sorted(e["overall"] for e in progress)
