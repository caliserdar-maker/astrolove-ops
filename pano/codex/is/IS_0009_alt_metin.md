# Codex IS 0009 - galeri alt metin ureticisi (kod yaz/duzelt)
AGENTS.md kurallari. Etsy yok. Alt metni ureten fonksiyonlari bul (ornek pod_galeri_tamset.alt_uyarla, pod_media vb.) ama pod_galeri_tamset.py'yi DEGISTIRME; bulgulari ve onerilen yamayi rapora yaz. Ayrica bagimsiz scripts/etsy/alt_metin_kontrol.py yaz:
- 250 karakter, sondaki bosluk kirpilmis, uzun/orta tire yok, burc adlari cifte uygun (ayni burc ciftinde tekrar), "Hahnemühle" yazimi, yasak ifadeler (CLAUDE.md urun metni).
- Girdi: SET.json benzeri {sira: alt} sozlugu; cikti PASS/FAIL listesi. Test dosyasi ile.
