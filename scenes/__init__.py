"""Sahne kaydı: sahne id -> Scene. Arayüzdeki "Sahne ekle" listesi bu sırayı kullanır."""
from scenes import (bar_list, county_focus, county_quiz, house_bars, house_grid, line_trend, price_ladder,
                    question_board, ring, state_map, thermometer)

REGISTRY = {s.id: s for s in (state_map.SCENE, county_focus.SCENE, price_ladder.SCENE,
                              question_board.SCENE, county_quiz.SCENE, house_bars.SCENE, line_trend.SCENE,
                              bar_list.SCENE, ring.SCENE, thermometer.SCENE, house_grid.SCENE)}
