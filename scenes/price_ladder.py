"""Fiyat merdiveni: bir evin fiyat geçmişi, sayaçlar ve alış fiyatıyla karşılaştırma.
Görünüm ve zamanlamalar orijinal scene_b.py ile aynıdır; update(t) içindeki t temel süre (11,5 sn) cinsindendir."""
import datetime as dt
import math

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from engine import brand
from engine.params import Color, Date, Number, PriceTable, Text
from engine.scene import Scene, cap_scale, ease, fit_text, round_half_up, seg

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
NUM_WORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN",
             "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN", "TWENTY"]
# Orijinal yerleşim 769 günlük ve 340.000 $'lık eksen için elle ayarlanmıştı; ofsetler bu oranlarla ölçeklenir.
REF_DAYS, REF_SPAN = 769, 340000
# fiyat çizgisinin çizildiği aralık (temel süre, sn); sayaç yanıp sönmesi ve etiketlerin belirmesi (sn)
DRAW_START, DRAW_DUR = 2.4, 6.0
FLASH_DUR, LABEL_FADE = 0.35, 0.25
# piksel boşlukları 1080p içindir (dpi 100); önizlemede dpi'ye göre ölçeklenir
TICK_GAP_PX, DIFF_GAP_PX = 24, 16

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
    Color("accent", "Çizgi rengi (neon)", default=brand.color("accent"), group="Renkler"),
]


def money_short(v):
    """"$5K", "$1.2M"; yarımlar yukarı (engine.scene.round_half_up)."""
    a = abs(v)
    if a >= 1_000_000:
        return f"${round_half_up(a / 1e6, 1):.1f}M".replace(".0M", "M")
    return f"${round_half_up(a / 1000)}K"


def money_axis(v):
    return f"${v / 1e6:g}M" if v >= 1_000_000 else f"${round_half_up(v / 1000)}K"


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
    """Aday zaman etiketleri: ilan ayı, aradaki her 1 Ocak ve TODAY. Çakışanları thin_ticks ayıklar."""
    end = (today - listed).days
    ticks = [(0, f"{MONTHS[listed.month - 1]} {listed.year}")]
    for year in range(listed.year + 1, today.year + 1):
        d = (dt.date(year, 1, 1) - listed).days
        if 0 < d < end:
            ticks.append((d, str(year)))
    ticks.append((end, "TODAY"))
    return ticks


def thin_ticks(ticks, centers, widths, min_gap):
    """Ortalanmış etiketlerin piksel konum ve genişliklerine göre, komşusuyla arasında min_gap pikselden az
    boşluk kalan yıl etiketlerini atlar. İlk (ilan) ve son (TODAY) etiket her zaman kalır."""
    n = len(ticks)
    if n <= 2:
        return list(ticks)

    def left(i):
        return centers[i] - widths[i] / 2

    def right(i):
        return centers[i] + widths[i] / 2

    kept = [0]
    for i in range(1, n - 1):
        if left(i) - right(kept[-1]) >= min_gap and left(n - 1) - right(i) >= min_gap:
            kept.append(i)
    kept.append(n - 1)
    return [ticks[i] for i in kept]


def change_groups(X, P, end, frac=0.06):
    """Değişim etiketi grupları (1'den başlayan olay indeksleri). Zaman ekseninde birbirine end*frac'tan yakın
    ardışık indirimler tek grupta toplanır; artışlar ve uzak indirimler tek başına kalır."""
    groups = []
    for i in range(1, len(X)):
        drop = P[i] < P[i - 1]
        last = groups[-1] if groups else None
        if last and drop and last["drop"] and X[i] - X[last["idx"][-1]] < frac * end:
            last["idx"].append(i)
        else:
            groups.append({"idx": [i], "drop": drop})
    return [g["idx"] for g in groups]


def group_label(P, idx):
    """Tek değişim için "−$5K", grup için "5 CUTS −$25K" (grubun toplam düşüşü)."""
    if len(idx) == 1:
        return change_label(P[idx[0] - 1], P[idx[0]])
    return f"{len(idx)} CUTS " + change_label(P[idx[0] - 1], P[idx[-1]])


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


def place_diff_text(fig, ax, text, paid_txt, X, P, paid, span, labels=()):
    """Fark yazısını fiyat çizgisinin dik bölümlerine ve değişim etiketlerine binmeyecek yere koyar. Varsayılan yer
    (sağda, alış fiyatı ile güncel fiyatın ortası) bir dik çizgiye ya da etikete biniyorsa yazı onun soluna, arada
    en az 16 px kalacak şekilde kayar; eksenden ya da alış yazısının üstüne taşarsa alış çizgisinin altına alınır."""
    r = fig.canvas.get_renderer()
    gap = DIFF_GAP_PX * fig.dpi / 100
    to_px = ax.transData.transform
    x_default, y_mid = text.get_position()
    bb = text.get_window_extent(renderer=r)
    w, h = bb.width, bb.height
    obstacles = []  # (sol x, sağ x, alt y, üst y) piksel: dik çizgiler ve değişim etiketleri
    for i in range(1, len(X)):
        (sx, a), (_, b) = to_px([(X[i], P[i - 1]), (X[i], P[i])])
        obstacles.append((sx, sx, min(a, b), max(a, b)))
    for lb in labels:
        e = lb.get_window_extent(renderer=r)
        obstacles.append((e.x0, e.x1, e.y0, e.y1))
    pb = paid_txt.get_window_extent(renderer=r)
    axes_left = to_px((ax.get_xlim()[0], 0))[0]

    def fit(y0, y1):
        """Yazının sağ kenarının piksel x'i (engellerden kaçacak kadar sola kaymış) ya da sığmazsa None."""
        xr = to_px((x_default, 0))[0]
        for _ in range(len(obstacles) + 1):
            hits = [ox0 for ox0, ox1, oy0, oy1 in obstacles
                    if oy0 <= y1 and oy1 >= y0 and xr - w - gap < ox1 and ox0 < xr + gap]
            if not hits:
                break
            xr = min(hits) - gap
        else:
            return None
        if xr - w < axes_left:
            return None
        if xr > pb.x0 and xr - w < pb.x1 and y1 > pb.y0 and y0 < pb.y1:  # alış yazısının üstüne biniyor
            return None
        return xr

    yc = to_px((0, y_mid))[1]
    xr = fit(yc - h / 2, yc + h / 2)
    if xr is None:  # alış çizgisinin altına
        y_mid = paid - span * 9000 / REF_SPAN
        text.set_va("top")
        yt = to_px((0, y_mid))[1]
        xr = fit(yt - h, yt)
        if xr is None:
            xr = to_px((x_default, 0))[0]
    text.set_position((ax.transData.inverted().transform((xr, 0))[0], y_mid))


def check(p):
    if p["today"] < p["history"][-1]["date"]:
        return {"today": "Bugünün tarihi fiyat geçmişindeki son tarihten önce olamaz."}
    return {}


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    NUM, BAR, BARB = F["numbers"], F["label"], F["label_bold"]
    C = brand.colors()
    NEON, RED, MUTED, TEXT, LINE = p["accent"], C["loss"], C["muted"], C["text"], C["line"]
    AMBER = brand.category_color("price")  # alış çizgisi ve fark oku
    NK = cap_scale(fig, NUM)  # büyük rakam yazı tipini tasarım boyutlarına eşitler
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
    ax.set_yticklabels([money_axis(v) for v in yticks], parse_math=False, fontproperties=BAR, fontsize=20)
    # zaman etiketleri: gerçek piksel genişlikleri ölçülür, komşusuna 24 px'ten yakın yıl etiketi atlanır
    xt = x_ticks(listed, today)
    tick_prop = BAR.copy()
    tick_prop.set_size(20)
    renderer = fig.canvas.get_renderer()
    centers = ax.transData.transform([(d, Y0) for d, _ in xt])[:, 0]
    widths = [renderer.get_text_width_height_descent(s, tick_prop, ismath=False)[0] for _, s in xt]
    xt = thin_ticks(xt, centers, widths, TICK_GAP_PX * fig.dpi / 100)
    ax.set_xticks([d for d, _ in xt])
    ax.set_xticklabels([s for _, s in xt], parse_math=False, fontproperties=BAR, fontsize=20)
    grid = [ax.axhline(v, color=LINE, lw=1, zorder=0) for v in yticks]

    glow_specs = [(14, 0.06), (8, 0.14), (4.5, 0.3), (2.4, 1.0)]
    glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_joinstyle="miter", zorder=5)[0] for w, a in glow_specs]
    head = ax.plot([], [], "o", color=TEXT, ms=11, zorder=7)[0]
    head_ring = ax.plot([], [], "o", color=NEON, ms=26, alpha=0.25, zorder=6)[0]
    fill = [None]

    # her değişim ayrı nokta; yakın ardışık indirimler tek etikette ("5 CUTS −$25K")
    t_pass = DRAW_START + DRAW_DUR * X / END  # çizgi başının her değişim noktasından geçtiği an
    cut_dots = []
    for i in range(1, len(X)):
        color = RED if drops[i - 1] else NEON
        cut_dots.append(ax.plot([X[i]], [P[i]], "o", color=color, ms=9, alpha=0, zorder=8)[0])
    groups = change_groups(X, P, END)
    cut_labels = []  # (etiket, grubun son değişim indeksi)
    for k, idx in enumerate(groups):
        first, last = idx[0], idx[-1]
        color = RED if drops[first - 1] else NEON
        above = k % 2 == 0
        # grup etiketi ilk indirimin hizasında durur (tek indirimdeki yerle aynı kural)
        if above:
            xv, yv, ha = (X[first] + X[last]) / 2, P[first - 1] + SPAN * 14000 / REF_SPAN, "center"
        else:
            xv, yv, ha = X[first] - END * 6 / REF_DAYS, P[first] - SPAN * 24000 / REF_SPAN, "right"
        label = ax.text(xv, yv, group_label(P, idx), parse_math=False, fontproperties=BARB, fontsize=20,
                        color=color, ha=ha, va="center", alpha=0, zorder=9)
        cut_labels.append((label, last))

    if paid is not None:
        paid_line = ax.plot([], [], color=AMBER, lw=2.4, ls=(0, (6, 5)), zorder=4)[0]
        paid_txt = ax.text(END * 10 / REF_DAYS, paid + SPAN * 9000 / REF_SPAN,
                           p["paid_text"] or auto_paid_text(paid, paid_year), parse_math=False,
                           fontproperties=BARB, fontsize=22, color=AMBER, ha="left", va="bottom", alpha=0, zorder=9)
        bx = END + END * 8 / REF_DAYS
        diff_color = AMBER if P[-1] >= paid else RED  # alış fiyatının altındaysa zarar rengi
        brk = ax.annotate("", xy=(bx, paid), xytext=(bx, P[-1]),
                          arrowprops=dict(arrowstyle="<->", color=diff_color, lw=2.2), alpha=0, zorder=9,
                          parse_math=False)
        brk_txt = ax.text(END - END * 12 / REF_DAYS, (paid + P[-1]) / 2,
                          p["diff_text"] or auto_diff_text(int(P[-1]), paid), parse_math=False,
                          fontproperties=BARB, fontsize=22, color=diff_color, ha="right", va="center", alpha=0,
                          zorder=9, linespacing=1.1)
        place_diff_text(fig, ax, brk_txt, paid_txt, X, P, paid, SPAN, [lb for lb, _ in cut_labels])

    # başlık
    K = fig.text(0.07, 0.905, p["kicker"], parse_math=False, fontproperties=BAR, fontsize=26, color=NEON, alpha=0)
    T = fig.text(0.068, 0.885, p["title"] or auto_title(n_cuts(list(P))), parse_math=False, fontproperties=NUM,
                 fontsize=92 * NK, color=TEXT, alpha=0, va="top")
    fit_text(fig, T, 0.88)
    S = fig.text(0.07, 0.745, p["subtitle"], parse_math=False, fontproperties=BAR, fontsize=24, color=MUTED,
                 alpha=0, va="top")

    # sağ panel
    PX = 0.73

    def block(y, label, big):
        lab = fig.text(PX, y, label, parse_math=False, fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)
        val = fig.text(PX - 0.003, y - 0.012, "", parse_math=False, fontproperties=NUM, fontsize=big * NK,
                       color=TEXT, alpha=0, va="top")
        return lab, val

    def fit_value(val, widest):
        # sayaç metni her karede değişir; en geniş değere göre bir kez boyutlanır
        val.set_text(widest)
        fit_text(fig, val, 0.24)
        val.set_text("")

    L1, V1 = block(0.66, p["label_price"], 118)
    L2, V2 = block(0.44, p["label_days"], 96)
    L3, V3 = block(0.25, p["label_cuts"], 96)
    fit_value(V1, f"${int(P.max()):,}")
    fit_value(V2, str(END))
    fit_value(V3, str(len(X) - 1))
    sep = [fig.add_artist(plt.Line2D([PX, 0.95], [y, y], transform=fig.transFigure, color=LINE, lw=1.2, alpha=0))
           for y in (0.475, 0.285)]
    white, red = np.array(mcolors.to_rgb(TEXT)), np.array(mcolors.to_rgb(RED))

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

        def shown(i):
            # değişim noktasının görünürlüğü: baş geçtikten sonra LABEL_FADE saniyede belirir (geçen süreye bağlı)
            e = t - t_pass[i]
            return ease(np.clip(e / LABEL_FADE, 0, 1)) if t >= DRAW_START and e >= 0 else 0

        flash = 0.0
        for i in range(1, len(X)):
            cut_dots[i - 1].set_alpha(shown(i))
            e = t - t_pass[i]  # baş bu indirimi geçeli kaç saniye oldu
            if drops[i - 1] and t < DRAW_START + DRAW_DUR and 0 <= e < FLASH_DUR:
                flash = max(flash, 1 - e / FLASH_DUR)
        for label, last in cut_labels:
            label.set_alpha(shown(last))
        V1.set_text(f"${int(cur):,}")
        V1.set_color(tuple(white * (1 - flash) + red * flash))
        V2.set_text(f"{round_half_up(xh) if t >= 2.4 else 0}")
        V3.set_text(f"{ncut}")

        if paid is None:
            return
        pl = ease(seg(t, 8.7, 9.5))
        paid_line.set_data([0, END * pl], [paid, paid])
        paid_txt.set_alpha(ease(seg(t, 9.0, 9.6)))
        ba = ease(seg(t, 9.7, 10.3))
        brk.arrow_patch.set_alpha(ba)
        brk_txt.set_alpha(ba)

    # testler ve hata ayıklama için kurulmuş parçalar
    update.parts = {"ax": ax, "price": V1, "cuts": V3, "cut_dots": cut_dots, "cut_labels": [lb for lb, _ in cut_labels],
                    "diff_text": brk_txt if paid is not None else None, "X": X, "P": P, "END": END}
    return update


SCENE = Scene(id="price_ladder", title="Fiyat merdiveni", base_duration=11.5, params=PARAMS, setup=setup,
              bg_center=(0.4, 0.5), check=check)
