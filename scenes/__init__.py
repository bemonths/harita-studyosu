"""Sahne kaydı: sahne id -> Scene."""
from scenes import state_map

REGISTRY = {s.id: s for s in (state_map.SCENE,)}
