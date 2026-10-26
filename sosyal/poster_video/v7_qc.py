#!/usr/bin/env python3
"""v7 QC (Merkez 26 Eki, CANCER_LIBRA yeni Canva kapagi): tek betik, PASS/FAIL, QC.json + KONTAK.jpg.
Kullanim: v7_qc.py <video.mp4> <kapak.png> <uretim_log.txt> <cikti_dir>
 a) 180 kare, 1440x1080, 30 fps, 6,0 sn, H.264, ses akisi yok (ffprobe)
 b) ilk ve son kare ile kapagin 1440x1080 INTER_AREA kucultmesi arasindaki ortalama mutlak fark <= kapagin kayipsiz
    4:2:0 kodlama tabani (ayni kapak libx264 crf 0 yuv420p) + 0,2
 c) <video>.ic.json 'ihlal' en buyuk <= 0 (murekkep tozun onune gecmiyor)
 d) uretim logunda 'poster kapakta X,Y WxH oran R' satiri: kutu orani (H / W) 1,29-1,31
 e) KONTAK.jpg: 0 / 0,5 / 1,5 / 2,5 / 3,5 / 4,5 / 5,9 sn (gercek oran)"""
import json, os, re, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

KONTAK_SN = [0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.9]


def probe(v):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', v],
                                  capture_output=True, text=True, check=True).stdout)
    vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    return {'olcu': f"{vs['width']}x{vs['height']}", 'kare': int(vs['nb_read_frames']), 'fps': vs['r_frame_rate'],
            'sure_sn': round(float(j['format']['duration']), 3), 'codec': vs['codec_name'],
            'ses_akisi': any(s['codec_type'] == 'audio' for s in j['streams']), 'boyut_mb': round(os.path.getsize(v) / 1e6, 2)}


def kareler(v):
    p = probe(v); w, h = map(int, p['olcu'].split('x'))
    d = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(d, np.uint8).reshape(-1, h, w, 3), p


fk = lambda a, b: round(float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()), 3)


def font(n):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', n)
    except OSError:
        return ImageFont.load_default()


def main():
    v, kap_yol, log_yol, out = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    F, p = kareler(v); R = {'video': os.path.basename(v), 'probe': p, 'kontrol': {}}
    K = R['kontrol']
    K['a_bicim'] = {'gecti': p['kare'] == 180 and p['olcu'] == '1440x1080' and p['fps'] == '30/1' and abs(p['sure_sn'] - 6.0) <= 0.05
                    and p['codec'] == 'h264' and not p['ses_akisi'], 'deger': p}
    kap = cv2.resize(np.asarray(Image.open(kap_yol).convert('RGB')), (F.shape[2], F.shape[1]), interpolation=cv2.INTER_AREA)
    tb = os.path.join(out, '_taban.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{kap.shape[1]}x{kap.shape[0]}', '-r', '30',
                    '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=kap.tobytes(), check=True)
    taban = fk(kareler(tb)[0][0], kap); os.remove(tb)
    ilk, son = fk(F[0], kap), fk(F[-1], kap)
    K['b_ilk_son_kare'] = {'gecti': ilk <= taban + 0.2 and son <= taban + 0.2,
                           'deger': {'taban_420': taban, 'esik': round(taban + 0.2, 3), 'ilk': ilk, 'son': son}}
    ic = json.load(open(v + '.ic.json'))
    ih = max(ic['ihlal'])
    K['c_ihlal'] = {'gecti': ih <= 0, 'deger': {'ihlal_en_buyuk': round(ih, 6), 'kare_sayisi': len(ic['ihlal'])}}
    satir = [l for l in open(log_yol, encoding='utf-8').read().splitlines() if l.startswith('poster kapakta')]
    m = re.match(r'poster kapakta (\d+),(\d+) (\d+)x(\d+)', satir[0]) if satir else None
    oran = round(int(m.group(4)) / int(m.group(3)), 4) if m else None
    K['d_kutu_orani'] = {'gecti': oran is not None and 1.29 <= oran <= 1.31, 'deger': {'satir': satir[0] if satir else None, 'oran': oran}}
    th = 270; tw = round(F.shape[2] * th / F.shape[1]); ust = 32
    KT = Image.new('RGB', (4 * (tw + 8), 2 * (th + ust + 8)), (245, 245, 245)); dr = ImageDraw.Draw(KT)
    for n, t in enumerate(KONTAK_SN):
        x, y = (n % 4) * (tw + 8), (n // 4) * (th + ust + 8)
        dr.text((x + 6, y + 4), f'{t:g} sn'.replace('.', ','), fill=(0, 0, 0), font=font(22))
        KT.paste(Image.fromarray(F[min(len(F) - 1, int(round(t * 30)))]).resize((tw, th), Image.LANCZOS), (x, y + ust))
    KT.save(os.path.join(out, 'KONTAK.jpg'), quality=92)
    K['e_kontak'] = {'gecti': os.path.isfile(os.path.join(out, 'KONTAK.jpg')), 'deger': {'sn': KONTAK_SN}}
    R['sonuc'] = 'PASS' if all(k['gecti'] for k in K.values()) else 'FAIL'
    json.dump(R, open(os.path.join(out, 'QC.json'), 'w'), indent=1, ensure_ascii=False)
    for ad, k in K.items():
        print(('PASS ' if k['gecti'] else 'FAIL ') + ad, json.dumps(k['deger'], ensure_ascii=False))
    print('QC', R['sonuc'])
    return 0 if R['sonuc'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
