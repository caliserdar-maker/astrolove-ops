"""Aggregate per-video QC (*-qc.json) into QC.csv / QC.json / FAIL.txt and build KONTAK_9s.jpg from *-kare_9s.jpg.

Usage: python3 kontak.py <dir> [--beklenen 78]
"""
import argparse, csv, glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--beklenen', type=int, default=78); g = ap.parse_args()
rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(g.dir, '*-qc.json')))]
cols = ['cift', 'sonuc', 'q_poster', 'q_video', 'q_son', 'codec', 'w', 'h', 'fps', 'kare', 'sure', 'son_oran', 'bos_oran', 'kamera_orani', 'mb', 'uretim_sn', 'dosya', 'hata']
with open(os.path.join(g.dir, 'QC.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, cols, extrasaction='ignore'); w.writeheader(); [w.writerow(r) for r in rs]
json.dump(rs, open(os.path.join(g.dir, 'QC.json'), 'w'), indent=1)
fails = [r['cift'] for r in rs if r.get('sonuc') != 'PASS']
open(os.path.join(g.dir, 'FAIL.txt'), 'w').write('\n'.join(fails) + ('\n' if fails else ''))

tw, th, cols_n, lh = 240, 427, 13, 30
try:
    font = ImageFont.truetype(os.path.join(HERE, '..', 'pin_v6', 'assets', 'EBGaramond-Regular.ttf'), 20)
except Exception:
    font = ImageFont.load_default()
ims = sorted(glob.glob(os.path.join(g.dir, '*-kare_9s.jpg')))
rows = (len(ims) + cols_n - 1) // cols_n
sheet = Image.new('RGB', (cols_n * (tw + 8) + 8, max(1, rows) * (th + lh + 8) + 60), (245, 243, 238))
d = ImageDraw.Draw(sheet); d.text((12, 16), f'video v9, 9 s frame, {len(ims)} videos', fill=(18, 24, 52), font=font)
for i, p in enumerate(ims):
    im = Image.open(p).convert('RGB').resize((tw, th), Image.LANCZOS)
    x = 8 + (i % cols_n) * (tw + 8); y = 60 + (i // cols_n) * (th + lh + 8)
    sheet.paste(im, (x, y)); d.text((x + 2, y + th + 4), os.path.basename(p).replace('-kare_9s.jpg', ''), fill=(18, 24, 52), font=font)
sheet.save(os.path.join(g.dir, 'KONTAK_9s.jpg'), quality=88)
ok = len(rs) == g.beklenen and not fails and len(ims) == g.beklenen
print(f'OZET QC {len(rs) - len(fails)}/{len(rs)} PASS, beklenen {g.beklenen}, kontak {len(ims)} kare: {"PASS" if ok else "FAIL"}'
      + (f' FAIL: {",".join(fails)}' if fails else ''))
sys.exit(0 if ok else 1)
