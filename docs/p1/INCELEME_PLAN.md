# P1 plan incelemesi (E; işi yapmamış tek ajan, "neden yanlış, kanıtla"; 4 Kas)

Kapsam: PLAN_P1.md + kuru çıktısı docs/p1/P1_KURU_20261104_1255/ (koşu 41833440548).

## Veri doğrulaması: TEMİZ (bağımsız yeniden hesap, 78/78)

- EN ve RU'da silinen parça tam 1 kez geçiyor; silinince kalan metin "sonra" ile birebir aynı. Fazladan boşluk, nokta, \r ya da HTML varlığı yok.
- ru_geri = ru_once.
- onay_ozet = sha256(en + "\n\x00\n" + ru), FARK ve ONCE_SONRA'da aynı.
- Fark tam 1 paragrafta, EN ve RU'da paragraf [4].
- Yedek eksiksiz: başlık, malzeme, 13 etiket, RU başlık, 13 RU etiket.
- METIN_KESIN, RU_YASAK ve uzun/orta tire taramasında eşleşme 0.
- Plandaki RU paragrafı = SABIT anahtarı = YENI_RU.

## Bulgular ve yapılanlar

| # | Düzey | Bulgu | Yapılan |
|---|---|---|---|
| 1 | YÜKSEK | Plan §4 "tahmini + 10 karşılanmıyorsa böl" ile yeni eşik öneriyordu. "Kalan ≥ 20 + 10" kapısı fiilen ilan başına 30 eşiği; CLAUDE.md KOTA SINIRI = 10, "yeni eşik önerilmez". | Ek eşik cümlesi çıkarıldı. 20 + 10 kapısının 3-4 Kas'ta Serdar onaylı sapma olduğu yazıldı. P1 için kullanılıp kullanılmayacağı SERDAR SORUSU olarak açık bırakıldı (§4). |
| 2 | ORTA | §7 eksikti: plan_ilan imza/dönüş uyumsuzluğu, yukle() YEDEK.json, yml'de sabit kuru yolu, varsayılan ids, iş akışı main'de olmalı, birleştirme listesinde p1_poster_kuru yok. | §7 yeniden yazıldı (uyarlayıcı, ONCE_SONRA.yedek, yol, ids, parti, DEGISIKLIK her ilanda, sha256, main). Birleştirme listesine p1_poster_kuru eklendi. |
| 3 | ORTA | Son okuma ölçütü zayıftı (ZATEN_YENI sınıfı tam metne bakmıyor). | §6: tam metin = "sonra" + onay_ozet + başlık/etiket/malzeme/RU başlık/etiket + state. |
| 4 | ORTA | Zaman aşımı ve iptal DUR listesinde yoktu; iptalde yarım kalan ilan kayıtsız. | §3'e eklendi; yazıcıda DEGISIKLIK.csv her ilandan sonra eklenecek (§7). Süre: 4 Kas'ta 77 ilan ~3 dk (22:55:22 → 22:58:06, DEGISIKLIK). |
| 5 | ORTA | 3-4 Kas son doğrulaması (poster_son_ozet) P1'den sonra koşulamaz. | §8'e yazıldı (canlıda "premium" 0, yani 3-4 Kas tamam). |
| 6 | ORTA | Galeri kartlarında aynı söz var; açıklama ile çelişki. | §8'e risk ve Serdar kararı olarak eklendi (kart_nokta_marka.py, wa_kupa_kart_ornek.py:81). |
| 7 | ORTA | "246 aktif" kuru OZET'te yok; sayımın kapsamı dar. | §1'de kaynak (okuma OZET + AKTIF_SAYIM, Drive) ve kapsam sınırı (aktif, yalnız EN, tek kalıp) yazıldı. |
| D1 | DÜŞÜK | 1560 bir üst sınır değil (5xx yeniden gönderimi). | §4 düzeltildi. |
| D2 | DÜŞÜK | §7 gerekçesi kısmen yanlış (poster_metin_yaz/pod_5x7_yaz kur'dan önce DUR verir). | §7 düzeltildi. |
| D3 | DÜŞÜK | --immutable dosyayı korumaz; sha256 karşılaştırılmıyor. | §6'ya dal sha256 değerleri ve yazıcıda karşılaştırma eklendi. |
| D4 | DÜŞÜK | Söz şablonlarda duruyor (aciklama_v3_sablon, pod_5x7_kuru, pod_changes_v3). | §8. |
| D5 | DÜŞÜK | Yazıcıda parti kavramı yok. | §7. |
| D6 | DÜŞÜK | RU sıfırlanma riski düşük. | §8. |
| D7 | DÜŞÜK | Yanıt gelmezse ne olacağı metinde yok (iş riski). | §8, Serdar bilgisine. |
