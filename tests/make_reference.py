"""Regresyon referans karelerini mevcut koddan yeniden üretir.
Görünüm bilerek değiştiğinde kullanılır:
    .venv\\Scripts\\python -m tests.make_reference              # iki örnek proje
    .venv\\Scripts\\python -m tests.make_reference grafikler    # yalnız ornek_grafikler (ornek_florida'ya dokunmaz)
Kareler önce out/referans_kontrol/ altına yazılır (gözle kontrol için), sonra reference/ altına kopyalanır.
Eski referanslar silinmez; reference/eski_<tarih-saat>/ klasörüne taşınır (yalnız yeniden üretilen setinkiler)."""
import datetime as dt
import glob
import os
import shutil
import sys

from engine import assets, project, render
from scenes import REGISTRY

# set -> (proje dosyası, {önek: (sahne sırası, [anlar])})
SETS = {
    "florida": ("ornek_florida.json", {"a": (0, [2.0, 4.0, 6.0, 8.6, 10.5, 12.5]), "b": (1, [1.0, 5.0, 8.0, 10.5, 11.0])}),
    "grafikler": ("ornek_grafikler.json", {
        "g0": (0, [1.2, 5.5]), "g1": (1, [2.5, 9.2]), "g2": (2, [2.0, 6.7]), "g3": (3, [6.7]), "g4": (4, [2.5, 6.7]),
        "g5": (5, [5.7]), "g6": (6, [6.2]), "g7": (7, [2.0, 5.7]), "g8": (8, [6.2]), "g9": (9, [3.2, 7.2]),
    }),
}
TIMES = SETS["florida"][1]  # geriye uyum


def main(names=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    names = names or list(SETS)
    ref = os.path.join(assets.ROOT, "reference")
    check = os.path.join(assets.ROOT, "out", "referans_kontrol")
    os.makedirs(check, exist_ok=True)
    backup = os.path.join(ref, "eski_" + dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    for name in names:
        filename, times = SETS[name]
        clean, errors = project.load(os.path.join(assets.ROOT, "projects", filename))
        if errors:
            raise SystemExit(f"{filename} hatalı: {errors}")
        old = [f for prefix in times for f in glob.glob(os.path.join(ref, f"test_{prefix}_*.png"))]
        if old:
            os.makedirs(backup, exist_ok=True)
            for f in old:
                shutil.move(f, backup)
            print("eski referanslar:", backup)
        for prefix, (i, ts) in times.items():
            s = clean["scenes"][i]
            fr = render.Frames(REGISTRY[s["type"]], s["params"], dpi=100)
            try:
                for t in ts:
                    name_ = f"test_{prefix}_{t:.1f}.png"
                    png = render.to_png(fr.draw(int(t * 30) / 30))
                    for folder in (check, ref):
                        with open(os.path.join(folder, name_), "wb") as f:
                            f.write(png)
                    print(os.path.join(check, name_))
            finally:
                fr.close()


if __name__ == "__main__":
    bad = [a for a in sys.argv[1:] if a not in SETS]
    if bad:
        raise SystemExit(f"Bilinmeyen set: {bad}. Seçenekler: {', '.join(SETS)}")
    main(sys.argv[1:])
