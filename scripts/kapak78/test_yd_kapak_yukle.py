#!/usr/bin/env python3
"""YD kapak yukleyicisi yerel testi (plan v3 adim 8). Ag yok, Drive yok, Etsy yok: sahte Etsy (test_eski78_gorsel_yukle.Sahte'nin
Style 513 / Format 514 surumu), pilot HAM'in gercek yapisi (test_veri/HAM_4595350971.json: 13 gorsel, rank 2-13 alt metni bos,
Style bagi r9-r13, Botanical r12). Girdi yd_liste_uret.py liste ile uretilir.
Senaryolar: YD normal akis (kuru PLAN + plan_damga, yazim 13 -> 14 -> 13, yazim sirasi, alt metinler, baglar, eski kapak silindi);
yukleme hatasi sonrasi ikinci yukleme yok; son bag bos -> DUR + bag onarimi; bos alt metinli KORU (alt_text alani gonderilmez);
DEVAM -> ZATEN -> BLOK sirasi (yarim ilan BLOK'a dusmez, bitmis ilan ZATEN, kayitsiz yeni alt metin BLOK); cdn_yedek kilit altinda
cagrilmaz; durum esigi 13 (durum_dosyasi); BLOK turleri; kota kapisi; plan kilidi; en kotu istek 185 (+4 kapi okumasi)."""
import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy")); sys.path.insert(0, str(KOK / "scripts/kapak78")); sys.path.insert(0, str(KOK / "scripts/ops"))
import test_eski78_gorsel_yukle as T  # noqa: E402  (G.time.sleep etkisiz)
import eski78_gorsel_yukle as Y  # noqa: E402
import yd_liste_uret as L  # noqa: E402
import yd_kapak_yukle as K  # noqa: E402
import durum_dosyasi as DD  # noqa: E402

HAM = json.loads((KOK / "scripts/kapak78/test_veri/HAM_4595350971.json").read_text())
LID, CIFT = "4595350971", "CANCER_LIBRA"
STIL_VID = {v["value"]: v["value_id"] for v in HAM["variation_images"]}
YENI_ALT = "Cancer and Libra 1st anniversary zodiac print, paper anniversary gift"
SONUC = []


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def cdn_yasak(u):
    raise AssertionError("cdn_indir cagrildi (kilit altinda indirme yok)")


Y.cdn_indir = cdn_yasak


class SahteYD(T.Sahte):
    """Style (513) baglari + Format (514); sira POST'unda alt_text yoksa alt metin degismez."""
    def __init__(self, kota=5000, state="active", ham=HAM):
        g = sorted(ham["images"], key=lambda x: x["rank"])
        super().__init__([(x["rank"], x["listing_image_id"]) for x in g], {}, kota=kota, state=state)
        for x, h in zip(self.img, g):
            x["alt_text"] = h["alt_text"]
        self.bag = {v["value"]: v["image_id"] for v in ham["variation_images"]}
        self.alt_yok = 0      # sira / kapak POST'larindan alt_text alani olmayanlar

    def get(self, path, params=None, ok404=False):
        if path.endswith("/variation-images"):
            self._k(); self.n_get += 1
            return {"results": [dict(property_id=513, value_id=STIL_VID[k], value=k, image_id=v) for k, v in self.bag.items()]}
        if path.endswith("/inventory"):
            self._k(); self.n_get += 1
            return copy.deepcopy(HAM["inventory"])
        return super().get(path, params, ok404)

    def post_file(self, path, files=None, data=None, tekrar=3):
        if "image" not in (files or {}) and "alt_text" not in files:
            self.alt_yok += 1
            x = next(y for y in self.img if y["listing_image_id"] == int(files["listing_image_id"][1]))
            f = dict(files, alt_text=(None, x["alt_text"]))   # Etsy varsayimi: alan yoksa alt metin degismez
            return super().post_file(path, files=f, data=data, tekrar=tekrar)
        return super().post_file(path, files=files, data=data, tekrar=tekrar)

    def post_json(self, path, body):
        self._k(); self.vi_cagri += 1; self.yaz.append(("bag",))
        if self.bag_yut:
            self.bag = {}; self._iz(); return {}
        vid = {v: k for k, v in STIL_VID.items()}
        self.bag = {vid[v["value_id"]]: v["image_id"] for v in body["variation_images"]}
        self._iz()


DEPO = Path(tempfile.mkdtemp(prefix="ydk_"))


def hazir_kur(ad="h", ham=HAM, kapak_boyut=(2400, 2400)):
    d = DEPO / ad
    for x in ("HAM", "kapak", "out"):
        (d / x).mkdir(parents=True, exist_ok=True)
    (d / "yd.csv").write_text(f"listing_id,cift,a,b\n{LID},{CIFT},Cancer,Libra\n")
    (d / "HAM" / f"{LID}.json").write_text(json.dumps(ham))
    Image.new("RGB", kapak_boyut, (40, 100, 50)).save(d / "kapak" / f"KAPAK_{CIFT}.jpg", "JPEG", quality=90)
    s = L.sha(d / "kapak" / f"KAPAK_{CIFT}.jpg")
    (d / "kapak" / "MANIFEST.csv").write_text(f"ad,cift,kart_no,design_id,boyut,sha256,durum\nKAPAK_{CIFT}.jpg,{CIFT},1,DAHZIAyOYA8,2400x2400,{s},YENI\n")
    (d / "QC.json").write_text(json.dumps(dict(esik=dict(poster_min=0.9, sahne_min=0.9), dosyalar=[dict(dosya=f"KAPAK_{CIFT}.jpg", durum="PASS")])))
    (d / "OZET.md").write_text(f"| {LID} | {CIFT} | 13 | PASS |  |\n")
    (d / "yl.json").write_text(json.dumps([dict(Path=f"{LID}_{CIFT}/r{g['rank']}_{g['listing_image_id']}.jpg", Size=9) for g in HAM["images"]]))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = L.main(["liste", "--ciftler", str(d / "yd.csv"), "--kaynak", str(KOK / "docs/yd_kapak/KAPAK_KAYNAK.csv"), "--ham-dir", str(d / "HAM"),
                     "--kapak-dir", str(d / "kapak"), "--qc", str(d / "QC.json"), "--yedek-ozet", str(d / "OZET.md"),
                     "--yedek-liste", str(d / "yl.json"), "--out", str(d / "hazir")])
    assert rc == 0
    return d / "hazir"


def arg(hazir, out, *ek):
    return K.arg(["--hazir", str(hazir), "--out", str(out), *ek])


def kuru(api, hazir, ad, devam=None, ilerleme=None):
    out = DEPO / ad
    ek = (["--devam", str(devam)] if devam else []) + (["--ilerleme", str(ilerleme)] if ilerleme else [])
    with contextlib.redirect_stdout(io.StringIO()):
        rc = K.sonlandir(api, "1", arg(hazir, out, "--kuru", "--kosu", "111", *ek))
    R = json.loads((out / "RAPOR.json").read_text())
    return rc, R, out


def yaz(api, hazir, plan_out, ad, damga, devam, ilerleme, *ek):
    out = DEPO / ad
    with contextlib.redirect_stdout(io.StringIO()):
        rc = K.sonlandir(api, "1", arg(hazir, out, "--confirm", "YD_KAPAK", "--plan", str(plan_out / "PLAN_YD.json"), "--plan-damga", damga,
                                       "--devam", str(devam), "--ilerleme", str(ilerleme), "--kosu", "222", *ek))
    return rc, json.loads((out / "RAPOR.json").read_text())


def durum_dosyalari(ad):
    d = DEPO / ad; d.mkdir(exist_ok=True)
    (d / "DEVAM.json").write_text('{"ilanlar": {}}'); (d / "ILERLEME.json").write_text('{"ilanlar": {}}')
    return d / "DEVAM.json", d / "ILERLEME.json"


def normal_akis():
    hz = hazir_kur()
    api = SahteYD()
    rc, R, po = kuru(api, hz, "k1")
    s = R["ilanlar"][0]
    kontrol("kuru: PLAN, yazma yok, plan_damga", rc == 0 and s["durum"] == "PLAN" and not api.yaz and R["plan_damga"].startswith("111_"))
    plan = json.loads((po / "PLAN_YD.json").read_text())["girdiler"][LID]
    kontrol("plan adimlari: yukle kapak -> kapak -> bag -> sil eski -> sira -> bag; en fazla 14",
            plan["adimlar"] == [["yukle", "01_1.jpg"], ["kapak"], ["bag"], ["sil", 8760104081], ["sira"], ["bag"]] and plan["en_fazla"] == 14)
    kontrol(f"en kotu istek 185 + 4 kapi okumasi = 189 (plan v3 Kota: 185) | olculen {s['en_kotu']}", s["en_kotu"] == 189)
    dv, il = durum_dosyalari("d1")
    rc, R = yaz(api, hz, po, "y1", R["plan_damga"], dv, il)
    s = R["ilanlar"][0]
    g = sorted(api.img, key=lambda x: x["rank"])
    kontrol("yazim PASS", rc == 0 and s["durum"] == "PASS")
    kontrol("13 gorsel, rank 1 yeni kapak + yeni alt metin, eski kapak silindi",
            len(g) == 13 and g[0]["listing_image_id"] == 7001 and g[0]["alt_text"] == YENI_ALT and 8760104081 not in [x["listing_image_id"] for x in g])
    kontrol("rank 2-13 KORU kimlik sirasi HAM ile ayni, alt metinler bos kaldi",
            [x["listing_image_id"] for x in g[1:]] == [h["listing_image_id"] for h in HAM["images"][1:]] and all(x["alt_text"] == "" for x in g[1:]))
    kontrol("5 Style bagi aynen (Botanical 8678064852 rank 12), kapak bagsiz",
            api.bag == {v["value"]: v["image_id"] for v in HAM["variation_images"]} and 7001 not in api.bag.values() and g[11]["listing_image_id"] == 8678064852)
    kontrol(f"gorsel sayisi en fazla 14 (olculen {api.max_n})", api.max_n == 14)
    tur = [y[0] for y in api.yaz if y[0] in ("yukle", "sil", "bag")]
    kontrol(f"yazim sirasi: yukle, bag (erken), sil eski, bag (son) | {tur}", tur == ["yukle", "bag", "sil", "bag"])
    kontrol(f"bos alt metinli KORU: sira POST'larinda alt_text alani yok ({api.alt_yok} POST)", api.alt_yok == 12)
    ilr = json.loads(il.read_text())["ilanlar"][LID]
    kontrol("ILERLEME set 13 hedef 13 PASS", ilr["set"] == 13 and ilr["hedef"] == 13 and ilr["durum"] == "PASS")
    dvr = json.loads(dv.read_text())["ilanlar"][LID]
    kontrol("DEVAM kaydi bitti (adim 6/6), yuklenen kimlik 7001", dvr["adim"] == 6 and dvr["yuklenen"] == {"01_1.jpg": 7001})
    # ZATEN: ayni girdilerle tekrar -> yazma yok
    n0 = len(api.yaz)
    rc, R2, _ = kuru(api, hz, "k1b", devam=dv, ilerleme=il)
    kontrol("bitmis ilan tekrar: ZATEN, yazma yok", R2["ilanlar"][0]["durum"] == "ZATEN" and len(api.yaz) == n0)
    # durum esigi 13
    D = DD.Dosya("gdrive:X/ILERLEME.json", "json-ilanlar")
    once = {"ilanlar": {LID: ilr}}
    try:
        D.azalmama(once, {"ilanlar": {LID: dict(ilr, durum="DUR")}}); geri = False
    except DD.DurumHatasi:
        geri = True
    D.azalmama({"ilanlar": {LID: dict(ilr, durum="DUR", set="-")}}, {"ilanlar": {LID: ilr}})
    kontrol("durum_dosyasi: set 13 / hedef 13 PASS geri donmez (esik kayittaki hedef)", geri)
    return hz


def yukleme_hatasi(hz):
    api = SahteYD(); api.yukle_hata = {1: ("500", True, 0)}        # yukleme olustu ama 500 dondu
    _, R, po = kuru(api, hz, "k2")
    dv, il = durum_dosyalari("d2")
    rc, R = yaz(api, hz, po, "y2", R["plan_damga"], dv, il)
    kontrol(f"yukleme 500 ama olustu: ikinci yukleme yok, PASS (yukleme {api.n_yukle})", R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 1)


def bag_bos(hz):
    api = SahteYD()
    _, R, po = kuru(api, hz, "k3")
    damga = R["plan_damga"]
    dv, il = durum_dosyalari("d3")
    api.bag_yut = True
    rc, R = yaz(api, hz, po, "y3", damga, dv, il)
    kontrol("bag bos donerse DUR (dogrulanamadi), kosu durur", rc == 1 and R["ilanlar"][0]["durum"] == "DUR" and "dogrulanamadi" in R["ilanlar"][0]["neden"][0])
    # bag onarimi: once kalan adimlar (devam, kurtar), sonra yalniz bag
    api.bag_yut = False
    rc, R = yaz(api, hz, po, "y3b", damga, dv, il, "--kurtar")
    kontrol(f"kurtarma: kayitli plan + canli galeriyle surer, PASS (yukleme toplam {api.n_yukle})", R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 1)
    api.bag = {}
    out = DEPO / "y3c"
    with contextlib.redirect_stdout(io.StringIO()):
        K.sonlandir(api, "1", arg(hz, out, "--bag-onar", "--confirm", "YD_KAPAK_BAG", "--plan-damga", damga, "--devam", str(dv), "--ilerleme", str(il)))
    R = json.loads((out / "RAPOR.json").read_text())
    kontrol("bag onarimi (YD_KAPAK_BAG): 5 Style bagi geri, gorsele yazim yok",
            R["ilanlar"][0]["durum"] == "PASS" and api.bag == {v["value"]: v["image_id"] for v in HAM["variation_images"]})


def devam_zaten_blok(hz):
    # yarim ilan: kapak yuklendi + rank 1 (galeri 14, yeni alt metin) -> kota tabaninda durdu; ikinci kosu DEVAM ile surer (BLOK degil)
    api = SahteYD()
    _, R, po = kuru(api, hz, "k4")
    damga = R["plan_damga"]
    dv, il = durum_dosyalari("d4")
    api.kes_kalan = None
    api.remaining = 5000
    orig = api._k
    say = {"n": 0}

    def kes():
        say["n"] += 1
        if any(y[0] == "yukle" for y in api.yaz) and any(y[0] == "sira" for y in api.yaz) and not any(y[0] == "bag" for y in api.yaz):
            api.remaining = 9                                          # kapak rank 1 yazildi, erken bag gonderilmeden kota tabani
        return orig()
    api._k = kes
    rc, R = yaz(api, hz, po, "y4", damga, dv, il)
    api._k = orig; api.remaining = 5000
    g = sorted(api.img, key=lambda x: (x["rank"], x["listing_image_id"]))   # sahte Etsy sirasi (Sahte.get)
    kontrol(f"yarim ilan: kota tabaninda durdu, galeri {len(g)}, rank 1 yeni alt metin", len(g) == 14 and g[0]["alt_text"] == YENI_ALT
            and R["ilanlar"][0]["durum"] in ("DUR", "KALAN"))
    _, Rk, _ = kuru(api, hz, "k4b", devam=dv, ilerleme=il)
    kontrol("yarim ilan kuru: DEVAM (BLOK'a dusmez; galeri 14 / yeni alt metin)", Rk["ilanlar"][0]["durum"] == "DEVAM")
    rc, R = yaz(api, hz, po, "y4b", damga, dv, il)
    kontrol(f"yarim ilan yazim: DEVAM ile PASS, ikinci yukleme yok (yukleme {api.n_yukle})", R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 1)
    # kayitsiz yeni alt metin -> BLOK
    api2 = SahteYD(); api2.img[0]["alt_text"] = YENI_ALT
    _, R, _ = kuru(api2, hz, "k5")
    kontrol("rank 1 yeni alt metinli ama kayit yok: BLOK (elle)", R["ilanlar"][0]["durum"] == "BLOK" and "kayitta" in R["ilanlar"][0]["neden"][0])


def bloklar(hz):
    def blok(api, beklenen, hz_=hz):
        _, R, _ = kuru(api, hz_, "kb")
        s = R["ilanlar"][0]
        kontrol(f"BLOK: {beklenen}", s["durum"] == "BLOK" and any(beklenen in n for n in s["neden"]) and not api.yaz)
    a = SahteYD(state="draft"); blok(a, "state draft")
    a = SahteYD(); a.img.pop(); blok(a, "canli galeri 12 gorsel")
    a = SahteYD(); a.bag["Botanical"] = 8760104081; blok(a, "kapak (rank 1) bagli")
    a = SahteYD(); a.bag["Botanical"] = 8725886577; blok(a, "Botanical bagli gorsel 8725886577")
    a = SahteYD(); a.bag.pop("Layers"); blok(a, "canli Style bagi 4 kayit")
    a = SahteYD(); a.img[5]["listing_image_id"] = 1234; blok(a, "canli kimlik kumesi yedekten farkli")
    a = SahteYD(); a.img[2]["rank"], a.img[3]["rank"] = a.img[3]["rank"], a.img[2]["rank"]; blok(a, "sirasi yedekten")
    a = SahteYD(); a.img[4]["alt_text"] = "yeni elle yazilmis"; blok(a, "alt metinler (rank 2-13) yedekten")
    hz2 = hazir_kur("h2")
    (hz2 / LID / "hedef" / "01_1.jpg").write_bytes((hz2 / LID / "hedef" / "01_1.jpg").read_bytes() + b"x")
    blok(SahteYD(), "sha256 manifest", hz2)
    hz3 = hazir_kur("h3", kapak_boyut=(3000, 2250))
    _, R, _ = kuru(SahteYD(), hz3, "kb3")
    kontrol("BLOK (liste kapisi): kapak 3000x2250", R["ilanlar"][0]["durum"] == "BLOK" and "2400x2400" in " ".join(R["ilanlar"][0]["neden"]))


def kota_ve_kilit(hz):
    api = SahteYD()
    _, R, po = kuru(api, hz, "k6")
    damga = R["plan_damga"]
    dv, il = durum_dosyalari("d6")
    api.remaining = 150
    rc, R = yaz(api, hz, po, "y6", damga, dv, il)
    kontrol("kota: kalan 150 < en kotu + 10 -> KALAN, ilan baslamadi", R["ilanlar"][0]["durum"] == "KALAN" and not api.yaz)
    api.remaining = 5000; api.img[0]["alt_text"] = "degisti"
    rc, R = yaz(api, hz, po, "y6b", damga, dv, il)
    kontrol("plan kilidi: canli durum kuru plandan farkli -> BLOK", R["ilanlar"][0]["durum"] == "BLOK" and not api.yaz)
    try:
        K.arg(["--hazir", str(hz), "--out", str(DEPO / "x"), "--confirm", "YD_KAPAK"]); ok = False
    except SystemExit:
        ok = True
    kontrol("onay + plan + plan_damga olmadan yazim yok", ok)
    try:
        K.plan_yukle(po / "PLAN_YD.json", damga[:-1] + ("0" if damga[-1] != "0" else "1")); ok = False
    except SystemExit:
        ok = True
    kontrol("plan_damga bozuk -> DUR", ok)


def main():
    hz = normal_akis()
    yukleme_hatasi(hz)
    bag_bos(hz)
    devam_zaten_blok(hz)
    bloklar(hz)
    kota_ve_kilit(hz)
    gec = sum(1 for _, ok in SONUC if ok)
    print(f"yd_kapak_yukle testleri: {gec}/{len(SONUC)} PASS")
    return 0 if gec == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
