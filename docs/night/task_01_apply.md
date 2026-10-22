# GOREV 1 - 78 ilanlik CANLI apply kosusu

- **Baslangic:** 2026-09-15 18:29:21 UTC (kosu 35007789976, adim 18:30:35)
- **Bitis:** 2026-09-15 18:45:51 UTC (yazma adimi 15 dk 16 sn)
- **Durum: PASS**
- **Islenen kayit:** 78 ilan (78 GUNCELLENECEK, 0 ATLA, 0 SORUN)
- **Hata sayisi:** 0
- **Hata aciklamasi:** yok. Ilk ilan hatasinda durma kurali devreye girmedi.
- **Sonraki goreve gecildi mi:** evet (GOREV 2)

## Sonuc
| olcu | deger |
|---|---|
| Basarili + dogrulandi | **78** |
| Atlandi (zaten ayni) | 0 |
| Hatali | 0 |
| Islenmedi | 0 |
| Durus nedeni | yok |
| OAuth | /users/me -> OK, scope'ta `listings_w` VAR |
| Kota | 629 -> 386 (244 API cagrisi) |

## Yazilan alanlar
Ilan basina govdede YALNIZ `title`, `description`, `tags` (13 tag virgulle birlesik).
Alan dagilimi: title 72 ilanda, description 78 ilanda, tags 73 ilanda degisti.
Degismeyen 6 ilanda (4570113157 title; 4570153208, 4570160260, 4570198669,
4570201313, 4570220634 title+tags) v2 metni zaten canlidaydi, yalniz description yazildi.

## Her ilanda dogrulanan kapilar
1. Taze GET + `backups/<id>.before_apply.json` yedegi.
2. `state` active degilse DUR (hicbir ilanda tetiklenmedi).
3. PATCH sonrasi 10 sn arayla en fazla 3 geri okuma; title/description/tags birebir.
4. 12 korunan alan (price, state, shop_section_id, taxonomy_id, shipping_profile_id,
   return_policy_id, materials, who_made, when_made, is_supply, has_variations,
   should_auto_renew) once/sonra ayni.
5. Ilk yazilan ilanda ek olarak gorseller, varyasyon gorselleri, video ve envanter
   fiyatlari once/sonra karsilastirildi: AYNI.
6. Sonuc `backups/<id>.after.json` olarak yedeklendi.

## Yeni apply kosusu
Baslatilmadi. Gece plani geregi yeni canli Etsy yazma cagrisi yapilmayacak.

Kaynak: Drive `ASTROLOVE/TEMP/POD_SEO/APPLY_20260915_1845/` (report.md, report.csv,
ozet.json, pod_changes_v2.json, backups/ = 78 before_apply + 78 after + 78 before).
