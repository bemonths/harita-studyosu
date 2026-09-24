"""Sahne kaydı: sahne id -> Scene."""
from scenes import price_ladder, state_map

REGISTRY = {s.id: s for s in (state_map.SCENE, price_ladder.SCENE)}
