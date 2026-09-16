# AstroLove Operasyon Durumu

Guncelleme: **2026-09-16**

> Bu belge `config/operational_state.json` dosyasindan uretilir. Tamamlanan işler
> `config/completed_operations.json` defteriyle tek yönlü kilitlenir. Eski batch raporlari durum kaynagi degildir.

| oncelik | is | durum | kapsam | kanit / hazir dosya |
|---:|---|---|---|---|
| 0 | 54 Etsy başlık bulgusu incelemesi | **TAMAMLANDI** | 54/54 yanlış pozitif; 0 canlı değişiklik | `docs/batch4/TITLE_54_REVIEW.md` |
| 0 | GPSR panel girişi | **TAMAMLANDI** | 78/78 POD ilanı | `docs/start_here/B99.txt` |
| 0 | Workflow hardening merge | **TAMAMLANDI** | claude/wf-hardening -> main | `docs/batch4/workflow_final_test.md` |
| 10 | Wallpaper açıklama düzeltmesi | **ONAY BEKLIYOR** | 78 ilan | `wallpaper_title_description_approval.csv (yalnız tur=description)` |
| 20 | Duplicate arşivleme | **ONAY BEKLIYOR** | 722 dosya / 0,99 GB / 200 grup | `duplicate_archive_plan.csv` |
| 30 | Etsy Ads veri içe alma | **GIRDI BEKLIYOR** | Gerçek Etsy Ads CSV | `ads_import_template.csv` |
| 40 | Mağaza paneli P0-P1 düzeltmeleri | **ONAY BEKLIYOR** | P0-P1 maddeleri | `store_conversion_actions.md` |
| 50 | Sosyal medya / Metricool yayını | **ONAY BEKLIYOR** | 546 satır | `platform_content_final.csv` |

## Zorunlu karar kurali

1. Bir isin durumu yalnizca kanonik JSON kaydindan okunur.
2. Tamamlanma defterindeki bir is yeniden bekleyenler listesine eklenemez.
3. Kanit eksikse veya belgeler celisiyorsa kontrol FAIL olur; sonraki is onerilmez.
4. Canli islem, durum `pending_approval` olsa bile Serdar'in o isleme ozel acik onayi olmadan baslamaz.
