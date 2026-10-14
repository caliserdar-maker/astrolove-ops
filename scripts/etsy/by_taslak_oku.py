#!/usr/bin/env python3
"""SALT OKUR: taslak ilanin aciklamasini CSV ile karsilastirir (html.unescape sonrasi) -> <OUT>/ACIKLAMA_FARK.json. Yazma YOK."""
import csv, difflib, html, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
mask(k); mask(s)
store = TokenStore(os.environ["TOKEN_FILE"], k, s)
if store.needs_refresh():
    store.refresh()
api = Etsy(store)
lid = os.environ["LISTING_ID"]
L = api.get(f"/listings/{lid}") or {}
row = next(r for r in csv.DictReader(open(os.environ["CSV"], encoding="utf-8")) if r["cift"] == "CANCER_LIBRA")
a, b = row["aciklama"], L.get("description") or ""
fark = [d for d in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)][:60]
R = dict(state=L.get("state"), ham_ayni=a == b, strip_ayni=a.strip() == b.strip(), unescape_ayni=a.strip() == html.unescape(b).strip(),
         csv_uzunluk=len(a), etsy_uzunluk=len(b), fark=fark)
out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
json.dump(R, open(out / "ACIKLAMA_FARK.json", "w"), indent=1, ensure_ascii=False)
print(f"::warning::state={R['state']} ham={R['ham_ayni']} strip={R['strip_ayni']} unescape={R['unescape_ayni']} uzunluk {len(a)}/{len(b)} fark_satir={len(fark)}")
