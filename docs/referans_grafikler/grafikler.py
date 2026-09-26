"""The Housing Atlas — grafik örnekleri (gerçek Florida verisi, Ağustos/Mayıs 2026).
Her sahne tek bir fikri gösterir; oranlar gerçek, sütunlar sıfırdan başlar."""
import math, sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Wedge, Circle
from vaad import (C, F_PLACE, F_NUM, F_LAB, F_BOLD, W, H, FPS, new_fig, txt, seg, ease, house_path,
                  house_icon, render)


def header(ax, county, title, sub, a):
    txt(ax, 110, H - 105, county, 54, F_PLACE, C["text"], ha="left", alpha=a)
    txt(ax, 112, H - 172, title, 32, F_BOLD, C["text"], ha="left", alpha=a)
    txt(ax, 112, H - 215, sub, 22, F_LAB, C["muted"], ha="left", alpha=a)


def source(ax, s, a):
    txt(ax, 112, 58, s, 20, F_LAB, C["muted"], ha="left", alpha=a, stroke=False)


def house_bar(ax, x, base, w, h, color, alpha, fill=0.45, z=6):
    pts = house_path(x, base, w, max(h, 0.1))
    ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", alpha=fill * alpha, zorder=z))
    for lw, aa in ((8, 0.10), (2.4, 1.0)):
        ax.add_patch(Polygon(pts, closed=True, fc="none", ec=color, lw=lw, alpha=aa * alpha, joinstyle="round", zorder=z + 1))


def arrow_path(ax, pts, prog, color, alpha, lw=7):
    """pts: çizgi noktaları; prog 0..1 kadar çizilir, ucunda ok başı."""
    pts = np.asarray(pts, float)
    segs = np.hypot(*np.diff(pts, axis=0).T)
    L = segs.sum() * prog
    if L <= 0:
        return
    out = [pts[0]]
    acc = 0
    for i, s in enumerate(segs):
        if acc + s >= L:
            f = (L - acc) / s
            out.append(pts[i] + (pts[i + 1] - pts[i]) * f)
            break
        out.append(pts[i + 1]); acc += s
    out = np.array(out)
    for w_, aa in ((lw * 3, 0.12), (lw, 1.0)):
        ax.plot(out[:, 0], out[:, 1], color=color, lw=w_, alpha=aa * alpha, solid_capstyle="round", solid_joinstyle="round", zorder=15)
    if len(out) >= 2:
        p1, p0 = out[-1], out[-2]
        d = p1 - p0; n = np.hypot(*d)
        if n > 0:
            d /= n; nrm = np.array([-d[1], d[0]])
            tip = p1 + d * 18
            head = [tip, p1 - d * 26 + nrm * 22, p1 - d * 26 - nrm * 22]
            ax.add_patch(Polygon(head, closed=True, fc=color, alpha=alpha, zorder=16))


# ---------------- G1: Lee — satış fiyatı ev sütunları (çıkış ve iniş) ----------------
def g1(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "LEE COUNTY", "WHAT A TYPICAL HOME SOLD FOR", "MEDIAN SALE PRICE  ·  MAY OF EACH YEAR", a)
    source(ax, "SOURCE: REDFIN", a)
    yrs = list(range(2019, 2027)); vals = [243, 243, 319, 419, 411, 399, 368, 360]
    bw, gap = 128, 66; x0 = (W - (8 * bw + 7 * gap)) / 2; base = 170; hmax = 460; vmax = 450
    tops = []
    for i, (y, v) in enumerate(zip(yrs, vals)):
        g = seg(t, 0.5 + i * 0.3, 1.1 + i * 0.3)
        x = x0 + i * (bw + gap)
        h = hmax * v / vmax * g
        col = C["gold"] if y == 2022 else (C["loss"] if y > 2022 else C["line"])
        if y < 2022:
            col = "#5b7fa6"
        house_bar(ax, x, base, bw, h, col, a)
        roof = base + h + bw * 0.42
        tops.append((x + bw / 2, base + hmax * v / vmax + bw * 0.42))
        txt(ax, x + bw / 2, base - 38, str(y), 26, F_LAB, C["muted"], alpha=a)
        if g > 0.95:
            txt(ax, x + bw / 2, roof + 36, f"${v}K", 36, F_NUM, C["text"], alpha=min(1, (g - 0.95) * 20))
    pr = seg(t, 3.4, 4.4)
    pts = [(tops[3][0], tops[3][1] + 110)] + [(tx, ty + 110) for tx, ty in tops[4:]]
    arrow_path(ax, pts, pr, C["loss"], a)
    b = seg(t, 4.5, 5.0)
    txt(ax, W - 110, H - 140, "−$59K", 96, F_NUM, C["loss"], ha="right", alpha=b)
    txt(ax, W - 110, H - 215, "SINCE MAY 2022", 26, F_BOLD, C["text"], ha="right", alpha=b)
    return fig


# ---------------- G2: Osceola — satılık ev çizgisi (iniş çıkış) ----------------
def g2(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "OSCEOLA COUNTY", "HOMES FOR SALE", "EVERY AUGUST  ·  KISSIMMEE  ·  ST. CLOUD", a)
    source(ax, "SOURCE: REALTOR.COM VIA FRED", a)
    yrs = list(range(2016, 2027)); vals = [2445, 2380, 1991, 2075, 2278, 816, 1992, 2316, 3801, 4282, 4135]
    x0, x1, y0, y1, vmax = 190, 1560, 170, 740, 4500
    xs = [x0 + (x1 - x0) * i / (len(yrs) - 1) for i in range(len(yrs))]
    ys = [y0 + (y1 - y0) * v / vmax for v in vals]
    ax.plot([x0 - 30, x1 + 60], [y0, y0], color=C["line"], lw=2, alpha=a, zorder=3)
    for i, yr in enumerate(yrs):
        txt(ax, xs[i], y0 - 36, str(yr)[2:] if i not in (0, len(yrs) - 1) else str(yr), 24, F_LAB, C["muted"], alpha=a)
    ly = y0 + (y1 - y0) * 2075 / vmax
    ax.plot([x0 - 30, x1 + 60], [ly, ly], color=C["muted"], lw=2, ls=(0, (8, 7)), alpha=0.7 * a, zorder=4)
    txt(ax, x1 + 60, ly - 30, "2019 LEVEL: 2,075", 24, F_LAB, C["muted"], ha="right", alpha=a)
    pr = seg(t, 0.7, 4.2)
    arrow_path(ax, list(zip(xs, ys)), pr, C["accent"], a, lw=6)
    n_shown = int(pr * (len(xs) - 1) + 1e-6) + 1
    for i in range(min(n_shown, len(xs) - 1)):
        ax.add_patch(Circle((xs[i], ys[i]), 9, fc=C["accent"], ec=C["bg"], lw=3, alpha=a, zorder=17))
    if pr > 0.52:
        txt(ax, xs[5], ys[5] - 44, "816", 32, F_NUM, C["muted"], alpha=min(1, (pr - 0.52) * 8))
    b = seg(t, 4.3, 4.9)
    txt(ax, xs[-1] + 20, ys[-1] + 95, "4,135", 80, F_NUM, C["text"], ha="right", alpha=b)
    txt(ax, W - 110, H - 140, "2×", 110, F_NUM, C["accent"], ha="right", alpha=b)
    txt(ax, W - 110, H - 215, "THE 2019 LEVEL", 26, F_BOLD, C["text"], ha="right", alpha=b)
    return fig


# ---------------- G3: Pasco / Florida / ABD — ilerleme çubukları ----------------
def rbar(ax, x, y, w, h, color, alpha, z=5):
    if w < h:
        w = h
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={h/2}", fc=color, ec="none", alpha=alpha, zorder=z))


def g3(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "PASCO COUNTY", "SELLERS WHO CUT THEIR PRICE", "OUT OF EVERY 100 HOMES FOR SALE  ·  AUGUST 2026", a)
    source(ax, "SOURCE: REALTOR.COM VIA FRED", a)
    rows = [("PASCO COUNTY", 44, C["accent"]), ("FLORIDA", 31, "#5b7fa6"), ("UNITED STATES", 35, "#5b7fa6")]
    x0, wmax, bh = 560, 1000, 74
    for i, (lab, v, col) in enumerate(rows):
        y = 620 - i * 190
        g = seg(t, 0.7 + i * 0.6, 1.9 + i * 0.6)
        txt(ax, x0 - 40, y + bh / 2, lab, 34, F_BOLD, C["text"] if i == 0 else C["muted"], ha="right", alpha=a)
        rbar(ax, x0, y, wmax, bh, C["line"], 0.55 * a)
        rbar(ax, x0, y, wmax * v / 100 * g, bh, col, 0.95 * a, z=6)
        if g > 0.9:
            txt(ax, x0 + wmax * v / 100 + 30, y + bh / 2, f"{round(v * g)} OF 100", 50, F_NUM,
                C["text"], ha="left", alpha=min(1, (g - 0.9) * 10))
    return fig


# ---------------- G4: Collier — halka ----------------
def g4(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "COLLIER COUNTY", "WHAT BUYERS REALLY PAY", "NAPLES  ·  MAY 2026 SALES", a)
    source(ax, "SOURCE: REDFIN", a)
    cx, cy, R, w = W / 2, 470, 300, 56
    ax.add_patch(Wedge((cx, cy), R, 0, 360, width=w, fc=C["line"], alpha=0.6 * a, zorder=4))
    g = seg(t, 0.8, 3.0)
    v = 94.3 * g
    ax.add_patch(Wedge((cx, cy), R, 90 - 360 * v / 100, 90, width=w, fc=C["accent"], alpha=a, zorder=5))
    ax.add_patch(Wedge((cx, cy), R + 14, 90 - 360, 90 - 360 * 94.3 / 100, width=w + 28, fc=C["loss"],
                       alpha=a * seg(t, 3.1, 3.6), zorder=5))
    txt(ax, cx, cy + 30, f"${v:.0f}", 190, F_NUM, C["text"], alpha=a)
    txt(ax, cx, cy - 110, "OF EVERY $100 ASKED", 30, F_BOLD, C["muted"], alpha=a)
    b = seg(t, 3.4, 3.9)
    txt(ax, cx + R + 70, cy + R - 30, "$6 OFF", 64, F_NUM, C["loss"], ha="left", alpha=b)
    txt(ax, cx + R + 72, cy + R - 90, "AT THE TABLE", 26, F_BOLD, C["text"], ha="left", alpha=b)
    return fig


# ---------------- G5: Highlands ve Florida — termometre ----------------
def g5(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "HIGHLANDS COUNTY", "HOW LONG TO SELL EVERY HOME FOR SALE", "IF NO NEW HOME WERE LISTED  ·  MAY 2026", a)
    source(ax, "SOURCE: REDFIN", a)
    base, top, vmax = 170, 760, 8.0
    def yv(m): return base + (top - base) * m / vmax
    for m, lab in ((3, "SELLER'S MARKET: UNDER 3"), (6, "BUYER'S MARKET: OVER 6")):
        ax.plot([480, 1330], [yv(m), yv(m)], color=C["loss"] if m == 6 else "#5b7fa6", lw=2.5, ls=(0, (8, 7)), alpha=0.8 * a, zorder=3)
        txt(ax, 1350, yv(m), lab, 24, F_BOLD, C["loss"] if m == 6 else C["muted"], ha="left", alpha=a)
    tubes = [("HIGHLANDS", 6.2, C["loss"], 640), ("FLORIDA", 4.7, "#5b7fa6", 1030)]
    tw = 120
    for i, (lab, m, col, x) in enumerate(tubes):
        g = seg(t, 0.8 + i * 0.8, 2.6 + i * 0.8)
        ax.add_patch(FancyBboxPatch((x - tw / 2, base), tw, top - base, boxstyle=f"round,pad=0,rounding_size={tw/2}",
                                    fc=C["surface"], ec=C["line"], lw=3, alpha=a, zorder=4))
        hh = (top - base) * m / vmax * g
        ax.add_patch(FancyBboxPatch((x - tw / 2 + 14, base + 14), tw - 28, max(hh - 28, 1),
                                    boxstyle=f"round,pad=0,rounding_size={(tw-28)/2}", fc=col, ec="none", alpha=0.95 * a, zorder=5))
        txt(ax, x, base - 40, lab, 30, F_BOLD, C["text"], alpha=a)
        txt(ax, x + tw / 2 + 24, base + hh, f"{m * g:.1f}", 64, F_NUM, C["text"], ha="left", alpha=a * min(1, g * 3))
        if g > 0.95:
            txt(ax, x + tw / 2 + 26, base + hh - 52, "MONTHS", 22, F_BOLD, C["muted"], ha="left", alpha=a)
    return fig


# ---------------- G6: on county — aylık stok karşılaştırması ----------------
def g6(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "FLORIDA  ·  10 COUNTIES", "HOW MANY MONTHS TO SELL EVERY HOME", "IF NO NEW HOME WERE LISTED  ·  MAY 2026", a)
    source(ax, "SOURCE: REDFIN", a)
    data = [("MIAMI-DADE", 7.7), ("WALTON", 6.3), ("HIGHLANDS", 6.2), ("ST. LUCIE", 6.1), ("OSCEOLA", 5.6),
            ("COLLIER", 5.3), ("LEE", 4.9), ("CHARLOTTE", 4.3), ("POLK", 4.2), ("PASCO", 3.7)]
    x0, wmax, vmax, rh, bh = 520, 1150, 8.0, 64, 40
    y_top = 745
    x6 = x0 + wmax * 6 / vmax
    ax.plot([x6, x6], [y_top - 9 * rh - 30, y_top + 60], color=C["loss"], lw=2.5, ls=(0, (8, 7)), alpha=0.8 * a, zorder=3)
    txt(ax, x6 + 14, y_top + 70, "BUYER'S MARKET: 6+ MONTHS", 22, F_BOLD, C["loss"], ha="left", alpha=a)
    for i, (lab, m) in enumerate(data):
        y = y_top - i * rh
        g = seg(t, 0.6 + i * 0.18, 1.6 + i * 0.18)
        col = C["loss"] if m >= 6 else "#5b7fa6"
        txt(ax, x0 - 30, y, lab, 28, F_BOLD, C["text"], ha="right", alpha=a)
        rbar(ax, x0, y - bh / 2, wmax * m / vmax * g, bh, col, 0.95 * a)
        if g > 0.9:
            txt(ax, x0 + wmax * m / vmax + 20, y, f"{m:.1f}", 36, F_NUM, C["text"], ha="left", alpha=min(1, (g - 0.9) * 10))
    return fig


# ---------------- G7: Charlotte — ev ızgarası (satılık ev azaldı) ----------------
def g7(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "CHARLOTTE COUNTY", "HOMES FOR SALE", "PUNTA GORDA  ·  PORT CHARLOTTE  ·  EACH HOUSE = 100 HOMES", a)
    source(ax, "SOURCE: REALTOR.COM VIA FRED  ·  AUGUST 2025 AND AUGUST 2026", a)
    cols, rows, iw, gx, gy = 12, 3, 88, 34, 60
    x0 = 170; y0 = 575
    fade_idx = [35, 34, 33, 23, 22, 11, 32, 21, 10]
    for k in range(36):
        r_, c_ = divmod(k, cols)
        x = x0 + c_ * (iw + gx); y = y0 - r_ * (iw * 0.62 + iw * 0.42 + gy)
        app = seg(t, 0.4 + k * 0.025, 0.8 + k * 0.025)
        if app <= 0:
            continue
        col, al = C["accent"], app
        if k in fade_idx:
            j = fade_idx.index(k); st = 2.4 + j * 0.28
            f = seg(t, st, st + 0.35)
            if f > 0:
                col = C["loss"]; al = app * (1 - 0.8 * f)
        house_icon(ax, x, y, iw, col, al * a, fill_alpha=0.35, window=False)
    nf = sum(1 for j in range(9) if t >= 2.4 + j * 0.28 + 0.35)
    val = 3625 - round((3625 - 2705) * nf / 9)
    yr = "AUGUST 2025" if t < 2.4 else "AUGUST 2026"
    txt(ax, W - 110, H - 140, f"{val:,}", 110, F_NUM, C["text"], ha="right", alpha=a)
    txt(ax, W - 110, H - 240, yr, 26, F_BOLD, C["muted"], ha="right", alpha=a)
    b = seg(t, 5.2, 5.7)
    txt(ax, W / 2, 150, "920 FEWER HOMES FOR SALE IN ONE YEAR", 44, F_NUM, C["loss"], alpha=b)
    return fig


# ---------------- G8: Polk — yükselen ev sütunları ve ok ----------------
def g8(t):
    fig, ax = new_fig(); a = seg(t, 0, 0.5)
    header(ax, "POLK COUNTY", "HOMES FOR SALE", "EVERY AUGUST  ·  LAKELAND  ·  HAINES CITY", a)
    source(ax, "SOURCE: REALTOR.COM VIA FRED", a)
    yrs = list(range(2019, 2027)); vals = [2931, 2078, 1082, 2564, 2769, 4543, 4912, 4771]
    bw, gap = 128, 66; x0 = (W - (8 * bw + 7 * gap)) / 2; base = 170; hmax = 480; vmax = 5200
    tops = []
    for i, (y, v) in enumerate(zip(yrs, vals)):
        g = seg(t, 0.5 + i * 0.28, 1.1 + i * 0.28)
        x = x0 + i * (bw + gap)
        h = hmax * v / vmax * g
        col = C["accent"] if y >= 2024 else "#5b7fa6"
        house_bar(ax, x, base, bw, h, col, a)
        tops.append((x + bw / 2, base + hmax * v / vmax + bw * 0.42))
        txt(ax, x + bw / 2, base - 38, str(y), 26, F_LAB, C["muted"], alpha=a)
        if g > 0.95:
            txt(ax, x + bw / 2, base + h + bw * 0.42 + 34, f"{v:,}", 32, F_NUM, C["text"], alpha=min(1, (g - 0.95) * 20))
    pr = seg(t, 3.2, 4.3)
    pts = [(tops[2][0], tops[2][1] + 110), (tops[5][0], tops[5][1] + 110), (tops[7][0], tops[7][1] + 110)]
    arrow_path(ax, pts, pr, C["gold"], a)
    b = seg(t, 4.4, 4.9)
    txt(ax, W - 110, H - 140, "+1,840", 96, F_NUM, C["accent"], ha="right", alpha=b)
    txt(ax, W - 110, H - 215, "MORE THAN AUGUST 2019", 26, F_BOLD, C["text"], ha="right", alpha=b)
    return fig


SCENES = {"g1": (g1, 7.0), "g2": (g2, 7.0), "g3": (g3, 6.0), "g4": (g4, 6.0),
          "g5": (g5, 6.5), "g6": (g6, 6.5), "g7": (g7, 7.5), "g8": (g8, 7.0)}
NAMES = {"g1": "01_lee_fiyat_sutunlari", "g2": "02_osceola_stok_cizgisi", "g3": "03_pasco_ilerleme_cubuklari",
         "g4": "04_collier_halka", "g5": "05_highlands_termometre", "g6": "06_on_county_aylik_stok",
         "g7": "07_charlotte_ev_izgarasi", "g8": "08_polk_yukselen_sutunlar"}

if __name__ == "__main__":
    out = "/home/claude/info/graf/"
    for key in sys.argv[1:]:
        fn, dur = SCENES[key]
        render(fn, dur, out + NAMES[key] + ".mp4", stills=[(dur - 0.3, out + NAMES[key] + ".png")])
        print("ok", key)
