"""Eyalet haritası: ABD'den eyalete inen kamera, neon sınır, kategorilere boyanan county'ler, vurgulanan county.
Görünüm ve zamanlamalar orijinal scene_a.py ile aynıdır; update(t) içindeki t temel süre (13 sn) cinsindendir."""
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.collections import PolyCollection

from engine import brand, framing, geo
from engine.params import Categories, Color, CountyAssign, CountySelect, Number, StateSelect, Text
from engine.scene import Scene, cap_scale, ease, fit_text, seg

DEFAULT_CATEGORIES = brand.categories()

PARAMS = [
    StateSelect("state", "Eyalet", default="FL"),
    Text("title", "Başlık", default="", auto=True, help="Boş bırakılırsa eyalet adı yazılır."),
    Text("subtitle", "Alt başlık", default=""),
    Color("accent", "Sınır rengi (neon)", default=brand.color("accent"), group="Renkler"),
    Categories("categories", "Renk kategorileri", default=DEFAULT_CATEGORIES, group="Renkler"),
    CountyAssign("assign", "County boyama", default={}, group="County boyama",
                 state_param="state", categories_param="categories"),
    CountySelect("focus", "Vurgulanan county", default=None, group="Vurgu", state_param="state"),
    Text("focus_name", "Vurgu adı", default="", auto=True, group="Vurgu",
         help="Boş bırakılırsa '<AD> COUNTY' yazılır."),
    Text("focus_sub", "Vurgu alt yazısı", default="", group="Vurgu"),
    Text("focus_stat", "Vurgu istatistiği", default="", group="Vurgu",
         help="County'nin kategori renginde yazılır."),
    Number("focus_zoom", "Vurgu yakınlığı", default=0.55, group="Vurgu", lo=0.1, hi=1.5, step=0.05),
    Number("zoom", "Yakınlaştırma", default=1.0, group="Kamera", lo=0.5, hi=2.0, step=0.01),
    Number("shift_x", "Yatay kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
    Number("shift_y", "Dikey kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
]


def cam_lerp(a, b, t):
    e = ease(t)
    c = a[:2] + (b[:2] - a[:2]) * e
    w = np.exp(np.log(a[2]) + (np.log(b[2]) - np.log(a[2])) * e)
    return np.array([c[0], c[1], w])


def focus_title(c):
    return (f"{c.name} {c.lsad}" if c.lsad else c.name).upper()


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    PLACE, BAR, BARB = F["place"], F["label"], F["label_bold"]
    C = brand.colors()
    PK = cap_scale(fig, PLACE)  # yer adı yazı tipini tasarım boyutlarına eşitler
    NEON = p["accent"]
    fips, _, state_name = geo.state(p["state"])
    cats = p["categories"]
    col = {c["key"]: c["color"] for c in cats}

    # ---------- geometri ----------
    us = geo.us_outlines(fips)
    us_polys = [r for _, rs in us for r in rs]
    fl_rings = [r for st, rs in us if st == fips for r in rs]
    cs = geo.counties(fips)
    c_polys, c_owner = [], []
    for i, c in enumerate(cs):
        for r in c.rings:
            c_polys.append(r)
            c_owner.append(i)
    c_owner = np.array(c_owner)
    c_key = [p["assign"].get(c.fips, "none") for c in cs]

    # ---------- kamera ----------
    CAM_US = framing.box(np.vstack(us_polys), 0.06)
    CAM_FL = framing.state_frame(np.vstack(fl_rings), p["zoom"], p["shift_x"], p["shift_y"])
    ch_idx = next((i for i, c in enumerate(cs) if c.fips == p["focus"]), None)
    if ch_idx is not None:
        ch_pts = np.vstack(cs[ch_idx].rings)
        ch_center = ch_pts.mean(0)
        CAM_CH = framing.focus_frame(ch_pts, CAM_FL[2], p["focus_zoom"])

    # ---------- figür ----------
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.patch.set_alpha(0)
    for lon in range(-125, -64, 5):
        la = np.linspace(20, 52, 120)
        x, y = geo.albers(np.full_like(la, lon), la)
        ax.plot(x, y, color=C["line"], lw=0.6, alpha=0.5, zorder=1)
    for lat in range(20, 55, 5):
        lo = np.linspace(-130, -60, 200)
        x, y = geo.albers(lo, np.full_like(lo, lat))
        ax.plot(x, y, color=C["line"], lw=0.6, alpha=0.5, zorder=1)

    us_coll = PolyCollection(us_polys, facecolors=C["surface"], edgecolors=C["line"], linewidths=0.8, zorder=2)
    ax.add_collection(us_coll)
    fl_fill = PolyCollection(fl_rings, facecolors=NEON, edgecolors="none", alpha=0.0, zorder=3)
    ax.add_collection(fl_fill)
    base_rgba = np.array([mcolors.to_rgba(col[c_key[o]]) for o in c_owner])
    c_coll = PolyCollection(c_polys, facecolors=base_rgba, edgecolors=C["bg_dark"], linewidths=0.9, zorder=4)
    ax.add_collection(c_coll)

    # ana halka üzerinde neon sınır
    main = max(fl_rings, key=len)
    segl = np.hypot(*np.diff(main, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(segl)])
    glow_specs = [(16, 0.05), (10, 0.10), (6, 0.22), (2.4, 1.0)]
    glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_capstyle="round", zorder=6)[0] for w, a in glow_specs]
    isles = [r for r in fl_rings if r is not main]
    isle_lines = [ax.plot(r[:, 0], r[:, 1], color=NEON, lw=1.4, alpha=0.0, zorder=6)[0] for r in isles]
    head = ax.plot([], [], "o", color=C["text"], ms=7, alpha=0.0, zorder=7)[0]

    def partial(t):
        L = cum[-1] * t
        k = np.searchsorted(cum, L)
        if k == 0:
            return main[:1]
        k = min(k, len(main) - 1)
        f = (L - cum[k - 1]) / max(cum[k] - cum[k - 1], 1e-9)
        pt = main[k - 1] + (main[k] - main[k - 1]) * f
        return np.vstack([main[:k], pt])

    # vurgulanan county
    ch_glow = []
    if ch_idx is not None:
        for r in cs[ch_idx].rings:
            for w, a in [(12, 0.08), (6, 0.2), (2.2, 1.0)]:
                ch_glow.append((ax.plot(r[:, 0], r[:, 1], color=NEON, lw=w, alpha=0.0, zorder=8)[0], a))
        lab_x = ch_center[0] - 0.19 * CAM_CH[2]
        lab_y = ch_center[1] + 0.06 * CAM_CH[2]
        leader = ax.plot([], [], color=C["text"], lw=1.6, alpha=0.0, zorder=9)[0]
        dot = ax.plot([ch_center[0]], [ch_center[1]], "o", color=C["text"], ms=9, alpha=0.0, zorder=9)[0]
        t_name = ax.text(lab_x, lab_y, p["focus_name"] or focus_title(cs[ch_idx]), fontproperties=PLACE, fontsize=64 * PK,
                         color=C["text"], ha="right", va="bottom", alpha=0, zorder=10)
        fit_text(fig, t_name, 0.30)
        t_sub = ax.text(lab_x, lab_y, p["focus_sub"], fontproperties=BAR, fontsize=24, color=C["muted"],
                        ha="right", va="top", alpha=0, zorder=10)
        stat_color = col[c_key[ch_idx]] if c_key[ch_idx] != "none" else NEON
        t_stat = ax.text(lab_x, lab_y, p["focus_stat"], fontproperties=BARB, fontsize=26, color=stat_color,
                         ha="right", va="top", alpha=0, zorder=10)

    # ekran yazıları
    T1 = fig.text(0.055, 0.56, p["title"] or state_name.upper(), fontproperties=PLACE, fontsize=150 * PK,
                  color=C["text"], alpha=0, va="bottom")
    fit_text(fig, T1, 0.34)
    T2 = fig.text(0.058, 0.545, p["subtitle"], fontproperties=BAR, fontsize=26, color=C["muted"], alpha=0, va="top")
    legend_items = []
    ly = 0.30 + max(0, len(cats) - 5) * 0.045
    for i, c in enumerate(cats):
        y = ly - i * 0.045
        sq = mpatches.FancyBboxPatch((0.058, y - 0.012), 0.016, 0.026, boxstyle="round,pad=0.002",
                                     transform=fig.transFigure, facecolor=c["color"], edgecolor="none", alpha=0)
        fig.add_artist(sq)
        tx = fig.text(0.082, y, c["label"], fontproperties=BAR, fontsize=22, color=C["muted"], alpha=0, va="center")
        legend_items.append((sq, tx))

    n_c = len(cs)
    rank = np.argsort(np.argsort(-np.array([np.vstack(c.rings)[:, 1].mean() for c in cs])))
    bgc = np.array(mcolors.to_rgb(C["surface"]))
    edge = np.array([[*mcolors.to_rgb(C["bg_dark"]), 1.0]] * len(c_owner))
    is_focus = c_owner == ch_idx if ch_idx is not None else np.zeros(len(c_owner), bool)

    def update(t):
        # kamera
        if t < 3.8:
            cam = cam_lerp(CAM_US, CAM_FL, seg(t, 0.4, 3.8))
        elif t < 9.0 or ch_idx is None:
            cam = CAM_FL
        else:
            cam = cam_lerp(CAM_FL, CAM_CH, seg(t, 9.0, 11.2))
        ax.set_xlim(cam[0] - cam[2] / 2, cam[0] + cam[2] / 2)
        ax.set_ylim(cam[1] - cam[2] * 9 / 32, cam[1] + cam[2] * 9 / 32)

        # içeri girerken ABD kararır
        us_coll.set_alpha(1.0 - 0.45 * seg(t, 2.0, 4.0))

        # sınır çizimi
        d = seg(t, 1.6, 4.6)
        if d > 0:
            pts = partial(ease(d))
            for ln in glow:
                ln.set_data(pts[:, 0], pts[:, 1])
            head.set_data([pts[-1, 0]], [pts[-1, 1]])
            head.set_alpha(0.9 * (1 - seg(t, 4.5, 4.9)))
        else:
            for ln in glow:
                ln.set_data([], [])
            head.set_data([], [])
            head.set_alpha(0.0)
        for ln in isle_lines:
            ln.set_alpha(0.8 * seg(t, 4.2, 4.9))
        fl_fill.set_alpha(0.10 * seg(t, 4.3, 5.0) * (1 - seg(t, 5.2, 6.0)))

        # county'ler sırayla belirir; vurgu sırasında diğerleri kararır
        cols = base_rgba.copy()
        a = np.array([seg(t, 5.0 + 2.6 * rank[o] / n_c, 5.6 + 2.6 * rank[o] / n_c) for o in c_owner])
        focus = seg(t, 9.2, 10.0) if ch_idx is not None else 0.0
        k = np.where(is_focus, 0.0, 0.62 * focus)[:, None]
        cols[:, :3] = cols[:, :3] * (1 - k) + bgc * k
        cols[:, 3] = a * 0.95
        c_coll.set_facecolors(cols)
        ec = edge.copy()
        ec[:, 3] = a
        c_coll.set_edgecolors(ec)

        # county'lerden sonra parıltı yumuşar
        soft = 1.0 - 0.35 * seg(t, 7.5, 8.5)
        for ln, (_, a0) in zip(glow, glow_specs):
            ln.set_alpha(a0 * soft)

        # başlıklar
        tt = seg(t, 4.6, 5.4)
        fo = 1 - seg(t, 9.0, 9.6) if ch_idx is not None else 1.0
        T1.set_alpha(ease(tt) * fo)
        T1.set_y(0.56 + 0.02 * ease(tt))
        T2.set_alpha(ease(seg(t, 5.0, 5.8)) * fo)
        for i, (sq, tx) in enumerate(legend_items):
            la = ease(seg(t, 7.4 + i * 0.12, 8.0 + i * 0.12))
            sq.set_alpha(la)
            tx.set_alpha(la)

        if ch_idx is None:
            return
        # vurgu nabzı ve etiket
        pa = seg(t, 9.6, 10.2)
        pulse = 0.55 + 0.45 * np.cos((t - 9.6) * 2 * np.pi * 0.9) if t > 9.6 else 0
        for ln, a0 in ch_glow:
            ln.set_alpha(a0 * pa * (0.35 + 0.65 * max(pulse, 0)))
        lp = ease(seg(t, 10.3, 10.9))
        elbow = (lab_x + 0.01 * CAM_CH[2], lab_y)
        ex = ch_center[0] + (elbow[0] - ch_center[0]) * lp
        ey = ch_center[1] + (elbow[1] - ch_center[1]) * lp
        leader.set_data([ch_center[0], ex], [ch_center[1], ey])
        leader.set_alpha(0.9 * (lp > 0))
        dot.set_alpha(pa)
        na = ease(seg(t, 10.7, 11.3))
        t_name.set_alpha(na)
        t_sub.set_alpha(na)
        t_name.set_position((lab_x, lab_y + 0.004 * CAM_CH[2]))
        t_sub.set_position((lab_x, lab_y - 0.004 * CAM_CH[2]))
        t_stat.set_position((lab_x, lab_y - 0.034 * CAM_CH[2]))
        t_stat.set_alpha(ease(seg(t, 11.4, 12.0)))

    return update


SCENE = Scene(id="state_map", title="Eyalet haritası", base_duration=13.0, params=PARAMS, setup=setup,
              bg_center=(0.6, 0.45))
