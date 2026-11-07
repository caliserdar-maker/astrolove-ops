# astrolove-ops — calisma kurallari

Bu depo AstroLoveArt Etsy magazasinin (shop 39729443) otomasyon deposudur.
Oturum gunlugu ve baglayici kararlar Drive'daki START_HERE dokumanindadir
(00_START_HERE__ASTROLOVE_FILE_SYSTEM); yeni bir ise o dokumanin ilgili
bolumu okunmadan baslanmaz.

## Git

- Bu depoda dogrudan `main`'e push serbesttir; PR gerekmez (1 Eyl 2026 karari).
- `workflow_dispatch` yalniz `main`'deki workflow'lar icin calisir; yeni bir
  workflow tetiklenecekse once `main`'e alinir.

## Etsy

- Salt okur isler (listing okuma, dogrulama, SEO taramasi) onaysiz kosulur.
- ETSY TOPLU YAZIM (Serdar 3 Kas Soru 14 A; state, medya/ZIP/video yukleme/silme, yayin, fiyat/etiket/aciklama dahil tum yazimlar):
  1) Yedek (Drive, salt okuma) + kuru kosu (salt okuma) + tek bagimsiz inceleme -> Serdar PLAN onayi.
  2) Pilot: tek ilan yazilir; Serdar canli sayfada bakar -> PILOT onayi (29 Eki dersi: pilot gorulmeden 18 ilana CI kapak yazildi).
  3) Kalanlar partiler halinde; partiler ARASI ONAY YOK. Her ilan geri okuma + canli sayfa dogrulamasi; FAIL, son okuma farki ya da
     karar degisikliginde DUR + kisa rapor. Kota bitince is bolunur, mevcut kotayla kaldigi yerden devam (ilan yarim birakilmaz).
  4) Her partide tek satir rapor; sonda toplu rapor -> Merkez kontrol.
  Degismeyenler: tek Etsy yazimi + kilit_bekle.py; kota tabani 10 + "tahmini istek + 10"; salt okuma onaysiz.
- ETSY OKUMA YOLU OLCUMU (Merkez dersi, Serdar 7 Kas onayi): Etsy'ye yazan kodun kullandigi her okuma uc noktasi ve hedef deger
  listesi (ulke kodu, enum) kod ve sahte Etsy yazilmadan once salt okuma kosusuyla gercek Etsy'de olculur (salt okuma, onaysiz;
  Etsy bolumu 1. madde); sahte Etsy bu olcumden kurulur. Bilinen (7 Kas, tek olcum): shipping profile destinations ucu kesik
  doner (limit=100 -> 1, parametresiz 25; teshis 42359284764); profil GET ve magaza profil listesi 125/125 ayni; 25'in kati
  kesik okuma DUR verir; Etsy ulke listesinde CI ve XK yok.
- Token sahibi: Drive `ASTROLOVE/TEMP/ETSY_TOKEN.json` tek kaynaktir; yenilenen
  refresh token her kosuda geri yazilir (bkz. docs/SECRETS.md). Ayni anda tek
  Etsy kosusu: `scripts/etsy/kilit_bekle.py` (28 Eyl 2026, Serdar onayi; GitHub
  `concurrency: etsy-token` KULLANILMAZ, bekleyen kosuyu iptal ediyordu). Yeni Etsy
  workflow'u: `permissions: actions: read` + token indirmeden ve ilk Etsy isteginden hemen
  ONCE `GH_TOKEN: ${{ github.token }}` ile `python3 scripts/etsy/kilit_bekle.py` adimi (Serdar 7 Kas: checkout, kurulum ve
  Etsy disi girdi indirme kilitten once olabilir; token ile Etsy kosularinin yazdigi Drive durumu (DURUM, plan) kilitten SONRA
  indirilir; sira dogrulugu degismez, kilit_bekle.py kendinden once olusan tum aktif kume kosularini bekler).
  Zamanlanmis router mesgulse turu atlar (`--mod atla`).
  KILIT SURESI (Serdar 23 Eki): Etsy kilidini tutan kosuda uzun Etsy disi is (OCR, goruntu isleme, toplu indirme) yapilmaz;
  Etsy okumasi biter bitmez kosu biter (ham veri Drive'a), isleme kilitsiz ayri is akisinda yapilir (kagit-tara 39947456694
  OCR boyunca kilidi 90+ dk tuttu, pilot kuru plani bekletti).
  ISTISNA (Serdar 31 Eki, karar 6b): yd-kapak-yukle.yml (1st Anniversary galeri yukleyicisi) kilidi is akisinin EN BASINDA alir; girdi
  indirme (en fazla 15 dk) kilit altindadir. Gerekce (bagimsiz inceleme 30 Eki): canli okuma ile yazim arasinda baska Etsy kosusu
  araya girmesin. Sure butcesi kilit anindan sayilir (KILIT_T0; azami_dk <= 75) ve YD kapak adimi 95 dk ile sert sinirlidir; kilit
  tutma ~120 dk altinda kalir. Bu yalniz TEK bekleyen kosu icin gecerlidir: kuyrukta arka arkaya bekleyen kosularin beklemesi
  toplanir (kilit_bekle.py onceki her aktif kosuyu bekler). Baska is akisina genellenmez.
- KURAL (tum oturumlar): Etsy kosusunu istedigin an baslat; kilit sirayi kendisi tutar,
  hicbir kosu iptal edilmez (bekleme en fazla 120 dk, asilirsa is yapmadan FAIL).
- Hicbir sir loga yazilmaz; token degerleri `::add-mask::` ile maskelenir.
- KOTA SINIRI: "Etsy kota sınırı 10 (Serdar 15 ve 24 Eki). Serdar açıkça söylemeden değiştirilmez; yeni eşik önerilmez."
  Tek deger: kosu/ilan baslangic esigi ve her istekten once sert taban = 10, tum roller (genel, pod-audit, siparis, router)
  ve tum betik/is akisi varsayilanlari (`--quota-min` vb.). Kaynak `etsy_common.KOTA_SINIRI`. 23 Eki esikleri (genel 481/430,
  pod-audit 2068, router 400, siparis 415, ihtiyac kapisi 430) ve config/etsy_kota_esik.json KALDIRILDI (24 Eki).
  Toplu isler ilan basina `api.kota_kapisi(...)` cagirmali (su an yalniz beyan_marka_yaz toplu).
- **updateListing bir TASLAGI otomatik yayina alir** (7 Eyl 2026 olcumu: gece
  aciklama guncellemesi 72 taslagi `active` yapti; `state_timestamp` = PATCH ani).
  Toplu guncellemede "ilan taslak kalir" varsayimi YAPILMAZ: yazmadan once state
  okunur, taslak kalmasi gerekiyorsa o ilan guncellenmez ve Mo'ya sorulur.

## MUSTERIYE DOKUNAN HER EYLEM (26 Eyl 2026, Serdar kesin talimati)

- Musteriye bildirim/mesaj/e-posta dogurabilecek HICBIR eylem Serdar'in o eyleme ozel acik onayi olmadan yapilmaz.
  Kapsam: Etsy mesaji, createReceiptShipment / takip yazma veya duzeltme (Etsy aliciya bildirim gonderebilir),
  siparis durumu degistirme, iade/iptal, yorum yaniti, dijital dosya teslimi, Prodigi'ye siparis gonderimi.
- "Koordinator onayi" / pano "CLAUDE ONAYI" bu eylemler icin GECERSIZDIR. Yalniz Serdar onaylar.
- Musteri mesajlari yalniz TASLAK olarak Drive'a yazilir; gonderimi Serdar yapar ya da ayri acik onay verir.

## Urun metni (25 Eyl 2026 karari; 24 Eyl B-5'i gunceller; KAGIT: Serdar 23 Eki)

- KAGIT (Serdar 23 Eki): baski Hahnemuhle DEGIL. Kagit turu 13 Eki'de kriter olmaktan cikti; canli EN ve materials
  "matte art paper". Hahnemuhle / Photo Rag / 308 g/m2 / giclee / Prodigi / %100 cotton / museum (ISO 9706) ifadeleri
  HICBIR dilde yazilmaz; RU ve diger ceviriler EN ile birebir ayni bilgiyi verir. (25 Eyl Hahnemuhle izni KALDIRILDI.)
- PREMIUM (Serdar 3 Kas A): "premium" ve "long-lasting"/"long lasting" (RU: премиал/премиум, стойк, долговеч) musteriye gorunen hicbir metin/gorselde kullanilmaz; kagit icin yalniz "matte art paper" (15 Eki genel ifade izninin yerine).
  23 Eki "Izinli: premium matte art paper, long-lasting inks" satiri KALDIRILDI (29b72a67; Serdar 3 Kas Soru 3 A): bu ifadeler izinli DEGIL.
- BAGLAM IZINLERI (Serdar 3 Kas, kuru kosu cevaplari 2 ve 5; `etsy_common.METIN_IZIN`): "300 dpi" yalniz poster78 aciklamasinda
  (dijital dosya satiri + SSS, EN + RU) izinli, galeri kartlarinda yasak surer. "free preview" yd78 aciklama + alt metninde KALIR
  (surec karti); poster78 aciklamasinda yok (Soru 11: "We send a preview ...").
- RU YAZIM KAPISI (Serdar 23 Eki madde 4): her RU ceviri yazimi `etsy_common.ru_yazim_kapisi`'ndan gecer; yasak ifade
  (RU_YASAK) varsa istek gonderilmez. 78 poster ilaninda (data/pod/pod78_ids.csv) RU aciklama yalniz `ru_poster.kur` + kontrol
  PASS + `ru_poster.izin_ver` ile yazilir. metin_78, yayilim_78 yaz/metin2 ve pod_ru_tags --apply KAPALI (eski poster metni).
- Yasak: OBA-free, bright white, omur yili (orn. 100-200 years), "12-colour".
  Ingilizce metinde uzun/orta tire yok.
- Tek kaynak (Serdar 3 Kas A): `etsy_common.METIN_KESIN` + `METIN_BAGLAM`; `metin_yasak_kapisi` Etsy._call ve post_file icinde tum istek
  degerlerini (EN + RU) tarar. 3 Kas: UYARI modu (eslesme raporlanir, yazim durmaz); ENGEL moduna gecis canli metinler temizlendikten
  sonra ayri Serdar onayiyla. `scripts/medya_v1/uretim/metin_kurali.py` (medya-v1) EMEKLI, kullanilmaz.

## Uretim

- GALERI (Serdar 23 Eki): 78 poster galerisi `galeri77_cift.sh` / `kart02_duvar_kur.py` ile YENIDEN URETILMEZ (uc sutun,
  Framed ve Hahnemuhle metni; canli kartlar 17 Eki `eski78_gorsel_uret.py` + `kart02_iki_sutun.py` hattindan). Kart degisikligi
  canli galeriden (`eski78_gorsel_indir.py`) bant duzenlemesiyle yapilir; bant disi fark kapisi zorunlu (eski78_gorsel_uret.py
  esigi: kutu disi p99.9 <= 12 ve max <= 45, JPEG yeniden kodlama gurultusu; yeni esik ancak olcumle ve Serdar onayiyla).

- PILLOW (Serdar 24 Eki, duzeltme): yerel test ve uretim, test edilen is akisinin kurdugu Pillow surumuyle kosar (is akislari
  farkli surum kurar: 11.0.0, 12.3.0, 11.3.0, surumsuz; is akisi surumleri bu kurala dayanilarak DEGISTIRILMEZ). 12.x glif
  yerlesimini degistirir (pilot kart 04 farki 87 > esik 45). Galeri/kart betikleri (kart_nokta_marka / eski78_gorsel_uret /
  kart02_iki_sutun; is akislari 11.0.0) baska surumde DUR verir. Ornek venv: `python3 -m venv v && v/bin/pip install pillow==<surum>`.
- Wallpaper hatti dahil tum uretim GitHub Actions'ta kosar; ChatGPT/Colab
  uretim hattinda yoktur (KARAR 3, 1 Eyl 2026).
- Esik ve yerlesim kurallari tahminle degil, onayli dosyalardan olculerek
  turetilir (docs/WP_LAYOUT_SPEC.md bu yontemle yazilir).

## HIZ VE KALITE KURALLARI (2 Eyl 2026 karari)

1. Alt ajan (Serdar 26 Eki + 3 Kas A): yalniz dosya/gorsel/video URETIMI paralel alt ajanlara bolunebilir; ajan sayisi her
   gorev metninde yazilir. Etsy (ve Metricool) yazimi ajanla yapilmaz: sirayla, kilit_bekle.py ile. Toplu uretimden once
   gercek oranda ornek + Serdar onayi; paralel uretilen gorseller bagimsiz goz kontrolu bitmeden disa aktarilmaz/yayina gitmez.
   "En fazla 2 deneme" TOPLAMDIR, ajan sayisiyla cogalmaz; "Actions en fazla 1 kez" ve "yontem degisecekse DUR, sor" aynen.
   Yasak kalir: arastirma icin ajan surusu, cok ajanli inceleme is akisi, Extra/ultracode. Inceleme: tek bagimsiz inceleme
   ajani (asagida "Capraz inceleme"). Ortak kaynak: kilit, kota ve ayni dosyaya iki ajan yazmaz.
2. Iterasyon YERELDE: kucuk ornek (6 poster / 1 cift) ile 60 sn altinda
   test. Actions yalniz yerelde temiz cikan surum icin, en fazla 1 kez.
   TEMIZ KOPYA VE KABUK TESTI (Merkez dersi, Serdar 7 Kas onayi; 5-6 Kas): Actions'a gidecek kod yerelde commit'in temiz
   kopyasindan (git archive ya da yeni klon) test edilir; `git check-ignore` ile commit'e girmeyen dosya taranir (6 Kas galeri78
   kosu 42282343035: fonts/ .gitignore). Is akisi (yml) kabuk adimlari push oncesi yerelde sahte aracla ve is akisinin kullandigi
   kabukla kosulur (varsayilan `bash -e`; `shell: bash` adimi `-eo pipefail`); yeniden deneme / cikis kodu toplayan adimda
   `set +e` ya da `|| RC=1` (5 Kas ornament 78 toplama). Sahte aracin taklit ettigi cikti gercek aracin bilinen davranisiyla
   (resmi belge ya da onceki salt okuma kosusunun logu) karsilastirilir; liste
   ciktisini ayristiran kapi beklenmeyen ciktida DUR verir (6 Kas ornament-taslak pilot 42290409207: rclone lsf klasorleri de listeledi).
3. Her gorev basinda 3 satir yaz: (a) yontem, (b) "bitti" tanimi (olculur
   esik), (c) tahmini sure. Yontem degisecekse DUR, Mo'ya sor.
4. En fazla 2 iterasyon. Ikincisi de temiz degilse DUR, durumu raporla,
   devam etme.
5. Uzun her kosuda ETA sayaci (islenen/toplam, gecen, kalan, yuzde).
6. Rapor: en fazla 6 satir + dosya yollari. Aciklama yok.
7. QC: tek script, olculebilir esik, PASS/FAIL. "Gozle bakiyorum" dongusu yok.

## SIPARIS ISI KESINTISIZ (1 Eki 2026, Serdar kesin talimati)

- Musteri siparisi dosyalari (dijital ve baski) TUM kapilar PASS olana kadar is ARALIKSIZ surer. Tek dakika bekleme yok.
- Kosu biter bitmez sonuc okunur, ayni dakikada sonraki duzeltme veya kosu baslar. Onay, kuyruk, "raporlayip bekle" yok.
- Bu islerde HIZ VE KALITE madde 4 ("2 iterasyondan sonra DUR") GECERSIZDIR: FAIL'de durulmaz; 6 satir durum yazilir ve calismaya devam edilir.
- Musteriye teslim, Etsy mesaji ve yukleme yine yalniz Serdar'in acik onayiyla.

## ZAMANLAYICI YASAK (1 Eki 2026, Serdar kesin talimati)

- Hicbir oturum, hicbir koşuda "X dk sonra bakarim" zamanlayicisi KURMAZ (send_later, ScheduleWakeup, cron ile bekleme, sleep ile uzun bekleme dahil).
- Baslatilan her koşu ARALIKSIZ izlenir: GitHub API ile jobs her 30-60 sn okunur (tek komut icinde dongu), bir is biter bitmez sonucu okunur.
- FAIL olan is icin koşunun tamamini bekleme: ayni dakikada rapor oku, duzelt, yerelde dogrula, o is icin yeni koşu baslat.
- Kosu bitince ayni dakikada 6 satir rapor. Bekleme gereken tek durum: Serdar'in acik onayi gereken eylem (Etsy yazma, musteriye dokunan eylem).

## MARKA ADI (1 Eki 2026, Serdar kesin talimati)

- Marka adi **AstroLoveArt**. Musterinin gorebilecegi her seyde (PDF/dosya/klasor adi, mesaj, metin) yalniz "AstroLove" YAZILMAZ.
- Siparis dosyalari: AstroLoveArt_<Burc1>_<Burc2>_<Renk>.pdf (orn. AstroLoveArt_Cancer_Leo_Deep_Black.pdf).

## SIPARIS URETIMI: OGRENILENLER (1 Eki 2026, EMILY + Test 1 + Test 2; ayrinti docs/SIPARIS_DERSLER.md)

Hedef: Serdar isim + burc yeri + tagline verir, 15 dk icinde 5 PDF Drive'da (Test 2: 11 dk 19 sn, PASS).

- CIFT ANAHTARI ALFABETIK: CAPRICORN_SAGITTARIUS (SAGITTARIUS_CAPRICORN degil). isim1 = cift adindaki ILK burc
  (posterde sol), isim2 = ikinci burc (sag). Ters sira kaynak bulamaz, tum isler ~1 dk'da FAIL (Test 2).
- DISPATCH (siparis-dijital): Content-Type: application/json; mesaj girdisi `mesaj_b64` (UTF-8 base64);
  `renk_ref` HER ZAMAN acikca verilir; siparis girisi (siparis-giris) bunu kendisi verir (asagidakiler is akisi VARSAYILANI;
  repo degiskeni tanimliysa o gecerli: SIPARIS_GPT_REF tanimsiz (22 Eki kosu 39850280226), ESKI_RENK_REF / SIPARIS_WP_REF
  dogrulanmadi). ESKI_RENK_REF = b8c8c4b
  (siparis-baski-v1 dal basindaki DB ton esitleme commit'leri DAHIL DEGIL), yalniz CI ve anahtar kapaliyken MB/DB/PW.
  Anahtar acikken (SIPARIS_GPT_ACIK, varsayilan 1) MB/DB/PW yeni yol: siparis-gpt GPT_REF 243c9a4. WP: 360cbef (giris WP'de de
  renk_ref verir, siparis-giris.yml:97). kaynak-olcum
  varsayilani b8c8c4b. siparis-dijital renk_ref varsayilani 8a8b370 ESKI ve girisce kullanilmaz (Serdar 22 Eki A2/A2-not;
  degistirilmedi). Temiz dallara gecis (P0.7) yalniz kupada (0196e37a, A3 kiyasi PASS); poster A3 kiyasi FAIL. wp_pod_kod v1;
  receipt yalniz rakam (test: 900000000N, N >= 1).
- Siparis kosusu sirasinda prova / tani / toplu kosu ACILMAZ: runner kuyrugu siparis islerini geciktirir
  (Test 2: CI 2 dk gec basladi).
- "Dosyalar hazir" = 5 PDF Drive'da (createdTime), job bitisi degil. Teslim oncesi 1:1 / onizleme ile
  isim-burc eslesmesi ve tagline gozle kontrol edilir.
- FAIL olan tek sayfa icin tum siparis yeniden kosulmaz: `isler=` + `onceki_kosu=` ile yalniz o is.
- FAIL nedeni Drive SIPARIS_ISIM/DIJITAL/<receipt>/OZET.json (kapilar, kalan) ve KAPI_RAPORU_<RENK>.json'dan okunur
  (job loglari proxy'de kapali; annotations yalniz "exit code 1" verir).
- Olcek (yazi yerlesim) kapisi FAIL'i isme bagliydi ve olcum hatasiydi (bfaed5d: esit bant olcumu, MB 2400 referansi
  plaka_ss, dikey merkez). Tek sayfaya yama yapilmaz; kok neden + isim on testi (EMILY, SERDAR, MAXI, ANNE,
  uzun/aksanli isimler orn. MAXIMILIAN, CAGLAYANGUL) ile dogrulanir.
- MB sayfalari paralel (5 is) kosar: 33 dk -> 6 dk. WP duz renk yalniz CHAMPAGNE_IVORY, JPEG 95 (5cf010a).
- Bilinen darbogaz kapatilmadan test/siparis baslatilmaz; once olc, sonra kos.

- TUM DERSLER (47 madde; 37-47 fiziksel siparis + tedarikci) ve TEST BASLANGIC KAPISI: docs/SIPARIS_DERSLER.md. Her test/siparis oncesi kapi madde madde
  isaretlenip Serdar'a gosterilir; bir madde HAYIR ise dispatch yok.

### Test 3 dersleri (1 Eki 19:14, ARIES_VIRGO; 4 renk ~8 dk PASS, MB 2 sayfa FAIL)

- KAYNAK ON TESTI ZORUNLU: yalniz 3 cift denenmisti; ARIES_VIRGO MB 2:3 kaynaginda tagline bandi olculemedi
  (KeyError 'tag_bant'). Gercek siparis kabulunden ONCE kaynak-olcum workflow'u (tum ciftler x renkler x boylar)
  PASS olmali; kaynak dosya degisince yeniden kosulur. Sonuc: inceleme/kaynak-olcum dali.
- ACIK IS KAPISI: docs/SIPARIS_DERSLER.md "Acik isler" listesinde siparis boyunu etkileyen madde varken test/siparis
  baslatilmaz (Test 1 ve Test 3'te iki kez cignendi: MB yavasligi, MB 11x14).
- Test, birkac dakika once main'e giren DOGRULANMAMIS kodla baslatilmaz (Test 3, 4fb7a35 ile 1 dk sonra kostu).
- Ayni koda ayni anda tek oturum dokunur: duzeltmeyi kim yapiyorsa o; koordinator o sirada kod degistirmez.
- Koordinator sessiz kalmaz: hata ayiklarken de en gec 2 dk'da bir Serdar'a tek satir durum.
- Test sonucu maskelenmez (Serdar 1 Eki + 4 Kas): test komutu TEK BASINA kosar, cikis kodu AYRI kontrol edilir; boru (`| tail`,
  `| grep`), `|| true` ya da `&&` zinciri sonucu gizlemez (boru gerekiyorsa `set -o pipefail`). FAIL varken commit, push ve kosu YOK
  (1 Eki: `--is` hatasi main'e gitti; 4 Kas: poster kuru betiginde test 13/14 FAIL iken grep cikisi zinciri surdurdu, commit + kosu gitti).
- Baska oturumun izledigi kosu iptal edilmeden once o oturuma/Serdar'a yeni kosu no bildirilir.
- Uzun bloklayan izleme dongusu yok: en fazla ~2 dk bekle, sonra Serdar'a durum yaz (Serdar iki kez durdurdu).
- Yeni test/arac ilk surumde hizli tasarlanir: yalniz gereken boylar, paralel indirme/olcum.
- Teshis icin OZET sayfa kaydinda `iz` (traceback) ve `olcek` (olcek kapisi ayrintisi) alanlari var (030f767, 1fa8f68);
  job loglari okunamadiginda once bunlara bakilir.

## Çapraz inceleme ve bağlam (Serdar, 21 Eki 2026)
- Etsy'ye veya Metricool'a toplu yazmadan önce ve sonuç raporu vermeden önce TEK bir bağımsız inceleme ajanı çalıştırılır. Görevi: "Bu planın/raporun neden yanlış olduğunu kanıtla; kapıların atladığı hataları, yanlış varsayımları ve kaynaksız iddiaları bul." Bulgular düzeltilmeden rapor verilmez. Bunun dışında alt ajan yalnız dosya/görsel/video ÜRETİMİ için kullanılır (HIZ VE KALITE madde 1; Serdar 26 Eki + 3 Kas A): Etsy/Metricool yazımı ajanla yapılmaz, araştırma ajan sürüsü ve çok ajanlı inceleme yasak.
- KALİTE KURALLARI (Serdar 4 Kas, "onaylıyorum"; 4 Kas olayları):
  1. Etsy'ye yazan yeni ya da değişen kod (kapı dahil), yazım koşusundan ÖNCE işi yapmamış tek ajana bağımsız incelemeye verilir
     ("bunun neden yanlış olduğunu kanıtla"); bulgular düzeltilmeden koşu yok. İncelemeden sonra yazım yolu yeniden değişirse
     değişen kısım da incelenir. (4 Kas: YD talimat kapı kodu incelenmeden main'e alındı, 2 dk sonra 77 ilan yazıldı.)
  2. Testlerin çıkış kodu: "Test 3 dersleri" bölümündeki "Test sonucu maskelenmez" maddesi (tek başına koşum, ayrı çıkış kodu, pipefail, FAIL'de commit/koşu yok).
  3. Her kapı ve test bilinen PASS + bilinen FAIL örneğiyle denenir. Yalnız kendi kurduğu veriyi doğrulayan (FAIL veremeyen) test
     kanıt sayılmaz; raporda "zayıf test" diye yazılır. (4 Kas: YD c testi kendi sahte verisini doğruluyordu.)
  4. KAPI GEVŞETME YASAĞI (Serdar 1 Kas "b" + 4 Kas): kapı tanımı gevşetilmez, yalnız sıkılaştırılır. Ölçüm bölgesini daraltan,
     payı büyüten, eşiği gevşeten değişiklik gevşetmedir; Serdar onayı olmadan yapılmaz. Ölçüm ile üretim aynı parametreyle çalışır;
     farklıysa raporda yazılır. (4 Kas: ornament Kova kapısının ölçüm payı 24 -> 66 px büyütüldü, üretim 24 px'te kaldı: kör bant.)
     Sıkılaştırma da önce tipik ve en kötü veriyle ölçülür; "temkinli" diye ölçülmeden kapı konmaz, onaylı planın tanımını
     değiştiren sıkılaştırma Serdar'a sorulur (Merkez dersi, Serdar 7 Kas onayı; 6 Kas gece: ornament sipariş hattında
     tarih_alt_795 ve 32 px eşitliği ölçülmeden konmuştu, siparişlerin çoğunu düşürecekti).
- Raporlardaki her rakamın kaynağı yazılır (ölçüm / API / dosya / tahmin). Kaynaksız rakam yok.
- Görev metinlerinde rol verme yok; oturum, işe başlamadan ilgili karar dosyalarını ve önceki sonuçları okur.
- İş sırasında görevin dışında bir hata, risk ya da fırsat görülürse (ör. sipariş hattında kapı FAIL'i), kanıtıyla rapora eklenir; kendiliğinden düzeltilmez.
