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

## 25 Kas 2026: GitHub temizligi, workflow arsivi (Serdar 25 Kas onayi; rapor RAPOR_GITHUB_TEMIZLIK_20261122 Grup D)

Olcut: yalniz elle tetiklenen, 2 Kas sonrasi kosmamis (GitHub API), son degisikligi 10 Kas oncesi, adi scripts/, diger workflow, config, CLAUDE.md, AGENTS.md, docs/SECRETS.md ve skill dosyalarinda gecmeyen; siparis/sosyal/pin/video/reel/ig korumasi disinda. Silme yok; geri almak icin dosya .github/workflows/ altina tasinir.

| Dosya | Eski yer | Son kosu | Neden |
|---|---|---|---|
| workflows/aktif-metin-oku.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/ayar77-kuru.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/b-temas.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/banner-birlestir.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/batch3.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/beyan-marka-yaz.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/brand-banner.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/burc-gift-yaz.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by-baski-kaldir.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by-boy-ornek.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by-ornek3.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-kapak-bordo-etsy.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-kapak-bordo.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-kapak-poster.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-kapak.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-ksa.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-say.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-taslak-kontrol.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-uret.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/by78-vitrin.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/canli-metin-tara.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/canli-metin-tarama.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/cerceve-kart-ornek.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/cerceve-ornek.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/chatgpt-paket-qc.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/chatgpt-zip.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/ci-renk-karti.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/cl-galeri-degistir.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/cl-galeri-drive.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/conf-betik-kuru.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dal-yedek-sil-p04.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/desen-uret.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/digital-audit.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/digital-desc-batch.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/digital-file-add.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/digital-pod-map.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dijital-donusum-plan.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dijital-jest-kontrol.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dijital-secenek-plan.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dijital-secenek-tek.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/dikis-kesit.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-acik-tara.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-gpt-girdi.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-kayit-yaz.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-kirp.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-log-temizle.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-ozet-kiyas.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/drive-test.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/duplicate-archive-522-apply.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
| workflows/duvar-ornek.yml | .github/workflows | 2 Kas sonrasi yok (API) | parti 1: kullanilmayan elle tetiklenen is akisi |
