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
  git archive kopyasinda ek olarak yalniz CLAUDE.md:121'deki 3 test dusebilir.
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

## 7) Kod asamasinin kapanisi

- Tek bagimsiz inceleme, en cok 2 tur (CLAUDE.md:221); 2. tur yeni YUKSEK verirse DUR, push yok.
- Gizlilik taramasi (diff ve commit mesaji): \b42\d{8}\b, gercek 10 haneli ilan kimligi (sahte 900000000N haric), musteri adi,
  e-posta, Drive ID: 0 eslesme.
- Dal push, dal CI (ai-beyan-test, head_sha = yeni dal ucu) success.
- Disk: yeni tam klon ~6,2G (O1 olcumu); baslangic sarti klon + 5 GB bos; her test sonrasi ve kontrol noktalarinda 1 GB alti DUR,
  hicbir sey silinmez. Gorev sonunda klon yerinde kalir, silme Serdar'a sorulur.
- Ayri onayla main: push oncesi ls-remote main beklenen taban sha'si degilse DUR; yalniz fast-forward; push sonrasi main CI
  (push olayi, head_sha yeni uc) success.

## 8) Kapanan kapi

Yok. Hicbir kapi kaldirilmaz ya da gevsetilmez: yazim_kapisi (322e066:urun_ayar.py:414-) nedenlerinin hepsi kalir; sha kapisi
(:421-424) yeni sha ile calismaya devam eder; olculmedi kapisi (:419-420) taslak.nitelikler yuzunden DUR vermeye devam eder;
S13 kapilari (102d0c52:ornament_metin_canli.py:125-145) degismez. metin_kontrol'un yeni surumu eski kurallarin hepsini icerir
(322e066:ornament_taslak.py:305-328 ile 102d0c52:...:263-285 ayni kurallar) ve ek olarak galeri sayisi sutun kontrolu getirir
(:295-297). kilit.kilitli false kalir.

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
