#!/usr/bin/env python3
"""1:1 kesit karsilastirmasi (Serdar 3 Eki, zemin lekesi kaynagi): 3 bolge x [orijinal | eski kosu | yeni].
(a) cember cevresi, (b) yazi cevresi yildiz temizlenen alan (eski ile yeni farkinin en buyuk kucuk bileseni, cember
disi), (c) dokunulmamis bos zemin. Her bolge 400x400 px 1:1; alt satir ayni kesit 4x kontrast (leke gorunsun).

Kullanim: kesit_zemin.py --orijinal F --eski F --yeni F --etiket-eski "kosu N" --etiket-yeni "yeni" --cikti DIR --ad CIFT
          [--b-merkez x,y]
"""
import argparse, json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
KOK = Path(__file__).resolve().parent
A_KUTU = (560, 1880)     # cember sol yayi (16x20, 4800 px)
C_KUTU = (3900, 250)     # sag ust bos zemin
W_ = 400


def b_merkez(plate, kutular):
    """motorun temizledigi yildizlar: plate'te yazi kutulari (isim1, isim2, sonsuz, mesaj) + pay icindeki yildiz
    maskesi (tek_doku.yildiz_maskesi, motorla ayni); en buyuk bilesenin merkezi."""
    import sys
    sys.path.insert(0, str(KOK))
    import tek_doku as tdk
    P = np.asarray(Image.open(plate).convert('RGB'), np.float32)
    H, W = P.shape[:2]
    pay = int(round(tdk.PAY_ORAN * tdk.TEMIZLIK_PAYI * W))
    bolge = np.zeros((H, W), bool)
    K = json.loads(Path(kutular).read_text())
    for ad in ('isim1', 'isim2', 'sonsuz', 'mesaj'):
        y0, y1, x0, x1 = K[ad]
        bolge[max(0, y0 - pay):y1 + pay, max(0, x0 - pay):x1 + pay] = True
    m, _ = tdk.yildiz_maskesi(P, bolge)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, 4]))
    return int(cen[i][0]), int(cen[i][1])


def main():
    ap = argparse.ArgumentParser()
    for k in ('orijinal', 'eski', 'yeni', 'etiket-eski', 'etiket-yeni', 'cikti', 'ad'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--b-merkez')
    ap.add_argument('--plate', default=str(KOK / 'varlik' / 'plates' / 'BLUE_16x20_halkasiz.png'))
    ap.add_argument('--kutular', help='motor hucresi _oge_kutulari.json ([y0, y1, x0, x1])')
    a = ap.parse_args()
    L = lambda f: np.asarray(Image.open(f).convert('RGB'), np.float32)
    G, O, N = L(a.orijinal), L(a.eski), L(a.yeni)
    if a.b_merkez:
        bx, by = map(int, a.b_merkez.split(','))
    else:
        bm = b_merkez(a.plate, a.kutular) if a.kutular else None
        if bm is None:
            raise SystemExit('b bolgesi: temizlenen yildiz yok; --b-merkez ver')
        bx, by = bm
    H, W = G.shape[:2]
    B = {'a_cember_cevresi': A_KUTU,
         'b_yildiz_temizligi': (min(max(bx - W_ // 2, 0), W - W_), min(max(by - W_ // 2, 0), H - W_)),
         'c_bos_zemin': C_KUTU}
    f = ImageFont.truetype(str(KOK / 'font' / 'EBGaramond-Italic.ttf'), 24)
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    kay = {}
    for ad, (x, y) in B.items():
        out = Image.new('RGB', (3 * W_ + 40, 2 * W_ + 70), 'white'); d = ImageDraw.Draw(out)
        for i, (et, P) in enumerate((('orijinal', G), (a.etiket_eski, O), (a.etiket_yeni, N))):
            k = P[y:y + W_, x:x + W_]
            out.paste(Image.fromarray(np.clip(k, 0, 255).astype(np.uint8)), (i * (W_ + 20), 40))
            out.paste(Image.fromarray(np.clip(k * 4, 0, 255).astype(np.uint8)), (i * (W_ + 20), 50 + W_))
            d.text((i * (W_ + 20) + 6, 6), et, font=f, fill=(20, 20, 20))
        fn = C / f'{a.ad}_KESIT_{ad}.png'
        out.save(fn)
        kay[ad] = {'x': x, 'y': y, 'w': W_, 'h': W_}
    (C / f'{a.ad}_KESIT.json').write_text(json.dumps({'ust_satir': '1:1', 'alt_satir': '4x kontrast', 'kutular': kay}, indent=1))
    print(a.ad, kay)


if __name__ == '__main__':
    main()
