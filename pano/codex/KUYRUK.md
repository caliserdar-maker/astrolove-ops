# Codex is kuyrugu (Claude yonetir, denetler, sorumludur)

KALICI KURAL (Serdar, 26 Eyl): Agir isin tamami Codex'e. Codex hicbir an bos kalmaz: en az 5 is calisir.
Claude: gorev yazar, her teslimi okur, diff'i uygular, test eder, gerekirse duzeltir, main'e alir, kosuyu baslatir,
sonucu denetler, bulgudan yeni Codex isi uretir. Hedef: Etsy magazasinda HER SEY hatasiz, eksiksiz, Etsy kurallarina ve SEO'ya uygun.
Teslim: PR yorumunun sonunda TAM unified diff. Etsy'ye yazan her adim Serdar kararlari dahilinde, pano "CLAUDE ONAYI" ile.

## Calisan (14:30)
- IS_0019 PR #32 POD fiyat/SKU/envanter
- IS_0027 PR #40 tum workflow hata logu Drive
- IS_0031 PR #44 gorsel-denetim cikti + kisisel_uyum POD soru kurali
- IS_0032 PR #45 kisisel dijital teslim modeli (Etsy kurallari, kaynakli)
- IS_0033 PR #46 kisisel dijital ilan sablonu (78+78)

## Bulgular (14:30)
- varyasyon-canli: 42/43 PASS (CL -> medya_GOREV_0027)
- kisisel_uyum: 545 ilan; 467 dijital hala anlik indirme + kisisellestirme kapali (donusum bekliyor); POD soru kurali hatali olabilir -> 0031
- magaza-ayar: kargo profili processing null; about metni -> MAGAZA_METINLERI.md taslak (Serdar onayi)
- tamset-77: TS77 listeleri yok -> video_GOREV_0018

## Biten
- 0002-0018, 0020-0026, 0028-0030 main'de; 0012 siparis-baski-v1; 0015 medya-v1
- 0001 PR #13: pod kuru kosu bekleniyor

## Siradaki (bulgulara gore genisler)
1. 0018-0023 bulgulari icin duzeltme scriptleri (Etsy yazma: Serdar karari + CLAUDE ONAYI).
2. Dijital 156 ilan donusumu + 312 inaktif ilan icin kuru kosu araci.
3. Musteri deneyimi: siparis sonrasi mesaj akisi, SSS/iptal politikasi metinleri (Ingilizce, tire yok).
4. Gunluk magaza saglik raporu (0018+0019+0020 ozetini tek sayfa, Drive TEMP).
