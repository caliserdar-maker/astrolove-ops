#!/usr/bin/env python3
"""Bekleyen IG Reels kapagi (videoThumbnailUrl) -> yeni videonun ilk karesi (P karesi). Serdar ek onayi 20 Eki 2026.
YAZAR (Metricool PUT); yalniz videoThumbnailUrl degisir. Video, metin, tarih, Reel turu, showReelOnFeed DEGISMEZ.
Hedefler: SOSYAL_DEGISIM_20261020/UYGULAMA_IG_FB/SONUC.csv'de ag=instagram, sonuc=PASS (Reels P videosu yazilmis 70 gonderi).
Gonderi basina (yayin sirasina gore):
  1. uuid + tarih ile guncel gonderi (metricool_video_degistir.bul). ONCE kapisi: PENDING, tek saglayici instagram,
     instagramData.type REEL, tek mp4 ve media[0] == SONUC.csv yeni_media (P videosu), cift metinde, yayina >= 2 sa + PAY.
     Mevcut kapak zaten P karesiyse (fark < ESIK) ZATEN.
  2. P karesi = Drive SOSYAL_VIDEO_P_78_20261020/<a>-and-<b>-astroloveart-reel.mp4 0. karesi (ffmpeg, q 1; FB kapagi ile ayni
     yontem). Metricool'a jpg yuklenir (metricool_5p_yaz.video_yukle), indirilen kapak - yerel kare < ESIK.
  3. PUT: ONCE govdesi, yalniz videoThumbnailUrl (govde farki tam olarak ['videoThumbnailUrl']).
  4. uuid ile geri okuma: izinli fark yalniz id, creationDate.*, videoThumbnailUrl; kapak URL'si yeni; indirilen kapak - P karesi
     < ESIK; durum PENDING; uuid ayni; media[0] ayni. Ilk FAIL -> DUR (sonraki gonderiye gecilmez).
Mod: tek (yayini >= 1 gun sonra olan en erken gonderi ya da --cift), kalan (geri kalanlar; ZATEN olanlar atlanir).
Cikti: CIKTI/SONUC.csv (kosular birikir), CIKTI/OZET.txt, CIKTI/<CIFT>/ (ONCE.json, SONRA.json, FARK.csv).
Kullanim: ig_kapak_degistir.py --token T --hedef SONUC_IG_FB.csv --video-dir gdrive:... --mod tek|kalan [--cift A_B]
          --cikti DIR --is DIR [--onceki SONUC.csv]"""
import argparse, copy, csv, importlib.util, json, os, re, subprocess, sys, time
from collections import Counter
from datetime import timedelta

D = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(D))
PAY_DK = 15
ALAN = ['zaman_ist', 'mod', 'cift', 'yayin', 'uuid', 'id_once', 'id_sonra', 'media0', 'kapak_once', 'kapak_sonra', 'kapak_fark',
        'izinsiz_fark', 'sonuc', 'neden']


def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def izinli(yol):
    return yol in ('id', 'videoThumbnailUrl') or yol.startswith('creationDate.')


def main():
    a = argparse.ArgumentParser()
    for k in ('token', 'hedef', 'video-dir', 'mod', 'cikti', 'is'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--cift', default=''); a.add_argument('--onceki', default='')
    o = a.parse_args()
    isd = getattr(o, 'is')
    for d in (o.cikti, isd):
        os.makedirs(d, exist_ok=True)
    mvd = yukle('mvd', os.path.join(D, 'metricool_video_degistir.py'))
    yz = yukle('yz', os.path.join(D, 'metricool_5p_yaz.py'))
    sko = yukle('sko', os.path.join(D, 'sosyal_kapak_oku.py'))
    kb = yukle('kb', os.path.join(KOK, 'sosyal', 'video_v9', 'kapak_basa.py'))
    mpb = yz.mpb
    mc = mpb.MC(json.load(open(o.token)))
    ozet = open(os.path.join(o.cikti, 'OZET.txt'), 'a', encoding='utf-8')

    def log(s):
        print(s, flush=True); ozet.write(s + '\n'); ozet.flush()

    satirlar = list(csv.DictReader(open(o.onceki, encoding='utf-8'))) if o.onceki and os.path.exists(o.onceki) else []

    def satir(**k):
        satirlar.append(dict({'zaman_ist': mvd.simdi_ist().strftime('%Y-%m-%dT%H:%M:%S'), 'mod': o.mod}, **k))
        with open(os.path.join(o.cikti, 'SONUC.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, ALAN, extrasaction='ignore'); w.writeheader(); w.writerows(satirlar)

    hed = {}
    for r in csv.DictReader(open(o.hedef, encoding='utf-8')):
        if r['ag'] == 'instagram' and r['sonuc'] == 'PASS':
            hed[r['uuid']] = r
    hed = sorted(hed.values(), key=lambda r: r['yayin'])
    log(f'=== {mvd.simdi_ist():%Y-%m-%d %H:%M} mod {o.mod}: hedef IG Reels (UYGULAMA_IG_FB PASS): {len(hed)}')
    if o.mod == 'tek':
        esik = (mvd.simdi_ist() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
        hed = [r for r in hed if r['cift'] == o.cift] if o.cift else [r for r in hed if r['yayin'] >= esik][:1]
    elif o.mod != 'kalan':
        sys.exit(f'DUR: mod {o.mod}')
    if not hed:
        sys.exit('DUR: hedef yok')

    t0 = time.time()
    for i, r in enumerate(hed, 1):
        c, uuid, yayin = r['cift'], r['uuid'], r['yayin'][:19]
        k = dict(cift=c, yayin=yayin, uuid=uuid)

        def dur(neden, **e):
            satir(**k, **e, sonuc='FAIL', neden=neden)
            log(f'DUR: {i}/{len(hed)} {c}: {neden} (sonraki gonderilere gecilmedi)')
            sys.exit(1)

        if mvd.datetime.fromisoformat(yayin) - mvd.simdi_ist() < timedelta(hours=mvd.MIN_SAAT, minutes=PAY_DK):
            satir(**k, sonuc='ATLANDI', neden=f'yayina {mvd.MIN_SAAT} sa + {PAY_DK} dk dan az'); continue
        once, yol = mvd.bul(mc, mpb, '', uuid, yayin)
        if once is None:
            dur(f'bulunamadi: {yol}')
        m = once.get('media') or []
        kapi = {'durum_PENDING': mvd.durum(once, 'instagram') == 'PENDING',
                'reel': (once.get('instagramData') or {}).get('type') == 'REEL',
                'media0_P_videosu': len(m) == 1 and m[0].split('?')[0] == r['yeni_media'].split('?')[0],
                'cift': mvd.cift_esit(sko, once, c), 'kapak_alani': bool(once.get('videoThumbnailUrl'))}
        k.update(id_once=once.get('id'), media0=sko.kisa(m[0] if m else ''), kapak_once=sko.kisa(once.get('videoThumbnailUrl') or ''))
        if not all(kapi.values()):
            dur('ONCE kapisi: ' + ', '.join(x for x, v in kapi.items() if not v))
        d = os.path.join(o.cikti, c)
        os.makedirs(d, exist_ok=True)
        json.dump(once, open(os.path.join(d, 'ONCE.json'), 'w'), ensure_ascii=False, indent=1)

        s = c.lower().replace('_', '-and-')
        vid, kap = os.path.join(isd, f'{c}.mp4'), os.path.join(isd, f'{c}_P.jpg')
        subprocess.run(['rclone', 'copyto', f'{o.video_dir}/{s}-astroloveart-reel.mp4', vid, '-q'], check=True, timeout=600)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', vid, '-frames:v', '1', '-q:v', '1', kap], check=True)
        os.remove(vid)
        f0 = mvd.kapak_fark(kb, once['videoThumbnailUrl'], kap, os.path.join(isd, '_k0.jpg'))
        if isinstance(f0, float) and f0 < kb.ESIK:
            satir(**k, sonuc='ZATEN', kapak_fark=f0, neden='mevcut kapak zaten P karesi'); os.remove(kap); continue

        for dn in range(3):   # kalan 39470805566: S3 PUT 'handshake operation timed out' (gonderiye yazmadan once)
            try:
                kurl, kk = yz.video_yukle(mc, kap, 'image/jpeg', 'jpg')
                break
            except Exception as x:
                log(f'  {c}: kapak yukleme {dn + 1}/3 hata {type(x).__name__}: {str(x)[:120]}')
                if dn == 2:
                    dur(f'kapak yuklenemedi: {type(x).__name__} (yazilmadi)')
                time.sleep(10 * (dn + 1))
        f1 = mvd.kapak_fark(kb, kurl, kap, os.path.join(isd, '_k1.jpg'))
        if not isinstance(f1, float) or f1 >= kb.ESIK:
            dur(f'yuklenen kapak farki {f1} (yazilmadi)')
        tekrar, _ = mvd.bul(mc, mpb, str(once.get('id')), uuid, yayin)
        if tekrar is None or mpb.fark(once, tekrar) or mvd.simdi_ist() + timedelta(hours=mvd.MIN_SAAT) > mvd.datetime.fromisoformat(yayin):
            dur(f'PUT oncesi gonderi degismis / yayina yakin: {mpb.fark(once, tekrar) if tekrar else "okunamadi"} (yazilmadi)')
        yeni = copy.deepcopy(once)
        yeni['videoThumbnailUrl'] = kurl
        if mpb.fark(once, yeni) != ['videoThumbnailUrl']:
            dur(f'govde farki beklenmedik: {mpb.fark(once, yeni)} (yazilmadi)')
        y = mc.istek('PUT', f"/v2/scheduler/posts/{once.get('id')}", govde=yeni, yok404=True)
        if y is mpb.YOK:
            dur('PUT 404 (yayinlanmis olabilir)')
        sonra, yol = mvd.bul(mc, mpb, '', uuid, yayin)
        if sonra is None:
            dur(f'PUT sonrasi bulunamadi: {yol}')
        json.dump(sonra, open(os.path.join(d, 'SONRA.json'), 'w'), ensure_ascii=False, indent=1)
        fk = mpb.fark(once, sonra)
        with open(os.path.join(d, 'FARK.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['alan', 'once', 'sonra', 'izinli'])
            for x in fk:
                w.writerow([x] + [json.dumps(mvd.deger(g, x), ensure_ascii=False, default=str)[:200] for g in (once, sonra)] + [izinli(x)])
        izinsiz = [x for x in fk if not izinli(x)]
        t2 = sonra.get('videoThumbnailUrl') or ''
        f2 = mvd.kapak_fark(kb, t2, kap, os.path.join(isd, '_k2.jpg')) if t2 else 'kapak yok'
        os.remove(kap)
        kapi = {'izinsiz_fark_yok': not izinsiz, 'kapak_yeni': t2.split('?')[0] == kurl.split('?')[0],
                'kapak_P_karesi': isinstance(f2, float) and f2 < kb.ESIK, 'durum_PENDING': mvd.durum(sonra, 'instagram') == 'PENDING',
                'uuid_ayni': str(sonra.get('uuid')) == uuid, 'media0_ayni': (sonra.get('media') or [''])[0] == m[0],
                'reel_ayni': (sonra.get('instagramData') or {}).get('type') == 'REEL'}
        e = dict(id_sonra=sonra.get('id'), kapak_sonra=sko.kisa(t2), kapak_fark=f2, izinsiz_fark=' '.join(izinsiz))
        if not all(kapi.values()):
            dur('SONRA kapisi: ' + ', '.join(x for x, v in kapi.items() if not v), **e)
        satir(**k, **e, sonuc='PASS', neden='')
        g = time.time() - t0
        log(f'{i}/{len(hed)} ({100 * i // len(hed)}%) {c} {yayin}: PASS, fark {fk}, kapak farki {f2} | gecen {g / 60:.1f} dk, '
            f'kalan ~{g / i * (len(hed) - i) / 60:.1f} dk')
    log(f'BITTI mod {o.mod}: bu kosu {dict(Counter(x["sonuc"] for x in satirlar if x["mod"] == o.mod))}; '
        f'toplam {dict(Counter(x["sonuc"] for x in satirlar))}')


if __name__ == '__main__':
    main()
