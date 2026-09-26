"""Grafik ve vaat sahneleri: varsayılanlarla doğrulama, kare üretimi, durumsuzluk, şeffaf kip, gerçek oranlar,
'%' kuralı ve sahnelere özgü kurallar."""
import numpy as np
import pytest

from engine import params as P
from engine import render
from scenes import REGISTRY, chartlib as cl, county_quiz, house_bars, house_grid, line_trend, ring

CHARTS = ["question_board", "county_quiz", "house_bars", "line_trend", "bar_list", "ring", "thermometer",
          "house_grid"]


def frames(sid, dpi=50, transparent=False, **kw):
    scene = REGISTRY[sid]
    p, errors = scene.validate(kw)
    assert errors == {}
    return render.Frames(scene, p, transparent=transparent, dpi=dpi), p


@pytest.mark.parametrize("sid", CHARTS)
def test_defaults_validate(sid):
    assert REGISTRY[sid].validate({})[1] == {}


@pytest.mark.parametrize("sid", CHARTS)
def test_frames_are_stateless_and_animate(sid):
    fr, p = frames(sid)
    try:
        d = p["duration"]
        first, mid, last = (fr.draw(t) for t in (0.0, d / 2, d - 1 / 30))
        assert first.shape == (540, 960, 4)
        assert np.array_equal(fr.draw(d / 2), mid)  # sona gidip geri dönünce aynı kare
        assert np.array_equal(fr.draw(0.0), first)
        assert not np.array_equal(first, last)
    finally:
        fr.close()


@pytest.mark.parametrize("sid", CHARTS)
def test_transparent_has_alpha(sid):
    fr, p = frames(sid, transparent=True)
    try:
        a = fr.draw(p["duration"] - 1 / 30)[..., 3]
        assert a.min() == 0 and a.max() == 255
    finally:
        fr.close()


def test_full_size_frame():
    fr, _ = frames("house_bars", dpi=100)
    try:
        assert fr.draw(1.0).shape == (1080, 1920, 4)
        assert fr.n_frames == 7 * 30
    finally:
        fr.close()


@pytest.mark.parametrize("sid", CHARTS)
def test_percent_sign_is_rejected(sid):
    errors = REGISTRY[sid].validate({"title": "44% OF HOMES", "source": "SOURCE: REDFIN"})[1]
    assert "title" in errors and "yüzde" in errors["title"]


def test_percent_in_table_label_is_rejected():
    t = P.ValueTable("rows", "Satırlar", min_rows=1, max_rows=3)
    with pytest.raises(P.ParamError, match="yüzde"):
        t.validate([{"label": "44%", "value": 44}], {})


# ---------- gerçek oranlar ----------
def test_house_bars_heights_are_proportional():
    bars = [{"label": str(2019 + i), "value": v} for i, v in enumerate([243000, 419000, 360000, 120000, 5000])]
    fr, p = frames("house_bars", bars=bars, arrow_from="", arrow_to="")
    try:
        fr.draw(6.9)
        parts = fr.update.parts
        for bar, v in zip(parts["bars"], p["bars"]):
            apex = bar.polys[0].get_xy()[:, 1].max() - house_bars.BASE  # çizilen şeklin çatı tepesi
            expected = house_bars.APEX_MAX * v["value"] / 419000
            assert abs(apex - expected) <= expected * 0.01
    finally:
        fr.close()


def test_bar_list_lengths_are_proportional():
    rows = [{"label": s, "value": v} for s, v in (("A", 7.7), ("B", 6.3), ("C", 3.7), ("D", 0.4), ("E", 5.0))]
    fr, p = frames("bar_list", rows=rows, max_value=8, value_suffix="", decimals=1)
    try:
        fr.draw(6.4)
        parts = fr.update.parts
        for bar, r in zip(parts["bars"], p["rows"]):
            expected = parts["wmax"] * r["value"] / 8
            assert abs(bar.get_width() - expected) <= expected * 0.01
    finally:
        fr.close()


def test_ring_angle_matches_value():
    fr, _ = frames("ring", value=62.5, max_value=100)
    try:
        fr.draw(5.9)
        fill = fr.update.parts["fill"]
        assert abs((fill.theta2 - fill.theta1) - 360 * 0.625) < 0.01
    finally:
        fr.close()


def test_compare_columns_use_true_ratio():
    fr, _ = frames("county_quiz", duration=9.5)
    try:
        fr.draw(9.4)
        ref, col = fr.update.parts["updaters"][2].bars
        assert abs(col.h / ref.h - 360000 / 415000) < 0.01
    finally:
        fr.close()


# ---------- sahne kuralları ----------
def test_county_quiz_row_stays_question_when_reveal_after_end():
    fr, _ = frames("county_quiz", row1_reveal=20)
    try:
        fr.draw(9.4)
        row1, row2 = fr.update.parts["updaters"][:2]
        assert row1.question.t.get_alpha() > 0.9 and row1.value.get_alpha() == 0
        assert row2.value.get_alpha() > 0.9  # 5,0 sn'de açılan satır açıldı
    finally:
        fr.close()


def test_county_quiz_reveal_is_real_seconds():
    # süre iki katına çıkınca 3,4 sn'de açılan satır gerçek zamanda yine 3,4 sn'de açılır
    fr, _ = frames("county_quiz", duration=19.0)
    try:
        fr.draw(3.3)
        assert fr.update.parts["updaters"][0].value.get_alpha() == 0
        fr.draw(3.5)
        assert fr.update.parts["updaters"][0].value.get_alpha() > 0.9
    finally:
        fr.close()


def test_county_quiz_counter_decimals_and_prefix():
    fr, _ = frames("county_quiz", row1_value=6.2, row1_decimals=1, row2_kind="counter", row2_value=94.3,
                   row2_prefix="$")
    try:
        fr.draw(9.4)
        row1, row2 = fr.update.parts["updaters"][:2]
        assert row1.value.get_text() == "6.2" and row2.value.get_text() == "$94"
    finally:
        fr.close()


def test_county_quiz_checks():
    s = REGISTRY["county_quiz"]
    assert "row2_value" in s.validate({"row2_value": 12})[1]
    assert "row3_value2" in s.validate({"row3_value2": None})[1]
    assert "row1_kind" in s.validate({"row1_kind": "none", "row2_kind": "none", "row3_kind": "none"})[1]


def test_question_board_needs_two_cards_and_county_for_county_icon():
    s = REGISTRY["question_board"]
    assert "card2_value" in s.validate({"card2_value": "", "card3_value": "", "card4_value": ""})[1]
    assert "card2_fips" in s.validate({"card2_fips": None})[1]
    assert s.validate({"card4_value": ""})[1] == {}  # üç kart da olur


def test_house_bars_arrow_labels_must_exist_and_be_ordered():
    s = REGISTRY["house_bars"]
    assert "arrow_from" in s.validate({"arrow_from": "1999"})[1]
    assert "arrow_to" in s.validate({"arrow_from": "2026", "arrow_to": "2022"})[1]
    assert s.validate({"arrow_from": "", "arrow_to": ""})[1] == {}


def test_house_bars_colors():
    C = {"neutral": "N", "accent": "A"}
    p = {"bars": [{"highlight": False}] * 3, "highlight_color": "H", "after_color": "X"}
    assert house_bars.colors(p, C) == ["N", "N", "A"]
    p["bars"] = [{"highlight": False}, {"highlight": True}, {"highlight": False}]
    assert house_bars.colors(p, C) == ["N", "H", "X"]


def test_backdrop_county_needs_fips():
    assert "fips" in REGISTRY["ring"].validate({"backdrop": "county", "fips": None})[1]
    assert REGISTRY["ring"].validate({"backdrop": "state", "fips": None})[1] == {}


def test_max_value_checks():
    assert "max_value" in REGISTRY["bar_list"].validate({"max_value": 40})[1]
    assert "value" in REGISTRY["ring"].validate({"value": 120})[1]
    assert "high_value" in REGISTRY["thermometer"].validate({"low_value": 6, "high_value": 3})[1]


def test_house_grid_auto_unit_and_result():
    assert house_grid.auto_unit(3625, 2705) == 100
    assert house_grid.auto_unit(500, 300) == 25
    assert house_grid.auto_unit(90, 50) == 10
    p = {"before": 3625, "after": 2705, "before_label": "AUGUST 2025", "after_label": "AUGUST 2026"}
    assert house_grid.auto_result(p) == "920 FEWER HOMES FOR SALE IN ONE YEAR"
    p.update(after=4000, before_label="2019")
    assert house_grid.auto_result(p) == "375 MORE HOMES FOR SALE"
    assert "unit" in REGISTRY["house_grid"].validate({"unit": 10})[1]  # 363 simge çizilemez


def test_house_grid_counter_moves_from_before_to_after():
    fr, _ = frames("house_grid")
    try:
        fr.draw(1.0)
        assert fr.update.parts["counter"].get_text() == "3,625"
        fr.draw(7.4)
        assert fr.update.parts["counter"].get_text() == "2,705"
    finally:
        fr.close()


def test_ring_auto_remainder():
    assert ring.auto_remainder({"center_prefix": "$", "value": 94.3, "max_value": 100}) == "$6 OFF"


def test_line_trend_axis_and_ref_label_side():
    assert line_trend.axis([10, 20], None, True) == (0.0, 21.0)
    lo, hi = line_trend.axis([1500, 2000], None, False)
    assert 0 < lo < 1500 and hi == 2100
    xs = np.array([0, 100])
    assert line_trend.ref_label_side(xs, np.array([500, 500]), 300, 0, 100) == -1  # veri referansın üstünde: etiket altta
    assert line_trend.ref_label_side(xs, np.array([100, 100]), 300, 0, 100) == 1  # veri altta: etiket üstte


def test_tokenize_arrow_and_question_marks():
    assert cl.tokenize("$580K -> ?") == [("text", "$580K"), ("space",), ("arrow",), ("space",), ("q",)]
    assert cl.tokenize("#1 ?") == [("text", "#1"), ("space",), ("q",)]
    assert cl.tokenize("? IN 10") == [("q",), ("space",), ("text", "IN 10")]
    assert cl.tokenize("A→B") == [("text", "A"), ("arrow",), ("text", "B")]


def test_round_half_up():
    from engine.scene import round_half_up
    assert [round_half_up(v) for v in (0.5, 1.5, 2.5, 30.5, 30.54, -2.5, 29.49)] == [1, 2, 3, 31, 31, -3, 29]
    assert round_half_up(6.25, 1) == 6.3 and round_half_up(2.675, 2) == 2.68 and round_half_up(94.3, 1) == 94.3
    assert isinstance(round_half_up(2.5), int)
    assert cl.fmt_value(30.5, "count") == "31" and cl.fmt_value(2.5, "count") == "3" and cl.fmt_value(1234.5, "count") == "1,235"
    assert cl.fmt_value(6.25, "count", 1) == "6.3"
    assert cl.money_k(2500) == "$3K" and cl.money_k(1_250_000) == "$1.3M"


def test_bar_list_rounds_half_up_on_screen():
    rows = [{"label": "FLORIDA", "value": 30.5}, {"label": "X", "value": 2.5}, {"label": "Y", "value": 30.54}]
    fr, _ = frames("bar_list", rows=rows, decimals=0, value_suffix=" OF 100")
    try:
        fr.draw(6.4)
        texts = [t.get_text() for t in fr.update.parts["value_text"]]
        assert texts == ["31 OF 100", "3 OF 100", "31 OF 100"]
    finally:
        fr.close()


def test_money_format():
    assert cl.money_k(419000) == "$419K" and cl.money_k(1_250_000) == "$1.3M" and cl.money_k(2_000_000) == "$2M"
    assert cl.signed(-55000, "money_k") == "−$55K" and cl.signed(1840, "count") == "+1,840"
