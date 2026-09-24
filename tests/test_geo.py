import numpy as np
import pytest

from engine import geo


def test_state_table():
    assert len(geo.STATES) == 48
    assert geo.state("FL") == ("12", "FL", "Florida")
    with pytest.raises(ValueError):
        geo.state("AK")


def test_albers_origin():
    x, y = geo.albers(np.array([-96.0]), np.array([23.0]))
    assert abs(x[0]) < 1e-12 and abs(y[0]) < 1e-12


def test_outlines_cover_all_states():
    full, simp = geo._outlines()
    assert list(full) == list(simp)
    for fips, _, _ in geo.STATES:
        assert full[fips] and simp[fips]
    assert "11" in simp  # DC arka planda çizilir


def test_us_outlines_selected_state_full_resolution():
    us = geo.us_outlines("12")
    assert [st for st, _ in us] == list(geo._outlines()[1])
    fl = dict(us)["12"]
    assert sum(len(r) for r in fl) == sum(len(r) for r in geo._outlines()[0]["12"])


def test_florida_counties():
    cs = geo.counties("12")
    assert len(cs) == 67
    ch = next(c for c in cs if c.name == "Charlotte")
    assert ch.fips == "12015" and ch.display == "Charlotte"
    assert ch.rings[0].shape[1] == 2


def test_duplicate_names_get_lsad():
    names = {c.display for c in geo.counties("51")}
    assert {"Richmond city", "Richmond County"} <= names


def test_county_svg():
    svg = geo.county_svg("12")
    assert svg["width"] == 1000 and svg["height"] > 0
    assert len(svg["counties"]) == 67
    assert svg["counties"][0]["d"].startswith("M")
