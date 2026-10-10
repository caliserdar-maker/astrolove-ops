#!/usr/bin/env python3
"""47e: kategori tam yol adlari (SALT OKUR, etsy-arama, 10 Eki 2026 gece). Tek GET: /seller-taxonomy/nodes.
Kullanim: python3 arama_47e.py <47d_RAKIP_ILAN_ALANLAR.csv> <cikti.csv>"""
import csv
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from arama_oku import taxonomy_paths  # noqa: E402

BIZIM = 121


def run(api, rakip_csv, cikti):
    say = Counter(str(r.get("taxonomy_id") or "").strip() for r in csv.DictReader(open(rakip_csv, encoding="utf-8-sig")))
    say.pop("", None)
    yollar = {str(k): v for k, v in taxonomy_paths((api.get("/seller-taxonomy/nodes") or {}).get("results") or []).items()}
    ids = sorted(set(say) | {str(BIZIM)}, key=lambda x: (-say.get(x, 0), int(x) if x.isdigit() else 0))
    with open(cikti, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["taxonomy_id", "tam_yol", "rakip_ilan_sayisi"])
        for t in ids:
            w.writerow([t, yollar.get(t, "agacta yok") + (" (bizim 78 ilan)" if t == str(BIZIM) else ""), say.get(t, 0)])
    eksik = sum(1 for t in ids if t not in yollar)
    log(f"SONUC: {len(ids)} satir, agac dugum {len(yollar)}, agacta yok {eksik}, API cagri {api.calls}; Etsy yazma 0")
    return 0


def main():
    key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    if not key or not secret or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    return run(Etsy(store), sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    sys.exit(main())
