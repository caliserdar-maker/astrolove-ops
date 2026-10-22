"""Compare generated Gemini & Leo pins with onayli/ (mean absolute difference, 0-255 levels). PASS if every mean < 2.

Usage: python3 dogrula.py <dir with gemini-and-leo-zodiac-wall-art-astroloveart-p1/p2/p3.jpg>
"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ONAY = {'p1': 'PIN_P1_urun_NIHAI.jpg', 'p2': 'PIN_P2_cevap_NIHAI.jpg', 'p3': 'PIN_P3_isimli_NIHAI.jpg'}


def main(d):
    res = {}
    for k, f in ONAY.items():
        a = np.asarray(Image.open(os.path.join(HERE, 'onayli', f)).convert('RGB')).astype(np.int16)
        b = np.asarray(Image.open(os.path.join(d, f'gemini-and-leo-zodiac-wall-art-astroloveart-{k}.jpg')).convert('RGB')).astype(np.int16)
        if a.shape != b.shape:
            res[k] = {'ortalama': None, 'olcu': [a.shape, b.shape]}
            continue
        df = np.abs(a - b)
        res[k] = {'ortalama': round(float(df.mean()), 3), 'p99': int(np.percentile(df, 99)), 'max': int(df.max())}
    ok = all(v['ortalama'] is not None and v['ortalama'] < 2 for v in res.values())
    res['PASS'] = ok
    print('DOGRULAMA ' + json.dumps(res))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
