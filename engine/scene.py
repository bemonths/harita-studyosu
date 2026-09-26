"""Sahne sözleşmesi ve sahnelerin ortak yardımcıları."""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable

import numpy as np

from engine.params import Number, validate_all

FPS = 30
W_IN, H_IN = 19.2, 10.8  # 100 dpi'da 1920x1080


@dataclass
class SceneContext:
    fig: object
    p: dict
    transparent: bool
    fonts: dict
    dpi: int


@dataclass
class Scene:
    id: str
    title: str
    base_duration: float
    params: list
    setup: Callable  # setup(ctx) -> update(t); t temel süre cinsinden
    bg_center: tuple = (0.5, 0.5)  # koyu arka plan ışığının merkezi (x, y üstten), ekran oranı
    check: Callable = None  # check(clean) -> {ad: hata}; ayarlar arası kurallar

    def all_params(self):
        dur = Number("duration", "Süre (sn)", default=self.base_duration, group="Zaman",
                     lo=round(self.base_duration * 0.5, 2), hi=round(self.base_duration * 2, 2), step=0.1)
        return self.params + [dur]

    def validate(self, values):
        clean, errors = validate_all(self.all_params(), values or {})
        if not errors and self.check:
            errors.update(self.check(clean))
        return clean, errors

    def defaults(self):
        return self.validate({})[0]

    def schema(self):
        return {"id": self.id, "title": self.title, "base_duration": self.base_duration,
                "params": [p.schema() for p in self.all_params()]}


def round_half_up(v, dec=0):
    """Ekrana yazılan sayıların yuvarlaması: yarımlar yukarı (0,5 → 1; 30,5 → 31; 2,5 → 3; −2,5 → −3). Python'un round'u
    ve biçimlendirmesi yarımı çifte yuvarlar (30,5 → 30, 2,5 → 2). Değer ondalık yazılışıyla (str) ele alınır, böylece
    ikili gösterimden gelen 2,675 → 2,67 gibi sapmalar olmaz. dec 0 ise int döner."""
    d = Decimal(str(v)).quantize(Decimal(1).scaleb(-int(dec)), rounding=ROUND_HALF_UP)
    return int(d) if int(dec) <= 0 else float(d)


def ease(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    return np.clip((t - a) / (b - a), 0, 1)


def cap_scale(fig, prop, ref=0.70):
    """Yazı tipinin büyük harf yüksekliğini tasarım referansına (em'in %70'i) eşitleyen boyut çarpanı.
    Sahne yazı boyutları bu referansa göre verilir; marka yazı tipi değişince yerleşim bozulmaz."""
    p = prop.copy()
    p.set_size(100)
    _, h, _ = fig.canvas.get_renderer().get_text_width_height_descent("H", p, ismath=False)
    return ref / (h / (100 * fig.dpi / 72))


def fit_text(fig, text, max_frac):
    """Metin figür genişliğinin max_frac oranını aşıyorsa font boyutunu küçültür (sığıyorsa dokunmaz)."""
    text.set_parse_math(False)  # "$94 ... $100" gibi metinler mathtext sanılmasın
    renderer = fig.canvas.get_renderer()
    limit = max_frac * fig.bbox.width
    for _ in range(3):
        w = text.get_window_extent(renderer=renderer).width
        if w <= limit:
            return
        text.set_fontsize(text.get_fontsize() * limit / w * 0.99)
