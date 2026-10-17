#!/usr/bin/env python3
"""SALT OKUMA: eski 78 ilanin canli galerisi (Serdar 17 Eki, cerceve temizligi gorselleri). Etsy'ye yazma yok.
Ilan basina 1 GET (getListingImages, API anahtari) + Etsy CDN'den url_fullxfull indirme (kota harcamaz).
Cikti: OUT/<CIFT>/galeri.json (18 gorselin rank, listing_image_id, alt_text, boyut, url) + rNN.jpg (yalniz --ranklar).
Kullanim: eski78_gorsel_indir.py --out CANLI [--ids data/pod/pod78_ids.csv] [--ranklar 1,2,3,5,7,8,9,10,12,13] [--ciftler HEPSI]"""
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402

KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--ids", default="data/pod/pod78_ids.csv")
    ap.add_argument("--ranklar", default="1,2,3,5,7,8,9,10,12,13"); ap.add_argument("--ciftler", default="HEPSI")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.ids)))
    if a.ciftler != "HEPSI":
        s = set(a.ciftler.split()); rows = [r for r in rows if r["cift"] in s]
    rk = {int(x) for x in a.ranklar.split(",")}
    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    out = Path(a.out); t0 = time.time(); sorun = []

    def indir(u, p):
        for k in range(3):
            try:
                r = requests.get(u, timeout=90); r.raise_for_status(); p.write_bytes(r.content); return
            except Exception:                                   # noqa: BLE001
                time.sleep(3 * (k + 1))
        raise SystemExit(f"indirilemedi {u}")

    for i, r in enumerate(rows, 1):
        lid, c = r["listing_id"].strip(), r["cift"]
        g = sorted((api.get(f"/listings/{lid}/images") or {}).get("results") or [], key=lambda x: x.get("rank") or 0)
        try:
            if int(api.remaining) < KOTA_MIN:
                raise SystemExit(f"KOTA {api.remaining} < {KOTA_MIN}")
        except (TypeError, ValueError):
            pass
        d = out / c; d.mkdir(parents=True, exist_ok=True)
        man = dict(cift=c, listing_id=lid, gorsel_sayisi=len(g), gorseller=[{k: x.get(k) for k in (
            "rank", "listing_image_id", "alt_text", "full_width", "full_height", "url_fullxfull")} for x in g])
        (d / "galeri.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
        if len(g) != 18:
            sorun.append(f"{c}: {len(g)} gorsel")
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda x: indir(x["url_fullxfull"], d / f"r{x['rank']:02d}.jpg"), [x for x in g if x.get("rank") in rk]))
        gc = time.time() - t0
        print(f"[{i}/{len(rows)}] {c} {len(g)} gorsel | gecen {gc:.0f}s kalan ~{gc / i * (len(rows) - i):.0f}s | %{100 * i // len(rows)} | kota {api.remaining}",
              flush=True)
    print(f"::warning::INDIR {len(rows)} ilan | 18 olmayan: {sorun or 'yok'} | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    main()
