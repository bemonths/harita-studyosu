import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("out", exist_ok=True)

from scene_common import ffmpeg_exe

import json, subprocess, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os, sys
from matplotlib.collections import PolyCollection
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

W, H, FPS = 1920, 1080, 30
DUR = 13.0
N = int(DUR * FPS)
OUT = "out/scene_a.mp4"

for f in ["BebasNeue-Regular", "Barlow-Regular", "Barlow-SemiBold", "Barlow-Bold"]:
    fm.fontManager.addfont(f"fonts/{f}.ttf")
BEBAS = fm.FontProperties(fname="fonts/BebasNeue-Regular.ttf")
BAR = fm.FontProperties(fname="fonts/Barlow-SemiBold.ttf")
BARB = fm.FontProperties(fname="fonts/Barlow-Bold.ttf")

# ---------- palette ----------
BG0 = np.array([7, 13, 24]) / 255
BG1 = np.array([16, 30, 52]) / 255
NEON = "#3ee6ff"
COL = {
    "buyers": "#ff5a4f",
    "price": "#ffb020",
    "weak": "#e6d45a",
    "stable": "#3b6694",
    "none": "#16233a",
}
LABEL = {
    "buyers": "BUYERS PULLED BACK",
    "price": "PRICES BREAKING",
    "weak": "WEAKENING",
    "stable": "HOLDING STEADY",
    "none": "NOT ENOUGH DATA",
}
SIGNAL = {}
for n in ["Highlands", "St. Lucie", "Polk", "Osceola", "Clay", "Okaloosa", "Pasco", "Alachua", "Santa Rosa", "Miami-Dade"]:
    SIGNAL[n] = "buyers"
for n in ["Charlotte", "Collier", "Lee", "Manatee", "Sarasota"]:
    SIGNAL[n] = "price"
for n in ["Bay", "Walton", "Monroe"]:
    SIGNAL[n] = "weak"
for n in ["Sumter", "Pinellas", "Broward", "Lake", "Marion", "Escambia", "Hernando", "Brevard", "Duval", "Indian River",
          "Martin", "Nassau", "Volusia", "Citrus", "Orange", "Flagler", "Palm Beach", "St. Johns", "Hillsborough", "Seminole", "Leon"]:
    SIGNAL[n] = "stable"

# ---------- projection ----------
def albers(lon, lat, lon0=-96, lat0=23, p1=29.5, p2=45.5):
    lon, lat = np.radians(lon), np.radians(lat)
    l0, f0, f1, f2 = map(np.radians, (lon0, lat0, p1, p2))
    n = (np.sin(f1) + np.sin(f2)) / 2
    C = np.cos(f1) ** 2 + 2 * n * np.sin(f1)
    r0 = np.sqrt(C - 2 * n * np.sin(f0)) / n
    th = n * (lon - l0)
    r = np.sqrt(C - 2 * n * np.sin(lat)) / n
    return r * np.sin(th), r0 - r * np.cos(th)

def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon":
        return [np.array(c[0], float)]
    if t == "MultiPolygon":
        return [np.array(p[0], float) for p in c]
    return []

def proj(ring):
    x, y = albers(ring[:, 0], ring[:, 1])
    return np.column_stack([x, y])

outl = json.load(open("state_outlines.json", encoding="utf-8"))
us_polys, fl_rings = [], []
for st, rs in outl.items():
    for r in rs:
        p = proj(np.array(r, float))
        us_polys.append(p)
        if st == "12":
            fl_rings.append(p)

counties = [f for f in json.load(open("counties.json", encoding="utf-8"))["features"] if f["properties"]["STATE"] == "12"]
c_polys, c_owner, c_names = [], [], []
for i, f in enumerate(counties):
    c_names.append(f["properties"]["NAME"])
    for r in rings(f["geometry"]):
        c_polys.append(proj(r))
        c_owner.append(i)
c_owner = np.array(c_owner)

# ---------- extents ----------
allus = np.vstack(us_polys)
flall = np.vstack(fl_rings)

def box(pts, pad, dx=0.0, dy=0.0, scale=1.0):
    xmin, ymin = pts.min(0); xmax, ymax = pts.max(0)
    w = max(xmax - xmin, (ymax - ymin) * 16 / 9) * (1 + pad) * scale
    return np.array([(xmin + xmax) / 2 + dx * w, (ymin + ymax) / 2 + dy * w, w])

CAM_US = box(allus, 0.06)
CAM_FL = box(flall, 0.42, dx=-0.17, dy=-0.035)
ch_idx = c_names.index("Charlotte")
ch_pts = np.vstack([c_polys[k] for k in np.where(c_owner == ch_idx)[0]])
ch_center = ch_pts.mean(0)
CAM_CH = np.array([ch_center[0] - 0.06 * CAM_FL[2] * 0.55, ch_center[1] + 0.02 * CAM_FL[2], CAM_FL[2] * 0.55])

def ease(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def cam_lerp(a, b, t):
    e = ease(t)
    c = a[:2] + (b[:2] - a[:2]) * e
    w = np.exp(np.log(a[2]) + (np.log(b[2]) - np.log(a[2])) * e)
    return np.array([c[0], c[1], w])

def seg(t, a, b):
    return np.clip((t - a) / (b - a), 0, 1)

# ---------- figure ----------
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
fig.patch.set_alpha(0)
yy, xx = np.mgrid[0:H, 0:W]
d = np.sqrt(((xx - W * 0.6) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
g = np.clip(1 - d * 1.6, 0, 1)[..., None]
bg = (BG0 * (1 - g) + BG1 * g)
fig.figimage(np.dstack([bg, np.ones((H, W))]), 0, 0, zorder=-10)

ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off(); ax.patch.set_alpha(0)

# graticule
for lon in range(-125, -64, 5):
    la = np.linspace(20, 52, 120); x, y = albers(np.full_like(la, lon), la)
    ax.plot(x, y, color="#1c2c47", lw=0.6, alpha=0.5, zorder=1)
for lat in range(20, 55, 5):
    lo = np.linspace(-130, -60, 200); x, y = albers(lo, np.full_like(lo, lat))
    ax.plot(x, y, color="#1c2c47", lw=0.6, alpha=0.5, zorder=1)

us_coll = PolyCollection(us_polys, facecolors="#0f1b2e", edgecolors="#2b3f60", linewidths=0.8, zorder=2)
ax.add_collection(us_coll)

fl_fill = PolyCollection(fl_rings, facecolors=NEON, edgecolors="none", alpha=0.0, zorder=3)
ax.add_collection(fl_fill)

base_rgba = np.array([matplotlib.colors.to_rgba(COL[SIGNAL.get(c_names[o], "none")]) for o in c_owner])
c_coll = PolyCollection(c_polys, facecolors=base_rgba, edgecolors="#070d18", linewidths=0.9, zorder=4)
ax.add_collection(c_coll)

# neon outline on the main ring
main = max(fl_rings, key=len)
segl = np.hypot(*np.diff(main, axis=0).T)
cum = np.concatenate([[0], np.cumsum(segl)])
glow_specs = [(16, 0.05), (10, 0.10), (6, 0.22), (2.4, 1.0)]
glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_capstyle="round", zorder=6)[0] for w, a in glow_specs]
isles = [r for r in fl_rings if r is not main]
isle_lines = [ax.plot(r[:, 0], r[:, 1], color=NEON, lw=1.4, alpha=0.0, zorder=6)[0] for r in isles]
head = ax.plot([], [], "o", color="white", ms=7, alpha=0.0, zorder=7)[0]

def partial(t):
    L = cum[-1] * t
    k = np.searchsorted(cum, L)
    if k == 0:
        return main[:1]
    k = min(k, len(main) - 1)
    f = (L - cum[k - 1]) / max(cum[k] - cum[k - 1], 1e-9)
    p = main[k - 1] + (main[k] - main[k - 1]) * f
    return np.vstack([main[:k], p])

# Charlotte highlight
ch_rings = [c_polys[k] for k in np.where(c_owner == ch_idx)[0]]
ch_glow = []
for r in ch_rings:
    for w, a in [(12, 0.08), (6, 0.2), (2.2, 1.0)]:
        ch_glow.append((ax.plot(r[:, 0], r[:, 1], color="#ffffff", lw=w, alpha=0.0, zorder=8)[0], a))

# label with leader line
lab_x = ch_center[0] - 0.19 * CAM_CH[2]
lab_y = ch_center[1] + 0.06 * CAM_CH[2]
leader = ax.plot([], [], color="white", lw=1.6, alpha=0.0, zorder=9)[0]
dot = ax.plot([ch_center[0]], [ch_center[1]], "o", color="white", ms=9, alpha=0.0, zorder=9)[0]
t_name = ax.text(lab_x, lab_y, "CHARLOTTE COUNTY", fontproperties=BEBAS, fontsize=64, color="white", ha="right", va="bottom", alpha=0, zorder=10)
t_sub = ax.text(lab_x, lab_y, "Punta Gorda  ·  Port Charlotte", fontproperties=BAR, fontsize=24, color="#a9c3e6", ha="right", va="top", alpha=0, zorder=10)
t_stat = ax.text(lab_x, lab_y, "", fontproperties=BARB, fontsize=26, color=COL["price"], ha="right", va="top", alpha=0, zorder=10)

# screen-space texts
T1 = fig.text(0.055, 0.56, "FLORIDA", fontproperties=BEBAS, fontsize=150, color="white", alpha=0, va="bottom")
T2 = fig.text(0.058, 0.545, "10 COUNTIES  ·  AUGUST 2026 DATA", fontproperties=BAR, fontsize=26, color="#8fb0d8", alpha=0, va="top")
legend_items = []
ly = 0.30
for i, k in enumerate(["buyers", "price", "weak", "stable", "none"]):
    y = ly - i * 0.045
    sq = mpatches.FancyBboxPatch((0.058, y - 0.012), 0.016, 0.026, boxstyle="round,pad=0.002",
                                 transform=fig.transFigure, facecolor=COL[k], edgecolor="none", alpha=0)
    fig.add_artist(sq)
    tx = fig.text(0.082, y, LABEL[k], fontproperties=BAR, fontsize=22, color="#d6e4f5", alpha=0, va="center")
    legend_items.append((sq, tx))

TEST = os.environ.get("TEST")
test_frames = [int(float(x) * FPS) for x in TEST.split(",")] if TEST else None
writer = None if TEST else subprocess.Popen([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)

rank = np.argsort(np.argsort(-np.array([np.vstack([c_polys[k] for k in np.where(c_owner == i)[0]])[:, 1].mean() for i in range(len(c_names))])))

for fi in (range(N) if not TEST else range(max(test_frames) + 1)):
    t = fi / FPS
    # camera
    if t < 3.8:
        cam = cam_lerp(CAM_US, CAM_FL, seg(t, 0.4, 3.8))
    elif t < 9.0:
        cam = CAM_FL
    else:
        cam = cam_lerp(CAM_FL, CAM_CH, seg(t, 9.0, 11.2))
    ax.set_xlim(cam[0] - cam[2] / 2, cam[0] + cam[2] / 2)
    ax.set_ylim(cam[1] - cam[2] * 9 / 32, cam[1] + cam[2] * 9 / 32)

    # US dims as we go in
    us_coll.set_alpha(1.0 - 0.45 * seg(t, 2.0, 4.0))

    # outline draw
    d = seg(t, 1.6, 4.6)
    if d > 0:
        pts = partial(ease(d))
        for ln in glow:
            ln.set_data(pts[:, 0], pts[:, 1])
        head.set_data([pts[-1, 0]], [pts[-1, 1]])
        head.set_alpha(0.9 * (1 - seg(t, 4.5, 4.9)))
    for ln in isle_lines:
        ln.set_alpha(0.8 * seg(t, 4.2, 4.9))
    fl_fill.set_alpha(0.10 * seg(t, 4.3, 5.0) * (1 - seg(t, 5.2, 6.0)))

    # counties staggered in
    cols = base_rgba.copy()
    a = np.array([seg(t, 5.0 + 2.6 * rank[o] / len(c_names), 5.6 + 2.6 * rank[o] / len(c_names)) for o in c_owner])
    # dim others during Charlotte focus
    focus = seg(t, 9.2, 10.0)
    k = np.where(c_owner == ch_idx, 0.0, 0.62 * focus)[:, None]
    bgc = np.array([15 / 255, 27 / 255, 46 / 255])
    cols[:, :3] = cols[:, :3] * (1 - k) + bgc * k
    cols[:, 3] = a * 0.95
    c_coll.set_facecolors(cols)
    ec = np.array([[7 / 255, 13 / 255, 24 / 255, 1.0]] * len(c_owner)); ec[:, 3] = a
    c_coll.set_edgecolors(ec)

    # glow stays but softens after counties
    soft = 1.0 - 0.35 * seg(t, 7.5, 8.5)
    for ln, (_, a0) in zip(glow, glow_specs):
        ln.set_alpha(a0 * soft)

    # titles
    tt = seg(t, 4.6, 5.4)
    fo = 1 - seg(t, 9.0, 9.6)
    T1.set_alpha(ease(tt) * fo); T1.set_y(0.56 + 0.02 * ease(tt))
    T2.set_alpha(ease(seg(t, 5.0, 5.8)) * fo)
    for i, (sq, tx) in enumerate(legend_items):
        la = ease(seg(t, 7.4 + i * 0.12, 8.0 + i * 0.12))
        sq.set_alpha(la); tx.set_alpha(la)

    # Charlotte pulse + label
    p = seg(t, 9.6, 10.2)
    pulse = 0.55 + 0.45 * np.cos((t - 9.6) * 2 * np.pi * 0.9) if t > 9.6 else 0
    for ln, a0 in ch_glow:
        ln.set_alpha(a0 * p * (0.35 + 0.65 * max(pulse, 0)))
    lp = ease(seg(t, 10.3, 10.9))
    elbow = (lab_x + 0.01 * CAM_CH[2], lab_y)
    ex = ch_center[0] + (elbow[0] - ch_center[0]) * lp
    ey = ch_center[1] + (elbow[1] - ch_center[1]) * lp
    leader.set_data([ch_center[0], ex], [ch_center[1], ey]); leader.set_alpha(0.9 * (lp > 0))
    dot.set_alpha(p)
    na = ease(seg(t, 10.7, 11.3))
    t_name.set_alpha(na); t_sub.set_alpha(na)
    t_name.set_position((lab_x, lab_y + 0.004 * CAM_CH[2]))
    t_sub.set_position((lab_x, lab_y - 0.004 * CAM_CH[2]))
    sa = ease(seg(t, 11.4, 12.0))
    t_stat.set_text("~900 LISTINGS PULLED IN 12 MONTHS")
    t_stat.set_position((lab_x, lab_y - 0.034 * CAM_CH[2])); t_stat.set_alpha(sa)

    if TEST:
        if fi in test_frames:
            fig.savefig(f"out/test_a_{fi/FPS:.1f}.png", dpi=100)
        continue
    fig.canvas.draw()
    writer.stdin.write(bytes(fig.canvas.buffer_rgba()))
    if fi % 60 == 0:
        print("frame", fi, "/", N, flush=True)

if writer:
    writer.stdin.close(); writer.wait()
print("done", OUT)
