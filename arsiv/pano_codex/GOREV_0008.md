# Codex GOREV 0008 (Claude, 26 Eyl 2026) - dijital kisisel wallpaper kodu incelemesi

AGENTS.md kurallari. KOD DEGISTIRME, yalniz rapor. ONEM: yuksek/orta/dusuk yaz.

Kaynak: pano/codex/kaynak/dijital-v1_29a3e3c/ (dijital-v1 dali 29a3e3c'nin salt okunur kopyasi; orijinal dala erisimin yok).
Is: kisisel POD siparisinde musteriye dijital wallpaper da uretiliyor (4 renk: Midnight Blue, Deep Black, Champagne Ivory, Warm Parchment; 3 cihaz). Baski dosyasi 7200x9600 -> 24x32 plate -> wallpaper.

Bilinen son hatalar (oturum duzeltti): cift adi alt dizge eslesmesi (CANCER_LIBRA vs CANCER_LIBRA_UZUN), BLUE/BLACK'te mesaj puntosunun farkli olculmesi (172 vs 337), kapilar() klasor olusturmuyordu, WARM_PARCHMENT ZIP'i bos cikti, dijital uretim 26 dk surdu (hedef 10 dk).

Kontrol et:
1. Duzeltmeler dogru mu, ayni sinifta baska hata kaldi mi (dosya eslestirme, edisyonlar arasi geometri tutarliligi)?
2. Bos ZIP / eksik renk durumunda kod DURUYOR mu yoksa bos teslimat mi uretiyor?
3. Musteri adi/mesaji: uzun isim, 35 karakter mesaj, aksanli harf tasmasi, font kapsami.
4. 26 dk'nin olasi darbogazlari (LANCZOS buyutme, tekrarli olcum, seri I/O); somut hizlandirma onerisi.
5. Testleri kostur (test_siparis_birim.py vb.), sonucu yaz.

RAPOR: pano/codex/RAPOR_0008.md, PR ile. En fazla 2 iterasyon.
