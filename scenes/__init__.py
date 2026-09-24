"""Sahne kaydı: sahne id -> Scene. Arayüzdeki "Sahne ekle" listesi bu sırayı kullanır."""
from scenes import county_focus, price_ladder, state_map

REGISTRY = {s.id: s for s in (state_map.SCENE, county_focus.SCENE, price_ladder.SCENE)}
