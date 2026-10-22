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

