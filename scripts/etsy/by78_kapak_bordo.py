#!/usr/bin/env python3
"""BIZIM YILIMIZ: BORDO KARE KAPAK + LAYERS BAGI (Serdar 15 Eki). YAYIN YOK, PATCH/updateListing YOK (yalniz acil state=inactive).

Secilen taslak(lar) (BY78_TASLAKLAR.csv; workflow varsayilani YALNIZ CANCER_LIBRA):
  1) state oku (draft degilse DUR); gorsel listesi (rank, id, boyut) = ONCE
  2) uploadListingImage rank=1 overwrite=true <- Drive v3/<CIFT>/vitrin/00_Kapak.jpg (2400x2400)
  3) state oku; gorsel listesi = SONRA: sayi ve sira ayni, yalniz rank 1 degisti ve 2400x2400, diger id'ler ayni
  4) stil baglari: Layers -> rank 13 gorselinin image_id'si; Starlit/Timeless/First Page/Botanical mevcut bagda kalir (9/10/11/12 olmali)
     (updateVariationImages = POST variation-images; 5 bag birlikte gonderilir)
  5) state oku + baglari oku (Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=13)
"active" -> aninda inactive ve TUM IS DURUR. Kota < 10 -> DUR.
Cikti: <OUT>/BY78_KAPAK_BORDO.json (+ Drive).
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
KARE = (2400, 2400)
BEKLENEN = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 13}
KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10


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
    if not sec:
        raise SystemExit("HATA: CIFTLER bos (bilerek secilmeli)")
    rows = [r for r in csv.DictReader(open(os.environ["TASLAK_CSV"])) if r["cift"] in sec and r.get("listing_id")]
    if len(rows) != len(sec):
        raise SystemExit(f"HATA: taslak listesinde bulunamayan cift: {set(sec) - {r['cift'] for r in rows}}")
    R = {"basla": time.strftime("%H:%M:%S"), "ilan": {}, "olaylar": []}

    def yaz():
        json.dump(R, open(out / "BY78_KAPAK_BORDO.json", "w"), indent=1, ensure_ascii=False, default=str)
        if DOUT:
            subprocess.run(["rclone", "copy", str(out), DOUT, "--include", "/BY78_KAPAK_BORDO.json", "-q"], check=True)

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

    def gorseller(lid):
        for _ in range(5):
            ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
            if all(x.get("full_width") for x in ims):
                break
            time.sleep(8)                                   # yeni gorselin boyutu birkac sn gec yaziliyor
        return [(x.get("rank"), x.get("listing_image_id"), x.get("full_width"), x.get("full_height")) for x in ims]

    def baglar(lid):
        inv = api.get(f"/listings/{lid}/inventory") or {}
        vname = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
                 if v.get("property_id") == P_STYLE and v.get("value_ids")}
        vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
        return vname, {vname.get(v.get("value_id")): v.get("image_id") for v in vis if v.get("property_id") == P_STYLE}

    try:
        for r in rows:
            c, lid = r["cift"], int(r["listing_id"])
            api.lid = lid
            R["ilan"][c] = {"listing_id": lid}
            state(c, "basla")
            once = gorseller(lid)
            R["ilan"][c]["once"] = once
            if len(once) != 13 or [g[0] for g in once] != list(range(1, 14)):
                raise Dur(f"{c} {lid}: baslangic galerisi 13 degil {[g[0] for g in once]}")
            vname, bag_once = baglar(lid)
            id_rank_once = {g[1]: g[0] for g in once}
            R["ilan"][c]["bag_once"] = {a: (i, id_rank_once.get(i)) for a, i in bag_once.items()}

            p = Path(f"_img/{c}_00_Kapak.jpg"); p.parent.mkdir(exist_ok=True)
            subprocess.run(["rclone", "copyto", f"{V3}/{c}/vitrin/00_Kapak.jpg", str(p), "-q"], check=True)
            with open(p, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": ("00_Kapak.jpg", fh, "image/jpeg")},
                              data={"rank": "1", "overwrite": "true"})
            p.unlink()
            state(c, "kapak yuklendi")
            sonra = gorseller(lid)
            R["ilan"][c]["sonra"] = sonra
            degisen = [g[0] for g, h in zip(once, sonra) if g[1] != h[1]]
            if [g[0] for g in sonra] != list(range(1, 14)) or (sonra[0][2], sonra[0][3]) != KARE or degisen != [1]:
                raise Dur(f"{c} {lid}: kapak overwrite beklendigi gibi degil: sira {[g[0] for g in sonra]}, rank1 {sonra[0][2:]}, degisen {degisen}")

            rank_id = {g[0]: g[1] for g in sonra}
            id_rank = {g[1]: g[0] for g in sonra}
            yeni = dict(bag_once)
            yeni["Layers"] = rank_id[13]
            if {a: id_rank.get(i) for a, i in yeni.items()} != BEKLENEN:
                raise Dur(f"{c} {lid}: bag plani beklenenle uyusmuyor {({a: id_rank.get(i) for a, i in yeni.items()})}")
            ad_vid = {a: v for v, a in vname.items()}
            vi = [dict(property_id=P_STYLE, value_id=ad_vid[a], image_id=yeni[a]) for a in BEKLENEN]
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
            state(c, "stil bag")
            _, bag_son = baglar(lid)
            R["ilan"][c]["bag_sonra"] = {a: (i, id_rank.get(i)) for a, i in bag_son.items()}
            if {a: id_rank.get(i) for a, i in bag_son.items()} != BEKLENEN:
                raise Dur(f"{c} {lid}: bag sonrasi {R['ilan'][c]['bag_sonra']}")
            state(c, "son")
            R["ilan"][c]["sonuc"] = "PASS"
            print(f"::warning::{c} {lid} PASS draft | gorsel {len(sonra)} | rank1 {sonra[0][1]} {sonra[0][2]}x{sonra[0][3]} | "
                  + " ".join(f"{a}={i}@{rk}" for a, (i, rk) in R["ilan"][c]["bag_sonra"].items()))
            print(f"::warning::{c} ONCE " + " ".join(f"{g[0]}:{g[1]}:{g[2]}x{g[3]}" for g in once))
            print(f"::warning::{c} SONRA " + " ".join(f"{g[0]}:{g[1]}:{g[2]}x{g[3]}" for g in sonra))
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
