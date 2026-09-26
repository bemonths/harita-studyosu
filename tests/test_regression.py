"""ornek_florida projesinin karelerini reference/ klasöründeki referanslarla karşılaştırır.
Referanslar marka görünümüyle (brand.json) üretildi; orijinal kodun kareleri reference/orijinal/ altında saklanıyor."""
import json
import os

import numpy as np
import pytest
from PIL import Image

from engine import assets, render
from scenes import REGISTRY
from tests.make_reference import SETS

REF = os.path.join(assets.ROOT, "reference")
SAMPLE = os.path.join(assets.ROOT, "projects", "ornek_florida.json")
GRAFIKLER = os.path.join(assets.ROOT, "projects", "ornek_grafikler.json")


def sample_scene(i, path=SAMPLE):
    with open(path, encoding="utf-8") as f:
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


def test_price_ladder_matches_original():
    scene, p = sample_scene(1)
    compare(scene, p, "b", [1.0, 5.0, 8.0, 10.5, 11.0])


@pytest.mark.parametrize("prefix", sorted(SETS["grafikler"][1]))
def test_chart_scenes_match_reference(prefix):
    """ornek_grafikler: grafik ve vaat sahnelerinin kareleri (tests/make_reference.py → SETS["grafikler"])."""
    i, times = SETS["grafikler"][1][prefix]
    scene, p = sample_scene(i, GRAFIKLER)
    compare(scene, p, prefix, times)
