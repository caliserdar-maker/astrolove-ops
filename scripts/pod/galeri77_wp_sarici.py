#!/usr/bin/env python3
"""WP siparisi (siparis_dosyasi.py, kilitli kod) icin ayni argumanlarla calistirici; piksel degistirmez.
wp_ornek.cift_boy donusundeki QC ayrintisini (f_kabartma, g_kontrast, a-e, hedef gecmisi) <cik>/WP_QC_AYRINTI.json'a
yazar (KAPI_RAPORU yalniz true/false tasiyor; WP_TANI icin ayrinti gerekli). cwd = WP dali kok dizini."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / 'scripts' / 'medya_v1'))
sys.argv[0] = str(Path.cwd() / 'scripts' / 'medya_v1' / 'siparis_dosyasi.py')
import siparis_dosyasi as sd  # noqa: E402
import wp_ornek as wo  # noqa: E402

_cift_boy = wo.cift_boy


def cift_boy(*a, **k):
    R, WP = _cift_boy(*a, **k)
    cik = Path(a[5] if len(a) > 5 else k['cik'])
    try:
        d = {x: v for x, v in R.items() if not x.startswith('_')}
        (cik / 'WP_QC_AYRINTI.json').write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str))
    except Exception as e:  # noqa: BLE001  (ayrinti yazilamazsa uretim etkilenmez)
        print('WP_QC_AYRINTI yazilamadi:', type(e).__name__, e, flush=True)
    return R, WP


wo.cift_boy = cift_boy
sd.main()
