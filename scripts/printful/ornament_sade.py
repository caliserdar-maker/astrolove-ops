#!/usr/bin/env python3
"""SADE_8 (Merkez / Serdar 3 Kas): beyaz seramik yuzey, 8 renk / doku adayi. Etsy / Printful / Drive yazma yok (mockup ayri is akisi modu).
Duzen: ALTIN_MOTOR deneme 4 (e5412718, Serdar kabul) ile birebir (yerlesim_V5, halka T1, yazi P1; ornament_motor.py ORN_DUMP katmani: E, M maskeleri,
renk_uyum sonrasi motor oge katmanlari CC, ic golge ICP: guc 0.35, genislik oge yari kalinligina oranli).
Zemin: SEFFAF PNG (alfa 0; Merkez 3 Kas karar A). Yalniz ogeler basilir; mockup beyaz seramik uzerinde.
Tek doku birligi: tum ogeler ayni kaynak dokudan (ana: a114ddb G2 sembol rengi; kucuk ogeler: motor katmani); aday yalniz renk eslemesini degistirir.
Zemin rengi ogeye karismaz (karar 18): dis golge YOK, parlaklik dususu YOK (beyaz duz zeminde formul 1.0).
Ton adaylari (1, 5, 6; eski adi "metalik"): sublimasyonda metalik murekkep yok, baski DUZ renktir; adlar ALTIN_TONU / GUMUS_TONU / ROSE_TONU.
  Renk = altin katmani; Lab'da L aynen, ton acisi ve kroma hedefe; gamut disi pikselde L ve ton sabit, kroma kuculur (kanal kirpmasi yok).
Murekkep (2 bronz, 3 mat siyah, 4 grafit, 7 bordo, 8 lacivert): acik zemin kurali (karar 12, P1): luma orani r = L / Lmed(ana) ->
  koyu..ana..acik paleti (ornament_ornek5.bronz_fonk ile ayni egri); kucuk ogeler yalniz koyulasir, acik uc ana ton.
  Bronz = BEIGE bronz PALETI (BRONZ, carpan 1.0). Not: BEIGE kucuk ogeleri duz model rengiyle cizilmisti; burada motor dokusu (tek doku birligi).
Kapilar (renk beyaz seramik uzerinde, alfa ile birlestirilerek olculur): acik zemin KATI kontrast >= 4.5 (karar 14; isim1, isim2, tarih,
kucuk_sol, kucuk_sag, sonsuz, halka govdesi, halka uclari >= 2 px); gecmeyen aday uretilir, etiketi OKUNMAZ. Ana sembol kati degeri bilgi.
Leke 0, tasma 0, delik ve guvenli daire disi 0, zemin seffaf (maske disi alfa 0), yerlesim 20/20/20 ve sembol y 246.
Kullanim: ornament_sade.py --katman PKL --cikti DIR"""
import argparse
import hashlib
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


def lab_rgb_ham(L):
    """Lab (D65) -> sRGB 0-1, KIRPMASIZ (cv2.COLOR_Lab2RGB gamut disini sessizce [0, 1]'e kirpiyor; inceleme bulgusu)."""
    L = np.asarray(L, np.float64).reshape(-1, 3)
    fy = (L[:, 0] + 16) / 116; fx = fy + L[:, 1] / 500; fz = fy - L[:, 2] / 200
    d = 6 / 29
    finv = lambda t: np.where(t > d, t ** 3, 3 * d * d * (t - 4 / 29))
    X, Y, Z = 0.950456 * finv(fx), finv(fy), 1.088754 * finv(fz)
    r = 3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    g = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    b = 0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z
    lin = np.stack([r, g, b], 1)
    s_ = np.sign(lin); v = np.abs(lin)
    return (s_ * np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)).astype(np.float32)


def gamut_kroma(L_):
    """gamut disi pikselde L ve ton sabit, kroma ikili aramayla kuculur (12 adim); doner (rgb 0-255, kuculen piksel sayisi)."""
    r = lab_rgb_ham(L_)
    dis = ((r < -1e-4) | (r > 1 + 1e-4)).any(1)
    n = int(dis.sum())
    if n:
        lo, hi = np.zeros(n, np.float32), np.ones(n, np.float32)
        base = L_[dis].copy()
        for _ in range(12):
            mid = (lo + hi) / 2
            t = base.copy(); t[:, 1:] *= mid[:, None]
            ok = ~(((lab_rgb_ham(t) < -1e-4) | (lab_rgb_ham(t) > 1 + 1e-4)).any(1))
            lo = np.where(ok, mid, lo); hi = np.where(ok, hi, mid)
        t = base.copy(); t[:, 1:] *= lo[:, None]
        r[dis] = lab_rgb_ham(t)
    return np.clip(r, 0, 1) * 255, n


HEX = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
# hedef tonlar: kaynak = tahmin / yaygin renk adlari (olculmus urun degil); raporda belirtilir
ADAY = [
    (1, 'ALTIN_TONU', 'ton', None),
    (2, 'KOYU_BRONZ', 'murekkep', o5.BRONZ['ana']),
    (3, 'MAT_SIYAH', 'murekkep', HEX('#1E1E20')),
    (4, 'GRAFIT_GRI', 'murekkep', HEX('#404246')),
    (5, 'GUMUS_TONU', 'ton', dict(C=3.0, h=250.0)),               # notr, hafif soguk (tahmin)
    (6, 'ROSE_TONU', 'ton', HEX('#B76E79')),                       # yaygin "rose gold" web rengi (3. taraf adlandirma)
    (7, 'BORDO', 'murekkep', HEX('#70182A')),
    (8, 'LACIVERT', 'murekkep', HEX('#182656')),
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--katman', required=True); ap.add_argument('--cikti', required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    pkl_sha = hashlib.sha256(Path(a.katman).read_bytes()).hexdigest()
    D = pickle.load(open(a.katman, 'rb'))
    E, M, CC, ICP, govde, um = D['E'], D['M'], D['CC'], D['ICP'], D['govde'], D['um']
    o4.YASAK = o4.yasak_m(); o3.YASAK = o4.YASAK
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)   # inceleme: goruntu_yasak halka muafiyet bandi (altin/son ile ayni)
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
    L_med = float(np.median(lum(ALT['sembol'][ms])))
    a_med, b_med = float(np.median(Lab_s[:, 1])), float(np.median(Lab_s[:, 2]))
    C_alt, h_alt = float(np.hypot(a_med, b_med)), float(np.degrees(np.arctan2(b_med, a_med)) % 360)
    beyaz = np.full((N, N, 3), 255, np.uint8)
    BR = o5.BRONZ
    Lr = float(lum(BR['acik'][None])[0] / lum(BR['ana'][None])[0])
    gamut = {}

    def ton(cc, m, hedef, anahtar):
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
        out[sec], n = gamut_kroma(L_)
        gamut[anahtar] = gamut.get(anahtar, 0) + n
        return out

    def murekkep(cc, ad, ana):
        k = BR['koyu'] if np.array_equal(ana, BR['ana']) else ana * 0.6
        c = BR['acik'] if np.array_equal(ana, BR['ana']) else np.clip(ana * Lr, 0, 255)
        r = np.clip(lum(cc) / max(L_med, 1.0), 0.5, 1.5)
        t1 = np.clip((r - 0.5) / 0.5, 0, 1)[..., None]; t2 = np.clip((r - 1.0) / 0.5, 0, 1)[..., None]
        out = np.where(r[..., None] <= 1.0, k + (ana - k) * t1, ana + (c - ana) * t2)
        if ad in KUCUK_OGE:
            L = lum(out); La = float(lum(ana[None])[0])
            out = out * np.where(L > La, La / np.maximum(L, 1e-3), 1.0)[..., None]
        return out.astype(np.float32)

    def butunlestir(renk):
        """seffaf: on carpilmis 'over' birlestirme (zeminsiz). Doner (RGBA uint8, beyaz seramik uzerinde RGB uint8)."""
        Cp = np.zeros((N, N, 3), np.float32); Ap = np.zeros((N, N), np.float32)
        sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
        for ad in E:
            m = M[ad]; q = ICP[ad]
            ic = cv2.GaussianBlur(np.clip(m - sh(m, q['kayma']), 0, 1), (0, 0), q['sigma']) * m
            cc = renk[ad] * (1 - q['guc'] * ic)[..., None]
            sat = cc.max(2, keepdims=True); cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
            Cp = Cp * (1 - m[..., None]) + cc * m[..., None]; Ap = Ap * (1 - m) + m
        a8 = np.clip(np.round(Ap * 255), 0, 255).astype(np.uint8)
        col = np.where(Ap[..., None] > 1e-6, Cp / np.maximum(Ap, 1e-6)[..., None], 255.0)
        rgba = np.dstack([np.clip(np.round(col), 0, 255).astype(np.uint8), a8])
        af = a8.astype(np.float32)[..., None] / 255                                   # beyaz seramikte gorunum: kaydedilen 8 bit RGBA'dan
        rgb_b = np.clip(np.round(rgba[..., :3].astype(np.float32) * af + 255 * (1 - af)), 0, 255).astype(np.uint8)
        return rgba, rgb_b

    tum = np.maximum.reduce([M[k] for k in M])
    disari = tum < 0.5 / 255                                                        # 8 bitte alfa 0'a yuvarlanan (oge kenar kuyrugu disi)
    R = dict(karar=dict(zemin='SEFFAF PNG, maske disi alfa 0 (Merkez 3 Kas karar A); kontrast ve gorunum beyaz seramik (255) uzerinde birlestirilerek olculur',
                        katman=f'ornament_motor.py ORN_DUMP, ALTIN_MOTOR deneme 4 (e5412718, Serdar kabul); pkl sha256 {pkl_sha}',
                        uretim='yerel (Merkez gorevi: "yerelde calis"); KARAR 3 (Actions) ile celiski raporda',
                        dis_golge='yok (karar 18, zemin murekkepsiz)', dusus='yok (beyaz duz zeminde 1.0)',
                        ton_adaylari='sublimasyonda metalik murekkep yok: 1, 5, 6 duz baski renkleri (ALTIN_TONU, GUMUS_TONU, ROSE_TONU)',
                        bronz='BEIGE bronz paleti (o5.BRONZ, carpan 1.0); kucuk ogeler motor dokusuyla (BEIGE duz model rengiyle cizilmisti)',
                        hedef_ton_kaynak='tahmin / yaygin renk adlari: rose #B76E79, gumus C 3 h 250, siyah #1E1E20, grafit #404246, bordo #70182A, '
                                         'lacivert #182656'),
             altin_referans=dict(Lmed_luma=round(L_med, 2), C=round(C_alt, 2), h=round(h_alt, 2)), aday={})
    for n, ad_r, tur, hedef in ADAY:
        renk = {ad: (ton(ALT[ad], M[ad], hedef, ad_r) if tur == 'ton' else murekkep(ALT[ad], ad, hedef)) for ad in E}
        rgba, rgb = butunlestir(renk)
        ok = {k: o5.kontrast_yeni(rgb, M[k], 'acik') for k in KAPI_OGE}
        ok['halka_govde'] = o5.kontrast_yeni(rgb, M['halka'] * govde, 'acik')
        ok['halka_uclari'] = o5.kontrast_yeni(rgb, M['halka'] * um[0], 'acik')               # inceleme: BEIGE'deki gibi kapida (>= 2 px)
        ok['sembol_bilgi'] = o5.kontrast_yeni(rgb, M['sembol'], 'acik')
        ok['halka_uclari_2px_alti_bilgi'] = o5.kontrast_yeni(rgb, M['halka'] * um[1], 'acik', cekirdek=0.5)
        kk = {k: v['deger'] for k, v in ok.items() if not k.endswith('_bilgi') and v.get('deger') is not None}
        en_ad = min(kk, key=kk.get)
        gy, gb = o4.goruntu_yasak(rgb, beyaz, M.get('halka'))
        lk = o5.leke_kapisi(M, rgb, None)
        r = dict(tur=tur, kati_kontrast_en_kotu=round(kk[en_ad], 2), en_kotu_oge=en_ad, okunur=bool(kk[en_ad] >= o4.HEDEF), kontrast=ok,
                 sembol_kati_bilgi=ok['sembol_bilgi'].get('deger'), halka_uclari_kati=ok['halka_uclari'].get('deger'),
                 ortanca_en_kotu_bilgi=round(min(v['ortanca_bilgi'] for k, v in ok.items() if not k.endswith('_bilgi') and v.get('deger') is not None), 2),
                 goruntu_yasak=gy, leke_a=sum(v['alfa_lt_09'] for k2, v in lk.items() if k2 in o5.LEKE_KAPI_OGE),
                 zemin_seffaf=bool((rgba[..., 3][disari] == 0).all()), zemin_disi_alfa_sifir_olmayan=int((rgba[..., 3][disari] != 0).sum()),
                 gamut_kroma_kuculen_piksel=gamut.get(ad_r, 0),
                 bosluk_px=o5.bosluklar(E), sembol_kutu=list(o5.kutu(E, 'sembol')),
                 renk_medyan_rgb={k: [int(v) for v in np.median(rgb[M[k] >= 0.9], 0)] for k in ('sembol', 'isim1', 'kucuk_sol', 'halka')})
        dosya = f'SADE_{n}_{ad_r}_954.png'
        Image.fromarray(rgba, 'RGBA').save(O / dosya)
        r['dosya'] = dosya
        r['kapi'] = dict(leke_0=r['leke_a'] == 0, tasma_ve_yasak_0=sum(gy.values()) == 0, zemin_seffaf=r['zemin_seffaf'],
                         yerlesim_ayni=r['bosluk_px'] == [20, 20, 20] and r['sembol_kutu'][1] == 246)
        r['etiket'] = f'{n} {ad_r}: kati {r["kati_kontrast_en_kotu"]}' + ('' if r['okunur'] else ' OKUNMAZ (uretim adayi degil)')
        R['aday'][str(n)] = r
        print(r['etiket'], '| sembol', r['sembol_kati_bilgi'], '| uclar', r['halka_uclari_kati'], '| leke', r['leke_a'], '| yasak', sum(gy.values()),
              '| seffaf', r['zemin_seffaf'], r['zemin_disi_alfa_sifir_olmayan'], '| gamut', r['gamut_kroma_kuculen_piksel'], flush=True)
    R['teknik_kapi_hepsi'] = all(all(v['kapi'].values()) for v in R['aday'].values())
    R['okunur_adaylar'] = [n for n, v in R['aday'].items() if v['okunur']]
    R['okunmaz_adaylar'] = [n for n, v in R['aday'].items() if not v['okunur']]
    R['not_'] = 'teknik_kapi_hepsi yalniz leke / tasma / zemin / yerlesim; okunurluk ayri (okunur_adaylar)'
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('TEKNIK KAPI', 'PASS' if R['teknik_kapi_hepsi'] else 'FAIL', '| okunur', R['okunur_adaylar'], '| okunmaz', R['okunmaz_adaylar'], flush=True)
    return 0 if R['teknik_kapi_hepsi'] else 1


if __name__ == '__main__':
    sys.exit(main())
