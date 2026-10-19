#!/usr/bin/env python3
"""SALT OKUMA: canli kupa ilaninin videosunu indir (Serdar 19 Eki, poster video v4 referansi). Etsy'ye YAZMA YOK.
En fazla 2 Etsy cagrisi: 1) getListingVideos (API anahtari, public); bossa/erisilemezse 2) ayni uc OAuth ile (taslak ilan).
Video dosyasi Etsy CDN'den indirilir (kota harcamaz). Kota tabani 10: x-remaining-today < 10 ise ikinci cagri yapilmaz.
Cikti: <OUT>/CANLI_KUPA_VIDEO.mp4 + <OUT>/CANLI_KUPA_VIDEO.json (ilan, cagri sayisi, kota, video alanlari).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, TOKEN_FILE (istege bagli, 2. cagri icin). Kullanim: kupa_video_indir.py <listing_id> <OUT>"""
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy, TokenStore  # noqa: E402

KOTA_MIN = 10


class Okur(Etsy):
    def _call(self, method, path, **k):
        if method != "GET":
            raise SystemExit(f"YASAK: {method} {path} (salt okuma)")
        return super()._call(method, path, **k)


def videolar(api, lid):
    try:
        j = api.get(f"/listings/{lid}/videos", ok404=True)
    except SystemExit as e:
        print(f"getListingVideos HATA: {str(e)[:200]}"); return None
    return (j or {}).get("results") if isinstance(j, dict) else None


def main():
    lid, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    R = {"listing_id": int(lid), "cagrilar": []}
    api = Okur(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    v = videolar(api, lid); R["cagrilar"].append({"yol": "GET /listings/{id}/videos (API anahtari)", "kota": api.remaining,
                                                  "sonuc": len(v) if v is not None else "yok"})
    if not v and os.environ.get("TOKEN_FILE"):
        if api.remaining is not None and int(api.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_MIN}")
        st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
        if st.needs_refresh():
            st.refresh()                                              # yenilenen token workflow'da Drive'a geri yazilir
        api2 = Okur(st)
        v = videolar(api2, lid); R["cagrilar"].append({"yol": "GET /listings/{id}/videos (OAuth)", "kota": api2.remaining,
                                                       "sonuc": len(v) if v is not None else "yok"})
    if not v:
        json.dump(R, open(out / "CANLI_KUPA_VIDEO.json", "w"), indent=1); raise SystemExit("HATA: ilanda video bulunamadi")
    vid = v[0]
    R["video"] = {k: vid.get(k) for k in vid if k not in ("video_url", "thumbnail_url")}
    url = vid.get("video_url")
    r = requests.get(url, timeout=120); r.raise_for_status()
    (out / "CANLI_KUPA_VIDEO.mp4").write_bytes(r.content)
    R["indirilen_bayt"] = len(r.content); R["etsy_cagri_sayisi"] = len(R["cagrilar"])
    json.dump(R, open(out / "CANLI_KUPA_VIDEO.json", "w"), indent=1, default=str)
    print(json.dumps(R, default=str))


if __name__ == "__main__":
    main()
