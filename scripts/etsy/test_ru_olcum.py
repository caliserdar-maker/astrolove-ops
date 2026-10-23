#!/usr/bin/env python3
"""ru_olcum sahte testi (ag yok): oku() ilan basina kota_kapisi + yalniz GET; analiz sorun turleri."""
import gzip
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ru_olcum as R  # noqa: E402

EN = "Intro.\n\nNames: up to 11 letters each. Message: up to 35 characters.\n\nSIZES\n2 sizes. Printed on premium matte art paper."
RU_IYI = "Вступление.\n\nИмена: до 11 букв. Надпись: до 35 символов. Цифровой файл или печать.\n\n2 РАЗМЕРА\n8 × 10 и A4."
RU_KOTU = ("Дизайн AstroLove. Hahnemühle Photo Rag 308 г/м². Партнер Prodigi. Имена: до 12 букв — тире.\n\n"
           "3 РАЗМЕРА\n8 × 10, 30 × 40 и A4. Цена $20.")


def inv(boy):
    return {"products": [{"sku": f"S{i}", "is_deleted": False, "offerings": [], "property_values": [
        {"property_name": "Format", "values": ["Digital File"]}, {"property_name": "Primary color", "values": ["Deep Black"]},
        {"property_name": "Size", "values": [b]}]} for i, b in enumerate(boy)]}


class Sahte:
    def __init__(self, kapi_dur=None):
        self.remaining, self.calls, self.yol, self.kapi, self.kapi_dur = 3000, 0, [], [], kapi_dur

    def get(self, path, params=None, ok404=False):
        self.calls += 1; self.yol.append(path)
        if path.endswith("/sections"):
            return {"results": [{"shop_section_id": 9, "title": "Zodiac Couple Posters"}]}
        if path.endswith("/listings") and "shops" in path:
            return {"count": 2, "results": [{"listing_id": 1}, {"listing_id": 2}]}
        if path == "/listings/batch":
            return {"results": [{"listing_id": i, "state": "active", "shop_section_id": 9, "description": EN, "title": "T"} for i in (1, 2)]}
        if path.endswith("/translations/ru"):
            return {"language": "ru", "title": "Т", "description": RU_IYI if "/1/" in path else RU_KOTU}
        if path.endswith("/inventory"):
            return inv(["8×10″ (20×25cm)", "A4 (21×29.7cm)"])
        raise AssertionError(path)

    def kota_kapisi(self, ne):
        self.kapi.append(ne)
        if self.kapi_dur and len(self.kapi) == self.kapi_dur:
            raise SystemExit(f"DUR: kota esigi ({ne} baslamadi)")

    def __getattr__(self, ad):   # patch/put/post/delete: yazma cagrisi testte hata verir
        raise AssertionError(f"yazma cagrisi: {ad}")


def main():
    s = []
    out = pathlib.Path(tempfile.mkdtemp())
    api = Sahte()
    ham = R.oku(api, "7", out)
    s.append(("oku: 2 ilan, ilan basina kota_kapisi, HAM.json.gz", api.kapi == ["ilan 1", "ilan 2"] and len(ham) == 2
              and (out / "HAM.json.gz").exists()))
    oz = R.analiz(ham, out)
    satir = {r["listing_id"]: r for r in __import__("csv").DictReader(open(out / "RU_OLCUM.csv", encoding="utf-8"))}
    s.append(("iyi RU: sorun yok", satir["1"]["sorunlar"] == ""))
    beklenen = {"boy_sayisi", "boy_fazla", "kagit_celiski", "tedarikci", "marka_artsiz", "tire", "isim_siniri", "dijital_yok", "fiyat",
                "mesaj_siniri"}
    s.append(("kotu RU: beklenen sorun turleri", beklenen <= set(satir["2"]["sorunlar"].split())))
    s.append(("kotu RU: fazla boy 30x40", satir["2"]["ru_boy_fazla"] == "30x40" and satir["2"]["ru_boy_beyan"] == "3" and "20" in satir["2"]["ru_sayi_en_yok"].split()))
    s.append(("ozet: poster 2 ilan, 1 sorunlu", oz["poster"]["ilan"] == 2 and oz["poster"]["sorunlu"] == 1))
    api = Sahte(kapi_dur=2)
    try:
        R.oku(api, "7", pathlib.Path(tempfile.mkdtemp())); dur = None
    except SystemExit as e:
        dur = str(e)
    s.append(("kota kapisi 2. ilanda DUR: 2. ilanin RU/envanteri okunmaz", dur and "ilan 2" in dur
              and not any("/2/" in y for y in api.yol)))
    with gzip.open(out / "HAM.json.gz", "rt", encoding="utf-8") as f:
        s.append(("analiz modu HAM'dan ayni sonucu verir", R.analiz(json.load(f), pathlib.Path(tempfile.mkdtemp())) == oz))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"ru_olcum testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
