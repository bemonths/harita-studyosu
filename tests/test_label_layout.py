"""Vurgu etiketi yerleşimi ve harita katmanlarının görünüm kuralları."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from engine import assets
from scenes import REGISTRY, maplib, state_map

SUB = "Santa Rosa Beach  ·  DeFuniak Springs"
MEDIUM_STAT = "1,240 LISTINGS WITHDRAWN IN 12 MONTHS"
LONG_STAT = "BUYERS PULLED BACK: 1,240 LISTINGS WITHDRAWN IN 12 MONTHS"
HUGE_STAT = LONG_STAT + " AS PRICES FELL FOR THE THIRD QUARTER IN A ROW"
ASSIGN = {"12131": "weak", "12055": "buyers", "12015": "price", "12071": "price"}


def layout(scene_id, fips, stat=LONG_STAT, sub=SUB):
    p, errors = REGISTRY[scene_id].validate({"state": "FL", "focus": fips, "focus_sub": sub, "focus_stat": stat,
                                             "assign": ASSIGN})
    assert errors == {}
    fig = plt.figure(figsize=(19.2, 10.8), dpi=50)
    g = maplib.MapGeometry(p, "auto" if scene_id == "county_focus" else "left")
    m = maplib.MapLayers(fig, g, p, assets.fonts())
    m.set_camera(g.cam_focus)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer=r) for t in (m.t_name, m.t_sub, m.t_stat)]
    size = (fig.bbox.width, fig.bbox.height)
    plt.close(fig)
    return g, m, boxes, size


@pytest.mark.parametrize("scene_id", ["county_focus", "state_map"])
@pytest.mark.parametrize("fips", ["12131", "12055"])  # Walton, Highlands
@pytest.mark.parametrize("stat", [LONG_STAT, HUGE_STAT])
def test_label_stays_inside_frame(scene_id, fips, stat):
    g, m, boxes, (W, H) = layout(scene_id, fips, stat)
    for b in boxes:
        assert b.x0 >= 0.03 * W - 1 and b.x1 <= 0.97 * W + 1, (b.x0 / W, b.x1 / W)
        assert b.y0 >= 0.03 * H - 1 and b.y1 <= 0.97 * H + 1, (b.y0 / H, b.y1 / H)


@pytest.mark.parametrize("scene_id", ["county_focus", "state_map"])
@pytest.mark.parametrize("fips", ["12131", "12055"])
def test_label_does_not_cover_county(scene_id, fips):
    g, m, boxes, (W, _) = layout(scene_id, fips)
    _, xl, xr = m._screen_x(g.label_side)
    if g.label_side == "left":
        assert max(b.x1 for b in boxes) / W <= xl + 1e-3
    else:
        assert min(b.x0 for b in boxes) / W >= xr - 1e-3


@pytest.mark.parametrize("fips", ["12131", "12055"])
def test_medium_stat_is_shifted_inward_only(fips):
    # varsayılan yerde kenara taşan ama boşluğa sığan istatistik: yalnızca içeri kayar
    g, m, _, _ = layout("county_focus", fips, MEDIUM_STAT)
    cx = g.focus_center[0]
    fw = g.cam_focus[2]
    default_x = cx - 0.19 * fw if g.label_side == "left" else cx + 0.19 * fw
    assert m.t_stat.get_position()[0] != pytest.approx(default_x)
    assert m.t_stat.get_fontsize() == 26 and "\n" not in m.t_stat.get_text()


@pytest.mark.parametrize("fips", ["12131", "12055"])
def test_long_stat_is_shrunk_at_most_25_percent(fips):
    # boşluğa kaydırınca da sığmayan istatistik: tek satırda en fazla %25 küçülür
    _, m, _, _ = layout("county_focus", fips, LONG_STAT)
    assert 26 * maplib.STAT_MIN_SCALE <= m.t_stat.get_fontsize() < 26
    assert "\n" not in m.t_stat.get_text()


def test_huge_stat_is_split_before_heavy_shrink():
    _, m, _, _ = layout("county_focus", "12055", HUGE_STAT)
    assert "\n" in m.t_stat.get_text()
    assert m.t_stat.get_fontsize() >= 26 * maplib.STAT_MIN_SCALE - 1e-9


def test_sample_label_position_unchanged():
    # Charlotte'ta etiket zaten sığıyor: sol taraf, kayma yok, özgün boyut
    g, m, _, _ = layout("state_map", "12015", "~900 LISTINGS PULLED IN 12 MONTHS", "Punta Gorda  ·  Port Charlotte")
    cx, cy = g.focus_center
    fw = g.cam_focus[2]
    assert g.label_side == "left"
    assert m.t_stat.get_position() == (cx - 0.19 * fw, cy + 0.06 * fw - 0.034 * fw)
    assert m.t_stat.get_fontsize() == 26


def test_split_two_lines():
    assert maplib.split_two_lines("ONE TWO THREE FOUR") == "ONE TWO\nTHREE FOUR"
    assert maplib.split_two_lines("TEK") == "TEK"


def test_legend_shows_only_used_categories():
    p = state_map.SCENE.validate({"state": "FL", "assign": {"12015": "price", "12131": "weak", "12055": "price"}})[0]
    assert [c["key"] for c in state_map.legend_categories(p)] == ["price", "weak", "none"]
    empty = state_map.SCENE.validate({"state": "FL"})[0]
    assert [c["key"] for c in state_map.legend_categories(empty)] == ["none"]


def test_glow_is_stronger_for_orange():
    assert [a for _, a in maplib.GLOW_SPECS] == pytest.approx([0.075, 0.15, 0.33, 1.0])


def test_dimming_keeps_hue():
    g, m, _, _ = layout("county_focus", "12015")
    captured = {}
    m.c_coll.set_facecolors = lambda cols: captured.update(cols=np.array(cols))
    m.set_counties(np.ones(len(g.c_owner)), 0.0)
    assert np.array_equal(captured["cols"][:, :3], m.base_rgba[:, :3])
    m.set_counties(np.ones(len(g.c_owner)), 1.0)
    base = mcolors.rgb_to_hsv(m.base_rgba[:, :3])
    dim = mcolors.rgb_to_hsv(np.clip(captured["cols"][:, :3], 0, 1))
    other = ~m.is_focus
    assert np.allclose(dim[other, 0], base[other, 0], atol=1e-6)            # ton aynı
    assert np.allclose(dim[other, 1], base[other, 1] * (1 - maplib.DIM_SAT))  # doygunluk düşer
    floor = np.minimum(base[other, 2], m.surface_v)  # koyu renkler zeminden karanlığa düşmez
    assert np.allclose(dim[other, 2], np.maximum(base[other, 2] * (1 - maplib.DIM_VAL), floor))  # parlaklık düşer
    assert (dim[other, 2] <= base[other, 2] + 1e-9).all()
    assert np.allclose(captured["cols"][m.is_focus, :3], m.base_rgba[m.is_focus, :3])  # vurgu değişmez
