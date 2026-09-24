import json

import pytest

from engine import brand


@pytest.fixture(autouse=True)
def fresh_cache():
    brand.load.cache_clear()
    yield
    brand.load.cache_clear()


def test_repo_file_matches_defaults():
    assert brand.load() == brand.DEFAULTS
    assert [c["key"] for c in brand.categories()][-1] == "none"
    assert brand.color("accent") == "#ff7a1f"
    assert brand.category_color("price") == "#e9b949"


def test_missing_file_uses_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(brand, "PATH", str(tmp_path / "yok.json"))
    assert brand.load() == brand.DEFAULTS


def test_partial_override_is_merged(tmp_path, monkeypatch):
    f = tmp_path / "brand.json"
    f.write_text(json.dumps({"colors": {"accent": "#00FF00"}, "fonts": {"place": "x/Y-Regular.ttf"}}), encoding="utf-8")
    monkeypatch.setattr(brand, "PATH", str(f))
    assert brand.color("accent") == "#00ff00"
    assert brand.color("loss") == brand.DEFAULTS["colors"]["loss"]
    assert brand.fonts()["place"] == "x/Y-Regular.ttf" and brand.fonts()["numbers"] == brand.DEFAULTS["fonts"]["numbers"]
    assert brand.categories() == brand.DEFAULTS["categories"]


@pytest.mark.parametrize("data", [
    {"colors": {"accent": "turuncu"}},
    {"categories": [{"key": "a", "label": "A", "color": "#000000"}, {"key": "b", "label": "B", "color": "#111111"}]},
    {"categories": [{"key": "none", "label": "YOK", "color": "#000000"}]},
    {"fonts": {"place": ""}},
    ["liste"],
])
def test_invalid_brand_raises(tmp_path, monkeypatch, data):
    f = tmp_path / "brand.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(brand, "PATH", str(f))
    with pytest.raises(brand.BrandError):
        brand.load()


def test_broken_json_raises(tmp_path, monkeypatch):
    f = tmp_path / "brand.json"
    f.write_text("{bozuk", encoding="utf-8")
    monkeypatch.setattr(brand, "PATH", str(f))
    with pytest.raises(brand.BrandError, match="okunamadı"):
        brand.load()


def test_accessors_return_copies():
    brand.categories()[0]["label"] = "DEĞİŞTİ"
    brand.colors()["accent"] = "#000000"
    assert brand.categories()[0]["label"] == "BUYERS PULLED BACK"
    assert brand.color("accent") == "#ff7a1f"
