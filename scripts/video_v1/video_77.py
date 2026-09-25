#!/usr/bin/env python3
"""video-v1: 77 cift videosu (Serdar onayi 25 Eyl 2026; ornekler Aries+Leo, Aquarius+Aquarius onaylandi).
Sablon = v5 (video_cift.py + qc_cift.py; AM tagline kaydirmasi olcume bagli). Girdi: A1_77/<CIFT>/POSTER_EJ|IN|AM.png + RAPOR_tam.json.
AM posteri olmayan cift URETILMEZ (BEKLE). Onceki kosuda PASS olan cift atlanir (tekrar kosuda yalniz yeni AM'ler islenir).
Cikti: A1_77/<CIFT>/{VIDEO.mp4, VIDEO_qc.json, VIDEO_KARE.jpg}; A1_77/_VIDEO/{RAPOR_parca<n>.json, VIDEO_SERIT_77.jpg, VIDEO_RAPOR_77.json}.
Kullanim: video_77.py uret <parca> <toplam> | video_77.py serit. Yalniz Drive (rclone). Etsy/Prodigi erisimi yok."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
REF = HERE / 'ref'
W = Path('_video77').resolve()
def rc(*a):
    r = subprocess.run(['rclone', *a, '--retries', '3'], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f'rclone {a[0]}: {r.stderr[-300:]}')
    return r.stdout
def ffmpeg_yolu():
    import imageio_ffmpeg
    b = W / 'bin'; b.mkdir(parents=True, exist_ok=True); f = b / 'ffmpeg'
    if not f.exists(): f.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ['PATH'] = f'{b}:{os.environ["PATH"]}'
def ciftler():
    return sorted(x.strip('/') for x in rc('lsf', A77, '--dirs-only').split() if not x.startswith('_'))
def isle(c):
    d = W / 'in' / c; o = W / 'out' / c
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(o, ignore_errors=True); d.mkdir(parents=True); o.mkdir(parents=True)
    rc('copy', f'{A77}/{c}', str(d), '--include', 'POSTER_*.png', '--include', 'RAPOR_tam.json', '--include', 'VIDEO_qc.json')
    if (d / 'VIDEO_qc.json').exists() and json.loads((d / 'VIDEO_qc.json').read_text()).get('SONUC') == 'PASS':
        return {'durum': 'PASS', 'not': 'onceki kosu'}
    rap = d / 'RAPOR_tam.json'
    if not (d / 'POSTER_EJ.png').exists() or (rap.exists() and not json.loads(rap.read_text()).get('gecti', False)):
        return {'durum': 'ATLA', 'not': 'POSTER_EJ yok ya da medya FAIL'}
    if not (d / 'POSTER_AM.png').exists(): return {'durum': 'BEKLE', 'not': 'POSTER_AM yok'}
    if not (d / 'POSTER_IN.png').exists(): return {'durum': 'BEKLE', 'not': 'POSTER_IN yok'}
    v = o / 'VIDEO.mp4'
    r = subprocess.run([sys.executable, str(HERE / 'video_cift.py'), str(REF / 'AstroLove_Centered_Immediate_12s.mp4'), str(REF / 'v2_meta.json'),
                        str(REF / 'P_emily_james.png'), str(d), str(v)], capture_output=True, text=True)
    if r.returncode: return {'durum': 'FAIL', 'not': 'video_cift hata: ' + (r.stdout + r.stderr)[-300:]}
    q = subprocess.run([sys.executable, str(HERE / 'qc_cift.py'), str(v)], capture_output=True, text=True)
    qc = json.loads((o / 'VIDEO_qc.json').read_text())
    from PIL import Image
    Image.open(o / 'VIDEO_AM.png').convert('RGB').resize((540, 675), Image.LANCZOS).save(o / 'VIDEO_KARE.jpg', quality=88)
    rc('copy', str(o), f'{A77}/{c}', '--include', 'VIDEO.mp4', '--include', 'VIDEO_qc.json', '--include', 'VIDEO_KARE.jpg')
    kalan = [k for k, x in qc['PASS'].items() if not x]
    return {'durum': qc['SONUC'], 'not': ','.join(kalan), 'tagline_fark': qc['tagline_fark'], 'gecis_bas_sn': qc['gecis_bas_sn'][:1]}
def uret(parca, toplam):
    ffmpeg_yolu(); t0 = time.time()
    benim = ciftler()[parca::toplam]; R = {}
    for n, c in enumerate(benim, 1):
        t1 = time.time()
        try: r = isle(c)
        except Exception as e: r = {'durum': 'FAIL', 'not': repr(e)[:300]}
        r['sn'] = round(time.time() - t1, 1); R[c] = r
        el = time.time() - t0
        print(f'[{n}/{len(benim)}] %{100*n/len(benim):.0f} {c} {r["durum"]} {r.get("not","")} | gecen {el/60:.1f} dk kalan {el/n*(len(benim)-n)/60:.1f} dk', flush=True)
    p = W / f'RAPOR_parca{parca}.json'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(R, indent=1))
    rc('copy', str(p), f'{A77}/_VIDEO')
def serit():
    from PIL import Image, ImageDraw
    S = W / 'serit'; shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
    rc('copy', f'{A77}/_VIDEO', str(S), '--include', 'RAPOR_parca*.json')
    R = {}
    for p in sorted(S.glob('RAPOR_parca*.json')): R.update(json.loads(p.read_text()))
    rc('copy', A77, str(S / 'k'), '--include', '*/VIDEO_KARE.jpg')
    ad = sorted(R); tw, th, sut = 270, 338, 11; sat = (len(ad) + sut - 1) // sut
    pg = Image.new('RGB', (sut * tw, sat * (th + 22)), 'white'); dr = ImageDraw.Draw(pg)
    for i, c in enumerate(ad):
        x, y = (i % sut) * tw, (i // sut) * (th + 22); k = S / 'k' / c / 'VIDEO_KARE.jpg'
        if k.exists(): pg.paste(Image.open(k).convert('RGB').resize((tw - 4, th - 4)), (x + 2, y + 20))
        dr.text((x + 4, y + 4), f"{c} {R[c]['durum']}", fill='black' if R[c]['durum'] == 'PASS' else 'red')
    pg.save(S / 'VIDEO_SERIT_77.jpg', quality=85)
    say = {}
    for c in ad: say[R[c]['durum']] = say.get(R[c]['durum'], 0) + 1
    rap = {'toplam_klasor': len(ad), 'sayim': say, 'fail': {c: R[c]['not'] for c in ad if R[c]['durum'] == 'FAIL'},
           'bekle': {c: R[c]['not'] for c in ad if R[c]['durum'] == 'BEKLE'}, 'atla': {c: R[c]['not'] for c in ad if R[c]['durum'] == 'ATLA'}}
    (S / 'VIDEO_RAPOR_77.json').write_text(json.dumps(rap, indent=1))
    rc('copy', str(S), f'{A77}/_VIDEO', '--include', 'VIDEO_SERIT_77.jpg', '--include', 'VIDEO_RAPOR_77.json')
    print(json.dumps(rap), flush=True)
if __name__ == '__main__':
    if sys.argv[1] == 'uret': uret(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == 'serit': serit()
