# KOVA DUZELTME (Serdar 4 Kas O1 + "a"): yerel sonuc ve bagimsiz inceleme (F)

## D hesap satiri (olcum: gercek_boy_kontrol.py, GERCEK_BOY_KONTROL_YEREL.json)
- 1 px = 25,4/300 mm. Tuval 954 px = 80,77 mm; kesim capi 2 x 449 px = 898 px = 76,03 mm (ORNAMENT_KARAR 6).
- Bilinen PASS: yeni gercek boy onizleme (300 dpi, kesim r 449) PASS.
- Bilinen FAIL: deneme 3 GEMINI_VIRGO_SADE_GERCEK_BOY_76mm.png (318,85 dpi, tuval 76,0 mm, kesim 71,54 mm) FAIL; %95 yeniden orneklenmis kopya FAIL.
- Sinir (zayif yan): kontrol cizgiyi ciziciyle ayni sabitlerden dogrular; 954 PNG'nin icerik olcegini olcmez.

## Yerel testler (cikis kodlari ayri)
- test_workflows.py 0; py_compile (6 dosya) 0.
- kova_kapi_testi (CL kaynaklari + CL ana bilinen PASS, sahte buyuk Kova kenar zorunlu): 0. CL kaynaklari ve CL ana kapi 0 px; ic yapay leke 113 px
  (CL), 1009 px (sahte Kova); kenar (ii) sahte Kova y 0-2 bandinda 107 px; kucuk kaynaklarda kenar 0 = "kenar bandi kor (ice 4-5 px)", bilgi.
- Testin kendi bilinen FAIL'leri: lekeli kaynak --pass listesinde -> 1; zorunlu kaynak (aquarius) eksik -> 1.
- ornek78 uctan uca (CL gercek + sahte Kova): 0; CL kontrol 5 stil 0 seviye / 0 px; onarimsiz motor 1 (beklenen); KENAR_ONARIM ve yakin planlar uretildi.

## F bagimsiz inceleme bulgulari ve yanit
1. Drive adiminda hata sessiz (set -e yok, ID [0]): DUZELTILDI (set -euo pipefail, tek eslesme assert, Sonuc Drive'i kontrol eder).
2. Varsayilan modda kaynak leke kapisi (koyu_leke_a_kaynak_0) kenar_onar SONRASI olculur, FAIL veremez: ZAYIF TEST. 518904f'ten beri tasarim
   (Merkez incelemesi madde 1). Yontem degistirmez; bilinen FAIL KAPALI modda. Karar Serdar'da. "gizlendi" alani yapisi geregi True (bilgi).
3. Ana yolu denenmiyordu: DUZELTILDI (--pass_ana CL ana bilinen PASS 1600 olcek; --ana AQUARIUS_PISCES_ana bilgi).
4. Bilesen listesi raster sirasiyla kesiliyordu: DUZELTILDI (alana gore sirala, sonra 40).
5. gercek_boy_kontrol.py git'e eklenmemisti: EKLENDI. Kontrol kismen totolojik: karo 1:1 (954) ve her karo kontrolu eklendi; ikinci bilinen FAIL
   (yeniden orneklenmis) eklendi; sinir yukarida yazili.
6. Kenar (ii) yalniz ust/alt ve alfa > 0.99 istiyordu, sayim disk icinde: DUZELTILDI (dort kenar, kapi esigi alfa > 0.5, sayim disk ve kenardan ilk 3 px).
   Gercek Kova'da denenmedi (kaynak yalniz Drive): Actions kosusunda.
7. Acik moddaki alfa farki yapay lekeye ozel degildi: DUZELTILDI (disk icinde alfa farki).
8. Dusuk: ETIKET_O2 kapi FAIL'inde "?" ile yaziliyordu (DUZELTILDI: olcum yoksa ::error:: eksik); D tanimsiz olabilirdi (DUZELTILDI: ilk adimda,
   kosu no'lu); ayni adli klasor (DUZELTILDI: tek eslesme); aquarius sha beklenen listede sabit degil (ACIK: Drive md5 kapisi var, sabit sha yok).
9. Motor varsayilan ciktisi degismedi (CL n0 = 0 ayni nesne). OLCUM anahtar adlari degisti (alfa_degisimi_en_buyuk -> alfa_farki_en_buyuk,
   onarim_oncesi_leke_px -> n0); okuyan kod yok.
