"""Marka dosyası (brand.json): renk paleti, varsayılan kategoriler ve yazı tipleri.
Dosya bir kez okunup önbelleğe alınır; yoksa DEFAULTS kullanılır. Eksik alanlar varsayılanlarla tamamlanır."""
import copy
import json
import os
import re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "brand.json")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
KEY_RE = re.compile(r"^[a-z0-9_]{1,20}$")

DEFAULTS = {
    "colors": {
        "bg_dark": "#07111d",    # arka plan degradesinin kenarı
        "bg_light": "#102338",   # arka plan degradesinin merkezi
        "surface": "#0e1c2e",    # ABD'deki diğer eyaletlerin dolgusu
        "line": "#23405e",       # kenarlar, enlem-boylam, ızgara ve ayırıcı çizgiler
        "text": "#f4ecdd",       # başlıklar ve yer adları
        "muted": "#a9b4c2",      # alt başlıklar, açıklama, eksen ve sayaç başlıkları
        "accent": "#ff7a1f",     # neon sınır, vurgu parlaması, fiyat çizgisi, üst satır
        "loss": "#e0301e",       # indirim noktaları/etiketleri, zarar
        "neutral": "#5b7fa6",    # grafik sahneleri: karşılaştırma sütun ve çubuklarının nötr rengi
    },
    "categories": [
        {"key": "buyers", "label": "BUYERS PULLED BACK", "color": "#e0301e"},
        {"key": "sellers", "label": "SELLERS PULLING OUT", "color": "#b5487a"},
        {"key": "price", "label": "PRICES BREAKING", "color": "#e9b949"},
        {"key": "weak", "label": "WEAKENING", "color": "#b89b72"},
        {"key": "stable", "label": "HOLDING STEADY", "color": "#3e6a8f"},
        {"key": "hot", "label": "STILL HOT", "color": "#3fa37a"},
        {"key": "none", "label": "NOT ENOUGH DATA", "color": "#152538"},
    ],
    "fonts": {  # Google Fonts deposundaki ofl/ altına göreli yollar
        "place": "cinzel/Cinzel[wght].ttf",      # yer adları: eyalet başlığı, vurgu adı
        "numbers": "anton/Anton-Regular.ttf",    # büyük rakamlar ve büyük başlıklar
        "label": "barlow/Barlow-SemiBold.ttf",
        "label_bold": "barlow/Barlow-Bold.ttf",
        "label_regular": "barlow/Barlow-Regular.ttf",
    },
}


class BrandError(ValueError):
    pass


def _check(b):
    for k, v in b["colors"].items():
        if not HEX_RE.match(str(v)):
            raise BrandError(f"brand.json: colors.{k} #rrggbb biçiminde olmalı.")
    cats = b["categories"]
    if not isinstance(cats, list) or not 2 <= len(cats) <= 7:
        raise BrandError("brand.json: categories 2 ile 7 arasında öğe içermeli.")
    seen = set()
    for i, c in enumerate(cats, 1):
        if not isinstance(c, dict):
            raise BrandError(f"brand.json: {i}. kategori geçersiz.")
        key, label, color = str(c.get("key", "")), str(c.get("label", "")).strip(), str(c.get("color", ""))
        if not KEY_RE.match(key) or key in seen:
            raise BrandError(f"brand.json: {i}. kategorinin anahtarı geçersiz.")
        if not 1 <= len(label) <= 40:
            raise BrandError(f"brand.json: {i}. kategorinin etiketi 1–40 karakter olmalı.")
        if not HEX_RE.match(color):
            raise BrandError(f"brand.json: {i}. kategorinin rengi geçersiz.")
        seen.add(key)
    if cats[-1]["key"] != "none":
        raise BrandError("brand.json: son kategorinin anahtarı 'none' olmalı.")
    for k, v in b["fonts"].items():
        if not isinstance(v, str) or not v.lower().endswith((".ttf", ".otf")):
            raise BrandError(f"brand.json: fonts.{k} bir .ttf/.otf yolu olmalı.")


def parse(data):
    """Dosya içeriğini varsayılanlarla birleştirir, doğrular ve renkleri küçük harfe çevirir."""
    if not isinstance(data, dict):
        raise BrandError("brand.json bir JSON nesnesi olmalı.")
    out = copy.deepcopy(DEFAULTS)
    out["colors"].update(data.get("colors") or {})
    if "categories" in data:
        out["categories"] = data["categories"]
    out["fonts"].update(data.get("fonts") or {})
    _check(out)
    out["colors"] = {k: v.lower() for k, v in out["colors"].items()}
    out["categories"] = [{"key": c["key"], "label": c["label"].strip(), "color": c["color"].lower()}
                         for c in out["categories"]]
    return out


@lru_cache(maxsize=None)
def load():
    if not os.path.exists(PATH):
        return copy.deepcopy(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise BrandError(f"brand.json okunamadı: {e}") from e
    return parse(data)


def colors():
    return dict(load()["colors"])


def color(key):
    return load()["colors"][key]


def categories():
    return copy.deepcopy(load()["categories"])


def category_color(key, fallback=None):
    """Kategori rengini döndürür; kategori yoksa fallback (verilmezse vurgu rengi)."""
    for c in load()["categories"]:
        if c["key"] == key:
            return c["color"]
    return fallback or color("accent")


def fonts():
    """Yazı tipi görevi -> Google Fonts ofl/ altındaki göreli yol."""
    return dict(load()["fonts"])
