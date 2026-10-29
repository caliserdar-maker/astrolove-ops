# Galeri v11 W02-W06 bilgi kartları: biçim ve kapı ÖNERİSİ (Denetim, 29 Eki 2026)

Durum: ÖNERİ, onay bekler. Kod yok, üretim yok, Etsy isteği yok. Kaynak etiketi: [DOSYA] depo / Drive, [OLCUM] betik çıktısı, [KARAR] karar belgesi.

## 1. Dosya adı ve MANIFEST

Taşınan W01/W07-W10 adlarıyla aynı kalıp (`<CIFT>_<Wnn>_<AD>.jpg`, galeri_tasi v11) [DOSYA scripts/kapak78/galeri_tasi.py]:

| W | dosya | sahip | kart (28 Eki şablonu) |
|---|---|---|---|
| W02 | `<CIFT>_W02_SEMBOL.jpg` | çift | S1_SEMBOL |
| W03 | `<CIFT>_W03_KISISEL.jpg` | çift | S2_KISISEL |
| W04 | `ORTAK_W04_FORMAT.jpg` (tek dosya, 78 ilanda aynı) | ORTAK | S3_FORMAT |
| W05 | `<CIFT>_W05_SUREC.jpg` | çift | S4_SUREC |
| W06 | `<CIFT>_W06_GENEL.jpg` | çift | S5_GENEL |

Klasör: `TEMP/POSTER_GALERI_V11/20261029_103607` (W01/W07-W10 ile aynı). Tamlık 78 x 4 + 1 = 313 kart, toplam 390 + 313 = 703. Bu sayı OZET.md'deki "78 x 9 + ORTAK W04 = 703" ile aynı [DOSYA OZET.md].

MANIFEST.csv'ye satır biçimi (mevcut sütunlara ek; bilgi kartı satırlarında Canva sütunları boş kalır):
`cift` (ORTAK satırında `ORTAK`), `ad` (W02_SEMBOL ...), `dosya`, `sha256`, `boyut`, `kaynak` (`kart_sablon@<commit>`), `kosu` (üretim koşu no), `durum` (kart kapısı PASS/FAIL).

Liste girdisi (`--kart-manifest`, galeri_v11_liste.py'de var olan sözleşme) [DOSYA scripts/kapak78/galeri_v11_liste.py:10-12]:
`{"format_boy_sayisi": <int|null>, "kartlar": {"ORTAK": {"4": "ORTAK_W04_FORMAT.jpg"}, "<CIFT>": {"2": "<CIFT>_W02_SEMBOL.jpg", "3": ..., "5": ..., "6": ...}}}`
Öneri: Ayrı bir JSON tutulmaz. Bu JSON, kart üretim koşusunda MANIFEST.csv'den üretilir; böylece tek kaynak kalır.

## 2. CANCER_LIBRA 10 görsel

| W | durum | kaynak |
|---|---|---|
| W01 kapak CI | VAR, kapı PASS | POSTER_GALERI_V11/20261029_103607/CANCER_LIBRA_W01_KAPAK.jpg (Canva DAHZUPu9Uvs) [DOSYA, KAPI 40863379487] |
| W02 sembol | ÜRETİLECEK (28 Eki örneği var) | TEMP/KART_SABLON_ORNEK/20261028_155614/WA_CANCER_LIBRA_S1_SEMBOL.jpg (koşu 40719918531) [DOSYA] |
| W03 kişiselleştirme | ÜRETİLECEK (örnek var) | aynı klasör WA_CANCER_LIBRA_S2_KISISEL.jpg |
| W04 format (ORTAK) | ÜRETİLECEK (örnek var), KARAR GEREKLİ | aynı klasör WA_ORTAK_S3_FORMAT.jpg; "14 Sizes" yalnız 5x7 yüklemesiyle doğru [DOSYA docs/kart_sablon/RAPOR_28EKI.md madde 1] |
| W05 süreç | ÜRETİLECEK (örnek var) | aynı klasör WA_CANCER_LIBRA_S4_SUREC.jpg (adımlar: Your Preview, Your Approval, Made to Order, Free Shipping) |
| W06 genel bakış | ÜRETİLECEK (örnek var) | aynı klasör WA_CANCER_LIBRA_S5_GENEL.jpg ("Choose Your Color") |
| W07 MB, W08 DB, W09 PW, W10 WP | VAR, kapı PASS | POSTER_GALERI_V11/20261029_103607/CANCER_LIBRA_W07_MB ... W10_WP.jpg [DOSYA] |

Üretim kodu `scripts/kapak78/kart_sablon.py` ve `wa_kupa_kart_ornek.py` yalnız `kart-sablon-20261028` dalında (909671ae) duruyor, main'de değil [DOSYA git]. Toplu üretimden önce main'e alınmalı (`workflow_dispatch` yalnız main).

## 3. Toplu üretimden önce açık kalanlar (kanıtlı)

1. W04 "14 Sizes" ve `format_boy_sayisi`: 5x7 envanteri canlıda yoksa kart yanlış bilgi verir. Bu bir karar konusu (Serdar).
2. W05 "Free shipping worldwide": plan v2 "Plan dışı bulgular" maddesi, canlı kargo profilinin yayından önce okunmasını istiyor [KARAR AstroLove_WA_CI_PLAN_20261029.md]. Yeni alt metin sıra 5 de "free shipping" diyor (a201160d).
3. W05/W06 poster kaynağı (şüphe, ölçülmedi): 28 Eki örneği `ref/kart_sablon_20261028/poster_kaynak` kırpımını kullanıyor; kırpım (891,591)-(2118,2128) [DOSYA OKU.md]. A kesimi ise şeridi dışarıda bırakmak için (901,601)-(2107,2118) [DOSYA kapak-ci-ref-20261029]. Canlı G7/G8'deki 10-14 px açık şerit [KARAR kapak kararı "Bilinen sorun"] bu nedenle W05 ve W06'ya taşınmış olabilir. Önce ölçülmeli; şerit varsa 78 çift için kaynak `ref/kapak_ci` CI_/PW_ kesimleri olmalı.
4. Çifte özel kaynaklar 78 için: W03 MB 2000x3000 posteri ve W06'nın 5 renk posteri. Örnekte yalnız CANCER_LIBRA dosyaları verildi (`--poster`, `--mb45`, `--poster-kaynak`); 78 çiftin kaynak klasörü belgede yok. Tahmin edilmez, Merkez/Serdar belirler.

## 4. Kapının W02-W06'ya genişlemesi

W02-W06 Canva'da değil, kodla (Pillow 11.0.0 + raqm) üretiliyor. Bu nedenle kapı iki katmanlı olur:
- a) Üretim kapıları (kart_sablon.py'de var, 28 Eki'de 17 kart PASS): çizilen metin satırları = beklenen satırlar sırayla, başlık/etiket birebir, yasak sözcük ve tire yok ("Frame not included" dahil), punto >= 58, ortalama |sol - sağ| <= 2, bloklar >= 40 px [OLCUM RAPOR_28EKI]. Yeni eşik yok.
- b) Dosya kapısı (galeri_v11_kapi.py'ye eklenir):
  - 3000x2250 JPEG.
  - sha256 = MANIFEST.
  - W04: tek dosya; 78 ilanda aynı sha.
  - W02/W03/W05/W06: çiftler arasında sha tekrarı 0.
  - Çifte özel metin: OCR ile burç adları = çift. Kodla üretildiği için çizilen metin listesi MANIFEST'e yazılır ve kapı onu okur.
  - Sahne farkı: onaylı CANCER_LIBRA kartıyla, çifte özel kutular (sembol, burç etiketleri, poster) hariç tutularak ölçülür. Eşik ÖNERİLMEZ. Önce 78 kartta `--olc` modu çalıştırılır, dağılım raporlanır, eşik Serdar onayına sunulur. Kod deterministik olduğundan beklenen fark 0'a yakındır; bu bir ölçüm hipotezidir.
- Onaylı referans: önce CANCER_LIBRA W02-W06 v11 adıyla üretilir ve Serdar onaylar. Eşik ölçümü bu onaylı setten yapılır (W01/W07-W10'daki K2 yöntemiyle aynı).
