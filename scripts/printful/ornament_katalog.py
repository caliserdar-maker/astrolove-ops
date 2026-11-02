#!/usr/bin/env python3
"""Printful ornament katalog SALT OKUMA (Serdar 2 Kas 2026).
Yalniz GET + kargo ucreti sorgusu (POST /shipping/rates, POST /v2/shipping-rates). Siparis, urun, sablon, mockup gorevi
OLUSTURULMAZ: izinli POST yollari POST_IZIN'de, disindaki her POST betigi durdurur. Etsy'ye dokunmaz.

Kullanim:
  ornament_katalog.py oku <ham_klasor>      env PRINTFUL_TOKEN. Ham API yanitlari (token yazilmaz; istek basliklari kaydedilmez).
  ornament_katalog.py rapor <cikti_klasor>  API yok; <cikti>/ham'dan okur. PRINTFUL_ORNAMENT.csv, PRINTFUL_ORNAMENT_KARGO.csv,
                                            PRINTFUL_ORNAMENT.md yazar. API'nin vermedigi alan: "API vermedi".
Aday urun: v1 /products ve v2 /v2/catalog-products listesinde title/type_name/model/name/description alaninda "ornament"
gecen, adi "ornament" gecen kategorideki ve gorevde adi gecen (881, 900, 634) urunler. Kargo: aciklama disi eslesen her
urunun her varyanti x ULKELER, 1 adet, USD (v1: secenek + ucret + gun; v2: cikis ulkesi / gumruk)."""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.printful.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops"
POST_IZIN = {"/shipping/rates", "/v2/shipping-rates"}
ULKELER = os.environ.get("ULKELER", "US CA GB DE FR IT ES NL AU").split()
ZORUNLU = [881, 900, 634]
ANAHTAR = re.compile(r"ornament", re.I)
ADRES = {"US": {"state_code": "NY", "city": "New York", "zip": "10001"},
         "CA": {"state_code": "ON", "city": "Toronto", "zip": "M5V 2T6"},
         "GB": {"city": "London", "zip": "SW1A 1AA"}, "DE": {"city": "Berlin", "zip": "10115"},
         "FR": {"city": "Paris", "zip": "75001"}, "IT": {"city": "Rome", "zip": "00184"},
         "ES": {"city": "Madrid", "zip": "28001"}, "NL": {"city": "Amsterdam", "zip": "1012 JS"},
         "AU": {"state_code": "NSW", "city": "Sydney", "zip": "2000"}}
YOK = "API vermedi"
ISTEKLER = []


# ----------------------------------------------------------------------------------------------------------- oku
def istek(yol, token, veri=None):
    yontem = "POST" if veri is not None else "GET"
    if yontem == "POST" and yol.split("?")[0] not in POST_IZIN:
        raise SystemExit(f"DUR: izinsiz POST {yol}")
    kod, j = 0, {}
    for deneme in range(6):
        req = urllib.request.Request(API + yol, data=json.dumps(veri).encode() if veri is not None else None,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                                              "User-Agent": UA, "Accept": "application/json"}, method=yontem)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                kod, j = r.status, json.load(r)
        except urllib.error.HTTPError as e:
            govde = e.read().decode(errors="replace")[:5000]
            if e.code in (429, 500, 502, 503, 504) and deneme < 5:
                try:
                    bekle = int(e.headers.get("Retry-After") or 0)
                except ValueError:
                    bekle = 0
                bekle = min(max(bekle, 15 * (deneme + 1)), 90)
                print(f"  {yontem} {yol} HTTP {e.code}, {bekle}s bekleniyor", flush=True)
                time.sleep(bekle)
                continue
            kod = e.code
            try:
                j = json.loads(govde)
            except ValueError:
                j = {"ham": govde}
        except (urllib.error.URLError, TimeoutError) as e:
            if deneme < 5:
                time.sleep(10)
                continue
            kod, j = 0, {"hata": type(e).__name__}
        break
    ISTEKLER.append({"yontem": yontem, "yol": yol, "http": kod, "zaman": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    time.sleep(0.35)
    return kod, j


def sar(yontem, yol, govde, kod, j):
    return {"istek": {"yontem": yontem, "yol": yol, "govde": govde}, "http": kod, "yanit": j}


def yaz(p, veri):
    p.write_text(json.dumps(veri, indent=1, ensure_ascii=False), encoding="utf-8")


def oku(ham):
    token = os.environ["PRINTFUL_TOKEN"].strip()
    ham.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    k, v1list = istek("/products", token)
    yaz(ham / "v1_products.json", sar("GET", "/products", None, k, v1list))
    print(f"GET /products -> {k}", flush=True)
    k, kat = istek("/categories", token)
    yaz(ham / "v1_categories.json", sar("GET", "/categories", None, k, kat))
    print(f"GET /categories -> {k}", flush=True)
    sayfalar, off = [], 0
    while off < 5000:
        yol = f"/v2/catalog-products?limit=100&offset={off}&selling_region_name=worldwide"
        k, j = istek(yol, token)
        sayfalar.append(sar("GET", yol, None, k, j))
        data = j.get("data") if isinstance(j, dict) else None
        data = data if isinstance(data, list) else []
        if k != 200 or not data:
            break
        off += len(data)
        top = (j.get("paging") or {}).get("total") if isinstance(j.get("paging"), dict) else None
        if top is None or off >= int(top):
            break
    yaz(ham / "v2_catalog_products.json", {"sayfalar": sayfalar})
    print(f"GET /v2/catalog-products: {len(sayfalar)} sayfa, {off} urun", flush=True)

    try:
        aday = adaylar(ham)
    except Exception as e:  # ayristirma hatasi ham toplamayi durdurmaz
        print(f"UYARI aday ayristirma hatasi {type(e).__name__}: {e}; yalniz gorev listesi", flush=True)
        aday = {str(z): {"neden": ["gorev_listesi"], "kargo": True} for z in ZORUNLU}
    yaz(ham / "_adaylar.json", aday)
    print("ADAY " + json.dumps({k_: v["neden"] for k_, v in aday.items()}, ensure_ascii=False), flush=True)

    for i, pid in enumerate(sorted(aday, key=int), 1):
        for ad, yol in (("v1", f"/products/{pid}"), ("v1_sizes", f"/products/{pid}/sizes?unit=inches,cm"),
                        ("printfiles", f"/mockup-generator/printfiles/{pid}"), ("v2", f"/v2/catalog-products/{pid}"),
                        ("v2_variants", f"/v2/catalog-products/{pid}/catalog-variants?limit=100"),
                        ("v2_prices_USD", f"/v2/catalog-products/{pid}/prices?currency=USD&selling_region_name=worldwide"),
                        ("v2_prices_EUR", f"/v2/catalog-products/{pid}/prices?currency=EUR&selling_region_name=worldwide"),
                        ("v2_prices_EUR_europe", f"/v2/catalog-products/{pid}/prices?currency=EUR&selling_region_name=europe"),
                        ("v2_prices_USD_north_america",
                         f"/v2/catalog-products/{pid}/prices?currency=USD&selling_region_name=north_america"),
                        ("v2_availability", f"/v2/catalog-products/{pid}/availability?limit=100"),
                        ("v2_sizes", f"/v2/catalog-products/{pid}/sizes"),
                        ("v2_mockup_templates", f"/v2/catalog-products/{pid}/mockup-templates?limit=100")):
            k, j = istek(yol, token)
            if k == 400 and "selling region" in json.dumps(j).lower() and "selling_region_name" not in yol:
                yaz(ham / f"urun_{pid}_{ad}_bolgesiz.json", sar("GET", yol, None, k, j))
                yol += ("&" if "?" in yol else "?") + "selling_region_name=worldwide"
                k, j = istek(yol, token)
            yaz(ham / f"urun_{pid}_{ad}.json", sar("GET", yol, None, k, j))
            if k != 200:
                print(f"  {yol} -> HTTP {k} {json.dumps(j, ensure_ascii=False)[:200]}", flush=True)
        print(f"[urun {i}/{len(aday)}] {pid} detay okundu | gecen {int(time.time() - t0)}s", flush=True)

    # kargo plani: aciklama-disi eslesen urunlerin tum varyantlari
    plan = []
    for pid in sorted(aday, key=int):
        if not aday[pid]["kargo"]:
            continue
        v1 = json.loads((ham / f"urun_{pid}_v1.json").read_text(encoding="utf-8"))
        r1 = (v1.get("yanit") or {}).get("result")
        for v in (r1.get("variants") or []) if isinstance(r1, dict) else []:
            if isinstance(v, dict) and v.get("id") is not None:
                for ulke in ULKELER:
                    plan.append((pid, v.get("id"), ulke))
    print(f"KARGO plani: {len(plan)} varyant x ulke (x2: v1 + v2)", flush=True)
    k1, k2, t1 = [], [], time.time()
    for n, (pid, vid, ulke) in enumerate(plan, 1):
        g1 = {"recipient": {"country_code": ulke, **ADRES.get(ulke, {})},
              "items": [{"variant_id": vid, "quantity": 1}], "currency": "USD"}
        k, j = istek("/shipping/rates", token, g1)
        k1.append({"urun": pid, "varyant": vid, "ulke": ulke, **sar("POST", "/shipping/rates", g1, k, j)})
        g2 = {"recipient": {"country_code": ulke, **ADRES.get(ulke, {})},
              "order_items": [{"source": "catalog", "catalog_variant_id": vid, "quantity": 1}], "currency": "USD"}
        k_, j_ = istek("/v2/shipping-rates", token, g2)
        k2.append({"urun": pid, "varyant": vid, "ulke": ulke, **sar("POST", "/v2/shipping-rates", g2, k_, j_)})
        if n % 9 == 0 or n == len(plan):
            g = time.time() - t1
            print(f"[kargo {n}/{len(plan)} %{100 * n // len(plan)}] gecen {int(g)}s kalan ~{int(g * (len(plan) - n) / n)}s "
                  f"| son: {pid}/{vid}/{ulke} v1 {k} v2 {k_}", flush=True)
    yaz(ham / "kargo_v1.json", k1)
    yaz(ham / "kargo_v2.json", k2)
    yaz(ham / "_istekler.json", ISTEKLER)
    post = [x for x in ISTEKLER if x["yontem"] == "POST"]
    print(f"ISTEK toplam {len(ISTEKLER)} | GET {len(ISTEKLER) - len(post)} | POST {len(post)} "
          f"(yollar: {sorted({x['yol'] for x in post})}) | sure {int(time.time() - t0)}s", flush=True)
    return 0 if (ham / "v1_products.json").exists() else 1


def liste(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def sozluk(x):
    return x if isinstance(x, dict) else {}


def adaylar(ham):
    def oku_j(ad):
        p = ham / ad
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    v1 = liste((oku_j("v1_products.json").get("yanit") or {}).get("result"))
    kat = (oku_j("v1_categories.json").get("yanit") or {}).get("result")
    kat = liste(kat.get("categories") if isinstance(kat, dict) else None)
    katid = {c.get("id") for c in kat if ANAHTAR.search(str(c.get("title") or ""))}
    v2 = [p for s in oku_j("v2_catalog_products.json").get("sayfalar") or [] for p in liste((s.get("yanit") or {}).get("data"))]
    a = {}

    def ekle(pid, neden):
        a.setdefault(str(pid), {"neden": [], "kargo": False})
        if neden not in a[str(pid)]["neden"]:
            a[str(pid)]["neden"].append(neden)
        if not neden.endswith("description"):
            a[str(pid)]["kargo"] = True
    for kaynak, urun_liste, alanlar in (("v1", v1, ("title", "type_name", "model", "type", "description")),
                                        ("v2", v2, ("name", "type", "model", "description"))):
        for p in urun_liste:
            for al in alanlar:
                if ANAHTAR.search(str(p.get(al) or "")):
                    ekle(p.get("id"), f"{kaynak}.{al}")
            if p.get("main_category_id") in katid:
                ekle(p.get("id"), f"{kaynak}.kategori")
    for z in ZORUNLU:
        ekle(z, "gorev_listesi")
    return a


# --------------------------------------------------------------------------------------------------------- rapor
def jy(ham, ad):
    p = ham / ad
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def yanit(w):
    y = (w or {}).get("yanit")
    return y if isinstance(y, dict) else {}


def http(w):
    return (w or {}).get("http")


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def anahtar_bul(d, kelime, yol=""):
    b = {}
    if isinstance(d, dict):
        for k, v in d.items():
            y = f"{yol}.{k}" if yol else k
            if kelime in k.lower():
                b[y] = v
            b.update(anahtar_bul(v, kelime, y))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            b.update(anahtar_bul(v, kelime, f"{yol}[{i}]"))
    return b


def en_ucuz(secenekler):
    s = [x for x in liste(secenekler) if fl(x.get("rate")) is not None]
    return min(s, key=lambda x: fl(x["rate"])) if s else None


def kisa_hata(m):
    if "united states only" in m.lower():
        return "ships to United States only"
    return m[:80]


def hata_mesaj(w):
    y = yanit(w)
    m = sozluk(y.get("error")).get("message") or (y.get("data") if isinstance(y.get("data"), str) else None) \
        or (y.get("result") if isinstance(y.get("result"), str) else None)
    return str(m or y)[:160]


def aciklama_satir(metin, desen):
    parca = [s.strip(" •-*\t") for s in re.split(r"[\n\r]+|•", metin or "") if s.strip(" •-*\t")]
    return [s for s in parca if re.search(desen, s, re.I)]


OLCU = r"″|\d\s*(?:cm|mm)\b|diameter|size"
MALZEME = r"^material|100%|alumin|acrylic|hinoki|wood\b|glass\b|ceramic\b|base\b"
PAKET = r"ribbon|string|packag|gift|hole|magnetic|bundle|pack"
YUZ = r"sided|side print|2-side"
KALINLIK = r"thickness"
MENSE = r"sourced from"


def olcu_satir(ac, boyut):
    satir = [s for s in aciklama_satir(ac, OLCU) if re.search(r"″|cm|mm", s) and not re.search(KALINLIK, s, re.I)]
    kelime = re.split(r"[\s+/(]+", str(boyut or "").strip())[0]
    if kelime:
        # "Sizes: Rectangle 3″ x 4″ (...), Scalloped ..." gibi tek satirda birden fazla sekil: virgulle bol
        parca = [p.strip() for s in satir for p in re.split(r",\s*(?=[A-Z])", s)]
        es = [p for p in parca if re.search(rf"\b{re.escape(kelime)}\b", p, re.I)]
        if es:
            return es
    return [s for s in satir if not re.search(r"(circle|heart|star|snowflake|round|bell|oval|tree|rectangle|scalloped|paw|tag)",
                                              s, re.I)] or satir


def urun_veri(ham, pid):
    U = {ad: jy(ham, f"urun_{pid}_{ad}.json") for ad in ("v1", "v1_sizes", "printfiles", "v2", "v2_variants", "v2_availability")}
    U["tablo"] = {}
    for t in liste(sozluk(yanit(U["v1_sizes"]).get("result")).get("size_tables")):
        for m in liste(t.get("measurements")):
            for x in liste(m.get("values")):
                deg = x.get("value") if x.get("value") is not None else f"{x.get('min_value')}-{x.get('max_value')}"
                U["tablo"].setdefault(x.get("size"), []).append(f"{m.get('type_label')} {deg} {m.get('unit') or t.get('unit')}")
    r1 = sozluk(yanit(U["v1"]).get("result"))
    U["p"] = sozluk(r1.get("product"))
    U["vs1"] = liste(r1.get("variants"))
    U["p2"] = sozluk(yanit(U["v2"]).get("data"))
    U["vs2"] = liste(yanit(U["v2_variants"]).get("data"))
    pf = sozluk(yanit(U["printfiles"]).get("result"))
    U["pf_id"] = {x.get("printfile_id"): x for x in liste(pf.get("printfiles"))}
    U["pf_var"] = {x.get("variant_id"): sozluk(x.get("placements")) for x in liste(pf.get("variant_printfiles"))}
    U["pf_yer"] = sozluk(pf.get("available_placements"))
    U["fiyat2"], U["yer_fiyat2"] = {}, {}
    for cur in ("USD", "EUR", "EUR_europe", "USD_north_america"):
        d = sozluk(yanit(jy(ham, f"urun_{pid}_v2_prices_{cur}.json")).get("data"))
        for v in liste(d.get("variants")):
            U["fiyat2"][(v.get("id"), cur)] = [(t.get("technique_key"), t.get("price")) for t in liste(v.get("techniques"))]
        U["yer_fiyat2"][cur] = [(pl.get("id"), pl.get("title"), pl.get("price")) for pl in liste(sozluk(d.get("product")).get("placements"))]
    U["uyg2"] = {}
    for v in liste(yanit(U["v2_availability"]).get("data")):
        for t in liste(v.get("techniques")):
            for sr in liste(t.get("selling_regions")):
                U["uyg2"].setdefault(v.get("catalog_variant_id"), []).append(f"{sr.get('name')}:{sr.get('availability')}")
    return U


def yuz_bilgi(U, ac):
    """Baski alanlari: v2 placements (mockup haric) + v1 printfiles available_placements etiketi + aciklama satiri."""
    yer2 = [(p.get("placement"), p.get("technique")) for p in liste(U["p2"].get("placements")) if p.get("placement") != "mockup"]
    etiket = U["pf_yer"]
    alan = [f"{y}" + (f" '{etiket.get(y)}'" if etiket.get(y) else "") for y, _ in yer2] or [f"{y} '{e}'" for y, e in etiket.items()]
    if not alan:
        return YOK, YOK
    yer = [y for y, _ in yer2] or list(etiket)
    satir = aciklama_satir(ac, YUZ)
    if any(re.search(r"back", y or "", re.I) for y in yer):
        sinif = "cift yuz: on + arka ayri baski alani"
    elif any(re.search(r"2-side|two-sided", str(e), re.I) for e in list(etiket.values()) + satir):
        sinif = "cift yuz: ayni tasarim, tek dosya"
    else:
        sinif = "tek yuz"
    return sinif, "; ".join(alan) + (" | aciklama: " + " / ".join(satir) if satir else "")


def rapor(cikti):
    ham = cikti / "ham"
    aday = jy(ham, "_adaylar.json") or {}
    k1 = jy(ham, "kargo_v1.json") or []
    k2 = jy(ham, "kargo_v2.json") or []
    K1 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in k1}
    K2 = {(str(x["urun"]), x["varyant"], x["ulke"]): x for x in k2}
    satirlar, kargo_satir, urunler = [], [], []
    for pid in sorted(aday, key=int):
        U = urun_veri(ham, pid)
        p, p2 = U["p"], U["p2"]
        ac = p2.get("description") or p.get("description") or ""
        yuz, alan = yuz_bilgi(U, ac)
        teknik = sorted({f"{y}:{t}" for y, t in ((x.get("placement"), x.get("technique")) for x in liste(p2.get("placements")))
                         if y != "mockup"}) or [t.get("display_name") for t in liste(p.get("techniques"))]
        kaynak = "v1" if U["vs1"] else ("v2" if U["vs2"] else YOK)
        vs = U["vs1"] or U["vs2"]
        uru = {"id": pid, "ad": p.get("title") or p2.get("name") or YOK, "neden": aday[pid]["neden"], "http_v1": http(U["v1"]),
               "http_v2": http(U["v2"]), "kaynak": kaynak, "yuz": yuz, "alan": alan, "teknik": teknik or [YOK], "aciklama": ac,
               "durdu": p2.get("is_discontinued", p.get("is_discontinued")), "varyant": [], "cikis": {}, "U": U,
               "kargo_var": any(k[0] == pid for k in K1)}
        ek1 = "; ".join(f"{f.get('id')}:{f.get('additional_price')}" for f in liste(p.get("files")) if f.get("type") != "mockup") or YOK
        for v in vs:
            vid = v.get("id")
            yer = U["pf_var"].get(vid) or {}
            pf = [(y, U["pf_id"].get(i) or {}) for y, i in yer.items()]
            durum1 = liste(v.get("availability_status"))
            f2 = {c: "; ".join(f"{t}:{pr}" for t, pr in U["fiyat2"].get((vid, c)) or []) or YOK
                  for c in ("USD", "EUR", "EUR_europe", "USD_north_america")}
            s = {
                "urun_id": pid, "urun_adi": uru["ad"], "varyant_kaynagi": kaynak, "varyant_id": vid,
                "varyant_adi": v.get("name") or YOK, "sekil_boyut_api": v.get("size") or YOK,
                "olcu_aciklama": " / ".join(olcu_satir(ac, v.get("size"))) or YOK,
                "olcu_tablo_v1": "; ".join(U["tablo"].get(v.get("size")) or []) or YOK,
                "kalinlik_aciklama": " / ".join(aciklama_satir(ac, KALINLIK)) or YOK,
                "yuz": yuz, "baski_alanlari": alan, "teknik": "; ".join(uru["teknik"]),
                "arka_ek_ucret_v1_usd": ek1 if kaynak == "v1" else YOK,
                "alan_fiyat_v2_usd": "; ".join(f"{i}:{pr}" for i, _, pr in U["yer_fiyat2"]["USD"]) or YOK,
                "alan_fiyat_v2_eur": "; ".join(f"{i}:{pr}" for i, _, pr in U["yer_fiyat2"]["EUR"]) or YOK,
                "malzeme_aciklama": " / ".join(aciklama_satir(ac, MALZEME)) or YOK,
                "paket_kurdele_aciklama": " / ".join(aciklama_satir(ac, PAKET)) or YOK,
                "mense_aciklama": " / ".join(aciklama_satir(ac, MENSE)) or YOK,
                "origin_country_v1": p.get("origin_country") or YOK,
                "fiyat_usd_v1": v.get("price") if kaynak == "v1" and v.get("price") is not None else f"{YOK} (v1 HTTP {uru['http_v1']})",
                "fiyat_usd_v2": f2["USD"], "fiyat_eur_v2": f2["EUR"], "fiyat_eur_v2_europe": f2["EUR_europe"],
                "fiyat_usd_v2_north_america": f2["USD_north_america"],
                "uretim_bolgesi_durum_v1": "; ".join(f"{a.get('region')}:{a.get('status')}" for a in durum1) or YOK,
                "uygunluk_v2": "; ".join(U["uyg2"].get(vid) or []) or YOK,
                "printfile_id": "; ".join(f"{y}={x.get('printfile_id')}" for y, x in pf) or YOK,
                "printfile_px": "; ".join(f"{y}={x.get('width')}x{x.get('height')}" for y, x in pf) or YOK,
                "printfile_dpi": "; ".join(f"{y}={x.get('dpi')}" for y, x in pf) or YOK,
                "fill_mode": "; ".join(f"{y}={x.get('fill_mode')}" for y, x in pf) or YOK,
                "can_rotate": "; ".join(f"{y}={x.get('can_rotate')}" for y, x in pf) or YOK,
                "tasma_payi": " / ".join(aciklama_satir(ac, r"bleed")) or YOK,
            }
            gonderim_var, gonderim_yok, cikis = [], [], set()
            for ulke in ULKELER:
                x1, x2 = K1.get((pid, vid, ulke)), K2.get((pid, vid, ulke))
                if x1 is None:
                    s[f"kargo_{ulke}_usd"] = "sorgulanmadi"
                    continue
                s1, s2 = liste(yanit(x1).get("result")), liste(yanit(x2).get("data"))
                e = en_ucuz(s1) if http(x1) == 200 else None
                m2 = next((y for y in s2 if e and y.get("shipping") == e.get("id")), None) or (en_ucuz(s2) if http(x2) == 200 else None)
                dep = sorted({sh.get("departure_country") for sh in liste((m2 or {}).get("shipments")) if sh.get("departure_country")})
                gum = sorted({str(sh.get("customs_fees_possible")) for sh in liste((m2 or {}).get("shipments"))
                              if "customs_fees_possible" in sh})
                takip = {**(anahtar_bul(e, "track") if e else {}), **(anahtar_bul(m2, "track") if m2 else {})}
                if e:
                    s[f"kargo_{ulke}_usd"] = e.get("rate")
                    gonderim_var.append(ulke)
                else:
                    s[f"kargo_{ulke}_usd"] = f"HATA {http(x1)}"
                    gonderim_yok.append(f"{ulke} ({hata_mesaj(x1)})")
                cikis.update(dep)
                uru["cikis"].setdefault(ulke, set()).update(dep)
                kargo_satir.append({
                    "urun_id": pid, "urun_adi": uru["ad"], "varyant_id": vid, "varyant_adi": v.get("name"), "ulke": ulke,
                    "adres": ", ".join(f"{a}={b}" for a, b in ADRES.get(ulke, {}).items()), "http_v1": http(x1),
                    "yontem_id": e.get("id") if e else YOK, "yontem_adi": (e.get("name") or "").strip() if e else YOK,
                    "ucret": e.get("rate") if e else YOK, "para": e.get("currency") if e else YOK,
                    "min_gun": e.get("minDeliveryDays") if e else YOK, "max_gun": e.get("maxDeliveryDays") if e else YOK,
                    "min_tarih": e.get("minDeliveryDate") if e else YOK, "max_tarih": e.get("maxDeliveryDate") if e else YOK,
                    "tum_secenekler_v1": "; ".join(f"{y.get('id')}={y.get('rate')} {y.get('currency')}" for y in s1) or YOK,
                    "http_v2": http(x2), "ucret_v2": m2.get("rate") if m2 else YOK,
                    "cikis_ulkesi_v2": ", ".join(dep) or YOK, "gumruk_olasi_v2": ", ".join(gum) or YOK,
                    "takip_api": json.dumps(takip, ensure_ascii=False) if takip else YOK,
                    "hata_v1": "" if e else hata_mesaj(x1)})
            s["gonderim_var_9ulke"] = ", ".join(gonderim_var) or ("sorgulanmadi" if not uru["kargo_var"] else "yok")
            s["gonderim_yok_9ulke"] = "; ".join(gonderim_yok) or ("sorgulanmadi" if not uru["kargo_var"] else "yok")
            s["cikis_ulkesi_v2"] = ", ".join(sorted(cikis)) or ("sorgulanmadi" if not uru["kargo_var"] else YOK)
            satirlar.append(s)
            uru["varyant"].append(s)
        # urun duzeyi: ABD disi hicbir ulkeye ucret donmedi ve ABD disi her hata "United States only"
        ks = [k for k in kargo_satir if k["urun_id"] == pid]
        abd_disi = [k for k in ks if k["ulke"] != "US"]
        uru["yalniz_abd"] = bool(abd_disi) and all(k["ucret"] == YOK and "united states only" in k["hata_v1"].lower() for k in abd_disi) \
            and any(k["ulke"] == "US" and k["ucret"] != YOK for k in ks)
        for s in uru["varyant"]:
            s["yalniz_abd_urun"] = "EVET" if uru["yalniz_abd"] else ("sorgulanmadi" if not uru["kargo_var"] else "hayir")
        urunler.append(uru)

    alanlar = list(dict.fromkeys(k for s in satirlar for k in s)) or ["urun_id"]
    with open(cikti / "PRINTFUL_ORNAMENT.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)
    ka = list(kargo_satir[0].keys()) if kargo_satir else ["urun_id"]
    with open(cikti / "PRINTFUL_ORNAMENT_KARGO.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ka)
        w.writeheader()
        w.writerows(kargo_satir)
    (cikti / "PRINTFUL_ORNAMENT.md").write_text(md(urunler, kargo_satir, ham), encoding="utf-8")
    print(f"RAPOR urun {len(urunler)} | varyant satiri {len(satirlar)} | kargo satiri {len(kargo_satir)}", flush=True)
    return 0 if satirlar else 1


def aralik(deg):
    s = sorted({x for x in deg if fl(x) is not None}, key=fl)
    if not s:
        return YOK
    return s[0] if len(s) == 1 else f"{s[0]}-{s[-1]}"


def kargo_hucre(ks):
    """urun x ulke: varyantlar arasi en ucuz yontem ucreti (aralik), yontem id ve gun."""
    if not ks:
        return "sorgulanmadi"
    ok = [k for k in ks if fl(k["ucret"]) is not None]
    if not ok:
        m = sorted({kisa_hata(k["hata_v1"]) for k in ks})
        return "GONDERILMEZ (API: " + " / ".join(m) + ")"
    a = aralik([k["ucret"] for k in ok])
    yon = sorted({str(k["yontem_id"]) for k in ok})
    gun = sorted({f"{k['min_gun']}-{k['max_gun']}" for k in ok})
    ek = (f"; {len(ks) - len(ok)} varyant HATA: " + " / ".join(sorted({kisa_hata(k["hata_v1"]) for k in ks if k not in ok}))
          if len(ok) < len(ks) else "")
    return f"{a} ({'/'.join(yon)}, {'/'.join(gun)} g{ek})"


def md(urunler, kargo, ham):
    ist = jy(ham, "_istekler.json") or []
    post = sorted({x["yol"] for x in ist if x["yontem"] == "POST"})
    zaman = max((x["zaman"] for x in ist), default=YOK)
    L = ["# Printful ornament urunleri (salt okuma)", "",
         f"Kaynak: Printful API v1 + v2, ham yanitlar `ham/`. Son istek {zaman}. Istek {len(ist)}: GET "
         f"{sum(1 for x in ist if x['yontem'] == 'GET')}, POST {sum(1 for x in ist if x['yontem'] == 'POST')} (yalniz {', '.join(post) or 'yok'}).",
         "", "Notlar:",
         "- Fiyat USD = v1 `variants[].price` (kargo haric); v1'de olmayan urunde v2 `prices?currency=USD&selling_region_name=worldwide`.",
         "- Olcu, malzeme, kurdele/paket: urun aciklama metni (API, aynen); aciklamada olcu yoksa v1 /products/{id}/sizes tablosu. Hesap yok.",
         "- Uretim yeri = v2 /v2/shipping-rates `shipments[].departure_country` (hedef ulke basina). v1 `availability_status` "
         "bolgesi ayrica CSV'de (`uretim_bolgesi_durum_v1`); uretim yeriyle ayni sey degil (881: v1 'US', cikis LV).",
         "- Satilabildigi bolge = 9 ulke kargo sorgusunda ucret donen ulkeler; donmeyende API hata mesaji.",
         "- Kargo: 1 adet, ornek adres (merkez posta kodu), USD, en ucuz secenek. Takip: yanitlarda takip alani yok -> API vermedi.",
         "", "## 1. Urunler", "",
         "| urun | sekil/olcu | yuz | fiyat USD | uretim yeri (cikis ulkesi) | satilabildigi bolgeler (9 ulke testi) | baski dosyasi piksel (dpi) |",
         "|---|---|---|---|---|---|---|"]
    for u in urunler:
        sekil = list(dict.fromkeys(f"{v['sekil_boyut_api']}: " + (v["olcu_aciklama"] if v["olcu_aciklama"] != YOK else
                                   (f"v1 olcu tablosu: {v['olcu_tablo_v1']}" if v["olcu_tablo_v1"] != YOK else YOK))
                                   for v in u["varyant"]))
        if u["kaynak"] == "v1":
            fiyat = aralik([v["fiyat_usd_v1"] for v in u["varyant"]])
        else:
            fiyat = aralik([pr.split(":")[-1] for v in u["varyant"] for pr in v["fiyat_usd_v2"].split("; ")]) + " (v2)"
        grup = {}
        for hedef, dep in u["cikis"].items():
            grup.setdefault(", ".join(sorted(dep)) or "-", []).append(hedef)
        cik = "; ".join(f"{d} (hedef {', '.join(h)})" for d, h in grup.items() if d != "-") or (
            "sorgulanmadi" if not u["kargo_var"] else YOK)
        var = sorted({b for v in u["varyant"] for b in v["gonderim_var_9ulke"].split(", ")} - {"yok", "sorgulanmadi"},
                     key=ULKELER.index)
        if not u["kargo_var"]:
            uyg = sorted({x for v in u["varyant"] for x in v["uygunluk_v2"].split("; ")})
            bol = f"kargo sorgulanmadi (v1 HTTP {u['http_v1']}); v2 uygunluk: {', '.join(uyg)}"
        elif u["yalniz_abd"]:
            bol = "**YALNIZ ABD** (API: ships to United States only)"
        else:
            bol = ", ".join(var) + ("" if len(var) == len(ULKELER) else " (eksik ulke: tablo 2)")
        px = list(dict.fromkeys(f"{v['printfile_px']} ({v['printfile_dpi'].split('=')[-1]} dpi)" for v in u["varyant"]))
        L.append(f"| {u['id']} {u['ad']} | {'<br>'.join(sekil) or YOK} | {u['yuz']} | {fiyat} | {cik} | {bol} | {'<br>'.join(px) or YOK} |")
    L += ["", "## 2. Kargo ucreti (USD, 1 adet, en ucuz yontem). Hucre: ucret (yontem id, min-max is gunu)", "",
          "| urun | " + " | ".join(ULKELER) + " |", "|---|" + "---|" * len(ULKELER)]
    for u in urunler:
        hucre = [kargo_hucre([k for k in kargo if k["urun_id"] == u["id"] and k["ulke"] == ul]) for ul in ULKELER]
        L.append(f"| {u['id']} {u['ad']} | " + " | ".join(hucre) + " |")
    adlar = sorted({(k["yontem_id"], re.sub(r"\s*\(Estimated delivery.*", "", k["yontem_adi"])) for k in kargo if k["ucret"] != YOK})
    L += ["", "Yontem adlari (v1 `name`, tahmini teslim tarihi kismi atildi): " + "; ".join(f"{i} = {a}" for i, a in adlar), ""]
    L += ["## 3. Urun ayrintilari", ""]
    for u in urunler:
        v0 = u["varyant"][0] if u["varyant"] else {}
        L += [f"### {u['id']} {u['ad']}", "",
              f"- eslesme: {', '.join(u['neden'])} | HTTP v1 {u['http_v1']} v2 {u['http_v2']} | varyant kaynagi {u['kaynak']}"
              f" | durdurulmus: {u['durdu'] if u['durdu'] is not None else YOK}",
              f"- yuz: {u['yuz']} | alanlar: {u['alan']}",
              f"- baski teknigi (v2 placement:technique): {', '.join(u['teknik'])}",
              f"- alan ek ucreti: v1 files {v0.get('arka_ek_ucret_v1_usd', YOK)} | v2 USD {v0.get('alan_fiyat_v2_usd', YOK)}"
              f" | v2 EUR {v0.get('alan_fiyat_v2_eur', YOK)}",
              f"- malzeme: {v0.get('malzeme_aciklama', YOK)} | kalinlik: {v0.get('kalinlik_aciklama', YOK)}",
              f"- kurdele/paket: {v0.get('paket_kurdele_aciklama', YOK)}",
              f"- mense: {v0.get('mense_aciklama', YOK)} | v1 origin_country: {v0.get('origin_country_v1', YOK)}",
              f"- tasma payi: {v0.get('tasma_payi', YOK)}", "",
              "| varyant | ad | USD v1 | USD v2 | EUR v2 | EUR europe | USD north_america | v1 bolge | v2 uygunluk | printfile | px | dpi | fill |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for v in u["varyant"]:
            L.append(f"| {v['varyant_id']} | {v['varyant_adi']} | {v['fiyat_usd_v1']} | {v['fiyat_usd_v2']} | {v['fiyat_eur_v2']} | "
                     f"{v['fiyat_eur_v2_europe']} | {v['fiyat_usd_v2_north_america']} | {v['uretim_bolgesi_durum_v1']} | "
                     f"{v['uygunluk_v2']} | {v['printfile_id']} | {v['printfile_px']} | {v['printfile_dpi']} | {v['fill_mode']} |")
        L += ["", "Aciklama metni (API, aynen):", "", "```", (u["aciklama"] or YOK).strip(), "```", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("oku", "rapor"):
        sys.exit(__doc__)
    sys.exit(oku(Path(sys.argv[2])) if sys.argv[1] == "oku" else rapor(Path(sys.argv[2])))
