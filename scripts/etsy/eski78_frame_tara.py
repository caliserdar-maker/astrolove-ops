#!/usr/bin/env python3
"""ESKI 78 POSTER: framed durumu SALT OKUMA taramasi (Serdar 17 Eki, ACIL adim 1). Etsy'ye yalniz GET; yazma metodu YOK.
Istek: toplu oku (1) + ilan basina envanter GET (78) = ~79.
Ilan basina: state, envanter urun sayisi, format menusu adi, framed urun sayisi (format degeri 4 cerceve degerinden biri),
  framed deger sayisi, aciklamada frame/framed/unframed/framing gecis sayisi, C yeni satiri var mi, kagit sozu (Hahnemuhle/
  Photo Rag/gsm/cotton/giclee) sayisi, materials.
Cikti (OUT): ESKI78_FRAME_TARA.csv + OZET.md; ozet satirlari ::warning:: (job logu proxy'de okunamiyor).
Kullanim: eski78_frame_tara.py --ids data/pod/pod78_ids.csv --out DIR"""
import argparse
import csv
import html
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
P_FORMAT = 514
CERCEVE = {"Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"}
FRAME = re.compile(r"\b(frames?|framed|unframed|framing)\b", re.I)
KAGIT = re.compile(r"hahnem|photo rag|\bgsm\b|cotton|gicl", re.I)
YENI_SATIR = "Frames shown in photos are for display only and are not included. Prints ship unframed."


class SaltOkur:
    """Etsy istemcisi: yalniz GET."""

    def __init__(self, api):
        self.api = api

    def get(self, *a, **k):
        r = self.api.get(*a, **k)
        try:
            if int(self.api.remaining) < KOTA_MIN:
                raise SystemExit(f"KOTA {self.api.remaining} < {KOTA_MIN}")
        except (TypeError, ValueError):
            pass
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="data/pod/pod78_ids.csv")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    ham = Etsy(store); api = SaltOkur(ham)
    rows = list(csv.DictReader(open(a.ids)))
    ids = [r["listing_id"].strip() for r in rows]
    L = {}
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    tab, t0 = [], time.time()
    for i, r in enumerate(rows, 1):
        lid = r["listing_id"].strip(); x = L.get(lid) or {}
        d = html.unescape(x.get("description") or "")
        inv = api.get(f"/listings/{lid}/inventory") or {}
        prods = inv.get("products") or []
        fmt, adlar = [], set()
        for p in prods:
            for v in p.get("property_values") or []:
                if v.get("property_id") == P_FORMAT:
                    fmt.append((v.get("values") or [""])[0]); adlar.add(v.get("property_name"))
        fr = [f for f in fmt if f in CERCEVE]
        # geri okuma (17 Eki adim 3): fiyat renkten bagimsiz mi, stok, SKU
        fiyat, stok, skus = {}, set(), []
        fiyat_tutarsiz = 0
        for p in prods:
            d_ = {v.get("property_id"): (v.get("values") or [""])[0] for v in p.get("property_values") or []}
            o = (p.get("offerings") or [{}])[0]; pr = o.get("price") or {}
            f_ = round(pr.get("amount", 0) / (pr.get("divisor") or 1), 2); k_ = (d_.get(514), d_.get(513))
            if k_ in fiyat and fiyat[k_] != f_:
                fiyat_tutarsiz += 1
            fiyat[k_] = f_; stok.add(o.get("quantity")); skus.append(p.get("sku") or "")
        frame_satir = [ln for ln in d.splitlines() if FRAME.search(ln) and ln.strip() != YENI_SATIR]
        tab.append(dict(cift=r["cift"], listing_id=lid, state=x.get("state"), urun=len(prods), format_menu="|".join(sorted(a_ for a_ in adlar if a_)),
                        framed_urun=len(fr), framed_deger=len(set(fr)), aciklama_frame=len(FRAME.findall(d)),
                        yeni_satir=YENI_SATIR in d, kagit_sozu=len(KAGIT.findall(d)), materials=";".join(x.get("materials") or []),
                        frame_disi_satir=len(frame_satir), fiyat_imza=";".join(f"{k[0]}|{k[1]}={v}" for k, v in sorted(fiyat.items(), key=str)),
                        fiyat_tutarsiz=fiyat_tutarsiz, stok="|".join(sorted(str(q) for q in stok)),
                        sku_dolu=sum(1 for q in skus if q), sku_benzersiz=len(set(skus)),
                        sku_onek_ok=all(q.startswith(f"POD-{r['cift'].split('_')[0][:3]}_{r['cift'].split('_')[1][:3]}-") for q in skus if q)))
        if i % 10 == 0 or i == len(rows):
            g = time.time() - t0
            print(f"[{i}/{len(rows)}] %{i * 100 // len(rows)} gecen {g:.0f}s kalan ~{g / i * (len(rows) - i):.0f}s kota {ham.remaining}", flush=True)
    alan = list(tab[0])
    with open(out / "ESKI78_FRAME_TARA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(tab)
    md = ["| " + " | ".join(alan) + " |", "|" + "---|" * len(alan)] + ["| " + " | ".join(str(t[c]) for c in alan) + " |" for t in tab]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    from collections import Counter
    oz = lambda c: dict(Counter(str(t[c]) for t in tab))  # noqa: E731
    print("::warning::OZET " + " | ".join(f"{c}: {oz(c)}" for c in ("state", "urun", "format_menu", "framed_urun", "framed_deger",
                                                                   "aciklama_frame", "yeni_satir", "kagit_sozu", "materials")))
    # KONTROL (17 Eki adim 3): ilan basina PASS/FAIL; fiyat imzasi CL ile ayni (CL canlida dogrulandi)
    cl_imza = next((t["fiyat_imza"] for t in tab if t["cift"] == "CANCER_LIBRA"), None)
    for t in tab:
        ned = []
        if t["state"] != "active": ned.append(f"state {t['state']}")
        if t["urun"] != 130: ned.append(f"urun {t['urun']}")
        if t["framed_urun"]: ned.append(f"framed {t['framed_urun']}")
        if t["format_menu"] != "Format": ned.append(f"menu {t['format_menu']}")
        if not t["yeni_satir"] or t["frame_disi_satir"]: ned.append(f"frame satir yeni={t['yeni_satir']} disi={t['frame_disi_satir']}")
        if t["kagit_sozu"]: ned.append(f"kagit {t['kagit_sozu']}")
        if t["materials"] != "matte art paper;ink": ned.append(f"materials {t['materials']}")
        if t["fiyat_tutarsiz"] or t["fiyat_imza"] != cl_imza: ned.append("fiyat")
        if t["stok"] != "999": ned.append(f"stok {t['stok']}")
        if t["sku_dolu"] != t["urun"] or t["sku_benzersiz"] != 26 or not t["sku_onek_ok"]:
            ned.append(f"sku dolu {t['sku_dolu']} benzersiz {t['sku_benzersiz']} onek {t['sku_onek_ok']}")
        t["kontrol"] = "PASS" if not ned else "FAIL: " + ", ".join(ned)
    n_pass = sum(1 for t in tab if t["kontrol"] == "PASS")
    print(f"::warning::KONTROL PASS {n_pass}/{len(tab)} | FAIL: " + "; ".join(f"{t['cift']} ({t['kontrol'][6:]})" for t in tab if t["kontrol"] != "PASS")[:900])
    with open(out / "ESKI78_KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tab[0])); w.writeheader(); w.writerows(tab)
    # yapi tanisi (ilk ilan, CL): ozellikler, deger sayilari, *_on_property alanlari (409 "max 2 variations" icin)
    cl = next((r for r in rows if r["cift"] == "CANCER_LIBRA"), rows[0])
    inv = api.get(f"/listings/{cl['listing_id'].strip()}/inventory") or {}
    from collections import Counter, defaultdict
    pv = Counter(); dg = defaultdict(set)
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            pv[(v.get("property_id"), v.get("property_name"), v.get("scale_id"))] += 1
            dg[v.get("property_id")].add(tuple(v.get("values") or []))
    print(f"::warning::YAPI {cl['cift']}: urun {len(inv.get('products') or [])} | ozellik {dict(pv)} | deger_sayisi "
          f"{ {k: len(v) for k, v in dg.items()} } | price_on {inv.get('price_on_property')} qty_on {inv.get('quantity_on_property')} "
          f"sku_on {inv.get('sku_on_property')} ready_on {inv.get('readiness_state_on_property')}")
    fiyat = defaultdict(set); skus = []
    for p in inv.get("products") or []:
        d_ = {v.get("property_id"): (v.get("values") or [""])[0] for v in p.get("property_values") or []}
        o = (p.get("offerings") or [{}])[0]; pr = o.get("price") or {}
        fiyat[(d_.get(514), d_.get(513))].add(round(pr.get("amount", 0) / (pr.get("divisor") or 1), 2))
        skus.append(p.get("sku") or "")
    tek = {f"{k[0]}|{k[1]}": sorted(v) for k, v in sorted(fiyat.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))}
    print(f"::warning::YAPI fiyat (format|boy -> fiyat, renkler ayni mi): {str(tek)[:950]}")
    print(f"::warning::YAPI sku: dolu {sum(1 for x in skus if x)}/{len(skus)} benzersiz {len(set(skus))} ornek {skus[:3]}")
    p0 = (inv.get("products") or [{}])[0]
    print(f"::warning::YAPI urun0: {str({k: p0.get(k) for k in ('sku', 'property_values', 'offerings')})[:900]}")
    aries = next((t for t in tab if t["listing_id"] == "4570031205"), None)
    print(f"::warning::4570031205: {aries}")
    print(f"::warning::BITTI | istek {ham.calls} | kota {ham.remaining}")


if __name__ == "__main__":
    main()
