#!/usr/bin/env python3
"""GECICI: video/dosya API alan adlarini dogrulamak icin tek ilan JSON dump (salt okur)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
shop_id = os.environ.get("ETSY_SHOP_ID", "")
mask(keystring); mask(shared)
store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
if store.needs_refresh():
    store.refresh()
api = Etsy(store)
lid = os.environ["LISTING_ID"]
print("--- videos ---")
print(json.dumps(api.get(f"/listings/{lid}/videos"), indent=1))
print("--- files ---")
print(json.dumps(api.get(f"/shops/{shop_id}/listings/{lid}/files"), indent=1))
print("--- images (first) ---")
imgs = api.get(f"/listings/{lid}/images")
print(json.dumps((imgs.get("results") or [None])[0], indent=1))
