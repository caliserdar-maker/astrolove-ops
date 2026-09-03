#!/usr/bin/env python3
"""SALT OKUR: verilen gorsel/video ID'lerinin Etsy'de hala var olup olmadigini sorar.

Ilandan cikarilmis (silinmis) medya 404 doner; hala shop havuzunda duran gorsel
200 doner. Etsy v3'te video icin tekil GET yoktur; yalniz ilan listesi okunur.
Hicbir yazma/silme yapmaz.

  LISTING_ID   : ilan
  IMAGE_IDS    : virgullu listing_image_id listesi
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

key = os.environ.get("ETSY_API_KEY", "")
shared = os.environ.get("ETSY_SHARED_SECRET", "")
mask(key)
mask(shared)
store = TokenStore(os.environ["TOKEN_FILE"], key, shared)
if store.needs_refresh():
    store.refresh()
api = Etsy(store)
lid = os.environ["LISTING_ID"]

log(f"== ilan {lid} halihazirdaki videolar")
cur = api.get(f"/listings/{lid}/videos", ok404=True) or {}
for v in cur.get("results", []):
    log(f"  video_id={v.get('video_id')} state={v.get('video_state')}")

log("== eski gorsel ID'leri (200 = hala var, 404 = silinmis)")
for iid in [x.strip() for x in os.environ.get("IMAGE_IDS", "").split(",") if x.strip()]:
    r = api.get(f"/listings/{lid}/images/{iid}", ok404=True)
    if r:
        log(f"  {iid}: VAR (200) {r.get('full_width')}x{r.get('full_height')} rank={r.get('rank')}")
    else:
        log(f"  {iid}: YOK (404)")

log("== eski video ID'si (tekil GET yok; ilan listesinde mi diye bakilir)")
old = os.environ.get("OLD_VIDEO_ID", "").strip()
if old:
    ids = [str(v.get("video_id")) for v in cur.get("results", [])]
    log(f"  {old}: {'ILANDA' if old in ids else 'ILANDA DEGIL'} (Etsy v3 tekil video GET sunmaz)")
