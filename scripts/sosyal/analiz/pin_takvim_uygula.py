#!/usr/bin/env python3
"""Pinterest takvim v2 UYGULAMA (PLAN_V2.csv -> Metricool). Mevcut pinlerde YALNIZ publicationDate degisir.
  --mod kuru : SALT OKUMA. Canli okuma (GET /v2/scheduler/posts), uuid ile esleme, siniflama + cagri tahmini -> KURU_UYGULAMA.txt/.csv
  --mod yaz  : METRICOOL'A YAZAR (--confirm PIN_TAKVIM_V2, ayri onay). PUT gonderiye YENI id verir, uuid ayni kalir; bu yuzden her pin
               icin uygulama aninda yeniden canli okuma: GET (mevcut gun, uuid) -> kapi -> PUT (ayni govde, yalniz publicationDate)
               -> GET (yeni gun, uuid) -> fark: yalniz id, publicationDate.dateTime ve metricool_pin_baslik.IZINLI_FARK.
               Ilk FAIL'de DUR. Ilerleme ve sonuc UYGULAMA.csv'ye satir satir yazilir.
Siniflar: DEGISECEK | AYNI | GECMIS (yayinlandi / saati gecmis / yayina < 2 sa: oldugu gibi kalir) | PLAN_SAATI_GECMIS (yeni saat
  uygulama aninda < simdi + 2 sa: yazilmaz, plan yeniden kosulur) | KAYIP (uuid canli listede yok) | YENI_POST (yeni yil donumu +
  kupa: bu script yazmaz; gorsel URL ve pano id gerekir, ayri adim).
Kullanim: pin_takvim_uygula.py TOKEN.json --plan PLAN_V2.csv --mod kuru|yaz --out OUT [--confirm PIN_TAKVIM_V2] [--sahte S.json]"""
import argparse
import copy
import csv
import importlib.util
import json
import os
import time
from collections import Counter
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('v1', os.path.join(D, 'pin_takvim_plan.py'))
v1 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v1)
mpb, IST, TZ = v1.mpb, v1.IST, v1.TZ
ESIK = timedelta(hours=2)
BEKLE = mpb.BEKLE


def zaman(p):
    try:
        return datetime.fromisoformat((p.get('publicationDate') or {}).get('dateTime') or '').replace(tzinfo=IST)
    except ValueError:
        return None


def pencere(mc, bas, son):
    """[bas, son) arasi Pinterest gonderileri, uuid -> gonderi (5 gunluk pencereler)."""
    ps, t = {}, bas
    while t < son:
        e = min(t + timedelta(days=5), son)
        for p in v1.liste(mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}',
                                                                    'timezone': TZ})):
            if mpb.pin_durum(p) is not None and p.get('uuid') is not None:
                ps[str(p['uuid'])] = p
        t = e
    return ps


def gun_oku(mc, g, uuid):
    bas = datetime(g.year, g.month, g.day)
    return pencere(mc, bas, bas + timedelta(days=1)).get(uuid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('--plan', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--mod', required=True, choices=['kuru', 'yaz']); ap.add_argument('--confirm', default='')
    ap.add_argument('--sahte', default=''); ap.add_argument('--simdi', default='')
    a = ap.parse_args()
    if a.mod == 'yaz' and a.confirm != 'PIN_TAKVIM_V2':
        raise SystemExit('HATA: --mod yaz icin --confirm PIN_TAKVIM_V2 gerekir. YAZMA YOK.')
    os.makedirs(a.out, exist_ok=True)
    simdi = datetime.fromisoformat(a.simdi).replace(tzinfo=IST) if a.simdi else datetime.now(IST)
    plan = list(csv.DictReader(open(a.plan, encoding='utf-8')))
    tarihler = [datetime.fromisoformat(r['yeni_tarih']) for r in plan] + \
               [datetime.fromisoformat(r['eski_tarih_saat'][:10]) for r in plan if r['eski_tarih_saat']]
    bas = datetime(simdi.year, simdi.month, simdi.day)
    son = max(tarihler) + timedelta(days=2)
    if a.sahte:
        canli = {k: v for k, v in json.load(open(a.sahte))['ps'].items()}
        mc = None
        okuma_cagri = 0
    else:
        mc = mpb.MC(json.load(open(a.token)))
        canli = pencere(mc, bas, son)
        okuma_cagri = -(-(son - bas).days // 5)
    sinif, satir = Counter(), []
    for r in plan:
        yeni = datetime.fromisoformat(f"{r['yeni_tarih']}T{r['yeni_saat']}:00").replace(tzinfo=IST)
        if not r['uuid']:
            s = 'YENI_POST'
            cur = None
        else:
            p = canli.get(r['uuid'])
            cur = zaman(p) if p else None
            if p is None:
                s = 'KAYIP'
            elif mpb.pin_durum(p) != 'PENDING':
                s = 'GECMIS (yayinlandi)'
            elif cur is None or cur < simdi + ESIK:
                s = 'GECMIS (saati gecmis / yayina < 2 sa)'
            elif cur == yeni:
                s = 'AYNI'
            elif yeni < simdi + ESIK:
                s = 'PLAN_SAATI_GECMIS'
            else:
                s = 'DEGISECEK'
        sinif[s.split(' (')[0]] += 1
        satir.append(dict(r, sinif=s, canli_zaman=cur.strftime('%Y-%m-%d %H:%M') if cur else '', canli_id=(canli.get(r['uuid']) or {}).get('id', '') if r['uuid'] else ''))
    deg = [x for x in satir if x['sinif'] == 'DEGISECEK']
    yaz_cagri = 3 * len(deg)
    k = ['yeni_tarih', 'yeni_saat', 'aile', 'cift', 'uuid', 'canli_id', 'canli_zaman', 'sinif', 'pano', 'link', 'kaynak']
    with open(os.path.join(a.out, 'KURU_UYGULAMA.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(satir)
    o = [f'KURU UYGULAMA: okuma {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul); canli GET /v2/scheduler/posts {bas:%Y-%m-%d} - {son:%Y-%m-%d} '
         f'({okuma_cagri} cagri); Metricool yazma YOK',
         f'Plan satiri {len(plan)}; canli Pinterest gonderisi {len(canli)}',
         f'Sinif: {dict(sinif)}',
         f'Aile x sinif: {dict(Counter((x["aile"], x["sinif"].split(" (")[0]) for x in satir))}',
         f'YAZ modu cagri tahmini: ilk canli okuma {okuma_cagri} + DEGISECEK {len(deg)} x 3 (GET mevcut gun, PUT, GET yeni gun) = '
         f'{okuma_cagri + yaz_cagri} cagri; sure ~{(okuma_cagri + yaz_cagri) * BEKLE / 60:.0f} dk (istek arasi {BEKLE} sn)',
         'YAZ kurallari: --confirm PIN_TAKVIM_V2; her pin uygulama aninda yeniden okunur (PUT yeni id verir, uuid ile bulunur); yalniz '
         'publicationDate degisir; kapi: PENDING, mevcut ve yeni saat >= simdi + 2 sa; geri okuma fark disi alan = FAIL -> DUR.',
         'YENI_POST (yeni yil donumu 12 + kupa 78) bu scriptle yazilmaz: gorsel URL (github.io), pano id ("Zodiac Couple Mugs" '
         'olusturulduktan sonra) gerekir; ayri adim ve onay.',
         '', 'DEGISECEK (ilk 40):']
    for x in deg[:40]:
        o.append(f"  {x['aile']:<9} {x['cift']:<22} uuid {x['uuid']}: {x['canli_zaman']} -> {x['yeni_tarih']} {x['yeni_saat']}")
    for s_ in ('PLAN_SAATI_GECMIS', 'KAYIP', 'GECMIS'):
        L = [x for x in satir if x['sinif'].startswith(s_)]
        if L:
            o.append(f'{s_} ({len(L)}): ' + '; '.join(f"{x['aile']} {x['cift']} {x['uuid']} {x['canli_zaman']}" for x in L[:15]))
    open(os.path.join(a.out, 'KURU_UYGULAMA.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o[:8]))
    if a.mod == 'kuru':
        return

    # --- YAZ (ayri onay) ---
    yol = os.path.join(a.out, 'UYGULAMA.csv')
    kk = ['uuid', 'aile', 'cift', 'eski_id', 'yeni_id', 'once', 'hedef', 'okunan', 'fark', 'sonuc']
    t0 = time.time()
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=kk, lineterminator='\n'); w.writeheader()
        for i, x in enumerate(deg, 1):
            hedef = datetime.fromisoformat(f"{x['yeni_tarih']}T{x['yeni_saat']}:00").replace(tzinfo=IST)
            cur0 = datetime.fromisoformat(x['canli_zaman']).replace(tzinfo=IST)
            sat = dict(uuid=x['uuid'], aile=x['aile'], cift=x['cift'], once=x['canli_zaman'], hedef=f"{x['yeni_tarih']} {x['yeni_saat']}")
            once = gun_oku(mc, cur0.date(), x['uuid'])
            an = datetime.now(IST)
            if once is None or mpb.pin_durum(once) != 'PENDING' or zaman(once) != cur0:
                sat['sonuc'] = 'ATLANDI (canli degisti/yayinlandi)'
            elif cur0 < an + ESIK or hedef < an + ESIK:
                sat['sonuc'] = 'ATLANDI (2 saat kurali)'
            else:
                yeni = copy.deepcopy(once)
                yeni['publicationDate'] = {'dateTime': hedef.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ}
                sat['eski_id'] = once.get('id')
                if mc.istek('PUT', f"/v2/scheduler/posts/{once['id']}", govde=yeni, yok404=True) is mpb.YOK:
                    sat['sonuc'] = 'ATLANDI (PUT 404, yayinlanmis olabilir)'
                else:
                    sonra = gun_oku(mc, hedef.date(), x['uuid'])
                    if sonra is None:
                        sat['sonuc'] = 'FAIL (PUT sonrasi yeni gunde bulunamadi)'
                    else:
                        df = [y for y in mpb.fark(once, sonra) if y not in ('id', 'publicationDate.dateTime') and y not in mpb.IZINLI_FARK
                              and not y.startswith('creationDate')]
                        sat.update(yeni_id=sonra.get('id'), okunan=(sonra.get('publicationDate') or {}).get('dateTime'), fark='|'.join(df))
                        sat['sonuc'] = 'PASS' if zaman(sonra) == hedef and not df else 'FAIL'
            w.writerow(sat); f.flush()
            g = time.time() - t0
            print(f"[{i}/{len(deg)}] {x['aile']} {x['cift']} {sat['sonuc']} | gecen {g / 60:.1f} dk, kalan ~{g / i * (len(deg) - i) / 60:.1f} dk, "
                  f"%{100 * i / len(deg):.0f}", flush=True)
            if sat['sonuc'].startswith('FAIL'):
                raise SystemExit(f"DUR: {x['uuid']} {sat['sonuc']} {sat.get('fark', '')}")


if __name__ == '__main__':
    main()
