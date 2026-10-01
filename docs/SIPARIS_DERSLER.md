# Siparis uretimi: dersler ve olcumler

Kaynak: 1 Ekim 2026, Tara siparisi + Test 1 + Test 2. Tum saatler UTC. Sayilar GitHub koşu kayitlari ve
Drive OZET dosyalarindan alinmistir.

## Hedef

Serdar yalniz su bilgileri verir: iki isim, her ismin hangi burcun altina gidecegi, tagline.
En gec 15 dk sonra 5 renk PDF (her biri 5 boy, 300 dpi) Drive'da, tum kapilar PASS.

## Sonuclar

| Is | Cift / isimler | Basla | 5 PDF Drive'da | Sure | Not |
|---|---|---|---|---|---|
| Tara (4188621967) | CANCER_LEO, TARA / ROSS | 13:17 | 16:57 | ~3 sa 40 dk | 11 koşu; DB 18x24 olcek kapisi |
| Test 1 (9000000001) | CANCER_LIBRA, SERDAR / LENA, "To My Adorable Angel" | 17:26 | 18:42 | 76 dk | ilk koşu 35 dk, 2 sayfa FAIL |
| Test 2 (9000000002) | CAPRICORN_SAGITTARIUS, GEORGE / MEG, "Happy 5th Anniversary" | 18:47:35 | 18:58:54 | 11 dk 19 sn | dogru dispatch 18:49:46'dan 9 dk 8 sn |

Test 2 is sureleri (dk): WP 11x14 2.1, MB 4x5 2.3, MB 11x14 2.6, MB A2 2.8, WP 16x20 3.5, WP 18x24 3.8,
WP A2 3.7, MB 18x24 4.3, CI 4.4 (2 dk gec basladi), MB 24x36 5.3, PW 5.4, DB 7.1, WP 24x36 7.8.
Paket: PDF'ler son isten ~1 dk sonra Drive'da; paket isi sonraki 5 dk'yi inceleme kesitlerine harcadi.

## Hatalar ve kok nedenleri

1. **Olcek (yazi yerlesim) kapisi, isme bagli FAIL** (Tara: DB 18x24; Test 1: MB 11x14).
   Kok neden olcumdeydi, baskida degil:
   - 2400 referansin 4x kutu kucultmesi 0.25 px font farkini ~0.9 px'e buyutuyordu, sapma harf sekline bagli.
   - MB'nin 2400 referansi farkli rasterlayici (pilot12.plaka, hinting) kullaniyordu, harf yuksekliginde 1.3 px'e kadar kayma.
   - Duzeltme (siparis-baski-v1 bfaed5d): esit bant olcumu, MB referansi da plaka_ss, dikey merkez yerlesim.
     Gercek 1.2 px kayma hala FAIL veriyor (hassasiyet korunuyor). Yerel sim 71/72.
   - Acik: CAGLAYANGUL 11x14 1.13 px (plaka alpha>40 kirpimi soluk serif uclarini atiyor).
   - Ders: tek sayfaya yama yapma; kok nedeni coz, isim on testiyle dogrula.
2. **WP 24x36 yanlis taban renk** (Test 1): duz renk MIDNIGHT_BLUE secildi, a_renk / f_kabartma / g_kontrast FAIL.
   Ayrica is 23 dk'da cokuyordu. Duzeltme 5cf010a: duz renk yalniz CHAMPAGNE_IVORY, JPEG 95. Sonra 7-9.5 dk.
3. **MB yavasligi**: sayfalar sirayla uretiliyordu, 33 dk. Paralel 5 is ile 6 dk.
4. **Cift sirasi** (Test 2): SAGITTARIUS_CAPRICORN girildi; kaynak klasor alfabetik CAPRICORN_SAGITTARIUS.
   13 is ~1 dk'da bos FAIL, 2 dk kayip. isim1 = cift adindaki ilk burc (posterde sol).
5. **Runner kuyrugu** (Test 2): ayni anda koşan prova 8 runner tuttu, CI 2 dk gec basladi.
6. **Dispatch hatalari** (Test 1): Content-Type yok -> 415; girdi adi `mesaj` degil `mesaj_b64` -> 422.
   `renk_ref` varsayilani eski 8a8b370; her zaman guncel siparis-baski-v1 head verilir.
7. **Bilinen darbogaz kapatilmadan test baslatildi** (Test 1): MB yavasligi Tara'dan biliniyordu.

## Dispatch sablonu (siparis-dijital, main)

```
receipt     : yalniz rakam (test: 900000000N)
cift        : ALFABETIK, orn. CAPRICORN_SAGITTARIUS
isim1       : cift adindaki ilk burcun altina giden isim (sol)
isim2       : ikinci burcun altina giden isim (sag)
mesaj_b64   : tagline, UTF-8 base64
renk_ref    : siparis-baski-v1 guncel head (tam sha)
wp_pod_kod  : v1
isler       : bos = hepsi; tek is icin orn. renk:MIDNIGHT_BLUE,wp:24x36
onceki_kosu : PASS isleri bu koşulardan al (tek is yeniden kosuda)
```

## Kontrol listesi (her test / siparis)

1. Calisan prova / tani / toplu koşu var mi? Varsa siparis once.
2. Cift alfabetik, isim1/isim2 burclarla eslesiyor.
3. renk_ref = siparis-baski-v1 head.
4. Saat dispatch aninda baslar; her dakika jobs okunur.
5. FAIL: OZET.json / KAPI_RAPORU oku, yalniz o isi duzelt ve yeniden kos.
6. 5 PDF Drive'da + OZET SONUC PASS + onizlemede isim-burc ve tagline dogru: hazir.
7. Teslim ve musteri mesaji yalniz Serdar onayiyla.

## Acik isler (1 Eki aksam)

- Cift sirasi otomatik normalize + isim yer degistirme.
- Kaynak yoksa plan adiminda hizli FAIL (10 sn).
- Paket <= 1 dk: inceleme kesitleri PDF'lerden sonra ayri is.
- Isim on testi (prova 36907530617) kalan 13 is; prova en fazla 4 paralel is.
- CAGLAYANGUL 11x14 soluk serif ucu.
- Harf bankasi: olcum basladi (b81d79f), karar verilmedi; olcek hatasi icin artik gerekli degil, hiz icin olculecek.

## Test 3 (9000000003, ARIES_VIRGO, LIAM / CATHERINE, "The World is Ours") - 1 Eki 19:14

- Basla 19:14:24. DB, PW, CI, WP PASS ve PDF'ler Drive'da ~19:22 (~8 dk). Paket 51 sn (yeni paket calisti).
- MB 24x36 (2x3): HATA `KeyError: 'tag_bant'`. Iz: siparis_dosyasi.render_et -> P_blue.hedef_render -> a1_poster.sayfa_kur
  -> pilot16.oran_kur (o28["tag_bant"]). Kok neden KAYNAK DOSYADA: kaynak-olcum (run 36915481126) ARIES_VIRGO MB
  2:3 boylarinda (12x18, 16x24, 20x30, 24x36) pilot11.sayfa_olc tagline bandi bulamiyor; isim_bant 3009-3090 / 3600
  (diger oranlarda ~%74, burada %84). Diger 11 boy PASS. Kaynak gorseli henuz incelenmedi (tagline eksik/kesik olabilir).
  Kod tarafi: a1_poster.sayfa_kur'da tag_bant yoksa fail-closed net hata ya da guvenli yedek gerekli.
- MB 11x14: olcek kapisi FAIL, cap_sol +1.09 (esik 1.0) tum denemelerde (baski-duzelt teshisi).
- Ders: yalniz 3 cift denenmisti; her cift x renk x boy kaynagi siparisten ONCE olculmeli (kaynak-olcum workflow,
  scripts/siparis_dijital/kaynak_olcum.py; sonuclar inceleme/kaynak-olcum dali).
- Ders: bilinen acik (MB 11x14) kapanmadan Test 3 baslatildi; kural yine cignendi.
- Ders: Test 3, 1 dk once main'e giren dogrulanmamis kodla (4fb7a35) kostu.
- Ders: iki oturum (koordinator + baski-duzelt) ayni anda ayni koda dokundu; tek sahip kurali konuldu.
- Ders: koordinator hata ayiklarken Serdar'a yazmayi birakti; en gec 2 dk'da bir durum kurali konuldu.
- Iyi giden: cift normalize, hizli kaynak denetimi (plan 6 sn), runner kuyrugu yok, paket 51 sn.

## Acik isler (Test 3 sonrasi, 1 Eki 19:45)

- MB 24x36 (ve 2:3 boylar) ARIES_VIRGO: kaynak gorseli incelenecek; tag_bant yoksa fail-closed / guvenli yedek (baski-duzelt).
- MB 11x14 olcek cap_sol +1.09 (baski-duzelt).
- Kaynak on testi HEPSI (run 36915485075) sonucu: etkilenen ciftler listelenecek.
- Test 3 MB yeniden kosu + paket, sonra Test 4 (yeni cift).
