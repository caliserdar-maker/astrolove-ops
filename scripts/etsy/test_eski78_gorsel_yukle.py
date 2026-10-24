#!/usr/bin/env python3
"""eski78_gorsel_yukle sahte testi (ag yok, Serdar 24 Eki B4): ARIES_VIRGO benzeri canli galeri (17 gorsel, rank 1 iki kez, rank 12
yok, 4 renk bagi KORU gorsellerinde, WP bagi CIKAR gorselinde) -> hedef 17; on kosul, kota, 20 siniri, renk baglari tek cagri,
sira + alt metin, korunanlar, devam kaydi."""
import copy
import csv
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402

G.time.sleep = lambda s: None
RENK = {"Midnight Blue": (200, 1), "Deep Black": (200, 2), "Pure White": (200, 3), "Champagne Ivory": (200, 4), "Warm Parchment": (200, 5)}


def kur(tmp):
    """hedef 17: 1 KORU, 2 DEG, 3 ALT, 4 KORU, 5-9 DEG, 10 KORU, 11 12 DEG, 13-16 KORU (renk), 17 DEG (WP). Canli: 8 eslesen + 9 CIKAR."""
    hedef_islem = {1: "KORU", 2: "DEGISTIR", 3: "ALT", 4: "KORU", 5: "DEGISTIR", 6: "DEGISTIR", 7: "DEGISTIR", 8: "DEGISTIR",
                   9: "DEGISTIR", 10: "KORU", 11: "DEGISTIR", 12: "DEGISTIR", 13: "KORU", 14: "KORU", 15: "KORU", 16: "KORU", 17: "DEGISTIR"}
    canli_id = {1: 501, 3: 503, 4: 504, 10: 511, 13: 514, 14: 515, 15: 516, 16: 517}
    cikar = [601, 602, 605, 606, 607, 608, 609, 610, 613]
    rows, dosya = [], pathlib.Path(tmp) / "hedef"; dosya.mkdir()
    for s, isl in hedef_islem.items():
        ad = f"{s:02d}_{900 + s}.jpg"
        if isl == "DEGISTIR":
            (dosya / ad).write_bytes(b"jpg")
        rows.append(dict(hedef_sira=s, hedef_gorsel=ad, hedef_alt=f"alt {s}", islem=isl, simdi_sira="", simdi_id=canli_id.get(s, ""),
                         simdi_alt="", ncc="", fark="", en_yakin_hedef=""))
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira="", simdi_id=c, simdi_alt="", ncc="",
                  fark="", en_yakin_hedef="") for c in cikar]
    lp = pathlib.Path(tmp) / "LISTE.csv"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    man = dict(listing_id="4570155846", variation_images=[dict(value=ad, image_id=900 + s) for ad, s in
                                                         zip(RENK, (13, 14, 15, 16, 17))])
    mp = pathlib.Path(tmp) / "manifest.json"; mp.write_text(json.dumps(man))
    canli = [(1, 601), (1, 501), (2, 602), (3, 503), (4, 504), (5, 605), (6, 606), (7, 607), (8, 608), (9, 609), (10, 610),
             (11, 511), (13, 613), (14, 514), (15, 515), (16, 516), (17, 517)]
    bag = {"Midnight Blue": 514, "Deep Black": 515, "Pure White": 516, "Champagne Ivory": 517, "Warm Parchment": 613}
    return lp, dosya, mp, canli, bag


class Sahte:
    def __init__(self, canli, bag, kota=900, state="active"):
        self.img = [dict(rank=r, listing_image_id=i, alt_text=f"eski {i}", url_fullxfull=f"u{i}") for r, i in canli]
        self.bag = dict(bag); self.remaining = kota; self.calls = 0; self.state = state; self.yeni = 7000
        self.yaz = []; self.vi_cagri = 0; self.max_n = len(self.img); self.boz = None
        self.sert_taban = 430; self.sira_yut = 0   # sira_yut: ilk N rank cagrisi etkisiz (kapak_yukle_78 28 Eyl gozlemi)

    def kota_kapisi(self, ne):
        if self.remaining < 481:
            raise SystemExit(f"DUR: kota esigi: kalan {self.remaining} < 481 ({ne} baslamadi)")

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/images"):
            return {"results": copy.deepcopy(sorted(self.img, key=lambda x: (x["rank"], x["listing_image_id"])))}
        if path.endswith("/variation-images"):
            return {"results": [dict(property_id=200, value_id=RENK[k][1], value=k, image_id=v) for k, v in self.bag.items()]}
        if path.endswith("/inventory"):
            return {"products": [dict(sku="s", offerings=[dict(price=1)], property_values=[dict(property_id=200,
                    value_ids=[v[1] for v in RENK.values()], values=list(RENK))])]}
        if path.endswith("/videos"):
            return {"results": []}
        return dict(state=self.state, title="T", tags=["a"], description="D")

    def delete(self, path):
        self.calls += 1; iid = int(path.rsplit("/", 1)[1]); self.yaz.append(("sil", iid))
        if any(v == iid for v in self.bag.values()):
            raise SystemExit("HATA: renk bagli gorsel silindi (test)")
        self.img = [x for x in self.img if x["listing_image_id"] != iid]

    def post_file(self, path, files=None, data=None):
        self.calls += 1
        if "image" in (files or {}):
            self.yeni += 1; self.img.append(dict(rank=99, listing_image_id=self.yeni, alt_text=data["alt_text"], url_fullxfull="u"))
            self.max_n = max(self.max_n, len(self.img)); self.yaz.append(("yukle", self.yeni, tuple(sorted(data))))
            if self.boz == "yukle" and self.yeni == 7003:
                raise SystemExit("HATA: ag koptu (test)")
            return {"listing_image_id": self.yeni}
        iid = int(files["listing_image_id"][1]); rk = int(files["rank"][1])
        if self.sira_yut > 0:
            self.sira_yut -= 1; self.yaz.append(("sira_yutuldu", iid, rk)); return {"listing_image_id": iid}
        for x in self.img:
            if x["listing_image_id"] == iid:
                x["rank"] = rk; x["alt_text"] = files["alt_text"][1]
        self.yaz.append(("sira", iid, rk))
        return {"listing_image_id": iid}

    def post_json(self, path, body):
        self.calls += 1; self.vi_cagri += 1; self.yaz.append(("bag",))
        self.bag = {k: next(v["image_id"] for v in body["variation_images"] if v["value_id"] == RENK[k][1]) for k in RENK}


def kur_gercek(tmp):
    """24 Eki inceleme: duzeltilmis kartlarla gercek pilot plani 1 KORU / 16 DEGISTIR / 16 CIKAR; 4 renk bagi CIKAR gorsellerinde,
    WP bagsiz. Eski algoritma 20 gorsel sinirinda yarida duruyordu."""
    rows, dosya = [], pathlib.Path(tmp) / "hedef"; dosya.mkdir()
    for s in range(1, 18):
        ad = f"{s:02d}_{900 + s}.jpg"
        isl = "KORU" if s == 1 else "DEGISTIR"
        if isl == "DEGISTIR":
            (dosya / ad).write_bytes(b"jpg")
        rows.append(dict(hedef_sira=s, hedef_gorsel=ad, hedef_alt=f"alt {s}", islem=isl, simdi_sira="", simdi_id=501 if s == 1 else "",
                         simdi_alt="", ncc="", fark="", en_yakin_hedef=""))
    cikar = list(range(601, 617))
    rows += [dict(hedef_sira="", hedef_gorsel="", hedef_alt="", islem="CIKAR", simdi_sira="", simdi_id=c, simdi_alt="", ncc="",
                  fark="", en_yakin_hedef="") for c in cikar]
    lp = pathlib.Path(tmp) / "LISTE.csv"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    man = dict(listing_id="4570155846", variation_images=[dict(value=ad, image_id=900 + s) for ad, s in zip(RENK, (13, 14, 15, 16, 17))])
    mp = pathlib.Path(tmp) / "manifest.json"; mp.write_text(json.dumps(man))
    canli = [(1, 501)] + [(i + 1, c) for i, c in enumerate(cikar)]
    bag = {"Midnight Blue": 613, "Deep Black": 614, "Pure White": 615, "Champagne Ivory": 616}
    return lp, dosya, mp, canli, bag


def gercekci():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    g = sorted(api.img, key=lambda x: x["rank"])
    s.append(("gercekci pilot (1 KORU / 16 DEG / 16 CIKAR, 4 bag CIKAR'da): PASS, en fazla 17 gorsel, 5 bag yeni kartlarda",
              R["sonuc"] == "PASS" and api.max_n <= 17 and len(g) == 17 and api.vi_cagri == 1
              and all(api.bag[k] == g[s_ - 1]["listing_image_id"] for k, s_ in zip(RENK, (13, 14, 15, 16, 17)))))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag, kota=520); R = kos(api, tmp, lp, dosya, mp)
    s.append(("kota ihtiyaci: kalan 520 - tahmini istek < 430 -> yazmadan DUR", R["sonuc"] == "DUR" and "kota yetmez" in R["sorun"][0]
              and api.yaz == []))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    api = Sahte(canli, bag); api.sira_yut = 3; R = kos(api, tmp, lp, dosya, mp)
    s.append(("sira: ilk gecis oturmazsa ikinci gecis, PASS", R["sonuc"] == "PASS"
              and len([y for y in api.yaz if y[0] == "sira"]) == 17 + 14))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur_gercek(tmp)
    rows = list(csv.DictReader(open(lp, encoding="utf-8"))); rows[2]["hedef_alt"] = "original AstroLove design"
    with open(lp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("alt metinde Art'siz marka -> DUR, yazma yok", R["sonuc"] == "DUR" and "yasak" in R["sorun"][0] and api.yaz == []))
    a, mx = Y.adim_plani(17, list(range(601, 617)), {613, 614, 615, 616}, [dict(hedef_sira=s_, hedef_gorsel=f"{s_}") for s_ in
                                                                          range(2, 18)], {13, 14, 15, 16, 17})
    s.append(("adim plani: bag, 5 renk yuklemesinden hemen sonra; en fazla 17", mx == 17 and a.index(("bag",)) ==
              max(i for i, x in enumerate(a) if x == ("yukle", "17")) + 1))
    return s


def kos(api, tmp, lp, dosya, mp, kuru=False):
    try:
        return Y.bir_ilan(api, "1", "4570155846", lp, dosya, mp, pathlib.Path(tmp) / "out", kuru=kuru)
    except (Y.Dur, SystemExit) as e:
        return dict(sonuc="DUR", sorun=[str(e)])


def main():
    s = []
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp, kuru=True)
    s.append(("kuru: yazma yok, plan 9 cikar (1 bagli) / 9 yukle", R["sonuc"] == "KURU" and api.yaz == [] and api.vi_cagri == 0
              and len(R["plan"]["cikar"]) == 9 and R["plan"]["cikar_bagli"] == [613] and len(R["plan"]["yukle"]) == 9))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R = kos(api, tmp, lp, dosya, mp)
    g = sorted(api.img, key=lambda x: x["rank"])
    s.append(("PASS: 17 gorsel, rank 1..17, alt metin hedef, KORU kimlikleri korundu", R["sonuc"] == "PASS" and len(g) == 17
              and [x["rank"] for x in g] == list(range(1, 18)) and [x["alt_text"] for x in g] == [f"alt {i}" for i in range(1, 18)]
              and g[0]["listing_image_id"] == 501 and g[3]["listing_image_id"] == 504 and g[12]["listing_image_id"] == 514))
    s.append(("renk baglari tek cagri; WP yeni gorsele, 4 renk KORU kimliklerinde", api.vi_cagri == 1
              and api.bag["Warm Parchment"] == g[16]["listing_image_id"] and api.bag["Midnight Blue"] == 514
              and api.bag["Champagne Ivory"] == 517))
    s.append(("gorsel sayisi en fazla 18, bagli gorsel ancak bag cagrisindan sonra silindi", api.max_n <= 18
              and ("sil", 613) in api.yaz and api.yaz.index(("sil", 613)) > api.yaz.index(("bag",))))
    s.append(("yuklemede overwrite / rank yok (yalniz alt_text)", all(y[2] == ("alt_text",) for y in api.yaz if y[0] == "yukle")
              and len([y for y in api.yaz if y[0] == "yukle"]) == 9))
    # on kosul: canli galeri LISTE'den farkli
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli + [(18, 777)], bag); R = kos(api, tmp, lp, dosya, mp)
    s.append(("canli galeri LISTE'den farkli -> DUR, yazma yok", R["sonuc"] == "DUR" and "LISTE ile ayni degil" in R["sorun"][0]
              and api.yaz == []))
    api = Sahte(canli, bag, state="draft"); R = kos(api, tempfile.mkdtemp() and tmp, lp, dosya, mp)
    s.append(("state draft -> DUR, yazma yok", R["sonuc"] == "DUR" and "active" in R["sorun"][0] and api.yaz == []))
    api = Sahte(canli, bag, kota=470); R = kos(api, tmp, lp, dosya, mp)
    s.append(("kota esigi -> DUR, yazma yok", R["sonuc"] == "DUR" and "kota" in R["sorun"][0] and api.yaz == []))
    # devam: 3. yuklemede ag koparsa kayit kalir; ikinci kosu kaldigi yerden tamamlar
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); api.boz = "yukle"; R1 = kos(api, tmp, lp, dosya, mp)
    dv = json.loads((pathlib.Path(tmp) / "out" / "DEVAM_4570155846.json").read_text())
    api.boz = None
    # ag koptu ama gorsel Etsy'de olustu: kayitta yok -> canli galeri son kayittan farkli -> DUR (elle bakilir)
    R2 = kos(api, tmp, lp, dosya, mp)
    s.append(("devam: yanit dusen yukleme -> ilk kosu DUR + hata kaydi, ikinci kosu otomatik devam etmez (cift yukleme yok)",
              R1["sonuc"] == "DUR" and len(dv["yuklenen"]) == 2 and dv.get("hata") and R2["sonuc"] == "DUR"
              and "otomatik devam yok" in R2["sorun"][0] and len([y for y in api.yaz if y[0] == "yukle"]) == 3))
    tmp = tempfile.mkdtemp(); lp, dosya, mp, canli, bag = kur(tmp)
    api = Sahte(canli, bag); R1 = kos(api, tmp, lp, dosya, mp)
    n = api.calls; yaz = len(api.yaz); R2 = kos(api, tmp, lp, dosya, mp)
    s.append(("devam: tamamlanmis ilanda ikinci kosu yeniden yuklemez / silmez", R1["sonuc"] == "PASS" and R2["sonuc"] == "PASS"
              and len([y for y in api.yaz[yaz:] if y[0] in ("yukle", "sil")]) == 0))
    s += gercekci()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"eski78_gorsel_yukle testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
