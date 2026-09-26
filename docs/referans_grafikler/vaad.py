"""Vaat ve county soru kartı denemesi (The Housing Atlas).
Sahne A: girişteki vaat ekranı (4 soru kartı).
Sahne B: Lee County soru kartı -> cevaplar.
Çıktı: 1920x1080, 30 fps MP4 ve kontrol kareleri."""
import json, math, subprocess, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle
from matplotlib import patheffects as pe
from shapely.geometry import shape

A = "/home/claude/info/assets/"
C = dict(bg="#07111d", bg2="#102338", surface="#0e1c2e", line="#23405e", text="#f4ecdd",
         muted="#a9b4c2", accent="#ff7a1f", loss="#e0301e", gold="#e9b949")
F_PLACE = FontProperties(fname=A + "Cinzel.ttf")
F_NUM = FontProperties(fname=A + "Anton.ttf")
F_LAB = FontProperties(fname=A + "Barlow-SemiBold.ttf")
F_BOLD = FontProperties(fname=A + "Barlow-Bold.ttf")
W, H, FPS = 1920, 1080, 30

geo = json.load(open(A + "counties.json"))
FEAT = {f["id"]: f for f in geo["features"]}


def county_rings(fips):
    g = shape(FEAT[fips]["geometry"])
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    polys = sorted(polys, key=lambda p: -p.area)
    lat0 = g.centroid.y
    k = math.cos(math.radians(lat0))
    rings = [np.array([(x * k, y) for x, y in p.exterior.coords]) for p in polys if p.area > polys[0].area * 0.02]
    allp = np.vstack(rings)
    mn, mx = allp.min(0), allp.max(0)
    s = 1.0 / max(mx - mn)
    return [(r - mn) * s - (mx - mn) * s / 2 for r in rings]


RINGS = {f: county_rings(f) for f in ("12071", "12015", "12055")}


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def seg(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    yy, xx = np.mgrid[0:H:6, 0:W:6]
    d = np.hypot((xx - W * 0.5) / W, (yy - H * 0.55) / H)
    g = np.clip(1 - d * 1.6, 0, 1)[..., None]
    c1 = np.array(matplotlib.colors.to_rgb(C["bg"])); c2 = np.array(matplotlib.colors.to_rgb(C["bg2"]))
    ax.imshow(c1 + (c2 - c1) * g * 0.8, extent=(0, W, 0, H), origin="lower", zorder=0, interpolation="bilinear")
    return fig, ax


def txt(ax, x, y, s, size, font, color, ha="center", va="center", alpha=1.0, stroke=True):
    t = ax.text(x, y, s, fontproperties=font, fontsize=size, color=color, ha=ha, va=va, alpha=alpha, zorder=20)
    if stroke:
        t.set_path_effects([pe.withStroke(linewidth=6, foreground=C["bg"], alpha=0.9 * alpha)])
    return t


def glow_poly(ax, pts, color, alpha=1.0, fill=None, fill_alpha=0.0, z=5):
    if fill:
        ax.add_patch(Polygon(pts, closed=True, fc=fill, ec="none", alpha=fill_alpha * alpha, zorder=z))
    for lw, a in ((18, 0.05), (10, 0.12), (5, 0.35), (2.2, 1.0)):
        ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, alpha=a * alpha, solid_joinstyle="round", zorder=z + 1)


def draw_county(ax, fips, cx, cy, size, alpha=1.0, fill=None):
    for r in RINGS[fips]:
        glow_poly(ax, r * size + [cx, cy], C["accent"], alpha, fill=fill or C["accent"], fill_alpha=0.16)


def house_path(x, y, w, h, roof=0.42):
    """Tabanı (x,y), genişliği w, gövde yüksekliği h olan çatılı ev/sütun."""
    r = w * roof
    return np.array([(x, y), (x + w, y), (x + w, y + h), (x + w / 2, y + h + r), (x, y + h)])


def house_icon(ax, x, y, w, color, alpha=1.0, fill_alpha=0.2, window=True, z=6):
    pts = house_path(x, y, w, w * 0.62)
    ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", alpha=fill_alpha * alpha, zorder=z))
    for lw, a in ((9, 0.10), (4, 0.35), (2.2, 1.0)):
        ax.add_patch(Polygon(pts, closed=True, fc="none", ec=color, lw=lw, alpha=a * alpha, joinstyle="round", zorder=z + 1))
    if window:
        dw = w * 0.2
        ax.add_patch(Rectangle((x + w / 2 - dw / 2, y), dw, w * 0.3, fc=color, alpha=0.8 * alpha, zorder=z + 2))


def card(ax, x, y, w, h, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=26", fc=C["surface"],
                                ec=C["line"], lw=2, alpha=0.92 * alpha, zorder=2))


def qmark(ax, x, y, size, t, alpha=1.0):
    pulse = 1 + 0.06 * math.sin(t * 2 * math.pi * 0.9)
    txt(ax, x, y, "?", size * pulse, F_NUM, C["accent"], alpha=alpha)


def icon_row(ax, x, y, w_icon, gap, n_on, reveal, t, alpha=1.0):
    """10 ev simgesi; reveal 0..1 arası, n_on tanesi kırmızıya döner."""
    lit = int(round(n_on * reveal + 0.0001)) if reveal > 0 else 0
    for i in range(10):
        on = i < lit
        col = C["loss"] if on else C["line"]
        house_icon(ax, x + i * (w_icon + gap), y, w_icon, col, alpha, fill_alpha=0.55 if on else 0.25, window=False)


# ---------------- Sahne A: vaat ekranı ----------------

def arrow(ax, x0, x1, y, color, alpha):
    ax.plot([x0, x1 - 10], [y, y], color=color, lw=6, alpha=alpha, solid_capstyle="round", zorder=19)
    ax.add_patch(Polygon([(x1, y), (x1 - 26, y + 17), (x1 - 26, y - 17)], closed=True, fc=color, alpha=alpha, zorder=19))


def scene_a(t):
    fig, ax = new_fig()
    a0 = seg(t, 0.0, 0.6)
    txt(ax, W / 2, H - 110, "FLORIDA", 70, F_PLACE, C["text"], alpha=a0)
    txt(ax, W / 2, H - 180, "10 COUNTIES  ·  4 QUESTIONS", 28, F_LAB, C["muted"], alpha=a0)
    cw, ch, gap = 410, 600, 36
    x0 = (W - (4 * cw + 3 * gap)) / 2
    y0 = 130
    starts = [0.6, 1.4, 2.2, 3.0]
    for i, st in enumerate(starts):
        p = seg(t, st, st + 0.6)
        if p <= 0:
            continue
        x = x0 + i * (cw + gap)
        y = y0 - (1 - p) * 40
        card(ax, x, y, cw, ch, p)
        cx = x + cw / 2
        vy = y + 215
        if i == 0:
            house_icon(ax, cx - 100, y + 330, 200, C["accent"], p)
            txt(ax, x + 34, vy, "$580K", 58, F_NUM, C["text"], ha="left", alpha=p)
            arrow(ax, x + 250, x + 314, vy, C["muted"], p)
            qmark(ax, x + 356, vy, 84, t, p)
            txt(ax, cx, y + 100, "ONE HOUSE IN", 26, F_LAB, C["muted"], alpha=p)
            txt(ax, cx, y + 62, "FORT MYERS", 26, F_LAB, C["muted"], alpha=p)
        elif i == 1:
            draw_county(ax, "12015", cx, y + 430, 230, p)
            qmark(ax, cx - 92, vy, 84, t, p)
            txt(ax, cx - 50, vy, "HOMES", 60, F_NUM, C["text"], ha="left", alpha=p)
            txt(ax, cx, y + 100, "PULLED OFF", 26, F_LAB, C["muted"], alpha=p)
            txt(ax, cx, y + 62, "THE MARKET", 26, F_LAB, C["muted"], alpha=p)
        elif i == 2:
            iw, ig = 52, 14
            rx = cx - (5 * iw + 4 * ig) / 2
            for r_ in range(2):
                for c_ in range(5):
                    house_icon(ax, rx + c_ * (iw + ig), y + 440 - r_ * 80, iw, C["line"], p, fill_alpha=0.3, window=False)
            qmark(ax, cx - 70, vy, 84, t, p)
            txt(ax, cx - 30, vy, "IN 10", 60, F_NUM, C["text"], ha="left", alpha=p)
            txt(ax, cx, y + 100, "SELLERS CUT", 26, F_LAB, C["muted"], alpha=p)
            txt(ax, cx, y + 62, "THEIR PRICE", 26, F_LAB, C["muted"], alpha=p)
        else:
            draw_county(ax, "12055", cx, y + 430, 220, p)
            txt(ax, cx - 20, vy, "#1", 64, F_NUM, C["text"], ha="right", alpha=p)
            qmark(ax, cx + 40, vy, 84, t, p)
            txt(ax, cx, y + 100, "AND IT'S NOT", 26, F_LAB, C["muted"], alpha=p)
            txt(ax, cx, y + 62, "CAPE CORAL", 26, F_LAB, C["muted"], alpha=p)
    return fig


# ---------------- Sahne B: county soru kartı -> cevap ----------------
LEE = dict(fips="12071", name="LEE COUNTY", sub="CAPE CORAL  ·  FORT MYERS",
           homes=9351, cut10=3, peak=415, today=360)


def scene_b(t):
    fig, ax = new_fig()
    d = LEE
    a0 = seg(t, 0.0, 0.8)
    draw_county(ax, d["fips"], 440, 590, 440, a0)
    txt(ax, 440, 260, d["name"], 62, F_PLACE, C["text"], alpha=a0)
    txt(ax, 440, 196, d["sub"], 27, F_LAB, C["muted"], alpha=a0)
    rx, rw, rh = 860, 980, 250
    rows_y = [700, 420, 140]
    labels = ["HOMES FOR SALE", "SELLERS WHO CUT THEIR PRICE", "WHAT BUYERS PAY"]
    subs = ["AUGUST 2026", "AUGUST 2026", "MAY 2026 SALES"]
    reveal_at = [3.4, 5.0, 6.6]
    for i in range(3):
        p = seg(t, 0.4 + i * 0.25, 1.1 + i * 0.25)
        if p <= 0:
            continue
        y = rows_y[i]
        card(ax, rx, y, rw, rh, p)
        txt(ax, rx + 40, y + rh - 42, labels[i], 27, F_BOLD, C["text"], ha="left", alpha=p)
        txt(ax, rx + 40, y + 34, subs[i], 19, F_LAB, C["muted"], ha="left", alpha=p)
        shown = t >= reveal_at[i]
        r = seg(t, reveal_at[i], reveal_at[i] + 1.0)
        vx, vy = rx + rw - 50, y + 118
        if i == 0:
            house_icon(ax, rx + 40, y + 72, 105, C["accent"] if shown else C["line"], p)
            if not shown:
                qmark(ax, vx - 60, vy, 120, t, p)
            else:
                txt(ax, vx, vy, f"{int(d['homes'] * r):,}", 120, F_NUM, C["text"], ha="right", alpha=p)
        elif i == 1:
            iw, ig = 46, 14
            icon_row(ax, rx + 40, y + 95, iw, ig, d["cut10"], r if shown else 0, t, p)
            if not shown:
                txt(ax, vx, vy, "IN 10", 60, F_NUM, C["muted"], ha="right", alpha=p)
                qmark(ax, vx - 215, vy, 96, t, p)
            else:
                txt(ax, vx, vy, f"{d['cut10']} IN 10", 70, F_NUM, C["loss"], ha="right", alpha=p * min(1, r * 2))
        else:
            base, bw, hmax = y + 62, 80, 92
            pk = house_path(rx + 40, base, bw, hmax)
            ax.add_patch(Polygon(pk, closed=True, fc=C["gold"], alpha=0.35 * p, zorder=6))
            ax.add_patch(Polygon(pk, closed=True, fc="none", ec=C["gold"], lw=2.2, alpha=p, zorder=7))
            txt(ax, rx + 145, y + 140, f"${d['peak']}K", 58, F_NUM, C["gold"], ha="left", alpha=p)
            txt(ax, rx + 147, y + 80, "2022 PEAK", 20, F_LAB, C["muted"], ha="left", alpha=p)
            bx = rx + 390
            if not shown:
                pts = house_path(bx, base, bw, hmax)
                ax.add_patch(Polygon(pts, closed=True, fc="none", ec=C["line"], lw=2.5, ls=(0, (6, 5)), alpha=p, zorder=7))
                qmark(ax, bx + bw / 2, base + 50, 70, t, p)
                qmark(ax, bx + 160, y + 135, 90, t, p)
            else:
                hh = hmax * (1 - (1 - d["today"] / d["peak"]) * r)
                pts = house_path(bx, base, bw, hh)
                ax.add_patch(Polygon(pts, closed=True, fc=C["loss"], alpha=0.45 * p, zorder=6))
                ax.add_patch(Polygon(pts, closed=True, fc="none", ec=C["loss"], lw=2.2, alpha=p, zorder=7))
                cur = d["peak"] - (d["peak"] - d["today"]) * r
                txt(ax, bx + 105, y + 140, f"${cur:.0f}K", 58, F_NUM, C["loss"], ha="left", alpha=p)
                txt(ax, bx + 107, y + 80, "TODAY", 20, F_LAB, C["muted"], ha="left", alpha=p)
                if r > 0.6:
                    txt(ax, vx, y + 140, "−$55K", 58, F_NUM, C["loss"], ha="right", alpha=p * seg(t, reveal_at[i] + 0.6, reveal_at[i] + 1.1))
    return fig


def render(scene, dur, path, stills=()):
    n = int(dur * FPS)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                             "-crf", "18", path], stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS
        fig = scene(t)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        proc.stdin.write(buf.tobytes())
        for (ts, sp) in stills:
            if abs(t - ts) < 0.5 / FPS:
                fig.savefig(sp, dpi=100)
        plt.close(fig)
    proc.stdin.close(); proc.wait()


if __name__ == "__main__":
    which = sys.argv[1]
    out = "/home/claude/info/"
    if which == "a":
        render(scene_a, 6.0, out + "vaad_giris.mp4", stills=[(5.5, out + "vaad_giris.png")])
    else:
        render(scene_b, 9.5, out + "county_soru_karti.mp4",
               stills=[(2.5, out + "county_soru.png"), (9.2, out + "county_cevap.png")])
