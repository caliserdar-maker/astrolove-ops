#!/usr/bin/env python3
"""Metricool: TEK bekleyen video gonderisinin videosunu kapakli videoyla degistir (Serdar onayi 15 Eki 2026, 1 gonderi denemesi).

Akis (her adim FAIL -> DUR, PUT yapilmaz):
  1. GET /v2/scheduler/posts/{id} -> ONCE.json. Kapi: durum PENDING, yayina >= 2 sa, tek medya .mp4, ag = --ag, cift = --cift,
     videoThumbnailUrl dolu.
  2. Kapakli video (FINAL_KAPAKLI) Metricool S3 planner akisiyla yuklenir (metricool_5p_yaz.video_yukle) -> donusturulmus URL.
  3. Donusturulmus dosya indirilir ve olculur (kapak_basa.py olcumleri): ilk kare ~ kapak < 2.0, 0-1.5 sn her kare parlaklik
     >= kapak/2, 720 kare, 24.0 sn.
  4. PUT oncesi yeniden GET: ONCE ile ayni ve hala PENDING olmali.
  5. PUT /v2/scheduler/posts/{id}: ONCE govdesi, YALNIZ media[0] = yeni URL.
  6. GET -> SONRA.json; fark: izinli yalniz media[0] + Metricool'un kendi alanlari (creationDate, instagramData.type /
     showReelOnFeed: pin basligi PUT olcumu). videoThumbnailUrl ayni, durum PENDING, id ayni. Gonderideki medya yeniden
     indirilip ilk kare olculur.
Modlar: kuru (1, 3 yerine yerel dosya olcumu; yukleme ve PUT yok), yaz (1-6), geri (ONCE.json govdesiyle PUT: geri alma).
Token loga/dosyaya yazilmaz; presigned URL'ler maskelenir. Kullanim:
  metricool_video_degistir.py --token T.json --id 394635992 --ag facebook --cift PISCES_SAGITTARIUS --video V.mp4 --kapak K.jpg
                              --mod kuru|yaz|geri --cikti DIR [--once ONCE.json]"""
import argparse, copy, importlib.util, json, os, subprocess, sys
from datetime import datetime, timedelta

import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(D))
IZINLI = {'media[0]', 'creationDate.dateTime', 'creationDate.timezone', 'instagramData.type', 'instagramData.showReelOnFeed'}
MIN_SAAT = 2


def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def olc(kb, yol, kapak):
    """Videonun ilk kare / parlaklik / kare / sure olcumu (kapak_basa ile ayni esikler)."""
    v = kb.probe(yol)
    W, H = v['w'], v['h']
    K = kb.kapak_dizi(kapak, W, H)
    n = int(round(kb.KONTROL_SN * v['fps'])) + 1
    ilk = kb.kareler(yol, W, H, n)
    parl = [float(f.mean()) for f in ilk]
    q = {'boyut_px': f'{W}x{H}', 'kare': v['kare'], 'video_sn': v['video_sn'], 'ses_sn': v['ses_sn'], 'bayt': v['boyut'],
         'kapak_parlaklik': round(float(K.mean()), 1), 'ilk_kare_fark': round(float(np.abs(ilk[0] - K).mean()), 2),
         'min_parlaklik_0_1.5': round(min(parl), 1)}
    q['kapilar'] = {'ilk_kare': q['ilk_kare_fark'] < kb.ESIK, 'min_parlaklik': min(parl) >= float(K.mean()) / 2,
                    'kare': v['kare'] == 720, 'sure': abs(v['video_sn'] - 24.0) <= 0.05,
                    'ses': v['ses_sn'] is not None and abs(v['ses_sn'] - 24.0) <= 0.05}
    q['sonuc'] = 'PASS' if all(q['kapilar'].values()) else 'FAIL'
    return q


def durum(p, ag):
    pr = [x for x in p.get('providers') or [] if (x.get('network') or '').lower() == ag]
    return (pr[0].get('status') or '') if len(pr) == 1 and len(p.get('providers') or []) == 1 else f'AG? {p.get("providers")}'


def main():
    a = argparse.ArgumentParser()
    for k in ('token', 'id', 'ag', 'cift', 'mod', 'cikti'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--video', default=''); a.add_argument('--kapak', default=''); a.add_argument('--once', default='')
    o = a.parse_args()
    os.makedirs(o.cikti, exist_ok=True)
    yz = yukle('yz', os.path.join(D, 'metricool_5p_yaz.py'))
    sko = yukle('sko', os.path.join(D, 'sosyal_kapak_oku.py'))
    kb = yukle('kb', os.path.join(KOK, 'sosyal', 'video_v9', 'kapak_basa.py'))
    mpb = yz.mpb
    mc = mpb.MC(json.load(open(o.token)))
    rapor = {'id': o.id, 'ag': o.ag, 'cift': o.cift, 'mod': o.mod, 'basla': simdi_ist().strftime('%Y-%m-%dT%H:%M:%S'), 'adimlar': []}

    def kaydet():
        json.dump(rapor, open(os.path.join(o.cikti, 'DEGISTIR_RAPOR.json'), 'w'), ensure_ascii=False, indent=1)

    def dur(neden):
        rapor['sonuc'] = f'DUR: {neden}'
        kaydet()
        print(f'DUR: {neden}', flush=True)
        sys.exit(1)

    def adim(ad, **k):
        rapor['adimlar'].append(dict(ad=ad, **k)); kaydet()
        print(f'ADIM {ad}: ' + json.dumps(k, ensure_ascii=False, default=str)[:600], flush=True)

    def oku():
        p = mc.istek('GET', f'/v2/scheduler/posts/{o.id}', yok404=True)
        return None if p is mpb.YOK or p is None else mpb.veri(p)

    # 1) ONCE
    once = oku()
    if once is None:
        dur('gonderi bulunamadi (404)')
    if o.mod == 'geri':
        if not o.once:
            dur('geri: --once gerekli')
        geri = json.load(open(o.once))
        if str(geri.get('id')) != str(o.id):
            dur(f"geri: ONCE id {geri.get('id')} != {o.id}")
        if durum(once, o.ag) != 'PENDING':
            dur(f'geri: durum {durum(once, o.ag)}')
        mc.istek('PUT', f'/v2/scheduler/posts/{o.id}', govde=geri)
        son = oku()
        f = [x for x in mpb.fark(geri, son) if x not in IZINLI - {'media[0]'}] if son else ['GERI OKUNAMADI']
        adim('geri_put', fark=f, media=(son or {}).get('media'))
        rapor['sonuc'] = 'PASS' if not f else 'FAIL'
        kaydet(); print('SONUC', rapor['sonuc']); sys.exit(0 if not f else 1)
    json.dump(once, open(os.path.join(o.cikti, 'ONCE.json'), 'w'), ensure_ascii=False, indent=1)
    zaman = datetime.fromisoformat((once.get('publicationDate') or {}).get('dateTime'))
    tz = (once.get('publicationDate') or {}).get('timezone')
    c = sko.cift_bul(once)
    medya = once.get('media') or []
    kapi = {'durum_PENDING': durum(once, o.ag) == 'PENDING', 'saat_tz_istanbul': tz == 'Europe/Istanbul',
            f'yayina_>=_{MIN_SAAT}_sa': zaman - simdi_ist() >= timedelta(hours=MIN_SAAT),
            'tek_mp4_medya': len(medya) == 1 and isinstance(medya[0], str) and medya[0].split('?')[0].endswith('.mp4'),
            'cift': c is not None and '_'.join(x.upper() for x in c) == o.cift,
            'kapak_alani': bool(once.get('videoThumbnailUrl'))}
    adim('once', yayin=f'{zaman} {tz}', durum=durum(once, o.ag), cift=c, medya=[sko.kisa(m) for m in medya],
         kapak=sko.kisa(once.get('videoThumbnailUrl') or ''), kapilar=kapi)
    if not all(kapi.values()):
        dur('ONCE kapisi: ' + ', '.join(k for k, v in kapi.items() if not v))

    # 2-3) yukleme + donusturulmus dosya olcumu
    if o.mod == 'kuru':
        q = olc(kb, o.video, o.kapak)
        adim('kuru_yerel_olcum', **q)
        rapor['sonuc'] = 'KURU ' + q['sonuc']
        kaydet(); print('SONUC', rapor['sonuc']); sys.exit(0 if q['sonuc'] == 'PASS' else 1)
    yeni_url, yk = yz.video_yukle(mc, o.video)
    adim('yukleme', url=sko.kisa(yeni_url), boyut=yk['boyut'], prob=yk['prob'])
    if not sko.kisa(yeni_url).endswith('.mp4'):
        dur(f'yeni URL .mp4 degil: {sko.kisa(yeni_url)}')
    indir = os.path.join(o.cikti, '_donusturulmus.mp4')
    h = subprocess.run(['curl', '-sL', '-m', '300', '-o', indir, '-w', '%{http_code}', yeni_url], capture_output=True, text=True).stdout
    if h != '200':
        dur(f'donusturulmus dosya indirilemedi http {h}')
    q = olc(kb, indir, o.kapak)
    adim('donusturulmus_olcum', **q)
    if q['sonuc'] != 'PASS':
        dur('donusturulmus dosya kapisi: ' + ', '.join(k for k, v in q['kapilar'].items() if not v))

    # 4) PUT oncesi yeniden okuma
    tekrar = oku()
    f0 = mpb.fark(once, tekrar) if tekrar else ['OKUNAMADI']
    if f0 or durum(tekrar, o.ag) != 'PENDING' or simdi_ist() + timedelta(hours=MIN_SAAT) > zaman:
        dur(f'PUT oncesi degisiklik/durum: fark {f0}, durum {durum(tekrar, o.ag) if tekrar else "-"}')

    # 5) PUT (yalniz media[0])
    yeni = copy.deepcopy(once)
    yeni['media'][0] = yeni_url
    if mpb.fark(once, yeni) != ['media[0]']:
        dur(f'govde farki beklenmedik: {mpb.fark(once, yeni)}')
    y = mc.istek('PUT', f'/v2/scheduler/posts/{o.id}', govde=yeni, yok404=True)
    if y is mpb.YOK:
        dur('PUT 404 (yayinlanmis olabilir)')
    adim('put', yanit_anahtarlari=sorted(mpb.veri(y).keys()) if isinstance(mpb.veri(y), dict) else str(type(y)))

    # 6) GET + fark
    sonra = oku()
    if sonra is None:
        dur('PUT sonrasi gonderi okunamadi')
    json.dump(sonra, open(os.path.join(o.cikti, 'SONRA.json'), 'w'), ensure_ascii=False, indent=1)
    fk = mpb.fark(once, sonra)
    izinsiz = [x for x in fk if x not in IZINLI]
    m_sonra = (sonra.get('media') or [''])[0]
    kapi = {'izinsiz_fark_yok': not izinsiz, 'media0_yeni': m_sonra.split('?')[0] == yeni_url.split('?')[0],
            'kapak_ayni': sonra.get('videoThumbnailUrl') == once.get('videoThumbnailUrl'),
            'durum_PENDING': durum(sonra, o.ag) == 'PENDING', 'id_ayni': str(sonra.get('id')) == str(o.id),
            'saat_ayni': sonra.get('publicationDate') == once.get('publicationDate')}
    m2 = os.path.join(o.cikti, '_gonderideki.mp4')
    h = subprocess.run(['curl', '-sL', '-m', '300', '-o', m2, '-w', '%{http_code}', m_sonra], capture_output=True, text=True).stdout
    q2 = olc(kb, m2, o.kapak) if h == '200' else {'sonuc': f'INDIRILEMEDI http {h}'}
    kapi['gonderideki_video_PASS'] = q2['sonuc'] == 'PASS'
    adim('sonra', fark=fk, izinsiz=izinsiz, media=[sko.kisa(x) for x in sonra.get('media') or []],
         kapak=sko.kisa(sonra.get('videoThumbnailUrl') or ''), durum=durum(sonra, o.ag), gonderideki_video=q2, kapilar=kapi)
    rapor['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL: ' + ', '.join(k for k, v in kapi.items() if not v)
    kaydet()
    for f in ('_donusturulmus.mp4', '_gonderideki.mp4'):
        if os.path.exists(os.path.join(o.cikti, f)):
            os.remove(os.path.join(o.cikti, f))
    print('SONUC', rapor['sonuc'], flush=True)
    sys.exit(0 if rapor['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
