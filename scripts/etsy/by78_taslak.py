#!/usr/bin/env python3
"""BIZIM YILIMIZ 78 TASLAK (14 Eki 2026, Takip gorevi, Serdar onayi). YAYIN YOK, PATCH YOK (yalniz acil state=inactive).

Akis:
  0) canli CANCER_LIBRA (4570143815) OKUNUR: readiness + nitelikler (Holiday HARIC 8 nitelik). Kota kapisi.
  1) eski CANCER_LIBRA taslagi (ESKI_ID) yalniz state=draft ise SILINIR.
  2) 78 cift (CSV sirasi), her cift icin asamalar; her asamadan sonra state okunur:
       olustur (tek POST, tek deneme) -> envanter (Style x Format, fiyat Format'a gore) -> 13 gorsel ->
       varyasyon gorselleri (Style -> 09..13) -> kisisellestirme (5 kutu) -> 8 nitelik -> tamam
     "active" -> aninda inactive ve TUM IS DURUR. Kota < KOTA_MIN -> DUR.
  3) <OUT>/BY78_TASLAKLAR.csv (cift, listing_id, asama, state, link) Drive'a: olusturma aninda ve her cift bitince.
     Tekrar kosuda: CSV'deki ilan kaldigi asamadan devam eder; ayni baslikli taslak varsa o kullanilir (cift ilan YOK).
  4) <OUT>/BY78_RAPOR.json: 3 ornek ilanin tam dogrulamasi.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, CSV, V3 (rclone yolu .../BIZIM_YILIMIZ_78_20261014_v3),
       OUT, DRIVE_OUT (rclone klasoru), ESKI_ID, CIFTLER (bos = 78)
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import requests  # noqa: E402
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402

REF = 4570143815
SECTION_ID = 60895624
SHIP, RET, TAX, PARTNER = 314711751541, 1513990287785, 121, 5817638
WHO, WHEN = "i_did", "made_to_order"
MATERIALS = ["matte paper", "ink"]
HARIC_NITELIK = {"Holiday"}
STYLES = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]
FORMATS = [("Digital card 5x7", 5.00), ("Digital file 8x10", 9.00), ("Shipped print 8x10", 29.00)]
P_STYLE, P_FORMAT = 513, 514
GALERI = ["01_Cover", "02_Shared_Symbol", "03_Formats", "04_Five_Styles", "05_Layers_Material", "06_Personalization",
          "07_Size_Gift_Scene", "08_Free_Preview", "09_Style_Starlit", "10_Style_Timeless", "11_Style_FirstPage", "12_Style_Layers",
          "13_Style_Botanical"]
STIL_GORSEL = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Layers": 12, "Botanical": 13}   # rank
ASAMA = ["olusturuldu", "envanter", "gorseller", "varyasyon_gorsel", "kisisel", "nitelik", "tamam"]
ISTEK_ILAN = 31            # ilan basina istek (olcum: 1+1+1+1+13+1+1+1+1+1+8+1)
KOTA_MIN = 500
ORNEK = ["CANCER_LIBRA", "LEO_LEO", "SAGITTARIUS_SAGITTARIUS"]


def sorular(pair):
    a, b = (p.capitalize() for p in pair.split("_", 1))
    ad = "Up to 11 letters. Printed in capitals."
    l1, l2 = ("Name on the left", "Name on the right") if a == b else (f"Name under {a}", f"Name under {b}")
    return [dict(question_text=l1, instructions=ad, question_type="text_input", required=True, max_allowed_characters=11),
            dict(question_text=l2, instructions=ad, question_type="text_input", required=True, max_allowed_characters=11),
            dict(question_text="Your special date", instructions="Write the month in letters, for example 14 June 2025",
                 question_type="text_input", required=True, max_allowed_characters=20),
            dict(question_text="Heading", instructions="Paper Anniversary or Our First Year. Poster only; the card says Happy First Anniversary.",
                 question_type="text_input", required=True, max_allowed_characters=20),
            dict(question_text="Optional short line", instructions="Leave empty for Year One", question_type="text_input",
                 required=False, max_allowed_characters=20)]


class Dur(Exception):
    pass


class Kilitli(Etsy):
    """Yazmalar yalniz o an islenen taslaga (lid); canli ilana (REF) yazma yok; DELETE yalniz eski taslak."""
    lid = None
    silinebilir = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = []
        if lid:
            ok += [("PUT", rf"^/listings/{lid}/inventory$"), ("POST", rf"^/shops/\d+/listings/{lid}/images$"),
                   ("POST", rf"^/shops/\d+/listings/{lid}/variation-images$"), ("POST", rf"^/shops/\d+/listings/{lid}/personalization$"),
                   ("PUT", rf"^/shops/\d+/listings/{lid}/properties/\d+$"), ("PATCH", rf"^/shops/\d+/listings/{lid}$")]
        if self.silinebilir:
            ok += [("DELETE", rf"^/listings/{self.silinebilir}$")]
        if str(REF) in path or not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def put(self, path, data):
        self._izin("PUT", path); return super().put(path, data)

    def put_json(self, path, body):
        self._izin("PUT", path); return super().put_json(path, body)

    def post_json(self, path, body):
        self._izin("POST", path); return super().post_json(path, body)

    def post_file(self, path, files, data=None):
        self._izin("POST", path); return super().post_file(path, files, data)

    def post(self, path, data):
        raise SystemExit(f"YASAK: form POST {path} (olusturma yalniz olustur() icinde)")

    def patch(self, path, data):
        self._izin("PATCH", path)
        if data != {"state": "inactive"}:
            raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        return super().patch(path, data)

    def delete(self, path):
        self._izin("DELETE", path); return super().delete(path)


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
    rows = list(csv.DictReader(open(os.environ["CSV"], encoding="utf-8")))
    sec = os.environ.get("CIFTLER", "").split()
    rows = [r for r in rows if not sec or r["cift"] in sec]
    csv_f = out / "BY78_TASLAKLAR.csv"
    T = {}
    if csv_f.exists():
        for r in csv.DictReader(open(csv_f)):
            T[r["cift"]] = r
    R = {"basla": time.strftime("%H:%M:%S"), "olaylar": [], "ornek": {}}

    def yaz(drive=False):
        with open(csv_f, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["cift", "listing_id", "asama", "state", "link"])
            w.writeheader()
            for c in [r["cift"] for r in rows] + [c for c in T if c not in {r["cift"] for r in rows}]:
                if c in T:
                    w.writerow({k_: T[c].get(k_, "") for k_ in ("cift", "listing_id", "asama", "state", "link")})
        json.dump(R, open(out / "BY78_RAPOR.json", "w"), indent=1, ensure_ascii=False, default=str)
        if drive and DOUT:
            subprocess.run(["rclone", "copyto", str(csv_f), f"{DOUT}/BY78_TASLAKLAR.csv", "-q"], check=True)

    def kota():
        rem = int(api.remaining) if api.remaining not in (None, "") else None
        if rem is not None and rem < KOTA_MIN:
            raise Dur(f"KOTA {rem} < {KOTA_MIN}")
        return rem

    def state(c, adim):
        L = api.get(f"/listings/{api.lid}") or {}
        st = L.get("state")
        T[c]["state"] = st
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            T[c]["state"] = f"active->{st2}"
            R["olaylar"].append(f"ACIL {c} {api.lid} {adim}: active -> {st2}")
            yaz(True)
            print(f"::error::ACIL: {c} {api.lid} {adim} sonrasi active -> inactive ({st2}). TUM IS DURDU.")
            raise SystemExit(2)
        if st != "draft":
            raise Dur(f"{c} {api.lid} {adim}: beklenmeyen state {st}")
        kota()
        return L

    # 0) canli referans (salt okuma) + kota kapisi
    L0 = api.get(f"/listings/{REF}") or {}
    props0 = (api.get(f"/shops/{shop}/listings/{REF}/properties") or {}).get("results") or []
    inv0 = api.get(f"/listings/{REF}/inventory") or {}
    rs = sorted({o.get("readiness_state_id") for p in inv0.get("products") or [] for o in p.get("offerings") or [] if o.get("readiness_state_id")})
    if len(rs) != 1:
        raise SystemExit(f"HATA: canli readiness tek degil {rs}")
    props_hedef = [p for p in props0 if p.get("value_ids") and p.get("property_name") not in HARIC_NITELIK]
    kontrol = dict(ship=L0.get("shipping_profile_id") == SHIP, ret=L0.get("return_policy_id") == RET, tax=L0.get("taxonomy_id") == TAX,
                   partner=[p.get("production_partner_id") for p in L0.get("production_partners") or []] == [PARTNER],
                   who=L0.get("who_made") == WHO, when=L0.get("when_made") == WHEN, nitelik=len(props_hedef) == 8)
    R["referans"] = dict(kontrol=kontrol, readiness=rs[0], processing=(L0.get("processing_min"), L0.get("processing_max")),
                         nitelikler=[(p["property_name"], p.get("values")) for p in props_hedef])
    if not all(kontrol.values()):
        yaz(); raise SystemExit(f"HATA: canli referans beklenen ayarlarla uyusmuyor {kontrol}")
    kalan_ilan = sum(1 for r in rows if T.get(r["cift"], {}).get("asama") != "tamam")
    rem = int(api.remaining or 0)
    gerek = kalan_ilan * ISTEK_ILAN + KOTA_MIN + 30
    R["kota_bas"] = dict(kalan=rem, gerek=gerek, ilan=kalan_ilan)
    print(f"::warning::KOTA kalan {rem}, gerek {gerek} ({kalan_ilan} ilan x {ISTEK_ILAN} + {KOTA_MIN})")
    if rem < gerek:
        yaz(True); print("::error::KOTA YETMEZ, baslanmadi"); raise SystemExit(3)

    # 1) eski taslak
    eski = os.environ.get("ESKI_ID", "").strip()
    if eski:
        E = api.get(f"/listings/{eski}", ok404=True)
        if E is None:
            R["eski_taslak"] = f"{eski} zaten yok"
        elif E.get("state") == "draft":
            api.silinebilir = eski
            api.delete(f"/listings/{eski}")
            api.silinebilir = None
            R["eski_taslak"] = f"{eski} silindi" if api.get(f"/listings/{eski}", ok404=True) is None else f"{eski} SILINEMEDI"
        else:
            R["eski_taslak"] = f"{eski} state={E.get('state')}: SILINMEDI"
        print("eski taslak:", R["eski_taslak"])

    # mevcut taslaklar (cift ilan acmamak icin baslik eslesmesi)
    drafts, off = {}, 0
    while True:
        r_ = api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100, "offset": off}) or {}
        for x in r_.get("results") or []:
            drafts[x.get("title")] = x.get("listing_id")
        off += 100
        if off >= (r_.get("count") or 0):
            break

    t0 = time.time()
    img_root = Path("_img");
    try:
        for i, r in enumerate(rows, 1):
            c = r["cift"]
            T.setdefault(c, {"cift": c})
            asama = T[c].get("asama") or ""
            if asama == "tamam":
                continue
            title, desc = r["baslik"], r["aciklama"]
            tags = [r[f"etiket_{j}"] for j in range(1, 14)]
            Q = sorular(c)
            if re.search("[–—]", title + desc + "".join(tags) + json.dumps(Q)):
                raise Dur(f"{c}: metinde uzun/orta tire")
            lid = T[c].get("listing_id") or drafts.get(title)
            # gorseller (yerel)
            d = img_root / c
            if d.exists():
                shutil.rmtree(d)
            subprocess.run(["rclone", "copy", f"{V3}/{c}/galeri", str(d), "-q", "--transfers", "8"], check=True)
            yol = [d / f"{n}.jpg" for n in GALERI]
            if not all(p.exists() for p in yol):
                raise Dur(f"{c}: galeri eksik {[p.name for p in yol if not p.exists()]}")

            if not lid:
                body = {"quantity": 999, "title": title, "description": desc, "price": FORMATS[0][1], "who_made": WHO,
                        "when_made": WHEN, "is_supply": "false", "taxonomy_id": TAX, "type": "physical",
                        "shipping_profile_id": SHIP, "return_policy_id": RET, "readiness_state_id": rs[0],
                        "shop_section_id": SECTION_ID, "tags": ",".join(tags), "materials": ",".join(MATERIALS),
                        "should_auto_renew": "true", "is_personalizable": "true", "production_partner_ids": str(PARTNER)}
                rq = requests.post(API + f"/shops/{shop}/listings", data=body, headers=api._headers(), timeout=120)   # TEK deneme
                api.calls += 1
                if rq.headers.get("x-remaining-today") is not None:
                    api.remaining = rq.headers["x-remaining-today"]
                if rq.status_code == 401:
                    store.refresh()
                    rq = requests.post(API + f"/shops/{shop}/listings", data=body, headers=api._headers(), timeout=120)
                if rq.status_code not in (200, 201):
                    raise Dur(f"{c}: createDraftListing {rq.status_code}: {rq.text[:300]}")
                lid = rq.json().get("listing_id")
                if not lid:
                    raise Dur(f"{c}: listing_id donmedi")
                T[c].update(listing_id=lid, asama="olusturuldu", link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}")
                yaz(True)                                     # cift ilan acmamak icin HEMEN Drive'a
                asama = "olusturuldu"
            T[c].update(listing_id=lid, link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}")
            api.lid = lid
            state(c, "olusturma")
            asama = asama or "olusturuldu"
            T[c]["asama"] = asama
            gec = lambda a: ASAMA.index(asama) < ASAMA.index(a)   # noqa: E731

            vid = {}
            if gec("envanter"):
                prods = [dict(sku="", property_values=[dict(property_id=P_STYLE, property_name="Style", values=[st]),
                                                       dict(property_id=P_FORMAT, property_name="Format", values=[fm])],
                              offerings=[dict(price=pr, quantity=999, is_enabled=True, readiness_state_id=rs[0])])
                         for st in STYLES for fm, pr in FORMATS]
                inv = api.put_json(f"/listings/{lid}/inventory", dict(products=prods, price_on_property=[P_FORMAT],
                                                                      quantity_on_property=[], sku_on_property=[])) or {}
                asama = T[c]["asama"] = "envanter"
                state(c, "envanter")
            else:
                inv = api.get(f"/listings/{lid}/inventory") or {}
            for p in inv.get("products") or []:
                for v in p.get("property_values") or []:
                    if v.get("property_id") == P_STYLE and v.get("value_ids"):
                        vid[v["values"][0]] = v["value_ids"][0]
            if sorted(vid) != sorted(STYLES):
                raise Dur(f"{c}: Style value_id eksik {vid}")

            if gec("gorseller"):
                have = {x.get("rank"): x.get("listing_image_id") for x in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
                for rk, p in enumerate(yol, 1):
                    if rk in have:
                        continue
                    with open(p, "rb") as fh:
                        x = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")},
                                          data={"rank": str(rk)}) or {}
                    have[rk] = x.get("listing_image_id")
                asama = T[c]["asama"] = "gorseller"
                state(c, "gorseller")
                img = have
            else:
                img = {x.get("rank"): x.get("listing_image_id") for x in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
            if sorted(k_ for k_ in img if k_) != list(range(1, 14)):
                raise Dur(f"{c}: gorsel siralari {sorted(img)}")

            if gec("varyasyon_gorsel"):
                vi = [dict(property_id=P_STYLE, value_id=vid[st], image_id=img[rk]) for st, rk in STIL_GORSEL.items()]
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
                asama = T[c]["asama"] = "varyasyon_gorsel"
                state(c, "varyasyon_gorsel")

            if gec("kisisel"):
                api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": Q})
                asama = T[c]["asama"] = "kisisel"
                state(c, "kisisel")

            if gec("nitelik"):
                for p in props_hedef:
                    b = {"value_ids": ",".join(str(v) for v in p["value_ids"]), "values": ",".join(p.get("values") or [])}
                    if p.get("scale_id"):
                        b["scale_id"] = p["scale_id"]
                    api.put(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}", b)
                asama = T[c]["asama"] = "nitelik"
                L = state(c, "nitelik")
                hata = [k_ for k_, ok in (("baslik", L.get("title") == title), ("etiket", len(L.get("tags") or []) == 13),
                                          ("bolum", L.get("shop_section_id") == SECTION_ID),
                                          ("partner", [p.get("production_partner_id") for p in L.get("production_partners") or []] == [PARTNER]),
                                          ("who", L.get("who_made") == WHO), ("when", L.get("when_made") == WHEN),
                                          ("malzeme", L.get("materials") == MATERIALS), ("kargo", L.get("shipping_profile_id") == SHIP)) if not ok]
                if hata:
                    raise Dur(f"{c}: dogrulama {hata}")
            T[c]["asama"] = "tamam"
            yaz(True)
            shutil.rmtree(d, ignore_errors=True)
            el = time.time() - t0
            n_ok = sum(1 for x in T.values() if x.get("asama") == "tamam")
            print(f"{i}/{len(rows)} %{100 * i // len(rows)} {c} {lid} draft | gecen {el / 60:.1f} dk kalan ~{el / i * (len(rows) - i) / 60:.1f} dk | kota {api.remaining} | tamam {n_ok}", flush=True)
    except Dur as e:
        R["dur"] = str(e)
        yaz(True)
        print(f"::error::DURDU: {e}")
        raise SystemExit(4)

    # ornek 3 ilan tam dogrulama
    for c in ORNEK:
        if c not in T or not T[c].get("listing_id"):
            continue
        lid = T[c]["listing_id"]
        L = api.get(f"/listings/{lid}") or {}
        ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
        vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        inv = api.get(f"/listings/{lid}/inventory") or {}
        per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
        idrank = {x.get("listing_image_id"): x.get("rank") for x in ims}
        vname = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or [] if v.get("property_id") == P_STYLE}
        fiyat = sorted({(v["values"][0], round(p["offerings"][0]["price"]["amount"] / p["offerings"][0]["price"]["divisor"], 2))
                        for p in inv.get("products") or [] for v in p.get("property_values") or [] if v.get("property_id") == P_FORMAT})
        R["ornek"][c] = dict(listing_id=lid, state=L.get("state"), link=T[c]["link"], gorsel=len(ims),
                             gorsel_sira=[(x.get("rank"), x.get("full_width"), x.get("full_height")) for x in ims],
                             varyasyon_gorsel=[(vname.get(v.get("value_id")), idrank.get(v.get("image_id"))) for v in vis],
                             urun=len(inv.get("products") or []), format_fiyat=fiyat,
                             kutular=[(q.get("question_text"), q.get("required"), q.get("max_allowed_characters"), q.get("instructions")) for q in per])
    R["bitis"] = time.strftime("%H:%M:%S")
    R["kota_son"] = api.remaining
    n_ok = sum(1 for r in rows if T.get(r["cift"], {}).get("asama") == "tamam" and T[r["cift"]].get("state") == "draft")
    R["tamam_draft"] = n_ok
    yaz(True)
    print(f"::warning::TASLAK {n_ok}/{len(rows)} tamam+draft | kota {api.remaining} | eski: {R.get('eski_taslak')}")
    for c, o in R["ornek"].items():
        print(f"::warning::{c} {o['listing_id']} {o['state']} gorsel {o['gorsel']} varyasyon_gorsel {o['varyasyon_gorsel']} kutu {len(o['kutular'])}")
    if n_ok != len(rows):
        raise SystemExit(5)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):                   # HATA mesaji: job logu okunamadigi icin annotation'a yaz
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:                            # beklenmeyen hata da annotation'a
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
