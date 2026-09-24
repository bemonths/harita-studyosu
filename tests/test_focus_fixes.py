"""Odak noktası, istatistik rengi, etiket kontürü, sol blok boşluğu ve kategorisiz odak county testleri."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from engine import assets, framing, geo, render
from scenes import REGISTRY, maplib, state_map

STATE_OF = {"12": "FL", "26": "MI"}


def params(scene_id, fips, **kw):
    p, errors = REGISTRY[scene_id].validate({"state": STATE_OF[fips[:2]], "focus": fips, **kw})
    assert errors == {}
    return p


def layers(p, label_side="auto"):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=20)
    g = maplib.MapGeometry(p, label_side)
    m = maplib.MapLayers(fig, g, p, assets.fonts())
    return fig, g, m


def county_shape(fips):
    c = next(c for c in geo.counties(fips[:2]) if c.fips == fips)
    return unary_union([Polygon(r).buffer(0) for r in c.rings])


# 1) odak noktası county'nin içinde; kamera, bağlantı çizgisi ve nokta aynı noktayı kullanır
@pytest.mark.parametrize("fips", ["12015", "12087", "26083"])  # Charlotte, Monroe, Keweenaw
def test_focus_point_inside_county(fips):
    g = maplib.MapGeometry(params("county_focus", fips), "auto")
    assert county_shape(fips).contains(Point(*g.focus_center))


@pytest.mark.parametrize("fips", ["12015", "12087", "26083"])
def test_camera_leader_and_dot_use_focus_point(fips):
    fig, g, m = layers(params("county_focus", fips, focus_stat="TEST"))
    try:
        cx, cy = g.focus_center
        cam = g.cam_focus
        screen_x = (cx - (cam[0] - cam[2] / 2)) / cam[2]
        expected = framing.FOCUS_SCREEN[0] if g.label_side == "left" else 1 - framing.FOCUS_SCREEN[0]
        assert screen_x == pytest.approx(expected)
        m.set_focus(1.0, 1.0, 1.0, 1.0, 1.0)
        xs, ys = m.leader.get_data()
        assert (xs[0], ys[0]) == (cx, cy)
        assert tuple(np.ravel(m.dot.get_data())) == (cx, cy)
    finally:
        plt.close(fig)


# 2) koyu kategori renginde istatistik açık tonla yazılır; dolgu asıl renkte kalır
def test_readable_on_dark():
    light = maplib.readable_on_dark("#3e6a8f", "#f4ecdd")
    assert mcolors.rgb_to_hsv(mcolors.to_rgb(light))[2] >= maplib.STAT_MIN_VALUE
    assert maplib.readable_on_dark("#e9b949", "#f4ecdd") == "#e9b949"  # zaten açık renk aynen kalır


def test_stat_light_tone_fill_unchanged():
    fig, g, m = layers(params("county_focus", "12009", assign={"12009": "stable"}, focus_stat="HOLDING"))
    try:
        stat = mcolors.to_rgb(m.t_stat.get_color())
        assert mcolors.rgb_to_hsv(stat)[2] >= maplib.STAT_MIN_VALUE
        assert mcolors.to_hex(stat) != "#3e6a8f"
        assert np.allclose(m.base_rgba[m.is_focus][:, :3], mcolors.to_rgb("#3e6a8f"))
    finally:
        plt.close(fig)


# 3) etiket yazılarında zemin renginde kontür
def test_label_texts_have_outline():
    fig, g, m = layers(params("county_focus", "12015", focus_sub="SUB", focus_stat="STAT"))
    try:
        for t in (m.t_name, m.t_sub, m.t_stat):
            effects = t.get_path_effects()
            assert len(effects) == 1 and isinstance(effects[0], pe.withStroke)
    finally:
        plt.close(fig)


# 4) state_map: sol blok ile eyalet arasında en az %3 boşluk; eyalet ekranın içinde
@pytest.mark.parametrize("abbr", ["WA", "MA", "LA", "OK"])
def test_left_block_keeps_gap(abbr):
    p, errors = state_map.SCENE.validate({"state": abbr, "subtitle": "10 COUNTIES  ·  AUGUST 2026 DATA"})
    assert errors == {}
    fr = render.Frames(state_map.SCENE, p, dpi=50)
    try:
        u = fr.update
        gap = state_map.state_left(u.geometry) - state_map.block_right(fr.fig, u.left_texts)
        assert gap >= state_map.LEFT_GAP - 1e-3, gap
        cam, pts = u.geometry.cam_state, np.vstack(u.geometry.state_rings)
        left, bottom = cam[0] - cam[2] / 2, cam[1] - cam[2] * 9 / 32
        assert (pts[:, 0].max() - left) / cam[2] <= 0.97
        assert 0.0 <= (pts[:, 1].min() - bottom) / (cam[2] * 9 / 16) and (pts[:, 1].max() - bottom) / (cam[2] * 9 / 16) <= 1.0
    finally:
        fr.close()


def test_left_block_untouched_when_it_fits():
    # Florida örneğinde boşluk zaten yeterli: başlık küçülmez, eyalet kaymaz
    p = state_map.SCENE.validate({"state": "FL", "subtitle": "10 COUNTIES  ·  AUGUST 2026 DATA"})[0]
    g = maplib.MapGeometry(p, "left")
    before = g.cam_state.copy()
    fr = render.Frames(state_map.SCENE, p, dpi=50)
    try:
        assert np.allclose(fr.update.geometry.cam_state, before)
    finally:
        fr.close()


# 5) kategorisiz odak county'si vurgu rengiyle görünür olur
def test_none_focus_gets_accent_tint_and_glow():
    p = params("county_focus", "26083", focus_stat="NO DATA")  # Keweenaw, assign boş
    fig, g, m = layers(p)
    try:
        captured = {}
        m.c_coll.set_facecolors = lambda cols: captured.update(cols=np.array(cols))
        m.set_counties(np.ones(len(g.c_owner)), 1.0)
        base = m.base_rgba[m.is_focus, :3]
        accent = np.array(mcolors.to_rgb(p["accent"]))
        a = maplib.NONE_FOCUS_TINT
        assert np.allclose(captured["cols"][m.is_focus, :3], base * (1 - a) + accent * a)
        assert all(mcolors.to_hex(ln.get_color()) == p["accent"] for ln, _ in m.ch_glow)
        assert mcolors.to_hex(m.t_stat.get_color()) == p["accent"]
        m.set_counties(np.ones(len(g.c_owner)), 0.0)  # odak öncesi dolgu değişmez
        assert np.allclose(captured["cols"][m.is_focus, :3], base)
    finally:
        plt.close(fig)
