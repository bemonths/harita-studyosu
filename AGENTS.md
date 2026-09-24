# Yapay zeka ajanları için notlar

Bu depo "Harita Stüdyosu": ABD eyalet/county harita animasyonlarını video olarak üreten yerel bir araç (Python + matplotlib + ffmpeg, FastAPI arayüzü).

- **Entegrasyon ve otomasyon:** [docs/ENTEGRASYON.md](docs/ENTEGRASYON.md). Proje JSON şeması, komut satırı, HTTP API ve county eşleme orada anlatılıyor.
- **Son kullanıcı kılavuzu:** [README.md](README.md).
- **Tasarım ve plan:** `docs/superpowers/specs/` ve `docs/superpowers/plans/`.

## Çalışma kuralları

- Ortam: Windows, Python 3.12, `.venv\Scripts\python`. Komutları depo kökünden çalıştırın.
- Değişiklikten sonra `.venv\Scripts\python -m pytest` çalıştırın. Render motoruna dokunduysanız `-m slow` testlerini de çalıştırın.
- Sahnelerin `update(t)` fonksiyonu durumsuz olmalı: aynı `t` aynı kareyi vermeli.
- `ornek_florida` projesinin kareleri `reference/` klasöründeki referanslarla karşılaştırılıyor (`tests/test_regression.py`). Görünümü bilerek değiştirirseniz referans kareleri de güncelleyin.
- Renk ve yazı tiplerini sahne koduna sabit yazmayın; `brand.json` / `engine/brand.py` kullanın.
- Referans kareleri yeniden üretmek için: `.venv\Scripts\python -m tests.make_reference`.
- Arayüz metinleri ve commit mesajları Türkçe, video içi varsayılan metinler İngilizce.
- `data/`, `out/` ve `reference/` klasörleri git dışıdır. `reference/` klasörünü silmeyin; regresyon testleri onu kullanır.
