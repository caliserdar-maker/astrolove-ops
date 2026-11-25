# Codex IS 0005 - plate onay defteri araci (kod yaz, yeni dosya)
AGENTS.md kurallari. Etsy/Prodigi/Drive yok. PR #13 (codex-is/siparis-failclosed) config/plate_onay.json'u getiriyor ({"onayli": []}); main'de yoksa ayni semayla olustur.
Yeni: scripts/prodigi/plate_onay.py (CLI) + test.
- ekle --edisyon BLUE --boylar 8x10,A4,... --kanit "<onay sayfasi Drive id>" --onaylayan Serdar : kayit {edisyon, boy, kanit, onaylayan, tarih_utc}
- listele, kaldir, dogrula (16 onayli boy disinda boy, bilinmeyen edisyon -> hata; edisyonlar: MIDNIGHT_BLUE, DEEP_BLACK, PURE_WHITE, CHAMPAGNE_IVORY, WARM_PARCHMENT - repodaki mevcut adlandirmayi bul ve ona uy).
- Ayni kayit iki kez eklenmez; dosya atomik yazilir.
- order_router.plate_onayli_mi ile uyumlu sema (dict kayitlarda edisyon+boy).
