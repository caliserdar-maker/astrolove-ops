#!/usr/bin/env python3
"""Referans maske HIZALI MI? (GOREV_0010 md.1 - SALT OKUR, kod degisikligi yok)

VINTAGE (tum boylar) ve MODERN A3 icin, ayni boyun PURE_WHITE kirpimiyla
slogan maskesi karsilastirilir: IoU ve en iyi dx/dy kaymasi.

Kirpimlarin ONCE blogu = ham plate'in slogan seridi. Plate'ler ayni sablondan
uretildigi icin kayma 0 BEKLENIR; kayma cikarsa 4. iterasyonun cozumu maske
degil HIZALAMA olur (GOREV_0010 md.2).
"""
import argparse, json, subprocess
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
KIRPIM = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES/SLOGAN_KIRPIM'
W = Path('_hiza').resolve(); W.mkdir(exist_ok=True)
REFERANS = 'PURE_WHITE'


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def bloklar(yol):
    """slogan_kirpim yerlesimi: y=4 etiket, +18 goruntu, blok sonu +26 pay."""
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    h = (a.shape[0] - 78) // 2
    if h < 20:
        return None, None
    return a[22:22 + h], a[h + 48:h + 48 + h]


def maske(once):
    """slogan_temizle ile AYNI olcut: |serit - zemin| > med + 6*MAD, taban 18."""
    import cv2
    kaba = np.abs(once - np.median(once)) > 25
    zem = np.zeros_like(once)
    for y in range(once.shape[0]):
        d = once[y][~kaba[y]]
        zem[y] = np.median(d) if d.size >= 20 else np.median(once[y])
    fark = np.abs(once - zem)
    med = float(np.median(fark)); mad = float(np.median(np.abs(fark - med))) * 1.4826
    esik = max(med + 6.0 * mad, 18.0)
    m = fark > esik
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    return m, round(esik, 1)


def zeminsiz(once):
    """Satir zemini cikarilmis, isaretten bagimsiz slogan sinyali.

    Maske-IoU dokulu edisyonlarda ISE YARAMAZ: Champagne'de maske butun
    kirpimi kapliyor (kutu 0-2399), IoU hizalama degil doku olcuyor. Burada
    zemin cikarilir ve MUTLAK deger alinir - slogan her iki edisyonda da
    zeminden SAPMA'dir (birinde koyu, digerinde acik olabilir), doku ise
    sifir ortalamali gurultu olarak korelasyonda sonumlenir.
    """
    zem = np.median(once, axis=1, keepdims=True)
    d = np.abs(once - zem)
    return d - d.mean()


def ncc(A, B, tara):
    """En iyi dx/dy ve o kaymadaki normalize capraz korelasyon."""
    en, arg = -2.0, (0, 0)
    pa = float(np.sqrt((A * A).sum()))
    for dy in range(-tara, tara + 1):
        for dx in range(-tara, tara + 1):
            Bs = np.roll(np.roll(B, dy, 0), dx, 1)
            pb = float(np.sqrt((Bs * Bs).sum()))
            if pa < 1e-6 or pb < 1e-6:
                continue
            r = float((A * Bs).sum()) / (pa * pb)
            if r > en:
                en, arg = r, (dx, dy)
    return round(en, 3), arg


def kutu(m):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    return [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())]


def kirpim_yolu(ed, boy):
    for ad in (f'SLOGAN_{ed}_{boy}_x3.jpg', f'SLOGAN_KALDI_{ed}_{boy}_x3.jpg'):
        f = W / ad
        if f.exists():
            return f
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edisyonlar', default='VINTAGE,MODERN')
    ap.add_argument('--tara', type=int, default=14, help='+-N piksel kayma taramasi')
    a = ap.parse_args()
    rc('copy', KIRPIM, str(W), '--include', '*.jpg')
    boylar = sorted({f.stem.replace('_x3', '').split('_')[-1] for f in W.glob('*.jpg')})
    sonuc, atlanan = {}, []
    for boy in boylar:
        rf = kirpim_yolu(REFERANS, boy)
        if rf is None:
            atlanan.append(f'{boy}: {REFERANS} kirpimi yok')
            continue
        ro, _ = bloklar(rf)
        if ro is None:
            atlanan.append(f'{boy}: {REFERANS} blok ayrilamadi')
            continue
        mr, er = maske(ro)
        for ed in [x.strip() for x in a.edisyonlar.split(',') if x.strip()]:
            hf = kirpim_yolu(ed, boy)
            if hf is None:
                continue
            ho, _ = bloklar(hf)
            if ho is None:
                atlanan.append(f'{ed}_{boy}: blok ayrilamadi')
                continue
            mh, eh = maske(ho)
            n = min(mr.shape[0], mh.shape[0])
            A, B = mr[:n], mh[:n]
            en, arg = -1.0, (0, 0)
            for dy in range(-a.tara, a.tara + 1):
                for dx in range(-a.tara, a.tara + 1):
                    Bs = np.roll(np.roll(B, dy, 0), dx, 1)
                    i = (A & Bs).sum() / max((A | Bs).sum(), 1)
                    if i > en:
                        en, arg = i, (dx, dy)
            r, (rdx, rdy) = ncc(zeminsiz(ro[:n]), zeminsiz(ho[:n]), a.tara)
            sonuc[f'{ed}_{boy}'] = {
                'NCC': r, 'NCC_dx': rdx, 'NCC_dy': rdy,
                'ham_IoU': round(float((A & B).sum() / max((A | B).sum(), 1)), 3),
                'en_iyi_IoU': round(float(en), 3), 'dx': arg[0], 'dy': arg[1],
                'ref_esik': er, 'hedef_esik': eh,
                'ref_kutu': kutu(A), 'hedef_kutu': kutu(B),
                'ref_maske_%': round(float(A.mean() * 100), 2),
                'hedef_maske_%': round(float(B.mean() * 100), 2)}
    print(json.dumps({'referans': REFERANS, 'atlanan': atlanan,
                      'sonuc': sonuc}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
