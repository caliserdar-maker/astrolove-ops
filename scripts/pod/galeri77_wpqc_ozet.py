#!/usr/bin/env python3
"""WP_QC_AYRINTI.json (galeri77_wp_sarici) -> basarisiz kapilarin olculen degerleri (tek satir/kapi, loga)."""
import json
import sys

R = json.load(open(sys.argv[1]))
q = R.get('qc') or {}
for k in ('a_renk', 'b_tasma', 'c_iz', 'e_kagit', 'f_kabartma', 'g_kontrast'):
    v = q.get(k) or {}
    if v.get('gecti'):
        continue
    if k == 'g_kontrast':
        print('WPQC g_kontrast yeni', v.get('yeni'), 'onayli', v.get('onayli'))
    else:
        print('WPQC', k, json.dumps({a: b for a, b in v.items() if not isinstance(b, (list, dict)) or a in ('esik', 'hedefe_dE')},
                                    default=str)[:600])
print('WPQC hedef_gecmis', json.dumps(R.get('hedef_gecmis') or (R.get('bakir') or {}).get('hedef_gecmis'), default=str)[:800])
print('WPQC duz_renk', R.get('duz_renk'), json.dumps([{'renk': d.get('renk'), 'kimlik': (d.get('kimlik') or {}).get('kalan'),
                                                       'siparis': (d.get('siparis') or {}).get('kalan')}
                                                      for d in R.get('duz_renk_denemeleri') or []]))
print('WPQC bantlar', json.dumps(R.get('bantlar'), default=str)[:300])
