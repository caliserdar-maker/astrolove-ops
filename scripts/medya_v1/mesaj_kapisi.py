#!/usr/bin/env python3
"""GOREV_0020: mesaj (tagline) murekkebi kapisi + koyu murekkep duzeltmesi.

KOK NEDEN: isimler `pilot12.altin_isim` ile profili dogrudan boyar; tagline ise
`pilot12.tagline_plaka` (satir 364) icinde `pilot7.kuyruk_duzlestir`'den gecer.
Oradaki kural (pilot7.py:103-105) `L >= L.max() * 0.80` ALTIN (acik) murekkep
icindir: koyu murekkepte (CI, WP) L.max() profilin EN SOLUK satiridir; son
"iyi" satir o soluk satir olur ve altindaki butun profil ona duzlenir.
DUZELTME: koyu murekkepte (profil medyan L < KOYU_L) iyi satir = medyandan
cok acik olmayan satir. Altin murekkepte (MB/DB/PW) eski fonksiyon aynen kosar.

KAPI: poster uzerinde isim bandi ve mesaj bandinin murekkep rengi (Lab) olculur.
  dE    = |Lab_mesaj - Lab_isim|                    <= DE_ESIK
  oran  = |L_mesaj - L_zemin| / |L_isim - L_zemin|  >= KONTRAST_ESIK
Esikler dogru orneklerden olculur (--kalibre); env MESAJ_ESIK="dE,oran" ezer.
"""
import json, os, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
KOYU_L = 128.0                      # altin murekkep L ~190, CI ~70, WP ~97
DE_ESIK, KONTRAST_ESIK = 8.0, 0.75  # gecici (yerel onayli kirpimlar); --kalibre olcer
if os.environ.get('MESAJ_ESIK'):
    DE_ESIK, KONTRAST_ESIK = map(float, os.environ['MESAJ_ESIK'].split(','))


def duzeltme_uygula(pilot12):
    eski = getattr(pilot12.kuyruk_duzlestir, 'eski', pilot12.kuyruk_duzlestir)

    def kuyruk_duzlestir(prof, oran=0.80):
        p = np.asarray(prof, np.float32).copy()
        L = p @ LUMA
        med = float(np.median(L))
        if med >= KOYU_L:
            return eski(prof, oran)
        ok = np.nonzero(L <= med / oran)[0]
        p[ok[-1] + 1:] = p[ok[-1]]
        return p, int(ok[-1])
    kuyruk_duzlestir.eski = eski
    pilot12.kuyruk_duzlestir = kuyruk_duzlestir
    return eski


def _lab(rgb):
    u = np.clip(np.asarray(rgb, np.float32).reshape(1, -1, 3), 0, 255).astype(np.uint8)
    return cv2.cvtColor(u, cv2.COLOR_RGB2LAB)[0].astype(np.float32) * [100 / 255., 1, 1] - [0, 128, 128]


def murekkep(a, bant, k=1.0):
    """Payli bantta zemin (medyan) ve murekkep cekirdegi (medyan RGB)."""
    y0, y1 = bant[0] * k, bant[1] * k
    p = 0.5 * (y1 - y0)
    W = a.shape[1]
    kes = a[max(int(y0 - p), 0):int(y1 + p), int(W * 0.05):int(W * 0.95)].astype(np.float32)
    z = np.median(kes.reshape(-1, 3), 0)
    d = np.abs(kes - z).max(2)
    m = d > max(40.0, 0.5 * float(np.percentile(d, 99.5)))
    c = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    c = c if c.sum() >= 50 else m
    return z, (np.median(kes[c], 0) if c.any() else z), int(c.sum())


def kapi(a, isim_bant, tag_bant, k=1.0):
    a = np.asarray(a.convert('RGB') if hasattr(a, 'convert') else a)
    z, ci, ni = murekkep(a, isim_bant, k)
    zt, ct, nt = murekkep(a, tag_bant, k)
    L = _lab(np.stack([ci, ct, z]))
    dE = float(np.linalg.norm(L[0] - L[1]))
    oran = abs(L[1, 0] - L[2, 0]) / max(abs(L[0, 0] - L[2, 0]), 1e-3)
    return {'gecti': bool(dE <= DE_ESIK and oran >= KONTRAST_ESIK and nt > 0),
            'dE': round(dE, 1), 'kontrast_orani': round(float(oran), 2),
            'isim_rgb': [int(v) for v in ci], 'mesaj_rgb': [int(v) for v in ct],
            'zemin_rgb': [int(v) for v in z], 'esik': [DE_ESIK, KONTRAST_ESIK]}


# ------------------------------------------------------------ Actions kosusu
def _bir(arg):
    """Tek (renk, oran): o oranin her boyu; orijinal + eski kod + yeni kod."""
    import siparis_dosyasi as sd
    renk, oran, boylar, sayfa, bitis = arg
    ed = sd.RENK_ED[renk]
    P_ed = sd.EdisyonPoster()
    P_blue = sd.BluePoster() if ed == 'blue' else None
    eski = duzeltme_uygula(P_ed.p12)
    yeni = P_ed.p12.kuyruk_duzlestir
    out = []
    for boy in boylar:
        r = {'renk': renk, 'boy': boy}
        if time.time() > bitis:
            out.append({**r, 'hata': 'OLCULMEDI (sure)'}); continue
        try:
            yol = sd.pod_kaynak('CANCER_LIBRA', renk, boy)
            sd.olcek_kur(2400)
            o, _, _ = P_ed.olc(yol, P_ed.plate(ed, oran, boy))
            ib, tb = o['isim_bant'], o['tag_bant']
            ref = P_ed.p11.norm(Image.open(yol).convert('RGB'))[0]
            r['orijinal'] = kapi(ref, ib, tb)
            kb = yol.read_bytes()
            for ad, f in (('eski', eski), ('yeni', yeni)):
                if ed == 'blue' and ad == 'eski':
                    continue                           # altin: iki kod ayni
                P_ed.p12.kuyruk_duzlestir = f
                p, bi, _ = sd.render_et(ed, oran, sayfa, kb, ('EMMA', 'NOAH'),
                                        'Written in the stars', P_blue, P_ed,
                                        'CANCER_LIBRA', ref_boy=boy, hedef_en=2400, boy=boy)
                r[ad] = kapi(p, bi['olcum']['isim_bant'], bi['olcum']['tag_bant'],
                             p.width / 2400.0) if p is not None else {'hata': bi.get('durum')}
            P_ed.p12.kuyruk_duzlestir = yeni
            yol.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['hata'] = f'{type(e).__name__}: {str(e)[:120]}'
        out.append(r)
        print('SATIR', json.dumps(r, ensure_ascii=False), flush=True)
    return out


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import siparis_dosyasi as sd
    from multiprocessing import get_context
    T = time.time()
    sd.kisisel_hazirla()
    sd.PLATE_EK = '_CANVA'                    # GOREV_0019 ornekleriyle ayni plate kumesi
    no, _ = sd.sayfa_no_tablosu()
    ornek = eski_ornekler(sd)
    # ACIL: CI ve WP ornekleri yeni kodla yeniden (kapi PASS degilse yazilmaz)
    import subprocess
    p = subprocess.run([sys.executable, 'scripts/medya_v1/chatgpt_ornek.py',
                        'CHAMPAGNE_IVORY', 'WARM_PARCHMENT'], capture_output=True, text=True)
    yeni_ornek = [json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')]
    print('\n'.join(x for x in p.stdout.splitlines()[-6:]), flush=True)
    bitis = T + 60 * float(os.environ.get('MESAJ_DAKIKA', '34'))
    isler = [(r, o, [b for b, v in sd.BOY.items() if v[0] == o], no['CANCER_LIBRA'], bitis)
             for r in sd.RENKLER for o in ('4x5', '3x4', '2x3', '11x14', 'A')]
    t0 = time.time(); sonuc = []
    with get_context('fork').Pool(processes=4) as h:
        for i, s in enumerate(h.imap_unordered(_bir, isler), 1):
            sonuc += s
            g = time.time() - t0
            print(f'ETA {i}/{len(isler)} gecen {g/60:.1f} dk kalan ~{g/i*(len(isler)-i)/60:.1f} dk '
                  f'%{100*i//len(isler)}', flush=True)
    # Kalibrasyon: dogru ornekler = Canva orijinalleri (5 edisyon) + onayli MB/DB/PW ornekleri
    dogru = [r['orijinal'] for r in sonuc if 'dE' in r.get('orijinal', {})] + \
            [v for k, v in ornek.items() if k != 'CHAMPAGNE_IVORY' and 'dE' in v] or \
            [{'dE': DE_ESIK / 1.25, 'kontrast_orani': KONTRAST_ESIK / 0.8}]
    de = round(max(v['dE'] for v in dogru) * 1.25, 1)
    ko = round(min(v['kontrast_orani'] for v in dogru) * 0.8, 2)
    print(f'KALIBRE n={len(dogru)} dE_max={max(v["dE"] for v in dogru)} '
          f'oran_min={min(v["kontrast_orani"] for v in dogru)} -> ESIK dE<={de} oran>={ko}')
    for v in [x for r in sonuc for x in r.values() if isinstance(x, dict)] + list(ornek.values()):
        if 'dE' in v:
            v['gecti'], v['esik'] = bool(v['dE'] <= de and v['kontrast_orani'] >= ko), [de, ko]
    for x in yeni_ornek:
        v = x.get('mesaj_kapisi') or {}
        if 'dE' in v:
            v['gecti'] = bool(v['dE'] <= de and v['kontrast_orani'] >= ko)
        print('YENI_ORNEK', json.dumps(x, ensure_ascii=False))
    for k, v in ornek.items():
        print('ESKI_ORNEK', k, json.dumps(v))
    Path('_siparis').mkdir(exist_ok=True)
    yol = Path('_siparis/MESAJ_KAPISI_TABLO.json')
    yol.write_text(json.dumps({'esik': [de, ko], 'eski_ornekler': ornek,
                               'yeni_ornekler': yeni_ornek, 'tablo': sonuc},
                              ensure_ascii=False, indent=1))
    sd.rc('copyto', str(yol), f'{sd.SIP}/MESAJ_KAPISI/MESAJ_KAPISI_TABLO.json')
    for r in sonuc:
        print(f"{r['renk'][:4]} {r['boy']:6s}", *[
            f"{a}={r[a].get('dE')}/{r[a].get('kontrast_orani')}/{'P' if r[a].get('gecti') else 'F'}"
            for a in ('orijinal', 'eski', 'yeni') if a in r], r.get('hata', ''))


def eski_ornekler(sd):
    """Drive'daki mevcut CL_EMMA_NOAH_<RENK>.jpg ornekleri (8x10) kapidan gecer."""
    P = sd.EdisyonPoster(); out = {}
    for renk in ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY'):
        try:
            yol = Path(f'_siparis/eski_{renk}.jpg')
            sd.rc('copyto', f'gdrive:ASTROLOVE/TEMP/CHATGPT_ORNEK/POSTER/CL_EMMA_NOAH_{renk}.jpg', str(yol))
            sd.olcek_kur(2400)
            o, _, _ = P.olc(yol, P.plate(sd.RENK_ED[renk], '4x5', '8x10'))
            out[renk] = kapi(Image.open(yol), o['isim_bant'], o['tag_bant'])
        except BaseException as e:                                # noqa: BLE001
            out[renk] = {'hata': f'{type(e).__name__}: {str(e)[:120]}'}
    return out

if __name__ == '__main__':
    main()
