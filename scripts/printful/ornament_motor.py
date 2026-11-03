#!/usr/bin/env python3
"""ALTIN_MOTOR (Merkez / Serdar 3 Kas): RUBY, SAPPHIRE, EMERALD. Etsy / Printful / Drive yazma yok. BEIGE / AGED_PAPYRUS'a dokunulmaz.
Ana sembol: a114ddb G2 aynen (CANCER_LIBRA_ana.png). Kucuk burclar, isimler, tarih, logo, halka: posterin motoru (dal siparis-gpt 6da763a,
motor_gpt/) AYNI fonksiyonlar (golge_motor: kure_yukle, egim_tup, golgele_g, luma, renk_haritasi_dogrusal, uygula_harita2, srgb, lineer;
vektor_yuzey.yon_alani; alfa_temizle.temizle) ve KILIT_GPTGIRDI.json AYAR + ORTAM ile.
1 OLCEK k = 10 (tam sayi): ornament duzeni 9540 x 9540; a114ddb alfalari bu olcekte KAYNAKTAN yeniden uretilir (metin_alfa font x10, halka
  analitik x10 (T1), logo LOGO_1'den, kucuk burclar a114ddb zinciri). uret_tam butun olarak kosulmaz; golgele_oge (uret_tam'dan aynen) bu alfalara.
  Renk haritasi: ayni ciftin POSTER ana alfasi (girdi78/ana/cancer_libra_alfa.png, yerlesim78 + cember, temizle) golgele_oge -> Ys['ana'].
2 ZEMINSIZ KUCULTME: oge katmani zeminsiz; dogrusal isikta rgb x A ve A ayri INTER_AREA /10, sonra bolunur. 8 bit ara kayit yok.
3 RENK_UYUM 954'te, butunlesmeden ONCE: hedef G2 ana (a114ddb sembol) Lab ortancasi, alfa >= 0.9, asindirma yok, en az 200 piksel (yoksa DUR);
  oge katmanina tam Lab kaydirmasi (renk_uyum.py ile ayni d = Lana - Loge). Kapi dE00 <= 1.
4 GREN: KILIT gren (1.0), uret_tam formulu (sRGB 0-255, GaussianBlur(N(0,1), 0.8) / 0.35 x gren), yalniz ogede, 10x cizimde; 954'te kalan genlik olculur.
5 DISARIDA: yansima, temas, isima, poster dis golgesi, zemin_daire (karar 18: zemin rengi ogeye tasinmaz).
7 ALFA_TEMIZLE: yalniz kucuk burclar ve logo (posterde uygulandigi ogeler), 10x olcekte, pad 40 (olustur_alfa_sablon ile ayni). Isim / tarih / halka YOK.
Butunlesme: boya_motor = ornament_altin.boya_altin (a114ddb) ile ayni; deneme 4 (Merkez 3 Kas, Serdar kabul): kucuk ogelerde dusus = ana sembol
ortanca carpani (dus_sabit), esit 'goz' (KILIT esit=kazanc'tan onayli sapma; KILIT kontrolu yalniz dosya degerini dogrular), ic golge guc 0.35,
genislik x min(1, D_oge / D_ana). Kapilar: son dosya HAM dE00 <= 2 (dusus bolunmus deger ve renk_uyum dE00 <= 1 yalniz bilgi), ortanca kontrast
>= 4.5 (logo ve halka govdesi dahil), leke 0, tasma 0, ton, halka govde surekliligi (s >= 0.30, 3 px yay, >= %70; deneme 4: 0.692 FAIL, Serdar kabul;
neden esit 'goz' govdeyi parlatti), yerlesim a114ddb, IoU: kucuk burc / logo >= 0.98; isim / tarih / halka murekkep bolgesi ort. alfa farki <= 0.035; RUBY kurali.
Kullanim: ornament_motor.py --kaynak DIR --motor DIR(motor_gpt kopyasi) --cikti DIR --son DIR(a5e3ea2 STIL3_SON)"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


K10 = 10
AD_MOTOR = {'kucuk_sol': 'kucuk1', 'kucuk_sag': 'kucuk2', 'sonsuz': 'sonsuz', 'isim1': 'isim1', 'isim2': 'isim2', 'tarih': 'tagline', 'halka': 'cember'}
TEMIZ_OGE = ('kucuk_sol', 'kucuk_sag', 'sonsuz')
KUCUK_OGE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'kucuk_sol', 'kucuk_sag', 'halka')   # gorev tanimi: kucuk ogeler halka dahil (inceleme bulgu 3)
MOTOR_DOSYA = ('KILIT_GPTGIRDI.json', 'golge_motor.py', 'vektor_yuzey.py', 'alfa_temizle.py', 'uret_tam.py', 'renk_uyum.py', 'olustur_alfa_sablon.py',
               'kure/k4.npy', 'palet/chatgpt_altin.png', 'yerlesim78.json', 'cember.json')
# 78 cift (karar 28): kucuk burc poster yuksekligi = KUCUK_1/2 sprite kirpim yuksekligi (olustur_alfa_sablon, 6da763a; >8 kirpim, poster px);
# ornament hedef = sprite x C (cancer / libra kalibrasyon ortalamasi); CANCER ve LIBRA onayli degerlerle aynen (351 / 363, referans degismesin)
SPRITE_H = {'AQUARIUS': 381, 'ARIES': 615, 'CANCER': 594, 'CAPRICORN': 700, 'GEMINI': 614, 'LEO': 614, 'LIBRA': 615, 'PISCES': 613,
            'SAGITTARIUS': 658, 'SCORPIO': 615, 'TAURUS': 612, 'VIRGO': 683}
SPRITE_C = (351 / 594 + 363 / 615) / 2
P_VARSAYILAN = dict(pah=0.6, k=0.8, karisim=0.0, g=0.5, gs=60, golge_sigma=12, golge_dx=6, golge_dy=10, golge_opak=0.55, m1=0.0, m2=0.0, poz=1.0,
                    pah_px=0.0, kubbe=0.0, kure='studio2', mot_yer='Y', esit='goz', temas=0.0, zemin_daire=0, sarma=0.0, arka_isik=0.0, renk_ayar=0.0,
                    kararma=0.0, yansima=0.0, isima=0.0, isima_sigma=30.0, gren=0.0, kenar_yum=0.0, egim_max=0.0, pah_oran_max=0.0, ton=0.0, yildiz='t5',
                    parilti=0.0, parilti_esik=2.3, isik_leke=0.0, mot_poz=0, mot_s2=5.0, harita='sira')   # uret_tam.py satir 10 (6da763a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--motor', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--son', required=True)
    ap.add_argument('--cift', default='CANCER_LIBRA', help='alfabetik cift anahtari (karar 28); isim1 / sol kucuk burc = ilk burc')
    ap.add_argument('--zemin', default=None, help='KOYU_G1 (Serdar 3 Kas): koyu zemin dosyalari bu klasorden (ad ayni: RUBY_1264.png ...); kaynak sha kontrolu degismez')
    a = ap.parse_args()
    K_, MD, O, SON = Path(a.kaynak), Path(a.motor), Path(a.cikti), Path(a.son)
    O.mkdir(parents=True, exist_ok=True)
    # --- 6 KILIT: AYAR + ORTAM dosyadan; ortam motor importundan ONCE ---
    KL = json.loads((MD / 'KILIT_GPTGIRDI.json').read_text())
    ortam = dict(KL['ortam'])
    ortam['PALET_KAYNAK'] = str(MD / 'palet' / 'chatgpt_altin.png')   # KILIT'teki /home/claude/blender/palet/chatgpt_altin.png ile ayni dosya (sha raporda)
    os.environ.update(ortam)
    P = dict(P_VARSAYILAN); P.update(KL['AYAR'])
    CIFT = a.cift.upper(); B1, B2 = CIFT.split('_')
    assert '_'.join(sorted([B1, B2])) == CIFT, f'cift anahtari alfabetik degil: {CIFT}'
    POSTER_ALFA = f'girdi78/ana/{CIFT.lower()}_alfa.png'
    motor_sha = {f: sha(MD / f) for f in MOTOR_DOSYA + (POSTER_ALFA,)}
    log('KILIT ortam', json.dumps(ortam)); log('KILIT AYAR', json.dumps(KL['AYAR'])); log('P', json.dumps(P))
    log('motor sha', json.dumps({k: v[:16] for k, v in motor_sha.items()}))
    assert P['g'] == 0 and P['m1'] == 0 and P['m2'] == 0 and P['parilti'] == 0 and P['isik_leke'] == 0 and P['ton'] == 0 and P['esit'] == 'kazanc' \
        and P['harita'] == 'dogrusal', 'KILIT beklenen dallar disinda'
    sys.path.insert(0, str(MD))
    import golge_motor as gm
    from vektor_yuzey import yon_alani
    from alfa_temizle import temizle
    _s = importlib.util.spec_from_file_location('altin', Path(__file__).resolve().parent / 'ornament_altin.py')
    al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
    _s = importlib.util.spec_from_file_location('son2', Path(__file__).resolve().parent / 'ornament_altin_son2.py')
    s2 = importlib.util.module_from_spec(_s); _s.loader.exec_module(s2)
    al.INCE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'halka')        # a114ddb ile ayni (son2 deneme 2 degisikligi geri)
    son, o5, o4, o3, o1 = al.son, al.o5, al.o4, al.o3, al.o1
    N, MM, Pc, CX, CY = o5.N, o5.MM, o5.P, o5.CX, o5.CY
    lum = o4.lum
    for f, h in son.GERCEK.items():
        if not o1.sha(K_ / f).startswith(h):
            log('FAIL kaynak sha', f); return 1
    Kk = gm.kure_yukle(str(MD / 'kure' / f"{P['kure']}.exr"))          # kure_yukle .exr -> .npy
    # palet (uret_tam 143-147)
    pk = np.asarray(Image.open(os.environ['PALET_KAYNAK']).convert('RGB')).astype(np.float32) / 255
    hk = cv2.cvtColor(pk, cv2.COLOR_RGB2HSV); mk = ((hk[..., 1] > 0.45) & (hk[..., 2] > 0.42)).astype(np.uint8)
    ref_ana = pk[cv2.erode(mk, np.ones((3, 3), np.uint8)) > 0]
    log('palet', len(ref_ana))

    # --- golgele_oge: uret_tam.py 149-213 (6da763a) aynen; gurultu g = 0 (KILIT) -> Nx = Ny = 0; KAVSAK / SERIT kapali (KILIT) ---
    VEK = os.environ.get('VEKTOR', '0') == '1'
    VEK_OGE = os.environ.get('VEKTOR_OGELER', 'ana,kucuk1,kucuk2,sonsuz').split(',')
    assert float(os.environ.get('KAVSAK_YUM', '0')) == 0 and float(os.environ.get('KEMER_KAVSAK', '0')) == 0 and os.environ.get('SERIT', '0') == '0' \
        and os.environ.get('SIRT_SUREKLI', '0') == '0'

    def golgele_oge(a8, ad):
        A = a8.astype(np.float32) / 255
        h, w = A.shape; Yt = np.zeros((h, w), np.float32); At = np.zeros((h, w), np.float32)
        VYN = None
        if VEK and ad in VEK_OGE:
            assert P['karisim'] == 1.0 and P['pah_px'] == 0 and not P['kubbe']
            Ap = np.pad(A, 32)
            (vy_, vx_), alt_ = yon_alani(Ap)
            VYN = []
            for ux_s, uy_s in alt_:
                gxa = np.zeros(Ap.shape, np.float32); gya = np.zeros(Ap.shape, np.float32)
                gxa[vy_, vx_] = ux_s; gya[vy_, vx_] = uy_s
                VYN.append((gxa[32:-32, 32:-32], gya[32:-32, 32:-32]))
        KR, PD = 2048, 128
        for y0 in range(0, h, KR):
            for x0 in range(0, w, KR):
                ya, xa = max(0, y0 - PD), max(0, x0 - PD); yb, xb = min(h, y0 + KR + PD), min(w, x0 + KR + PD)
                Ak = A[ya:yb, xa:xb]
                if Ak.max() == 0: continue
                Ak = np.pad(Ak, 16)
                gm.egim_tup.kv = None; gm.egim_tup.H = None; gm.egim_tup.yon = None
                if VYN is not None:
                    Al = A[ya:yb, xa:xb]
                    kk_ = P['k'] / P['pah']
                    Y = np.zeros(Al.shape, np.float32)
                    for gxa, gya in VYN:
                        Y += gm.luma(gm.golgele_g(kk_ * gxa[ya:yb, xa:xb], kk_ * gya[ya:yb, xa:xb], Kk))
                    Y /= len(VYN)
                    ia, ib, ja, jb = y0 - ya, min(KR, h - y0) + (y0 - ya), x0 - xa, min(KR, w - x0) + (x0 - xa)
                    Yt[y0:y0 + ib - ia, x0:x0 + jb - ja] = Y[ia:ib, ja:jb]; At[y0:y0 + ib - ia, x0:x0 + jb - ja] = Al[ia:ib, ja:jb]
                    continue
                gx, gy, Al = gm.egim_tup(Ak, P['k'], pah=P['pah'], karisim=P['karisim'], pah_px=P['pah_px'], kubbe=P['kubbe'], egim_max=P['egim_max'],
                                         pah_oran_max=P['pah_oran_max'])
                gx, gy, Al = gx[16:-16, 16:-16], gy[16:-16, 16:-16], Al[16:-16, 16:-16]
                Y = gm.luma(gm.golgele_g(gx, gy, Kk))
                sr = getattr(gm.egim_tup, 'sirt', None)
                if sr is not None:
                    sr = sr[16:-16, 16:-16] if sr.shape != Y.shape else sr
                    Yb = cv2.GaussianBlur(Y, (0, 0), 0.7)
                    Y = np.where(sr, Yb, Y).astype(np.float32)
                    gm.egim_tup.sirt = None
                ia, ib, ja, jb = y0 - ya, min(KR, h - y0) + (y0 - ya), x0 - xa, min(KR, w - x0) + (x0 - xa)
                Yt[y0:y0 + ib - ia, x0:x0 + jb - ja] = Y[ia:ib, ja:jb]; At[y0:y0 + ib - ia, x0:x0 + jb - ja] = Al[ia:ib, ja:jb]
        return Yt, At

    def cekirdek_Y(Y, A):
        return Y[cv2.erode((A > 0.99).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0]

    # --- poster ana (renk haritasi icin): olustur_alfa_sablon.py 45-61 ile ayni ---
    def kirp8(x):
        ys, xs = np.nonzero(x > 8)
        return x[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    src = kirp8(np.asarray(Image.open(MD / POSTER_ALFA)).astype(np.float32))
    Yl = json.loads((MD / 'yerlesim78.json').read_text())[CIFT]
    Cm = json.loads((MD / 'cember.json').read_text())['cember']
    sp = (Cm['cx'] + Yl['u1'] * Cm['R'] - (Cm['cx'] + Yl['u0'] * Cm['R'])) / src.shape[1]
    tpa = np.clip(cv2.resize(src, None, fx=sp, fy=sp, interpolation=cv2.INTER_AREA if sp < 1 else cv2.INTER_CUBIC), 0, 255).astype(np.uint8)
    tpa, b_ = temizle(tpa)
    log('poster ana', tpa.shape, 'olcek', round(sp, 4), b_)
    Ya, Aa = golgele_oge(tpa, 'ana')
    cm = cv2.erode((Aa > 0.99).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    har = gm.renk_haritasi_dogrusal(Ya[cm], ref_ana)
    QS = [2, 5, 25, 50, 75, 95, 98]
    qa = np.percentile(cekirdek_Y(Ya, Aa), QS)

    def gorunen(Y, A):
        """uret_tam.py gorunen (6da763a) aynen: goz olcegi (1/3.6), alfa agirlikli kucultme, aa > 0.85."""
        f = 1 / 3.6
        ya = cv2.resize(Y * A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        aa = cv2.resize(A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        return (ya / np.maximum(aa, 1e-4))[aa > 0.85]
    qa_goz = np.percentile(gorunen(Ya, Aa), QS)                      # deneme 4 (Merkez 3 Kas onayi): kucuk ogelerde esit 'goz'
    log('harita', [round(float(v), 4) for v in har[1:6]], 'qa50', round(float(qa[3]), 4))

    # --- ornament duzeni (a114ddb ile ayni) ---
    o4.YASAK = o4.yasak_m(); o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2); o3.YASAK = o4.YASAK
    spec = importlib.util.spec_from_file_location('tek_doku', K_ / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    pp = o4.poster_profil(K_ / 'HALKA_BLUE_16x20.png')
    KENAR_ONARIM = {}

    def kenar_onar(ad, g):
        """Serdar 4 Kas (Kova): olcum payi eski haline (24 px) dondu; kapinin leke saydigi pikseller (ic & alfa < 0.9) varsa goruntu duzeltilir:
        delik_kapat ic onarimi kapi olcumuyle ayni cercevede (dis pay yok) bir kez daha uygulanir (alfa 1, renk inpaint). Sayi 0 ise dokunulmaz
        (CANCER_LIBRA ve leke saymayan kaynaklar birebir). Kaynak dosyaya dokunulmaz; yalniz bellekteki kopya."""
        ic0, _ = o5.leke_ic_kaynak(g[..., 3]); n0 = int((ic0 & (g[..., 3] < 0.9)).sum())
        if n0 == 0:
            return g
        g2, tur = g, []
        for _ in range(3):                                                   # dolan pikseller kapanisi buyutebilir: sayi 0 olana kadar (en cok 3 tur)
            g2, n_ = o5._delik_kapat(g2)
            ic1, _ = o5.leke_ic_kaynak(g2[..., 3]); n1 = int((ic1 & (g2[..., 3] < 0.9)).sum()); tur.append(dict(onarilan=int(n_), kalan=n1))
            if n1 == 0:
                break
        KENAR_ONARIM[ad] = dict(onarim_oncesi_leke_px=n0, tur=tur, alfa_degisimi_en_buyuk=round(float(np.abs(g2[..., 3] - g[..., 3]).max()), 4),
                                degisen_piksel=int((np.abs(g2 - g) > 1e-6).any(-1).sum()))
        log('kenar onarim', ad, KENAR_ONARIM[ad])
        return g2
    ANA_DOSYA = K_ / f'{CIFT}_ana.png'
    ana0 = np.asarray(Image.open(ANA_DOSYA).convert('RGBA'), np.float32); ana0[..., 3] /= 255.0
    ana0 = o1.kirp(ana0, ana0[..., 3], pad=2)
    if ana0.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(ana0, 1600 / ana0.shape[1]); ana0 = np.dstack([r_, a_])
    ana5, _ = o5.delik_kapat(ana0)
    ana5 = kenar_onar('ana', ana5)
    ic_, _ = o5.leke_ic_kaynak(ana5[..., 3]); o5.KAYNAK_SONRA['ana'] = int((ic_ & (ana5[..., 3] < 0.9)).sum())
    lsrc = o4.logo_kaynak(K_ / 'LOGO_1.png')
    cap = o4.CAP0
    G = int(math.ceil(o5.BOSLUK_ORAN * cap))
    kucuk_g = {}

    def kucuk(burc, h_ratio, k=1):
        if burc not in kucuk_g:
            g = np.asarray(Image.open(K_ / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32); g[..., 3] /= 255.0
            g = o1.kirp(g, g[..., 3], pad=2)
            g, _ = o5.delik_kapat(g)
            g = kenar_onar(burc, g)
            ic2, _ = o5.leke_ic_kaynak(g[..., 3]); o5.KAYNAK_SONRA[burc] = int((ic2 & (g[..., 3] < 0.9)).sum())
            kucuk_g[burc] = g
        g = kucuk_g[burc]
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        rgb_, a_ = o1.rgba_olcek(g, h_ratio * cap * k / (gy1 - gy0))
        rgb_, a_, _ = o5.hedef_kapat(rgb_, a_)
        return rgb_, a_

    def logo(k=1):
        kk = cap * o4.LOGO_H * k / lsrc.shape[0]
        sz = (max(1, int(round(lsrc.shape[1] * kk))), max(1, int(round(cap * o4.LOGO_H * k))))
        return np.clip(cv2.resize(lsrc, sz, interpolation=cv2.INTER_AREA if kk <= 1 else cv2.INTER_CUBIC), 0, 1)
    T = dict(isim1=o1.metin_alfa('EMILY', K_ / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa('JAMES', K_ / 'Cinzel.ttf', cap, 500),
             tarih=o1.metin_alfa('14 JUNE 2025', K_ / 'EBGaramond-Italic.ttf', Pc['tagline_T'] / Pc['cap'] * cap, None, ref='T'), sonsuz=logo(), cap=cap)
    def h_oran(b):
        if b == 'CANCER':
            return Pc['kucuk_sol_h'] / Pc['cap']
        if b == 'LIBRA':
            return Pc['kucuk_sag_h'] / Pc['cap']
        return SPRITE_H[b] * SPRITE_C / Pc['cap']
    kc = {'sol': kucuk(B1.lower(), h_oran(B1)), 'sag': kucuk(B2.lower(), h_oran(B2))}
    KUCUK_H = {'sol': (B1, round(h_oran(B1) * Pc['cap'], 2)), 'sag': (B2, round(h_oran(B2) * Pc['cap'], 2))}
    # karar 28: ana sembol CANCER_LIBRA kutusuna (genislik hedefi, yukseklik = CANCER_LIBRA en / boy) orani bozulmadan sigar; buyutme yok
    if CIFT != 'CANCER_LIBRA':
        _cl = np.asarray(Image.open(K_ / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32); _cl[..., 3] /= 255.0
        _cl = o1.kirp(_cl, _cl[..., 3], pad=2)
        if _cl.shape[1] > 1600:
            _r, _a = o1.rgba_olcek(_cl, 1600 / _cl.shape[1]); _cl = np.dstack([_r, _a])
        _cl, _ = o5.delik_kapat(_cl)
        _b = o1.bbox(_cl[..., 3], 0.5); ORAN_CL = (_b[3] - _b[1]) / (_b[2] - _b[0])
        _orj = o3.sembol_yerlestir

        def sembol_kutu(ana, w_hedef, cx, cy):
            x0, y0, x1, y1 = o1.bbox(ana[..., 3], 0.5)
            olc0_ = min(w_hedef / (x1 - x0), w_hedef * ORAN_CL / (y1 - y0))
            olc_ = olc0_
            if KUCULT[0] > 0:                                                 # teshis 3 Kas: halka ile sigmazsa yukseklik KUCULT px kucultulur (oran sabit, yalniz kucultme)
                h_s = (y1 - y0) * olc0_; olc_ = olc0_ * (h_s - KUCULT[0]) / h_s
            KUTU_BILGI.update(w_hedef=round(float(w_hedef), 2), h_hedef=round(float(w_hedef * ORAN_CL), 2), olcek=round(float(olc_), 5),
                              olcek_kutu=round(float(olc0_), 5), kucultme_px=int(KUCULT[0]),
                              sinir='genislik' if olc0_ == w_hedef / (x1 - x0) else 'yukseklik', buyutme=bool(olc_ > 1))
            rgb_, a_ = o1.rgba_olcek(ana, olc_)
            bb_ = o1.bbox(a_, 0.5)
            return (rgb_, a_, int(round(cx - (bb_[0] + bb_[2]) / 2)), int(round(cy - (bb_[1] + bb_[3]) / 2)))
        o3.sembol_yerlestir = sembol_kutu
        o5.o3.sembol_yerlestir = sembol_kutu
    KUTU_BILGI = {}
    KUCULT = [0]
    ha, hb = o5.halka_T(pp, son.S0)
    Y, bilgi = o5.yerlesim_V5(pp, ana5, T, kc, ha, hb, G)
    KUCULT_IZ = []
    while CIFT != 'CANCER_LIBRA' and Y is None and bilgi.get('hata') == 'sembol sigmiyor' and len(KUCULT_IZ) < 10:
        KUCULT_IZ.append(dict(kucultme_px=KUCULT[0], gereken_kucultme_px=bilgi.get('gereken_kucultme_px'), cakisma=bilgi.get('cakisma')))
        KUCULT[0] += max(1, int(bilgi.get('gereken_kucultme_px') or 1))
        log('sembol sigmiyor: kutu yuksekligi', KUCULT[0], 'px kucultulup yeniden', KUCULT_IZ[-1])
        Y, bilgi = o5.yerlesim_V5(pp, ana5, T, kc, ha, hb, G)
    KUTU_BILGI['kucultme_iz'] = KUCULT_IZ
    if Y is None:
        log('FAIL yerlesim', json.dumps(bilgi, default=str))
        (O / 'OLCUM.json').write_text(json.dumps(dict(hata='yerlesim_V5', cift=CIFT, bilgi=bilgi, kucuk_burc_hedef_h_poster_px=KUCUK_H, kutu=KUTU_BILGI),
                                                  indent=1, ensure_ascii=False, default=str))
        return 1
    if CIFT != 'CANCER_LIBRA':                                                # alt kenar kucuk burc satirinin G px ustu (bosluk 20/20/20)
        E_ = Y['E']; k0 = o5.satir(E_, o5.KUCUK)[0]; s4 = o5.kutu(E_, 'sembol'); dy = (k0 - G) - s4[3]
        o5.kaydir(E_, ('sembol',), dy)
        M_, yb_, cak_, ok_ = o4.kapi(E_)
        bilgi.update(sembol_alt_hizalama_dy=int(dy), kapi_ok=bool(ok_), kutu=KUTU_BILGI)
        if not ok_:
            log('FAIL yerlesim (alt hizalama sonrasi kapi)', yb_, cak_[:4])
            (O / 'OLCUM.json').write_text(json.dumps(dict(hata='alt_hizalama_kapi', cift=CIFT, yasak=yb_, cakisma=cak_[:8], bilgi=bilgi),
                                                      indent=1, ensure_ascii=False, default=str))
            return 1
        Y.update(M=M_, yasak=yb_, cak=cak_)
    bilgi['kucuk_burc_hedef_h_poster_px'] = KUCUK_H
    log('yerlesim', CIFT, bilgi, 'sembol kutu', o5.kutu(Y['E'], 'sembol'))
    model = son.model_kur(td, Y)

    # --- 1 10x alfalar (kaynaktan) ---
    def metin_alfa10(metin, font_yolu, cap_px, wght=None, ref='H', ss=4):
        """o1.metin_alfa ile ayni punto arama (954 cap). 954'un 4x tuvalinin TAM 10 kati tuval, ayni capa x 10, punto x 10;
        olcek 954'teki gibi (round(W/ss), round(H/ss)) x 10 cerceveye INTER_AREA (954 yuvarlamasi aynen). Hizalama yok."""
        def f_(pt):
            f = ImageFont.truetype(str(font_yolu), max(4, int(round(pt))))
            if wght:
                f.set_variation_by_axes([wght])
            return f
        pt = cap_px * ss * 1.45
        for _ in range(4):
            f = f_(pt); b = f.getbbox(ref, anchor='ls'); pt *= cap_px * ss / max(1, -b[1])
        pt_i = max(4, int(round(pt)))
        b1 = f_(pt_i).getbbox(metin, anchor='ls'); pad = 6 * ss
        W1, H1 = b1[2] - b1[0] + 2 * pad, b1[3] - b1[1] + 2 * pad
        w9, h9 = max(1, round(W1 / ss)), max(1, round(H1 / ss))
        im = Image.new('L', (W1 * K10, H1 * K10), 0)
        ImageDraw.Draw(im).text(((pad - b1[0]) * K10, (pad - b1[1]) * K10), metin, font=f_(pt_i * K10), fill=255, anchor='ls')
        PUNTO[metin] = dict(punto_954_ss4=pt_i, punto_10x_ss4=pt_i * K10)
        return cv2.resize(np.asarray(im, np.float32) / 255.0, (w9 * K10, h9 * K10), interpolation=cv2.INTER_AREA)

    def cerceve10(a10, a954, ad):
        assert a10.shape == (a954.shape[0] * K10, a954.shape[1] * K10), (ad, a10.shape, a954.shape)
        return a10, (0, 0)
    PUNTO = {}
    A10, hiz = {}, {}
    A10['isim1'], hiz['isim1'] = cerceve10(metin_alfa10('EMILY', K_ / 'Cinzel.ttf', cap, 500), Y['E']['isim1'][1], 'isim1')
    A10['isim2'], hiz['isim2'] = cerceve10(metin_alfa10('JAMES', K_ / 'Cinzel.ttf', cap, 500), Y['E']['isim2'][1], 'isim2')
    A10['tarih'], hiz['tarih'] = cerceve10(metin_alfa10('14 JUNE 2025', K_ / 'EBGaramond-Italic.ttf', Pc['tagline_T'] / Pc['cap'] * cap, None, ref='T'),
                                       Y['E']['tarih'][1], 'tarih')
    temiz_bilgi = {}
    def kucuk10(burc, ad):
        """a114ddb zinciri: delik_kapat'li kaynak -> 954 cercevesinin TAM 10 kati (w x 10, h x 10) on carpilmis INTER_AREA -> hedef_kapat.
        (deneme 2: yuvarlanmamis olcek x 10 ile cizim 954 boyu yuvarlamasindan %0.4-0.9 sapiyordu; inceleme bulgu 1)"""
        g = kucuk_g[burc]; h, w = Y['E'][ad][1].shape
        pm = cv2.resize(np.concatenate([g[..., :3] * g[..., 3:4], g[..., 3:4]], -1), (w * K10, h * K10), interpolation=cv2.INTER_AREA)
        a2 = np.clip(pm[..., 3], 0, 1); rgb_ = np.clip(pm[..., :3] / np.maximum(a2[..., None], 1e-4), 0, 255)
        return o5.hedef_kapat(rgb_, a2)[1]

    def logo10(ad):
        h, w = Y['E'][ad][1].shape
        return np.clip(cv2.resize(lsrc, (w * K10, h * K10), interpolation=cv2.INTER_CUBIC), 0, 1)
    for ad, src10 in (('sonsuz', logo10('sonsuz')), ('kucuk_sol', kucuk10(B1.lower(), 'kucuk_sol')), ('kucuk_sag', kucuk10(B2.lower(), 'kucuk_sag'))):
        a8 = np.clip(np.round(src10 * 255), 0, 255).astype(np.uint8)
        q = 40; t8, b_ = temizle(np.pad(a8, q)); temiz_bilgi[ad] = b_
        A10[ad], hiz[ad] = cerceve10(t8[q:-q, q:-q].astype(np.float32) / 255, Y['E'][ad][1], ad)
    log('temizle', json.dumps(temiz_bilgi))
    # halka 10x: o5.halka_T ile ayni yontem (analitik, ikili ss = 4 alt ornek / piksel), 10x piksel izgarasinda (= 954'te ss 40), ayni T1
    hm = Y['M']['halka']
    ys_, xs_ = np.nonzero(hm > 0.001)
    hy0, hy1, hx0, hx1 = ys_.min() - 2, ys_.max() + 3, xs_.min() - 2, xs_.max() + 3
    ax, by, cyh = hb['ax'], hb['by'], hb['cy']
    SSH = 4
    H10 = np.zeros(((hy1 - hy0) * K10, (hx1 - hx0) * K10), np.float32)
    xx = ((np.arange(H10.shape[1] * SSH) + 0.5) / (K10 * SSH) + hx0).astype(np.float32)
    for r0 in range(0, H10.shape[0], 100):
        r1 = min(H10.shape[0], r0 + 100)
        yy = ((np.arange(r0 * SSH, r1 * SSH) + 0.5) / (K10 * SSH) + hy0).astype(np.float32)
        dx_, dy_ = xx[None, :] - CX, yy[:, None] - cyh
        rho = np.sqrt((dx_ / ax) ** 2 + (dy_ / by) ** 2)
        d = (rho - 1) * np.sqrt(dx_ ** 2 + dy_ ** 2) / np.maximum(rho, 1e-6)
        ang = (np.degrees(np.arctan2(dy_, dx_)) + 360) % 360
        w = o5.genislik_T(pp, ang, son.S0)
        H10[r0:r1] = ((np.abs(d) <= w / 2) & (w > 0)).astype(np.float32).reshape(r1 - r0, SSH, -1, SSH).mean((1, 3))
    A10['halka'] = H10
    log('10x alfalar', {k: v.shape for k, v in A10.items()})

    # --- golgeleme + renk (10x), zeminsiz katman, dogrusal kucultme ---
    rng = np.random.default_rng(11)
    katman, Atest, gren_olc = {}, {}, {}
    for ad in ('kucuk_sol', 'kucuk_sag', 'sonsuz', 'isim1', 'isim2', 'tarih', 'halka'):
        a10 = A10[ad]
        a8 = np.clip(np.round(a10 * 255), 0, 255).astype(np.uint8)
        Yo, Ao = golgele_oge(a8, AD_MOTOR[ad])
        for _ in range(2):                                                                     # esit 'goz' (uret_tam.py ile ayni dongu)
            qo = np.percentile(gorunen(Yo, Ao), QS); qo = np.maximum.accumulate(qo + np.arange(len(qo)) * 1e-5)
            Yo = np.interp(Yo, qo, qa_goz).astype(np.float32)
        rgb_s = gm.uygula_harita2(Yo, har)                                                     # sRGB 0-1
        rgb = gm.lineer(rgb_s) * P['poz']
        Ak = cv2.GaussianBlur(Ao, (0, 0), P['kenar_yum']) if P['kenar_yum'] else Ao
        c255 = gm.srgb(rgb) * 255
        gn = cv2.GaussianBlur(rng.standard_normal(Ao.shape).astype(np.float32), (0, 0), 0.8)
        c255g = c255 + (gn / 0.35 * P['gren'])[..., None]                                       # gren yalniz ogede (uret_tam formulu)
        out = []
        for cc in (c255g, c255):
            lin = gm.lineer(np.clip(cc, 0, 255) / 255)
            h9, w9 = a10.shape[0] // K10, a10.shape[1] // K10
            num = cv2.resize(lin * Ak[..., None], (w9, h9), interpolation=cv2.INTER_AREA)
            den = cv2.resize(Ak, (w9, h9), interpolation=cv2.INTER_AREA)
            col = num / np.maximum(den, 1e-6)[..., None]
            # destek disi (alfa ~0) piksel: normalize bulanik doldurma (yalniz bindirmede maske kenari icin)
            bos = den < 0.02
            if bos.any():
                nb = cv2.GaussianBlur(num, (0, 0), 2.0); db = cv2.GaussianBlur(den, (0, 0), 2.0)
                col = np.where(bos[..., None], nb / np.maximum(db, 1e-6)[..., None], col)
            out.append(gm.srgb(np.clip(col, 0, 1)) * 255)
        katman[ad] = out[0]
        Atest[ad] = cv2.resize(Ao, (a10.shape[1] // K10, a10.shape[0] // K10), interpolation=cv2.INTER_AREA)
        ce9 = Atest[ad] >= 0.9
        gren_olc[ad] = dict(std_10x_seviye=round(float(gn.std() / 0.35 * P['gren']), 3),
                            kalan_954_luma_std=round(float(lum((out[0] - out[1])[ce9]).std()), 3) if ce9.sum() > 10 else None)
        log('oge', ad, a10.shape, 'gren 954 kalan', gren_olc[ad]['kalan_954_luma_std'])
        if ad in ('kucuk_sol', 'isim1', 'sonsuz', 'halka'):
            np.save(O / f'_poster10x_{ad}.npy', np.dstack([np.clip(c255g, 0, 255), Ak[..., None] * 255]).astype(np.uint8)) if ad != 'halka' else None

    # tam tuval renkleri (954) ve IoU
    def tuvale(ad, arr):
        out = np.zeros((N, N) + arr.shape[2:], np.float32)
        if ad == 'halka':
            out[hy0:hy1, hx0:hx1] = arr
        else:
            rgb_, a_, x, y = Y['E'][ad]; h, w = a_.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            out[ya:yb, xa:xb] = arr[ya - y:yb - y, xa - x:xb - x]
        return out
    CC = {ad: tuvale(ad, v) for ad, v in katman.items()}
    IOU, IOU_B = {}, {}
    for ad in katman:
        t1_, t2_ = tuvale(ad, Atest[ad]), Y['M'][ad]
        m1 = t1_ > 0.5; m2 = t2_ > 0.5
        IOU[ad] = round(float((m1 & m2).sum() / max((m1 | m2).sum(), 1)), 4)
        m1 = t1_ >= 0.5; m2 = t2_ >= 0.5
        IOU_B[ad] = dict(ikili_ge_05=round(float((m1 & m2).sum() / max((m1 | m2).sum(), 1)), 4),
                         yumusak=round(float(np.minimum(t1_, t2_).sum() / max(np.maximum(t1_, t2_).sum(), 1e-6)), 4),
                         ort_mutlak_fark_murekkep=round(float(np.abs(t1_ - t2_)[(t1_ > 0.02) | (t2_ > 0.02)].mean()), 4))
    log('IoU', IOU)
    # --- 3 renk_uyum (954, butunlesme oncesi) ---
    labf = lambda x: cv2.cvtColor((np.clip(x, 0, 255).reshape(-1, 1, 3) / 255).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    rgbS, aS, xS, yS = Y['E']['sembol']
    mS = aS >= 0.9
    Lana = np.median(labf(rgbS[mS]), 0)
    ru = {}
    for ad in katman:
        m = Y['M'][ad] >= 0.9
        if m.sum() < 200:
            log('DUR renk_uyum piksel', ad, int(m.sum())); json.dump(dict(dur='renk_uyum < 200 piksel', oge=ad, piksel=int(m.sum())), open(O / 'DUR.json', 'w'))
            return 2
        Lo = np.median(labf(CC[ad][m]), 0)
        d = Lana - Lo
        sec = Y['M'][ad] > 0.001
        L = labf(CC[ad][sec]) + d[None, :]
        CC[ad][sec] = np.clip(cv2.cvtColor(L.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255, 0, 255)
        Ls = np.median(labf(CC[ad][m]), 0)
        ru[ad] = dict(piksel=int(m.sum()), kaydirma_Lab=[round(float(v), 2) for v in d], dE00_once=round(de00(Lana, Lo), 3), dE00_sonra=round(de00(Lana, Ls), 3))
    log('renk_uyum', json.dumps({k: (v['dE00_once'], v['dE00_sonra']) for k, v in ru.items()}))
    # --- butunlesme (a114ddb) + kapilar ---
    KAT = {}

    def oge_renk_motor(Y_, model_, td_, ad, varyant, kazanc):
        if ad == 'sembol':
            cc = np.zeros((N, N, 3), np.float32); rgb_, a_, x, y = Y_['E'][ad]; h, w = a_.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = rgb_[ya - y:yb - y, xa - x:xb - x]
        else:
            cc = CC[ad].copy()
        return np.clip(cc * kazanc * KAT.get(ad, 1.0), 0, 255)
    al.oge_renk = oge_renk_motor
    um = o5.uc_maske(pp, son.S0)
    # --- deneme 3 (Merkez 3 Kas): ic golge oge yari kalinligina oranli; ana sembolde a114ddb ile ayni ---
    from skimage.morphology import skeletonize

    def yari_kal(a):
        m = (a > 0.5).astype(np.uint8)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        return float(np.median(dt[skeletonize(m > 0)]))
    sx0_, _, sx1_, _ = o1.bbox(Y['E']['sembol'][1], 0.5); ax0_, _, ax1_, _ = o1.bbox(ana5[..., 3], 0.5)
    D_ana = yari_kal(ana5[..., 3]) * (sx1_ - sx0_) / (ax1_ - ax0_)          # ana kaynak (1600 px) cozunurlugunde olculur, 954 pikseline cevrilir
    YK = {'sembol': round(D_ana, 3)}
    YK.update({ad: round(yari_kal(A10[ad]) / K10, 3) for ad in A10})        # 10x alfadan, 954 pikseline
    IC0 = al.IC_GOLGE
    ICP = {}
    for ad in Y['E']:
        r_ = min(1.0, YK[ad] / D_ana)
        ICP[ad] = dict(oran=round(r_, 4), kayma=IC0['kayma'] * r_, sigma=IC0['sigma'] * r_, guc=IC0['guc'])   # deneme 4: guc 0.35 aynen, yalniz genislik
    ICP_A114 = {ad: dict(oran=None, kayma=IC0['kayma'], sigma=IC0['sigma'], guc=IC0['ince'] if ad in al.INCE else IC0['guc']) for ad in Y['E']}
    log('yari kalinlik (954 px)', YK); log('ic golge', {k: (v['oran'], round(v['guc'], 3)) for k, v in ICP.items()})

    def f_dus_hesap(z):
        """ornament_altin.boya_altin 2. adim ile ayni formul (alt 0.92, us 0.25, sigma 60)."""
        zf = z.astype(np.float32)
        Lz = cv2.GaussianBlur(lum(zf), (0, 0), al.DUSUS['sigma'])
        yy, xx = np.mgrid[0:N, 0:N]
        Lref = float(np.median(Lz[np.hypot(xx + 0.5 - CX, yy + 0.5 - CY) < 150]))
        return np.clip((Lz / max(Lref, 1)) ** al.DUSUS['us'], al.DUSUS['alt'], 1.0)

    def boya_motor(Y_, model_, z, td_, varyant, kazanc, icp, dus_sabit=None):
        """ornament_altin.boya_altin (a114ddb) ile ayni; farklar: ic golge (kayma, sigma, guc) ogeye gore icp'den; dus_sabit verilirse sembol disi ogelerde sabit dusus."""
        M = Y_['M']
        zf = z.astype(np.float32)
        out = zf.copy()
        tum = np.maximum.reduce([M[k] for k in M])
        gm_ = cv2.GaussianBlur(tum, (0, 0), al.DIS_GOLGE['sigma'])
        gm_ = cv2.warpAffine(gm_, np.float32([[1, 0, al.DIS_GOLGE['kayma']], [0, 1, al.DIS_GOLGE['kayma']]]), (N, N))
        out = out * (1 - al.DIS_GOLGE['opak'] * gm_)[..., None]
        f_dus = f_dus_hesap(z)
        f_doku = np.ones((N, N), np.float32)
        once = {}
        sh = lambda a_, d: cv2.warpAffine(a_, np.float32([[1, 0, d], [0, 1, d]]), (N, N))
        for ad in Y_['E']:
            cc = al.oge_renk(Y_, model_, td_, ad, varyant, kazanc)
            once[ad] = cc.copy()
            m = M[ad]; q = icp[ad]
            ic = cv2.GaussianBlur(np.clip(m - sh(m, q['kayma']), 0, 1), (0, 0), q['sigma']) * m
            fd = f_dus if (dus_sabit is None or ad == 'sembol') else dus_sabit       # deneme 4: kucuk ogelerde ana sembol ortanca carpani
            carpan = fd * f_doku * (1 - q['guc'] * ic)
            cc = cc * carpan[..., None]
            sat = cc.max(2, keepdims=True)
            cc = np.where(sat > 255, cc * 255 / np.maximum(sat, 1e-3), cc)
            out = out * (1 - m[..., None]) + cc * m[..., None]
        return np.clip(np.round(out), 0, 255).astype(np.uint8), once
    # halka govdesi (T1: s >= 0.30)
    yy_, xx_ = np.mgrid[0:N, 0:N].astype(np.float32)
    angm = (np.degrees(np.arctan2(yy_ + 0.5 - cyh, xx_ + 0.5 - CX)) + 360) % 360
    r_p = (pp['el']['a'] + pp['el']['b']) / 2
    s_m = np.minimum(np.radians((pp['t1'] - angm) % 360), np.radians((angm - pp['t2']) % 360)) * r_p / pp['L']
    govde = (s_m >= son.S0) & ~((angm > pp['t1']) & (angm < pp['t2']))
    if os.environ.get('ORN_DUMP'):                                          # SADE_8 icin: renk_uyum sonrasi oge katmanlari + duzen (varsayilan kapali)
        import pickle
        pickle.dump(dict(CC=CC, E=Y['E'], M=Y['M'], ICP=ICP, YK=YK, govde=govde, um=um, hb=hb, iou=IOU, iou_bilgi=IOU_B, renk_uyum=ru,
                         motor_sha=motor_sha, yerlesim=bilgi), open(os.environ['ORN_DUMP'], 'wb'))
        log('DUMP', os.environ['ORN_DUMP']); return 0
    hk_ = s2.lab_ton(ana5[..., :3][ana5[..., 3] >= 0.98].astype(np.float32))
    TON_REF = (float(np.percentile(hk_, 5)), float(np.percentile(hk_, 95)))

    def sureklilik(rgb):
        L = lum(rgb.astype(np.float32))
        Tg = np.arange(0, 360, 0.05); tr = np.radians(Tg)
        px = CX + ax * np.cos(tr); py = cyh + by * np.sin(tr)
        al_ = cv2.remap(hm, (px - 0.5).astype(np.float32)[None], (py - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        gv = cv2.remap(govde.astype(np.float32), (px - 0.5).astype(np.float32)[None], (py - 0.5).astype(np.float32)[None], cv2.INTER_NEAREST)[0] > 0.5
        Lv = cv2.remap(L, (px - 0.5).astype(np.float32)[None], (py - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        ok = gv & (al_ >= 0.5)
        ds = np.hypot(np.diff(np.r_[px, px[0]]), np.diff(np.r_[py, py[0]])); s = np.cumsum(ds)
        med = float(np.median(Lv[ok])); en, yer = 1e9, None
        for i in np.nonzero(ok)[0][::4]:
            w_ = ok & (np.abs(s - s[i]) <= 1.5)
            v = float(Lv[w_].mean())
            if v < en: en, yer = v, float(Tg[i])
        uc = (~gv) & (al_ >= 0.5)
        return dict(yontem='orta eksen (1 px cizgi, 0.05 derece adim) uzerinde 3 px yay penceresi ortalamasi; yalniz govde (s >= 0.30, alfa >= 0.5)',
                    govde_ortanca=round(med, 1), en_dusuk_3px=round(en, 1), oran=round(en / med, 3), en_dusuk_aci=yer,
                    uclar_bilgi=dict(ortanca=round(float(np.median(Lv[uc])), 1) if uc.any() else None,
                                     en_dusuk=round(float(Lv[uc].min()), 1) if uc.any() else None))

    def lab_med(img, m):
        return np.median(labf(img[m]), 0)

    def de_tablo(img):
        m0 = Y['M']['sembol'] >= 0.9; Ls_ = lab_med(img, m0)
        return {k: round(de00(Ls_, lab_med(img, Y['M'][k] >= 0.9)), 3) for k in Y['E'] if k != 'sembol'}

    def de_dusus(rgb, z):
        """son dosya: dusus carpani (sRGB'de uygulanan tek skaler) bolunerek; oge ve ana sembol alfa >= 0.9 ortanca Lab dE00."""
        fd = f_dus_hesap(z)
        rb = np.clip(rgb.astype(np.float32) / fd[..., None], 0, 255)
        return de_tablo(rb)

    def L_dag(rgb):
        r = {}
        for k in Y['E']:
            Lk = labf(rgb[Y['M'][k] >= 0.9].astype(np.float32))[:, 0]
            r[k] = dict(L_p50=round(float(np.percentile(Lk, 50)), 1), L_p95=round(float(np.percentile(Lk, 95)), 1),
                        L_ge_80_yuzde=round(float((Lk >= 80).mean() * 100), 1))
        return r

    def olc(rgb, once, z):
        onc = np.zeros((N, N, 3), np.float32)
        for k in Y['E']:
            msk = Y['M'][k] >= 0.9; onc[msk] = once[k][msk]
        ok = {k: o5.kontrast_yeni(rgb, Y['M'][k], 'koyu') for k in ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag')}
        ok['sonsuz'] = o5.kontrast_yeni(rgb, Y['M']['sonsuz'], 'koyu')                                # logo kapida (standart cekirdek alfa >= 0.9)
        ok['halka_govde'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * govde, 'koyu')
        ok['halka_uclari_2px_alti_bilgi'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[1], 'koyu', cekirdek=0.5)
        kk = [v for k, v in ok.items() if not k.endswith('_bilgi') and v.get('deger') is not None]
        gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
        return dict(kontrast_ortanca_en_kotu=round(min(v['ortanca_bilgi'] for v in kk), 2), kati_koyu5_en_kotu_bilgi=round(min(v['deger'] for v in kk), 2),
                    kontrast=ok, goruntu_yasak=gy, goruntu=gb, leke=o5.leke_kapisi(Y['M'], rgb, None), renk_sadakati=al.renk_sadakati(rgb, once, Y['M']),
                    ton_lab=s2.ton_kapisi(rgb, Y['M'], TON_REF), bosluk_px=o5.bosluklar(Y['E']), sembol_kutu=list(o5.kutu(Y['E'], 'sembol')),
                    halka_sureklilik=sureklilik(rgb), dE00_butunlesme_oncesi=de_tablo(onc), dE00_son_ham=de_tablo(rgb), dE00_son_dusus_bolunmus_bilgi=de_dusus(rgb, z), L_dagilim_bilgi=L_dag(rgb))
    R = {'motor': dict(dal='siparis-gpt', commit='6da763a', dosya_sha256=motor_sha, KILIT_ortam=ortam, KILIT_AYAR=KL['AYAR'], P=P,
                       paketler=dict(numpy=np.__version__, opencv=cv2.__version__, pillow=Image.__version__,
                                     not_='Pillow 11.0.0 kalir (Merkez 3 Kas): a114ddb maskeleri 11.0.0 ile uretildi; motor Pillow kutuphanesini yalniz okuma icin kullanir. Motor is akisi 12.3.0 / numpy 2.5.3 kurar')),
         'olcek': dict(k=K10, not_='tek tam sayi olcek; alfalar 10x kaynaktan; poster parametreleri (kenar_yum 0.5, YON_SIGMA 6, sirt 0.7, gren sigma 0.8) '
                                   'poster pikselinde ve 10x cizimde AYNEN (poster ogesi / ornament 10x orani: isim 298 / 282 = 1.06, halka 5695 / ' + str(H10.shape[1]) + ' = ' + str(round(5695 / H10.shape[1], 2)) + ')',
                       logo='LOGO_1 kaynagi 200 px yukseklik; 10x 282 px -> 1.41 buyutme (INTER_CUBIC); kaynak yetersiz', hizalama=hiz),
         'disarida': 'yansima, temas, isima, poster dis golgesi, zemin_daire (karar 18)', 'temizle': temiz_bilgi, 'iou_954': IOU, 'iou_954_bilgi': IOU_B, 'punto': PUNTO, 'gren': gren_olc,
         'renk_uyum': ru, 'yerlesim': bilgi, 'ton_referans_lab_p5_p95': [round(TON_REF[0], 1), round(TON_REF[1], 1)], 'sonuc': {}}
    rgbler = {}
    oz_test, DUSLAR, ZEMIN_SHA = {}, {}, {}
    for renk, zf in al.RENKLER:
        zyol = (Path(a.zemin) / zf) if a.zemin else (K_ / zf)
        ZEMIN_SHA[renk] = sha(zyol)
        z = o1.zemin_canva(zyol)
        KAT.clear()
        r0_, _ = al.boya_altin(Y, model, z, td, 'G2', 1.0); r1_, _ = boya_motor(Y, model, z, td, 'G2', 1.0, ICP_A114)
        oz_test[renk] = bool(np.array_equal(r0_, r1_))                      # oz test: a114ddb ayariyla boya_motor == boya_altin (bayt)
        if not oz_test[renk]:
            log('FAIL oz test boya_motor', renk, int(np.abs(r0_.astype(int) - r1_).max())); return 4
        fdz = f_dus_hesap(z); DUS = float(np.median(fdz[Y['M']['sembol'] >= 0.9])); DUSLAR[renk] = round(DUS, 4)
        rgb, once = boya_motor(Y, model, z, td, 'G2', 1.0, ICP, DUS)
        r = olc(rgb, once, z)
        artis = 1.0
        if r['kontrast_ortanca_en_kotu'] < o4.HEDEF:
            if renk != 'RUBY':
                R['sonuc'][renk] = r
                log('DUR', renk, 'ortanca', r['kontrast_ortanca_en_kotu'])
                R['cikis'] = dict(kod=1, fail=[f'kontrast_ortanca {renk}'], aciklama='sert kapi FAIL (SAPPHIRE / EMERALD kontrast: DUR)')
                (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float)); return 1
            for k100 in range(101, 161):
                artis = k100 / 100
                KAT.clear(); KAT.update({k: artis for k in KUCUK_OGE})
                rgb, once = boya_motor(Y, model, z, td, 'G2', 1.0, ICP, DUS)
                r = olc(rgb, once, z)
                if r['kontrast_ortanca_en_kotu'] >= o4.HEDEF:
                    break
        r['kucuk_oge_parlaklik_artisi'] = round(artis, 2)
        R['sonuc'][renk] = r; rgbler[renk] = rgb
        o1.kaydet(rgb, O / f'{CIFT}_{renk}_954.png')
        log(renk, 'ortanca', r['kontrast_ortanca_en_kotu'], 'kati', r['kati_koyu5_en_kotu_bilgi'], 'artis', artis, 'yasak', sum(r['goruntu_yasak'].values()),
            'leke', sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE), 'halka', r['halka_sureklilik']['oran'],
            {k: v.get('ortanca_bilgi') for k, v in r['kontrast'].items()})
    font = ImageFont.truetype(str(K_ / 'EBGaramond-Italic.ttf'), 24)
    liste, et = [], []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD', 'BEIGE', 'AGED_PAPYRUS'):
        if renk in rgbler:
            r = R['sonuc'][renk]
            liste.append(rgbler[renk])
            et.append(f'{renk}: motor (k4 kure, KILIT)\nortanca {r["kontrast_ortanca_en_kotu"]} {"PASS" if r["kontrast_ortanca_en_kotu"] >= 4.5 else "FAIL"}, koyu %5 {r["kati_koyu5_en_kotu_bilgi"]}\n'
                      f'dE00 son dosya (ham) en cok {max(r["dE00_son_ham"].values())} {"PASS" if max(r["dE00_son_ham"].values()) <= 2.0 else "FAIL"}, halka govde {r["halka_sureklilik"]["oran"]}\nkucuk oge parlaklik x{r["kucuk_oge_parlaklik_artisi"]}')
        else:
            if not (SON / f'{CIFT}_{renk}_954.png').exists():
                continue
            liste.append(np.asarray(Image.open(SON / f'{CIFT}_{renk}_954.png').convert('RGB'))); et.append(f'{renk}: a5e3ea2 (onayli, aynen)')
    son.onizleme_etiketli(liste, et, font, h_et=130).save(O / 'ONIZLEME_76mm_5RENK.png', dpi=(300, 300))
    # YAKIN_DOKU: her oge poster olceginde (10x motor cizimi, zeminsiz, notr koyu zemin; ana: poster katmani) | ornament 954 (3x)
    zem_g = np.array([28, 30, 36], np.float32)
    s_ = o5.kutu(Y['E'], 'sembol')
    t45 = math.radians(-35); hx_, hy_ = int(CX + ax * math.cos(t45)), int(cyh + by * math.sin(t45))
    kut = {'ana': (s_[0] + 20, s_[1] + 150, s_[0] + 120, s_[1] + 230), 'kucuk_sol': o5.kutu(Y['E'], 'kucuk_sol'), 'isim1': o5.kutu(Y['E'], 'isim1'),
           'sonsuz': o5.kutu(Y['E'], 'sonsuz'), 'halka': (hx_ - 30, hy_ - 30, hx_ + 30, hy_ + 30)}
    satirlar = []
    for ad, bx in kut.items():
        bx = (bx[0] - 3, bx[1] - 3, bx[2] + 3, bx[3] + 3)
        orn = Image.fromarray(rgbler['RUBY']).crop(bx); orn = orn.resize((orn.width * 3, orn.height * 3), Image.NEAREST)
        if ad == 'ana':
            sx_, sy_ = (bx[0] - xS) / aS.shape[1], (bx[1] - yS) / aS.shape[0]
            g0 = np.asarray(Image.open(ANA_DOSYA).convert('RGBA'), np.float32)
            g0 = o1.kirp(g0, g0[..., 3] / 255, pad=2)
            fx = g0.shape[1] / aS.shape[1]
            x0_, y0_ = int((bx[0] - xS) * fx), int((bx[1] - yS) * fx)
            cr = g0[y0_:y0_ + int((bx[3] - bx[1]) * fx), x0_:x0_ + int((bx[2] - bx[0]) * fx)]
            pst = cr[..., :3] * (cr[..., 3:] / 255) + zem_g * (1 - cr[..., 3:] / 255)
        elif ad == 'halka':
            Hc = A10['halka']; rs_ = katman['halka']
            ys0, xs0 = (bx[1] - hy0) * K10, (bx[0] - hx0) * K10
            ys1, xs1 = (bx[3] - hy0) * K10, (bx[2] - hx0) * K10
            pst = None
        else:
            pst = None
        if pst is None:
            fpath = O / f'_poster10x_{ad}.npy'
            if fpath.exists():
                arr = np.load(fpath).astype(np.float32); rgb_, a_, x, y = Y['E'][ad]
                y0_, x0_ = (bx[1] - y) * K10, (bx[0] - x) * K10
                cr = arr[max(0, y0_):max(0, y0_) + (bx[3] - bx[1]) * K10, max(0, x0_):max(0, x0_) + (bx[2] - bx[0]) * K10]
                c3 = cr[..., :3].reshape(-1, 3)
                Lk = labf(c3) + np.array(ru[ad]['kaydirma_Lab'], np.float32)[None]
                c3 = np.clip(cv2.cvtColor(Lk.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_Lab2RGB).reshape(cr.shape[:2] + (3,)) * 255, 0, 255)
                pst = c3 * (cr[..., 3:] / 255) + zem_g * (1 - cr[..., 3:] / 255)
            else:                                                     # halka: 10x katman tekrar yerine 954 katmanin 10x yakin goruntusu yok; alfa x renk
                a10c = A10['halka'][ys0:ys1, xs0:xs1]
                c10 = cv2.resize(katman['halka'][bx[1] - hy0:bx[3] - hy0, bx[0] - hx0:bx[2] - hx0], (a10c.shape[1], a10c.shape[0]), interpolation=cv2.INTER_CUBIC)
                pst = c10 * a10c[..., None] + zem_g * (1 - a10c[..., None])
        pim = Image.fromarray(np.clip(pst, 0, 255).astype(np.uint8)).resize((orn.width, orn.height), Image.LANCZOS)
        etk = ('poster katmani CANCER_LIBRA_ana.png (ornament kirpiminin ayni bolgesi)' if ad == 'ana' else
               ('954 halka rengi x 10x alfa (poster pikseli degil)' if ad == 'halka' else 'motor 10x cizim + renk_uyum kaydirmasi (poster pikseli degil)'))
        yazi = f'{ad}: sol {etk}, notr zemin | sag ornament RUBY 954 (3x)'
        tw = int(ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(yazi, font=font)) + 12
        c = Image.new('RGB', (max(pim.width + orn.width + 24, tw), max(pim.height, orn.height) + 36), 'white')
        c.paste(pim, (0, 0)); c.paste(orn, (pim.width + 24, 0))
        ImageDraw.Draw(c).text((4, max(pim.height, orn.height) + 4), yazi, fill=(20, 20, 20), font=font)
        satirlar.append(c)
    u = Image.new('RGB', (max(s.width for s in satirlar), sum(s.height for s in satirlar) + 24 * (len(satirlar) - 1)), 'white'); yy0 = 0
    for s in satirlar:
        u.paste(s, (0, yy0)); yy0 += s.height + 24
    u.save(O / 'YAKIN_DOKU.png')
    for f in O.glob('_poster10x_*.npy'):
        f.unlink()
    A_ = list(R['sonuc'].values())
    g = dict(kontrast_ortanca=all(r['kontrast_ortanca_en_kotu'] >= o4.HEDEF for r in A_),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A_),
             leke_a_0=all(sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE) == 0 for r in A_),
             leke_a_kaynak_0=all(v == 0 for v in o5.KAYNAK_SONRA.values()),
             ton=all(v['dhue_ortanca'] < 1.0 and v['b_ge_r_yuzde'] == 0 for r in A_ for v in r['renk_sadakati'].values()) and
                 all(v['aralikta'] and v['b_ge_r_yuzde'] == 0 for r in A_ for v in r['ton_lab'].values()),
             bosluk_20_20_20=all(r['bosluk_px'] == [20, 20, 20] for r in A_),
             iou_kucuk_logo_ge_098=all(IOU[k] >= 0.98 for k in ('kucuk_sol', 'kucuk_sag', 'sonsuz')),
             alfa_fark_metin_halka_le_0035=all(IOU_B[k]['ort_mutlak_fark_murekkep'] <= 0.035 for k in ('isim1', 'isim2', 'tarih', 'halka')),
             dE00_son_ham_le_2=all(max(r['dE00_son_ham'].values()) <= 2.0 for r in A_),
             artis_yalniz_ruby=all(R['sonuc'][r]['kucuk_oge_parlaklik_artisi'] == 1.0 for r in ('SAPPHIRE', 'EMERALD')))
    if CIFT == 'CANCER_LIBRA':                                                 # onayli CL: sembol ust y 246 sert (kapi listesi)
        g['sembol_ust_246_cancer_libra'] = all(r['sembol_kutu'][1] == 246 for r in A_)
    g = {k: bool(v) for k, v in g.items()}
    s4b = o5.kutu(Y['E'], 'sembol')
    BILGI = dict(halka_govde_sureklilik=dict(gecti=bool(all(r['halka_sureklilik']['oran'] >= 0.70 for r in A_)),
                                             oran={k: R['sonuc'][k]['halka_sureklilik']['oran'] for k in R['sonuc']}, esik=0.70),
                 sembol_ust_y=int(s4b[1]), sembol_ust_y_cancer_libra=246,
                 sembol_genislik=int(s4b[2] - s4b[0]), sembol_yukseklik=int(s4b[3] - s4b[1]),
                 sembol_kutu_hedef=dict(w=KUTU_BILGI.get('w_hedef'), h=KUTU_BILGI.get('h_hedef', 404), sinir=KUTU_BILGI.get('sinir'),
                                        olcek=KUTU_BILGI.get('olcek'), buyutme=KUTU_BILGI.get('buyutme'),
                                        olcek_kutu=KUTU_BILGI.get('olcek_kutu'), kucultme_px=KUTU_BILGI.get('kucultme_px', 0),
                                        kucultme_iz=KUTU_BILGI.get('kucultme_iz', []),
                                        h_w_orani=(round(float(s4b[3] - s4b[1]) / float(s4b[2] - s4b[0]), 4) if s4b[2] > s4b[0] else None),
                                        not_='CANCER_LIBRA onayli hali 425 x 404 (kutu fonksiyonu kullanilmaz)'))
    R['kapi_sert'] = g; R['kapi_bilgi'] = BILGI
    R['kapi'] = g; R['kaynak_leke_onarim_sonrasi'] = dict(o5.KAYNAK_SONRA); R['kaynak_kenar_onarim'] = KENAR_ONARIM
    R['bilgi_renk_uyum_dE00_le_1'] = bool(all(v['dE00_sonra'] <= 1.0 for v in ru.values()))   # tanim geregi gecer (medyan -> medyan); yalniz bilgi
    R['deneme4'] = dict(dusus_kucuk_oge_sabit=DUSLAR, dusus_yontem='kucuk ogelerde f_dus = ana sembol (alfa >= 0.9) f_dus ortancasi; ana sembol degismez',
                        esit_kucuk_oge='goz: uret_tam.py gorunen (1/3.6 goz olcegi, alfa agirlikli, aa > 0.85) yuzdelikleri QS poster ana Ys[ana] yuzdeliklerine '
                                       'iki tur np.interp; KILIT AYAR esit=kazanc yerine (Merkez 3 Kas: Serdar "ayni altin" istegiyle onayli sapma)',
                        qa_goz=[round(float(v), 4) for v in qa_goz], ic_golge='guc 0.35 aynen, kayma ve sigma x min(1, D_oge / D_ana)')
    R['kutu'] = {k: [int(v) for v in o5.kutu(Y['E'], k)] for k in Y['E']}
    R['zemin'] = dict(klasor=str(a.zemin) if a.zemin else 'kaynak (GERCEK)', sha256=ZEMIN_SHA)
    R['ic_golge'] = dict(yontem='kayma, sigma = a114ddb (1.0, 0.6) x min(1, D_oge / D_ana), guc 0.35 aynen (deneme 4); D = iskelet uzerinde mesafe donusumu ortancasi '
                                '(yari kalinlik, 954 px; ogeler 10x alfadan, ana 1600 px kaynaktan); INCE (0.15) listesi kullanilmaz',
                         yari_kalinlik_954px=YK, oge=ICP, oz_test_a114ddb_bayt_ayni=oz_test)
    R['dE00_son_yontem'] = ('kapi: son PNG (ham, dusus bolunmeden) oge ve ana sembol alfa >= 0.9 pikselleri ortanca Lab -> CIEDE2000 (renk_uyum.py de00) <= 2.0; '
                            'dusus bolunmus deger bilgi')
    R['iou_kapi'] = 'kucuk_sol / kucuk_sag / sonsuz: IoU (alfa > 0.5) >= 0.98; isim / tarih / halka: IoU bilgi, kapi ort_mutlak_fark_murekkep (murekkep bolgesi: iki maskeden birinde alfa > 0.02) <= 0.035 (Merkez 3 Kas + onay)'
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    R['cikis'] = dict(kod=0 if all(g.values()) else 1, aciklama='0 = sert kapilar gecti, 1 = sert kapi FAIL, 2 = cokus; bilgi kapilari etkilemez',
                      fail=[k for k, v in g.items() if not v])
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    log('KAPI sert', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', '| bilgi', json.dumps(BILGI, default=str))
    return 0 if all(g.values()) else 1


def de00(Lab1, Lab2):
    """renk_uyum.py (6da763a) de00 ile ayni formul."""
    L1, a1, b1 = [float(v) for v in Lab1]; L2, a2, b2 = [float(v) for v in Lab2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    if C1p * C2p == 0: hpm = hs
    elif abs(h1p - h2p) <= 180: hpm = hs / 2
    else: hpm = (hs + 360) / 2 if hs < 360 else (hs - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2); Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001  (cikis 2 = cokus, tam traceback)
        import traceback
        traceback.print_exc()
        sys.exit(2)
