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
