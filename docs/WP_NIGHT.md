# GECE ZINCIRI (ADIM 2) - wallpaper hatti

Karar: 3 Eyl 2026 (Mo). Insan onayi beklenmez, YAYIN HARIC. Alt-ajan yok.
Her asamanin QC'si olculur; gorsel kusurda dur, sayisal esik olculen dogal
referansa gore yeniden tanimlanabilir (EK KURAL, gerekce rapora yazilir).

## Asamalar ve kapilar

| Asama | Ne uretilir | Nereye | QC kapisi (PASS/FAIL) |
|---|---|---|---|
| a | 78 x 16 wallpaper | `WALLPAPER/FINAL_V2/<CIFT>` | dosya basina: cekirdekte cikti=poster (ort<0.01, maks<=1), plakaya daha yakin piksel 0, JPEG turu posterin kendi q95 turunu 1.15 kat asmaz, tuval olcusu |
| b | 78 x 6 galeri gorseli | `WALLPAPER/MOCKUP_V2/<CIFT>` | `wp_mockup_render`: geri tespit <=1.5 px / inlier>=20 (Watch corr>=0.90), sahne disi fark <=1.0, murekkep degisimi >5, 3000x2250 q95 4:4:4 |
| c | 78 ilan videosu | `WALLPAPER/VIDEO_V2/<CIFT>` | ACIK (asagida) |
| d | 78 x 4 teslim ZIP | `WALLPAPER/DELIVERY/<CIFT>` | ZIP yeniden acilir: 5 girdi, ad listesi birebir, cihaz tuval olculeri, LICENSE bayt bayt, <= 20 MB (kademe 95->92->90) |
| e | Etsy medya yukleme | 78 ilan | yukleme sonrasi geri okuma: 6 gorsel rank 1-6, 1 video, 5 dosya; iki ardisik okuma ayni (10 sn, 3 deneme) |
| f | Son dogrulama | - | ilan basina 6 gorsel 3000x2250, 1 video, 5 dosya adi, baslik sablonu, 3.99 USD, bolum 60120017, state (pilot active, digerleri draft) |

## Kosu

- `wp-night` (asama a/b/c/d): `stage`, `shards` (paralel is), `limit` (parca
  basina cift, 0 = hepsi), `force` (STATE'te PASS olanlari yeniden uret).
  STATE: Drive `TEMP/WP_NIGHT_STATE.csv` (parca dosyalari birlestirilir).
  Kesilen kosu ayni girdilerle yeniden tetiklenir; PASS olan cift atlanir.
- `wp-media` (asama e + f): `dry_run` varsayilan true; `no_video`; `limit`,
  `pairs`, `quota_stop`. Tek Etsy kosusu (`concurrency: etsy-token`), token
  her kosuda Drive'a geri yazilir.
- `wp-full-chain` (3 Eyl, Mo karari): TEK workflow_dispatch kosusunda b -> c
  -> d -> (e+f) zinciri; yukaridaki script'leri AYNEN kullanir (yeni kod
  yalniz orkestrasyon). Girdiler: `shards`, `pairs`, `limit`, `upload_dry_run`,
  `quota_stop`. `upload_verify` isi `concurrency: etsy-token` ile digerlerine
  karsilikli disli.

## Pilot dosyalari

Asama a, `FINAL_V2/CANCER_LIBRA`'yi yeniden uretip uzerine yazar. Ozgun 16 dosya
once `ARCHIVE/FINAL_V2_PILOT_V1`'e kopyalanir (idempotent `archive` isi) ve
mockup/video referansi olarak ORADAN okunur: mockup masterlari ve ilan videosu
o dosyalarla uretildi, referans degisirse `wp_mockup_render`'in relight/paste
hesabi kayar.

## KARAR (3 Eyl, Mo): asama c yontemi sabitlendi

wp_video_render.py mevcut haliyle (SET01 sahnesi + `WA_WP_VIDEO_TOZ_V3.mp4`
master, asagidaki olcum) 78 cift icin kullanilir; guncelleme yok. Ayri bir
"V02_ZOOM" kaynagi / "Reel V03" recetesi (21-30 Agu, Colab donemi, farkli
olcek 1080x1350, KARAR 3 ile celisir) DEGERLENDIRILMEDI, kullanilmiyor.

## ACIK (tarihsel, asagidaki olcum asamasinda cozuldu): asama c (ilan videosu)

Pilotun ilan videosu `TEMP/WP_VIDEO_TEST/WA_WP_VIDEO_TOZ_V3.mp4`: SET01 sahnesi
(iki telefon, MB + CI), 1800x1350, 11.5 sn, 30 fps, 345 kare. Ekran icerigi
`EKRAN_MB_11S2.mp4` / `EKRAN_CI_11S2.mp4` (720x1600, 345 kare): wallpaper +
gliflerden yukselen toz + gliflerin sonmesi.

Olcum (3 Eyl): sahne durgun, ekran dortgeni SET01 kalibrasyonundan olcege
indirilip ECC ile rafine edilebiliyor (kaydirma -0.05, +0.42 px) ve ekran disi
fark 0 tutuluyor. Ancak ekran icinde `out = master + M*(warp(yeni) - warp(pilot))`
fark modu YETMIYOR: master ekraninda pilot murekkebi animasyon boyunca eriyor,
cikarma tam iptal etmiyor; sonuc karede iki ciftin isimleri ust uste kaliyor
(ARIES_LEO denemesi). Yani ilan videosu, ciftin kendi glif maskesinden toz
uretimi (parcacik motoru) gerektiriyor; kopyala-yapistir ile uretilemez.

Karar (Claude, EK KURAL geregi belirsizlikte kendi karari): asama c a/b/d/e/f
zincirini BEKLETMEZ. Once 1248 wallpaper + 468 galeri + 312 ZIP uretilir ve
medya (video haric) yuklenir; ilan videosu ayri is olarak, pilotun EKRAN
videolariyla olculen bir toz motoru portu ile uretilir ve once tek cift Mo'nun
gorsel onayina sunulur. Etsy tarafinda video olmayan ilan eksik degil, videosuz
yayina hazir; video sonradan `wp-media` ile eklenebilir (yayin komutu Mo'dan).
