#!/usr/bin/env python3
"""Printful katalog salt okuma (Merkez 28 Eki madde 3, Serdar onayi): urun 19 (White Glossy Mug) olculeri birincil kaynaktan.
Yalniz GET: /products/19 (varyantlar, aciklama metni), /products/19/sizes?unit=inches,cm (olcu tablosu); v1 olcu tablosu
yoksa /v2/catalog-products/19/sizes. Ham yanitlar + OLCU.md (11 oz / 15 oz yukseklik, cap, hacim satirlari). Token yazilmaz.
Kullanim: PRINTFUL_TOKEN=... katalog_olcu.py <cikti>"""
import json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

API = "https://api.printful.com"
URUN = 19


def get(yol, token):
    for i in range(4):
        try:
            r = urllib.request.Request(API + yol, headers={"Authorization": f"Bearer {token}", "User-Agent": "astrolove-katalog/1"})
            with urllib.request.urlopen(r, timeout=60) as y:
                return y.status, json.load(y)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < 3:
                time.sleep(5 * (i + 1)); continue
            try:
                return e.code, json.load(e)
            except Exception:
                return e.code, {"hata": str(e)}
    return 0, {}


def main():
    token = os.environ["PRINTFUL_TOKEN"].strip(); out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    R = {}
    for ad, yol in (("urun", f"/products/{URUN}"), ("olcu_v1", f"/products/{URUN}/sizes?unit=inches,cm"),
                    ("olcu_v2", f"/v2/catalog-products/{URUN}/sizes")):
        kod, j = get(yol, token); R[ad] = kod
        (out / f"{ad}.json").write_text(json.dumps(j, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"GET {yol} -> {kod}", flush=True)
    u = json.loads((out / "urun.json").read_text(encoding="utf-8")).get("result") or {}
    p = u.get("product") or {}
    sat = [f"# Printful urun {URUN} olculeri (birincil kaynak: Printful API, {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})", "",
           f"urun: {p.get('title') or p.get('model')} | varyantlar: " + ", ".join(sorted({str(v.get('size') or v.get('name')) for v in u.get('variants') or []})), "",
           "## Aciklama metninde olcu gecen satirlar"]
    ac = p.get("description") or ""
    sat += [f"- {s.strip()}" for s in ac.splitlines() if re.search(r"oz|ml|cm|\d\s*(?:\"|″|in\b)|height|diameter", s, re.I)] or ["- (yok)"]
    for ad in ("olcu_v1", "olcu_v2"):
        j = json.loads((out / f"{ad}.json").read_text(encoding="utf-8"))
        res = j.get("result") or j.get("data") or {}
        tablolar = res.get("size_tables") if isinstance(res, dict) else None
        if not tablolar and isinstance(res, list):
            tablolar = [t for r_ in res for t in (r_.get("size_tables") or [])]
        sat += ["", f"## {ad} ({R[ad]})"]
        for t in tablolar or []:
            sat.append(f"- tablo {t.get('type')} birim {t.get('unit')}")
            for m in t.get("measurements") or []:
                v = "; ".join(f"{x.get('size')}: {x.get('value') or (str(x.get('min_value')) + '-' + str(x.get('max_value')))}" for x in m.get("values") or [])
                sat.append(f"  - {m.get('type_label')} ({m.get('unit') or t.get('unit')}): {v}")
        if not tablolar:
            sat.append("- olcu tablosu yok")
    (out / "OLCU.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    print("\n".join(sat), flush=True)
    return 0 if R["urun"] == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
