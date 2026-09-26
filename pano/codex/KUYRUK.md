# Codex is kuyrugu (Claude yonetir)

Kural (Serdar, 26 Eyl): Codex hicbir an bos kalmaz. Hedef: ayni anda 3-4 is. Claude her 15 dk kontrolde biten isi inceler (diff uygula, test, merge karari) ve kuyruktan yenisini baslatir.
Teslim bicimi: PR yorumunun sonunda TAM unified diff (Codex dala push edemiyor). Merge yalniz Claude kontrolunden sonra.

## Calisan
- IS_0003 PR #15 POD sablon kodu hizalama
- PR #16 dijital-v1 inceleme (GOREV_0014)
- IS_0004 PR #17 ortak video icerik dogrulayici
- IS_0005 PR #18 plate onay defteri araci
- IS_0006 PR #19 musteri mesaj sablonlari

## Siradaki
1. IS_0007 Rusca aciklama: onayli Ingilizce aciklamanin dogrudan cevirisi sablonu + EN/RU yapi eslesme testi (etiketler Ingilizce kalir).
2. IS_0008 video_dogrula entegrasyonu: pod_galeri_tamset (yukleme sonrasi) ve canli_qc K5'e bagla (IS_0004 merge sonrasi).
3. IS_0009 alt metin ureticisi denetimi: 250 karakter, tire yok, burc adlari dogru, Etsy sondaki bosluk kirpmasi.
4. IS_0010 tamset_qc OCR yanlis alarm kurallari icin regresyon testleri (PR, ITH, STROLOVE, WARM PARCHMENT ornekleri).
5. IS_0011 order_router GONDERME -> IS_0006 sablonuyla musteri mesaj TASLAGI uretimi (gonderme yok, taslak dosya).
6. IS_0012 kisisel siparis uretim hattinda olcek/leke kapilari neden TEST_A'da FAIL (siparis-baski-v1 dali, PR uzerinden).
