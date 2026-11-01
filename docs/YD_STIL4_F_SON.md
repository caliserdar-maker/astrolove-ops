# Gorev F son kosu (3. ve son; Serdar 1 Kas onayi): bagimsiz inceleme sonrasi duzeltilmis rapor

- Kosu 41315246868, commit 55043c85 (dal yd-stil4), damga 20261101_141704. Kapi sonucu PASS 4/4, AMA asagidaki
  "Inceleme sonrasi gercek durum" bolumu kapi PASS'inin iki stilde kusurun duzeldigini gostermedigini yaziyor.
- Olcum kaynagi: bu kosunun OLCUM.json (kopya docs/yd_stil4/OLCUM_41315246868.json). Esiklerin cogu TAHMIN.
- Bagimsiz inceleme (1 Kas, tek ajan, yerel olcum /tmp/incF): tablodaki rakamlar OLCUM.json ile birebir; uyusmayan, karsilastirma TANIMLARI.

Drive (TEMP/YD_STIL4_ORNEK/20261101_141704):
- Kontak: https://drive.google.com/file/d/10p9rhm7LXGVqakD4YVQB86c45ys0E0S6/view
- Timeless 12x18: https://drive.google.com/file/d/1YuWKpn8r2KQ9Ibna2XoF8ypnm9JaeOBF/view
- FirstPage 12x18: https://drive.google.com/file/d/1DShVHY4RAxVHeOSqHX5cFhNim0TJqbUC/view
- Layers_A 12x18: https://drive.google.com/file/d/1DntX4CZtpoeoIeJ3a_SZcA7p2b2He9CM/view
- Botanical 12x18: https://drive.google.com/file/d/1FR11RlQsb5GNw5r8zkptX5Sd1dON0iwF/view
- Klasor: https://drive.google.com/drive/folders/1BMCjuHpJx0ayc2YlBTqXA8k9ZUBjQbpI

| Stil | Kapi (deger; esik, kaynak) | Kapi | Kusur gercekten duzeldi mi (inceleme) |
|---|---|---|---|
| Timeless | korelasyon 0,9965-0,9974 (>= 0,98 gorev metni); kazanc 0,9924-0,9946; kayma <= 0,10 px; SIFT <= 0,00054; yeni kirpma <= 0,00114 (<= 0,01 tahmin); doygun fazlasi 0,0012-0,0091 (<= 0,01 tahmin); maske disi 0 | PASS | KISMEN: yay 255 kirpmasi azaldi, ama rapordaki 0,0134 -> 0,0033 karsilastirmasi farkli tanimlar (asagi) |
| FirstPage | kenar paylari 178,05-178,37, fark 0,32 (<= 1); kose tasmasi 12x18 = 0, 8x10 = 0; profil ornek basina 0,021-0,067 (<= 0,08 tahmin) | PASS | EVET (kose; kapinin siniri asagida) |
| Layers_A | kirpilan bantta oge 0 px; SIFT 0,00006 | PASS | KAPSAM DISI KAYIP: kemerin %33,2'si kesiliyor (asagi) |
| Botanical | korelasyon 0,9922 / 0,9876; kazanc 1,0113 / 1,0145; maske disi (yeni tanim) 0,0076 / 0,0021 (<= 0,02 tahmin) | PASS | HAYIR: gorsel 2. kosuyla ayni; PASS yalniz kapi tanimi degistigi icin |

## Inceleme sonrasi gercek durum (kanitli)

1. Botanical maske disi susleme DUZELTILMEDI. botanical_parcalar 3081e4ad -> 55043c85 degismedi; maske disi olcusu yalniz eski 8x10
   koyulugundan hesaplaniyor, ciktiya bakmiyor (by_stil4.py:306-313). ESKI tanim iki kosuda ayni: 0,0227 / 0,0235 (> 0,02).
   k2 ile k3 Botanical yakin planlari arasinda piksel farki p99 6, 20'yi asan piksel 0. KAGIT_KENAR 31 (tahmin) kagidin yirtik kenar
   bandini kapi disinda birakiyor; adacayi uzerindeki sap uclari (177 / 185 px) o bantta oldugu icin kapi bu kusuru goremez.
2. Timeless: 2. kosu 0,0134 JPEG ciktidan, 3. kosu 0,0033 JPEG'e yazilmadan onceki diziden olculdu (ayni kodla JPEG yay 0,00274 ->
   0,00348). Eski taban 0,0055 (Lanczos) -> 0,0021 (dogrusal) dususu yalniz ara degerleme farki; kod yorumu (by_stil4.py:301) "Lanczos"
   diyor, kod INTER_LINEAR (:296). Ayni (3. kosu) tanimla: yay 2. kosu 0,0050 -> 3. kosu 0,00025; dallar 0,0044-0,0070 -> 0,0008-0,0011.
   Yani duzelme GERCEK, rapordaki eski rakamlarla degil.
3. Timeless "dallar hala fazla doygun" bulgusu taban seciminden: eski 8x10'un kendi cozunurlugunde dallarda 254+ orani 0,0241-0,0267,
   3. kosu ciktisi 0,0173-0,0214 (eskiden AZ). dal_sol_alt fazla 0,0091 / esik 0,01: JPEG farki (+0,0020) ile ~0,011 olur; esik
   marjinal ve tabana bagli (onceki inceleme bulgusu gecerli).
4. Layers_A: kemerin %33,2'si kesiliyor (OLCUM kemer_kesilen_oran 0,3321, 1.800.187 / 5.419.975 px); yanlardaki koyu kiremit kemer
   katmanlari kontakta gorunur bicimde kayboluyor. Kemer icin kapi ve esik yok.
5. FirstPage kose: kose_tasma 2. kosu JPEG'inde 1280, 3. kosuda 0 (dogru). Kapi siniri: merkezden <= 10 px tasma 0 sayiliyor
   (yapay test); kisa / yuvarlak kose yakalanmaz. 2. kosu taslaginda "169+169" eski tanimla yazilmisti.
6. R kanali omuz kirpmasi: OLCUM'da alan yok; yakin planda TL %0,99, BR %3,45 (eski 8x10 %3,96). Tam boy yerelde yok; dogrulanmadi.

## Durum ve oneri

- 3. kosu son kosuydu (HIZ VE KALITE madde 4: 2 iterasyon siniri asildi); yeni uretim kosusu ACILMADI.
- Kullanilabilir: FirstPage (kose duzeldi), Timeless (yay ve dal kirpmasi gercekten azaldi; esik marjinal).
- Serdar gorsel karari gereken: Botanical (maske disi kusur ayni; sap uclari aktarilmiyor) ve Layers_A (%33 kemer kesimi).
- Botanical icin duzeltme ancak yeni kod + 4. kosu ile (Serdar karari): maske disi olcusunu CIKTIDAN ve kagit kenar bandi dahil yapmak,
  sap ucu aktarimini adacayi ustunde ayri esikle denemek.
Bilinen kor noktalar: kose gonyesi bicimi, yazi blogu olcegi, Botanical yalniz 2 ceyrek, profil kapisi kendi cizim girdisini olcer.
