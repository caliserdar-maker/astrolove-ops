#!/usr/bin/env python3
"""WARM_PARCHMENT bakir referansi (Serdar 3 Eki: bakir = eski sistem wp_bakir rengi ve dokusu). Referans: Test 5
WP 11x14 sayfasi (siparis-dijital 9000000005, kilitli wp_bakir hatti; Serdar onayli bakir). Olcum, Test 5'in kendi
kagidina (ham PLATES/<plate>.png) gore yapilir; sonuc sabitler JSON'una 'bakir' olarak yazilir. Konum/olcek yok.

Oge gruplari (sabitlerdeki bantlar): buyuk_sembol, kucuk_sembol, isim (isim + sonsuz), mesaj. Test 5'te mesaj
bandinin ustundeki kaymis ikinci kopya (bilinen hata) olcume girmez: her grup yalniz sabit bandiyla en cok
kesisen Test 5 bandindan olculur. Test 5'te daire de bakira basildigi icin buyuk sembol, sembol kutusu (+-30 px) ile
sinirlanir; daire ayri olculur (asagida).
- rgb, Lk, cv: olc.renk_olc ile ayni tanim (dolu murekkep ortalamasi, murekkep gucu ortancasi, golge genligi).
- kabartma: kilitli wp_bakir.kabartma_olc (isim + mesaj satirlari; eski hatta kabartma yalniz bunlara uygulanir).
- daire: Test 5 halka bakiri (Serdar 3 Eki: halka da bakir), motor halka katmani geometrisiyle.

Kullanim: bakir_olc.py --kaynak DIR --sabit motor/sabitler/X.json
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
sys.path.insert(0, str(KOK))
import wp_bakir as wb                                                 # noqa: E402
from olc import murekkep, bantlar, renk_olc                          # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def oku(f):
    return np.asarray(Image.open(f).convert('RGB'), np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    a = ap.parse_args()
    K = Path(a.kaynak)
    Z = json.loads(Path(a.sabit).read_text())
    T = oku(K / 'test5_WP_11x14.jpeg')
    P = oku(K / 'plates' / f"{Z['plate']}.png")                        # Test 5'in kagidi (ham plate)
    m, ink = murekkep(T, P)
    tb = bantlar(ink)
    R = {'referans': 'TEMP/SIPARIS_ISIM/DIJITAL/9000000005/AstroLoveArt_Scorpio_Virgo_Warm_Parchment.pdf sayfa 4 '
                     '(11x14, gomulu goruntu birebir)', 'test5_bantlar': tb, 'ogeler': {}}
    for ad, (y0, y1) in Z['bantlar'].items():
        kes = [(min(y1, b[1]) - max(y0, b[0]), b) for b in tb]
        ov, b = max(kes)
        if ov <= 0:
            sys.exit(f'FAIL: Test 5 sayfasinda {ad} bandi bulunamadi')
        mm = np.zeros_like(ink); mm[b[0]:b[1]] = ink[b[0]:b[1]]
        if ad == 'buyuk_sembol':                                       # Test 5'te daire de bakir: sembol kutusu
            x0, y0_, x1, y1_ = Z['buyuk_sembol']['kutu']
            kut = np.zeros_like(ink); kut[y0_ - 30:y1_ + 30, x0 - 30:x1 + 30] = True
            mm &= kut
        rgb, n, Lk, cv = renk_olc(T, m, mm)
        R['ogeler'][ad] = {'bant': b, 'rgb': rgb, 'dolu_px': n, 'Lk': Lk, 'cv': cv}
    # kabartma: isim + mesaj satirlari, Test 5'in kendi glif alfasi (murekkep gucu / ortanca, 0-1)
    sat = np.zeros(T.shape[0], bool)
    for ad in ('isim', 'mesaj'):
        y0, y1 = R['ogeler'][ad]['bant']
        sat[y0:y1] = True
    A = np.zeros_like(m)
    for ad in ('isim', 'mesaj'):
        y0, y1 = R['ogeler'][ad]['bant']
        A[y0:y1] = np.clip(m[y0:y1] / R['ogeler'][ad]['Lk'], 0, 1) * ink[y0:y1]
    R['kabartma'] = wb.kabartma_olc(A, T, P, sat, T.shape[1] / 2400.0)
    # halka (daire): Test 5'te bakir. Geometri motor halka katmani (alfa >= 0.9 cekirdek); kagit = ham plate'ten
    # kilitli wp_bakir.kagit_tabani ile halka cikarilmis kagit (m = kagit - Test 5 lumasi)
    if 'halka' in Z:
        al = np.asarray(Image.open(KOK.parent / Z['halka']['dosya']), np.float32) / 255.0
        daire = al > 0.02
        Pk, _ = wb.kagit_tabani(P, daire)
        md = np.clip((Pk - T) @ wb.LUMA, 0, None)
        ce = al >= 0.9
        Lk = float(np.median(md[ce]))
        dolu = ce & (md >= 0.9 * Lk)
        R['ogeler']['daire'] = {'rgb': [round(float(x), 1) for x in T[dolu].mean(0)], 'dolu_px': int(dolu.sum()),
                                'Lk': round(Lk, 1), 'cv': round(float(md[ce].std() / max(np.median(md[ce]), 1)), 4),
                                'olcum': 'halka katmani alfa >= 0.9; kagit = kagit_tabani(ham plate)'}
    Z['bakir'] = R
    Path(a.sabit).write_text(json.dumps(Z, indent=1, ensure_ascii=False))
    print(json.dumps(R, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
