#!/usr/bin/env python3
"""KULLANIM DISI (24 Eki): 17 Eki akisinin kontrolu; eski78_gorsel_yukle.py yeniden yazildi (alt_metin / cdn_ncc yok), bu betik
artik kosulmaz. Gecmis icin duruyor.
SALT OKUMA geri okuma (Serdar 17 Eki): eski 78 galeri yuklemesinden sonra her ilanda
  - gorsel sayisi = uretim anindaki sayi - 1 (18 -> 17)
  - eski rank 6 gorseli (Four classic frames, uretimdeki id) YOK
  - yeni kartlar dogru sirada: kart rNN -> canli rank {1:1,2:2,3:3,5:5,7:6,8:7,9:8,10:9,12:11,13:12}, CDN NCC >= 0.999
  - alt metinler onayli metin (eski78_gorsel_yukle.alt_metin), digerleri uretimdeki alt metinle ayni
Ilan basina 1 GET (API anahtari) + CDN indirme (kota harcamaz). Yazma yok.
Kullanim: eski78_gorsel_kontrol.py --kaynak DIR(Drive ESKI78_GORSEL_20261017 kopyasi) --out OUT [--ciftler HEPSI]"""
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402

YENI_RANK = {1: 1, 2: 2, 3: 3, 5: 5, 7: 6, 8: 7, 9: 8, 10: 9, 12: 11, 13: 12}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="data/pod/pod78_ids.csv"); ap.add_argument("--ciftler", default="HEPSI")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.ids)))
    if a.ciftler != "HEPSI":
        s = set(a.ciftler.split()); rows = [r for r in rows if r["cift"] in s]
    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    kay = Path(a.kaynak); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); tab = []; t0 = time.time()
    for i, r in enumerate(rows, 1):
        c, lid = r["cift"], r["listing_id"].strip()
        u = json.loads((kay / "_canli" / c / "galeri.json").read_text())["gorseller"]
        g = sorted((api.get(f"/listings/{lid}/images") or {}).get("results") or [], key=lambda x: x.get("rank") or 0)
        ned = []
        if len(g) != len(u) - 1:
            ned.append(f"gorsel {len(g)} (beklenen {len(u) - 1})")
        ids = [x.get("listing_image_id") for x in g]
        r6 = u[5]["listing_image_id"]
        if r6 in ids:
            ned.append("eski r6 duruyor")
        AL = Y.alt_metin(r["a"], r["b"])
        u_alt = [x.get("alt_text") or "" for x in u]
        bek_alt = [AL[k] if k in AL and AL[k] is not None else u_alt[k - 1] for k in range(1, 19) if k != 6]
        son_alt = [x.get("alt_text") or "" for x in g]
        if son_alt != bek_alt:
            ned.append("alt: " + "; ".join(f"r{j + 1}" for j, (s_, e) in enumerate(zip(son_alt, bek_alt)) if s_ != e))
        # degismeyenler ayni id: eski r4, r11, r14-18 -> yeni r4, r10, r13-17
        for eski_r, yeni_r in [(4, 4), (11, 10), (14, 13), (15, 14), (16, 15), (17, 16), (18, 17)]:
            if len(ids) >= yeni_r and ids[yeni_r - 1] != u[eski_r - 1]["listing_image_id"]:
                ned.append(f"r{yeni_r} id degisti")
        with ThreadPoolExecutor(5) as ex:
            nc = dict(zip(YENI_RANK, ex.map(lambda k: Y.cdn_ncc(g[YENI_RANK[k] - 1]["url_fullxfull"], kay / c / f"r{k:02d}.jpg")
                                            if len(g) >= YENI_RANK[k] else -1, YENI_RANK)))
        dus = {k: v for k, v in nc.items() if v < 0.999}
        if dus:
            ned.append(f"NCC {dus}")
        tab.append(dict(cift=c, listing_id=lid, gorsel=len(g), kontrol="PASS" if not ned else "FAIL: " + ", ".join(ned)[:300],
                        ncc_min=min(nc.values()) if nc else None))
        gc = time.time() - t0
        print(f"[{i}/{len(rows)}] {c} {tab[-1]['kontrol']} | gecen {gc:.0f}s kalan ~{gc / i * (len(rows) - i):.0f}s | %{100 * i // len(rows)}", flush=True)
    with open(out / "ESKI78_GORSEL_KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tab[0])); w.writeheader(); w.writerows(tab)
    n = sum(1 for t in tab if t["kontrol"] == "PASS")
    print(f"::warning::GORSEL KONTROL PASS {n}/{len(tab)} | FAIL: " + "; ".join(f"{t['cift']} ({t['kontrol'][6:]})" for t in tab if t["kontrol"] != "PASS")[:900]
          + f" | istek {api.calls} kota {api.remaining}")
    sys.exit(0 if n == len(tab) else 1)


if __name__ == "__main__":
    main()
