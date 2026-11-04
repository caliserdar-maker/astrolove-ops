# ORNAMENT_78_ORNEK6: kapi listesi (kosudan ONCE yazildi, 3 Kas 2026)

Kaynak: onayli son uretim kosusu 41668820617 (5 stil, CANCER_LIBRA) ve ornament_motor.py kapi sozlugu (deneme 4 ayarlari).
Yeni esik YOK; yeni 5 cift icin ayni kapilar uygulanir, her cift x stil olculen deger OLCUM.json'a yazilir.

## Kontrol cifti (CANCER_LIBRA)
- 5 stil PNG, onayli ORNAMENT_5STIL_20261103_1539 (6daab364) dosyalarina ham pikselde en buyuk fark <= 1 seviye ve farkli piksel <= 10 / dosya.
- FAIL ise diger ciftlere bakilmadan DUR (Drive yok).

## Koyu 3 renk (RUBY, SAPPHIRE, EMERALD), cift basina
1. kontrast ortancasi (koyu zemin) >= 4.5 (isim1, isim2, tarih, kucuk_sol, kucuk_sag, sonsuz, halka govdesi); koyu %5 bilgi
2. kucuk oge ile ana sembol arasi dE00 (son dosya, ham) <= 2.0
3. kucuk burc ve logo IoU >= 0.98; isim / tarih / halka alfa farki (murekkep bolgesi) <= 0.035
4. leke 0 (oge alfa leke + kaynak leke), tasma 0 (goruntu yasak: delik, guvenli daire disi, ust yasak bolge px)
5. ton (renk sadakati + Lab kaynak araligi)
6. yerlesim: bosluk 20/20/20 px; sembol kutusu (CANCER_LIBRA'da ust y 246; yeni ciftte olculur, kutuya orani bozulmadan sigar, alt kenar kucuk burc satirinin 20 px ustu)
7. BILGI: halka govde surekliligi (CANCER_LIBRA 0.692-0.693, Serdar kabul), hucre dE00 (zemin)

## SADE ALTIN ve FILDISI, cift basina
- delik ve guvenli daire disi px = 0 (oge maskesi ile, yerlesim kapisi)
- SADE: zemin seffaf (maske disi alfa 0), leke 0, tasma 0 (sert: sade1_leke_0, sade1_tasma_ve_yasak_0, sade1_zemin_seffaf, sade1_yerlesim_ayni)
- O2 b (Serdar 4 Kas): SADE ALTIN = SADE_1_ALTIN_TONU (aday 1), altin KOYULASTIRILMAZ (ORNAMENT_KARAR 18); FILDISI girdisi ayni dosya.
  SADE kontrast kapisi YOK (sert degil).
- BILGI (dusuk_kontrast listesi, ham deger): SADE kati < 1,54 (3 Kas CL SADE olcumu); FILDISI kati < 1,31 YA DA ortanca < 2,48
  (O4 a, ORNAMENT_KARAR 24 onayli istisna duzeyi, CL). FILDISI listesindeki ciftler 78 sonrasi Serdar goz onayina.
  (Eski "FILDISI 2.53" Merkez olcumuydu, yontem kayitli degil; duzey 4 Kas kararlarina gore 1,31 / 2,48.)

## Ek sert kapilar (Serdar 4 Kas sikilastirma)
- kucultme_le_sinir (motor, O3 a): sigmayan sembolde toplam kutu kucultmesi <= 2 px (koda sabit; test parametresi ORN_KUCULT_SINIR_PX yalniz
  <= 2). FAIL ciftinde 5 stil PNG yine uretilir, gercek boy onizleme otomatik, is durur ve gorsel Serdar'a. 10 denemede sigmazsa gorsel yok.
- kenar_onarimsiz_neden_leke (ornek78, ORNEK78_KENAR_ZORUNLU ciftleri, O1): onarim kapaliyken motor cikis 1 ve nedeni leke_a_kaynak_0
  (kaynak lekesi onarilan kaynakta > 0). Kapi testi: kova_kapi_testi mod_kapali.onarimsiz_kapi_iddia (gercek Kova onarimsiz kapi > 0).
- onayli_kiyas_<STIL> (ornek78, ORNEK78_ONAYLI_EK): onayli dosyalara <= 1 seviye / <= 10 px (CL kontrolu ile ayni tolerans).
- Kenar onarimi (kenar_onar) bir kaynagi degistirirse ::warning:: + OLCUM kenar_onarim_uyari (FAIL degil); 954 once / sonra 3 koyu stil yalniz Drive.
- Zayif test (KALITE 3): varsayilan modda leke_a_kaynak_0 onarim sonrasi olculur, FAIL veremez; bilinen FAIL onarim kapali modda.

## Her cift icin OLCUM.json'a yazilanlar
guvenli daire disi px, delik yasak bolgesi px, ust yasak px, kontrast ortancasi (stil basina), dE00 maks, IoU, alfa farki, sembol kutusu
(x0, y0, x1, y1) ve olcek, halka konumu (kutu), kucuk burc hedef yuksekligi, kapi sonuclari.
