"""Fiyat merdiveni: bir evin fiyat geçmişi, sayaçlar ve alış fiyatıyla karşılaştırma.
Görünüm ve zamanlamalar orijinal scene_b.py ile aynıdır; update(t) içindeki t temel süre (11,5 sn) cinsindendir."""
import datetime as dt
import math

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from engine.params import Color, Date, Number, PriceTable, Text
from engine.scene import Scene, ease, seg

RED, AMBER, MUTED = "#ff5a4f", "#ffb020", "#8fb0d8"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
NUM_WORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN",
             "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN", "TWENTY"]
# Orijinal yerleşim 769 günlük ve 340.000 $'lık eksen için elle ayarlanmıştı; ofsetler bu oranlarla ölçeklenir.
REF_DAYS, REF_SPAN = 769, 340000

PARAMS = [
    Text("kicker", "Üst etiket", default=""),
    Text("title", "Başlık", default="", auto=True, help="Boş bırakılırsa 'ONE HOUSE. <N> PRICE CUTS.' yazılır."),
    Text("subtitle", "Alt başlık", default=""),
    PriceTable("history", "Fiyat geçmişi", group="Veri", help="İlk satır ilan tarihi ve ilk fiyattır.",
               default=[{"date": "2024-08-15", "price": 580000}, {"date": "2025-01-10", "price": 560000}]),
    Date("today", "Bugünün tarihi", default=dt.date.today().isoformat(), group="Veri"),
    Number("paid", "Alış fiyatı ($)", default=None, group="Veri", lo=0, integer=True, optional=True),
    Number("paid_year", "Alış yılı", default=None, group="Veri", lo=1900, hi=2100, integer=True, optional=True),
    Text("paid_text", "Alış yazısı", default="", auto=True, group="Veri"),
    Text("diff_text", "Fark yazısı", default="", auto=True, multiline=True, group="Veri"),
    Text("label_price", "Fiyat etiketi", default="ASKING PRICE"),
    Text("label_days", "Gün etiketi", default="DAYS FOR SALE"),
    Text("label_cuts", "İndirim etiketi", default="PRICE CUTS"),
    Color("accent", "Çizgi rengi (neon)", default="#3ee6ff", group="Renkler"),
]


def money_short(v):
    a = abs(v)
    if a >= 1_000_000:
        return f"${a / 1e6:.1f}M".replace(".0M", "M")
    return f"${round(a / 1000):.0f}K"


def money_axis(v):
    return f"${v / 1e6:g}M" if v >= 1_000_000 else f"${v / 1000:.0f}K"


def change_label(prev, cur):
    return ("−" if cur < prev else "+") + money_short(prev - cur)


def nice_step(r):
    """1-2-2,5-5 x 10^k serisinden, r aralığına en fazla 4 adım sığdıran en küçük değer."""
    e = math.floor(math.log10(r / 4))
    for scale in (10 ** e, 10 ** (e + 1)):
        for m in (1, 2, 2.5, 5):
            if r / (m * scale) <= 4:
                return m * scale
    return 10 ** (e + 1)


def y_axis(prices, paid=None):
    lo = min(list(prices) + ([paid] if paid is not None else []))
    hi = max(prices)
    r = (hi - lo) or max(hi * 0.1, 1000)
    step = nice_step(r)
    unit = step / 10
    y0 = round((lo - 0.11 * r) / unit) * unit
    y1 = round((hi + 0.15 * r) / unit) * unit
    first = math.ceil(y0 / step) * step
    ticks = [first + i * step for i in range(int((y1 - first) // step) + 1)]
    return (y0, y1), ticks


def x_ticks(listed, today):
    end = (today - listed).days
    ticks = [(0, f"{MONTHS[listed.month - 1]} {listed.year}")]
    for year in range(listed.year + 1, today.year + 1):
        d = (dt.date(year, 1, 1) - listed).days
        if d >= 0.06 * end and end - d >= 0.06 * end:
            ticks.append((d, str(year)))
    ticks.append((end, "TODAY"))
    return ticks


def n_cuts(prices):
    return sum(1 for a, b in zip(prices, prices[1:]) if b < a)


def auto_title(n):
    word = NUM_WORDS[n] if n <= 20 else str(n)
    return f"ONE HOUSE. {word} PRICE {'CUT' if n == 1 else 'CUTS'}."


def auto_paid_text(paid, year):
    return f"OWNER PAID ${paid:,}" + (f" IN {year}" if year else "")


def auto_diff_text(last, paid):
    d = last - paid
    if d >= 0:
        return f"STILL +${d:,}\nABOVE WHAT THEY PAID"
    return f"NOW −${-d:,}\nBELOW WHAT THEY PAID"


def check(p):
    if p["today"] < p["history"][-1]["date"]:
        return {"today": "Bugünün tarihi fiyat geçmişindeki son tarihten önce olamaz."}
    return {}


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    BEBAS, BAR, BARB = F["bebas"], F["semibold"], F["bold"]
    NEON = p["accent"]
    hist = p["history"]
    listed = dt.date.fromisoformat(hist[0]["date"])
    today = dt.date.fromisoformat(p["today"])
    X = np.array([(dt.date.fromisoformat(r["date"]) - listed).days for r in hist], float)
    P = np.array([r["price"] for r in hist], float)
    END = (today - listed).days
    paid, paid_year = p["paid"], p["paid_year"]
    (Y0, Y1), yticks = y_axis([r["price"] for r in hist], paid)
    SPAN = Y1 - Y0
    drops = P[1:] < P[:-1]

    def price_at(x):
        return P[np.searchsorted(X, x, side="right") - 1]

    def path_upto(x):
        xs, ys = [X[0]], [P[0]]
        for i in range(1, len(X)):
            if X[i] > x:
                break
            xs += [X[i], X[i]]
            ys += [P[i - 1], P[i]]
        xs.append(x)
        ys.append(price_at(x))
        return np.array(xs), np.array(ys)

    ax = fig.add_axes([0.07, 0.12, 0.58, 0.56])
    ax.patch.set_alpha(0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlim(-END * 15 / REF_DAYS, END + END * 25 / REF_DAYS)
    ax.set_ylim(Y0, Y1)
    ax.tick_params(colors=MUTED, length=0, labelsize=18)
    ax.set_yticks(yticks)
    ax.set_yticklabels([money_axis(v) for v in yticks], fontproperties=BAR, fontsize=20)
    xt = x_ticks(listed, today)
    ax.set_xticks([d for d, _ in xt])
    ax.set_xticklabels([s for _, s in xt], fontproperties=BAR, fontsize=20)
    grid = [ax.axhline(v, color="#1f3050", lw=1, zorder=0) for v in yticks]

    glow_specs = [(14, 0.06), (8, 0.14), (4.5, 0.3), (2.4, 1.0)]
    glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_joinstyle="miter", zorder=5)[0] for w, a in glow_specs]
    head = ax.plot([], [], "o", color="white", ms=11, zorder=7)[0]
    head_ring = ax.plot([], [], "o", color=NEON, ms=26, alpha=0.25, zorder=6)[0]
    fill = [None]

    cut_dots, cut_labels = [], []
    for i in range(1, len(X)):
        color = RED if drops[i - 1] else NEON
        cut_dots.append(ax.plot([X[i]], [P[i]], "o", color=color, ms=9, alpha=0, zorder=8)[0])
        above = i % 2 == 1
        yv = P[i - 1] + SPAN * 14000 / REF_SPAN if above else P[i] - SPAN * 24000 / REF_SPAN
        cut_labels.append(ax.text(X[i] if above else X[i] - END * 6 / REF_DAYS, yv, change_label(P[i - 1], P[i]),
                                  fontproperties=BARB, fontsize=20, color=color,
                                  ha="center" if above else "right", va="center", alpha=0, zorder=9))

    if paid is not None:
        paid_line = ax.plot([], [], color=AMBER, lw=2.4, ls=(0, (6, 5)), zorder=4)[0]
        paid_txt = ax.text(END * 10 / REF_DAYS, paid + SPAN * 9000 / REF_SPAN,
                           p["paid_text"] or auto_paid_text(paid, paid_year), fontproperties=BARB, fontsize=22,
                           color=AMBER, ha="left", va="bottom", alpha=0, zorder=9)
        bx = END + END * 8 / REF_DAYS
        brk = ax.annotate("", xy=(bx, paid), xytext=(bx, P[-1]),
                          arrowprops=dict(arrowstyle="<->", color=AMBER, lw=2.2), alpha=0, zorder=9)
        brk_txt = ax.text(END - END * 12 / REF_DAYS, (paid + P[-1]) / 2,
                          p["diff_text"] or auto_diff_text(int(P[-1]), paid), fontproperties=BARB, fontsize=22,
                          color=AMBER, ha="right", va="center", alpha=0, zorder=9, linespacing=1.1)

    # başlık
    K = fig.text(0.07, 0.905, p["kicker"], fontproperties=BAR, fontsize=26, color=NEON, alpha=0)
    T = fig.text(0.068, 0.885, p["title"] or auto_title(n_cuts(list(P))), fontproperties=BEBAS, fontsize=92,
                 color="white", alpha=0, va="top")
    S = fig.text(0.07, 0.745, p["subtitle"], fontproperties=BAR, fontsize=24, color=MUTED, alpha=0, va="top")

    # sağ panel
    PX = 0.73

    def block(y, label, big):
        lab = fig.text(PX, y, label, fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)
        val = fig.text(PX - 0.003, y - 0.012, "", fontproperties=BEBAS, fontsize=big, color="white", alpha=0, va="top")
        return lab, val

    L1, V1 = block(0.66, p["label_price"], 118)
    L2, V2 = block(0.44, p["label_days"], 96)
    L3, V3 = block(0.25, p["label_cuts"], 96)
    sep = [fig.add_artist(plt.Line2D([PX, 0.95], [y, y], transform=fig.transFigure, color="#1f3050", lw=1.2, alpha=0))
           for y in (0.475, 0.285)]
    white, red = np.array(mcolors.to_rgb("white")), np.array(mcolors.to_rgb(RED))

    def update(t):
        ha = ease(seg(t, 0.0, 0.8))
        K.set_alpha(ha)
        T.set_alpha(ha)
        S.set_alpha(ease(seg(t, 0.3, 1.1)))
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
        if fill[0] is not None:
            fill[0].remove()
            fill[0] = None
        if t >= 2.4:
            xs, ys = path_upto(xh)
            for ln in glow:
                ln.set_data(xs, ys)
            head.set_data([xh], [ys[-1]])
            head_ring.set_data([xh], [ys[-1]])
            fill[0] = ax.fill_between(xs, ys, Y0, color=NEON, alpha=0.07, lw=0, zorder=2)
        else:
            for ln in glow:
                ln.set_data([], [])
            head.set_data([], [])
            head_ring.set_data([], [])
        cur = price_at(xh) if t >= 2.4 else P[0]
        ncut = int(np.sum((X[1:] <= xh) & drops)) if t >= 2.4 else 0
        flash = 0.0
        for i in range(1, len(X)):
            dtc = (xh - X[i]) / END * 6.0  # baş bu noktayı geçeli kaç saniye oldu
            a = ease(np.clip(dtc / 0.25, 0, 1)) if xh >= X[i] and t >= 2.4 else 0
            cut_dots[i - 1].set_alpha(a)
            cut_labels[i - 1].set_alpha(a)
            if 0 <= dtc < 0.35 and xh >= X[i] and drops[i - 1]:
                flash = max(flash, 1 - dtc / 0.35)
        V1.set_text(f"${int(cur):,}")
        V1.set_color(tuple(white * (1 - flash) + red * flash))
        V2.set_text(f"{int(round(xh)) if t >= 2.4 else 0}")
        V3.set_text(f"{ncut}")

        if paid is None:
            return
        pl = ease(seg(t, 8.7, 9.5))
        paid_line.set_data([0, END * pl], [paid, paid])
        paid_txt.set_alpha(ease(seg(t, 9.0, 9.6)))
        ba = ease(seg(t, 9.7, 10.3))
        brk.arrow_patch.set_alpha(ba)
        brk_txt.set_alpha(ba)

    return update


SCENE = Scene(id="price_ladder", title="Fiyat merdiveni", base_duration=11.5, params=PARAMS, setup=setup,
              bg_center=(0.4, 0.5), check=check)
