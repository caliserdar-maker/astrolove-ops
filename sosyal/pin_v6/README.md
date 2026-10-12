# Pinterest pin paketi v6 (Serdar onayli tasarim, 12 Eki 2026)

Uc pin, 1000x1500 (2:3), her cift icin:
- **p1**: duvar sahnesi + gercek poster + lacivert yazi -> pano "Zodiac Couple Wall Art"
- **p2**: iki burc yorungede + birlesik sembol -> pano "Zodiac Compatibility Art" (YENI pano)
- **p3**: buyuk birlesik sembol + posterdeki isimler -> pano "Personalized Couple Gifts"

Onayli ornekler (Gemini & Leo): `onayli/`. `pin_uret.py` bunlari ortalama 1 seviye fark ile (JPEG) birebir uretir.

## Calistirma
```
pip install numpy opencv-python-headless pillow scipy
python3 sosyal/pin_v6/pin_uret.py --poster <cift posteri 2000x3000 jpg> --a Gemini --b Leo --out cikti/
```
- `--a` = cift anahtarinda ILK burc (posterde SOLDAKI kucuk burc), `--b` = ikinci (SAG). Cift anahtari alfabetik (CLAUDE.md).
- Poster: yeni 78 poster (9 Eki surumu), Midnight Blue, ORNEK isimlerle (Serdar & Lena isimleri YOK), 2000x3000.
- Her cift icin `{a}-and-{b}-parcalar.jpg` QC sayfasi da yazilir: posterden kesilen 5 parca (birlesik, sol burc, sag burc, isimler, mesaj).

## Kurallar
- Poster pikselleri yalniz kesilir, olceklenir, tasinir. Yapay zeka ile degistirilmez. Sembol sekli degismez.
- Gorsel yazilarinda cumle sonu nokta yok, "and" yerine "&".
- Metinler: `PIN_METIN_234.csv` (78 cift x 3 pin; baslik <=100, aciklama <=500, alt metin <=500, hashtag yok, uzun tire yok). `etsy_link` sutunu bos: her cift kendi kisisel ilanina (salt okuma ile eslestir).
