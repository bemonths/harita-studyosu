# Harita Stüdyosu: Tasarım

Tarih: 2026-09-24
Durum: Kullanıcı kapsamı ve arayüz taslağını onayladı. Teknik kararlar kullanıcının isteğiyle Claude'a bırakıldı.

## 1. Amaç

`anim/` klasöründeki örnek animasyon kodunu, ABD eyalet ve county haritası animasyonları üreten, tarayıcıdan kontrol edilen bir araca dönüştürmek. Proje başka hiçbir projeye (FredPull dahil) bağlı değil.

İlk sürüm:

- Yerel web arayüzü: ayar paneli, tek kare önizleme, render ve ilerleme göstergesi.
- İki sahne tipi. **Eyalet haritası** eski `scene_a.py`'nin 48 eyalete genelleştirilmiş hali, **fiyat merdiveni** ise eski `scene_b.py`'nin fiyat geçmişini ayardan okuyan hali.
- County renkleri CSV veya Excel'den yükleniyor, haritada tıklayarak düzeltiliyor.
- Çıktı her sahne için ayrı bir dosya ve istenirse sahnelerin geçişlerle birleştirildiği tek bir video. Arka plan koyu (MP4) ya da şeffaf (ProRes 4444 .mov) olabiliyor.
- Proje dosyaları (JSON) kaydediliyor ve açılıyor. Hazır gelen `ornek_florida` projesi bugünkü örnek videoyu görsel olarak aynen üretiyor.
- Format yalnızca 16:9, 1920x1080, 30 fps.

Kapsam dışı (sonraki sürümler): zaman çizelgesi editörü ve canlı oynatma, dikey/kare/4K format, ABD dışı ülkeler, Alaska ve Hawaii, sayısal değer + renk skalası modu, yeni sahne tipleri.

## 2. Klasör yapısı

```
anim/
  README.md              Türkçe kullanım kılavuzu (CLAUDE_CODE_ANIM_TASK.md'nin yerini alır)
  requirements.txt       numpy, matplotlib, shapely, imageio-ffmpeg, fastapi, uvicorn, openpyxl
  requirements-dev.txt   pytest, httpx
  kurulum.bat            .venv oluşturur, paketleri kurar
  baslat.bat             .venv\Scripts\python run_ui.py
  run_ui.py              veriyi hazırlar, boş port bulur, sunucuyu açar, tarayıcıyı açar
  engine/
    assets.py            veri ve font indirme, dosya yolları, FontProperties
    geo.py               eyalet tablosu, county geometrisi, Albers projeksiyonu, sınır birleştirme
    params.py            ayar tipleri ve doğrulama
    scene.py             Scene tanımı ve SceneContext
    framing.py           kamera çerçeveleme hesapları (saf fonksiyonlar)
    render.py            kare döngüsü, ffmpeg yazıcı, tek kare önizleme
    compose.py           sahneleri xfade geçişiyle birleştirme
    project.py           proje JSON yükle/kaydet/doğrula
    cli.py               arayüzsüz render ve kare alma
  scenes/
    __init__.py          REGISTRY: sahne id -> Scene
    state_map.py         eyalet haritası
    price_ladder.py      fiyat merdiveni
  app/
    server.py            FastAPI uçları
    jobs.py              render işi yöneticisi
    static/              index.html, style.css, js/*.js
  projects/ornek_florida.json
  tests/
  data/                  (git dışı) counties.json, fonts/, outlines/
  reference/             (git dışı) orijinal koddan alınan referans video ve kareler
  out/                   (git dışı) render çıktıları
```

Eski `scene_a.py`, `scene_b.py`, `scene_common.py`, `prep_data.py` ve `render_all.py` yeni yapı çalışıp referans karşılaştırması geçtikten sonra silinir. Orijinalleri git geçmişindeki ilk commit'te (`b2f3daf`) duruyor.

## 3. Sahne sözleşmesi

```python
@dataclass
class Scene:
    id: str                 # "state_map"
    title: str              # "Eyalet haritası" (arayüzde görünen ad)
    base_duration: float    # iç zamanlamaların yazıldığı süre (13.0 / 11.5)
    params: list[Param]
    setup: Callable[[SceneContext], Callable[[float], None]]
    bg_center: tuple[float, float]   # koyu arka plandaki ışık merkezinin konumu (ekran oranı)
```

- `setup(ctx)`: çizim nesnelerini kurar ve `update(t)` döndürür. `ctx` şunları içerir: `fig`, `ax`, doğrulanmış ayarlar (`ctx.p`), `transparent` ve fontlar.
- `update(t)`: `t` her zaman **temel süre** cinsindendir (0..base_duration). Kullanıcının seçtiği süreye göre ölçekleme `render.py`'de yapılır: `t_base = t_gercek * base_duration / duration`.
- Arka plan, şeffaflık, ffmpeg ve önizleme ölçeği sahnenin işi değildir.
- Her sahnenin ortak bir `duration` ayarı vardır. Alt sınırı temel sürenin 0,5 katı, üst sınırı 2 katıdır.

## 4. Ayar tipleri (`params.py`)

Her tip arayüz için bir JSON tanımı (`schema()`) ve bir `validate(value, all_values) -> value` fonksiyonu sağlar. Doğrulama hatasında alan adıyla birlikte `ParamError` fırlatır. Her ayarın bir `group` alanı vardır: Genel, Veri, Renkler, County boyama, Vurgu, Kamera veya Zaman.

| Tip | Değer | Arayüz kontrolü |
|---|---|---|
| `Text(multiline=False, auto=False)` | str. `auto=True` ise boş bırakılınca sahne yazıyı kendisi üretir | metin kutusu, boşsa gri "otomatik" ipucu |
| `Color` | `#rrggbb` | renk seçici |
| `Number(min, max, step)` | float | sayı kutusu |
| `Date` | `YYYY-MM-DD` | tarih seçici |
| `State` | eyalet kısaltması (`FL`) | açılır liste, 48 eyalet |
| `County(state_param, allow_none)` | county FIPS (5 hane) veya `null` | açılır liste, seçili eyaletin county'leri |
| `Categories(min=2, max=7)` | `[{key, label, color}]`, son eleman sabit `none` | satır listesi: etiket + renk, ekle/sil (`none` silinemez) |
| `CountyAssign(state_param, categories_param)` | `{fips: category_key}` | county boyama paneli + CSV/Excel içe aktarma |
| `PriceTable` | `[{date, price}]`, en az 2 satır, tarihler artan, fiyatlar > 0 | düzenlenebilir tablo, satır ekle/sil |
| `Money(optional)` | int veya `null` | sayı kutusu |

Eyalet değişince `County` ve `CountyAssign` değerleri geçersiz kalır. Arayüz onay sorup bunları temizler, sunucu doğrulaması da yabancı FIPS'leri reddeder.

## 5. Coğrafya (`geo.py`, `assets.py`)

- Kaynaklar eskisiyle aynı: plotly `geojson-counties-fips.json` (Sayım Bürosu kaynaklı) ve Google Fonts'tan Bebas Neue ile Barlow (Regular, SemiBold, Bold). Dosyalar `data/` altına indirilir.
- Eyalet tablosu `geo.py` içinde sabit durur: FIPS, kısaltma ve ad. 48 bitişik eyalet destekleniyor. DC arka plan haritasında çizilir ama seçilemez.
- County kimliği FIPS'tir (feature `id`, 5 hane). Görünen ad `NAME` alanıdır. Aynı eyalette aynı adı taşıyan birden fazla kayıt varsa (Virginia'daki bağımsız şehirler gibi) ada `LSAD` eklenir, örneğin "Richmond city".
- Arka plan sınırları: 48 eyalet county'lerden birleştirilip `simplify(0.01)` ile sadeleştirilir ve `data/outlines/_all_simplified.json` olarak saklanır. Seçili eyaletin sınırı sadeleştirilmeden bir kez hesaplanır ve `data/outlines/<FIPS>.json` dosyasına önbelleklenir. Eski kod Florida için tam bu mantığı uyguluyordu.
- Projeksiyon mevcut `albers()` fonksiyonu, parametreler aynı.
- Arayüz haritası için `geo.county_svg(state)` projekte edilmiş ve hafif sadeleştirilmiş SVG path'leri döndürür. Her kayıtta fips, ad ve path bulunur, y ekseni SVG için ters çevrilir.
- **County eşleme** (CSV/Excel içe aktarma) şu sırayla dener:
  1. 5 haneli FIPS ya da 3 haneli county kodu.
  2. Normalize edilmiş ad: küçük harf; "county", "parish", "city" ekleri atılır; "saint"/"st." ve "sainte"/"ste." eşitlenir; noktalama ve boşluk atılır.
  3. "ad + LSAD" biçimi.

  Eşleşmeyen ve birden fazla county'ye uyan satırlar ayrı listelerde döner.
- Kategori sütunu kategori `key` değeriyle ya da etiketle (büyük/küçük harf duyarsız) eşleşir.
- Dosya biçimi: ilk satır başlık satırıdır. County sütunu `county`, `name`, `fips` veya `ilce` adlarından biri, kategori sütunu `category`, `kategori` veya `signal` adlarından biri olabilir. Başlıklar tanınmazsa ilk iki sütun kullanılır. CSV'nin ayırıcısı `,`, `;` veya sekme olabilir ve otomatik algılanır. `.xlsx` dosyaları openpyxl ile okunur, ilk sayfa kullanılır.

## 6. Kamera çerçeveleme (`framing.py`)

Tüm hesaplar saf fonksiyonlardır ve kamera `[cx, cy, w]` (merkez ve görünür genişlik, projeksiyon birimi) olarak döner.

- `fit_region(bbox, region, aspect=16/9)`: eyaletin sınırlayıcı kutusunu ekranın `region = (x0, x1, y0, y1)` bölgesine sığdırır. Bölge ekran oranı cinsindendir, varsayılanı `(0.40, 0.96, 0.08, 0.94)`. Soldaki başlık ve açıklama alanı böylece boş kalır.
- Kullanıcı ince ayarları (Kamera grubu): `zoom` (1,0 = otomatik; büyüdükçe yaklaşır), `shift_x` ve `shift_y` (ekran genişliği oranı cinsinden kaydırma). Çerçeveye en son uygulanırlar.
- ABD görünümü: 48 eyaletin tamamına `box(pad=0.06)`, eski koddaki gibi.
- Vurgu (county) görünümü:
  - Genişlik `focus_zoom × eyalet_w`, varsayılanı 0,55. Sonuç, county'nin ekran genişliğinin %5'i ile %30'u arasını kaplayacağı şekilde sınırlanır.
  - County ekranda (0,56; 0,435) noktasına yerleşir. Bu değer orijinal Charlotte kadrajından türetildi.
- Etiket konumu, vurgu görünümündeki ekran oranlarıyla tanımlanır: sağa hizalı metin x=0,37'de, bağlantı çizgisinin köşesi x=0,38 ve y=0,542'de. Böylece county'nin eyaletteki yerinden bağımsız olarak etiket hep solda kalır.
- `ornek_florida` projesi `zoom`, `shift_x` ve `shift_y` değerlerini, üretilen kamera orijinal `CAM_FL` ile aynı olacak şekilde sabitler. Değerler uygulama sırasında hesaplanıp projeye yazılır.

## 7. Eyalet haritası sahnesi (`scenes/state_map.py`)

Temel süre 13,0 sn. İç zamanlamalar, çizim katmanları, renk paleti ve efektler (neon parıltı, sıralı boyama, Charlotte nabzı) `scene_a.py` ile aynıdır. Değişen tek şey sabit değerlerin ayarlardan gelmesidir.

| Ayar | Grup | Varsayılan (yeni sahne) |
|---|---|---|
| `state` | Genel | FL |
| `title` (auto) | Genel | boş: eyalet adı büyük harfle |
| `subtitle` | Genel | "" |
| `accent` | Renkler | #3ee6ff |
| `categories` | Renkler | eski 5 kategori (BUYERS PULLED BACK … NOT ENOUGH DATA) ve renkleri |
| `assign` | County boyama | {} |
| `focus` | Vurgu | null (vurgu yok) |
| `focus_name` (auto) | Vurgu | boş: "<AD> COUNTY" |
| `focus_sub` | Vurgu | "" |
| `focus_stat` | Vurgu | "" |
| `focus_zoom` | Vurgu | 0,55 |
| `zoom`, `shift_x`, `shift_y` | Kamera | 1,0 / 0 / 0 |
| `duration` | Zaman | 13,0 |

Davranış kuralları:

- **Başlık sığdırma:** `title` en fazla 150 pt ve ekran genişliğinin en fazla %34'ü kadar yer kaplar. Daha genişse font küçültülür. Aynı kural vurgu adına da uygulanır (en fazla 64 pt, en fazla %30).
- **Açıklama kutusu:** Kategori sayısı n > 5 olduğunda açıklama kutusunun üst satırı `0.30 + (n-5)*0.045` konumuna çıkar. Açıklama kutusunda `none` kategorisi de gösterilir.
- **İstatistik yazısının rengi:** `focus_stat`, vurgulanan county'nin kategori rengiyle yazılır. Orijinal videoda Charlotte "price" kategorisinde olduğu için rengi turuncuydu, bu kural onu korur. County `none` kategorisindeyse (koyu renk okunmaz) accent rengi kullanılır.
- **Vurgu yoksa** (`focus = null`): 9,0 sn'den sonra kamera eyalette kalır. Başlıklar kaybolmaz, nabız ve etiket aşaması atlanır.
- **Parçalı eyaletler:** Ana halka, en çok noktası olan halkadır. Diğer halkalar (adalar, Michigan'ın yukarı yarımadası) eski koddaki "isles" gibi sonradan belirir.
- **Boyama sırası:** County'ler kuzeyden güneye sıralı boyanır (eski `rank` mantığı).

## 8. Fiyat merdiveni sahnesi (`scenes/price_ladder.py`)

Temel süre 11,5 sn. Görünüm ve zamanlamalar `scene_b.py` ile aynıdır.

| Ayar | Grup | Varsayılan (yeni sahne) |
|---|---|---|
| `kicker` | Genel | "" |
| `title` (auto) | Genel | boş: "ONE HOUSE. <N> PRICE CUTS." (1–20 arası sayı İngilizce kelimeyle yazılır, üstü rakamla) |
| `subtitle` | Genel | "" |
| `history` | Veri | 2 örnek satır |
| `today` | Veri | proje oluşturulduğu gün |
| `paid`, `paid_year` | Veri | null |
| `paid_text` (auto) | Veri | boş: "OWNER PAID $310,000 IN 2017" biçimi |
| `diff_text` (auto) | Veri | boş: fark ≥ 0 ise "STILL +$X\nABOVE WHAT THEY PAID", değilse "NOW −$X\nBELOW WHAT THEY PAID" |
| `label_price`, `label_days`, `label_cuts` | Genel | ASKING PRICE / DAYS FOR SALE / PRICE CUTS |
| `accent` | Renkler | #3ee6ff |
| `duration` | Zaman | 11,5 |

Hesaplanan değerler:

- **Y ekseni:** `lo = min(fiyatlar ∪ {paid})`, `hi = max(fiyatlar)`, `R = hi - lo`, `ylim = (lo - 0,11R, hi + 0,15R)`. Tik aralığı 1-2-2,5-5 × 10^k serisinden, ylim içinde 3 ile 6 arasında tik düşecek en küçük değer seçilir. Etiket biçimi $300K, 1 milyon ve üstü için $1.2M. Örnek veride sonuç orijinal değerlere eşittir: 280K–620K aralığı, 300K…600K tikleri.
- **X ekseni:** tikler ilan ayı ("AUG 2024"), aradaki her 1 Ocak ("2025") ve "TODAY" noktalarına konur. Bir yıl tiki ilan ya da TODAY tikine eksen uzunluğunun %6'sından daha yakınsa atlanır.
- **Değişim etiketi:** düşüşte kırmızı "−$6K" (orijinaldeki gibi), artışta accent renginde "+$6K". 1 milyon ve üstü farklarda $1.2M biçimi kullanılır.
- **Alış fiyatı yoksa** alış çizgisi, yazısı ve fark oku gösterilmez.

## 9. Render motoru (`render.py`, `compose.py`)

- Figür 19,2×10,8 inç ve 100 dpi. Opak modda radyal degrade arka plan, orijinaldeki gibi `figimage` ile ve sahnenin `bg_center` noktası merkezli çizilir. Şeffaf modda degrade çizilmez, figür ve eksen zemini şeffaf kalır. Harita zemini, graticule ve yazılar her iki modda da çizilir.
- Kare sayısı `round(duration × 30)`, kare zamanı `i / 30`.
- **Opak çıktı:** `libx264`, `-crf 17 -preset medium -pix_fmt yuv420p`, `.mp4`. Orijinal ayarlarla aynı.
- **Şeffaf çıktı:** `prores_ks -profile:v 4444 -pix_fmt yuva444p10le`, `.mov`. matplotlib'in RGBA tamponu ön çarpımsız (straight alpha) olmalıdır, bu uygulama sırasında testle doğrulanır.
- **Önizleme:** `render_still(scene, params, t, dpi=50)` aynı figürü 50 dpi'da çizer ve 960x540 boyutunda, 1080p kareyle aynı yerleşimde bir PNG döndürür. `figimage` piksel koordinatında çalıştığı için degrade arka plan her zaman figürün gerçek piksel boyutunda üretilir (önizlemede 960x540).
- **İlerleme:** `on_progress(frame, total)` geri çağrısı.
- **Birleştirme:** `compose(paths, durations, transition=0.6, transparent)` ardışık `xfade=transition=fade` zinciri kurar. Ofsetler `sum(d[0..k]) - (k+1)×transition` formülüyle hesaplanır. Şeffaf modda zincir `yuva444p10le` formatında çalışır ve alfanın korunduğu testle doğrulanır. Alfa korunmazsa şeffaf birleşik çıktı geçişsiz uç uca eklemeye düşer ve README'de belirtilir.
- **CLI:**
  - `python -m engine.cli render <proje.json> [--out KLASOR] [--transparent] [--no-combined] [--no-separate] [--progress-json]`
  - `python -m engine.cli still <proje.json> --scene N --t SANIYE --out dosya.png`
  - `--progress-json` açıkken her satırda bir JSON olayı yazılır: `{"event":"progress","scene":i,"frame":f,"total":n}`, `{"event":"output","path":...}`, `{"event":"done"}` ya da `{"event":"error","message":...}`.
- **Çıktı yolu:** `out/<proje>/<YYYYMMDD-HHMMSS>/01_<sahne-id>.mp4 …` ve `birlesik.mp4` (şeffafta `.mov`). "Her sahne ayrı dosya" kapalıysa sahne dosyaları birleştirmeden sonra silinir.

## 10. Proje dosyası (`project.py`)

```json
{
  "version": 1,
  "name": "ornek_florida",
  "transition": 0.6,
  "output": {"separate": true, "combined": true, "transparent": false},
  "scenes": [
    {"type": "state_map", "enabled": true, "params": {"state": "FL", "...": "..."}},
    {"type": "price_ladder", "enabled": true, "params": {"...": "..."}}
  ]
}
```

- Proje dosyaları `projects/<ad>.json` olarak saklanır. Ad yalnızca harf, rakam, `_` ve `-` içerebilir.
- Yükleme sırasında `version` kontrol edilir. Bilinmeyen sürüm, bilinmeyen sahne tipi ya da geçersiz ayar anlaşılır bir hata mesajıyla reddedilir. Eksik ayarlar varsayılanla doldurulur.
- `ornek_florida.json` orijinal videonun bütün değerlerini içerir: county atamaları FIPS ile, Charlotte vurgusu ve yazıları, fiyat geçmişi, 310.000 $ / 2017 ve 2026-09-23.

## 11. Web sunucusu (`app/server.py`, `app/jobs.py`)

Sunucu yalnızca `127.0.0.1` adresini dinler. Port 8765'ten başlayarak ilk boş port seçilir.

| Uç | İş |
|---|---|
| `GET /` | `static/index.html` |
| `GET /api/scenes` | sahne tipleri ve ayar şemaları |
| `GET /api/states` | eyalet listesi |
| `GET /api/geo/{state}` | county SVG path'leri, fips, ad |
| `GET /api/projects` · `GET/PUT /api/projects/{ad}` | listele, aç, kaydet |
| `GET /api/projects/_new` | varsayılan iki sahneli yeni proje |
| `POST /api/validate` | proje → alan bazlı hata listesi |
| `POST /api/preview` | `{scene, params, t}` → `image/png` |
| `POST /api/import-assignments` | `{state, categories, filename, content_b64}` → `{assign, unmatched, ambiguous}` |
| `POST /api/render` | `{project}` → `{job_id}` (aynı anda tek iş; ikinci istek 409 döner) |
| `GET /api/jobs/{id}` | durum, sahne/kare ilerlemesi, çıktılar, hata ve son 20 log satırı |
| `POST /api/jobs/{id}/cancel` | işi durdurur, yarım kalan dosyaları siler |
| `GET /api/outputs/{yol}` | `out/` altındaki dosyayı servis eder (tarayıcıda oynatmak için) |
| `POST /api/open-folder` | `out/` altındaki bir klasörü Windows Gezgini'nde açar (`os.startfile`) |

- **Önizleme:** Önizlemeler sunucu sürecinde tek bir kilit altında sırayla çizilir, çünkü matplotlib iş parçacığı güvenli değildir. Coğrafi veri süreç içinde önbelleklenir. Aynı sahne ve aynı ayarlarla gelen isteklerde kurulmuş figür yeniden kullanılır, yalnızca `update(t)` çağrılır. Bu sayede kaydırma çubuğu hızlı çalışır.
- **Render işi:** `sys.executable -m engine.cli render <geçici proje> --progress-json` ayrı bir süreçte çalışır. Bir okuyucu iş parçacığı stdout'u satır satır işleyip iş durumunu günceller.
- **İptal:** Süreç sonlandırılır. ffmpeg alt süreci stdin kapanınca kendiliğinden çıkar.
- **Güvenlik:** Dosya yolları `out/` ve `projects/` dışına çıkamaz (yol normalize edilip kontrol edilir).

## 12. Arayüz (`app/static/`)

Derleme adımı yoktur. Düz HTML, CSS ve ES modülleri kullanılır. Koyu tema videonun renk dünyasıyla uyumludur. Arayüz dili Türkçedir.

Yerleşim, onaylanan taslaktaki gibidir:

- **Üst çubuk:** proje adı, kaydedilmemiş değişiklik işareti, Yeni / Aç / Kaydet düğmeleri.
- **Sol sütun:**
  - Sahne listesi: seç, aç/kapat, yukarı/aşağı taşı, sil, "Sahne ekle".
  - Seçili sahnenin ayarları: şemadan otomatik üretilir ve gruplara ayrılmış, açılıp kapanabilen bölümlerde gösterilir.
- **Sağ sütun:**
  - 16:9 önizleme ve altında zaman kaydırma çubuğu.
  - County boyama paneli (yalnızca `CountyAssign` ayarı olan sahnede görünür).
  - Render paneli.

Modüller:

- `api.js`: fetch sarmalayıcıları.
- `state.js`: proje durumu ve kaydedilmemiş değişiklik takibi.
- `form.js`: şemadan form kurar; her ayar tipi için bir kontrol üretir.
- `preview.js`:
  - Ayar değişikliğinden 500 ms sonra önizleme isteği gönderir. Yeni istek gelince eskisini `AbortController` ile iptal eder.
  - Kaydırma çubuğu hareket ettikçe istek atar.
- `countymap.js`:
  - SVG haritayı çizer. Kategori fırçası seçilip tıklanan ya da basılı tutup üzerinden geçilen county'ler boyanır.
  - Üzerine gelinen county'nin adı gösterilir.
  - "Temizle" düğmesi tüm atamaları `none` yapar.
  - CSV/Excel içe aktarma sonucunda eşleşmeyen satırlar listelenir.
- `pricetable.js`: tarih ve fiyat tablosu.
- `render.js`: çıktı seçenekleri, "Render al" düğmesi, ilerleme çubuğu (sahne i/n, yüzde), iptal. Biten dosyalar listelenir; MP4'ler panelde `<video>` ile oynatılır, "Klasörü aç" düğmesi vardır.

Hata gösterimi:

- Doğrulama hataları ilgili alanın altında kırmızı metin olarak görünür. Hata varken "Render al" düğmesine basılınca hataların listesi gösterilir ve render başlamaz.
- Önizleme hatası önizleme alanının üstünde metin olarak görünür.

## 13. Hata durumları

- **İlk açılışta veri yoksa:** `run_ui.py` veriyi indirir ve ilerlemeyi konsola yazar. İndirme başarısız olursa Türkçe bir açıklama ve README'deki elle indirme adımlarını gösterip çıkar.
- **Font eksikse:** render başlamadan açık bir hata verilir. Yedek fontla sessizce devam edilmez.
- **Render hatası:** iş "başarısız" durumuna geçer. Arayüz hatayı ve son log satırlarını gösterir.
- **Proje dosyası bozuksa:** açılmaz, hata mesajı gösterilir. Mevcut açık proje etkilenmez.
- **Port doluysa:** sıradaki port denenir (en fazla 20 deneme).

## 14. Test

- **Referans (uygulamanın ilk adımı):** Orijinal kod hiç değiştirilmeden çalıştırılır.
  - `reference/ornek_orijinal.mp4` üretilir, süre ve kare sayısı kaydedilir.
  - Sahne A'dan 2.0, 4.0, 6.0, 8.6, 10.5 ve 12.5. saniyelerin, sahne B'den 1.0, 5.0, 8.0 ve 10.5. saniyelerin kareleri `reference/` altına PNG olarak alınır.
  - Render süresi ölçülür.
- **Birim testleri (pytest):**
  - Ayar doğrulama.
  - Eyalet tablosu: 48 eyaletin her biri için county listesi ve sınır boş olmamalı.
  - County ad eşleme: "St. Lucie"/"Saint Lucie", "Miami-Dade County", FIPS, Virginia'da "Richmond" belirsizliği.
  - CSV/Excel okuma: ayırıcı algılama ve başlık tanıma.
  - Çerçeveleme: 48 eyaletin her birinde eyalet kutusu ekran bölgesinin içinde kalmalı; vurgu county'si ekranın %5–30'unu kaplamalı.
  - Fiyat merdiveni hesapları: örnek veride ylim ve tikler orijinalle aynı; x tikleri; değişim etiketleri; fark yazısı.
  - Birleştirme ofsetleri.
  - Proje kaydetme/açma turu ve sürüm kontrolü.
- **Duman testleri:**
  - `render_still` ile her iki sahne 5 farklı anda hatasız çizilmeli.
  - Eyalet haritası FL, TX, MI, RI, CA, NC ve VA (vurgu bir bağımsız şehir) eyaletlerinde çizilmeli.
  - Uzun başlık testi: "NORTH CAROLINA" ve "MASSACHUSETTS".
- **Görsel regresyon:** `ornek_florida` projesinin kareleri referans karelerle karşılaştırılır. Kare başına ortalama mutlak piksel farkı 1,5/255'in altında olmalı.
- **Entegrasyon (`-m slow`):**
  - CLI ile örnek proje render edilir. Birleşik video ≈ (717 kare, 23,9 sn) olmalı.
  - Şeffaf render: `.mov` dosyasından çözülen bir karede köşe pikselinin alfası 0, başlık yazısı üzerindeki pikselin alfası 255 olmalı. Aynı kontrol şeffaf birleşik çıktı için de yapılır.
- **API testleri (TestClient):** şemalar, eyaletler, geo, PNG dönen önizleme, doğrulama hataları, proje kaydet/aç, CSV içe aktarma, kısa bir projeyle render işi yaşam döngüsü ve iptal.
- **Elle arayüz kontrolü (tarayıcı paneli):**
  - Proje açılır, eyalet Texas yapılır, önizleme güncellenir.
  - County boyanır, CSV içe aktarılır.
  - Render alınır, video panelde oynatılır.

## 15. Başarı ölçütleri

1. `kurulum.bat` ardından `baslat.bat` çalıştırılınca arayüz tarayıcıda açılıyor.
2. `ornek_florida` projesinin render'ı orijinal videoyla görsel olarak aynı: regresyon testi geçiyor, süre ≈ 23,9 sn.
3. Başka bir eyalet (Texas) seçilip county'ler boyanınca, vurgu verilince ve render alınınca düzgün kadrajlı bir video çıkıyor.
4. Şeffaf çıktı gerçekten şeffaf.
5. Tüm pytest testleri geçiyor.
6. README FredPull'dan bahsetmiyor ve kurulum, kullanım ve sorun gidermeyi Türkçe anlatıyor.
