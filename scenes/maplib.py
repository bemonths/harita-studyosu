"""Harita sahnelerinin (state_map, county_focus) ortak parçaları: ayar tanımları, geometri, kameralar ve
çizim katmanları. Katmanlar state_map'teki sırayla oluşturulur; sıra değişirse görünüm de değişir."""
import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.collections import PolyCollection

from engine import brand, framing, geo
from engine.params import Categories, Color, CountyAssign, CountySelect, Number, StateSelect, Text
from engine.scene import cap_scale, ease, fit_text

# neon sınır: (çizgi kalınlığı, opaklık). Parlama katmanları turuncu vurgu rengi için 1,5 kat güçlü.
GLOW_SPECS = [(16, 0.075), (10, 0.15), (6, 0.33), (2.4, 1.0)]
# vurgu sırasında diğer county'lerin tam soluklaşmada kaybettiği doygunluk ve parlaklık oranı
DIM_SAT, DIM_VAL = 0.55, 0.5
# vurgu etiketi yerleşimi (ekran oranı): kenar boşluğu ve istatistik satırının en fazla küçülebileceği oran
LABEL_MARGIN, STAT_MIN_SCALE = 0.03, 0.75
# etiket bloğu ile vurgulanan county'nin sınır kutusu arasındaki en az boşluk; kara örtüşmesi ölçülürken bloğa
# eklenen pay (yazı kıyı çizgisine yapışmasın). İkisi de 1080p pikseli.
LABEL_PAD_PX, LAND_PAD_PX = 24, 16
# varsayılan etiket yeri: county merkezinden yatay LABEL_DX (ekran oranı), dikey LABEL_DY (kamera genişliği oranı).
# Satırlar (ad, alt yazı, istatistik) dirsek yüksekliğine göre LINE_DY kadar kaydırılır (kamera genişliği oranı).
LABEL_DX, LABEL_DY, LINE_DY = 0.19, 0.06, (0.004, -0.004, -0.034)
# bağlantı çizgisinin dirseği: yazıdan ELBOW uzakta, county merkezinden en az LEADER_MIN dışarıda (ekran oranı)
ELBOW, LEADER_MIN = 0.01, 0.02
# etiket yeri araması: adım (ekran oranı) ve puan ağırlıkları. Puan = eyalet karası payı + diğer kara payı * OTHER_LAND_W
# + varsayılan yere uzaklık * MOVE_W (+ varsayılan yerden ayrılma ve taraf değiştirme cezaları); en düşük puan seçilir.
SEARCH_STEP, OTHER_LAND_W, MOVE_W, LEAVE_DEFAULT, SWITCH_SIDE = 0.01, 0.25, 0.1, 0.02, 0.03
LAND_GRID = (384, 216)  # kara maskesinin ekran çözünürlüğü (sütun, satır)
# vurgu etiketi yazılarının zemin renginde kontürü (1080p'de yaklaşık 4 px; nokta = px * 72 / 100)
LABEL_STROKE_PT = 4 * 72 / 100
# istatistik yazısı koyu kategori renginde okunmuyorsa açılır: en az bu parlaklık (HSV value), text ile bu oranda karışım
STAT_MIN_VALUE, STAT_TEXT_MIX = 0.65, 0.45
# odaktaki county kategorisizse (none) üzerine binen vurgu rengi dolgusunun opaklığı
NONE_FOCUS_TINT = 0.3


def readable_on_dark(color, text_color):
    """Koyu zeminde okunur renk: parlaklığı yeterliyse aynen, değilse text rengiyle %45 karışmış ve
    parlaklığı en az 0,65'e çıkarılmış tonu döndürür."""
    rgb = np.array(mcolors.to_rgb(color))
    if mcolors.rgb_to_hsv(rgb)[2] >= STAT_MIN_VALUE:
        return color
    rgb = rgb * (1 - STAT_TEXT_MIX) + np.array(mcolors.to_rgb(text_color)) * STAT_TEXT_MIX
    h, s, v = mcolors.rgb_to_hsv(rgb)
    return tuple(mcolors.hsv_to_rgb([h, s, max(v, STAT_MIN_VALUE)]))


def to_screen(cam, pts):
    """Veri koordinatlarını kameranın ekran oranına çevirir: (n, 2) dizi, 0–1, y aşağıdan yukarı."""
    pts = np.atleast_2d(np.asarray(pts, float))
    return np.column_stack([(pts[:, 0] - cam[0]) / cam[2] + 0.5, (pts[:, 1] - cam[1]) / (cam[2] * 9 / 16) + 0.5])


def land_tables(cam, state_rings, all_rings, grid=LAND_GRID):
    """Kamerada görünen eyalet karası ve bütün kara (ABD) için alan toplamı tabloları (satır 0 = ekranın üstü)."""
    from PIL import Image, ImageDraw

    gw, gh = grid
    tables = []
    for rings in (state_rings, all_rings):
        img = Image.new("L", (gw, gh), 0)
        draw = ImageDraw.Draw(img)
        for ring in rings:
            s = to_screen(cam, ring)
            if s[:, 0].max() < 0 or s[:, 0].min() > 1 or s[:, 1].max() < 0 or s[:, 1].min() > 1 or len(s) < 3:
                continue
            draw.polygon(np.column_stack([s[:, 0] * gw, (1 - s[:, 1]) * gh]).ravel().tolist(), fill=1)
        table = np.zeros((gh + 1, gw + 1))
        table[1:, 1:] = np.asarray(img, float).cumsum(0).cumsum(1)
        tables.append(table)
    return tables


def rect_share(table, x0, x1, y0, y1):
    """Ekran dikdörtgenlerinin (ekran oranı, y aşağıdan yukarı) maskede kalan payı (0–1); dizilerle çalışır."""
    gh, gw = table.shape[0] - 1, table.shape[1] - 1
    c0, c1 = (np.clip(np.round(np.asarray(v) * gw), 0, gw).astype(int) for v in (x0, x1))
    r0, r1 = (np.clip(np.round((1 - np.asarray(v)) * gh), 0, gh).astype(int) for v in (y1, y0))
    total = table[r1, c1] - table[r0, c1] - table[r1, c0] + table[r0, c0]
    return total / np.maximum((c1 - c0) * (r1 - r0), 1)


def split_two_lines(text):
    """Metni kelime sınırından, iki satırın uzunlukları en yakın olacak şekilde ikiye böler."""
    words = text.split()
    if len(words) < 2:
        return text
    i = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
    return " ".join(words[:i]) + "\n" + " ".join(words[i:])


# ---------- ayarlar ----------
def state_param():
    return StateSelect("state", "Eyalet", default="FL")


def style_params():
    return [
        Color("accent", "Sınır rengi (neon)", default=brand.color("accent"), group="Renkler"),
        Categories("categories", "Renk kategorileri", default=brand.categories(), group="Renkler"),
    ]


def assign_param():
    return CountyAssign("assign", "County boyama", default={}, group="County boyama",
                        state_param="state", categories_param="categories")


def focus_params(required):
    return [
        CountySelect("focus", "Vurgulanan county", default=None, group="Vurgu", state_param="state",
                     allow_none=not required),
        Text("focus_name", "Vurgu adı", default="", auto=True, group="Vurgu",
             help="Boş bırakılırsa '<AD> COUNTY' yazılır."),
        Text("focus_sub", "Vurgu alt yazısı", default="", group="Vurgu"),
        Text("focus_stat", "Vurgu istatistiği", default="", group="Vurgu",
             help="County'nin kategori renginde yazılır."),
        Number("focus_zoom", "Vurgu yakınlığı", default=0.55, group="Vurgu", lo=0.1, hi=1.5, step=0.05),
    ]


def camera_params():
    return [
        Number("zoom", "Yakınlaştırma", default=1.0, group="Kamera", lo=0.5, hi=2.0, step=0.01),
        Number("shift_x", "Yatay kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
        Number("shift_y", "Dikey kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
    ]


# ---------- yardımcılar ----------
def cam_lerp(a, b, t):
    """İki kamera arasında yumuşak geçiş; genişlik logaritmik ölçekte değişir."""
    e = ease(t)
    c = a[:2] + (b[:2] - a[:2]) * e
    w = np.exp(np.log(a[2]) + (np.log(b[2]) - np.log(a[2])) * e)
    return np.array([c[0], c[1], w])


def cam_zoom(cam, anchor, k):
    """Kamerayı k oranında daraltır (k<1 yaklaşır); anchor noktası ekrandaki yerinde kalır."""
    return np.array([anchor[0] + (cam[0] - anchor[0]) * k, anchor[1] + (cam[1] - anchor[1]) * k, cam[2] * k])


def focus_title(c):
    return (f"{c.name} {c.lsad}" if c.lsad else c.name).upper()


class MapGeometry:
    """Seçili eyaletin projekte edilmiş geometrisi, county boyaması ve kameralar.
    label_side: "left", "right" ya da "auto" (eyalete daha az binen taraf).
    region: eyalet kadrajında eyaletin sığacağı ekran bölgesi (bkz. framing.state_frame)."""

    def __init__(self, p, label_side="left", region=framing.REGION):
        fips, _, self.state_name = geo.state(p["state"])
        us = geo.us_outlines(fips)
        self.us_polys = [r for _, rs in us for r in rs]
        self.state_rings = [r for st, rs in us if st == fips for r in rs]
        self.counties = cs = geo.counties(fips)
        polys, owner = [], []
        for i, c in enumerate(cs):
            for r in c.rings:
                polys.append(r)
                owner.append(i)
        self.c_polys, self.c_owner = polys, np.array(owner)
        self.c_key = [p["assign"].get(c.fips, "none") for c in cs]
        self.col = {c["key"]: c["color"] for c in p["categories"]}
        # county'lerin kuzeyden güneye sırası (boyama sırası)
        self.rank = np.argsort(np.argsort(-np.array([np.vstack(c.rings)[:, 1].mean() for c in cs])))

        self.cam_us = framing.box(np.vstack(self.us_polys), 0.06)
        state_pts = np.vstack(self.state_rings)
        self.state_center = (state_pts.min(0) + state_pts.max(0)) / 2
        self.cam_state = framing.state_frame(state_pts, p["zoom"], p["shift_x"], p["shift_y"], region)
        self.focus_idx = next((i for i, c in enumerate(cs) if c.fips == p["focus"]), None)
        self.label_side = None
        self.focus_zoom = p["focus_zoom"]
        if self.focus_idx is not None:
            self.focus_pts = np.vstack(cs[self.focus_idx].rings)
            # kamera hedefi, bağlantı çizgisi ve nokta: en büyük parçanın içindeki nokta
            self.focus_center = framing.focus_point(cs[self.focus_idx].rings)
            if label_side == "auto":
                label_side = framing.label_side(self.state_rings, self.focus_pts, self.cam_state[2], p["focus_zoom"],
                                                self.focus_center)
            self.set_label_side(label_side)

    def focus_camera(self, side):
        return framing.focus_frame(self.focus_pts, self.cam_state[2], self.focus_zoom, side, self.focus_center)

    def set_label_side(self, side):
        """Etiket tarafını ve ona göre vurgu kamerasını belirler (etiket sığmazsa MapLayers değiştirir)."""
        self.label_side = side
        self.cam_focus = self.focus_camera(side)

    def set_state_camera(self, cam):
        """Eyalet kadrajını değiştirir (state_map sol blok için eyaleti kaydırınca); vurgu kamerası da yenilenir."""
        self.cam_state = np.asarray(cam, float)
        if self.focus_idx is not None:
            self.cam_focus = self.focus_camera(self.label_side)


class MapLayers:
    """Harita çizim katmanları: enlem-boylam, ABD zemini, eyalet dolgusu, county'ler, neon sınır,
    vurgu parlaması ve etiket. Değerler update() içinde set_* metotlarıyla verilir (durumsuz)."""

    def __init__(self, fig, g, p, fonts, place_label=True):
        """place_label=False: etiket yerleşimi ertelenir; sahne eyalet kadrajını ayarladıktan sonra
        place_label(fig) çağrılır (state_map sol blok boşluğu)."""
        C = brand.colors()
        PLACE, BAR, BARB = fonts["place"], fonts["label"], fonts["label_bold"]
        PK = cap_scale(fig, PLACE)  # yer adı yazı tipini tasarım boyutlarına eşitler
        NEON = p["accent"]
        self.g = g

        ax = self.ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        for lon in range(-125, -64, 5):
            la = np.linspace(20, 52, 120)
            x, y = geo.albers(np.full_like(la, lon), la)
            ax.plot(x, y, color=C["line"], lw=0.6, alpha=0.5, zorder=1)
        for lat in range(20, 55, 5):
            lo = np.linspace(-130, -60, 200)
            x, y = geo.albers(lo, np.full_like(lo, lat))
            ax.plot(x, y, color=C["line"], lw=0.6, alpha=0.5, zorder=1)

        self.us_coll = PolyCollection(g.us_polys, facecolors=C["surface"], edgecolors=C["line"], linewidths=0.8, zorder=2)
        ax.add_collection(self.us_coll)
        self.state_fill = PolyCollection(g.state_rings, facecolors=NEON, edgecolors="none", alpha=0.0, zorder=3)
        ax.add_collection(self.state_fill)
        self.base_rgba = np.array([mcolors.to_rgba(g.col[g.c_key[o]]) for o in g.c_owner])
        self.c_coll = PolyCollection(g.c_polys, facecolors=self.base_rgba, edgecolors=C["bg_dark"], linewidths=0.9, zorder=4)
        ax.add_collection(self.c_coll)

        # ana halka üzerinde neon sınır
        self.main = main = max(g.state_rings, key=len)
        segl = np.hypot(*np.diff(main, axis=0).T)
        self.cum = np.concatenate([[0], np.cumsum(segl)])
        self.glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_capstyle="round", zorder=6)[0] for w, a in GLOW_SPECS]
        isles = [r for r in g.state_rings if r is not main]
        self.isle_lines = [ax.plot(r[:, 0], r[:, 1], color=NEON, lw=1.4, alpha=0.0, zorder=6)[0] for r in isles]
        self.head = ax.plot([], [], "o", color=C["text"], ms=7, alpha=0.0, zorder=7)[0]

        # vurgulanan county: kenar parlaması, bağlantı çizgisi ve etiket
        self.ch_glow = []
        if g.focus_idx is not None:
            for r in g.counties[g.focus_idx].rings:
                for w, a in [(12, 0.08), (6, 0.2), (2.2, 1.0)]:
                    self.ch_glow.append((ax.plot(r[:, 0], r[:, 1], color=NEON, lw=w, alpha=0.0, zorder=8)[0], a))
            cx, cy = g.focus_center
            self.leader = ax.plot([], [], color=C["text"], lw=1.6, alpha=0.0, zorder=9)[0]
            self.dot = ax.plot([cx], [cy], "o", color=C["text"], ms=9, alpha=0.0, zorder=9)[0]
            # etiket yazıları harita üstünde de okunsun diye zemin renginde ince kontür
            stroke = [pe.withStroke(linewidth=LABEL_STROKE_PT, foreground=C["bg_dark"])]
            self.t_name = ax.text(0, 0, p["focus_name"] or focus_title(g.counties[g.focus_idx]),
                                  parse_math=False, fontproperties=PLACE, fontsize=64 * PK, color=C["text"],
                                  va="bottom", alpha=0, zorder=10, path_effects=stroke)
            fit_text(fig, self.t_name, 0.30)
            self.t_sub = ax.text(0, 0, p["focus_sub"], parse_math=False, fontproperties=BAR, fontsize=24,
                                 color=C["muted"], va="top", alpha=0, zorder=10, path_effects=stroke)
            key = g.c_key[g.focus_idx]
            # istatistik kategori renginde; koyu kategori renklerinde okunur açık ton (dolgu ve nabız değişmez)
            stat_color = readable_on_dark(g.col[key], C["text"]) if key != "none" else NEON
            self.t_stat = ax.text(0, 0, p["focus_stat"], parse_math=False, fontproperties=BARB, fontsize=26,
                                  color=stat_color, va="top", alpha=0, zorder=10, path_effects=stroke)
            if place_label:
                self.place_label(fig)

        # odaktaki county kategorisizse vurgu renginde düşük opaklıkta dolguyla görünür olur
        self.focus_none = g.focus_idx is not None and g.c_key[g.focus_idx] == "none"
        self.accent_rgb = np.array(mcolors.to_rgb(NEON))
        self.base_hsv = mcolors.rgb_to_hsv(self.base_rgba[:, :3])
        self.surface_v = mcolors.rgb_to_hsv(mcolors.to_rgb(C["surface"]))[2]
        self.edge = np.array([[*mcolors.to_rgba(C["bg_dark"])[:3], 1.0]] * len(g.c_owner))
        self.is_focus = g.c_owner == g.focus_idx if g.focus_idx is not None else np.zeros(len(g.c_owner), bool)

    # ---------- vurgu etiketinin yerleşimi ----------
    def _block(self, fig):
        """Etiket bloğunun ekran oranı cinsinden genişliği ve dirsek yüksekliğine göre alt ve üst sınırı."""
        r = fig.canvas.get_renderer()
        W, H = fig.bbox.width, fig.bbox.height
        width, lo, hi = 0.0, 0.0, 0.0
        for t, dy in zip((self.t_name, self.t_sub, self.t_stat), LINE_DY):
            if not t.get_text():
                continue
            bb = t.get_window_extent(renderer=r)
            y = self.ax.transData.transform(t.get_position())[1]
            width = max(width, bb.width / W)
            lo = min(lo, (bb.y0 - y) / H + dy * 16 / 9)
            hi = max(hi, (bb.y1 - y) / H + dy * 16 / 9)
        return width, lo, hi

    def _room(self, side):
        """Blok county'nin üstüne ya da altına alındığında sığabileceği en büyük genişlik (ekran oranı)."""
        c = to_screen(self.g.focus_camera(side), self.g.focus_center)[0, 0]
        if side == "left":
            return c - LEADER_MIN - ELBOW - LABEL_MARGIN
        return 1 - LABEL_MARGIN - (c + LEADER_MIN + ELBOW)

    def _land(self, side):
        if side not in self._land_cache:
            self._land_cache[side] = land_tables(self.g.focus_camera(side), self.g.state_rings, self.g.us_polys)
        return self._land_cache[side]

    def _search(self, fig, sides):
        """Etiket bloğunun en iyi yeri: (taraf, iç kenarın ekran x'i, dirseğin ekran y'si); yer yoksa None.
        Koşullar: blok ekran kenarlarından LABEL_MARGIN içeride; county'nin sınır kutusuna ve place_label'a verilen
        engellere LABEL_PAD_PX'ten fazla yaklaşmaz; iç kenarı county merkezinin dışında kalır (bağlantı çizgisi
        yazıların üstünden geçmez).
        Uyan yerler arasında eyaletin karasıyla en az örtüşen (su ya da eyalet dışı), varsayılan yere en yakın
        olan seçilir; varsayılan yer ve tercih edilen taraf küçük bir öncelik alır."""
        g = self.g
        width, lo, hi = self._block(fig)
        pad = np.array([LABEL_PAD_PX / 1920, LABEL_PAD_PX / 1080])
        best = None
        for k, side in enumerate(sides):
            cam = g.focus_camera(side)
            c, cy = to_screen(cam, g.focus_center)[0]
            pts = to_screen(cam, g.focus_pts)
            (bx0, by0), (bx1, by1) = pts.min(0) - pad, pts.max(0) + pad
            sign = -1 if side == "left" else 1
            x_def, y_def = c + sign * LABEL_DX, cy + LABEL_DY * 16 / 9
            if side == "left":  # iç kenar = bloğun sağ kenarı
                x_lo, x_hi = LABEL_MARGIN + width, c - LEADER_MIN - ELBOW
            else:  # iç kenar = bloğun sol kenarı
                x_lo, x_hi = c + LEADER_MIN + ELBOW, 1 - LABEL_MARGIN - width
            y_lo, y_hi = LABEL_MARGIN - lo, 1 - LABEL_MARGIN - hi
            if x_lo > x_hi or y_lo > y_hi:
                continue
            xs = np.append(np.arange(x_lo, x_hi, SEARCH_STEP), [x_hi] + ([x_def] if x_lo <= x_def <= x_hi else []))
            ys = np.append(np.arange(y_lo, y_hi, SEARCH_STEP), [y_hi] + ([y_def] if y_lo <= y_def <= y_hi else []))
            X, Y = np.meshgrid(xs, ys)
            x0, x1 = (X - width, X) if side == "left" else (X, X + width)
            y0, y1 = Y + lo, Y + hi
            free = (x1 <= bx0) | (x0 >= bx1) | (y1 <= by0) | (y0 >= by1)
            for ox0, oy0, ox1, oy1 in self._avoid:
                free &= (x1 <= ox0 - pad[0]) | (x0 >= ox1 + pad[0]) | (y1 <= oy0 - pad[1]) | (y0 >= oy1 + pad[1])
            if not free.any():
                continue
            state_t, all_t = self._land(side)
            lx, ly = LAND_PAD_PX / 1920, LAND_PAD_PX / 1080
            land = rect_share(state_t, x0 - lx, x1 + lx, y0 - ly, y1 + ly)
            other = np.maximum(rect_share(all_t, x0 - lx, x1 + lx, y0 - ly, y1 + ly) - land, 0)
            default = (X == x_def) & (Y == y_def) & (k == 0)
            score = (land + OTHER_LAND_W * other + MOVE_W * np.hypot(X - x_def, (Y - y_def) * 9 / 16)
                     + LEAVE_DEFAULT * ~default + SWITCH_SIDE * k)
            score[~free] = np.inf
            i = np.unravel_index(np.argmin(score), score.shape)
            if best is None or score[i] < best[0]:
                best = (score[i], side, X[i], Y[i])
        return None if best is None else best[1:]

    def place_label(self, fig, avoid=()):
        """Etiketi yerleştirir (koşullar ve seçim için bkz. _search). avoid: etiketin binmemesi gereken, vurgu
        sırasında ekranda kalan bölgeler (x0, y0, x1, y1; ekran oranı, y aşağıdan yukarı). Blok hiçbir yere
        sığmazsa sırayla dener: istatistiği en fazla %25 küçültme, istatistiği iki satıra bölme; en son sığmayan
        satırları küçültür."""
        g = self.g
        texts = [self.t_name, self.t_sub, self.t_stat]
        r = fig.canvas.get_renderer()
        self._land_cache, self._avoid = {}, list(avoid)

        def width(t):
            return t.get_window_extent(renderer=r).width / fig.bbox.width if t.get_text() else 0.0

        sides = [g.label_side, "right" if g.label_side == "left" else "left"]
        room = max(self._room(s) for s in sides)
        base = self.t_stat.get_fontsize()

        def shrink_stat():
            w = width(self.t_stat)
            if w > room:
                self.t_stat.set_fontsize(max(base * STAT_MIN_SCALE, self.t_stat.get_fontsize() * room / w * 0.99))

        plan = self._search(fig, sides)
        if plan is None and self.t_stat.get_text():
            shrink_stat()
            plan = self._search(fig, sides)
        if plan is None and len(self.t_stat.get_text().split()) > 1:
            self.t_stat.set_text(split_two_lines(self.t_stat.get_text()))
            self.t_stat.set_fontsize(base)
            plan = self._search(fig, sides)
            if plan is None:
                shrink_stat()
                plan = self._search(fig, sides)
        if plan is None:  # son çare: sığmayan satırları en geniş boşluğa göre küçült
            side = max(sides, key=self._room)
            for t in texts:
                if width(t) > self._room(side):
                    fit_text(fig, t, self._room(side))
            plan = self._search(fig, [side])
        if plan is None:  # hiçbir koşul sağlanamıyor: varsayılan yer
            cam = g.focus_camera(sides[0])
            c, cy = to_screen(cam, g.focus_center)[0]
            plan = (sides[0], c + (-1 if sides[0] == "left" else 1) * LABEL_DX, cy + LABEL_DY * 16 / 9)

        side, sx, sy = plan
        g.set_label_side(side)
        cam = g.cam_focus
        fw = cam[2]
        lab_x, lab_y = cam[0] + (sx - 0.5) * fw, cam[1] + (sy - 0.5) * fw * 9 / 16
        if side == "right":
            ha, self.elbow = "left", (lab_x - ELBOW * fw, lab_y)
        else:
            ha, self.elbow = "right", (lab_x + ELBOW * fw, lab_y)
        for t, dy in zip(texts, LINE_DY):
            t.set_ha(ha)
            t.set_position((lab_x, lab_y + dy * fw))

    # ---------- kare kare ayarlar ----------
    def set_camera(self, cam):
        self.ax.set_xlim(cam[0] - cam[2] / 2, cam[0] + cam[2] / 2)
        self.ax.set_ylim(cam[1] - cam[2] * 9 / 32, cam[1] + cam[2] * 9 / 32)

    def _partial(self, t):
        main, cum = self.main, self.cum
        L = cum[-1] * t
        k = np.searchsorted(cum, L)
        if k == 0:
            return main[:1]
        k = min(k, len(main) - 1)
        f = (L - cum[k - 1]) / max(cum[k] - cum[k - 1], 1e-9)
        pt = main[k - 1] + (main[k] - main[k - 1]) * f
        return np.vstack([main[:k], pt])

    def set_border(self, d, head_alpha):
        """d: sınırın çizilen oranı (0–1); head_alpha: çizen ucun opaklığı."""
        if d > 0:
            pts = self._partial(ease(d))
            for ln in self.glow:
                ln.set_data(pts[:, 0], pts[:, 1])
            self.head.set_data([pts[-1, 0]], [pts[-1, 1]])
            self.head.set_alpha(head_alpha)
        else:
            for ln in self.glow:
                ln.set_data([], [])
            self.head.set_data([], [])
            self.head.set_alpha(0.0)

    def set_glow(self, soft):
        for ln, (_, a0) in zip(self.glow, GLOW_SPECS):
            ln.set_alpha(a0 * soft)

    def set_isles(self, alpha):
        for ln in self.isle_lines:
            ln.set_alpha(alpha)

    def set_counties(self, appear, focus_dim):
        """appear: her poligonun görünürlüğü (0–1); focus_dim: vurgu dışındaki county'lerin soluklaşma oranı (0–1).
        Soluklaşma renk tonunu korur: zemine karıştırmak yerine doygunluk ve parlaklık düşer (renk çamurlaşmaz)."""
        cols = self.base_rgba.copy()
        if focus_dim > 0:
            d = np.where(self.is_focus, 0.0, focus_dim)
            hsv = self.base_hsv.copy()
            hsv[:, 1] *= 1 - DIM_SAT * d
            # koyu renkler (ör. NOT ENOUGH DATA) zemin renginden daha karanlığa düşüp delik gibi görünmesin
            hsv[:, 2] = np.maximum(hsv[:, 2] * (1 - DIM_VAL * d), np.minimum(hsv[:, 2], self.surface_v))
            cols[:, :3] = mcolors.hsv_to_rgb(hsv)
            if self.focus_none:
                a = NONE_FOCUS_TINT * focus_dim
                cols[self.is_focus, :3] = self.base_rgba[self.is_focus, :3] * (1 - a) + self.accent_rgb * a
        cols[:, 3] = appear * 0.95
        self.c_coll.set_facecolors(cols)
        ec = self.edge.copy()
        ec[:, 3] = appear
        self.c_coll.set_edgecolors(ec)

    def set_focus(self, glow_on, pulse_t, leader, name, stat):
        """glow_on: kenar parlaması ve noktanın açılma oranı; pulse_t: nabız başlangıcından beri geçen süre
        (<=0 ise nabız yok); leader: bağlantı çizgisinin uzama oranı; name: ad ve alt yazı opaklığı;
        stat: istatistik opaklığı."""
        pulse = 0.55 + 0.45 * np.cos(pulse_t * 2 * np.pi * 0.9) if pulse_t > 0 else 0
        for ln, a0 in self.ch_glow:
            ln.set_alpha(a0 * glow_on * (0.35 + 0.65 * max(pulse, 0)))
        cx, cy = self.g.focus_center
        ex = cx + (self.elbow[0] - cx) * leader
        ey = cy + (self.elbow[1] - cy) * leader
        self.leader.set_data([cx, ex], [cy, ey])
        self.leader.set_alpha(0.9 * (leader > 0))
        self.dot.set_alpha(glow_on)
        self.t_name.set_alpha(name)
        self.t_sub.set_alpha(name)
        self.t_stat.set_alpha(stat)
