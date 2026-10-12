#!/usr/bin/env python3
"""Metricool: "Anniversary Gifts for Couples" pin basliklari (Serdar onayi 12 Eki 2026).
Eski: "A Personalized Anniversary Gift for a|an {A} and {B} Couple"
Yeni: "{A} and {B} Anniversary Gift, Personalized Zodiac Couple Wall Art"
Yalniz Pinterest durumu PENDING olan gonderilerde YALNIZ pinterestData.pinTitle degisir (GET -> pinTitle -> PUT -> GET).
Yayinlanmis/diger durumlara dokunulmaz. Uc noktalar: data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json
  GET /v2/scheduler/posts?start&end&timezone   GET|PUT /v2/scheduler/posts/{id}   (X-Mc-Auth, userId, blogId)
Mod: kuru (liste + CSV), tek (1 gonderi), hepsi (kalanlar). Token loga yazilmaz (::add-mask::).
Kullanim: metricool_pin_baslik.py --token-dosya T.json --mod kuru|tek|hepsi --cikti DIR"""
import argparse, copy, csv, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

API = 'https://app.metricool.com/api'
TZ = 'Europe/Istanbul'
BAS, SON = '2026-10-11T14:00:00', '2026-10-16T23:00:00'
ESKI = re.compile(r'^A Personalized Anniversary Gift for an? (.+?) and (.+?) Couple$')
BEKLE = 1.1
YOK = '__404__'
# PUT sonrasi Metricool'un kendisinin degistirdigi alanlar (3. deneme olcumu, 385760353): duzenleme zamani ve
# Pinterest'e gitmeyen instagramData varsayilanlari. Metin, link, gorsel, pano, saat, durum burada YOK -> degisirse FAIL.
IZINLI_FARK = ('creationDate.dateTime', 'creationDate.timezone', 'instagramData.type', 'instagramData.showReelOnFeed')


def yeni_baslik(eski):
    m = ESKI.match(eski.strip())
    return f'{m.group(1)} and {m.group(2)} Anniversary Gift, Personalized Zodiac Couple Wall Art' if m else None


class MC:
    def __init__(self, tok):
        self.t, self.u, self.b = tok['userToken'], str(tok['userId']), str(tok['blogId'])
        print(f'::add-mask::{self.t}', flush=True)
        self.son = 0.0

    def istek(self, yontem, yol, params=None, govde=None, yok404=False):
        q = dict(params or {}, userId=self.u, blogId=self.b)
        url = f'{API}{yol}?{urllib.parse.urlencode(q)}'
        veri = json.dumps(govde).encode() if govde is not None else None
        for deneme in range(4):
            bekle = BEKLE - (time.time() - self.son)
            if bekle > 0:
                time.sleep(bekle)
            r = urllib.request.Request(url, data=veri, method=yontem,
                                       headers={'X-Mc-Auth': self.t, 'Accept': 'application/json',
                                                'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(r, timeout=60) as y:
                    self.son = time.time()
                    g = y.read()
                    return json.loads(g) if g else None
            except urllib.error.HTTPError as e:
                self.son = time.time()
                if e.code == 404 and yok404:
                    return YOK
                if e.code == 429 and deneme < 3:
                    s = int(e.headers.get('Retry-After') or 60)
                    print(f'429: {s} sn bekleniyor', flush=True); time.sleep(s); continue
                if e.code in (502, 503, 504) and yontem in ('GET', 'DELETE') and deneme < 3:
                    print(f'{e.code} {yontem}: {10 * (deneme + 1)} sn sonra yeniden', flush=True)
                    time.sleep(10 * (deneme + 1)); continue
                govde_h = e.read()[:300].decode('utf-8', 'replace').replace(self.t, '***')
                raise SystemExit(f'HTTP {e.code} {yontem} {yol}: {govde_h}')


def veri(j):
    return j.get('data', j) if isinstance(j, dict) else j


def bul(liste, ref):
    """Ayni gonderi: id, yoksa uuid, yoksa (yayin saati + pinLink). Liste ucu kimligi her okumada ayni olmayabilir."""
    for anahtar in (lambda x: x.get('id') == ref['id'], lambda x: ref.get('uuid') and x.get('uuid') == ref['uuid'],
                    lambda x: (x.get('publicationDate') or {}).get('dateTime') == ref['tarih']
                    and (x.get('pinterestData') or {}).get('pinLink') == ref['pinLink']):
        m = [x for x in liste if anahtar(x)]
        if m:
            return m
    return []


def oku(mc, ref):
    """Tekil GET (404 -> liste ucu). Bulunamazsa None; birden fazla eslesme DUR."""
    p = mc.istek('GET', f"/v2/scheduler/posts/{ref['id']}", yok404=True)
    if p is not YOK and p is not None:
        return veri(p), 'tekil'
    m = bul(veri(mc.istek('GET', '/v2/scheduler/posts', {'start': BAS, 'end': SON, 'timezone': TZ})), ref)
    if len(m) > 1:
        raise SystemExit(f"DUR: {ref['id']} icin {len(m)} eslesme (kopya?): {[x.get('id') for x in m]}")
    return (m[0], 'liste') if m else (None, 'liste')


def pin_durum(p):
    for pr in p.get('providers') or []:
        if (pr.get('network') or '').lower() == 'pinterest':
            return pr.get('status') or ''
    return None


def satir(p):
    pd = p.get('pinterestData') or {}
    eski = pd.get('pinTitle') or ''
    y = yeni_baslik(eski)
    return {'id': p.get('id'), 'uuid': p.get('uuid', ''), 'tarih': (p.get('publicationDate') or {}).get('dateTime', ''),
            'tz': (p.get('publicationDate') or {}).get('timezone', ''), 'durum': pin_durum(p),
            'boardId': pd.get('boardId', ''), 'pinLink': pd.get('pinLink', ''), 'eski_baslik': eski,
            'yeni_baslik': y or '', 'yeni_uzunluk': len(y) if y else ''}


def fark(a, b, yol=''):
    """a ve b arasindaki farkli alan yollari (pinterestData.pinTitle dahil)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += fark(a.get(k), b.get(k), f'{yol}.{k}' if yol else k)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += fark(x, y, f'{yol}[{i}]')
        return out
    return [] if a == b else [yol]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token-dosya', required=True); ap.add_argument('--mod', choices=['kuru', 'tek', 'hepsi'], required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    mc = MC(json.load(open(a.token_dosya)))

    liste = veri(mc.istek('GET', '/v2/scheduler/posts', {'start': BAS, 'end': SON, 'timezone': TZ}))
    if not isinstance(liste, list):
        raise SystemExit(f'DUR: beklenmeyen liste yaniti: {str(liste)[:200]}')
    json.dump(liste, open(os.path.join(a.cikti, 'HAM_LISTE.json'), 'w'), ensure_ascii=False, indent=1)
    pinler = [p for p in liste if pin_durum(p) is not None]
    eslesen = [satir(p) for p in pinler if yeni_baslik((p.get('pinterestData') or {}).get('pinTitle') or '')]
    zaten = [satir(p) for p in pinler if ((p.get('pinterestData') or {}).get('pinTitle') or '').endswith(
        'Anniversary Gift, Personalized Zodiac Couple Wall Art')]
    hedef = [r for r in eslesen if r['durum'] == 'PENDING']
    hata = [f"{r['id']} uzunluk/tire" for r in eslesen if not r['yeni_uzunluk'] or r['yeni_uzunluk'] >= 100
            or '—' in r['yeni_baslik'] or '–' in r['yeni_baslik']]
    with open(os.path.join(a.cikti, 'KURU_DENEME.csv'), 'w', newline='', encoding='utf-8') as f:
        k = ['id', 'uuid', 'tarih', 'tz', 'durum', 'boardId', 'pinLink', 'eski_baslik', 'yeni_baslik', 'yeni_uzunluk', 'islem']
        w = csv.DictWriter(f, fieldnames=k, lineterminator='\n'); w.writeheader()
        for r in sorted(eslesen + zaten, key=lambda r: r['tarih']):
            w.writerow(dict(r, islem='DEGISECEK' if r in hedef else ('ZATEN_YENI' if r in zaten else 'DOKUNULMAZ')))
    say = {}
    for r in eslesen:
        say[r['durum']] = say.get(r['durum'], 0) + 1
    print(f'liste {len(liste)} gonderi, pinterest {len(pinler)}, eski kalip {len(eslesen)} {say}, '
          f'zaten yeni {len(zaten)}, hedef (PENDING) {len(hedef)}, boardId {sorted({r["boardId"] for r in eslesen})}')
    if hata:
        raise SystemExit('DUR: ' + '; '.join(hata))
    if a.mod == 'kuru':
        return

    sec = sorted(hedef, key=lambda r: r['tarih'], reverse=True)
    if a.mod == 'tek':
        sec = sec[:1]
    yol = os.path.join(a.cikti, f'ONCE_SONRA_{a.mod}.csv')
    k = ['id', 'yeni_id', 'tarih', 'eski_baslik', 'yeni_baslik', 'okunan_baslik', 'diger_fark', 'sonuc']
    t0, sonuc = time.time(), []
    with open(yol, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=k, lineterminator='\n'); w.writeheader()
        for i, r in enumerate(sec, 1):
            once, kaynak = oku(mc, r)
            if once is None:
                sonuc.append(dict(r, sonuc='ATLANDI kayboldu (yayinlanmis olabilir)'))
                w.writerow({x: sonuc[-1].get(x, '') for x in k}); f.flush(); continue
            o = satir(once)
            if o['durum'] != 'PENDING' or o['eski_baslik'] != r['eski_baslik']:
                sonuc.append(dict(r, okunan_baslik=o['eski_baslik'], sonuc=f"ATLANDI durum={o['durum']}"))
                w.writerow({x: sonuc[-1].get(x, '') for x in k}); f.flush(); continue
            yeni = copy.deepcopy(once)
            yeni['pinterestData']['pinTitle'] = r['yeni_baslik']
            if mc.istek('PUT', f"/v2/scheduler/posts/{once['id']}", govde=yeni, yok404=True) is YOK:
                sonuc.append(dict(r, sonuc='ATLANDI PUT 404 (yayinlanmis olabilir)'))
                w.writerow({x: sonuc[-1].get(x, '') for x in k}); f.flush(); continue
            sonra, _ = oku(mc, dict(r, id=once['id']))
            if sonra is None:
                sonuc.append(dict(r, sonuc='ATLANDI PUT sonrasi bulunamadi (yayinlanmis olabilir)'))
                w.writerow({x: sonuc[-1].get(x, '') for x in k}); f.flush(); continue
            okunan = (sonra.get('pinterestData') or {}).get('pinTitle')
            tum = [x for x in fark(once, sonra) if x not in ('pinterestData.pinTitle', 'id')]
            df = [x for x in tum if x not in IZINLI_FARK]
            ok = okunan == r['yeni_baslik'] and not df
            sonuc.append(dict(r, yeni_id=sonra.get('id'), okunan_baslik=okunan, diger_fark='|'.join(tum),
                              sonuc='PASS' if ok else 'FAIL'))
            w.writerow({x: sonuc[-1].get(x, '') for x in k}); f.flush()
            g = time.time() - t0
            print(f"[{i}/{len(sec)}] {r['id']} ({kaynak}) {sonuc[-1]['sonuc']} | gecen {g:.0f} sn, kalan ~{g / i * (len(sec) - i):.0f} sn, "
                  f"%{100 * i / len(sec):.0f}" + (f' fark: {df}' if df else ''), flush=True)
            if not ok:
                raise SystemExit(f"DUR: dogrulama FAIL {r['id']} (okunan={okunan!r}, fark={df})")
    n = sum(s['sonuc'] == 'PASS' for s in sonuc)
    print(f'DEGISEN {n}/{len(sec)} PASS, atlanan {sum(s["sonuc"].startswith("ATLANDI") for s in sonuc)}')


if __name__ == '__main__':
    main()
