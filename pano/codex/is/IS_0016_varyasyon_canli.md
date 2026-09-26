# Codex IS 0016 - canli renk varyasyonu denetimi workflow'u (salt okur)
AGENTS.md kurallari. Etsy'ye YAZMA YOK. Amac: medya'nin renk-gorsel duzeltmesini Claude kotasi harcamadan bagimsiz dogrulamak.
Yeni: .github/workflows/varyasyon-canli.yml (workflow_dispatch) + scripts/etsy/varyasyon_canli.py
- Girdi: ilan listesi (varsayilan: medya GALERI_TAMSET state'indeki PASS ilanlar + CL 4570143815; state yolu pod-galeri-tamset.yml'deki Drive konumundan rclone ile).
- Her ilan: GET inventory, GET variation-images, GET images. Mumkunse yalniz x-api-key; OAuth gerekirse etsy_common token akisi + concurrency: etsy-token, refresh token geri yazimi (docs/SECRETS.md), ::add-mask::.
- SET.json (Drive TAM_SET) ile scripts/etsy/varyasyon_denetle.denetle() calistir.
- Cikti: VARYASYON_CANLI.csv (ilan, cift, PASS/FAIL, renk bazinda neden) Drive TEMP'e + job ozeti ilk satir "X/Y PASS". Cagri sayaci logda; butce en fazla 3 cagri/ilan.
Test: sentetik JSON ile varyasyon_canli'nin ilan dongusu (en az 3 senaryo, ag yok).
Teslim: yanit yorumunun sonuna TAM unified diff (tek ```diff blogu). pano/codex/RAPOR_0016.md 5 satir.
