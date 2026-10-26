#!/usr/bin/env python3
"""galeri-v10-yukle.yml durum adimlari yerel testi: 'Durum dosyalari oku' ve 'Token + durum dosyalari + cikti Drive'a' adimlari
YAML'dan alinir, bash ile sahte rclone (scripts/ops/sahte_rclone.py + 'copy' icin cp) uzerinde kosar. Gercek Drive yok.
Senaryolar: ilk kayit (3 dosya yazilir), ikinci yazim (yedek YEDEK/ altinda, eski kayit korunur), kayit silinirse FAIL (Drive degismez),
devam_kosu birlestirme (adimi buyuk olan alinir), kuru kosuda yazma yok, okuma hatasi FAIL."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[2]
WF = yaml.safe_load((KOK / ".github/workflows/galeri-v10-yukle.yml").read_text(encoding="utf-8"))
ADIM = {s.get("name"): s for s in WF["jobs"]["is"]["steps"]}
OKU, YAZ = "Durum dosyalari oku (kilit sonrasi)", "Token + durum dosyalari + cikti Drive'a"
SONUC = []


def kontrol(ad, ok):
    SONUC.append(bool(ok)); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def main():
    t = Path(tempfile.mkdtemp(prefix="gv10wf_")); b = t / "bin"; b.mkdir(); d = t / "drive"; is_ = t / "is"; is_.mkdir()
    (is_ / "scripts").symlink_to(KOK / "scripts")
    r = b / "rclone"
    r.write_text("#!/bin/bash\nif [ \"$1\" = copy ]; then s=\"${2#gdrive:}\"; h=\"${3#gdrive:}\"; [[ \"$2\" == gdrive:* ]] && s=\"$FAKE_ROOT/$s\"; "
                 "[[ \"$3\" == gdrive:* ]] && h=\"$FAKE_ROOT/$h\"; mkdir -p \"$h\"; cp -r \"$s\"/. \"$h\"/ 2>/dev/null; exit 0; fi\n"
                 f"exec {sys.executable} {KOK / 'scripts/ops/sahte_rclone.py'} \"$@\"\n")
    r.chmod(0o755)
    U = d / "ASTROLOVE/TEMP/POSTER_GALERI_V10_YUKLE"; U.mkdir(parents=True)
    env = dict(os.environ, PATH=f"{b}:{os.environ['PATH']}", FAKE_ROOT=str(d), FAKE_HATA="", FAKE_ANA="x", RCLONE=str(r),
               O="gdrive:ASTROLOVE/TEMP/POSTER_GALERI_V10_YUKLE", T="gdrive:ASTROLOVE/TEMP", GITHUB_RUN_ID="555",
               GITHUB_ENV=str(t / "genv"), GITHUB_STEP_SUMMARY=str(t / "sum"), DK="")

    def kos(ad, **e):
        (is_ / "_work").mkdir(exist_ok=True); (is_ / "_out").mkdir(exist_ok=True)   # onceki adim (Girdiler) olusturur
        p = subprocess.run(["bash", "-e", "-c", ADIM[ad]["run"]], cwd=is_, env=dict(env, **e), capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def temizle():
        for x in ("_work", "_out"):
            shutil.rmtree(is_ / x, ignore_errors=True)

    def jyaz(ad, f):
        p = is_ / "_work" / ad; j = json.loads(p.read_text()); f(j); p.write_text(json.dumps(j))

    rc, log = kos(OKU)
    kontrol("ilk okuma: 3 dosya yok, ilk kayit izniyle bos baslar", rc == 0 and log.count("ilk kayit") == 3)
    jyaz("DEVAM.json", lambda j: j["ilanlar"].update({"1": dict(cift="A_B", durum="PASS", adim=30)}))
    jyaz("ILERLEME.json", lambda j: j["ilanlar"].update({"1": dict(cift="A_B", set=9, durum="PASS")}))
    (is_ / "_work/SONUC.csv").write_text("ilan,cift,durum\n1,A_B,PASS\n")
    rc, log = kos(YAZ, KURU="false", KOD="0")
    kontrol("yazim kosusu: DEVAM / ILERLEME / SONUC ilk kayit yazildi", rc == 0 and sorted(x.name for x in U.iterdir())
            == ["DEVAM.json", "ILERLEME.json", "KOSU", "SONUC.csv"])
    temizle(); kos(OKU)
    jyaz("DEVAM.json", lambda j: j["ilanlar"].update({"2": dict(cift="C_D", durum="DUR", adim=3)}))
    rc, log = kos(YAZ, KURU="false", KOD="0")
    kontrol("ikinci yazim: eski kayit korunur, yedek YEDEK/ altinda", rc == 0 and list(json.loads((U / "DEVAM.json").read_text())["ilanlar"])
            == ["1", "2"] and len(list((U / "YEDEK").glob("DEVAM_*.json"))) == 1)
    temizle(); kos(OKU)
    jyaz("DEVAM.json", lambda j: j.update(ilanlar={}))
    once = (U / "DEVAM.json").read_bytes()
    rc, log = kos(YAZ, KURU="false", KOD="0")
    kontrol("kayitlar silinirse FAIL, Drive degismez", rc == 1 and "korunmadi" in log and (U / "DEVAM.json").read_bytes() == once)
    (U / "KOSU/444/devam").mkdir(parents=True)
    (U / "KOSU/444/devam/DEVAM_2.json").write_text(json.dumps(dict(adim=9))); (U / "KOSU/444/devam/DEVAM_1.json").write_text(json.dumps(dict(adim=1)))
    temizle(); rc, log = kos(OKU, DK="444")
    ad = {k: v.get("adim") for k, v in json.loads((is_ / "_work/DEVAM.json").read_text())["ilanlar"].items()}
    kontrol("devam_kosu: adimi buyuk kopya alinir (2: 3 -> 9), kucuk alinmaz (1: 30 kalir)", rc == 0 and ad == {"1": 30, "2": 9})
    once = {x.name: x.read_bytes() for x in U.iterdir() if x.is_file()}
    (is_ / "_work/SONUC.csv").write_text("ilan,cift,durum\n")
    rc, log = kos(YAZ, KURU="true", KOD="0")
    kontrol("kuru kosu: durum dosyalarina yazma yok", rc == 0 and once == {x.name: x.read_bytes() for x in U.iterdir() if x.is_file()})
    temizle(); rc, log = kos(OKU, FAKE_HATA="lsjson")
    kontrol("okuma hatasi: FAIL (bos varsayilanla devam yok)", rc != 0 and "listeleme hatasi" in log)
    shutil.rmtree(t, ignore_errors=True)
    print(f"galeri-v10-yukle durum adimlari: {sum(SONUC)}/{len(SONUC)} PASS")
    return 0 if all(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
