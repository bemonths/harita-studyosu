import base64
import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import server
from engine import project as proj


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(proj, "PROJECTS", str(tmp_path / "projects"))
    monkeypatch.setattr(server, "OUT", str(tmp_path / "out"))
    return TestClient(server.app)


def new(client):
    return client.get("/api/projects/_new").json()


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200 and "Harita Stüdyosu" in r.text


def test_scenes_and_states(client):
    assert [s["id"] for s in client.get("/api/scenes").json()] == ["state_map", "county_focus", "price_ladder"]
    states = client.get("/api/states").json()
    assert len(states) == 48 and states[0] == {"abbr": "AL", "name": "Alabama", "fips": "01"}


def test_geo(client):
    assert len(client.get("/api/geo/FL").json()["counties"]) == 67
    assert client.get("/api/geo/XX").status_code == 404


def test_project_save_and_load(client):
    p = new(client)
    r = client.put("/api/projects/deneme", json=p)
    assert r.status_code == 200 and r.json()["errors"] == []
    assert client.get("/api/projects").json() == {"projects": ["deneme"]}
    assert client.get("/api/projects/deneme").json()["project"]["name"] == "deneme"
    assert client.get("/api/projects/yok").status_code == 404
    assert client.put("/api/projects/kötü ad", json=p).status_code == 400


def test_validate(client):
    p = new(client)
    p["scenes"][0]["params"]["accent"] = "mavi"
    errs = client.post("/api/validate", json=p).json()["errors"]
    assert errs[0]["scene"] == 0 and errs[0]["param"] == "accent"
    assert client.post("/api/validate", json={"version": 9}).json()["errors"][0]["param"] is None


def test_preview(client):
    s = new(client)["scenes"][0]
    r = client.post("/api/preview", json={"type": s["type"], "params": s["params"], "t": 8.6})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (960, 540)
    again = client.post("/api/preview", json={"type": s["type"], "params": s["params"], "t": 2.0})
    assert again.status_code == 200 and again.content != r.content
    bad = client.post("/api/preview", json={"type": s["type"], "params": {**s["params"], "accent": "x"}, "t": 1})
    assert bad.status_code == 422 and "accent" in bad.json()["detail"]["errors"]


def test_import_assignments(client):
    cats = new(client)["scenes"][0]["params"]["categories"]
    body = {"state": "FL", "categories": cats, "filename": "a.csv",
            "content_b64": base64.b64encode(b"county,category\nCharlotte,price\n").decode()}
    assert client.post("/api/import-assignments", json=body).json()["assign"] == {"12015": "price"}
    assert client.post("/api/import-assignments", json={**body, "filename": "a.xlsx"}).status_code == 400


def test_outputs_are_confined(client, tmp_path):
    (tmp_path / "out" / "p").mkdir(parents=True)
    (tmp_path / "out" / "p" / "a.mp4").write_bytes(b"123")
    (tmp_path / "gizli.txt").write_text("x")
    assert client.get("/api/outputs/p/a.mp4").content == b"123"
    assert client.get("/api/outputs/%2E%2E/gizli.txt").status_code in (403, 404)
    assert client.post("/api/open-folder", json={"path": "../"}).status_code == 403


def test_render_rejects_invalid_project(client):
    p = new(client)
    p["scenes"][0]["params"]["accent"] = "x"
    r = client.post("/api/render", json={"project": p})
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["param"] == "accent"


@pytest.mark.slow
def test_render_job_end_to_end(client):
    p = new(client)
    p["name"] = "hizli"
    p["scenes"] = p["scenes"][1:]
    p["scenes"][0]["params"]["duration"] = 5.75
    job_id = client.post("/api/render", json={"project": p}).json()["job_id"]
    deadline = time.time() + 300
    while time.time() < deadline:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["state"] != "running":
            break
        time.sleep(1)
    assert j["state"] == "done", j
    assert len(j["outputs"]) == 1 and j["outputs"][0].endswith("01_price_ladder.mp4")
    assert client.get(f"/api/outputs/{j['outputs'][0]}").status_code == 200


def test_static_assets(client):
    html = client.get("/").text
    assert '<script type="module" src="/static/js/main.js">' in html
    for f in ("style.css", "js/main.js", "js/api.js", "js/state.js", "js/form.js", "js/preview.js",
              "js/countymap.js", "js/render.js", "js/pricetable.js", "js/dom.js"):
        assert client.get(f"/static/{f}").status_code == 200, f


def test_import_project_saves_and_conflicts(client):
    p = new(client)
    p["name"] = "disaridan"
    r = client.post("/api/projects/import", json=p)
    assert r.status_code == 200 and r.json()["saved"] == "disaridan"
    assert r.json()["project"]["scenes"][0]["type"] == "state_map"
    assert "disaridan" in client.get("/api/projects").json()["projects"]
    again = client.post("/api/projects/import", json=p)
    assert again.status_code == 409 and again.json()["detail"]["name"] == "disaridan"
    assert client.post("/api/projects/import?overwrite=true", json=p).status_code == 200


def test_import_project_rejects_invalid(client):
    p = new(client)
    p["name"] = "bozuk"
    p["scenes"][0]["params"]["accent"] = "x"
    r = client.post("/api/projects/import", json=p)
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["param"] == "accent"
    assert "bozuk" not in client.get("/api/projects").json()["projects"]
    assert client.post("/api/projects/import", json={"version": 9}).status_code == 400


def test_import_keeps_file_as_given(client, tmp_path):
    import json

    p = {"version": 1, "name": "kisa", "scenes": [{"type": "county_focus", "params": {"state": "FL", "focus": "12015"}}]}
    r = client.post("/api/projects/import", json=p)
    assert r.status_code == 200
    saved = json.loads((tmp_path / "projects" / "kisa.json").read_text(encoding="utf-8"))
    assert saved == p  # marka varsayılanları dosyaya dondurulmaz
    assert r.json()["project"]["scenes"][0]["params"]["categories"][-1]["key"] == "none"


def test_project_list_sees_external_files(client, tmp_path):
    (tmp_path / "projects").mkdir(exist_ok=True)
    assert client.get("/api/projects").json()["projects"] == []
    (tmp_path / "projects" / "fredpull_fl.json").write_text("{}", encoding="utf-8")
    assert client.get("/api/projects").json()["projects"] == ["fredpull_fl"]
