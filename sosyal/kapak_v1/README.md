# Video kapagi v1 (Serdar onayli tasarim, 13 Eki 2026)

Reel / Facebook Reel / TikTok / YouTube Shorts kapagi, 1080x1920 (9:16), her cift icin bir tane.
- Buyuk birlesik sembol (posterden), altinda: sol burc sembolu + adi, ortada AstroLoveArt sonsuzluk logosu, sag burc sembolu + adi.
- Baska yazi yok. Her sey Instagram profil izgarasinin gosterdigi ortadaki 3:4 alanda (y 240..1680).
- Onayli ornek: `onayli/kapak_gemini_leo.jpg`; izgara gorunumu: `onayli/profil_izgara_temsili.jpg`.
- Logo: `assets/logo_sonsuz.png`, onayli Gemini & Leo posterinin isim satirindan bir kez kesildi; 78 kapakta ayni.

## Calistirma
```
python3 sosyal/kapak_v1/kapak_uret.py --poster <cift posteri 2000x3000 jpg> --a Gemini --b Leo --out cikti/
```
- `--a` ilk burc (posterde SOL), `--b` ikinci (SAG); cift anahtari alfabetik. Poster: video ve IG uretiminde kullanilan ayni kaynak.
- QC (cikis kodu 0 = PASS): boyut 1080x1920, tum ogeler izgara alaninda (30 px pay), ogeler arasi bosluk >= 24 px.
- GEMINI_LEO onayli ornekle ortalama fark 0.48 (yerel test, 13 Eki).
