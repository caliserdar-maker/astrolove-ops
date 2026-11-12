# Sirlar (Secrets)

Bu dosya yalnizca **gereken sirlarin listesini** icerir. Hicbir gercek deger
buraya yazilmaz. Degerler GitHub reposunda
`Settings > Secrets and variables > Actions` altinda, lokalde ise
versiyonlanmayan bir `.env` dosyasinda tutulur.

| Sir | Aciklama |
| --- | --- |
| `ETSY_API_KEY` | Etsy uygulamasinin genel API anahtari (keystring); API isteklerini uygulamaya baglar. |
| `ETSY_SHARED_SECRET` | Etsy uygulamasinin gizli anahtari; OAuth token degisimi ve imzalama icin kullanilir. |
| `SIPARIS_KOD_ANAHTARI` | Loglardaki ve raporlardaki opak kodlarin (`S-...`; router'da receipt, kupa hattinda transaction icin) HMAC anahtari (KARAR, 12 Kasim 2026). HENUZ TANIMLI DEGIL; `etsy-secret-gecis` (mod `kod_anahtari`) rastgele uretir, deger hicbir yerde gorunmez. Tanimli DEGILKEN kod `ETSY_SHARED_SECRET` ile uretilir (onceki davranis). Tanimlandigi anda kodlar bir kez degisir (eski rapor ve loglardaki kodlarla eslesmez); sonra Etsy shared secret'i yenilense de degismez. Okuyan adimlar: `pod-order-router.yml` (2), `kupa-siparis.yml`, `router-kota-deneme.yml`, `pod-arac-v4.yml`. Haric: `pod-order-router.yml` sahte receipt adimi (env'siz; sabit yedek anahtarla kod uretir). |
| `ETSY_REFRESH_TOKEN` | KULLANILMAZ (1 Eyl 2026 karari). Etsy OAuth token zinciri Drive'daki `ASTROLOVE/TEMP/ETSY_TOKEN.json` dosyasindan yurur; asagidaki "Etsy token sahibi" bolumune bakin. Secret silinene kadar yalnizca tarihsel kayittir. |
| `ETSY_SHOP_ID` | Islem yapilacak Etsy magazasinin sayisal kimligi. |
| `RCLONE_CONF_B64` | Base64 ile kodlanmis `rclone.conf` icerigi (remote `gdrive`, kendi OAuth istemcimizle yetkilendirilmis, 2 Eyl 2026). Icindeki `client_secret` satiri bayattir; gecerli secret `GOOGLE_CLIENT_SECRET` ile calisma aninda ezilir. |
| `GOOGLE_CLIENT_SECRET` | Kendi Google OAuth istemcimizin (proje `gen-lang-client-0835100486`) guncel secret'i. Her rclone kosusunda `RCLONE_CONFIG_GDRIVE_CLIENT_SECRET` olarak ortama yazilir ve conf'daki degeri ezer; secret Console'da sifirlaninca yalniz bu deger guncellenir, conf'a dokunulmaz. |
| `GDRIVE_ROOT_FOLDER_ID` | Dosyalarin yazilacagi Google Drive kok klasorunun kimligi. |
| `OPS_ADMIN_TOKEN` | Fine-grained GitHub PAT (astrolove-ops + astrolove-media; Secrets/Variables/Contents/Actions/Workflows RW, 1 yil). Tum otomasyon yetkisi buradan: `gh_secrets.py` secret/variable yazar, `ig-media-sync` medya reposuna push eder. HER IKI repoda da tanimli olmali. Tek elle kurulan sir budur (asagiya bakin). |

## Repo degiskenleri (Variables, sir degil)

| Degisken | Aciklama |
| --- | --- |
| `IG_PUBLISH_ENABLED` | `true` olmadikca `ig-publish`'in zamanlanmis (06:00 UTC) kosusu atlanir. Yayina gecis karari bu degiskenle verilir; elle tetikleme `dry_run` varsayilani ile her zaman calisir. |

## Otomasyon kurali (KARAR, 2 Eylul 2026)

- GitHub/Drive/Console'da elle is yapilmaz. Secret ve variable'lar
  `scripts/common/gh_secrets.py` ile (libsodium sealed box, GitHub REST)
  yazilir; bu script Actions runner icinde `OPS_ADMIN_TOKEN` ile calisir.
- ISTISNA (kacinilmaz): `OPS_ADMIN_TOKEN`'in kendisi bir kez tarayicidan
  girilir. Otomasyonu yetkilendiren ilk kimlik, yetkilendirdigi otomasyonla
  kurulamaz. Ayrica Claude Code sandbox proxy'si `api.github.com/.../actions/*`
  yollarini (secrets, variables) engeller; bu yuzden sohbetten API ile secret
  yazilamaz, yalniz Actions icinden yazilir.
- ISTISNA 2 (KARAR, 12 Kasim 2026): Etsy shared secret yenilemesinde Serdar tarayicidan iki giris yapar: (1) gecisten once, erisimi olcmek icin anlamsiz bir degerle `ETSY_SECRET_DENEME` adina deneme girisi; (2) Etsy panelinden kopyalanan yeni degerin `ETSY_SHARED_SECRET_YENI` adina girisi (kapi FAIL verirse yeniden girilir). Canli `ETSY_SHARED_SECRET`'i yalniz `etsy-secret-gecis` is akisi yazar. Deger sohbete, is akisi girdisine ve Drive'a yazilmaz.
- Instagram kimligi secret DEGILDIR: Drive `TEMP/ig_token.json`
  ({"token","ig_id","expiry"}). `publish.py` dosyayi rclone ile okur, 60
  gunluk token bitise 10 gunden az kaldiysa `refresh_access_token` ile
  yeniler ve dosyaya geri yazar (Etsy token modeliyle ayni: tek kaynak,
  geri yazma zorunlu, tek yazici = concurrency grubu).

## Kurallar

- Gercek degerler asla depoya commit edilmez; `.gitignore` `.env`,
  `rclone.conf` ve `*.json` token dosyalarini haric tutar.
- Sir degeri degistiginde once GitHub Secrets guncellenir, sonra ilgili
  workflow yeniden calistirilir.
- Yeni bir sir eklendiginde bu tabloya tek satirlik aciklamasiyla eklenir.

## Etsy token sahibi (KARAR, 1 Eylul 2026)

- Etsy OAuth2 refresh token'inin TEK KAYNAGI Drive'daki
  `ASTROLOVE/TEMP/ETSY_TOKEN.json` dosyasidir. Etsy her yenilemede yeni bir
  refresh token dondurur ve eskisini gecersiz kilar; bu yuzden token zinciri
  yalniz tek bir yerde tutulabilir.
- Workflow'lar dosyayi rclone ile okur, access token'i yeniler ve donen yeni
  refresh token'i ayni dosyaya GERI YAZAR. Geri yazmayan bir kosu zinciri
  koparir.
- `ETSY_REFRESH_TOKEN` GitHub secret'i kullanilmaz; hicbir workflow bu
  secret'i okumaz. Colab veya baska bir ortamdan ayni dosya disinda bir
  token ile Etsy'ye baglanilmaz.
- `ETSY_API_KEY` (keystring) kalicidir ve GitHub Secrets'ta kalir.
  `ETSY_SHARED_SECRET` yenilenebilir; yalniz `etsy-secret-gecis` is akisiyla
  degistirilir (asagida "Etsy shared secret gecisi"). Etsy v3 `x-api-key`
  basligi `keystring:shared_secret` bicimindedir.
- `ETSY_SHOP_ID` sabittir ve GitHub Secrets'ta kalir.
- Ayni anda yalnizca TEK Etsy kosusu calisir (concurrency grubu); iki kosu
  ayni dosyayi paralel yenilerse biri gecersiz token ile kalir.
- Not: Drive TEMP'te `etsy_tokens.json` adli ikinci, eski bir dosya daha
  vardir (9 Agu tarihli OAuth kurulumundan). Gecerli dosya `ETSY_TOKEN.json`
  olanidir; eski dosya karistirilmamalidir.

## Etsy shared secret gecisi (KARAR, 12 Kasim 2026)

- Is akisi `.github/workflows/etsy-secret-gecis.yml`, betik
  `scripts/etsy/secret_gecis.py`, test `scripts/etsy/test_secret_gecis.py`.
  Girdi yalniz `mod` ve `onay`; sir degeri girdi olmaz. HER KOSU AYRI SERDAR
  ONAYIDIR. Onay sozcugu moda ozeldir: `SERDAR_SECRET_<MOD buyuk harf>`
  (ornek: mod `degistir` icin `SERDAR_SECRET_DEGISTIR`). Kosu yalniz `main`
  dalindan ve ilk denemede (yeniden kosu yok) calisir.
- Cikti yalniz sabit metin + EVET / HAYIR / DOLU / BOS / VAR / YOK / HTTP
  kodu. Artifact, is ozeti, Drive raporu yok. Sir degeri, parcasi, uzunlugu,
  ozeti yazilmaz (tek istisna: `olc` modunda "secret en az 12 karakter").
- Etsy istekleri: yalniz `GET /openapi-ping`, `GET /users/me` (OAuth'lu salt
  okuma) ve token yenileme (kilit altinda, standart geri yazim). `x-api-key`
  basligini betik, sinanan HEDEF secret'la kendisi kurar. 401'de
  kendiliginden yenileme yok; token dosyasindaki alan canliya esit degilken
  yenileme denenmez. Her istekten once kota tabani 10.
- KANIT UCU: hangi istegin secret'i dogruladigi olculmedi. Kod sabiti
  `secret_gecis.KANIT_UCU` varsayilani AYARSIZ; `olc` kosusundan sonra ayri
  commit ve incelemeyle `ping` ya da `oauth` yapilir. Ayarsizken
  `yedek_dogrula`, `degistir`, `dogrula`, `tamam_kontrol`, `geri_al`,
  `geri_dogrula`, `temizle`, `temizle_drive` DUR verir. Bu modlar once
  pozitif istegi atar (hedef secret 200 olmali; ilk 200 kotayi bildirir),
  sonra 5 rastgele secret'la (10, 12, 16, 24, 32 karakter, harf-rakam; gercek
  degerden turetilmez) negatif kontrol yapar: biri 200 donerse ya da 401 /
  403 disinda kod donerse DUR. Kanit PASS olmadan ne secret ne dosya
  yazilir. Ardisik istekler arasi 0,25 sn.
- Kanit ucu secilirken on sart: `olc` ciktisinda o ucun "yaniti kota basligi
  tasiyor: EVET" satiri (`yedek_dogrula` bunu yeniden sinar; baslik yoksa
  gecise baslanmaz). `oauth` secilirse: access token suresi dolmusken kanitli
  modlar (acil `geri_al` dahil) DUR verir (gecerliligi kanitlanmamis
  secret'la yenileme yok); once herhangi bir Etsy okuma kosusu token'i
  tazeler. Kanit ucu karari verilirken bu maliyet hesaba katilir.
- Kilit ve siparis: `kapat` / `ac` disindaki her modda `kilit_bekle.py`.
  Siparis icin BEKLENMEZ: yazan modlarda kilitten once ve sonra
  `siparis_bekle.py --dk 0`; aktif `siparis-*` kosusu varsa kosu hemen DUR
  verir (yeni kosu ayri onay). Hicbir sey yazmayan `tamam_kapisi`,
  `yedek_dogrula`, `geri_dogrula` modlarinda ve `kapat` / `ac`'ta siparis
  kontrolu yoktur. Neden: kosu olusturuldugu andan itibaren Etsy kilit
  sirasindadir ve `siparis-kisisel-oku` ayni kumededir; beklemek karsilikli
  bekleme olurdu.
- Not (ISTISNA 2 ile birlikte okunur): Serdar degeri Drive'a yazmaz. Betik,
  token dosyasinda `shared_secret` alani DOLU ise `degistir` / `geri_al` /
  `alan_geri` modlarinda degeri o alana yazar ve her alan yaziminda dosyanin
  tarihli yedegini `ASTROLOVE/TEMP/SECRET_GECIS_YEDEK` altina koyar (yedek,
  eski alani ve token'lari tasir; `temizle_drive`'a kadar durur). Alan once
  `alan_sil` ile kaldirilirsa yeni deger Drive'a hic yazilmaz.

| Mod | Ne yapar | Yazdigi yer | Etsy istegi (en cok) |
| --- | --- | --- | --- |
| `olc` | Olcum: token dosyasi alanlari (DOLU / BOS, ortama esit mi), ucuncu dosya, OAuth GET ve ping'in ortam / alan / 5 rastgele secret'la HTTP kodu, yanitin kota basligi tasiyip tasimadigi; SONUC: kanit ucu adayi ya da "KANIT UCU YOK" | yok (suresi dolmus token yenilenirse standart geri yazim) | 15 |
| `yedek` | canli deger -> `ETSY_SHARED_SECRET_YEDEK`. YEDEK zaten VARSA ya da canli == YENI ise DUR (uzerine yazilmaz) | GitHub secret | 0 |
| `yedek_dogrula` | AYRI kosu: YEDEK == canli + negatif kontrol + kanit ucu YEDEK ile 200 + yanit kota basligi tasiyor | yok | 6 |
| `prova` | Serdar'in `ETSY_SECRET_DENEME` girisi VAR mi (okur, siler); `OPS_ADMIN_TOKEN` secret yazma / silme ve is akisi kapatma / acma yetkisi (`ETSY_SECRET_PROVA`, `etsy-quota-probe.yml`; sonunda eski duruma). Canli secret'a dokunmaz | gecici GitHub secret | 0 |
| `kapat` | Asagidaki 18 is akisindan ETKIN olanlari kapatir; adlari `ETSY_GECIS_KAPATILAN` repo degiskenine EKLER | is akisi durumu, repo degiskeni | 0 |
| `ac` | Yalniz `ETSY_GECIS_KAPATILAN`'daki is akislarini acar (onceden kapali olan acilmaz) | is akisi durumu, repo degiskeni | 0 |
| `kod_anahtari` | `SIPARIS_KOD_ANAHTARI` yoksa rastgele (48 bayt) yazar; VARSA dokunmaz | GitHub secret | 0 |
| `alan_sil` | Token dosyasindan `shared_secret` alanini kaldirir (on kapi: alan == canli; "zaten yok" PASS; tarihli Drive yedegi; geri okuma: yalniz o alan, refresh_token ayni) | Drive token dosyasi + yedek | 1 |
| `alan_geri` | Alan yoksa canli degerle geri koyar (YEDEK varsa canli == YEDEK sarti; YEDEK yoksa bu sart yok) | Drive token dosyasi + yedek | 0 |
| `degistir` | Kapilar (YENI dolu ve bosluksuz, YENI != YEDEK, canli YEDEK'e ya da YENI'ye esit, 18 is akisinda aktif kosu yok, ucuncu dosyada eski alan yok, dosya alani BOS / eski / yeni, negatif kontrol, kanit ucu YENI ile 200) PASS ise canli := YENI; dosya alani DOLU ise YENI'ye cekilir, BOS ise dokunulmaz. Kapi FAIL ise hicbir sey yazilmaz. Yeniden kosulabilir (ayri onay): yarim kalan dosya alani kanit PASS olduktan sonra tamamlanir | GitHub secret, (alan DOLU ise) Drive token dosyasi + yedek | 6 |
| `dogrula` | AYRI kosu: canli == YENI, canli != YEDEK, dosya alanlari beklenen durumda, negatif kontrol, kanit ucu canli ile 200, zincir testi (token yenileme + geri yazim) | Drive token dosyasi (yenilenen token) | 7 |
| `tamam_kapisi` | "completed"den hemen once: canli == YENI; son yazimdan (secret ya da dosya alani, +5 dk pay) once baslamis aktif Etsy kosusu yok (kilit kumesi + `secrets.ETSY_*` ya da `ETSY_TOKEN.json` iceren her yml); dosya alani beklenen durumda | yok | 0 |
| `tamam_kontrol` | "completed"den sonra TEK okuma: negatif kontrol, eski (YEDEK) reddediliyor, canli 200, zincir testi, OAuth'lu GET 200 | Drive token dosyasi (yenilenen token) | 9 |
| `geri_al` | canli := YEDEK (YEDEK != YENI ve kanit ucu YEDEK ile 200 ise); dosya alani DOLU ve YEDEK degilse (YENI ya da taninmayan deger) kanitlanmis YEDEK'e cekilir, onceki hali tarihli yedekte kalir | GitHub secret, (alan guncellendiyse) Drive token dosyasi + yedek | 6 |
| `geri_dogrula` | AYRI kosu: canli == YEDEK, YEDEK != YENI, dosya alani beklenen durumda, negatif kontrol, kanit ucu YEDEK ile 200 | yok | 6 |
| `temizle` | Iki dal. Gecis tamam (canli != YEDEK): canli 200, eski reddediliyor, negatif kontrol. Geri donus tamam (canli == YEDEK): canli 200, YENI varsa reddediliyor, negatif kontrol. Sonra `ETSY_SHARED_SECRET_YENI`, `ETSY_SECRET_DENEME`, `ETSY_SECRET_PROVA` ve EN SON `ETSY_SHARED_SECRET_YEDEK` silinir; Drive token yedekleri yalniz LISTELENIR (ad + tarih) | GitHub secret (silme) | 7 |
| `temizle_drive` | Ayri onayla, YEDEK secret'i silindikten sonra: yalniz bu betigin yedek klasoru (`ASTROLOVE/TEMP/SECRET_GECIS_YEDEK`) kalici silinir; `ETSY_TOKEN_ONCEKI_*` yalniz listelenir | Drive (silme) | 6 |

- Sira ozeti (baglayici ayrinti 12 Kasim plani C4; her adim ayri onay): `olc`
  -> kanit ucu ayari (commit + inceleme) -> `kod_anahtari` -> `yedek` ->
  `yedek_dogrula` -> Serdar `ETSY_SECRET_DENEME` girer -> `prova` -> (karara
  gore) `alan_sil` -> `kapat` -> Serdar Etsy panelinde yeni secret uretir ve
  `ETSY_SHARED_SECRET_YENI`'ye girer -> `degistir` -> `dogrula` ->
  `tamam_kapisi` -> Serdar panelde "completed" -> `tamam_kontrol` ->
  `temizle` -> `ac` -> (ayri onayla) `temizle_drive`. Geri donusten sonra
  (asagidaki a-c tamamlaninca): `temizle` (geri donus dali) -> `ac` ->
  (ayri onayla) `temizle_drive`.
- `degistir` on sarti (kodda kapi YOK, sirayla saglanir): `kod_anahtari`
  kosulmus ve `SIPARIS_KOD_ANAHTARI` env satirlari `main`'de olmali; yoksa
  opak siparis kodlari Etsy secret'i degisince bir kez, anahtar gelince bir
  kez daha degisir.
- GERI DONUS SIRASI ("completed"den once): (a) `geri_al` kosusu: YEDEK ->
  canli (+ dosya alani eski degere, alan guncellendiyse); (b) AYRI kosuda
  `geri_dogrula`: canli == YEDEK EVET, dosya alani beklenen durumda, kanit
  ucu YEDEK ile 200; (c) EN SON Serdar panelde "Cancel". "completed"den
  sonra eski deger Etsy'de silinmistir, geri donus yoktur.
- Gecisten once kapatilan 18 is akisi (sir sizdirabilen log yollari; liste
  `secret_gecis.KAPAT`): gorsel-denetim, wp-pdf-probe, wp-saat80-ornek,
  wp-share-mockups, by-taslak-hazirlik, etsy-ai-scan, etsy-quota-probe,
  etsy-ru-probe, etsy-state-probe, ig-ilan-dogrula, pw-ru-probe,
  urun-gorsel-cl, gorsel02, gorsel19, seo51, pin-v6, dijital-donusum-uygula,
  pod-arac-v4.
- Gecici secret adlari: `ETSY_SHARED_SECRET_YEDEK`, `ETSY_SHARED_SECRET_YENI`,
  `ETSY_SECRET_DENEME`, `ETSY_SECRET_PROVA`. `gh_secrets.delete_secret` yalniz
  bu dort adi siler.

## rclone OAuth istemcisi (KARAR, 2 Eylul 2026)

- `gdrive` remote'u artik KENDI Google Cloud projemizin OAuth istemcisiyle
  yetkilendirilmis (proje `gen-lang-client-0835100486`; Drive, Docs ve
  Sheets API acik; scope `drive` + `documents` + `spreadsheets`, offline
  refresh token). rclone'un paylasimli istemcisi kullanilmiyor; ortak kota
  ve Docs API blokaji ortadan kalkti.
- Kurulum tek seferlik `google-oauth-bootstrap` workflow'u ile yapildi ve
  workflow sonra silindi: GitHub `workflow_dispatch` girdilerini loga acik
  yazdigi icin `client_secret` run loguna dusmustu; log silindi, secret
  Console'da sifirlandi, yeni deger `GOOGLE_CLIENT_SECRET` olarak eklendi.
  DERS: sir hicbir zaman workflow girdisi olarak verilmez; yalniz GitHub
  Secrets uzerinden gelir.
- Refresh token `client_id`'ye baglidir, secret'a degil. Secret rotasyonunda
  yeniden yetkilendirme GEREKMEZ: Console'da sifirla, `GOOGLE_CLIENT_SECRET`
  secret'ini guncelle, bitti. `RCLONE_CONF_B64` degismez.
- Her workflow'un `rclone.conf olustur` adimi `GOOGLE_CLIENT_SECRET`'i
  `$GITHUB_ENV` uzerinden `RCLONE_CONFIG_GDRIVE_CLIENT_SECRET` olarak
  yayar; boylece adimlardaki ve Python'dan cagrilan tum rclone komutlari
  guncel secret'i kullanir.
- Gecici dosya `ASTROLOVE/TEMP/rclone_new_b64.txt` (yeni conf'un base64'u)
  secret guncellendikten sonra Drive'dan silinir; sir iceren dosya Drive'da
  birakilmaz.

## Instagram yayin hatti (2 Eylul 2026)

- `WA_IG_PLAN` sheet'i `ig-publish` tarafindan rclone.conf'daki OAuth
  kimligiyle (Plan A) okunur ve yazilir; Sheets icin ayri secret yoktur.
- Tekrar yayin korumasi: durum sutunu (`ST_REEL`/`ST_CAR`/`ST_STORY`) bos
  degilse o tur atlanir. Yayindan ONCE `PENDING <ts>` yazilir, container
  olusunca id eklenir, sonra `OK <media_id> <ts>` ya da `ERR <sebep> <ts>`.
  `media_publish` hicbir zaman yeniden denenmez. `PENDING` kalmis hucre
  otomatik acilmaz; container_id ile Graph API'den bakilip elle temizlenir.
- Ayni cift + ayni medya daha erken gunde OK ise `SKIP_DUP D<NN>` yazilir
  (plandaki D79 = D01 tekrari).
- Carousel medyasi sheet'teki SLIDE_URLS'den degil,
  `astrolove-media/carousel_v2/D<NN>/slide_1..5.jpg` yolundan turetilir;
  `ig-media-sync` bu dosyalari Drive'dan Pages reposuna tasir.

## Prodigi anahtari (6 Eylul 2026)

Prodigi Print API anahtari GitHub secret'i DEGILDIR; Etsy token modeliyle Drive'da
durur: `ASTROLOVE/TEMP/PRODIGI_TOKEN.json` (`{"api_key": "..."}`). `prodigi-quote`
workflow'u dosyayi rclone ile okur, `::add-mask::` ile maskeler ve cikti dosyalarinda
sizinti kontrolu yapar (anahtar bulunursa dosya silinir, kosu hata verir). Anahtar
hicbir loga, dosyaya, commit'e ve workflow girdisine yazilmaz. Yerel deneme icin
yalniz `PRODIGI_API_KEY` ortam degiskeni kabul edilir.

Sandbox: `ASTROLOVE/TEMP/PRODIGI_SANDBOX_TOKEN.json` (`{"api_key": "..."}`), Prodigi panelinde ayri uretilir; `pod-order-router` env=sandbox bunu okur. Ayni maskeleme kurallari gecerlidir.

## Etsy yeniden yetkilendirme — transactions_r (20 Eyl 2026)

Yonlendiricinin siparisleri okumasi icin token'a `transactions_r` gerekiyor
(7 Eyl olcumu: `GET /shops/{id}/receipts` -> 403 "requires scope: transactions_r").

- Betik: `scripts/etsy/etsy_yetki.py` (PKCE S256). Workflow: `pod-sablon-v4`
  mod=`yetki` (link uret) / `yetki_degistir` (kodu token'a cevir, confirm=`YETKI_DEGISTIR`) /
  `yetki_test` (salt okuma kaniti).
- Redirect URI (9 Agu 2026 ilk kurulumdan): `https://astrolove.art/oauth/callback`.
  Etsy uygulama ayarlarindaki kayitli deger budur, degistirilmez.
- Kapsam kaybolmaz: `link` modu canli `ETSY_TOKEN.json`'daki `scope`'u okur, uzerine
  eksikleri ekler. Olculen: eski `listings_r listings_w shops_r shops_w` ->
  yeni `listings_r listings_w shops_r shops_w transactions_r`.
  `listings_d` GEREKMEZ: depodaki tum `DELETE` cagrilari alt kaynaklara
  (images/videos/files) gider ve mevcut kapsamla calisir; ilan silme cagrisi yok.
  `email_r`/`profile_r` mevcut token'da yok, `/users/me` bunlarsiz calisiyor.
- keystring (client_id) degismez; hicbir GitHub secret'i guncellenmez.
- Tek kaynak: 70 Etsy workflow'unun 70'i token'i `gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json`
  dosyasindan ceker ve hepsi `concurrency: etsy-token` grubundadir. `degistir` bu tek
  dosyayi yeniler; eski surum `POD_5X7/YEDEK/ETSY_TOKEN_<zaman>.json` olarak saklanir.
- Baglanti ve PKCE dogrulayici yalniz Drive'a yazilir
  (`POD_5X7/ETSY_YETKI_LINK.txt`, `POD_5X7/ETSY_YETKI_PKCE.json`); loga/sohbete asla.
