> **KARAR (Serdar, 26 Eyl 2026): ONAYLANDI.** Dijital ilan + made-to-order; dosya Serdar onayindan sonra
> Etsy Orders & Shipping sayfasindan siparise yuklenir (yalniz web surumu; tablette Chrome ile etsy.com).
> Claude dogrulamasi: Etsy duyurusu "We've improved our made-to-order digital listing experience"
> (https://community.etsy.com/forum/announcements-290/topic/weve-improved-our-made-to-order-digital-listing-experience-22506/):
> dosya siparis sonrasi yuklenir, siparis otomatik tamamlanmaz, aliciya e-posta gider, yalniz web.

# Kisisellestirilmis dijital urun: Etsy teslim modeli

**Kapsam:** 78 dijital duvar sanati ve 78 telefon duvar kagidi ilani.

**Karar tarihi:** 25 Eyl 2026.

**Bu belge bir canli-islem talimati degildir.** Etsy'ye yazma, ancak ilgili
isleme ozel acik onaydan sonra yapilir.

## Kisa sonuc

Etsy'nin bu ihtiyac icin yerel modeli **digital + made-to-order** ilandir.
Ilan acilirken teslim dosyasi yuklemek gerekmez; satici siparise ozel dosyayi
hazirlayip Orders & Shipping ekraninda siparisi tamamlar ve dosyayi o siparise
yukler. Alici dosyayi Etsy'nin Purchases/Downloads akisi icinden alir.
[Etsy Help: How to Manage Your Digital Listings](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings)

`physical` ilan acip yalniz dijital dosya/link teslim etmek onerilmez: urunun
ilan edilen turu ile gercek teslim sekli uyusmaz, fiziksel ilana kargo ve
teslim beklentisi yukler ve Etsy'nin dogru temsil kuralina gereksiz risk
ekler. Etsy'nin yaraticilik kurallari dijital indirmeyi ayri bir urun bicimi
olarak tanimlar; satici politikasi ilan ve uygulamalarin dogru temsilini
ister. [Etsy Creativity Standards](https://www.etsy.com/legal/creativity/)
[Etsy Seller Policy](https://www.etsy.com/legal/sellers/)

Open API v3'teki `uploadListingFile` bir **listing** dosyasi yukler; bir
receipt/transaction'a siparise ozel dosya ekleyen veya Etsy Messages ile
dosya/link gonderen bir public API islemi belgelenmemistir. Bu nedenle yerel
made-to-order tesliminin son adimi su an manuel Etsy panel adimidir.
[Open API v3: uploadListingFile](https://developers.etsy.com/documentation/reference/#operation/uploadListingFile)
[Open API v3 reference](https://developers.etsy.com/documentation/reference/)

## Resmi kaynaklardan bulgular

### A. Digital ilanda dosyasiz kisisellestirme ve sonradan teslim

- Etsy dijital ilanlari **instant download** ve **made-to-order download**
  olarak ikiye ayirir. Instant ilanda dosya ilan olusturulurken eklenir;
  made-to-order ilanda dosya siparis tamamlandiginda eklenir.
  [Dijital ilanlari yonetme yardimi](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings)
- Made-to-order seceneginde satici, tamamlanan dosyayi Orders & Shipping
  icindeki ilgili siparise yukleyip siparisi tamamlar. Bu, "ilan dosyasiz
  yayinlanabilir mi?" sorusuna **evet**, "dosya daha sonra yerel Etsy
  indirmesi olarak verilebilir mi?" sorusuna da **evet** yanitidir.
  [Ayni Etsy Help akisi](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings)
- Alici, tamamlamadan sonra dosyaya Etsy hesabi altindaki Purchases and
  Reviews/Download Files yoluyla erisir; uygulama icinden indirme desteklenmez,
  mobil tarayici veya masaustu gerekir.
  [Etsy Help: How to Download a Digital Item](https://help.etsy.com/hc/en-us/articles/115013328108-How-to-Download-a-Digital-Item)
- Kisisellestirme alanlari, teslim turunden ayri ilan ozelligidir. Ilan bu
  alanlarla siparis girdisini toplayabilir; ancak alinan metnin dogrulanmasi,
  render ve insan onayi AstroLove sorumlulugundadir.
  [Etsy Help: How to Offer Personalized Listings](https://help.etsy.com/hc/en-us/articles/115015570787-How-to-Offer-Personalized-Listings)

### B. Physical ilan + dijital teslim

Bu yol icin resmi kaynaklarda bir istisna veya tavsiye bulunmamistir.
Tersine, Etsy dijital dosyalari dijital kategori/teslim akisi icinde tarif
eder ve ilanin urunu dogru temsil etmesini ister. Yalniz dijital teslim
edilecek bir urunu `physical` olarak isaretlemek:

1. aliciya fiziksel paket ve kargo takibi beklentisi verir;
2. kargo profili/adresi ve processing/estimated-delivery davranisini gereksiz
   yere devreye sokar;
3. Etsy'nin yerel download kaydini ve alici Download Files deneyimini atlar;
4. "teslim edildi" kanitini bir mesaj veya dis baglantiya indirger.

Sonuc: **AstroLove bunu uyumlu bir yedek yol saymamalidir.** Mesaj eki veya
indirme linki ile dijital teslim, yanlis fiziksel siniflandirmayi duzeltmez.
Gercek bir fiziksel urun de gonderiliyorsa ayri bir fiziksel/karma urun
degerlendirmesi gerekir; bu belgenin 156 yalniz-dijital ilani buna girmez.
[Etsy Creativity Standards](https://www.etsy.com/legal/creativity/)
[Etsy Seller Policy](https://www.etsy.com/legal/sellers/)

### C. Siparis sonrasi API ile teslim

| Islem | Public Open API v3 durumu | Sonuc |
|---|---|---|
| Ilana dosya ekleme | `uploadListingFile` ve listing-file okuma/silme islemleri var | Dosya ilan duzeyindedir; receipt teslimi degildir. |
| Receipt/transaction okuma ve guncelleme | Receipt islemleri var | Belgelenen semada receipt'e dijital dosya ekleme islemi yoktur. |
| Etsy Messages gonderme | Reference'ta public mesaj gonderme islemi yok | Otomatik mesaj/ek/link teslimi bu API ile kurulamaz. |
| Made-to-order siparisi dosyayla tamamlama | Public receipt-file upload islemi belgelenmemis | Orders & Shipping panelinde manuel tamamlanir. |

Kaynaklar: [uploadListingFile islemi](https://developers.etsy.com/documentation/reference/#operation/uploadListingFile),
[getListingFiles islemi](https://developers.etsy.com/documentation/reference/#operation/getListingFiles),
[getShopReceipt islemi](https://developers.etsy.com/documentation/reference/#operation/getShopReceipt),
[tum Open API v3 referansi](https://developers.etsy.com/documentation/reference/).

Buradaki "yok" ifadesi, Etsy panelinde ozelligin olmadigi anlamina gelmez;
yalnizca yayinlanmis Open API v3 yuzeyinde belgeli endpoint olmadigini anlatir.
`uploadListingFile`i her sipariste ortak ilan dosyasini degistirmek icin
kullanmak yanlistir: ayni ilanin tum alicilarini etkileyebilir ve siparis ile
dosya arasinda yerel teslim bagi kurmaz.

### D. Made-to-order ve sureler

- Dijital ilandaki **made-to-order**, dosyanin siparisten sonra uretilecegini
  ve tamamlaninca aliciya sunulacagini belirtir. Satici ilani kurarken
  processing time belirler; musteri bu sureye gore teslim beklentisi gorur.
  [Dijital ilanlari yonetme yardimi](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings)
- Fiziksel ilanlarda processing profile/readiness state, urunun gonderime
  hazirlanma suresini besler ve kargo ile birlikte tahmini teslimi olusturur.
  Bu fiziksel modele ait mekanizma, yalniz dijital urunu fiziksel yapma gerekcesi
  degildir. [Etsy Help: processing times](https://help.etsy.com/hc/en-us/articles/115015588087-How-to-Set-Processing-Times-and-Ship-By-Dates)
  [Open API: createShopReadinessStateDefinition](https://developers.etsy.com/documentation/reference/#operation/createShopReadinessStateDefinition)
- AstroLove, panelin izin verdigi araliktan gercekci bir sure secmelidir.
  Ilk olcumde 3-5 is gunu adaydir; paneldeki guncel sinir ve musteriye
  gosterilen tarih dry-run kontrolunde kaydedilmeden **kesinlestirilmez**.

## Secenekler

| Secenek | Kural uyumu | Musteri deneyimi | Otomasyon | Baslica risk | Karar |
|---|---|---|---|---|---|
| **Digital / made-to-order; siparise panelden dosya yukle** | Etsy'nin yerel modeli | Etsy Downloads, e-posta bildirimi ve siparise bagli dosya | Render/onay otomatik olabilir; son yukleme manuel | Sure asimi ve yanlis siparise dosya | **Onerilen** |
| Digital / instant; ilana yer tutucu veya talimat PDF'i koy | Urun son dosyayi vaat ediyorsa yaniltici olabilir | Alici hemen nihai urun yerine yer tutucu alir | Yuksek gorunur ama gercek teslim yine ayri | Kafa karisikligi, erken "teslim" kaydi | Kullanma |
| Physical; mesaj eki veya dis link | Yalniz-dijital urunun turu/teslimi uyusmaz | Kargo beklentisi; yerel Downloads yok | Public mesaj API'si yok; manuel | Politika, vaka ve teslim kaniti riski | Kullanma |
| Digital / made-to-order; teslimi yalniz mesaj/link ile yap | Ilan turu dogru, fakat yerel teslim akisi atlanir | Link erisimi/guveni ve kaliciligi zayif | Public mesaj API'si yok | Dosya guvenligi ve teslim uyusmazligi | Ana yol yapma |

## Onerilen uygulama plani

### 0. Canli degisiklikten once

1. 156 ilanin kimlik, urun ailesi, mevcut `type`, ekli dosya sayisi,
   kisisellestirme alanlari ve metinlerinde "instant" iddialarini salt-okur
   envanterle.
2. Tek bir taslak/pasif test ilaninda panelin digital + made-to-order akisini,
   izin verilen processing araligini, kisisellestirme alanlarini ve aliciya
   gosterilen vaadi elle dogrula. API alan yoklugu panelde alan yoklugu kaniti
   sayilmaz.
3. Baslik/aciklama/SSS metnini acik hale getir: fiziksel urun yok; anlik
   indirme yok; kisisellestirilmis dosya belirtilen surede Etsy Downloads
   uzerinden teslim edilir.
4. Degisiklik plani ve geri alma envanterini Claude incelemesine sun; ilgili
   canli Etsy yazmasi icin Serdar'in isleme ozel acik onayini bekle.

### 1. Ilan donusumu (onaydan sonra)

1. Once tek pilot ilani digital + made-to-order yap; nihai dosyayi ilana
   instant dosya olarak ekleme. Zorunlu kisisellestirme sorularini ve sinirlari
   uygula.
2. Processing time'i panelde dogrulanan gercekci degerle ayarla. Metinden tum
   "instant download" ve fiziksel/kargo imalarini kaldir.
3. Pilotun panel goruntusunu ve salt-okur geri okumasini iki-kisilik kontrolden
   gecir. Basariliysa 78 duvar sanati ve sonra 78 wallpaper ilani icin kademeli
   uygula; her kume sonrasinda sayim ve metin denetimi yap.

### 2. Her siparisin uretim ve onay kapisi (IS_0024)

1. Receipt'i salt-okur al; ilan/receipt kimligini dahili siparis kimligine
   esle. Musteri verisini repoya veya loga yazma.
2. Kisisellestirme girdilerini dogrula. Eksik/gecersizse uretme ve teslim etme;
   manuel musteri iletisim kuyruguna al.
3. Nihai dosyalari gecici siparis dizininde uret; boyut, format, isim/metin ve
   urun ailesi kontrollerini calistir.
4. IS_0024 akisi ile `onay.html` ve `kayit.json` paketini olustur. Tam
   cozunurluklu teslim dosyalarinin SHA256 degerlerini onay defterine bagla.
5. **Serdar onayi yoksa, onay kaydi eksikse veya dosya hash'i degismisse
   fail-closed dur.** Etsy'ye dosya yukleme ya da siparis tamamlama yapma.
6. Gecerli onaydan sonra yetkili kisi Etsy Orders & Shipping'de dogru siparisi
   acar, nihai dosyalari yukler ve siparisi tamamlar. Bu adim otomatikmis gibi
   raporlanmaz.
7. Teslimden sonra receipt durumu, dosya adlari/sayisi ve teslim zamani
   salt-okur dogrulanir; kisisel veri icermeyen kanit kaydi tutulur. Hata varsa
   kuyruk durdurulur, sonraki siparise gecilmez.

### 3. Pilot kabul ve yayginlastirma kapilari

- **Ilan kapisi:** digital, made-to-order, zorunlu alanlar, dosyasiz ilan ve
  dogru processing vaadi panelde gorulmeli.
- **Dosya kapisi:** beklenen uzanti/sayi/olcu ve SHA256, IS_0024 onay kaydiyla
  birebir olmali.
- **Insan kapisi:** ilgili pakete ait Serdar onayi olmali.
- **Teslim kapisi:** operatorden once receipt/urun/isimler, operatorden sonra
  Etsy download kaydi ikinci kez kontrol edilmeli.
- **Yayginlastirma:** en az bir sahte/test akisi ve bir acikca onaylanmis pilot
  sorunsuz tamamlanmadan 156 ilana toplu gecis yapilmamali.

## Bilinen sinirlar ve acik dogrulamalar

- Open API referansinda receipt-file veya Messages endpoint'i sonradan
  eklenebilir; uygulama gununde resmi reference yeniden kontrol edilmelidir.
- Paneldeki processing-time secenekleri bolge/hesap/arayuz degisikligine tabi
  olabilir; kesin 3-5 gun karari panel kaniti olmadan verilmemistir.
- Dijital sipariste iptal/iade ve AB tuketici haklari ayri hukuk/politika
  incelemesidir; bu belge bu konuda yeni magazaya-ozel kural koymaz.
- Bu arastirma Etsy/Drive/Prodigi'ye yazmadan ve musteri verisi kullanmadan
  yapilmistir.
