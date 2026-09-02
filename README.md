# astrolove-ops

AstroLove otomasyon scriptleri.

Bu depo, AstroLove icin Etsy, Instagram ve Pinterest tarafindaki tekrarli
islerin otomasyonunu barindirir. Scriptler GitHub Actions workflow'lari
uzerinden veya lokalde elle calistirilabilir.

## Klasor yapisi

| Yol | Icerik |
| --- | --- |
| `scripts/etsy/` | Etsy API scriptleri (listeleme, siparis, envanter) |
| `scripts/instagram/` | Instagram scriptleri: `build_carousel.py` (5 slaytlik carousel uretimi) |
| `scripts/pinterest/` | Pinterest scriptleri: `merge_week.py` (haftalik toplu-pin CSV'si), `pin_media_perms.py` (PIN_MEDIA izin duzeltme) |
| `scripts/common/` | Ortak yardimci moduller (auth, http, log) |
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
| `pin-merge-week` | elle (`week`, `day_from`, `day_to`, `start_date`) | `TEMP/PIN_CSVS/WA_PIN_GUN_xx..yy.csv` dosyalarini birlestirir, Publish date doldurur (gunde 13 pin, UTC 13:00'dan 30 dk arayla), dogrular, `WA_PIN_HAFTAn_GUNxx_yy.csv` yazar. Pinterest'e dokunmaz |
| `pin-media-perms` | elle (`mode`, `apply`, `folder_id`, `keep_id`) | `fix`: agactaki "anyone" iznini reader'a ceker; `remove`: anyone iznini kaldirir, `keep_id` agacini korur ve anonim HTTP ile dogrular. Varsayilan dry-run |
| `start-here-append` | elle (`record_file`) | Depodaki `docs/start_here/Bnn.txt` kaydini Drive'daki START_HERE dokumaninin sonuna ekler (Docs API); ayni numara varsa yazmaz |
