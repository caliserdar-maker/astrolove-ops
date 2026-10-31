# AI beyan kapisi: aciklama yazan yollar (Gorev E, Serdar 31 Eki 2026)

Kural: Etsy "Sellers must disclose within their listing description if an item is created with the use of AI." Kapi tek yerde:
`etsy_common.Etsy._call` -> `ai_beyan_kapisi` (EN: `AI_BEYAN['en']`, RU: `beyan_marka_yaz.RU_BEYAN`). Beyansiz aciklama gonderilmez,
ilan `BEYAN_HATA`'ya girer, surec cikisinda kosu FAIL. Dogrudan `requests` kullanan 3 createDraftListing yolu kapiyi ayrica cagirir.
Kalici CI testi: `scripts/etsy/test_ai_beyan.py` (kapi birimi, _call yolu, post_file, kacis yollari, surec cikisi, AST depo taramasi +
mutasyon, eski kaynak FAIL). Canli yukleyiciler (kupa-galeri78-yukle, yd-kapak-yukle) `--canli` kosar: depo taramasi yok.
Liste statik taramadan (patch / put / post cagrisi yaninda `description` ya da `translations`, +-6 satir sezgisi; degiskenle kurulan
govdeler "kosullu" yazar); kaynak: depo kodu, 31 Eki. Satir numaralari tarama anina aittir.

| betik | yazim satiri (tarama) | yol | eski kaynak notu (OKU) |
|---|---|---|---|
| `scripts/etsy/beyan_marka_yaz.py` | 486,490 | `Etsy._call` (kapi) | - |
| `scripts/etsy/burc_gift_yaz.py` | 331,336,475,476 | `Etsy._call` (kapi) | - |
| `scripts/etsy/by78_kargo_sku_aciklama.py` | 108,114,357 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/by_baski_ekle.py` | 341,347 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/by_baski_kaldir.py` | 75,80,150 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/digital_desc_batch.py` | 118 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/eski78_cerceve.py` | 105,111,230 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/hazirlik_yaz.py` | 120 | `Etsy._call` (kapi) | - |
| `scripts/etsy/kupa_galeri78.py` | 876 | `Etsy._call` (kapi) | - |
| `scripts/etsy/kupa_ru.py` | 111 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_5x7_yaz.py` | 371,380 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_crosslink.py` | 189,192 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_desc_batch.py` | 106 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/pod_desc_set.py` | 136,142 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/pod_desc_update.py` | 130,135 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/pod_inventory_update.py` | 247 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_listing_create.py` | 610,616 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/pod_listing_update.py` | 127 | `Etsy._call` (kapi), kosullu (payload degiskeni) | - |
| `scripts/etsy/pod_seo_update.py` | 172 | `Etsy._call` (kapi), YAZ_ALAN govdesi | - |
| `scripts/etsy/pod_paper_update.py` | 248,254 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_ru_tags.py` | 120 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pw_ru_fill.py` | 234 | `Etsy._call` (kapi) | - |
| `scripts/etsy/seo51_yaz.py` | 186,192,224,226 | `Etsy._call` (kapi) | - |
| `scripts/etsy/seo_accuracy_apply.py` | 174 | `Etsy._call` (kapi), kosullu (alan listesi) | - |
| `scripts/etsy/wp_description_78_apply.py` | 170 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/wp_listing_update.py` | 205 | `Etsy._call` (kapi) | - |
| `scripts/etsy/xsell_links.py` | 385,434,440 | `Etsy._call` (kapi) | - |
| `scripts/kapak78/yd_kapak_yukle.py` | tg_metin / tg_geri PATCH | `Etsy._call` (kapi) + kuruda tg_metin_kapisi | - |
| `scripts/etsy/by78_taslak.py` | 249,255 | dogrudan requests createDraftListing, `ai_beyan_kapisi` 248 | - |
| `scripts/etsy/by_taslak_ac.py` | 215 | dogrudan requests createDraftListing, `ai_beyan_kapisi` 214 | - |
| `scripts/etsy/kupa_taslak.py` | 388 | dogrudan requests createDraftListing, `ai_beyan_kapisi` 386 | - |
| `scripts/pod/ayar77_yaz.py` | 147 | `Etsy._call` (kapi) | - |
| `scripts/pod/dijital_secenek_tek.py` | 142 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/pod/ilan_yapi_v2.py` | 531,536 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/pod/pod_boy_15.py` | 347,349 | `Etsy._call` (kapi) | - |
| `scripts/pod/pod_pilot_15.py` | 582,584 | `Etsy._call` (kapi) | - |
| `scripts/pod/yayilim_78.py` | 292,295,300,377 | `Etsy._call` (kapi) | OKU notu eklendi |

Ek: `scripts/etsy/by78_yayinla.py:202` dogrudan requests ile yalniz `state` PATCH'i (aciklama yok; testte muaf).
YD yolu (`scripts/kapak78/yd_kapak_yukle.py` tek gecis) yalniz EN baslik + aciklama PATCH'i; RU ceviri yazimi yok (test A11).
`scripts/etsy/tek_ilan_adim.py:103` yalniz `shipping_profile_id` PATCH'i (aciklama yazmaz; ilk taramada yanlislikla listelenmisti).

## Bagimsiz inceleme (31 Eki) sonrasi: duzeltilenler
- Statik koruma AST'ye tasindi: cok satirli cagri, degiskenle URL, Session, yorumdaki kapi metni, karisik govde, ortam URL'si, urllib,
  `requests.request(method, ...)`, baska fonksiyonda kapi: 9 kacis bicimi mutasyonla yakalaniyor, 2 gecerli bicim muaf (test C/D mutasyon).
- Kapi: yol sorgu dizesindeki description, `post_file` (multipart createDraftListing), `rus` / `zh-hant` yollari, tekrarli description,
  JSON dizesi govde kapsamda; `description: None` kismi yazim sayilir. Surec cikisi alt surecte olculuyor (F8); cikista logging.shutdown.
- Canli yukleyicilerde yalniz kapi davranisi testi (`--canli`): ilgisiz bir betik degisikligi canli yazimi / geri almayi durdurmaz.

## Acik kararlar (Serdar)
1. Kismi yazim ile yayina alma: `state=active` (by78_yayinla:202, pod_publish:127, wp_ilan_yayinla:74) ve aciklamasiz updateListing
   (taslagi otomatik yayina alir) canli aciklamanin beyanini OKUMAZ. Oneri: yayina alan / taslaga dokunan yazimdan once 1 GET ile
   canli aciklamada beyan kontrolu (ilan basina +1 istek).
2. Geri alma: eski canli metin beyansizsa kapi geri almayi durdurur (yd tg_geri, kupa_galeri78 desc_once, burc_gift_yaz). Oneri: yalniz
   yedekteki eski metnin sha'si ile birebir ayni metne donuste izin (istisna kayitli), ya da geri almada metin yerine beyanli yeni metin.
3. RU sirasi: pod_inventory_update / pod_boy_15 / pod_pilot_15 / beyan_marka_yaz once EN, sonra RU yazar; RU beyansizsa ilan EN-yeni /
   RU-eski kalir. Oneri: ilan basina iki kapiyi yazimdan once birlikte calistir.
4. RU yanlis FAIL: RU PUT hep tum metni gonderir; eski RU metni beyansiz ilanda yalniz baslik / etiket duzeltmesi de FAIL olur.
5. kupa_galeri78 kuru plani (metin_plani) beyan kontrolu yapmaz; canli kupa yazimi bittikten sonra eklenecek (kosu sirasinda kupa koduna
   dokunulmadi; bugunku kupa metni beyanli, 58 ilan PASS).
