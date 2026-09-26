# Codex is kuyrugu (Claude yonetir, denetler, sorumludur)

KALICI KURAL (Serdar, 26 Eyl): Agir isin tamami Codex'e. Codex hicbir an bos kalmaz: en az 5 is calisir.
Claude: gorev yazar, her teslimi okur, diff'i uygular, test eder, gerekirse duzeltir, main'e alir, kosuyu baslatir,
sonucu denetler, bulgudan yeni Codex isi uretir. Hedef: Etsy magazasinda HER SEY hatasiz, eksiksiz, Etsy kurallarina ve SEO'ya uygun.
Teslim: PR yorumunun sonunda TAM unified diff. Etsy'ye yazan her adim Serdar kararlari dahilinde, pano "CLAUDE ONAYI" ile.

## Calisan (15:25)
- IS_0027 PR #40 tum workflow hata logu (parca 1/3)
- IS_0033 PR #46 dijital sablon (2. red; onayli kararlar docs/kararlar'da)
- IS_0035 PR #48 teslim paketi ZIP/PDF
- IS_0036 PR #49 dijital donusum uygulama araci (kuru kosu varsayilan)
- IS_0037 PR #50 SSS, iptal politikasi, siparis mesajlari

## Bulgular (15:25)
- varyasyon-canli 14:47: 43/43 PASS
- canli video/kapak: 43 yeni, 35 eski (35 cift seti yok -> video_GOREV_0018)
- canli metin (78 POD): 0 ihlal
- kisisel_uyum: 467 dijital donusum bekliyor
- ChatGPT: gorsel DNA brifi verildi (docs/chatgpt), arastirma raporu bekleniyor

## Biten
- 0002-0018, 0020-0026, 0028-0030 main'de; 0012 siparis-baski-v1; 0015 medya-v1
- 0001 PR #13: pod kuru kosu bekleniyor

## Siradaki (bulgulara gore genisler)
1. 0018-0023 bulgulari icin duzeltme scriptleri (Etsy yazma: Serdar karari + CLAUDE ONAYI).
2. Dijital 156 ilan donusumu + 312 inaktif ilan icin kuru kosu araci.
3. Musteri deneyimi: siparis sonrasi mesaj akisi, SSS/iptal politikasi metinleri (Ingilizce, tire yok).
4. Gunluk magaza saglik raporu (0018+0019+0020 ozetini tek sayfa, Drive TEMP).
