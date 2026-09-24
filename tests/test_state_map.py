import numpy as np
import pytest

from engine import render
from scenes import state_map

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


def test_no_focus_keeps_state_view():
    fr = render.Frames(S, params(state="TN"), dpi=20)
    try:
        a, b = fr.draw(9.5), fr.draw(12.9)
    finally:
        fr.close()
    assert np.abs(a.astype(int) - b.astype(int)).mean() < 0.5


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
