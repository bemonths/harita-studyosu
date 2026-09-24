import numpy as np
import pytest

from engine import framing, geo

ORIG_CAM_FL = [0.14131970888099443, 0.08739125759532332, 0.2736116695463418]
FL_TUNE = (0.822673668267268, -0.009999999999999926, 0.05222222222222225)


def test_florida_sample_reproduces_original_camera():
    pts = np.vstack(geo.state_rings("12"))
    cam = framing.state_frame(pts, *FL_TUNE)
    assert np.allclose(cam, ORIG_CAM_FL, rtol=0, atol=1e-12)


@pytest.mark.parametrize("fips", [f for f, _, _ in geo.STATES])
def test_state_fits_region(fips):
    pts = np.vstack(geo.state_rings(fips))
    cx, cy, w = framing.state_frame(pts)
    h = w * 9 / 16
    (xmin, ymin), (xmax, ymax) = pts.min(0), pts.max(0)
    x0, x1, y0, y1 = framing.REGION
    eps = 1e-9
    assert (xmin - (cx - w / 2)) / w >= x0 - eps and (xmax - (cx - w / 2)) / w <= x1 + eps
    assert (ymin - (cy - h / 2)) / h >= y0 - eps and (ymax - (cy - h / 2)) / h <= y1 + eps


def test_focus_matches_original_charlotte():
    ch = next(c for c in geo.counties("12") if c.fips == "12015")
    pts = np.vstack(ch.rings)
    c = pts.mean(0)
    expected = [c[0] - 0.06 * ORIG_CAM_FL[2] * 0.55, c[1] + 0.02 * ORIG_CAM_FL[2], ORIG_CAM_FL[2] * 0.55]
    assert np.allclose(framing.focus_frame(pts, ORIG_CAM_FL[2], 0.55), expected, rtol=0, atol=1e-12)


def test_focus_clamps_county_share():
    square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    size = 16 / 9
    far = framing.focus_frame(square, 1000.0)
    assert abs(size / far[2] - framing.FOCUS_MIN) < 1e-12
    near = framing.focus_frame(square, 1.0)
    assert abs(size / near[2] - framing.FOCUS_MAX) < 1e-12


def test_box_matches_original_formula():
    pts = np.array([[0.0, 0.0], [2.0, 1.0]])
    assert np.allclose(framing.box(pts, 0.06), [1.0, 0.5, 2.0 * 1.06])
