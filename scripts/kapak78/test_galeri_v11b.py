#!/usr/bin/env python3
"""galeri v11b (Serdar 29 Eki kesin karar) yerel testi: sira 1 canli MB kapak DOKUNMA, 2-6 W02-W06, 7-10 W07-W10, W01 yok, renk baglari
MB 7 DB 8 PW 9 WP 10 (CI bagsiz). Ag / Drive / Etsy yok (sahte Etsy test_galeri_v10.S10 / Coklu, girdiler test_galeri_v11.girdi).
Senaryolar: liste HAZIR (1 DOKUNMA + 9 DEGISTIR + 8 CIKAR, 4 bag), satir 1 KULLANILMAZ iken --yazim HAZIR, canli galeri yedekten
farkli (v11 yazilmis) BLOK, --canli-dir yok cikis 2; kuru PLAN; yazim PASS (rank 1 kimligi / alt metni ayni, rank 1'e sil / yukle /
sira / alt yazimi yok, baglar 4); rank yok sayilir + sira POST'u bag siler -> sira yeniden, rank 1'e yazim yok, PASS."""
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import test_galeri_v11 as T11  # noqa: E402
import test_galeri_v10 as T10  # noqa: E402
import galeri_v11_liste as L11  # noqa: E402
import galeri_v11_yukle as Y11  # noqa: E402
import galeri_v10_yukle as V  # noqa: E402

V.profil_kur("v11b", Y11.ek_kapi)
SONUC = []
ILAN = T10.ILAN
LID = "4570110121"
BAG_B = {"Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def canli_kur(d, g, v11_yazilmis=()):
    """yedek-oku bicimi: B1 yedegiyle ayni (v10 durumu) + ilan state; v11_yazilmis ilanlarda 10 gorsel (rank 1 farkli)."""
    c = d / "canli"
    for y in Path(g["yd"]).iterdir():
        if not y.is_dir():
            continue
        j = json.loads((y / "GALERI.json").read_text()); j["ilan"] = dict(state="active")
        for x in j["gorseller"]:   # canli okuma = sahte Etsy'nin canli alt metni (S10: "eski <kimlik>")
            x["alt_text"] = f"eski {x['listing_image_id']}"
        if y.name.split("_")[0] in v11_yazilmis:
            base = int(y.name.split("_")[0][-3:]) * 100
            j["gorseller"] = [dict(rank=r, listing_image_id=base + 50 + r, alt_text=f"v11 {r}") for r in range(1, 11)]
        (c / y.name).mkdir(parents=True, exist_ok=True); (c / y.name / "GALERI.json").write_text(json.dumps(j))
    return c


def liste(d, g, canli, yazim=False, out="hazir"):
    args = ["--ciftler", str(T10.ciftler_csv(d)), "--alt", str(KOK / "data/pod/galeri_v11_alt.csv"), "--galeri-dir", str(g["gd"]),
            "--kapi-csv", str(d / "KAPI.csv"), "--kesim-dir", str(g["ks"]), "--yedek-dir", str(g["yd"]), "--yedek-ozet", str(g["yd"] / "OZET.md"),
            "--yedek-liste", str(g["ls"]), "--out", str(d / out), "--is", "2", "--kart-manifest", str(g["kart"]), "--profil", "v11b"]
    args += (["--canli-dir", str(canli)] if canli else []) + (["--yazim"] if yazim else [])
    rc = L11.main(args)
    return rc, json.loads((d / out / "LISTE_OZET.json").read_text()) if rc == 0 else None


def kos(api, hazir, out, kuru=True, plan=None, damga=""):
    args = ["--hazir", str(hazir), "--out", str(out), "--bes-x7", "zorunlu", "--kosu", "889",
            "--devam", str(out / "DEVAM.json"), "--ilerleme", str(out / "ILERLEME.json")]
    args += ["--kuru"] if kuru else ["--confirm", "GALERI_V11B", "--plan", str(plan), "--plan-damga", damga]
    a = V.arg(args)
    try:
        Y11.on_kapi(a, "v11b")
        rc = V.sonlandir(api, "1", a)
    except SystemExit as e:
        return 9, dict(hata=str(e.code))
    return rc, json.loads((Path(out) / "RAPOR.json").read_text())


def yaz(t0, hz, ad, **ayar):
    o = t0 / ad; o.mkdir()
    sh = {k: T11.sahte(k) for k in ILAN}
    for x in sh.values():
        for k, v in ayar.items():
            setattr(x, k, v)
    api = T10.Coklu(sh); rc, R = kos(api, hz, o); shutil.copyfile(o / "PLAN_V11B.json", t0 / f"PLAN_{ad}.json")
    rc, R = kos(api, hz, o, kuru=False, plan=t0 / f"PLAN_{ad}.json", damga=R["plan_damga"])
    return rc, R, sh[LID]


def main():
    t0 = Path(tempfile.mkdtemp(prefix="gv11b_"))
    try:
        d = t0 / "a"; d.mkdir(); g = T11.girdi(d); canli = canli_kur(d, g)
        rc, oz = liste(d, g, canli, yazim=True)
        kontrol("liste v11b: 2 ilan HAZIR, profil v11b, satir 1 KULLANILMAZ iken --yazim gecer",
                rc == 0 and oz["profil"] == "v11b" and oz["alt_sablon_durum"] == ["ONAYLI"]
                and all(x["durum"] == "HAZIR" for x in oz["ilanlar"].values()))
        rows = list(csv.DictReader(open(d / "hazir" / LID / f"LISTE_{LID}.csv")))
        base = int(LID[-3:]) * 100
        r1 = next(x for x in rows if x["hedef_sira"] == "1")
        kontrol("liste v11b: sira 1 DOKUNMA (canli rank 1 kimligi, alt metni canlidaki), 9 DEGISTIR, 8 CIKAR (rank 1 cikmaz)",
                r1["islem"] == "DOKUNMA" and r1["simdi_id"] == str(base + 1) and r1["hedef_alt"] == f"eski {base + 1}"
                and sum(x["islem"] == "DEGISTIR" for x in rows) == 9 and sum(x["islem"] == "CIKAR" for x in rows) == 8
                and str(base + 1) not in [x["simdi_id"] for x in rows if x["islem"] == "CIKAR"])
        m = json.loads((d / "hazir" / LID / "manifest.json").read_text())
        kontrol("liste v11b: renk baglari 4 (MB 7, DB 8, PW 9, WP 10; CI yok), W01 hedefte yok",
                {v["value"]: v["image_id"] for v in m["variation_images"]} == BAG_B and m["renk_bag_sayisi"] == 4
                and not (d / "hazir" / LID / "hedef" / "01_1.jpg").exists() and len(list((d / "hazir" / LID / "hedef").glob("*.jpg"))) == 9)
        d2 = t0 / "b"; d2.mkdir(); g2 = T11.girdi(d2); c2 = canli_kur(d2, g2, v11_yazilmis=(LID,))
        rc, oz2 = liste(d2, g2, c2)
        kontrol("liste v11b: canli galeri yedekten farkli (v11 yazilmis, MB kapak yok) -> BLOK",
                oz2["ilanlar"][LID]["durum"] == "BLOK" and any("ne B1 yedegi" in n for n in oz2["ilanlar"][LID]["neden"]))
        kontrol("liste v11b: --canli-dir yok -> cikis 2", liste(d2, g2, None, out="h2")[0] == 2)

        hz = d / "hazir"
        o1 = t0 / "o1"; o1.mkdir(); api = T10.Coklu({k: T11.sahte(k) for k in ILAN})
        rc, R = kos(api, hz, o1)
        p = [x for x in R.get("ilanlar") or [] if x.get("ilan") == LID]
        kontrol(f"kuru v11b: PLAN 2, ilan en az {p[0].get('en_az') if p else '?'} / en kotu {p[0].get('en_kotu') if p else '?'}",
                rc == 0 and R["sayilar"].get("PLAN") == 2)

        rc, R, f = yaz(t0, hz, "y1")
        gal = sorted(f.img, key=lambda x: x["rank"]); rk = {x["listing_image_id"]: x["rank"] for x in gal}
        kontrol("yazim v11b: PASS 2, 10 gorsel, rank 1 ayni kimlik ve alt metin", rc == 0 and R["sayilar"].get("PASS") == 2
                and len(gal) == 10 and gal[0]["listing_image_id"] == base + 1 and gal[0]["alt_text"] == f"eski {base + 1}")
        kontrol("yazim v11b: rank 1'e sil / sira / alt yazimi yok, 9 yukleme, 8 silme",
                not any(y[0] in ("sil", "sira") and y[1] == base + 1 for y in f.yaz if len(y) > 1)
                and f.n_yukle == 9 and len(f.silinenler) == 8)
        kontrol("yazim v11b: baglar MB 7, DB 8, PW 9, WP 10; CI bagsiz", {k: rk.get(v) for k, v in f.bag.items()} == BAG_B)
        ist = [x.get("istek") for x in R.get("ilanlar") or []]
        kontrol(f"yazim v11b: ilan basina istek {ist}", all(isinstance(x, int) for x in ist))

        rc, R, f = yaz(t0, hz, "y2", rank_yut=True, sira_bag_sil=True)
        gal = sorted(f.img, key=lambda x: x["rank"]); rk = {x["listing_image_id"]: x["rank"] for x in gal}
        kontrol("yazim v11b: rank yok sayilir + sira POST'u bag siler -> sira + bag yeniden, rank 1'e yazim yok, PASS",
                rc == 0 and R["sayilar"].get("PASS") == 2 and gal[0]["listing_image_id"] == base + 1
                and not any(y[0] == "sira" and y[1] == base + 1 for y in f.yaz if len(y) > 1)
                and {k: rk.get(v) for k, v in f.bag.items()} == BAG_B)
        # 29 Eki inceleme Y1: Etsy eksik rengin eski bagini birakirsa bag denemesinde DUR, yukleme / silme yok
        rc, R, f = yaz(t0, hz, "y3", bag_birlestir=True)
        kontrol("yazim v11b: 4 bagli POST eski CI bagini birakirsa DUR, yukleme 0, silme 0, galeri 9",
                rc != 0 and f.n_yukle == 0 and not f.silinenler and len(f.img) == 9)
        # 29 Eki inceleme O1: yukleme rank 1'e eklenirse silme / bag oncesi DUR, rank 1'e yazim yok, eski gorsel silinmez
        rc, R, f = yaz(t0, hz, "y4", rank_bir=True)
        kontrol("yazim v11b: yukleme rank 1'in onune gecerse silmeden once DUR, MB kapak silinmez, rank 1'e yazim yok",
                rc != 0 and not f.silinenler and any(x["listing_image_id"] == base + 1 for x in f.img)
                and not any(y[0] in ("sil", "sira") and y[1] == base + 1 for y in f.yaz if len(y) > 1))
        # 29 Eki inceleme D1: canli rank 1 MB'ye bagli degilse liste BLOK
        d3 = t0 / "c"; d3.mkdir(); g3 = T11.girdi(d3); c3 = canli_kur(d3, g3)
        p3 = next(c3.glob(f"{LID}_*")) / "GALERI.json"; j3 = json.loads(p3.read_text())
        for b in j3["baglar"]:
            if b["value"] == "Midnight Blue":
                b["image_id"] = base + 2
        p3.write_text(json.dumps(j3))
        rc, oz3 = liste(d3, g3, c3)
        kontrol("liste v11b: canli rank 1 MB'ye bagli degil -> BLOK", oz3["ilanlar"][LID]["durum"] == "BLOK"
                and any("Midnight Blue bagli" in n for n in oz3["ilanlar"][LID]["neden"]))
        # O2: bag_onar yolu DOKUNMA satirini taniyor (basarili yazimdan sonra bag modu okuma PASS)
        import eski78_gorsel_yukle as Y
        rc, R, f = yaz(t0, hz, "y5")
        dv = next((t0 / "y5" / "ilanlar").glob(f"DEVAM_{LID}.json"))
        Rb = Y.bag_kur(T10.Coklu({LID: f}), "1", LID, hz / LID / f"LISTE_{LID}.csv", hz / LID / "manifest.json", dv, t0 / "y5b",
                       yaz=False, hedef_n=10)
        kontrol(f"bag_kur (bag_onar) DOKUNMA satiriyla calisir, okuma {Rb['sonuc']}", Rb["sonuc"] == "PASS")
    finally:
        shutil.rmtree(t0, ignore_errors=True)
    bad = [a for a, ok in SONUC if not ok]
    print(f"galeri_v11b testleri: {len(SONUC) - len(bad)}/{len(SONUC)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
