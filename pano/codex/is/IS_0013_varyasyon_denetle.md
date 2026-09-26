# Codex IS 0013 - renk varyasyonu gorsel baglantisi icin bagimsiz denetci (salt okur, cevrimdisi)
AGENTS.md kurallari. Etsy'ye yazma YOK, ag cagrisi YOK. scripts/etsy/pod_galeri_tamset.py DEGISTIRILMEZ (medya duzeltiyor).
Sorun (26 Eyl): baglan() hedef listeyi mevcut variation-images kayitlarindan kuruyor; Etsy silinen gorselin kaydini da siliyor; bos listede any([])=False ve all([])=True -> POST yok, PASS. Magazada renk secince gorsel degismiyor.
Yeni: scripts/etsy/varyasyon_denetle.py
- Girdi (JSON dosyalari): inventory (GET listings/{id}/inventory ciktisi), variation_images (GET .../variation-images), images (GET .../images), SET.json (renk_gorselleri + galeri dosya->sira).
- Kural: inventory'deki Primary color property'sinin TUM value_id'leri (5 renk) variation_images'ta tam bir kez olmali; image_id galeride var olmali; image_id = SET'e gore beklenen siradaki gorsel. Bos/eksik/fazla/yanlis = FAIL, renk bazinda neden.
- Cikti: PASS/FAIL + JSON rapor, exit 0/1. Ayrica hedef_liste(): POST govdesi olarak dogru {variation_images:[...]} uretir (envanterden).
Test: scripts/etsy/test_varyasyon_denetle.py: dogru 5/5 PASS; bos liste FAIL; 4/5 FAIL; silinmis image_id FAIL; yanlis siraya bagli FAIL; property_id farkli FAIL.
Teslim: yanit yorumunun sonuna TAM unified diff (tek ```diff blogu). pano/codex/RAPOR_0013.md 5 satir.
