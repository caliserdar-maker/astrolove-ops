#!/usr/bin/env python3
"""K1 ornek QC (19 Eki 2026): eski / A / B acilislarinin olcumu + KONTAK.jpg. Tek script, PASS/FAIL.

Girdi DIR: ESKI_<CIFT>.mp4, A_<CIFT>.mp4, B_<CIFT>.mp4, bilgi_eski.json (video_uret.py --bilgi), muzik.m4a.
Olcumler (gri, 1080x1920 kare):
  parlaklik        karenin gri ortalamasi
  r_sembol         birlesik sembol kutusunda (bilgi.sembol_kutu) kare ile referans arasindaki korelasyon
                   (ikisi de gauss sigma 3; kamera yakinlasmasi %0-3 farki tolere edilir). Referans: ESKI, T_B0 + 0.5 sn
                   (sembol tam, toz yok).
  r_ad             burc adlari bandi (etiket_y .. +70 px, tum genislik) ve soru metni bandi (soru_y +-60 px):
                   referans ESKI 3.0 sn (ikisi de tam gorunur, solma 3.3 sn'de baslar). B'de soru metni yok (tasarim geregi).
  okunur           r >= 0.9
Kapilar (A ve B): 0. kare parlaklik > 0; 0. karede r_sembol >= 0.9 ve r_ad(etiket) >= 0.9; 1080x1920, 720 kare,
  video 24.0 sn (+-0.05); ses akisi var, 24.0 sn (+-0.05); ses paketleri muzik dosyasiyla ayni (md5) -> yumusak giris/cikis
  korunur; RMS (dBFS) 0-0.2 sn < 1-2 sn ve 23.8-24 sn < 22-23 sn.
Kullanim: k1_qc.py DIR CIFT"""
import hashlib, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ESIK_R = 0.9
SN = [0, 0.5, 1, 2, 3]


def kare(v, t):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-ss', f'{t:.3f}', '-frames:v', '1', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(1920, 1080, 3)


def gri(a):
    return np.asarray(Image.fromarray(a).convert('L').filter(ImageFilter.GaussianBlur(3)), np.float32)


def kor(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return round(float((a * b).sum() / d), 3) if d > 0 else 0.0


def probe(v):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', v],
                                  capture_output=True, text=True, check=True).stdout)
    vs = next(s for s in j['streams'] if s['codec_type'] == 'video')
    au = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    return {'boyut': f"{vs['width']}x{vs['height']}", 'kare': int(vs.get('nb_read_frames') or 0),
            'video_sn': round(float(vs['duration']), 3), 'ses': au is not None,
            'ses_sn': round(float(au['duration']), 3) if au else None}


def ses_md5(v):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-map', '0:a', '-c', 'copy', '-f', 'md5', '-'],
                       capture_output=True, text=True)
    return r.stdout.strip()


def rms(v):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-map', '0:a', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                       capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    db = lambda a, b: round(float(20 * np.log10(np.sqrt(np.mean(x[int(a * 48000):int(b * 48000)] ** 2)) + 1e-9)), 1)
    return {'0-0.2': db(0, 0.2), '1-2': db(1, 2), '22-23': db(22, 23), '23.8-24': db(23.8, 24)}


def main():
    d, cift = sys.argv[1], sys.argv[2]
    bi = json.load(open(os.path.join(d, 'bilgi_eski.json')))
    x, y, w, h = bi['sembol_kutu']; ey, sy = bi['etiket_y'], bi['soru_y']
    kut = {'sembol': (slice(max(0, y), y + h), slice(max(0, x), x + w)),
           'etiket': (slice(ey - 10, ey + 70), slice(0, 1080)), 'soru': (slice(sy - 60, sy + 60), slice(0, 1080))}
    V = {k: os.path.join(d, f'{k}_{cift}.mp4') for k in ('ESKI', 'A', 'B')}
    ref_s = gri(kare(V['ESKI'], bi['T_B0'] + 0.5)); ref_a = gri(kare(V['ESKI'], 3.0))

    def olc(a):
        g = gri(a)
        return {'parlaklik': round(float(np.asarray(Image.fromarray(a).convert('L'), np.float32).mean()), 2),
                'r_sembol': kor(g[kut['sembol']], ref_s[kut['sembol']]),
                'r_etiket': kor(g[kut['etiket']], ref_a[kut['etiket']]), 'r_soru': kor(g[kut['soru']], ref_a[kut['soru']])}

    muz = ses_md5(os.path.join(d, 'muzik.m4a'))
    S, KAR, rc = {}, {}, 0
    for k, v in V.items():
        p = probe(v); m = ses_md5(v); r = rms(v)
        kr = {t: kare(v, t) for t in SN}; KAR[k] = kr
        o = {t: olc(a) for t, a in kr.items()}
        S[k] = {'probe': p, 'ses_md5_ayni': m == muz and bool(m), 'rms_db': r, 'kareler': {str(t): o[t] for t in SN}}
        if k != 'ESKI':
            o0 = o[0]
            kapi = {'parlaklik_0>0': o0['parlaklik'] > 0, 'sembol_0_okunur': o0['r_sembol'] >= ESIK_R,
                    'ad_0_okunur': o0['r_etiket'] >= ESIK_R, 'boyut': p['boyut'] == '1080x1920', 'kare_720': p['kare'] == 720,
                    'video_24': abs(p['video_sn'] - 24) <= 0.05, 'ses_var': p['ses'],
                    'ses_24': p['ses_sn'] is not None and abs(p['ses_sn'] - 24) <= 0.05,
                    'muzik_ayni': S[k]['ses_md5_ayni'], 'yumusak_giris': r['0-0.2'] < r['1-2'], 'yumusak_cikis': r['23.8-24'] < r['22-23']}
            S[k]['kapi'] = kapi; S[k]['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL'
            rc |= S[k]['sonuc'] != 'PASS'
    # 1) ESKI zaman cizelgesi: ad ve sembol hangi saniyede okunur (0.1 sn adim)
    zc = {}
    for t in [i / 10 for i in range(0, 31)] + [i / 10 for i in range(60, 101)]:
        zc[f'{t:.1f}'] = olc(kare(V['ESKI'], t))
    ilk = lambda key: next((float(t) for t, o in zc.items() if o[key] >= ESIK_R), None)
    S['ESKI']['okunur_ilk_sn'] = {'etiket': ilk('r_etiket'), 'soru_metni': ilk('r_soru'), 'sembol': ilk('r_sembol')}
    S['ESKI']['zaman_cizelgesi'] = zc
    S['bilgi'] = bi
    json.dump(S, open(os.path.join(d, 'K1_QC.json'), 'w'), indent=1)

    # KONTAK: 3 satir (eski / A / B) x 5 sutun (0 / 0.5 / 1 / 2 / 3 sn), 9:16
    tw, th, ust, sol = 324, 576, 44, 110
    K = Image.new('RGB', (sol + tw * 5 + 8 * 4, ust + (th + 8) * 3), (245, 245, 245)); dr = ImageDraw.Draw(K)
    try:
        f = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
    except OSError:
        f = ImageFont.load_default()
    for j, t in enumerate(SN):
        dr.text((sol + j * (tw + 8) + 8, 8), f'{t:g} sn', fill=(0, 0, 0), font=f)
    for i, k in enumerate(('ESKI', 'A', 'B')):
        yy = ust + i * (th + 8); dr.text((10, yy + th // 2 - 14), k, fill=(0, 0, 0), font=f)
        for j, t in enumerate(SN):
            K.paste(Image.fromarray(KAR[k][t]).resize((tw, th), Image.LANCZOS), (sol + j * (tw + 8), yy))
    K.save(os.path.join(d, 'KONTAK.jpg'), quality=92)

    print(f"T_LAND_END {bi['T_LAND_END']} sn, T_B0 (B baslangici) {bi['T_B0']} sn")
    print(f"ESKI okunur ilk sn (r>={ESIK_R}): {S['ESKI']['okunur_ilk_sn']}")
    for k in ('ESKI', 'A', 'B'):
        print(k, {t: (o['parlaklik'], o['r_sembol'], o['r_etiket'], o['r_soru']) for t, o in S[k]['kareler'].items()},
              S[k]['probe'], 'rms', S[k]['rms_db'], 'muzik_ayni', S[k]['ses_md5_ayni'], S[k].get('sonuc', ''))
        if 'kapi' in S[k]:
            print(k, 'KAPI', {a: ('PASS' if b else 'FAIL') for a, b in S[k]['kapi'].items()})
    print('SONUC', 'PASS' if rc == 0 else 'FAIL')
    return rc


if __name__ == '__main__':
    sys.exit(main())
