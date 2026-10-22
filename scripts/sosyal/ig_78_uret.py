#!/usr/bin/env python3
"""IG/FB 78 cift: onayli ig_bas.py (ChatGPT sahne + gercek poster + yazi) birebir; yalniz yazilardaki
"Cancer & Libra" -> "<Sol> & <Sag>" (ayni burc: "Leo & Leo"). Yazi kutuya sigmazsa hata; kucultme YOK.
Cikti: CIKTI/<CIFT>/C01..C03_1080x1350.jpg + REEL_1080x1920_9sn.mp4, CIKTI/QC.csv, CIKTI/SIGMA.csv.
Kullanim:
  ig_78_uret.py --paket P --fontlar F --tagline IG_78.csv --cikti OUT --yalniz-sigma
  ig_78_uret.py --paket P --fontlar F --tagline IG_78.csv --posterler DIR --cikti OUT [--ciftler A_B,C_D] [--reel]"""
import argparse, copy, csv, importlib.util, json, os, subprocess, sys, time
import numpy as np
from PIL import Image

ESKI = 'Cancer & Libra'


def yukle_ig_bas(paket, fontlar):
    spec = importlib.util.spec_from_file_location('ig_bas', os.path.join(paket, 'ig_bas.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.FONT = {'Cormorant Garamond': os.path.join(fontlar, 'CormorantGaramond[wght].ttf'),
              'Manrope': os.path.join(fontlar, 'Manrope[wght].ttf')}
    return m


def katmanlar(spec):
    for p in spec['plates']:
        yield from p['overlay_text_layers']
    yield from spec['reel']['overlay_text_layers']


def cift_spec(orj, sol, sag):
    s = copy.deepcopy(orj)
    yeni = f'{sol} & {sag}'
    n = 0
    for L in katmanlar(s):
        if ESKI in L['text']:
            L['text'] = L['text'].replace(ESKI, yeni); n += 1
        elif 'Cancer' in L['text'] or 'Libra' in L['text']:
            raise SystemExit(f"DUR: burc adi beklenmeyen kalipta: {L['text']}")
    if n != 4:  # C01, C02, R01 plate, reel katmani
        raise SystemExit(f'DUR: degisen yazi sayisi {n} != 4')
    return s


def sigma(m, spec):
    """Her yazi katmanini ig_bas.yazi_katmani ile cizer; sigmayanlari dondurur."""
    hata = []
    for p in spec['plates']:
        for L in p['overlay_text_layers']:
            try:
                m.yazi_katmani(tuple(p['canvas_px']), [L])
            except SystemExit as e:
                hata.append(f"{p['id']}: {e}")
    for L in spec['reel']['overlay_text_layers']:
        try:
            m.yazi_katmani((1080, 1920), [L])
        except SystemExit as e:
            hata.append(f'REEL: {e}')
    return hata


def psnr(a, b):
    d = np.mean((a.astype(float) - b.astype(float)) ** 2)
    return 99.0 if d == 0 else 10 * np.log10(255 ** 2 / d)


def qc(m, spec, poster, kl, mk):
    s = []
    for p in spec['plates']:
        if not p['id'].startswith('C'):
            continue
        y = os.path.join(kl, f"{p['id']}_1080x1350.jpg")
        im = Image.open(y)
        if im.size != (1080, 1350) or im.format != 'JPEG':
            s.append(f"{p['id']} boyut {im.size} {im.format}")
        # Poster dogru yerde mi: kutuda PSNR >= 30 (CL q95 JPEG olcumu 35.7) ve +-2 px kaymalardan iyi
        x0, y0, w, h = p['poster_inner_box_xywh']
        ref = np.asarray(poster.resize((w, h), Image.LANCZOS))[2:-2, 2:-2]
        a = np.asarray(im.convert('RGB'))
        v = {(dx, dy): psnr(ref, a[y0 + 2 + dy:y0 + h - 2 + dy, x0 + 2 + dx:x0 + w - 2 + dx])
             for dx in (-2, 0, 2) for dy in (-2, 0, 2)}
        if v[(0, 0)] < 30 or max(v, key=v.get) != (0, 0):
            s.append(f"{p['id']} poster PSNR {v[(0, 0)]:.1f}, en iyi kayma {max(v, key=v.get)}")
    mp4 = os.path.join(kl, 'REEL_1080x1920_9sn.mp4')
    if os.path.exists(mp4):
        o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                            'stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt', '-of', 'json', mp4],
                           capture_output=True, text=True)
        st = json.loads(o.stdout)['streams'][0]
        bek = {'width': 1080, 'height': 1920, 'r_frame_rate': '30/1', 'nb_read_frames': '270', 'codec_name': 'h264',
               'pix_fmt': 'yuv420p'}
        for k, v in bek.items():
            if str(st.get(k)) != str(v):
                s.append(f'reel {k}={st.get(k)} != {v}')
    if mk:
        for L in katmanlar(spec):
            s += [f"metin_kurali {L['text']}: {x}" for x in mk.denetle(L['text'])]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paket', required=True); ap.add_argument('--fontlar', required=True)
    ap.add_argument('--tagline', required=True); ap.add_argument('--cikti', required=True)
    ap.add_argument('--posterler'); ap.add_argument('--ciftler', default='HEPSI')
    ap.add_argument('--reel', action='store_true'); ap.add_argument('--yalniz-sigma', action='store_true')
    ap.add_argument('--metin-kurali')
    a = ap.parse_args()
    m = yukle_ig_bas(a.paket, a.fontlar)
    orj = copy.deepcopy(m.SPEC)
    mk = None
    if a.metin_kurali:
        sp = importlib.util.spec_from_file_location('mk', a.metin_kurali)
        mk = importlib.util.module_from_spec(sp); sp.loader.exec_module(mk)
    ciftler = list(csv.DictReader(open(a.tagline, encoding='utf-8')))
    if len(ciftler) != 78 or len({c['cift'] for c in ciftler}) != 78:
        raise SystemExit(f'DUR: tagline CSV 78 essiz cift degil ({len(ciftler)})')
    os.makedirs(a.cikti, exist_ok=True)

    # 1) sigma: 78 cift, poster gerekmez
    sig = []
    for c in ciftler:
        for h in sigma(m, cift_spec(orj, c['sol_burc'], c['sag_burc'])):
            sig.append({'cift': c['cift'], 'hata': h})
    with open(os.path.join(a.cikti, 'SIGMA.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['cift', 'hata'], lineterminator='\n'); w.writeheader(); w.writerows(sig)
    print(f'SIGMA {78 - len({x["cift"] for x in sig})}/78 PASS' + ''.join(f'\n  {x["cift"]}: {x["hata"]}' for x in sig))
    if a.yalniz_sigma:
        return
    if sig:
        raise SystemExit('DUR: sigmayan cift var (SIGMA.csv); uretim yapilmadi')

    # 2) uretim
    sec = ciftler if a.ciftler == 'HEPSI' else [c for c in ciftler if c['cift'] in a.ciftler.split(',')]
    eksik = [c['cift'] for c in sec if not os.path.exists(os.path.join(a.posterler, c['cift'] + '.png'))]
    if eksik:
        raise SystemExit(f'DUR: poster yok ({len(eksik)}): {", ".join(eksik)}')
    sat, t0 = [], time.time()
    for i, c in enumerate(sec, 1):
        m.SPEC = cift_spec(orj, c['sol_burc'], c['sag_burc'])
        py = os.path.join(a.posterler, c['cift'] + '.png')
        poster = Image.open(py).convert('RGB')
        kl = os.path.join(a.cikti, c['cift']); os.makedirs(kl, exist_ok=True)
        m.carousel(poster, kl)
        if a.reel:
            m.reel(poster, kl)
        s = qc(m, m.SPEC, poster, kl, mk)
        sat.append({'cift': c['cift'], 'cift_adi': f"{c['sol_burc']} & {c['sag_burc']}",
                    'poster_sha256': subprocess.run(['sha256sum', py], capture_output=True, text=True).stdout[:64],
                    'sonuc': 'FAIL' if s else 'PASS', 'not': '; '.join(s)})
        g = time.time() - t0
        print(f'[{i}/{len(sec)}] {c["cift"]} {sat[-1]["sonuc"]} | gecen {g:.0f} sn, kalan ~{g / i * (len(sec) - i):.0f} sn, '
              f'%{100 * i / len(sec):.0f}', flush=True)
    with open(os.path.join(a.cikti, 'QC.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(sat[0]), lineterminator='\n'); w.writeheader(); w.writerows(sat)
    n = sum(r['sonuc'] == 'PASS' for r in sat)
    print(f'QC {n}/{len(sat)} PASS')
    sys.exit(0 if n == len(sat) else 1)


if __name__ == '__main__':
    main()
