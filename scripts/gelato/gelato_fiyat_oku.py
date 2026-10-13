#!/usr/bin/env python3
"""Gelato FIYAT OKUMA (13 Eki 2026, Serdar onayi): YALNIZ Product API. SIPARIS YOK, quote YOK.
Izinli uclar (kod icinde kilitli): GET /v3/catalogs, GET /v3/catalogs/{uid}, POST /v3/catalogs/{uid}/products:search
(salt arama), GET /v3/products/{uid}/prices. Baska her istek RuntimeError ile durur. Anahtar ortamdan (GELATO_API_KEY), loga yazilmaz.
Cikti: GELATO_FIYAT.csv (urun, gsm, boy, ulke, para birimi, fiyat, productUid, + kagit/cerceve/yon), _katalog_*.json (oznitelik dokumu).
"""
import csv, json, os, re, sys, time
from pathlib import Path
import requests

BASE = "https://product.gelatoapis.com/v3"
IZIN = [re.compile(r"^GET /v3/catalogs$"), re.compile(r"^GET /v3/catalogs/[^/]+$"),
        re.compile(r"^POST /v3/catalogs/[^/]+/products:search$"), re.compile(r"^GET /v3/products/[^/]+/prices$")]
ULKE = {"US": "USD", "DE": "EUR", "GB": "GBP", "AU": "AUD"}
BOY = {"8x10": (8, 10), "11x14": (11, 14), "12x16": (12, 16), "12x18": (12, 18), "16x20": (16, 20), "16x24": (16, 24),
       "18x24": (18, 24), "20x30": (20, 30), "24x36": (24, 36), "A4": (210, 297), "A3": (297, 420), "A2": (420, 594)}
GSM = {"Classic Matte": 170, "Premium Matte": 200, "Archival Matte": 250}
S = requests.Session(); S.headers.update({"X-API-KEY": os.environ["GELATO_API_KEY"], "Content-Type": "application/json"})
CAGRI = [0]


def istek(yontem, yol, **kw):
    if not any(p.match(f"{yontem} /v3{yol}") for p in IZIN): raise RuntimeError(f"IZINSIZ UC: {yontem} {yol}")
    for d in range(4):
        CAGRI[0] += 1; r = S.request(yontem, BASE + yol, timeout=60, **kw)
        if r.status_code == 429 or r.status_code >= 500: time.sleep(2 + 3 * d); continue
        if r.status_code != 200: raise SystemExit(f"HATA {yontem} {yol} -> {r.status_code}: {r.text[:300]}")
        return r.json()
    raise SystemExit(f"HATA {yontem} {yol}: tekrarlar tukendi")


def mm(v):
    try: return float(v)
    except Exception: return None


def boy_kesin(p):
    """Format metni boyu dogrudan veriyorsa True (8x10-inch, a4); yalniz olcuyle eslesme (or. 210x300-mm ~ A4) False."""
    at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
    fmt = at.get("paperformat") or at.get("format") or ""
    return bool(re.search(r"(^|[^0-9])\d+x\d+-inch|(^|[^0-9a-z])a[0-9]($|[^0-9])", fmt))


def boy_bul(p):
    """Urunun boyu: once format oznitelik metni (8x10 / A4), sonra dikey olcu (mm, +-4)."""
    at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
    fmt = at.get("paperformat") or at.get("format") or ""
    for ad, (a, b) in BOY.items():
        if ad.startswith("A"):
            if re.search(rf"(^|[^0-9a-z]){ad.lower()}($|[^0-9])", fmt): return ad
        elif re.search(rf"(^|[^0-9]){a}x{b}-inch", fmt) or re.search(rf"(^|[^0-9]){b}x{a}-inch", fmt): return ad
    dim = p.get("dimensions") or {}
    w = mm((dim.get("Width") or {}).get("value")); h = mm((dim.get("Height") or {}).get("value"))
    if not w or not h: return None
    k, u = sorted((w, h))
    for ad, (a, b) in BOY.items():
        aa, bb = (a, b) if ad.startswith("A") else (a * 25.4, b * 25.4)
        if abs(k - aa) <= 4 and abs(u - bb) <= 4: return ad
    return None


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    kat = istek("GET", "/catalogs"); kat = kat.get("data", kat) if isinstance(kat, dict) else kat
    (out / "_kataloglar.json").write_text(json.dumps(kat, indent=1, ensure_ascii=False))
    secili = [c["catalogUid"] for c in kat if "poster" in c.get("catalogUid", "").lower()]
    print(f"katalog: {len(kat)} | poster kataloglari: {secili}", flush=True)
    urunler = {}
    for cu in secili:
        det = istek("GET", f"/catalogs/{cu}"); (out / f"_katalog_{cu}.json").write_text(json.dumps(det, indent=1, ensure_ascii=False))
        off, top = 0, []
        while True:
            r = istek("POST", f"/catalogs/{cu}/products:search", json={"limit": 100, "offset": off})
            p = r.get("products") or []; top += p
            if len(p) < 100 or off > 20000: break
            off += 100
        urunler[cu] = top
        (out / f"_urunler_{cu}.json").write_text(json.dumps(top[:5], indent=1, ensure_ascii=False))
        print(f"{cu}: {len(top)} urun ({time.time() - t0:.0f}s)", flush=True)
    # oznitelik deger ozetleri
    ozet = {cu: {} for cu in urunler}
    for cu, ps in urunler.items():
        for p in ps:
            for k, v in (p.get("attributes") or {}).items(): ozet[cu].setdefault(k, {}).setdefault(str(v), 0); ozet[cu][k][str(v)] += 1
    (out / "_oznitelik_ozet.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False))
    for cu, o in ozet.items():
        for k, v in o.items(): print(f"  {cu}.{k}: {sorted(v)[:40]}", flush=True)
    # secim: mat (uncoated) kagit, gsm, dikey yon
    def kagit(p):
        at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
        pt = at.get("papertype", ""); m = re.search(r"(\d{3})-gsm", pt)
        return pt, int(m.group(1)) if m else None, ("uncoated" in pt or "matt" in pt), at.get("orientation", "")
    satir = []; isler = []
    poster_kat = [cu for cu in urunler if "framed" not in cu.lower()]
    cer_kat = [cu for cu in urunler if "framed" in cu.lower()]
    for urun, gsm in GSM.items():
        for ad in BOY:
            aday = []
            for cu in poster_kat:
                for p in urunler[cu]:
                    pt, g, mat, yon = kagit(p)
                    if g == gsm and mat and boy_bul(p) == ad:
                        aday.append(((0 if boy_kesin(p) else 1, 0 if cu == "posters" else 1, 0 if yon in ("ver", "portrait", "vertical") else 1), p, cu, pt, yon))
            if not aday:
                for u in ULKE: satir.append(dict(urun=urun, gsm=gsm, boy=ad, ulke=u, para=ULKE[u], fiyat="YOK", productUid="", kagit="", cerceve="", yon=""))
                continue
            aday.sort(key=lambda x: x[0]); _, p, cu, pt, yon = aday[0]
            isler.append(dict(urun=urun, gsm=gsm, boy=ad, p=p, kagit=pt, cerceve="", yon=yon))
    # cerceveli: her boy x her cerceve rengi, tercihen 200 gsm mat, dikey
    renkler = set()
    for cu in cer_kat:
        for p in urunler[cu]:
            at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
            renk = at.get("framecolor", "") or at.get("framecolour", "")
            if renk: renkler.add(renk)
    print(f"cerceve renkleri: {sorted(renkler)}", flush=True)
    for ad in BOY:
        for renk in sorted(renkler):
            aday = []
            for cu in cer_kat:
                for p in urunler[cu]:
                    at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
                    if (at.get("framecolor") or at.get("framecolour")) != renk or boy_bul(p) != ad: continue
                    pt, g, mat, yon = kagit(p)
                    if at.get("mattetype", at.get("passepartout", "none")) not in ("", "none", "no-passepartout", "no-matte"): continue
                    aday.append(((0 if boy_kesin(p) else 1, 0 if g == 200 else 1 if g == 250 else 2), 0 if yon in ("ver", "portrait", "vertical") else 1, p, pt, yon, g))
            if not aday:
                for u in ULKE: satir.append(dict(urun=f"Framed {renk}", gsm="", boy=ad, ulke=u, para=ULKE[u], fiyat="YOK", productUid="", kagit="", cerceve=renk, yon=""))
                continue
            aday.sort(key=lambda x: (x[0], x[1])); _, _, p, pt, yon, g = aday[0]
            isler.append(dict(urun=f"Framed {renk}", gsm=g or "", boy=ad, p=p, kagit=pt, cerceve=renk, yon=yon))
    n = len(isler) * len(ULKE)
    for i, isx in enumerate(isler):
        uid = isx["p"]["productUid"]
        for u, para in ULKE.items():
            r = istek("GET", f"/products/{uid}/prices", params={"country": u, "currency": para})
            r = r if isinstance(r, list) else r.get("data", r.get("prices", []))
            bir = [x for x in r if int(x.get("quantity", 0)) == 1 and int(x.get("pageCount") or 1) in (0, 1)] or [x for x in r if int(x.get("quantity", 0)) == 1]
            fiyat = bir[0]["price"] if bir else "YOK"; pc = bir[0].get("currency", para) if bir else para
            satir.append(dict(urun=isx["urun"], gsm=isx["gsm"], boy=isx["boy"], ulke=u, para=pc, fiyat=fiyat, productUid=uid,
                              kagit=isx["kagit"], cerceve=isx["cerceve"], yon=isx["yon"]))
        k = (i + 1) * len(ULKE); g = time.time() - t0
        if (i + 1) % 10 == 0 or i + 1 == len(isler):
            print(f"[fiyat {k}/{n}] gecen {g:.0f}s | kalan ~{g / k * (n - k):.0f}s | %{100 * k // n}", flush=True)
    sira = {a: i for i, a in enumerate(BOY)}
    satir.sort(key=lambda x: (x["urun"].startswith("Framed"), x["urun"], sira[x["boy"]], list(ULKE).index(x["ulke"])))
    with open(out / "GELATO_FIYAT.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["urun", "gsm", "boy", "ulke", "para birimi", "fiyat", "productUid", "kagit", "cerceve", "yon"])
        for s in satir: w.writerow([s[k] for k in ("urun", "gsm", "boy", "ulke", "para", "fiyat", "productUid", "kagit", "cerceve", "yon")])
    pm = {(s["boy"], s["ulke"]): s["fiyat"] for s in satir if s["urun"] == "Premium Matte"}
    print("OZET Premium Matte 8x10: " + ", ".join(f"{u} {pm.get(('8x10', u))}" for u in ULKE), flush=True)
    print("OZET Premium Matte 24x36: " + ", ".join(f"{u} {pm.get(('24x36', u))}" for u in ULKE), flush=True)
    print(f"OZET cerceve renkleri: {sorted(renkler)} | altin: {'VAR' if any('gold' in r or 'brass' in r for r in renkler) else 'YOK'}", flush=True)
    print(f"OZET satir {len(satir)} | YOK {sum(1 for s in satir if s['fiyat'] == 'YOK')} | API cagri {CAGRI[0]} | {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
