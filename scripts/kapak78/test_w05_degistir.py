#!/usr/bin/env python3
"""w05_degistir.py yerel testi. Ag / Drive / Etsy / token YOK: sahte Etsy (bellekte galeri, renk baglari) + sentetik ilanlar
(9100000001..4) + sentetik JPEG. Bilinen PASS ve bilinen FAIL:
  plan: PLAN; W05'e renk bagi -> BLOK; MANIFEST kimlik zinciri FAIL -> BLOK; galeri 20 -> BLOK; plan_damga bozuk -> DUR.
  kuru: HAZIR, yazim yok, istek 3. Yazim: kilit yok / --sadece yok / onay yok -> DUR (yazim yok).
  pilot: PASS (rank 5 yeni, alt metin = eski W05, eski silindi, digerleri ayni, baglar ayni, istek = en az tahmini, diger ilan dokunulmaz).
  yukleme sonrasi sha tutmaz -> DUR, eski W05 SILINMEZ; alt metin farkli -> DUR, eski silinmez; yukleme rank 5'e oturmaz -> DUR, silinmez;
  yeni gorsel yokken silme denemesi -> FAIL (silme yok); canli != plan -> BLOK; canli r5 kimligi plandan farkli -> BLOK;
  silme hatasi -> DUR (YARIM, ARA kaydi) -> --kurtar -> PASS; --devam -> ZATEN (yazim yok); DUR sonrasi sonraki ilan KALAN; kota -> KALAN.
  Secenek 2 (Merkez / Serdar 6 Kas): sahte yukleme VARSAYILANI kaydirma yok, esit rank (6 Kas canli olcum 4570143815); kaydir (KAYMA),
  karisik (esit rank'lar her okumada farkli API sirasinda), ters (yeni 6, eski 5), fazla (yuklemede yabanci gorsel), sil_karistir
  (silme sonrasi sira bozulur). ESIT / KAYMA / karisik / sikismamis PASS; ters / fazla / sira bozuk DUR; id ile silme; --kurtar ESIT
  ve KAYMA; geri al ESIT; canli W05 bagli / rank ardisik degil / rank 5'te iki gorsel BLOK; main --kuru salt_okur (yazma yok).
  Inceleme 6 Kas: ZATEN + bag farki / draft BLOK; boyut gec dolar -> stabil yeniden, PASS; geri al KAYMA sikismamis UYARI; kuru --kurtar
  YARIM; kurtar kota KALAN. Dosyanin tamami W05_TEST_KAYDIR=1 (sahte yukleme varsayilani KAYMA) ile ikinci kez kosar (ESIT'e ozel
  testler kaydir=False'u acik verir).
Kullanim: python3 scripts/kapak78/test_w05_degistir.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import copy
import csv
import subprocess
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
KAYDIR0 = os.environ.get("W05_TEST_KAYDIR") == "1"   # ikinci gecis: sahte yukleme varsayilani KAYMA
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
    kota ilk istege kadar None: gercek etsy_common).
    Yukleme rank'i (Etsy OpenAPI uploadListingImage "rank" kaydirma vaat etmiyor; 6 Kas canli: eski ve yeni rank 5): VARSAYILAN esit rank,
    kaydirma yok. kaydir: rank >= verilen gorseller +1 (KAYMA). ters: yeni rank+1'e, ondan sonrakiler +1 (eski 5'te kalir).
    karisik: getListingImages esit rank'lari her okumada ters API sirasinda dondurur. fazla: yuklemede yabanci bir gorsel daha eklenir.
    sil_karistir: silmeden sonra rank 1 ve 2 yer degistirir (sira bozuk)."""
    def __init__(self, L, kalan=5000, bilinmiyor=False):
        self.L, self.calls, self._kalan, self.yazimlar, self._n = L, 0, kalan, [], 7_000_000
        self.remaining = None if bilinmiyor else kalan
        self.rank_yok = self.alt_bozuk = self.sil_hata = self.sikistirmaz = self.bag_dus = self.boyut_boz = False; self.dosya_boz = None
        self.bag_post_yok = self.yukleme_hata = self.boyut_yok = False   # bag POST'u yok sayilir / yukleme 500 ve gorsel olusmaz (belirsiz yukleme)
        self.kaydir = KAYDIR0; self.karisik = self.ters = self.fazla = self.sil_karistir = False; self._ters_okuma = False
        self.boyut_gec = 0; self._gec = None   # boyut_gec: yeni gorselin boyutu ilk N galeri okumasinda bos

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
            if self._gec and self._gec[0] == self._lid(path):
                self._gec[2] -= 1
                if self._gec[2] < 0:
                    for i in x["images"]:
                        if i["listing_image_id"] == self._gec[1]:
                            i.update(full_width=3000, full_height=2250)
                    self._gec = None
            self._ters_okuma = not self._ters_okuma
            yon = -1 if (self.karisik and self._ters_okuma) else 1
            return {"results": copy.deepcopy(sorted(x["images"], key=lambda i: (i["rank"], yon * i["listing_image_id"])))}
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
        if self.ters:
            rank += 1
        if self.kaydir or self.ters:
            for i in x["images"]:
                if i["rank"] >= rank:
                    i["rank"] += 1
        alt = (data or {}).get("alt_text") + (" X" if self.alt_bozuk else "")
        x["images"].append(dict(listing_image_id=yid, rank=min(rank, n + 1), alt_text=alt, url_fullxfull=f"u/{yid}",
                                **({} if (self.boyut_yok or self.boyut_gec) else dict(full_width=1500 if self.boyut_boz else 3000,
                                                                                       full_height=1125 if self.boyut_boz else 2250))))
        if self.boyut_gec:
            self._gec = [lid, yid, self.boyut_gec]
        if self.fazla:
            x["images"].append(dict(listing_image_id=self._n + 500, rank=n + 2, alt_text="yabanci", url_fullxfull="u",
                                    full_width=3000, full_height=2250))
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
        if self.sil_karistir:
            g = sorted(x["images"], key=lambda i: i["rank"]); g[0]["rank"], g[1]["rank"] = g[1]["rank"], g[0]["rank"]
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
k(f"istek tahmini: kuru 3, en az 16, en kotu {t['yaz_en_kotu']} (O={t['okuma_tekrar']}; boyut + yeniden stabil, bag yazimi + onarim + TANI 2), "
  "kota = en kotu + 10", t["kuru"] == 3 and t["yaz_en_az"] == 16 and t["yaz_en_kotu"] == 98 and t["kurtar_en_kotu"] == 77
  and t["kota_ihtiyac"] == t["yaz_en_kotu"] + 10)

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
    api = Sahte(L); api.sil_hata = True; api.kaydir = False
    rc, R = kos(api, td, P, *YAZ, "--sadece", "9100000004", out="yarim")
    s = durum(R, "9100000004")
    r5 = sorted(i["listing_image_id"] for i in L["9100000004"]["images"] if i["rank"] == 5)
    k("silme hatasi -> DUR (YARIM ESIT: yeni ve eski rank 5, ARA yukleme ESIT), otomatik kurtarma yok", s["durum"] == "DUR"
      and r5 == sorted([4005, s["yeni_id"]]) and len(ids(L["9100000004"])) == 12
      and json.loads((td / "yarim" / "ilanlar" / "ARA_9100000004.json").read_text()).get("yukleme") == "ESIT", (s, r5))
    rc, R = kos(api := Sahte(L), td, P, "--kuru", "--dosya-dir", str(dd), "--sadece", "9100000004", "--kurtar", "--onceki", str(td / "yarim"),
                out="yarimkuru")
    k("kuru --kurtar YARIM ESIT -> YARIM, yazim yok", durum(R, "9100000004")["durum"] == "YARIM" and not api.yazimlar, R["ilanlar"])
    rc, R = kos(api := Sahte(L, kalan=t["kurtar_en_kotu"] + 9), td, P, *YAZ, "--sadece", "9100000004", "--kurtar", "--onceki",
                str(td / "yarim"), out="kurtarkota")
    k("bilinen FAIL: --kurtar kota < kurtar en kotu + 10 -> KALAN, istek yok", durum(R, "9100000004")["durum"] == "KALAN"
      and api.calls == 0 and not api.yazimlar)
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000004", out="yarim2")
    k("bilinen FAIL: YARIM ilan --kurtar'siz -> BLOK, yazim yok", durum(R, "9100000004")["durum"] == "BLOK" and not api.yazimlar)
    rc, R = kos(api := Sahte(L), td, P, *YAZ, "--sadece", "9100000004", "--kurtar", "--onceki", str(td / "yarim"), out="kurtar")
    k(f"--kurtar: istek {durum(R, '9100000004')['istek']} = kurtar en az {t['kurtar_en_az']}", durum(R, "9100000004")["istek"] == t["kurtar_en_az"])
    k("--kurtar: YARIM ilan -> silme + bag yazimi, PASS, galeri 11 (eski W05 yerine yeni)", durum(R, "9100000004")["durum"] == "PASS"
      and [w[0] for w in api.yazimlar] == ["sil", "bag"] and len(ids(L["9100000004"])) == 11 and 4005 not in ids(L["9100000004"]),
      (R["ilanlar"], api.yazimlar))
    # Etsy silmeden sonra rank sikistirmaz -> yine PASS (sira kontrolu; KAYMA + sikismamis 1..5,7..12, Merkez 6 Kas karar 1)
    L3, dd3, P3, _ = kur(td / "s")
    api = Sahte(L3); api.sikistirmaz = True; api.kaydir = True
    rc, R = kos(api, td / "s", P3, "--confirm", W.ONAY, "--dosya-dir", str(dd3), "--sadece", "9100000001", out="sik")
    s = durum(R, "9100000001")
    k("silme sonrasi rank sikistirilmaz (KAYMA, 6 bos) -> PASS, sira dogru", s["durum"] == "PASS"
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

# ---------- Secenek 2 (Merkez / Serdar 6 Kas): ESIT, KAYMA, karisik, ters, fazla, sira bozuk, id ile silme, kurtar, geri al, canli kapilar
os.environ[W.KILIT_ORTAM] = "1"


def taze(td, ad):
    L, dd, P, _ = kur(td / ad)
    return L, dd, P, (lambda api, lid, out, *ek: kos(api, td / ad, P, "--confirm", W.ONAY, "--dosya-dir", str(dd), "--sadece", lid, *ek, out=out))


def ara(td, ad, out, lid):
    return json.loads((td / ad / out / "ilanlar" / f"ARA_{lid}.json").read_text())


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, yaz = taze(td, "e")
    once = {lid: ids(L[lid]) for lid, _ in ILAN}
    api = Sahte(L); api.kaydir = False
    rc, R = yaz(api, "9100000001", "esit"); s = durum(R, "9100000001"); yid = s["yeni_id"]
    k("ESIT (yeni ve eski rank 5, digerleri yerinde): PASS, ARA yukleme ESIT, silinen = eski kimlik, sira = plan (5 = yeni), n gorsel",
      s["durum"] == "PASS" and ara(td, "e", "esit", "9100000001").get("yukleme") == "ESIT" and ("sil", "9100000001", 1005) in api.yazimlar
      and ids(L["9100000001"]) == [yid if i == 1005 else i for i in once["9100000001"]]
      and len(L["9100000001"]["images"]) == P["girdiler"]["9100000001"]["n"],
      (s, api.yazimlar))
    k(f"ESIT: istek {s['istek']} = en az {t['yaz_en_az']}", s["istek"] == t["yaz_en_az"], s["istek"])
    api = Sahte(L); api.kaydir = True
    rc, R = yaz(api, "9100000002", "kayma"); s = durum(R, "9100000002")
    k("KAYMA (yeni 5, eski 6, digerleri +1): PASS, ARA yukleme KAYMA, sira = plan", s["durum"] == "PASS"
      and ara(td, "e", "kayma", "9100000002").get("yukleme") == "KAYMA"
      and ids(L["9100000002"]) == [s["yeni_id"] if i == 2005 else i for i in once["9100000002"]], s)
    api = Sahte(L); api.karisik = True; api.kaydir = False
    rc, R = yaz(api, "9100000003", "karisik"); s = durum(R, "9100000003")
    k("karisik (esit rank'lar her okumada ters API sirasinda): PASS (stabil_w05 (rank, kimlik) sirali)", s["durum"] == "PASS"
      and ids(L["9100000003"]) == [s["yeni_id"] if i == 3005 else i for i in once["9100000003"]], s)
    # paylasilan stabil_galeri ayni durumda kararli olmaz (stabil_w05 neden gerekli; paylasilan fonksiyon DEGISMEDI)
    Lk = copy.deepcopy(L); Lk["9100000004"]["images"].append(dict(listing_image_id=4999, rank=5, alt_text="x", url_fullxfull="u"))
    ak = Sahte(Lk); ak.karisik = True
    try:
        Y.stabil_galeri(ak, "9100000004"); h = None
    except Y.Dur as e:
        h = str(e)
    g2 = W.stabil_w05(ak, "9100000004")
    k("bilinen FAIL (paylasilan): esit rank + karisik okumada stabil_galeri kararli degil; stabil_w05 kararli (rank, kimlik)",
      h and "kararli degil" in h and [x["listing_image_id"] for x in g2][4:6] == [4005, 4999], h)
    k("bir ilan yazildi, digerleri dokunulmadi", ids(L["9100000004"]) == once["9100000004"])

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, yaz = taze(td, "t")
    api = Sahte(L); api.ters = True
    rc, R = yaz(api, "9100000001", "ters"); s = durum(R, "9100000001")
    k("bilinen FAIL: ters sira (eski 5, yeni 6) -> DUR + TANI, silme yok", s["durum"] == "DUR" and "ESIT" in s["neden"][0]
      and [w[0] for w in api.yazimlar] == ["upload"] and 1005 in ids(L["9100000001"])
      and (td / "t" / "ters" / "ilanlar" / "TANI_9100000001.json").exists(), (s, api.yazimlar))
    api = Sahte(L); api.fazla = True
    rc, R = yaz(api, "9100000002", "fazla"); s = durum(R, "9100000002")
    k("bilinen FAIL: yuklemeden sonra fazla (yabanci) gorsel -> DUR, silme yok", s["durum"] == "DUR" and "plan disi" in s["neden"][0]
      and [w[0] for w in api.yazimlar] == ["upload"] and 2005 in ids(L["9100000002"]), (s, api.yazimlar))
    api = Sahte(L); api.sil_karistir = True
    rc, R = yaz(api, "9100000003", "sirabozuk"); s = durum(R, "9100000003")
    k("bilinen FAIL: silme sonrasi sira plan degil -> DUR + TANI", s["durum"] == "DUR" and "son geri okuma" in s["neden"][0]
      and (td / "t" / "sirabozuk" / "ilanlar" / "TANI_9100000003.json").exists(), s)
    # bir ilan DUR olunca digerleri etkilenmez (KALAN, yazim yok, galeri ayni)
    L2, dd2, P2, yaz2 = taze(td, "t2")
    o4 = ids(L2["9100000004"]); api = Sahte(L2); api.ters = True
    rc, R = kos(api, td / "t2", P2, "--confirm", W.ONAY, "--dosya-dir", str(dd2), "--sadece", "9100000001,9100000004", out="iki")
    k("bilinen FAIL: ilk ilan DUR -> ikinci ilan KALAN, ikinci ilana yazim yok, galerisi ayni", durum(R, "9100000001")["durum"] == "DUR"
      and durum(R, "9100000004")["durum"] == "KALAN" and all(w[1] != "9100000004" for w in api.yazimlar) and ids(L2["9100000004"]) == o4)

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, yaz = taze(td, "i")
    api = Sahte(L); api._n = 100   # yeni kimlik (101) eski W05'ten (1005) kucuk: (rank, kimlik) sirasinda yeni once gelir
    rc, R = yaz(api, "9100000001", "kucuk"); s = durum(R, "9100000001")
    k("ayni alt metinli iki kart (yeni kimlik < eski): id ile dogru silme (eski 1005 silindi, yeni 101 rank 5)", s["durum"] == "PASS"
      and s["yeni_id"] == 101 and [w for w in api.yazimlar if w[0] == "sil"] == [("sil", "9100000001", 1005)]
      and ids(L["9100000001"])[4] == 101, (s, api.yazimlar))
    # --kurtar: KAYMA YARIM
    api = Sahte(L); api.kaydir = True; api.sil_hata = True
    rc, R = yaz(api, "9100000002", "ykayma")
    k("silme hatasi (KAYMA) -> DUR, YARIM", durum(R, "9100000002")["durum"] == "DUR" and len(ids(L["9100000002"])) == 12)
    rc, R = yaz(api := Sahte(L), "9100000002", "kkayma", "--kurtar", "--onceki", str(td / "i" / "ykayma"))
    k("--kurtar YARIM KAYMA -> PASS (silme + bag), n gorsel", durum(R, "9100000002")["durum"] == "PASS"
      and [w[0] for w in api.yazimlar] == ["sil", "bag"] and 2005 not in ids(L["9100000002"]) and len(ids(L["9100000002"])) == 11,
      (R["ilanlar"], api.yazimlar))
    # geri al ESIT durumdan
    api = Sahte(L); api.sil_hata = True; api.kaydir = False
    rc, R = yaz(api, "9100000003", "yesit"); yid3 = durum(R, "9100000003")["yeni_id"]
    rc, R = kos(api := Sahte(L), td / "i", P, "--confirm", W.ONAY, "--sadece", "9100000003", "--geri-al", "--onceki", str(td / "i" / "yesit"),
                out="gesit")
    s = durum(R, "9100000003")
    k("--geri-al ESIT durumdan -> GERI_ALINDI: yalniz yeni kimlik silindi, sira = plan, eski W05 rank 5", s["durum"] == "GERI_ALINDI"
      and api.yazimlar == [("sil", "9100000003", yid3)] and ids(L["9100000003"]) == [i for _, i, _ in P["girdiler"]["9100000003"]["galeri"]],
      (s, api.yazimlar))
    # canli kapilar (yazim oncesi): W05 bagli, rank ardisik degil, rank 5'te iki gorsel
    L["9100000004"]["var"].append(dict(property_id=200, value_id=99, image_id=4005))
    rc, R = yaz(api := Sahte(L), "9100000004", "w05bag"); s = durum(R, "9100000004")
    k("bilinen FAIL: canli W05 renge bagli -> BLOK, yazim yok", s["durum"] == "BLOK" and any("W05'e renk bagi" in n for n in s["neden"])
      and not api.yazimlar, s)
    L["9100000004"]["var"] = [b for b in L["9100000004"]["var"] if b["image_id"] != 4005]
    for i in L["9100000004"]["images"]:
        if i["rank"] >= 6:
            i["rank"] += 1
    rc, R = yaz(api := Sahte(L), "9100000004", "bosluk"); s = durum(R, "9100000004")
    k("bilinen FAIL: canli rank'lar 1..n ardisik degil (sira ayni) -> BLOK, yazim yok", s["durum"] == "BLOK"
      and any("ardisik degil" in n for n in s["neden"]) and not api.yazimlar, s)
    for i in L["9100000004"]["images"]:
        if i["rank"] >= 7:
            i["rank"] -= 1
    L["9100000004"]["images"].append(dict(listing_image_id=4999, rank=5, alt_text="x", url_fullxfull="u"))
    rc, R = yaz(api := Sahte(L), "9100000004", "iki5"); s = durum(R, "9100000004")
    k("bilinen FAIL: canli rank 5'te iki gorsel -> BLOK, yazim yok", s["durum"] == "BLOK" and any("rank 5'te tek" in n for n in s["neden"])
      and not api.yazimlar, s)

# ---------- main() --kuru: salt_okur devrede, yazma yontemleri cagrilamaz (gercek giris noktasi, sahte istemci)
import etsy_common as EC  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    LM, ddm, PM, _ = kur(td / "m")

    class SahteEtsy(Sahte):
        son = None

        def __init__(self, st):
            super().__init__(LM); SahteEtsy.son = self

    class SahteTS:
        def __init__(self, *a, **kw):
            pass

        def needs_refresh(self):
            return False

    asil = (EC.Etsy, EC.TokenStore, EC.mask); ortam = {x: os.environ.get(x) for x in ("TOKEN_FILE", "ETSY_SHOP_ID")}
    EC.Etsy, EC.TokenStore, EC.mask = SahteEtsy, SahteTS, (lambda *a: None)
    os.environ["TOKEN_FILE"], os.environ["ETSY_SHOP_ID"] = "yok.json", SHOP
    try:
        rc = W.main(["etsy", "--plan", str(td / "m" / "plan" / W.PLAN_AD), "--plan-damga", PM["plan_damga"], "--out", str(td / "m" / "o"),
                     "--kuru", "--dosya-dir", str(ddm), "--sadece", "9100000001"])
        api = SahteEtsy.son; Rm = json.loads((td / "m" / "o" / "RAPOR.json").read_text())
        engel = []
        for ad, cagri in (("post_file", lambda: api.post_file("/shops/1/listings/9100000001/images", files={})),
                          ("delete", lambda: api.delete("/shops/1/listings/9100000001/images/1005", ok404=True)),
                          ("post_json", lambda: api.post_json("/shops/1/listings/9100000001/variation-images", {})),
                          ("put", lambda: api.put("/x")), ("patch", lambda: api.patch("/x")), ("post", lambda: api.post("/x")),
                          ("put_json", lambda: api.put_json("/x", {})), ("_call POST", lambda: api._call("POST", "/listings/9100000001"))):
            try:
                cagri(); engel.append((ad, False))
            except SystemExit as e:
                engel.append((ad, "salt okuma" in str(e)))
        k("main --kuru: salt_okur devrede (8 yazma yolu SystemExit), HAZIR, yazim 0, istek 3", rc == 0 and Rm["sayilar"] == {"HAZIR": 1}
          and not api.yazimlar and api.calls == W.OKUMA and all(v for _, v in engel), (rc, Rm["sayilar"], engel, api.yazimlar))
    finally:
        EC.Etsy, EC.TokenStore, EC.mask = asil
        for x, v in ortam.items():
            os.environ.pop(x, None) if v is None else os.environ.__setitem__(x, v)

# ---------- inceleme 6 Kas: ZATEN + bag / state, boyut gec, geri al KAYMA sikismamis
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    L, dd, P, yaz = taze(td, "z")
    rc, R = yaz(api := Sahte(L), "9100000001", "ok1")
    L["9100000001"]["var"] = []
    rc, R = yaz(api := Sahte(L), "9100000001", "zb", "--devam", "--onceki", str(td / "z" / "ok1"))
    s = durum(R, "9100000001")
    k("bilinen FAIL: galeri yazilmis ama baglar bos -> --devam ZATEN degil BLOK, rc 1, yazim yok", s["durum"] == "BLOK" and rc == 1
      and "baglar" in s["neden"][0] and not api.yazimlar, s)
    rc, R = yaz(api := Sahte(L), "9100000001", "zk", "--kurtar", "--onceki", str(td / "z" / "ok1"))
    k("bilinen FAIL: ayni durumda --kurtar -> BLOK, yazim yok", durum(R, "9100000001")["durum"] == "BLOK" and not api.yazimlar)
    rc, R = yaz(api := Sahte(L), "9100000002", "ok2"); L["9100000002"]["state"] = "draft"
    rc, R = yaz(api := Sahte(L), "9100000002", "zd", "--devam", "--onceki", str(td / "z" / "ok2"))
    k("bilinen FAIL: galeri yazilmis ama state draft -> --devam BLOK", durum(R, "9100000002")["durum"] == "BLOK" and rc == 1 and not api.yazimlar)
    api = Sahte(L); api.boyut_gec = 4   # gorunur 1 + stabil 2 + bekleme 1 okumada bos
    rc, R = yaz(api, "9100000003", "gec"); s = durum(R, "9100000003")
    k("boyut gec dolar -> boyut bekleme + stabil_w05 yeniden, PASS, istek > en az", s["durum"] == "PASS" and s["istek"] > t["yaz_en_az"]
      and s["istek"] <= t["yaz_en_kotu"], s)
    api = Sahte(L); api.kaydir = True; api.sikistirmaz = True; api.sil_hata = True
    rc, R = yaz(api, "9100000004", "gk")
    api = Sahte(L); api.sikistirmaz = True
    rc, R = kos(api, td / "z", P, "--confirm", W.ONAY, "--sadece", "9100000004", "--geri-al", "--onceki", str(td / "z" / "gk"), out="gk2")
    s = durum(R, "9100000004")
    k("geri al KAYMA + sikismamis -> GERI_ALINDI, sira = plan, rank bosluklu UYARI notu", s["durum"] == "GERI_ALINDI"
      and ids(L["9100000004"]) == [i for _, i, _ in P["girdiler"]["9100000004"]["galeri"]] and any("UYARI" in n for n in s["neden"]), s)

# ---------- ikinci gecis: sahte yukleme varsayilani KAYMA (eski bloklar KAYMA ile de)
if not KAYDIR0:
    r2 = subprocess.run([sys.executable, __file__], env=dict(os.environ, W05_TEST_KAYDIR="1"), capture_output=True, text=True, timeout=900)
    son = (r2.stdout.strip().splitlines() or [""])[-1]
    k(f"tum testler sahte KAYMA varsayilaniyla da PASS ({son})", r2.returncode == 0,
      "\n".join(x for x in r2.stdout.splitlines() if x.startswith("FAIL"))[:600] or r2.stderr[-400:])

print(f"SONUC: {sum(SONUC)}/{len(SONUC)} PASS")
sys.exit(0 if all(SONUC) else 1)
