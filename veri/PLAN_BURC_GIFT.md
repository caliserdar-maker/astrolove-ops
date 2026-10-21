# PLAN_BURC_GIFT 22 Eki 2026: 234 aktif ilanda burc hediye ifadesi (Serdar karari, KARAR 8 yerine). UYGULANMADI.
Yontem: canli okuma -> kural ile uretim -> olcum (yerel, yazma yok). Bitti: 234/234 PASS (ifade 3 alanda, 13 etiket, <=20, <=140, tire 0)
+ bagimsiz inceleme + Serdar onayi. Uygulama: tek birlesik arac (baslik+etiket+aciklama tek PATCH), sahte API testi, CANCER_LIBRA x3,
pilot 5, kalan. Sure: arac + test ~2 sa; yazma ~15 dk [TAHMIN].

## 0. Canli okuma ve 20/22 Eki farki
- 2 canli okuma: kosu 39684183199 (21 Eki 22:08 UTC) ve 39686295137 (22:25 UTC); 234 ilan, dosyalar BIREBIR ayni (cmp) [API].
  Etsy count 234 = okunan 234; aile basina 78; kota kalan 2992 [API OZET.json].
- 20 Eki canli kaydi olarak bulunan tek dosya: Drive TEMP/ETSY_ADS_TESPIT_20261020/HAM_SONRA.json (20 Eki 17:20 UTC). Kapsami yalniz
  78 POSTER ilaninin baslik + etiketi (aciklama yok); bunlar 22 Eki okumasiyla 78/78 ayni [olcum]. Kupa ve yil donumu (156 ilan) icin
  20 Eki kaydi bulunamadi; karsilastirilmadi. Serdar'in "20 Eki sayimi" baska dosyadansa dosya adi gerekir.

## 1. Ifadeler (Serdar, MI 12 ay)
Aquarius Gift, Aries Gift, Cancer Gifts, Gemini Gifts, Leo Gifts, Virgo Gifts, Libra Gifts, Scorpio Gifts, Sagittarius Gift,
Capricorn Gifts, Pisces Gift, Taurus Gifts. Baslikta bu yazimla, etikette kucuk harf. Ayni burclu ciftte tek ifade. Sira: basliktaki burc sirasi.

## 2. Baslik
- Kural: ifadeler, burc ciftini iceren ilk virgullu bolumden hemen sonra (urun adi bolunmez). Ornek: "Cancer and Libra Couple Wall Art,
  Cancer Gifts, Libra Gifts, Newlywed Gift, ...". Not: "cift adindan hemen sonra" kelimesi kelimesine uygulanirsa urun adi bolunur
  ("Cancer and Libra, Cancer Gifts, Libra Gifts Couple Wall Art"); oneri: bolum sonu. KARAR SERDAR'IN (iki ornek: bolum sonu /
  kelimesi kelimesine). Not: yil donumunde ifade basligin ikinci yarisina (~90. karakter sonrasi) duser; arama sonucunda kesilen kisimda
  kalma riski var (TAHMIN, olculmedi).
- Yil donumu: "Zodiac Couple Print with" -> "Zodiac Couple Printable Art with" (Serdar 22 Eki).
- 140 olcumu [olcum, ONCE_SONRA_234.csv]: poster 92-130 (asan 0), kupa 84-122 (asan 0), yil donumu 133-174 (76/78 asar).
- Yil donumu kisaltma (78'in hepsine, tutarlilik; Serdar secer) [olcum, ONCE_SONRA_234.csv]:
  A (oneri): sondaki ", Paper Anniversary Card" ve " with Names and Date" cikar, "Personalized" KALIR -> 89-130, asan 0.
     CANCER_LIBRA: "1st Anniversary Gift for Husband, Personalized Cancer Libra Zodiac Couple Printable Art, Cancer Gifts, Libra Gifts".
     Gerekce: 78 yil donumu ilaninin hicbirinin etiketinde "personalized" yok [olcum]; B secenegi bu sozcugu aramadan tamamen siler.
  B: ", Paper Anniversary Card" ve "Personalized " cikar, "with Names and Date" kalir -> 117-137.
  Digerleri: yalniz son bolum (max 150, 22 asar); son bolum + "with Names" (max 141, 2 asar).
  Iki secenekte de "paper anniversary" basliktan cikar (MI "paper anniversary gift" 7k [Serdar ekrani, PLAN_BASLIK]); etiket 78/78'de kalir [API].
- Bu, PLAN_BASLIK_20261022 ("Printable Card" kalibi) onerisinin yerine gecer (Serdar 22 Eki "Printable Art").

## 3. Etiket (13 etiket ve 20 karakter kontrolu: 234/234 PASS)
- Poster ve yil donumu: iki burc etiketi ilgili ifadeyle degisir; ifade zaten varsa dokunulmaz. Degisim onceligi: X gift(s)
  (tekil/cogul es) > X zodiac gift > X print > X wall art (inceleme 1: aksi halde CAPRICORN_CAPRICORN ve CAPRICORN_SAGITTARIUS
  posterlerinde "capricorn gift" + "capricorn gifts" birlikte kaliyordu; duzeltildi, simdi 0 [olcum]).
- Ayni burclu ciftte tek ifade; ikinci burc etiketi (orn. LEO_LEO "leo print", ARIES_ARIES "aries wall art") KALIR (9 ayni burclu poster).
  CAPRICORN_SAGITTARIUS posterinde 3. burc etiketi "capricorn wall art" kalir (ilan 3 burc etiketi tasiyordu) [olcum]. Cikan (adet) [olcum]: poster aquarius wall art 12, aries gifts 12, cancer wall art 11, cancer zodiac gift 1,
  capricorn gift 2, capricorn wall art 10, leo print 11, libra gift 12, sagittarius gifts 12 (etiketi degismeyen 16);
  yil donumu aries gifts 12, cancer zodiac gift 12, capricorn gift 12, libra gift 12, sagittarius gifts 12 (degismeyen 28);
  kupa zodiac symbols 78, zodiac gift 66.
- Kupa: burc etiketi yok; cift adi etiketi ("cancer and libra") KALIR. Degisen aday: "zodiac symbols" (78; baslikta "Zodiac Symbols"
  zaten geciyor) ve "zodiac gift" (66; ayni burclu 12 kupada yalniz 1 degisim). MI olcumu YOK: secim Serdar'in. "evil eye mug" kalir
  (aciklama: kupanin arkasinda nazar var [API aciklama]).
- Ilan bazinda cikan/giren etiket: ONCE_SONRA_234.csv (etiket_cikan, etiket_giren).

## 4. Aciklama
- Ilk paragrafin sonuna tek cumle: "A thoughtful choice for Cancer gifts and Libra gifts." Tekil ifade dilbilgisi icin a/an alir:
  "A thoughtful choice for an Aries gift and Libra gifts." / "... for a Pisces gift." Ayni burclu: "A thoughtful choice for Leo gifts."
  Serdar karari: aciklamada "gifts" kucuk harf mi (cumle ici) yoksa "Cancer Gifts" mi; karisik tekil/cogul cumle kabul mu.
- 234 aciklamanin hepsinde bos satir var ve ilk paragraf noktalamayla bitiyor; HTML entity yok [olcum, bagimsiz inceleme].
- 234/234 ilanda eklenir (hicbirinde ifade aciklamada yoktu [olcum]). Uzun/orta tire 0; metin_kurali.py ONCE_SONRA_234.csv GENEL PASS [olcum].

## 5. Uygulama (ayri onay)
- Arac: scripts/etsy/burc_gift_yaz.py (yeni). Etiketler virgullu tek metin olarak gonderilir (depodaki kanitli yol:
  dijital_donusum_uygula.py:170, kupa_ru.py B95). Aciklama cumlesi CANLI ilk paragrafa eklenir (sabit eski metinle eslesme aranmaz);
  cumle zaten varsa atlanir. Geri okuma 10 sn arayla en fazla 3 deneme (kupa_ru.py:111, B68). Ilan basina: GET (state active degilse ATLA; updateListing taslagi yayina alir,
  CLAUDE.md 7 Eyl) -> alan bazli idempotans (her alan: eski -> yaz, yeni -> atla, ikisi de degil -> DUR, o ilan listeden cikar)
  -> tek PATCH (title, tags, description) -> GET: uc alan birebir, state active, diger alanlar ayni. Yedek: ONCE GET Drive'a (yazmadan once).
- Istek: ilan basina 3 (GET, PATCH, GET) + geri okuma tekrari en fazla +2 + RU sayimi 1 -> 234 x 4-6 = 936-1.404 [TAHMIN]. Kota tabani 10 (CLAUDE.md); kalan 2992 [API].
- Sira: sahte-API testi -> bagimsiz inceleme -> Serdar onayi -> CANCER_LIBRA 3 ailesi (tek kosu, geri okuma, DUR, Serdar canli bakar)
  -> pilot 5 (her aileden, ayni burclu 1 dahil) -> kalan 226. Ilk FAIL'de DUR.
- Diger planlarla iliski (inceleme 3): yil donumu 77 ilan plani (PLAN_BY77 v2) ayni ilanlarin aciklamasina yazar ve by_baski_kaldir.py:157
  basligin degismedigini kontrol eder. Oneri sira: once BY77 isi (yeni alan bazli arac, PLAN_BASLIK 4), sonra bu is; bu arac aciklamayi
  canli metinden okudugu icin BY77 sonrasinda da calisir. Alternatif: tek kosuda birlestirme. Serdar karari. Pin metinleri (Metricool) ayri is.
- Etki: by78_kargo_sku_aciklama.py:366 ve by78_yayinla.py:139 baslik degisince DUR verir (eski betikler, yeniden kosulmaz).
- RU ceviri: kupa ilanlarinda RU katmani var (kupa_ru.py:2); poster/yil donumu olculmedi. Yedek adiminda GET translations/ru ile
  234 ilan sayilir; RU baslik/etiket guncellemesi ayri karar.
- Risk (TAHMIN, Etsy kilavuzu bu oturumda dogrulanmadi): poster basliklarinda "Gift/Gifts" 5 kereye kadar tekrar (22 ilan); Etsy kisa ve
  tekrarsiz baslik oneriyor.

## 6. Ornek: CANCER_LIBRA (3 aile)
| aile | once | sonra |
|---|---|---|
| poster | Cancer and Libra Couple Wall Art, Newlywed Gift, 1st Anniversary Gift, Engagement Keepsake | Cancer and Libra Couple Wall Art, Cancer Gifts, Libra Gifts, Newlywed Gift, 1st Anniversary Gift, Engagement Keepsake (117) |
| yil donumu | 1st Anniversary Gift for Husband, Personalized Cancer Libra Zodiac Couple Print with Names and Date, Paper Anniversary Card | A: 1st Anniversary Gift for Husband, Personalized Cancer Libra Zodiac Couple Printable Art, Cancer Gifts, Libra Gifts (114) / B: 1st Anniversary Gift for Husband, Cancer Libra Zodiac Couple Printable Art with Names and Date, Cancer Gifts, Libra Gifts (121) |
| kupa | Cancer and Libra Personalized Mug, Zodiac Symbols with Names, Gift for Couples | Cancer and Libra Personalized Mug, Cancer Gifts, Libra Gifts, Zodiac Symbols with Names, Gift for Couples (105) |
Etiket: poster cancer wall art, libra gift -> cancer gifts, libra gifts; yil donumu cancer zodiac gift, libra gift -> cancer gifts, libra gifts;
kupa zodiac symbols, zodiac gift -> cancer gifts, libra gifts. Aciklama (3 aile): + "A thoughtful choice for Cancer gifts and Libra gifts."

## Bagimsiz inceleme ozeti (22 Eki, tek ajan, salt okuma)
Dogrulanan: 234 satir, 78/78/78, ifadeler 3 alanda, 13 tekil etiket <=20, kisa baslik <=140, tire 0, ayni burclu tek ifade, iki okuma ayni.
| # | onem | bulgu | islem |
|---|---|---|---|
| 1 | ORTA | 2 posterde tekil+cogul etiket birlikte | etiket onceligi duzeltildi, 0 [olcum] |
| 2 | ORTA | B kisaltmasi "Personalized"i tamamen siliyor | A secenegi eklendi (89-130), oneri A |
| 3 | ORTA | BY77 ile sira celiskisi | canli ilk paragrafa ekleme + sira onerisi |
| 4 | ORTA | 20 Eki kaydi yalniz 78 poster | 0. bolum duzeltildi |
| 5 | ORTA | "Serdar onayi" kaynaksiz; yerlesim riski | karar Serdar'a, risk yazildi |
| 6 | KUCUK | bayat geri okuma, etiket formati, RU | 5. bolum |
| 7 | KUCUK | baslikta tekrar | risk yazildi |
| 8 | KUCUK | aciklama cumlesi buyuk/kucuk harf, karisik tekil/cogul | Serdar karari |
| 9 | KUCUK | kupa zayif etiket MI'siz | Serdar karari (zaten yazili) |
