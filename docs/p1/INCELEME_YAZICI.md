# P1 yazıcı incelemesi (4 Kas; işi yapmamış tek ajan, "neden yanlış, kanıtla")

Kapsam: dal p1-poster-yanitsiz a1b4a345. Dosyalar: scripts/etsy/poster_metin_yaz.py, .github/workflows/poster-metin-yaz.yml, scripts/etsy/test_poster_metin_yaz.py. İnceleme kod değiştirmedi, ağ isteği yapmadı.

## İncelemenin doğruladıkları
- sha256 sabitleri dal dosyalarıyla aynı.
- Bash ve Python onay kapısı tutarlı.
- Kilit, token indirilmeden önce alınıyor.
- EN_BASLADI satırı PATCH'ten önce diske yazılıyor (fsync).
- Gerçek `Etsy._call` ile ilan başına tipik 9 istek.
- Gerçek 78 ONCE_SONRA ile, sahte canlı `&#39;` ve `\r\n` içerirken: KURU 78/78, UYGULA 78/78, --geri-al 78/78.

YÜKSEK bulgu: 0.

## Bulgular ve yapılanlar

| # | Düzey | Bulgu | Yapılan |
|---|---|---|---|
| ORTA-1 | ORTA | YARIM durum (EN yeni, RU eski) hiçbir araçla düzeltilemiyor. Ne sonraki koşu ne --geri-al çalışıyor, ikisi de DUR veriyor. Bu durum EN PATCH işlenip hata dönerse, zaman aşımında ya da EN geri okuması tutmazsa oluşur. | Kod değişmedi. YARIM → DUR, görev tanımındaki kural. Toparlama yolu eklemek yöntem değişikliği olur, Serdar kararı. Pilot DUR verirse elle bakılır, ikinci koşu yok. Rapora yazıldı. |
| ORTA-2 | ORTA | RU geri okuması gecikirse EN yanlışlıkla geri alınıyordu: 3 okuma + 1 okumayla karar veriliyordu. Sonuç ters YARIM (EN eski, RU yeni) olurdu. | ru_basarisiz yeni RU'yu 3 kez daha arıyor (toplam 6 okuma, 3 sn arayla). Test: 4 okuma gecikmede EN geri alınmıyor (TAMAM_HATALI, DUR). 9 okuma gecikmede EN geri yazılıyor (sınır testi). En kötü istek sayısı 20; kapı 20 + 10 değişmedi. |
| D1 | DÜŞÜK | Son okumadaki onay_ozet denetimi kendini doğruluyordu: FARK değeriyle değil, hedef metnin özetiyle karşılaştırıyordu. | Karşılaştırma artık kuru plandaki onay_ozet ile (yukle, FARK = ONCE_SONRA'yı denetliyor); --geri-al'da once_ozet ile. Gerçek 78'de son okuma 78/78 PASS. |
| D2 | DÜŞÜK | ids'nin kuru planda olup olmadığı Etsy isteğinden önce denetlenmiyordu; yinelenen id kabul ediliyordu. | calis başında, Etsy isteği olmadan: kuru planda olmayan ya da yinelenen id → DUR. Test: istek 0. |
| D3 | DÜŞÜK | Geri alma yolu metin kapısını ve AI beyanını kendisi denetlemiyor. | Kod değişmedi. AI beyanını Etsy._call yazım öncesi zaten denetliyor; geri-al bu görevde koşmuyor. Kayıt. |
| D4 | DÜŞÜK | GitHub iptalinde gelen KeyboardInterrupt (BaseException) yakalanmıyor. PATCH'ten sonra gelirse yalnız EN_BASLADI satırı kalır. | Kod değişmedi; PLAN §3 bunu kabul ediyor. EN_BASLADI satırı tam bu durum için var. Kayıt. |
| D5 | DÜŞÜK | `sir_koru tara` FAIL verirse DEGISIKLIK.csv dahil hiçbir çıktı Drive'a gitmiyor. `neden` alanına Etsy hata gövdesi giriyor. | Kod değişmedi; sır kapısı gevşetilmez. Pilotta çıktı Drive'a gitmezse loga bakılır. Kayıt. |
| D6 | DÜŞÜK | Kota rakamları çelişiyor: p1_poster_kuru / FARK "7", yazıcı "9 / 18". En kötü sayıya 5xx/429 yeniden gönderimleri ve 401 yenilemesi girmiyor. | Yazıcı yorumu düzeltildi: tipik 9 (test ölçümü), en kötü 20, yeniden gönderimler hariç. FARK.csv sha ile sabit olduğundan değişmedi. |
| D7 | DÜŞÜK | İlk ilanda kalan kota bilinmediği için kapıdan önce 1 GET gidiyor. Sahte testteki "istek 0" gerçeği temsil etmiyordu. | Gerçek _call testi eklendi: kalan 29 → 1 GET, ardından kota DUR, yazım yok. |
| D8 | DÜŞÜK | ETA sayacı yoktu (CLAUDE.md HIZ madde 5). | Her ilan satırına yüzde, geçen ve kalan süre eklendi. |
| T1 | TEST | Kuru plan aynı sahte API'den kurulduğu için "uyarlayıcı = kuru" kendini doğruluyordu. | Gerçek 78 testi eklendi (dalda docs/p1 varken): canlı `&#39;` + `\r\n`; KURU 78, UYGULA 78, son okuma 78, gönderilen metinde kaçış / `\r` 0. |
| T2 | TEST | "HTML varlıksız" testi boşa geçiyordu. | Gerçek _call testinde canlı EN/RU `&#39;` ile dönüyor. Gönderilen PATCH'te `&#39;` yok. |
| T3 | TEST | Gecikmeli tutarlılık modellenmiyordu. | `ru_gecikme` testi eklendi (ORTA-2). |
| T4 | TEST | D1 dalı başarısız kılınamıyordu. | D1 düzeltmesiyle denetim artık bağımsız bir değere (kuru onay_ozet) bakıyor. |

Doğrulanamayan: Drive kopyasının dal kopyasıyla bayt bayt aynı olduğu. Merkez sha256'yı doğruladı (56d86efa…). Farklıysa yazıcı Etsy'den önce DUR verir.

Testler (düzeltme sonrası): test_poster_metin_yaz 73/73 PASS (çıkış 0).
