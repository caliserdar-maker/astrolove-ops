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
- SADE: zemin seffaf (maske disi alfa 0), leke 0, tasma 0
- BILGI: acik zemin kati kontrast (SADE 1.54 ve FILDISI 2.53 Serdar istisnasi)

## Her cift icin OLCUM.json'a yazilanlar
guvenli daire disi px, delik yasak bolgesi px, ust yasak px, kontrast ortancasi (stil basina), dE00 maks, IoU, alfa farki, sembol kutusu
(x0, y0, x1, y1) ve olcek, halka konumu (kutu), kucuk burc hedef yuksekligi, kapi sonuclari.
