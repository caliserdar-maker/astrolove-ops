# Kupa üretim paketi (17 Ekim 2026)

Onaylı kupa ilanı (Printful White Glossy Mug, 11 oz / 15 oz) için galeri ve video üretimi.
Kayıt ve kararlar: claude.ai proje dosyası `claude/AstroLove_KUPA_STIL_ONAY_20261016.md`.
Doğrulama (17.10.2026): bu klasördeki kod ve dosyalarla 7 kapak, tek kupa, yakın plan, 5 kart ve video onaylı çıktılarla birebir aynı üretildi (fark 0).

Örnek isimler: Emily & James (Cancer · Libra). Bu depo herkese açık: token, müşteri verisi, kişisel isim yok.

## Klasörler
- `kod/`: betikler (aşağıda)
- `sahne/kapak/`: 7 stilin Canva AI kapak sahnesi (2576x2576, iki boş kupa; sol = ön yüz, sağ = arka yüz)
- `sahne/tek/`: tek kupa ön/arka sahneleri (eşitlenmiş, `esit_NN_on/arka.jpg`)
- `sahne/yakin/`: yakın plan sahneleri (kapak sahnesinden `yakin.py` ile kırpılmış)
- `geo/`: silindir geometrisi `[xl, xr, yt, yb, et, eb]`; "sol" = ön yüz, "sag" = arka yüz. `ortu_*.npy`: kupanın önündeki nesne maskesi (Aegean kapakta kullanılır)
- `font/`: Cinzel, EB Garamond, EB Garamond Italic (SIL Open Font License)

Baskı dosyaları (11 oz 2700x1050, 15 oz 2700x1140) bu dalda `tasarim/` klasöründe.

- `susleme/`: 7 stilin süs görselleri (22 PNG; `kupa_7stil.py` girdisi)
- `sembol/CANCER_LIBRA/`: sembol maskeleri (ana, sol, sag, sonsuz, halka_ring, halka_sembol). Diğer çiftler: Midnight Blue posterinden `python3 kod/sembol_cikar.py <poster> sembol/<CIFT> sembol/CANCER_LIBRA/sonsuz.png` (yeniden çizim yok).
- Doğrulama: `python3 kod/kupa_7stil.py sembol/CANCER_LIBRA font susleme <cikti>` 7 baskı dosyasını `tasarim/` ile birebir aynı üretir (Emily & James varsayılan).

## Komutlar (NN = 01..07; stil adları: 01_Botanical 02_Gold 03_NazarBond 04_RoseRibbon 05_PromiseLine 06_AegeanTile 07_Mediterranean)
Baskı dosyası (çift başına, 7 stil):
`python3 kod/kupa_7stil.py sembol/<CIFT> font susleme <cikti>`
Ortam: `CIFT='{"isim1":"Emily","isim2":"James","burc":"CANCER · LIBRA"}'`, `MESAJ='...'`, `YALNIZ=04` (tek stil).

Kapak (galeri 1, 3-8):
`python3 kod/kapak_canva.py sahne/kapak/sahne_NN.jpg <baski_2700x1050.png> geo/kapak_NN.json KAPAK_NN.jpg`
Aegean: sona `geo/ortu_06_AegeanTile.npy` eklenir.

Tek kupa (sosyal medya): `SABIT_YUKSEKLIK=1 python3 kod/kapak_canva.py sahne/tek/esit_NN_on.jpg <baski> geo/tek_NN_on.json TEK_NN_on.jpg` (arka için `_arka`).

Yakın plan (galeri 9): `SABIT_YUKSEKLIK=1 python3 kod/kapak_canva.py sahne/yakin/yakin_NN.jpg <baski> geo/yakin_NN.json YAKIN_NN.jpg`
Yeni yakın sahne: `python3 kod/yakin.py sahne/kapak/sahne_NN.jpg geo/kapak_NN.json 2.4 70 yakin_NN`

Kartlar (vurgu bordo `130,18,46`, üst başlık örn. `CANCER · LIBRA`):
- Galeri 2: `python3 kod/kart_stiller.py <KAPAK_NN_*.jpg klasoru> font "CANCER · LIBRA" KART_02_STILLER.jpg`
- Galeri 10: `python3 kod/kart_kisisel.py ../sonuc_tasarim/KUPA_04_RoseRibbon_baski_2700x1050/02_Handle_on_Left.png ../sonuc_tasarim/KUPA_04_RoseRibbon_baski_2700x1050/01_default.png font Cancer Libra Emily James "A love worth protecting" KART_10_KISISEL.jpg`
- Galeri 11: `python3 kod/kart_uzunluk.py kisa_on.jpg uzun_on.jpg kisa_arka.jpg uzun_arka.jpg font "CANCER · LIBRA" KART_11_UZUNLUK.jpg` (kısa: Mia & Leo, "Always"; uzun: Maximilian & Josephine, "Forever starts with you and me"; Rose Ribbon tek kupa çıktıları)
- Galeri 12: `python3 kod/kart_olcu.py font "CANCER · LIBRA" 130,18,46 KART_12_OLCU.jpg`
- Galeri 13: `python3 kod/kart_bakim.py font "CANCER · LIBRA" 130,18,46 KART_13_BAKIM.jpg`

Video (Rose Ribbon kapağı, 6,3 sn, 1080x1080):
`python3 kod/video_kupa.py sahne/kapak/sahne_04_RoseRibbon.jpg geo/kapak_04_RoseRibbon.json <KUPA_04_RoseRibbon_baski_2700x1050.png> KAPAK_04_RoseRibbon.jpg VIDEO_04_RoseRibbon.mp4`

Yeni sahne ölçümü: `olcum.py` / `olcum_tek.py` (geometri), `pafta.py` (kontrol paftası), `esitle.py` (ön/arka tek kupa boy eşitleme).

Gerekenler: Python 3, numpy, scipy, Pillow; video için ffmpeg.
