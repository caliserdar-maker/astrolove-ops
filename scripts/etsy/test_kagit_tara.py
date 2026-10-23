#!/usr/bin/env python3
"""kagit_tara sahte testi (ag yok): desenler, magaza alanlari, ilan/alt metin/OCR bulgulari, ilan basina kota kapisi, yazma yok."""
import json
import os
import pathlib
import sys
import tempfile

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
            return {"results": [{"rank": 1, "listing_image_id": 11, "alt_text": "Fine art paper detail, 100 percent cotton",
                                 "url_570xN": "x"}]}
        raise AssertionError(path)

    def kota_kapisi(self, ne):
        self.kapi.append(ne)

    def __getattr__(self, ad):
        raise AssertionError(f"yazma cagrisi: {ad}")


def main():
    s = []
    s.append(("desen", K.bul("Hahnemühle Photo Rag 308 gsm, giclée, хлопковой, Prodigi, музейному") ==
              sorted(["hahnemühle", "photo rag", "308", "giclée", "хлопковой", "prodigi", "музейному"])))
    s.append(("desen: matte art paper temiz", K.bul("premium matte art paper, long-lasting inks") == []))
    api = Sahte()
    K.B.Etsy = lambda store: api
    K.B.TokenStore = type("T", (), {"__init__": lambda self, *a: None, "needs_refresh": lambda self: False})
    K.gorsel_isle = lambda lid, aile, im, refler: dict(listing_id=lid, aile=aile, rank=1, image_id=11,
                                                        ocr_bulgu="fine art paper" if lid == "2" else "")
    os.environ.update(TOKEN_FILE="x", ETSY_SHOP_ID="7")
    out = pathlib.Path(tempfile.mkdtemp())
    sys.argv = ["k", "--out", str(out)]
    K.main()
    oz = json.loads((out / "KAGIT_OZET.json").read_text())
    rows = list(__import__("csv").DictReader(open(out / "KAGIT_TARAMA.csv", encoding="utf-8")))
    s.append(("magaza: duyuru + politika bulgulari", {r["alan"] for r in rows if r["kaynak"] == "magaza"} == {"announcement", "policy_refunds"}))
    s.append(("ilan 2: aciklama + materials", {(r["alan"], r["terim"]) for r in rows if r["kaynak"] == "ilan"} >=
              {("description", "prodigi"), ("description", "giclée"), ("materials", "cotton")}))
    s.append(("alt metin her ilanda", oz["ilan_sayisi_kaynak"]["alt_metin"] == 2))
    s.append(("OCR bulgusu yalniz ilan 2", oz["ilan_sayisi_kaynak"]["gorsel_ocr"] == 1))
    s.append(("ilan basina kota kapisi", api.kapi == ["ilan 1", "ilan 2"]))
    s.append(("about ucu yok", oz["about_ucu"].startswith("yok")))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"kagit_tara testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
