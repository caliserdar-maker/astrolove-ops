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
- Ders (koordinator, 19:35-20:00): test ciktisi `| tail` ile maskelendi, hatali kod push edildi (1 dk'da duzeldi);
  baski-duzelt'in izledigi kaynak-olcum kosusu haber vermeden iptal edildi; ilk kaynak on testi seri ve 15 boy
  (~40 dk) tasarlandi, paralel + 5 boy ile yeniden kuruldu; uzun bloklayan izleme donguleri Serdar'i yanitsiz birakti.
- Isim on testi (prova, eski olcek kapisi): 36/37 PASS (TARA, SERDAR, MAXI, ANNE). MB 11x14 LIAM: esit bant olcumu
  duz kenarli harflerde yeni sapma uretiyor; baski-duzelt olcum oncesi simetrik bulanik deniyor (126/126, en kotu 0.99).
- Iyi giden: cift normalize, hizli kaynak denetimi (plan 6 sn), runner kuyrugu yok, paket 51 sn.

## Acik isler (Test 3 sonrasi, 1 Eki 19:45)

- MB 24x36 (ve 2:3 boylar) ARIES_VIRGO: kaynak gorseli incelenecek; tag_bant yoksa fail-closed / guvenli yedek (baski-duzelt).
- MB 11x14 olcek cap_sol +1.09 (baski-duzelt).
- Kaynak on testi MB (run 36918326986, 78 cift x 5 siparis boyu, 250 sn): 388/390 PASS; FAIL: ARIES_GEMINI 24x36, ARIES_VIRGO 24x36 (ikisi de ARIES harf boslugu). Diger renkler (DB/PW/CI/WP) icin kaynak on testi henuz yok (farkli olcum yolu).
- Kaynak on testi 4 renk (36921322373): DB/PW/CI 390/390 PASS; WARM_PARCHMENT 229/390 (161 FAIL, 34 cift alfabetik
  GEMINI_LIBRA..VIRGO_VIRGO). baski-duzelt teshisi: on test WP'yi uretimden farkli olcuyordu (yerel kontrast maskesi
  atlaniyordu); ayrica uretimdeki plate_slogan_kapisi (tum renklerde render_et icinde) ham sayfa_olc kullaniyor ve ARIES
  bolunme zayifligini tasiyor. Duzeltme: slogan kapisina guvenli olcum (gerek = isim + tagline), 5 renk yeniden on test.
- Test 3 MB yeniden kosu + paket, sonra Test 4 (yeni cift).

## TUM DERSLER (Tara + Test 1-3 + gece, 1 Eki; Serdar: Test 4'te hepsi uygulanacak)

Tara (4188621967)
1. Tek sayfaya yama yapildi (DB 18x24 altin profili), kok neden cozulmedi; isim degisince hata baska sayfada cikti.
2. Dosya/klasor adi AstroLove_ yazildi; marka her yerde AstroLoveArt.
3. Musteri metninde olculmemis cozunurluk iddiasi (11x14 -> 22x28); boy/dpi iddiasi yalniz olcumle.
4. Yalniz GitHub'a bakip oturum "bos" denildi; oturum yerelde calisiyor olabilir.
5. Beklenerek ilerlendi; siparis isi kesintisiz, zamanlayici yok.
6. MB yavasligi (25 dk) olculdu ama giderilmedi.
Test 1 (9000000001)
7. Dispatch hatalari (Content-Type yok 415, `mesaj` yerine `mesaj_b64` 422); sablon kullan.
8. Bilinen MB yavasligi kapatilmadan test basladi (MB 33 dk).
9. WP 24x36 yanlis taban renk (MB) + 23 dk'da cokme; duz renk yalniz CHAMPAGNE_IVORY, JPEG 95.
10. Olcek kapisi FAIL olcum hatasiydi (kutu kucultme + farkli rasterlayici); esit bant olcumu.
11. MB sayfalari sirayla; paralel 5 is (33 -> 6 dk).
12. FAIL nedeni Drive OZET/KAPI raporundan okunur (loglar kapali).
13. Tek sayfa FAIL'de yalniz o is yeniden (isler + onceki_kosu).
Test 2 (9000000002)
14. Cift sirasi ters girildi; cift alfabetik, isim1 = ilk burc (sol). Artik otomatik normalize.
15. Yanlis giriste 13 is 1 dk bosa; plan adiminda hizli kaynak denetimi (sn'ler).
16. Prova siparis sirasinda runner doldurdu (CI 2 dk gec); siparis sirasinda prova/tani yok.
17. Paket 5 dk inceleme kesitine gitti; paket yalniz PDF + OZET (~51 sn).
18. "Hazir" = 5 PDF Drive'da (createdTime), job bitisi degil.
19. renk_ref her zaman acik tam sha (varsayilan eski).
20. Teslim oncesi onizlemede isim-burc ve tagline kontrol.
Test 3 (9000000003)
21. Yalniz 3 cift denenmisti; ARIES_VIRGO MB 2:3 bant olcumu kaydi (kok neden, baski-duzelt 20:10: "ARIES" harfleri arasindaki 20 px bosluk ismi 4 kumeye boluyor; isim satiri 3 kume beklendigi icin taninmiyor, tagline isim sanilyor; duzeltme: gecersiz olcumde 60 px kume boslugu ile yeniden olc, yine gecersizse acik hata). Tum ciftler x renkler x boylar kaynak on testi.
22. Acik is (MB 11x14) kapatilmadan test (ikinci kez).
23. 1 dk once main'e giren dogrulanmamis kodla test.
24. Esit bant olcumu duz kenarli harflerde (LIAM) yeni sapma; olcum oncesi bulanik sigma 1.0 (en kotu 0.78, gercek 1.1 px kayma FAIL).
25. Hata izi / olcek ayrintisi OZET'te yoktu; eklendi.
26. Ayni koda iki oturum dokundu; tek sahip.
Koordinator
27. Hata ayiklarken Serdar'a yazilmadi; en gec 2 dk'da bir durum.
28. Uzun bloklayan izleme donguleri; kisa kontrol + rapor.
29. Test ciktisi maskelendi, hatali kod push edildi; once test + cikis kodu, sonra push.
30. Baska oturumun izledigi kosu haber vermeden iptal edildi; once bildir.
31. Yeni arac yavas tasarlandi (seri, 15 boy); baştan hizli (paralel, yalniz gereken boylar).
32. Yazilan kurallar uygulanmadi; Test 4 oncesi kontrol listesi madde madde isaretlenip Serdar'a gosterilir.

Gece (20:00-21:10)
33. Test araci uretimi yeniden yazarak olctu (kaynak_olcum): MB'de duz esik, WP'de eksik maske -> sahte FAIL.
    Test araci uretimin KENDI fonksiyonlarini cagirir, kopyasini yazmaz.
34. Hipotez bulgu gibi iletildi ("Virgo kuyrugu"; gercek neden ARIES harf boslugu). Dogrulanmamis neden "olasi" diye yazilir.
35. "ARIES duzeldi" denildi, ayni zayiflik plate_slogan_kapisi'nda kaldi. Bir duzeltmeden sonra ayni olcumu kullanan
    tum yerler aranir.
36. Uretim kodu degisince calisan isim on testi gecersiz olur; kapi icin yeni head ile yeniden kosulur.

## TEST 4 BASLANGIC KAPISI (hepsi EVET olmadan dispatch yok; Serdar'a madde madde gosterilir)

- [ ] Acik is listesi bos: Test 3 MB 11x14 + 24x36 duzeldi, Test 3 OZET 5/5 PASS.
- [ ] Kaynak on testi: tum ciftler x 5 renk x 5 siparis boyu PASS (yalniz MB degil).
- [ ] Isim on testi yeni kodla PASS (11x14 dahil, uzun/aksanli isimler dahil).
- [ ] Kod sabit: renk_ref tam sha + main sha not edildi; son degisiklik testlerden gecti.
- [ ] Calisan prova / tani / toplu kosu yok.
- [ ] Cift alfabetik, isim1/isim2 burclarla eslesiyor.
- [ ] Saat dispatch aninda baslar; 2 dk'da bir rapor.
- [ ] Bitti tanimi: 5 PDF Drive'da + OZET PASS + onizleme kontrolu.

## DURUM 1 Eki 21:40 UTC (Serdar: Test 4 yarin)

- Kaynak on testi v1 6e02ffe (5 kosu 3692660x): MB/DB/PW/CI 390/390; WP 388/390 - acik: LEO_SAGITTARIUS ve LEO_VIRGO
  WARM_PARCHMENT 18x24 (tag_bant yok). baski-duzelt inceliyor (kaynak-olcum 36929585913).
- Isim on testi prova 36926624004 (6e02ffe, 54 is): 21:35'te 13 success, FAIL yok, devam ediyor.
- Test 4 kapisi: kalan = 2 WP 18x24 dosyasi + isim on testinin bitmesi. Test 4 icin cift secimi bu 2 ciftin disindan.
