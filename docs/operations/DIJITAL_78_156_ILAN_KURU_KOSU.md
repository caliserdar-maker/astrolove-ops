# 156 ilan donusumu - KURU KOSU plani (GOREV_0010 md.5)

26 Eyl 2026. **Etsy'ye YAZMA YOK.** Bu dosya plan + eksik listesidir; sayilar
Etsy salt-okuma turu yapilmadan DOLDURULAMAZ (asagida "gerekli veri").

## Kapsam

- 78 dijital ilan + 78 wallpaper ilani = **156 ilan**, made-to-order'a donusecek.
- Her cift icin bugun 4 edisyon x (dijital / wallpaper) varyanti var; donusumde
  cift basina **1 ilan korunur**, kalanlar pasife alinir.
- Pasife alinacak sayi: 156 - (korunan) = **312** (gorevde verilen sayi).
  DIKKAT: 156 ilan icinden 312 pasif cikmaz. Bu sayi ancak toplam ilan havuzu
  156'dan buyukse tutar (78 cift x 4 edisyon x 2 tur = 624 varyant gibi).
  **Bu celiski Claude'a soruldu** - kesin sayi, ilan envanteri okunmadan
  dogrulanamaz. Asagidaki kural sayidan bagimsiz calisir.

## Secim kurali (gorevde verilen sira, aynen)

Her cift + tur (dijital / wallpaper) icin korunacak tek ilan:
1. **Siparis** almis ilan varsa o (coktan aza; esitlikte 2'ye gec).
2. Yoksa **favori** sayisi en yuksek olan (esitlikte 3'e gec).
3. Yoksa **ziyaret** (views) en yuksek olan (esitlikte 4'e gec).
4. Hala esitse **Midnight Blue** edisyonu.

Kural deterministik: her adim bir onceki esitligi kirar, son adim tek bir
edisyon secer. Cikti tablosu: `cift, tur, korunan_listing_id, korunma_sebebi
(siparis/favori/ziyaret/midnight_blue), pasife_alinacak_listing_id listesi`.

## Gerekli veri (bende YOK, Etsy salt-okuma turu gerekir)

| veri | kaynak | not |
|---|---|---|
| ilan envanteri (id, baslik, edisyon, tur, state) | `getShopListings` (draft+active) | ~1 cagri/100 ilan |
| siparis sayisi / ilan | `getShopReceipts` -> transactions | tarih araligi gerekir |
| favori sayisi / ilan | `getListing` (num_favorers) | ilan basina 1 cagri |
| ziyaret (views) | Etsy API'de YOK | yalniz Shop Manager arayuzu / CSV indirimi. **Karar gerekli:** views olmadan kural 3 atlanir mi, yoksa Serdar CSV'yi Drive'a mi koyar? |
| galeri kartlari 10/6 hazir mi | Drive `A1_77/<CIFT>/SET.json` | medya uretiyor |

Tahmini cagri: envanter ~7 + favori 156 + receipts ~10 = **~175 salt-okuma
cagrisi**. Kota tabani 230'un altina inmemesi icin ayri turda kosulmali.

## Eksikler (kim uretecek)

1. **views verisi** - Etsy API vermiyor. Serdar/koordinator karari.
2. **312 sayisinin dogrulanmasi** - envanter okunmadan teyit edilemez.
3. **Galeri kartlari** - 10 kart (dijital) / 6 kart (wallpaper) her korunan ilan
   icin gerekli. medya oturumu uretiyor; 77 cift seti hazir mi kontrol edilmeli.
4. **made-to-order alanlari** - `is_made_to_order`, `when_made`, processing
   suresi ve kargo profili her korunan ilanda guncellenecek. Bu YAZMA islemidir;
   ayri onay gerekir (CLAUDE.md: Etsy'ye yazan her adim onay bekler).
5. **updateListing taslagi yayina alir** kurali: donusumde her ilanin state'i
   YAZMADAN ONCE okunacak; taslak kalmasi gerekenler guncellenmeyecek.

## Kuru kosu cikti dosyalari (uretilecek, yazma yok)

- `DIJITAL_78/DONUSUM_KURU_KOSU.csv` - yukaridaki secim tablosu.
- `DIJITAL_78/DONUSUM_PASIF_LISTE.csv` - pasife alinacak ilan id'leri.
- `DIJITAL_78/DONUSUM_EKSIK.csv` - ilan basina eksik olan sey (kart, alan, veri).

Bu uc dosya, veri turu kosulunca tek script ile uretilir; script henuz
yazilmadi (veri sozlesmesi netlesmeden yazmak bos is olur).
