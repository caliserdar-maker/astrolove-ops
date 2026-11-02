# STIL3_V2: SAPPHIRE_GOLD, EMERALD_GOLD, RUBY_GOLD (2 Kas 2026)

Kosu: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41436684361 (deneme 2/2; betigin kendi kapilari PASS).
Deneme 1: https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41435681741 (EMERALD 3.31, FAIL). Deneme hakki bitti, yeni kosu yok.
Betik: `scripts/printful/ornament_ornek2.py` (uretim 7b7e565). Rakamlar `OLCUM_V2.json` (kosu) ve bagimsiz inceleme olcumleri (ayni PNG'ler).
1 px = 0.0847 mm.

## Ozet: istek maddeleri

| madde | durum |
|---|---|
| 0 yerlesim (buyuk + yukari, guvenli daire 15 px, yazi boyu) | TUTTU |
| 1 halka en kalin yer >= 6 px | TUTTU, ama halkanin yalniz %14'u >= 6 px; %68'i 4 px alti |
| 2 uc keskin, uc parlakligi govdeyle ayni | TUTMADI: uclar 30-44 derecede soluk |
| 3 halka parlakligi tek duze | GOVDEDE TUTTU (0-29 ve 151-360 derece), uclarda tutmadi |
| 4 okunurluk | SAPPHIRE / RUBY tuttu; EMERALD yalniz secilen olcum bandinda tuttu, hale "cok hafif" degil |
| 5 sonsuz en ince >= 3 px | SINIRDA: mesafe donusumuyle tam 3 px; kenar yumusatmasiyla en ince yer 2.75 px |
| 6 onizleme | TUTTU |
| 7 sekil dogrulama | Olculdu; en / boy farkinin aciklamasi KANITSIZ (geri cekildi) |

## 0. Yerlesim

| olcu | v1 | V2 | kazanc |
|---|---|---|---|
| halka dis capi (alfa 0.5 kutusu) | 554 px | 608 px (51.5 mm) | +%9.7 |
| ana sembol (en x boy) | 344 x 327 px | 378 x 358 px (32.0 x 30.3 mm) | +%9.9 |

- Ayni esikle karsilastirma. Olcek oraniyla (0.1814 / 0.1656) kazanc +%9.5. Onceki taslaktaki +%10.1 farkli esikleri karsilastiriyordu.
- Halka dis kenari y=222 (alfa 0.45; 223'ten itibaren 1). Delik alt kenari 192.6, centik alti 216.9. Halka centigin 5.1 px altinda (istekteki y >= 222 tanimi).
- Halkanin buyumesini sinirlayan: Rc 304'te tarih, 305-306'da isim1 de guvenli daire sinirinin (380.3 - 15) disina tasiyor.
  Rc 360'tan 1 px adimla arandi, ilk gecen Rc=303.
- Guvenli daireye pay 16.0 px (en dis nokta tarih, r=364.3). 15 px pay guvenli daireye uygulandi, centige uygulanmadi.
- Yazi kutulari v1 ile birebir ayni: isim buyuk harf 2.38 mm, tarih 2.02 mm. Kucuk Cancer / Libra 4.91 / 5.08 mm.
- Sira ayni. Araliklar daraltildi (isim buyuk harf birimi; tasarim secimi): sembol -> kucuk sembol 0.30, kucuk sembol -> isim 0.55, isim -> tarih 0.45.
- Cakisma yok.

## 1-3. Halka

Poster halkasi (ornek-tek-doku 2a08a78, HALKA_BLUE_16x20.png) olculdu:
- Merkez cizgisi yaricapi 1670.1 px.
- Genislik: tepe 19.5 px, yanlar yaklasik 10 px. Acik aralik 44-136 derece (0 = sag, 90 = asagi).

V2 halka bu merkez cizgisi ve genislik profiliyle (7 derece medyan) cizildi; genislik esit oranla tepe 7.0 px olacak sekilde buyutuldu.
Genislik dagilimi:
- 6 px ve ustu yalniz 251-288 derece: halkanin %14'u.
- %68'i 4 px alti, %31'i 3 px alti (0.25 mm).
- Iki daralma var: 215 derecede 2.72 px, 321 derecede 3.19 px. Sonra yeniden kalinlasiyor; posterde de var, profil oldugu gibi tasindi.
- Bu yuzden "uclara dogru tekduze incelme" yok.
- Baski riski suruyor: v1'deki 3 px uyarisi halkanin %31'i icin gecerli.

Uclar TUTMADI:
- Genislik 1 px altina 30-44 derecede iniyor: uc basina yaklasik 14 derece, 74 px yay, halkanin yaklasik %11'i. Posterde bu bolge yalniz 37-44 derece.
- Bu bolgede gorunen parlaklik dusuyor ve titresiyor. Inceleme: 37-43 derecede en yuksek luma 49-83; govdede 136-145.
- Neden 1: 7 derece medyan uca 40-43 derecede sabit 0.13 px duz kuyruk birakiyor; uc gercekten keskin degil, 44 derecede birden 0.
- Neden 2: kapsama formulu clip(h - |d| + 0.5) 1 px altinda kapsamayi yaklasik 2.4 kat sisiriyor.
- Betigin parlaklik kapisi bunu goremedi: yalniz alfa > 0.99 ve genislik >= 1 px acilara bakiyordu, halka tek renk oldugu icin min = max cikti.
Govde: 0-29 ve 151-360 derecede en yuksek gorunen luma 136-145, kesinti yok.

Duzeltme onerisi (yeni kosu, Merkez onayi gerekir):
- (a) Uc kuyrugu: medyan yerine genislik profiline monoton sonum.
- (b) Alt piksel kapsamasi icin dogru alan formulu (ya da 4x supersample).
- (c) Uc soluklugu: uclarda genislik 1 px'e inene kadar posterdeki incelme, sonra 2-3 px icinde sivri kapanis.
- (d) Kalinlik: govdeye taban (ornek >= 4 px) ya da tepe 9-10 px. Ikisi de poster oranindan sapma; karar Merkez'de.

## 4. Okunurluk

WCAG. Yazi = cekirdek ortanca renk. Parantez = arkadaki en acik %5 zemin.

| stil | yontem | bant | isim1 | isim2 | tarih |
|---|---|---|---|---|---|
| SAPPHIRE | hale yok, altin %4 acik | 3-6 px | 7.18 (6.31) | 7.47 (6.46) | 5.53 (5.01) |
| EMERALD | hale s=0.5, altin %12 acik | 3-6 px | 7.07 (5.99) | 7.91 (6.24) | 5.63 (4.55) |
| EMERALD | ayni cikti | kutu + 6 px (v1 yontemi) | (5.46) | (4.66) | (3.86) |
| EMERALD | ayni cikti | 6-12 px | (4.18) | (4.11) | (3.02) |
| RUBY | hale yok, altin %12 acik | 3-6 px | 7.26 (6.73) | 8.08 (7.48) | 5.62 (5.25) |

v1 ve 6-12 px satirlari bagimsiz inceleme olcumudur.

- **SAPPHIRE:** tarih 5'in ustunde ama payi yalniz 0.01. Hemen bitisik 1-3 px bantta en acik %5 ile 4.83.
- **EMERALD (TUTMADI):**
  - Deneme 1 FAIL olunca olcum bandi "kutu + 6 px"ten "murekkep cevresi 3-6 px"ye degistirildi.
  - Bu bant halenin tam koyulastirdigi bolgenin icinde kaliyor. Ayni ciktida v1 yontemiyle tarih 3.86, 6-12 px bantta 3.02.
  - Hale zemini yazi cevresinde %44 (3-6 px), %33 (1-12 px) koyulastiriyor; "cok hafif" degil.
  - Hale gucu icin kapi yoktu.
- **Tek doku:** EMERALD ve RUBY'de yazi altini halka ve sembolden %12 acik; tek doku birligi bozuluyor.
- Oneri (Merkez karari):
  - (a) EMERALD icin zemin degisikligi (yazi bolgesi daha koyu Canva zemini).
  - (b) EMERALD hedefini yalniz isimler icin 4.5, tarihi daha buyuk.
  - (c) Hale gucu ust siniri (orn. s <= 0.25) + kapi; tutmazsa EMERALD stilinden vazgecmek.

## 5. Sonsuz

Kaynak alfa (siparis-gpt alfa_ogeler.npz) hedef olcekte 1.25 px genisletildi; 3x3 acmada kayip %0, bilesen 1.
- **Kalinlik:** hassas mesafe donusumuyle en ince cizgi tam 3 px. Kenar yumusatmasiyla en ince yerin kapsama genisligi 2.75 px; sinirda.
  Taslaktaki 3.82 px tahmini yanliydi, yaklasik 1 px fazla gosteriyordu.
- **Boyut:** sonsuz v1'e gore kuculdu, 62 -> 60 px (5.25 -> 5.08 mm, -%3.2). Neden: genisletme payi da olcege katildi.

## 6. Onizleme (TUTTU)

- STIL3_V2_ONIZLEME_7cm.png: 827 px gorunen daire, koseler beyaz (saydamlik yok), asma deligi beyaz daire.
  Olculen merkez (476.5, 163.5), esdeger cap 57.9.
- STIL3_V2_KILAVUZ.png: tam 954 baski dosyasi.
  - Beyaz ince cizgi: 827 gorunen daire (x 63-890).
  - Mavi ince cizgi: 761 guvenli daire (x 96-857).
  - Kirmizi cizgi: delik. Mavi kisa cizgi: centik alti. Beyaz kisa cizgi: gorunen daire tepesi.

## 7. Ana sembol ile ozgun cizim

Ham alfa: siparis-gpt (6da763a) motor_gpt/girdi78/ana/cancer_libra_alfa.png. Kullanilan katman: CANCER_LIBRA_ana.png (sha e86c2629...).
Ikisi 0.5 esikte ikili, kirpilip 1200 px'e olceklendi, olcek + oteleme aramasiyla hizalandi.

| | ham | ana |
|---|---|---|
| en / boy | 1.0627 | 1.0571 |
| alan / kutu | 0.1635 | 0.1599 |
| cizgi kalinligi / genislik | 0.03058 | 0.03086 |

| hizalanmis | deger |
|---|---|
| olcek / oteleme | 1.000 / (-1, 3) px |
| NCC | 0.957 |
| IoU | 0.900 |
| +-2 px icinde kalan murekkep | %98.6 |
| hamda fazla / anada fazla | %1.45 / %1.37 |

- Olculen: hizalayinca murekkebin %98.6'si +-2 px icinde (1200 px'te).
- En / boy farki AÇIKLANMADI (%0.5, 1200 px'te yaklasik 6 px dikey).
  - Taslaktaki "ham alfa tuval kenarina degiyor, ana katmanda 300 px pay var" aciklamasi GERI CEKILDI.
  - Ham murekkep kenarlara yalniz tegit degiyor (kesilme yok). Pay, murekkep kutusunun en / boy oranini etkilemez.
- 0.831 -> 0.900 farki tek nedene baglanamaz: v1 ile V2 arasinda kirpma esigi, temizlik, calisma genisligi ve hizalama birlikte degisti.
- V2'de sifir otelemeli IoU raporlanmadi.
- Sonuc: sekil yuksek oranda ortusuyor; dikeyde %0.5 olcek farki ve kenar farklari var. Nedeni bilinmiyor. Uretimde posterde kullanilan ana
  katman kullanildi.

## Surec notu

- Deneme 1 Actions'ta FAIL oldu. Yerel test vekil kaynaklarla temizdi, ama gercek Drive kaynaklari (ana katman, kucuk semboller) yerelde yoktu.
  Bu, "Actions yalniz yerelde temiz cikan surum icin" kuralinin bu iste tam uygulanamadigini gosteriyor.
- Yerel vekil dosyalar kosudakilerle ayni degil (sha farkli).

## Dosyalar (Drive TEMP/ORNAMENT_ORNEK_20261102_1126/STIL3_V2/)

SAPPHIRE_GOLD_954.png, EMERALD_GOLD_954.png, RUBY_GOLD_954.png, STIL3_V2_ONIZLEME_7cm.png, STIL3_V2_KILAVUZ.png, OLCUM_V2.json,
KOSU_LOG.txt, KAYNAK_COMMIT.txt, RAPOR_STIL3_V2.md.
