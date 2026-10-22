# Kisisel dijital ilan sablonu

Bu sablonun baglayici metin kaynagi
`docs/kararlar/DIJITAL_WALLPAPER_KARARLAR_20260925.md` dosyasidir. Basliklar,
13 etiket semasi ve Ingilizce aciklamalar degistirilmeden
`scripts/etsy/dijital_sablon.py` icinde tutulur. Yalniz `{A}`, `{B}`, `{a}` ve
`{b}` burc yer tutuculari doldurulur.

Uretici 78 burc cifti icin dijital duvar sanati ve telefon duvar kagidi olmak
uzere 156 salt-okur kayit uretir. Kisisellestirme alanlari
`pod_listing_create.py` icindeki kanonik uc sorudan alinir.

Etiketlerde `cancer gift`, `cancer zodiac gift` olur. Cift etiketi 20 karakteri
asarsa `and` kaldirilir; bu da 20 karakteri asarsa etiket atlanir. Bu nedenle
onayli karar bazi kayitlarda 13 yerine 12 etiket uretebilir.

```bash
python scripts/etsy/dijital_sablon.py
python scripts/etsy/dijital_sablon.py --pair ARIES_LEO --product wall_art
```

Arac yalniz JSON'u standart ciktiya yazar; Etsy, Drive veya baska bir uzak
servise baglanmaz.
