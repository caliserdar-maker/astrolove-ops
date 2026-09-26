# Codex IS 0010 - tamset_qc OCR yanlis alarm regresyon testleri (yeni test dosyasi)
AGENTS.md kurallari. scripts/etsy/tamset_qc.py'yi DEGISTIRME (pod'un). Yeni: scripts/etsy/test_tamset_ocr.py.
Bilinen yanlis alarmlar: "PRINT" -> "PR — NT" (tire sayilmamali), "ITH" (With kirpigi), "STROLOVE" (ASTROLOVE kirpigi), "Warm Parchment" okunamamasi (3 okumada tutarsizsa FAIL degil). Gercek hatalar yakalanmali: yanlis burc (SCORPIO yerine LIBRA), "FULFILMENT", eski slogan "TWO SOULS" / "ONE BOND", eksik satir.
tamset_qc'nin karar fonksiyonlarini import edip sentetik OCR ciktilariyla test et; fonksiyonlar import edilemiyorsa hangi refaktorun gerektigini rapora yaz.
