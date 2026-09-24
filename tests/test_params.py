import pytest

from engine import params as P

CATS = [{"key": "a", "label": "A", "color": "#FF0000"}, {"key": "none", "label": "YOK", "color": "#000000"}]


def test_text():
    t = P.Text("title", "Başlık", default="")
    assert t.validate(None, {}) == ""
    assert t.validate("FLORIDA", {}) == "FLORIDA"
    with pytest.raises(P.ParamError):
        t.validate(5, {})
    with pytest.raises(P.ParamError):
        P.Text("x", "X", max_len=3).validate("abcd", {})


def test_color():
    c = P.Color("c", "Renk", default="#000000")
    assert c.validate("#3EE6FF", {}) == "#3ee6ff"
    for bad in ("3ee6ff", "#12345", "red", None):
        with pytest.raises(P.ParamError, match="#rrggbb"):
            c.validate(bad, {})


def test_number():
    n = P.Number("z", "Z", default=1.0, lo=0.5, hi=2.0)
    assert n.validate("1.25", {}) == 1.25
    assert n.validate(0.822673668267268, {}) == 0.822673668267268  # adıma yuvarlanmaz
    for bad in (0.4, 2.1, "abc", True, None, float("nan")):
        with pytest.raises(P.ParamError):
            n.validate(bad, {})
    opt = P.Number("p", "P", lo=0, integer=True, optional=True)
    assert opt.validate(None, {}) is None and opt.validate("", {}) is None
    v = opt.validate(310000.0, {})
    assert v == 310000 and isinstance(v, int)
    with pytest.raises(P.ParamError):
        opt.validate(1.5, {})


def test_date():
    d = P.Date("d", "D", default="2026-09-23")
    assert d.validate("2026-09-23", {}) == "2026-09-23"
    with pytest.raises(P.ParamError):
        d.validate("23.09.2026", {})


def test_state_and_county():
    vals = {"state": P.StateSelect("state", "Eyalet").validate("FL", {})}
    cs = P.CountySelect("focus", "Vurgu", state_param="state")
    assert cs.validate("12015", vals) == "12015"
    assert cs.validate(None, vals) is None and cs.validate("", vals) is None
    with pytest.raises(P.ParamError):
        cs.validate("48201", vals)
    with pytest.raises(P.ParamError):
        P.StateSelect("state", "E").validate("AK", {})


def test_categories():
    c = P.Categories("categories", "K")
    assert c.validate(CATS, {})[0] == {"key": "a", "label": "A", "color": "#ff0000"}
    bad_sets = [
        CATS[:1],                                               # tek kategori
        list(reversed(CATS)),                                   # none sonda değil
        [CATS[0], dict(CATS[0]), CATS[1]],                      # tekrar eden anahtar
        [{**CATS[0], "label": " "}, CATS[1]],                   # boş etiket
        [{**CATS[0], "key": f"k{i}"} for i in range(7)] + [CATS[1]],  # 8 kategori
        "bozuk",
    ]
    for bad in bad_sets:
        with pytest.raises(P.ParamError):
            c.validate(bad, {})


def test_county_assign():
    vals = {"state": "FL", "categories": P.Categories("categories", "K").validate(CATS, {})}
    a = P.CountyAssign("assign", "A", state_param="state", categories_param="categories")
    assert a.validate({"12111": "a", "12015": "a", "12001": "none"}, vals) == {"12015": "a", "12111": "a"}
    assert a.validate(None, vals) == {}
    with pytest.raises(P.ParamError):
        a.validate({"48201": "a"}, vals)
    with pytest.raises(P.ParamError):
        a.validate({"12015": "zzz"}, vals)


def test_price_table():
    t = P.PriceTable("history", "H")
    ok = t.validate([{"date": "2024-08-15", "price": "580000"}, {"date": "2024-09-11", "price": 574999.0}], {})
    assert ok == [{"date": "2024-08-15", "price": 580000}, {"date": "2024-09-11", "price": 574999}]
    bad_sets = [
        [{"date": "2024-08-15", "price": 1}],
        [{"date": "2024-08-15", "price": 2}, {"date": "2024-08-15", "price": 1}],
        [{"date": "2024-08-15", "price": 2}, {"date": "2024-09-15", "price": 2}],
        [{"date": "2024-08-15", "price": 0}, {"date": "2024-09-15", "price": 2}],
        [{"date": "bozuk", "price": 2}, {"date": "2024-09-15", "price": 1}],
        ["satır", {"date": "2024-09-15", "price": 1}],
    ]
    for bad in bad_sets:
        with pytest.raises(P.ParamError):
            t.validate(bad, {})


def test_validate_all_fills_defaults_and_collects_errors():
    ps = [
        P.StateSelect("state", "E", default="FL"),
        P.CountySelect("focus", "V", state_param="state"),
        P.Color("accent", "R", default="#3ee6ff"),
    ]
    clean, errors = P.validate_all(ps, {"focus": "12015", "accent": "kırmızı"})
    assert clean == {"state": "FL", "focus": "12015", "accent": "#3ee6ff"}
    assert list(errors) == ["accent"]


def test_validate_all_copies_defaults():
    p = P.Categories("categories", "K", default=CATS)
    clean, errors = P.validate_all([p], {"categories": "bozuk"})
    assert "categories" in errors
    clean["categories"].append({"key": "x"})
    assert len(p.default) == 2


def test_schema():
    s = P.Number("z", "Z", default=1.0, lo=0.5, hi=2.0, step=0.01, group="Kamera").schema()
    assert s == {"name": "z", "label": "Z", "kind": "number", "default": 1.0, "group": "Kamera", "help": "",
                 "min": 0.5, "max": 2.0, "step": 0.01, "integer": False, "optional": False}
    assert P.StateSelect("state", "E").schema()["options"][0] == {"value": "AL", "label": "Alabama"}
    assert P.CountyAssign("assign", "A").schema()["categories_param"] == "categories"
