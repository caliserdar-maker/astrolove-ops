"""galeri_tek (tam yeni set) yerel testi: ag yok, Etsy sahte. Calistir: python3 scripts/pod/test_galeri_tek.py"""
import csv, json, pathlib, sys, tempfile, types
KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import galeri_tek as G

W = pathlib.Path(tempfile.mkdtemp(prefix="galeri_tek_"))
sonuc = []
def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))

RENK = ["Midnight Blue", "Deep Black", "Warm Parchment", "Champagne Ivory", "Pure White"]
REFR = {"sira": [{"rank": i, "renk": (RENK[i - 9] if i >= 9 else None)} for i in range(1, 14)], "video": True}
(W / "ref.json").write_text(json.dumps(REFR), encoding="utf-8")
CIFT = {"1001": "ARIES_LEO", "4570113157": "ARIES_TAURUS", "1003": "LEO_LEO", "1004": "GEMINI_LEO", "1005": "LEO_VIRGO",
        "1006": "CANCER_LEO", "1007": "LEO_PISCES", "1008": "ARIES_ARIES", G.REF: "CANCER_LIBRA"}
with open(W / "m.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["ilan_id", "cift"]); w.writerows(CIFT.items())

def set_yaz(c, genel1=False, renk_kay=False, eksik=False):
    d = W / "tek" / c; d.mkdir(parents=True, exist_ok=True)
    g = [{"dosya": f"{i:02d}_{'GENEL_1_kisisellestirme' if genel1 and i == 2 else 'YENI'}.jpg",
          "renk": (RENK[i - 9] if i >= 9 else None)} for i in range(1, 14)]
    if renk_kay:
        g[7]["renk"], g[8]["renk"] = g[8]["renk"], None
    for x in g:
        (d / x["dosya"]).write_bytes(b"x")
    if eksik:
        (d / g[3]["dosya"]).unlink()
    (d / "VIDEO.mp4").write_bytes(b"v")
    (d / "SET.json").write_text(json.dumps({"gorseller": g, "video": "VIDEO.mp4"}), encoding="utf-8")
for c in ("ARIES_LEO", "ARIES_TAURUS", "LEO_VIRGO", "CANCER_LEO", "ARIES_ARIES"): set_yaz(c)
set_yaz("LEO_LEO", genel1=True); set_yaz("GEMINI_LEO", renk_kay=True); set_yaz("LEO_PISCES", eksik=True)

# --- saf fonksiyonlar
k("GENEL_1 sette -> red", any("GENEL_1" in x for x in G.set_dogrula(json.loads((W / "tek/LEO_LEO/SET.json").read_text()), REFR)))
k("renk yerlesimi farkli -> red", any("renk yerlesimi" in x for x in G.set_dogrula(json.loads((W / "tek/GEMINI_LEO/SET.json").read_text()), REFR)))
k("temiz set -> hata yok", not G.set_dogrula(json.loads((W / "tek/ARIES_LEO/SET.json").read_text()), REFR, W / "tek/ARIES_LEO"))
k("cagri formulu: 13 eski + 13 yeni + video = 35, 14 eski = 36", G.cagri_tahmini(13, 13) == 35 and G.cagri_tahmini(14, 13) == 36)

# --- sahte Etsy: 20 siniri, renk bagi bosluk izleme
class FE:
    def __init__(s, state_draft=(), renksiz=(), hata_ilan=None):
        s.calls, s.remaining, s.log, s.nid = 0, "4000", [], 90000
        s.img, s.vid, s.bag, s.state, s.maks, s.bos_bag = {}, {}, {}, {}, 0, []
        s.hata_ilan = hata_ilan
        for n, lid in enumerate(CIFT):
            b = 1000 * (n + 1)
            s.img[lid] = [b + i for i in range(1, 14)] + ([b + 50] if lid == "4570113157" else [])   # 14: GENEL_1 dahil
            s.bag[lid] = {700 + j: b + 9 + j for j in range(5)}                                     # value_id -> image
            s.vid[lid] = [{"video_id": b + 99}]
            s.state[lid] = "draft" if lid in state_draft else "active"
        s.renksiz = set(renksiz)
    def _c(s, *a): s.calls += 1; s.log.append(a)
    def _lid(s, path): return [p for p in path.split("/") if p.isdigit() and len(p) >= 4 and p != "9"][0]
    def get(s, path, params=None, ok404=False):
        s._c("GET", path); lid = s._lid(path)
        if path.endswith("variation-images"):
            return {"results": [{"property_id": 200, "value_id": v, "image_id": i} for v, i in s.bag[lid].items()]}
        if path.endswith("inventory"):
            vals = [] if lid in s.renksiz else RENK
            return {"products": [{"property_values": [{"property_name": "Primary color", "property_id": 200,
                                                       "value_ids": [700 + j], "values": [v]}]} for j, v in enumerate(vals)]}
        return {"state": s.state[lid], "images": [{"listing_image_id": x, "rank": r} for r, x in enumerate(s.img[lid], 1)],
                "videos": s.vid[lid]}
    def delete(s, path):
        s._c("DELETE", path); lid = s._lid(path); p = path.split("/")
        if p[-2] == "images":
            iid = int(p[-1]); s.img[lid].remove(iid)
            for v, i in list(s.bag[lid].items()):
                if i == iid: del s.bag[lid][v]; s.bos_bag.append((lid, v))       # bagli gorsel silindi -> bag bosaldi
        else:
            s.vid[lid] = []
    def post_file(s, path, files, data=None):
        s._c("POST", path); lid = s._lid(path)
        if lid == s.hata_ilan and len([x for x in s.log if x[0] == "POST" and lid in x[1]]) == 3:
            raise SystemExit("HTTP 500 sahte")
        s.nid += 1
        if path.endswith("/videos"):
            s.vid[lid] = [{"video_id": s.nid}]; return {"video_id": s.nid}
        s.img[lid].append(s.nid); s.maks = max(s.maks, len(s.img[lid]))
        if len(s.img[lid]) > 20: raise SystemExit("20 gorsel asildi")
        return {"listing_image_id": s.nid}
    def post_json(s, path, body):
        s._c("POSTJ", path); lid = s._lid(path)
        s.bag[lid] = {x["value_id"]: x["image_id"] for x in body["variation_images"]}
    def patch(s, path, data):
        s._c("PATCH", path); lid = s._lid(path)
        yeni = [int(x) for x in data["image_ids"].split(",")]
        assert sorted(yeni) == sorted(s.img[lid]); s.img[lid] = yeni

a = types.SimpleNamespace(confirm="GALERI_TEK", out=str(W / "out"), csv=str(W / "m.csv"), referans=str(W / "ref.json"),
                          yerel=str(W / "tek"), listing="1001,4570113157,1003,1004,1007,1005,1006," + G.REF, kota_alt=230)
api = FE(state_draft={"1005"}, renksiz={"1006"})
try:
    G.yaz(types.SimpleNamespace(**{**vars(a), "confirm": "X"}), api, "9"); k("yanlis onay -> yazma yok", False)
except SystemExit:
    k("yanlis onay -> yazma yok", api.calls == 0)
eski1, eski2 = list(api.img["1001"]), list(api.img["4570113157"])
G.yaz(a, api, "9")
S = {r["ilan"]: r for r in csv.DictReader(open(W / "out/SONUC_GALERI_TEK.csv", encoding="utf-8"))}
k("1001: PASS, 13 yeni gorsel, eski hic kalmadi, 35 cagri", S["1001"]["sonuc"] == "PASS" and len(api.img["1001"]) == 13
  and not set(eski1) & set(api.img["1001"]) and "cagri 35" in S["1001"]["not"], S["1001"]["not"])
k("1001: renk baglari yeni 9-13'e tasindi", list(api.bag["1001"].values()) == api.img["1001"][8:13])
k("1001: video degisti (1 adet)", len(api.vid["1001"]) == 1 and api.vid["1001"][0]["video_id"] != 1099)
k("4 kartli ilan: PASS, GENEL_1 (14. eski) silindi, 36 cagri", S["4570113157"]["sonuc"] == "PASS"
  and 2050 not in api.img["4570113157"] and "cagri 36" in S["4570113157"]["not"], S["4570113157"]["not"])
k("20 gorsel siniri hic asilmadi", api.maks <= 20, api.maks)
k("renk bagi hic bosa dusmedi", not api.bos_bag, api.bos_bag[:3])
k("GENEL_1 setli ilan ATLANDI, yazma yok", S["1003"]["sonuc"] == "ATLANDI" and not [x for x in api.log if "/1003/" in x[1] and x[0] != "GET"])
k("renk yerlesimi farkli ATLANDI", S["1004"]["sonuc"] == "ATLANDI" and "renk yerlesimi" in S["1004"]["not"])
k("dosya eksik ATLANDI", S["1007"]["sonuc"] == "ATLANDI" and "dosya yok" in S["1007"]["not"])
k("taslak ATLANDI, yazma yok", S["1005"]["sonuc"] == "ATLANDI" and "draft" in S["1005"]["not"]
  and not [x for x in api.log if "/1005/" in x[1] and x[0] != "GET"])
k("envanterde renk yok ATLANDI", S["1006"]["sonuc"] == "ATLANDI" and "renk" in S["1006"]["not"])
k("Cancer-Libra haric", S[G.REF]["sonuc"] == "ATLANDI")
api2 = FE(hata_ilan="1001")
G.yaz(types.SimpleNamespace(**{**vars(a), "out": str(W / "out2"), "listing": "1001,1008"}), api2, "9")
S2 = list(csv.DictReader(open(W / "out2/SONUC_GALERI_TEK.csv", encoding="utf-8")))
k("yazma hatasi: FAIL + adim adi + kosu durur", S2[0]["sonuc"] == "FAIL" and "adiminda hata" in S2[0]["not"] and len(S2) == 1, S2[0]["not"][:90])
api3 = FE(); api3.remaining = "200"
G.yaz(types.SimpleNamespace(**{**vars(a), "out": str(W / "out3")}), api3, "9")
k("kota 200 < 230 -> DURDU, cagri yok", next(csv.DictReader(open(W / "out3/SONUC_GALERI_TEK.csv")))["sonuc"] == "DURDU" and api3.calls == 0)
api4 = FE()
G.referans(types.SimpleNamespace(out=str(W / "ref_out")), api4, "9")
R4 = json.loads((W / "ref_out/REFERANS_SIRA.json").read_text())
k("referans modu: 3 GET, renkli rank 9-13, yazma yok", api4.calls == 3 and [s["rank"] for s in R4["sira"] if s["renk"]] == [9, 10, 11, 12, 13]
  and all(x[0] == "GET" for x in api4.log))
pl = types.SimpleNamespace(out=str(W / "plan"), csv=str(W / "m.csv"), referans=str(W / "ref.json"), plan=str(W / "yok.json"),
                           varsayilan_sayi=13, yerel=str(W / "tek"))
G.plan(pl)
TP = json.loads((W / "plan/TEK_PLAN.json").read_text())["ilan"]
k("plan: 4 kartli 36, digerleri 35 cagri; GENEL_1 setli hatali", TP["4570113157"]["cagri"] == 36 and TP["1001"]["cagri"] == 35 and TP["1003"]["hata"])
print(f"{sum(sonuc)}/{len(sonuc)} PASS"); sys.exit(0 if all(sonuc) else 1)
