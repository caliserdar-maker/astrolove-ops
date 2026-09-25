#!/usr/bin/env python3
"""video'nun 78 cift kartpostal testi (video-v1 scripts/video_v1/kartpostal_test78.py) DEGISTIRILMEDEN kosar;
yalniz iki uyarlama: (1) A1_77'de POSTER_AM olmayan cift (CANCER_LIBRA) icin pod akisinin kaynak sirasi
(siparis_onay.poster_adaylari: POD_PRINT/<cift>/MIDNIGHT_BLUE/8x10.jpg), (2) cikti video'nun dosyalarini ezmesin diye
TEMP/KARTPOSTAL_ORNEK/POD_TEST. Musteri verisi yok (EMILY & JAMES + uzun ornek isimler). Etsy/Prodigi erisimi yok."""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "etsy")); sys.path.insert(0, str(HERE.parent / "pinterest"))
import siparis_onay as O  # noqa: E402

subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "video-v1"], check=True)
kaynak = subprocess.run(["git", "show", "FETCH_HEAD:scripts/video_v1/kartpostal_test78.py"], capture_output=True, text=True, check=True).stdout
kaynak = kaynak.replace("HEDEF = 'gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK'", "HEDEF = 'gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK/POD_TEST'")
assert "KARTPOSTAL_ORNEK/POD_TEST" in kaynak

_run = subprocess.run


def run(cmd, *a, **kw):
    """rclone copyto A1_77/<cift>/POSTER_AM.png basarisizsa pod akisinin sonraki adayi denenir."""
    r = _run(cmd, *a, **kw)
    if (isinstance(cmd, list) and cmd[:2] == ["rclone", "copyto"] and len(cmd) >= 4 and cmd[2].endswith("/POSTER_AM.png")
            and r.returncode != 0):
        cift = cmd[2].rstrip("/").split("/")[-2]
        for aday in O.poster_adaylari(cift)[1:]:
            r2 = _run(["rclone", "copyto", aday, cmd[3]], *a, **kw)
            if r2.returncode == 0:
                print(f"POSTER KAYNAGI {cift}: {aday.split('TEMP/', 1)[-1]}", flush=True)
                return r2
    return r


subprocess.run = run
d = Path(tempfile.mkdtemp(prefix="kt78_"))
(d / "kartpostal_test78.py").write_text(kaynak, encoding="utf-8")
g = {"__name__": "__main__", "__file__": str(d / "kartpostal_test78.py")}
exec(compile(kaynak, str(d / "kartpostal_test78.py"), "exec"), g)
