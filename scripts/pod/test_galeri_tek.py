"""galeri_tek yerel testi (ag yok, Etsy sahte). Calistir: python3 scripts/pod/test_galeri_tek.py"""
import csv, json, pathlib, sys, tempfile, types
KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import galeri_tek as G

W = pathlib.Path(tempfile.mkdtemp(prefix="galeri_tek_"))
sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))

# --- sahte plan: A yeni (13), B 4 kartli (galeri_genel sonrasi), C renk baglari farkli, D taslak
def once(b): return [b + i for i in range(1, 14)]
P = {}
for lid, b in (("1001", 100), ("1002", 200), ("1003", 300), ("1004", 400), ("1005", 500)):
    o = once(b)
    P[lid] = {"once_ids": o, "sil_ids": o[5:8], "bagli_ids": o[8:13]}
with open(W / "m.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["ilan_id", "cift"])
    for lid, c in (("1001", "ARIES_LEO"), ("1002", "ARIES_TAURUS"), ("1003", "LEO_LEO"), ("1004", "GEMINI_LEO"), ("1005", "LEO_VIRGO"), (G.REF, "CANCER_LIBRA")):
        w.writerow([lid, c])
(W / "plan.json").write_text(json.dumps({"plan": P}), encoding="utf-8")

# --- saf fonksiyonlar
tip, rol, h = G.roller(P["1001"], P["1001"]["once_ids"])
ip = G.islem_plani(tip, rol, P["1001"]["bagli_ids"])
k("yeni ilan: tip + 4 silme (kapak + 6/7/8)", tip == "yeni" and ip["sil"] == [101, 106, 107, 108], ip["sil"])
k("yeni ilan: 7 yukleme", ip["yukle"] == ["KAPAK", "GENEL_1", "KART3", "KART09", "GENEL_2", "GENEL_3", "GENEL_4"], ip["yukle"])
k("yeni ilan: 18 cagri", ip["cagri_toplam"] == 18, ip["cagri"])
k("sonuc 16 gorsel <= 20", ip["sonuc_sayi"] == 16 and not ip["kapi"])
o2 = P["1002"]["once_ids"]
sonra2 = [o2[0], 901] + o2[1:5] + o2[8:13] + [902, 903, 904]        # galeri_genel yaz sonrasi
tip2, rol2, h2 = G.roller(P["1002"], sonra2)
ip2 = G.islem_plani(tip2, rol2, P["1002"]["bagli_ids"])
k("4 kartli ilan: tip genel_var, G1..G4 korunur", tip2 == "genel_var" and rol2["GENEL_1"] == 901 and rol2["GENEL_4"] == 904)
k("4 kartli ilan: yalniz kapak silinir, 3 yukleme, 11 cagri", ip2["sil"] == [201] and ip2["yukle"] == ["KAPAK", "KART3", "KART09"]
  and ip2["cagri_toplam"] == 11, (ip2["sil"], ip2["yukle"], ip2["cagri_toplam"]))
yeni = {"KAPAK": 1, "KART3": 3, "KART09": 4}
k("4 kartli ilan: hedef sira", G.hedef_ids(rol2, yeni) == [1, 901, 3, 4] + o2[1:5] + o2[8:13] + [902, 903, 904])
t3, _, h3 = G.roller(P["1003"], P["1003"]["once_ids"][:-1] + [999])
k("bilinmeyen durum -> tip yok", t3 is None and h3)
_, rol4, _ = G.roller(P["1004"], P["1004"]["once_ids"])
k("renk bagi 9-13 disinda -> kapi", G.islem_plani("yeni", rol4, [401, 409, 410, 411, 412])["kapi"])

# --- yaz: sahte Etsy
class FE:
    def __init__(s):
        s.calls, s.remaining, s.log = 0, "4000", []
        s.img = {"1001": list(P["1001"]["once_ids"]), "1002": list(sonra2), "1003": list(P["1003"]["once_ids"]),
                 "1004": list(P["1004"]["once_ids"]), "1005": list(P["1005"]["once_ids"])}
        s.vid = {x: [{"video_id": 7000 + i}] for i, x in enumerate(s.img)}
        s.state = {x: "active" for x in s.img}; s.state["1005"] = "draft"
        s.var = {x: P[x]["bagli_ids"] for x in s.img}; s.var["1003"] = [301] + P["1003"]["bagli_ids"][1:]
        s.nid = 5000
    def _c(s, *a): s.calls += 1; s.log.append(a)
    def get(s, path, params=None, ok404=False):
        s._c("GET", path); lid = path.split("/")[-1] if "variation" not in path else path.split("/")[-2]
        if "variation-images" in path:
            return {"results": [{"value_id": 50 + j, "image_id": iid} for j, iid in enumerate(s.var[lid])]}
        return {"state": s.state[lid], "images": [{"listing_image_id": x, "rank": r} for r, x in enumerate(s.img[lid], 1)],
                "videos": s.vid[lid]}
    def delete(s, path):
        s._c("DELETE", path); p = path.split("/"); lid = p[4]
        if p[5] == "images": s.img[lid].remove(int(p[6]))
        else: s.vid[lid] = []
    def post_file(s, path, files, data=None):
        s._c("POST", path); lid = path.split("/")[4]; s.nid += 1
        if path.endswith("/videos"):
            s.vid[lid] = [{"video_id": s.nid}]; return {"video_id": s.nid}
        s.img[lid].append(s.nid); return {"listing_image_id": s.nid}
    def patch(s, path, data):
        s._c("PATCH", path); lid = path.split("/")[-1]
        yeni = [int(x) for x in data["image_ids"].split(",")]
        assert sorted(yeni) == sorted(s.img[lid]); s.img[lid] = yeni

yerel = W / "tek"; kart = W / "kart"; kart.mkdir()
for f in G.GENEL_DOSYA.values(): (kart / f).write_bytes(b"x")
for c in ("ARIES_LEO", "ARIES_TAURUS", "LEO_LEO", "GEMINI_LEO", "LEO_VIRGO"):
    (yerel / c).mkdir(parents=True)
    for f in ("KAPAK.jpg", "KART09.jpg", "KART3.jpg", "VIDEO.mp4"): (yerel / c / f).write_bytes(b"x")
a = types.SimpleNamespace(confirm="GALERI_TEK", out=str(W / "out"), csv=str(W / "m.csv"), plan=str(W / "plan.json"),
                          kartlar=str(kart), yerel=str(yerel), listing="1001,1002,1003,1004,1005,4570143815", kota_alt=230,
                          medya="gdrive:X/A1_77", kart3="{CIFT}/KART3.jpg", video="{CIFT}/VIDEO.mp4")
api = FE()
try:
    G.yaz(types.SimpleNamespace(**{**vars(a), "confirm": "YANLIS"}), api, "9")
    k("yanlis onayla yazma yok", False)
except SystemExit:
    k("yanlis onayla yazma yok", api.calls == 0)
rc = G.yaz(a, api, "9")
S = {r["ilan"]: r for r in csv.DictReader(open(W / "out/SONUC_GALERI_TEK.csv", encoding="utf-8"))}
k("1001 yeni: PASS, 16 gorsel, 1 video, 18 cagri", S["1001"]["sonuc"] == "PASS" and len(api.img["1001"]) == 16
  and len(api.vid["1001"]) == 1 and "cagri 18" in S["1001"]["not"], S["1001"])
k("1001: renk bagli 5 gorsel 9-13'te, kapak yeni", api.img["1001"][8:13] == P["1001"]["bagli_ids"] and api.img["1001"][0] not in P["1001"]["once_ids"])
k("1001: eski kapak + 6/7/8 silindi", not {101, 106, 107, 108} & set(api.img["1001"]))
k("1002 4 kartli: PASS, 16 gorsel, 11 cagri", S["1002"]["sonuc"] == "PASS" and len(api.img["1002"]) == 16 and "cagri 11" in S["1002"]["not"], S["1002"])
k("1002: G1 2. sirada, G2-4 sonda", api.img["1002"][1] == 901 and api.img["1002"][-3:] == [902, 903, 904])
k("1003 kapak renge bagli -> ATLANDI, yazma yok", S["1003"]["sonuc"] == "ATLANDI" and not [x for x in api.log if "1003" in x[1] and x[0] != "GET"])
k("1005 taslak -> ATLANDI, yazma yok", S["1005"]["sonuc"] == "ATLANDI" and "draft" in S["1005"]["not"]
  and not [x for x in api.log if "1005" in x[1] and x[0] != "GET"])
k("Cancer-Libra haric", S[G.REF]["sonuc"] == "ATLANDI")
api2 = FE(); api2.remaining = "200"
G.yaz(types.SimpleNamespace(**{**vars(a), "out": str(W / "out2")}), api2, "9")
S2 = list(csv.DictReader(open(W / "out2/SONUC_GALERI_TEK.csv", encoding="utf-8")))
k("kota 200 < 230 -> DURDU, cagri yok", S2[0]["sonuc"] == "DURDU" and api2.calls == 0)
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
