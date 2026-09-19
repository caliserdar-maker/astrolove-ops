# V01 KESIF (19 Eyl 2026) — WA_VIDEO_V01_BATCH_V5.py

Tum sayilar GERCEK dosyalardan olculdu (Drive + Etsy GET). Etsy'ye yazma yok.

## 1. Betik akisi (10 satir)

1. Girdi: `TEMP/WA_HERO_ZOOM_V4/<EDITION>/WA_06_MOCKUP_<PAIR>_<EDITION>_ZOOM60.png`
   (3000x2250) ve `POSTERS/OPTIMIZED_FOR_PRODUCTION/<ED>/3X4/<PAIR>.jpg`.
2. `kutu_olc`: mockup grisi ile posterin satir/sutun profili korele edilerek
   (kaba 5x + ince 10 px arama) poster kutusu bulunur; skor < 0.95 ise HATA.
3. Mockup merkezden 4:5 kirpilir (3000x2250 -> 1800x2250; KX = (3000 - 2250*0.8)/2 = 600), poster kutusu
   kirpima tasinir; poster alani `poster` olarak ayrilir.
4. Murekkep alani: gri - medyan(151) fark goruntusu `d`; esik Otsu'dan
   (12..60 arasi kirpilir). `M0 = d > TH` ana maske.
5. Fusion kutusu (`FR_FUS`) icindeki bilesenlerden daire (`doluluk<0.030`) ve
   gercek cizgi ayrilir; cizgi iki glife (sol/sag) bolunur -> `F_CAN`, `F_LIB`.
6. Kucuk glifler: `B_CAN`/`B_LIB` kutularindan turetilen YATAY SERIT (+-28 px)
   icindeki bilesenler; seridi KESEN bilesen alinmaz; merkez x'e gore sol/sag.
   Parcaciklarin DOGDUGU maske budur (`M_CAN`, `M_LIB`).
7. 88000 parcacik glif pikselleri arasindan seed 20260816 ile secilir; her
   parcacigin hedefi fusion cizgisinin ayni acisal siradaki pikselidir
   (acisal eslesme). Renk parcacigin DOGDUGU posterin kendi pikselinden gelir.
8. Kucuk glifler posterden silinir (`inpaint`, silme kutusu = maskenin gercek
   siniri + 6 px; kutu fusion ile kesisirse HATA) -> `TABLO_BOS`.
9. 0-152 kare uretilir, 15-152 yazilir (138 kare, 4.6 sn, 30 fps, 1080x1350);
   kare = TABLO_BOS -> TABLO gecisi + parcacik izleri (cekirdek/halo/kuyruk,
   `screen` benzeri alfa) + 112-146 arasi yerlesme; ROI disi hic degismez.
10. Kodlama: libx264 CRF 12 preset slow yuv420p BT.709 -an +faststart; ardindan
    11 olcumlu oz-dogrulama (toz tonu, kalinti, dongu farki, sure, boyut).

## 2. Envanter (rclone lsf, gercek)

- `TEMP/WA_HERO_ZOOM_V4/MIDNIGHT_BLUE`: **78** adet `*_ZOOM60.png`.
- `01_EXPORTS/MIDNIGHT_BLUE`: **77** adet `WA_VIDEO_V01_*.mp4` (eksik: 1).
- `01_EXPORTS` edisyonlari: CHAMPAGNE_IVORY, DEEP_BLACK, MIDNIGHT_BLUE,
  PURE_WHITE, WARM_PARCHMENT.

## 3. Uc mockup'in sahnesi / cerceve konumu (olculdu)

| cift | mockup (GxY) | poster kutusu (x0,y0,x1,y1) | 4:5 kirpimda (KX=600) | kutu skoru |
|---|---|---|---|---|
| AQUARIUS_GEMINI | 3000x2250 | [994, 264, 2006, 1614] | [394, 264, 1406, 1614] | 0.9932 |
| AQUARIUS_ARIES | 3000x2250 | [994, 264, 2006, 1614] | [394, 264, 1406, 1614] | 0.9933 |
| SCORPIO_TAURUS | 3000x2250 | [994, 264, 2006, 1614] | [394, 264, 1406, 1614] | 0.9956 |

**Ayni sahne, ayni cerceve kutusu** (uc ciftte de piksel piksel ayni kutu).

## 4. Canli 78 video = V01 ciktilari mi? HAYIR

Canli video (Etsy GET) 1024x1280, 138 kare, 4.60 sn. V01 ciktisi 1080x1350,
138 kare, 4.60 sn. V01 ciktisi canli cozunurluge LANCZOS ile indirilip dikey
kaydirma 0-140 px arasi tarandi; en iyi kaydirmadaki Y MAE:

| cift | kare 0 | kare 60 | kare 120 | en iyi dy |
|---|---|---|---|---|
| AQUARIUS_GEMINI | 81.85 | 85.64 | 82.64 | 28 / 50 / 34 |
| AQUARIUS_ARIES | 80.66 | 82.84 | 81.11 | 22 / 18 / 22 |
| SCORPIO_TAURUS | 58.43 | 62.69 | 59.36 | 0 |

Sebep: **sahne farkli**. Canli videodaki oda (koyu duvar, lamba, mumlar) V01
MIDNIGHT_BLUE mockup'inin odasi (bej duvar, konsol, orkide) degil.

Diger adaylar da tutmadi (AQUARIUS_GEMINI, kare 0, en iyi kaydirma):

| kaynak | Y MAE |
|---|---|
| V01 MIDNIGHT_BLUE export | 81.85 |
| V01 DEEP_BLACK | 106.88 |
| V01 WARM_PARCHMENT | 110.37 |
| V01 CHAMPAGNE_IVORY | 148.96 |
| V01 PURE_WHITE | 175.20 |
| POD_HERO_CROP/AQUARIUS_GEMINI/video_MB_cropped.mp4 (14 Eyl) | 51.85 |
| WALLPAPER/VIDEO_V2/.../WA_WP_VIDEO_AQUARIUS_GEMINI.mp4 (1800x1350, 345 kare) | 120.03 |

### POD videolari nereden geliyor?

- `pod-video-cover-match.yml` ilanin **kendi canli videosunu** Etsy'den GET eder
  ve yalnizca dikey konumunu kapaga gore kaydirir; sahneyi degistirmez. Yani
  843084674'un icerigi daha onceki POD yuklemesinden gelir.
- `pod-video-match.yml` (14 Eyl) V01 MB ciktisini hero kadrajina kirpip
  `POD_HERO_CROP/<cift>/video_MB_cropped.mp4` uretmis; bu dosya **bej sahne**
  (canli ile MAE 51.85) ve `ETSY_SWAP/` icinde yalnizca
  `swap_result.json` + `backup_4570112095_20260914_105345.json` var, video yok
  -> bu kirpim ilana **uygulanmamis**.
- Canli videonun sahnesi canli kapagin sahnesiyle ayni; o sahne
  `WALLPAPER/MOCKUP_V2/<CIFT>/WA_MOCKUP_V2_SET*_<Cift>_FINAL.jpg` (3-5 Eyl)
  ailesi. Canli video V01'in zaman imzasini tasiyor (138 kare / 4.60 sn /
  30 fps), yani ayni ates bocegi hatti **baska bir mockup girdisiyle**
  kosulmus; o kosunun ciktisi Drive'da aranan agaclarda (01_EXPORTS,
  POD_HERO_CROP, WALLPAPER/VIDEO_V2) bulunamadi.

## 5. ADIM 2 — referansi yeniden uretme

Betik yerelde, **yalniz DRIVE_ROOT ve EDITION sabitleri** degistirilerek
(seed 20260816, 88000 parcacik, KESIM 15-152, CRF 12, preset slow) kosuldu.

- Uretilen dosya 1 386 230 bayt; Drive orijinali 1 386 713 bayt.
- Kare basina Y MAE: **ortalama 0.0489**, en cok **0.0835** (kare 61),
  kare 0 = 0.0000. Hedef < 1.5 -> **GECTI**.
- Betigin kendi oz-testi MB edisyonunda "sembol genlik <5" FAIL veriyor
  (olculen 22.0); bu test orijinal 78 kosuda da ayni, uretim etkilenmiyor.

- 86 px kaydirma + canli referans (843084674) kiyasi: Y MAE **83.36** (kare 0),
  **86.13** (kare 60), **83.84** (kare 120). Hedef < 2.5 -> **GECMEDI**.
  Neden: yukaridaki sahne farki (kaydirma miktarindan bagimsiz; 0-140 px
  taramasinda en iyi deger 81.85).

**Kural geregi DURULDU: ADIM 3 (Aquarius+Aries uretimi) kosulmadi.**
