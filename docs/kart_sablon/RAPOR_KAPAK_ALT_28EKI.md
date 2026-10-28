# Kupa kapagi 4:3 alternatifleri CANCER_LIBRA orange (Merkez 28 Eki, Serdar karari): rapor

Dal kupa-kapak-alt-20261028 (main'e alinmadi), kod scripts/kapak78/kupa_kapak_alt.py, is akisi wa-kupa-kart-ornek.yml mod=kapak_alt.
Kosu 40744939463 (861ad3db) [API]; Drive TEMP/KUPA_KAPAK_ALT/20261028_182605 (6 dosya). Etsy istegi 0, toplu uretim yok.
Kaynak: [OLCUM] OLCUM.json (CI ve yerel Pillow 11.0.0 ayni sha256 6b864883), sahne pikseli 2048 kare, cikti pikseli 3000x2250.

- A URETILMEDI [OLCUM]: mevcut 4:3 kapak sahnenin 2048 px genisliginin tamamini kullaniyor (kirpim yalniz dikey). Kulpla icerik 1957 px,
  4:5 kirpim 1229 px: olcek 0,628, kuculen sahne tuval genisliginin %63'u; kulpsuz govdeler bile olcek 0,879. Yatayda sahnede piksel yok.
  Acik yorum (karar Serdar'in): kenarlari sahnenin kendi duvar / masa / kumas pikselleriyle kopyala-yama doldurmak; yasak sayildi, uretilmedi.
- B ISTENDIGI GIBI URETILEMEZ [OLCUM]: govde arasi 35 px; yalniz iki govde yan yana 1363 px > 1229; kulplarla bosluk 0 iken 1922 px, 693 px ust uste binme gerekir.
- C (mevcut kapak, bayt kopyasi): 3000x2250 PASS, kenar tek renk serit 0. 4:5 kirpim: baslik ve isimler (sol EMILY JAMES / CANCER LIBRA, sag Emily & James) icerde;
  mesaj 70 px kesik ("you"), sol govde 120 px, sag govde 128 px, sol kulp 536 px, sag kulp 531 px disarida -> FAIL. 1:1 kirpim (bilgi): yalniz kulplar (311 / 306 px) disarida.
- Not: sag kulp dis kenari golgede; esik lum > 190 ile 2001 (gradyanla ~2004-2009, inceleme). Sol isim satiri sag ucu (954) bitisik yaprak dahil ust sinir.

Bagimsiz inceleme (tek ajan) duzeltildi: isim / mesaj / govde / kulp ayri kontrol (eski "isimler kesik" yanlisti), sag kulp esigi, sol baski aykiri sutun (354 -> 377),
C bayt kopyasi, A gerekcesi, B "uretilemez" ifadesi, olcum cizimi etiketi, Pillow 11.0.0 yerel kosu, rakamlar CI ciktisindan.
Eski ilk kosu klasoru TEMP/KUPA_KAPAK_ALT/20261028_181645 (hatali isim kontrolu) duruyor; silinmedi.
