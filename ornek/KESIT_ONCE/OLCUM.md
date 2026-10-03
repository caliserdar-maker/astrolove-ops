# Zemin lekesi kaynagi (once, yeni = ornek-tek-doku 644d435), CANCER_LIBRA, 4800 px

Kesitler: ust satir 1:1, alt satir 4x kontrast. Sutunlar: orijinal | eski kosu | yeni.

| bolge | yeni - eski fark | eski - orijinal fark | sonuc |
|---|---|---|---|
| (a) cember cevresi, cemberden 3-8 px | ort 1.03, p99 7 luma | ort 0.60, p99 6 | leke yok (halkasiz zemin dolgusu cemberin altinda kaliyor) |
| (a) cember cevresi, 8-20 px | ort 0.00, p99 0 | ort 0.01, p99 0 | birebir ayni |
| (c) dokunulmamis bos zemin | 0 px fark (sayfanin cember / oge / temizlik disi tamami) | plate dokusu orijinalde de ayni | leke yok, doku plate'in kendisi |
| (b) yildiz temizligi | yildiz yerinde duz dolgu: rgb (17, 14, 18) std 6 / zemin (1, 4, 21) std 1.5 | - | LEKE YALNIZ BURADA ve yalniz yeni ciktida |

Kok neden (b): yildiz cekirdegi 45 px yerel medyanla dolduruluyor; medyan yildiz isigini da iceriyor (gri-kahve duz yama), 7 px genisletilmis maske yildiz isinlarini kapsamiyor (kirik isin kenari kaliyor).
CANCER_LIBRA 7, AQUARIUS_LEO 1 yildiz temizlenmis; SCORPIO_VIRGO 0 (b kesiti tagline sag payi).
