# Urun ayar kodunu main'e alma plani (urun-ayar/kod -> main)

Denetim, 14 Kas 2026. Kapsam: yalniz plan (adim 2'nin ilk asamasi). Kod, test, is akisi ve belge bu asamada DEGISMEZ; test kosulmadi.
Serdar onayi: 14 Kas "Ok" (Genel Merkez: urun ayar kodunu main'e alma plani). Kod asamasi ayri gorev metni ve ayri onayla gelir.
Ref adlari: 322e066 = urun-ayar/kod (tek commit, taban b82f2ec); 102d0c52 = main (S13 CSV'si dahil); 4857c67 = plan/urun-ayar (ana plan).
Her atif "ref:dosya:satir" bicimindedir. Sha degerleri on ek olarak yazilir; tam degerin kaynagi yanindadir (gizlilik taramasinin
Drive ID deseni 64 haneli sha'lari da yakaliyor).

## 1) Rebase plani ve merge-tree sonucu

- Olcum (14 Kas, sig klon --depth 25): git merge-base origin/main origin/urun-ayar/kod = b82f2ec. b82f2ec..102d0c52: 21 commit,
  47 dosya. b82f2ec..322e066: 6 dosya (M .github/workflows/ornament-taslak.yml, A docs/urun/ornament78/URUN_AYAR.json,
  M scripts/etsy/ornament_taslak.py, M scripts/etsy/test_ornament_taslak.py, A scripts/etsy/test_urun_ayar.py, A scripts/etsy/urun_ayar.py).
  Ortak dosya yok.
- git merge-tree --write-tree 102d0c52 322e066: cikis 0, tek satir (agac eef2f36), cakisma yok. Metin cakismasi yok ama
  davranis cakismasi var (madde 2, 3, 4).
- Yontem: yeni tam gecmisli klonda `git checkout -B urun-ayar/kod 322e066; git rebase 102d0c52` (cakisma varsa DUR). Ardindan
  madde 2-5 degisiklikleri AYRI commit(ler) olarak eklenir (rebase edilen commit'in yamasi `git range-diff b82f2ec..322e066
  102d0c52..HEAD~n` ile birebir gosterilir). Dala push: urun-ayar/kod force-with-lease (beklenen eski uc 322e066) ya da yeni dal
  urun-ayar/kod-main (karar gorev metninde; oneri: yeni dal, eski dal iz olarak kalir).

## 2) metin_kontrol uyumu

- Imza degisikligi: 322e066:scripts/etsy/ornament_taslak.py:292 `def metin_kontrol(row, A)` (102d0c52:scripts/etsy/ornament_taslak.py:253
  `def metin_kontrol(row)`). Yeni surum A'dan galeri sayisini (322e066:...ornament_taslak.py:295-297, galeri :69-70) ve stil adlarini
  (322e066:...ornament_taslak.py:320-322, stiller :64-66) okur; eski surum sabit 11 alt sutun (102d0c52:...ornament_taslak.py:256)
  ve STILLER sabiti (102d0c52:...ornament_taslak.py:278-280).
- Cagri yerlerinin TAM listesi (git grep "metin_kontrol", *.py ve *.yml, iki ref; kupa_ru / kupa_taslak / takvim_plan /
  takvim_v2 / alt_metin_kontrol / magaza_metin_kontrol ayri fonksiyonlardir, ornament_taslak'i cagirmaz):
  - 322e066:scripts/etsy/ornament_taslak.py:461 `metin_kontrol(metin_satiri(pair), A)` (rebase sonrasi yerinde kalir).
  - 322e066:scripts/etsy/test_urun_ayar.py:440 `dur(T_.metin_kontrol, r2, k.A)`.
  - 102d0c52:scripts/etsy/ornament_metin_canli.py:140 `ornament_taslak.metin_kontrol(r)[-1]` (S13; A vermez). Rebase sonrasi
    TypeError olusur ama 102d0c52:ornament_metin_canli.py:246 genel `except Exception` ile yutulur; test_ornament_metin_canli
    KeyError 'yeni_zorunlu_cumle' ile rc=1 verir (bagimsiz inceleme olcumu, merge-tree agaci eef2f36 git archive kopyasi, ag kapali).
  - 102d0c52:scripts/etsy/test_ornament_metin_canli.py:177, :230 metin_kontrol'u betik uzerinden dolayli kullanir (yeni cagri yok).
- Secilen yol: A varsayilani. `def metin_kontrol(row, A=None)`; govdenin basinda `A = A if A is not None else ayar()`
  (322e066:...ornament_taslak.py:59-61 ayar(): UA.yukle, URUN_AYAR ortam yolu yalniz kuru/test).
  Gerekce: (a) S13 araci main'de, testli ve canli kosusu yapilmis (43556659999); dokunulmazsa yeniden test / inceleme / CI zinciri
  acilmaz; (b) ayar() zaten modulun tek ayar kaynagi; S13 calisma aninda depodaki URUN_AYAR.json'u yukler (S13 is akisi URUN_AYAR
  ortam degiskeni vermez); (c) taslak yolu (:461) A'yi acik verir, davranisi degismez.
  Alternatif (S13 cagrisina A) reddedildi: 102d0c52:ornament_metin_canli.py'ye urun_ayar bagimliligi ve yeni test gerekir.
- Davranis farki (olculecek, madde 6): yeni surum stil adlarini A["varyasyon"]["menu"]'den alir; S13 yeni CSV'sinde eski surumle
  metin_kontrol hatasi 0 (S13 OZET yeni_metin_kontrol_hata 0); yeni surumle olculmedi. Kod asamasinda 78 satir icin iki surum
  karsilastirilir; fark varsa DUR.
- Ek test (kod asamasi): test_ornament_metin_canli.py rebase sonrasi da PASS (51/51; inceleme olcumunde A=None yamasiyla 51/51,
  yamasiz rc=1); metin_kontrol(row) A'siz cagri = A'li cagri (gercek ayarla) birim testi.

## 3) Test fiksturu: depo CSV'sinden ayirma

- Sorun: 322e066:scripts/etsy/test_urun_ayar.py:27-32 sahte_csv() depo CSV'sinde ESKI kargo blogunu (:23) 78 kez arar; yeni CSV'de 0
  (S13: yasak desen 0) -> "DUR: sahte CSV kurulamadi". 322e066:scripts/etsy/test_ornament_taslak.py:17-19 modul yuklenirken
  UT.sahte_ortam() cagirir (322e066:test_urun_ayar.py:62-69) -> iki test dosyasi da baslamadan coker.
- Duzeltme (emsal 102d0c52:scripts/etsy/test_ornament_metin_canli.py:52-61 `_eski_hal`): sahte_csv() BAYT duzeyinde calisir
  (DictReader/DictWriter ile yeniden yazmaz; tirnak ve CRLF degismesin): b = depo CSV baytlari; b.count(ESKI) == 78 ise aynen,
  b.count(YENI) == 78 ise b.replace(YENI, ESKI) ile ESKI taban kurulur, ikisi de degilse DUR; sonra taban.replace(ESKI, YENI) yazilir.
  Boylece fikstur depo CSV'sinin bugunku durumundan bagimsiz kalir. Olcum (inceleme): eski CSV'de ESKI->YENI degisimi 102d0c52
  CSV'sine bayt bayt esit (iki yonde de); yeni CSV'de YENI 78, ESKI 0. Kontrol testi: depo CSV'si eski de yeni de olsa sahte CSV ayni.
- 322e066:scripts/etsy/test_urun_ayar.py:87-95 beklentisinin yeni hali (gercek ayar + gercek yeni CSV, madde 4 sonrasi ayar):
  - kalan DUR nedenleri yalniz: "kilitli false", "ayar sha256 kilit.ayar_sha256 ile farkli" (kilit.ayar_sha256 null oldukca
    her zaman; 322e066:urun_ayar.py:215-216), "onay kaydi yok", "panel on isi yapilmadi" (3 panel isi), "olculmedi alanlar var"
    (taslak.nitelikler listede kalir; 322e066:urun_ayar.py:419-420);
  - "aciklama_yasak eslesmesi" YOK, "aciklama_zorunlu yok" YOK, "EN metin CSV sha256 ayardan farkli" YOK (sha esit; :421-424);
  - yorum satiri :87 ve test adi :93 guncellenir ("free shipping" ifadesi kalkar).
- Ek bilinen FAIL testi (kod asamasi): gercek ayar + ESKI blokla uretilmis sahte CSV -> "aciklama_yasak eslesmesi" ve
  "aciklama_zorunlu yok" ve sha farki (kapinin eski metni hala yakaladigi kaniti).

## 4) URUN_AYAR.json degisiklikleri (322e066:docs/urun/ornament78/URUN_AYAR.json)

- :88 metin.en.sha256: c8d18aa9... (eski CSV; S13 OZET csv_sha256_eski) -> 170ea16c... (yeni CSV; S13 OZET csv_sha256_yeni, kosu
  43556659999; 102d0c52:data/pod/ORNAMENT78_METIN.csv uzerinde sha256sum ile ayni on ek, Denetim 14 Kas).
- :21-26 olculmedi listesi: "ilan.readiness_state_id" (:22), "ilan.return_policy_id" (:23), "ilan.shop_section_id" (:24) cikar;
  "taslak.nitelikler" (:25) kalir. Degerler (:34 return_policy_id, :35 readiness_state_id, :36 shop_section_id) DEGISMEZ: O1
  koşusu 43565663626 (Genel Merkez Drive OZET.md okumasi) ile birebir.
- :12 kaynak notu: "[kaynak dosya, olculmedi; O1(1) ile okunacak]" -> "O1 olc kosusu 43565663626 (14 Kas, canli 78/78 ayni deger;
  Genel Merkez OZET.md) [olculdu]".
- :17 kaynak notu metin.en: "bugunku sha (canlidan eski, plan B8; S13 sonrasi guncellenir)" -> "S13 kosusu 43556659999 sonrasi
  CSV (main 102d0c52; aciklama canlidan)".
- :16 taslak.nitelikler notu aynen ([olculmedi]). kilit (:219-222) aynen: kilitli false, sha'lar null.
- Sema kontrolu: 322e066:urun_ayar.py:31 olculmedi liste:str zorunlu; liste bos olamaz degil (taslak.nitelikler kalir);
  dogrula() (:92-) yeni dosyada temiz olmali (test_urun_ayar "gercek ayar sema temiz", :85-86).

## 5) CI listesi (ai-beyan-test.yml) ve test_workflows kontrolu

- 102d0c52:.github/workflows/ai-beyan-test.yml:32-34 v2-test dongu listesine eklenir: scripts/etsy/test_urun_ayar.py,
  scripts/etsy/test_ornament_taslak.py, scripts/etsy/test_canli_yapi_olc.py (Serdar 9 Kas "hepsi oneriyle") ve
  scripts/etsy/test_ornament_metin_canli.py (S13 korumasi: bugun yalniz 102d0c52:.github/workflows/ornament-metin-canli.yml:38'de
  kosuyor; A varsayilaninin kaldirilmasi main push CI'sinda yakalanmali; bagimsiz inceleme bulgusu).
  Kurulum :28 (requests, numpy, pillow 11.0.0, pyyaml) bu testler icin yeterli mi kod asamasinda olculur.
- 102d0c52:.github/workflows/ai-beyan-test.yml:6-8 yol filtresi scripts/** ve .github/workflows/**: docs/urun/** degisikligi tek
  basina CI'yi tetiklemez; kod asamasindaki commit scripts/ dosyalari icerdigi icin tetiklenir.
- 102d0c52:scripts/ops/test_workflows.py:508-509 emsaline gore dort assert eklenir: dort test yolunun her biri abt metninde gecer.
- 322e066:.github/workflows/ornament-taslak.yml degisikligi rebase ile gelir; test_workflows.py tum yml'leri tarar (510 YAML,
  S13 D(1)); kod asamasinda PASS olmali.

## 6) Kod asamasinin test plani

- Yeni tam gecmisli klonda tam paket, her test tek basina, cikis kodu ayri (CLAUDE.md:195). Beklenen: 135 dosya (102d0c52'de 134
  + test_urun_ayar.py), bilinen 7 FAIL ile 128/135. Bilinen 7 FAIL (tam yollar): pano/codex/kaynak/dijital-v1_29a3e3c/test_kume.py,
  pano/codex/kaynak/dijital-v1_29a3e3c/test_medyan_plate.py, pano/codex/kaynak/dijital-v1_29a3e3c/test_siparis.py,
  pano/codex/kaynak/dijital-v1_29a3e3c/test_siparis_birim.py, scripts/pod/hat_yama/test_sembol_kapisi_kayik.py,
  scripts/kapak78/test_galeri_v10.py, scripts/prodigi/test_router_sku_v3.py ("--inv gerekli"). Liste disi FAIL -> DUR.
- Ozel PASS sartlari: test_ornament_kargo (TOPLAM 74 | PASS 74 | FAIL 0; ornament_kargo degerleri URUN_AYAR'dan okur,
  322e066:ornament_taslak.py:101-108), test_ornament_metin_canli (51/51), test_urun_ayar, test_ornament_taslak, test_workflows.
  git archive kopyasinda ek olarak yalniz CLAUDE.md:121'deki 3 test dusebilir. (14 Kas: bu satir 10) G3(b) ile daraltildi;
  archive'de CI_KOK / KISISEL_KOK zorunlu verilir, yalniz test_printful_5x7 dusebilir; 10'a bakiniz.)
- Kuru olcum (ana plan 4857c67:docs/plan/URUN_AYAR_PLAN.md:300, adim 2b; kapsam ana planla ayni): gercek URUN_AYAR (madde 4
  sonrasi) + 102d0c52 CSV, 78 ornament cifti, ornament_taslak `--mod kuru` yolu ile TUM yazim uclari (createDraftListing, envanter,
  nitelik, gorsel alt_text, kisisellestirme, stil_gorsel) yazim_kapisi'ndan gecirilir (sahte Etsy, ag kapali, token yok); ayrica
  ana planin istedigi kupa sabitleri ayni kapidan (kupa ayari yoksa "kapsam disi, neden" yazilir ve Genel Merkez'e sorulur).
  Cikti: uc basina kac ilan DUR ve neden listesi (neden basina sayi). Beklenen: 78/78 DUR, nedenler yalniz kilitli false,
  ayar sha256 farkli, onay kaydi yok, panel on isi yapilmadi (3), olculmedi alanlar var; aciklama_yasak 0, aciklama_zorunlu yok 0,
  sha farki 0, _spec_fark / _csv_satiri / _taslak_govde / _metin_yasak 0. Beklenen disi neden -> DUR, rapor. On olcum (bagimsiz
  inceleme, eef2f36 kopyasi, yalniz createDraftListing): 78/78 DUR, nedenler tam bu liste. SAHTE kilitli ayar + SAHTE onay ile ayni
  78 cift ve tum uclar: DUR 0 beklenir (inceleme on olcumu: createDraftListing ve 78x11 alt metinde DUR 0). metin_kontrol iki surum
  karsilastirmasi (madde 2): 78 satirda hata sayisi ayni (inceleme on olcumu: 0 / 0).
- Mutasyon ornekleri (her biri ilgili testi kirmizi yapmali): (a) metin_kontrol A varsayilani kaldirilir -> S13 testi kirmizi;
  (b) sahte_csv'den _eski_hal adimi kaldirilir -> test_urun_ayar fikstur DUR; (c) URUN_AYAR sha'si eski degere doner -> kuru olcumde
  sha nedeni; (d) olculmedi listesinden taslak.nitelikler de silinir -> "olculmedi alanlar var" beklentisi kirmizi;
  (e) CI listesinden test_urun_ayar silinir -> test_workflows kirmizi.

- 14 Kas eki: kuru olcumun yontemi (kayit + gercek ayarla tekrar oynatma, 1560 kapi cagrisi), test agi kurali ve yapi testi
  10) bolumundedir (G1, G2, G4); yukaridaki satirlar yerinde kalir, celiskide 10) gecerlidir.

## 7) Kod asamasinin kapanisi

- Tek bagimsiz inceleme, en cok 2 tur (CLAUDE.md:221); 2. tur yeni YUKSEK verirse DUR, push yok.
- Gizlilik taramasi (diff ve commit mesaji): \b42\d{8}\b, gercek 10 haneli ilan kimligi (sahte 900000000N haric), musteri adi,
  e-posta, Drive ID: 0 eslesme.
- Dal push, dal CI (ai-beyan-test, head_sha = yeni dal ucu) success.
- Disk: yeni tam klon ~6,2G (O1 olcumu); baslangic sarti klon + 5 GB bos; her test sonrasi ve kontrol noktalarinda 1 GB alti DUR,
  hicbir sey silinmez. Gorev sonunda klon yerinde kalir, silme Serdar'a sorulur.
- Ayri onayla main: push oncesi ls-remote main beklenen taban sha'si degilse DUR; yalniz fast-forward; push sonrasi main CI
  (push olayi, head_sha yeni uc) success.

- 14 Kas eki: son commit'te yeniden test, temiz kopya / CLAUDE.md:121 uyumu ve CI surumleriyle kosu 10) G3'tedir.

## 8) Kapanan kapi

Yok. Hicbir kapi kaldirilmaz ya da gevsetilmez: yazim_kapisi (322e066:urun_ayar.py:414-) nedenlerinin hepsi kalir; sha kapisi
(:421-424) yeni sha ile calismaya devam eder; olculmedi kapisi (:419-420) taslak.nitelikler yuzunden DUR vermeye devam eder;
S13 kapilari (102d0c52:ornament_metin_canli.py:125-145) degismez. metin_kontrol'un yeni surumu eski kurallarin hepsini icerir
(322e066:ornament_taslak.py:305-328 ile 102d0c52:...:263-285 ayni kurallar) ve ek olarak galeri sayisi sutun kontrolu getirir
(:295-297). kilit.kilitli false kalir.

14 Kas eki: createDraftListing metin yasak kapisinin yeri (main'de yazma fonksiyonu icinde, dalda _ayar_kapi'da) 10) G2'dedir;
varsayilan yol o satiri taslak_olustur'a geri koyar, boylece "kapanan kapi yok" harfiyen saglanir. Kosul: Serdar "zincir yeterli"
yorumunu secerse yukaridaki "Yok" yerine "main:351'deki ayni-fonksiyon cagrisi kalkti; esdegeri _ayar_kapi :359" yazilir.

## 9) Olculmeyenler

- Asagidaki uc madde Denetim'ce kosulmadi; bagimsiz inceleme bir kez eef2f36 git archive kopyasinda olctu (yerel Pillow 12.3.0):
  S13 kirilmasi (yamasiz rc=1), yeni metin_kontrol 0/0, fikstur yamasiyla test_ornament_taslak 23/23 ve test_urun_ayar 162/163
  (tek FAIL :93, beklenen). Kod asamasinda yeni klonda yeniden olculur.
- ai-beyan-test.yml:28 kurulumunda (pillow 11.0.0) dort testin kosmasi.
- Kuru olcumun tum uclardaki ve kupa sabitlerindeki sonucu (on olcum yalniz createDraftListing).
- taslak.nitelikler canli degeri (O1 kapsami disi).
- Kod asamasinin suresi ve tepe disk kullanimi.

Kapsam disi (ayri isler): ana plan adim 4 (yayina_hazir turetme; Serdar 9 Kas "2. A"), ORN_ETSY_AYAR emekliligi (ana plan S5;
dosya silinmez), ornament_metin.py:96 ureteci ("free shipping" cumlesi; yeniden kosarsa CSV'yi ezer), taslak.nitelikler olcumu.

## 10) Kod asamasi ek kurallari (14 Kas)

Girdi: Genel Merkez'in kod asamasi metni taslagina uc bagimsiz inceleme turunun bulgulari (G1-G4; Genel Merkez kayit
KARARLAR_20261113_EK_MADDE54 madde 115-117). Asagidaki yontemler Denetim'in kod okumasidir (322e066 / 102d0c52); kod bu asamada
degismez. Sayilar koddan hesaptir; kosulmadi.

### G1 Kuru olcum "tum uclar": kayit + tekrar oynatma

- Sorun: gercek ayarda (kilitli false) kuru yol ilk yazimda durur: yaz() once metin (322e066:scripts/etsy/ornament_taslak.py:461-464),
  sonra medya (:465-467; cift basina 11 jpg + 1 mp4, medya() :332-337, IMG_ROOT), sonra taslak_kapi (:553 -> :406-408 ->
  _tek_kapilar :362-376 -> _ayar_kapi :348-360 -> urun_ayar.yazim_kapisi). Gercek ayarla 1. cagrida DUR verdigi icin envanter, gorsel,
  video, stil, kisisellestirme ve nitelik uclari hic kapiya gelmez. Kuru kaydi (Kuru._kaydet :703-710) yalniz govdeyi tutar; kapi
  envanter / createDraftListing icin cift (322e066:scripts/etsy/urun_ayar.py:414-416), stil_gorsel icin stil_baglam (:334-339) ister;
  video yuklemesi _uc'ta "diger" ucudur (:162-176; Kuru.post_file :725-731).
- Secilen yontem (iki gecis, ag yok, token yok):
  1. KAYIT: test_urun_ayar.sahte_ortam() (322e066:scripts/etsy/test_urun_ayar.py:62-69; sahte_ayar :47-59: olculmedi = [], panel
     kanitli, SAHTE onay, kilitli) ve sahte medya (emsal 322e066:scripts/etsy/test_ornament_taslak.py:26-32 medya_kur, :87-88 IMG_ROOT)
     ile 78 cift kuru kosulur. Kosu AYNI SURECTE yapilir (CLI alt sureci degil: sarmalayici alt surece gecmez): betik
     ornament_taslak'i import eder, ornament_taslak.UA.yazim_kapisi'ni sarmalayiciyla degistirir ve kuru yolunu (Kuru sinifi :694-;
     --mod kuru'nun cagirdigi fonksiyon) dogrudan cagirir. Her cagrinin (method, path, data, json_body, cift, stil_baglam, metin_yolu)
     kopyasi JSON satiri olarak yazilir; stil_baglam'daki rank_id'nin anahtarlari int'tir (:608, :614) ve JSON'da str'ye donusur, bu
     yuzden vid ve rank_id [[anahtar, deger], ...] listesi olarak kaydedilir. Sonra gercek fonksiyon cagrilir (SAHTE ayarda DUR 0
     beklenir; DUR > 0 ise olcum DUR).
  2. TEKRAR OYNATMA: kayittaki her cagri urun_ayar.yazim_kapisi'na gercek ayarla (UA.yukle("ornament78"), madde 4 sonrasi) aynen
     verilir; stil_baglam listeden int anahtarli dict'e geri cevrilir (urun_ayar.py:341 rank_id.get(int)); degisen yalniz A, onay_yolu
     (None; gercek onay kaydi yok) ve metin_yolu (SAHTE yoldan depodaki data/pod/ORNAMENT78_METIN.csv'ye); SAHTE
     CSV ile bayt bayt ayni olmali (madde 3 fiksturu ESKI tabandan YENI uretir; ayni degilse olcum DUR). Her cagrinin DUR nedenleri
     ayri ayri toplanir (yazim_kapisi SystemExit metni; neden listesi "; " ile ayrilir).
- Beklenen kayit sayisi (koddan hesap; NIT 3, galeri 11, menu 5: 322e066 URUN_AYAR.json taslak.nitelikler / taslak.galeri /
  varyasyon.menu): cift basina 20 = createDraftListing 2 (taslak_kapi :553 ve taslak_olustur :555, ikisi de _tek_kapilar) + envanter 1
  (:575) + gorsel 11 (:581-586) + diger (video) 1 (:601-603) + stil_gorsel 1 (:615-616) + kisisellestirme 1 (:619) + nitelik 3
  (:622-626). Toplam 1560: createDraftListing 156, envanter 78, gorsel 858, diger 78, stil_gorsel 78, kisisellestirme 78, nitelik 234.
  Sayi farkliysa olcum DUR (sarmalayici eksik ya da fazla cagri).
  On olcum (bagimsiz inceleme, 14 Kas, 322e066 git archive kopyasi, ag kapali, madde 4 ayari bellekte): kayit 1560, dagilim ayni;
  SAHTE ayarla DUR 0; SAHTE CSV = 102d0c52 CSV bayt bayt; tekrar oynatmada her cagrida beklenen 7 neden (stil_gorsel'deki ek neden
  JSON anahtar tipinden; yukaridaki [[anahtar, deger]] kaydi bunu giderir). Kod asamasinda yeni klonda yeniden olculur.
- Beklenen tekrar oynatma sonucu: 1560/1560 cagri DUR; her cagride nedenler yalniz kilitli false, ayar sha256 kilit.ayar_sha256 ile
  farkli, onay kaydi yok, panel on isi yapilmadi (3 panel isi), olculmedi alanlar var. Sifir listesi (madde 6) korunur:
  aciklama_yasak, aciklama_zorunlu yok, EN metin sha farki, _spec_fark, _csv_satiri, _taslak_govde, _metin_yasak, _envanter,
  _stil_gorsel, _gorsel, _nitelik nedenleri 0. Beklenen disi neden -> DUR, rapor (uc ve neden basina sayi).
  metin_kontrol iki surum karsilastirmasi (madde 6) ve kupa sabitleri satiri (madde 6) aynen.
- Kanit testi: (a) SAHTE ayarla kayit gecisinde DUR 0 ve 1560 kayit; (a2) kayit JSON'a yazilip geri okunduktan sonra SAHTE ayarla
  tekrar oynatmada stil_gorsel ek nedeni 0 (anahtar tipi kaniti; bagimsiz inceleme olcumu: str anahtarla 78/78 stil_gorsel cagrisi
  "menu degeri -> gorsel eslemesi ... farkli" verdi); (b) bir kayitta stil_baglam None yapilinca tekrar oynatmada
  "eslem baglami ... verilmedi" nedeni cikar (kayit eksikse olcumun yakaladigi kaniti); (c) kayit dosyasinda ilan kimligi yok
  (Kuru sahte listing_id 9000000000 + n; :742) ve token yok.

### G2 Ortak istemci kurali (CLAUDE.md:220)

- Durum: main'de createDraftListing'in yazma fonksiyonu taslak_olustur icinde, gonderilen govdeyle, istekten once
  metin_yasak_kapisi(..., mod="ENGEL") var (102d0c52:scripts/etsy/ornament_taslak.py:351, requests.post :354). Dalda taslak_olustur
  (322e066:scripts/etsy/ornament_taslak.py:412-421) bu satiri tasimaz; kapi ayni b2 ile _tek_kapilar :371 -> _ayar_kapi :359'da,
  post'tan once calisir (davranis korunur) ama "ayni fonksiyonda" degil. 102d0c52:337 (istek gondermeyen taslak_kapi) icin dalda
  _tek_kapilar -> _ayar_kapi :359 karsilar; ek satir gerekmez (bilgi).
- VARSAYILAN YOL (planda kalir, karar gerektirmez): 322e066:ornament_taslak.py taslak_olustur icinde, b2 = self._tek_kapilar(...)
  (:416) ve ai_beyan_kapisi (:417) satirlarindan sonra, self._istek_oncesi() (:418) ve self._bekle() (:419) satirlarindan ONCE:
  `metin_yasak_kapisi("POST", f"/shops/{shop}/listings", data=b2, mod="ENGEL")`. Siralama gerekcesi: _bekle sayaci istekten once
  artirir (102d0c52:scripts/etsy/etsy_common.py:748-756); ENGEL'de sayac ve kota etkilenmez. Govde b2 (gonderilen, html_coz sonrasi).
- Yapi testi (davranis testi yetmez: kapi _ayar_kapi'da zaten calistigi icin yeni satir yokken de yesil kalir): test_urun_ayar'a iki
  kontrol. (1) AST: Kilitli.taslak_olustur govdesinde requests.post'tan once metin_yasak_kapisi cagrisi var, data argumani b2
  (emsal 102d0c52:scripts/etsy/test_ai_beyan.py:169-226 C kontrolu, AST taramasi). (2) Casus: Kilitli nesnesi
  (emsal 322e066:scripts/etsy/test_urun_ayar.py:357-360 object.__new__ + sahte requests.post; 322e066:scripts/etsy/test_ornament_taslak.py:213-221)
  uzerinde _ayar_kapi'daki kapi su yolla devre disi birakilir: modul degiskeni T.metin_yasak_kapisi YAMANMAZ (yeni satir da ayni
  degiskeni cagirir; yamanirsa satir varken de test kirmizi olur). Bunun yerine ornegin k._ayar_kapi'si ezilir: yerine konan
  sarmalayici yalniz (html_coz(data), html_coz(json_body)) dondurur (gerekirse SAHTE ayarla UA.yazim_kapisi'ni da cagirir, metin
  yasak kapisini cagirmaz). Ornek alanlari 322e066:test_urun_ayar.py:357-358'deki gibi kurulur (remaining, _kalan_yaz,
  _istek_oncesi, _bekle, _headers). KESIN yasak bir baslikla taslak_olustur cagrilir: istek gitmemeli (sahte post cagrilmamali) ve
  SystemExit metninde "metin yasak kapisi" ve "KESIN yasak" gecmeli (102d0c52:scripts/etsy/etsy_common.py:373-374; metinde
  "ENGEL" kelimesi yok). Kuru.taslak_olustur (:738-748) bu fonksiyonu
  ezdigi icin kuru olcum bu satirin kaniti sayilmaz. Mutasyon: yeni satir silinince (1) ve (2) kirmizi.
- Kural yorumu ve Serdar sorusu (oneri; karar Serdar'da, varsayilan yol planda kalir): "Dalin bugunku yapisi kurali ozde karsiliyor:
  createDraftListing'in tek gonderim yolu taslak_olustur -> _tek_kapilar -> _ayar_kapi :359 zinciridir; metin yasak kapisi ayni b2 ile
  post'tan once, ayni Kilitli nesnesinde calisir (kanit: 322e066:test_ornament_taslak.py ve test_urun_ayar.py'deki ENGEL testleri;
  kosulmadi). Fazladan satir ayni govdeye ikinci kez ENGEL uygular (yan etkisi yok). Soru: varsayilan yol (satiri taslak_olustur'a
  geri koymak) mu, yoksa 'zincir yeterli' yorumu mu?" Denetim'in onerisi: varsayilan yol (kural harfiyen, maliyet 1 satir + yapi testi).

### G3 Kapanis: son commit'te yeniden test ve temiz kopya

- Inceleme duzeltmesinden sonra (her turda), push edilecek SON commit'te yeniden: temiz kopya (git archive) + git check-ignore taramasi,
  tam paket (madde 6 sayilari), mutasyonlar (madde 6 + G2 + G4), kuru olcum (G1). Onceki commit'teki sonuclar push kaniti sayilmaz.
- Madde 6'daki (eski :104 satiri, 14 Kas notundan once) "git archive kopyasinda yalniz CLAUDE.md:121'deki 3 test ek dusebilir" ile
  CLAUDE.md:121 ("uc test de bu kosullar saglanmis ortamda gecmeli") uyumu: iki ortam ayri kanittir. (a) Tam gecmisli yeni klonda
  (origin'i var) 3 test GECMELI (test_printful_5x7 gecmis okur; test_p1g_kart ve test_tag_kerning origin'den dal ceker). (b) git
  archive kopyasinda CI_KOK (kapak-ci-ref-20261029 dalindaki ref/kapak_ci) ve KISISEL_KOK (kisisel-v1 dalindan cikarilmis
  scripts/kisisel + assets koku) ZORUNLU verilir; test_p1g_kart ve test_tag_kerning orada da PASS sarttir (CLAUDE.md:121); yalniz
  test_printful_5x7 (git gecmisi) archive'de dusebilir. Rapor iki ortami ayri yazar.
- CI listesi testleri CI surumleriyle: kurulum test surecinin DISINDA, ayri ortamda (yeni venv; pip agi yalniz kurulumda, testte ag
  kapali). test_ai_beyan 102d0c52:.github/workflows/ai-beyan-test.yml:17 surumuyle (yalniz requests==2.34.2); v2-test listesi
  (madde 5'in eklediği dort test dahil) :28 surumleriyle (requests 2.34.2, numpy 2.1.3, pillow 11.0.0, pyyaml 6.0.2). Sonuc rapora
  surum + cikis kodu.

### G4 Test agi (CLAUDE.md:124)

- Kural yeni ve degisen testler icindir: test_urun_ayar, test_ornament_taslak (dalda degisen / yeni) ve kod asamasinda degisecek
  test_workflows. Uc dosya da gercek agi baştan kapatir (emsal 102d0c52:scripts/sosyal/test_metricool_yedek.py:19-25:
  socket.socket, socket.create_connection, urllib.request.urlopen -> AssertionError). Bugun 322e066'daki ilk ikisinde socket
  kapatma yok (grep 0); 102d0c52 test_workflows'ta da yok (grep 0). test_workflows alt surec kosar: bash (102d0c52:scripts/ops/test_workflows.py:30,
  :138, :205, :207, :247; yml adim parcalari) ve python3 - (:266, :268, :272). Ana surecteki socket yamasi alt surece gecmez
  (CLAUDE.md:124 alt surecte de agi kapatmayi ister): python3 alt sureclerine agi kapatan on kod verilir (stdin basina ya da
  sitecustomize ile PYTHONPATH); bash alt sureclerinin PATH'ine sahte gh, curl, rclone konur (emsal 102d0c52:scripts/etsy/test_kolye_pazar.py:73-85).
- Kanit: her biri icin mutasyon: test icine (ve test_workflows'ta bir python3 alt surecine) ag cagrisi eklenince test FAIL
  (AssertionError "gercek ag"); adres TEST-NET 192.0.2.1 (gercek alan adi yok; kapatma eksik kalsa da gercek hizmete gidilmez) ve
  mutasyon ag kapali ortamda (unshare -rn) kosulur; cikti rapora.
- Tam paketteki eski testlere yeni ag kurali uygulanmaz. test_p1g_kart ve test_tag_kerning'in origin'den git fetch'i CLAUDE.md:121
  ve :124'teki istisnaya gore kalir.
