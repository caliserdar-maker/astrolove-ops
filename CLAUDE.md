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
  Etsy kosusu: `scripts/etsy/kilit_bekle.py` (28 Eyl 2026, Serdar onayi; GitHub
  `concurrency: etsy-token` KULLANILMAZ, bekleyen kosuyu iptal ediyordu). Yeni Etsy
  workflow'u: `permissions: actions: read` + checkout'tan hemen sonra, token indirmeden
  ONCE `GH_TOKEN: ${{ github.token }}` ile `python3 scripts/etsy/kilit_bekle.py` adimi.
  Zamanlanmis router mesgulse turu atlar (`--mod atla`).
- KURAL (tum oturumlar): Etsy kosusunu istedigin an baslat; kilit sirayi kendisi tutar,
  hicbir kosu iptal edilmez (bekleme en fazla 120 dk, asilirsa is yapmadan FAIL).
- Hicbir sir loga yazilmaz; token degerleri `::add-mask::` ile maskelenir.
- **updateListing bir TASLAGI otomatik yayina alir** (7 Eyl 2026 olcumu: gece
  aciklama guncellemesi 72 taslagi `active` yapti; `state_timestamp` = PATCH ani).
  Toplu guncellemede "ilan taslak kalir" varsayimi YAPILMAZ: yazmadan once state
  okunur, taslak kalmasi gerekiyorsa o ilan guncellenmez ve Mo'ya sorulur.

## MUSTERIYE DOKUNAN HER EYLEM (26 Eyl 2026, Serdar kesin talimati)

- Musteriye bildirim/mesaj/e-posta dogurabilecek HICBIR eylem Serdar'in o eyleme ozel acik onayi olmadan yapilmaz.
  Kapsam: Etsy mesaji, createReceiptShipment / takip yazma veya duzeltme (Etsy aliciya bildirim gonderebilir),
  siparis durumu degistirme, iade/iptal, yorum yaniti, dijital dosya teslimi, Prodigi'ye siparis gonderimi.
- "Koordinator onayi" / pano "CLAUDE ONAYI" bu eylemler icin GECERSIZDIR. Yalniz Serdar onaylar.
- Musteri mesajlari yalniz TASLAK olarak Drive'a yazilir; gonderimi Serdar yapar ya da ayri acik onay verir.

## Urun metni (25 Eyl 2026 karari; 24 Eyl B-5'i gunceller)

- Birincil kaynak: Hahnemuhle Photo Rag datasheet + urun sayfasi, Prodigi HPR urun foyu.
- Izinli: acid-free, 100% cotton, pigment-based archival inks, natural white,
  matte, "Hahnemühle rates Photo Rag as museum quality (ISO 9706)".
- Yasak: OBA-free, bright white, omur yili (orn. 100-200 years), "12-colour".
  Ingilizce metinde uzun/orta tire yok.
- Tek kaynak ve PASS/FAIL denetim: `scripts/medya_v1/uretim/metin_kurali.py`
  (medya-v1 dali).

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

## SIPARIS ISI KESINTISIZ (1 Eki 2026, Serdar kesin talimati)

- Musteri siparisi dosyalari (dijital ve baski) TUM kapilar PASS olana kadar is ARALIKSIZ surer. Tek dakika bekleme yok.
- Kosu biter bitmez sonuc okunur, ayni dakikada sonraki duzeltme veya kosu baslar. Onay, kuyruk, "raporlayip bekle" yok.
- Bu islerde HIZ VE KALITE madde 4 ("2 iterasyondan sonra DUR") GECERSIZDIR: FAIL'de durulmaz; 6 satir durum yazilir ve calismaya devam edilir.
- Musteriye teslim, Etsy mesaji ve yukleme yine yalniz Serdar'in acik onayiyla.

## ZAMANLAYICI YASAK (1 Eki 2026, Serdar kesin talimati)

- Hicbir oturum, hicbir koşuda "X dk sonra bakarim" zamanlayicisi KURMAZ (send_later, ScheduleWakeup, cron ile bekleme, sleep ile uzun bekleme dahil).
- Baslatilan her koşu ARALIKSIZ izlenir: GitHub API ile jobs her 30-60 sn okunur (tek komut icinde dongu), bir is biter bitmez sonucu okunur.
- FAIL olan is icin koşunun tamamini bekleme: ayni dakikada rapor oku, duzelt, yerelde dogrula, o is icin yeni koşu baslat.
- Kosu bitince ayni dakikada 6 satir rapor. Bekleme gereken tek durum: Serdar'in acik onayi gereken eylem (Etsy yazma, musteriye dokunan eylem).

## MARKA ADI (1 Eki 2026, Serdar kesin talimati)

- Marka adi **AstroLoveArt**. Musterinin gorebilecegi her seyde (PDF/dosya/klasor adi, mesaj, metin) yalniz "AstroLove" YAZILMAZ.
- Siparis dosyalari: AstroLoveArt_<Burc1>_<Burc2>_<Renk>.pdf (orn. AstroLoveArt_Cancer_Leo_Deep_Black.pdf).

## SIPARIS URETIMI: OGRENILENLER (1 Eki 2026, Tara + Test 1 + Test 2; ayrinti docs/SIPARIS_DERSLER.md)

Hedef: Serdar isim + burc yeri + tagline verir, 15 dk icinde 5 PDF Drive'da (Test 2: 11 dk 19 sn, PASS).

- CIFT ANAHTARI ALFABETIK: CAPRICORN_SAGITTARIUS (SAGITTARIUS_CAPRICORN degil). isim1 = cift adindaki ILK burc
  (posterde sol), isim2 = ikinci burc (sag). Ters sira kaynak bulamaz, tum isler ~1 dk'da FAIL (Test 2).
- DISPATCH (siparis-dijital): Content-Type: application/json; mesaj girdisi `mesaj_b64` (UTF-8 base64);
  `renk_ref` HER ZAMAN acikca verilir = siparis-baski-v1 guncel head (varsayilan 8a8b370 ESKI); wp_pod_kod v1;
  receipt yalniz rakam (test: 900000000N).
- Siparis kosusu sirasinda prova / tani / toplu kosu ACILMAZ: runner kuyrugu siparis islerini geciktirir
  (Test 2: CI 2 dk gec basladi).
- "Dosyalar hazir" = 5 PDF Drive'da (createdTime), job bitisi degil. Teslim oncesi 1:1 / onizleme ile
  isim-burc eslesmesi ve tagline gozle kontrol edilir.
- FAIL olan tek sayfa icin tum siparis yeniden kosulmaz: `isler=` + `onceki_kosu=` ile yalniz o is.
- FAIL nedeni Drive SIPARIS_ISIM/DIJITAL/<receipt>/OZET.json (kapilar, kalan) ve KAPI_RAPORU_<RENK>.json'dan okunur
  (job loglari proxy'de kapali; annotations yalniz "exit code 1" verir).
- Olcek (yazi yerlesim) kapisi FAIL'i isme bagliydi ve olcum hatasiydi (bfaed5d: esit bant olcumu, MB 2400 referansi
  plaka_ss, dikey merkez). Tek sayfaya yama yapilmaz; kok neden + isim on testi (TARA, SERDAR, MAXI, ANNE,
  uzun/aksanli isimler orn. MAXIMILIAN, CAGLAYANGUL) ile dogrulanir.
- MB sayfalari paralel (5 is) kosar: 33 dk -> 6 dk. WP duz renk yalniz CHAMPAGNE_IVORY, JPEG 95 (5cf010a).
- Bilinen darbogaz kapatilmadan test/siparis baslatilmaz; once olc, sonra kos.
