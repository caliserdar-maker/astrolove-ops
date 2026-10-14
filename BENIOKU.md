# Bizim Yilimiz (Paper Anniversary): uretim paketi

Hazirlayan: Takip sohbeti (https://claude.ai/code/session_01QKBw5eacaXipRDept3xmCM), 14 Eki 2026. Serdar onayli: 5 stil, kart, galeri, 78 ilan metni.
Sartname: proje dokumani claude/AstroLove_BIZIM_YILIMIZ_PAPER.md (en ust bolum).

## Icerik
- kod/by_poster.py: 8x10 poster, 2400x3000, 300 dpi, 5 stil (1_Starlit, 2_Timeless, 3_FirstPage, 4_Layers, 5_Botanical).
- kod/by_kart.py: 5x7 kart, 1500x2100, 300 dpi, ayni 5 stil (by_poster malzemelerini kullanir).
- kod/by_galeri.py + by_galeri_render.py: cift basina 10 galeri gorseli, 3200x2400 (ornek isim EMMA / JAMES).
- kod/uret_hepsi.py: 78 cift icin hepsi + kontak sayfalari (ETA sayaci var).
- ilan78.py + BIZIM_YILIMIZ_78_ILAN_METIN.csv: 78 ilanin basligi, 13 etiketi, aciklamasi (Serdar onayli; tire kontrolu kodda).
- kaynak/ana/<cift>_alfa.png: 78 ORIJINAL birlesik sembol alfasi (siparis-gpt motor_gpt/girdi78/ana ile ayni). kaynak/KUCUK_1/2.png: burc isaretleri (motor ile ayni kutular). kaynak/yerlesim78.json: canli posterlerdeki goreli sembol boyu.
- z/: ChatGPT poster zeminleri + Olculer.json + altin dokulari. kart/: kart zeminleri + Olculer_5x7.json. galeri/: galeri zeminleri + gallery_layout.json + fontlar. fonts/: poster/kart fontlari (Google Fonts, OFL).

## Calistirma
```
pip install numpy opencv-python-headless pillow   # Pillow raqm (libraqm) gerekli: kerning
BY_ROOT=$PWD python3 kod/uret_hepsi.py CANCER_LIBRA        # tek cift
BY_ROOT=$PWD python3 kod/uret_hepsi.py                     # 78 cift (~45 sn/cift, 2 cekirdek)
```
Musteri dosyasi (siparis): `BY_ROOT=$PWD PAIR=CANCER_LIBRA NAME1=SERDAR NAME2=LENA DATE="12 JUNE 2025" LINE="YEAR ONE" python3 kod/by_poster.py` (ve by_kart.py). NAME1 = cift adindaki ILK burcun (soldaki) ismi. Cikti: cikti/<CIFT>/poster|kart.
Ust satir "Our First Year" secenegi ve stil secimi icin tek dosya uretimi henuz parametre degil (siradaki is).

## Kurallar (degismez)
- Birlesik sembol ve burc isaretleri sekilleri DEGISMEZ; yalniz orantili kucultulur (INTER_AREA).
- 5 stil ChatGPT tasarimidir, degistirilmez. "&" her zaman duz (italik & yok).
- Ingilizce metinlerde uzun tire yok. Galeride "Lena & Serdar" imzasi YOK, aciklamada imza YOK.
- Mevcut 78 canli ilana dokunulmaz. Etsy'de YAYIN YOK; once 1 taslak, Serdar onayi.

## Bilinen sinirlar
- Zeminler ChatGPT'den kucuk geldi (1120x1400, kart 1060x1484, sahne 1448x1086), Lanczos ile buyutuldu. 8x10 ve 5x7 icin yeterli; 16x20 ve ustu icin buyuk zemin gerekir.
- Uzun isim (11 harf) iki isim birlikte kuculur; 20 karakterlik kisa satir sigar (14 Eki testleri: AQUARIUS_AQUARIUS, ARIES_CAPRICORN, SAGITTARIUS_SCORPIO, CHRISTOPHER / ALEXANDRA).
- Cok uzun/genis semboller canli posterdeki goreli boyla olceklenir, kutu sinirina kirpilir (yukseklik x1.10, genislik x1.30). 78 kontak sayfasi gozle kontrol edilmeli.
