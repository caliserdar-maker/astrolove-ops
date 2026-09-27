#!/usr/bin/env python3
"""SALT OKUMA: bir ilanin canli galeri gorsellerini (getListingImages, yalniz API anahtari) sirayla indirir.
Kullanim: ilan_gorsel_indir.py <ilan_id> <cikti_klasoru>. Etsy'ye yazma yok."""
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402

lid, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
r = api.get(f"/listings/{lid}/images") or {}
for im in sorted(r.get("results") or [], key=lambda x: x.get("rank") or 0):
    url = im.get("url_fullxfull")
    b = requests.get(url, timeout=60).content
    (out / f"{im.get('rank'):02d}_{im.get('listing_image_id')}.jpg").write_bytes(b)
    print(f"rank {im.get('rank')} id {im.get('listing_image_id')} {len(b)} bayt {im.get('full_width')}x{im.get('full_height')}")
print(f"kota {api.remaining}")
