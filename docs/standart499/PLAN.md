# STANDART 4,99 USD ORNEGI: YENI ALTIN GECIS PLANI (CANCER_LIBRA, tasarim denemesi)

Gorev: Denetim-Standart (Merkez, 28 Kas 2026; KARARLAR_20261128_74/_84/_88/_89/_95/_96).
Durum: PLAN. Siparis hatti koduna dokunulmadi. Uretim YOK. Merkez karari bekleniyor (asagida "Karar").
Satir numaralari: bu dosyanin commit'i ve asagida yazilan sabit SHA'lar (main f522f5d4, motor_gpt d2b414ee,
eski renk kodu b8c8c4b1, Merkez pilotu altin-pilot-kaynak c964f94a).

## 0. A) Test on kontrolu (yerel, Pillow 13.0.0 / numpy 2.5.5 / opencv 5.1.0; is akisi surumsuz kurar)

| test | cikis kodu | sonuc |
|---|---|---|
| scripts/siparis_dijital/test_a_renk_istisna.py | 0 | SONUC PASS |
| scripts/siparis_dijital/test_plan.py | 0 | 8 test OK |
| scripts/siparis_dijital/test_sira.py | 0 | 7 test OK |
| scripts/siparis_dijital/test_tag_kerning.py | 0 | 29/29 PASS (kisisel-v1 origin'den) |

## 1. Siparis hattinda altin nereden geliyor (olcum degil, kod okumasi)

Yonlendirme (canli kisisel siparis): `.github/workflows/siparis-giris.yml:2-7` ve `:54-56` (main f522f5d4)
- MIDNIGHT_BLUE, DEEP_BLACK, PURE_WHITE -> YENI YOL: motor_gpt, GPT_REF d2b414ee (`siparis-giris.yml:54`).
- CHAMPAGNE_IVORY -> ESKI YOL: siparis-dijital, renk_ref ESKI_RENK_REF b8c8c4b1 (`:55`).
- WARM_PARCHMENT -> ESKI YOL: siparis-dijital, wp_ref 360cbef9 (`:56`).

YENI YOL altini (motor_gpt @ d2b414ee):
- Birlesik (ana) sembol: hazir ChatGPT katmani, Drive `ANA_SEMBOL78_KATMAN_20261008/<CIFT>_ana.png`
  (`motor_gpt/BENIOKU.md:6-7`); okunur `motor_gpt/siparis_uret.py:37`, alfa `:43`, posterin ustune bindirilir `:66-67`.
- Diger ogeler (isimler, mesaj, kucuk burclar, sonsuz, cember): motor `uret_tam.py`, altin paleti
  `palet/chatgpt_altin.png` (`siparis_uret.py:29`, `KILIT_GPTGIRDI.json:21`, `uret_tam.py:137-147`), sonra
  `renk_uyum.py:1-2, 51-63` ile her oge ana sembolun Lab ortancasina kaydirilir (dE00 <= 1).
- DB / PW: ayni ogeler, zemin degisir (`uret_tam.py:42`, `db_pw_uret.py`).

ESKI YOL altini (siparis_dosyasi @ b8c8c4b1, `scripts/medya_v1/siparis_dosyasi.py`):
- Sembol, kucuk burclar, halka: onayli baski dosyasi `POD_PRINT/<cift>/<renk>/<boy>.jpg` (`:22`, `:38`, `pod_kaynak :1415`);
  isim bandi PLATES ile temizlenir (`:40`, `plate :404`).
- Isimler ve mesaj: `pilot12.altin_isim` + onayli isim altin profili (`:358`, `:1643-1647`).
- Cagri zinciri: `scripts/siparis_dijital/prova.py:97` -> `surucu.py:271 renk_asamasi` -> `surucu.py:287 sd.dijital_uret`
  (`siparis_dosyasi.py:2400`).

## 2. "Yeni altin" nereden geliyor

- Merkez pilotu `scripts/altin_pilot/pin_katman.py` (dal altin-pilot-kaynak c964f94a): katmanlar
  `POSTER2000_CANCER_LIBRA.jpg` uzerinden `PosterR.layer` ile kesilir (sembol, burc_a, burc_b, isimler, mesaj, halka).
- O poster = `gecici/pin78-girdi:POSTER_CANCER_LIBRA.jpg` = Drive `TEMP/PIN_V6_20261012/_POSTER2000/CANCER_LIBRA.jpg`
  (2000x3000, MB, isimler EMILY / JAMES, mesaj "It Began With a Kiss in the Rain"; dosyayi actim).
- `_POSTER2000` uretimi: `.github/workflows/pin-v6.yml:4-6, 63-89`: Drive `POSTER78_CHATGPT_7200x10800_20261008`
  (9 Eki surumu) yalniz olceklenerek 2000x3000 yapilmis.
- `motor_gpt/BENIOKU.md:1-4`: yeni yol "Onayli 78 poster ile ayni sonuc: ChatGPT ana sembol katmani + motor".

Sonuc (HIPOTEZ, olculmedi): "yeni altin" = 8 Eki ChatGPT / motor_gpt altini. Canli MB / DB / PW kisisel siparis (yeni yol)
bu altini zaten uretiyor olabilir; eski altin galeride (17 Eki eski78 hatti) ve ESKI YOL'da (POD_PRINT + pilot12) kalir.
Dogrulama icin yeni yol ciktisi gerekir (Drive katmani; Code ortami okuyamaz).

## 3. Gorev yontemiyle celiski (DUR nedeni)

1. Gorev B "prova.py yolu" diyor. prova.py MB / DB / PW'yi ESKI YOL'dan (siparis_dosyasi, POD_PRINT) uretir
   (`prova.py:97`, `prova.yml:65, 77, 171`). Canli MB / DB / PW siparisi 9 Eki'den beri YENI YOL'dan gider. Yani prova yolu
   (a) kisisel siparisle ayni hat degil (karar _88/_89: "Kisisel siparisle ayni tasarim ve hat"), (b) buyuk olasilikla ESKI altin verir.
2. prova.py WP'yi `prova.yml:66` WP_REF adfb2b99 ile kosar; canli WP 360cbef9 (`siparis-giris.yml:56`). Farkli kod.
3. prova.py sayfa JPEG'lerini siler (`prova.py:122`), prova.yml Drive'a yalniz JSON / kesit yazar (`prova.yml:231, 332-333`).
   Tam boy STANDART_CL_ORNEK_<renk>.jpg'yi OFIS'e yazan mevcut bir main is akisi bulamadim:
   - siparis-yardimci `halka_ornek`: motor_gpt'yi sahte isimle kosar ama cift / isim / mesaj / olcu sabit (CANCER_LEO, Milo, Harper, 11x14).
   - siparis-giris: receipt ister, siparis klasorlerine yazar (gercek siparis yolu; deneme icin uygun degil).
   - drive-dosya-yukle: yalniz veri/* dali -> TEMP/DENETIM_*; OFIS degil.
   Yeni is akisi (ya da mevcut birine yeni mod) main'e girmeli -> gorev kurali geregi DUR, ayri onay.
4. CI / WP posterlerinin murekkebi kahve tonlu; Merkez pilotu da bunlara dokunmadi (`altin_pilot.py:28`,
   `pin_degistir.py:354`). Bu iki renkte "yeni altin" neyin yerine konacak, tanimsiz.
5. Isim ve mesaj katmanlari kaynak posterde EMILY / JAMES ve baska mesaj: standart metin (CANCER, LIBRA, "Two Signs, One Story")
   icin pin_degistir.py'deki gibi katman yapistirma kullanilamaz; yalniz renk / doku aktarimi olabilir (altin_pilot.py yontemi:
   parlaklik sirasini pin dagilimina esleme).
6. Cozunurluk: kaynak katmanlar 2000 px genislikten; 16x20 sayfa 4800x6000. Yapistirma 2,4 kat BUYUTME demek (pin_degistir.py
   yalniz kucultur). Tam boy kaynak Drive'da var (7200x10800).

## 4. Secenekler

A) MB / DB / PW: YENI YOL (motor_gpt d2b414ee, `siparis_uret.py` CANCER_LIBRA, isim1=CANCER, isim2=LIBRA,
   mesaj "Two Signs, One Story", OLCU=16x20, ayni kapilar `siparis_kapi.py`). Kod degisikligi yok; altin = canli siparisle ayni.
   Cikti altini `_POSTER2000` CL ile olculur (sembol ve isim satiri Lab ortanca dE00). Fark kucukse "yeni altin" zaten bu.
   CI / WP: ESKI YOL (siparis-dijital ile ayni kod, renk_ref b8c8c4b1 / wp 360cbef9), altin degisikligi yok (kahve murekkep).
   Gereken: OFIS'e tam boy yazan yeni is akisi (ya da siparis-yardimci'ye yeni `standart_ornek` modu) main'e: ayri onay.
B) Gorevdeki gibi prova / ESKI YOL + son islem: sembol, burclar, halka `_POSTER2000` katmanlariyla (pin_degistir.py yontemi,
   tam boy kaynak gerekir), isim ve mesaj parlaklik sirasi esleme ile (altin_pilot.py yontemi). Yeni kod; canli siparis hattindan
   farkli bir urun cikar (kisisel siparis ile "ayni hat" sarti bozulur). Yine OFIS icin yeni is akisi gerekir.
C) Once yalniz olcum: yeni yol ile tek MB 16x20 standart ornek + `_POSTER2000` CL altin karsilastirmasi; sonra A / B karari.

Oneri: A (ilk adimi C ile: tek MB olcumu). Gerekce: karar _88/_89 "kisisel siparisle ayni tasarim ve hat"; yeni yol canli hat;
kod degisikligi gerekmeyebilir. Bu bir oneri; karar Merkez / Serdar'in.

## 5. C) Galeri kartlari: arama

aranan (200 dalin hepsinde, `git grep -F`, *.py *.json *.md *.yml *.csv):
"Your Names, Your Message", "Digital File or Print", "Made for You, Step by Step", "within 24 hours",
"8812062435", "8764245228", "8855745013".
- "Your Names, Your Message": yalniz `scripts/kapak78/wa_kupa_kart_ornek.py` (kupa) ve `ref/kart_sablon_20261028/mock/mock_kisisel3.py`.
- "Digital File or Print": `scripts/etsy/eski78_cerceve.py`, `scripts/kapak78/yd_kart_ornek.py`, `scripts/kapak78/wa_kupa_kart_ornek.py`.
- "Made for You, Step by Step": `scripts/kapak78/yd_kart_ornek.py`, `wa_kupa_kart_ornek.py`, `sade_kart.py`.
- "within 24 hours" (poster kartlari): `scripts/pod/kart02_dijital_metin.py`, `kart05_satir.py`, `kart05v2_kur.py`, `kart11_kur.py`.
- il 8812062435 / 8764245228: yalniz `claude/sag-sag-y03:premium/POSTER_GORSEL.csv:356-357` (CL sira 3 ve 4) ve
  `altin_pilot.py` (r03). il 8855745013: hicbir dalda yok.
Bu uc canli kartin (poster ilani CL) uretim kodu kesin bulunamadi; adaylar yukarida. Kartlar B'deki posteri icerdigi icin
C, B kararindan sonra.

Ad duzeltmesi (Merkez mesaji 28 Kas 16:59, KARARLAR_20261128_98): kartlarda "Standard Digital File" / "Standard" YOK.
- C1 sirasi: 1. "Digital, No Names" (US$4.99), 2. "Personalized Digital" (US$9.90), 3. "Personalized Print" (US$24.90 - US$69.90).
  Not: son satirdaki fiyat araligi tireli; Ingilizce metinde uzun / orta tire yasak, burada yalniz duz kisa cizgi (-) kullanilir.
- C2 notu: "Digital, No Names files skip the preview".
- C3 satiri: "Or choose Digital, No Names: your two signs with Two Signs, One Story".
- C4 basligi "Personalized or Standard" bu adlarla uyumlu degil; yeni baslik Merkez'den beklenir (oneri: "Personalized or Digital, No Names").

## 6. D) 78 poster galerisi yeni altin (Merkez mesaji 28 Kas 16:57, KARARLAR_20261128_97). PLAN, uretim yok

Sira: B ve C'den sonra; once yalniz CANCER_LIBRA (eski / yeni pafta, yakin kirpinti) -> rapor -> DUR -> Merkez onayi -> kalan 77.
Etsy'ye yazim yok. Kapak ve video haric (KARARLAR_92).

Altinli galeri siralari (CL; Merkez'in aktardigi KARARLAR_74): r03, r06, r07, r08, r09, r10 ve r11 (r10 / r11 yalniz Canva basligi;
poster murekkebi kahve). r01 kapak haric. Celiski: pilotun is listesi r01'i iceriyor (`altin_pilot.py:25`); D'de r01 atlanir.
Kalan 77 ciftte siralar ayni mi: dogrulanmadi (galeri yedegi okunmadan bilinmez).

Yontem (Merkez pilotu, degistirilmeden; yollar depoya uyarlanir):
- katman: `pin_katman.py` -> `sosyal/pin_v6/pin_uret.py` PosterR + `lib.py` Poster.layer, kaynak `_POSTER2000/<CIFT>.jpg`.
- degistirme: `pin_degistir.py` tum modu (sembol, burc_a, burc_b, isimler, mesaj, halka; Canva basligi isim degradesiyle).
- Kapi (eklenmesi gereken): galeri posterindeki isim / mesaj metni _POSTER2000'deki ile AYNI olmali (katman yapistirildigi icin);
  CL'de ikisi de EMILY / JAMES (dosyalari actim). Farkli ciftte farkliysa o cift DUR.
- Olcek: galeri poster kutusu ~1040 px genis (`altin_pilot.py:25`), kaynak 2000 px: yalniz kucultme (pilot kurali korunur).
- Laptop yollari (`../logo_wt`, `pin_kaynak/`, `eski/`, `C:/Windows/Fonts/arial.ttf` `pafta.py:11-12`) depo yollarina cevrilir;
  pafta fontu Linux'ta yok, depodaki bir fontla degistirilir (yalniz pafta etiketi; urun gorseli degil).
- Poster kutulari pilotta elle olculmus (`altin_pilot.py:24-32`); 77 cift icin kutu olcumu gerekir (kapi: kutu disi assert).

Drive asil galeri dosyalari: yol DOGRULANMADI. Depoda gecen adaylar: `TEMP/POSTER_GALERI_V11/`, `TEMP/POSTER_GALERI_V11_YEDEK/`,
`TEMP/GALERI_77`, `TEMP/CL_GALERI_FINAL19`. Code ortami Drive'i okuyamaz; once salt okuma listeleme kosusu gerekir.

Is akisi: mevcut main is akislari arasinda bunu yapan yok. Yeni is akisi main'e girmeli (Drive girdi -> uretim -> Drive
`GALERI_YENI_ALTIN/<CIFT>/`): gorev kurali geregi DUR, ayri onay.

### 6.1 Durum (28 Kas, Merkez oncelik mesaji 17:52: once D, sonra C2; B / C1 / C3 / C4 BEKLER)

- Drive asillari dala alinamadi: `drive-dala-al.yml` ve `drive-onizleme-kopya.yml` ikisi de DEVRE DISI
  (API: "Cannot trigger a 'workflow_dispatch' on a disabled workflow"). Drive'dan dala dosya tasiyan etkin main is akisi yok.
  Not: drive-dala-al icin acilan bos dal `claude/standart-499-girdi` (= main f522f5d4, icerik yok) kaldi; silme istegi
  vekil sunucuda kesildi, tekrar denenmedi.
- Beklenen Drive asil yollari (kod okumasi, DOGRULANMADI): `TEMP/POSTER_GALERI_V11/20261029_103607/CANCER_LIBRA_W07_MB.jpg`,
  `_W08_DB`, `_W09_PW`, `_W10_WP`, `_W01_KAPAK` (CI karti, galeri-ci11 varsayilani ayni damga) ve
  `TEMP/POSTER_GALERI_V11/20261029_103607/W02_W06/40879133310/CANCER_LIBRA_W03_KISISEL.jpg`, `_W06_GENEL.jpg`
  (adlar `galeri_v11_dogrula.py:8`, `galeri_v11_liste.py:47-69`; damga / kosu `galeri-v11-dogrula.yml` varsayilanlari).
  Canli galeri id'leri r03, r06-r09 88120xxxxx (29 Eki v11b yuklemesi) ile uyumlu; r10 (8764250162) ve r11 (8822288409) farkli
  tarihli: o ikisinin asli baska klasorde olabilir. W05 (r05) 5-6 Kas'ta p1g_kart ile yeniden uretildi (baska kosu).
- Yontem kodu depoya uyarlandi (yeni dosyalar): `scripts/galeri_yeni_altin/katman.py` (pin_katman.py), `degistir.py`
  (pin_degistir.py; islem fonksiyonlari diff ile AYNI, yalniz yol argumanlari + baslik kapisi). Yeni kapi: tum modunda
  BASLIK_BOLGE poster kutusuyla kesisirse DUR (bilinen FAIL denendi: final19 kartinda DUR verdi; kesismeyen durumda gecer).
- YEDEK GIRDI denemesi (Drive asli DEGIL): `altin-pilot-kaynak:data/pod/cl_galeri_final19/15, 16, 17` (MB, DB, PW renk kartlari,
  3000x2250, poster kutusu olcumu 810,150,2189,1905) + `_POSTER2000` CL (`gecici/pin78-girdi`). Pillow 13.0.0 / numpy 2.5.5 /
  opencv 5.1.0 / scipy (yerel venv). 3 gorsel 13 sn, kutu disi assert PASS. IoU (yeni alfa > 0.5 / eski cekirdek):
  sembol 0.878 / 0.878 / 0.886, burc_a 0.85 / 0.855 / 0.831, burc_b 0.766 / 0.773 / 0.772, isimler 0.303 / 0.293 / 0.285,
  mesaj 0.31 / 0.322 / 0.488, halka 0.524 / 0.53 / 0.41 (kaynak: OLCUM_TUM.json). Isim / mesaj IoU dusuk: yeni isim satiri
  eskisinden biraz genis (harf araligi farki; yakin kesitte gorunuyor). Pafta: `d_yedek_girdi_deneme/`.
- Pilot IoU degerleri (canli CDN girdisi) Merkez'de; karsilastirma icin gerekli. Isim / mesaj icin esik onerilmedi (olcum yok).

### 6.2 D icin gereken is akisi (main'e girmeli -> ayri onay; yazilmadi)

`galeri-yeni-altin.yml` (workflow_dispatch; Etsy YOK, token YOK, kilit YOK): girdi `cift`, `galeri_damga`, `kart_kosu`, `mod` (kuru | uret).
1. Drive salt okuma: `_POSTER2000/<CIFT>.jpg` + yukaridaki W dosyalari (eksikse DUR; sha256 MANIFEST / KAPI.csv ile ayni olmali).
2. Kapi: boyut 3000x2250; poster kutusu pilot kutusuyla (`altin_pilot.py:24-32`) +-3 px (koyu: esik olcumu; PW: duvar / poster ayrimi).
3. `katman.py` -> `degistir.py --mod tum` (r10 / r11 yalniz baslik; r01 kapak yok) -> pafta (eski / yeni, yakin kirpinti).
4. Drive `TEMP/GALERI_YENI_ALTIN/<CIFT>/` (yeni gorseller + OLCUM_TUM.json + paftalar). Etsy'ye yazim ayri onay (toplu yazim kurali).
Pillow surumu sabitlenmeli (CLAUDE.md PILLOW kurali; pilotun surumu bilinmiyor, Merkez'den).

### 6.3 C2 (Made for You karti, 24 -> 12 hours)

Canli kart il 8855745013 (r05 = W05_SUREC). Uretim kodu adayi `scripts/kapak78/p1g_kart.py` (W05_SUREC, 5-6 Kas). Asil dosya Drive'da
(p1g_kart kosu klasoru); ayni engel: Drive girdisi icin etkin is akisi yok. Kod okumasi bir sonraki adim.
