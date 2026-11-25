# Dijital araştırma: terim taraması + derin toplayıcı düzeltmesi (plan ve uygulama kaydı)

Dayanak: Serdar 26 Kas "Evet derhal başla" (Drive KARARLAR_20261126_1 ve _2), Merkez analizi RAPOR_ELESTIREL_ANALIZ_URUN_BULMA_20261126.
Kapsam: kod + test + PR. Bu işte Etsy'ye istek ve Actions koşusu YOK. Satır numaraları bu dosyayı içeren commit'e göredir.

Sapma: plan, görev metnindeki sırayla (önce plan, sonra kod) ayrı bir dosya olarak yazılmadı. Kodla aynı oturumda hazırlandı ve
bağımsız incelemeden (2 tur) sonra bu dosyaya geçirildi.

## Mevcut yapı (okunan yollar)

- İstemci: `etsy_common.Etsy._call` (scripts/etsy/etsy_common.py:852). Sert taban `_istek_oncesi` (:721), `KOTA_SINIRI = 10` (:169).
  Salt okuma sarmalayıcısı `SaltOkur` (scripts/etsy/dijital_arastirma.py:100): GET dışında bir istek gelirse SystemExit.
- Kota / süre / yol verme kapısı: `Okuyucu` (dijital_arastirma.py:149). 429 ve "DUR: kota" durumlarında KotaDur verir.
- Drive: iş akışı rclone ile `gdrive:ASTROLOVE/DIJITAL_ARASTIRMA_20261125` klasörünü kullanır. Klasör kimliği kodda yok; yetki gizli
  değişken `RCLONE_CONF_B64` ile gelir.
- Kilit: `python3 scripts/etsy/kilit_bekle.py`. Drive durumu kilit alındıktan sonra indirilir (terim-tarama.yml:85,
  dijital-arastirma.yml:77).

## C) Terim taraması (YENİ): scripts/etsy/terim_tarama.py, .github/workflows/terim-tarama.yml

- Tetik yalnız `workflow_dispatch` (terim-tarama.yml:11). schedule ve zincir yok.
- Girdi: config/dijital_terimler.txt (153 terim), `yalniz` (`;` ile ayrılmış), `yeniden`, `dk`, `kota_alt`.
- Terim başına en çok 6 mantıksal çağrı (`TERIM_ISTEK_AZAMI`, terim_tarama.py:44; bütçe kontrolü `terim_tara` içinde, :197):
  1. score sırasıyla 1. sayfa (100 ilan).
  2. İndirilebilir ilan sayısı 30'dan azsa ve sayfa doluysa en çok 2 sayfa daha.
  3. `/listings/batch` (includes=Shop, 100'lük). Okunmamış ya da 7 günden eski okunmuş mağaza başına tek temsilci ilan gönderilir
     (`taze_magaza`, :174).
  Sayfalar arası tekilleştirme: `tekil_ekle` (:187).
- 5xx / kısa 429 yeniden denemeleri gerçek istek sayısını 6'nın üstüne çıkarabilir. Bunlar `istek` sütununda ve sayaçta ayrıca sayılır.
- Ölçütler `metrikler` (:104) içinde, indirilebilir ilan kümesi üzerinden hesaplanır:
  - `ilk100_*` sütunları yalnız 1. sayfadan gelir.
  - `az_veri`: indirilebilir ilan sayısı 10'dan az.
  - Fiyat: USD, USD dışı ve fiyatı yok ayrı sayılır.
  - Genç mağaza payının paydası, yaşı bilinen mağaza sayısıdır.
- Kota kapısı: koşu başında `/openapi-ping` (:301) ve her terimden önce `kota_kapisi` (:180, çağrı :305). Başlık yoksa DUR.
  Kalan, eşiğin altındaysa da DUR (çıkış 3). Sonraki koşu kaldığı terimden sürer.
- Okunamayan terim sona alınır; 2 koşuda okunamazsa 'hata' olarak kapanır (:314). Önceki 'tamam' ölçüm varsa korunur.
- Kayıt sırası (`kaydet`, :162): TERIM_ILAN, TERIM_MAGAZA, TERIM_TARAMA, terim_durum.json.
- Log: açık loga yalnız sayılar gider (KimlikSuz). Dosyaya yazılan log `sir_koru.py tee`'den geçer (terim-tarama.yml:111).
- Sonuç adımı yalnız çıkış 0, 3 ve 4'te yeşil (:142).

### CLAUDE.md ile çelişki (görev metni: "çelişirse CLAUDE.md geçerli")

Görev metni "kalan < 1.200 ise DUR" diyor. CLAUDE.md KOTA SINIRI kuralı ise şunu söylüyor: "tüm betik/iş akışı varsayılanları 10;
Serdar açıkça söylemeden değiştirilmez; yeni eşik önerilmez."

Uygulanan çözüm:
- Varsayılan eşik `KOTA_ALT = E.KOTA_SINIRI` (terim_tarama.py:40).
- 1.200 yalnız Serdar açıkça onaylarsa `kota_alt` girdisiyle verilir. Girdi 10-4000 arasında doğrulanır.

Önceden var olan çelişki: derin toplayıcıdaki %20 payı `KOTA_PAY` (dijital_arastirma.py:47) 25 Kas'tan beri main'de. Bu işte ona
dokunulmadı; rapora yazıldı.

## D) Derin toplayıcı: scripts/etsy/dijital_arastirma.py, .github/workflows/dijital-arastirma.yml

- Taksonomi ağacı kaldırıldı. Girdi 1-8 terimdir (`secim_coz`, :124), config/dijital_terimler.txt içinden.
- Durum terim kümesine bağlıdır (:633). Drive'da `DERIN_<etiket>` alt klasörü kullanılır; 25 Kas kök verisine dokunulmaz.
- Örnek aşaması (`asama_ornek`, :324; `grup_topla`, :293):
  - relevans = score sırası; yeni = created sırası, yalnız `original_creation_timestamp` son 365 gün içindeyse (`yeni_mi`, :287).
  - İlan kimliğiyle tekil kayıt (ILANLAR.csv) tutulur; terim ve grup bağları ILAN_TERIM.csv'dedir (`terim_ilanlari`, :245).
  - Okuma hatası boş sayfa sayılmaz: grup bitti sayılmaz, relevans okunmadan yeni grubu seçilmez, 2 koşuda kapanır.
  - Okunamayan mağaza için boş satır yazılmaz (`magaza_topla`, :366).
- Yorum aşaması (`asama_yorum`, :435; `sayfa_al`, :413):
  - Yorum önbelleğinin anahtarı yalnız ilan kimliğidir.
  - Her ilanın ilk sayfası okunur; hata verirse aynı koşuda bir kez daha denenir.
  - Her terimde en çok yorumlu 5 ilanın kalan sayfaları okunur (ilan başına en çok 10 sayfa; aşılırsa 'kesik').
  - 50+50 hedefi kaldırıldı.
- Özet aşaması (`asama_ozet`, :514):
  - `son_12ay_yorum_sayisi` (:564) sıralamada kullanılmaz. Tamlığı `son12_tam` (:504) belirler.
  - ilk10 payı ve "kanıtlı satış" sütunları kaldırıldı.
  - Fiyat yalnız USD; ilan yaşı `original_creation_timestamp`'ten.
  - Düşük yıldız (3 ve altı) yalnız sayılır, hedef yok.
- Durum dosyasında istek sayacı (`istek_toplam`), zaman damgası ve koşu kayıtları vardır (`calis`, :622; `kaydet`, :235).
- İş akışı: schedule, push tetiği ve zincir kaldırıldı; `actions: read`. Sonuç adımı yalnız 0, 3 ve 4'te yeşil
  (dijital-arastirma.yml:132).

## E) Testler (ağ kapalı, sahte Etsy, gerçek fonksiyon + mutasyon)

- scripts/etsy/test_terim_tarama.py
- scripts/etsy/test_dijital_arastirma.py
- scripts/etsy/test_dijital_is_akisi.py: iş akışı kabuk adımları sahte rclone ile ve gerçek sir_koru ile koşar.
- Her push'ta: ai-beyan-test.yml `dijital-arastirma-test` işi.

## Koşu başına tahmini istek (hesap, ölçüm değil)

- Terim taraması: 153 terim × en çok 6 + 1 ping = en çok 919 mantıksal çağrı. Yeniden denemeler buna eklenebilir.
- Derin toplayıcı (8 terim), üst sınırlar:
  - Örnek: 8 × 2 grup × 4 sayfa = 64. Mağaza: 240 ilan / 100 = 3.
  - Yorum: ilk sayfa en çok 240; tam okuma en çok 8 × 5 × 9 = 360.
  - Toplam en çok yaklaşık 670 + 1 ping. Ortak ilanlar ve az yorumlu ilanlar bu sayıyı düşürür.
