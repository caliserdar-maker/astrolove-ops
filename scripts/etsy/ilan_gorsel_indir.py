#!/usr/bin/env python3
"""SALT OKUMA: bir ilanin canli galeri gorsellerini (getListingImages, yalniz API anahtari) sirayla indirir
ve galeri yedegini (sira, listing_image_id, alt metin, boyut, url, ilan durumu) galeri.json olarak yazar.
Kullanim: ilan_gorsel_indir.py <ilan_id> <cikti_klasoru>. Etsy'ye yazma yok."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402

lid, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
ilan = api.get(f"/listings/{lid}") or {}
r = api.get(f"/listings/{lid}/images") or {}
gorseller = sorted(r.get("results") or [], key=lambda x: x.get("rank") or 0)
yedek = {"listing_id": int(lid), "okuma_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "state": ilan.get("state"), "title": ilan.get("title"), "gorsel_sayisi": len(gorseller),
         "gorseller": []}
for im in gorseller:
    url = im.get("url_fullxfull")
    b = requests.get(url, timeout=60).content
    (out / f"{im.get('rank'):02d}_{im.get('listing_image_id')}.jpg").write_bytes(b)
    yedek["gorseller"].append({k: im.get(k) for k in (
        "rank", "listing_image_id", "alt_text", "full_width", "full_height", "hex_code", "url_fullxfull")})
    print(f"rank {im.get('rank')} id {im.get('listing_image_id')} {len(b)} bayt "
          f"{im.get('full_width')}x{im.get('full_height')} alt={im.get('alt_text')!r}")
(out / "galeri.json").write_text(json.dumps(yedek, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"state {yedek['state']} | gorsel {len(gorseller)} | kota {api.remaining}")
