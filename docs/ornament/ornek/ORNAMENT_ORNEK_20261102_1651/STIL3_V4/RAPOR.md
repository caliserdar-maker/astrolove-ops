# STIL3_V4: halkali + halkasiz x RUBY / SAPPHIRE / EMERALD (2 Kas 2026)

Kosu (gecerli): https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41485011606 (deneme 2/2; kapilar PASS).
Deneme 1: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41480832147 (PASS; Drive TEMP/ORNAMENT_ORNEK_20261102_1624, GECERSIZ).
Bagimsiz inceleme deneme 1'de 2 yuksek, 5 orta, 6 dusuk bulgu buldu. Deneme 2 duzeltilebilenleri duzeltti; kalanlar asagida acik.
Betik: `scripts/printful/ornament_ornek4.py` (7c87fc1). Rakamlar `OLCUM.json` (kosu olcumu). 1 px = 0.0847 mm.

## Printful 900 sablonu (Serdar'in verdigi resmi PSD, Merkez olcumu): yeni / eski

| olcu | yeni (V4) | eski (V3) |
|---|---|---|
| guvenli daire | merkez (476, 477), r 380 | merkez (477, 477), r 380.3 |
| delik | merkez (476, 163); yasak r 34, delik r 25 | (476.7, 163.9), r 28.3 |
| ust yasak | y < 221 (delik alti kirmizi yay, en alt y 220) | y < 217 + centik |
| kesim dairesi (onizleme) | r 448.8 = 7.6 cm (hesap: 38 mm x 11.81 px/mm; 900 aciklamasi 2.99 inc) | r 413.5 = 7 cm (881'in olcusu, yanlis urun) |

Ogeler buyutulmedi (%8 buyutme iptal).

## Kapilar (6 dosya, PASS)

| kapi | sonuc |
|---|---|
| son goruntude guvenli daire disi (golge / isik dahil) | 0 piksel; gercek pay 7.9-8.4 px |
| delik r 34 ve y < 221 icinde, halka disi | 0 piksel (halka muaf; halkasizda en ust icerik y=225) |
| cakisma | 0 |
| isim ve tarih kontrasti >= 4.5 (kati olcut) | PASS, en dusuk 4.53 (halkasiz EMERALD tarih) |
| halka tepe merkez cizgisi = delik merkezi | y 163.0 |
| halka govdesi >= 4 px | en ince 4.04 px (pay 0.04) |
| gorunen doku %4-6, OGE BASINA | 4.99-5.01 |
| isik tasmasi 4-10 px | p95 4.5-5.0 px, en fazla 7.0-7.2 px |

## 1 HALKA

- Tepe merkez cizgisi delik merkezinden (476, 163) gecer. Merkez x 476 (sablon); deneme 1'de 477'ydi.
- Yari eksenler 343.0 / 347.6, oran 0.9868 (poster, degismedi).
- Dis genislik 690 px (58.4 mm), V3'e gore +%7.8. Sol / sag pay 345 / 345 px (simetrik).
- Sinirlayan: guvenli daire + isik payi 8 px.
- Ana sembol halkayla oranli buyudu: 428 x 406 px, V3'e gore +%7.8.
- Halka murekkebinin yaklasik %6'si delikte kalir ve delinir (tepede yaklasik 4 mm bosluk; inceleme olcumu deneme 1). Istenen geometrinin dogal sonucu.

## 2 HALKA PROFILI (posterden olculen, birebir goreli)

Govde medyani 4.39 px, tepe 7.81 px (posterde medyan 11.4, tepe 20.3; oran ayni). Uc profili, genislik / govde medyani:

| uca uzaklik (yay %) | 20 | 15 | 10 | 8 | 5 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| V4 sag / sol | 1.03 / 0.99 | 0.88 / 0.88 | 0.68 / 0.55 | 0.50 / 0.46 | 0.25 / 0.24 | 0.09 / 0.07 | 0.04 / 0.04 | 0.01 / 0 |
| poster sag / sol | 1.01 / 0.98 | 0.87 / 0.87 | 0.67 / 0.55 | 0.49 / 0.48 | 0.27 / 0.25 | 0.07 / 0.07 | 0.04 / 0.04 | 0 / 0 |

- Incelme %15-20'de baslar, kil inceliginde biter.
- UYARI: genislik son yaklasik %4.8'de 1 px'in altinda (~6 mm / uc). Bu kisim baskida cok silik ya da gorunmez olabilir. Posterde ayni goreli profil %2.1-2.4.

## 3 LOGO (LOGO_1 sag yarisi, birebir)

- Yalniz olcek (0.1406) + altin renk. Yukseklik = isim buyuk harfi, 90 x 28 px.
- Kalinlastirma, birlestirme ve yeniden cizim yok. Inceleme dogruladi: hedef alfa kaynagin INTER_AREA kucultmesi, fark 0.
- IoU 0.942. Bu gidis-donus olcusu kalin cizgilerin agirliginda; ince cizgi sadakatini gostermez.
- En ince cizgi hedefte 0.16 px (p1). Medyan 2.13 px. Hedef >= 2 px TUTMUYOR.
- Hedefte logo 4 parcaya bolunur, ic bosluk kaybolur. Kaynak murekkebin %22'si hedefte 2 px'ten ince cizgide.
- 2 px icin logo genisligi en az 1113 px olmali (p1). Ornament 954 px oldugundan hicbir boyda tutmaz.
- Oneriler (karar Serdar'da):
  1. Kucuk boy logo (Merkez onerisi): sekil birebir; yalniz 2 px altindaki ince cizgiler elle 2 px (0.17 mm) yapilir. Tek tip genisletme uygun degil: 2 px icin 7 px gerekir, IoU 0.53'e duser, 14 sahte ic bosluk olusur.
  2. Logo daha buyuk: hicbir boyda 2 px tutmaz; yalniz kalin govde okunur.
  3. Sadelestirilmis isaret: dis siluet dolu (ic sac cizgileri yok) ya da V3 sonsuzu. Sekil degisir.

## 4 BUTUNLESME

- **Gomulu kenar:** sol ust ic kenar koyu (zemin x 0.45, %55), sag alt ic kenar acik (zemin x 1.9, %40). Halka, sembol ve kucuk sembollerde tam.
- **CELISKI (Merkez karari gerekir):** isim, tarih ve logoda gomulu kenar opakligi x0.2.
  - Tam opaklikta kontrast 3.1-3.5'e iner, ton kazanci 1.30'da bile 4.5 tutmaz.
  - Yani "tum altin ogeler ayni butunlesme" ile "kontrast >= 4.5" ayni anda saglanamiyor.
- **Ana sembolde gomulu kenar etkisi zayif:** kaynak sembolun kendi kabartmasi "kabarik, isik sol ust" okunuyor; gomulu kenar "cukur" der ve yalnizca 1-4 luma fark birakir (inceleme olcumu). Isik yonu ayni (sol ust).
- **Sicak altin isik tasmasi:** (255, 196, 110), opaklik 0.16, sigma 3, en fazla 8 px. Olculen p95 4.5-5.0 px; 0-1 px'te yaklasik +8.5 luma.
- **Doku:** zeminin kendi yuksek gecirgen dokusu, overlay. Opaklik oge basina ayarli; her ogede gorunen %5.0.
  - Olcu: dokulu - dokusuz luma std / dokusuz luma ortalamasi.
  - Deneme 1'de toplu olcu %4.7-5.0'ti; oge basina halka ve tarih %4'un altindaydi (inceleme). Duzeltildi.
- **Golge tonu:** ogenin kendi murekkep ortancasindan en az %30 koyu tonlara zemin rengi %28 karisir (aradaki tonlarda dogrusal).
  - Olculen golge tonunda ortalama karisim 0.28. Sembolde golge tonu payi %6.3-6.4.
  - Duz renkli ogelerde (halka, isim, tarih, logo) golge tonu yok, karisim 0.
  - Deneme 1'de formul nedeniyle fiilen 0'di (inceleme). Duzeltildi.
- V3'teki dis golge (sag alt) kaldirildi.
- Altin ton kazanci: halkali 1.12 / 1.08 / 1.12, halkasiz 1.12 / 1.08 / 1.12 (RUBY / SAPPHIRE / EMERALD).

## Okunurluk (kati olcut: alfa > 0.5 tum murekkep ortancasi / murekkebin 1-12 px cevresi ortanca ve en acik %5)

| | isim1 | isim2 | tarih |
|---|---|---|---|
| HALKALI RUBY | 5.55 / 5.08 | 5.40 / 4.96 | 4.97 / 4.58 |
| HALKALI SAPPHIRE | 5.22 / 4.88 | 5.28 / 4.95 | 4.88 / 4.58 |
| HALKALI EMERALD | 5.54 / 4.91 | 5.52 / 4.91 | 5.10 / 4.54 |
| HALKASIZ RUBY | 5.49 / 5.02 | 5.30 / 4.85 | 5.07 / 4.69 |
| HALKASIZ SAPPHIRE | 5.18 / 4.84 | 5.20 / 4.91 | 4.88 / 4.61 |
| HALKASIZ EMERALD | 5.47 / 4.85 | 5.44 / 4.85 | 5.07 / 4.53 |

Not (inceleme): ortanca olcut murekkebin %32-42'sinin 4.5 altinda kaldigini gizler (kenar yumusatmasi; p10 yaklasik 2.7).

## B) HALKASIZ

- Sembol 444 x 421 px, V3'e gore -%3.3.
- Neden: yeni ust yasak (y < 221, eskisi 217) ve isik payi (8 px). Isigin gorunen uzanimi yaklasik 5 px; pay daha da daraltilirsa yaklasik %1-2 geri gelir (hesap).

## Inceleme bulgulari (deneme 1) ve durum

| bulgu | durum |
|---|---|
| Y1 golge tonu %28 fiilen 0 | duzeltildi (golge tonunda 0.28) |
| Y2 yazida gomulu kenar x0.2 | celiski raporda; Merkez karari |
| O3 sembolde kabartma yonu celiskisi | raporda |
| O4 doku toplu olcu | oge basina olcu ve ayar |
| O5 logo gorunurde birebir degil, 3 oneri eksik | raporda, OLCUM logo_oneriler |
| O6 halka ucu son %4.8 < 1 px | raporda (uyari) |
| O7 halkasiz kucuklugunun nedeni | isik payi 10 -> 8; neden yazildi |
| D8 halka 3 px buyuyebilir | pay 8 ile ax 341 -> 343 |
| D9 merkez 477 / 476 | 476 |
| D10 isik kapisi FAIL veremez | kapi p95 >= 4 ve en fazla <= 10 |
| D11 kontrast dagilimi | not raporda |
| D12 halkanin delikte kalan kismi | raporda |
| D13 commit / adim adi, docstring | duzeltildi |

Deneme 2 ciktisi ayrica yeniden bagimsiz incelenmedi.

## Dosyalar (Drive TEMP/ORNAMENT_ORNEK_20261102_1651/STIL3_V4/)

- {RUBY,SAPPHIRE,EMERALD}_GOLD_{HALKALI,HALKASIZ}_954.png (6)
- ONIZLEME_76mm.png: ust satir halkali, alt satir halkasiz; soldan RUBY, SAPPHIRE, EMERALD; 7.6 cm kesim dairesi disi ve delik (r 25) beyaz; 300 dpi.
- OLCUM.json, KOSU_LOG.txt, KAYNAK_COMMIT.txt, RAPOR.md.
