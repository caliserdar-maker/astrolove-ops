#!/usr/bin/env python3
"""BIZIM YILIMIZ 78 TASLAK: KAPAK = YALNIZ POSTER (Serdar 14 Eki 20:00). YAYIN YOK, PATCH YOK (yalniz acil state=inactive).

Her taslak (BY78_TASLAKLAR.csv) icin:
  state oku (draft degilse DUR) -> rank 1 gorseli zaten 2400x3000 poster mi? degilse uploadListingImage rank=1 overwrite=true
  (silme izni listings_d token'da yok; overwrite ayni sirayi degistirir) -> gorselleri oku (13 adet, rank 1 = 2400x3000)
  -> stil bag(lar)i oku (Starlit=9 ... Botanical=13); bozuksa yeniden bagla -> state oku.
  "active" -> aninda inactive ve TUM IS DURUR. Kota < 500 -> DUR.
Cikti: <OUT>/BY78_KAPAK_DEGIS.csv + BY78_KAPAK_RAPOR.json (Drive'a her ilandan sonra).

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, TASLAK_CSV, V3, OUT, DRIVE_OUT, CIFTLER (bos = hepsi)
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
STIL_GORSEL = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Layers": 12, "Botanical": 13}
KOTA_MIN = 500
ISTEK_ILAN = 7
ORNEK = ["CANCER_LIBRA", "LEO_LEO", "SAGITTARIUS_SAGITTARIUS"]


class Dur(Exception):
    pass


class Kilitli(Etsy):
    lid = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings/{lid}/images$"), ("POST", rf"^/shops/\d+/listings/{lid}/variation-images$"),
              ("PATCH", rf"^/shops/\d+/listings/{lid}$")] if lid else []
        if str(REF) in path or not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def post_file(self, path, files, data=None):
        self._izin("POST", path); return super().post_file(path, files, data)

    def post_json(self, path, body):
        self._izin("POST", path); return super().post_json(path, body)

    def patch(self, path, data):
        self._izin("PATCH", path)
        if data != {"state": "inactive"}:
            raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        return super().patch(path, data)

    def post(self, *a, **k):
        raise SystemExit("YASAK: form POST")

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
    rows = [r for r in csv.DictReader(open(os.environ["TASLAK_CSV"])) if r.get("listing_id") and (not sec or r["cift"] in sec)]
    R = {"basla": time.strftime("%H:%M:%S"), "ilan": {}, "olaylar": []}
    S = {}

    def yaz(drive=False):
        f = out / "BY78_KAPAK_DEGIS.csv"
        with open(f, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["cift", "listing_id", "kapak", "gorsel", "stil_bag", "state"])
            w.writeheader()
            for r in rows:
                if r["cift"] in S:
                    w.writerow(S[r["cift"]])
        json.dump(R, open(out / "BY78_KAPAK_RAPOR.json", "w"), indent=1, ensure_ascii=False, default=str)
        if drive and DOUT:
            subprocess.run(["rclone", "copy", str(out), DOUT, "--include", "/BY78_KAPAK_*", "-q"], check=True)

    def state(c, adim):
        st = (api.get(f"/listings/{api.lid}") or {}).get("state")
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            R["olaylar"].append(f"ACIL {c} {api.lid} {adim}: active -> {st2}")
            S.setdefault(c, {})["state"] = f"active->{st2}"
            yaz(True)
            print(f"::error::ACIL: {c} {api.lid} {adim} sonrasi active -> inactive ({st2}). TUM IS DURDU.")
            raise SystemExit(2)
        if st != "draft":
            raise Dur(f"{c} {api.lid} {adim}: state {st}")
        rem = int(api.remaining) if api.remaining not in (None, "") else None
        if rem is not None and rem < KOTA_MIN:
            raise Dur(f"KOTA {rem} < {KOTA_MIN}")
        return st

    api.get(f"/listings/{REF}")                      # kota okuma (salt)
    rem = int(api.remaining or 0)
    gerek = len(rows) * ISTEK_ILAN + KOTA_MIN
    R["kota_bas"] = dict(kalan=rem, gerek=gerek, ilan=len(rows))
    print(f"::warning::KOTA kalan {rem}, gerek {gerek} ({len(rows)} ilan)")
    if rem < gerek:
        yaz(True); print("::error::KOTA YETMEZ, baslanmadi"); raise SystemExit(3)

    Path("_img").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        for i, r in enumerate(rows, 1):
            c, lid = r["cift"], int(r["listing_id"])
            api.lid = lid
            state(c, "basla")
            ims = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
            r1 = next((x for x in ims if x.get("rank") == 1), {})
            if (r1.get("full_width"), r1.get("full_height")) == (2400, 3000):
                kapak = "zaten poster"
            else:
                p = Path(f"_img/{c}.jpg")
                subprocess.run(["rclone", "copyto", f"{V3}/{c}/poster/4_Layers_8x10.jpg", str(p), "-q"], check=True)
                with open(p, "rb") as fh:
                    api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": ("01_Cover.jpg", fh, "image/jpeg")},
                                  data={"rank": "1", "overwrite": "true"})
                p.unlink()
                kapak = "degisti"
                state(c, "kapak")
                ims = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
            ims = sorted(ims, key=lambda x: x.get("rank") or 0)
            ranks = [x.get("rank") for x in ims]
            r1 = ims[0] if ims else {}
            if ranks != list(range(1, 14)) or (r1.get("full_width"), r1.get("full_height")) != (2400, 3000):
                raise Dur(f"{c} {lid}: gorsel sira {ranks}, rank1 {r1.get('full_width')}x{r1.get('full_height')}")
            idrank = {x.get("listing_image_id"): x.get("rank") for x in ims}
            rankid = {v: k_ for k_, v in idrank.items()}
            vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
            inv = api.get(f"/listings/{lid}/inventory") or {}
            vname = {v["value_ids"][0]: v["values"][0] for p_ in inv.get("products") or [] for v in p_.get("property_values") or []
                     if v.get("property_id") == P_STYLE and v.get("value_ids")}
            bag = {v.get("value_id"): idrank.get(v.get("image_id")) for v in vis}
            dogru = len(vis) == 5 and all(STIL_GORSEL.get(vname.get(v)) == rk for v, rk in bag.items())
            if not dogru:
                ad_vid = {a: v for v, a in vname.items()}
                vi = [dict(property_id=P_STYLE, value_id=ad_vid[st], image_id=rankid[rk]) for st, rk in STIL_GORSEL.items()]
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
                state(c, "stil_bag")
                vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
                bag = {v.get("value_id"): idrank.get(v.get("image_id")) for v in vis}
                if not all(STIL_GORSEL.get(vname.get(v)) == rk for v, rk in bag.items()) or len(bag) != 5:
                    raise Dur(f"{c} {lid}: stil bag yeniden kurulamadi {bag}")
                R["olaylar"].append(f"{c}: stil bag yeniden kuruldu")
            st = state(c, "son")
            S[c] = dict(cift=c, listing_id=lid, kapak=kapak, gorsel=len(ims),
                        stil_bag=" ".join(f"{vname.get(v, v)}={rk}" for v, rk in sorted(bag.items(), key=lambda x: x[1])), state=st)
            if c in ORNEK:
                R["ilan"][c] = dict(listing_id=lid, gorsel_sira=[(x.get("rank"), x.get("full_width"), x.get("full_height")) for x in ims],
                                    stil_bag=S[c]["stil_bag"], state=st)
            if i % 5 == 0 or i == len(rows):
                yaz(True)
            el = time.time() - t0
            print(f"{i}/{len(rows)} %{100 * i // len(rows)} {c} {lid} {kapak} | gecen {el / 60:.1f} dk kalan ~{el / i * (len(rows) - i) / 60:.1f} dk | kota {api.remaining}", flush=True)
    except Dur as e:
        R["dur"] = str(e); yaz(True)
        print(f"::error::DURDU: {e}"); raise SystemExit(4)
    R["bitis"] = time.strftime("%H:%M:%S"); R["kota_son"] = api.remaining
    n = sum(1 for x in S.values() if x["state"] == "draft" and x["gorsel"] == 13)
    yaz(True)
    print(f"::warning::KAPAK {n}/{len(rows)} tamam (draft, 13 gorsel, rank1 2400x3000, stil bag dogru) | degisti {sum(1 for x in S.values() if x['kapak'] == 'degisti')} | kota {api.remaining}")
    for c, o in R["ilan"].items():
        print(f"::warning::{c} {o['listing_id']} {o['state']} sira {[x[0] for x in o['gorsel_sira']]} rank1 {o['gorsel_sira'][0][1:]} | {o['stil_bag']}")
    if n != len(rows):
        raise SystemExit(5)


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
