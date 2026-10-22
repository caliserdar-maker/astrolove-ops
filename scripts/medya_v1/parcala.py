#!/usr/bin/env python3
"""medya-v1: Drive dosyalarini 5 MB parcalara bolup Drive'a yazar (24 Eyl 2026).

Claude sandbox'i Drive MCP ile ~6 MB ustu dosyayi indiremiyor; bu betik
kaynak dosyalari DEGISTIRMEDEN kopyalar, tar + split ile parcalar ve
TEMP/POD_KISISEL/AQUARIUS_AQUARIUS_v1/_girdi/parca/ altina yazar.
Yerelde `cat parca_* > paket.tar` ile birlesir; sha256 listesi eklenir.
Etsy/Prodigi erisimi yok. Yalniz Drive okuma + _girdi/parca altina yazma.

Kullanim: parcala.py <drive_file_id> [<drive_file_id> ...]
"""
import hashlib
import subprocess
import sys
import time
from pathlib import Path

DEST = "gdrive:ASTROLOVE/TEMP/POD_KISISEL/AQUARIUS_AQUARIUS_v1/_girdi/parca"
W = Path("_parca")
src = W / "src"
src.mkdir(parents=True, exist_ok=True)
ids = sys.argv[1:]
t0 = time.time()
for i, fid in enumerate(ids, 1):
    subprocess.run(["rclone", "backend", "copyid", "gdrive:", fid, str(src) + "/"], check=True)
    el = time.time() - t0
    print(f"[{i}/{len(ids)}] %{100*i/len(ids):.0f} gecen {el:.0f}s kalan ~{el/i*(len(ids)-i):.0f}s", flush=True)
lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.stat().st_size}  {p.name}"
         for p in sorted(src.iterdir())]
(W / "SHA256_KAYNAK.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
subprocess.run(f"tar -cf {W}/paket.tar -C {src} .", shell=True, check=True)
subprocess.run(f"split -b 5000000 -d -a 3 {W}/paket.tar {W}/parca_", shell=True, check=True)
(W / "paket.tar").unlink()
print(f"parca sayisi: {len(list(W.glob('parca_*')))}")
subprocess.run(["rclone", "copy", str(W), DEST, "--exclude", "src/**", "--transfers", "8"], check=True)
subprocess.run(["rclone", "ls", DEST], check=True)
