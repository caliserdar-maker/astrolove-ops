#!/usr/bin/env python3
"""Bekleyen TikTok + YouTube video gonderilerinde video degisimi (Serdar onayi 20 Eki 2026): acilisi siyah eski video ->
SOSYAL_VIDEO_P_78_20261020 P acilisli video. YAZAR (Metricool PUT); yalniz bekleyen TikTok/YouTube gonderisi, yalniz media[0]
(YouTube'da ek olarak videoThumbnailUrl = yeni videonun ilk karesi, P karesi).
Akis (cift basina, yayin sirasina gore):
  1. Guncel liste: GET /v2/scheduler/posts (simdi -> 31 Oca 2027), providers[tiktok|youtube] PENDING; cift metin/baslikta 'X and|& Y'.
     Cift basina tam 1 TikTok + 1 YouTube olmali; medya[0] ESLEME.csv'deki eski URL olmali (degilse ATLANDI: zaten degismis?).
     Yayina < 2 sa + PAY dk kalan cift ATLANDI. Onceki SONUC.csv'de PASS olan cift atlanir (yeniden calistirma).
  2. P videosunun 0. karesi -> kapak jpg (ffmpeg, q 2). metricool_video_degistir.py --mod yaz --hedef tiktok:id:uuid,youtube:id:uuid
     --video P.mp4 --kapak ilk_kare.jpg --yt-kapak ilk_kare.jpg: tek video + tek kapak yuklemesi, donusturulmus dosya kapisi,
     PUT, uuid ile geri okuma (izinsiz fark yok = metin, tarih, saat, durum ayni; video yeni; YouTube kapagi yeni; gonderideki video PASS).
  3. Bir cift FAIL -> DUR (sonraki ciftlere gecilmez). mod tek: yalniz ilk uygun cift.
Cikti: CIKTI/SONUC.csv, CIKTI/OZET.txt, CIKTI/<CIFT>/ (DEGISTIR_RAPOR.json, <uuid>/ONCE.json, SONRA.json, FARK.csv).
Kullanim: tt_yt_video_uygula.py TOKEN.json CIKTI VIDEO_DIR ESLEME.csv --mod tek|hepsi [--onceki SONUC.csv]"""
import argparse
import csv
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('mpb', os.path.join(D, 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)

TZ = 'Europe/Istanbul'
SON = datetime(2027, 1, 31)
MIN_SAAT, PAY_DK = 2, 20      # degistir betigi de >= 2 sa ister; PAY: yukleme + olcum suresi
AGLAR = ('tiktok', 'youtube')
BURC = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn',
        'aquarius', 'pisces')
BAS = ['cift', 'ag', 'yayin', 'uuid', 'id_once', 'id_sonra', 'medya_once', 'medya_sonra', 'kapak_once', 'kapak_sonra',
       'metin_ayni', 'tarih_saat_ayni', 'uuid_ayni', 'video_yeni', 'kapak_yeni', 'izinsiz_fark', 'gonderideki_video', 'sonuc',
       'neden', 'kosu_zamani']
OZET = None


def log(s):
    print(s, flush=True)
    with open(OZET, 'a', encoding='utf-8') as f:
        f.write(s + '\n')


def simdi():
    return datetime.now(ZoneInfo(TZ)).replace(tzinfo=None)


def kisa(u):
    return (u or '').split('?')[0]


def cift_ad(p):
    b = '|'.join(BURC)
    for t in ((p.get('youtubeData') or {}).get('title'), p.get('text')):
        m = re.search(r'\b(' + b + r')\s*(?:&|and)\s*(' + b + r')\b', (t or '').lower())
        if m:
            return '_'.join(sorted((m.group(1).upper(), m.group(2).upper())))
    return ''


def m0(p):
    m = (p.get('media') or [''])[0]
    return kisa(m if isinstance(m, str) else (m or {}).get('url', ''))


def jl(yol):
    return json.load(open(yol)) if os.path.exists(yol) else {}


def main():
    global OZET
    a = argparse.ArgumentParser()
    a.add_argument('token'); a.add_argument('cikti'); a.add_argument('video_dir'); a.add_argument('esleme')
    a.add_argument('--mod', choices=['tek', 'hepsi'], required=True); a.add_argument('--onceki', default='')
    o = a.parse_args()
    os.makedirs(o.cikti, exist_ok=True)
    OZET = os.path.join(o.cikti, 'OZET.txt')
    open(OZET, 'a').close()
    kosu = simdi().strftime('%Y-%m-%dT%H:%M:%S')
    mc = mpb.MC(json.load(open(o.token)))
    log(f'=== KOSU {kosu} (Istanbul) mod {o.mod}; blogId {mc.b}')

    eski = defaultdict(dict)    # cift -> ag -> eski medya URL (ESLEME.csv, 20 Eki 17:03 okumasi)
    for r in csv.DictReader(open(o.esleme, encoding='utf-8')):
        eski[r['cift']][r['ag']] = kisa(r['medya_url'])
    onceki = list(csv.DictReader(open(o.onceki, encoding='utf-8'))) if o.onceki and os.path.exists(o.onceki) else []
    tamam = {c for c, n in Counter(r['cift'] for r in onceki if r['sonuc'] == 'PASS').items() if n == 2}
    log(f'ESLEME: {len(eski)} cift; onceki SONUC: {len(onceki)} satir, iki agda PASS cift {len(tamam)}')

    # 1) guncel bekleyenler
    ps, t = {}, simdi().replace(minute=0, second=0, microsecond=0)
    while t < SON:
        e = min(t + timedelta(days=3), SON)
        ls = mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}',
                                                              'timezone': TZ}))
        ls = ls if isinstance(ls, list) else []
        if len(ls) >= 100:
            sys.exit(f'DUR: {t:%Y-%m-%d} penceresinde {len(ls)} kayit (kesilmis olabilir)')
        for p in ls:
            ps[str(p.get('id'))] = p
        t = e
    grup = defaultdict(list)
    for p in ps.values():
        pr = p.get('providers') or []
        ag = (pr[0].get('network') or '').lower() if len(pr) == 1 else ''
        if ag in AGLAR and (pr[0].get('status') or '') == 'PENDING':
            z = datetime.fromisoformat(((p.get('publicationDate') or {}).get('dateTime') or '')[:19])
            if z > simdi():
                grup[cift_ad(p)].append((z, ag, p))
    log(f'GUNCEL bekleyen TikTok/YouTube: {sum(len(v) for v in grup.values())} gonderi, {len(grup)} cift '
        f'(cift bos: {len(grup.get("", []))})')

    satirlar = [r for r in onceki if r['sonuc'] != 'ATLANDI']   # ATLANDI her kosuda yeniden hesaplanir
    plan = []
    for c, g in sorted(grup.items(), key=lambda kv: min(x[0] for x in kv[1])):
        z = min(x[0] for x in g)
        neden = ''
        if not c:
            neden = 'cift okunamadi'
        elif sorted(x[1] for x in g) != list(AGLAR):
            neden = f'cift basina 1 TikTok + 1 YouTube degil: {sorted(x[1] for x in g)}'
        elif c in tamam:
            continue
        elif any(m0(p) != eski.get(c, {}).get(ag, '?') for _, ag, p in g):
            neden = 'medya[0] ESLEME.csv eski URL ile ayni degil (zaten degismis ya da baska degisiklik)'
        elif z - simdi() < timedelta(hours=MIN_SAAT, minutes=PAY_DK):
            neden = f'yayina {MIN_SAAT} sa {PAY_DK} dk dan az'
        elif not os.path.exists(os.path.join(o.video_dir, f"{c.lower().replace('_', '-and-')}-astroloveart-reel.mp4")):
            neden = 'P videosu yok'
        if neden:
            for zz, ag, p in sorted(g, key=lambda x: x[1]):
                satirlar.append([c, ag, f'{zz:%Y-%m-%d %H:%M}', p.get('uuid'), p.get('id'), '', m0(p), '', kisa(p.get('videoThumbnailUrl')),
                                 '', '', '', '', '', '', '', '', 'ATLANDI', neden, kosu])
            log(f'ATLANDI {c or "?"} {z:%Y-%m-%d %H:%M}: {neden}')
        else:
            plan.append((z, c, sorted(g, key=lambda x: x[1])))
    log(f'PLAN: {len(plan)} cift ({2 * len(plan)} gonderi); ilk {plan[0][0]:%Y-%m-%d %H:%M} {plan[0][1]}' if plan else 'PLAN: uygun cift yok')
    if o.mod == 'tek':
        plan = plan[:1]

    def yaz_sonuc():
        with open(os.path.join(o.cikti, 'SONUC.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(BAS)
            for r in satirlar:
                w.writerow([r.get(k, '') for k in BAS] if isinstance(r, dict) else r)
    yaz_sonuc()

    # 2) cift cift uygula
    t0, dur = time.time(), ''
    for i, (z, c, g) in enumerate(plan, 1):
        v = os.path.join(o.video_dir, f"{c.lower().replace('_', '-and-')}-astroloveart-reel.mp4")
        cd = os.path.join(o.cikti, c)
        os.makedirs(cd, exist_ok=True)
        kapak = os.path.join(cd, '_ilk_kare.jpg')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', v, '-frames:v', '1', '-q:v', '2', kapak], check=True)
        hedef = ','.join(f"{ag}:{p.get('id')}:{p.get('uuid')}" for _, ag, p in g)
        r = subprocess.run([sys.executable, os.path.join(D, 'metricool_video_degistir.py'), '--token', o.token, '--cift', c, '--mod', 'yaz',
                            '--hedef', hedef, '--video', v, '--kapak', kapak, '--yt-kapak', kapak, '--cikti', cd],
                           capture_output=True, text=True)
        satir_log = (r.stdout + r.stderr).splitlines()
        for s in satir_log:
            if s.startswith('::add-mask::'):
                print(s, flush=True)       # presigned URL maskesi Actions'a iletilir, dosyalara yazilmaz
        with open(os.path.join(cd, 'kosu_log.txt'), 'w') as f:
            f.write('\n'.join(s for s in satir_log if not s.startswith('::add-mask::')) + '\n')
        rp = jl(os.path.join(cd, 'DEGISTIR_RAPOR.json'))
        for zz, ag, p in g:
            u = str(p.get('uuid'))
            gr = (rp.get('gonderiler') or {}).get(u, {})
            once, sonra = jl(os.path.join(cd, u, 'ONCE.json')), jl(os.path.join(cd, u, 'SONRA.json'))
            kp = gr.get('kapilar') or {}
            fk = {x['alan'] for x in gr.get('fark') or []}
            satirlar.append([c, ag, f'{zz:%Y-%m-%d %H:%M}', u, p.get('id'), sonra.get('id', ''), m0(once or p), m0(sonra) if sonra else '',
                             kisa((once or p).get('videoThumbnailUrl')), kisa(sonra.get('videoThumbnailUrl')) if sonra else '',
                             ('evet' if 'text' not in fk else 'HAYIR') if sonra else '',
                             ('evet' if not any(x.startswith('publicationDate') for x in fk) else 'HAYIR') if sonra else '',
                             'evet' if kp.get('uuid_ayni') else ('HAYIR' if sonra else ''), 'evet' if kp.get('media0_yeni') else ('HAYIR' if sonra else ''),
                             ('evet' if kp.get('yt_kapak_yeni') else 'HAYIR') if ag == 'youtube' and sonra else ('degismedi (yalniz media[0])' if sonra else ''),
                             ', '.join(x['alan'] for x in gr.get('fark') or [] if not x['izinli']),
                             (gr.get('gonderideki_video') or {}).get('sonuc', ''), gr.get('sonuc') or ('FAIL' if r.returncode else ''),
                             '' if gr.get('sonuc') == 'PASS' else (rp.get('sonuc') or f'rc {r.returncode}')[:300], kosu])
        yaz_sonuc()
        g_ = time.time() - t0
        sonuc = 'PASS' if r.returncode == 0 and rp.get('sonuc') == 'PASS' else 'FAIL'
        log(f'[{i}/{len(plan)} {100 * i // len(plan)}%] {c} {z:%Y-%m-%d %H:%M}: {sonuc} ({rp.get("sonuc", "rapor yok")[:160]}); '
            f'gecen {g_ / 60:.1f} dk, kalan ~{g_ / i * (len(plan) - i) / 60:.1f} dk')
        if sonuc != 'PASS':
            dur = f'{c}: {rp.get("sonuc") or r.stderr[-300:]}'
            break
        kp_ = os.path.join(cd, '_ilk_kare.jpg')
        os.replace(kp_, os.path.join(cd, 'P_ilk_kare.jpg'))

    son = list(csv.DictReader(open(os.path.join(o.cikti, 'SONUC.csv'), encoding='utf-8')))
    log(f'SONUC.csv: {len(son)} satir; {dict(Counter((r["ag"], r["sonuc"]) for r in son))}')
    log(f'Bu kosu: {len(plan)} cift planlandi; ' + (f'DUR: {dur}' if dur else 'hepsi PASS'))
    sys.exit(1 if dur else 0)


if __name__ == '__main__':
    main()
