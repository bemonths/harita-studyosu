"""Örnek videoyu baştan sona üretir: hazırlık -> sahne A -> sahne B -> birleştirme.
Çalıştır: python render_all.py   Çıktı: out/ornek_animasyon_florida.mp4"""
import os, sys, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from scene_common import ffmpeg_exe

def run(script):
    print(f"\n=== {script} ===", flush=True)
    r = subprocess.run([sys.executable, script], env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode != 0:
        sys.exit(f"{script} hata verdi (kod {r.returncode})")

run("prep_data.py")
run("scene_a.py")
run("scene_b.py")

out = os.path.join("out", "ornek_animasyon_florida.mp4")
cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-i", "out/scene_a.mp4", "-i", "out/scene_b.mp4",
       "-filter_complex", "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=12.4,format=yuv420p[v]",
       "-map", "[v]", "-c:v", "libx264", "-crf", "17", "-preset", "medium", out]
print("\n=== birleştirme ===", flush=True)
subprocess.run(cmd, check=True)
print("\nBITTI:", os.path.abspath(out))
