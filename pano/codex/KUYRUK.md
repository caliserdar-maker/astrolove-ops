# Codex is kuyrugu (Claude yonetir)

Kural (Serdar, 26 Eyl): Codex hicbir an bos kalmaz. Hedef: ayni anda 3-4 is. Claude her 15 dk kontrolde biten isi inceler (diff uygula, test, merge karari) ve kuyruktan yenisini baslatir.
Teslim bicimi: PR yorumunun sonunda TAM unified diff (Codex dala push edemiyor). Merge yalniz Claude kontrolunden sonra.

## Calisan (11:30)
- IS_0007 PR #20 RU aciklama cevirisi
- IS_0008 PR #21 canli_qc K5 video_dogrula entegrasyonu
- IS_0009 PR #22 alt metin kontrolu
- IS_0010 PR #23 tamset_qc OCR regresyon testleri

## Biten (main'e alindi)
- IS_0002 metin tire/Hahnemuhle, IS_0003 POD sablon, IS_0004 video_dogrula (Claude son-kare duzeltmesi), IS_0005 plate onay CLI, IS_0006 musteri mesaj sablonlari
- IS_0001 PR #13 siparis fail-closed: pod dogrulamasi bekleniyor (Draft alani + bekletme stage)

## Siradaki
1. IS_0011 order_router GONDERME -> musteri mesaj TASLAGI uretimi (docs/MUSTERI_MESAJ_SABLONLARI.md), gonderme yok.
2. IS_0012 kisisel siparis uretim hattinda olcek/leke kapilari neden TEST_A'da FAIL (siparis-baski-v1, PR uzerinden inceleme).
3. IS_0013 medya pod_galeri_tamset'in kendi 3-kare video kontrolunu video_dogrula'ya tasima onerisi (diff; medya uygular).
4. IS_0014 durum ozeti araci: GALERI_TAMSET.json + TAMSET_QC.csv + VIDEO_QC.csv semalarini repodaki kodlardan cikar, 78 cift x asama tablosu ureten scripts/ops/durum_ozet.py.
