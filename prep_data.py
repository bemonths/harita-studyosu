"""Bir kerelik hazırlık: county sınırları, yazı tipleri ve birleştirilmiş eyalet sınırları.
Çalıştır: python prep_data.py   (internet gerekir, ~5 MB)"""
import os, json, urllib.request
os.chdir(os.path.dirname(os.path.abspath(__file__)))

COUNTIES_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
FONT_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = ["bebasneue/BebasNeue-Regular.ttf", "barlow/Barlow-Regular.ttf", "barlow/Barlow-SemiBold.ttf", "barlow/Barlow-Bold.ttf"]

def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print("var:", dest); return
    print("indiriliyor:", url)
    urllib.request.urlretrieve(url, dest)

os.makedirs("fonts", exist_ok=True)
get(COUNTIES_URL, "counties.json")
for f in FONTS:
    get(FONT_BASE + f, os.path.join("fonts", os.path.basename(f)))

if not os.path.exists("state_outlines.json"):
    from shapely.geometry import shape
    from shapely.ops import unary_union
    print("eyalet sınırları birleştiriliyor (county'lerden)...")
    groups = {}
    for feat in json.load(open("counties.json", encoding="utf-8"))["features"]:
        st = feat["properties"]["STATE"]
        if st in ("02", "15", "72"):  # Alaska, Hawaii, Puerto Rico hariç
            continue
        groups.setdefault(st, []).append(shape(feat["geometry"]).buffer(0))
    out = {}
    for st, geoms in groups.items():
        u = unary_union(geoms)
        if st != "12":
            u = u.simplify(0.01, preserve_topology=True)
        polys = [u] if u.geom_type == "Polygon" else list(u.geoms)
        out[st] = [list(map(list, p.exterior.coords)) for p in polys if p.area > 1e-5]
    json.dump(out, open("state_outlines.json", "w", encoding="utf-8"))
    print("state_outlines.json yazıldı:", len(out), "eyalet")
print("hazırlık tamam")
