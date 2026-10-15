"""Prepend the video cover (kapak_v1) to a reel as a 0.5 s still, hard cut (Serdar onayi 15 Eki 2026, sosyal-kapak-oku 38700285414).

Why: Facebook's player and Threads open on the video's first frame, which is black (v9 fades in from black over 0-1 s).
The same file goes to every platform; Instagram and TikTok keep using the uploaded cover (videoThumbnailUrl).

Video: cover scaled/cropped to the video size, N = round(sn * fps) frames, then the original frames unchanged in order.
Re-encoded with the v9 settings (libx264 High, CRF 16, preset slow, tune grain, aq-mode 3, yuv420p).
Audio: the original track delayed by sn (picture/music sync of the approved video is kept), AAC at the original bit rate.

QC (PASS/FAIL, exit 1 on FAIL), written to --qc JSON:
  ilk_kare_fark   frame 0 vs cover (mean abs RGB diff, 0-255)            < 2.0
  son_kapak_fark  frame N-1 vs cover                                       < 2.0
  kayma_fark      frame N + k vs original frame k (k = 0, 8 s)             < 2.0
  kare            frames = original + N;  video/audio duration = original + sn (+-0.05)
  lufs            integrated loudness within 0.5 LU of the original
  sure_sinir      total <= 60 s (strictest target: YouTube Shorts 60 s; IG/FB Reels 90 s; TikTok longer)
Usage: python3 kapak_basa.py --video in.mp4 --kapak kapak.jpg --cikis out.mp4 [--sn 0.5] [--qc out-qc.json]
"""
import argparse, json, os, re, subprocess, sys, tempfile, time

import numpy as np
from PIL import Image

SINIR_SN = 60.0
ESIK = 2.0


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration,bit_rate,sample_rate,channels',
                        '-show_entries', 'format=duration,size', '-of', 'json', p], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j['streams'] if s['codec_type'] == 'video')
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    n, d = v['r_frame_rate'].split('/')
    return {'w': int(v['width']), 'h': int(v['height']), 'fps': int(n) / int(d), 'fps_str': v['r_frame_rate'],
            'kare': int(v.get('nb_frames') or 0), 'video_sn': float(v.get('duration') or 0),
            'ses': a and {'codec': a['codec_name'], 'sn': float(a.get('duration') or 0), 'bit_rate': int(a.get('bit_rate') or 192000),
                          'hz': int(a.get('sample_rate') or 48000), 'kanal': int(a.get('channels') or 2)},
            'boyut': int(j['format']['size']), 'toplam_sn': float(j['format']['duration'])}


def kare(p, i, w, h, tmp):
    """Frame i (0-based, exact via select) as float RGB array."""
    f = os.path.join(tmp, f'k_{os.path.basename(p)}_{i}.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-vf', f'select=eq(n\\,{i})', '-vsync', '0', '-frames:v', '1', f], check=True)
    return np.asarray(Image.open(f).convert('RGB').resize((w, h)), np.float32)


def lufs(p):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-map', '0:a', '-af', 'ebur128', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', required=True); ap.add_argument('--kapak', required=True); ap.add_argument('--cikis', required=True)
    ap.add_argument('--sn', type=float, default=0.5); ap.add_argument('--qc', default='')
    g = ap.parse_args()
    t0 = time.time()
    v = probe(g.video)
    W, H, fps = v['w'], v['h'], v['fps']
    N = int(round(g.sn * fps))
    sn = N / fps
    vf = (f'[1:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p,'
          f'fps={v["fps_str"]},trim=end_frame={N},setpts=PTS-STARTPTS[k];'
          f'[0:v]setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v];[k][v]concat=n=2:v=1:a=0[vo]')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', g.video, '-loop', '1', '-framerate', v['fps_str'], '-i', g.kapak]
    harita = ['-map', '[vo]']
    if v['ses']:
        ms = int(round(sn * 1000))
        vf += f';[0:a]adelay={ms}:all=1,asetpts=PTS-STARTPTS[ao]'
        harita += ['-map', '[ao]', '-c:a', 'aac', '-b:a', str(v['ses']['bit_rate']), '-ar', str(v['ses']['hz']), '-ac', str(v['ses']['kanal'])]
    cmd += ['-filter_complex', vf] + harita + [
        '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'slow', '-tune', 'grain',
        '-aq-mode', '3', '-r', v['fps_str'], '-t', f'{v["video_sn"] + sn:.3f}', '-movflags', '+faststart', g.cikis]
    subprocess.run(cmd, check=True)
    uretim_sn = time.time() - t0

    o = probe(g.cikis)
    with tempfile.TemporaryDirectory() as tmp:
        K = np.asarray(Image.open(g.kapak).convert('RGB'), np.float32)
        kh, kw = K.shape[:2]
        if (kw, kh) != (W, H):   # same cover-fit as the filter, for comparison
            s = max(W / kw, H / kh)
            im = Image.open(g.kapak).convert('RGB').resize((round(kw * s), round(kh * s)), Image.LANCZOS)
            x, y = (im.width - W) // 2, (im.height - H) // 2
            K = np.asarray(im.crop((x, y, x + W, y + H)), np.float32)
        f0, fn = kare(g.cikis, 0, W, H, tmp), kare(g.cikis, N - 1, W, H, tmp)
        k8 = int(round(8 * fps))
        kayma = max(float(np.abs(kare(g.cikis, N + k, W, H, tmp) - kare(g.video, k, W, H, tmp)).mean()) for k in (0, k8))
        q = {'giris': os.path.basename(g.video), 'cikis': os.path.basename(g.cikis), 'kapak': os.path.basename(g.kapak),
             'kapak_kare': N, 'kapak_sn': round(sn, 3), 'boyut_px': f'{o["w"]}x{o["h"]}', 'fps': o['fps_str'],
             'kare_once': v['kare'], 'kare_sonra': o['kare'], 'video_sn_once': v['video_sn'], 'video_sn_sonra': o['video_sn'],
             'ses_sn_once': v['ses'] and v['ses']['sn'], 'ses_sn_sonra': o['ses'] and o['ses']['sn'],
             'toplam_sn': round(o['toplam_sn'], 3), 'bayt_once': v['boyut'], 'bayt_sonra': o['boyut'],
             'ilk_kare_fark': round(float(np.abs(f0 - K).mean()), 2), 'son_kapak_fark': round(float(np.abs(fn - K).mean()), 2),
             'ilk_kare_parlaklik': round(float(f0.mean()), 1), 'kayma_fark': round(kayma, 2),
             'lufs_once': lufs(g.video) if v['ses'] else None, 'lufs_sonra': lufs(g.cikis) if o['ses'] else None,
             'uretim_sn': round(uretim_sn, 1)}
    kap = {'ilk_kare': q['ilk_kare_fark'] < ESIK, 'son_kapak_karesi': q['son_kapak_fark'] < ESIK, 'kayma': q['kayma_fark'] < ESIK,
           'boyut_fps': (o['w'], o['h'], o['fps_str']) == (W, H, v['fps_str']),
           'kare': o['kare'] == v['kare'] + N,
           'video_sure': abs(o['video_sn'] - (v['video_sn'] + sn)) <= 0.05,
           'ses_sure': (not v['ses']) or (o['ses'] is not None and abs(o['ses']['sn'] - (v['ses']['sn'] + sn)) <= 0.05),
           'lufs': (not v['ses']) or (q['lufs_once'] is not None and q['lufs_sonra'] is not None and abs(q['lufs_sonra'] - q['lufs_once']) <= 0.5),
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
