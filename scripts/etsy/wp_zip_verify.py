#!/usr/bin/env python3
"""
TESLIM ZIP'LERININ DOGRULANMASI (DELIVERY, salt okur) - 4 Eyl 2026.

Her cift icin DELIVERY/<CIFT> indirilir, 4 ZIP acilir ve olculur:
  - girdi sayisi ve ad listesi (4 wallpaper + LICENSE.txt + kurulum PDF'i)
  - testzip (bozuk girdi yok)
  - PDF ve LICENSE'in kaynakla BAYT esitligi
  - ornek ZIP'lerde PDF sayfa sayisi (/Type /Page sayimi)
Indirilen dosyalar cift bitince silinir (disk sabit kalir). Ilerleme sayaci:
islenen/toplam, gecen, kalan, yuzde. Hicbir sey yazilmaz.
"""
import argparse
import csv
import hashlib
import os
import random
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import EDITIONS, log  # noqa: E402

ZIP_DEVICES = ["Phone", "Tablet", "Desktop", "Watch"]
GUIDE_NAME = "HOW_TO_SET_YOUR_WALLPAPER.pdf"


def rclone(*args):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)[-400:]


def sayfa_sayisi(data):
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return n if n else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--guide", required=True)
    ap.add_argument("--drive", default="gdrive:ASTROLOVE")
    ap.add_argument("--zip-dir", default="WALLPAPER/DELIVERY")
    ap.add_argument("--work", default="_verify")
    ap.add_argument("--sample", type=int, default=5, help="PDF sayfa sayisi acilacak ZIP adedi")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    lic = Path(a.license).read_bytes()
    pdf = Path(a.guide).read_bytes()
    log(f"referans: LICENSE {len(lic)} B, PDF {len(pdf)} B sha256 {hashlib.sha256(pdf).hexdigest()[:16]}")
    pairs = [p.strip() for p in Path(a.pairs_file).read_text().split() if p.strip()]
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(20260904)
    satirlar, hatalar = [], []
    t0 = time.time()
    ornekler = set(rnd.sample(range(len(pairs) * len(EDITIONS)), min(a.sample, len(pairs) * len(EDITIONS))))
    idx = 0
    for i, pair in enumerate(pairs):
        up = pair.upper()
        d = work / up
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        rc, tail = rclone("copy", f"{a.drive}/{a.zip_dir}/{up}", str(d), "--include", "*.zip",
                          "--transfers", "4", "--checkers", "8")
        zips = sorted(d.glob("*.zip"))
        if rc != 0 or len(zips) != len(EDITIONS):
            hatalar.append(f"{pair}: {len(zips)}/4 ZIP" + (f" (rclone {rc}: {tail[-120:]})" if rc else ""))
        for ed in EDITIONS:
            p = d / f"AstroLove_{pair}_{ed}.zip"
            r = dict(cift=pair, edisyon=ed, dosya=p.name)
            if not p.exists():
                r["sonuc"] = "YOK"
                hatalar.append(f"{pair}/{ed}: ZIP yok")
                satirlar.append(r)
                idx += 1
                continue
            beklenen = [f"AstroLove_{pair}_{ed}_{dev}.jpg" for dev in ZIP_DEVICES] + ["LICENSE.txt", GUIDE_NAME]
            try:
                with zipfile.ZipFile(p) as zf:
                    names = zf.namelist()
                    bozuk = zf.testzip()
                    ic_pdf = zf.read(GUIDE_NAME) if GUIDE_NAME in names else b""
                    ic_lic = zf.read("LICENSE.txt") if "LICENSE.txt" in names else b""
            except Exception as e:                                   # noqa: BLE001
                r.update(sonuc="ACILAMADI", detay=str(e)[:120])
                hatalar.append(f"{pair}/{ed}: acilamadi")
                satirlar.append(r)
                idx += 1
                continue
            r.update(boyut=p.stat().st_size, girdi=len(names), testzip=bozuk or "temiz",
                     ad_listesi="EVET" if sorted(names) == sorted(beklenen) else "HAYIR",
                     pdf_bayt="EVET" if ic_pdf == pdf else "HAYIR",
                     license_bayt="EVET" if ic_lic == lic else "HAYIR")
            if idx in ornekler:
                r["pdf_sayfa"] = sayfa_sayisi(ic_pdf)
                log(f"    ornek: {p.name} PDF sayfa {r['pdf_sayfa']}")
            ok = (len(names) == 6 and r["ad_listesi"] == "EVET" and r["pdf_bayt"] == "EVET"
                  and r["license_bayt"] == "EVET" and bozuk is None)
            r["sonuc"] = "PASS" if ok else "FAIL"
            if not ok:
                hatalar.append(f"{pair}/{ed}: {r['ad_listesi']}/{r['pdf_bayt']}/{r['license_bayt']}/{bozuk}")
            satirlar.append(r)
            idx += 1
        shutil.rmtree(d, ignore_errors=True)
        el = time.time() - t0
        rem = el / (i + 1) * (len(pairs) - i - 1)
        log(f"[{i + 1}/{len(pairs)}] {pair}: {sum(1 for s in satirlar[-4:] if s.get('sonuc') == 'PASS')}/4 PASS "
            f"| gecen {el / 60:.1f} dk kalan {rem / 60:.1f} dk %{100 * (i + 1) / len(pairs):.0f}")

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    n_pass = sum(1 for r in satirlar if r.get("sonuc") == "PASS")
    ozet = (f"SONUC: {n_pass}/{len(satirlar)} ZIP PASS"
            + (f" | HATA ({len(hatalar)}): " + "; ".join(hatalar[:12]) if hatalar else ""))
    log(ozet)
    sayfalar = [r.get("pdf_sayfa") for r in satirlar if r.get("pdf_sayfa") is not None]
    log(f"ornek PDF sayfa sayilari: {sayfalar}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## ZIP dogrulama\n\n{ozet}\n\nornek PDF sayfa: {sayfalar}\n")
    return 0 if n_pass == len(satirlar) and not hatalar else 1


if __name__ == "__main__":
    sys.exit(main())
