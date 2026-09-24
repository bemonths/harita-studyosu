import matplotlib.patches as mpatches
import pytest

from engine.params import Color
from engine.scene import Scene


@pytest.fixture
def dummy_scene():
    """1 saniyelik deneme sahnesi: ortada opak bir kare; update çağrılarını kaydeder."""
    calls = []

    def setup(ctx):
        ax = ctx.fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(mpatches.Rectangle((0.4, 0.4), 0.2, 0.2, color=ctx.p["color"]))

        def update(t):
            calls.append(t)

        return update

    scene = Scene(id="dummy", title="Deneme", base_duration=1.0,
                  params=[Color("color", "Renk", default="#ff0000")], setup=setup)
    scene.calls = calls
    return scene
