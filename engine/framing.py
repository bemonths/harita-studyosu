"""Kamera çerçeveleme. Kamera = np.array([cx, cy, w]) (projeksiyon birimi); görünür yükseklik w*9/16."""
import numpy as np

ASPECT = 16 / 9
REGION = (0.40, 0.96, 0.08, 0.94)  # eyaletin sığacağı ekran bölgesi (x0, x1, y0, y1), y aşağıdan yukarı
# Vurgu county'sinin ekrandaki yeri: orijinal Charlotte kadrajından (0.5+0.06, 0.5-(0.02/0.55)/(9/16))
FOCUS_SCREEN = (0.56, 0.5 - (0.02 / 0.55) / (9 / 16))
FOCUS_MIN, FOCUS_MAX = 0.05, 0.30  # vurgu county'sinin ekran genişliğindeki payı


def _bbox(pts):
    return pts.min(0), pts.max(0)


def box(pts, pad):
    """Orijinal box(): noktaları pad paylı 16:9 kadraja ortalar (ABD görünümü)."""
    (xmin, ymin), (xmax, ymax) = _bbox(pts)
    w = max(xmax - xmin, (ymax - ymin) * ASPECT) * (1 + pad)
    return np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, w])


def state_frame(pts, zoom=1.0, shift_x=0.0, shift_y=0.0, region=REGION):
    """Eyaleti ekran bölgesine sığdırır. zoom>1 yaklaşır; shift_x/shift_y eyaleti ekran oranı kadar sağa/yukarı kaydırır."""
    (xmin, ymin), (xmax, ymax) = _bbox(pts)
    x0, x1, y0, y1 = region
    w = max((xmax - xmin) / (x1 - x0), (ymax - ymin) / ((y1 - y0) * 9 / 16)) / zoom
    sx, sy = (xmin + xmax) / 2, (ymin + ymax) / 2
    rx, ry = (x0 + x1) / 2, (y0 + y1) / 2
    return np.array([sx - (rx - 0.5 + shift_x) * w, sy - (ry - 0.5 + shift_y) * w * 9 / 16, w])


def focus_frame(county_pts, state_w, focus_zoom=0.55):
    """Vurgu kamerası: county FOCUS_SCREEN noktasına oturur ve ekran genişliğinin %5–30'unu kaplar."""
    (xmin, ymin), (xmax, ymax) = _bbox(county_pts)
    size = max(xmax - xmin, (ymax - ymin) * ASPECT)
    w = float(np.clip(state_w * focus_zoom, size / FOCUS_MAX, size / FOCUS_MIN))
    c = county_pts.mean(0)
    fx, fy = FOCUS_SCREEN
    return np.array([c[0] - (fx - 0.5) * w, c[1] - (fy - 0.5) * w * 9 / 16, w])
