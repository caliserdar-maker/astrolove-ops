#!/usr/bin/env python3
"""Galeri v11 canli dogrulama (Merkez 29 Eki: pilot ve 77 ilan sonrasi). ETSY API YOK: canli okuma galeri-v11-yedek-oku
(ilan basina 4 GET, Etsy kilidiyle) + galeri-v11-yedek-indir (CDN, kilitsiz) ciktisindan; yukleme kaydi galeri-v11-yukle SONRA_<ilan>.json.
Girdiler:
  --canli   TEMP/POSTER_GALERI_V11_YEDEK/<damga> (yukleme SONRASI okuma): <ilan>_<CIFT>/GALERI.json + r<rank>_<id>.jpg
  --sonra   SONRA_<ilan>.json klasoru (TEMP/POSTER_GALERI_V11_YUKLE/KOSU/<kosu>/), birden fazla verilebilir
  --galeri  TEMP/POSTER_GALERI_V11/<damga> (<CIFT>_W01_KAPAK|W07_MB|W08_DB|W09_PW|W10_WP.jpg)
  --kart    wa-kart-v11 cikti klasoru (<CIFT>_W02_SEMBOL|W03_KISISEL|W05_SUREC|W06_GENEL.jpg, ORTAK_W04_FORMAT.jpg)
  --alt data/pod/galeri_v11_alt.csv  --ciftler data/pod/pod78_ids.csv (listing_id, cift, a, b)  --sadece virgullu listing_id
Ilan basina kapilar (biri tutmazsa FAIL):
  galeri   10 gorsel, rank 1..10 tekil; kimlik sirasi = SONRA son_ids (yuklenen gorseller W01..W10 sirasinda)
  alt      her rank alt metni = sablon (galeri_v10_liste.alt_metin, <A>/<B> = burclar)
  bag      5 renk bagi property 200: Champagne Ivory 1, Midnight Blue 7, Deep Black 8, Pure White 9, Warm Parchment 10
  state    active (GALERI.json ilan.state); video 1
  sha      kaynak dosyanin sha256'si = SONRA yukleme_kaydi sha256 (yuklenen dosya dogru kaynak)
  ncc      indirilen canli gorsel (Etsy yeniden kodlar, sha256 farkli) ile kaynak: 256x192 gri NCC; ESIKSIZ kimlik kurali: her rank'in
           en benzer kaynagi ilanin 10 kaynagi icinde kendisi olmali (argmax). min NCC raporda (dagilim).
Cikti --out: DOGRULA.csv (ilan basina), DOGRULA.md, DOGRULA.json. Cikis 0 = hepsi PASS, 1 = FAIL var."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_v10_liste as L  # noqa: E402

N = 10
RENK_SIRA = {"Champagne Ivory": 1, "Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}
KAYNAK = {1: "W01_KAPAK", 2: "W02_SEMBOL", 3: "W03_KISISEL", 4: "W04_FORMAT", 5: "W05_SUREC", 6: "W06_GENEL",
          7: "W07_MB", 8: "W08_DB", 9: "W09_PW", 10: "W10_WP"}
BOY = (256, 192)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vek(p):
    with Image.open(p) as im:
        v = np.asarray(im.convert("L").resize(BOY, Image.BILINEAR), np.float64).ravel()
    v -= v.mean()
    return v / (np.linalg.norm(v) or 1.0)


def kaynak_yol(cift, s, galeri, kart):
    if s == 4:
        return Path(kart) / "ORTAK_W04_FORMAT.jpg"
    return (Path(kart) if 2 <= s <= 6 else Path(galeri)) / f"{cift}_{KAYNAK[s]}.jpg"


def ilan(lid, r, d, sonra, sab, galeri, kart):
    neden, olc = [], {}
    j = json.loads((d / "GALERI.json").read_text(encoding="utf-8"))
    g = sorted(j.get("gorseller") or [], key=lambda x: x.get("rank") or 0)
    ids = [x["listing_image_id"] for x in g]
    if len(g) != N or [x["rank"] for x in g] != list(range(1, N + 1)) or len(set(ids)) != N:
        neden.append(f"galeri {len(g)} gorsel / rank {[x['rank'] for x in g]}")
    if ids != sonra.get("son_ids"):
        neden.append(f"kimlik sirasi SONRA son_ids ile ayni degil ({ids} != {sonra.get('son_ids')})")
    alt = L.alt_metin(sab, r["a"], r["b"])
    kotu = [x["rank"] for x in g if x.get("alt_text") != alt.get(x["rank"])]
    if kotu:
        neden.append(f"alt metin farkli: rank {kotu}")
    rk = {x["listing_image_id"]: x["rank"] for x in g}
    b = j.get("baglar") or []
    sira = {x.get("value"): rk.get(x.get("image_id")) for x in b}
    if len(b) != 5 or sira != RENK_SIRA or any(x.get("property_id") != 200 for x in b):
        neden.append(f"renk baglari {sira}")
    st = (j.get("ilan") or {}).get("state")
    if st != "active":
        neden.append(f"state {st}")
    if len(j.get("videolar") or []) != 1:
        neden.append(f"video {len(j.get('videolar') or [])}")
    kay = {int(x["hedef_sira"]): x for x in sonra.get("yukleme_kaydi") or []}
    kv, cv = {}, {}
    for s in range(1, N + 1):
        p = kaynak_yol(r["cift"], s, galeri, kart)
        if not p.exists():
            neden.append(f"kaynak yok {p.name}"); continue
        if (kay.get(s) or {}).get("sha256") != sha(p):
            neden.append(f"rank {s}: yuklenen sha256 kaynak {p.name} ile ayni degil")
        if (kay.get(s) or {}).get("listing_image_id") != (ids[s - 1] if len(ids) >= s else None):
            neden.append(f"rank {s}: yuklenen kimlik canli rank {s} degil")
        kv[s] = vek(p)
        c = d / f"r{s}_{ids[s - 1]}.jpg" if len(ids) >= s else None
        if not c or not c.exists():
            neden.append(f"canli gorsel indirilmemis r{s}"); continue
        cv[s] = vek(c)
    for s, v in cv.items():
        m = {t: float(v @ k) for t, k in kv.items()}
        en = max(m, key=m.get)
        olc[s] = round(m.get(s, -1.0), 4)
        if en != s:
            neden.append(f"rank {s}: canli gorsel en cok kaynak {en}'e benziyor (NCC {m[en]:.3f} > {m.get(s, -1):.3f})")
    return dict(ilan=lid, cift=r["cift"], durum="FAIL" if neden else "PASS", neden="; ".join(neden),
                ncc_min=min(olc.values()) if olc else None, ncc=olc, state=st)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--canli", required=True); ap.add_argument("--sonra", required=True, action="append")
    ap.add_argument("--galeri", required=True); ap.add_argument("--kart", required=True)
    ap.add_argument("--alt", required=True); ap.add_argument("--ciftler", required=True)
    ap.add_argument("--sadece", default=""); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sab = {int(r["sira"]): r for r in csv.DictReader(open(a.alt, encoding="utf-8-sig"))}
    if sorted(sab) != list(range(1, N + 1)):
        raise SystemExit("alt metin sablonu 1..10 degil")
    rows = {r["listing_id"]: r for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig"))}
    s = [x.strip() for x in a.sadece.split(",") if x.strip()] or list(rows)
    sonra = {}
    for k in a.sonra:
        for p in sorted(Path(k).rglob("SONRA_*.json")):   # KOSU/<kosu>/ilanlar/SONRA_<ilan>.json
            sonra[p.stem.split("_", 1)[1]] = json.loads(p.read_text(encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = []
    for lid in s:
        r = rows.get(lid)
        d = Path(a.canli) / f"{lid}_{r['cift']}" if r else None
        if not r or not d.is_dir() or lid not in sonra:
            R.append(dict(ilan=lid, cift=(r or {}).get("cift", "-"), durum="FAIL", ncc_min=None, ncc={}, state=None,
                          neden="ilan listede yok" if not r else ("canli okuma yok" if not d.is_dir() else "SONRA kaydi yok")))
        else:
            R.append(ilan(lid, r, d, sonra[lid], sab, a.galeri, a.kart))
        print(f"{lid} {R[-1]['cift']} {R[-1]['durum']} ncc_min {R[-1]['ncc_min']} {R[-1]['neden'][:200]}", flush=True)
    with open(out / "DOGRULA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "durum", "state", "ncc_min", "neden"], extrasaction="ignore")
        w.writeheader(); w.writerows(R)
    (out / "DOGRULA.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    nf = sum(1 for x in R if x["durum"] != "PASS")
    nm = [x["ncc_min"] for x in R if x["ncc_min"] is not None]
    md = [f"# Galeri v11 canli dogrulama\n", f"ilan {len(R)} | PASS {len(R) - nf} | FAIL {nf}",
          f"NCC (canli / kaynak, ilan basina en dusuk): min {min(nm) if nm else '-'} medyan {float(np.median(nm)) if nm else '-'}\n"]
    md += [f"- {x['ilan']} {x['cift']} FAIL: {x['neden']}" for x in R if x["durum"] != "PASS"]
    (out / "DOGRULA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
