import numpy as np
import pytest

from engine import render
from scenes import maplib, state_map

S = state_map.SCENE


def params(**kw):
    clean, errors = S.validate(kw)
    assert errors == {}
    return clean


@pytest.mark.parametrize("state,focus", [
    ("FL", "12015"), ("TX", "48201"), ("MI", "26163"), ("RI", "44007"),
    ("CA", "06037"), ("NC", "37119"), ("VA", "51760"),
])
def test_smoke_states(state, focus):
    fr = render.Frames(S, params(state=state, focus=focus), dpi=20)
    try:
        for t in (0.5, 4.0, 8.6, 10.5, 12.9):
            img = fr.draw(t)
            assert img.shape == (216, 384, 4)
            assert img[..., :3].std() > 1
    finally:
        fr.close()


def camera_at(fr, t):
    fr.update(t)
    (x0, x1), (y0, y1) = fr.update.layers.ax.get_xlim(), fr.update.layers.ax.get_ylim()
    return np.array([(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0])


def test_no_focus_slow_zoom_until_end():
    # vurgu yoksa 8,5 sn'den sahne sonuna kadar toplam %3 yavaş yakınlaşma; eyalet ekranda yerinde kalır
    fr = render.Frames(S, params(state="TN"), dpi=20)
    try:
        g = fr.update.geometry
        assert np.allclose(camera_at(fr, 4.0), g.cam_state)
        assert np.allclose(camera_at(fr, 8.5), g.cam_state)
        widths = [camera_at(fr, t)[2] for t in (8.5, 9.5, 11.0, 12.4, 13.0)]
        assert all(a > b for a, b in zip(widths, widths[1:]))
        assert widths[-1] == pytest.approx(g.cam_state[2] * (1 - state_map.DRIFT_ZOOM))
        home = maplib.to_screen(g.cam_state, g.state_center)
        for t in (9.5, 13.0):
            assert np.allclose(maplib.to_screen(camera_at(fr, t), g.state_center), home)
        a, b = fr.draw(9.5), fr.draw(12.9)
        assert np.abs(a.astype(int) - b.astype(int)).mean() > 0.05
    finally:
        fr.close()


def test_focus_view_static_until_zoom():
    fr = render.Frames(S, params(state="FL", focus="12015"), dpi=20)
    try:
        g = fr.update.geometry
        for t in (4.0, 8.5, 8.99):
            assert np.allclose(camera_at(fr, t), g.cam_state)
        assert np.allclose(camera_at(fr, 11.2), g.cam_focus)
    finally:
        fr.close()


def test_scrubbing_backwards_is_stateless():
    fr = render.Frames(S, params(state="FL", focus="12015"), dpi=20)
    try:
        first = fr.draw(1.0)
        fr.draw(12.0)
        again = fr.draw(1.0)
    finally:
        fr.close()
    assert np.array_equal(first, again)


def test_long_title_smoke():
    fr = render.Frames(S, params(state="MA", title="MASSACHUSETTS AND NORTH CAROLINA"), dpi=20)
    try:
        assert fr.draw(6.0)[..., :3].std() > 1
    finally:
        fr.close()


def test_focus_must_be_in_state():
    _, errors = S.validate({"state": "FL", "focus": "48201"})
    assert "focus" in errors
