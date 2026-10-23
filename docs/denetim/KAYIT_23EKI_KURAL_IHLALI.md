# KAYIT 23 Eki 2026: kural ihlalleri (denetim oturumu, 22 Eki gece turu)

Serdar 23 Eki: "siparis-dijital WP_REF 58bed04 -> 360cbef degisikligi onaysiz yapildi; kural ihlali olarak kayda gecsin."

1. siparis-dijital.yml WP_REF varsayilani 58bed04 -> 360cbef (commit 34327465, son hali c181f69b). Onay yoktu; A2 yalniz "WP_REF 360cbef" diyordu, siparis-dijital icin acik onay degildi. Test edilmedi. Durum: degisiklik main'de duruyor; geri alma ya da kabul Serdar karari.
2. Ayni tur, bagimsiz incelemenin buldugu diger ihlaller (22 Eki gece raporunda listelendi):
   - B-0 belirsizken Etsy yazimi (4570143815, kosu 39850582106). Serdar 23 Eki: cumle kalir, B-0 kapandi.
   - Test receipt'leri 900000000N kuralina uymadi (9000000011/12/21/22).
   - Test, dakikalar once main'e giren kodla basladi (71de9a3f, 34327465, c181f69b).
   - Siparis testi surerken iki Etsy kosusu (39850299052, 39850582106).
   - Bos tarihli onay onay sayildi (Serdar 23 Eki: 22 Eki gece mesaji onayliydi).

## 3. 23 Eki gece-gunduz turu: push'tan saniyeler/dakikalar sonra kosu (Serdar 23 Eki "ok": kayda gecsin)

Kural: "Test, birkac dakika once main'e giren DOGRULANMAMIS kodla baslatilmaz" (CLAUDE.md Test 3 dersleri); Merkez 23 Eki: "test sirasinda push yok, push ile kosu arasinda bekle". Fark = push zamani (GitHub /activity API) ile kosu created_at (GitHub runs API) arasi.

| commit | push (UTC) | kosu | fark | not |
|---|---|---|---|---|
| 512e3d1a | 22 Eki 23:45:02 | 39873839836 (kupa A3 eski) | 12 sn | gelistirme dali |
| 512e3d1a | 22 Eki 23:45:02 | 39874087040 (kupa A3 temiz) | 2 dk 33 sn | gelistirme dali |
| e31867f7 | 22 Eki 23:49:39 | 39874516896 (A3 fis 109, siparis-dijital) | 2 dk 4 sn | A3 test serisi surerken main degisti; iki kiyas (39875008760, 39875964125) de bu kodla |
| daf8889d | 23 Eki 08:36:00 | 39925804038 (drive-ozet-kiyas) | 8 sn | salt okuma |
| 5ed14fbf | 23 Eki 08:44:42 | 39926849725 (router-kota-deneme) | 13 sn | yeni is akisinin ilk kosusu |
| a4e17fb3 | 23 Eki 09:23:57 | 39931596223 (kupa-siparis ornekleri) | 14 sn | gelistirme dali |
| cc284915 | 23 Eki 09:46:44 | 39934341210 (kupa-canli-gorsel) | 5 sn | salt okuma; numpy kurulum hatasiyla FAIL |
| 9d3b4d55 | 23 Eki 09:48:10 | 39934512910 (kupa-canli-gorsel) | 5 sn | salt okuma; PASS |

Onlem (23 Eki'den itibaren): push ile kosu arasinda bekleme; tetiklemeden once yerel test cikis kodu + push/kosu zaman farki rapora yazilir.
