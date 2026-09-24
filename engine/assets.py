"""Veri ve font dosyaları: yollar, indirme, eski yerleşimden taşıma, FontProperties.
Hangi yazı tiplerinin kullanılacağı brand.json'daki "fonts" bölümünden gelir."""
import os
import shutil
import urllib.parse
import urllib.request
from functools import lru_cache

from engine import brand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FONT_DIR = os.path.join(DATA, "fonts")
COUNTIES = os.path.join(DATA, "counties.json")

COUNTIES_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
FONT_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"


class AssetError(RuntimeError):
    pass


def font_files():
    """Yazı tipi görevi -> Google Fonts ofl/ altındaki göreli yol (brand.json)."""
    return brand.fonts()


def font_path(key):
    return os.path.join(FONT_DIR, os.path.basename(font_files()[key]))


def _ok(path):
    return os.path.exists(path) and os.path.getsize(path) > 1000


def missing():
    """Eksik veri/font dosyalarının yolları."""
    return [p for p in [COUNTIES] + [font_path(k) for k in font_files()] if not _ok(p)]


def ensure(log=print):
    """Eksik dosyaları indirir. Eski yerleşimdeki (klasör kökü) dosyaları önce data/ altına taşır."""
    os.makedirs(FONT_DIR, exist_ok=True)
    files = font_files()
    old = {os.path.join(ROOT, "counties.json"): COUNTIES}
    for key, rel in files.items():
        old[os.path.join(ROOT, "fonts", os.path.basename(rel))] = font_path(key)
    for src, dst in old.items():
        if _ok(src) and not _ok(dst):
            shutil.move(src, dst)
    jobs = [(COUNTIES_URL, COUNTIES)] + [(FONT_BASE + urllib.parse.quote(rel), font_path(k)) for k, rel in files.items()]
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
    """Yazı tipi görevi (place, numbers, label, label_bold, label_regular) -> FontProperties.
    Font dosyası eksikse AssetError."""
    from matplotlib import font_manager as fm

    out = {}
    for key in font_files():
        path = font_path(key)
        if not _ok(path):
            raise AssetError(f"Font eksik: {path}")
        fm.fontManager.addfont(path)
        out[key] = fm.FontProperties(fname=path)
    return out
