# Codex is kuyrugu (Claude yonetir, denetler, sorumludur)

KALICI KURAL (Serdar, 26 Eyl): Agir isin tamami Codex'e. Codex hicbir an bos kalmaz: en az 5 is calisir.
Claude: gorev yazar, her teslimi okur, diff'i uygular, test eder, gerekirse duzeltir, main'e alir, kosuyu baslatir,
sonucu denetler, bulgudan yeni Codex isi uretir. Hedef: Etsy magazasinda HER SEY hatasiz, eksiksiz, Etsy kurallarina ve SEO'ya uygun.
Teslim: PR yorumunun sonunda TAM unified diff. Etsy'ye yazan her adim Serdar kararlari dahilinde, pano "CLAUDE ONAYI" ile.

## Calisan (12:15)
- IS_0018 PR #31 tum magaza ilan denetimi
- IS_0019 PR #32 POD fiyat/SKU/envanter tutarliligi
- IS_0020 PR #33 tum gorsel kalitesi + yinelenen gorsel + kapak OCR
- IS_0021 PR #34 dijital dosya denetimi
- IS_0022 PR #35 magaza ayarlari (kargo, iade, section, partner)
- IS_0023 PR #36 SEO puani ve oneriler (cevrimdisi)

## Kosuda (sonuc denetlenecek)
- varyasyon-canli, canli-metin-tara, tamset-77 mod tam (35 cift, medya-v1 98b085c)

## Biten
- 0002-0011, 0013-0017 main'de; 0012 siparis-baski-v1 e56e78d; 0015 medya-v1 98b085c
- 0001 PR #13 siparis fail-closed: pod kuru kosu sonucu bekleniyor

## Siradaki (bulgulara gore genisler)
1. 0018-0023 bulgulari icin duzeltme scriptleri (Etsy yazma: Serdar karari + CLAUDE ONAYI).
2. Dijital 156 ilan donusumu + 312 inaktif ilan icin kuru kosu araci.
3. Musteri deneyimi: siparis sonrasi mesaj akisi, SSS/iptal politikasi metinleri (Ingilizce, tire yok).
4. Gunluk magaza saglik raporu (0018+0019+0020 ozetini tek sayfa, Drive TEMP).
