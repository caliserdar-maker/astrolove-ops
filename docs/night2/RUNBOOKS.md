# ONCELIK 9 - Canli islem runbook'lari

Ortak kural: her runbook once DRY-RUN ile kosar, ciktisi Drive'a yazilir, Serdar
sohbette onay verir, ancak ondan sonra canli adim calisir. Etsy yazan her kosu
`concurrency: etsy-token` grubunda tek basina calisir. Kota tabani altinda hicbir
yazma baslamaz. Uzun tire (em/en dash) hicbir metinde kullanilmaz.

---

## R1 - GPSR panel girisi - TAMAMLANDI

Bu runbook tarihsel kayittir; acik is degildir.

- Tamamlanma: **8 Eyl 2026**
- Kapsam: **78/78 POD ilani**, Etsy panelinden elle
- Kanit: `docs/start_here/B99.txt`
- Kanonik durum: `config/operational_state.json` (`gpsr_pod_78=completed`)
- Etsy API ve bulk edit GPSR alanini gostermedigi icin API taramasinda alanin
  gorunmemesi eksik giris kaniti sayilamaz.
- Bu is yeniden onerilmez veya calistirilmaz. Ancak kullanici belirli bir ilanda
  eksik alan bildirdiginde yeni ve ayri bir duzeltme isi acilir.

---

## R2 - Duplicate arsivleme (Drive)

**On kosullar**
- `duplicate_candidates.csv` (MD5 esitligiyle dogrulanmis gercek kopyalar).
- Hedef arsiv klasoru: `ASTROLOVE/ARCHIVE/DUPLICATES_<UTC>/` (YENI klasor).

**Gerekli onay:** Serdar; silme DEGIL tasima onayi.

**Dry-run:** `rclone move --dry-run` ile tasinacak dosya listesi ve bosalacak alan
raporlanir. Her kopya grubunda EN ESKI yol birincil sayilir, digerleri aday olur.

**Geri alma:** Arsiv klasorunden `rclone move` ile geri tasima (dosyalar silinmedigi
icin kayipsiz).

**Durma kosulu:** Bir grupta birincil dosya bir ilan tarafindan kullaniliyorsa
(matriste ana_zip/video olarak gecerse) o grup ATLANIR. Toplam tasinacak alan
beklenenin %20'sinden fazla saparsa DUR.

**Canli adim:** Onaylanan gruplar icin `rclone move <kaynak> <arsiv>` (silme yok).

---

## R3 - Etsy Ads CSV importu

**On kosullar**
- Shop Manager > Marketing > Etsy Ads > disa aktarim CSV'si
  `ASTROLOVE/TEMP/ADS/etsy_ads_stats_<tarih>.csv` yoluna konmus olmali.
- Kolonlar `etsy_ads_column_dictionary.csv` ile uyusmali.

**Gerekli onay:** gerekmez (salt okur analiz), ancak butce/teklif degisikligi
icin ayri onay sarttir.

**Dry-run:** `ads_kpi.py --csv <dosya> --out <klasor>`; kolon eksikse betik DURUR
ve hangi kolonun eksik oldugunu yazar. Veri uydurulmaz.

**Geri alma:** Yok (yalniz okuma ve hesaplama).

**Durma kosulu:** CSV bos, kolon eksik ya da listing_id'ler katalogla eslesmiyorsa DUR.

**Canli adim:** Yok. Cikti KEEP/WATCH/REDUCE/REVIEW karar tablosudur; butce
degisikligi Serdar'in panelden yapacagi ayri bir istir.

---

## R4 - Metricool icerik aktarimi

**On kosullar**
- `platform_content_dataset.csv` (546 satir) ve ilgili medya dosyalari.
- Metricool hesabinda ilgili platformlar bagli.

**Gerekli onay:** Serdar; hangi platform, hangi tarih araligi, kac gonderi.

**Dry-run:** Once 7 satir (her platformdan 1) secilir, Metricool'e TASLAK olarak
girilir, yayin zamani ayarlanmaz. Gorsel oranlari ve karakter sinirlari kontrol edilir.

**Geri alma:** Taslaklar Metricool'den silinir (yayinlanmadigi icin iz kalmaz).

**Durma kosulu:** Bir platformda karakter siniri asiliyorsa ya da medya orani
uyusmuyorsa o platform ATLANIR, digerleri surer.

**Canli adim:** Onaylanan satirlar toplu olarak Metricool takvimine planlanir.
Bu batch'te HICBIR planlama yapilmadi.

---

## R5 - Sosyal platform yayinlama

**On kosullar:** R4 tamamlanmis, taslaklar onaylanmis olmali.

**Gerekli onay:** Serdar'in ilk 3 gonderi icin tek tek onayi; sonrasi haftalik onay.

**Dry-run:** Ilk gonderi "yalniz ben" gorunurlugu ile yayinlanir, gorsel/metin
kontrol edilir, sonra herkese acilir.

**Geri alma:** Gonderi silinir. Marka hesaplarinda silinen gonderi iz birakabilir;
bu yuzden ilk kontrol sart.

**Durma kosulu:** Platform reklam/telif uyarisi verirse ya da yorumlarda urun
yanlis anlasilirsa DUR.

**Canli adim:** Planlanan takvime gore yayin. Bu batch'te yayin YAPILMADI.

---

## R6 - Yeni listing olusturma

**On kosullar**
- Urun dosyalari Drive'da tam (matriste eksik_ogeler = "-").
- SEO v2 sablonu, 13 etiket kurali, edisyon adlari, fiyat ve kargo profili hazir.
- Kota: ilan basina ~15 cagri + medya yuklemeleri.

**Gerekli onay:** Serdar; kac ilan, hangi cift/aile/edisyon.

**Dry-run:** `pod_listing_create.py` benzeri akisla TASLAK (state=draft) tek ilan
olusturulur ve tum alanlar geri okunur. DIKKAT: `updateListing` bir taslagi
otomatik YAYINA alir (7 Eyl 2026 olcumu); taslak kalmasi gerekiyorsa guncelleme
cagrisi yapilmaz.

**Geri alma:** Ilan `state=inactive` yapilir ya da silinir (yeni olusturuldugu icin
veri kaybi olmaz).

**Durma kosulu:** Ilk ilanda geri okuma birebir degilse, medya eksikse ya da kota
tabani asiliyorsa DUR.

**Canli adim:** Onaylanan ilanlar tek tek olusturulur, her ilandan sonra geri okuma
yapilir, 5 ilanda bir ara verilir.
