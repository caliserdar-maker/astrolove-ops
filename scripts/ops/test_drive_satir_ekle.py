#!/usr/bin/env python3
"""drive-satir-ekle.yml yerel testi: is akisinin 'Satir ekle' adimi YAML'dan alinir, bash ile sahte rclone uzerinde kosar.
Gercek Drive yok. Senaryolar: varsayilan hedef TEMP/OTURUM_NOTLARI.md, YAYIN_DURUM.md hedefinin reddi (yazim olmadan),
OTURUM_NOTLARI.md ilk kayit (Drive'da yok), ikinci ekleme (onceki satir korunur, yedek YEDEK/ altinda)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WF = yaml.safe_load((ROOT / ".github/workflows/drive-satir-ekle.yml").read_text(encoding="utf-8"))
ADIM = next(s for s in WF["jobs"]["ekle"]["steps"] if s.get("name") == "Satir ekle")


class DriveSatirEkleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = Path(self.tmp.name)
        self.kok = t / "drive"; (self.kok / "ASTROLOVE/TEMP").mkdir(parents=True)
        self.is_ = t / "is"; self.is_.mkdir(); (self.is_ / "scripts").symlink_to(ROOT / "scripts")

    def tearDown(self):
        self.tmp.cleanup()

    def kos(self, dosya, satir):
        env = dict(os.environ, DOSYA=dosya, SATIR=satir, FAKE_ROOT=str(self.kok), FAKE_HATA="",
                   FAKE_ANA=Path(dosya).name, RCLONE=f"{sys.executable} {ROOT / 'scripts/ops/sahte_rclone.py'}")
        for f in ("_d.md",):
            (self.is_ / f).unlink(missing_ok=True)
        subprocess.run(["rm", "-rf", str(self.is_ / "_durum_md")])
        r = subprocess.run(["bash", "-c", ADIM["run"]], cwd=self.is_, env=env, capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout + r.stderr

    def test_1_varsayilan_hedef(self):
        g = WF[True]["workflow_dispatch"]["inputs"]["dosya"] if True in WF else WF["on"]["workflow_dispatch"]["inputs"]["dosya"]
        self.assertEqual(g["default"], "TEMP/OTURUM_NOTLARI.md")

    def test_2_yayin_durum_reddi(self):
        p = self.kok / "ASTROLOVE/TEMP/YAYIN_DURUM.md"; p.write_text("# Yayin\n- 2026-10-26 tablo\n")
        for hedef in ("TEMP/YAYIN_DURUM.md", "TEMP//YAYIN_DURUM.md", "TEMP/./YAYIN_DURUM.md"):
            rc, log = self.kos(hedef, "- not")
            self.assertNotEqual(rc, 0, hedef); self.assertIn("yayin-durum her gun bu dosyayi yeniden uretir", log)
        self.assertEqual(p.read_text(), "# Yayin\n- 2026-10-26 tablo\n")
        self.assertFalse((self.kok / "ASTROLOVE/TEMP/YEDEK").exists())

    def test_3_ilk_kayit_ve_ikinci_ekleme(self):
        p = self.kok / "ASTROLOVE/TEMP/OTURUM_NOTLARI.md"
        rc, log = self.kos("TEMP/OTURUM_NOTLARI.md", "- 26 Eki birinci not")
        self.assertEqual(rc, 0, log); self.assertIn("ilk kayit", log)
        self.assertEqual(p.read_text(), "- 26 Eki birinci not\n")
        rc, log = self.kos("TEMP/OTURUM_NOTLARI.md", "- 26 Eki ikinci not")
        self.assertEqual(rc, 0, log)
        self.assertEqual(p.read_text(), "- 26 Eki birinci not\n- 26 Eki ikinci not\n")
        y = list((self.kok / "ASTROLOVE/TEMP/YEDEK").glob("OTURUM_NOTLARI_*.md"))
        self.assertEqual(len(y), 1); self.assertEqual(y[0].read_text(), "- 26 Eki birinci not\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
