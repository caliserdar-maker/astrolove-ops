#!/usr/bin/env python3
"""kagit_tara sahte testi (ag yok): desenler, oku (magaza/ilan/alt metin bulgulari hemen yazilir, ilan basina kota kapisi,
gorsel indirme, yazma yok), ocr (satir satir yazim, sure siniri -> yarim)."""
import csv
import json
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kagit_tara as K  # noqa: E402


class Sahte:
    def __init__(self):
        self.remaining, self.calls, self.kapi = 3000, 0, []

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/about"):
            return None
        if path.endswith("/sections"):
            return {"results": [{"shop_section_id": 9, "title": "Zodiac Couple Posters"}]}
        if path.endswith("/listings") and "shops" in path:
            return {"count": 2, "results": [{"listing_id": 1}, {"listing_id": 2}]}
        if path.startswith("/shops/"):
            return {"announcement": "Printed on Hahnemühle Photo Rag", "sale_message": "Thanks", "policy_refunds": "museum quality"}
        if path == "/listings/batch":
            return {"results": [{"listing_id": 1, "shop_section_id": 9, "title": "T", "description": "premium matte art paper",
                                 "tags": ["a"], "materials": ["matte art paper"]},
                                {"listing_id": 2, "shop_section_id": 9, "title": "T", "description": "Prodigi giclée", "tags": [],
                                 "materials": ["cotton"]}]}
        if path.endswith("/images"):
            lid = path.split("/")[2]
            return {"results": [{"rank": 1, "listing_image_id": int(lid) * 10, "alt_text": "Fine art paper detail, 100 percent cotton",
                                 "url_570xN": f"u{lid}"}]}
        raise AssertionError(path)

    def kota_kapisi(self, ne):
        self.kapi.append(ne)

    def __getattr__(self, ad):
        raise AssertionError(f"yazma cagrisi: {ad}")


def jpg(yol, renk):
    from PIL import Image
    Image.new("RGB", (80, 80), renk).save(yol)


def main():
    s = []
    s.append(("desen", K.bul("Hahnemühle Photo Rag 308 gsm, giclée, хлопковой, Prodigi, музейному") ==
              sorted(["hahnemühle", "photo rag", "308", "giclée", "хлопковой", "prodigi", "музейному"])))
    s.append(("desen: OCR hatali yazim (Halnemuhle) yakalanir", K.bul("Halnemuhle Photo Rag") == ["halnemuhle", "photo rag"]))
    s.append(("desen: matte art paper temiz", K.bul("premium matte art paper, long-lasting inks") == []))
    api = Sahte()
    K.B.Etsy = lambda store: api
    K.B.TokenStore = type("T", (), {"__init__": lambda self, *a: None, "needs_refresh": lambda self: False})
    K.indir = lambda url, yol: jpg(yol, "white") if url != "u2" else (_ for _ in ()).throw(OSError("404"))
    os.environ.update(TOKEN_FILE="x", ETSY_SHOP_ID="7")
    out = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["k", "--mod", "oku", "--out", str(out)]
    K.main()
    oz = json.loads((out / "OKU_OZET.json").read_text())
    rows = list(csv.DictReader(open(out / "KAGIT_METIN.csv", encoding="utf-8")))
    s.append(("oku: magaza duyuru + politika", {r["alan"] for r in rows if r["kaynak"] == "magaza"} == {"announcement", "policy_refunds"}))
    s.append(("oku: ilan 2 aciklama + materials", {(r["alan"], r["terim"]) for r in rows if r["kaynak"] == "ilan"} >=
              {("description", "prodigi"), ("description", "giclée"), ("materials", "cotton")}))
    s.append(("oku: alt metin her ilanda", oz["metin_bulgu"]["alt_metin"] == 4 and len({r["listing_id"] for r in rows
              if r["kaynak"] == "alt_metin"}) == 2))
    s.append(("oku: ilan basina kota kapisi", api.kapi == ["ilan 1", "ilan 2"]))
    s.append(("oku: gorsel listesi + indirme (1 hata sayilir)", oz["gorsel"] == 2 and oz["indirilen"] == 1 and len(oz["indirme_hata"]) == 1
              and (out / "GORSEL" / "1_01_10.jpg").exists()))
    s.append(("oku: about ucu yok", oz["about_ucu"].startswith("yok")))
    # ocr asamasi: Etsy yok
    K.B.Etsy = lambda store: (_ for _ in ()).throw(AssertionError("ocr Etsy kullanmamali"))
    jpg(out / "GORSEL" / "2_01_20.jpg", "black")
    ref = out / "ref.jpg"; jpg(ref, "white")
    K.ocr = lambda b: "Fine Art Paper Hahnemuhle" if b == (out / "GORSEL" / "2_01_20.jpg").read_bytes() else "hello"
    o2 = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["k", "--mod", "ocr", "--kaynak", str(out), "--out", str(o2), "--ref", str(ref)]
    K.main()
    oo = json.loads((o2 / "OCR_OZET.json").read_text())
    r2 = list(csv.DictReader(open(o2 / "GORSEL_OCR.csv", encoding="utf-8")))
    s.append(("ocr: 2 gorsel, bulgu yalniz ilan 2, satirlar CSV'de", oo["islenen"] == 2 and oo["ocr_bulgu_ilan"] == 1 and len(r2) == 2
              and not oo["yarim"]))
    s.append(("ocr: kart benzerligi (beyaz = ref, MAE 0)", oo["en_yakin_ref"][0][:2] == ["1", 1] and oo["en_yakin_ref"][0][2] == 0))
    yavas = K.gorsel_isle
    K.gorsel_isle = lambda g, gd, refler: (time.sleep(0.6), yavas(g, gd, refler))[1]
    o3 = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["k", "--mod", "ocr", "--kaynak", str(out), "--out", str(o3), "--sure-dk", "0.005", "--isci", "1"]
    K.main()
    o3z = json.loads((o3 / "OCR_OZET.json").read_text())
    s.append(("ocr: sure dolunca yeni gorsel baslamaz, yarim isareti, yapilan satir dosyada", o3z["yarim"] and 1 <= o3z["islenen"] < 2
              and len(list(csv.DictReader(open(o3 / "GORSEL_OCR.csv", encoding="utf-8")))) == o3z["islenen"]))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"kagit_tara testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
