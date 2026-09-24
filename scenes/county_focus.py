"""County odak sahnesi: eyalet kadrajında, county'ler boyalı ve neon sınır çizili olarak başlar, anlatılan
county'ye yakınlaşır ve etiketini gösterir. Videonun county bölümlerini açmak için kullanılır.
Başlık ve renk açıklaması yoktur. Etiket, county'nin eyalete daha az binen tarafına konur.
update(t) içindeki t temel süre (5 sn) cinsindendir."""
import numpy as np

from engine.scene import Scene, ease, seg
from scenes import maplib

PARAMS = [
    maplib.state_param(),
    *maplib.style_params(),
    maplib.assign_param(),
    *maplib.focus_params(required=True),
    *maplib.camera_params(),
]


def setup(ctx):
    p, fig = ctx.p, ctx.fig
    g = maplib.MapGeometry(p, label_side="auto")
    m = maplib.MapLayers(fig, g, p, ctx.fonts)
    appear = np.ones(len(g.c_owner))

    # state_map'in eyalet kadrajındaki son hali: ABD soluk, sınır çizili ve yumuşamış, county'ler boyalı
    m.us_coll.set_alpha(0.55)
    m.set_border(1.0, 0.0)
    m.set_glow(0.65)
    m.set_isles(0.8)
    m.state_fill.set_alpha(0.0)

    def update(t):
        # 0,0–0,4 sabit eyalet kadrajı; 0,4–2,2 county'ye yakınlaşma
        m.set_camera(g.cam_state if t < 0.4 else maplib.cam_lerp(g.cam_state, g.cam_focus, seg(t, 0.4, 2.2)))
        m.set_counties(appear, seg(t, 0.6, 1.6))
        # 1,8–2,6 kenar nabzı ve bağlantı çizgisi; 2,4–3,0 ad ve alt yazı; 3,0–3,6 istatistik; sonra tutma
        m.set_focus(glow_on=seg(t, 1.8, 2.4), pulse_t=t - 1.8, leader=ease(seg(t, 2.0, 2.6)),
                    name=ease(seg(t, 2.4, 3.0)), stat=ease(seg(t, 3.0, 3.6)))

    return update


SCENE = Scene(id="county_focus", title="County odak", base_duration=5.0, params=PARAMS, setup=setup,
              bg_center=(0.6, 0.45))
