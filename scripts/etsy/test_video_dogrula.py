#!/usr/bin/env python3
"""video_dogrula icin ffmpeg ile uretilen sentetik video testleri."""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_dogrula import dogrula


FFMPEG_VAR = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
OCR_VAR = importlib.util.find_spec("pytesseract") is not None and shutil.which("tesseract") is not None


class VideoDogrulaTest(unittest.TestCase):
    def setUp(self):
        if not FFMPEG_VAR:
            self.skipTest("ffmpeg/ffprobe yok")
        self.gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def video(self, ad, renk, metin="YENI VIDEO"):
        yol = self.dizin / ad
        filtre = (
            f"color=c={renk}:s=320x240:d=1:r=10,"
            "drawbox=x=35:y=25:w=105:h=115:color=white:t=fill,"
            "drawbox=x=180:y=25:w=105:h=115:color=black:t=fill,"
            f"drawtext=text='{metin}':fontcolor=white:fontsize=25:x=(w-text_w)/2:y=185"
        )
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", filtre,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(yol)],
            check=True,
        )
        return yol

    def test_ayni_video_pass(self):
        video = self.video("ayni.mp4", "blue")
        sonuc = dogrula(video, video)
        self.assertTrue(sonuc["pass"], sonuc)
        self.assertEqual(10, len(sonuc["kare_fark_list"]))

    def test_farkli_cift_fail(self):
        beklenen = self.video("beklenen.mp4", "blue")
        farkli = self.video("farkli.mp4", "red")
        sonuc = dogrula(farkli, beklenen, beklenen)
        self.assertFalse(sonuc["pass"], sonuc)

    @unittest.skipUnless(OCR_VAR, "pytesseract/tesseract yok")
    def test_eski_slogan_fail(self):
        eski = self.video("eski.mp4", "blue", "TWO SOULS")
        sonuc = dogrula(eski, eski)
        self.assertFalse(sonuc["pass"], sonuc)
        self.assertTrue(sonuc["eski_slogan"], sonuc)

    def test_bos_dosya_fail(self):
        bos = self.dizin / "bos.mp4"
        bos.touch()
        sonuc = dogrula(bos, bos)
        self.assertFalse(sonuc["pass"], sonuc)
        self.assertIn("bos", sonuc["neden"])


if __name__ == "__main__":
    unittest.main()
