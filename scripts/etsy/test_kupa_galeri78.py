#!/usr/bin/env python3
"""kupa_galeri78.py yerel testi. Ag / Drive / Etsy / token YOK: sahte Etsy (bellekte galeri, Style baglari, video, envanter,
kisisellestirme, aciklama, RU), sentetik ilanlar (9100000001..) ve sentetik JPEG / MP4 baytlari (Pillow gerekmez).
Senaryolar: kaynak kapisi (PASS, kart sha farki FAIL); kuru PLAN (yazim yok, istek 6 / ayni burc +1 RU, RU_ACIK); haric (ilan hic
okunmaz); alt metin TASLAK iken yazim yok; pilot sadece (PASS, 14 gorsel hedef sira + alt metin, 8 bag 7-14, yeni video, diger ilanlar
dokunulmaz, istek <= en kotu); yedek silmeden ONCE (her DELETE aninda YEDEK.json + Drive listesi var); yedek yoksa yazim yok;
canli != plan BLOK; zaten yapilmis ZATEN (kuru + yazim, yazim yok); planda olmayan ilan ATLA; ayni burc metni (First Name / Second Name,
PATCH yalniz description, tire yok); tire / tek sayi / kalip yok kapilari; yukleme hatasi -> geri alma (eski galeri, baglar, video);
bag geri okuma hatasi -> geri alma; kota KALAN (ilan okunmaz); kota tabani ortada -> DEVAM, sonraki kosu cift yukleme olmadan PASS;
elle geri_al modu; plan_damga bozuk DUR. Kullanim: python3 scripts/etsy/test_kupa_galeri78.py"""
import copy
import csv
import hashlib
import json
import re
import shutil
import sys
import tempfile
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
TIRE = re.compile("[–—]")


def kontrol(ad, ok, ek=""):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad + (f" ({ek})" if ek and not ok else ""), flush=True)


def jpeg(tohum):
    return b"\xff\xd8\xff\xe0" + hashlib.sha256(tohum.encode()).digest() * 8


def mp4(tohum):
    return b"\x00\x00\x00\x18ftypmp42" + hashlib.sha256(tohum.encode()).digest() * 8


# ------------------------------------------------------------------ sahte Etsy
class Sahte:
    """Etsy v3 alt kumesi. uploadListingImage (rank ile araya girer; listing_image_id ile sira + alt metin; sira yazimi Style baglarini
    siler, 19 Eyl olcumu), deleteListingImage (bagi da duser), updateVariationImages (tum seti degistirir), video yukle / sil,
    updateListing (PATCH), updateListingPersonalization. Hata: yukleme_hata (n. yuklemede 500, gorsel olusmaz), bag_tutmaz (ilk bag
    POST'u yok sayilir), kota_kes (n. yazimda 'DUR: kota sert tabani', istek gitmez)."""
    def __init__(self, kalan=100000):
        self.L, self.calls, self.remaining, self.yazimlar, self._n, self.cdn = {}, 0, kalan, [], 5_000_000, {}
        self.yukleme_hata = None; self.bag_tutmaz = 0; self.kota_kes = None; self.salt = False
        self.yukleme_say = 0; self.yazim_say = 0; self.silme_oncesi = None; self.ihlal = []

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

    # --- istemci arayuzu
    def kota_kapisi(self, ne="is"):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _say(self, yazim=False):
        if self.remaining < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self.remaining} < 10")
        if yazim:
            if self.salt:
                raise SystemExit("DUR: salt okuma kosusunda Etsy yazma cagrisi")
            self.yazim_say += 1
            if self.kota_kes and self.yazim_say == self.kota_kes:
                raise SystemExit(f"DUR: kota sert tabani: kalan 9 < 10")
        self.calls += 1; self.remaining -= 1

    def _lid(self, path):
        return re.search(r"/listings/(\d+)", path).group(1)

    def _sirala(self, x):
        for i, im in enumerate(x["images"], 1):
            im["rank"] = i

    def get(self, path, params=None, ok404=False):
        self._say()
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
            x["videos"].append(dict(video_id=self._n, video_state="active", video_url=u))
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
        im = dict(listing_image_id=self._n, rank=rk, alt_text=(data or {}).get("alt_text"), url_fullxfull=u, full_width=2000)
        x["images"].insert(min(rk, len(x["images"]) + 1) - 1, im); self._sirala(x)
        assert len(x["images"]) <= 20, "20 gorsel siniri asildi"
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
            self.silme_oncesi(lid)
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
        api.ilan(c, DESC_FARKLI.format(a=a, b=b), PER(a, b))
    return api


def kos(api, kok, mod, *ek, ad=None):
    ad = ad or f"out_{mod}"
    a = K.arg([mod, "--liste", str(kok / "liste.csv"), "--out", str(kok / ad), "--alt", str(kok / "alt.csv"),
               "--kaynak", str(kok / "k" / "KAYNAK.csv"), "--kosu", "777", *ek])
    kod = K.sonlandir(api, SHOP, a)
    R = json.loads((kok / ad / "RAPOR.json").read_text())
    return kod, {s["ilan"]: s for s in R["ilanlar"]}, R


def yaz_arg(kok, pd, *ek):
    return ("--confirm", K.ONAY, "--plan", str(kok / "out_kuru" / K.PLAN_AD), "--plan-damga", pd, "--dosya-dir", str(kok / "dosya"),
            "--yedek-dir", str(kok / "yedek"), "--yedek-liste", str(kok / "lsjson.json"), "--devam", str(kok / "DEVAM.json"),
            "--ilerleme", str(kok / "ILERLEME.json"), *ek)


def drive_liste(kok):
    """yedek klasorunun 'rclone lsjson -R' karsiligi (Drive'a yuklendi varsayimi)"""
    y = kok / "yedek"
    L = [dict(Path=str(p.relative_to(y)), Size=p.stat().st_size, IsDir=False) for p in sorted(y.rglob("*")) if p.is_file()]
    (kok / "lsjson.json").write_text(json.dumps(L))


def hazirla(kok, sadece):
    """kaynak + kuru + yedek; -> (api, plan_damga)"""
    sahne(kok)
    assert K.main(["kaynak", "--liste", str(kok / "liste.csv"), "--out", str(kok / "k"), "--sadece", sadece, "--dosya-dir", str(kok / "dosya"),
                   "--kart-manifest", str(kok / "MANIFEST.csv"), "--kapak-kayit", str(kok / "KAYIT.tsv")]) == 0
    api = sahte_kur()
    api.salt = True
    kod, S, R = kos(api, kok, "kuru", "--sadece", sadece)
    api.salt = False
    pd = R["plan_damga"]
    ya = K.arg(["yedek", "--liste", str(kok / "liste.csv"), "--out", str(kok / "y"), "--plan", str(kok / "out_kuru" / K.PLAN_AD),
                "--plan-damga", pd, "--yedek-dir", str(kok / "yedek"), "--sadece", sadece])
    assert K.yedek_mod(ya, indir=lambda u: api.cdn[u]) == 0
    drive_liste(kok)
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
    x = api.L[lid]
    rk = {i["listing_image_id"]: i["rank"] for i in x["images"]}
    eski_rk = {i["listing_image_id"]: i["rank"] for i in eski["images"]}
    return ([i["alt_text"] for i in x["images"]] == [i["alt_text"] for i in eski["images"]]
            and {v["value_id"]: rk.get(v["image_id"]) for v in x["var"]} == {v["value_id"]: eski_rk[v["image_id"]] for v in eski["var"]}
            and [v["video_url"] for v in x["videos"]] == [v["video_url"] for v in eski["videos"]] and x["description"] == eski["description"]
            and x["per"] == eski["per"])


def main():
    tmp = Path(tempfile.mkdtemp(prefix="kupa78_"))
    try:
        # ---- birim: metin
        y, d = K.isim_degistir("1. Name Under Leo (x)\n2. Name Under Leo (y)", "Leo")
        kontrol("metin: Name Under ciftleri -> First Name / Second Name", d == "DEGISTI" and y == "1. First Name (x)\n2. Second Name (y)")
        kontrol("metin: tek sayida kalip TEK", K.isim_degistir("Name Under Leo", "Leo")[1] == "TEK")
        kontrol("metin: zaten degismis ZATEN", K.isim_degistir("First Name and Second Name", "Leo")[1] == "ZATEN")
        mp = K.metin_plani({"description": "Name Under Leo — Name Under Leo"}, PER("Leo", "Leo"), "Leo", "Leo")
        kontrol("metin: yeni metinde uzun tire -> hata", any("tire" in h for h in mp["hata"]))
        mp = K.metin_plani({"description": "Left name, Right name"}, [dict(instructions="Left name")], "Leo", "Leo")
        kontrol("metin: kalip yok -> hata (elle)", any("kalibi" in h for h in mp["hata"]))
        kontrol("metin: farkli burc yazim yok", K.metin_plani({"description": "Name Under Leo"}, [], "Aries", "Leo")["yaz"] is False)
        ad, mx = K.adim_kur(14, list(range(1, 15)), {1, 8, 9, 10, 11, 12, 13, 14}, list(range(1, 15)), range(7, 15), True)
        sil_once = [a[1] for a in ad[:ad.index(("bag",))] if a[0] == "sil"]
        kontrol("plan: en fazla 20 gorsel, bag oncesi yalniz bagsiz eski silinir", mx == 20 and set(sil_once) <= set(range(2, 8)))
        t = K.istek_tahmini(metin=True)
        kontrol("istek tahmini: en az < en kotu", 0 < t["en_az"] < t["en_kotu_geri_almasiz"] < t["en_kotu"])

        # ---- kaynak kapisi
        k1 = tmp / "kaynak"; k1.mkdir(); sahne(k1)
        man = list(csv.DictReader(open(k1 / "MANIFEST.csv"))); man[0]["sha256"] = "0" * 64
        with open(k1 / "MANIFEST.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(man[0])); w.writeheader(); w.writerows(man)
        kod = K.main(["kaynak", "--liste", str(k1 / "liste.csv"), "--out", str(k1 / "k"), "--sadece", LID["ARIES_LEO"],
                      "--dosya-dir", str(k1 / "dosya"), "--kart-manifest", str(k1 / "MANIFEST.csv"), "--kapak-kayit", str(k1 / "KAYIT.tsv")])
        kontrol("kaynak: kart sha256 MANIFEST'ten farkli -> FAIL", kod == 1)

        # ---- ana akis
        kok = tmp / "ana"; kok.mkdir()
        hepsi = ",".join(LID[c] for c in TEST)
        api, pd, S, R = hazirla(kok, hepsi)
        kontrol("kuru: 3 ilan PLAN, yazim yok", all(S[LID[c]]["durum"] == "PLAN" for c in TEST) and not api.yazimlar)
        kontrol("kuru: istek ilan basina 6 (ayni burc +1 RU okumasi)",
                S[LID["ARIES_LEO"]]["istek"] == 6 and S[LID["LEO_LEO"]]["istek"] == 7, f"{[S[LID[c]]['istek'] for c in TEST]}")
        kontrol("kuru: ayni burc RU_ACIK raporda, metin DEGISTI", S[LID["LEO_LEO"]]["ru"].startswith("RU_ACIK")
                and "DEGISTI" in S[LID["LEO_LEO"]]["metin"])
        yd = json.loads((kok / "yedek" / f"{LID['ARIES_LEO']}_ARIES_LEO" / "YEDEK.json").read_text())
        kontrol("yedek: 14 gorsel + 8 bag (ad, rank) + 1 video, sha256", len(yd["galeri"]) == 14 and len(yd["baglar"]) == 8
                and len(yd["video"]) == 1 and all(b["stil"] and b["rank"] for b in yd["baglar"]))

        # haric: ilan hic okunmaz
        c0 = api.calls; api.salt = True
        kod, Sh, _ = kos(api, kok, "kuru", "--sadece", hepsi, "--haric", LID["LEO_LEO"], ad="kuru_haric")
        api.salt = False
        kontrol("haric: ilan raporda yok, okunmadi", LID["LEO_LEO"] not in Sh and len(Sh) == 2 and api.calls - c0 == 12)
        api.salt = True; _, _, R2 = kos(api, kok, "kuru", "--sadece", hepsi, ad="kuru_tekrar"); api.salt = False
        kontrol("kuru tekrar: ayni canli durum -> ayni plan_damga", R2["plan_damga"] == pd)

        # alt metin TASLAK -> yazim yok
        taslak = kok / "alt_taslak.csv"; shutil.copy(K.ALT_CSV, taslak)
        try:
            K.sonlandir(api, SHOP, K.arg(["yaz", "--liste", str(kok / "liste.csv"), "--out", str(kok / "o"), "--alt", str(taslak),
                                          "--kaynak", str(kok / "k" / "KAYNAK.csv"), *yaz_arg(kok, pd, "--sadece", LID["ARIES_LEO"])]))
            kontrol("alt TASLAK: yazim DUR", False)
        except SystemExit as e:
            kontrol("alt TASLAK: yazim DUR", "ONAYLI" in str(e.code) and not api.yazimlar)

        # yedek yoksa yazim yok
        yol = kok / "lsjson.json"; L = json.loads(yol.read_text())
        yol.write_text(json.dumps([x for x in L if not x["Path"].startswith(f"{LID['CANCER_LIBRA']}_")]))
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
        kontrol("yedek Drive'da yok: BLOK, yazim yok", S[LID["CANCER_LIBRA"]]["durum"] == "BLOK" and not api.yazimlar and kod == 1)
        drive_liste(kok)

        # pilot sadece: yedek silmeden once
        once = {c: copy.deepcopy(api.L[LID[c]]) for c in TEST}

        def silme_kontrol(lid):
            cift = next(c for c, v in LID.items() if v == lid)
            p = kok / "yedek" / f"{lid}_{cift}" / "YEDEK.json"
            ls = {x["Path"] for x in json.loads((kok / "lsjson.json").read_text())}
            if not p.exists() or f"{lid}_{cift}/YEDEK.json" not in ls:
                api.ihlal.append(lid)
        api.silme_oncesi = silme_kontrol
        c0 = api.calls
        kod, S, R = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["ARIES_LEO"]))
        lid = LID["ARIES_LEO"]
        kontrol("pilot sadece: PASS, cikis 0", S[lid]["durum"] == "PASS" and kod == 0, str(S[lid]["neden"])[:300])
        kontrol("pilot: 14 gorsel hedef sira + alt metin, 8 Style bagi 7-14, yeni video", galeri_hedefte(api, lid, "ARIES_LEO"))
        kontrol("pilot: diger ilanlar dokunulmaz", all(api.L[LID[c]] == once[c] for c in TEST if c != "ARIES_LEO"))
        kontrol("yedek silmeden ONCE (her DELETE aninda YEDEK.json + Drive listesi)", not api.ihlal and any(y[0] == "DELETE" for y in api.yazimlar))
        kontrol("pilot: metin yazilmadi (farkli burc), PATCH yok", not any(y[0] == "PATCH" for y in api.yazimlar)
                and api.L[lid]["description"] == once["ARIES_LEO"]["description"])
        t0 = K.istek_tahmini()
        kontrol("pilot: istek <= en kotu (geri almasiz) ve >= en az", t0["en_az"] <= S[lid]["istek"] <= t0["en_kotu_geri_almasiz"],
                f"istek {S[lid]['istek']} en az {t0['en_az']}")
        print(f"  bilgi: pilot istek {S[lid]['istek']} (en az {t0['en_az']}, en kotu geri almasiz {t0['en_kotu_geri_almasiz']}, "
              f"geri alma +{t0['geri_alma']})")
        ilr = json.loads((kok / "ILERLEME.json").read_text())
        kontrol("pilot: ILERLEME PASS kaydi (son_ids, video)", ilr["ilanlar"][lid]["durum"] == "PASS" and len(ilr["ilanlar"][lid]["son_ids"]) == 14)

        # zaten yapilmis
        n0 = len(api.yazimlar)
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["ARIES_LEO"]))
        kontrol("zaten yapilmis: yazimda ZATEN, yazim yok", S[lid]["durum"] == "ZATEN" and len(api.yazimlar) == n0 and kod == 0)
        api.salt = True
        kod, S, _ = kos(api, kok, "kuru", "--sadece", LID["ARIES_LEO"], "--ilerleme", str(kok / "ILERLEME.json"), ad="kuru_zaten")
        api.salt = False
        kontrol("zaten yapilmis: kuruda ZATEN", S[lid]["durum"] == "ZATEN")
        kod, S, _ = kos(api, kok, "kuru", "--sadece", LID["ARIES_LEO"], ad="kuru_kayitsiz")
        kontrol("ILERLEME kaydi olmadan hedef galeri: BLOK (KAYITSIZ)", S[lid]["durum"] == "BLOK")

        # canli != plan
        api.L[LID["CANCER_LIBRA"]]["images"][3]["alt_text"] = "elle degisti"
        n0 = len(api.yazimlar)
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
        kontrol("canli != plan: BLOK, yazim yok", S[LID["CANCER_LIBRA"]]["durum"] == "BLOK" and len(api.yazimlar) == n0
                and "canli != plan" in S[LID["CANCER_LIBRA"]]["neden"][0])
        api.L[LID["CANCER_LIBRA"]]["images"][3]["alt_text"] = "eski 4"

        # ayni burc metni
        lid = LID["LEO_LEO"]
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        x = api.L[lid]
        kontrol("ayni burc: PASS + galeri hedefte", S[lid]["durum"] == "PASS" and galeri_hedefte(api, lid, "LEO_LEO"), str(S[lid]["neden"])[:300])
        kontrol("ayni burc: aciklama ve talimat First Name / Second Name", "Name Under" not in x["description"]
                and "1. First Name" in x["description"] and "2. Second Name" in x["description"]
                and x["per"][0]["instructions"].startswith("1. First Name (max 10)\n2. Second Name (max 10)"))
        kontrol("ayni burc: PATCH yalniz description (1 kez)", [y for y in api.yazimlar if y[0] == "PATCH"] == [("PATCH", lid, ("description",))])
        kontrol("tire yok: aciklama + talimat", not TIRE.search(x["description"] + x["per"][0]["instructions"]))
        kontrol("ayni burc: RU yazimi yok", not any("translations" in str(y) for y in api.yazimlar))

        # planda olmayan ilan ATLA (kuru PLAN degil), kota KALAN
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["ARIES_ARIES"]))
        kontrol("planda olmayan ilan: ATLA (okuma yok), cikis 0", S[LID["ARIES_ARIES"]]["durum"] == "ATLA" and S[LID["ARIES_ARIES"]]["istek"] == 0
                and kod == 0)
        api.remaining = 50; c0 = api.calls
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", LID["CANCER_LIBRA"]))
        kontrol("kota: kalan - en kotu < 10 -> KALAN, istek yok", S[LID["CANCER_LIBRA"]]["durum"] == "KALAN" and api.calls == c0 and kod == 1)
        api.remaining = 100000

        # bozuk plan_damga
        try:
            kos(api, kok, "yaz", *yaz_arg(kok, pd[:-1] + ("0" if pd[-1] != "0" else "1"), "--sadece", LID["CANCER_LIBRA"]))
            kontrol("plan_damga bozuk: DUR", False)
        except SystemExit as e:
            kontrol("plan_damga bozuk: DUR", "plan_damga" in str(e.code))

        # ---- yukleme hatasi -> geri alma; sonraki ilan KALAN
        kok = tmp / "geri"; kok.mkdir()
        api, pd, S, R = hazirla(kok, hepsi)
        once = copy.deepcopy(api.L[LID["ARIES_LEO"]])
        api.yukleme_hata = 11
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", ",".join(LID[c] for c in ("ARIES_LEO", "CANCER_LIBRA"))))
        lid = LID["ARIES_LEO"]
        kontrol("yukleme hatasi: FAIL + GERI ALINDI", S[lid]["durum"] == "FAIL" and any("GERI ALINDI" in n for n in S[lid]["neden"]),
                str(S[lid]["neden"])[:300])
        kontrol("geri alma: eski galeri (sira, alt metin), Style baglari, video, metin", eski_halde(api, lid, once))
        kontrol("yukleme hatasi: sonraki ilan KALAN, cikis 1", S[LID["CANCER_LIBRA"]]["durum"] == "KALAN" and kod == 1)

        # ---- bag geri okuma hatasi -> geri alma
        api.yukleme_hata = None; api.yukleme_say = 0
        dv = json.loads((kok / "DEVAM.json").read_text())
        lid = LID["CANCER_LIBRA"]; once = copy.deepcopy(api.L[lid])
        api.bag_tutmaz = 1
        api.L[lid]["videos"][0]["video_url"] += "?imza=yeni"   # CDN adresi degisir: canli == plan kapisi kimlikle (adres haric)
        once = copy.deepcopy(api.L[lid])
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        kontrol("bag geri okuma hatasi: FAIL + geri alindi", S[lid]["durum"] == "FAIL" and "Style bag" in S[lid]["neden"][0], str(S[lid]["neden"])[:300])
        kontrol("bag hatasi geri alma: eski hal", eski_halde(api, lid, once))
        kontrol("geri alinan ilan DEVAM'da GERI_ALINDI", json.loads((kok / "DEVAM.json").read_text())["ilanlar"][lid]["durum"] == "GERI_ALINDI"
                and dv["ilanlar"][LID["ARIES_LEO"]]["durum"] == "GERI_ALINDI")

        # ---- kota tabani ortada -> DEVAM; sonraki kosu cift yukleme olmadan PASS
        kok = tmp / "devam"; kok.mkdir()
        api, pd, S, R = hazirla(kok, hepsi)
        lid = LID["LEO_LEO"]
        api.kota_kes = 9
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        dv = json.loads((kok / "DEVAM.json").read_text())["ilanlar"][lid]
        kontrol("kota tabani ortada: DUR, geri alma yok, DEVAM kaydi", S[lid]["durum"] == "DUR" and dv["durum"] == "BASLADI"
                and len(dv["yuklenen"]) >= 1 and not dv.get("geri_alma"), str(S[lid]["neden"])[:200])
        api.kota_kes = None
        kod, S, _ = kos(api, kok, "yaz", *yaz_arg(kok, pd, "--sadece", lid))
        kontrol("devam: PASS, toplam 14 yukleme (cift yukleme yok)", S[lid]["durum"] == "PASS" and api.yukleme_say == 14
                and galeri_hedefte(api, lid, "LEO_LEO"), f"{S[lid]['durum']} yukleme {api.yukleme_say} {str(S[lid]['neden'])[:200]}")

        # ---- elle geri_al modu
        once_y = json.loads((kok / "yedek" / f"{lid}_LEO_LEO" / "YEDEK.json").read_text())
        vid_pass = api.L[lid]["videos"][0]["video_id"]
        a = K.arg(["geri_al", "--liste", str(kok / "liste.csv"), "--out", str(kok / "gg"), "--confirm", K.ONAY_GERI, "--sadece", lid,
                   "--yedek-dir", str(kok / "yedek"), "--plan-damga", pd, "--devam", str(kok / "DEVAM.json")])
        kod = K.sonlandir(api, SHOP, a)
        x = api.L[lid]
        kontrol("geri_al modu: eski galeri alt metinleri, 8 bag eski siralarda, eski metin", kod == 0
                and [i["alt_text"] for i in x["images"]] == [g["alt_text"] for g in once_y["galeri"]]
                and x["description"] == once_y["metin"]["desc_once"] and "Name Under Leo" in x["per"][0]["instructions"]
                and len(x["var"]) == 8 and len(x["videos"]) == 1 and x["videos"][0]["video_id"] != vid_pass)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bas = sum(1 for _, ok in SONUC if not ok)
    print(f"\n{len(SONUC) - bas}/{len(SONUC)} PASS" + (f", {bas} FAIL" if bas else ""))
    return 1 if bas else 0


if __name__ == "__main__":
    sys.exit(main())
