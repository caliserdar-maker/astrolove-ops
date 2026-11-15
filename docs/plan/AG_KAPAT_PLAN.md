# Test agi kapatma: ortak modul PLANI (kod yok)

Durum: PLAN. Kod degisikligi yok. Dayanak commit: b1e21190 (aksi yazilmadikca tum dosya:satir bu commit'tedir).
Istek: Serdar 15 Kas, K4. Uygulama ayri gorev ve ayri onayla.

## 1. Bugun: ayni kapatma blogu kac yerde kopya

| Yer | Ne yapar |
|---|---|
| scripts/etsy/test_urun_ayar.py:16-30 | ssl onceden yuklenir; socket.socket.connect/connect_ex/sendto, create_connection, getaddrinfo, urllib.request.urlopen yamasi |
| scripts/etsy/test_urun_ayar.py:31-40 | sys.addaudithook kancasi (connect/sendto/sendmsg, AF_UNIX haric; getaddrinfo/gethostbyname/gethostbyaddr/getnameinfo) |
| scripts/etsy/test_ornament_metin_canli.py:24-30 | socket.socket sinifinin tamami, create_connection, urlopen yerine _ag_yok (yama bicimi urun_ayar'dan farkli) |
| scripts/etsy/test_ornament_metin_canli.py:31-40 | ayni kanca (kopya) |
| scripts/ops/test_workflows.py:20-25 (yama), :26-35 (kanca) | ayni yama + ayni kanca (kopya) |
| scripts/ops/test_workflows.py:38-44 | alt surec python3 icin sitecustomize.py: yama + kanca metni dizgi olarak ucuncu kez kopya |
| scripts/ops/test_workflows.py:45-48 | sahte ag araclari gh, curl, wget, rclone (exit 97), PATH'in onune |
| scripts/ops/test_workflows.py:49, :53-64 | PYTHONPATH'e sitecustomize dizini; subprocess.run sarmalanir, acik env verilene de PYTHONPATH eklenir |
| test/toplu-2 89c59bc3 scripts/etsy/test_ornament_metin.py:22-37 | K1 testi: urun_ayar blogunun birebir kopyasi (dorduncu kopya) |
| scripts/etsy/test_kupa_zam_1114.py:22-24 | yalniz socket.socket.connect, create_connection, urlopen; kanca yok, getaddrinfo/sendto/connect_ex acik |
| scripts/etsy/test_ornament_taslak.py:14-29, :30, :34 | urun_ayar ile ayni yama (kopya); kanca kendi kopyasi degil, `import test_urun_ayar as UT` (:34) ile kurulur |
| scripts/etsy/test_secret_gecis.py:28-33 | socket.socket ve create_connection yerine _ag_yok (ucuncu yama bicimi); kanca yok |
| scripts/etsy/p1_poster_kuru.py:66-76 | uretim kodunda gecici yama (connect, connect_ex, create_connection, getaddrinfo; geri() ile geri alinir); test degil, modul disinda kalir |

Risk: kanca b1e21190'da 4 yerde (test_urun_ayar.py:40, test_ornament_metin_canli.py:40, test_workflows.py:35 ve :43 dizgisi), K1 ile 5; ayri ayri degisirse sapar; test_workflows.py:43 dizgi kopyasi
elle esitlenir (ilk satir yorumu bile :26 ile ayni tutulmus). Ornek sapma bugun var: canli testi socket.socket'i
tamamen degistirir (:28), digerleri yalniz yontemleri.

## 2. Oneri: scripts/ops/ag_kapat.py (tek kaynak)

- `kapat(loopback=False)`: bugunku yama listesi (test_urun_ayar.py:25-30) + kanca (:31-40). Idempotent (ikinci cagri yeni kanca eklemez;
  audit kancasi kaldirilamaz, bu yuzden bayrak modulde tutulur).
- `sitecustomize_yaz(dizin)`: alt surec dosyasini dizgi kopyasi yerine `import ag_kapat; ag_kapat.kapat()` iki satiriyla yazar
  (test_workflows.py:38-44 yerine). Dizin PYTHONPATH'e modulun kendi dizini de eklenir.
- `sahte_araclar(dizin, araclar=("gh","curl","wget","rclone","git","nc","openssl","node","gcloud"))`: test_workflows.py:45-48'in genel hali.
- `run_sarmala()`: test_workflows.py:53-64 (acik env'e PYTHONPATH) tasinir.
- `denetle()`: K1 testindeki dogrudan _socket denetimi (89c59bc3 test_ornament_metin.py:73-77) ortak oz-test olur; her test bir satirla cagirir.
- Kendi testi: scripts/ops/test_ag_kapat.py (yama, kanca, AF_UNIX izni, loopback modu, sitecustomize alt surec, -I yolu belgelenmis acik).
- Ice aktarma: testler scripts/ops'u sys.path'e ekler (test_workflows zaten scripts/ops'ta; etsy testleri `Path(__file__).parents[1] / "ops"`).

Tahmini is: modul + kendi testi ~1,5 saat; 5 testin gecisi ~1 saat; CI listesine test_ag_kapat ekleme + test_workflows denetimi ~20 dk (tahmin).
Risk: ortak modul bozulursa CI listesindeki tum testler birden kirilir (tek hata, genis etki); yama sirasi onemli
(ssl/requests oncesi yuklenmeli, test_urun_ayar.py:16 yorumu) ve modulde korunmali.

## 3. CI listesindeki diger testler (ai-beyan-test.yml:18, :31-34, :40-41) bugun ne yapiyor

| Test | Bugunku ag durumu |
|---|---|
| scripts/etsy/test_ai_beyan.py | modul duzeyi kapatma yok (:139, :192, :245 eslesmeleri statik tarama dizgisi); :98-99 requests.request taklidi; :284 subprocess.run([sys.executable, "-c", ...]) alt surec kapatmasiz |
| scripts/etsy/test_ru_kapisi.py | :21 E.requests.request taklidi; :88 subprocess.run([sys.executable, betik]) alt surec kapatmasiz |
| scripts/etsy/test_beyan_marka_yaz.py | belgede "ag yok" (:2); socket/urlopen yamasi yok (grep 0) |
| scripts/etsy/test_pod_5x7_yaz.py | :62-63 _call AssertionError; socket yamasi yok |
| scripts/etsy/test_kota_esik.py | :30 E.requests.request taklidi; socket yamasi yok |
| scripts/etsy/test_kupa_galeri78.py | sahte Etsy/Drive (:2-4), :839 sahte rclone; socket yamasi yok |
| scripts/etsy/test_secret_gecis.py | :28-33 socket.socket + create_connection; :340-341 kendi sitecustomize'i (test_secret_gecis.alt_surec); :346 bash alt surec; kanca yok |
| scripts/etsy/test_canli_yapi_olc.py | :132-137 EC.requests.request/post taklidi; socket yamasi yok |
| scripts/etsy/test_ornament_taslak.py | :14-29 urun_ayar ile ayni yama; kanca :34 test_urun_ayar ice aktarimiyla kurulur ve :136'da denetlenir (tam sayilir; gecisde kopya yama silinir, cift kurulum olmamali) |
| scripts/etsy/test_etsy_kota_kilit.py | sahte GitHub kosulari (:5-8); socket yamasi yok |
| scripts/etsy/test_urun_ayar.py, test_ornament_metin_canli.py, scripts/ops/test_workflows.py | tam (yama + kanca), bkz. bolum 1 |
| scripts/etsy/test_kupa_zam_1114.py, test_ornament_metin.py | K2 ile listeye girer (test/toplu-2); durum bolum 1 |

Oneri sirasi (her biri tek satir `ag_kapat.kapat()` + calistirma): once yama/kanca olmayan 8 test (ai_beyan, ru_kapisi, beyan_marka_yaz,
pod_5x7_yaz, kota_esik, kupa_galeri78, canli_yapi_olc, etsy_kota_kilit), sonra kismi olanlar (kupa_zam_1114, secret_gecis), sonra ornament_taslak (UT bagimliligi kalkar),
en son kopyasi silinecek uc dosya. Her gecis: CI surumleriyle ve `unshare -rn` ile PASS sayisi ayni kalmali.
Risk: taklit yerine gercek socket'e yaslanan bir test (ornek: yerel sunucu) kapatmayla kirilabilir; bkz. bolum 6. Gecis basina ~5-10 dk (tahmin).

## 4. Alt surec yollari

- python3 (PYTHONPATH ile): sitecustomize kapsar (test_workflows.py:38-44, :49).
- python3 -I veya -E: PYTHONPATH yok sayilir, sitecustomize yuklenmez; -S: site modulu yuklenmez. Bugun acik oldugu kodda yazili
  (test_workflows.py:26 yorumu: "-I / Popen / Python disi araclar acik").
- subprocess.Popen / check_output dogrudan: test_workflows.py:64 yalniz subprocess.run'i sarar; Popen'e acik env verilirse PYTHONPATH eklenmez.
- sys.executable ile alt surec: test_ai_beyan.py:284, test_ru_kapisi.py:88 hicbir kapatma tasimaz.
Oneri: ag_kapat `Popen.__init__` duzeyinde sarar (run, check_output, call hepsi Popen'den gecer) ve argv'de python + -I/-E/-S gorurse
AssertionError verir (acik izin listesi parametresiyle). Kesin kapatma yalniz surec disi: CI'da `unshare -rn` (kullanici ad alani) ya da
runner ag kurali; bu ayri karar. Tahmini is ~45 dk. Risk: -I mesru kullaniliyor. b1e21190 scripts/ altinda cagri satirlari: cift tirnakli 7 (scripts/kupa_siparis/kupa_siparis.py:219, :254;
scripts/kapak78/sade_kart.py:48, :56, :64; scripts/kapak78/ci_renk/ci_renk_toplu.py:28; scripts/kapak78/kupa_kart78.py:180), tek tirnakli 4
(scripts/kapak78/kupa_kapak43.py:40, :42; scripts/kapak78/orchard_gorunum.py:39, :46); ayrica 3 belge satiri (ci_renk_karti.py:9, simd_calistir.py:6, :7).
.github/workflows altinda `python3 -I` / `python -I` 106 satir (git grep -c); test_workflows bunlarin bir kismini (kostugu adimlar) bash olarak kosar (:210, :319, :407);
Popen argv'si "bash" oldugu icin Popen duzeyi -I denetimi bunlari GORMEZ ve -I PYTHONPATH'i yok saydigi icin sitecustomize de yuklenmez; bu yol yalniz surec disi kapatmayla (unshare -rn) kapanir.
Bunlari test eden bir test Popen denetimiyle kirilir; yasak yerine izin listesi + uyari gerekebilir.

## 5. Sahte araclar

Bugun: gh, curl, wget, rclone (test_workflows.py:45). test_secret_gecis kendi araclar() dizinini kurar (:342, rclone/curl/sudo :2-3).
Eklenecek aday: git (fetch/push/ls-remote), nc, openssl (s_client), node, gcloud/gsutil/bq (ortamda kurulu ve proxy'ye ayarli;
CLAUDE.md degil, ortam bilgisi). Kural: testin kendi sahtesi onde kalir (test_workflows.py:45 yorumu). git icin dikkat: scripts/kapak78/test_p1g_kart.py:36 ve scripts/siparis_dijital/test_tag_kerning.py:30
origin'den `git fetch` yapar (CI_KOK / KISISEL_KOK verilmezse; CLAUDE.md:124 istisnasi); fetch'i reddeden sahte git bu ikisini kirar,
bu yuzden git sahtesi ya bu iki testte devre disi ya da girdi kokleri zorunlu olmali (karar gerekir). Yerel git
islemleri (diff, rev-parse, archive) de test icinde kullaniliyor olabilir; sahte git yalniz ag alt komutlarini (fetch, pull, push,
clone, ls-remote, remote update) reddedip digerlerini gercek git'e gecirmeli. Tahmini is ~30 dk. Risk: sahte git yanlis alt komutu
reddederse yerel git kullanan testler kirilir.

## 6. Loopback istisnasi

Yerel sahte HTTP sunucu kullanan testler: scripts/kapak78/test_galeri_tasi.py:49-54 (NO_PROXY=127.0.0.1, ThreadingHTTPServer
("127.0.0.1", 0)), test_galeri_tasi_v11.py:2, test_galeri_tasi_yd.py:2, test_yd_yedek.py:47-51, scripts/printful/test_pet_katalog.py:330-343,
scripts/printify/test_kolye_katalog.py:292-304. Bugunku kanca (test_urun_ayar.py:33-37) AF_INET 127.0.0.1 connect'i de reddeder;
bu testler bugun ai-beyan-test listesinde degil (ai-beyan-test.yml:31-34).
Oneri: `kapat(loopback=True)` yalniz connect hedefi 127.0.0.1 / ::1 ise gecirir; getaddrinfo yalniz "127.0.0.1", "::1", "localhost"
icin gercek cagriya gider; baska her ad reddedilir. NO_PROXY ayari testte kalir (proxy'ye gitmesin). Tahmini is ~30 dk + 6 testte deneme.
Risk: loopback modu yanlislikla varsayilan olursa yerel proxy (ortamdaki HTTPS_PROXY 127.0.0.1 portu ise) uzerinden dis aga cikis acilir;
bu yuzden varsayilan loopback=False ve proxy degiskenleri kapat() icinde bosaltilmali (karar gerekir).

## 7. Toplam

Tahmini is: ~4-5 saat (bolum 2-6 toplami, tahmin). Onerilen sira: 2 (modul + kendi testi) -> 3 (CI testleri) -> 4 -> 5 -> 6.
Her adim ayri commit, ayri dal; CI listesindeki PASS sayisi her adimda ayni kalir. Acik kararlar: (a) CI'da unshare -rn kullanilsin mi,
(b) loopback modunda proxy degiskenleri bosaltilsin mi, (c) -I/-E/-S alt surecleri yasak mi izinli mi,
(d) git fetch yapan iki testte sahte git nasil ele alinir.
