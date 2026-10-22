#!/usr/bin/env python3
"""SALT OKUMA: Etsy gunluk kota olcumu (tek hafif GET). Sonuc: stdout + KOTA_LOG.csv satiri."""
import csv
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, TokenStore, mask  # noqa: E402

store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
if store.needs_refresh():
    store.refresh()
r = requests.get(f"{API}/shops/{os.environ['ETSY_SHOP_ID']}", timeout=60,
                 headers={"x-api-key": store.api_key_header, "Authorization": f"Bearer {store.access_token}"})
h = {k: v for k, v in r.headers.items() if any(t in k.lower() for t in ("limit", "remaining", "reset", "retry"))}
zaman = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
print(f"KOTA {zaman} UTC | HTTP {r.status_code} | kalan {h.get('x-remaining-today')} / {h.get('x-limit-per-day')} | {h}")
yol = Path(sys.argv[1] if len(sys.argv) > 1 else "_out/KOTA_LOG.csv")
yeni = not yol.exists()
with yol.open("a", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    if yeni:
        w.writerow(["utc", "kalan", "gunluk_limit", "http"])
    w.writerow([zaman, h.get("x-remaining-today"), h.get("x-limit-per-day"), r.status_code])
