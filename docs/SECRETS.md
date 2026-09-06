# Sirlar (Secrets)

Bu dosya yalnizca **gereken sirlarin listesini** icerir. Hicbir gercek deger
buraya yazilmaz. Degerler GitHub reposunda
`Settings > Secrets and variables > Actions` altinda, lokalde ise
versiyonlanmayan bir `.env` dosyasinda tutulur.

| Sir | Aciklama |
| --- | --- |
| `ETSY_API_KEY` | Etsy uygulamasinin genel API anahtari (keystring); API isteklerini uygulamaya baglar. |
| `ETSY_SHARED_SECRET` | Etsy uygulamasinin gizli anahtari; OAuth token degisimi ve imzalama icin kullanilir. |
| `ETSY_REFRESH_TOKEN` | KULLANILMAZ (1 Eyl 2026 karari). Etsy OAuth token zinciri Drive'daki `ASTROLOVE/TEMP/ETSY_TOKEN.json` dosyasindan yurur; asagidaki "Etsy token sahibi" bolumune bakin. Secret silinene kadar yalnizca tarihsel kayittir. |
| `ETSY_SHOP_ID` | Islem yapilacak Etsy magazasinin sayisal kimligi. |
| `RCLONE_CONF_B64` | Base64 ile kodlanmis `rclone.conf` icerigi (remote `gdrive`, kendi OAuth istemcimizle yetkilendirilmis, 2 Eyl 2026). Icindeki `client_secret` satiri bayattir; gecerli secret `GOOGLE_CLIENT_SECRET` ile calisma aninda ezilir. |
| `GOOGLE_CLIENT_SECRET` | Kendi Google OAuth istemcimizin (proje `gen-lang-client-0835100486`) guncel secret'i. Her rclone kosusunda `RCLONE_CONFIG_GDRIVE_CLIENT_SECRET` olarak ortama yazilir ve conf'daki degeri ezer; secret Console'da sifirlaninca yalniz bu deger guncellenir, conf'a dokunulmaz. |
| `GDRIVE_ROOT_FOLDER_ID` | Dosyalarin yazilacagi Google Drive kok klasorunun kimligi. |
| `OPS_ADMIN_TOKEN` | Fine-grained GitHub PAT (astrolove-ops + astrolove-media; Secrets/Variables/Contents/Actions/Workflows RW, 1 yil). Tum otomasyon yetkisi buradan: `gh_secrets.py` secret/variable yazar, `ig-media-sync` medya reposuna push eder. HER IKI repoda da tanimli olmali. Tek elle kurulan sir budur (asagiya bakin). |

## Repo degiskenleri (Variables, sir degil)

| Degisken | Aciklama |
| --- | --- |
| `IG_PUBLISH_ENABLED` | `true` olmadikca `ig-publish`'in zamanlanmis (06:00 UTC) kosusu atlanir. Yayina gecis karari bu degiskenle verilir; elle tetikleme `dry_run` varsayilani ile her zaman calisir. |

## Otomasyon kurali (KARAR, 2 Eylul 2026)

- GitHub/Drive/Console'da elle is yapilmaz. Secret ve variable'lar
  `scripts/common/gh_secrets.py` ile (libsodium sealed box, GitHub REST)
  yazilir; bu script Actions runner icinde `OPS_ADMIN_TOKEN` ile calisir.
- ISTISNA (kacinilmaz): `OPS_ADMIN_TOKEN`'in kendisi bir kez tarayicidan
  girilir. Otomasyonu yetkilendiren ilk kimlik, yetkilendirdigi otomasyonla
  kurulamaz. Ayrica Claude Code sandbox proxy'si `api.github.com/.../actions/*`
  yollarini (secrets, variables) engeller; bu yuzden sohbetten API ile secret
  yazilamaz, yalniz Actions icinden yazilir.
- Instagram kimligi secret DEGILDIR: Drive `TEMP/ig_token.json`
  ({"token","ig_id","expiry"}). `publish.py` dosyayi rclone ile okur, 60
  gunluk token bitise 10 gunden az kaldiysa `refresh_access_token` ile
  yeniler ve dosyaya geri yazar (Etsy token modeliyle ayni: tek kaynak,
  geri yazma zorunlu, tek yazici = concurrency grubu).

## Kurallar

- Gercek degerler asla depoya commit edilmez; `.gitignore` `.env`,
  `rclone.conf` ve `*.json` token dosyalarini haric tutar.
- Sir degeri degistiginde once GitHub Secrets guncellenir, sonra ilgili
  workflow yeniden calistirilir.
- Yeni bir sir eklendiginde bu tabloya tek satirlik aciklamasiyla eklenir.

## Etsy token sahibi (KARAR, 1 Eylul 2026)

- Etsy OAuth2 refresh token'inin TEK KAYNAGI Drive'daki
  `ASTROLOVE/TEMP/ETSY_TOKEN.json` dosyasidir. Etsy her yenilemede yeni bir
  refresh token dondurur ve eskisini gecersiz kilar; bu yuzden token zinciri
  yalniz tek bir yerde tutulabilir.
- Workflow'lar dosyayi rclone ile okur, access token'i yeniler ve donen yeni
  refresh token'i ayni dosyaya GERI YAZAR. Geri yazmayan bir kosu zinciri
  koparir.
- `ETSY_REFRESH_TOKEN` GitHub secret'i kullanilmaz; hicbir workflow bu
  secret'i okumaz. Colab veya baska bir ortamdan ayni dosya disinda bir
  token ile Etsy'ye baglanilmaz.
- `ETSY_API_KEY` (keystring) ve `ETSY_SHARED_SECRET` sabittir ve GitHub
  Secrets'ta kalir. Etsy v3 `x-api-key` basligi `keystring:shared_secret`
  bicimindedir.
- `ETSY_SHOP_ID` sabittir ve GitHub Secrets'ta kalir.
- Ayni anda yalnizca TEK Etsy kosusu calisir (concurrency grubu); iki kosu
  ayni dosyayi paralel yenilerse biri gecersiz token ile kalir.
- Not: Drive TEMP'te `etsy_tokens.json` adli ikinci, eski bir dosya daha
  vardir (9 Agu tarihli OAuth kurulumundan). Gecerli dosya `ETSY_TOKEN.json`
  olanidir; eski dosya karistirilmamalidir.

## rclone OAuth istemcisi (KARAR, 2 Eylul 2026)

- `gdrive` remote'u artik KENDI Google Cloud projemizin OAuth istemcisiyle
  yetkilendirilmis (proje `gen-lang-client-0835100486`; Drive, Docs ve
  Sheets API acik; scope `drive` + `documents` + `spreadsheets`, offline
  refresh token). rclone'un paylasimli istemcisi kullanilmiyor; ortak kota
  ve Docs API blokaji ortadan kalkti.
- Kurulum tek seferlik `google-oauth-bootstrap` workflow'u ile yapildi ve
  workflow sonra silindi: GitHub `workflow_dispatch` girdilerini loga acik
  yazdigi icin `client_secret` run loguna dusmustu; log silindi, secret
  Console'da sifirlandi, yeni deger `GOOGLE_CLIENT_SECRET` olarak eklendi.
  DERS: sir hicbir zaman workflow girdisi olarak verilmez; yalniz GitHub
  Secrets uzerinden gelir.
- Refresh token `client_id`'ye baglidir, secret'a degil. Secret rotasyonunda
  yeniden yetkilendirme GEREKMEZ: Console'da sifirla, `GOOGLE_CLIENT_SECRET`
  secret'ini guncelle, bitti. `RCLONE_CONF_B64` degismez.
- Her workflow'un `rclone.conf olustur` adimi `GOOGLE_CLIENT_SECRET`'i
  `$GITHUB_ENV` uzerinden `RCLONE_CONFIG_GDRIVE_CLIENT_SECRET` olarak
  yayar; boylece adimlardaki ve Python'dan cagrilan tum rclone komutlari
  guncel secret'i kullanir.
- Gecici dosya `ASTROLOVE/TEMP/rclone_new_b64.txt` (yeni conf'un base64'u)
  secret guncellendikten sonra Drive'dan silinir; sir iceren dosya Drive'da
  birakilmaz.

## Instagram yayin hatti (2 Eylul 2026)

- `WA_IG_PLAN` sheet'i `ig-publish` tarafindan rclone.conf'daki OAuth
  kimligiyle (Plan A) okunur ve yazilir; Sheets icin ayri secret yoktur.
- Tekrar yayin korumasi: durum sutunu (`ST_REEL`/`ST_CAR`/`ST_STORY`) bos
  degilse o tur atlanir. Yayindan ONCE `PENDING <ts>` yazilir, container
  olusunca id eklenir, sonra `OK <media_id> <ts>` ya da `ERR <sebep> <ts>`.
  `media_publish` hicbir zaman yeniden denenmez. `PENDING` kalmis hucre
  otomatik acilmaz; container_id ile Graph API'den bakilip elle temizlenir.
- Ayni cift + ayni medya daha erken gunde OK ise `SKIP_DUP D<NN>` yazilir
  (plandaki D79 = D01 tekrari).
- Carousel medyasi sheet'teki SLIDE_URLS'den degil,
  `astrolove-media/carousel_v2/D<NN>/slide_1..5.jpg` yolundan turetilir;
  `ig-media-sync` bu dosyalari Drive'dan Pages reposuna tasir.

## Prodigi anahtari (6 Eylul 2026)

Prodigi Print API anahtari GitHub secret'i DEGILDIR; Etsy token modeliyle Drive'da
durur: `ASTROLOVE/TEMP/PRODIGI_TOKEN.json` (`{"api_key": "..."}`). `prodigi-quote`
workflow'u dosyayi rclone ile okur, `::add-mask::` ile maskeler ve cikti dosyalarinda
sizinti kontrolu yapar (anahtar bulunursa dosya silinir, kosu hata verir). Anahtar
hicbir loga, dosyaya, commit'e ve workflow girdisine yazilmaz. Yerel deneme icin
yalniz `PRODIGI_API_KEY` ortam degiskeni kabul edilir.
