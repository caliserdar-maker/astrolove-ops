#!/usr/bin/env python3
"""w05_degistir.py yerel testi. Ag / Drive / Etsy / token YOK: sahte Etsy (bellekte galeri, renk baglari) + sentetik ilanlar
(9100000001..4) + sentetik JPEG. Bilinen PASS ve bilinen FAIL:
  plan: PLAN; W05'e renk bagi -> BLOK; MANIFEST kimlik zinciri FAIL -> BLOK; galeri 20 -> BLOK; plan_damga bozuk -> DUR.
  kuru: HAZIR, yazim yok, istek 3. Yazim: kilit yok / --sadece yok / onay yok -> DUR (yazim yok).
  pilot: PASS (rank 5 yeni, alt metin = eski W05, eski silindi, digerleri ayni, baglar ayni, istek = en az tahmini, diger ilan dokunulmaz).
  yukleme sonrasi sha tutmaz -> DUR, eski W05 SILINMEZ; alt metin farkli -> DUR, eski silinmez; yukleme rank 5'e oturmaz -> DUR, silinmez;
  yeni gorsel yokken silme denemesi -> FAIL (silme yok); canli != plan -> BLOK; canli r5 kimligi plandan farkli -> BLOK;
  silme hatasi -> DUR (YARIM, ARA kaydi) -> --kurtar -> PASS; --devam -> ZATEN (yazim yok); DUR sonrasi sonraki ilan KALAN; kota -> KALAN.
Kullanim: python3 scripts/kapak78/test_w05_degistir.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import copy
import csv
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
import w05_degistir as W  # noqa: E402

G.OKUMA_BEKLE = 0; Y.BEKLE_429 = 0
SONUC = []
SHOP = "1"
ILAN = [("9100000001", "ARIES_LEO"), ("9100000002", "CANCER_CANCER"), ("9100000003", "LIBRA_VIRGO"), ("9100000004", "LEO_LEO")]


def k(ad, ok, ayr=""):
    SONUC.append(bool(ok)); print(("PASS " if ok else "FAIL ") + ad + ("" if ok else f"  [{str(ayr)[:300]}]"), flush=True)


class Sahte:
    """Etsy v3 alt kumesi: getListing, getListingImages, getListingVariationImages, uploadListingImage (rank), deleteListingImage.
    Ayarlar: rank_yok (yukleme rank'i yok sayilir, sona oturur), alt_bozuk (alt metin degisir), dosya_boz (yukleme sirasinda yerel dosya
    degisir: yuklenen dosya sha256 != MANIFEST), sil_hata (ilk silme 500), sikistirmaz (silmeden sonra rank'lar sikistirilmaz: canli
    Etsy 28 / 30 Eyl), bag_dus (yukleme renk baglarini siler: 19 Eyl olcumu), boyut_boz (yeni gorsel 1500x1125), bilinmiyor (kalan
    kota ilk istege kadar None: gercek etsy_common)."""
    def __init__(self, L, kalan=5000, bilinmiyor=False):
        self.L, self.calls, self._kalan, self.yazimlar, self._n = L, 0, kalan, [], 7_000_000
        self.remaining = None if bilinmiyor else kalan
        self.rank_yok = self.alt_bozuk = self.sil_hata = self.sikistirmaz = self.bag_dus = self.boyut_boz = False; self.dosya_boz = None
        self.bag_post_yok = self.yukleme_hata = self.boyut_yok = False   # bag POST'u yok sayilir / yukleme 500 ve gorsel olusmaz (belirsiz yukleme)

    def kota_kapisi(self, ne="is"):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _say(self):
        if self._kalan < 10:
            raise SystemExit(f"DUR: kota sert tabani: kalan {self._kalan} < 10")
        self.calls += 1; self._kalan -= 1; self.remaining = self._kalan

    def _lid(self, p):
        return re.search(r"/listings/(\d+)", p).group(1)

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            raise AssertionError("yazim _call ile gelmez")
        self._say(); x = self.L[self._lid(path)]
        if path.endswith("/images"):
            return {"results": copy.deepcopy(sorted(x["images"], key=lambda i: i["rank"]))}
        if path.endswith("/variation-images"):
            return {"results": copy.deepcopy(x["var"])}
        return {"state": x["state"]}

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params, ok404=ok404)

    def post_file(self, path, files, data=None, tekrar=3):
        self._say(); lid = self._lid(path); x = self.L[lid]
        if self.yukleme_hata:
            raise SystemExit(f"POST {path} -> 500")
        self._n += 1; yid = self._n
        n = len(x["images"])
        rank = n + 1 if self.rank_yok else int((data or {}).get("rank") or n + 1)
        for i in x["images"]:
            if i["rank"] >= rank:
                i["rank"] += 1
        alt = (data or {}).get("alt_text") + (" X" if self.alt_bozuk else "")
        x["images"].append(dict(listing_image_id=yid, rank=min(rank, n + 1), alt_text=alt, url_fullxfull=f"u/{yid}",
                                **({} if self.boyut_yok else dict(full_width=1500 if self.boyut_boz else 3000,
                                                                   full_height=1125 if self.boyut_boz else 2250))))
        if self.bag_dus:
            x["var"] = []
        if self.dosya_boz:
            Path(self.dosya_boz).write_bytes(b"bozuk")
        self.yazimlar.append(("upload", lid, yid))
        return {"listing_image_id": yid}

    def delete(self, path, ok404=False):
        self._say(); lid = self._lid(path); x = self.L[lid]
        iid = int(path.rstrip("/").split("/")[-1])
        assert ok404, "silme ok404=True ile cagrilmali (5xx tekrarinda 404 = zaten silinmis)"
        if iid not in [i["listing_image_id"] for i in x["images"]]:
            return None
        if self.sil_hata:
            self.sil_hata = False
            raise SystemExit(f"DELETE {path} -> 500")
        self.yazimlar.append(("sil", lid, iid))
        x["images"] = [i for i in x["images"] if i["listing_image_id"] != iid]
        if not self.sikistirmaz:
            for n, i in enumerate(sorted(x["images"], key=lambda i: i["rank"]), 1):
                i["rank"] = n
        return {}

    def post_json(self, path, body):
        self._say(); lid = self._lid(path); x = self.L[lid]
        assert path.endswith("/variation-images"), path
        self.yazimlar.append(("bag", lid, len(body["variation_images"])))
        if not self.bag_post_yok:
            x["var"] = [dict(property_id=b["property_id"], value_id=b["value_id"], image_id=b["image_id"]) for b in body["variation_images"]]
        return {}

    def _yasak(self, *a, **kw):
        raise AssertionError("beklenmeyen yazim yontemi")
    post = put = patch = put_json = _yasak


def ilan_kur(lid, n=11, w05_bag=False):
    base = int(lid[-1]) * 1000
    imgs = [dict(listing_image_id=base + r, rank=r, alt_text=f"alt {lid} {r}" if r != 5 else
                 "How your order works: preview via Etsy Messages, your approval, made to order and free shipping", url_fullxfull="u")
            for r in range(1, n + 1)]
    var = [dict(property_id=200, value_id=100 + r, image_id=base + r) for r in (7, 8, 9, 10, 11) if r <= n]
    if w05_bag:
        var.append(dict(property_id=200, value_id=99, image_id=base + 5))
    return dict(state="active", images=imgs, var=var)


def galeri_json(lid, cift, x):
    return dict(listing_id=lid, cift=cift, gorseller=[dict(rank=i["rank"], listing_image_id=i["listing_image_id"], alt_text=i["alt_text"])
                                                      for i in x["images"]], baglar=x["var"])


def kur(td, ayar=None):
    """sentetik canli okuma + MANIFEST + dosyalar + plan"""
    ayar = ayar or {}
    L = {lid: ilan_kur(lid, n=ayar.get(lid, {}).get("n", 11), w05_bag=ayar.get(lid, {}).get("bag", False)) for lid, _ in ILAN}
    for lid, _ in ILAN:
        if ayar.get(lid, {}).get("cift_bosluk"):
            r5 = next(i for i in L[lid]["images"] if i["rank"] == 5); r5["alt_text"] = r5["alt_text"].replace(" ", "  ", 1)
    cd, dd = td / "canli", td / "dosya"; dd.mkdir(parents=True, exist_ok=True)
    rows = []
    for lid, cift in ILAN:
        (cd / f"{lid}_{cift}").mkdir(parents=True, exist_ok=True)
        (cd / f"{lid}_{cift}" / "GALERI.json").write_text(json.dumps(galeri_json(lid, cift, L[lid])))
        b = io.BytesIO(); Image.new("RGB", (64, 48), (int(lid[-1]) * 40, 10, 10)).save(b, "JPEG", quality=95)
        (dd / f"{cift}_W05_SUREC.jpg").write_bytes(b.getvalue())
        kim = ayar.get(lid, {}).get("kimlik", "PASS")
        rows.append(dict(cift=ayar.get(lid, {}).get("m_cift", cift), ilan=lid, dosya=f"{cift}_W05_SUREC.jpg", sha256=Y.sha256(dd / f"{cift}_W05_SUREC.jpg"), kimlik=kim,
                         canli_ocr="PASS", bilinen_pass="PASS", durum="PASS" if kim == "PASS" else "DUR"))
    with open(td / "MANIFEST_W05.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(td / "ciftler.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "cift"]); w.writeheader(); w.writerows(dict(listing_id=a, cift=b) for a, b in ILAN)
    rc = W.plan_kur(cd, td / "MANIFEST_W05.csv", td / "ciftler.csv", td / "plan", "123")
    P = json.loads((td / "plan" / W.PLAN_AD).read_text())
    return L, dd, P, rc


def kos(api, td, P, *ek, out="o"):
    if "--confirm" in ek and "--sadece" in ek:   # is akisi onay girdisi (W05-YAZ-<sadece>) Python'a da gecer
        ek = (*ek, "--onay", f"W05-YAZ-{ek[ek.index('--sadece') + 1]}")
    a = W.arg(["etsy", "--plan", str(td / "plan" / W.PLAN_AD), "--plan-damga", P["plan_damga"], "--out", str(td / out), *ek])
    rc = W.sonlandir(api, SHOP, a)
    return rc, json.loads((td / out / "RAPOR.json").read_text())


def durum(R, lid):
    return next(s for s in R["ilanlar"] if s["ilan"] == lid)


def ids(x):
    return [i["listing_image_id"] for i in sorted(x["images"], key=lambda i: i["rank"])]


t = W.istek_tahmini()
k(f"istek tahmini: kuru 3, en az 16, en kotu {t['yaz_en_kotu']} (O={t['okuma_tekrar']}; bag yazimi + onarim + TANI 2), kota = en kotu + 10",
  t["kuru"] == 3 and t["yaz_en_az"] == 16 and t["kota_ihtiyac"] == t["yaz_en_kotu"] + 10)

# ---------- plan
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, rc = kur(td, {"9100000002": dict(bag=True), "9100000003": dict(kimlik="FAIL"), "9100000004": dict(n=20)})
    st = {s["ilan"]: s for s in P["satirlar"]}
    st = {s["ilan"]: s for s in P["satirlar"]}
    k("plan: normal ilan PLAN (eski r5 id, eski W05 alt metni, sha)", st["9100000001"]["durum"] == "PLAN"
      and P["girdiler"]["9100000001"]["eski_id"] == 1005 and P["girdiler"]["9100000001"]["alt"].startswith("How your order works"))
    k("bilinen FAIL: W05'e renk bagi var -> plan BLOK", st["9100000002"]["durum"] == "BLOK" and P["w05_bagli"] == 1, st["9100000002"])
    k("bilinen FAIL: taban kimlik zinciri tutmaz (MANIFEST kimlik FAIL) -> plan BLOK", st["9100000003"]["durum"] == "BLOK", st["9100000003"])
    k("bilinen FAIL: galeri 20 (+1 > 20) -> plan BLOK", st["9100000004"]["durum"] == "BLOK", st["9100000004"])
    k("plan: BLOK varsa cikis 1", rc == 1)
    L, dd, P, rc = kur(td / "m", {"9100000001": dict(m_cift="LEO_LEO"), "9100000002": dict(cift_bosluk=True)})
    k("bilinen FAIL: eski W05 ham alt metninde cift bosluk (AYNEN gidemez) -> plan BLOK",
      {s["ilan"]: s for s in P["satirlar"]}["9100000002"]["durum"] == "BLOK", P["satirlar"])
    k("bilinen FAIL: MANIFEST satiri baska ciftin (cift / dosya ilanla eslesmez) -> plan BLOK",
      {s["ilan"]: s for s in P["satirlar"]}["9100000001"]["durum"] == "BLOK")

# ---------- yazim yollari
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, rc = kur(td)
    k("plan: 4/4 PLAN, cikis 0", rc == 0 and P["ilan_plan"] == 4, P["satirlar"])
    api = Sahte(L)
    rc, R = kos(api, td, P, "--kuru", "--dosya-dir", str(dd), out="kuru")
    k("kuru: 4 HAZIR, yazim 0, istek 4 x 3, kart sha256 = plan", rc == 0 and R["sayilar"] == {"HAZIR": 4} and not api.yazimlar and api.calls == 12,
      R["sayilar"])
    try:
        W.arg(["etsy", "--plan", "x", "--plan-damga", "1_" + "0" * 12, "--out", "o", "--kuru"]); h = None
    except SystemExit as e:
        h = str(e)
    k("bilinen FAIL: kuru --dosya-dir yok (kart sha kontrolu yapilamaz) -> DUR", h and "dosya-dir" in h, h)
    yedek_kart = (dd / "ARIES_LEO_W05_SUREC.jpg").read_bytes(); (dd / "ARIES_LEO_W05_SUREC.jpg").write_bytes(b"baska")
    rc, R = kos(api := Sahte(L), td, P, "--kuru", "--dosya-dir", str(dd), "--sadece", "9100000001", out="kuru_sha")
    k("bilinen FAIL: kuru kart sha256 plandan farkli -> BLOK, istek yok", durum(R, "9100000001")["durum"] == "BLOK" and api.calls == 0, R["ilanlar"])
    (dd / "ARIES_LEO_W05_SUREC.jpg").write_bytes(yedek_kart)
    for ek, ne in ((["--confirm", W.ONAY, "--dosya-dir", str(dd)], "--sadece yok"), (["--dosya-dir", str(dd), "--sadece", "9100000001"], "onay yok")):
        try:
            W.arg(["etsy", "--plan", "x", "--plan-damga", "1_" + "0" * 12, "--out", "o", *ek]); h = None
        except SystemExit as e:
            h = str(e)
        k(f"bilinen FAIL: yazim {ne} -> DUR", h and "DUR" in h, h)
    os.environ.pop(W.KILIT_ORTAM, None)
    try:
        W.arg(["etsy", "--plan", "x", "--plan-damga", "1_" + "0" * 12, "--out", "o", "--confirm", W.ONAY, "--dosya-dir", str(dd),
               "--sadece", "9100000001", "--onay", "W05-YAZ-9100000001"]); h = None
    except SystemExit as e:
        h = str(e)
    k("bilinen FAIL: yazim Etsy kilidi yok (W05_KILIT) -> DUR", h and W.KILIT_ORTAM in h, h)
    for onay in ("", "W05-KURU-9100000001", "W05-YAZ-9100000002"):
        try:
            W.arg(["etsy", "--plan", "x", "--plan-damga", "1_" + "0" * 12, "--out", "o", "--confirm", W.ONAY, "--dosya-dir", str(dd),
                   "--sadece", "9100000001", "--onay", onay]); h = None
        except SystemExit as e:
            h = str(e)
        k(f"bilinen FAIL: yazim onay {onay!r} (kip / ilan birebir degil) -> DUR", h and "--onay" in h, h)
    os.environ[W.KILIT_ORTAM] = "1"
    YAZ = ["--confirm", W.ONAY, "--dosya-dir", str(dd)]

    # pilot PASS
    once = {lid: ids(L[lid]) for lid, _ in ILAN}
    var0 = copy.deepcopy(L["9100000001"]["var"])
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000001", out="pilot")
    s = durum(R, "9100000001"); yid = s["yeni_id"]
    g = sorted(L["9100000001"]["images"], key=lambda i: i["rank"])
    k("pilot: PASS, yazim = 1 yukleme + 1 silme + 1 bag yazimi (plandaki baglar aynen)", rc == 0 and s["durum"] == "PASS"
      and [w[0] for w in api.yazimlar] == ["upload", "sil", "bag"], (s, api.yazimlar))
    k("pilot: rank 5 = yeni gorsel, alt metin = eski W05 alt metni", g[4]["listing_image_id"] == yid and g[4]["alt_text"].startswith("How your order"))
    k("pilot: galeri 11, diger kimlikler ve sira ayni (eski W05 yerine yeni), eski silindi",
      ids(L["9100000001"]) == [yid if i == 1005 else i for i in once["9100000001"]] and 1005 not in ids(L["9100000001"]))
    k("pilot: renk baglari aynen", L["9100000001"]["var"] == var0)
    k(f"pilot: istek {s['istek']} = en az tahmini {t['yaz_en_az']}", s["istek"] == t["yaz_en_az"], s["istek"])
    k("pilot: diger ilanlar dokunulmadi", all(ids(L[lid]) == once[lid] for lid, _ in ILAN[1:]))
    k("pilot: SONRA kaydi (yeni id, sha256 = MANIFEST)", json.loads((td / "pilot" / "ilanlar" / "SONRA_9100000001.json").read_text())["sha256"]
      == P["girdiler"]["9100000001"]["sha256"])

    # devam -> ZATEN
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000001", "--devam", "--onceki", str(td / "pilot"), out="devam")
    k("--devam: yazilmis ilan ZATEN, yazim yok", durum(R, "9100000001")["durum"] == "ZATEN" and not api.yazimlar, durum(R, "9100000001"))
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000001", out="tekrar")
    k("bilinen FAIL: yazilmis ilan --devam'siz -> BLOK (canli != plan), yazim yok", durum(R, "9100000001")["durum"] == "BLOK" and not api.yazimlar)

    # sha tutmaz (yukleme sirasinda dosya degisti) -> DUR, eski silinmez; sonraki KALAN
    api = Sahte(L); api.dosya_boz = str(dd / "CANCER_CANCER_W05_SUREC.jpg")
    rc, R = kos(api, td, P, *YAZ, "--sadece", "9100000002,9100000003", out="sha")
    s = durum(R, "9100000002")
    k("bilinen FAIL: yukleme sonrasi sha256 tutmaz -> DUR, eski W05 SILINMEDI (otomatik kurtarma yok)",
      s["durum"] == "DUR" and "sha256" in s["neden"][0] and 2005 in ids(L["9100000002"]) and [w[0] for w in api.yazimlar] == ["upload"], s)
    k("DUR sonrasi sonraki ilan KALAN, yazim yok", durum(R, "9100000003")["durum"] == "KALAN" and len(api.yazimlar) == 1)
    k("DUR: ARA kaydi (yeni id + eski id)", json.loads((td / "sha" / "ilanlar" / "ARA_9100000002.json").read_text())["eski_id"] == 2005)

    # alt metin farkli -> DUR
    api = Sahte(L); api.alt_bozuk = True
    rc, R = kos(api, td, P, *YAZ, "--sadece", "9100000003", out="alt")
    s = durum(R, "9100000003")
    k("bilinen FAIL: alt_text farkli -> DUR, eski silinmedi", s["durum"] == "DUR" and "alt metni" in s["neden"][0] and 3005 in ids(L["9100000003"])
      and [w[0] for w in api.yazimlar] == ["upload"], s)

# ---------- rank, silme kapisi, canli != plan, kimlik, kurtar, kota
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, rc = kur(td)
    os.environ[W.KILIT_ORTAM] = "1"
    YAZ = ["--confirm", W.ONAY, "--dosya-dir", str(dd)]
    api = Sahte(L); api.rank_yok = True
    rc, R = kos(api, td, P, *YAZ, "--sadece", "9100000001", out="rank")
    s = durum(R, "9100000001")
    k("bilinen FAIL: yukleme rank 5'e oturmadi -> DUR, eski silinmedi", s["durum"] == "DUR" and 1005 in ids(L["9100000001"])
      and [w[0] for w in api.yazimlar] == ["upload"], s)
    # silme kapisi: yeni yuklenmeden silme denemesi
    api = Sahte(L); gd = P["girdiler"]["9100000002"]
    try:
        W.sil_guvenli(api, SHOP, "9100000002", gd, None, G.galeri(api, "9100000002")); h = None
    except W.Hata as e:
        h = str(e)
    k("bilinen FAIL: eski W05 yeni yuklenmeden silinmeye calisildi -> FAIL, silme yok", h and "silme kapisi" in h and not api.yazimlar, h)
    try:
        W.sil_guvenli(api, SHOP, "9100000002", gd, 123, G.galeri(api, "9100000002")); h = None
    except W.Hata as e:
        h = str(e)
    k("bilinen FAIL: yeni kimlik galeride rank 5'te degil -> silme yok", h and not api.yazimlar, h)
    # canli != plan
    L["9100000002"]["images"][0]["alt_text"] = "degisti"
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000002", out="fark")
    k("bilinen FAIL: canli galeri plandan farkli -> BLOK, yazim yok", durum(R, "9100000002")["durum"] == "BLOK" and not api.yazimlar)
    # canli r5 kimligi farkli
    x = L["9100000003"]["images"]; r5 = next(i for i in x if i["rank"] == 5); r5["listing_image_id"] = 3999
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000003", out="kim")
    k("bilinen FAIL: canli r5 kimligi plandan farkli -> BLOK, yazim yok", durum(R, "9100000003")["durum"] == "BLOK" and not api.yazimlar)
    # silme hatasi -> YARIM -> kurtar
    api = Sahte(L); api.sil_hata = True
    rc, R = kos(api, td, P, *YAZ, "--sadece", "9100000004", out="yarim")
    s = durum(R, "9100000004")
    k("silme hatasi -> DUR (YARIM: yeni rank 5, eski rank 6), otomatik kurtarma yok", s["durum"] == "DUR" and 4005 in ids(L["9100000004"])
      and len(ids(L["9100000004"])) == 12, s)
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000004", out="yarim2")
    k("bilinen FAIL: YARIM ilan --kurtar'siz -> BLOK, yazim yok", durum(R, "9100000004")["durum"] == "BLOK" and not api.yazimlar)
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000004", "--kurtar", "--onceki", str(td / "yarim"), out="kurtar")
    k(f"--kurtar: istek {durum(R, '9100000004')['istek']} = kurtar en az {t['kurtar_en_az']}", durum(R, "9100000004")["istek"] == t["kurtar_en_az"])
    k("--kurtar: YARIM ilan -> silme + bag yazimi, PASS, galeri 11 (eski W05 yerine yeni)", durum(R, "9100000004")["durum"] == "PASS"
      and [w[0] for w in api.yazimlar] == ["sil", "bag"] and len(ids(L["9100000004"])) == 11 and 4005 not in ids(L["9100000004"]),
      (R["ilanlar"], api.yazimlar))
    # Etsy silmeden sonra rank sikistirmaz -> yine PASS (sira kontrolu)
    L3, dd3, P3, _ = kur(td / "s")
    api = Sahte(L3); api.sikistirmaz = True
    rc, R = kos(api, td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000001", out="sik")
    s = durum(R, "9100000001")
    k("silme sonrasi rank sikistirilmaz (5 bos) -> PASS, sira dogru", s["durum"] == "PASS"
      and [i["rank"] for i in sorted(L3["9100000001"]["images"], key=lambda i: i["rank"])][4:6] == [5, 7], (s, L3["9100000001"]["images"][:2]))
    rc, R = kos(api := Sahte(L3), td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000001", "--devam",
                "--onceki", str(td / "s" / "sik"), out="sik2")
    k("rank bosluklu ilan --devam -> ZATEN, yazim yok", durum(R, "9100000001")["durum"] == "ZATEN" and not api.yazimlar)
    # yukleme renk baglarini dusurur -> fark kaydedilir, silme surer, baglar plandaki haliyle yeniden yazilir (Serdar 6 Kas)
    bag0 = copy.deepcopy(L3["9100000002"]["var"])
    api = Sahte(L3); api.bag_dus = True
    rc, R = kos(api, td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000002", out="bag")
    s = durum(R, "9100000002")
    k("bag_dus: PASS, baglar plana esit, eski W05 silindi, yazim upload + sil + bag", s["durum"] == "PASS"
      and W.bag_imza(L3["9100000002"]["var"]) == W.bag_imza(bag0) and 2005 not in ids(L3["9100000002"])
      and [w[0] for w in api.yazimlar] == ["upload", "sil", "bag"], (s, api.yazimlar))
    k("bag_dus: SONRA kaydinda yukleme sonrasi bag farki", json.loads((td / "s" / "bag" / "ilanlar" / "SONRA_9100000002.json").read_text())
      .get("bag_farki_yukleme_sonrasi"))
    # bag yeniden yazim geri okumasi tutmaz -> DUR + TANI
    api = Sahte(L3); api.bag_dus = True; api.bag_post_yok = True
    rc, R = kos(api, td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000004", out="bagyok")
    s = durum(R, "9100000004"); tani = td / "s" / "bagyok" / "ilanlar" / "TANI_9100000004.json"
    k("bilinen FAIL: bag yazimi geri okumasi plana esit degil -> DUR + TANI (canli galeri + baglar)", s["durum"] == "DUR"
      and "bag yeniden yazimi" in s["neden"][0] and tani.exists() and "canli_baglar" in json.loads(tani.read_text()), (s, tani.exists()))
    api = Sahte(L3); api.boyut_boz = True
    rc, R = kos(api, td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000003", out="boyut")
    s = durum(R, "9100000003")
    k("bilinen FAIL: yeni gorsel 3000x2250 degil -> DUR, silme yok", s["durum"] == "DUR" and "boyutu" in s["neden"][0]
      and [w[0] for w in api.yazimlar] == ["upload"], s)
    # --kurtar boyut kapisi: boyut bozuk yukleme sonrasi DUR (YARIM), --kurtar da silmez
    rc, R = kos(api := Sahte(L3), td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000003", "--kurtar",
                "--onceki", str(td / "s" / "boyut"), out="kurtarboyut")
    s = durum(R, "9100000003")
    k("bilinen FAIL: --kurtar yeni gorsel boyutu 3000x2250 degil -> DUR, eski W05 silinmedi", s["durum"] == "DUR"
      and not [w for w in api.yazimlar if w[0] == "sil"] and 3005 in ids(L3["9100000003"]), (s, api.yazimlar))
    L6, dd6, P6, _ = kur(td / "b6")
    api = Sahte(L6); api.boyut_yok = True
    rc, R = kos(api, td / "b6", P6, "--confirm", W.ONAY, "--dosya-dir", str(dd6), "--sadece", "9100000001", out="boyutyok")
    s = durum(R, "9100000001")
    k("bilinen FAIL: yeni gorsel boyutu okunamadi -> DUR, eski W05 silinmedi", s["durum"] == "DUR" and "boyutu" in s["neden"][0]
      and [w[0] for w in api.yazimlar] == ["upload"] and 1005 in ids(L6["9100000001"]), s)
    k("DUR: TANI hata anindaki durumu tasir (bag_farki alani var)", "bag_farki_yukleme_sonrasi" in json.loads(
      (td / "b6" / "boyutyok" / "ilanlar" / "TANI_9100000001.json").read_text()))
    # kayma tutmaz + bag dusmus -> baglar yeniden yazilir, sonra DUR (eski silinmez)
    L5, dd5, P5, _ = kur(td / "r")
    bag0 = copy.deepcopy(L5["9100000001"]["var"])
    api = Sahte(L5); api.rank_yok = True; api.bag_dus = True
    rc, R = kos(api, td / "r", P5, "--confirm", W.ONAY, "--dosya-dir", str(dd5), "--sadece", "9100000001", out="rankbag")
    s = durum(R, "9100000001")
    tani = json.loads((td / "r" / "rankbag" / "ilanlar" / "TANI_9100000001.json").read_text())
    k("TANI hata anindaki durum: onarim oncesi canli baglar bos, bag_onarimi notu, bag farki 'olculmedi'",
      tani.get("canli_baglar") == [] and tani.get("bag_onarimi") and tani.get("bag_farki_yukleme_sonrasi") == "olculmedi", tani)
    k("bilinen FAIL: kayma tutmaz + bag dusmus -> bag yeniden yazildi, sonra DUR, eski W05 silinmedi, TANI", s["durum"] == "DUR"
      and W.bag_imza(L5["9100000001"]["var"]) == W.bag_imza(bag0) and 1005 in ids(L5["9100000001"])
      and [w[0] for w in api.yazimlar] == ["upload", "bag"] and (td / "r" / "rankbag" / "ilanlar" / "TANI_9100000001.json").exists(),
      (s, api.yazimlar))
    # geri al: TANI'dan cikan tek aday (ARA yok) -> yeni id silinir, galeri plan haline doner
    rc, R = kos(api := Sahte(L5), td / "r", P5, "--confirm", W.ONAY, "--sadece", "9100000001", "--geri-al", out="geri")
    s = durum(R, "9100000001")
    k("--geri-al: eski W05 duruyor, tek aday -> yalniz yeni id silindi, sira = plan (GERI_ALINDI)", s["durum"] == "GERI_ALINDI"
      and [w[0] for w in api.yazimlar] == ["sil"] and ids(L5["9100000001"]) == [i for _, i, _ in P5["girdiler"]["9100000001"]["galeri"]],
      (s, api.yazimlar))
    k(f"--geri-al: istek {s['istek']} = geri al en az {t['geri_en_az']}", s["istek"] == t["geri_en_az"], s["istek"])
    # geri al: plan disi tek aday ama alt metni eski W05 metni degil (elle eklenmis baska gorsel) + baglar dusmus -> DUR, silme yok,
    # yalniz bag onarimi (gorev: "ayni akis geri al yolunda")
    L5["9100000004"]["images"].append(dict(listing_image_id=41, rank=12, alt_text="elle eklenen", url_fullxfull="u"))
    bag4 = copy.deepcopy(L5["9100000004"]["var"]); L5["9100000004"]["var"] = []
    rc, R = kos(api := Sahte(L5), td / "r", P5, "--confirm", W.ONAY, "--sadece", "9100000004", "--geri-al", out="geri4")
    s = durum(R, "9100000004")
    k("bilinen FAIL: --geri-al aday alt metni eski W05 degil -> DUR, silme yok, yalniz bag onarimi", s["durum"] == "DUR"
      and [w[0] for w in api.yazimlar] == ["bag"] and "alt metni" in s["neden"][0] and W.bag_imza(L5["9100000004"]["var"]) == W.bag_imza(bag4), s)
    L5["9100000004"]["images"] = [i for i in L5["9100000004"]["images"] if i["listing_image_id"] != 41]
    # geri al: eski W05 yok (PASS sonrasi) -> DUR, silme yok
    rc, R = kos(api := Sahte(L5), td / "r", P5, "--confirm", W.ONAY, "--dosya-dir", str(dd5), "--sadece", "9100000002", out="ok2")
    rc, R = kos(api := Sahte(L5), td / "r", P5, "--confirm", W.ONAY, "--sadece", "9100000002", "--geri-al", "--onceki", str(td / "r" / "ok2"),
                out="geri2")
    s = durum(R, "9100000002")
    k("bilinen FAIL: --geri-al eski W05 galeride yok -> DUR, silme yok", s["durum"] == "DUR" and not api.yazimlar and "eski W05" in s["neden"][0], s)
    # geri al: plan disi iki kimlik, ARA yok -> DUR
    L5["9100000003"]["images"] += [dict(listing_image_id=31, rank=12, alt_text="x", url_fullxfull="u"),
                                   dict(listing_image_id=32, rank=13, alt_text="y", url_fullxfull="u")]
    rc, R = kos(api := Sahte(L5), td / "r", P5, "--confirm", W.ONAY, "--sadece", "9100000003", "--geri-al", out="geri3")
    s = durum(R, "9100000003")
    k("bilinen FAIL: --geri-al TANI'da birden fazla aday kimlik -> DUR (yalniz elle), silme yok", s["durum"] == "DUR" and not api.yazimlar
      and "tek degil" in s["neden"][0], s)
    # belirsiz yukleme (500, gorsel olusmadi) -> DUR + TANI, ARA yok
    api = Sahte(L5); api.yukleme_hata = True
    rc, R = kos(api, td / "r", P5, "--confirm", W.ONAY, "--dosya-dir", str(dd5), "--sadece", "9100000004", out="belirsiz")
    s = durum(R, "9100000004"); io_ = td / "r" / "belirsiz" / "ilanlar"
    k("bilinen FAIL: belirsiz yukleme -> DUR, TANI yazildi, ARA yok, yazim yok", s["durum"] == "DUR" and (io_ / "TANI_9100000004.json").exists()
      and not (io_ / "ARA_9100000004.json").exists() and not api.yazimlar, (s, api.yazimlar))
    # kalan kota ilk istege kadar bilinmiyor (gercek istemci): dusuk kalan -> 3 GET sonra KALAN, yukleme yok
    L4, dd4, P4, _ = kur(td / "n")
    api = Sahte(L4, kalan=t["yaz_en_kotu"] + 9, bilinmiyor=True)
    rc, R = kos(api, td / "n", P4, "--confirm", W.ONAY, "--dosya-dir", str(dd4), "--sadece", "9100000001", out="bilinmiyor")
    k("bilinen FAIL: ilk ilanda kalan bilinmiyor + dusuk -> okuma sonrasi KALAN, yukleme yok (inceleme 6 Kas YUKSEK 1)",
      durum(R, "9100000001")["durum"] == "KALAN" and not api.yazimlar and api.calls == W.OKUMA, (R["ilanlar"], api.calls))
    rc, R = kos(api := Sahte(L4, bilinmiyor=True), td / "n", P4, "--confirm", W.ONAY, "--dosya-dir", str(dd4), "--sadece", "9100000001", out="bilinmiyor2")
    k("ilk ilanda kalan bilinmiyor + yeterli -> PASS", durum(R, "9100000001")["durum"] == "PASS")
    # kota
    L2, dd2, P2, _ = kur(td / "k")
    rc, R = kos(api := Sahte(L2, kalan=t["yaz_en_kotu"] + 9), td / "k", P2, "--confirm", W.ONAY, "--dosya-dir", str(dd2), "--sadece", "9100000001", out="kota")
    k("bilinen FAIL: kota < en kotu + 10 -> KALAN, istek yok", durum(R, "9100000001")["durum"] == "KALAN" and api.calls == 0 and not api.yazimlar)
    try:
        W.plan_yukle(td / "plan" / W.PLAN_AD, P["plan_damga"][:-1] + "0"); h = None
    except SystemExit as e:
        h = str(e)
    k("bilinen FAIL: plan_damga bozuk -> DUR", h and "DUR" in h, h)

print(f"SONUC: {sum(SONUC)}/{len(SONUC)} PASS")
sys.exit(0 if all(SONUC) else 1)
