# Metricool API: zamanlama gövdeleri (IG, FB, Threads, TikTok, YouTube)

12 Eki 2026, oturum sosyal. Yalnız belge ve GET ile hazırlandı; Metricool'a gönderi YAZILMADI.
Token bu dosyada yok (Drive `TEMP/METRICOOL_TOKEN.json`, repo secret `METRICOOL_USER_TOKEN`).

Kaynaklar (hepsi `data/sosyal/kaynak/metricool/`):

- **[SW]** `METRICOOL_SWAGGER.json` (app.metricool.com/api/swagger.json, 3 Eki 2026)
- **[CSV]** `METRICOOL_CSV_YARDIM.html` (toplu CSV yardım sayfası; alan değerleri burada)
- **[API]** `METRICOOL_API_REHBER.html` (API rehberi)
- **[LIM]** `METRICOOL_API_SINIRLAMALAR.html` (ağ başına API sınırlamaları, 12 Eki 2026)
- **[GH]** `GITHUB_PAGES_LIMITS.html`, `GITHUB_LARGE_FILES.html` (docs.github.com, 12 Eki 2026)
- **[GET]** 12 Eki 2026 salt okuma koşusu (`metricool-oku.yml`, `HESAPLAR_20261012.json`)
- **[GÖZLEM]** Mevcut Pinterest gönderilerinin `GET /v2/scheduler/posts` yanıtı (`data/sosyal/pinterest/pin_baslik_20261012/HAM_LISTE.json`)

## 1. Bağlı hesaplar [GET]

Kaynak: `GET /admin/simpleProfiles` ve `GET /v2/settings/brands/6974606`. Marka AstroLoveArt (blogId 6974606, saat dilimi Europe/Istanbul).

| Ağ | Bağlı | Hesap | Not |
|---|---|---|---|
| Instagram | evet | astroloveart | connectionType FACEBOOK_LOGIN; `instagram-properties`: autopublishAllowed=true, hasBeenCreator=false |
| Facebook | evet | Astroloveart (sayfa 1331479546706857) | |
| Threads | evet | astroloveart | |
| TikTok | evet | @astroloveart | accountType **BUSINESS** |
| YouTube | evet | AstroLoveArt (UCFNSFjhxrV9IendgQL6uU1w) | |
| Pinterest | evet | astroloveart | BUSINESS |

## 2. Ortak gövde: `POST /v2/scheduler/posts?userId&blogId` (ScheduledPost) [SW]

Kimlik doğrulama: başlık `X-Mc-Auth: <userToken>`, sorgu parametreleri `userId` ve `blogId` [API].

| Alan | Tip | Kullanım | Durum |
|---|---|---|---|
| publicationDate | {dateTime, timezone} | `"2026-10-25T18:00:00"`, `"Europe/Istanbul"` | [SW] + [GÖZLEM] |
| text | string | Gönderi metni; YouTube'da açıklama olarak kullanıldığı varsayılıyor | [SW]; YouTube açıklama eşlemesi **doğrulanmadı** |
| providers | array<{network}> | Bir gövde birden fazla ağa gidebilir; ağ başına ayrı metin için ayrı gövde | [SW]; ağ adlarından yalnız `pinterest` gözlendi, `instagram/facebook/threads/tiktok/youtube` yazımı **doğrulanmadı** |
| media | array<string> | Herkese açık, süresi dolmayan URL; karuselde birden fazla öğe | [SW] + [GÖZLEM] (github.io URL). Rehber `{"mediaId": ...}` örneği veriyor, swagger URL dizisi diyor: API'de hangi biçimin geçerli olduğu **doğrulanmadı** |
| mediaAltText | array<string> | media ile aynı sırada | [SW]; ağlara iletildiği **doğrulanmadı** |
| firstCommentText | string | İlk yorum (FB'de Etsy linki) | [SW], [CSV] |
| videoThumbnailUrl | string | Kapak görseli URL'si (FB gönderi ve Reel, IG Reel, TikTok business, YouTube video) | [SW], [CSV] |
| videoCoverMilliseconds | int64 | Videodan kare seçerek kapak (IG Reel, Pinterest, TikTok) | [SW]; CSV'deki karşılığı "Video Cover Frame" |
| autoPublish | boolean | true | [SW] + [GÖZLEM] |
| draft | boolean | false = zamanla | [SW] + [GÖZLEM] |
| shortener | boolean | false | [SW] |

Medya hazırlığı [API]: "Media links must be public and must not expire: private or temporary URLs are skipped". İsteğe bağlı olarak `GET /actions/normalize/image/url?url=` URL'yi doğrulayıp Metricool deposuna taşır. Video için davranışı **doğrulanmadı**.

## 3. Ağ başına alanlar

### Instagram: `instagramData` [SW]

| Alan | Değer / not | Kaynak |
|---|---|---|
| type | `POST` (tek görsel ya da karusel), `REEL`, `TRIAL_REEL`, `STORY` | değerler [CSV] |
| showReelOnFeed | true (Reel akışta da görünsün) | [SW], [CSV] |
| isAiGenerated | AI etiketi (`is_ai_generated` olarak iletilir) | [SW] açıklaması |
| autoPublish | true | [SW] + [GÖZLEM] |
| collaborators, tags, productTags, carouselTags | kullanılmıyor | [SW] |
| audioName / audioConfiguration | Yalnız Reel; karusel ve tek görselde müzik yok | [SW], [LIM] |

Sınırlar [LIM]: karuselde en fazla 10 öğe; slayt başına ayrı metin yok; statik görselden Reel olmaz (gerçek video dosyası gerekir); en fazla 30 hashtag; yayınlanan gönderi düzenlenemez.
Karusel: `type=POST` ve 4 öğeli `media`. CSV'de bu, "Picture Url 1..10" ile yapılıyor; API'de **doğrulanmadı**.

### Facebook: `facebookData` [SW]

| Alan | Değer / not | Kaynak |
|---|---|---|
| type | `POST` (çok görselli dahil), `REEL`, `STORY` | değerler [CSV] |
| title | Yalnız video gönderisi ve Reel için başlık | [CSV] |
| firstCommentText (üst düzey) | Etsy linki | [CSV] |

Sınırlar [LIM]: bir gönderide en fazla 35 görsel; karusel reklam yok; gruplara doğrudan yayın yok.

### Threads: `threadsData` [SW]

| Alan | Değer / not | Kaynak |
|---|---|---|
| type | `POST` ya da `GHOST` | [SW] açıklaması |
| replyControl | Varsayılan `EVERYONE` | [SW] |
| allowedCountryCodes, isSpoiler | kullanılmıyor | [SW] |
| shareAsInstagramStory, instagramStoryTheme | **false** (IG'ye çift paylaşım olmasın) | [SW] |

Karusel ve video: ayrı bir tip alanı yok; `media` içeriğinden belirleniyor. Karuseldeki en fazla öğe sayısı Metricool belgesinde yok, **doğrulanmadı**. [LIM]: GIF ve anket yok.

### TikTok: `tiktokData` [SW]; hesap türü BUSINESS [GET]

| Alan | Değer / not | Kaynak |
|---|---|---|
| disableComment / disableDuet / disableStitch | false | [SW], [CSV] |
| isAigc | AI etiketi | [SW]; alan adının anlamı **doğrulanmadı** (açıklama yok) |
| commercialContentThirdParty / commercialContentOwnBrand | [CSV]'ye göre "personal accounts only"; hesap BUSINESS olduğu için büyük olasılıkla yok sayılır, **doğrulanmadı** | [SW], [CSV] |
| privacyOption | [CSV]'ye göre yalnız kişisel hesap; boş bırak | [CSV] |
| title, autoAddMusic, photoCoverIndex | Yalnız fotoğraf gönderisi; videoda boş | [CSV] |
| Kapak | `videoThumbnailUrl` (özel kapak yalnız Business hesapta) ya da `videoCoverMilliseconds` | [CSV], [LIM] |

Sınırlar [LIM]: metin üstü yazı, filtre ve Story yok; açıklamada satır sonu yok (paragraflar ayrılamıyor).

### YouTube Shorts: `youtubeData` [SW]

| Alan | Değer / not | Kaynak |
|---|---|---|
| title | En fazla 100 karakter | [CSV] |
| type | `SHORT` (ya da `VIDEO`) | [CSV] |
| privacy | `PUBLIC`, `PRIVATE` ya da `UNLISTED` | [CSV] |
| category | `EDUCATION` (Serdar kararı). Tam liste `GET /v2/scheduler/catalogs/youtube/categories` ucunda; okunmadı | [CSV], [SW] |
| madeForKids | false | [SW] |
| isAiGeneratedContent | Sentetik içerik bildirimi | [SW] |
| notifySubscribers | true | [SW], [CSV] |
| tags | array<string> | [SW] |
| playlistId | kullanılmıyor | [SW] |
| Açıklama | Ayrı alan yok; üst düzey `text` kullanılıyor | **doğrulanmadı** |

Sınırlar [LIM]: Shorts için özel kapak yüklenemez; yayınlanan videoda yalnız metadata düzenlenebilir.

## 4. Instagram'dan Facebook'a otomatik paylaşım

Metricool'da görünmüyor. `GET /v2/scheduler/posts/instagram-properties` yalnız `hasBeenCreator` ve `autopublishAllowed` alanlarını döndürüyor; swagger'da IG'den FB'ye paylaşımla ilgili alan yok.
Bu ayar Instagram uygulamasında, Hesaplar Merkezi altındaki "Facebook'ta paylaş" seçeneğinde duruyor. **Serdar kontrol etmeli**: IG Reel'i Metricool'dan ayrıca FB'ye de gönderilecekse bu otomatik paylaşım kapalı olmalı, yoksa aynı Reel FB'ye iki kez düşer.

## 5. Medya barındırma (GitHub Pages)

[GH] Pages sınırları:

- Yayınlanmış Pages sitesi en fazla **1 GB** olabilir.
- Kaynak repo için önerilen sınır 1 GB.
- Bant genişliğinin yumuşak sınırı ayda 100 GB.
- 50 MiB üstü dosyada uyarı verilir, 100 MiB üstü dosya engellenir.
- "GitHub Pages is not intended for ... a free web-hosting service to run your online business, e-commerce site ...": bu bir risk notudur.

Durum:

- **Görseller:** Uygun. Pin görselleri (234 adet, ~200-500 KB) ve IG karusel kareleri küçük.
- **Videolar (78 × 13-14 MB):** Dosya başına sorun yok (100 MiB altı). Ancak toplam yaklaşık 1,05 GB ve astrolove-media şimdiden yaklaşık 370 MB (GitHub API `size` 369518 KB). Tüm videolar yüklenirse yayınlanmış site 1 GB sınırını aşar. Bu yüzden Pages, tam video seti için **uygun değil**.
- **Öneri:** Videolar için kayan pencere. Yalnız önümüzdeki birkaç günün videoları Pages'te durur; Metricool gönderiyi oluşturup medyayı kendi deposuna aldıktan sonra (normalize ucu ya da gönderi oluşturma) dosya Pages'ten silinir. Medyanın gönderi oluşturulurken Metricool'a kopyalanıp kopyalanmadığı **doğrulanmadı**; ilk deneme gönderisinde ölçülmeli.
- **Alternatif:** Metricool'un kendi yükleme ucu `PUT /v2/media/s3/upload-transactions`. Rehberde anlatılmıyor, **doğrulanmadı**.

## 6. Örnek gövdeler (yazılmadı, yalnız şablon)

IG karusel (4 görsel):

```json
{
  "publicationDate": {"dateTime": "2026-10-25T18:00:00", "timezone": "Europe/Istanbul"},
  "text": "<ig_caption>",
  "providers": [{"network": "instagram"}],
  "media": ["https://caliserdar-maker.github.io/astrolove-media/instagram/v2/CANCER_LIBRA/C01.jpg",
            "https://.../C02.jpg", "https://.../C03.jpg", "https://.../C04.jpg"],
  "mediaAltText": ["<alt1>", "<alt2>", "<alt3>", "<alt4>"],
  "autoPublish": true, "draft": false, "shortener": false,
  "instagramData": {"type": "POST", "autoPublish": true, "isAiGenerated": false}
}
```

IG Reel:

```json
{
  "publicationDate": {"dateTime": "2026-10-26T03:00:00", "timezone": "Europe/Istanbul"},
  "text": "<ig_caption>",
  "providers": [{"network": "instagram"}],
  "media": ["https://.../REEL.mp4"],
  "videoCoverMilliseconds": 1000,
  "autoPublish": true, "draft": false,
  "instagramData": {"type": "REEL", "showReelOnFeed": true, "autoPublish": true, "isAiGenerated": false}
}
```

FB çok görselli gönderi ve FB Reel:

```json
{"text": "<fb_caption>", "providers": [{"network": "facebook"}], "media": ["...C01.jpg", "...C02.jpg", "...C03.jpg", "...C04.jpg"],
 "firstCommentText": "Find Cancer & Libra in our Etsy shop: https://www.etsy.com/listing/4570143815",
 "facebookData": {"type": "POST"}, "publicationDate": {"dateTime": "2026-10-25T18:05:00", "timezone": "Europe/Istanbul"}}
```

```json
{"text": "<fb_caption>", "providers": [{"network": "facebook"}], "media": ["...REEL.mp4"],
 "firstCommentText": "<etsy link>", "facebookData": {"type": "REEL", "title": "Cancer & Libra"},
 "publicationDate": {"dateTime": "2026-10-26T03:05:00", "timezone": "Europe/Istanbul"}}
```

Threads karusel ve video:

```json
{"text": "<metin>", "providers": [{"network": "threads"}], "media": ["...C01.jpg", "...C02.jpg", "...C03.jpg", "...C04.jpg"],
 "threadsData": {"type": "POST", "replyControl": "EVERYONE", "shareAsInstagramStory": false}}
```

```json
{"text": "<metin>", "providers": [{"network": "threads"}], "media": ["...REEL.mp4"],
 "threadsData": {"type": "POST", "replyControl": "EVERYONE", "shareAsInstagramStory": false}}
```

TikTok video (BUSINESS hesap):

```json
{"text": "<tiktok metni, satır sonu yok>", "providers": [{"network": "tiktok"}], "media": ["...REEL.mp4"],
 "videoThumbnailUrl": "https://.../KAPAK.jpg",
 "tiktokData": {"disableComment": false, "disableDuet": false, "disableStitch": false, "isAigc": false}}
```

YouTube Shorts:

```json
{"text": "<açıklama>", "providers": [{"network": "youtube"}], "media": ["...REEL.mp4"],
 "youtubeData": {"title": "Cancer & Libra Personalized Zodiac Couple Print | AstroLoveArt", "type": "SHORT",
                 "privacy": "PUBLIC", "category": "EDUCATION", "madeForKids": false,
                 "isAiGeneratedContent": false, "notifySubscribers": true,
                 "tags": ["cancerlibra", "zodiac couple", "couple gift", "personalized gift", "zodiac art"]}}
```

`isAiGenerated`, `isAigc` ve `isAiGeneratedContent` için değer Serdar kararıdır. Görseller AI sahne + gerçek poster içeriyor; Metricool'un AI etiketi sayfası (METRICOOL.md kaynak 16) ilgili.

## 7. Doğrulanmayanlar (ilk tek gönderilik denemede ölçülecek)

1. `providers.network` yazımı: pinterest dışındaki ağlar.
2. `media` biçimi: URL dizisi mi, `{mediaId}` mi?
3. YouTube açıklaması = `text`.
4. Threads karusel öğe sınırı.
5. TikTok `commercialContent*` alanlarının BUSINESS hesapta davranışı; `isAigc` anlamı.
6. Medyanın gönderi oluşturulurken Metricool'a kopyalanıp kopyalanmadığı (Pages'ten silme güvenliği).
7. YouTube kategori anahtar listesi.
8. `mediaAltText` alanının ağlara iletilip iletilmediği.
