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
    except (KeyError, TypeError):
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
