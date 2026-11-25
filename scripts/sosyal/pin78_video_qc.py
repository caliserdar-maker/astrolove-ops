#!/usr/bin/env python3
"""Pinterest 78 cift video ornegi QC (Serdar 25 Kas 2026, KARARLAR_20261125_49/_50).
Video = onayli sosyal video (video_v9) acilis B (poster karesi yok) + --sure 15 (son kart kisa) + onayli kapak_v1 kapagi
kapak_basa.py ile 0-0.5 sn tam, 0.5-1.0 sn gecis. Son kart metni onayli (degismez).
Kapilar (PASS/FAIL):
  1) Render esitligi: B/15 sn kareleri, onayli P/24 sn kareleriyle (ayni poster, ayni kod) 1.5 <= t < SON_FO arasinda fark 0.
  2) Son kart suresi: sure - (19.6 - T_B0) 3.0-4.0 sn (Serdar "3-4 sn").
  3) Son mp4: 1080x1920, 30 fps, kare = 30 x sure, sure +-0.05, h264, ses = sure +-0.05.
  4) kapak_basa QC json: sonuc PASS (ilk kare = kapak < 2.0, 0-1.5 sn parlaklik, kayma, kare/sure/ses ayni).
Bilgi: onayli Drive P videosu ile son mp4 kare farki (iki kodlama; esik olculmeden kapi yok).
Kullanim: pin78_video_qc.py --b DIR --p DIR --bilgi bilgi.json --sure 15 --video V.mp4 --kapak_qc Q.json [--onayli_mp4 O.mp4] [--oz-test]
"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

SON_ALT, SON_UST = 3.0, 4.0


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
            (f'{sure:g} sn', abs(float(s['duration']) - sure) <= 0.05, s['duration']),
            ('h264', s['codec_name'] == 'h264', s['codec_name']),
            (f'ses {sure:g} sn', bool(au) and abs(float(au[0]['duration']) - sure) <= 0.05, au[0]['duration'] if au else 'ses yok')]


def kiyas(v, o, ts):
    t = tempfile.mkdtemp(); out = []
    for s in ts:
        a, b = os.path.join(t, 'a.png'), os.path.join(t, 'b.png')
        for src, dst in ((v, a), (o, b)):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s}', '-i', src, '-frames:v', '1', dst], check=True)
        d = np.abs(np.asarray(Image.open(a).convert('RGB')).astype(int) - np.asarray(Image.open(b).convert('RGB')).astype(int))
        out.append(f'{s:g}s ort {d.mean():.2f} p99 {np.percentile(d, 99):.0f}')
    return out


def kapilar(g):
    bi = json.load(open(g.bilgi))
    son_bas = round(19.6 - bi['T_B0'], 3); son_fo = round(g.sure - 0.9, 3)
    S = esitlik(g.b, g.p, son_fo)
    sk = round(g.sure - son_bas, 3)
    S.append((f'son kart {SON_ALT:g}-{SON_UST:g} sn', SON_ALT <= sk <= SON_UST, f'{sk} sn ({son_bas}-{g.sure:g})'))
    if g.video:
        S += video(g.video, g.sure)
    if g.kapak_qc:
        q = json.load(open(g.kapak_qc)) if os.path.exists(g.kapak_qc) else {}
        S.append(('kapak_basa QC PASS', q.get('sonuc') == 'PASS', q.get('sonuc', 'yok')))
    return S, son_bas, son_fo


def main():
    ap = argparse.ArgumentParser()
    for k in ('b', 'p', 'bilgi'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--sure', type=float, required=True); ap.add_argument('--video'); ap.add_argument('--kapak_qc')
    ap.add_argument('--onayli_mp4'); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    S, son_bas, son_fo = kapilar(g)
    if g.oz_test:
        sonuc = [('bilinen PASS (kare + son kart)', all(o for a, o, _ in S if a.startswith('kare') or a.startswith('son kart')))]
        t = tempfile.mkdtemp()
        for f in glob.glob(os.path.join(g.b, '*-kare_*.jpg')):
            shutil.copy(f, t)
        k = kareler(t); f0 = k[min(x for x in k if x >= 1.5)]
        a = np.asarray(Image.open(f0)).copy(); a[300:320, 300:320] = 255; Image.fromarray(a).save(f0, quality=95)
        sonuc.append(('FAIL: bozuk kare', not all(o for _, o, _ in esitlik(t, g.p, son_fo))))
        g24 = argparse.Namespace(**{**vars(g), 'sure': 24.0, 'video': None, 'kapak_qc': None})
        sonuc.append(('FAIL: 24 sn (son kart 13 sn)', not all(o for a, o, _ in kapilar(g24)[0] if a.startswith('son kart'))))
        if g.video:
            sonuc.append(('FAIL: yanlis sure beklentisi', not all(o for _, o, _ in video(g.video, g.sure + 1))))
        for ad, v in sonuc:
            print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
        sys.exit(0 if all(v for _, v in sonuc) else 1)
    for ad, o, d in S:
        print(f"{'PASS' if o else 'FAIL'} {ad} | {d}")
    if g.video and g.onayli_mp4:
        for s in kiyas(g.video, g.onayli_mp4, [2, 5, 8, 10.5]):
            print('BILGI onayli P mp4 kiyas ' + s)
    sys.exit(0 if all(o for _, o, _ in S) else 1)


if __name__ == '__main__':
    main()
