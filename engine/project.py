"""Proje dosyası (JSON): sahne listesi, geçiş süresi, çıktı seçenekleri. Doğrulama, yükleme, kaydetme."""
import json
import os
import re

from engine.assets import ROOT
from scenes import REGISTRY

PROJECTS = os.path.join(ROOT, "projects")
VERSION = 1
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


class ProjectError(ValueError):
    pass


def default_output():
    return {"separate": True, "combined": True, "transparent": False}


def new_project(name="yeni_proje"):
    return {"version": VERSION, "name": name, "transition": 0.6, "output": default_output(),
            "scenes": [{"type": sid, "enabled": True, "params": REGISTRY[sid].defaults()}
                       for sid in ("state_map", "price_ladder")]}


def validate(project):
    """(temiz proje, hatalar). Yapısal sorunlarda ProjectError."""
    if not isinstance(project, dict):
        raise ProjectError("Proje bir JSON nesnesi olmalı.")
    if project.get("version") != VERSION:
        raise ProjectError(f"Desteklenmeyen proje sürümü: {project.get('version')!r}")
    errors = []

    def err(param, message, scene=None):
        errors.append({"scene": scene, "param": param, "message": message})

    name = str(project.get("name", ""))
    if not NAME_RE.match(name):
        err("name", "Ad yalnızca harf, rakam, _ ve - içerebilir.")
    try:
        transition = float(project.get("transition", 0.6))
    except (TypeError, ValueError):
        transition = 0.6
        err("transition", "Geçiş süresi sayı olmalı.")
    output = {**default_output(), **(project.get("output") or {})}
    output = {k: bool(output[k]) for k in default_output()}

    scenes = []
    for i, s in enumerate(project.get("scenes") or []):
        if not isinstance(s, dict) or s.get("type") not in REGISTRY:
            raise ProjectError(f"Bilinmeyen sahne tipi: {s.get('type') if isinstance(s, dict) else s!r}")
        clean, errs = REGISTRY[s["type"]].validate(s.get("params") or {})
        for k, m in errs.items():
            err(k, m, i)
        scenes.append({"type": s["type"], "enabled": bool(s.get("enabled", True)), "params": clean})

    enabled = [s for s in scenes if s["enabled"]]
    if not enabled:
        err("scenes", "En az bir sahne açık olmalı.")
    if not output["separate"] and not output["combined"]:
        err("output", "En az bir çıktı türü seçilmeli (ayrı dosyalar ya da birleşik video).")
    if not 0 <= transition <= 2:
        err("transition", "Geçiş süresi 0 ile 2 saniye arasında olmalı.")
    elif output["combined"] and len(enabled) > 1:
        shortest = min(float(s["params"]["duration"]) for s in enabled)
        if transition >= shortest:
            err("transition", f"Geçiş süresi en kısa sahneden ({shortest:g} sn) kısa olmalı.")
    clean = {"version": VERSION, "name": name, "transition": transition, "output": output, "scenes": scenes}
    return clean, errors


def path_for(name):
    if not NAME_RE.match(str(name)):
        raise ProjectError("Geçersiz proje adı.")
    return os.path.join(PROJECTS, f"{name}.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ProjectError(f"Proje okunamadı: {e}") from e
    return validate(data)


def save(project, path=None):
    path = path or path_for(project["name"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def list_projects():
    if not os.path.isdir(PROJECTS):
        return []
    return sorted(f[:-5] for f in os.listdir(PROJECTS) if f.endswith(".json") and NAME_RE.match(f[:-5]))
