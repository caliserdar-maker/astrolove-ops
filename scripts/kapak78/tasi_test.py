#!/usr/bin/env python3
"""Poster 78 kapak TASIMA TESTI (Merkez 26 Eki plan adim 3; Serdar onayi). Etsy'ye dokunmaz.
Girdi: TSV (cift, design_id, url; baslik satiri olabilir). Imzali URL loga / depoya / rapora YAZILMAZ (::add-mask::).
Her satir: indir -> JPEG mi, 3000x2250 mi -> <out>/KAPAK_<CIFT>.jpg. <out>/OZET.md (cift, design_id, boyut, sha256, PASS/FAIL).
403 ya da suresi dolmus link: o satir FAIL ("403 / sure dolmus olabilir"), cikis 1."""
import argparse
import csv
import hashlib
import io
import pathlib
import re
import sys
import urllib.error
import urllib.request

from PIL import Image

HEDEF = (3000, 2250)


def maskele(s):
    if s:
        print(f"::add-mask::{s}", flush=True)


def satirlar(yol):
    out = []
    for r in csv.reader(open(yol, encoding="utf-8-sig"), delimiter="\t"):
        r = [c.strip() for c in r]
        if len(r) < 3 or not r[2].lower().startswith("http"):
            continue                                            # baslik / bos satir
        maskele(r[2])
        out.append(dict(cift=r[0], design_id=r[1], url=r[2]))
    return out


def indir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-kapak78/1"})
    with urllib.request.urlopen(req, timeout=120) as y:
        return y.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = satirlar(a.tsv)
    if not rows:
        print("FAIL: TSV'de gecerli satir yok (cift, design_id, url)"); return 1
    sonuc = []
    for n, r in enumerate(rows, 1):
        cift = r["cift"]
        if not re.fullmatch(r"[A-Z]+_[A-Z]+", cift):
            sonuc.append([cift, r["design_id"], "-", "-", "FAIL cift adi gecersiz"]); continue
        try:
            veri = indir(r["url"])
        except urllib.error.HTTPError as e:
            neden = f"HTTP {e.code}" + (" (403: link suresi dolmus olabilir)" if e.code == 403 else "")
            sonuc.append([cift, r["design_id"], "-", "-", f"FAIL {neden}"]); print(f"[{n}/{len(rows)}] {cift} {neden}"); continue
        except Exception as e:  # noqa: BLE001
            sonuc.append([cift, r["design_id"], "-", "-", f"FAIL indirme {type(e).__name__}"]); continue
        sha = hashlib.sha256(veri).hexdigest()
        jpeg = veri[:3] == b"\xff\xd8\xff"
        try:
            im = Image.open(io.BytesIO(veri)); boyut = im.size; fmt = im.format
        except Exception:  # noqa: BLE001
            boyut, fmt = None, None
        ok = jpeg and fmt == "JPEG" and boyut == HEDEF
        if ok:
            (out / f"KAPAK_{cift}.jpg").write_bytes(veri)
        neden = "PASS" if ok else f"FAIL {'JPEG degil' if not (jpeg and fmt == 'JPEG') else ''} {'' if boyut == HEDEF else f'boyut {boyut}'}".strip()
        sonuc.append([cift, r["design_id"], f"{boyut[0]}x{boyut[1]}" if boyut else "-", sha, neden])
        print(f"[{n}/{len(rows)}] {cift} {fmt} {boyut} {len(veri)} bayt {neden}", flush=True)
    gecti = sum(1 for s in sonuc if s[4] == "PASS")
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Poster 78 kapak tasima testi\n\nPASS {gecti} / {len(sonuc)}\n\n| cift | design_id | boyut | sha256 | durum |\n|---|---|---|---|---|\n")
        f.writelines(f"| {' | '.join(map(str, s))} |\n" for s in sonuc)
    print(f"OZET: PASS {gecti}/{len(sonuc)}")
    return 0 if gecti == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
