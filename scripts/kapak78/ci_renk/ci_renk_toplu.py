#!/usr/bin/env python3
"""78 cift Champagne Ivory renk karti (W11_CI) toplu uretim (Serdar 30 Eki: CI gorseli W01 kapak degil, W07-W10 gibi renk karti).
ETSY API YOK. Her cift: ci_renk_karti.py <CIFT>_W07_MB.jpg <CIFT>_W01_KAPAK.jpg <CIFT>_W11_CI.jpg (ayri surec; betigin kapilari:
boyut, MB/W01 birlesim bandi, MB renk satiri referansi). Kapi FAIL olan cift icin dosya yazilmaz, raporlanir.
Ek cikti kapisi: 3000x2250 JPEG. Cikti: <out>/<CIFT>_W11_CI.jpg, MANIFEST.csv (cift, dosya, sha256, durum, neden), KONTAK_W11_CI.jpg
(78 kucuk, cift adli; yd_kontak.pafta), OZET.md. Cikis 0 = 78/78 PASS, 1 = FAIL var."""
import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent))
from yd_kontak import pafta  # noqa: E402

KART = KOK / "ci_renk_karti.py"


def tek(src, out, cift):
    mb, w1, hedef = src / f"{cift}_W07_MB.jpg", src / f"{cift}_W01_KAPAK.jpg", out / f"{cift}_W11_CI.jpg"
    eksik = [p.name for p in (mb, w1) if not p.is_file()]
    if eksik:
        return dict(cift=cift, dosya="", sha256="", durum="FAIL", neden=f"kaynak yok: {' '.join(eksik)}")
    r = subprocess.run([sys.executable, "-I", str(KART), str(mb), str(w1), str(hedef)], capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not hedef.is_file():
        hedef.unlink(missing_ok=True)
        son = (r.stderr.strip().splitlines() or ["?"])[-1]
        return dict(cift=cift, dosya="", sha256="", durum="FAIL", neden=f"kapi: {son[:200]}")
    with Image.open(hedef) as im:
        bicim, boyut = im.format, im.size
        im.load()
    if bicim != "JPEG" or boyut != (3000, 2250):
        hedef.unlink(missing_ok=True)
        return dict(cift=cift, dosya="", sha256="", durum="FAIL", neden=f"cikti {bicim} {boyut}")
    return dict(cift=cift, dosya=hedef.name, sha256=hashlib.sha256(hedef.read_bytes()).hexdigest(), durum="PASS", neden="")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="W07_MB + W01_KAPAK klasoru")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ciftler", default=str(KOK.parents[2] / "data/pod/pod78_ids.csv"))
    ap.add_argument("--kaynak", default="", help="raporda gosterilecek Drive klasoru")
    a = ap.parse_args(argv)
    ciftler = [r["cift"].strip() for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if (r.get("cift") or "").strip()]
    if len(ciftler) != 78 or len(set(ciftler)) != 78:
        raise SystemExit(f"HATA: cift listesi 78 tekil degil ({len(ciftler)}). DUR.")
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    satir = []
    for n, c in enumerate(ciftler, 1):
        satir.append(tek(src, out, c))
        print(f"[{n}/78] %{100 * n // 78} {c} {satir[-1]['durum']} {satir[-1]['neden']}", flush=True)
    with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "dosya", "sha256", "durum", "neden"])
        w.writeheader(); w.writerows(satir)
    k = pafta([(s["cift"], out / s["dosya"] if s["dosya"] else None) for s in satir], out / "KONTAK_W11_CI.jpg", 320, 10,
              f"W11 Champagne Ivory | 78 cift | {a.kaynak}")
    fail = [s for s in satir if s["durum"] != "PASS"]
    cl = next((s for s in satir if s["cift"] == "CANCER_LIBRA"), {})
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# W11 Champagne Ivory renk karti\n\n{'PASS' if not fail else 'FAIL'} | PASS {78 - len(fail)} / 78 | FAIL {len(fail)}\n"
                f"kaynak: {a.kaynak or a.src}; kontak {k['dosya']} ({k['boyut']}); CANCER_LIBRA sha256 {cl.get('sha256') or '-'}\n\n"
                "## FAIL\n" + ("".join(f"- {s['cift']}: {s['neden']}\n" for s in fail) or "- yok\n"))
    print(f"OZET: PASS {78 - len(fail)}/78 FAIL {len(fail)} | CANCER_LIBRA {cl.get('sha256')}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
