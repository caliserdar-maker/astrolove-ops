#!/usr/bin/env python3
"""K1 ornek QC (19 Eki 2026): eski / A / B acilislarinin olcumu + KONTAK.jpg. Tek script, PASS/FAIL.

Girdi DIR: ESKI_<CIFT>.mp4, A_<CIFT>.mp4, B_<CIFT>.mp4, bilgi_eski.json (video_uret.py --bilgi), muzik.m4a.
Olcumler (gri, 1080x1920 kare):
  parlaklik        karenin gri ortalamasi
  r_sembol         birlesik sembol kutusunda (bilgi.sembol_kutu) kare ile referans arasindaki korelasyon (gauss sigma 3).
                   Referans: ESKI, T_B0 + 0.5 sn (sembol tam, toz yok). Referans karesi, kaynak zamanlarindaki kamera
                   yakinlasmasi z(t) = 1 + (ZN - 1) * ease(t, 0, 15.4) oranina gore ekran merkezinde olceklenir
                   (1. kosu: duzeltmesiz A 0. kare 0.887; %1.6 yakinlasma farki).
  r_etiket         burc adlari bandi (etiket_y-10 .. +70 px), sembol kutusunun solu ve sagi (sembol haric; 1. kosuda
                   ortadaki sembol bandi kesiyordu). r_soru: soru metni bandi (soru_y +-60 px). Referans ESKI 3.0 sn (ikisi de
                   tam gorunur, solma 3.3 sn'de baslar), ayni yakinlasma duzeltmesi. B'de soru metni yok (tasarim geregi).
  okunur           r >= 0.9
Kapilar (A ve B): 0. kare parlaklik > 0; 0. karede r_sembol >= 0.9 ve r_ad(etiket) >= 0.9; 1080x1920, 720 kare,
  video 24.0 sn (+-0.05); ses akisi var, 24.0 sn (+-0.05); ses paketleri muzik dosyasiyla ayni (md5) -> yumusak giris/cikis
  korunur; RMS (dBFS) 0-0.2 sn < 1-2 sn ve 23.8-24 sn < 22-23 sn.
Kullanim: k1_qc.py DIR CIFT [--k2]   (--k2: B / B1 / C, KONTAK2.jpg, K1_QC2.json; ayrinti main_k2)"""
import hashlib, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ESIK_R = 0.9
SN = [0, 0.5, 1, 2, 3]
ZN, T_END_FREEZE = 1.03, 23.1          # video_uret.py ile ayni


def ease(t, a, b):
    s = min(max((t - a) / (b - a), 0.0), 1.0); return 0.5 - 0.5 * np.cos(np.pi * s)


def z(ts):
    return 1 + (ZN - 1) * ease(ts, 0, 15.4) if ts < 15.4 else ZN


def kaynak(k, t, t0):
    return min(t + t0, T_END_FREEZE) if k == 'B' else t


def olcekle(g, oran):
    """Gri kareyi ekran merkezinde 'oran' kadar buyut (oran < 1 kucult): referansi olculen karenin yakinlasmasina getirir."""
    if abs(oran - 1) < 1e-6:
        return g
    a = 1 / oran; cx, cy = 540, 960
    im = Image.fromarray(g).transform((1080, 1920), Image.AFFINE, (a, 0, cx * (1 - a), 0, a, cy * (1 - a)), Image.BICUBIC)
    return np.asarray(im, np.float32)


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
    kut = {'sembol': (slice(max(0, y), y + h), slice(max(0, x), x + w)), 'soru': (slice(sy - 60, sy + 60), slice(0, 1080))}
    eb = slice(ey - 10, ey + 70); sol_, sag_ = slice(0, max(0, x - 10)), slice(min(1080, x + w + 10), 1080)
    V = {k: os.path.join(d, f'{k}_{cift}.mp4') for k in ('ESKI', 'A', 'B')}
    T0 = bi['T_B0']; ts_s, ts_a = T0 + 0.5, 3.0
    ref_s = gri(kare(V['ESKI'], ts_s)); ref_a = gri(kare(V['ESKI'], ts_a))

    def olc(a, k, t):
        g = gri(a); zk = z(kaynak(k, t, T0))
        rs = olcekle(ref_s, zk / z(ts_s)); ra = olcekle(ref_a, zk / z(ts_a))
        et = np.concatenate([g[eb, sol_].ravel(), g[eb, sag_].ravel()]); er = np.concatenate([ra[eb, sol_].ravel(), ra[eb, sag_].ravel()])
        return {'parlaklik': round(float(np.asarray(Image.fromarray(a).convert('L'), np.float32).mean()), 2),
                'r_sembol': kor(g[kut['sembol']], rs[kut['sembol']]), 'r_etiket': kor(et, er),
                'r_soru': kor(g[kut['soru']], ra[kut['soru']])}

    muz = ses_md5(os.path.join(d, 'muzik.m4a'))
    S, KAR, rc = {}, {}, 0
    for k, v in V.items():
        p = probe(v); m = ses_md5(v); r = rms(v)
        kr = {t: kare(v, t) for t in SN}; KAR[k] = kr
        o = {t: olc(a, k, t) for t, a in kr.items()}
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
        zc[f'{t:.1f}'] = olc(kare(V['ESKI'], t), 'ESKI', t)
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


def lum(a):
    """sRGB -> goreli parlaklik (WCAG 2.x), piksel basina."""
    c = a.astype(np.float32) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def main_k2(d, cift):
    """B / B1 / C (19 Eki 2. tur). Referanslar B'den (ayni kaynak zamanlari, yakinlasma duzeltmeli):
    B1 0. kare: r_sembol (ref B 0.5 sn), r_ust (ust yazi bandi, ref B 1.5 sn: 'Two signs' tam), ust_oran (yazi pikselleri
    parlakligi / ref, >= 0.95 = soluk degil), r_etiket (ref B 0 sn, sembol haric). B1 2.0 sn: r_duvar (ref B 10.0 sn =
    kaynak 18.6 sn duvar sahnesi). C 0. kare: posterdeki isimler kutusunda WCAG kontrast (en parlak %15 / en koyu %50
    piksel) >= 4.5 ve yazi yuksekligi (px). Hepsi: 3.0 / 6 / 12 / 23.5 sn kareleri B ile ortalama mutlak fark < 2.5
    (dogrula.py esigi); sure, kare, ses = muzik (md5), RMS giris/cikis."""
    bi = json.load(open(os.path.join(d, 'bilgi_b1.json')))
    x, y, w, h = bi['sembol_kutu']; ey = bi['etiket_y']; T0 = bi['T_B0']
    sk = (slice(max(0, y), y + h), slice(max(0, x), x + w))
    eb = slice(ey - 10, ey + 70); sol_, sag_ = slice(0, max(0, x - 10)), slice(min(1080, x + w + 10), 1080)
    ub = slice(bi['ust_yazi_y'][0] - 60, bi['ust_yazi_y'][1] + 50)
    V = {k: os.path.join(d, f'{k}_{cift}.mp4') for k in ('B', 'B1', 'C')}
    rs, ru, re_, rw = (gri(kare(V['B'], t)) for t in (0.5, 1.5, 0.0, 10.0))
    muz = ses_md5(os.path.join(d, 'muzik.m4a'))
    S, KAR, rc = {'bilgi': bi}, {}, 0
    for k, v in V.items():
        p = probe(v); r = rms(v); KAR[k] = {t: kare(v, t) for t in SN}
        S[k] = {'probe': p, 'ses_md5_ayni': ses_md5(v) == muz and bool(muz), 'rms_db': r,
                'parlaklik': {str(t): round(float(np.asarray(Image.fromarray(a).convert('L'), np.float32).mean()), 2)
                              for t, a in KAR[k].items()}}
        if k == 'B':
            continue
        o = {}
        if k == 'B1':
            g = gri(KAR[k][0]); zk = z(T0)
            o['r_sembol'] = kor(g[sk], olcekle(rs, zk / z(T0 + 0.5))[sk])
            ru_z = olcekle(ru, zk / z(T0 + 1.5)); o['r_ust'] = kor(g[ub], ru_z[ub])
            m = ru_z[ub] > np.median(ru_z[ub]) + 20
            o['ust_oran'] = round(float(g[ub][m].mean() / ru_z[ub][m].mean()), 3) if m.any() else 0.0
            o['r_etiket'] = kor(np.concatenate([g[eb, sol_].ravel(), g[eb, sag_].ravel()]),
                                np.concatenate([re_[eb, sol_].ravel(), re_[eb, sag_].ravel()]))
            o['r_duvar_2sn'] = kor(gri(KAR[k][2]), rw)
        else:
            cx, cy, cw, chh = bi['c_isim_kutu']; L = lum(KAR[k][0][cy:cy + chh, cx:cx + cw]).ravel()
            hi, lo = L[L >= np.percentile(L, 85)].mean(), L[L <= np.percentile(L, 50)].mean()
            o['isim_kontrast'] = round(float((hi + 0.05) / (lo + 0.05)), 2); o['isim_yukseklik_px'] = chh
        fark = {}
        for t in (3.0, 6.0, 12.0, 23.5):
            fark[str(t)] = round(float(np.abs(kare(v, t).astype(np.float32) - kare(V['B'], t).astype(np.float32)).mean()), 3)
        o['B_farki'] = fark
        kapi = {'parlaklik_0>0': S[k]['parlaklik']['0'] > 0, 'boyut': p['boyut'] == '1080x1920', 'kare_720': p['kare'] == 720,
                'video_24': abs(p['video_sn'] - 24) <= 0.05, 'ses_var': p['ses'],
                'ses_24': p['ses_sn'] is not None and abs(p['ses_sn'] - 24) <= 0.05, 'muzik_ayni': S[k]['ses_md5_ayni'],
                'yumusak_giris': r['0-0.2'] < r['1-2'], 'yumusak_cikis': r['23.8-24'] < r['22-23'],
                '3sn_sonrasi_B': all(x < 2.5 for x in fark.values())}
        if k == 'B1':
            kapi.update(sembol_0=o['r_sembol'] >= ESIK_R, ust_yazi_0=o['r_ust'] >= ESIK_R, ust_soluk_degil=o['ust_oran'] >= 0.95,
                        ad_0=o['r_etiket'] >= ESIK_R, duvar_2sn=o['r_duvar_2sn'] >= ESIK_R)
        else:
            kapi['isim_okunur_0'] = o['isim_kontrast'] >= 4.5
        S[k].update(olcum=o, kapi=kapi, sonuc='PASS' if all(kapi.values()) else 'FAIL'); rc |= S[k]['sonuc'] != 'PASS'
    json.dump(S, open(os.path.join(d, 'K1_QC2.json'), 'w'), indent=1, default=str)
    tw, th, ust, sol = 324, 576, 44, 110
    K = Image.new('RGB', (sol + tw * 5 + 8 * 4, ust + (th + 8) * 3), (245, 245, 245)); dr = ImageDraw.Draw(K)
    try:
        f = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
    except OSError:
        f = ImageFont.load_default()
    for j, t in enumerate(SN):
        dr.text((sol + j * (tw + 8) + 8, 8), f'{t:g} sn', fill=(0, 0, 0), font=f)
    for i, k in enumerate(('B', 'B1', 'C')):
        yy = ust + i * (th + 8); dr.text((10, yy + th // 2 - 14), k, fill=(0, 0, 0), font=f)
        for j, t in enumerate(SN):
            K.paste(Image.fromarray(KAR[k][t]).resize((tw, th), Image.LANCZOS), (sol + j * (tw + 8), yy))
    K.save(os.path.join(d, 'KONTAK2.jpg'), quality=92)
    for k in ('B', 'B1', 'C'):
        print(k, 'parlaklik', S[k]['parlaklik'], S[k]['probe'], 'rms', S[k]['rms_db'], 'muzik_ayni', S[k]['ses_md5_ayni'])
        if 'kapi' in S[k]:
            print(k, 'OLCUM', S[k]['olcum']); print(k, 'KAPI', {a: ('PASS' if b else 'FAIL') for a, b in S[k]['kapi'].items()}, S[k]['sonuc'])
    print('SONUC', 'PASS' if rc == 0 else 'FAIL')
    return rc


if __name__ == '__main__':
    sys.exit(main_k2(sys.argv[1], sys.argv[2]) if '--k2' in sys.argv else main())
