#!/usr/bin/env python3
"""Galeri v11 W02-W06 dosya kapisi + sahne olcumu (Merkez 29 Eki). ETSY YOK. Pillow 11.0.0.
Girdi --dir: wa-kart-v11 cikti klasoru (TEMP/POSTER_GALERI_V11/<damga>/W02_W06/<kosu>: kartlar, MANIFEST_W02_W06_p*.csv,
KART_OZET_V11_<CIFT>.json). --ref: onayli CANCER_LIBRA ornegi (Serdar 29 Eki "ok", kosu 40874497709) ayni bicim.
DOSYA KAPISI (FAIL = cikis 1):
  - MANIFEST: 78 cift x {W02_SEMBOL, W03_KISISEL, W05_SUREC, W06_GENEL} + tek ORTAK W04_FORMAT, durum PASS, satir tekrari yok.
  - her dosya JPEG 3000x2250, sha256 = MANIFEST.
  - ciftler arasi sha256 tekrari 0 (W04 tek dosya; diger kartlar cifte ozel).
  - W03 kaynak kapisi (KART_OZET w03_kaynak): oran 4:5, renk MB, isimler = CSV, hepsi PASS (uretimde zorunlu; burada yeniden okunur).
  - W04 sha256 onayli ornekle ayni; CANCER_LIBRA kartlari onayli ornekle ayni sha256 (deterministik uretim).
SAHNE OLCUMU (--olc; ESIK YOK, yalniz dagilim; esik Serdar onayiyla): onayli CANCER_LIBRA ayni kartina en buyuk kanal farki,
  sabit bantlar (baslik y 0-450, alt not y 2000-2250; ciftten bagimsiz metin) p99.9 / max; W05 / W06 ayrica poster kutulari
  (KART_OZET foto_kutu, iki kartin birlesimi) disinda tum kart. Dagilim (min / medyan / en buyuk) KAPI_W02_W06.md'de.
Cikti --out: KAPI_W02_W06.csv, KAPI_W02_W06.md, OLC_W02_W06.json."""
import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

import numpy as np
from PIL import Image

KARTLAR = ("W02_SEMBOL", "W03_KISISEL", "W05_SUREC", "W06_GENEL")
BOYUT = (3000, 2250)
SABIT = ((0, 450), (2000, 2250))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def manifest(d):
    rows = []
    for m in sorted(Path(d).glob("MANIFEST_W02_W06*.csv")):
        rows += list(csv.DictReader(open(m, encoding="utf-8")))
    return rows


def fark(a, b, maske=None):
    d = np.abs(np.asarray(a.convert("RGB"), np.int16) - np.asarray(b.convert("RGB"), np.int16)).max(2)
    v = d[maske] if maske is not None else d.ravel()
    return round(float(np.percentile(v, 99.9)), 1), int(v.max())


def bant_maske():
    m = np.zeros((BOYUT[1], BOYUT[0]), bool)
    for y0, y1 in SABIT:
        m[y0:y1] = True
    return m


def foto_maske(kutular):
    m = np.ones((BOYUT[1], BOYUT[0]), bool)
    for x0, y0, x1, y1 in kutular:
        m[y0:y1, x0:x1] = False
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True); ap.add_argument("--ref", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ciftler", default="data/pod/pod78_ids.csv"); ap.add_argument("--olc", action="store_true")
    a = ap.parse_args(argv)
    d, rd, out = Path(a.dir), Path(a.ref), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ciftler = [r["cift"] for r in csv.DictReader(open(a.ciftler, encoding="utf-8"))]
    rows, sorun = manifest(d), []
    anah = [(r["cift"], r["ad"]) for r in rows]
    if len(set(anah)) != len(anah):
        sorun.append("MANIFEST satir tekrari")
    bek = {(c, k) for c in ciftler for k in KARTLAR} | {("ORTAK", "W04_FORMAT")}
    eksik, fazla = bek - set(anah), set(anah) - bek
    if eksik or fazla:
        sorun.append(f"MANIFEST tamligi: eksik {len(eksik)} {sorted(eksik)[:4]} fazla {len(fazla)} {sorted(fazla)[:4]}")
    ref_rows = {(r["cift"], r["ad"]): r for r in manifest(rd)}
    R, shas = [], {}
    for r in rows:
        p = d / r["dosya"]; n = []
        if r.get("durum") != "PASS":
            n.append(f"MANIFEST durum {r.get('durum')}")
        if not p.exists():
            n.append("dosya yok")
        else:
            with Image.open(p) as im:
                if im.format != "JPEG" or im.size != BOYUT:
                    n.append(f"bicim {im.format} {im.size}")
            h = sha(p)
            if h != r["sha256"]:
                n.append("sha256 MANIFEST ile ayni degil")
            shas.setdefault(h, []).append(r["dosya"])
            rr = ref_rows.get((r["cift"], r["ad"])) if r["cift"] in ("ORTAK", "CANCER_LIBRA") else None
            if rr and rr["sha256"] != h:
                n.append("onayli ornekten farkli sha256 (deterministik uretim beklenir)")
        R.append(dict(cift=r["cift"], ad=r["ad"], dosya=r["dosya"], sha256=r["sha256"], durum="FAIL" if n else "PASS", neden="; ".join(n)))
    tekrar = {h: v for h, v in shas.items() if len(v) > 1}
    if tekrar:
        sorun.append(f"ciftler arasi sha256 tekrari {len(tekrar)}: {list(tekrar.values())[:3]}")
    w03 = []
    for c in ciftler:
        k = d / f"KART_OZET_V11_{c}.json"
        if not k.exists():
            w03.append(f"{c}: KART_OZET yok"); continue
        w = json.loads(k.read_text(encoding="utf-8")).get("w03_kaynak") or {}
        if not (w.get("oran_PASS") and (w.get("renk") or {}).get("PASS") and (w.get("isim") or {}).get("PASS")):
            w03.append(f"{c}: W03 kaynak kapisi {w}")
    if w03:
        sorun.append(f"W03 kaynak kapisi FAIL {len(w03)}: {w03[:3]}")
    olc = {}
    if a.olc:
        rk = json.loads((rd / "KART_OZET_V11_CANCER_LIBRA.json").read_text(encoding="utf-8"))["kartlar"]
        bm = bant_maske()
        for k in KARTLAR:
            ref = Image.open(rd / f"CANCER_LIBRA_{k}.jpg")
            rkutu = rk[f"CANCER_LIBRA_{k}.jpg"].get("foto_kutu") or []
            v = []
            for c in ciftler:
                p = d / f"{c}_{k}.jpg"; ko = d / f"KART_OZET_V11_{c}.json"
                if not p.exists() or not ko.exists():
                    continue
                im = Image.open(p)
                x = dict(cift=c, sabit=fark(im, ref, bm))
                if k in ("W05_SUREC", "W06_GENEL"):
                    kutu = (json.loads(ko.read_text(encoding="utf-8"))["kartlar"].get(f"{c}_{k}.jpg") or {}).get("foto_kutu") or []
                    x["poster_disi"] = fark(im, ref, foto_maske(rkutu + kutu))
                v.append(x)
            olc[k] = v
        (out / "OLC_W02_W06.json").write_text(json.dumps(olc, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "KAPI_W02_W06.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(R[0]) if R else ["dosya"]); w.writeheader(); w.writerows(R)
    nf = sum(1 for x in R if x["durum"] != "PASS")
    md = [f"# Galeri v11 W02-W06 dosya kapisi\n", f"dosya {len(R)} | PASS {len(R) - nf} | FAIL {nf} | genel sorun {len(sorun)}",
          f"sha256 tekrari {len(tekrar)} | W03 kaynak kapisi FAIL {len(w03)}\n"]
    md += [f"- SORUN: {s}" for s in sorun] + [f"- {x['dosya']} FAIL: {x['neden']}" for x in R if x["durum"] != "PASS"]
    if olc:
        md.append("\n## Sahne olcumu (onayli CANCER_LIBRA'ya; ESIK YOK, dagilim)\n")
        for k, v in olc.items():
            for alan in ("sabit", "poster_disi"):
                xs = [x[alan] for x in v if alan in x]
                if not xs:
                    continue
                p9 = [t[0] for t in xs]; mx = [t[1] for t in xs]
                md.append(f"- {k} {alan}: n {len(xs)} | p99.9 min {min(p9)} medyan {statistics.median(p9)} en buyuk {max(p9)} | "
                          f"max min {min(mx)} medyan {statistics.median(mx)} en buyuk {max(mx)}")
    (out / "KAPI_W02_W06.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:4]), flush=True)
    return 1 if (nf or sorun) else 0


if __name__ == "__main__":
    sys.exit(main())
