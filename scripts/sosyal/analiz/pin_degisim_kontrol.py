#!/usr/bin/env python3
"""Pin degisimi sonrasi SALT OKUMA kontrol (20 Eki 2026): ESLEME.csv'deki her uuid Metricool'da su an hangi gorsel ve alt
metinle duruyor. Yalniz GET /v2/scheduler/posts (gun penceresi), yazma yok.
Cikti: KONTROL.csv (uuid, tarih, aile, cift, durum, gorsel_sinifi YENI|ESKI|BASKA|YOK, medya, alt) + KONTROL_OZET.txt.
Kullanim: pin_degisim_kontrol.py MC.json ESLEME.csv URL_KOK CIKTI_DIR"""
import csv, importlib.util, json, os, sys
from collections import Counter
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(D, '..', 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
TZ = 'Europe/Istanbul'


def main():
    tok, esleme, kok, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    mc = mpb.MC(json.load(open(tok)))
    E = list(csv.DictReader(open(esleme, encoding='utf-8')))
    gunler = sorted({r['tarih'][:10] for r in E})
    bas = datetime.fromisoformat(gunler[0]) - timedelta(days=1)
    son = datetime.fromisoformat(gunler[-1]) + timedelta(days=2)
    tum, g = {}, bas
    while g < son:  # 3 gunluk dilimler
        s = min(g + timedelta(days=3), son)
        j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{g:%Y-%m-%dT00:00:00}', 'end': f'{s:%Y-%m-%dT00:00:00}', 'timezone': TZ})
        for p in mpb.veri(j) or []:
            tum.setdefault(str(p.get('uuid')), {})[str(p.get('id'))] = p
        g = s
    satir = []
    for r in E:
        yeni = f"{kok.rstrip('/')}/{'poster' if r['aile'] == 'poster' else 'y1'}/{r['yeni_pin_dosyasi']}"
        ps = list((tum.get(str(r['uuid'])) or {}).values())
        if not ps:
            satir.append(dict(uuid=r['uuid'], tarih=r['tarih'], aile=r['aile'], cift=r['cift'], durum='bulunamadi',
                              gorsel_sinifi='YOK', medya='', alt='')); continue
        p = ps[0]
        m = (p.get('media') or [''])[0]
        sinif = 'YENI' if m == yeni else 'ESKI' if m == r['eski_medya'] else 'BASKA'
        satir.append(dict(uuid=r['uuid'], tarih=r['tarih'], aile=r['aile'], cift=r['cift'], durum=str(mpb.pin_durum(p)),
                          gorsel_sinifi=sinif + ('' if len(ps) == 1 else f'_KOPYA{len(ps)}'), medya=m,
                          alt=(p.get('mediaAltText') or [''])[0]))
    with open(os.path.join(out, 'KONTROL.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0]), lineterminator='\n'); w.writeheader(); w.writerows(satir)
    c = Counter((s['gorsel_sinifi'], s['durum']) for s in satir)
    o = [f'KONTROL {datetime.now():%Y-%m-%d %H:%M} UTC, ESLEME {len(E)} gonderi (salt okuma)']
    o += [f'{k[0]} / {k[1]}: {v}' for k, v in sorted(c.items())]
    open(os.path.join(out, 'KONTROL_OZET.txt'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print('\n'.join(o))


if __name__ == '__main__':
    main()
