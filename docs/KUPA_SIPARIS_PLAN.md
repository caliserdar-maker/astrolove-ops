# Kupa siparisi (Orchard) -> Printful: canli plan (19 Eki 2026, kuru)

Kod: `scripts/kupa_siparis/kupa_siparis.py`, workflow `.github/workflows/kupa-siparis.yml`.
Musteriye dokunan ve Printful'a gonderen adim bu planda YOK; her biri Serdar'in o siparise ozel acik onayi ile.

## 1. Tetikleme: router'a ek degil, ayri workflow

- `pod-order-router.yml` cron'u 13 Eki'den beri KAPALI (Serdar). Router KUPA- SKU'larini `parse_tx` ile tanimaz,
  "POD disi" sayip atlar; Prodigi'ye ozgu STATE/paket/onay sayfasi akisi kupaya uymaz.
- Kupa akisi agir bagimlilik ister (numpy/scipy/fonttools, kupa-orchard kodu, sembol dali) ve kalem basina 35-60 sn surer;
  router'in 20 dk zaman asimini ve Etsy kilidini gereksiz tutar.
- Oneri: `kupa-siparis.yml` ayri; ayni kilit (`scripts/etsy/kilit_bekle.py`: cron `--mod atla`, elle sira bekle),
  Etsy yalniz GET (`was_paid`, `was_shipped=false`, son N gun), kota tabani 10. STATE: Drive `KUPA_SIPARIS/STATE.csv`
  (transaction bazinda; islenen kalem tekrar islenmez, Drive'a yazilamayan kalem STATE'e girmez).
- Siparis BEKLETILMEZ (Serdar 19.10): cron `*/15` acildiginda kapilar PASS/GOZ ise baski 15 dk icinde Drive'da.
  Cron satiri yorumda; acilmasi Serdar onayi ister (13 Eki karari otomatik GONDERIMI kapatti; bu akis gondermez).
  Kota: tarama kosu basina 1 cagri (gunde ~96).

## 2. Printful dosya teslimi

Dogrulama durumu: Printful dokumani bu oturumun aginda kapali (developers.printful.com proxy 403); asagidaki maddeler
resmi sayfalarin arama ozetinden. Canliya almadan once dokumanin kendisi bir kez okunmali (acik is).

- Siparis kalemi dosyayi `files: [{"url": ...}]` ile alir; Printful dosyayi o URL'den kendisi indirir ve File Library'ye
  ekler. Kutuphanedeki dosya `files: [{"id": ...}]` ile de verilebilir. Kutuphaneye ekleme (`POST /files`) de URL ile
  yapilir; ikili (binary) yukleme ucu gorulmedi. Yani her iki yolda Printful dosyayi bir URL'den ceker.
- `confirm=false` (ya da varsayilan) siparis TASLAK olarak acilir; uretime gecis ayri onay adimi.
- `recipient.email` istege bagli; verilmezse Printful aliciya kargo e-postasi gonderemez. Yuk dosyasinda e-posta/telefon
  BILEREK yok (musteriye dokunan bildirim olmasin).

Guvenli yol (oneri, router'daki Prodigi yontemiyle ayni):
1. Baski dosyasi yalniz Drive `KUPA_SIPARIS/<receipt>/<transaction>/` (ozel). Depoya, Actions artifact'ina, loga girmez.
2. Serdar onayi aninda: dosyaya gecici `anyone:reader` izni (`DriveLinks.open`, `scripts/prodigi/order_router.py`),
   `POST /files {"url": ...}` -> File Library; `GET /files/{id}` durumu `ok` olunca izin HEMEN kaldirilir
   (`DriveLinks.close`). URL loga yazilmaz (`::add-mask::`). Link tahmin edilemez Drive kimligidir, dakikalar surer.
3. `POST /orders?confirm=false` + `files: [{"id": <kutuphane id>}]` -> Printful'da TASLAK; uretime onay yine Serdar.
Alternatif (Drive izni hic acilmasin): kisa omurlu imzali URL veren ozel bir depolama (or. GCS signed URL). Ek hesap/sir
gerektirir; ilk siparislerde Drive gecici izni yeterli.

## 3. Drive cikti duzeni

`ASTROLOVE/KUPA_SIPARIS/<receipt>/<transaction>/`: `BASKI_AstroLoveArt_<B1>_<B2>_<Stil>_<11|15>oz_<boyut>.png`,
`ONIZLEME_*.jpg`, `OZET.json` (kapilar, notlar, piksel ozeti), `PRINTFUL_TASLAK.json` (confirm=false yuku, gonderilmedi),
`MUSTERI_MESAJI_TASLAK.md` (kupa_orchard/mesaj/MUSTERI_MESAJLARI.md: PASS/GOZ 1 (+6 ayni burc), isim 2, mesaj 3,
eksik 4, karakter 5), FAIL'de `SORU.md`, `kontrol/burc_mesafe.txt`.

## 4. Onay akisi (ilk siparisler)

PASS -> baski hazir; Serdar Printful siparisini ELLE_SIPARIS.txt ile panelden ELLE verir (19.10: API gonderimi ve cron yok).
GOZ -> ayni, once baski dosyasina gozle bakilir.
FAIL -> baski yok; SORU.md + musteri mesaji taslagi; Serdar mesaji gonderir ya da karar verir, duzeltilmis metinle
`--receipt-id` ile yeniden kosulur (STATE'teki satir silinerek).

## 5. Acik isler

- Printful dokumani (files/url, POST /files, confirm) dogrudan okunup bu bolum teyit edilecek.
- Printful TASLAK gonderim betigi (gecici link + File Library + confirm=false) yazilacak; yalniz Serdar onayiyla kosar.
- Cron acilisi (Serdar karari). Kisisellestirme Etsy'nin yeni coklu alan modelinde gelirse `metin_coz` yeniden olculecek.
