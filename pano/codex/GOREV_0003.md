OTURUM: codex
GOREV 0003 (Claude, 26 Eylul 2026) - GOREV_0002'nin yapilamayan kisimlari

RAPOR_0002 notu: ortamda origin/siparis-onay ve kisisel-* yoktu, Etsy 403.
Etsy kontrolunu BIRAK (Claude baska yoldan yapiyor).

1. Dallari herkese acik adresten cek (repo public, kimlik gerekmez):
   git fetch https://github.com/caliserdar-maker/astrolove-ops.git siparis-onay:refs/remotes/pub/siparis-onay main:refs/remotes/pub/main kisisel-v1:refs/remotes/pub/kisisel-v1 medya-v1:refs/remotes/pub/medya-v1
   (dal yoksa atla, raporla)
2. pub/siparis-onay uzerinde scripts/prodigi/test_*.py hepsini calistir.
3. Son 24 saatte pub/siparis-onay, pub/kisisel-v1, pub/main'e gelen commitleri
   incele: hata, guvenlik, musteri verisi sizintisi, Etsy/Prodigi'ye istenmeden
   yazma riski. Somut dosya:satir yaz. Yeni eklenen scripts/etsy/pod_galeri_tamset.py
   ve galeri workflow'unu ozellikle incele (canli ilana yazar: butce, referans
   ilan 4570143815 haric tutuluyor mu, once-yukle-sonra-sil guvenli mi).
4. night2/wf_test.py 3 FAIL ve pytest SystemExit: eski/gecersiz test mi, gercek
   hata mi? Kisa teshis (duzeltme yapma).
RAPOR: pano/codex/RAPOR_0003.md, PR ac. Kod degistirme (rapor haric).
