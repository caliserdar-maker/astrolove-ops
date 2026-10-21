# PLAN_BURC_GIFT v3 eki (22 Eki 2026): Serdar kararlari 1-6 islendi. UYGULANMADI.
Dosyalar: ONCE_SONRA_234.csv (ozet, ilan basina), SONRA_234.json (234 ilanin tam yeni baslik/etiket/aciklamasi).
Olcum: 234/234 PASS (ifadeler 3 alanda birebir ve buyuk/kucuk harf duyarli, 13 tekil kucuk harf etiket <=20, baslik <=140, tire 0);
metin_kurali GENEL PASS. Baslik: yil donumu 88-129, poster 92-130, kupa 84-122 [olcum]. Serdar'in 135 olcumu teorik ust sinir:
CAPRICORN_SAGITTARIUS gercekte "1st Wedding Anniversary Gift" grubunda (126); gercek en uzun 129 [olcum, bagimsiz inceleme].

## Kararlarin uygulanisi
1. Yil donumu kalip C (78/78 birebir). 2. Poster/kupa: ifade urun adindan hemen sonra. 3. Kupa: "zodiac symbols" ve "zodiac gift" 78/78 cikar.
   Ayni burclu 12 kupada tek ifade girdigi icin 1 bos yer kalir: ONERI "<burc> mug" (orn. "leo mug"); Serdar secer.
4. Cumle: "A thoughtful choice when you are looking for an Aries gift or Libra gifts." / ayni burc "... for Leo gifts." (a/an: an Aries,
   an Aquarius, a Pisces, a Sagittarius). 5. Tek kosu: yil donumu aciklamasi tek seferde (baski metni 77 ilanda, PLEASE NOTE + WHY PAPER 78).
   Bagimsiz inceleme satir satir diff: yalniz istenen parcalar degisiyor; yil donumunde vaat taramasi temiz [olcum].

## Tek kosuda ilan basina yazilacaklar (birlesik arac; ilan bir kez yazilir)
- Tum 234: PATCH title + tags (virgullu tek metin) + description. Once state GET (active degilse ATLA).
- Yil donumu 78 ek: materials = "digital file"; production partner kaldir ("" ile, geri okuma kapisi; olmazsa Serdar panel adimi);
  hazirlik: YENI 1-3 gun tanimi (mevcut 1517641240112 poster ve kupa ile ORTAK, degismez) envanter PUT ile.
- Yil donumu 77 ek (CANCER_LIBRA haric): envanter 15 -> 10 (Shipped print 8x10 cikar, imza kontrolu); kargo profili -> 318577242658.
  (CSV tek_kosu_diger kolonu.) by_baski_kaldir.py bu is icin kullanilamaz (yalniz aciklama PATCH, :77; baslik ayni kontrolu, :157).
- Alan bazli idempotans: her alan eski -> yaz, yeni -> atla, ikisi de degil -> DUR (o ilan listeden cikar).

## On kosullar (yazmadan once, salt okuma)
- Yedek kosusu: 234 ilanin baslik/etiket/aciklama + yil donumu envanter + translations/ru Drive'a (md5).
- Bekleyen siparis: gonderilmemis makbuzlarda SKU *-PRINT8X10 sayisi (yalniz sayi); 0 degilse DUR.
- Metricool bekleyen pin metinleri Etsy adimindan ONCE (Serdar karari 4, 21 Eki).
- 03_Formats gorseli (canli ilanda 3 format, Serdar 22 Eki): yeni gorsel ayri is; yazi duzeltmesi gorselden bagimsiz.
- Arac + sahte API testi + yeniden bagimsiz inceleme + Serdar onayi -> CANCER_LIBRA 3 aile -> pilot 5 -> kalan 226.

## Serdar'a gosterilen riskler (kaynaksiz, MI olcumu yok)
- Yil donumunde "zodiac" basliktan (78) ve etiketten (12, "X zodiac gift") tamamen kalkar; "personalized" da basliktan kalkar
  (etikette zaten yok) [olcum]. Arama etkisi olculmedi.
- Tekrarlar: baslikta "Paper Anniversary" + etiket "paper anniversary"; "anniversary" 78/78 baslikta 2 kez; 44 posterde "gift" 3 kez
  [olcum]. Etsy kilavuzu bu oturumda dogrulanmadi.
- RU ceviriler (kupa_ru.py; poster/yil donumu olculmedi) eski basligi tasir; ayri karar.
