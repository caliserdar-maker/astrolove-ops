#!/usr/bin/env python3
"""Pinterest 78 cift video ornegi QC (Serdar 25 Kas 2026, KARARLAR_20261125_49/_50).
Video = onayli sosyal video (video_v9) acilis B (poster karesi yok) + --sure 15 (son kart kisa) + onayli kapak_v1 kapagi
kapak_basa.py ile 0-0.5 sn tam, 0.5-1.0 sn gecis. Son kart metni onayli (degismez).
Kapilar (PASS/FAIL):
  1) Render esitligi: B/15 sn kareleri, onayli P/24 sn kareleriyle (ayni poster, ayni kod) 1.5 <= t < SON_FO arasinda fark 0.
  2) Son kart suresi: sure - (19.6 - T_B0) 3.0-4.0 sn (Serdar "3-4 sn").
  3) Son mp4: 1080x1920, 30 fps, kare = 30 x sure, sure +-0.05, h264, ses = sure +-0.05.
  4) kapak_basa QC json: sonuc PASS (ilk kare = kapak < 2.0, 0-1.5 sn parlaklik, kayma, kare/sure/ses ayni).
  5) Son kart ekranda olculen sure (son mp4, 0.1 sn adim, "Make it yours" bandinda yazi maskesi - zemin farki >= tepenin %10'u)
     3.0-4.0 sn;
     tam gorunur sure (>= %90) bilgi olarak yazilir.
  6) Muzik: integrated -16 LUFS +-1.0 (muzik_ekle.py kurali), --muzik verilirse.
  7) Onayli Drive P videosuyla (--onayli_mp4) 2 / 5 / 8 / 10.5 sn karelerinde ortalama fark <= 2.0 (kapak_basa.py ESIK) VE
     p99 <= 10 (25 Kas olcum: ayni kaynak ort 0.86-1.32 p99 4-5; farkli isimli poster ort 1.03-1.86 p99 6-20, ortalama tek basina
     ayirt edemedi). Ilk 1.5 sn (kapak + gecis) ve son kararma bu kapinin disinda.
Kullanim: pin78_video_qc.py --b DIR --p DIR --bilgi bilgi.json --sure 15 --video V.mp4 --kapak_qc Q.json [--kapak K.jpg --kapak_son_qc Q2.json
          --son_kapak 1.0] [--onayli_mp4 O.mp4] [--oz-test]
  8) (Serdar 25 Kas) --kapak verilirse: ilk kare = kapak, son kare = kapak, ilk kare = son kare (ort. fark < 2.0).
"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

SON_ALT, SON_UST = 3.0, 4.0
BANT1 = (576, 704)        # son kart 1. satiri "Make it yours" (CY - 130 = 640)


def kareler(d):
    return {float(os.path.basename(f).split('kare_')[1][:-5]): f for f in glob.glob(os.path.join(d, '*-kare_*.jpg'))}


def esitlik(bd, pd, son_fo):
    kb, kp = kareler(bd), kareler(pd)
    ts = [t for t in sorted(kb) if 1.5 <= t < son_fo]
    if not ts or set(kb) != set(kp):
        return [('kare listesi (1.5 sn sonrasi, ayni)', False, f'{sorted(kb)} / {sorted(kp)}')]
    S = []
    for t in ts:
        d = int(np.abs(np.asarray(Image.open(kb[t])).astype(int) - np.asarray(Image.open(kp[t])).astype(int)).max())
        S.append((f'kare {t:g}s onayli P ile ayni', d == 0, f'max {d}'))
    return S


def probe(v):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration',
                        '-of', 'json', v], capture_output=True, text=True)
    return json.loads(r.stdout)['streams'] if r.returncode == 0 else None


def video(v, sure):
    st = probe(v)
    if not st:
        return [('video okunur', False, v)]
    vs = [s for s in st if s['codec_type'] == 'video']; au = [s for s in st if s['codec_type'] == 'audio']
    s = vs[0]; nf = int(round(30 * sure))
    return [('1080x1920', (s['width'], s['height']) == (1080, 1920), f"{s['width']}x{s['height']}"),
            ('30 fps', s['r_frame_rate'] == '30/1', s['r_frame_rate']),
            (f'{nf} kare', str(s.get('nb_frames')) == str(nf), str(s.get('nb_frames'))),
            (f'{sure:g} sn (>= {sure:g}, <= +0.05)', sure <= float(s['duration']) <= sure + 0.05, s['duration']),
            ('h264', s['codec_name'] == 'h264', s['codec_name']),
            (f'ses {sure:g} sn', bool(au) and abs(float(au[0]['duration']) - sure) <= 0.05, au[0]['duration'] if au else 'ses yok')]


def son_kart_sure(v, ref_sn):
    """Son kart gorunurlugu: tam karttaki (ref) yazi maskesinde parlaklik - bant icindeki yazi disi parlaklik. Duvar sahnesinde
    iki bolge birlikte parlak oldugu icin fark ~0; son kartta yazi parlak, zemin lacivert. Gorunur >= tepenin %10'u, tam >= %90."""
    t = tempfile.mkdtemp()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '9.0', '-i', v, '-vf', 'fps=10', os.path.join(t, 'k_%04d.png')], check=True)
    fs = sorted(glob.glob(os.path.join(t, 'k_*.png')))
    br = [np.asarray(Image.open(f).convert('L')).astype(float)[BANT1[0]:BANT1[1]] for f in fs]
    if not br:
        return 0.0, 0.0
    ref = br[min(len(br) - 1, int(round((ref_sn - 9.0) * 10)))]   # tam son kart karesi (sure - 2 sn)
    m = ref > 120
    if m.sum() < 50:
        return 0.0, 0.0
    fark = [float(x[m].mean() - x[~m].mean()) for x in br]
    tepe = max(fark)
    gor = sum(1 for x in fark if x >= 0.1 * tepe) / 10.0
    tam = sum(1 for x in fark if x >= 0.9 * tepe) / 10.0
    return gor, tam


def lufs(m):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', m, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
    v = [l for l in r.stderr.splitlines() if l.strip().startswith('I:')]
    return float(v[-1].split()[1]) if v else None


def kiyas(v, o, ts, ofs=0.0):
    t = tempfile.mkdtemp(); out = []
    for s in ts:
        a, b = os.path.join(t, 'a.png'), os.path.join(t, 'b.png')
        for src, dst, ss in ((v, a, s), (o, b, s + ofs)):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ss}', '-i', src, '-frames:v', '1', dst], check=True)
        d = np.abs(np.asarray(Image.open(a).convert('RGB')).astype(int) - np.asarray(Image.open(b).convert('RGB')).astype(int))
        out.append((s, float(d.mean()), float(np.percentile(d, 99))))
    return out


def kapilar(g):
    bi = json.load(open(g.bilgi))
    son_bas = round(19.6 - bi['T_B0'], 3); son_fo = round(g.sure - 0.9, 3)
    S = esitlik(g.b, g.p, son_fo)
    sk = round(g.sure - (g.son_kapak or 0.0) - son_bas, 3)     # sonda kapak varsa son kart kapak gecisinde biter
    S.append((f'son kart {SON_ALT:g}-{SON_UST:g} sn', SON_ALT <= sk <= SON_UST, f'{sk} sn ({son_bas}-{g.sure:g})'))
    if g.video:
        S += video(g.video, g.sure)
    if g.video:
        gor, tam = son_kart_sure(g.video, g.sure - 2.0)
        S.append((f'son kart ekranda (olculen) {SON_ALT:g}-{SON_UST:g} sn', SON_ALT <= gor <= SON_UST, f'gorunur {gor:.1f} sn, tam {tam:.1f} sn'))
    if g.muzik:
        L = lufs(g.muzik)
        S.append(('muzik -16 LUFS +-1.0', L is not None and abs(L + 16) <= 1.0, L))
    if g.video and g.onayli_mp4:
        for s_, m, p in kiyas(g.video, g.onayli_mp4, [2, 5, 8, 10.5]):
            S.append((f'onayli P mp4 kare {s_:g}s ort <= 2.0 ve p99 <= 10', m <= 2.0 and p <= 10, f'ort {m:.2f} p99 {p:.0f}'))
    if g.kapak_qc:
        q = json.load(open(g.kapak_qc)) if os.path.exists(g.kapak_qc) else {}
        S.append(('kapak_basa QC PASS', q.get('sonuc') == 'PASS', q.get('sonuc', 'yok')))
    if g.kapak_son_qc:
        q = json.load(open(g.kapak_son_qc)) if os.path.exists(g.kapak_son_qc) else {}
        S.append(('kapak_son QC PASS', q.get('sonuc') == 'PASS', q.get('sonuc', 'yok')))
    if g.video and g.kapak:
        S += ilk_son(g.video, g.kapak)
    return S, son_bas, son_fo


def mp4_kare(v, son=False):
    t = tempfile.mkdtemp(); o = os.path.join(t, 'k.png')
    a = ['ffmpeg', '-v', 'error', '-y'] + (['-sseof', '-0.1'] if son else []) + ['-i', v] + (['-update', '1'] if son else ['-frames:v', '1']) + [o]
    subprocess.run(a, check=True)
    return np.asarray(Image.open(o).convert('RGB')).astype(float)


def kapak_dizi(k, W, H):
    im = Image.open(k).convert('RGB'); s_ = max(W / im.size[0], H / im.size[1])
    im = im.resize((round(im.size[0] * s_), round(im.size[1] * s_)), Image.LANCZOS)
    x0 = (im.size[0] - W) // 2; y0 = (im.size[1] - H) // 2
    return np.asarray(im.crop((x0, y0, x0 + W, y0 + H))).astype(float)


def ilk_son(v, kapak, ilk=None, son=None):
    """Serdar 25 Kas: video kapakla baslar, kapakla biter; ilk kare = son kare (ort. fark < 2.0, kapak_basa ESIK)."""
    ilk = mp4_kare(v) if ilk is None else ilk; son = mp4_kare(v, son=True) if son is None else son
    K = kapak_dizi(kapak, ilk.shape[1], ilk.shape[0])
    d1, d2, d3 = (float(np.abs(x - y).mean()) for x, y in ((ilk, K), (son, K), (ilk, son)))
    return [('ilk kare = kapak (ort < 2.0)', d1 < 2.0, round(d1, 2)), ('son kare = kapak (ort < 2.0)', d2 < 2.0, round(d2, 2)),
            ('ilk kare = son kare (ort < 2.0)', d3 < 2.0, round(d3, 2))]


def main():
    ap = argparse.ArgumentParser()
    for k in ('b', 'p', 'bilgi'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--sure', type=float, required=True); ap.add_argument('--video'); ap.add_argument('--kapak_qc')
    ap.add_argument('--onayli_mp4'); ap.add_argument('--muzik'); ap.add_argument('--oz-test', action='store_true')
    ap.add_argument('--kapak', help='onayli kapak (ilk = son kare kapisi)'); ap.add_argument('--kapak_son_qc')
    ap.add_argument('--son_kapak', type=float, default=0.0, help='sondaki kapak tam + gecis suresi (sn)')
    g = ap.parse_args()
    S, son_bas, son_fo = kapilar(g)
    if g.oz_test:
        sonuc = [('bilinen PASS (tum kapilar)', all(o for _, o, _ in S))]
        t = tempfile.mkdtemp()
        for f in glob.glob(os.path.join(g.b, '*-kare_*.jpg')):
            shutil.copy(f, t)
        k = kareler(t); f0 = k[min(x for x in k if x >= 1.5)]
        a = np.asarray(Image.open(f0)).copy(); a[300:320, 300:320] = 255; Image.fromarray(a).save(f0, quality=95)
        sonuc.append(('FAIL: bozuk kare', not all(o for _, o, _ in esitlik(t, g.p, son_fo))))
        g24 = argparse.Namespace(**{**vars(g), 'sure': 24.0, 'video': None, 'kapak_qc': None, 'muzik': None, 'onayli_mp4': None,
                                    'kapak_son_qc': None, 'kapak': None, 'son_kapak': 0.0})
        sonuc.append(('FAIL: 24 sn (son kart 13 sn)', not all(o for a, o, _ in kapilar(g24)[0] if a.startswith('son kart'))))
        if g.video:
            sonuc.append(('FAIL: yanlis sure beklentisi', not all(o for _, o, _ in video(g.video, g.sure + 1))))
        if g.video and g.kapak:
            # bilinen FAIL: son kare yerine 8. saniye karesi (kapakla bitmeyen video)
            t8 = tempfile.mkdtemp(); o8 = os.path.join(t8, 'k8.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '8', '-i', g.video, '-frames:v', '1', o8], check=True)
            k8 = np.asarray(Image.open(o8).convert('RGB')).astype(float)
            sonuc.append(('FAIL: kapakla bitmeyen video', not all(o for _, o, _ in ilk_son(g.video, g.kapak, son=k8))))
        if g.video and g.onayli_mp4:
            # bilinen FAIL: 3 sn kaymis kare (ayni olmayan goruntu) kiyas kapisini gecemez
            sonuc.append(('FAIL: kaymis kare kiyasi', any(m > 2.0 or p > 10 for _, m, p in kiyas(g.video, g.onayli_mp4, [5], ofs=3.0))))
            # bilinen FAIL: onayli 24 sn P videosunda son kart ~13 sn, 3-4 sn kapisini gecemez
            gor, _ = son_kart_sure(g.onayli_mp4, 22.0)
            sonuc.append((f'FAIL: 24 sn videoda olculen son kart ({gor:.1f} sn)', not (SON_ALT <= gor <= SON_UST)))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    for ad, o, d in S:
        print(f"{'PASS' if o else 'FAIL'} {ad} | {d}")
    sys.exit(0 if all(o for _, o, _ in S) else 1)


if __name__ == '__main__':
    main()
