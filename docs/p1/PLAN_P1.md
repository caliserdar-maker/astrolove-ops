# PLAN P1: poster açıklamasından "yanıt yoksa basılır" sözünün çıkarılması (78 poster, EN + RU)

Dayanak: Serdar 4 Kas P1 "A" (cümle 78 poster ilanından çıkar; EN ve RU birlikte; başlık ve etiket değişmez; toplu yazım sırası).
Bu belge PLANDIR; Etsy'ye yazım yok. Yazım için gerekenler:
- Serdar plan onayı,
- Serdar + Lena RU onayı,
- yazıcı değişikliğinin KALİTE 1 incelemesi (ayrı görev).

## 1. Kaynak ve sayılar

- **Okuma:** koşu 41827729485 (main 7eb7bc37), Drive TEMP/P1_ENVANTER_20261104_1215/.
  - 78/78 ilan okundu; okunamayan, RU'su olmayan ve işlenmeyen ilan yok.
  - 237 istek (tahmin 237); kalan kota 2964 (4 Kas 12:17 UTC).
- **Kuru:** koşu 41833440548 (dal p1-poster-yanitsiz; Etsy isteği 0, kilitsiz, ağ engeli açık, ağ denemesi 0).
  - Drive TEMP/P1_KURU_20261104_1255/; dal docs/p1/P1_KURU_20261104_1255/ (FARK.csv, DUR.csv, ONCE_SONRA.json, DIGER_URUNLER.csv, OZET.json, LOG.txt).
- **Sonuç (78 içinde):**

  | Sınıf | İlan |
  |---|---|
  | PLAN | 78 |
  | DUR | 0 |
  | ZATEN_YENI | 0 |

  - kur(EN yeni) PASS 78.
  - kur(EN önce) = canlı RU: 78.
  - Yeni RU = canlı RU eksi silinen RU parçası: 78.
  - EN ve RU farkı tam 1 paragraf: 78.
  - Metin kapısı uyarısı 0; AI beyanı 78/78; state active 78.
- **Bağımsız yeniden hesap** (dal çıktısından, kuru kodundan bağımsız):
  - EN'den tam olarak silinen parça kalkmış: 78/78.
  - RU'dan tam olarak silinen parça kalkmış: 78/78.
  - onay_ozet yeniden hesaplandı: 78/78.
  - FARK ile ONCE_SONRA onay özeti aynı: 78/78.
  - Yasak ifade 0; EN'de uzun tire 0.
- **Diğer ürünler:** Okuma koşusu 246 aktif ilanı taradı (kaynak: Drive TEMP/P1_ENVANTER_20261104_1215/OZET.json "aktif" 246 ve AKTIF_SAYIM.csv; bu ikisi dalda yok).
  - Söz yalnız 78 posterde geçiyor; kupa ve 1. yıl dönümü ilanlarında 0. DIGER_URUNLER boş.
  - Kapsam sınırı: yalnız AKTİF ilanlar, yalnız EN açıklama, tek kalıp ("If we don't hear from you within 24 hours of receiving the preview"; p1_poster_oku.py SOZ). RU, taslak ilanlar ve farklı ifadeler taranmadı.

## 2. Değişen metin (birebir)

- **Silinen EN** (baştaki boşluk dahil):
  " If we don't hear from you within 24 hours of receiving the preview, we go ahead with the design as shown: we print your poster, or send your digital file as a download link in Etsy Messages."
- **Silinen RU** (baştaki boşluk dahil):
  " Если в течение 24 часов после получения макета мы не получим от вас ответа, мы продолжим работу с дизайном в том виде, в каком он показан на макете: напечатаем постер или отправим цифровой файл в виде ссылки для скачивания в сообщениях Etsy."
- **Yeni EN paragrafı:**
  YOUR PREVIEW
  We send you a preview via Etsy Messages within 24 hours of your order. We print your poster or prepare your file as soon as you approve it.
- **YENİ RU PARAGRAFI** (Serdar + Lena onayı için; kaynak scripts/etsy/p1_poster_kuru.py YENI_RU = ru_poster.SABIT yeni anahtarı):
  ВАШ МАКЕТ
  Мы отправляем вам макет через сообщения Etsy в течение 24 часов после заказа. Мы печатаем постер или готовим файл сразу после того, как вы одобрите макет.
- Başlık, etiket, malzeme, RU başlık ve RU etiket değişmez. Yedek ONCE_SONRA.json içinde (`yedek` alanı).

## 3. Pilot ve partiler

1. **Pilot:** 4570165628 (CAPRICORN_VIRGO), tek ilan. Sonra DUR. Serdar canlı sayfaya (EN + RU) bakar ve onay verir.
2. **Kalanlar:** 77 ilan, 4 parti (20 / 20 / 20 / 17), tek koşuda arka arkaya. Partiler arası onay yok; her parti sonunda tek satır rapor. 4 Kas poster yazımıyla aynı düzen.
3. **DUR koşulları** (koşu durur, sonraki ilan yazılmaz):
   - geri okuma farkı;
   - metin kapısı eşleşmesi;
   - state active değil;
   - canlı metin ne "önce" ne "sonra";
   - başlık, etiket, malzeme ya da RU başlık / etiket yedekten farklı;
   - onay özeti tutmuyor;
   - kota;
   - 4xx / 5xx yazım hatası;
   - RU yazım kapısı ya da AI beyan kapısı;
   - RU başarısız olduktan sonra EN geri yazımı da başarısız;
   - koşu zaman aşımı ya da iptal. Job 140 dk; kilit beklemesi 120 dk'ya kadar bunun içinde. Bugün DEGISIKLIK.csv yalnız döngü sonunda yazılıyor; iptalde EN yazılmış ama RU yazılmamış ilan kayıtsız kalır. Yazıcı değişikliğinde DEGISIKLIK.csv her ilandan sonra eklenir (bkz. §7).
   - 77 ilanın süresi ölçülmedi. 4 Kas poster yazımında 77 ilan ~3 dk sürdü (koşu 41734850615; kaynak o koşunun logu).

## 4. Kota (Etsy x-remaining-today)

- **Tipik:** ilan başına 7 istek (GET ilan, GET envanter, GET RU, PATCH, GET geri okuma, PUT RU, GET RU geri okuma). 78 × 7 = 546; 1 pilot + 77.
- **Yazıcı bütçesi:** ilan başına 20 (poster_metin_yaz.py:33). 78 × 20 = 1560. Bu bir üst sınır DEĞİL: 5xx yeniden gönderimleri bütçeye dahil değil; etsy_common her isteği 3 kez gönderebilir (:861).
- **Kalan kota:** 2964 (4 Kas 12:17 UTC, okuma koşusu sonu). Yazım günü koşudan önce yeniden okunur.
- **Eşik (yeni eşik önerilmez; CLAUDE.md KOTA SINIRI = 10):**
  - Mevcut yazıcının ilan başına kapısı kalan ≥ 20 + 10 ister (poster_metin_yaz.py:85, :120, :124, :163). Fiilen ilan başına 30 eşiği demektir.
  - Bu kapı 3-4 Kas poster yazımında Serdar onaylı bir sapma olarak kullanıldı (a93e8d80 sapmaları: "kota eşiği 20 + 10").
  - **SERDAR SORUSU:** P1 yazımında bu 20 + 10 kapısı yine kullanılsın mı, yoksa yalnız KOTA_SINIRI = 10 mu? Karar gelmeden yazıcı değişmez.

## 5. Yedek ve geri alma

- **Yedek:** ONCE_SONRA.json (her ilan için en_once, ru_once, ru_geri = kur(EN önce), yedek alanları). Drive kopyası `--immutable` ile yazıldı.
- **Geri alma:** aynı yazıcının `--geri-al` kipi. EN = en_once. RU = kur(EN önce) (= canlı RU, 78/78).
  - Eski SABIT anahtarı ("... we go ahead with the design as shown ...") ru_poster.py'de geri alma için duruyor; kur(EN önce) PASS (test_p1_poster_kuru).
  - `--geri-al` Serdar onayı olmadan çalışmaz. Yalnız RU başarısız olduğunda aynı ilanda EN'nin geri yazılması otomatiktir.

## 6. Geri okuma ölçütü

- Her ilanda yazımdan sonra okunan EN ve RU (norm: html.unescape + \r\n, kenar boşlukları) ONCE_SONRA "sonra" metniyle birebir aynı olmalı.
- onay_ozet(EN sonra, RU sonra) = FARK.csv onay_ozet.
- Başlık, etiket, malzeme, RU başlık ve RU etiket yedekle aynı olmalı.
- **Son okuma (salt okuma, yazımdan sonra):** her ilanda
  - canlı EN + RU (norm) = ONCE_SONRA "sonra" metni, tam metin birebir;
  - onay_ozet(canlı EN, canlı RU) = FARK onay_ozet;
  - başlık, etiket, malzeme, RU başlık ve RU etiket = ONCE_SONRA.yedek;
  - state active.
- p1_poster_kuru'nun ZATEN_YENI sınıfı (yalnız söz yokluğu + yeni paragraf + state) son okuma için YETERSİZ; son okuma yukarıdaki tam karşılaştırmayı kullanır. Yazıcının ZATEN_YENI yolu bugün tam metin eşitliği kontrol eder (poster_metin_yaz.py:129-134), ama başlık ve etiketi bu yolda yeniden kontrol etmez.
- **Kaynak sabitleme:** dal kopyası ONCE_SONRA.json sha256 56d86efaf7b32e7eec2ce7d1e44782eaac5d12cd3a36badf07e894af03843f9b; FARK.csv c622807dc40f84b2cdcc9788f43f36b4073fa73806f0cd7732d5fdef2af7f065. Yazıcı okuduğu dosyanın sha256'sını bununla karşılaştırır; farklıysa DUR. --immutable yalnız üzerine yazmayı engeller, dosyayı korumaz.

## 7. Yazıcı değişikliği (ayrı görev; KALİTE 1 incelemesi zorunlu)

- poster-metin-yaz.yml / poster_metin_yaz.py bugün 3 Kas planına bağlı. P1 için şunlar değişir:
  - **Kuru klasörü:** iş akışında sabit TEMP/POSTER_KURU_20261103_220036 (poster-metin-yaz.yml:74) → TEMP/P1_KURU_20261104_1255.
  - **Plan fonksiyonu:** yazıcı P.plan_ilan(lid, L, ru, inv, shop) → (k, hata) çağırıyor (poster_metin_yaz.py:152). p1_poster_kuru.plan_ilan(kayit) → (satir, detay); imza ve dönüş uyumsuz. Yazıcıya P1 için ince bir uyarlayıcı yazılır; canlı L/ru/inv'den kayit kurulur.
  - **Yedek:** yukle() YEDEK.json okuyor (poster_metin_yaz.py:207). P1'de yedek ONCE_SONRA.json içinde (yedek alanı); yukle() P1 için ONCE_SONRA.yedek'i okur.
  - **Onay girdisi ve kimlikler:** varsayılan ids 4570143815 (eski pilot); P1 onay öneki ayrılır, pilot 4570165628.
  - **4 parti:** yazıcıda "parti" kavramı yok (tek ids listesi). Parti raporu yazıcıya eklenir; "4 Kas ile aynı düzen" ifadesi bu eklemeyle anlam kazanır.
  - **DEGISIKLIK.csv:** her ilandan sonra eklenir (iptal ve zaman aşımı koruması).
  - **sha256:** girdi ONCE_SONRA.json ve FARK.csv sha256'sı §6'daki değerlerle karşılaştırılır.
  - **İş akışı main'de olmalı** (CLAUDE.md: workflow_dispatch yalnız main).
- **Birleştirme sırası:**
  - Yazımdan ÖNCE aynı commit ile main'e girer: ru_poster.py yeni SABIT anahtarı + p1_poster_kuru.py + P1 yazıcı değişikliği + testleri.
  - Gerekçe: yazıcı kuru planı canlıdan yeniden kurmak için p1_poster_kuru ve ru_poster'a bağımlı.
  - P1 sonrası beyan_marka_yaz --ru-yeniden, güncellenen ilanlarda kur için yeni anahtara ihtiyaç duyar.
  - poster_metin_yaz ve pod_5x7_yaz eski plana göre "bayat" ya da "kayma" ile kur'a gelmeden DUR verir (poster_metin_yaz.py:135-140). Bu güvenli, ama bu iki yazıcı P1'den sonra eski planlarla kullanılamaz.
  - Bu main'e alım ayrı Serdar onayıyla yapılır.
- **Bu görevde main'e alınmayanlar:** p1_poster_kuru, test_p1_*, p1-poster-kuru.yml, ru_poster SABIT anahtarı.

## 8. Açık konular ve riskler

- **Kota eşiği:** §4 Serdar sorusu.
- **Galeri kartlarıyla çelişki:**
  - Galeri kart metninde aynı söz var: "or as shown if there is no reply within 24 hours" (kart üreticileri scripts/pod/kart_nokta_marka.py, scripts/kapak78/wa_kupa_kart_ornek.py:81).
  - P1 açıklamadan çıkarır ama kartlar değişene kadar müşteri iki farklı bilgi görür.
  - Serdar kararı: P1 yazımı galeri işinden önce mi, birlikte mi (galeri 5 ayrı iş, sonra).
- **3-4 Kas yazımının son doğrulaması:**
  - Canlı EN'de "premium" 78/78 yok, yani 3-4 Kas yazımı tamam görünüyor.
  - poster_son_ozet (57291af5, poster-son-ozet dalı) 3 Kas FARK'ına karşı kontrol eder; P1'den sonra 78/78 FAIL verir. P1'den sonra bu kontrol yeniden koşulamaz (beklenen durum).
- **Şablonlarda söz duruyor:** data/pod/aciklama_v3_sablon.txt:14, pod_5x7_kuru.py:60-61, scripts/etsy/seo/pod_changes_v3.json. Bunlar eski/kapalı hat ama ileride yeniden üretimde söz geri gelir. Ayrı iş.
- **Yanıt gelmezse ne olacağı** P1 sonrası hiçbir müşteri metninde yazmıyor. Bu 3 Kas Soru 12'yle uyumlu: onay beklenir, 2 gün sonra hatırlatma, sonra Serdar kararı, ilana yeni söz yazılmaz. 7 iş günü üretim süresi onaya bağlı. İş riski; Serdar bilgisine.
- **RU çevirisinin EN değişince sıfırlanması:** düşük risk. Yazıcı RU başlık ve etiketi önce okur, PUT sonrası geri okur; RU hatasında ru_basarisiz yolu var.
- **main'deki p1-poster-oku.yml artifact adımı** kaldırılmalı (envanter içeriyor; koşu 41827729485'in artifact'ı silindi, 404). Ayrı görev.
