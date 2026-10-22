# Codex RAPOR 0009
- `pod_galeri_tamset.alt_uyarla` referans Cancer/Libra adlarini degistiriyor; 250 karakteri kesip `rstrip` yapiyor, fakat burc, tire, yazim ve yasak ifade QC'si yok.
- `pod_referans_kiyas.sablon` alt metni karsilastirma icin normallestiriyor; `pod_media` alt metin uretmiyor. Kapak betikleri sabit alt metin uretiyor ve ortak QC kullanmiyor.
- Onerilen `pod_galeri_tamset.py` yamasi: `alt` sozlugu olustuktan hemen sonra `alt_metin_kontrol.denetle(alt, c)` cagirip herhangi bir FAIL'de Etsy yazmasindan once DUR; gorev geregi bu dosya degistirilmedi.
- Bagimsiz `scripts/etsy/alt_metin_kontrol.py`, `{sira: alt}` JSON girdisini `--cift` ile denetler ve sira bazinda PASS/FAIL basar; Etsy/Drive erisimi yoktur.
- `scripts/etsy/test_alt_metin_kontrol.py` farkli/ayni burc PASS yollarini ve tum metin kurali FAIL nedenlerini kapsar.
