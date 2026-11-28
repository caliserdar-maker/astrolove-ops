# RAPOR D: CANCER_LIBRA galerisi yeni altin (pafta) -> DUR, Serdar / Merkez onayi

Kosu: galeri-yeni-altin `46161491148` (main d183134f, mod uret), 28 Kas 15:45-15:47 UTC, tum adimlar success (kaynak: GitHub API).
Drive cikti: `OFIS/GALERI_YENI_ALTIN/CANCER_LIBRA/46161491148/` (yeni/ tam boy 7 gorsel + OLCUM_TUM.json, HAZIRLA.json, LISTE.json, pafta/).
Dalda paftalar: `docs/standart499/kosu_46161491148/` (en cok 1600 px). Etsy'ye yazim YOK.

1. Yollar dogrulandi (LISTE.json, Drive): `POSTER_GALERI_V11/20261029_103607/CANCER_LIBRA_W01_KAPAK, W07_MB, W08_DB, W09_PW, W10_WP`
   ve `W02_W06/40879133310/CANCER_LIBRA_W02_SEMBOL, W03_KISISEL, W05_SUREC, W06_GENEL` + 8 MANIFEST + `_POSTER2000/CANCER_LIBRA.jpg`.
2. Girdi kapisi PASS (HAZIRLA.json): 7 dosyanin hepsi 3000x2250; koyu poster kutularinin olculen sinirlari pilot kutularina 0 px fark
   (W03, W06 x2, W07, W08). Not: Drive asillarinin canli Etsy gorseliyle ayni oldugu ayrica (sha / NCC) olculmedi.
3. Kutu disi piksel ayni (assert) 7/7 PASS. Islenen: W03 (r03), W06 (r06; MB, DB, PW kucuk posterler), W07-W09 (r07-r09) poster
   ogeleri + halka; W07-W10 ve W01 (r11 CI) Canva "CANCER & LIBRA" basligi (yazi 23648 px). CI / WP poster murekkebi (kahve) degismedi.
4. Gozle (1:1 yakin kirpintilar): eski altin kalintisi / hayalet yok; yeni isim ve mesaj ayni yerde. PW'deki soluk acik dikdortgenler
   eski gorselde de var (yeni islemden degil). Halka da yeni altina gecti (TUM modu; PW'de eski gumus halka -> altin).
5. IoU (bilgi; Merkez: karsilastirma gerekmez): sembol 0.73-0.88, isimler 0.29-0.58, mesaj 0.33-0.47; PW'de dusuk (sembol 0.73,
   burc 0.49-0.52, halka 0.16-0.20). Kaynak OLCUM_TUM.json.
6. Is akisi testi: temiz kopya (git archive) + `bash -eo pipefail` + sahte rclone / git; bilinen PASS 1, bilinen FAIL 4 (eksik dosya,
   yanlis boyut, gecersiz cift girdisi, sizintili JSON) beklendigi gibi; liste modunda Drive yazimi yok; test_workflows 425 YAML PASS.

Sonraki (onaydan sonra): kalan 77 cift (ayni is akisi, cift basina kosu; toplu uretim oncesi tek bagimsiz inceleme CLAUDE.md geregi),
sonra C2 (W05 karti, `wa_kupa_kart_ornek.py:83` "within 24 hours of your order" -> 12 hours).
Acik: Pillow surumu is akisinda 12.3.0 (pilotun surumu bilinmiyor). Bos dal `claude/standart-499-girdi` duruyor (silme vekilde kesildi).
