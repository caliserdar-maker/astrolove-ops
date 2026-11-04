# Bağımsız inceleme: PLAN_78_URETIM.md (4 Kas; işi yapmamış tek ajan, "neden yanlış, kanıtla")

| # | Bulgu | Karar | Planda |
|---|---|---|---|
| 1 | Doğru: 78/78/78 envanter, grup sayıları 23/12/12/36, jobs süreleri 71/51/116 sn, dpi/mod ölçümü, satır atıfları, CL SADE 1,5372 | - | - |
| 2 | GV süresi 227,9 sn BITTI satırı (önizleme dahil); çift 222,2 sn; sınır-1 çift 221,4 sn | DÜZELTİLDİ | §3 |
| 3 | Drive 45 dosya (46 değil); süre çağrı sayısıyla büyür; "584 dosya" kaynaksız; Drive çıkınca seri ~327 dk < 360 | DÜZELTİLDİ | §3, §8 |
| 4 | Onarımsız motor her `degisen` çiftte koşar; 6 sembol + 75 ana onarımı ölçülmedi; TAURUS hiç denenmedi | DÜZELTİLDİ (hazırlık ön ölçümü, risk) | §2, §3, §4, §11 |
| 5 | Kova "tek neden" yanlış FAIL verebilir | RİSK + ÖNERİ (Soru 6) | §7, §10 |
| 6 | CLAUDE.md:97-99 toplu üretimden ÖNCE örnek + onay; bağımsız göz kontrolü yok | DÜZELTİLDİ (önce örnek koşusu; birleştirme sonrası göz kontrolü) | §5, §9 |
| 7 | Matrix vb. yerelde test edilemez, 78 koşusu test koşusu olur; parça yeniden koşusu deneme sınırından yer; 60 sn sınırı | DÜZELTİLDİ (örnek koşusu matrix'i sınar) | §5 |
| 8 | CL her parçada Drive'a 6 kez yüklenir, OLCUM'da tekrar; parça 1 / onaylı çelişkisi | DÜZELTİLDİ (CL yalnız kontrol, tekilleştirme, Soru 2) | §4, §10 |
| 9 | Sipariş kontrolü için `actions: read` yok; koşu sırasında sipariş; eşzamanlı iş sınırı ölçülmedi | DÜZELTİLDİ (izin, Soru 7, risk) | §1, §4, §10, §11 |
| 10 | Onaylı dosyalara dpi yazmak sha kapılarını ve ONAY_COMMIT kanıtını kırar | DÜZELTİLDİ (onaylılar değişmez) | §10 Soru 4 |
| 11 | Devam: runner geçici; PNG artifact public depoda sızıntı; çöküşte koşu durmaz (ornek78.py:282) | DÜZELTİLDİ (Drive'dan devam, artifact yalnız JSON, çöküş tanımı) | §4, §6, §7 |
| 12 | yml:164 GV sınır-1 (sabit 3 çift değil); ana PNG indirme süresi | DÜZELTİLDİ | §1, §4 |
| 13 | SADE listesi onay noktasında yok (ölçülen 3/3 1,54 altı) | DÜZELTİLDİ | §9 |
