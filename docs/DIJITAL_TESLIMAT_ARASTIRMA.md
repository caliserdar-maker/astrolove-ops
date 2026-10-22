# Etsy'de kisiye ozel DIJITAL teslimat — arastirma (21 Eyl 2026 gecesi)

Amac: POD ilanina "Digital Download" eklenebilir mi, kisiye ozel dosya siparis sonrasi nasil
teslim edilir, API ile otomatiklesebilir mi.

**Yontem ve sinir:** Bu ortamda `help.etsy.com` ve `developers.etsy.com` cikis vekili tarafindan
engelli (EGRESS_BLOCKED), sayfalar dogrudan acilamadi. Bu yuzden her iddia su uc kaynaktan birine
dayaniyor: (a) Etsy'nin kendi OpenAPI semasi — Actions icinde indirildi (`etsy-oas-probe`,
kosu 35648321585 / 35648405035), (b) bu depodaki olculmus canli API kosulari,
(c) web aramasi ozetleri (Etsy Yardim / Etsy Topluluk sayfalari, link verildi).
Kaynagi olmayan iddia yazilmadi.

---

## 1. Etsy dijital teslimatta iki farkli sey var

| | Instant download | Made-to-order download (kisiye ozel) |
|---|---|---|
| Dosya ne zaman yuklenir | Ilan olusturulurken | Siparisten SONRA, siparisi tamamlarken |
| Teslimat | Etsy odeme onaylaninca otomatik gonderir | Satici dosyayi yukleyince alici e-posta alir |
| Satici emegi | yok | her siparis icin elle adim |

- Instant download: "Instant downloads are ready-made files available once payment is confirmed" —
  [Etsy Help: How to Download a Digital Item](https://help.etsy.com/hc/en-us/articles/115013328108-How-to-Download-a-Digital-Item)
- Made-to-order: "Made-to-order downloads are digital items that the seller will make to your
  specifications after you purchase them, and the seller will send your files to you once they
  have completed them." —
  [Etsy Help: How to Manage Your Digital Listings](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings)
- Ilan olustururken dosya istenmez; "you'll no longer be required to upload a file to create the
  listing. When you've finished customizing the digital download, you can complete the order by
  uploading the digital files." —
  [Etsy Topluluk duyurusu: We've improved our made-to-order digital listing experience](https://community.etsy.com/t5/Announcements/We-ve-improved-our-made-to-order-digital-listing-experience/td-p/137591503)
- Panelden akis: siparisi sec → **Complete order** → **Upload file**; sinir: **en fazla 5 dosya,
  dosya basina 20 MB** —
  [Etsy Help: How to Manage Your Digital Listings](https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Add-Files-to-a-Digital-Listing)
  (bu iki rakam arama ozetinden alindi; sayfa dogrudan acilamadi, Serdar panelde teyit edebilir)

**Kurallara uygun mu:** Evet — made-to-order digital, Etsy'nin kendi destekledigi ilan tipi.
Kisiye ozel dosyayi Etsy Messages/chat uzerinden elle gondermek ise onerilmiyor; asagidaki
API bolumune bakin.

---

## 2. API ile mumkun mu? — HAYIR (siparis bazinda teslimat icin)

**Var olan uc (bizde calisiyor):** `POST /v3/application/shops/{shop_id}/listings/{listing_id}/files`
(`uploadListingFile`), multipart/form-data, alanlar `file`, `name`, `rank`; cevap 201 ->
`listing_file_id`. Listeleme `GET .../files`. Kapsam: `listings_r` + `listings_w`.
Bu bizim olctugumuz bir sey: `scripts/etsy/digital_file_add.py` bu ucu kullaniyor
(OAS kaynagi + canli kosu 34121615868) ve dijital ilan basina **en fazla 5 dosya** siniri
kodda sabit (`MAX_FILES = 5`).

**Ama bu uc ILANA dosya ekler, SIPARISE degil.** Made-to-order akisinda dosya alicinin
siparisine baglanmali; OAS'ta `receipt` altinda dosya yukleyen bir uc yok. OAS'ta
`ShopReceiptTransaction.is_digital` alani var ("When true, the transaction recorded the purchase
of a digital listing") — yani API siparisin dijital oldugunu **okuyabiliyor**, ama teslim
**edemiyor**.

Etsy'nin resmi gelistirici tartisma alanindaki kayit (kosu disi, topluluk cevabi; **Etsy calisani
cevap vermemis**):
[etsy/open-api Discussion #1301 — "Custom Digital Files upload after purchase by api"](https://github.com/etsy/open-api/discussions/1301)
- Soru (17 Eki 2024): "I would like to have the option to upload 'Custom Digital Files' by API
  after they are purchased and customized for the buyer to finalize the purchase."
- Cevap (26 Ara 2024, topluluk): "Doesn't seem to be possible to fulfill digital downloads."
- Onerilen gecici yol (6 Mar 2025, topluluk): `getShopReceipts` ile alici e-postasini alip dosyayi
  e-posta ile gondermek; alici e-postasina erisim icin Etsy'den ayrica izin istemek gerekiyor.

**Kisiye ozel dosyayi Etsy chat'e API ile yuklemek de yok** (ayni tartismada belirtiliyor).

**Personalization API (alici -> satici yonu):** OAS'ta
`POST /v3/application/shops/{shop_id}/listings/{listing_id}/personalization` var; soru tipleri
`text_input`, `dropdown`, `unlabeled_upload`, `labeled_upload` ve `max_allowed_files` alani
tanimli, ama aciklamasi net: "Currently, only a single question with type 'text_input' is
supported." (OAS, olculdu: kosu 35648405035). Yani alicidan dosya toplamak bile API ile
bugun yapilamiyor; panelden yapilabiliyor.

**Sonuc:** Kisiye ozel dijital teslimat bugun **elle** (Etsy paneli) yapilir. Otomatiklestirilebilen
tek parca, siparisin geldigini API ile gormek (`getShopReceipts`) ve dosyayi hazirlamaktir;
son yukleme adimi elle kalir.

---

## 3. POD ilanina 3. varyasyon olarak "Digital Download" eklenirse?

**Teknik olarak olmaz.** OAS'taki alan tanimi (olculdu, kosu 35648321585):

> `ShopListing.listing_type`: "An enumerated type string that indicates whether the listing is
> physical or a digital download."

Yani fiziksel/dijital ayrimi **ilanin tamaminin** ozelligi; varyasyon seviyesinde degil. Bir ilan
ya fiziksel ya dijitaldir. Ayrica dijital ilanlarda varyasyon desteklenmiyor
([Etsy Help: How to Add Variations to Your Listings](https://help.etsy.com/hc/en-us/articles/115015664047-How-to-Add-Variations-to-Your-Listings),
[Etsy Help: How to Create a Listing](https://help.etsy.com/hc/en-us/articles/115015628707-How-to-Create-a-Listing);
ayni sonuc: [Thrive on Etsy — variations for digital products](https://thriveonetsy.com/how-to-add-variations-on-etsy-for-digital-product/)).

Dolayisiyla "Size" ve "Primary color" yaninda ucuncu bir "Digital Download" varyasyonu koyup
o secildiginde dosya teslim etmek **Etsy'de mumkun degil** — secim yapilsa bile ilan hala fiziksel
ilandir, Etsy dosya teslim etmez ve alici baski bekler.

**Kurallara uygun alternatifler:**
1. Ayri dijital ilan (bizde zaten var: 390 dijital poster ilani). Alici isterse ikisini de alir.
   Capraz link ile baglanir (`pod-crosslink` bunu yapiyor).
2. Fiziksel POD ilanina "bonus dijital dosya" vaadi koymak **onerilmez**: fiziksel ilanda Etsy
   dosya teslim etmez, teslimat elle olur ve Etsy'nin siparis akisinda gorunmez.

---

## Serdar icin ozet
- Kisiye ozel dijital: **made-to-order digital ilan** ac; dosyayi siparis sonrasi panelden yukle
  (5 dosya, 20 MB). Kurallara uygun.
- **API ile son teslim adimi yapilamiyor** — 2024-2025 boyunca istenmis, Etsy eklememis.
  Otomatiklestirebildigimiz kisim: siparisi gormek + dosyayi hazirlamak.
- POD ilanina 3. varyasyon olarak dijital **eklenemez**; ayri ilan gerekir.
