#!/usr/bin/env python3
"""galeri_ci11.py + ci11_dosya_kapi.py yerel testi. Ag / Drive / Etsy / token YOK: sahte Etsy (bellekte galeri, renk baglari, envanter),
sentetik ilanlar (9000000001..3) ve sentetik 3000x2250 JPEG'ler. Senaryolar: dosya kapisi (PASS, boyut, PNG, sha, eksik, OCR frame
VAR rapor, FAZLA); kuru PLAN (yazim yok, istek 4); alt metin TASLAK iken yazim yok; pilot sadece (PASS, 1-10 ayni, 11 yeni, 5 bag,
istek = en az tahmini, diger ilanlar dokunulmaz); haric; canli != plan BLOK; zaten yapilmis ZATEN (kuru + yazim, yazim yok);
CI degeri yok BLOK; geri okuma hatasi (bag POST'u tutmaz) -> geri alma, sonraki ilan KALAN; yukleme rank 1'e oturur -> geri alma;
YARIM BLOK; v11 durumu (CI kapak + 5 bag) BLOK; canli okuma farki BLOK; plan_damga bozuk DUR; kota KALAN.
Kullanim: python3 scripts/kapak78/test_galeri_ci11.py (Pillow surumu: is akisinin kurdugu 11.0.0 ile kosulmali; CLAUDE.md PILLOW)."""
import copy
import csv
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
import galeri_ci11 as C  # noqa: E402
import ci11_dosya_kapi as D  # noqa: E402

G.OKUMA_BEKLE = 0; Y.BEKLE_429 = 0
SONUC = []
SHOP = "1"
ILAN = [("9000000001", "ARIES_LEO", "Aries", "Leo"), ("9000000002", "CANCER_CANCER", "Cancer", "Cancer"),
        ("9000000003", "LIBRA_VIRGO", "Libra", "Virgo")]
VID = {"Midnight Blue": 101, "Deep Black": 102, "Pure White": 103, "Champagne Ivory": 104, "Warm Parchment": 105}


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


# ------------------------------------------------------------------ sahte Etsy
class Sahte:
    """Etsy v3 alt kumesi: getListing, getListingImages, getListingVariationImages, getListingInventory, uploadListingImage (rank),
    updateVariationImages (tum seti degistirir), deleteListingImage. Ayarlar: bag_tutmaz (CI bag POST'u yok sayilir), rank_yok
    (yukleme rank'i yok sayilir, 1'e oturur), ci_yok (envanterde CI yok)."""
    def __init__(self, ilanlar, kalan=5000):
        self.L, self.calls, self.remaining, self.yazimlar, self._n = ilanlar, 0, kalan, [], 9_000_000
        self.bag_tutmaz = False; self.rank_yok = False

    def kota_kapisi(self, ne="is"):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _say(self):
        if self.remaining < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < 10")
        self.calls += 1; self.remaining -= 1

    def _lid(self, path):
        return re.search(r"/listings/(\d+)", path).group(1)

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            raise AssertionError("yazim _call ile gelmez")
        self._say()
        x = self.L[self._lid(path)]
        if path.endswith("/images"):
            return {"results": copy.deepcopy(sorted(x["images"], key=lambda i: i["rank"]))}
        if path.endswith("/variation-images"):
            ad = {v: k for k, v in VID.items()}
            return {"results": [dict(b, value=ad.get(b["value_id"])) for b in copy.deepcopy(x["var"])]}
        if path.endswith("/inventory"):
            return {"products": [{"property_values": [{"property_id": 200, "value_ids": [VID[n]], "values": [n]},
                                                      {"property_id": 513, "value_ids": [7], "values": ["8x10"]}]} for n in x["renkler"]]}
        return {"state": x["state"]}

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params, ok404=ok404)

    def post_file(self, path, files, data=None, tekrar=3):
        self._say(); lid = self._lid(path); x = self.L[lid]
        self._n += 1; yid = self._n
        rank = int((data or {}).get("rank") or len(x["images"]) + 1)
        if self.rank_yok:
            rank = 1
        for i in x["images"]:
            if i["rank"] >= rank:
                i["rank"] += 1
        x["images"].append(dict(listing_image_id=yid, rank=min(rank, len(x["images"]) + 1), alt_text=(data or {}).get("alt_text"),
                                url_fullxfull=f"u/{yid}"))
        self.yazimlar.append(("upload", lid, yid, files["image"][0]))
        return {"listing_image_id": yid}

    def post_json(self, path, body):
        self._say(); lid = self._lid(path); x = self.L[lid]
        self.yazimlar.append(("bag", lid, len(body["variation_images"])))
        yeni = [dict(property_id=b["property_id"], value_id=b["value_id"], image_id=b["image_id"]) for b in body["variation_images"]]
        if self.bag_tutmaz and any(b["value_id"] == VID["Champagne Ivory"] for b in yeni):
            return {}
        x["var"] = yeni
        return {}

    def delete(self, path, ok404=False):
        self._say(); lid = self._lid(path); x = self.L[lid]
        iid = int(path.rstrip("/").split("/")[-1])
        self.yazimlar.append(("sil", lid, iid))
        x["images"] = [i for i in x["images"] if i["listing_image_id"] != iid]
        for n, i in enumerate(sorted(x["images"], key=lambda i: i["rank"]), 1):
            i["rank"] = n
        x["var"] = [b for b in x["var"] if b["image_id"] != iid]
        return {}

    def _yasak(self, *a, **k):
        raise AssertionError("beklenmeyen yazim yontemi")
    post = put = patch = put_json = _yasak


def v11_alt():
    return {int(r["sira"]): r for r in csv.DictReader(open(KOK / "data/pod/galeri_v11_alt.csv", encoding="utf-8"))}


def ilan_kur(lid, a, b, v11=False):
    """v11b canli durumu (Serdar 29 Eki): 1 MB kapak, 2-6 bilgi kartlari, 7-10 MB / DB / PW / WP; 4 bag. v11=True: rank 1 CI kapak + 5 bag."""
    sab = v11_alt(); base = int(lid[-1]) * 1000
    imgs = [dict(listing_image_id=base + 1, rank=1, alt_text=f"{a} and {b} personalized zodiac couple wall art poster in Midnight Blue, "
                 "shown in a black frame with mat, frame not included", url_fullxfull="u")]
    for r in range(2, 11):
        imgs.append(dict(listing_image_id=base + r, rank=r, alt_text=C.alt_metin(sab[r], a, b), url_fullxfull="u"))
    var = [dict(property_id=200, value_id=VID[n], image_id=base + r) for n, r in C.BAG_SIRA.items()]
    if v11:
        imgs[0]["alt_text"] = C.alt_metin(sab[1], a, b)
        var.append(dict(property_id=200, value_id=VID["Champagne Ivory"], image_id=base + 1))
    return dict(state="active", images=imgs, var=var, renkler=list(VID))


def dunya(**ayar):
    return Sahte({lid: ilan_kur(lid, a, b) for lid, _, a, b in ILAN}, **ayar)


# ------------------------------------------------------------------ sentetik dosyalar
def font(px):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def kapak(p, a, b, boyut=(3000, 2250), frame=False, bicim="JPEG"):
    im = Image.new("RGB", boyut, (238, 232, 222)); d = ImageDraw.Draw(im)
    d.text((700, 165), "Personalized Zodiac Couple Gift", fill=(10, 22, 56), font=font(104))
    d.text((1100, 330), f"{a.upper()} & {b.upper()}", fill=(138, 98, 30), font=font(96))
    d.rectangle((888, 588, 2114, 2126), outline=(0, 0, 0), width=24)
    if frame:
        d.text((2160, 2000), "Frame not included", fill=(60, 60, 60), font=font(30))
    im.save(p, bicim, quality=95)


def girdiler(t, bozuk=None, frame=()):
    """-> (dosya_dir, ciftler.csv, manifest.csv)"""
    dd = t / "dosya"; dd.mkdir(parents=True, exist_ok=True)
    cf = t / "ciftler.csv"
    with open(cf, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"]); w.writerows(ILAN)
    man = []
    for lid, cift, a, b in ILAN:
        p = dd / f"{cift}_W01_KAPAK.jpg"
        kw = (bozuk or {}).get(cift, {})
        if kw.get("yok"):
            continue
        kapak(p, a, b, frame=cift in frame, **{k: v for k, v in kw.items() if k in ("boyut", "bicim")})
        man.append([p.name, cift, "W01_KAPAK", "D", "3000x2250", "0" * 64 if kw.get("sha") else D.sha256(p), "MEVCUT"])
    mf = t / "MANIFEST.csv"
    with open(mf, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ad", "cift", "kart_no", "design_id", "boyut", "sha256", "durum"]); w.writerows(man)
    return dd, cf, mf


def dosya_kapi(t, **kw):
    dd, cf, mf = girdiler(t, **kw)
    rc = D.main(["--dir", str(dd), "--ciftler", str(cf), "--manifest", str(mf), "--out", str(t / "kapi"), "--is", "3"])
    return rc, {r["cift"]: r for r in csv.DictReader(open(t / "kapi" / "CI_KAPI.csv"))}, dd, cf


# ------------------------------------------------------------------ yukleyici kosusu
def alt_ci(t, durum):
    p = t / f"ci_alt_{durum}.csv"
    rows = list(csv.DictReader(open(KOK / "data/pod/galeri_ci11_alt.csv", encoding="utf-8")))
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(dict(r, durum=durum) for r in rows)
    return p


def kos(api, t, ad, kuru=True, plan=None, damga="", sadece="", haric="", canli=None, durum="ONAYLI", ekstra=()):
    o = t / ad
    args = ["--ciftler", str(t / "ciftler.csv"), "--dosya-kapi", str(t / "kapi" / "CI_KAPI.csv"), "--alt-ci", str(alt_ci(t, durum)),
            "--out", str(o), "--kosu", "777", "--sadece", sadece, "--haric", haric, *ekstra]
    args += ["--canli-dir", str(canli)] if canli else []
    args += ["--kuru"] if kuru else ["--confirm", C.ONAY, "--plan", str(plan), "--plan-damga", damga, "--dosya-dir", str(t / "dosya")]
    try:
        a = C.arg(args)
        rc = C.sonlandir(api, SHOP, a)
    except SystemExit as e:
        return 9, dict(hata=str(e.code))
    R = json.loads((o / "RAPOR.json").read_text())
    R["d"] = {s["ilan"]: s for s in R["ilanlar"]}
    return rc, R


def kuru_plan(api, t, ad="kuru", **kw):
    rc, R = kos(api, t, ad, **kw)
    if rc == 9:
        return rc, R, None, ""
    return rc, R, t / ad / C.PLAN_AD, R.get("plan_damga", "")


def main():
    t0 = Path(tempfile.mkdtemp(prefix="ci11_"))
    try:
        T = C.istek_tahmini()
        print(f"istek tahmini: {T}")
        # ---- dosya kapisi
        t = t0 / "dk"; rc, k, dd, cf = dosya_kapi(t, frame=("LIBRA_VIRGO",))
        kontrol("dosya kapisi 3 PASS (rc 0)", rc == 0 and all(r["durum"] == "PASS" for r in k.values()))
        ocr_var = shutil.which("tesseract") is not None
        if ocr_var:
            kontrol("OCR: Frame not included VAR (rapor, PASS kalir)", k["LIBRA_VIRGO"]["ocr_frame"] == "VAR" and k["LIBRA_VIRGO"]["durum"] == "PASS")
            kontrol("OCR: etiketsiz dosyada YOK", k["ARIES_LEO"]["ocr_frame"] == "YOK")
            kontrol("OCR: cift satiri VAR", k["ARIES_LEO"]["ocr_cift"] == "VAR" and k["CANCER_CANCER"]["ocr_cift"] == "VAR")
        else:
            kontrol("OCR: tesseract yok -> ATLANDI", k["ARIES_LEO"]["ocr_frame"] == "ATLANDI")
        kapak(dd / "PISCES_PISCES_W01_KAPAK.jpg", "Pisces", "Pisces")
        D.main(["--dir", str(dd), "--ciftler", str(cf), "--out", str(t / "k2"), "--ocr-yok"])
        kontrol("FAZLA dosya raporu", "PISCES_PISCES_W01_KAPAK.jpg" in (t / "k2" / "CI_KAPI.md").read_text())
        t = t0 / "dkb"
        rc, k, _, _ = dosya_kapi(t, bozuk=dict(ARIES_LEO=dict(boyut=(3000, 2000)), CANCER_CANCER=dict(bicim="PNG"), LIBRA_VIRGO=dict(sha=1)))
        kontrol("dosya kapisi: boyut FAIL", rc == 1 and "boyut 3000x2000" in k["ARIES_LEO"]["neden"])
        kontrol("dosya kapisi: PNG (.jpg adli) JPEG degil FAIL", "JPEG degil" in k["CANCER_CANCER"]["neden"])
        kontrol("dosya kapisi: MANIFEST sha256 FAIL", "MANIFEST" in k["LIBRA_VIRGO"]["neden"])
        t = t0 / "dky"; rc, k, _, _ = dosya_kapi(t, bozuk=dict(ARIES_LEO=dict(yok=1)))
        kontrol("dosya kapisi: dosya yok FAIL", k["ARIES_LEO"]["neden"] == "dosya yok" and k["CANCER_CANCER"]["durum"] == "PASS")

        # ---- yukleyici: ortak girdi (gecerli dosyalar)
        t = t0 / "y"; dosya_kapi(t)
        api = dunya(); ilk = copy.deepcopy(api.L)
        rc, R, plan, damga = kuru_plan(api, t, durum="TASLAK")
        kontrol("kuru: 3 PLAN, yazim yok, ilan basina 4 istek",
                rc == 0 and R["sayilar"] == {"PLAN": 3} and not api.yazimlar and all(s["istek"] == T["kuru"] for s in R["ilanlar"]))
        kontrol("kuru: TASLAK alt metin notu", "TASLAK" in R["ilanlar"][0]["neden"][0])
        kontrol("kuru: plan rank 11 + CI value_id", json.loads(plan.read_text())["girdiler"]["9000000001"]["ci_value_id"] == 104)
        rc, R = kos(api, t, "taslak_yaz", kuru=False, plan=plan, damga=damga, sadece="9000000001", durum="TASLAK")
        kontrol("yazim: alt metin TASLAK -> DUR, Etsy istegi yok", rc == 9 and "TASLAK" in R["hata"] and api.calls == 12 and not api.yazimlar)

        # pilot sadece (ONAYLI alt metinle yeni kuru plan)
        api = dunya(); rc, R, plan, damga = kuru_plan(api, t, "kuru2")
        c0 = api.calls
        rc, R = kos(api, t, "pilot", kuru=False, plan=plan, damga=damga, sadece="9000000001")
        x = api.L["9000000001"]; g = sorted(x["images"], key=lambda i: i["rank"])
        yid = R["d"]["9000000001"]["yeni_id"]
        kontrol("pilot sadece: PASS, yalniz 1 ilan", rc == 0 and R["sayilar"] == {"PASS": 1} and list(R["d"]) == ["9000000001"])
        kontrol("pilot: rank 1-10 ayni (kimlik + alt metin)", [(i["listing_image_id"], i["alt_text"]) for i in g[:10]]
                == [(i["listing_image_id"], i["alt_text"]) for i in ilk["9000000001"]["images"]])
        kontrol("pilot: rank 11 = yeni CI gorseli", len(g) == 11 and g[10]["listing_image_id"] == yid and "Champagne Ivory" in g[10]["alt_text"])
        bag = {b["value_id"]: b["image_id"] for b in x["var"]}
        kontrol("pilot: 5 bag, 4 eski aynen + CI -> yeni", len(x["var"]) == 5 and bag[104] == yid
                and all(bag[VID[n]] == 1000 + r for n, r in C.BAG_SIRA.items()))
        kontrol(f"pilot: istek = en az tahmini ({T['yaz_en_az']})", api.calls - c0 == T["yaz_en_az"] == R["d"]["9000000001"]["istek"])
        kontrol("pilot: diger ilanlar dokunulmadi", api.L["9000000002"] == ilk["9000000002"] and api.L["9000000003"] == ilk["9000000003"])
        kontrol("pilot: YEDEK + SONRA dosyalari", (t / "pilot/ilanlar/YEDEK_9000000001.json").exists() and (t / "pilot/ilanlar/SONRA_9000000001.json").exists())

        # zaten yapilmis: kuru ZATEN, yazim ZATEN (yazim yok)
        n0 = len(api.yazimlar)
        rc, R = kos(api, t, "zaten_kuru")
        kontrol("zaten: kuru ZATEN (yazim yok)", R["d"]["9000000001"]["durum"] == "ZATEN" and len(api.yazimlar) == n0)
        rc, R = kos(api, t, "zaten_yaz", kuru=False, plan=plan, damga=damga, sadece="9000000001")
        kontrol("zaten: yazim ZATEN, yazim yok", rc == 0 and R["d"]["9000000001"]["durum"] == "ZATEN" and len(api.yazimlar) == n0)

        # haric: kalan iki ilandan biri haric
        rc, R = kos(api, t, "haric", kuru=False, plan=plan, damga=damga, haric="9000000001,9000000002")
        kontrol("haric: yalniz 9000000003 PASS, 9000000002 dokunulmadi", rc == 0 and list(R["d"]) == ["9000000003"]
                and R["d"]["9000000003"]["durum"] == "PASS" and api.L["9000000002"] == ilk["9000000002"])
        rc, R = kos(dunya(), t, "haric_kuru", haric="9000000002")
        kontrol("haric (kuru): ilan kapsam disi", "9000000002" not in R["d"] and len(R["d"]) == 2)
        rc, R = kos(dunya(), t, "bilinmeyen", sadece="123")
        kontrol("sadece: 78 disi ilan DUR", rc == 9 and "78 disi" in R["hata"])

        # canli != plan
        api = dunya(); rc, R, plan, damga = kuru_plan(api, t, "kuru3")
        api.L["9000000002"]["images"][2]["alt_text"] = "elle degisti"
        api.L["9000000003"]["images"][9]["listing_image_id"] = 3999; api.L["9000000003"]["var"][3]["image_id"] = 3999
        rc, R = kos(api, t, "farkli", kuru=False, plan=plan, damga=damga, haric="9000000001")
        kontrol("canli != plan (alt metin) BLOK", R["d"]["9000000002"]["durum"] == "BLOK")
        kontrol("canli != plan (kimlik) BLOK, yazim yok", "canli != plan" in R["d"]["9000000003"]["neden"][0] and not api.yazimlar)
        kontrol("plan_damga bozuk DUR", kos(api, t, "damga", kuru=False, plan=plan, damga="777_000000000000")[0] == 9)

        # CI degeri yok
        api = dunya(); api.L["9000000002"]["renkler"] = [n for n in VID if n != "Champagne Ivory"]
        rc, R = kos(api, t, "ci_yok")
        kontrol("CI degeri yok BLOK", R["d"]["9000000002"]["durum"] == "BLOK" and "Champagne Ivory degeri yok" in R["d"]["9000000002"]["neden"][0]
                and R["d"]["9000000001"]["durum"] == "PLAN")

        # geri okuma hatasi: CI bag POST'u tutmaz -> geri alma; sonraki ilan KALAN
        api = dunya(); rc, R, plan, damga = kuru_plan(api, t, "kuru4"); api.bag_tutmaz = True
        c0 = api.calls
        rc, R = kos(api, t, "geri", kuru=False, plan=plan, damga=damga)
        x = api.L["9000000001"]
        kontrol("geri okuma hatasi: FAIL + GERI ALINDI, cikis 1", rc == 1 and R["d"]["9000000001"]["durum"] == "FAIL"
                and "GERI ALINDI" in R["d"]["9000000001"]["neden"][-1])
        kontrol("geri alma: galeri 10 eski, 4 bag eski", x["images"] == ilk["9000000001"]["images"]
                and sorted(map(str, x["var"])) == sorted(map(str, ilk["9000000001"]["var"])))
        kontrol("geri alma: yeni gorsel silindi", any(y[0] == "sil" for y in api.yazimlar))
        kontrol("geri alma: sonraki ilanlar KALAN (yazim yok)", R["d"]["9000000002"]["durum"] == "KALAN" and R["d"]["9000000003"]["durum"] == "KALAN"
                and api.L["9000000002"] == ilk["9000000002"])
        kontrol(f"geri alma istek <= en kotu tahmini ({T['yaz_en_kotu']})", R["d"]["9000000001"]["istek"] <= T["yaz_en_kotu"])

        # yukleme rank'i yok sayilir (1'e oturur) -> geri alma
        api = dunya(); rc, R, plan, damga = kuru_plan(api, t, "kuru5"); api.rank_yok = True
        rc, R = kos(api, t, "rank", kuru=False, plan=plan, damga=damga, sadece="9000000002")
        kontrol("rank 11 tutmaz: FAIL + GERI ALINDI, galeri eski", R["d"]["9000000002"]["durum"] == "FAIL"
                and api.L["9000000002"]["images"] == ilk["9000000002"]["images"] and len(api.L["9000000002"]["var"]) == 4)

        # YARIM: rank 11 CI metinli ama bag yok
        api = dunya(); x = api.L["9000000003"]
        x["images"].append(dict(listing_image_id=3011, rank=11, alt_text=C.alt_metin(C.sablon_oku(KOK / "data/pod/galeri_ci11_alt.csv", [11])[11],
                                                                                       "Libra", "Virgo"), url_fullxfull="u"))
        rc, R = kos(api, t, "yarim")
        kontrol("YARIM BLOK", R["d"]["9000000003"]["durum"] == "BLOK" and "YARIM" in R["d"]["9000000003"]["neden"][0])

        # v11 durumu (rank 1 CI kapak + 5 bag) BLOK
        api = dunya(); api.L["9000000001"] = ilan_kur("9000000001", "Aries", "Leo", v11=True)
        rc, R = kos(api, t, "v11")
        kontrol("v11 durumu (CI kapak + 5 bag) BLOK", R["d"]["9000000001"]["durum"] == "BLOK"
                and any("CI bagi zaten var" in n for n in R["d"]["9000000001"]["neden"]))

        # canli okuma (canli_damga) farki
        api = dunya(); cd = t / "canli"
        for lid, cift, _, _ in ILAN:
            x = api.L[lid]; (cd / f"{lid}_{cift}").mkdir(parents=True, exist_ok=True)
            ref = copy.deepcopy(dict(gorseller=x["images"], baglar=x["var"]))
            if lid == "9000000001":   # canli tutarli (v11b), yalniz canli_damga okumasi farkli
                ref["gorseller"][1]["listing_image_id"] = 9999
            (cd / f"{lid}_{cift}" / "GALERI.json").write_text(json.dumps(ref))
        rc, R = kos(api, t, "canli", canli=cd)
        kontrol("canli okuma farki BLOK, digerleri PLAN", R["d"]["9000000001"]["durum"] == "BLOK" and R["d"]["9000000002"]["durum"] == "PLAN"
                and R["d"]["9000000001"]["neden"] == ["canli galeri kimlikleri canli okumadan (canli_damga GALERI.json) farkli"])

        # kota: kalan dusuk -> yazim baslamaz
        api = dunya(); rc, R, plan, damga = kuru_plan(api, t, "kuru6"); api.remaining = T["yaz_en_kotu"] + 5
        rc, R = kos(api, t, "kota", kuru=False, plan=plan, damga=damga, sadece="9000000001")
        kontrol("kota: kalan < en kotu + 10 -> KALAN, yazim yok", R["d"]["9000000001"]["durum"] == "KALAN" and not api.yazimlar)
    finally:
        shutil.rmtree(t0, ignore_errors=True)
    bad = [a for a, ok in SONUC if not ok]
    print(f"\n{len(SONUC) - len(bad)}/{len(SONUC)} PASS" + (f" | FAIL: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
