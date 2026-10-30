#!/usr/bin/env python3
"""Printful 5x7 poster (varyant 16364) baski dosyasi gereksinimi, SALT OKUMA (Merkez 30 Eki, Serdar: 5x7 tedarikci Printful).
Yalniz GET: /products/variant/16364 (urun kimligi, boy), /mockup-generator/printfiles/<urun> (baski dosyasi px / dpi / fill_mode,
varyant -> printfile eslemesi), /v2/catalog-variants/16364 ve /v2/catalog-products/<urun> (v2 bilgisi; yoksa not). Siparis /
yukleme / mockup uretimi yok, Etsy yok. Token ortamdan (PRINTFUL_TOKEN), ciktiya yazilmaz.
Cikti <out>/: ham yanitlar (*.json) + PF_5X7.md (varyant 16364 baski dosyasi: genislik x yukseklik px, dpi, oran, inc)."""
import json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

API = "https://api.printful.com"
VARYANT = 16364


def get(yol, token):
    for i in range(4):
        try:
            r = urllib.request.Request(API + yol, headers={"Authorization": f"Bearer {token}", "User-Agent": "astrolove-pf5x7/1"})
            with urllib.request.urlopen(r, timeout=60) as y:
                return y.status, json.load(y)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < 3:
                time.sleep(5 * (i + 1)); continue
            try:
                return e.code, json.load(e)
            except Exception:
                return e.code, {"hata": str(e)}
        except urllib.error.URLError as e:
            if i < 3:
                time.sleep(5); continue
            return 0, {"hata": str(e)}
    return 0, {}


def main():
    token = os.environ["PRINTFUL_TOKEN"].strip(); out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    md = [f"# Printful 5x7 baski dosyasi (varyant {VARYANT}, salt okuma {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n"]
    k, v = get(f"/products/variant/{VARYANT}", token); (out / "variant_16364.json").write_text(json.dumps(v, indent=1))
    var = (v.get("result") or {}).get("variant") or {}; urun = (v.get("result") or {}).get("product") or {}
    pid = var.get("product_id") or urun.get("id")
    md.append(f"- /products/variant/{VARYANT}: HTTP {k} | urun {pid} {urun.get('title')!r} | varyant {var.get('name')!r} boy {var.get('size')!r}")
    sonuc = 0 if k == 200 and pid else 1
    if pid:
        k2, p = get(f"/mockup-generator/printfiles/{pid}", token); (out / f"printfiles_{pid}.json").write_text(json.dumps(p, indent=1))
        r = p.get("result") or {}
        pf = {x.get("printfile_id"): x for x in r.get("printfiles") or []}
        es = [x for x in r.get("variant_printfiles") or [] if x.get("variant_id") == VARYANT]
        md.append(f"- /mockup-generator/printfiles/{pid}: HTTP {k2} | printfile {len(pf)} | varyant eslemesi {len(es)}")
        for e in es:
            for yer, fid in (e.get("placements") or {}).items():
                f = pf.get(fid) or {}
                w, h, d = f.get("width"), f.get("height"), f.get("dpi")
                oran = round(w / h, 5) if w and h else None
                inc = f"{w / d:.3f} x {h / d:.3f} inc" if w and h and d else "-"
                md.append(f"  - yerlesim {yer}: printfile {fid} | {w} x {h} px | dpi {d} | oran (g/y) {oran} | {inc} | fill_mode "
                          f"{f.get('fill_mode')} | can_rotate {f.get('can_rotate')}")
        if not es:
            sonuc = 1; md.append("  - varyant 16364 printfile eslemesi YOK (dogrulanmadi)")
        md.append(f"- secenek / not: {json.dumps(r.get('options') or [], ensure_ascii=False)[:600]}")
        k3, c = get(f"/v2/catalog-variants/{VARYANT}", token); (out / "v2_variant_16364.json").write_text(json.dumps(c, indent=1))
        md.append(f"- /v2/catalog-variants/{VARYANT}: HTTP {k3}")
        k4, c2 = get(f"/v2/catalog-products/{pid}", token); (out / f"v2_product_{pid}.json").write_text(json.dumps(c2, indent=1))
        d2 = (c2.get("data") or {})
        md.append(f"- /v2/catalog-products/{pid}: HTTP {k4} | teknik {d2.get('techniques')} | yerlesim "
                  f"{[(x.get('placement'), x.get('technique')) for x in d2.get('placements') or []]}")
    (out / "PF_5X7.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return sonuc


if __name__ == "__main__":
    sys.exit(main())
