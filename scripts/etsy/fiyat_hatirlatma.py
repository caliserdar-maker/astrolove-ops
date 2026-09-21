#!/usr/bin/env python3
"""FIYAT GOZDEN GECIRME HATIRLATMASI (Serdar hicbir seyi hatirlamayacak; 21 Eyl 2026).

Gunluk hafif kontrol. Esiklerden biri gerceklesince BIR KEZ POD satis raporu uretir:
  - magaza toplam satis >= --satis-esik (30), ya da
  - yorum sayisi >= --yorum-esik (10), ya da
  - --baslangic tarihinden bu yana --gun (60) gun gecti.
Rapor: Drive TEMP/POD_ORDERS/FIYAT_RAPORU.md (boy bazinda adet, Prodigi maliyeti ekler dahil,
Etsy ucretleri, net kar/zarar) + kosu bilincli BASARISIZ (GitHub e-postasi).
Tekrar etmez: durum Drive TEMP/POD_ORDERS/FIYAT_HATIRLATMA.json dosyasinda tutulur.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE; Prodigi anahtari (Drive).
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "prodigi"))
from etsy_common import Etsy, TokenStore  # noqa: E402
from pod_sku import parse_sku  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_ORDERS"
DURUM_DRV = f"{DRV}/FIYAT_HATIRLATMA.json"
RAPOR_DRV = f"{DRV}/FIYAT_RAPORU.md"
# Etsy ucret modeli (7 Eyl olcumu): islem %6.5, odeme %6.5 + 14 TRY, duzenleyici %1.67,
# doviz %2.5, ilan 0.20 USD. Offsite Ads haric (satis basina degisken).
UCRET_ORAN = 0.065 + 0.065 + 0.0167 + 0.025
UCRET_SABIT = 0.20
TRY_SABIT_USD = 14 / 48.785        # odeme sabiti (olculen kur)


def log(m):
    print(m, flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def durum_oku():
    r = rclone("cat", DURUM_DRV, sert=False)
    if r.returncode != 0 or not r.stdout.strip():
        return {}
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def durum_yaz(isd, d):
    p = isd / "FIYAT_HATIRLATMA.json"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(p), DURUM_DRV)


def prodigi_maliyet(prod_siparisler):
    """Prodigi siparislerinden gercek maliyet (ekler dahil): {merchantReference: (toplam, para)}."""
    out = {}
    for o in prod_siparisler:
        toplam = 0.0
        for c in o.get("charges") or []:
            for k in c.get("items") or []:
                toplam += float((k.get("cost") or {}).get("amount") or 0)
        if toplam:
            out[str(o.get("merchantReference") or o.get("id"))] = round(toplam, 2)
    return out


def rapor_uret(api, shop, prod, gun):
    """Son <gun> gunun POD satislarindan boy bazinda rapor. -> (metin, ozet)."""
    since = int(time.time()) - gun * 86400
    satirlar, boylar = [], {}
    offset, receipts = 0, []
    for _ in range(5):
        r = api.get(f"/shops/{shop}/receipts",
                    params={"limit": 100, "offset": offset, "min_created": since}) or {}
        res = r.get("results") or []
        receipts += res
        if len(res) < 100:
            break
        offset += 100
    prod_sip = prod.siparisler(100) if prod else []
    maliyet_haritasi = prodigi_maliyet(prod_sip)
    toplam_gelir = toplam_maliyet = 0.0
    for rc in receipts:
        rid = str(rc.get("receipt_id"))
        for t in rc.get("transactions") or []:
            p = parse_sku((t.get("sku") or "").strip())
            if not p:
                continue
            _pair, _ed, boy = p
            adet = int(t.get("quantity") or 1)
            pr = t.get("price") or {}
            fiyat = float(pr.get("amount") or 0) / float(pr.get("divisor") or 100)
            b = boylar.setdefault(boy, {"adet": 0, "gelir": 0.0, "maliyet": 0.0, "maliyet_bilinen": 0})
            b["adet"] += adet
            b["gelir"] += fiyat * adet
            toplam_gelir += fiyat * adet
            m = maliyet_haritasi.get(rid) or maliyet_haritasi.get(f"etsy-{rid}-{boy}")
            if m:
                b["maliyet"] += m
                b["maliyet_bilinen"] += adet
                toplam_maliyet += m
    ucret = toplam_gelir * UCRET_ORAN + (UCRET_SABIT + TRY_SABIT_USD) * sum(
        b["adet"] for b in boylar.values())
    net = toplam_gelir - toplam_maliyet - ucret
    satirlar = ["# POD fiyat gozden gecirme raporu", f"(uretim {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"
                f" | son {gun} gun)", "",
                "| boy | adet | Etsy geliri | Prodigi maliyeti (ekler dahil) | maliyeti bilinen adet |",
                "|---|---|---|---|---|"]
    for boy in sorted(boylar, key=lambda x: -boylar[x]["adet"]):
        b = boylar[boy]
        satirlar.append(f"| {boy} | {b['adet']} | {b['gelir']:.2f} | {b['maliyet']:.2f} | "
                        f"{b['maliyet_bilinen']} |")
    satirlar += ["", f"- Toplam Etsy geliri: **{toplam_gelir:.2f} USD**",
                 f"- Toplam Prodigi maliyeti (ekler dahil, bilinen siparisler): **{toplam_maliyet:.2f} USD**",
                 f"- Etsy ucretleri (model: %{UCRET_ORAN * 100:.2f} + {UCRET_SABIT + TRY_SABIT_USD:.2f}/kalem, "
                 f"Offsite Ads haric): **{ucret:.2f} USD**",
                 f"- **Net: {net:.2f} USD**", "",
                 "Fiyat gozden gecirme zamani: 5x7 19.99 (bilincli zarar) ve A1 89.99 kararlarini "
                 "gercek maliyetle karsilastir.", ""]
    return "\n".join(satirlar), {"adet": sum(b["adet"] for b in boylar.values()),
                                 "gelir": round(toplam_gelir, 2), "maliyet": round(toplam_maliyet, 2),
                                 "ucret": round(ucret, 2), "net": round(net, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--satis-esik", type=int, default=30)
    ap.add_argument("--yorum-esik", type=int, default=10)
    ap.add_argument("--baslangic", default="2026-09-21")
    ap.add_argument("--gun", type=int, default=60)
    ap.add_argument("--is-dizin", default="_work/fiyat")
    ap.add_argument("--kuru", action="store_true", help="yalniz olcumleri yazdir, rapor/hata yok")
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)

    durum = durum_oku()
    if durum.get("rapor_utc"):
        log(f"hatirlatma zaten uretildi ({durum['rapor_utc']}); bir sey yapilmadi")
        return 0

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop_id = os.environ["ETSY_SHOP_ID"]
    shop = api.get(f"/shops/{shop_id}") or {}
    satis = int(shop.get("transaction_sold_count") or 0)
    yorum = int(shop.get("review_count") or 0)
    gecen_gun = (time.time() - time.mktime(time.strptime(a.baslangic, "%Y-%m-%d"))) / 86400
    tetik = []
    if satis >= a.satis_esik:
        tetik.append(f"satis {satis} >= {a.satis_esik}")
    if yorum >= a.yorum_esik:
        tetik.append(f"yorum {yorum} >= {a.yorum_esik}")
    if gecen_gun >= a.gun:
        tetik.append(f"{gecen_gun:.0f} gun >= {a.gun}")
    log(f"olcum: satis {satis} | yorum {yorum} | {gecen_gun:.1f} gun | kota {api.remaining} | "
        f"tetik: {tetik or 'yok'}")
    if a.kuru or not tetik:
        return 0

    from order_router import Prodigi, load_prodigi_key      # noqa: E402
    prod = Prodigi(load_prodigi_key("live"), "live")
    metin, ozet = rapor_uret(api, shop_id, prod, a.gun)
    metin = f"Tetikleyen: {'; '.join(tetik)}\n\n" + metin
    p = isd / "FIYAT_RAPORU.md"
    p.write_text(metin, encoding="utf-8")
    rclone("copyto", str(p), RAPOR_DRV)
    durum_yaz(isd, {"rapor_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "tetik": tetik, "ozet": ozet})
    log(metin[:1500])
    ozeti = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozeti:
        with open(ozeti, "a", encoding="utf-8") as fh:
            fh.write(metin + "\n")
    raise SystemExit("DUR: Fiyat gozden gecirme zamani, rapor Drive'da "
                     f"({RAPOR_DRV}); tetik: {'; '.join(tetik)}")


if __name__ == "__main__":
    sys.exit(main())
