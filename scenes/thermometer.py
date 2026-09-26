"""Termometre: 1–3 tüp sırayla dolar, değer tüpün yanında sayar. İki eşik (alt ve üst) kesikli yatay çizgiyle ve
sağdaki etiketiyle gösterilir; üst eşiği aşan tüp kırmızı, diğerleri nötr. Dolum boyu değerle orantılıdır (sıfırdan).
update(t) içindeki t temel süre (6,5 sn) cinsindendir."""
from matplotlib.patches import FancyBboxPatch

from engine.params import Number, ValueTable
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

BASE, TOP, TUBE_W, INSET = 170, 760, 120, 14  # tüpün tabanı, tepesi, genişliği ve iç boşluğu (1080p piksel)
MID_X, SPACING = 835, 390  # tüp grubunun ortası ve tüpler arası

PARAMS = cl.common_params(heading="HIGHLANDS COUNTY", title="HOW LONG TO SELL EVERY HOME FOR SALE",
                          subtitle="IF NO NEW HOME WERE LISTED  ·  MAY 2026", source="SOURCE: REDFIN",
                          fips="12055") + [
    ValueTable("tubes", "Tüpler", group="Veri", min_rows=1, max_rows=3, lo=0,
               default=[{"label": "HIGHLANDS", "value": 6.2, "highlight": False},
                        {"label": "FLORIDA", "value": 4.7, "highlight": False}]),
    Number("max_value", "Tüpün tam boyu", default=8, group="Veri", lo=0.001),
    T("unit_label", "Birim", "MONTHS", group="Veri"),
    Number("decimals", "Ondalık basamak", default=1, group="Veri", lo=0, hi=1, integer=True),
    Number("low_value", "Alt eşik", default=3, group="Eşikler", lo=0, optional=True),
    T("low_label", "Alt eşik etiketi", "SELLER'S MARKET: UNDER 3", group="Eşikler"),
    Number("high_value", "Üst eşik", default=6, group="Eşikler", lo=0, optional=True,
           help="Bu değeri aşan tüp kırmızı dolar."),
    T("high_label", "Üst eşik etiketi", "BUYER'S MARKET: OVER 6", group="Eşikler"),
]


def check(p):
    errors = cl.common_check(p)
    over = [r["label"] for r in p["tubes"] if r["value"] > p["max_value"]]
    if over:
        errors["max_value"] = f"Tüpün tam boyu en büyük değerden küçük olamaz ({over[0]})."
    for key in ("low_value", "high_value"):
        if p[key] is not None and p[key] > p["max_value"]:
            errors[key] = "Eşik tüpün tam boyundan büyük olamaz."
    if p["low_value"] is not None and p["high_value"] is not None and p["low_value"] >= p["high_value"]:
        errors["high_value"] = "Üst eşik alt eşikten büyük olmalı."
    return errors


def inner_h(m, vmax):
    return (TOP - BASE - 2 * INSET) * m / vmax


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    tubes, vmax, dec = p["tubes"], p["max_value"], p["decimals"]
    n = len(tubes)
    xs = [MID_X + (i - (n - 1) / 2) * SPACING for i in range(n)]
    back, head, call = cv.backdrop(), cv.header(), cv.callout()
    fixed = cl.Group()

    def yv(m):
        return BASE + INSET + inner_h(m, vmax)

    x_left, x_right = xs[0] - 160, xs[-1] + 300
    for key, lab_key, color, lab_color in (("low_value", "low_label", C["neutral"], C["muted"]),
                                           ("high_value", "high_label", C["loss"], C["loss"])):
        if p[key] is None:
            continue
        fixed.add(cv.ax.plot([x_left, x_right], [yv(p[key])] * 2, color=color, lw=2.5, ls=(0, (8, 7)), zorder=3)[0], 0.8)
        if p[lab_key]:
            t_ = fixed.add(cv.text(x_right + 20, yv(p[key]), p[lab_key], 24, "label_bold", lab_color, ha="left"))
            cv.fit(t_, cl.W - 50 - (x_right + 20))  # etiket kadrajın içinde kalır
    fills, values, units = [], [], []
    for i, (r, x) in enumerate(zip(tubes, xs)):
        fixed.add(cv.ax.add_patch(FancyBboxPatch((x - TUBE_W / 2, BASE), TUBE_W, TOP - BASE,
                                                 boxstyle=f"round,pad=0,rounding_size={TUBE_W / 2}", fc=C["surface"],
                                                 ec=C["line"], lw=3, zorder=4)))
        hot = p["high_value"] is not None and r["value"] > p["high_value"]
        fills.append(cv.rounded_vbar(x - TUBE_W / 2 + INSET, BASE + INSET, TUBE_W - 2 * INSET,
                                     C["loss"] if hot else C["neutral"], z=5))
        lab = fixed.add(cv.text(x, BASE - 40, r["label"], 30, "label_bold", C["text"]))
        cv.fit(lab, SPACING - 30)
        vt = cv.text(x + TUBE_W / 2 + 24, BASE, "", 64, "numbers", C["text"], ha="left")
        cv.fit_widest(vt, [f"{vmax:,.{dec}f}"], SPACING - TUBE_W - 40)
        values.append(vt)
        units.append(cv.text(x + TUBE_W / 2 + 26, BASE, p["unit_label"], 22, "label_bold", C["muted"], ha="left"))

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        fixed.set_alpha(a)
        for i, (r, x) in enumerate(zip(tubes, xs)):
            g = cl.grow(t, 0.8 + i * 0.8, 2.6 + i * 0.8)
            hh = inner_h(r["value"], vmax) * g
            cl.set_vbar_height(fills[i], hh)
            fills[i].set_alpha(0.95 * a)
            top = BASE + INSET + hh
            values[i].set_text(f"{r['value'] * g:,.{dec}f}")
            values[i].set_y(top)
            values[i].set_alpha(a * min(1, g * 3))
            units[i].set_y(top - 52)
            units[i].set_alpha(a if g > 0.95 and p["unit_label"] else 0)
        call.set_alpha(cl.grow(t, 3.6, 4.1))

    update.parts = {"fills": fills, "values": [r["value"] for r in tubes], "max_value": vmax}
    return update


SCENE = Scene(id="thermometer", title="Termometre", base_duration=6.5, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
