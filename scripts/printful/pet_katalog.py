#!/usr/bin/env python3
"""Pet urun adaylari (battaniye, yastik, evcil hayvan bandanasi) katalog SALT OKUMA (Serdar 9 Kas 2026 "ok").
Yalniz standart kutuphane (urllib). Etsy'ye dokunmaz. Siparis, urun, sablon, mockup gorevi, yukleme OLUSTURULMAZ.

Printful: GET + kargo ucreti sorgusu. POST yalniz POST_IZIN'deki iki yol (tam yol eslesmesi, sorgu dizesi haric); baska her POST
  ve host / yol disi istek betigi durdurur (emsal ornament_katalog.py).
Printify (istege bagli): yalniz GET, yalniz PY_IZIN'deki /catalog uclari (printify_kupa_oku.py:25-33 aynen, tam eslesme). Anahtar
  (env PRINTIFY_API_KEY) yoksa ya da bossa Printify adimi atlanir, kosu FAIL olmaz. Printify katalog API'si maliyet vermez.

Kullanim:
  pet_katalog.py oku <ham_klasor>      env PRINTFUL_TOKEN (zorunlu), PRINTIFY_API_KEY (istege bagli). Ham API yanitlari yazilir;
                                       token / anahtar hicbir dosyaya ve loga yazilmaz (istek basliklari kaydedilmez, yazimda maskelenir).
  pet_katalog.py rapor <cikti_klasor>  AG YOK; <cikti>/ham'dan PET_KATALOG.csv, PET_KARGO.csv, PET_KATALOG.md uretir.

Aday kurali (yalniz baslik / tur / model / ad alani; aciklama DEGIL): \\bblanket\\b, \\bpillow\\b, \\bcushion\\b, \\bbandana\\b
  (\\bpet\\b / \\bdog\\b ayrica isaretlenir). Zorunlu: Printful 902 (Pet Bandana Collar). Tedarikci basina aday > AZAMI_ADAY ise
  agdaki sonraki adimlara gecmeden DUR (aday listesi ham/_adaylar*.json ve loga yazilir).
Kargo (Printful): her adayin en kucuk ve en buyuk varyanti (v2 boy bilgisi; esitlikte kucuk varyant id) x ULKELER, 1 adet, USD,
  v1 /shipping/rates + v2 /v2/shipping-rates. Printify: v1 + v2 kargo profilleri (GET). API'nin vermedigi alan: "API vermedi"."""
import csv
from http.client import HTTPException
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PF_API = "https://api.printful.com"
PY_API = "https://api.printify.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops"
POST_IZIN = {"/shipping/rates", "/v2/shipping-rates"}
PY_IZIN = [
    r"/v1/catalog/blueprints\.json",
    r"/v1/catalog/blueprints/\d+\.json",
    r"/v1/catalog/blueprints/\d+/print_providers\.json",
    r"/v1/catalog/blueprints/\d+/print_providers/\d+/(variants|shipping)\.json",
    r"/v1/catalog/print_providers/\d+\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping/[a-z_]+\.json",
]
ULKELER = "US CA GB DE FR IT ES NL AU TR".split()
ADRES = {"US": {"state_code": "NY", "city": "New York", "zip": "10001"},
         "CA": {"state_code": "ON", "city": "Toronto", "zip": "M5V 2T6"},
         "GB": {"city": "London", "zip": "SW1A 1AA"}, "DE": {"city": "Berlin", "zip": "10115"},
         "FR": {"city": "Paris", "zip": "75001"}, "IT": {"city": "Rome", "zip": "00184"},
         "ES": {"city": "Madrid", "zip": "28001"}, "NL": {"city": "Amsterdam", "zip": "1012 JS"},
         "AU": {"state_code": "NSW", "city": "Sydney", "zip": "2000"},
         "TR": {"city": "Istanbul", "zip": "34000"}}
ZORUNLU = [902]
AZAMI_ADAY = 40
KELIME = re.compile(r"\b(?:blanket|pillow|cushion|bandana)\b", re.I)
PET = re.compile(r"\b(?:pet|dog)\b", re.I)
PF_ALAN = {"v1": ("title", "type_name", "model", "type"), "v2": ("name", "type", "model")}
BOY_SIRA = ["XXS", "XS", "S", "M", "L", "XL", "2XL", "XXL", "3XL", "4XL", "5XL"]
BICIM = re.compile(r"^\S+$")                    # token / anahtar: bosluk ve satir sonu YOK
YOK = "API vermedi"
PRINTIFY_YOK = "Printify anahtari yok (71c1afc kaydi, is sonunda silinmis)"
ISTEKLER = []
SIRLAR = []
PF_BEKLE = 0.35
PY_BEKLE = 0.4


def maskele(metin):
    for s in SIRLAR:
        if s:
            metin = metin.replace(s, "***")
    return metin


def kisa(metin, n):
    """Once maskele, SONRA kes (kesilen yarim sir maskeden kacmaz)."""
    return maskele(str(metin))[:n]


class YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    """30x takip EDILMEZ: urllib yonlendirmede Authorization basligini yeni hosta tasir ve hedef yol izin listesinden gecmez.
    30x HTTPError olarak doner, istek kaydina yazilir."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ACICI = urllib.request.build_opener(YonlendirmeYok)


def ac(req, timeout=60):
    return _ACICI.open(req, timeout=timeout)


def json_coz(b):
    """Govde -> json; JSON degilse {"ham": maskeli + kisa metin} (200 HTML yaniti kosuyu dusurmez)."""
    t = b.decode(errors="replace") if isinstance(b, (bytes, bytearray)) else str(b)
    try:
        return json.loads(t)
    except ValueError:
        return {"ham": kisa(t, 5000)}


def log(m):
    print(maskele(str(m)), flush=True)


def yaz(p, veri):
    p.write_text(maskele(json.dumps(veri, indent=1, ensure_ascii=False)), encoding="utf-8")


def sar(yontem, yol, govde, kod, j):
    return {"istek": {"yontem": yontem, "yol": yol, "govde": govde}, "http": kod, "yanit": j}


def _yol_ok(yol):
    return isinstance(yol, str) and yol.startswith("/") and "//" not in yol and "://" not in yol and "@" not in yol.split("?")[0]


# ----------------------------------------------------------------------------------------------------------- Printful
def istek(yol, token, veri=None):
    """Printful. veri None -> GET, aksi POST. POST yalniz POST_IZIN (tam yol). -> (http, json)."""
    yontem = "POST" if veri is not None else "GET"
    if not _yol_ok(yol):
        raise SystemExit(f"DUR: gecersiz yol {yol!r}")
    if yontem == "POST" and yol.split("?")[0] not in POST_IZIN:
        raise SystemExit(f"DUR: izinsiz POST {yol}")
    kod, j = 0, {}
    for deneme in range(6):
        req = urllib.request.Request(PF_API + yol, data=json.dumps(veri).encode() if veri is not None else None,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                              "User-Agent": UA, "Accept": "application/json"}, method=yontem)
        try:
            with ac(req, timeout=60) as r:
                kod, j = r.status, json_coz(r.read())
        except urllib.error.HTTPError as e:
            govde = kisa(e.read().decode(errors="replace"), 5000)
            if e.code in (429, 500, 502, 503, 504) and deneme < 5:
                try:
                    bekle = int(e.headers.get("Retry-After") or 0)
                except ValueError:
                    bekle = 0
                bekle = min(max(bekle, 15 * (deneme + 1)), 90)
                log(f"  {yontem} {yol} HTTP {e.code}, {bekle}s bekleniyor")
                time.sleep(bekle)
                continue
            kod = e.code
            j = json_coz(govde)
        except (urllib.error.URLError, TimeoutError, ConnectionError, HTTPException) as e:
            if deneme < 5:
                time.sleep(10)
                continue
            kod, j = 0, {"hata": type(e).__name__}
        break
    ISTEKLER.append({"tedarikci": "printful", "yontem": yontem, "yol": yol, "http": kod,
                     "zaman": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    time.sleep(PF_BEKLE)
    return kod, j


# ----------------------------------------------------------------------------------------------------------- Printify
def py_istek(yontem, yol, anahtar, params=None):
    """Printify: YALNIZ GET ve PY_IZIN (tam eslesme). -> json ya da {"_hata": kod, ...}."""
    if yontem != "GET":
        raise SystemExit(f"DUR: Printify'da GET disi istek ({yontem} {yol})")
    if not _yol_ok(yol) or not any(re.fullmatch(p, yol) for p in PY_IZIN):
        raise SystemExit(f"DUR: Printify izinsiz uc (istek atilmadi): GET {yol}")
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    j = {"_hata": 429, "_metin": "hiz limiti"}
    kod = 429
    for deneme in range(4):
        time.sleep(PY_BEKLE)
        req = urllib.request.Request(PY_API + yol + q, headers={"Authorization": f"Bearer {anahtar}", "User-Agent": UA,
                                                                 "Accept": "application/json"}, method="GET")
        try:
            with ac(req, timeout=60) as r:
                kod, j = r.status, json_coz(r.read())
        except urllib.error.HTTPError as e:
            kod = e.code
            if e.code == 429 and deneme < 3:
                time.sleep(5 * (deneme + 1))
                continue
            j = {"_hata": e.code, "_metin": kisa(e.read().decode(errors="replace"), 300)}
        except (urllib.error.URLError, TimeoutError, ConnectionError, HTTPException) as e:
            if deneme < 3:
                time.sleep(10)
                continue
            kod, j = 0, {"_hata": 0, "_metin": type(e).__name__}
        break
    ISTEKLER.append({"tedarikci": "printify", "yontem": "GET", "yol": yol + q, "http": kod,
                     "zaman": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return j


# ----------------------------------------------------------------------------------------------------------- aday
def liste(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def sozluk(x):
    return x if isinstance(x, dict) else {}


def eslesme(metinler):
    """-> (kelime eslesti mi, pet/dog var mi). Yalniz verilen alan metinleri (aciklama verilmez)."""
    m = " | ".join(str(x) for x in metinler if x)
    return bool(KELIME.search(m)), bool(PET.search(m))


def jy(ham, ad):
    p = ham / ad
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def yanit(w):
    y = (w or {}).get("yanit")
    return y if isinstance(y, dict) else {}


def http(w):
    return (w or {}).get("http")


def pf_adaylar(ham):
    v1 = liste(yanit(jy(ham, "v1_products.json")).get("result"))
    v2 = [p for s in (jy(ham, "v2_catalog_products.json") or {}).get("sayfalar") or [] for p in liste(yanit(s).get("data"))]
    a = {}
    for kaynak, urunler in (("v1", v1), ("v2", v2)):
        for p in urunler:
            if p.get("id") is None:
                continue
            for al in PF_ALAN[kaynak]:
                k, pet = eslesme([p.get(al)])
                if k:
                    x = a.setdefault(str(p.get("id")), {"neden": [], "ad": p.get("title") or p.get("name") or YOK, "pet_dog": False})
                    if f"{kaynak}.{al}" not in x["neden"]:
                        x["neden"].append(f"{kaynak}.{al}")
                    x["pet_dog"] = x["pet_dog"] or eslesme([p.get(f) for f in PF_ALAN[kaynak]])[1]
    for z in ZORUNLU:
        a.setdefault(str(z), {"neden": [], "ad": YOK, "pet_dog": False})["neden"].append("gorev_listesi")
    return a


def py_adaylar(bps):
    a = {}
    for b in liste(bps):
        k, pet = eslesme([b.get("title")])
        if k and b.get("id") is not None:
            a[str(b["id"])] = {"neden": ["title"], "ad": b.get("title"), "pet_dog": pet}
    return a


def boy_deger(v, sira):
    """v2 boy bilgisi: 'AxB' olcusunde alan, tek sayida sayi, harf boyunda Printful sizes sirasi ya da BOY_SIRA. Yoksa None."""
    s = str(v.get("size") or "").strip()
    n = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if len(n) >= 2:
        return n[0] * n[1]
    if s.upper() in BOY_SIRA:                     # harf boyu ONCE sabit sira (Printful sizes sirasi L,M,S,XL gelebilir)
        return float(BOY_SIRA.index(s.upper()))
    if len(n) == 1:
        return n[0]
    if s in sira:                                 # BOY_SIRA'da olmayan boy: Printful sizes sirasi
        return 100.0 + sira.index(s)
    return None


def kucuk_buyuk(vs, sira):
    """-> [(varyant, etiket)] en kucuk + en buyuk (esitlikte kucuk id). Boy bilgisi yoksa yalniz en kucuk id."""
    vs = [v for v in liste(vs) if isinstance(v.get("id"), int)]
    if not vs:
        return []
    olc = [(boy_deger(v, sira), v["id"], v) for v in vs]
    bil = [x for x in olc if x[0] is not None]
    if not bil:
        return [(min(vs, key=lambda v: v["id"]), "boy bilgisi yok: en kucuk id")]
    kucuk = min(bil, key=lambda x: (x[0], x[1]))[2]
    buyuk = min(bil, key=lambda x: (-x[0], x[1]))[2]
    return [(kucuk, "en kucuk")] if kucuk["id"] == buyuk["id"] else [(kucuk, "en kucuk"), (buyuk, "en buyuk")]


# ----------------------------------------------------------------------------------------------------------- oku
PF_DETAY = (("v1", "/products/{pid}"), ("v1_sizes", "/products/{pid}/sizes?unit=inches,cm"),
            ("printfiles", "/mockup-generator/printfiles/{pid}"), ("v2", "/v2/catalog-products/{pid}"),
            ("v2_prices_USD", "/v2/catalog-products/{pid}/prices?currency=USD&selling_region_name=worldwide"),
            ("v2_availability", "/v2/catalog-products/{pid}/availability?limit=100"),
            ("v2_sizes", "/v2/catalog-products/{pid}/sizes"))


def oku(ham):
    token = os.environ.get("PRINTFUL_TOKEN", "").strip()
    anahtar = os.environ.get("PRINTIFY_API_KEY", "").replace("\ufeff", "").strip()
    SIRLAR[:] = [x for x in (token, anahtar) if x] + [y for x in (token, anahtar) for y in x.split() if len(y) >= 8]
    if not token:
        raise SystemExit("DUR: PRINTFUL_TOKEN yok")
    if not BICIM.match(token):
        raise SystemExit("DUR: PRINTFUL_TOKEN bicimi gecersiz (bosluk / satir sonu)")
    if anahtar and not BICIM.match(anahtar):
        os.environ["PRINTIFY_DURUM"] = "Printify anahtari bicimi gecersiz (bosluk / satir sonu); Printify atlandi"
        anahtar = ""
    ham.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        return _oku(ham, token, anahtar, t0)
    finally:
        yaz(ham / "_istekler.json", ISTEKLER)
        post = [x for x in ISTEKLER if x["yontem"] == "POST"]
        log(f"ISTEK toplam {len(ISTEKLER)} | printful {sum(x['tedarikci'] == 'printful' for x in ISTEKLER)} | printify "
            f"{sum(x['tedarikci'] == 'printify' for x in ISTEKLER)} | POST {len(post)} (yollar: {sorted({x['yol'] for x in post})}) "
            f"| sure {int(time.time() - t0)}s")


def _oku(ham, token, anahtar, t0):  # noqa: C901
    # 1) listeler (Printful v1 + v2, Printify blueprint listesi) -> aday kontrolu, ag ONCESI DUR
    k, j = istek("/products", token)
    yaz(ham / "v1_products.json", sar("GET", "/products", None, k, j))
    log(f"GET /products -> {k}")
    sayfalar, off = [], 0
    while off < 5000:
        yol = f"/v2/catalog-products?limit=100&offset={off}&selling_region_name=worldwide"
        k, j = istek(yol, token)
        sayfalar.append(sar("GET", yol, None, k, j))
        data = liste(sozluk(j).get("data"))
        if k != 200 or not data:
            break
        off += len(data)
        top = sozluk(sozluk(j).get("paging")).get("total")
        if top is None or off >= int(top):
            break
    yaz(ham / "v2_catalog_products.json", {"sayfalar": sayfalar})
    log(f"GET /v2/catalog-products: {len(sayfalar)} sayfa, {off} urun")
    pf = pf_adaylar(ham)
    yaz(ham / "_adaylar_printful.json", pf)
    log("ADAY printful " + json.dumps({i: f"{v['ad']} [{','.join(v['neden'])}]" for i, v in pf.items()}, ensure_ascii=False))

    py, bps, py_dur = {}, None, None
    if anahtar:
        bps = py_istek("GET", "/v1/catalog/blueprints.json", anahtar)
        yaz(ham / "py_blueprints.json", bps)
        py = py_adaylar(bps if isinstance(bps, list) else [])
        yaz(ham / "_adaylar_printify.json", py)
        yaz(ham / "_printify.json", {"durum": "okundu" if isinstance(bps, list) else f"liste okunamadi {sozluk(bps).get('_hata')}"})
        log("ADAY printify " + json.dumps({i: v["ad"] for i, v in py.items()}, ensure_ascii=False))
    else:
        neden = os.environ.get("PRINTIFY_DURUM") or PRINTIFY_YOK
        yaz(ham / "_printify.json", {"durum": "atlandi", "neden": neden})
        log(f"PRINTIFY atlandi: {neden}")
    if len(pf) > AZAMI_ADAY:
        yaz(ham / "_dur.json", {"neden": f"Printful aday sayisi {len(pf)} > {AZAMI_ADAY}"})
        raise SystemExit(f"DUR: Printful aday sayisi {len(pf)} > {AZAMI_ADAY}; ag adimlarina gecilmedi, liste ham/_adaylar_printful.json")
    if len(py) > AZAMI_ADAY:                      # Printify istege bagli: yalniz Printify durur, Printful surer, kosu sonunda FAIL
        py_dur = f"DUR: Printify aday sayisi {len(py)} > {AZAMI_ADAY}; Printify detay / kargo istegi yok, liste ham/_adaylar_printify.json"
        yaz(ham / "_printify.json", {"durum": "DUR", "neden": py_dur})
        log(py_dur)
        py = {}
    log(f"TAHMIN (detay oncesi) printful GET ~{len(pf) * len(PF_DETAY) + len(pf)} + kargo POST <= {len(pf) * 2 * len(ULKELER) * 2}"
        + (f" | printify GET ~{len(py) * 2} + saglayici basina ~8" if anahtar else ""))

    # 2) Printful detay
    for i, pid in enumerate(sorted(pf, key=int), 1):
        for ad, sab in PF_DETAY:
            yol = sab.format(pid=pid)
            k, j = istek(yol, token)
            if k == 400 and "selling region" in json.dumps(j).lower() and "selling_region_name" not in yol:
                yaz(ham / f"urun_{pid}_{ad}_bolgesiz.json", sar("GET", yol, None, k, j))
                yol += ("&" if "?" in yol else "?") + "selling_region_name=worldwide"
                k, j = istek(yol, token)
            yaz(ham / f"urun_{pid}_{ad}.json", sar("GET", yol, None, k, j))
            if k != 200:
                log(f"  {yol} -> HTTP {k} {kisa(json.dumps(j, ensure_ascii=False), 200)}")
        vs_say, off = [], 0
        while off < 1000:
            yol = f"/v2/catalog-products/{pid}/catalog-variants?limit=100&offset={off}"
            k, j = istek(yol, token)
            vs_say.append(sar("GET", yol, None, k, j))
            d = liste(sozluk(j).get("data"))
            if k != 200 or not d:
                break
            off += len(d)
            top = sozluk(sozluk(j).get("paging")).get("total")
            if top is None or off >= int(top):
                break
        yaz(ham / f"urun_{pid}_v2_variants.json", {"sayfalar": vs_say})
        log(f"[printful urun {i}/{len(pf)}] {pid} detay okundu | gecen {int(time.time() - t0)}s")

    # 3) Printful kargo plani: en kucuk + en buyuk varyant x ULKELER
    plan = []
    for pid in sorted(pf, key=int):
        vs, sira = pf_varyantlar(ham, pid)
        for v, etiket in kucuk_buyuk(vs, sira):
            for ulke in ULKELER:
                plan.append((pid, v["id"], etiket, ulke))
    log(f"TAHMIN kargo: {len(plan)} varyant x ulke x 2 (v1 + v2) = {len(plan) * 2} POST")
    yaz(ham / "_kargo_plani.json", [{"urun": a, "varyant": b, "etiket": c, "ulke": d} for a, b, c, d in plan])
    k1, k2, t1 = [], [], time.time()
    try:
        _kargo(plan, token, k1, k2, t1)
    finally:                                      # kesintide (istisna, iptal) o ana kadarki kargo yanitlari kaybolmaz
        yaz(ham / "kargo_v1.json", k1)
        yaz(ham / "kargo_v2.json", k2)
    _printify_detay(ham, py, anahtar, t0)
    kargo_ok = sum(1 for x in k1 + k2 if x.get("http") == 200)
    hata = []
    if http(jy(ham, "v1_products.json")) != 200:
        hata.append("v1 /products okunamadi")
    if not any(http(s) == 200 for s in (jy(ham, "v2_catalog_products.json") or {}).get("sayfalar") or []):
        hata.append("v2 katalog listesi okunamadi")
    if plan and kargo_ok == 0:
        hata.append(f"kargo: {len(k1) + len(k2)} sorgunun hicbiri 200 donmedi")
    if py_dur:
        hata.append(py_dur)
    log(f"KARGO basarili {kargo_ok}/{len(k1) + len(k2)}" + (f" | FAIL: {'; '.join(hata)}" if hata else ""))
    return 1 if hata else 0


def _kargo(plan, token, k1, k2, t1):
    for n, (pid, vid, etiket, ulke) in enumerate(plan, 1):
        g1 = {"recipient": {"country_code": ulke, **ADRES[ulke]}, "items": [{"variant_id": vid, "quantity": 1}], "currency": "USD"}
        k, j = istek("/shipping/rates", token, g1)
        k1.append({"urun": pid, "varyant": vid, "etiket": etiket, "ulke": ulke, **sar("POST", "/shipping/rates", g1, k, j)})
        g2 = {"recipient": {"country_code": ulke, **ADRES[ulke]},
              "order_items": [{"source": "catalog", "catalog_variant_id": vid, "quantity": 1}], "currency": "USD"}
        k_, j_ = istek("/v2/shipping-rates", token, g2)
        k2.append({"urun": pid, "varyant": vid, "etiket": etiket, "ulke": ulke, **sar("POST", "/v2/shipping-rates", g2, k_, j_)})
        if n % 10 == 0 or n == len(plan):
            g = time.time() - t1
            log(f"[kargo {n}/{len(plan)} %{100 * n // len(plan)}] gecen {int(g)}s kalan ~{int(g * (len(plan) - n) / n)}s "
                f"| son: {pid}/{vid}/{ulke} v1 {k} v2 {k_}")


def _printify_detay(ham, py, anahtar, t0):
    if anahtar and py:
        pp_bilgi = {}
        for i, bid in enumerate(sorted(py, key=int), 1):
            yaz(ham / f"py_bp_{bid}.json", py_istek("GET", f"/v1/catalog/blueprints/{bid}.json", anahtar))
            pps = py_istek("GET", f"/v1/catalog/blueprints/{bid}/print_providers.json", anahtar)
            yaz(ham / f"py_bp_{bid}_print_providers.json", pps)
            for pp in liste(pps):
                pid = pp.get("id")
                if not isinstance(pid, int):
                    continue
                if pid not in pp_bilgi:
                    pp_bilgi[pid] = py_istek("GET", f"/v1/catalog/print_providers/{pid}.json", anahtar)
                    yaz(ham / f"py_pp_{pid}.json", pp_bilgi[pid])
                yaz(ham / f"py_bp_{bid}_pp_{pid}_variants.json",
                    py_istek("GET", f"/v1/catalog/blueprints/{bid}/print_providers/{pid}/variants.json", anahtar,
                             {"show-out-of-stock": 1}))
                yaz(ham / f"py_bp_{bid}_pp_{pid}_shipping_v1.json",
                    py_istek("GET", f"/v1/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json", anahtar))
                v2 = py_istek("GET", f"/v2/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json", anahtar)
                yaz(ham / f"py_bp_{bid}_pp_{pid}_shipping_v2.json", v2)
                for d in liste(sozluk(v2).get("data")):
                    ad = sozluk(d.get("attributes")).get("name") or d.get("id")
                    yk = re.sub(r"[^a-z_]", "", str(ad or "").lower())
                    if yk:
                        yaz(ham / f"py_bp_{bid}_pp_{pid}_shipping_v2_{yk}.json",
                            py_istek("GET", f"/v2/catalog/blueprints/{bid}/print_providers/{pid}/shipping/{yk}.json", anahtar))
            log(f"[printify blueprint {i}/{len(py)}] {bid} okundu | gecen {int(time.time() - t0)}s")


def pf_varyantlar(ham, pid):
    """-> (v2 varyantlari [yoksa v1], Printful sizes sirasi)."""
    v2 = [v for s in (jy(ham, f"urun_{pid}_v2_variants.json") or {}).get("sayfalar") or [] for v in liste(yanit(s).get("data"))]
    p2 = sozluk(yanit(jy(ham, f"urun_{pid}_v2.json")).get("data"))
    sira = [str(x) for x in (p2.get("sizes") or []) if isinstance(x, (str, int, float))]
    if v2:
        return v2, sira
    return liste(sozluk(yanit(jy(ham, f"urun_{pid}_v1.json")).get("result")).get("variants")), sira


# ----------------------------------------------------------------------------------------------------------- rapor
def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def en_ucuz(secenekler):
    s = [x for x in liste(secenekler) if fl(x.get("rate")) is not None]
    return min(s, key=lambda x: fl(x["rate"])) if s else None


def hata_mesaj(w):
    y = yanit(w)
    m = sozluk(y.get("error")).get("message") or (y.get("result") if isinstance(y.get("result"), str) else None)
    return kisa(m or y, 160)


def aralik(deg):
    s = sorted({fl(x) for x in deg if fl(x) is not None})
    if not s:
        return YOK
    return f"{s[0]:g}" if len(s) == 1 else f"{s[0]:g}-{s[-1]:g}"


def pf_rapor(ham, satir, kargo, ozet):  # noqa: C901
    aday = jy(ham, "_adaylar_printful.json") or {}
    K1 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in jy(ham, "kargo_v1.json") or []}
    K2 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in jy(ham, "kargo_v2.json") or []}
    for pid in sorted(aday, key=int):
        v1 = jy(ham, f"urun_{pid}_v1.json")
        r1 = sozluk(yanit(v1).get("result"))
        p1, vs1 = sozluk(r1.get("product")), {v.get("id"): v for v in liste(r1.get("variants"))}
        p2 = sozluk(yanit(jy(ham, f"urun_{pid}_v2.json")).get("data"))
        vs, sira = pf_varyantlar(ham, pid)
        pf = sozluk(yanit(jy(ham, f"urun_{pid}_printfiles.json")).get("result"))
        pf_id = {x.get("printfile_id"): x for x in liste(pf.get("printfiles"))}
        pf_var = {x.get("variant_id"): sozluk(x.get("placements")) for x in liste(pf.get("variant_printfiles"))}
        fiyat2 = {}
        for v in liste(sozluk(yanit(jy(ham, f"urun_{pid}_v2_prices_USD.json")).get("data")).get("variants")):
            fiyat2[v.get("id")] = "; ".join(f"{t.get('technique_key')}:{t.get('price')}" for t in liste(v.get("techniques")))
        uyg = {}
        for v in liste(yanit(jy(ham, f"urun_{pid}_v2_availability.json")).get("data")):
            for t in liste(v.get("techniques")):
                for sr in liste(t.get("selling_regions")):
                    uyg.setdefault(v.get("catalog_variant_id"), []).append(f"{sr.get('name')}:{sr.get('availability')}")
        yer = [f"{p.get('placement')}:{p.get('technique')}" for p in liste(p2.get("placements")) if p.get("placement") != "mockup"]
        tek = [str(t.get("display_name") or t.get("key")) for t in liste(p2.get("techniques")) or liste(p1.get("techniques"))] + \
              [str(p.get("technique")) for p in liste(p2.get("placements")) if p.get("technique")]
        teknik = sorted({t.lower(): t for t in sorted(tek, key=str.lower, reverse=True)}.values(), key=str.lower)  # buyuk/kucuk tekrar yok
        ad = p1.get("title") or p2.get("name") or aday[pid].get("ad") or YOK
        tur = p1.get("type_name") or p2.get("type") or p1.get("type") or YOK
        cikis_urun = {}
        for v in vs:
            vid = v.get("id")
            v1v = vs1.get(vid) or {}
            yerl = pf_var.get(vid) or {}
            pfx = [(y, pf_id.get(i) or {}) for y, i in yerl.items()]
            dep = set()
            for ulke in ULKELER:
                x2 = K2.get((pid, vid, ulke))
                for o in liste(yanit(x2).get("data")):
                    for sh in liste(o.get("shipments")):
                        if sh.get("departure_country"):
                            dep.add(sh["departure_country"])
                            cikis_urun.setdefault(sh["departure_country"], set()).add(ulke)
            satir.append({
                "tedarikci": "Printful", "urun_id": pid, "urun_adi": ad, "tur": tur, "eslesme": ",".join(aday[pid]["neden"]),
                "pet_dog": "evet" if aday[pid].get("pet_dog") else "hayir", "saglayici": "Printful",
                "varyant_id": vid, "varyant_adi": v.get("name") or YOK, "boy": v.get("size") or YOK, "renk": v.get("color") or YOK,
                "fiyat_usd_v1": v1v.get("price") if v1v.get("price") is not None else YOK,
                "fiyat_usd_v2_worldwide": fiyat2.get(vid) or YOK,
                "baski_yerlesimleri": "; ".join(yer) or "; ".join(sozluk(pf.get("available_placements"))) or YOK,
                "baski_dosyasi_px": "; ".join(f"{y}={x.get('width')}x{x.get('height')}" for y, x in pfx) or YOK,
                "baski_dosyasi_dpi": "; ".join(f"{y}={x.get('dpi')}" for y, x in pfx) or YOK,
                "baski_alani_inch_v2": "; ".join(f"{d.get('placement')}={d.get('width')}x{d.get('height')}"
                                                for d in liste(v.get("placement_dimensions"))) or YOK,
                "teknik": "; ".join(teknik) or YOK,
                "uretim_yeri_v2_cikis": ", ".join(sorted(dep)) or ("kargo sorgulanmadi" if not any(
                    (pid, vid, u) in K2 for u in ULKELER) else YOK),
                "bolge_durum_v1": "; ".join(f"{a.get('region')}:{a.get('status')}" for a in liste(v1v.get("availability_status"))) or YOK,
                "uygunluk_v2": "; ".join(uyg.get(vid) or []) or YOK,
                "stok_v1": v1v.get("in_stock") if v1v.get("in_stock") is not None else YOK,
            })
        kac = [k for k in K1 if k[0] == pid]
        for (u_, vid, ulke) in sorted(kac, key=lambda k: (k[1], ULKELER.index(k[2]))):
            x1, x2 = K1[(u_, vid, ulke)], K2.get((u_, vid, ulke))
            e = en_ucuz(yanit(x1).get("result")) if http(x1) == 200 else None
            o2 = en_ucuz(yanit(x2).get("data")) if http(x2) == 200 else None
            kargo.append({
                "tedarikci": "Printful", "urun_id": pid, "urun_adi": ad, "saglayici": "Printful", "varyant_id": vid,
                "varyant_etiket": x1.get("etiket"), "ulke": ulke, "http_v1": http(x1), "ucret_usd": e.get("rate") if e else YOK,
                "yontem": (e.get("id") if e else YOK), "min_gun": e.get("minDeliveryDays") if e else YOK,
                "max_gun": e.get("maxDeliveryDays") if e else YOK, "http_v2": http(x2),
                "ucret_v2": o2.get("rate") if o2 else YOK,
                "cikis_ulkesi_v2": ", ".join(sorted({sh.get("departure_country") for sh in liste((o2 or {}).get("shipments"))
                                                     if sh.get("departure_country")})) or YOK,
                "ek_urun_usd": YOK, "hata": "" if e else hata_mesaj(x1)})
        ks = [k for k in kargo if k["tedarikci"] == "Printful" and k["urun_id"] == pid]
        ozet.append({"tedarikci": "Printful", "id": pid, "ad": ad, "tur": tur, "varyant": len(vs),
                     "boy": aralik_boy(vs, sira),
                     "fiyat": aralik([s["fiyat_usd_v1"] for s in satir if s["tedarikci"] == "Printful" and s["urun_id"] == pid]
                                     + [p.split(":")[-1] for s in satir if s["tedarikci"] == "Printful" and s["urun_id"] == pid
                                        for p in s["fiyat_usd_v2_worldwide"].split("; ")]),
                     "baski": "; ".join(sorted({s["baski_dosyasi_px"] + " @" + s["baski_dosyasi_dpi"] for s in satir
                                                if s["tedarikci"] == "Printful" and s["urun_id"] == pid})) or YOK,
                     "teknik": "; ".join(teknik) or YOK,
                     "uretim": "; ".join(f"{d} (hedef {','.join(sorted(h, key=ULKELER.index))})" for d, h in sorted(cikis_urun.items()))
                     or ("kargo sorgulanmadi" if not ks else YOK),
                     "kargo": kargo_ozet(ks), "http": f"v1 {http(v1)} v2 {http(jy(ham, f'urun_{pid}_v2.json'))}",
                     "eslesme": ",".join(aday[pid]["neden"])})


def aralik_boy(vs, sira=()):
    """Boylar boy_deger sirasinda (olculemeyen sonda): 'ilk .. son (N boy)'."""
    b = {}
    for v in liste(vs):
        s = str(v.get("size") or "").strip()
        if s:
            b.setdefault(s, boy_deger(v, list(sira)))
    s = sorted(b, key=lambda x: (b[x] is None, b[x] if b[x] is not None else 0, x))
    return (s[0] if len(s) == 1 else f"{s[0]} .. {s[-1]} ({len(s)} boy)") if s else YOK


def kargo_ozet(ks):
    if not ks:
        return "sorgulanmadi"
    h = []
    for ulke in ULKELER:
        u = [k for k in ks if k["ulke"] == ulke]
        if not u:
            continue
        ok = [k["ucret_usd"] for k in u if fl(k["ucret_usd"]) is not None]
        h.append(f"{ulke} {aralik(ok)}" if ok else f"{ulke} yok")
    return ", ".join(h)


def py_rapor(ham, satir, kargo, ozet):
    aday = jy(ham, "_adaylar_printify.json") or {}
    for bid in sorted(aday, key=int):
        bp = sozluk(jy(ham, f"py_bp_{bid}.json"))
        ad = bp.get("title") or aday[bid].get("ad") or YOK
        pps = liste(jy(ham, f"py_bp_{bid}_print_providers.json"))
        boylar, yerler, saglayici = [], set(), []
        for pp in pps:
            pid = pp.get("id")
            info = sozluk(jy(ham, f"py_pp_{pid}.json"))
            konum = sozluk(info.get("location"))
            yer = ", ".join(str(konum.get(k)) for k in ("country", "region", "city") if konum.get(k)) or YOK
            saglayici.append(f"{pid} {pp.get('title')} ({yer})")
            var = sozluk(jy(ham, f"py_bp_{bid}_pp_{pid}_variants.json"))
            for v in liste(var.get("variants")):
                opt = sozluk(v.get("options"))
                boylar.append(opt.get("size"))
                ph = "; ".join(f"{p.get('position')}={p.get('width')}x{p.get('height')}" for p in liste(v.get("placeholders"))) or YOK
                yerler.add(ph)
                satir.append({"tedarikci": "Printify", "urun_id": bid, "urun_adi": ad, "tur": bp.get("model") or YOK,
                              "eslesme": "title", "pet_dog": "evet" if aday[bid].get("pet_dog") else "hayir",
                              "saglayici": f"{pid} {pp.get('title')}", "varyant_id": v.get("id"),
                              "varyant_adi": v.get("title") or YOK, "boy": opt.get("size") or YOK, "renk": opt.get("color") or YOK,
                              "fiyat_usd_v1": YOK, "fiyat_usd_v2_worldwide": YOK,
                              "baski_yerlesimleri": "; ".join(str(p.get("position")) for p in liste(v.get("placeholders"))) or YOK,
                              "baski_dosyasi_px": ph, "baski_dosyasi_dpi": YOK, "baski_alani_inch_v2": YOK, "teknik": YOK,
                              "uretim_yeri_v2_cikis": yer, "bolge_durum_v1": YOK, "uygunluk_v2": YOK,
                              "stok_v1": v.get("is_available") if v.get("is_available") is not None else YOK})
            s1 = sozluk(jy(ham, f"py_bp_{bid}_pp_{pid}_shipping_v1.json"))
            prof = liste(s1.get("profiles"))
            secim = kucuk_buyuk([{"id": v.get("id"), "size": sozluk(v.get("options")).get("size")} for v in liste(var.get("variants"))], [])
            for v, etiket in secim:                  # Printful ile ayni kural: en kucuk + en buyuk varyant, profil variant_ids uzerinden
                vp = [p for p in prof if v["id"] in (p.get("variant_ids") or [])] or prof
                for ulke in ULKELER:
                    pr = [p for p in vp if ulke in (p.get("countries") or [])] or \
                         [p for p in vp if "REST_OF_THE_WORLD" in (p.get("countries") or [])]
                    ilk = sozluk(pr[0].get("first_item")).get("cost") if pr else None
                    ek = sozluk(pr[0].get("additional_items")).get("cost") if pr else None
                    kargo.append({"tedarikci": "Printify", "urun_id": bid, "urun_adi": ad, "saglayici": f"{pid} {pp.get('title')}",
                                  "varyant_id": v["id"], "varyant_etiket": etiket, "ulke": ulke,
                                  "http_v1": s1.get("_hata", 200 if prof else YOK),
                                  "ucret_usd": ilk / 100 if isinstance(ilk, int) else YOK, "yontem": "v1 profil",
                                  "min_gun": YOK, "max_gun": YOK, "http_v2": YOK, "ucret_v2": YOK, "cikis_ulkesi_v2": yer,
                                  "ek_urun_usd": ek / 100 if isinstance(ek, int) else YOK,
                                  "hata": "" if pr else "profilde ulke yok"})
        ks = [k for k in kargo if k["tedarikci"] == "Printify" and k["urun_id"] == bid]
        ozet.append({"tedarikci": "Printify", "id": bid, "ad": ad, "tur": bp.get("model") or YOK, "varyant":
                     sum(1 for s in satir if s["tedarikci"] == "Printify" and s["urun_id"] == bid),
                     "boy": aralik_boy([{"size": b} for b in boylar]),
                     "fiyat": f"{YOK} (Printify katalog API'si maliyet vermez)", "baski": "; ".join(sorted(yerler)) or YOK,
                     "teknik": YOK, "uretim": "; ".join(saglayici) or YOK,
                     "kargo": kargo_ozet(ks), "http": "GET", "eslesme": "title"})


SATIR_ALAN = ["tedarikci", "urun_id", "urun_adi", "tur", "eslesme", "pet_dog", "saglayici", "varyant_id", "varyant_adi", "boy",
              "renk", "fiyat_usd_v1", "fiyat_usd_v2_worldwide", "baski_yerlesimleri", "baski_dosyasi_px", "baski_dosyasi_dpi",
              "baski_alani_inch_v2", "teknik", "uretim_yeri_v2_cikis", "bolge_durum_v1", "uygunluk_v2", "stok_v1"]
KARGO_ALAN = ["tedarikci", "urun_id", "urun_adi", "saglayici", "varyant_id", "varyant_etiket", "ulke", "http_v1", "ucret_usd",
              "yontem", "min_gun", "max_gun", "http_v2", "ucret_v2", "cikis_ulkesi_v2", "ek_urun_usd", "hata"]


def rapor(cikti):
    """AG YOK: yalniz <cikti>/ham'dan okur."""
    ham = cikti / "ham"
    satir, kargo, ozet = [], [], []
    pf_rapor(ham, satir, kargo, ozet)
    py_rapor(ham, satir, kargo, ozet)
    for ad, alan, veri in (("PET_KATALOG.csv", SATIR_ALAN, satir), ("PET_KARGO.csv", KARGO_ALAN, kargo)):
        with open(cikti / ad, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=alan)
            w.writeheader()
            w.writerows(veri)
    ist = jy(ham, "_istekler.json") or []
    pyd = sozluk(jy(ham, "_printify.json"))
    dur = sozluk(jy(ham, "_dur.json"))
    post = sorted({x["yol"] for x in ist if x.get("yontem") == "POST"})
    L = ["# Pet urun adaylari: battaniye, yastik, bandana (salt okuma)", "",
         f"Kaynak: Printful API v1 + v2" + (", Printify katalog API" if pyd.get("durum") == "okundu" else "") +
         f"; ham yanitlar `ham/`. Istek {len(ist)} (GET {sum(1 for x in ist if x.get('yontem') == 'GET')}, POST "
         f"{sum(1 for x in ist if x.get('yontem') == 'POST')}: {', '.join(post) or 'yok'}). Son istek "
         f"{max((x.get('zaman', '') for x in ist), default=YOK)}.",
         f"Aday sayisi: Printful {sum(1 for o in ozet if o['tedarikci'] == 'Printful')} | Printify "
         + (str(sum(1 for o in ozet if o['tedarikci'] == 'Printify')) if pyd.get("durum") == "okundu"
            else (pyd.get("neden") or pyd.get("durum") or YOK)),
         "Kural: baslik/tur/model/ad alaninda \\bblanket\\b|\\bpillow\\b|\\bcushion\\b|\\bbandana\\b (aciklama degil) + zorunlu 902. "
         f"Kargo: Printful en kucuk + en buyuk varyant x {' '.join(ULKELER)}, 1 adet, USD (v1 en ucuz yontem); Printify v1 profil ilk urun.",
         "Fiyat: Printful v1 `price` ve v2 worldwide teknik fiyati (USD, kargo haric). Printify: API vermedi.", ""]
    if dur:
        L += [f"**DUR**: {dur.get('neden')}", ""]
    for o in ozet:
        L += [f"- **{o['tedarikci']} {o['id']} {o['ad']}** ({o['tur']}; eslesme {o['eslesme']}; {o['http']}) | varyant {o['varyant']}, "
              f"boy {o['boy']} | fiyat USD {o['fiyat']}",
              f"  baski dosyasi: {o['baski']} | teknik: {o['teknik']} | uretim yeri: {o['uretim']}",
              f"  kargo USD: {o['kargo']}"]
    (cikti / "PET_KATALOG.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"RAPOR aday {len(ozet)} | varyant satiri {len(satir)} | kargo satiri {len(kargo)}")
    return 0 if ozet and not dur else 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("oku", "rapor"):
        sys.exit(__doc__)
    sys.exit(oku(Path(sys.argv[2])) if sys.argv[1] == "oku" else rapor(Path(sys.argv[2])))
