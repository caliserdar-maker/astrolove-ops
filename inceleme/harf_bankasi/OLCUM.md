# HARF BANKASI pilotu - olcum (MB 11x14, CANCER_LIBRA, test seti)

## 1) MB sayfa suresi: isim / mesaj render + altin payi
Kaynak: olcek-tani-siparis 36907767161 (profil renk:MIDNIGHT_BLUE:11x14, kod bfaed5d), _dijital_is cProfile altinda 120.0 sn.

| adim | cagri | sn | pay |
|---|---|---|---|
| isim plaka_ss (glif + altin, 2400 + hi-res) | 8 | 0.37 | 0.31% |
| pilot12.plaka (Blue oran referansi) | 2 | 0.13 | 0.11% |
| mesaj tagline_plaka | 3 | 0.14 | 0.11% |
| altin_isim (altin efekt, yukaridakilerin icinde) | 12 | 0.01 | 0.01% |
| **isim + mesaj + altin toplam** | | **0.64** | **0.53%** |
| ince_hiza (zemin hizalama, pilot12.olc / fark_haritasi) | 2 | 73.9 | 61.6% |
| rclone / subprocess (indirme) | 5 | 14.2 | 11.8% |
| sembol_kapisi | 2 | 10.8 | 9.0% |
| BluePoster kurulumu | 1 | 10.7 | 8.9% |

Altin efekt (pilot12.altin_isim) KELIME BOYU tek dokudur: tek dikey profil plaka yuksekligine gerilir, tum sutunlarda ayni.
Harf bazli degil -> banka yalniz glif maskesi saklar, altin dizimden sonra kelimeye uygulanir.

## 2-3) Pilot: SERDAR / LENA bankadan (Cinzel, ISIM_W 500, s4 634 = 115 x 1.3779 x 4)
- Banka: A-Z + bosluk + tire, 28 glif, uretim 0.19 sn (bir kez).
- Ilerleme: font.getlength(c) + tracking (s4 x -0.0388), onayli ciz_metin ile ayni. Cinzel GPOS 'kern' tablosu VAR
  (ornek AV: 850 vs 919 px @634) ama onayli hat cift kerning UYGULAMIYOR; banka da uygulamaz (uygularsa gorunum degisir).
- Pillow glifi s4 izgarasinda tam sayi x'e yuvarliyor (10.49 -> 10, 10.5 -> 11): banka ayni yuvarlama + Pillow BLEND.
- Sonuc: SERDAR ve LENA plakalari mevcut ile BAYT BAYT AYNI (farkli piksel 0, max fark 0); satir max fark 0.
- Olcek kapisi (banka vs mevcut): PASS, konum 0.00, kenar 0.00.
- Sure: SERDAR mevcut 0.042 / banka 0.056 sn; LENA 0.029 / 0.025 sn.

## Kesit
KESIT_mevcut_banka_fark8_MB_11x14.png: 1:1, solda mevcut | ortada banka | sagda fark x8 (tamamen siyah = fark yok).
Altin profil yerelde temsili (iki yontemde ayni; profil dizimden sonra uygulandigi icin fark sonucunu etkilemez).

## Not
Mesaj (EB Garamond Italic) mevcut yontemle kalir. Tum renk / boylara yayma Serdar onayina bagli.
