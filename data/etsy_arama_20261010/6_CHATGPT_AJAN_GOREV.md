# ChatGPT AJANI GÖREV METNİ (koordinatör düzeltmesi, 10 Eki)

```
ARAÇ: ChatGPT agent (tarayıcı + Google Drive bağlı). OTURUM: etsy-arama.
Claude oturumu: https://claude.ai/code/session_01S8oeNuGz5F26LSAUgZCtZe
GÖREV: YALNIZ OKUMA. (1) 204 arama terimini iki kaynaktan oku. (2) 78 ilanın eRank Listing Audit puanını oku.
(3) 12 terimde Etsy arama sonuç sayfasını incele (kapak, sıra, rakip). Dosyaları teslim et. DUR.

KESİN KURALLAR
- Giriş (login), şifre, doğrulama (2FA, captcha, "robot değilim"), ödeme, abonelik, kart ekranı çıkarsa DUR, Serdar'a yaz.
  eRank PRO hesabını ve ödemesini Serdar açar; sen yalnız açık oturumda okursun.
- Etsy'de, eRank'te ve Drive'da hiçbir ayar değişmez. Hiçbir şey yayınlanmaz, düzenlenmez, silinmez, kimseye mesaj gitmez.
  eRank'te rakip takibine (competitor) ekleme yapılmaz, liste/etiket kaydedilmez.
- Drive'da yalnız aşağıdaki teslim dosyaları YENİ dosya olarak yazılır. Başka hiçbir dosya değiştirilmez, silinmez, taşınmaz.
- Listede olmayan terim sorgulanmaz (istisna: c1'deki MI "Similar terms" satırları). Bir terim bir kez sorgulanır.
- Rakam ekranda nasıl görünüyorsa öyle yazılır (1.2k, 77,5 bin). Tahmin, yuvarlama, yorum yok. Veri yoksa "yok".
- eRank tek başına kanıt değildir. Karar Marketplace insights (MI) verisine göre verilir.
- Rapor en çok 6 satır.

a) OKU
   Drive: ASTROLOVE/TEMP/ETSY_ARAMA_20261010/
   - 5_CAPRAZ_KONTROL.csv (204 terim, satır no "not" sütununun başında: S001-S204)
   - 2_ETSY_ARAMA_78_ONERI.csv (78 ilan; listing_id, cift)
   - KAPAK_ONIZLEME/ (bizim 3 örnek kapak, 340x270) ve KAPAK_ONIZLEME/KAPAK_KARSILASTIRMA_SABLON.md
   Dosya açılmazsa bu metindeki listelerle çalış (aşağıda TERİM LİSTESİ ve İLAN LİSTESİ).

b) HAZIRLIK
   5_CAPRAZ_KONTROL.csv'yi kopyala. Sütunlar değişmez:
   terim | MI arama/30g | MI rekabet | eRank hacim | eRank rekabet | fark oranı | not
   "fark oranı" BOŞ kalır (Claude hesaplar). "not"taki mevcut metni silme, sonuna "; " ile ekle. Satır sırası değişmez.

c) VERİ TOPLA: ÖNCE Marketplace insights, SONRA eRank, SONRA arama sayfası
   c1. Kaynak 1 (ANA): Etsy Shop Manager > Stats > Marketplace insights, son 30 gün. Öncelik sırası: G1, G2, G5, G3, G4.
       Her terim: arama sayısı -> "MI arama/30g"; rekabet / sonuç sayısı -> "MI rekabet".
       "not" sonuna: "MI üst: <o aramada üstteki ilk 3 ilanın mağaza adı>".
       SIMILAR TERMS: G1+G2+G5 içinde MI arama sayısı EN YÜKSEK 10 genel terim için (tek burç ve çift adı değil),
       MI "Similar terms" listesindeki ilk 5 terimi ARAMA SAYISIYLA birlikte CSV'nin SONUNA yeni satır olarak ekle:
       terim = benzer terim, MI arama/30g = sayısı, MI rekabet = görünüyorsa, not = "S2xx G6 benzer: <kaynak terim>".
       Satır no S205'ten devam eder. En çok 50 satır. eRank sütunları G6 için yalnız gün 2'de hak kalırsa doldurulur.
   c2. Kaynak 2 (yardımcı): eRank PRO Keyword Explorer (200 sorgu/gün). Her terim: hacim -> "eRank hacim";
       rekabet -> "eRank rekabet"; "not" sonuna "eRank trend: <ekranda yazdığı gibi>".
   c3. eRank PRO Listing Audit (200/gün): 78 ilan, İLAN LİSTESİ sırasıyla. Yeni dosya 7_ERANK_AUDIT.csv:
       listing_id | cift | eRank puan | eRank ilk 3 uyarı (ekrandaki metin)
   c4. KAPAK SORUSU (Etsy arama sonuç sayfası, MASAÜSTÜ görünüm, Etsy'ye giriş yapmadan gizli pencere; giriş isterse DUR).
       12 terim: zodiac couple print | personalized couple gift | zodiac wall art | anniversary gift couple |
       couple wall art | zodiac couple gift | cancer and leo | aquarius and libra | scorpio and taurus |
       libra gift | scorpio wall art | cancer zodiac gift
       Her terim için:
       - Sonuç sayfasının ilk 2 satırının ekran görüntüsü -> RAKIP_EKRAN/<NN>_<terim_alt_cizgili>.png (NN = 01-12).
       - Bizim mağaza (AstroLoveArt) ilk 3 sayfada var mı; varsa sayfa ve sıra (reklam mı, organik mi).
       - Üstteki ilk 8 ilan -> 8_RAKIP_KAPAK.csv, sütunlar:
         terim | sira (1-8) | reklam (Ad etiketi var/yok) | magaza | kapak turu (mockup/oda, duz poster, yakin plan, yazi karti)
         | fiyat (ekrandaki para birimiyle) | yildiz | yorum sayisi | bizim ilan (sayfa/sira ya da "ilk 3 sayfada yok") | ekran dosyasi
       - Ekranda görünen ülke ve para birimini ilk satırın notuna yaz.

   GÜN PLANI (eRank PRO: Keyword Explorer 200/gün, Listing Audit 200/gün)
   | Gün | MI | eRank Keyword Explorer | eRank Listing Audit | Arama sayfası |
   | 1 | S001-S204 (sıra G1, G2, G5, G3, G4) + G6 benzer satırları | S001-S200 (G1, G2, G5, G3 tamamı + G4'ün ilk 59'u) | 78 ilanın hepsi | 12 terim |
   | 2 | gün 1'de bitmeyen MI satırları | S201-S204 + G6 satırları (hak kalırsa) | - | - |
   eRank günlük hakkı erken biterse dur, kaldığın satır numarasını rapora yaz; ertesi gün oradan devam.
   G4 için eRank hakkı kalmazsa G4 yalnız MI ile bırakılır ("not": "eRank yok, hak bitti").

d) TESLİM ve DUR
   - Önce Drive ASTROLOVE/TEMP/ETSY_ARAMA_20261010/ klasörüne YENİ dosya olarak yaz:
     5_CAPRAZ_KONTROL_DOLU.csv, 7_ERANK_AUDIT.csv, 8_RAKIP_KAPAK.csv, RAKIP_EKRAN/ (12 PNG).
   - Yazamazsan 1 kez daha dene. Yine olmazsa dosyaları bu ChatGPT sohbetinde indirilebilir olarak ver.
   - Serdar'a en çok 6 satır: MI dolu terim sayısı, eRank dolu terim sayısı, audit ilan sayısı, 12 terimde bizim ilan
     kaç terimde ilk 3 sayfada, eksik satırlar, karşılaşılan engel.
   - DUR. Fark oranı ve "çelişkili" işaretini Claude hesaplar (eşik 2 kat; karar MI'ya göre).

TERİM LİSTESİ (satır no + terim)
[G1 mevcut 12 ortak etiket: S001-S012]
  S001 zodiac couple print | S002 astrology couple art | S003 zodiac wall art | S004 astrology wall art
  S005 personalized couple | S006 custom couple gift | S007 zodiac gift | S008 anniversary gift
  S009 engagement gift | S010 wedding gift couple | S011 newlywed gift | S012 giclee print
[G2 aday genel terim: S013-S028]
  S013 personalized couple gift | S014 wedding gift for couple | S015 zodiac poster | S016 zodiac print
  S017 zodiac couple art | S018 zodiac couple poster | S019 personalized zodiac couple | S020 zodiac couple gift
  S021 personalized wall art | S022 personalized couple wall art | S023 couple names print | S024 astrology gift
  S025 astrology lover gift | S026 framed zodiac print | S027 christmas gift for couple | S028 valentines gift couple
[G5 alici aramalari (E = etiket adayi, <=20 kr): S029-S065]
  S029 aries gift E | S030 aries wall art E | S031 taurus gift E | S032 taurus wall art E
  S033 gemini gift E | S034 gemini wall art E | S035 cancer zodiac gift E | S036 cancer zodiac art E
  S037 leo gift E | S038 leo wall art E | S039 virgo gift E | S040 virgo wall art E
  S041 libra gift E | S042 libra wall art E | S043 scorpio gift E | S044 scorpio wall art E
  S045 sagittarius gift E | S046 sagittarius wall art E | S047 capricorn gift E | S048 capricorn wall art E
  S049 aquarius gift E | S050 aquarius wall art E | S051 pisces gift E | S052 pisces wall art E
  S053 personalized anniversary gift | S054 paper anniversary gift | S055 1st anniversary gift E | S056 gift for boyfriend E
  S057 gift for girlfriend E | S058 gift for husband E | S059 gift for wife E | S060 couple wall art E
  S061 bedroom wall art couple | S062 star sign print E | S063 zodiac sign art E | S064 custom couple poster E
  S065 zodiac compatibility gift
[G3 mevcut cift adi etiketi: S066-S141]
  S066 aquarius aquarius | S067 aquarius and aries | S068 aquarius and cancer | S069 aquarius capricorn
  S070 aquarius and gemini | S071 aquarius and leo | S072 aquarius and libra | S073 aquarius and pisces
  S074 aquarius sagittarius | S075 aquarius and scorpio | S076 aquarius and taurus | S077 aquarius and virgo
  S078 aries and aries | S079 aries and cancer | S080 aries and capricorn | S081 aries and gemini
  S082 aries and leo | S083 aries and libra | S084 aries and pisces | S085 aries sagittarius
  S086 aries and scorpio | S087 aries and taurus | S088 aries and virgo | S089 cancer and cancer
  S090 cancer and capricorn | S091 cancer and gemini | S092 cancer and leo | S093 cancer and libra
  S094 cancer and pisces | S095 cancer sagittarius | S096 cancer and scorpio | S097 cancer and taurus
  S098 cancer and virgo | S099 capricorn capricorn | S100 capricorn and gemini | S101 capricorn and leo
  S102 capricorn and libra | S103 capricorn and pisces | S104 capricorn scorpio | S105 capricorn and taurus
  S106 capricorn and virgo | S107 gemini and gemini | S108 gemini and leo | S109 gemini and libra
  S110 gemini and pisces | S111 gemini sagittarius | S112 gemini and scorpio | S113 gemini and taurus
  S114 gemini and virgo | S115 leo and leo | S116 leo and libra | S117 leo and pisces
  S118 leo and sagittarius | S119 leo and scorpio | S120 leo and taurus | S121 leo and virgo
  S122 libra and libra | S123 libra and pisces | S124 libra sagittarius | S125 libra and scorpio
  S126 libra and taurus | S127 libra and virgo | S128 pisces and pisces | S129 pisces sagittarius
  S130 pisces and scorpio | S131 pisces and taurus | S132 pisces and virgo | S133 sagittarius scorpio
  S134 sagittarius taurus | S135 sagittarius virgo | S136 scorpio and scorpio | S137 scorpio and taurus
  S138 scorpio and virgo | S139 taurus and taurus | S140 taurus and virgo | S141 virgo and virgo
[G4 faz 2 aday cift etiketi: S142-S204]
  S142 aquarius aries print | S143 aquarius cancer art | S144 aquarius gemini art | S145 aquarius leo print
  S146 aquarius libra print | S147 aquarius pisces art | S148 aquarius scorpio art | S149 aquarius taurus art
  S150 aquarius virgo print | S151 aries aries print | S152 aries cancer print | S153 aries capricorn art
  S154 aries gemini print | S155 aries and leo print | S156 aries libra print | S157 aries pisces print
  S158 aries scorpio print | S159 aries taurus print | S160 aries virgo print | S161 cancer cancer print
  S162 cancer capricorn art | S163 cancer gemini print | S164 cancer and leo print | S165 cancer libra print
  S166 cancer pisces print | S167 cancer scorpio print | S168 cancer taurus print | S169 cancer virgo print
  S170 capricorn gemini art | S171 capricorn leo print | S172 capricorn libra art | S173 capricorn pisces art
  S174 capricorn taurus art | S175 capricorn virgo art | S176 gemini gemini print | S177 gemini and leo print
  S178 gemini libra print | S179 gemini pisces print | S180 gemini scorpio print | S181 gemini taurus print
  S182 gemini virgo print | S183 leo and leo print | S184 leo and libra print | S185 leo and pisces print
  S186 leo sagittarius art | S187 leo scorpio print | S188 leo and taurus print | S189 leo and virgo print
  S190 libra libra print | S191 libra pisces print | S192 libra scorpio print | S193 libra taurus print
  S194 libra virgo print | S195 pisces pisces print | S196 pisces scorpio print | S197 pisces taurus print
  S198 pisces virgo print | S199 scorpio scorpio art | S200 scorpio taurus print | S201 scorpio virgo print
  S202 taurus taurus print | S203 taurus virgo print | S204 virgo virgo print

İLAN LİSTESİ (sıra, listing_id, çift)
  01 4570110121 AQUARIUS_AQUARIUS | 02 4570110641 AQUARIUS_ARIES | 03 4570125580 AQUARIUS_CANCER | 04 4570126104 AQUARIUS_CAPRICORN
  05 4570112095 AQUARIUS_GEMINI | 06 4570127160 AQUARIUS_LEO | 07 4570113157 AQUARIUS_LIBRA | 08 4570113675 AQUARIUS_PISCES
  09 4570128546 AQUARIUS_SAGITTARIUS | 10 4570114301 AQUARIUS_SCORPIO | 11 4570150148 AQUARIUS_TAURUS | 12 4570136319 AQUARIUS_VIRGO
  13 4570151370 ARIES_ARIES | 14 4570151950 ARIES_CANCER | 15 4570152410 ARIES_CAPRICORN | 16 4570152820 ARIES_GEMINI
  17 4570031205 ARIES_LEO | 18 4570153208 ARIES_LIBRA | 19 4570138967 ARIES_PISCES | 20 4570154042 ARIES_SAGITTARIUS
  21 4570139913 ARIES_SCORPIO | 22 4570140539 ARIES_TAURUS | 23 4570155846 ARIES_VIRGO | 24 4570141945 CANCER_CANCER
  25 4570157258 CANCER_CAPRICORN | 26 4570157716 CANCER_GEMINI | 27 4570143387 CANCER_LEO | 28 4570143815 CANCER_LIBRA
  29 4570144239 CANCER_PISCES | 30 4570144663 CANCER_SAGITTARIUS | 31 4570145103 CANCER_SCORPIO | 32 4570160260 CANCER_TAURUS
  33 4570160676 CANCER_VIRGO | 34 4570161266 CAPRICORN_CAPRICORN | 35 4570147149 CAPRICORN_GEMINI | 36 4570162562 CAPRICORN_LEO
  37 4570163164 CAPRICORN_LIBRA | 38 4570148769 CAPRICORN_PISCES | 39 4570163968 CAPRICORN_SAGITTARIUS | 40 4570149603 CAPRICORN_SCORPIO
  41 4570164962 CAPRICORN_TAURUS | 42 4570165628 CAPRICORN_VIRGO | 43 4570166282 GEMINI_GEMINI | 44 4570152121 GEMINI_LEO
  45 4570152561 GEMINI_LIBRA | 46 4570153015 GEMINI_PISCES | 47 4570153495 GEMINI_SAGITTARIUS | 48 4570154049 GEMINI_SCORPIO
  49 4570169354 GEMINI_TAURUS | 50 4570155327 GEMINI_VIRGO | 51 4570155945 LEO_LEO | 52 4570198669 LEO_LIBRA
  53 4570199091 LEO_PISCES | 54 4570199509 LEO_SAGITTARIUS | 55 4570214304 LEO_SCORPIO | 56 4570214784 LEO_TAURUS
  57 4570200893 LEO_VIRGO | 58 4570201313 LIBRA_LIBRA | 59 4570216030 LIBRA_PISCES | 60 4570202333 LIBRA_SAGITTARIUS
  61 4570202793 LIBRA_SCORPIO | 62 4570203229 LIBRA_TAURUS | 63 4570203731 LIBRA_VIRGO | 64 4570204167 PISCES_PISCES
  65 4570204681 PISCES_SAGITTARIUS | 66 4570205473 PISCES_SCORPIO | 67 4570205899 PISCES_TAURUS | 68 4570220634 PISCES_VIRGO
  69 4570206865 SAGITTARIUS_SAGITTARIUS | 70 4570221662 SAGITTARIUS_SCORPIO | 71 4570207855 SAGITTARIUS_TAURUS | 72 4570208321 SAGITTARIUS_VIRGO
  73 4570209015 SCORPIO_SCORPIO | 74 4570224058 SCORPIO_TAURUS | 75 4570210411 SCORPIO_VIRGO | 76 4570225672 TAURUS_TAURUS
  77 4570226386 TAURUS_VIRGO | 78 4570227104 VIRGO_VIRGO
```
