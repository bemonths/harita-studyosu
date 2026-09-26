"""Ev ızgarası: önce "önce" değeri kadar ev simgesi belirir (her simge `unit` ev), sağ üstteki sayaç bu değeri
gösterir. Sonra fark kadar simge teker teker söner (azalışta kırmızı yanıp sönükleşir) ya da eklenir (artışta vurgu
renginde); sayaç "sonra" değerine iner ya da çıkar. Sonda sonuç yazısı. Alt yazıda birim açıkça yazar
("EACH HOUSE = 100 HOMES"). Sağ üst köşe sayaca ayrıldığı için bu sahnede büyük rakam (callout) çizilmez.
update(t) içindeki t temel süre (7,5 sn) cinsindendir."""
import math
import re

from engine.params import Number
from engine.scene import Scene, round_half_up
from scenes import chartlib as cl
from scenes.chartlib import T

UNITS = (10, 25, 50, 100, 200, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000)
MAX_ICONS, HARD_MAX = 48, 60
COLS = 12
X0, BOTTOM_BASE, TOP_BASE_MAX = 170, 272, 640  # ilk sütunun x'i; alt satırın tabanı; üst satırın tabanı en fazla
IW, GX, GY = 88, 34, 60  # prototipteki simge genişliği, yatay ve dikey aralık
CHANGE_AT, CHANGE_WINDOW, STEP_MAX, FADE = 2.4, 2.5, 0.28, 0.35
YEAR_RE = re.compile(r"^(.*?)(\d{4})$")

PARAMS = cl.common_params(heading="CHARLOTTE COUNTY", title="HOMES FOR SALE",
                          subtitle="PUNTA GORDA  ·  PORT CHARLOTTE",
                          source="SOURCE: REALTOR.COM VIA FRED  ·  AUGUST 2025 AND AUGUST 2026", fips="12015") + [
    Number("before", "Önce", default=3625, group="Veri", lo=0, integer=True),
    Number("after", "Sonra", default=2705, group="Veri", lo=0, integer=True),
    Number("unit", "Bir simge kaç ev", default=None, group="Veri", lo=1, integer=True, optional=True,
           help="Boşsa 10/25/50/100/200/500… serisinden simge sayısını 20–48 arasında tutan en küçük değer."),
    T("before_label", "Önceki dönem", "AUGUST 2025", group="Veri"),
    T("after_label", "Sonraki dönem", "AUGUST 2026", group="Veri"),
    T("result_text", "Sonuç yazısı", "", auto=True, group="Veri",
      help="Boşsa '920 FEWER HOMES FOR SALE IN ONE YEAR' gibi kendiliğinden yazılır."),
]


def auto_unit(before, after):
    """Simge sayısını 48'in altında tutan en küçük birim. Seri büyüdükçe simge azaldığı için bu, 20–48 aralığına
    düşen en küçük birimdir; değerler küçükse (en küçük birimle bile 20'den az simge) en küçük birim kalır."""
    top = max(before, after)
    return next((u for u in UNITS if top / u <= MAX_ICONS), UNITS[-1])


def unit_of(p):
    return p["unit"] or auto_unit(p["before"], p["after"])


def check(p):
    errors = cl.common_check(p)
    if max(p["before"], p["after"]) / unit_of(p) > HARD_MAX:
        errors["unit"] = f"En fazla {HARD_MAX} simge çizilir; bir simgenin temsil ettiği ev sayısını büyütün."
    return errors


def auto_result(p):
    d = p["after"] - p["before"]
    word = "FEWER" if d < 0 else "MORE"
    text = f"{abs(d):,} {word} HOMES FOR SALE"
    a, b = YEAR_RE.match(p["before_label"].strip()), YEAR_RE.match(p["after_label"].strip())
    if a and b and a.group(1) == b.group(1) and int(b.group(2)) - int(a.group(2)) == 1:
        text += " IN ONE YEAR"
    return text


def grid(n):
    """Simgelerin taban noktaları (satır satır, soldan sağa) ve simge genişliği. Üç satırdan fazlası küçülür."""
    cols = min(COLS, max(n, 1))
    rows = max(math.ceil(n / COLS), 1)
    pitch = IW * 1.04 + GY
    if rows > 1:
        pitch = min(pitch, (TOP_BASE_MAX - BOTTOM_BASE) / (rows - 1))
    iw = min(IW, (pitch - 40) / 1.04) if rows > 1 else IW
    gx = iw * GX / IW
    top = BOTTOM_BASE + (rows - 1) * pitch
    return [(X0 + (k % cols) * (iw + gx), top - (k // cols) * pitch) for k in range(n)], iw, cols


def fade_order(n, cols):
    """Azalışta sönecek simgelerin sırası: her satırın sağ ucundan, alt satırdan başlayan merdiven (prototipteki
    gibi alt satırda daha çok simge söner)."""
    rows = math.ceil(n / cols)

    def key(k):
        r, c = divmod(k, cols)
        row_len = min(cols, n - r * cols)
        return (row_len - 1 - c) + (rows - 1 - r) * 0.9

    return sorted(range(n), key=key)


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    before, after = p["before"], p["after"]
    unit = unit_of(p)
    nb, na = round_half_up(before / unit), round_half_up(after / unit)
    n = max(nb, na)
    each = f"EACH HOUSE = {unit:,} HOMES"
    cv.p = dict(p, subtitle=f"{p['subtitle']}  ·  {each}" if p["subtitle"] else each)
    back, head = cv.backdrop(), cv.header(max_px=1150)
    cv.p = p
    pos, iw, cols = grid(n)
    drop = na < nb
    changed = fade_order(nb, cols)[:nb - na] if drop else list(range(nb, na))
    step = min(STEP_MAX, CHANGE_WINDOW / max(len(changed), 1))
    start = {k: CHANGE_AT + j * step for j, k in enumerate(changed)}
    base_color = C["accent"] if drop or na == nb else C["neutral"]
    icons = []  # (k, normal simge, değişim simgesi)
    for k, (x, y) in enumerate(pos):
        normal = cv.house_icon(x, y, iw, base_color, fill_alpha=0.35, window=False)
        alt = cv.house_icon(x, y, iw, C["loss"] if drop else C["accent"], fill_alpha=0.35, window=False)
        icons.append((k, normal, alt))

    counter = cv.text(cl.W - 110, cl.H - 200, "", 110, "numbers", C["text"], ha="right", va="baseline")
    cv.fit_widest(counter, [f"{max(before, after):,}"], 600)
    period = [cv.text(cl.W - 110, cl.H - 225, s, 26, "label_bold", C["muted"], ha="right", va="top")
              for s in (p["before_label"], p["after_label"])]
    result = cv.text(cl.W / 2, 150, p["result_text"] or auto_result(p), 44, "numbers", C["loss"] if drop else C["accent"])
    cv.fit(result, 1700)
    diff = after - before

    def update(t):
        a = cl.grow(t, 0, 0.5)
        back.set_alpha(a)
        head.set_alpha(a)
        for k, normal, alt in icons:
            if k in start:
                f = cl.grow(t, start[k], start[k] + FADE)
                if drop:  # kırmızıya döner ve sönükleşir
                    app = cl.grow(t, 0.4 + k * 0.025, 0.8 + k * 0.025)
                    normal.set_alpha(app * a if f <= 0 else 0)
                    alt.set_alpha(app * a * (1 - 0.8 * f) if f > 0 else 0)
                else:  # yeni simge vurgu renginde belirir
                    normal.set_alpha(0)
                    alt.set_alpha(f * a)
            else:
                app = cl.grow(t, 0.4 + k * 0.025, 0.8 + k * 0.025) if k < nb else 0
                normal.set_alpha(app * a)
                alt.set_alpha(0)
        done = sum(1 for k in changed if t >= start[k] + FADE)
        val = before + round_half_up(diff * done / len(changed)) if changed else (after if t >= CHANGE_AT else before)
        counter.set_text(f"{val:,}")
        counter.set_alpha(a)
        later = t >= CHANGE_AT
        period[0].set_alpha(0 if later else a)
        period[1].set_alpha(a if later else 0)
        result.set_alpha(cl.grow(t, 5.2, 5.7))

    update.parts = {"icons": icons, "unit": unit, "counter": counter, "before_n": nb, "after_n": na}
    return update


SCENE = Scene(id="house_grid", title="Ev ızgarası", base_duration=7.5, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
