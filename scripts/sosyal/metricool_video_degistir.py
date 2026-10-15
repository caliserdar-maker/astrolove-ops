#!/usr/bin/env python3
"""Metricool: TEK bekleyen video gonderisinin videosunu kapakli videoyla degistir (Serdar onayi 15 Eki 2026, 1 gonderi denemesi).

Olcum (15 Eki, 38712850093): PUT /v2/scheduler/posts/{id} gonderiye YENI id verir (394635992 -> 396651816), uuid ayni kalir.
Bu yuzden gonderi her zaman bul(): once id ile GET, 404 ise yayin gununun +-1 gun listesinden uuid ile aranir.
Izinli fark YALNIZ id ve media[0] (Serdar 15 Eki); metin, kapak, saat, durum, ag alanlari, saglayicilar, taslak ve
otomatik yayin dahil her baska fark = FAIL.

Akis, mod yaz (her adim FAIL -> DUR, PUT yapilmaz):
  1. bul() -> ONCE.json. Kapi: durum PENDING, yayina >= 2 sa, tek medya .mp4, ag = --ag, cift = --cift, kapak dolu.
  2. Kapakli video Metricool S3 planner akisiyla yuklenir (metricool_5p_yaz.video_yukle) -> donusturulmus URL.
  3. Donusturulmus dosya olculur (kapak_basa esikleri): ilk kare ~ kapak < 2.0, 0-1.5 sn parlaklik >= kapak/2, 720 kare, 24 sn.
  4. PUT oncesi yeniden bul(): ONCE ile ayni ve PENDING olmali.
  5. PUT: ONCE govdesi, YALNIZ media[0] = yeni URL.
  6. bul() (uuid) -> SONRA.json; tam fark tablosu (FARK.csv); gonderideki video yeniden olculur.
Diger modlar:
  kuru    : 1 + yerel dosya olcumu; yukleme / PUT yok.
  kontrol : SALT OKUMA. --once ONCE.json; gonderi uuid ile bulunur, tam govde ONCE ile alan alan karsilastirilir
            (SIMDI.json, FARK.csv, KONTROL_RAPOR.json). Metricool'a hicbir yazma yok.
  geri    : ONCE govdesini (id = guncel id) PUT eder; gonderi uuid ile bulunur, ardindan tam fark (izinli yalniz id).
Token loga/dosyaya yazilmaz; presigned URL'ler maskelenir. Kullanim:
  metricool_video_degistir.py --token T.json --id 394635992 --ag facebook --cift PISCES_SAGITTARIUS --video V.mp4 --kapak K.jpg
                              --mod kuru|yaz|kontrol|geri --cikti DIR [--once ONCE.json] [--uuid U]"""
import argparse, copy, csv, importlib.util, json, os, subprocess, sys
from datetime import datetime, timedelta

import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(D))
IZINLI = {'id', 'media[0]'}
MIN_SAAT = 2
TZ = 'Europe/Istanbul'


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


def bul(mc, mpb, pid, uuid, tarih):
    """Gonderi: uuid + tarih varsa HER ZAMAN tarih +-1 gun listesinde uuid ile (kopya kontrolu: birden fazla -> DUR);
    yoksa id ile tekil GET. (govde, yol) ya da (None, sebep)."""
    if not uuid or not tarih:
        if pid:
            p = mc.istek('GET', f'/v2/scheduler/posts/{pid}', yok404=True)
            if p is not mpb.YOK and p is not None:
                p = mpb.veri(p)
                if not uuid or str(p.get('uuid')) == str(uuid):
                    return p, 'id'
        return None, 'id ile bulunamadi, uuid/tarih yok'
    t = datetime.fromisoformat(tarih)
    liste = mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': (t - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                                                            'end': (t + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                                                            'timezone': TZ})) or []
    m = [x for x in liste if str(x.get('uuid')) == str(uuid)]
    if len(m) > 1:
        raise SystemExit(f'DUR: uuid {uuid} icin {len(m)} gonderi (kopya?): {[x.get("id") for x in m]}')
    return (m[0], 'uuid') if m else (None, f'uuid {uuid} listede yok ({len(liste)} gonderi)')


def deger(x, yol):
    """'a.b[0].c' yolundaki deger (yoksa '<yok>')."""
    import re
    for parca in re.findall(r'[^.\[\]]+|\[\d+\]', yol):
        if parca.startswith('['):
            i = int(parca[1:-1])
            x = x[i] if isinstance(x, list) and i < len(x) else '<yok>'
        else:
            x = x.get(parca, '<yok>') if isinstance(x, dict) else '<yok>'
        if x == '<yok>':
            break
    return x


def fark_tablosu(mpb, sko, once, simdi, cikti):
    """Alan alan fark: (satirlar, izinsiz). FARK.csv yazar. URL'ler sorgusuz."""
    def k(v):
        return sko.kisa(v) if isinstance(v, str) and v.startswith('http') else json.dumps(v, ensure_ascii=False, default=str)[:300]
    yollar = mpb.fark(once, simdi)
    satir = [{'alan': y, 'once': k(deger(once, y)), 'simdi': k(deger(simdi, y)), 'izinli': y in IZINLI} for y in yollar]
    with open(os.path.join(cikti, 'FARK.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, ['alan', 'once', 'simdi', 'izinli']); w.writeheader(); [w.writerow(r) for r in satir]
    return satir, [r['alan'] for r in satir if not r['izinli']]


def main():
    a = argparse.ArgumentParser()
    for k in ('token', 'ag', 'cift', 'mod', 'cikti'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--id', default=''); a.add_argument('--uuid', default='')
    a.add_argument('--video', default=''); a.add_argument('--kapak', default=''); a.add_argument('--once', default='')
    o = a.parse_args()
    os.makedirs(o.cikti, exist_ok=True)
    yz = yukle('yz', os.path.join(D, 'metricool_5p_yaz.py'))
    sko = yukle('sko', os.path.join(D, 'sosyal_kapak_oku.py'))
    mpb = yz.mpb
    mc = mpb.MC(json.load(open(o.token)))
    ad = 'KONTROL_RAPOR.json' if o.mod == 'kontrol' else 'DEGISTIR_RAPOR.json'
    rapor = {'id': o.id, 'uuid': o.uuid, 'ag': o.ag, 'cift': o.cift, 'mod': o.mod, 'izinli_fark': sorted(IZINLI),
             'basla': simdi_ist().strftime('%Y-%m-%dT%H:%M:%S'), 'adimlar': []}

    def kaydet():
        json.dump(rapor, open(os.path.join(o.cikti, ad), 'w'), ensure_ascii=False, indent=1)

    def dur(neden):
        rapor['sonuc'] = f'DUR: {neden}'
        kaydet()
        print(f'DUR: {neden}', flush=True)
        sys.exit(1)

    def adim(ad_, **k):
        rapor['adimlar'].append(dict(ad=ad_, **k)); kaydet()
        print(f'ADIM {ad_}: ' + json.dumps(k, ensure_ascii=False, default=str)[:900], flush=True)

    def bul_(*x):
        try:
            return bul(mc, mpb, *x)
        except SystemExit as e:   # uuid kopyasi
            dur(str(e).replace('DUR: ', ''))

    def bitir(kapi):
        rapor['kapilar'] = kapi
        rapor['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL: ' + ', '.join(k for k, v in kapi.items() if not v)
        kaydet(); print('SONUC', rapor['sonuc'], flush=True)
        sys.exit(0 if rapor['sonuc'] == 'PASS' else 1)

    # --- kontrol / geri: ONCE.json'dan uuid ve tarih ---
    if o.mod in ('kontrol', 'geri'):
        if not o.once:
            dur(f'{o.mod}: --once gerekli')
        ref = json.load(open(o.once))
        uuid = o.uuid or str(ref.get('uuid') or '')
        if o.uuid and str(ref.get('uuid')) != o.uuid:
            dur(f"ONCE uuid {ref.get('uuid')} != --uuid {o.uuid}")
        tarih = (ref.get('publicationDate') or {}).get('dateTime')
        simdi, yol = bul_(o.id, uuid, tarih)
        if simdi is None:
            dur(f'gonderi bulunamadi: {yol}')
        adim('bul', yol=yol, id_once=ref.get('id'), id_simdi=simdi.get('id'), uuid=simdi.get('uuid'), durum=durum(simdi, o.ag))
        if o.mod == 'kontrol':
            json.dump(simdi, open(os.path.join(o.cikti, 'SIMDI.json'), 'w'), ensure_ascii=False, indent=1)
            satir, izinsiz = fark_tablosu(mpb, sko, ref, simdi, o.cikti)
            adim('fark', alan_sayisi=len(satir), izinsiz=izinsiz, tablo=satir)
            bitir({'izinsiz_fark_yok': not izinsiz, 'uuid_ayni': str(simdi.get('uuid')) == uuid,
                   'durum_PENDING': durum(simdi, o.ag) == 'PENDING'})
        # geri
        if durum(simdi, o.ag) != 'PENDING':
            dur(f'geri: durum {durum(simdi, o.ag)}')
        if datetime.fromisoformat(tarih) - simdi_ist() < timedelta(hours=MIN_SAAT):
            dur(f'geri: yayina {MIN_SAAT} saatten az')
        govde = copy.deepcopy(ref); govde['id'] = simdi.get('id')
        mc.istek('PUT', f"/v2/scheduler/posts/{simdi.get('id')}", govde=govde)
        son, yol = bul_('', uuid, tarih)
        if son is None:
            dur(f'geri sonrasi bulunamadi: {yol}')
        json.dump(son, open(os.path.join(o.cikti, 'GERI_SONRA.json'), 'w'), ensure_ascii=False, indent=1)
        satir, _ = fark_tablosu(mpb, sko, ref, son, o.cikti)
        izinsiz = [r['alan'] for r in satir if r['alan'] != 'id']
        adim('geri', id_simdi=son.get('id'), media=[sko.kisa(x) for x in son.get('media') or []], izinsiz=izinsiz)
        bitir({'once_ile_ayni': not izinsiz, 'durum_PENDING': durum(son, o.ag) == 'PENDING'})

    # --- kuru / yaz ---
    kb = yukle('kb', os.path.join(KOK, 'sosyal', 'video_v9', 'kapak_basa.py'))
    once, yol = bul_(o.id, o.uuid, '')
    if once is None:
        dur(f'gonderi bulunamadi: {yol}')
    json.dump(once, open(os.path.join(o.cikti, 'ONCE.json'), 'w'), ensure_ascii=False, indent=1)
    uuid = str(once.get('uuid') or '')
    zaman = datetime.fromisoformat((once.get('publicationDate') or {}).get('dateTime'))
    tz = (once.get('publicationDate') or {}).get('timezone')
    c = sko.cift_bul(once)
    medya = once.get('media') or []
    kapi = {'durum_PENDING': durum(once, o.ag) == 'PENDING', 'saat_tz_istanbul': tz == TZ,
            f'yayina_>=_{MIN_SAAT}_sa': zaman - simdi_ist() >= timedelta(hours=MIN_SAAT),
            'tek_mp4_medya': len(medya) == 1 and isinstance(medya[0], str) and medya[0].split('?')[0].endswith('.mp4'),
            'cift': c is not None and '_'.join(x.upper() for x in c) == o.cift,
            'kapak_alani': bool(once.get('videoThumbnailUrl')), 'uuid_var': bool(uuid)}
    adim('once', yol=yol, id=once.get('id'), uuid=uuid, yayin=f'{zaman} {tz}', durum=durum(once, o.ag), cift=c,
         medya=[sko.kisa(m) for m in medya], kapak=sko.kisa(once.get('videoThumbnailUrl') or ''), kapilar=kapi)
    if not all(kapi.values()):
        dur('ONCE kapisi: ' + ', '.join(k for k, v in kapi.items() if not v))
    if o.mod == 'kuru':
        q = olc(kb, o.video, o.kapak)
        adim('kuru_yerel_olcum', **q)
        bitir({'yerel_olcum': q['sonuc'] == 'PASS'})
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
    tekrar, _ = bul_(str(once.get('id')), uuid, zaman.isoformat())
    f0 = mpb.fark(once, tekrar) if tekrar else ['OKUNAMADI']
    if f0 or durum(tekrar, o.ag) != 'PENDING' or simdi_ist() + timedelta(hours=MIN_SAAT) > zaman:
        dur(f'PUT oncesi degisiklik/durum: fark {f0}, durum {durum(tekrar, o.ag) if tekrar else "-"}')
    yeni = copy.deepcopy(once)
    yeni['media'][0] = yeni_url
    if mpb.fark(once, yeni) != ['media[0]']:
        dur(f'govde farki beklenmedik: {mpb.fark(once, yeni)}')
    y = mc.istek('PUT', f"/v2/scheduler/posts/{once.get('id')}", govde=yeni, yok404=True)
    if y is mpb.YOK:
        dur('PUT 404 (yayinlanmis olabilir)')
    adim('put', yanit_id=(mpb.veri(y) or {}).get('id') if isinstance(mpb.veri(y), dict) else None)
    sonra, yol = bul_(str(once.get('id')), uuid, zaman.isoformat())
    if sonra is None:
        dur(f'PUT sonrasi gonderi bulunamadi: {yol}')
    json.dump(sonra, open(os.path.join(o.cikti, 'SONRA.json'), 'w'), ensure_ascii=False, indent=1)
    satir, izinsiz = fark_tablosu(mpb, sko, once, sonra, o.cikti)
    m_sonra = (sonra.get('media') or [''])[0]
    m2 = os.path.join(o.cikti, '_gonderideki.mp4')
    h = subprocess.run(['curl', '-sL', '-m', '300', '-o', m2, '-w', '%{http_code}', m_sonra], capture_output=True, text=True).stdout
    q2 = olc(kb, m2, o.kapak) if h == '200' else {'sonuc': f'INDIRILEMEDI http {h}'}
    adim('sonra', yol=yol, id_yeni=sonra.get('id'), tablo=satir, izinsiz=izinsiz, gonderideki_video=q2)
    for f in ('_donusturulmus.mp4', '_gonderideki.mp4'):
        if os.path.exists(os.path.join(o.cikti, f)):
            os.remove(os.path.join(o.cikti, f))
    bitir({'izinsiz_fark_yok': not izinsiz, 'media0_yeni': m_sonra.split('?')[0] == yeni_url.split('?')[0],
           'durum_PENDING': durum(sonra, o.ag) == 'PENDING', 'uuid_ayni': str(sonra.get('uuid')) == uuid,
           'gonderideki_video_PASS': q2['sonuc'] == 'PASS'})


if __name__ == '__main__':
    main()
