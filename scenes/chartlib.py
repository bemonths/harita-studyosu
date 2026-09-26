"""Grafik ve vaat sahnelerinin ortak parçaları: ortak ayarlar ("Başlık" ve "Zemin" grupları), piksel koordinatlı
tam ekran eksen, başlık bloğu, sağ üstteki büyük rakam, soluk county/eyalet zemini, ev simgesi ve ev biçimli sütun,
parıltılı county sınırı, nabız gibi atan soru işareti, çizilen ok ve "?"/"->" içeren zengin metin.

Koordinatlar 1920x1080 tasarım pikselidir (x soldan, y aşağıdan). Eksen bütün figürü kapladığı için önizlemede
(dpi 50) her şey figürle birlikte ölçeklenir. Görünüm, yerleşim ve zamanlamalar docs/referans_grafikler/
prototipleriyle aynıdır."""
import math
import re

import matplotlib.patheffects as pe
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

from engine import brand, geo
from engine.params import Choice, Color, CountySelect, StateSelect, Text
from engine.scene import cap_scale

W, H = 1920, 1080
# Prototipler Anton ve Cinzel'le tasarlandı; bu yazı tiplerinin cap_scale değerleri. Boyutlar bu oranla çarpılır,
# böylece marka yazı tipi değişince büyük harf yüksekliği aynı kalır (Anton'la prototip boyutları birebir).
REF_K = {"numbers": 0.8102, "place": 1.0007}
STROKE_PT = 6  # yazıların zemin renginde kontürü (prototipteki gibi)
Q_SCALE = 1.4  # "?" karakteri çevresindeki yazıdan bu oranda büyük
PULSE_AMP, PULSE_HZ = 0.06, 0.9  # soru işaretinin nabzı: ±%6, saniyede 0,9 kez
ARROW_RE = re.compile(r"->|→")

BACKDROPS = (("none", "Yok"), ("county", "County (sağda, soluk)"), ("state", "Eyalet (ortada, soluk)"))
FORMATS = (("money_k", "Para, bin ($419K)"), ("count", "Adet (4,771)"))


# ---------- ayarlar ----------
def T(name, label, default="", **kw):
    """Grafik sahnelerinin metin ayarı: '%' içeren metin doğrulamada reddedilir (kanal kuralı)."""
    return Text(name, label, default=default, no_percent=True, **kw)


def common_params(heading="", title="", subtitle="", source="", callout_value="", callout_label="",
                  backdrop="none", fips=None, callout_color=None):
    """Sekiz sahnenin ortak ayarları. Eyalet, ona bağlı county ayarlarından önce doğrulanmalı; bu yüzden sahnenin
    kendi county ayarları bu listeden sonra gelir."""
    return [
        T("heading", "Yer adı", heading, group="Başlık", help="Sol üstte yer adı (ör. LEE COUNTY)."),
        T("title", "Başlık", title, group="Başlık", help="Yer adının altındaki kalın satır."),
        T("subtitle", "Açıklama satırı", subtitle, group="Başlık"),
        T("source", "Kaynak", source, group="Başlık", help="Sol altta; boşsa gösterilmez."),
        T("callout_value", "Büyük rakam", callout_value, group="Başlık", help="Sağ üstte (ör. −$59K); boşsa gösterilmez."),
        T("callout_label", "Büyük rakamın alt satırı", callout_label, group="Başlık"),
        Color("callout_color", "Büyük rakam rengi", default=callout_color or brand.color("loss"), group="Başlık"),
        Choice("backdrop", "Zemin", default=backdrop, options=BACKDROPS, group="Zemin",
               help="County: sağ yarıda soluk county sınırı. Eyalet: ortada soluk eyalet sınırı."),
        StateSelect("state", "Eyalet", default="FL", group="Zemin"),
        CountySelect("fips", "County", default=fips, group="Zemin", state_param="state",
                     help="County zemini ve county sınırı çizen sahneler için."),
    ]


def common_check(p):
    if p["backdrop"] == "county" and not p["fips"]:
        return {"fips": "County zemini için bir county seçin."}
    return {}


# ---------- biçimler ve zaman ----------
def money_k(v):
    a = abs(v)
    if a >= 1_000_000:
        return f"${a / 1e6:.1f}M".replace(".0M", "M")
    return f"${round(a / 1000):,}K"


def fmt_value(v, fmt, decimals=0):
    if fmt == "money_k":
        return money_k(v)
    return f"{v:,.{int(decimals)}f}"


def signed(diff, fmt):
    """Fark yazısı: "−$55K", "+1,840" (eksi işareti U+2212)."""
    return ("−" if diff < 0 else "+") + fmt_value(abs(diff), fmt)


def ease_out(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 3


def grow(t, a, b):
    """Prototiplerin seg'i: a–b aralığında 0'dan 1'e, sonu yavaşlayan (kübik) geçiş."""
    return float(ease_out((t - a) / (b - a))) if b > a else float(t >= a)


def pulse(t):
    return 1 + PULSE_AMP * math.sin(t * 2 * math.pi * PULSE_HZ)


def house_path(x, y, w, total_h, roof=0.42):
    """Tabanı (x, y), genişliği w ve çatı tepesiyle birlikte yüksekliği total_h olan ev biçimi. Sütunlarda boy
    değerle orantılı olsun diye yükseklik çatı tepesine kadardır; çatı en fazla boyun %40'ı kadar olur."""
    r = min(w * roof, 0.4 * max(total_h, 0))
    body = max(total_h - r, 0)
    return np.array([(x, y), (x + w, y), (x + w, y + body), (x + w / 2, y + body + r), (x, y + body)])


def icon_height(w):
    """house_icon'un toplam yüksekliği (gövde 0,62w + çatı 0,42w)."""
    return w * (0.62 + 0.42)


# ---------- geometri ----------
def _area(r):
    x, y = r[:, 0], r[:, 1]
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


def fit_rings(rings, cx, cy, size, min_share=0.02):
    """Halkaları en uzun kenarı size piksel olacak şekilde (cx, cy) merkezli kutuya yerleştirir. Çok küçük parçalar
    (en büyüğün %2'sinden küçük adacıklar) atılır."""
    rings = [np.asarray(r, float) for r in rings if len(r) >= 3]
    if not rings:
        return []
    big = max(_area(r) for r in rings)
    rings = [r for r in rings if _area(r) >= big * min_share]
    pts = np.vstack(rings)
    mn, mx = pts.min(0), pts.max(0)
    s = size / max(mx - mn)
    mid = (mn + mx) / 2
    return [(r - mid) * s + [cx, cy] for r in rings]


def local_projection(rings):
    """Tek bir county ya da eyalet için yerel eşdikdörtgen projeksiyon (x = boylam * cos(orta enlem)). Albers'ta
    doğudaki eyaletler döndüğü için simgelerde sınırlar prototipteki gibi dik dursun diye bu kullanılır."""
    if not rings:
        return []
    lat = np.concatenate([r[:, 1] for r in rings])
    k = math.cos(math.radians((lat.min() + lat.max()) / 2))
    return [np.column_stack([r[:, 0] * k, r[:, 1]]) for r in rings]


def county_rings(fips):
    return local_projection(geo.county_lonlat(fips))


def state_rings(abbr):
    return local_projection(geo.state_lonlat(geo.state(abbr)[0]))


# ---------- çizim ----------
class Group:
    """Birlikte belirip kaybolan çizim parçaları. Her parçanın kendi temel opaklığı vardır; set_alpha(a) hepsini a ile
    çarpar. update(t) durumsuz kalsın diye her karede yeniden ayarlanır."""

    def __init__(self, items=()):
        self.items = list(items)  # (artist, temel opaklık)

    def add(self, artist, base=1.0):
        self.items.append((artist, base))
        return artist

    def extend(self, other):
        self.items += other.items
        return self

    def set_alpha(self, a):
        for art, base in self.items:
            art.set_alpha(base * a)

    def artists(self):
        return [a for a, _ in self.items]


class Canvas:
    def __init__(self, ctx):
        self.fig, self.p, self.F = ctx.fig, ctx.p, ctx.fonts
        self.C = brand.colors()
        self.ax = ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        self.k = {"numbers": cap_scale(self.fig, self.F["numbers"]) / REF_K["numbers"],
                  "place": cap_scale(self.fig, self.F["place"]) / REF_K["place"]}
        self.stroke = [pe.withStroke(linewidth=STROKE_PT, foreground=self.C["bg_dark"])]
        self.renderer = self.fig.canvas.get_renderer()

    # --- yazı ---
    def size(self, size, font):
        return size * self.k.get(font, 1.0)

    def text(self, x, y, s, size, font, color, ha="center", va="center", stroke=True, z=20):
        t = self.ax.text(x, y, s, fontproperties=self.F[font], fontsize=self.size(size, font), color=color,
                         ha=ha, va=va, zorder=z, parse_math=False, alpha=0)
        if stroke:
            t.set_path_effects(self.stroke)
        return t

    def px(self, display_w):
        return display_w * W / self.fig.bbox.width

    def width(self, s, size, font):
        """Metnin tasarım pikseli cinsinden genişliği (size prototip boyutu)."""
        prop = self.F[font].copy()
        prop.set_size(self.size(size, font))
        return self.px(self.renderer.get_text_width_height_descent(s, prop, ismath=False)[0])

    def fit(self, t, max_px):
        """Yazı max_px'ten genişse küçültür (sığıyorsa dokunmaz)."""
        limit = max_px * self.fig.bbox.width / W
        for _ in range(3):
            w = t.get_window_extent(renderer=self.renderer).width
            if w <= limit:
                return
            t.set_fontsize(t.get_fontsize() * limit / w * 0.99)

    def fit_widest(self, t, samples, max_px):
        """Her karede değişen sayaç yazısını en geniş değerine göre bir kez boyutlar."""
        old = t.get_text()
        t.set_text(max(samples, key=lambda s: self.width(s, 10, "numbers")))
        self.fit(t, max_px)
        t.set_text(old)

    def bottom(self, t):
        """Yazının kutusunun alt kenarı (tasarım pikseli)."""
        e = t.get_window_extent(renderer=self.renderer)
        return self.ax.transData.inverted().transform((0, e.y0))[1]

    # --- ortak bloklar ---
    def header(self, max_px=None):
        """Sol üstte yer adı, kalın başlık ve açıklama satırı; sol altta kaynak. Boş olanlar çizilmez."""
        p, C = self.p, self.C
        if max_px is None:
            max_px = 1150 if p["callout_value"] else 1700
        g = Group()
        for key, y, size, font, color in (("heading", H - 105, 54, "place", C["text"]),
                                          ("title", H - 172, 32, "label_bold", C["text"]),
                                          ("subtitle", H - 215, 22, "label", C["muted"])):
            if p[key]:
                t = g.add(self.text(110 if key == "heading" else 112, y, p[key], size, font, color, ha="left"))
                self.fit(t, max_px)
        if p["source"]:
            t = g.add(self.text(112, 58, p["source"], 20, "label", C["muted"], ha="left", stroke=False))
            self.fit(t, 1700)
        return g

    def callout(self, value=None, label=None, color=None, size=96, baseline=H - 190, max_px=640):
        """Sağ üstte büyük rakam ve altında kısa satır. Satır rakamın taban çizgisinin 14 px altından başlar,
        rakam ne kadar büyük olursa olsun üst üste binmez."""
        p, C = self.p, self.C
        value = p["callout_value"] if value is None else value
        label = p["callout_label"] if label is None else label
        g = Group()
        if not value:
            return g
        v = g.add(self.text(W - 110, baseline, value, size, "numbers", color or p["callout_color"], ha="right",
                            va="baseline"))
        self.fit(v, max_px)
        if label:
            lab = g.add(self.text(W - 110, baseline - 14, label, 26, "label_bold", C["text"], ha="right", va="top"))
            self.fit(lab, max_px)
        return g

    def backdrop(self):
        """Çok soluk zemin: county (sağ yarıda büyük) ya da eyalet (ortada) sınırı. Şeffaf kipte de çizilir."""
        p, color = self.p, self.C["text"]
        g = Group()
        if p["backdrop"] == "county" and p["fips"]:
            rings = fit_rings(county_rings(p["fips"]), W * 0.72, H * 0.44, 800)
        elif p["backdrop"] == "state":
            rings = fit_rings(state_rings(p["state"]), W * 0.5, H * 0.44, 900)
        else:
            return g
        for r in rings:
            g.add(self.ax.add_patch(Polygon(r, closed=True, fc=color, ec="none", zorder=1)), 0.06)
            g.add(self.ax.add_patch(Polygon(r, closed=True, fc="none", ec=color, lw=2, zorder=1)), 0.15)
        return g

    # --- şekiller ---
    def card(self, x, y, w, h, z=2):
        return self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=26",
                                                fc=self.C["surface"], ec=self.C["line"], lw=2, zorder=z, alpha=0))

    def rounded_bar(self, x, y, w, h, color, z=5):
        """Uçları yuvarlak yatay çubuk; genişliği tam olarak w (yuvarlama kısa çubukta daralır)."""
        bar = self.ax.add_patch(FancyBboxPatch((x, y), max(w, 0.01), h, boxstyle="round,pad=0,rounding_size=1",
                                               fc=color, ec="none", zorder=z, alpha=0))
        set_bar_width(bar, w)
        return bar

    def rounded_vbar(self, x, y, w, color, z=5):
        """Uçları yuvarlak dikey çubuk (termometre dolgusu); boyu set_vbar_height ile değişir."""
        bar = self.ax.add_patch(FancyBboxPatch((x, y), w, 0.01, boxstyle="round,pad=0,rounding_size=0.01",
                                               fc=color, ec="none", zorder=z, alpha=0))
        set_vbar_height(bar, 0)
        return bar

    def glow_outline(self, rings, color, fill_alpha=0.16, z=5):
        """Parıltılı sınır: dolgu + dört kat kenar (prototipteki county çizimi)."""
        g = Group()
        for r in rings:
            g.add(self.ax.add_patch(Polygon(r, closed=True, fc=color, ec="none", zorder=z)), fill_alpha)
            closed = np.vstack([r, r[:1]])
            for lw, a in ((18, 0.05), (10, 0.12), (5, 0.35), (2.2, 1.0)):
                g.add(self.ax.add_line(Line2D(closed[:, 0], closed[:, 1], color=color, lw=lw, zorder=z + 1,
                                              solid_joinstyle="round")), a)
        return g

    def county(self, fips, cx, cy, size, color=None, z=5):
        if not fips:
            return Group()
        return self.glow_outline(fit_rings(county_rings(fips), cx, cy, size), color or self.C["accent"], z=z)

    def house_icon(self, x, y, w, color, fill_alpha=0.2, window=True, z=6):
        """Ev simgesi: tabanı (x, y), genişliği w."""
        g = Group()
        pts = house_path(x, y, w, icon_height(w))
        g.add(self.ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", zorder=z)), fill_alpha)
        for lw, a in ((9, 0.10), (4, 0.35), (2.2, 1.0)):
            g.add(self.ax.add_patch(Polygon(pts, closed=True, fc="none", ec=color, lw=lw, joinstyle="round",
                                            zorder=z + 1)), a)
        if window:
            dw = w * 0.2
            g.add(self.ax.add_patch(Rectangle((x + w / 2 - dw / 2, y), dw, w * 0.3, fc=color, zorder=z + 2)), 0.8)
        return g

    def house_bar(self, x, base, w, color, fill=0.45, z=6):
        return HouseBar(self, x, base, w, color, fill, z)

    def qmark(self, x, y, size, z=21):
        return QMark(self, x, y, size, z)

    def arrow(self, pts, color, lw=7, z=15):
        return ArrowPath(self, pts, color, lw, z)

    def rich(self, s, x, y, size, color, max_px, ha="center", font="numbers"):
        return RichText(self, s, x, y, size, color, max_px, ha, font)


def set_bar_width(bar, w):
    """Yuvarlak uçlu çubuğun genişliğini değiştirir; yuvarlama yarıçapı kısa kenarın yarısını geçmez."""
    w = max(float(w), 0.0)
    h = bar.get_height()
    bar.set_width(max(w, 0.01))
    bar.set_boxstyle("round", pad=0, rounding_size=max(min(w, h) / 2, 0.01))
    bar.set_visible(w > 0.5)


def set_vbar_height(bar, h):
    h = max(float(h), 0.0)
    w = bar.get_width()
    bar.set_height(max(h, 0.01))
    bar.set_boxstyle("round", pad=0, rounding_size=max(min(w, h) / 2, 0.01))
    bar.set_visible(h > 0.5)


class HouseBar:
    """Ev biçimli sütun: set_height(toplam yükseklik) ile büyür. Boy (çatı tepesine kadar) değerle orantılıdır."""

    def __init__(self, cv, x, base, w, color, fill, z):
        self.x, self.base, self.w, self.h = x, base, w, 0.0
        pts = house_path(x, base, w, 0.1)
        self.group = Group()
        self.polys = [self.group.add(cv.ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", zorder=z)), fill)]
        for lw, a in ((8, 0.10), (2.4, 1.0)):
            self.polys.append(self.group.add(cv.ax.add_patch(
                Polygon(pts, closed=True, fc="none", ec=color, lw=lw, joinstyle="round", zorder=z + 1)), a))

    def set_height(self, h):
        self.h = max(float(h), 0.1)
        pts = house_path(self.x, self.base, self.w, self.h)
        for poly in self.polys:
            poly.set_xy(pts)

    def set_alpha(self, a):
        self.group.set_alpha(a)

    def top(self):
        return self.base + self.h


class QMark:
    """Vurgu renginde, nabız gibi atan soru işareti (ortası sabit)."""

    def __init__(self, cv, x, y, size, z):
        self.cv, self.base = cv, cv.size(size, "numbers")
        self.t = cv.text(x, y, "?", size, "numbers", cv.C["accent"], z=z)

    def update(self, t, alpha):
        self.t.set_fontsize(self.base * pulse(t))
        self.t.set_alpha(alpha)

    def artists(self):
        return [self.t]


class ArrowPath:
    """Noktalardan geçen, ucunda ok başı olan kalın çizgi; set(prog, alpha) ile 0–1 arası çizilir."""

    def __init__(self, cv, pts, color, lw, z):
        self.pts = np.asarray(pts, float)
        self.lw = lw
        self.lines = [cv.ax.add_line(Line2D([], [], color=color, lw=w, zorder=z, solid_capstyle="round",
                                            solid_joinstyle="round")) for w in (lw * 3, lw)]
        self.bases = (0.12, 1.0)
        self.head = cv.ax.add_patch(Polygon(np.zeros((3, 2)), closed=True, fc=color, ec="none", zorder=z + 1))

    def partial(self, prog):
        pts = self.pts
        segs = np.hypot(*np.diff(pts, axis=0).T)
        L = segs.sum() * prog
        if L <= 0:
            return pts[:1]
        out, acc = [pts[0]], 0.0
        for i, s in enumerate(segs):
            if acc + s >= L:
                out.append(pts[i] + (pts[i + 1] - pts[i]) * ((L - acc) / s if s else 0))
                break
            out.append(pts[i + 1])
            acc += s
        return np.array(out)

    def set(self, prog, alpha):
        out = self.partial(prog) if len(self.pts) >= 2 else self.pts
        visible = prog > 0 and len(out) >= 2
        for ln, base in zip(self.lines, self.bases):
            ln.set_data(out[:, 0], out[:, 1])
            ln.set_alpha(base * alpha)
            ln.set_visible(visible)
        self.head.set_visible(False)
        if visible:
            d = out[-1] - out[-2]
            n = np.hypot(*d)
            if n > 0:
                d = d / n
                nrm = np.array([-d[1], d[0]])
                k = self.lw / 7
                tip = out[-1] + d * 18 * k
                self.head.set_xy([tip, out[-1] - d * 26 * k + nrm * 22 * k, out[-1] - d * 26 * k - nrm * 22 * k])
                self.head.set_alpha(alpha)
                self.head.set_visible(True)


def tokenize(s):
    """Metni parçalara ayırır: ("text", s), ("q",) soru işareti, ("arrow",) ok ve ("space",) boşluk."""
    out = []
    for i, part in enumerate(ARROW_RE.split(s)):
        if i > 0:
            out.append(("arrow",))
        for j, chunk in enumerate(part.split("?")):
            if j > 0:
                out.append(("q",))
            if chunk.strip():
                out.append(("text", chunk))
            elif chunk:
                out.append(("space",))
    # metin parçalarının baş/son boşlukları ayrı "space" olur; art arda ve uçlardaki boşluklar atılır
    items = []
    for tok in out:
        if tok[0] == "text":
            s0 = tok[1]
            if s0[:1].isspace():
                items.append(("space",))
            items.append(("text", s0.strip()))
            if s0[-1:].isspace():
                items.append(("space",))
        else:
            items.append(tok)
    clean = []
    for tok in items:
        if tok[0] == "space" and (not clean or clean[-1][0] == "space"):
            continue
        clean.append(tok)
    while clean and clean[-1][0] == "space":
        clean.pop()
    return clean


class RichText:
    """Düz yazı + vurgu renginde nabızlı "?" + çizilmiş ok ("->" ya da "→"; yazı tipinde yok). Parçalar yatayda
    dizilir, dikeyde ortaları hizalanır. Toplam genişlik max_px'i aşarsa hepsi birlikte küçülür."""

    def __init__(self, cv, s, x, y, size, color, max_px, ha, font):
        self.cv = cv
        toks = tokenize(s)
        px_pt = 100 / 72  # 1080p'de 1 punto = 100/72 piksel

        def layout(sz):
            widths = []
            for tok in toks:
                if tok[0] == "text":
                    widths.append(cv.width(tok[1], sz, font))
                elif tok[0] == "q":
                    widths.append(cv.width("?", sz * Q_SCALE, "numbers"))
                elif tok[0] == "arrow":
                    widths.append(1.1 * sz * px_pt * 0.8)
                else:
                    widths.append(0.22 * sz * px_pt)
            # boşluksuz yan yana gelen parçalar arasında küçük bir aralık
            gaps = [0.0] + [0.0 if "space" in (toks[i - 1][0], toks[i][0]) else 0.06 * sz * px_pt
                            for i in range(1, len(toks))]
            return widths, gaps, sum(widths) + sum(gaps)

        widths, gaps, total = layout(size)
        if total > max_px:
            size *= max_px / total
            widths, gaps, total = layout(size)
        left = {"center": x - total / 2, "left": x, "right": x - total}[ha]
        self.width = total
        self.parts = Group()
        self.qmarks = []
        cur = left
        for tok, w, gap in zip(toks, widths, gaps):
            cur += gap
            cx = cur + w / 2
            if tok[0] == "text":
                self.parts.add(cv.text(cx, y, tok[1], size, font, color))
            elif tok[0] == "q":
                self.qmarks.append(cv.qmark(cx, y, size * Q_SCALE))
            elif tok[0] == "arrow":
                k = size / 58
                x0, x1 = cur, cur + w
                self.parts.add(cv.ax.add_line(Line2D([x0, x1 - 10 * k], [y, y], color=cv.C["muted"], lw=6 * k,
                                                     solid_capstyle="round", zorder=19)))
                self.parts.add(cv.ax.add_patch(Polygon([(x1, y), (x1 - 26 * k, y + 17 * k), (x1 - 26 * k, y - 17 * k)],
                                                       closed=True, fc=cv.C["muted"], ec="none", zorder=19)))
            cur += w

    def update(self, t, alpha):
        self.parts.set_alpha(alpha)
        for q in self.qmarks:
            q.update(t, alpha)
