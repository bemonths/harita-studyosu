"""Harita sahnelerinin (state_map, county_focus) ortak parçaları: ayar tanımları, geometri, kameralar ve
çizim katmanları. Katmanlar state_map'teki sırayla oluşturulur; sıra değişirse görünüm de değişir."""
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.collections import PolyCollection

from engine import brand, framing, geo
from engine.params import Categories, Color, CountyAssign, CountySelect, Number, StateSelect, Text
from engine.scene import cap_scale, ease, fit_text

GLOW_SPECS = [(16, 0.05), (10, 0.10), (6, 0.22), (2.4, 1.0)]  # neon sınır: (çizgi kalınlığı, opaklık)


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


def focus_title(c):
    return (f"{c.name} {c.lsad}" if c.lsad else c.name).upper()


class MapGeometry:
    """Seçili eyaletin projekte edilmiş geometrisi, county boyaması ve kameralar.
    label_side: "left", "right" ya da "auto" (eyalete daha az binen taraf)."""

    def __init__(self, p, label_side="left"):
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
        self.cam_state = framing.state_frame(np.vstack(self.state_rings), p["zoom"], p["shift_x"], p["shift_y"])
        self.focus_idx = next((i for i, c in enumerate(cs) if c.fips == p["focus"]), None)
        self.label_side = None
        if self.focus_idx is not None:
            self.focus_pts = np.vstack(cs[self.focus_idx].rings)
            self.focus_center = self.focus_pts.mean(0)
            if label_side == "auto":
                label_side = framing.label_side(self.state_rings, self.focus_pts, self.cam_state[2], p["focus_zoom"])
            self.label_side = label_side
            self.cam_focus = framing.focus_frame(self.focus_pts, self.cam_state[2], p["focus_zoom"], label_side)


class MapLayers:
    """Harita çizim katmanları: enlem-boylam, ABD zemini, eyalet dolgusu, county'ler, neon sınır,
    vurgu parlaması ve etiket. Değerler update() içinde set_* metotlarıyla verilir (durumsuz)."""

    def __init__(self, fig, g, p, fonts):
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
            fw = g.cam_focus[2]
            if g.label_side == "right":
                lab_x, ha = cx + 0.19 * fw, "left"
                self.elbow = (lab_x - 0.01 * fw, cy + 0.06 * fw)
            else:
                lab_x, ha = cx - 0.19 * fw, "right"
                self.elbow = (lab_x + 0.01 * fw, cy + 0.06 * fw)
            lab_y = cy + 0.06 * fw
            self.leader = ax.plot([], [], color=C["text"], lw=1.6, alpha=0.0, zorder=9)[0]
            self.dot = ax.plot([cx], [cy], "o", color=C["text"], ms=9, alpha=0.0, zorder=9)[0]
            self.t_name = ax.text(lab_x, lab_y + 0.004 * fw, p["focus_name"] or focus_title(g.counties[g.focus_idx]),
                                  fontproperties=PLACE, fontsize=64 * PK, color=C["text"], ha=ha, va="bottom",
                                  alpha=0, zorder=10)
            fit_text(fig, self.t_name, 0.30)
            self.t_sub = ax.text(lab_x, lab_y - 0.004 * fw, p["focus_sub"], fontproperties=BAR, fontsize=24,
                                 color=C["muted"], ha=ha, va="top", alpha=0, zorder=10)
            key = g.c_key[g.focus_idx]
            self.t_stat = ax.text(lab_x, lab_y - 0.034 * fw, p["focus_stat"], fontproperties=BARB, fontsize=26,
                                  color=g.col[key] if key != "none" else NEON, ha=ha, va="top", alpha=0, zorder=10)

        self.bgc = np.array(mcolors.to_rgb(C["surface"]))
        self.edge = np.array([[*mcolors.to_rgba(C["bg_dark"])[:3], 1.0]] * len(g.c_owner))
        self.is_focus = g.c_owner == g.focus_idx if g.focus_idx is not None else np.zeros(len(g.c_owner), bool)

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
        """appear: her poligonun görünürlüğü (0–1); focus_dim: vurgu dışındaki county'lerin zemine soluklaşma oranı."""
        cols = self.base_rgba.copy()
        k = np.where(self.is_focus, 0.0, 0.62 * focus_dim)[:, None]
        cols[:, :3] = cols[:, :3] * (1 - k) + self.bgc * k
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
