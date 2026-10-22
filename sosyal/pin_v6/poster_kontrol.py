"""Poster source gate for the pin run (PASS/FAIL per poster) + one contact sheet.

Usage: python3 poster_kontrol.py <dir with PAIR.jpg> <out_dir>
Per poster: size 2000x3000, background navy (Midnight Blue: blue clearly above red in the whole-poster median),
names row OCR (tesseract) does not contain SERDAR or LENA. Writes POSTER_KONTROL.csv, POSTER_KONTAK.jpg.
"""
import csv, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pin_uret as PU

YASAK = ('SERDAR', 'LENA')


def ocr(im):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        im.save(f.name)
        r = subprocess.run(['tesseract', f.name, '-', '--psm', '7'], capture_output=True, text=True)
    return ' '.join(r.stdout.split())


def main(src, out):
    os.makedirs(out, exist_ok=True)
    rows, thumbs = [], []
    files = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
    for f in files:
        key = f[:-4]; p = os.path.join(src, f)
        im = Image.open(p).convert('RGB'); a = np.asarray(im)
        bg = np.median(a[::4, ::4].reshape(-1, 3), 0)  # whole-poster median = background (gold is a small share)
        rec = {'cift': key, 'olcu': f'{im.size[0]}x{im.size[1]}', 'bg_rgb': ' '.join(str(int(v)) for v in bg)}
        rec['q_olcu'] = im.size == (2000, 3000)
        rec['q_lacivert'] = bool(bg[2] > bg[0] + 8 and bg[2] > 1.5 * bg[0] + 3 and bg.max() < 120)
        try:
            P = PU.PosterR(p)
            _, x, y, w, h, _ = P.names_row
            crop = im.crop((max(0, x - 20), max(0, y - 20), x + w + 20, y + h + 20)).convert('L')
            crop = Image.eval(crop, lambda v: 255 - v)  # dark text on light for tesseract
            rec['isimler_ocr'] = ocr(crop)
        except Exception as e:
            rec['isimler_ocr'] = f'HATA {type(e).__name__}: {e}'
        up = rec['isimler_ocr'].upper()
        words = set(re.findall(r'[A-Z]+', up))  # whole words: ELENA / SELENA are not LENA
        rec['q_ornek_isim'] = not (words & set(YASAK)) and not up.startswith('HATA')
        rec['PASS'] = rec['q_olcu'] and rec['q_lacivert'] and rec['q_ornek_isim']
        rows.append(rec)
        t = im.copy(); t.thumbnail((200, 300)); thumbs.append((t, key))
        print(key, 'PASS' if rec['PASS'] else 'FAIL', rec['bg_rgb'], rec['isimler_ocr'], flush=True)
    with open(os.path.join(out, 'POSTER_KONTROL.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    cols = 13; tw, th = 200, 300; lh = 22
    nrow = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 6) + 6, nrow * (th + lh + 6) + 6), (245, 243, 238)); d = ImageDraw.Draw(sheet)
    for i, (t, key) in enumerate(thumbs):
        x = 6 + (i % cols) * (tw + 6); y = 6 + (i // cols) * (th + lh + 6)
        d.text((x, y + 4), key, fill=(18, 24, 52)); sheet.paste(t, (x, y + lh))
    sheet.save(os.path.join(out, 'POSTER_KONTAK.jpg'), quality=85)
    nf = [r['cift'] for r in rows if not r['PASS']]
    print(f'OZET POSTER {len(rows) - len(nf)}/{len(rows)} PASS; FAIL: {" ".join(nf) or "yok"}')
    return 0 if not nf and len(rows) == 78 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
