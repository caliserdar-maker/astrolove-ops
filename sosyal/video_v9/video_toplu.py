"""Batch run of video_uret.build for several pairs + per-video QC (PASS/FAIL).

Usage:
  python3 video_toplu.py --posters <dir with PAIR.jpg 2000x3000> --out <dir> [--pairs CAPRICORN_SAGITTARIUS,...] [--toplam 78 --sira 0]
Pair key is alphabetic (CLAUDE.md): first sign = --a (left small sign), second = --b (right).
For every pair writes {slug}-astroloveart-reel.mp4, {slug}-qc.json and {slug}-kare_9s.jpg (contact sheet frame).
QC per video (all must hold):
  q_poster : PosterR found the poster parts (no exception)
  q_video  : 1080x1920, 30 fps, 24.0 s (720 frames), H.264
  q_son    : the "Make it yours" area of the 22 s frame is not empty
Exit code 1 if any pair FAILs.
"""
import argparse, json, os, subprocess, sys, time, traceback
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import video_uret as VU

# "Make it yours" is drawn at y = CY - 130 (CY = 770); empty control band lower on the end card
SON_KUTU = (140, 570, 940, 710)
BOS_KUTU = (140, 1480, 940, 1620)
SON_ESIK = 0.005   # >= 0.5% bright (gold) pixels in the text band


def kare(mp4, sec, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{sec}', '-i', mp4, '-frames:v', '1', '-q:v', '2', dst], check=True)
    return np.asarray(Image.open(dst).convert('RGB')).astype(np.float32)


def parlak_oran(img, box):
    x0, y0, x1, y1 = box
    y = img[y0:y1, x0:x1] @ np.array([0.299, 0.587, 0.114], np.float32)
    return float((y > np.median(y) + 40).mean())


def probe(mp4):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                        'stream=codec_name,width,height,r_frame_rate,nb_read_frames:format=duration', '-of', 'json', mp4],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    return dict(codec=s['codec_name'], w=int(s['width']), h=int(s['height']), fps=s['r_frame_rate'],
                kare=int(s['nb_read_frames']), sure=round(float(j['format']['duration']), 3))


def qc_video(mp4, out, slug):
    r = probe(mp4)
    r['q_video'] = (r['codec'] == 'h264' and (r['w'], r['h']) == (1080, 1920) and r['fps'] == '30/1'
                    and r['kare'] == 720 and abs(r['sure'] - 24.0) < 0.05)
    tmp = os.path.join(out, f'_{slug}_22s.jpg')
    f22 = kare(mp4, 22.0, tmp); os.remove(tmp)
    r['son_oran'] = round(parlak_oran(f22, SON_KUTU), 4); r['bos_oran'] = round(parlak_oran(f22, BOS_KUTU), 4)
    r['q_son'] = r['son_oran'] >= SON_ESIK
    kare(mp4, 9.0, os.path.join(out, f'{slug}-kare_9s.jpg'))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posters', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pairs', default='')
    ap.add_argument('--toplam', type=int, default=0, help='total pairs over all jobs (progress line only)')
    ap.add_argument('--sira', type=int, default=0, help='index of the first pair of this job in the total (progress line only)')
    g = ap.parse_args()
    os.makedirs(g.out, exist_ok=True)
    pairs = [p.strip() for p in g.pairs.split(',') if p.strip()] or \
        sorted(os.path.splitext(f)[0] for f in os.listdir(g.posters) if f.endswith('.jpg'))
    toplam = g.toplam or len(pairs)
    t0 = time.time(); fails = []
    for i, key in enumerate(pairs):
        A, B = [s.capitalize() for s in key.split('_')]
        slug = f'{A.lower()}-and-{B.lower()}'
        r = dict(cift=key, a=A, b=B, q_poster=False, q_video=False, q_son=False)
        try:
            ts = time.time()
            mp4 = VU.build(os.path.join(g.posters, key + '.jpg'), A, B, g.out)[0]
            r['q_poster'] = True; r['uretim_sn'] = round(time.time() - ts)
            r['dosya'] = os.path.basename(mp4); r['mb'] = round(os.path.getsize(mp4) / 1e6, 2)
            r.update(qc_video(mp4, g.out, slug))
        except Exception as e:
            r.update(hata=f'{type(e).__name__}: {e}', iz=traceback.format_exc()[-600:])
        r['sonuc'] = 'PASS' if (r['q_poster'] and r['q_video'] and r['q_son']) else 'FAIL'
        json.dump(r, open(os.path.join(g.out, f'{slug}-qc.json'), 'w'), indent=1)
        if r['sonuc'] == 'FAIL':
            fails.append(key)
        el = time.time() - t0; n = i + 1
        print(f'ILERLEME {key} {r["sonuc"]} | is {n}/{len(pairs)} | genel ~{g.sira + n}/{toplam} %{100 * (g.sira + n) / toplam:.0f} | '
              f'gecen {el / 60:.1f} dk | kalan (bu is) {el / n * (len(pairs) - n) / 60:.1f} dk | '
              + ' '.join(f'{k}={r.get(k)}' for k in ('q_poster', 'q_video', 'q_son', 'son_oran', 'bos_oran', 'sure', 'kare', 'uretim_sn', 'hata')),
              flush=True)
    print(f'OZET {len(pairs) - len(fails)}/{len(pairs)} PASS' + (f' FAIL: {",".join(fails)}' if fails else ''))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
