#!/usr/bin/env python3
"""AstroLoveArt IG/FB ornek seti: ChatGPT bos sahneleri + gercek poster + yazilar (kodla).
Kullanim: python3 ig_bas.py POSTER.png CIKTI_KLASORU [--reel]
Poster 4:5 olmali (kontrol edilir, oran bozulmaz).
Gereken dosyalar (bu betikle ayni klasorde):
  set/  -> AstroLoveArt_Cancer_Libra_IG_FB_Ornek.zip icerigi (C01..C03, R01..R03 PNG + YERLESIM_STORYBOARD.json)
  CormorantGaramond[wght].ttf, Manrope[wght].ttf  (github.com/google/fonts ofl/)
NOT: Yazilar su an Cancer & Libra icin sabit (JSON'dan). 78 cift icin metindeki burc adlari cifte gore degistirilmeli.
Koordinator yerel denemesi (3 Eki): carousel 3 JPG + Reel MP4 ~27 sn; Serdar onayladi."""
import json, sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.abspath(__file__))
SET = os.path.join(KOK, 'set')
FONT = {'Cormorant Garamond': os.path.join(KOK, 'CormorantGaramond[wght].ttf'),
        'Manrope': os.path.join(KOK, 'Manrope[wght].ttf')}
SPEC = json.load(open(os.path.join(SET, 'YERLESIM_STORYBOARD.json')))


def font(aile, agirlik, px):
    f = ImageFont.truetype(FONT[aile], px)
    try:
        f.set_variation_by_axes([agirlik])
    except Exception as e:
        raise SystemExit(f'font agirligi ayarlanamadi: {aile} {agirlik}: {e}')
    return f


def yazi_katmani(boyut, katmanlar, alfa=None):
    """Seffaf RGBA katman; her yazi kutusunda yatay+dikey ortali. Sigmazsa hata."""
    k = Image.new('RGBA', boyut, (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    for i, L in enumerate(katmanlar):
        a = 1.0 if alfa is None else alfa[i]
        if a <= 0:
            continue
        f = font(L['font_family'], L['font_weight'], L['font_size_px'])
        x, y, w, h = L['box_xywh']
        l, t, r, b = d.textbbox((0, 0), L['text'], font=f)
        tw, th = r - l, b - t
        if tw > w or th > h:
            raise SystemExit(f"yazi kutuya sigmiyor: {L['text']} ({tw}x{th} > {w}x{h})")
        renk = tuple(int(L['color_hex'][j:j + 2], 16) for j in (1, 3, 5))
        d.text((x + (w - tw) / 2 - l, y + (h - th) / 2 - t), L['text'], font=f,
               fill=renk + (round(255 * a),))
    return k


def poster_yerlestir(sahne, poster, kutu):
    x, y, w, h = kutu
    pw, ph = poster.size
    if abs(pw / ph - 0.8) > 0.002:
        raise SystemExit(f'poster 4:5 degil: {pw}x{ph}')
    s = sahne.copy()
    s.paste(poster.resize((w, h), Image.LANCZOS), (x, y))
    return s


def carousel(poster, cikti):
    out = []
    for p in SPEC['plates']:
        if not p['id'].startswith('C'):
            continue
        sahne = Image.open(os.path.join(SET, p['file'])).convert('RGB')
        s = poster_yerlestir(sahne, poster, p['poster_inner_box_xywh']).convert('RGBA')
        s.alpha_composite(yazi_katmani(s.size, p['overlay_text_layers']))
        yol = os.path.join(cikti, f"{p['id']}_1080x1350.jpg")
        s.convert('RGB').save(yol, quality=95)
        out.append(yol)
    return out


def rampa(t, giris, cikis=None):
    a = 0.0
    if t >= giris[0]:
        a = 1.0 if t >= giris[1] else (t - giris[0]) / (giris[1] - giris[0])
    if cikis and t >= cikis[0]:
        a = min(a, 0.0 if t >= cikis[1] else 1 - (t - cikis[0]) / (cikis[1] - cikis[0]))
    return a


def reel(poster, cikti):
    R = SPEC['reel']
    p0 = next(p for p in SPEC['plates'] if p['id'] == 'R01')
    usta = poster_yerlestir(Image.open(os.path.join(SET, p0['file'])).convert('RGB'), poster,
                            p0['poster_inner_box_xywh'])
    W, H = usta.size
    px, py = R['camera']['pivot_px']
    fps, n = R['frames_per_second'], R['total_frames']
    katmanlar = R['overlay_text_layers']
    yol = os.path.join(cikti, 'REEL_1080x1920_9sn.mp4')
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264',
                           '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', yol],
                          stdin=subprocess.PIPE)
    for i in range(n):
        t = i / fps
        s = 1 + 0.10 * min(max(t, 0) / 6.6, 1)
        kx0, ky0 = px - px / s, py - py / s
        kare = usta.resize((W, H), Image.LANCZOS, box=(kx0, ky0, kx0 + W / s, ky0 + H / s)).convert('RGBA')
        alfa = [rampa(t, L['enter_sec'], L.get('exit_sec')) for L in katmanlar]
        kare.alpha_composite(yazi_katmani((W, H), katmanlar, alfa))
        ff.stdin.write(kare.convert('RGB').tobytes())
        if i in (0, 99, 198, 269):
            kare.convert('RGB').save(os.path.join(cikti, f'REEL_kare_{t:0.2f}sn.jpg'), quality=92)
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit('ffmpeg hata')
    return yol


if __name__ == '__main__':
    poster = Image.open(sys.argv[1]).convert('RGB')
    cikti = sys.argv[2]
    os.makedirs(cikti, exist_ok=True)
    for y in carousel(poster, cikti):
        print('carousel', y)
    if '--reel' in sys.argv:
        print('reel', reel(poster, cikti))
