#!/usr/bin/env python3
"""Metricool: bekleyen Pinterest gonderilerinin gorselini + alt metnini yeni pinle degistir (Serdar onayi 20 Eki 2026).
Kaynak: PINTEREST_PIN_DEGISIM_20261020/ESLEME.csv (gonderi_id, uuid, tarih, aile, cift, eski_medya, yeni_pin_dosyasi).
Yeni gorsel URL: <url-kok>/poster/<dosya> (PIN_V2) ya da <url-kok>/y1/<dosya> (KAPAK_Y1 PIN).
Modlar:
  dogrula : her benzersiz yeni URL GET /actions/normalize/image/url ile denenir -> NORMALIZE.csv (yazma yok).
  test    : ilk uygun TEK gonderi.   hepsi : kalan uygun gonderiler (onceki SONUC.csv'de PASS olanlar atlanir).
Gonderi basina: uuid ile bul (yayin gunu +-1 gun listesi; kopya = DUR) -> kapi (PENDING, yayina >= 2 sa, tek medya,
  eski medya = ESLEME eski_medya ya da zaten yeni) -> ONCE govdesi, YALNIZ media[0] + mediaAltText[0] degisir -> PUT
  /v2/scheduler/posts/{id} -> uuid ile geri oku -> fark yalniz media[0], mediaAltText[0], id + IZINLI_FARK olmali.
  FAIL -> DUR (sonraki gonderiye gecilmez). Yayina < 2 sa kalan: ATLANDI_2SAAT (yazma yok).
Alt metin (uzun/orta tire yok, <= 500): poster "<A> and <B> zodiac couple wall art with names, personalized unframed
  print on a warm wall"; yildonumu "1st anniversary gift, personalized <A> and <B> paper anniversary print with names
  and date". A/B sirasi gonderi basligindaki sira (yoksa cift anahtari sirasi).
Token loga/dosyaya yazilmaz (mpb.MC). Kullanim:
  metricool_pin_gorsel_degistir.py --token-dosya T.json --esleme ESLEME.csv --url-kok URL --mod dogrula|test|hepsi --cikti DIR
                                   [--normalize NORMALIZE.csv] [--onceki SONUC.csv]"""
import argparse, copy, csv, importlib.util, json, os, re, sys, time
from datetime import datetime, timedelta, timezone

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(D, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
ESIK = timedelta(hours=2)
BURC = r'Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces'
ALT = {'poster': '{a} and {b} zodiac couple wall art with names, personalized unframed print on a warm wall',
       'yildonumu': '1st anniversary gift, personalized {a} and {b} paper anniversary print with names and date'}
ALT_DEGISEN = ('media[0]', 'mediaAltText[0]', 'id')
SK = ['uuid', 'eski_id', 'yeni_id', 'tarih', 'aile', 'cift', 'eski_gorsel', 'yeni_gorsel', 'eski_alt', 'yeni_alt', 'durum', 'not']


def simdi():
    return datetime.now(IST)


def yeni_url(kok, r):
    return f"{kok.rstrip('/')}/{'poster' if r['aile'] == 'poster' else 'y1'}/{r['yeni_pin_dosyasi']}"


def alt_metin(aile, cift, baslik):
    z = [x.capitalize() for x in re.findall(BURC, baslik or '', flags=re.I)[:2]]
    c = [x.capitalize() for x in cift.split('_')]
    a, b = z if len(z) == 2 and sorted(x.upper() for x in z) == sorted(cift.split('_')) else c
    t = ALT[aile].format(a=a, b=b)
    if '—' in t or '–' in t or len(t) > 500:
        raise SystemExit(f'DUR: alt metin kurali: {t!r}')
    return t


def bul(mc, uuid, tarih):
    """uuid ile, yayin gununun +-1 gun penceresinde. Donus: (gonderi|None, not)."""
    g = datetime.fromisoformat(tarih[:19])
    j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{g - timedelta(days=1):%Y-%m-%dT00:00:00}',
                                                'end': f'{g + timedelta(days=2):%Y-%m-%dT00:00:00}', 'timezone': TZ})
    m = [p for p in (mpb.veri(j) or []) if str(p.get('uuid')) == str(uuid)]
    if len(m) > 1:
        raise SystemExit(f'DUR: uuid {uuid} listede {len(m)} kez (kopya)')
    return (m[0], '') if m else (None, 'uuid bulunamadi (silinmis/yayinlanmis olabilir)')


def dogrula(mc, a, satirlar):
    urller = sorted({yeni_url(a.url_kok, r) for r in satirlar})
    yol = os.path.join(a.cikti, 'NORMALIZE.csv')
    t0, hata = time.time(), 0
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['url', 'sonuc', 'yanit'])
        for i, u in enumerate(urller, 1):
            try:
                y = mc.istek('GET', '/actions/normalize/image/url', {'url': u})
                m = re.findall(r'https?://([^/\s"]+)', json.dumps(y))
                ok = bool(m)                                   # HTTP 200 + yanitta URL (ham yanit yazilmaz: imzali URL olabilir)
                s = f"200; anahtarlar {sorted(y) if isinstance(y, dict) else type(y).__name__}; url host {sorted(set(m))[:3]}"
            except SystemExit as e:
                s, ok = re.sub(r'https?://\S+', '<url>', str(e))[:200], False
            hata += not ok
            w.writerow([u, 'OK' if ok else 'HATA', s]); f.flush()
            if i % 20 == 0 or i == len(urller):
                g = time.time() - t0
                print(f'NORMALIZE [{i}/{len(urller)}] hata {hata} | gecen {g:.0f} sn, kalan ~{g / i * (len(urller) - i):.0f} sn', flush=True)
    print(f'NORMALIZE {len(urller) - hata}/{len(urller)} OK')
    if hata:
        raise SystemExit(f'DUR: normalize HATA {hata}')


def main():
    ap = argparse.ArgumentParser()
    for k in ('token-dosya', 'esleme', 'url-kok', 'mod', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--normalize', default=''); ap.add_argument('--onceki', default='')
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token_dosya)))
    E = [r for r in csv.DictReader(open(a.esleme, encoding='utf-8-sig')) if r['durum'] == 'eslesti']
    E.sort(key=lambda r: r['tarih'])
    print(f'ESLEME eslesti: {len(E)}; mod {a.mod}; simdi {simdi():%Y-%m-%d %H:%M} Istanbul')
    if a.mod == 'dogrula':
        return dogrula(mc, a, E)
    ok_url = set()
    if a.normalize and os.path.exists(a.normalize):
        ok_url = {r['url'] for r in csv.DictReader(open(a.normalize, encoding='utf-8')) if r['sonuc'] == 'OK'}
    bitti = set()
    if a.onceki and os.path.exists(a.onceki):
        bitti = {r['uuid'] for r in csv.DictReader(open(a.onceki, encoding='utf-8')) if r['durum'] in ('PASS', 'ZATEN_YENI')}
    hedef = [r for r in E if r['uuid'] not in bitti]
    yol = os.path.join(a.cikti, f'SONUC_{a.mod}.csv')
    t0, n_yaz, sonuc = time.time(), 0, []
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=SK, lineterminator='\n'); w.writeheader()

        def kayit(**k):
            sonuc.append({x: k.get(x, '') for x in SK}); w.writerow(sonuc[-1]); f.flush()
        for i, r in enumerate(hedef, 1):
            u = yeni_url(a.url_kok, r)
            temel = dict(uuid=r['uuid'], eski_id=r['gonderi_id'], tarih=r['tarih'], aile=r['aile'], cift=r['cift'],
                         eski_gorsel=r['eski_medya'], yeni_gorsel=u)
            if datetime.fromisoformat(r['tarih'][:19]).replace(tzinfo=IST) - simdi() < ESIK:
                kayit(**temel, yeni_alt=alt_metin(r['aile'], r['cift'], ''), durum='ATLANDI_2SAAT')
                continue
            if a.mod == 'test' and n_yaz >= 1:
                break
            if u not in ok_url:
                kayit(**temel, durum='DUR', **{'not': 'yeni URL normalize OK degil'})
                raise SystemExit(f'DUR: normalize OK olmayan URL {u}')
            once, notu = bul(mc, r['uuid'], r['tarih'])
            if once is None:
                kayit(**temel, durum='ATLANDI', **{'not': notu}); continue
            zt = (once.get('publicationDate') or {}).get('dateTime', '')
            med, alt = once.get('media') or [], once.get('mediaAltText') or []
            pd = once.get('pinterestData') or {}
            temel.update(eski_id=once.get('id'), eski_alt=alt[0] if alt else '')
            yalt = alt_metin(r['aile'], r['cift'], pd.get('pinTitle'))
            temel['yeni_alt'] = yalt
            if mpb.pin_durum(once) != 'PENDING':
                kayit(**temel, durum='ATLANDI', **{'not': f'durum {mpb.pin_durum(once)}'}); continue
            if datetime.fromisoformat(zt[:19]).replace(tzinfo=IST) - simdi() < ESIK:
                kayit(**temel, durum='ATLANDI_2SAAT', **{'not': f'canli tarih {zt}'}); continue
            if len(med) != 1:
                kayit(**temel, durum='DUR', **{'not': f'medya sayisi {len(med)}'}); raise SystemExit(f'DUR: {r["uuid"]} medya {len(med)}')
            if med[0] == u and alt and alt[0] == yalt:
                kayit(**temel, durum='ZATEN_YENI', yeni_id=once.get('id')); continue
            if med[0] not in (r['eski_medya'], u):
                kayit(**temel, durum='DUR', **{'not': f'medya beklenmedik: {med[0][:120]}'})
                raise SystemExit(f'DUR: {r["uuid"]} medya ESLEME ile ayni degil')
            json.dump(once, open(os.path.join(a.cikti, f'ONCE_{r["uuid"]}.json'), 'w'), ensure_ascii=False, indent=1)
            yeni = copy.deepcopy(once)
            yeni['media'][0] = u
            yeni['mediaAltText'] = [yalt]
            y = mc.istek('PUT', f"/v2/scheduler/posts/{once['id']}", govde=yeni, yok404=True)
            n_yaz += 1
            if y is mpb.YOK:
                kayit(**temel, durum='ATLANDI', **{'not': 'PUT 404 (yayinlanmis olabilir)'}); continue
            sonra, notu = bul(mc, r['uuid'], r['tarih'])
            if sonra is None:
                kayit(**temel, durum='DUR', **{'not': 'PUT sonrasi bulunamadi'}); raise SystemExit(f'DUR: {r["uuid"]} PUT sonrasi yok')
            json.dump(sonra, open(os.path.join(a.cikti, f'SONRA_{r["uuid"]}.json'), 'w'), ensure_ascii=False, indent=1)
            tum = mpb.fark(once, sonra)
            df = [x for x in tum if x not in ALT_DEGISEN and x not in mpb.IZINLI_FARK]
            sm, sa = (sonra.get('media') or [''])[0], (sonra.get('mediaAltText') or [''])[0]
            ok = sm == u and sa == yalt and not df and mpb.pin_durum(sonra) == 'PENDING'
            kayit(**temel, yeni_id=sonra.get('id'), durum='PASS' if ok else 'FAIL',
                  **{'not': ('' if ok else f'gorsel {sm == u}, alt {sa == yalt}, durum {mpb.pin_durum(sonra)}, fark {df}') + f' | degisen {tum}'})
            g = time.time() - t0
            print(f"[{i}/{len(hedef)}] {r['uuid']} {r['tarih']} {r['aile']} {r['cift']} {sonuc[-1]['durum']} | gecen {g:.0f} sn, "
                  f"kalan ~{g / i * (len(hedef) - i):.0f} sn, %{100 * i / len(hedef):.0f}", flush=True)
            if not ok:
                raise SystemExit(f"DUR: dogrulama FAIL {r['uuid']}: {sonuc[-1]['not'][:300]}")
    from collections import Counter
    print(f'SONUC {a.mod}: {dict(Counter(s["durum"] for s in sonuc))}; PUT {n_yaz}')


if __name__ == '__main__':
    main()
