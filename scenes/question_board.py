"""Vaat ekranı: ortada büyük başlık (ör. FLORIDA) ve altında açıklama; altında 2–4 soru kartı 0,8 sn arayla hafifçe
yükselerek belirir. Kartta bir simge (ev, county sınırı, 2x5 ev ya da yok), bir değer satırı ("?" karakterleri vurgu
renginde ve nabızlı, "->" çizilmiş ok) ve iki satırlık açıklama vardır. Değeri boş olan kart çizilmez; kartlar
ortalanır. update(t) içindeki t temel süre (6 sn) cinsindendir."""
import matplotlib.transforms as mtransforms

from engine.params import Choice, CountySelect
from engine.scene import Scene
from scenes import chartlib as cl
from scenes.chartlib import T

CARD_W, CARD_H, GAP, CARD_Y, RISE = 410, 600, 36, 130, 40
ICONS = (("house", "Ev"), ("county", "County sınırı"), ("houses10", "10 ev (2x5)"), ("none", "Yok"))
DEFAULT_CARDS = [
    ("house", None, "$580K -> ?", "ONE HOUSE IN / FORT MYERS"),
    ("county", "12015", "? HOMES", "FEWER HOMES FOR SALE / IN ONE YEAR"),
    ("houses10", None, "? IN 10", "SELLERS CUT / THEIR PRICE"),
    ("county", "12055", "#1 ?", "AND IT'S NOT / CAPE CORAL"),
]


def card_params():
    out = []
    for k, (icon, fips, value, caption) in enumerate(DEFAULT_CARDS, 1):
        g = f"Kart {k}"
        out += [
            Choice(f"card{k}_icon", "Simge", default=icon, options=ICONS, group=g),
            CountySelect(f"card{k}_fips", "County (simge için)", default=fips, group=g, state_param="state"),
            T(f"card{k}_value", "Değer", value, group=g, max_len=40,
              help="'?' vurgu renginde ve nabızlı, '->' ok olarak çizilir. Boşsa kart çizilmez."),
            T(f"card{k}_caption", "Açıklama", caption, group=g, max_len=60, help="İki satır için ' / ' ile ayırın."),
        ]
    return out


PARAMS = cl.common_params(heading="FLORIDA", subtitle="10 COUNTIES  ·  4 QUESTIONS") + card_params()
PARAMS[0] = T("heading", "Başlık (ortada)", "FLORIDA", group="Başlık", help="Ortada büyük başlık (ör. FLORIDA).")


def cards(p):
    return [k for k in range(1, 5) if p[f"card{k}_value"].strip()]


def check(p):
    errors = cl.common_check(p)
    if len(cards(p)) < 2:
        errors["card2_value"] = "En az iki kartın değeri dolu olmalı."
    for k in cards(p):
        if p[f"card{k}_icon"] == "county" and not p[f"card{k}_fips"]:
            errors[f"card{k}_fips"] = "County simgesi için bir county seçin."
    return errors


def caption_lines(s):
    return [x.strip() for x in s.split(" / ") if x.strip()][:2]


def setup(ctx):
    cv = cl.Canvas(ctx)
    p, C = cv.p, cv.C
    back = cv.backdrop()
    head = cl.Group()
    ht = head.add(cv.text(cl.W / 2, cl.H - 110, p["heading"], 70, "place", C["text"]))
    cv.fit(ht, 1300)
    y_sub = cl.H - 180
    if p["title"]:
        cv.fit(head.add(cv.text(cl.W / 2, cl.H - 178, p["title"], 32, "label_bold", C["text"])), 1500)
        y_sub = cl.H - 222
    if p["subtitle"]:
        cv.fit(head.add(cv.text(cl.W / 2, y_sub, p["subtitle"], 28, "label", C["muted"])), 1500)
    if p["source"]:
        head.add(cv.text(112, 58, p["source"], 20, "label", C["muted"], ha="left", stroke=False))
    call = cv.callout()

    ks = cards(p)
    n = len(ks)
    x0 = (cl.W - (n * CARD_W + (n - 1) * GAP)) / 2
    items = []  # (başlangıç anı, kaydırma dönüşümü, parçalar, zengin metin)
    for i, k in enumerate(ks):
        before = set(cv.ax.get_children())
        x, y = x0 + i * (CARD_W + GAP), CARD_Y
        cx = x + CARD_W / 2
        g = cl.Group()
        g.add(cv.card(x, y, CARD_W, CARD_H), 0.92)
        icon = p[f"card{k}_icon"]
        if icon == "house":
            g.extend(cv.house_icon(cx - 100, y + 330, 200, C["accent"]))
        elif icon == "county":
            g.extend(cv.county(p[f"card{k}_fips"], cx, y + 430, 230))
        elif icon == "houses10":
            iw, ig = 52, 14
            rx = cx - (5 * iw + 4 * ig) / 2
            for r in range(2):
                for c in range(5):
                    g.extend(cv.house_icon(rx + c * (iw + ig), y + 440 - r * 80, iw, C["line"], fill_alpha=0.3,
                                           window=False))
        rich = cv.rich(p[f"card{k}_value"], cx, y + 215, 60, C["text"], CARD_W - 60)
        lines = caption_lines(p[f"card{k}_caption"])
        for j, s in enumerate(lines):
            yy = y + (100 - 38 * j if len(lines) == 2 else 81)
            cv.fit(g.add(cv.text(cx, yy, s, 26, "label", C["muted"])), CARD_W - 40)
        # kartın bütün parçaları aynı kaydırma dönüşümünü kullanır: yükselme update'te tek yerden ayarlanır
        shift = mtransforms.Affine2D()
        for art in cv.ax.get_children():
            if art not in before and hasattr(art, "set_transform"):
                art.set_transform(shift + cv.ax.transData)
        items.append((0.6 + i * 0.8, shift, g, rich))

    def update(t):
        a0 = cl.grow(t, 0.0, 0.6)
        back.set_alpha(a0)
        head.set_alpha(a0)
        call.set_alpha(cl.grow(t, 3.6, 4.2))
        for st, shift, g, rich in items:
            pr = cl.grow(t, st, st + 0.6)
            shift.clear().translate(0, -(1 - pr) * RISE)
            g.set_alpha(pr)
            rich.update(t, pr)

    update.parts = {"cards": ks, "rich": [it[3] for it in items]}
    return update


SCENE = Scene(id="question_board", title="Vaat ekranı", base_duration=6.0, params=PARAMS, setup=setup,
              bg_center=(0.5, 0.45), check=check)
