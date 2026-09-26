OTURUM: codex
GOREV 0004 (Claude, 26 Eylul 2026) - CANLI YAZAN KODUN INCELEMESI (acil, salt okuma)

Bu kod SU AN canli Etsy ilanlarina galeri yukluyor. Yalniz main'deki son hali incele,
kod DEGISTIRME. Somut dosya:satir yaz, oncelik sirasiyla.

1. scripts/etsy/pod_galeri_tamset.py (commit 57c1843, 54c47cc):
   a) Yeni icerik karsilastirmasi (gri, 256px, ortalama piksel farki, esik
      0.004): galeri kartlari ciftten cifte yalniz kucuk yazi ile ayrilir. Farkli
      bir kart "ayni" sayilip ilanda yanlis foto kalabilir mi? Esik guvenli mi?
      Sentetik test yap: ayni kart sablonu, yalniz burc adi yazisi farkli iki
      goruntu uret (Pillow ile), olculen farki yaz.
   b) onar/yukle modunda silme mantigi: yanlis fotoyu silme ya da dogru fotoyu
      silme riski var mi? Referans ilan 4570143815 her yolda haric mi?
   c) Butce: ilana baslamadan kalan butce kontrolu var mi, kota tabani var mi?
2. .github/workflows/pod-galeri-tamset.yml: yanlis tetiklemeye karsi koruma.
3. plate-uret workflow + ilgili script (commit e989927, e588889): --sadece
   argumani onayli edisyonlari (PURE_WHITE, BLACK, BLUE) gercekten koruyor mu?

RAPOR: pano/codex/RAPOR_0004.md, PR ac. Her bulgu: ciddiyet (YUKSEK/ORTA/DUSUK),
dosya:satir, somut senaryo, onerilen duzeltme (tek cumle).
