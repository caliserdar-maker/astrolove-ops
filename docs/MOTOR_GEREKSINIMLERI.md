# AstroLoveArt Kisisel Poster Motoru: Gereksinimler ve Testler

3 Eki 2026, koordinator. Kaynak: claude/AstroLove_Siparis_Uretim_Dersleri_20261001.md (ders 1-92), Test 1-5, on testler.
Amac: Test 1-5 ve on testlerde ogrenilen her sey yeni motora kural veya otomatik test olarak tasinir; hicbiri bosa gitmez.
Durum: Serdar onayladi (3 Eki): envanter + prototip baslar. Eski sistem (siparis-dijital) prototip onaylanana kadar canli kalir.

## 1. Mimari karar
- Eski sistem: bitmis posterin uzerinde silme + kagit yama + hizalama + yazi yapistirma. Bugunku hatalarin kaynagi (dikis, cift tagline, kagit dokusu, iz, olcek).
- Yeni motor: her poster TEMIZ KATMANLARDAN sifirdan basilir: (1) yazisiz zemin, (2) seffaf sembol, (3) isim + tagline yeniden yazilir (sabit font, sabit altin/bakir efekti).
- Yapay zeka gorsel uretimi KULLANILMAZ (isimler harfi harfine kusursuz olmali).

## 2. Kurallar (derslerden)
Girdi
- Serdar yalniz verir: iki isim, hangi isim hangi burcun altinda, tagline. Isim <= 11 harf, buyuk harf; tagline <= 35 karakter, yazildigi gibi.
- Cift adi otomatik alfabetik normalize; isim1 = cift adindaki ilk burc = SOL.
- Aksanli/ozel harfler desteklenir ve test edilir: C G S I O U (CAGLAYANGUL vakasi), J K B Z F P X W Q, kucuk f c y w.
Cikti
- 5 renk PDF (MIDNIGHT_BLUE, DEEP_BLACK, PURE_WHITE, CHAMPAGNE_IVORY, WARM_PARCHMENT), her biri 5 sayfa (2x3, 3x4, 4x5, 11x14, A serisi), 300 dpi.
- Dosya/klasor adi her yerde AstroLoveArt. Olculmemis boy/dpi iddiasi musteri metnine yazilmaz.
- WARM_PARCHMENT: tum ogeler bakir (1 Eki karari). DEEP_BLACK: tagline tonu isim altiniyla esit.
- WARM_PARCHMENT bakiri = eski sistem wp_bakir rengi ve dokusu (Serdar, 3 Eki).
- WARM_PARCHMENT halkasi da bakir (Test 5'teki gibi; Serdar, 3 Eki).
Hiz
- Hedef: Serdar bilgiyi verdikten sonra en gec 15 dk, 5 PDF Drive'da (eski sistem Test 5: ~10 dk). Paralel uretim.
- Siparis sirasinda baska kosu yok; ayni anda tek buyuk dogrulama.
Kod ve surum
- Her kosuda kod surumu acik tam sha; varsayilan surum kullanilmaz.
- Test araci uretimin KENDI fonksiyonlarini cagirir. Once yerel test + cikis kodu, sonra push. Tek sahip oturum.
- En fazla 2 deneme; sonra dur, Serdar karar verir.
Kalite
- Kapilar: isim-burc dogru taraf, tagline harf harf, ust/alt hat yok, ikinci metin izi yok, renk/ton, kagit, olcek/konum.
- Kapi degisince iki yonlu test GERCEK kusurlu ornekle. Esik gevsetilerek PASS alinmaz.
- Sonuc hucre bazinda raporlanir, job success degil. Tarama araci once 1 PASS + 1 FAIL ile dogrulanir, 0 kayit = FAIL.
- Harf ici renk bandi kapisi (e) zorunlu; deneme 2 ciktisi (TEMP/MOTOR/PROTOTIP/37115656988) negatif test (Serdar, 3 Eki).
- DEEP_BLACK tagline tonu = isim altini (Serdar, 3 Eki; olc.py --mesaj-isim-tonu).
- Altin edisyonlar (MB, DB, PW, CI): plate ustune alfa bindirme; sembol rengi orijinalden olculen kanal tablosu (LUT),
  yazi dokusu orijinal kelimenin harf cekirdegi satir profili (gurultu satirlari elenir, sigma 2 yumusatma) (3 Eki).
- QC kapilari 3307 px olceginde (11x14'te kalibre); buyuk boylar BOX ile indirilir. e esigi edisyon basina: orijinallerin
  en buyugu x 1.15, en az 3.6 (motor/sabitler/E_ESIK.json). Plate halkasi (altin edisyon) b'de notr (onayli kural) (3 Eki).
- Temiz zemin bir kez: plate_temizle (tam boy) + gerekirse zemin_ek_onar (QC olceginde gorulen kosu); sha sabitlerde,
  buyuk dosyalar inceleme/motor-varlik dalinda (3 Eki).
- 78 cift (3 Eki, ADIM 3): plate halkasi ana sembol / bant olcumunden dislanir (orijinal halka plate'tekiyle birebir
  cakismayabilir); sembol oturtma NCC >= 0.80, altindaysa cift FAIL (uretilmez). QC f) sembol rengi dE <= esik
  (a-e sembol yerlesimini olcmuyordu: ilk kosuda 10 ciftte bozuk ana sembol a-e'den gecti). Yazi profili yalniz
  dikey govdeden; isim OCR psm 7/8; e profili bitisik satir parcalarinda; MB e esigi 78 orijinalden (6.12).
- Katman cizimi orijinalden farkli ciftler (AQUARIUS_LEO, AQUARIUS_TAURUS) ve ana sembol + kucuk sembol ayni bantta
  (LIBRA_LIBRA): motorla sadik uretilemez, FAIL listesinde; kaynak katman / yerlesim karari Serdar'da.
- GOZ SON KARAR: Serdar'a her renk x boy TAM SAYFA gider, kesit secilip elenmez. Gorsel suphede once Serdar.
Teslim
- Teslim ve musteri mesaji yalniz Serdar onayiyla.

## 3. Altin test seti (motor her degisiklikte otomatik kosar)
Pozitif (Serdar onayli ciktilar referans):
- Test 2 CAPRICORN_SAGITTARIUS GEORGE / MEG "Happy 5th Anniversary"
- Test 3 ARIES_VIRGO LIAM / CATHERINE "The World is Ours"
- Test 4 PISCES_SCORPIO JAKOB / ZOFIA "Perfectly Paired by Zodiac Kisses" (4 renk onayli)
- Test 5 SCORPIO_VIRGO MAXWELL / QUINN "Written in the Stars, Always Yours" (4 renk onayli; PDF klasoru Drive 1LnfDT9da1mXGlHKojdFkYsezhzJjb2n9)
- Tara CANCER_LEO TARA / ROSS "A King and his Crab" (teslim edildi)
- Isim setleri A/B (prova): A sol ismi CAGLAYANGUL; B JO / MAXIMILLIAN "Two Souls, One Bond: Forever Ours!!"
Negatif (bu kusurlar ASLA tekrar gecemez):
- Test 1 MB "To My Adorable Angel": tagline ust/alt dikis hatti
- Test 5 WP 11x14: tagline'in kaymis ikinci kopyasi
- WP sayfa 45-78 kagit dokusu farki -> yeni motorda zemin ciftin kendi temiz zemini
- DB uzun mesaj tagline tonu koyu
- Ters cift sirasi girdisi -> otomatik duzeltilmeli
Kapsam: 78 cift x 5 renk x 5 boy; aksanli isim seti dahil.

## 4. Ogrenme dongusu
- Onay sayfasi (Artifact, kalici kayit): Serdar her ciktiya isaret koyar ve not birakir.
- Isaretlenen her kusur ayni gun negatif teste, onaylanan her cikti referansa donusur.
- Kurallar tek yerde: motor skill'i + depo.

## 5. Ilk adimlar
1. Envanter (~1 sa): temiz zemin (22 Eyl kaydi: TEMP/KISISEL_PILOT/HAZIR/zemin_<edisyon>_<oran>.png), seffaf sembol, font dosyalari, altin/bakir efekt kaynagi, Canva tasarim kimlikleri. Eksik olan listelenir.
2. Prototip: 1 cift x 1 renk x 1 boy; eski sistem ciktisiyla yan yana, tam sayfa, Serdar'a.
3. Onay -> 78 cifte genisleme + altin test seti + onay sayfasi + skill.
