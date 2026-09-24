"""Harita Stüdyosu web sunucusu. run_ui.py ile yalnızca 127.0.0.1 üzerinde çalıştırılır."""
import base64
import datetime as dt
import hashlib
import json
import os
import threading

from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.jobs import BusyError, JobManager
from engine import assets, geo, importer, render
from engine import project as proj
from engine.params import Categories
from scenes import REGISTRY

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
OUT = os.path.join(assets.ROOT, "out")

app = FastAPI(title="Harita Stüdyosu")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
jobs = JobManager(assets.ROOT)
_preview = {"key": None, "frames": None}
_preview_lock = threading.Lock()


def fail(status, message, **extra):
    raise HTTPException(status, detail={"message": message, **extra})


def safe_path(base, rel):
    base = os.path.realpath(base)
    full = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, full]) != base:
        fail(403, "Bu yola erişilemez.")
    return full


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"), headers={"Cache-Control": "no-store"})


@app.get("/api/scenes")
def scenes():
    return [s.schema() for s in REGISTRY.values()]


@app.get("/api/states")
def states():
    return [{"abbr": abbr, "name": name, "fips": fips} for fips, abbr, name in geo.STATES]


@app.get("/api/geo/{abbr}")
def county_geo(abbr: str):
    try:
        fips = geo.state(abbr)[0]
    except ValueError as e:
        fail(404, str(e))
    return geo.county_svg(fips)


@app.get("/api/projects")
def list_projects():
    return {"projects": proj.list_projects()}


@app.get("/api/projects/_new")
def new_project():
    return proj.new_project()


@app.post("/api/projects/import")
def import_project(project: dict = Body(...), overwrite: bool = False):
    """Dışarıdan gelen proje JSON'unu doğrular ve projects/<name>.json olarak kaydeder.
    Dosya olduğu gibi kaydedilir (eksik alanlar dondurulmaz, marka varsayılanları geçerli kalır)."""
    try:
        clean, errors = proj.validate(project)
    except proj.ProjectError as e:
        fail(400, str(e))
    if errors:
        fail(422, "Proje dosyasında hatalar var.", errors=errors)
    path = proj.path_for(clean["name"])
    if os.path.exists(path) and not overwrite:
        fail(409, f"\"{clean['name']}\" adında bir proje zaten var.", name=clean["name"])
    proj.save(project, path)
    return {"saved": clean["name"], "project": clean}


@app.get("/api/projects/{name}")
def load_project(name: str):
    try:
        path = proj.path_for(name)
        if not os.path.exists(path):
            fail(404, "Proje bulunamadı.")
        project, errors = proj.load(path)
    except proj.ProjectError as e:
        fail(400, str(e))
    return {"project": project, "errors": errors}


@app.put("/api/projects/{name}")
def save_project(name: str, project: dict = Body(...)):
    try:
        path = proj.path_for(name)
        project = {**project, "name": name}
        _, errors = proj.validate(project)
        proj.save(project, path)
    except proj.ProjectError as e:
        fail(400, str(e))
    return {"saved": name, "errors": errors}


@app.post("/api/validate")
def validate(project: dict = Body(...)):
    try:
        _, errors = proj.validate(project)
    except proj.ProjectError as e:
        errors = [{"scene": None, "param": None, "message": str(e)}]
    return {"errors": errors}


@app.post("/api/preview")
def preview(body: dict = Body(...)):
    scene = REGISTRY.get(body.get("type"))
    if scene is None:
        fail(400, "Bilinmeyen sahne tipi.")
    clean, errors = scene.validate(body.get("params") or {})
    if errors:
        fail(422, "Ayarlarda hata var.", errors=errors)
    transparent = bool(body.get("transparent"))
    try:
        t = min(max(float(body.get("t", 0)), 0.0), float(clean["duration"]))
    except (TypeError, ValueError):
        fail(400, "Geçersiz zaman.")
    key = hashlib.sha1(json.dumps([scene.id, clean, transparent], sort_keys=True).encode()).hexdigest()
    with _preview_lock:
        try:
            if _preview["key"] != key:
                if _preview["frames"] is not None:
                    _preview["frames"].close()
                _preview["frames"], _preview["key"] = None, None
                _preview["frames"] = render.Frames(scene, clean, transparent, dpi=50)
                _preview["key"] = key
            png = render.to_png(_preview["frames"].draw(t))
        except Exception as e:
            fail(500, f"Önizleme çizilemedi: {e}")
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/api/import-assignments")
def import_assignments(body: dict = Body(...)):
    try:
        fips = geo.state(body.get("state"))[0]
        cats = Categories("categories", "Kategoriler").validate(body.get("categories"), {})
        data = base64.b64decode(body.get("content_b64") or "")
        return importer.parse_assignments(str(body.get("filename") or ""), data, geo.counties(fips), cats)
    except Exception as e:
        fail(400, f"Dosya okunamadı: {e}")


@app.post("/api/render")
def start_render(body: dict = Body(...)):
    try:
        clean, errors = proj.validate(body.get("project"))
    except proj.ProjectError as e:
        fail(400, str(e))
    if errors:
        fail(422, "Projede hatalı ayarlar var.", errors=errors)
    out_dir = os.path.join(OUT, clean["name"], dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        job = jobs.start(clean, out_dir)
    except BusyError as e:
        fail(409, str(e))
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        fail(404, "İş bulunamadı.")
    return job.to_dict(OUT)


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = jobs.cancel(job_id)
    if job is None:
        fail(404, "İş bulunamadı.")
    return job.to_dict(OUT)


@app.get("/api/outputs/{rel:path}")
def output_file(rel: str):
    path = safe_path(OUT, rel)
    if not os.path.isfile(path):
        fail(404, "Dosya bulunamadı.")
    return FileResponse(path)


@app.post("/api/open-folder")
def open_folder(body: dict = Body(...)):
    path = safe_path(OUT, str(body.get("path") or ""))
    if os.path.isfile(path):
        path = os.path.dirname(path)
    if not os.path.isdir(path):
        fail(404, "Klasör bulunamadı.")
    if not hasattr(os, "startfile"):
        fail(501, "Bu işlem yalnızca Windows'ta destekleniyor.")
    os.startfile(path)
    return {"opened": True}
