# GÖZ RAPORU: kontrol-75 (bağımsız görsel kontrol)

Tarih: 3 Eki 2026. Kaynak: `kontrol-75` dalı, `kontrol/*.jpg` (75 adet, her biri 1600x1048; sol panel orijinal, sağ panel motor; panel 800x1000).
Üreten oturumun raporları kullanılmadı. Kod değişikliği ve üretim yok.

## Özet

- 75/75 dosya tek tek açılıp gözle karşılaştırıldı; ardından sol−sağ piksel farkıyla ikinci tur yapıldı.
- **75/75 ŞÜPHELİ**, hepsinde ortak bulgu **Z1** var (aşağıda). Z1 dışında poster-özgü görünür bulgu: **3**
  (CANCER_LIBRA görünür; CANCER_LEO ve LEO_LIBRA yakın yıldız).
- Kalan 72 posterde Z1 dışında kusur bulunmadı: ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu.

## Z1: tagline bandında yıldız deseni orijinalden farklı (75/75)

Ölçümle bulundu; 800 px'lik panelde gözle ancak yakından görülüyor. Koordinatlar panel içi (x,y):

| konum | orijinal | motor |
|---|---|---|
| (107,873) | yıldız var (126) | **yok** (3) |
| (710,873) | yıldız var (94) | **yok** (3) |
| (772,853) | yok (4) | **yeni yıldız** (102) |
| (648,859) | yok (4) | **yeni yıldız** (52) |
| (622,886) | yok (5) | **yeni yıldız** (95) |

- 75 posterin hepsinde aynı 5 noktada aynı fark var. Bant dışındaki zemin piksel düzeyinde aynı (fark 0).
  Dikiş, çizgi, bant ya da leke izi yok. Yalnız yıldızlar değişmiş.
- Anlamı: motorun kullandığı zemin plakası tagline satırında orijinal kompozitten farklı. Kasıtlı mı bilinmiyor, bu yüzden ŞÜPHELİ.
- Etkisi: (622,886)'daki yeni yıldız tagline'ın sağ ucuna denk geliyor. Uzun tagline'larda yazıya değiyor ya da çok yaklaşıyor
  (CANCER_LIBRA, CANCER_LEO, LEO_LIBRA).

## Kontrol edilenler ve ölçülen değerler (75/75)

| kontrol | sonuç |
|---|---|
| Ana sembol yeri | en iyi hizalamada kayma 0 px (±4 px tarandı); ağırlık merkezi farkı ≤1,6 px |
| Ana sembol şekil/boyut | altın maske IoU 0,93–0,99 (fark yalnız kenarlarda, yeniden örnekleme) |
| Ana sembol rengi | parlaklık farkı −0,1 ile −2,6 (0–255 ölçeğinde); koyulaşma yok. Doygunluk farkı ≤3,2 |
| Çember | üst tepe y=121 her iki panelde (PISCES_SCORPIO'da orijinal 120 / motor 121) |
| Küçük burç sembolleri | doğru burç, doğru sıra (sol = adın ilk burcu); şekil IoU 0,79–0,99; her biri altındaki ismin üstünde ortalı (fark ≤4 px; LIBRA_VIRGO −8 px, J harfinin sola taşmasından) |
| Burç adları | motor panelinde burç adları yerine kişi isimleri basılıyor (tasarım); küçük semboller burcu gösteriyor |
| İsimler | gözle 150/150 isim okundu; eksik ya da bozuk harf görülmedi. İsim satırı ortası panel ortasından ±2 px |
| Tagline | gözle 75/75 okundu; eksik ya da bozuk harf görülmedi. Merkez x=399–402 (panel ortası 400) |
| Eski yazı kalıntısı (hayalet) | orijinal yazının silindiği yerlerde motor pikseli en çok 26, ortalama 6–10 (zemin 5–7); kalıntı yok |
| Çift yazı | yok |
| Zemin (bant/çizgi/leke) | Z1 dışında yok (metin ve sembol dışı zeminde >8 farkı olan piksel: posterde 14, hepsi tagline satırındaki sönük yıldızlar) |

## Sınırlar

- Kontrol JPG önizlemeleri üzerinde yapıldı (panel 800 px). Baskı çözünürlüğündeki ince kusurlar burada görünmeyebilir.
- Harf doğruluğu yalnız gözle kontrol edildi (OCR yok).
- 78 çiftten 3'ü dosyada yok, kontrol edilmedi: AQUARIUS_LEO, AQUARIUS_TAURUS, LIBRA_LIBRA.

## Tablo (75 satır)

| # | çift | motor: isimler / tagline | durum | not (ne ve nerede) |
|---|---|---|---|---|
| 1 | AQUARIUS_AQUARIUS | OLIVIA ∞ NOAH / "Two Hearts, One Home" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 2 | AQUARIUS_ARIES | LIAM ∞ SOPHIA / "Our Favorite Adventure" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 3 | AQUARIUS_CANCER | AVA ∞ ETHAN / "Since the Day We Met" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 4 | AQUARIUS_CAPRICORN | MASON ∞ CHLOE / "You Are My Calm" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 5 | AQUARIUS_GEMINI | GRACE ∞ LUCAS / "Always and Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 6 | AQUARIUS_LIBRA | LILY ∞ OWEN / "My Best Decision" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 7 | AQUARIUS_PISCES | JACK ∞ HANNAH / "Still Choosing You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 8 | AQUARIUS_SAGITTARIUS | NORA ∞ BEN / "Still You, Every Day" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 9 | AQUARIUS_SCORPIO | SAM ∞ ZOE / "Better Together" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 10 | AQUARIUS_VIRGO | DANIEL ∞ MAYA / "You and Me, Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 11 | ARIES_ARIES | RUBY ∞ THEO / "The Start of Everything" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 12 | ARIES_CANCER | ADAM ∞ CLARA / "My Person" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 13 | ARIES_CAPRICORN | EVA ∞ MILES / "Hand in Hand" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 14 | ARIES_GEMINI | JULIAN ∞ ROSE / "Where Our Story Began" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 15 | ARIES_LEO | ALICE ∞ FINN / "Love at First Laugh" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 16 | ARIES_LIBRA | OSCAR ∞ LUNA / "Forever Starts Today" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 17 | ARIES_PISCES | MIA ∞ JONAH / "You Make It Home" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 18 | ARIES_SAGITTARIUS | ELI ∞ STELLA / "Side by Side" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 19 | ARIES_SCORPIO | IVY ∞ CALEB / "My Favorite Hello" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 20 | ARIES_TAURUS | LEVI ∞ NAOMI / "Only Ever You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 21 | ARIES_VIRGO | AMELIA ∞ RYAN / "Our Happily Ever After" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 22 | CANCER_CANCER | ARIA ∞ DYLAN / "Yours, Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 23 | CANCER_CAPRICORN | NATHAN ∞ LUCY / "Two Paths, One Way" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 24 | CANCER_GEMINI | VIOLET ∞ ADRIAN / "Meant to Be" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 25 | CANCER_LEO | PAUL ∞ HAZEL / "A Love Worth Waiting For" | ŞÜPHELİ | **Z1 + YAKIN:** yeni yıldız (panel x622,y886) tagline sonundan (~x588) ~34 px sağda, taban çizgisi hizasında; nokta gibi okunabilir |
| 26 | CANCER_LIBRA | EMILY ∞ JAMES / "It Began With a Kiss in the Rain" | ŞÜPHELİ | **Z1 + GÖRÜNÜR:** yeni yıldız (panel x623,y887) tagline sonundaki "Rain" kelimesinin "n" harfinin dibine yapışık; nokta/leke gibi okunuyor |
| 27 | CANCER_PISCES | MARCUS ∞ JADE / "With You, Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 28 | CANCER_SAGITTARIUS | ELENA ∞ LOGAN / "Our Forever Song" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 29 | CANCER_SCORPIO | CARTER ∞ SIENNA / "The Best Is Ahead of Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 30 | CANCER_TAURUS | FREYA ∞ SIMON / "Love Found Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 31 | CANCER_VIRGO | AARON ∞ BELLA / "Together Is My Favorite" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 32 | CAPRICORN_CAPRICORN | CORA ∞ MICAH / "Every Moment With You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 33 | CAPRICORN_GEMINI | ROWAN ∞ ELISE / "Two of a Kind" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 34 | CAPRICORN_LEO | SARAH ∞ TYLER / "My Heart Is Yours" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 35 | CAPRICORN_LIBRA | DEAN ∞ FIONA / "Our Story, Our Way" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 36 | CAPRICORN_PISCES | PIPER ∞ COLE / "Still My Favorite" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 37 | CAPRICORN_SAGITTARIUS | GAVIN ∞ AUDREY / "Love You More" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 38 | CAPRICORN_SCORPIO | ANNA ∞ LUKE / "The Two of Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 39 | CAPRICORN_TAURUS | REID ∞ MAISIE / "Our Kind of Magic" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 40 | CAPRICORN_VIRGO | ESME ∞ CHASE / "Always My Home" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 41 | GEMINI_GEMINI | ALEX ∞ JUNE / "Love, Laughter, Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 42 | GEMINI_LEO | NINA ∞ MAX / "A Little Love Story" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 43 | GEMINI_LIBRA | BLAKE ∞ CLAIRE / "You Light Up My Days" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 44 | GEMINI_PISCES | JULIA ∞ TOBY / "Forever and a Day" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 45 | GEMINI_SAGITTARIUS | KAI ∞ LEAH / "From Hello to Forever" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 46 | GEMINI_SCORPIO | SADIE ∞ ROMAN / "Our Beautiful Mess" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 47 | GEMINI_TAURUS | ELLIOT ∞ GEMMA / "My Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 48 | GEMINI_VIRGO | TESSA ∞ HUGO / "Hearts in Harmony" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 49 | LEO_LEO | GRANT ∞ MOLLY / "To Us, Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 50 | LEO_LIBRA | POPPY ∞ WYATT / "Different Signs, One Heart" | ŞÜPHELİ | **Z1 + YAKIN:** yeni yıldız (panel x622,y886) tagline sonundan (~x585) ~37 px sağda, taban çizgisi hizasında; nokta gibi okunabilir |
| 51 | LEO_PISCES | SETH ∞ IRIS / "Where You Go, I Go" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 52 | LEO_SAGITTARIUS | MAEVE ∞ JASPER / "Partners in Everything" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 53 | LEO_SCORPIO | CONNOR ∞ EDEN / "Our Greatest Adventure" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 54 | LEO_TAURUS | LAILA ∞ BRODY / "Love Grows Here" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 55 | LEO_VIRGO | FELIX ∞ AMBER / "Two Souls, One Story" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 56 | LIBRA_PISCES | QUINN ∞ PETER / "My Forever Favorite" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 57 | LIBRA_SAGITTARIUS | HOLLY ∞ SEAN / "Simply Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 58 | LIBRA_SCORPIO | BRYCE ∞ KATE / "Coffee, Rain and You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 59 | LIBRA_TAURUS | VERA ∞ IAN / "Every Step Together" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 60 | LIBRA_VIRGO | JESSE ∞ PAIGE / "Here's to Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 61 | PISCES_PISCES | DAISY ∞ WESLEY / "I Choose You, Always" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 62 | PISCES_SAGITTARIUS | CAMILA ∞ DREW / "The Love of My Life" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 63 | PISCES_SCORPIO | ANDRE ∞ LYDIA / "Brave Together" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 64 | PISCES_TAURUS | SKYE ∞ MARTIN / "Our Quiet Forever" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 65 | PISCES_VIRGO | NOEL ∞ HARPER / "Love in Every Season" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 66 | SAGITTARIUS_SAGITTARIUS | WILLOW ∞ EVAN / "Sweet Little Forever" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 67 | SAGITTARIUS_SCORPIO | LANCE ∞ NATALIE / "You Feel Like Home" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 68 | SAGITTARIUS_TAURUS | BRIANNA ∞ COLIN / "It Was Always You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 69 | SAGITTARIUS_VIRGO | SHANE ∞ OLIVE / "Two Hearts in Tune" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 70 | SCORPIO_SCORPIO | MEGAN ∞ RHYS / "Our Love, Our Rules" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 71 | SCORPIO_TAURUS | GRETA ∞ ARCHIE / "Made for Each Other" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 72 | SCORPIO_VIRGO | VICTOR ∞ ELLIE / "My Safe Place" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 73 | TAURUS_TAURUS | SELENA ∞ JORDAN / "Still Falling for You" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 74 | TAURUS_VIRGO | KATIE ∞ FRANK / "One Life, Together" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
| 75 | VIRGO_VIRGO | MATTEO ∞ ROSALIE / "Written by Us" | ŞÜPHELİ | Z1 (aşağıda). Bunun dışında ana sembol, küçük semboller, isimler, tagline ve zemin orijinalle uyumlu |
