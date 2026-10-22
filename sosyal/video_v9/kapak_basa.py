"""Cover (kapak_v1) over the black fade-in of a reel, no added time (Serdar onayi 15 Eki 2026, 2. yontem).

Why: Facebook's player opens on the video's first frame; v9 fades in from black over 0-1 s (first frame brightness 0).
1. yontem (0.5 s prepended, 38703541337) gave "cover, black, fade-in"; replaced by this.

Video: 0 - TAM s the cover (scaled/cropped to the video size); TAM - TAM+GECIS s cosine cross-fade cover -> original
(overlaps the original's own fade-in, so no black frame is ever shown); after that the original frames unchanged.
Duration and frame count unchanged. Re-encoded with the v9 settings (libx264 High, CRF 16, preset slow, tune grain,
aq-mode 3, yuv420p). Audio: stream copy (bit-identical, no shift).

QC (PASS/FAIL, exit 1 on FAIL), written to --qc JSON:
  ilk_kare_fark   frame 0 vs cover (mean abs RGB diff, 0-255)                  < 2.0
  tam_kapak_fark  last full-cover frame vs cover                                < 2.0
  min_parlaklik   every frame 0 - 1.5 s: mean brightness >= cover mean / 2
  kayma_fark      frames at TAM+GECIS s and 8 s vs the original                 < 2.0
  kare / sure     frame count and video duration equal to the original
  ses             audio duration equal and audio packets bit-identical (md5)
  sure_sinir      total <= 60 s (strictest target: YouTube Shorts)
Usage: python3 kapak_basa.py --video in.mp4 --kapak kapak.jpg --cikis out.mp4 [--tam 0.5] [--gecis 0.5] [--qc out-qc.json]
"""
import argparse, json, os, subprocess, sys, time

import numpy as np
from PIL import Image

SINIR_SN = 60.0
ESIK = 2.0
KONTROL_SN = 1.5


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration',
                        '-show_entries', 'format=duration,size', '-of', 'json', p], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j['streams'] if s['codec_type'] == 'video')
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    n, d = v['r_frame_rate'].split('/')
    return {'w': int(v['width']), 'h': int(v['height']), 'fps': int(n) / int(d), 'fps_str': v['r_frame_rate'],
            'kare': int(v.get('nb_frames') or 0), 'video_sn': float(v.get('duration') or 0),
            'ses_sn': a and float(a.get('duration') or 0), 'boyut': int(j['format']['size']), 'toplam_sn': float(j['format']['duration'])}


def kareler(p, w, h, n):
    """First n frames as float RGB arrays (one ffmpeg decode)."""
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3).astype(np.float32)


def kare(p, i, w, h):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-vf', f'select=eq(n\\,{i})', '-vsync', '0', '-frames:v', '1',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(h, w, 3).astype(np.float32)


def ses_md5(p):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-map', '0:a', '-c', 'copy', '-f', 'md5', '-'],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def kapak_dizi(yol, W, H):
    im = Image.open(yol).convert('RGB')
    if im.size != (W, H):   # cover-fit, same as the ffmpeg filter
        s = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x, y = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((x, y, x + W, y + H))
    return np.asarray(im, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', required=True); ap.add_argument('--kapak', required=True); ap.add_argument('--cikis', required=True)
    ap.add_argument('--tam', type=float, default=0.5); ap.add_argument('--gecis', type=float, default=0.5); ap.add_argument('--qc', default='')
    g = ap.parse_args()
    t0 = time.time()
    v = probe(g.video)
    W, H, fps = v['w'], v['h'], v['fps']
    a, b = g.tam, g.tam + g.gecis
    # weight of the ORIGINAL: 0 until a, cosine ease a -> b, 1 after b (A = original, B = cover)
    x = f'(0.5-0.5*cos(PI*clip((T-{a})/{g.gecis},0,1)))'
    nb = int(np.ceil(b * fps))                         # first frame that is 100 % original
    # blend only the first nb frames (speed); the rest of the original is passed through and concatenated
    fc = (f'[1:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p,'
          f'fps={v["fps_str"]},trim=end_frame={nb},setpts=PTS-STARTPTS[k];[0:v]setsar=1,format=yuv420p,split[o1][o2];'
          f'[o1]trim=end_frame={nb},setpts=PTS-STARTPTS[h];[o2]trim=start_frame={nb},setpts=PTS-STARTPTS[t];'
          f"[h][k]blend=all_expr='A*{x}+B*(1-{x})'[m];[m][t]concat=n=2:v=1:a=0[vo]")
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', g.video, '-loop', '1', '-framerate', v['fps_str'], '-t', f'{b + 1:.3f}',
           '-i', g.kapak, '-filter_complex', fc, '-map', '[vo]']
    if v['ses_sn']:
        cmd += ['-map', '0:a', '-c:a', 'copy']
    cmd += ['-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'slow', '-tune', 'grain',
            '-aq-mode', '3', '-r', v['fps_str'], '-frames:v', str(v['kare']), '-movflags', '+faststart', g.cikis]
    subprocess.run(cmd, check=True)
    uretim_sn = time.time() - t0

    o = probe(g.cikis)
    K = kapak_dizi(g.kapak, W, H)
    kb = float(K.mean())
    nk = int(round(KONTROL_SN * fps)) + 1
    ilk = kareler(g.cikis, W, H, nk)
    parl = [float(f.mean()) for f in ilk]
    ntam = max(0, int(np.floor(a * fps)) - 1)          # last frame that is still 100 % cover
    kayma = max(float(np.abs(kare(g.cikis, i, W, H) - kare(g.video, i, W, H)).mean()) for i in (nb, int(round(8 * fps))))
    q = {'giris': os.path.basename(g.video), 'cikis': os.path.basename(g.cikis), 'kapak': os.path.basename(g.kapak),
         'tam_sn': a, 'gecis_sn': g.gecis, 'boyut_px': f'{o["w"]}x{o["h"]}', 'fps': o['fps_str'],
         'kare_once': v['kare'], 'kare_sonra': o['kare'], 'video_sn_once': v['video_sn'], 'video_sn_sonra': o['video_sn'],
         'ses_sn_once': v['ses_sn'], 'ses_sn_sonra': o['ses_sn'], 'toplam_sn': round(o['toplam_sn'], 3),
         'bayt_once': v['boyut'], 'bayt_sonra': o['boyut'],
         'kapak_parlaklik': round(kb, 1), 'ilk_kare_fark': round(float(np.abs(ilk[0] - K).mean()), 2),
         'tam_kapak_fark': round(float(np.abs(ilk[ntam] - K).mean()), 2),
         'min_parlaklik_0_1.5': round(min(parl), 1), 'min_parlaklik_kare': int(np.argmin(parl)),
         'parlaklik_0_0.5_0.8_1.2': [round(parl[int(round(t * fps))], 1) for t in (0, 0.5, 0.8, 1.2)],
         'kayma_fark': round(kayma, 2), 'uretim_sn': round(uretim_sn, 1)}
    if v['ses_sn']:
        q['ses_ayni'] = ses_md5(g.video) == ses_md5(g.cikis)
    kap = {'ilk_kare': q['ilk_kare_fark'] < ESIK, 'tam_kapak': q['tam_kapak_fark'] < ESIK,
           'min_parlaklik': min(parl) >= kb / 2, 'kayma': q['kayma_fark'] < ESIK,
           'boyut_fps': (o['w'], o['h'], o['fps_str']) == (W, H, v['fps_str']),
           'kare': o['kare'] == v['kare'], 'video_sure': abs(o['video_sn'] - v['video_sn']) <= 0.02,
           'ses': (not v['ses_sn']) or (q['ses_ayni'] and o['ses_sn'] is not None and abs(o['ses_sn'] - v['ses_sn']) <= 0.001),
           'sure_sinir': o['toplam_sn'] <= SINIR_SN}
    q['kapilar'] = kap
    q['sonuc'] = 'PASS' if all(kap.values()) else 'FAIL'
    if g.qc:
        json.dump(q, open(g.qc, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(q, ensure_ascii=False))
    print(f'OZET kapak_basa {q["cikis"]}: {q["sonuc"]}' + ('' if q['sonuc'] == 'PASS' else ' FAIL: ' + ','.join(k for k, x in kap.items() if not x)))
    sys.exit(0 if q['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
