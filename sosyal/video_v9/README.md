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

## Toplu uretim (Actions: `video-v9.yml`)
- `mod=ornek`: Drive `AstroLoveArt_Gemini_Leo_2000.jpg` ile 6 kare + `dogrula.py` (her kare < 2.5). PASS ise CAPRICORN_SAGITTARIUS
  sessiz + 3 muzikli hal -> Drive `TEMP/VIDEO_V9_20261012/ORNEK/`.
- `mod=hepsi`: `_POSTER2000` (pin-uretim'in 78 posteri) -> matrix (is basina `grup` cift) `video_toplu.py` -> `SESSIZ/`;
  `kontak.py` QC.csv / QC.json / FAIL.txt / KONTAK_9s.jpg.
  QC: q_poster (PosterR hatasiz), q_video (1080x1920, 30/1 fps, 720 kare, 24.0 sn, h264), q_son (22 sn karesinde
  "Make it yours" bandinda >= %0.5 parlak piksel; onayli karede %7.1, bos bantta %0).
- `mod=muzik muzik=N`: SESSIZ/ + muzik N (kopya, yeniden kodlama yok) -> `FINAL/`.
- `mod=ornek_muzik muzik=N`: ORNEK/ sessiz ornege muzik N -> `ORNEK/..._muzikN.mp4`. `muzik_ekle.py` QC: ses ve video 24.0 sn, 720 kare, -16 LUFS +-1.
- `mod=hepsi` 78/78 PASS ise ayni kosuda muzik N (varsayilan 2, kesin secim) eklenir -> `FINAL/`.
- Parola: Drive `ASTROLOVE/TEMP/MUZIK_PAROLA.txt` (rclone cat, hemen `::add-mask::`, openssl'e env ile). Dosyaya/loga yazilmaz.

## Basa kapak (15 Eki 2026, Serdar onayi, 2. yontem)
`kapak_basa.py`: FINAL videonun siyah acilisinin USTUNE kapak_v1: 0-0.5 sn tam kapak, 0.5-1.0 sn kapaktan orijinale
kosinus capraz gecis (orijinalin siyahtan acilisiyla ortusur, siyah kare yok). Sure (24.0 sn), kare (720) ve ses (kopya) ayni.
Neden: Facebook oynaticisi ilk kareyle aciliyor, v9 ilk karesi siyah. (1. yontem, basa 0.5 sn ekleme, "kapak, siyah, acilis"
verdigi icin birakildi.) QC: ilk kare = kapak (fark < 2.0), 0-1.5 sn her kare parlaklik >= kapak/2, kayma < 2.0,
kare/sure/ses ayni, <= 60 sn. Actions: `video-kapak-basa.yml` (`mod=ornek` -> `KAPAKLI_ORNEK2/`, `mod=hepsi` -> 6 paralel is -> `FINAL_KAPAKLI/` + `KAPAKLI_QC.csv` + `KONTAK_0sn.jpg`;
FINAL/ degismez).
