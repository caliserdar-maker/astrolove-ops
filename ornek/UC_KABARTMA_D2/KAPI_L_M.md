# Cember uclari (l) + kabartma stili (m), iki yonlu test, 4 Eki 2026 (deneme 2: kapi m FAIL, DURULDU)

Uc kusuru (once): geometrik alfa yarim pikselden ince ucta ~%80 kaplama veriyordu; uc parlak doygun sari, basamakli; aci yumusatmasi ucu ~2 derece uzatiyordu.
Duzeltme: kapsama 2 x hw ile sinirli; uc bolgesinde dar yumusatma; orijinal cemberin ucta solgunlasma / sonuklesme carpani (aci basina, govdede 1).

l: uc acisindan -14/+3 derece radyal kesit; normalize kesit alani farki <= 0.10, altin doygunlugu farki <= 0.15 (orijinal posterle).
m: goreli derinlik t kutularinda L = p(t) + qc cos th + qs sin th; (qc, qs)/core ana sembolden ortalama fark <= 0.03; kenar isik acisi farki <= 25 derece.

| cift | sayfa | l sag (sekil / renk) | l sol | l | m en kotu oge (dq) | m |
|---|---|---|---|---|---|---|
| CANCER_LIBRA | 0bf017f | 0.093 / 0.443 | 0.109 / 0.591 | FAIL | isim_sag 0.132 | FAIL |
| CANCER_LIBRA | yeni deneme 2 | 0.033 / 0.131 | 0.032 / 0.107 | PASS | sonsuz 0.068 | FAIL |
| SCORPIO_VIRGO | 0bf017f | 0.091 / 0.429 | 0.111 / 0.515 | FAIL | sonsuz 0.067 | FAIL |
| SCORPIO_VIRGO | yeni deneme 2 | 0.031 / 0.135 | 0.038 / 0.099 | PASS | sonsuz 0.034 | FAIL |
| AQUARIUS_LEO | 0bf017f | 0.094 / 0.671 | 0.106 / 0.962 | FAIL | isim_sol 0.131 | FAIL |
| AQUARIUS_LEO | yeni deneme 2 | 0.030 / 0.146 | 0.042 / 0.100 | PASS | sonsuz 0.054 | FAIL |

Deneme 2 diger kapilar: a-k PASS; yalniz CANCER_LIBRA i 0.0732 (esik 0.072) FAIL.

Kok neden (m kalan): (1) CANCER_LIBRA ana sembolu varlik (asset) yolundan; motor stili asset alfasi + carpilmamis renkten olcuyor -> vurgu-golge 152 (sayfada 20.6); tum ogeler 7 kat guclu kabartma. (2) sonsuz alfasi orijinalin parlakligindan (fark / ortanca) -> kendi kabartmasini saydamlik olarak tasiyor (cemberdeki eski kusurun aynisi); dq 0.034-0.068.
Onerilen 3. deneme (Serdar onayi ile): asset yolunda stil, sayfa birlesimi uzerinden qc ile ayni tahminci; sonsuz alfasi geometrik (esik + kapama + 0.7 px yumusatma).
