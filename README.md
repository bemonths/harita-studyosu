# Harita Stüdyosu

ABD eyalet ve county haritaları için animasyonlu video üreten yerel bir araç. Ayarlar tarayıcıda açılan bir panelden yapılır, önizlenir ve tek tuşla videoya dönüştürülür.

- **Eyalet haritası:** ABD'den seçilen eyalete inen kamera, neon sınır çizimi, kategorilere göre boyanan county'ler ve isteğe bağlı olarak vurgulanan bir county.
- **County odak:** boyalı eyalet haritasından anlatılan county'ye yakınlaşma ve etiketi. Videonun county bölümlerini açmak için. Etiket, county'nin deniz ya da eyalet dışı tarafına kendiliğinden yerleşir.
- **Fiyat merdiveni:** bir evin fiyat geçmişi, indirim sayaçları ve alış fiyatıyla karşılaştırma.
- **Çıktı:** 1920x1080, 30 kare/sn. Her sahne ayrı bir dosya olarak alınabilir, sahneler geçişlerle birleşik tek videoya da dönüştürülebilir. Arka plan koyu (MP4) ya da şeffaf (ProRes 4444 .mov) olabilir.

## Kurulum (bir kez)

1. Python 3.12 kurulu olmalı. Kontrol etmek için `py --version` çalıştırın. Yüklü değilse: `winget install -e --id Python.Python.3.12`.
2. `kurulum.bat` dosyasına çift tıklayın. Paketler kurulur ve yaklaşık 5 MB harita verisi ile yazı tipleri indirilir.

Komut satırından kurmak isterseniz:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Başlatma

`baslat.bat` dosyasına çift tıklayın. Tarayıcıda `http://127.0.0.1:8765/` adresi açılır. Kapatmak için siyah pencereyi kapatın.

## Kullanım

- **Sahneler:** Sol üstte projedeki sahneler listelenir. Kutucuk sahneyi render'a dahil eder; ↑ ↓ sırayı değiştirir, ✕ siler. "Sahne ekle" yeni bir sahne ekler.
- **Ayarlar:** Seçili sahnenin ayarlarıdır. "otomatik" yazan alanlar boş bırakılırsa metin kendiliğinden oluşur (örneğin eyalet adı). Hatalı bir değer girildiğinde alanın altında kırmızı bir açıklama çıkar.
- **Önizleme:** Ayar değiştikçe kendiliğinden yenilenir. Alttaki çubukla sahnenin istediğiniz anına bakabilirsiniz.
- **County boyama:** Üstten bir renk (kategori) seçin, haritada county'lere tıklayın ya da basılı tutup sürükleyin. "NOT ENOUGH DATA" rengi boyamayı siler.
- **CSV / Excel yükle:** İlk satır başlık olmalı. County sütunu `county`, `name` ya da `fips`; kategori sütunu `category` ya da `kategori` olabilir. Kategori olarak etiket (`PRICES BREAKING`) ya da anahtar (`price`) yazılabilir. Örnek:

  ```
  county,category
  Charlotte,PRICES BREAKING
  St. Lucie,BUYERS PULLED BACK
  12071,price
  ```

  Eşleşmeyen satırlar panelde listelenir. Aynı adı taşıyan county'lerde (ör. Virginia'da "Richmond city" ve "Richmond County") tam adı yazın.
- **Vurgu:** "Vurgulanan county" seçilirse kamera sahnenin sonunda o county'ye yaklaşır ve adını, alt yazısını ve istatistiğini gösterir. Seçilmezse kamera eyalette kalır.
- **Kamera:** Otomatik kadraj beğenilmezse "Kamera" bölümündeki yakınlaştırma ve kaydırma ayarlarıyla düzeltin.
- **Render:** Çıktı seçeneklerini işaretleyip "Render al"a basın. Dosyalar `out\<proje adı>\<tarih-saat>\` klasörüne yazılır; "Klasörü aç" ile açılır.
- **Projeler:** "Kaydet" ayarları `projects\<ad>.json` dosyasına yazar. "Proje aç…" listesinden geri açılır. Hazır gelen `ornek_florida` projesi örnek Florida videosunu üretir.

## Marka (renkler ve yazı tipleri)

Videolardaki renkler, varsayılan renk kategorileri ve yazı tipleri depo kökündeki `brand.json` dosyasından gelir. Bu dosyayı değiştirip Harita Stüdyosu'nu yeniden başlatmanız yeterlidir; yeni yazı tipleri ilk açılışta indirilir. Dosya silinirse yerleşik varsayılanlar kullanılır. Ayrıntılar: [docs/ENTEGRASYON.md](docs/ENTEGRASYON.md) §3.1.

## Şeffaf arka plan

Şeffaf çıktı ProRes 4444 (.mov) biçimindedir. Premiere Pro, DaVinci Resolve ve Final Cut Pro'da doğrudan açılır. Tarayıcı bu dosyayı oynatamaz; kurgu programında açın.

## Komut satırı

Otomasyon, HTTP API ve proje dosyası şeması için ayrıntılı rehber: [docs/ENTEGRASYON.md](docs/ENTEGRASYON.md).

```powershell
.\.venv\Scripts\python -m engine.cli render projects\ornek_florida.json
.\.venv\Scripts\python -m engine.cli render projects\ornek_florida.json --transparent --no-separate
.\.venv\Scripts\python -m engine.cli still projects\ornek_florida.json --scene 0 --t 8.6 --out kare.png
```

## Testler

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest            # hızlı testler
.\.venv\Scripts\python -m pytest -m slow    # tam render testleri (birkaç dakika)
```

Görsel regresyon testleri `reference\` klasöründeki karelerle karşılaştırma yapar. Bu klasör yoksa testler atlanır.

## Sorun giderme

### Elle indirme

Veri ya da yazı tipi indirilemiyorsa aşağıdaki dosyaları tarayıcıyla indirip belirtilen yerlere koyun:

- `https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json` → `data\counties.json`
- `https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf` → `data\fonts\Cinzel[wght].ttf`
- `https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf` → `data\fonts\`
- `https://raw.githubusercontent.com/google/fonts/main/ofl/barlow/Barlow-Regular.ttf`, `Barlow-SemiBold.ttf`, `Barlow-Bold.ttf` → `data\fonts\`

Bu liste varsayılan marka yazı tipleri içindir. `brand.json` içinde başka yazı tipleri seçtiyseniz aynı adresin sonuna oradaki yolu ekleyin.

### Diğer sorunlar

- **shapely kurulamıyor:** Python 3.12 kullanın.
- **Konsolda Türkçe karakterler bozuk:** `$env:PYTHONUTF8="1"` ile tekrar çalıştırın.
- **"Boş port bulunamadı":** Açık kalan başka bir Harita Stüdyosu penceresini kapatın.

## Klasörler

| Klasör | İçerik |
|---|---|
| `engine\` | veri, geometri, ayarlar, render, birleştirme, proje dosyası, komut satırı |
| `scenes\` | sahne tanımları |
| `app\` | web sunucusu ve arayüz |
| `projects\` | kaydedilen projeler |
| `data\` | indirilen harita verisi ve yazı tipleri |
| `out\` | render çıktıları |

## Kaynaklar

- County sınırları: ABD Sayım Bürosu verisinden türetilmiş GeoJSON (plotly/datasets).
- Yazı tipleri: Cinzel, Anton ve Barlow (Google Fonts, SIL Open Font License).
