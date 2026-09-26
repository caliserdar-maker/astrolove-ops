# AstroLove Operasyon Durumu

Guncelleme: **2026-09-20**

> Bu belge `config/operational_state.json` dosyasindan uretilir. Tamamlanan işler
> `config/completed_operations.json` defteriyle tek yönlü kilitlenir. Eski batch raporlari durum kaynagi degildir.

| oncelik | is | durum | kapsam | kanit / hazir dosya |
|---:|---|---|---|---|
| 0 | 54 Etsy başlık bulgusu incelemesi | **TAMAMLANDI** | 54/54 yanlış pozitif; 0 canlı değişiklik | `docs/batch4/TITLE_54_REVIEW.md` |
| 0 | GPSR panel girişi | **TAMAMLANDI** | 78/78 POD ilanı | `docs/start_here/B99.txt` |
| 0 | Wallpaper açıklama düzeltmesi | **TAMAMLANDI** | 78/78 wallpaper ilanı; yalnız description | `docs/operations/WP_DESCRIPTION_78_APPLY_20260916.md` |
| 0 | Workflow hardening merge | **TAMAMLANDI** | claude/wf-hardening -> main | `docs/batch4/workflow_final_test.md` |
| 5 | Dijital 390 -> 78 birlestirme | **ONAY BEKLIYOR** | 78 cift; 78 ilan kalir, 312 ilan devre disi; ARIES_SCORPIO karar bekliyor | `docs/operations/DIJITAL_78_V2_20260920.md` |
| 10 | Duplicate arşivleme | **ONAY BEKLIYOR** | 722 dosya / 0,99 GB / 200 grup | `duplicate_archive_plan.csv` |
| 20 | Etsy Ads veri içe alma | **GIRDI BEKLIYOR** | Gerçek Etsy Ads CSV | `ads_import_template.csv` |
| 30 | Mağaza paneli P0-P1 düzeltmeleri | **ONAY BEKLIYOR** | P0-P1 maddeleri | `store_conversion_actions.md` |
| 40 | Sosyal medya / Metricool yayını | **ONAY BEKLIYOR** | 546 satır | `platform_content_final.csv` |

## Zorunlu karar kurali

1. Bir isin durumu yalnizca kanonik JSON kaydindan okunur.
2. Tamamlanma defterindeki bir is yeniden bekleyenler listesine eklenemez.
3. Kanit eksikse veya belgeler celisiyorsa kontrol FAIL olur; sonraki is onerilmez.
4. Canli islem, durum `pending_approval` olsa bile Serdar'in o isleme ozel acik onayi olmadan baslamaz.
