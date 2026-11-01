#!/usr/bin/env python3
"""yd-kapak-yukle 'Geri alma hazirligi Drive'a (6a)' adimi testi (bagimsiz inceleme 1 Kas madde 11). Drive yok: sahte rclone
(gdrive:ASTROLOVE/TEMP -> yerel klasor; copyto / copy, --ignore-existing). Adimin bash'i YAML'dan aynen kosulur.
D1 HAZIR ilan: yeni HAM yazilir, eski HAM HAM_ONCEKI'ye; yeni yedek adlari eklenir, mevcut yedek dosyasina dokunulmaz
D2 yeniden deneme (ayni RUN_ID): HAM_ONCEKI ilk (gercek eski) HAM olarak kalir, ezilmez
D3 BLOK ilan: HAM degismez, KAYNAK_YAMA'ya satiri yazilmaz; HAZIR ilanin satiri eski yama satirlariyla birlesir
D4 kuru kosuda adim hicbir sey yazmaz
Calistir: python3 scripts/kapak78/test_yd_geri_drive.py"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[2]
sonuc = []
RCLONE = r'''#!/usr/bin/env python3
import os, shutil, sys
from pathlib import Path
kok = Path(os.environ["SAHTE_DRIVE"])
def yol(x):
    return kok / x.split("gdrive:ASTROLOVE/TEMP/", 1)[1] if x.startswith("gdrive:") else Path(x)
a = [x for x in sys.argv[1:] if x != "-q"]
ign = "--ignore-existing" in a; a = [x for x in a if x != "--ignore-existing"]
k, src, dst = a[0], yol(a[1]), yol(a[2])
if not src.exists():
    sys.exit(3)
if k == "copyto":
    if ign and dst.exists():
        sys.exit(0)
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
elif k == "copy":
    for f in src.rglob("*"):
        if f.is_file():
            t = dst / f.relative_to(src)
            if ign and t.exists():
                continue
            t.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, t)
'''


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def adim():
    w = yaml.safe_load((KOK / ".github/workflows/yd-kapak-yukle.yml").read_text())
    st = w["jobs"][next(iter(w["jobs"]))]["steps"]
    return next(x for x in st if (x.get("name") or "").startswith("Geri alma hazirligi"))["run"]


def kos(t, kuru="false", run="777"):
    env = dict(os.environ, PATH=f"{t / 'bin'}:{os.environ['PATH']}", SAHTE_DRIVE=str(t / "drive"), T="gdrive:ASTROLOVE/TEMP", YD="Y1",
               EN="ENV1", KURU=kuru, GITHUB_RUN_ID=run)
    return subprocess.run(["bash", "-c", adim()], cwd=t / "is", env=env, capture_output=True, text=True, timeout=60)


def main():
    t = Path(tempfile.mkdtemp(prefix="ydgd_"))
    try:
        (t / "bin").mkdir(); (t / "bin" / "rclone").write_text(RCLONE); (t / "bin" / "rclone").chmod(0o755)
        dr = t / "drive"; (dr / "ENV1/HAM").mkdir(parents=True); (dr / "YD_KAPAK_V1_YEDEK/Y1/1_A_A").mkdir(parents=True)
        (dr / "ENV1/HAM/1.json").write_text('{"eski": 1}'); (dr / "ENV1/HAM/2.json").write_text('{"eski": 2}')
        (dr / "YD_KAPAK_V1_YEDEK/Y1/1_A_A/r1_10.jpg").write_text("ESKI"); (dr / "YD_KAPAK_V1_YEDEK/Y1/KAYNAK_YAMA.csv").write_text("listing_id,kaynak_image_id\n9,99\n")
        g = t / "is/_out/GERI_HAZIRLIK"; (g / "HAM").mkdir(parents=True); (g / "YEDEK/1_A_A").mkdir(parents=True); (t / "is/_work").mkdir()
        shutil.copyfile(dr / "YD_KAPAK_V1_YEDEK/Y1/KAYNAK_YAMA.csv", t / "is/_work/KAYNAK_YAMA.csv")
        (g / "HAM/1.json").write_text('{"yeni": 1}'); (g / "HAM/2.json").write_text('{"yeni": 2}')
        (g / "YEDEK/1_A_A/r2_20.jpg").write_text("YENI"); (g / "YEDEK/1_A_A/r1_10.jpg").write_text("DEGISMIS")
        (g / "1.json").write_text(json.dumps({"durum": "HAZIR"})); (g / "2.json").write_text(json.dumps({"durum": "BLOK"}))
        (g / "KAYNAK_YAMA.csv").write_text("listing_id,kaynak_image_id\n1,111\n2,222\n")
        p = kos(t)
        k(f"D1 HAZIR ilan: yeni HAM, eski HAM_ONCEKI'de; yeni yedek adi eklendi, mevcut yedek dosyasi degismedi (rc {p.returncode})",
          p.returncode == 0 and (dr / "ENV1/HAM/1.json").read_text() == '{"yeni": 1}' and (dr / "ENV1/HAM_ONCEKI/1_777.json").read_text() == '{"eski": 1}'
          and (dr / "YD_KAPAK_V1_YEDEK/Y1/1_A_A/r2_20.jpg").read_text() == "YENI" and (dr / "YD_KAPAK_V1_YEDEK/Y1/1_A_A/r1_10.jpg").read_text() == "ESKI", p.stderr[-300:])
        p = kos(t)
        k("D2 yeniden deneme (ayni RUN_ID): HAM_ONCEKI ilk eski HAM olarak kalir (yeni HAM ile ezilmez)",
          p.returncode == 0 and (dr / "ENV1/HAM_ONCEKI/1_777.json").read_text() == '{"eski": 1}')
        ky = (dr / "YD_KAPAK_V1_YEDEK/Y1/KAYNAK_YAMA.csv").read_text().splitlines()
        k(f"D3 BLOK ilan: HAM degismedi, yama satiri yok; HAZIR satiri eski yamayla birlesti ({ky})",
          (dr / "ENV1/HAM/2.json").read_text() == '{"eski": 2}' and not (dr / "ENV1/HAM_ONCEKI/2_777.json").exists()
          and ky == ["listing_id,kaynak_image_id", "1,111", "9,99"] and "2 geri hazirlik BLOK" in p.stdout + p.stderr)
        (dr / "ENV1/HAM/1.json").write_text('{"eski": 1}')
        p = kos(t, kuru="true", run="778")
        k("D4 kuru kosu: adim hicbir sey yazmaz", p.returncode == 0 and (dr / "ENV1/HAM/1.json").read_text() == '{"eski": 1}'
          and not (dr / "ENV1/HAM_ONCEKI/1_778.json").exists())
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
