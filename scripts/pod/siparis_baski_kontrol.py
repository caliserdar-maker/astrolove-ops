#!/usr/bin/env python3
"""Tek siparis baski dosyasinda Terazi cubugu kontrolu (salt okur; Etsy/Prodigi YOK).
Baski dosyasi (Prodigi'ye giden) ile ayni renk/boy CANCER_LIBRA dosyasi karsilastirilir:
  - konum: kaynak_terazi.bul (CANCER_LIBRA MB 11x14 Terazi sablonu, sag yari, cok olcekli NCC)
  - parcalar: yay (en buyuk bilesen) + alt cubuk (en alttaki bilesen)
  - kayma = cubuk orta x - yay orta x ; bosluk = cubuk ustu - yay alti (px)
Karar: |kayma - kayma_CL| <= ESIK_KAYMA ve |bosluk - bosluk_CL| <= ESIK_BOSLUK ve cubuk ayri bilesen -> PASS (hatali degil).
Cikti: OUT/KONTROL.json + OUT/KARSILASTIRMA.png (Terazi 3x buyutulmus, yay ortasi yesil / cubuk ortasi kirmizi).
Kullanim: siparis_baski_kontrol.py BASKI.jpg CL_AYNI_RENK_BOY.jpg CL_MB_11x14.jpg OUT [--md5 BEKLENEN] [--etiket METIN]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kaynak_terazi as KT  # noqa: E402

ESIK_KAYMA = 3.0
ESIK_BOSLUK = 3.0


def terazi(yol, sablon):
    a = np.asarray(Image.open(yol).convert('RGB')).astype(np.float32)
    kutu, skor = KT.bul(a, sablon)
    x0, y0, x1, y1 = kutu; w, h = x1 - x0, y1 - y0
    X0, Y0 = max(int(x0 - 0.25 * w), 0), max(int(y0 - 0.25 * h), 0)
    X1, Y1 = min(int(x1 + 0.25 * w), a.shape[1]), min(int(y1 + 0.25 * h), a.shape[0])
    P = KT.bilesenler(KT.murekkep(a[Y0:Y1, X0:X1]) > 0.5)
    if not P:
        return {'skor': skor, 'hata': 'murekkep yok'}
    yay = max(P, key=lambda p: p['alan'])
    P = [p for p in P if p['x'][0] >= yay['x'][0] - 0.2 * w and p['x'][1] <= yay['x'][1] + 0.2 * w]
    alt = max(P, key=lambda p: p['y'][1])
    return {'skor': skor, 'bilesen': len(P), 'cubuk_ayri': alt['lab'] != yay['lab'],
            'yay': {'x': [X0 + v for v in yay['x']], 'y': [Y0 + v for v in yay['y']]},
            'cubuk': {'x': [X0 + v for v in alt['x']], 'y': [Y0 + v for v in alt['y']]},
            'yay_orta_x': X0 + yay['orta_x'], 'cubuk_orta_x': X0 + alt['orta_x'],
            'kayma': round(alt['orta_x'] - yay['orta_x'], 1), 'bosluk': int(alt['y'][0] - yay['y'][1]),
            'boyut': list(a.shape[1::-1])}


def kirp(yol, o, etiket):
    im = Image.open(yol).convert('RGB')
    x0 = min(o['yay']['x'][0], o['cubuk']['x'][0]); x1 = max(o['yay']['x'][1], o['cubuk']['x'][1])
    y0, y1 = o['yay']['y'][0], o['cubuk']['y'][1]
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, 0.8 * max(x1 - x0, y1 - y0)
    K = (int(cx - r), int(cy - r), int(cx + r), int(cy + r)); f = 600 / (K[2] - K[0])
    t = im.crop(K).resize((600, 600), Image.LANCZOS); d = ImageDraw.Draw(t)
    for x, renk in ((o['yay_orta_x'], (0, 220, 0)), (o['cubuk_orta_x'], (255, 40, 40))):
        X = (x - K[0]) * f; d.line([(X, 0), (X, 599)], fill=renk, width=2)
    k = Image.new('RGB', (600, 660), (255, 255, 255)); k.paste(t, (0, 60)); d = ImageDraw.Draw(k)
    d.text((6, 6), etiket, fill=(0, 0, 0))
    d.text((6, 26), f"kayma {o['kayma']:+.1f} px | bosluk {o['bosluk']} px | cubuk ayri {o['cubuk_ayri']} | {o['boyut'][0]}x{o['boyut'][1]}",
           fill=(0, 0, 0))
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baski'); ap.add_argument('ref'); ap.add_argument('sablon'); ap.add_argument('out')
    ap.add_argument('--md5', default=''); ap.add_argument('--etiket', default='BASKI')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    md5 = hashlib.md5(Path(a.baski).read_bytes()).hexdigest()
    sablon = KT.sablon_kur(a.sablon)
    B, R = terazi(a.baski, sablon), terazi(a.ref, sablon)
    if 'hata' in B or 'hata' in R:
        sonuc = {'karar': 'OLCULEMEDI', 'baski': B, 'ref': R}
    else:
        dk, db = round(B['kayma'] - R['kayma'], 1), B['bosluk'] - R['bosluk']
        hatali = (not B['cubuk_ayri']) or abs(dk) > ESIK_KAYMA or abs(db) > ESIK_BOSLUK
        sonuc = {'karar': 'HATALI' if hatali else 'DOGRU', 'kayma_farki': dk, 'bosluk_farki': db,
                 'esik': {'kayma': ESIK_KAYMA, 'bosluk': ESIK_BOSLUK}, 'baski': B, 'ref': R}
        k1, k2 = kirp(a.baski, B, a.etiket), kirp(a.ref, R, 'CANCER_LIBRA ayni renk/boy (referans)')
        T = Image.new('RGB', (1220, 700), (255, 255, 255)); T.paste(k1, (0, 40)); T.paste(k2, (620, 40))
        ImageDraw.Draw(T).text((6, 10), f"Terazi karsilastirma: {sonuc['karar']} | kayma farki {dk:+.1f} px (esik {ESIK_KAYMA}) | "
                                        f"bosluk farki {db:+d} px (esik {ESIK_BOSLUK}) | yesil=yay orta, kirmizi=cubuk orta", fill=(0, 0, 0))
        T.save(out / 'KARSILASTIRMA.png')
    sonuc.update({'md5': md5, 'md5_beklenen': a.md5, 'md5_esit': (md5 == a.md5) if a.md5 else None})
    (out / 'KONTROL.json').write_text(json.dumps(sonuc, indent=1, ensure_ascii=False))
    print(f"KARAR {sonuc['karar']} | md5 esit {sonuc['md5_esit']} | kayma farki {sonuc.get('kayma_farki')} | "
          f"bosluk farki {sonuc.get('bosluk_farki')}", flush=True)
    return 0 if sonuc['karar'] != 'OLCULEMEDI' else 2


if __name__ == '__main__':
    sys.exit(main())
