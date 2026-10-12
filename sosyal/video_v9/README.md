# Reel videosu paketi v9 (Serdar onayli tasarim, 12 Eki 2026)

24 sn, 1080x1920 (9:16), 30 fps, H.264 High CRF 16. Ayni video: Instagram Reels, Facebook Reels, TikTok, YouTube Shorts.
Onayli referans kareler (Gemini & Leo): `onayli/kare_{2,5,8,13,17,22}s.jpg` (onayli videodan alinmis).
`video_uret.py --kareler 2,5,8,13,17,22` ile ayni kareler uretilip karsilastirilir: ortalama fark < 2.5 olmali
(5 sn karesinde toz taneleri rastgele dagildigi icin fark ~2.3 normaldir; gorunus ayni).
lib.py, layouts.py, fontlar ve PosterR `../pin_v6/`, soru isareti `../ig_v6/assets/` klasorunden gelir.

## Calistirma
```
pip install numpy opencv-python-headless pillow scipy   # ffmpeg gerekli
python3 sosyal/video_v9/video_uret.py --poster <2000x3000 poster> --a Gemini --b Leo --out cikti/ [--muzik muzik.m4a]
```
- `--a` = cift anahtarinda ILK burc (posterde SOL), `--b` = ikinci (SAG). Cift anahtari alfabetik.
- Bir video yerelde ~5-10 dk surer (720 kare, 60.000 toz tanesi). 78 video icin Actions'ta paralel isler (matrix) kullanilir.
- `--muzik` verilmezse video sessiz yazilir; muzik sonra saniyeler icinde eklenir (yeniden kodlama yok):
  `ffmpeg -i video.mp4 -i muzik.m4a -map 0:v -map 1:a -c copy -t 24 -movflags +faststart cikti.mp4`

## Muzik
`assets/muzik_{1,2,3}.m4a.enc`: Lena'nin sectigi adaylar (1 = ADAY_07, 2 = ADAY_09, 3 = ADAY_15 B). Hepsi 24 sn,
sesi yavas acilip yavas kapanan, -16 LUFS final ses. Pixabay lisansi muzigin tek basina dagitilmasina izin vermedigi icin
sifreli tutulur. Parola gorev metninde verilir, depoya/loga YAZILMAZ:
`openssl enc -d -aes-256-cbc -pbkdf2 -in assets/muzik_N.m4a.enc -out muzik.m4a -pass pass:<PAROLA>`
Cozulen .m4a dosyasi depoya commit edilmez.

## Kurallar
- Poster pikselleri yalniz kesilir, olceklenir, tasinir. Yapay zeka ile degistirilmez.
- Gorsel yazilarinda cumle sonu nokta yok, "and" yerine "&".
