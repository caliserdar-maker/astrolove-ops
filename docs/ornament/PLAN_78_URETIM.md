# PLAN: Ornament 78 üretimi (koşusuz plan; Serdar onayına)

Tarih: 4 Kas 2026. Dal ornament-printful-katalog, HEAD 1695619 (ls-remote). Üretim, Actions ve Etsy yok; bu belge yalnız plan.
Dayanak: sıkılaştırma koşusu 41839101824 (BEKLENEN_SONUC 14/14 PASS, OLCUM çıkış 0). ORNAMENT_KARAR 28: 78 ilan × 5 stil.
ORNAMENT_KARAR 6: Printful 900 Circle, 954×954 px, 300 dpi. Serdar 4 Kas: GV + AQU görsel "A", O2 b, O3 a, O4 a.
Rakam kaynakları köşeli parantezde: [ölçüm], [dosya], [API], [tahmin]. Bağımsız inceleme bulguları işlendi: INCELEME_PLAN_78.md.

## 0. Ön kontrol (her biri tek başına, pipefail)
test_workflows.py 0; py_compile (7 dosya) 0; kova_kapi_testi yerel iki mod (CL + sahte Kova) 0; sikilastirma_mantik_testi 0 (22 vaka).

## 1. Girdi envanteri (koşusuz)
| Kaynak | Sayı | Beklenen 78 çiftle | Kaynak |
|---|---|---|---|
| `<CIFT>_ana.png` Drive md5 satırları (41839101824 girdi_sha.txt, 4 Kas 13:33 anlık) | 78 | birebir; eksik 0, fazla 0 | [dosya] |
| motor 6da763a `motor_gpt/girdi78/ana/*_alfa.png` | 78 | birebir | [dosya: git ls-tree] |
| motor 6da763a `motor_gpt/yerlesim78.json` anahtarları | 78 | birebir | [dosya] |
| `<burc>_symbol_gold.png` | 12 | 12 burç tam | [dosya] |

Üç liste birbiriyle ve alfabetik 78 çiftle aynı; ad uyuşmazlığı yok. Tam liste: motor yerlesim78.json anahtarları (AQUARIUS ile 12, ARIES 11, CANCER 10,
CAPRICORN 9, GEMINI 8, LEO 7, LIBRA 6, PISCES 5, SAGITTARIUS 4, SCORPIO 3, TAURUS 2, VIRGO_VIRGO 1 = 78).
İş akışında 78 için değişmesi gerekenler (bugün 6 çift sabit): ornament-78-ornek.yml:71-72 yalnız 6 ana PNG indiriyor; :84 `len(y) == 18`;
:107-108 yalnız 6 `*_alfa.png` (motor POSTER_ALFA çift başına zorunlu, ornament_motor.py:98); :142 ORNEK78_CIFTLER sabit 3 çift (:164 GV sınır-1
adımı, tek çift); :17 timeout-minutes 120; :12-13 `permissions: contents: write` (koşu listelemek için `actions: read` gerekir).

## 2. Gruplar ve denenme durumu
| Grup | Sayı | Neden ayrı | Yeni kodla denendi mi |
|---|---|---|---|
| Cancer ya da Libra içeren | 23 | ornament_motor.py:266-270 h_oran: CANCER her zaman CL sol, LIBRA CL sağ yüksekliği (taraftan bağımsız) | yalnız CANCER_LIBRA |
| Aynı burç | 12 | iki küçük sembol aynı kaynak | hiçbiri (ARIES_ARIES yalnız 2202 eski kodla) |
| Kova içeren | 12 | aquarius kenar onarımı (445 px) + onarımsız motor | yalnız AQUARIUS_PISCES |
| Diğer | 36 | - | GEMINI_VIRGO (CAP_SAG ve LEO_SCO yalnız eski kodla) |
Kesişim: CANCER_CANCER, LIBRA_LIBRA (CL+aynı), AQUARIUS_CANCER, AQUARIUS_LIBRA (CL+Kova), AQUARIUS_AQUARIUS (aynı+Kova); birleşim 42, diğer 36 [ölçüm].
Hiç denenmemiş sembol: TAURUS (12 çift; hiçbir koşuda yok) [dosya]. Kenar onarımı yeni kodla yalnız 7 kaynakta ölçüldü (ana, aquarius, cancer,
gemini, libra, pisces, virgo; KENAR_ONARIM.json 9 satır); aries, capricorn, sagittarius, leo, scorpio, taurus sembolleri ve 75 ana ölçülmedi [dosya].

## 3. Süre
Çift başına [ölçüm: log_ornek78.txt, çift başlangıcından çift sonuç satırına]:
- 41839101824 (son kod): CL 226,8 sn (kontrol dahil); GV 222,2 sn (596,6 → 818,8); GV sınır-1 221,4 sn; AQU 369,8 sn (onarımsız motor dahil).
- 2202 (eski kod, çift başlangıçları arası): 218,0 / 220,3 / 218,3 / 225,8 / 223,9 / 227,1 sn (sonuncu önizleme dahil).
- Onarımsız motor ek süresi: ~143 sn [tahmin: AQU 369,8 − ~227]. Onarımsız motor `degisen` olan HER çiftte koşar (ornek78.py:177-178), yalnız Kova'da
  değil; hangi kaynakların değiştiği 6 sembol ve 75 ana için bilinmiyor (bölüm 2) → hazırlıkta ölçülür (bölüm 4).
Sabit süreler [API: jobs 41839101824]: kurulum + girdi 71 sn; kapı testi 51 sn; Drive adımı 116 sn (45 dosya, ~20 ayrı rclone çağrısı + 3 listeleme;
süre çağrı sayısıyla büyür, dosya sayısıyla doğrusal değil).
78 çift seri [tahmin]: 78 × 227 = 17 706 sn + 12 Kova × 143 = 1 716 sn → 19 422 sn = 324 dk (+ bilinmeyen sayıda başka onarım çifti × 2,4 dk)
+ kurulum/kapı 2 dk + Drive (çağrı sayısına bağlı, ölçülmedi). Tek iş seri ÇALIŞMAZ: yml timeout 120 dk; GitHub barındırılan iş sınırı 360 dk
[GitHub belgesi; doğrulanmadı] sınıra yakın; tek hata noktası.

## 4. Bölme seçenekleri
Ortak koşullar:
- Tek Drive klasörü: hazırlık işi bir kez oluşturur (`rclone mkdir`, ID çıktı); paralel işler `--drive-root-folder-id` ile yazar
  (bugün yml:40 işe göre damga, :229-230 `assert len(m)==1` eşzamanlı yazımda bozulur).
- Tek dal yazıcısı: yalnız birleştirme işi commit/push (yml:251).
- CANCER_LIBRA her parçada İLK sırada, YALNIZ kontrol: kontrol PNG'leri ayrı klasöre, Drive'a yüklenmez, OLCUM'da `kontrol` alanına yazılır;
  CL ilan çıktısı tek bir parçadan (parça 1) ya da onaylı dosya (Soru 2). ornek78 başlangıcında "ilk çift CANCER_LIBRA değilse çıkış 2".
  Birleştirme CL'yi tekilleştirir (dusuk_kontrast, png_sha256).
- Hazırlık işi: (i) kapı testi (bir kez); (ii) TÜM kaynakların kenar onarımı ön ölçümü: 12 sembol + 78 ana için o5.kenar_onar n0 / değişen piksel
  (motor yolu; ana 1600 px hızlı, aquarius ~50 sn [ölçüm yerel]) → onarımsız motor koşacak çift listesi ve süre; (iii) sipariş koşusu
  kontrolü (`actions: read`): `siparis-*` in_progress/queued varsa DUR.
- Artifact: parçalar arası yalnız JSON (OLCUM, KENAR_ONARIM, log). PNG artifact'a girmez (public depoda artifact indirilebilir; yml:2 kuralı);
  PNG'ler yalnız Drive.

| Seçenek | Koşu | Duvar süresi [tahmin] | Uyum |
|---|---|---|---|
| (a) Matrix: hazırlık + 6 parça × 13 çift + birleştirme | 1 | ~70-75 dk (parça: kurulum + 13 ana indirme ~1-2 dk, CL kontrol 3,8, 13 × 3,8, 2 Kova × 2,4, Drive ~3-5 dk) | Actions 1 kez (CLAUDE.md:100/:104) |
| (b) Tek iş, süreç paralelliği | 1 | bilinmiyor: çekirdek, bellek, iş parçacığı ölçülmedi (paket.txt yalnız model) | ölçüm koşusu gerekir |
| (c) Sıralı partiler (ör. 4 × ~20 çift, ~85-95 dk) | 4 | ~6 saat | CLAUDE.md:100 ile çelişir; yalnız Serdar onayıyla |

ÖNERİ: (a). Parçalama: 12 Kova çifti 2'şer; Cancer/Libra (23), aynı burç (12) ve hazırlıkta onarım bulunan çiftler dengeli. max-parallel 6.

## 5. Sıra ve test (kurallar: CLAUDE.md:97-99, :100, :104)
Toplu üretimden ÖNCE gerçek oranda örnek + Serdar onayı zorunlu (:97-99). Matrix, artifact birleştirme, Drive ID ile yazım ve sipariş kontrolü
yerelde test edilemez; 78 koşusu test koşusu olmamalı. Bu yüzden İKİ AYRI görev (her biri Serdar onayıyla, her biri tek Actions koşusu):
1. ÖRNEK KOŞUSU (78 öncesi): aynı matrix iş akışı, 2 parça × 3-4 çift: denenmemiş gruplardan örnek (ör. ARIES_TAURUS ya da TAURUS_TAURUS,
   CANCER_CANCER, AQUARIUS_CANCER, VIRGO_VIRGO, LIBRA_LIBRA, AQUARIUS_AQUARIUS) + her parçada CL kontrol. Matrix, tek Drive klasörü, artifact
   birleştirme, sipariş kontrolü ve kenar onarımı ön ölçümü bu koşuda sınanır. Çıktı: çift başına 5 stil gerçek boy → Serdar göz onayı.
2. 78 KOŞUSU: örnek onayından sonra, kod değişmeden yalnız çift listesiyle.
Paralel üretilen görseller bağımsız göz kontrolü bitmeden dışa aktarılmaz (:98-99): birleştirmeden sonra tek bağımsız inceleme ajanı gerçek boy
görsellerde göz kontrolü yapar (FAIL ve dusuk_kontrast listeleri önce); sonuç Serdar'a.
Yerel test: tek çift ~222 sn [ölçüm], 60 sn sınırı (:103) tek çiftle sağlanamaz; yerel testler mantık testi + sahte kaynak + tek çift
uçtan uca (önceki görevlerdeki gibi). Parça yeniden koşusu "toplam 2 deneme" sınırından yer.

## 6. Dayanıklılık
- ETA satırı (:109): her çift sonunda `islenen/toplam, gecen, kalan, yuzde` (ornek78.py:261 döngüsü).
- Çift başına ara OLCUM (bugün yalnız sonda, ornek78.py:416) her çiftten sonra parça OLCUM'u güncellenir.
- Devam: runner geçicidir; yeniden koşuda `_is` boştur. Devam, Drive'daki parça OLCUM'u ve PNG listesi okunarak yapılır (PASS çift atlanır);
  ayrı Serdar onayıyla (ikinci koşu sayılır).
- Disk: çift başına çalışma klasörü 116-122 MB, katman.pkl 111,3 MB [ölçüm: yerel]. Parça (14 çift) ~1,7 GB [tahmin]. Çift bitince katman.pkl ve
  dump/ silinir (bugün silinmiyor); `df -h` başta ve sonda loga.

## 7. Kapılar ve FAIL davranışı
| Kapı | Yer | 78'de |
|---|---|---|
| CL onaylı kontrol (≤ 1 seviye / ≤ 10 px) | ornek78.py:348-361; return 3 :281/:301/:361 | her parçada ilk; FAIL = o parça DUR, birleştirme tüm koşuyu FAIL |
| Sert kapılar (koyu_*, sade1_*, fildisi_cikis_0) | ornament_motor.py:720-733, ornek78.py:313 | çift FAIL |
| Kova onarımsız bilinen FAIL (tek neden leke_a_kaynak_0) | ornek78.py:159-197 | ORNEK78_KENAR_ZORUNLU = 12 Kova çifti |
| Kapı testi onarimsiz_kapi_iddia | kova_kapi_testi.py | hazırlıkta; FAIL = koşu DUR |
| kucultme_le_sinir (2 px) | ornament_motor.py:63, :731 | çift FAIL, PNG üretilir, gerçek boy, Serdar'a |
| Kenar onarımı uyarısı + yakın plan | ornek78.py:184-188 | uyarı; onarım olan her çift |
| dusuk_kontrast (ham) | ornek78.py:404 | bilgi; listeler Serdar'a |
| Gerçek boy kontrolü | gercek_boy_kontrol.py | FAIL = koşu FAIL |
| YENİ önerilen: printful_dosya | (yeni) | aşağıda |

Kova "tek neden" kapısında yanlış FAIL riski: onarımsız motor leke_a_kaynak_0 dışında da FAIL olursa (ör. küçültme > 2 px, sembol sığmadı,
OLCUM'da kapi_sert yok) onarımlı çıktısı temiz olan Kova çifti FAIL olur (ornek78.py:159/:165). Öneri: koşul "onarımsız FAIL listesi = onarımlı
FAIL listesi + leke_a_kaynak_0" (kapı gevşemez: beklenen nedeni yine ister; yalnız onarımlı tarafta da olan FAIL'i ayrıca saymaz). Serdar sorusu 6.
YENİ kapı "printful_dosya" (sert): 954×954; renk modu RGB (koyu, FİLDİŞİ) ya da RGBA (SADE, şeffaf zemin kararı A); ICC yok ya da sRGB; dpi bilgisi
300 ± 0,5 (Soru 4). Bugün [ölçüm 6daab364 ve 41839101824]: koyu 3 stil RGB + 299,9994 dpi; SADE RGBA dpi yok; FİLDİŞİ RGB dpi yok; ICC yok.
Bilinen PASS: RUBY_954; bilinen FAIL: FİLDİŞİ_954 (dpi yok) ve 900 px'e ölçeklenmiş kopya.
"Durur"un anlamı (öneri): çift FAIL → 5 PNG Drive `FAIL/<CIFT>/`, ilana girmez, parça devam eder (O3). Çöküş (çıkış 2): bugün çift atlanır ve
koşu devam eder, 2 sonda verilir (ornek78.py:282 `continue`); öneri aynı (çift FAIL listesine). Koşu yalnız CL kontrolü ya da kapı testi FAIL'de durur.

## 8. Çıktı düzeni
- Tek Drive klasörü `ASTROLOVE/TEMP/ORNAMENT_78_<damga>_<run_id>/`: PASS çiftler kökte `<CIFT>_<STIL>_954.png`; FAIL çiftler `FAIL/<CIFT>/`
  (bugün yml:205 hepsini köke); `GERCEK_BOY/` (78 × 5 stil, 300 dpi); `YAKIN/`; `ONIZLEME/` (çift başına); `RAPOR/` (parça ve birleşik OLCUM,
  BEKLENEN_SONUC_78, KENAR_ONARIM, ön ölçüm, loglar).
- Dosya sayısı [tahmin]: 390 PNG + 78 gerçek boy + 78 önizleme + YAKIN (onarım olan çift × 8) + RAPOR (~20) ≈ 670+.
- Drive alanı [tahmin, 41839101824 boyutlarından]: 954 PNG 3,48 MB/çift → 0,27 GB; gerçek boy ~3,5 MB × 78 = 0,27 GB; önizleme ~2,8 MB × 78
  = 0,22 GB; ~0,8 GB. Boş alan hazırlıkta `rclone about`.
- ONIZLEME_76mm tek dosya 3 çiftte 8,38 MB [ölçüm] → çift başına, yalnız Drive. Dala yalnız JSON / MD / log (bugün yml:239, :249 önizlemeyi dala yazıyor).

## 9. Serdar onay noktaları
- 78'den ÖNCE: GV ve AQU 5 stil onayı ALINDI ("A", 41839101824); örnek koşusu çiftleri (bölüm 5) gerçek boy onayı.
- 78'den SONRA: bağımsız göz kontrolü sonucu; FİLDİŞİ CL düzeyi altı çiftler (O4); SADE dusuk_kontrast listesi (O2 b: bilgi; ölçülen 3 çiftin
  3'ü de 1,54 altında [ölçüm], 78'in çoğu girecek [tahmin]); küçültme > 2 px çiftleri (O3); kenar onarımı yakın planları.
  Biçim: çift başına 5 stil gerçek boy, 300 dpi.

## 10. Serdar soruları (öneri + seçenek)
1. SADE listesinde CL (ham 1,5372 < 1,54 [ölçüm]): öneri düzey 1,54 kalır, CL satırı "kontrol çifti" işaretlenir; seçenek düzey değişir
   (KALİTE 4 gevşetme, Serdar onayı).
2. CL ilanı için Printful dosyası: öneri onaylı 5STIL (6daab364); seçenek parça 1 çıktısı (fark 1 seviye / 1 px). Seçim bölüm 4 ile tutarlı uygulanır.
3. Bölme: öneri (a) + önce örnek koşusu (bölüm 5); (c) seçilirse 4 koşu için açık onay.
4. dpi bilgisi: öneri yeni 78 çıktısına piksel değiştirmeden dpi 300 yazılır; onaylı dosyalar (CL 6daab364, Kova 41839101824) DEĞİŞMEZ (sha
   kapıları yml:93-102 ve ONAY_COMMIT kanıtı kırılmasın). Onaylı CL ilanda kullanılırsa printful_dosya dpi kapısı CL için bilgi olur. Seçenek:
   dpi kapısı yok (Printful dpi bilgisini okuyor mu bilinmiyor; doğrulanmadı).
5. "Durur": öneri çift FAIL klasörü + devam.
6. Kova tek neden: öneri "onarımlı FAIL listesi + leke_a_kaynak_0" (bölüm 7).
7. Koşu sırasında sipariş gelirse: öneri parça başlangıcında yeniden kontrol, varsa parça beklemez, devam eder ve raporlar; seçenek parça iptal.

## 11. Risk ve bilinmeyenler
- TAURUS hiç denenmedi (12 çift). Cancer/Libra yolu (23) yalnız CL ile; aynı burç (12) yeni kodla hiç.
- Kenar onarımı 6 sembol ve 75 ana için ölçülmedi; onarımsız motor sayısı ve süre bilinmiyor (hazırlık ön ölçümü).
- O3 > 2 px gereken çift sayısı bilinmiyor (yalnız GV 2 px ölçüldü); 10 denemede sığmayan çiftte PNG yok.
- Kova tek neden kapısında yanlış FAIL (bölüm 7).
- Matrix / artifact / Drive ID / sipariş kontrolü yeni kod: örnek koşusunda doğrulanır.
- Sipariş kuyruğu: 6 runner ~70 dk dolu; hesap türü ve eşzamanlı iş sınırı ölçülmedi.
- ornament-son-uretim.yml `|| true` kaldırılması koşuyla test edilmedi; o2_sha_esit zayıf test; BEKLENEN_SONUC gercek_boy listesinde GV iki kez.
- Runner çekirdek, bellek, disk boş alanı ölçülmedi.
