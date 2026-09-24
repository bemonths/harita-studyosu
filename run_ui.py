"""Harita Stüdyosu'nu başlatır: veriyi hazırlar, boş port bulur, sunucuyu açar, tarayıcıyı açar.
Kullanım: .venv\\Scripts\\python run_ui.py [--port 8765] [--no-browser]"""
import argparse
import os
import socket
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def free_port(start=8765, tries=20):
    for port in range(start, start + tries):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"Boş port bulunamadı ({start}–{start + tries - 1}). Açık kalan Harita Stüdyosu pencerelerini kapatın.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    from engine import assets

    try:
        assets.ensure()
    except assets.AssetError as e:
        print("HATA:", e)
        return 1
    port = args.port or free_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"Harita Stüdyosu açılıyor: {url}")
    print("Kapatmak için bu pencerede Ctrl+C'ye basın ya da pencereyi kapatın.")
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    import uvicorn

    uvicorn.run("app.server:app", host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
