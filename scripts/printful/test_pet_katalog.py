#!/usr/bin/env python3
"""pet_katalog sahte API testi (gercek istek YOK: urllib.request.urlopen taklit edilir; taklit disi cagri testi FAIL eder).
Her kural icin bilinen PASS + bilinen FAIL: izin listesi disi POST, Printify'da GET disi istek, aday regex'i, aday > 40 DUR,
Printify anahtari yokken atlama, token / anahtar ham dosyaya ve loga yazilmaz, rapor modu ag acmaz. Inceleme tur 1 (9 Kas): yonlendirme
takip edilmez (gercek yerel HTTP sunucusu), JSON olmayan 200 / baglanti kopmasi, hata govdesinde kesilen token, cok satirli anahtar,
harf boyu sirasi (Printful sizes L,M,S,XL), Printify aday asimi Printful'u durdurmaz, kargo tamamen basarisizsa FAIL."""
import contextlib
import http.server
import io
import threading
import json
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pet_katalog as P  # noqa: E402

P.time.sleep = lambda s: None
TOK, KEY = "PFTOKEN_sahte_9f8e7d", "PYKEY_sahte_1a2b3c"


class Yanit:
    def __init__(self, kod, veri, ham=None):
        self.status, self._b = kod, (ham if ham is not None else json.dumps(veri).encode())

    def read(self, *a):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Sahte:
    """Sahte Printful + Printify. cagri: (yontem, url, govde)."""
    def __init__(self, urunler=None, v2=None, py_bp=None, yansit=False, html_post=None, kopma=None, kargo_kod=200,
                 hata_govde=False):
        self.cagri, self.yansit = [], yansit
        self.html_post, self.kopma, self.kargo_kod, self.hata_govde = html_post, kopma, kargo_kod, hata_govde
        self.urunler = urunler if urunler is not None else [
            {"id": 902, "title": "Pet Bandana Collar", "type_name": "Pet Bandana", "model": "Pet Bandana Collar"},
            {"id": 500, "title": "Throw Blanket", "type_name": "Blanket", "model": "Throw Blanket"},
            {"id": 1, "title": "Ornament", "type_name": "Ornament"}, {"id": 2, "title": "Carpet", "type_name": "Carpet"},
            {"id": 3, "title": "Petite Tee", "type_name": "T-Shirt"},
            {"id": 4, "title": "Sherpa Jacket", "type_name": "Jacket", "description": "warm like a blanket, pillow soft"}]
        self.v2 = v2 if v2 is not None else [{"id": 500, "name": "Throw Blanket", "type": "BLANKET"},
                                             {"id": 600, "name": "Basic Pillow", "type": "PILLOW"}]
        self.py_bp = py_bp if py_bp is not None else [{"id": 77, "title": "Pet Bandana"},
                                                      {"id": 78, "title": "Velveteen Plush Blanket"},
                                                      {"id": 79, "title": "Ceramic Ornament"}]

    def __call__(self, req, timeout=None):
        url, yontem = req.full_url, req.get_method()
        govde = json.loads(req.data) if req.data else None
        self.cagri.append((yontem, url, govde))
        u = urllib.parse.urlparse(url)
        yol = u.path
        yan = {"auth_yansima": req.headers.get("Authorization")} if self.yansit else {}
        if u.netloc == "api.printify.com":
            if yol == "/v1/catalog/blueprints.json":
                return Yanit(200, self.py_bp)
            if re.fullmatch(r"/v1/catalog/blueprints/\d+\.json", yol):
                return Yanit(200, {"id": 77, "title": "Pet Bandana", "model": "Bandana", **yan})
            if yol.endswith("/print_providers.json"):
                return Yanit(200, [{"id": 5, "title": "Sahte Saglayici"}])
            if re.fullmatch(r"/v1/catalog/print_providers/\d+\.json", yol):
                return Yanit(200, {"id": 5, "location": {"country": "US", "region": "NC"}})
            if yol.endswith("/variants.json"):
                return Yanit(200, {"variants": [{"id": 1, "title": "S", "options": {"size": "S"}, "is_available": True,
                                                 "placeholders": [{"position": "front", "width": 3000, "height": 2000}]}]})
            if yol.startswith("/v1/") and yol.endswith("/shipping.json"):
                return Yanit(200, {"profiles": [{"countries": ["US"], "first_item": {"cost": 499}, "additional_items": {"cost": 200}},
                                                {"countries": ["REST_OF_THE_WORLD"], "first_item": {"cost": 999},
                                                 "additional_items": {"cost": 500}}]})
            if yol.startswith("/v2/") and yol.endswith("/shipping.json"):
                return Yanit(200, {"data": [{"id": "standard", "attributes": {"name": "standard"}}]})
            if yol.startswith("/v2/"):
                return Yanit(200, {"data": []})
            raise AssertionError(f"sahte: bilinmeyen Printify {yol}")
        assert u.netloc == "api.printful.com", url
        if self.kopma is not None and len(self.cagri) == self.kopma:
            raise ConnectionResetError("sahte kopma")
        if yontem == "POST":
            if self.html_post is not None and sum(1 for c in self.cagri if c[0] == "POST") == self.html_post:
                return Yanit(200, None, ham=b"<html>bakim</html>")
            if self.kargo_kod != 200:
                raise urllib.error.HTTPError(url, self.kargo_kod, "x", {}, io.BytesIO(b'{"error":{"message":"bad"}}'))
            if yol == "/shipping/rates":
                return Yanit(200, {"result": [{"id": "STANDARD", "rate": "6.50", "minDeliveryDays": 4, "maxDeliveryDays": 8}], **yan})
            if yol == "/v2/shipping-rates":
                return Yanit(200, {"data": [{"shipping": "STANDARD", "rate": "6.50", "shipments": [{"departure_country": "LV"}]}]})
            raise AssertionError(f"sahte: bilinmeyen POST {yol}")
        if yol == "/products":
            if self.hata_govde:                     # API hata govdesinde token'i yansitir; token 5000. karakterde kesilir
                g = ("x" * 4990 + (req.headers.get("Authorization") or "")).encode()
                raise urllib.error.HTTPError(url, 400, "x", {}, io.BytesIO(g))
            return Yanit(200, {"result": self.urunler, **yan})
        if yol == "/v2/catalog-products":
            return Yanit(200, {"data": self.v2, "paging": {"total": len(self.v2)}})
        m = re.fullmatch(r"/products/(\d+)", yol)
        if m:
            pid = int(m.group(1))
            vs = ([{"id": 9021, "size": "S", "price": "12.00", "in_stock": True}, {"id": 9022, "size": "L", "price": "13.00"}]
                  if pid == 902 else [{"id": pid * 10 + 1, "size": "50″×60″", "price": "30.00"},
                                      {"id": pid * 10 + 2, "size": "60″×80″", "price": "40.00"}])
            return Yanit(200, {"result": {"product": {"id": pid, "title": f"Urun {pid}", "type_name": "X"}, "variants": vs}})
        m = re.fullmatch(r"/v2/catalog-products/(\d+)/catalog-variants", yol)
        if m:
            pid = int(m.group(1))
            vs = ([{"id": 9022, "size": "L"}, {"id": 9023, "size": "M"}, {"id": 9021, "size": "S"}, {"id": 9024, "size": "XL"}]
                  if pid == 902 else
                  [{"id": pid * 10 + 3, "size": "60″×80″"}, {"id": pid * 10 + 1, "size": "50″×60″"}, {"id": pid * 10 + 2, "size": "60″×80″"}])
            return Yanit(200, {"data": vs, "paging": {"total": len(vs)}})
        m = re.fullmatch(r"/v2/catalog-products/(\d+)", yol)
        if m:
            return Yanit(200, {"data": {"id": int(m.group(1)), "sizes": ["L", "M", "S", "XL"], "placements": [{"placement": "front",
                                                                                                        "technique": "sublimation"}]}})
        if yol.startswith("/products/") or yol.startswith("/mockup-generator/") or yol.startswith("/v2/catalog-products/"):
            return Yanit(200, {"result": {}, "data": []})
        raise AssertionError(f"sahte: bilinmeyen GET {yol}")


@contextlib.contextmanager
def ortam(sahte, anahtar=None):
    eski, eski_ac = P.urllib.request.urlopen, P.ac
    P.urllib.request.urlopen = P.ac = sahte
    P.ISTEKLER.clear()
    os.environ["PRINTFUL_TOKEN"] = TOK
    if anahtar:
        os.environ["PRINTIFY_API_KEY"] = anahtar
    else:
        os.environ.pop("PRINTIFY_API_KEY", None)
    try:
        yield
    finally:
        P.urllib.request.urlopen, P.ac = eski, eski_ac
        for k in ("PRINTFUL_TOKEN", "PRINTIFY_API_KEY", "PRINTIFY_DURUM"):
            os.environ.pop(k, None)


def kos(sahte, anahtar=None):
    d = pathlib.Path(tempfile.mkdtemp(prefix="pet_katalog_test_"))
    out = io.StringIO()
    hata = None
    with ortam(sahte, anahtar), contextlib.redirect_stdout(out):
        try:
            kod = P.oku(d / "ham")
        except SystemExit as e:
            kod, hata = None, str(e.code)
    return d, kod, hata, out.getvalue()


def dur(f, *a):
    try:
        f(*a)
    except SystemExit as e:
        return str(e.code)
    return None


def testler():  # noqa: C901
    s = []
    # regex (yalniz baslik / tur / model / ad)
    for ad in ("Pet Bandana Collar", "Throw Blanket", "Basic Pillow", "Floor Cushion", "Dog Bandana"):
        s.append((f"PASS: regex eslesir {ad!r}", P.eslesme([ad])[0]))
    for ad in ("Ornament", "Carpet", "Petite Tee", "Sherpa Jacket", "Blanketing Fabric", "Pillowcase Mug"):
        s.append((f"FAIL: regex eslesmez {ad!r}", not P.eslesme([ad])[0]))
    s.append(("pet/dog isareti", P.eslesme(["Pet Bandana Collar"]) == (True, True) and P.eslesme(["Throw Blanket"]) == (True, False)))

    # tam kosu, anahtarsiz
    sh = Sahte()
    d, kod, hata, log = kos(sh)
    ad = json.loads((d / "ham" / "_adaylar_printful.json").read_text())
    s.append(("PASS: anahtarsiz kosu 0", kod == 0 and hata is None))
    s.append(("PASS: adaylar 500, 600, 902 (zorunlu)", sorted(ad, key=int) == ["500", "600", "902"]))
    s.append(("FAIL: aciklamadaki 'blanket' aday yapmaz (Sherpa Jacket 4)", "4" not in ad))
    s.append(("FAIL: Ornament / Carpet / Petite Tee aday degil", not {"1", "2", "3"} & set(ad)))
    pyd = json.loads((d / "ham" / "_printify.json").read_text())
    s.append(("PASS: Printify anahtari yok -> atlandi, metin raporda", pyd.get("durum") == "atlandi" and pyd.get("neden") == P.PRINTIFY_YOK
              and P.PRINTIFY_YOK in log))
    s.append(("FAIL: anahtar yokken Printify'a istek yok", not any("printify" in u for _, u, _ in sh.cagri)))
    post = [(y, urllib.parse.urlparse(u).path) for y, u, _ in sh.cagri if y == "POST"]
    s.append(("PASS: POST yalniz iki kargo yolu", post and {p for _, p in post} == P.POST_IZIN))
    plan = json.loads((d / "ham" / "_kargo_plani.json").read_text())
    s.append(("PASS: kargo plani 3 urun x 2 varyant x 10 ulke", len(plan) == 60 and {x["ulke"] for x in plan} == set(P.ULKELER)))
    tr = [g for y, u, g in sh.cagri if y == "POST" and g["recipient"]["country_code"] == "TR"]
    s.append(("PASS: TR adresi Istanbul 34000", tr and all(g["recipient"]["city"] == "Istanbul" and g["recipient"]["zip"] == "34000"
                                                          for g in tr)))
    s.append(("PASS: tahmini istek kargo oncesi loga", "TAHMIN kargo: 60" in log and log.index("TAHMIN kargo") < log.index("[kargo ")))
    v902 = sorted({x["varyant"] for x in plan if x["urun"] == "902"})
    v500 = sorted({x["varyant"] for x in plan if x["urun"] == "500"})
    s.append(("PASS: en kucuk/en buyuk boy (902 Printful sirasi L,M,S,XL -> S + XL; 500 50x60=5001, 60x80 esit -> kucuk id 5002)",
              v902 == [9021, 9024] and v500 == [5001, 5002]))
    s.append(("FAIL: Printful sizes sirasina guvenilseydi 902 en kucuk L olurdu (yakalanir)", 9022 not in v902))
    s.append(("FAIL: kargo sorgusunda siparis ucu yok", not any(re.search(r"/orders|/files|/store|/mockup-generator/create", u)
                                                                for _, u, _ in sh.cagri)))

    # rapor: ag acmaz
    def ag_yasak(*a, **k):
        raise AssertionError("rapor modunda ag")
    eski, eski_ac = P.urllib.request.urlopen, P.ac
    P.urllib.request.urlopen = P.ac = ag_yasak
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = P.rapor(d)
        ag = None
    except AssertionError as e:
        r, ag = None, str(e)
    finally:
        P.urllib.request.urlopen, P.ac = eski, eski_ac
    md = (d / "PET_KATALOG.md").read_text() if (d / "PET_KATALOG.md").exists() else ""
    s.append(("PASS: rapor ag acmadan 0", r == 0 and ag is None))
    s.append(("PASS: rapor dosyalari", all((d / f).exists() for f in ("PET_KATALOG.csv", "PET_KARGO.csv", "PET_KATALOG.md"))))
    s.append(("PASS: MD aday basina 3 satir", len(re.findall(r"^- \*\*Printful ", md, re.M)) == 3
              and len(re.findall(r"^  baski dosyasi:", md, re.M)) == 3 and len(re.findall(r"^  kargo USD:", md, re.M)) == 3))
    s.append(("PASS: MD Printify durumu yazili", P.PRINTIFY_YOK in md))
    rows = list(__import__("csv").DictReader(open(d / "PET_KATALOG.csv", encoding="utf-8")))
    s.append(("PASS: CSV alanlari (tedarikci, urun, varyant, fiyat, baski olcusu, uretim yeri)",
              rows and {"tedarikci", "urun_adi", "varyant_id", "fiyat_usd_v1", "baski_dosyasi_px", "uretim_yeri_v2_cikis"} <= set(rows[0])))
    s.append(("PASS: API vermedigi alan 'API vermedi'", any(x["baski_dosyasi_px"] == P.YOK for x in rows)))
    P.urllib.request.urlopen = P.ac = ag_yasak
    try:
        P.istek("/products", TOK)
        ag_yakalandi = False
    except AssertionError:
        ag_yakalandi = True
    finally:
        P.urllib.request.urlopen, P.ac = eski, eski_ac
    s.append(("FAIL: ag cagrisi olursa ag_yasak yakalar (rapor testi anlamli)", ag_yakalandi))

    # izin listesi disi POST / gecersiz yol
    sh2 = Sahte()
    with ortam(sh2):
        for yol in ("/orders", "/orders?confirm=1", "/shipping/rates/x", "/v2/orders", "/v2/shipping-rates/../orders", "/files",
                    "/mockup-generator/create-task/1"):
            s.append((f"FAIL: izinsiz POST {yol} durur", "DUR" in (dur(P.istek, yol, TOK, {"a": 1}) or "")))
        s.append(("FAIL: tam URL / host degisimi durur", "DUR" in (dur(P.istek, "//evil.example/x", TOK) or "")
                  and "DUR" in (dur(P.istek, "https://evil.example/x", TOK) or "")))
        n0 = len(sh2.cagri)
        k, j = P.istek("/shipping/rates", TOK, {"recipient": {"country_code": "US"}, "items": []})
    s.append(("PASS: izinli POST /shipping/rates gider", n0 == 0 and k == 200 and len(sh2.cagri) == 1))
    s.append(("FAIL: durdurulan POST'larda istek gitmedi", n0 == 0))

    # Printify: GET disi / izin disi
    sh3 = Sahte()
    with ortam(sh3, KEY):
        for y in ("POST", "PUT", "DELETE", "PATCH"):
            s.append((f"FAIL: Printify {y} durur", "GET disi" in (dur(P.py_istek, y, "/v1/catalog/blueprints.json", KEY) or "")))
        for yol in ("/v1/shops.json", "/v1/shops/1/products.json", "/v1/catalog/blueprints.json/../shops.json", "/v1/uploads/images.json"):
            s.append((f"FAIL: Printify izin disi GET {yol}", "izinsiz" in (dur(P.py_istek, "GET", yol, KEY) or "")))
        n0 = len(sh3.cagri)
        j = P.py_istek("GET", "/v1/catalog/blueprints.json", KEY)
    s.append(("PASS: Printify izinli GET", n0 == 0 and isinstance(j, list) and len(sh3.cagri) == 1))
    s.append(("PASS: Printify IZIN listesi printify_kupa_oku.py ile ayni", P.PY_IZIN == __import__("ast").literal_eval(
        re.search(r"IZIN = (\[.*?\n\])", (P.Path(__file__).resolve().parents[1] / "printify" / "printify_kupa_oku.py").read_text(),
                  re.S).group(1))))

    # anahtarli tam kosu + yansima (sahte API Authorization basligini yanita koyar): ham + log maskeli
    sh4 = Sahte(yansit=True)
    d4, kod4, hata4, log4 = kos(sh4, KEY)
    hamtxt = "".join(p.read_text() for p in (d4 / "ham").rglob("*.json"))
    s.append(("PASS: anahtarli kosu 0, Printify okundu", kod4 == 0 and json.loads((d4 / "ham" / "_printify.json").read_text())["durum"]
              == "okundu"))
    s.append(("PASS: Printify adaylari 77, 78 (79 Ornament degil)", sorted(json.loads((d4 / "ham" / "_adaylar_printify.json")
                                                                              .read_text()), key=int) == ["77", "78"]))
    s.append(("PASS: Printify istekleri yalniz GET", all(y == "GET" for y, u, _ in sh4.cagri if "printify" in u)))
    gm = P.maskele
    P.maskele = lambda m: m                      # bilinen FAIL: maskeleme kapali -> yansiyan token ham dosyaya duser (test anlamli)
    try:
        d4b, _, _, _ = kos(Sahte(yansit=True), KEY)
    finally:
        P.maskele = gm
    s.append(("FAIL (bilinen): maskeleme kapaliyken token hamda gorunur", TOK in "".join(p.read_text() for p in (d4b / "ham").rglob("*.json"))))
    s.append(("PASS: token ve anahtar ham dosyada yok", TOK not in hamtxt and KEY not in hamtxt and "Bearer PF" not in hamtxt
              and "***" in hamtxt))
    s.append(("PASS: token ve anahtar logda yok", TOK not in log4 and KEY not in log4))
    s.append(("PASS: istek kaydinda baslik yok", "Authorization" not in (d4 / "ham" / "_istekler.json").read_text()))
    with contextlib.redirect_stdout(io.StringIO()):
        P.rapor(d4)
    cikti = "".join(p.read_text() for p in d4.iterdir() if p.is_file())
    s.append(("PASS: rapor ciktilarinda token / anahtar yok", TOK not in cikti and KEY not in cikti))
    s.append(("PASS: MD Printify adaylari", len(re.findall(r"^- \*\*Printify ", (d4 / "PET_KATALOG.md").read_text(), re.M)) == 2))

    # aday > 40 -> DUR, detay / kargo istegi yok
    cok = [{"id": 1000 + i, "title": f"Sherpa Blanket {i}"} for i in range(41)]
    sh5 = Sahte(urunler=cok, v2=[])
    d5, kod5, hata5, log5 = kos(sh5)
    s.append(("FAIL: aday 42 > 40 -> DUR", hata5 is not None and "aday sayisi" in hata5))
    s.append(("FAIL: DUR'da detay / kargo istegi yok", len(sh5.cagri) == 2 and not any(y == "POST" for y, _, _ in sh5.cagri)))
    s.append(("PASS: DUR'da aday listesi yazildi", len(json.loads((d5 / "ham" / "_adaylar_printful.json").read_text())) == 42
              and (d5 / "ham" / "_dur.json").exists()))
    s.append(("FAIL: Printful DUR'da Printify istegi yok", not any("printify" in u for _, u, _ in sh5.cagri)))
    ok40 = [{"id": 1000 + i, "title": f"Sherpa Blanket {i}"} for i in range(39)]
    sh6 = Sahte(urunler=ok40, v2=[])
    d6, kod6, hata6, _ = kos(sh6)
    s.append(("PASS: aday 40 (39 + 902) DUR yok", hata6 is None and kod6 == 0))
    sh7 = Sahte(py_bp=[{"id": i, "title": f"Pillow {i}"} for i in range(41)])
    d7, kod7, hata7, log7 = kos(sh7, KEY)
    pyd7 = json.loads((d7 / "ham" / "_printify.json").read_text())
    s.append(("FAIL: Printify aday 41 > 40 -> yalniz Printify DUR, kosu 1", hata7 is None and kod7 == 1 and pyd7["durum"] == "DUR"))
    s.append(("PASS: Printify asiminda Printful kargo surdu", len(json.loads((d7 / "ham" / "kargo_v1.json").read_text())) == 60
              and sum(1 for _, u, _ in sh7.cagri if "printify" in u) == 1))

    # token yok
    with ortam(Sahte()):
        os.environ.pop("PRINTFUL_TOKEN")
        s.append(("FAIL: PRINTFUL_TOKEN yok -> DUR", "PRINTFUL_TOKEN yok" in (dur(P.oku, pathlib.Path(tempfile.mkdtemp())) or "")))
    # kucuk / buyuk
    s.append(("PASS: boy bilgisi yoksa en kucuk id", [v["id"] for v, _ in P.kucuk_buyuk([{"id": 9, "size": "?"}, {"id": 3, "size": "?"}],
                                                                                      [])] == [3]))
    s.append(("PASS: tek boy -> tek varyant", len(P.kucuk_buyuk([{"id": 1, "size": "One size"}], ["One size"])) == 1))
    # --- inceleme tur 1 ---
    # yonlendirme: gercek yerel HTTP sunucusu A 302 -> B; B'ye istek GITMEZ (token tasinmaz)
    B_say = []

    class B(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            B_say.append(self.headers.get("Authorization")); self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
        do_POST = do_GET

        def log_message(self, *a):
            pass
    sb = http.server.HTTPServer(("127.0.0.1", 0), B)

    class A(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302); self.send_header("Location", f"http://127.0.0.1:{sb.server_port}/v1/shops.json"); self.end_headers()
        do_POST = do_GET

        def log_message(self, *a):
            pass
    sa = http.server.HTTPServer(("127.0.0.1", 0), A)
    for sv in (sa, sb):
        threading.Thread(target=sv.serve_forever, daemon=True).start()
    eski_pf, eski_py = P.PF_API, P.PY_API
    P.PF_API = P.PY_API = f"http://127.0.0.1:{sa.server_port}"
    try:
        k_g, _ = P.istek("/products", TOK)
        k_p, _ = P.istek("/shipping/rates", TOK, {"a": 1})
        j_y = P.py_istek("GET", "/v1/catalog/blueprints.json", KEY)
    finally:
        P.PF_API, P.PY_API = eski_pf, eski_py
        sa.shutdown(); sb.shutdown()
    s.append(("FAIL: 302 takip edilmez, token baska hosta gitmez (GET, POST, Printify)", k_g == 302 and k_p == 302
              and j_y.get("_hata") == 302 and B_say == []))
    s.append(("PASS: urllib varsayilani 302'yi takip ederdi (test anlamli)", issubclass(P.YonlendirmeYok, P.urllib.request.HTTPRedirectHandler)
              and P.YonlendirmeYok().redirect_request(None, None, 302, "", {}, "http://x/") is None))
    # JSON olmayan 200 kargo yaniti + baglanti kopmasi
    sh8 = Sahte(html_post=10, kopma=5)
    d8, kod8, hata8, _ = kos(sh8)
    k8 = json.loads((d8 / "ham" / "kargo_v1.json").read_text()) + json.loads((d8 / "ham" / "kargo_v2.json").read_text())
    s.append(("FAIL: HTML 200 yaniti kosuyu dusurmez, kargo dosyalari tam", hata8 is None and kod8 == 0 and len(k8) == 120
              and any("ham" in (x.get("yanit") or {}) for x in k8)))
    s.append(("PASS: baglanti kopmasi ayni istekle yeniden denenir", hata8 is None and kod8 == 0 and sh8.cagri[4][:2] == sh8.cagri[5][:2]))
    # kargo tamamen basarisiz -> 1
    d9, kod9, hata9, log9 = kos(Sahte(kargo_kod=400))
    s.append(("FAIL: kargo sorgularinin hicbiri 200 degil -> kosu 1", kod9 == 1 and "hicbiri 200" in log9))
    # hata govdesinde token: once maskele sonra kes
    d10, kod10, hata10, log10 = kos(Sahte(hata_govde=True))
    ham10 = "".join(p.read_text() for p in (d10 / "ham").rglob("*.json"))
    s.append(("FAIL: kesilen hata govdesinde token oneki yok", TOK[:10] not in ham10 and TOK[:10] not in log10 and kod10 == 1))
    # cok satirli / bosluklu anahtar -> Printify atlanir, istek yok, traceback yok
    sh11 = Sahte()
    d11, kod11, hata11, log11 = kos(sh11, "PYKEY_satir1\nPYKEY_satir2")
    pyd11 = json.loads((d11 / "ham" / "_printify.json").read_text())
    s.append(("FAIL: cok satirli anahtar -> Printify atlandi (bicim), istek yok", pyd11["durum"] == "atlandi" and "bicimi" in pyd11["neden"]
              and not any("printify" in u for _, u, _ in sh11.cagri) and "PYKEY_satir2" not in log11 and "PYKEY_satir1" not in log11))
    with ortam(Sahte()):
        os.environ["PRINTFUL_TOKEN"] = "PF ARALIKLI"
        s.append(("FAIL: bosluklu Printful token -> DUR", "bicimi" in (dur(P.oku, pathlib.Path(tempfile.mkdtemp())) or "")))
    # Printify kargo: en kucuk + en buyuk varyant, profil variant_ids
    k4 = list(__import__("csv").DictReader(open(d4 / "PET_KARGO.csv", encoding="utf-8")))
    s.append(("PASS: Printify kargo satiri varyant + etiket", any(x["tedarikci"] == "Printify" and x["varyant_etiket"] == "en kucuk"
                                                                    for x in k4)))
    return s


def main():
    s = testler()
    for ad, ok in s:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in s)
    print(f"pet_katalog testleri TOPLAM: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
