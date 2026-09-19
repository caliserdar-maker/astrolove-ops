#!/usr/bin/env python3
"""Tek ilanin canli galerisini okur ve PLAN ile karsilastirir (SALT OKUMA)."""
import json
import os
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import gallery, variation_images, videos  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_RANK3_TO_11"
LID = os.environ.get("OKU_LISTING", "4570031205")


def main():
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    imgs = gallery(api, LID)
    canli = [(str(x.get("listing_image_id")), x.get("rank")) for x in imgs]
    log(f"{LID} canli sira: {canli}")
    isd = pathlib.Path("_work/oku")
    isd.mkdir(parents=True, exist_ok=True)
    y = isd / "PLAN.csv"
    subprocess.run(["rclone", "copyto", f"{DRV}/PLAN.csv", str(y)], check=False)
    import csv
    kayit = None
    with y.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["listing_id"] == LID:
                kayit = r
    once = [kayit[f"once_{i}"] for i in range(1, 14)] if kayit else []
    sonra = [kayit[f"sonra_{i}"] for i in range(1, 14)] if kayit else []
    idler = [i for i, _ in canli]
    tasinan = kayit["rank3_image_id"] if kayit else ""
    cikti = {"listing": LID, "canli": canli, "plan_once": once, "plan_sonra": sonra,
             "tasinan": tasinan,
             "tasinan_canli_konum": idler.index(tasinan) + 1 if tasinan in idler else None,
             "tasinan_plan_konum": sonra.index(tasinan) + 1 if tasinan in sonra else None,
             "canli_eq_sonra": idler == sonra, "canli_eq_once": idler == once,
             "video": [str(v.get("video_id")) for v in videos(api, LID)],
             "varyasyon": [[r.get("value"), str(r.get("image_id"))]
                           for r in variation_images(api, shop, LID)],
             "kota": api.remaining}
    (isd / "OKUMA.json").write_text(json.dumps(cikti, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    subprocess.run(["rclone", "copyto", str(isd / "OKUMA.json"),
                    f"{DRV}/OKUMA_{LID}.json"], check=False)
    print(json.dumps(cikti, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
