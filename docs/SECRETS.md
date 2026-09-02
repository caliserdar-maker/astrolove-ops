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
