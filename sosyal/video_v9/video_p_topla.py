#!/usr/bin/env python3
"""video_p_toplu.py islerinin ciktilarini birlestirir (20 Eki 2026). Yazma yok; yalniz dosya.

Girdi (T): satir/<CIFT>.json, ILK/<CIFT>.jpg (arayuz alanlari isaretli ilk kare).
Cikti (OUT): KONTROL.csv (78 satir), KONTAK_ILK_KARE_01..n.jpg (sayfa basina 12 ilk kare), OZET.txt. 78 PASS degilse cikis 1.
Kullanim: video_p_topla.py T OUT
"""
import csv
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

KOLON = ['cift', 'baslik', 'sonuc', 'fail', 'baslik_px', 'baslik_kucultme', 'sure', 'kare', 'muzik_ayni', 'ilk_kare_ncc',
         'ilk_kare_parlaklik', 'poster_ncc', 'poster_kutu', 'pay_baslik', 'pay_poster', 'gecis_adim_oran', 'siyah_kare_yok',
         'b_fark_max', 'mp4_b_psnr_min', 'onayli_p_fark', 'sure_sn']
SAYFA, KOL, TW, TH = 12, 6, 300, 533


def main():
    t, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    sat = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(t, 'satir', '*.json')))]
    with open(os.path.join(out, 'KONTROL.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=KOLON, extrasaction='ignore'); w.writeheader(); w.writerows(sat)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
    except OSError:
        f = ImageFont.load_default(size=20)
    sayfalar = []
    for p in range(0, len(sat), SAYFA):
        grup = sat[p:p + SAYFA]
        sat_n = (len(grup) + KOL - 1) // KOL
        sh = Image.new('RGB', (20 + KOL * (TW + 20), 20 + sat_n * (TH + 80)), 'white'); d = ImageDraw.Draw(sh)
        for i, s in enumerate(grup):
            x, y = 20 + (i % KOL) * (TW + 20), 20 + (i // KOL) * (TH + 80)
            yol = os.path.join(t, 'ILK', f"{s['cift']}.jpg")
            if os.path.isfile(yol):
                sh.paste(Image.open(yol).convert('RGB').resize((TW, TH), Image.LANCZOS), (x, y + 56))
            k = s.get('baslik_kucultme', 1.0)
            renk = (20, 20, 20) if s.get('sonuc') == 'PASS' else (200, 0, 0)
            d.text((x, y), s['cift'], font=f, fill=renk)
            d.text((x, y + 24), f"{s.get('sonuc')}  baslik {s.get('baslik_px')} px" + (f" (x{k})" if k not in (1, 1.0, None) else ''), font=f, fill=renk)
        ad = f'KONTAK_ILK_KARE_{p // SAYFA + 1:02d}.jpg'
        sh.save(os.path.join(out, ad), quality=88); sayfalar.append(ad)
    n = sum(s.get('sonuc') == 'PASS' for s in sat)
    kucuk = sorted((s for s in sat if s.get('baslik_kucultme', 1) < 1), key=lambda s: s['baslik_kucultme'])
    say = lambda k: [s[k] for s in sat if isinstance(s.get(k), (int, float))]  # noqa: E731
    oz = [f'SOSYAL VIDEO P x{len(sat)} (Metricool/hesap yazma 0): {n} PASS / {len(sat) - n} FAIL',
          f"FAIL: {[(s['cift'], s.get('fail')) for s in sat if s.get('sonuc') != 'PASS']}",
          f'sure {min(say("sure"), default=0)}-{max(say("sure"), default=0)} sn, kare {min(say("kare"), default=0)}-{max(say("kare"), default=0)}, '
          f'muzik ayni {sum(bool(s.get("muzik_ayni")) for s in sat)}/{len(sat)}, siyah kare yok {sum(bool(s.get("siyah_kare_yok")) for s in sat)}/{len(sat)}',
          f'ilk kare NCC en az {min(say("ilk_kare_ncc"), default=0)}, poster NCC en az {min(say("poster_ncc"), default=0)}, '
          f'gecis adim orani en cok {max(say("gecis_adim_oran"), default=0)}, B fark en cok {max(say("b_fark_max"), default=-1)}, '
          f'mp4 / B PSNR en az {min(say("mp4_b_psnr_min"), default=0)} dB',
          f"onayli CANCER_LIBRA P karesi farki: {[s.get('onayli_p_fark') for s in sat if s['cift'] == 'CANCER_LIBRA']}",
          f'baslik kuculen {len(kucuk)} (kural 128.3 px): ' + ', '.join(f"{s['cift']} {s['baslik_px']}px (x{s['baslik_kucultme']})" for s in kucuk),
          f'kontak: {sayfalar}']
    open(os.path.join(out, 'OZET.txt'), 'w', encoding='utf-8').write('\n'.join(oz) + '\n')
    print('\n'.join(oz))
    sys.exit(0 if n == 78 and len(sat) == 78 else 1)


if __name__ == '__main__':
    main()
