# Görev: Örnek animasyon videosunu bu bilgisayarda üret

## Amaç

Bu klasördeki kodla 24 saniyelik örnek animasyon videosunu bu bilgisayarda üretmek. Video iki sahneden oluşuyor:

1. ABD haritasından Florida'ya inen kamera, neon hatla çizilen eyalet sınırı, sinyal rengine boyanan county'ler ve yanıp sönen Charlotte County.
2. Lee County'deki bir evin fiyat merdiveni: dokuz indirim, sayaçlar ve 2017'deki alış fiyatı.

Bu görev sadece örneği kurup çalıştırmak. **Kodun tasarımını değiştirme.** Yalnızca kurulum ya da çalıştırma hatası çıkarsa onu düzelt ve neyi değiştirdiğini bildir.

## Klasör

Bu `anim/` klasörü FredPull deposunun köküne kopyalandı. İçindekiler:

| Dosya | Görevi |
|---|---|
| `requirements.txt` | Python paketleri: numpy, matplotlib, shapely, imageio-ffmpeg (ffmpeg'i kendi içinde getirir, ayrıca kurulum gerekmez) |
| `prep_data.py` | Bir kerelik hazırlık: county sınırlarını (GitHub, Sayım Bürosu kaynaklı GeoJSON) ve yazı tiplerini (Google Fonts: Bebas Neue, Barlow) indirir, county'leri birleştirip `state_outlines.json` üretir |
| `scene_a.py` | Harita sahnesi, 13 saniye, `out/scene_a.mp4` |
| `scene_b.py` | Fiyat merdiveni sahnesi, 11,5 saniye, `out/scene_b.mp4` |
| `scene_common.py` | ffmpeg yolunu bulan yardımcı |
| `render_all.py` | Hepsini sırayla çalıştırır ve iki sahneyi yarım saniyelik geçişle birleştirir |
| `.gitignore` | Sanal ortam, indirilen veriler ve çıktılar depoya girmesin |

## Adımlar (Windows, PowerShell)

1. Python kontrolü: `py --version`. Python 3.11 veya 3.12 yoksa kur: `winget install -e --id Python.Python.3.12` (sonra yeni bir terminal aç).
2. Sanal ortam ve paketler:
   ```powershell
   cd anim
   py -3 -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Videoyu üret:
   ```powershell
   .\.venv\Scripts\python render_all.py
   ```
   İlk çalıştırmada yaklaşık 5 MB veri indirilir. Render bu bilgisayarda birkaç dakikadan kısa sürmeli.

## Beklenen sonuç

- `anim/out/ornek_animasyon_florida.mp4` oluşur: 1920x1080, 30 kare/saniye, yaklaşık 23,9 saniye.
- Süre kontrolü:
  ```powershell
  .\.venv\Scripts\python -c "import imageio_ffmpeg as f; print(f.count_frames_and_secs('out/ornek_animasyon_florida.mp4'))"
  ```
  Beklenen çıktı yaklaşık `(717, 23.9)`.
- Tek kare kontrolü (isteğe bağlı): aşağıdaki komut `out/test_a_8.6.png` üretir. Görüntüde solda büyük "FLORIDA" başlığı ve renk açıklaması, sağda renkli county'lerle Florida haritası olmalı.
  ```powershell
  $env:TEST="8.6"; .\.venv\Scripts\python scene_a.py; Remove-Item Env:TEST
  ```

## Bitince bildir

- Videonun tam yolu.
- `count_frames_and_secs` çıktısı.
- `render_all.py` çalıştırmasının toplam süresi.
- Yaptığın her değişiklik (varsa) ve sebebi.

## Sorun giderme

- **shapely kurulamıyor:** Python 3.12 kullan; bu sürüm için hazır paket var.
- **Veri ya da font indirilemiyor:** `prep_data.py` içindeki adreslere tarayıcıdan erişilebildiğini kontrol et; dosyaları elle indirip aynı adlarla koymak da yeterli (`counties.json` klasör kökünde, fontlar `fonts/` altında).
- **ffmpeg bulunamadı:** `imageio-ffmpeg` paketi kuruluysa ffmpeg otomatik bulunur; paket kurulumunu kontrol et.
- **Konsolda Türkçe karakterler bozuk:** `$env:PYTHONUTF8="1"` ile tekrar çalıştır.
- **Font uyarısı ve farklı görünen yazılar:** `fonts/` klasöründe dört `.ttf` dosyası olmalı.

## Sonraki adım (ŞİMDİ YAPMA)

Örnek çalıştıktan sonra ayrı bir görev olarak ele alınacak:

- Sahnelerin eyalet, county ve ev bilgisini FredPull çıktılarından (`out/cache_XX.json`, `out/listings_XX.json`) okuması.
- FredPull'a "Animasyon üret" düğmesi.
- Kurguda bindirme için şeffaf arka planlı çıktı.
