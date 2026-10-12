# data/sosyal/metin: 78 cift gonderi metinleri (TASLAK)

ChatGPT arastirmasiyla karsilastirildiktan sonra kesinlesecek. Yayin yok.

| Dosya | Sutunlar |
|---|---|
| IG_KARUSEL_78.csv | cift_anahtari, burc_sol, burc_sag, caption, referans_hashtag, alt_metin_1..4 |
| IG_REEL_78.csv | cift_anahtari, caption, referans_hashtag |
| TIKTOK_78.csv | cift_anahtari, caption (tek paragraf, B sablonu: profilde tiklanabilir link yok), referans_hashtag, kapak_yazisi |
| FACEBOOK_78.csv | cift_anahtari, gonderi_metni (3 gorsel: slayt 2, 3, 4), reel_caption, referans_hashtag, alt_metin_2..4 |

- Hashtag'ler yalniz caption / gonderi_metni / reel_caption icinde (metnin sonunda).
- **referans_hashtag sutunu Metricool'a gonderilmez.** Yalniz denetim ve okuma icin; caption'a ayrica eklenirse hashtag'ler iki kez yazilir.
- Sablonlar: `data/sosyal/arastirma/raporlar/INSTAGRAM_CLAUDE.md`, `TIKTOK_CLAUDE.md`, `FACEBOOK_CLAUDE.md` (AYNEN). Cift adi alfabetik (Gemini & Leo, Pisces & Scorpio).
- Alt metinler: ornek isim yazilmaz ("the couple's two names"); gorsel tarifi `sosyal/ig_v6/onayli/` ve `sosyal/pin_v6/onayli/` dosyalarina gore.
- Uret ve denetle: `python3 data/sosyal/metin/metin_78_uret.py` (PASS/FAIL; 78 satir, uzun/orta tire ve "+" yok, yasak ifade ve ornek isim yok, hashtag <= 5, caption <= 2200, iki burc dogru ve alfabetik).
