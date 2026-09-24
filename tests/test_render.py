import io

import imageio_ffmpeg
import numpy as np
from PIL import Image

from engine import render
from tests.helpers import decode_frame


def test_background_is_brighter_at_center():
    bg = render.background(192, 108, (0.6, 0.45))
    assert bg.shape == (108, 192, 4) and np.all(bg[..., 3] == 1)
    assert bg[int(108 * 0.45), int(192 * 0.6), 0] > bg[0, 0, 0]


def test_frame_sizes(dummy_scene):
    p = dummy_scene.defaults()
    for dpi, shape in ((100, (1080, 1920, 4)), (50, (540, 960, 4))):
        fr = render.Frames(dummy_scene, p, dpi=dpi)
        try:
            assert fr.draw(0.5).shape == shape
        finally:
            fr.close()


def test_time_is_scaled_to_base_duration(dummy_scene):
    p = dummy_scene.defaults()
    p["duration"] = 2.0
    fr = render.Frames(dummy_scene, p, dpi=20)
    try:
        fr.draw(1.0)
        assert dummy_scene.calls[-1] == 0.5 and fr.n_frames == 60
    finally:
        fr.close()


def test_transparent_and_opaque_corners(dummy_scene):
    p = dummy_scene.defaults()
    for transparent, corner in ((True, 0), (False, 255)):
        fr = render.Frames(dummy_scene, p, transparent=transparent, dpi=20)
        try:
            a = fr.draw(0.5)
            assert a[0, 0, 3] == corner and a[a.shape[0] // 2, a.shape[1] // 2, 3] == 255
        finally:
            fr.close()


def test_draw_returns_independent_copies(dummy_scene):
    fr = render.Frames(dummy_scene, dummy_scene.defaults(), dpi=20)
    try:
        a = fr.draw(0.1)
        a[:] = 0
        assert fr.draw(0.1).max() > 0
    finally:
        fr.close()


def test_still_png(dummy_scene):
    png = render.still_png(dummy_scene, dummy_scene.defaults(), 0.5)
    assert Image.open(io.BytesIO(png)).size == (960, 540)


def test_render_video_mp4(dummy_scene, tmp_path):
    out = render.render_video(dummy_scene, dummy_scene.defaults(), str(tmp_path / "a.mp4"))
    assert imageio_ffmpeg.count_frames_and_secs(out) == (30, 1.0)


def test_render_video_transparent_mov(dummy_scene, tmp_path):
    progress = []
    out = render.render_video(dummy_scene, dummy_scene.defaults(), str(tmp_path / "a.mov"), transparent=True,
                              on_progress=lambda f, n: progress.append((f, n)))
    assert progress[0] == (1, 30) and progress[-1] == (30, 30)
    f = decode_frame(out, 0.5, 1920, 1080)
    assert f[0, 0, 3] == 0 and f[540, 960, 3] == 255
