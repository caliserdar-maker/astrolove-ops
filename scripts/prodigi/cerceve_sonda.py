#!/usr/bin/env python3
"""Prodigi CERCEVE sondasi — SALT OKUMA (22 Eyl 2026).

Amac: HPR boylarimizla eslesen cerceveli urunler canli katalogda var mi, hangi renk/boy
secenekleriyle, birim maliyet ve ABD/Ingiltere kargosu ne.

Yontem:
  1) GET /v4.0/products/<SKU> ile aday SKU'larin varligi ve nitelikleri (renk, glaze, mount)
     olculur. 404 -> yok. Tahmin YAZILMAZ; yalniz donen veri raporlanir.
  2) Var olan SKU'lar icin POST /quotes (US ve GB) ile birim + kargo maliyeti alinir.
     quote SIPARIS DEGILDIR: hicbir sey uretilmez, hicbir sey yazilmaz.

Cikti: <out>/CERCEVE_SONDA.json + ekrana ozet. Prodigi'ye YAZMA (siparis) YOK.
"""
import argparse
import json
import pathlib
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from order_router import Prodigi, load_prodigi_key, KARGO_SECENEK  # noqa: E402

# Bizim 15 boyumuz (Etsy menusundeki anahtarlar)
BOYLAR = ["5x7", "8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2",
          "18x24", "20x30", "A1", "24x36", "30x40"]
# Aday cerceve aileleri: CFP = classic frame, CFPM = classic frame + mount (passepartout).
AILELER = ["GLOBAL-CFP", "GLOBAL-CFPM", "GLOBAL-BFP", "GLOBAL-FRA"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def urun_oku(prod, sku):
    st, d = prod.call("GET", f"/products/{sku}")
    if st != 200:
        return None
    u = (d.get("product") or d)
    nitelikler = {}
    for k, v in (u.get("attributes") or {}).items():
        nitelikler[k] = v if isinstance(v, list) else [v]
    return {"sku": u.get("sku") or sku, "aciklama": (u.get("description") or "")[:120],
            "nitelikler": nitelikler,
            "baski_alanlari": list((u.get("printAreas") or {}).keys()),
            "olculer": u.get("productDimensions")}


def teklif(prod, sku, ulke, nitelikler):
    """Cerceveli urunlerde 'attributes' (renk vb.) ZORUNLU: ilk sonda HTTP 400 dondu.
    Tum kargo yontemleri sorulur, en ucuzu secilir. Bu bir SIPARIS DEGILDIR."""
    kalem = {"sku": sku, "copies": 1, "assets": [{"printArea": "default"}]}
    if nitelikler:
        kalem["attributes"] = nitelikler
    secenekler, hatalar = [], []
    for yontem in KARGO_SECENEK:
        st, d = prod.call("POST", "/quotes", {"shippingMethod": yontem,
                                              "destinationCountryCode": ulke,
                                              "currencyCode": "USD", "items": [kalem]})
        if st != 200 or not d.get("quotes"):
            hatalar.append(f"{yontem}: HTTP {st} {json.dumps(d)[:160]}")
            continue
        for q in d["quotes"]:
            cs = q.get("costSummary") or {}
            it = float((cs.get("items") or {}).get("amount") or 0)
            kg = float((cs.get("shipping") or {}).get("amount") or 0)
            secenekler.append({"yontem": q.get("shipmentMethod") or yontem,
                               "birim": round(it, 2), "kargo": round(kg, 2),
                               "toplam": round(it + kg, 2)})
    if not secenekler:
        return None, "; ".join(hatalar)[:300]
    return min(secenekler, key=lambda x: x["toplam"]), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="live")
    ap.add_argument("--out", default="_out/cerceve")
    ap.add_argument("--teklif-boy", default="8x10,16x20,18x24",
                    help="maliyet teklifi alinacak boylar (virgullu)")
    ap.add_argument("--ulke", default="US,GB")
    ap.add_argument("--renk", default="black,white,natural")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prod = Prodigi(load_prodigi_key(a.env), a.env)

    sonuc = {"zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "env": a.env, "urunler": {}, "teklifler": {}, "hpr_karsilastirma": {}}

    # 1) katalog varligi
    for aile in AILELER:
        bulunan = {}
        for b in BOYLAR:
            for aday in (f"{aile}-{b}", f"{aile}-{b.upper()}", f"{aile}-{b.lower()}"):
                u = urun_oku(prod, aday)
                if u:
                    bulunan[b] = u
                    break
        sonuc["urunler"][aile] = bulunan
        log(f"{aile}: {len(bulunan)}/{len(BOYLAR)} boy katalogda -> {sorted(bulunan)}")
        if bulunan:
            ornek = next(iter(bulunan.values()))
            log(f"  ornek {ornek['sku']}: nitelikler {json.dumps(ornek['nitelikler'], ensure_ascii=False)[:300]}")

    # HPR karsilastirmasi (ayni boylar basili kagitta var mi)
    for b in BOYLAR:
        u = urun_oku(prod, f"GLOBAL-HPR-{b}")
        sonuc["hpr_karsilastirma"][b] = bool(u)
    log(f"HPR katalogda: {sum(sonuc['hpr_karsilastirma'].values())}/{len(BOYLAR)} boy")

    # 2) maliyet teklifi (SIPARIS DEGIL) — cerceve renkleri ayri ayri
    boylar = [x.strip() for x in a.teklif_boy.split(",") if x.strip()]
    renkler = [x.strip() for x in a.renk.split(",") if x.strip()]
    for aile, bulunan in sonuc["urunler"].items():
        if not bulunan:
            continue
        mevcut_renk = (next(iter(bulunan.values()))["nitelikler"].get("color") or [])
        for b in boylar:
            if b not in bulunan:
                continue
            sku = bulunan[b]["sku"]
            for renk in [r for r in renkler if r in mevcut_renk]:
                for ulke in [x.strip() for x in a.ulke.split(",") if x.strip()]:
                    secilen, hata = teklif(prod, sku, ulke, {"color": renk})
                    anahtar = f"{sku}|{renk}|{ulke}"
                    sonuc["teklifler"][anahtar] = {"secilen": secilen, "hata": hata}
                    if secilen:
                        log(f"teklif {anahtar}: birim {secilen['birim']:.2f} + kargo "
                            f"{secilen['kargo']:.2f} ({secilen['yontem']}) = {secilen['toplam']:.2f} USD")
                    else:
                        log(f"teklif {anahtar}: HATA {hata[:160]}")

    p = out / "CERCEVE_SONDA.json"
    p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"yazildi: {p} | kargo secenekleri: {KARGO_SECENEK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
