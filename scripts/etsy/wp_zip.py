#!/usr/bin/env python3
"""
wp-night d) Teslim ZIP'leri: cift basina 4 edisyon ZIP (her biri 4 cihaz JPEG +
LICENSE.txt). Pilot ZIP'i (Cancer_Libra, 31 Agu) yapisiyla birebir:
  AstroLove_<Pair>_<Edition>.zip
    AstroLove_<Pair>_<Edition>_Phone.jpg / _Tablet / _Desktop / _Watch
    LICENSE.txt
ZIP boyutu 20 MB'i asarsa kalite kademesi 95 -> 92 -> 90 (B93 WA_WP_ZIP_V1
karari); her kademe yeniden sikistirir, gecmezse FAIL.

QC (PASS/FAIL, ZIP yeniden acilarak):
  4 ZIP, her ZIP 5 girdi, ad listesi birebir, her JPEG cihaz tuvali boyutunda,
  boyut <= 20 MB, LICENSE.txt bayt bayt kaynakla ayni.
Kullanim:
  wp_zip.py --pair Aries_Leo --wallpapers <dir> --license LICENSE.txt --out <dir>
"""
import argparse
import io
import json
import zipfile
from pathlib import Path

import cv2

from wp_mockup_common import DEVICES, EDITIONS, imread, log

MAX_BYTES = 20 * 1024 * 1024
QUALITY_CASCADE = [95, 92, 90]
ZIP_DEVICES = ["Phone", "Tablet", "Desktop", "Watch"]


def jpeg_bytes(img, q):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q,
                                         cv2.IMWRITE_JPEG_SAMPLING_FACTOR, cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444])
    if not ok:
        raise SystemExit("HATA: JPEG kodlanamadi")
    return buf.tobytes()


def build_zip(pair, ed, wp_dir, license_bytes, out_dir, extras=None):
    """extras: {zip_icindeki_ad: bayt} - istege bagli ek dosyalar (or. kurulum
    PDF'i). Wallpaper'lar ve LICENSE.txt her zaman yazilir; extras en sona
    eklenir. 4 Eyl 2026 (Mo): ilan metni PDF vaat ediyor, ZIP'lerde yoktu."""
    names = [f"AstroLove_{pair}_{ed}_{dev}.jpg" for dev in ZIP_DEVICES]
    srcs = [Path(wp_dir) / n for n in names]
    missing = [str(p) for p in srcs if not p.exists()]
    if missing:
        raise SystemExit(f"HATA: eksik wallpaper: {missing}")
    out = Path(out_dir) / f"AstroLove_{pair}_{ed}.zip"
    used_q = None
    for attempt, q in enumerate([None] + QUALITY_CASCADE):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for n, p in zip(names, srcs):
                zf.writestr(n, p.read_bytes() if q is None else jpeg_bytes(imread(p), q))
            zf.writestr("LICENSE.txt", license_bytes)
            for n, b in (extras or {}).items():
                zf.writestr(n, b)
        data = buf.getvalue()
        used_q = q
        if len(data) <= MAX_BYTES:
            break
        log(f"    {ed}: {len(data)/1e6:.1f} MB > 20 MB, kalite kademesi {QUALITY_CASCADE[attempt] if attempt < len(QUALITY_CASCADE) else 'tukendi'}")
    out.write_bytes(data)
    return out, used_q, len(data)


def qc_zip(path, pair, ed, license_bytes, extras=None):
    names = ([f"AstroLove_{pair}_{ed}_{dev}.jpg" for dev in ZIP_DEVICES]
             + ["LICENSE.txt"] + list((extras or {})))
    issues = []
    size = path.stat().st_size
    if size > MAX_BYTES:
        issues.append(f"boyut {size}")
    with zipfile.ZipFile(path) as zf:
        got = zf.namelist()
        if got != names:
            issues.append(f"icerik {got}")
        else:
            for dev in ZIP_DEVICES:
                n = f"AstroLove_{pair}_{ed}_{dev}.jpg"
                import numpy as np
                im = cv2.imdecode(np.frombuffer(zf.read(n), np.uint8), cv2.IMREAD_COLOR)
                W, H = DEVICES[dev]
                if im is None or im.shape[1] != W or im.shape[0] != H:
                    issues.append(f"{dev} boyut {None if im is None else (im.shape[1], im.shape[0])}")
            if zf.read("LICENSE.txt") != license_bytes:
                issues.append("LICENSE farkli")
            for n, b in (extras or {}).items():
                got = zf.read(n)
                if got != b:
                    issues.append(f"{n} farkli ({len(got)} vs {len(b)} bayt)")
                elif n.lower().endswith(".pdf") and not got.startswith(b"%PDF-"):
                    issues.append(f"{n} PDF basligi yok")
    return dict(file=path.name, size_bytes=size, files=len(names), ok=not issues, issues="; ".join(issues))


def build_pair(pair, wp_dir, license_path, out_dir, editions=EDITIONS, guide_path=""):
    lic = Path(license_path).read_bytes()
    extras = {}
    if guide_path:
        gp = Path(guide_path)
        if not gp.exists():
            raise SystemExit(f"HATA: kurulum kilavuzu yok: {gp}")
        extras[gp.name] = gp.read_bytes()
        log(f"  ek dosya: {gp.name} ({len(extras[gp.name])} bayt)")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    rows = {}
    for ed in editions:
        p, q, n = build_zip(pair, ed, wp_dir, lic, out_dir, extras)
        r = qc_zip(p, pair, ed, lic, extras); r["quality"] = q
        rows[ed] = r
        log(f"  ZIP {pair} {ed}: {n/1e6:.2f} MB kalite {q or 'kaynak'} -> {'PASS' if r['ok'] else 'FAIL ' + r['issues']}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True)
    ap.add_argument("--wallpapers", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--editions", default=",".join(EDITIONS))
    ap.add_argument("--guide", default="",
                    help="ZIP'e eklenecek kurulum PDF'i (bos = eklenmez)")
    a = ap.parse_args()
    rows = build_pair(a.pair, a.wallpapers, a.license, a.out,
                      [e for e in a.editions.split(",") if e], guide_path=a.guide)
    ok = all(r["ok"] for r in rows.values())
    (Path(a.out) / f"zip_{a.pair}.json").write_text(json.dumps(dict(pair=a.pair, ok=ok, zips=rows), indent=1))
    log(f"SONUC ZIP {a.pair}: {'PASS' if ok else 'FAIL'} ({sum(r['ok'] for r in rows.values())}/{len(rows)})")
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
