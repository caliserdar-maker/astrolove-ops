#!/usr/bin/env python3
"""video-v1: 77 cift KART 3 (Serdar onayi 25 Eyl 2026; ornekler Aries+Leo, Aquarius+Aquarius onaylandi).
Girdi: gdrive A1_77/<CIFT>/POSTER_EJ.png + RAPOR_tam.json (medya-v1; yalniz 'gecti' olan ciftler).
Cikti: A1_77/<CIFT>/KART3.jpg + KART3_qc.json; A1_77/_KART3/{RAPOR_parca<n>.json, KART3_SERIT_77.jpg, KART3_RAPOR_77.json}.
Kullanim: kart3_77.py uret <parca> <toplam> | kart3_77.py serit | kart3_77.py yerel <CIFT_DIZINI> <CIKTI_DIZINI>
Yalniz Drive (rclone). Etsy/Prodigi erisimi yok."""
import json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
REF = HERE / 'ref/03_8615800647.jpg'; HIZA = HERE / 'kart3_panel_hiza.json'
W = Path('_kart3').resolve()
def rc(*a, cikti=False):
    r = subprocess.run(['rclone', *a, '--retries', '3'], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f'rclone {a[0]}: {r.stderr[-300:]}')
    return r.stdout
def fontlar():
    fd = W / 'fonts'; fd.mkdir(parents=True, exist_ok=True)
    for rel, ad in (('montserrat/Montserrat%5Bwght%5D.ttf', 'Montserrat[wght].ttf'), ('ebgaramond/EBGaramond%5Bwght%5D.ttf', 'EBGaramond[wght].ttf')):
        if not (fd / ad).exists():
            subprocess.run(['curl', '-sfL', '-o', str(fd / ad), f'https://raw.githubusercontent.com/google/fonts/main/ofl/{rel}'], check=True)
    os.environ['FONT_DIR'] = str(fd) + '/'
def isle(c, d, o):
    """d: POSTER_EJ.png (+ RAPOR_tam.json) iceren dizin; o: cikti dizini. {'gecti', ...} doner."""
    rap = d / 'RAPOR_tam.json'
    if not (d / 'POSTER_EJ.png').exists(): return {'gecti': False, 'neden': 'POSTER_EJ yok'}
    if rap.exists() and not json.loads(rap.read_text()).get('gecti', False): return {'gecti': False, 'neden': 'POSTER_EJ medya FAIL'}
    s1, s2 = c.split('_')
    o.mkdir(parents=True, exist_ok=True); k = o / 'KART3.jpg'
    r = subprocess.run([sys.executable, str(HERE / 'kart3.py'), str(REF), str(k), s1, s2, '--poster', str(d / 'POSTER_EJ.png'), '--hiza', str(HIZA)],
                       capture_output=True, text=True)
    if r.returncode: return {'gecti': False, 'neden': 'kart3.py hata: ' + r.stderr[-300:]}
    q = subprocess.run([sys.executable, str(HERE / 'qc_kart3.py'), str(REF), str(k), str(o / 'KART3_log.json'), '--cift', str(d / 'POSTER_EJ.png')],
                       capture_output=True, text=True)
    qc = json.loads((o / 'KART3_qc.json').read_text())
    return {'gecti': qc['SONUC'] == 'PASS', 'qc': qc['PASS'], 'neden': '' if qc['SONUC'] == 'PASS' else 'QC FAIL'}
def uret(parca, toplam):
    fontlar(); t0 = time.time()
    ciftler = sorted(x.strip('/') for x in rc('lsf', A77, '--dirs-only').split() if not x.startswith('_'))
    benim = ciftler[parca::toplam]; R = {}
    for n, c in enumerate(benim, 1):
        d = W / 'in' / c; o = W / 'out' / c; d.mkdir(parents=True, exist_ok=True); t1 = time.time()
        try:
            rc('copy', f'{A77}/{c}', str(d), '--include', 'POSTER_EJ.png', '--include', 'RAPOR_tam.json')
            r = isle(c, d, o)
            if (o / 'KART3.jpg').exists():
                rc('copy', str(o), f'{A77}/{c}', '--include', 'KART3.jpg', '--include', 'KART3_qc.json')
        except Exception as e:
            r = {'gecti': False, 'neden': repr(e)[:300]}
        r['sn'] = round(time.time() - t1, 1); R[c] = r
        el = time.time() - t0; kalan = el / n * (len(benim) - n)
        print(f'[{n}/{len(benim)}] %{100*n/len(benim):.0f} {c} {"PASS" if r["gecti"] else "FAIL " + r["neden"]} | gecen {el/60:.1f} dk kalan {kalan/60:.1f} dk', flush=True)
    p = W / f'RAPOR_parca{parca}.json'; p.write_text(json.dumps(R, indent=1)); rc('copy', str(p), f'{A77}/_KART3')
def serit():
    from PIL import Image, ImageDraw, ImageFont
    fontlar(); S = W / 'serit'; S.mkdir(parents=True, exist_ok=True)
    rc('copy', f'{A77}/_KART3', str(S), '--include', 'RAPOR_parca*.json')
    R = {}
    for p in sorted(S.glob('RAPOR_parca*.json')): R.update(json.loads(p.read_text()))
    rc('copy', A77, str(S / 'k'), '--include', '*/KART3.jpg')
    ad = sorted(R); gec = [c for c in ad if R[c]['gecti']]; kal = {c: R[c].get('neden', '') for c in ad if not R[c]['gecti']}
    tw, th, sut = 600, 450, 7; sat = (len(ad) + sut - 1) // sut
    f = ImageFont.truetype(os.environ['FONT_DIR'] + 'Montserrat[wght].ttf', 22)
    pg = Image.new('RGB', (sut * tw, sat * (th + 34)), 'white'); dr = ImageDraw.Draw(pg)
    for i, c in enumerate(ad):
        x, y = (i % sut) * tw, (i // sut) * (th + 34)
        k = S / 'k' / c / 'KART3.jpg'
        if k.exists(): pg.paste(Image.open(k).convert('RGB').resize((tw - 6, th - 4)), (x + 3, y + 32))
        dr.text((x + 6, y + 4), f"{c} {'PASS' if R[c]['gecti'] else 'FAIL'}", fill='black' if R[c]['gecti'] else 'red', font=f)
    pg.save(S / 'KART3_SERIT_77.jpg', quality=85)
    rap = {'toplam': len(ad), 'pass': len(gec), 'fail': len(kal), 'fail_liste': kal}
    (S / 'KART3_RAPOR_77.json').write_text(json.dumps(rap, indent=1))
    rc('copy', str(S), f'{A77}/_KART3', '--include', 'KART3_SERIT_77.jpg', '--include', 'KART3_RAPOR_77.json')
    print(json.dumps(rap), flush=True)
if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'uret': uret(int(sys.argv[2]), int(sys.argv[3]))
    elif m == 'serit': serit()
    elif m == 'yerel':
        d = Path(sys.argv[2]); print(json.dumps(isle(d.name, d, Path(sys.argv[3]))))
