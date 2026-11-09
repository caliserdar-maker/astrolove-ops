#!/usr/bin/env python3
"""kolye_katalog sahte Printify testi (gercek istek YOK: kolye_katalog.ac taklit; yonlendirme testi yalniz 127.0.0.1).
Bilinen PASS: aday secimi, zorunlu 778 / 9114 / 2947, varyant / placeholder / kargo tablolari, decoration_methods ayrimi, rapor ag acmaz.
Bilinen FAIL: izin disi yol, GET disi yontem, aday > 40, zorunlu 3 blueprint'ten biri yok,
tahmin > 600, anahtar yok / bos / icte bosluk, 401 / 403,
4 denemeden sonra 429, 30x takip edilmez, anahtar ham dosyada / logda yok."""
import contextlib
import csv
import http.server
import io
import json
import os
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kolye_katalog as K  # noqa: E402

K.time.sleep = lambda s: None
ANAHTAR = "PYKEY_sahte_kolye_77aa"


class Yanit:
    def __init__(self, kod, veri):
        self.status, self._b = kod, json.dumps(veri).encode()

    def read(self, *a):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def hata(url, kod, govde=b'{"error":"x"}'):
    return urllib.error.HTTPError(url, kod, "x", {}, io.BytesIO(govde))


class Sahte:
    def __init__(self, bps=None, saglayici=2, kod_yol=None, yansit=False):
        self.cagri = []
        self.bps = bps if bps is not None else [
            {"id": 778, "title": "Oval Necklace"}, {"id": 801, "title": "Engraved Bar Pendant"}, {"id": 802, "title": "Heart Necklace"},
            {"id": 803, "title": "Necklaces Gift Set"}, {"id": 804, "title": "Charm Bracelet"}, {"id": 805, "title": "Ceramic Ornament"},
            {"id": 9114, "title": "Oval Pendant"}, {"id": 2947, "title": "Birthstone Circle Charm (Engraving)"}]
        self.saglayici, self.kod_yol, self.yansit = saglayici, kod_yol or {}, yansit

    def __call__(self, req, timeout=None):
        url, y = req.full_url, req.get_method()
        self.cagri.append((y, url))
        u = urllib.parse.urlparse(url)
        assert u.netloc == "api.printify.com" and y == "GET", url
        yol = u.path
        for desen, kod in self.kod_yol.items():
            if re.search(desen, yol):
                raise hata(url, kod, (req.headers.get("Authorization") or "").encode() * 3 if self.yansit else b'{"e":1}')
        yan = {"yansima": req.headers.get("Authorization")} if self.yansit else {}
        if yol == "/v1/catalog/blueprints.json":
            return Yanit(200, self.bps)
        m = re.fullmatch(r"/v1/catalog/blueprints/(\d+)\.json", yol)
        if m:
            b = int(m.group(1))
            ac = {778: "<p>Dye sublimation printed white aluminum</p>", 801: "Laser engraved stainless steel", 802: "A lovely heart"}
            return Yanit(200, {"id": b, "title": next(x["title"] for x in self.bps if x["id"] == b), "brand": "Generic", "model": f"M{b}",
                               "description": ac.get(b, ""), **yan})
        if yol.endswith("/print_providers.json"):
            return Yanit(200, [{"id": 10 + i, "title": f"PP{i}"} for i in range(self.saglayici)])
        if yol.endswith("/variants.json"):
            b = int(yol.split("/")[4])
            ph = [{"position": "front", "width": 1200, "height": 900}, {"position": "back", "width": 600, "height": 400}]
            if b == 802:
                ph = [dict(ph[0], decoration_methods=["engraving"])]
            return Yanit(200, {"variants": [{"id": b * 10 + 1, "title": "Silver / Small", "options": {"size": "Small", "color": "Silver"},
                                             "placeholders": ph, "is_available": True},
                                            {"id": b * 10 + 2, "title": "Gold / Large", "options": {"size": "Large", "color": "Gold"},
                                             "placeholders": ph[:1], "is_available": False}]})
        if yol.startswith("/v1/") and yol.endswith("/shipping.json"):
            return Yanit(200, {"handling_time": {"value": 3, "unit": "day"}, "profiles": [
                {"variant_ids": [1], "countries": ["US"], "first_item": {"cost": 499, "currency": "USD"}, "additional_items": {"cost": 150, "currency": "USD"}},
                {"variant_ids": [1], "countries": ["REST_OF_THE_WORLD"], "first_item": {"cost": 999, "currency": "USD"},
                 "additional_items": {"cost": 300, "currency": "USD"}}]})
        if yol.startswith("/v2/") and yol.endswith("/shipping.json"):
            return Yanit(200, {"data": [{"id": "standard", "attributes": {"name": "standard"}}]})
        if re.search(r"/v2/.*/shipping/standard\.json$", yol):
            return Yanit(200, {"data": [{"attributes": {"country": {"code": "US"}, "shippingCost": {"firstItem": {"amount": 499, "currency": "USD"},
                                                                                                    "additionalItems": {"amount": 150}},
                                                        "handlingTime": {"from": 2, "to": 5}}},
                                        {"attributes": {"country": {"code": "REST_OF_THE_WORLD"},
                                                        "shippingCost": {"firstItem": {"amount": 999, "currency": "USD"}}}}]})
        if re.fullmatch(r"/v1/catalog/print_providers/\d+\.json", yol):
            return Yanit(200, {"location": {"country": "US", "region": "NC"}})
        raise AssertionError(f"sahte: bilinmeyen {yol}")


@contextlib.contextmanager
def ortam(sahte, anahtar=ANAHTAR):
    eski = K.ac
    K.ac = sahte
    K.ISTEKLER.clear()
    K.GONDERIM[0] = 0
    if anahtar is None:
        os.environ.pop("PRINTIFY_API_KEY", None)
    else:
        os.environ["PRINTIFY_API_KEY"] = anahtar
    try:
        yield
    finally:
        K.ac = eski
        os.environ.pop("PRINTIFY_API_KEY", None)


def kos(sahte, anahtar=ANAHTAR):
    d = Path(tempfile.mkdtemp(prefix="kolye_katalog_test_"))
    out = io.StringIO()
    hata_ = None
    with ortam(sahte, anahtar), contextlib.redirect_stdout(out):
        try:
            kod = K.oku(d / "ham")
        except SystemExit as e:
            kod, hata_ = None, str(e.code)
    return d, kod, hata_, out.getvalue()


def dur(f, *a):
    try:
        f(*a)
    except SystemExit as e:
        return str(e.code)
    return None


def testler():  # noqa: C901
    t = []
    for b, ok in (("Oval Necklace", True), ("Engraved Bar Pendant", True), ("NECKLACE", True), ("Necklaces Gift Set", False),
                  ("Charm Bracelet", False), ("Ceramic Ornament", False), ("Pendants", False)):
        t.append((f"{'PASS' if ok else 'FAIL'}: aday basligi {b!r}", bool(K.ADAY_RX.search(b)) == ok))
    for metin, beklenen in (("laser-cut stainless steel", "belirsiz"), ("stretch chain, sketch style", "belirsiz"),
                            ("ships via print provider; print area 1x1", "belirsiz"), ("laser engraved bar", "kazimali"),
                            ("etched heart", "kazimali"), ("photograving", "kazimali"), ("UV print on steel", "baskili"),
                            ("sublimation pendant", "baskili"), ("full color printed", "baskili")):
        t.append((f"PASS: teknik {metin!r} -> {beklenen}", K.teknik({"description": metin}, [{}])[0] == beklenen))
    sh = Sahte()
    d, kod, h, log = kos(sh)
    a = json.loads((d / "ham" / "_adaylar.json").read_text())
    t.append(("PASS: oku 0", kod == 0 and h is None))
    t.append(("PASS: adaylar 778, 801, 802, 2947, 9114 (aciklama / cogul / bilezik yok)", sorted(a, key=int) == ["778", "801", "802", "2947", "9114"]))
    t.append(("PASS: 2947 basliksiz zorunlu aday (neden zorunlu), 9114 baslikla", a["2947"]["neden"] == "zorunlu" and a["9114"]["neden"] == "baslik"
              and a["778"]["neden"] == "baslik" and sorted(K.ZORUNLU) == [778, 2947, 9114]))
    t.append(("PASS: yalniz GET ve yalniz izinli yollar", all(y == "GET" and any(re.fullmatch(p, urllib.parse.urlparse(u).path) for p in K.PY_IZIN)
                                                              for y, u in sh.cagri)))
    t.append(("PASS: istek tahmini loga, saglayici okumalarindan sonra", "TAHMIN istek" in log and log.index("[aday 5/5]") < log.index("TAHMIN istek")))
    t.append(("PASS: print_providers/{id} tekil saglayici basina 1", sum(1 for _, u in sh.cagri if re.search(r"/v1/catalog/print_providers/\d+\.json", u)) == 2))
    rc_out = io.StringIO()
    eski = K.ac
    K.ac = lambda *x, **y: (_ for _ in ()).throw(AssertionError("rapor modunda ag"))
    try:
        with contextlib.redirect_stdout(rc_out):
            r = K.rapor(d)
        ag = None
    except AssertionError as e:
        r, ag = None, str(e)
    finally:
        K.ac = eski
    rows = list(csv.DictReader(open(d / "KOLYE_KATALOG.csv", encoding="utf-8")))
    kargo = list(csv.DictReader(open(d / "KOLYE_KARGO.csv", encoding="utf-8")))
    md = (d / "KOLYE_KATALOG.md").read_text()
    t.append(("PASS: rapor ag acmadan 0", r == 0 and ag is None))
    t.append(("PASS: varyant tablosu (5 aday x 2 saglayici x 2 varyant)", len(rows) == 20 and all(x["maliyet"] == K.YOK for x in rows)))
    t.append(("PASS: placeholder px", any(x["placeholder_px"] == "front=1200x900; back=600x400" for x in rows)))
    tk = {x["blueprint_id"]: (x["teknik"], x["teknik_kaynak"]) for x in rows}
    t.append(("PASS: teknik 778 baskili (aciklama), 801 kazimali (aciklama), 802 kazimali (decoration_methods)",
              tk["778"] == ("baskili", "aciklama metni") and tk["801"] == ("kazimali", "aciklama metni")
              and tk["802"][0] == "kazimali" and tk["802"][1].startswith("decoration_methods")
              and tk["2947"][0] == "kazimali" and tk["9114"][0] == "belirsiz"))
    t.append(("FAIL: aciklama ve dekor yoksa belirsiz", K.teknik({"description": "A lovely heart"}, [{}])[0] == "belirsiz"))
    t.append(("FAIL: ikisi birden -> belirsiz", K.teknik({"description": "printed and engraved"}, [{}])[0] == "belirsiz"))
    us1 = [k for k in kargo if k["ulke"] == "US" and k["kaynak"] == "v1"]
    tr1 = [k for k in kargo if k["ulke"] == "TR" and k["kaynak"] == "v1"]
    t.append(("PASS: kargo v1 US 4.99 + 1.5, TR REST 9.99", us1 and us1[0]["ilk_adet"] == "4.99" and us1[0]["ek_adet"] == "1.5"
              and tr1 and tr1[0]["ilk_adet"] == "9.99" and us1[0]["teslim"] == "hazirlik 3 day"))
    us2 = [k for k in kargo if k["ulke"] == "US" and k["kaynak"].startswith("v2:standard")]
    t.append(("PASS: kargo v2 yontem basina, sent / 100, 'kargo suresi'", us2 and us2[0]["ilk_adet"] == "4.99"
              and us2[0]["teslim"] == "kargo suresi 2-5 gun" and us2[0]["not"] == ""))
    tr2 = [k for k in kargo if k["ulke"] == "TR" and k["kaynak"].startswith("v2:standard")]
    t.append(("PASS: REST_OF_THE_WORLD yedegi not sutununda (v1 ve v2)", tr1 and tr1[0]["not"] == "REST_OF_THE_WORLD profili"
              and us1[0]["not"] == "" and tr2 and tr2[0]["not"] == "REST_OF_THE_WORLD"))
    t.append(("PASS: 10 ulke", {k["ulke"] for k in kargo} == set(K.ULKELER) and "TR" in K.ULKELER))
    t.append(("PASS: MD aday basina 3 satir + maliyet API vermedi", len(re.findall(r"^- \*\*\d+ ", md, re.M)) == 5
              and len(re.findall(r"^  en kucuk baski alani", md, re.M)) == 5 and "Maliyet: API vermedi" in md))
    oz = [x for x in rc_out.getvalue().splitlines() if x.startswith("OZET printify")]
    t.append(("PASS: log ozeti (istek, aday, tablo)", any(re.search(r"OZET printify \| istek \d+ \| HTTP gonderim \d+ \| aday 5", x) for x in oz) and any(x.startswith("OZET printify | 778 | Oval Necklace | baskili | 2 | 600x400")
                                                                                            for x in oz)))
    # izin disi / GET disi
    with ortam(Sahte()):
        for yol in ("/v1/shops.json", "/v1/shops/1/products.json", "/v1/uploads/images.json", "/v1/catalog/blueprints/1/../../shops.json",
                    "//evil/v1/catalog/blueprints.json", "/v1/catalog/blueprints.json?x=1"):
            t.append((f"FAIL: izin disi yol {yol}", "DUR" in (dur(K.get, yol, ANAHTAR) or "")))
        for y in ("POST", "PUT", "DELETE", "PATCH"):
            t.append((f"FAIL: {y} DUR", "GET disi" in (dur(K.istek, y, "/v1/catalog/blueprints.json", ANAHTAR) or "")))
    t.append(("PASS: Printify IZIN listesi printify_kupa_oku.py ile ayni", K.PY_IZIN == __import__("ast").literal_eval(re.search(
        r"IZIN = (\[.*?\n\])", (Path(__file__).resolve().parent / "printify_kupa_oku.py").read_text(), re.S).group(1))))
    # aday > 40, 778 yok, tahmin > 600
    zor = [{"id": 778, "title": "Oval Necklace"}, {"id": 9114, "title": "Oval Pendant"}, {"id": 2947, "title": "Birthstone Circle Charm (Engraving)"}]
    _, _, h, _ = kos(Sahte(bps=zor + [{"id": 900 + i, "title": f"Pendant {i}"} for i in range(38)]))
    t.append(("FAIL: aday 41 > 40 DUR (2947 zorunlu sayilir)", h is not None and "aday 41 > 40" in h))
    _, kod_u, h_u, log_u = kos(Sahte(bps=[dict(zor[0], title="Oval Necklace V2")] + zor[1:]))
    t.append(("PASS: zorunlu ad uyusmazsa UYARI satiri, DUR degil", h_u is None and kod_u == 0
              and "UYARI: zorunlu blueprint 778 katalog adi 'Oval Necklace V2'" in log_u and log_u.count("UYARI: zorunlu") == 1))
    _, _, _, log_n = kos(Sahte())
    t.append(("PASS: ad uyusuyorsa UYARI yok", "UYARI: zorunlu" not in log_n))
    for z in (778, 9114, 2947):
        sh = Sahte(bps=[b for b in zor if b["id"] != z] + [{"id": 801, "title": "Pendant"}])
        _, _, h, _ = kos(sh)
        t.append((f"FAIL: zorunlu {z} katalogda yok -> DUR, baska istek yok", h is not None and "zorunlu blueprint katalogda yok" in h
                  and f"{z} (" in h and len(sh.cagri) == 1))
    sh = Sahte(saglayici=26)
    _, _, h, log = kos(sh)
    t.append(("FAIL: tahmin > 600 DUR, varyant istegi yok", h is not None and "tahmini" in h and not any(u.endswith("variants.json?show-out-of-stock=1")
                                                                                                 for _, u in sh.cagri)))
    # anahtar
    for ad, k_, msj in (("yok", None, "yok ya da bos"), ("bos", "  \n", "yok ya da bos"), ("icte bosluk", "PY KEY", "gecersiz"),
                        ("satir sonu", "PYKEY1\nPYKEY2", "gecersiz")):
        sh = Sahte()
        _, _, h, _ = kos(sh, k_)
        t.append((f"FAIL: anahtar {ad} -> DUR ({msj}), istek yok", h is not None and msj in h and sh.cagri == []))
    _, kod_b, h_b, _ = kos(Sahte(), "﻿" + ANAHTAR + " \n")
    t.append(("PASS: BOM + sondaki bosluk temizlenir", h_b is None and kod_b == 0))
    # 401 / 403 / 429 / diger 4xx
    for kod_ in (401, 403):
        _, _, h, _ = kos(Sahte(kod_yol={r"blueprints\.json$": kod_}))
        t.append((f"FAIL: {kod_} -> DUR anahtar ya da kapsam", h is not None and "anahtar ya da kapsam" in h))
    sh = Sahte()
    with ortam(sh):
        K.GONDERIM[0] = K.AZAMI_TAHMIN
        h = dur(K.get, "/v1/catalog/blueprints.json", ANAHTAR)
    t.append(("FAIL: HTTP gonderimi 600'e ulasti -> DUR (sert ust sinir), istek gitmez", h is not None and "sert ust sinir" in h and sh.cagri == []))
    sh = Sahte(kod_yol={r"blueprints\.json$": 429})
    with ortam(sh):
        dur(K.get, "/v1/catalog/blueprints.json", ANAHTAR)
        g429 = K.GONDERIM[0]
    t.append(("PASS: tekrarlar HTTP gonderimine sayilir (429 x4 = 4)", g429 == 4))
    sh = Sahte(kod_yol={r"blueprints\.json$": 429})
    _, _, h, _ = kos(sh)
    t.append(("FAIL: 429 x4 -> DUR '4 denemeden sonra', tam 4 deneme", h is not None and "429: 4 denemeden sonra" in h and len(sh.cagri) == 4))
    sh = Sahte(kod_yol={r"blueprints\.json$": 429})
    bekleme = []
    gs = K.time.sleep
    K.time.sleep = bekleme.append
    try:
        kos(sh)
    finally:
        K.time.sleep = gs
    t.append(("PASS: 429 ustel bekleme 5, 10, 20 sn (her istek oncesi 0,65)", [b for b in bekleme if b != K.BEKLE] == [5, 10, 20]
              and bekleme.count(K.BEKLE) == 4))
    d5, kod5, h5, _ = kos(Sahte(kod_yol={r"/variants\.json$": 404}))
    with contextlib.redirect_stdout(io.StringIO()):
        K.rapor(d5)
    r5 = list(csv.DictReader(open(d5 / "KOLYE_KATALOG.csv", encoding="utf-8")))
    t.append(("PASS: diger 4xx (404) -> alan API vermedi, aday surer", h5 is None and kod5 == 0 and r5 and all(x["varyant_id"] == K.YOK for x in r5)))
    # anahtar sizmaz: yansiyan anahtar ham ve logda maskeli; kesilen hata govdesinde de
    d6, _, _, log6 = kos(Sahte(yansit=True, kod_yol={r"/variants\.json$": 400}))
    ham6 = "".join(p.read_text() for p in (d6 / "ham").glob("*.json"))
    t.append(("PASS: anahtar ham dosyada ve logda yok", ANAHTAR not in ham6 and ANAHTAR[:10] not in ham6 and ANAHTAR not in log6 and "***" in ham6))
    K.SIRLAR[:] = [ANAHTAR]
    kes = K.kisa("x" * 290 + "Bearer " + ANAHTAR, 300)
    K.SIRLAR[:] = []
    t.append(("FAIL: kesme sinirindaki anahtar onek olarak sizmaz (once maskele, sonra kes)", ANAHTAR[:3] not in kes and kes.endswith("***")))
    t.append(("PASS: bekleme 0,65 sn (~92 istek/dk)", K.BEKLE == 0.65))
    gm = K.maskele
    K.maskele = lambda m: m
    try:
        d7, _, _, _ = kos(Sahte(yansit=True))
    finally:
        K.maskele = gm
    t.append(("KONTROL: sahte yansitma calisir (maskeleme kapaliyken anahtar hamda gorunur; ustteki PASS bos degil)", ANAHTAR in "".join(p.read_text() for p in (d7 / "ham").glob("*.json"))))
    # 30x: gercek yerel sunucu, yonlendirme takip edilmez
    gelen = []

    class B(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            gelen.append(self.headers.get("Authorization")); self.send_response(200); self.end_headers(); self.wfile.write(b"[]")

        def log_message(self, *a):
            pass
    sb = http.server.HTTPServer(("127.0.0.1", 0), B)

    class A(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302); self.send_header("Location", f"http://127.0.0.1:{sb.server_port}/v1/shops.json"); self.end_headers()

        def log_message(self, *a):
            pass
    sa = http.server.HTTPServer(("127.0.0.1", 0), A)
    for sv in (sa, sb):
        threading.Thread(target=sv.serve_forever, daemon=True).start()
    eski_api = K.API
    K.API = f"http://127.0.0.1:{sa.server_port}"
    try:
        k3, _ = K.get("/v1/catalog/blueprints.json", ANAHTAR)
    finally:
        K.API = eski_api
        sa.shutdown(); sb.shutdown()
    t.append(("FAIL: 302 takip edilmez, anahtar baska hosta gitmez", k3 == 302 and gelen == []))
    # tarama
    kaynak = (Path(__file__).resolve().parent / "kolye_katalog.py").read_text()
    t.append(("PASS: tarama: requests yok, GET disi cagri yok", not re.search(r"^\s*(import|from)\s+requests|method=\"(POST|PUT|PATCH|DELETE)\"|"
                                                                              r"\.(post|put|patch|delete)\(", kaynak, re.M)))
    return t


def main():
    t = testler()
    for ad, ok in t:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in t)
    print(f"kolye_katalog testleri TOPLAM: {n}/{len(t)} PASS")
    sys.exit(0 if n == len(t) else 1)


if __name__ == "__main__":
    main()
