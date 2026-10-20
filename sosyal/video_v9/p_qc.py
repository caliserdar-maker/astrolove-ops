#!/usr/bin/env python3
"""Acilis P olcum + kontak (20 Eki 2026). Yazma yok; yalniz dosya.

Girdi (DIR): P_<CIFT>.mp4, P_kare.png, p.json (acilis_p.py), poster.jpg (kaynak), muzik.m4a,
  kare/<B1|C|P>/<slug>-kare_<s>s.jpg (ilk 3 sn, KONTAK_T), kare/B_esit/ ve kare/P_esit/ (ESIT_T: B ile ayni mi).
Kontrol (OLCUM.txt, PASS/FAIL; herhangi FAIL -> cikis 1):
  video 1080x1920, 30 fps, 24,0 sn, ses var ve muzik ile ayni (PCM md5); 0. kare = P karesi (NCC >= 0.99), siyah degil;
  0. karede poster NCC (kaynak) >= 0.99; baslik ve poster arayuz alanlari disinda (ust 230, alt 1536, sag 918; sol 162)
  ve 9:16'da ortali; 0-3 sn ardisik kare farki (gecis yumusak, siyah kare yok); 1,5 sn sonrasi B ile ayni (fark 0).
Cikti: KONTAK_B1_C_P.jpg (satir = acilis, sutun = KONTAK_T), ILK_KARE_ARAYUZ.jpg, OLCUM.txt
Kullanim: p_qc.py DIR CIFT
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
KONTAK_T = [0, 0.6, 1.2, 1.35, 1.5, 2.0, 2.5, 3.0]
ESIT_T = [1.5, 3, 10, 20]
OLC = []


def kayit(ad, ok, ayrinti):
    OLC.append((ad, bool(ok), ayrinti)); print(f"{'PASS' if ok else 'FAIL'} {ad}: {ayrinti}", flush=True)


def ncc(a, b):
    a = np.asarray(a, np.float64).ravel(); b = np.asarray(b, np.float64).ravel()
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def ffprobe(yol):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', yol], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def pcm_md5(yol, t=24):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', yol, '-map', '0:a:0', '-t', str(t), '-f', 'md5', '-'], capture_output=True, text=True)
    return r.stdout.strip()


def kareler(yol, t1, olcek=4):
    """0..t1 sn arasi tum kareler (1/olcek boyutunda), float32 dizisi."""
    w, h = W // olcek, H // olcek
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', yol, '-t', str(t1), '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3).astype(np.float32)


def ilk_kare(yol):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', yol, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3)


def olc(d, cift, kontak=True):
    """Olcumler (OLC listesine PASS/FAIL), ILK_KARE_ARAYUZ.jpg ve OLCUM.txt; kontak=True ise KONTAK_B1_C_P.jpg da.
    Donus: (OLC, M) - M toplu tablo icin sayilar."""
    OLC.clear(); M = {}
    a, b = (x.capitalize() for x in cift.split('_'))
    slug = f'{a.lower()}-and-{b.lower()}'
    vid = os.path.join(d, f'P_{cift}.mp4')
    bi = json.load(open(os.path.join(d, 'p.json')))
    P = np.asarray(Image.open(os.path.join(d, 'P_kare.png')).convert('RGB'))

    # 1) dosya
    pr = ffprobe(vid)
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    au = [s for s in pr['streams'] if s['codec_type'] == 'audio']
    sure = float(pr['format']['duration'])
    fps = eval(v['r_frame_rate'])
    md_v, md_m = (pcm_md5(vid), pcm_md5(os.path.join(d, 'muzik.m4a'))) if au else ('', '')
    M.update(sure=round(sure, 3), kare=int(v.get('nb_frames', 0)), muzik_ayni=md_v == md_m and md_v != '')
    kayit('Video dosyasi', (v['width'], v['height']) == (W, H) and abs(fps - FPS) < 0.01 and abs(sure - 24.0) <= 0.05 and int(v.get('nb_frames', 720)) == 720,
          f"{v['width']}x{v['height']}, {fps:g} fps, {sure:.3f} sn, {v.get('nb_frames')} kare, {v['codec_name']}")
    kayit('Muzik degismedi', len(au) == 1 and md_v == md_m and md_v != '',
          f"ses {au[0]['codec_name'] if au else 'yok'}, PCM md5 video {md_v[-12:]} / muzik {md_m[-12:]}")

    # 2) 0. kare
    f0 = ilk_kare(vid)
    n0 = ncc(f0.mean(2), P.mean(2))
    M.update(ilk_kare_ncc=round(n0, 4), ilk_kare_parlaklik=round(float(f0.mean()), 1))
    kayit('0. kare = P karesi, siyah degil', n0 >= 0.99 and f0.mean() > 60, f'NCC {n0:.4f}, ortalama parlaklik {f0.mean():.1f}')
    px0, py0, px1, py1 = bi['poster_kutu']
    src = Image.open(os.path.join(d, 'poster.jpg')).convert('L').resize((px1 - px0, py1 - py0), Image.LANCZOS)
    g0 = Image.fromarray(f0).convert('L').crop((px0 + 3, py0 + 3, px1 - 3, py1 - 3))
    n1 = ncc(g0, src.crop((3, 3, src.width - 3, src.height - 3)))
    M['poster_ncc'] = round(n1, 4)
    kayit('Poster pikselleri (0. kare, kaynak)', n1 >= 0.99, f'NCC {n1:.4f}; poster {px1 - px0}x{py1 - py0} @({px0},{py0}), kaynak {bi["poster_kaynak"]}')

    # 3) arayuz alanlari, ortalama
    ui = bi['arayuz']; tb = bi['baslik_kutu']
    ogeler = {'baslik': tb, 'poster': bi['poster_kutu']}
    sol = W - ui['sag']
    pay = {k: (q[0] - sol, q[1] - ui['ust'], ui['sag'] - q[2], ui['alt'] - q[3]) for k, q in ogeler.items()}
    M.update(pay_baslik='/'.join(str(x) for x in pay['baslik']), pay_poster='/'.join(str(x) for x in pay['poster']),
             baslik_px=bi['baslik_px'], baslik_kucultme=bi.get('baslik_kucultme', 1.0), poster_kutu='x'.join(str(x) for x in bi['poster_kutu']))
    kayit('Arayuz alanlari (ust %12, alt %20, sag %15; sol ayni pay)', all(min(p) >= 0 for p in pay.values()),
          '; '.join(f'{k} pay sol/ust/sag/alt {p[0]}/{p[1]}/{p[2]}/{p[3]} px' for k, p in pay.items())
          + f" (alan: y {ui['ust']}-{ui['alt']}, x {sol}-{ui['sag']})")
    cx = {k: (q[0] + q[2]) / 2 for k, q in ogeler.items()}
    cy = (bi['blok_y'][0] + bi['blok_y'][1]) / 2
    kayit('9:16 ortali', all(abs(c - W / 2) <= 1 for c in cx.values()) and abs(cy - H / 2) <= 1,
          f"yatay merkez baslik {cx['baslik']:.1f}, poster {cx['poster']:.1f}; blok y {bi['blok_y'][0]}-{bi['blok_y'][1]} merkez {cy:.1f}; "
          f"olcek s {bi['s']} (PIN_V2 x s), baslik {bi['baslik_px']} px, & {bi['amp_px']} px, kontrast {bi['kontrast']}:1")

    # 4) gecis: 0-3 sn ardisik kare farki. Yumusak = tek karede P->B toplam degisiminin <= %35'i (sert kesme %100);
    #    siyah kare yok = 0. kare siyah degil ve 0-1,5 sn'de B'nin kendi en koyu karesinden koyu kare yok.
    F = kareler(vid, 3.0)
    df = np.abs(np.diff(F, axis=0)).mean((1, 2, 3))
    parl = F.mean((1, 2, 3))
    t = np.arange(len(F)) / FPS
    i15 = int(round(1.5 * FPS))
    toplam = float(np.abs(F[0] - F[i15]).mean())
    gec = df                                         # 0-3 sn tum ardisik kare adimlari (sert kesme hicbir yerde yok)
    oran = float(gec.max() / toplam)
    karanlik = parl[t < 1.5].min() >= 0.9 * parl[t >= 1.5].min()
    M.update(gecis_adim_oran=round(oran, 3), siyah_kare_yok=bool(karanlik and parl[0] > 60))
    kayit('Gecis yumusak, siyah kare yok (0-3 sn)', oran <= 0.35 and karanlik and parl[0] > 60,
          f'0-3 sn: en buyuk tek kare adimi {gec.max():.1f} ({t[1:][int(gec.argmax())]:.2f} sn)'
          f' = P->B toplam farkin ({toplam:.1f}) %{100 * oran:.0f}'
          f' (esik %35; sert kesme %100); parlaklik 0. kare {parl[0]:.1f}, 0-1,5 sn en az {parl[t < 1.5].min():.1f}, '
          f'B (1,5-3 sn) en az {parl[t >= 1.5].min():.1f}; {len(F)} kare')

    # 5) 1,5 sn sonrasi B ile ayni
    fk = []
    for s in ESIT_T:
        x = np.asarray(Image.open(os.path.join(d, 'kare', 'P_esit', f'{slug}-kare_{s:g}s.jpg'))).astype(int)
        y = np.asarray(Image.open(os.path.join(d, 'kare', 'B_esit', f'{slug}-kare_{s:g}s.jpg'))).astype(int)
        fk.append(int(np.abs(x - y).max()))
    # mp4'un kendisi: ayni saniyelerdeki kare B karesiyle ayni; kodlama farki icin PSNR >= 35 dB (koyu lacivert karelerde NCC
    # kodlama gurultusune duyarli; yerel olcum: ayni kare 40-42 dB, yanlis kare ~4 dB)
    nv = []
    for s in ESIT_T:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', vid, '-ss', f'{s}', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           capture_output=True, check=True)
        x = np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3).astype(np.float64)
        y = np.asarray(Image.open(os.path.join(d, 'kare', 'B_esit', f'{slug}-kare_{s:g}s.jpg')).convert('RGB')).astype(np.float64)
        nv.append(10 * np.log10(255 ** 2 / max(((x - y) ** 2).mean(), 1e-9)))
    M['b_fark_max'] = max(fk); M['mp4_b_psnr_min'] = round(min(nv), 1)
    kayit('1,5 sn sonrasi B ile ayni (akis degismedi)', max(fk) == 0 and min(nv) >= 35,
          ', '.join(f'{s:g} sn fark {f}' for s, f in zip(ESIT_T, fk)) + '; mp4 karesi / B PSNR ' + ', '.join(f'{n:.1f}' for n in nv) + ' dB (esik 35)')

    try:
        fo = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
    except OSError:
        fo = fb = ImageFont.load_default(size=20)
    # kontak: B1 / C / P ilk 3 sn (yalniz tek ornekte)
    if kontak:
        tw, th = 216, 384
        sh = Image.new('RGB', (120 + len(KONTAK_T) * (tw + 10), 50 + 3 * (th + 40)), 'white'); dr = ImageDraw.Draw(sh)
        for j, s in enumerate(KONTAK_T):
            dr.text((120 + j * (tw + 10), 12), f'{s:g} sn', font=fo, fill=(60, 60, 60))
        for i, ac in enumerate(['B1', 'C', 'P']):
            y = 50 + i * (th + 40)
            dr.text((12, y + th // 2), ac, font=fb, fill=(20, 20, 20))
            for j, s in enumerate(KONTAK_T):
                im = Image.open(os.path.join(d, 'kare', ac, f'{slug}-kare_{s:g}s.jpg')).resize((tw, th), Image.LANCZOS)
                sh.paste(im, (120 + j * (tw + 10), y))
        sh.save(os.path.join(d, 'KONTAK_B1_C_P.jpg'), quality=90)

    # arayuz alanlari isaretli ilk kare
    im = Image.fromarray(f0).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); o = ImageDraw.Draw(ov)
    for kutu in ((0, 0, W, ui['ust']), (0, ui['alt'], W, H), (ui['sag'], 0, W, H)):
        o.rectangle(kutu, fill=(220, 30, 30, 90))
    o.rectangle((0, 0, sol, H), outline=(220, 30, 30, 160), width=2)
    for k, q in ogeler.items():
        o.rectangle(q, outline=(20, 170, 60, 255), width=4)
    im = Image.alpha_composite(im, ov).convert('RGB'); dr = ImageDraw.Draw(im)
    for txt, y in (('TikTok/Reels ust arayuz %12', 12), ('alt arayuz %20 (aciklama, muzik)', ui['alt'] + 12)):
        dr.text((16, y), txt, font=fb, fill=(255, 255, 255))
    dr.text((ui['sag'] + 6, H // 2), 'sag\n%15', font=fb, fill=(255, 255, 255))
    im.save(os.path.join(d, 'ILK_KARE_ARAYUZ.jpg'), quality=92)

    fail = [k for k, ok, _ in OLC if not ok]
    with open(os.path.join(d, 'OLCUM.txt'), 'w', encoding='utf-8') as fh:
        fh.write(f'ACILIS P OLCUM ({cift}, ornek; Metricool/hesap yazma 0)\n')
        for k, ok, ay in OLC:
            fh.write(f"{'PASS' if ok else 'FAIL'} {k}: {ay}\n")
        fh.write('Zamanlama: 0-1,2 sn P karesi, 1,2-1,5 sn yumusak gecis (cos), 1,5 sn sonrasi B (C acilisi ile ayni kurgu)\n')
        fh.write(f"SONUC: {'PASS' if not fail else 'FAIL ' + ', '.join(fail)}\n")
    print('SONUC:', 'PASS' if not fail else 'FAIL ' + ', '.join(fail))
    M['sonuc'] = 'PASS' if not fail else 'FAIL'; M['fail'] = '; '.join(fail)
    return list(OLC), M


def main():
    _, M = olc(sys.argv[1], sys.argv[2])
    sys.exit(0 if M['sonuc'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
