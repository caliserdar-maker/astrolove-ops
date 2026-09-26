# Codex IS 0011 - order_router GONDERME/ISIM_BEKLIYOR durumlari icin musteri mesaj TASLAGI uretimi
AGENTS.md kurallari. Etsy'ye, Prodigi'ye, e-postaya GONDERME YOK. Yalniz taslak dosyasi uretilir.
Kaynak: scripts/prodigi/order_router.py (STAGES, _neden, ISIM_BEKLIYOR, atlandi, error), docs/MUSTERI_MESAJ_SABLONLARI.md (6 sablon + tablo).
Yeni: scripts/prodigi/mesaj_taslak.py
- Girdi: order_router STATE JSON yolu (--state). Cikti: --cikti dizinine receipt basina <receipt>.txt taslak + OZET.csv (receipt, stage, neden, sablon_no).
- Eslesme: stage/neden -> sablon (MUSTERI_MESAJ_SABLONLARI.md tablosu). Eslesmeyen = "SABLON_YOK" satiri, taslak yazilmaz.
- Yer tutucular: {isim}, {tarih} vb. STATE'te yoksa taslakta acikca "[DOLDUR: alan]" kalir; uydurma deger yok.
- Musteri adi/adres loga veya stdout'a YAZILMAZ; yalniz dosyaya. Test verisi tamamen sentetik.
- Uzun/orta tire kontrolu: taslakta varsa FAIL.
Test: scripts/prodigi/test_mesaj_taslak.py (en az 6 senaryo: her sablon + SABLON_YOK + eksik alan).
Teslim: yanit yorumunun sonuna TAM unified diff (tek ```diff blogu). pano/codex/RAPOR_0011.md 5 satir.
