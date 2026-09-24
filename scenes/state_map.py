"""Eyalet haritası: ABD'den eyalete inen kamera, neon sınır, kategorilere boyanan county'ler, vurgulanan county.
Zamanlamalar orijinal scene_a.py ile aynıdır; update(t) içindeki t temel süre (13 sn) cinsindendir.
Harita katmanları scenes/maplib.py ile county_focus sahnesiyle paylaşılır."""
import matplotlib.patches as mpatches
import numpy as np

from engine import brand
from engine.params import Text
from engine.scene import Scene, cap_scale, ease, fit_text, seg
from scenes import maplib

PARAMS = [
    maplib.state_param(),
    Text("title", "Başlık", default="", auto=True, help="Boş bırakılırsa eyalet adı yazılır."),
    Text("subtitle", "Alt başlık", default=""),
    *maplib.style_params(),
    maplib.assign_param(),
    *maplib.focus_params(required=False),
    *maplib.camera_params(),
]


def legend_categories(p):
    """Renk açıklamasındaki satırlar: assign içinde kullanılan kategoriler (liste sırasıyla) ve en sonda 'none'."""
    used = set(p["assign"].values())
    cats = p["categories"]
    return [c for c in cats if c["key"] != "none" and c["key"] in used] + [c for c in cats if c["key"] == "none"]


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    C = brand.colors()
    g = maplib.MapGeometry(p, label_side="left")
    m = maplib.MapLayers(fig, g, p, F)
    has_focus = g.focus_idx is not None

    # ekran yazıları: başlık, alt başlık, renk açıklaması
    T1 = fig.text(0.055, 0.56, p["title"] or g.state_name.upper(), fontproperties=F["place"],
                  fontsize=150 * cap_scale(fig, F["place"]), color=C["text"], alpha=0, va="bottom")
    fit_text(fig, T1, 0.34)
    T2 = fig.text(0.058, 0.545, p["subtitle"], fontproperties=F["label"], fontsize=26, color=C["muted"], alpha=0, va="top")
    cats = legend_categories(p)
    legend_items = []
    ly = 0.30 + max(0, len(cats) - 5) * 0.045
    for i, c in enumerate(cats):
        y = ly - i * 0.045
        sq = mpatches.FancyBboxPatch((0.058, y - 0.012), 0.016, 0.026, boxstyle="round,pad=0.002",
                                     transform=fig.transFigure, facecolor=c["color"], edgecolor="none", alpha=0)
        fig.add_artist(sq)
        tx = fig.text(0.082, y, c["label"], fontproperties=F["label"], fontsize=22, color=C["muted"], alpha=0, va="center")
        legend_items.append((sq, tx))

    n_c = len(g.counties)
    rank, owner = g.rank, g.c_owner

    def update(t):
        # kamera
        if t < 3.8:
            cam = maplib.cam_lerp(g.cam_us, g.cam_state, seg(t, 0.4, 3.8))
        elif t < 9.0 or not has_focus:
            cam = g.cam_state
        else:
            cam = maplib.cam_lerp(g.cam_state, g.cam_focus, seg(t, 9.0, 11.2))
        m.set_camera(cam)

        # içeri girerken ABD kararır; sınır çizilir
        m.us_coll.set_alpha(1.0 - 0.45 * seg(t, 2.0, 4.0))
        m.set_border(seg(t, 1.6, 4.6), 0.9 * (1 - seg(t, 4.5, 4.9)))
        m.set_isles(0.8 * seg(t, 4.2, 4.9))
        m.state_fill.set_alpha(0.10 * seg(t, 4.3, 5.0) * (1 - seg(t, 5.2, 6.0)))

        # county'ler kuzeyden güneye sırayla belirir; vurgu sırasında diğerleri kararır
        a = np.array([seg(t, 5.0 + 2.6 * rank[o] / n_c, 5.6 + 2.6 * rank[o] / n_c) for o in owner])
        m.set_counties(a, seg(t, 9.2, 10.0) if has_focus else 0.0)

        # county'lerden sonra parıltı yumuşar
        m.set_glow(1.0 - 0.35 * seg(t, 7.5, 8.5))

        # başlıklar
        tt = seg(t, 4.6, 5.4)
        fo = 1 - seg(t, 9.0, 9.6) if has_focus else 1.0
        T1.set_alpha(ease(tt) * fo)
        T1.set_y(0.56 + 0.02 * ease(tt))
        T2.set_alpha(ease(seg(t, 5.0, 5.8)) * fo)
        for i, (sq, tx) in enumerate(legend_items):
            la = ease(seg(t, 7.4 + i * 0.12, 8.0 + i * 0.12))
            sq.set_alpha(la)
            tx.set_alpha(la)

        # vurgu nabzı ve etiket
        if has_focus:
            m.set_focus(glow_on=seg(t, 9.6, 10.2), pulse_t=t - 9.6, leader=ease(seg(t, 10.3, 10.9)),
                        name=ease(seg(t, 10.7, 11.3)), stat=ease(seg(t, 11.4, 12.0)))

    return update


SCENE = Scene(id="state_map", title="Eyalet haritası", base_duration=13.0, params=PARAMS, setup=setup,
              bg_center=(0.6, 0.45))
