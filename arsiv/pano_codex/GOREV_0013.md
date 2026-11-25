# Codex GOREV 0013 (Claude, 26 Eyl 2026 10:55 UTC) - 78 kisisel POD ilaninin metin/fiyat/alan SABLONU onayli kararlara uyuyor mu

AGENTS.md kurallari. KOD DEGISTIRME; rapor + gerekirse onerilen tam diff (yanit sonunda tek ```diff blogu). ONEM yaz.
Repo icinde 78 kisisel POD ilanina giden baslik/aciklama/kisisellestirme/fiyat/boy ureten kodu bul (ornek: scripts/pod/, scripts/etsy/pod_*.py, fiyat_b.py) ve Serdar'in ONAYLI kararlariyla birebir karsilastir:
1. Baslik: "{A} and {B} Zodiac Wall Art, Personalized Couple Print with Names and Message, Unframed".
2. Kisisellestirme: 3 zorunlu alan. "Name under {A}" / "Name under {B}" ("Up to 11 letters. Printed in capitals."), "Your message" ("Up to 35 characters, including spaces. Printed as you type it."). Ayni burc: "Left name" / "Right name". Burc sirasi secimi YOK.
3. 16 boy ve fiyat (USD): 8x10 34.99, A4 37.99, 11x14 42.99, 12x16 46.99, A3 47.99, 12x18 49.99, 16x20 54.99, 16x24 57.99, A2 57.99, 18x24 64.99, 20x30 84.99, 24x30 94.99, 24x32 99.99, A1 99.99, 24x36 109.99, 30x40 139.99. 5x7 YOK.
4. Rusca aciklama Ingilizcenin dogrudan cevirisi; etiketler Ingilizce.
5. Urun metni kurali (CLAUDE.md): izinli/yasak ifadeler, uzun/orta tire yok.
Her sapma: dosya:satir, beklenen, bulunan.
RAPOR: pano/codex/RAPOR_0013.md, PR ile. Yanit yorumunda YUKSEK/ORTA bulgulari dosya:satir ile listele.
