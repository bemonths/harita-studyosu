"""Eyalet haritası: ABD'den eyalete inen kamera, neon sınır, kategorilere boyanan county'ler, vurgulanan county.
Zamanlamalar orijinal scene_a.py ile aynıdır; update(t) içindeki t temel süre (13 sn) cinsindendir.
Harita katmanları scenes/maplib.py ile county_focus sahnesiyle paylaşılır."""
import matplotlib.patches as mpatches
import numpy as np

from engine import brand, framing
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


# sol blok (başlık, alt başlık, açıklama) ile eyalet sınırı arasındaki en az boşluk (ekran oranı);
# başlığın bunun için küçülebileceği en düşük oran
LEFT_GAP, TITLE_MIN_SCALE = 0.03, 0.7
# vurgu yoksa DRIFT_START'tan sahne sonuna (DRIFT_END, temel süre) kadar toplam DRIFT_ZOOM oranında yakınlaşma
DRIFT_START, DRIFT_END, DRIFT_ZOOM = 8.5, 13.0, 0.03


def state_left(g):
    """Eyaletin eyalet kadrajındaki sol kenarının ekran x'i (0–1)."""
    cam = g.cam_state
    xmin = min(r[:, 0].min() for r in g.state_rings)
    return (xmin - (cam[0] - cam[2] / 2)) / cam[2]


def block_right(fig, texts):
    """Yazıların en sağ kenarının ekran x'i (0–1)."""
    r = fig.canvas.get_renderer()
    edges = [t.get_window_extent(renderer=r).x1 / fig.bbox.width for t in texts if t.get_text()]
    return max(edges, default=0.0)


def legend_box(fig, items):
    """Renk açıklamasının kapladığı ekran bölgesi (x0, y0, x1, y1; figür oranı, y aşağıdan yukarı)."""
    r = fig.canvas.get_renderer()
    bbs = [a.get_window_extent(renderer=r) for item in items for a in item]
    W, H = fig.bbox.width, fig.bbox.height
    return (min(b.x0 for b in bbs) / W, min(b.y0 for b in bbs) / H,
            max(b.x1 for b in bbs) / W, max(b.y1 for b in bbs) / H)


def fit_left_block(fig, g, p, title, texts):
    """Sol blok ile eyalet arasında en az LEFT_GAP boşluk bırakır. Önce başlığı küçültür (en fazla %30),
    yetmezse eyaleti sağa kaydırır; ekrana sığması için gerekirse eyalet kadrajı biraz küçülür."""
    limit = state_left(g) - LEFT_GAP
    if block_right(fig, texts) <= limit:
        return
    r = fig.canvas.get_renderer()
    ext = title.get_window_extent(renderer=r)
    room = limit - ext.x0 / fig.bbox.width
    if title.get_text() and ext.width / fig.bbox.width > room > 0:
        size = title.get_fontsize()
        title.set_fontsize(max(size * TITLE_MIN_SCALE, size * room / (ext.width / fig.bbox.width) * 0.99))
    if block_right(fig, texts) <= limit:
        return
    x0 = min(block_right(fig, texts) + LEFT_GAP, 0.7)
    pts = np.vstack(g.state_rings)
    g.set_state_camera(framing.state_frame(pts, p["zoom"], p["shift_x"], p["shift_y"],
                                           region=(x0, 0.96, 0.08, 0.94)))
    deficit = x0 - state_left(g)  # kullanıcı yakınlaştırması eyaleti yine sola taşırsa doğrudan kaydır
    if deficit > 0:
        cam = g.cam_state.copy()
        cam[0] -= deficit * cam[2]
        g.set_state_camera(cam)


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    C = brand.colors()
    g = maplib.MapGeometry(p, label_side="left")
    m = maplib.MapLayers(fig, g, p, F, place_label=False)
    has_focus = g.focus_idx is not None

    # ekran yazıları: başlık, alt başlık, renk açıklaması
    T1 = fig.text(0.055, 0.56, p["title"] or g.state_name.upper(), parse_math=False, fontproperties=F["place"],
                  fontsize=150 * cap_scale(fig, F["place"]), color=C["text"], alpha=0, va="bottom")
    fit_text(fig, T1, 0.34)
    T2 = fig.text(0.058, 0.545, p["subtitle"], parse_math=False, fontproperties=F["label"], fontsize=26,
                  color=C["muted"], alpha=0, va="top")
    cats = legend_categories(p)
    legend_items = []
    ly = 0.30 + max(0, len(cats) - 5) * 0.045
    for i, c in enumerate(cats):
        y = ly - i * 0.045
        sq = mpatches.FancyBboxPatch((0.058, y - 0.012), 0.016, 0.026, boxstyle="round,pad=0.002",
                                     transform=fig.transFigure, facecolor=c["color"], edgecolor="none", alpha=0)
        fig.add_artist(sq)
        tx = fig.text(0.082, y, c["label"], parse_math=False, fontproperties=F["label"], fontsize=22,
                      color=C["muted"], alpha=0, va="center")
        legend_items.append((sq, tx))

    left_texts = [T1, T2, *(tx for _, tx in legend_items)]
    fit_left_block(fig, g, p, T1, left_texts)
    if has_focus:
        # eyalet kadrajı kesinleştikten sonra (vurgu kamerası ona bağlı); renk açıklaması vurguda da ekranda kalır
        m.place_label(fig, avoid=[legend_box(fig, legend_items)])

    n_c = len(g.counties)
    rank, owner = g.rank, g.c_owner

    def update(t):
        # kamera
        if t < 3.8:
            cam = maplib.cam_lerp(g.cam_us, g.cam_state, seg(t, 0.4, 3.8))
        elif has_focus:
            cam = maplib.cam_lerp(g.cam_state, g.cam_focus, seg(t, 9.0, 11.2)) if t >= 9.0 else g.cam_state
        else:  # vurgu yoksa son animasyondan sonra sahne sonuna kadar çok yavaş yakınlaşma; eyalet yerinde kalır
            cam = maplib.cam_zoom(g.cam_state, g.state_center, 1 - DRIFT_ZOOM * seg(t, DRIFT_START, DRIFT_END))
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

    # testler ve hata ayıklama için kurulmuş parçalar
    update.geometry, update.layers, update.left_texts = g, m, left_texts
    return update


SCENE = Scene(id="state_map", title="Eyalet haritası", base_duration=13.0, params=PARAMS, setup=setup,
              bg_center=(0.6, 0.45))
