#!/usr/bin/env python3
"""DOKU_AI ek girdi sayfalari, 2. tur (Serdar 4 Eki):
  PLAKA_1R / PLAKA_2R : 175c4f0 PLAKA_1/2 ile ayni duzen ve olcek; tek fark kose referansi = onayli Canva harfleri
                        (ISIM_1 'A' + ISIM_2 v2 'R', cila sonrasi; sekil vektor maskeden, doku Canva'dan, 24x36 olcek).
                        ISIM_1 sayfasinda R yok (A-L); R onayli ISIM_2 v2 sayfasindan.
  KUCUK_1A / KUCUK_1B : 175c4f0 KUCUK_1 olcekleri, sayfa basina 3 sembol, tek satir, dar sayfa (pay PAY px).
  CEMBER_UST/SOL/SAG/UC : HALKA_24x36 (1:1) aci dilimleri, komsu dilimler en az %15 ortusur; JSON'da aci araligi
                        ve merkeze gore kutu. Aci: merkezden, saga 0, yukari 90 (derece, saat yonu tersi).
Kose referansi KUCUK / CEMBER'de orijinal AQUARIUS_ARIES (doku_ai_sayfa.referans).

Kullanim: doku_ai_ek_sayfa_r.py --girdi GIRDI_DIR --sayfa-json DIR --isim1 ISIM_1.npz --isim2 ISIM_2.npz
          --sym DIR --referans main_aquarius_aries_gold.png --cikti DIR
"""
import argparse, hashlib, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_ai_sayfa as das                                          # noqa: E402
import doku_ai_ek_sayfa as dek                                       # noqa: E402

Image.MAX_IMAGE_PIXELS = None
PAY = 30
REF = (640, 580)
# halka dilimleri: u = (aci - SAG_UC) mod 360, 0 = sag uc, artan = saat yonu tersi (yukari, sola)
DILIM = {'CEMBER_SAG': (0, 95), 'CEMBER_UST': (75, 195), 'CEMBER_SOL': (175, 238), 'CEMBER_UC': (218, 268)}


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def kaydet(C, ad, rgb, j):
    p = C / f'DOKU_AI_{ad}.png'
    Image.fromarray(np.clip(np.round(rgb), 0, 255).astype(np.uint8)).save(p, optimize=True)
    j |= {'dosya': p.name, 'sha256': sha(p), 'olcek': '24x36 baski, 300 dpi, 1:1'}
    (C / f'DOKU_AI_{ad}.json').write_text(json.dumps(j, ensure_ascii=False, indent=1))
    return {'sayfa': ad, 'boyut': j['boyut']}


def glif_kes(npz, sayfa_json, k):
    """cila sonrasi glif (doku x alfa, siyah zemin), murekkep kutusu + 12 px."""
    z = np.load(npz); t = z['t1'].astype(np.float32); A = z['O'].astype(np.float32) / 255
    j = json.loads(Path(sayfa_json).read_text())
    x0, y0, x1, y1 = [g['hucre'] for g in j['glifler'] if g['karakter'] == k][0]
    a = A[y0:y1, x0:x1]; ys, xs = np.nonzero(a > 0)
    a0, a1, b0, b1 = ys.min() - 12, ys.max() + 13, xs.min() - 12, xs.max() + 13
    return (t[y0:y1, x0:x1] * a[..., None])[a0:a1, b0:b1]


def plaka_r(a, C):
    out = []
    A = glif_kes(a.isim1, Path(a.sayfa_json) / 'DOKU_AI_ISIM_1.json', 'A')
    R = glif_kes(a.isim2, Path(a.sayfa_json) / 'DOKU_AI_ISIM_2.json', 'R')
    h = max(A.shape[0], R.shape[0]); w = A.shape[1] + R.shape[1] + 3 * PAY
    for ad in ('PLAKA_1', 'PLAKA_2'):
        j = json.loads((Path(a.girdi) / f'DOKU_AI_{ad}.json').read_text())
        P = np.asarray(Image.open(Path(a.girdi) / f'DOKU_AI_{ad}.png').convert('RGB'), np.float32)
        x0, y0, x1, y1 = j['referans_kutu']
        P[y0:y1, x0:x1] = 0                                          # eski referans (AQUARIUS_ARIES) silinir
        rk = [0, 0, w, h + 2 * PAY]
        for o in j['ogeler']:
            k = o['kutu']
            if not (k[0] >= rk[2] or k[2] <= rk[0] or k[1] >= rk[3] or k[3] <= rk[1]):
                sys.exit(f'FAIL: {ad} referans kutusu {o["oge"]} ile cakisiyor')
        y = PAY + (h - A.shape[0]); P[y:y + A.shape[0], PAY:PAY + A.shape[1]] = A
        y = PAY + (h - R.shape[0]); x = 2 * PAY + A.shape[1]; P[y:y + R.shape[0], x:x + R.shape[1]] = R
        j = {k_: v for k_, v in j.items() if k_ not in ('dosya', 'sha256')}
        j |= {'tur': 'plaka_r', 'kaynak_sayfa': f'DOKU_AI_{ad}.png (175c4f0)', 'referans_kutu': rk,
              'referans': 'onayli Canva harfleri, cila sonrasi: A = ISIM_1 (DOKU_AI_ISIM_1_CANVA.jpg), '
                          'R = ISIM_2 v2 (DOKU_AI_ISIM_2_CANVA_v2.jpg); sekil vektor maske, 24x36 olcek'}
        out.append(kaydet(C, ad + 'R', P, j))
    return out


def kucuk(a, C):
    j1 = json.loads((Path(a.girdi) / 'DOKU_AI_KUCUK_1.json').read_text())
    olc = {o['oge']: o for o in j1['ogeler']}
    out = []
    for ad, burclar in (('KUCUK_1A', ['AQUARIUS', 'ARIES', 'CANCER']), ('KUCUK_1B', ['CAPRICORN', 'GEMINI', 'LEO'])):
        ms = []
        for b in burclar:
            o = olc[b]; f = Path(a.sym) / o['kaynak']
            if sha(f) != o['sha256']:
                sys.exit(f'FAIL: {f} sha 175c4f0 ile ayni degil')
            m, k = dek.maske(f, o['olcek'])
            ms.append((b, m, {kk: o[kk] for kk in ('kaynak', 'sha256', 'olcek', 'olcek_kaynagi')} | {'kaynak_kirp': k}))
        H = max(max(m.shape[0] for _, m, _ in ms) + 2 * PAY, REF[1])
        W = REF[0] + PAY + sum(m.shape[1] + PAY for _, m, _ in ms)
        P = np.zeros((H, W, 3), np.float32)
        P[:REF[1], :REF[0]] = das.referans(a.referans, *REF)
        x = REF[0] + PAY; kay = []
        for b, m, bil in ms:
            y = (H - m.shape[0]) // 2
            P[y:y + m.shape[0], x:x + m.shape[1]] = m[..., None]
            kay.append({'oge': b, 'kutu': [x, y, x + m.shape[1], y + m.shape[0]]} | bil)
            x += m.shape[1] + PAY
        out.append(kaydet(C, ad, P, {'tur': 'kucuk', 'boyut': [W, H], 'referans_kutu': [0, 0, *REF],
                                     'referans': Path(a.referans).name, 'ogeler': kay}))
    return out


def halka_geo(h):
    ys, xs = np.nonzero(h > 128)
    M = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; b = (xs ** 2 + ys ** 2).astype(np.float64)
    cx, cy, c = np.linalg.lstsq(M, b, rcond=None)[0]
    r = float(np.sqrt(c + cx ** 2 + cy ** 2))
    th = np.degrees(np.arctan2(-(ys - cy), xs - cx)) % 360
    hs = np.histogram(th, bins=360, range=(0, 360))[0]
    bos = np.nonzero(hs == 0)[0]
    return float(cx), float(cy), r, int(bos.max()) + 1, int(bos.min())    # sag uc (bosluk sonu), sol uc


def cember(a, C):
    hf = KOK / 'varlik' / 'halka' / 'HALKA_24x36.png'
    h = np.asarray(Image.open(hf).convert('L'), np.float32)
    cx, cy, r, sag_uc, sol_uc = halka_geo(h)
    yy, xx = np.mgrid[0:h.shape[0], 0:h.shape[1]]
    u = (np.degrees(np.arctan2(-(yy - cy), xx - cx)) - sag_uc) % 360
    out = []; pay = 60
    for ad, (u0, u1) in DILIM.items():
        sec = (u >= u0) & (u < u1) & (h > 0)
        ys, xs = np.nonzero(sec)
        x0, y0, x1, y1 = xs.min() - pay, ys.min() - pay, xs.max() + 1 + pay, ys.max() + 1 + pay
        m = np.where(sec, h, 0)[y0:y1, x0:x1]
        # referans sol ustte; halkaya degiyorsa uste bant eklenir
        ek = 0 if not (m[:REF[1] + PAY, :REF[0] + PAY] > 0).any() else REF[1] + PAY
        W, H = max(m.shape[1], REF[0] + PAY), m.shape[0] + ek
        P = np.zeros((H, W, 3), np.float32)
        P[ek:ek + m.shape[0], :m.shape[1]] = m[..., None]
        P[:REF[1], :REF[0]] = das.referans(a.referans, *REF)
        aci = [round((sag_uc + u0) % 360, 1), round((sag_uc + u1) % 360, 1)]
        out.append(kaydet(C, ad, P, {
            'tur': 'cember_dilim', 'boyut': [W, H], 'referans_kutu': [0, 0, *REF], 'referans': Path(a.referans).name,
            'ogeler': [{'oge': ad, 'kutu': [0, ek, m.shape[1], ek + m.shape[0]], 'kaynak': hf.name, 'sha256': sha(hf),
                        'olcek': 1.0, 'kaynak_kirp': [int(x0), int(y0), int(x1), int(y1)]}],
            'halka': {'merkez': [round(cx, 2), round(cy, 2)], 'yaricap': round(r, 2), 'sag_uc_aci': sag_uc, 'sol_uc_aci': sol_uc,
                      'aci_araligi': aci, 'u_araligi': [u0, u1],
                      'aci_tanimi': 'merkezden, saga 0, yukari 90 derece (saat yonu tersi); u = (aci - sag_uc) mod 360',
                      'merkeze_gore_kutu': [round(x0 - cx, 1), round(y0 - cy, 1), round(x1 - cx, 1), round(y1 - cy, 1)],
                      'sayfa_kaydirma': [int(x0), int(y0) - ek]}}))
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ('girdi', 'sayfa-json', 'isim1', 'isim2', 'sym', 'referans', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    print(json.dumps(plaka_r(a, C) + kucuk(a, C) + cember(a, C), ensure_ascii=False))


if __name__ == '__main__':
    main()
