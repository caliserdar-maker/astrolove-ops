# Codex IS 0008 - canli_qc K5'i video_dogrula'ya bagla (kod yaz)
AGENTS.md kurallari. Etsy yok. main'de scripts/etsy/video_dogrula.py (dogrula API) var.
Yalniz scripts/etsy/canli_qc.py'yi degistir (pod_galeri_tamset.py'ye DOKUNMA, medya'nin).
1. K5: canli video indirildikten sonra video_dogrula.dogrula(canli, beklenen A1_77/<CIFT>/VIDEO.mp4, tuzak=baska ciftin VIDEO.mp4, poster) kullan; eski %5/%50/%95 yontemini kaldir.
2. Sonuc CSV'ye: sure_fark, ort kare farki, tuzak_orani, eski_slogan, neden.
3. Birim testi (mock indirme ile). Mevcut testler bozulmasin.
