<!-- Yalnız plan. Kod, test, iş akışı YOK. Müşteri verisi, görsel, Drive adresi ya da kimliği YOK. -->

# PLAN: TASARIM KİLİDİ (otomasyon parça 3; kod düzeyi plan)

Serdar 12 Kas 2026: "Tek yeni sayfa: tasarım kilidinin yalnız KOD PLANI (belge). Kod yok." Kilit KODU için karar ayrıca
verilecek [görev]. Bu belge karar vermez: Serdar kararı gereken her yer bölüm 11.1'de seçenekleri ve sonuçlarıyla durur;
öneri yalnız 11.2'deki teknik sorularda vardır. Tasarım önerisi, seçenek sıralaması, ürün kararı yoktur.

## 0. Okunan kaynaklar, kısaltmalar, etiketler

Dallar `git fetch` ile alındı, yalnız `git show` ile okundu; depodaki hiçbir betik çalıştırılmadı.

| Kısaltma | Dosya | Dal, commit |
|---|---|---|
| TD | scripts/tasarim_deneme/tasarim_deneme.py | tasarim-deneme-dilim1, 57510062fe2cbee11a40d30d889a7df68f1b0d53 |
| TK | scripts/tasarim_deneme/tasarim_kapi.py | aynı |
| TT | scripts/tasarim_deneme/test_tasarim_deneme.py | aynı |
| UG | data/tasarim_deneme/urun/DENEME_YUVARLAK_1087.json | aynı |
| DP | docs/tasarim_deneme/PLAN_TASARIM_DENEME.md | plan/tasarim-deneme, 3fdcc5b52a8b5aeb64a44a467cd5fa0e5fc4f9f8 |
| UA | scripts/etsy/urun_ayar.py | urun-ayar/kod, 322e066e050c8d734635c39dcbc3f1c4fce87e93 |
| UP | docs/plan/URUN_AYAR_PLAN.md | plan/urun-ayar, 4857c6708d44c7c0d2db7e4271913dc659e37e48 |
| OS | scripts/printful/ornament_siparis.py | ornament-printful-katalog, c950151627b4aba29bdea8f75e4c533cea599424 |
| G78 | scripts/ornament_galeri/galeri78.py | aynı |
| SO | scripts/ops/siparis_onay.py | main, 5a3d85e41b15ca57a4468941b2763a107ce81f9d |
| KS | scripts/kupa_siparis/kupa_siparis.py | main, aynı |
| MK | scripts/kupa_printful/mockup.py | main, aynı |
| KSB | scripts/kapak78/kart_sablon.py | main, aynı |
| W | .github/workflows/ay-takvim-ornek.yml | main, aynı |
| CM | CLAUDE.md | main, aynı |
| AT | scripts/ay_takvim/ay_takvim_ornek.py | a9b1323 (TD:45 sabiti; main'in atası; main'de aynı dosya) |
| ATK | scripts/ay_takvim/ay_takvim_kapi.py | aynı |

Etiketler: [kod] = bu oturumda dosyadan okundu, yanında dosya:satır. [görev] = görev metnindeki Dayanak; bu oturum
doğrulayamaz (Project belgeleri, Drive ve OZET dosyaları okunmadı). [öneri] = teknik öneri (ürün ya da tasarım kararı değil).
[okunmadı], [ölçülmedi], [tahmin] = adı üstünde.

Okunmayanlar: ürün karar dosyası, OTOMASYON_KARAR_LISTESI_20261111 (CM:206 adını anar; depoda dosyası yok), "kilit
açılınca" tablosunun ilk satırı dışındaki satırları, hiçbir OZET / OLCUM dosyası, ornament motoru (deneme planının
OM atıfları bu oturumda açılmadı; DP atfıyla anılır), test_ai_beyan (CM:220 adını anar).

Koddan çıkan ve planı belirleyen olgular [kod]:

1. Araç ve karar kilidi kodu main'de DEĞİL: `scripts/tasarim_deneme/` yalnız tasarim-deneme-dilim1'de, `urun_ayar.py`
   yalnız urun-ayar/kod'da (`git cat-file -e origin/main:<yol>` ikisinde de yok).
2. OZET kendi kendini doğrulamaz: şema sürümü alanı yok (tek tanıtıcı `arac` dizesi, TD:994); OLCUM dosyasının sha'sını
   taşımaz (TD:965-967 alan listesi); aracın git commit'ini taşımaz, yalnız dosya sha256'larını (TD:993, 999).
3. `uret` ürün girdisini depodaki dosyadan değil OZET'in içinden okur (TD:1032); `urun_sha256` ve `kod_sha256` alanlarını
   denetlemez; yalnız katman sha'sını denetler (TD:1038-1039).
4. `uret` sert DUR almış seçenekte de "aynı" der: karşılaştırma `png_sha256` ve `durum` eşitliğidir (TD:1044); DUR'da
   ikisi de None / 'DUR' olduğu için eşittir ve çıkış 0 olur (TD:1048). Çıkış 0 "seçenek tamam" demek değildir.
5. Katman türü yalnız dosya adından gelir: ad `DENEME_` ile başlıyorsa 'deneme', değilse 'gercek' (TD:996). Adı
   değiştirilmiş deneme sembolü 'gercek' görünür.
6. Deneme sembolünün yan json'unda `deneme: true` vardır (AT:1694-1695); sembol_yukle sayı / bool alanları `yan_json`'a
   alır (AT:992); OZET bunu `sembol_katmani.olcum.yan_json` altında taşır (TD:997-998). Bu alan "deneme" kanıtıdır;
   yokluğu "gerçek" kanıtı değildir.
7. `alt_sinir` isteğe bağlıdır (TD:244, 292-296); yoksa gerçek ölçü kapısı kendiliğinden PASS yazar (TK:529-530).
8. Kaynak etiketi yalnız `mm_kaynak.tur` için sayılabilir değerdir (TD:117, 264-266). `guvenli.etiket`, `alt_sinir.kaynak`
   ve `alt_sinir.etiket` serbest metindir (TD:270, 294; UG:7, 10); `sekil` ve `baski_px` etiket taşımaz; tedarikçi şablonu
   için alan yoktur (TD:243-244).
9. Gerçek ölçü işaretleri öğe başına OLCUM dosyasındadır (TK:477-483, 498-501, 517-519); OZET yalnız sayıları taşır
   (TK:525-528, 537).
10. Araç `kod_sha256`'yı kendi klasöründeki `tasarim_*.py` dosyalarından toplar (TD:993). O klasöre konan her
    `tasarim_*.py` bütün yeni OZET'lerin içeriğini değiştirir.
11. Geri dönüş: istenen 'iki_yan' / 'isim_arasi' sessizce 'tek_satir' / logo 'yok' olur, yalnız etiket yazılır
    (TD:400-406, 992).
12. `ornek_en_kotu` ve `kesim` ürün şemasında kabul edilir (TD:244) ama 5751006'da hiçbir yerde kullanılmaz (TD ve TK'da
    başka geçişi yok): en kötü örnek seti ölçümü bugün yoktur.
13. Mevcut üretim / sipariş emsalleri bugün hiçbir kilit dosyası okumaz: girdileri komut satırı ve ortam değişkenidir
    (OS:133-135, 145; KS:469-477; MK:4; KSB:18; G78:7); beş dosyada "tasarim_kilit" geçmez.

## 1. P1: Kilit dosyası

### 1.1 Yer ve ad [öneri]

```
scripts/tasarim_kilit/tasarim_kilit.py         çekirdek: şema, kanonik sha, kilitle, dogrula, ac, denetle, damga
scripts/tasarim_kilit/ozet_oku.py              aracın OZET / OLCUM biçimini okuyan uyarlayıcı (araca bağlı TEK yer) + hazirla
scripts/tasarim_kilit/test_tasarim_kilit.py
data/tasarim_kilit/GERCEK_KATMAN.json          gerçek sembol katmanlarının sha256 kaydı (bölüm 4.3)
data/tasarim_kilit/ASAMA_BAGLI.json            "kilit açılınca" tablosu (Serdar'ın satırları, kendi yönünde) + iş adı -> aşama kodu eşlemesi (6.3)
data/tasarim_kilit/URETIM_KOD.json             aşama -> o aşamanın üretim kodu dosya listesi (parça 4 / 5 planından gelir; 5.3)
data/tasarim_kilit/<URUN>/KARAR_GIRDI_<NNN>.json   araçtan gelmeyen kararlar ve girdi kaynak etiketleri (bölüm 2)
data/tasarim_kilit/<URUN>/KILIT_<NNN>.json     kilit dosyası; yazıldıktan sonra DEĞİŞMEZ (yalnız `muhur` bloğu bir kez dolar)
data/tasarim_kilit/<URUN>/DURUM.json           ürünün geçerli kilidi ve geçmişi
.github/workflows/tasarim-kilit.yml            yalnız gerçek katman yolu seçilirse (soru S2, T2)
```

Kilit kodu `scripts/tasarim_deneme/` içine KONMAZ: TD:993 nedeniyle `tasarim_kilit.py` oraya girerse aracın her OZET'inde
`kod_sha256` değişir; ayrıca o klasörde başka oturum çalışıyor (CM:193 "Ayni koda ayni anda tek oturum dokunur").

`<URUN>` deseni aracın ürün adı desenidir: `[A-Z0-9_]{1,40}` (TD:115, 251). `<NNN>` = `kilit_no`, 001'den başlar.

Birden çok ürün: ürün başına ayrı klasör. Aynı ürünün yeniden kilitlenmesi: yeni `KILIT_<NNN+1>.json` + `onceki` alanı;
eski dosya silinmez ve değişmez; hangisinin geçerli olduğunu yalnız `DURUM.json` ve gizli Drive'daki açma kaydı söyler
(bölüm 6). Bir ürünün birden çok baskı alanı (karar 2: boy ya da oran) varsa tek kilitte `yuzey` listesi (soru T9).

### 1.2 Şema, sürüm 1

Tür kısaltmaları: s = dize, i = tam sayı, f = sayı, b = bool, sha = 64 hane küçük harf onaltılık, [] = liste, {} = sözlük.
Bilinmeyen anahtar, eksik anahtar, yanlış tür = DUR (emsal UA:6, 29-36).

| Alan | Tür | İçerik | Kaynak |
|---|---|---|---|
| sema | i | 1 | bu plan |
| urun | s | ürün adı (klasör adıyla aynı) | KARAR_GIRDI |
| kilit_no | i >= 1 | | hazirla |
| onceki | null / {kilit_no: i, kilit_sha256: sha} | bir önceki kilit | DURUM.json |
| girdi.yuzey[] | [] | baskı alanı başına bir kayıt (aşağıda) | |
| girdi.yuzey[].yuzey_ad | s | karar 2'deki seçeneğin adı | KARAR_GIRDI |
| girdi.yuzey[].urun_dosya | s | depo yolu, `data/tasarim_deneme/urun/<AD>.json` | KARAR_GIRDI |
| girdi.yuzey[].urun_sha256 | sha | o dosyanın sha256'sı | OZET `urun_sha256` (TD:995) + depo dosyası |
| girdi.yuzey[].urun | {} | dosyanın içeriği birebir | OZET `urun` (TD:995) |
| girdi.yuzey[].kaynak | {} | `sekil`, `baski_px`, `gercek_mm`, `guvenli`, `alt_sinir`, `sablon` için {tur, not}; tur: 'resmi' / 'ölçüm' / 'varsayım' / 'serdar'; `sablon` ayrıca {sha256: sha / null} | KARAR_GIRDI (olgu 8: araç bunu sayılabilir biçimde taşımıyor) |
| karar.k1 ... karar.k7 | {} | her biri {deger: {}, ref: s, tarih: s (YYYY-AA-GG)}; `deger` biçimi bölüm 2.1 | KARAR_GIRDI; k3 ve k4 ayrıca araçtan |
| kanit[] | [] | yüzey başına bir kayıt (aşağıda) | hazirla |
| kanit[].yuzey_ad | s | | |
| kanit[].secim | {ozet_sha256: sha, secenek_no: i, secenek_ad: s} | seçimin izi; KİMLİK DEĞİL | OZET dosyası; TD:452, 966 |
| kanit[].ayar | {} | TAM ayar sözlüğü | OZET secenek `ayar` (TD:966) |
| kanit[].ayar_sha256 | sha | ayarın kanonik sha'sı (1.3) | hesap |
| kanit[].ayar_kilitli_sha256 | sha | ayarın, `karar.k4.deger.degisebilir` anahtarları ÇIKARILMIŞ halinin kanonik sha'sı (5.2, D09) | hesap |
| kanit[].arac | {commit: s (40 hane), kod_sha256: {}, ay_sha: s, motor_sha: s, ornament_sha: s, kaynak_sha256: {}, paketler: {}} | aracın sabitlendiği commit ve OZET'teki sürüm alanları | `commit` hazirla argümanı; diğerleri OZET (TD:999-1000) |
| kanit[].katman | {cift: s, sha256: sha, olcum: {}, kayit: 'gercek' / 'deneme'} | `kayit` dosya adından DEĞİL GERCEK_KATMAN.json'dan | OZET `cift`, `sembol_katmani` (TD:995-998); 4.3 |
| kanit[].ornek | {png_sha256: sha, tuval: [i, i], k: {}, altin_sirasi: [], olcum_sha256: sha, olcum_ozet: {}} | onaylı örnek ve kapı özeti | OZET secenek (TD:966-967); `olcum_sha256` hazirla'nın kendi yeniden üretiminden |
| kanit[].yeniden | {tarih: s, ortam: 'yerel' / 'actions', kosu: null / {run_id: i, run_attempt: i, sha: s}, png_sha256: sha, ayni: true} | hazirla'nın yaptığı yeniden üretim | hazirla |
| kanit[].gercek_olcum | null / {} | yalnız S2 (b) seçilirse; biçimi 4.3 | Actions kaydı |
| kanit[].olcer | {fail: [s], kabul: [{kapi: s, ozet: s, ref: s}]} | ölçer FAIL adları ve kayıtlı kabuller | OZET `olcum_ozet.olcer_fail` (TK:533, 535); KARAR_GIRDI `olcer_kabul` |
| kanit[].girdi_kabul | [{alan: s, ref: s}] | 'varsayım' / eksik alt sınır için kayıtlı kabuller (S4, S5) | KARAR_GIRDI `girdi_kabul` |
| kanit[].isaret_liste_sha256 | sha | kabullerin dayandığı ISARET_LISTESI.json'un sha256'sı (bölüm 3) | KARAR_GIRDI |
| hat | {arac_yolu: {<asama>: b}, sert: [s]} | aşama başına "son ürün aracın çizim yolundan mı üretilir" (S7 birinci soru) ve ürün hattında sert sayılan kapı adları (S7 (a)) | KARAR_GIRDI `arac_yolu`, `hat_sert` |
| kanit[].etiket | {taban: s, taban_etiket: s, geri_donus: [s]} | | OZET (TD:994) ve secenek `geri_donus` (TD:966) |
| karar_sha256 | {girdi: sha, k1: sha ... k7: sha, olcer: sha, hat: sha} | blok sha'ları; her bloğun kapsadığı alanlar 1.4'te | hesap |
| muhur | {kilitli: b, kilit_sha256: sha / null, onay_sha256: sha / null, kilit_tarihi: s / null} | ADAY'da kilitli false, üç alan null | kilitle |

`kilit_sha256` = `muhur` bloğu HARİÇ dosyanın kanonik JSON'unun sha256'sı (emsal: UA:148-151, `kilit` bloğu hariç).

OZET'in koşu düzeyi anahtar kümesi, 5751006'da TAM 21 anahtar [kod; TD:994-1003, 1012]: `arac`, `not_`, `taban`,
`taban_etiket`, `geri_donus`, `urun`, `urun_sha256`, `mm_px`, `cift`, `sembol_katmani`, `ay_sha`, `motor_sha`,
`ornament_sha`, `kaynak_sha256`, `kod_sha256`, `paketler`, `butce`, `secenek`, `musteri_verisi`, `pafta`,
`sure_toplam_sn`. Seçenek düzeyi TAM 17 anahtar [kod; TD:965-967]: `no`, `ad`, `tur`, `durum`, `kod`, `neden`, `ayar`,
`degisen`, `geri_donus`, `satir`, `sutun`, `png_sha256`, `tuval`, `k`, `altin_sirasi`, `olcum_ozet`, `sure`.

Kilide BİREBİR alınanlar: koşu düzeyi `taban`, `taban_etiket`, `urun`, `urun_sha256`, `cift`, `sembol_katmani.sha256`,
`sembol_katmani.olcum`, `ay_sha`, `motor_sha`, `ornament_sha`, `kaynak_sha256`, `kod_sha256`, `paketler`; seçenek düzeyi
`no`, `ad`, `ayar`, `geri_donus`, `png_sha256`, `tuval`, `k`, `altin_sirasi`, `olcum_ozet` (anahtarları TK:535-544).
Yalnız H01'de kullanılan (kilide yazılmayan): `arac`. ALINMAYANLAR: `sembol_katmani.tur` (olgu 5), `not_`, koşu düzeyi
`geri_donus` (seçeneklerin birleşimidir, TD:992; kilide seçeneğinki girer), `mm_px` (ürün girdisinden türer, TD:305-307),
`butce`, `pafta`, `musteri_verisi`, `sure_toplam_sn`, seçenek `tur`, `kod`, `neden`, `degisen`, `satir`, `sutun`, `sure`;
`durum` alınmaz ama 'tamam' olması kapıdır (4.1).

### 1.3 Kilitlenen seçeneğin kimliği

Seçenek numarası ve adı kimlik değildir: ad `SEC_<no>_<tur>` üretim sırasından gelir (TD:452) ve iki seçenek aynı ayarı
taşıyabilir [görev: ilk koşuda iki seçenek aynı ayar ve aynı PNG sha256]. Kimlik içerikten türetilir [öneri]:

- `ayar_sha256` = OZET'ten okunan TAM ayar sözlüğünün kanonik JSON'unun sha256'sı. Kanonik kural UA:148-151 ile aynı:
  `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))`, UTF-8. Sözlük yeniden biçimlenmez (1 ile 1,0
  ayrı JSON'dur; OZET'te nasıl yazılıysa öyle alınır).
- Tam kimlik beşlisi: (`urun_sha256`, `ayar_sha256`, `katman.sha256`, `arac.commit`, `ornek.png_sha256`). İlk dördü
  girdiyi, beşincisi çıktıyı sabitler; `urun_sha256` `girdi` bloğunda, diğer dördü `k4` bloğundadır (1.4).
- Kapı (4.1, H04): OZET'te aynı `ayar_sha256`'yı taşıyan bütün seçeneklerin `durum` ve `png_sha256` değeri aynı olmalı;
  değilse DUR (aynı ayar iki farklı görsel vermiş demektir).

### 1.4 Blok sha'larının kapsamı (her alan TAM bir blokta)

Blok sha'sı = aşağıdaki alanlardan kurulan sözlüğün kanonik JSON'unun sha256'sı (kural 1.3). Liste kapalıdır; şemaya
eklenen her yeni alan bu tabloya da eklenir (test: şemadaki her alan tam bir satırda geçer).

| Blok | Kapsadığı alanlar |
|---|---|
| girdi | `girdi` (bütün yüzeyler: `yuzey_ad`, `urun_dosya`, `urun_sha256`, `urun`, `kaynak`) + her `kanit[].girdi_kabul` |
| k1 | `karar.k1` |
| k2 | `karar.k2` |
| k3 | `karar.k3` + her `kanit[].ornek.altin_sirasi` |
| k4 | `karar.k4` + her kanıt kaydının `yuzey_ad`, `secim`, `ayar`, `ayar_sha256`, `ayar_kilitli_sha256`, `arac`, `katman`, `ornek` (`altin_sirasi` hariç), `yeniden`, `gercek_olcum`, `etiket` alanları |
| k5 | `karar.k5` (şema 2'de stil başına kanıt alanları da; bölüm 7) |
| k6 | `karar.k6` + her `kanit[].isaret_liste_sha256` |
| k7 | `karar.k7` |
| olcer | her `kanit[].olcer` (ölçer FAIL adları ve kabuller; karar 6 DEĞİL, S3'ün konusu) |
| hat | `hat` (`arac_yolu`, `sert`) |
| (blok dışı, `kilit_sha256` içinde) | `sema`, `urun`, `kilit_no`, `onceki`: kimlik alanları; aşama geçersizliği doğurmaz |
| (blok dışı, `kilit_sha256` dışında) | `muhur` ve `karar_sha256`'nın kendisi |

`girdi`, `olcer` ve `hat` blokları karar numarası değildir: Serdar'ın "kilit açılınca" tablosu karar numaralarıyla yazılıdır
[görev]; bu üç blok değişince hangi işlerin geçersiz olacağı o tabloda yoksa soru S15. Cevap gelene kadar `denetle` bu
bloklardaki değişimde 'tanımsız' döner (6.3).

### 1.5 KARAR_GIRDI_<NNN>.json şeması (`hazirla`'nın girdisi; Code oturumu Merkez'in görev metninden yazar)

| Alan | Tür | İçerik |
|---|---|---|
| sema | i | 1 |
| urun | s | ürün adı |
| kilit_no | i | hazırlanacak kilidin numarası |
| yuzey[] | [{yuzey_ad: s, urun_dosya: s, kaynak: {sekil, baski_px, gercek_mm, guvenli, alt_sinir, sablon}}] | `kaynak` alt alanlarının her biri {tur: s, not: s}; `sablon` ayrıca {sha256: sha / null} |
| karar.k1 ... k7 | {deger: {}, ref: s, tarih: s} | `deger` biçimleri 2.1 tablosunda; k4'te yalnız `alan_sinir` ve `degisebilir` (ayar araçtan gelir); k3'te `ogeler` |
| karar.k6.deger.ogeler[] | [{yuzey_ad: s, oge: s, isaret: [s], karar: s}] | işaret metinleri ön koşunun ISARET_LISTESI.json dosyasından AYNEN (bölüm 3) |
| olcer_kabul[] | [{yuzey_ad: s, kapi: s, ozet: s, ref: s}] | yalnız S3 kabul yolunu açarsa |
| girdi_kabul[] | [{yuzey_ad: s, alan: s, ref: s}] | yalnız S4 / S5 kabul yolunu açarsa |
| hat_sert[] | [s] | ürün hattında sert sayılacak kapı adları; yalnız S7 (a) seçilirse; kilitte `hat.sert` |
| arac_yolu | {<asama>: b} | aşama başına: son ürün aracın çizim yolundan mı üretilir (S7 birinci sorunun cevabı; Merkez'den); kilitte `hat.arac_yolu` |
| isaret_liste_sha256 | sha | kabullerin dayandığı ISARET_LISTESI.json dosyasının sha256'sı |

Bilinmeyen anahtar, eksik anahtar, yanlış tür = girdi hatası (çıkış 3).

## 2. P2: Kararlar 1-7 ve Serdar sözü

### 2.1 Kararların kilitteki karşılığı

| Karar [görev] | Araçtan gelen [kod] | Araçtan gelmeyen | Kilitte `deger` |
|---|---|---|---|
| girdi (şekil, baskı px, mm, alt sınır, şablon; kaynak etiketiyle) | `urun` sözlüğü, `urun_sha256` (TD:995) | alan alan kaynak etiketi (olgu 8); şablon sha'sı | `girdi.yuzey[]` |
| 1 ilan birimi | yok | değer | {birim: s} |
| 2 ürün seçenekleri (boy / oran, baskı tekniği) | boy / oran dolaylı: yüzey başına ürün girdisi; baskı tekniği için araçta alan yok (TD:243-244) | seçenek adları, teknik | {secenekler: [{yuzey_ad: s, ad: s}], baski_teknigi: s} |
| 3 öğeler | öğe listesi: OLCUM `kapi.olcer.oge_sayisi.beklenen` (TK:393-395) + 'sembol'; OZET `altin_sirasi` (TD:786) | Serdar'ın öğe listesi | {ogeler: [s]}; kapı: iki liste aynı (H13) |
| 4 yerleşim + kişiselleştirilen her alanın sınırı | yerleşim: `ayar` (TD:966). Alan sınırı: araçta yalnız isim satırı genişliği ölçülür (TK:446-453); karakter sınırı ve en kötü örnek ölçümü yok (olgu 12) | alan sınırları; hangi ayar anahtarlarının kişiselleştirme olduğu | {alan_sinir: [{alan: s, en_cok_karakter: i, not: s}], degisebilir: [ayar anahtarı]}; yerleşim `kanit[].ayar` |
| 5 renk ve doku, stil seti | bugün yok: tek görünüm (DP:413-414) | stil seti | şema 1'de yalnız {tek_gorunum: true} yazılabilir; bunun "karar 5 tamam" sayılıp sayılmayacağı S14 (ek); bölüm 7 |
| 6 gerçek ölçü uyarıları | işaretli öğeler: OLCUM `oge.<ad>.isaret` (olgu 9) | her işaret için Serdar'ın "kabul" sözü | {olcut: {yazi: s, cizgi: s}, ogeler: [{yuzey_ad: s, oge: s, isaret: [s], karar: 'kabul'}]} |
| 7 benzer tasarım taraması | yok | sonuç | {sonuc: s, tarama_sha256: sha / null} |

Araçtan gelmeyen değerler kilide tek yoldan girer [öneri]: Genel Merkez, ürün karar dosyasındaki satırlardan değerleri
görev metnine yazar; Code oturumu bunları `KARAR_GIRDI_<NNN>.json` dosyasına aynen geçirir; `hazirla` dosyayı şemayla
doğrular ve kilide kopyalar. Her kararın `ref` alanı ürün karar dosyasındaki satırı adlandırır (tarih + başlık; Drive
adresi DEĞİL), `tarih` o satırın tarihidir. Kod ürün karar dosyasını okuyamaz [görev]; değerlerin o dosyayla aynı olduğunu
kod kanıtlayamaz. Bağ şöyle kurulur: Merkez, ADAY kilidin değerlerini karar dosyasıyla karşılaştırır ve ancak ondan sonra
onay kaydını yazar (2.2); onay kaydı `kilit_sha256`'yı taşıdığı için onay o değerlerin tamamına bağlanır.

"Yerleşime dön" kararı kilide giremez: bir işaret için karar 'kabul' değilse ya da eksikse kilit DUR verir (H10).

`degisebilir` (kişiselleştirme anahtarları): ayar sözlüğü örnek isim ve örnek metni de taşır (`isim1`, `isim2`, `satirlar`;
TD:122-124, 137) ve sipariş üretiminde bunların yerine müşterinin değeri gelir. Hangi anahtarların siparişte değişebileceği
karar 4'ün parçasıdır ("kişiselleştirilen her alan") ve KARAR_GIRDI'den gelir; plan liste önermez. Kapı (H13): her
`degisebilir` anahtarı aracın ayar anahtarlarından biridir (TD:122-124) ve `alan_sinir`'da karşılığı vardır. Listede
olmayan HER anahtar kilitlidir; tüketen onu değiştiremez (5.2, D09). `alan_sinir[].alan` bir ayar anahtarının adıdır
(serbest metin değil); liste değerli anahtarda (`satirlar`) `en_cok_karakter` satır başınadır ve kayıt ayrıca `en_cok_satir: i`
taşır. Çift, ayar anahtarı değildir (araçta tek çifte sabit, TD:105). Aynı ayarın başka çiftte çizilebildiği [ölçülmedi]:
araç bugün yalnız CANCER_LIBRA ile koşar; diğer çiftler S14 (c)'nin konusudur.

### 2.2 Onay kaydı ve ürün karar dosyasıyla bağ

Emsal [görev]: kütüphanede "Onay sözü gizli Drive'da; depoda yalnız ayar ve sha"; kart kilidinde "söz gizli Drive'da, kartta
sha". Karar kilidi kodu bu kalıbı uygular [kod]: depo yalnız `onay_sha256` tutar, kapı yerel yoldaki kaydın sha'sını ve
kaydın `urun`, `ayar_sha256`, `onay_sozu`, `tarih` alanlarını denetler (UA:210-229; UP:163-168). Tasarım kilidinde sözün
nerede duracağı Serdar kararıdır (S8). Şema tek biçimde çizilebildiği için aşağıdaki alanlar emsal kalıbıyla (söz Drive'da)
çizildi; bu bir tercih beyanı değildir. S8'de söz için (b) seçilirse değişen yerler: `muhur` bloğuna `onay_sozu` ve `tarih`
alanları eklenir; Drive kaydı ve D03 aynen kalır.

Onay kaydı (gizli Drive; depoya girmez), ad `ONAY_TASARIM_<URUN>_<NNN>.json`:

| Alan | Tür | İçerik |
|---|---|---|
| tur | s | 'tasarim_kilit' |
| urun, kilit_no | s, i | |
| kilit_sha256 | sha | ADAY dosyanın `hazirla` çıktısındaki sha'sı |
| onay_sozu | s | Serdar sözü birebir [görev: "tasarım kilitlensin"] |
| tarih | s | YYYY-AA-GG |
| karar_dosyasi_ref | s | ürün karar dosyasındaki kilit satırının adı |
| ornek | [{yuzey_ad: s, png_sha256: sha, yol: s}] | Serdar'ın gördüğü onaylı örnek; `yol` Drive yoludur ve YALNIZ bu kayıtta durur |
| olcer_kabul, girdi_kabul | [] | S3 / S4 / S5 kabul gerektirirse Serdar sözleri birebir |
| yazan | s | 'Genel Merkez' |

Kim yazar: Genel Merkez (Serdar'ın sözünü alan sayfa). Code oturumu onay kaydı YAZMAZ ve içeriğini üretmez [öneri];
gerekçe: kilidi hazırlayan ile onayı kaydeden ayrı olsun. Ürün karar dosyasındaki satır [görev: "tarih, Serdar sözü
birebir, kilitlenen kararların değerleri, onaylı örnek dosyası: Drive yolu + sha"] Merkez'in işidir; satıra `kilit_no` ve
`kilit_sha256` de yazılırsa belge ile kod aynı şeyi gösterir (soru S11).

Sahte ya da eksik onay nasıl engellenir, ve sınırı:

- Eksik: kayıt yoksa, okunamıyorsa, sha'sı `muhur.onay_sha256` değilse ya da alanları kilide bağlanmıyorsa `kilitle`
  mühürlemez ve `dogrula` DUR verir. Atlama bayrağı, ortam değişkeni, "kayıt yoksa geç" dalı YOKTUR (emsal: SO:57-79 her
  eksikte reddeder; UA:217-218 "onay kaydi yok").
- Elle `kilitli: true` yazmak yetmez: `kilit_sha256` yeniden hesaplanır ve Drive'daki kayıt o sha'yı taşımalıdır.
- Hazırlama ile onay arasında değişen dosya reddedilir (emsal SO:122-141): `kilitle` ADAY'ın sha'sını yeniden hesaplar.
- Onaylı örnek = kilitlenen örnek: kayıttaki her `ornek.png_sha256`, kilitteki `kanit[].ornek.png_sha256` ile aynı olmalı.
- Kabuller: onay kaydındaki `olcer_kabul` ve `girdi_kabul` listelerinin kapı / alan adları, kilitteki `kanit[].olcer.kabul`
  ve `kanit[].girdi_kabul` ile aynı olmalı (`kilitle` ve D03 sınar); kilitte olup kayıtta sözü olmayan kabul = DUR.
- SINIR (açık yazılır): kod Serdar'ın sözünü doğrulayamaz. Hem depoya hem gizli Drive'a yazabilen biri tutarlı bir sahte
  çift üretebilir. Kapının kanıtladığı şudur: "depodaki kilit, Drive'da Merkez'in yazdığı bir kayda bağlı ve ikisi de
  sonradan değişmedi". Sözün gerçekliği Merkez'in kaydıdır (ürün karar dosyası satırı).

### 2.3 Herkese açık depoda ne durur

| Depoda durabilir | Depoda DURAMAZ |
|---|---|
| ayar sözlüğü (örnek isim ve örnek metin dahil; araç girdisi yalnız örnektir, DP:349-353), ürün girdisi, sha256 ve commit değerleri, kapı ölçüm özetleri, `ref` adları | Drive adresi ya da kimliği, görsel, kota bilgisi, müşteri verisi, token [görev: bu görevin veri kuralı] |

S8'e bağlı olanlar (iki sütundan birine Serdar'ın cevabıyla girer): Serdar sözü; kararlar 1, 2, 7'nin değerleri; karar 6
kabul listesi.

Kod, ayardaki ismin örnek mi müşteri verisi mi olduğunu ayırt edemez (DP:349-353); kilide giren ayar depoya girdiği için
"girdi yalnız örnek" kuralı burada da süreç kuralıdır ve görev metnine yazılır.

## 3. P3: Kilit nasıl üretilir

İki adım; ikisi arasında Serdar onayı durur (emsal: SO `hazirla` / `onayla`, SO:158-171).

Adım 1, `hazirla` (ADAY üretir; mühür yok):

```
tasarim_kilit.py hazirla --urun <URUN> --karar KARAR_GIRDI_<NNN>.json --arac-commit <40 hane>
    --yuzey <AD> --ozet OZET.json --secenek <N> --katman <P.png> --kaynak <K>      (yüzey başına yinelenir)
    --cikti <D>
```

- `--kaynak`, `--katman`, `--ozet`, `--secenek` aracın `uret` argümanlarıdır (TD:1067-1070). `hazirla`, aracı
  `git archive <arac-commit>` kopyasından AYRI SÜREÇTE `uret` ile çalıştırır (TD:1025-1048); aracı içe almaz.
- Çıktı: `KILIT_<NNN>.json` (muhur.kilitli false), `HAZIRLIK_RAPOR.json` (her kapı PASS / FAIL + neden), tek satır
  `kilit_sha256`. Bir kapı FAIL ise ADAY yazılmaz. Çıkış kodları: 0 tamam, 3 girdi hatası, 4 DUR (kapı FAIL), 2 çöküş.
  Aracın 1 kodu (bir seçenek sert DUR ya da yeniden üretim sha'sı farklı; TD:26-27, 1048) `hazirla`'da KULLANILMAZ: `uret`
  1 dönerse H06 FAIL sayılır ve `hazirla` 4 ile çıkar.
- İki geçiş (karar 6 ve ölçer kabulleri Serdar'ın gördüğü değerlere dayansın diye): önce `hazirla --on` koşar; H01-H08'i
  uygular, ADAY yazmaz, `ISARET_LISTESI.json` yazar (yüzey ve öğe başına H06 koşusunun OLCUM'undaki `isaret` metinleri +
  ölçer FAIL adları ve özetleri + geri dönüş etiketleri). Merkez bu listeyi Serdar'a gösterir; kabuller ve listenin sha'sı
  KARAR_GIRDI'ye yazılır (1.5). Sonra `hazirla` (tam) koşar: H06'yı yeniden yapar ve yeni OLCUM'dan çıkan listenin sha'sı
  KARAR_GIRDI'deki `isaret_liste_sha256` ile aynı değilse DUR (Serdar'ın görmediği bir değer kabul edilmiş sayılmaz).
  Aynı ayar, katman ve kodla OLCUM'un her koşuda aynı çıkması [ölçülmedi]; çıkmıyorsa bu kapı DUR verir, gevşetilmez.
- Kim çalıştırır: Merkez'in görev metniyle bir Code oturumu. Nerede: soru T2 (gerçek katman yerelde yok; S2'ye bağlı).

OZET nereden gelir: OZET depoda değildir [görev]. `hazirla` OZET'i yerel bir yol olarak alır; onu oraya koyan koşuya göre
iki durum: (i) yerel koşu: aracı koşturan oturumun çalışma klasöründen ya da Merkez'in verdiği dosyadan; (ii) Actions
koşusu: iş akışı Drive'dan indirir (yer plana yazılmaz; soru T6). İki durumda da `hazirla` OZET'e GÜVENMEZ: `ozet_sha256`
kaydedilir, içerik H01-H06 ile yeniden doğrulanır, örnek yeniden üretilir.

Adım 2, `kilitle` (mühürler):

```
tasarim_kilit.py kilitle --urun <URUN> --no <NNN> --onay-klasor <D>
```

`<D>` ürünün onay klasörünün tam yerel kopyasıdır (5.2, D04'teki KLASOR_LISTE.json ile). Onay kaydını doğrular (2.2), zinciri
doğrular (önceki mühürlü her kilidin açma kaydı klasörde ve DURUM'da; 5.2 D02), `muhur` bloğunu doldurur, `DURUM.json`'u
günceller. Onay kaydı Drive'da olduğu için bu adımın nerede koşacağı soru T2.

Aracın kod dosyalarına dokunmak gerekir mi: HAYIR, şema 1 için gerekmez. Kilit aracı aracın yalnız iki dış yüzünü
kullanır: OZET / OLCUM dosya biçimi ve `uret` komutu. Dokunmadan yapmanın bedeli olgu 2-5'in kilit tarafında telafi
edilmesidir (H01, H05, H06, H07). Aracın değişmesi kolaylaştırırdı ama zorunlu değildir (soru T3, T4; değişiklik yerleri:
TD:994 şema sürümü, TD:967 OLCUM sha'sı, TD:996 katman türü). Bunlar TASARIM ARACI oturumunun dosyalarıdır.

## 4. P4: Kilitleme ön koşulları

### 4.1 `hazirla` kapıları (hepsi sert; biri FAIL ise ADAY yok)

| No | Kapı | Koşul | Dayanak |
|---|---|---|---|
| H01 | OZET biçimi | Katı JSON (yinelenen anahtar, NaN reddi; emsal TD:410-423); `arac` dizesi uyarlayıcının tanıdığı sürüm; koşu ve seçenek anahtar kümeleri TAM o sürümünki (fazla / eksik = DUR "biçim tanınmadı"); `olcum_ozet.sert_fail` ve `olcer_fail` içindeki her ad uyarlayıcının tablosunda | olgu 2; TD:965-967, 994-1003; TK:532-544 |
| H02 | ürün girdisi | OZET `urun_sha256` = depodaki `urun_dosya`'nın sha256'sı VE OZET `urun` = o dosyanın içeriği; dosya `git check-ignore` dışı ve commit'li | olgu 3; TD:995, 1032 |
| H03 | seçenek tamam | `no` = N olan TAM bir kayıt; `durum` 'tamam'; `kod` null; `png_sha256` sha; `olcum_ozet.sert_fail` boş | TD:788-792, 1028-1030; TK:532, 535 |
| H04 | kimlik | aynı `ayar_sha256`'lı seçeneklerin `durum` ve `png_sha256` değeri aynı | 1.3 |
| H05 | araç kodu | `--arac-commit` içindeki `scripts/tasarim_deneme/tasarim_*.py` dosya kümesi ve sha256'ları = OZET `kod_sha256`; commit origin/main'in atası (soru T3) | olgu 1, 2, 10; TD:993 |
| H06 | yeniden üretim | sabitlenmiş kodla ayrı süreçte `uret`: çıkış 0 VE `<ad>_YENIDEN.json` `ayni` true VE `durum` 'tamam' VE `png_sha256` = OZET'teki VE `hazirla`'nın üretilen PNG dosyasından kendi hesapladığı sha256 aynı. OLCUM dosyası bu koşudan alınır, `olcum_sha256` buradan yazılır | olgu 4; TD:1044-1048, 799 |
| H07 | katman | `katman.kayit` şöyle yazılır: sha GERCEK_KATMAN.json'da o çift için kayıtlıysa 'gercek'; değilse 'deneme' (OZET `sembol_katmani.olcum.yan_json.deneme` true olması ek 'deneme' kanıtıdır; dosya adı hiçbir yönde kanıt değil). PASS koşulu S2'ye göre: (a) `kayit` 'gercek' olmalı; (b) `kayit` iki değerden biri olabilir, ama `gercek_olcum.katman_sha256` kayıtlı olmalı; (c) engellemez, yalnız yazar | olgu 5, 6; 4.3 |
| H08 | gerçek katman ölçümü | S2'nin cevabına göre (4.3). Bugün yol yok: bu kapı her kilitte FAIL 'gercek_yol_yok' verir | 4.3 |
| H09 | ölçer FAIL'ler | S3'ün cevabına göre (4.4) | TK:533 |
| H10 | karar 6 | H06 koşusunun OLCUM'undaki `isaret` satırlarından S6'nın cevabıyla karar 6'ya giren türler (yazı ölçütü, çizgi ölçütü, taşma satırı girer mi) için: her satıra KARAR_GIRDI'de aynı metinle 'kabul' kaydı; fazla ya da eksik kayıt DUR; liste sha'sı = `isaret_liste_sha256` (bölüm 3, iki geçiş). S6 cevaplanmadan H10 yazılamaz. `alt_sinir` yoksa S5 | olgu 7, 9 |
| H11 | girdi kaynağı | S4'ün cevabına göre: `girdi.yuzey[].kaynak` içindeki 'varsayım' alanlar; ayrıca `kaynak.gercek_mm.tur` = OZET `urun.mm_kaynak.tur` (iki kaynak çelişmesin) | olgu 8; TD:264-266 |
| H12 | etiketler | `geri_donus` boş değilse S3 (d) | olgu 11 |
| H13 | kararlar tam | k1-k7'nin her biri var, `deger` boş değil, `ref` ve `tarih` dolu; k3 öğe listesi = OLCUM'daki beklenen liste + 'sembol'; k2'deki her `yuzey_ad` için bir `girdi.yuzey` ve bir `kanit` kaydı; k4 `degisebilir` anahtarları ayar anahtarı ve `alan_sinir`'da karşılığı var; k5 şema 1'de yalnız {tek_gorunum: true} ve S14 (ek) "sayılır" ise PASS, "sayılmaz" ise FAIL (şema 1 ile kilit çıkmaz) | 2.1; TK:393-395; TD:122-124 |
| H14 | ürün hattı bağı | S7'nin cevabına göre (4.5) | 4.5 |
| H15 | ürün durumu | DURUM.json'da geçerli kilit YOK ve `kilit_no` = klasördeki en büyük KILIT numarası + 1 ve DURUM `gecmis`'i 1..N-1 için eksiksiz; önceki mühürlü her kilidin `acma_sha256`'sı `gecmis`'te dolu. `hazirla` Drive'a erişmediği için açma kaydının kendisini `kilitle` denetler (bölüm 3) | bölüm 6 |

Ortam: araç pillow 11.0.0 + raqm'ı sert denetler (TD:224-229) ama numpy ve opencv sürümlerini denetlemez; OZET bunları
`paketler` altında yazar (TD:229, 999). Sürüm farkı PNG sha'sını değiştirirse H06 FAIL verir [ölçülmedi: fark verir mi].
`hazirla` çalıştığı ortamın sürümlerini OZET `paketler` ile karşılaştırır; farklıysa H06'dan önce DUR [öneri].

### 4.2 Kilit hangi koşuya dayanır

Serdar kararı [görev, 11 Kas]: yerleşim denemeleri yerelde deneme sembolüyle; renk, doku ve son teyit Actions'ta gerçek
katmanla; "Seçilen yerleşim kilitlenmeden önce Actions'ta gerçek katmanla bir kez ölçülür"; yerel kapı sonucu gerçek
katman için kanıt sayılmaz (aracın kendi notu da böyle: TD:106). Bu sözler gerçek katman ölçümünü ve son teyidi şart
koşar; kilit dosyasındaki `ornek.png_sha256`'nın hangi koşunun dosyası olacağını ayrıca söylemez [görev metninde yok]:
soru S2. Seçeneklerin her birinin bu sözlerle ilişkisi S2'de yazılıdır; şema üçünü de taşır (`katman.kayit`,
`yeniden.ortam`, `gercek_olcum`).

### 4.3 Gerçek katman: kayıt, tanıma, "yol yok"

"Yol yok" durumu [kod]: aracın Actions yolu yazılmadı (deneme planında dilim 8, DP:991); main'deki iş akışları arasında
araca ait dosya yok; araç kodu main'de değil (olgu 1). Gerçek katman Drive'dadır; ay takvimi iş akışı onu Drive'dan indirir
(W:124-136). Yerel oturumda gerçek katman yoktur. Sonuç: S2 (a) ya da (b) seçiliyken, aracın Actions yolu gelene kadar
HİÇBİR kilit mühürlenemez; H08 'gercek_yol_yok' verir. Bunu aşan bayrak plana konmadı.

Gerçek katmanın tanınması [öneri]: dosya adıyla değil sha256 ile. `data/tasarim_kilit/GERCEK_KATMAN.json`:
`{sema: 1, katman: {<CIFT>: [{sha256: sha, bayt: i, boyut: [i, i], kayit_tarihi: s, kaynak: s}]}}`. `kaynak` = sha'yı
basan Actions koşusunun numarası (katmanı Drive'daki sabit yerinden indiren iş akışı; emsal W:124-136; ay takvimi `sembol`
komutu katmanın sha256'sını ölçüm sözlüğüne koyar, AT:987, ve SEMBOL_OLCUM.json'a yazar, AT:1674). Kayda ekleme Merkez'in görev metniyle yapılır; Merkez sha'yı Drive'daki
dosyayla karşılaştırır. SINIR: bu dosya depodadır, push edebilen herkes değiştirebilir; bu yüzden katman sha'sı onay
kaydının bağlandığı `kilit_sha256`'nın içindedir (Merkez onay kaydını yazarken katman sha'sını da görür).

Gerçek katman ölçümünün kaydı, S2'ye göre:

- S2 (a): ayrı kayıt gerekmez. `hazirla` gerçek katmanla Actions'ta koşar; H06'nın kendisi ölçümdür. `yeniden.ortam`
  'actions', `yeniden.kosu` dolu, `katman.kayit` 'gercek'.
- S2 (b): `kanit[].gercek_olcum` zorunlu. Önerilen biçim: `{kosu: {run_id, run_attempt, sha}, katman_sha256, urun_sha256,
  ayar_sha256, kod_sha256, durum, png_sha256, olcum_ozet, fark: {...}}`. Kapı: `katman_sha256` GERCEK_KATMAN.json'da;
  `urun_sha256`, `ayar_sha256`, `kod_sha256` yerel kanıtla aynı; `durum` 'tamam'; `sert_fail` boş. `fark` = deneme planı
  7.4'ün ölçümleri (kutu, en boy, çevre yarıçapı, grup ölçeği, yerleşen alfa farkı; DP:915-918); yeterlilik eşiği o planda
  konmamıştır (DP:917-918) ve burada da konmaz. Kaydın gerçekten o koşudan çıktığını `hazirla` yerelde kanıtlayamaz
  (GitHub'a sorgu ağ ister; testte taklit edilir, CM:124): bu yüzden (b)'de de kaydı Actions içinde üreten ve ADAY'a
  yazan adım aynı iş akışı olmalıdır (soru T2).

Bilinen risk [görev; hesap]: yerelde ölçülen en büyük kapı 2 farkı 1,389 px, pay 2 px (TK:158; ATK:78); gerçek katmanda
2,04 - 2,17 px çıkabilir. Yani yerelde 'tamam' olan seçenek gerçek katmanda sert DUR alabilir; o durumda H03 / H06 FAIL
verir ve kilit olmaz. Kapı gevşetilmez (CM:214); Merkez tek satırla bildirir [görev].

### 4.4 Ölçer FAIL'ler ve karar 6

5751006'da sert kapılar: `2_sembol`, `2_grup` (TK:356-358) ve üretim sırasındaki DUR'lar (TK:15-16). Ölçer kapılar
(FAIL görseli durdurmaz), 15 ad [kod]: `oge_sayisi` (TK:395), `tek_doku` (396), `kontrast` (400), `yazim` (403),
`duz_renk` (405), `yildiz` (417), `grup_yazi` (428), `cakisma` (435), `tasma` (438), `tuval_tasma` (439), `cikti` (441),
`isim` (451), `metin_genis` (454), `metin_taban` (460, 463), `gercek_olcu` (529).

Karar 6 ile ilişki: karar 6 [görev] "işaretli her öğe için kabul / yerleşime dön"dür; araçtaki karşılığı `gercek_olcu`
ölçeri ve öğe başına `isaret` listesidir (olgu 9). `isaret` listesine üç tür satır düşer: yazı alt sınır altı (TK:498-501),
çizgi alt sınır altı; en ince, 1. yüzdelik ve ortanca AYRI (TK:477-483), taşma pikseli (TK:517-519). Hangi çizgi ve yazı
ölçütünün "sınır altı" sayılacağı seçilmedi (TK:24; DP:1052-1055): karar 6 listesinin hangi satırlardan oluşacağı buna
bağlıdır (soru S6). Diğer 14 ölçerin kilitteki hükmü soru S3.

Ürün hattı bağlantısı [görev]: taşma ve çakışma araçta ölçer, ornament ürün hattında serttir (DP:821-829; OS:9, 186
sert kapı sınıflaması). Taşma ya da çakışma FAIL'iyle kilitlenen seçenek o hattın kapısından geçemez.

### 4.5 Ürün hattının sert kapılarıyla bağ

Bağın kurulacağı yer [görev]: tasarım kilidi kapısı ve deneme planı 5.1 / soru 16 (DP:731-735, 1038-1041): "ürün hattı son
ürünü aracın ayarından ve aynı çizim yolundan mı üretecek" Serdar'a sorulmadı. Kilit kodu iki cevabı da taşıyacak biçimde
planlandı; hangisinin uygulanacağı soru S7. Şemadaki karşılığı: KARAR_GIRDI'de ürün başına `hat_sert: [kapı adı]` listesi
(S7 (a)) ve `dogrula`'nın `SON_ORNEK` şartı (5.3).

## 5. P5: Tüketen taraf

### 5.1 Arayüz: tek ortak modül [öneri]

Tek modül: `scripts/tasarim_kilit/tasarim_kilit.py`. Gerekçe: bugünkü emsallerin giriş noktaları birbirine benzemez (olgu
13); ortak nokta ancak içe alınan tek fonksiyon olabilir (emsal: karar kilidinde tek `yazim_kapisi`, UA:414-440).

```
K = tasarim_kilit.dogrula(urun, asama, onay_klasor, girdiler, son_ornek=None, kok=KOK)   geçemezse Dur (çıkış 4); atlama yok
    girdiler = {arac_klasor: yol / None, katman: {<CIFT>: yol}, ...}    tüketenin GERÇEKTEN kullanacağı dosyalar (D08)
K.ayar(yuzey_ad, kisisel=None)    kilitli ayar; `kisisel` yalnız `degisebilir` anahtarlarını taşıyabilir (başka anahtar = Dur)
K.ayar_denetle(yuzey_ad, ayar)    verilen ayarın kilitli kısmı kilitle aynı mı (D09); çıktı yazmadan hemen önce çağrılır
K.urun(yuzey_ad)                  ürün girdisi sözlüğü
K.arac_arsivi(hedef)              aracı `arac.commit`'ten `git archive` ile `hedef`e çıkarır ve kod sha'larını doğrular
K.stil_seti                       şema 2 (bölüm 7)
K.damga(asama)                    {urun, kilit_no, kilit_sha256, karar_sha256: {...}, asama}    her çıktı kaydına yazılır
tasarim_kilit.py dogrula --urun U --asama A --onay-klasor D --girdiler G.json [--son-ornek F]    iş akışı adımı; çıkış 0 / 4
```

`asama` kodları [öneri]: 'toplu', 'mockup', 'kart', 'video', 'siparis'; kilidin kapattığı işlerden türetildi [görev:
"Toplu üretim, mockup, video, kart, sipariş hattı üretimi"]. Kodların "kilit açılınca" tablosundaki iş adlarıyla eşlemesi
ASAMA_BAGLI.json `ad_esleme` parçasındadır ve teyit ister (6.3, T11).

### 5.2 `dogrula` kapıları ve sha zinciri

| No | Koşul | FAIL kodu |
|---|---|---|
| D01 | `data/tasarim_kilit/<URUN>/DURUM.json` var ve `gecerli` dolu | kilit_yok |
| D02 | `KILIT_<NNN>.json` şemaya uyar, `sema` destekli, `muhur.kilitli` true; `kilit_sha256` ve `karar_sha256` blokları yeniden hesaplanınca aynı; DURUM'daki sha ile aynı. ZİNCİR: `gecerli.kilit_no` klasördeki en büyük KILIT numarasıdır; `gecmis` 1..N için eksiksizdir ve her girişin sha'sı o dosyanın yeniden hesaplanan sha'sıdır; `onceki.kilit_sha256` bir önceki dosyanınkidir; N'den küçük mühürlü her kilit için `gecmis`'te `acma_sha256` doludur VE o açma kaydı `onay_klasor`'dedir, sha'sı aynıdır (mühürlenmemiş ADAY `gecmis`'te 'iptal' durur) | kilit_bozuk / zincir_bozuk |
| D03 | `onay_klasor`'de `ONAY_TASARIM_<URUN>_<NNN>.json` var; dosya sha256'sı = `muhur.onay_sha256`; `tur`, `urun`, `kilit_no`, `kilit_sha256`, `onay_sozu`, `tarih` kilide bağlanıyor (emsal UA:217-228); kayıt başka ürünün ya da başka kilit numarasının kaydı olamaz | onay_yok / onay_farkli |
| D04 | `onay_klasor` TAM kopyadır ve içinde bu kilit için açma kaydı YOK. Tamlık: klasörde ortak indirme adımının yazdığı `KLASOR_LISTE.json` vardır (Drive listesinden dosya adları ve sayısı); klasördeki dosyalar bu listeyle birebir aynıdır; liste yoksa ya da uyuşmuyorsa DUR (6.1) | klasor_eksik / kilit_acildi |
| D05 | her yüzey için depodaki `urun_dosya`'nın sha256'sı = `urun_sha256` | urun_degisti |
| D06 | `asama` ASAMA_BAGLI.json'un ad eşlemesinde ve URETIM_KOD.json'da tanımlı | asama_bilinmiyor |
| D07 | aşama için son örnek şartı varsa (5.3) `son_ornek` kaydı ve Drive'daki son örnek onay kaydı geçerli | son_ornek_yok |
| D08 | üretim girdileri kilitle aynı; sha'ları modül KENDİSİ hesaplar (çağıranın beyanı alınmaz). (i) `girdiler.arac_klasor` verildiyse içindeki `tasarim_*.py` kümesi ve sha256'ları = `arac.kod_sha256`, çalışan ortamın paket sürümleri = `arac.paketler`; verilmediyse KİLİTTEKİ `hat.arac_yolu[asama]` false olmalı (S7; bu değer `kilit_sha256` içindedir, Serdar onayına bağlıdır; depodaki başka hiçbir dosya bu şartı kaldıramaz). (ii) `girdiler.katman`: örnek çiftin dosyasının sha256'sı = `katman.sha256`; diğer çiftlerin her biri GERCEK_KATMAN.json'da kayıtlı VE son örnek şartı olan aşamada GERCEK_KATMAN.json'un sha256'sı = son örnek onay kaydındaki `gercek_katman_sha256` (5.3) | arac_farkli / katman_farkli |
| D09 | (`K.ayar_denetle`) tüketenin kullandığı ayarın, `degisebilir` anahtarları çıkarılmış halinin kanonik sha'sı = `ayar_kilitli_sha256`; `degisebilir` değerleri `alan_sinir` içinde | ayar_farkli |

Zincir: Serdar sözü (Drive, onay kaydı) -> `onay_sha256` (depo) -> `kilit_sha256` -> blok sha'ları -> `urun_sha256`,
`ayar_sha256`, `katman.sha256`, `arac.commit` + `kod_sha256`, `ornek.png_sha256`. Tüketenin okuduğu dosyalar: depodan
DURUM.json, bütün KILIT dosyaları (zincir), ASAMA_BAGLI.json, URETIM_KOD.json, GERCEK_KATMAN.json, ürün girdisi dosyaları;
yerel klasörden (ortak indirme adımı Drive'dan indirir) KLASOR_LISTE.json, onay, açma ve son örnek onay kayıtları; ayrıca
`girdiler`'de verilen araç klasörü ve katman dosyaları. OZET tüketimde GEREKMEZ.

Ayar: tüketen yerleşimi `K.ayar()`'dan alır. Kişiselleştirme (sipariş): müşterinin değerleri yalnız `degisebilir`
anahtarlarına `kisisel=` ile verilir; `K.ayar()` başka anahtarı kabul etmez. Tüketen ayarı başka yoldan kurduysa çıktıyı
yazmadan önce `K.ayar_denetle()` çağırır (D09). Modül, kendisini hiç çağırmayan ya da ayarı sonradan değiştiren betiği
durduramaz: bu en açık atlatma yoludur; karşılığı dilim K5'teki statik tarama testi (9. bölüm; emsal olarak anılan
test_ai_beyan [okunmadı]), iş akışında ayrı `dogrula` adımı ve çıktı kaydına yazılan damgadır (damgasız çıktı `denetle`'de
ayrı raporlanır, 6.3).

Araç koduna sabitleme: tüketen son ürünü aracın çizim yolundan üretecekse (S7) aracı `K.arac_arsivi()` ile `arac.commit`
kopyasından kurar (aracın kendi kaynak sabitleme kalıbı: TD:8-11, 45-47, 165-178) ve o klasörü `girdiler.arac_klasor`
olarak verir; D08 kod, paket ve katman eşitliğini kapıda sınar. Böylece aracın main'de ilerlemesi kilidi bozmaz, ama
ilerlemiş araçla ya da değişmiş katmanla üretim D08'de durur. Sabiti değiştirmek yeni kilittir (6.2).

SINIR (açık yazılır): D04 ve D08 çağıranın verdiği yerel klasörleri ve dosyaları sınar. Depoya yazabilen ve koşusunu
kendisi kuran biri eksik bir onay klasörü ya da başka bir dosya vererek kapıyı yanıltmayı deneyebilir. Karşılıklar:
indirme adımı tüketenlerin ORTAK tek adımıdır ve KLASOR_LISTE.json'u Drive listesinden yazar (liste çıktısını ayrıştıran
kapı beklenmeyen çıktıda DUR verir, CM:113-119); açılma iki ayrı yerde durur (depo `gecmis` + Drive kaydı; 6.1). Bunlar
yanlışlıkla atlamayı kapatır; kasıtlı atlatmayı yalnız görünür kılar (git geçmişi, damga).

### 5.3 CM:206'daki iki kuralın kapıdaki karşılığı

Kural 1: "tasarım kilidinden sonra üretilen görsel deneme sayılmaz" (CM:206).
- Tüketen tarafta: `dogrula`'dan geçen her koşunun çıktı kaydı `K.damga()` taşır; damgalı çıktı tanım gereği deneme
  değildir, bağımsız inceleme istisnası ona uygulanmaz.
- Araç tarafında: kilitli ürün adıyla aracın yeniden koşması bugün serbesttir ve çıktısı "deneme" görünür. Bunun kod
  karşılığı araç koduna dokunur; iki yol soru S12'de. Dokunmadan yapılabilen: `tasarim_kilit.py durum --urun U` komutu
  (kilit var mı; yalnız okur), Merkez'in görev metni yazarken bakması için.

Kural 2: "toplu üretimden önceki son örnek, ürün ayarıyla ve son üretim yolundan çıkar ve incelenir" (CM:206; ayrıca
CM:106-107 "Toplu uretimden once gercek oranda ornek + Serdar onayi"). Kapıdaki karşılığı İKİ ayrı kayıttır; üretim kodu
kendi incelemesini ve onayını yazamaz:

- SON_ORNEK kaydı (üretim kodu yazar; son üretim yolu odur): `{urun, kilit_no, kilit_sha256, asama, ornek: [{ad,
  sha256}]}`. İnceleme sonucu ve onay bu kayıtta YOKTUR.
- Son örnek onay kaydı (gizli Drive; Merkez yazar), ad `ONAY_SON_ORNEK_<URUN>_<NNN>_<ASAMA>.json`: `{tur: 'son_ornek',
  urun, kilit_no, kilit_sha256, asama, son_ornek_sha256, ornek: [{ad, sha256}], uretim_kod_sha256: {yol: sha},
  gercek_katman_sha256: sha, inceleme: {tarih, sonuc, inceleyen}, onay_sozu, tarih, yazan}`. `gercek_katman_sha256` =
  onay anındaki GERCEK_KATMAN.json dosyasının sha256'sı: toplu üretimin kullanacağı bütün çift katmanları onaydan önce
  kayıtlı olmalıdır; kayıt sonradan değişirse D08 (ii) DUR verir ve son örnek onayı yenilenir. Son örnek aranmayan
  aşamalarda (S16) diğer çiftlerin katmanı yalnız depodaki kayıtla sınanır (açık SINIR). `inceleme` bağımsız incelemenin sonucudur ve Merkez'in kaydıdır.
- D07 koşulları: SON_ORNEK'in `kilit_sha256`'sı geçerli kilitle aynı; Drive kaydının `tur` 'son_ornek', `son_ornek_sha256`
  = SON_ORNEK dosyasının sha256'sı, örnek sha listeleri aynı, `inceleme.sonuc` 'PASS', `onay_sozu` ve `tarih` dolu;
  `uretim_kod_sha256` = modülün, URETIM_KOD.json'da o aşama için sayılan dosyalardan o an KENDİ hesapladığı sha'lar (üretim
  kodu değiştiyse son örnek yenilenir). Tasarım kilidinin onay kaydı son örnek onayının yerine GEÇMEZ (`tur` ayrıdır).
- URETIM_KOD.json YALNIZ dosya listesidir (aşama -> üretim kodu dosyaları); parça 4 / 5 planından gelir ve depodadır;
  listeyi tüketen koşu veremez. "Araç yolu kullanılır mı" bilgisi bu dosyada DEĞİL, kilittedir (`hat.arac_yolu`).
- Hangi aşamalar son örnek ister: CM:206 ve CM:106-107 "toplu üretim" der; 'toplu', 'mockup', 'kart', 'video' aşamalarının
  toplu üretim sayılıp sayılmadığı ve sipariş hattındaki karşılığı ("sipariş hattı testi" [görev]) soru S16.

Mevcut ürün hatlarına (ornament, kupa, ay takvimi) uygulama bu planın kapsamı dışıdır [görev]: soru S10.

## 6. P6: Kilidi açma ve değiştirme

### 6.1 Açma

Kural [görev]: "Kilidi yalnız Serdar açık sözle açar." Karşılığı: gizli Drive'da `ACMA_TASARIM_<URUN>_<NNN>.json`
(`{tur: 'tasarim_acma', urun, kilit_no, kilit_sha256, acma_sozu, tarih, degisen_karar: [s], yazan}`); Merkez yazar.
Açılma İKİ yerde durur: Drive'daki bu kayıt ve depodaki DURUM.json. `tasarim_kilit.py ac --urun U --no N --onay-klasor <D>`
DURUM.json'u günceller (`gecerli: null`, geçmişe `durum: 'acildi'`, `acma_sha256`, `degisen_karar`). KILIT dosyası değişmez.

DURUM.json: `{sema: 1, urun: s, gecerli: null / {kilit_no, kilit_sha256}, gecmis: [{kilit_no, kilit_sha256, durum:
'aday' / 'gecerli' / 'acildi' / 'iptal', acma_sha256, acma_tarihi, degisen_karar}]}`. Durumu yazan komutlar: `hazirla`
'aday', `kilitle` 'gecerli', `ac` 'acildi', `tasarim_kilit.py iptal --urun U --no N` 'iptal' (yalnız mühürlenmemiş ADAY
için; mühürlü kilide uygulanamaz). H15: `gecmis`'te 'aday' ya da 'gecerli' giriş varken yeni `hazirla` DUR verir.
`gecmis` yalnız ekleme almalıdır; D02 bunu tek bir depo durumunun iç tutarlılığıyla sınar, geri alınmış bir commit'i
GÖREMEZ (aşağıdaki üçüncü madde; git geçmişi denetimi soru T13).

Ne zaman DUR verir, ne zaman vermez (açık yazılır):

- Açma kaydı Drive'da ve tüketenin onay klasörü tam kopyaysa: D04 DUR verir; depodaki DURUM henüz güncellenmemiş olsa bile.
- DURUM güncellenmişse (`ac` commit'i main'de): D01 DUR verir; klasör eksik olsa bile.
- İkisi birden atlatılırsa DUR VERMEZ: `ac` commit'i geri alınır (DURUM tutarlı eski haline döner) VE tüketen koşuya açma
  kaydını içermeyen bir klasör verilir. KLASOR_LISTE.json şartı (D04) eksik indirmeyi yanlışlıkla yapmayı kapatır, kasıtlı
  yapılanı kapatmaz (5.2 SINIR). Bu yol depoya yazma ve koşuyu kendisi kurma yetkisi ister; yalnız açılan kilit en son
  kilitken çalışır (D02: geçerli = en büyük numara); git geçmişinde görünür. Damga bunu GÖSTERMEZ: DURUM eski haline
  dönünce `denetle` o çıktıyı 'gecerli' sayar, DURUM düzeltilene kadar. T13 bu yolu daraltır.

### 6.2 Hangi değişiklik kilidi geçersiz kılar

| Değişen | Nerede yakalanır | Sonuç |
|---|---|---|
| kilit dosyasının herhangi bir alanı (ayar dahil) | D02 | DUR; düzeltme yeni kilit |
| ürün girdisi dosyası (depo) | D05 | DUR; yeni kilit. Not: yerleşim birimi güvenli yarıçaptır (TD:310-315); güvenli alan değişince aynı ayar başka piksel verir |
| onay kaydı (Drive) | D03 | DUR |
| açma kaydı konması | D04 | DUR |
| aracın kodu (main'de ilerlemesi) | kilidi geçersiz KILMAZ: kilit kodu commit'e sabitler. Tüketen aracın çizim yolunu kullanıyorsa D08 (i) verilen araç klasörünü kilitle karşılaştırır | ilerlemiş araçla üretim DUR (arac_farkli). Sabiti değiştirmek = yeni kilit: `hazirla` yeni commit'le H06'yı yeniden koşar. Aynı PNG sha'sı çıkarsa yeni Serdar sözü gerekip gerekmediği soru S13 |
| kaynak dosya sha256'ları, ay takvimi / motor / ornament sha'ları | aracın kodundaki sabitlerdir (TD:45-73), yani `arac.commit` ile belirlenir (D08 (i) kod sha'sını sınar); araç ayrıca her koşuda kaynakları sert denetler (TD:165-178) | DUR |
| paket sürümleri | D08 (i): çalışan ortam = `arac.paketler` (aracın kendisi yalnız pillow + raqm'ı denetler, TD:224-229) | DUR |
| sembol katmanı dosyası (Drive) | D08 (ii): örnek çiftin dosyası = `katman.sha256`; diğer çiftler GERCEK_KATMAN.json kaydıyla | DUR (katman_farkli) |
| GERCEK_KATMAN.json | kilit kendi katman sha'sını taşır; kayıt değişimi mevcut kilidi etkilemez, yeni `hazirla`'yı etkiler | |
| ASAMA_BAGLI.json | D06 ve `denetle` | tablo Serdar'ındır; değişimi ayrı onay |

### 6.3 "Yalnız o karara bağlı aşamalar geçersiz olur"

- Kilit, karar başına blok sha'sı taşır (`karar_sha256`). Her üretim çıktısının kaydında `K.damga()` durur.
- `tasarim_kilit.py denetle --urun U --kayit <çıktı kaydı>...`: çıktının damgasındaki blok sha'larını GEÇERLİ kilidinkilerle
  karşılaştırır. ASAMA_BAGLI.json o aşamanın hangi bloklara bağlı olduğunu söyler; bağlı bloklardan biri farklıysa çıktı
  'gecersiz' (hangi karar yüzünden olduğu yazılır), hiçbiri farklı değilse 'gecerli'. Geçerli kilit yoksa bütün çıktılar
  'kilit_acik' işaretlenir.
- Geçersiz kilitle üretilmiş çıktı böyle tanınır: damgasındaki `kilit_sha256` geçerli kilidinki değildir ve bağlı
  bloklarından biri değişmiştir. Damgasız çıktı 'damgasiz' olarak ayrı raporlanır (kilit öncesi ya da kapıyı çağırmayan
  kod). Çıktılar Drive'dadır; `denetle` yerel yoldaki kayıtları okur, Drive'a kendisi gitmez.
- ASAMA_BAGLI.json iki parçadır. (1) `tablo`: Serdar'ın "kilit açılınca" tablosunun satırları, KENDİ yönünde ve kendi
  sözleriyle: `[{degisen_karar: [i], acilan_kilit: [s], gecersiz: [s]}]`. Bu oturum yalnız ilk satırı gördü [görev]: "1-5
  (stil seti dahil) | İkisi de | Toplu üretim çıktıları, sipariş hattı testi, 8-10, 11; 14-16 metinleri yeniden kontrol".
  Diğer satırlar [okunmadı]; 6 ve 7 için satır yok [görev]: soru S9; `girdi` bloğu için satır var mı [okunmadı]: soru S15.
  (2) `ad_esleme`: tablodaki iş adlarının aşama kodlarına eşlemesi (ör. "Toplu üretim çıktıları" -> 'toplu', "sipariş hattı
  testi" -> 'siparis', 8 / 9 / 10 -> 'mockup' / 'kart' / 'video'). Bu eşleme tabloda yazılı DEĞİLDİR, bu planın yorumudur:
  Merkez / Serdar teyidi olmadan kullanılmaz (soru T11). "Aşama -> bağlı blok" ilişkisi bu iki parçadan kodla türetilir;
  ayrı bir tablo olarak elle yazılmaz.
- Tablonun kapsamadığı her durumda (6 / 7 değişimi, `girdi` değişimi, eşlemesi teyit edilmemiş iş adı) `denetle`
  "tanımsız: Serdar'a sor" döner; kendiliğinden hüküm vermez. Bu, soruların cevabı gelene kadarki kapalı davranıştır,
  seçeneklerden biri değildir.

### 6.4 İki kilit arasındaki bağ

[görev] ilk satır: 1-5 değişirse "İkisi de" açılır. Karar kilidinin bunu kodla görebilmesi için tasarım kilidinin sha'sını
taşıması gerekir [öneri]: URUN_AYAR.json'a üst düzey `tasarim_kilit: {urun, kilit_no, kilit_sha256}` alanı. Bu alan `kilit`
bloğunun DIŞINDA olmalı ki `ayar_sha` içine girsin (UA:148-151) ve Serdar'ın karar onayı onu da kapsasın. Değişecek
yerler: SEMA (UA:29-36; bilinmeyen anahtar bugün reddedilir, UA:6) ve `_kilit` (UA:210-229; ek koşul: `tasarim_kilit.dogrula`
geçer ve sha aynı). Sonuç: tasarım kilidi açılır ya da yenilenirse karar kilidi kapısı Etsy yazımını durdurur (yazım
kapısının ilk denetimi `_kilit`'tir, UA:418). Bu, Etsy'ye yazan kodun kapısını değiştirir: ayrı dilim (K6), ayrı Serdar
onayı ve yazımdan önce bağımsız inceleme (CM:208). `urun_ayar.py` bugün main'de değildir (olgu 1). Soru T5.

### 6.5 Görev metni satırından kod kapısına geçiş

Bugün [görev]: kilit belge satırıdır; kapsamdaki ürünlerde üretim, sipariş ve Etsy görev metinlerine kilit satırı birebir
yazılır; satır yoksa görev metni hazırlanmaz. Aşamalar [öneri]:

| Aşama | Koşul | Görev metni | Kod |
|---|---|---|---|
| G0 (bugün) | kilit kodu yok | kilit satırı birebir | yok |
| G1 | dilim K1 main'de; ürün için mühürlü kilit var | satır + `kilit_no` + `kilit_sha256` | yeni üretim kodu `dogrula` çağırır; satırla sha'nın aynı olduğunu oturum raporda yazar |
| G2 | parça 4 / 5 tüketenleri bağlı (K5), tarama testi yeşil | S11'in cevabına göre | kapı tek yetkili |

G1'e ve G2'ye geçiş anı Serdar kararıdır (S11). Geçişte hiçbir an "ne satır ne kapı" olmamalı: satır, kapı bağlanmadan
kaldırılmaz.

## 7. P7: Parça 2 (renk ve doku, stil seti) ve kütüphane gelince; sıra sorusunun açık cevabı

### 7.1 Şema nasıl genişler

Bugünkü durum [kod]: tek görünüm (motor zemini, tek palet; DP:413-414); ürün girdisinde `zemin` yalnız 'motor' (TD:290-291);
ayar sözlüğünde renk / doku anahtarı yok (TD:122-124); planlanan arayüz koşu girdisinde `gorunum` listesi, her öğe
{zemin, renk, doku} ad + sha256 (DP:416-419). Kütüphane kaydının planlanan alanları: ad, sekil, ayar, sha'lar, paketler,
ürün adı ve sha'sı, katman sha'sı, logo sha'sı, altın sırası, örnek PNG sha'sı, onay (DP:357-364).

Şema 2'de eklenenler [öneri; parça 2'nin gerçek dosya biçimi belli olunca kesinleşir]:

- `karar.k5.deger`: `{stil_seti: [{ad: s, zemin: {ad, sha256}, renk: {ad, sha256}, doku: {ad, sha256}}]}`.
- `kanit[]` anahtarı (yuzey_ad) yerine (yuzey_ad, stil_ad): her stil için ayrı `ornek` ve `yeniden` (stil başına onaylı
  örnek sha'sı). H06 stil başına koşar.
- `kanit[].kutuphane`: null / {ad: s, sha256: sha} (yerleşim bir kütüphane kaydından geldiyse; `taban` kütüphane kaydının
  adı olabilecek, DP:291).
- `K.stil_seti` dolar; ASAMA_BAGLI'da k5'e bağlı aşamalar zaten ilk satırda sayılıdır [görev].
- `sema` 2 olur; sürüm 1 kilitleri sürüm 2 koduyla okunur ama `k5` tanımsız olduğu için 'toplu' aşamasında geçip
  geçmeyeceği S1 / S14'e bağlıdır.

### 7.2 Açık cevap: kod parça 1 ve 2 bitmeden yazılırsa ne yeniden yazılır, ne kalır

Kilit kodunun beş parçası ve neye bağlı oldukları:

| Parça | İçerik | Bağlı olduğu şey |
|---|---|---|
| A çekirdek | kanonik sha, şema doğrulama, DURUM, onay / açma kaydı denetimi, `kilitle`, `dogrula`, `ac`, `denetle`, damga, bunların testleri | yalnız bu plan ve S8, S9 |
| B uyarlayıcı | OZET / OLCUM okuma, H01-H06, H09-H13, `uret` çağrısı, testleri | aracın çıktı biçimi ve komutu (TD:965-1048; TK:532-544) |
| C gerçek katman | GERCEK_KATMAN kaydı, H07-H08, iş akışı | aracın Actions yolu (yok) ve S2 |
| D karar 5 | stil seti alanları, stil başına örnek | parça 2 (yok) |
| E kütüphane bağı | `kutuphane` alanı, ortak sha / onay kodu | kütüphane (yok) |

Her sıranın sonucu, aynı başlıklarla (öneri yok; karar Serdar'da, soru S1). Onaylı yapım sırası [görev]: parça 3'ün ön
koşulu parça 1 ve 2'dir.

| | (1) ŞİMDİ | (2) PARÇA 1'DEN SONRA (araç dilimleri + Actions yolu) | (3) PARÇA 2'DEN SONRA |
|---|---|---|---|
| Bir kez yazılıp kalan | A | A, B, C | A, B, C, D, E |
| Yeniden yazılan | B'nin araca bağlı tabloları ve testleri (bölüm 8'deki her değişiklik B'de bir değişikliktir; bu görev sırasında bile araç 'dilim 1b'ye geçti, Ek 2); C (bugün yalnız "yol yok: DUR" yazılabilir, kayıt biçimi tahmindir) | yok | yok |
| Sonradan eklenen | D, E (biçim yok; şema 2) | D, E (şema 2: A'da `sema` dalı, B'de stil başına H06) | yok |
| İlk mühürlü kilit | çıkmaz: H08 her kilitte FAIL (S2 (a) / (b) altında) ve karar 5 için biçim yok | Actions yolu varsa çıkabilir; karar 5 için S14 (ek) cevabı gerekir (H13) | çıkabilir |
| Test kanıtı | B ve C yalnız sahte veri ve yerel deneme sembolüyle sınanır ("zayıf test", CM:212) | gerçek katmanla sınanabilir | gerçek katman ve stil setiyle sınanabilir |
| Parça 4 / 5 ve geçiş dönemi | parça 4 / 5 planları `dogrula` arayüzüne göre yazılabilir; kod kapısı yine ilk mühürlü kilide kadar boştur | parça 4 / 5 parça 1 kadar bekler | parça 4 / 5 parça 1 ve 2 kadar bekler; kilit o süre belge satırı kalır (G0) |
| Mühürlü kilidin şema değişiminden etkilenmesi | ortada mühürlü kilit olmaz | şema 1 ile mühürlenen ürün, şema 2 gelince ya şema 1'de kalır ya yeniden kilitlenir (Serdar sözü gerekir) | yok |
| Onaylı yapım sırasıyla ilişki | sıradan sapar (ön koşul 1 ve 2 bitmeden) | sıradan sapar (ön koşul 2 bitmeden) | sıraya uyar |

Üç sırada da değişmeyen: A'nın tasarımı; onay ve açma kayıtlarının biçimi; `dogrula` arayüzü.

## 8. P8: Aracın hâlâ değişen yerleri ve şemanın sürümlenmesi

| Değişen [görev] | 5751006'daki durum [kod] | Kilide etkisi |
|---|---|---|
| çıktı kapısı sert olacak | ölçer (TK:18, 440-444) | `cikti` adı `olcer_fail`'den `sert_fail`'e geçer; uyarlayıcı tablosu değişir. H03 zaten sert FAIL'i engeller |
| tuvalden taşan grup öğesi seçeneği durduracak; isim satırı taşması ölçülecek | kısmi taşma ölçer: `kontrol['tasma']` (TD:725-731), `tuval_tasma` (TK:439) | bir ölçer adı kalkar ya da bölünür; uyarlayıcı tablosu |
| ürün girdisi: 23,0 mm, güvenli r 515, etiketler | 25,4 mm; r 543,5; 'varsayım' (UG:5-7, 10) | `urun_sha256` değişir: eski OZET'ler H02'de düşer. Eski OZET `uret` ile yine yeniden üretilebilir, çünkü `uret` ürünü OZET'ten okur (olgu 3): H02 bu yüzden zorunlu |
| yeni ayar anahtarı (sembol boyu) | 23 anahtar (TD:122-124) | yeni kodda eski ayar yeniden doğrulanınca aynı çıkmaz (TD:1034-1036): kilidin `arac.commit`'e sabitlenmesi bunu çözer; yeni commit'e geçiş = yeni kilit |
| Actions yolu | yok | C parçası; `sembol_katmani.tur` değişebilir (olgu 5); kilit bu alanı zaten kullanmaz |
| çok sayfalı pafta, tipik / en kötü setler (deneme planı dilim 2, DP:985) | tek set, tek sayfa | OZET yapısı değişebilir; `hazirla` argümanlarına set adı eklenir; S14 |

Sürümleme [öneri]: iki ayrı sürüm. (1) Kilit şeması: `sema` tam sayısı; `dogrula` tanımadığı sürümde DUR. (2) Araç biçimi:
`ozet_oku.py` içinde `arac` dizesi (TD:994) -> {koşu anahtar kümesi, seçenek anahtar kümesi, sert adlar, ölçer adlar}
tablosu. Tanınmayan `arac` dizesi, fazla / eksik anahtar ya da tabloda olmayan kapı adı = DUR (kapalı kalır): araca
eklenen yeni bir kapı, uyarlayıcı güncellenmeden sessizce yok sayılamaz. `arac` dizesi kod değiştiği halde aynı kalabilir
(bugün 'tasarim_deneme dilim 1'); bu yüzden anahtar kümesi denetimi de yapılır ve asıl bağ `kod_sha256` + `arac.commit`'tir
(H05). OZET'e sayısal şema sürümü eklenmesi soru T4.

Mühürlü kilit araç biçimi değişiminden ETKİLENMEZ: tüketimde OZET okunmaz (5.2), kilit kendi alanlarını taşır.

Ek 2, dal bu görev sırasında ilerledi: tasarim-deneme-dilim1 yeni ucu f6167573fe409fac42cbe7e2cbb90355d3a35c05 ("dilim 1b";
üç dosya değişti: tasarim_deneme.py, tasarim_kapi.py, test dosyası). Plan 5751006'ya göre yazıldı; aşağıdakiler yeni uçtan
okundu [kod; satırlar f616757'ye göre] ve yukarıdaki tablonun ilk satırlarını doğrular:

| Değişen (f616757) | Kilide etkisi |
|---|---|
| `arac` dizesi 'tasarim_deneme dilim 1b' (TD:1033) | uyarlayıcıda yeni sürüm satırı (H01) |
| `cikti` ölçerden serte geçti (TK:470-473); sert adlar 3, ölçer adlar 14 | uyarlayıcı tablosu; 4.4'teki sayı 15 -> 14, S3'teki 14 -> 13 |
| `olcum_ozet`'e yeni anahtarlar: `cift_px`, `kucuk_yazi_px`, `kok_neden`, `isim_guvenli_disinda`, `yildiz_sayi`; `cakisma.ornament_ciftler` (TK:582-594); OLCUM'a `bilgi` bloğu (TK:596) | `kanit[].ornek.olcum_ozet` birebir alındığı için kilit şeması değişmez; H01 anahtar kümesi değişir |
| isim satırı güvenli alan dışındaysa DUR yok, `isim` ölçeri FAIL (TK:488 ve devamı) | S3 kapsamına yeni bir ölçer FAIL nedeni |
| ikinci ızgara türü 'kucuk' (TD:140-141, 480): seçenek `tur` ve `ad` yeni değer alır | kimlik zaten ad / tur'a dayanmıyor (1.3) |
| pafta 3 MB'ı aşarsa OZET yine yazılır, `pafta` bir DUR sözlüğü olur (TD:1046) | kilit `pafta`'yı almıyor; H01 bu alanın iki biçimini tanımalı |
| `kod_sha()` ayrı fonksiyon, aynı desen (TD:522-524); `uret` mantığı aynı, satırları 1071-1094 (karşılaştırma TD:1090) | olgu 4 ve 10 yeni uçta da geçerli |

## 9. P9: Testler

Kural: her kapı bilinen PASS + bilinen FAIL; test gerçek fonksiyonu çalıştırır; mutasyon (kod bozulunca test FAIL); test
tek başına koşar, çıkış kodu ayrı okunur; test dış ağa çıkmaz, `git` dışındaki dış araçlar sahteyle değiştirilir (CM:124,
195, 212, 220). "Sahte veri" testleri yalnız kapı mantığını sınar ve raporda öyle yazılır (emsal TT:13).

Sahte veriyle (kendi kurduğu OZET / kilit / kayıt; hızlı):

| Kapı | Bilinen PASS | Bilinen FAIL | Mutasyon |
|---|---|---|---|
| kanonik sha | aynı sözlük farklı anahtar sırasıyla aynı sha | tek değer değişince farklı sha; 1 ile 1,0 farklı | `sort_keys` kaldırılınca test FAIL |
| şema | tam kilit | her zorunlu alan tek tek eksik; bilinmeyen anahtar; yanlış tür; desen dışı ürün adı | bir alan denetimi silinince FAIL |
| blok kapsamı (1.4) | şemadaki her alan tam bir blokta | bir alanı değişen kilitte yalnız o alanın bloğu değişir (her blok için tek tek) | bir alan blok tablosundan çıkarılınca "her alan tam bir blokta" testi FAIL |
| H01 | tanınan `arac`, tam anahtar kümesi | tanınmayan `arac`; fazla anahtar; eksik anahtar; tabloda olmayan ölçer adı; yinelenen anahtar; NaN | anahtar kümesi eşitliği "alt küme"ye çevrilince fazla anahtarlı OZET geçer: test FAIL |
| H03 | `durum` tamam | `durum` DUR; `sert_fail` dolu; `png_sha256` null; aynı `no` iki kez | `durum` denetimi silinince DUR'lu seçenek geçer: test FAIL |
| H04 | aynı ayar, aynı sha | aynı ayar, farklı `png_sha256` | karşılaştırma silinince test FAIL |
| H09 | S3 cevabına göre kabul kayıtlı | kabulsüz ölçer FAIL; başka kapının kabulüyle geçme denemesi | kabul eşlemesi kapı adından bağımsız yapılınca test FAIL |
| H10 | tam kabul listesi, liste sha'sı aynı | eksik kayıt; fazla kayıt; 'yerleşime dön'; işaret metni farklı; `isaret_liste_sha256` farklı | sha karşılaştırması silinince test FAIL |
| H11, H12 | S4 / S5 cevabına göre etiketler | 'varsayım' alan; `alt_sinir` yok; `kaynak.gercek_mm.tur` OZET ile çelişiyor; geri dönüş etiketli seçenek | etiket denetimi silinince test FAIL |
| H13 | tam kararlar | boş `deger`; öğe listesi farklı; `degisebilir`'de ayar anahtarı olmayan ad; `alan_sinir` karşılığı yok; k5 başka değer | her alt koşul tek tek silinince ilgili test FAIL |
| H15, iptal | ilk kilit; açılmış kilitten sonra ikinci; iptal edilmiş ADAY'dan sonra yeni `hazirla` | geçerli kilit varken `hazirla`; 'aday' dururken ikinci `hazirla`; `gecmis` eksik; numara atlanmış; önceki mühürlü kilidin `acma_sha256`'sı boş; mühürlü kilide `iptal` | koşul silinince test FAIL |
| kabul bağı | onay kaydındaki kabul adları = kilitteki | kilitte olup kayıtta olmayan kabul; `hat.arac_yolu` false yapılmış ama `kilit_sha256` eski (D02 FAIL) | kabul eşitliği silinince test FAIL |
| T13 (seçilirse) | geçmişi temiz DURUM | `ac` commit'i geri alınmış depo: DUR | geçmiş okuması kapatılınca test FAIL |
| kilitle | bağlanan onay kaydı | kayıt yok; sha farklı; başka ürünün kaydı; başka `kilit_no`'nun kaydı (yeniden kullanım); boş söz; örnek sha'sı farklı; ADAY hazırlıktan sonra değişmiş; önceki mühürlü kilidin açma kaydı klasörde yok | onay ve zincir denetimleri tek tek silinince test FAIL |
| D01-D03, D05, D06 | mühürlü kilit + kayıt | tek tek: DURUM yok; `kilitli` false; elle `kilitli: true` (sha uyuşmaz); DURUM daha küçük numaralı kilidi gösteriyor; `onceki` sha'sı yanlış; onay yok; başka kilidin onay kaydı; ürün girdisi 1 bayt değişmiş; bilinmeyen aşama | her koşul tek tek silinince ilgili test FAIL |
| D04 | tam klasör, açma kaydı yok | açma kaydı var; KLASOR_LISTE.json yok; listede olup klasörde olmayan dosya ("Drive'da var, yerelde yok"); listede olmayan fazla dosya | liste eşitliği silinince eksik klasör geçer: test FAIL |
| D07 | geçerli SON_ORNEK + Drive son örnek onayı | son örnek yok; başka kilide ait; Drive kaydı yok; `tur` 'tasarim_kilit' (tasarım onayıyla geçme denemesi); `inceleme.sonuc` PASS değil; üretim kodu 1 bayt değişmiş; örnek sha'sı farklı | `tur` denetimi ve kod sha hesabı tek tek silinince test FAIL |
| D08 | kilitle aynı araç klasörü, katman, paketler | araç klasöründe 1 bayt değişmiş dosya; fazladan `tasarim_x.py`; başka katman dosyası; kayıtsız çift katmanı; farklı paket sürümü; araç klasörü verilmemiş ama aşama araç yolunu kullanıyor | sha'yı çağıranın beyanından alan bozuk kopya: test FAIL |
| D09, K.ayar | yalnız `degisebilir` anahtarları değişmiş ayar | kilitli bir anahtarı değişmiş ayar; `kisisel` içinde kilitli anahtar; `alan_sinir`'ı aşan değer | çıkarma listesi boşaltılınca / genişletilince test FAIL |
| ac, denetle | açılan kilit; bağlı bloğu değişmemiş çıktı 'gecerli' | bağlı bloğu değişmiş çıktı 'gecersiz' + karar adı; damgasız çıktı; karar 6 / 7 ve `girdi` değişimi 'tanımsız'; açılmış kilidin `ac` commit'i geri alınmış + tam klasör: D04 DUR | 'tanımsız' dalı 'gecerli'ye çevrilince test FAIL |
| atlama yok | | ortam değişkeni / bayrak ile geçme denemesi: yine DUR | modüle atlama dalı eklenmiş kopya: test FAIL |

Gerçek dosyayla (aracın sabitlenmiş kopyası, motor kaynakları, yerel deneme sembolü; yavaş; emsal TT `t_motor`, TT:601-605,
662-664):

| Kapı | Bilinen PASS | Bilinen FAIL |
|---|---|---|
| H02 | aracın gerçek koşusunun OZET'i + depodaki ürün girdisi | ürün girdisi dosyası değiştirilmiş; OZET içindeki `urun` değiştirilmiş (OZET kendi içinde tutarlı kalsa da H02 FAIL) |
| H05 | doğru commit | başka commit; klasöre fazladan `tasarim_x.py` konmuş kopya |
| H06 | temiz seçenek: aynı sha | bir ayarı değiştirilmiş OZET (sha farklı); sert DUR almış seçenek (`uret` çıkış 0 verir ama H06 FAIL: olgu 4'ün kanıtı); katmanı değişmiş koşu |
| H07 | yalnız kapı mantığı: testin KENDİ kurduğu kayıt dosyasına yazılmış sha 'gercek' sayılır (sahte kayıt; gerçek katman kanıtı DEĞİL) | adı değiştirilmiş deneme sembolü (OZET `tur` 'gercek' der, H07 'deneme' der); kayıtsız sha, S2 (a) altında FAIL |
| H10 | işaretli öğeleri olan seçenek + tam kabul listesi | bir kabul eksik |
| uçtan uca | hazirla -> kilitle -> dogrula -> ac -> dogrula (DUR) | |

Gerçek katmanla (yalnız Actions; C parçası): H07 / H08'in GERÇEK katmanla bilinen PASS'ı yerelde kurulamaz; yerelde
yalnız kapı mantığı (yukarıdaki sahte kayıt), bilinen FAIL ve "yol yok" sınanır. Bu, raporda "gerçek PASS kanıtı yok" diye yazılır. İş akışı kabuk adımları yerelde
sahte araçla ve iş akışının kabuğuyla sınanır (CM:113).

Tarama testi (dilim K5): yeni genel üretim klasörlerindeki her giriş betiği `tasarim_kilit.dogrula`'yı ilk dosya
yazımından önce çağırıyor mu; bilinen FAIL: çağrısı silinmiş kopya.

## 10. P10: Dilimler

Süreler [tahmin]; her dilim en çok 2 deneme, sonra DUR (CM:127). Hiçbir dilim Serdar'ın kilit kodu kararı
(S1) ve bağlı soruların cevabı olmadan başlamaz. Her dilimde bağımsız inceleme (CM:208-221).

| Dilim | Kapsam | Dosyalar | Ön koşul | Süre [tahmin] |
|---|---|---|---|---|
| K1 | Çekirdek (parça A): şema 1, kanonik sha, blok kapsamı, DURUM ve zincir, onay / açma kaydı denetimi, `kilitle`, `dogrula` (D01-D06, D09), `ac`, `denetle`, `durum`, damga; sahte veri testleri | tasarim_kilit.py, test_tasarim_kilit.py, ASAMA_BAGLI.json | S8. ASAMA_BAGLI'nın `tablo` parçası görev metnindeki ilk satırla başlar; kalan satırlar, S9, S15 ve ad eşlemesi teyidi (T11) gelene kadar `denetle` o durumlarda 'tanımsız' döner. K5'ten önce tablo ve eşleme tam olmalı | 5 - 7 saat |
| K2 | Uyarlayıcı ve `hazirla` (parça B): H01-H06, H09-H13, H15; gerçek dosyayla testler | ozet_oku.py, test dosyası, örnek KARAR_GIRDI | K1; aracın biçimi kararlı (S1); araç main'de (T3); S3, S4, S5, S6, S14 | 5 - 7 saat |
| K3 | Gerçek katman (parça C): GERCEK_KATMAN.json, H07, H08, iş akışı, kabuk testleri | GERCEK_KATMAN.json, tasarim-kilit.yml, test | K2; aracın Actions yolu (DP:991); S2; T2, T6 | 3 - 4 saat + 1 koşu |
| K4 | Şema 2 (parça D, E): karar 5, stil başına örnek, kütüphane bağı | tasarim_kilit.py, ozet_oku.py, test | parça 2 ve kütüphane | 3 - 5 saat |
| K5 | Tüketen bağlama: parça 4 / 5 kodunda `dogrula` (D07, D08 dahil), damga, SON_ORNEK, URETIM_KOD.json, ortak indirme adımı (KLASOR_LISTE.json), tarama testi, H14 | parça 4 / 5 dosyaları + test | K1; parça 4 / 5 planı; S7, S16; T6 | tüketen başına 1 - 2 saat + ortak adım 2 - 3 saat |
| K6 | Karar kilidi bağı (6.4) | urun_ayar.py ve testi | K1; `urun_ayar.py` main'de; ayrı Serdar onayı; T5 | 2 - 3 saat + inceleme |

Sıra: K1 tek başına yazılabilir. K2 ve K3 araca bağlıdır. K4 parça 2'ye bağlıdır. İlk mühürlü kilit en erken K3'ten sonra
çıkar (S2 (a) / (b) altında).

## 11. P11: Açık sorular

### 11.1 Serdar kararı gerekenler (seçenek ve sonuç; öneri yok)

S1. Kilit kodu ne zaman yazılsın? (a) şimdi; (b) parça 1 bitince; (c) parça 2 de bitince. Sonuçlar bölüm 7.2'de.

S2. Kilit dosyasındaki onaylı örnek hangi koşunun görseli olsun? Verilmiş kararlar [görev, 11 Kas]: "renk, doku ve son
teyit Actions'ta gerçek katmanla"; "Seçilen yerleşim kilitlenmeden önce Actions'ta gerçek katmanla bir kez ölçülür".
(a) Gerçek katman koşusunun görseli: `hazirla` Actions'ta koşar; aracın Actions yolu gelene kadar kilit çıkmaz; iki
verilmiş kararla da uyumludur. (b) Yerel deneme koşusunun görseli + ayrı gerçek katman ölçüm kaydı: ölçüm kararıyla
uyumludur; kilitteki örnek deneme sembolünün görseli olur (gerçek katman için kanıt değildir, TD:106), yani "son teyit
gerçek katmanla" sözündeki teyit görseli ile kilitteki örnek AYRI dosyalar olur; iki kayıt tutulur; yine Actions yolu
gerekir. (c) Yalnız yerel koşu: bugün yapılabilir; iki verilmiş kararı da DEĞİŞTİRİR (yeni karar gerektirir; seçenek
olarak yalnız bu sonuç görünsün diye yazıldı).

S3. Ölçer FAIL'i olan seçenek kilitlenebilir mi? (a) Her ölçer FAIL kilidi engeller; yalnız o kapı için kayıtlı Serdar
kabulüyle geçer (14 ölçerin her biri ayrı). (b) Taşma, çakışma ve ürün hattında sert olan kapılar hiç geçemez; diğerleri
kayıtlı kabulle geçer. (c) Yalnız gerçek ölçü uyarısı (karar 6) kabul ister; diğer ölçer FAIL'ler kilide yazılır ama
engellemez: bu durumda taşmalı / çakışmalı seçenek kilitlenebilir ve ürün hattının sert kapısında durur. (d) Ek: "geri
dönüş" etiketli seçenek (istenen düzen yerine başka düzen çizilmiş, olgu 11) kilitlenebilir mi: evet / yalnız kabulle / hayır.

S4. 'varsayım' etiketli ürün girdisiyle kilit olur mu? (a) Hiçbir alan 'varsayım' iken kilit yok. (b) Alan alan, kayıtlı
Serdar kabulüyle olur. (c) mm eşlemesi (baskı px, gerçek mm) ve güvenli alan 'resmi' / 'ölçüm' / 'serdar' olmalı; alt
sınır 'varsayım' olabilir. Sonuç: (b) ve (c)'de kilitteki mm uyarıları doğrulanmamış girdiye dayanabilir.

S5. Üretici alt sınırı bilinmiyorsa (renkli baskı [görev])? (a) Kilit yok; önce sınır bulunur. (b) "Sınır bilinmiyor"
kayıtlı kabulüyle kilit; karar 6 listesi boş kalır (gerçek ölçü denetimi yapılmamış olur, olgu 7). (c) Kazıma sınırı
renkli baskıya 'varsayım' etiketiyle uygulanır; S4'e bağlanır.

S6. Karar 6 listesi hangi işaretlerden oluşsun (deneme planının açık sorusu 4, DP:1052-1055)? Yazı: büyük harf / küçük
harf yüksekliği. Çizgi: en ince / 1. yüzdelik / ortanca. Taşma işareti karar 6'ya mı, S3'e mi girer. Sonuç: ölçüt
seçilmeden H10'un listesi tanımsızdır.

S7. Ürün hattıyla bağ (deneme planı soru 16 dahil). Birinci soru: ürün hattı son ürünü aracın ayarından ve aynı çizim
yolundan mı üretecek? (i) Evet: kilitteki örnek son üretim yoluyla yeniden üretilebilir, kapı bunu sha ile sınar.
(ii) Hayır: kilit ayarı ve ölçüleri taşır; kilitteki örnek son ürünün kanıtı olmaz; kanıt yalnız "son örnek"tir (5.3).
İkinci soru: sert kapılar ne zaman uygulanır? (a) Kilit anında: ürün başına sert sayılacak kapı listesi verilir, biri
FAIL ise kilit yok. (b) Kilit bakmaz; ürün hattı kendi kapısını uygular; FAIL çıkarsa Merkez bildirir, kilit açılır.
(c) Mühürden önce ürün hattından tek ön örnek geçmelidir: ADAY kilitle tek örnek üretimine izin gerekir.

S8. Onay sözü ve karar değerleri nerede dursun? Söz: (a) kütüphane ve kart kilidi emsalindeki gibi gizli Drive'da, depoda
yalnız sha: kilit dosyasında söz yok. (b) Depoda da: `muhur` bloğuna söz ve tarih eklenir, söz herkese açık depoda görünür.
Kararlar 1, 2, 7'nin değerleri ve karar 6 kabul listesi: (a) açık depoda: kilit tek başına okunur, üretim kodu değerleri
kullanabilir. (b) Depoda yalnız sha, değerler Drive kaydında: her tüketen koşu kaydı indirir; kod değerleri yalnız eşitlik
için görür; 1.2'deki `karar.k1`, `k2`, `k7` ve `k6` `deger` alanları sha'ya iner.

S9. "Kilit açılınca" tablosunda 6 ve 7 için satır yok. Karar 6 ya da 7 değişirse? (a) 1-5 satırıyla aynı sonuç. (b) Yalnız
tasarım kilidi yenilenir; üretim çıktıları geçerli kalır. (c) Her seferinde Serdar ayrıca söyler; tabloya satır yazılmaz.

S10. Mevcut ürün hatlarına (ornament, kupa, ay takvimi) uygulansın mı [görev: ayrı Serdar kararı]? (a) Hayır, yalnız yeni
ürünler. (b) Evet: bu hatlar araçtan geçmediği için H01-H08 uygulanamaz; ayrı bir "devralınan kilit" türü ve ayrı plan
gerekir. (c) Hat hat ayrı karar.

S11. Kod kapısı gelince görev metnindeki kilit satırı? (a) Aynen kalır (satır + kapı). (b) Kısalır: ürün, kilit no, sha.
(c) Kalkar. Ek: ürün karar dosyasındaki kilit satırına `kilit_no` ve `kilit_sha256` yazılsın mı.

S12. Kilitli ürün için aracın yeniden koşması (CM:206 kural 1)? (a) Serbest; çıktı "kilitli ürün: deneme değil" etiketi
taşır, inceleme istisnası uygulanmaz (araç koduna küçük ek gerekir). (b) Araç kilitli ürün girdisiyle DUR verir; önce
kilit açılır (araç koduna ek gerekir). (c) Araç değişmez; kural yalnız görev metni ve Merkez denetimiyle uygulanır.

S13. Aracın sabitlendiği commit değişir ve örnek aynı PNG sha'sını verirse yeni Serdar sözü gerekir mi? (a) Evet, her yeni
kilit yeni söz ister. (b) Hayır: yalnız `arac.commit` değişen ve aynı sha'yı veren yenileme Merkez kaydıyla olur (yeni bir
kayıt türü gerekir; kural "Kilidi yalnız Serdar açık sözle açar" ile ilişkisi Serdar'ındır).

S14. Kilit hangi örneklerle mühürlensin? (a) Tek çift, tek örnek isim seti (bugün aracın yaptığı: TD:105). (b) Tipik + en
kötü isim / metin seti (araçta henüz yok: olgu 12; deneme planı dilim 2). (c) Birden çok çift. Sonuç: (a)'da "kişiselleştirilen
her alanın sınırı" (karar 4) ölçümsüz kilitlenir; diğer çiftlerde ve uzun isimlerde sığmama üretimde ya da siparişte kapı
FAIL'i olarak çıkar. Ek: parça 2 gelmeden, tek görünümlü üründe karar 5 "tamam" sayılır mı: sayılır (şema 1 ile kilit
çıkabilir) / sayılmaz (şema 1 ile hiçbir kilit çıkmaz; H13).

S15. Karar numarası olmayan üç şey kilitten sonra değişirse hangi kilit açılır, hangi işler geçersiz olur: ürün girdisi
(şekil, baskı alanı px, gerçek mm, alt sınır, şablon); ölçer kabulleri (taşma, çakışma gibi; S3); ürün hattı bağı (araç
yolu, sert kapı listesi; S7)? Tablonun bu oturumun görmediği satırlarında karşılıkları var mı [okunmadı]. Her biri için
ayrı ayrı: (a) 1-5 satırıyla aynı. (b) Ayrı satır yazılır (ör. yalnız alt sınır değişimi karar 6 gibi işlem görür).
(c) Her seferinde Serdar ayrıca söyler.

S16. "Son örnek" şartı hangi işlerde aransın (CM:206, CM:106-107 "toplu üretim" der)? (a) Yalnız toplu üretim çıktıları.
(b) Toplu üretim + mockup, kart, video (her biri için ayrı son örnek ve ayrı Serdar onayı). (c) (b) + sipariş hattı: sipariş
hattında karşılığı "sipariş hattı testi"dir [görev]; her sipariş için değil, hat için bir kez. Sonuç: son örnek aranmayan
işlerde üretim kodunun hangi sürümle koştuğu yalnız damgada görünür, kapıda sınanmaz.

### 11.2 Teknik sorular (öneriyle)

T1. Kilit kodunun yeri. Öneri: `scripts/tasarim_kilit/` ve `data/tasarim_kilit/` (1.1; gerekçe olgu 10).

T2. `hazirla` ve `kilitle` nerede koşsun? Öneri: S2 (a) ya da (b) ise ikisi de Actions'ta, tek iş akışında iki kip
(gerçek katman ve onay kaydı oradan erişilir); ADAY ve mühürlü dosya artifact olarak çıkar, depoya Code oturumu commit
eder ve commit'ten önce sha'yı iş akışı çıktısıyla karşılaştırır. İş akışı tetiklenebilmek için main'de olmalı (CM:11).
S2 (c) ise `hazirla` yerelde koşabilir; `kilitle` yine onay kaydına erişen yerde.

T3. `arac.commit` origin/main'in atası olmalı mı? Öneri: evet (tüketen iş akışları main'den koşar; dalda kalan commit
silinebilir). Sonucu: araç main'e alınmadan kilit çıkmaz (olgu 1).

T4. OZET'e `ozet_sema` (sayı) ve seçenek başına `olcum_sha256` eklensin mi (TD:994, 967)? Öneri: evet, TASARIM ARACI
oturumunun işi olarak; gelene kadar uyarlayıcı anahtar kümesini tam eşler ve OLCUM'u kendi yeniden üretiminden alır.

T5. Karar kilidine `tasarim_kilit` alanı (6.4). Öneri: K6 dilimi olarak, `urun_ayar.py` main'e geldikten sonra.

T6. Onay ve açma kayıtlarının Drive'daki yeri plana yazılmadı. Öneri: iş akışı girdisi ya da depo değişkeni olarak verilir;
`dogrula` yalnız yerel klasör alır (emsal UA:8 "YEREL yol").

T7. Kütüphane kaydı ile kilit aynı kanonik sha ve onay kodunu paylaşsın mı (DP:357-364)? Öneri: evet; kütüphane dilimi
`tasarim_kilit.py`'nin kanonik sha ve onay denetimi fonksiyonlarını içe alır. Not: deneme planındaki `kayit --onay "..."`
(DP:360) sözü komut satırından alıp kayda yazıyor; emsal kural "söz gizli Drive'da" [görev] ile aynı değil; kütüphane
planında düzeltilmesi gerekir.

T8. Katman türünün dosya adından gelmesi (olgu 5). Öneri: araç `tur` alanını kayıttan ya da açık argümandan alsın (TASARIM
ARACI oturumu); kilit bu alana zaten bakmaz.

T9. Birden çok baskı alanı. Öneri: tek kilitte `yuzey` listesi (1.2); tek yüzeyli üründe liste bir öğelidir.

T10. Tüketenin kapıyı çağırdığının denetimi. Öneri: statik tarama testi + iş akışında ayrı `dogrula` adımı (5.2, 9).

T11. ASAMA_BAGLI `ad_esleme` (tablodaki iş adı -> aşama kodu) bu planın yorumudur. Öneri: Merkez tabloyu ve her iş adının
hangi üretim işine karşılık geldiğini görev metninde birebir verir; teyitsiz ad için `denetle` 'tanımsız' döner. İlk
satırdaki "8-10" (mockup sahnesi, kartlar, video [görev]) 6.3'teki örnekle aynı biçimde 'mockup' / 'kart' / 'video' üretim
çıktılarına eşlenir (teyit ister). "11" (menü) ve "14-16 metinleri yeniden kontrol" karar kilidi tarafındaki işlerdir;
tasarım kilidi modülü onları yalnız raporlar.

T12. Onay klasörünün tam kopyası (D04). Öneri: tüketen iş akışlarının ortak tek indirme adımı; önce listeler, sonra indirir,
KLASOR_LISTE.json'u listeden yazar; liste çıktısı beklenmeyen biçimdeyse DUR (CM:113-119). Adım yerelde sahte araçla
sınanır (CM:113, 124).

T13. Geri alınmış açılmayı yakalama (6.1 üçüncü madde). Öneri: `dogrula` iş akışında tam geçmişli checkout ile koşar ve
DURUM.json'un git geçmişini okur; bu ürün için geçmişteki herhangi bir sürümde 'acildi' yazılmış bir kilit bugün 'gecerli'
görünüyorsa DUR. O zaman yalnız commit'i geri almak yetmez; geçmişin yeniden yazılması gerekir. Bedel: tam geçmişli klon
(geçmiş okuyan test ve kod sığ klonda yanlış FAIL verir, CM:120); testi tam geçmişli geçici depoda kurulur.

## Ek: bu planın sınırları

- Depodaki hiçbir betik çalıştırılmadı; hiçbir OZET, OLCUM, Drive dosyası ya da Project belgesi okunmadı. [görev] etiketli
  her şey görev metninden alındı.
- Süreler [tahmin]. Paket sürümü farkının PNG sha'sını değiştirip değiştirmediği [ölçülmedi].
- Plan 5751006'ya göre yazıldı; araç dalı bu görev sırasında f616757'ye ilerledi (bölüm 8, Ek 2). Kod yazılmadan önce
  bölüm 8'deki tablo ve bütün TD / TK dosya:satır atıfları o günkü uçla yeniden okunmalıdır.
- Ornament motorunun sert kapı listesi bu oturumda açılmadı; deneme planının atfıyla (DP:821-829) ve OS:9, 186 ile anıldı.

## İnceleme kaydı

Tek bağımsız inceleme ajanı (işi yapmamış; yalnız okuma), 2 tur. Görevi: "bu plan neden yanlış, kanıtla".

| Tur | Bulgu | Sonuç |
|---|---|---|
| 1 | 19: 6 YÜKSEK, 8 ORTA, 5 DÜŞÜK. Yaklaşık 125 dosya:satır atfı açıldı; 121 doğru, 4 sapma (ajan sayımı) | 19'u da düzeltildi |
| 2 | Tur 1'in 19 bulgusu: 16 kapandı, 3 kısmen. YENİ YÜKSEK: yok. 10 yeni / açık bulgu: 6 ORTA, 4 DÜŞÜK | 10'u da düzeltildi (aşağıda); bu düzeltmeler YENİDEN İNCELENMEDİ (2 tur sınırı) |

Tur 1 YÜKSEK bulguları ve düzeltmeleri: (1) açma kaydı klasörde yoksa açılmış kilit geçerli görünüyordu -> D04 tam klasör
şartı, 6.1 "ne zaman DUR vermez"; (2) kilit zinciri denetlenmiyordu -> D02 zincir, H15, `kilitle`; (3) son örnek kaydı kendi
kendini onaylıyordu -> iki ayrı kayıt, onay ve inceleme Merkez'in Drive kaydında (5.3); (4) tüketenin gerçek araç kodu,
katmanı ve paketleri kapıda sınanmıyordu -> D08; (5) sipariş, kilitli ayardaki örnek isimle çelişiyordu -> `degisebilir`,
D09; (6) blok sha'larının kapsamı tanımsızdı -> 1.4.

Tur 2 bulguları (inceleme sonrası düzeltildi; bağımsız inceleme bu düzeltmeleri görmedi):

| No | Önem | Bulgu | Yapılan |
|---|---|---|---|
| A | ORTA | "`gecmis` yalnız ekleme alır" iddiası D02'nin sınayabildiğinden fazlaydı; geri alınmış açılma ucuz kapıyla daralır | 6.1 düzeltildi; T13 (git geçmişi denetimi) eklendi |
| B | ORTA | "araç yolu kullanmaz" işareti onaysız depo dosyasındaydı (fiilen atlama bayrağı) | işaret kilide alındı (`hat.arac_yolu`); URETIM_KOD.json yalnız dosya listesi |
| C | ORTA | örnek çift dışındaki katmanlar yalnız depo kaydına dayanıyordu | son örnek onay kaydına `gercek_katman_sha256`; D08 (ii); kalan sınır 5.3'te |
| D | ORTA | ölçer kabulleri k6 bloğundaydı (örtük karar) | ayrı `olcer` bloğu; S15 genişletildi |
| E | DÜŞÜK | 1.3 ile 1.4 çelişiyordu; `muhur` 1.4'te yoktu | düzeltildi |
| F | DÜŞÜK | 'iptal' durumunu yazan komut yoktu | `iptal` komutu, 'aday' durumu, test satırı |
| G | DÜŞÜK | `alan_sinir.alan` ve liste anahtarında karakter sınırı tanımsızdı | 2.1'de tanımlandı |
| H | ORTA | T11, 6.3'teki "8-10" eşlemesiyle çelişiyordu | T11 düzeltildi |
| I | ORTA | KARAR_GIRDI'deki üç alanın kilitte yeri yoktu; kabuller onaya bağlanmıyordu | 1.2, 1.4, 2.2 (kabul bağı), test satırı |
| J | DÜŞÜK | "çift ayarı değiştirmez" kaynaksızdı | [ölçülmedi] yazıldı, S14 (c)'ye bağlandı |

Düzeltilmeyen bulgu: yok. Açık kalan ve plana SINIR olarak yazılanlar (bulgu değil, kapının yapamadığı):

| Sınır | Yer |
|---|---|
| Kod Serdar'ın sözünü doğrulayamaz; depoya ve gizli Drive'a birlikte yazabilen biri tutarlı sahte çift üretebilir | 2.2 |
| Kapıyı hiç çağırmayan ya da ayarı sonradan değiştiren betiği modül durduramaz (tarama testi ve damga yalnız görünür kılar) | 5.2 |
| Geri alınmış `ac` commit'i + eksik onay klasörü birlikte kullanılırsa DUR çıkmaz (T13 seçilirse daralır) | 6.1 |
| Son örnek aranmayan aşamalarda örnek çift dışındaki katmanlar yalnız depodaki kayıtla sınanır | 5.3 |
| H07 / H08'in gerçek katmanla bilinen PASS'ı yerelde kurulamaz | 9 |
