# V11 ENVANTER (19 Eyl 2026)

## 1. Eksik cift

YOK. Olculen: `TEMP/WA_HERO_ZOOM_V4/MIDNIGHT_BLUE` **78** ZOOM60 mockup,
`01_EXPORTS/MIDNIGHT_BLUE` **78** video (`WA_VIDEO_V01_<CIFT>_MIDNIGHT_BLUE.mp4`),
eksik cift listesi bos.

Not: onceki oturumdaki "77 video" bulgusu hatali sayimdan geliyordu (dokum
dosyasinin son satirinda satir sonu yoktu, `wc -l` bir eksik saydi). Bu kosuda
iki liste dogrudan karsilastirildi.

## 2. 78 mockup'ta poster kutusu

Her ZOOM60 mockup'ta poster kutusu uretim betiginin kendi olcumuyle
(`WA_VIDEO_V01_BATCH_V5.kutu_olc`, poster ile korelasyon) hesaplandi;
dosyalar tek tek inip olculdukten sonra silindi (`KUTULAR.csv`).

- **78/78 ciftte kutu ayni**: `x0=994, y0=264, x1=2006, y1=1614`
  (1012 x 1350 px, 3000x2250 mockup icinde).
- Korelasyon skoru: **min 0.9922 / maks 0.9956**, hepsi >= 0.95.
- Olculemeyen veya farkli kutuya sahip cift: **yok**.

Sonuc: sahne ve poster yerlesimi 78 ciftte birebir ayni; V11 kompoziti tum
ciftlerde ayni donusumle calisabilir.

## 3. V11 donusumu

Panel ici, ciftin V01 MB videosundan REFERANSIN donusumuyle alinir:
`olcek 1.1607, tx -106.1, ty -4.4, donme 0` (ORB+RANSAC ile bulundu, kodlanmis
Y duzleminde ince ayar: panel ici MAE 2.93 -> 2.28). Ciftin kendi ty'si
kullanilmaz. Panel kutusu (canli referans, 1024x1280): ust 176, sol 158,
alt 1123, sag 887; ic kenarda 2 px yumusak gecis.
