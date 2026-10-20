#!/usr/bin/env python3
"""Bekleyen IG + FB Reels -> yeni P acilisli video (Serdar onayi 20 Eki 2026). Karusel / FB album DEGISMEZ.
Kaynak: Drive TEMP/SOSYAL_VIDEO_P_78_20261020/<a>-and-<b>-astroloveart-reel.mp4 (78/78 PASS).
Eslesme: SOSYAL_DEGISIM_20261020/INSTAGRAM/ESLEME.csv (tur Reels, karar degismeli) ve FACEBOOK/ESLEME.csv
(facebookData_type REEL, karar degismeli). Yazma metricool_video_degistir.py --mod yaz ile (cift basina ayri surec:
ONCE kapisi -> 1 yukleme + donusmus dosya olcumu -> PUT yalniz media[0] (FB: + videoThumbnailUrl = yeni videonun ilk
karesi, --fb-kapak) -> uuid ile geri okuma + tam fark + gonderideki video olcumu). Ilk FAIL -> DUR (sonraki cifte gecilmez).
Mod: tek_ig (1 cift, yalniz IG), tek_fb (ayni cift, yalniz FB), kalan (geri kalan tum ciftler, IG + FB).
Her hedef once uuid ile guncel haliyle okunur: guncel id kullanilir; durum PENDING degilse ya da media[0] ESLEME'deki
eski URL degilse yazilmaz (ZATEN / DURUM); yayina 2 sa + PAY dk'dan az kalan ATLANDI.
Kullanim: reels_p_degistir.py --token T --ig IG.csv --fb FB.csv --video-dir gdrive:... --mod tek_ig|tek_fb|kalan
          [--cift A_B] --cikti DIR --is DIR [--onceki SONUC.csv]"""
import argparse, csv, importlib.util, json, os, subprocess, sys, time
from datetime import datetime, timedelta

D = os.path.dirname(os.path.abspath(__file__))
PAY_DK = 15
ALAN = ['zaman_ist', 'mod', 'cift', 'ag', 'yayin', 'uuid', 'id_once', 'id_sonra', 'sonuc', 'neden', 'eski_media', 'yeni_media',
        'yeni_kapak', 'gonderideki_video', 'kapak_fark', 'rapor_klasoru']


def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def oku_csv(yol):
    return list(csv.DictReader(open(yol, encoding='utf-8'))) if yol and os.path.exists(yol) else []


def hedefler(ig_csv, fb_csv):
    """{cift: {'instagram': {...}, 'facebook': {...}}} yalniz degismeli Reels."""
    out = {}
    for r in oku_csv(ig_csv):
        if r['tur'].startswith('Reels') and r['karar'] == 'degismeli':
            out.setdefault(r['cift'], {})['instagram'] = {'uuid': r['uuid'], 'id': r['metricool_id'], 'yayin': r['yayin_zamani'],
                                                          'eski': r['medya_url'].split()[0]}
    for r in oku_csv(fb_csv):
        if r['facebookData_type'] == 'REEL' and r['karar'] == 'degismeli':
            out.setdefault(r['cift'], {})['facebook'] = {'uuid': r['uuid'], 'id': r['gonderi_id'], 'yayin': r['tarih'],
                                                         'eski': r['medya_url'].split(' | ')[0].split()[0]}
    return out


def main():
    a = argparse.ArgumentParser()
    for k in ('token', 'ig', 'fb', 'video-dir', 'mod', 'cikti', 'is'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--cift', default=''); a.add_argument('--onceki', default='')
    o = a.parse_args()
    for d in (o.cikti, getattr(o, 'is')):
        os.makedirs(d, exist_ok=True)
    mvd = yukle('mvd', os.path.join(D, 'metricool_video_degistir.py'))
    yz = yukle('yz', os.path.join(D, 'metricool_5p_yaz.py'))
    mpb = yz.mpb
    mc = mpb.MC(json.load(open(o.token)))
    ozet = open(os.path.join(o.cikti, 'OZET.txt'), 'a', encoding='utf-8')

    def log(s):
        print(s, flush=True); ozet.write(s + '\n'); ozet.flush()

    satirlar = oku_csv(o.onceki)
    sonuc_yol = os.path.join(o.cikti, 'SONUC.csv')

    def kaydet():
        with open(sonuc_yol, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, ALAN, extrasaction='ignore'); w.writeheader(); w.writerows(satirlar)

    def satir(**k):
        satirlar.append(dict({'zaman_ist': mvd.simdi_ist().strftime('%Y-%m-%dT%H:%M:%S'), 'mod': o.mod}, **k)); kaydet()

    H = hedefler(o.ig, o.fb)
    log(f'=== {mvd.simdi_ist():%Y-%m-%d %H:%M} mod {o.mod}: ESLEME Reels degismeli: IG {sum("instagram" in v for v in H.values())}, '
        f'FB {sum("facebook" in v for v in H.values())}, cift {len(H)}')
    aglar = {'tek_ig': ['instagram'], 'tek_fb': ['facebook'], 'kalan': ['instagram', 'facebook']}.get(o.mod)
    if not aglar:
        sys.exit(f'DUR: mod {o.mod}')
    ciftler = sorted(H, key=lambda c: min(v['yayin'] for v in H[c].values()))
    if o.mod in ('tek_ig', 'tek_fb'):
        if o.cift:
            ciftler = [o.cift] if o.cift in H else []
        else:   # tek_ig: yayini en erken, IG + FB ikisi de olan ve her ikisi de >= 2 sa + 1 gun sonra olan cift
            esik = (mvd.simdi_ist() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
            ciftler = [c for c in ciftler if {'instagram', 'facebook'} <= set(H[c]) and min(v['yayin'] for v in H[c].values()) >= esik][:1]
        if not ciftler:
            sys.exit(f'DUR: {o.mod} icin cift yok ({o.cift or "otomatik"})')

    t0, toplam = time.time(), len(ciftler)
    for i, c in enumerate(ciftler, 1):
        hed = []
        for ag in aglar:
            h = H[c].get(ag)
            if not h:
                continue
            k = dict(cift=c, ag=ag, yayin=h['yayin'], uuid=h['uuid'], id_once=h['id'], eski_media=h['eski'])
            if datetime.fromisoformat(h['yayin'][:19]) - mvd.simdi_ist() < timedelta(hours=mvd.MIN_SAAT, minutes=PAY_DK):
                satir(**k, sonuc='ATLANDI', neden=f'yayina {mvd.MIN_SAAT} sa + {PAY_DK} dk dan az'); continue
            p, yol = mvd.bul(mc, mpb, '', h['uuid'], h['yayin'][:19])
            if p is None:
                satir(**k, sonuc='DUR', neden=f'bulunamadi: {yol}'); log(f'DUR: {c} {ag} bulunamadi ({yol})'); sys.exit(1)
            m0 = (p.get('media') or [''])[0]
            if mvd.durum(p, ag) != 'PENDING':
                satir(**k, sonuc='YAZILMADI', neden=f'durum {mvd.durum(p, ag)}'); continue
            if m0.split('?')[0] != h['eski'].split('?')[0]:
                satir(**k, sonuc='ZATEN', neden='media[0] ESLEME eski URL degil (once degismis)', yeni_media=m0); continue
            hed.append((ag, str(p.get('id')), h, k))
        if not hed:
            log(f'{i}/{toplam} {c}: yazilacak hedef yok'); continue
        s = c.lower().replace('_', '-and-')
        vid, kap = os.path.join(getattr(o, 'is'), f'{c}.mp4'), os.path.join(getattr(o, 'is'), f'{c}_ilk_kare.jpg')
        subprocess.run(['rclone', 'copyto', f'{getattr(o, "video_dir")}/{s}-astroloveart-reel.mp4', vid, '-q'], check=True, timeout=600)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', vid, '-frames:v', '1', '-q:v', '1', kap], check=True)
        rk = os.path.join(o.cikti, f'{c}_{o.mod}')
        komut = [sys.executable, os.path.join(D, 'metricool_video_degistir.py'), '--token', o.token, '--cift', c, '--mod', 'yaz',
                 '--hedef', ','.join(f'{ag}:{pid}:{h["uuid"]}' for ag, pid, h, _ in hed), '--video', vid, '--kapak', kap,
                 '--cikti', rk] + (['--fb-kapak'] if any(ag == 'facebook' for ag, *_ in hed) else [])
        r = subprocess.run(komut, capture_output=True, text=True)
        if os.path.isdir(rk):   # presigned URL maskesi (::add-mask::) dosyaya yazilmaz
            open(os.path.join(rk, 'LOG.txt'), 'w').write(''.join(x for x in (r.stdout + r.stderr).splitlines(True)
                                                                 if not x.startswith('::add-mask::')))
        rap = json.load(open(os.path.join(rk, 'DEGISTIR_RAPOR.json'))) if os.path.exists(os.path.join(rk, 'DEGISTIR_RAPOR.json')) else {}
        for ag, pid, h, k in hed:
            g = (rap.get('gonderiler') or {}).get(h['uuid'], {})
            gv = g.get('gonderideki_video') or {}
            yeni_kapak = next((x.get('url') for x in rap.get('adimlar', []) if x.get('ad') == 'kapak_yukleme'), '') if ag == 'facebook' else ''
            yeni = next((x.get('url') for x in rap.get('adimlar', []) if x.get('ad') == 'yukleme'), '')
            satir(**dict(k, id_once=pid), id_sonra=g.get('id_sonra', ''), sonuc=g.get('sonuc') or ('YAZILMADI' if r.returncode else '?'),
                  neden='' if g.get('sonuc') == 'PASS' else str(rap.get('sonuc') or (r.stdout.strip().splitlines() or ['?'])[-1])[:300],
                  yeni_media=yeni if g.get('sonuc') else '', yeni_kapak=yeni_kapak if g.get('sonuc') else '',
                  gonderideki_video=gv.get('sonuc', ''), kapak_fark=gv.get('kapak_fark', ''), rapor_klasoru=os.path.basename(rk))
        for x in (vid, kap):
            os.remove(x)
        g_ = time.time() - t0
        log(f'{i}/{toplam} ({100 * i // toplam}%) {c} {[ag for ag, *_ in hed]}: rc {r.returncode} {rap.get("sonuc", "")[:160]} | '
            f'gecen {g_ / 60:.1f} dk, kalan ~{g_ / i * (toplam - i) / 60:.1f} dk')
        if r.returncode != 0:
            log(f'DUR: {c} FAIL, sonraki ciftlere gecilmedi')
            sys.exit(1)
    from collections import Counter
    log(f'BITTI mod {o.mod}: bu kosu {dict(Counter(x["sonuc"] for x in satirlar if x["mod"] == o.mod))}; '
        f'toplam (tum kosular) {dict(Counter((x["ag"], x["sonuc"]) for x in satirlar))}')


if __name__ == '__main__':
    main()
