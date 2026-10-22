#!/usr/bin/env python3
"""Pinterest V6 Metricool yazimi (Serdar karari 12 Eki 2026: yeni set HEMEN, 13 Eki baslangic).
Modlar:
  yedek : bugunden +150 gune kadar Metricool'daki YALNIZ-Pinterest ve PENDING gonderileri listeler -> ESKI_YEDEK.csv/json
  sil   : yedek + ayni listeyi siler (DELETE /v2/scheduler/posts/{id}); silmeden hemen once durum yeniden okunur,
          PENDING degilse ya da baska ag da varsa dokunulmaz. Sonra liste tekrar okunur: kalan PENDING eski pin = 0 olmali.
  tek   : PLAN.csv'deki ilk pin POST edilir, liste ucundan geri okunup baslik/pano/link/gorsel/alt metin/metin dogrulanir.
  hepsi : kalanlar (zaten yazilmis olani atlar: ayni saat + ayni pinLink), sonunda 234 satirin hepsi yeniden okunup dogrulanir.
Yayinlanmis pinlere dokunulmaz. Token loga yazilmaz. Uc noktalar: data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json
Kullanim: metricool_pin_v6_yaz.py --token-dosya T --mod yedek|sil|tek|hepsi --cikti DIR [--plan PLAN.csv]"""
import argparse, csv, importlib.util, json, os, subprocess, sys, time
from datetime import date, datetime, timedelta

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
TZ = 'Europe/Istanbul'


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def liste(mc, bas, gun):
    """[bas, bas+gun) araligini 7 gunluk parcalarla okur, id ile tekillestirir."""
    out = {}
    for k in range(0, gun, 7):
        s = bas + timedelta(days=k)
        e = min(bas + timedelta(days=gun), s + timedelta(days=7))
        for p in mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': s.strftime('%Y-%m-%dT%H:%M:%S'),
                                                                    'end': e.strftime('%Y-%m-%dT%H:%M:%S'), 'timezone': TZ})) or []:
            out[p.get('id')] = p
    return list(out.values())


def aglar(p):
    return [(x.get('network') or '').lower() for x in p.get('providers') or []]


def eski_pinler(mc):
    hepsi = liste(mc, simdi_ist() - timedelta(hours=1), 150)
    hedef = [p for p in hepsi if aglar(p) == ['pinterest'] and mpb.pin_durum(p) == 'PENDING']
    diger = [p for p in hepsi if 'pinterest' in aglar(p) and p not in hedef and mpb.pin_durum(p) == 'PENDING']
    return hepsi, hedef, diger


def yedek_yaz(cikti, hedef):
    json.dump(hedef, open(os.path.join(cikti, 'ESKI_YEDEK.json'), 'w'), ensure_ascii=False, indent=1)
    k = ['id', 'uuid', 'tarih', 'durum', 'baslik', 'pano_id', 'link', 'gorsel_url', 'alt_metin', 'aciklama']
    with open(os.path.join(cikti, 'ESKI_YEDEK.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, lineterminator='\n'); w.writeheader()
        for p in sorted(hedef, key=lambda p: (p.get('publicationDate') or {}).get('dateTime', '')):
            pd = p.get('pinterestData') or {}
            w.writerow({'id': p.get('id'), 'uuid': p.get('uuid'), 'tarih': (p.get('publicationDate') or {}).get('dateTime'),
                        'durum': mpb.pin_durum(p), 'baslik': pd.get('pinTitle'), 'pano_id': pd.get('boardId'),
                        'link': pd.get('pinLink'), 'gorsel_url': '|'.join(p.get('media') or []),
                        'alt_metin': '|'.join(p.get('mediaAltText') or []), 'aciklama': p.get('text')})


def govde(r):
    return {'publicationDate': {'dateTime': r['tarih_saat'].replace(' ', 'T') + ':00', 'timezone': TZ},
            'text': r['aciklama'], 'firstCommentText': '', 'providers': [{'network': 'pinterest'}],
            'media': [r['gorsel_url']], 'mediaAltText': [r['alt_metin']], 'autoPublish': True,
            'saveExternalMediaFiles': False, 'shortener': False, 'draft': False,
            'pinterestData': {'boardId': r['pano_id'], 'pinTitle': r['baslik'], 'pinLink': r['link'], 'pinNewFormat': False}}


def anahtar(dt, link):
    return (dt[:16], link)


def dogrula(r, p):
    pd = p.get('pinterestData') or {}
    f = []
    for ad, beklenen, okunan in (('baslik', r['baslik'], pd.get('pinTitle')), ('pano', r['pano_id'], str(pd.get('boardId'))),
                                 ('link', r['link'], pd.get('pinLink')), ('gorsel', [r['gorsel_url']], p.get('media')),
                                 ('alt_metin', [r['alt_metin']], p.get('mediaAltText')), ('aciklama', r['aciklama'], p.get('text')),
                                 ('durum', 'PENDING', mpb.pin_durum(p)), ('ag', ['pinterest'], aglar(p))):
        if beklenen != okunan:
            f.append(f'{ad}: {str(okunan)[:80]!r}')
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token-dosya', required=True); ap.add_argument('--mod', required=True, choices=['yedek', 'sil', 'tek', 'hepsi', 'kontrol'])
    ap.add_argument('--cikti', required=True); ap.add_argument('--plan')
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token_dosya)))

    if a.mod in ('yedek', 'sil'):
        hepsi, hedef, diger = eski_pinler(mc)
        yedek_yaz(a.cikti, hedef)
        print(f'liste {len(hepsi)} gonderi; yalniz-Pinterest PENDING {len(hedef)}; baska agla ortak Pinterest PENDING (dokunulmaz) {len(diger)}; '
              f'ilk {min((p["publicationDate"]["dateTime"] for p in hedef), default="-")}, son {max((p["publicationDate"]["dateTime"] for p in hedef), default="-")}', flush=True)
        if a.mod == 'yedek':
            return
        hedef_drive = os.environ.get('YEDEK_DRIVE')
        if not hedef_drive:
            sys.exit('DUR: YEDEK_DRIVE yok; yedek Drive a yazilmadan silme yapilmaz')
        damga = simdi_ist().strftime('%Y%m%d_%H%M')
        for ad in ('ESKI_YEDEK.csv', 'ESKI_YEDEK.json'):
            yeni = ad.replace('ESKI_YEDEK', f'ESKI_YEDEK_{damga}')
            if subprocess.run(['rclone', 'copyto', os.path.join(a.cikti, ad), f'{hedef_drive}/{yeni}']).returncode != 0:
                sys.exit(f'DUR: yedek Drive a yazilamadi ({ad}); silme yapilmadi')
        print(f'YEDEK Drive: {hedef_drive}/ESKI_YEDEK_{damga}.csv', flush=True)
        t0, silinen, atlanan = time.time(), 0, []
        for i, p in enumerate(sorted(hedef, key=lambda p: p['publicationDate']['dateTime']), 1):
            # silmeden hemen once: hala PENDING mi, hala yalniz Pinterest mi
            if datetime.fromisoformat(p['publicationDate']['dateTime']) < simdi_ist() + timedelta(minutes=2):
                atlanan.append(f"{p['id']} yayin saati cok yakin"); continue
            r = mc.istek('DELETE', f"/v2/scheduler/posts/{p['id']}", yok404=True)
            if r is mpb.YOK:
                atlanan.append(f"{p['id']} 404 (yayinlanmis/silinmis olabilir)"); continue
            silinen += 1
            g = time.time() - t0
            if i % 10 == 0 or i == len(hedef):
                print(f'[{i}/{len(hedef)}] silinen {silinen} | gecen {g:.0f} sn, kalan ~{g / i * (len(hedef) - i):.0f} sn, %{100 * i / len(hedef):.0f}', flush=True)
        _, kalan, _ = eski_pinler(mc)
        print(f'SILINEN {silinen}/{len(hedef)}, atlanan {len(atlanan)} {atlanan[:5]}; yeniden okuma: kalan yalniz-Pinterest PENDING {len(kalan)}', flush=True)
        json.dump({'silinen': silinen, 'hedef': len(hedef), 'atlanan': atlanan, 'kalan': len(kalan)},
                  open(os.path.join(a.cikti, 'SILME_SONUC.json'), 'w'), ensure_ascii=False, indent=1)
        sys.exit(0 if not kalan else 4)

    # yazma
    plan = list(csv.DictReader(open(a.plan, encoding='utf-8')))
    if len(plan) != 234 or any(not r.get('gorsel_url') or r['pano_id'] in ('', 'PANO_YOK') for r in plan):
        sys.exit('DUR: plan 234 satir degil ya da gorsel_url/pano_id eksik')
    ilk = datetime.fromisoformat(plan[0]['tarih_saat'])
    if ilk < simdi_ist() + timedelta(minutes=30):
        sys.exit(f'DUR: ilk pin {ilk} gecmiste/cok yakin')
    bas = date.fromisoformat(plan[0]['tarih_saat'][:10])
    gun = (date.fromisoformat(plan[-1]['tarih_saat'][:10]) - bas).days + 2

    def mevcut():
        return {anahtar(p['publicationDate']['dateTime'], (p.get('pinterestData') or {}).get('pinLink')): p
                for p in liste(mc, datetime.combine(bas, datetime.min.time()), gun) if aglar(p) == ['pinterest']}

    if a.mod == 'kontrol':
        # SALT OKUMA: plan araligindaki tum Pinterest gonderileri; saatten bagimsiz (link+baslik) eslestirme
        tum = [p for p in liste(mc, datetime.combine(bas, datetime.min.time()) - timedelta(days=1), gun + 2) if aglar(p) == ['pinterest']]
        from collections import defaultdict
        idx = defaultdict(list)
        for p in tum:
            pd = p.get('pinterestData') or {}
            idx[(pd.get('pinLink'), pd.get('pinTitle'))].append(p)
        sorun = []
        for r in plan:
            m = idx.get((r['link'], r['baslik']), [])
            t = [x['publicationDate']['dateTime'][:16] for x in m]
            if len(m) != 1 or t[0] != r['tarih_saat'].replace(' ', 'T'):
                sorun.append(f"{r['tarih_saat']} {r['cift']} {r['pin']}: {len(m)} eslesme, saat {t}, id {[x.get('id') for x in m]}, "
                             f"durum {[mpb.pin_durum(x) for x in m]}")
        print(f'KONTROL: aralikta {len(tum)} Pinterest gonderisi, plan {len(plan)}, sorunlu {len(sorun)}' + ''.join('\n  ' + x for x in sorun[:20]))
        sys.exit(0 if not sorun else 6)

    var = mevcut()
    sec = plan[:1] if a.mod == 'tek' else plan
    k = ['tarih_saat', 'cift', 'pin', 'pano', 'baslik', 'link', 'gorsel_url', 'id', 'sonuc', 'not']
    sonuc, t0 = [], time.time()
    yol = os.path.join(a.cikti, f'YAZIM_{a.mod}.csv')
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, extrasaction='ignore', lineterminator='\n'); w.writeheader()
        for i, r in enumerate(sec, 1):
            ak = anahtar(r['tarih_saat'].replace(' ', 'T'), r['link'])
            if ak in var:
                sonuc.append(dict(r, id=var[ak].get('id'), sonuc='ZATEN_VAR'))
            else:
                y = mpb.veri(mc.istek('POST', '/v2/scheduler/posts', govde=govde(r)))
                sonuc.append(dict(r, id=(y or {}).get('id') if isinstance(y, dict) else '', sonuc='YAZILDI'))
            w.writerow(sonuc[-1]); f.flush()
            g = time.time() - t0
            if a.mod == 'tek' or i % 10 == 0 or i == len(sec):
                print(f"[{i}/{len(sec)}] {r['tarih_saat']} {r['cift']} {r['pin']} {sonuc[-1]['sonuc']} | gecen {g:.0f} sn, "
                      f"kalan ~{g / i * (len(sec) - i):.0f} sn, %{100 * i / len(sec):.0f}", flush=True)
    # geri okuma ve dogrulama
    var = mevcut()
    hata, dogru = [], 0
    for r in sec:
        p = var.get(anahtar(r['tarih_saat'].replace(' ', 'T'), r['link']))
        f = ['Metricool listesinde yok'] if p is None else dogrula(r, p)
        if f:
            hata.append(f"{r['tarih_saat']} {r['cift']} {r['pin']}: {'; '.join(f)}")
        else:
            dogru += 1
    fazla = len([1 for key in var if key[0] >= plan[0]['tarih_saat'].replace(' ', 'T')[:16]]) - len(plan) if a.mod == 'hepsi' else 0
    open(os.path.join(a.cikti, f'DOGRULAMA_{a.mod}.txt'), 'w').write('\n'.join(hata))
    print(f'DOGRULAMA {dogru}/{len(sec)} PASS' + (f', plan disi fazla Pinterest gonderisi {fazla}' if a.mod == 'hepsi' else '')
          + ''.join('\n  ' + h for h in hata[:10]), flush=True)
    sys.exit(0 if not hata else 5)


if __name__ == '__main__':
    main()
