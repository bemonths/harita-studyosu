"""County soru kartı: solda county sınırı (turuncu, parıltılı), altında yer adı ve şehirler; sağda 1–3 satır. Her
satırın değeri açılış anına kadar "?" olarak durur. Açılışta `counter` sıfırdan değere sayar, `in10` on ev simgesinden
değer kadarı kırmızıya döner ve "N IN 10" yazar, `compare` ev biçimli sütun ikinci değerden (ör. zirve) birinci değere
gerçek oranla iner ve sağda farkı yazar. Açılış anı sahne süresinden büyükse satır soru olarak kalır (bölümün başında
yalnızca soruyu göstermek için). Bu sahnede başlık satırı (title) ve büyük rakam (callout) çizilmez.
update(t) içindeki t temel süre (9,5 sn) cinsindendir; satırların açılış anı (reveal) gerçek saniyedir."""
from matplotlib.patches import Polygon

from engine import brand
from engine.params import Choice, Number
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

BASE_DURATION = 9.5
RX, RW, RH, PITCH, MID = 860, 980, 250, 280, 545  # satır kartları: sol x, genişlik, yükseklik, aralık, blok ortası
KINDS = (("counter", "Sayaç"), ("in10", "10 evde N"), ("compare", "Karşılaştırma (sütun)"), ("none", "Satır yok"))
COL_W, COL_APEX = 80, 126  # karşılaştırma sütunlarının genişliği ve büyük değerin çatı tepesi (piksel)

DEFAULT_ROWS = [
    dict(kind="counter", label="HOMES FOR SALE", note="AUGUST 2026", value=9351, value2=None, value2_label="",
         value_label="", format="count", reveal=3.4),
    dict(kind="in10", label="SELLERS WHO CUT THEIR PRICE", note="AUGUST 2026", value=3, value2=None, value2_label="",
         value_label="", format="count", reveal=5.0),
    dict(kind="compare", label="WHAT BUYERS PAY", note="MAY 2026 SALES", value=360000, value2=415000,
         value2_label="2022 PEAK", value_label="TODAY", format="money_k", reveal=6.6),
]


def row_params():
    out = []
    for k, d in enumerate(DEFAULT_ROWS, 1):
        g = f"Satır {k}"
        out += [
            Choice(f"row{k}_kind", "Tür", default=d["kind"], options=KINDS, group=g),
            T(f"row{k}_label", "Başlık", d["label"], group=g, max_len=60),
            T(f"row{k}_note", "Not", d["note"], group=g, max_len=60, help="Sol altta küçük satır (ör. AUGUST 2026)."),
            Number(f"row{k}_value", "Değer", default=d["value"], group=g, lo=0,
                   help="in10'da 0–10 arası tam sayı."),
            Number(f"row{k}_value2", "Karşılaştırılan değer", default=d["value2"], group=g, lo=0, optional=True,
                   help="Yalnız compare: ör. zirve."),
            T(f"row{k}_value2_label", "Karşılaştırılanın etiketi", d["value2_label"], group=g, max_len=30),
            T(f"row{k}_value_label", "Değerin etiketi", d["value_label"], group=g, max_len=30),
            Choice(f"row{k}_format", "Biçim", default=d["format"], options=cl.FORMATS, group=g),
            Number(f"row{k}_decimals", "Ondalık basamak", default=0, group=g, lo=0, hi=1, integer=True,
                   help="Yalnız counter ve adet biçimi (ör. 6.2 ay)."),
            T(f"row{k}_prefix", "Önek", "", group=g, max_len=5, help="Yalnız counter: sayının önüne (ör. $94)."),
            Number(f"row{k}_reveal", "Açılış anı (sn)", default=d["reveal"], group=g, lo=0, step=0.1,
                   help="Sahne süresinden büyükse satır soru olarak kalır."),
        ]
    return out


PARAMS = cl.common_params(heading="LEE COUNTY", subtitle="CAPE CORAL  ·  FORT MYERS", fips="12071") + row_params()
PARAMS[0] = T("heading", "Yer adı", "LEE COUNTY", group="Başlık", help="County sınırının altında (Cinzel).")
PARAMS[2] = T("subtitle", "Şehirler", "CAPE CORAL  ·  FORT MYERS", group="Başlık", help="Yer adının altında.")


def rows(p):
    return [k for k in range(1, 4) if p[f"row{k}_kind"] != "none"]


def check(p):
    errors = cl.common_check(p)
    if not rows(p):
        errors["row1_kind"] = "En az bir satır olmalı."
    for k in rows(p):
        kind, v = p[f"row{k}_kind"], p[f"row{k}_value"]
        if kind == "in10" and (v != int(v) or not 0 <= v <= 10):
            errors[f"row{k}_value"] = "10 evde N için değer 0–10 arası tam sayı olmalı."
        if kind == "compare" and not p[f"row{k}_value2"]:
            errors[f"row{k}_value2"] = "Karşılaştırma için ikinci değer gerekli."
    return errors


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    gold = brand.category_color("price")
    to_base = BASE_DURATION / float(p["duration"])  # açılış anı gerçek saniye; t temel süre
    back = cv.backdrop()
    left = cl.Group().extend(cv.county(p["fips"], 440, 590, 440))
    if p["heading"]:
        cv.fit(left.add(cv.text(440, 260, p["heading"], 62, "place", C["text"])), 760)
    if p["subtitle"]:
        cv.fit(left.add(cv.text(440, 196, p["subtitle"], 27, "label", C["muted"])), 760)
    if p["source"]:
        left.add(cv.text(112, 58, p["source"], 20, "label", C["muted"], ha="left", stroke=False))

    ks = rows(p)
    n = len(ks)
    updaters = []
    for i, k in enumerate(ks):
        y = MID - RH / 2 + ((n - 1) / 2 - i) * PITCH
        kind, fmt = p[f"row{k}_kind"], p[f"row{k}_format"]
        v, v2 = p[f"row{k}_value"], p[f"row{k}_value2"]
        reveal = p[f"row{k}_reveal"] * to_base
        frame = cl.Group()
        frame.add(cv.card(RX, y, RW, RH), 0.92)
        cv.fit(frame.add(cv.text(RX + 40, y + RH - 42, p[f"row{k}_label"], 27, "label_bold", C["text"], ha="left")),
               RW - 80)
        frame.add(cv.text(RX + 40, y + 34, p[f"row{k}_note"], 19, "label", C["muted"], ha="left"))
        vx, vy = RX + RW - 50, y + 118
        appear = (0.4 + i * 0.25, 1.1 + i * 0.25)
        if kind == "counter":
            updaters.append(counter_row(cv, frame, y, vx, vy, v, fmt, reveal, appear,
                                        p[f"row{k}_decimals"], p[f"row{k}_prefix"]))
        elif kind == "in10":
            updaters.append(in10_row(cv, frame, y, vx, vy, int(v), reveal, appear))
        else:
            updaters.append(compare_row(cv, frame, y, vx, v, v2, fmt, reveal, appear, gold,
                                        p[f"row{k}_value_label"], p[f"row{k}_value2_label"]))

    def update(t):
        a = cl.grow(t, 0, 0.8)
        back.set_alpha(a)
        left.set_alpha(a)
        for u in updaters:
            u(t)

    update.parts = {"rows": ks, "updaters": updaters}
    return update


def counter_row(cv, frame, y, vx, vy, v, fmt, reveal, appear, decimals=0, prefix=""):
    C = cv.C
    icon_off = cv.house_icon(RX + 40, y + 72, 105, C["line"])
    icon_on = cv.house_icon(RX + 40, y + 72, 105, C["accent"])
    q = cv.qmark(vx - 60, vy, 120)
    num = cv.text(vx, vy, "", 120, "numbers", C["text"], ha="right")

    def show(x):
        return prefix + cl.fmt_value(x, fmt, decimals)

    cv.fit_widest(num, [show(v)], RW - 260)

    def upd(t):
        pa = cl.grow(t, *appear)
        frame.set_alpha(pa)
        shown = t >= reveal
        r = cl.grow(t, reveal, reveal + 1.0)
        icon_off.set_alpha(0 if shown else pa)
        icon_on.set_alpha(pa if shown else 0)
        q.update(t, 0 if shown else pa)
        num.set_text(show(v * r))
        num.set_alpha(pa if shown else 0)

    upd.question = q
    upd.value = num
    return upd


def in10_row(cv, frame, y, vx, vy, v, reveal, appear):
    C = cv.C
    iw, ig = 46, 14
    off = [cv.house_icon(RX + 40 + j * (iw + ig), y + 95, iw, C["line"], fill_alpha=0.25, window=False)
           for j in range(10)]
    on = [cv.house_icon(RX + 40 + j * (iw + ig), y + 95, iw, C["loss"], fill_alpha=0.55, window=False)
          for j in range(10)]
    ask = cv.rich("? IN 10", vx, vy, 60, C["muted"], 420, ha="right")
    ans = cv.text(vx, vy, f"{v} IN 10", 70, "numbers", C["loss"], ha="right")

    def upd(t):
        pa = cl.grow(t, *appear)
        frame.set_alpha(pa)
        shown = t >= reveal
        r = cl.grow(t, reveal, reveal + 1.0)
        lit = int(round(v * r + 0.0001)) if shown else 0
        for j in range(10):
            off[j].set_alpha(0 if j < lit else pa)
            on[j].set_alpha(pa if j < lit else 0)
        ask.update(t, 0 if shown else pa)
        ans.set_alpha(pa * min(1, r * 2) if shown else 0)

    upd.question = ask
    upd.value = ans
    return upd


def compare_row(cv, frame, y, vx, v, v2, fmt, reveal, appear, gold, value_label, value2_label):
    """İki ev biçimli sütun, sıfırdan ve gerçek oranla: büyük olan COL_APEX yüksekliğinde."""
    C = cv.C
    base = y + 62
    scale = COL_APEX / max(v, v2)
    h2, h1 = v2 * scale, v * scale
    color = C["loss"] if v < v2 else C["accent"]
    ref = cv.house_bar(RX + 40, base, COL_W, gold, fill=0.35)
    ref.set_height(h2)
    frame.add(cv.text(RX + 145, y + 140, cl.fmt_value(v2, fmt), 58, "numbers", gold, ha="left"))
    if value2_label:
        frame.add(cv.text(RX + 147, y + 80, value2_label, 20, "label", C["muted"], ha="left"))
    bx = RX + 390
    placeholder = cl.Group([(cv.ax.add_patch(Polygon(cl.house_path(bx, base, COL_W, h2), closed=True, fc="none",
                                                       ec=C["line"], lw=2.5, ls=(0, (6, 5)), zorder=7)), 1.0)])
    q1, q2 = cv.qmark(bx + COL_W / 2, base + 50, 70), cv.qmark(bx + 160, y + 135, 90)
    col = cv.house_bar(bx, base, COL_W, color)
    cur_txt = cv.text(bx + 105, y + 140, "", 58, "numbers", color, ha="left")
    cv.fit_widest(cur_txt, [cl.fmt_value(max(v, v2), fmt)], vx - 150 - (bx + 105))
    cur_lab = cv.text(bx + 107, y + 80, value_label, 20, "label", C["muted"], ha="left")
    diff = cv.text(vx, y + 140, cl.signed(v - v2, fmt), 58, "numbers", color, ha="right")

    def upd(t):
        pa = cl.grow(t, *appear)
        frame.set_alpha(pa)
        ref.set_alpha(pa)
        shown = t >= reveal
        r = cl.grow(t, reveal, reveal + 1.0)
        placeholder.set_alpha(0 if shown else pa)
        q1.update(t, 0 if shown else pa)
        q2.update(t, 0 if shown else pa)
        col.set_height(h2 + (h1 - h2) * r)
        col.set_alpha(pa if shown else 0)
        cur_txt.set_text(cl.fmt_value(v2 + (v - v2) * r, fmt))
        cur_txt.set_alpha(pa if shown else 0)
        cur_lab.set_alpha(pa if shown and value_label else 0)
        diff.set_alpha(pa * cl.grow(t, reveal + 0.6, reveal + 1.1) if shown else 0)

    upd.question = q2
    upd.value = cur_txt
    upd.bars = (ref, col)
    return upd


SCENE = Scene(id="county_quiz", title="County soru kartı", base_duration=BASE_DURATION, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
