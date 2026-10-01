#!/usr/bin/env python3
"""OLCEK TANISI (Serdar 1 Eki 16:28, siparis 4188621967 DB 18x24): onayli 2400 referansi (p0) ve BASKI dosyasi
isim satiri olculeri, DEEP_BLACK ve MIDNIGHT_BLUE icin AYNI 2400 koordinatlarinda.

Yalniz SAYI yazar (isim / mesaj / goruntu yok): satir_olc_alt sonuclari (p0, baski), kume sinirlari, olcum
penceresi, sol ismin sag kenarindaki kutle kuyrugu ve isim ile sonsuz arasindaki murekkep bilesenleri (yildiz vb.).
Girdi siparis-dijital ile ayni (GITHUB_EVENT_PATH, maskeli). Etsy / musteri / Drive yazimi YOK.
"""
import json, os, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surucu                                                     # noqa: E402


def ayrinti(sd, im, bant, k):
    """satir_olc_alt'in ara olculeri (2400 birimi)."""
    import cv2
    from pilot6 import LUMA
    eu = sd._mod('edisyon_uret')
    pay = sd.OLCEK_PAY
    Y0, Y1 = (bant[0] - pay) * k, (bant[1] + pay) * k
    y0, y1 = max(int(np.floor(Y0)), 0), min(int(np.ceil(Y1)), im.height)
    kes = np.asarray(im.convert('RGB').crop((0, y0, im.width, y1))).astype(np.float32)
    m = eu.murekkep(kes)
    km_tum = eu._kumeler(m, max(int(round(20 * k)), 1))
    km = [c for c in km_tum if c[1] - c[0] > 40 * k]
    r = {'kume_tum': [[round(a / k, 2), round(b / k, 2)] for a, b in km_tum],
         'kume': [[round(a / k, 2), round(b / k, 2)] for a, b in km]}
    if len(km) != 3:
        return r
    L = kes @ LUMA
    mu = m.astype(np.uint8)
    rr = max(int(round(3 * k)), 1)
    yakin = cv2.dilate(mu, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rr + 1,) * 2)) > 0
    uzak = ~(cv2.dilate(mu, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4 * rr + 1,) * 2)) > 0)
    cekirdek = cv2.erode(mu, np.ones((3, 3), np.uint8)) > 0
    if cekirdek.sum() < 50:
        cekirdek = m
    Li, Lz = float(np.median(L[cekirdek])), float(np.median(L[uzak] if uzak.any() else L))
    c = np.clip((L - Lz) / (Li - Lz), 0, 1) * yakin
    satir = np.arange(y0, y1)
    c *= np.clip(np.minimum(satir + 1, Y1) - np.maximum(satir, Y0), 0, 1)[:, None]
    Wd = c.shape[1]
    M = max(int(round(eu.UZAT_AZAMI * k)), 1)
    sinir = [0, (km[0][1] + km[1][0]) // 2, (km[1][1] + km[2][0]) // 2, Wd]
    xa = max(km[0][0] - M, sinir[0]); xb = min(km[0][1] + M, sinir[1])
    C = c[:, xa:xb].sum(axis=0)
    x0, x1 = sd._uc(C)
    T = float(C.sum())
    # sol ismin sag kuyrugu: x1 - 12 .. pencere sonu, 2400 birimine toplanmis kutle payi (binde)
    kuy = {}
    for i in range(max(int(x1 - 12 * k), 0), len(C)):
        b = round((xa + i) / k)
        kuy[b] = kuy.get(b, 0.0) + float(C[i]) / T * 1000
    # dikey: sol ismin satir kutle profili (ust / alt kuyruk, binde) - cap / taban farki icin
    Cr = c[:, xa:xb].sum(axis=1)
    u, t = sd._uc(Cr)
    Tr = float(Cr.sum())
    dik = {}
    for i in list(range(max(int(u - 6 * k), 0), int(u + 8 * k))) + list(range(max(int(t - 8 * k), 0), min(int(t + 6 * k), len(Cr)))):
        b_ = round((y0 + i) / k)
        dik[b_] = dik.get(b_, 0.0) + float(Cr[i]) / Tr * 1000
    r.update({'sol_ust_taban': [round((y0 + u) / k, 2), round((y0 + t) / k, 2)],
              'sol_dikey_binde': {str(a_): round(v_, 2) for a_, v_ in sorted(dik.items()) if v_ > 0.005}})
    r.update({'pencere_sol': [round(xa / k, 2), round(xb / k, 2)], 'M': round(M / k, 2),
              'sol_x0x1': [round((xa + x0) / k, 2), round((xa + x1) / k, 2)],
              'sol_kuyruk_binde': {str(a): round(v, 2) for a, v in sorted(kuy.items()) if v > 0.005},
              'kontrast': [round(Li, 1), round(Lz, 1)]})
    # sol isim ile sonsuz arasi murekkep bilesenleri (yildiz vb.)
    n, lab, st, _ = cv2.connectedComponentsWithStats(mu)
    bil = []
    for j in range(1, n):
        x, y, w, h, a = st[j]
        if km[0][1] - 30 * k <= x <= km[1][0] + 5 * k and w < 40 * k:
            bil.append({'x': [round(x / k, 1), round((x + w) / k, 1)], 'y': [round((y0 + y) / k, 1), round((y0 + y + h) / k, 1)],
                        'alan_2400': round(a / k / k, 1)})
    r['ara_bilesen'] = bil
    return r


def main():
    g = surucu.girdi()
    kod = Path(sys.argv[1]).resolve()
    os.chdir(kod)
    sd = surucu.kod_yukle(str(kod))
    no, _ = sd.sayfa_no_tablosu()
    sd.kisisel_hazirla()
    oran = sys.argv[2] if len(sys.argv) > 2 else '3x4'
    boy = sd.DIJITAL_BOY[oran]
    from PIL import Image
    renkler = (sys.argv[3].split(',') if len(sys.argv) > 3 else ['DEEP_BLACK', 'MIDNIGHT_BLUE'])
    for renk in renkler:
        ed = sd.RENK_ED[renk]
        yol = sd.pod_kaynak(g['cift'], renk, boy); kb = yol.read_bytes()
        with Image.open(yol) as im:
            hedef = list(im.size)
        P_ed = sd.EdisyonPoster(); P_blue = sd.BluePoster() if ed == 'blue' else None
        sd.MB_HEDEF['etkin'] = ed == 'blue'
        try:
            poster, bi, ek = sd.render_et(ed, oran, no[g['cift']], kb, (g['isim1'], g['isim2']), g['mesaj'],
                                          P_blue, P_ed, g['cift'], ref_boy=boy, hedef_en=hedef[0], boy=boy)
            cik = Path('_olcek_tani'); cik.mkdir(exist_ok=True)
            baski, _ = sd.tek_dosya(poster, bi, ek, kb, hedef, cik / f'{renk}.jpg', kalite=sd.DIJITAL_KALITE)
        finally:
            sd.MB_HEDEF['etkin'] = False
        p0 = ek.get('p0', poster)
        bant = bi['olcum']['isim_bant']
        k = baski.width / float(p0.width)
        sd.olcek_kur(baski.width); g1 = sd.satir_olc_alt(baski, bant, k); a1 = ayrinti(sd, baski, bant, k)
        sd.olcek_kur(2400); g0 = sd.satir_olc_alt(p0, bant, 1.0); a0 = ayrinti(sd, p0, bant, 1.0)
        kap = sd.olcek_kapisi(g1, g0, 1.0)
        # ESIT BANT GENISLIGI denemesi: baski 2400 izgarasina ALAN ortalamasiyla (cv2.INTER_AREA) indirilip olculur
        import cv2
        B24 = Image.fromarray(cv2.resize(np.asarray(baski.convert('RGB')), (2400, round(baski.height * 2400 / baski.width)),
                                         interpolation=cv2.INTER_AREA))
        sd.olcek_kur(2400); g1a = sd.satir_olc_alt(B24, bant, 1.0)
        kap_alan = sd.olcek_kapisi(g1a, g0, 1.0)
        print('OLCEK_TANI_ALAN', renk, boy, json.dumps({q: kap_alan.get(q) for q in ('gecti', 'konum_fark_px', 'kenar_fark_px', 'fark')}), flush=True)
        tem = lambda d: {q: d.get(q) for q in ('sol_isim', 'sonsuz', 'sag_isim', 'bosluk', 'satir_merkez',
                                                 'taban_sol', 'taban_sag', 'cap_sol', 'cap_sag', 'kontrast', 'hata')}
        print('OLCEK_TANI', renk, boy, json.dumps({'k': round(k, 4), 'isim_bant': bant, 'p0_px': list(p0.size),
              'baski_px': list(baski.size), 'p0': tem(g0), 'baski': tem(g1),
              'kapi': {q: kap.get(q) for q in ('gecti', 'konum_fark_px', 'kenar_fark_px', 'fark')}}), flush=True)
        print('OLCEK_TANI_AYRINTI', renk, boy, 'p0', json.dumps(a0), flush=True)
        print('OLCEK_TANI_AYRINTI', renk, boy, 'baski', json.dumps(a1), flush=True)
        # ham hi-res poster (birlestirme oncesi) ve plate: kuyruk nereden
        sd.olcek_kur(poster.width); ap = ayrinti(sd, poster, bant, poster.width / 2400.0); sd.olcek_kur(2400)
        print('OLCEK_TANI_AYRINTI', renk, boy, 'poster_hires', json.dumps(ap), flush=True)
        from pilot6 import LUMA
        pl = Image.open(bi['plate']).convert('RGB') if bi.get('plate') else None
        sat = {}
        for ad, im in (('p0', p0), ('baski', baski), ('poster', poster), ('plate', pl), ('kaynak', Image.open(yol))):
            if im is None:
                continue
            kk = im.width / 2400.0
            y0_, y1_ = int((bant[0] - 10) * kk), int((bant[1] + 10) * kk)
            A = np.asarray(im.convert('RGB').crop((int(940 * kk), y0_, int(990 * kk), y1_))).astype(np.float32) @ LUMA
            col = A.max(axis=0)                          # sutun basina en parlak (2400 birimine toplanir)
            sat[ad] = {str(940 + int(i / kk)): round(float(v), 1) for i, v in enumerate(col) if int(i / kk) % 2 == 0}
        print('OLCEK_TANI_SUTUN_MAKS', renk, boy, json.dumps(sat), flush=True)
        sat2 = {}
        for ad, im in (('p0', p0), ('baski', baski), ('kaynak', Image.open(yol))):
            kk = im.width / 2400.0
            x0_, x1_ = (g0.get('sol_isim') or [600, 1000])
            A = np.asarray(im.convert('RGB').crop((int(x0_ * kk), int((bant[0] - 15) * kk), int(x1_ * kk),
                                                   int((bant[1] + 15) * kk)))).astype(np.float32) @ LUMA
            row = A.max(axis=1)
            sat2[ad] = {str(round(bant[0] - 15 + i / kk)): round(float(v), 1) for i, v in enumerate(row)
                        if round(i / kk) % 2 == 0}
        print('OLCEK_TANI_SATIR_MAKS', renk, boy, json.dumps(sat2), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
