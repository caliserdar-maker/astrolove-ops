#!/usr/bin/env python3
"""ornament_pazar.py yerel testi: SAHTE yanitlar, Etsy'ye istek YOK (requests.request ve CDN indirme yamalanir).
Senaryolar: (A) normal kosu, (B) dusuk kota -> baslamaz, (C) butce kapisi, (D) 403 alan bos kalir, (E) 429 durdurur.
Cikis 0 = PASS."""
import csv
import io
import json
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import ornament_pazar as OP  # noqa: E402

from PIL import Image  # noqa: E402

GERCEK_ISTEK = []


class Yanit:
    def __init__(self, kod, j=None, kalan=None):
        self.status_code, self._j = kod, j
        self.headers = {"x-remaining-today": str(kalan)} if kalan is not None else {}
        self.text = json.dumps(j)[:300] if j is not None else ""

    def json(self):
        return self._j


class Sahte:
    def __init__(self, kalan=5000, shop_kod=200, yorum_kod=200, arama_kod=200):
        self.kalan, self.log = kalan, []
        self.shop_kod, self.yorum_kod, self.arama_kod = shop_kod, yorum_kod, arama_kod
        rnd = random.Random(7)
        # 6 arama x 100 ilan, ortusen havuz (tekillestirme testi): havuz 350 ilan, 40 magaza
        self.havuz = {}
        for i in range(350):
            lid = 1000000 + i
            self.havuz[lid] = {"listing_id": lid, "title": f"Ornament {i}", "url": f"https://www.etsy.com/listing/{lid}/x",
                               "price": {"amount": 1500 + i, "divisor": 100, "currency_code": "USD"},
                               "shop_id": 500 + (i % 40), "num_favorers": rnd.randint(0, 5000) if i != 3 else None,
                               "views": rnd.randint(0, 90000), "materials": ["wood"], "tags": ["ornament", "couple"],
                               "is_personalizable": True, "original_creation_timestamp": 1700000000 + i}
        # esit favori -> magaza satisi ayirsin
        self.havuz[1000010]["num_favorers"] = self.havuz[1000011]["num_favorers"] = 99999

    def __call__(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):
        assert method == "GET", f"yazma istegi: {method} {url}"
        assert "Authorization" not in (headers or {}), "OAuth basligi gitmemeli"
        self.kalan -= 1
        yol = url.replace(E.API, "")
        self.log.append((yol, dict(params or {})))
        if yol == "/openapi-ping":
            return Yanit(200, {"application_id": 1}, self.kalan)
        if yol == "/listings/active":
            if self.arama_kod != 200:
                return Yanit(self.arama_kod, {"error": "x"}, self.kalan)
            assert params["sort_on"] == "score" and params["limit"] == 100
            k = OP.IFADELER.index(params["keywords"])
            ids = sorted(self.havuz)[k * 50: k * 50 + 100]
            return Yanit(200, {"count": 1234 + k, "results": [self.havuz[i] for i in ids]}, self.kalan)
        if yol == "/listings/batch":
            ids = [int(x) for x in params["listing_ids"].split(",")]
            assert len(ids) <= 100
            res = []
            for i in ids:
                L = dict(self.havuz[i])
                L["images"] = [{"rank": 2, "url_570xN": f"https://i.etsystatic.com/{i}_b.jpg"},
                               {"rank": 1, "url_570xN": f"https://i.etsystatic.com/{i}_a.jpg"}]
                L["shop"] = {"shop_name": f"Dukkan{L['shop_id']}"}
                res.append(L)
            return Yanit(200, {"count": len(res), "results": res}, self.kalan)
        if yol.startswith("/shops/"):
            if self.shop_kod != 200:
                return Yanit(self.shop_kod, {"error": "forbidden"}, self.kalan)
            sid = int(yol.split("/")[2])
            return Yanit(200, {"shop_id": sid, "shop_name": f"Shop{sid}", "transaction_sold_count": sid * 10,
                               "review_count": sid, "review_average": 4.9}, self.kalan)
        if yol.endswith("/reviews"):
            if self.yorum_kod == 429:
                r = Yanit(429, {"error": "quota"}, self.kalan); r.headers["retry-after"] = "86400"; return r
            if self.yorum_kod != 200:
                return Yanit(self.yorum_kod, {"error": "x"}, self.kalan)
            return Yanit(200, {"count": int(yol.split("/")[2]) % 97, "results": []}, self.kalan)
        raise AssertionError(f"beklenmeyen yol {yol}")


def resim(u):
    b = io.BytesIO()
    Image.new("RGB", (570, 456), (200, 30, 30)).save(b, "JPEG")
    return b.getvalue()


def kur(s):
    E.requests.request = s
    E.time.sleep = lambda *_: None
    api = E.Etsy(E.APIKeyStore("anahtar", "sir"))
    api.pace = 0
    return api


def oku(yol):
    with open(yol, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():  # noqa: C901
    hata = []

    def kontrol(k, m):
        print(("PASS " if k else "FAIL ") + m)
        if not k:
            hata.append(m)

    # A: normal
    s = Sahte()
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)
        kod = OP.calis(out, kur(s), indir=resim)
        oz = json.loads((out / "OZET.json").read_text())
        tum, ilk = oku(out / "ILANLAR.csv"), oku(out / "ILK20.csv")
        kontrol(kod == 0, f"A kod 0 ({kod})")
        kontrol(len(s.log) <= OP.BUTCE, f"A istek {len(s.log)} <= {OP.BUTCE}")
        kontrol(oz["etsy_istek"] == len(s.log), f"A sayac {oz['etsy_istek']} = gercek {len(s.log)}")
        aramalar = [p for y, p in s.log if y == "/listings/active"]
        kontrol(len(aramalar) == 6 and [p["keywords"] for p in aramalar] == OP.IFADELER, "A 6 arama dogru ifadelerle")
        kontrol(len(tum) == 350 and len({r["listing_id"] for r in tum}) == 350, f"A tekil ilan {len(tum)} (beklenen 350)")
        shops = [y for y, _ in s.log if y.startswith("/shops/")]
        kontrol(len(shops) == len(set(shops)) <= 40, f"A getShop tekil {len(shops)} <= 40")
        kontrol(sum(1 for y, _ in s.log if y.endswith("/reviews")) == 20, "A 20 yorum istegi")
        kontrol(len(ilk) == 20 and all(r["ana_gorsel_url"].endswith("_a.jpg") for r in ilk), "A ilk 20, ana gorsel = rank 1")
        fav = [int(r["favori"]) for r in ilk]
        kontrol(fav == sorted(fav, reverse=True), "A favori azalan")
        e = [r for r in ilk if r["favori"] == "99999"]
        kontrol(len(e) == 2 and int(e[0]["magaza_toplam_satis"]) >= int(e[1]["magaza_toplam_satis"]),
                "A esit favoride magaza satisi azalan")
        kontrol(all(r["magaza_adi"].startswith("Shop") and r["magaza_toplam_satis"] for r in ilk), "A magaza adi/satis dolu")
        kontrol(all(r["ilan_yorum"] != "" for r in ilk), "A ilan yorum dolu")
        n3 = [r for r in tum if r["listing_id"] == "1000003"]
        kontrol(n3 and n3[0]["favori"] == "", "A favori None -> bos (uydurma yok)")
        kontrol([r["sira"] for r in tum] == [str(i) for i in range(1, 351)], "A sira 1..N")
        kontrol(all(r["magaza_toplam_satis"] == "" for r in tum[40:]), "A ilk 40 disinda magaza satisi bos")
        kontrol((out / "TEMAS.jpg").stat().st_size > 5000 and oz["gorsel_indirilen"] == 20, "A TEMAS.jpg + 20 gorsel")
        kontrol(Image.open(out / "TEMAS.jpg").size == (1500, 1360), f"A TEMAS boyutu {Image.open(out / 'TEMAS.jpg').size}")
        kontrol("TOPLAM satisidir" in (out / "RAPOR_TASLAK.md").read_text(), "A rapor uyari notu")
        print(f"   A: istek {len(s.log)}, kota {oz['kota_baslangic']} -> {oz['kota_bitis']}")

    # B: dusuk kota -> 1 istek, baslamaz
    for kalan, beklenen in ((580, 0), (581, 2)):    # ping sonrasi kalan 579 / 580: 579-80=499 <500 baslamaz, 580-80=500 baslar
        s = Sahte(kalan=kalan)
        with tempfile.TemporaryDirectory() as d:
            kod = OP.calis(Path(d), kur(s), indir=resim)
            if beklenen == 2:
                kontrol(kod == 0 and len(s.log) > 1, f"B sinir: ping sonrasi kalan {kalan - 1} -> basladi")
            else:
                kontrol(kod == 2 and len(s.log) == 1, f"B sinir: ping sonrasi kalan {kalan - 1} -> BASLAMADI, 1 istek ({len(s.log)})")

    # C: butce kapisi (kucuk butce)
    s = Sahte()
    api = kur(s)
    ok = OP.Okuyucu(api, butce=5)
    try:
        for _ in range(10):
            ok.get("/openapi-ping")
        kontrol(False, "C butce kapisi")
    except OP.Butce:
        kontrol(len(s.log) <= 5, f"C butce kapisi: {len(s.log)} istek <= 5")

    # D: getShop 403 + yorum 403 -> alanlar bos, kosu tamam
    s = Sahte(shop_kod=403, yorum_kod=403)
    with tempfile.TemporaryDirectory() as d:
        kod = OP.calis(Path(d), kur(s), indir=resim)
        ilk = oku(Path(d) / "ILK20.csv")
        oz = json.loads((Path(d) / "OZET.json").read_text())
        kontrol(kod == 0 and all(r["magaza_toplam_satis"] == "" and r["ilan_yorum"] == "" for r in ilk) and oz["atlanan"],
                "D 403 -> alan bos, not dusuldu")
        kontrol(all(r["magaza_adi"].startswith("Dukkan") for r in ilk), "D magaza adi batch include'dan")

    # E: 429 (gunluk kota) -> durur
    s = Sahte(yorum_kod=429)
    with tempfile.TemporaryDirectory() as d:
        try:
            OP.calis(Path(d), kur(s), indir=resim)
            kontrol(False, "E 429 durdurmali")
        except SystemExit as e:
            kontrol("429" in str(e), f"E 429 durdu: {str(e)[:60]}")

    # F: arama 403 -> durur (arama zorunlu veri; bos rapor uretilmez)
    s = Sahte(arama_kod=403)
    with tempfile.TemporaryDirectory() as d:
        try:
            OP.calis(Path(d), kur(s), indir=resim)
            kontrol(False, "F arama hatasi durdurmali")
        except SystemExit as e:
            kontrol("403" in str(e) and len(s.log) == 2, f"F arama 403 durdu ({len(s.log)} istek)")

    print("SONUC:", "PASS" if not hata else f"FAIL {len(hata)}: {hata}")
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main())
