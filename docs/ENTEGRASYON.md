# Harita Stüdyosu: Entegrasyon Rehberi

Bu belge, Harita Stüdyosu'nu bir iş akışına ya da başka bir yapay zeka ajanına bağlayacak kişiler için yazıldı. Aracın ne ürettiğini, nasıl sürüleceğini, girdilerin biçimini, çıktıları ve sınırları anlatır. Son kullanıcı kılavuzu [README.md](../README.md) dosyasındadır.

- **Sürüm:** v1 (2026-09-24). Proje dosyası şema sürümü: `1`.
- **Depo:** https://github.com/bemonths/harita-studyosu

## 1. Ne üretir?

ABD harita animasyonlarını video olarak üretir. Çıktı 1920x1080, 30 kare/sn, ses yok. İki sahne tipi var:

| Sahne tipi (`type`) | Ne gösterir | Temel süre |
|---|---|---|
| `state_map` | ABD'den seçilen eyalete inen kamera, neon sınır çizimi, kategorilere göre boyanan county'ler, açıklama kutusu, isteğe bağlı olarak vurgulanan bir county ve etiketi | 13 sn |
| `price_ladder` | Bir evin fiyat geçmişi (basamaklı çizgi), indirim etiketleri, fiyat/gün/indirim sayaçları, alış fiyatıyla karşılaştırma | 11,5 sn |

Bir **proje**, bu sahnelerden oluşan sıralı bir listedir. Her sahne ayrı video olarak alınabilir, sahneler geçişli (crossfade) tek videoda da birleştirilebilir. Arka plan koyu degrade (MP4, H.264) ya da şeffaf (MOV, ProRes 4444, alfa kanallı) olabilir.

## 2. Aracı sürmenin üç yolu

| Yol | Ne zaman |
|---|---|
| **A. Proje JSON dosyası + komut satırı** | Otomasyon için önerilen yol. Sunucu gerekmez, her çağrı bağımsız bir süreçtir. |
| **B. Yerel HTTP API** | Arayüzün kullandığı API. Önizleme PNG'si almak, iş kuyruğu mantığıyla render etmek ya da county listesi çekmek için. |
| **C. Python'dan doğrudan** | Aynı depo içinde Python kodu yazılıyorsa. |

Üçü de aynı doğrulama ve render motorunu kullanır. Aynı proje JSON'u her yolda aynı videoyu verir.

## 3. Kurulum

Platform Windows 10/11 ve Python 3.12. ffmpeg `imageio-ffmpeg` paketiyle birlikte gelir, ayrıca kurulmaz.

```powershell
git clone https://github.com/bemonths/harita-studyosu.git
cd harita-studyosu
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -c "from engine import assets; assets.ensure()"
```

Son komut county sınırlarını (yaklaşık 3 MB) ve dört yazı tipini `data/` altına indirir. İnternet yalnızca bu adımda gerekir. Geliştirme ve test için ek olarak `requirements-dev.txt` kurulur.

**Karakter kodlaması:** Windows'ta konsol kodlaması yerel ayara bağlıdır. Geliştirme bilgisayarında bu kodlama GBK idi ve Türkçe karakter basan Python kodu `UnicodeEncodeError` verdi. Motoru kendi Python kodunuzdan çağırırken ya da çıktısını okurken süreci `PYTHONUTF8=1` ortam değişkeniyle çalıştırın. `engine.cli`, `run_ui.py` ve `.bat` başlatıcıları bunu zaten kendileri ayarlar. JSON olayları her zaman UTF-8'dir.

## 4. Önerilen iş akışı

1. Veri adımınız her county için bir **kategori** üretir, örneğin "fiyatlar düşüyor" ya da "alıcılar çekildi". Fiyat merdiveni kullanılacaksa bir evin fiyat geçmişi de gerekir.
2. Bir proje JSON'u oluşturun. Başlangıç için `projects/ornek_florida.json` dosyasını ya da `GET /api/projects/_new` yanıtını şablon olarak kullanın (bkz. §5).
3. Render edin: `python -m engine.cli render proje.json --out CIKTI_KLASORU --progress-json` (bkz. §6).
4. `output` olaylarından dosya yollarını alın ve kurgu ya da yayın adımına verin.

Doğrulama render'dan önce otomatik yapılır. Hatalı bir alan varsa render başlamaz ve hangi sahnenin hangi alanının neden hatalı olduğu bildirilir.

## 5. Proje JSON şeması (sürüm 1)

```json
{
  "version": 1,
  "name": "florida_agustos",
  "transition": 0.6,
  "output": {"separate": true, "combined": true, "transparent": false},
  "scenes": [
    {"type": "state_map", "enabled": true, "params": { "...": "..." }},
    {"type": "price_ladder", "enabled": true, "params": { "...": "..." }}
  ]
}
```

| Alan | Kural |
|---|---|
| `version` | `1` olmalı. Başka bir değer yapısal hatadır. |
| `name` | `^[A-Za-z0-9_-]{1,60}$`. Varsayılan çıktı klasörünün adında kullanılır. |
| `transition` | Sahneler arası geçiş süresi (sn), 0–2 arası. 0 ise sahneler geçişsiz art arda eklenir. Birleşik video isteniyorsa açık sahnelerin en kısasından kısa olmalı. |
| `output.separate` | Her sahne ayrı dosya olarak kalsın mı. |
| `output.combined` | Açık sahneler tek videoda birleştirilsin mi. Tek sahne açıksa bu ayar yok sayılır. İki seçenekten en az biri `true` olmalı. |
| `output.transparent` | `true` ise arka plan şeffaf olur ve çıktı `.mov` (ProRes 4444) olarak yazılır. |
| `scenes[].type` | `state_map` ya da `price_ladder`. Bilinmeyen tip yapısal hatadır. |
| `scenes[].enabled` | `false` olan sahne render edilmez. En az bir sahne açık olmalı. |
| `scenes[].params` | Sahne ayarları. Eksik alanlar varsayılanla doldurulur. |

Güncel ayar listesi, varsayılanlar ve sınırlar makine tarafından okunabilir biçimde `GET /api/scenes` ucundan alınabilir. Python'da aynı bilgi `scenes.REGISTRY["state_map"].schema()` ile alınır.

### 5.1 `state_map` ayarları

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `state` | 48 bitişik eyaletin iki harfli kısaltması (`FL`, `TX`…). AK, HI, PR ve DC seçilemez. | `FL` | Kameranın indiği eyalet |
| `title` | metin, en fazla 200 karakter | `""` | Büyük başlık. Boşsa eyalet adı büyük harfle yazılır. Uzun başlık kendiliğinden küçültülür. |
| `subtitle` | metin | `""` | Başlığın altındaki satır |
| `accent` | `#rrggbb` | `#3ee6ff` | Neon sınır rengi |
| `categories` | 2–7 öğe: `{key, label, color}`. `key` `^[a-z0-9_]{1,20}$` ve benzersiz, `label` 1–40 karakter, `color` `#rrggbb`. **Son öğenin anahtarı `none` olmalı.** | 5 kategori (aşağıda) | Açıklama kutusu ve boyama renkleri. `none`, atanmamış county'lerin rengi ve etiketidir. |
| `assign` | `{ "<5 haneli FIPS>": "<kategori key>" }` | `{}` | County boyaması. FIPS seçili eyalete ait olmalı. Listede olmayan county'ler `none` sayılır. |
| `focus` | 5 haneli FIPS ya da `null` | `null` | Sahnenin sonunda yakınlaşılacak county. `null` ise kamera eyalette kalır. |
| `focus_name` | metin | `""` | Vurgu etiketi. Boşsa `<AD> <LSAD>` büyük harfle yazılır (ör. `CHARLOTTE COUNTY`). |
| `focus_sub` | metin | `""` | Etiketin altındaki küçük satır |
| `focus_stat` | metin | `""` | İstatistik satırı. Vurgulanan county'nin kategori renginde yazılır; county `none` ise `accent` renginde. |
| `focus_zoom` | 0,1–1,5 | 0,55 | Vurgu yakınlığı. Kadraj, county ekran genişliğinin %5–30'unu kaplayacak şekilde sınırlanır. |
| `zoom` | 0,5–2 | 1 | Eyalet kadrajı ince ayarı. 1 otomatik kadraj demektir, büyüdükçe yaklaşır. |
| `shift_x`, `shift_y` | −0,5–0,5 | 0 | Eyaleti ekran oranı kadar sağa ya da yukarı kaydırır. |
| `duration` | 6,5–26 sn | 13 | Sahne süresi. İç zamanlamalar orantılı ölçeklenir. |

Varsayılan kategoriler (`key` → `label`):

| key | label | renk |
|---|---|---|
| `buyers` | BUYERS PULLED BACK | `#ff5a4f` |
| `price` | PRICES BREAKING | `#ffb020` |
| `weak` | WEAKENING | `#e6d45a` |
| `stable` | HOLDING STEADY | `#3b6694` |
| `none` | NOT ENOUGH DATA | `#16233a` |

Zaman çizelgesi (13 sn temel süre):

| Saniye | Olay |
|---|---|
| 0,4–3,8 | ABD'den eyalete kamera inişi |
| 1,6–4,6 | Neon sınır çizimi |
| 4,6–5,8 | Başlık ve alt başlık belirir |
| 5,0–8,2 | County'ler kuzeyden güneye sırayla boyanır |
| 7,4–8,5 | Açıklama kutusu belirir |
| 9,0–11,2 | Vurgu county'sine yakınlaşma (vurgu varsa) |
| 9,6–12,0 | Vurgu nabzı, bağlantı çizgisi, etiket, alt yazı ve istatistik sırayla belirir |

### 5.2 `price_ladder` ayarları

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `kicker` | metin | `""` | En üstteki küçük renkli satır (ör. `LEE COUNTY  ·  FORT MYERS`) |
| `title` | metin | `""` | Büyük başlık. Boşsa `ONE HOUSE. <N> PRICE CUTS.` yazılır; N, düşüş sayısıdır. |
| `subtitle` | metin | `""` | Başlığın altındaki satır |
| `history` | En az 2 satır: `{date: "YYYY-MM-DD", price: int>0}`. Tarihler kesin artan, ardışık iki fiyat farklı olmalı. | 2 örnek satır | İlk satır ilan tarihi ve ilk fiyat, sonrakiler fiyat değişiklikleri. Artışlar da desteklenir. |
| `today` | `YYYY-MM-DD`, son `history` tarihinden önce olamaz | proje oluşturulduğu gün | Eksenin sonu ("TODAY") ve gün sayacı |
| `paid` | int ya da `null` | `null` | Sahibinin alış fiyatı. `null` ise alış çizgisi ve fark oku çizilmez. |
| `paid_year` | 1900–2100 ya da `null` | `null` | Alış yılı |
| `paid_text` | metin | `""` | Boşsa `OWNER PAID $310,000 IN 2017` biçiminde üretilir. |
| `diff_text` | metin, çok satırlı olabilir (`\n`) | `""` | Boşsa `STILL +$100,000\nABOVE WHAT THEY PAID` ya da `NOW −$X\nBELOW WHAT THEY PAID` üretilir. |
| `label_price`, `label_days`, `label_cuts` | metin | `ASKING PRICE`, `DAYS FOR SALE`, `PRICE CUTS` | Sağ paneldeki sayaç başlıkları |
| `accent` | `#rrggbb` | `#3ee6ff` | Çizgi rengi |
| `duration` | 5,75–23 sn | 11,5 | Sahne süresi |

Eksen aralığı, tik aralığı ve yıl etiketleri veriden kendiliğinden hesaplanır.

### 5.3 Hata biçimi

Doğrulama hataları şu biçimde bir listedir:

```json
[{"scene": 0, "param": "accent", "message": "#rrggbb biçiminde bir renk olmalı"}]
```

`scene`, `scenes` dizisindeki sıradır (0'dan başlar). Proje düzeyindeki hatalarda `scene` değeri `null`, `param` değeri `name`, `transition`, `output` ya da `scenes` olur.

## 6. Komut satırı

```powershell
.\.venv\Scripts\python -m engine.cli render PROJE.json [--out KLASOR] [--transparent | --opaque] [--no-combined] [--no-separate] [--progress-json]
.\.venv\Scripts\python -m engine.cli still  PROJE.json --scene 0 --t 8.6 --out kare.png [--dpi 100] [--transparent]
```

- Komutlar depo kökünden çalıştırılmalı, çünkü `python -m engine.cli` modülü çalışma klasöründe arar. Proje dosyası yolu göreli ya da mutlak olabilir.
- `--out` verilmezse çıktılar `out/<name>/<YYYYMMDD-HHMMSS>/` klasörüne yazılır.
- `--transparent`, `--opaque`, `--no-combined` ve `--no-separate` proje dosyasındaki `output` ayarlarını bu çağrı için geçersiz kılar.
- `still`, tek bir PNG kare üretir. `--dpi 100` 1920x1080, `--dpi 50` 960x540 verir. Küçük önizlemeler için kullanışlıdır.

**Çıkış kodları:** `0` başarılı, `1` doğrulama/veri/render hatası, `2` hatalı komut satırı argümanı.

**Çıktı dosya adları:**

| Dosya | Ne zaman |
|---|---|
| `01_state_map.mp4`, `02_price_ladder.mp4`… | Her açık sahne için, sıra numarasıyla. Şeffafta `.mov`. |
| `birlesik.mp4` (şeffafta `birlesik.mov`) | `combined` açıksa ve birden fazla sahne varsa |

`separate=false` ve `combined=true` ise sahne dosyaları birleştirmeden sonra silinir, yalnızca `birlesik.*` kalır.

**`--progress-json` olayları:** stdout'a her satırda bir JSON nesnesi yazılır.

```json
{"event": "log", "message": "indiriliyor: ..."}
{"event": "progress", "scene": 0, "scenes": 2, "frame": 120, "total": 390}
{"event": "compose"}
{"event": "output", "path": "C:\\...\\out\\florida_agustos\\20260924-101500\\birlesik.mp4"}
{"event": "done"}
{"event": "error", "message": "Projede hatalı ayarlar var: ..."}
```

`output` yolları mutlaktır. Başarılı çalıştırma `done` ile biter; başarısız çalıştırma `error` olayı yazar ve 1 koduyla çıkar. Genel ilerleme `(scene + frame/total) / scenes` formülüyle hesaplanabilir.

**Süre:** Render süresi işlemciye bağlıdır. Geliştirme bilgisayarında ölçülen değerler:

- 24 sn'lik örnek videonun opak render'ı (iki sahne + birleştirme): yaklaşık 2 dakika (117 sn).
- Aynı projenin şeffaf render'ı (yalnızca birleşik): yaklaşık 45 sn. Degrade arka plan çizilmediği için daha hızlı.
- Dosya boyutları: `01_state_map.mp4` 2,5 MB, `02_price_ladder.mp4` 0,7 MB, `birlesik.mp4` 3,3 MB, şeffaf `birlesik.mov` 8,4 MB.

Aynı anda birden fazla komut satırı süreci çalıştırılabilir. Her biri bir işlemci çekirdeğini büyük ölçüde doldurur.

## 7. Yerel HTTP API

```powershell
.\.venv\Scripts\python run_ui.py --port 8765 --no-browser
```

Sunucu yalnızca `127.0.0.1` adresini dinler ve kimlik doğrulaması yoktur. **Ağa açmayın.** `--port` verilmezse 8765'ten başlayarak ilk boş port seçilir. Hatalar `{"detail": {"message": "...", "errors": ...}}` biçiminde döner.

| Uç | Gövde / parametre | Yanıt |
|---|---|---|
| `GET /api/scenes` | | Sahne tipleri ve ayar şemaları (ad, tip, varsayılan, min/max, seçenekler) |
| `GET /api/states` | | `[{"abbr", "name", "fips"}]` (48 eyalet) |
| `GET /api/geo/{abbr}` | | `{"width", "height", "counties": [{"fips", "name", "d"}]}`. `d` bir SVG path'idir. County FIPS/ad listesi almak için de kullanılabilir. |
| `GET /api/projects` | | `{"projects": ["ornek_florida", ...]}` (`projects/` klasörü) |
| `GET /api/projects/_new` | | Varsayılan ayarlı iki sahneli yeni proje |
| `GET /api/projects/{name}` | | `{"project", "errors"}` |
| `PUT /api/projects/{name}` | proje JSON'u | Kaydeder: `{"saved", "errors"}` |
| `POST /api/validate` | proje JSON'u | `{"errors": [...]}` |
| `POST /api/preview` | `{"type", "params", "t", "transparent"}` | `image/png`, 960x540. Hatalı ayarda 422. |
| `POST /api/import-assignments` | `{"state", "categories", "filename", "content_b64"}` | `{"assign", "unmatched", "ambiguous"}` (bkz. §8) |
| `POST /api/render` | `{"project": {...}}` | `{"job_id"}`. Hatalı projede 422, süren başka iş varsa 409. |
| `GET /api/jobs/{id}` | | `{"state": "running" \| "done" \| "failed" \| "canceled", "phase", "scene", "scenes", "frame", "total", "percent", "outputs", "dir", "error", "log"}`. `outputs` ve `dir`, `out/` klasörüne göreli yollardır. |
| `POST /api/jobs/{id}/cancel` | | İşi durdurur, yarım dosyaları siler. |
| `GET /api/outputs/{yol}` | | `out/` altındaki dosyayı indirir. |
| `POST /api/open-folder` | `{"path"}` | Klasörü Windows Gezgini'nde açar (arayüz için). |

Sunucu aynı anda tek render işi çalıştırır. İş bilgileri bellekte tutulur; sunucu yeniden başlarsa iş geçmişi kaybolur ama dosyalar kalır.

## 8. County verisi ve eşleme

- **Kimlik:** County'ler 5 haneli FIPS koduyla tanımlanır: 2 hane eyalet + 3 hane county (ör. Charlotte County, FL = `12015`). Kaynak, ABD Sayım Bürosu verisinden türetilmiş plotly GeoJSON'udur.
- **Öneri:** Otomasyonda `assign` alanına doğrudan FIPS yazın; ad eşlemesine gerek kalmaz.
- **Adla eşleme (CSV/Excel içe aktarma):** Sırasıyla şunlar denenir:
  1. 5 haneli FIPS ya da 3 haneli county kodu.
  2. `"<ad> <LSAD>"` tam eşleşmesi (ör. `Richmond city`).
  3. Normalize edilmiş ad: büyük/küçük harf, `County`/`Parish`/`city`/`Borough` ekleri, `St.`/`Saint` farkı ve noktalama yok sayılır.
- **Aynı adlı county'ler:** Bazı eyaletlerde aynı adı taşıyan birden fazla kayıt var (Virginia'da Richmond, Fairfax, Bedford, Franklin, Roanoke; Missouri'de St. Louis; Maryland'de Baltimore). Bunlar "belirsiz" olarak döner; tam adla (`Richmond city` / `Richmond County`) ya da FIPS ile verilmeli.
- **CSV biçimi:** İlk satır başlıktır. County sütunu `county`, `name`, `fips` ya da `ilce`; kategori sütunu `category`, `kategori`, `signal` ya da `sinyal` olabilir. Başlıklar tanınmazsa ilk iki sütun kullanılır. Ayırıcı `,`, `;` ya da sekme olabilir. Kategori değeri, kategorinin `key` ya da `label` değeridir.

Python ile county listesi:

```python
from engine import geo
for c in geo.counties("12"):          # eyaletin FIPS kodu
    print(c.fips, c.name, c.lsad, c.display)
```

## 9. Python'dan doğrudan kullanım

```python
import json
from engine import assets, project
from engine.cli import run_render

assets.ensure()                                   # veri ve fontlar hazır mı
data = json.load(open("projects/ornek_florida.json", encoding="utf-8"))
data["scenes"][0]["params"]["assign"]["12071"] = "price"
clean, errors = project.validate(data)
if errors:
    raise SystemExit(errors)
paths = run_render(clean, "out/deneme", emit=lambda **ev: print(ev))
```

Depo kökü `sys.path` içinde olmalıdır. Tek kare için `engine.render.still_png(scene, params, t, transparent=False, dpi=50)` kullanılır.

## 10. Yeni sahne tipi eklemek (geliştiriciler için)

1. `scenes/<id>.py` dosyası oluşturun. İçinde `PARAMS` listesi, `setup(ctx)` fonksiyonu ve `SCENE = Scene(id=..., title=..., base_duration=..., params=PARAMS, setup=setup, bg_center=(x, y))` tanımı bulunsun.
2. `setup(ctx)` çizim nesnelerini `ctx.fig` üzerinde kurar ve `update(t)` döndürür. `ctx` içinde şunlar var: `p` (doğrulanmış ayarlar), `fonts` (`bebas`, `regular`, `semibold`, `bold`), `transparent` ve `dpi`.
3. `update(t)` için kurallar:
   - `t` her zaman temel süre cinsindendir; süre ölçeklemesini motor yapar.
   - **Durumsuz olmalıdır:** aynı `t` her zaman aynı kareyi vermeli. Önizleme zamanda geri gidebilir.
   - Arka planı çizmez; degradeyi ve şeffaflığı motor yönetir.
4. Sahneyi `scenes/__init__.py` içindeki `REGISTRY`'ye ekleyin. Arayüz formu ayar tiplerinden kendiliğinden oluşur.
5. Kullanılabilecek ayar tipleri (`engine/params.py`): `Text`, `Color`, `Number`, `Date`, `StateSelect`, `CountySelect`, `Categories`, `CountyAssign`, `PriceTable`.
6. Ayarlar arası kurallar için `Scene(check=...)` kullanın. Fonksiyon `{ayar_adı: hata_mesajı}` döndürür.

## 11. Testler

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest            # hızlı testler (~40 sn)
.\.venv\Scripts\python -m pytest -m slow    # tam video render testleri (~3 dk)
```

`tests/test_regression.py`, `ornek_florida` projesinin karelerini orijinal koddan alınan referans karelerle karşılaştırır. Referans kareler (`reference/`) depoya konmadı; klasör yoksa bu testler atlanır.

Referansları yeniden üretmek için:

1. Orijinal kodu ilk commit'ten (`b2f3daf`) ayrı bir klasöre çıkarın.
2. Orada `scene_a.py` dosyasını `TEST=2.0,4.0,6.0,8.6,10.5,12.5`, `scene_b.py` dosyasını `TEST=1.0,5.0,8.0,10.5` ortam değişkeniyle çalıştırın.
3. Oluşan `out/test_*.png` dosyalarını bu deponun `reference/` klasörüne kopyalayın.

## 12. Sınırlar

- Yalnızca 48 bitişik eyalet destekleniyor; Alaska, Hawaii, Porto Riko ve DC seçilemez. Ülke dışı haritalar yok.
- Format sabit: 16:9, 1920x1080, 30 kare/sn. Dikey ya da kare format yok.
- Video metinleri serbesttir ama yazı tipleri (Bebas Neue, Barlow) Latin alfabesi içindir.
- Arayüzdeki önizleme tek kare gösterir, oynatma yoktur.
- Şeffaf `.mov` dosyaları tarayıcıda oynatılmaz. Premiere, DaVinci Resolve ve Final Cut destekler.
- HTTP API kimlik doğrulaması içermez ve yalnızca yerel kullanım içindir.

## 13. Depo haritası

| Yol | İçerik |
|---|---|
| `engine/assets.py` | Veri ve font indirme, yollar |
| `engine/geo.py` | Eyalet tablosu, Albers projeksiyonu, eyalet/county geometrisi |
| `engine/importer.py` | CSV/Excel okuma, county eşleme |
| `engine/params.py` | Ayar tipleri ve doğrulama |
| `engine/framing.py` | Kamera kadrajları |
| `engine/scene.py` | `Scene` sözleşmesi ve yardımcılar |
| `engine/render.py` | Kare üretimi, ffmpeg ile video yazma, PNG önizleme |
| `engine/compose.py` | Sahneleri birleştirme |
| `engine/project.py` | Proje JSON doğrulama/yükleme/kaydetme |
| `engine/cli.py` | Komut satırı |
| `scenes/` | Sahne tanımları ve `REGISTRY` |
| `app/server.py`, `app/jobs.py` | HTTP API ve render işleri |
| `app/static/` | Arayüz (derleme adımı olmayan HTML/CSS/JS) |
| `projects/` | Proje dosyaları (`ornek_florida.json`) |
| `run_ui.py`, `kurulum.bat`, `baslat.bat` | Başlatıcılar |
| `docs/superpowers/` | Tasarım belgesi ve uygulama planı |
| `data/`, `out/`, `reference/` | Git dışı: indirilen veri, render çıktıları, test referansları |
