# AstroLove operasyon güvenilirlik kuralları

Bu repoda durum, tamamlanma ve "siradaki is" yanitlari icin asagidaki kurallar
zorunludur.

1. Once `python scripts/ops/state_guard.py` calistirilir. PASS olmadan durum
   raporu verilmez ve hicbir operasyon baslatilmaz.
2. "Siradaki is" yalniz `python scripts/ops/state_guard.py --next` ciktisindan
   okunur. Eski `final_summary`, runbook, sohbet ozeti veya API alan yoklugu
   durum kaniti olarak kullanilmaz.
3. Kanonik guncel durum `config/operational_state.json`; tamamlanmis islerin
   tek yonlu kilidi `config/completed_operations.json` dosyasidir.
4. Kaynaklar celisirse tahmin edilmez. Islem durdurulur, celiski ve kanit
   kullaniciya bildirilir.
5. Etsy API'nin bir alani gostermemesi, panelde alanin bos oldugunu kanitlamaz.
   GPSR gibi panel-only alanlarda elle tamamlanma kaniti esas alinir.
6. Bir is tamamlandiginda ayni commit icinde durum kaydi, tamamlanma defteri,
   kanit ve ilgili aktif runbook guncellenir; durum testi gecmeden raporlanmaz.
7. `pending_approval` canli islem yetkisi degildir. Serdar'in ilgili isleme ozel
   acik onayi olmadan Etsy, Drive, reklam veya sosyal hesapta yazma yapilmaz.


## Codex calisma kurallari (26 Eyl 2026, Serdar karari)

Codex, Claude'un koordine ettigi ek calisandir. Isi Claude verir, son kontrolu
Claude yapar. Serdar yalniz claude.ai sohbetinde konusur; ona soru sorma,
belirsizligi rapora yaz.

1. Gorevler: Google Drive `ASTROLOVE/TEMP/GOREV_PANOSU` klasorunde
   `codex_GOREV_NNNN.md` (en yuksek numara gecerli). Rapor: ayni klasore
   `codex_RAPOR_NNNN.md` (gorevle ayni numara). Drive'a erisemiyorsan raporu
   PR aciklamasina yaz ve "Drive erisimi yok" diye belirt.
2. Yalniz `codex/` ile baslayan kendi dallarinda calis, PR ac. `main`'e ve diger
   oturumlarin dallarina (siparis-*, pod-*, medya-v1, kisisel-*, dijital-v1,
   video-v1) push YOK. Force-push, gecmis yeniden yazma, dal silme YOK.
3. Repoya musteri adi, adresi, e-postasi veya Etsy receipt no YAZMA. Test verisi
   sahte olsun.
4. Etsy, Prodigi, Drive'a yazma ve Actions canli modu yalniz gorevde acikca
   yaziliysa yapilir.
5. Ayni is icin en fazla 2 iterasyon; sonra dur ve raporla. Gorsel ve video
   sonuclarini Serdar onaylar; "onayli" diye raporlama.
