"""Halka: halka saat 12 yönünden saat yönünde dolar, ortadaki sayı sayar. Dolum bitince kalan dilim kırmızı yanar,
yanında kalan miktar ("$6 OFF") ve kısa açıklama belirir. Dolum açısı değerle orantılıdır.
update(t) içindeki t temel süre (6 sn) cinsindendir."""
from matplotlib.patches import Wedge

from engine.params import Number
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

CX, CY, R, RING_W = cl.W / 2, 470, 300, 56

PARAMS = cl.common_params(heading="COLLIER COUNTY", title="WHAT BUYERS REALLY PAY",
                          subtitle="NAPLES  ·  MAY 2026 SALES", source="SOURCE: REDFIN", fips="12021") + [
    Number("value", "Değer", default=94.3, group="Veri", lo=0),
    Number("max_value", "Tam halkanın değeri", default=100, group="Veri", lo=0.001),
    T("center_prefix", "Sayının öneki", "$", group="Veri", help="ör. $"),
    T("center_label", "Sayının alt satırı", "OF EVERY $100 ASKED", group="Veri"),
    T("remainder_value", "Kalan yazısı", "", auto=True, group="Veri", help="Boşsa '$6 OFF' gibi kendiliğinden yazılır."),
    T("remainder_label", "Kalanın alt satırı", "AT THE TABLE", group="Veri"),
]


def check(p):
    errors = cl.common_check(p)
    if p["value"] > p["max_value"]:
        errors["value"] = "Değer tam halkanın değerinden büyük olamaz."
    return errors


def auto_remainder(p):
    return f"{p['center_prefix']}{cl.fmt_value(p['max_value'] - p['value'], 'count')} OFF"


def angle(v, vmax):
    """Saat 12'den saat yönünde, v/vmax oranında dolmuş dilimin başlangıç açısı (derece, matplotlib)."""
    return 90 - 360 * v / vmax


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    v, vmax, prefix = p["value"], p["max_value"], p["center_prefix"]
    back, head, call = cv.backdrop(), cv.header(), cv.callout()
    track = cv.ax.add_patch(Wedge((CX, CY), R, 0, 360, width=RING_W, fc=C["line"], zorder=4, alpha=0))
    fill = cv.ax.add_patch(Wedge((CX, CY), R, 90, 90, width=RING_W, fc=C["accent"], zorder=5, alpha=0))
    rest = cv.ax.add_patch(Wedge((CX, CY), R + 14, angle(vmax, vmax), angle(v, vmax), width=RING_W + 28,
                                 fc=C["loss"], zorder=5, alpha=0))
    has_rest = vmax - v > 0
    num = cv.text(CX, CY + 30, "", 190, "numbers", C["text"])
    cv.fit_widest(num, [prefix + cl.fmt_value(vmax, "count")], 2 * (R - RING_W) - 40)
    lab = cv.text(CX, CY - 110, p["center_label"], 30, "label_bold", C["muted"])
    cv.fit(lab, 2 * (R - RING_W) - 30)
    side = cl.Group()
    if has_rest:
        side.add(cv.text(CX + R + 70, CY + R - 30, p["remainder_value"] or auto_remainder(p), 64, "numbers", C["loss"],
                         ha="left"))
        if p["remainder_label"]:
            side.add(cv.text(CX + R + 72, CY + R - 90, p["remainder_label"], 26, "label_bold", C["text"], ha="left"))
        for t_ in side.artists():
            cv.fit(t_, cl.W - 50 - (CX + R + 70))

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        track.set_alpha(0.6 * a)
        g = cl.grow(t, 0.8, 3.0)
        cur = v * g
        fill.set_theta1(angle(cur, vmax))
        fill.set_visible(cur > 0)
        fill.set_alpha(a)
        num.set_text(prefix + cl.fmt_value(cur, "count"))
        num.set_alpha(a)
        lab.set_alpha(a)
        rest.set_alpha(a * cl.grow(t, 3.1, 3.6))
        rest.set_visible(has_rest)
        side.set_alpha(cl.grow(t, 3.4, 3.9))
        call.set_alpha(cl.grow(t, 3.4, 3.9))

    update.parts = {"fill": fill, "value": v, "max_value": vmax}
    return update


SCENE = Scene(id="ring", title="Halka", base_duration=6.0, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
