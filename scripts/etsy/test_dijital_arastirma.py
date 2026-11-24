#!/usr/bin/env python3
"""dijital_arastirma sahte testi. Etsy'ye / aga istek YOK: etsy_common.requests.request sahte Etsy; socket kapali.
Bilinen PASS: tam akis (olc -> agac -> ornek -> yorum -> ozet), kota durdurma + kaldigi yerden devam (ayni sonuc), yol verme
+ devam, sure dolmasi + devam. Bilinen FAIL: GET disi istek (SaltOkur), kisisellestirmeli / fiziksel ilan orneklemde, yorumcu
kimligi ciktida, loga 6+ haneli kimlik (KimlikSuz), bozuk uygun() mutasyonu."""
import contextlib
import csv
import io
import json
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import dijital_arastirma as D  # noqa: E402


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag cagrisi")


socket.socket = _ag_yok          # type: ignore[assignment]
socket.create_connection = _ag_yok
E.requests.post = E.requests.get = _ag_yok
E.time.sleep = lambda *_: None
D.YOL_VER_SN = 0

# ------------------------------------------------------------------ sahte Etsy
AGAC = [{"id": 1, "name": "Paper", "children": [
            {"id": 11, "name": "Planners", "children": [
                {"id": 111, "name": "Digital Planners", "children": []},
                {"id": 112, "name": "Paper Planners", "children": []}]},
            {"id": 12, "name": "Clip Art", "children": [
                {"id": 121, "name": "Clip Art Sets", "children": [{"id": 1211, "name": "Floral Clip Art", "children": []}]}]}]},
        {"id": 2, "name": "Jewelry", "children": [{"id": 21, "name": "Rings", "children": []}]}]
YAPRAK = {111: "download", 112: "physical", 1211: "download", 21: "physical"}
ILAN = {}
for yap, tip in YAPRAK.items():
    for k in range(150):
        lid = 900000000 + yap * 1000 + k
        t = tip
        if tip == "download" and k % 10 == 9:
            t = "both"
        ILAN[lid] = {"listing_id": lid, "shop_id": 70000000 + (k % 23), "title": f"Ilan {k}", "url": f"https://etsy/{lid}",
                     "listing_type": t, "is_personalizable": (k % 7 == 3), "taxonomy_id": yap, "num_favorers": k,
                     "views": 0, "price": {"amount": 100 + k * 10, "divisor": 100, "currency_code": "USD"},
                     "tags": ["a", "b"], "created_timestamp": 1760000000 + k * 1000, "updated_timestamp": 1760000000 + k}


def altlar(tid):
    def bul(ns):
        for n in ns:
            if n["id"] == tid:
                return n
            r = bul(n["children"])
            if r:
                return r
    n = bul(AGAC)
    out = []

    def gez(n):
        out.append(n["id"])
        for c in n["children"]:
            gez(c)
    gez(n)
    return set(out)


def yorumlar(lid):
    n = lid % 260
    return [{"shop_id": ILAN[lid]["shop_id"], "listing_id": lid, "transaction_id": 5550000000 + i, "buyer_user_id": 4440000000 + i,
             "rating": (2 if i % 6 == 0 else (4 if i % 6 == 1 else 5)), "review": f"love it great quality print {i}" if i % 3 else "",
             "language": "en", "image_url_fullxfull": "x", "created_timestamp": 1790000000 - i * 86400 * 3,
             "create_timestamp": 1790000000 - i * 86400 * 3} for i in range(n)]


class Yanit:
    def __init__(self, kod, j, kalan):
        self.status_code = kod
        self._j = j
        self.headers = {"x-remaining-today": str(kalan), "x-limit-per-day": "10000"}
        self.text = json.dumps(j)[:300]

    def json(self):
        return self._j


class Sahte:
    def __init__(self, kalan=9000):
        self.kalan = kalan
        self.yollar = []
        self.yazma = 0

    def ping(self, path):
        return {"x-limit-per-day": "10000", "x-remaining-today": str(self.kalan), "x-limit-per-second": "10",
                "x-remaining-this-second": "9", "http": 200}

    def __call__(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):  # noqa: A002
        assert "x-api-key" in (headers or {}) and "Authorization" not in headers, "OAuth basligi"
        if method != "GET":
            self.yazma += 1
        self.kalan -= 1
        p = urlparse(url).path.replace("/v3/application", "")
        self.yollar.append(p)
        params = params or {}
        if self.kalan < 0:
            return Yanit(429, {"error": "kota"}, 0)
        if p == "/seller-taxonomy/nodes":
            return Yanit(200, {"count": 2, "results": AGAC}, self.kalan)
        if p == "/listings/active":
            off, lim = int(params.get("offset", 0)), int(params.get("limit", 25))
            if off + lim > 12000:
                return Yanit(400, {"error": "offset"}, self.kalan)
            if params.get("taxonomy_id"):
                s = altlar(int(params["taxonomy_id"]))
                L = [x for x in ILAN.values() if x["taxonomy_id"] in s]
            else:
                L = list(ILAN.values())
            if params.get("sort_on") == "created":
                L.sort(key=lambda x: -x["created_timestamp"])
            return Yanit(200, {"count": len(L), "results": L[off:off + lim]}, self.kalan)
        if p == "/listings/batch":
            ids = [int(x) for x in params["listing_ids"].split(",")]
            res = [dict(ILAN[i], shop={"shop_id": ILAN[i]["shop_id"], "shop_name": "S", "transaction_sold_count": 50,
                                       "review_count": 10, "review_average": 4.8, "create_date": 1600000000,
                                       "listing_active_count": 30, "url": "u"}) for i in ids]
            return Yanit(200, {"count": len(res), "results": res}, self.kalan)
        if p.startswith("/shops/"):
            return Yanit(200, {"shop_id": int(p.split("/")[2]), "shop_name": "S", "transaction_sold_count": 50}, self.kalan)
        if p.endswith("/reviews"):
            lid = int(p.split("/")[2])
            y = yorumlar(lid)
            off, lim = int(params.get("offset", 0)), int(params.get("limit", 25))
            return Yanit(200, {"count": len(y), "results": y[off:off + lim]}, self.kalan)
        return Yanit(404, {"error": "yok"}, self.kalan)


def api_kur(s):
    E.requests.request = s
    api = D.SaltOkur(E.APIKeyStore("anahtar", "sir"))
    api.pace = 0
    return api


def kos(s, d, dk=60, yv=None):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        api = api_kur(s)
        api.pace = 0
        kod = D.calis(d, dk, api, yv, s.ping, simdi=1790000000)
    return kod, log.getvalue()


def oku(d, ad):
    with open(Path(d) / ad, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


HATA = []


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def durum(d):
    return json.loads((Path(d) / "durum.json").read_text())


def main():
    # pace dosyadan okunsa bile 0 kalsin
    D.Okuyucu  # noqa: B018
    tmp = Path(tempfile.mkdtemp(prefix="dij_"))
    try:
        # 1) tam akis
        s = Sahte()
        d1 = tmp / "a"
        kod, lg = kos(s, d1)
        st = durum(d1)
        kontrol("tam akis kod 0", kod == 0)
        kontrol("tam akis bitti", st["asama"] == "bitti")
        kontrol("yazma yok", s.yazma == 0)
        tur = [r for r in oku(d1, "TURLER.csv") if r["tur"] == "1"]
        kontrol("tur secimi en ozel dugum (111 ve 1211)", sorted(r["tur_id"] for r in tur) == ["111", "1211"])
        il = oku(d1, "ILANLAR.csv")
        kontrol("orneklem yalniz download", all(r["listing_type"] == "download" for r in il))
        kontrol("orneklem kisisellestirmesiz", all(r["is_personalizable"] in ("False", "") for r in il))
        kontrol("grup basina 15", all(sum(1 for r in il if r["tur_id"] == t and r["grup"] == g) == 15
                                      for t in ("111", "1211") for g in ("relevans", "yeni")))
        y = oku(d1, "YORUMLAR.csv")
        beklenen = sum(len(yorumlar(int(r["listing_id"]))) for r in il)
        kontrol(f"butun yorumlar ({len(y)}/{beklenen})", len(y) == beklenen)
        ham = (d1 / "YORUMLAR.csv").read_text(encoding="utf-8")
        kontrol("yorumcu kimligi yok", "buyer_user_id" not in ham and "444000" not in ham and "555000" not in ham)
        oz = oku(d1, "TUR_OZET.csv")
        kontrol("ozet 2 tur x 3 grup", len(oz) == 6)
        h = [o for o in oz if o["grup"] == "hepsi"]
        kontrol("ozet kanitli satis = api yorum toplami", all(int(o["kanitli_satis_toplam"]) == int(o["yorum_toplami_api"]) for o in h))
        kontrol("ozet olumsuz sayimi", all(int(o["olumsuz"]) == sum(1 for r in y if r["tur_id"] == o["tur_id"] and int(r["rating"]) <= 3) for o in h))
        kontrol("ozet tema", any(o["olumlu_ilk3_tema"] for o in h))
        for f in ("API_OLCUM.json", "TAKSONOMI.csv", "MAGAZALAR.csv", "EKSIK_ALAN.csv", "YORUMLAR_ETIKETLI.csv"):
            kontrol(f"dosya {f}", (d1 / f).exists())
        api = json.loads((d1 / "API_OLCUM.json").read_text())
        kontrol("olc alt_kapsar", api["uc_noktalar"]["taxonomy_id"]["alt_dugum_kapsar"] is True)
        kontrol("olc views var", api["ilan_alanlari"]["views"]["var"] > 0)
        kontrol("magaza tablosu = ilanlardaki tekil magaza", len(oku(d1, "MAGAZALAR.csv")) == len({r["shop_id"] for r in il}) and all(r["transaction_sold_count"] for r in oku(d1, "MAGAZALAR.csv")))
        # log suzgeci
        buf = io.StringIO()
        ks = D.KimlikSuz(buf)
        ks.write(lg)
        kontrol("log suzgeci 6+ hane", not D.KimlikSuz.RX.search(buf.getvalue()))
        kontrol("log metin yok", "Ilan " not in lg and "love it" not in lg)
        buf2 = io.StringIO()
        D.KimlikSuz(buf2).write("ilan 900111001 hata")
        kontrol("bilinen FAIL: suzgec kimligi yakalar", "<id>" in buf2.getvalue())
        # 2) kota durdurma + devam
        s2 = Sahte(kalan=2000 + 80)       # %20 esigi 2000: birkac istekte durur
        d2 = tmp / "b"
        kod2, _ = kos(s2, d2)
        kontrol("kota DUR kod 3", kod2 == 3)
        kontrol("kota DUR asama bitmedi", durum(d2)["asama"] != "bitti")
        s2.kalan = 9000
        for _ in range(5):
            k, _l = kos(s2, d2)
            if durum(d2)["asama"] == "bitti":
                break
        kontrol("kota sonrasi devam bitti", durum(d2)["asama"] == "bitti")
        kontrol("devam sonucu ayni (yorum)", len(oku(d2, "YORUMLAR.csv")) == len(y))
        kontrol("devam sonucu ayni (ilan)", len(oku(d2, "ILANLAR.csv")) == len(il))
        # 3) yol verme
        s3 = Sahte()
        d3 = tmp / "c"
        n = {"i": 0}

        def yv():
            n["i"] += 1
            return n["i"] == 3
        kod3, _ = kos(s3, d3, yv=yv)
        kontrol("yol ver kod 4", kod3 == 4)
        kod3b, _ = kos(s3, d3)
        kontrol("yol ver sonrasi bitti", durum(d3)["asama"] == "bitti" and len(oku(d3, "YORUMLAR.csv")) == len(y))
        # 4) sure doldu
        s4 = Sahte()
        d4 = tmp / "d"
        kod4, _ = kos(s4, d4, dk=0)
        kontrol("sure 0 kod 0 bitmedi", kod4 == 0 and durum(d4)["asama"] != "bitti")
        # 5) GET disi yasak
        api5 = api_kur(Sahte())
        try:
            api5.patch("/shops/1/listings/2", {"title": "x"})
            kontrol("bilinen FAIL: PATCH yasak", False)
        except SystemExit as e:
            kontrol("bilinen FAIL: PATCH yasak", "yasak" in str(e))
        # 6) mutasyon: uygun() bozulursa test yakalar
        eski = D.uygun
        D.uygun = lambda L: L.get("listing_type") in ("download", "both")
        s6 = Sahte()
        d6 = tmp / "e"
        kos(s6, d6)
        il6 = oku(d6, "ILANLAR.csv")
        kontrol("mutasyon yakalanir (both / kisisel)", not all(r["listing_type"] == "download" and r["is_personalizable"] in ("False", "")
                                                              for r in il6))
        D.uygun = eski
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"SONUC: {'FAIL ' + str(len(HATA)) if HATA else 'PASS'}")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
