#!/usr/bin/env python3
"""Pinterest karsilastirma okumasi (19 Eki 2026; ChatGPT PIEV01 serisi ile ayrisma). SALT OKUMA: yalniz GET.
1) /v2/analytics/timelines network=pinterest, metric impression|pin_click|outbound_click|save, subject posts ve account
   (varsayilan subject: 400 yaniti "Metric followers not allowed for subject posts" -> varsayilan posts).
2) Eski uc /stats/timeline/{PIEV01,PIEV05,PIEV06,PIEV07} (start/end YYYYMMDD) ve /stats/aggregations/pinterest.
3) /v2/scheduler/posts 19 - 26 Eki: Pinterest kayitlari, durum, pano kimligi, link ve alt metin dolulugu.
Ham yanitlar HAM_K_*.json; ozet ekrana. Kullanim: pinterest_karsilastir.py TOKEN.json CIKTI_DIR"""
import importlib.util
import json
import os
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(KOK, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
TZ = 'Europe/Istanbul'
BAS, SON = '2026-09-18', '2026-10-19'


def oku(mc, out, ad, yol, params):
    try:
        j = mc.istek('GET', yol, params)
    except SystemExit as e:
        j = {'_hata': str(e)[:300]}
    json.dump(j, open(os.path.join(out, f'HAM_K_{ad}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
    print(f'{ad}: {json.dumps(j, ensure_ascii=False, default=str)[:400]}')
    return j


def main():
    tok, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    for subj in ('posts', 'account'):
        for m in ('impression', 'pin_click', 'outbound_click', 'save'):
            oku(mc, out, f'timeline_{subj}_{m}', '/v2/analytics/timelines', {'network': 'pinterest', 'metric': m, 'subject': subj,
                'from': f'{BAS}T00:00:00', 'to': f'{SON}T23:59:59', 'timezone': TZ})
    for m in ('PIEV01', 'PIEV05', 'PIEV06', 'PIEV07'):
        oku(mc, out, f'stats_timeline_{m}', f'/stats/timeline/{m}', {'start': BAS.replace('-', ''), 'end': SON.replace('-', ''),
                                                                      'timezone': TZ})
    oku(mc, out, 'stats_aggregations_pinterest', '/stats/aggregations/pinterest',
        {'start': BAS.replace('-', ''), 'end': SON.replace('-', ''), 'timezone': TZ})
    j = oku(mc, out, 'scheduler_20261019_26', '/v2/scheduler/posts', {'start': '2026-10-19T00:00:00', 'end': '2026-10-26T00:00:00',
                                                                       'timezone': TZ})
    ps = [p for p in (mpb.veri(j) or []) if isinstance(p, dict) and mpb.pin_durum(p) is not None] if isinstance(mpb.veri(j), list) else []
    ps = [p for p in ps if (p.get('publicationDate') or {}).get('dateTime', '')[:10] <= '2026-10-25']
    pd = [p.get('pinterestData') or {} for p in ps]
    print(f'TAKVIM 19-25 Eki Pinterest: {len(ps)}; durum {dict(Counter(mpb.pin_durum(p) for p in ps))}; '
          f'pano {dict(Counter(str(x.get("boardId")) for x in pd))}; link dolu {sum(1 for x in pd if x.get("pinLink"))}; '
          f'alt metin dolu {sum(1 for p in ps if any(p.get("mediaAltText") or []))}')


if __name__ == '__main__':
    main()
