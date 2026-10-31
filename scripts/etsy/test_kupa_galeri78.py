#!/usr/bin/env python3
"""kupa_galeri78.py yerel testi. Ag / Drive / Etsy / token YOK: sahte Etsy (bellekte galeri, Style baglari, video, envanter,
kisisellestirme, aciklama, RU; yuklenen dosyalarin BAYTLARI saklanir; kalan kota ilk yanittan once None olabilir; CDN 404 / HTML),
sahte Drive (klasor; rclone --immutable ve lsjson --hash karsiligi) ve sahte rclone (RCLONE ortam degiskeni: DEVAM_<ilan>.json ve
geri alma dosyalari "fake:" uzaginden). Sentetik ilanlar (9100000001..) ve sentetik JPEG / MP4 baytlari.
Inceleme 30 Eki (8d8c66a8) bulgulari icin, duzeltmeden ONCE FAIL veren testler:
  1 devam: ayni plan_damga ile ikinci yedek kosusu ayni bayt (zaman damgasi yok) + Drive'daki ilan VAR (CDN 404 iken bile), --immutable
  2 kosu ilan ortasinda olur (runner kaybi): toplu DEVAM yok, Drive'daki DEVAM_<ilan>.json ile devam (cift yukleme yok) ve geri_al
  3 kalan kota None ile baslayan kosu: ilk ilandan once tek GET, kapi uygulanir (sinir: en kotu + 10 baslar, + 9 KALAN)
  4 is akislari: hazir ayri ve kilitsiz / tokensiz; yukleyici yalniz parti dosyalarini indirir, geri_al modu, azami 15
  5 geri alma tahmini gercek eski gorsel sayisiyla (16 eski gorselli ilan)
  6 yedek bayt imzasi (16 bayt HTML FAIL) + Drive hash farki BLOK; silme aninda yedegin BAYTLARI Drive'da
  7 metin varsayilan kapali (ayni burcta PATCH / POST yok); --metin-yaz ile yazim
  8 YASAK_EN (Printful) + RU_YASAK; kisisellestirme birden fazla soru BLOK; POST question_id korur
  9 video geri almasi otomatik yolda (son kontrol FAIL), bayt karsilastirmasiyla
Kullanim: python3 scripts/etsy/test_kupa_galeri78.py"""
import copy
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
import kupa_galeri78 as K  # noqa: E402

G.OKUMA_BEKLE = 0; Y.BEKLE_429 = 0; K.VIDEO_BEKLE = 0
SONUC = []
SHOP = "1"
STIL_VID = {ad: 1001 + i for i, (ad, _, _) in enumerate(K.STILLER)}
LID = {c: str(9100000001 + i) for i, c in enumerate(K.CIFTLER)}
TEST = ["ARIES_LEO", "LEO_LEO", "CANCER_LIBRA"]
ESKI_N = {"ARIES_LEO": 16}          # 16 eski gorselli ilan (geri alma tahmini gercek sayiyla)
TIRE = re.compile("[–—]")


def kontrol(ad, ok, ek=""):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad + (f" ({ek})" if ek and not ok else ""), flush=True)


def jpeg(tohum):
    return b"\xff\xd8\xff\xe0" + hashlib.sha256(tohum.encode()).digest() * 8


def mp4(tohum):
    return b"\x00\x00\x00\x18ftypmp42" + hashlib.sha256(tohum.encode()).digest() * 8


class Olum(BaseException):
    """runner kaybi: surec olur (except Exception yakalamaz, kosu sonu yazimlari olmaz)"""


# ------------------------------------------------------------------ sahte Drive + rclone
SAHTE_RCLONE = """#!{py}
import os, shutil, sys
from pathlib import Path
kok = Path(os.environ["SAHTE_DRIVE"])
a = [x for x in sys.argv[1:] if x != "-q"]
if os.environ.get("SAHTE_DRIVE_KAPALI") == "1" or a[0] != "copyto":
    sys.exit(1)
yol = lambda s: kok / s[5:] if s.startswith("fake:") else Path(s)
src, dst = yol(a[1]), yol(a[2])
if not src.is_file():
    sys.exit(3)
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(src, dst)
"""


def drive_immutable(src, dst):
    """rclone copy --immutable: hedefte ayni yolda FARKLI bayt varsa hata (dosya degistirilmez). -> catisan yollar"""
    src, dst = Path(src), Path(dst); cat = []
    for p in sorted(src.rglob("*")):
        if p.is_file():
            q = dst / p.relative_to(src)
            if q.exists():
                if q.read_bytes() != p.read_bytes():
                    cat.append(str(p.relative_to(src)))
                continue
            q.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, q)
    return cat


def lsjson_hash(d, out):
    d = Path(d)
    L = [dict(Path=str(p.relative_to(d)), Size=p.stat().st_size, IsDir=False,
              Hashes=dict(md5=hashlib.md5(p.read_bytes()).hexdigest(), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
         for p in sorted(d.rglob("*")) if p.is_file()] if d.exists() else []
    Path(out).write_text(json.dumps(L))
    return L


# ------------------------------------------------------------------ sahte Etsy
class Sahte:
    """Etsy v3 alt kumesi. uploadListingImage (rank ile araya girer; listing_image_id ile sira + alt metin; sira yazimi Style baglarini
    siler, 19 Eyl olcumu), deleteListingImage (bagi da duser), updateVariationImages (tum seti degistirir), video yukle / sil,
    updateListing (PATCH), updateListingPersonalization. Yuklenen gorsel / video baytlari self.bayt'ta. remaining None ile baslarsa ilk
    yanitta gercek - 1 olur (x-remaining-today). Hata: yukleme_hata (n. yuklemede 500, gorsel olusmaz), olum_yukleme (n. yuklemede gorsel
    olusur, yanit gelmeden surec olur), olum_video, bag_tutmaz, kota_kes (n. yazimda 'DUR: kota sert tabani', istek gitmez),
    etiket_boz_video (video silinince etiket degisir -> son kontrol FAIL)."""
    def __init__(self, kalan=100000):
        self.L, self.calls, self.remaining, self.gercek, self.yazimlar, self._n, self.cdn = {}, 0, kalan, kalan, [], 5_000_000, {}
        self.yukleme_hata = None; self.bag_tutmaz = 0; self.kota_kes = None; self.salt = False; self.olum_yukleme = None
        self.olum_video = False; self.etiket_boz_video = False
        self.yukleme_say = 0; self.yazim_say = 0; self.silme_oncesi = None; self.ihlal = []; self.bayt = {}
        self.cdn_404, self.cdn_html, self.cdn_istek, self.pers_govde = set(), set(), [], []

    # --- kurulum
    def ilan(self, cift, desc, per, n_eski=14, durum="active"):
        lid = LID[cift]; a, b = cift.split("_")
        imgs, var = [], []
        for r in range(1, n_eski + 1):
            self._n += 1; u = f"https://i.etsystatic.com/eski/{lid}/{self._n}.jpg"; self.cdn[u] = jpeg(u)
            imgs.append(dict(listing_image_id=self._n, rank=r, alt_text=f"eski {r}", url_fullxfull=u, full_width=2000))
        eski_sira = {"Orange Blossom": 1, "Purple Fig": 8, "Olive Breeze": 9, "Pomegranate Bloom": 10, "Almond Blossom": 11,
                     "Lemon Grove": 12, "Blue Grape": 13, "Golden Loquat": 14}
        for ad, r in eski_sira.items():
            var.append(dict(property_id=513, value_id=STIL_VID[ad], image_id=imgs[r - 1]["listing_image_id"]))
        self._n += 1; vu = f"https://v.etsystatic.com/eski/{lid}.mp4"; self.cdn[vu] = mp4(vu)
        urun = [dict(sku=f"KUPA-{cift}-{i:02d}-{bk}", offerings=[dict(price=dict(amount=1290, divisor=100), quantity=999)],
                     property_values=[dict(property_id=513, values=[ad], value_ids=[STIL_VID[ad]]),
                                      dict(property_id=514, values=[bo], value_ids=[2000 + i])])
                for i, (ad, _, _) in enumerate(K.STILLER) for bo, bk in (("11 oz", "11"), ("15 oz", "15"))]
        self.L[lid] = dict(state=durum, shop_section_id=K.BOLUM, title=f"{a} and {b} mug", tags=["mug", "zodiac"], description=desc,
                           images=imgs, var=var, videos=[dict(video_id=self._n, video_state="active", video_url=vu)],
                           inv=dict(products=urun), per=copy.deepcopy(per), ru={"description": "RU metin"} if a == b else None)
        return lid

    def indir(self, u):
        """CDN (Etsy API degil): 404 / HTML hata sayfasi benzetimi"""
        self.cdn_istek.append(u)
        if u in self.cdn_404:
            raise OSError(f"HTTP Error 404: Not Found {u}")
        if u in self.cdn_html:
            return b"<html>404</html>"
        return self.cdn[u]

    def gorsel_bayt(self, im):
        return self.bayt.get(im["listing_image_id"]) or self.cdn.get(im["url_fullxfull"])

    def video_bayt(self, v):
        return self.bayt.get(("v", v["video_id"])) or self.cdn.get(v["video_url"])

    # --- istemci arayuzu (etsy_common.Etsy ile ayni kural: remaining None iken kapi yok)
    def kota_kapisi(self, ne="is"):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _say(self, yazim=False):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < 10")
        if yazim:
            if self.salt:
                raise SystemExit("DUR: salt okuma kosusunda Etsy yazma cagrisi")
            self.yazim_say += 1
            if self.kota_kes and self.yazim_say == self.kota_kes:
                raise SystemExit("DUR: kota sert tabani: kalan 9 < 10")
        self.calls += 1
        if self.remaining is None:
            self.remaining = self.gercek
        self.remaining -= 1

    def _lid(self, path):
        return re.search(r"/listings/(\d+)", path).group(1)

    def _sirala(self, x):
        for i, im in enumerate(x["images"], 1):
            im["rank"] = i

    def get(self, path, params=None, ok404=False):
        self._say()
        if "/listings/" not in path:
            return {"shop_id": int(SHOP)}
        x = self.L[self._lid(path)]
        if path.endswith("/images"):
            return {"results": copy.deepcopy(x["images"])}
        if path.endswith("/videos"):
            return {"results": copy.deepcopy(x["videos"])}
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(x["var"])}
        if path.endswith("/inventory"):
            return copy.deepcopy(x["inv"])
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(x["per"])}
        if path.endswith("/translations/ru"):
            return copy.deepcopy(x["ru"]) if x["ru"] else None
        return {k: copy.deepcopy(x[k]) for k in ("state", "shop_section_id", "title", "tags", "description")}

    def post_file(self, path, files, data=None, tekrar=3):
        self._say(True)
        lid = self._lid(path); x = self.L[lid]
        self.yazimlar.append(("POST_FILE", lid, path))
        if path.endswith("/videos"):
            self._n += 1; u = f"https://v.etsystatic.com/yeni/{self._n}.mp4"
            self.bayt[("v", self._n)] = files["video"][1].read()
            x["videos"].append(dict(video_id=self._n, video_state="active", video_url=u))
            if self.olum_video:
                raise Olum("video yanitindan once surec oldu")
            return {"video_id": self._n}
        if "listing_image_id" in files:      # sira + alt metin
            iid = int(files["listing_image_id"][1]); rk = int(files["rank"][1])
            im = next(i for i in x["images"] if i["listing_image_id"] == iid)
            x["images"].remove(im); x["images"].insert(rk - 1, im); im["alt_text"] = files["alt_text"][1]
            self._sirala(x); x["var"] = []          # 19 Eyl olcumu: sira yazimi bagi siler
            return {"listing_image_id": iid}
        self.yukleme_say += 1
        if self.yukleme_hata and self.yukleme_say == self.yukleme_hata:
            raise SystemExit(f"HATA: POST(file) {path} -> 500: sahte")
        self._n += 1
        rk = int((data or {}).get("rank") or len(x["images"]) + 1)
        u = f"https://i.etsystatic.com/yeni/{self._n}.jpg"
        self.bayt[self._n] = files["image"][1].read()
        im = dict(listing_image_id=self._n, rank=rk, alt_text=(data or {}).get("alt_text"), url_fullxfull=u, full_width=2000)
        x["images"].insert(min(rk, len(x["images"]) + 1) - 1, im); self._sirala(x)
        assert len(x["images"]) <= 20, "20 gorsel siniri asildi"
        if self.olum_yukleme and self.yukleme_say == self.olum_yukleme:
            raise Olum("gorsel olustu, yanittan once surec oldu")
        return {"listing_image_id": self._n}

    def post_json(self, path, body):
        self._say(True)
        lid = self._lid(path); x = self.L[lid]
        self.yazimlar.append(("POST_JSON", lid, path))
        if path.endswith("/variation-images"):
            if self.bag_tutmaz:
                self.bag_tutmaz -= 1; return {}
            ids = {i["listing_image_id"] for i in x["images"]}
            assert all(v["image_id"] in ids for v in body["variation_images"]), "bag galeride olmayan gorsele"
            x["var"] = [dict(property_id=v["property_id"], value_id=v["value_id"], image_id=v["image_id"]) for v in body["variation_images"]]
            return {}
        if path.endswith("/personalization"):
            self.pers_govde.append(copy.deepcopy(body))
            x["per"] = copy.deepcopy(body["personalization_questions"]); return {}
        raise AssertionError(path)

    def patch(self, path, data):
        self._say(True)
        lid = self._lid(path); x = self.L[lid]
        self.yazimlar.append(("PATCH", lid, tuple(sorted(data))))
        x.update(data); return {}

    def delete(self, path, ok404=False):
        self._say(True)
        lid = self._lid(path); x = self.L[lid]
        self.yazimlar.append(("DELETE", lid, path))
        if self.silme_oncesi:
            self.silme_oncesi(lid, path)
        m = re.search(r"/images/(\d+)$", path)
        if m:
            iid = int(m.group(1))
            if not any(i["listing_image_id"] == iid for i in x["images"]):
                return None
            assert len(x["images"]) > 1, "son gorsel silinmez"
            x["images"] = [i for i in x["images"] if i["listing_image_id"] != iid]; self._sirala(x)
            x["var"] = [v for v in x["var"] if v["image_id"] != iid]
            return {}
        vid = int(re.search(r"/videos/(\d+)$", path).group(1))
        x["videos"] = [v for v in x["videos"] if v["video_id"] != vid]
        if self.etiket_boz_video:
            x["tags"] = x["tags"] + ["elle"]
        return {}


# ------------------------------------------------------------------ test duzeni
DESC_FARKLI = "A personalized mug for {a} and {b}.\n\n[ HOW TO PERSONALIZE ]\n1. Name Under {a} (up to 10 letters)\n2. Name Under {b} (up to 10 letters)\n"
PER = lambda a, b: [dict(question_id=77, question_text="Personalization", question_type="text_input", required=True,  # noqa: E731
                         max_allowed_characters=256, instructions=f"1. Name Under {a} (max 10)\n2. Name Under {b} (max 10)\n3. Message")]


def sahne(kok, alt_onay=True):
    """dosyalar + liste + kart MANIFEST + kapak KAYIT + alt metin"""
    kok = Path(kok)
    with open(kok / "liste.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cift", "listing_id"]); w.writerows((c, LID[c]) for c in K.CIFTLER)
    d = kok / "dosya"
    man = []
    for c in TEST:
        for s, rel in K.kaynak_yollari(c).items():
            p = d / rel; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(mp4(rel) if s == "video" else jpeg(rel))
            if s in K.KART:
                man.append(dict(cift=c, kart=K.KART[s], galeri_no=s, dosya=p.name, sha256=Y.sha256(p), durum="PASS", neden=""))
    with open(kok / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "kart", "galeri_no", "dosya", "sha256", "durum", "neden"]); w.writeheader(); w.writerows(man)
    (kok / "KAYIT.tsv").write_text("# sembol x\ncift baslik\n" + "".join(f"{c} \"x\" boy 1\n" for c in TEST))
    rows = list(csv.DictReader(open(K.ALT_CSV, encoding="utf-8")))
    with open(kok / "alt.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        w.writerows(dict(r, durum="ONAYLI" if alt_onay else r["durum"]) for r in rows)
    return d


def sahte_kur():
    api = Sahte()
    for c in TEST:
        a, b = (x.capitalize() for x in c.split("_"))
        api.ilan(c, DESC_FARKLI.format(a=a, b=b), PER(a, b), n_eski=ESKI_N.get(c, 14))
    return api


def kos(api, kok, mod, *ek, ad=None):
    ad = ad or f"out_{mod}"
    if mod in ("yaz", "geri_al"):
        devam_indir(kok)
    a = K.arg([mod, "--liste", str(kok / "liste.csv"), "--out", str(kok / ad), "--alt", str(kok / "alt.csv"),
               "--kaynak", str(kok / "k" / "KAYNAK.csv"), "--kosu", "777", *ek])
    kod = K.sonlandir(api, SHOP, a)
    R = json.loads((kok / ad / "RAPOR.json").read_text())
    return kod, {s["ilan"]: s for s in R["ilanlar"]}, R


def pd_of(kok):
    return (kok / "PD.txt").read_text()


def yaz_arg(kok, pd, *ek):
    return ("--confirm", K.ONAY, "--plan", str(kok / "out_kuru" / K.PLAN_AD), "--plan-damga", pd, "--dosya-dir", str(kok / "dosya"),
            "--yedek-dir", str(kok / "yedek"), "--yedek-liste", str(kok / "lsjson.json"), "--devam", str(kok / "DEVAM.json"),
            "--ilerleme", str(kok / "ILERLEME.json"), "--yedek-uzak", f"fake:YEDEK/{pd}", "--devam-hedef-kok", f"fake:DEVAM_ILAN/{pd}",
            "--devam-ilan-dir", str(kok / "devam_ilan"), *ek)


def geri_arg(kok, pd, sadece, *ek):
    return ("--confirm", K.ONAY_GERI, "--sadece", sadece, "--yedek-dir", str(kok / "yedek"), "--plan-damga", pd,
            "--devam", str(kok / "DEVAM.json"), "--yedek-uzak", f"fake:YEDEK/{pd}", "--devam-hedef-kok", f"fake:DEVAM_ILAN/{pd}",
            "--devam-ilan-dir", str(kok / "devam_ilan"), *ek)


def drive(kok):
    return Path(os.environ["SAHTE_DRIVE"])


def devam_indir(kok):
    """is akisi: rclone copy $O/DEVAM_ILAN/$PD _work/devam_ilan (her kosu basinda)"""
    if not (kok / "PD.txt").exists():
        return
    d = kok / "devam_ilan"; shutil.rmtree(d, ignore_errors=True); d.mkdir()
    s = drive(kok) / "DEVAM_ILAN" / pd_of(kok)
    if s.exists():
        for p in s.glob("DEVAM_*.json"):
            shutil.copyfile(p, d / p.name)


def yedek_kos(kok, api, pd, ad):
    """hazir is akisi (kilitsiz): Drive listesi + mevcut YEDEK.json'lar -> yedek -> rclone copy --immutable -> lsjson --hash dogrulama.
    -> (kod, immutable catismasi, dogrulama eksigi, ozet)"""
    Y_dr = drive(kok) / "YEDEK" / pd
    var = kok / f"{ad}_var"; shutil.rmtree(var, ignore_errors=True); var.mkdir()
    if Y_dr.exists():
        for p in Y_dr.glob("*/YEDEK.json"):
            (var / p.parent.name).mkdir(); shutil.copyfile(p, var / p.parent.name / "YEDEK.json")
    lsjson_hash(Y_dr, kok / f"{ad}_once.json")
    ya = K.arg(["yedek", "--liste", str(kok / "liste.csv"), "--out", str(kok / f"{ad}_out"), "--plan", str(kok / "out_kuru" / K.PLAN_AD),
                "--plan-damga", pd, "--yedek-dir", str(kok / ad), "--yedek-liste", str(kok / f"{ad}_once.json"), "--yedek-var-dir", str(var),
                "--sadece", ",".join(LID[c] for c in TEST)])
    kod = K.yedek_mod(ya, indir=api.indir)
    cat = drive_immutable(kok / ad, Y_dr)
    lsjson_hash(Y_dr, kok / f"{ad}_sonra.json")
    eksik = K.yerel_drive_eksik(kok / ad, K.drive_liste_oku(kok / f"{ad}_sonra.json"))
    oz = {r["ilan"]: r for r in csv.DictReader(open(kok / f"{ad}_out" / "YEDEK_OZET.csv"))}
    return kod, cat, eksik, oz


def yaz_hazirla(kok, pd):
    """etsy is akisi: yedek klasorunde yalniz YEDEK.json (Drive'dan), lsjson --hash"""
    shutil.rmtree(kok / "yedek", ignore_errors=True); (kok / "yedek").mkdir()
    Y_dr = drive(kok) / "YEDEK" / pd
    for p in Y_dr.glob("*/YEDEK.json"):
        (kok / "yedek" / p.parent.name).mkdir(); shutil.copyfile(p, kok / "yedek" / p.parent.name / "YEDEK.json")
    lsjson_hash(Y_dr, kok / "lsjson.json")


def hazirla(kok, sadece, metin=False):
    """kaynak + kuru + yedek; -> (api, plan_damga, S, R)"""
    sahne(kok)
    assert K.main(["kaynak", "--liste", str(kok / "liste.csv"), "--out", str(kok / "k"), "--sadece", sadece, "--dosya-dir", str(kok / "dosya"),
                   "--kart-manifest", str(kok / "MANIFEST.csv"), "--kapak-kayit", str(kok / "KAYIT.tsv")]) == 0
    api = sahte_kur()
    api.salt = True
    kod, S, R = kos(api, kok, "kuru", "--sadece", sadece, *(["--metin-yaz"] if metin else []))
    api.salt = False
    pd = R["plan_damga"]; (kok / "PD.txt").write_text(pd)
    kod, cat, eksik, oz = yedek_kos(kok, api, pd, "yedek_out")
    assert kod == 0 and not cat and not eksik, (kod, cat, eksik)
    yaz_hazirla(kok, pd)
    return api, pd, S, R


def galeri_hedefte(api, lid, cift):
    x = api.L[lid]
    a, b = (s.capitalize() for s in cift.split("_"))
    alt = K.alt_oku(K.ALT_CSV)
    bek = [K.alt_metin(alt[s], a, b) for s in range(1, 15)]
    rk = {i["listing_image_id"]: i["rank"] for i in x["images"]}
    bag = {v["value_id"]: rk.get(v["image_id"]) for v in x["var"]}
    return ([i["alt_text"] for i in x["images"]] == bek and [i["rank"] for i in x["images"]] == list(range(1, 15))
            and bag == {STIL_VID[ad]: s for ad, s, _ in K.STILLER} and len(x["videos"]) == 1
            and "yeni" in x["videos"][0]["video_url"] and all("yeni" in i["url_fullxfull"] for i in x["images"]))


def eski_halde(api, lid, eski):
    """eski hal BAYT duzeyinde: gorsel baytlari + alt metin + sira, baglar (sira), video baytlari, metin"""
    x = api.L[lid]
    rk = {i["listing_image_id"]: i["rank"] for i in x["images"]}
    eski_rk = {i["listing_image_id"]: i["rank"] for i in eski["images"]}
    return ([i["alt_text"] for i in x["images"]] == [i["alt_text"] for i in eski["images"]]
            and [api.gorsel_bayt(i) for i in x["images"]] == [api.gorsel_bayt(i) for i in eski["images"]]
            and {v["value_id"]: rk.get(v["image_id"]) for v in x["var"]} == {v["value_id"]: eski_rk[v["image_id"]] for v in eski["var"]}
            and [api.video_bayt(v) for v in x["videos"]] == [api.video_bayt(v) for v in eski["videos"]]
            and x["description"] == eski["description"] and x["per"] == eski["per"])


def devam_drive(kok, lid):
    p = drive(kok) / "DEVAM_ILAN" / pd_of(kok) / f"DEVAM_{lid}.json"
    return json.loads(p.read_text()) if p.exists() else None


def birim():
    y, d = K.isim_degistir("1. Name Under Leo (x)\n2. Name Under Leo (y)", "Leo")
    kontrol("metin: Name Under ciftleri -> First Name / Second Name", d == "DEGISTI" and y == "1. First Name (x)\n2. Second Name (y)")
    kontrol("metin: tek sayida kalip TEK", K.isim_degistir("Name Under Leo", "Leo")[1] == "TEK")
    kontrol("metin: zaten degismis ZATEN", K.isim_degistir("First Name and Second Name", "Leo")[1] == "ZATEN")
    mp = K.metin_plani({"description": "Name Under Leo — Name Under Leo"}, PER("Leo", "Leo"), "Leo", "Leo")
    kontrol("metin: yeni metinde uzun tire -> hata", any("tire" in h for h in mp["hata"]))
    mp = K.metin_plani({"description": "Name Under Leo, Name Under Leo. Printed by Printful on 100% cotton"}, PER("Leo", "Leo"), "Leo", "Leo")
    kontrol("metin: YASAK_EN (Printful, cotton) -> hata (eski yerel liste yakalamiyordu)", any("Printful" in h for h in mp["hata"]), mp["hata"])
    mp = K.metin_plani({"description": "Name Under Leo, Name Under Leo. Lasts 100 years"}, PER("Leo", "Leo"), "Leo", "Leo")
    kontrol("metin: RU_YASAK omur yili -> hata", any("years" in h for h in mp["hata"]), mp["hata"])
    mp = K.metin_plani({"description": "Name Under Leo, Name Under Leo"}, PER("Leo", "Leo") + [dict(question_id=78, question_text="Gift note",
                                                                                                     question_type="text_input")], "Leo", "Leo")
    kontrol("metin: birden fazla kisisellestirme sorusu -> BLOK", any("tek soru" in h for h in mp["hata"]), mp["hata"])
    canli = "1. Left name (max 10 letters)\n2. Right name (max 10 letters)\n3. Message (max 30 characters or blank)"   # 12 ilan canli (31 Eki)
    y, d = K.isim_degistir(canli, "Leo")
    kontrol("metin: canli Left name / Right name -> First Name / Second Name (Serdar 31 Eki 7a)", d == "DEGISTI" and y ==
            "1. First Name (max 10 letters)\n2. Second Name (max 10 letters)\n3. Message (max 30 characters or blank)", y)
    kontrol("metin: Left / Right sayisi tutmaz -> TEK", K.isim_degistir("Left name, Left name, Right name", "Leo")[1] == "TEK")
    mp = K.metin_plani({"description": "1. Left name (up to 10 letters)\n2. Right name (up to 10 letters)"},
                       [dict(question_id=5, question_text="Personalization", question_type="text_input", instructions=canli)], "Leo", "Leo")
    kontrol("metin: canli Left / Right aciklama + talimat -> yaz, ikisi de First / Second", mp["yaz"] and not mp["hata"]
            and "First Name" in mp["desc_sonra"] and "Left name" not in mp["desc_sonra"]
            and mp["pers_sonra"][0]["instructions"].startswith("1. First Name (max 10 letters)"), mp["hata"])
    mp = K.metin_plani({"description": "First Name, Second Name"},
                       [dict(question_id=5, question_text="Personalization", question_type="text_input", instructions=canli)], "Leo", "Leo")
    kontrol("metin: aciklama ZATEN ama talimat Left / Right -> talimat yine cevrilir (sessiz kalmaz)", mp["yaz"]
            and mp["pers_sonra"][0]["instructions"].startswith("1. First Name"), mp)
    import kupa_en_ornek as TR   # canli kalipta EN (eski foto numaralari)
    canli_en = TR.en("Leo", "Leo", "Leo gifts")
    mp = K.metin_plani({"description": canli_en}, [dict(question_id=5, question_text="Personalization", question_type="text_input",
                                                         instructions=canli)], "Leo", "Leo")
    import ru_kupa as RK
    kontrol("metin: ayni burc hedef = ru_kupa.kupa_en (foto + Latin + isim; tek kaynak, inceleme 31 Eki)", mp["yaz"] and not mp["hata"]
            and mp["desc_sonra"] == RK.kupa_en(canli_en, "Leo", "Leo")[0], mp["hata"])
    canli_f = TR.en("Cancer", "Libra", "Cancer gifts or Libra gifts")
    mp = K.metin_plani({"description": canli_f}, [], "Cancer", "Libra")
    kontrol("metin: farkli burc hedef = galeri_en (foto + Latin), talimat yok", mp["yaz"] and mp["desc_sonra"] == RK.galeri_en(RK.norm(canli_f))[0]
            and mp["pers_sonra"] is None, mp["hata"])
    yeni_latinsiz = RK.galeri_en(RK.norm(canli_f))[0].replace(RK.LATIN_EN + "\n", "")
    mp = K.metin_plani({"description": yeni_latinsiz}, [], "Cancer", "Libra")
    kontrol("metin: yeni gorsel adli ama Latin notsuz metin -> galeri_en Latin ekler (inceleme 31 Eki: atlaniyordu)", mp["yaz"]
            and RK.LATIN_EN in mp["desc_sonra"] and not RK.hedef_kapisi(mp["desc_sonra"]), mp["hata"])
    mp = K.metin_plani({"description": RK.galeri_en(RK.norm(canli_f))[0].replace("See the sizes photo.", "See photo 9.")}, [], "Cancer", "Libra")
    kontrol("metin: yeni metinde numarali atif -> hata, yazim yok", not mp["yaz"] and mp["hata"], mp["hata"])
    mp = K.metin_plani({"description": "Your names"}, [dict(instructions="Your names")], "Leo", "Leo")
    kontrol("metin: kalip yok -> hata (elle)", any("kalibi" in h for h in mp["hata"]))
    kontrol("metin: farkli burc yazim yok", K.metin_plani({"description": "Name Under Leo"}, [], "Aries", "Leo")["yaz"] is False)
    kontrol("alt metin: YASAK_EN / RU_YASAK kapisi", not K.alt_gecerli("mug printed by Printful") and not K.alt_gecerli("lasts 50 years")
            and K.alt_gecerli("Two mug sizes: 11 oz and 15 oz"))
    ad, mx = K.adim_kur(14, list(range(1, 15)), {1, 8, 9, 10, 11, 12, 13, 14}, list(range(1, 15)), range(7, 15), True)
    sil_once = [a[1] for a in ad[:ad.index(("bag",))] if a[0] == "sil"]
    kontrol("plan: en fazla 20 gorsel, bag oncesi yalniz bagsiz eski silinir", mx == 20 and set(sil_once) <= set(range(2, 8)))
    t14, t20 = K.istek_tahmini(n_sil=14), K.istek_tahmini(n_sil=20)
    yk_k = (2 + 1) + (2 + G.OKUMA_TEKRAR)
    kontrol("istek tahmini: en az < en kotu geri almasiz < en kotu", 0 < t14["en_az"] < t14["en_kotu_geri_almasiz"] < t14["en_kotu"])
    kontrol("istek tahmini: geri alma GERCEK eski gorsel sayisiyla (20 eski: +6 yeniden yukleme + 6 sira yazimi)",
            t20["geri_alma"] - t14["geri_alma"] == 6 * yk_k + 2 * 6 * 4, f"{t20['geri_alma']} - {t14['geri_alma']}")
    tm = K.istek_tahmini(n_sil=14, metin=True)
    print(f"  bilgi: en kotu (geri alma dahil) 14 eski {t14['en_kotu']}, 20 eski {t20['en_kotu']}, metin acik 14 eski {tm['en_kotu']}; "
          f"en az {t14['en_az']} (metin {tm['en_az']})")


def kaynak_testi(tmp):
    k1 = tmp / "kaynak"; k1.mkdir(); sahne(k1)
    man = list(csv.DictReader(open(k1 / "MANIFEST.csv"))); man[0]["sha256"] = "0" * 64
    with open(k1 / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(man[0])); w.writeheader(); w.writerows(man)
    kod = K.main(["kaynak", "--liste", str(k1 / "liste.csv"), "--out", str(k1 / "k"), "--sadece", LID["ARIES_LEO"],
                  "--dosya-dir", str(k1 / "dosya"), "--kart-manifest", str(k1 / "MANIFEST.csv"), "--kapak-kayit", str(k1 / "KAYIT.tsv")])
    kontrol("kaynak: kart sha256 MANIFEST'ten farkli -> FAIL", kod == 1)


def ana(tmp):
    kok = tmp / "ana"; kok.mkdir(); os.environ["SAHTE_DRIVE"] = str(kok / "drive")
    hepsi = ",".join(LID[c] for c in TEST)
    api, pd, S, R = hazirla(kok, hepsi)
    kontrol("kuru: 3 ilan PLAN, yazim yok", all(S[LID[c]]["durum"] == "PLAN" for c in TEST) and not api.yazimlar)
    kontrol("kuru: istek ilan basina 6 (ayni burc +1 RU okumasi)",
            S[LID["ARIES_LEO"]]["istek"] == 6 and S[LID["LEO_LEO"]]["istek"] == 7, f"{[S[LID[c]]['istek'] for c in TEST]}")
    kontrol("kuru: metin varsayilan KAPALI (ayni burc durum KAPALI:DEGISTI, RU_ACIK raporda)",
            S[LID["LEO_LEO"]]["ru"].startswith("RU_ACIK") and S[LID["LEO_LEO"]]["metin"].startswith("KAPALI:")
            and "DEGISTI" in S[LID["LEO_LEO"]]["metin"], S[LID["LEO_LEO"]]["metin"])
    alt_a = f"{LID['ARIES_LEO']}_ARIES_LEO"
    yb = (drive(kok) / "YEDEK" / pd / alt_a / "YEDEK.json").read_bytes(); yd = json.loads(yb)
    kontrol("yedek: 16 gorsel + 8 bag (ad, rank) + 1 video, sha256 + md5, zaman damgasi yok",
            len(yd["galeri"]) == 16 and len(yd["baglar"]) == 8 and len(yd["video"]) == 1 and all(b["stil"] and b["rank"] for b in yd["baglar"])
            and all(x.get("md5") and x.get("sha256") for x in yd["galeri"] + yd["video"]) and "ts_utc" not in yb.decode())

    # ---- madde 1: devam yedegi. Zaman degisir + islenmis ilanin eski CDN adresi 404: ayni bayt, VAR, immutable gecer
    gercek_strftime = time.strftime
    try:
        time.strftime = lambda f, t=None: "2099-01-01 00:00:00"   # yedek ikinci kez baska zamanda
        api.cdn_404 |= {i["url_fullxfull"] for i in api.L[LID["ARIES_LEO"]]["images"]} | {api.L[LID["ARIES_LEO"]]["videos"][0]["video_url"]}
        n_cdn = len(api.cdn_istek)
        kod, cat, eksik, oz = yedek_kos(kok, api, pd, "yedek_out2")
    finally:
        time.strftime = gercek_strftime
    kontrol("devam yedegi: Drive'da tam ilanlar VAR (CDN'e gidilmedi, 404 olsa da), cikis 0, --immutable catisma yok",
            kod == 0 and not cat and not eksik and all(oz[LID[c]]["durum"] == "VAR" for c in TEST) and len(api.cdn_istek) == n_cdn,
            f"kod {kod} cat {cat} {[oz[LID[c]]['durum'] for c in TEST]}")
    # bir ilanin Drive yedegi yarim (1 dosya yok): yeniden kurulur, ayni bayt (zaman damgasi yok) -> immutable gecer
    Y_dr = drive(kok) / "YEDEK" / pd / f"{LID['CANCER_LIBRA']}_CANCER_LIBRA"
    yarim = sorted(Y_dr.glob("r03_*.jpg"))[0]; yarim.unlink()
    try:
        time.strftime = lambda f, t=None: "2099-01-01 00:00:01"
        kod, cat, eksik, oz = yedek_kos(kok, api, pd, "yedek_out3")
    finally:
        time.strftime = gercek_strftime
    kontrol("devam yedegi: yarim Drive yedegi yeniden kurulur, YEDEK.json ayni bayt, --immutable catisma yok",
            kod == 0 and not cat and not eksik and oz[LID["CANCER_LIBRA"]]["durum"] == "PASS" and yarim.exists(), f"{kod} {cat} {eksik}")
    api.cdn_404.clear()

    # ---- madde 6: HTML hata sayfasi yedek sayilmaz (yeni kok: bu ilan Drive'da yok)
    k6 = tmp / "html"; k6.mkdir(); os.environ["SAHTE_DRIVE"] = str(k6 / "drive")
    shutil.copytree(kok / "out_kuru", k6 / "out_kuru"); shutil.copy(kok / "liste.csv", k6)
    api.cdn_html.add(api.L[LID["LEO_LEO"]]["images"][4]["url_fullxfull"])
    kod, cat, eksik, oz = yedek_kos(k6, api, pd, "yedek_out")
    kontrol("yedek: 16 bayt HTML (JPEG imzasi yok) -> o ilan FAIL, Drive'a hicbir dosyasi gitmez, digerleri PASS, cikis 1",
            kod == 1 and oz[LID["LEO_LEO"]]["durum"] == "FAIL" and "imza" in oz[LID["LEO_LEO"]]["neden"]
            and not (k6 / "drive" / "YEDEK" / pd / f"{LID['LEO_LEO']}_LEO_LEO").exists() and oz[LID["ARIES_LEO"]]["durum"] == "PASS",
            f"{kod} {oz[LID['LEO_LEO']]}")
    api.cdn_html.clear(); os.environ["SAHTE_DRIVE"] = str(kok / "drive")

    # haric: ilan hic okunmaz
    c0 = api.calls; api.salt = True
    kod, Sh, _ = kos(api, kok, "kuru", "--sadece", hepsi, "--haric", LID["LEO_LEO"], ad="kuru_haric")
    api.salt = False
    kontrol("haric: ilan raporda yok, okunmadi", LID["LEO_LEO"] not in Sh and len(Sh) == 2 and api.calls - c0 == 12)
    api.salt = True; _, _, R2 = kos(api, kok, "kuru", "--sadece", hepsi, ad="kuru_tekrar"); api.salt = False
    kontrol("kuru tekrar: ayni canli durum -> ayni plan_damga", R2["plan_damga"] == pd)

    # alt metin TASLAK -> yazim yok
    taslak = kok / "alt_taslak.csv"                                   # depo CSV'si ONAYLI (Serdar 31 Eki); test icin TASLAK kopya
    _r = list(csv.DictReader(open(K.ALT_CSV, encoding="utf-8")))
    with open(taslak, "w", newline="") as f:
        _w = csv.DictWriter(f, fieldnames=list(_r[0])); _w.writeheader(); _w.writerows(dict(r, durum="TASLAK") for r in _r)
    try:
        K.sonlandir(api, SHOP, K.arg(["yaz", "--liste", str(kok / "liste.csv"), "--out", str(kok / "o"), "--alt", str(taslak),
                                      "--kaynak", str(kok / "k" / "KAYNAK.csv"), *yaz_arg(kok, pd, "--sadece", LID["ARIES_LEO"])]))
        kontrol("alt TASLAK: yazim DUR", False)
    except SystemExit as e:
        kontrol("alt TASLAK: yazim DUR", "ONAYLI" in str(e.code) and not api.yazimlar)

    # yedek Drive listesinde yok -> yazim yok; Drive'da ayni boyut ama farkli bayt (hash) -> yazim yok
    yol = kok / "lsjson.json"; L = json.loads(yol.read_text())
    yol.write_text(json.dumps([x for x in L if not x["Path"].startswith(f"{LID['CANCER_LIBRA']}_")]))
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
    kontrol("yedek Drive'da yok: BLOK, yazim yok", S[LID["CANCER_LIBRA"]]["durum"] == "BLOK" and not api.yazimlar and kod == 1)
    bozuk = sorted((drive(kok) / "YEDEK" / pd / f"{LID['CANCER_LIBRA']}_CANCER_LIBRA").glob("r05_*.jpg"))[0]
    b0 = bozuk.read_bytes(); bozuk.write_bytes(b0[:-1] + bytes([b0[-1] ^ 1]))
    lsjson_hash(drive(kok) / "YEDEK" / pd, yol)
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
    kontrol("yedek Drive'da ayni boyut, farkli hash: BLOK, yazim yok (boyut kapisi yetmez)", S[LID["CANCER_LIBRA"]]["durum"] == "BLOK"
            and any("hash" in n for n in S[LID["CANCER_LIBRA"]]["neden"]) and not api.yazimlar, str(S[LID["CANCER_LIBRA"]]["neden"])[:200])
    bozuk.write_bytes(b0); lsjson_hash(drive(kok) / "YEDEK" / pd, yol)

    # ---- madde 3 + 5: kalan kota None ile baslar; ilk ilan kapisi gercek eski gorsel sayisiyla (16) en kotu + 10
    lid = LID["ARIES_LEO"]
    gd = json.loads((kok / "out_kuru" / K.PLAN_AD).read_text())["girdiler"][lid]
    t = K.istek_tahmini(n_sil=16)["en_kotu"]
    kontrol("tahmin: plandaki 16 eski gorselle (plan en_kotu degeri eski kodla daha dusuk kalabilir)", K.ilan_tahmini(gd)["en_kotu"] == t)
    api.remaining = None; api.gercek = t + 10        # ucuz GET sonrasi kalan t + 9: en kotu + 10 tutmaz
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid), ad="out_kota")
    kontrol("kota None ile baslangic: tek ucuz GET, kalan - en kotu < 10 -> KALAN, ilan okunmadi, yazim yok",
            S[lid]["durum"] == "KALAN" and S[lid]["istek"] == 0 and not api.yazimlar
            and api.remaining == t + 9, f"{S[lid]} kalan {api.remaining}")

    # pilot (kota None, sinirda baslar): yedek silmeden ONCE ve Drive'da BAYT olarak
    once = {c: copy.deepcopy(api.L[LID[c]]) for c in TEST}
    eski_url = {i["listing_image_id"]: i["url_fullxfull"] for c in TEST for i in api.L[LID[c]]["images"]}
    eski_vid = {v["video_id"]: v["video_url"] for c in TEST for v in api.L[LID[c]]["videos"]}
    sayac = {"gorsel": 0, "video": 0}

    def silme_kontrol(lid_, path):
        cift = next(c for c, v in LID.items() if v == lid_)
        d = drive(kok) / "YEDEK" / pd / f"{lid_}_{cift}"
        m = re.search(r"/(images|videos)/(\d+)$", path); i = int(m.group(2))
        if m.group(1) == "images" and i in eski_url:
            f = sorted(d.glob(f"r??_{i}.jpg"))
            if not (d / "YEDEK.json").exists() or len(f) != 1 or f[0].read_bytes() != api.cdn[eski_url[i]]:
                api.ihlal.append((lid_, i))
            sayac["gorsel"] += 1
        elif m.group(1) == "videos" and i in eski_vid:
            f = d / f"video_{i}.mp4"
            if not f.exists() or f.read_bytes() != api.cdn[eski_vid[i]]:
                api.ihlal.append((lid_, "video", i))
            sayac["video"] += 1
    api.silme_oncesi = silme_kontrol
    api.remaining = None; api.gercek = t + 11
    kod, S, R = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    kontrol("pilot (kota None, kalan = en kotu + 10): PASS, cikis 0", S[lid]["durum"] == "PASS" and kod == 0, str(S[lid]["neden"])[:300])
    api.remaining = 100000
    kontrol("pilot: 14 gorsel hedef sira + alt metin, 8 Style bagi 7-14, yeni video", galeri_hedefte(api, lid, "ARIES_LEO"))
    kontrol("pilot: yuklenen baytlar kaynak dosyalarla ayni", [api.gorsel_bayt(i) for i in api.L[lid]["images"]]
            == [(kok / "dosya" / rel).read_bytes() for s, rel in sorted((k, v) for k, v in K.kaynak_yollari("ARIES_LEO").items() if k != "video")])
    kontrol("pilot: diger ilanlar dokunulmaz", all(api.L[LID[c]] == once[c] for c in TEST if c != "ARIES_LEO"))
    kontrol("yedek silmeden ONCE: silinen her eski gorsel (16) ve video Drive'da bayt bayt ayni", not api.ihlal and sayac == {"gorsel": 16, "video": 1},
            f"{api.ihlal[:3]} {sayac}")
    kontrol("pilot: metin yazilmadi (farkli burc), PATCH yok", not any(y[0] == "PATCH" for y in api.yazimlar)
            and api.L[lid]["description"] == once["ARIES_LEO"]["description"])
    t0 = K.istek_tahmini(n_sil=16)
    kontrol("pilot: istek <= en kotu (geri almasiz) ve >= en az", t0["en_az"] <= S[lid]["istek"] <= t0["en_kotu_geri_almasiz"],
            f"istek {S[lid]['istek']} en az {t0['en_az']}")
    print(f"  bilgi: pilot istek {S[lid]['istek']} (16 eski; en az {t0['en_az']}, en kotu geri almasiz {t0['en_kotu_geri_almasiz']}, "
          f"geri alma +{t0['geri_alma']})")
    ilr = json.loads((kok / "ILERLEME.json").read_text())
    dvd = devam_drive(kok, lid)
    kontrol("pilot: ILERLEME PASS + Drive'da DEVAM_<ilan>.json PASS (son_sira, video)", ilr["ilanlar"][lid]["durum"] == "PASS"
            and len(ilr["ilanlar"][lid]["son_ids"]) == 14 and dvd and dvd["durum"] == "PASS" and dvd["son_sira"] == ilr["ilanlar"][lid]["son_ids"])

    # zaten yapilmis; ILERLEME kosu sonunda yazilamadiysa Drive'daki DEVAM_<ilan> PASS kaydi yeter
    n0 = len(api.yazimlar)
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    kontrol("zaten yapilmis: yazimda ZATEN, yazim yok", S[lid]["durum"] == "ZATEN" and len(api.yazimlar) == n0 and kod == 0)
    (kok / "ILERLEME.json").unlink(); (kok / "DEVAM.json").unlink()
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid), ad="out_zaten2")
    kontrol("ILERLEME / toplu DEVAM yok, Drive DEVAM_<ilan> PASS: ZATEN (KAYITSIZ BLOK degil), ILERLEME geri yazilir",
            S[lid]["durum"] == "ZATEN" and len(api.yazimlar) == n0 and json.loads((kok / "ILERLEME.json").read_text())["ilanlar"][lid]["durum"] == "PASS",
            str(S[lid]))
    api.salt = True
    kod, S, _ = kos(api, kok, "kuru", "--sadece", lid, "--ilerleme", str(kok / "ILERLEME.json"), ad="kuru_zaten")
    api.salt = False
    kontrol("zaten yapilmis: kuruda ZATEN", S[lid]["durum"] == "ZATEN")
    kod, S, _ = kos(api, kok, "kuru", "--sadece", lid, ad="kuru_kayitsiz")
    kontrol("ILERLEME kaydi olmadan hedef galeri: BLOK (KAYITSIZ)", S[lid]["durum"] == "BLOK")

    # canli != plan
    api.L[LID["CANCER_LIBRA"]]["images"][3]["alt_text"] = "elle degisti"
    n0 = len(api.yazimlar)
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
    kontrol("canli != plan: BLOK, yazim yok", S[LID["CANCER_LIBRA"]]["durum"] == "BLOK" and len(api.yazimlar) == n0
            and "canli != plan" in S[LID["CANCER_LIBRA"]]["neden"][0])
    api.L[LID["CANCER_LIBRA"]]["images"][3]["alt_text"] = "eski 4"

    # ---- madde 7: ayni burc, metin varsayilan KAPALI -> galeri PASS, aciklama / kisisellestirme degismez
    lid = LID["LEO_LEO"]
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    x = api.L[lid]
    kontrol("ayni burc (metin kapali): galeri PASS, PATCH / kisisellestirme POST yok, metin eski",
            S[lid]["durum"] == "PASS" and galeri_hedefte(api, lid, "LEO_LEO") and not any(y[0] == "PATCH" or "personalization" in y[2]
                                                                                       for y in api.yazimlar)
            and x["description"] == once["LEO_LEO"]["description"] and x["per"] == once["LEO_LEO"]["per"], str(S[lid]["neden"])[:300])
    kontrol("ayni burc: RU yazimi yok", not any("translations" in str(y) for y in api.yazimlar))

    # planda olmayan ilan ATLA; bozuk plan_damga
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["ARIES_ARIES"]))
    kontrol("planda olmayan ilan: ATLA (okuma yok), cikis 0", S[LID["ARIES_ARIES"]]["durum"] == "ATLA" and S[LID["ARIES_ARIES"]]["istek"] == 0
            and kod == 0)
    try:
        kos(api, kok, "yaz", *yaz_arg(kok, pd[:-1] + ("0" if pd[-1] != "0" else "1"), "--sadece", LID["CANCER_LIBRA"]))
        kontrol("plan_damga bozuk: DUR", False)
    except SystemExit as e:
        kontrol("plan_damga bozuk: DUR", "plan_damga" in str(e.code))

    # parti: PASS ilanlar disarida, azami, yalniz partinin dosyalari
    pa = K.arg(["parti", "--liste", str(kok / "liste.csv"), "--out", str(kok / "parti"), "--plan", str(kok / "out_kuru" / K.PLAN_AD),
                "--plan-damga", pd, "--devam", str(kok / "DEVAM.json"), "--ilerleme", str(kok / "ILERLEME.json"),
                "--devam-ilan-dir", str(kok / "devam_ilan"), "--azami-ilan", "1"])
    devam_indir(kok); K.parti_mod(pa)
    stil = (kok / "parti" / "stil.txt").read_text().split()
    kontrol("parti: PASS ilanlar (ARIES_LEO, LEO_LEO) disarida, azami 1, yalniz o ilanin 8 stil dosyasi",
            (kok / "parti" / "PARTI.txt").read_text() == LID["CANCER_LIBRA"] and len(stil) == 8 and all("CANCER_LIBRA" in s for s in stil)
            and (kok / "parti" / "yedek.txt").read_text().split() == [f"{LID['CANCER_LIBRA']}_CANCER_LIBRA/YEDEK.json"])
    kontrol("azami_ilan varsayilani 15", K.arg(["parti", "--liste", "x", "--out", "x", "--plan", "x", "--plan-damga", "x"]).azami_ilan == 15)


def metin_acik(tmp):
    """madde 7 + 8: --metin-yaz ile (kuru + yaz ayni bayrak) ayni burc metni; POST question_id korur"""
    kok = tmp / "metin"; kok.mkdir(); os.environ["SAHTE_DRIVE"] = str(kok / "drive")
    lid = LID["LEO_LEO"]
    api, pd, S, R = hazirla(kok, lid, metin=True)
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    kontrol("yaz bayraksiz, plan --metin-yaz ile: canli != plan BLOK (bayrak plana bagli), yazim yok", S[lid]["durum"] == "BLOK"
            and not api.yazimlar, str(S[lid]["neden"]))
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid, "--metin-yaz"))
    x = api.L[lid]
    kontrol("metin acik: PASS + galeri hedefte", S[lid]["durum"] == "PASS" and galeri_hedefte(api, lid, "LEO_LEO"), str(S[lid]["neden"])[:300])
    kontrol("metin acik: aciklama ve talimat First Name / Second Name, tire yok", "Name Under" not in x["description"]
            and "1. First Name" in x["description"] and "2. Second Name" in x["description"]
            and x["per"][0]["instructions"].startswith("1. First Name (max 10)\n2. Second Name (max 10)")
            and not TIRE.search(x["description"] + x["per"][0]["instructions"]))
    kontrol("metin acik: PATCH yalniz description (1 kez), kisisellestirme POST question_id 77 ile tek soru",
            [y for y in api.yazimlar if y[0] == "PATCH"] == [("PATCH", lid, ("description",))] and len(api.pers_govde) == 1
            and [q.get("question_id") for q in api.pers_govde[0]["personalization_questions"]] == [77])


def geri(tmp):
    kok = tmp / "geri"; kok.mkdir(); os.environ["SAHTE_DRIVE"] = str(kok / "drive")
    hepsi = ",".join(LID[c] for c in TEST)
    api, pd, S, R = hazirla(kok, hepsi)
    # yukleme hatasi -> geri alma (16 eski gorsel; yedek dosyalari Drive'dan, yerelde yalniz YEDEK.json); sonraki ilan KALAN
    once = copy.deepcopy(api.L[LID["ARIES_LEO"]])
    api.yukleme_hata = 11
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", ",".join(LID[c] for c in ("ARIES_LEO", "CANCER_LIBRA"))))
    lid = LID["ARIES_LEO"]
    kontrol("yukleme hatasi: FAIL + GERI ALINDI", S[lid]["durum"] == "FAIL" and any("GERI ALINDI" in n for n in S[lid]["neden"]),
            str(S[lid]["neden"])[:300])
    kontrol("geri alma: eski galeri bayt bayt (16 gorsel, sira, alt metin), Style baglari, video, metin", eski_halde(api, lid, once))
    kontrol("yukleme hatasi: sonraki ilan KALAN, cikis 1", S[LID["CANCER_LIBRA"]]["durum"] == "KALAN" and kod == 1)
    api.yukleme_hata = None; api.yukleme_say = 0

    # madde 9: video degistikten SONRA son kontrol FAIL -> otomatik geri alma eski videoyu yedekten (bayt) geri yukler
    lid = LID["CANCER_LIBRA"]; once = copy.deepcopy(api.L[lid])
    eski_vid = once["videos"][0]["video_id"]
    api.etiket_boz_video = True
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    api.etiket_boz_video = False
    x = api.L[lid]
    kontrol("video sonrasi son kontrol FAIL: FAIL + geri alindi", S[lid]["durum"] == "FAIL" and "etiket" in S[lid]["neden"][0],
            str(S[lid]["neden"])[:300])
    kontrol("otomatik geri alma: eski video silinmisti, yedekten BAYT olarak geri yuklendi (yeni kimlik), galeri eski",
            len(x["videos"]) == 1 and x["videos"][0]["video_id"] != eski_vid and api.video_bayt(x["videos"][0]) == api.cdn[once["videos"][0]["video_url"]]
            and any(y[0] == "DELETE" and y[2].endswith(f"/videos/{eski_vid}") for y in api.yazimlar) and eski_halde(api, lid, once))

    # bag geri okuma hatasi -> geri alma
    lid = LID["LEO_LEO"]
    api.bag_tutmaz = 1
    api.L[lid]["videos"][0]["video_url"] += "?imza=yeni"   # CDN adresi degisir: canli == plan kapisi kimlikle (adres haric)
    api.cdn[api.L[lid]["videos"][0]["video_url"]] = api.cdn[api.L[lid]["videos"][0]["video_url"].split("?")[0]]
    once = copy.deepcopy(api.L[lid])
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    kontrol("bag geri okuma hatasi: FAIL + geri alindi", S[lid]["durum"] == "FAIL" and "Style bag" in S[lid]["neden"][0], str(S[lid]["neden"])[:300])
    kontrol("bag hatasi geri alma: eski hal (bayt)", eski_halde(api, lid, once))
    kontrol("geri alinan ilanlar DEVAM'da (toplu + Drive) GERI_ALINDI",
            all(json.loads((kok / "DEVAM.json").read_text())["ilanlar"][LID[c]]["durum"] == "GERI_ALINDI" == devam_drive(kok, LID[c])["durum"]
                for c in TEST))


def devam(tmp):
    """madde 2 + 3: kosu ilan ortasinda olur / kota ortada durur -> Drive'daki DEVAM_<ilan>.json ile devam ya da geri_al"""
    kok = tmp / "devam"; kok.mkdir(); os.environ["SAHTE_DRIVE"] = str(kok / "drive")
    hepsi = ",".join(LID[c] for c in TEST)
    api, pd, S, R = hazirla(kok, hepsi)

    # LEO_LEO: 6. yuklemede gorsel olusur, yanittan once surec olur -> toplu DEVAM.json yazilmaz
    lid = LID["LEO_LEO"]
    api.olum_yukleme = 6
    try:
        kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        kontrol("olum: surec oldu", False)
    except Olum:
        pass
    api.olum_yukleme = None
    dv = devam_drive(kok, lid)
    kontrol("olum: toplu DEVAM.json yok, Drive'da DEVAM_<ilan>.json: 5 yeni kimlik + belirsiz yukleme",
            not (kok / "DEVAM.json").exists() and dv and len(dv["yuklenen"]) == 5 and dv.get("belirsiz") and dv["durum"] == "BASLADI", str(dv)[:300])
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    kontrol("olum sonrasi devam (yalniz Drive DEVAM_<ilan>): PASS, toplam 14 yukleme (belirsiz yukleme alt metinle eslendi, cift yok)",
            S[lid]["durum"] == "PASS" and api.yukleme_say == 14 and galeri_hedefte(api, lid, "LEO_LEO"),
            f"{S[lid]['durum']} yukleme {api.yukleme_say} {str(S[lid]['neden'])[:200]}")

    # ARIES_LEO: 14 gorsel yuklendi, video yuklemesi yanitindan once surec olur -> geri_al modu yeni gorselleri ve videoyu tanir
    lid = LID["ARIES_LEO"]; once = copy.deepcopy(api.L[lid])
    api.olum_video = True
    try:
        kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        kontrol("olum (video): surec oldu", False)
    except Olum:
        pass
    api.olum_video = False
    dv = devam_drive(kok, lid)
    kontrol("olum (video): Drive DEVAM_<ilan>: 14 yeni kimlik + video belirsiz", dv and len(dv["yuklenen"]) == 14 and dv.get("video_yeni_belirsiz")
            and len(api.L[lid]["videos"]) == 2, str(dv)[:200])
    (kok / "DEVAM.json").unlink(missing_ok=True)
    kod, S, _ = kos(api, kok, "geri_al", *geri_arg(kok, pd, lid))
    kontrol("geri_al (yalniz Drive DEVAM_<ilan>): eski galeri bayt bayt, baglar, eski video (yeni silindi), cikis 0",
            kod == 0 and S[lid]["durum"] == "PASS" and eski_halde(api, lid, once), str(S[lid]["neden"])[:300])
    kontrol("geri_al: Drive DEVAM_<ilan> GERI_ALINDI", devam_drive(kok, lid)["durum"] == "GERI_ALINDI")

    # CANCER_LIBRA: kota tabani ilan ortasinda -> DUR, geri alma yok, kota_durdu Drive'da; sonra geri_al
    lid = LID["CANCER_LIBRA"]; once = copy.deepcopy(api.L[lid])
    api.kota_kes = api.yazim_say + 9
    kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
    api.kota_kes = None
    dv = devam_drive(kok, lid)
    kontrol("kota tabani ortada: DUR, geri alma yok, Drive DEVAM_<ilan> kota_durdu + yeni kimlikler", S[lid]["durum"] == "DUR"
            and dv["durum"] == "BASLADI" and dv.get("kota_durdu") and len(dv["yuklenen"]) >= 1 and not dv.get("geri_alma"), str(S[lid]["neden"])[:200])
    kod, S, _ = kos(api, kok, "geri_al", *geri_arg(kok, pd, lid))
    kontrol("kota durmasi sonrasi geri_al: eski hal (bayt)", kod == 0 and eski_halde(api, lid, once), str(S[lid]["neden"])[:300])

    # Drive'a DEVAM yazilamiyorsa ilan baslamaz
    kok2 = tmp / "devam2"; kok2.mkdir(); os.environ["SAHTE_DRIVE"] = str(kok2 / "drive")
    api, pd, S, R = hazirla(kok2, LID["CANCER_LIBRA"])
    os.environ["SAHTE_DRIVE_KAPALI"] = "1"
    try:
        kod, S, _ = kos(api, kok2, "yaz", *yaz_arg(kok2, pd, "--sadece", LID["CANCER_LIBRA"]))
    finally:
        os.environ.pop("SAHTE_DRIVE_KAPALI")
    kontrol("DEVAM Drive'a yazilamiyor: DUR, Etsy yazimi yok", S[LID["CANCER_LIBRA"]]["durum"] == "DUR" and not api.yazimlar)


def is_akislari():
    """madde 4 + 2: hazir ayri, kilitsiz, Etsy token yok; yukleyici kilitte, yalniz parti dosyalari, geri_al, DEVAM_<ilan> Drive'a"""
    W = KOK / ".github" / "workflows"
    h = (W / "kupa-galeri78-hazir.yml").read_text(encoding="utf-8")
    y = (W / "kupa-galeri78-yukle.yml").read_text(encoding="utf-8")
    kontrol("hazir: kilit / Etsy token / Etsy sirri yok; --immutable + lsjson --hash dogrulama + VAR girdileri",
            "kilit_bekle" not in h and "ETSY_" not in h and "--immutable" in h and "lsjson -R --hash" in h and "--yedek-var-dir" in h
            and "yerel_drive_eksik" in h)
    k = y.index("python3 scripts/etsy/kilit_bekle.py")
    kontrol("yukle: yedek / CDN / --immutable yok; kilit token ve durum okumasindan once; toplu kaynak indirme yok",
            "kupa_galeri78.py yedek" not in y and "--immutable" not in y and "KUPA_GALERI_KAYNAK/$GD/kapak\" _d/kapak --files-from _work/parti" in y
            and k < y.index("ETSY_TOKEN.json") and k < y.index("durum_dosyasi.py oku") and "needs:" not in y)
    kontrol("yukle: parti on okumasi kilitten once, yetkili parti kilitten sonra; yaz --sadece \"$PARTI\"",
            y.index("--out _work/parti_on") < k < y.index("--out _work/parti\n") and "--sadece \"$PARTI\"" in y and "[ -z \"$PARTI\" ]" in y)
    kontrol("yukle: DEVAM_<ilan> Drive'a her yuklemede (--devam-hedef-kok) ve devamda okunur (--devam-ilan-dir); geri_al modu; azami 15",
            y.count("--devam-hedef-kok \"$O/DEVAM_ILAN/$PD\"") == 2 and y.count("--devam-ilan-dir _work/devam_ilan") >= 2
            and "geri_al" in y and "KUPA_GALERI78_GERI" in y and "azami_ilan: {description: \"yaz: kosu basina en fazla ilan\", required: false, default: \"15\"}" in y)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="kupa78_"))
    rc = tmp / "rclone_sahte"; rc.write_text(SAHTE_RCLONE.replace("{py}", sys.executable)); rc.chmod(0o755)
    os.environ["RCLONE"] = str(rc)
    try:
        birim()
        kaynak_testi(tmp)
        ana(tmp)
        metin_acik(tmp)
        geri(tmp)
        devam(tmp)
        is_akislari()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bas = sum(1 for _, ok in SONUC if not ok)
    print(f"\n{len(SONUC) - bas}/{len(SONUC)} PASS" + (f", {bas} FAIL" if bas else ""))
    return 1 if bas else 0


if __name__ == "__main__":
    sys.exit(main())
