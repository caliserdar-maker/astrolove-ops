# Öncelik kararı (Serdar, 26 Eki 2026 akşam)

"Önce wall art işleri tamamen bitecek, Etsy'de yayınlanacak. Ardından 1st Anniversary işine başlanacak."

## Wall art (Zodiac Couple Poster, 78 ilan): bitirme sırası
1. Galeri v10 yükleyicisi (Denetim): bağımsız inceleme, commit, rapor.
2. Dışa aktarma (Claude): 78 POSTER_GALERI_V1 tasarımı + ortak kartlar (DAHZGSI_nLw s12, s13). TSV'ler (G1, G2, G3) Drive'a gider.
3. Taşıma (Denetim): galeri-v10-tasi, aynı hedef_damga, OZET 470/470 PASS.
4. Kuru koşu (salt okuma; ayrı onay).
5. Pilot 4570110121 (ayrı onay), sonra kalan 77 ilan gruplar halinde (her grup ayrı onay).
6. Açıklama düzeltmesi (onaylı metin; ayrı yazım, ayrı onay).
7. Video v7b: 3 örnek (Serdar onayı), 78 toplu üretim, yükleme galeriden sonra (ayrı onay).
8. 5x7: wall art'ın son adımı, ayrı iş (tedarikçi çelişkisi çözülmeli: yönlendirici Hahnemühle, 23 Eki kararı Hahnemühle değil).

## 1st Anniversary (YD): DONDURULDU
- Wall art Etsy'de yayınlanana kadar YD'de üretim, kod ve Etsy işi yapılmaz.
- Hazır olanlar korunur:
  - 75 kapak (YD_KAPAK_V1, bağımsız inceleme 75/75 hatasız);
  - galeri örnekleri DAHZIQjIitA (format kartı "14 Sizes" ile kaydedildi) ve DAHZIQfp8Bw;
  - stil kaynak listesi ve galeri üretim aracı (Claude çalışma klasörü).
- Plan: docs/yd_kapak/AstroLove_YD_KAPAK_PLAN_V3_20261026.md (proje kopyası: claude/AstroLove_YD_KAPAK_PLAN_V3_20261026.md).

## Güncelleme (Serdar, 27 Eki 2026)
- YD dondurması YALNIZ Etsy'siz hazırlık için kaldırıldı (plan v3 adım 2, 4, 5, 6, 7, 8: taşıma profili, QC betiği, yedek iş akışı, yükleyici girdileri, yükleyici YD profili ve yerel testler). İşi Denetim yapar.
- Kurallar: Etsy API isteği yok; ayrı dal yd-kapak, main'e yazma ve merge yok (yükleyici poster galerisiyle ortak); Canva işi Merkez'de; görsel onayı Serdar'da.
- Kuru koşu, pilot ve yükleme poster galerisi 78/78 bittikten sonra, her biri ayrı Serdar onayıyla.
- Durum 27 Eki: poster galerisi 28/78, Etsy kotası (5000/gün, son 24 saat) darboğaz.
