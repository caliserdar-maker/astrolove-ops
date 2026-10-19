#!/usr/bin/env python3
"""v5 QC (19 Eki): poster v5 ve kupa ince toz ornekleri. Tek script, PASS/FAIL, kontak + %200 yakin kirpim.
poster <v5.mp4> <kapak.jpg> <cikti_dir>: probe; ilk/son kare = kapak (kayipsiz 4:2:0 tabani + 0,2); 0,5 sn tablosu (ic olcum,
  poster_video_v5 <mp4>.ic.json: cekirdek sembol piksellerinde ortalama murekkep ve ortalama toz birikimi F; ihlal =
  max(murekkep - F) > 0 ise bir pikselde murekkep tozun onunde); sembol tam (murekkep >= 0,99) <= 150. kare; KONTAK + YAKIN.
kupa <eski.mp4> <ince.mp4> <tozsuz.mp4> <k_mask_nosym.png> <k_beyaz.png> <cikti_dir>: eski = video6b (sigma 0.9), ince =
  ayni kod sigma 0.45, tozsuz = ayni kod toz kapali. Toz bolgesi = eski ya da ince karenin tozsuzdan farki > 3 (5 px
  genisletilmis); bu bolgenin DISINDA eski ile ince arasindaki fark (ortalama / en buyuk) ~0 olmali; kare/sure/olcu ayni.
  KONTAK: ust eski, alt ince, 0-6 sn her 0,5 sn; YAKIN: 3 sn sembol bolgesi %200 (sol eski, sag ince)."""
import json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

SN = [k * 0.5 for k in range(13)]


def probe(v):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', v],
                                  capture_output=True, text=True, check=True).stdout)
    vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    return {'olcu': f"{vs['width']}x{vs['height']}", 'kare': int(vs['nb_read_frames']), 'fps': vs['r_frame_rate'],
            'sure_sn': round(float(j['format']['duration']), 3), 'ses_akisi': any(s['codec_type'] == 'audio' for s in j['streams']),
            'boyut_mb': round(os.path.getsize(v) / 1e6, 2)}


def kareler(v):
    p = probe(v); w, h = map(int, p['olcu'].split('x'))
    d = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(d, np.uint8).reshape(-1, h, w, 3), p


ix = lambda F, t: min(len(F) - 1, int(round(t * 30)))
fk = lambda a, b: round(float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()), 3)


def font(n):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', n)
    except OSError:
        return ImageFont.load_default()


def kontak(satirlar, yol, th=270):
    """satirlar: [(ad, kareler)]; her satir 0-6 sn her 0,5 sn, gercek oran."""
    sut = len(SN); ust, sol = 32, (150 if len(satirlar) > 1 else 0)
    tw = max(round(F.shape[2] * th / F.shape[1]) for _, F in satirlar)
    if len(satirlar) == 1:   # tek satir: 5 sutun x 3 satir
        F = satirlar[0][1]; tw_ = round(F.shape[2] * th / F.shape[1]); c = 5
        K = Image.new('RGB', (c * (tw_ + 8), 3 * (th + ust + 8)), (245, 245, 245)); dr = ImageDraw.Draw(K)
        for n, t in enumerate(SN):
            x, y = (n % c) * (tw_ + 8), (n // c) * (th + ust + 8)
            dr.text((x + 6, y + 4), f'{t:g} sn', fill=(0, 0, 0), font=font(22))
            K.paste(Image.fromarray(F[ix(F, t)]).resize((tw_, th), Image.LANCZOS), (x, y + ust))
        K.save(yol, quality=92); return
    K = Image.new('RGB', (sol + sut * (tw + 6), ust + len(satirlar) * (th + 8)), (245, 245, 245)); dr = ImageDraw.Draw(K)
    for j, t in enumerate(SN):
        dr.text((sol + j * (tw + 6) + 4, 4), f'{t:g} sn', fill=(0, 0, 0), font=font(20))
    for r_, (ad, F) in enumerate(satirlar):
        y = ust + r_ * (th + 8); dr.text((6, y + th // 2 - 10), ad, fill=(0, 0, 0), font=font(20))
        for j, t in enumerate(SN):
            K.paste(Image.fromarray(F[ix(F, t)]).resize((tw, th), Image.LANCZOS), (sol + j * (tw + 6), y))
    K.save(yol, quality=92)


def kutu(m, pay=24):
    ys, xs = np.where(m)
    return max(0, ys.min() - pay), min(m.shape[0], ys.max() + pay), max(0, xs.min() - pay), min(m.shape[1], xs.max() + pay)


def poster(v5, kap_yol, out):
    F, p = kareler(v5); R = {'video': p}
    kap = cv2.resize(np.asarray(Image.open(kap_yol).convert('RGB')), (F.shape[2], F.shape[1]), interpolation=cv2.INTER_AREA)
    tb = os.path.join(out, '_t.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{kap.shape[1]}x{kap.shape[0]}', '-r', '30',
                    '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=kap.tobytes(), check=True)
    R['taban_420'] = fk(kareler(tb)[0][0], kap); os.remove(tb)
    R['ilk_kare_fark'], R['son_kare_fark'] = fk(F[0], kap), fk(F[-1], kap)
    ic = json.load(open(v5 + '.ic.json'))
    R['parametre'] = {'N': ic['N'], 'tane_sigma': ic['tane_sigma'], 'birikim_esik': ic['birikim_esik']}
    km = {k: (m, t) for k, m, t in zip(ic['kare'], ic['murekkep'], ic['toz_ortusu'])}
    tab = {}
    for t in SN:
        i = ix(F, t)
        m, tz = km.get(i, (0.0 if 0 < i < 150 else 1.0, 0.0 if 0 < i < 150 else 1.0))
        if i == 0:
            m, tz = 1.0, None                      # kapak (silinmeden once)
        tab[f'{t:g}'] = {'kare': i, 'murekkep': round(m, 3), 'toz_birikimi': None if tz is None else round(tz, 3)}
    R['tablo_0_5sn'] = tab
    R['ihlal_en_buyuk'] = round(max(ic['ihlal']), 4)
    R['murekkep_toz_onunde_kare'] = [k for k, m, t in zip(ic['kare'], ic['murekkep'], ic['toz_ortusu']) if m > t + 1e-6]
    tam = next((k for n, k in enumerate(ic['kare']) if all(x >= 0.99 for x in ic['murekkep'][n:])), 150)
    R['sembol_tam_kare'] = tam
    R['kapi'] = {'sure_6': abs(p['sure_sn'] - 6) < 0.05, 'kare_180': p['kare'] == 180, 'fps_30': p['fps'] == '30/1',
                 'olcu_1440x1080': p['olcu'] == '1440x1080', 'ses_yok': not p['ses_akisi'],
                 'ilk_kare_kapak': R['ilk_kare_fark'] <= R['taban_420'] + 0.2, 'son_kare_kapak': R['son_kare_fark'] <= R['taban_420'] + 0.2,
                 'murekkep_tozdan_once_degil': R['ihlal_en_buyuk'] <= 0 and not R['murekkep_toz_onunde_kare'],
                 'sembol_tam_5sn': tam <= 150, 'toz_26000': ic['N'] == 26000, 'tane_0_45': ic['tane_sigma']['v5'] == 0.45}
    R['sonuc'] = 'PASS' if all(R['kapi'].values()) else 'FAIL'
    kontak([('POSTER v5', F)], os.path.join(out, 'POSTER_v5_KONTAK.jpg'))
    SM = np.asarray(Image.open(v5 + '.sembol_maske.png')) > 127
    y0, y1, x0, x1 = kutu(SM)
    Image.fromarray(F[90][y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS).save(os.path.join(out, 'POSTER_v5_YAKIN_3sn_200.jpg'), quality=94)
    return R


def kupa(eski, ince, tozsuz, km_, kb_, out):
    FE, pe = kareler(eski); FI, pi = kareler(ince); FT, _ = kareler(tozsuz)
    R = {'eski': pe, 'ince': pi, 'tane_sigma': {'eski': 0.9, 'ince': 0.45}}
    n = min(len(FE), len(FI), len(FT)); dis_ort, dis_max, ic_ort, toz_px_e, toz_px_i = [], [], [], [], []
    for i in range(n):
        e, ii, t = (x[i].astype(np.int16) for x in (FE, FI, FT))
        de, di = np.abs(e - t).max(-1) > 3, np.abs(ii - t).max(-1) > 3
        toz = cv2.dilate((de | di).astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
        d = np.abs(e - ii).max(-1)
        dis_ort.append(float(d[~toz].mean())); dis_max.append(int(d[~toz].max()) if (~toz).any() else 0)
        ic_ort.append(float(d[toz].mean()) if toz.any() else 0.0)
        toz_px_e.append(int(de.sum())); toz_px_i.append(int(di.sum()))
    R['toz_disi_fark'] = {'ortalama_en_buyuk': round(max(dis_ort), 3), 'en_buyuk_piksel': max(dis_max)}
    R['toz_ici_fark_ortalama_en_buyuk'] = round(max(ic_ort), 3)
    R['toz_piksel_3sn'] = {'eski': toz_px_e[90], 'ince': toz_px_i[90]}
    R['kapi'] = {'kare_ayni': pe['kare'] == pi['kare'], 'sure_ayni': pe['sure_sn'] == pi['sure_sn'], 'olcu_ayni': pe['olcu'] == pi['olcu'],
                 'ses_yok': not pi['ses_akisi'], 'toz_disi_ayni': R['toz_disi_fark']['ortalama_en_buyuk'] < 0.5}
    R['sonuc'] = 'PASS' if all(R['kapi'].values()) else 'FAIL'
    kontak([('ESKI (0.9)', FE), ('INCE (0.45)', FI)], os.path.join(out, 'KUPA_KONTAK.jpg'))
    oku = lambda p_: cv2.resize(np.asarray(Image.open(p_).convert('RGB')).astype(np.float32), (FE.shape[2], FE.shape[1]), interpolation=cv2.INTER_AREA)
    SM = np.clip((1 - oku(km_).mean(-1) / np.maximum(oku(kb_).mean(-1), 1)) * 1.4, 0, 1) > 0.5
    y0, y1, x0, x1 = kutu(SM, 40)
    a = Image.fromarray(FE[90][y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS)
    b = Image.fromarray(FI[90][y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS)
    K = Image.new('RGB', (a.width * 2 + 12, a.height + 34), (245, 245, 245)); dr = ImageDraw.Draw(K)
    dr.text((6, 4), 'ESKI (sigma 0.9)', fill=(0, 0, 0), font=font(20)); dr.text((a.width + 18, 4), 'INCE (sigma 0.45)', fill=(0, 0, 0), font=font(20))
    K.paste(a, (0, 34)); K.paste(b, (a.width + 12, 34)); K.save(os.path.join(out, 'KUPA_YAKIN_3sn_200.jpg'), quality=94)
    return R


if __name__ == '__main__':
    mod = sys.argv[1]
    if mod == 'poster':
        R = poster(*sys.argv[2:4], sys.argv[4]); ad = 'QC_poster.json'
    else:
        R = kupa(*sys.argv[2:7], sys.argv[7]); ad = 'QC_kupa.json'
    out = sys.argv[-1]
    json.dump(R, open(os.path.join(out, ad), 'w'), indent=1, default=str)
    print(json.dumps(R, default=str)[:3000]); print('SONUC', mod, R['sonuc'])
    sys.exit(0 if R['sonuc'] == 'PASS' else 1)
