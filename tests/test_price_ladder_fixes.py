"""Fiyat merdiveni: zaman etiketi çakışması, sayaç yanıp sönmesi, yakın indirimlerin birleşmesi, fark yazısı yeri.
Veriler FredPull'un FL_20260924 projesinden (Pasco, Polk, Miami-Dade, Walton)."""
import matplotlib.colors as mcolors
import numpy as np
import pytest

from engine import brand, render
from scenes import price_ladder as pl

S = pl.SCENE


def hist(*rows):
    return [{"date": d, "price": p} for d, p in rows]


CASES = {
    "pasco": {"history": hist(("2024-11-19", 250000), ("2025-02-22", 275000), ("2025-05-15", 249000),
                              ("2025-11-03", 240000)), "today": "2026-09-24", "paid": 275000, "paid_year": 2021},
    "polk": {"history": hist(("2024-10-20", 320000), ("2024-12-28", 317000), ("2025-03-15", 315000),
                             ("2025-06-21", 310000), ("2025-07-04", 300000), ("2026-09-02", 195000)),
             "today": "2026-09-24", "paid": 213615, "paid_year": 2019},
    "miami_dade": {"history": hist(("2023-10-03", 930000), ("2024-05-02", 795000), ("2024-05-08", 830000),
                                   ("2025-01-06", 795000), ("2025-01-31", 790000), ("2025-02-21", 785000),
                                   ("2025-03-25", 784000), ("2025-09-26", 700000), ("2026-04-29", 670000)),
                   "today": "2026-09-24", "paid": 355000, "paid_year": 2016},
    "walton": {"history": hist(("2025-03-10", 750000), ("2025-04-27", 745000), ("2025-05-02", 740000),
                               ("2025-05-09", 735000), ("2025-05-16", 730000), ("2025-05-23", 725000),
                               ("2025-10-16", 575000)), "today": "2026-09-24"},
}


def frames(case, dpi=100):
    clean, errors = S.validate(CASES[case])
    assert errors == {}
    return render.Frames(S, clean, dpi=dpi)


# 1) zaman etiketleri üst üste binmez
@pytest.mark.parametrize("case", ["pasco", "miami_dade", "polk", "walton"])
def test_time_labels_keep_24px_gap(case):
    fr = frames(case)
    try:
        fr.draw(11.0)
        ax = fr.update.parts["ax"]
        r = fr.fig.canvas.get_renderer()
        boxes = sorted((lab.get_window_extent(renderer=r) for lab in ax.get_xticklabels() if lab.get_text()),
                       key=lambda b: b.x0)
        for a, b in zip(boxes, boxes[1:]):
            assert b.x0 - a.x1 >= 24 - 0.5, (a, b)
        labels = [lab.get_text() for lab in ax.get_xticklabels()]
        assert labels[-1] == "TODAY"
    finally:
        fr.close()


def test_pasco_skips_2025_next_to_listing_label():
    fr = frames("pasco")
    try:
        labels = [lab.get_text() for lab in fr.update.parts["ax"].get_xticklabels()]
        assert labels == ["NOV 2024", "2026", "TODAY"]
    finally:
        fr.close()


def test_thin_ticks_keeps_first_and_last():
    ticks = [(0, "A"), (5, "B"), (50, "C"), (100, "D")]
    assert pl.thin_ticks(ticks, [0, 20, 200, 400], [30, 30, 30, 30], 24) == [(0, "A"), (50, "C"), (100, "D")]


# 2) sayaç yanıp sönmesi en fazla 0,35 sn sürer ve çizim bitince her zaman normal renge döner
def test_counter_flash_never_sticks():
    fr = frames("polk", dpi=20)
    try:
        price = fr.update.parts["price"]
        text = mcolors.to_rgb(brand.color("text"))
        for t in (8.4, 8.6, 9.5, 11.0, 11.4):
            fr.draw(t)
            assert np.allclose(mcolors.to_rgb(price.get_color()), text), t
        # son indirim (2026-09-02) geçilirken kısa bir süre kırmızıya döner
        X, END = fr.update.parts["X"], fr.update.parts["END"]
        t_last = pl.DRAW_START + pl.DRAW_DUR * X[-1] / END
        fr.draw(t_last + 0.05)
        assert not np.allclose(mcolors.to_rgb(price.get_color()), text)
        fr.draw(t_last + pl.FLASH_DUR + 0.01)
        assert np.allclose(mcolors.to_rgb(price.get_color()), text)
    finally:
        fr.close()


def test_late_cut_label_fully_visible_at_end():
    fr = frames("polk", dpi=20)
    try:
        fr.draw(11.0)
        assert all(lb.get_alpha() == pytest.approx(1.0) for lb in fr.update.parts["cut_labels"])
        assert all(d.get_alpha() == pytest.approx(1.0) for d in fr.update.parts["cut_dots"])
    finally:
        fr.close()


# 3) yakın ardışık indirimler tek etikette; noktalar ve sayaç değişmez
def test_walton_close_cuts_merge_into_one_label():
    fr = frames("walton", dpi=20)
    try:
        fr.draw(11.0)
        parts = fr.update.parts
        assert [lb.get_text() for lb in parts["cut_labels"]] == ["5 CUTS −$25K", "−$150K"]
        assert len(parts["cut_dots"]) == 6
        assert parts["cuts"].get_text() == "6"
    finally:
        fr.close()


def test_change_groups():
    X = np.array([0, 48, 53, 60, 67, 74, 220], float)
    P = np.array([750, 745, 740, 735, 730, 725, 575], float)
    assert pl.change_groups(X, P, 563) == [[1, 2, 3, 4, 5], [6]]
    # artış grubu böler, uzak indirimler ayrı kalır
    X2, P2 = np.array([0, 10, 12, 14, 300], float), np.array([10, 9, 11, 8, 7], float)
    assert pl.change_groups(X2, P2, 400) == [[1], [2], [3], [4]]


# 4) fark yazısı dik düşüş çizgisine binmez: solunda en az 16 px boşluk ya da alış çizgisinin altında
@pytest.mark.parametrize("case", ["polk", "pasco", "miami_dade"])
def test_diff_text_clear_of_vertical_lines(case):
    fr = frames(case)
    try:
        fr.draw(11.0)
        parts = fr.update.parts
        ax, txt, X, P = parts["ax"], parts["diff_text"], parts["X"], parts["P"]
        bb = txt.get_window_extent(renderer=fr.fig.canvas.get_renderer())
        for i in range(1, len(X)):
            (sx, a), (_, b) = ax.transData.transform([(X[i], P[i - 1]), (X[i], P[i])])
            if min(a, b) <= bb.y1 and max(a, b) >= bb.y0:  # yazıyla aynı yükseklikte dik çizgi
                assert sx - bb.x1 >= 16 - 0.5 or bb.x0 - sx >= 16 - 0.5, (case, i, sx, bb)
    finally:
        fr.close()


def _sample_frames():
    import os

    from engine import assets, project

    clean, errors = project.load(os.path.join(assets.ROOT, "projects", "ornek_florida.json"))
    assert errors == []
    return render.Frames(S, clean["scenes"][1]["params"], dpi=100)


@pytest.mark.parametrize("case", ["polk", "pasco", "miami_dade", "ornek_lee"])
def test_diff_text_does_not_cover_change_labels(case):
    fr = _sample_frames() if case == "ornek_lee" else frames(case)
    try:
        fr.draw(11.0)
        parts = fr.update.parts
        r = fr.fig.canvas.get_renderer()
        d = parts["diff_text"].get_window_extent(renderer=r)
        for lb in parts["cut_labels"]:
            e = lb.get_window_extent(renderer=r)
            assert e.x1 <= d.x0 or e.x0 >= d.x1 or e.y1 <= d.y0 or e.y0 >= d.y1, (case, lb.get_text())
    finally:
        fr.close()


def test_polk_diff_text_moves_left_of_the_drop():
    fr = frames("polk")
    try:
        parts = fr.update.parts
        ax, txt, X, P = parts["ax"], parts["diff_text"], parts["X"], parts["P"]
        bb = txt.get_window_extent(renderer=fr.fig.canvas.get_renderer())
        drop_x = ax.transData.transform((X[-1], P[-1]))[0]
        assert bb.x1 <= drop_x - 16 + 0.5
    finally:
        fr.close()
