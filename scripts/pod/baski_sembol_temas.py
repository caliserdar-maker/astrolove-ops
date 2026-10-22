#!/usr/bin/env python3
"""Test baski dosyalari: isimlerin ustundeki kucuk sembol bandi temas sayfasi (SALT OKUMA, 28 Eyl hata-kontrol).
Girdi: KOK/<CIFT>_<RENK>_11x14/BASKI_11x14.jpg (+ KAPI_RAPORU.json), siparis_dosyasi.py --urun pod ciktisi.
Bant, kapak olcumunden oranla (kapak_v8: poster = BASKI - 5 mm rebate; 78 kapakta sembol y 1390-1539 / poster
ic yuksekligi): baski yuksekliginin %56-%75'i, eninin %18-%82'si (her renkte yerlesim birkac px farkli, pay genis).
Kareler 1:1 piksel (olcekleme yok); satir = renk, sutun = cift; her karenin ustunde cift, renk, kapi sonuclari.
Ayrica her kare icin 3x buyutulmus sol/sag sembol kirpimi: SEMBOL_x3/<CIFT>_<RENK>.jpg.
Kullanim: baski_sembol_temas.py KOK CIKIS
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RENKLER = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'WARM_PARCHMENT', 'CHAMPAGNE_IVORY', 'PURE_WHITE']
Y0, Y1, X0, X1 = 0.56, 0.75, 0.18, 0.82


def kapi_ozet(p):
    if not p.is_file():
        return 'rapor yok'
    r = json.loads(p.read_text())
    sk = r.get('sembol_kapisi') or (r.get('bilgi') or {}).get('sembol_kapisi') or {}
    kg = r.get('kapilar_gecti')
    return f"durum {r.get('durum')} | kapilar {kg} | sembol_kapisi {sk.get('gecti') if isinstance(sk, dict) else sk}"


def main():
    kok, cik = Path(sys.argv[1]), Path(sys.argv[2])
    (cik / 'SEMBOL_x3').mkdir(parents=True, exist_ok=True)
    ciftler = sorted({d.name[:-len(r) - 7] for d in kok.iterdir() if d.is_dir()
                      for r in RENKLER if d.name.endswith(f'_{r}_11x14')})
    kareler, satir = {}, []
    for c in ciftler:
        for r in RENKLER:
            d = kok / f'{c}_{r}_11x14'
            b = d / 'BASKI_11x14.jpg'
            oz = kapi_ozet(d / 'KAPI_RAPORU.json')
            if not b.is_file():
                satir.append(f'- {c} {r}: BASKI YOK ({oz})')
                continue
            im = Image.open(b).convert('RGB')
            W, H = im.size
            k = im.crop((round(W * X0), round(H * Y0), round(W * X1), round(H * Y1)))
            kareler[(c, r)] = (k, oz)
            sol = k.crop((0, 0, k.width // 2, k.height)); sag = k.crop((k.width // 2, 0, k.width, k.height))
            for ad, p in (('SOL', sol), ('SAG', sag)):
                p.resize((p.width * 3, p.height * 3), Image.LANCZOS).save(cik / 'SEMBOL_x3' / f'{c}_{r}_{ad}.jpg',
                                                                        quality=92)
            satir.append(f'- {c} {r}: {W}x{H} | {oz}')
    if not kareler:
        print('\n'.join(satir)); sys.exit('hic baski dosyasi yok')
    kw = max(k.width for k, _ in kareler.values()); kh = max(k.height for k, _ in kareler.values())
    et, bos = 60, 20
    T = Image.new('RGB', (len(ciftler) * (kw + bos) + bos, len(RENKLER) * (kh + et + bos) + bos), (128, 128, 128))
    d = ImageDraw.Draw(T)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
    except OSError:
        font = ImageFont.load_default()
    for i, c in enumerate(ciftler):
        for j, r in enumerate(RENKLER):
            x, y = bos + i * (kw + bos), bos + j * (kh + et + bos)
            if (c, r) not in kareler:
                d.text((x + 6, y + 8), f'{c} {r}: BASKI YOK', fill=(255, 255, 0), font=font)
                continue
            k, oz = kareler[(c, r)]
            d.text((x + 6, y + 8), f"{c.replace('_', ' + ')} | {r}", fill=(255, 255, 255), font=font)
            T.paste(k, (x, y + et))
    T.save(cik / 'BASKI_SEMBOL_TEMAS.jpg', quality=92)
    (cik / 'BASKI_SEMBOL_OZET.md').write_text('# Test baski sembol bandi\n\n' + '\n'.join(satir) + '\n')
    print('\n'.join(satir))


if __name__ == '__main__':
    main()
