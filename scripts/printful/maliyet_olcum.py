#!/usr/bin/env python3
"""Poster kar tablosu icin eksik maliyet OLCUMU (Merkez 28 Eki, Serdar onayi). Yalniz olcum; oneri yok. ETSY API YOK.
Printful'da siparis ONAYLANMAZ, odeme yok, Etsy baglantisi kurulmaz.
1) printful : GET /products/1 (Enhanced Matte Paper Poster (in)) ve /products/268 ((cm)) varyantlari; 5x7 ve 8x10 icin
              POST /orders/estimate-costs (siparis olusturmaz) x ulke (US-NY, US-OR, DE, GB, NO, AU, JP, CA, TR); ornek IS adresi, ad "Test".
              Uc yoksa (HTTP 404 / 405) TASLAK yolu: POST /orders (confirm yok) -> GET -> DELETE -> GET ile silinme kaniti. A4 varyantlari listelenir.
2) belge    : Printful yardim merkezi makaleleri (Zendesk API, salt okuma) metin olarak; vergi / Etsy entegrasyonu.
3) teslim   : PRINTFUL_POSTER.csv (Drive, 25 Eki) -> boy x AU / JP en kucuk / en buyuk gun, > 20 gun boylar, ayni boyun hizli varyanti.
4) prodigi  : AU teklif (POST /v4.0/quotes, siparis degil) yavas boylar + 5x7; aday urun aileleri GET /products ile var mi bakilir.
5) ulke     : Drive siparis kayitlari (POD_ORDERS_STATE.csv, KUPA_SIPARIS PRINTFUL_TASLAK.json) + Printful siparis listesi (GET):
              yalniz ulke ve adet; ad / adres / receipt ciktiya yazilmaz. Test receipt'leri haric.
Kullanim: maliyet_olcum.py <out> --csv PRINTFUL_POSTER.csv --pod-state <csv> --kupa-dir <dir> (env PRINTFUL_TOKEN, PRODIGI_API_KEY)"""
import argparse
import csv
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

PF = "https://api.printful.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 astrolove-ops"
DOSYA_URL = "https://raw.githubusercontent.com/caliserdar-maker/astrolove-ops/main/data/pod/cl_galeri_final19/04_kisisellestirme.jpg"
# ornek IS adresleri (kamu binalari / isletmeler; gercek musteri degil), ad "Test"
ADRES = {
    "US-NY": dict(country_code="US", state_code="NY", city="New York", zip="10118", address1="350 5th Ave"),
    "US-OR": dict(country_code="US", state_code="OR", city="Portland", zip="97204", address1="1221 SW 4th Ave"),
    "DE": dict(country_code="DE", city="Berlin", zip="10557", address1="Platz der Republik 1"),
    "GB": dict(country_code="GB", city="London", zip="WC2N 5DN", address1="Trafalgar Square"),
    "NO": dict(country_code="NO", city="Oslo", zip="0026", address1="Karl Johans gate 22"),
    "AU": dict(country_code="AU", state_code="NSW", city="Sydney", zip="2000", address1="Bennelong Point"),
    "JP": dict(country_code="JP", city="Chiyoda-ku, Tokyo", zip="100-0005", address1="1-9-1 Marunouchi"),
    "CA": dict(country_code="CA", state_code="ON", city="Ottawa", zip="K1A 0A9", address1="111 Wellington St"),
    "TR": dict(country_code="TR", city="Istanbul", zip="34435", address1="Taksim Meydani, Beyoglu")}
MAKALE = [("support", 41396638872977), ("support", 41396636552721), ("help", 360016054999), ("help", 4402032573586),
          ("support", 41396660283921), ("help", 360014067599)]
ARAMA = ["Etsy sales tax", "Etsy VAT", "manual order tax", "marketplace facilitator", "Norway VAT", "UK VAT orders"]
TEST_RID = re.compile(r"^(900000\d+|99000\d+|4000000001|1000000001)$")
S = requests.Session(); S.headers.update({"User-Agent": UA, "Accept": "application/json"})


def norm(b):
    return re.sub(r"[\s\"″'”]", "", str(b)).replace("×", "x").lower()


def sonuc(d):
    """Printful yaniti: result sozluk ise o, degilse (hata metni) {}"""
    r = d.get("result") if isinstance(d, dict) else None
    return r if isinstance(r, dict) else {}


def pf(yontem, yol, veri=None):
    for d in range(3):
        r = S.request(yontem, PF + yol, json=veri, timeout=60,
                      headers={"Authorization": f"Bearer {os.environ['PRINTFUL_TOKEN']}", "Content-Type": "application/json"})
        if r.status_code == 429 and d < 2:
            time.sleep(30); continue
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {"ham": r.text[:1500]}


def printful(out):
    R = {"urunler": {}, "a4": [], "tahmin": [], "taslak": [], "yol": None}
    var = {}
    for uid in (1, 268):
        st, d = pf("GET", f"/products/{uid}")
        vs = sonuc(d).get("variants") or []
        R["urunler"][uid] = dict(status=st, ad=(sonuc(d).get("product") or {}).get("title"),
                                 varyant=[dict(id=v["id"], boy=v.get("size"), fiyat=v.get("price")) for v in vs])
        for v in vs:
            var[(uid, norm(v.get("size")))] = v
            if "a4" in norm(v.get("size")) or norm(v.get("size")) in ("21x30cm", "8.27x11.69", "21x29.7cm"):
                R["a4"].append(dict(urun=uid, id=v["id"], boy=v.get("size"), fiyat=v.get("price")))
    hedef = [(b, var.get((1, b))) for b in ("5x7", "8x10")]
    for b, v in hedef:
        if not v:
            R["tahmin"].append(dict(boy=b, hata="varyant bulunamadi")); continue
        for ul, adr in ADRES.items():
            govde = {"recipient": dict(name="Test", **adr), "shipping": "STANDARD", "currency": "USD",
                     "items": [{"variant_id": v["id"], "quantity": 1, "files": [{"url": DOSYA_URL}]}]}
            st, d = pf("POST", "/orders/estimate-costs", govde)
            R["tahmin"].append(dict(boy=b, varyant=v["id"], ulke=ul, status=st, costs=sonuc(d).get("costs"),
                                    hata=None if st == 200 else d))
            print(f"tahmin {b} {ul}: HTTP {st} {(sonuc(d).get('costs') or {}).get('total')}", flush=True)
            time.sleep(0.7)
    ok = [t for t in R["tahmin"] if t.get("status") == 200]
    if ok:
        R["yol"] = "estimate-costs"
    elif all(t.get("status") in (404, 405) for t in R["tahmin"] if "status" in t):
        R["yol"] = "taslak"; taslak(R, hedef)
    else:
        R["yol"] = "HATA (taslak denenmedi: uc var ama istek reddedildi)"
    (out / "PRINTFUL_VERGI.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    with open(out / "PRINTFUL_VERGI.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["boy", "varyant", "ulke", "http", "baski", "kargo", "vergi", "kdv", "toplam", "para", "yol"])
        for t in R["tahmin"] + R["taslak"]:
            c = t.get("costs") or {}
            w.writerow([t.get("boy"), t.get("varyant"), t.get("ulke"), t.get("status"), c.get("subtotal"), c.get("shipping"),
                        c.get("tax"), c.get("vat"), c.get("total"), c.get("currency"), t.get("yol", R["yol"])])
    return R


def taslak(R, hedef):
    """estimate-costs yoksa: TASLAK (confirm yok) -> oku -> sil -> silindi mi"""
    for b, v in hedef:
        for ul, adr in ADRES.items():
            ext = f"TEST-VERGI-{os.environ.get('GITHUB_RUN_ID', 'yerel')}-{b}-{ul}"
            st, d = pf("POST", "/orders", {"external_id": ext, "recipient": dict(name="Test", **adr), "shipping": "STANDARD",
                                           "items": [{"variant_id": v["id"], "quantity": 1, "files": [{"url": DOSYA_URL}]}]})
            oid = sonuc(d).get("id")
            kayit = dict(boy=b, varyant=v["id"], ulke=ul, status=st, yol="taslak", order_id=oid,
                         durum=sonuc(d).get("status"), costs=sonuc(d).get("costs"))
            if oid:
                s2, d2 = pf("GET", f"/orders/{oid}"); kayit["oku"] = dict(status=s2, durum=sonuc(d2).get("status"))
                if sonuc(d2).get("costs"):
                    kayit["costs"] = d2["result"]["costs"]
                s3, d3 = pf("DELETE", f"/orders/{oid}"); kayit["sil"] = dict(status=s3, durum=sonuc(d3).get("status"))
                s4, d4 = pf("GET", f"/orders/{oid}"); kayit["sil_sonra"] = dict(status=s4, durum=sonuc(d4).get("status"))
            R["taslak"].append(kayit); print(f"taslak {b} {ul}: {kayit.get('durum')} sil {kayit.get('sil')} sonra {kayit.get('sil_sonra')}",
                                             flush=True)
            time.sleep(0.7)


def _get(url, **kw):
    try:
        r = S.get(url, timeout=60, **kw)
        return r.status_code, (r.json() if r.ok else {})
    except Exception as e:                                       # noqa: BLE001  (28 Eki: support.printful.com DNS cozulmedi)
        return f"{type(e).__name__}", {}


def belge(out):
    D = []
    for _, aid in MAKALE:
        for alan in ("help", "support"):                         # makale kimligi iki alan adinda da denenir
            st, j = _get(f"https://{alan}.printful.com/api/v2/help_center/en-us/articles/{aid}.json")
            a = j.get("article") or {}
            if a:
                break
        D.append(dict(id=aid, alan=alan, status=st, baslik=a.get("title"), url=a.get("html_url"),
                      guncelleme=a.get("updated_at"), govde=re.sub(r"<[^>]+>", " ", a.get("body") or "")))
    for q in ARAMA:
        for alan in ("help", "support"):
            st, j = _get(f"https://{alan}.printful.com/api/v2/help_center/articles/search.json", params={"query": q})
            for a in (j.get("results") or [])[:6]:
                if all(x["id"] != a["id"] for x in D):
                    D.append(dict(id=a["id"], alan=alan, status=st, arama=q, baslik=a.get("title"), url=a.get("html_url"),
                                  guncelleme=a.get("updated_at"), govde=re.sub(r"<[^>]+>", " ", a.get("body") or "")))
    (out / "PRINTFUL_BELGE.json").write_text(json.dumps(D, indent=1, ensure_ascii=False))
    with open(out / "PRINTFUL_BELGE.md", "w") as f:
        for a in D:
            f.write(f"## {a.get('baslik')}\n{a.get('url')} (id {a.get('id')}, guncelleme {a.get('guncelleme')}, HTTP {a.get('status')})\n\n"
                    f"{re.sub(r'[ ]+', ' ', a.get('govde') or '')[:8000]}\n\n")
    print(f"belge: {len(D)} makale, govdeli {sum(1 for a in D if a.get('govde'))}", flush=True)


def teslim(out, csv_yol):
    rows = list(csv.DictReader(open(csv_yol, encoding="utf-8")))
    print("teslim CSV sutunlari:", list(rows[0].keys()) if rows else None, flush=True)
    T = defaultdict(list)
    for r in rows:
        if r["ulke"] in ("AU", "JP") and r.get("adet", "1") == "1" and r.get("min_gun"):
            T[(r["urun"], r["boy"], r["ulke"])].append((r["kargo_adi"], r["kargo"], int(r["min_gun"]), int(r["max_gun"])))
    with open(out / "TESLIM_AU_JP.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["urun", "boy", "ulke", "kargo_adi", "kargo_usd", "min_gun", "max_gun", "20_gun_asar"])
        for (u, b, ul), ss in sorted(T.items()):
            for s in ss:
                w.writerow([u, b, ul, s[0], s[1], s[2], s[3], s[3] > 20])
    print(f"teslim: {len(T)} boy x ulke", flush=True)
    return T


def prodigi(out, T):
    key = os.environ.get("PRODIGI_API_KEY")
    if not key:
        return print("prodigi: anahtar yok", flush=True)
    H = {"X-API-Key": key, "Content-Type": "application/json"}
    def kod(b):                                           # '12x16' -> 12X16, 'a4(8.27x11.69)' -> A4
        m = re.match(r"^(a\d)", b)
        return m.group(1).upper() if m else re.sub(r"[^0-9x.]", "", b).upper()
    # yavas: AU'da en ucuz (standart) secenegin en buyuk gunu > 20 (urun 1, canli olcu ailesi)
    yavas = sorted({kod(norm(b)) for (u, b, ul), ss in T.items()
                    if ul == "AU" and u == "1" and min(ss, key=lambda s: float(s[1] or 1e9))[3] > 20})
    boylar = sorted(set(yavas) | {"5X7"})
    P = []
    for kodu in boylar:
        b = kodu
        for aile in ("EMA", "FAP", "BAP", "HPR"):
            sku = f"GLOBAL-{aile}-{kodu}"
            r = requests.get(f"https://api.prodigi.com/v4.0/products/{sku}", headers=H, timeout=60)
            var = r.status_code == 200
            kayit = dict(boy=b, sku=sku, urun_var=var, urun_http=r.status_code,
                         aciklama=(r.json().get("product") or {}).get("description") if var else None, teklif=[])
            if var:
                for y in ("Budget", "Standard", "Express"):
                    q = requests.post("https://api.prodigi.com/v4.0/quotes", headers=H, timeout=60, json={
                        "shippingMethod": y, "destinationCountryCode": "AU", "currencyCode": "USD",
                        "items": [{"sku": sku, "copies": 1, "assets": [{"printArea": "default"}]}]})
                    d = q.json() if q.headers.get("content-type", "").startswith("application/json") else {}
                    for qq in d.get("quotes") or []:
                        cs = qq.get("costSummary") or {}
                        kayit["teklif"].append(dict(yontem=y, http=q.status_code, urun=(cs.get("items") or {}).get("amount"),
                                                    kargo=(cs.get("shipping") or {}).get("amount"),
                                                    vergi=(cs.get("totalTax") or {}).get("amount"), toplam=(cs.get("totalCost") or {}).get("amount"),
                                                    para=(cs.get("totalCost") or {}).get("currency"),
                                                    gonderi=[dict(tasiyici=s.get("carrier"), ulke=(s.get("fulfillmentLocation") or {}).get("countryCode"),
                                                                  lab=(s.get("fulfillmentLocation") or {}).get("labCode"))
                                                             for s in qq.get("shipments") or []]))
                    if not d.get("quotes"):
                        kayit["teklif"].append(dict(yontem=y, http=q.status_code, hata=str(d)[:300]))
                    time.sleep(0.5)
            P.append(kayit); print(f"prodigi {sku}: urun {r.status_code}, teklif {len(kayit['teklif'])}", flush=True)
    (out / "PRODIGI_AU.json").write_text(json.dumps(dict(yavas_boylar=yavas, sonuc=P), indent=1, ensure_ascii=False))


def ulke(out, pod_state, kupa_dir):
    U = {"pod_state": Counter(), "pod_stage": Counter(), "kupa_taslak": Counter(), "printful_api": Counter(), "printful_api_durum": Counter()}
    if pod_state and os.path.exists(pod_state):
        for r in csv.DictReader(open(pod_state, encoding="utf-8")):
            if TEST_RID.match(str(r.get("receipt_id", ""))):
                continue
            U["pod_state"][(r.get("country") or "?").upper()] += 1; U["pod_stage"][r.get("stage") or "?"] += 1
    for p in glob.glob(f"{kupa_dir}/**/PRINTFUL_TASLAK.json", recursive=True) if kupa_dir else []:
        rid = Path(p).parts[-3] if len(Path(p).parts) >= 3 else ""
        if TEST_RID.match(rid) or "TEST" in p.upper():
            continue
        try:
            U["kupa_taslak"][(json.load(open(p)).get("recipient") or {}).get("country_code") or "?"] += 1
        except Exception:                                       # noqa: BLE001
            U["kupa_taslak"]["okunamadi"] += 1
    off = 0
    while True:                                                 # Printful siparis listesi (GET; ad / adres yazilmaz)
        st, d = pf("GET", f"/orders?offset={off}&limit=100")
        rs = d.get("result") if st == 200 and isinstance(d.get("result"), list) else []
        for o in rs:
            if str(o.get("external_id") or "").startswith("TEST") or TEST_RID.match(str(o.get("external_id") or "")):
                continue
            U["printful_api"][((o.get("recipient") or {}).get("country_code") or "?")] += 1
            U["printful_api_durum"][o.get("status") or "?"] += 1
        if len(rs) < 100:
            break
        off += 100
    (out / "ULKE_DAGILIMI.json").write_text(json.dumps({k: dict(v) for k, v in U.items()}, indent=1))
    print("ulke:", json.dumps({k: dict(v) for k, v in U.items()}), flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--csv"); ap.add_argument("--pod-state")
    ap.add_argument("--kupa-dir"); ap.add_argument("--bolum", default="printful,belge,teslim,prodigi,ulke")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); b = a.bolum.split(",")
    if "printful" in b:
        printful(out)
    if "belge" in b:
        belge(out)
    T = teslim(out, a.csv) if "teslim" in b and a.csv else {}
    if "prodigi" in b:
        prodigi(out, T)
    if "ulke" in b:
        ulke(out, a.pod_state, a.kupa_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
