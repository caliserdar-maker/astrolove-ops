# WP 24x36 plate dikis adayi (inceleme, 1 Eki 2026)

Karar Serdar'da. Onarim YOK; bu klasor yalniz inceleme icindir (main'e merge edilmez).

- Aday: `VINTAGE_24x36.png` (baski boyu 7200x10800), acik dikey cizgi x 1937, y 4376-4440 (65 satir).
  Siparis dikis kapisi olcumu: sapma +12.2 luma (komsu sutunlardan acik), onayli WP 24x36 ayni yerde 0.0.
- Profil (y 4376-4440 ortalamasi, x 1922-1952):
  195.9 194.7 194.0 192.4 190.5 189.4 188.6 187.7 187.2 187.4 188.8 189.3 189.8 193.2 **201.7 205.8 205.6** 203.0
  200.5 198.8 198.1 198.1 198.0 198.1 197.6 197.0 196.7 196.6 195.6 194.6 193.6
- Dosyalar (hepsi baski pikseli, plate baski boyuna olceklenmis; tarama ile ayni koordinat):
  - `PLATE_24x36_x1837-2037_y4276-4540_1e1.png`: aday cevresi 1:1 (aday kesitte x 100, y 100-164)
  - `PLATE_24x36_x1837-2037_y4276-4540_3x.png`: ayni bolge 3 kat (en yakin komsu)
  - `PLATE_8x10_x546-746_y1092-1356_1e1.png`, `PLATE_11x14_x790-990_y1582-1846_1e1.png`: 8x10 / 11x14 plate'te
    ayni goreli merkez, ayni piksel boyu (300 dpi: ayni fiziksel alan)
  - `ONAYLI_WP_24x36_CANCER_LIBRA_x1837-2037_y4276-4540_1e1.png`: onayli WP 24x36 ayni bolge (karsilastirma)
- Uretim: `wp-dikis-tara` kosusu 36859349596 (dal claude/wp-katman-baski-60sk0s, commit 8569cce),
  `scripts/medya_v1/wp_dikis_tara.py --kesit`.
