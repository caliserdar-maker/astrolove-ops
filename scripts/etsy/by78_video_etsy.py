#!/usr/bin/env python3
"""BIZIM YILIMIZ: ilan videosu yukleme (Serdar 15 Eki). YAYIN YOK, PATCH/updateListing YOK, SILME YOK (yalniz acil state=inactive).

Secilen taslak(lar) (BY78_TASLAKLAR.csv; workflow varsayilani YALNIZ CANCER_LIBRA):
  1) state oku (draft degilse DUR); gorseller (rank, id, boyut), stil baglari, mevcut video = ONCE
     (ilanda zaten video varsa yukleme YAPILMAZ, DUR: Etsy ilan basina 1 video)
  2) uploadListingVideo <- Drive v3/<CIFT>/vitrin/00_Video.mp4
  3) state oku; video bilgisi (API ne donduruyorsa); gorseller ve 5 stil bagi ONCE ile ayni olmali
"active" -> aninda inactive ve TUM IS DURUR. Kota < 500 -> DUR.
Cikti: <OUT>/BY78_VIDEO_ETSY.json (+ Drive).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, TASLAK_CSV, V3, OUT, DRIVE_OUT, CIFTLER (zorunlu)
"""
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

REF = 4570143815
P_STYLE = 513
BEKLENEN = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 13}
KOTA_MIN = 500


class Dur(Exception):
    pass


class Kilitli(Etsy):
    lid = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings/{lid}/videos$"), ("PATCH", rf"^/shops/\d+/listings/{lid}$")] if lid else []
        if str(REF) in path or not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def post_file(self, path, files, data=None):
        self._izin("POST", path); return super().post_file(path, files, data)

    def patch(self, path, data):
        self._izin("PATCH", path)
        if data != {"state": "inactive"}:
            raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        return super().patch(path, data)

    def post(self, *a, **k):
        raise SystemExit("YASAK: form POST")

    def post_json(self, *a, **k):
        raise SystemExit("YASAK: POST json")

    def put(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def put_json(self, *a, **k):
        raise SystemExit("YASAK: PUT")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Kilitli(store)
    shop = os.environ["ETSY_SHOP_ID"]
    V3, DOUT = os.environ["V3"], os.environ.get("DRIVE_OUT", "")
    sec = os.environ.get("CIFTLER", "").split()
    if not sec:
        raise SystemExit("HATA: CIFTLER bos (bilerek secilmeli)")
    rows = [r for r in csv.DictReader(open(os.environ["TASLAK_CSV"])) if r["cift"] in sec and r.get("listing_id")]
    if len(rows) != len(sec):
        raise SystemExit(f"HATA: taslak listesinde bulunamayan cift: {set(sec) - {r['cift'] for r in rows}}")
    R = {"basla": time.strftime("%H:%M:%S"), "ilan": {}, "olaylar": []}

    def yaz():
        json.dump(R, open(out / "BY78_VIDEO_ETSY.json", "w"), indent=1, ensure_ascii=False, default=str)
        if DOUT:
            subprocess.run(["rclone", "copy", str(out), DOUT, "--include", "/BY78_VIDEO_ETSY.json", "-q"], check=True)

    def state(c, adim):
        st = (api.get(f"/listings/{api.lid}") or {}).get("state")
        R["ilan"][c].setdefault("state", []).append((adim, st))
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            R["olaylar"].append(f"ACIL {c} {api.lid} {adim}: active -> {st2}")
            yaz()
            print(f"::error::ACIL: {c} {api.lid} {adim} sonrasi active -> inactive ({st2}). TUM IS DURDU.")
            raise SystemExit(2)
        if st != "draft":
            raise Dur(f"{c} {api.lid} {adim}: state {st}")
        rem = int(api.remaining) if api.remaining not in (None, "") else None
        if rem is not None and rem < KOTA_MIN:
            raise Dur(f"KOTA {rem} < {KOTA_MIN}")
        return st

    def gorseller(lid):
        ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
        return [(x.get("rank"), x.get("listing_image_id"), x.get("full_width"), x.get("full_height")) for x in ims]

    def baglar(lid, ims):
        id_rank = {g[1]: g[0] for g in ims}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        vname = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
                 if v.get("property_id") == P_STYLE and v.get("value_ids")}
        vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
        return {vname.get(v.get("value_id")): (v.get("image_id"), id_rank.get(v.get("image_id"))) for v in vis if v.get("property_id") == P_STYLE}

    def videolar(lid):
        return (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []

    try:
        for r in rows:
            c, lid = r["cift"], int(r["listing_id"])
            api.lid = lid
            R["ilan"][c] = {"listing_id": lid}
            state(c, "once")
            g0 = gorseller(lid)
            b0 = baglar(lid, g0)
            v0 = videolar(lid)
            R["ilan"][c].update(gorsel_once=g0, bag_once=b0, video_once=v0)
            if v0:
                raise Dur(f"{c} {lid}: ilanda zaten video var ({[v.get('video_id') for v in v0]}); yukleme yapilmadi")
            p = Path(f"_vid/{c}_00_Video.mp4"); p.parent.mkdir(exist_ok=True)
            subprocess.run(["rclone", "copyto", f"{V3}/{c}/vitrin/00_Video.mp4", str(p), "-q"], check=True)
            boyut = p.stat().st_size
            with open(p, "rb") as fh:
                yanit = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("00_Video.mp4", fh, "video/mp4")},
                                      data={"name": f"AstroLoveArt_{c}_video.mp4"}) or {}
            p.unlink()
            R["ilan"][c]["yukleme_yaniti"] = yanit
            R["ilan"][c]["dosya_boyut"] = boyut
            state(c, "video yuklendi")
            v1 = videolar(lid)
            for _ in range(6):                               # video islenirken durum degisebilir
                if v1:
                    break
                time.sleep(10)
                v1 = videolar(lid)
            g1 = gorseller(lid)
            b1 = baglar(lid, g1)
            R["ilan"][c].update(video_sonra=v1, gorsel_sonra=g1, bag_sonra=b1)
            if len(v1) != 1:
                raise Dur(f"{c} {lid}: yukleme sonrasi video sayisi {len(v1)}")
            if g1 != g0:
                raise Dur(f"{c} {lid}: gorseller degisti")
            if b1 != b0 or {a: rk for a, (_, rk) in b1.items()} != BEKLENEN:
                raise Dur(f"{c} {lid}: stil baglari degisti/beklenen degil {b1}")
            st = state(c, "son")
            R["ilan"][c]["sonuc"] = "PASS"
            v = v1[0]
            alanlar = {k_: v.get(k_) for k_ in v if k_ not in ("video_url", "thumbnail_url")}
            print(f"::warning::{c} {lid} PASS state {st} | video {alanlar} | gorsel {len(g1)} ayni | "
                  + " ".join(f"{a}={i}@{rk}" for a, (i, rk) in b1.items()))
    except Dur as e:
        R["dur"] = str(e); yaz()
        print(f"::error::DURDU: {e}"); raise SystemExit(4)
    R["kota_son"] = api.remaining
    yaz()
    print(f"::warning::BITTI {sum(1 for x in R['ilan'].values() if x.get('sonuc') == 'PASS')}/{len(rows)} | kota {api.remaining}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
