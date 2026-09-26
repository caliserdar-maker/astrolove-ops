# Codex is kuyrugu (Claude yonetir)

Kural (Serdar, 26 Eyl): Codex hicbir an bos kalmaz. Hedef: ayni anda 3-4 is. Claude her 15 dk kontrolde biten isi inceler (diff uygula, test, merge karari) ve kuyruktan yenisini baslatir.
Teslim bicimi: PR yorumunun sonunda TAM unified diff (Codex dala push edemiyor). Merge yalniz Claude kontrolunden sonra.

## Calisan (11:40)
- IS_0008 PR #21 canli_qc K5 video_dogrula entegrasyonu
- IS_0011 PR #24 GONDERME -> musteri mesaj taslagi
- IS_0013 PR #25 renk varyasyonu gorsel denetcisi (cevrimdisi)
- IS_0014 PR #26 78 cift durum ozeti

## Biten (main'e alindi)
- IS_0002 metin tire/Hahnemuhle, IS_0003 POD sablon, IS_0004 video_dogrula (Claude son-kare duzeltmesi), IS_0005 plate onay CLI, IS_0006 musteri mesaj sablonlari
- IS_0007 RU aciklama, IS_0009 alt metin denetcisi, IS_0010 tamset OCR testleri (db2a491)
- IS_0001 PR #13 siparis fail-closed: pod dogrulamasi bekleniyor (Draft alani + bekletme stage)

## Siradaki
1. IS_0012 kisisel siparis uretim hattinda olcek/leke kapilari neden TEST_A'da FAIL (siparis-baski-v1, PR uzerinden inceleme).
2. IS_0015 medya pod_galeri_tamset'in kendi 3-kare video kontrolunu video_dogrula'ya tasima onerisi (diff; medya uygular).
3. IS_0016 alt_metin_kontrol'u pod_galeri_tamset'e baglama diff'i (RAPOR_0009 onerisi; medya uygular).
