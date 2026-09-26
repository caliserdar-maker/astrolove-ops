#!/usr/bin/env python3
"""kisisel-pilot kosucusu icin (yalniz Drive, Etsy YOK): 78 video QC (video GOREV 0012).
Indirir: A1_77/<CIFT>/{VIDEO.mp4, POSTER_EJ|IN|AM.png} + CL v5 (Drive id), bagimliliklar (tesseract, scipy, pytesseract,
imageio-ffmpeg); qc_video78.py kosar; cikti Drive TEMP/VIDEO_QC_78/ (pano disi)."""
import os, subprocess, sys
from pathlib import Path

A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
CL_ID = '1D9vk_HGotgzrRWWfEmIcBLSPkxvNkVX6'            # YENI_AstroLove_CANCER_LIBRA_12.6s_v5.mp4 (onayli)
HEDEF = 'gdrive:ASTROLOVE/TEMP/VIDEO_QC_78'
W = Path('_qc78'); W.mkdir(exist_ok=True)


def sh(*a, **k):
    print('+', ' '.join(a[:4]), flush=True); return subprocess.run(a, check=True, **k)


sh('sudo', 'apt-get', 'install', '-y', '-qq', 'tesseract-ocr', stdout=subprocess.DEVNULL)
sh(sys.executable, '-m', 'pip', 'install', '-q', 'scipy', 'pytesseract', 'imageio-ffmpeg')
import imageio_ffmpeg  # noqa: E402
os.environ['FFMPEG'] = imageio_ffmpeg.get_ffmpeg_exe()
sh('rclone', 'copy', A77, str(W / 'A1_77'), '--include', '*/VIDEO.mp4', '--include', '*/POSTER_EJ.png',
   '--include', '*/POSTER_IN.png', '--include', '*/POSTER_AM.png', '--transfers', '8', '-q')
sh('rclone', 'backend', 'copyid', 'gdrive:', CL_ID, str(W / 'cl') + '/')
cl = next((W / 'cl').glob('*.mp4'))
print('cift:', len([p for p in (W / 'A1_77').iterdir() if (p / 'VIDEO.mp4').exists()]), 'CL:', cl.name, flush=True)
here = Path(__file__).resolve().parent
sh(sys.executable, str(here / 'qc_video78.py'), '--a1', str(W / 'A1_77'), '--cl', str(cl), '--ref', str(here / 'ref'),
   '--out', str(W / 'out'))
sh('rclone', 'copy', str(W / 'out'), HEDEF, '-q')
sh('rclone', 'lsl', HEDEF, '--max-depth', '1')
