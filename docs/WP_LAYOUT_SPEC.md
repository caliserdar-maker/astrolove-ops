# Wallpaper yerlesim spesifikasyonu (WP_LAYOUT_SPEC)

Kaynak: `WALLPAPER/FINAL_V2/CANCER_LIBRA` altindaki 16 onayli dosya,
`scripts/etsy/wp_measure_spec.py` ile olculdu
(workflow `wp-measure-spec`, kosu 33599412172, 2 Eyl 2026 06:34 UTC;
ham JSON artifact `wp-spec-CANCER_LIBRA`, 30 gun saklanir).

Bu dosya 77 cift icin uretim kuralinin KAYNAGIDIR. Buradaki her deger
olculmustur; tahmin edilen hicbir deger yoktur. Olcumun okuyamadigi
alanlar "ACIK" olarak isaretlenmistir ve uretime gecmeden once
kapatilmalidir.

Olcum yontemi: zemin = kenar bandi (%2) medyani; "ana kutu" = zeminden
14/255'ten fazla farkli en buyuk baglantili bilesen; "murekkep" =
40/255'ten fazla farkli piksellerin medyani. Dokulu zeminlerde (CI, WP)
ve gradyanli zeminde (MB) bu yontem poster KENARINI degil, zeminden
farkli PARLAK BOLGEYI bulur; bu durum tabloda "doluluk" ve "oran"
sutunlarindan okunur.

## 1. Tuval boyutlari (KILIT, 16/16 dogrulandi)

| Cihaz   | Boyut      | Oran   |
|---------|------------|--------|
| Phone   | 1440x3200  | 0.4500 |
| Tablet  | 2048x2732  | 0.7496 |
| Desktop | 3840x2160  | 1.7778 |
| Watch   | 1000x1220  | 0.8197 |

Dosya adi: `AstroLove_<Sign1>_<Sign2>_<Edition>_<Cihaz>.jpg`
(Edition: Champagne_Ivory | Midnight_Blue | Warm_Parchment | Deep_Black).
Boyut: FINAL_V2 dosyalari 124 KB - 1.7 MB.

## 2. Zemin renkleri (olculen, kenar bandi medyani)

| Edisyon | Phone        | Tablet       | Desktop      | Watch         | Kenar yayilimi (p95-p5) |
|---------|--------------|--------------|--------------|---------------|--------------------------|
| CI      | 214,174,127  | 219,182,136  | 230,203,175  | 243,221,194   | orta (26-82): vinyet var |
| MB      | 1,5,39       | 1,7,53       | 1,10,64      | 1,6,36        | dusuk-orta (2-69): gradyan |
| WP      | 160,73,5     | 181,97,12    | 213,160,80   | 232,200,136   | YUKSEK (95-159): doku, kenar koyu |
| DB      | 0,0,0        | 0,0,0        | 0,0,0        | 0,0,0         | 0: saf siyah, duz |

Kural (turetilen): DB zemini saf siyah ve duzdur. CI/MB/WP'de zemin
"tek renk" degildir; posterin kendi zemini (kagit/gece/parsomen) kenara
dogru koyulasarak tuvali doldurur. Bu uc edisyonda ayri bir "tuval
zemini" boyanmaz; poster dokusu tuvalin tamamini kaplar.

## 3. Ana kutu olcumleri (l,t,r,b piksel; yuzde = tuvale gore)

### Deep Black (temiz okuma; zemin duz oldugu icin ogeler tek tek ayristi)

| Cihaz   | Fuzyon sembolu orta parca | Halka (cember) bbox        | Halka merkez % | Halka genislik % | Metin blogu (isim+tagline) | Metin merkez y % |
|---------|---------------------------|----------------------------|----------------|------------------|----------------------------|------------------|
| Phone   | 386,1269,1035,1553        | 183,868,1257,1746          | 50.0 / 40.8    | 74.6             | 107,1724,1357,2658         | 68.5             |
| Tablet  | 549,1078,1472,1481        | 260,507,1788,1755          | 50.0 / 41.4    | 74.6             | 152,1725,1930,2700         | 81.0             |
| Desktop | 1476,640,2338,1016        | 1207,107,2633,1271         | 50.0 / 31.9    | 37.1             | 285,1245,3603,2154         | 78.7             |
| Watch   | 106,523,867,854           | yok (yalniz sembol)        | -              | -                | yok                        | -                |

DB Watch sembol kutusu (3 bilesen birlesimi): **106,236,895,976**
(789x740; merkez %50.0 / %49.7; genislik %78.9). Cancer-Libra fuzyonu
3 parcalidir (B64); 55 ciftte tek parcadir, kutu birlesimle alinir.

Murekkep (altin) DB: 223-232, 161-172, 46-53 -> **(225,165,48)** bandi.
Metin blogu rengi DB: (218-222, 164-166, 55-56).

Turetilen DB kurali: siyah tuval; halka+sembol grubu yatayda tam merkez;
Phone ve Tablet'te halka genisligi tuvalin %74.6'si, Desktop'ta %37.1'i
(yani Desktop'ta halka, yukseklige gore olceklenmis: 1164 px = %53.9 H);
metin blogu halkanin altinda, Phone'da y merkez %68.5, Tablet %81.0,
Desktop %78.7. Poster kagidi GORUNMEZ (siyah = zemin).

### Champagne Ivory (dokulu; ana kutu = parlak kagit bolgesi)

| Cihaz   | Ana kutu           | Doluluk | Oran w/h | Ic kagit rengi | Murekkep     | Not |
|---------|--------------------|---------|----------|----------------|--------------|-----|
| Phone   | 35,0,1429,3200     | 0.886   | 0.436    | 225,192,154    | (acik: 234,214,192) | kagit tuvali doldurur, kenarda vinyet |
| Tablet  | 80,0,1993,2732     | 0.966   | 0.700    | 228,199,167    | (acik)       | ayni |
| Desktop | 680,0,3224,2160    | 0.913   | 1.178    | 236,219,201    | 96,60,30     | orta bolge parlak; yan bantlar 0-324 ve 3538-3840 koyu |
| Watch   | 104,522,871,858 (sembol orta parca) | 0.142 | 2.28 | -        | 95,55,31     | 303 bilesen: doku gurultusu; ACIK |

CI'da "murekkep" olcumu Phone/Tablet'te kagidin acik tonunu yakaladi
(zeminden farkli en belirgin piksel = kagit, cizgi degil). CI cizgi
rengi Desktop ve Watch'tan okunur: **(95-96, 55-60, 30-31)**.

### Midnight Blue (gradyanli; ana kutu = acik lacivert gokyuzu bolgesi)

| Cihaz   | Ana kutu           | Doluluk | Oran w/h | Ic ton      | Not |
|---------|--------------------|---------|----------|-------------|-----|
| Phone   | 0,239,1440,2972    | 0.766   | 0.527    | 1,10,64     | ust 239 px ve alt 228 px koyu bant (2970-3200: 27 bilesen = metin?) |
| Tablet  | 202,0,1875,2732    | 0.831   | 0.612    | 1,14,79     | yan bantlar koyu |
| Desktop | 596,0,3287,2160    | 0.928   | 1.246    | 0,17,92     | yan bantlar koyu |
| Watch   | 101,50,902,1141    | 0.783   | 0.734    | 0,11,63     | **3:4 dikdortgen (801x1091)** = tam poster |

MB murekkep (altin) bu yontemle okunamadi (parlak bolge gokyuzu; altin
cizgiler kucuk). ACIK.

### Warm Parchment (agir doku; kenar bandi kendisi koyu)

| Cihaz   | Ana kutu           | Doluluk | Oran w/h | Not |
|---------|--------------------|---------|----------|-----|
| Phone   | 0,0,1440,3200      | 0.940   | 0.450    | parsomen tuvalin tamami |
| Tablet  | 0,0,2048,2732      | 0.931   | 0.750    | tuvalin tamami |
| Desktop | 456,0,3510,2160    | 0.907   | 1.414    | orta bolge parlak; yan bantlar 0-464 ve 3440-3840 koyu |
| Watch   | 100,0,968,1220     | 0.530   | 0.712    | 729 bilesen: doku; ACIK |

WP murekkep: Watch'ta (141,83,27) bakir-sepya okundu; Phone/Tablet'te
olcum parsomenin acik lekelerini yakaladi. Cizgi rengi icin Watch degeri
esas alinir; dogrulama ACIK.

## 4. Turetilen uretim kurallari (KILIT adaylari)

1. **Tuval boyutlari** bolum 1'deki gibi; JPEG, sRGB. (KILIT)
2. **Phone ve Tablet, CI/MB/WP:** poster sanat eseri tuvali TAMAMEN
   doldurur (cover), esnetme yok, sembol yatayda merkez (olculen merkez
   x %50.0-50.8). Ayri tuval zemini boyanmaz. (KILIT)
3. **Desktop, CI/MB/WP:** poster yuksekligi tuval yuksekligine oturur
   (0-2160), sanat eseri merkezde; parlak bolge genisligi edisyona gore
   %66-80 (CI 2544, MB 2691, WP 3054 px). Yan bantlar posterin kendi
   koyu kenar dokusuyla (CI 0-324 / 3538-3840, WP 0-464 / 3440-3840)
   doldurulmus; **bantin nasil uretildigi (ayna / uzatma / vinyet)
   olcumden okunamiyor. ACIK - 77 cift icin ayni yontem gerekli.**
4. **Deep Black, tum cihazlar:** siyah zemin + oge yerlesimi, bolum 3'teki
   yuzdeler. Uretim hattinda DB posterinden halka+sembol+isim+tagline
   maskesi (altin, esik B47 db_cool degil, ham DB poster) cikarilir ve bu
   yuzdelerle yerlestirilir. (KILIT adayi; uc cihazda tutarli olculdu)
5. **Watch:** B93 karari "YALNIZ ozgun sembol, baska hicbir oge yok".
   Olcum bunu YALNIZ DB'de dogruluyor (3 bilesen, kutu 106,236,895,976).
   MB Watch'ta 3:4 tam poster dikdortgeni var (801x1091); CI ve WP
   Watch'ta doku gurultusu nedeniyle icerik ayristirilamadi.
   **ACIK - Watch dosyalari 4 edisyonda tutarli degil; uretime gecmeden
   Mo karari + tek ornekte gozle dogrulama gerekir.**
6. **Tagline "Two Souls · One Bond":** yalniz DB'de metin blogu olarak
   ayristi (isimle birlikte, bolum 3). CI/MB/WP'de kagit dokusu metni
   ayristirmadi. Konum ve font olcumu ACIK; DB metin blogu merkezleri
   (Phone %68.5, Tablet %81.0, Desktop %78.7) referans alinabilir.

## 5. Acik isler (uretim oncesi kapatilacak)

- [ ] Olcum V2: polarite-farkli (acik/koyu kagit) ve doku-dayanikli
      murekkep maskesi (yuksek gecirgen filtre + Otsu; B63 polarite
      kurali) ile CI/MB/WP'de halka, sembol, isim ve tagline kutulari.
- [ ] Desktop yan bant yontemi (madde 3).
- [ ] Watch icerik karari (madde 5).
- [ ] Tagline font/boyut/konum (madde 6).
- [ ] Kaynak poster hangi klasorden: OHR 3X4 (9375x12500) mi, OPTIMIZED
      3X4 (7200x9600) mi. Phone 1440x3200 icin 7200x9600 yeterlidir;
      Desktop 3840 genislik icin de yeterlidir. Oneri: OPTIMIZED (B84
      wallpaper hatti OHR kullanmisti; yeni tasarim icin gerek yok).
- [ ] Tek ciftte (CANCER_LIBRA) uretim ciktisi FINAL_V2 ile piksel
      karsilastirmasi: fark gurultu tabanina inmeden 77'ye gecilmez
      (B68 yontemi).

## 5a. Kararlar (Mo, 2 Eyl 2026)

| # | Konu | Karar |
|---|---|---|
| 1 | Olcum V2 | (a) Yuksek gecirgen filtre + Otsu ile yeniden olcum: `scripts/etsy/wp_measure_spec_v2.py`, workflow `wp-measure-spec-v2`. Sonuclar bolum 7'ye islenir. |
| 2 | Desktop yan bant | V2 olcumde bant kesitleri alinir; ayna/uzatma karari olcumden sonra, tahminle secilmez. |
| 3 | Watch | (a) B93 kurali KALIR: yalniz ozgun sembol. MB (gerekirse CI/WP) Watch dosyalari yeniden uretilir; pilot ZIP guncellenir. Referans kutu: DB 106,236,895,976. |
| 4 | Tagline | (c) V2 olcumle posterin kendisinde olup olmadigi dogrulanir; sonra karar (buyuk olasilikla poster ici, ayri basilmaz). |
| 5 | Kaynak poster | (a) POSTERS/OPTIMIZED_FOR_PRODUCTION/[ED]/3X4 (7200x9600). OHR kullanilmaz. |
| 6 | Pilot kiyas esigi | (a) DB: ortalama mutlak fark < 1.0 ZORUNLU; CI/MB/WP: < 3.0 + Mo gozle. Esik saglanmadan 77'ye gecilmez. |
| - | SET04 | Secenek A: 3000x2250 yeniden render, wp-mockup hattinin ILK ciktisi olarak (pilotta dogrulanir). 31 Agu dosyasi (farkli kompozisyon) ELENDI. |

## 6. Pilot Etsy durumu (etsy-verify, 2 Eyl 2026 06:33 UTC)

Listing 4565911475: **active**, 3.99 USD, bolum 60120017, 6 gorsel
(sira SET01-03-04-06-07-10Y, imza eslesmesi 6/6 skor 1.000), 1 video
(840266730), 5 dijital dosya (4 ZIP + PDF). Bulgu: rank 3 (SET04)
2048x1536, digerleri 3000x2250; B93 madde 4 standardi 3000x2250.
