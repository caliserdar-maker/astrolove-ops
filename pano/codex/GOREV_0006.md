# Codex GOREV 0006 (Claude, 26 Eyl 2026 09:45 UTC) - canli yazan ve QC kodunun ikinci goz incelemesi

AGENTS.md Codex kurallari gecerli. KOD DEGISTIRME, yalniz rapor. Etsy/Drive yok.

## 1. scripts/etsy/pod_galeri_tamset.py (commit 6af443a)
Yeni: alt metin listing_image_id ile yeniden iliskilendirme (dosyasiz multipart), tek ilan FAIL kosuyu durdurmaz (1 onarim, sonra listeye), art arda 3 FAIL'de DUR, 429'da DUR, butce payi +25.
Bu kosu (36232637530) 7 dk icinde failure ile bitti (beklenen ~90 dk). Log okunamiyor.
- Koda bakarak en olasi 3 failure nedenini sirala (satir numarasiyla).
- Dosyasiz multipart istek Etsy uploadListingImage (listing_image_id + alt_text) ile uyumlu mu? Etsy Open API v3 dokumanina bak (internet serbest), alan adlari ve content-type dogru mu?
- Bir ilan yarida kalirsa (foto silindi, yenisi yuklenmedi) sonraki ilana gecmek ilani eksik galeriyle birakir mi? Somut senaryo yaz.
- Referans ilan (CANCER_LIBRA 4570143815) artik bilerek guncellenecek (Serdar onayi). Hedef secim yolunda CL'yi dislayan bir kosul varsa hangi satirda, ciftler=CANCER_LIBRA ile acikca istenince calisir mi?

## 2. scripts/etsy/canli_qc.py (commit 445297a)
- K2 OCR: conf>=80 kelime kurali. Kucuk gri alt satir ("PERSONALIZED ZODIAC ART PRINT / UNFRAMED") okunmadi diye FAIL uretiyor. Olcek/esik mantigini incele: yanlis FAIL ve yanlis PASS senaryolari.
- K4 leke esigi CL ayni-icerik karelerinden [8,60] araliginda turetiliyor (33.9 cikti). Bu esik gercek bir lekeyi kacirir mi? n>=5 kurali mantikli mi?
- K1 (TAM_SET 256px <= 0.001) senin RAPOR_0004 bulgunla (burc yazisi farki 0.00003) cift karisikligini yakalayamaz; canli_qc'de ayrica cift kontrolu var mi?

## 3. Metin kurali taramasi
scripts/ altinda Etsy'ye giden Ingilizce metin ureten tum dosyalarda (aciklama, alt metin, kart yazilari) CLAUDE.md "Urun metni" kuralini tara:
- yasak: OBA-free, bright white, omur yili (years), 12-colour, uzun/orta tire (— –)
- "fulfilment"/"fulfillment" ve "colour"/"color" tutarsizligi (kart 10 canli ilanda "PALETTE / FULFILMENT", onayli sette "COLOR / FULFILLMENT")
- yazim hatalari
Dosya:satir listesi ver.

RAPOR: pano/codex/RAPOR_0006.md, PR ile. Her bulguya ONEM (yuksek/orta/dusuk) yaz. En fazla 2 iterasyon.
