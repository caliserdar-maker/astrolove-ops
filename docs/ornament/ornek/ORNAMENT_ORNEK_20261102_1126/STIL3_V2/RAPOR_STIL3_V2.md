# STIL3_V2: SAPPHIRE_GOLD, EMERALD_GOLD, RUBY_GOLD (2 Kas 2026)

Kosu: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41436684361 (deneme 2/2, kapilar PASS).
Deneme 1: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41435681741, EMERALD okunurluk FAIL 3.31; asagida neden ve duzeltme.
Betik: `scripts/printful/ornament_ornek2.py` (dal ornament-printful-katalog, 7b7e565). Tum rakamlar `OLCUM_V2.json` (kosu olcumu).
1 px = 0.0847 mm.

## 0. Yerlesim (kapilar PASS)

| olcu | v1 | V2 | kazanc |
|---|---|---|---|
| halka dis capi | 554.1 px | 610 px (51.65 mm) | +%10.1 |
| ana sembol (en x boy) | 344 x 327 px | 378 x 358 px (32.0 x 30.3 mm) | +%9.9 |

- Halka tepesi y=222; Printful centik alti y=216.9. Halka delige ve centige girmiyor.
- Halka capi kapilar altinda en buyuk deger: Rc 360'tan 1 px adimla aranip ilk gecen Rc=303 secildi.
  - Bir buyuk Rc'yi (304) reddeden kapi: tarih guvenli daire sinirinin (380.3 - 15) disina tasiyor; Rc 305-306'da isim1 de tasiyor
    (OLCUM_V2.json arama_son_red). Halkayi buyutmeyi sinirlayan, altta yazilarin sigmasi.
- Guvenli daire (cap 760.6, merkez 477,477): en dis icerik merkezden 364.3 px, pay 16.0 px (esik 15).
- Yazi boylari degismedi: isim buyuk harf 2.38 mm, tarih 2.02 mm. Kucuk Cancer / Libra 4.91 / 5.08 mm.
- Sembol posterdeki oranda: genislik = 2084 / poster halka merkez cizgisi yaricapi 1670.1 x Rc. Merkez dy da posterdeki oranda.
- Sira ayni: kucuk semboller, EMILY ∞ JAMES, tarih. Araliklar daraltildi: sembol alti -> kucuk sembol 0.30, kucuk sembol -> isim 0.55,
  isim -> tarih 0.45 (isim buyuk harf yuksekligi biriminde; tasarim secimi).
- Cakisma (halka ve sembol 7 px genisletilmis) 0.

## 1-3. Halka

Poster halkasi (ornek-tek-doku 2a08a78, HALKA_BLUE_16x20.png) olculdu:
- Merkez (2399.2, 2402.5), merkez cizgisi yaricapi 1670.1 px.
- Genislik: tepe 19.5 px, yanlar yaklasik 10 px. Acik aralik 44-136 derece (0 = sag, 90 = asagi).
- Merkez cizgisi uclara dogru +20 px disa aciliyor.

V2 halka bu olculen merkez cizgisi ve genislik profiliyle (7 derece medyan) analitik cizildi. Genislik esit oranla tepe 7 px olacak sekilde buyutuldu; bu
"yeni sekil" degil, olculen profilin olceklenmis hali.

| bolge (aci) | genislik (px) |
|---|---|
| tepe 265-275 | 7.1-7.2 (0.60 mm) |
| omuz 241-301 | 4.1-6.9 |
| yanlar 0-11 / 171-211 | 2.9-4.0 |
| 215-225 ve 321-325 (posterdeki ince yerler) | 2.7-3.2 |

Uc geometrisi (sag uc; sol uc ayna):

| aci | 11 | 21 | 25 | 31 | 35 | 41 | 44 |
|---|---|---|---|---|---|---|---|
| genislik (px) | 2.97 | 2.08 | 1.78 | 0.87 | 0.63 | 0.32 | 0 |

- Genislik tekduze azalip keskin uca iniyor.
- Halka tek renk: tek doku modelinin Lmed rengi.
- Tam kapsamali (alfa > 0.99) piksellerin parlakligi tum acilarda 145.0 (min = max).
- Ucta renk ayni. Genislik 1 px altina inince (31-44 derece) tam kapsamali piksel kalmiyor; gorunen parlaklik yalniz kapsama oraninda azaliyor.
- Deneme 1'de boru profili ince bolgelerde tepe uretmedigi icin govde parlakligi 151-184 arasinda degisiyordu; tek renge gecildi.

## 4. Okunurluk

WCAG kontrasti. Yazi = cekirdek ortanca renk. Zemin = murekkebin 3-6 px cevresindeki bant: ortanca ve en acik %5 (parantez icinde).

| stil | yontem | isim1 | isim2 | tarih |
|---|---|---|---|---|
| SAPPHIRE once | - | 6.67 (5.86) | 6.98 (6.03) | 5.17 (4.68) |
| SAPPHIRE sonra | hale yok, altin %4 acik | 7.18 (6.31) | 7.47 (6.46) | 5.53 (5.01) |
| EMERALD once | - | 3.94 (2.92) | 4.57 (2.91) | 3.42 (2.31) |
| EMERALD sonra | hale s=0.5, altin %12 acik | 7.07 (5.99) | 7.91 (6.24) | 5.63 (4.55) |
| RUBY once | - | 5.89 (5.46) | 6.49 (6.01) | 4.60 (4.30) |
| RUBY sonra | hale yok, altin %12 acik | 7.26 (6.73) | 8.08 (7.48) | 5.62 (5.25) |

- Hedefler tuttu: SAPPHIRE ve RUBY en kotu deger > 5 (5.01 / 5.25), EMERALD >= 4.5 (4.55).
- Yontem: yazi altini (yalniz isim, sonsuz, tarih) luma x 1.04-1.12, ayni altin egrisiyle.
- Hale: zemin x (1 - s G). G = yazi murekkebi 7 px genisletilip sigma 2.5 bulanik, tepe 1. Yalniz isim, sonsuz ve tarih cevresinde.
- Arama: once en hafif hale; her hale degerinde altin en fazla %12.
- EMERALD'da s=0.5 yazilarin cevresinde gozle secilen koyu bir golge birakiyor; "cok hafif" degil. Merkez karari: kabul ya da EMERALD icin
  hedefin dusurulmesi ya da zemin degisikligi.
- Olcum bolgesi degisti: deneme 1'de "yazi kutusu + 6 px" idi; J inisi yuzunden harflerden 25-30 px uzak zemini de kapsiyordu ve
  hale oraya ulasmiyordu (EMERALD 3.31). Yukaridaki once / sonra degerlerinin ikisi de yeni bant yontemiyle; v1 tablosuyla dogrudan karsilastirilmaz.

## 5. Sonsuz

Kaynak alfa (siparis-gpt alfa_ogeler.npz) hedef olcekte 1.25 px genisletildi.
- 3x3 acmada kayip %0, bilesen 1: en ince cizgi >= 3 px.
- Iskelet uzerindeki en ince %2 tahmini 3.82 px.
- Genislik 5.08 mm.

## 6. Onizleme

- STIL3_V2_ONIZLEME_7cm.png: 827 px gorunen daire, koseler beyaz (saydamlik yok), asma deligi beyaz daire (merkez 477,164; cap 56.6).
- STIL3_V2_KILAVUZ.png: tam 954 baski dosyasi. Beyaz ince cizgi 827 px gorunen daire, mavi ince cizgi 761 px guvenli daire, kirmizi cizgi
  delik, mavi kisa cizgi centik alti (y=216.9), beyaz kisa cizgi gorunen dairenin tepesi.

## 7. Ana sembol ile ozgun cizim

Karsilastirilanlar: ham alfa siparis-gpt (6da763a) motor_gpt/girdi78/ana/cancer_libra_alfa.png (8185x7702) ve kullanilan katman
CANCER_LIBRA_ana.png alfasi.
- Ikisi de 0.5 esikte ikili, kucuk bilesen temizligi (yalniz hamda 1 piksel).
- Murekkep kutusuna kirpildi, 1200 px genislige esit oranla olceklendi.
- Olcek (0.95-1.05) ve oteleme aramasiyla hizalandi.

| | ham | ana |
|---|---|---|
| murekkep kutusu | tum tuval (0,0,8185,7702) | 305,293,3839,3636 |
| en / boy | 1.0627 | 1.0571 |
| alan / kutu | 0.1635 | 0.1599 |
| cizgi kalinligi / genislik | 0.03058 | 0.03086 |

| hizalanmis | deger |
|---|---|
| olcek / oteleme | 1.000 / (-1, 3) px |
| NCC | 0.957 |
| IoU | 0.900 |
| +-2 px icinde kalan murekkep | %98.6 |
| hamda olup anada +-2 px icinde olmayan | %1.45 |
| anada olup hamda +-2 px icinde olmayan | %1.37 |

Aciklama:
- Onceki 0.831 hizalamasiz olcumdu; hizalayinca 0.900.
- Kalan fark kenar bandinda: murekkebin %98.6'si 1200 px'te +-2 px icinde (genisligin %0.17'si). Cizgi kalinligi orani %1 farkli.
- En / boy farki (%0.5): ham alfanin murekkebi tuvalin dort kenarina degiyor, ana katmanda 300 px pay var. Fark yaklasik 6 px / 1200 dikey
  uzunluk; kenar cizim farkiyla (ChatGPT yuzeyi ile ham alfa kenari) uyumlu.
- Sekil ayni cizim; fark kenar duzeyinde. Bu bir yorumdur; noktasal fark haritasi uretilmedi.

## Dosyalar (Drive TEMP/ORNAMENT_ORNEK_20261102_1126/STIL3_V2/)

SAPPHIRE_GOLD_954.png, EMERALD_GOLD_954.png, RUBY_GOLD_954.png, STIL3_V2_ONIZLEME_7cm.png, STIL3_V2_KILAVUZ.png, OLCUM_V2.json,
KOSU_LOG.txt, KAYNAK_COMMIT.txt, RAPOR_STIL3_V2.md.
