import io

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from engine import framing, render
from scenes import county_focus, maplib

S = county_focus.SCENE


def params(**kw):
    clean, errors = S.validate({"state": "FL", **kw})
    assert errors == {}
    return clean


def test_registered_after_state_map():
    from scenes import REGISTRY

    assert list(REGISTRY)[:3] == ["state_map", "county_focus", "price_ladder"]
    assert S.base_duration == 5.0


@pytest.mark.parametrize("focus", [None, ""])
def test_focus_is_required(focus):
    _, errors = S.validate({"state": "FL", "focus": focus})
    assert "focus" in errors


def test_focus_must_belong_to_state():
    _, errors = S.validate({"state": "FL", "focus": "48201"})
    assert "focus" in errors
    assert S.validate({"state": "TX", "focus": "48201"})[1] == {}


def test_no_title_or_subtitle_params():
    names = [p.name for p in S.all_params()]
    assert "title" not in names and "subtitle" not in names
    assert {"state", "categories", "assign", "focus", "focus_name", "focus_sub", "focus_stat", "focus_zoom",
            "zoom", "shift_x", "shift_y", "accent", "duration"} == set(names)


@pytest.mark.parametrize("fips,side", [
    ("12111", "right"),  # St. Lucie, doğu kıyısı
    ("12086", "right"),  # Miami-Dade, doğu kıyısı
    ("12071", "left"),   # Lee, batı kıyısı
    ("12015", "left"),   # Charlotte, batı kıyısı
])
def test_label_goes_to_open_side(fips, side):
    assert maplib.MapGeometry(params(focus=fips), label_side="auto").label_side == side


def test_right_side_mirrors_camera():
    g = maplib.MapGeometry(params(focus="12111"), label_side="auto")
    cx, cy, w = g.cam_focus
    screen_x = (g.focus_center[0] - (cx - w / 2)) / w
    assert abs(screen_x - (1 - framing.FOCUS_SCREEN[0])) < 1e-9


def test_preview_frame_and_statelessness():
    p = params(focus="12015", focus_sub="Punta Gorda", focus_stat="~900 LISTINGS PULLED")
    png = render.still_png(S, p, 4.0)
    img = np.asarray(Image.open(io.BytesIO(png)))
    assert img.shape[:2] == (540, 960) and img[..., :3].std() > 1
    fr = render.Frames(S, p, dpi=20)
    try:
        first = fr.draw(4.0)
        fr.draw(0.2)
        assert np.array_equal(first, fr.draw(4.0))
        # başta hareket yok: 0,0 ve 0,3 aynı kare
        assert np.array_equal(fr.draw(0.0), fr.draw(0.3))
    finally:
        fr.close()


def test_short_render(tmp_path):
    p = params(focus="12071")
    p["duration"] = 2.5
    out = render.render_video(S, p, str(tmp_path / "cf.mp4"))
    assert imageio_ffmpeg.count_frames_and_secs(out) == (75, 2.5)
