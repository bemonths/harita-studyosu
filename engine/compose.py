"""Sahne videolarını xfade geçişiyle (ya da geçişsiz) tek videoda birleştirir."""
import shutil
import subprocess

from engine.render import encoder_args, ffmpeg_exe


def xfade_offsets(durations, transition):
    """k'ıncı geçişin başlangıcı: sum(d[0..k]) - (k+1)*transition."""
    out, acc = [], 0.0
    for k, d in enumerate(durations[:-1]):
        acc += d
        out.append(acc - (k + 1) * transition)
    return out


def compose(paths, durations, out_path, transition=0.6, transparent=False):
    if len(paths) == 1:
        shutil.copyfile(paths[0], out_path)
        return out_path
    fmt = "yuva444p10le" if transparent else "yuv420p"
    n = len(paths)
    if transition <= 0:
        chain = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0,format={fmt}[v]"
    else:
        parts = [f"[{i}:v]format={fmt}[s{i}]" for i in range(n)] if transparent else []
        src = (lambda i: f"s{i}") if transparent else (lambda i: f"{i}:v")
        prev = src(0)
        for k, off in enumerate(xfade_offsets(durations, transition)):
            label = f"x{k}"
            parts.append(f"[{prev}][{src(k + 1)}]xfade=transition=fade:duration={transition}:offset={off:.4f}[{label}]")
            prev = label
        parts.append(f"[{prev}]format={fmt}[v]")
        chain = ";".join(parts)
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error"]
    for p in paths:
        cmd += ["-i", p]
    cmd += ["-filter_complex", chain, "-map", "[v]", *encoder_args(transparent), out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"Birleştirme başarısız: {r.stderr.strip()[-500:]}")
    return out_path
