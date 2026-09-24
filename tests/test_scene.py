import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from engine.scene import ease, fit_text, seg


def test_duration_param(dummy_scene):
    d = dummy_scene.all_params()[-1]
    assert (d.name, d.lo, d.hi, d.default, d.group) == ("duration", 0.5, 2.0, 1.0, "Zaman")


def test_defaults_and_schema(dummy_scene):
    assert dummy_scene.defaults() == {"color": "#ff0000", "duration": 1.0}
    s = dummy_scene.schema()
    assert s["id"] == "dummy" and [p["name"] for p in s["params"]] == ["color", "duration"]


def test_check_hook(dummy_scene):
    dummy_scene.check = lambda p: {"color": "olmaz"} if p["color"] == "#000000" else {}
    assert dummy_scene.validate({"color": "#000000"})[1] == {"color": "olmaz"}
    assert dummy_scene.validate({"color": "#00ff00"})[1] == {}


def test_ease_and_seg():
    assert seg(5, 4, 6) == 0.5 and seg(1, 4, 6) == 0 and seg(9, 4, 6) == 1
    assert ease(0) == 0 and ease(1) == 1 and ease(0.5) == 0.5


def test_fit_text():
    fig = plt.figure(figsize=(19.2, 10.8), dpi=50)
    long = fig.text(0, 0.5, "NORTH CAROLINA NORTH CAROLINA", fontsize=150)
    fit_text(fig, long, 0.34)
    w = long.get_window_extent(renderer=fig.canvas.get_renderer()).width
    assert w <= 0.34 * fig.bbox.width + 1
    short = fig.text(0, 0.2, "FL", fontsize=150)
    fit_text(fig, short, 0.34)
    assert short.get_fontsize() == 150
    plt.close(fig)
