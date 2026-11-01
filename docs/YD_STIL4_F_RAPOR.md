# Görev F raporu: YD 4 stil 12x18 örneği, 2. koşu (1 Kas 2026)

- Koşu 41305506283, commit 3081e4ad (dal yd-stil4), damga 20261101_121621.
- Çıktı: Drive `ASTROLOVE/TEMP/YD_STIL4_ORNEK/20261101_121621/` (https://drive.google.com/drive/folders/1OM6sJlt9D29V8Jg_yGLp96ZFPHEjuW_Z).
- Bu koşu, Serdar'ın verdiği 2 deneme hakkının ikincisiydi (son deneme).
- Koşu sonucu FAIL. Yeni (onaysız) kapılarla yalnız Layers_B düştü. Diğer stillerin hangi kapıdan geçtiği aşağıdaki tabloda; yeni kapılarla geçmek **PASS sayılmaz**, çünkü yeni kapılar onaylı değil.
- Sayıların kaynağı ayrıca yazılmadıysa: bu koşunun OLCUM.json dosyası (kopyası `docs/yd_stil4/OLCUM_41305506283.json`).

## Kapı sürümleri

| Ad | Commit | Ne değişti | Onay |
|---|---|---|---|
| G0 | 7a06e68f (1. koşu 41301638793) | Görev metnindeki kapılar: korelasyon ≥ 0,98; kazanç 0,95-1,05; kayma < 0,5 px; SIFT x/y ≤ %1; kırpılan / eklenen bantta öğe yok; çerçeve payları ≤ 1 px. Kayma cv2.phaseCorrelate ile ölçülür. | Eşikler Serdar görev metninden (dosya) |
| G1 | d2a38e47 (yerel, hiç koşulmadı) | G0'a ek: 255 kırpma oranı ≤ 0,01 (eskide de doygun olan pikseller dahil); maske dışı süsleme oranı ≤ 0,02 (taban çıkarılmadan); FirstPage çerçeve profili örnek başına fark ≤ 0,08 | Onaysız; eşikler tahmin |
| G2 | 3081e4ad (2. koşu) | Kayma artık numpy faz korelasyonu ile ölçülür. Kırpma yalnız yeni doyan pikseli sayar. Maske dışı oranından kağıt tabanı çıkarılır. FirstPage profili: en koyu nokta farkı ≤ 0,05 ve FWHM farkı ≤ 1 px. Layers_B dikiş kapısı: dE76 ≤ 3 ve gradyan oranı ≤ 1,5 | Onaysız; eşikler tahmin |

ESKİ tanımların bu koşuya uygulanmış değerleri `docs/yd_stil4/ESKI_YENI_KAPI_41305506283.json` dosyasında (betik `scripts/siparis_by/yd_stil4_eski_kapi_yeniden.py`).
- Maske dışı oranı yalnız eski 8x10 görselden hesaplanır; bu yüzden OLCUM.json ile birebir aynı çıktı.
- Kırpma oranı ise JPEG çıktıdan yeniden ölçüldü, değerleri yaklaşık. Yeni tanımın JPEG değeri OLCUM.json'dan en çok 0,0004 farklı.

## Stil bazında ESKİ ve YENİ kapı

### Timeless

Parça sırası: dal_sol_ust / yay / dal_sag_alt / dal_sol_alt.

| Ölçüm | Değer | Eşik (kaynak) | ESKİ | YENİ |
|---|---|---|---|---|
| korelasyon | 0,9974 / 0,9965 / 0,9972 / 0,9971 | ≥ 0,98 (görev metni) | PASS (G0) | PASS |
| kazanç | 0,9919 / 0,9930 / 0,9943 / 0,9934 | 0,95-1,05 (görev metni) | PASS | PASS |
| kayma, en büyük eksen | 0,012 / 0,045 / 0,004 / 0,006 px (numpy) | < 0,5 (görev metni) | 1. koşuda cv2 ile 0,511 FAIL (G0). Bu koşu cv2 ile ölçülmedi. | numpy ile geçti, ama ölçüm yöntemi onaysız değişti |
| SIFT x/y farkı | 0,00042 / 0,00026 / 0,00006 / 0,00081 | ≤ 0,01 (görev metni) | PASS | PASS |
| 255 kırpma oranı | ESKİ 0,0294 / 0,0134 / 0,0275 / 0,0338 (JPEG); YENİ 0,00153 / 0,00233 / 0,00079 / 0,00135 | ≤ 0,01 (tahmin) | **FAIL 4/4 (G1)** | yeni tanımla geçti |
| maske dışı süsleme | ESKİ 0,0064 / 0,0060 / 0,0020 / 0; YENİ 0 / 0 / 0 / 0 | ≤ 0,02 (tahmin) | PASS (G1) | PASS |
| dE76 çekirdek, medyan / p95 | 1,41/2,75; 1,47/2,56; 1,27/2,56; 1,41/2,56 | eşik yok | kapıda değil | kapıda değil |
| süsleme ile öğe kesişimi | 0 px | 0 | PASS | PASS |

### FirstPage

| Ölçüm | Değer | Eşik (kaynak) | ESKİ | YENİ |
|---|---|---|---|---|
| kenar payları | sol 178,37 / sağ 178,30 / üst 178,05 / alt 178,16; fark 0,32 | ≤ 1 px (görev metni) | PASS (G0) | PASS |
| sol pay, beklenenle | beklenen 178,34 (8x10 yan pay 118,89 × 1,5), fark 0,03 | ≤ 1 px | PASS | PASS |
| profil, örnek başına fark | 0,0813 / 0,0869 / 0,1187 / 0,0826 (sol / sağ / üst / alt) | ≤ 0,08 (tahmin) | **FAIL 4/4 (G1)** | yalnız bilgi |
| en koyu nokta farkı | 0,0138 / 0,0173 / 0,0028 / 0,0027 | ≤ 0,05 (tahmin; yerel vekil ölçüm 0,019) | yok | yeni tanımla geçti |
| FWHM, 8x10 → 12x18 | 7,60→7,65 / 8,05→8,05 / 6,85→6,85 / 7,15→7,15 | fark ≤ 1 px (tahmin) | yok | yeni tanımla geçti |
| **köşe** | **hiçbir kapı ölçmüyor** | | | |

**Köşe kusuru (kapılar görmedi).**
- 12x18 köşelerinde çizgiler birbirini kesip dışarı taşıyor ("+" şekli). 8x10'da köşe temiz L şeklinde.
- Ölçüm: sol üst köşede çizginin dışında kalan koyu piksel 12x18'de 169 + 169, 8x10'da 0 (bizim ölçümümüz, `/tmp` betiği).
- Görseller: kontak ve YAKIN_STIL4 (FirstPage (0,0) ve (3000,4800)).
- Neden: `cerceve_ciz`, çizgiyi köşeden profil penceresi kadar (`yari = PROFIL_T × 1,5`, yaklaşık 21 px) uzatıyor (by_stil4.py, cerceve_ciz).
- Görsel gözlem, ölçülmedi: çizginin yanında ondan ayrık, açık renkli ikinci bir iz görünüyor.

### Layers_A (kırpma)

Kapı tanımı G0 ve G2'de aynı.

| Ölçüm | Değer | Eşik (kaynak) | Sonuç |
|---|---|---|---|
| kırpılan bantta öğe | 0 px | 0 (görev metni) | PASS |
| SIFT | sx 1,80005, sy 1,79995, x/y farkı 0,00006 | ≤ 0,01 | PASS |
| kesilen kemer oranı | 0,3321 | eşik yok | yalnız bilgi |

### Layers_B (yeni düz doku + kemer üste sabit)

| Ölçüm | Değer | Eşik (kaynak) | ESKİ | YENİ |
|---|---|---|---|---|
| eklenen bantta kemer | 0 (yapı gereği; kemer yalnız 0-4500 satırına çiziliyor) | 0 | PASS (G0) | yok |
| eklenen bantta öğe | 0 px | 0 (görev metni) | G0 kapısında yoktu | PASS |
| SIFT üst bölüm | x/y farkı 0,00005 | ≤ 0,01 | PASS | PASS |
| dikiş renk basamağı | dE76 ort 2,92; p95 5,06 | ort ≤ 3 (tahmin); p95 için eşik yok | yok | ortalama geçti |
| dikiş gradyan oranı p99 | 1,615 | ≤ 1,5 (tahmin) | yok | **FAIL** |

Görsel gözlem (ölçülmedi):
- Dikişte renk basamağı görmedim.
- Yüksek gradyan noktaları kemer uçlarında toplanıyor (sol kenar y 2000-4500, sağ kenar). Orada eski kemerin kendi açık kenar çizgisi var; kapı bu gerçek kemer kenarını da sayıyor olabilir.
- Yeni dokuda 1:1 bakışta küçük benekler var; eski düz alanda yok.
- Tasarımın altında 1146 px boşluk kalıyor; bu düzen ölçüsü kapıda yok.

### Botanical

Parça sırası: cicek_sag_ust / cicek_sol_alt.

| Ölçüm | Değer | Eşik (kaynak) | ESKİ | YENİ |
|---|---|---|---|---|
| korelasyon | 0,9922 / 0,9876 | ≥ 0,98 (görev metni) | PASS (G0) | PASS |
| kazanç | 1,0100 / 1,0134 | 0,95-1,05 | PASS | PASS |
| kayma | 0,038 / 0,007 px (numpy) | < 0,5 | ölçüm yöntemi değişti | PASS |
| SIFT x/y | 0,0002 / 0,0004 | ≤ 0,01 | PASS | PASS |
| 255 kırpma | ESKİ 0,00066 / 0,00049; YENİ 0,00033 / 0,00003 | ≤ 0,01 (tahmin) | PASS | PASS |
| maske dışı süsleme | ESKİ 0,0227 / 0,0235; YENİ 0,0023 / 0,0180 | ≤ 0,02 (tahmin) | **FAIL 2/2 (G1)** | yeni tanımla geçti; cicek_sol_alt eşiğe yakın |
| dE76 medyan / p95 | 1,54/2,75; 1,41/2,75 | eşik yok | kapıda değil | kapıda değil |

Botanical betiği yalnız sağ üst ve sol alt çeyrekteki süslemeyi arıyor; diğer çeyreklere bakılmadı.

## Timeless kayma ölçümü: öz-test

- Betik: `scripts/siparis_by/yd_stil4_faz_oztest.py`. Sonuçlar: `docs/yd_stil4/FAZ_OZTEST_41305506283.json`.
- Girdi: bu koşunun Timeless çıktısı, 2400 genişliğe küçültülüp koyuluk haritasına çevrildi.
- İki kırpım boyu test edildi: 702x650 ve 1968x1842 (1. koşuda 0,50 px yanlılık veren boylar).
- Kaydırma iki yolla yapıldı: Fourier ile tam alt piksel kaydırma ve bilinear kaydırma.
- Ortam: OpenCV 5.0.0.93, numpy 2.5.3. Bunlar iş akışının kurduğu sürümlerle aynı.

| Bilinen kayma | numpy (yeni) | cv2.phaseCorrelate (eski) |
|---|---|---|
| 0 (özdeş girdi) | 0,000 | dik eksende 0,49-0,50 |
| 0,25 | 0,084-0,143 | 0,030-0,725 |
| 0,45 | 0,256-0,381 | 0,148-0,786 |
| 0,5 | 0,473-0,521 | 0,196-0,813 |
| 0,55 | 0,619-0,743 | 0,627-1,354 |
| 1 | 1,000 | 0,996-1,504 |
| 2 | 2,000 | 1,938-2,498 |

Sonuç:
- Yeni ölçüm özdeş girdide 0 veriyor; 0,5 / 1 / 2 px kaymaları en çok 0,027 px hatayla buluyor.
- Ancak ara değerlerde S biçimli yanlılık var: 0,5'in altındaki kaymayı küçük, üstündekini büyük ölçüyor (en büyük hata 0,214 px). Bu testte 0,5 eşiğine göre karar hep doğru çıktı, ama raporlanan değer kesin değil.
- cv2 bu sürümde özdeş girdide dik eksende 0,5 px veriyor. Bu yüzden 1. koşudaki 0,511, eşik 0,5'e göre kaymayı gürültüden ayıramaz.
- Öneri (uygulanmadı): alt piksel kestirimini daha doğru bir yöntemle değiştirmek, örneğin büyütülmüş DFT ile tepe arama.

## Kapı listesi ve eksik tanımlar

| Stil | Kapıda olan | Ölçüp kapıya koymayan / hiç ölçmeyen |
|---|---|---|
| Timeless | 4 parçanın her birinde korelasyon, kazanç, kayma, SIFT, kırpma, maske dışı; öğe kesişimi; 4 parçanın da bulunması | dE76 eşiksiz; yazı ve öğe bloğunun ölçeği ve yeri ölçülmüyor (by_poster çizimi); eklenen bantta öğe olmaması yalnız yapı gereği |
| FirstPage | 4 pay eşit (≤ 1 px), sol pay beklenen değerde, profil (G2) | **köşe ölçülmüyor (kusur bu yüzden kaçtı)**; sağ / üst / alt pay beklenenle doğrudan kıyaslanmıyor (dolaylı olarak 2 px'e kadar kaçabilir; ölçülen hepsi ≤ 0,29); yazı bloğu ölçülmüyor; SIFT yok |
| Layers_A | kırpılan bantta öğe, SIFT (tüm görsel) | kesilen kemer oranı (%33,2) yalnız bilgi |
| Layers_B | eklenen bantta öğe, SIFT (üst bölüm), dikiş dE ortalaması, dikiş gradyanı | dE p95 eşiksiz; gradyan kapısı gerçek kemer kenarını da sayıyor olabilir; alt boşluk (1146 px) ölçülmüyor |
| Botanical | Timeless ile aynı (2 parça) | yalnız 2 çeyrek aranıyor; dE76 eşiksiz; yazı bloğu ölçülmüyor |
| İş akışı | | Python FAIL döndürünce `bash -e` adımı, KOD değişkeni yazılmadan düşürüyor. "by_stil4 hata" iletisi yanıltıcı: gerçekte bir kapı FAIL oldu (LOG.txt sonu: "sonuc": "FAIL"). |

## Öneriler (hiçbiri uygulanmadı; her biri 3. koşu demek, Serdar onayı gerekir)

1. FirstPage köşesi: çizgiyi köşede profil penceresi yerine çizgi yarı kalınlığı kadar uzatmak. Ayrıca köşe kapısı eklemek: köşe dışındaki koyu piksel, 8x10 × 1,5 değerinden fazla olmasın.
2. Layers_B gradyan kapısı: ölçüm bandından eski kemerin kendi kenarını çıkarmak, ya da aynı ölçümü eski 8x10'da yapıp oranı onunla kıyaslamak.
3. Kayma: alt piksel yöntemini düzeltmek, öz-testi kapı betiğine eklemek.
4. Eşikler (0,01 / 0,02 / 0,05 / 3 / 1,5): hepsi tahmin. Onay ya da ölçümle türetme bekliyor.
