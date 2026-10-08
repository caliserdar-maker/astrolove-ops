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
