"""Add the final music track to silent reels (stream copy, no re-encode) + PASS/FAIL QC.

Usage: python3 muzik_ekle.py --muzik muzik.m4a --giris <dir or mp4> --cikis <dir> [--ek _muzik2] [--beklenen 78]
QC per video: audio and video 24.0 s (+-0.05), video stream bit-identical in length (720 frames), integrated loudness
-16 LUFS +-1.0 (ffmpeg ebur128). Writes MUZIK_QC.csv in --cikis; exit code 1 if any FAIL or count != --beklenen.
"""
import argparse, csv, glob, json, os, re, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--muzik', required=True); ap.add_argument('--giris', required=True); ap.add_argument('--cikis', required=True)
ap.add_argument('--ek', default=''); ap.add_argument('--beklenen', type=int, default=0)
g = ap.parse_args()
os.makedirs(g.cikis, exist_ok=True)
vids = [g.giris] if g.giris.endswith('.mp4') else sorted(glob.glob(os.path.join(g.giris, '*-astroloveart-reel*.mp4')))


def sure(p, s):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', s, '-show_entries', 'stream=duration,nb_frames,codec_name',
                        '-of', 'json', p], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)['streams']
    return st[0] if st else {}


def lufs(p):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-map', '0:a', '-af', 'ebur128', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None


rows = []; t0 = time.time()
for i, v in enumerate(vids):
    b = os.path.basename(v).replace('_sessiz', '')
    out = os.path.join(g.cikis, b.replace('.mp4', f'{g.ek}.mp4'))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-i', g.muzik, '-map', '0:v', '-map', '1:a', '-c', 'copy',
                    '-t', '24', '-movflags', '+faststart', out], check=True)
    a, vv = sure(out, 'a:0'), sure(out, 'v:0')
    r = dict(dosya=os.path.basename(out), ses_sn=float(a.get('duration', 0)), ses_codec=a.get('codec_name'),
             video_sn=float(vv.get('duration', 0)), kare=int(vv.get('nb_frames', 0)), lufs=lufs(out))
    r['sonuc'] = 'PASS' if (abs(r['ses_sn'] - 24) < 0.05 and abs(r['video_sn'] - 24) < 0.05 and r['kare'] == 720
                            and r['lufs'] is not None and abs(r['lufs'] + 16) <= 1.0) else 'FAIL'
    rows.append(r); n = i + 1; el = time.time() - t0
    print(f'ILERLEME {n}/{len(vids)} %{100 * n / len(vids):.0f} gecen {el:.0f} sn kalan {el / n * (len(vids) - n):.0f} sn '
          f'{r["dosya"]} ses={r["ses_sn"]} video={r["video_sn"]} kare={r["kare"]} lufs={r["lufs"]} {r["sonuc"]}', flush=True)
with open(os.path.join(g.cikis, 'MUZIK_QC.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0]) if rows else ['dosya']); w.writeheader(); [w.writerow(r) for r in rows]
fails = [r['dosya'] for r in rows if r['sonuc'] != 'PASS']
ok = rows and not fails and (not g.beklenen or len(rows) == g.beklenen)
print(f'OZET muzik {len(rows) - len(fails)}/{len(rows)} PASS' + (f', beklenen {g.beklenen}' if g.beklenen else '')
      + (f' FAIL: {",".join(fails)}' if fails else '') + f': {"PASS" if ok else "FAIL"}')
sys.exit(0 if ok else 1)
