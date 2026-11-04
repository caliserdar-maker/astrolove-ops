# P1 kod incelemeleri (CLAUDE.md KALİTE 1; işi yapmamış tek ajan, "neden yanlış, kanıtla")

Kapsam: dal p1-poster-yanitsiz. Etsy'ye yazım yok. main'e yalnız salt okuma iş akışı + betik girdi (7eb7bc37).

## D incelemesi (4 Kas, ilk kod: okuma betiği + SABIT + p1_poster_kuru)

| # | Düzey | Bulgu | Yapılan |
|---|---|---|---|
| 1 | YÜKSEK | `sinif` yarım yazımı (EN yeni + RU eski) ve varyantları (kıvrık kesme işareti, çift boşluk, taslak) ZATEN_YENI sayıyordu. | ZATEN_YENI için üç koşul birlikte aranıyor: EN'de esnek desen (GENEL_EN) 0, RU'da GENEL_RU 0, YENI_EN ve YENI_RU paragrafları birebir; ayrıca state active. Değilse DUR. Varyant da DUR. Testler eklendi. |
| 2 | ORTA | "Okunamadı" yolu gerçek koda uymuyordu (etsy_common 2xx dışında SystemExit atar); testler SaltOku'yu sınamıyordu. | Yalnız 404 ve 5xx "okunamadı"; 429, 403, kota ve YASAK koşuyu durdurur. Test gerçek SaltOku kapısıyla (Etsy._call alttan sahte): PUT, PATCH, POST, DELETE ve post_file DUR. |
| 3 | ORTA | İstek tahmini 7, kaynak yanlış. | Yazıcı bütçesi 20 (poster_metin_yaz.py:33), tipik 7 ayrı alan. |
| 4 | ORTA | RU başlık boş ve süslü parantez DUR'u yoktu. | Eklendi (poster_metin_kuru.py:86-87, :94 deseni). |
| 5 | ORTA | Okuma koşusundaki artifact. | Koşu 41827729485'te artifact indirilemedi (proxy) ve silindi (404). Kuru artık artifact kullanmıyor (Serdar 4 Kas "B"). main'deki p1-poster-oku.yml artifact adımının kaldırılması ayrı iş (main'e push bu görevde yok). |
| 6-11 | DÜŞÜK | islenmedi listesi, 2+ eşleşme, birleştirme sırası, test verisi, encoding, post_file. | Düzeltildi. Birleştirme sırası PLAN_P1.md'de. |

## C incelemesi (4 Kas, kuru iş akışı p1-poster-kuru.yml + girdi kapısı + ağ engeli + p1_dal_kapi)

YÜKSEK 0. İnceleme, Etsy biçimli sentetik 78 ilanla iş akışı adımlarını yerelde taklit etti: 78 PLAN, ag_deneme 0, sir_koru TEMIZ, dal kapısı PASS.

| # | Düzey | Bulgu | Yapılan |
|---|---|---|---|
| 1 | ORTA | Tek ilan okunamazsa girdi kapısı (HAM = 78 = OZET.okunan) koşuyu düşürür. | Kapı katı kalır. Drive OZET.json salt okumayla doğrulandı: okunan 78; okunamadi, ru_yok ve islenmedi boş; istek 237 (Merkez de doğruladı). |
| 2 | ORTA | İlan başına istisna yakalama yok. | `_isle` ilan başına yakalar; ilan DUR "istisna: <tür>". Test: bozuk HAM kaydı → 1 DUR, 77 PLAN, çıkış 0. |
| 3 | ORTA | Testlerde "canlı RU" = kur(EN). | Gerçek veri testi eklendi: testdata (3 Kas canlı EN + RU) için kur(EN) == canlı RU; canlı RU'da SIL_RU tam 1. Asıl kanıt koşuda `kur_once_esit`. |
| 4 | ORTA | main p1-poster-oku.yml artifact'ı envanter içerir. | Bu koşunun artifact'ı silindi (404). Adımın kaldırılması ayrı görev (öneri). |
| D | DÜŞÜK | Çıkış 0, plan sağlığını göstermez. | Rapor PLAN / DUR / ZATEN_YENI sayılarını ayrı verir. |
| D | DÜŞÜK | Dal kapısında CSV sütun adı ve sembolik bağ deliği. | Kapatıldı (test 10/10). |
| D | DÜŞÜK | sha256 karşılaştırılmıyor; indirme düşerse dala log yok; dala eşzamanlı push. | Kayıt amaçlı; indirme hatası Actions logunda. Koşu sırasında dala push yapılmaz. |

## Ağ engeli kanıtı (dosya:satır)

- Kuru yolu Etsy sınıfını kurmaz. Ağa çıkan çağrılar yalnız Etsy sınıfında: etsy_common.py:108 (token), :835, :864.
- Kuru yolunun çağırdığı fonksiyonlar yerel:
  - html_coz :343
  - metin_yasak_kapisi :356
  - beyan_var :399
  - ru_yazim_kapisi :227 (yerel CSV okur)
  - ru_poster.izin_ver :285
- etsy_common atexit rclone (:574-577) RU_BEYANSIZ_DRIVE=0 ile kapalı.
- p1_poster_kuru.ag_kapat şunları yamalar: socket.connect / connect_ex / create_connection / getaddrinfo. Her deneme sayılır; sayı > 0 ise çıkış 1.
