# SIKILASTIRMA (Serdar 4 Kas: O2 b, O3 a, O4 a, O1 tamamlama): yerel testler ve bagimsiz inceleme (F)

## Yerel testler (cikis kodlari ayri; motor girdisi yalniz Actions, aquarius SAHTE)
- A1 test_workflows 0; A2 py_compile 0; A3 kova_kapi_testi (CL + lekeli sahte Kova) 0.
- Kapi testi O1: b1 tam dolu sahte Kova (kenara degen, ic leke yok) cikis 1, FAIL yalniz onarimsiz_kapi_iddia (kenar ve ic testi True);
  b2 lekeli sahte Kova cikis 0 (iddia 38447 px). KOVA_KAPI_TESTI_YEREL.json.
- Motor O3: sahte Kova ORN_KUCULT_SINIR_PX=-1 cikis 1, tek FAIL kucultme_le_sinir, 3 koyu PNG uretildi; =3 cikis 2 (gevsetme reddi). MOTOR_SINIR_YEREL.json.
- Mantik testi (sahte OLCUM): 22 vaka 0 (sinir okuma, onarimsiz neden, dusuk_kontrast, onayli kiyas). MANTIK_TESTI.json.
- Uctan uca: deneme 1 cokus (KeyError 'kati', dusuk_kontrast girdisi) -> duzeltildi; deneme 2 (CL gercek + sahte Kova) cikis 0, CL kontrol 0/0,
  onayli kiyas 0/0, onarimsiz neden PASS, uyari + 3 koyu yakin plan. UCTAN_UCA_YEREL.json.
- Uctan uca SONRASI degisiklikler (tam kosu tekrarlanmadi, deneme siniri): kontrast_ham (o1.kontrast 2 haneye yuvarliyordu; 2000 rastgele
  ciftte round(ham) = o1.kontrast; CL sade yeniden: SADE_1 bayt ayni, deger ayni); F duzeltmeleri (asagida).

## F bulgulari ve yanit
1. Drive adiminda eslesmeyen ls + pipefail adimi dusuruyordu: DUZELTILDI (find || true ile sayim; olmayan klasorde adim devam).
2. girdi_sha.txt onayli Kova sha satirlari sonra siliniyordu: DUZELTILDI (tee -a).
3. CANCER_LIBRA SADE kati ham 1,5372 < 1,54: CL SADE dusuk_kontrast listesine girer (bilgi; gorev "ham degerle kiyas, CL ayri bilgi alani,
   duzeyi degistirmez"). FILDISI CL 1,3121 / 2,4839 duzeyin ustunde. Duzey / kiyas bicimi Serdar'da.
4. onarimsiz_neden leke + baska FAIL'de PASS veriyordu: SIKILASTIRILDI (tek neden zorunlu; mantik testi vakasi eklendi).
   sade_kontrast ham alan yoksa yuvarlanmis degere dusuyordu: DUZELTILDI (ham zorunlu).
5. Zayif testler: mantik testindeki sabit "2 <= 2" vakalari CIKARILDI (motor baglantisi gercek motor kosusuyla); o2_sha_esit yapisi geregi
   esit = ZAYIF TEST (BEKLENEN_SONUC'ta not); O2 kaniti o2_kati_aqu + o2_bilinen_fail.
6. kova_kapi_testi yer_ic tuval siniri arka plan (np.pad): tam dolu sahte kaynakta kose secilmesin diye; CL kaynaklarinda ic leke 113 px degismedi
   (yerel); gercek Kova'da konum degisebilir, Actions'ta dogrulanir (ic > 0 sart).
7. GV beklentileri (varsayilan 2 px gecer, kenar onarimi yok) 2202 olcumunden, kenar_onar oncesi: dogrulanmadi (BEKLENEN_SONUC not).
Diger (dogru bulundu): GV sinir1 env'leri yalniz o adimda; dump motoru sinirdan once doner; onayli sha = 1f24d49 OLCUM; not_ ve genel cikis
tutarli; dal PNG korumasi; son-uretim pipefail ile || true kaldirilmasi etkili.
