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
DE_ESIK, KONTRAST_ESIK = 9.2, 0.76  # kosu 36255489602: 51 dogru ornek dE<=7.4 x1.25, oran>=0.95 x0.8
if os.environ.get('MESAJ_ESIK'):
    DE_ESIK, KONTRAST_ESIK = map(float, os.environ['MESAJ_ESIK'].split(','))


ETKIN = {'edisyon': False}     # tagline ton eslemesi yalniz edisyon (Blue disi) render'inda (siparis_dosyasi)
TON_SINIR = (0.6, 1.7)

# DIKIS DUZELTMESI (Serdar onayi 2 Eki; DIKIS_TANI): tagline profili (pilot7.altin_sekil) isim referans
# glifinden ornekleniyor; ilk satirlari kenar / parlama sicramasi (MB: dL +63, -99, +101) -> cap ust kenarinda ve aynalanan
# ust uzantilarda cok cizgili acik bant; kuyruk_duzlestir'in SABIT kuyrugu baseline cevresinde iki sert kenarli serit.
# Duzeltme: bas ve son %20'de |dL| > esik olan uc satirlar atilir, kalan profil butun banda gerilir (sabit kuyruk yok).
# esik = max(6, 4 x medyan |dL|) (kisa profilde satir basi egim buyuk). Serdar onayi 2 Eki: varsayilan ACIK (DIKIS_DUZELT=0 kapatir).
DIKIS = {'etkin': os.environ.get('DIKIS_DUZELT', '1') != '0'}
DIKIS_UC, DIKIS_ESIK = 0.20, 6.0


def altin_sekil_duz(mask, prof, bant, yumusak=False, sigma=None, kh=None, ks=None):
    """pilot7.altin_sekil ile AYNI (gecis + glif kabartmasi); tek fark: taban (baseline) altinda profil AYNALANMAZ,
    son satirin rengi duz devam eder (2. deneme, 2 Eki: aynalama kirpilan profilin son egimini baseline'da tepeye
    ceviriyordu; 11x14 MB alt hat 10.5 -> 17). Ust (cap ustu) aynalama aynen."""
    import pilot7
    from PIL import Image as _I, ImageFilter
    sigma = pilot7.SIGMA if sigma is None else sigma; kh = pilot7.KH if kh is None else kh; ks = pilot7.KS if ks is None else ks
    m = np.asarray(mask).astype(np.float32) / 255.0
    h, w = m.shape
    ust, taban = bant
    r = np.arange(h, dtype=np.float32)
    u = (r - ust) / max(taban - ust, 1)
    u = np.where(u < 0, -u, u)
    u = np.clip(u, 0, 1)                                   # taban alti: duz uc (aynalama yok)
    idx = u * (len(prof) - 1)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(prof) - 1)
    t = (idx - lo)[:, None]
    base = (prof[lo] * (1 - t) + prof[hi] * t)[:, None, :] * np.ones((1, w, 1), np.float32)
    hf = np.asarray(_I.fromarray((m * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(sigma))).astype(np.float32) / 255.0
    gy = np.gradient(hf, axis=0)
    sm = float(np.max(np.abs(gy))) or 1.0
    sh = np.clip(gy / sm, -1, 1)[:, :, None]
    o = np.zeros((h, w, 4), np.uint8)
    o[..., :3] = np.clip(base * (1 + kh * np.clip(sh, 0, 1) + ks * np.clip(sh, -1, 0)), 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return _I.fromarray(o, "RGBA")


def profil_kenar_kirp(prof, uc=DIKIS_UC, esik=DIKIS_ESIK):
    """Profilin bas / son kenar satirlarini atar. Doner (profil, (i0, i1))."""
    p = np.asarray(prof, np.float32)
    d = np.abs(np.diff(p @ LUMA)); n = len(d)
    if n < 10:
        return p.copy(), (0, len(p) - 1)
    e = max(esik, 4.0 * float(np.median(d)))
    bas = [i for i in range(int(n * uc)) if d[i] > e]
    son = [i for i in range(int(n * (1 - uc)), n) if d[i] > e]
    i0 = bas[-1] + 1 if bas else 0
    i1 = son[0] if son else n
    return p[i0:i1 + 1].copy(), (int(i0), int(i1))


def ortak_profil(p1, p2):
    """Iki isim profilinin (farkli uzunluk) ortak boya yeniden orneklenmis ortalamasi."""
    a, b = np.asarray(p1, np.float32), np.asarray(p2, np.float32)
    n = max(len(a), len(b))
    ia = np.linspace(0, len(a) - 1, n); ib = np.linspace(0, len(b) - 1, n)
    ra = np.stack([np.interp(ia, np.arange(len(a)), a[:, c]) for c in range(3)], 1)
    rb = np.stack([np.interp(ib, np.arange(len(b)), b[:, c]) for c in range(3)], 1)
    return ((ra + rb) / 2).astype(np.float32)


def ton_esle(img, hedef):
    """RGBA tagline plakasinin murekkep cekirdegi medyanini hedef renge kanal kazanciyla esler; golge / doku
    deseni (altin_sekil) korunur, yalniz ton kayar."""
    a = np.asarray(img).astype(np.float32)
    cek = a[..., 3] > 200
    if cek.sum() < 100:
        return img, None
    med = np.median(a[cek][:, :3], 0)
    kaz = np.clip(np.asarray(hedef, np.float32) / np.maximum(med, 1.0), *TON_SINIR)
    a[..., :3] = np.clip(a[..., :3] * kaz, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA'), [round(float(v), 3) for v in kaz]


def duzeltme_uygula(pilot12, pilot16=None):
    """30 Eyl (Leo / Libra DB mesaj_murekkep, ARIES_LEO PW; tani 36695282686, dogrulama 36702761868):
    isimler kendi eski-isim profilleriyle, tagline yalniz SOL profilin kuyruk-duzlestirilmis haliyle ve
    altin_sekil golgesiyle boyaniyordu; LEO profili acik-sari (253,210,96), ARIES / LIBRA koyu-turuncu.
    Kapi isim ile mesaj rengini karsilastirir. Duzeltme: tagline plakasi uretildikten sonra murekkep
    cekirdegi medyani, iki ismin ORTAK profilinin medyanina kanal kazanciyla eslenir (desen korunur).
    Yalniz edisyon render'inda (ETKIN), Blue yolu degismez (dogrulamada MB gerilemesi olculdu)."""
    eski = getattr(pilot12.kuyruk_duzlestir, 'eski', pilot12.kuyruk_duzlestir)

    def kuyruk_duzlestir(prof, oran=0.80):
        if DIKIS['etkin']:
            q, (i0, i1) = profil_kenar_kirp(prof)
            return q, len(q) - 1
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
    asil_sekil = getattr(pilot12.altin_sekil, 'eski', pilot12.altin_sekil)
    if DIKIS['etkin']:
        altin_sekil_duz.eski = asil_sekil
        pilot12.altin_sekil = altin_sekil_duz
    else:
        pilot12.altin_sekil = asil_sekil
    tp = getattr(pilot12.tagline_plaka, 'eski', pilot12.tagline_plaka)

    def tagline_plaka(s, S, metin):
        img, bilgi = tp(s, S, metin)
        pr = (S or {}).get('prof') or {}
        if ETKIN['edisyon'] and 'sol' in pr and 'sag' in pr:
            hedef = np.median(ortak_profil(pr['sol'], pr['sag']), 0)
            img, kaz = ton_esle(img, hedef)
            bilgi = {**bilgi, 'ton_kazanci': kaz}
        return img, bilgi
    tagline_plaka.eski = tp
    pilot12.tagline_plaka = tagline_plaka
    if pilot16 is not None and hasattr(pilot16, 'tagline_plaka'):
        pilot16.tagline_plaka = tagline_plaka
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
