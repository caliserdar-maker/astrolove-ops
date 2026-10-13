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


def istek(yontem, yol, yok404=False, **kw):
    if not any(p.match(f"{yontem} /v3{yol}") for p in IZIN): raise RuntimeError(f"IZINSIZ UC: {yontem} {yol}")
    for d in range(4):
        CAGRI[0] += 1; r = S.request(yontem, BASE + yol, timeout=60, **kw)
        if r.status_code == 429 or r.status_code >= 500: time.sleep(2 + 3 * d); continue
        if r.status_code == 404 and yok404: return None
        if r.status_code != 200: raise SystemExit(f"HATA {yontem} {yol} -> {r.status_code}: {r.text[:300]}")
        return r.json()
    raise SystemExit(f"HATA {yontem} {yol}: tekrarlar tukendi")


def mm(v):
    try: return float(v)
    except Exception: return None


def boy_kesin(p):
    """Format metni boyu dogrudan veriyorsa True (8x10-inch, a4); yalniz olcuyle eslesme (or. 210x300-mm ~ A4) False."""
    at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
    fmt = at.get("paperformat") or at.get("format") or at.get("unifiedpaperformat") or ""
    return bool(re.search(r"(^|[^0-9])\d+x\d+-inch|(^|[^0-9a-z])a[0-9]($|[^0-9])", fmt))


def boy_bul(p):
    """Urunun boyu: once format oznitelik metni (8x10 / A4), sonra dikey olcu (mm, +-4)."""
    at = {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}
    fmt = at.get("paperformat") or at.get("format") or at.get("unifiedpaperformat") or ""
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


KAGIT_ESDEGER = {170: ("170-gsm-uncoated", "65-lb-cover-uncoated"), 200: ("200-gsm-uncoated", "80-lb-cover-uncoated"),
                 250: ("250-gsm-uncoated-offwhite-archival", "100-lb-cover-uncoated-offwhite-archival")}
DIKEY = ("ver", "portrait", "vertical")


def ozn(p):
    return {k.lower(): str(v).lower() for k, v in (p.get("attributes") or {}).items()}


def kagit_turu(at):
    """(kagit metni, mat mi, silk/parlak mi). PaperType yoksa UnifiedPaperType."""
    pt = at.get("papertype") or at.get("unifiedpapertype") or ""
    return pt, ("uncoated" in pt and "silk" not in pt and "gloss" not in pt), ("silk" in pt or "gloss" in pt or ("coated" in pt and "uncoated" not in pt))


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    kat = istek("GET", "/catalogs"); kat = kat.get("data", kat) if isinstance(kat, dict) else kat
    (out / "_kataloglar.json").write_text(json.dumps(kat, indent=1, ensure_ascii=False))
    POSTER, CERCEVE, CERCEVE_FA = "posters", "framed-posters", "fine-art-framed-poster"     # mounted (paspartulu) ve askili HARIC
    secili = [c["catalogUid"] for c in kat if c.get("catalogUid") in (POSTER, CERCEVE, CERCEVE_FA)]
    print(f"katalog: {len(kat)} | kullanilan: {secili} (mounted-framed-posters paspartulu, poster-hangers / hanging-posters askili: haric)", flush=True)
    urunler = {}
    for cu in secili:
        off, top = 0, []
        while True:
            r = istek("POST", f"/catalogs/{cu}/products:search", json={"limit": 100, "offset": off})
            p = r.get("products") or []; top += p
            if len(p) < 100 or off > 20000: break
            off += 100
        urunler[cu] = top; print(f"{cu}: {len(top)} urun ({time.time() - t0:.0f}s)", flush=True)
    isler, satir = [], []

    def yok(urun, gsm, ad, kagit="", cerceve=""):
        for u in ULKE: satir.append(dict(urun=urun, gsm=gsm, boy=ad, ulke=u, para=ULKE[u], fiyat="YOK", productUid="", kagit=kagit, cerceve=cerceve, yon=""))

    # a) mat posterler: gsm adli kagit once, sonra ABD lb esdegeri; A boylari yalniz tam format (pf_a4 = 210x297)
    for urun, gsm in GSM.items():
        for ad in BOY:
            aday = []
            for p in urunler.get(POSTER, []):
                at = ozn(p); pt = at.get("papertype", "")
                if pt not in KAGIT_ESDEGER[gsm] or boy_bul(p) != ad: continue
                if ad.startswith("A") and not boy_kesin(p): continue
                aday.append(((0 if boy_kesin(p) else 1, KAGIT_ESDEGER[gsm].index(pt), 0 if at.get("orientation") in DIKEY else 1), p, pt, at.get("orientation", "")))
            if not aday: yok(urun, gsm, ad); continue
            aday.sort(key=lambda x: x[0]); _, p, pt, yon = aday[0]
            isler.append(dict(urun=urun, gsm=gsm, boy=ad, p=p, kagit=pt, cerceve="", yon=yon))
    # b) cerceveli (paspartusuz): her renk x boy; MAT (200 gsm uncoated / 80 lb uncoated; yoksa fine-art enhanced matte) + ayri SILK satiri
    renkler = sorted({ozn(p).get("framecolor", "") for cu in (CERCEVE, CERCEVE_FA) for p in urunler.get(cu, [])} - {""})
    print(f"cerceve renkleri: {renkler}", flush=True)
    for ad in BOY:
        for renk in renkler:
            mat, silk = [], []
            for cu in (CERCEVE, CERCEVE_FA):
                for p in urunler.get(cu, []):
                    at = ozn(p)
                    if at.get("framecolor") != renk or boy_bul(p) != ad: continue
                    if ad.startswith("A") and not boy_kesin(p): continue
                    pt, m, sk = kagit_turu(at); g = re.search(r"(\d{3})-gsm", pt); lb = "80-lb" in pt
                    if not ((g and g.group(1) == "200") or lb): continue
                    k = (0 if boy_kesin(p) else 1, 0 if cu == CERCEVE else 1, 0 if at.get("orientation") in DIKEY else 1)
                    (mat if m else silk if sk else []).append((k, p, pt, at.get("orientation", ""), cu))
            for etiket, liste in (("mat", mat), ("silk", silk)):
                urun = f"Framed {renk}" + ("" if etiket == "mat" else " (silk/parlak)")
                if not liste:
                    yok(urun, 200, ad, kagit=f"{etiket} yok", cerceve=renk); continue
                liste.sort(key=lambda x: x[0]); _, p, pt, yon, cu = liste[0]
                isler.append(dict(urun=urun, gsm=200, boy=ad, p=p, kagit=f"{pt} ({cu})", cerceve=renk, yon=yon))
    n = len(isler) * len(ULKE); yok404 = 0
    for i, isx in enumerate(isler):
        uid = isx["p"]["productUid"]
        for u, para in ULKE.items():
            r = istek("GET", f"/products/{uid}/prices", yok404=True, params={"country": u, "currency": para})
            if r is None: yok404 += 1; r = []
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
        for x in satir: w.writerow([x[k] for k in ("urun", "gsm", "boy", "ulke", "para", "fiyat", "productUid", "kagit", "cerceve", "yon")])
    fx = lambda v: v if v == "YOK" else f"{float(v):.2f}"
    for urun in ("Classic Matte", "Premium Matte"):
        print(f"OZET {urun} A4: " + ", ".join(f"{x['ulke']} {fx(x['fiyat'])}" for x in satir if x["urun"] == urun and x["boy"] == "A4"), flush=True)
    altin = [x for x in satir if x["urun"] == "Framed gold" and x["ulke"] == "US"]
    print("OZET mat altin US: " + ", ".join(f"{x['boy']} {fx(x['fiyat'])}" for x in altin), flush=True)
    print(f"OZET satir {len(satir)} | YOK {sum(1 for x in satir if x['fiyat'] == 'YOK')} | fiyat 404 {yok404} | API cagri {CAGRI[0]} | {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
