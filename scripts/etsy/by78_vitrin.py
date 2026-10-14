#!/usr/bin/env python3
"""BIZIM YILIMIZ 78 TASLAK: VITRIN GORSELLERI (Serdar 14 Eki). YAYIN YOK, PATCH YOK (yalniz acil state=inactive).

Takip notu (14 Eki): SILME YOK (token'da listings_d yok). uploadListingImage ayni rank'e overwrite=true:
  rank 1 = vitrin/01_Cover.jpg, 9 = Style_Starlit, 10 = Style_Timeless, 11 = Style_FirstPage, 12 = Style_Botanical,
  13 = vitrin/01_Cover.jpg (Layers; silinemedigi icin). Galeri 13 gorsel kalir.
Stil baglari: Starlit=9, Timeless=10, First Page=11, Botanical=12, Layers=1.
Kontrol (her ilan): 13 gorsel, sira 1..13, rank 1 ve 9-13 dikey 2400x3000, 2-8 yatay 3200x2400, 9-13 yeni gorsel (id degisti),
  5 bag dogru, state draft. Ilk ilanda overwrite beklendigi gibi calismazsa (eski gorsel kaldi, sira kaydi, ekstra gorsel) DUR.
Asamalar BY78_VITRIN.csv'de: gorsel -> bag -> tamam (tekrar kosuda kaldigi yerden; overwrite tekrar edilebilir).
Her yazma adimindan sonra state okunur; "active" -> aninda inactive ve TUM IS DURUR. Kota < 500 -> DUR.

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
YUKLE = [(1, "01_Cover.jpg"), (9, "Style_Starlit.jpg"), (10, "Style_Timeless.jpg"), (11, "Style_FirstPage.jpg"),
         (12, "Style_Botanical.jpg"), (13, "01_Cover.jpg")]
DIKEY, YATAY = (2400, 3000), (3200, 2400)
BAG = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 1}
ASAMA = ["", "gorsel", "bag", "tamam"]
KOTA_MIN = 500
ISTEK_ILAN = 14
ORNEK = ["CANCER_LIBRA", "LEO_LEO", "SAGITTARIUS_SAGITTARIUS"]


class Dur(Exception):
    pass


class Kilitli(Etsy):
    lid = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings/{lid}/images$"),
              ("POST", rf"^/shops/\d+/listings/{lid}/variation-images$"), ("PATCH", rf"^/shops/\d+/listings/{lid}$")] if lid else []
        if str(REF) in path or not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def post_file(self, path, files, data=None):
        self._izin("POST", path); return super().post_file(path, files, data)

    def post_json(self, path, body):
        self._izin("POST", path); return super().post_json(path, body)

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE (listings_d yok; overwrite kullanilir)")

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
    dur_f = out / "BY78_VITRIN.csv"
    S = {r["cift"]: r for r in csv.DictReader(open(dur_f))} if dur_f.exists() else {}
    R = {"basla": time.strftime("%H:%M:%S"), "ilan": {}, "olaylar": []}

    def yaz(drive=False):
        with open(dur_f, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["cift", "listing_id", "asama", "gorsel", "stil_bag", "id_degisti", "state"])
            w.writeheader()
            for c in sorted(S):
                w.writerow({k_: S[c].get(k_, "") for k_ in ("cift", "listing_id", "asama", "gorsel", "stil_bag", "id_degisti", "state")})
        json.dump(R, open(out / "BY78_VITRIN_RAPOR.json", "w"), indent=1, ensure_ascii=False, default=str)
        if drive and DOUT:
            subprocess.run(["rclone", "copy", str(out), DOUT, "--include", "/BY78_VITRIN*", "-q"], check=True)

    def state(c, adim):
        st = (api.get(f"/listings/{api.lid}") or {}).get("state")
        S[c]["state"] = st
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            S[c]["state"] = f"active->{st2}"
            R["olaylar"].append(f"ACIL {c} {api.lid} {adim}: active -> {st2}")
            yaz(True)
            print(f"::error::ACIL: {c} {api.lid} {adim} sonrasi active -> inactive ({st2}). TUM IS DURDU.")
            raise SystemExit(2)
        if st != "draft":
            raise Dur(f"{c} {api.lid} {adim}: state {st}")
        rem = int(api.remaining) if api.remaining not in (None, "") else None
        if rem is not None and rem < KOTA_MIN:
            raise Dur(f"KOTA {rem} < {KOTA_MIN} ({c} {adim} sonrasi; tekrar kosuda kaldigi yerden)")

    def gorseller(lid):
        return sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)

    def indir(c, ad):
        p = Path(f"_img/{c}_{ad}")
        subprocess.run(["rclone", "copyto", f"{V3}/{c}/vitrin/{ad}", str(p), "-q"], check=True)
        return p

    def yukle(c, lid, ad, rank, overwrite=False):
        p = indir(c, ad)
        d = {"rank": str(rank)}
        if overwrite:
            d["overwrite"] = "true"
        with open(p, "rb") as fh:
            x = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (ad, fh, "image/jpeg")}, data=d) or {}
        p.unlink()
        return x

    api.get(f"/listings/{REF}")
    rem = int(api.remaining or 0)
    kalan = sum(1 for r in rows if S.get(r["cift"], {}).get("asama") != "tamam")
    R["kota_bas"] = dict(kalan=rem, ilan=kalan, tum_is_icin_gerek=kalan * ISTEK_ILAN + KOTA_MIN)
    print(f"::warning::KOTA kalan {rem}; {kalan} ilan x {ISTEK_ILAN} + {KOTA_MIN} = {kalan * ISTEK_ILAN + KOTA_MIN}"
          f"{' (YETMEZ: kota 500e inince durur, tekrar kosu kaldigi yerden)' if rem < kalan * ISTEK_ILAN + KOTA_MIN else ''}")
    if rem < KOTA_MIN + ISTEK_ILAN:
        yaz(True); print("::error::KOTA YETMEZ, baslanmadi"); raise SystemExit(3)

    Path("_img").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        for i, r in enumerate(rows, 1):
            c, lid = r["cift"], int(r["listing_id"])
            S.setdefault(c, {"cift": c, "listing_id": lid, "asama": ""})
            if S[c].get("asama") == "tamam":
                continue
            api.lid = lid
            asama = S[c].get("asama") or ""
            gec = lambda a: ASAMA.index(asama) < ASAMA.index(a)   # noqa: E731
            state(c, "basla")
            ims = gorseller(lid)

            if gec("gorsel"):
                if [x.get("rank") for x in ims] != list(range(1, 14)):
                    raise Dur(f"{c} {lid}: baslangic galerisi 13 degil {[x.get('rank') for x in ims]}")
                once = {x.get("rank"): x.get("listing_image_id") for x in ims}
                for rk, ad in YUKLE:
                    yukle(c, lid, ad, rk, overwrite=True)
                asama = S[c]["asama"] = "gorsel"
                state(c, "gorsel")
                ims = gorseller(lid)
                sonra = {x.get("rank"): x.get("listing_image_id") for x in ims}
                S[c]["id_degisti"] = " ".join(str(rk) for rk, _ in YUKLE if once.get(rk) != sonra.get(rk))
            for _ in range(4):                                # Etsy yeni gorselin boyutunu birkac sn gec yaziyor (20:23 PISCES_SAGITTARIUS)
                if all(x.get("full_width") for x in ims):
                    break
                time.sleep(8)
                ims = gorseller(lid)
            ranks = [x.get("rank") for x in ims]
            boy = {x.get("rank"): (x.get("full_width"), x.get("full_height")) for x in ims}
            hata = [rk for rk in range(1, 14) if boy.get(rk) != (DIKEY if rk in (1, 9, 10, 11, 12, 13) else YATAY)]
            bos = [rk for rk in hata if boy.get(rk) == (None, None) and rk in dict(YUKLE)]
            if hata and bos == hata and ranks == list(range(1, 14)):   # boyutu hic yazilmamis gorsel: o rank'i 1 kez yeniden yukle
                for rk in bos:
                    yukle(c, lid, dict(YUKLE)[rk], rk, overwrite=True)
                state(c, f"yeniden yukleme {bos}")
                R["olaylar"].append(f"{c}: rank {bos} boyutsuzdu, yeniden yuklendi")
                for _ in range(4):
                    ims = gorseller(lid)
                    if all(x.get("full_width") for x in ims):
                        break
                    time.sleep(8)
                ranks = [x.get("rank") for x in ims]
                boy = {x.get("rank"): (x.get("full_width"), x.get("full_height")) for x in ims}
                hata = [rk for rk in range(1, 14) if boy.get(rk) != (DIKEY if rk in (1, 9, 10, 11, 12, 13) else YATAY)]
            if ranks != list(range(1, 14)) or hata:
                raise Dur(f"{c} {lid}: overwrite beklendigi gibi degil: sira {ranks}, boyut hatali rank {hata} {[boy.get(r) for r in hata]}")
            rankid = {x.get("rank"): x.get("listing_image_id") for x in ims}
            idrank = {v: k_ for k_, v in rankid.items()}
            inv = api.get(f"/listings/{lid}/inventory") or {}
            vname = {v["value_ids"][0]: v["values"][0] for p_ in inv.get("products") or [] for v in p_.get("property_values") or []
                     if v.get("property_id") == P_STYLE and v.get("value_ids")}
            ad_vid = {a: v for v, a in vname.items()}

            if gec("bag"):
                vi = [dict(property_id=P_STYLE, value_id=ad_vid[a], image_id=rankid[rk]) for a, rk in BAG.items()]
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
                asama = S[c]["asama"] = "bag"
                state(c, "bag")

            vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
            bag = {vname.get(v.get("value_id")): idrank.get(v.get("image_id")) for v in vis}
            if bag != BAG:
                raise Dur(f"{c} {lid}: stil bag {bag}")
            S[c].update(asama="tamam", gorsel=len(ims), stil_bag=" ".join(f"{a}={rk}" for a, rk in sorted(bag.items(), key=lambda x: x[1])))
            if c in ORNEK:
                R["ilan"][c] = dict(listing_id=lid, gorsel_sira=[(x.get("rank"), x.get("full_width"), x.get("full_height")) for x in ims],
                                    stil_bag=S[c]["stil_bag"], id_degisti=S[c].get("id_degisti"), state=S[c]["state"])
            if i % 5 == 0 or i == len(rows):
                yaz(True)
            el = time.time() - t0
            print(f"{i}/{len(rows)} %{100 * i // len(rows)} {c} {lid} tamam | gecen {el / 60:.1f} dk kalan ~{el / i * (len(rows) - i) / 60:.1f} dk | kota {api.remaining}", flush=True)
    except Dur as e:
        R["dur"] = str(e); yaz(True)
        print(f"::error::DURDU: {e}"); raise SystemExit(4)
    except BaseException:
        yaz(True); raise
    R["bitis"] = time.strftime("%H:%M:%S"); R["kota_son"] = api.remaining
    n = sum(1 for r in rows if S.get(r["cift"], {}).get("asama") == "tamam" and S[r["cift"]].get("state") == "draft")
    yaz(True)
    print(f"::warning::VITRIN {n}/{len(rows)} tamam (draft, 13 gorsel, 1+9-13 dikey, 2-8 yatay, 5 bag) | kota {api.remaining}")
    for c, o in R["ilan"].items():
        print(f"::warning::{c} {o['listing_id']} {o['state']} sira {[x[0] for x in o['gorsel_sira']]} | {o['stil_bag']}")
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
