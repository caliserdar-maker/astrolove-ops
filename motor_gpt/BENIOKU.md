# motor_gpt: kisisel siparis posteri, yeni yol (8 Eki 2026)

Onayli 78 poster ile ayni sonuc: ChatGPT ana sembol katmani + motor (isim, tagline, kucuk semboller, sonsuz, cember, zemin)
+ renk_uyum (ogeler ana sembolun altinina, dE00 <= 1). ChatGPT/OpenAI gerekmez.

- Katmanlar Drive: ASTROLOVE/ANA_SEMBOL78_KATMAN_20261008 (1ZQGR0fI0HQNq1D2Lbmr2qlkNVbD8jRyD), sha256: KATMAN_MANIFEST.json
  - <CIFT>_ana.png (RGBA: ChatGPT yuzeyi + alfa), <CIFT>_ana.png.json (konum), <CIFT>_std_alfa.npz (standart yerlesim)
  - ek/SCORPIO_VIRGO_T5_FAIL_tam.png (uret_tam.py bu dosyayi acar; yildiz=refkopya ayarinda degeri kullanilmaz)
- Uretim: siparis_uret.py CIFT ISIM1 ISIM2 MESAJ_B64 KATMAN_PNG IS_KLASORU
- Kapilar: siparis_kapi.py IS_KLASORU REFERANS_POSTER (a ana ayni, b dE00, c isim-burc, d yazim, e dikis);
  bilinen PASS + FAIL dogrulamasi: kapi_dogrula.py -> kapi_dogrula.json
- Actions: .github/workflows/siparis-gpt.yml (motor_gpt /home/claude/blender'a baglanir; yollar yerel ile ayni)
- Paket surumleri: numpy 2.5.3, opencv-python-headless 5.0.0.93, pillow 12.3.0, scipy 1.18.1, scikit-image 0.26.0, potracer 0.0.4
- Katman cikarimi (yeniden gerekirse): katman_cikar.py (gpt_birlestir2.py KATMAN_YOL modu)

## & isareti (8 Eki 2026, Serdar onayi)
- Tagline'daki "&" artik "and" olmaz; her & ChatGPT & isaretiyle dizilir (amp/AMP_ALFA.png 16 bit + AMP_YUZEY.png, sha256 AMP_MANIFEST.json).
- 35 karakter siniri musterinin yazdigi metne uygulanir.
- Boy: & murekkep yuksekligi = ayni puntoda "A" buyuk harf yuksekligi. Aralik: & yerinde "and" olsaydi komsu kelimelerle olacak
  murekkep bosluklarinin ortalamasi (onayli ornek: Forever and Always 58/51 -> 54 px). Taban ortak. Birden cok & desteklenir.
- Motor & alfasini harflerle ayni cizer (golge, parilti); ChatGPT yuzeyi renk_uyum icinde (AMP_JSON) ayni alfayla bindirilir,
  rengi yalniz ortalama Lab kaydirmasiyla ana ortancasina. Tek JPEG kaydi (ikinci kayit ana farkini 0.341 -> 0.487 yapiyordu).
- Kapi d: & iceren tagline bagimsiz cizilir (ayni & alfasi). Kapi f: her & icin IoU >= 0.90, leke, dE00 <= 1.

## Etsy teslim dosyasi (8 Eki 2026, Serdar onayli B q97, ders 199)
- Cikti: AstroLoveArt_<Burc1>_<Burc2>_7200x10800.jpg (musteriye giden) + AstroLoveArt_<Burc1>_<Burc2>.jpg (q100 ana kopya). Ikisi de 300 dpi.
- Teslim: 7200x10800, 4:4:4, TPDF titresim (genlik 0.5) yalniz koyu zeminde (oge alfasi 0), mozjpeg 4.1.1 q97 -sample 1x1 -optimize -progressive,
  JFIF yogunlugu yerinde 300 dpi (teslim_jpg.py). ~17 MB (< 20 MB, Etsy "Complete order" siniri).
- bin/cjpeg-mozjpeg-4.1.1: mozjpeg 4.1.1 kaynaktan derlendi (libjpeg statik, glibc >= 2.34), sha256 8e256d4e665b5147dab2486700e91ad0e451c67ca4b8a0dbe4122c8002a0dbfc.
- Kapi g: < 20 MB, 7200x10800, 4:4:4, dpi 300 (teslim + ana), halka <= 0.075 (onayli B q97 0.066; bilinen bozuk Pillow q95 0.093).
