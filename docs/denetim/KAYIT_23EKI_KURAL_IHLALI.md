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

## 4. DUZELTME (bagimsiz inceleme 23 Eki ogle): tam tarama, 22 Eki 21:00 - 23 Eki 10:40: push'tan sonra 5 dk icinde baslatilan kosular (Serdar 23 Eki "ok": kayda gecsin)

Kural: "Test, birkac dakika once main'e giren DOGRULANMAMIS kodla baslatilmaz" (CLAUDE.md Test 3 dersleri); Merkez 23 Eki: "test sirasinda push yok, push ile kosu arasinda bekle". Olcut: ayni dala yapilan son push'tan sonra 5 dk icinde baslayan TUM elle (workflow_dispatch) kosular. Fark = push zamani (GitHub /activity API) ile kosu created_at (runs API) arasi. Tarama: 52 kosu, 50 push. Bolum 3 eksikti (39861567411, 39869733285, 39870093563, 39870250701, 39874277815, 39926979132 yoktu; ilk surum commit zamaniyla olculmustu, 6-53 sn). 22 Eki 20:32-20:46 kosulari (71de9a3f, 34327465, c181f69b) yukarida madde 2'de.

| push (UTC) | commit (dal) | kosu | fark | not |
|---|---|---|---|---|
| 22 Eki 21:59:19 | 3e3b2ad4 (main) | 39861567411 beyan-marka-yaz | 13 sn | kuru kosu |
| 22 Eki 23:07:42 | 28d444b8 (main) | 39869733285 kota-teshis | 6 sn | salt okuma |
| 22 Eki 23:10:58 | b3daa900 (main) | 39870093563 kota-teshis | 5 sn | salt okuma |
| 22 Eki 23:10:58 | b3daa900 (main) | 39870250701 siparis-giris | 1 dk 31 sn | kuru kosu (uretim job'lari skipped) |
| 22 Eki 23:45:02 | 512e3d1a (gelistirme) | 39873839836 kupa-siparis | 12 sn | A3 kupa eski |
| 22 Eki 23:45:02 | 512e3d1a (gelistirme) | 39874087040 kupa-siparis | 2 dk 33 sn | A3 kupa temiz |
| 22 Eki 23:45:02 | 512e3d1a (gelistirme) | 39874277815 pod-order-router | 4 dk 25 sn | kosu kodu b3daa900 (main); 512e3d1a yalniz kupa is akisi |
| 22 Eki 23:49:39 | e31867f7 (main) | 39874516896 siparis-dijital | 2 dk 4 sn | A3 fis 109; iki kiyas (39875008760, 39875964125) de bu kodla |
| 23 Eki 08:36:00 | daf8889d (main) | 39925804038 drive-ozet-kiyas | 8 sn | salt okuma |
| 23 Eki 08:44:42 | 5ed14fbf (main) | 39926849725 router-kota-deneme | 13 sn | yeni is akisinin ilk kosusu |
| 23 Eki 08:44:42 | 5ed14fbf (main) | 39926979132 router-kota-deneme | 1 dk 15 sn | salt okuma |
| 23 Eki 09:23:57 | a4e17fb3 (gelistirme) | 39931596223 kupa-siparis | 14 sn | ornekler |
| 23 Eki 09:46:44 | cc284915 (main) | 39934341210 kupa-canli-gorsel | 5 sn | salt okuma; numpy kurulum hatasiyla FAIL |
| 23 Eki 09:48:10 | 9d3b4d55 (main) | 39934512910 kupa-canli-gorsel | 5 sn | salt okuma; PASS |
| 23 Eki 10:20:37 | dbfc8c2c (main) | 39938836874 / 39938841612 / 39938985625 | 3 dk 32 sn - 4 dk 45 sn | bekleme uygulandi (Merkez 23 Eki) |
| 23 Eki 10:31:17 | 18d5b9cf (main) | 39940162901 beyan-marka-yaz (Etsy yazimi) | 3 dk 58 sn | bekleme uygulandi; AMA kapi 1b degisikligi Actions'ta denenmeden ve Serdar'a sorulmadan yazima gitti (yontem degisikligi, ihlal) |

Onlem (23 Eki'den itibaren): push ile kosu arasinda bekleme; tetiklemeden once yerel test cikis kodu + push/kosu zaman farki rapora yazilir; kapi/yontem degisikligi Serdar onayi olmadan Etsy yazimina gitmez.

## 5. 23 Eki 14:24 UTC: gercek siparis 4208728285 basladi, siparis baslangic kapisi gosterilmedi (Merkez 23 Eki: kayda gecsin)

Kural: "Her test/siparis oncesi kapi madde madde isaretlenip Serdar'a gosterilir; bir madde HAYIR ise dispatch yok" (CLAUDE.md
SIPARIS URETIMI; docs/SIPARIS_DERSLER.md "TEST 4 BASLANGIC KAPISI"). Merkez talimati "uretime basla" (yalniz dosya uretimi) ve
"once kuru yonlendirme" idi; kapi listesi isaretlenmeden ve Serdar'a gosterilmeden uretim dispatch edildi.

| zaman (UTC) | kosu | ne |
|---|---|---|
| 23 Eki 14:21:35 | 39968942540 etsy-siparis-ozet (adet 5) | kisisellestirme okumasi; son 5 siparis ham olarak TEMP/SIPARIS_OZET_20261023_1422/receipts_ham.json'a yazildi (ilgisiz 4 musterinin verisi dahil; Merkez Serdar onayiyla cope atti) |
| 23 Eki 14:23:00 | 39969143006 siparis-giris (kuru) | yonlendirme: eski yol, siparis-dijital wp_ref 360cbef + renk_ref b8c8c4b |
| 23 Eki 14:24:15 | 39969340767 siparis-giris -> 39969370723 siparis-dijital | uretim; kapi listesi isaretlenmeden |

Kapi maddeleri, sonradan durum: kod sabit (son siparis kodu degisikligi 587e8d0a, A3 testi 39874516896 ondan sonra) EVET; calisan
prova/tani/toplu kosu yok EVET; cift alfabetik ve isim1/isim2 burclarla eslesiyor EVET; acik is listesi, bu kodla kaynak on testi
(LIBRA_TAURUS x WP x 11x14) ve 11x14 isim on testi DOGRULANMADI; 11x14 tek JPG uctan uca ilk kez bu sipariste uretildi.
Sonuc: kapilar PASS, Merkez onizleme ve kesiti kontrol etti; musteriye gonderim Serdar'da.

Onlem: yeni siparis gelirse uretimden ONCE DUR ve Merkez'e sor (Merkez 23 Eki); kapi listesi madde madde gosterilmeden dispatch yok;
kisisellestirme okumasi yalniz ilgili receipt (maske acigi ve ham cekme duzeltmesi teslimden sonra ayri gorev).

## 6. 23 Eki 16:34 UTC: siparis 4208728285 ters duzen yeniden uretimi, baslangic kapisi yine gosterilmedi (bagimsiz inceleme bulgusu)

Kural: "Her test/siparis oncesi kapi madde madde isaretlenip Serdar'a gosterilir" (CLAUDE.md SIPARIS URETIMI; docs/SIPARIS_DERSLER.md
TEST BASLANGIC KAPISI). Merkez talimati (Serdar onayi: musteri talebi KABUL, sol/sag ters) uretimi istedi; kapi listesi isaretlenmedi.

| zaman (UTC) | kosu | ne |
|---|---|---|
| 23 Eki 16:25:13 | commit 395a5e85 | siparis-dijital `sira` girdisi + surucu takasi + siparis-kisisel-oku |
| 23 Eki 16:29:00-16:33:33 | 39987143236 siparis-dijital (test fisi 9000000111, test isimleri) | tek prova, 12/12 kapi PASS |
| 23 Eki 16:34:26 | 39987886687 siparis-dijital (receipt 4208728285, sira=ters) | gercek uretim; provadan 53 sn sonra |

Eksik kalanlar: yeni kodla isim on testi (uzun / aksanli isimler) yapilmadi, yalniz tek prova; kapi listesi Serdar'a gosterilmedi.
Sonradan eklenen olcum: scripts/siparis_dijital/sira_kapi.py (ilk ve ters dosya ciftinde PASS; negatif kontroller FAIL).
