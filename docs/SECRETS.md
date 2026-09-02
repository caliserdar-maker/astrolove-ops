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
| `RCLONE_CONF_B64` | Base64 ile kodlanmis `rclone.conf` icerigi; uzak depolama baglantisini calisma aninda olusturur. |
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

## rclone OAuth istemcisi (NOT, 2 Eylul 2026)

- `RCLONE_CONF_B64` icindeki `gdrive` remote'u rclone'un PAYLASIMLI varsayilan
  OAuth istemcisiyle (proje 202264815644) yetkilendirilmis. Sonuclari:
  (1) Drive API dakikalik sorgu kotasi diger rclone kullanicilariyla ortak,
  yogun listeleme (`pin_media_perms.py --scan`) 403 "Quota exceeded" alir;
  (2) Google Docs API bu projede kapali, `start_here_append.py` 403 alir.
- Cozum: Google Cloud'da kendi projesi + OAuth istemcisi (Drive API ve Docs
  API acik), rclone remote'u `client_id`/`client_secret` ile yeniden
  yetkilendirilir, yeni `rclone.conf` base64'lenip secret guncellenir.
  Token degerleri yine yalniz secret'ta durur.
