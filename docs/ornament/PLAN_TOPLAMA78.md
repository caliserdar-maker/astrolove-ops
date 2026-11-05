# Ornament 78 cift toplama plani (5 Kas 2026; Serdar "devam", "Basla" ile plan ve kod; kosu ayri onay)

Dayanak: PLAN67 7. madde; KARARLAR_20261104_2 (5 Kas: asama 2 onayi 10 cift, GEMINI_VIRGO istisnasi; yd67 A/B/C, GG + PP istisnasi, GS goz onayi).
Inceleme: 1 tur, 12 bulgu (4 ORTA, 8 DUSUK); 1-11 bu metne ve koda islendi, 12 bilgi (asagida).

## On kosul (kosudan once)
- yd67 eksik 9 cift (SAGITTARIUS_SAGITTARIUS, SAGITTARIUS_SCORPIO, SAGITTARIUS_TAURUS, SAGITTARIUS_VIRGO, SCORPIO_SCORPIO, SCORPIO_TAURUS, SCORPIO_VIRGO,
  TAURUS_VIRGO, VIRGO_VIRGO) Merkez kontrolu yapildi (5 Kas aksam; sembol orani secime gore 0,95-0,98, rapor ile fark <= 3 px, Merkez olcumu;
  gorsel EKSIK9_5STIL.jpg Serdar'a gonderildi). Serdar gorsel onayi kosu onayiyla birlikte alinir ve karar dosyasina yazilir.

## Kapsam
- Kaynak 1: Drive TEMP/ORNAMENT_78YENI_DUZEN_20261105_0930_42001867106 (kosu 42001867106): 10 cift kokte, GEMINI_VIRGO FAIL/GEMINI_VIRGO/.
- Kaynak 2: Drive TEMP/ORNAMENT_78URETIM_YD67_20261105_1629_42063472397 (kosu 42063472397): 64 cift kokte, GG / GS / PP FAIL/<CIFT>/.
- CANCER_LIBRA, AQUARIUS_PISCES ve GEMINI_VIRGO yeni duzen dosyalarindan (kaynak 1). Eski 5STIL (6daab364) ve ONAYLI_KOVA_GV klasoru (kosu 41839101824) GIRMEZ.
- Hedef: Drive TEMP/ORNAMENT_78_TOPLAMA_<damga>_<kosu>: 78 x 5 = 390 dosya kokte (<CIFT>_<STIL>_954.png) + RAPOR/ (DURUM_PASS.txt ya da DURUM_FAIL.txt).
- Yalniz sunucu tarafi KOPYA (rclone copy --files-from --no-traverse --immutable). Kaynakta silme / tasima / yazma yok. Etsy / Printful API yok.

## Kapilar (scripts/printful/toplama78.py; 10 beklenti, hepsi PASS olmali)
1. manifest_78x5: kaynak BIRLESIK yukleme kayitlarindan 390 dosya, 78 cift = CIFT78, cift basina 5 stil, 390 tekil ad ve 390 tekil sha256.
2. kaynak_rapor_kume: kaynak 1 = YD11, kaynak 2 = 78 - YD11; cift iki kaynakta yok; dosya yolu kok (PASS) ya da FAIL/<CIFT>/ (FAIL);
   BIRLESIK drive.gecti, kontrol_hepsi, her yukleme.ok True; eksik parca / cokus yok.
3. istisna_kayitli: ISTISNA78.json = toplama78.ISTISNA_ONAYLI (cift, kapi, onay tarihi, kosu, dE00 azami); her FAIL ciftinin dusen kapilari tam olarak
   [koyu_dE00_son_ham_le_2], eksik / cokus yok; koyu 3 stil dE00_ham_maks <= azami (karardaki ust deger + 0,005: GV 2,355, GG 2,205, PP 2,085,
   GS 3,405); istisnasiz FAIL yok; kullanilmayan istisna yok.
   SINIR: dosya ve kod ayni depoda; ikisinin ayni commit'te birlikte genisletilmesini bu kapi YAKALAMAZ (inceleme ve Serdar onayina kalir).
4. kaynak_beklenen: kaynak BEKLENEN_SONUC'ta 15 beklenti adi tam; yalniz birlesik_gecti dusebilir, nedeni yalniz istisna ciftleri.
5. kaynak_drive: kopyadan ONCE kaynak lsjson (--hash) sha256 = manifest, her yol bir kez. FAIL ise kopya yok.
6. hedef_drive: hedef kokte tam 390 dosya; ad ve sha256 = manifest; md5 = kaynak lsjson md5; RAPOR/ disinda fazla dosya yok.
   sha256 / md5 bos gelirse (Drive gecikmesi) 60 sn arayla en cok 2 yeniden liste; fark / eksik / fazla varsa yeniden deneme yok.
7. sunucu_kopya: rclone -v logunda her dosya icin tam bir "Copied (server-side copy)"; "Copied (new)" (indir-yukle) yok.
8. printful_dosya: hedef indirilir; uretim78.printful_dosya 390/390 (954x954; RGB, SADE_ALTIN RGBA; 300 dpi; ICC yok ya da sRGB;
   PRINTFUL_ORNAMENT.md 900 Circle, varyant 23133).
9. yerel_sha: indirilen dosya sha256 = manifest; eksik / fazla yok.
10. kaynak_degismedi: kaynak ozeti (yol, boyut, sha256) once = sonra.
- Istisna gorunurlugu: SONUC.txt, log ve TOPLAMA_SONUC.json'da 4 satir "ISTISNA ile kabul (kapi FAIL): <cift> | kapi ... FAIL | dE00 aralik |
  onay | kosu"; MANIFEST_csv.txt kapi_durumu sutunu (20 satir "FAIL (istisna ile kabul)").

## Kosu (ornament-78-toplama.yml; tetik docs/ornament/TOPLAMA78_TETIK.txt)
- Sira: paketler (Pillow 11.0.0, numpy 2.5.4) -> mantik testi -> siparis kontrolu (etkin siparis varsa DUR) -> manifest -> rclone ->
  kaynak once -> hedef klasor -> kopya (14 grup, grup <= 40 dosya, ETA) -> sunucu kopya kaniti -> hedef -> printful -> kaynak sonra -> sonuc ->
  rapor Drive RAPOR/ (3 deneme dusenler FAIL) -> dal.
- Dala yalniz JSON / TXT (MANIFEST.json, SHA256SUMS.txt, MANIFEST_csv.txt, B_*.json, KAYNAK_ONCE/SONRA.json, loglar, DURUM); dal_kapisi +
  Drive ID kontrolu (lsjson kimlikleri raporda yok, "ID" alani yok, okunamayan lsjson FAIL). rclone stderr dosyaya (public loga degil).
- Boyut: kaynak 1'de 954 PNG ortalamasi 0,679 MB (55 dosya, ONAYLI_YD11_ONCE.json, bizim veri); 390 dosya ~265 MB indirme (tahmin). Sure olculmedi.
- Tek kosu; FAIL'de otomatik ikinci kosu yok. Siparis kontrolu yalniz kosu basinda (kosu sirasinda gelen siparisi gormez; bilgi).

## Yerel test (5 Kas, Merkez)
- toplama78_mantik_testi.py: 64 vaka (bilinen PASS + bilinen FAIL), Pillow 11.0.0 ve 12.3.0, cikis 0.
- Sahte rclone ile yml adimlari (Paketler, Mantik testi, Siparis, rclone kur ve Dal ATLANDI; Dal'in Drive ID kontrolu ayrica denendi):
  iyi 10/10 PASS, 390 dosya; bozuk kaynak kopya ONCESI durdu, hedef 0 dosya; sha gecikmesi 1 yeniden liste ile PASS.
- Sahte rclone gercek Drive davranisini kanitlamaz: sunucu tarafi kopya log metni ve kopyada sha256 dolumu ilk gercek kosuda olculur (kapi 6 ve 7).
- git add --sparse, dal_kapisi + push adimi bu is akisinda yerelde kosmadi (ornament-78-uretim.yml'deki ayni desen 3 kosuda calisti).

## Bilgi
- uretim78.py ve ornament-78-uretim.yml'de dalda Drive klasor ID'leri var (onceki isler; URETIM78_CIFTLER.json onayli alani, yml env). Bu is yeni ID eklemez.
- uretim78.py:30 ONAYLI sabiti eski ("onayli dosyalari kullanilir"); yeni duzende CL / AP / GV yeniden uretildi (KARARLAR_20261104_2). Bu iste kullanilmaz.
