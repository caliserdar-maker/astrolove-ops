#!/usr/bin/env python3
"""
Prodigi maliyet dogrulamasi (SALT OKUMA) - Serdar/Mo, 25 Eyl 2026.

Yalniz POST /v4.0/quotes (CANLI api.prodigi.com; siparis OLUSTURMAZ). Order API cagrisi YOK.
SKU: GLOBAL-HPR-<boy> (order_router.py eslemesi), 16 boy = B plani fiyat tablosu
(scripts/pod/fiyat_b.py, pod-v4 dali, 08af145, Serdar onayi 24 Eyl 2026). Etsy API cagrisi YOK.
Ulkeler US GB DE CA AU TR JP; kargo Budget ve Standard; para birimi USD istenir (donus farkliysa isaretlenir, cevrilmez).
net = fiyat - (0.582 + 0.176 x fiyat) - urun - kargo;  net_offsite = net - 0.15 x fiyat. (vergi ayri sutun, net'e dahil degil)
Cikti: PRODIGI_MALIYET_API.csv, PRODIGI_MALIYET_API_OZET.md, raw/*.json (yalniz teklif yaniti; musteri verisi yok).
Karsilastirma: DIJITAL_78/POD_FIYAT_KAR_TABLOSU_20260924.txt (US detay + 'Cheapest cost incl tax' tablosu).
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_pilot_quote import Api, leak_check, load_key, log  # noqa: E402

# B plani fiyatlari (fiyat_b.py FIYAT, 5 rengin hepsinde ayni)
FIYAT = {
    "8x10": 34.99, "A4": 37.99, "11x14": 42.99, "12x16": 46.99, "A3": 47.99,
    "12x18": 49.99, "16x20": 54.99, "16x24": 57.99, "A2": 57.99, "18x24": 64.99,
    "20x30": 84.99, "24x30": 94.99, "24x32": 99.99, "A1": 99.99, "24x36": 109.99,
    "30x40": 139.99,
}
assert FIYAT["8x10"] == 34.99 and FIYAT["30x40"] == 139.99 and len(FIYAT) == 16   # Serdar referansi
ULKELER = ["US", "GB", "DE", "CA", "AU", "TR", "JP"]
YONTEMLER = {"budget": "Budget", "standard": "Standard"}
ESKI = "gdrive:ASTROLOVE/TEMP/DIJITAL_78/POD_FIYAT_KAR_TABLOSU_20260924.txt"
ALANLAR = ["boyut", "ulke", "kargo_tipi", "urun", "kargo", "vergi", "para_birimi", "uretim_yeri", "fiyat", "net", "net_offsite",
           "sku", "not"]


def para(c):
    try:
        return float((c or {}).get("amount")), (c or {}).get("currency", "")
    except (TypeError, ValueError):
        return None, (c or {}).get("currency", "")


def ayikla(q):
    """quote yaniti -> {yontem: dict(urun, kargo, vergi, para, lab, kaynak)} (yalniz yanittaki alanlar)."""
    out = {}
    for qu in (q or {}).get("quotes") or []:
        m = (qu.get("shipmentMethod") or "").replace(" ", "").lower()
        cs = qu.get("costSummary") or {}
        urun, c1 = para(cs.get("items"))
        kargo, c2 = para(cs.get("shipping"))
        vergi, c3 = para(cs.get("totalTax"))
        kaynak = "costSummary.totalTax"
        if vergi is None:                                   # yedek: kalem + gonderi vergileri toplami
            parcalar = [para(i.get("taxUnitCost"))[0] for i in qu.get("items") or []]
            parcalar += [para(sh.get("tax"))[0] for sh in qu.get("shipments") or []]
            parcalar = [p for p in parcalar if p is not None]
            vergi = round(sum(parcalar), 2) if parcalar else None
            kaynak = "items.taxUnitCost+shipments.tax" if parcalar else "yok"
        labs = []
        for sh in qu.get("shipments") or []:
            fl = sh.get("fulfillmentLocation") or {}
            labs.append(f"{fl.get('countryCode', '')}/{fl.get('labCode', '')}")
        out[m] = dict(urun=urun, kargo=kargo, vergi=vergi, para=c1 or c2 or c3,
                      lab=" ".join(dict.fromkeys(labs)), kaynak=kaynak)
    return out


def hesap(fiyat, urun, kargo):
    net = fiyat - (0.582 + 0.176 * fiyat) - urun - kargo
    return round(net, 2), round(net - 0.15 * fiyat, 2)


def eski_oku(metin):
    """Eski tablo: US detay (urun, kargo, B net) + 'Cheapest cost incl tax' (boy x ulke)."""
    us, ucuz, bolum, basliklar = {}, {}, None, []
    for sat in metin.splitlines():
        m = re.match(r"^(\S+)\s+urun\s+([\d.]+)\s+kargo\s+([\d.]+).*?maliyet\+ek\s+([\d.]+).*\|\s*B\s+([\d.]+)\s+net\s+(-?[\d.]+)\s+ads\s+(-?[\d.]+)", sat)
        if m:
            us[norm(m.group(1))] = dict(urun=float(m.group(2)), kargo=float(m.group(3)), ek=round(float(m.group(4)) - float(m.group(2)) - float(m.group(3)), 2),
                                        b_fiyat=float(m.group(5)), b_net=float(m.group(6)), b_ads=float(m.group(7)))
            continue
        if sat.startswith("Cheapest cost incl tax"):
            bolum = "ucuz"; continue
        if bolum == "ucuz" and sat.startswith("size"):
            basliklar = sat.replace("|", " ").split()[1:8]; continue
        if bolum == "ucuz" and sat.strip() and basliklar:
            p = sat.split("|")[0].split()
            if len(p) == 8:
                ucuz[norm(p[0])] = dict(zip(basliklar, map(float, p[1:])))
    return us, ucuz


def norm(b):
    b = b.strip()
    return b.upper() if b.upper().startswith("A") and len(b) <= 2 else b.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--eski", default="", help="yerel eski tablo (bos = rclone cat)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    out = Path(a.out_dir); (out / "raw").mkdir(parents=True, exist_ok=True)
    api = Api(load_key())
    isler = [(b, u) for b in FIYAT for u in ULKELER]

    def cek(is_):
        b, u = is_
        q, err = api.quote(f"GLOBAL-HPR-{b}", {}, dest=u)
        return b, u, q, err
    with ThreadPoolExecutor(4) as ex:
        sonuc = list(ex.map(cek, isler))
    rows, hatalar = [], []
    for b, u, q, err in sonuc:
        if q:
            (out / "raw" / f"{b}_{u}.json").write_text(json.dumps(q, indent=1))
        m = ayikla(q) if q else {}
        for k, ad in YONTEMLER.items():
            r = {x: "" for x in ALANLAR}
            r.update(boyut=b, ulke=u, kargo_tipi=ad, fiyat=FIYAT[b], sku=f"GLOBAL-HPR-{b}")
            v = m.get(k)
            if not v or v["urun"] is None or v["kargo"] is None:
                r["not"] = err or f"yontem yok (donen: {','.join(m) or '-'})"
                hatalar.append(f"{b} {u} {ad}: {r['not']}")
            else:
                r.update(urun=v["urun"], kargo=v["kargo"], vergi="" if v["vergi"] is None else v["vergi"],
                         para_birimi=v["para"], uretim_yeri=v["lab"])
                if v["para"] != "USD":
                    r["not"] = f"para birimi {v['para']} (cevrilmedi)"
                else:
                    r["net"], r["net_offsite"] = hesap(FIYAT[b], v["urun"], v["kargo"])
                if v["kaynak"] != "costSummary.totalTax":
                    r["not"] = (r["not"] + "; " if r["not"] else "") + f"vergi kaynagi {v['kaynak']}"
            rows.append(r)
        log(f"{b} {u}: " + " | ".join(f"{k} {m[k]['urun']}+{m[k]['kargo']} vergi {m[k]['vergi']} {m[k]['lab']}" for k in YONTEMLER if k in m) + (f" HATA {err}" if err else ""))
    rows.sort(key=lambda r: (list(FIYAT).index(r["boyut"]), ULKELER.index(r["ulke"]), r["kargo_tipi"]))
    with open(out / "PRODIGI_MALIYET_API.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR); w.writeheader(); w.writerows(rows)
    eski_txt = Path(a.eski).read_text(encoding="utf-8") if a.eski else subprocess.run(["rclone", "cat", ESKI], capture_output=True, text=True).stdout
    ozet(rows, hatalar, eski_oku(eski_txt), out)
    leak_check(out)


def ozet(rows, hatalar, eski, out):
    us_eski, ucuz_eski = eski
    tam = [r for r in rows if r["net"] != ""]
    dusuk = [r for r in tam if r["net"] < 3]
    zarar = [r for r in tam if r["net"] < 0]
    off_zarar = [r for r in tam if r["net_offsite"] < 0]
    md = ["# Prodigi maliyet (Quote API, canli, salt okuma) - 16 HPR boy x 7 ulke x Budget/Standard", "",
          f"- satir: {len(rows)}; hesaplanan: {len(tam)}; eksik/hata: {len(hatalar)}",
          f"- net < $3: {len(dusuk)} satir (zarar: {len(zarar)}); offsite dahil zarar: {len(off_zarar)} satir",
          "- net = fiyat - (0.582 + 0.176 x fiyat) - urun - kargo; vergi ayri sutunda, net'e dahil degil.", "",
          "## Net < $3 veya zarar", "", "| boyut | ulke | kargo | urun | kargo | vergi | fiyat | net | net_offsite | lab |", "|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['boyut']} | {r['ulke']} | {r['kargo_tipi']} | {r['urun']} | {r['kargo']} | {r['vergi']} | {r['fiyat']} | **{r['net']}** | {r['net_offsite']} | {r['uretim_yeri']} |"
           for r in dusuk] or ["| - | yok | | | | | | | | |"]
    md += ["", "## Eski tablo (20260924, dogrulanmamis) ile fark", "", "### US Budget: urun / kargo / B fiyatta net", "",
           "Eski net 'maliyet+ek' ile hesaplanmis (urun + kargo + ek pay); bu formulde ek pay yok. 'fark (ek haric)' = API net - (eski net + ek pay).", "",
           "| boyut | urun eski | urun API | kargo eski | kargo API | ek pay (eski) | net eski (B) | net API | fark | fark (ek haric) |", "|---|---|---|---|---|---|---|---|---|---|"]
    idx = {(r["boyut"], r["ulke"], r["kargo_tipi"]): r for r in rows}
    for b in FIYAT:
        e = us_eski.get(b); n = idx.get((b, "US", "Budget"))
        if not e or not n or n["net"] == "":
            md.append(f"| {b} | {e and e['urun']} | {n and n['urun']} | {e and e['kargo']} | {n and n['kargo']} | {e and e['ek']} | {e and e['b_net']} | {n and n['net']} | eksik | |"); continue
        md.append(f"| {b} | {e['urun']} | {n['urun']} | {e['kargo']} | {n['kargo']} | {e['ek']} | {e['b_net']} | {n['net']} | {n['net'] - e['b_net']:+.2f} | {n['net'] - e['b_net'] - e['ek']:+.2f} |")
    md += ["", "### En ucuz toplam (urun + kargo + vergi), Budget/Standard icinden: eski -> API (fark)", "",
           "| boyut | " + " | ".join(ULKELER) + " |", "|---" * (len(ULKELER) + 1) + "|"]
    for b in FIYAT:
        hucre = []
        for u in ULKELER:
            ad = [idx.get((b, u, k)) for k in YONTEMLER.values()]
            top = [r["urun"] + r["kargo"] + (r["vergi"] or 0) for r in ad if r and r["urun"] != "" and r["kargo"] != ""]
            e = (ucuz_eski.get(b) or {}).get(u)
            if not top:
                hucre.append(f"{e} -> eksik"); continue
            m = round(min(top), 2)
            hucre.append(f"{e} -> {m} ({m - e:+.2f})" if e is not None else f"yok -> {m}")
        md.append(f"| {b} | " + " | ".join(hucre) + " |")
    if hatalar:
        md += ["", "## Eksik / hata", ""] + [f"- {h}" for h in hatalar]
    (out / "PRODIGI_MALIYET_API_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log("\n".join(md[:6]))


def self_test():
    q = {"quotes": [{"shipmentMethod": "Budget", "costSummary": {"items": {"amount": "10.00", "currency": "USD"},
                     "shipping": {"amount": "6.85", "currency": "USD"}, "totalTax": {"amount": "0.00", "currency": "USD"}},
                     "shipments": [{"fulfillmentLocation": {"countryCode": "US", "labCode": "us1"}}], "items": [{}]},
                    {"shipmentMethod": "Standard", "costSummary": {"items": {"amount": "10.00", "currency": "USD"},
                     "shipping": {"amount": "9.10", "currency": "USD"}},
                     "shipments": [{"fulfillmentLocation": {"countryCode": "US", "labCode": "us1"}, "tax": {"amount": "1.20"}}],
                     "items": [{"taxUnitCost": {"amount": "0.80"}}]}]}
    m = ayikla(q)
    assert m["budget"]["urun"] == 10.0 and m["budget"]["kargo"] == 6.85 and m["budget"]["vergi"] == 0.0 and m["budget"]["lab"] == "US/us1"
    assert m["standard"]["vergi"] == 2.0 and m["standard"]["kaynak"] == "items.taxUnitCost+shipments.tax"
    assert hesap(34.99, 10.0, 6.85) == (11.4, 6.15), hesap(34.99, 10.0, 6.85)
    eski = ("US detail\n8X10   urun   10.0 kargo   6.85 (Budget) maliyet+ek  21.85 | fiyat   29.99 ucret  5.86 net   2.28 ads  -2.22 | B   34.99 net   6.40 ads   1.15\n\n"
            "Cheapest cost incl tax (Prodigi) by country (USD)\nsize       US      GB      DE      CA      AU      TR      JP     | lab\n"
            "8X10     16.85   13.39   15.69   13.14   21.07   16.08   29.42  | lab: US,GB,NL,GB,AU,NL,AU\n")
    us, uc = eski_oku(eski)
    assert us["8x10"]["b_net"] == 6.40 and us["8x10"]["ek"] == 5.0 and uc["8x10"]["JP"] == 29.42, (us, uc)
    print("self-test PASS")


if __name__ == "__main__":
    main()
