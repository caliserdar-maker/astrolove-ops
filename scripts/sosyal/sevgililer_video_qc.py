#!/usr/bin/env python3
"""Sevgililer video ornegi QC (25 Kas 2026; bagimsiz inceleme 1. tur duzeltmesi).
Onayli sosyal video (video_v9 --acilis P, onayli _POSTER2000 posteri) ile Sevgililer surumu ayni kodla uretilir; tek fark son
kartin 3. satiri (--son_alt; "Make it yours" CTA'si ve ASTROLOVEART aynen). Kapilar (PASS/FAIL):
  1) Son kart oncesi kareler (t <= SON_BAS = 19.6 - T_B0): onayli metinli render ile Sevgililer render'i TAM karede fark 0.
  2) Son kart kareleri (t > SON_BAS): BANT disinda fark 0; BANT icinde fark > 0 (satir gercekten degisti).
  3) Son karede BANT icinde parlak piksel orani >= %0.5 (yazi var; bos bantta %0, bilinen FAIL oz-testte).
  4) Video: 1080x1920, 30 fps, 720 kare, 24.0 sn (+-0.05), h264, ses 24.0 sn (LUFS ayrica muzik_ekle.py).
  5) Metin: etsy_common.METIN_KESIN (tek kaynak) + "free".
Bilgi (kapi degil): --onayli_mp4 verilirse onayli Drive videosu ile son mp4'ten cikarilan karelerin ortalama farki yazilir
(iki ayri H.264 kodlama; esik olculmeden kapi konmaz, CLAUDE.md KALITE 4).
Kullanim: sevgililer_video_qc.py --onayli DIR --yeni DIR --son_bas SN --metin T [--video V.mp4] [--onayli_mp4 O.mp4] [--oz-test]
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'scripts', 'etsy'))
from etsy_common import METIN_KESIN  # noqa: E402

BANT = (848, 960)        # son kart 3. satiri (olculdu 25 Kas: fark y 876-933); kenarlar JPEG 16 px blok sinirinda (848 = 53x16)


def yasak(metin):
    bul = [ad for ad, rx in METIN_KESIN if re.search(rx, metin, re.I)]
    if re.search(r'\bfree\b', metin, re.I):
        bul.append('free')
    return bul


def kareler(d):
    return {float(os.path.basename(f).split('kare_')[1][:-5]): f for f in glob.glob(os.path.join(d, '*-kare_*.jpg'))}


def kare_kapilari(onayli, yeni, son_bas):
    ko, ky = kareler(onayli), kareler(yeni)
    if not ko or set(ko) != set(ky):
        return [('kare listesi ayni', False, f'{sorted(ko)} / {sorted(ky)}')]
    S = []
    if not any(t <= son_bas for t in ko) or not any(t > son_bas for t in ko):
        S.append(('kareler son kart oncesi ve sonrasini kapsar', False, str(sorted(ko))))
    for t in sorted(ko):
        a = np.asarray(Image.open(ko[t])).astype(int); b = np.asarray(Image.open(ky[t])).astype(int)
        d = np.abs(a - b)
        if t <= son_bas:          # son_bas karesinde son kart henuz gorunmez (ease = 0)
            S.append((f'kare {t:g}s (son kart oncesi) tam karede fark 0', int(d.max()) == 0, f'max {int(d.max())}'))
        else:
            m = np.ones(a.shape[:2], bool); m[BANT[0]:BANT[1]] = False
            S.append((f'kare {t:g}s bant disi fark 0', int(d[m].max()) == 0, f'max {int(d[m].max())}'))
            S.append((f'kare {t:g}s bantta satir degisti', int(d[~m].max()) > 0, f'bant max {int(d[~m].max())}'))
    son = max(ky)
    b = np.asarray(Image.open(ky[son])).astype(int)
    oran = float((b[BANT[0]:BANT[1]].max(2) > 120).mean())
    S.append((f'son karede ({son:g}s) yeni satir gorunur (>= %0.5 parlak)', oran >= 0.005, f'oran {oran:.4f}'))
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
    return [('1080x1920', (s['width'], s['height']) == (1080, 1920), f"{s['width']}x{s['height']}"),
            ('30 fps', s['r_frame_rate'] == '30/1', s['r_frame_rate']),
            ('720 kare', str(s.get('nb_frames')) == '720', str(s.get('nb_frames'))),
            ('24.0 sn', abs(float(s['duration']) - 24.0) <= 0.05, s['duration']),
            ('h264', s['codec_name'] == 'h264', s['codec_name']),
            ('ses 24.0 sn', bool(au) and abs(float(au[0]['duration']) - 24.0) <= 0.05, au[0]['duration'] if au else 'ses yok')]


def mp4_kare(v, t, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t}', '-i', v, '-frames:v', '1', out], check=True)
    return np.asarray(Image.open(out).convert('RGB')).astype(int)


def mp4_kiyas(yeni, onayli, son_bas):
    t = tempfile.mkdtemp(); out = []
    for s in (0.5, 3, 7, 10, son_bas + 1.0, 23.5):
        a = mp4_kare(yeni, s, os.path.join(t, 'a.png')); b = mp4_kare(onayli, s, os.path.join(t, 'b.png'))
        d = np.abs(a - b)
        m = np.ones(d.shape[:2], bool)
        if s >= son_bas:
            m[BANT[0]:BANT[1]] = False
        out.append(f'{s:g}s ort {d[m].mean():.2f} p99 {np.percentile(d[m], 99):.0f}')
    return out


def oz_test(onayli, yeni, son_bas):
    sonuc = []
    sonuc.append(('bilinen PASS', all(ok for _, ok, _ in kare_kapilari(onayli, yeni, son_bas))))
    # FAIL 1: onayli metin = yeni metin (satir degismedi)
    sonuc.append(('FAIL: satir degismedi', not all(ok for _, ok, _ in kare_kapilari(onayli, onayli, son_bas))))
    # FAIL 2: son kart oncesi karede bozulma
    t = tempfile.mkdtemp()
    for f in glob.glob(os.path.join(yeni, '*-kare_*.jpg')):
        shutil.copy(f, t)
    k = kareler(t); f0 = k[min(k)]
    a = np.asarray(Image.open(f0)).copy(); a[100:120, 100:120] = 255; Image.fromarray(a).save(f0, quality=95)
    sonuc.append(('FAIL: son kart oncesi bozulma', not all(ok for _, ok, _ in kare_kapilari(onayli, t, son_bas))))
    # FAIL 3: son karede bant bos (yazi yok)
    t2 = tempfile.mkdtemp()
    for f in glob.glob(os.path.join(yeni, '*-kare_*.jpg')):
        shutil.copy(f, t2)
    k2 = kareler(t2); fs = k2[max(k2)]
    a = np.asarray(Image.open(fs)).copy(); a[BANT[0]:BANT[1]] = a[BANT[0] - 60:BANT[0] - 60 + 1].repeat(BANT[1] - BANT[0], 0) * 0
    Image.fromarray(a).save(fs, quality=95)
    sonuc.append(('FAIL: son kartta yazi yok', not all(ok for _, ok, _ in kare_kapilari(onayli, t2, son_bas))))
    # FAIL 4: yasak metin (gercek yasak() fonksiyonu)
    sonuc.append(('FAIL: yasak metin yakalanir', bool(yasak('A free Valentine’s gift — premium'))))
    for ad, v in sonuc:
        print(('PASS ' if v else 'FAIL ') + 'oz-test ' + ad)
    return all(v for _, v in sonuc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--onayli', required=True); ap.add_argument('--yeni', required=True)
    ap.add_argument('--son_bas', type=float, required=True); ap.add_argument('--metin', required=True)
    ap.add_argument('--video'); ap.add_argument('--onayli_mp4'); ap.add_argument('--oz-test', action='store_true')
    g = ap.parse_args()
    if g.oz_test:
        sys.exit(0 if oz_test(g.onayli, g.yeni, g.son_bas) else 1)
    S = kare_kapilari(g.onayli, g.yeni, g.son_bas)
    y = yasak(g.metin)
    S.append(('metin yasak ifade yok (METIN_KESIN + free)', not y, f'{g.metin} {y}'))
    if g.video:
        S += video_kapilari(g.video)
    for ad, ok, det in S:
        print(f"{'PASS' if ok else 'FAIL'} {ad} | {det}")
    if g.video and g.onayli_mp4:
        for s in mp4_kiyas(g.video, g.onayli_mp4, g.son_bas):
            print('BILGI onayli mp4 kiyas ' + s)
    sys.exit(0 if all(ok for _, ok, _ in S) else 1)


if __name__ == '__main__':
    main()
