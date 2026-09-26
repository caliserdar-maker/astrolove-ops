#!/usr/bin/env python3
"""Plate uretiminin SONUCU: kac plate yazildi, kac kapida kaldi, neden.

SALT OKUR. PLATES klasorunu listeler, RAPOR_*.json'lari ozetler, ardindan
slogan onay sayfasini uretir. Tek kosuda tam durum.
"""
import json, subprocess, sys
from pathlib import Path

PLATES = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_ozet').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
BOYLAR = ['8x10', '11x14', '12x16', '12x18', '16x20', '16x24', '18x24', '20x30',
          '24x30', '24x32', '24x36', '30x40', 'A1', 'A2', 'A3', 'A4']


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def main():
    var = set()
    for satir in rc('lsf', PLATES, '--include', '*.png').splitlines():
        var.add(satir.strip().replace('.png', ''))
    rc('copy', PLATES, str(W), '--include', 'RAPOR_*.json')
    yazildi, kaldi, bant_yok, diger = {}, {}, {}, {}
    for f in sorted(W.glob('RAPOR_*.json')):
        d = json.loads(f.read_text())
        yazildi.update(d.get('plateler', {}))
        for k, v in (d.get('hata') or {}).items():
            if isinstance(v, dict) and v.get('slogan_temizlik_kapisi') == 'KALDI':
                kaldi[k] = {x: v.get(x) for x in ('hayalet', 'hayalet_ONCE',
                                                  'iyilesme_orani', 'sebep') if x in v}
            elif isinstance(v, dict) and 'bulunamadi' in str(v.get('sebep', '')):
                bant_yok[k] = v.get('tani')
            else:
                diger[k] = v
    # 16 boy x 5 edisyon matrisi: hangi plate dosyasi Drive'da GERCEKTEN var
    eksik = [f'{e}_{b}' for b in BOYLAR for e in EDISYONLAR if f'{e}_{b}' not in var]
    print(json.dumps({
        'PLATES_de_png': len(var),
        'hedef': len(BOYLAR) * len(EDISYONLAR),
        'eksik_sayi': len(eksik),
        'eksik': eksik,
        'rapora_yazilan': len(yazildi),
        'kapida_KALDI': {'sayi': len(kaldi), 'liste': kaldi},
        'slogan_bandi_BULUNAMADI': {'sayi': len(bant_yok),
                                    'liste': {k: 'tani var' for k in bant_yok}},
        'diger_hata': diger,
    }, indent=1, ensure_ascii=False))
    # Bant bulunamayanlarin tanisi ayri: uzun, sona konur.
    if bant_yok:
        print('\n--- SLOGAN BANDI BULUNAMADI TANILARI ---')
        for k, t in bant_yok.items():
            print(f'{k}: {json.dumps(t, ensure_ascii=False)[:600]}')


if __name__ == '__main__':
    main()
