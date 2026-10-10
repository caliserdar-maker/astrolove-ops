# Etsy organik arama: kısa teşhis (10 Eki 2026, etsy-arama oturumu)

Kapsam: yalnız inceleme. Etsy'ye hiçbir şey yazılmadı (API yalnız GET, 82 çağrı).
Veri: canlı API 10 Eki 08:33 UTC (Drive `canli/canli_78.json`, `kategori_nitelik.json`) + Serdar'ın 10 Eki ekranları.

## Kanıtlı maddeler

| # | Bulgu | Kanıt |
|---|---|---|
| K1 | Etsy aramasından gelen ziyaret çok az ve oranı sabit: 30 günde 14/345 (%4,1; Ekim'de 4). Eylül 1-27: 12/267 (%4,5). | Serdar ekranları 10 Eki ve 27 Eyl |
| K2 | 78 ilanda 13 etiketin 12'si ve başlık kalıbı birebir aynı. İlanı ayıran tek ifade çift adı (başlıkta + 1 etiket). CAPRICORN_SAGITTARIUS ve SAGITTARIUS_SAGITTARIUS'ta çift adı etiketi hiç yok (20 karaktere sığmıyor). | API 10 Eki |
| K3 | Kategorinin (121, Prints > Giclée) sunduğu nitelikler boş (78/78): Art subject (listede "Zodiac" ve "Stars & celestial" var), Primary color, Secondary color, Room, Home style, Holiday. Dolu olanlar: Can be personalized, Framing, Material, Number of pieces, Occasion (Anniversary), Orientation. | API 10 Eki |
| K4 | Etsy: kategori ve nitelikler etiket gibi çalışır; filtreli aramada yalnız o niteliği dolu ilanlar görünür. Bizim ilanlar "Zodiac" konu filtresine ve renk/oda filtrelerine giremiyor. | Keywords 101 (K1), Attributes yardım sayfası (K2), Add Attributes (K3) |
| K5 | Framing = "Unframed" (78/78) ama ilanlar çerçeveli seçenek de satıyor. Alan tek değerli; çerçeveli arayanın filtresinde görünmüyoruz. | API 10 Eki (multi = false) |
| K6 | Etkileşim düşük: 78 ilan ömür boyu 1.085 görüntülenme, 19 favori; ilanlar 6 Eyl'de açıldı (5 hafta). Etsy organik sıralamada "Listing Engagement Rate" (tık, görüntülenme, favori, satın alma) kullanır. | API 10 Eki; Etsy Search & Ads Ranking Disclosures (K5) |
| K7 | Eylül etiket pilotu bugünkü 78 ilan için ölçülemez: 17 Eyl'de yalnız 107 DİJİTAL ilanın (95 wall art + 12 wallpaper) etiketi değişti; bu ilanlar sonra deaktif edildi; 78 POD ile kesişim 0. O dönemde Etsy aramasından ayda ~10-12 ziyaret vardı. | Drive SEO_TAG_PILOT_107_APPLY/summary.md + plan.json |
| K8 | Etsy, ücret karşılığı organik sıra satmaz; Ads ayrı etiketlenir. Ads (ROAS 1,38) organik açığı kapatmaz. | Disclosures (K5) |
| K9 | Organik gelen arama terimlerinin 8/12'si çift adı içeriyor (ters sıra dahil: "libra and cancer"). Çift adı ana kaldıraç. | Stats > Etsy Search, 1-27 Eyl (devir dosyası, Serdar ekranından) |

## Hipotezler (veri yetmiyor)

- H1. 12 ortak etiket genel sorgulara yöneliyor (anniversary gift ~1,2M sonuç, engagement gift ~1,7M; Ağustos Marketplace Insights). Yeni ve düşük etkileşimli ilanlar bu sorgularda ilk sayfalara çıkamıyor; gösterim neredeyse yalnız çift adı sorgularından geliyor.
- H2. Çift adı + ürün sözcüğü etiketi ("cancer libra print") tam ifadeyle eşleşip küçük sorgularda sırayı yükseltebilir. Tam eşleşme kuralının resmi metni bu oturumda okunamadı.
- H3. Mağaza müşteri deneyimi skoru (yorum puanı, mesaj yanıt oranı, case oranı) sıralamayı etkiliyor olabilir; yorum sayımız bilinmiyor. Search visibility sayfasından bakılmalı.
- H4. Başlıkta "print/poster" ve "names" yok; Etsy sözcükleri başlık, etiket ve açıklamada birlikte eşlediği için etkisi küçük olabilir.
- H5. Ekim-Aralık hediye sezonu öncesi/sonrası karşılaştırmayı bozar; kontrol grubu bunu kısmen dengeler.

## Yan bulgu (kapsam dışı, yalnız rapor)

- 78 açıklamanın ilk paragrafında "Our original AstroLove design" geçiyor. MARKA ADI kuralı (yalnız "AstroLove" yazılmaz) ile çelişiyor. Ayrı onayla düzeltilmeli.
- "Tartışmaya açma" notu (DEVİR 5 Eki) başlık şablonu için var; bu yüzden başlık değişikliği önerilmedi, yalnız faz 2 hipotezi olarak CSV'de.

## Kaynaklar

Etsy sayfaları bu ortamdan ve GitHub runner'dan 403 döndü (bot koruması). Aşağıdaki içerik arama motorunun bu resmi URL'lerden okuduğu metne dayanır; Serdar tarayıcıda teyit eder.
- K1 Keywords 101: https://www.etsy.com/seller-handbook/article/keywords-101-everything-you-need-to-know/382774281517 ("The categories and attributes you add act like tags, so if an exact phrase appears in your categories, you don't need to add it as a tag.")
- K2 How to Use Attributes: https://help.etsy.com/hc/en-gb/articles/115014502508
- K3 Add Attributes to Help Increase Your Shop's Visibility: https://www.etsy.com/seller-handbook/article/add-attributes-to-help-increase-your/604203126614 (filtreli sonuçta yalnız niteliği dolu ilanlar)
- K4 New Guidance for Listing Titles: https://www.etsy.com/seller-handbook/article/1399426136697
- K5 Search, Advertisement & Recommendation Ranking Disclosures: https://www.etsy.com/legal/policy/search-advertisement-recommendation/899478564529
- K6 How Etsy Search Works: https://www.etsy.com/seller-handbook/article/how-etsy-search-works/375461474487
- K7 Search analytics / Search visibility: https://help.etsy.com/hc/en-us/articles/25869947521175

## Gerekçe kodları (2_ETSY_ARAMA_78_ONERI.csv `*_gerekce` sütunları)

- G-B (başlık değişmez): başlıktaki ifade konumu sıralamayı etkilemez, başlık sözcükleri etiket ve açıklama ile birlikte eşleşir (K1, K6). İki burç ve ürün adı zaten var. Aynı anda 3 alan değişirse ölçüm bozulur. DEVİR 5 Eki: şablon onaylı. Alternatif yalnız faz 2 hipotezi.
- G-E1 (giclee print -> çift adı + print/art): kategori "Prints > Giclée" ifadeyi zaten kapsar (K1). Boşalan yere çift adı + ürün sözcüğü: organik terimlerin 8/12'si bu biçimde (K9). Etkisi HİPOTEZ (H2).
- G-E0 (etiket değişmez): 20 karaktere sığan çift + ürün ifadesi yok (15 ilan; çoğu Sagittarius/Capricorn/aynı burç çifti).
- G-N (nitelik ekle): nitelikler etiket gibi çalışır ve filtreli sonuçta yalnız dolu ilanlar görünür (K1, K2, K3). Kategori 121 bu 3 niteliği sunuyor; 78/78 boş (API). "Zodiac" ürünün birebir konusu. Primary color = Gold: tasarım 5 renkte altın (DEVİR 5 Eki "tek doku"); Serdar teyit eder.
