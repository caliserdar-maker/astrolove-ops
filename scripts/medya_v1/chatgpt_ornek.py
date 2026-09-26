#!/usr/bin/env python3
"""GOREV_0019: ChatGPT gorsel DNA ornekleri icin kaynak posterler.

Onayli uretim yolu (siparis_dosyasi.py, --plate canva) ile CANCER_LIBRA /
EMMA (Cancer) / NOAH (Libra) / "Written in the stars" posterleri uretir.
Kapilar PASS degilse dosya YAZILMAZ, yalniz raporlanir. Etsy'ye yazma yok.
Isimler ornek (musteri verisi degil).
"""
import json, subprocess, sys
from pathlib import Path

from PIL import Image, ImageCms

HED = 'gdrive:ASTROLOVE/TEMP/CHATGPT_ORNEK/POSTER'
W = Path('_siparis').resolve()
CIFT, ISIM1, ISIM2, MESAJ = 'CANCER_LIBRA', 'EMMA', 'NOAH', 'Written in the stars'
ISLER = [(r, '8x10', f'CL_EMMA_NOAH_{r}.jpg') for r in
         ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT')]
ISLER.append(('MIDNIGHT_BLUE', '16x20', 'CL_EMMA_NOAH_MIDNIGHT_BLUE_TAM.jpg'))   # en buyuk POD 4x5


def rc(*a):
    r = subprocess.run(['rclone', '--timeout', '300s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=1800)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')


def main():
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    ozet = []
    for i, (renk, boy, ad) in enumerate(ISLER, 1):
        print(f'[{i}/{len(ISLER)}] {renk} {boy}', flush=True)
        p = subprocess.run([sys.executable, 'scripts/medya_v1/siparis_dosyasi.py',
                            '--cift', CIFT, '--renk', renk, '--boy', boy, '--isim1', ISIM1,
                            '--isim2', ISIM2, '--mesaj', MESAJ, '--plate', 'canva'],
                           capture_output=True, text=True)
        cik = W / f'{CIFT}_{renk}_{boy}'
        rap = cik / 'KAPI_RAPORU.json'
        d = json.loads(rap.read_text()) if rap.exists() else {}
        kap = d.get('kapilar') or {}
        satir = {'dosya': ad, 'durum': d.get('durum'), 'kapilar_gecti': d.get('kapilar_gecti'),
                 'FAIL': [k for k, v in kap.items() if v is False], 'yazildi': False}
        if d.get('kapilar_gecti') is True:
            jpg = max(cik.glob('*.jpg'), key=lambda f: f.stat().st_size)
            yerel = cik / ad
            Image.open(jpg).convert('RGB').save(yerel, 'JPEG', quality=92, icc_profile=srgb)
            rc('copyto', str(yerel), f'{HED}/{ad}')
            satir.update(yazildi=True, px=list(Image.open(yerel).size))
        elif not d:
            satir['hata'] = (p.stderr or p.stdout)[-300:]
        ozet.append(satir)
        print(json.dumps(satir, ensure_ascii=False), flush=True)
    print('OZET', sum(s['yazildi'] for s in ozet), '/', len(ozet), 'yazildi')


if __name__ == '__main__':
    main()
