import imageio_ffmpeg
import pytest

from engine import compose, render
from tests.helpers import decode_frame


def test_offsets():
    assert compose.xfade_offsets([13.0, 11.5], 0.6) == pytest.approx([12.4])
    assert compose.xfade_offsets([2.0, 3.0, 4.0], 0.5) == pytest.approx([1.5, 4.0])


def _clips(scene, tmp_path, ext, transparent=False):
    return [render.render_video(scene, scene.defaults(), str(tmp_path / f"{n}{ext}"), transparent) for n in "ab"]


def test_compose_crossfade(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mp4"), transition=0.5)
    assert imageio_ffmpeg.count_frames_and_secs(out) == (45, 1.5)


def test_compose_hard_cut(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mp4"), transition=0)
    assert imageio_ffmpeg.count_frames_and_secs(out) == (60, 2.0)


def test_compose_transparent_keeps_alpha(dummy_scene, tmp_path):
    a, b = _clips(dummy_scene, tmp_path, ".mov", transparent=True)
    out = compose.compose([a, b], [1.0, 1.0], str(tmp_path / "ab.mov"), transition=0.5, transparent=True)
    f = decode_frame(out, 0.75, 1920, 1080)
    assert f[0, 0, 3] == 0 and f[540, 960, 3] == 255


def test_single_clip_is_copied(dummy_scene, tmp_path):
    a, _ = _clips(dummy_scene, tmp_path, ".mp4")
    out = compose.compose([a], [1.0], str(tmp_path / "tek.mp4"))
    assert imageio_ffmpeg.count_frames_and_secs(out) == (30, 1.0)
