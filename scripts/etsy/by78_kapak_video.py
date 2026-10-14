#!/usr/bin/env python3
"""BIZIM YILIMIZ 77 TASLAK: bordo kare kapak + Layers bagi 13 + video, tek kosu (Serdar 15 Eki).
YAYIN YOK, PATCH/updateListing YOK, SILME YOK (yalniz acil durumda state=inactive).

Ilan basina istek (hedef 6):
  1) getListing?includes=Images,Inventory,Videos   state + gorseller + Style value_id + mevcut video
     state draft degilse ilan ATLANIR (raporlanir); "active" ise aninda inactive ve TUM IS DURUR
  2) uploadListingImage rank=1 overwrite=true      00_Kapak.jpg  (rank 1 zaten 2400x2400 ise atlanir)
  3) updateVariationImages                          Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=13
  4) uploadListingVideo                             00_Video.mp4  (ilanda video varsa atlanir)
  5) getListing?includes=Images,Videos              son state + 13 gorsel, rank 1 2400x2400, 1 video
  6) getListingVariationImages                      5 bag
  Bos boyut (None): 8 sn bekleyip yeniden okunur (en fazla 4); hala bossa o rank 1 kez yeniden yuklenir.
Kota < 500 olursa ilan bitince DURUR; BY78_KAPAK_VIDEO.csv'de tamam olanlar tekrar kosuda atlanir.
CANCER_LIBRA (4595350971) her zaman haric.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, TASLAK_CSV, V3, OUT, DRIVE_OUT,
       CIFTLER ("HEPSI" = CANCER_LIBRA haric tum taslaklar CSV sirasiyla; ya da bosluklu cift listesi)
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
HARIC = {"CANCER_LIBRA"}
P_STYLE = 513
KARE, DIKEY, YATAY = (2400, 2400), (2400, 3000), (3200, 2400)
BAG = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 13}
KOTA_MIN = 500
ISTEK_TAHMIN = 6
ALAN = ["cift", "listing_id", "sonuc", "kapak_id", "video_id", "bag", "state", "istek", "not"]


class Dur(Exception):
    pass


class Atla(Exception):
    pass


class Kilitli(Etsy):
    lid = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings/{lid}/images$"), ("POST", rf"^/shops/\d+/listings/{lid}/variation-images$"),
              ("POST", rf"^/shops/\d+/listings/{lid}/videos$"), ("PATCH", rf"^/shops/\d+/listings/{lid}$")] if lid else []
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


def boy(x):
    return (x.get("full_width"), x.get("full_height"))


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
        raise SystemExit("HATA: CIFTLER bos (HEPSI ya da cift listesi bilerek verilmeli)")
    tum = [r for r in csv.DictReader(open(os.environ["TASLAK_CSV"])) if r.get("listing_id") and r["cift"] not in HARIC]
    rows = tum if sec == ["HEPSI"] else [r for r in tum if r["cift"] in sec]
    if sec != ["HEPSI"] and len(rows) != len(sec):
        raise SystemExit(f"HATA: bulunamayan/haric cift: {set(sec) - {r['cift'] for r in rows}}")
    csv_f = out / "BY78_KAPAK_VIDEO.csv"
    S = {r["cift"]: r for r in csv.DictReader(open(csv_f))} if csv_f.exists() else {}
    R = {"basla": time.strftime("%H:%M:%S"), "olaylar": []}

    def yaz():
        with open(csv_f, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=ALAN, extrasaction="ignore")
            w.writeheader()
            for r in tum:
                if r["cift"] in S:
                    w.writerow(S[r["cift"]])
        json.dump(R, open(out / "BY78_KAPAK_VIDEO.json", "w"), indent=1, ensure_ascii=False, default=str)
        if DOUT:
            subprocess.run(["rclone", "copy", str(out), DOUT, "--include", "/BY78_KAPAK_VIDEO*", "-q"], check=True)

    def acil(c, lid, adim):
        api.patch(f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
        st2 = (api.get(f"/listings/{lid}") or {}).get("state")
        R["olaylar"].append(f"ACIL {c} {lid} {adim}: active -> {st2}")
        S[c] = dict(cift=c, listing_id=lid, sonuc="ACIL", state=f"active->{st2}", not_=adim)
        yaz()
        print(f"::error::ACIL: {c} {lid} {adim} sonrasi active -> inactive ({st2}). TUM IS DURDU.")
        raise SystemExit(2)

    def oku(lid, inc):
        L = api.get(f"/listings/{lid}", params={"includes": inc}) or {}
        ims = sorted(L.get("images") or [], key=lambda x: x.get("rank") or 0)
        return L, ims

    def indir(c, ad):
        p = Path(f"_dl/{c}_{ad}"); p.parent.mkdir(exist_ok=True)
        subprocess.run(["rclone", "copyto", f"{V3}/{c}/vitrin/{ad}", str(p), "-q"], check=True)
        return p

    api.get(f"/listings/{REF}")                       # kota okuma (salt)
    rem = int(api.remaining or 0)
    kalan = [r for r in rows if S.get(r["cift"], {}).get("sonuc") != "TAMAM"]
    gerek = len(kalan) * ISTEK_TAHMIN + KOTA_MIN
    R["kota_bas"] = dict(kalan_kota=rem, ilan=len(kalan), tahmini_istek=len(kalan) * ISTEK_TAHMIN, gerek=gerek, sigar=rem >= gerek)
    print(f"::warning::KOTA kalan {rem} | {len(kalan)} ilan x ~{ISTEK_TAHMIN} = {len(kalan) * ISTEK_TAHMIN} istek + taban {KOTA_MIN} = {gerek} | "
          f"{'SIGAR' if rem >= gerek else 'SIGMAZ (taban 500e inince durur, tekrar kosuda kaldigi yerden)'}")
    if rem < KOTA_MIN + ISTEK_TAHMIN:
        yaz(); print("::error::KOTA YETMEZ, baslanmadi"); raise SystemExit(3)

    t0 = time.time()
    try:
        for i, r in enumerate(rows, 1):
            c, lid = r["cift"], int(r["listing_id"])
            if S.get(c, {}).get("sonuc") == "TAMAM":
                continue
            api.lid = lid
            n0 = api.calls
            try:
                # 1) state + gorseller + value_id + video
                L, ims = oku(lid, "Images,Inventory,Videos")
                st = L.get("state")
                if st == "active":
                    acil(c, lid, "basla")
                if st != "draft":
                    raise Atla(f"state {st}")
                if [x.get("rank") for x in ims] != list(range(1, 14)):
                    raise Atla(f"baslangic gorsel sirasi {[x.get('rank') for x in ims]}")
                rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
                vid = {v["values"][0]: v["value_ids"][0] for p in (L.get("inventory") or {}).get("products") or []
                       for v in p.get("property_values") or [] if v.get("property_id") == P_STYLE and v.get("value_ids")}
                if sorted(vid) != sorted(BAG):
                    raise Atla(f"Style value_id eksik {sorted(vid)}")
                # 2) kapak
                if boy(ims[0]) != KARE:
                    p = indir(c, "00_Kapak.jpg")
                    with open(p, "rb") as fh:
                        api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": ("00_Kapak.jpg", fh, "image/jpeg")},
                                      data={"rank": "1", "overwrite": "true"})
                    p.unlink()
                # 3) stil baglari (rank 9-13 overwrite edilmedi; id'ler 1. okumadan)
                vi = [dict(property_id=P_STYLE, value_id=vid[a], image_id=rank_id[rk]) for a, rk in BAG.items()]
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
                # 4) video
                if not (L.get("videos") or []):
                    p = indir(c, "00_Video.mp4")
                    with open(p, "rb") as fh:
                        api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("00_Video.mp4", fh, "video/mp4")},
                                      data={"name": f"AstroLoveArt_{c}_video.mp4"})
                    p.unlink()
                # 5) son okuma
                L2, ims2 = oku(lid, "Images,Videos")
                if L2.get("state") == "active":
                    acil(c, lid, "son")
                bos = 0
                while not all(x.get("full_width") for x in ims2) and bos < 4:
                    time.sleep(8); bos += 1
                    L2, ims2 = oku(lid, "Images,Videos")
                if (ims2[0].get("full_width") if ims2 else 1) is None:      # hala bos: rank 1 bir kez yeniden yukle
                    p = indir(c, "00_Kapak.jpg")
                    with open(p, "rb") as fh:
                        api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": ("00_Kapak.jpg", fh, "image/jpeg")},
                                      data={"rank": "1", "overwrite": "true"})
                    p.unlink()
                    R["olaylar"].append(f"{c}: rank 1 boyutsuzdu, yeniden yuklendi")
                    time.sleep(8)
                    L2, ims2 = oku(lid, "Images,Videos")
                hata = []
                if L2.get("state") != "draft":
                    hata.append(f"state {L2.get('state')}")
                if [x.get("rank") for x in ims2] != list(range(1, 14)):
                    hata.append(f"sira {[x.get('rank') for x in ims2]}")
                if ims2 and boy(ims2[0]) != KARE:
                    hata.append(f"rank1 {boy(ims2[0])}")
                yanlis = [x.get("rank") for x in ims2[1:] if boy(x) != (YATAY if x.get("rank") <= 8 else DIKEY)]
                if yanlis:
                    hata.append(f"boyut hatali rank {yanlis}")
                vids = L2.get("videos") or []
                if len(vids) != 1:
                    hata.append(f"video {len(vids)}")
                # 6) baglar
                vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
                id_rank = {x.get("listing_image_id"): x.get("rank") for x in ims2}
                ad = {v: a for a, v in vid.items()}
                bag = {ad.get(v.get("value_id")): id_rank.get(v.get("image_id")) for v in vis if v.get("property_id") == P_STYLE}
                if bag != BAG:
                    hata.append(f"bag {bag}")
                S[c] = dict(cift=c, listing_id=lid, sonuc="HATA" if hata else "TAMAM",
                            kapak_id=ims2[0].get("listing_image_id") if ims2 else "", video_id=vids[0].get("video_id") if vids else "",
                            bag=" ".join(f"{a}={rk}" for a, rk in sorted(bag.items(), key=lambda x: x[1] or 0)),
                            state=L2.get("state"), istek=api.calls - n0, not_="; ".join(hata))
                S[c]["not"] = S[c].pop("not_")
            except Atla as e:
                S[c] = dict(cift=c, listing_id=lid, sonuc="ATLANDI", istek=api.calls - n0, **{"not": str(e)})
                print(f"::warning::ATLANDI {c} {lid}: {e}")
            yaz()
            el = time.time() - t0
            print(f"{i}/{len(rows)} %{100 * i // len(rows)} {c} {lid} {S[c]['sonuc']} istek {S[c]['istek']} | gecen {el / 60:.1f} dk "
                  f"kalan ~{el / i * (len(rows) - i) / 60:.1f} dk | kota {api.remaining}", flush=True)
            if api.remaining not in (None, "") and int(api.remaining) < KOTA_MIN:
                raise Dur(f"KOTA {api.remaining} < {KOTA_MIN} ({c} sonrasi); tekrar kosuda kaldigi yerden")
    except Dur as e:
        R["dur"] = str(e); yaz()
        print(f"::error::DURDU: {e}"); raise SystemExit(4)
    R["bitis"] = time.strftime("%H:%M:%S"); R["kota_son"] = api.remaining
    yaz()
    secili = [S.get(r["cift"], {}) for r in rows]
    tamam = sum(1 for x in secili if x.get("sonuc") == "TAMAM")
    istekler = [int(x["istek"]) for x in secili if x.get("sonuc") == "TAMAM" and str(x.get("istek", "")).isdigit()]
    print(f"::warning::BITTI {tamam}/{len(rows)} TAMAM | istek/ilan {min(istekler) if istekler else '-'}-{max(istekler) if istekler else '-'} | "
          f"kota {api.remaining} | sorunlu: {[(x.get('cift'), x.get('sonuc'), x.get('not')) for x in secili if x.get('sonuc') != 'TAMAM']}")
    for x in secili[:3]:
        print(f"::warning::{x.get('cift')} {x.get('listing_id')} {x.get('sonuc')} kapak {x.get('kapak_id')} video {x.get('video_id')} | {x.get('bag')} | {x.get('state')} | istek {x.get('istek')}")
    if tamam != len(rows):
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
