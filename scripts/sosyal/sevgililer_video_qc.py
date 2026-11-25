#!/usr/bin/env python3
"""Sevgililer video ornegi QC (25 Kas 2026). Onayli sosyal video (video_v9 --acilis P) ile Sevgililer surumu ayni kodla,
ayni posterle uretilir; tek fark son kartin ilk satiri (--son_satir). Kapilar (PASS/FAIL):
  1) Kare esitligi: onayli metinli ve Sevgililer metinli kareler, son kart ilk satir bandi (y BANT) DISINDA birebir ayni (max fark 0).
  2) Son karede yazi var: Sevgililer karesinde bant icinde parlak piksel orani >= %0.5 (bos bantta %0).
  3) Video: 1080x1920, 30 fps, 720 kare, 24.0 sn (+-0.05), h264; ses 24.0 sn (muzik_ekle.py ayrica LUFS kapisi).
  4) Metin: uzun/orta tire, "free", "premium" yok.
Kullanim: sevgililer_video_qc.py --onayli DIR --yeni DIR --video V.mp4 --metin "A Valentine's gift" [--oz-test]
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
from PIL import Image

BANT = (575, 705)        # son kart ilk satiri: CY-130 = 640 merkezli (olculdu 25 Kas: fark bolgesi y 591-689)
YASAK = ['—', '–', 'free', 'premium']


def kareler(d):
    return {os.path.basename(f).split('kare_')[1]: f for f in glob.glob(os.path.join(d, '*-kare_*.jpg'))}


def kare_kapilari(onayli, yeni, degisik=True):
    S = []
    ko, ky = kareler(onayli), kareler(yeni)
    if not ko or set(ko) != set(ky):
        return [('kare listesi ayni', False, f'{sorted(ko)} / {sorted(ky)}')]
    yazi_var = False
    for k in sorted(ko, key=lambda s: float(s[:-5])):
        a = np.asarray(Image.open(ko[k])).astype(int); b = np.asarray(Image.open(ky[k])).astype(int)
        m = np.ones(a.shape[:2], bool); m[BANT[0]:BANT[1]] = False
        mx = int(np.abs(a - b)[m].max())
        S.append((f'kare {k} bant disi fark 0', mx == 0, f'max {mx}'))
        oran = float((b[BANT[0]:BANT[1]].max(2) > 120).mean())
        if oran >= 0.005:
            yazi_var = True
    S.append(('son kartta yeni satir gorunur (>= %0.5 parlak)', yazi_var, ''))
    son = sorted(ko, key=lambda s: float(s[:-5]))[-1]
    bd = int(np.abs(np.asarray(Image.open(ko[son])).astype(int) - np.asarray(Image.open(ky[son])).astype(int))[BANT[0]:BANT[1]].max())
    S.append((f'son karede ({son}) satir onayli metinden farkli', bd > 0 or not degisik, f'bant max fark {bd}'))
    return S


def video_kapilari(v):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration',
                        '-of', 'json', v], capture_output=True, text=True)
    if r.returncode:
        return [('video okunur', False, r.stderr[-200:])]
    st = json.loads(r.stdout)['streams']
    vs = [s for s in st if s['codec_type'] == 'video']; au = [s for s in st if s['codec_type'] == 'audio']
    if not vs:
        return [('video akisi var', False, '')]
    s = vs[0]
    S = [('1080x1920', (s['width'], s['height']) == (1080, 1920), f"{s['width']}x{s['height']}"),
         ('30 fps', s['r_frame_rate'] == '30/1', s['r_frame_rate']),
         ('720 kare', str(s.get('nb_frames')) == '720', str(s.get('nb_frames'))),
         ('24.0 sn', abs(float(s['duration']) - 24.0) <= 0.05, s['duration']),
         ('h264', s['codec_name'] == 'h264', s['codec_name']),
         ('ses 24.0 sn', bool(au) and abs(float(au[0]['duration']) - 24.0) <= 0.05, au[0]['duration'] if au else 'ses yok')]
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--onayli', required=True); ap.add_argument('--yeni', required=True)
    ap.add_argument('--video'); ap.add_argument('--metin', required=True); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    S = kare_kapilari(g.onayli, g.yeni)
    S.append(('metin yasak ifade yok', not any(y in g.metin.lower() for y in YASAK), g.metin))
    if g.video:
        S += video_kapilari(g.video)
    if g.oz_test:
        # bilinen PASS: onayli kareler kendileriyle -> fark 0 ama yazi kapisi? onayli karede de "Make it yours" var (PASS beklenir)
        p = all(ok for _, ok, _ in kare_kapilari(g.onayli, g.onayli, degisik=False)) and not all(ok for _, ok, _ in kare_kapilari(g.onayli, g.onayli))
        # bilinen FAIL: bant disinda bozulmus kare
        import tempfile, shutil
        t = tempfile.mkdtemp()
        for f in glob.glob(os.path.join(g.yeni, '*-kare_*.jpg')):
            shutil.copy(f, t)
        f0 = sorted(glob.glob(os.path.join(t, '*-kare_*.jpg')))[0]
        a = np.asarray(Image.open(f0)).copy(); a[100:120, 100:120] = 255; Image.fromarray(a).save(f0, quality=95)
        fl = not all(ok for _, ok, _ in kare_kapilari(g.onayli, t))
        # bilinen FAIL: yasak metin
        fm = any(y in 'Free Valentine gift'.lower() for y in YASAK)
        print(f"{'PASS' if p else 'FAIL'} oz-test bilinen PASS\n{'PASS' if fl else 'FAIL'} oz-test bant disi bozulma FAIL verir\n"
              f"{'PASS' if fm else 'FAIL'} oz-test yasak metin FAIL verir")
        sys.exit(0 if (p and fl and fm) else 1)
    for ad, ok, det in S:
        print(f"{'PASS' if ok else 'FAIL'} {ad} | {det}")
    sys.exit(0 if all(ok for _, ok, _ in S) else 1)


if __name__ == '__main__':
    main()
