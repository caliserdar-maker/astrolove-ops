# POD siparis yonlendirici (Etsy -> Prodigi -> Etsy), 6 Eyl 2026

## Parcalar

| Parca | Dosya | Is |
|---|---|---|
| Baski dosyalari | `scripts/pod/pod_print_build.py`, `pod-print-build` | 78 cift x 5 edisyon x 13 boyut = 5.070 JPEG; hedef piksel Prodigi print-area (`scripts/prodigi/prodigi_print_areas.py` -> `TEMP/PRODIGI/PRODIGI_HPR_PRINT_AREAS.json`; inc boyutlar inc x 300 ile dogrulanir, A serisi API degeri). Drive `TEMP/POD_PRINT/<PAIR>/<ED>/<SIZE>.jpg`, PAYLASIM YOK. STATE `TEMP/POD_PRINT_STATE.csv`, rapor `TEMP/POD_PRINT_REPORT.md`. QC: geri okuma, piksel tam esit. |
| Yonlendirici | `scripts/prodigi/order_router.py`, `pod-order-router` | asagida |

## Akis (her kosu, 30 dk)

1. Etsy `getShopReceipts` (was_paid=true, was_shipped=false). SKU `POD-<burc3>_<burc3>-<ed2>-<SIZE>` (`scripts/etsy/pod_sku.py`, or. POD-ARI_LEO-MB-18x24) olan islemler.
2. Yeni receipt:
   - ulke `US/CA/AU/GB` degilse `manual` (elle islenir; dokunulmaz).
   - Prodigi teklif (Budget, USD) -> `prodigi_cost` (urun + kargo); `etsy_total` = islem fiyat x adet;
     `margin = (etsy_total - prodigi_cost) / etsy_total`; `< 0.20` ise `warn=MARJ_DUSUK` (durdurmaz).
   - apply: baski dosyasina gecici Drive izni (`anyone:reader`, dosya bazinda; klasor degil) ->
     `POST /orders` (`idempotencyKey = etsy-<receipt_id>`, `merchantReference` ayni, `shippingMethod Budget`,
     `sizing fillPrintArea`, alici adresi Etsy'den) -> `ordered` + `prodigi_order_id`.
3. `ordered`: `GET /orders/{id}`; `status.details.downloadAssets == Complete` olunca gecici izinler silinir
   (`asset_perms` bosalir; tamamlanmadiysa sonraki kosuda tekrar denenir). Shipment'ta `tracking.number`
   gelince `shipped` (+ `carrier`).
4. `shipped`: Etsy `createReceiptShipment` (`tracking_code`, `carrier_name`, `send_bcc`) -> geri okuma ->
   `tracked`. Yalniz `--etsy-writes` ile (cron = live + apply + etsy_writes).
5. Herhangi bir Prodigi/Etsy hatasi: satir `error`, STATE yazilir, kosu `exit 1` (DUR); `error` satiri
   otomatik yeniden denenmez (Mo inceler, STATE'te stage duzeltilir ya da satir silinir).

Kosu basina en fazla `--max-orders` (5) yeni siparis. Idempotent: STATE + Prodigi idempotencyKey.

## STATE semasi (`TEMP/POD_ORDERS_STATE.csv`, anahtar receipt_id)

| sutun | anlam |
|---|---|
| receipt_id | Etsy receipt |
| stage | dryrun / manual / ordered / shipped / tracked / error |
| country | alici ulke (ISO) |
| items | `SKUxADET, ...` |
| etsy_total / prodigi_cost / margin | USD; marj orani |
| warn | `MARJ_DUSUK ...`, `POD disi urun: [...]` |
| prodigi_order_id / prodigi_status | Prodigi siparis id; `stage/downloadAssets/inProduction` |
| asset_perms | acik gecici Drive izinleri `[[file_id, perm_id], ...]` (bos = kapatildi) |
| tracking / carrier | kargo |
| ts_utc / note | son guncelleme; aciklama |

## Ortamlar ve anahtarlar

- `--env sandbox`: `https://api.sandbox.prodigi.com/v4.0`, anahtar Drive `TEMP/PRODIGI_SANDBOX_TOKEN.json`
  (`{"api_key": "..."}`; Prodigi panelinde sandbox anahtari ayri uretilir — Mo). Sandbox siparisleri
  uretime gitmez.
- `--env live`: `https://api.prodigi.com/v4.0`, anahtar `TEMP/PRODIGI_TOKEN.json`.
- Anahtar loga/dosyaya yazilmaz (`::add-mask::`, log maskesi). Etsy token: `TEMP/ETSY_TOKEN.json` (tek kaynak).

## Test sirasi (sandbox, uctan uca)

1. Mo: sandbox anahtarini `TEMP/PRODIGI_SANDBOX_TOKEN.json` olarak Drive'a koyar.
2. `TEMP/POD_ORDERS/TEST_RECEIPT.json`: Etsy receipt bicimi (`receipt_id`, `name`, `first_line`, `city`,
   `state`, `zip`, `country_iso`, `buyer_email`, `transactions[{transaction_id, sku, quantity, price{amount,divisor}}]`),
   SKU `POD-ARIES_LEO-MIDNIGHT_BLUE-18x24` (baski dosyasi POD_PRINT'te olmali).
3. `pod-order-router` dispatch: env=sandbox, dry_run=true, test_receipt=... -> teklif + marj raporu.
4. `pod-order-router` dispatch: env=sandbox, dry_run=false, test_receipt=... -> sandbox siparis, izin ac/kapat,
   sonraki kosularda shipped (sandbox kargo simulasyonu) -> Etsy'ye yazilmaz (etsy_writes kapali).
5. Canli: `POD_ROUTER_ENABLED=true` degiskeni (gh_secrets.py ile) + workflow'da `schedule` satiri acilir -> cron 30 dk
   live/apply/etsy_writes. (Cron kapali tutuluyor: is atlansa bile etsy-token grubuna girip bekleyen Etsy kosusunu iptal ediyor.)

## Maliyet kontrolu

Prodigi HPR US Budget (6 Eyl teklifi) vs Etsy fiyat (pod_prices.csv): 8x10 30.99 vs 10.00+6.85 (marj %46),
18x24 56.99 vs 24.00+7.10 (%45), 24x36 100.99 vs 41.00+14.65 (%45), 30x40 124.99 vs 54.00+14.65 (%45).
Etsy komisyon/odeme ucretleri (~%9.5 + listeleme) marja dahil degildir; kosu basina gercek teklif alinir.
