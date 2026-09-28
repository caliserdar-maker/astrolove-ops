"""hazirlik_yaz oz-testi (sahte Etsy, ag yok). Calistir: python3 scripts/etsy/hazirlik_yaz_selftest.py"""
import csv, json, os, sys, tempfile, types
from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy"))
import hazirlik_yaz as H
H.BEKLE = 0
IDS = [r["listing_id"] for r in csv.DictReader(open(KOK / "data/pod/pod78_ids.csv"))]
METIN = "We&#39;re happy.\nMade to order. Printed and shipped within 5 business days after you approve your preview.\nsend a photo within 7 days"


class Sahte:
    def __init__(s, kota=5000, iki=None):
        s.remaining, s.calls, s.yaz = str(kota), 0, []
        s.L = {i: {"listing_id": i, "state": "active", "title": "T" + i, "tags": ["a"], "description": METIN} for i in IDS}
        s.L[IDS[3]]["state"] = "draft"
        s.L[IDS[4]]["description"] = METIN.replace("5 business", "7 business")
        if iki:
            s.L[IDS[iki]]["description"] = METIN + "\nwithin 5 business days"
        s.T = {"readiness_state_id": H.READINESS_ID, "readiness_state": "made_to_order", "min_processing_time": 3,
               "max_processing_time": 5, "processing_time_unit": "business_days"}

    def _k(s):
        s.calls += 1; s.remaining = str(int(s.remaining) - 1)

    def get(s, p, params=None, ok404=False):
        s._k()
        if "readiness" in p:
            return dict(s.T)
        return json.loads(json.dumps(s.L[p.split("/")[2]]))

    def put(s, p, d):
        s._k(); s.yaz.append(("PUT", p, dict(d))); s.T.update(d)

    def patch(s, p, d):
        s._k(); s.yaz.append(("PATCH", p, dict(d)))
        lid = p.split("/")[-1]
        assert set(d) == {"description"}, d
        s.L[lid]["description"] = d["description"].replace("'", "&#39;")


def kos(api, arg):
    m = types.ModuleType("etsy_common")
    m.Etsy = lambda st: api; m.mask = lambda v: None
    m.TokenStore = type("TS", (), {"__init__": lambda self, *a: None, "needs_refresh": lambda self: False})
    sys.modules["etsy_common"] = m
    os.environ.update(TOKEN_FILE="/dev/null", ETSY_SHOP_ID="1")
    sys.argv = ["h"] + arg
    try:
        return H.main()
    except SystemExit as e:
        return e.code


sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))

W = Path(tempfile.mkdtemp())
A = Sahte(); rc = kos(A, ["--mod", "yedek", "--out", str(W / "y")])
k("yedek: hic yazma yok", not A.yaz and rc == 0, A.yaz[:2])
k("yaz: confirm olmadan red", "HAZIRLIK" in str(kos(Sahte(), ["--mod", "yaz", "--out", str(W / "x")])))
A = Sahte(); rc = kos(A, ["--mod", "yaz", "--confirm", "HAZIRLIK", "--out", str(W / "a")])
R = json.loads((W / "a/ILERLEME.json").read_text()); say = {}
for v in R["ilanlar"].values():
    say[v["durum"]] = say.get(v["durum"], 0) + 1
k("readiness 4-7 yazildi, birim/tur korundu", A.T["min_processing_time"] == 4 and A.T["max_processing_time"] == 7
  and A.T["processing_time_unit"] == "business_days" and R["readiness"] == "YAZILDI")
k("76 YAZILDI, 1 ATLANDI (draft), 1 ZATEN", say == {"YAZILDI": 76, "ATLANDI": 1, "ZATEN": 1}, say)
k("draft ilana PATCH yok", not any(IDS[3] in y[1] for y in A.yaz))
k("PATCH govdesi unescape + yalniz ifade degisti", A.yaz[1][2]["description"] == H.normalize(METIN).replace(H.ESKI, H.YENI)
  and "We're" in A.yaz[1][2]["description"])
k("yedek: 78 ilan + tanim yazmadan once", len(list((W / "a/YEDEK").glob("*.json"))) == 79)
A = Sahte(iki=10); rc = kos(A, ["--mod", "yaz", "--confirm", "HAZIRLIK", "--out", str(W / "b")])
k("ilk FAIL'de DUR (ifade 2 kez)", "DUR" in str(rc) and not any(IDS[j] in y[1] for y in A.yaz for j in range(10, 78)), rc)
A = Sahte(kota=200); rc = kos(A, ["--mod", "yaz", "--confirm", "HAZIRLIK", "--out", str(W / "c"), "--kota-taban", "150"])
R = json.loads((W / "c/ILERLEME.json").read_text()); n1 = len(R["ilanlar"])
k("kota tabaninda temiz dur", rc in (0, None) and 0 < n1 < 78, n1)
A.remaining = "5000"
rc = kos(A, ["--mod", "yaz", "--confirm", "HAZIRLIK", "--out", str(W / "c"), "--ilerleme", str(W / "c/ILERLEME.json")])
R = json.loads((W / "c/ILERLEME.json").read_text())
k("ertesi gun kaldigi yerden: 78 tamam, readiness tekrar yazilmadi", len(R["ilanlar"]) == 78
  and sum(1 for y in A.yaz if y[0] == "PUT") == 1, len(R["ilanlar"]))
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
