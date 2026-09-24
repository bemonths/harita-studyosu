# Harita Stüdyosu Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `anim/` klasöründeki iki sahnelik matplotlib animasyonunu, 48 ABD eyaletinde çalışan, tarayıcıdan kontrol edilen (ayar paneli + önizleme + render) bir araca dönüştürmek.

**Architecture:** `engine/` saf Python çekirdeği sağlar: veri, geometri, ayar tipleri, çerçeveleme, render, birleştirme, proje dosyası ve CLI. `scenes/` iki sahneyi sabit değer yerine ayarla çalışan `Scene` nesneleri olarak tanımlar. `app/` FastAPI sunucusu ve derleme adımı olmayan HTML/JS arayüzdür. Render ayrı bir süreçte `engine.cli` ile yapılır. Görsel doğruluk, orijinal koddan alınan referans karelerle karşılaştırılarak test edilir.

**Tech Stack:** Python 3.12, numpy, matplotlib (Agg), shapely, imageio-ffmpeg (ffmpeg 7.1), FastAPI + uvicorn, openpyxl, pytest + httpx, vanilla ES modules.

**Spec:** `docs/superpowers/specs/2026-09-24-harita-studyosu-design.md`

## Global Constraints

- Platform Windows 10, Python 3.12 (`.venv\Scripts\python`). Bütün komutlar `anim/` klasöründe çalıştırılır.
- Video 1920x1080, 30 fps. Opak çıktı `libx264 -preset medium -crf 17 -pix_fmt yuv420p` (.mp4), şeffaf çıktı `prores_ks -profile:v 4444 -pix_fmt yuva444p10le` (.mov).
- Sahnelerin görünümü ve zamanlamaları orijinal `scene_a.py` ve `scene_b.py` ile aynı kalır. `ornek_florida` projesi referans karelerle ortalama mutlak piksel farkı < 1,5/255 olacak şekilde eşleşmelidir (istisna: Görev 10'daki başlık alanı).
- Arayüz metinleri Türkçe, video içi varsayılan metinler İngilizce.
- Sunucu yalnızca `127.0.0.1` adresini dinler. Dosya yolları `out/` ve `projects/` dışına çıkamaz.
- Yeni bağımlılık yalnızca: fastapi, uvicorn, openpyxl (çalışma zamanı); pytest, httpx (test).
- Proje FredPull ya da başka bir projeyle ilişkili değildir, hiçbir dosyada böyle bir referans yer almaz.
- Uzun render testleri `@pytest.mark.slow` ile işaretlenir. Normal çalıştırma `python -m pytest`, uzun testler `python -m pytest -m slow`.
- Commit mesajları Türkçe, sonunda: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Dosya haritası

| Dosya | Sorumluluk |
|---|---|
| `engine/assets.py` | `data/` yolları, veri ve font indirme, eski yerleşimden taşıma, `fonts()` |
| `engine/geo.py` | eyalet tablosu, Albers, eyalet sınırları (tam/sade), county listesi, arayüz SVG'si |
| `engine/importer.py` | CSV/Excel okuma, county adı/FIPS eşleme |
| `engine/params.py` | ayar tipleri, `schema()`, `validate()`, `validate_all()` |
| `engine/framing.py` | eyalet/ABD/vurgu kamerası |
| `engine/scene.py` | `Scene`, `SceneContext`, `ease`, `seg`, `fit_text`, `FPS` |
| `engine/render.py` | `Frames` (kurulmuş figür), `to_png`, `still_png`, `render_video` |
| `engine/compose.py` | xfade zinciri |
| `engine/project.py` | proje JSON doğrula/yükle/kaydet |
| `engine/cli.py` | `render` ve `still` komutları, JSON ilerleme olayları |
| `scenes/state_map.py` | eyalet haritası sahnesi |
| `scenes/price_ladder.py` | fiyat merdiveni sahnesi |
| `scenes/__init__.py` | `REGISTRY` |
| `app/jobs.py` | render işi süreci ve ilerleme takibi |
| `app/server.py` | FastAPI uçları |
| `app/static/*` | arayüz |
| `run_ui.py`, `kurulum.bat`, `baslat.bat` | başlatıcılar |
| `projects/ornek_florida.json` | orijinal videonun değerleri |
| `tests/*` | pytest testleri |

---

### Task 1: Ortam ve referans (TAMAMLANDI, plan yazılırken yapıldı)

**Files:** `reference/` (git dışı)

- [x] **Step 1:** `py -3.12 -m venv .venv` ve `.venv\Scripts\python -m pip install -r requirements.txt` komutları çalıştırıldı.
- [x] **Step 2:** Orijinal `render_all.py` çalıştırıldı. Sonuç: `out/ornek_animasyon_florida.mp4`, `count_frames_and_secs` = `(717, 23.9)`. Veri indirme dahil toplam süre 112,5 sn.
- [x] **Step 3:** Referans kareler alındı ve video kopyalandı:
  - Sahne A için `TEST=2.0,4.0,6.0,8.6,10.5,12.5` ile, sahne B için `TEST=1.0,5.0,8.0,10.5` ile kareler üretildi.
  - Kareler `reference/test_a_*.png` ve `reference/test_b_*.png` olarak saklandı.
  - Video `reference/ornek_orijinal.mp4` olarak kopyalandı.
- [x] **Step 4:** Doğrulanan gerçekler:
  - matplotlib'in RGBA tamponu ön çarpımsız (straight alpha).
  - ffmpeg 7.1'de `prores_ks` var ve `xfade` alfayı `yuva444p10le` formatında koruyor.
  - `counties.json` özellikleri: `STATE`, `COUNTY`, `NAME`, `LSAD`. Feature `id` 5 haneli FIPS.
  - Aynı eyalette aynı adı taşıyan kayıtlar var: VA Richmond/Fairfax/Bedford/Franklin/Roanoke, MO St. Louis, MD Baltimore.
  - Eyalet birleştirme 0,4 sn sürüyor.
  - Florida sabitleri: `CAM_FL = [0.14131970888099443, 0.08739125759532332, 0.2736116695463418]`. `REGION=(0.40, 0.96, 0.08, 0.94)` ile birebir üretmek için gereken ince ayar `zoom=0.822673668267268, shift_x=-0.009999999999999926, shift_y=0.05222222222222225`.
  - Charlotte (12015) vurgu kadrajında ekranın %8,6'sını kaplıyor, %5–30 sınırına takılmıyor.

---

### Task 2: Proje iskeleti ve `engine/assets.py`

**Files:**
- Modify: `requirements.txt`, `.gitignore`
- Create: `requirements-dev.txt`, `pytest.ini`, `engine/__init__.py`, `scenes/__init__.py`, `tests/__init__.py`, `engine/assets.py`
- Test: `tests/test_assets.py`

**Interfaces:**
- Produces:
  - `assets.ROOT`, `assets.DATA`, `assets.FONT_DIR`, `assets.COUNTIES` (str yollar).
  - `assets.FONTS` (anahtar → Google Fonts yolu), `assets.font_path(key) -> str`, `assets.missing() -> list[str]`.
  - `assets.ensure(log=print) -> None` (hata durumunda `AssetError`).
  - `assets.fonts() -> {"bebas","regular","semibold","bold": FontProperties}`, `assets.AssetError`.

- [ ] **Step 1: Bağımlılık ve test ayarlarını yaz**

`requirements.txt`:
```
numpy>=1.26
matplotlib>=3.8
shapely>=2.0
imageio-ffmpeg>=0.5
fastapi>=0.110
uvicorn>=0.29
openpyxl>=3.1
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0
httpx>=0.27
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -m "not slow"
markers =
    slow: uzun süren render testleri (python -m pytest -m slow)
```

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
data/
out/
reference/
# eski yerleşim (Görev 15'teki temizliğe kadar)
fonts/
counties.json
state_outlines.json
```

`engine/__init__.py`, `tests/__init__.py`: boş dosya.

`scenes/__init__.py`:
```python
"""Sahne kaydı: sahne id -> Scene."""
REGISTRY = {}
```

Run: `.venv\Scripts\python -m pip install -r requirements-dev.txt`
Expected: fastapi, uvicorn, openpyxl, pytest, httpx kurulur.

- [ ] **Step 2: Başarısız testi yaz** — `tests/test_assets.py`

```python
import os

import pytest

from engine import assets


def _point_to(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(assets, "ROOT", str(tmp_path))
    monkeypatch.setattr(assets, "DATA", str(data))
    monkeypatch.setattr(assets, "FONT_DIR", str(data / "fonts"))
    monkeypatch.setattr(assets, "COUNTIES", str(data / "counties.json"))


def test_font_paths_under_data():
    for key in assets.FONTS:
        assert assets.font_path(key).startswith(assets.FONT_DIR)


def test_ensure_moves_old_layout(tmp_path, monkeypatch):
    _point_to(tmp_path, monkeypatch)
    (tmp_path / "fonts").mkdir()
    (tmp_path / "counties.json").write_bytes(b"x" * 2000)
    for key in assets.FONTS:
        (tmp_path / "fonts" / os.path.basename(assets.FONTS[key])).write_bytes(b"y" * 2000)

    def no_download(*args, **kwargs):
        raise AssertionError("indirme yapılmamalıydı")

    monkeypatch.setattr(assets.urllib.request, "urlretrieve", no_download)
    assets.ensure(log=lambda m: None)
    assert assets.missing() == []
    assert not (tmp_path / "counties.json").exists()


def test_ensure_reports_download_failure(tmp_path, monkeypatch):
    _point_to(tmp_path, monkeypatch)

    def broken(*args, **kwargs):
        raise OSError("ağ yok")

    monkeypatch.setattr(assets.urllib.request, "urlretrieve", broken)
    with pytest.raises(assets.AssetError, match="counties.json"):
        assets.ensure(log=lambda m: None)


def test_real_data_and_fonts_load():
    assets.ensure(log=lambda m: None)  # eski kökteki dosyaları data/ altına taşır
    assert assets.missing() == []
    assert set(assets.fonts()) == {"bebas", "regular", "semibold", "bold"}
```

- [ ] **Step 3: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_assets.py -v`
Expected: FAIL. `ImportError: cannot import name 'assets'`.

- [ ] **Step 4: `engine/assets.py` dosyasını yaz**

```python
"""Veri ve font dosyaları: yollar, indirme, eski yerleşimden taşıma, FontProperties."""
import os
import shutil
import urllib.request
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FONT_DIR = os.path.join(DATA, "fonts")
COUNTIES = os.path.join(DATA, "counties.json")

COUNTIES_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
FONT_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {
    "bebas": "bebasneue/BebasNeue-Regular.ttf",
    "regular": "barlow/Barlow-Regular.ttf",
    "semibold": "barlow/Barlow-SemiBold.ttf",
    "bold": "barlow/Barlow-Bold.ttf",
}


class AssetError(RuntimeError):
    pass


def font_path(key):
    return os.path.join(FONT_DIR, os.path.basename(FONTS[key]))


def _ok(path):
    return os.path.exists(path) and os.path.getsize(path) > 1000


def missing():
    """Eksik veri/font dosyalarının yolları."""
    return [p for p in [COUNTIES] + [font_path(k) for k in FONTS] if not _ok(p)]


def ensure(log=print):
    """Eksik dosyaları indirir. Eski yerleşimdeki (klasör kökü) dosyaları önce data/ altına taşır."""
    os.makedirs(FONT_DIR, exist_ok=True)
    old = {os.path.join(ROOT, "counties.json"): COUNTIES}
    for key in FONTS:
        old[os.path.join(ROOT, "fonts", os.path.basename(FONTS[key]))] = font_path(key)
    for src, dst in old.items():
        if _ok(src) and not _ok(dst):
            shutil.move(src, dst)
    jobs = [(COUNTIES_URL, COUNTIES)] + [(FONT_BASE + FONTS[k], font_path(k)) for k in FONTS]
    for url, dest in jobs:
        if _ok(dest):
            continue
        log(f"indiriliyor: {url}")
        try:
            urllib.request.urlretrieve(url, dest + ".part")
            os.replace(dest + ".part", dest)
        except Exception as e:
            raise AssetError(
                f"{os.path.basename(dest)} indirilemedi ({e}). README'deki 'Elle indirme' adımlarına bakın."
            ) from e


@lru_cache(maxsize=None)
def fonts():
    """Anahtar -> FontProperties. Font dosyası eksikse AssetError."""
    from matplotlib import font_manager as fm

    out = {}
    for key in FONTS:
        path = font_path(key)
        if not _ok(path):
            raise AssetError(f"Font eksik: {path}")
        fm.fontManager.addfont(path)
        out[key] = fm.FontProperties(fname=path)
    return out
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_assets.py -v`
Expected: 4 passed. `data/counties.json` ve `data/fonts/*.ttf` oluşmuş olmalı, kökteki `counties.json` ile `fonts/` taşınmış olmalı.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini .gitignore engine scenes tests
git commit -m "İskelet ve veri/font yönetimi (engine/assets.py)"
```

---

### Task 3: `engine/geo.py` — eyaletler, sınırlar, county'ler

**Files:**
- Create: `engine/geo.py`
- Test: `tests/test_geo.py`

**Interfaces:**
- Consumes: `assets.COUNTIES`.
- Produces:
  - `geo.STATES: list[(fips, abbr, name)]` (48 kayıt), `geo.BY_ABBR: dict[abbr -> (fips, abbr, name)]`.
  - `geo.state(abbr) -> (fips, abbr, name)`. Bilinmeyen eyalette `ValueError`.
  - `geo.albers(lon, lat) -> (x, y)`, `geo.rings(geometry) -> list[np.ndarray]`, `geo.proj(ring) -> np.ndarray (n,2)`.
  - `geo._outlines() -> (full, simplified)`: `{state_fips: [np.ndarray lon/lat ring]}`, sıra counties.json'daki gibi.
  - `geo.us_outlines(selected_fips) -> list[(fips, [projected ring])]`: seçili eyalet tam, diğerleri sade.
  - `geo.state_rings(fips) -> list[projected ring]` (tam).
  - `geo.County(fips, name, lsad, display, rings)`, `geo.counties(state_fips) -> list[County]` (dosya sırası).
  - `geo.county_svg(state_fips, width=1000) -> {"width", "height", "counties": [{"fips", "name", "d"}]}`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_geo.py`

```python
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
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_geo.py -v`
Expected: FAIL. `ImportError: cannot import name 'geo'`.

- [ ] **Step 3: `engine/geo.py` dosyasını yaz**

```python
"""ABD eyalet ve county geometrisi, Albers projeksiyonu."""
import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from engine import assets

# (fips, kısaltma, ad): 48 bitişik eyalet
STATES = [
    ("01", "AL", "Alabama"), ("04", "AZ", "Arizona"), ("05", "AR", "Arkansas"), ("06", "CA", "California"),
    ("08", "CO", "Colorado"), ("09", "CT", "Connecticut"), ("10", "DE", "Delaware"), ("12", "FL", "Florida"),
    ("13", "GA", "Georgia"), ("16", "ID", "Idaho"), ("17", "IL", "Illinois"), ("18", "IN", "Indiana"),
    ("19", "IA", "Iowa"), ("20", "KS", "Kansas"), ("21", "KY", "Kentucky"), ("22", "LA", "Louisiana"),
    ("23", "ME", "Maine"), ("24", "MD", "Maryland"), ("25", "MA", "Massachusetts"), ("26", "MI", "Michigan"),
    ("27", "MN", "Minnesota"), ("28", "MS", "Mississippi"), ("29", "MO", "Missouri"), ("30", "MT", "Montana"),
    ("31", "NE", "Nebraska"), ("32", "NV", "Nevada"), ("33", "NH", "New Hampshire"), ("34", "NJ", "New Jersey"),
    ("35", "NM", "New Mexico"), ("36", "NY", "New York"), ("37", "NC", "North Carolina"), ("38", "ND", "North Dakota"),
    ("39", "OH", "Ohio"), ("40", "OK", "Oklahoma"), ("41", "OR", "Oregon"), ("42", "PA", "Pennsylvania"),
    ("44", "RI", "Rhode Island"), ("45", "SC", "South Carolina"), ("46", "SD", "South Dakota"), ("47", "TN", "Tennessee"),
    ("48", "TX", "Texas"), ("49", "UT", "Utah"), ("50", "VT", "Vermont"), ("51", "VA", "Virginia"),
    ("53", "WA", "Washington"), ("54", "WV", "West Virginia"), ("55", "WI", "Wisconsin"), ("56", "WY", "Wyoming"),
]
BY_ABBR = {abbr: (fips, abbr, name) for fips, abbr, name in STATES}
EXCLUDED = ("02", "15", "72")  # Alaska, Hawaii, Porto Riko


def state(abbr):
    try:
        return BY_ABBR[abbr]
    except KeyError:
        raise ValueError(f"Desteklenmeyen eyalet: {abbr!r}") from None


def albers(lon, lat, lon0=-96, lat0=23, p1=29.5, p2=45.5):
    lon, lat = np.radians(lon), np.radians(lat)
    l0, f0, f1, f2 = map(np.radians, (lon0, lat0, p1, p2))
    n = (np.sin(f1) + np.sin(f2)) / 2
    C = np.cos(f1) ** 2 + 2 * n * np.sin(f1)
    r0 = np.sqrt(C - 2 * n * np.sin(f0)) / n
    th = n * (lon - l0)
    r = np.sqrt(C - 2 * n * np.sin(lat)) / n
    return r * np.sin(th), r0 - r * np.cos(th)


def rings(geom):
    """Poligonların yalnızca dış halkaları (orijinal scene_a ile aynı)."""
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon":
        return [np.array(c[0], float)]
    if t == "MultiPolygon":
        return [np.array(p[0], float) for p in c]
    return []


def proj(ring):
    x, y = albers(ring[:, 0], ring[:, 1])
    return np.column_stack([x, y])


@lru_cache(maxsize=None)
def _features():
    with open(assets.COUNTIES, encoding="utf-8") as f:
        return json.load(f)["features"]


@lru_cache(maxsize=None)
def _outlines():
    """(tam, sade) eyalet sınırları: {fips: [lon/lat halka]}. Orijinal prep_data.py ile aynı yöntem ve sıra."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    groups = {}
    for feat in _features():
        st = feat["properties"]["STATE"]
        if st in EXCLUDED:
            continue
        groups.setdefault(st, []).append(shape(feat["geometry"]).buffer(0))
    full, simp = {}, {}
    for st, geoms in groups.items():
        u = unary_union(geoms)
        for out, g in ((full, u), (simp, u.simplify(0.01, preserve_topology=True))):
            polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
            out[st] = [np.array(p.exterior.coords, float) for p in polys if p.area > 1e-5]
    return full, simp


def us_outlines(selected_fips):
    """Arka plan için tüm eyaletler: seçili eyalet tam çözünürlükte, diğerleri sade."""
    full, simp = _outlines()
    return [(st, [proj(r) for r in (full[st] if st == selected_fips else simp[st])]) for st in simp]


def state_rings(fips):
    return [proj(r) for r in _outlines()[0][fips]]


@dataclass(frozen=True, eq=False)
class County:
    fips: str
    name: str
    lsad: str
    display: str
    rings: tuple


@lru_cache(maxsize=None)
def counties(state_fips):
    feats = [f for f in _features() if f["properties"]["STATE"] == state_fips]
    counts = Counter(f["properties"]["NAME"] for f in feats)
    out = []
    for f in feats:
        p = f["properties"]
        display = f"{p['NAME']} {p['LSAD']}".strip() if counts[p["NAME"]] > 1 else p["NAME"]
        out.append(County(f["id"], p["NAME"], p["LSAD"], display, tuple(proj(r) for r in rings(f["geometry"]))))
    return out


@lru_cache(maxsize=None)
def county_svg(state_fips, width=1000):
    """Arayüz haritası: projekte edilmiş, seyreltilmiş SVG path'leri (y ekseni ters)."""
    cs = counties(state_fips)
    pts = np.vstack([r for c in cs for r in c.rings])
    (xmin, ymin), (xmax, ymax) = pts.min(0), pts.max(0)
    s = width / (xmax - xmin)
    items = []
    for c in cs:
        parts = []
        for r in c.rings:
            q = r[:: max(1, len(r) // 200)]
            xy = np.column_stack([(q[:, 0] - xmin) * s, (ymax - q[:, 1]) * s])
            parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in xy) + "Z")
        items.append({"fips": c.fips, "name": c.display, "d": "".join(parts)})
    return {"width": width, "height": round(float((ymax - ymin) * s), 1), "counties": items}
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_geo.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/geo.py tests/test_geo.py
git commit -m "Coğrafya modülü: eyaletler, sınırlar, county'ler"
```

---

### Task 4: `engine/importer.py` — CSV/Excel ile county ataması

**Files:**
- Create: `engine/importer.py`
- Test: `tests/test_importer.py`

**Interfaces:**
- Consumes: `geo.County` listesi (`geo.counties`).
- Produces:
  - `importer.norm(text) -> str`.
  - `importer.CountyMatcher(counties).match(text) -> (County | None, [aday County])`.
  - `importer.read_rows(filename, data: bytes) -> list[list[str]]`.
  - `importer.parse_assignments(filename, data, counties, categories) -> {"assign": {fips: key}, "unmatched": [{"row","county","category","reason"}], "ambiguous": [{"row","county","candidates"}]}`. Boş dosyada `ValueError`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_importer.py`

```python
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
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v`
Expected: FAIL. `ImportError: cannot import name 'importer'`.

- [ ] **Step 3: `engine/importer.py` dosyasını yaz**

```python
"""County -> kategori atamalarını CSV/Excel dosyasından okur ve county'lerle eşler."""
import csv
import io
import re

COUNTY_HEADERS = {"county", "name", "fips", "ilce", "ilçe", "county_name", "countyname"}
CATEGORY_HEADERS = {"category", "kategori", "signal", "sinyal"}


def norm(text):
    s = str(text).lower().strip()
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bsainte\b", "ste", s)
    s = re.sub(r"\b(county|parish|city|borough)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _squash(text):
    return " ".join(str(text).lower().split())


class CountyMatcher:
    def __init__(self, counties):
        self.by_fips = {c.fips: c for c in counties}
        self.by_code = {c.fips[2:]: c for c in counties}
        self.by_full = {_squash(f"{c.name} {c.lsad}"): c for c in counties}
        self.by_norm = {}
        for c in counties:
            self.by_norm.setdefault(norm(c.name), []).append(c)

    def match(self, text):
        """(County, []) tek eşleşme; (None, adaylar) belirsiz; (None, []) bulunamadı."""
        t = str(text).strip()
        if re.fullmatch(r"\d{1,5}(\.0+)?", t):
            d = t.split(".")[0]
            c = self.by_fips.get(d.zfill(5)) if len(d) > 3 else self.by_code.get(d.zfill(3))
            return (c, []) if c else (None, [])
        c = self.by_full.get(_squash(t))
        if c:
            return c, []
        cands = self.by_norm.get(norm(t), [])
        if len(cands) == 1:
            return cands[0], []
        return None, list(cands)


def read_rows(filename, data):
    if filename.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = [["" if v is None else str(v) for v in r] for r in wb.worksheets[0].iter_rows(values_only=True)]
    else:
        text = data.decode("utf-8-sig", errors="replace")
        lines = text.splitlines()
        first = lines[0] if lines else ""
        delim = max([",", ";", "\t"], key=first.count)
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return [r for r in rows if any(str(x).strip() for x in r)]


def parse_assignments(filename, data, counties, categories):
    rows = read_rows(filename, data)
    if not rows:
        raise ValueError("Dosya boş.")
    head = [h.strip().lower() for h in rows[0]]
    ci = next((i for i, h in enumerate(head) if h in COUNTY_HEADERS), None)
    ki = next((i for i, h in enumerate(head) if h in CATEGORY_HEADERS), None)
    if ci is None or ki is None:
        ci, ki = 0, 1
    lookup = {}
    for c in categories:
        lookup[c["key"].lower()] = c["key"]
        lookup[c["label"].strip().lower()] = c["key"]
    matcher = CountyMatcher(counties)
    assign, unmatched, ambiguous = {}, [], []
    for n, r in enumerate(rows[1:], start=2):
        cname = r[ci].strip() if ci < len(r) else ""
        cat = r[ki].strip() if ki < len(r) else ""
        key = lookup.get(cat.lower())
        if key is None:
            unmatched.append({"row": n, "county": cname, "category": cat, "reason": "kategori bulunamadı"})
            continue
        c, cands = matcher.match(cname)
        if c:
            assign[c.fips] = key
        elif cands:
            ambiguous.append({"row": n, "county": cname, "candidates": [x.display for x in cands]})
        else:
            unmatched.append({"row": n, "county": cname, "category": cat, "reason": "county bulunamadı"})
    return {"assign": assign, "unmatched": unmatched, "ambiguous": ambiguous}
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v`
Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/importer.py tests/test_importer.py
git commit -m "CSV/Excel county ataması içe aktarma"
```

---

### Task 5: `engine/params.py` — ayar tipleri

**Files:**
- Create: `engine/params.py`
- Test: `tests/test_params.py`

**Interfaces:**
- Consumes: `geo.BY_ABBR`, `geo.STATES`, `geo.counties`.
- Produces:
  - `ParamError(name, message)` (ValueError alt sınıfı; `.name` ve `.message` alanları var).
  - `Param(name, label, default=None, group="Genel", help="")`, `.schema() -> dict`, `.validate(value, values) -> value`.
  - Alt sınıflar ve `kind` değerleri:
    - `Text(multiline, auto, max_len)` → "text"
    - `Color` → "color"
    - `Number(lo, hi, step, integer, optional)` → "number"
    - `Date` → "date"
    - `StateSelect` → "state"
    - `CountySelect(state_param, allow_none)` → "county"
    - `Categories(min_count=2, max_count=7)` → "categories"
    - `CountyAssign(state_param, categories_param)` → "county_assign"
    - `PriceTable(min_rows=2)` → "price_table"
  - `validate_all(params, values) -> (clean: dict, errors: {name: message})`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_params.py`

```python
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
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_params.py -v`
Expected: FAIL. `ImportError: cannot import name 'params'`.

- [ ] **Step 3: `engine/params.py` dosyasını yaz**

```python
"""Sahne ayar tipleri: arayüz şeması (schema) ve sunucu tarafı doğrulama (validate)."""
import copy
import datetime as dt
import math
import re
from dataclasses import dataclass

from engine import geo

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
KEY_RE = re.compile(r"^[a-z0-9_]{1,20}$")


class ParamError(ValueError):
    def __init__(self, name, message):
        super().__init__(f"{name}: {message}")
        self.name = name
        self.message = message


@dataclass
class Param:
    name: str
    label: str
    default: object = None
    group: str = "Genel"
    help: str = ""
    kind = "param"

    def schema(self):
        d = {"name": self.name, "label": self.label, "kind": self.kind, "default": self.default,
             "group": self.group, "help": self.help}
        d.update(self.extra())
        return d

    def extra(self):
        return {}

    def validate(self, value, values):
        return value

    def fail(self, message):
        raise ParamError(self.name, message)


@dataclass
class Text(Param):
    multiline: bool = False
    auto: bool = False
    max_len: int = 200
    kind = "text"

    def extra(self):
        return {"multiline": self.multiline, "auto": self.auto, "max_len": self.max_len}

    def validate(self, value, values):
        if value is None:
            value = ""
        if not isinstance(value, str):
            self.fail("metin olmalı")
        if len(value) > self.max_len:
            self.fail(f"en fazla {self.max_len} karakter olabilir")
        return value


@dataclass
class Color(Param):
    kind = "color"

    def validate(self, value, values):
        if not isinstance(value, str) or not HEX_RE.match(value):
            self.fail("#rrggbb biçiminde bir renk olmalı")
        return value.lower()


@dataclass
class Number(Param):
    lo: float = None
    hi: float = None
    step: float = None
    integer: bool = False
    optional: bool = False
    kind = "number"

    def extra(self):
        return {"min": self.lo, "max": self.hi, "step": self.step, "integer": self.integer, "optional": self.optional}

    def validate(self, value, values):
        if value is None or value == "":
            if self.optional:
                return None
            self.fail("boş bırakılamaz")
        if isinstance(value, bool):
            self.fail("sayı olmalı")
        try:
            v = float(value)
        except (TypeError, ValueError):
            self.fail("sayı olmalı")
        if not math.isfinite(v):
            self.fail("sayı olmalı")
        if self.integer:
            if v != int(v):
                self.fail("tam sayı olmalı")
            v = int(v)
        too_low = self.lo is not None and v < self.lo
        too_high = self.hi is not None and v > self.hi
        if too_low or too_high:
            if self.lo is not None and self.hi is not None:
                self.fail(f"{self.lo:g} ile {self.hi:g} arasında olmalı")
            self.fail(f"en az {self.lo:g} olmalı" if too_low else f"en fazla {self.hi:g} olmalı")
        return v


@dataclass
class Date(Param):
    kind = "date"

    def validate(self, value, values):
        try:
            return dt.date.fromisoformat(str(value)).isoformat()
        except ValueError:
            self.fail("tarih YYYY-AA-GG biçiminde olmalı")


@dataclass
class StateSelect(Param):
    kind = "state"

    def extra(self):
        return {"options": [{"value": abbr, "label": name} for _, abbr, name in geo.STATES]}

    def validate(self, value, values):
        if value not in geo.BY_ABBR:
            self.fail("geçersiz eyalet")
        return value


def _state_counties(values, state_param):
    return geo.counties(geo.BY_ABBR[values[state_param]][0])


@dataclass
class CountySelect(Param):
    state_param: str = "state"
    allow_none: bool = True
    kind = "county"

    def extra(self):
        return {"state_param": self.state_param, "allow_none": self.allow_none}

    def validate(self, value, values):
        if value in (None, ""):
            if self.allow_none:
                return None
            self.fail("bir county seçin")
        if not any(c.fips == value for c in _state_counties(values, self.state_param)):
            self.fail("seçili eyalette böyle bir county yok")
        return value


@dataclass
class Categories(Param):
    min_count: int = 2
    max_count: int = 7
    kind = "categories"

    def extra(self):
        return {"min_count": self.min_count, "max_count": self.max_count}

    def validate(self, value, values):
        if not isinstance(value, list):
            self.fail("kategori listesi olmalı")
        if not self.min_count <= len(value) <= self.max_count:
            self.fail(f"{self.min_count} ile {self.max_count} arasında kategori olmalı")
        out, seen = [], set()
        for i, c in enumerate(value, 1):
            if not isinstance(c, dict):
                self.fail(f"{i}. kategori geçersiz")
            key, label, color = str(c.get("key", "")), str(c.get("label", "")).strip(), str(c.get("color", ""))
            if not KEY_RE.match(key) or key in seen:
                self.fail(f"{i}. kategorinin anahtarı geçersiz")
            if not label or len(label) > 40:
                self.fail(f"{i}. kategorinin etiketi 1–40 karakter olmalı")
            if not HEX_RE.match(color):
                self.fail(f"{i}. kategorinin rengi geçersiz")
            seen.add(key)
            out.append({"key": key, "label": label, "color": color.lower()})
        if out[-1]["key"] != "none":
            self.fail("son kategori 'none' (veri yok) olmalı")
        return out


@dataclass
class CountyAssign(Param):
    state_param: str = "state"
    categories_param: str = "categories"
    kind = "county_assign"

    def extra(self):
        return {"state_param": self.state_param, "categories_param": self.categories_param}

    def validate(self, value, values):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            self.fail("geçersiz atama listesi")
        fips_ok = {c.fips for c in _state_counties(values, self.state_param)}
        keys = {c["key"] for c in values[self.categories_param]}
        out = {}
        for fips, key in value.items():
            if fips not in fips_ok:
                self.fail(f"seçili eyalette olmayan county: {fips}")
            if key not in keys:
                self.fail(f"bilinmeyen kategori: {key}")
            if key != "none":
                out[fips] = key
        return dict(sorted(out.items()))


@dataclass
class PriceTable(Param):
    min_rows: int = 2
    kind = "price_table"

    def extra(self):
        return {"min_rows": self.min_rows}

    def validate(self, value, values):
        if not isinstance(value, list) or len(value) < self.min_rows:
            self.fail(f"en az {self.min_rows} satır olmalı")
        out = []
        for i, r in enumerate(value, 1):
            if not isinstance(r, dict):
                self.fail(f"{i}. satır geçersiz")
            try:
                d = dt.date.fromisoformat(str(r.get("date")))
            except ValueError:
                self.fail(f"{i}. satırın tarihi geçersiz")
            try:
                price = int(float(r.get("price")))
            except (TypeError, ValueError):
                price = 0
            if price <= 0:
                self.fail(f"{i}. satırın fiyatı pozitif bir sayı olmalı")
            if out:
                if d <= dt.date.fromisoformat(out[-1]["date"]):
                    self.fail(f"{i}. satırın tarihi bir öncekinden sonra olmalı")
                if price == out[-1]["price"]:
                    self.fail(f"{i}. satırın fiyatı bir öncekiyle aynı olamaz")
            out.append({"date": d.isoformat(), "price": price})
        return out


def validate_all(params, values):
    """Ayarları sırayla doğrular (eyalet, ona bağlı county'lerden önce gelmeli).
    Eksik değer varsayılanla, hatalı değer varsayılanla doldurulur ve hataya yazılır."""
    clean, errors = {}, {}
    for p in params:
        value = copy.deepcopy(values[p.name] if p.name in values else p.default)
        try:
            clean[p.name] = p.validate(value, clean)
        except ParamError as e:
            errors[p.name] = e.message
            clean[p.name] = copy.deepcopy(p.default)
    return clean, errors
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_params.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/params.py tests/test_params.py
git commit -m "Ayar tipleri ve doğrulama"
```

---

### Task 6: `engine/framing.py` — kamera çerçeveleme

**Files:**
- Create: `engine/framing.py`
- Test: `tests/test_framing.py`

**Interfaces:**
- Consumes: `geo.state_rings`, `geo.counties` (yalnızca testlerde).
- Produces:
  - Sabitler: `REGION = (0.40, 0.96, 0.08, 0.94)`, `FOCUS_SCREEN`, `FOCUS_MIN = 0.05`, `FOCUS_MAX = 0.30`.
  - `box(pts, pad) -> np.array([cx, cy, w])`.
  - `state_frame(pts, zoom=1.0, shift_x=0.0, shift_y=0.0, region=REGION)`.
  - `focus_frame(county_pts, state_w, focus_zoom=0.55)`.
  - Kamera görünür yüksekliği her zaman `w * 9 / 16`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_framing.py`

```python
import numpy as np
import pytest

from engine import framing, geo

ORIG_CAM_FL = [0.14131970888099443, 0.08739125759532332, 0.2736116695463418]
FL_TUNE = (0.822673668267268, -0.009999999999999926, 0.05222222222222225)


def test_florida_sample_reproduces_original_camera():
    pts = np.vstack(geo.state_rings("12"))
    cam = framing.state_frame(pts, *FL_TUNE)
    assert np.allclose(cam, ORIG_CAM_FL, rtol=0, atol=1e-12)


@pytest.mark.parametrize("fips", [f for f, _, _ in geo.STATES])
def test_state_fits_region(fips):
    pts = np.vstack(geo.state_rings(fips))
    cx, cy, w = framing.state_frame(pts)
    h = w * 9 / 16
    (xmin, ymin), (xmax, ymax) = pts.min(0), pts.max(0)
    x0, x1, y0, y1 = framing.REGION
    eps = 1e-9
    assert (xmin - (cx - w / 2)) / w >= x0 - eps and (xmax - (cx - w / 2)) / w <= x1 + eps
    assert (ymin - (cy - h / 2)) / h >= y0 - eps and (ymax - (cy - h / 2)) / h <= y1 + eps


def test_focus_matches_original_charlotte():
    ch = next(c for c in geo.counties("12") if c.fips == "12015")
    pts = np.vstack(ch.rings)
    c = pts.mean(0)
    expected = [c[0] - 0.06 * ORIG_CAM_FL[2] * 0.55, c[1] + 0.02 * ORIG_CAM_FL[2], ORIG_CAM_FL[2] * 0.55]
    assert np.allclose(framing.focus_frame(pts, ORIG_CAM_FL[2], 0.55), expected, rtol=0, atol=1e-12)


def test_focus_clamps_county_share():
    square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    size = 16 / 9
    far = framing.focus_frame(square, 1000.0)
    assert abs(size / far[2] - framing.FOCUS_MIN) < 1e-12
    near = framing.focus_frame(square, 1.0)
    assert abs(size / near[2] - framing.FOCUS_MAX) < 1e-12


def test_box_matches_original_formula():
    pts = np.array([[0.0, 0.0], [2.0, 1.0]])
    assert np.allclose(framing.box(pts, 0.06), [1.0, 0.5, 2.0 * 1.06])
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_framing.py -v`
Expected: FAIL. `ImportError: cannot import name 'framing'`.

- [ ] **Step 3: `engine/framing.py` dosyasını yaz**

```python
"""Kamera çerçeveleme. Kamera = np.array([cx, cy, w]) (projeksiyon birimi); görünür yükseklik w*9/16."""
import numpy as np

ASPECT = 16 / 9
REGION = (0.40, 0.96, 0.08, 0.94)  # eyaletin sığacağı ekran bölgesi (x0, x1, y0, y1), y aşağıdan yukarı
# Vurgu county'sinin ekrandaki yeri: orijinal Charlotte kadrajından (0.5+0.06, 0.5-(0.02/0.55)/(9/16))
FOCUS_SCREEN = (0.56, 0.5 - (0.02 / 0.55) / (9 / 16))
FOCUS_MIN, FOCUS_MAX = 0.05, 0.30  # vurgu county'sinin ekran genişliğindeki payı


def _bbox(pts):
    return pts.min(0), pts.max(0)


def box(pts, pad):
    """Orijinal box(): noktaları pad paylı 16:9 kadraja ortalar (ABD görünümü)."""
    (xmin, ymin), (xmax, ymax) = _bbox(pts)
    w = max(xmax - xmin, (ymax - ymin) * ASPECT) * (1 + pad)
    return np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, w])


def state_frame(pts, zoom=1.0, shift_x=0.0, shift_y=0.0, region=REGION):
    """Eyaleti ekran bölgesine sığdırır. zoom>1 yaklaşır; shift_x/shift_y eyaleti ekran oranı kadar sağa/yukarı kaydırır."""
    (xmin, ymin), (xmax, ymax) = _bbox(pts)
    x0, x1, y0, y1 = region
    w = max((xmax - xmin) / (x1 - x0), (ymax - ymin) / ((y1 - y0) * 9 / 16)) / zoom
    sx, sy = (xmin + xmax) / 2, (ymin + ymax) / 2
    rx, ry = (x0 + x1) / 2, (y0 + y1) / 2
    return np.array([sx - (rx - 0.5 + shift_x) * w, sy - (ry - 0.5 + shift_y) * w * 9 / 16, w])


def focus_frame(county_pts, state_w, focus_zoom=0.55):
    """Vurgu kamerası: county FOCUS_SCREEN noktasına oturur ve ekran genişliğinin %5–30'unu kaplar."""
    (xmin, ymin), (xmax, ymax) = _bbox(county_pts)
    size = max(xmax - xmin, (ymax - ymin) * ASPECT)
    w = float(np.clip(state_w * focus_zoom, size / FOCUS_MAX, size / FOCUS_MIN))
    c = county_pts.mean(0)
    fx, fy = FOCUS_SCREEN
    return np.array([c[0] - (fx - 0.5) * w, c[1] - (fy - 0.5) * w * 9 / 16, w])
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_framing.py -v`
Expected: 52 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/framing.py tests/test_framing.py
git commit -m "Kamera çerçeveleme"
```

---

### Task 7: `engine/scene.py` ve `engine/render.py` — sahne sözleşmesi ve render motoru

**Files:**
- Create: `engine/scene.py`, `engine/render.py`, `tests/conftest.py`, `tests/helpers.py`
- Test: `tests/test_scene.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `params.Number`, `params.validate_all`, `assets.fonts`.
- Produces:
  - `scene.FPS = 30`, `scene.W_IN = 19.2`, `scene.H_IN = 10.8`.
  - `scene.SceneContext(fig, p, transparent, fonts, dpi)`.
  - `scene.Scene(id, title, base_duration, params, setup, bg_center=(0.5, 0.5), check=None)` ve metotları: `.all_params()`, `.validate(values) -> (clean, errors)`, `.defaults() -> dict`, `.schema() -> dict`.
  - `scene.ease(t)`, `scene.seg(t, a, b)`, `scene.fit_text(fig, text, max_frac)`.
  - `render.ffmpeg_exe()`, `render.background(w, h, center) -> (h,w,4) float`.
  - `render.Frames(scene, params, transparent=False, dpi=100)`:
    - `.draw(t)` gerçek saniye alır ve kopyalanmış `(h,w,4) uint8` döndürür.
    - Ayrıca `.n_frames`, `.w`, `.h`, `.close()`.
  - `render.to_png(rgba) -> bytes`, `render.still_png(scene, params, t, transparent=False, dpi=50) -> bytes`.
  - `render.encoder_args(transparent) -> list[str]`, `render.video_ext(transparent) -> ".mov" | ".mp4"`.
  - `render.render_video(scene, params, out_path, transparent=False, on_progress=None) -> out_path`.
  - `tests/helpers.decode_frame(path, t, w, h) -> (h,w,4) uint8`.
  - `conftest` içinde `dummy_scene` fixture'ı: base 1 sn, `color` ayarı, `.calls` listesi.

- [ ] **Step 1: Test yardımcılarını yaz**

`tests/helpers.py`:
```python
import subprocess

import imageio_ffmpeg
import numpy as np


def decode_frame(path, t, w, h):
    """Videodan t saniyesindeki kareyi RGBA olarak çözer."""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = subprocess.run([exe, "-loglevel", "error", "-ss", str(t), "-i", path, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 4)
```

`tests/conftest.py`:
```python
import matplotlib.patches as mpatches
import pytest

from engine.params import Color
from engine.scene import Scene


@pytest.fixture
def dummy_scene():
    """1 saniyelik deneme sahnesi: ortada opak bir kare; update çağrılarını kaydeder."""
    calls = []

    def setup(ctx):
        ax = ctx.fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(mpatches.Rectangle((0.4, 0.4), 0.2, 0.2, color=ctx.p["color"]))

        def update(t):
            calls.append(t)

        return update

    scene = Scene(id="dummy", title="Deneme", base_duration=1.0,
                  params=[Color("color", "Renk", default="#ff0000")], setup=setup)
    scene.calls = calls
    return scene
```

- [ ] **Step 2: Başarısız testleri yaz**

`tests/test_scene.py`:
```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from engine.scene import ease, fit_text, seg


def test_duration_param(dummy_scene):
    d = dummy_scene.all_params()[-1]
    assert (d.name, d.lo, d.hi, d.default, d.group) == ("duration", 0.5, 2.0, 1.0, "Zaman")


def test_defaults_and_schema(dummy_scene):
    assert dummy_scene.defaults() == {"color": "#ff0000", "duration": 1.0}
    s = dummy_scene.schema()
    assert s["id"] == "dummy" and [p["name"] for p in s["params"]] == ["color", "duration"]


def test_check_hook(dummy_scene):
    dummy_scene.check = lambda p: {"color": "olmaz"} if p["color"] == "#000000" else {}
    assert dummy_scene.validate({"color": "#000000"})[1] == {"color": "olmaz"}
    assert dummy_scene.validate({"color": "#00ff00"})[1] == {}


def test_ease_and_seg():
    assert seg(5, 4, 6) == 0.5 and seg(1, 4, 6) == 0 and seg(9, 4, 6) == 1
    assert ease(0) == 0 and ease(1) == 1 and ease(0.5) == 0.5


def test_fit_text():
    fig = plt.figure(figsize=(19.2, 10.8), dpi=50)
    long = fig.text(0, 0.5, "NORTH CAROLINA NORTH CAROLINA", fontsize=150)
    fit_text(fig, long, 0.34)
    w = long.get_window_extent(renderer=fig.canvas.get_renderer()).width
    assert w <= 0.34 * fig.bbox.width + 1
    short = fig.text(0, 0.2, "FL", fontsize=150)
    fit_text(fig, short, 0.34)
    assert short.get_fontsize() == 150
    plt.close(fig)
```

`tests/test_render.py`:
```python
import io

import imageio_ffmpeg
import numpy as np
from PIL import Image

from engine import render
from tests.helpers import decode_frame


def test_background_is_brighter_at_center():
    bg = render.background(192, 108, (0.6, 0.45))
    assert bg.shape == (108, 192, 4) and np.all(bg[..., 3] == 1)
    assert bg[int(108 * 0.45), int(192 * 0.6), 0] > bg[0, 0, 0]


def test_frame_sizes(dummy_scene):
    p = dummy_scene.defaults()
    for dpi, shape in ((100, (1080, 1920, 4)), (50, (540, 960, 4))):
        fr = render.Frames(dummy_scene, p, dpi=dpi)
        try:
            assert fr.draw(0.5).shape == shape
        finally:
            fr.close()


def test_time_is_scaled_to_base_duration(dummy_scene):
    p = dummy_scene.defaults()
    p["duration"] = 2.0
    fr = render.Frames(dummy_scene, p, dpi=20)
    try:
        fr.draw(1.0)
        assert dummy_scene.calls[-1] == 0.5 and fr.n_frames == 60
    finally:
        fr.close()


def test_transparent_and_opaque_corners(dummy_scene):
    p = dummy_scene.defaults()
    for transparent, corner in ((True, 0), (False, 255)):
        fr = render.Frames(dummy_scene, p, transparent=transparent, dpi=20)
        try:
            a = fr.draw(0.5)
            assert a[0, 0, 3] == corner and a[a.shape[0] // 2, a.shape[1] // 2, 3] == 255
        finally:
            fr.close()


def test_draw_returns_independent_copies(dummy_scene):
    fr = render.Frames(dummy_scene, dummy_scene.defaults(), dpi=20)
    try:
        a = fr.draw(0.1)
        a[:] = 0
        assert fr.draw(0.1).max() > 0
    finally:
        fr.close()


def test_still_png(dummy_scene):
    png = render.still_png(dummy_scene, dummy_scene.defaults(), 0.5)
    assert Image.open(io.BytesIO(png)).size == (960, 540)


def test_render_video_mp4(dummy_scene, tmp_path):
    out = render.render_video(dummy_scene, dummy_scene.defaults(), str(tmp_path / "a.mp4"))
    assert imageio_ffmpeg.count_frames_and_secs(out) == (30, 1.0)


def test_render_video_transparent_mov(dummy_scene, tmp_path):
    progress = []
    out = render.render_video(dummy_scene, dummy_scene.defaults(), str(tmp_path / "a.mov"), transparent=True,
                              on_progress=lambda f, n: progress.append((f, n)))
    assert progress[0] == (1, 30) and progress[-1] == (30, 30)
    f = decode_frame(out, 0.5, 1920, 1080)
    assert f[0, 0, 3] == 0 and f[540, 960, 3] == 255
```

- [ ] **Step 3: Testlerin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_scene.py tests/test_render.py -v`
Expected: FAIL. `ModuleNotFoundError: No module named 'engine.scene'`.

- [ ] **Step 4: `engine/scene.py` dosyasını yaz**

```python
"""Sahne sözleşmesi ve sahnelerin ortak yardımcıları."""
from dataclasses import dataclass
from typing import Callable

import numpy as np

from engine.params import Number, validate_all

FPS = 30
W_IN, H_IN = 19.2, 10.8  # 100 dpi'da 1920x1080


@dataclass
class SceneContext:
    fig: object
    p: dict
    transparent: bool
    fonts: dict
    dpi: int


@dataclass
class Scene:
    id: str
    title: str
    base_duration: float
    params: list
    setup: Callable  # setup(ctx) -> update(t); t temel süre cinsinden
    bg_center: tuple = (0.5, 0.5)  # koyu arka plan ışığının merkezi (x, y üstten), ekran oranı
    check: Callable = None  # check(clean) -> {ad: hata}; ayarlar arası kurallar

    def all_params(self):
        dur = Number("duration", "Süre (sn)", default=self.base_duration, group="Zaman",
                     lo=round(self.base_duration * 0.5, 2), hi=round(self.base_duration * 2, 2), step=0.1)
        return self.params + [dur]

    def validate(self, values):
        clean, errors = validate_all(self.all_params(), values or {})
        if not errors and self.check:
            errors.update(self.check(clean))
        return clean, errors

    def defaults(self):
        return self.validate({})[0]

    def schema(self):
        return {"id": self.id, "title": self.title, "base_duration": self.base_duration,
                "params": [p.schema() for p in self.all_params()]}


def ease(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    return np.clip((t - a) / (b - a), 0, 1)


def fit_text(fig, text, max_frac):
    """Metin figür genişliğinin max_frac oranını aşıyorsa font boyutunu küçültür (sığıyorsa dokunmaz)."""
    renderer = fig.canvas.get_renderer()
    limit = max_frac * fig.bbox.width
    for _ in range(3):
        w = text.get_window_extent(renderer=renderer).width
        if w <= limit:
            return
        text.set_fontsize(text.get_fontsize() * limit / w * 0.99)
```

- [ ] **Step 5: `engine/render.py` dosyasını yaz**

```python
"""Kare üretimi: kurulmuş sahne figürü, ffmpeg ile video yazma, tek kare önizleme."""
import io
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from engine import assets
from engine.scene import FPS, H_IN, W_IN, SceneContext

BG0 = np.array([7, 13, 24]) / 255
BG1 = np.array([16, 30, 52]) / 255


def ffmpeg_exe():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def background(w, h, center):
    """Orijinal sahnelerdeki radyal koyu degrade (satır 0 = üst)."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w * center[0]) / w) ** 2 + ((yy - h * center[1]) / h) ** 2)
    g = np.clip(1 - d * 1.6, 0, 1)[..., None]
    return np.dstack([BG0 * (1 - g) + BG1 * g, np.ones((h, w))])


class Frames:
    """Bir sahnenin kurulmuş figürü; draw(t) istenen anın RGBA karesini verir."""

    def __init__(self, scene, params, transparent=False, dpi=100):
        self.scene = scene
        self.duration = float(params["duration"])
        self.fig = plt.figure(figsize=(W_IN, H_IN), dpi=dpi)
        self.fig.patch.set_alpha(0)
        self.w, self.h = int(round(W_IN * dpi)), int(round(H_IN * dpi))
        if not transparent:
            self.fig.figimage(background(self.w, self.h, scene.bg_center), 0, 0, zorder=-10)
        self.update = scene.setup(SceneContext(self.fig, params, transparent, assets.fonts(), dpi))

    @property
    def n_frames(self):
        return int(round(self.duration * FPS))

    def draw(self, t):
        """t: gerçek saniye; sahneye temel süre cinsinden verilir."""
        if self.duration != self.scene.base_duration:
            t = t * self.scene.base_duration / self.duration
        self.update(t)
        self.fig.canvas.draw()
        return np.array(self.fig.canvas.buffer_rgba())

    def close(self):
        plt.close(self.fig)


def to_png(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, "PNG", compress_level=1)
    return buf.getvalue()


def still_png(scene, params, t, transparent=False, dpi=50):
    fr = Frames(scene, params, transparent, dpi)
    try:
        return to_png(fr.draw(t))
    finally:
        fr.close()


def encoder_args(transparent):
    if transparent:
        return ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p"]


def video_ext(transparent):
    return ".mov" if transparent else ".mp4"


def render_video(scene, params, out_path, transparent=False, on_progress=None):
    fr = Frames(scene, params, transparent, dpi=100)
    n = fr.n_frames
    proc = subprocess.Popen([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                             "-s", f"{fr.w}x{fr.h}", "-r", str(FPS), "-i", "-", *encoder_args(transparent), out_path],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            proc.stdin.write(fr.draw(i / FPS).tobytes())
            if on_progress:
                on_progress(i + 1, n)
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg hata verdi: {err.strip()[-500:]}")
    except BaseException:
        proc.kill()
        raise
    finally:
        fr.close()
    return out_path
```

- [ ] **Step 6: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_scene.py tests/test_render.py -v`
Expected: 13 passed.

- [ ] **Step 7: Commit**

```bash
git add engine/scene.py engine/render.py tests/conftest.py tests/helpers.py tests/test_scene.py tests/test_render.py
git commit -m "Sahne sözleşmesi ve render motoru (opak/şeffaf)"
```

---

### Task 8: `scenes/state_map.py` — eyalet haritası (orijinalle birebir)

**Files:**
- Create: `scenes/state_map.py`, `projects/ornek_florida.json`
- Modify: `scenes/__init__.py`
- Test: `tests/test_state_map.py`, `tests/test_regression.py`

**Interfaces:**
- Consumes:
  - `geo.state/us_outlines/counties/albers`
  - `framing.box/state_frame/focus_frame`
  - `params.*`
  - `scene.Scene/ease/seg/fit_text`
- Produces:
  - `state_map.SCENE` (id `"state_map"`, base 13.0, bg_center (0.6, 0.45)).
  - `state_map.DEFAULT_CATEGORIES`.
  - `REGISTRY["state_map"]`.
  - Ayar adları: `state, title, subtitle, accent, categories, assign, focus, focus_name, focus_sub, focus_stat, focus_zoom, zoom, shift_x, shift_y, duration`.
  - `update(t)` durumsuzdur: aynı `t` her zaman aynı kareyi verir, önizlemede geri kaydırma güvenlidir.

- [ ] **Step 1: Örnek projeyi yaz** — `projects/ornek_florida.json`

```json
{
  "version": 1,
  "name": "ornek_florida",
  "transition": 0.6,
  "output": {"separate": true, "combined": true, "transparent": false},
  "scenes": [
    {
      "type": "state_map",
      "enabled": true,
      "params": {
        "state": "FL",
        "title": "FLORIDA",
        "subtitle": "10 COUNTIES  ·  AUGUST 2026 DATA",
        "accent": "#3ee6ff",
        "categories": [
          {"key": "buyers", "label": "BUYERS PULLED BACK", "color": "#ff5a4f"},
          {"key": "price", "label": "PRICES BREAKING", "color": "#ffb020"},
          {"key": "weak", "label": "WEAKENING", "color": "#e6d45a"},
          {"key": "stable", "label": "HOLDING STEADY", "color": "#3b6694"},
          {"key": "none", "label": "NOT ENOUGH DATA", "color": "#16233a"}
        ],
        "assign": {
          "12001": "buyers", "12005": "weak", "12009": "stable", "12011": "stable", "12015": "price",
          "12017": "stable", "12019": "buyers", "12021": "price", "12031": "stable", "12033": "stable",
          "12035": "stable", "12053": "stable", "12055": "buyers", "12057": "stable", "12061": "stable",
          "12069": "stable", "12071": "price", "12073": "stable", "12081": "price", "12083": "stable",
          "12085": "stable", "12086": "buyers", "12087": "weak", "12089": "stable", "12091": "buyers",
          "12095": "stable", "12097": "buyers", "12099": "stable", "12101": "buyers", "12103": "stable",
          "12105": "buyers", "12109": "stable", "12111": "buyers", "12113": "buyers", "12115": "price",
          "12117": "stable", "12119": "stable", "12127": "stable", "12131": "weak"
        },
        "focus": "12015",
        "focus_name": "CHARLOTTE COUNTY",
        "focus_sub": "Punta Gorda  ·  Port Charlotte",
        "focus_stat": "~900 LISTINGS PULLED IN 12 MONTHS",
        "focus_zoom": 0.55,
        "zoom": 0.822673668267268,
        "shift_x": -0.009999999999999926,
        "shift_y": 0.05222222222222225,
        "duration": 13.0
      }
    },
    {
      "type": "price_ladder",
      "enabled": true,
      "params": {
        "kicker": "LEE COUNTY  ·  FORT MYERS",
        "title": "ONE HOUSE. NINE PRICE CUTS.",
        "subtitle": "4 bedrooms  ·  built 2000  ·  listed August 2024",
        "history": [
          {"date": "2024-08-15", "price": 580000},
          {"date": "2024-09-11", "price": 574999},
          {"date": "2024-12-19", "price": 565000},
          {"date": "2025-05-13", "price": 540000},
          {"date": "2025-10-15", "price": 510000},
          {"date": "2026-02-11", "price": 490000},
          {"date": "2026-03-09", "price": 489000},
          {"date": "2026-05-04", "price": 475000},
          {"date": "2026-06-04", "price": 430000},
          {"date": "2026-06-30", "price": 410000}
        ],
        "today": "2026-09-23",
        "paid": 310000,
        "paid_year": 2017,
        "paid_text": "",
        "diff_text": "",
        "label_price": "ASKING PRICE",
        "label_days": "DAYS FOR SALE",
        "label_cuts": "PRICE CUTS",
        "accent": "#3ee6ff",
        "duration": 11.5
      }
    }
  ]
}
```

- [ ] **Step 2: Başarısız testleri yaz**

`tests/test_state_map.py`:
```python
import numpy as np
import pytest

from engine import render
from scenes import state_map

S = state_map.SCENE


def params(**kw):
    clean, errors = S.validate(kw)
    assert errors == {}
    return clean


@pytest.mark.parametrize("state,focus", [
    ("FL", "12015"), ("TX", "48201"), ("MI", "26163"), ("RI", "44007"),
    ("CA", "06037"), ("NC", "37119"), ("VA", "51760"),
])
def test_smoke_states(state, focus):
    fr = render.Frames(S, params(state=state, focus=focus), dpi=20)
    try:
        for t in (0.5, 4.0, 8.6, 10.5, 12.9):
            img = fr.draw(t)
            assert img.shape == (216, 384, 4)
            assert img[..., :3].std() > 1
    finally:
        fr.close()


def test_no_focus_keeps_state_view():
    fr = render.Frames(S, params(state="TN"), dpi=20)
    try:
        a, b = fr.draw(9.5), fr.draw(12.9)
    finally:
        fr.close()
    assert np.abs(a.astype(int) - b.astype(int)).mean() < 0.5


def test_scrubbing_backwards_is_stateless():
    fr = render.Frames(S, params(state="FL", focus="12015"), dpi=20)
    try:
        first = fr.draw(1.0)
        fr.draw(12.0)
        again = fr.draw(1.0)
    finally:
        fr.close()
    assert np.array_equal(first, again)


def test_long_title_smoke():
    fr = render.Frames(S, params(state="MA", title="MASSACHUSETTS AND NORTH CAROLINA"), dpi=20)
    try:
        assert fr.draw(6.0)[..., :3].std() > 1
    finally:
        fr.close()


def test_focus_must_be_in_state():
    _, errors = S.validate({"state": "FL", "focus": "48201"})
    assert "focus" in errors
```

`tests/test_regression.py`:
```python
"""Orijinal koddan alınan referans karelerle karşılaştırma (reference/ klasörü, Görev 1)."""
import json
import os

import numpy as np
import pytest
from PIL import Image

from engine import assets, render
from scenes import REGISTRY

REF = os.path.join(assets.ROOT, "reference")
SAMPLE = os.path.join(assets.ROOT, "projects", "ornek_florida.json")


def sample_scene(i):
    with open(SAMPLE, encoding="utf-8") as f:
        s = json.load(f)["scenes"][i]
    scene = REGISTRY[s["type"]]
    clean, errors = scene.validate(s["params"])
    assert errors == {}
    return scene, clean


def compare(scene, params, prefix, times, rows_from=0):
    fr = render.Frames(scene, params, dpi=100)
    try:
        for t in times:
            path = os.path.join(REF, f"test_{prefix}_{t:.1f}.png")
            if not os.path.exists(path):
                pytest.skip("reference/ klasöründe referans kare yok")
            ref = np.asarray(Image.open(path).convert("RGB")).astype(int)
            got = fr.draw(int(t * 30) / 30)[..., :3].astype(int)
            diff = np.abs(ref - got)[rows_from:]
            assert diff.mean() < 1.5, f"{prefix} {t} sn: ortalama fark {diff.mean():.3f}"
    finally:
        fr.close()


def test_state_map_matches_original():
    scene, p = sample_scene(0)
    compare(scene, p, "a", [2.0, 4.0, 6.0, 8.6, 10.5, 12.5])
```

- [ ] **Step 3: Testlerin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_state_map.py tests/test_regression.py -v`
Expected: FAIL. `ImportError: cannot import name 'state_map' from 'scenes'`.

- [ ] **Step 4: `scenes/state_map.py` dosyasını yaz**

```python
"""Eyalet haritası: ABD'den eyalete inen kamera, neon sınır, kategorilere boyanan county'ler, vurgulanan county.
Görünüm ve zamanlamalar orijinal scene_a.py ile aynıdır; update(t) içindeki t temel süre (13 sn) cinsindendir."""
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.collections import PolyCollection

from engine import framing, geo
from engine.params import Categories, Color, CountyAssign, CountySelect, Number, StateSelect, Text
from engine.scene import Scene, ease, fit_text, seg

DEFAULT_CATEGORIES = [
    {"key": "buyers", "label": "BUYERS PULLED BACK", "color": "#ff5a4f"},
    {"key": "price", "label": "PRICES BREAKING", "color": "#ffb020"},
    {"key": "weak", "label": "WEAKENING", "color": "#e6d45a"},
    {"key": "stable", "label": "HOLDING STEADY", "color": "#3b6694"},
    {"key": "none", "label": "NOT ENOUGH DATA", "color": "#16233a"},
]

PARAMS = [
    StateSelect("state", "Eyalet", default="FL"),
    Text("title", "Başlık", default="", auto=True, help="Boş bırakılırsa eyalet adı yazılır."),
    Text("subtitle", "Alt başlık", default=""),
    Color("accent", "Sınır rengi (neon)", default="#3ee6ff", group="Renkler"),
    Categories("categories", "Renk kategorileri", default=DEFAULT_CATEGORIES, group="Renkler"),
    CountyAssign("assign", "County boyama", default={}, group="County boyama",
                 state_param="state", categories_param="categories"),
    CountySelect("focus", "Vurgulanan county", default=None, group="Vurgu", state_param="state"),
    Text("focus_name", "Vurgu adı", default="", auto=True, group="Vurgu",
         help="Boş bırakılırsa '<AD> COUNTY' yazılır."),
    Text("focus_sub", "Vurgu alt yazısı", default="", group="Vurgu"),
    Text("focus_stat", "Vurgu istatistiği", default="", group="Vurgu",
         help="County'nin kategori renginde yazılır."),
    Number("focus_zoom", "Vurgu yakınlığı", default=0.55, group="Vurgu", lo=0.1, hi=1.5, step=0.05),
    Number("zoom", "Yakınlaştırma", default=1.0, group="Kamera", lo=0.5, hi=2.0, step=0.01),
    Number("shift_x", "Yatay kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
    Number("shift_y", "Dikey kaydırma", default=0.0, group="Kamera", lo=-0.5, hi=0.5, step=0.01),
]


def cam_lerp(a, b, t):
    e = ease(t)
    c = a[:2] + (b[:2] - a[:2]) * e
    w = np.exp(np.log(a[2]) + (np.log(b[2]) - np.log(a[2])) * e)
    return np.array([c[0], c[1], w])


def focus_title(c):
    return (f"{c.name} {c.lsad}" if c.lsad else c.name).upper()


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    BEBAS, BAR, BARB = F["bebas"], F["semibold"], F["bold"]
    NEON = p["accent"]
    fips, _, state_name = geo.state(p["state"])
    cats = p["categories"]
    col = {c["key"]: c["color"] for c in cats}

    # ---------- geometri ----------
    us = geo.us_outlines(fips)
    us_polys = [r for _, rs in us for r in rs]
    fl_rings = [r for st, rs in us if st == fips for r in rs]
    cs = geo.counties(fips)
    c_polys, c_owner = [], []
    for i, c in enumerate(cs):
        for r in c.rings:
            c_polys.append(r)
            c_owner.append(i)
    c_owner = np.array(c_owner)
    c_key = [p["assign"].get(c.fips, "none") for c in cs]

    # ---------- kamera ----------
    CAM_US = framing.box(np.vstack(us_polys), 0.06)
    CAM_FL = framing.state_frame(np.vstack(fl_rings), p["zoom"], p["shift_x"], p["shift_y"])
    ch_idx = next((i for i, c in enumerate(cs) if c.fips == p["focus"]), None)
    if ch_idx is not None:
        ch_pts = np.vstack(cs[ch_idx].rings)
        ch_center = ch_pts.mean(0)
        CAM_CH = framing.focus_frame(ch_pts, CAM_FL[2], p["focus_zoom"])

    # ---------- figür ----------
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.patch.set_alpha(0)
    for lon in range(-125, -64, 5):
        la = np.linspace(20, 52, 120)
        x, y = geo.albers(np.full_like(la, lon), la)
        ax.plot(x, y, color="#1c2c47", lw=0.6, alpha=0.5, zorder=1)
    for lat in range(20, 55, 5):
        lo = np.linspace(-130, -60, 200)
        x, y = geo.albers(lo, np.full_like(lo, lat))
        ax.plot(x, y, color="#1c2c47", lw=0.6, alpha=0.5, zorder=1)

    us_coll = PolyCollection(us_polys, facecolors="#0f1b2e", edgecolors="#2b3f60", linewidths=0.8, zorder=2)
    ax.add_collection(us_coll)
    fl_fill = PolyCollection(fl_rings, facecolors=NEON, edgecolors="none", alpha=0.0, zorder=3)
    ax.add_collection(fl_fill)
    base_rgba = np.array([mcolors.to_rgba(col[c_key[o]]) for o in c_owner])
    c_coll = PolyCollection(c_polys, facecolors=base_rgba, edgecolors="#070d18", linewidths=0.9, zorder=4)
    ax.add_collection(c_coll)

    # ana halka üzerinde neon sınır
    main = max(fl_rings, key=len)
    segl = np.hypot(*np.diff(main, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(segl)])
    glow_specs = [(16, 0.05), (10, 0.10), (6, 0.22), (2.4, 1.0)]
    glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_capstyle="round", zorder=6)[0] for w, a in glow_specs]
    isles = [r for r in fl_rings if r is not main]
    isle_lines = [ax.plot(r[:, 0], r[:, 1], color=NEON, lw=1.4, alpha=0.0, zorder=6)[0] for r in isles]
    head = ax.plot([], [], "o", color="white", ms=7, alpha=0.0, zorder=7)[0]

    def partial(t):
        L = cum[-1] * t
        k = np.searchsorted(cum, L)
        if k == 0:
            return main[:1]
        k = min(k, len(main) - 1)
        f = (L - cum[k - 1]) / max(cum[k] - cum[k - 1], 1e-9)
        pt = main[k - 1] + (main[k] - main[k - 1]) * f
        return np.vstack([main[:k], pt])

    # vurgulanan county
    ch_glow = []
    if ch_idx is not None:
        for r in cs[ch_idx].rings:
            for w, a in [(12, 0.08), (6, 0.2), (2.2, 1.0)]:
                ch_glow.append((ax.plot(r[:, 0], r[:, 1], color="#ffffff", lw=w, alpha=0.0, zorder=8)[0], a))
        lab_x = ch_center[0] - 0.19 * CAM_CH[2]
        lab_y = ch_center[1] + 0.06 * CAM_CH[2]
        leader = ax.plot([], [], color="white", lw=1.6, alpha=0.0, zorder=9)[0]
        dot = ax.plot([ch_center[0]], [ch_center[1]], "o", color="white", ms=9, alpha=0.0, zorder=9)[0]
        t_name = ax.text(lab_x, lab_y, p["focus_name"] or focus_title(cs[ch_idx]), fontproperties=BEBAS, fontsize=64,
                         color="white", ha="right", va="bottom", alpha=0, zorder=10)
        fit_text(fig, t_name, 0.30)
        t_sub = ax.text(lab_x, lab_y, p["focus_sub"], fontproperties=BAR, fontsize=24, color="#a9c3e6",
                        ha="right", va="top", alpha=0, zorder=10)
        stat_color = col[c_key[ch_idx]] if c_key[ch_idx] != "none" else NEON
        t_stat = ax.text(lab_x, lab_y, p["focus_stat"], fontproperties=BARB, fontsize=26, color=stat_color,
                         ha="right", va="top", alpha=0, zorder=10)

    # ekran yazıları
    T1 = fig.text(0.055, 0.56, p["title"] or state_name.upper(), fontproperties=BEBAS, fontsize=150,
                  color="white", alpha=0, va="bottom")
    fit_text(fig, T1, 0.34)
    T2 = fig.text(0.058, 0.545, p["subtitle"], fontproperties=BAR, fontsize=26, color="#8fb0d8", alpha=0, va="top")
    legend_items = []
    ly = 0.30 + max(0, len(cats) - 5) * 0.045
    for i, c in enumerate(cats):
        y = ly - i * 0.045
        sq = mpatches.FancyBboxPatch((0.058, y - 0.012), 0.016, 0.026, boxstyle="round,pad=0.002",
                                     transform=fig.transFigure, facecolor=c["color"], edgecolor="none", alpha=0)
        fig.add_artist(sq)
        tx = fig.text(0.082, y, c["label"], fontproperties=BAR, fontsize=22, color="#d6e4f5", alpha=0, va="center")
        legend_items.append((sq, tx))

    n_c = len(cs)
    rank = np.argsort(np.argsort(-np.array([np.vstack(c.rings)[:, 1].mean() for c in cs])))
    bgc = np.array([15 / 255, 27 / 255, 46 / 255])
    edge = np.array([[7 / 255, 13 / 255, 24 / 255, 1.0]] * len(c_owner))
    is_focus = c_owner == ch_idx if ch_idx is not None else np.zeros(len(c_owner), bool)

    def update(t):
        # kamera
        if t < 3.8:
            cam = cam_lerp(CAM_US, CAM_FL, seg(t, 0.4, 3.8))
        elif t < 9.0 or ch_idx is None:
            cam = CAM_FL
        else:
            cam = cam_lerp(CAM_FL, CAM_CH, seg(t, 9.0, 11.2))
        ax.set_xlim(cam[0] - cam[2] / 2, cam[0] + cam[2] / 2)
        ax.set_ylim(cam[1] - cam[2] * 9 / 32, cam[1] + cam[2] * 9 / 32)

        # içeri girerken ABD kararır
        us_coll.set_alpha(1.0 - 0.45 * seg(t, 2.0, 4.0))

        # sınır çizimi
        d = seg(t, 1.6, 4.6)
        if d > 0:
            pts = partial(ease(d))
            for ln in glow:
                ln.set_data(pts[:, 0], pts[:, 1])
            head.set_data([pts[-1, 0]], [pts[-1, 1]])
            head.set_alpha(0.9 * (1 - seg(t, 4.5, 4.9)))
        else:
            for ln in glow:
                ln.set_data([], [])
            head.set_data([], [])
            head.set_alpha(0.0)
        for ln in isle_lines:
            ln.set_alpha(0.8 * seg(t, 4.2, 4.9))
        fl_fill.set_alpha(0.10 * seg(t, 4.3, 5.0) * (1 - seg(t, 5.2, 6.0)))

        # county'ler sırayla belirir; vurgu sırasında diğerleri kararır
        cols = base_rgba.copy()
        a = np.array([seg(t, 5.0 + 2.6 * rank[o] / n_c, 5.6 + 2.6 * rank[o] / n_c) for o in c_owner])
        focus = seg(t, 9.2, 10.0) if ch_idx is not None else 0.0
        k = np.where(is_focus, 0.0, 0.62 * focus)[:, None]
        cols[:, :3] = cols[:, :3] * (1 - k) + bgc * k
        cols[:, 3] = a * 0.95
        c_coll.set_facecolors(cols)
        ec = edge.copy()
        ec[:, 3] = a
        c_coll.set_edgecolors(ec)

        # county'lerden sonra parıltı yumuşar
        soft = 1.0 - 0.35 * seg(t, 7.5, 8.5)
        for ln, (_, a0) in zip(glow, glow_specs):
            ln.set_alpha(a0 * soft)

        # başlıklar
        tt = seg(t, 4.6, 5.4)
        fo = 1 - seg(t, 9.0, 9.6) if ch_idx is not None else 1.0
        T1.set_alpha(ease(tt) * fo)
        T1.set_y(0.56 + 0.02 * ease(tt))
        T2.set_alpha(ease(seg(t, 5.0, 5.8)) * fo)
        for i, (sq, tx) in enumerate(legend_items):
            la = ease(seg(t, 7.4 + i * 0.12, 8.0 + i * 0.12))
            sq.set_alpha(la)
            tx.set_alpha(la)

        if ch_idx is None:
            return
        # vurgu nabzı ve etiket
        pa = seg(t, 9.6, 10.2)
        pulse = 0.55 + 0.45 * np.cos((t - 9.6) * 2 * np.pi * 0.9) if t > 9.6 else 0
        for ln, a0 in ch_glow:
            ln.set_alpha(a0 * pa * (0.35 + 0.65 * max(pulse, 0)))
        lp = ease(seg(t, 10.3, 10.9))
        elbow = (lab_x + 0.01 * CAM_CH[2], lab_y)
        ex = ch_center[0] + (elbow[0] - ch_center[0]) * lp
        ey = ch_center[1] + (elbow[1] - ch_center[1]) * lp
        leader.set_data([ch_center[0], ex], [ch_center[1], ey])
        leader.set_alpha(0.9 * (lp > 0))
        dot.set_alpha(pa)
        na = ease(seg(t, 10.7, 11.3))
        t_name.set_alpha(na)
        t_sub.set_alpha(na)
        t_name.set_position((lab_x, lab_y + 0.004 * CAM_CH[2]))
        t_sub.set_position((lab_x, lab_y - 0.004 * CAM_CH[2]))
        t_stat.set_position((lab_x, lab_y - 0.034 * CAM_CH[2]))
        t_stat.set_alpha(ease(seg(t, 11.4, 12.0)))

    return update


SCENE = Scene(id="state_map", title="Eyalet haritası", base_duration=13.0, params=PARAMS, setup=setup,
              bg_center=(0.6, 0.45))
```

`scenes/__init__.py`:
```python
"""Sahne kaydı: sahne id -> Scene."""
from scenes import state_map

REGISTRY = {s.id: s for s in (state_map.SCENE,)}
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_state_map.py tests/test_regression.py -v`
Expected: 12 passed. Regresyon testi 6 karede ortalama farkı < 1,5 bulmalı (beklenen ≈ 0).

Geçmezse sırayla şunlara bak:
1. `geo.us_outlines` sırası.
2. `framing.state_frame` sonucu (`tests/test_framing.py::test_florida_sample_reproduces_original_camera`).
3. `update` içindeki satırların orijinal `scene_a.py` (commit `b2f3daf`) ile karşılaştırması: `git show b2f3daf:scene_a.py`.

- [ ] **Step 6: Gözle kontrol**

Run: `.venv\Scripts\python -c "from engine import render; from tests.test_regression import sample_scene; s,p=sample_scene(0); open('out/kontrol_a.png','wb').write(render.still_png(s,p,12.5,dpi=100))"`
`out/kontrol_a.png` dosyasını aç. `reference/test_a_12.5.png` ile aynı görünmeli: Charlotte vurgusu, etiket ve turuncu istatistik yazısı.

- [ ] **Step 7: Commit**

```bash
git add scenes projects tests/test_state_map.py tests/test_regression.py
git commit -m "Eyalet haritası sahnesi (48 eyalet) ve Florida örnek projesi"
```

---

### Task 9: `scenes/price_ladder.py` — fiyat merdiveni (orijinalle birebir)

**Files:**
- Create: `scenes/price_ladder.py`
- Modify: `scenes/__init__.py`, `tests/test_regression.py`
- Test: `tests/test_price_ladder.py`

**Interfaces:**
- Consumes: `params.*`, `scene.Scene/ease/seg`.
- Produces:
  - `price_ladder.SCENE` (id `"price_ladder"`, base 11.5, bg_center (0.4, 0.5), `check`).
  - Saf fonksiyonlar: `money_short(v)`, `money_axis(v)`, `change_label(prev, cur)`, `nice_step(r)`, `y_axis(prices, paid=None) -> ((y0, y1), ticks)`, `x_ticks(listed: date, today: date) -> [(gün, etiket)]`, `auto_title(n)`, `auto_paid_text(paid, year)`, `auto_diff_text(last, paid)`, `n_cuts(prices)`.
  - Ayar adları: `kicker, title, subtitle, history, today, paid, paid_year, paid_text, diff_text, label_price, label_days, label_cuts, accent, duration`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_price_ladder.py`

```python
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
```

`tests/test_regression.py` dosyasının sonuna ekle:
```python


def test_price_ladder_matches_original():
    scene, p = sample_scene(1)
    compare(scene, p, "b", [1.0, 5.0, 8.0, 10.5])
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_price_ladder.py tests/test_regression.py -v`
Expected: FAIL. `ImportError: cannot import name 'price_ladder'`.

- [ ] **Step 3: `scenes/price_ladder.py` dosyasını yaz**

```python
"""Fiyat merdiveni: bir evin fiyat geçmişi, sayaçlar ve alış fiyatıyla karşılaştırma.
Görünüm ve zamanlamalar orijinal scene_b.py ile aynıdır; update(t) içindeki t temel süre (11,5 sn) cinsindendir."""
import datetime as dt
import math

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from engine.params import Color, Date, Number, PriceTable, Text
from engine.scene import Scene, ease, seg

RED, AMBER, MUTED = "#ff5a4f", "#ffb020", "#8fb0d8"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
NUM_WORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN",
             "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN", "TWENTY"]
# Orijinal yerleşim 769 günlük ve 340.000 $'lık eksen için elle ayarlanmıştı; ofsetler bu oranlarla ölçeklenir.
REF_DAYS, REF_SPAN = 769, 340000

PARAMS = [
    Text("kicker", "Üst etiket", default=""),
    Text("title", "Başlık", default="", auto=True, help="Boş bırakılırsa 'ONE HOUSE. <N> PRICE CUTS.' yazılır."),
    Text("subtitle", "Alt başlık", default=""),
    PriceTable("history", "Fiyat geçmişi", group="Veri", help="İlk satır ilan tarihi ve ilk fiyattır.",
               default=[{"date": "2024-08-15", "price": 580000}, {"date": "2025-01-10", "price": 560000}]),
    Date("today", "Bugünün tarihi", default=dt.date.today().isoformat(), group="Veri"),
    Number("paid", "Alış fiyatı ($)", default=None, group="Veri", lo=0, integer=True, optional=True),
    Number("paid_year", "Alış yılı", default=None, group="Veri", lo=1900, hi=2100, integer=True, optional=True),
    Text("paid_text", "Alış yazısı", default="", auto=True, group="Veri"),
    Text("diff_text", "Fark yazısı", default="", auto=True, multiline=True, group="Veri"),
    Text("label_price", "Fiyat etiketi", default="ASKING PRICE"),
    Text("label_days", "Gün etiketi", default="DAYS FOR SALE"),
    Text("label_cuts", "İndirim etiketi", default="PRICE CUTS"),
    Color("accent", "Çizgi rengi (neon)", default="#3ee6ff", group="Renkler"),
]


def money_short(v):
    a = abs(v)
    if a >= 1_000_000:
        return f"${a / 1e6:.1f}M".replace(".0M", "M")
    return f"${round(a / 1000):.0f}K"


def money_axis(v):
    return f"${v / 1e6:g}M" if v >= 1_000_000 else f"${v / 1000:.0f}K"


def change_label(prev, cur):
    return ("−" if cur < prev else "+") + money_short(prev - cur)


def nice_step(r):
    """1-2-2,5-5 x 10^k serisinden, r aralığına en fazla 4 adım sığdıran en küçük değer."""
    e = math.floor(math.log10(r / 4))
    for scale in (10 ** e, 10 ** (e + 1)):
        for m in (1, 2, 2.5, 5):
            if r / (m * scale) <= 4:
                return m * scale
    return 10 ** (e + 1)


def y_axis(prices, paid=None):
    lo = min(list(prices) + ([paid] if paid is not None else []))
    hi = max(prices)
    r = (hi - lo) or max(hi * 0.1, 1000)
    step = nice_step(r)
    unit = step / 10
    y0 = round((lo - 0.11 * r) / unit) * unit
    y1 = round((hi + 0.15 * r) / unit) * unit
    first = math.ceil(y0 / step) * step
    ticks = [first + i * step for i in range(int((y1 - first) // step) + 1)]
    return (y0, y1), ticks


def x_ticks(listed, today):
    end = (today - listed).days
    ticks = [(0, f"{MONTHS[listed.month - 1]} {listed.year}")]
    for year in range(listed.year + 1, today.year + 1):
        d = (dt.date(year, 1, 1) - listed).days
        if d >= 0.06 * end and end - d >= 0.06 * end:
            ticks.append((d, str(year)))
    ticks.append((end, "TODAY"))
    return ticks


def n_cuts(prices):
    return sum(1 for a, b in zip(prices, prices[1:]) if b < a)


def auto_title(n):
    word = NUM_WORDS[n] if n <= 20 else str(n)
    return f"ONE HOUSE. {word} PRICE {'CUT' if n == 1 else 'CUTS'}."


def auto_paid_text(paid, year):
    return f"OWNER PAID ${paid:,}" + (f" IN {year}" if year else "")


def auto_diff_text(last, paid):
    d = last - paid
    if d >= 0:
        return f"STILL +${d:,}\nABOVE WHAT THEY PAID"
    return f"NOW −${-d:,}\nBELOW WHAT THEY PAID"


def check(p):
    if p["today"] < p["history"][-1]["date"]:
        return {"today": "Bugünün tarihi fiyat geçmişindeki son tarihten önce olamaz."}
    return {}


def setup(ctx):
    p, fig, F = ctx.p, ctx.fig, ctx.fonts
    BEBAS, BAR, BARB = F["bebas"], F["semibold"], F["bold"]
    NEON = p["accent"]
    hist = p["history"]
    listed = dt.date.fromisoformat(hist[0]["date"])
    today = dt.date.fromisoformat(p["today"])
    X = np.array([(dt.date.fromisoformat(r["date"]) - listed).days for r in hist], float)
    P = np.array([r["price"] for r in hist], float)
    END = (today - listed).days
    paid, paid_year = p["paid"], p["paid_year"]
    (Y0, Y1), yticks = y_axis([r["price"] for r in hist], paid)
    SPAN = Y1 - Y0
    drops = P[1:] < P[:-1]

    def price_at(x):
        return P[np.searchsorted(X, x, side="right") - 1]

    def path_upto(x):
        xs, ys = [X[0]], [P[0]]
        for i in range(1, len(X)):
            if X[i] > x:
                break
            xs += [X[i], X[i]]
            ys += [P[i - 1], P[i]]
        xs.append(x)
        ys.append(price_at(x))
        return np.array(xs), np.array(ys)

    ax = fig.add_axes([0.07, 0.12, 0.58, 0.56])
    ax.patch.set_alpha(0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlim(-END * 15 / REF_DAYS, END + END * 25 / REF_DAYS)
    ax.set_ylim(Y0, Y1)
    ax.tick_params(colors=MUTED, length=0, labelsize=18)
    ax.set_yticks(yticks)
    ax.set_yticklabels([money_axis(v) for v in yticks], fontproperties=BAR, fontsize=20)
    xt = x_ticks(listed, today)
    ax.set_xticks([d for d, _ in xt])
    ax.set_xticklabels([s for _, s in xt], fontproperties=BAR, fontsize=20)
    grid = [ax.axhline(v, color="#1f3050", lw=1, zorder=0) for v in yticks]

    glow_specs = [(14, 0.06), (8, 0.14), (4.5, 0.3), (2.4, 1.0)]
    glow = [ax.plot([], [], color=NEON, lw=w, alpha=a, solid_joinstyle="miter", zorder=5)[0] for w, a in glow_specs]
    head = ax.plot([], [], "o", color="white", ms=11, zorder=7)[0]
    head_ring = ax.plot([], [], "o", color=NEON, ms=26, alpha=0.25, zorder=6)[0]
    fill = [None]

    cut_dots, cut_labels = [], []
    for i in range(1, len(X)):
        color = RED if drops[i - 1] else NEON
        cut_dots.append(ax.plot([X[i]], [P[i]], "o", color=color, ms=9, alpha=0, zorder=8)[0])
        above = i % 2 == 1
        yv = P[i - 1] + SPAN * 14000 / REF_SPAN if above else P[i] - SPAN * 24000 / REF_SPAN
        cut_labels.append(ax.text(X[i] if above else X[i] - END * 6 / REF_DAYS, yv, change_label(P[i - 1], P[i]),
                                  fontproperties=BARB, fontsize=20, color=color,
                                  ha="center" if above else "right", va="center", alpha=0, zorder=9))

    if paid is not None:
        paid_line = ax.plot([], [], color=AMBER, lw=2.4, ls=(0, (6, 5)), zorder=4)[0]
        paid_txt = ax.text(END * 10 / REF_DAYS, paid + SPAN * 9000 / REF_SPAN,
                           p["paid_text"] or auto_paid_text(paid, paid_year), fontproperties=BARB, fontsize=22,
                           color=AMBER, ha="left", va="bottom", alpha=0, zorder=9)
        bx = END + END * 8 / REF_DAYS
        brk = ax.annotate("", xy=(bx, paid), xytext=(bx, P[-1]),
                          arrowprops=dict(arrowstyle="<->", color=AMBER, lw=2.2), alpha=0, zorder=9)
        brk_txt = ax.text(END - END * 12 / REF_DAYS, (paid + P[-1]) / 2,
                          p["diff_text"] or auto_diff_text(int(P[-1]), paid), fontproperties=BARB, fontsize=22,
                          color=AMBER, ha="right", va="center", alpha=0, zorder=9, linespacing=1.1)

    # başlık
    K = fig.text(0.07, 0.905, p["kicker"], fontproperties=BAR, fontsize=26, color=NEON, alpha=0)
    T = fig.text(0.068, 0.885, p["title"] or auto_title(n_cuts(list(P))), fontproperties=BEBAS, fontsize=92,
                 color="white", alpha=0, va="top")
    S = fig.text(0.07, 0.765, p["subtitle"], fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)

    # sağ panel
    PX = 0.73

    def block(y, label, big):
        lab = fig.text(PX, y, label, fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)
        val = fig.text(PX - 0.003, y - 0.012, "", fontproperties=BEBAS, fontsize=big, color="white", alpha=0, va="top")
        return lab, val

    L1, V1 = block(0.66, p["label_price"], 118)
    L2, V2 = block(0.44, p["label_days"], 96)
    L3, V3 = block(0.25, p["label_cuts"], 96)
    sep = [fig.add_artist(plt.Line2D([PX, 0.95], [y, y], transform=fig.transFigure, color="#1f3050", lw=1.2, alpha=0))
           for y in (0.475, 0.285)]
    white, red = np.array(mcolors.to_rgb("white")), np.array(mcolors.to_rgb(RED))

    def update(t):
        ha = ease(seg(t, 0.0, 0.8))
        K.set_alpha(ha)
        T.set_alpha(ha)
        S.set_alpha(ease(seg(t, 0.3, 1.1)))
        pa = ease(seg(t, 0.6, 1.6))
        for o in (L1, L2, L3, V1, V2, V3):
            o.set_alpha(pa)
        for s in sep:
            s.set_alpha(pa)
        axa = ease(seg(t, 1.0, 2.2))
        for gl in grid:
            gl.set_alpha(axa)
        for lab in ax.get_xticklabels() + ax.get_yticklabels():
            lab.set_alpha(axa)

        prog = seg(t, 2.4, 8.4)
        xh = END * prog
        if fill[0] is not None:
            fill[0].remove()
            fill[0] = None
        if t >= 2.4:
            xs, ys = path_upto(xh)
            for ln in glow:
                ln.set_data(xs, ys)
            head.set_data([xh], [ys[-1]])
            head_ring.set_data([xh], [ys[-1]])
            fill[0] = ax.fill_between(xs, ys, Y0, color=NEON, alpha=0.07, lw=0, zorder=2)
        else:
            for ln in glow:
                ln.set_data([], [])
            head.set_data([], [])
            head_ring.set_data([], [])
        cur = price_at(xh) if t >= 2.4 else P[0]
        ncut = int(np.sum((X[1:] <= xh) & drops)) if t >= 2.4 else 0
        flash = 0.0
        for i in range(1, len(X)):
            dtc = (xh - X[i]) / END * 6.0  # baş bu noktayı geçeli kaç saniye oldu
            a = ease(np.clip(dtc / 0.25, 0, 1)) if xh >= X[i] and t >= 2.4 else 0
            cut_dots[i - 1].set_alpha(a)
            cut_labels[i - 1].set_alpha(a)
            if 0 <= dtc < 0.35 and xh >= X[i] and drops[i - 1]:
                flash = max(flash, 1 - dtc / 0.35)
        V1.set_text(f"${int(cur):,}")
        V1.set_color(tuple(white * (1 - flash) + red * flash))
        V2.set_text(f"{int(round(xh)) if t >= 2.4 else 0}")
        V3.set_text(f"{ncut}")

        if paid is None:
            return
        pl = ease(seg(t, 8.7, 9.5))
        paid_line.set_data([0, END * pl], [paid, paid])
        paid_txt.set_alpha(ease(seg(t, 9.0, 9.6)))
        ba = ease(seg(t, 9.7, 10.3))
        brk.arrow_patch.set_alpha(ba)
        brk_txt.set_alpha(ba)

    return update


SCENE = Scene(id="price_ladder", title="Fiyat merdiveni", base_duration=11.5, params=PARAMS, setup=setup,
              bg_center=(0.4, 0.5), check=check)
```

`scenes/__init__.py`:
```python
"""Sahne kaydı: sahne id -> Scene."""
from scenes import price_ladder, state_map

REGISTRY = {s.id: s for s in (state_map.SCENE, price_ladder.SCENE)}
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_price_ladder.py tests/test_regression.py -v`
Expected: 10 passed. `test_price_ladder_matches_original` 4 karede ortalama farkı < 1,5 bulmalı.

- [ ] **Step 5: Tüm testleri çalıştır**

Run: `.venv\Scripts\python -m pytest`
Expected: tümü geçer.

- [ ] **Step 6: Commit**

```bash
git add scenes tests/test_price_ladder.py tests/test_regression.py
git commit -m "Fiyat merdiveni sahnesi (fiyat geçmişi ayardan)"
```

---

### Task 10: Fiyat merdiveninde başlık ile alt başlığın çakışmasını düzelt

Orijinal tasarımda alt başlık (`S`, y=0.765, taban çizgisi) büyük başlığın (`T`, 92 pt Bebas, y=0.885'ten aşağı) alt kısmına biniyor (bkz. `reference/test_b_10.5.png`). Alt başlık başlığın altına taşınacak.

**Files:**
- Modify: `scenes/price_ladder.py` (`S = fig.text(...)` satırı), `tests/test_regression.py`

- [ ] **Step 1: Regresyon testini başlık alanını hariç tutacak şekilde değiştir**

`tests/test_regression.py` içinde:
```python
def test_price_ladder_matches_original():
    scene, p = sample_scene(1)
    # Görev 10: alt başlık başlığın altına taşındı; üstteki 320 piksel satır karşılaştırılmaz.
    compare(scene, p, "b", [1.0, 5.0, 8.0, 10.5], rows_from=320)
```

- [ ] **Step 2: Alt başlığı taşı**

`scenes/price_ladder.py` içinde:
```python
    S = fig.text(0.07, 0.765, p["subtitle"], fontproperties=BAR, fontsize=24, color=MUTED, alpha=0)
```
satırını şununla değiştir:
```python
    S = fig.text(0.07, 0.745, p["subtitle"], fontproperties=BAR, fontsize=24, color=MUTED, alpha=0, va="top")
```

- [ ] **Step 3: Gözle kontrol**

Run: `.venv\Scripts\python -c "from engine import render; from tests.test_regression import sample_scene; s,p=sample_scene(1); open('out/kontrol_b.png','wb').write(render.still_png(s,p,10.5,dpi=100))"`
`out/kontrol_b.png` dosyasını aç. Kontrol edilecekler:
- Alt başlık büyük başlığın altında ve aralarında boşluk var.
- Alt başlık grafiğin "$600K" etiketine değmiyor.

Değiyorsa y değerini 0,005'lik adımlarla ayarla (0,735–0,755 aralığı).

- [ ] **Step 4: Testler**

Run: `.venv\Scripts\python -m pytest tests/test_regression.py tests/test_price_ladder.py -v`
Expected: tümü geçer.

- [ ] **Step 5: Commit**

```bash
git add scenes/price_ladder.py tests/test_regression.py
git commit -m "Fiyat merdiveni: alt başlık artık başlığın üstüne binmiyor"
```

---

### Task 11: `engine/project.py` — proje dosyası

**Files:**
- Create: `engine/project.py`
- Test: `tests/test_project.py`

**Interfaces:**
- Consumes: `scenes.REGISTRY`, `Scene.validate/defaults`, `assets.ROOT`.
- Produces:
  - `project.PROJECTS` (klasör), `project.VERSION = 1`, `project.NAME_RE`, `project.ProjectError`.
  - `default_output() -> {"separate": True, "combined": True, "transparent": False}`, `new_project(name="yeni_proje") -> dict`.
  - `validate(project) -> (clean, errors)`: hata listesi `[{"scene": int|None, "param": str|None, "message": str}]`. Yapısal hatada `ProjectError` fırlatır.
  - `path_for(name) -> str`, `load(path) -> (clean, errors)`, `save(project, path=None) -> path`, `list_projects() -> list[str]`.

- [ ] **Step 1: Başarısız testi yaz** — `tests/test_project.py`

```python
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
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_project.py -v`
Expected: FAIL. `ImportError: cannot import name 'project'`.

- [ ] **Step 3: `engine/project.py` dosyasını yaz**

```python
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
```

- [ ] **Step 4: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_project.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add engine/project.py tests/test_project.py
git commit -m "Proje dosyası: doğrulama, yükleme, kaydetme"
```

---

### Task 12: `engine/compose.py` ve `engine/cli.py` — birleştirme ve komut satırı

**Files:**
- Create: `engine/compose.py`, `engine/cli.py`
- Test: `tests/test_compose.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes:
  - `render.render_video/still_png/encoder_args/video_ext/ffmpeg_exe`
  - `project.load/validate/ProjectError`
  - `assets.ensure/AssetError/ROOT`
  - `scenes.REGISTRY`
- Produces:
  - `compose.xfade_offsets(durations, transition) -> list[float]`.
  - `compose.compose(paths, durations, out_path, transition=0.6, transparent=False) -> out_path`.
  - `cli.run_render(project_clean, out_dir, emit) -> list[str]`: `emit(**event)` olayları `progress` (scene, scenes, frame, total), `compose` ve `output` (path).
  - `cli.output_dir(project, out=None) -> str`, `cli.main(argv=None) -> int`.
  - `--progress-json` açıkken stdout'a satır başına bir JSON olayı yazılır: `log`, `progress`, `compose`, `output`, `done` ya da `error`.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_compose.py`:
```python
import imageio_ffmpeg
import pytest

from engine import compose, render
from tests.helpers import decode_frame


def test_offsets():
    assert compose.xfade_offsets([13.0, 11.5], 0.6) == pytest.approx([12.4])
    assert compose.xfade_offsets([2.0, 3.0, 4.0], 0.5) == pytest.approx([1.5, 4.0])


def _clips(scene, tmp_path, ext, transparent=False):
    return [render.render_video(scene, scene.defaults(), str(tmp_path / f"{n}{ext}"), transparent) for n in "ab"]


def test_compose_crossfade(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mp4"), transition=0.5)
    assert imageio_ffmpeg.count_frames_and_secs(out) == (45, 1.5)


def test_compose_hard_cut(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mp4"), transition=0)
    assert imageio_ffmpeg.count_frames_and_secs(out) == (60, 2.0)


def test_compose_transparent_keeps_alpha(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mov", transparent=True)
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mov"), transition=0.5, transparent=True)
    f = decode_frame(out, 0.75, 1920, 1080)
    assert f[0, 0, 3] == 0 and f[540, 960, 3] == 255


def test_single_clip_is_copied(dummy_scene, tmp_path):
    a, _ = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a], [1.0], str(tmp_path / "tek.mp4"))
    assert imageio_ffmpeg.count_frames_and_secs(out) == (30, 1.0)
```

`tests/test_cli.py`:
```python
import json
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from engine import assets, cli
from tests.helpers import decode_frame

SAMPLE = os.path.join("projects", "ornek_florida.json")


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "engine.cli", *args], cwd=assets.ROOT, capture_output=True,
                          text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})


def test_still(tmp_path):
    out = tmp_path / "kare.png"
    r = run_cli("still", SAMPLE, "--scene", "0", "--t", "8.6", "--out", str(out), "--dpi", "50")
    assert r.returncode == 0, r.stderr
    assert Image.open(out).size == (960, 540)


def test_bad_project_reports_error_event(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": 1, "name": "x",
                               "scenes": [{"type": "state_map", "params": {"accent": "mavi"}}]}), encoding="utf-8")
    r = run_cli("render", str(bad), "--progress-json")
    assert r.returncode == 1
    last = json.loads(r.stdout.strip().splitlines()[-1])
    assert last["event"] == "error" and "accent" in last["message"]


def test_run_render_combined_only(dummy_scene, tmp_path, monkeypatch):
    monkeypatch.setitem(cli.REGISTRY, "dummy", dummy_scene)
    p = {"name": "t", "transition": 0.5,
         "output": {"separate": False, "combined": True, "transparent": False},
         "scenes": [{"type": "dummy", "enabled": True, "params": dummy_scene.defaults()} for _ in range(2)]}
    events = []
    outs = cli.run_render(p, str(tmp_path), lambda **e: events.append(e))
    assert [os.path.basename(o) for o in outs] == ["birlesik.mp4"]
    assert sorted(os.listdir(tmp_path)) == ["birlesik.mp4"]
    assert events[-1] == {"event": "output", "path": outs[0]}
    assert any(e["event"] == "compose" for e in events)
    assert events[0] == {"event": "progress", "scene": 0, "scenes": 2, "frame": 1, "total": 30}


def test_run_render_single_scene_ignores_combine(dummy_scene, tmp_path, monkeypatch):
    monkeypatch.setitem(cli.REGISTRY, "dummy", dummy_scene)
    p = {"name": "t", "transition": 0.5,
         "output": {"separate": False, "combined": True, "transparent": True},
         "scenes": [{"type": "dummy", "enabled": True, "params": dummy_scene.defaults()},
                    {"type": "dummy", "enabled": False, "params": dummy_scene.defaults()}]}
    outs = cli.run_render(p, str(tmp_path), lambda **e: None)
    assert [os.path.basename(o) for o in outs] == ["01_dummy.mov"]


@pytest.mark.slow
def test_render_sample_matches_original_length(tmp_path):
    r = run_cli("render", SAMPLE, "--out", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert imageio_ffmpeg.count_frames_and_secs(str(tmp_path / "birlesik.mp4")) == (717, 23.9)
    assert (tmp_path / "01_state_map.mp4").exists() and (tmp_path / "02_price_ladder.mp4").exists()


@pytest.mark.slow
def test_render_transparent(tmp_path):
    with open(os.path.join(assets.ROOT, SAMPLE), encoding="utf-8") as f:
        p = json.load(f)
    p["scenes"][0]["params"]["duration"] = 6.5
    p["scenes"][1]["params"]["duration"] = 5.75
    src = tmp_path / "p.json"
    src.write_text(json.dumps(p), encoding="utf-8")
    r = run_cli("render", str(src), "--out", str(tmp_path / "o"), "--transparent")
    assert r.returncode == 0, r.stderr
    f = decode_frame(str(tmp_path / "o" / "birlesik.mov"), 3.0, 1920, 1080)
    assert (f[..., 3] == 0).mean() > 0.2 and f[..., 3].max() == 255
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_compose.py tests/test_cli.py -v`
Expected: FAIL. `ImportError: cannot import name 'compose'`.

- [ ] **Step 3: `engine/compose.py` dosyasını yaz**

```python
"""Sahne videolarını xfade geçişiyle (ya da geçişsiz) tek videoda birleştirir."""
import shutil
import subprocess

from engine.render import encoder_args, ffmpeg_exe


def xfade_offsets(durations, transition):
    """k'ıncı geçişin başlangıcı: sum(d[0..k]) - (k+1)*transition."""
    out, acc = [], 0.0
    for k, d in enumerate(durations[:-1]):
        acc += d
        out.append(acc - (k + 1) * transition)
    return out


def compose(paths, durations, out_path, transition=0.6, transparent=False):
    if len(paths) == 1:
        shutil.copyfile(paths[0], out_path)
        return out_path
    fmt = "yuva444p10le" if transparent else "yuv420p"
    n = len(paths)
    if transition <= 0:
        chain = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0,format={fmt}[v]"
    else:
        parts = [f"[{i}:v]format={fmt}[s{i}]" for i in range(n)] if transparent else []
        src = (lambda i: f"s{i}") if transparent else (lambda i: f"{i}:v")
        prev = src(0)
        for k, off in enumerate(xfade_offsets(durations, transition)):
            label = f"x{k}"
            parts.append(f"[{prev}][{src(k + 1)}]xfade=transition=fade:duration={transition}:offset={off:.4f}[{label}]")
            prev = label
        parts.append(f"[{prev}]format={fmt}[v]")
        chain = ";".join(parts)
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error"]
    for p in paths:
        cmd += ["-i", p]
    cmd += ["-filter_complex", chain, "-map", "[v]", *encoder_args(transparent), out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"Birleştirme başarısız: {r.stderr.strip()[-500:]}")
    return out_path
```

- [ ] **Step 4: `engine/cli.py` dosyasını yaz**

```python
"""Arayüzsüz kullanım.
  python -m engine.cli render projects/ornek_florida.json [--out KLASOR] [--transparent|--opaque]
                                                         [--no-combined] [--no-separate] [--progress-json]
  python -m engine.cli still projects/ornek_florida.json --scene 0 --t 8.6 --out kare.png [--dpi 100]
"""
import argparse
import datetime as dt
import json
import os
import sys

from engine import assets, compose, render
from engine import project as proj
from scenes import REGISTRY


def output_dir(project, out=None):
    return out or os.path.join(assets.ROOT, "out", project["name"], dt.datetime.now().strftime("%Y%m%d-%H%M%S"))


def run_render(project, out_dir, emit):
    """Doğrulanmış projeyi render eder, üretilen dosyaların yollarını döndürür."""
    o = project["output"]
    ext = render.video_ext(o["transparent"])
    os.makedirs(out_dir, exist_ok=True)
    enabled = [s for s in project["scenes"] if s["enabled"]]
    paths, durations = [], []
    for i, s in enumerate(enabled):
        path = os.path.join(out_dir, f"{i + 1:02d}_{s['type']}{ext}")
        render.render_video(REGISTRY[s["type"]], s["params"], path, o["transparent"],
                            on_progress=lambda f, n, i=i: emit(event="progress", scene=i, scenes=len(enabled),
                                                                frame=f, total=n))
        paths.append(path)
        durations.append(float(s["params"]["duration"]))
    outputs = []
    if o["combined"] and len(paths) > 1:
        emit(event="compose")
        combined = os.path.join(out_dir, "birlesik" + ext)
        compose.compose(paths, durations, combined, project["transition"], o["transparent"])
        outputs.append(combined)
    if o["separate"] or not outputs:
        outputs = paths + outputs
    else:
        for p in paths:
            os.remove(p)
    for p in outputs:
        emit(event="output", path=p)
    return outputs


def _describe(errors):
    return "Projede hatalı ayarlar var:\n" + "\n".join(
        f"- {'proje' if e['scene'] is None else str(e['scene'] + 1) + '. sahne'} / {e['param']}: {e['message']}"
        for e in errors)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="python -m engine.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="projeyi videoya dönüştürür")
    r.add_argument("project")
    r.add_argument("--out")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--transparent", action="store_true")
    g.add_argument("--opaque", action="store_true")
    r.add_argument("--no-combined", action="store_true")
    r.add_argument("--no-separate", action="store_true")
    r.add_argument("--progress-json", action="store_true")
    s = sub.add_parser("still", help="tek kare PNG üretir")
    s.add_argument("project")
    s.add_argument("--scene", type=int, default=0)
    s.add_argument("--t", type=float, default=0.0)
    s.add_argument("--out", required=True)
    s.add_argument("--dpi", type=int, default=100)
    s.add_argument("--transparent", action="store_true")
    args = ap.parse_args(argv)
    as_json = getattr(args, "progress_json", False)

    def emit(**ev):
        if as_json:
            print(json.dumps(ev, ensure_ascii=False), flush=True)
        elif ev["event"] == "progress" and (ev["frame"] % 60 == 0 or ev["frame"] == ev["total"]):
            print(f"sahne {ev['scene'] + 1}/{ev['scenes']}: kare {ev['frame']}/{ev['total']}", flush=True)
        elif ev["event"] == "compose":
            print("sahneler birleştiriliyor...", flush=True)
        elif ev["event"] == "output":
            print("çıktı:", ev["path"], flush=True)
        elif ev["event"] == "log":
            print(ev["message"], flush=True)

    try:
        assets.ensure(log=lambda m: emit(event="log", message=m))
        project, errors = proj.load(args.project)
        if errors:
            raise proj.ProjectError(_describe(errors))
        if args.cmd == "render":
            o = project["output"]
            if args.transparent:
                o["transparent"] = True
            if args.opaque:
                o["transparent"] = False
            if args.no_combined:
                o["combined"] = False
            if args.no_separate:
                o["separate"] = False
            errors = proj.validate(project)[1]  # seçenek değişiklikleri proje kurallarını bozmasın
            if errors:
                raise proj.ProjectError(_describe(errors))
            run_render(project, output_dir(project, args.out), emit)
            emit(event="done")
            if not as_json:
                print("BİTTİ")
        else:
            sc = project["scenes"][args.scene]
            png = render.still_png(REGISTRY[sc["type"]], sc["params"], args.t, args.transparent, args.dpi)
            with open(args.out, "wb") as f:
                f.write(png)
            print(args.out)
        return 0
    except (proj.ProjectError, assets.AssetError, RuntimeError, IndexError, OSError) as e:
        if as_json:
            print(json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False), flush=True)
        else:
            print("HATA:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_compose.py tests/test_cli.py -v`
Expected: 9 passed, 2 deselected (slow).

Run: `.venv\Scripts\python -m pytest tests/test_cli.py -m slow -v`
Expected: 2 passed (yaklaşık 3–4 dakika).

- [ ] **Step 6: Commit**

```bash
git add engine/compose.py engine/cli.py tests/test_compose.py tests/test_cli.py
git commit -m "Birleştirme ve komut satırı arayüzü"
```

---

### Task 13: `app/jobs.py`, `app/server.py`, `run_ui.py` — web sunucusu

**Files:**
- Create: `app/__init__.py` (boş), `app/jobs.py`, `app/server.py`, `app/static/index.html` (geçici, Görev 14'te değişecek), `run_ui.py`
- Test: `tests/test_jobs.py`, `tests/test_server.py`

**Interfaces:**
- Consumes:
  - `project.*`, `geo.STATES/state/counties/county_svg`, `importer.parse_assignments`
  - `params.Categories`, `render.Frames/to_png`, `scenes.REGISTRY`, `assets.ROOT`
  - `engine.cli` olay biçimi
- Produces:
  - `jobs.BusyError`.
  - `jobs.Job`: alanları `.id`, `.state` ("running" | "done" | "failed" | "canceled"), `.finished` (threading.Event); metodu `.to_dict(out_root)`.
  - `jobs.JobManager(root, command=None)`: metotları `.start(project, out_dir) -> Job`, `.get(id)`, `.cancel(id)`.
  - `to_dict` alanları: `id, state, phase, scene, scenes, frame, total, percent, outputs (out/ altına göre, "/" ayraçlı), dir, error, log`.
  - `server.app` (FastAPI) ve `server.OUT`. Uçlar tasarım belgesinin 11. bölümündeki gibi. Hatalar `{"detail": {"message": str, "errors"?: ...}}` biçiminde döner.
  - `run_ui.py [--port N] [--no-browser]`.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_jobs.py`:
```python
import sys
import textwrap
import time

import pytest

from app.jobs import BusyError, JobManager

FAKE = textwrap.dedent('''
    import json, os, sys, time
    out = sys.argv[sys.argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    for f in (1, 2):
        print(json.dumps({"event": "progress", "scene": 0, "scenes": 1, "frame": f, "total": 2}), flush=True)
    if os.environ.get("FAKE_SLEEP"):
        time.sleep(30)
    if os.environ.get("FAKE_FAIL"):
        print(json.dumps({"event": "error", "message": "bozuldu"}), flush=True)
        sys.exit(1)
    path = os.path.join(out, "01_dummy.mp4")
    open(path, "wb").write(b"x")
    print("düz log satırı", flush=True)
    print(json.dumps({"event": "output", "path": path}), flush=True)
    print(json.dumps({"event": "done"}), flush=True)
''')
PROJECT = {"name": "t", "scenes": [{"type": "dummy", "enabled": True, "params": {}}]}


@pytest.fixture
def manager(tmp_path):
    script = tmp_path / "fake_cli.py"
    script.write_text(FAKE, encoding="utf-8")
    return JobManager(str(tmp_path), command=[sys.executable, str(script)])


def test_job_done(manager, tmp_path):
    job = manager.start(PROJECT, str(tmp_path / "out" / "t" / "1"))
    assert job.finished.wait(15)
    assert job.state == "done"
    d = job.to_dict(str(tmp_path / "out"))
    assert d["outputs"] == ["t/1/01_dummy.mp4"] and d["dir"] == "t/1" and d["percent"] == 100
    assert "düz log satırı" in d["log"]


def test_job_failed(manager, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_FAIL", "1")
    job = manager.start(PROJECT, str(tmp_path / "o"))
    assert job.finished.wait(15)
    assert job.state == "failed" and job.error == "bozuldu"


def test_busy_and_cancel(manager, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_SLEEP", "1")
    out = tmp_path / "o"
    job = manager.start(PROJECT, str(out))
    with pytest.raises(BusyError):
        manager.start(PROJECT, str(tmp_path / "o2"))
    deadline = time.time() + 10
    while job.frame < 2 and time.time() < deadline:
        time.sleep(0.05)
    assert job.state == "running" and job.to_dict(str(tmp_path))["percent"] == 100
    manager.cancel(job.id)
    assert job.finished.wait(15)
    assert job.state == "canceled" and not out.exists()
```

`tests/test_server.py`:
```python
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
    assert [s["id"] for s in client.get("/api/scenes").json()] == ["state_map", "price_ladder"]
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
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `.venv\Scripts\python -m pytest tests/test_jobs.py tests/test_server.py -v`
Expected: FAIL. `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: `app/jobs.py` dosyasını yaz**

```python
"""Render işlerini ayrı süreçte (engine.cli) çalıştırır ve ilerlemeyi izler."""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid


class BusyError(RuntimeError):
    pass


class Job:
    def __init__(self, job_id, out_dir, scenes):
        self.id = job_id
        self.out_dir = out_dir
        self.state = "running"
        self.phase = "render"
        self.scene, self.scenes, self.frame, self.total = 0, scenes, 0, 0
        self.outputs = []
        self.error = None
        self.log = collections.deque(maxlen=20)
        self.proc = None
        self.finished = threading.Event()

    def percent(self):
        if self.state == "done":
            return 100
        if self.phase == "compose":
            return 99
        if not self.total:
            return 0
        return int(100 * (self.scene + self.frame / self.total) / max(self.scenes, 1))

    def to_dict(self, out_root):
        def rel(p):
            return os.path.relpath(p, out_root).replace(os.sep, "/")

        return {"id": self.id, "state": self.state, "phase": self.phase, "scene": self.scene, "scenes": self.scenes,
                "frame": self.frame, "total": self.total, "percent": self.percent(),
                "outputs": [rel(p) for p in self.outputs], "dir": rel(self.out_dir),
                "error": self.error, "log": list(self.log)}


class JobManager:
    def __init__(self, root, command=None):
        self.root = root
        self.command = command or [sys.executable, "-m", "engine.cli", "render"]
        self.jobs = {}
        self.lock = threading.Lock()

    def start(self, project, out_dir):
        with self.lock:
            if any(j.state == "running" for j in self.jobs.values()):
                raise BusyError("Zaten süren bir render var. Bitmesini bekleyin ya da iptal edin.")
            job = Job(uuid.uuid4().hex[:8], out_dir, sum(1 for s in project["scenes"] if s.get("enabled", True)))
            fd, tmp = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(project, f, ensure_ascii=False)
            job.proc = subprocess.Popen(
                [*self.command, tmp, "--out", out_dir, "--progress-json"], cwd=self.root,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONUTF8": "1"}, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.jobs[job.id] = job
            threading.Thread(target=self._watch, args=(job, tmp), daemon=True).start()
            return job

    def _watch(self, job, tmp):
        for line in job.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                job.log.append(line)
                continue
            kind = ev.get("event")
            if kind == "progress":
                job.phase = "render"
                job.scene, job.scenes, job.frame, job.total = ev["scene"], ev["scenes"], ev["frame"], ev["total"]
            elif kind == "compose":
                job.phase = "compose"
            elif kind == "output":
                job.outputs.append(ev["path"])
            elif kind == "error":
                job.error = ev["message"]
            elif kind == "log":
                job.log.append(ev["message"])
        rc = job.proc.wait()
        try:
            os.remove(tmp)
        except OSError:
            pass
        if job.state == "canceled":
            for _ in range(10):
                shutil.rmtree(job.out_dir, ignore_errors=True)
                if not os.path.exists(job.out_dir):
                    break
                time.sleep(0.3)
        elif rc == 0 and not job.error:
            job.state = "done"
        else:
            job.state = "failed"
            job.error = job.error or f"Render süreci {rc} koduyla bitti."
        job.finished.set()

    def get(self, job_id):
        return self.jobs.get(job_id)

    def cancel(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.state == "running":
            job.state = "canceled"
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(job.proc.pid)], capture_output=True)
            else:
                job.proc.kill()
        return job
```

- [ ] **Step 4: Geçici arayüz sayfasını yaz** — `app/static/index.html`

```html
<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Harita Stüdyosu</title></head>
<body><h1>Harita Stüdyosu</h1><p>Arayüz hazırlanıyor.</p></body></html>
```

- [ ] **Step 5: `app/server.py` dosyasını yaz**

```python
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
```

- [ ] **Step 6: `run_ui.py` dosyasını yaz**

```python
"""Harita Stüdyosu'nu başlatır: veriyi hazırlar, boş port bulur, sunucuyu açar, tarayıcıyı açar.
Kullanım: .venv\\Scripts\\python run_ui.py [--port 8765] [--no-browser]"""
import argparse
import os
import socket
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def free_port(start=8765, tries=20):
    for port in range(start, start + tries):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"Boş port bulunamadı ({start}–{start + tries - 1}). Açık kalan Harita Stüdyosu pencerelerini kapatın.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    from engine import assets

    try:
        assets.ensure()
    except assets.AssetError as e:
        print("HATA:", e)
        return 1
    port = args.port or free_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"Harita Stüdyosu açılıyor: {url}")
    print("Kapatmak için bu pencerede Ctrl+C'ye basın ya da pencereyi kapatın.")
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    import uvicorn

    uvicorn.run("app.server:app", host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Testlerin geçtiğini gör**

Run: `.venv\Scripts\python -m pytest tests/test_jobs.py tests/test_server.py -v`
Expected: 12 passed, 1 deselected.

Run: `.venv\Scripts\python -m pytest tests/test_server.py -m slow -v`
Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add app run_ui.py tests/test_jobs.py tests/test_server.py
git commit -m "Web sunucusu, render işi yöneticisi ve başlatıcı"
```

---

### Task 14: Arayüz (`app/static/`)

**Files:**
- Create/Replace: `app/static/index.html`, `app/static/style.css`, `app/static/js/dom.js`, `app/static/js/api.js`, `app/static/js/state.js`, `app/static/js/form.js`, `app/static/js/pricetable.js`, `app/static/js/preview.js`, `app/static/js/countymap.js`, `app/static/js/render.js`, `app/static/js/main.js`, `.claude/launch.json`
- Test: `tests/test_server.py` (statik dosya testi eklenir) + tarayıcı panelinde elle doğrulama

**Interfaces:**
- Consumes: Görev 13'teki API uçları ve JSON biçimleri.
- Produces: `window.studio = { store }` (yalnızca hata ayıklama ve doğrulama için).

- [ ] **Step 1: Statik dosya testini ekle** — `tests/test_server.py` sonuna

```python


def test_static_assets(client):
    html = client.get("/").text
    assert '<script type="module" src="/static/js/main.js">' in html
    for f in ("style.css", "js/main.js", "js/api.js", "js/state.js", "js/form.js", "js/preview.js",
              "js/countymap.js", "js/render.js", "js/pricetable.js", "js/dom.js"):
        assert client.get(f"/static/{f}").status_code == 200, f
```

Run: `.venv\Scripts\python -m pytest tests/test_server.py::test_static_assets -v`
Expected: FAIL (geçici `index.html` script içermiyor).

- [ ] **Step 2: `app/static/index.html`**

```html
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harita Stüdyosu</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="topbar">
  <span class="brand">Harita Stüdyosu</span>
  <span id="project-name" class="muted"></span>
  <span id="dirty" class="dirty" hidden>● kaydedilmedi</span>
  <span class="spacer"></span>
  <button id="btn-new">Yeni</button>
  <select id="open-select" aria-label="Proje aç"></select>
  <button id="btn-save">Kaydet</button>
</header>
<main class="layout">
  <aside>
    <section class="panel">
      <h2>Sahneler</h2>
      <ul id="scene-list" class="scene-list"></ul>
      <div class="add-scene">
        <select id="add-scene-type" aria-label="Eklenecek sahne tipi"></select>
        <button id="btn-add-scene">Sahne ekle</button>
      </div>
    </section>
    <section class="panel">
      <h2 id="form-title">Ayarlar</h2>
      <div id="form"></div>
    </section>
  </aside>
  <section>
    <div id="preview-wrap" class="preview-wrap">
      <img id="preview-img" alt="Önizleme karesi">
      <div id="preview-status" class="overlay"></div>
    </div>
    <div class="timebar">
      <span id="t-label">0,0 sn</span>
      <input type="range" id="t-slider" min="0" max="13" step="0.1" value="0" aria-label="Önizleme zamanı">
      <span id="t-max"></span>
    </div>
    <section id="county-panel" class="panel" hidden>
      <h2>County boyama</h2>
      <div id="county-map"></div>
    </section>
    <section class="panel">
      <h2>Render</h2>
      <div id="render"></div>
    </section>
  </section>
</main>
<noscript>Harita Stüdyosu için JavaScript gerekli.</noscript>
<script type="module" src="/static/js/main.js"></script>
</body>
</html>
```

- [ ] **Step 3: `app/static/style.css`**

```css
:root {
  --bg: #0a1220; --panel: #101a2d; --field: #0d1627; --line: #1f2d45;
  --text: #dbe6f5; --muted: #8fb0d8; --accent: #3ee6ff; --danger: #ff5a4f; --warn: #ffb020;
  --radius: 8px;
  font-family: "Segoe UI", system-ui, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-size: 14px; }
button, select, input, textarea {
  font: inherit; color: var(--text); background: var(--field);
  border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px;
}
button { cursor: pointer; }
button:hover:not(:disabled) { border-color: var(--accent); }
button:disabled { opacity: .5; cursor: default; }
button.primary { background: var(--accent); color: #04222b; border-color: var(--accent); font-weight: 600; }
input[type=color] { padding: 0; width: 36px; height: 30px; }
input[type=checkbox], input[type=radio] { accent-color: var(--accent); }
.topbar {
  display: flex; align-items: center; gap: 10px; padding: 10px 16px;
  border-bottom: 1px solid var(--line); background: var(--panel); position: sticky; top: 0; z-index: 5;
}
.brand { font-weight: 700; letter-spacing: .5px; }
.muted { color: var(--muted); }
.spacer { flex: 1; }
.dirty { color: var(--warn); font-size: 12px; }
.layout { display: grid; grid-template-columns: 380px minmax(0, 1fr); gap: 16px; padding: 16px; align-items: start; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px 14px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); font-weight: 600; }
.scene-list { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.scene-item { display: flex; align-items: center; gap: 6px; padding: 8px; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
.scene-item.selected { border-color: var(--accent); }
.scene-item .title { flex: 1; }
.scene-item .dur { color: var(--muted); font-size: 12px; }
.err-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); }
.icon-btn { padding: 2px 7px; font-size: 12px; }
.add-scene { display: flex; gap: 8px; }
.add-scene select { flex: 1; }
details.group { border-top: 1px solid var(--line); padding: 8px 0; }
details.group > summary { cursor: pointer; color: var(--muted); font-weight: 600; }
.field { display: flex; flex-direction: column; gap: 4px; margin: 8px 0; }
.field label { font-size: 12px; color: var(--muted); }
.field .help { font-size: 11px; color: var(--muted); }
.field .err { font-size: 12px; color: var(--danger); }
.field .err:empty { display: none; }
.field input[type=text], .field input[type=number], .field input[type=date], .field select, .field textarea { width: 100%; }
.cat-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.cat-row input[type=text] { flex: 1; }
table.prices { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
table.prices th { text-align: left; font-size: 11px; color: var(--muted); font-weight: 600; }
table.prices td { padding: 2px; }
table.prices input { width: 100%; }
.preview-wrap { position: relative; aspect-ratio: 16 / 9; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--line); background: #070d18; }
.preview-wrap.checker { background: repeating-conic-gradient(#1a2233 0% 25%, #111827 0% 50%) 50% / 24px 24px; }
.preview-wrap img { width: 100%; height: 100%; display: block; object-fit: contain; }
.overlay { position: absolute; left: 10px; bottom: 10px; padding: 4px 8px; border-radius: 6px; background: rgba(7, 13, 24, .85); font-size: 12px; color: var(--muted); max-width: calc(100% - 20px); }
.overlay:empty { display: none; }
.overlay.error { color: var(--danger); }
.timebar { display: flex; align-items: center; gap: 10px; margin: 10px 0 16px; }
.timebar input { flex: 1; accent-color: var(--accent); }
.map-toolbar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }
.brush { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; font-size: 12px; user-select: none; }
.brush.active { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent) inset; }
.swatch { width: 14px; height: 14px; border-radius: 3px; display: inline-block; border: 1px solid var(--line); }
.county-map svg { width: 100%; height: auto; max-height: 560px; display: block; user-select: none; touch-action: none; }
.county-map path { stroke: #070d18; stroke-width: .8; cursor: crosshair; }
.county-map path:hover { stroke: var(--accent); stroke-width: 2; }
.map-info { font-size: 12px; color: var(--muted); min-height: 18px; margin-top: 6px; }
.import-result { font-size: 12px; margin-top: 6px; }
.import-result li { color: var(--warn); }
.render-opts { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-bottom: 10px; }
.progress { display: flex; align-items: center; gap: 10px; }
.bar { flex: 1; height: 8px; background: var(--field); border-radius: 4px; overflow: hidden; }
.bar > div { height: 100%; width: 0; background: var(--accent); transition: width .3s; }
.outputs { list-style: none; padding: 0; margin: 10px 0 0; }
.outputs li { margin-bottom: 12px; }
.outputs video { width: 100%; max-width: 640px; display: block; margin-top: 6px; border-radius: 6px; }
.errors-box { color: var(--danger); font-size: 13px; margin-top: 8px; white-space: pre-line; }
@media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: `app/static/js/dom.js` ve `app/static/js/api.js`**

`dom.js`:
```js
// Küçük DOM yardımcısı: h("div", {class: "x", onclick: fn}, çocuklar...)
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k in el) el[k] = v;
    else el.setAttribute(k, v);
  }
  for (const c of children) if (c != null) el.append(c);
  return el;
}
```

`api.js`:
```js
// Sunucu API'si için fetch sarmalayıcıları. Hatalar Error(message) olarak fırlatılır.
export function apiError(status, data) {
  const d = data && data.detail;
  let msg = typeof d === "string" ? d : (d && d.message) || `İstek başarısız oldu (${status}).`;
  if (d && d.errors && !Array.isArray(d.errors)) {
    msg += " " + Object.entries(d.errors).map(([k, v]) => `${k}: ${v}`).join(", ");
  }
  const err = new Error(msg);
  err.status = status;
  err.data = data;
  return err;
}

async function request(method, url, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(url, opts);
  const isJson = (r.headers.get("content-type") || "").includes("json");
  const data = isJson ? await r.json() : await r.blob();
  if (!r.ok) throw apiError(r.status, data);
  return data;
}

const enc = encodeURIComponent;
export const api = {
  scenes: () => request("GET", "/api/scenes"),
  states: () => request("GET", "/api/states"),
  geo: abbr => request("GET", `/api/geo/${enc(abbr)}`),
  projects: () => request("GET", "/api/projects"),
  newProject: () => request("GET", "/api/projects/_new"),
  loadProject: name => request("GET", `/api/projects/${enc(name)}`),
  saveProject: (name, project) => request("PUT", `/api/projects/${enc(name)}`, project),
  validate: project => request("POST", "/api/validate", project),
  importAssignments: body => request("POST", "/api/import-assignments", body),
  render: project => request("POST", "/api/render", { project }),
  job: id => request("GET", `/api/jobs/${enc(id)}`),
  cancel: id => request("POST", `/api/jobs/${enc(id)}/cancel`),
  openFolder: path => request("POST", "/api/open-folder", { path }),
};

export async function previewBlob(body, signal) {
  const r = await fetch("/api/preview", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  });
  if (!r.ok) {
    let data = null;
    try { data = await r.json(); } catch { data = null; }
    throw apiError(r.status, data);
  }
  return r.blob();
}
```

- [ ] **Step 5: `app/static/js/state.js`**

```js
// Uygulama durumu: açık proje, seçili sahne, hatalar ve değişiklik bildirimi.
import { api } from "./api.js";

export const store = { project: null, schemas: {}, states: [], selected: 0, dirty: false, errors: [], geo: {} };
const listeners = new Set();

export function on(fn) { listeners.add(fn); }
export function emit(reason) { for (const fn of listeners) fn(reason); }

export function setProject(p) {
  store.project = p;
  store.selected = 0;
  store.dirty = false;
  store.errors = [];
  emit("project");
}
export function currentScene() { return store.project ? store.project.scenes[store.selected] ?? null : null; }
export function currentSchema() { const s = currentScene(); return s ? store.schemas[s.type] : null; }
export function setParam(name, value, reason = "param") {
  currentScene().params[name] = value;
  store.dirty = true;
  emit(reason);
}
export function touch(reason) { store.dirty = true; emit(reason); }
export function selectScene(i) { store.selected = i; emit("select"); }
export function sceneErrors(i) { return store.errors.filter(e => e.scene === i); }
export async function geoFor(abbr) {
  if (!store.geo[abbr]) store.geo[abbr] = await api.geo(abbr);
  return store.geo[abbr];
}
export function defaultsFor(type) {
  return Object.fromEntries(store.schemas[type].params.map(p => [p.name, structuredClone(p.default)]));
}
```

- [ ] **Step 6: `app/static/js/pricetable.js`**

```js
// Fiyat geçmişi tablosu: tarih + fiyat satırları, ekle/sil.
import { h } from "./dom.js";

export function priceTable(rows, onChange) {
  const box = h("div");
  const data = structuredClone(rows || []);
  const commit = () => onChange(structuredClone(data));
  const draw = () => {
    box.innerHTML = "";
    const body = h("tbody");
    data.forEach((r, i) => {
      body.append(h("tr", {},
        h("td", {}, h("input", { type: "date", value: r.date, onchange: e => { r.date = e.target.value; commit(); } })),
        h("td", {}, h("input", { type: "number", min: 1, step: 1, value: r.price ?? "",
          oninput: e => { r.price = e.target.value === "" ? null : Number(e.target.value); commit(); } })),
        h("td", {}, h("button", { class: "icon-btn", title: "Satırı sil", onclick: () => { data.splice(i, 1); draw(); commit(); } }, "✕")),
      ));
    });
    box.append(h("table", { class: "prices" },
      h("thead", {}, h("tr", {}, h("th", {}, "Tarih"), h("th", {}, "Fiyat ($)"), h("th"))), body));
    box.append(h("button", { onclick: () => {
      const last = data[data.length - 1];
      const next = last ? new Date(Date.parse(last.date) + 30 * 864e5) : new Date();
      data.push({ date: next.toISOString().slice(0, 10), price: last ? last.price : 100000 });
      draw();
      commit();
    } }, "Satır ekle"));
  };
  draw();
  return box;
}
```

- [ ] **Step 7: `app/static/js/form.js`**

```js
// Seçili sahnenin ayar formu: sahne şemasından otomatik kurulur.
import { h } from "./dom.js";
import { priceTable } from "./pricetable.js";
import { currentScene, currentSchema, geoFor, sceneErrors, setParam, store } from "./state.js";

const GROUP_ORDER = ["Genel", "Veri", "Renkler", "County boyama", "Vurgu", "Kamera", "Zaman"];
const CLOSED = new Set(["Kamera"]);
let token = 0;

export function assignText(value) {
  return `${Object.keys(value || {}).length} county boyandı. Düzenlemek için sağdaki "County boyama" panelini kullanın.`;
}

export async function renderForm(root) {
  const my = ++token;
  const scene = currentScene(), schema = currentSchema();
  document.getElementById("form-title").textContent = schema ? `Ayarlar · ${schema.title}` : "Ayarlar";
  if (!scene) { root.innerHTML = ""; return; }
  const groups = new Map();
  for (const p of schema.params) {
    if (!groups.has(p.group)) groups.set(p.group, []);
    groups.get(p.group).push(p);
  }
  const rank = g => (GROUP_ORDER.indexOf(g) + 1) || 99;
  const frag = document.createDocumentFragment();
  for (const g of [...groups.keys()].sort((a, b) => rank(a) - rank(b))) {
    const det = h("details", { class: "group", open: !CLOSED.has(g) }, h("summary", {}, g));
    for (const p of groups.get(g)) det.append(await field(p, scene));
    frag.append(det);
  }
  if (my !== token) return; // bu arada yeni bir çizim başladı
  root.innerHTML = "";
  root.append(frag);
  showErrors();
}

export function showErrors() {
  const errs = sceneErrors(store.selected);
  for (const el of document.querySelectorAll("#form .field")) {
    const e = errs.find(x => x.param === el.dataset.param);
    el.querySelector(".err").textContent = e ? e.message : "";
  }
}

async function field(p, scene) {
  const id = `f-${p.name}`;
  return h("div", { class: "field", dataset: { param: p.name } },
    h("label", { htmlFor: id }, p.label),
    await control(p, scene.params[p.name], scene, id),
    p.help ? h("div", { class: "help" }, p.help) : null,
    h("div", { class: "err" }));
}

async function control(p, value, scene, id) {
  const set = v => setParam(p.name, v);
  switch (p.kind) {
    case "text":
      return p.multiline
        ? h("textarea", { id, rows: 2, value: value ?? "", placeholder: p.auto ? "otomatik" : "", oninput: e => set(e.target.value) })
        : h("input", { type: "text", id, value: value ?? "", maxLength: p.max_len, placeholder: p.auto ? "otomatik" : "",
            oninput: e => set(e.target.value) });
    case "color":
      return h("input", { type: "color", id, value, oninput: e => set(e.target.value) });
    case "number": {
      const el = h("input", { type: "number", id, step: p.step ?? "any", value: value ?? "",
        oninput: e => set(e.target.value === "" ? (p.optional ? null : "") : Number(e.target.value)) });
      if (p.min != null) el.min = p.min;
      if (p.max != null) el.max = p.max;
      return el;
    }
    case "date":
      return h("input", { type: "date", id, value, onchange: e => set(e.target.value) });
    case "state":
      return stateSelect(p, value, id);
    case "county":
      return countySelect(p, value, scene, id);
    case "categories":
      return categoriesEditor(p, value);
    case "county_assign":
      return h("div", { class: "help", id, dataset: { assignSummary: p.name } }, assignText(value));
    case "price_table":
      return priceTable(value, rows => set(rows));
    default:
      return h("div", { class: "err" }, `Desteklenmeyen ayar tipi: ${p.kind}`);
  }
}

function stateSelect(p, value, id) {
  const sel = h("select", { id });
  for (const o of p.options) sel.add(new Option(o.label, o.value, false, o.value === value));
  sel.addEventListener("change", () => {
    const s = currentScene(), sch = currentSchema();
    const deps = sch.params.filter(q => (q.kind === "county" || q.kind === "county_assign") && q.state_param === p.name);
    const hasData = deps.some(q => q.kind === "county" ? s.params[q.name] : Object.keys(s.params[q.name] || {}).length);
    if (hasData && !confirm("Eyalet değişince county boyamaları ve vurgu temizlenecek. Devam edilsin mi?")) {
      sel.value = s.params[p.name];
      return;
    }
    const oldName = (p.options.find(o => o.value === s.params[p.name]) || {}).label?.toUpperCase();
    for (const q of sch.params) if (q.kind === "text" && q.auto && s.params[q.name] === oldName) s.params[q.name] = "";
    for (const q of deps) s.params[q.name] = q.kind === "county" ? null : {};
    for (const q of sch.params) if (q.kind === "text" && q.auto && deps.some(d => d.kind === "county" && d.group === q.group)) s.params[q.name] = "";
    setParam(p.name, sel.value, "structure");
  });
  return sel;
}

async function countySelect(p, value, scene, id) {
  const sel = h("select", { id });
  if (p.allow_none) sel.add(new Option("— yok —", ""));
  const geo = await geoFor(scene.params[p.state_param]);
  for (const c of [...geo.counties].sort((a, b) => a.name.localeCompare(b.name, "en"))) sel.add(new Option(c.name, c.fips));
  sel.value = value || "";
  sel.addEventListener("change", () => {
    const s = currentScene();
    // Vurgu değişince aynı gruptaki otomatik yazılar (ör. vurgu adı) otomatiğe döner.
    for (const q of currentSchema().params) if (q.kind === "text" && q.auto && q.group === p.group) s.params[q.name] = "";
    setParam(p.name, sel.value || null, "structure");
  });
  return sel;
}

function categoriesEditor(p, value) {
  const box = h("div");
  const cats = structuredClone(value);
  const commit = () => setParam(p.name, structuredClone(cats), "categories");
  const draw = () => {
    box.innerHTML = "";
    cats.forEach((c, i) => {
      const row = h("div", { class: "cat-row" },
        h("input", { type: "color", value: c.color, title: "Renk", oninput: e => { c.color = e.target.value; commit(); } }),
        h("input", { type: "text", value: c.label, maxLength: 40, oninput: e => { c.label = e.target.value; commit(); } }));
      if (c.key !== "none") {
        row.append(h("button", { class: "icon-btn", title: "Kategoriyi sil", onclick: () => {
          if (cats.length <= p.min_count) { alert(`En az ${p.min_count} kategori olmalı.`); return; }
          const s = currentScene();
          const ap = currentSchema().params.find(q => q.kind === "county_assign" && q.categories_param === p.name);
          if (ap) for (const [f, k] of Object.entries(s.params[ap.name])) if (k === c.key) delete s.params[ap.name][f];
          cats.splice(i, 1);
          draw();
          commit();
        } }, "✕"));
      }
      box.append(row);
    });
    box.append(h("button", { onclick: () => {
      if (cats.length >= p.max_count) { alert(`En fazla ${p.max_count} kategori olabilir.`); return; }
      let n = 1;
      while (cats.some(c => c.key === `k${n}`)) n++;
      cats.splice(cats.length - 1, 0, { key: `k${n}`, label: "NEW CATEGORY", color: "#8fb0d8" });
      draw();
      commit();
    } }, "Kategori ekle"));
  };
  draw();
  return box;
}
```

- [ ] **Step 8: `app/static/js/preview.js`**

```js
// Tek kare önizleme: ayar değişince gecikmeli, kaydırma çubuğunda hızlı istek; eski istek iptal edilir.
import { previewBlob } from "./api.js";
import { currentScene, store } from "./state.js";

const $ = id => document.getElementById(id);
let timer = null, ctrl = null, lastUrl = null;

export function fmtSec(v) { return `${Number(v).toFixed(1).replace(".", ",")} sn`; }

function setStatus(text, error = false) {
  $("preview-status").textContent = text;
  $("preview-status").classList.toggle("error", error);
}

export function syncSlider() {
  const s = currentScene();
  if (!s) return;
  const dur = Number(s.params.duration) || 1;
  const sl = $("t-slider");
  sl.max = dur;
  if (Number(sl.value) > dur) sl.value = dur;
  $("t-max").textContent = fmtSec(dur);
  $("t-label").textContent = fmtSec(sl.value);
  $("preview-wrap").classList.toggle("checker", !!store.project.output.transparent);
}

export function schedulePreview(delay = 500) {
  clearTimeout(timer);
  timer = setTimeout(run, delay);
}

async function run() {
  const s = currentScene();
  if (!s) return;
  if (ctrl) ctrl.abort();
  ctrl = new AbortController();
  setStatus("Önizleme hazırlanıyor…");
  try {
    const blob = await previewBlob({ type: s.type, params: s.params, t: Number($("t-slider").value),
      transparent: !!store.project.output.transparent }, ctrl.signal);
    if (lastUrl) URL.revokeObjectURL(lastUrl);
    lastUrl = URL.createObjectURL(blob);
    $("preview-img").src = lastUrl;
    setStatus("");
  } catch (e) {
    if (e.name !== "AbortError") setStatus(e.message, true);
  }
}

export function initPreview() {
  $("t-slider").addEventListener("input", () => {
    $("t-label").textContent = fmtSec($("t-slider").value);
    schedulePreview(120);
  });
}
```

- [ ] **Step 9: `app/static/js/countymap.js`**

```js
// County boyama paneli: kategori fırçası, tıkla/sürükle ile boyama, CSV/Excel içe aktarma.
import { api } from "./api.js";
import { h } from "./dom.js";
import { currentScene, currentSchema, geoFor, touch } from "./state.js";

const NS = "http://www.w3.org/2000/svg";
let brush = null, painting = false, token = 0;
window.addEventListener("pointerup", () => { painting = false; });

export async function renderCountyPanel(panel, body) {
  const my = ++token;
  const schema = currentSchema(), scene = currentScene();
  const ap = schema && schema.params.find(p => p.kind === "county_assign");
  panel.hidden = !ap;
  if (!ap) { body.innerHTML = ""; return; }
  const abbr = scene.params[ap.state_param];
  const cats = scene.params[ap.categories_param];
  const assign = scene.params[ap.name];
  if (!cats.some(c => c.key === brush)) brush = cats[0].key;
  const color = Object.fromEntries(cats.map(c => [c.key, c.color]));
  const geo = await geoFor(abbr);
  if (my !== token) return;

  const info = h("div", { class: "map-info" }, "Bir renk seçin, sonra county'lere tıklayın ya da basılı tutup sürükleyin.");
  const result = h("div", { class: "import-result" });
  const paths = {};
  const repaint = () => { for (const [f, el] of Object.entries(paths)) el.setAttribute("fill", color[assign[f] || "none"]); };
  const changed = () => touch("assign");
  const paint = fips => {
    if ((assign[fips] || "none") === brush) return;
    if (brush === "none") delete assign[fips]; else assign[fips] = brush;
    paths[fips].setAttribute("fill", color[brush]);
    changed();
  };

  const bar = h("div", { class: "map-toolbar" });
  for (const c of cats) {
    const b = h("span", { class: "brush" + (c.key === brush ? " active" : ""), title: "Fırça", onclick: () => {
      brush = c.key;
      bar.querySelectorAll(".brush").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
    } });
    const sw = h("span", { class: "swatch" });
    sw.style.background = c.color;
    b.append(sw, c.label);
    bar.append(b);
  }
  const file = h("input", { type: "file", accept: ".csv,.xlsx,.xlsm", hidden: true, onchange: async () => {
    const f = file.files[0];
    file.value = "";
    if (f) await importFile(f);
  } });
  bar.append(h("span", { class: "spacer" }),
    h("button", { onclick: () => file.click() }, "CSV / Excel yükle"), file,
    h("button", { onclick: () => {
      if (!Object.keys(assign).length || !confirm("Tüm county boyamaları silinsin mi?")) return;
      for (const k of Object.keys(assign)) delete assign[k];
      repaint();
      changed();
    } }, "Temizle"));

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${geo.width} ${geo.height}`);
  for (const c of geo.counties) {
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", c.d);
    const title = document.createElementNS(NS, "title");
    title.textContent = c.name;
    path.append(title);
    path.addEventListener("pointerdown", e => { e.preventDefault(); painting = true; paint(c.fips); });
    path.addEventListener("pointerenter", () => {
      const k = assign[c.fips] || "none";
      info.textContent = `${c.name} · ${(cats.find(x => x.key === k) || {}).label || ""}`;
      if (painting) paint(c.fips);
    });
    paths[c.fips] = path;
    svg.append(path);
  }

  async function importFile(f) {
    result.textContent = "Dosya okunuyor…";
    try {
      const buf = new Uint8Array(await f.arrayBuffer());
      let bin = "";
      for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
      const res = await api.importAssignments({ state: abbr, categories: cats, filename: f.name, content_b64: btoa(bin) });
      for (const [fips, key] of Object.entries(res.assign)) {
        if (key === "none") delete assign[fips]; else assign[fips] = key;
      }
      repaint();
      changed();
      result.innerHTML = "";
      result.append(h("div", {}, `${Object.keys(res.assign).length} county atandı.`));
      if (res.unmatched.length || res.ambiguous.length) {
        const ul = h("ul");
        for (const u of res.unmatched) ul.append(h("li", {}, `Satır ${u.row}: "${u.county}" (${u.category}): ${u.reason}`));
        for (const a of res.ambiguous) {
          ul.append(h("li", {}, `Satır ${a.row}: "${a.county}" birden fazla county'ye uyuyor (${a.candidates.join(", ")}). Tam adı yazın.`));
        }
        result.append(ul);
      }
    } catch (e) {
      result.textContent = e.message;
    }
  }

  body.innerHTML = "";
  body.append(bar, h("div", { class: "county-map" }, svg), info, result);
  repaint();
}
```

- [ ] **Step 10: `app/static/js/render.js`**

```js
// Render paneli: çıktı seçenekleri, başlatma, ilerleme, iptal, biten dosyalar.
import { api } from "./api.js";
import { h } from "./dom.js";
import { schedulePreview, syncSlider } from "./preview.js";
import { emit, store, touch } from "./state.js";

let jobId = null, root = null;
const $ = id => root.querySelector("#" + id);

export function renderRenderPanel(el) {
  root = el;
  const o = store.project.output;
  root.innerHTML = `
    <div class="render-opts">
      <label><input type="checkbox" id="o-separate"> Her sahne ayrı dosya</label>
      <label><input type="checkbox" id="o-combined"> Birleşik video</label>
      <label><input type="radio" name="o-bg" id="o-opaque"> Koyu arka plan</label>
      <label><input type="radio" name="o-bg" id="o-transparent"> Şeffaf arka plan</label>
      <label>Geçiş <input type="number" id="o-transition" min="0" max="2" step="0.1" style="width:70px"> sn</label>
    </div>
    <div class="progress">
      <button class="primary" id="btn-render">Render al</button>
      <button id="btn-cancel" hidden>İptal</button>
      <div class="bar"><div id="bar-fill"></div></div>
      <span id="render-status" class="muted"></span>
    </div>
    <div id="render-errors" class="errors-box"></div>
    <ul id="outputs" class="outputs"></ul>`;
  $("o-separate").checked = o.separate;
  $("o-combined").checked = o.combined;
  $("o-opaque").checked = !o.transparent;
  $("o-transparent").checked = o.transparent;
  $("o-transition").value = store.project.transition;
  $("o-separate").addEventListener("change", e => { o.separate = e.target.checked; touch("output"); });
  $("o-combined").addEventListener("change", e => { o.combined = e.target.checked; touch("output"); });
  for (const id of ["o-opaque", "o-transparent"]) {
    $(id).addEventListener("change", () => {
      o.transparent = $("o-transparent").checked;
      touch("output");
      syncSlider();
      schedulePreview(0);
    });
  }
  $("o-transition").addEventListener("input", e => {
    store.project.transition = e.target.value === "" ? 0 : Number(e.target.value);
    touch("output");
  });
  $("btn-render").addEventListener("click", start);
  $("btn-cancel").addEventListener("click", () => { if (jobId) api.cancel(jobId).catch(e => alert(e.message)); });
  if (jobId) { $("btn-render").disabled = true; $("btn-cancel").hidden = false; }
}

function describe(e) {
  const where = e.scene == null ? "Proje" : `${e.scene + 1}. sahne`;
  const sc = e.scene == null ? null : store.project.scenes[e.scene];
  const label = sc ? (store.schemas[sc.type].params.find(p => p.name === e.param) || {}).label || e.param : e.param;
  return `• ${where}${label ? " · " + label : ""}: ${e.message}`;
}

async function start() {
  $("render-errors").textContent = "";
  try {
    const { errors } = await api.validate(store.project);
    store.errors = errors;
    emit("errors");
    if (errors.length) {
      $("render-errors").textContent = "Render başlamadı. Önce şu hataları düzeltin:\n" + errors.map(describe).join("\n");
      return;
    }
    jobId = (await api.render(store.project)).job_id;
  } catch (e) {
    $("render-errors").textContent = e.message;
    return;
  }
  $("btn-render").disabled = true;
  $("btn-cancel").hidden = false;
  $("outputs").innerHTML = "";
  poll();
}

async function poll() {
  let j;
  try {
    j = await api.job(jobId);
  } catch (e) {
    $("render-status").textContent = e.message;
    finish();
    return;
  }
  $("bar-fill").style.width = `${j.percent}%`;
  if (j.state === "running") {
    $("render-status").textContent = j.phase === "compose"
      ? "Sahneler birleştiriliyor…" : `Sahne ${j.scene + 1}/${j.scenes} · %${j.percent}`;
    setTimeout(poll, 700);
    return;
  }
  if (j.state === "done") {
    $("render-status").textContent = "Tamamlandı";
    showOutputs(j);
  } else if (j.state === "canceled") {
    $("render-status").textContent = "İptal edildi";
    $("bar-fill").style.width = "0";
  } else {
    $("render-status").textContent = "Başarısız";
    $("render-errors").textContent = [j.error, ...(j.log || [])].filter(Boolean).join("\n");
  }
  finish();
}

function finish() {
  jobId = null;
  $("btn-render").disabled = false;
  $("btn-cancel").hidden = true;
}

function showOutputs(j) {
  const ul = $("outputs");
  ul.innerHTML = "";
  for (const rel of j.outputs) {
    const li = h("li", {}, h("div", {}, rel.split("/").pop()));
    if (rel.endsWith(".mp4")) {
      li.append(h("video", { controls: true, preload: "metadata", src: "/api/outputs/" + rel.split("/").map(encodeURIComponent).join("/") }));
    } else {
      li.append(h("div", { class: "muted" }, "Şeffaf .mov dosyası tarayıcıda oynatılamaz; kurgu programında açın."));
    }
    ul.append(li);
  }
  ul.append(h("li", {}, h("button", { onclick: () => api.openFolder(j.dir).catch(e => alert(e.message)) }, "Klasörü aç")));
}
```

- [ ] **Step 11: `app/static/js/main.js`**

```js
// Uygulamanın girişi: veriyi yükler, parçaları bağlar, olayları dağıtır.
import { api } from "./api.js";
import { h } from "./dom.js";
import { assignText, renderForm, showErrors } from "./form.js";
import { renderCountyPanel } from "./countymap.js";
import { initPreview, schedulePreview, syncSlider } from "./preview.js";
import { renderRenderPanel } from "./render.js";
import { currentScene, defaultsFor, emit, on, sceneErrors, selectScene, setProject, store, touch } from "./state.js";

const $ = id => document.getElementById(id);
let validateTimer = null;
window.studio = { store };

function fmtDur(v) { return `${Number(v).toFixed(1).replace(".", ",")} sn`; }

function renderSceneList() {
  const ul = $("scene-list");
  ul.innerHTML = "";
  store.project.scenes.forEach((s, i) => {
    const sch = store.schemas[s.type];
    const li = h("li", { class: "scene-item" + (i === store.selected ? " selected" : ""), onclick: () => selectScene(i) },
      h("input", { type: "checkbox", checked: s.enabled, title: "Render'a dahil et",
        onclick: e => e.stopPropagation(), onchange: e => { s.enabled = e.target.checked; touch("scenes"); } }),
      h("span", { class: "title" }, `${i + 1}. ${sch.title}`),
      sceneErrors(i).length ? h("span", { class: "err-dot", title: "Bu sahnede hatalı ayar var" }) : null,
      h("span", { class: "dur" }, fmtDur(s.params.duration)));
    for (const [label, tip, fn] of [["↑", "Yukarı taşı", () => move(i, -1)], ["↓", "Aşağı taşı", () => move(i, 1)],
      ["✕", "Sahneyi sil", () => remove(i)]]) {
      li.append(h("button", { class: "icon-btn", title: tip, onclick: e => { e.stopPropagation(); fn(); } }, label));
    }
    ul.append(li);
  });
}

function move(i, d) {
  const sc = store.project.scenes, j = i + d;
  if (j < 0 || j >= sc.length) return;
  [sc[i], sc[j]] = [sc[j], sc[i]];
  if (store.selected === i) store.selected = j;
  else if (store.selected === j) store.selected = i;
  touch("scenes");
}

function remove(i) {
  const sc = store.project.scenes;
  if (sc.length === 1) { alert("Projede en az bir sahne kalmalı."); return; }
  if (!confirm(`${i + 1}. sahne silinsin mi?`)) return;
  sc.splice(i, 1);
  store.selected = Math.min(store.selected, sc.length - 1);
  touch("select");
}

function updateHeader() {
  $("project-name").textContent = `· ${store.project.name}`;
  $("dirty").hidden = !store.dirty;
}

function updateAssignSummary() {
  const el = document.querySelector("[data-assign-summary]");
  if (el) el.textContent = assignText(currentScene().params[el.dataset.assignSummary]);
}

function validateSoon() {
  clearTimeout(validateTimer);
  validateTimer = setTimeout(async () => {
    try {
      store.errors = (await api.validate(store.project)).errors;
      emit("errors");
    } catch (e) {
      console.warn("Doğrulama yapılamadı:", e);
    }
  }, 600);
}

async function refreshProjectList() {
  const sel = $("open-select");
  const { projects } = await api.projects();
  sel.innerHTML = "";
  sel.add(new Option("Proje aç…", ""));
  for (const n of projects) sel.add(new Option(n, n));
  sel.value = "";
  return projects;
}

function confirmDiscard() {
  return !store.dirty || confirm("Kaydedilmemiş değişiklikler kaybolacak. Devam edilsin mi?");
}

async function openProject(name) {
  const { project, errors } = await api.loadProject(name);
  setProject(project);
  if (errors.length) {
    alert("Projedeki bazı ayarlar geçersizdi ve varsayılanlarla değiştirildi:\n" +
      errors.map(e => `• ${e.param}: ${e.message}`).join("\n"));
  }
}

async function redrawScene() {
  renderSceneList();
  syncSlider();
  await renderForm($("form"));
  await renderCountyPanel($("county-panel"), $("county-map"));
  schedulePreview(0);
  validateSoon();
}

on(async reason => {
  updateHeader();
  switch (reason) {
    case "project":
      $("t-slider").value = Math.min(8.6, Number(store.project.scenes[0]?.params.duration) || 0);
      renderRenderPanel($("render"));
      await redrawScene();
      break;
    case "select":
    case "structure":
      await redrawScene();
      break;
    case "param":
      renderSceneList();
      syncSlider();
      schedulePreview();
      validateSoon();
      break;
    case "categories":
      await renderCountyPanel($("county-panel"), $("county-map"));
      schedulePreview();
      validateSoon();
      break;
    case "assign":
      updateAssignSummary();
      schedulePreview();
      validateSoon();
      break;
    case "scenes":
      renderSceneList();
      validateSoon();
      break;
    case "output":
      validateSoon();
      break;
    case "errors":
      renderSceneList();
      showErrors();
      break;
  }
});

$("btn-new").addEventListener("click", async () => {
  if (!confirmDiscard()) return;
  try { setProject(await api.newProject()); } catch (e) { alert(e.message); }
});

$("open-select").addEventListener("change", async e => {
  const name = e.target.value;
  e.target.value = "";
  if (!name || !confirmDiscard()) return;
  try { await openProject(name); } catch (err) { alert(err.message); }
});

$("btn-save").addEventListener("click", async () => {
  const answer = prompt("Proje adı (harf, rakam, _ ve -):", store.project.name);
  if (answer === null) return;
  const name = answer.trim();
  if (!/^[A-Za-z0-9_-]{1,60}$/.test(name)) { alert("Ad yalnızca harf, rakam, _ ve - içerebilir."); return; }
  try {
    const exists = (await api.projects()).projects.includes(name);
    if (exists && name !== store.project.name && !confirm(`"${name}" adında bir proje var. Üzerine yazılsın mı?`)) return;
    store.project.name = name;
    const res = await api.saveProject(name, store.project);
    store.dirty = false;
    updateHeader();
    await refreshProjectList();
    if (res.errors.length) {
      store.errors = res.errors;
      emit("errors");
      alert("Proje kaydedildi, ancak bazı ayarlar hatalı. Render almadan önce düzeltin.");
    }
  } catch (e) {
    alert(e.message);
  }
});

$("btn-add-scene").addEventListener("click", () => {
  const type = $("add-scene-type").value;
  store.project.scenes.push({ type, enabled: true, params: defaultsFor(type) });
  store.selected = store.project.scenes.length - 1;
  touch("select");
});

window.addEventListener("beforeunload", e => {
  if (store.dirty) { e.preventDefault(); e.returnValue = ""; }
});

async function init() {
  try {
    const [schemas, states] = await Promise.all([api.scenes(), api.states()]);
    store.schemas = Object.fromEntries(schemas.map(s => [s.id, s]));
    store.states = states;
    for (const s of schemas) $("add-scene-type").add(new Option(s.title, s.id));
    initPreview();
    const projects = await refreshProjectList();
    if (projects.includes("ornek_florida")) await openProject("ornek_florida");
    else setProject(await api.newProject());
  } catch (e) {
    document.body.prepend(h("div", { class: "errors-box", style: "padding:12px" }, `Arayüz başlatılamadı: ${e.message}`));
  }
}

init();
```

- [ ] **Step 12: Statik testi çalıştır**

Run: `.venv\Scripts\python -m pytest tests/test_server.py -v`
Expected: tümü geçer (slow hariç).

- [ ] **Step 13: Tarayıcı panelinde doğrula**

`.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "harita-studyosu",
      "runtimeExecutable": ".venv/Scripts/python.exe",
      "runtimeArgs": ["run_ui.py", "--port", "8765", "--no-browser"],
      "port": 8765
    }
  ]
}
```

Doğrulama sırası:

1. `preview_start` ile `harita-studyosu` yapılandırmasını aç.
2. `read_console_messages` (onlyErrors) boş olmalı.
3. `get_page_text` içinde "1. Eyalet haritası", "2. Fiyat merdiveni", "Render al" geçmeli.
4. `javascript_tool` ile `document.getElementById("preview-img").naturalWidth` değeri 960 olmalı (gerekirse 2–3 sn bekle).
5. `javascript_tool` ile Texas'a geç:
   ```js
   window.confirm = () => true;
   const s = document.getElementById("f-state"); s.value = "TX"; s.dispatchEvent(new Event("change"));
   ```
   Birkaç saniye sonra şunlar sağlanmalı:
   - `document.querySelectorAll("#county-map path").length === 254`
   - `studio.store.project.scenes[0].params.assign` boş olmalı.
   - Önizleme görseli yenilenmiş olmalı.
6. Boyamayı dene:
   ```js
   const p = document.querySelector("#county-map path");
   p.dispatchEvent(new PointerEvent("pointerdown", {bubbles: true}));
   window.dispatchEvent(new PointerEvent("pointerup"));
   ```
   Sonra `Object.keys(studio.store.project.scenes[0].params.assign).length === 1` olmalı.
7. `computer` ile ekran görüntüsü al. Yerleşim onaylanan taslağa benzemeli: solda sahneler ve ayarlar, sağda önizleme, county haritası ve render paneli.
8. Hızlı render:
   ```js
   studio.store.project.scenes[0].enabled = false;
   studio.store.project.scenes[1].params.duration = 5.75;
   document.getElementById("btn-render").click();
   ```
   İş bitene kadar `#render-status` metnini takip et (en fazla 3 dk). Sonunda "Tamamlandı" yazmalı ve `#outputs video` elemanı bulunmalı.
9. Sorun bulunursa ilgili JS dosyasını düzelt, sayfayı yenile ve adımı tekrarla.

- [ ] **Step 14: Commit**

```bash
git add app/static .claude/launch.json tests/test_server.py
git commit -m "Arayüz: ayar paneli, önizleme, county boyama, render paneli"
```

---

### Task 15: Başlatıcılar, README ve eski dosyaların temizliği

**Files:**
- Create: `kurulum.bat`, `baslat.bat`, `.gitattributes`, `README.md`
- Delete: `CLAUDE_CODE_ANIM_TASK.md`, `scene_a.py`, `scene_b.py`, `scene_common.py`, `prep_data.py`, `render_all.py`, kökteki `state_outlines.json` (git dışı)
- Modify: `.gitignore`

- [ ] **Step 1: `.gitattributes`**

```
*.bat text eol=crlf
```

- [ ] **Step 2: `kurulum.bat`** (yalnızca ASCII karakterler)

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org adresinden Python 3.12 kurun, sonra bu dosyayi tekrar calistirin.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv || py -3 -m venv .venv
)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Paket kurulumu basarisiz oldu. Internet baglantinizi kontrol edin.
  pause
  exit /b 1
)
set PYTHONUTF8=1
.venv\Scripts\python -c "from engine import assets; assets.ensure()"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo Kurulum tamam. Baslatmak icin baslat.bat dosyasina cift tiklayin.
pause
```

- [ ] **Step 3: `baslat.bat`**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)
set PYTHONUTF8=1
.venv\Scripts\python run_ui.py
pause
```

Satır sonlarını CRLF yap:

Run: `powershell -Command "foreach ($f in 'kurulum.bat','baslat.bat') { (Get-Content $f) | Set-Content -Encoding ascii $f }"`

- [ ] **Step 4: `README.md`**

````markdown
# Harita Stüdyosu

ABD eyalet ve county haritaları için animasyonlu video üreten yerel bir araç. Ayarlar tarayıcıda açılan bir panelden yapılır, önizlenir ve tek tuşla videoya dönüştürülür.

- **Eyalet haritası:** ABD'den seçilen eyalete inen kamera, neon sınır çizimi, kategorilere göre boyanan county'ler ve isteğe bağlı olarak vurgulanan bir county.
- **Fiyat merdiveni:** bir evin fiyat geçmişi, indirim sayaçları ve alış fiyatıyla karşılaştırma.
- **Çıktı:** 1920x1080, 30 kare/sn. Her sahne ayrı bir dosya olarak alınabilir, sahneler geçişlerle birleşik tek videoya da dönüştürülebilir. Arka plan koyu (MP4) ya da şeffaf (ProRes 4444 .mov) olabilir.

## Kurulum (bir kez)

1. Python 3.12 kurulu olmalı. Kontrol etmek için `py --version` çalıştırın. Yüklü değilse: `winget install -e --id Python.Python.3.12`.
2. `kurulum.bat` dosyasına çift tıklayın. Paketler kurulur ve yaklaşık 5 MB harita verisi ile yazı tipleri indirilir.

Komut satırından kurmak isterseniz:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Başlatma

`baslat.bat` dosyasına çift tıklayın. Tarayıcıda `http://127.0.0.1:8765/` adresi açılır. Kapatmak için siyah pencereyi kapatın.

## Kullanım

- **Sahneler:** Sol üstte projedeki sahneler listelenir. Kutucuk sahneyi render'a dahil eder; ↑ ↓ sırayı değiştirir, ✕ siler. "Sahne ekle" yeni bir sahne ekler.
- **Ayarlar:** Seçili sahnenin ayarlarıdır. "otomatik" yazan alanlar boş bırakılırsa metin kendiliğinden oluşur (örneğin eyalet adı).
- **Önizleme:** Ayar değiştikçe kendiliğinden yenilenir. Alttaki çubukla sahnenin istediğiniz anına bakabilirsiniz.
- **County boyama:** Üstten bir renk (kategori) seçin, haritada county'lere tıklayın ya da basılı tutup sürükleyin. "NOT ENOUGH DATA" rengi boyamayı siler.
- **CSV / Excel yükle:** İlk satır başlık olmalı. County sütunu `county`, `name` ya da `fips`; kategori sütunu `category` ya da `kategori` olabilir. Kategori olarak etiket (`PRICES BREAKING`) ya da anahtar (`price`) yazılabilir. Örnek:

  ```
  county,category
  Charlotte,PRICES BREAKING
  St. Lucie,BUYERS PULLED BACK
  12071,price
  ```

  Eşleşmeyen satırlar panelde listelenir. Aynı adı taşıyan county'lerde (ör. Virginia'da "Richmond city" ve "Richmond County") tam adı yazın.
- **Kamera:** Otomatik kadraj beğenilmezse "Kamera" bölümündeki yakınlaştırma ve kaydırma ayarlarıyla düzeltin.
- **Render:** Çıktı seçeneklerini işaretleyip "Render al"a basın. Dosyalar `out\<proje adı>\<tarih-saat>\` klasörüne yazılır; "Klasörü aç" ile açılır.
- **Projeler:** "Kaydet" ayarları `projects\<ad>.json` dosyasına yazar. "Proje aç…" listesinden geri açılır. Hazır gelen `ornek_florida` projesi örnek Florida videosunu üretir.

## Şeffaf arka plan

Şeffaf çıktı ProRes 4444 (.mov) biçimindedir. Premiere Pro, DaVinci Resolve ve Final Cut Pro'da doğrudan açılır. Tarayıcı bu dosyayı oynatamaz; kurgu programında açın.

## Komut satırı

```powershell
.\.venv\Scripts\python -m engine.cli render projects\ornek_florida.json
.\.venv\Scripts\python -m engine.cli render projects\ornek_florida.json --transparent --no-separate
.\.venv\Scripts\python -m engine.cli still projects\ornek_florida.json --scene 0 --t 8.6 --out kare.png
```

## Testler

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest            # hızlı testler
.\.venv\Scripts\python -m pytest -m slow    # tam render testleri (birkaç dakika)
```

Görsel regresyon testleri `reference\` klasöründeki karelerle karşılaştırma yapar. Bu klasör yoksa testler atlanır.

## Sorun giderme

- **Veri ya da yazı tipi indirilemiyor:** Aşağıdaki dosyaları tarayıcıyla indirip belirtilen yerlere koyun:
  - `https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json` → `data\counties.json`
  - `https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf` → `data\fonts\`
  - `https://raw.githubusercontent.com/google/fonts/main/ofl/barlow/Barlow-Regular.ttf`, `Barlow-SemiBold.ttf`, `Barlow-Bold.ttf` → `data\fonts\`
- **shapely kurulamıyor:** Python 3.12 kullanın.
- **Konsolda Türkçe karakterler bozuk:** `$env:PYTHONUTF8="1"` ile tekrar çalıştırın.
- **"Boş port bulunamadı":** Açık kalan başka bir Harita Stüdyosu penceresini kapatın.

## Klasörler

| Klasör | İçerik |
|---|---|
| `engine\` | veri, geometri, ayarlar, render, birleştirme, proje dosyası, komut satırı |
| `scenes\` | sahne tanımları |
| `app\` | web sunucusu ve arayüz |
| `projects\` | kaydedilen projeler |
| `data\` | indirilen harita verisi ve yazı tipleri |
| `out\` | render çıktıları |

## Kaynaklar

- County sınırları: ABD Sayım Bürosu verisinden türetilmiş GeoJSON (plotly/datasets).
- Yazı tipleri: Bebas Neue ve Barlow (Google Fonts, SIL Open Font License).
````

- [ ] **Step 5: Eski dosyaları sil ve `.gitignore` dosyasını sadeleştir**

Run:
```bash
git rm CLAUDE_CODE_ANIM_TASK.md scene_a.py scene_b.py scene_common.py prep_data.py render_all.py
```

Run: `powershell -Command "Remove-Item -ErrorAction SilentlyContinue state_outlines.json"`

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
data/
out/
reference/
```

- [ ] **Step 6: FredPull referansı kalmadığını doğrula**

Run: `git grep -i fredpull -- . ":!docs"`
Expected: çıktı yok.

- [ ] **Step 7: Tüm testler**

Run: `.venv\Scripts\python -m pytest`
Expected: tümü geçer.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Başlatıcılar, README; eski tek seferlik betikler kaldırıldı"
```

---

### Task 16: Son doğrulama

- [ ] **Step 1:** Run: `.venv\Scripts\python -m pytest -m "slow or not slow" -v`. Expected: bütün testler geçer (slow dahil).
- [ ] **Step 2:** `cmd /c baslat.bat` komutunu arka planda çalıştır. Aynı işi `preview_start` ile de yapabilirsin. `http://127.0.0.1:8765/` açılmalı ve arayüz yüklenmeli.
- [ ] **Step 3:** Arayüzden `ornek_florida` projesini "Render al" ile üret. `birlesik.mp4` için `count_frames_and_secs` sonucu `(717, 23.9)` olmalı.
- [ ] **Step 4:** Texas senaryosu:
  1. Yeni proje aç, eyaleti Texas yap.
  2. Birkaç county'yi boya, Harris'i vurgula.
  3. Yalnızca 1. sahneyi render al.
  4. Videodan 3 kare çıkar ve gözle bak: kadraj, başlık ve etiket düzgün olmalı.
- [ ] **Step 5:** Şeffaf render al. `.mov` dosyası üretilmeli; alfa değeri test yardımcısı `decode_frame` ile kontrol edilir.
- [ ] **Step 6:** Kullanıcıya rapor: ne yapıldı, nasıl başlatılır, test sonuçları, bilinen sınırlar ve sonraki adım önerileri.
