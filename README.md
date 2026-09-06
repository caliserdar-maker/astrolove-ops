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
| `pod-gallery-build` | elle (`pairs` ALL/liste, `shards`, `force`) | 78 cift POD galerisi: cift x 5 edisyon x 10 kare (11_EXTRA yok), 05/08/10 kartlari cizilir, kart basina QC (boyut, ust bant, rozet, 6 bosluk, palet/geometri); Drive `TEMP/POD_GALLERY/<PAIR>/<ED>/` + `_CONTACT/`; shard STATE `TEMP/POD_GALLERY_STATE/shard_n.csv`, birlesik `TEMP/POD_GALLERY_STATE.csv` + `POD_GALLERY_REPORT.md`; FAIL cift STATE'e yazilir, kosu surer; resume |
| `pod-listing-update` | elle (`pair`, `listing_id`, `dry_run` varsayilan acik, `wp_state_file`) | POD (Prodigi poster) ilaninda tag + aciklama katmanini `docs/POD_LISTING_TEMPLATE.md` sablonuna gore gunceller (EN). `listing_id` bos + dry_run: magazadaki taslaklari listeler (WP haric). dry_run=false Etsy'ye YAZAR (Mo onayi); basliga dokunmaz |
| `repo-public` | elle (`delete_runs`, `set_public`) | PUBLIC gecis (6 Eyl 2026): run gecmisini siler, gorunurlugu public yapar, secret isimlerini dogrular (OPS_ADMIN_TOKEN, runner icinde) |
| `pod-listing-create` | elle (`pairs` / `ALL`, `limit`, `dry_run` varsayilan acik, `primary`, `return_policy_id`, `return_policy_spec`) | POD YENI ILAN: createDraftListing + 12 gorsel (10 kare + Symbol Story/Crafted Detail teknik karti rank 4-5, kart OCR on kontrolu) + V01 video (ana edisyon; eksik medya raporlanir, kosu surer) + Color(5)xSize(13)=65 varyant (SKU `POD-<burc3>_<burc3>-<ed2>-<SIZE>` (<=32), adet 999, fiyat `scripts/etsy/pod_prices.csv`) + renk secenegine edisyon 01 karesi; kargo profili/bolum/partner/iade/taxonomy API'den. dry_run: kesif + payload JSON. STATE `TEMP/POD_LISTING/POD_LISTINGS_STATE.csv` (resume); kota 400 altinda yeni ilana baslamaz |
| `pod-media-add` | elle (`listing_id`, `pair`, `edition`, `dry_run` varsayilan acik, `quota_min`) | EK 3: mevcut POD ilanina 2 teknik kart (rank 4 Symbol Story, 5 Crafted Detail; `LISTING_MEDIA/TECHNICAL`) + 1 video (`VIDEOS/V01_FIREFLY_STORY/01_EXPORTS/<ED>`, 1080x1350). Kart OCR on kontrolu (download/instant/print at home/JPG/PDF/file -> yukleme yok), mevcut gorsel silinmez, sira id ile kurulur, geri okuma 12/12 id + piksel, video 1; cikti `TEMP/POD_LISTING/MEDIA_<MODE>_<stamp>/` |
| `pod-inventory-update` | elle (`listing_id`, `dry_run` varsayilan acik, `quota_min`) | POD ilani envanterinde Size degerlerine oran etiketi (EK 1): SKU/fiyat/adet/gorunurluk korunur, tek updateListingInventory; dry-run eski->yeni tablo, apply geri okuma 65/65 |
| `pod-print-build` | elle (`pairs` ALL/liste, `shards`, `force`) | POD baski dosyalari: 78 cift x 5 edisyon x 13 boyut (Prodigi print-area pikseli, 300 dpi, q95) -> Drive `TEMP/POD_PRINT/<PAIR>/<ED>/<SIZE>.jpg` (paylasimsiz); STATE `TEMP/POD_PRINT_STATE.csv` + rapor; QC piksel tam esit |
| `pod-order-router` | elle (cron 30 dk sandbox testi + `POD_ROUTER_ENABLED=true` sonrasi acilir; kapaliyken bile etsy-token grubunu tuttugu icin simdilik kapali) (`env`, `dry_run`, `etsy_writes`, `test_receipt`) | Etsy POD siparisi -> Prodigi siparisi (Budget, gecici Drive asset linki) -> kargo takibi -> Etsy; STATE `TEMP/POD_ORDERS_STATE.csv`; `docs/POD_ORDER_ROUTER.md` |
