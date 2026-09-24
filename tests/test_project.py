import pytest

from engine import project as proj


def test_new_project_is_valid():
    clean, errors = proj.validate(proj.new_project())
    assert errors == []
    assert [s["type"] for s in clean["scenes"]] == ["state_map", "price_ladder"]


def test_sample_project_is_valid():
    clean, errors = proj.load(proj.path_for("ornek_florida"))
    assert errors == [] and clean["name"] == "ornek_florida"


def test_roundtrip_keeps_float_precision(tmp_path, monkeypatch):
    monkeypatch.setattr(proj, "PROJECTS", str(tmp_path))
    p = proj.new_project("deneme_1")
    p["scenes"][0]["params"]["zoom"] = 0.822673668267268
    path = proj.save(p)
    assert path == str(tmp_path / "deneme_1.json")
    clean, errors = proj.load(path)
    assert errors == [] and clean["scenes"][0]["params"]["zoom"] == 0.822673668267268
    assert proj.list_projects() == ["deneme_1"]


def test_structural_errors():
    with pytest.raises(proj.ProjectError, match="sürüm"):
        proj.validate({"version": 99})
    p = proj.new_project()
    p["scenes"][0]["type"] = "yok"
    with pytest.raises(proj.ProjectError, match="sahne tipi"):
        proj.validate(p)
    with pytest.raises(proj.ProjectError):
        proj.validate("bozuk")


def test_param_errors_have_scene_index():
    p = proj.new_project()
    p["scenes"][1]["params"]["accent"] = "mavi"
    _, errors = proj.validate(p)
    assert errors == [{"scene": 1, "param": "accent", "message": "#rrggbb biçiminde bir renk olmalı"}]


def test_project_level_rules():
    p = proj.new_project()
    p["name"] = "boşluklu ad"
    p["transition"] = 50
    p["output"] = {"separate": False, "combined": False, "transparent": False}
    for s in p["scenes"]:
        s["enabled"] = False
    _, errors = proj.validate(p)
    assert {e["param"] for e in errors} == {"name", "transition", "output", "scenes"}


def test_transition_must_be_shorter_than_scenes(dummy_scene, monkeypatch):
    monkeypatch.setitem(proj.REGISTRY, "dummy", dummy_scene)
    p = {"version": 1, "name": "t", "transition": 1.0, "output": proj.default_output(),
         "scenes": [{"type": "dummy", "params": {"duration": 0.8}}, {"type": "dummy", "params": {}}]}
    assert [e["param"] for e in proj.validate(p)[1]] == ["transition"]
    p["transition"] = 0.5
    assert proj.validate(p)[1] == []


def test_bad_json_and_bad_name(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("{bozuk", encoding="utf-8")
    with pytest.raises(proj.ProjectError):
        proj.load(str(f))
    with pytest.raises(proj.ProjectError):
        proj.path_for("../kacis")
