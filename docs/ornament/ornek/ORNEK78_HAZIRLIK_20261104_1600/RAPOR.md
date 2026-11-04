# ORNEK78 HAZIRLIK (1. kısım; koşu yok) — Serdar 4 Kas onayları, PLAN_78_URETIM.md 9f88868

## Test çıkış kodları (her biri tek başına, pipefail)
- A (başta ve commit öncesi): test_workflows 0 (495 YAML); py_compile 10 dosya 0; kova_kapi_testi yerel iki mod 0; sikilastirma_mantik_testi 0 (22 vaka).
- D: uretim78_mantik_testi 70 vaka 0 (URETIM78_MANTIK_TESTI.json; her grup bilinen PASS + bilinen FAIL). Yerel düzeltme turları: 2
  (1: test fontu; 2: çöküş çiftinde `eksik` işaretlenmiyordu, gerçek hata) + F düzeltmeleri.
- Yerel uçtan uca (PARCA modu, CL gerçek + sahte Kova, Drive yerine yerel klasör): ornek78 0; CL kontrol 5 stil 0/0; birleştir 0
  (Drive 15 = 15 dosya, sha eşit); gerçek boy 0; ETA 2 satır; katman.pkl silindi. UCTAN_UCA_YEREL.json, ETA_YEREL.log.
- Kova tek neden kodu (ornek78.py 9f88868:147-167 ve :189-196) DEĞİŞMEDİ: metin birebir (test betiği).

## Yeni / değişen dosyalar
- YENİ .github/workflows/ornament-78-uretim.yml (tetik docs/ornament/URETIM78_TETIK.txt; bu görevde OLUŞTURULMADI).
- YENİ docs/ornament/URETIM78_CIFTLER.json (aktif "ornek"; örnek 2 × 4; 78 = 75 çift / 6 parça, Kova 2-2-2-2-2-1).
- YENİ scripts/printful/uretim78.py, uretim78_beklenen.py (BEKLENEN_SONUC_ORNEK.json), uretim78_mantik_testi.py.
- DEĞİŞEN scripts/printful/ornek78.py: PARCA modu (ilk çift CL değilse 4), çift gövdesi try/except (çöküş çift FAIL, CL çöküşü DUR 3),
  çift sonu kancası (Drive tek yükleme, ETA, temizlik), dpi 300 yazımı (5 stil, piksel aynı), printful_dosya sert kapısı, piksel sha,
  onarımsız ek FAIL listesi, dusuk_kontrast `kontrol_cifti`.

## Sipariş iş akışı listesi (main .github/workflows, "siparis|order"; 14)
by-siparis-ornek, etsy-siparis-ozet, kupa-siparis, olcek-tani-siparis, pod-order-router, siparis-baski-kontrol, siparis-dijital, siparis-giris,
siparis-kesit-birlesik, siparis-kesit-son, siparis-kisisel-oku, siparis-onay-yaz, siparis-pdf-test, siparis-test-topla (.yml).

## Örnek koşusu çiftleri (yerlesim78.json'da var; URETIM78_CIFTLER.json "ornek")
Parça 1: CL kontrol + TAURUS_TAURUS, CANCER_TAURUS, AQUARIUS_CANCER, LIBRA_LIBRA. Parça 2: CL kontrol + AQUARIUS_AQUARIUS, ARIES_SCORPIO,
LEO_SAGITTARIUS, CAPRICORN_CAPRICORN.

## Sapma ve notlar
- "İlk çift CL değilse 4" yalnız PARCA modunda (ORNEK78_PARCA dolu); eski ornament-78-ornek.yml (dokunulmadı) GV sınır-1 adımı bozulmasın diye.
- Drive kıyası sha256 ile (görevde "md5"; Drive lsjson sha256 verir; sha yoksa FAIL).
- Zayıf testler: o2_piksel (aynı dosya), kenar_dogrula (aynı kaynak), n0 = 0 kenar satırları.
- Görev dışı (inceleme 7): dalda 164 izlenen PNG var (public kural); düzeltilmedi.
