#!/usr/bin/env python3
"""kapak_yukle_78 yerel testi - sahte Etsy, 3 ilan, 60 sn alti. Senaryolar:
kuru PLAN + silinecek liste; varyasyon bagli eski kapak BLOK; temiz apply (yedek, rank 1, silme, sayi ayni);
tekrar kuru -> ZATEN; plan-canli uyusmazligi DUR (yazma yok); yukleme geri okuma FAIL -> silme YOK, DUR."""
import csv
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kapak_yukle_78 as K  # noqa: E402

K.OKUMA_BEKLE = 0
K.SIRA_BEKLE = 0
K.YUKLEME_BEKLE = 0
K.BEKLENEN = 3
K.KAPAK_BOYUT = (400, 300)
K.time.sleep = lambda s: None
import pod_cover_from_video  # noqa: E402
pod_cover_from_video.time.sleep = lambda s: None

TMP = Path(tempfile.mkdtemp())
IDS = [("111", "ARIES_LEO", "Aries", "Leo"), ("222", "CANCER_LIBRA", "Cancer", "Libra"),
       ("333", "PISCES_VIRGO", "Pisces", "Virgo")]


def resim(p, w=300, h=225, renk=(20, 30, 90)):
    Image.effect_noise((w, h), 60).convert("RGB").save(p, quality=95)


class Fake:
    def __init__(self, bozuk_rank=False, bozuk_bag=False, tie=0, bosluk=False):
        self.bosluk = bosluk  # Etsy silmeden sonra siralari sikistirmaz (28 Eyl 4570110641)
        self.rank_say, self.cozum, self.hic = {}, {}, set()  # cozum[lid]: kacinci rank cagrisi cozer; hic: asla
        self.remaining = "5000"; self.calls = 0; self.nid = 9000; self.yaz = []; self.store = None
        self.bozuk_rank = bozuk_rank; self.bozuk_bag = bozuk_bag
        self.tie = tie; self.bekleyen = {}  # tie: yuklemeden sonra kac okuma boyunca rank 1 cift kalir (99 = hic)
        self.L = {}
        for lid, *_ in IDS:
            imgs = [{"listing_image_id": int(lid) * 100 + n, "rank": n, "alt_text": f"eski {n}",
                     "full_width": 300, "full_height": 225, "url_fullxfull": f"fake://{lid}/{n}"} for n in range(1, 13)]
            self.L[lid] = {"state": "active", "imgs": imgs,
                           "vimg": [{"property_id": 1, "value_id": 2, "value": "MB", "image_id": int(lid) * 100 + 5},
                                    {"property_id": 1, "value_id": 3, "value": "DB", "image_id": int(lid) * 100 + 6}],
                           "vids": [{"video_id": 7}]}

    def _renum(self, lid):
        im = sorted(self.L[lid]["imgs"], key=lambda x: x["rank"])
        for i, x in enumerate(im, 1):
            x["rank"] = i
        self.L[lid]["imgs"] = im

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        if path.endswith("/images"):
            if lid in self.bekleyen:
                self.bekleyen[lid][0] -= 1
                if self.bekleyen[lid][0] < 0:
                    yeni = self.bekleyen.pop(lid)[1]
                    for x in self.L[lid]["imgs"]:
                        if x["listing_image_id"] != yeni:
                            x["rank"] += 1
                    self._renum(lid)
            return {"results": sorted([dict(x) for x in self.L[lid]["imgs"]], key=lambda x: x["rank"])}
        if path.endswith("/variation-images"):
            return {"results": [dict(v) for v in self.L[lid]["vimg"]]}
        if path.endswith("/videos"):
            return {"results": [dict(v) for v in self.L[lid]["vids"]]}
        return {"listing_id": int(lid), "state": self.L[lid]["state"]}

    def post_file(self, path, files, data=None):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        self.yaz.append(("POST", lid))
        if "image" in files:
            self.nid += 1
            fh = files["image"][1]
            with Image.open(fh) as im:
                w, h = im.size
            rank = 99 if self.bozuk_rank else int(data["rank"])
            yeni = {"listing_image_id": self.nid, "rank": rank, "alt_text": data["alt_text"],
                    "full_width": w, "full_height": h, "url_fullxfull": f"fake://yeni/{self.nid}"}
            if self.tie and rank == 1:  # Etsy: yeni ve eski ayni anda rank 1 (28 Eyl 4570125580)
                self.L[lid]["imgs"].insert(1, yeni)
                self.bekleyen[lid] = [self.tie, self.nid]
                return {"listing_image_id": self.nid}
            for x in self.L[lid]["imgs"]:
                if x["rank"] >= rank:
                    x["rank"] += 1
            self.L[lid]["imgs"].append(yeni)
            self._renum(lid)
            return {"listing_image_id": self.nid}
        # rank duzeltme: alt_text gonderilmezse Etsy alt metni BOSALTIR (28 Eyl gozlemi)
        self.yaz[-1] = ("RANK", lid)
        if self.bozuk_rank:
            return {}
        iid = int(files["listing_image_id"][1])
        x = next(i for i in self.L[lid]["imgs"] if i["listing_image_id"] == iid)
        x["alt_text"] = files["alt_text"][1] if "alt_text" in files else ""
        self.rank_say[lid] = self.rank_say.get(lid, 0) + 1
        if lid in self.hic or (lid in self.cozum and self.rank_say[lid] < self.cozum[lid]):
            return {}
        self.bekleyen.pop(lid, None)
        for y in self.L[lid]["imgs"]:
            if y is not x:
                y["rank"] = y["rank"] * 10 + 5
        x["rank"] = 1
        self._renum(lid)
        return {}

    def post_json(self, path, body):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        self.yaz.append(("VARYASYON", lid))
        if not self.bozuk_bag:
            ad = {(v["property_id"], v["value_id"]): v["value"] for v in self.L[lid]["vimg"]}
            self.L[lid]["vimg"] = [{**v, "value": ad[(v["property_id"], v["value_id"])]} for v in body["variation_images"]]
        return {}

    def delete(self, path):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        iid = int(path.rsplit("/", 1)[1])
        self.yaz.append(("DELETE", lid, iid))
        self.L[lid]["imgs"] = [x for x in self.L[lid]["imgs"] if x["listing_image_id"] != iid]
        if not self.bosluk:
            self._renum(lid)
        return {}


def hazirla():
    ids = TMP / "ids.csv"
    with open(ids, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["listing_id", "cift", "a", "b"])
        for r in IDS:
            w.writerow(r)
    kd = TMP / "kapak"
    kd.mkdir(exist_ok=True)
    for _, c, *_ in IDS:
        resim(kd / f"KAPAK_{c}.jpg", 400, 300)
    return ids, kd


def args(ids, kd, out, **kw):
    d = dict(ids=str(ids), kapak_dir=str(kd), out=str(out), plan=None, yedek_drive=None,
             apply=False, confirm="", quota_min=60, devam={}, devam_eski={}, kaynak={"klasor": "test", "ozet": "PASS: 3 / 3"})
    d.update(kw)
    return SimpleNamespace(**d)


def indir_fake(url, yol):
    resim(yol)


def main():
    K.indir = indir_fake
    ids, kd = hazirla()
    satirlar, kapak, sorun, fazla = K.kapaklar_oku(ids, kd)
    kont = {}
    kont["kapak okuma"] = not sorun and not fazla and len(kapak) == 3 and kapak["ARIES_LEO"]["alt"].startswith("Aries and Leo")
    kont["alt metinde uzun/orta tire yok"] = all("–" not in k["alt"] and "—" not in k["alt"] for k in kapak.values())

    # 1) varyasyon bagli eski kapak -> PLAN + bag tasi; apply: yedek, bag yeni kapakta, digeri ayni, sonra silme
    f = Fake(); f.L["222"]["vimg"][0]["image_id"] = 22201
    o1 = TMP / "o1"
    ok = K.kuru(args(ids, kd, o1), f, "S", o1, satirlar, kapak, sorun, fazla)
    p = json.loads((o1 / "PLAN.json").read_text())["satirlar"]
    kont["bagli eski kapak: PLAN + bag_tasi (MB)"] = ok and [r["durum"] for r in p] == ["PLAN"] * 3 and \
        [b["value"] for b in p[1]["bag_tasi"]] == ["MB"] and p[0]["bag_tasi"] == []
    kont["rapor: bag tasinacak 1 ilan"] = "Bag tasinacak 1 ilan" in (o1 / "report.md").read_text()
    kont["kuru: yazma yok"] = f.yaz == []
    yd1 = TMP / "yd1"
    ok = K.apply(args(ids, kd, TMP / "o1a", plan=str(o1 / "PLAN.json"), yedek_drive=str(yd1), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o1a", kapak)
    yeni222 = f.L["222"]["imgs"][0]["listing_image_id"]
    kont["bag tasima apply PASS"] = ok
    kont["MB bagi yeni kapakta, DB bagi ayni"] = [(v["value"], v["image_id"]) for v in f.L["222"]["vimg"]] == \
        [("MB", yeni222), ("DB", 22206)]
    kont["sira: yukle -> rank1+alt -> bag -> sil (222)"] = [x[0] for x in f.yaz if x[1] == "222"] == \
        ["POST", "RANK", "VARYASYON", "DELETE"]
    kont["bagsiz ilanda varyasyon cagrisi yok"] = not any(x[0] == "VARYASYON" and x[1] != "222" for x in f.yaz)
    kont["varyasyon yedegi Drive'da"] = (yd1 / "222_VARYASYON_ONCE.json").is_file()

    # 1b) bag tasima geri okumasi FAIL -> eski kapak silinmez, DUR
    f = Fake(bozuk_bag=True); f.L["111"]["vimg"][0]["image_id"] = 11101
    o1b = TMP / "o1b"
    K.kuru(args(ids, kd, o1b), f, "S", o1b, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o1c", plan=str(o1b / "PLAN.json"), yedek_drive=str(TMP / "yd1c"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o1c", kapak)
    kont["bag tasima FAIL: silme yok, DUR"] = (not ok) and not any(x[0] == "DELETE" for x in f.yaz) and \
        {x[1] for x in f.yaz} == {"111"}

    # 2) temiz kuru + apply
    f = Fake(); o2 = TMP / "o2"
    ok = K.kuru(args(ids, kd, o2), f, "S", o2, satirlar, kapak, sorun, fazla)
    kont["kuru PASS 3/3 PLAN"] = ok and (o2 / "SILINECEK_IMAGE_ID.txt").read_text().splitlines() == \
        ["111,11101", "222,22201", "333,33301"]
    kont["rapor silinecek listesi"] = "Silinecek 3 image_id" in (o2 / "report.md").read_text()
    o3 = TMP / "o3"; yd = TMP / "drive_yedek"
    ok = K.apply(args(ids, kd, o3, plan=str(o2 / "PLAN.json"), yedek_drive=str(yd), apply=True,
                      confirm=K.ONAY), f, "S", o3, kapak)
    kont["apply PASS 3/3"] = ok
    kont["her ilan: sayi 12, rank1 yeni, eski yok"] = all(
        len(f.L[l]["imgs"]) == 12 and f.L[l]["imgs"][0]["listing_image_id"] > 9000
        and int(l) * 100 + 1 not in [x["listing_image_id"] for x in f.L[l]["imgs"]] for l, *_ in IDS)
    kont["yalniz plandaki eski id'ler silindi"] = [x for x in f.yaz if x[0] == "DELETE"] == \
        [("DELETE", "111", 11101), ("DELETE", "222", 22201), ("DELETE", "333", 33301)]
    kont["yedek dosyalari hedefte"] = sorted(p.name for p in yd.iterdir()) == \
        ["111_11101.jpg", "222_22201.jpg", "333_33301.jpg"]
    kont["kalan gorsel sirasi korundu"] = [x["listing_image_id"] for x in f.L["111"]["imgs"][1:]] == \
        [11100 + n for n in range(2, 13)]

    # 3) tekrar kuru -> ZATEN (ikinci silme plani cikmaz)
    o4 = TMP / "o4"
    K.kuru(args(ids, kd, o4), f, "S", o4, satirlar, kapak, sorun, fazla)
    p = json.loads((o4 / "PLAN.json").read_text())["satirlar"]
    kont["tekrar kuru: 3 ZATEN, silinecek 0"] = [r["durum"] for r in p] == ["ZATEN"] * 3 and \
        (o4 / "SILINECEK_IMAGE_ID.txt").read_text() == ""

    # 4) plan sonrasi canli degisti -> DUR, yazma yok
    f = Fake(); o5 = TMP / "o5"
    K.kuru(args(ids, kd, o5), f, "S", o5, satirlar, kapak, sorun, fazla)
    f.L["111"]["imgs"][0]["rank"], f.L["111"]["imgs"][1]["rank"] = 2, 1; f._renum("111")
    o6 = TMP / "o6"
    ok = K.apply(args(ids, kd, o6, plan=str(o5 / "PLAN.json"), yedek_drive=str(TMP / "yd6"), apply=True,
                      confirm=K.ONAY), f, "S", o6, kapak)
    s = json.loads((o6 / "SONUC.json").read_text())
    kont["plan-canli uyusmazligi: DUR, yazma yok"] = (not ok) and f.yaz == [] and len(s) == 1 and "on kontrol" in s[0]["hata"]

    # 5) yukleme 1. siraya oturmuyor -> silme YOK, ilk ilanda DUR
    f = Fake(bozuk_rank=True); o7 = TMP / "o7"
    K.kuru(args(ids, kd, o7), f, "S", o7, satirlar, kapak, sorun, fazla)
    o8 = TMP / "o8"
    ok = K.apply(args(ids, kd, o8, plan=str(o7 / "PLAN.json"), yedek_drive=str(TMP / "yd8"), apply=True,
                      confirm=K.ONAY), f, "S", o8, kapak)
    kont["yukleme FAIL: silme yok, 2. ilana gecilmedi"] = (not ok) and not any(x[0] == "DELETE" for x in f.yaz) \
        and {x[1] for x in f.yaz} == {"111"} and len(f.L["111"]["imgs"]) == 13

    # 6) kapak dosyasi plandan sonra degisti -> DUR
    f = Fake(); o9 = TMP / "o9"
    K.kuru(args(ids, kd, o9), f, "S", o9, satirlar, kapak, sorun, fazla)
    k2 = json.loads(json.dumps(kapak)); k2["ARIES_LEO"]["sha256"] = "x"
    try:
        K.apply(args(ids, kd, TMP / "o10", plan=str(o9 / "PLAN.json"), yedek_drive=str(TMP / "yd10"),
                     apply=True, confirm=K.ONAY), f, "S", TMP / "o10", k2)
        kont["kapak sha degisti: DUR"] = False
    except SystemExit:
        kont["kapak sha degisti: DUR"] = f.yaz == []

    # 7) kuru yedegi Drive'da (boyut = plan) -> apply yeniden indirmez; kuru yedek + galeri JSON yazar
    f = Fake(); o11 = TMP / "o11"
    K.kuru(args(ids, kd, o11), f, "S", o11, satirlar, kapak, sorun, fazla)
    kont["kuru yedek: 3 eski kapak + GALERI_ONCE.json"] = sorted(p.name for p in (o11 / "yedek").iterdir()) == \
        ["111_11101.jpg", "222_22201.jpg", "333_33301.jpg", "GALERI_ONCE.json"]
    sayac = []
    K.indir = lambda url, yol: (sayac.append(url), indir_fake(url, yol))
    ok = K.apply(args(ids, kd, TMP / "o12", plan=str(o11 / "PLAN.json"), yedek_drive=str(o11 / "yedek"),
                      apply=True, confirm=K.ONAY), f, "S", TMP / "o12", kapak)
    kont["yedek Drive'da: apply PASS, yeniden indirme yok"] = ok and sayac == []
    K.indir = indir_fake

    # 8) eslesmeyen cift (kapak yok) -> BLOK
    (kd / "KAPAK_PISCES_VIRGO.jpg").rename(TMP / "x.jpg")
    s2, k3, so3, fz3 = K.kapaklar_oku(ids, kd)
    f = Fake(); o13 = TMP / "o13"
    ok = K.kuru(args(ids, kd, o13), f, "S", o13, s2, k3, so3, fz3)
    p = json.loads((o13 / "PLAN.json").read_text())["satirlar"]
    kont["eslesmeyen cift: BLOK"] = (not ok) and p[2]["durum"] == "BLOK" and "eslesmeyen" in p[2]["neden"]
    (TMP / "x.jpg").rename(kd / "KAPAK_PISCES_VIRGO.jpg")

    # 9) Etsy rank 1 cift (2 okuma) -> tekillesmeyi bekler, PASS; alt metin korunur
    f = Fake(tie=2); o20 = TMP / "o20"
    K.kuru(args(ids, kd, o20), f, "S", o20, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o21", plan=str(o20 / "PLAN.json"), yedek_drive=str(TMP / "yd21"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o21", kapak)
    kont["rank 1 cift -> bekle -> PASS, alt dolu"] = ok and all(
        f.L[l]["imgs"][0]["alt_text"] and f.L[l]["imgs"][0]["listing_image_id"] > 9000 for l, *_ in IDS)

    # 9b) Etsy rank 1 ciftini kendiliginden hic cozmuyor (4570126104) -> hemen rank1+alt cagrisi cozer -> PASS
    f = Fake(tie=50); o40 = TMP / "o40"
    K.kuru(args(ids, kd, o40), f, "S", o40, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o41", plan=str(o40 / "PLAN.json"), yedek_drive=str(TMP / "yd41"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o41", kapak)
    kont["rank 1 cift kendiliginden cozulmuyor -> rank1+alt cagrisi -> PASS"] = ok and all(
        f.L[l]["imgs"][0]["alt_text"] == kapak[c]["alt"] and len(f.L[l]["imgs"]) == 12 for l, c, *_ in IDS) \
        and all([x[0] for x in f.yaz if x[1] == l] == ["POST", "RANK", "DELETE"] for l, *_ in IDS)

    # 10) rank 1 cift hic tekillesmiyor -> her ilan YARIM (DUR yok), 2. turda da YARIM, silme yok
    f = Fake(tie=10 ** 6); f.hic = {"111", "222", "333"}; o22 = TMP / "o22"
    K.kuru(args(ids, kd, o22), f, "S", o22, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o23", plan=str(o22 / "PLAN.json"), yedek_drive=str(TMP / "yd23"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o23", kapak)
    s23 = json.loads((TMP / "o23" / "SONUC.json").read_text())
    kont["tekillesmiyor: 3 ilan YARIM (DUR yok), 2. tur da YARIM, silme yok"] = (not ok) and \
        not any(x[0] == "DELETE" for x in f.yaz) and [r["sonuc"] for r in s23] == ["YARIM"] * 6 and \
        [r["tur"] for r in s23] == ["1. tur"] * 3 + ["2. tur"] * 3 and \
        all([x[0] for x in f.yaz if x[1] == l] == ["POST", "RANK", "RANK", "RANK", "RANK"] for l, *_ in IDS) and \
        "YARIM 3" in (TMP / "o23" / "report.md").read_text()

    # 10b) 111 1. turda YARIM (2 rank cagrisi yetmez), 222/333 PASS; 2. turda 111 kesin id ile tamamlanir (bag dahil)
    f = Fake(tie=10 ** 6); f.cozum = {"111": 3, "222": 1, "333": 1}; f.L["111"]["vimg"][0]["image_id"] = 11101
    o50 = TMP / "o50"
    K.kuru(args(ids, kd, o50), f, "S", o50, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o51", plan=str(o50 / "PLAN.json"), yedek_drive=str(TMP / "yd51"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o51", kapak)
    s51 = json.loads((TMP / "o51" / "SONUC.json").read_text())
    kont["YARIM -> 2. tur PASS (111), 222/333 1. turda PASS"] = ok and \
        [(r["listing_id"], r["tur"], r["sonuc"]) for r in s51] == [("111", "1. tur", "YARIM"), ("222", "1. tur", "PASS"),
                                                                   ("333", "1. tur", "PASS"), ("111", "2. tur", "PASS")]
    kont["2. tur: 111 yeni dosya yuklenmedi, bag tasindi, eski silindi"] = \
        [x[0] for x in f.yaz if x[1] == "111"] == ["POST", "RANK", "RANK", "RANK", "VARYASYON", "DELETE"] and \
        f.L["111"]["vimg"][0]["image_id"] == f.L["111"]["imgs"][0]["listing_image_id"] and \
        11101 not in [x["listing_image_id"] for x in f.L["111"]["imgs"]] and len(f.L["111"]["imgs"]) == 12
    kont["rapor: PASS 3, YARIM 0, 2. turda 1"] = "PASS 3" in (TMP / "o51" / "report.md").read_text() and \
        "YARIM 0" in (TMP / "o51" / "report.md").read_text() and "2. turda 1" in (TMP / "o51" / "report.md").read_text()

    # 10c) kota tabani: kalan < 400 -> yeni ilana baslanmaz, yazma yok
    f = Fake(); o52 = TMP / "o52"
    K.kuru(args(ids, kd, o52), f, "S", o52, satirlar, kapak, sorun, fazla)
    f.remaining = "350"
    ok = K.apply(args(ids, kd, TMP / "o53", plan=str(o52 / "PLAN.json"), yedek_drive=str(TMP / "yd53"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o53", kapak)
    kont["kota < 400: yeni ilana baslanmadi, yazma yok"] = (not ok) and f.yaz == [] and \
        "KOTA < 400 DURDU" in (TMP / "o53" / "report.md").read_text()

    # 11) 4570125580 benzeri yarim durum: yeni gorsel rank 1 cift + alt BOS -> --devam kesin id ile tamamlanir
    f = Fake(); f.L["111"]["vimg"][0]["image_id"] = 11101; o24 = TMP / "o24"
    K.kuru(args(ids, kd, o24), f, "S", o24, satirlar, kapak, sorun, fazla)
    f.L["111"]["imgs"].insert(1, {"listing_image_id": 9500, "rank": 1, "alt_text": "", "full_width": 400,
                                  "full_height": 300, "url_fullxfull": "fake://yeni/9500"})
    f.nid = 9600
    ok = K.apply(args(ids, kd, TMP / "o25", plan=str(o24 / "PLAN.json"), yedek_drive=str(TMP / "yd25"), apply=True,
                      confirm=K.ONAY, devam={"111": 9500}, devam_eski={"111": 11101}), f, "S", TMP / "o25", kapak)
    i111 = f.L["111"]["imgs"]
    kont["devam: 9500 rank 1 + alt dolu, 11101 silindi, bag 9500'de, 12 gorsel"] = ok and \
        i111[0]["listing_image_id"] == 9500 and i111[0]["alt_text"] == kapak["ARIES_LEO"]["alt"] and \
        11101 not in [x["listing_image_id"] for x in i111] and len(i111) == 12 and \
        f.L["111"]["vimg"][0]["image_id"] == 9500
    kont["devam: 111'e yeni dosya yuklenmedi"] = [x[0] for x in f.yaz if x[1] == "111"] == ["RANK", "VARYASYON", "DELETE"]
    kont["devam: eski id plandan farkliysa DUR"] = True
    f2 = Fake(); o26 = TMP / "o26"
    K.kuru(args(ids, kd, o26), f2, "S", o26, satirlar, kapak, sorun, fazla)
    f2.L["111"]["imgs"].insert(1, {"listing_image_id": 9500, "rank": 1, "alt_text": "", "full_width": 400,
                                   "full_height": 300, "url_fullxfull": "fake://yeni/9500"})
    ok = K.apply(args(ids, kd, TMP / "o27", plan=str(o26 / "PLAN.json"), yedek_drive=str(TMP / "yd27"), apply=True,
                      confirm=K.ONAY, devam={"111": 9500}, devam_eski={"111": 99999}), f2, "S", TMP / "o27", kapak)
    kont["devam: eski id plandan farkliysa DUR"] = (not ok) and f2.yaz == []

    # 12) ayni planla tekrar apply -> tamamlananlar ZATEN, yazma yok
    n = len(f.yaz)
    ok = K.apply(args(ids, kd, TMP / "o28", plan=str(o24 / "PLAN.json"), yedek_drive=str(TMP / "yd25"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o28", kapak)
    s28 = json.loads((TMP / "o28" / "SONUC.json").read_text())
    kont["tekrar apply: 3 ZATEN, yazma yok"] = ok and [r["sonuc"] for r in s28] == ["ZATEN"] * 3 and len(f.yaz) == n

    # 13) Etsy silmeden sonra siralari sikistirmiyor (1, 3, 4..) -> PASS; tekrar apply -> ZATEN
    f = Fake(bosluk=True); f.L["222"]["vimg"][0]["image_id"] = 22201; o30 = TMP / "o30"
    K.kuru(args(ids, kd, o30), f, "S", o30, satirlar, kapak, sorun, fazla)
    ok = K.apply(args(ids, kd, TMP / "o31", plan=str(o30 / "PLAN.json"), yedek_drive=str(TMP / "yd31"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o31", kapak)
    rk = [x["rank"] for x in f.L["222"]["imgs"]]
    kont["bosluklu sira (1,3,4..): apply PASS"] = ok and rk[:3] == [1, 3, 4] and len(rk) == 12
    n = len(f.yaz)
    ok = K.apply(args(ids, kd, TMP / "o32", plan=str(o30 / "PLAN.json"), yedek_drive=str(TMP / "yd31"), apply=True,
                      confirm=K.ONAY), f, "S", TMP / "o32", kapak)
    s32 = json.loads((TMP / "o32" / "SONUC.json").read_text())
    kont["bosluklu sira: tekrar apply 3 ZATEN, yazma yok"] = ok and [r["sonuc"] for r in s32] == ["ZATEN"] * 3 \
        and len(f.yaz) == n
    kont["sira_tekil: cift rank FAIL, bosluk PASS"] = (not K.sira_tekil([{"rank": 1}, {"rank": 1}, {"rank": 2}])) \
        and K.sira_tekil([{"rank": 1}, {"rank": 3}, {"rank": 4}])

    for k, v in kont.items():
        print(f"{'PASS' if v else 'FAIL'} {k}")
    ok = all(kont.values())
    print(f"SONUC: {'PASS' if ok else 'FAIL'} ({sum(kont.values())}/{len(kont)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
