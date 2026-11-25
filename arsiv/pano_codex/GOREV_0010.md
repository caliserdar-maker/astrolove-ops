# Codex GOREV 0010 (Claude, 26 Eyl 2026 09:58 UTC) - medya yeni galeri akisi incelemesi + onceki raporlarin tam metni

AGENTS.md kurallari. KOD DEGISTIRME. ONEM yaz.

## A. ONCE: onceki raporlarin tam metni
RAPOR_0006, 0007, 0008, 0009 senin dallarinda (codex/gorev-000N) kaldi, main'e gelmedi; Claude yalniz ozeti gorebildi.
Bu gorevin PR'ina o dort raporun TAM metnini de ekle (pano/codex/RAPOR_0006.md ... RAPOR_0009.md) ve yanit yorumunda her raporun YUKSEK onemli bulgularini dosya:satir ile tek tek listele.
Ozellikle: RAPOR_0006 metin kurali ihlalleri (yasak tire, Hahnemuhle yazimi) dosya:satir tam liste.

## B. scripts/etsy/pod_galeri_tamset.py (main 4e34046, medya'nin GOREV 0015 guvenli akisi)
Yeni: kur() yalniz sona ekler, ilan hic 0 fotoda kalmaz, 20 siniri, her fazda galeri okunur; onar dogru on-eki korur; alt metin yeni foto (yeniden kodlama) ile; --onar hedefli onarim; renk eslesmesi yazmadan once.
Senin RAPOR_0009 kok neden bulgunla (tekillestirme + bayat silme listesi) karsilastir:
1. Kok neden bu akista gercekten kapandi mi? Tekillestirmede donen eski listing_image_id'yi silme riski kaldi mi?
2. Yeniden kodlanmis gorsel icerik olarak ayni kaliyor mu (fark <= 0.001), ama Etsy yeni kayit aciyor mu?
3. Hata aninda ilan yarim kalirsa bir sonraki kosu devam edebilir mi?
4. CANCER_LIBRA referans dislamasi: Serdar CL'nin guncellenmesini onayladi; bu akista acikca istenince nasil acilir (tek satirlik oneri)?
RAPOR: pano/codex/RAPOR_0010.md, PR ile. En fazla 2 iterasyon.
