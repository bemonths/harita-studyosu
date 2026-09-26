# Harita Stüdyosu: Entegrasyon Rehberi

Bu belge, Harita Stüdyosu'nu bir iş akışına ya da başka bir yapay zeka ajanına bağlayacak kişiler için yazıldı. Aracın ne ürettiğini, nasıl sürüleceğini, girdilerin biçimini, çıktıları ve sınırları anlatır. Son kullanıcı kılavuzu [README.md](../README.md) dosyasındadır.

- **Sürüm:** v1.3 (2026-09-26): sekiz grafik ve vaat sahnesi (`question_board`, `county_quiz`, `house_bars`, `line_trend`, `bar_list`, `ring`, `thermometer`, `house_grid`; §5.5–5.13), yeni ayar tipleri `Choice` ve `ValueTable` (§10), marka rengi `neutral` (§3.1), örnek proje `projects/ornek_grafikler.json`. v1.2 (2026-09-24): metinlerde `$` işareti düz yazılır (§5), vurgusuz `state_map`'te yavaş yakınlaşma (§5.1), ortalı `county_focus` açılışı ve yeni etiket yerleşimi (§5.3). v1.1: marka dosyası (§3.1), `county_focus` sahnesi (§5.3), dosyadan proje yükleme (§4, §7). Proje dosyası şema sürümü: `1`.
- **Depo:** https://github.com/bemonths/harita-studyosu

## 1. Ne üretir?

ABD harita animasyonlarını ve veri grafiklerini video olarak üretir. Çıktı 1920x1080, 30 kare/sn, ses yok. On bir sahne tipi var:

| Sahne tipi (`type`) | Ne gösterir | Temel süre |
|---|---|---|
| `state_map` | ABD'den seçilen eyalete inen kamera, neon sınır çizimi, kategorilere göre boyanan county'ler, açıklama kutusu, isteğe bağlı olarak vurgulanan bir county ve etiketi | 13 sn |
| `county_focus` | Boyalı eyalet kadrajından anlatılan county'ye yakınlaşma, kenar nabzı ve etiket. Başlık ve açıklama kutusu yok. County bölümlerini açmak için. | 5 sn |
| `price_ladder` | Bir evin fiyat geçmişi (basamaklı çizgi), indirim etiketleri, fiyat/gün/indirim sayaçları, alış fiyatıyla karşılaştırma | 11,5 sn |
| `question_board` | Vaat ekranı: ortada başlık, altında 2–4 soru kartı (simge, nabızlı "?" içeren değer, açıklama) | 6 sn |
| `county_quiz` | County soru kartı: solda county sınırı, sağda 1–3 satır; değerler "?" olarak durur, sırayla açılır | 9,5 sn |
| `house_bars` | Ev biçimli sütunlar (ör. yıllara göre fiyat), vurgulanan sütun ve iki sütun arasında ok | 7 sn |
| `line_trend` | İniş çıkışlı çizgi ve ok, isteğe bağlı referans çizgisi (ör. 2019 düzeyi) | 7 sn |
| `bar_list` | Yatay ilerleme çubukları (2–10 satır), isteğe bağlı eşik çizgisi | 6,5 sn |
| `ring` | Dolan halka ve kalan dilim (ör. "$94 OF EVERY $100 ASKED", "$6 OFF") | 6 sn |
| `thermometer` | 1–3 tüp, alt ve üst eşik çizgileri (ör. aylık stok) | 6,5 sn |
| `house_grid` | Ev ızgarası: önce/sonra değerine göre simgeler söner ya da eklenir, sayaç | 7,5 sn |

Grafik sahneleri veriyi ayar olarak alır ve çizer; veriyi hesaplamak aracı süren tarafın (ör. FredPull) işidir. Arayüzden elle de doldurulabilirler.

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

Son komut county sınırlarını (yaklaşık 3 MB) ve `brand.json`'da tanımlı yazı tiplerini (varsayılan: Cinzel, Anton, Barlow SemiBold/Bold/Regular) `data/` altına indirir. İnternet yalnızca bu adımda gerekir. Geliştirme ve test için ek olarak `requirements-dev.txt` kurulur.

**Karakter kodlaması:** Windows'ta konsol kodlaması yerel ayara bağlıdır. Geliştirme bilgisayarında bu kodlama GBK idi ve Türkçe karakter basan Python kodu `UnicodeEncodeError` verdi. Motoru kendi Python kodunuzdan çağırırken ya da çıktısını okurken süreci `PYTHONUTF8=1` ortam değişkeniyle çalıştırın. `engine.cli`, `run_ui.py` ve `.bat` başlatıcıları bunu zaten kendileri ayarlar. JSON olayları her zaman UTF-8'dir.

### 3.1 Marka dosyası (`brand.json`)

Depo kökündeki `brand.json` kanalın renk paletini, varsayılan renk kategorilerini ve yazı tiplerini tanımlar. Yükleyici `engine/brand.py`'dir:

- Dosya süreç başına bir kez okunur. Değişiklikten sonra arayüzü ya da komut satırını yeniden başlatın.
- Dosya yoksa yerleşik varsayılanlar kullanılır. Eksik alanlar varsayılanlarla tamamlanır.
- Hatalı bir değer (geçersiz renk, `none` ile bitmeyen kategori listesi gibi) açık bir hata mesajıyla reddedilir.

| `colors` anahtarı | Varsayılan | Görevi |
|---|---|---|
| `bg_dark` / `bg_light` | `#07111d` / `#102338` | Arka plan degradesinin kenarı ve merkezi |
| `surface` | `#0e1c2e` | ABD'deki diğer eyaletlerin dolgusu. Vurgu sırasında soluklaşan county'ler bu rengin parlaklığından daha karanlığa inmez. |
| `line` | `#23405e` | Eyalet kenarları, enlem-boylam çizgileri, fiyat merdiveninin ızgara ve ayırıcı çizgileri |
| `text` | `#f4ecdd` | Başlıklar, yer adları, büyük sayaçlar |
| `muted` | `#a9b4c2` | Alt başlıklar, açıklama kutusu yazıları, eksen etiketleri, sayaç başlıkları |
| `accent` | `#ff7a1f` | Neon sınır, vurgulanan county'nin kenar parlaması, fiyat merdiveninin çizgisi ve üst satırı. Sahnelerdeki `accent` ayarının varsayılanıdır. |
| `loss` | `#e0301e` | İndirim noktaları ve etiketleri; güncel fiyat alış fiyatının altındaysa fark oku ve yazısı; grafik sahnelerinde düşüş ve eşiği aşan değerler |
| `neutral` | `#5b7fa6` | Grafik sahnelerinde karşılaştırma sütun ve çubuklarının nötr rengi |

`categories`, `state_map` ve `county_focus` sahnelerinin varsayılan renk kategorileridir; kuralları §5.1'deki `categories` ayarıyla aynıdır. Fiyat merdiveninde alış fiyatı çizgisi ve yazısı `price` kategorisinin rengini kullanır.

| `fonts` anahtarı | Varsayılan dosya | Görevi |
|---|---|---|
| `place` | `cinzel/Cinzel[wght].ttf` | Yer adları: eyalet başlığı, vurgulanan county adı |
| `numbers` | `anton/Anton-Regular.ttf` | Büyük rakamlar ve büyük başlıklar: fiyat merdiveninin başlığı ve üç sayacı |
| `label`, `label_bold`, `label_regular` | `barlow/Barlow-SemiBold.ttf`, `-Bold`, `-Regular` | Diğer bütün yazılar |

Yazı tipi yolları Google Fonts deposunun `ofl/` klasörüne göredir ve `assets.ensure()` tarafından indirilir. Sahnelerdeki yazı boyutları büyük harf yüksekliğine göre ayarlanır (`engine.scene.cap_scale`). Bu sayede farklı oranlara sahip bir yazı tipi seçildiğinde yerleşim bozulmaz.

## 4. Önerilen iş akışı

1. Veri adımınız her county için bir **kategori** üretir, örneğin "fiyatlar düşüyor" ya da "alıcılar çekildi". Fiyat merdiveni kullanılacaksa bir evin fiyat geçmişi de gerekir.
2. Bir proje JSON'u oluşturun. Başlangıç için `projects/ornek_florida.json` dosyasını ya da `GET /api/projects/_new` yanıtını şablon olarak kullanın (bkz. §5).
3. Render edin: `python -m engine.cli render proje.json --out CIKTI_KLASORU --progress-json` (bkz. §6).
4. `output` olaylarından dosya yollarını alın ve kurgu ya da yayın adımına verin.

Doğrulama render'dan önce otomatik yapılır. Hatalı bir alan varsa render başlamaz ve hangi sahnenin hangi alanının neden hatalı olduğu bildirilir.

**Projeyi arayüze vermek:** Proje JSON'u doğrudan `projects/<name>.json` olarak yazılabilir. Dosya adı, `name` alanıyla aynı olmalı. Arayüzdeki "Proje aç…" listesi her açılışta klasörü yeniden okur, bu yüzden yeni dosya sayfayı yenilemeden görünür. Başka bir yerden gelen dosya için arayüzdeki "Dosyadan yükle…" düğmesi ya da `POST /api/projects/import` ucu kullanılır (§7). Bu yollar dosyayı kaydetmeden önce doğrular.

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
| `scenes[].type` | §1'deki on bir tipten biri. Bilinmeyen tip yapısal hatadır. |
| `scenes[].enabled` | `false` olan sahne render edilmez. En az bir sahne açık olmalı. |
| `scenes[].params` | Sahne ayarları. Eksik alanlar varsayılanla doldurulur. |

**Metinler:** Bütün metin ayarları düz yazı olarak çizilir. `$` işareti matematik yazısı olarak yorumlanmaz, olduğu gibi görünür (ör. `BUYERS PAY $94 FOR EVERY $100 ASKED`).

Güncel ayar listesi, varsayılanlar ve sınırlar makine tarafından okunabilir biçimde `GET /api/scenes` ucundan alınabilir. Python'da aynı bilgi `scenes.REGISTRY["state_map"].schema()` ile alınır.

### 5.1 `state_map` ayarları

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `state` | 48 bitişik eyaletin iki harfli kısaltması (`FL`, `TX`…). AK, HI, PR ve DC seçilemez. | `FL` | Kameranın indiği eyalet |
| `title` | metin, en fazla 200 karakter | `""` | Büyük başlık. Boşsa eyalet adı büyük harfle yazılır. Uzun başlık kendiliğinden küçültülür. Başlık, alt başlık ve açıklama kutusundan oluşan sol blok ile eyalet sınırı arasında en az ekran genişliğinin %3'ü kadar boşluk kalır: gerekirse önce başlık en fazla %30 küçülür, yetmezse eyalet sağa kaydırılır (ekrana sığması için gerekirse biraz küçülür). |
| `subtitle` | metin | `""` | Başlığın altındaki satır |
| `accent` | `#rrggbb` | `brand.json` → `colors.accent` | Neon sınır ve vurgu parlaması rengi |
| `categories` | 2–7 öğe: `{key, label, color}`. `key` `^[a-z0-9_]{1,20}$` ve benzersiz, `label` 1–40 karakter, `color` `#rrggbb`. **Son öğenin anahtarı `none` olmalı.** | `brand.json` kategorileri (aşağıda) | Açıklama kutusu ve boyama renkleri. `none`, atanmamış county'lerin rengi ve etiketidir. Açıklama kutusunda yalnızca `assign` içinde kullanılan kategoriler (liste sırasıyla) ve en sonda `none` gösterilir. |
| `assign` | `{ "<5 haneli FIPS>": "<kategori key>" }` | `{}` | County boyaması. FIPS seçili eyalete ait olmalı. Listede olmayan county'ler `none` sayılır. |
| `focus` | 5 haneli FIPS ya da `null` | `null` | Sahnenin sonunda yakınlaşılacak county. `null` ise kamera eyalette kalır ve 8,5 sn'den sahne sonuna kadar eyalete çok yavaş (toplam %3) yaklaşır. |
| `focus_name` | metin | `""` | Vurgu etiketi. Boşsa `<AD> <LSAD>` büyük harfle yazılır (ör. `CHARLOTTE COUNTY`). |
| `focus_sub` | metin | `""` | Etiketin altındaki küçük satır |
| `focus_stat` | metin | `""` | İstatistik satırı. Vurgulanan county'nin kategori renginde yazılır; county `none` ise `accent` renginde. |
| `focus_zoom` | 0,1–1,5 | 0,55 | Vurgu yakınlığı. Kadraj, county ekran genişliğinin %5–30'unu kaplayacak şekilde sınırlanır. |
| `zoom` | 0,5–2 | 1 | Eyalet kadrajı ince ayarı. 1 otomatik kadraj demektir, büyüdükçe yaklaşır. |
| `shift_x`, `shift_y` | −0,5–0,5 | 0 | Eyaleti ekran oranı kadar sağa ya da yukarı kaydırır. |
| `duration` | 6,5–26 sn | 13 | Sahne süresi. İç zamanlamalar orantılı ölçeklenir. |

Varsayılan kategoriler (`brand.json`, `key` → `label`):

| key | label | renk |
|---|---|---|
| `buyers` | BUYERS PULLED BACK | `#e0301e` |
| `sellers` | SELLERS PULLING OUT | `#b5487a` |
| `price` | PRICES BREAKING | `#e9b949` |
| `weak` | WEAKENING | `#b89b72` |
| `stable` | HOLDING STEADY | `#3e6a8f` |
| `hot` | STILL HOT | `#3fa37a` |
| `none` | NOT ENOUGH DATA | `#152538` |

Proje dosyasında `categories` verilmezse bu liste kullanılır. `categories` verilirse o projeye özel liste geçerli olur.

Zaman çizelgesi (13 sn temel süre):

| Saniye | Olay |
|---|---|
| 0,4–3,8 | ABD'den eyalete kamera inişi |
| 1,6–4,6 | Neon sınır çizimi |
| 4,6–5,8 | Başlık ve alt başlık belirir |
| 5,0–8,2 | County'ler kuzeyden güneye sırayla boyanır |
| 7,4–8,5 | Açıklama kutusu belirir |
| 8,5–13,0 | Vurgu yoksa eyalete çok yavaş yakınlaşma (toplam %3); eyaletin ekrandaki merkezi yerinde kalır |
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
| `accent` | `#rrggbb` | `brand.json` → `colors.accent` | Fiyat çizgisi ve üst satır rengi |
| `duration` | 5,75–23 sn | 11,5 | Sahne süresi |

Eksen aralığı, tik aralığı ve yıl etiketleri veriden kendiliğinden hesaplanır. Ayrıca:

- **Zaman etiketleri:** İlan ayı ve TODAY her zaman yazılır. Aradaki yıl etiketlerinin piksel genişliği ölçülür; komşusuyla arasında 24 px'ten az boşluk kalan yıl etiketi atlanır (ör. ilan Kasım 2024 ise "2025" etiketi).
- **Değişim etiketleri:** Her değişimin noktası ayrı çizilir. Zaman ekseninde birbirine eksen uzunluğunun %6'sından yakın ardışık indirimler tek etikette birleşir ("5 CUTS −$25K"). Etiket grubun ilk indiriminin hizasında durur ve grubun son indirimi geçilince belirir. Artışlar birleşmez. İndirim sayacı birleşmeden etkilenmez.
- **Sayaç yanıp sönmesi:** Fiyat sayacı, her indirimden sonra en fazla 0,35 sn kırmızıya döner. Süre, çizgi başının konumuna değil geçen zamana bağlıdır; çizim bitince (sahnenin 8,4. saniyesi, temel süre) sayaç her zaman normal renktedir.
- **Fark yazısı:** Varsayılan yeri alış fiyatı ile güncel fiyatın ortası, grafiğin sağıdır. Orada fiyat çizgisinin dik bir bölümüne ya da bir değişim etiketine biniyorsa yazı onun soluna, arada en az 16 px kalacak şekilde kayar. Eksenden ya da alış yazısının üstüne taşarsa alış çizgisinin altına alınır.

### 5.3 `county_focus` ayarları

Videonun county bölümlerini açar. `state_map` gibi ABD'den inmez: eyalet kadrajında, county'ler boyalı ve neon sınır çizili olarak başlar, anlatılan county'ye yakınlaşır. Başlık ve renk açıklaması kutusu yoktur.

**Açılış kadrajı:** Eyalet ekranın ortasındadır; üstte ve altta en az %8, yanlarda en az %6 boşluk kalır (`engine/framing.py` → `CENTER_REGION`). Yakınlaşma bu kadrajdan başlar. `state_map`'teki sağa yaslı kadraj (sol blok için) burada kullanılmaz.

Ayarlar `state_map` ile aynı ad ve kurallara sahiptir (bkz. §5.1). Farklar şunlar:

| Ayar | Kural | Varsayılan |
|---|---|---|
| `state`, `accent`, `categories`, `assign` | §5.1 ile aynı | §5.1 ile aynı |
| `focus` | **Zorunlu.** Seçili eyalete ait 5 haneli FIPS; `null` ya da boş olamaz. | `null` (doldurulmalı) |
| `focus_name`, `focus_sub`, `focus_stat`, `focus_zoom` | §5.1 ile aynı. Ad `place` yazı tipiyle, istatistik county'nin kategori renginde yazılır. | §5.1 ile aynı |
| `zoom`, `shift_x`, `shift_y` | §5.1 ile aynı; ortalı açılış kadrajını ayarlar. Varsayılan değerler kuralı sağlar, değiştirilirse boşluklar değişir. | 1 / 0 / 0 |
| `duration` | 2,5–10 sn | 5 |
| `title`, `subtitle` | Bu sahnede yok | |

**Etiket yerleşimi** (`county_focus` ve `state_map`): Etiket bloğu (ad, alt yazı, istatistik) şu koşulları her zaman sağlar:

- Ekranın içinde, kenarlardan en az %3 boşlukla kalır.
- Vurgulanan county'nin sınır kutusuna 24 px'ten (1080p) fazla yaklaşmaz.
- County merkezinin dış tarafında durur, böylece bağlantı çizgisi yazıların üstünden geçmez.
- `state_map`'te vurgu sırasında ekranda kalan renk açıklaması kutusuna da 24 px'ten fazla yaklaşmaz.

Koşulları sağlayan yerler (county'nin solu ya da sağı, yukarı ya da aşağı kaydırılmış) arasından eyaletin karasına en az binen seçilir: önce su, sonra eyalet dışı. Komşu eyaletlerin karası %25 ağırlıkla sayılır. Yazılar kıyı çizgisine yapışmasın diye kara ölçülürken bloğa 16 px pay eklenir. Yakın durumlarda varsayılan yere (county merkezinin ekran genişliğinin %19'u kadar solu ya da sağı, biraz yukarısı) yakın olan kazanır. Başlangıç tarafı `county_focus`'ta etiket bölgesinin eyaletle daha az örtüştüğü taraftır (`engine/framing.py` → `label_side`), `state_map`'te soldur. Diğer tarafa geçmek küçük bir ceza alır ve kamera da aynalanır. Örneğin `county_focus`'ta, Florida'da St. Lucie, Miami-Dade ve Highlands'ta etiket Atlantik'e, Lee, Charlotte, Pasco ve Polk'ta Meksika Körfezi'ne, Walton'da county'nin altına düşer. Suda ya da eyalet dışında yer yoksa etiket karaya konur; yazılardaki kontür okunurluğu korur.

Blok hiçbir yere sığmazsa sırayla şunlar denenir:

1. İstatistik satırı en fazla %25 küçültülür.
2. İstatistik iki satıra bölünür.

Son çare olarak sığmayan satır küçültülür. Kısa metinlerde (ör. örnek projedeki Charlotte) etiket varsayılan yerinde kalır. Kural `scenes/maplib.py` içindeki `MapLayers.place_label` ve `MapLayers._search` metotlarındadır, ağırlıklar dosyanın başındaki sabitlerdir. Etiket yazılarında (ad, alt yazı, istatistik) `bg_dark` renginde yaklaşık 4 px kontür vardır; harita üstüne düştüklerinde de okunurlar.

**Soluklaşma:** Vurgu sırasında diğer county'ler renk tonunu korur; doygunlukları %55, parlaklıkları %50 azalır. Kırmızı ve altın zemin rengine karışıp çamurlaşmaz.

**Odak noktası:** Kamera hedefi, bağlantı çizgisi ve nokta, county'nin en büyük parçasının içinde kenarlardan en uzak noktayı kullanır (`engine/framing.py` → `focus_point`, polylabel). Köşe ortalaması girintili kıyılarda ya da çok parçalı county'lerde (ör. Charlotte, Monroe, Keweenaw) county dışına düşüyordu.

**İstatistik rengi:** İstatistik satırı county'nin kategori rengindedir. Kategori rengi koyuysa (HSV parlaklığı 0,65'ten azsa, ör. `stable` `#3e6a8f`) yazı, kategori rengiyle `text` renginin %45 karışımıyla ve en az 0,65 parlaklıkla yazılır. County dolgusu ve kenar parlaması değişmez.

**Kategorisiz odak:** Vurgulanan county `none` ise kenar parlaması ve istatistik `accent` rengindedir. Dolgusu da odak sırasında %30 opaklıkta `accent` ile boyanır, böylece koyu zeminde kaybolmaz.

Zaman çizelgesi (5 sn temel süre):

| Saniye | Olay |
|---|---|
| 0,0–0,4 | Ortalı eyalet kadrajı, county'ler boyalı, neon sınır çizili, hareket yok |
| 0,4–2,2 | Kamera vurgulanan county'ye yakınlaşır; diğer county'ler zemine doğru soluklaşır (0,6–1,6) |
| 1,8–2,6 | County'nin kenar nabzı başlar, bağlantı çizgisi uzar |
| 2,4–3,0 | County adı ve alt yazı belirir |
| 3,0–3,6 | İstatistik satırı county'nin kategori renginde belirir |
| 3,6–5,0 | Tutma; nabız sürer |

### 5.4 Hata biçimi

Doğrulama hataları şu biçimde bir listedir:

```json
[{"scene": 0, "param": "accent", "message": "#rrggbb biçiminde bir renk olmalı"}]
```

`scene`, `scenes` dizisindeki sıradır (0'dan başlar). Proje düzeyindeki hatalarda `scene` değeri `null`, `param` değeri `name`, `transition`, `output` ya da `scenes` olur.

### 5.5 Grafik sahnelerinin ortak kuralları ve ayarları

Sekiz grafik sahnesi (`question_board`, `county_quiz`, `house_bars`, `line_trend`, `bar_list`, `ring`, `thermometer`, `house_grid`) için geçerlidir. Görsel referans ve prototipler: `docs/referans_grafikler/` (bkz. `OKU.md`).

- **Oranlar gerçektir.** Sütun ve çubuklar sıfırdan başlar; boyları değerle doğru orantılıdır (`house_bars`'ta boy çatı tepesine kadar ölçülür). Görsel etki için ölçek abartılmaz. Tam boyun değeri (`max_value`) en büyük satırdan küçük olamaz.
- **Yüzde işareti yok.** Kanal kuralı: oranlar `44 OF 100`, `3 IN 10`, `$94 OF EVERY $100` gibi yazılır. Bu sahnelerin metin alanlarında ve tablo etiketlerinde `%` doğrulama hatası verir (render başlamaz).
- **Soru işaretleri** (`?`) vurgu renginde ve ±%6 genlikle, saniyede 0,9 kez nabız gibi atar. `->` ya da `→` yazı tipinde olmadığı için çizilmiş bir ok olarak gösterilir.
- **Para biçimi** (`money_k`): değerler dolar olarak verilir (`419000` → `$419K`, `1250000` → `$1.2M`). Adet biçimi (`count`): `4,771`. Farklarda eksi işareti U+2212'dir (`−$55K`).
- Renk ve yazı tipleri `brand.json`'dan gelir: yer adları `place`, büyük rakamlar `numbers`, etiketler `label_bold`/`label`. Hareket: sahne başında tek bir giriş sırası (başlık 0–0,5 sn), ardından değerlerin açılışı.
- Şeffaf dışa aktarımda zemin (`backdrop`) katmanı da çizilir; istenmiyorsa `none` seçilir.

Ortak ayarlar (sekizinde de var; arayüzde "Başlık" ve "Zemin" grupları):

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `heading` | metin | sahneye göre | Sol üstte yer adı (`place`), ör. `LEE COUNTY`. `question_board`'da ortada büyük başlık, `county_quiz`'de county sınırının altında. |
| `title` | metin | sahneye göre | Başlığın altındaki kalın satır, ör. `WHAT A TYPICAL HOME SOLD FOR` |
| `subtitle` | metin | sahneye göre | İnce açıklama satırı. `county_quiz`'de şehirler, `house_grid`'de sonuna birim eklenir (`EACH HOUSE = 100 HOMES`). |
| `source` | metin | sahneye göre | Sol altta kaynak satırı; boşsa çizilmez. |
| `callout_value` | metin | sahneye göre | Sağ üstte büyük rakam, ör. `−$59K`; boşsa çizilmez. |
| `callout_label` | metin | sahneye göre | Büyük rakamın altındaki satır. Rakamın taban çizgisinin 14 px altından başlar, üst üste binmez. |
| `callout_color` | `#rrggbb` | `loss` (`line_trend`'de `accent`) | Büyük rakamın rengi |
| `backdrop` | `none` / `county` / `state` | `none` | `county`: sağ yarıda çok soluk (dolgu %6, kenar %15) büyük county sınırı; `fips` gerekir. `state`: ortada soluk eyalet sınırı. |
| `state` | 48 eyaletin kısaltması | `FL` | `fips` ve kartlardaki county'lerin eyaleti; `state` zemininde çizilen eyalet |
| `fips` | seçili eyaletin 5 haneli FIPS'i ya da `null` | sahneye göre | Zemin için county; `county_quiz`'de soldaki county sınırı |
| `duration` | temel sürenin 0,5–2 katı | temel süre | Bütün zamanlamalar orantılı ölçeklenir (`county_quiz`'deki açılış anları hariç, onlar gerçek saniyedir). |

Kullanılmayan ortak ayarlar: `question_board`'da `title` başlığın altında ortalanır; `county_quiz`'de `title` ve `callout_*` çizilmez (sağ taraf satırlara ayrılmıştır); `house_grid`'de `callout_*` çizilmez (sağ üst köşe sayaca ayrılmıştır).

Metin ayarlarında satır sonu yoktur; sığmayan satırlar küçültülür. County sınırları simgelerde ve zeminde yerel eşdikdörtgen projeksiyonla çizilir (harita sahnelerindeki Albers'tan farklı olarak dik durur).

### 5.6 `question_board` (vaat ekranı, 6 sn)

Ortada `heading` (ör. `FLORIDA`), altında `subtitle` (ör. `10 COUNTIES  ·  4 QUESTIONS`). Altında 2–4 kart yan yana; kart sayısına göre ortalanır. Kartlar 0,6. saniyeden başlayarak 0,8 sn arayla, 40 px aşağıdan yükselerek belirir.

| Ayar (k = 1..4) | Tip / kural | Anlamı |
|---|---|---|
| `cardk_icon` | `house` / `county` / `houses10` / `none` | Kartın simgesi: büyük ev, county sınırı (turuncu, parıltılı), 2x5 ev ya da yok |
| `cardk_fips` | seçili eyaletin FIPS'i ya da `null` | `county` simgesi için zorunlu |
| `cardk_value` | metin, en fazla 40 karakter | Büyük satır. `?` vurgu renginde ve nabızlı, `->` ok. **Boşsa kart çizilmez**; en az iki kart dolu olmalı. |
| `cardk_caption` | metin, en fazla 60 karakter | Açıklama, en fazla iki satır; satır sonu için ` / ` (ör. `ONE HOUSE IN / FORT MYERS`) |

### 5.7 `county_quiz` (county soru kartı, 9,5 sn)

Solda county sınırı (`fips`, turuncu ve parıltılı), altında `heading` ve `subtitle` (şehirler). Sağda 1–3 satır kartı; satırlar 0,4. saniyeden 0,25 sn arayla belirir. Her satırın değeri açılış anına (`rowk_reveal`) kadar `?` olarak durur.

| Ayar (k = 1..3) | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `rowk_kind` | `counter` / `in10` / `compare` / `none` | 1: `counter`, 2: `in10`, 3: `compare` | `none`: satır çizilmez. En az bir satır olmalı. |
| `rowk_label` | metin | `HOMES FOR SALE` … | Satır başlığı |
| `rowk_note` | metin | `AUGUST 2026` … | Sol alttaki küçük satır |
| `rowk_value` | sayı ≥ 0 | 9351 / 3 / 360000 | Değer. `in10`'da 0–10 arası tam sayı. |
| `rowk_value2` | sayı ya da `null` | `compare`: 415000 | Yalnız `compare`: karşılaştırılan değer (ör. zirve); `compare`'de zorunlu |
| `rowk_value2_label` | metin | `2022 PEAK` | Karşılaştırılan değerin etiketi |
| `rowk_value_label` | metin | `TODAY` | Değerin etiketi (`compare`) |
| `rowk_format` | `count` / `money_k` | `count` / `money_k` | Değer biçimi |
| `rowk_decimals` | 0 ya da 1 | 0 | Yalnız `counter` ve `count` biçimi: ondalık basamak (ör. `6.2` ay) |
| `rowk_prefix` | metin, en fazla 5 karakter | `""` | Yalnız `counter`: sayının öneki (ör. `$` → `$94`) |
| `rowk_reveal` | sayı ≥ 0, **gerçek saniye** | 3,4 / 5,0 / 6,6 | Açılış anı. Sahne süresinden büyükse satır soru olarak kalır (bölümün başında yalnız soruyu göstermek için). |

Açılışta: `counter` sıfırdan değere 1 sn'de sayar ve ev simgesi yanar; `in10` on ev simgesinden değer kadarı kırmızıya döner ve `N IN 10` yazar; `compare` ev biçimli ikinci sütun karşılaştırılan değerin boyundan değerin boyuna gerçek oranla iner (büyük olan değer 126 px), sağda fark kendiliğinden yazılır (`−$55K`; değer büyükse `+` ve vurgu rengi).

### 5.8 `house_bars` (ev sütunları, 7 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `bars` | ValueTable, 2–10 satır, değer ≥ 0 | Lee 2019–2026 | Sütunlar; etiket genelde yıl |
| `value_format` | `money_k` / `count` | `money_k` | Sütun üstündeki değer biçimi |
| `arrow_from`, `arrow_to` | satır etiketi ya da ikisi de boş | `2022`, `2026` | Bu iki sütunun ve aradakilerin tepesinin 110 px üstünden, değer yazılarının üstünden geçen ok. Uç, baştan sonraki bir sütun olmalı. |
| `arrow_color` | `#rrggbb` | `loss` | Ok rengi |
| `highlight_color` | `#rrggbb` | `price` kategori rengi (altın) | İşaretli (`highlight`) satırın rengi |
| `after_color` | `#rrggbb` | `loss` | İşaretli satırdan sonraki sütunların rengi |

Renk kuralı: işaretli satırdan öncekiler `neutral`, işaretliler `highlight_color`, sonrakiler `after_color`. İşaret yoksa hepsi `neutral`, sonuncusu `accent`. Böylece "zirveden düşüş" (zirve altın, sonrası kırmızı) ve "dipten yükseliş" (`highlight_color` nötr, `after_color` turuncu) aynı sahneyle çizilir. Zaman: sütunlar 0,5. saniyeden 0,3 sn arayla büyür; ok son sütundan sonra (en erken 3,4. sn) 1 sn'de çizilir; ok bitince büyük rakam belirir.

### 5.9 `line_trend` (çizgi ve ok, 7 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `points` | ValueTable, 3–15 satır, değer ≥ 0 | Osceola 2016–2026 | Noktalar. Etiketlerin hepsi dört haneli yılsa ve 6'dan fazlaysa aradakiler iki haneye kısalır (`2016, 17 … 2026`). |
| `value_format` | `count` / `money_k` | `count` | |
| `ref_value` | sayı ya da `null` | 2075 | Kesikli yatay referans çizgisi |
| `ref_label` | metin | `2019 LEVEL: 2,075` | Çizginin sağ ucunda; çizgiyle çakışmayan tarafta (üst ya da alt) |
| `mark_min` | `yes` / `no` | `yes` | En düşük noktanın değeri altında küçük yazı |
| `axis_from_zero` | `yes` / `no` | `yes` | `no` ise eksen yuvarlak bir değerden başlar ve `AXIS STARTS AT …` yazar |

Çizgi 0,7–4,2 sn arasında soldan sağa çizilir, ucunda ok başı; geçilen noktalarda nokta belirir. Son değer 4,3. saniyede son noktanın üstünde büyük yazıyla, büyük rakamla birlikte belirir.

### 5.10 `bar_list` (çubuk listesi, 6,5 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `rows` | ValueTable, 2–10 satır, değer ≥ 0 | Pasco / Florida / ABD | Çubuklar |
| `max_value` | sayı > 0, en büyük satırdan küçük olamaz | 100 | Tam boyun değeri |
| `value_suffix` | metin | ` OF 100` | Değerin arkasına eklenir; boş olabilir |
| `decimals` | 0 ya da 1 | 0 | |
| `threshold` | sayı ya da `null`, `max_value`'dan büyük olamaz | `null` | Bu değeri aşan satırlar `loss`; kesikli dikey çizgi |
| `threshold_label` | metin | `""` | Eşik çizgisinin üstünde (ör. `BUYER'S MARKET: 6+ MONTHS`) |

2–4 satırda büyük yerleşim (satır aralığı 190 px, çubuklar 0,6 sn arayla), 5–10 satırda sıkı yerleşim (64 px, 0,18 sn arayla). Renk: işaretli satır `accent`, eşiği aşan `loss`, diğerleri `neutral`. Çubukların arkasında soluk tam boy iz (`line`) vardır.

### 5.11 `ring` (halka, 6 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `value` | sayı ≥ 0, `max_value`'dan büyük olamaz | 94,3 | Dolum |
| `max_value` | sayı > 0 | 100 | Tam halka |
| `center_prefix` | metin | `$` | Ortadaki sayının öneki |
| `center_label` | metin | `OF EVERY $100 ASKED` | Sayının alt satırı |
| `remainder_value` | metin | `""` | Boşsa `<önek><kalan> OFF` (ör. `$6 OFF`) |
| `remainder_label` | metin | `AT THE TABLE` | Kalanın alt satırı |

Halka 0,8–3,0 sn arasında saat 12 yönünden saat yönünde dolar, ortadaki sayı sayar. 3,1. saniyede kalan dilim `loss` renginde yanar, 3,4. saniyede kalan yazısı belirir.

### 5.12 `thermometer` (termometre, 6,5 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `tubes` | ValueTable, 1–3 satır, değer ≥ 0 | Highlands 6,2 / Florida 4,7 | Tüpler |
| `max_value` | sayı > 0 | 8 | Tüpün tam boyu |
| `unit_label` | metin | `MONTHS` | Değerin altındaki birim |
| `decimals` | 0 ya da 1 | 1 | |
| `low_value`, `low_label` | sayı ya da `null`; metin | 3, `SELLER'S MARKET: UNDER 3` | Alt eşik (nötr kesikli çizgi) |
| `high_value`, `high_label` | sayı ya da `null`; metin | 6, `BUYER'S MARKET: OVER 6` | Üst eşik (`loss`); bu değeri aşan tüp kırmızı dolar. Alt eşikten büyük olmalı. |

Eşik etiketleri çizgilerin sağında ve her zaman kadrajın içindedir (sığmazsa küçültülür). Tüpler 0,8. saniyeden 0,8 sn arayla dolar; değer tüpün yanında sayar.

### 5.13 `house_grid` (ev ızgarası, 7,5 sn)

| Ayar | Tip / kural | Varsayılan | Anlamı |
|---|---|---|---|
| `before`, `after` | tam sayı ≥ 0 | 3625, 2705 | Önceki ve sonraki değer |
| `unit` | tam sayı ≥ 1 ya da `null` | `null` | Bir simgenin temsil ettiği ev. Boşsa 10/25/50/100/200/500/1000… serisinden simge sayısını 20–48 arasında tutan en küçük değer. En fazla 60 simge çizilir. |
| `before_label`, `after_label` | metin | `AUGUST 2025`, `AUGUST 2026` | Sayacın altındaki dönem |
| `result_text` | metin | `""` | Boşsa `920 FEWER HOMES FOR SALE` / `… MORE …`; etiketler aynı ayın ardışık iki yılıysa sonuna ` IN ONE YEAR` eklenir. |

Önce `before/unit` kadar simge belirir ve sağ üstteki sayaç `before`'u gösterir. 2,4. saniyeden itibaren fark kadar simge teker teker (en çok 0,28 sn arayla, toplam 2,5 sn içinde) değişir: azalışta her satırın sağ ucundan, alt satırdan başlayan bir merdivenle kırmızıya döner ve sönükleşir; artışta yeni simgeler vurgu renginde eklenir (mevcutlar nötr). Sayaç `after`'a iner ya da çıkar, dönem etiketi değişir. 5,2. saniyede sonuç yazısı. Alt yazıda birim açıkça yazar (`EACH HOUSE = 100 HOMES`).

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
| `POST /api/projects/import?overwrite=false` | proje JSON'u | Doğrular ve `projects/<name>.json` olarak kaydeder: `{"saved", "project"}`. Dosya olduğu gibi yazılır; eksik alanlar dondurulmaz. Hatalı projede 422 (`detail.errors`), yapısal hatada 400. Aynı ad varsa 409 (`detail.name`); `overwrite=true` ile üzerine yazar. |
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
2. `setup(ctx)` çizim nesnelerini `ctx.fig` üzerinde kurar ve `update(t)` döndürür. `ctx` içinde şunlar var: `p` (doğrulanmış ayarlar), `fonts` (`place`, `numbers`, `label`, `label_bold`, `label_regular`), `transparent` ve `dpi`. Renkleri sabit yazmayın, `engine.brand.colors()` ile alın. Büyük yazılarda boyutu `engine.scene.cap_scale(fig, font)` çarpanıyla ayarlayın.
3. `update(t)` için kurallar:
   - `t` her zaman temel süre cinsindendir; süre ölçeklemesini motor yapar.
   - **Durumsuz olmalıdır:** aynı `t` her zaman aynı kareyi vermeli. Önizleme zamanda geri gidebilir.
   - Arka planı çizmez; degradeyi ve şeffaflığı motor yönetir.
4. Sahneyi `scenes/__init__.py` içindeki `REGISTRY`'ye ekleyin. Arayüz formu ayar tiplerinden kendiliğinden oluşur.
5. Kullanılabilecek ayar tipleri (`engine/params.py`): `Text`, `Color`, `Number`, `Date`, `StateSelect`, `CountySelect`, `Categories`, `CountyAssign`, `PriceTable`, `Choice`, `ValueTable`.
   - `Choice` (`kind: "choice"`): `options` listesi `((değer, etiket), ...)`; şemada `[{"value", "label"}]`. Değer listede olmalı. Arayüzde açılır liste.
   - `ValueTable` (`kind: "value_table"`): satırlar `{"label": str, "value": sayı, "highlight": bool}`. Seçenekler `min_rows`, `max_rows`, `integer`, `lo` (en küçük değer; şemada `min`). Etiket boş olamaz, en fazla 24 karakter, `%` içeremez; değer sonlu bir sayı olmalı (`true`/`false` sayı sayılmaz); `highlight` verilmezse `false`. Arayüzde satır ekle/sil ve işaret kutusu olan tablo (`app/static/js/valuetable.js`).
   - `Text(no_percent=True)`: `%` içeren metni reddeder. Grafik sahnelerinin bütün metin ayarları böyledir (`scenes.chartlib.T`).
   - Grafik sahnesi yazarken ortak ayarlar, başlık bloğu, büyük rakam, zemin, ev simgesi/sütunu, parıltılı county, nabızlı `?` ve çizilen ok için `scenes/chartlib.py` kullanılır.
6. Ayarlar arası kurallar için `Scene(check=...)` kullanın. Fonksiyon `{ayar_adı: hata_mesajı}` döndürür.

## 11. Testler

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest            # hızlı testler (~40 sn)
.\.venv\Scripts\python -m pytest -m slow    # tam video render testleri (~3 dk)
```

`tests/test_regression.py`, `ornek_florida` projesinin karelerini `reference/` klasöründeki referans karelerle karşılaştırır. Kare başına ortalama piksel farkı 1,5/255'in altında olmalı. Referans kareler depoya konmadı; klasör yoksa bu testler atlanır.

Referanslar marka görünümüyle (`brand.json`) üretildi. Marka öncesi orijinal kodun kareleri, geliştirme bilgisayarında `reference/orijinal/` altında saklanıyor.

Görünüm bilerek değiştiğinde referansları yeniden üretin:

```powershell
.\.venv\Scripts\python -m tests.make_reference
```

Komut yeni kareleri önce gözle kontrol için `out/referans_kontrol/` klasörüne, sonra `reference/` klasörüne yazar. Eski referanslar silinmez, `reference/eski_<tarih-saat>/` klasörüne taşınır.

`projects/ornek_grafikler.json` (on grafik sahnesi, Florida verisi, prototiplerdeki değerler) için de referans kareler vardır (`test_g0_…` – `test_g9_…`). Yalnız bu seti yeniden üretmek için `python -m tests.make_reference grafikler` (`ornek_florida` referanslarına dokunmaz). Grafik sahnelerinin testleri `tests/test_charts.py`'dedir: varsayılanlarla doğrulama, başta/ortada/sonda kare, durumsuzluk, şeffaf kipte alfa, sütun/çubuk boylarının değerle orantılı olması (%1 tolerans), `%` kuralı, `county_quiz`'de süreden sonra açılan satırın soru kalması.

## 12. Sınırlar

- Yalnızca 48 bitişik eyalet destekleniyor; Alaska, Hawaii, Porto Riko ve DC seçilemez. Ülke dışı haritalar yok.
- Format sabit: 16:9, 1920x1080, 30 kare/sn. Dikey ya da kare format yok.
- Video metinleri serbesttir ama varsayılan yazı tipleri (Cinzel, Anton, Barlow) Latin alfabesi içindir.
- Arayüzdeki önizleme tek kare gösterir, oynatma yoktur.
- Şeffaf `.mov` dosyaları tarayıcıda oynatılmaz. Premiere, DaVinci Resolve ve Final Cut destekler.
- HTTP API kimlik doğrulaması içermez ve yalnızca yerel kullanım içindir.

## 13. Depo haritası

| Yol | İçerik |
|---|---|
| `brand.json`, `engine/brand.py` | Marka paleti, varsayılan kategoriler, yazı tipleri |
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
| `scenes/` | Sahne tanımları ve `REGISTRY`. `scenes/maplib.py`, `state_map` ile `county_focus`un ortak harita katmanlarıdır; `scenes/chartlib.py` sekiz grafik sahnesinin ortak parçalarıdır. |
| `app/server.py`, `app/jobs.py` | HTTP API ve render işleri |
| `app/static/` | Arayüz (derleme adımı olmayan HTML/CSS/JS) |
| `projects/` | Proje dosyaları (`ornek_florida.json`, `ornek_grafikler.json`) |
| `docs/referans_grafikler/` | Grafik sahnelerinin görsel referansı: prototip görüntüleri ve betikleri (`vaad.py`, `grafikler.py`) |
| `run_ui.py`, `kurulum.bat`, `baslat.bat` | Başlatıcılar |
| `docs/superpowers/` | Tasarım belgesi ve uygulama planı |
| `data/`, `out/`, `reference/` | Git dışı: indirilen veri, render çıktıları, test referansları |
