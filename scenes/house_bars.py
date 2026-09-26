"""Ev sütunları: ev biçimli sütunlar soldan sağa büyür, üstlerinde değer, altlarında etiket (genelde yıl). İşaretli
satır vurgulanır; ondan öncekiler nötr, sonrakiler ayrı renkte. İki sütun arasında, değer yazılarının üstünden geçen
bir ok çizilebilir; ok bitince sağ üstteki büyük rakam belirir. Sütunlar sıfırdan başlar, boyları (çatı tepesine kadar)
değerle orantılıdır. update(t) içindeki t temel süre (7 sn) cinsindendir."""
from engine import brand
from engine.params import Choice, Color, ValueTable
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

BASE, APEX_MAX = 170, 490  # sütun tabanı ve en büyük değerin çatı tepesi (1080p piksel, tabandan)
ARROW_LIFT, LABEL_LIFT = 110, 36  # okun ve değer yazısının çatı tepesinden yüksekliği

LEE = [("2019", 243000), ("2020", 243000), ("2021", 319000), ("2022", 419000), ("2023", 411000),
       ("2024", 399000), ("2025", 368000), ("2026", 360000)]

PARAMS = cl.common_params(heading="LEE COUNTY", title="WHAT A TYPICAL HOME SOLD FOR",
                          subtitle="MEDIAN SALE PRICE  ·  MAY OF EACH YEAR", source="SOURCE: REDFIN",
                          callout_value="−$59K", callout_label="SINCE MAY 2022", fips="12071") + [
    ValueTable("bars", "Sütunlar", group="Veri", min_rows=2, max_rows=10, lo=0,
               default=[{"label": y, "value": v, "highlight": y == "2022"} for y, v in LEE],
               help="Etiket genelde yıldır. İşaretli satır vurgulanır (ör. zirve ya da dip)."),
    Choice("value_format", "Değer biçimi", default="money_k", options=cl.FORMATS, group="Veri"),
    T("arrow_from", "Ok başı (satır etiketi)", "2022", group="Ok", help="Boş bırakılırsa ok çizilmez."),
    T("arrow_to", "Ok ucu (satır etiketi)", "2026", group="Ok"),
    Color("arrow_color", "Ok rengi", default=brand.color("loss"), group="Ok"),
    Color("highlight_color", "İşaretli sütunun rengi", default=brand.category_color("price"), group="Renkler"),
    Color("after_color", "Sonraki sütunların rengi", default=brand.color("loss"), group="Renkler"),
]


def check(p):
    errors = cl.common_check(p)
    labels = [r["label"] for r in p["bars"]]
    a, b = p["arrow_from"].strip(), p["arrow_to"].strip()
    if a or b:
        if a not in labels:
            errors["arrow_from"] = "Sütun etiketlerinden biri olmalı (ya da ok için ikisi de boş)."
        elif b not in labels:
            errors["arrow_to"] = "Sütun etiketlerinden biri olmalı (ya da ok için ikisi de boş)."
        elif labels.index(a) >= labels.index(b):
            errors["arrow_to"] = "Okun ucu başından sonraki bir sütun olmalı."
    return errors


def colors(p, C):
    """İşaretli satırdan öncekiler nötr, işaretliler vurgu rengi, sonrakiler after_color. İşaret yoksa hepsi nötr,
    sonuncu accent."""
    rows = p["bars"]
    marked = [i for i, r in enumerate(rows) if r["highlight"]]
    if not marked:
        return [C["neutral"]] * (len(rows) - 1) + [C["accent"]]
    first = marked[0]
    return [p["highlight_color"] if r["highlight"] else (C["neutral"] if i < first else p["after_color"])
            for i, r in enumerate(rows)]


def layout(n):
    """Sütun genişliği, aralık ve ilk sütunun x'i: 8 sütunda prototipteki 128/66 px."""
    bw = min(160.0, 1486 / (n + (n - 1) * 66 / 128))
    gap = bw * 66 / 128
    return bw, gap, (cl.W - (n * bw + (n - 1) * gap)) / 2


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    rows = p["bars"]
    n = len(rows)
    vals = [r["value"] for r in rows]
    vmax = max(vals) or 1
    bw, gap, x0 = layout(n)
    cols = colors(p, C)
    back, head = cv.backdrop(), cv.header()
    bars, value_txt, labels = [], [], cl.Group()
    tops = []
    for i, (r, col) in enumerate(zip(rows, cols)):
        x = x0 + i * (bw + gap)
        bar = cv.house_bar(x, BASE, bw, col)
        bars.append(bar)
        apex = BASE + APEX_MAX * r["value"] / vmax
        tops.append((x + bw / 2, apex))
        labels.add(cv.text(x + bw / 2, BASE - 38, r["label"], 26, "label", C["muted"]))
        vt = cv.text(x + bw / 2, apex + LABEL_LIFT, cl.fmt_value(r["value"], p["value_format"]), 36, "numbers", C["text"])
        cv.fit(vt, bw + gap * 0.9)
        value_txt.append(vt)
    for vt in value_txt:  # sütun sayısı çoksa hepsi aynı (en küçük) boyutta
        vt.set_fontsize(min(v.get_fontsize() for v in value_txt))

    label_list = [r["label"] for r in rows]
    arrow = None
    last_end = 1.1 + (n - 1) * 0.3
    a0 = max(3.4, last_end + 0.2)
    if p["arrow_from"] and p["arrow_to"]:
        i0, i1 = label_list.index(p["arrow_from"]), label_list.index(p["arrow_to"])
        arrow = cv.arrow([(x, y + ARROW_LIFT) for x, y in tops[i0:i1 + 1]], p["arrow_color"])
        call_at = a0 + 1.1
    else:
        call_at = last_end + 0.3
    call = cv.callout()

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        labels.set_alpha(a)
        for i, (bar, vt) in enumerate(zip(bars, value_txt)):
            g = cl.grow(t, 0.5 + i * 0.3, 1.1 + i * 0.3)
            bar.set_height(APEX_MAX * vals[i] / vmax * g)
            bar.set_alpha(a if g > 0 else 0)
            vt.set_alpha(min(1, (g - 0.95) * 20) if g > 0.95 else 0)
        if arrow:
            arrow.set(cl.grow(t, a0, a0 + 1.0), a)
        call.set_alpha(cl.grow(t, call_at, call_at + 0.5))

    update.parts = {"bars": bars, "values": vals, "scale": APEX_MAX / vmax, "arrow": arrow, "value_text": value_txt}
    return update


SCENE = Scene(id="house_bars", title="Ev sütunları", base_duration=7.0, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
