# Codex IS 0002 (Claude, 26 Eyl 2026) - urun metni ureten koddaki yasak tire ve Hahnemuhle yazimi (kod yaz)

AGENTS.md kurallari. KOD YAZMA isi. Etsy/Drive yok.
Kaynak: senin RAPOR_0006 bulgun.
Dosyalar: scripts/etsy/pod_listing_create.py (88,104,132 tire; 115 Hahnemuhle), scripts/pod/factcheck.py (39-64), scripts/etsy/xsell_links.py (48,63), scripts/pinterest/build_week_v2.py (56-57), scripts/etsy/desc/AQUARIUS_AQUARIUS_4570110121.txt (9).
Yap:
1. Musteriye giden Ingilizce metinlerde uzun ve orta tire karakterlerini dogal noktalama ile degistir (virgul, nokta, iki nokta, parantez); anlam degismesin. Kod yorumu/log satirlarina dokunma.
2. "Hahnemuhle" -> "Hahnemühle" (musteriye giden metinlerde).
3. factcheck.py tire karakterlerini YASAK LISTESI olarak tutuyorsa (kontrol amacli) DOKUNMA, raporla.
4. Basit tarama testi ekle (scripts/etsy/test_metin_tire.py): hedef dosyalarin musteri metninde uzun/orta tire yok; kostur.
TESLIM: Yanit yorumunun SONUNA tam unified diff'i tek ```diff blogu olarak ekle. Kisaltma yok.
