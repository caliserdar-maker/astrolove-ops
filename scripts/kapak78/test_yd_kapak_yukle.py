#!/usr/bin/env python3
"""YD kapak + 10'lu galeri yukleyicisi yerel testi (plan v3 adim 8; Serdar 27 Eki). Ag yok, Drive yok, Etsy yok: sahte Etsy
(test_eski78_gorsel_yukle.Sahte'nin Style 513 / Format 514 surumu), pilot HAM'in gercek yapisi (test_veri/HAM_4595350971.json: 13 gorsel,
Style bagi r9-r13, Botanical r12). Girdi yd_liste_uret.py liste ile uretilir (test_yd_liste_uret.galeri_kur).
Senaryolar: normal akis (kuru PLAN + plan_damga, yazim 13 -> en fazla 14 -> 10, eski 13'un hepsi silindi, bagli eski gorsel erken bagdan
sonra silinir, baglar sira 6-10, kapak bagsiz, alt metinler); yukleme hatasi sonrasi ikinci yukleme yok; son bag bos -> DUR + kurtarma +
bag onarimi; DEVAM -> ZATEN -> BLOK sirasi (yarim ilan BLOK'a dusmez, bitmis ilan ZATEN, kayitsiz yeni alt metin BLOK); cdn_yedek
kilit altinda cagrilmaz; durum esigi 10 (durum_dosyasi); BLOK turleri; kota kapisi; plan kilidi; en kotu istek (kod okumasi)."""
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
import test_yd_liste_uret as TL  # noqa: E402
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


def hazir_kur(ad="h", qc_durum="PASS", kapak_boyut=None):
    d = DEPO / ad
    TL.galeri_kur(d)
    if kapak_boyut:
        Image.new("RGB", kapak_boyut, (40, 100, 50)).save(d / "kapak" / f"{CIFT}_Y01.jpg", "JPEG", quality=90); TL.manifest(d)
    TL.qc(d, durum=qc_durum)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = L.main(["liste", "--ciftler", str(d / "yd.csv"), "--kaynak", str(KOK / "docs/yd_kapak/KAPAK_KAYNAK.csv"), "--ham-dir", str(d / "HAM"),
                     "--kapak-dir", str(d / "kapak"), "--qc", str(d / "QC.json"), "--alt", str(d / "ALT.csv"), "--yedek-ozet", str(d / "OZET.md"),
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


ESKI = [g["listing_image_id"] for g in HAM["images"]]
BAGLI0 = {v["image_id"] for v in HAM["variation_images"]}
EN_KOTU = 4 + 7 + 10 * 21 + 11 + 13 * 11 + 2 * 11 + 2 * (10 * 3 + 8) + 19   # kod okumasi: kapi 4 + on okuma 7 + yukle + kapak + sil + bag + sira + son


def normal_akis():
    hz = hazir_kur()
    api = SahteYD()
    rc, R, po = kuru(api, hz, "k1")
    s = R["ilanlar"][0]
    kontrol("kuru: PLAN, yazma yok, plan_damga", rc == 0 and s["durum"] == "PLAN" and not api.yaz and R["plan_damga"].startswith("111_"))
    plan = json.loads((po / "PLAN_YD.json").read_text())["girdiler"][LID]
    ad = [a[0] for a in plan["adimlar"]]
    kontrol(f"plan: yukle kapak -> kapak; 10 yukle, 13 sil, 2 bag, 1 sira; erken bag 5 stil kartindan sonra; en fazla {plan['en_fazla']}",
            plan["adimlar"][:2] == [["yukle", "01_1.jpg"], ["kapak"]] and ad.count("yukle") == 10 and ad.count("sil") == 13
            and ad.count("bag") == 2 and ad[-2:] == ["sira", "bag"] and plan["en_fazla"] == 14
            and [a[1] for a in plan["adimlar"] if a[0] == "yukle"][1:6] == [f"{k:02d}_{k}.jpg" for k in range(6, 11)]
            and ad.index("bag") > max(i for i, a in enumerate(plan["adimlar"]) if a[0] == "yukle" and a[1] == "10_10.jpg"))
    kontrol(f"en kotu istek {EN_KOTU} (kod okumasi; 4 kapi okumasi dahil) | olculen {s['en_kotu']}", s["en_kotu"] == EN_KOTU)
    dv, il = durum_dosyalari("d1")
    rc, R = yaz(api, hz, po, "y1", R["plan_damga"], dv, il)
    s = R["ilanlar"][0]
    g = sorted(api.img, key=lambda x: (x["rank"], x["listing_image_id"]))
    kontrol("yazim PASS", rc == 0 and s["durum"] == "PASS")
    kontrol("10 gorsel, rank 1 yeni kapak + yeni alt metin, eski 13'un hepsi silindi",
            len(g) == 10 and g[0]["alt_text"] == YENI_ALT and not set(ESKI) & {x["listing_image_id"] for x in g} and sorted(api.silinenler) == sorted(ESKI))
    yk = json.loads(dv.read_text())["ilanlar"][LID]["yuklenen"]
    kontrol("rank 1..10 = yuklenen 01..10, alt metinler hedef", [x["listing_image_id"] for x in g] == [yk[f"{k:02d}_{k}.jpg"] for k in range(1, 11)]
            and g[3]["alt_text"] == "Format and size options card" and g[9]["alt_text"] == "Cancer and Libra card 10 alt text")
    rk = {x["listing_image_id"]: x["rank"] for x in g}
    kontrol(f"5 Style bagi yeni kartlarda (Starlit 6 ... Botanical 10), kapak bagsiz | {({k: rk.get(v) for k, v in api.bag.items()})}",
            {k: rk.get(v) for k, v in api.bag.items()} == K.STIL_SIRA and g[0]["listing_image_id"] not in api.bag.values())
    kontrol(f"gorsel sayisi en fazla 14 (olculen {api.max_n})", api.max_n == 14)
    ilk_bag = next(i for i, y in enumerate(api.yaz) if y[0] == "bag")
    kontrol("bagli eski stil gorselleri ancak erken bagdan sonra silindi",
            all(i > ilk_bag for i, y in enumerate(api.yaz) if y[0] == "sil" and y[1] in BAGLI0))
    kontrol(f"izler: kapak yazimindan sonra bag hic 0 degil (en az {min(b for _, b in api.izler)})", min(b for _, b in api.izler) == 5)
    kontrol(f"sira POST'larinda alt_text hep var ({api.alt_yok} eksik)", api.alt_yok == 0)
    ilr = json.loads(il.read_text())["ilanlar"][LID]
    kontrol("ILERLEME set 10 hedef 10 PASS", ilr["set"] == 10 and ilr["hedef"] == 10 and ilr["durum"] == "PASS")
    dvr = json.loads(dv.read_text())["ilanlar"][LID]
    kontrol(f"DEVAM kaydi bitti (adim {dvr['adim']}/{len(dvr['plan'])}), 10 yukleme kaydi", dvr["adim"] == len(dvr["plan"]) and len(dvr["yuklenen"]) == 10)
    n0 = len(api.yaz)
    rc, R2, _ = kuru(api, hz, "k1b", devam=dv, ilerleme=il)
    kontrol("bitmis ilan tekrar: ZATEN, yazma yok", R2["ilanlar"][0]["durum"] == "ZATEN" and len(api.yaz) == n0)
    hz4 = hazir_kur("h4", qc_durum="OLCUM")
    rc, R3, _ = kuru(api, hz4, "k1c", devam=dv, ilerleme=il)
    kontrol("bitmis ilan + liste kapisi BLOK: once ZATEN (BLOK degil)", R3["ilanlar"][0]["durum"] == "ZATEN" and len(api.yaz) == n0)
    D = DD.Dosya("gdrive:X/ILERLEME.json", "json-ilanlar")
    try:
        D.azalmama({"ilanlar": {LID: ilr}}, {"ilanlar": {LID: dict(ilr, durum="DUR")}}); geri = False
    except DD.DurumHatasi:
        geri = True
    D.azalmama({"ilanlar": {LID: dict(ilr, durum="DUR", set="-")}}, {"ilanlar": {LID: ilr}})
    kontrol("durum_dosyasi: set 10 / hedef 10 PASS geri donmez (esik kayittaki hedef)", geri)
    return hz


def yukleme_hatasi(hz):
    api = SahteYD(); api.yukle_hata = {1: ("500", True, 0)}        # yukleme olustu ama 500 dondu
    _, R, po = kuru(api, hz, "k2")
    dv, il = durum_dosyalari("d2")
    rc, R = yaz(api, hz, po, "y2", R["plan_damga"], dv, il)
    kontrol(f"yukleme 500 ama olustu: ikinci yukleme yok, PASS (yukleme {api.n_yukle})", R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 10)


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
    kontrol(f"kurtarma: kayitli plan + canli galeriyle surer, PASS (yukleme toplam {api.n_yukle})", R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 10)
    api.bag = {}
    out = DEPO / "y3c"
    with contextlib.redirect_stdout(io.StringIO()):
        K.sonlandir(api, "1", arg(hz, out, "--bag-onar", "--confirm", "YD_KAPAK_BAG", "--plan-damga", damga, "--devam", str(dv), "--ilerleme", str(il)))
    R = json.loads((out / "RAPOR.json").read_text())
    rk = {x["listing_image_id"]: x["rank"] for x in api.img}
    kontrol("bag onarimi (YD_KAPAK_BAG): 5 Style bagi sira 6-10'a geri, gorsele yazim yok",
            R["ilanlar"][0]["durum"] == "PASS" and {k: rk.get(v) for k, v in api.bag.items()} == K.STIL_SIRA)


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
    _, Rk, pk = kuru(api, hz, "k4b", devam=dv, ilerleme=il)
    kontrol("yarim ilan kuru: DEVAM (BLOK'a dusmez; galeri 14 / yeni alt metin), kayitli plan raporda",
            Rk["ilanlar"][0]["durum"] == "DEVAM" and damga in Rk["ilanlar"][0]["neden"][0])
    kontrol(f"DEVAM kota tahmini son tamamlanan sil/yukle'den (devam_basla 1; en kotu {Rk['ilanlar'][0]['en_kotu']})",
            K.devam_basla([("yukle",), ("kapak",), ("bag",), ("sil", 1), ("sira",), ("bag",)], 3) == 1
            and Rk["ilanlar"][0]["en_kotu"] == Y.istek_en_kotu([tuple(x) for x in json.loads(dv.read_text())["ilanlar"][LID]["plan"]], 1, ilk=False, n=10))
    rc, R = yaz(api, hz, pk, "y4b", Rk["plan_damga"], dv, il)                # YENI kuru damgasiyla (inceleme 27 Eki bulgu 1)
    kontrol(f"yarim ilan, yeni kuru damgasi: kayitli planla DEVAM, PASS, ikinci yukleme yok (yukleme {api.n_yukle})",
            R["ilanlar"][0]["durum"] == "PASS" and api.n_yukle == 10 and Rk["plan_damga"] != damga)
    # yarim ilan + manifest yok (HAM eksik): cokmez, DUR, cikis 1, durum dosyalari yazilir
    api3 = SahteYD(); _, R, po3 = kuru(api3, hz, "k7"); d7, i7 = durum_dosyalari("d7")
    orig = api3._k

    def kes3():
        if any(y[0] == "yukle" for y in api3.yaz) and not any(y[0] == "bag" for y in api3.yaz) and any(y[0] == "sira" for y in api3.yaz):
            api3.remaining = 9
        return orig()
    api3._k = kes3
    yaz(api3, hz, po3, "y7", R["plan_damga"], d7, i7)
    api3._k = orig; api3.remaining = 5000
    import shutil
    hz7 = DEPO / "h7"; shutil.copytree(hz, hz7); shutil.rmtree(hz7 / LID)
    oz = json.loads((hz7 / "LISTE_OZET.json").read_text()); oz["ilanlar"][LID].update(durum="BLOK", neden=["HAM yok"])
    (hz7 / "LISTE_OZET.json").write_text(json.dumps(oz))
    rc, R = yaz(api3, hz7, po3, "y7b", R["plan_damga"], d7, i7)
    kontrol("yarim ilan + manifest yok: DUR, cikis 1, DEVAM.json yazildi (cokmedi)",
            rc == 1 and R["ilanlar"][0]["durum"] == "DUR" and LID in json.loads(d7.read_text())["ilanlar"])
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
    a = SahteYD(); a.bag["Layers"] = a.img[2]["listing_image_id"]; blok(a, "canli Style baglari yedekteki baglardan farkli")
    hz2 = hazir_kur("h2")
    (hz2 / LID / "hedef" / "04_4.jpg").write_bytes((hz2 / LID / "hedef" / "04_4.jpg").read_bytes() + b"x")
    blok(SahteYD(), "04_4.jpg (ORTAK_Y04.jpg) sha256 manifest", hz2)
    hz3 = hazir_kur("h3", kapak_boyut=(2400, 2400))          # Merkez 27 Eki karar e: yeni kapak 3000x2250; kare BLOK
    _, R, _ = kuru(SahteYD(), hz3, "kb3")
    kontrol("BLOK (liste kapisi): kapak 2400x2400", R["ilanlar"][0]["durum"] == "BLOK" and "3000x2250" in " ".join(R["ilanlar"][0]["neden"]))


def kota_ve_kilit(hz):
    api = SahteYD()
    _, R, po = kuru(api, hz, "k6")
    damga = R["plan_damga"]
    dv, il = durum_dosyalari("d6")
    api.remaining = EN_KOTU + 5
    rc, R = yaz(api, hz, po, "y6", damga, dv, il)
    kontrol(f"kota: kalan {EN_KOTU + 5} < en kotu + 10 -> KALAN, ilan baslamadi", R["ilanlar"][0]["durum"] == "KALAN" and not api.yaz)
    api.remaining = 5000; api.img[2]["rank"], api.img[3]["rank"] = api.img[3]["rank"], api.img[2]["rank"]
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
