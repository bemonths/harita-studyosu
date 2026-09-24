"""Regresyon referans karelerini mevcut koddan yeniden üretir.
Görünüm bilerek değiştiğinde kullanılır:
    .venv\\Scripts\\python -m tests.make_reference
Kareler önce out/referans_kontrol/ altına yazılır (gözle kontrol için), sonra reference/ altına kopyalanır.
Eski referanslar silinmez; reference/eski_<tarih-saat>/ klasörüne taşınır."""
import datetime as dt
import glob
import os
import shutil
import sys

from engine import assets, project, render
from scenes import REGISTRY

TIMES = {"a": (0, [2.0, 4.0, 6.0, 8.6, 10.5, 12.5]), "b": (1, [1.0, 5.0, 8.0, 10.5, 11.0])}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ref = os.path.join(assets.ROOT, "reference")
    check = os.path.join(assets.ROOT, "out", "referans_kontrol")
    os.makedirs(check, exist_ok=True)
    clean, errors = project.load(os.path.join(assets.ROOT, "projects", "ornek_florida.json"))
    if errors:
        raise SystemExit(f"ornek_florida.json hatalı: {errors}")
    old = sorted(glob.glob(os.path.join(ref, "test_*.png")))
    if old:
        backup = os.path.join(ref, "eski_" + dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(backup)
        for f in old:
            shutil.move(f, backup)
        print("eski referanslar:", backup)
    for prefix, (i, times) in TIMES.items():
        s = clean["scenes"][i]
        fr = render.Frames(REGISTRY[s["type"]], s["params"], dpi=100)
        try:
            for t in times:
                name = f"test_{prefix}_{t:.1f}.png"
                png = render.to_png(fr.draw(int(t * 30) / 30))
                for folder in (check, ref):
                    with open(os.path.join(folder, name), "wb") as f:
                        f.write(png)
                print(os.path.join(check, name))
        finally:
            fr.close()


if __name__ == "__main__":
    main()
