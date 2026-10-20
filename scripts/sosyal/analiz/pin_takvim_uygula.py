#!/usr/bin/env python3
"""Pinterest takvim v2 UYGULAMA (PLAN_V2.csv -> Metricool). Mevcut pinlerde YALNIZ publicationDate degisir.
  --mod kuru : SALT OKUMA. Canli okuma (GET /v2/scheduler/posts), uuid ile esleme, siniflama + cagri tahmini -> KURU_UYGULAMA.txt/.csv
  --mod yaz  : METRICOOL'A YAZAR (--confirm PIN_TAKVIM_V2, Serdar onayi 20 Eki). Once tum bekleyen Pinterest gonderileri YEDEK.json
               (--yedek-drive ile Drive'da boyut dogrulanir; dogrulanamazsa YAZMA YOK). PUT gonderiye YENI id verir, uuid ayni kalir;
               her pin icin uygulama aninda yeniden canli okuma: GET (mevcut gun, uuid) -> kapi (yalniz Pinterest saglayicisi,
               PENDING, mevcut ve yeni saat >= simdi + 2 sa; saati gecmis = GECMIS, dokunulmaz) -> PUT (ayni govde, yalniz
               publicationDate) -> GET (yeni gun, uuid) -> fark: yalniz id, publicationDate.dateTime, creationDate.*, IZINLI_FARK.
               Hata veren pin ATLANIR ve listelenir (5 ardisik HATA = sistematik sorun, DUR). Sonda tam canli geri okuma ile plan
               karsilastirmasi. Cikti: YEDEK.json, SONUC.csv, GERI_OKUMA.txt.
Siniflar: DEGISECEK | AYNI | GECMIS (yayinlandi / saati gecmis / yayina < 2 sa: oldugu gibi kalir) | PLAN_SAATI_GECMIS (yeni saat
  uygulama aninda < simdi + 2 sa: yazilmaz, plan yeniden kosulur) | KAYIP (uuid canli listede yok) | YENI_POST (yeni yil donumu +
  kupa: bu script yazmaz; gorsel URL ve pano id gerekir, ayri adim).
Kullanim: pin_takvim_uygula.py TOKEN.json --plan PLAN_V2.csv --mod kuru|yaz --out OUT [--confirm PIN_TAKVIM_V2] [--yedek-drive gdrive:...]"""
import argparse
import copy
import csv
import importlib.util
import json
import os
import subprocess
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
    ap.add_argument('--sahte', default=''); ap.add_argument('--simdi', default=''); ap.add_argument('--yedek-drive', default='')
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
        mc.n, _istek = 0, mc.istek

        def sayan(*x, **k):
            mc.n += 1
            return _istek(*x, **k)
        mc.istek = sayan
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
         'publicationDate degisir; kapi: yalniz Pinterest, PENDING, mevcut ve yeni saat >= simdi + 2 sa (gecmis = GECMIS, dokunulmaz); '
         'hata veren pin atlanir ve listelenir (5 ardisik hata = DUR); sonda tam geri okuma ile plan karsilastirmasi.',
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

    # --- YAZ (ayri onay, Serdar 20 Eki) ---
    # 1) tam yedek: tum bekleyen Pinterest gonderileri (canli okuma) -> YEDEK.json; --yedek-drive verilirse Drive'da boyut dogrulanir
    yedek = [p for p in canli.values() if mpb.pin_durum(p) == 'PENDING']
    yf = os.path.join(a.out, 'YEDEK.json')
    json.dump({'_okuma': simdi.strftime('%Y-%m-%dT%H:%M:%S'), '_adet': len(yedek), 'gonderiler': yedek}, open(yf, 'w'), ensure_ascii=False, indent=1)
    if a.yedek_drive:
        r1 = subprocess.run(['rclone', 'copyto', yf, f'{a.yedek_drive}/YEDEK.json'], capture_output=True, text=True)
        r2 = subprocess.run(['rclone', 'size', '--json', f'{a.yedek_drive}/YEDEK.json'], capture_output=True, text=True)
        if r1.returncode or r2.returncode or json.loads(r2.stdout or '{}').get('bytes') != os.path.getsize(yf):
            raise SystemExit('DUR: YEDEK.json Drive\'da dogrulanamadi. YAZMA YOK.')
    print(f'YEDEK: {len(yedek)} bekleyen Pinterest gonderisi' + (f' -> {a.yedek_drive}/YEDEK.json (dogrulandi)' if a.yedek_drive else ''))

    # 2) pin basina GET -> kapi -> PUT (yalniz publicationDate) -> GET; hata = atla + listele; 5 ardisik hata = sistematik, DUR
    kk = ['uuid', 'aile', 'cift', 'eski_id', 'yeni_id', 'once', 'hedef', 'okunan', 'fark', 'sonuc']
    t0, ardisik, sonuclar = time.time(), 0, []
    with open(os.path.join(a.out, 'SONUC.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=kk, lineterminator='\n'); w.writeheader()
        for i, x in enumerate(deg, 1):
            hedef = datetime.fromisoformat(f"{x['yeni_tarih']}T{x['yeni_saat']}:00").replace(tzinfo=IST)
            cur0 = datetime.fromisoformat(x['canli_zaman']).replace(tzinfo=IST)
            sat = dict(uuid=x['uuid'], aile=x['aile'], cift=x['cift'], once=x['canli_zaman'], hedef=f"{x['yeni_tarih']} {x['yeni_saat']}")
            try:
                once = gun_oku(mc, cur0.date(), x['uuid'])
                an = datetime.now(IST)
                ag = sorted({(pr.get('network') or '').lower() for pr in (once or {}).get('providers') or []})
                if once is None:
                    sat['sonuc'] = 'ATLANDI (canli listede yok: yayinlanmis/silinmis)'
                elif ag != ['pinterest']:
                    sat['sonuc'] = f'ATLANDI (Pinterest disi saglayici {ag})'
                elif mpb.pin_durum(once) != 'PENDING' or (zaman(once) or an) < an + ESIK:
                    sat['sonuc'] = 'GECMIS (yayinlandi / yayina < 2 sa, dokunulmadi)'
                elif zaman(once) != cur0:
                    sat['sonuc'] = f'ATLANDI (canli saat degismis: {zaman(once):%Y-%m-%d %H:%M})'
                elif hedef < an + ESIK:
                    sat['sonuc'] = 'ATLANDI (plan saati gecmis)'
                else:
                    yeni = copy.deepcopy(once)
                    yeni['publicationDate'] = {'dateTime': hedef.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ}
                    sat['eski_id'] = once.get('id')
                    if mc.istek('PUT', f"/v2/scheduler/posts/{once['id']}", govde=yeni, yok404=True) is mpb.YOK:
                        sat['sonuc'] = 'ATLANDI (PUT 404, yayinlanmis olabilir)'
                    else:
                        sonra = gun_oku(mc, hedef.date(), x['uuid'])
                        if sonra is None:
                            sat['sonuc'] = 'HATA (PUT sonrasi yeni gunde bulunamadi)'
                        else:
                            df = [y for y in mpb.fark(once, sonra) if y not in ('id', 'publicationDate.dateTime') and y not in mpb.IZINLI_FARK
                                  and not y.startswith('creationDate')]
                            sat.update(yeni_id=sonra.get('id'), okunan=(sonra.get('publicationDate') or {}).get('dateTime'), fark='|'.join(df))
                            sat['sonuc'] = 'PASS' if zaman(sonra) == hedef and not df else 'HATA (geri okuma farki)'
            except SystemExit as e:
                sat['sonuc'] = f'HATA ({str(e)[:160]})'
            w.writerow(sat); f.flush(); sonuclar.append(sat)
            ardisik = ardisik + 1 if sat['sonuc'].startswith('HATA') else 0
            g = time.time() - t0
            print(f"[{i}/{len(deg)}] {x['aile']} {x['cift']} {sat['sonuc']} | gecen {g / 60:.1f} dk, kalan ~{g / i * (len(deg) - i) / 60:.1f} dk, "
                  f"%{100 * i / len(deg):.0f}", flush=True)
            if ardisik >= 5:
                print('DUR: 5 ardisik HATA (sistematik sorun), kalan pinlere dokunulmadi', flush=True)
                break

    # 3) geri okuma: tum plan satirlari canli ile karsilastirilir
    son_canli = pencere(mc, bas, son)
    gk, fark_l = Counter(), []
    for x in satir:
        if not x['uuid']:
            continue
        p = son_canli.get(x['uuid'])
        plan_z = f"{x['yeni_tarih']} {x['yeni_saat']}"
        if p is None:
            gk['canli listede yok (yayinlanmis/silinmis)'] += 1; continue
        cz = zaman(p).strftime('%Y-%m-%d %H:%M') if zaman(p) else ''
        if mpb.pin_durum(p) != 'PENDING':
            gk[f'yayinlandi ({mpb.pin_durum(p)})'] += 1
        elif cz == plan_z:
            gk['canli = plan'] += 1
        else:
            gk['canli != plan'] += 1; fark_l.append(f"  {x['aile']} {x['cift']} uuid {x['uuid']}: canli {cz} plan {plan_z} ({x['sinif']})")
    sk = Counter(s_['sonuc'].split(' (')[0] for s_ in sonuclar)
    pin_once = len(yedek); pin_sonra = sum(1 for p in son_canli.values() if mpb.pin_durum(p) == 'PENDING')
    g = [f'GERI OKUMA {datetime.now(IST):%Y-%m-%d %H:%M} (Europe/Istanbul); plan PLAN_V2.csv; canli GET {bas:%Y-%m-%d} - {son:%Y-%m-%d}',
         f'Yazma: DEGISECEK {len(deg)} -> islenen {len(sonuclar)}; sonuc {dict(sk)}',
         f'Plan (mevcut pin) x canli: {dict(gk)}',
         f'Bekleyen Pinterest gonderisi: once {pin_once}, sonra {pin_sonra} (aradaki fark = bu surede yayinlanan)',
         f'Metricool cagri: {mc.n if hasattr(mc, "n") else "-"}; sure {(time.time() - t0) / 60:.1f} dk',
         '', 'ATLANDI / HATA / GECMIS:'] + [f"  {s_['aile']} {s_['cift']} uuid {s_['uuid']}: {s_['once']} -> {s_['hedef']} | {s_['sonuc']} {s_.get('fark', '')}"
                                            for s_ in sonuclar if s_['sonuc'] != 'PASS'] + ['', 'CANLI != PLAN:'] + fark_l
    open(os.path.join(a.out, 'GERI_OKUMA.txt'), 'w').write('\n'.join(g) + '\n')
    print('\n'.join(g[:5]))

if __name__ == '__main__':
    main()
