import datetime as dt

from engine import render
from scenes import price_ladder as pl

S = pl.SCENE
PRICES = [580000, 574999, 565000, 540000, 510000, 490000, 489000, 475000, 430000, 410000]


def test_y_axis_matches_original():
    assert pl.y_axis(PRICES, 310000) == ((280000, 620000), [300000, 400000, 500000, 600000])


def test_nice_step():
    assert pl.nice_step(270000) == 100000
    assert pl.nice_step(45000) == 20000


def test_x_ticks_match_original():
    assert pl.x_ticks(dt.date(2024, 8, 15), dt.date(2026, 9, 23)) == [
        (0, "AUG 2024"), (139, "2025"), (504, "2026"), (769, "TODAY")]


def test_x_ticks_skip_year_too_close():
    assert pl.x_ticks(dt.date(2024, 12, 28), dt.date(2025, 6, 1)) == [(0, "DEC 2024"), (155, "TODAY")]


def test_labels():
    assert pl.change_label(580000, 574999) == "−$5K"
    assert pl.change_label(500000, 520000) == "+$20K"
    assert pl.change_label(3000000, 1800000) == "−$1.2M"
    assert pl.money_short(2000000) == "$2M"
    assert pl.money_axis(300000) == "$300K" and pl.money_axis(1500000) == "$1.5M"


def test_auto_texts():
    assert pl.auto_title(9) == "ONE HOUSE. NINE PRICE CUTS."
    assert pl.auto_title(1) == "ONE HOUSE. ONE PRICE CUT."
    assert pl.auto_title(25) == "ONE HOUSE. 25 PRICE CUTS."
    assert pl.auto_paid_text(310000, 2017) == "OWNER PAID $310,000 IN 2017"
    assert pl.auto_paid_text(310000, None) == "OWNER PAID $310,000"
    assert pl.auto_diff_text(410000, 310000) == "STILL +$100,000\nABOVE WHAT THEY PAID"
    assert pl.auto_diff_text(300000, 310000) == "NOW −$10,000\nBELOW WHAT THEY PAID"
    assert pl.n_cuts([5, 4, 6, 3]) == 2


def test_check_today_before_last_date():
    _, errors = S.validate({"history": [{"date": "2024-01-01", "price": 5}, {"date": "2024-02-01", "price": 4}],
                            "today": "2024-01-15"})
    assert "today" in errors


def test_smoke_without_paid_and_with_increase():
    hist = [{"date": "2023-01-10", "price": 900000}, {"date": "2023-06-01", "price": 950000},
            {"date": "2024-02-01", "price": 870000}]
    clean, errors = S.validate({"history": hist, "today": "2024-05-01"})
    assert errors == {}
    fr = render.Frames(S, clean, dpi=20)
    try:
        for t in (0.5, 3.0, 6.0, 9.0, 11.4):
            assert fr.draw(t)[..., :3].std() > 1
        first = fr.draw(1.0)
        fr.draw(10.0)
        assert (fr.draw(1.0) == first).all()  # geri kaydırma durumsuz
    finally:
        fr.close()
