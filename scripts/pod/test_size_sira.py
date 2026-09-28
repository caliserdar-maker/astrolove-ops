#!/usr/bin/env python3
"""size_sira oz-testi (sahte Etsy, ag yok). Calistir: python3 scripts/pod/test_size_sira.py
S1 kuru: fiyat sirasi uygun -> PLAN; bozuk fiyatli ilan -> FAIL raporu, yazma yok
S2 yaz: CL once; Size ilk sirasi hedef, urun imzasi/Format/Color ayni, PUT baglari silerse renk-gorsel yeniden baglanir
S3 taslak ilan ATLANDI; S4 PUT sonrasi fiyat degisirse FAIL + DUR; S5 confirm yok -> red; S6 ikinci kosu ZATEN"""
import copy, csv, json, os, sys, tempfile, types
from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/pod")); sys.path.insert(0, str(KOK / "scripts/etsy"))
import test_ayar77_kuru as T
import ayar77_yaz as Y
import size_sira as S
Y.BEKLE = 0
FIY = {"8x10": 42, "11x14": 49, "12x16": 55, "12x18": 57, "16x20": 69, "16x24": 72, "18x24": 79, "20x30": 95, "24x30": 105,
       "24x36": 115, "A4": 44, "A3": 52, "A2": 68}
IDS = [r["listing_id"] for r in csv.DictReader(open(KOK / "data/pod/pod78_ids.csv"))]


def inv(bozuk=False, c99=False):
    I = T.cl_inv()
    for p in I["products"]:
        f = p["property_values"][0]["values"][0]; b = p["property_values"][2]["values"][0]
        if f == "Print":
            p["offerings"][0]["price"] = {"amount": (FIY[b] - (20 if bozuk and b == "12x18" else 0)) * 100 - (1 if c99 else 0), "divisor": 100}
        elif c99 and f == "Black Frame" and b == "8x10":
            p["offerings"][0]["price"]["amount"] = 4800                       # .99 olmayan: dokunulmamali
        for v in p["property_values"]:
            if v["property_id"] == 200:
                v["value_ids"] = [7000 + T.RENK.index(v["values"][0])]
    return I


class Fake(T.Fake if False else object):
    def __init__(s, bozuk_id=None, fiyat_bozan=False, c99=False):
        s.remaining, s.calls, s.yaz, s.fb = "5000", 0, [], fiyat_bozan
        s.I = {i: {"inv": inv(i == bozuk_id, c99), "L": {"listing_id": i, "state": "active", "title": "t", "tags": ["x"]},
                   "vimg": [{"property_id": 200, "value_id": 7000 + k, "value": r, "image_id": 900 + k} for k, r in enumerate(T.RENK)],
                   "imgs": [{"listing_image_id": 1, "rank": 1}], "q": [{"question_text": "a"}], "props": []} for i in IDS}
        s.I[IDS[5]]["L"]["state"] = "draft"

    def _lid(s, path):
        return next(p.split("?")[0] for p in path.split("/") if p.split("?")[0].isdigit() and len(p.split("?")[0]) == 10)

    def get(s, path, params=None, ok404=False):
        s.calls += 1
        if path == "/listings/batch":
            return {"results": [{"listing_id": i, "description": "Printed within 7 business days." + (" Only $39 today" if i == IDS[2] else "")}
                                for i in params["listing_ids"].split(",")]}
        if path.startswith("/shops/") and path.count("/") == 2:
            return {"announcement": "Welcome", "sale_message": "Thanks"}
        I = s.I[s._lid(path)]
        for suf, key in (("/inventory", "inv"), ("/variation-images", "vimg"), ("/images", "imgs")):
            if path.endswith(suf):
                return copy.deepcopy(I[key]) if key == "inv" else {"results": copy.deepcopy(I[key])}
        if path.endswith("/videos"):
            return {"results": [{"video_id": 1}]}
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(I["q"])}
        if path.endswith("/properties"):
            return {"results": []}
        return copy.deepcopy(I["L"])

    def put_json(s, path, body):
        s.yaz.append(("PUT", s._lid(path))); I = s.I[s._lid(path)]
        yeni = copy.deepcopy(body)
        for p in yeni["products"]:
            for v in p["property_values"]:
                if v["property_id"] == 200:
                    v["value_ids"] = [8000 + T.RENK.index(v["values"][0])]      # Etsy yeni value_id verir
            for o in p["offerings"]:
                o["price"] = {"amount": int(round(o["price"] * 100)) + (1 if s.fb else 0), "divisor": 100}
        I["inv"] = yeni; I["vimg"] = []                                         # PUT baglari siler

    def post_json(s, path, body):
        s.yaz.append(("VIMG", s._lid(path))); I = s.I[s._lid(path)]
        I["vimg"] = [{"property_id": 200, "value_id": x["value_id"], "value": T.RENK[x["value_id"] - 8000], "image_id": x["image_id"]}
                     for x in body["variation_images"]]


def kos(api, arg):
    m = types.ModuleType("etsy_common"); m.Etsy = lambda st: api; m.mask = lambda v: None
    m.TokenStore = type("TS", (), {"__init__": lambda self, *a: None, "needs_refresh": lambda self: False})
    sys.modules["etsy_common"] = m
    os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1"); sys.argv = ["s"] + arg
    try:
        return S.main()
    except SystemExit as e:
        return e.code


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))

W = Path(tempfile.mkdtemp())
A = Fake(bozuk_id=IDS[9]); rc = kos(A, ["--mod", "kuru", "--out", str(W / "k")])
R = json.loads((W / "k/ILERLEME.json").read_text())["ilanlar"]
k("kuru: yazma yok", not A.yaz)
k("kuru: 77 PLAN, bozuk fiyatli ilan FAIL + DUR", sum(v["durum"] == "PLAN" for v in R.values()) == 77 and R[IDS[9]]["durum"] == "FAIL"
  and "12x18" in R[IDS[9]]["not"] and "DUR" in str(rc), R[IDS[9]]["not"][:80])
k("confirm yok -> red", "SIZESIRA" in str(kos(Fake(), ["--mod", "yaz", "--out", str(W / "x")])))
A = Fake(); inv0 = copy.deepcopy(A.I[S.CL_ID]["inv"])
rc = kos(A, ["--mod", "yaz", "--confirm", "SIZESIRA", "--out", str(W / "y")])
R = json.loads((W / "y/ILERLEME.json").read_text())["ilanlar"]
say = {}
for v in R.values():
    say[v["durum"]] = say.get(v["durum"], 0) + 1
k("yaz: 77 YAZILDI + 1 ATLANDI (taslak)", say == {"YAZILDI": 77, "ATLANDI": 1} and rc in (0, None), say)
k("CL ilk yazilan", A.yaz[0] == ("PUT", S.CL_ID))
inv1 = A.I[S.CL_ID]["inv"]; rol = S.ozellik_adlari(inv1)
k("Size sirasi hedef", S.ilk_sira(inv1, rol["size"]) == S.HEDEF, S.ilk_sira(inv1, rol["size"]))
k("Format/Color sirasi ayni", S.ilk_sira(inv1, rol["format"]) == T.FORMATS and S.ilk_sira(inv1, rol["color"]) == T.RENK)
k("urun imzasi birebir (fiyat/SKU/stok/readiness)", S.K.imza(inv1) == S.K.imza(inv0) and len(inv1["products"]) == 390)
k("renk-gorsel yeniden baglandi, ayni gorseller", {x["value"]: x["image_id"] for x in A.I[S.CL_ID]["vimg"]}
  == {r: 900 + n for n, r in enumerate(T.RENK)})
k("taslak ilana yazma yok", not any(y[1] == IDS[5] for y in A.yaz))
k("yedek her ilanda yazmadan once", len(list((W / "y/YEDEK").glob("*.json"))) == 77)
n0 = len(A.yaz); rc = kos(A, ["--mod", "yaz", "--confirm", "SIZESIRA", "--out", str(W / "z")])
R = json.loads((W / "z/ILERLEME.json").read_text())["ilanlar"]
k("ikinci kosu: ZATEN, yazma yok", len(A.yaz) == n0 and sum(v["durum"] == "ZATEN" for v in R.values()) == 77)
A = Fake(fiyat_bozan=True); rc = kos(A, ["--mod", "yaz", "--confirm", "SIZESIRA", "--out", str(W / "f")])
k("PUT fiyati degistirirse FAIL + ilk ilanda DUR", "DUR" in str(rc) and len([y for y in A.yaz if y[0] == "PUT"]) == 1, rc)
# ---- .99 fiyat (ayni yazim) + kar kapisi (sahte maliyet)
MAL = {"PRINT": 20.0, "FGO": 25.0, "FBK": 25.0, "FWH": 25.0, "FNA": 25.0, "DIGITAL": 0.0}
S.MALIYET = lambda tur, boy, ulke: MAL[tur] + (60.0 if (tur == "PRINT" and boy == "8x10" and ulke == "AU" and PAHALI[0]) else 0)
PAHALI = [False]
A = Fake(c99=True); rc = kos(A, ["--mod", "kuru", "--fiyat99", "--out", str(W / "k99")])
rap = (W / "k99/RAPOR.md").read_text()
k("kuru .99: kar tablosu + .99 olmayan listesi + metin taramasi, yazma yok", not A.yaz and "net US eski/yeni" in rap
  and "8x10-FBK 48.0" in rap and "$39" in rap and "PLAN" in (W / "k99/ILERLEME.json").read_text(), rc)
A = Fake(c99=True); inv0 = copy.deepcopy(A.I[S.CL_ID]["inv"])
rc = kos(A, ["--mod", "yaz", "--fiyat99", "--confirm", "SIZESIRA", "--out", str(W / "y99"), "--yalniz", S.CL_ID])
inv1 = A.I[S.CL_ID]["inv"]
f0 = {p["sku"]: S.K.money(p["offerings"][0]["price"]) for p in inv0["products"]}
f1 = {p["sku"]: S.K.money(p["offerings"][0]["price"]) for p in inv1["products"]}
k("yaz .99: .99 -> asagi tam, digerleri ayni, SKU kumesi ayni", set(f0) == set(f1) and all(
  f1[x] == (float(int(f0[x])) if round(f0[x] * 100) % 100 == 99 else f0[x]) for x in f0) and any(round(v * 100) % 100 != 99 for v in f0.values()), rc)
k("yaz .99: Size sirasi da ayni yazimda (tek PUT)", S.ilk_sira(inv1, S.ozellik_adlari(inv1)["size"]) == S.HEDEF
  and [y[0] for y in A.yaz].count("PUT") == 1)
PAHALI[0] = True
A = Fake(c99=True); rc = kos(A, ["--mod", "yaz", "--fiyat99", "--confirm", "SIZESIRA", "--out", str(W / "p99")])
k("kar kapisi: AU 8x10 net <= 0 -> FAIL, hic PUT yok, DUR", not A.yaz and "DUR" in str(rc) and "kar kapisi" in str(rc), str(rc)[:120])
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
