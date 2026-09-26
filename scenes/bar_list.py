"""Çubuk listesi: yatay ilerleme çubukları sırayla büyür, değer çubuğun ucunda yazar. 2–4 satırda büyük yerleşim,
5–10 satırda sıkı yerleşim. İşaretli satırlar vurgu renginde, eşiği aşanlar kırmızı, diğerleri nötr; eşik varsa kesikli
dikey çizgi ve etiketi. Çubukların arkasında soluk tam boy iz vardır. Çubuk boyu değerle orantılıdır (sıfırdan).
update(t) içindeki t temel süre (6,5 sn) cinsindendir."""
from engine.params import Number, ValueTable
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

BIG_MAX_ROWS = 4
# (sol x, tam boy, çubuk kalınlığı, satır aralığı, etiket boyu, değer boyu, etiket boşluğu, değer boşluğu)
BIG = (560, 1000, 74, 190, 34, 50, 40, 30)
TIGHT = (520, 1150, 40, 64, 28, 36, 30, 20)
MID_Y = 467  # satır bloğunun dikey ortası

PARAMS = cl.common_params(heading="PASCO COUNTY", title="SELLERS WHO CUT THEIR PRICE",
                          subtitle="OUT OF EVERY 100 HOMES FOR SALE  ·  AUGUST 2026",
                          source="SOURCE: REALTOR.COM VIA FRED", fips="12101") + [
    ValueTable("rows", "Çubuklar", group="Veri", min_rows=2, max_rows=10, lo=0,
               default=[{"label": "PASCO COUNTY", "value": 44, "highlight": True},
                        {"label": "FLORIDA", "value": 31, "highlight": False},
                        {"label": "UNITED STATES", "value": 35, "highlight": False}],
               help="İşaretli satırlar vurgu renginde çizilir."),
    Number("max_value", "Tam boyun değeri", default=100, group="Veri", lo=0.001),
    T("value_suffix", "Değer eki", " OF 100", group="Veri", help="Değerin arkasına eklenir; boş olabilir."),
    Number("decimals", "Ondalık basamak", default=0, group="Veri", lo=0, hi=1, integer=True),
    Number("threshold", "Eşik", default=None, group="Eşik", lo=0, optional=True,
           help="Bu değeri aşan satırlar kırmızı; kesikli dikey çizgiyle gösterilir."),
    T("threshold_label", "Eşik etiketi", "", group="Eşik", help="ör. BUYER'S MARKET: 6+ MONTHS"),
]


def check(p):
    errors = cl.common_check(p)
    over = [r["label"] for r in p["rows"] if r["value"] > p["max_value"]]
    if over:
        errors["max_value"] = f"Tam boyun değeri en büyük satırdan küçük olamaz ({over[0]})."
    elif p["threshold"] is not None and p["threshold"] > p["max_value"]:
        errors["threshold"] = "Eşik tam boyun değerinden büyük olamaz."
    return errors


def row_color(r, p, C):
    if r["highlight"]:
        return C["accent"]
    if p["threshold"] is not None and r["value"] > p["threshold"]:
        return C["loss"]
    return C["neutral"]


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    rows = p["rows"]
    n = len(rows)
    big = n <= BIG_MAX_ROWS
    x0, wmax, bh, pitch, lab_size, val_size, lab_gap, val_gap = BIG if big else TIGHT
    vmax, dec, suffix = p["max_value"], p["decimals"], p["value_suffix"]
    any_marked = any(r["highlight"] for r in rows)
    back, head = cv.backdrop(), cv.header()
    fixed = cl.Group()
    bars, value_txt, ys = [], [], []
    for i, r in enumerate(rows):
        yc = MID_Y + ((n - 1) / 2 - i) * pitch
        y = yc - bh / 2
        ys.append(yc)
        strong = not big or r["highlight"] or not any_marked
        lab = fixed.add(cv.text(x0 - lab_gap, yc, r["label"], lab_size, "label_bold", C["text"] if strong else C["muted"],
                                ha="right"))
        cv.fit(lab, x0 - lab_gap - 100)
        fixed.add(cv.rounded_bar(x0, y, wmax, bh, C["line"], z=4), 0.55)
        bars.append(cv.rounded_bar(x0, y, 0, bh, row_color(r, p, C), z=6))
        vt = cv.text(x0 + wmax * r["value"] / vmax + val_gap, yc, "", val_size, "numbers", C["text"], ha="left")
        cv.fit_widest(vt, [cl.fmt_value(r["value"], "count", dec) + suffix], cl.W - 40 - (x0 + wmax * r["value"] / vmax + val_gap))
        value_txt.append(vt)
    if p["threshold"] is not None:
        xt = x0 + wmax * p["threshold"] / vmax
        top = ys[0] + pitch * (0.5 if big else 0.95)
        # iz çubuklarının üstünde, renkli çubukların altında
        fixed.add(cv.ax.plot([xt, xt], [ys[-1] - bh / 2 - 30, top], color=C["loss"], lw=2.5, ls=(0, (8, 7)),
                             zorder=5)[0], 0.8)
        if p["threshold_label"]:
            tl = fixed.add(cv.text(xt + 14, top + 10, p["threshold_label"], 22, "label_bold", C["loss"], ha="left"))
            if xt + 14 + cv.width(p["threshold_label"], 22, "label_bold") > cl.W - 60:
                tl.set_ha("right")
                tl.set_x(xt - 14)
    widths = [wmax * r["value"] / vmax for r in rows]

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        fixed.set_alpha(a)
        for i, (r, bar, vt) in enumerate(zip(rows, bars, value_txt)):
            g = cl.grow(t, 0.7 + i * 0.6, 1.9 + i * 0.6) if big else cl.grow(t, 0.6 + i * 0.18, 1.6 + i * 0.18)
            cl.set_bar_width(bar, widths[i] * g)
            bar.set_alpha(0.95 * a)
            vt.set_text(cl.fmt_value(r["value"] * g, "count", dec) + suffix)   # yarımlar yukarı: 30,5 → "31"
            vt.set_alpha(min(1, (g - 0.9) * 10) if g > 0.9 else 0)

    update.parts = {"bars": bars, "widths": widths, "values": [r["value"] for r in rows], "wmax": wmax, "max_value": vmax,
                    "value_text": value_txt}
    return update


SCENE = Scene(id="bar_list", title="Çubuk listesi", base_duration=6.5, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
