#!/usr/bin/env python3
"""ESKI 78 POSTER: cerceve SATISINI kaldirma, metin + envanter (Serdar onayi 15 Eki, C plani). ETSY'YE YAZAR. Gorsellere dokunmaz.
--ciftler "CANCER_LIBRA" | HEPSI  (data/pod/pod78_ids.csv)
Ilan basina: envanter GET -> varyasyon gorsel baglari GET (once) -> envanter PUT: 4 cerceve degeri (Antique Gold/Black/White/
  Natural Frame) urunleri SILINIR, 'Digital File, Print or Framed?' menu adi 'Format' olur; kalan urunlerin fiyat/stok/sku/
  readiness/deger id'leri AYNI (390 -> 130) -> updateListing PATCH yalniz {description, materials} -> baglar GET (sonra, once ile ayni).
Kagit ifadesi (Serdar NOT 1, 15 Eki; tedarikci kararina BAGLI DEGIL): PRINT bolumunde Hahnemuhle / Photo Rag / 308 gsm /
  100% cotton / giclee / archival / ISO 9706 -> "Printed on premium matte art paper with long-lasting inks"; materials -> MATERIALS.
Aciklama: onaylanan once/sonra listesi (her degisiklik tam 1 kez bulunmali, yoksa DUR). Sonuc metinde 'frame' yalniz
  "Frames shown in photos are for display only and are not included. Prints ship unframed." satirinda gecer; uzun tire yok.
Tekrar kosu: aciklamasi zaten yeni ve envanterde cerceve yoksa ATLANIR. Ilk hatada DUR; kota < 10 DUR; ilan active degilse DUR.
Cikti: OUT/ESKI78_CERCEVE.json + <CIFT>_ACIKLAMA_ONCE/SONRA.txt
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KOK = Path(__file__).resolve().parents[2]
KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
P_FORMAT = 514
ESKI_AD = "Digital File, Print or Framed?"
YENI_AD = "Format"
CERCEVE = {"Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"}
KALAN = {"Digital File", "Print"}
YENI_SATIR = "Frames shown in photos are for display only and are not included. Prints ship unframed."
KAGIT_SATIR = "- Printed on premium matte art paper with long-lasting inks"
MATERIALS = ["matte art paper", "ink"]
KAGIT_YASAK = re.compile(r"hahnem|photo rag|\bgsm\b|cotton|gicl|archival|museum|iso 9706|acid", re.I)
DEGIS = [
    ("Choose a digital file, a print or a framed print.", "Choose a digital file or a print."),
    ("1. Digital File, Print or Framed? Choose your format.", "1. Format: choose Digital File or Print."),
    ("For every print and framed print, we send you a preview", "For every print, we send you a preview"),
    ("- Unframed, ready for the frame of your choice\n", ""),
    ("- Hahnemühle Photo Rag, 308 gsm, 100% cotton, acid-free, matte finish\n- Giclée print with pigment-based archival inks\n",
     KAGIT_SATIR + "\n"),
    ("Hahnemühle rates Photo Rag as museum quality (ISO 9706).", YENI_SATIR),
    ("FRAMED\n- Classic wood frame in Antique Gold, Black, White or Natural (oak effect)\n"
     "- 20 mm (0.8 in) frame face, acrylic (Perspex) front, no mat\n- Arrives ready to hang, hanging hardware included\n"
     "- Printed on 200 gsm enhanced matte fine art paper\nFramed prints use a different paper from our unframed prints. "
     "Frames in some photos are for display. Please see the Frame Colors photo for the real frame.\n\n", ""),
    ("Every size is available as a print and in all 4 frame colors.", "Every size is available as a print and as a digital file."),
    ("- US orders are printed and framed in the US.", "- US orders are printed in the US."),
    ("- US orders and all framed prints ship with tracking.", "- US orders ship with tracking."),
    (" Framed prints come in a heavy-duty box with corner guards and a protective sheet over the front.", ""),
    (" Wipe the frame and acrylic with a soft, dry cloth.", ""),
    ("If your print or frame arrives damaged", "If your print arrives damaged"),
    ("Is a frame included with the Print option? No. The print comes unframed. Choose a frame option for a ready to hang piece.\n", ""),
]
FRAME = re.compile(r"\b(frames?|framed|unframed|framing)\b", re.I)


class Dur(Exception):
    pass


def yeni_aciklama(d):
    t = d.replace("\r\n", "\n")
    for eski, yeni in DEGIS:
        n = t.count(eski)
        if n != 1:
            raise Dur(f"aciklamada {n} kez: {eski[:60]!r}")
        t = t.replace(eski, yeni)
    kalan = [ln for ln in t.splitlines() if FRAME.search(ln) and ln.strip() != YENI_SATIR]
    if kalan:
        raise Dur(f"yeni aciklamada frame kaldi: {kalan}")
    if t.count(YENI_SATIR) != 1:
        raise Dur("yeni satir 1 kez olmali")
    if re.search("[–—]", t):
        raise Dur("uzun/orta tire")
    if re.search(r"prodigi|printful|gelato|printify|shortrun", t, re.I):
        raise Dur("tedarikci adi")
    if KAGIT_YASAK.search(t):
        raise Dur(f"kagit ifadesi kaldi: {KAGIT_YASAK.findall(t)}")
    if t.count(KAGIT_SATIR) != 1:
        raise Dur("kagit satiri 1 kez olmali")
    return t


def mat_norm(m):
    return [str(v).strip().lower() for v in (m or [])]


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else float(p)


def kur(store):
    from etsy_common import Etsy

    class Kilitli(Etsy):
        izin = []

        def _k(self, m, path):
            if not any(mm == m and re.match(p, path) for mm, p in self.izin):
                raise SystemExit(f"YASAK: {m} {path}")

        def put_json(self, path, body):
            self._k("PUT", path); return super().put_json(path, body)

        def patch(self, path, data):
            self._k("PATCH", path)
            if not data or not set(data) <= {"description", "materials"}:
                raise SystemExit(f"YASAK PATCH alani: {sorted(data)}")
            return super().patch(path, data)

        def post(self, *a, **k):
            raise SystemExit("YASAK: POST")

        def put(self, *a, **k):
            raise SystemExit("YASAK: PUT form")

        def post_json(self, *a, **k):
            raise SystemExit("YASAK: POST json")

        def post_file(self, *a, **k):
            raise SystemExit("YASAK: POST file")

        def delete(self, *a, **k):
            raise SystemExit("YASAK: DELETE")
    return Kilitli(store)


def kota(api):
    try:
        r = int(api.remaining)
    except (TypeError, ValueError):
        return
    if r < KOTA_MIN:
        raise Dur(f"KOTA {r} < {KOTA_MIN}")


def imza(p, ad_map=None):
    pv = {v["property_id"]: v for v in p.get("property_values") or []}
    o = (p.get("offerings") or [{}])[0]
    return (tuple(sorted((k, tuple(v.get("values") or []), tuple(v.get("value_ids") or [])) for k, v in pv.items())),
            p.get("sku"), para(o["price"]), o.get("quantity"), o.get("is_enabled"), o.get("readiness_state_id"))


def calistir(api, shop, ciftler, ids_csv, R, out):
    rows = {r["cift"]: r for r in csv.DictReader(open(ids_csv))}
    if ciftler == ["HEPSI"]:
        ciftler = sorted(rows)
    eksik = [c for c in ciftler if c not in rows]
    if eksik:
        raise Dur(f"listede yok: {eksik}")
    ids = [str(rows[c]["listing_id"]) for c in ciftler]
    api.izin = [("PUT", rf"^/listings/({'|'.join(ids)})/inventory$"), ("PATCH", rf"^/shops/{shop}/listings/({'|'.join(ids)})$")]
    L = {}
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    kota(api)
    t0, n_is = time.time(), 0
    for i, c in enumerate(ciftler, 1):
        lid = str(rows[c]["listing_id"])
        x = L.get(lid) or {}
        K = R["ilan"][c] = {"listing_id": lid, "link": f"https://www.etsy.com/listing/{lid}"}
        if x.get("state") != "active" or str(x.get("shop_id")) != str(shop):
            raise Dur(f"{c}: state {x.get('state')} shop {x.get('shop_id')}")
        d0 = html.unescape(x.get("description") or "")
        mat_gerek = mat_norm(x.get("materials")) != MATERIALS
        K["materials_once"] = x.get("materials")
        if YENI_SATIR in d0:
            if KAGIT_YASAK.search(d0) or d0.count(KAGIT_SATIR) != 1:
                raise Dur(f"{c}: cerceve satiri var ama kagit ifadesi eski (yarim kalmis surum)")
            K["aciklama"] = "zaten yeni"
            d1 = None
        else:
            d1 = yeni_aciklama(d0)
            (out / f"{c}_ACIKLAMA_ONCE.txt").write_text(d0, encoding="utf-8")
            (out / f"{c}_ACIKLAMA_SONRA.txt").write_text(d1, encoding="utf-8")
        inv = api.get(f"/listings/{lid}/inventory") or {}
        prods = inv.get("products") or []
        fmt = lambda p: next((v.get("values") or [""])[0] for v in p.get("property_values") or [] if v["property_id"] == P_FORMAT)  # noqa: E731
        cerceveli = [p for p in prods if fmt(p) in CERCEVE]
        if not cerceveli and d1 is None and not mat_gerek:
            K["sonuc"] = "ATLANDI_ZATEN_YAPILDI"
            continue
        n_is += 1
        bag_kontrol = n_is == 1 or n_is % 10 == 0 or len(ciftler) == 1
        bag0 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id")) for v in
                      ((api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or [])) if bag_kontrol else []
        if cerceveli:
            kalan = [p for p in prods if fmt(p) in KALAN]
            if len(kalan) + len(cerceveli) != len(prods) or {fmt(p) for p in kalan} != KALAN:
                raise Dur(f"{c}: beklenmeyen format degeri {sorted({fmt(p) for p in prods})}")
            once = {}
            yeni = []
            for p in kalan:
                pvs = []
                for v in p.get("property_values") or []:
                    ad = YENI_AD if v["property_id"] == P_FORMAT else v.get("property_name")
                    pvs.append(dict(property_id=v["property_id"], property_name=ad, value_ids=v.get("value_ids"), values=v.get("values")))
                o = (p.get("offerings") or [{}])[0]
                yeni.append(dict(sku=p.get("sku") or "", property_values=pvs,
                                 offerings=[dict(price=para(o["price"]), quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                                 readiness_state_id=o.get("readiness_state_id"))]))
                once[(fmt(p), p.get("sku"))] = imza(p)
            govde = dict(products=yeni, price_on_property=inv.get("price_on_property") or [],
                         quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                         readiness_state_on_property=inv.get("readiness_state_on_property") or [])
            inv2 = api.put_json(f"/listings/{lid}/inventory", govde) or {}
            kota(api)
            p2 = inv2.get("products") or []
            sonra = {(fmt(p), p.get("sku")): imza(p) for p in p2}
            adlar = {v.get("property_name") for p in p2 for v in p.get("property_values") or [] if v["property_id"] == P_FORMAT}
            K["envanter"] = dict(once=len(prods), sonra=len(p2), format_adi=sorted(adlar))
            if len(p2) != len(kalan) or any(fmt(p) in CERCEVE for p in p2):
                raise Dur(f"{c}: envanter {len(p2)} urun / cerceve kaldi")
            if adlar != {YENI_AD}:
                raise Dur(f"{c}: menu adi {adlar}")
            # menu adi disinda her sey ayni olmali
            norm = lambda s: (tuple((k, vals, vids) for k, vals, vids in s[0]),) + s[1:]  # noqa: E731
            if {k: norm(v) for k, v in sonra.items()} != {k: norm(v) for k, v in once.items()}:
                raise Dur(f"{c}: kalan urunlerde fiyat/stok/sku/deger id degisti")
        veri = {}
        if d1 is not None:
            veri["description"] = d1
        if mat_gerek:
            veri["materials"] = ",".join(MATERIALS)
        if veri:
            y = api.patch(f"/shops/{shop}/listings/{lid}", veri) or {}
            kota(api)
            if y.get("state") != "active":
                raise Dur(f"{c}: PATCH sonrasi state {y.get('state')}")
            if html.unescape(y.get("description") or "").replace("\r\n", "\n") != (d1 if d1 is not None else d0.replace("\r\n", "\n")):
                raise Dur(f"{c}: aciklama yanitla eslesmiyor")
            K["materials_sonra"] = y.get("materials")
            if mat_norm(y.get("materials")) != MATERIALS:
                raise Dur(f"{c}: materials yanitla eslesmiyor {y.get('materials')}")
            if (y.get("title"), y.get("tags"), y.get("shipping_profile_id")) != (x.get("title"), x.get("tags"), x.get("shipping_profile_id")):
                raise Dur(f"{c}: baslik/etiket/profil degisti")
        if bag_kontrol:
            bag1 = sorted((v.get("property_id"), v.get("value_id"), v.get("image_id")) for v in
                          ((api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []))
            K["varyasyon_gorsel_bag"] = dict(once=len(bag0), sonra=len(bag1), ayni=bag0 == bag1)
            if bag0 != bag1:
                raise Dur(f"{c}: varyasyon gorsel baglari degisti {bag0} -> {bag1}")
        K["sonuc"] = "PASS"
        g = time.time() - t0
        print(f"[{i}/{len(ciftler)}] {c} {lid} PASS | envanter {K.get('envanter')} | gecen {g:.0f}s | kalan ~{g / i * (len(ciftler) - i):.0f}s | "
              f"%{i / len(ciftler) * 100:.0f} | kota {api.remaining}", flush=True)
    n = sum(1 for v in R["ilan"].values() if v.get("sonuc") == "PASS")
    a = sum(1 for v in R["ilan"].values() if v.get("sonuc") == "ATLANDI_ZATEN_YAPILDI")
    print(f"::warning::ESKI78 CERCEVE PASS {n} | atlandi {a} | toplam {len(ciftler)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ciftler", required=True)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = kur(store)
    R = {"ilan": {}}
    try:
        calistir(api, os.environ["ETSY_SHOP_ID"], a.ciftler.split(), a.ids, R, out)
    except Dur as e:
        R["dur"] = str(e)
        print(f"::error::DURDU: {e}")
        raise SystemExit(4)
    finally:
        R["istek"], R["kota_son"] = api.calls, api.remaining
        (out / "ESKI78_CERCEVE.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"::warning::BITTI | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:                                        # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
