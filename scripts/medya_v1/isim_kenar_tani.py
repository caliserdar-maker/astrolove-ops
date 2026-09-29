#!/usr/bin/env python3
"""SALT OKUR tani (29 Eyl 2026): CI test siparisinde isim_kalinti / isim_kenar FAIL; MB, DB, PW PASS.
Sahte isimli (EMILY / JAMES) ARIES_SCORPIO 11x14 siparisi CI ve DB (kontrol) icin uretilir; PLATES /
musteri klasorune yazma yok. Cikti (Drive --kok): kapi ayrintisi (kalinti koordinatlari, kenar
sayilari, maske / poster / baski boyutlari) + her kalinti ve kesilen harf pikseli cevresinden x6
kirpim (sol: temizlik oncesi, orta: sonrasi, sag: ham koruma maskesi kirmizi)."""
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TEST = {'cift': 'ARIES_SCORPIO', 'boy': '11x14', 'isim1': 'EMILY', 'isim2': 'JAMES',
        'mesaj': 'Written in the Stars'}


def kirpim(once, sonra, P, x, y, r=14, b=6):
    x0, y0 = max(x - r, 0), max(y - r, 0)
    x1, y1 = x + r, y + r
    a = np.clip(once[y0:y1, x0:x1], 0, 255).astype(np.uint8)
    c = np.clip(sonra[y0:y1, x0:x1], 0, 255).astype(np.uint8)
    m = a.copy(); m[P[y0:y1, x0:x1]] = (255, 0, 0)
    s = np.concatenate([a, np.full((a.shape[0], 2, 3), 255, np.uint8), c,
                        np.full((a.shape[0], 2, 3), 255, np.uint8), m], axis=1)
    return Image.fromarray(s).resize((s.shape[1] * b, s.shape[0] * b), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    d = sd.W / '_isim_kenar_tani'; d.mkdir(parents=True, exist_ok=True)
    rapor = {}
    asil = sd.isim_bandi_temizle
    for renk in ('CHAMPAGNE_IVORY', 'DEEP_BLACK'):
        kay = {}

        def sar(out, yeni, olcum, ham=False):
            o2, t = asil(out, yeni, olcum, ham=ham)
            kay.update({'once': out, 'sonra': o2, 'yeni': yeni, 'ham': ham, 'olcum': olcum})
            return o2, t
        sd.isim_bandi_temizle = sar
        x = sd.normalize({'cift': TEST['cift'], 'renk': renk, 'boy': TEST['boy'], 'urun': 'pod',
                          'isim1': TEST['isim1'], 'isim2': TEST['isim2'], 'mesaj': TEST['mesaj']})
        x['receipt'] = f'TANI_{renk}'
        x['sayfa'] = no[TEST['cift']]
        yol = sd.pod_kaynak(TEST['cift'], renk, TEST['boy'])
        with Image.open(yol) as im:
            x['hedef_px'] = list(im.size)
        is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
        sd._TANI = {}
        s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
        sd.isim_bandi_temizle = asil
        T = sd._TANI
        Y, ham = T['koruma']
        H, Wd = kay['once'].shape[:2]
        Pm = sd._yeni_tam(Y, (Wd, H), ham=ham)
        r = {'kapilar': s.get('kapilar'), 'isim_kalinti': s.get('isim_kalinti_kapisi'),
             'isim_kenar': s.get('isim_kenar_kapisi'),
             'boyut': {'ham_maske': list(np.asarray(Y).shape), 'yeni_genis': list(np.asarray(T['yeni']).shape),
                       'poster': list(T['poster'].size), 'baski': [Wd, H], 'ham': ham},
             'temizlik': {q: v for q, v in (s.get('isim_bandi_temizligi') or {}).items() if q != 'kenar'}}
        # kesilen harf pikselleri (kenar kapisinin kendisi, yeniden)
        import cv2
        t = r['temizlik']
        if t.get('satir'):
            r0, r1 = t['satir']; c0, c1 = t['sutun']
            A = kay['once'][r0:r1, c0:c1]; B = kay['sonra'][r0:r1, c0:c1]; P = Pm[r0:r1, c0:c1]
            deg = np.abs(B - A).max(axis=2) > 0.5
            L = A @ np.array([0.299, 0.587, 0.114], np.float32)
            dL = np.abs(L - sd._yerel_zemin(L, Wd / 2400.0))
            esik = (r['isim_kenar'] or {}).get('guclu_esik', 40.0)
            halka = (cv2.dilate(P.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~P
            ys, xs = np.nonzero(deg & halka & (dL > esik))
            r['kesilen_ornek'] = [[int(xx + c0), int(yy + r0), round(float(dL[yy, xx]), 1),
                                   [int(v) for v in A[yy, xx]]] for yy, xx in list(zip(ys, xs))[:40]]
            # halkadaki maksimum dL dagilimi: koruma harfi ne kadar kapsiyor
            r['halka_dL_p99'] = round(float(np.percentile(dL[halka], 99)), 1) if halka.any() else None
            noktalar = [(z['x'] + z['w'] // 2, z['y'] + z['h'] // 2)
                        for z in (r['isim_kalinti'] or {}).get('kalintilar') or []][:6]
            noktalar += [(q[0], q[1]) for q in r['kesilen_ornek'][:6]]
            for i, (px, py) in enumerate(noktalar):
                kirpim(kay['once'], kay['sonra'], Pm, px, py).save(d / f'{renk}_{i:02d}_{px}_{py}.png')
        rapor[renk] = r
        print(renk, json.dumps({q: r.get(q) for q in ('kapilar', 'boyut', 'halka_dL_p99')}, default=str), flush=True)
        print('  kalinti', json.dumps((r['isim_kalinti'] or {}).get('kalintilar'), default=str), flush=True)
        print('  kenar', json.dumps(r['isim_kenar'], default=str), flush=True)
        print('  kesilen', json.dumps(r.get('kesilen_ornek', [])[:12]), flush=True)
    (d / 'ISIM_KENAR_TANI.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(d), a.kok, timeout=1800)


if __name__ == '__main__':
    main()
