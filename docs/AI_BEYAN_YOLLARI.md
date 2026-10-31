# AI beyan kapisi: aciklama yazan yollar (Gorev E, Serdar 31 Eki 2026)

Kural: Etsy "Sellers must disclose within their listing description if an item is created with the use of AI." Kapi tek yerde:
`etsy_common.Etsy._call` -> `ai_beyan_kapisi` (EN: `AI_BEYAN['en']`, RU: `beyan_marka_yaz.RU_BEYAN`). Beyansiz aciklama gonderilmez,
ilan `BEYAN_HATA`'ya girer, surec cikisinda kosu FAIL. Dogrudan `requests` kullanan 3 createDraftListing yolu kapiyi ayrica cagirir.
Kalici CI testi: `scripts/etsy/test_ai_beyan.py` (kapi birimi, _call yolu, dogrudan requests korumasi, kapsam, eski kaynak FAIL).
Liste statik taramadan (patch / put / post cagrisi yaninda `description` ya da `translations`); kaynak: depo kodu, 31 Eki.

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
| `scripts/etsy/pod_listing_update.py` | 127 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_paper_update.py` | 248,254 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pod_ru_tags.py` | 120 | `Etsy._call` (kapi) | - |
| `scripts/etsy/pw_ru_fill.py` | 234 | `Etsy._call` (kapi) | - |
| `scripts/etsy/seo51_yaz.py` | 186,192,224,226 | `Etsy._call` (kapi) | - |
| `scripts/etsy/seo_accuracy_apply.py` | 174 | `Etsy._call` (kapi) | - |
| `scripts/etsy/tek_ilan_adim.py` | 103 | `Etsy._call` (kapi) | - |
| `scripts/etsy/wp_description_78_apply.py` | 170 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/etsy/wp_listing_update.py` | 205 | `Etsy._call` (kapi) | - |
| `scripts/etsy/xsell_links.py` | 385,434,440 | `Etsy._call` (kapi) | - |
| `scripts/kapak78/yd_kapak_yukle.py` | 395,405 | `Etsy._call` (kapi) | - |
| `scripts/pod/ayar77_yaz.py` | 147 | `Etsy._call` (kapi) | - |
| `scripts/pod/dijital_secenek_tek.py` | 142 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/pod/ilan_yapi_v2.py` | 531,536 | `Etsy._call` (kapi) | OKU notu eklendi |
| `scripts/pod/pod_boy_15.py` | 347,349 | `Etsy._call` (kapi) | - |
| `scripts/pod/pod_pilot_15.py` | 582,584 | `Etsy._call` (kapi) | - |
| `scripts/pod/yayilim_78.py` | 292,295,300,377 | `Etsy._call` (kapi) | OKU notu eklendi |

Ek: `scripts/etsy/by78_yayinla.py:202` dogrudan requests ile yalniz `state` PATCH'i (aciklama yok; testte muaf).
YD yolu (`scripts/kapak78/yd_kapak_yukle.py` tek gecis) yalniz EN baslik + aciklama PATCH'i; RU ceviri yazimi yok (test A11).
