"""Kare üretimi: kurulmuş sahne figürü, ffmpeg ile video yazma, tek kare önizleme."""
import io
import subprocess

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["text.parse_math"] = False  # "$" işaretleri mathtext sanılmasın
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from matplotlib.artist import Artist
from matplotlib.colors import to_rgb

from engine import assets, brand
from engine.scene import FPS, H_IN, W_IN, SceneContext


def ffmpeg_exe():
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def background(w, h, center):
    """Radyal koyu degrade (satır 0 = üst): kenarlarda brand bg_dark, merkezde bg_light."""
    bg0, bg1 = np.array(to_rgb(brand.color("bg_dark"))), np.array(to_rgb(brand.color("bg_light")))
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w * center[0]) / w) ** 2 + ((yy - h * center[1]) / h) ** 2)
    g = np.clip(1 - d * 1.6, 0, 1)[..., None]
    return np.dstack([bg0 * (1 - g) + bg1 * g, np.ones((h, w))])


class Backdrop(Artist):
    """Hazır arka plan (uint8 RGBA, satır 0 üstte): her karede Agg tamponuna doğrudan kopyalanır, ardından sahnenin
    parçaları üstüne çizilir. Eskiden figimage kullanılıyordu; matplotlib görüntüyü her karede float'a çevirip yeniden
    örnekliyordu (kare süresinin ~%80'i, paralel render'da bellek yolunu tıkıyordu). Sonuç piksel piksel aynı."""

    def __init__(self, rgba):
        super().__init__()
        self.rgba = rgba
        self.set_zorder(-10)

    def draw(self, renderer):
        np.asarray(renderer.buffer_rgba())[...] = self.rgba


class Frames:
    """Bir sahnenin kurulmuş figürü; draw(t) istenen anın RGBA karesini verir."""

    def __init__(self, scene, params, transparent=False, dpi=100):
        self.scene = scene
        self.duration = float(params["duration"])
        self.fig = plt.figure(figsize=(W_IN, H_IN), dpi=dpi)
        self.fig.patch.set_alpha(0)
        self.w, self.h = int(round(W_IN * dpi)), int(round(H_IN * dpi))
        if not transparent:
            # figimage'ın çevirdiği gibi: 0–1 → bayt, kesme ile
            self.fig.add_artist(Backdrop((background(self.w, self.h, scene.bg_center) * 255).astype(np.uint8)))
        self.update = scene.setup(SceneContext(self.fig, params, transparent, assets.fonts(), dpi))

    @property
    def n_frames(self):
        return int(round(self.duration * FPS))

    def draw(self, t):
        """t: gerçek saniye; sahneye temel süre cinsinden verilir."""
        if self.duration != self.scene.base_duration:
            t = t * self.scene.base_duration / self.duration
        self.update(t)
        self.fig.canvas.draw()
        return np.array(self.fig.canvas.buffer_rgba())

    def close(self):
        plt.close(self.fig)


def to_png(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, "PNG", compress_level=1)
    return buf.getvalue()


def still_png(scene, params, t, transparent=False, dpi=50):
    fr = Frames(scene, params, transparent, dpi)
    try:
        return to_png(fr.draw(t))
    finally:
        fr.close()


def encoder_args(transparent, threads=None):
    """threads: kodlayıcı iş parçacığı sınırı (paralel render'da); None ise ffmpeg'in varsayılanı (bütün çekirdekler)."""
    extra = ["-threads", str(threads)] if threads else []
    if transparent:
        return ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", *extra]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", *extra]


def video_ext(transparent):
    return ".mov" if transparent else ".mp4"


def render_video(scene, params, out_path, transparent=False, on_progress=None, threads=None):
    fr = Frames(scene, params, transparent, dpi=100)
    n = fr.n_frames
    proc = subprocess.Popen([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                             "-s", f"{fr.w}x{fr.h}", "-r", str(FPS), "-i", "-", *encoder_args(transparent, threads),
                             out_path],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            proc.stdin.write(fr.draw(i / FPS).tobytes())
            if on_progress:
                on_progress(i + 1, n)
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg hata verdi: {err.strip()[-500:]}")
    except BaseException:
        proc.kill()
        raise
    finally:
        fr.close()
    return out_path
