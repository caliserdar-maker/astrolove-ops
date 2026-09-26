# Codex IS 0014 - 78 cift durum ozeti araci
AGENTS.md kurallari. Ag cagrisi YOK; girdiler yerel dosya.
Kaynak semalar: scripts/etsy/pod_galeri_tamset.py (GALERI_TAMSET state JSON), scripts/etsy/tamset_qc.py (TAMSET_QC.csv), video QC CSV semasi (kolonlar: cift, sonuc, teknik, ocr, renk, cift_dogru, leke, siyah_donma - dosya yoksa atla).
Yeni: scripts/ops/durum_ozet.py
- Girdiler opsiyonel: --galeri, --tamset-qc, --video-qc, --liste (78 cift listesi CSV; yoksa 12x12 burc ciftlerinden kanonik 78 uret, ayni burc dahil).
- Cikti: DURUM_78.csv (cift, tamset_var, galeri_sonuc, video_sonuc, varyasyon_ok, son_guncelleme) + terminale 6 satirlik ozet (sayilar).
- Eksik veri "?" olarak yazilir, uydurma yok.
Test: scripts/ops/test_durum_ozet.py sentetik girdilerle (en az 4 senaryo).
Teslim: yanit yorumunun sonuna TAM unified diff (tek ```diff blogu). pano/codex/RAPOR_0014.md 5 satir.
