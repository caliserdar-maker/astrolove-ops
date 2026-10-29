#!/usr/bin/env python3
"""galeri v11 (galeri_v11_liste + galeri_v11_yukle = galeri_v10_yukle profil v11 + eski78 bir_ilan hedef_n=10) yerel testi.
Ag / Drive / Etsy yok (sahte Etsy: test_galeri_v10.S10 / Coklu; canli 9 gorsel = v10). Poster kesimleri depodaki gercek CL renk kartlarindan
(data/pod/cl_galeri_final19 17 PW, 18 CI; KUTU kirpimi) uretilir; W01 / W09 = kesim siyah cerceveyle oda sahnesine (888, 588, 1226 x 1538).
Senaryolar: liste HAZIR; kart manifesti yok / B3 sha farkli / B3 FAIL / CI-PW yer degistirmis / yedek 17 gorsel / yazim + TASLAK BLOK;
yukleyici: TASLAK alt metin ve v10 listesi Etsy isteginden once DUR; kuru PLAN (istek tahmini n=10) + boy UYGULANAMAZ notu;
aciklamada cerceve satiri yok BLOK; boy sayisi farkli BLOK; v10 canli (17) BLOK; yazim 9 -> 10 PASS (baglar CI 1, MB 7, DB 8, PW 9,
WP 10; en fazla 10 gorsel); ikinci kosu ZATEN; v10 planiyla yazim DUR."""
import copy
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import test_galeri_v10 as T10  # noqa: E402  (S10, Coklu; G.time.sleep etkisiz)
import galeri_v10_liste as L  # noqa: E402
import galeri_v11_liste as L11  # noqa: E402
import galeri_v11_yukle as Y11  # noqa: E402
import galeri_v10_yukle as V  # noqa: E402

V.profil_kur("v11", Y11.ek_kapi)
SONUC = []
ILAN = T10.ILAN
CL = KOK / "data/pod/cl_galeri_final19"
V10_RANK = {"Midnight Blue": 1, "Deep Black": 6, "Pure White": 7, "Champagne Ivory": 8, "Warm Parchment": 9}
ACIKLAMA = "Personalized poster.\n\nFrames shown in photos are for display only and are not included. Prints ship unframed.\n"


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def sahne(kesim, yol, isaret):
    im = Image.new("RGB", L.BOYUT, (226, 216, 202)); d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 888, 588, 888 + 1226, 588 + 1538
    d.rectangle((x0 - 30, y0 - 30, x1 + 30, y1 + 30), fill=(14, 14, 14))
    im.paste(Image.open(kesim).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    d.text((40, 40), isaret, fill=(0, 0, 0)); im.save(yol, "JPEG", quality=95)


def duz(yol, renk, isaret):
    im = Image.new("RGB", L.BOYUT, renk); ImageDraw.Draw(im).text((60, 60), isaret, fill=(255, 255, 255)); im.save(yol, "JPEG", quality=92)


def girdi(d, takas=False, kapi_bozuk=None, kart=True, fb=None, yedek17=False):
    gd, kd, yd, ks = d / "galeri", d / "kart", d / "yedek", d / "kesim"
    for x in (gd, kd, yd, ks):
        x.mkdir(parents=True, exist_ok=True)
    kapi = []
    for lid, (cift, a, b) in ILAN.items():
        for on, f in (("CI", "18_renk_champagne_ivory.jpg"), ("PW", "17_renk_pure_white.jpg")):
            im = Image.open(CL / f).convert("RGB").crop(L.KUTU); ImageDraw.Draw(im).text((20, 20), cift, fill=(0, 0, 0))
            im.save(ks / f"{on}_{cift}.png")
        sahne(ks / f"{'PW' if takas else 'CI'}_{cift}.png", gd / f"{cift}_W01_KAPAK.jpg", f"W01 {cift}")
        sahne(ks / f"{'CI' if takas else 'PW'}_{cift}.png", gd / f"{cift}_W09_PW.jpg", f"W09 {cift}")
        for ad, renk in (("W07_MB", (18, 26, 60)), ("W08_DB", (20, 20, 22)), ("W10_WP", (236, 222, 196))):
            duz(gd / f"{cift}_{ad}.jpg", renk, f"{ad} {cift}")
        for ad in L11.CANVA.values():
            p = gd / f"{cift}_{ad}.jpg"
            kapi.append(dict(cift=cift, ad=ad, dosya=p.name, sha256=L.sha(p), durum="PASS"))
        for s in (2, 3, 5, 6):
            duz(kd / f"{cift}_W{s:02d}.jpg", (40 + 20 * s, 90, 120), f"W{s:02d} {cift}")
        y = yd / f"{lid}_{cift}"; y.mkdir(exist_ok=True)
        base = int(lid[-3:]) * 100
        n = 17 if yedek17 else 9
        gor = [dict(rank=r, listing_image_id=base + r, full_width=3000, full_height=2250, url_fullxfull="u", alt_text=f"eski {r}")
               for r in range(1, n + 1)]
        bag = [dict(property_id=200, value_id=T10.VID[k], value=k, image_id=base + r) for k, r in V10_RANK.items()]
        (y / "GALERI.json").write_text(json.dumps(dict(listing_id=lid, cift=cift, gorseller=gor, baglar=bag, videolar=[])))
        for g in gor:
            (y / f"r{g['rank']}_{g['listing_image_id']}.jpg").write_bytes(b"\xff\xd8\xff yedek")
    duz(kd / "ORTAK_W04.jpg", (60, 60, 60), "W04 ORTAK")
    if kapi_bozuk:
        for k in kapi:
            if k["dosya"] == kapi_bozuk[0]:
                k.update(kapi_bozuk[1])
    with open(d / "KAPI.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "ad", "dosya", "sha256", "durum"]); w.writeheader(); w.writerows(kapi)
    kartlar = {"ORTAK": {"4": "ORTAK_W04.jpg"}}
    kartlar.update({c: {str(s): f"{c}_W{s:02d}.jpg" for s in (2, 3, 5, 6)} for c, _, _ in ILAN.values()})
    (kd / "KART_MANIFEST.json").write_text(json.dumps(dict(format_boy_sayisi=fb, kartlar=kartlar)))
    (yd / "OZET.md").write_text("| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n"
                                + "".join(f"| {lid} | {c} | {17 if yedek17 else 9} | PASS |  |\n" for lid, (c, _, _) in ILAN.items()))
    ls = d / "yedek_ls.json"
    ls.write_text(json.dumps([dict(Path=x.relative_to(yd).as_posix(), Size=x.stat().st_size) for x in sorted(yd.rglob("*.jpg"))]))
    return dict(gd=gd, kd=kd, yd=yd, ks=ks, ls=ls, kart=kd / "KART_MANIFEST.json" if kart else None)


def alt_csv(d, durum):
    p = d / "alt.csv"
    t = (KOK / "data/pod/galeri_v11_alt.csv").read_text()
    p.write_text(t.replace(",TASLAK\n", f",{durum}\n").replace(",ONAYLI\n", f",{durum}\n")); return p


def liste(d, g, durum="ONAYLI", yazim=False):
    args = ["--ciftler", str(T10.ciftler_csv(d)), "--alt", str(alt_csv(d, durum)), "--galeri-dir", str(g["gd"]), "--kapi-csv", str(d / "KAPI.csv"),
            "--kesim-dir", str(g["ks"]), "--yedek-dir", str(g["yd"]), "--yedek-ozet", str(g["yd"] / "OZET.md"), "--yedek-liste", str(g["ls"]),
            "--out", str(d / "hazir"), "--is", "2"] + (["--kart-manifest", str(g["kart"])] if g["kart"] else []) + (["--yazim"] if yazim else [])
    rc = L11.main(args)
    return rc, json.loads((d / "hazir" / "LISTE_OZET.json").read_text()) if rc == 0 else None


class S11(T10.S10):
    def __init__(self, lid, *a, boy=14, aciklama=ACIKLAMA, **k):
        super().__init__(lid, *a, **k); self.boy, self.acik = boy, aciklama

    def get(self, path, params=None, ok404=False):
        r = super().get(path, params, ok404)
        if path.endswith("/inventory"):
            r = copy.deepcopy(r)
            r["products"] += [dict(sku=f"b{i}", offerings=[dict(price=1)], property_values=[dict(property_id=513, value_ids=[100 + i], values=[f"{i}x{i}"])])
                              for i in range(self.boy - 1)]     # S10 bir boy (5x7) ekler
        elif "/listings/" in path and path.rstrip("/").split("/")[-1].isdigit():
            r = dict(r, description=self.acik)
        return r


def sahte(lid, canli_n=9, **k):
    base = int(lid[-3:]) * 100
    s = S11(lid, [(r, base + r) for r in range(1, canli_n + 1)], {kk: base + r for kk, r in V10_RANK.items()}, **k)
    s.max_n = 0
    return s


def kos(api, hazir, out, kuru=True, plan=None, damga=""):
    args = ["--hazir", str(hazir), "--out", str(out), "--bes-x7", "zorunlu", "--kosu", "888",
            "--devam", str(out / "DEVAM.json"), "--ilerleme", str(out / "ILERLEME.json")]
    args += ["--kuru"] if kuru else ["--confirm", "GALERI_V11", "--plan", str(plan), "--plan-damga", damga]
    a = V.arg(args)
    try:
        Y11.on_kapi(a)
        rc = V.sonlandir(api, "1", a)
    except SystemExit as e:
        return 9, dict(hata=str(e.code))
    return rc, json.loads((Path(out) / "RAPOR.json").read_text())


def main():
    t0 = Path(tempfile.mkdtemp(prefix="gv11_"))
    d = t0 / "a"; d.mkdir(); g = girdi(d)
    rc, oz = liste(d, g, yazim=True)
    kontrol("liste: 2 ilan HAZIR, profil v11", rc == 0 and all(x["durum"] == "HAZIR" for x in oz["ilanlar"].values()) and oz["profil"] == "v11")
    lid = "4570110121"
    m = json.loads((d / "hazir" / lid / "manifest.json").read_text())
    kontrol("liste: renk baglari CI 1, MB 7, DB 8, PW 9, WP 10; 10 hedef; yedek 9",
            {v["value"]: v["image_id"] for v in m["variation_images"]} == L11.RENK_SIRA and len(m["hedef"]) == 10 and len(m["yedek_ids"]) == 9)
    r = oz["ilanlar"][lid]["renk"]
    kontrol(f"liste: W01 CI / W09 PW renk PASS (CI kendi {r['Champagne Ivory']['kendi']} diger {r['Champagne Ivory']['diger']})",
            r["Champagne Ivory"]["sonuc"] == "PASS" and r["Pure White"]["sonuc"] == "PASS")
    rows = list(csv.DictReader(open(d / "hazir" / lid / f"LISTE_{lid}.csv")))
    kontrol("liste: 10 DEGISTIR + 9 CIKAR", sum(x["islem"] == "DEGISTIR" for x in rows) == 10 and sum(x["islem"] == "CIKAR" for x in rows) == 9)

    def man_csv(kd, bozuk=None):                                # wa-kart-v11 MANIFEST_W02_W06 (Merkez 29 Eki: ayri JSON yok)
        km = json.loads((kd / "KART_MANIFEST.json").read_text()); ad = {"2": "W02_SEMBOL", "3": "W03_KISISEL", "4": "W04_FORMAT",
                                                                          "5": "W05_SUREC", "6": "W06_GENEL"}
        sat = [dict(cift=c, ad=ad[s], dosya=f, sha256=("0" * 64 if f == bozuk else L.sha(kd / f)), boyut=1, kaynak="t", durum="PASS")
               for c, k in km["kartlar"].items() for s, f in k.items()]
        with open(kd / "MANIFEST_W02_W06_p0.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(sat[0])); w.writeheader(); w.writerows(sat)
    man_csv(g["kd"])
    args = ["--ciftler", str(T10.ciftler_csv(d)), "--alt", str(alt_csv(d, "ONAYLI")), "--galeri-dir", str(g["gd"]), "--kapi-csv", str(d / "KAPI.csv"),
            "--kesim-dir", str(g["ks"]), "--yedek-dir", str(g["yd"]), "--yedek-ozet", str(g["yd"] / "OZET.md"), "--yedek-liste", str(g["ls"]),
            "--out", str(d / "hazir_csv"), "--is", "2", "--kart-manifest", str(g["kd"]), "--format-boy", "14"]
    rc = L11.main(args); oz2 = json.loads((d / "hazir_csv" / "LISTE_OZET.json").read_text())
    kontrol("liste: kart klasoru MANIFEST_W02_W06 csv + --format-boy 14 -> 2 HAZIR, format 14",
            rc == 0 and all(x["durum"] == "HAZIR" for x in oz2["ilanlar"].values()) and oz2["format_boy_sayisi"] == 14)
    man_csv(g["kd"], bozuk="ORTAK_W04.jpg"); L11.main(args[:-6] + ["--out", str(d / "hazir_csv2"), "--is", "2", "--kart-manifest", str(g["kd"]),
                                                                   "--format-boy", "14"])
    oz3 = json.loads((d / "hazir_csv2" / "LISTE_OZET.json").read_text())
    kontrol("liste: kart dosyasi MANIFEST sha256'sindan farkli -> BLOK",
            all(x["durum"] == "BLOK" and any("kart MANIFEST sha256" in n_ for n_ in x["neden"]) for x in oz3["ilanlar"].values()))
    man_csv(g["kd"])

    def blok(ad, d_, g_, ara, **kw):
        rc_, oz_ = liste(d_, g_, **kw)
        n = oz_["ilanlar"][lid]["neden"] if oz_ else ["liste cikisi"]
        kontrol(f"liste BLOK: {ad}", oz_ and oz_["ilanlar"][lid]["durum"] == "BLOK" and any(ara in x for x in n))
    d2 = t0 / "b"; d2.mkdir(); g2 = girdi(d2, kart=False); blok("kart manifesti yok", d2, g2, "bilgi kartlari yok")
    d3 = t0 / "c"; d3.mkdir(); g3 = girdi(d3, kapi_bozuk=("AQUARIUS_AQUARIUS_W08_DB.jpg", dict(sha256="0" * 64))); blok("B3 sha farkli", d3, g3, "B3 kapisindan gecen")
    d4 = t0 / "d"; d4.mkdir(); g4 = girdi(d4, kapi_bozuk=("AQUARIUS_AQUARIUS_W01_KAPAK.jpg", dict(durum="ESIK_YOK"))); blok("B3 ESIK_YOK", d4, g4, "PASS degil (ESIK_YOK)")
    d5 = t0 / "e"; d5.mkdir(); g5 = girdi(d5, takas=True); blok("CI / PW poster yer degistirmis", d5, g5, "renk Champagne Ivory")
    d6 = t0 / "f"; d6.mkdir(); g6 = girdi(d6, yedek17=True); blok("yedek 17 gorsel", d6, g6, "9 beklenir")
    d7 = t0 / "g"; d7.mkdir(); g7 = girdi(d7); blok("yazim + TASLAK", d7, g7, "ONAYLI degil", durum="TASLAK", yazim=True)

    # yukleyici
    dt = t0 / "t"; dt.mkdir(); gt = girdi(dt); liste(dt, gt, durum="TASLAK")
    api = T10.Coklu({k: sahte(k) for k in ILAN})
    rc, R = kos(api, dt / "hazir", t0 / "o0")
    kontrol("yukle: TASLAK alt metin -> Etsy isteginden once DUR", rc == 9 and "TASLAK" in R["hata"] and api.calls == 0)
    hz = d / "hazir"
    o1 = t0 / "o1"; o1.mkdir()
    api = T10.Coklu({k: sahte(k) for k in ILAN})
    rc, R = kos(api, hz, o1)
    ok = rc == 0 and R["sayilar"].get("PLAN") == 2
    s0 = next(x for x in R["ilanlar"] if x["ilan"] == lid)
    kontrol(f"yukle kuru: 2 PLAN, en kotu {s0['en_kotu']} en az {s0['en_az']}, boy UYGULANAMAZ notu", ok and s0["en_az"] and
            any("UYGULANAMAZ" in x for x in s0["neden"]))
    plan = json.loads((o1 / "PLAN_V11.json").read_text())
    kontrol("yukle kuru: PLAN_V11.json profil v11, plan_damga", plan["profil"] == "v11" and plan["plan_damga"] == R["plan_damga"])
    o2 = t0 / "o2"; o2.mkdir()
    api = T10.Coklu({lid: sahte(lid, aciklama="Poster.\n"), "4570110641": sahte("4570110641", boy=12)})
    d8 = t0 / "h"; d8.mkdir(); g8 = girdi(d8, fb=14); liste(d8, g8)
    rc, R = kos(api, d8 / "hazir", o2)
    nd = {x["ilan"]: x for x in R["ilanlar"]}
    kontrol("yukle kuru: aciklamada cerceve satiri yok BLOK", nd[lid]["durum"] == "BLOK" and "cerceve satiri yok" in nd[lid]["neden"][0])
    kontrol("yukle kuru: envanter boy 12 != format karti 14 BLOK", nd["4570110641"]["durum"] == "BLOK"
            and any("boy sayisi 12 != format karti 14" in x for x in nd["4570110641"]["neden"]))
    o3 = t0 / "o3"; o3.mkdir()
    api = T10.Coklu({k: sahte(k, canli_n=17) for k in ILAN})
    rc, R = kos(api, hz, o3)
    kontrol("yukle kuru: canli 17 (v10 oncesi) BLOK", all(x["durum"] == "BLOK" for x in R["ilanlar"]) and "9 beklenir" in R["ilanlar"][0]["neden"][0])
    # yazim
    o4 = t0 / "o4"; o4.mkdir()
    sh = {k: sahte(k) for k in ILAN}
    api = T10.Coklu(sh)
    rc, R = kos(api, hz, o4)
    pd = R["plan_damga"]
    shutil.copyfile(o4 / "PLAN_V11.json", t0 / "PLAN_V11.json")
    rc, R = kos(api, hz, o4, kuru=False, plan=t0 / "PLAN_V11.json", damga=pd)
    if "hata" in R:
        print("YAZIM HATA:", R["hata"]); R = dict(R, istek=None, sayilar={})
    f = sh[lid]
    gal = sorted(f.img, key=lambda x: x["rank"])
    rk = {x["listing_image_id"]: x["rank"] for x in gal}
    kontrol(f"yazim: 2 PASS, 10 gorsel, rank 1..10 (istek {R['istek']})", rc == 0 and R["sayilar"].get("PASS") == 2 and len(gal) == 10
            and [x["rank"] for x in gal] == list(range(1, 11)))
    kontrol("yazim: baglar CI 1, MB 7, DB 8, PW 9, WP 10", {k: rk.get(v) for k, v in f.bag.items()} == L11.RENK_SIRA)
    kontrol(f"yazim: en fazla {f.max_n or '?'} gorsel (<= 20), eski 9 kimlik silindi", all(x["listing_image_id"] >= 7000 for x in gal)
            and len(f.silinenler) == 9)
    alt1 = gal[0]["alt_text"]
    kontrol("yazim: kapak alt metni CI", "Champagne Ivory" in alt1 and "Aquarius and Aquarius" in alt1)
    ist = [x.get("istek") for x in R.get("ilanlar") or []]
    kontrol(f"yazim yalin: ilan basina istek {ist} <= 31 (Merkez 29 Eki karar 3; eski akis en az 71)", ist and max(ist) <= 31)
    kontrol("yazim yalin: yukleme rank + alt metinle, sira POST'u yok", f.n_yukle == 10 and not any(y[0] in ("sira", "sira_yutuldu") for y in f.yaz))
    rc, R = kos(api, hz, o4)
    kontrol("ikinci kuru: ZATEN 2", R["sayilar"].get("ZATEN") == 2)
    # yalin: Etsy yuklemedeki rank'i uygulamazsa sira_kontrol duzeltir
    o6 = t0 / "o6"; o6.mkdir(); sh6 = {k: sahte(k) for k in ILAN}
    for x in sh6.values():
        x.rank_yut = True
    api6 = T10.Coklu(sh6); rc, R = kos(api6, hz, o6); shutil.copyfile(o6 / "PLAN_V11.json", t0 / "PLAN6.json")
    rc, R = kos(api6, hz, o6, kuru=False, plan=t0 / "PLAN6.json", damga=R["plan_damga"])
    g6 = sorted(sh6[lid].img, key=lambda x: x["rank"])
    kontrol("yalin: rank yok sayilirsa sira_kontrol sira + alt metin yazar, PASS", rc == 0 and R["sayilar"].get("PASS") == 2
            and [x["alt_text"] for x in g6][0].startswith("Aquarius and Aquarius") and len(g6) == 10)
    # yalin: silmeler sirasinda kota kesintisi -> devam kosusu kaldigi yerden (cift yukleme yok)
    o7 = t0 / "o7"; o7.mkdir(); sh7 = {k: sahte(k) for k in ILAN}
    api7 = T10.Coklu(sh7); rc, R = kos(api7, hz, o7); shutil.copyfile(o7 / "PLAN_V11.json", t0 / "PLAN7.json"); pd7 = R["plan_damga"]
    sh7[lid].kes = api7.calls + 19                       # on okuma 1 + 10 yukleme + bag + birkac silme sonra kota 9
    rc, R = kos(api7, hz, o7, kuru=False, plan=t0 / "PLAN7.json", damga=pd7)
    ara = len(sh7[lid].img)
    api7.remaining = 100000
    rc2, R2 = kos(api7, hz, o7, kuru=False, plan=t0 / "PLAN7.json", damga=pd7)
    g7 = sorted(sh7[lid].img, key=lambda x: x["rank"])
    kontrol(f"yalin: kesinti ({ara} gorselde) sonrasi devam PASS, 10 gorsel, yukleme 10 (cift yok)",
            rc != 0 and rc2 == 0 and R2["sayilar"].get("PASS") == 2 and len(g7) == 10 and sh7[lid].n_yukle == 10
            and {k: {x["listing_image_id"]: x["rank"] for x in g7}.get(v) for k, v in sh7[lid].bag.items()} == L11.RENK_SIRA)
    p10 = json.loads((t0 / "PLAN_V11.json").read_text()); p10.pop("profil"); (t0 / "PLAN_V10x.json").write_text(json.dumps(p10))
    rc, R = kos(T10.Coklu({k: sahte(k) for k in ILAN}), hz, t0 / "o5", kuru=False, plan=t0 / "PLAN_V10x.json", damga=pd)
    kontrol("yazim: v10 planiyla DUR", rc == 9 and "profili v10" in R["hata"])
    bad = [a for a, ok in SONUC if not ok]
    print(f"\ngaleri_v11 testleri: {len(SONUC) - len(bad)}/{len(SONUC)} PASS" + (f" | FAIL: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
