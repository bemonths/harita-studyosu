import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("out", exist_ok=True)

from scene_common import ffmpeg_exe

import os, subprocess, datetime as dt, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

W, H, FPS = 1920, 1080, 30
DUR = 11.5
N = int(DUR * FPS)
OUT = "out/scene_b.mp4"
TEST = os.environ.get("TEST")
test_frames = [int(float(x) * FPS) for x in TEST.split(",")] if TEST else None

BEBAS = fm.FontProperties(fname="fonts/BebasNeue-Regular.ttf")
BAR = fm.FontProperties(fname="fonts/Barlow-SemiBold.ttf")
BARB = fm.FontProperties(fname="fonts/Barlow-Bold.ttf")
NEON, RED, AMBER, MUTED = "#3ee6ff", "#ff5a4f", "#ffb020", "#8fb0d8"

# ---------- data (FredPull listings_FL.csv, Lee County) ----------
listed = dt.date(2024, 8, 15)
today = dt.date(2026, 9, 23)
events = [(listed, 580000), (dt.date(2024, 9, 11), 574999), (dt.date(2024, 12, 19), 565000), (dt.date(2025, 5, 13), 540000),
          (dt.date(2025, 10, 15), 510000), (dt.date(2026, 2, 11), 490000), (dt.date(2026, 3, 9), 489000),
          (dt.date(2026, 5, 4), 475000), (dt.date(2026, 6, 4), 430000), (dt.date(2026, 6, 30), 410000)]
paid, paid_year = 310000, 2017
X = np.array([(d - listed).days for d, _ in events], float)
P = np.array([p for _, p in events], float)
END = (today - listed).days  # 769

def price_at(x):
    return P[np.searchsorted(X, x, side="right") - 1]

def path_upto(x):
    xs, ys = [X[0]], [P[0]]
    for i in range(1, len(X)):
        if X[i] > x:
            break
        xs += [X[i], X[i]]; ys += [P[i - 1], P[i]]
    xs.append(x); ys.append(price_at(x))
    return np.array(xs), np.array(ys)

def ease(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def seg(t, a, b):
    return np.clip((t - a) / (b - a), 0, 1)

# ---------- figure ----------
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
fig.patch.set_alpha(0)
BG0, BG1 = np.array([7, 13, 24]) / 255, np.array([16, 30, 52]) / 255
yy, xx = np.mgrid[0:H, 0:W]
g = np.clip(1 - np.sqrt(((xx - W * 0.4) / W) ** 2 + ((yy - H * 0.5) / H) ** 2) * 1.6, 0, 1)[..., None]
fig.figimage(np.dstack([BG0 * (1 - g) + BG1 * g, np.ones((H, W))]), 0, 0, zorder=-10)

ax = fig.add_axes([0.07, 0.12, 0.58, 0.56])
ax.patch.set_alpha(0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_xlim(-15, END + 25); ax.set_ylim(280000, 620000)
ax.tick_params(colors=MUTED, length=0, labelsize=18)
ax.set_yticks([300000, 400000, 500000, 600000])
ax.set_yticklabels(["$300K", "$400K", "$500K", "$600K"], fontproperties=BAR, fontsize=20)
xt = [0, (dt.date(2025, 1, 1) - listed).days, (dt.date(2026, 1, 1) - listed).days, END]
ax.set_xticks(xt)
ax.set_xticklabels(["AUG 2024", "2025", "2026", "TODAY"], fontproperties=BAR, fontsize=20)
grid = [ax.axhline(v, color="#1f3050", lw=1, zorder=0) for v in [300000, 400000, 500000, 600000]]

glow_specs = [(14, 0.06), (8, 0.14), (4.5, 0.3), (2.4, 1.0)]
glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_joinstyle="miter", zorder=5)[0] for w, a in glow_specs]
head = ax.plot([], [], "o", color="white", ms=11, zorder=7)[0]
head_ring = ax.plot([], [], "o", color=NEON, ms=26, alpha=0.25, zorder=6)[0]
fill = [None]

cut_dots, cut_labels = [], []
for i in range(1, len(X)):
    d = P[i - 1] - P[i]
    cut_dots.append(ax.plot([X[i]], [P[i]], "o", color=RED, ms=9, alpha=0, zorder=8)[0])
    above = i % 2 == 1
    yv = P[i - 1] + 14000 if above else P[i] - 24000
    cut_labels.append(ax.text(X[i] if above else X[i] - 6, yv, f"−${round(d / 1000):.0f}K", fontproperties=BARB, fontsize=20, color=RED,
                              ha="center" if above else "right", va="center", alpha=0, zorder=9))

paid_line = ax.plot([], [], color=AMBER, lw=2.4, ls=(0, (6, 5)), zorder=4)[0]
paid_txt = ax.text(10, paid + 9000, f"OWNER PAID ${paid:,} IN {paid_year}", fontproperties=BARB, fontsize=22, color=AMBER,
                   ha="left", va="bottom", alpha=0, zorder=9)
brk = ax.annotate("", xy=(END + 8, paid), xytext=(END + 8, P[-1]),
                  arrowprops=dict(arrowstyle="<->", color=AMBER, lw=2.2), alpha=0, zorder=9)
brk_txt = ax.text(END - 12, (paid + P[-1]) / 2, "STILL +$100,000\nABOVE WHAT THEY PAID", fontproperties=BARB, fontsize=22,
                  color=AMBER, ha="right", va="center", alpha=0, zorder=9, linespacing=1.1)

# header
K = fig.text(0.07, 0.905, "LEE COUNTY  ·  FORT MYERS", fontproperties=BAR, fontsize=26, color=NEON, alpha=0)
T = fig.text(0.068, 0.885, "ONE HOUSE. NINE PRICE CUTS.", fontproperties=BEBAS, fontsize=92, color="white", alpha=0, va="top")
S = fig.text(0.07, 0.765, "4 bedrooms  ·  built 2000  ·  listed August 2024", fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)

# right panel
PX = 0.73
def block(y, label, big):
    l = fig.text(PX, y, label, fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)
    v = fig.text(PX - 0.003, y - 0.012, "", fontproperties=BEBAS, fontsize=big, color="white", alpha=0, va="top")
    return l, v
L1, V1 = block(0.66, "ASKING PRICE", 118)
L2, V2 = block(0.44, "DAYS FOR SALE", 96)
L3, V3 = block(0.25, "PRICE CUTS", 96)
sep = [fig.add_artist(plt.Line2D([PX, 0.95], [y, y], transform=fig.transFigure, color="#1f3050", lw=1.2, alpha=0)) for y in (0.475, 0.285)]

writer = None if TEST else subprocess.Popen([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                                             "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)

for fi in (range(N) if not TEST else range(max(test_frames) + 1)):
    t = fi / FPS
    ha = ease(seg(t, 0.0, 0.8))
    K.set_alpha(ha); T.set_alpha(ha); S.set_alpha(ease(seg(t, 0.3, 1.1)))
    pa = ease(seg(t, 0.6, 1.6))
    for o in (L1, L2, L3, V1, V2, V3):
        o.set_alpha(pa)
    for s in sep:
        s.set_alpha(pa)
    axa = ease(seg(t, 1.0, 2.2))
    for gl in grid:
        gl.set_alpha(axa)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_alpha(axa)

    prog = seg(t, 2.4, 8.4)
    xh = END * prog
    if t >= 2.4:
        xs, ys = path_upto(xh)
        for ln in glow:
            ln.set_data(xs, ys)
        head.set_data([xh], [ys[-1]]); head_ring.set_data([xh], [ys[-1]])
        if fill[0] is not None:
            fill[0].remove()
        fill[0] = ax.fill_between(xs, ys, 280000, color=NEON, alpha=0.07, lw=0, zorder=2)
    cur = price_at(xh) if t >= 2.4 else P[0]
    ncut = int(np.sum(X[1:] <= xh)) if t >= 2.4 else 0
    flash = 0.0
    for i in range(1, len(X)):
        dtc = (xh - X[i]) / END * 6.0  # seconds since head passed this cut
        a = ease(np.clip(dtc / 0.25, 0, 1)) if xh >= X[i] and t >= 2.4 else 0
        cut_dots[i - 1].set_alpha(a)
        cut_labels[i - 1].set_alpha(a)
        if 0 <= dtc < 0.35 and xh >= X[i]:
            flash = max(flash, 1 - dtc / 0.35)
    V1.set_text(f"${int(cur):,}")
    V1.set_color(tuple(np.array(matplotlib.colors.to_rgb("white")) * (1 - flash) + np.array(matplotlib.colors.to_rgb(RED)) * flash))
    V2.set_text(f"{int(round(xh)) if t >= 2.4 else 0}")
    V3.set_text(f"{ncut}")

    pl = ease(seg(t, 8.7, 9.5))
    paid_line.set_data([0, END * pl], [paid, paid])
    paid_txt.set_alpha(ease(seg(t, 9.0, 9.6)))
    ba = ease(seg(t, 9.7, 10.3))
    brk.arrow_patch.set_alpha(ba); brk_txt.set_alpha(ba)

    if TEST:
        if fi in test_frames:
            fig.savefig(f"out/test_b_{fi / FPS:.1f}.png", dpi=100)
        continue
    fig.canvas.draw()
    writer.stdin.write(bytes(fig.canvas.buffer_rgba()))
    if fi % 60 == 0:
        print("frame", fi, "/", N, flush=True)

if writer:
    writer.stdin.close(); writer.wait()
print("done", OUT)
