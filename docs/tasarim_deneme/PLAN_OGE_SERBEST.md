# PLAN: öğelerin bağımsız yeri, boyu ve çıkarılması (yerleşim deneme aracı)

Durum: YALNIZ PLAN. Kod yazılmadı; araç dosyaları ve ürün girdisi değişmedi. Bu plan hiçbir kapıyı değiştirmez ve eşik
değeri önermez; kapı değişikliği SEÇENEKLERİNİ ve karar için gereken ölçümü yazar. Tasarım tavsiyesi, sıralama, puan yok.
Serdar kararı gereken yerde karar verilmez. "Teknik öneri" yazan yerler yalnız teknik sorulardır.

Dayanak (Serdar, 12 Kas 2026, birebir): "B" (sembolü küçültme işi yapılsın: önce kısa plan, sonra kapı onayı, sonra kod);
"halka ve özgün sembol de dahil olmak üzere, tüm öğelerin yerleri ve boyutları değiştirilebilir olmalı"; "özgün sembol
hariç, istendiğinde her bir öğe tasarımdan çıkarılabilir olmalı". Renk ve doku bu planın DIŞINDADIR (yalnız bölüm 9).

## 0. Ref'ler, kısaltmalar, etiketler

| Kısaltma | Dosya | Commit |
|---|---|---|
| TD | scripts/tasarim_deneme/tasarim_deneme.py | dal tasarim-deneme-dilim1, f6167573 |
| TK | scripts/tasarim_deneme/tasarim_kapi.py | f6167573 |
| TT | scripts/tasarim_deneme/test_tasarim_deneme.py | f6167573 |
| AT | scripts/ay_takvim/ay_takvim_ornek.py | main a9b1323 (araç sha ile sabitler; dokunulmaz) |
| ATK | scripts/ay_takvim/ay_takvim_kapi.py | main a9b1323 |
| YD | scripts/printful/yeni_duzen.py | dal ornament-printful-katalog, c950151 |
| MP | docs/tasarim_deneme/PLAN_TASARIM_DENEME.md (mevcut plan; değişmez) | dal plan/tasarim-deneme, 3fdcc5b |
| KP | docs/tasarim_kilit/PLAN_TASARIM_KILIT.md | dal plan/tasarim-kilit, a3184be |
| CM | CLAUDE.md | main 2e27dd72 |

Araç kodu bu dalda yoktur: `git show f6167573:<yol>`. Etiketler: [ölçüm] = bu oturumda ölçüldü; [hesap] = koddaki /
dosyadaki sayılardan hesap; [tahmin]; [ölçülmedi]; [varsayım] = Serdar'a sorulmadı. "Kontrol ölçümü" her yerde şu demektir:
yerel, deneme sembolü katmanı (sha256 ad677bab…a63f, 3841 x 3632 px), çizimsiz, yalnız `AT.rgba_olcek` (AT:1020-1027) ve
`AT.kutu` (AT:582-584) ile; gerçek katman için KANIT DEĞİLDİR (Serdar 11 Kas). Aracın Actions yolu henüz yoktur.

Ürün girdisi: "eski" = depodaki DENEME_YUVARLAK_1087.json (25,4 mm; güvenli r 543,5; sha256 0d170c64…8d90); "yeni" =
Serdar 12 Kas (23,0 mm; güvenli r 515; henüz koda girmedi). Her rakamın yanında hangi girdiyle hesaplandığı yazılıdır.

Varsayımlar [varsayım]: (a) "boyut" = eş oranlı ölçek; döndürme, esnetme, kırpma, biçim değiştirme planlanmaz (AT:20:
sembol katmanı "yalniz es oranli kucultulur"); (b) "büyütme yok" kuralı aynen (AT:1226-1227; TD:610-615).

Bugünkü yapı (özet; kanıtlar): grup tek fonksiyonda TEK oranla kurulur: `AT.grup_kur` (AT:1186-1286) halkayı, iki küçük
burcu, (istenirse) logoyu ve ana sembolü posterdeki göreli düzenle yerleştirir; ana sembolün ölçeği `olcek * s_ana`dır
(AT:1215, 1256) ve yeri poster oranından gelir (AT:1216, 1257-1258). Araç bu fonksiyonu değiştirmeden çağırır (TD:619-631)
ve grubu `grup_x / grup_y` noktasına taşır (TD:634-648). Yazılar araçta kurulur: isim satırı tek dizi (TD:716-730), metin
satırları (TD:731-741); ikisi de yatayda güvenli merkeze ortalanır (TD:747). Kapı 2 grup bölümü `ATK.grup_kapisi`'dir
(ATK:209-360), araç onu sentetik META ile değiştirmeden çağırır (TK:135-169).

## 1. P1: öğe modeli

### 1.1 İki model seçeneği (grup kavramı)

| | G1: çapa çemberi + öğe sapmaları | G2: her öğe mutlak |
|---|---|---|
| Tanım | Bugünkü `grup_x`, `grup_y`, `halka_r` (ya da `grup_r`) bir "çapa çemberi" tanımlar (merkez + yarıçap R). Ana sembol, halka, küçük burçlar ve logo bu çembere GÖRE yer (u, v; R birimi) ve boy (çarpan) alır. Yazılar bugünkü gibi güvenli alan biriminde (Rg). | Her öğenin yeri ve boyu doğrudan yerleşim biriminde (Rg) verilir; grup anahtarları kalkar. |
| Eski istekler (dilim 1, 1B) | Yeni anahtarlar varsayılandayken eski kurulum yolu korunabilir (iki yol; soru T5): aynı sonuç beklenir (test: bölüm 11, E1). Ayar sözlüğü büyür (bölüm 10). | Eski anahtarlar (grup_x, halka_r ...) ya ayrı bir "eski biçim" olarak tutulur ve eski yolla kurulur (iki yol) ya da yeni anahtarlara çevrilir; çevrimde kayan nokta farkı PNG baytını değiştirebilir [ölçülmedi]. |
| Birlikte taşıma / ölçekleme | `grup_x / grup_y / halka_r` bütün grubu taşır ve ölçekler (bugünkü grup ızgarası aynen, TD:140-141, 461-483). | Grubu taşımak = 4 - 5 anahtarı birlikte değiştirmek; ızgara türü yeniden tanımlanır. |
| Kapı 2 | Poster göreli düzen varsayılanda korunur: `ATK.grup_kapisi` varsayılanda aynen çağrılabilir (bölüm 7.3). | Yeni anahtarlarla verilen düzende poster göreli düzen kavramı yoktur; `ATK.grup_kapisi` yalnız eski biçimli istekte çağrılabilir. |
| Halka yokken birim | Çapa çemberi çizilmese de tanımlıdır (bölüm 3). | Birim zaten Rg. |

Seçim Serdar'dadır (soru S1); plan öneri vermez. Planın kalanı, anahtar adlarını somut yazabilmek için G1 adlarıyla
yazıldı; bu bir tercih değildir. G2 seçilirse bölüm 1.2 ve 7.3 yeniden yazılır.

### 1.2 Anahtarlar (G1; adlar teknik öneridir)

R = çapa yarıçapı = `halka_r` x Rg (halka_r modunda); Rg = güvenli yarıçap (TD:312-317). "Varsayılan" = f6167573
davranışı. Aralıklar BAŞLANGIÇ DEĞERİDİR: yalnız yanlış girişi yakalar, tasarım kararı değildir (TD:121 ile aynı kural).

| Öğe | Bugünkü anahtarlar (TD:122-127) | Yeni anahtar; birim; varsayılan | Başlangıç aralığı ve dayanağı |
|---|---|---|---|
| çapa (grup) | grup_merkez, grup_x, grup_y, halka_r / grup_r | yok (aynen) | aynen (TD:125-127) |
| ana sembol | yok (boy ve yer grup_kur içinde sabit, AT:1215-1216, 1256) | `sembol_oran`: çarpan; 1,0. `sembol_u`, `sembol_v`: sembolün KAYNAK kutusunun (yan json, paysız) merkezi, çapa merkezine göre, R birimi; 'poster' = bugünkü yer: u +0,0010, v -0,1245 [hesap; DENEME katmanıyla: yerlesim78 u0 -0,6233, u1 +0,6253, v0 -0,7119 ve katmanın kaynak kutusu oranı 3332 / 3541 → yükseklik 1,1749 R (grup_kur yüksekliği katmanın kendi oranından alır, AT:1189-1190)] | sembol_oran 0,30 .. üst uç ürün başına hesap: `olcek * s_ana * sembol_oran <= 1` (büyütme yok). 0,30 = `halka_r` alt ucunun aynısı (TD:125); başka dayanağı yok. u, v: -1,30 .. +1,30: `kucuk_v` üst ucunun (TD:126) iki yöne uygulanması; dayanak yalnız mertebe |
| halka | halka_kalinlik, halka_centik (kapalı: yalnız 1,0 / 'ozgun', TD:126, 129) | `halka_oran`: çarpan; 1,0 (halka yarıçapı = R x halka_oran). `halka_u`, `halka_v`: halka merkezinin çapa merkezinden sapması, R birimi; 0, 0 | halka_oran 0,30 .. üst uç hesap: `olcek * halka_oran <= 1` (0,30: `halka_r` alt ucunun aynısı; başka dayanağı yok). u, v: -1,30 .. +1,30 (yukarıdaki gibi) |
| küçük burçlar | kucuk_u (simetrik sayı ya da 'poster'), kucuk_v, kucuk_oran | Çift olarak: yok (aynen). Tek tek istenirse (soru S3): `kucuk1_u`, `kucuk1_v`, `kucuk1_oran`, `kucuk2_*`; varsayılan = çift anahtarının değeri | aynen (TD:125-126) |
| logo | logo (çarpan ya da 'yok'), logo_yer ('kucuk_arasi' / 'isim_arasi') | `logo_yer` 'serbest' + `logo_u`, `logo_v` (logo merkezi, R birimi); varsayılan yok ('serbest' yalnız istenince) | u, v: -1,30 .. +1,30; logo çarpanı aynen 0,50 .. 2,00 (TD:127) |
| isimler | isim_cap, isim_y, isim_duzen | `isim_x`: mürekkep kutusu merkezinin güvenli merkezden yatay sapması, Rg birimi; 0,0 (TD:747 bugün 0'a ortalar) | -1,0 .. +1,0 (isim_y ile aynı, TD:126) |
| metin / tarih | metin_tur, metin_cap, metin_y, satir_aralik, satirlar | `metin_x`: aynı tanım; 0,0 | -1,0 .. +1,0 |
| var / yok | logo 'yok', metin_tur 'yok' | `ogeler`: çizilen öğe adlarının listesi (MP:296'daki adla); varsayılan = hepsi. Ana sembol listede yoktur (çıkarılamaz) | alt küme: halka, kucuk (ya da kucuk1 / kucuk2), logo, isim (ya da isim1 / isim2), metin |

Olgular:
- `sembol_oran` ve `sembol_u / v` birlikte, Dayanak 7 (5)'teki iki küçülme merkezini de ifade eder: "sembol kendi yerinde" =
  yalnız `sembol_oran`; "halka merkezine doğru" = `sembol_oran` c ve `sembol_u / v` = poster değeri x c.
- Bağımsız sembol boyu ve yeri bugün `grup_kur`'un İÇİNDE sabittir (AT:1256-1258); ay takvimi kodu dokunulmaz olduğu için
  yeni anahtarlar araçta ek kurulum kodu ister (bölüm 2.3).
- Taban B2 (poster düzeni): yeni anahtarlar B2'yi tek başına ifade edilebilir yapmaz. B2'nin kodda tanımlı olmamasının
  nedeni isim ve metin yerinin aralık dışına düşmesidir: isim tabanı +1,070, metin tabanı +1,452 Rg [ölçüm + hesap; bu
  oturumun dilim 1 raporu madde 9, depoda kayıtlı değil; eski girdi]; `isim_y` ve `metin_y` aralığı -1,0 .. +1,0'dır (TD:126-127). B2 için gereken şey aralık
  kararıdır (soru S9), yeni anahtar değil.
- Dışarıdan verilen bir emsal düzen yalnız ayar sözlüğüyle ifade edilebilir mi: aşağıdakiler varsa EDİLEMEZ (bu planın
  anahtarlarında yok): döndürülmüş ya da eğik öğe [varsayım a]; yay üstüne yazı; iki ismin ayrı satır ya da ayrı yerde
  olması (bugün tek dizi "A & B", TD:716-720; soru S3); çok satırlı metin (bugün en çok 1 satır, TD:131); yazı tipi,
  harf aralığı, hizalama (sola / sağa) seçimi; çember olmayan halka (elips; ornament halkası analitik elipstir, MP:373-376);
  asimetrik küçük burç yeri (soru S3'e bağlı); emsalde araçtaki öğe türleri dışında bir öğe (çerçeve, ek süs, ikinci
  logo); öğelerin üst üste binme sırası (bugün sabit: gölge, sembol, yazılar, grup öğeleri; TD:796, AT:853). Bunların
  dışındaki bir emsal (öğeler çember + sembol + iki küçük işaret + logo + tek satır isim + tek satır metin ise) G1
  anahtarlarıyla ifade edilebilir [hesap; denenmedi].

## 2. P2: ana sembol

### 2.1 Dayanak 7 sorularının cevabı

(1) Mod sınırı. `grup_kur` grubun çevreleyen dairesini ana sembol dahil bütün noktalardan hesaplar (AT:1217-1225) ve
ölçeği ondan bulur (AT:1225). `grup_merkez` 'grup' ya da `grup_r` modunda sembolün boyu / yeri değişirse çevre dairesi ve
ölçek değişir: sembol boyu halkadan bağımsız OLAMAZ (MP:381-383 ile aynı tespit). Seçenekler: (i) `sembol_oran`,
`sembol_u / v`, `halka_oran`, `halka_u / v` yalnız halka_r + 'halka' merkez modunda kabul edilir, diğer modlarda girdi
hatası (bugünkü ızgara kuralıyla aynı kalıp, TD:471-472); (ii) diğer modlarda çevre dairesi araçta gerçek öğelerle
yeniden hesaplanır (ek kod; "en uzak piksel" hedefi de değişir, madde 2). Seçim soru K9'dadır; plan öneri vermez.

(2) "En uzak grup pikseli" hedefi. Kapı, grubun en uzak pikselini `hedef_r` ile karşılaştırır (ATK:219, 257-283, 353;
pay 2 px, ATK:78). Araçta halka_r modunda hedef = ölçek x ilk geçişin çevre yarıçapıdır (TD:604-616); ilk geçiş istenen
küçük burç ayarıyla ama ana sembol poster boyunda ve poster yerinde kurulur (TD:604-608). Olgu: bu modda koşul üretimi
kendi ilk geçişiyle karşılaştırır (TK:140-143); bağımsız denetim boy koşuludur (bölüm 3). Dilim 1B koşusunda en uzak
piksel farkı 0,293 - 1,699 px, kapı 2'nin en büyük bağımsız farkı 0,977 - 1,699 px idi [ölçüm; OLCUM, OZET]. B1'de çevre
yarıçapını halkanın belirlediğine dair kanıt dolaylıdır (TT:984 testi grup_r modundadır). `sembol_oran` > 1, `sembol_u / v`
ile dışarı taşıma ya da `halka_oran` < 1 durumunda sembol ya da küçük burç en uzak öğe olabilir; o zaman ilk geçişin
verdiği hedef gerçek en uzak pikselden sapar. Koşulun FAIL verip vermeyeceği sapmanın payı aşmasına bağlıdır
[ölçülmedi]. Bu koşulun serbest düzende ne olacağı bölüm 7.3 ve soru K1'dedir.

(3) Değişiklik nerede yapılır. Ay takvimi dosyaları dokunulmazdır. Teknik öneri: yeni kurulum TD içinde ayrı fonksiyon
(`grup_kur_serbest`), yalnız bir serbest anahtar varsayılan DIŞINDA iken çağrılır; varsayılanda bugünkü yol (TD:619-631)
AYNEN kalır. Yeni fonksiyon AT'nin yapı taşlarını değiştirmeden kullanır: `AT.grup_kaynak` (halka ve küçük burç kaynak
alfaları ve poster yerleri, AT:1044-1072), `AT.logo_kaynak` (AT:1159-1176), `AT.rgba_olcek` (sembol, AT:1020-1027); maske
küçültme ve k hesabı AT:1260-1267 ile aynı satırlar (tek adım INTER_AREA; k kaynaktan büyük olamaz). Kapı 2'nin grup
bölümü için seçenekler ve "aynı sayılar" eşdeğerlik testi bölüm 7.3 ve 11'dedir.

(4) Sembol boyunun değiştirdiği öteki şeyler:
- İç gölge oranı: `D_ana` yerleşen sembolün yarı kalınlığıdır (TD:706-713) ve diğer öğelerin iç gölge genişliği
  `min(1, yari_kal / D_ana)` ile ölçeklenir (AT:849, 886). Sembol küçülünce D_ana küçülür, diğer öğelerin iç gölgesi
  değişir: sembol boyu değişince yazıların ve halkanın PİKSELLERİ de değişir (maskeleri ve yerleri değişmez) [hesap;
  ölçülmedi]. "Tek öğe değişir" testi (TT; MP 4.2) sembol ızgarasında bu yüzden maske düzeyinde tutar, piksel düzeyinde
  tutmaz.
- Renk uyumu hedefi: `Lana` yerleşen sembolün alfa >= 0,9 piksellerinin Lab ortancasıdır (TD:787) ve bütün öğeler ona
  kaydırılır (AT:618-626). Ölçek değişince ortanca değişebilir [ölçülmedi].
- Grup - yazı boşluğu ölçeri (TK:449-458; eşik 12 px, ATK:76) ve çakışma ölçerleri (TK:252-292, 461-465) sembol maskesini
  kullanır: değerleri sembol boyu ve yeriyle değişir (beklenen davranış; tanım değişmez).
- "Büyütme yok": bugün `olcek`, `olcek * s_ana`, `olcek * kucuk_oran` ve logo için denetlenir (TD:610-615; AT:1226-1227).
  Yeni çarpanlar aynı kurala eklenir: `olcek * s_ana * sembol_oran <= 1`, `olcek * halka_oran <= 1`.
- Kapı 2 sembol bölümü ölçek koşulları (TK:99, 125) yerleşen sembolün gerçek ölçeğiyle çalışır: tanım aynen.
- Yıldız engeli sembol maskesinden kurulur (TD:776): yerleşen maskeyle aynen. Zemin merkezi grup merkezidir (TD:769),
  sembol yerinden etkilenmez.

(5) Küçülme merkezi: bölüm 1.2 (iki anahtar ikisini de üretir). Hangisinin kullanılacağı tasarım kararıdır; plan seçmez.

(6) Eşdeğerlik: bölüm 11, E1.

### 2.2 Ornament'e denk sembol boyu [hesap; deneme sembolü alfasıyla]

Ornament'te sembol boyu `YD.b3_olcek` ile bulunur: sembol yatayda ortalı, dikey alan 230 .. 562 (954 px tuval), bütün
mürekkep halka merkezinden en çok 306 px (YD:28-33, 45, 135-160); sonuç 0,85 ile çarpılır (YD:35, 222-229) ve dikeyde boşluğun
%75'i üstte kalacak yere konur (YD:36, 236-237). Bu oturumda `YD.b3_olcek` deneme sembolü alfasıyla çalıştırıldı (yalnız
sürekli model; YD:177'deki çizimle düzeltme adımı `b3_olcek_render` UYGULANMADI):

| Büyüklük | Değer | Kaynak |
|---|---|---|
| Sığan en büyük ölçek x 0,85 → 954 tuvalde sembol kutusu | 299,9 x 282,2 px | [hesap] YD.b3_olcek |
| Sembol genişliği / halka yarıçapı (336 px) | 0,8926 | [hesap] |
| Aynı oran posterde (u1 - u0) | 1,2486 | [dosya] yerlesim78.json |
| Ornament'e denk boy çarpanı (`sembol_oran` karşılığı) | 0,715 | [hesap] 0,8926 / 1,2486 |
| Ornament'te sembol kutusunun merkezi (v) ve alt kenarı | -0,284 R; +0,136 R | [hesap] üst = 230 + 0,75 x (332 - 282,2) |
| Alt kenarı ornament sınırına (+0,173 R) getiren çarpan, halka merkezine doğru küçülme | 0,373 | [hesap] 0,1726 / 0,4629 |
| Aynı, sembol kendi merkezinde küçülürse | 0,506 | [hesap] (0,1726 + 0,1245) / 0,5875 |

Son iki satır BOY oranı değildir (Dayanak 3); yalnız alt kenar koşulunun karşılığıdır. Bu tablonun bütün sayıları DENEME
katmanına bağlıdır: sembol yüksekliği katmanın kaynak kutusu oranından alındı (1,1749 R; alt kenar +0,4629 R).
yerlesim78.json'un kendi v1 değeriyle (+0,4473) yükseklik 1,1593 R, merkez -0,1323 R, son iki çarpan 0,386 ve 0,526 olur
[hesap]. Gerçek katmanla [ölçülmedi]: gerçek katmanın mürekkep kutusu kaynak kutusundan farklıdır (görev metni Dayanak
3). Bu sayılar hesap sonucudur; hedef, öneri ya da ızgara ucu değildir.

### 2.3 Sembol halkadan taşarsa ya da halka sembolden küçükse bugünkü kapılar ne der

Bugün "sembol halkanın içinde olmalı" diye bir kapı ya da ölçer YOKTUR. Dolaylı olarak: çakışma ölçerleri halka / sembol
çiftini sayar (takvim tanımı ve çift pikseli TK:252-263, 295-300; ornament tanımı 7 x 7 genişletmeyle TK:266-292); kapı
2'nin "en uzak piksel" koşulu FAIL verir (madde 2); güvenli alan taşması ölçeri (TK:209-249) ve sembol tuval dışına
taşarsa sert DUR (TD:752-753) aynen çalışır. Bunun dışında bir denetim istenip istenmediği soru K8'dir.

## 3. P3: halka

- Bağımsız yer ve boy: `halka_oran`, `halka_u / v` (bölüm 1.2). Halka kaynağı poster alfasıdır (AT:1056) ve bugün grup
  ölçeğiyle küçültülür (AT:1262-1264); serbest kurulumda ölçeği `olcek * halka_oran` olur. Çizgi kalınlığı ölçekle
  orantılı değişir (bugün de öyle; `halka_kalinlik` kapalı, soru S4). Küçük halkada 200 çekirdek piksel kapısı DUR
  verir: dilim 1B'de halka_r 0,30 seçeneği DUR renk_uyum_piksel verdi ("cekirdek piksel 142 < 200") [ölçüm; OZET]; öğenin halka
  olduğu çıkarımdır (OZET öğe adını yazmaz); `halka_oran`
  aralığının alt ucu bu bölgededir.
- Etkilenen kapılar: boy koşulu bugün "ölçülen halka yarıçapı = halka_r x Rg" der (TK:67-75, 158-168; Serdar K1: sert):
  `halka_oran` != 1 iken hedefin `halka_r x Rg x halka_oran` olması TANIM DEĞİŞİKLİĞİDİR (soru K5). "Halka merkezi grup
  merkezinde" koşulu (ATK:255-256) `halka_u / v` != 0 iken hedef nokta değişmeden sağlanamaz (soru K5).
- Çıkarma ve birim: G1'de çapa çemberi halka çizilmese de tanımlıdır; `halka_r`, `grup_merkez` 'halka' ve ölçek
  (TD:610: `halka_r * Rg / cember R`) aynen kalır, yalnız halka öğesi kurulmaz / boyanmaz. Kapı tarafı: `ATK.grup_kapisi`
  halkayı ZORUNLU ilk öğe sayar (ATK:223) ve bütün bağımsız ölçümleri halkaya uydurulan çemberden türetir (ATK:251-254,
  300-320, 350-351): halkasız görselde bu fonksiyon çalıştırılamaz. Yollar bölüm 6'da (H-a / H-b).

## 4. P4: yazılar

- Yatay yer: `isim_x`, `metin_x` (bölüm 1.2). Bugün her yazı öğesi `cx`'e ortalanır (TD:747).
- Genişlik sınırı: isim satırının sınırı o satırdaki güvenli alan kirişidir (TD:722; `kiris`, TD:326-337) ve kiriş güvenli
  MERKEZE göre simetrik varsayılır. `isim_x` != 0 iken aynı sınır, satırın bir ucunun güvenli alandan taşmasına izin
  verir; metin genişliği ölçeri (TD:737-742) için de aynı. Sınırın kaydırılmış satır için nasıl tanımlanacağı soru K6.
  K3 kuralı (kiriş 0 → sınır tuval genişliği, TD:723-727) ve "8 denemede sığmıyor" DUR'u (AT:563-573) tanımca aynen.
- İki ismin ayrı konumu: bugün isimler TEK öğedir ('isimler', TD:729). 'iki_yan' düzeni (isim1 [logo] isim2; MP:305) ve
  logo 'isim_arasi' kodda yoktur; istenirse geri dönüş uygulanır (TD:402-409). İki isim ayrı öğe olursa: iki ayrı
  sığdırma (bugünkü kural "iki isim BİRLİKTE küçülür", AT:559) ya da ortak çap; altın sırasında bir öğe artar (gren
  sırası kayar, bölüm 6.2); öğe sayısı ölçerinin beklenen listesi değişir (TK:422). Karar soru S3.
- Çıkarma: bölüm 6.

## 5. P5: logo

- Bugün: logo yalnız küçük burç satırında, grup ekseninde kurulur (AT:1171-1172) ve kapı 2 yalnız o yeri ölçer (ATK:326).
  Boy çarpanı var (TD:127), çıkarma var ('yok').
- Serbest yer: `logo_yer` 'serbest' + `logo_u / v`. Kaynak alfa yine `AT.logo_kaynak`'tan (kesim, 0,994 ölçek, temizlik
  aynı; AT:1163-1170); yerleştirme serbest kurulumda. `ATK.grup_kapisi` logo yerini sabit beklediği için serbest logoda
  FAIL verir: bölüm 7.3.
- Dilim 3 ile ilişki (MP:986): 'isim_arasi' = logonun iki ismin ARASINA, isim genişliklerine göre otomatik oturması
  ('iki_yan' düzeni). Serbest logo yeri elle koordinat verir; otomatik oturtma kuralını içermez. İkisi ayrı şeydir:
  serbest yer dilim 3'ün yerini tutmaz; dilim 3 yapılırsa 'isim_arasi' ayrı bir `logo_yer` değeri olarak kalır.

## 6. P6: çıkarma

### 6.1 Öğe başına kurulum yolu

| Öğe | Bugün | Yol seçenekleri | Kalan öğelerin yeri |
|---|---|---|---|
| logo | 'yok' var; grup ölçeği ve çevre dairesi logosuz hesaplanır (AT:1197, 1217-1225) | aynen | değişmez |
| metin | `metin_tur` 'yok' var (TD:130) | aynen | değişmez |
| isimler | yok: isim satırı her zaman kurulur (TD:716-730) | `ogeler`'de 'isim' yoksa satır kurulmaz | değişmez (yazılar birbirinden bağımsız konumlanır, TD:744-749) |
| küçük burçlar | yok: grup_kur her zaman kurar (AT:1059-1071) | K-a "çizilmedi": tam setle kurulur, maske üretilir, boyanmaz. K-b "küçük burçsuz kurulum": ek kod (MP:519-520) | halka_r + 'halka' merkezde değişmez. K-b'de: `grup_r` modunda çevre dairesi değişir, sembol ve halka büyür (MP:519-520); halka_r + 'grup' merkezde boy değişmez (TD:610), merkez kayar (AT:1219-1221) |
| halka | yok | H-a "çizilmedi": halka kurulur, maskesi üretilir, boyanmaz. H-b "halkasız kurulum": serbest kurulumda halka hiç kurulmaz | G1'de halka_r + 'halka' merkezde değişmez (çapa çemberi tanımlı kalır); halka çevre dairesine girdiği için (AT:1217-1225) H-b'de `grup_r` modunda ölçek ve merkez, halka_r + 'grup' merkezde yalnız merkez değişir (TD:610) |
| ana sembol | çıkarılamaz (Serdar sözü) | yok | yok |

### 6.2 Çıkarmanın öteki etkileri

- Altın çizim sırası ve gren: bütün altın öğeler TEK üreteçle, öğe sırasıyla çizilir (AT:854; sıra: yazılar, sonra grup
  öğeleri, logo sonda, AT:853, 1253). Bir öğe çizimden düşerse SONRAKİ öğelerin greni değişir; maskeleri ve yerleri
  değişmez (TT:998'deki "isim boyu degisince kucuk burcun motor katmani (gren) degisir; maskesi ayni kalir" testi aynı olguyu belgeliyor). Yani "çıkarılan öğe
  kalanların yerini değiştirmez" doğrudur, "piksellerini değiştirmez" doğru değildir. "Çizilmedi" yollarında (K-a, H-a)
  öğe üreteci ilerletecek biçimde çizilip atılırsa gren aynı kalır (ek süre: öğe başına çizim süresi; halka 14 sn
  [ölçüm; dilim 1 ön ölçümü, OZET'te yok]). Olgu: kalın halka dalında halka AYRI üreteçle çizilir ve ana üreteç halka boyu
  kadar ilerletilir (AT:867-869). Üreteç `AT.altin_ogeler` içinde kurulduğu (AT:854) ve AT dokunulmaz olduğu için bu kalıp
  çizilmeyen bir öğeye AT değişmeden uygulanamaz; bugünkü kodla gren sırasını korumanın yolu öğeyi çizip atmaktır.
  Hangisinin istendiği soru S6.
- Yıldız engeli: boyanan bütün öğelerin ve sembolün maskesinden kurulur (TD:772-778). Çıkarılan öğe engelden düşerse o
  bölgeye yıldız gelebilir (yıldız sayısı ve yerleri değişir) [ölçülmedi].
- Öğe sayısı ölçeri: beklenen liste bugün sabit kurulur (TK:422: isimler, metin satırları, halka, kucuk1, kucuk2, logo).
  `ogeler` ile beklenen listenin ayardan okunması TANIM DEĞİŞİKLİĞİDİR (soru K7).
- Yazı yokken ölçerler: grup - yazı boşluğu ölçeri yazı öğesi yoksa PASS veremez (TK:458: `gyv` boşsa False). İsim
  ölçeri isim öğesini zorunlu okur: isim yoksa TK:482'deki `next(...)` StopIteration fırlatır; bu bir DUR değildir,
  seçenek üretimi hatayı yeniden fırlatır (TD:829-831) ve koşu çöker (çıkış 2). Yani isim çıkarma bugünkü kapı koduyla
  ÇALIŞMAZ; isimsiz / metinsiz seçenekte bu ölçerlerin "uygulanamaz" yazması tanım değişikliğidir (soru K7).

### 6.3 Mevcut planın açık YÜKSEK bulgusu (MP:1 başlık notu; MP:522-540) her yolda

Bulgu: K-a'da çizilmeyen küçük burçların geometri maskeleri kapı 2 sembol bölümünün "örtülen piksel" hesabına girerse
(ATK:414-423, 427) sembolün renk ve kenar karşılaştırma bölgesi daralır: gevşetme.

- Olgu: araç ATK'nin o bölümünü ÇAĞIRMAZ; aynı koşulları kendi kopyasında uygular (TK:89-131) ve "örtülen" maskeyi
  kendisinin verdiği `diger` listesinden kurar (TK:106-115, 383: bugün bütün yazı ve grup öğeleri).
- K-a / H-a ("çizilmedi"): `diger` listesine yalnız BOYANAN öğeler verilirse çizilmeyen öğenin maskesi "örtülen" hesabına
  girmez; ölçüm bölgesi daralmaz. Bu bir kod kuralıdır, test ister (bölüm 11, C3: çizilmeyen öğe `diger`'e eklenirse test
  FAIL). Bu yapılırsa bulgunun sembol bölümü kısmı kapanır [iddia; kod yazılınca incelenmeli].
- K-a / H-a'nın öteki kısmı AÇIK KALIR: tek doku, kontrast, düz renk, altın binme, yıldız ve taşma ölçümlerinin kapsamı
  "boyanan öğeler"e daralır (MP:522-538); MP inceleme kaydı aynı listeye grup - yazı boşluğunu ve gerçek ölçü (mm)
  uyarısını da ekler (MP:1109). Bu Serdar onayı ister (MP soru 6 k; burada soru K4). MP'nin önerdiği yeni ölçer
  ("çizilmeyen öğe gerçekten yok mu", MP:535) bu planda da gereklidir; eşiksiz yazılır.
- K-b / H-b ("kurulmaz"): çizilmeyen öğenin maskesi hiç yoktur; "örtülen" bulgusu doğmaz. Bedeli: kapı 2 grup bölümünün
  TANIMI değişir (liste ve halka çemberi; bölüm 7.3).

## 7. P7: kapılar

### 7.1 Sert kapılar (tam liste: TK:7-33 ve TD'deki DUR'lar)

Sütun "durum": A = aynen; D = tanımı değişmeli (seçenek ve gereken ölçüm yazılı); D? = değişip değişmeyeceği Serdar kararına
bağlı; U = o ayarda uygulanamaz.

| Kapı | Bugünkü tanım | Durum | Değişiklik seçenekleri; gevşetme mi; gereken ölçüm |
|---|---|---|---|
| girdi (ürün, ayar, istek, bütçe) | TD:239-300, 339-409, 428-483, 538-573 | A | Yeni anahtarlar aynı doğrulama kalıbına eklenir (tür, aralık, bilinmeyen anahtar). Kapı değişikliği değil. |
| ortam, sabit kaynak sha256, yüzey, motor / KILIT, sembol biçimi | TD:226-232, 167-222, 76-104, 183-200; AT:685-702, 981 | A | Serbest kurulum yeni kaynak dosyası okumaz (grup_kaynak ve logo_kaynak'ın dosyaları sha tablosundadır). Yüzey denetimine (içe alınan adların imzası) yeni kullanılan AT adları eklenir: kapsam genişler, tanım aynı. |
| kayıt ve komut DUR'ları: katman sha, pafta sha / hücre / boyut, süre kaydı | TD:1084-1085, 943-1003, 491-519 | A | - |
| büyütme yok | TD:610-615; AT:1226-1227; AT:860-861 | A | Aynı kural yeni çarpanlara uygulanır (2.1 madde 4). Kapsam genişler; tanım aynı. |
| çerçeve | AT:865-873 | A | - |
| 200 çekirdek piksel | AT:138, 621-623 | A | Altın öğeler için aynen. Olgu: ana sembol bu kapıdan geçmez (altın çizimine girmez, AT:849). |
| kapı 2 sembol: en-boy | TK:96-101, 125; eşik ATK:75 | D? | Bölüm 7.4 (kontrol ölçümü) ve soru K2. |
| kapı 2 sembol: ölçek <= 1, ölçülen ölçek | TK:99, 102, 125 | A | Yerleşen ölçekle (`olcek * s_ana * sembol_oran`). OLGU: bu bölüm ölçeği ÜRETİMDEN okur (TK:102) ve aynı ölçekle yeniden küçültür (TK:128); sembolün AYARA göre doğru boyda olduğunu denetlemez. Bugün o denetim yalnız grup bölümündedir (ATK:230 ölçek eşitliği, ATK:351 boy). Serbest sembolde bu denetim yeni kapıya açıkça yazılmazsa kaybolur = gevşetme (soru K1). |
| kapı 2 sembol: yeniden küçültme, kaynak sha | TK:127-131 | A | - |
| kapı 2 sembol: renk ve kenar, "örtülen piksel" | TK:106-126 | A / D | Tanım aynen. Çıkarma yolunda `diger` listesi kuralı (6.3). Sembol başka öğenin ALTINDA kalacak biçimde taşınırsa örtülen bölge büyür, karşılaştırılan piksel azalır: bugünkü tanımın sonucu; alt sınır yok [ölçülmedi]. Soru K8. |
| kapı 2 grup: liste, yeniden kurulum eşitliği | ATK:223, 229-244 | D | Bölüm 7.3. |
| kapı 2 grup: halka çemberi, küçük burç yeri / boyu, ana sembol yeri / boyu, en uzak piksel, logo | ATK:251-256, 257-283, 300-321, 322-343, 345-352 | D | Bölüm 7.3. |
| kapı 2: boy koşulu (K1) ve beklenen merkez | TK:55-75, 158-168; ATK:249 | A / D | Çapa merkezi olarak aynen. `halka_oran` != 1, `halka_u / v` != 0 ya da halka yokken: soru K5. |
| tuvalden taşan grup öğesi → DUR (K2) | yeniden kurulum eşitliğinin sonucu (üretim maskeyi kırpar, TD:789-795; kırpılan maske kaynağın küçültülmüşü değildir, ATK:240); etiket TK:574-581 | A / D | Bugün ayrı bir koşul DEĞİL, yeniden kurulumun yan sonucudur. Serbest kapıda öğe başına birebir yeniden kurulum (7.3 GK1 a) korunursa sonuç da korunur; (a) zayıflatılırsa kaybolur = gevşetme. |
| çıktı kapısı (K4) | TK:319-334, 470-473 | A | - |
| ana sembol tuval dışına taşıyor | TD:752-753 | A | - |
| öğe tümüyle tuval dışında | TD:754-756 | A | - |
| isim: mürekkep tuval dışında; 8 denemede sığmıyor; kiriş 1 px altında | TD:763-764; AT:563-573; TD:726-727 | A / U | İsim çıkarılmışsa uygulanmaz. `isim_x` ile sınır tanımı: soru K6. |

### 7.2 Ölçer kapılar

| Ölçer | Bugünkü tanım | Durum | Not |
|---|---|---|---|
| güvenli alan / yasak bölge taşması (3 ölçüm) | TK:188-249 | A | Maskeler yerleşen öğelerden. |
| tuval taşması (öğe kutusu tuvali aşıyor; yazılar dahil) | TD:751-757; TK:468 | A | Serbest yerlerle daha sık tetiklenir; tanım aynı. |
| çakışma (takvim ve ornament tanımı), çift pikselleri | TK:252-300, 461-465 | A | Çıkarılan öğe için kapsam: soru K4. |
| tek doku dE00, kontrast, yazım farkı, düz renk | TK:403-435; eşikler ATK:74-83 | A | Çıkarılan öğe için kapsam: soru K4. Sembol boyu D_ana ve Lana üzerinden bu değerleri değiştirebilir [ölçülmedi]. |
| yıldız | TK:444-446; engel TD:772-778 | A | Çıkarmada engel listesi: 6.2. |
| öğe sayısı | TK:422-424 | D | Soru K7. |
| grup - yazı boşluğu (12 px) | TK:449-458; ATK:76 | A / U | "Grup" = sembol + grup öğeleri (TK:449). Yazı yoksa uygulanamaz: soru K7. Halka çıkarılınca ya da küçülünce ölçülen şey değişir (tanım aynı). |
| metin tabanı, metin genişliği | TK:491-500; TD:737-742 | A / D | `metin_x` ile genişlik sınırı: soru K6. |
| isim | TK:482-490 | A / U | İsim yoksa uygulanamaz: soru K7. |
| gerçek ölçü uyarısı | TK:502-568 | A | Öğe başına; yeni öğe türü yok. |
| bilgi ölçümleri (çift pikseli, küçük burç - yazı uzaklığı, yıldız sayısı) | TK:295-316, 474-481 | A | Eşiksiz. |

### 7.3 Kapı 2 grup bölümü: neden olduğu gibi kalamaz ve seçenekler

`ATK.grup_kapisi` iki şey yapar: (1) grubu `U.grup_kur` ile YENİDEN kurar ve her maskenin, yerin ve ölçeğin birebir aynı
olmasını ister (ATK:229-244); (2) bağımsız ölçüm: halkaya çember uydurur ve küçük burçların, ana sembolün, logonun yerini
ve boyunu O ÇEMBERE ve poster oranlarına göre bekler (ATK:251-256, 300-321, 322-343, 345-352); ayrıca en uzak piksel =
hedef (ATK:257-283). İkisi de poster göreli düzeni ve tek ölçeği varsayar. Bu yüzden: `sembol_oran` != 1 ya da
`sembol_u / v` != 'poster' iken (1) ve ana sembol ölçümleri (ATK:350-351) FAIL verir; `halka_oran` değişince ölçülen
ölçek `s_m` (ATK:253), `halka_u / v` değişince ölçülen halka merkezi (ATK:252) değişir ve öteki öğelerin yer hedefleri
kayar; serbest logo ATK:326'da FAIL verir;
halkasız görselde fonksiyon çalışamaz (ATK:223, 251). Yani serbest anahtarlar varsayılan dışındayken `ATK.grup_kapisi`
olduğu gibi KULLANILAMAZ. Fonksiyon dokunulmazdır; değişiklik yalnız araç tarafında (TK) olabilir.

| Seçenek | Ne yapılır | Kapı tanımı açısından | Eşdeğerlik |
|---|---|---|---|
| GK0 | Serbest anahtarlar eklenmez (bugünkü durum). | Değişiklik yok. | - |
| GK1 "serbest grup kapısı" | TK'de yeni fonksiyon: her öğe TEK TEK denetlenir: (a) maske = kaynağın beklenen ölçekle tek adım küçültülmüşü (yeniden kurulum, öğe başına); (b) tam sayı yer = ayardan bağımsız hesaplanan hedef (çapa merkezi + u, v x R; `beklenen_merkez` / `beklenen_boyut` kalıbı, TK:55-75); (c) maskeden ölçülen yer / boy (halkada çember uydurma, ötekilerde alfa kutusu) hedefle karşılaştırılır; sembolün boyu da AYARDAN beklenen ölçekle karşılaştırılır (7.1'deki olgu); (d) kırpılmış (tuvalden taşan) öğe FAIL ((a)'nın sonucu olarak). Varsayılan ayarda `ATK.grup_kapisi` AYNEN çağrılmaya devam eder. | Koşulların TÜRÜ aynı kalır (birebir yeniden kurulum; konum ve ölçüm karşılaştırması), HEDEFLER "poster göreli" yerine "ayardan" gelir. PAYLAR bu planda belirlenmez: bugünkü değerlerin (ATK:77-78) yeni koşullara uygulanıp uygulanamayacağı ancak ölçümle görülür (CM:217-219). "En uzak piksel = hedef" ve "küçük 1 solda, küçük 2 sağda" (ATK:321) koşullarının serbest düzendeki akıbeti soru K1'dedir: kaldırılmaları gevşetmedir; korunmaları için seçenekler K1 (b3) ve (b4). | Varsayılan ayarda GK1 fonksiyonu da çalıştırılır ve `ATK.grup_kapisi` ile AYNI sayıları vermelidir (bölüm 11, E2). |
| GK2 "ATK + ayrı sembol kapısı" | Halka, küçük burçlar ve logo poster göreli kalır (yalnız sembol serbest): `ATK.grup_kapisi` grup öğeleri için AYNEN çağrılır; ana sembol argümanı olarak poster yerindeki / boyundaki SANAL sembol verilir; gerçek sembolün yeri ve boyu TK'de ayrı koşulla denetlenir. | ATK'nin ana sembol koşulları (ATK:230-233, 350-351) sanal sembolü denetler: gerçek sembol için bu koşulların yerini yeni koşul alır = tanım değişikliği. Sanal sembol "en uzak piksel" hesabına da girer (ATK:262): gerçek sembol o hesaptan düşer. Halka ve logo serbestliğini KARŞILAMAZ. | Varsayılanda sanal = gerçek: aynı sayılar. |

Karar için gereken ölçümler (hiçbiri yapılmadı): GK1'in (c) ölçümlerinin serbest ayarlarda verdiği fark dağılımı (bugünkü
pay 2 px ile karşılaştırma için); küçük ölçekte çember uydurmanın (ATK:192) ve alfa kutusunun kararlılığı; gerçek
katmanla aynı ölçümler (Actions yolu yok).

### 7.4 Küçük sembolde en-boy koşulu: kontrol ölçümü

Koşul: yerleşen sembolün alfa > 0,5 kutusunun en / boy oranı ile katmanın kendi oranı arasındaki fark <= 0,005
(TK:96-101, 125; ATK:75; katman oranı 1,06273, deneme sembolü). Kutu TAM SAYI pikseldir.

Kontrol ölçümü [yerel, deneme sembolü, çizimsiz; tuval 1087; fonksiyonlar AT.sembol_yukle, AT.rgba_olcek, AT.kutu;
süre 80 sn]. Sembol ölçeği = halka_r x Rg / 2835,9 x s_ana (s_ana 0,99995; AT:1215). "Beklenen" = kaynak kutusu x ölçek.

| Nokta | Ölçek | Kutu alfa > 0,5 (px) | Beklenen (px) | Kutu alfa > 0,02 | En-boy farkı | Ölçülen ölçek | Yeniden küçültme | Sonuç |
|---|---|---|---|---|---|---|---|---|
| halka_r 0,30 (eski girdi) | 0,05749 | 203 x 191 | 203,6 x 191,6 | 205 x 193 | 0,00010 | 0,05733 | aynı | PASS |
| halka_r 0,40 | 0,07666 | 270 x 256 | 271,4 x 255,4 | 272 x 256 | 0,00804 | 0,07625 | aynı | FAIL |
| halka_r 0,45 | 0,08624 | 305 x 287 | 305,4 x 287,4 | 306 x 289 | 0,00001 | 0,08613 | aynı | PASS |
| halka_r 0,50 | 0,09582 | 338 x 320 | 339,3 x 319,3 | 340 x 320 | 0,00648 | 0,09545 | aynı | FAIL |
| halka_r 0,55 | 0,10540 | 373 x 351 | 373,2 x 351,2 | 375 x 353 | 0,00005 | 0,10534 | aynı | PASS |
| halka_r 0,60 | 0,11498 | 407 x 384 | 407,2 x 383,1 | 408 x 384 | 0,00283 | 0,11494 | aynı | PASS |
| halka_r 0,65 | 0,12457 | 440 x 414 | 441,1 x 415,1 | 442 x 416 | 0,00007 | 0,12426 | aynı | PASS |
| halka_r 0,70 | 0,13415 | 474 x 447 | 475,0 x 447,0 | 475 x 447 | 0,00233 | 0,13386 | aynı | PASS |
| halka_r 0,7514 | 0,14400 | 509 x 479 | 509,9 x 479,8 | 511 x 481 | 0,00010 | 0,14374 | aynı | PASS |
| halka_r 0,884 (B1, eski girdi) | 0,16941 | 600 x 565 | 599,9 x 564,5 | 601 x 565 | 0,00078 | 0,16944 | aynı | PASS |
| halka_r 0,99 (eski girdi) | 0,18972 | 672 x 633 | 671,8 x 632,2 | 673 x 633 | 0,00112 | 0,18978 | aynı | PASS |
| halka_r 0,884 (B1, yeni girdi r 515) | 0,16053 | 568 x 535 | 568,4 x 534,9 | 569 x 535 | 0,00105 | 0,16041 | aynı | PASS |
| ornament'e denk boy (x 0,715), B1 eski girdi | 0,12111 | 428 x 404 | 428,8 x 403,5 | 429 x 404 | 0,00332 | 0,12087 | aynı | PASS |
| ornament'e denk boy (x 0,715), B1 yeni girdi | 0,11476 | 406 x 383 | 406,4 x 382,4 | 407 x 383 | 0,00268 | 0,11466 | aynı | PASS |
| alt kenar çarpanı 0,373, B1 eski girdi | 0,06317 | 223 x 211 | 223,7 x 210,5 | 225 x 211 | 0,00586 | 0,06298 | aynı | FAIL |
| alt kenar çarpanı 0,373, B1 yeni girdi | 0,05986 | 211 x 199 | 212,0 x 199,4 | 212 x 201 | 0,00243 | 0,05959 | aynı | PASS |
| alt kenar çarpanı 0,506, B1 eski girdi | 0,08569 | 303 x 285 | 303,4 x 285,5 | 304 x 287 | 0,00043 | 0,08557 | aynı | PASS |
| alt kenar çarpanı 0,506, B1 yeni girdi | 0,08119 | 287 x 271 | 287,5 x 270,5 | 288 x 271 | 0,00369 | 0,08105 | aynı | PASS |

Tarama (aynı ölçüm; ölçek 0,040 - 0,200, adım 0,001; en-boy koşulu):

| Ölçek bandı | Kutu genişliği (px) | PASS | FAIL | Bandın en büyük farkı |
|---|---|---|---|---|
| 0,040 - 0,059 | 141 - 209 | 10 | 10 | 0,02018 |
| 0,060 - 0,079 | 212 - 279 | 14 | 6 | 0,01078 |
| 0,080 - 0,099 | 283 - 350 | 18 | 2 | 0,00831 |
| 0,100 - 0,119 | 354 - 421 | 19 | 1 | 0,00504 |
| 0,120 - 0,139 | 425 - 492 | 18 | 2 | 0,00677 |
| 0,140 - 0,159 | 495 - 563 | 20 | 0 | 0,00403 |
| 0,160 - 0,179 | 566 - 633 | 20 | 0 | 0,00348 |
| 0,180 - 0,199 | 636 - 703 | 20 | 0 | 0,00305 |
| 0,200 (tek nokta) | 707 | 1 | 0 | 0,00117 |

Ölçülmeyenler: renk farkı ve kenar koşulları (son görsel ve altınsız zemin ister), gerçek katman. Tablodaki "sonuç" yalnız
bu üç koşulundur, seçeneğin sonucu DEĞİLDİR: aracın gerçek koşusunda (dilim 1B) halka_r 0,30 başka kapıdan DUR verdi
(200 çekirdek piksel: 142) ve halka_r 0,40 aynı en-boy farkıyla (0,00804) `kapi_sert: 2_sembol` verdi [ölçüm; OZET].

Koşul neden düşüyor [kanıt: yukarıdaki tablo]:
- halka_r 0,40'ta alfa > 0,5 kutusu 270 x 256, beklenen 271,4 x 255,4: genişlik 1,4 px eksik, yükseklik 0,6 px fazla.
  270 / 256 = 1,05469; katman oranı 1,06273; fark 0,00804.
- Aynı ölçekte alfa > 0,02 kutusu 272 x 256'dır: yani sembolün uç pikselleri küçültmeden sonra vardır ama alfası 0,5'in
  altındadır (INTER_AREA kısmi kaplama). 0,5 eşikli kutu, sembolün uç noktalarının piksel ızgarasına göre fazına bağlı
  olarak 0 - 2 px dar ya da 0 - 1 px geniş çıkıyor.
- Kutu tam sayı olduğu için yüksekliği h olan kutuda 1 px'lik sapma oranı yaklaşık 1 / h kadar değiştirir [hesap]: h 256'da
  0,0039, h 565'te 0,0018. Küçük kutuda iki kenarın sapması toplanınca 0,005 aşılıyor; sonuç ölçekle PERİYODİK değişiyor
  (0,40 FAIL, 0,45 PASS, 0,50 FAIL, 0,55 PASS).
- Görev metnindeki şüphe ("FAIL deneme sembolüne özgü olabilir"): bu ölçüm şüpheyi ne doğrular ne çürütür. Deneme
  katmanı keskin kenarlıdır (alfa > 0,5 ve alfa > 0,02 kutuları aynı: [150, 150, 3691, 3482]); kenar profili değişken
  olarak denenmedi. Gözlenen sapma küçültme + 0,5 eşiği + tam sayı kutu ile açıklanabiliyor [çıkarım; tek katmanla];
  gerçek katmanda koşulun hangi ölçeklerde FAIL verdiği, hatta verip vermediği [ölçülmedi].

"Ornament'e denk sembol boyu bu tuvalde üretilebilir mi" [kontrol ölçümü; yerel, deneme sembolü]: denenen iki noktada
(B1, eski ve yeni girdi; ölçek 0,121 ve 0,115; kutu 428 x 404 ve 406 x 383 px) çizimsiz ölçülebilen üç koşul (en-boy,
ölçülen ölçek, yeniden küçültme) PASS verdi. Aynı ölçek bölgesinde (0,100 - 0,139) taramanın 40 noktasından 3'ü en-boy
koşulunda FAIL verdi: sonuç ölçeğin binde birlik değişimine duyarlıdır. Renk ve kenar koşulları ölçülmedi. BUGÜNKÜ
kapılarla cevap "hayır"dır: ana sembol halkadan bağımsız boydayken kapı 2 grup bölümü koddan bilinen FAIL verir
(ATK:230-233, 350-351; bölüm 7.3); üretilebilirlik soru K1'in kararına bağlıdır. Gerçek katman için ölçüm GEREKİR ve bugün
yapılamaz (Actions yolu yok).

### 7.5 Serdar'ın "kapı onayı" için karar listesi (seçenek + sonuç; öneri ve eşik değeri yok)

- K1. Kapı 2 grup bölümü, serbest ayarlarda. (a) GK0: serbestlik yok, kapı aynen. (b) GK1: öğe başına serbest kapı;
  sembolün ayara göre boy / yer denetimi yeni kapıya yazılır (7.1 olgusu). "En uzak piksel" ve "küçük 1 solda, küçük 2
  sağda" koşullarının akıbeti ayrıca kararlaştırılır: (b1) kaldırılır (gevşetme); (b2) kaldırılır, kırpılan öğenin FAIL
  vermesi yeterli sayılır (bu da gevşetmedir: kırpma koşulu zaten (a) yeniden kurulumun sonucudur, yeni bir şey eklemez);
  (b3) her öğe için ayardan hesaplanan "beklenen en uzak nokta" koşulu yazılır (yeni koşul; ölçüm ister); (b4) ilk geçiş
  araçta serbest ayarla kurulur ve bugünkü koşul korunur (olgu: halka_r modunda bu koşul bugün de üretimi kendi ilk
  geçişiyle karşılaştırır, TK:140-143). (c) GK2: yalnız sembol serbest. Sonuç: (a)'da bu planın P2 - P5 bölümleri
  uygulanmaz; (b)'de kapı tanımı değişir ve dilim D1 inceleme noktası olur; (c)'de halka ve logo serbestliği kalmaz.
- K2. Küçük sembolde en-boy koşulu (7.4). (a) Aynen: bazı ölçeklerde seçenek DUR verir, gizlenmez, hücrede kapı kodu
  yazar; hangi ölçeklerin düştüğü önceden bilinmez. (b) Ölçüm yöntemi değişir (ör. tam sayı kutu yerine alt piksel
  ölçüsü): tanım değişikliğidir; gevşetme mi sıkılaştırma mı olduğu ancak iki yöntemin aynı örneklerde karşılaştırmalı
  ölçümüyle söylenebilir. (c) Eşik değişir: gevşetmedir; değer bu planda yazılmaz, ölçüm ister. (d) Koşul ölçere çevrilir:
  gevşetmedir. Her seçenek için gereken ölçüm: 7.4 taramasının gerçek katmanla tekrarı (bugün yapılamaz) ve (b) için iki
  yöntemin yan yana tablosu.
- K3. Çıkarma yolu. Küçük burçlar: K-a / K-b. Halka: H-a / H-b. Sonuçlar bölüm 6.1 - 6.3'te.
- K4. "Çizilmedi" yolunda ölçerlerin kapsamının "boyanan öğeler"e daralması (MP soru 6 k): evet / hayır. Hayırsa K-a ve
  H-a kullanılamaz.
- K5. Boy koşulu ve "halka merkezi" koşulu: `halka_oran` != 1, `halka_u / v` != 0 ya da halka yokken. (a) Hedef ayardan
  yeniden tanımlanır (yarıçap x halka_oran; merkez + sapma): tanım değişikliği; aynı payın küçük ya da kaydırılmış halkada
  ne kadar sıkı olduğu [ölçülmedi] (7.3'teki gereken ölçüm). (b) O ayarlarda koşul
  uygulanmaz: gevşetme. (c) Halka serbestliği eklenmez.
- K6. Yatay kaydırılmış isim / metin satırında genişlik sınırı. (a) Bugünkü kiriş aynen (merkeze göre simetrik): satırın
  bir ucu güvenli alandan taşabilir; taşma ölçeri yazar. Bu, isim sığdırma sınırının ve isim / metin genişliği
  ölçerlerinin koruduğu şeyi daraltır: gevşetme niteliğindedir. (b) Sınır = satırın kendi merkezinden güvenli alan kenarına en
  kısa uzaklığın iki katı: isim daha erken küçülür (isim için sıkılaştırma; ölçüm ister). (c) Yatay yer eklenmez.
- K7. Öğe sayısı ölçeri ve yazı ölçerleri, öğe çıkarılınca. (a) Beklenen liste `ogeler`'den okunur; yazı yoksa grup - yazı
  ve isim ölçerleri "uygulanamaz" yazar (tanım değişikliği). (b) Tanımlar sabit kalır: öğe çıkarılan seçenekte öğe sayısı
  ölçeri FAIL yazar, yazı yokken grup - yazı ölçeri FAIL yazar; isim çıkarılamaz (bugünkü kod isimsiz veride çöker,
  bölüm 6.2).
- K8. Sembol - halka ilişkisi ve "örtülen piksel" için yeni ölçüm. (a) Yeni ölçüm yok (bugünkü durum: 2.3). (b) Eşiksiz
  BİLGİ ölçümü eklenir (sembolün halka dışında kalan pikseli; kapı 2 sembol bölümünde karşılaştırılan piksel sayısı):
  kapı değildir. (c) Kapı istenir: eşik ancak ölçümden sonra konuşulur.
- K9. Mod sınırı (2.1 madde 1): (i) serbest sembol / halka yalnız halka_r + 'halka' merkezde; (ii) öteki modlarda da
  (ek kod, "en uzak piksel" hedefi değişir).

## 8. P8: ızgaralar ve seçenek sayısı

- Bugün: bir istekte TEK ızgara türü (TD:140-141, 461-483), eksen başına en çok 7 değer (TD:138; kodun başlangıç değeri,
  Serdar kuralı değil), satır = boyut adımı, sütun = yer adımı. Bütçe: yerel koşu başına 900 sn (TD:110); dilim 1B'de 22
  seçenek 790,8 sn sürdü ve araç hesabı 23 seçenek sığar dedi [ölçüm]. 7 x 7 = 49 hücre bu bütçeye sığmaz [hesap].
- Yeni ızgara türleri (aynı kalıp; adlar teknik öneri): 'sembol' (boyut = `sembol_oran` çarpanı; yer = `sembol_v` farkı),
  'sembol_merkez' (boyut = `sembol_oran` çarpanı; yer ekseni yok, `sembol_u / v` poster değeri x çarpan: "halka merkezine
  doğru" küçülme), 'halka' (`halka_oran` çarpanı x `halka_v` farkı), 'isim' (`isim_cap` çarpanı x `isim_y` farkı),
  'metin' (aynı kalıp), 'logo' (`logo` çarpanı x `logo_v` farkı). Yatay yer eksenleri (`*_u`, `*_x`) ayrı tür ister.
- "Tek ızgara türü" sürer mi: (a) sürer: her öğe ayrı koşuda denenir; koşu sayısı artar. (b) bir istekte iki tür: hücre
  sayısı çarpılır; bütçe (22 - 23 seçenek) pratikte tek türe yer bırakır [hesap]. Karar soru S8.
- Izgara uçları ve adımları bu planda SEÇİLMEDİ ve önerilmedi: hangi değerlerin deneneceği görev metninde verilir.
  Girdi doğrulamasının sınırları bölüm 1.2'deki başlangıç aralıklarıdır. Bölüm 2.2'deki sayılar ızgara ucu değildir.
- Bütçe kuralının bilinen eksiği (dilim 1B raporu madde 11 a, b): üretimden önceki ön kontrol (her farklı küçük burç
  ayarı için ilk geçiş) bütçe hesabına girmiyor. Serbest kurulumda ilk geçiş sayısı artabilir; bütçe kuralının bunu
  sayması ayrı girdi kuralı değişikliğidir (soru S12).

## 9. P9: renk ve doku (yalnız engeller; çözüm tasarlanmadı)

Serdar: renk ve doku "her öğeye ayrı ayrı"; arka plan rengi ve dokusu da değişebilmeli. Bugünkü kodda engeller:

1. Renk uyumu bütün altın öğeleri ana sembolün tonuna çeker: `renk_uyum` her öğe katmanının Lab ortancasını `Lana`'ya TAM
   kaydırır (AT:618-626); araç `Lana`'yı sembolden alır ve bütün öğelere verir (TD:787-788).
2. "Tek doku" ölçeri bunu bekler: her öğenin sembole dE00 farkı eşik altında olmalı (TK:403-427; eşik ATK:74).
   Öğe başına renk bu ölçerin tanımıyla çelişir (ölçer FAIL yazar).
3. Süreç başına tek KILIT ve tek palet: `Motor` kurulurken KILIT ortam değişkenlerine yazılır ve palet tek dosyadan
   okunur (AT:691-697, 706-712); `oge_katman` tek parametre kümesiyle çalışır (AT:815-820).
4. Ana sembol katmanı kuralı: sembol yalnız eş oranlı küçültülür, rengi katmanın kendi RGB'sidir (AT:20, 1256); kapı 2
   sembol bölümü son görseldeki sembol pikselinin katmanla 1 seviye içinde aynı olmasını ister (TK:116, 125-126). Sembolün
   rengini / dokusunu değiştirmek bu sert kapının tanımına dokunur.
5. Zemin tek kaynaktan: `zemin_radyal` ve `zemin_yildiz` motor dosyalarından (TD:766-782); ürün girdisi şeması `zemin`
   için yalnız 'motor' kabul eder (TD:292-293).
6. Tek üreteç ve sıra: gren bütün öğelerde aynı üreteçten gelir (AT:854); öğe başına doku seti bu sırayı ve mevcut
   bayt eşitliği testlerini etkiler.

Bu plandaki yerleşim anahtarları öğe başına görünüm atamasına ENGEL DEĞİLDİR: öğe adları sabit kalır ('isimler',
'metin_N', 'halka', 'kucuk1', 'kucuk2', 'logo', 'sembol') ve görünüm bir öğe adına bağlanabilir. Tek bağ: iki isim ya da
iki küçük burç ayrı öğe olursa (soru S3) görünüm de ayrı ayrı atanabilir hâle gelir.

Parça 2 planına bırakılan sorular: Dayanak 1 (f) ve (g); madde 2 ve 4'teki kapı tanımları; palet / KILIT'in öğe başına
nasıl taşınacağı; zeminin öğe sayılıp sayılmayacağı (soru S5).

## 10. P10: kayıt ve kilit

- OZET bugün seçenek başına TAM ayar sözlüğünü taşır (TD:1005-1008, 1039) ve tek sürüm tanıtıcısı `arac` dizesidir
  (TD:1033: 'tasarim_deneme dilim 1b').
- `uret` olgusu: OZET'teki ayarı yeniden doğrular ve EŞİTLİK ister (TD:1080-1082). Yeni anahtarlar varsayılan değerle
  sözlüğe eklenirse eski OZET'in ayarı (yeni anahtarlar yok) yeniden doğrulanınca aynı çıkmaz: `uret` eski OZET'te
  DUR 'girdi_ayar' verir. Seçenekler: (a) eski OZET yalnız ESKİ commit'le yeniden üretilir (kilit planının yaklaşımı:
  kilit `arac.commit`'e sabitlenir, KP:661); (b) OZET'e sayısal `ayar_surum` eklenir, `uret` eski sürümde eksik anahtarları
  varsayılanla tamamlayıp karşılaştırır (bu, eşitlik DUR'unun tanımını değiştirir: gevşetme niteliğindedir); (c) yeni
  anahtarlar yalnız varsayılan DIŞINDA iken sözlüğe yazılır (sözlük eski biçimde kalır; "tam ayar" ilkesinden sapma).
  Plan öneri vermez; karar soru S11.
- Kilit planına etki: KP H01 OZET anahtar kümesinin TAM eşitliğini ister, fazla ya da eksik anahtar DUR'dur (KP:344, 701);
  yeni ayar anahtarları ve yeni `olcum_ozet` alanları uyarlayıcıda yeni `arac` sürüm satırı ister (KP:680-685 aynı işi
  dilim 1B için yapmış). KP:661 "yeni ayar anahtarı (sembol boyu)" satırı bu durumu öngörür. Kilit planının kendisi bu
  planla değişmez; sıra ilişkisi soru T2.
- Dilim 1 / 1B koşularının yeniden üretilebilirliği: varsayılan ayarda aynı PNG sha256 (bölüm 11, E1); OZET biçimi
  değiştiği için eski OZET dosyaları yukarıdaki (a) / (b)'ye bağlıdır.
- Bilgi (bu planda düzeltilmez; görev metni Dayanak 6): `uret` sert DUR almış seçenekte de "AYNI" der (TD:1090, 1094).

## 11. P11: testler

Her satır bilinen PASS + bilinen FAIL; mutasyonda FAIL vermeli (CM:212-223, KALİTE 3 - 5).

| No | Kural | Bilinen PASS | Bilinen FAIL / mutasyon |
|---|---|---|---|
| E1 | Varsayılan eşdeğerliği (Dayanak 7 (6)) | Yeni anahtarlar varsayılanda: B1 PNG sha256 = 307208f7…09e1; kapı sonuçları ve OLCUM sayıları f6167573 koşusuyla aynı. Sabitler: eski ürün girdisi sha256, deneme sembolü sha256, OZET'teki paket sürümleri (ortam farklıysa test "ATLANDI" yazar, PASS saymaz). | Serbest kurulum varsayılanda da çağrılacak biçimde bozulursa ya da ölçek ifadesi değişirse sha farklı: FAIL. |
| E2 | GK1 kapısı = ATK.grup_kapisi (varsayılanda aynı sayılar) | Aynı veride iki fonksiyonun öğe başına fark değerleri eşit. | GK1'in bir hedefi değiştirilince eşitlik bozulur: FAIL. |
| E3 | Serbest kurulum = AT.grup_kur (varsayılana eşdeğer ayarda) | Serbest kurulum fonksiyonu doğrudan çağrılır: her öğenin maskesi, tam sayı yeri, k değeri ve ölçeği AT.grup_kur çıktısıyla birebir aynı. | Kopyalanan satırlardan biri (AT:1260-1267 kalıbı) değiştirilince eşitlik bozulur: FAIL. |
| C1 | Sembol boyu / yeri | Varsayılan dışı bir `sembol_oran` ile kurulan sembol: kutu = ayardan beklenen ölçek; öteki öğelerin maskeleri ve yerleri aynı ("tek öğe değişir", maske düzeyi). | Üretimde ölçek %5 saptırılır: YENİ kapının ayara göre boy koşulu FAIL vermeli (bugünkü sembol bölümü bunu YAKALAMAZ: ölçeği üretimden okur, TK:102, 125, 128). `sembol_oran` 'grup' merkez modunda: girdi hatası (K9 (i) ise). |
| C2 | Halka boyu / yeri | `halka_oran` ile ölçülen yarıçap = hedef (K5 (a) ise). | Üretim yarıçapı saptırılır: FAIL. |
| C3 | Çıkarma ve "örtülen" kuralı (6.3) | Çizilmeyen öğe son görselde yok; kalanların maskesi ve yeri aynı; `diger` yalnız boyanan öğeler. | MP:1106'daki test: çizilmeyen öğenin maskesinin altında kalan sembol pikseli son görselde BOZULUR: kapı 2 sembol bölümü FAIL vermeli (maske `diger`'e eklenirse bu FAIL kaybolur: mutasyon). Öğe sayısı listesi sabit bırakılır: ölçer FAIL. K7 (a) seçilirse: isimsiz veride kapı kodu çökmemeli. |
| C4 | Yazı yatay yeri | `isim_x` ile mürekkep kutusu merkezi = hedef. | Üretim 3 px kaydırılır: test FAIL. |
| C5 | Büyütme yok (yeni çarpanlar) | Sınırın altında kabul. | Üstünde girdi hatası (üretim yok). |
| C6 | Tuvalden taşan öğe (K2) serbest kapıda | Tuvalde kalan öğe PASS. | Kırpılan öğe: sert FAIL ve kök neden etiketi (bugünkü davranışın korunması). |
| C7 | `uret` ve ayar sürümü (10; soru S11) | Eski biçimli OZET seçilen yolla yeniden üretilir. | Bilinmeyen sürüm: DUR. |
| C8 | En-boy tablosu (7.4) | Tablodaki PASS noktaları PASS. | Tablodaki FAIL noktaları FAIL (K2 kararına göre güncellenir). |

- TEST AĞI (CM:124): yeni testler TT'nin başındaki ağ kapatma ön ekiyle aynı süreçte koşar; alt süreç testi aynı ön eki
  kullanır (TT:39-48: `AG_KAPALI` / `ALT_SUREC`). Yeni ağ yolu açılmaz.
- "İterasyon yerelde, 60 sn altında" (CM:111): TT'nin tam koşusu 906 - 923 sn sürüyor [dilim 1B raporu; OZET'te yok].
  Teknik öneri: TT'ye `--hizli` seçeneği: kaynaksız testler (2 sn [ölçüm]) + çizimsiz geometri testleri (grup kurulumu
  ve kapı 2 grup bölümü; renk haritası kurulmadan). Çizimsiz ölçüm bu oturumda 18 nokta + 161 noktalık tarama için 80 sn
  sürdü [ölçüm]; hızlı alt kümenin 60 sn altında kalıp kalmadığı [ölçülmedi]. Tam koşu commit öncesi ve temiz kopyadan
  aynen kalır (CM:111-123 bölgesi).

## 12. P12: ürün ve tedarikçi bağımsızlığı (yalnız olgular ve seçenekler)

- Kodda tedarikçiye özgü hiçbir ad ya da kimlik yoktur. Ürün girdisi dosyasının alanları (TD:239-300): `sekil`,
  `baski_px`, `gercek_mm`, `mm_kaynak`, `guvenli`, `guvenli_pay_px`, `yasak`, `alt_sinir`, `zemin`. Bu planın anahtarları
  yalnız iki büyüklüğe dayanır: güvenli alan merkezi ve yerleşim birimi (TD:312-317; TK:55-75) ve çapa yarıçapı; ikisi de
  ürün girdisinden türer.
- Ürün girdisinden GELMEYEN, tuvale göre oranlanmayan piksel sabitleri vardır: taşma ölçümünün ışık payı 8 px (TK:43),
  ornament çakışma tanımının 7 ve 5 px çekirdekleri (TK:44), grup - yazı boşluğu 12 px ("px, 5400 tuval", ATK:76), yıldız
  payı 12 px (ATK:81), kapı 2'nin konum payları 1 ve 2 px (ATK:77-78). Bunlar 1087 ve 5400 px tuvalde aynı piksel
  değeriyle çalışır; başka çözünürlükteki ürün için anlamları değişir (kapı tanımı sorusu; bu planda karar yok).
- Bugün yeni bir ürünün araca girmesi için ürün girdisi dosyası YETMEZ (yukarıdaki sabitlere ek olarak): (1) görsel üretimi yalnız 'yuvarlak' şekilde
  (TD:696, 1013; şema üç şekli tanır, TD:116); (2) çift sabit: yalnız CANCER_LIBRA (TD:105; küçük burç yerleri yalnız o
  çift için tanımlı, AT:107); (3) zemin yalnız 'motor' (TD:292-293); (4) sembol katmanı yerelde deneme sembolüdür.
- Dikdörtgen baskı alanı (poster, tişört, kupa sargısı; MP dilim 5): yerleşim birimi güvenli kutunun kısa kenarının
  yarısıdır (TD:317; TK:60-63, 72-73) ve kiriş kutu genişliğidir (TD:329-331). G1 modeli bu birimle çalışır [hesap;
  denenmedi]: çapa çemberi kısa kenara göre ölçeklenir; yazıların dikey aralığı (-1 .. +1 Rg) uzun kenarda alanın
  tamamına erişmez (dikey 5400 x 7200 girdisinde uzun kenarın yarısı 1,36 Rg [hesap: TT:65-66'daki DIKEY sözlüğü, 3420 / 2520]).
  Aralığın şekle göre tanımlanması soru S9'a bağlıdır.
- Daire ve dikdörtgen dışı baskı alanı (oval, serbest kesim maskesi): bugünkü şema ifade EDEMEZ: `guvenli` yalnız daire ya
  da kutudur (TD:239-300; TK:188-195), `yasak` yalnız daire, kutu ve üst çizgidir (TK:197-205). Maske dosyasıyla güvenli
  alan yeni şema alanı ve taşma ölçerinin yeni girdisi demektir; kiriş hesabı (TD:326-337) maskeden yapılmalıdır.
- Tek tasarımdan çok oranlı dijital çıktı: bir koşu = bir ürün girdisi = bir tuvaldir (TD:1010-1016). Aynı ayar sözlüğü
  başka oranlı bir ürün girdisiyle yeniden koşulabilir (uzunluklar göreli birimde); sonuç her oranda ayrı ölçülür. Tek
  koşuda çok oran yoktur; öğelerin oranlara göre farklı yer alması gerekiyorsa oran başına ayrı ayar gerekir.
- Seçenekler (karar Serdar / Merkez; sıra soru S10): (a) önce yuvarlakta öğe serbestliği, şekil genellemesi sonra (MP
  dilim 5 aynen); (b) önce şekil genellemesi; (c) birlikte (dilim boyu büyür).

## 13. P13: dilimler ve açık sorular

### 13.1 Dilimler (süreler [tahmin]; her dilim en çok 2 deneme)

| Dilim | Kapsam | Dosyalar | Önkoşul | MP dilimleriyle ilişki | Süre |
|---|---|---|---|---|---|
| D0 | Ürün girdisi güncellemesi (23,0 mm; r 515) | ürün girdisi + TT sabitleri | Serdar'ın pay sorusu | ayrı görev (görev metni Dayanak 5) | ayrı |
| D1 | Sembol serbestliği: `sembol_oran`, `sembol_u / v`; serbest kurulum fonksiyonu; kapı (K1, K2, K9 kararına göre); 'sembol' ızgaraları; E1, E2, E3, C1, C5, C8 | TD, TK, TT | K1, K2, K9 kararı | MP dilim 4'ün "bağımsız sembol boyu" kısmını İÇERİR; "isim merkezli küçük burç yeri" kısmı D3'e kalır | 5 - 7 saat |
| D2 | Halka serbestliği ve çıkarma; küçük burç çıkarma; isim çıkarma; `ogeler` | TD, TK, TT | K3, K4, K5, K7 kararı; D1 | MP dilim 2'nin "kombinasyonlar (K-a)" kısmını İÇERİR ve halkayı ekler | 5 - 7 saat |
| D3 | Yazı yatay yeri; iki isim / iki küçük burç ayrı (S3 "ayrı" ise); logo serbest yeri | TD, TK, TT | K6, S3 kararı | MP dilim 3 ('iki_yan', isim arası logo) ile KESİŞİR: S3 ve otomatik oturtma kararına göre birleşir ya da ayrı kalır | 4 - 6 saat |
| D4 | Kalan ızgaralar, tipik / en kötü setler, çok sayfalı pafta | TD, TT | D1 - D3 | MP dilim 2'nin kalan kısmı | 3 - 5 saat |
| D5 | Dikdörtgen şekiller | TD, TK, TT + ürün girdisi | S10 | MP dilim 5 aynen | 3 - 4 saat |
| D6 | Actions yolu ve gerçek katman ölçümü (7.4 taramasının tekrarı dahil) | iş akışı + test | Serdar / Merkez kararı | MP dilim 8 aynen | 3 - 4 saat + 1 koşu |

Sıra için teknik öneri (karar Serdar'da): D0, D1'den önce yapılırsa E1 sabitleri bir kez yazılır; D0 sonra yapılırsa E1
eski girdiye sabit kalır ve yeni girdi için ikinci sabit eklenir. K2 kararı gerçek katman ölçümü isterse D6, D1'in kapı
kısmından önce gerekir.

### 13.2 Serdar kararı gereken sorular (seçenek ve sonuç; öneri yok)

- S1. Model: G1 (çapa çemberi + sapmalar) / G2 (her öğe mutlak). Sonuçlar bölüm 1.1.
- S2. Kapı onayı: K1 - K9 (bölüm 7.5), madde madde.
- S3 (Dayanak 1 c). İki isim ve iki küçük burç TEK TEK mi, çift olarak mı ayarlanır / çıkarılır; mesaj satırları tek tek
  mi. "Tek tek": öğe sayısı artar, sığdırma ve gren sırası değişir (bölüm 4, 6.2), anahtar sayısı artar. "Çift": bugünkü
  yapı; asimetrik düzen ifade edilemez.
- S4 (Dayanak 1 d; MP soru 2). Halka kalınlığı açılsın mı: (a) kapalı kalır; (b) açılır (kapı 2'nin kalın halka dalı ve
  bilgi ölçümleri devreye girer, ATK:265-283).
- S5 (Dayanak 1 e). Zemin, yıldızlar ve dış gölge "öğe" mi, çıkarılabilir mi. Evetse: zemin şeması (TD:292-293), yıldız
  ölçeri (TK:444-446) ve dış gölge (AT:136, 643-648) için ayrı kapsam kararı gerekir; bu planın anahtarlarında yoktur.
- S6. Çıkarılan öğe için gren: (a) kalan öğelerin greni değişebilir (maske ve yer aynı); (b) gren de aynı kalmalı
  ("çizilmedi" yolunda öğe çizilip atılır; ek süre).
- S7 (Dayanak 1 f, g). "Tüm öğelerin arka plan renkleri" sözünün anlamı ve özgün sembolün rengi / dokusu: parça 2
  planının sorusudur; burada yalnız kayıt.
- S8. Bir istekte tek ızgara türü sürsün mü (bölüm 8).
- S9. Yazıların dikey aralığı (-1 .. +1 Rg) genişletilsin mi (B2 ve dikdörtgen şekiller için; bölüm 1.2, 12).
- S10. Sıra: öğe serbestliği / şekil genellemesi / Actions yolu (bölüm 12, 13.1).
- S11. `uret` ve ayar sürümü (bölüm 10): (a) eski OZET yalnız eski commit'le; (b) `ayar_surum` + eksik anahtarın
  tamamlanması (eşitlik kuralı değişir); (c) yeni anahtarlar yalnız varsayılan dışında yazılır.
- S12. Bütçe kuralı ön kontrol süresini saysın mı (bölüm 8): (a) aynen; (b) ölçüm koşusunun SURE kaydına "ön kontrol sn"
  alanı eklenir ve istek süresine katılır (onaylı girdi kuralı değişir; CM:217-219).

### 13.3 Teknik sorular (teknik öneriyle)

- T2. Kilit planıyla sıra: kilit kodu bu dilimlerden önce yazılırsa uyarlayıcıya yeni `arac` satırı eklenir (KP:680-685
  kalıbı). Teknik öneri: kilit `arac.commit`'e sabit kaldığı için sıra serbest.
- T3. Sembol yeri anahtarının tanım noktası: kaynak kutusunun merkezi (ölçümsüz, belirlenimci) / alfa > 0,5 kutusunun
  merkezi (ölçüme bağlı). Teknik öneri: kaynak kutusu.
- T5. Serbest kurulumun varsayılanda da kullanılması (tek yol) / yalnız varsayılan dışında (iki yol). Teknik öneri: iki
  yol + E2 ve E3 testleri; tek yola geçiş ancak E1 bayt eşitliği kanıtlanırsa. Olgu: iki yolda E1 yeni kurulum kodunu
  SINAMAZ (varsayılanda çalışmaz); onu E3 sınar.

## Ek: bu planın sınırları

- Kod okundu, çalıştırılan tek şey bölüm 7.4 ve 2.2'deki çizimsiz kontrol ölçümüdür (deneme sembolü; gerçek katman değil).
- Serbest kurulum fonksiyonu ve GK1 kapısı yazılmadı: "aynı sayılar" (E2, E3) ve "aynı bayt" (E1) iddiaları TEST HEDEFİDİR,
  ölçülmüş sonuç değildir.
- Ornament'e denk boy hesabı deneme sembolü alfasıyla ve YD'nin sürekli modeliyle yapıldı; ornament motorunun çizimle
  düzeltme adımı uygulanmadı.
- Başlangıç aralıkları yalnız yanlış girişi yakalamak içindir; hiçbir aralık ya da hesaplanan çarpan tasarım önerisi
  değildir.

## İnceleme kaydı

Bağımsız inceleme: işi yapmamış tek ajan, 2 tur (12 Kas 2026). Görevi: "bu plan neden yanlış, kanıtla".
- 1. tur: 7 YÜKSEK, 8 ORTA, 11 DÜŞÜK; yaklaşık 200 atıf açıldı. Hepsi düzeltildi (model ve mod için verilen iki öneri
  kaldırıldı; sembol bölümünün ölçeği üretimden okuduğu olgusu ve yeni kapıya taşınması gereken boy denetimi yazıldı; en
  uzak piksel ve K1 seçenekleri düzeltildi; isimsiz veride çökme olgusu; tuvale oranlanmayan piksel sabitleri; deneme
  katmanına bağlı sayıların etiketi).
- 2. tur: yeni YÜKSEK yok. Yeni 3 ORTA ve 6 DÜŞÜK (inceleyenin özeti 4 ve 5 dedi; listesinde 3 ve 6 vardı). Aşağıdaki
  tablo dışındakiler düzeltildi. 2. tur düzeltmeleri YENİDEN İNCELENMEDİ (tur sınırı).

| No | Önem | Bulgu | Durum |
|---|---|---|---|
| N9 | DÜŞÜK | Plan "en çok 600 satır" hedefini aşıyor. | Düzeltilmedi: fazlalık inceleme bulgularının düzeltmelerinden ve bu kayıttan geliyor. |
