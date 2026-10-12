# Instagram / Facebook / Threads karusel paketi v6 (Serdar onayli tasarim, 12 Eki 2026)

4 slayt, 1080x1350 (4:5), her cift icin: 1 kapak (soru), 2 cevap (birlesik sembol + isimler), 3 duvar sahnesi, 4 yakin plan + "Make it yours / ASTROLOVEART / On Etsy".
Onayli ornekler (Gemini & Leo): `onayli/`. `ig_uret.py` bunlari ortalama 1 seviye fark ile (JPEG) birebir uretir.
lib.py, layouts.py, fontlar ve PosterR `../pin_v6/` klasorunden gelir (iki paket ayni kodu kullanir).

## Calistirma
```
pip install numpy opencv-python-headless pillow scipy
python3 sosyal/ig_v6/ig_uret.py --poster <cift posteri 2000x3000 jpg> --a Gemini --b Leo --out cikti/
```
- `--a` = cift anahtarinda ILK burc (posterde SOL), `--b` = ikinci (SAG). Cift anahtari alfabetik.
- Poster: pin paketiyle ayni 78 poster (9 Eki surumu, Midnight Blue, ORNEK isimli, 2000x3000).
- Uzun burc adi (SAGITTARIUS) yorungede once disa kayar, sigmazsa iki etiket birlikte kuculur; ortadaki sembole ve kenara degmez.

## Kurallar
- Poster pikselleri yalniz kesilir, olceklenir, tasinir. Yapay zeka ile degistirilmez.
- Gorsel yazilarinda cumle sonu nokta yok, "and" yerine "&".
