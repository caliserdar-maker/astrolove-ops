# astrolove-ops

AstroLove otomasyon scriptleri.

Bu depo, AstroLove icin Etsy, Instagram ve Pinterest tarafindaki tekrarli
islerin otomasyonunu barindirir. Scriptler GitHub Actions workflow'lari
uzerinden veya lokalde elle calistirilabilir.

## Klasor yapisi

| Yol | Icerik |
| --- | --- |
| `scripts/etsy/` | Etsy API scriptleri (listeleme, siparis, envanter) |
| `scripts/instagram/` | Instagram scriptleri: `build_carousel.py` (5 slaytlik carousel uretimi), `publish.py` (gunluk REEL/CAROUSEL/STORY yayini) |
| `scripts/pinterest/` | Pinterest scriptleri: `build_pins_v4.py` (pin gorselleri: poster 1000x1500, PIN_MEDIA_V2), `merge_week.py` (haftalik toplu-pin CSV'si), `pin_media_perms.py` (Drive "anyone" izin araci) |
| `scripts/common/` | Ortak yardimci moduller; `gh_secrets.py` (GitHub secret/variable yazma, OPS_ADMIN_TOKEN ile) |
| `.github/workflows/` | Zamanlanmis ve manuel GitHub Actions workflow'lari |
| `docs/` | Dokumantasyon |

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Sirlar

Calistirmak icin gereken ortam degiskenleri ve GitHub Secrets listesi
[`docs/SECRETS.md`](docs/SECRETS.md) dosyasindadir. Gercek deger hicbir
zaman depoya yazilmaz.

## Workflow'lar

| Workflow | Tetikleme | Is |
| --- | --- | --- |
| `drive-test` | elle | rclone ile Drive erisimini dogrular |
| `ig-build-carousel` | elle (`edition`, `days`, `contact`) | Poster + oda render'larindan Instagram carousel slaytlarini uretir, `TEMP/IG_CAROUSEL_V2/` altina yazar; kontak sayfalarini artifact olarak verir |
| `pin-build-v4` | elle (`edition`) | Edisyonun 78 posterini (2X3) 1000x1500'e kucultur, `LISTING_MEDIA/PIN_MEDIA_V2/<ED>/` altina yazar, klasoru anyone:reader (miras kapali) yapip dogrular, `TEMP/PIN_UPLOAD_STATE_V2.csv` ve kontak sayfasini gunceller. Filigran/mockup yok |
| `pin-week-v2` | elle (`week`, `start_date`, `force`) | V2 takvim: gunde 12 pin (UTC 08-19 saatlik), 33 gun, haftalik 84 pin. Metin `docs/PIN_TEXT_TEMPLATE_V2.md` sablonundan, Media URL PIN_MEDIA_V2, Etsy linki `TEMP/PIN_LISTING_MAP.csv`; `TEMP/PIN_CSVS_V2/WA_PIN_V2_HAFTAn_GUNxx_yy.csv` + plan dosyasi. Pinterest'e dokunmaz |
| `pin-merge-week` | elle (`week`, `day_from`, `day_to`, `start_date`) [ESKI hat, PIN_MEDIA linkli] | `TEMP/PIN_CSVS/WA_PIN_GUN_xx..yy.csv` dosyalarini birlestirir, Publish date doldurur (gunde 13 pin, UTC 13:00'dan 30 dk arayla), dogrular, `WA_PIN_HAFTAn_GUNxx_yy.csv` yazar. Pinterest'e dokunmaz |
| `pin-media-perms` | elle (`mode`, `apply`, `folder_id`, `keep_id`) | `fix`: agactaki "anyone" iznini reader'a ceker; `remove`: anyone iznini kaldirir, `keep_id` agacini korur ve anonim HTTP ile dogrular. Varsayilan dry-run |
| `start-here-append` | elle (`record_file`) | Depodaki `docs/start_here/Bnn.txt` kaydini Drive'daki START_HERE dokumaninin sonuna ekler (Docs API); ayni numara varsa yazmaz |
| `ig-media-sync` | elle (`days`, `dry_run`) | `TEMP/IG_CAROUSEL_V2` slaytlarini `astrolove-media/carousel_v2/` olarak GitHub Pages'e iter |
| `ig-publish` | elle (`dry_run` varsayilan acik) + gunluk 06:00 UTC (`IG_PUBLISH_ENABLED=true` ise) | WA_IG_PLAN'daki bugunun satirini Instagram'da yayinlar, durum sutunlarini gunceller |
| `prodigi-quote` | elle (`limit` 0=hepsi, `discover`, `skus`) | Prodigi pilot katalog + ABD fiyat/kargo okuma (salt okur); cikti Drive `TEMP/PRODIGI/` + artifact |
| `pod-gallery-sample` | elle (`pair`, `editions`) | POD galeri ornegi: ETSY_UPLOAD_SETS'ten 10 kare (6 mockup + symbol + crafted + 3 yeni kart) -> Drive `TEMP/POD_SAMPLE/<PAIR>/` + kontak sayfalari |
