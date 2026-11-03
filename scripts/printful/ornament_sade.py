#!/usr/bin/env python3
"""SADE_8 (Merkez / Serdar 3 Kas): beyaz seramik yuzey, 8 renk / doku adayi. Etsy / Printful / Drive yazma yok (mockup ayri is akisi modu).
Duzen: ALTIN_MOTOR ad3aa746 ile birebir (yerlesim_V5, halka T1, yazi P1; ornament_motor.py ORN_DUMP katmani: E, M maskeleri, renk_uyum sonrasi
motor oge katmanlari CC, ic golge ICP). Zemin: duz beyaz #FFFFFF (Serdar 3 Kas karari), murekkepsiz: tum maskeler disinda piksel tam 255.
Tek doku birligi: tum ogeler ayni kaynak dokudan (ana: a114ddb G2 sembol rengi; kucuk ogeler: motor katmani); aday yalniz renk eslemesini degistirir.
Zemin rengi ogeye karismaz (karar 18): dis golge YOK (beyaz zemine murekkep olur), parlaklik dususu beyaz duz zeminde 1.0 (ayni formul).
Ic golge: ad3aa746 ile ayni (oge yari kalinligina oranli).
Metalik (1 altin, 5 gumus/platin, 6 rose gold): renk = altin katmani; Lab'da L aynen, ton acisi ve kroma hedef tona kaydirilir.
Murekkep (2 bronz, 3 mat siyah, 4 grafit, 7 bordo, 8 lacivert): acik zemin kurali (karar 12, P1): luma orani r = L / Lmed(ana) ->
  koyu..ana..acik paleti (ornament_ornek5.bronz_fonk ile ayni egri); kucuk ogeler (yazi, logo, kucuk burc, halka) yalniz koyulasir, acik uc ana ton.
  Bronz = BEIGE bronzu (BRONZ, carpan 1.0; STIL3_SON OLCUM bronz_ana_rgb [84, 54, 14]).
Kapilar: acik zemin KATI kontrast >= 4.5 (karar 14; isim1, isim2, tarih, kucuk_sol, kucuk_sag, sonsuz, halka govdesi); gecmeyen aday uretilir,
etiketi OKUNMAZ. Leke 0, tasma 0, delik ve guvenli daire disi 0, zemin murekkepsiz, yerlesim 20/20/20 ve sembol y 246.
Kullanim: ornament_sade.py --katman PKL --cikti DIR"""
import argparse
import importlib.util
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o4, o3, o1 = al.o5, al.o4, al.o3, al.o1
N, CX, CY = o5.N, o5.CX, o5.CY
lum = o4.lum
KUCUK_OGE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'kucuk_sol', 'kucuk_sag', 'halka')
KAPI_OGE = ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag', 'sonsuz')


def lab(x):
    return cv2.cvtColor((np.clip(x, 0, 255).reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)


def rgb_lab(L):
    return np.clip(cv2.cvtColor(L.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)


HEX = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
# hedef tonlar: kaynak = tahmin / yaygin web renk adlari (olculmus urun degil); raporda belirtilir
ADAY = [
    (1, 'KLASIK_ALTIN', 'metal', None),
    (2, 'KOYU_BRONZ', 'murekkep', o5.BRONZ['ana']),
    (3, 'MAT_SIYAH', 'murekkep', HEX('#1E1E20')),
    (4, 'GRAFIT_GRI', 'murekkep', HEX('#404246')),
    (5, 'GUMUS_PLATIN', 'metal', dict(C=3.0, h=250.0)),            # notr, hafif soguk (tahmin)
    (6, 'ROSE_GOLD', 'metal', HEX('#B76E79')),                       # yaygin "rose gold" web rengi (3. taraf adlandirma)
    (7, 'BORDO', 'murekkep', HEX('#70182A')),
    (8, 'LACIVERT', 'murekkep', HEX('#182656')),
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--katman', required=True); ap.add_argument('--cikti', required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    D = pickle.load(open(a.katman, 'rb'))
    E, M, CC, ICP, govde, um = D['E'], D['M'], D['CC'], D['ICP'], D['govde'], D['um']
    o4.YASAK = o4.yasak_m(); o3.YASAK = o4.YASAK
    # altin oge renkleri (tam tuval): sembol G2, digerleri motor katmani
    ALT = {}
    for ad in E:
        if ad == 'sembol':
            cc = np.zeros((N, N, 3), np.float32); rgb_, a_, x, y = E[ad]; h, w = a_.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = rgb_[ya - y:yb - y, xa - x:xb - x]
        else:
            cc = CC[ad].astype(np.float32)
        ALT[ad] = cc
    ms = M['sembol'] >= 0.9
    Lab_s = lab(ALT['sembol'][ms])
    L_med = float(np.median(lum(ALT['sembol'][ms])))                    # tek doku Lmed (ana sembol cekirdek luma ortancasi)
    a_med, b_med = float(np.median(Lab_s[:, 1])), float(np.median(Lab_s[:, 2]))
    C_alt, h_alt = float(np.hypot(a_med, b_med)), float(np.degrees(np.arctan2(b_med, a_med)) % 360)
    z = np.full((N, N, 3), 255, np.uint8)
    BR = o5.BRONZ
    Lr = float(lum(BR['acik'][None])[0] / lum(BR['ana'][None])[0])     # bronz acik / ana luma orani (murekkep acik ucu)

    def metal(cc, m, hedef):
        sec = m > 0.001
        out = cc.copy()
        if hedef is None:
            return out
        if isinstance(hedef, dict):
            Ct, ht = hedef['C'], hedef['h']
        else:
            lt = lab(hedef[None])[0]; Ct, ht = float(np.hypot(lt[1], lt[2])), float(np.degrees(np.arctan2(lt[2], lt[1])) % 360)
        L_ = lab(cc[sec])
        C = np.hypot(L_[:, 1], L_[:, 2]); h = np.arctan2(L_[:, 2], L_[:, 1]) + np.radians(ht - h_alt)
        C2 = C * (Ct / max(C_alt, 1e-3))
        L_[:, 1], L_[:, 2] = C2 * np.cos(h), C2 * np.sin(h)
        out[sec] = rgb_lab(L_)
        return out

    def murekkep(cc, ad, ana):
        k = BR['koyu'] if np.array_equal(ana, BR['ana']) else ana * 0.6
        c = BR['acik'] if np.array_equal(ana, BR['ana']) else np.clip(ana * Lr, 0, 255)
        r = np.clip(lum(cc) / max(L_med, 1.0), 0.5, 1.5)
        t1 = np.clip((r - 0.5) / 0.5, 0, 1)[..., None]; t2 = np.clip((r - 1.0) / 0.5, 0, 1)[..., None]
        out = np.where(r[..., None] <= 1.0, k + (ana - k) * t1, ana + (c - ana) * t2)
        if ad in KUCUK_OGE:                                             # P1: doku yalniz koyulastirir, acik uc ana ton
            L = lum(out); La = float(lum(ana[None])[0])
            out = out * np.where(L > La, La / np.maximum(L, 1e-3), 1.0)[..., None]
        return out.astype(np.float32)

    def butunlestir(renk):
        f_dus = np.ones((N, N), np.float32)                             # beyaz duz zeminde boya_altin dusus formulu = 1
        out = z.astype(np.float32).copy()
        sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
        for ad in E:
            m = M[ad]; q = ICP[ad]
            ic = cv2.GaussianBlur(np.clip(m - sh(m, q['kayma']), 0, 1), (0, 0), q['sigma']) * m
            cc = renk[ad] * (f_dus * (1 - q['guc'] * ic))[..., None]
            sat = cc.max(2, keepdims=True); cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
            out = out * (1 - m[..., None]) + cc * m[..., None]
        return np.clip(np.round(out), 0, 255).astype(np.uint8)

    tum = np.maximum.reduce([M[k] for k in M])
    disari = tum < 0.002
    R = dict(karar=dict(zemin='duz beyaz #FFFFFF (Serdar 3 Kas, soru yaniti); Printful 900 printfiles kaydi zemin belirtmiyor (fill_mode cover), '
                              'sablon technique sublimation',
                        katman='ornament_motor.py ORN_DUMP (ad3aa746 ile ayni kod ve girdi); ana sembol a114ddb G2, kucuk ogeler motor_gpt 6da763a + renk_uyum',
                        dis_golge='yok (zemin murekkepsiz sarti)', dusus='beyaz duz zeminde 1.0',
                        hedef_ton_kaynak='tahmin / yaygin renk adlari: bronz = BEIGE bronzu (o5.BRONZ), rose gold #B76E79, gumus C 3 h 250, '
                                         'siyah #1E1E20, grafit #404246, bordo #70182A, lacivert #182656'),
             altin_referans=dict(Lmed_luma=round(L_med, 2), C=round(C_alt, 2), h=round(h_alt, 2)), aday={})
    for n, ad_r, tur, hedef in ADAY:
        renk = {ad: (metal(ALT[ad], M[ad], hedef) if tur == 'metal' else murekkep(ALT[ad], ad, hedef)) for ad in E}
        rgb = butunlestir(renk)
        ok = {k: o5.kontrast_yeni(rgb, M[k], 'acik') for k in KAPI_OGE}
        ok['halka_govde'] = o5.kontrast_yeni(rgb, M['halka'] * govde, 'acik')
        ok['sembol_bilgi'] = o5.kontrast_yeni(rgb, M['sembol'], 'acik')
        ok['halka_uclari_2px_alti_bilgi'] = o5.kontrast_yeni(rgb, M['halka'] * um[1], 'acik', cekirdek=0.5)
        kk = {k: v['deger'] for k, v in ok.items() if not k.endswith('_bilgi') and v.get('deger') is not None}
        en_ad = min(kk, key=kk.get)
        gy, gb = o4.goruntu_yasak(rgb, z, M.get('halka'))
        lk = o5.leke_kapisi(M, rgb, None)
        r = dict(tur=tur, kati_kontrast_en_kotu=round(kk[en_ad], 2), en_kotu_oge=en_ad, okunur=bool(kk[en_ad] >= o4.HEDEF), kontrast=ok,
                 goruntu_yasak=gy, leke_a=sum(v['alfa_lt_09'] for k2, v in lk.items() if k2 in o5.LEKE_KAPI_OGE),
                 zemin_murekkepsiz=bool((rgb[disari] == 255).all()), zemin_disi_255_olmayan=int((rgb[disari] != 255).any(1).sum()),
                 bosluk_px=o5.bosluklar(E), sembol_kutu=list(o5.kutu(E, 'sembol')),
                 renk_medyan_rgb={k: [int(v) for v in np.median(rgb[M[k] >= 0.9], 0)] for k in ('sembol', 'isim1', 'kucuk_sol', 'halka')})
        dosya = f'SADE_{n}_{ad_r}_954.png'
        o1.kaydet(rgb, O / dosya)
        r['dosya'] = dosya
        r['kapi'] = dict(leke_0=r['leke_a'] == 0, tasma_ve_yasak_0=sum(gy.values()) == 0, zemin_murekkepsiz=r['zemin_murekkepsiz'],
                         yerlesim_ayni=r['bosluk_px'] == [20, 20, 20] and r['sembol_kutu'][1] == 246)
        r['etiket'] = f'{n} {ad_r}: kati {r["kati_kontrast_en_kotu"]}' + ('' if r['okunur'] else ' OKUNMAZ (uretim adayi degil)')
        R['aday'][str(n)] = r
        print(r['etiket'], '| leke', r['leke_a'], '| yasak', sum(gy.values()), '| zemin', r['zemin_murekkepsiz'], '| en kotu', en_ad,
              {k: v for k, v in kk.items()}, flush=True)
    R['kapi_hepsi'] = all(all(v['kapi'].values()) for v in R['aday'].values())
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI (leke / tasma / zemin / yerlesim)', 'PASS' if R['kapi_hepsi'] else 'FAIL', '| okunur',
          [n for n, v in R['aday'].items() if v['okunur']], flush=True)
    return 0 if R['kapi_hepsi'] else 1


if __name__ == '__main__':
    sys.exit(main())
