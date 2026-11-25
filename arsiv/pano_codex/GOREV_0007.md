# Codex GOREV 0007 (Claude, 26 Eyl 2026) - POD siparis yolu incelemesi (CANLI, her ~15 dk kosuyor)

AGENTS.md kurallari. KOD DEGISTIRME, yalniz rapor. Etsy/Prodigi/Drive yok. ONEM: yuksek/orta/dusuk yaz.

Dosyalar (main): scripts/prodigi/order_router.py, kisisel_siparis.py, takip.py, pilot_skus.csv, hpr_sizes.txt, test_*.py

Onayli kurallar (Serdar):
- 78 POD ilani kisisel: 3 zorunlu alan. "Name under {A}" / "Name under {B}" (en fazla 11 harf, BUYUK harfle basilir), "Your message" (en fazla 35 karakter, bosluk dahil, yazildigi gibi). Ayni burc ciftinde "Left name" / "Right name". Burc sirasi secimi YOK.
- 16 boy: 8x10, A4, 11x14, 12x16, A3, 12x18, 16x20, 16x24, A2, 18x24, 20x30, 24x30, 24x32, A1, 24x36, 30x40. Kagit Hahnemuhle Photo Rag.
- Prodigi siparisleri "Pause indefinitely" ile kalir, elle serbest birakilir.
- Edisyonlar: Midnight Blue, Deep Black, Pure White, Champagne Ivory, Warm Parchment. Baski kalibi (plate) su an yeniden yapiliyor; kalibi onaysiz edisyon siparise GITMEMELI (yanlis baski yerine durup haber vermeli).

Kontrol et:
1. Her boy -> dogru Prodigi SKU ve dogru piksel/dpi mi? Eksik/yanlis eslesme.
2. Kisisellestirme ayristirma: 11 harf, 35 karakter, buyuk harf, Turkce/aksanli harf (I/i, Ü, é), emoji, bos alan, fazla uzun giris, ayni burc Left/Right. Sinirda neler olur?
3. Onaysiz edisyon veya kalibi olmayan boy gelirse ne olur? Sessizce yanlis dosya uretir mi?
4. Pause davranisi: kod siparisi otomatik serbest birakabilir mi?
5. Loglara musteri adi/adres/mesaj yaziliyor mu (repo public, Actions logu gorunur)?
6. Ayni siparis iki kez islenir mi (idempotency)?
7. Testleri kostur, sonucu yaz.

RAPOR: pano/codex/RAPOR_0007.md, PR ile. En fazla 2 iterasyon.
