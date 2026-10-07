#!/usr/bin/env python3
"""HEDEF GORUNUM KURULUMU (Serdar 7 Eki, ChatGPT referansi): ref_olc.py olcumunden (REF ve T5 ayni olcek, ayni maske)
doku_poster icin hedef JSON uretir. Her kalem surekli tek kural, bolgesel yama yok:

  ana_donusum : ana sembol L -> REF (25 yuzdelik cifti, T5 2000 olcek -> REF 2000 olcek; ara deger dogrusal, aralik
                disi uc farki sabit kayma) + a*, b* medyan farki. Diger ogeler ana sembole esitlenir (tek doku).
  kapi_hedef  : renk_kapi kapali dongu hedefi (7200 olcek): eski hedef L'nin donusumu, a*, b* + fark.
  zemin_egri  : 201 dugum; eski egri + (REF - T5) radyal profil farki (s %0.5 halkalari, Gauss 3 halka, veri olmayan
                uca sabit), izotonik (G, B disa artmayan; R azalmayan, zemin_gradient ile ayni).
  cember      : her 0.5 derecede genislik orani k = REF / T5 (alan / tepe), sonme g = REF / T5 normalize tepe orani
                (Gauss 8 derece, <= 1). Cember yaricap boyunca kendi merkez cizgisine gore k ile sikistirilir, alfa x g.
  doku        : metin ogesinde REF ic doku (2000 olcek, 3x3 std, asindirilmis cekirdek) asimi > %10 ise alfa agirlikli
                Gauss L yumusatma (sigma kalibre: tagline 3.0 px @7200 -> 4.63, REF 4.67).

Kullanim: hedef_kur.py --olcum olc_ref_t5.json --cikti HEDEF.json
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import zemin_gradient as zg                                          # noqa: E402

GRAD = KOK / 'varlik' / 'plates' / 'BLUE_16x20_gradient.json'
ESKI_HEDEF = (71.5, 8.5, 49.5)
DOKU_SIGMA = {'tagline': 3.0}       # kalibrasyon (7 Eki): T5 tagline ic doku 5.79 -> sigma 3.0 ile 4.63 (REF 4.67)


def dairesel_gauss(v, ok, sig):
    """0.5 derece adimli dairesel dizi; gecersiz noktalar agirlik 0 (normalize Gauss)."""
    n = len(v); k = int(4 * sig) + 1
    x = np.arange(-k, k + 1); g = np.exp(-0.5 * (x / sig) ** 2)
    vv = np.where(ok, v, 0.0); ww = ok.astype(float)
    pad = lambda a: np.r_[a[-k:], a, a[:k]]
    s = np.convolve(pad(vv), g, 'valid'); w = np.convolve(pad(ww), g, 'valid')
    return s / np.maximum(w, 1e-9), w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--olcum', required=True); ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    R = json.loads(Path(a.olcum).read_text())
    T = R[[k for k in R if k != 'REF'][0]]; F = R['REF']

    # ana donusum
    src = np.maximum.accumulate(np.array(T['ogeler']['ana_sembol']['L_q']) + np.arange(25) * 1e-4)
    dst = np.array(F['ogeler']['ana_sembol']['L_q'])
    da = F['ogeler']['ana_sembol']['Lab'][1] - T['ogeler']['ana_sembol']['Lab'][1]
    db = F['ogeler']['ana_sembol']['Lab'][2] - T['ogeler']['ana_sembol']['Lab'][2]
    kL = float(np.interp(ESKI_HEDEF[0], src, dst))
    out = {'ana_donusum': {'L_kaynak': src.round(3).tolist(), 'L_hedef': dst.round(3).tolist(), 'da': round(da, 3),
                           'db': round(db, 3)},
           'kapi_hedef': [round(kL, 3), round(ESKI_HEDEF[1] + da, 3), round(ESKI_HEDEF[2] + db, 3)]}

    # zemin egri
    g = json.loads(GRAD.read_text())['gradient']
    eski = np.array(g['egri'], np.float64)                      # 3 x 201, s dugumleri 0..1
    s_d = np.linspace(0, 1, eski.shape[1])
    nT, nF = np.array(T['zemin']['profil_n']), np.array(F['zemin']['profil_n'])
    ok = (nT >= 200) & (nF >= 200)
    sc = (np.arange(len(nT)) + 0.5) / 200
    yeni = []
    for c in range(3):
        d = np.array(F['zemin']['profil'][c]) - np.array(T['zemin']['profil'][c])
        dd = np.interp(s_d, sc[ok], d[ok])                      # veri disi uca sabit
        dd = cv2.GaussianBlur(dd[None].astype(np.float64), (0, 0), 3)[0]
        e = eski[c] + dd
        yeni.append(zg.pav(e, np.ones_like(e), c == 0))
    out['zemin_egri'] = [np.round(np.maximum(y, 0), 4).tolist() for y in yeni]
    out['zemin_fark_ozet'] = {'s_veri': [round(float(sc[ok].min()), 3), round(float(sc[ok].max()), 3)],
                              'B_fark_ic_dis': [round(float(yeni[2][0] - eski[2][0]), 2),
                                                round(float(yeni[2][-1] - eski[2][-1]), 2)]}

    # cember: 1 derece olcum -> 0.5 derece
    def dizi(C, k):
        v = np.array([c[k] if c else np.nan for c in C], float)
        return v
    wF, wT = dizi(F['cember'], 'genislik'), dizi(T['cember'], 'genislik')
    pF, pT = dizi(F['cember'], 'tepe'), dizi(T['cember'], 'tepe')
    gec = np.isfinite(wF) & np.isfinite(wT) & (pF > 60) & (pT > 60)
    gec[100:135] = False                                         # 120 derece civari: ana sembol / cember disi olcum
    kk, kw = dairesel_gauss(np.where(gec, wF / np.where(gec, wT, 1), 0), gec, 6)
    kk = np.where(kw > 0.05, kk, 1.0)                          # veri yok (cember yok): sikistirma yok
    var = np.isfinite(pF) & np.isfinite(pT) & (pF > 2) & (pT > 2)
    var[100:135] = False
    mF, mT = np.median(pF[gec]), np.median(pT[gec])
    sF, _ = dairesel_gauss(np.nan_to_num(pF), var, 8); sT, _ = dairesel_gauss(np.nan_to_num(pT), var, 8)
    oran = np.clip((sF / mF) / np.maximum(sT / mT, 1e-6), 0, 1)
    # sonme yalniz REF'in kendisinin sondugu uclarda (REF yumusak tepe < 0.95 x medyan); gecis surekli (0.95 -> 0.85)
    uc = np.clip((0.95 - sF / mF) / 0.10, 0, 1)
    gg = np.where(var, 1 - (1 - oran) * uc, 1.0)
    out['cember'] = {'aci_derece': list(range(360)), 'k': np.round(np.clip(kk, 0.5, 1.0), 4).tolist(),
                     'g': np.round(gg, 4).tolist(), 'k_medyan': round(float(np.median(kk[gec])), 3)}
    out['doku_sigma'] = DOKU_SIGMA
    Path(a.cikti).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ('zemin_egri', 'cember')}))
    print('cember k medyan', out['cember']['k_medyan'], 'g min', round(float(gg.min()), 3),
          'g < 0.95 aci', [i for i in range(360) if gg[i] < 0.95])


if __name__ == '__main__':
    main()
