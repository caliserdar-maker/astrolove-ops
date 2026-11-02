# STIL3_V5 yerel cikti (Merkez EK, 2 Kas 2026): Actions YOK, Serdar gorsel secimi icin

Betik `scripts/printful/ornament_ornek5.py` (a6c029e), yerel kosu (Pillow 11.0.0). Rakamlar `OLCUM.json`. Kapi sonucu: FAIL (yalniz RUBY kontrasti).
Bu yerel cikti ayrica bagimsiz incelemeden GECMEDI.

## Kaynaklar
- Ana sembol GERCEK: depo ffce7b62 db_pw_altin/veri/CANCER_LIBRA_ana.png, sha256 e86c2629629305fd... (Actions kosularindaki ile ayni).
- Kucuk Yengec / Terazi VEKIL (sha 1a34fa36..., 83871d5f...; gercekleri 2b5a3212..., 6fe2d035... yalniz Drive'da; 491 / 469 KB bu ortama alinamadi).
  Onizlemede kucuk burclar bu yuzden farkli gorunur. Gercekle yeniden uretim icin: dosyalar depoya konur ya da yalniz kopyalayan tek kosu.

## Sonuc (A secenekleri; T1 ve T2 ayni ton)
| satir | ton | kontrast (yeni olcut) | kapi |
|---|---|---|---|
| RUBY | altin 1.12 (V4, sabit) | 3.01 (isim1 3.01, isim2 3.20, tarih 3.66, halka uclari 4.84) | FAIL |
| BEIGE P1 (doku yalniz koyulastirir) | bronz 1.0, ana (84,54,14) | 5.08 | PASS |
| BEIGE P2 (duz ana ton) | bronz 1.0, ana (84,54,14) | 5.05 | PASS |
| AGED_PAPYRUS P1 | bronz 0.92, ana (77,50,13) | 4.54 | PASS |
| AGED_PAPYRUS P2 | bronz 0.85, ana (71,46,12) | 4.77 | PASS |

- RUBY V4 ayni olcutle 2.96 (V4 de gecmez). RUBY yazisinin koyu %5'i (161,94,14): doku + gomulu kenar (x0.2) koyulastirmasi.
  Oneri (karar Serdar): yazida doku yalniz acsin ya da yazida gomulu kenar kalksin; altin parlaklatmak istenmedi.
- Diger kapilar PASS: yasak / cakisma 0; bosluk 20/20/20 px (V4 10/12/11); sembol 425 x 404, ust y 246 (V4 262; 16 px yukari);
  isim satiri guvenli daireye 11.5 px; doku oge basina %5 (P2 yazilari duz, kapsam disi); halka kilidi goruntuden tepe y 163.0.

## Yontem degisiklikleri (V5 boyunca)
1. Kontrast (Serdar): acik zemin = zeminin koyu %5 / ogenin acik %5; koyu zemin = zeminin acik %5 / ogenin koyu %5. Zemin ogenin 6-12 px cevresi,
   oge alfa >= 0.9 murekkep (kenar yumusatmasi zemine karisir, disarida). Halka uclari: incelme bolgesinde genislik >= 2 px kismi kapida.
2. Aday listeleri: altin 1.0-1.36 (RUBY'de kullanilmadi, 1.12 sabit), bronz carpani 1.0-0.48; yalniz ANA ton koyulasir.
3. Yazilarda (isim, tarih, logo) golge tonu karisimi YOK (A). Bronz yazida acik uc = ana ton; P1 doku yalniz koyulastirir, P2 duz.
4. Halka gomulu kenar %20 (A; V4 %100): gorunus degisir, onizleme ve UC_T1_T2'de yan yana. Karar Serdar.
5. Leke kapisi (a): kapanis 3x3 + 2 px ice, alfa < 0.9 (alfa siniri yok); kaynak olceginde kapanis 9x9 (1600 px'e olcekli) + 5 px ice + kapali kucuk delik
   (alan < %0.1) + 24 px kenar payi. Kanit: onarimli ana 0, ayni sembole 20x20 yapay delik 400 px (FAIL veriyor); hedefte yapay 30 delik sayiliyor.
6. Terazi tepesi duz kesik (inceleme / UC_T1_T2): kaynak semboller 2 px payla kirpiliyordu; onarim (kapanis + asindirma) goruntu kenarini sinir
   saymadigi icin ust / alt 2 satirin alfasi 1'e zorlaniyordu. Duzeltme: onarim 24 px sifir kenar payiyla; kenar satirlarinda degisen piksel 0
   (Terazi onarimda degisen piksel 103 -> 9, Yengec 30 -> 10).

## Halka uclari (0.17 mm = 2 px, 300 dpi)
- 0.17 mm'den ince uc boyu: T1 sag / sol 19.1 / 19.2 mm, T2 25.4 / 25.7 mm (V4 9.6 / 10.2). 0.085 mm (1 px) alti: T1 12.9, T2 17.4 mm.
- 2 px alti kisimda kontrast 2.1-2.5 (bilgi): baskida silik kalma riski.

## Uzun isim (bilgi; karar Serdar)
- CAGLAYANGUL / MAXIMILIAN mevcut boyda sigmiyor. Yalniz yazi blogu 0.869 olcekte (buyuk harf 2.07 mm), sembol kucultulmeden tum duzen 0.557'de (1.33 mm).
- Aksan: CAGLAYANGUL Ğ / Ü buyuk harfin 7 px ustune, Ç cengeli tabanin 8 px altina.

## Dosyalar (bu klasor)
ONIZLEME_76mm_SECENEK.png (satirlar RUBY, BEIGE P1, BEIGE P2, AGED_PAPYRUS P1, P2; sutunlar V4 | A-T1 | A-T2), UC_T1_T2.png, UZUN_ISIM.png,
{satir}_{A-T1,A-T2}_954.png, OLCUM.json, KOSU_LOG.txt. Not: AGED_PAPYRUS etiketleri uzun, komsu kareye tasiyor (yalniz etiket).
