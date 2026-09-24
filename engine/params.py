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
