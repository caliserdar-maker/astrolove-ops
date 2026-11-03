# ru_poster.py "premium / long-lasting" duzeltme TASLAGI (Serdar 3 Kas A; UYGULANMADI, Etsy yazimi yok)

Yer: `scripts/etsy/ru_poster.py` ceviri tablosu, PRINT paragrafi (satir 173-176, main 3 Kas).

| | Simdi | Taslak |
|---|---|---|
| EN anahtar | `PRINT\n- Printed on premium matte art paper with long-lasting inks\nFrames shown in photos are for display only and are not included. Prints ship unframed.` | `PRINT\n- Printed on matte art paper\nFrames shown in photos are for display only and are not included. Prints ship unframed.` |
| RU deger | `ПЕЧАТЬ\n- Печать на премиальной матовой художественной бумаге стойкими чернилами\nРамы ...` | `ПЕЧАТЬ\n- Печать на матовой художественной бумаге\nРамы на фото показаны только для примера и в комплект не входят. Постеры отправляются без рамы.` |

Etki (parmak izi):
1. Tablo EN paragrafini anahtar olarak kullanir: canli EN aciklama degismeden yeni anahtar eslesmez. Bu yuzden EN aciklama ve RU sablonu AYNI parti
   ile degismeli (RU = EN ayni bilgi kurali). Gecis icin eski anahtar tabloda BIRAKILMAZ (eski EN'e yeni RU vermek bilgi farki yaratir).
2. `RU_POSTER_IZIN` kalici parmak izi tutmaz: `izin_ver` her kosuda kurulan RU metninin sha256'sini (E.ozet) yazar. Sablon degisince yeni
   RU'nun ozeti otomatik degisir; eski izinler gecersiz olur (kosu ici sozluk).
3. `onay_ozet(en, ru)` (kuru plan ozeti) EN + RU'yu kapsar: degisiklikten once alinmis kuru planlar yazimda tutmaz; yeni kuru kosu gerekir.
4. Testler: `test_ru_poster.py` / `test_beyan_marka_yaz.py` / `test_ru_olcum.py` icindeki ornek EN/RU metinleri ayni anda guncellenmeli.
5. Kapi: `metin_yasak_kapisi` UYARI modunda eski metni yazimda uyarir; ENGEL moduna gecis bu sablon + 78 poster EN/RU temizligi bittikten sonra.
