# GOREV 6 - Rakip ve pazar arastirmasi

Tarih: 15 Eyl 2026. **Durum: KISMI (PASS/veri sinirli).** Veri UYDURULMADI.

## Kapsam siniri (once bunu oku)

Bu gorevin tam yapilabilmesi icin rakip ilan sayfalarindan fiyat, baslik, gorsel ve
video verisi cekilmesi gerekir. Iki engel var:

1. **Etsy Open API v3'te genel arama ucu YOK.** v2'deki `findAllListings` kaldirildi;
   v3 ile yalniz kendi magazani okuyabilirsin. Rakip ilan verisi API'den alinamaz.
2. **Bu ortamda etsy.com sayfalari cekilemiyor**: egress proxy `www.etsy.com` icin
   403 donuyor (OAS indirmede de ayni sinir gorulmustu; Actions kosusunda OAS
   indirilebiliyor ama ilan sayfasi HTML'i kazinmasi Etsy kullanim sartlarina da
   takilir).

Bu yuzden asagida **yalnizca dogrulanabilen** seyler yazildi. Fiyat dagilimi, baslik
kalibi istatistigi, mockup turu orani ve video kullanim orani **olculmedi**; bunlar
icin onerilen yontem en altta.

## Dogrulanan pazar gozlemleri (kaynakli)

| gozlem | kaynak |
|---|---|
| "zodiac couple print" kategorisinde 1.000'den fazla sonuc var; kisisellestirilmis (isim/tarih) urunler one cikiyor | [Couples Zodiac Print - Etsy](https://www.etsy.com/market/couples_zodiac_print) |
| Kisisellestirilmis zodiac couple print ornegi 2.764 favori toplamis (DesignedByLeanneShop) | [Personalised Zodiac Couple Print](https://www.etsy.com/listing/978956244/personalised-zodiac-couple-print-custom) |
| Kategori komsulari: zodiac wedding gift, horoscope print, matching zodiac couple, personalized couple zodiac blanket | [zodiac_wedding_gift](https://www.etsy.com/uk/market/zodiac_wedding_gift), [matching_zodiac_couple](https://www.etsy.com/market/matching_zodiac_couple), [personalized_couple_zodiac_blanket](https://www.etsy.com/market/personalized_couple_zodiac_blanket) |
| Dijital tarafta yaygin format: tek burc printable, 8x10 JPG, "instant download"; 2026 zodiac takvimi gibi mevsimsel urunler var | [Printable Zodiac Wall Art](https://www.etsy.com/listing/605765589/printable-zodiac-wall-art-aries-print), [Printable Zodiac Calendar 2026](https://www.etsy.com/listing/4430123305/printable-zodiac-calendar-2026-hand) |
| Genis kategori sayfalari: zodiac wall art, astrology wall art, zodiac art print | [zodiac_wall_art](https://www.etsy.com/market/zodiac_wall_art), [astrology_wall_art](https://www.etsy.com/market/astrology_wall_art), [zodiac_art_print](https://www.etsy.com/market/zodiac_art_print) |

## AstroLove'un olculen konumu (kendi katalogumuzdan, gercek veri)

| olcu | deger |
|---|---|
| Aktif ilan | 546 (390 dijital poster + 78 wallpaper + 78 POD) |
| Fiyat | POD 30.99 USD (8x10) baslangic, dijital poster 9.99, wallpaper 6.65 |
| Baslik kalibi (POD, SEO v2) | `<Burc1> and <Burc2> Zodiac Couple Print, Minimalist Gold Line Art, Hahnemühle Giclée, Unframed` |
| Etiket kumesi | 4 cifte ozel + 9 ortak (zodiac couple print, compatibility print, giclee wall art, unframed art print, minimal gold art, couple bedroom art, relationship gift, astrology home decor, celestial poster) |
| Ilk gorsel stratejisi | Midnight Blue hero + oda sahnesi; POD'da 12 gorsel + 1 video (1080x1350) |
| Kapsam | 78 cift x 5 edisyon; rakiplerde gorulmeyen kombinasyon genisligi |

## Farklilasma firsatlari (gozleme dayali, olcum degil)

1. **Kisisellestirme bosluğu**: en cok favori alan rakip urun kisisellestirilmis
   (isim/tarih). AstroLove'da kisisellestirme YOK ve "isim/tarih eklenmez" politikasi
   aciklamada yazili. Bu bilincli bir karar; ancak pazarin en gucla talep sinyali orada.
2. **Cift kombinasyonu genisligi**: 78 ciftin tamami ayri ilan olarak var. Rakipler
   genelde tek burc ya da kisisellestirilmis tek urun satiyor. "Tam koleksiyon"
   konumlandirmasi magaza duzeyinde one cikarilabilir.
3. **Fiziksel + dijital ayni cift icin**: capraz satis bloklari zaten kurulu. Rakiplerde
   bu ikili yapi yaygin degil.
4. **Malzeme iddiasi**: Hahnemühle Photo Rag 308 gsm ve arsiv giclee, dijital agirlikli
   kategoride guclu bir ayirt edici; baslikta zaten var.
5. **Mevsimsellik**: "zodiac calendar 2026" gibi takvim/mevsim urunleri kategoride
   gorunuyor; AstroLove'da yok.

## Tam arastirma icin onerilen yontem (bu kosuda YAPILMADI)

- Etsy'nin resmi **Shop Manager > Search analytics** ekranindan kendi arama terimi
  verisini disa aktarmak (rakip degil ama gercek talep sinyali).
- Rakip verisi icin ucuncu parti arac (eRank, Alura, Marmalead) CSV disa aktarimi;
  cikti Drive'a konursa bu rapor gercek sayilarla yeniden uretilebilir.
- Elle 20 ilanlik ornek: kategori basina 4 ilan, baslik/fiyat/gorsel sayisi/video
  kaydedilir. Yaklasik 30 dakikalik elle is, kazima gerektirmez.
