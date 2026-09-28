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
K.BEKLENEN = 3
K.time.sleep = lambda s: None
import pod_cover_from_video  # noqa: E402
pod_cover_from_video.time.sleep = lambda s: None

TMP = Path(tempfile.mkdtemp())
IDS = [("111", "ARIES_LEO", "Aries", "Leo"), ("222", "CANCER_LIBRA", "Cancer", "Libra"),
       ("333", "PISCES_VIRGO", "Pisces", "Virgo")]


def resim(p, w=300, h=225, renk=(20, 30, 90)):
    Image.effect_noise((w, h), 60).convert("RGB").save(p, quality=95)


class Fake:
    def __init__(self, bozuk_rank=False):
        self.remaining = "5000"; self.calls = 0; self.nid = 9000; self.yaz = []; self.store = None
        self.bozuk_rank = bozuk_rank
        self.L = {}
        for lid, *_ in IDS:
            imgs = [{"listing_image_id": int(lid) * 100 + n, "rank": n, "alt_text": f"eski {n}",
                     "full_width": 300, "full_height": 225, "url_fullxfull": f"fake://{lid}/{n}"} for n in range(1, 13)]
            self.L[lid] = {"state": "active", "imgs": imgs, "vimg": [{"property_id": 1, "value_id": 2, "value": "MB",
                                                                     "image_id": int(lid) * 100 + 5}], "vids": [{"video_id": 7}]}

    def _renum(self, lid):
        im = sorted(self.L[lid]["imgs"], key=lambda x: x["rank"])
        for i, x in enumerate(im, 1):
            x["rank"] = i
        self.L[lid]["imgs"] = im

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        if path.endswith("/images"):
            return {"results": [dict(x) for x in self.L[lid]["imgs"]]}
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
            for x in self.L[lid]["imgs"]:
                if x["rank"] >= rank:
                    x["rank"] += 1
            self.L[lid]["imgs"].append({"listing_image_id": self.nid, "rank": rank, "alt_text": data["alt_text"],
                                        "full_width": w, "full_height": h, "url_fullxfull": f"fake://yeni/{self.nid}"})
            self._renum(lid)
            return {"listing_image_id": self.nid}
        return {}  # rank duzeltme: bozuk modda etkisiz

    def delete(self, path):
        self.calls += 1
        lid = path.split("/listings/")[1].split("/")[0]
        iid = int(path.rsplit("/", 1)[1])
        self.yaz.append(("DELETE", lid, iid))
        self.L[lid]["imgs"] = [x for x in self.L[lid]["imgs"] if x["listing_image_id"] != iid]
        self._renum(lid)
        return {}


def hazirla():
    ids = TMP / "ids.csv"
    with open(ids, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["listing_id", "cift", "a", "b"])
        for r in IDS:
            w.writerow(r)
    kd, idir = TMP / "kapak", TMP / "isim"
    kd.mkdir(exist_ok=True); idir.mkdir(exist_ok=True)
    for _, c, *_ in IDS:
        resim(kd / f"KAPAK_{c}.jpg", 400, 300)
        (idir / f"{c}.json").write_text(json.dumps({"isim1": "EMILY", "isim2": "JAMES"}))
    return ids, kd, idir


def args(ids, kd, idir, out, **kw):
    d = dict(ids=str(ids), kapak_dir=str(kd), isim_dir=str(idir), out=str(out), plan=None, yedek_drive=None,
             apply=False, confirm="", quota_min=60)
    d.update(kw)
    return SimpleNamespace(**d)


def indir_fake(url, yol):
    resim(yol)


def main():
    K.indir = indir_fake
    ids, kd, idir = hazirla()
    satirlar, kapak, hata = K.kapaklar_oku(ids, kd, idir)
    kont = {}
    kont["kapak/isim okuma"] = not hata and len(kapak) == 3 and "Emily and James" in kapak["ARIES_LEO"]["alt"]
    kont["alt metinde uzun/orta tire yok"] = all("–" not in k["alt"] and "—" not in k["alt"] for k in kapak.values())

    # 1) varyasyon bagli eski kapak -> BLOK
    f = Fake(); f.L["222"]["vimg"][0]["image_id"] = 22201
    o1 = TMP / "o1"
    ok = K.kuru(args(ids, kd, idir, o1), f, "S", o1, satirlar, kapak)
    p = json.loads((o1 / "PLAN.json").read_text())["satirlar"]
    kont["BLOK: varyasyona bagli eski kapak"] = (not ok) and [r["durum"] for r in p] == ["PLAN", "BLOK", "PLAN"]
    kont["kuru: yazma yok"] = f.yaz == []

    # 2) temiz kuru + apply
    f = Fake(); o2 = TMP / "o2"
    ok = K.kuru(args(ids, kd, idir, o2), f, "S", o2, satirlar, kapak)
    kont["kuru PASS 3/3 PLAN"] = ok and (o2 / "SILINECEK_IMAGE_ID.txt").read_text().splitlines() == \
        ["111,11101", "222,22201", "333,33301"]
    kont["rapor silinecek listesi"] = "Silinecek 3 image_id" in (o2 / "report.md").read_text()
    o3 = TMP / "o3"; yd = TMP / "drive_yedek"
    ok = K.apply(args(ids, kd, idir, o3, plan=str(o2 / "PLAN.json"), yedek_drive=str(yd), apply=True,
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
    K.kuru(args(ids, kd, idir, o4), f, "S", o4, satirlar, kapak)
    p = json.loads((o4 / "PLAN.json").read_text())["satirlar"]
    kont["tekrar kuru: 3 ZATEN, silinecek 0"] = [r["durum"] for r in p] == ["ZATEN"] * 3 and \
        (o4 / "SILINECEK_IMAGE_ID.txt").read_text() == ""

    # 4) plan sonrasi canli degisti -> DUR, yazma yok
    f = Fake(); o5 = TMP / "o5"
    K.kuru(args(ids, kd, idir, o5), f, "S", o5, satirlar, kapak)
    f.L["111"]["imgs"][0]["rank"], f.L["111"]["imgs"][1]["rank"] = 2, 1; f._renum("111")
    o6 = TMP / "o6"
    ok = K.apply(args(ids, kd, idir, o6, plan=str(o5 / "PLAN.json"), yedek_drive=str(TMP / "yd6"), apply=True,
                      confirm=K.ONAY), f, "S", o6, kapak)
    s = json.loads((o6 / "SONUC.json").read_text())
    kont["plan-canli uyusmazligi: DUR, yazma yok"] = (not ok) and f.yaz == [] and len(s) == 1 and "on kontrol" in s[0]["hata"]

    # 5) yukleme 1. siraya oturmuyor -> silme YOK, ilk ilanda DUR
    f = Fake(bozuk_rank=True); o7 = TMP / "o7"
    K.kuru(args(ids, kd, idir, o7), f, "S", o7, satirlar, kapak)
    o8 = TMP / "o8"
    ok = K.apply(args(ids, kd, idir, o8, plan=str(o7 / "PLAN.json"), yedek_drive=str(TMP / "yd8"), apply=True,
                      confirm=K.ONAY), f, "S", o8, kapak)
    kont["yukleme FAIL: silme yok, 2. ilana gecilmedi"] = (not ok) and not any(x[0] == "DELETE" for x in f.yaz) \
        and {x[1] for x in f.yaz} == {"111"} and len(f.L["111"]["imgs"]) == 13

    # 6) kapak dosyasi plandan sonra degisti -> DUR
    f = Fake(); o9 = TMP / "o9"
    K.kuru(args(ids, kd, idir, o9), f, "S", o9, satirlar, kapak)
    k2 = json.loads(json.dumps(kapak)); k2["ARIES_LEO"]["sha256"] = "x"
    try:
        K.apply(args(ids, kd, idir, TMP / "o10", plan=str(o9 / "PLAN.json"), yedek_drive=str(TMP / "yd10"),
                     apply=True, confirm=K.ONAY), f, "S", TMP / "o10", k2)
        kont["kapak sha degisti: DUR"] = False
    except SystemExit:
        kont["kapak sha degisti: DUR"] = f.yaz == []

    for k, v in kont.items():
        print(f"{'PASS' if v else 'FAIL'} {k}")
    ok = all(kont.values())
    print(f"SONUC: {'PASS' if ok else 'FAIL'} ({sum(kont.values())}/{len(kont)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
