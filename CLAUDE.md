# astrolove-ops — calisma kurallari

Bu depo AstroLoveArt Etsy magazasinin (shop 39729443) otomasyon deposudur.
Oturum gunlugu ve baglayici kararlar Drive'daki START_HERE dokumanindadir
(00_START_HERE__ASTROLOVE_FILE_SYSTEM); yeni bir ise o dokumanin ilgili
bolumu okunmadan baslanmaz.

## Git

- Bu depoda dogrudan `main`'e push serbesttir; PR gerekmez (1 Eyl 2026 karari).
- `workflow_dispatch` yalniz `main`'deki workflow'lar icin calisir; yeni bir
  workflow tetiklenecekse once `main`'e alinir.

## Etsy

- Salt okur isler (listing okuma, dogrulama, SEO taramasi) onaysiz kosulur.
- Etsy'ye YAZAN her adim onay bekler: state degistirme, medya/ZIP/video
  yukleme veya silme, yayinlama, fiyat/etiket/aciklama degisikligi.
- Token sahibi: Drive `ASTROLOVE/TEMP/ETSY_TOKEN.json` tek kaynaktir; yenilenen
  refresh token her kosuda geri yazilir (bkz. docs/SECRETS.md). Ayni anda tek
  Etsy kosusu (`concurrency: etsy-token`).
- Hicbir sir loga yazilmaz; token degerleri `::add-mask::` ile maskelenir.

## Uretim

- Wallpaper hatti dahil tum uretim GitHub Actions'ta kosar; ChatGPT/Colab
  uretim hattinda yoktur (KARAR 3, 1 Eyl 2026).
- Esik ve yerlesim kurallari tahminle degil, onayli dosyalardan olculerek
  turetilir (docs/WP_LAYOUT_SPEC.md bu yontemle yazilir).
