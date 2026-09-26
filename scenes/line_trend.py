"""Çizgi ve ok: iniş çıkışlı bir çizgi soldan sağa çizilir, ucunda ok başı, geçtiği noktalarda nokta. İsteğe bağlı
kesikli referans çizgisi (ör. 2019 düzeyi), en düşük noktanın değeri ve sonda son değer büyük yazıyla. Eksen sıfırdan
başlar; başlamıyorsa eksenin başladığı değer ekranda yazar. update(t) içindeki t temel süre (7 sn) cinsindendir."""
import numpy as np
from matplotlib.patches import Circle

from engine import brand
from engine.params import Choice, Number, ValueTable
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

X0, X1, Y0, Y1 = 190, 1560, 170, 740  # çizim alanı (1080p piksel)
DRAW = (0.7, 4.2)  # çizginin çizildiği aralık (temel süre, sn)
YES_NO = (("yes", "Evet"), ("no", "Hayır"))

OSCEOLA = [2445, 2380, 1991, 2075, 2278, 816, 1992, 2316, 3801, 4282, 4135]

PARAMS = cl.common_params(heading="OSCEOLA COUNTY", title="HOMES FOR SALE",
                          subtitle="EVERY AUGUST  ·  KISSIMMEE  ·  ST. CLOUD", source="SOURCE: REALTOR.COM VIA FRED",
                          callout_value="2×", callout_label="THE 2019 LEVEL", fips="12097",
                          callout_color=brand.color("accent")) + [
    ValueTable("points", "Noktalar", group="Veri", min_rows=3, max_rows=15, lo=0,
               default=[{"label": str(2016 + i), "value": v, "highlight": False} for i, v in enumerate(OSCEOLA)],
               help="Etiket genelde yıldır; hepsi yılsa aradakiler kısaltılır (2016, 17, 18 … 2026)."),
    Choice("value_format", "Değer biçimi", default="count", options=cl.FORMATS, group="Veri"),
    Number("ref_value", "Referans değeri", default=2075, group="Referans", lo=0, optional=True,
           help="Kesikli yatay çizgi; boşsa çizilmez."),
    T("ref_label", "Referans etiketi", "2019 LEVEL: 2,075", group="Referans"),
    Choice("mark_min", "En düşük noktayı yaz", default="yes", options=YES_NO, group="Veri"),
    Choice("axis_from_zero", "Eksen sıfırdan başlasın", default="yes", options=YES_NO, group="Veri",
           help="Hayır seçilirse eksenin başladığı değer ekranda yazar."),
]


def check(p):
    return cl.common_check(p)


def nice_floor(v, span):
    """v'nin altındaki yuvarlak değer (1-2-5 x 10^k adımıyla)."""
    if span <= 0:
        return max(v, 0)
    step = 10 ** np.floor(np.log10(span / 4))
    for m in (1, 2, 5, 10):
        if span / (m * step) <= 5:
            step *= m
            break
    return max(np.floor(v / step) * step, 0)


def axis(values, ref, from_zero):
    vals = list(values) + ([ref] if ref is not None else [])
    hi = max(vals) * 1.05 or 1
    if from_zero:
        return 0.0, hi
    lo_v = min(vals)
    return nice_floor(lo_v - 0.1 * (hi - lo_v), hi - lo_v), hi


def x_labels(labels):
    """Hepsi dört haneli yılsa ve 6'dan fazlaysa ilk ve son dışındakiler iki haneye kısalır."""
    if len(labels) > 6 and all(len(s) == 4 and s.isdigit() for s in labels):
        return [s if i in (0, len(labels) - 1) else s[2:] for i, s in enumerate(labels)]
    return labels


def ref_label_side(xs, ys, ly, x_from, x_to):
    """Referans etiketinin konacağı taraf (+1 üst, -1 alt): etiketin x aralığında çizgiden uzak olan taraf."""
    grid = np.linspace(x_from, x_to, 24)
    line = np.interp(grid, xs, ys)
    above, below = np.max(line) - ly, ly - np.min(line)
    if np.min(line) > ly + 10:
        return -1  # çizgi referansın üstünde: etiket altta
    if np.max(line) < ly - 10:
        return 1
    return -1 if above > below else 1


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    pts = p["points"]
    vals = np.array([r["value"] for r in pts], float)
    n = len(vals)
    lo, hi = axis(vals, p["ref_value"], p["axis_from_zero"] == "yes")
    xs = np.array([X0 + (X1 - X0) * i / (n - 1) for i in range(n)])
    ys = Y0 + (Y1 - Y0) * (vals - lo) / (hi - lo)
    back, head, call = cv.backdrop(), cv.header(), cv.callout()
    fixed = cl.Group()
    fixed.add(cv.ax.plot([X0 - 30, X1 + 60], [Y0, Y0], color=C["line"], lw=2, zorder=3)[0])
    spacing = (X1 - X0) / (n - 1)
    for x, s in zip(xs, x_labels([r["label"] for r in pts])):
        cv.fit(fixed.add(cv.text(x, Y0 - 36, s, 24, "label", C["muted"])), spacing * 0.95)
    if p["axis_from_zero"] == "no":
        fixed.add(cv.text(X0 - 30, Y0 + 16, f"AXIS STARTS AT {cl.fmt_value(lo, p['value_format'])}", 18, "label",
                          C["muted"], ha="left", va="bottom"))
    if p["ref_value"] is not None:
        ly = Y0 + (Y1 - Y0) * (p["ref_value"] - lo) / (hi - lo)
        fixed.add(cv.ax.plot([X0 - 30, X1 + 60], [ly, ly], color=C["muted"], lw=2, ls=(0, (8, 7)), zorder=4)[0], 0.7)
        if p["ref_label"]:
            w = cv.width(p["ref_label"], 24, "label")
            side = ref_label_side(xs, ys, ly, X1 + 60 - w, X1 + 60)
            fixed.add(cv.text(X1 + 60, ly + 30 * side, p["ref_label"], 24, "label", C["muted"], ha="right"))

    arrow = cv.arrow(np.column_stack([xs, ys]), C["accent"], lw=6)
    seg_len = np.hypot(np.diff(xs), np.diff(ys))
    at = np.concatenate([[0], np.cumsum(seg_len)]) / seg_len.sum()  # noktaların çizgi boyundaki yeri (0–1)
    dots = [cv.ax.add_patch(Circle((x, y), 9, fc=C["accent"], ec=C["bg_dark"], lw=3, zorder=17, alpha=0))
            for x, y in zip(xs[:-1], ys[:-1])]
    imin = int(np.argmin(vals))
    min_txt = None
    if p["mark_min"] == "yes" and imin < n - 1:
        min_txt = cv.text(xs[imin], ys[imin] - 44, cl.fmt_value(vals[imin], p["value_format"]), 32, "numbers",
                          C["muted"])
    last_txt = cv.text(xs[-1] + 20, min(ys[-1] + 95, 800), cl.fmt_value(vals[-1], p["value_format"]), 80, "numbers",
                       C["text"], ha="right")

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        fixed.set_alpha(a)
        prog = cl.grow(t, *DRAW)
        arrow.set(prog, a)
        for i, d in enumerate(dots):
            d.set_alpha(a if prog > 0 and prog >= at[i] - 1e-9 else 0)
        if min_txt is not None:
            min_txt.set_alpha(min(1, max(0, (prog - at[imin]) * 8)) * a if prog > 0 else 0)
        b = cl.grow(t, 4.3, 4.9)
        last_txt.set_alpha(b)
        call.set_alpha(b)

    update.parts = {"xs": xs, "ys": ys, "axis": (lo, hi), "arrow": arrow, "dots": dots}
    return update


SCENE = Scene(id="line_trend", title="Çizgi ve ok", base_duration=7.0, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
