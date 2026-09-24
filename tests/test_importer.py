import io

import openpyxl
import pytest

from engine import geo, importer

CATS = [
    {"key": "buyers", "label": "BUYERS PULLED BACK", "color": "#ff5a4f"},
    {"key": "price", "label": "PRICES BREAKING", "color": "#ffb020"},
    {"key": "none", "label": "NOT ENOUGH DATA", "color": "#16233a"},
]


@pytest.mark.parametrize("a,b", [
    ("St. Lucie", "Saint Lucie County"),
    ("Miami-Dade County", "miami dade"),
    ("DeSoto", "De Soto Parish"),
])
def test_norm_equal(a, b):
    assert importer.norm(a) == importer.norm(b)


@pytest.mark.parametrize("text", ["St. Lucie", "Saint Lucie County", "12111", "111", "12111.0", "st lucie"])
def test_match_florida(text):
    c, cands = importer.CountyMatcher(geo.counties("12")).match(text)
    assert c is not None and c.fips == "12111" and cands == []


def test_match_virginia_ambiguous_and_exact():
    m = importer.CountyMatcher(geo.counties("51"))
    c, cands = m.match("Richmond")
    assert c is None and {x.display for x in cands} == {"Richmond city", "Richmond County"}
    assert m.match("Richmond city")[0].fips == "51760"
    assert m.match("richmond COUNTY")[0].fips == "51159"


def test_match_unknown():
    assert importer.CountyMatcher(geo.counties("12")).match("Atlantis") == (None, [])


def test_parse_csv_semicolon_labels():
    data = "County;Kategori\nSt. Lucie;BUYERS PULLED BACK\nCharlotte;price\nAtlantis;price\nLee;bilinmiyor\n".encode("utf-8")
    res = importer.parse_assignments("veri.csv", data, geo.counties("12"), CATS)
    assert res["assign"] == {"12111": "buyers", "12015": "price"}
    assert [(u["row"], u["reason"]) for u in res["unmatched"]] == [(4, "county bulunamadı"), (5, "kategori bulunamadı")]
    assert res["ambiguous"] == []


def test_parse_csv_unknown_headers_uses_first_two_columns():
    res = importer.parse_assignments("x.csv", b"a,b\n12015,buyers\n", geo.counties("12"), CATS)
    assert res["assign"] == {"12015": "buyers"}


def test_parse_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["fips", "category"])
    ws.append([12015, "price"])
    ws.append([12111, "BUYERS PULLED BACK"])
    buf = io.BytesIO()
    wb.save(buf)
    res = importer.parse_assignments("veri.xlsx", buf.getvalue(), geo.counties("12"), CATS)
    assert res["assign"] == {"12015": "price", "12111": "buyers"}


def test_parse_ambiguous():
    res = importer.parse_assignments("v.csv", b"county,category\nRichmond,price\n", geo.counties("51"), CATS)
    assert res["assign"] == {}
    assert res["ambiguous"][0]["row"] == 2
    assert set(res["ambiguous"][0]["candidates"]) == {"Richmond city", "Richmond County"}


def test_empty_file():
    with pytest.raises(ValueError):
        importer.parse_assignments("v.csv", b"", geo.counties("12"), CATS)
