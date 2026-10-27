# 1st Anniversary (YD) 78 kapak: dışa aktarma, taşıma ve yükleme planı (v3, 26 Eki 2026)

Depo kopyası (27 Eki): yd_ops.py, KAPAK_KAYNAK.csv ve YD_LOG_B1..B4.tsv / YD_LOG_75.tsv bu klasörde (docs/yd_kapak/). Plandaki "yd_kapak/" yolları bu klasördür.

Kapsam: 78 YD ilanında yeni kare kapak (2400x2400, Botanical sahne) 1. sıraya girer. Kapak BAĞSIZ kalır; Botanical bağı kendi stil görselinde (rank 12) kalır. Eski kapağın silinmesi Serdar kararına açık (karar 2). Galeri kartları, fiyat, Heading ayrı iş. Video kapak işi bu yüklemeden SONRA, ayrı iş.
v2'ye yapılan bağımsız incelemenin 15 bulgusu işlendi. Etsy'ye yazan her adım ayrı Serdar onayı.

## Doğrulanmış durum (kaynaklı)
- 78/78 YD ilanı: active, 13 görsel, kapak 2400x2400, Style 5/5 bağlı ve bağlı görseller galeride, video var, 15 ürün (bizim veri: Drive TEMP/YD_ENVANTER_20261026/YD_OZET.csv, yd-envanter-oku, 13:06 UTC).
- YD_OZET'in kontrol ettiği alanlarda (state, görsel sayısı, kapak boyutu, Style seçenekleri, bağ sayısı, bağlı görsel galeride, video var, ürün sayısı, fiyat aralığı) 77 ilanın pilottan tek farkı fiyat aralığı: 77 ilan 3.9-29.0, pilot 3.9-24.9 (bizim veri: YD_OZET.csv, FARKLI.csv 77 satır). Kapağın bağsız olması, Botanical rank'i, alt metinler, görsel kimlikleri bu karşılaştırmada YOK; kuru koşu canlıdan okur. Ham veri: aynı klasör HAM/<listing_id>.json.
- Pilot 4595350971 (CANCER_LIBRA), PILOT_4595350971.json 13:13 UTC (bizim veri; saat inceleme bulgusu): rank 1 kapak 8760104081 2400x2400; rank 2-13 alt metni boş; Style (property 513) bağları Starlit r9, Timeless r10, First Page r11, Botanical 8678064852 r12, Layers r13; kapak bağsız; video 847831962; o anda kalan kota 343 (aynı json, "kota").
- Botanical kararı: kapak bağsız, Botanical bağı rank 12'deki kendi görselinde (Serdar 15 Eki; depo scripts/etsy/by78_kapak_bordo.py:2-9; Serdar 26 Eki teyit).
- Çift kümesi: YD 78 çift = data/pod/pod78_ids.csv 78 çift (yerel karşılaştırma). AMA pod78_ids.csv'deki listing_id'ler poster ilanları (ör. 4570110121); YD id'leri yalnız KAPAK_KAYNAK.csv (tur=yd) ve YD_OZET'te (bizim veri).
- Canva tasarım listesi (78):
  - 3 onaylı örnek, başlık "YD Kapak Ornek <CIFT>": SAGITTARIUS_SAGITTARIUS DAHZHr2mx2E, CAPRICORN_SAGITTARIUS DAHZHkbHFBk, ARIES_LEO DAHZHvJi_UE (yd_ops.py ORNEK).
  - 75 ajan tasarımı, başlık "YD_KAPAK_V1 <CIFT>", 4 grup B1 19, B2 19, B3 19, B4 18 (yd_ops.py liste). Kayıt 17:21 UTC: B1 12/19, B2 14/19, B3 19/19, B4 18/18 = 63/75; tekrar eden çift / tasarım yok (bizim veri: yd_kapak/YD_LOG_B1..B4.tsv, 5 sütun: cift, design_id, asset_id, listing_id, kaynak_image_id).
  - Pilot CANCER_LIBRA için ajan kopyası DAHZIAyOYA8 kullanılır (YD_LOG_B*.tsv); şablon DAHZHemU2a4 kullanılmaz.
  - Referans: şablon DAHZHemU2a4'ün ONAY ANINDAKİ görüntüsü ve metni. 26 Eki Merkez kontrolünde metin ve görüntü değişmemiş görünüyor; updated_at oynayabildiği için ölçüt değildir (inceleme bulgusu 10).
- Canva link ömrü: 65-115 dk (Merkez ölçümü, 26 Eki 17:13 UTC). Önbellekten eski imza dönebiliyor (bizim veri: poster_v10/exp_urls.txt, 35 link, X-Amz-Date 25 Eki).
- Depo (origin/main 32f7a83, 26 Eki 17:21 UTC fetch): kapak_v10_yukle.py yok. galeri_tasi.py yalnız poster profili (3000x2250, <CIFT>_G<n>.jpg, satirlar() 4 sütun ister: 3 sütunlu satır SESSİZCE atlanır, galeri_tasi.py:34-42). galeri-v10-tasi kilit grubu galeri-v10, bekleme 40 dk (yml:27). eski78'de cdn_yedek kilit ALTINDA koşuyor (eski78:495, yml kilit adımından sonra). durum_dosyasi.py:122 "PASS geri dönmez" koruması set >= 17'ye sabit.

## Adımlar
1. Canva metin kapısı (Claude, Etsy yok, dışa aktarmadan önce): 78 tasarım için read-design: başlık = "YD_KAPAK_V1 <CIFT>" ya da "YD Kapak Ornek <CIFT>"; çift satırı metni = "<A> & <B>" (yd_ops.py ops); design_id = YD_LOG_B1..B4 + 3 örnek listesi. Sonuç METIN_KAPI.tsv (cift, design_id, baslik, satir_metni, durum). 78/78 PASS olmadan dışa aktarma yok. B1/B2 tamamlanmadan bu adım başlamaz.
2. Taşıma hazırlığı (Denetim, Etsy yok, dışa aktarmadan ÖNCE):
   - galeri_tasi.py'ye `--urun yd` profili: hedef 2400x2400, ad KAPAK_<CIFT>.jpg, beklenen dosya listesi 78 (KAPAK_<CIFT>.jpg x 78), OZET "78/78".
   - TSV biçimi: Serdar kararı 4 (öneri 4 sütun: cift, kart_no=1, design_id, url; satirlar() aynen kalır). Hangi biçim seçilirse seçilsin: başlık dışı atlanan satır FAIL olur.
   - Çift/tasarım kapısı: TSV'deki (cift, design_id) çifti METIN_KAPI.tsv'deki PASS satırıyla aynı değilse satır FAIL.
   - Link süresi, satır başına: indirme anında kalan süre X-Amz-Date + X-Amz-Expires ile hesaplanır; 5 dk altıysa indirilmez, SURE_AZ yazılır (yeniden dışa aktarma listesi). Aynı tasarım için önceki koşudaki imza (X-Amz-Date + imza) aynen dönerse o satır DUR (önbellek döngüsü yok).
   - Yeni iş akışı yd-kapak-tasi.yml (galeri-v10-tasi.yml kopyası), AYRI kilit grubu yd-kapak; kilit bekleme 15 dk (öneri). Eşik kuralı: TSV'ye giriş eşiği > kilit beklemesi + koşu süresi + 5 dk. Öneri eşik 45 dk (15 + koşu üst sınırı 25 dk tahmin + 5); koşu süresi ilk grupta ölçülür, eşik ölçüme göre düzeltilir. Canva link ömrü 65-115 dk (Merkez ölçümü) olduğundan eşik 60 dk'yı geçemez.
   - Çıktı TEMP/YD_KAPAK_V1/<damga>/; ikinci ve sonraki gruplar hedef_damga ile aynı klasöre; yeni dosyalar --immutable; aynı ad farklı sha FAIL; iki adda aynı sha FAIL.
   - Testler: poster profili 8 testi aynen geçer + YD testleri (2400x2400 kabul / 3000x2250 red, KAPAK_<CIFT>.jpg adı, beklenen 78 listesi, 3 sütun satır davranışı, METIN_KAPI uyuşmazlığı FAIL, SURE_AZ, aynı imza DUR, ikinci grup aynı klasöre ekleme).
   - kapak78-tasi-test KULLANILMAZ (3000x2250 sabit, hedef_damga yok, --immutable yok, sha tekillik yok).
3. Dışa aktarma (Claude): tasarım başına 1 çağrı, sayfa 1, JPG kalite 95, 2400x2400; 8-10'luk gruplar. Kalan süresi eşiğin altındaki link TSV'ye girmez. TSV Drive'a; Denetim aynı dakikada yd-kapak-tasi koşturur. Bitiş: OZET 78/78 geçerli, FAIL 0, sha256 tekil.
4. Ölçümlü QC (tek betik, Actions, Etsy yok; göz kontrolünün yerine):
   - Her KAPAK_<CIFT>.jpg: JPEG, 2400x2400; poster bölgesi (şablondaki kutu, yd_ops.py KIRP) KAPAK_KAYNAK.csv'deki o çiftin kaynak görseli (kaynak_image_id, 2400x3000, aynı kırpma) ile NCC; poster dışı sahne, onay anındaki şablon görüntüsüyle NCC. Eşikler 3 onaylı örnek + pilot kopyası üzerinde ölçülür, sonra sabitlenir.
   - Çift satırı: adım 1 METIN_KAPI sonucu raporda yan yana.
   - Çıktı QC_RAPOR.json (dosya, NCC poster, NCC sahne, durum) + kontak sayfası (78 küçük görsel, çift adıyla). Kontak sayfası Serdar'a; görsel onayı yalnız Serdar'da.
5. Yedek (Actions, Etsy API yok, kilitsiz): HAM/<id>.json url_fullxfull'dan 78 ilanın 13 görseli + bağ listesi -> TEMP/YD_KAPAK_V1_YEDEK/<damga>/. yedek_mb_kontrol.py A kısmı genelleştirilir (girdi HAM, beklenen 13). Kontrol: ilan başına 13 dosya, boyut = JSON.
6. Yükleyici girdileri (Denetim, yeni betik yd_liste_uret.py, Etsy yok):
   - YD ilan kimlik listesi data/pod/yd78_ids.csv (listing_id, cift, a, b), KAPAK_KAYNAK.csv tur=yd'den; YD_OZET ile 78/78 aynı olmalı.
   - İlan başına LISTE_<ilan>.csv, HAM'dan: rank 1 yeni kapak DEGISTIR; eski kapak CIKAR (karar 2 "tut" çıkarsa CIKAR yerine KORU, son sıraya); rank 2-13 KORU; alt metinler HAM'daki gibi aynen (boş olanlar boş); yeni alt metin yalnız kapakta (karar 1).
   - Manifest: variation_images = HAM'daki 5 Style bağı aynen (Botanical -> rank 12 görseli); kapak bağsız.
   - Dosya adı eşlemesi: KAPAK_<CIFT>.jpg -> eski78 hedef_gorsel adı (NN_<id>.jpg; hedef_id bu addan okur, eski78:287-289). Eşleme tablosu + her dosyanın sha256'sı (taşıma MANIFEST.csv ile aynı olmalı).
   - Kart QC karşılığı: eski78 iş akışındaki KART_RAPOR.json kapısının YD karşılığı QC_RAPOR.json (adım 4); kapak PASS değilse yükleme koşusu başlamaz.
   - Üretilen 78 LISTE + manifest + eşleme kuru koşudan ÖNCE bağımsız incelemeden geçer.
7. Yükleyici (Denetim): eski78_gorsel_yukle.py'nin poster v10 genelleştirmesine YD profili (tek genelleştirme, iki profil). Kanıtlı parçalar aynen: adim_plani (erken bağ + son bağ, AYNEN; Serdar 26 Eki), yukle_guvenli, stabil_galeri, durum_uzlas, DEVAM/--kurtar, ayrı sıra geçişi, bag_kur onarımı, istek_en_kotu.
   YD profilinde değişenler (kod okuması):
   - HEDEF_N 17 sabit (eski78:45) -> 13 (karar 2 "tut" ise 14).
   - renk_degerleri yalnız renk adlarını alıyor (cl_galeri_degistir.py:68-77); YD'de {} döner ve DUR (eski78:446-448). YD: envanterden property 513 (Style) değerleri; Format 514 dışarıda.
   - liste_oku boş alt metni reddediyor (eski78:280); YD'de KORU satırında boş alt izinli, sıra geçişinde aynen geri gönderilir.
   - Sıra (adim_plani'nin YD için ürettiği, kod okuması eski78:224-258): kapak yükle -> kapak rank 1 -> erken bağ (5 Style bağı aynen) -> eski kapak sil -> sıra -> son bağ. En fazla 14 görsel.
   - Değerlendirme sırası: önce DEVAM kaydı (varsa devam/kurtarma yolu), sonra ZATEN, en son BLOK kuralları. BLOK yalnız ilk koşuda (DEVAM yok, ZATEN değil) uygulanır; yarım kalmış ilan BLOK'a düşmez.
   - ZATEN: rank 1 alt metni = yeni alt metin VE rank 1 id DEVAM kaydında. Yeni alt metin olup kayıt yoksa BLOK (elle).
   - BLOK (ilk koşu): state active değil | galeri 13 değil | Style bağı 5 değil ya da bağlı görsel galeride değil | kapak (rank 1) bağlı | Botanical bağlı görsel KAPAK_KAYNAK kaynak_image_id'si değil | canlı id kümesi = yedek değil | kapak dosyası 2400x2400 değil / sha eşleme tablosuyla aynı değil | yedekte eski kapak yok.
   - Kilit altında toplu indirme yok: 78 kapak, LISTE, manifest kilit öncesi indirilir; cdn_yedek YD profilinde kilit DIŞINA alınır (kilit öncesi adım; adım 5 yedeği zaten var). Kilit altında yalnız Etsy çağrıları.
   - Durum dosyaları durum_dosyasi.py kapısından; "PASS geri dönmez" eşiği sabit 17 yerine ürünün beklenen görsel sayısı (galeri77 17, poster v10 9, YD 13). DEVAM_<ilan>.json yazımları da (Kayit.yaz, Drive copyto) aynı kapıdan geçer.
   - Kota kapısı: etsy_common.KOTA_SINIRI 10 (etsy_common.py:164); ilan başında kalan - istek_en_kotu < 10 ise ilana başlamaz. Zamanlanmış koşu yok.
8. Yerel test (sahte Etsy): YD normal akış; yükleme hatası sonrası ikinci yükleme yok; bağ boş dönerse DUR; boş alt metinli KORU; DEVAM -> ZATEN -> BLOK sırası (yarım ilan BLOK'a düşmez); cdn_yedek kilit dışında; durum eşiği 13; poster testleri aynen geçer. Tek bağımsız inceleme; bulgular düzeltilmeden kuru koşu yok.
9. Kuru koşu (salt okuma, ayrı onay): kota sığma kontrolüyle (Kota bölümü). Sonra pilot 4595350971 (ayrı onay; kapak dosyası DAHZIAyOYA8'den).
10. Yükleme sonrası kontrol (her grup, kilitsiz, galeri_ornek.py kalıbı; eski78 yml:9): Etsy'deki rank 1 kapak (CDN) <-> yerel KAPAK_<CIFT>.jpg NCC; kapak bağsız; Botanical bağı rank 12 görselinde; galeri sayısı beklenen. Gruplar arasında Serdar Etsy'de görsel bakış yapar; onay gelmeden sonraki grup yok.
11. Kalan 77 ilan, kotaya göre gruplar (her grup ayrı onay).

## Kota
- Kuru koşu: ilan başına 7 GET (eski78:425-464), 78 ilanda 546 (hesap). 13:13 UTC'de kalan 343 (bizim veri: PILOT json). 343 ile tek koşuda en fazla (343 - 10) / 7 = 47 ilan (hesap); kuru koşu ya iki parçada ya da kota yenilendikten sonra, koşu başında kalan okunarak. Yenilenme saati/miktarı burada doğrulanmadı.
- Yükleme, en kötü durum (istek_en_kotu, eski78:56-70; OKUMA_TEKRAR 8, SIRA_TEKRAR 3, N 13): adim_plani AYNEN (erken + son bağ) ilan başına 185, 78 ilanda 14.430 (hesap: 7 + yükle 21 + kapak 11 + bağ 11 + sil 11 + sıra 94 + bağ 11 + son 19). Karar 2 "tut" (silme yok, N 14) ise ilan başına 180, 78 ilanda 14.040 (hesap).
- Yükleme, sorunsuz yol: ilan başına yaklaşık 35 (tahmin, kod okuması); pilot gerçek sayıyı ölçer.
- Grup boyu = (kalan kota - 10) / 185, aşağı yuvarlanır (kod kapısıyla aynı mantık).
- Poster galeri v10 aynı kotayı paylaşır (tahmin 5.000-6.000, GALERI_V10_PLAN_V2). Öneri: YD pilotu poster pilotundan sonra.
- Canva: 78 dışa aktarma + SURE_AZ tekrarları; 78 read-design (hesap). Hız sınırı: ~30 çağrıda "Too many requests" (bizim gözlem, poster v1).

## Serdar kararları
Verilenler (26 Eki): bağ sırası eski78 kanıtlı yol, adim_plani aynen; Botanical bağı kapağa taşınmaz, kapak bağsız; video kapak işi bu yüklemeden sonra, ayrı iş.
Açık kalanlar (öneri ve gerekçe; 26 Eki akşam kararlarıyla kapananlar aşağıda):
1. Yeni kapak alt metni (ZORUNLU: ZATEN tanıma alt metne dayanıyor). Öneri: "<A> and <B> personalized 1st anniversary zodiac print in the Botanical style, shown unframed on a green wall". Şu anki: "1st anniversary gift, personalized <A> and <B> paper anniversary print". Uzun tire yok; YASAK_ALT'tan geçer (eski78:221). "green wall" ifadesini Serdar görselden doğrular.
2. Eski kapak silinsin mi? Seçenekler: (a) sil: galeri 13, ilan başı en kötü 185 istek; (b) tut: galeri 14 (eski kapak son sıraya), en kötü 180 istek, galeride iki benzer kapak. Öneri: (a); yedek adım 5'te. Karar verilmeden yükleyici girdileri (adım 6) üretilmez.
3. Fiyat bilgisi (karar değil, bilgi): pilot 3.9-24.9, 77 ilan 3.9-29.0 (bizim veri: YD_OZET.csv). Bu işin kapsamı dışında; ayrı iş isteyip istemediğin.
4. TSV biçimi: öneri 4 sütun (cift, kart_no=1, design_id, url); mevcut okuyucu aynen kalır.
5. Canva'da 75 kopyanın kayda geçirilmesi (toplu onay); üretim 63/75 (17:21 UTC).
6. Pilot ilan 4595350971 CANCER_LIBRA (ajan kopyası DAHZIAyOYA8). Öneri: evet (yapısı tam okunmuş tek ilan).
7. Sıra geçişi her ilanda (en kötü 94 istek): öneri evet, kanıtlı yol.

## Riskler
- Yükleyici genelleştirmesi poster v10'a bağlı; v10'da çıkan hata YD'yi bekletir. Karşılık: profil testleri ayrı.
- 75 tasarım ajanlarca paralel üretildi (CLAUDE.md "HIZ VE KALITE" madde 1 paralel ajanı yasaklıyor). Karşılık: metin kapısı (adım 1) + ölçümlü QC (adım 4) + Serdar kontak bakışı.
- B1/B2 eksik (63/75, 17:21 UTC): üretim tamamlanmadan adım 1 başlamaz.
- Canva link ömrü 65-115 dk; kilit beklemesi linki öldürebilir. Karşılık: ayrı kilit grubu, satır başı kalan süre kontrolü, aynı imza DUR.
- NCC eşikleri henüz ölçülmedi; örneklerde ölçülmeden sabitlenmez.
- Envanter 13:06 / pilot 13:13 UTC'de okundu; arada değişen ilan kuru koşuda BLOK olur.
- Eski ve yeni kapak aynı boyutta: yanlış ZATEN riski; karşılık alt metin + DEVAM kaydı + yedek id kümesi.
- Geçişte ilan başına birkaç dakika eski/yeni kapak birlikte görünür (tahmin).
- Video eski kapaktan üretildiyse eski kapağı gösterir; video ayrı iş (Serdar 26 Eki).

## Serdar kararları (26 Eki akşam, "Tamam")
- Eski kapak yedeklenip silinir (galeri 13).
- Kapak sahnesi onaylı haliyle kalır.
- Pilot: 4595350971 CANCER_LIBRA (ajan kopyası DAHZIAyOYA8).
- Kapak alt metni: "<A> and <B> 1st anniversary zodiac print, paper anniversary gift" (Etsy Help: alt metin erişilebilirlik + Etsy dışı arama; Etsy içi sıralama etkisi belirtilmemiş).
- Teknik: 4 sütunlu TSV, her ilanda sıra geçişi.
- 1st Anniversary galerisi, onaylı poster galerisiyle aynı mantık ve tarzda kurulur (Serdar 26 Eki): kapak, sembol, kişiselleştirme, format (Digital File or Print + boylar), süreç, 5 stil kartı kapak sahnesinde. Görsellerin arkasında beyaz şerit yok.
