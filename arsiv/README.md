# arsiv (Serdar 3 Kas, kuru kosu cevabi 4)

Kapi disindan (Etsy._call / post_file disi, dogrudan requests) Etsy'ye yazan, isi bitmis betikler. Calistirilmaz:
is akislari `.github/workflows` disinda oldugu icin tetiklenemez. Geri almak icin dosyalar eski yerlerine tasinir ve
yazim yolu once metin_yasak_kapisi + kota tabanindan gecirilir.

| Dosya | Eski yer | Son kosu | Neden |
|---|---|---|---|
| etsy/by_taslak_ac.py + workflows/by-taslak-ac.yml | scripts/etsy, .github/workflows | 38594134543 (14 Eki) | tek seferlik eski 1st Anniversary taslak acici |
| etsy/by78_yayinla.py + test_by78_yayinla.py + workflows/by78-yayinla.yml | scripts/etsy, .github/workflows | 38657190366 (14 Eki) | tek seferlik 78 yayin isi bitti |
| etsy/kupa_eski_sil.py + test_kupa_eski_sil.py + workflows/kupa-eski-sil.yml | scripts/etsy, .github/workflows | 41532594365 (2 Kas, 403) | hedef ilan panelden silindi; token'da silme yetkisi yok |
| workflows/by78-taslak.yml | .github/workflows | 38602293491 (14 Eki) | by78_taslak.py yazim yolu KAPALI (3 Kas); tetiklenirse bosuna Etsy kilidi tutardi. Betik soru seti kaynagi olarak scripts/etsy'de kalir |
