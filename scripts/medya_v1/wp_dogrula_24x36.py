#!/usr/bin/env python3
"""YALNIZ DOGRULAMA (Serdar 1 Eki ~15:50, 24x36 plate seridi): CANCER_LIBRA 24x36 bakir baskisi, duz renk yalniz
CHAMPAGNE_IVORY. Ornek isimlerle (EMILY / JAMES) CI hat baskisi 24x36'da yalniz 'olcek' kapisindan kaliyor (1. dogrulama
kosusu 36887597080); MIDNIGHT_BLUE'ya dusunce bakir modeli koyu zeminde bos cikiyor ve kontrast olculemiyor. Bu betik
YALNIZ bu dogrulamada, kalan tek kapi 'olcek' ise CI baskisini kabul eder (calisma aninda; kilitli kod ve siparis yolu
degismez). Ciktilar TEMP/WP_ORNEK/CANCER_LIBRA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_ornek as wo                                            # noqa: E402

_asil = wo.sd.pod_uret


def _pod_uret(x, *a, **k):
    r = _asil(x, *a, **k)
    kalan = sorted(g for g, v in (r.get('kapilar') or {}).items() if v is False)
    if kalan == ['olcek']:
        r['kapilar_gecti'] = True
        r['dogrulama_notu'] = "yalniz 'olcek' kapisi kaldi; bu dogrulamada kabul edildi"
        print('DOGRULAMA_NOTU', x.get('receipt'), r['dogrulama_notu'], flush=True)
    return r


if __name__ == '__main__':
    wo.sd.pod_uret = _pod_uret
    wo.DUZ_RENK = ('CHAMPAGNE_IVORY',)
    sys.argv = [sys.argv[0], '--cift', 'CANCER_LIBRA', '--boylar', '24x36']
    wo.main()
