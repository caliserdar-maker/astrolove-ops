#!/usr/bin/env python3
"""78 poster ilani baslik + 13 etiket ONCE / SONRA karsilastirmasi (20 Eki 2026, ETSY_ADS_TESPIT). SALT OKUMA, yalniz GET.

ONCE  = Drive TEMP/ETSY_ARAMA_20261010/51_YEDEK_ONCE.json (_ts_utc 2026-10-11 07:31:45; SEO51 yazimindan hemen once)
        capraz: canli/canli_78.csv (10 Eki 08:33 dokumu). 9 Eki ILAN_YEDEK_20261009 kosusu yalniz aciklamayi degistirdi
        (FARK/*.diff), bu yuzden ONCE = 9 Eki oncesi baslik/etiket.
ARA   = 53_GERI_OKUMA_HAM.json (11 Eki 08:15 geri okuma, SEO51 sonrasi).
ZAMAN = 51_YAZIM/rapor/<CIFT>.json Drive degisme zamani (rclone lsjson ModTime, UTC) + 52_YAZIM_RAPORU.csv baslik_ok/etiket_ok.
SONRA = Etsy API bugun: GET /shops/{id} (kota) + GET /listings/batch?listing_ids=78 (1 cagri). Kota tabani 10, cagri siniri 80.
Kelime: kucuk harf, harf/rakam disi ayirici; burc adlari OZET'te <burc> olarak toplanir. Ifade: baslikta virgulle ayrilan parca.
Cikti: OUT/BASLIK_ETIKET_ONCE_SONRA.csv, OUT/OZET.txt, OUT/HAM_SONRA.json
Kullanim: baslik_once_sonra.py --once Y.json --canli C.csv --ham H.json --rapor-ls L.json --yazim R.csv --out OUT
          [--sonra-json S.json  (yerel test; verilmezse Etsy API: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE)]"""
import argparse
import csv
import datetime as dt
import json
import os
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

KOTA_TABAN, CAGRI_SINIRI = 10, 80
YOK = 'erisilemedi'
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
ONCELIK = ['4570114301', '4570143387', '4570113157', '4570160260', '4570143815', '4570224058', '4570204681',
           '4570144239', '4570152820', '4570214304']
IZLE = ('zodiac', 'personalized', 'print', 'astrology', 'custom', 'poster', 'art', 'wall', 'gift', 'couple', 'anniversary',
        'wedding', 'engagement', 'valentine', 'compatibility', 'constellation', 'star', 'sign')


def kel(s):
    return [w for w in re.split(r"[^a-z0-9']+", (s or '').lower()) if w]


def parca(s):
    return [p.strip().lower() for p in (s or '').split(',') if p.strip()]


def etiketler(v):
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v]
    s = str(v or '').strip()
    if s.startswith('['):
        try:
            return [str(x).strip().lower() for x in json.loads(s.replace("'", '"'))]
        except ValueError:
            pass
    return [x.strip().lower() for x in s.split('|') if x.strip()]


def fark_cok(a, b):
    """a'da olup b'de olmayanlar (cok kume)."""
    return list((Counter(a) - Counter(b)).elements())


def genel(w):
    return '<burc>' if w in BURC else w


def iso(t):
    return dt.datetime.fromtimestamp(int(t), dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if t else ''


def sonra_api(ids, out):
    from etsy_common import Etsy, TokenStore, log, mask
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    store = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    api.get(f"/shops/{os.environ['ETSY_SHOP_ID']}")
    kota0 = api.remaining
    log(f'kota basta {kota0} | taban {KOTA_TABAN} | cagri siniri {CAGRI_SINIRI}')
    res = []
    for i in range(0, len(ids), 100):
        if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
            raise SystemExit(f'DUR: kota {api.remaining} < {KOTA_TABAN}')
        if api.calls >= CAGRI_SINIRI:
            raise SystemExit(f'DUR: cagri siniri {CAGRI_SINIRI}')
        res += (api.get('/listings/batch', params={'listing_ids': ','.join(ids[i:i + 100])}) or {}).get('results') or []
    log(f'kota sonda {api.remaining} | cagri {api.calls}')
    meta = {'_ts_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), '_kota_bas': kota0,
            '_kota_son': api.remaining, '_cagri': api.calls}
    json.dump(dict(meta, results=[{k_: x.get(k_) for k_ in ('listing_id', 'state', 'title', 'tags', 'last_modified_timestamp',
                                                           'updated_timestamp', 'state_timestamp')} for x in res]),
              open(out / 'HAM_SONRA.json', 'w'), ensure_ascii=False, indent=1)
    return meta, res


def main():
    ap = argparse.ArgumentParser()
    for k in ('once', 'canli', 'ham', 'rapor-ls', 'yazim', 'out', 'sonra-json'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

    y = json.load(open(a.once))
    once = {str(v['listing_id']): dict(cift=c, title=v['title'], tags=etiketler(v['tags'])) for c, v in y.items() if not c.startswith('_')}
    canli = {r['listing_id']: r for r in csv.DictReader(open(a.canli, encoding='utf-8-sig'))} if os.path.exists(a.canli) else {}
    capraz = sum(1 for i, o in once.items() if i in canli and canli[i]['title'] == o['title']
                 and sorted(etiketler(canli[i]['tags'])) == sorted(o['tags']))
    ham = {str(x['listing_id']): x for x in json.load(open(a.ham))['ilanlar']} if os.path.exists(a.ham) else {}
    zaman = {}
    for f in json.load(open(a.rapor_ls)) if os.path.exists(a.rapor_ls) else []:
        m = re.fullmatch(r'([A-Z]+_[A-Z]+)\.json', f.get('Name', ''))
        if m:
            zaman[m.group(1)] = (f.get('ModTime') or '')[:19].replace('T', ' ')
    yazim = {r['listing_id']: r for r in csv.DictReader(open(a.yazim, encoding='utf-8-sig'))} if os.path.exists(a.yazim) else {}
    ids = sorted(once, key=lambda i: (i not in ONCELIK, ONCELIK.index(i) if i in ONCELIK else 0, once[i]['cift']))

    if a.sonra_json:
        meta, res = {'_ts_utc': 'yerel test', '_cagri': 0}, json.load(open(a.sonra_json))['results']
    else:
        meta, res = sonra_api(ids, out)
    sonra = {str(x['listing_id']): x for x in res}

    satir = []
    T = {k: Counter() for k in ('bk', 'be', 'ek', 'ee', 'bp', 'ep', 'bkg', 'ekg', 'ekel', 'eekel')}
    degisen_b = degisen_e = sonra_ara_fark = 0
    for i in ids:
        o, s, h = once[i], sonra.get(i), ham.get(i)
        st, se = (s.get('title'), etiketler(s.get('tags'))) if s else (None, None)
        if s is None:
            satir.append([ONCELIK.index(i) + 1 if i in ONCELIK else '', i, o['cift'], o['title'], ' | '.join(o['tags']), YOK, YOK]
                         + [YOK] * 8 + [zaman.get(o['cift'], ''), '', '', '', '', '', 'SONRA okunamadi'])
            continue
        bk, be = fark_cok(kel(o['title']), kel(st)), fark_cok(kel(st), kel(o['title']))
        bp, ep = [p for p in parca(o['title']) if p not in parca(st)], [p for p in parca(st) if p not in parca(o['title'])]
        ek, ee = [t for t in o['tags'] if t not in se], [t for t in se if t not in o['tags']]
        ekel, eekel = fark_cok([w for t in o['tags'] for w in kel(t)], [w for t in se for w in kel(t)]), \
            fark_cok([w for t in se for w in kel(t)], [w for t in o['tags'] for w in kel(t)])
        degisen_b += o['title'] != st; degisen_e += sorted(o['tags']) != sorted(se)
        T['bk'].update(set(genel(w) for w in bk)); T['be'].update(set(genel(w) for w in be))
        T['bp'].update(set(re.sub(r'\b(' + '|'.join(BURC) + r')\b', '<burc>', p) for p in bp))
        T['ep'].update(set(re.sub(r'\b(' + '|'.join(BURC) + r')\b', '<burc>', p) for p in ep))
        T['ek'].update(set(re.sub(r'\b(' + '|'.join(BURC) + r')\b', '<burc>', t) for t in ek))
        T['ee'].update(set(re.sub(r'\b(' + '|'.join(BURC) + r')\b', '<burc>', t) for t in ee))
        T['ekel'].update(set(genel(w) for w in ekel)); T['eekel'].update(set(genel(w) for w in eekel))
        T['bkg'].update(w for w in set(genel(x) for x in kel(o['title'])) if w in IZLE)
        T['ekg'].update(w for w in set(genel(x) for x in kel(st)) if w in IZLE)
        ara = ''
        if h:
            ara_ayni = h.get('title') == st and sorted(etiketler(h.get('tags'))) == sorted(se)
            sonra_ara_fark += not ara_ayni
            ara = '11 Eki geri okumayla ayni' if ara_ayni else '11 Eki sonrasi DEGISMIS'
        yz = yazim.get(i, {})
        satir.append([ONCELIK.index(i) + 1 if i in ONCELIK else '', i, o['cift'], o['title'], ' | '.join(o['tags']), st, ' | '.join(se),
                      ' '.join(bk), ' '.join(be), ' ; '.join(bp), ' ; '.join(ep), ' | '.join(ek), ' | '.join(ee),
                      ' '.join(ekel), ' '.join(eekel), zaman.get(o['cift'], YOK),
                      f"baslik_ok={yz.get('baslik_ok', '')} etiket_ok={yz.get('etiket_ok', '')}" if yz else YOK,
                      iso(s.get('last_modified_timestamp')), s.get('state') or '', ara,
                      'ONCE: 51_YEDEK_ONCE.json 2026-10-11 07:31:45 UTC' + (' = canli_78.csv 10 Eki' if i in canli else ''), ''])
    yaz = ['oncelik', 'listing_id', 'cift', 'once_baslik', 'once_etiketler', 'sonra_baslik', 'sonra_etiketler',
           'baslik_kaldirilan_kelime', 'baslik_eklenen_kelime', 'baslik_kaldirilan_ifade', 'baslik_eklenen_ifade',
           'kaldirilan_etiket', 'eklenen_etiket', 'etiketten_kaldirilan_kelime', 'etikete_eklenen_kelime',
           'degisim_zamani_utc_SEO51', 'seo51_yazim_raporu', 'etsy_last_modified_utc', 'sonra_state', 'ara_kontrol', 'kaynak', 'not']
    with open(out / 'BASLIK_ETIKET_ONCE_SONRA.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(yaz); w.writerows(satir)

    n = len(ids); okunan = sum(1 for r in satir if r[5] != YOK)
    zs = sorted(v for v in (zaman.get(once[i]['cift']) for i in ids) if v)
    o_ = [f"SONRA okuma: {meta.get('_ts_utc')} UTC, Etsy GET /listings/batch; cagri {meta.get('_cagri')}, kota {meta.get('_kota_bas')} -> {meta.get('_kota_son')}",
          f"ONCE: 51_YEDEK_ONCE.json (2026-10-11 07:31:45 UTC, SEO51 oncesi); capraz canli_78.csv (10 Eki 08:33) ayni: {capraz}/{n}",
          "9 Eki ILAN_YEDEK_20261009 kosusu yalniz aciklama metnini degistirdi (FARK/*.diff); baslik/etiket degisikligi tek: SEO51",
          f"Degisim: SEO51 seo51_yaz.py mod yaz (commit 6cbf82b9, onay SEO51); ilan yazim zamani (51_YAZIM/rapor) {zs[0] if zs else YOK} - {zs[-1] if zs else YOK} UTC",
          f"Ilan: {n}; SONRA okunan {okunan}; baslik degisen {degisen_b}; etiket kumesi degisen {degisen_e}; 11 Eki geri okumadan sonra yeniden degisen {sonra_ara_fark}",
          '',
          'EN SIK KALDIRILAN BASLIK KELIMELERI (ilan sayisi; <burc> = burc adi):',
          '  ' + ', '.join(f'{k} {v}' for k, v in T['bk'].most_common(20)),
          'EN SIK EKLENEN BASLIK KELIMELERI:', '  ' + ', '.join(f'{k} {v}' for k, v in T['be'].most_common(20)),
          'KALDIRILAN BASLIK IFADELERI (virgul parcasi):', '  ' + ', '.join(f'"{k}" {v}' for k, v in T['bp'].most_common(12)),
          'EKLENEN BASLIK IFADELERI:', '  ' + ', '.join(f'"{k}" {v}' for k, v in T['ep'].most_common(12)),
          'EN SIK KALDIRILAN ETIKETLER:', '  ' + ', '.join(f'"{k}" {v}' for k, v in T['ek'].most_common(25)),
          'EN SIK EKLENEN ETIKETLER:', '  ' + ', '.join(f'"{k}" {v}' for k, v in T['ee'].most_common(25)),
          'ETIKETLERDEN TAMAMEN CIKAN KELIMELER:', '  ' + ', '.join(f'{k} {v}' for k, v in T['ekel'].most_common(20)),
          'ETIKETLERE YENI GIREN KELIMELER:', '  ' + ', '.join(f'{k} {v}' for k, v in T['eekel'].most_common(20)),
          'IZLENEN KELIMELER, BASLIKTA GECEN ILAN SAYISI (ONCE -> SONRA):',
          '  ' + ', '.join(f'{w} {T["bkg"][w]} -> {T["ekg"][w]}' for w in IZLE),
          '', f'ONCELIKLI 10 ILAN:']
    for r in satir[:10]:
        o_ += [f'  {r[0]}. {r[1]} {r[2]} | zaman {r[15]} | {r[19]}', f'     ONCE  baslik: {r[3]}', f'     SONRA baslik: {r[5]}',
               f'     baslik kaldirilan: {r[7] or "-"} | eklenen: {r[8] or "-"}',
               f'     etiket kaldirilan: {r[11] or "-"}', f'     etiket eklenen: {r[12] or "-"}']
    open(out / 'OZET.txt', 'w').write('\n'.join(o_) + '\n')
    print('\n'.join(o_[:22]))


if __name__ == '__main__':
    main()
