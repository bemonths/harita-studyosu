"""FL_20260924 render kontrolünden gelen düzeltmeler: "$" içeren metinler, county_focus açılış kadrajı,
vurgu etiketinin county'ye binmemesi ve su üstünü tercih etmesi."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.text as mtext
import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from engine import render
from scenes import REGISTRY, maplib, state_map

DOLLARS = "BUYERS PAY $94 FOR EVERY $100 ASKED"
# FL_20260924 projesindeki vurgu istatistikleri
STATS = {
    "12055": "6+ MONTHS OF SUPPLY  ·  PRICES STILL AT PEAK",  # Highlands
    "12101": "4 IN 10 SELLERS CUT THEIR PRICE",  # Pasco
    "12105": "4,771 FOR SALE  ·  ≈2,900 IN 2019",  # Polk
    "12021": DOLLARS,  # Collier
}
ASSIGN = {"12055": "buyers", "12101": "buyers", "12105": "buyers", "12021": "price", "12111": "buyers",
          "12085": "buyers", "12093": "stable"}
HISTORY = [{"date": "2024-05-09", "price": 699000}, {"date": "2025-01-10", "price": 649000},
           {"date": "2026-03-12", "price": 599000}]
# vurgu etiketinin tamamen göründüğü an (gerçek saniye, varsayılan süreler)
LABEL_T = {"county_focus": 4.3, "state_map": 12.9}


def frames(scene_id, dpi=40, **kw):
    p, errors = REGISTRY[scene_id].validate(kw)
    assert errors == {}, errors
    return render.Frames(REGISTRY[scene_id], p, dpi=dpi)


def view(ax):
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return np.array([(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0])


# ---------- 6) "$" işaretleri matematik yazısı sanılmaz ----------
TEXT_CASES = [
    ("state_map", dict(state="FL", title="$1 AND $2", subtitle="FROM $300K TO $250K", focus="12021",
                       focus_sub="$5  ·  $6", focus_stat=DOLLARS, assign=ASSIGN)),
    ("county_focus", dict(state="FL", focus="12021", focus_sub="NAPLES $1 $2", focus_stat=DOLLARS, assign=ASSIGN)),
    ("price_ladder", dict(kicker="COLLIER $1  ·  $2", title=DOLLARS, subtitle="$3 AND $4", history=HISTORY,
                          today="2026-09-24", paid=470000, paid_year=2022, paid_text="PAID $470,000 ($1)",
                          diff_text="NOW $5\nBELOW $6")),
]


@pytest.mark.parametrize("scene_id,kw", TEXT_CASES, ids=[c[0] for c in TEXT_CASES])
def test_no_text_is_parsed_as_math(scene_id, kw):
    fr = frames(scene_id, dpi=20, **kw)
    try:
        fr.draw(fr.duration - 0.05)
        texts = [t for t in fr.fig.findobj(mtext.Text) if t.get_text()]
        assert sum(t.get_text().count("$") >= 2 for t in texts) >= 1
        assert [t.get_text() for t in texts if t.get_parse_math()] == []
    finally:
        fr.close()


def test_dollar_stat_renders_as_plain_text():
    # mathtext olsaydı "$94 FOR EVERY $" italik ve boşluksuz ("94FOREVERY") çizilir, genişlik değişirdi
    fr = frames("county_focus", state="FL", focus="12021", focus_stat=DOLLARS, assign=ASSIGN)
    try:
        fr.draw(4.3)
        t = fr.update.layers.t_stat
        r = fr.fig.canvas.get_renderer()
        prop = t.get_fontproperties()
        plain = r.get_text_width_height_descent(DOLLARS, prop, ismath=False)[0]
        math = r.get_text_width_height_descent(DOLLARS, prop, ismath=True)[0]
        assert t.get_text() == DOLLARS
        assert t.get_window_extent(renderer=r).width == pytest.approx(plain, abs=1)
        assert abs(math - plain) > 5
    finally:
        fr.close()


# ---------- 5) county_focus açılış kadrajı ortalı ----------
@pytest.mark.parametrize("state,focus", [("FL", "12015"), ("TN", "47037"), ("CA", "06037"), ("MI", "26163")])
def test_county_focus_opens_centered(state, focus):
    fr = frames("county_focus", dpi=20, state=state, focus=focus)
    try:
        g, m = fr.update.geometry, fr.update.layers
        pts = maplib.to_screen(g.cam_state, np.vstack(g.state_rings))
        (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
        assert (x0 + x1) / 2 == pytest.approx(0.5, abs=1e-6)
        assert (y0 + y1) / 2 == pytest.approx(0.5, abs=1e-6)
        assert y0 >= 0.08 - 1e-9 and y1 <= 0.92 + 1e-9  # üstte ve altta en az %8 boşluk
        assert x0 >= 0.06 - 1e-9 and x1 <= 0.94 + 1e-9
        for t in (0.0, 0.2, 0.39):  # 0–0,4 sn sabit açılış kadrajı
            fr.update(t)
            assert np.allclose(view(m.ax), g.cam_state)
        fr.update(0.42)  # yakınlaşma bu kadrajdan başlar
        assert np.allclose(view(m.ax), g.cam_state, rtol=2e-3)
        fr.update(2.2)
        assert np.allclose(view(m.ax), g.cam_focus)
    finally:
        fr.close()


# ---------- 7) vurgu etiketi county'ye binmez, mümkünse su üstünde durur ----------
def label_layout(scene_id, fips):
    fr = frames(scene_id, state="FL", focus=fips, focus_stat=STATS[fips], assign=ASSIGN)
    fr.draw(LABEL_T[scene_id])
    r = fr.fig.canvas.get_renderer()
    m = fr.update.layers
    boxes = [t.get_window_extent(renderer=r) for t in (m.t_name, m.t_sub, m.t_stat) if t.get_text()]
    return fr, fr.update.geometry, m, boxes


@pytest.mark.parametrize("scene_id", ["county_focus", "state_map"])
@pytest.mark.parametrize("fips", ["12055", "12101", "12105"])  # Highlands, Pasco, Polk
def test_label_keeps_24px_from_county_box(scene_id, fips):
    fr, g, m, boxes = label_layout(scene_id, fips)
    try:
        W, H = fr.w, fr.h
        assert np.allclose(view(m.ax), g.cam_focus)
        pts = maplib.to_screen(g.cam_focus, g.focus_pts) * (W, H)
        pad = 24 * W / 1920
        (x0, y0), (x1, y1) = pts.min(0) - pad, pts.max(0) + pad
        for b in boxes:
            assert b.x1 <= x0 + 1 or b.x0 >= x1 - 1 or b.y1 <= y0 + 1 or b.y0 >= y1 - 1, (b, (x0, y0, x1, y1))
            assert b.x0 >= 0.03 * W - 1 and b.x1 <= 0.97 * W + 1
            assert b.y0 >= 0.03 * H - 1 and b.y1 <= 0.97 * H + 1
        # bağlantı çizgisi yazıların üstünden geçmez: yazılar county merkezinin dış tarafında
        cx = maplib.to_screen(g.cam_focus, g.focus_center)[0, 0] * W
        if g.label_side == "left":
            assert max(b.x1 for b in boxes) < cx
        else:
            assert min(b.x0 for b in boxes) > cx
    finally:
        fr.close()


@pytest.mark.parametrize("scene_id", ["county_focus", "state_map"])
@pytest.mark.parametrize("fips", ["12055", "12101", "12105"])
def test_label_sits_over_water(scene_id, fips):
    # Florida'da bu county'lerin yakınında su var: etiket yazıları eyaletin karasına binmez
    fr, g, m, boxes = label_layout(scene_id, fips)
    try:
        W, H = fr.w, fr.h
        land = unary_union([Polygon(maplib.to_screen(g.cam_focus, r)).buffer(0) for r in g.state_rings])
        for b in boxes:
            rect = box(b.x0 / W, b.y0 / H, b.x1 / W, b.y1 / H)
            assert rect.intersection(land).area / rect.area < 0.01
    finally:
        fr.close()


@pytest.mark.parametrize("fips", ["12055", "12101", "12105", "12131", "12015"])
def test_state_map_label_clear_of_legend(fips):
    # renk açıklaması vurgu sırasında ekranda kalır; etiket ona binmez
    p, errors = REGISTRY["state_map"].validate({"state": "FL", "focus": fips, "focus_stat": STATS.get(fips, DOLLARS),
                                                "assign": ASSIGN})
    assert errors == {}
    fr = render.Frames(REGISTRY["state_map"], p, dpi=40)
    try:
        fr.draw(LABEL_T["state_map"])
        r = fr.fig.canvas.get_renderer()
        m = fr.update.layers
        W, H = fr.w, fr.h
        lx0, ly0, lx1, ly1 = state_map.legend_box(fr.fig, [(t,) for t in fr.update.left_texts[2:]])
        for t in (m.t_name, m.t_sub, m.t_stat):
            if t.get_text():
                b = t.get_window_extent(renderer=r)
                assert b.x1 <= lx0 * W or b.x0 >= lx1 * W or b.y1 <= ly0 * H or b.y0 >= ly1 * H, t.get_text()
    finally:
        fr.close()


def test_highlands_stat_off_red_fill():
    # Highlands: istatistik ("6+ ...") hiçbir county dolgusunun üstüne düşmez
    fr, g, m, boxes = label_layout("county_focus", "12055")
    try:
        W, H = fr.w, fr.h
        stat = m.t_stat.get_window_extent(renderer=fr.fig.canvas.get_renderer())
        rect = box(stat.x0 / W, stat.y0 / H, stat.x1 / W, stat.y1 / H)
        counties = unary_union([Polygon(maplib.to_screen(g.cam_focus, r)).buffer(0) for r in g.c_polys])
        assert rect.intersection(counties).area / rect.area < 0.01
    finally:
        fr.close()
