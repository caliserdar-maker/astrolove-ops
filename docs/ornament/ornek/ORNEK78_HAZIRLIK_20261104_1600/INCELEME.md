# Bağımsız inceleme (F): ornament-78-uretim.yml + uretim78 + ornek78 PARCA modu (4 Kas; işi yapmamış tek ajan)

| # | Bulgu | Karar |
|---|---|---|
| 1 | uretim78.py en başta numpy/PIL import ediyor; hazırlık `parcalar`/`siparis` ve birleştirme işi pip'siz → Actions'ta ModuleNotFoundError | DÜZELTİLDİ: numpy/PIL fonksiyon içinde (gecikmeli); test: numpy/PIL engelliyken modül yükleniyor ("OK") |
| 2 | Yeni `except` CL için de geçerli: CL gövde hatasında kontrol yapılmadan sonraki çiftler PASS olarak Drive köküne gidebilirdi | DÜZELTİLDİ: CL çökerse kontrol_pass False, OLCUM yazılır, çıkış 3 (parça DUR); test: CL'de sahte hata → 3, sonraki çift işlenmedi |
| 3 | cift_sonu FAIL/PASS klasörünü gerçek boy kontrolünden önce seçiyordu | DÜZELTİLDİ: önce gerçek boy, sonra sınıflandırma; test: gerçek boy yok → 5 PNG FAIL/<CIFT>/ |
| 4a | o2_piksel totoloji (sade1 ve FİLDİŞİ girdisi aynı dosya) | ZAYIF TEST olarak işaretlendi (BEKLENEN kaynak alanı); anlamlı kısım SADE_ALTIN (dpi sonrası) = sade1 |
| 4b | drive_karsilastir sayı kıyaslamıyordu; sha yoksa kıyas atlanıyordu | DÜZELTİLDİ: RAPOR/ dışı Drive dosya sayısı = beklenen; sha yoksa FAIL; testler eklendi |
| 4c | kenar_dogrula üretimde FAIL veremez (liste aynı kaynaktan) | ZAYIF TEST olarak işaretlendi (koruma; elle bozulmuş girdide FAIL) |
| 5 | TEMP klasör ad+ID listesi, kota, Drive dosya ID listeleri dala/artifact'a giriyordu (public depo) | DÜZELTİLDİ: /tmp dışı tutuluyor; dala yalnız "boş alan >= 2 GB" (evet/hayır) ve klasör tekliği sonucu |
| 6 | Doğru bulunanlar: matrix fromJSON, max-parallel, sparse desenler, artifact yolları, rclone argümanları, dpi'nin CL kıyasına etkisi yok, Kova kodu değişmemiş, beklenen anahtarları uyumlu, süre ~60 dk/parça (tahmin) < 110 | - |
| 7 | Görev dışı: dalda 164 izlenen PNG (ONIZLEME_76mm_*, 5STIL 954'ler) public kurala aykırı | DÜZELTİLMEDİ (görev dışı; Serdar/Merkez kararı) |
