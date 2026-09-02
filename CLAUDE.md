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

## HIZ VE KALITE KURALLARI (2 Eyl 2026 karari)

1. Alt-ajan / review workflow / paralel ajan YASAK. Tek surec.
2. Iterasyon YERELDE: kucuk ornek (6 poster / 1 cift) ile 60 sn altinda
   test. Actions yalniz yerelde temiz cikan surum icin, en fazla 1 kez.
3. Her gorev basinda 3 satir yaz: (a) yontem, (b) "bitti" tanimi (olculur
   esik), (c) tahmini sure. Yontem degisecekse DUR, Mo'ya sor.
4. En fazla 2 iterasyon. Ikincisi de temiz degilse DUR, durumu raporla,
   devam etme.
5. Uzun her kosuda ETA sayaci (islenen/toplam, gecen, kalan, yuzde).
6. Rapor: en fazla 6 satir + dosya yollari. Aciklama yok.
7. QC: tek script, olculebilir esik, PASS/FAIL. "Gozle bakiyorum" dongusu yok.
