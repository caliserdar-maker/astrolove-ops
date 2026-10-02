#!/usr/bin/env python3
"""DIKIS SON KONTROL (salt okur; Serdar 2 Eki): dikis-yayin sonucundan secilen (edisyon, boy) icin EN YUKSEK dikis
degerli yayindaki ZIP JPG'sinin tagline bolgesi 1:1 kesiti. Yeniden uretim / yeni olcum YOK: kutu ve deger
DIKIS_<EDISYON>.jsonl satirindan (tag_kutu, dikis) aynen alinir. Kesitin ustune ayri bir etiket seridi eklenir
(cift + edisyon + boy + deger); kesit pikselleri 1:1 kalir.
  --jsonl-kok : DIKIS_*.jsonl klasoru  --secim MIDNIGHT_BLUE:11x14,PURE_WHITE:18x24,...  --cik klasor
"""
import argparse
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def rc(*a):
    return subprocess.run(['rclone', '--tpslimit', '4', '--retries', '5', '--low-level-retries', '20', *a],
                          check=True, capture_output=True, text=True).stdout


def etiketle(kes, metin):
    try:
        f = ImageFont.truetype('DejaVuSans-Bold.ttf', 34)
    except OSError:
        f = ImageFont.load_default()
    out = Image.new('RGB', (kes.width, kes.height + 60), 'white')
    ImageDraw.Draw(out).text((12, 12), metin, fill='black', font=f)
    out.paste(kes, (0, 60))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jsonl-kok', required=True)
    ap.add_argument('--secim', required=True)
    ap.add_argument('--cik', required=True)
    a = ap.parse_args()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for s in a.secim.split(','):
            ed, boy = s.split(':')
            R = [json.loads(x) for x in open(Path(a.jsonl_kok) / f'DIKIS_{ed}.jsonl')]
            R = [r for r in R if r['boy'] == boy and 'dikis' in r]
            m = max(r['dikis'] for r in R)
            esit = sorted(r['urun'] for r in R if r['dikis'] == m)
            r = next(q for q in R if q['urun'] == esit[0])
            zy = tmp / 'z.zip'
            rc('copyto', f"gdrive:ASTROLOVE/{r['zip_yol']}", str(zy))
            with zipfile.ZipFile(zy) as zf:
                ad = next(x for x in zf.namelist() if Path(x).name == r['dosya'])
                j = tmp / r['dosya']; j.write_bytes(zf.read(ad))
            zy.unlink()
            X0, Y0, X1, Y1 = r['tag_kutu']
            with Image.open(j) as im:
                W, H = im.size
                p = int(0.12 * (Y1 - Y0))
                kes = im.convert('RGB').crop((max(X0 - p, 0), max(Y0 - p, 0), min(X1 + p, W), min(Y1 + p, H)))
            cift = r['urun'].replace('AstroLove_', '').rsplit(f"_{'_'.join(w.capitalize() for w in ed.split('_'))}", 1)[0]
            metin = (f"{cift} | {ed} {boy} | dikis {r['dikis']} (ust {r.get('dikis_ust')} / alt {r.get('dikis_alt')} / "
                     f"govde {r.get('dikis_govde')}) | esik 13 | 1:1")
            hedef = cik / f"DIKIS_KESIT_{ed}_{boy}_{cift.upper()}_{r['dikis']}.jpg"
            etiketle(kes, metin).save(hedef, 'JPEG', quality=92)
            print('KESIT', hedef.name, 'boyut', kes.size, 'esit_deger', len(esit), esit[:3], flush=True)
            j.unlink()


if __name__ == '__main__':
    main()
