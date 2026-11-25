"""Kapak SONDA (Serdar 25 Kas 2026: "video kapakla baslar, kapakla biter"; ilk kare = son kare).
kapak_basa.py'nin (onayli 2. yontem, 15 Eki) sondaki aynasi: --sure saniyelik cikti; SURE - TAM - GECIS'ten SURE - TAM'a kadar
orijinalden kapaga kosinus capraz gecis (kapak_basa ile ayni egri), son TAM saniye tam kapak. Giris videosu en az SURE + 0.5 sn
olmali (video_uret --sure SURE+0.9: sondaki karartma SURE'den sonraya kalir, cikista karartma karesi yoktur).
Muzik: verilirse ilk SURE saniye, son 2 sn yumusak kisilma (afade), AAC 192k; yoksa ses yok. Video v9 ayarlariyla yeniden kodlanir.
QC (PASS/FAIL, --qc JSON): son kare = kapak (ort. fark < 2.0), gecis oncesi kare = orijinal (< 2.0), kare = 30 x SURE,
video ve ses suresi SURE +-0.02.
Kullanim: python3 kapak_son.py --video in.mp4 --kapak kapak.jpg --cikis out.mp4 --sure 15 [--tam 0.5] [--gecis 0.5] [--muzik m.m4a] [--qc q.json]
"""
import argparse, json, subprocess, sys
import numpy as np
from PIL import Image

ESIK = 2.0


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate,nb_frames,duration',
                        '-of', 'json', p], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)['streams']
    v = next(s for s in st if s['codec_type'] == 'video'); a = next((s for s in st if s['codec_type'] == 'audio'), None)
    return {'w': int(v['width']), 'h': int(v['height']), 'fps_str': v['r_frame_rate'], 'kare': int(v.get('nb_frames') or 0),
            'video_sn': float(v.get('duration') or 0), 'ses_sn': float(a['duration']) if a else None}


def kare(p, i, W, H):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f'select=eq(n\\,{i})', '-vframes', '1', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3).astype(np.float32)


def kapak_dizi(k, W, H):
    im = Image.open(k).convert('RGB')
    s = max(W / im.size[0], H / im.size[1])
    im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    x0 = (im.size[0] - W) // 2; y0 = (im.size[1] - H) // 2
    return np.asarray(im.crop((x0, y0, x0 + W, y0 + H))).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', required=True); ap.add_argument('--kapak', required=True); ap.add_argument('--cikis', required=True)
    ap.add_argument('--sure', type=float, required=True); ap.add_argument('--tam', type=float, default=0.5)
    ap.add_argument('--gecis', type=float, default=0.5); ap.add_argument('--muzik'); ap.add_argument('--qc', default='')
    g = ap.parse_args()
    v = probe(g.video); W, H = v['w'], v['h']; fps = eval(v['fps_str'])
    if v['video_sn'] < g.sure + 0.5:
        sys.exit(f'DUR: giris {v["video_sn"]} sn < sure + 0.5 (sondaki karartma cikisa girer)')
    n = int(round(g.sure * fps))
    a = g.sure - g.tam - g.gecis; b = g.sure - g.tam
    w = f'(0.5-0.5*cos(PI*clip((T-{a})/{g.gecis},0,1)))'          # kapagin agirligi (kapak_basa ile ayni kosinus)
    fc = (f'[0:v]trim=end_frame={n},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[o];'
          f'[1:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p,'
          f'fps={v["fps_str"]},trim=end_frame={n},setpts=PTS-STARTPTS[k];'
          f"[o][k]blend=all_expr='A*(1-{w})+B*{w}'[vo]")
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', g.video, '-loop', '1', '-framerate', v['fps_str'], '-t', f'{g.sure + 1:.3f}',
           '-i', g.kapak]
    if g.muzik:
        cmd += ['-i', g.muzik]
    cmd += ['-filter_complex', fc, '-map', '[vo]']
    if g.muzik:
        cmd += ['-map', '2:a', '-af', f'atrim=0:{g.sure},afade=t=out:st={g.sure - 2.0}:d=2,asetpts=N/SR/TB', '-c:a', 'aac', '-b:a', '192k']
    cmd += ['-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'slow', '-tune', 'grain',
            '-aq-mode', '3', '-r', v['fps_str'], '-frames:v', str(n), '-t', f'{g.sure}', '-movflags', '+faststart', g.cikis]
    subprocess.run(cmd, check=True)
    o = probe(g.cikis); K = kapak_dizi(g.kapak, W, H)
    son = kare(g.cikis, n - 1, W, H); once = int(round((a - 0.1) * fps))
    q = {'sure': g.sure, 'tam_sn': g.tam, 'gecis_sn': g.gecis, 'kare': o['kare'], 'video_sn': o['video_sn'], 'ses_sn': o['ses_sn'],
         'son_kare_kapak_fark': round(float(np.abs(son - K).mean()), 2),
         'gecis_oncesi_fark': round(float(np.abs(kare(g.cikis, once, W, H) - kare(g.video, once, W, H)).mean()), 2)}
    kap = {'son_kare_kapak': q['son_kare_kapak_fark'] < ESIK, 'gecis_oncesi_orijinal': q['gecis_oncesi_fark'] < ESIK,
           'kare': o['kare'] == n, 'video_sure': abs(o['video_sn'] - g.sure) <= 0.02,
           'ses': (not g.muzik) or (o['ses_sn'] is not None and abs(o['ses_sn'] - g.sure) <= 0.02)}
    q['kapilar'] = kap; q['sonuc'] = 'PASS' if all(kap.values()) else 'FAIL'
    if g.qc:
        json.dump(q, open(g.qc, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(q, ensure_ascii=False))
    sys.exit(0 if q['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
