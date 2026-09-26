# Codex is kuyrugu (Claude yonetir, denetler, sorumludur)

KALICI KURAL (Serdar, 26 Eyl): Agir isin tamami Codex'e. Codex hicbir an bos kalmaz: en az 5 is calisir.
Claude: gorev yazar, her teslimi okur, diff'i uygular, test eder, gerekirse duzeltir, main'e alir, kosuyu baslatir,
sonucu denetler, bulgudan yeni Codex isi uretir. Hedef: Etsy magazasinda HER SEY hatasiz, eksiksiz, Etsy kurallarina ve SEO'ya uygun.
Teslim: PR yorumunun sonunda TAM unified diff. Etsy'ye yazan her adim Serdar kararlari dahilinde, pano "CLAUDE ONAYI" ile.

## Calisan (13:00)
- IS_0019 PR #32 POD fiyat/SKU/envanter
- IS_0026 PR #39 onay akisi workflow baglantisi
- IS_0027 PR #40 tum workflow hata logu Drive
- IS_0028 PR #41 magaza metinleri + profil duzeltme taslaklari
- IS_0029 PR #42 dijital 390->78 donusum kuru kosu plani
- IS_0030 PR #43 gunluk magaza saglik raporu

## Kosuda / sonuclar
- varyasyon-canli 12:33: 42/43 PASS (CL FAIL -> medya_GOREV_0027)
- magaza-ayar: kargo profili processing null, about metni -> IS_0028
- tamset-77: KeyError 'blue' (TS77 listeleri yok) -> video_GOREV_0018
- gorsel-denetim, kisisel-uyum, magaza-denetim: dispatch 12:58

## Biten
- 0002-0011, 0013-0018, 0020-0025 main'de; 0012 siparis-baski-v1; 0015 medya-v1
- 0001 PR #13: pod kuru kosu bekleniyor

## Siradaki (bulgulara gore genisler)
1. 0018-0023 bulgulari icin duzeltme scriptleri (Etsy yazma: Serdar karari + CLAUDE ONAYI).
2. Dijital 156 ilan donusumu + 312 inaktif ilan icin kuru kosu araci.
3. Musteri deneyimi: siparis sonrasi mesaj akisi, SSS/iptal politikasi metinleri (Ingilizce, tire yok).
4. Gunluk magaza saglik raporu (0018+0019+0020 ozetini tek sayfa, Drive TEMP).
