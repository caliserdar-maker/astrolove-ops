#!/usr/bin/env python3
"""Kupa galerisi kare kapaklari -> 4:3 (3000x2250) ORNEK (Merkez 28 Eki 2. mesaj madde 6, Serdar onayi: once yalniz 01 kapak + 1 stil
kapagi; toplu uretim Serdar gorsel onayindan sonra). Kapak kupa_orchard/kod/cift.py bolum 2 ile ayni cagrilar: kapak_canva3.py
(sahne/<st>_k40.png + B_<st>_baski_11oz.png + gorunum/geo_kapak_k40.json, GOLGE_US 0.4, PARLA 0.7) ve baslik4.py (RENK cift.py
RENKLER). Sahne 2048x2048 yasam fotografi (duvar, masa, meyve): 4:3 icin dikey kirpim 2048x1536 (Y0 = 226), LANCZOS ile 3000x2250
(1,465x buyutme). Kirpim olcumle: baslik y 328-712 (baslik4 cikti satiri), baski bolgesi y 856-1604 (giydir - sahne farki > 25,
CANCER_LIBRA orange 28 Eki); kupa + golge ~1660'a kadar. Kapi: baslik ve baski bolgesi kirpimin en az PAY px icinde, cikti 3000x2250.
Kullanim (kupa-orchard78 ortami, v12 venv): kupa_kapak43.py <kupa_orchard> <baski dir (B_<st>_baski_11oz.png)> <burc1> <burc2> <out>
  [--stiller orange,fig]"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

from PIL import Image

Y0, KH = 226, 1536                   # 2048 sahnede 4:3 kirpim (2048 x 1536)
BASLIK_Y, BASKI_Y, PAY = (328, 712), (856, 1604), 60
RENKLER = {'orange': '10,40,24', 'fig': '52,18,48', 'olive': '12,24,78', 'pomegranate': '100,16,24', 'almond': '52,22,14',
           'lemon': '12,22,76', 'grape': '16,30,90', 'loquat': '62,24,10'}      # cift.py ile ayni
SIRA = ['orange', 'fig', 'olive', 'pomegranate', 'almond', 'lemon', 'grape', 'loquat']   # cift.py ST8 (galeri: 01 orange, 08-14 digerleri)


def calis(a, env):
    r = subprocess.run(a, capture_output=True, text=True, env=env)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-1500:])
        raise SystemExit('HATA: ' + ' '.join(a[:3]))
    return r.stdout


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('ko'); ap.add_argument('baski'); ap.add_argument('b1'); ap.add_argument('b2')
    ap.add_argument('out'); ap.add_argument('--stiller', default='orange,fig'); a = ap.parse_args()
    K = os.path.abspath(os.path.join(a.ko, 'kod')) + '/'; V = os.path.abspath(os.path.join(a.ko, 'varlik')) + '/'
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); R = {}
    if not (Y0 + PAY <= BASLIK_Y[0] and BASKI_Y[1] <= Y0 + KH - PAY):
        raise SystemExit(f'DUR: kirpim {Y0}-{Y0 + KH} baslik / baski bolgesini PAY {PAY} ile kapsamiyor')
    for st in a.stiller.split(','):
        env = {'GOLGE_US': '0.4', 'PARLA': '0.7', 'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
        g = out / f'_{st}_giydir.jpg'; kp = out / f'_KAPAK_{st}_2048.jpg'
        calis([sys.executable, '-I', K + 'kapak_canva3.py', V + f'sahne/{st}_k40.png', str(Path(a.baski) / f'B_{st}_baski_11oz.png'),
               V + 'gorunum/geo_kapak_k40.json', str(g)], env)
        o = calis([sys.executable, '-I', K + 'baslik4.py', str(g), a.b1, a.b2, str(kp)], dict(env, RENK=RENKLER[st]))
        m = re.search(r'baslik y (\d+)-(\d+)', o)
        by = (int(m.group(1)), int(m.group(2))) if m else None
        if not by or by[0] < Y0 + PAY or by[1] > Y0 + KH - PAY:
            raise SystemExit(f'DUR: {st} baslik {by} kirpim disina yakin')
        import numpy as np                       # baski bolgesi her stilde olculur (inceleme 28 Eki: sabit BASKI_Y yalniz orange olcumuydu)
        gs = np.asarray(Image.open(g).convert('RGB')).astype(np.int16)
        sh = np.asarray(Image.open(V + f'sahne/{st}_k40.png').convert('RGB').resize(Image.open(g).size)).astype(np.int16)
        ys = np.nonzero((np.abs(gs - sh).max(axis=2) > 25).any(axis=1))[0]
        bk = (int(ys.min()), int(ys.max()) + 1) if len(ys) else None
        if not bk or bk[0] < Y0 + PAY or bk[1] > Y0 + KH - PAY:
            raise SystemExit(f'DUR: {st} baski bolgesi {bk} kirpim {Y0}-{Y0 + KH} (PAY {PAY}) disina yakin')
        im = Image.open(kp).convert('RGB')
        if im.size != (2048, 2048):
            raise SystemExit(f'DUR: {st} kapak {im.size} (2048x2048 beklenir)')
        no = SIRA.index(st)
        ad = f'KUPA_KAPAK43_{no + 1 if no == 0 else no + 7:02d}_{st}.jpg'           # galeri sirasi: 01 orange, 08-14 digerleri
        k = im.crop((0, Y0, 2048, Y0 + KH)).resize((3000, 2250), Image.LANCZOS)
        k.save(out / ad, quality=92)
        im.save(out / f'KUPA_KAPAK_KARE_{st}.jpg', quality=92)                       # karsilastirma icin mevcut kare kapak
        R[ad] = dict(stil=st, baslik_y=by, baski_y_olcum=bk, kirpim=[0, Y0, 2048, Y0 + KH], olcek=round(3000 / 2048, 4), boyut=list(k.size),
                     kb=round((out / ad).stat().st_size / 1024))
        g.unlink(); kp.unlink()
        print(ad, R[ad], flush=True)
    import PIL
    (out / 'KAPAK43_OZET.json').write_text(json.dumps(dict(kapaklar=R, pillow=PIL.__version__), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
