import subprocess

import imageio_ffmpeg
import numpy as np


def decode_frame(path, t, w, h):
    """Videodan t saniyesindeki kareyi RGBA olarak çözer."""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = subprocess.run([exe, "-loglevel", "error", "-ss", str(t), "-i", path, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 4)
