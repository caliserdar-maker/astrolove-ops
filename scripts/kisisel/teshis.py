#!/usr/bin/env python3
"""
Teshis + pilot, tek kosu (Mo, 21 Eyl 2026).

Kosu 3 ve 4 hicbir cikti yazmadan 25+ dk asili kaldi; SIGALRM asama siniri ve
job timeout'u da tetiklenmedi. Bu, surecin Python yorumlayicisina donmeyen bir
cagrida kilitlendigini gosterir; en olasi aday zaman siniri olmayan bir rclone
cagirisiydi. Bu script once rclone'u tek tek, sert sinirlarla dener; her adim
zaman damgali loglanir ve TESHIS.txt Drive'a yazilir.

Teshis PASS ise ayni kosuda pilot2 calisir.
"""
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from kisisel_pilot import DEST, FOLDERS, RC_SINIR, rc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
T0 = time.time()
SATIR = []


def log(m):
    s = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s] {m}"
    print(s, flush=True)
    SATIR.append(s)


def yaz_ve_gonder():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TESHIS.txt").write_text("\n".join(SATIR) + "\n", encoding="utf-8")
    try:
        subprocess.run(["rclone", *RC_SINIR, "copy", str(OUT / "TESHIS.txt"), DEST],
                       timeout=120, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        print(f"TESHIS.txt -> {DEST}", flush=True)
    except Exception as e:
        print(f"TESHIS.txt Drive'a yazilamadi: {e}", flush=True)


def adim(ad, fn):
    t = time.time()
    log(f"ADIM BASLADI: {ad}")
    try:
        sonuc = fn()
    except Exception as e:
        log(f"ADIM BASARISIZ: {ad} ({time.time() - t:.1f}s) -> {type(e).__name__}: {e}")
        raise
    log(f"ADIM TAMAM: {ad} ({time.time() - t:.1f}s) {sonuc}")
    return sonuc


def main():
    log(f"teshis basladi | rclone sinirlari: {' '.join(RC_SINIR)} | surec timeout 120s")
    try:
        adim("rclone surum", lambda: subprocess.run(
            ["rclone", "version"], capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL).stdout.splitlines()[0])
        # 1) duz yol (pod-order-router ile ayni adresleme)
        adim("lsf ASTROLOVE/TEMP (duz yol)",
             lambda: f"{len(rc('lsf', 'gdrive:ASTROLOVE/TEMP', '--max-depth', '1').splitlines())} oge")
        # 2) klasor-id adreslemesi: pilot bunu kullaniyor, kosu 3/4'un supheli noktasi
        adim("lsf --drive-root-folder-id (zodiac_names)",
             lambda: rc("lsf", "gdrive:", "--drive-root-folder-id", FOLDERS["names"]).split()[:3])
        # 3) gercek indirme
        def indir():
            d = OUT / "ref" / "names"
            d.mkdir(parents=True, exist_ok=True)
            rc("copy", "gdrive:cancer_name_gold.png", str(d),
               "--drive-root-folder-id", FOLDERS["names"])
            f = d / "cancer_name_gold.png"
            return f"{f.stat().st_size / 1e6:.2f} MB"
        adim("cancer_name_gold.png indir", indir)
        # 4) Drive'a yazma
        adim("Drive'a yaz (TESHIS.txt)", lambda: yaz_ve_gonder() or "yazildi")
    except Exception as e:
        log(f"TESHIS BASARISIZ: {type(e).__name__}: {e}")
        yaz_ve_gonder()
        sys.exit(1)

    log(f"TESHIS PASS ({time.time() - T0:.1f}s) -> pilot2 ayni kosuda basliyor")
    yaz_ve_gonder()
    import pilot2
    sys.argv = ["pilot2", "--asama-sinir", "480"]
    pilot2.main()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
