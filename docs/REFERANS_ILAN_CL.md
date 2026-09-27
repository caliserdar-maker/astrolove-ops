# Referans ilan: Cancer–Libra (4570143815) — yapı v3 (27 Eyl 2026)

Amaç: CL eksiksiz bitince aynı yöntem ve kodla kalan 77 POD ilanına geçmek. Bu belge tek kaynaktır.

## Kararlar (Serdar, 27 Eyl 2026)
| Konu | Karar |
|---|---|
| Mağaza | 78 ilan; 390 dijital ilan pasif (Serdar elle), 78 wallpaper pasif, wallpaper ürünü bırakıldı |
| Menü (3 varyasyon) | 1 "Digital File, Print or Framed?" (özel property 514): Digital File / Print / Antique Gold Frame / Black Frame / White Frame / Natural Frame (Prodigi Classic; 8 rengin hepsi ayni fiyat, US) · 2 "Primary color" (200): 5 renk + "All 5 colors (Digital)" · 3 "Size" (513): 16 boy, canlı etiketler |
| Dijital | 9.99, her boyda; yalnız "All 5 colors (Digital)" ile açık; 5 PDF (renk başına, her biri 5 oran) Etsy Messages ile, 24 saat içinde, her gönderim Serdar onayıyla |
| Baskı | Hahnemühle Photo Rag 308 gsm (GLOBAL-HPR-<boy>); fiyat = max(mevcut, Standard kargoda net 10 $) |
| Çerçeveli | Prodigi Classic Frame GLOBAL-CFP-<boy>, EMA 200 gsm, Perspex, paspartusuz; Antique Gold/Black/White/Natural aynı fiyat; net 10 $. Aluminium Gold ABD'de yalnız 8x10, 18x24, 24x36 (kullanılmıyor) |
| Kargo | Standard (US lab); çerçevelide Budget = Standard |
| Paket eki | Kartpostal + sticker kalır (maliyete 5 $ dahil) |
| Görseller | Kapak, video, kart DNA'sı kalır; yalnız dijital/çerçeve geçiş kartları (ChatGPT üretir, Claude denetler) |
| Hediye vurgusu | Tüm kart ve metinlerde |
| Metin kuralı | Uzun/orta tire yok; yasak: OBA-free, bright white, ömür yılı, 12-colour, instant download; çerçevelide Hahnemühle/cotton yok |
| Başlık | `{A} and {B} Personalized Zodiac Couple Wall Art` (CL: Cancer and Libra ...) |
| Açıklama | `data/pod/aciklama_v3_sablon.txt` + `data/pod/burc_tarih.csv` ({A},{B},{A_TARIH},{B_TARIH}); Prodigi adı yazılmaz; ABOUT US yok; COLORS/SIZES yalnız görsele yönlendirir |
| Etiketler | `data/pod/etiket_v3.txt` (Serdar onayı 27 Eyl): {CIFT} + zodiac couple print, astrology couple art, zodiac wall art, astrology wall art, personalized couple, custom couple gift, zodiac gift, anniversary gift, engagement gift, wedding gift couple, newlywed gift, giclee print. Çift etiketi 63 çiftte "a and b", 13'te "a b", 2'de yedek "astrology lover gift". 1 Oca-14 Şub: newlywed gift → valentines day gift. Araştırma: docs/arastirma/AstroLove_Etiket_Arastirma_20260927.md |
| Önizleme | Her baskı/çerçeveli siparişte: sipariş + en geç 24 saat içinde Etsy Messages ile önizleme (gönderen Serdar); onay gelince hemen baskı; önizlemeden 24 saat sonra cevap yoksa olduğu gibi baskı. Dijitalde ayrı önizleme yok (dosya 24 saatte gider, hata ücretsiz düzeltilir) |
| Süre (Prodigi kaynaklı + pay) | Üretim ABD baskı 24-72 sa, çerçeveli ≤96 sa → "5 iş günü içinde"; ABD Standard 4-6 iş günü → "5-8 iş günü"; takip: ABD içi ve tüm çerçeveliler. Etsy hazırlık süresi önerisi 4-7 iş günü (Etsy yazımı, onay bekliyor) |
| Paketleme (Prodigi) | Baskı: ipek kâğıt + kalın karton tüp (Avrupa'ya A4 ve altı sert zarf); çerçeveli: köşe koruma + ön karton + ağır hizmet kutusu |
| Çözünürlük | Dijital 5 oran 300 dpi: 16x20, 18x24, 24x36, 11x14, A2 (üretim kodu); yayından önce gerçek PDF'te ölçülecek |

## Fiyat tablosu (USD)
| Boy | Print | Frame (4 renk) |
|---|---|---|
| 8x10 | 47.99 | 95.99 |
| A4 | 48.99 | 97.99 |
| 11x14 | 51.99 | 98.99 |
| 12x16 | 53.99 | 101.99 |
| A3 | 56.99 | 107.99 |
| 12x18 | 57.99 | 107.99 |
| 16x20 | 60.99 | 112.99 |
| 16x24 | 61.99 | 115.99 |
| A2 | 62.99 | 117.99 |
| 18x24 | 66.99 | 121.99 |
| 20x30 | 84.99 | 142.99 |
| 24x30 | 94.99 | 148.99 |
| A1 | 99.99 | 157.99 |
| 24x32 | 99.99 | 148.99 |
| 24x36 | 109.99 | 164.99 |
| 30x40 | 139.99 | 197.99 |

Maliyet kaynağı: Drive `TEMP/PRODIGI/KATALOG/CERCEVE_KATALOG.csv` (27 Eyl, US, Standard). Etsy kesintisi (KDV dahil) ≈ 0.698 + 0.2062 × fiyat; Offsite Ads hariç.

## SKU şeması v3
- Renk SKU'da YOK. `POD-<S1>_<S2>-<BOY>` (baskı), `...-<BOY>-F<GO|BK|WH|NA>` (çerçeve; GO = Antique Gold, b235826), `...-<BOY>-DIGITAL`.
- Renk siparişteki "Primary color" varyasyonundan okunur: `scripts/etsy/pod_sku.py::parse_tx`. Renk yoksa/bilinmiyorsa kalem gönderilmez (fail-closed).
- Eski renkli SKU'lar (`POD-CAN_LIB-MB-8x10`) aynen çalışır (77 ilan geçene kadar).
- `sku_on_property = price_on_property = [format, size]` → Etsy ürün sınırı 2500 (CL: 576 ürün, 416 açık; 6 format × 6 renk × 16 boy).

## Kod ve iş akışları
| Parça | Dosya / workflow |
|---|---|
| Menü + fiyat verisi | `data/pod/yapi_v2.csv` (mod 3, 96 satır) |
| İlan yazıcı | `scripts/pod/ilan_yapi_v2.py` (`kuru` / `yaz --confirm YAPI_V2`), `.github/workflows/ilan-yapi-v2.yml`; canlı okuma → plan → REFERANS kontrolü (fiyat tablosu + SKU v3; değilse DUR) → PUT → tam geri okuma → renk-görsel onarımı + geri okuma → açıklama PATCH yalnız `--aciklama` ile (varsayılan KAPALI; v3 açıklama pod-seo-v3) → geri okuma (başlık/etiket/açıklama/görsel/video değişmedi); ilk hatada DUR; active değilse dokunmaz |
| Çerçeve eşlemesi | `data/pod/prodigi_cerceve_esleme.csv` (16 boy × BK/WH/NA → GLOBAL-CFP-<boy>) |
| Sipariş yönlendirme | `scripts/prodigi/order_router.py` (parse_tx, Standard varsayılan, dijital asla Prodigi'ye gitmez) |
| Kişisel sipariş kartı | `scripts/prodigi/kisisel_siparis.py` (yeni SKU + renk varyasyonu) |
| Testler | `scripts/prodigi/test_sku2_renk.py`, `test_cerceve_esleme.py`, `test_dijital.py`, `scripts/pod/test_ilan_yapi_v2.py` |
| Prodigi katalog | `scripts/prodigi/cerceve_katalog.py` (prodigi-quote.yml mode=cerceve_katalog, salt okuma) |
| Çerçeve kartı (kod) | `scripts/pod/cerceve_kart.py` (Prodigi ölçüleri: yüz 20 mm, derinlik 22 mm) |
| ChatGPT paketi QC | `scripts/pod/chatgpt_paket_qc.py`, `.github/workflows/chatgpt-paket-qc.yml` (boyut, tasarım birebir NCC ≥ 0.90, metin kuralı, karakter sınırları) |
| Satış varyasyon verisi | `scripts/etsy/varyasyon_satis.py` (salt okuma) |

## CL adımları (sıra)
1. [x] Prodigi katalog + fiyat (27 Eyl)
2. [x] Yapı v3 + SKU v3 + router + testler
3. [x] CL kuru koşu PASS (85 eski → 480 yeni)
4. [ ] ChatGPT paketi (kartlar + metinler) → `TEMP/CHATGPT_CL/` → QC PASS → Serdar onayı
5. [ ] CL yazım: envanter (ilan-yapi-v2 yaz), görseller, açıklama/etiket, "All 5 colors" varyasyon görseli
6. [ ] Canlı kontrol + Serdar onayı
7. [ ] 77 ilan: 03:00 TR (00:00 UTC kota yenilenince) otomatik, ilk hatada DUR, sabah rapor

## Açık konular
- Warm Parchment kişisel dosya: kağıt dokusu sembolün üstüne biniyor (Codex IS_0047, PR #60). Düzelene kadar dijital paket 4 renk + WP elle.
- Etsy "Primary color" (200) için özel değer "All 5 colors (Digital)" ilk gerçek yazımda doğrulanacak (PUT atomik; red gelirse ilan değişmez).
