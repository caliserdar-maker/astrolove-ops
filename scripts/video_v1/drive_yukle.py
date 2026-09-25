#!/usr/bin/env python3
"""video-v1: depodaki review/video_v1/<ALT> dosyalarini Drive klasorune kopyalar (kisisel-pilot kosucusu, yalniz Drive).
Kullanim: drive_yukle.py <drive_klasor_id> <ALT>   ornek: 1Vn1a05o3_HmHCD4FxduRU_H2COD1Js8b VIDEO_KART3
Etsy/Prodigi erisimi yok."""
import subprocess, sys
from pathlib import Path
fid, alt = sys.argv[1], sys.argv[2]
src = Path(__file__).resolve().parents[2] / 'review/video_v1' / alt
assert src.is_dir() and '..' not in alt, src
dosyalar = sorted(p.name for p in src.iterdir())
for i, f in enumerate(dosyalar, 1):
    subprocess.run(['rclone', 'copy', str(src / f), 'gdrive:', '--drive-root-folder-id', fid], check=True)
    print(f'[{i}/{len(dosyalar)}] %{100*i/len(dosyalar):.0f} {f}', flush=True)
subprocess.run(['rclone', 'lsl', 'gdrive:', '--drive-root-folder-id', fid], check=True)
