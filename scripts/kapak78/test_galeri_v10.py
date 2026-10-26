#!/usr/bin/env python3
"""galeri v10 (galeri_v10_liste + galeri_v10_yukle + eski78 hedef_n=9) yerel testi. Ag yok, Drive yok, Etsy yok (sahte Etsy:
scripts/etsy/test_eski78_gorsel_yukle.Sahte; ilan basina ayri sahte, ortak kota). Kartlar depodaki gercek CL renk kartlarindan
(data/pod/cl_galeri_final19 15-19) uretilir: yedek = kart aynen; yeni kapak / G6-G9 = kartin poster kutusu cerceve + paspartu ile
farkli konum ve olcekte bej duvara yerlestirilir (JPEG 90).
Senaryolar: liste (alt metin, ayni burc, dosya / boyut / sha, TASLAK, renk karisma 20 yanlis renk), kuru PLAN + plan_damga, yazim
17 -> 9, 20 siniri, yukleme sonrasi hata (ikinci yukleme yok), silinen kimligin yeniden verilmesi, sira 2. gecis ve DUR, son bag
bos -> DUR + bag_kur onarimi, kota kapisi (ilan baslamadan), her kesimde devam (kota) ve kurtarma (GET 503), ZATEN, BLOK turleri,
plan kilidi (canli degisti / damga bozuk / onay yok), DEVAM Drive kopyasi."""
import copy
import csv
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import test_eski78_gorsel_yukle as T  # noqa: E402  (G.time.sleep etkisiz, Y.cdn_indir ag yok)
import eski78_gorsel_yukle as Y  # noqa: E402
import cl_galeri_degistir as G  # noqa: E402
import galeri_v10_liste as L  # noqa: E402
import galeri_v10_yukle as V  # noqa: E402

CL = KOK / "data/pod/cl_galeri_final19"
KART = {"Midnight Blue": "15_renk_midnight_blue.jpg", "Deep Black": "16_renk_deep_black.jpg", "Pure White": "17_renk_pure_white.jpg",
        "Champagne Ivory": "18_renk_champagne_ivory.jpg", "Warm Parchment": "19_renk_warm_parchment.jpg"}
VID = {k: v[1] for k, v in T.RENK.items()}   # sahte Etsy value_id 1..5
ILAN = {"4570110121": ("AQUARIUS_AQUARIUS", "Aquarius", "Aquarius"), "4570110641": ("AQUARIUS_ARIES", "Aquarius", "Aries")}
YERLESIM = {1: (980, 640, 1040), 6: (300, 300, 900), 7: (1700, 200, 1200), 8: (600, 500, 1300), 9: (1400, 700, 1000)}
BAG_RANK = {"Midnight Blue": 13, "Deep Black": 14, "Pure White": 15, "Champagne Ivory": 16, "Warm Parchment": 17}
SONUC = []


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def sahne(renk, sira, yol):
    """renk kartinin poster kutusu -> cerceveli sahne (3000x2250 JPEG)"""
    x, y, h = YERLESIM[sira]
    p = Image.open(CL / KART[renk]).convert("RGB").crop(L.KUTU)
    w = round(h * p.width / p.height); p = p.resize((w, h), Image.LANCZOS)
    im = Image.new("RGB", L.BOYUT, (232, 222, 208)); d = ImageDraw.Draw(im)
    d.rectangle((x - 90, y - 90, x + w + 90, y + h + 90), fill=(20, 20, 20)); d.rectangle((x - 60, y - 60, x + w + 60, y + h + 60), fill=(250, 250, 248))
    im.paste(p, (x, y)); im.save(yol, "JPEG", quality=90)


DEPO = Path(tempfile.mkdtemp(prefix="gv10_"))


def girdi_kur():
    """kapak, galeri, yedek klasorleri (iki ilan)."""
    kd, gd, yd = DEPO / "kapak", DEPO / "galeri", DEPO / "yedek"
    for d in (kd, gd, yd):
        d.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(("02_format.jpg", "14_surec.jpg")):
        shutil.copyfile(CL / n, gd / f"ORTAK_G{4 + i}.jpg")
    for lid, (cift, a, b) in ILAN.items():
        sahne("Midnight Blue", 1, kd / f"KAPAK_{cift}.jpg")
        for s, renk in ((6, "Deep Black"), (7, "Pure White"), (8, "Champagne Ivory"), (9, "Warm Parchment")):
            sahne(renk, s, gd / f"{cift}_G{s}.jpg")
        for s, n in ((2, "03_konsept.jpg"), (3, "04_kisisellestirme.jpg")):
            im = Image.open(CL / n).convert("RGB"); ImageDraw.Draw(im).text((10, 10), cift, fill=(0, 0, 0)); im.save(gd / f"{cift}_G{s}.jpg", quality=90)
        y = yd / f"{lid}_{cift}"; y.mkdir(exist_ok=True)
        gor = [dict(rank=r, listing_image_id=int(lid[-3:]) * 100 + r, full_width=3000, full_height=2250, url_fullxfull="u",
                    alt_text=f"eski {r}") for r in range(1, 18)]
        bag = [dict(property_id=200, value_id=VID[k], value=k, image_id=int(lid[-3:]) * 100 + r, rank=r) for k, r in BAG_RANK.items()]
        (y / "GALERI.json").write_text(json.dumps(dict(gorseller=gor, baglar=bag)))
        for k, r in BAG_RANK.items():
            shutil.copyfile(CL / KART[k], y / f"r{r}_{int(lid[-3:]) * 100 + r}.jpg")
        for r in range(1, 13):
            (y / f"r{r}_{int(lid[-3:]) * 100 + r}.jpg").write_bytes(b"\xff\xd8\xff yedek")
    (yd / "OZET.md").write_text("# Poster 78 galeri yedegi\n\n| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n"
                                + "".join(f"| {lid} | {c} | 17 | PASS |  |\n" for lid, (c, _, _) in ILAN.items()))
    return kd, gd, yd


def yedek_ls(yd, d):
    p = d / "yedek_ls.json"
    p.write_text(json.dumps([dict(Path=x.relative_to(yd).as_posix(), Name=x.name, Size=x.stat().st_size) for x in sorted(yd.rglob("*.jpg"))]))
    return p


def ciftler_csv(d):
    p = d / "ciftler.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"])
        w.writerows([lid, c, a, b] for lid, (c, a, b) in ILAN.items())
    return p


def alt_csv(d, durum="TASLAK"):
    p = d / "alt.csv"
    t = (KOK / "data/pod/galeri_v10_alt.csv").read_text(encoding="utf-8")
    p.write_text(t.replace(",TASLAK", f",{durum}"), encoding="utf-8")
    return p


def liste(kd, gd, yd, yazim=False, durum="ONAYLI", sadece=""):
    d = Path(tempfile.mkdtemp(prefix="gv10l_"))
    args = ["--ciftler", str(ciftler_csv(d)), "--alt", str(alt_csv(d, durum)), "--kapak-dir", str(kd), "--galeri-dir", str(gd),
            "--yedek-dir", str(yd), "--yedek-ozet", str(yd / "OZET.md"), "--yedek-liste", str(yedek_ls(yd, d)),
            "--out", str(d / "hazir"), "--is", "2"] + (["--yazim"] if yazim else []) + (["--sadece", sadece] if sadece else [])
    rc = L.main(args)
    return rc, d / "hazir", json.loads((d / "hazir" / "LISTE_OZET.json").read_text()) if rc == 0 else None


class S10(T.Sahte):
    def __init__(self, lid, *a, bes_x7=True, **k):
        super().__init__(*a, **k); self.lid = lid; self.bes = bes_x7; self.bag_yut_n = 0; self.kes = None
        self.bag_ek = []          # var_img'e eklenecek fazladan kayitlar (BLOK testleri)
        self.bag_pid = 200

    def _k(self):
        if self.kes is not None and self.calls + 1 >= self.kes:
            self.kes = None; self.remaining = 9
        super()._k()

    def get(self, path, params=None, ok404=False):
        r = super().get(path, params, ok404)
        if path.endswith("/inventory"):
            r = copy.deepcopy(r)
            r["products"].append(dict(sku="s2", offerings=[dict(price=1)], property_values=[
                dict(property_id=513, value_ids=[11], values=["5×7″ (13×18cm)" if self.bes else "8×10″ (20×25cm)"])]))
        if path.endswith("/variation-images"):
            r = dict(results=[dict(x, property_id=self.bag_pid) for x in r["results"]] + copy.deepcopy(self.bag_ek))
        return r

    def post_json(self, path, body):
        if self.bag_yut_n and self.vi_cagri + 1 == self.bag_yut_n:
            self._k(); self.vi_cagri += 1; self.yaz.append(("bag",)); self.bag = {}; self._iz(); return {}
        return super().post_json(path, body)


class Coklu:
    """ilan basina sahte Etsy, ortak kota ve istek sayaci"""
    def __init__(self, sahteler, kota=100000):
        self.s = sahteler; self.remaining = kota; self.calls = 0; self.sert_taban = 10

    def _sec(self, path):
        import re
        return self.s[re.search(r"/listings/(\d+)", path).group(1)]

    def kota_kapisi(self, ne):
        if self.remaining is not None and self.remaining < 10:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 10 ({ne} baslamadi)")

    def _cagir(self, ad, path, *a, **k):
        f = self._sec(path); f.remaining, f.calls = self.remaining, self.calls
        try:
            return getattr(f, ad)(path, *a, **k)
        finally:
            self.remaining, self.calls = f.remaining, f.calls

    def get(self, path, params=None, ok404=False):
        return self._cagir("get", path, params, ok404)

    def delete(self, path):
        return self._cagir("delete", path)

    def post_file(self, path, files=None, data=None, tekrar=3):
        return self._cagir("post_file", path, files=files, data=data, tekrar=tekrar)

    def post_json(self, path, body):
        return self._cagir("post_json", path, body)


def sahte(lid, **k):
    base = int(lid[-3:]) * 100
    canli = [(r, base + r) for r in range(1, 18)]
    bag = {kk: base + r for kk, r in BAG_RANK.items()}
    return S10(lid, canli, bag, **k)


def kos(api, hazir, out, kuru=True, plan=None, damga="", bes_x7="zorunlu", durum_dir=None, kurtar=False, azami=0, kok_=""):
    durum_dir = durum_dir or out
    args = ["--hazir", str(hazir), "--out", str(out), "--bes-x7", bes_x7, "--kosu", "777",
            "--devam", str(durum_dir / "DEVAM.json"), "--ilerleme", str(durum_dir / "ILERLEME.json")]
    if kuru:
        args.append("--kuru")
    else:
        args += ["--confirm", "GALERI_V10", "--plan", str(plan), "--plan-damga", damga]
    if kurtar:
        args.append("--kurtar")
    if azami:
        args += ["--azami-dk", str(azami)]
    if kok_:
        args += ["--devam-hedef-kok", kok_]
    a = V.arg(args)
    try:
        rc = V.sonlandir(api, "1", a)
    except SystemExit as e:
        return 9, dict(hata=str(e.code))
    return rc, json.loads((Path(out) / "RAPOR.json").read_text())


def ilan_durum(R, lid):
    return next((s for s in R.get("ilanlar", []) if s["ilan"] == lid), {})


def tamam9(f, lid, hazir):
    """9 gorsel, rank 1..9, alt metinler hedef, 5 bag hedef sirada, cift yukleme yok (9 yukleme), en fazla 20"""
    g = sorted(f.img, key=lambda x: x["rank"])
    man = json.loads((hazir / lid / "manifest.json").read_text())
    alt = [Y.alt_norm(h["alt"]) for h in sorted(man["hedef"], key=lambda h: h["sira"])]
    rk = {x["listing_image_id"]: x["rank"] for x in g}
    return (len(g) == 9 and [x["rank"] for x in g] == list(range(1, 10)) and [Y.alt_norm(x["alt_text"]) for x in g] == alt
            and {k: rk.get(v) for k, v in f.bag.items()} == V.RENK_SIRA and len(T.yuklemeler(f)) == 9
            and len({x["listing_image_id"] for x in g}) == 9 and f.max_n <= G.IMG_LIMIT and not f.gec_kuyruk)


def kuru_ve_plan(hazir, lid="4570110121", **sk):
    """kuru kosu -> (plan yolu, damga, durum klasoru)"""
    d = Path(tempfile.mkdtemp(prefix="gv10k_"))
    api = Coklu({x: sahte(x, **sk) for x in ILAN})
    rc, R = kos(api, hazir, d / "kuru", durum_dir=d)
    return d, R, api


def yaz_kos(hazir, d, R, fakes, **k):
    api = Coklu(fakes, kota=k.pop("kota", 100000))
    rc, R2 = kos(api, hazir, Path(tempfile.mkdtemp(prefix="gv10y_")), kuru=False, plan=d / "kuru" / "PLAN_V10.json",
                 damga=R["plan_damga"], durum_dir=d, **k)
    return rc, R2, api


# ---------------- testler ----------------
def t_liste(kd, gd, yd):
    rc, hz, oz = liste(kd, gd, yd)
    kontrol("liste: 2 ilan HAZIR (dosya, yedek, renk karisma PASS)", rc == 0 and all(x["durum"] == "HAZIR" for x in oz["ilanlar"].values()))
    rows = list(csv.DictReader(open(hz / "4570110641" / "LISTE_4570110641.csv")))
    hedef = [r for r in rows if r["hedef_sira"]]
    kontrol("liste: 9 DEGISTIR + 17 CIKAR; eski78 liste_oku(n=9) kabul eder", len(hedef) == 9 and sum(r["islem"] == "CIKAR" for r in rows) == 17
            and len(Y.liste_oku(hz / "4570110641" / "LISTE_4570110641.csv", 9)[0]) == 9)
    a1 = {int(r["hedef_sira"]): r["hedef_alt"] for r in hedef}
    a2 = {int(r["hedef_sira"]): r["hedef_alt"] for r in csv.DictReader(open(hz / "4570110121" / "LISTE_4570110121.csv")) if r["hedef_sira"]}
    kontrol("alt metin: farkli burc '<A> and <B>' + ayni burc parantez bicimi (2, 3)",
            a1[2] == "Aquarius and Aries signs joined into one shared symbol" and a2[2] == "Two Aquarius signs joined into one shared symbol"
            and a2[3] == "Names and message printed under the two Aquarius signs" and a1[6].startswith("Deep Black Aquarius and Aries")
            and not any(c in "".join(a1.values()) for c in "—–"))
    man = json.loads((hz / "4570110641" / "manifest.json").read_text())
    kontrol("manifest: renk bagi MB->1 DB->6 PW->7 CI->8 WP->9, adlar yedekteki property 200 adlari",
            {v["value"]: v["image_id"] for v in man["variation_images"]} == V.RENK_SIRA and len(man["yedek_ids"]) == 17)
    rc, _, oz = liste(kd, gd, yd, yazim=True, durum="TASLAK", sadece="4570110641")
    kontrol("yazim + alt metin TASLAK -> BLOK", oz["ilanlar"]["4570110641"]["durum"] == "BLOK"
            and any("ONAYLI degil" in n for n in oz["ilanlar"]["4570110641"]["neden"]))
    # dosya kapilari
    for ad, bozan in (("kapak eksik", lambda: (kd / "KAPAK_AQUARIUS_ARIES.jpg").rename(kd / "x.jpg")),
                      ("G7 3000x2250 degil", lambda: Image.open(gd / "AQUARIUS_ARIES_G7.jpg").resize((2000, 1500)).save(gd / "AQUARIUS_ARIES_G7.jpg")),
                      ("G3 PNG", lambda: Image.open(gd / "AQUARIUS_ARIES_G3.jpg").save(gd / "AQUARIUS_ARIES_G3.jpg", "PNG")),
                      ("G2 = G3 ayni dosya", lambda: shutil.copyfile(gd / "AQUARIUS_ARIES_G3.jpg", gd / "AQUARIUS_ARIES_G2.jpg")),
                      ("Drive yedeginde r2 dosyasi yok", lambda: (yd / "4570110641_AQUARIUS_ARIES" / "r2_64102.jpg").unlink()),
                      ("yedek OZET satiri FAIL", lambda: (yd / "OZET.md").write_text((yd / "OZET.md").read_text().replace("| 17 | PASS |  |\n", "| 16 | FAIL | r2 |\n"))),
                      ("yedek baglari karisik (CI <-> WP kartlari)", lambda: (lambda p: p.write_text(json.dumps(dict(json.loads(p.read_text()), baglar=[
                          dict(b, image_id={64116: 64117, 64117: 64116}.get(b["image_id"], b["image_id"]),
                               rank={16: 17, 17: 16}.get(b["rank"], b["rank"])) for b in json.loads(p.read_text())["baglar"]]))))(
                          yd / "4570110641_AQUARIUS_ARIES" / "GALERI.json")),
                      ("yedek GALERI.json 16 gorsel", lambda: (lambda p: p.write_text(json.dumps(dict(json.loads(p.read_text()), gorseller=json.loads(p.read_text())["gorseller"][:16]))))(yd / "4570110641_AQUARIUS_ARIES" / "GALERI.json"))):
        yedek = Path(tempfile.mkdtemp()); shutil.copytree(DEPO, yedek / "d")
        bozan()
        rc, _, oz = liste(kd, gd, yd, sadece="4570110641")
        kontrol(f"liste kapisi: {ad} -> BLOK ({(oz['ilanlar']['4570110641']['neden'] or [''])[0][:70]})",
                oz["ilanlar"]["4570110641"]["durum"] == "BLOK")
        shutil.rmtree(DEPO); shutil.copytree(yedek / "d", DEPO)
    return hz


def t_renk():
    """renk karisma: her hedef slot (kapak MB, G6-G9) icin dogru renk PASS, diger 4 rengin her biri FAIL (20 yanlis)."""
    d = Path(tempfile.mkdtemp(prefix="gv10r_"))
    ref = {k: CL / v for k, v in KART.items()}
    for renk in KART:
        sahne(renk, 8, d / f"{renk}.jpg")
    kotu, en_kucuk_fark = [], 1e9
    for slot in KART:
        for renk in KART:
            r, esik = L.renk_kapisi(ref, {slot: d / f"{renk}.jpg"})
            ok = (r[slot]["sonuc"] == "PASS") == (renk == slot)
            if renk != slot:
                en_kucuk_fark = min(en_kucuk_fark, r[slot]["uzaklik"][slot])
            if not ok:
                kotu.append((slot, renk, r[slot].get("neden")))
    kontrol(f"renk karisma: 5 dogru PASS, 20 yanlis renk FAIL (esik {esik}, yanlis dosyada beklenen renge en kucuk uzaklik "
            f"{en_kucuk_fark:.1f})" + (f" | kotu {kotu[:2]}" if kotu else ""), not kotu)
    im = Image.new("RGB", L.BOYUT, (232, 222, 208)); im.save(d / "bos.jpg")
    r, _ = L.renk_kapisi(ref, {"Deep Black": d / "bos.jpg"})
    kontrol("renk karisma: postersiz kart -> FAIL (poster bulunamadi)", r["Deep Black"]["sonuc"] == "FAIL")


def t_akis(hz):
    lid = "4570110121"
    d, R, api = kuru_ve_plan(hz)
    kontrol(f"kuru: 2 ilan PLAN, yazma yok, plan_damga {R.get('plan_damga')}, en az {R.get('en_az_ilan')} / en kotu {R.get('en_kotu_ilan')}",
            R["sayilar"] == {"PLAN": 2} and all(f.yaz == [] for f in api.s.values()) and R["plan_damga"].startswith("777_"))
    O = G.OKUMA_TEKRAR
    hesap = 4 + 7 + 17 * (3 + O) + 9 * (5 + 2 * O) + (3 + O) + 2 * (9 * 3 + O) + 2 * (3 + O) + 2 * O + 3
    kontrol(f"en kotu istek (kod okumasi) {R['en_kotu_ilan']} = {hesap}; en az {R['en_az_ilan']} = 84", R["en_kotu_ilan"] == hesap
            and R["en_az_ilan"] == 4 + 7 + 17 * 2 + 9 * 2 + 2 + 10 + 4 + 5)
    pl = json.loads((d / "kuru" / "PLAN_V10.json").read_text())["girdiler"][lid]
    kontrol("plan: kapak ilk yukleme + rank 1; 2 bag (erken + son); son adim bag; en fazla 18 (<= 20)", pl["adimlar"][0] == ["yukle", "01_1.jpg"]
            and pl["adimlar"][1] == ["kapak"] and pl["adimlar"].count(["bag"]) == 2 and pl["adimlar"][-1] == ["bag"] and pl["en_fazla"] == 18)
    fakes = {x: sahte(x) for x in ILAN}
    rc, R2, api2 = yaz_kos(hz, d, R, fakes)
    f = fakes[lid]
    kontrol(f"yazim 17 -> 9: iki ilan PASS, 9 yukleme, rank/alt/bag hedef, en fazla {f.max_n} gorsel, istek {ilan_durum(R2, lid).get('istek')} <= en kotu",
            rc == 0 and R2["sayilar"] == {"PASS": 2} and all(tamam9(fakes[x], x, hz) for x in ILAN)
            and ilan_durum(R2, lid)["istek"] <= R["en_kotu_ilan"])
    kontrol("son yazim renk bagi (sonra gorsele yazim yok); yuklemelerde rank yok", f.yaz[-1] == ("bag",) and f.vi_cagri == 2)
    dv = json.loads((d / "DEVAM.json").read_text()); il = json.loads((d / "ILERLEME.json").read_text())
    kontrol("DEVAM.json + ILERLEME.json: iki ilan PASS, son kimlikler kayitli", all(il["ilanlar"][x]["durum"] == "PASS" for x in ILAN)
            and all(dv["ilanlar"][x]["durum"] == "PASS" for x in ILAN) and il["ilanlar"][lid]["son_ids"] == [x["listing_image_id"] for x in sorted(f.img, key=lambda x: x["rank"])])
    api3 = Coklu(fakes); rc, R3 = kos(api3, hz, Path(tempfile.mkdtemp()), durum_dir=d)
    rc4, R4, _ = yaz_kos(hz, d, R, fakes)
    kontrol("ZATEN: kuru ve yazim ikinci kez -> ZATEN 2, yazma yok", R3["sayilar"] == {"ZATEN": 2} and R4["sayilar"] == {"ZATEN": 2}
            and len(T.yuklemeler(f)) == 9 and f.vi_cagri == 2)
    # bag_kur onarimi icin: son bag bos
    fakes = {x: sahte(x) for x in ILAN}; fakes[lid].bag_yut_n = 2
    d, R, _ = kuru_ve_plan(hz)
    rc, R2, _ = yaz_kos(hz, d, R, fakes)
    f = fakes[lid]
    kontrol("son bag yaniti bos -> DUR (yeniden yazma yok), kosu durur (2. ilan KALAN)", ilan_durum(R2, lid)["durum"] == "DUR"
            and "renk baglari" in ilan_durum(R2, lid)["neden"][0] and f.vi_cagri == 2 and ilan_durum(R2, "4570110641")["durum"] == "KALAN")
    (d / "x").mkdir(exist_ok=True)
    (d / "x" / "DEVAM.json").write_text(json.dumps(json.loads((d / "DEVAM.json").read_text())["ilanlar"][lid]))
    try:
        B = Y.bag_kur(f, "1", lid, hz / lid / f"LISTE_{lid}.csv", hz / lid / "manifest.json", d / "x" / "DEVAM.json", d / "bag", yaz=True, hedef_n=9)
    except Exception as e:  # noqa: BLE001
        B = dict(sonuc="DUR", sorun=[str(e)])
    # surucu bag onarim modu (ayni durum: once baglar tekrar bosaltilir)
    f.bag = {}; vi0 = f.vi_cagri
    api = Coklu(fakes)
    a = V.arg(["--hazir", str(hz), "--out", str(d / "bagkos"), "--bes-x7", "zorunlu", "--kosu", "778", "--devam", str(d / "DEVAM.json"),
               "--ilerleme", str(d / "ILERLEME.json"), "--bag-onar", "--confirm", "GALERI_V10_BAG", "--plan-damga", R["plan_damga"]])
    rc = V.sonlandir(api, "1", a); RB = json.loads((d / "bagkos" / "RAPOR.json").read_text())
    dvk = json.loads((d / "DEVAM.json").read_text())["ilanlar"][lid]
    kontrol("surucu --bag-onar: kayitli ilan 5/5 PASS (TEK cagri, gorsele yazim yok), kayitsiz ilan ATLA; DEVAM tamam, ILERLEME PASS",
            ilan_durum(RB, lid)["durum"] == "PASS" and ilan_durum(RB, "4570110641")["durum"] == "ATLA" and f.vi_cagri == vi0 + 1
            and len(f.bag) == 5 and dvk["adim"] == len(dvk["plan"]) and json.loads((d / "ILERLEME.json").read_text())["ilanlar"][lid]["durum"] == "PASS")
    rc, R5 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), durum_dir=d)
    kontrol("bag onarimi sonrasi kuru: ilan ZATEN", ilan_durum(R5, lid)["durum"] == "ZATEN")
    kontrol("bag_kur onarimi (hedef_n=9, DEVAM.json kaydi): TEK variation-images, 5/5 PASS, 9 gorsel", B["sonuc"] == "PASS"
            and B["bag_sayisi"] == 5 and B["gorsel"] == 9 and vi0 == 3 and {k: {x["listing_image_id"]: x["rank"] for x in f.img}[v]
                                                                                  for k, v in f.bag.items()} == V.RENK_SIRA)


def t_yazim_hatalari(hz):
    lid = "4570110121"
    for ad, kur, bek in (("yukleme 502 ama gorsel olustu: tekrar yok, PASS", lambda f: setattr(f, "yukle_hata", {3: (502, True, 0)}), "PASS"),
                         ("yukleme 500, gorsel olusmadi: ikinci yukleme YOK, DUR", lambda f: setattr(f, "yukle_hata", {3: (500, False, 0)}), "DUR"),
                         ("Etsy silinen kimligi yeniden verir: PASS, cift yukleme yok", lambda f: setattr(f, "kimlik_geri", True), "PASS"),
                         ("rank kaymasi (Etsy benzeri): PASS", lambda f: setattr(f, "kaydir", True), "PASS"),
                         ("sira ilk gecis oturmaz -> ikinci gecis, PASS", lambda f: setattr(f, "sira_yut", 3), "PASS"),
                         ("sira 2 geciste oturmaz -> DUR, son bag yazilmaz", lambda f: setattr(f, "sira_yut", 99), "DUR")):
        d, R, _ = kuru_ve_plan(hz)
        fakes = {x: sahte(x) for x in ILAN}; kur(fakes[lid])
        rc, R2, _ = yaz_kos(hz, d, R, fakes)
        f = fakes[lid]; s = ilan_durum(R2, lid)
        if bek == "PASS":
            ok = s["durum"] == "PASS" and tamam9(f, lid, hz) and set(f.tekrar) == {1}
        elif "yukleme" in ad:
            ok = s["durum"] == "DUR" and len(T.yuklemeler(f)) == 2 and len(f.tekrar) == 3 and set(f.tekrar) == {1}
        else:
            ok = s["durum"] == "DUR" and "sira 2 geciste" in s["neden"][0] and f.vi_cagri == 1 and len(f.bag) == 5
        kontrol(f"yazim: {ad}", ok)


def t_devam_kurtarma(hz):
    lid = "4570110641"
    d0, R0, _ = kuru_ve_plan(hz)
    n_adim = len(json.loads((d0 / "kuru" / "PLAN_V10.json").read_text())["girdiler"][lid]["adimlar"])
    kotu_k, kotu_h, n, nh = [], [], 0, 0
    for kes in sorted(set(range(8, 95)) | set(range(8, 200, 5))):   # kota: her istek (1'er); GET 503: 5'er
      if kes < 95:
          # kota: istek kes'te sert tabana duser -> DUR (hata kaydi yok) -> ayni plan ile devam tamamlar
          d, R, _ = kuru_ve_plan(hz)
          fakes = {x: sahte(x) for x in ILAN}; api = Coklu(fakes)
          fakes["4570110121"].img = [dict(rank=r, listing_image_id=9000 + r, alt_text="baska", url_fullxfull="u") for r in range(1, 18)]
          # 1. ilan BLOK (canli yedekten farkli) -> yalniz 2. ilan yazilir
          fakes[lid].kes = kes
          rc, R1 = kos(api, hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
          rc2, R2 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
          n += 1
          s1, s2 = ilan_durum(R1, lid), ilan_durum(R2, lid)
          if not (s2["durum"] in ("PASS", "ZATEN") and tamam9(fakes[lid], lid, hz) and min(b for _, b in fakes[lid].izler) == 5):
              kotu_k.append((kes, s1["durum"], (s1["neden"] or [""])[0][:50], s2["durum"], (s2["neden"] or [""])[0][:80]))
      if (kes - 8) % 5 == 0:
        # GET 503 (kota disi): otomatik devam yok, --kurtar tamamlar
        nh += 1
        d, R, _ = kuru_ve_plan(hz)
        fakes = {x: sahte(x) for x in ILAN}
        fakes[lid].get_hata = {max(1, kes // 3)}
        rc, R1 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
        fakes[lid].get_hata = set()
        dvr = (json.loads((d / "DEVAM.json").read_text()).get("ilanlar") or {}).get(lid) if (d / "DEVAM.json").exists() else None
        rc, R2 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
        rc, R3 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d,
                     kurtar=True)
        s1, s2, s3 = ilan_durum(R1, lid), ilan_durum(R2, lid), ilan_durum(R3, lid)
        if s1["durum"] == "DUR" and dvr and dvr.get("hata"):     # yazim basladiktan sonra hata: otomatik devam yok, kurtarma tamamlar
            ok = s2["durum"] == "DUR" and "otomatik devam yok" in s2["neden"][0] and s3["durum"] == "PASS"
        elif s1["durum"] == "DUR" and dvr and dvr.get("adim") == len(dvr.get("plan") or []):   # tum yazimlar bitti, son okumada hata
            ok = s2["durum"] == "ZATEN" and s3["durum"] == "ZATEN" and (json.loads((d / "ILERLEME.json").read_text())["ilanlar"][lid]["durum"]
                                                                        == "PASS")
        elif s1["durum"] == "DUR":                                # ilk yazimdan once hata: kayit yok, ikinci kosu temiz baslar
            ok = s2["durum"] == "PASS" and s3["durum"] == "ZATEN"
        else:
            ok = s1["durum"] == "PASS"
        if not (ok and tamam9(fakes[lid], lid, hz)):
            kotu_h.append((kes // 3, s1["durum"], (s1["neden"] or [""])[0][:50], s2["durum"], s3["durum"], (s3["neden"] or [""])[0][:80]))
    kontrol(f"her kesimde devam (kota tabani, {n} kesim, plan {n_adim} adim): ayni plan_damga ile tamamlanir, cift yukleme yok, "
            "renk bagi hicbir yazimdan sonra 5'in altina inmez (erken bag devamda tekrarlanir)"
            + (f" | kotu {kotu_k[:2]}" if kotu_k else ""), not kotu_k)
    kontrol(f"her kesimde kurtarma (GET 503, {nh} kesim): otomatik devam yok, --kurtar tamamlar" + (f" | kotu {kotu_h[:2]}" if kotu_h else ""),
            not kotu_h)
    # DEVAM baska planla
    d, R, _ = kuru_ve_plan(hz)
    fakes = {x: sahte(x) for x in ILAN}; fakes["4570110121"].kes = 40
    kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
    dv = json.loads((d / "DEVAM.json").read_text()); dv["ilanlar"]["4570110121"]["uretim_kosu"] = "1_aaaaaaaaaaaa"
    (d / "DEVAM.json").write_text(json.dumps(dv))
    rc, R2 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
    kontrol("DEVAM kaydi baska plan_damga ile baslamis -> BLOK, yazma yok", ilan_durum(R2, "4570110121")["durum"] == "BLOK"
            and "baska planla" in ilan_durum(R2, "4570110121")["neden"][0])
    rc, R3 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), durum_dir=d)
    kontrol("kuru: bitmemis DEVAM kaydi -> DEVAM (okuma / yazma yok)", ilan_durum(R3, "4570110121")["durum"] == "DEVAM")
    # --kurtar yalniz hata kaydi olan ilana: 1. ilan GET 503 ile hata kaydi, 2. ilan kayitsiz -> kurtar kosusunda ikisi de PASS
    d, R, _ = kuru_ve_plan(hz)
    fakes = {x: sahte(x) for x in ILAN}; fakes["4570110121"].get_hata = {30}
    kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d)
    fakes["4570110121"].get_hata = set()
    hata = bool(json.loads((d / "DEVAM.json").read_text())["ilanlar"]["4570110121"].get("hata"))
    rc, R4 = kos(Coklu(fakes), hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d,
                 kurtar=True)
    kontrol("--kurtar: hata kayitli ilan kurtarilir, kayitsiz ilan normal yazilir (iki ilan PASS)", hata and R4["sayilar"] == {"PASS": 2}
            and all(tamam9(fakes[x], x, hz) for x in ILAN))


def t_kota(hz):
    d, R, _ = kuru_ve_plan(hz)
    ek = R["en_kotu_ilan"]
    fakes = {x: sahte(x) for x in ILAN}
    rc, R2, api = yaz_kos(hz, d, R, fakes, kota=ek + 9)
    kontrol(f"kota: kalan {ek + 9} < en kotu ({ek - 4} + 4 kapi okumasi) + 10 -> ilan baslamaz, KALAN, yazma yok",
            all(ilan_durum(R2, x)["durum"] == "KALAN" for x in ILAN) and all(f.yaz == [] for f in fakes.values()) and rc == 0)
    fakes = {x: sahte(x) for x in ILAN}
    rc, R2, api = yaz_kos(hz, d, R, fakes, kota=ek + 10 + 80)
    kontrol("kota: 1. ilana yeter, 2. ilana yetmez -> 1. PASS, 2. KALAN (baslamadi, yazma yok)", ilan_durum(R2, "4570110121")["durum"] == "PASS"
            and ilan_durum(R2, "4570110641")["durum"] == "KALAN" and fakes["4570110641"].yaz == [])
    fakes = {x: sahte(x) for x in ILAN}
    rc, R2, api = yaz_kos(hz, d, R, fakes, kota=5)
    kontrol("kota esigi (kalan 5 < 10): ilan baslamaz, istek yok", all(ilan_durum(R2, x)["durum"] == "KALAN" for x in ILAN) and api.calls == 0)


def t_blok(hz):
    lid = "4570110121"
    base = int(lid[-3:]) * 100
    durumlar = (
        ("state draft", lambda f: setattr(f, "state", "draft"), "zorunlu", "active"),
        ("galeri 16", lambda f: f.img.pop(), "zorunlu", "17 beklenir"),
        ("renk bagi 4", lambda f: f.bag.pop("Warm Parchment"), "zorunlu", "5 renk"),
        ("bir renk iki gorselde", lambda f: f.bag_ek.append(dict(property_id=200, value_id=1, value="Midnight Blue", image_id=base + 1)), "zorunlu", "birden fazla"),
        ("bag property 513", lambda f: setattr(f, "bag_pid", 513), "zorunlu", "property 200"),
        ("bagli gorsel galeride yok", lambda f: f.bag.__setitem__("Deep Black", 1), "zorunlu", "galeride yok"),
        ("canli kume yedekten farkli", lambda f: f.img[0].__setitem__("listing_image_id", 4242), "zorunlu", "kimlik kumesi"),
        ("canli baglar yedekten farkli", lambda f: f.bag.update({"Deep Black": base + 15, "Pure White": base + 14}), "zorunlu", "yedekteki"),
        ("bes_x7 zorunlu, envanterde 5x7 yok", lambda f: setattr(f, "bes", False), "zorunlu", "5x7"),
        ("renk bagi kaydinda ad yok (cokme yok)", lambda f: f.bag_ek.append(dict(property_id=200, value_id=9, image_id=base + 2)), "zorunlu", "5 renk"),
    )
    for ad, boz, bx, metin in durumlar:
        d = Path(tempfile.mkdtemp()); fakes = {x: sahte(x) for x in ILAN}; boz(fakes[lid])
        rc, R = kos(Coklu(fakes), hz, d / "k", durum_dir=d, bes_x7=bx)
        s = ilan_durum(R, lid)
        kontrol(f"BLOK: {ad}", s["durum"] == "BLOK" and any(metin in n for n in s["neden"]) and fakes[lid].yaz == []
                and ilan_durum(R, "4570110641")["durum"] == "PLAN")
    d = Path(tempfile.mkdtemp()); fakes = {x: sahte(x, bes_x7=False) for x in ILAN}
    rc, R = kos(Coklu(fakes), hz, d / "k", durum_dir=d, bes_x7="yok")
    kontrol("bes_x7=yok ve envanterde 5x7 yok -> PLAN", R["sayilar"] == {"PLAN": 2})
    kontrol("bes_x7 girdisi zorunlu (varsayilan yok)", _arg_hata(["--hazir", "x", "--out", "y", "--kuru"]))
    # plan kilidi
    d, R, _ = kuru_ve_plan(hz)
    fakes = {x: sahte(x) for x in ILAN}; fakes[lid].img[3]["rank"], fakes[lid].img[4]["rank"] = 5, 4
    rc, R2, _ = yaz_kos(hz, d, R, fakes)
    kontrol("yazim: canli sira kuru plandan farkli -> BLOK, yazma yok; diger ilan PASS", ilan_durum(R2, lid)["durum"] == "BLOK"
            and "plandan farkli" in ilan_durum(R2, lid)["neden"][0] and fakes[lid].yaz == [] and ilan_durum(R2, "4570110641")["durum"] == "PASS")
    fakes = {x: sahte(x) for x in ILAN}
    api = Coklu(fakes); rc, R2 = kos(api, hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json",
                                     damga=R["plan_damga"][:-1] + ("0" if R["plan_damga"][-1] != "0" else "1"), durum_dir=d)
    kontrol("yazim: plan_damga sha256 ile ayni degil -> DUR, istek yok", rc == 9 and "plan_damga" in R2["hata"] and api.calls == 0)
    rc, R2 = kos(api, hz, Path(tempfile.mkdtemp()), kuru=False, plan=d / "kuru" / "PLAN_V10.json", damga=R["plan_damga"], durum_dir=d,
                 bes_x7="yok")
    kontrol("yazim: bes_x7 kuru plandan farkli -> DUR, istek yok", rc == 9 and api.calls == 0)
    kontrol("yazim: onay kelimesi / plan yoksa arguman DUR", _arg_hata(["--hazir", "x", "--out", "y", "--bes-x7", "yok", "--confirm", "ESKI23_GALERI",
                                                                         "--plan", "p", "--plan-damga", "1_aaaaaaaaaaaa"])
            and _arg_hata(["--hazir", "x", "--out", "y", "--bes-x7", "yok", "--confirm", "GALERI_V10"]))
    # 20 siniri
    eski = G.IMG_LIMIT; G.IMG_LIMIT = 17
    try:
        d2 = Path(tempfile.mkdtemp()); rc, R3 = kos(Coklu({x: sahte(x) for x in ILAN}), hz, d2 / "k", durum_dir=d2)
    finally:
        G.IMG_LIMIT = eski
    kontrol("gorsel siniri: plan en fazla 18 > sinir (17'ye indirildi) -> BLOK", all("gorsel (>" in ilan_durum(R3, x)["neden"][0] for x in ILAN))


def _arg_hata(argv):
    try:
        V.arg(argv)
    except SystemExit:
        return True
    return False


def t_drive_kopya(hz):
    d0 = Path(tempfile.mkdtemp()); r = d0 / "rclone"; say = d0 / "say"
    r.write_text(f"#!/bin/sh\nmkdir -p \"$(dirname \"$3\")\" && cp \"$2\" \"$3\" && echo x >> {say}\n"); r.chmod(r.stat().st_mode | stat.S_IEXEC)
    eski = os.environ["PATH"]; os.environ["PATH"] = f"{d0}:{eski}"
    try:
        d, R, _ = kuru_ve_plan(hz)
        rc, R2, _ = yaz_kos(hz, d, R, {x: sahte(x) for x in ILAN}, kok_=str(d0 / "drive"))
    finally:
        os.environ["PATH"] = eski
    n = len(say.read_text().split()) if say.exists() else 0
    kontrol(f"DEVAM her yazimdan once / sonra ilan basina Drive kopyasi ({n} kopya, 2 dosya)", R2["sayilar"] == {"PASS": 2} and n > 60
            and sorted(p.name for p in (d0 / "drive").iterdir()) == ["DEVAM_4570110121.json", "DEVAM_4570110641.json"]
            and "DEVAM_HEDEF" not in os.environ)


def main():
    kd, gd, yd = girdi_kur()
    t_renk()
    hz = t_liste(kd, gd, yd)
    _, hz, _ = liste(kd, gd, yd, yazim=True, durum="ONAYLI")
    t_akis(hz); t_yazim_hatalari(hz); t_kota(hz); t_blok(hz); t_devam_kurtarma(hz); t_drive_kopya(hz)
    n = sum(ok for _, ok in SONUC)
    print(f"galeri_v10 testleri: {n}/{len(SONUC)} PASS")
    shutil.rmtree(DEPO, ignore_errors=True)
    return 0 if n == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
