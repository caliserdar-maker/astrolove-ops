#!/usr/bin/env python3
"""PLATE YENILEME: dokulu zeminde slogan temizligi (baski-duzelt, 28 Eyl 2026; Serdar onayi).

Sorun (PLATE_DURUM 28 Eyl): plate_uret'in slogan temizligi dokulu zeminde KALDI (WP hayalet
4.3 -> 26.9, iyilesme orani 6.27; CI 0.445 > 0.35) ve temizlenmemis 25 Eyl medyani PLATES'te
kaldi ya da hic plate yuklenmedi: WP 13 boy, CI 8x10/12x16, MB 12x18/24x36/16x24/20x30.

Yontem: sentetik dolgu YOK. Taban = HAM medyan plate (POD dosyalariyla piksel piksel ayni
zemin). Canva katman kaynakli plate (<ED>_CANVA_<boy>.png, slogan katmani gizli) ile HAM
arasindaki fark slogan GLIFLERINI verir (ayni kaynak; glif disi fark ~0). Yalniz glif pikselleri
(GLIF_PAY genisletme + TUY yumusatma) Canva pikseliyle degistirilir; Canva seridi once HAM'a
hizalanir (faz korelasyonu) ve dusuk frekansli ton farki glif disi piksellerden olculup eklenir.
QC (ikisi de PASS olmadan PLATES'e yazilmaz):
  1) plate_uret.temizlik_kapilari (Serdar'in onayli kapilari: murekkep / doku / ton / hayalet)
  2) siparis_dosyasi.plate_slogan_kapisi, 3 ciftin POD dosyasiyla
Yazmadan once mevcut PLATES/<ED>_<boy>.png -> PLATES/YEDEK_20260928/ (varsa).
Cikti raporu: <kok>/PLATE_YENILE.json + slogan once/sonra kirpimlari.
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plate_uret as pu                                          # noqa: E402
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
PLATES = sd.PLATES
YEDEK = f'{PLATES}/YEDEK_20260928'
CIFTLER = ('AQUARIUS_GEMINI', 'CANCER_LIBRA', 'ARIES_LIBRA')
ED_RENK = {'BLUE': 'MIDNIGHT_BLUE', 'BLACK': 'DEEP_BLACK', 'PURE_WHITE': 'PURE_WHITE',
           'MODERN': 'CHAMPAGNE_IVORY', 'VINTAGE': 'WARM_PARCHMENT'}
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
KAYMA_AZAMI = 12            # Canva-HAM hizasi (px, plate olceginde); asilirsa DUR


def al(ad, hedef):
    hedef.parent.mkdir(parents=True, exist_ok=True)
    sd.rc('copyto', f'{PLATES}/{ad}', str(hedef), timeout=2400)
    return hedef


def glif_maskesi(H, C, k):
    """HAM - Canva farkindan slogan glifleri (alt %32, orta %70 pencerede)."""
    h, w = H.shape[:2]
    y0, y1 = int(h * 0.66), int(h * 0.98)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    d = np.abs(H[y0:y1, x0:x1].astype(np.int16) - C[y0:y1, x0:x1].astype(np.int16)).max(axis=2)
    med = float(np.median(d)); mad = float(np.median(np.abs(d - med))) * 1.4826
    esik = max(med + pu.DOLGU_MAD * mad, pu.DOLGU_ESIK)
    m = (d > esik).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= max(int(pu.MASKE_MIN_ALAN * k * k / 4), 4)
    m = tut[lab]
    satir = m.sum(1)
    if satir.max() == 0:
        return None, {'sebep': 'HAM ile Canva arasinda slogan farki yok', 'esik': esik}
    # slogan = en yogun yatay bant (tek satir metin): tepe satirdan disa dogru bos satira kadar
    tepe = int(np.argmax(satir))
    a, b = tepe, tepe
    bos = max(int(8 * k), 4)
    while a > 0 and satir[max(a - bos, 0):a].sum() > 0:
        a -= 1
    while b < len(satir) - 1 and satir[b:b + bos].sum() > 0:
        b += 1
    bant = np.zeros_like(m)
    bant[a:b + 1] = m[a:b + 1]
    tam = np.zeros(H.shape[:2], bool)
    tam[y0:y1, x0:x1] = bant
    ys, xs = np.nonzero(tam)
    return tam, {'esik': round(esik, 1), 'y': [int(ys.min()), int(ys.max()) + 1],
                 'x': [int(xs.min()), int(xs.max()) + 1], 'glif_px': int(tam.sum())}


def hizala(H, C, y0, y1):
    """Canva'nin HAM'a gore kaymasi: slogan seridinin ustu+alti (glif yok) faz korelasyonu."""
    yuk = y1 - y0
    a0, a1 = max(y0 - 3 * yuk, 0), min(y1 + 3 * yuk, H.shape[0])
    ph = np.float32(H[a0:a1] @ LUMA)
    pc = np.float32(C[a0:a1] @ LUMA)
    ph[y0 - a0:y1 - a0] = ph.mean(); pc[y0 - a0:y1 - a0] = pc.mean()
    (dx, dy), r = cv2.phaseCorrelate(pc, ph)
    return int(round(dx)), int(round(dy)), round(float(r), 3)


def ham_plate(ed, boy, cik):
    """HAM medyan plate; PLATES/HAM'da yoksa 78 POD dosyasindan yeniden (plate_uret yolu)."""
    try:
        return np.asarray(Image.open(al(f'HAM/{ed}_{boy}.png', cik / 'ham.png')).convert('RGB')), 'HAM'
    except RuntimeError:
        renk = ED_RENK[ed]
        yollar = pu.indir(renk, boy)
        with Image.open(yollar[0]) as im:
            px = im.size
        H = pu.karo_ortanca(yollar, px, f'{ed}_{boy}')
        Image.fromarray(H).save(cik / 'ham.png', 'PNG')
        sd.rc('copyto', str(cik / 'ham.png'), f'{PLATES}/HAM/{ed}_{boy}.png', timeout=2400)
        for y in yollar:
            y.unlink(missing_ok=True)
        return H, f'yeniden medyan ({len(yollar)} dosya)'


def yenile(ed, boy, kok, cik):
    t0 = time.time()
    rap = {'plate': f'{ed}_{boy}.png'}
    H, rap['ham_kaynak'] = ham_plate(ed, boy, cik)
    Ci = Image.open(al(f'{ed}_CANVA_{boy}.png', cik / 'canva.png')).convert('RGB')
    if Ci.size != (H.shape[1], H.shape[0]):
        rap['canva_yeniden_ornek'] = [list(Ci.size), [H.shape[1], H.shape[0]]]
        Ci = Ci.resize((H.shape[1], H.shape[0]), Image.LANCZOS)
    yeni, r = melez_plate(H, np.asarray(Ci))
    del Ci
    rap['A'] = {q: v for q, v in r.items()}
    if yeni is None or not r['temizlik_kapisi']['gecti']:
        yb, rb = pw_referans_plate(H, ed, boy, cik)
        rap['B'] = rb
        if yb is not None and (yeni is None or rb['temizlik_kapisi']['gecti']):
            yeni, r = yb, rb
    rap.update(r)
    if yeni is None:
        return {**rap, 'durum': 'KALDI'}
    a0, a1 = r['serit']
    kapi = r['temizlik_kapisi']
    Image.fromarray(np.concatenate([H[a0:a1], yeni[a0:a1]], axis=0)).save(
        cik / f'SLOGAN_{ed}_{boy}_once_sonra.jpg', quality=90)
    yol = cik / f'{ed}_{boy}.png'
    Image.fromarray(yeni).save(yol, 'PNG')
    del H, yeni
    return yaz_qc(ed, boy, yol, kapi, rap, cik, t0)


def melez_plate(H, C):
    """HAM (H) + Canva (C) -> slogansiz plate. (yeni | None, rapor)."""
    rap = {}
    k = H.shape[1] / 2400.0
    m, g = glif_maskesi(H, C, k)
    rap['glif'] = g
    if m is None:
        return None, {**rap, 'sebep': g['sebep']}
    y0, y1 = g['y']
    dx, dy, r = hizala(H, C, y0, y1)
    rap['hiza'] = {'dx': dx, 'dy': dy, 'r': r}
    if abs(dx) > KAYMA_AZAMI or abs(dy) > KAYMA_AZAMI:
        return None, {**rap, 'sebep': f'Canva hizasi {dx},{dy} > {KAYMA_AZAMI}'}
    if dx or dy:
        C = np.roll(C, (dy, dx), axis=(0, 1))
        m, g = glif_maskesi(H, C, k)
        rap['glif'] = g
        if m is None:
            return None, {**rap, 'sebep': g['sebep']}
        y0, y1 = g['y']
    # serit: glif bandi + pay; islemler yalniz seritte (30x40 = 9000 px)
    yuk = y1 - y0
    pay = max(int(yuk * 0.35), 8)
    a0, a1 = max(y0 - pay, 0), min(y1 + pay, H.shape[0])
    ms = m[a0:a1].astype(np.uint8)
    # genisletme = glif payi + tuy payi: yumusak kenar (TUY) glif sacagini HAM'dan birakmasin
    # (sahte veri: koyu zeminde altin glif, yalniz GLIF_PAY ile kenar p99 17).
    ker = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * max(int(round((pu.GLIF_PAY + 2 * pu.TUY) * k)), 1) + 1,) * 2)
    genis = cv2.dilate(ms, ker)
    alfa = np.clip(cv2.GaussianBlur(genis.astype(np.float32), (0, 0), max(pu.TUY * k, 0.8)), 0, 1)
    # dusuk frekansli ton: glif disi piksellerden normalize bulaniklik
    Hs, Cs = H[a0:a1].astype(np.float32), C[a0:a1].astype(np.float32)
    w = 1.0 - np.clip(cv2.dilate(genis, ker).astype(np.float32), 0, 1)
    sg = max(pu.TON_SIGMA * k, 3.0)
    den = cv2.GaussianBlur(w, (0, 0), sg) + 1e-6
    lf = np.dstack([cv2.GaussianBlur((Hs[..., c] - Cs[..., c]) * w, (0, 0), sg) / den for c in range(3)])
    dolgu = Cs + lf
    yeni = H.copy()
    yeni[a0:a1] = np.clip(Hs * (1 - alfa[..., None]) + dolgu * alfa[..., None], 0, 255).astype(np.uint8)
    # QC 1: onayli temizlik kapilari (plate_uret), sloganin kendi sutunlarinda
    rap['temizlik_kapisi'], rap['temizlik_kapisi_tam_en'] = yerel_qc(H, yeni, [a0, a1], genis.astype(bool))
    rap['serit'] = [a0, a1]
    rap['yol'] = 'A: HAM + Canva glif dolgusu'
    return yeni, rap


def yerel_qc(H, yeni, serit, maske):
    """maske: seridin (a0:a1) glif maskesi.
    plate_uret.temizlik_kapilari, sloganin SUTUNLARINDA (x0-pay .. x1+pay, pay = serit yuksekligi).

    28 Eyl olcumu (kosu 36445106079): tam en olcumde ~gm bandin kenarlarini (parsomen vinyeti,
    cerceve) da kapsiyor; slogansiz seritlerde bile 'hayalet' 26-28 (WP), 11.7-12.1 (CI) cikiyor.
    O seviyede temizlenmis plate zemine esit oldugu halde iyilesme orani > 0.35 kaliyor (WP ONCE
    7.7 -> 28.5: koyu slogan murekkebi vinyet farkini bastiriyordu). Esikler AYNI; yalniz olcum
    penceresi sloganin kendi sutunlarina iner ve hayalet, zeminin 2. derece yuzeyinden (vinyet)
    sapma olarak olculur (ayni olcu ONCE ve taban seritlerine de uygulanir). Tam en sonucu da
    rapora yazilir.
    """
    a0, a1 = serit
    k = H.shape[1] / 2400.0
    xs = np.nonzero(maske.any(axis=0))[0]
    pay = a1 - a0
    c0, c1 = max(int(xs.min()) - pay, 0), min(int(xs.max()) + 1 + pay, H.shape[1])
    tam = pu.temizlik_kapilari(H, yeni, None, {'serit': [a0, a1], 'maske': maske})
    yer = pu.temizlik_kapilari(H[:, c0:c1], yeni[:, c0:c1], None,
                               {'serit': [a0, a1], 'maske': maske[:, c0:c1], 'k': k,
                                'hayalet_trend': True})
    yer['sutun'] = [c0, c1]
    return yer, {q: tam.get(q) for q in ('gecti', 'hayalet', 'hayalet_ONCE', 'hayalet_siniri',
                                          'iyilesme_orani', 'murekkep_kat', 'doku_kat', 'ton_fark')}


def hiza_incelt(H, ref, r0, r1, dy0, dx0, k, ara=12):
    """PW referans maskesini HAM'in kendi murekkep maskesine (onayli yerel kontrast) 2B oturtur.

    28 Eyl (WP A4): hiza_bul yatay profil korelasyonu 0.05 -> dx guvenilmez; kayik maske slogan
    kenarini birakiyor (murekkep 4.37 kat). Aday (dy, dx): hiza_bul sonucu ve (0, 0) cevresinde
    +-ara px; olcut: ortusen murekkep pikseli (ref & HAM maskesi) en cok olan."""
    a = max(int(round(ara * k)), 2)
    lo = max(min(dy0, 0) - a, -r0)
    hi = min(max(dy0, 0) + a, H.shape[0] - r1)
    L = H[r0 + lo:r1 + hi].astype(np.float32) @ pu.LUMA
    E = pu.yerel_maske(L, pu.MASKE_YARICAP * k, pu.MASKE_ESIK, pu.MASKE_MIN_ALAN * k * k)
    h = r1 - r0
    en, sec = -1, (dy0, dx0)
    dxs = sorted(set(range(-a, a + 1)) | set(range(dx0 - a, dx0 + a + 1)))
    for dy in range(lo, hi + 1):
        e = E[dy - lo:dy - lo + h]
        for dx in dxs:
            s_ = int((np.roll(ref, dx, axis=1) & e).sum())
            if s_ > en:
                en, sec = s_, (dy, dx)
    return {'dy': int(sec[0]), 'dx': int(sec[1]), 'hiza_bul': [int(dy0), int(dx0)],
            'ortusme': round(en / max(int(ref.sum()), 1), 3)}


def pw_referans_plate(H, ed, boy, cik):
    """B yolu: plate_uret'in onayli yontemi (PURE_WHITE HAM'dan referans glif maskesi + hiza +
    bandin kendi ust/alt seritlerinden dolgu). Canva disa aktarimi HAM'dan farkliysa (WP 11x14 / A4:
    glif esigi 53-63, hiza r 0.53) ya da A yolu kapidan gecmezse denenir."""
    k = H.shape[1] / 2400.0
    Pw = np.asarray(Image.open(al(f'HAM/PURE_WHITE_{boy}.png', cik / 'pw.png')).convert('RGB'))
    (cik / 'pw.png').unlink(missing_ok=True)
    if Pw.shape != H.shape:
        return None, {'sebep': f'PW HAM boyutu {Pw.shape} != {H.shape}'}
    bant = pu.slogan_bandi(Pw)
    if bant is None:
        return None, {'sebep': 'PW HAM slogan bandi bulunamadi'}
    _, tb = pu.slogan_temizle(Pw, bant)
    if tb is None or 'ham_maske' not in tb:
        return None, {'sebep': f"PW temizligi: {(tb or {}).get('sebep')}"}
    r0, r1 = tb['serit']
    ref, gor = tb['ham_maske'], Pw[r0:r1].copy()
    del Pw
    hz = pu.hiza_bul(gor, H, r0, r1, azami=int(round(pu.HIZA_AZAMI * k)))
    hz.update(hiza_incelt(H, ref, r0, r1, hz['dy'], hz['dx'], k))
    b2 = dict(bant)
    b2['y'] = [bant['y'][0] + hz['dy'], bant['y'][1] + hz['dy']]
    maske = ref if hz['dx'] == 0 else np.roll(ref, hz['dx'], axis=1)
    yeni, t2 = pu.slogan_temizle(H, b2, ref_maske=maske)
    if yeni is None:
        return None, {'sebep': f"slogan_temizle: {t2.get('sebep')}", 'hiza': hz}
    a0, a1 = t2['serit']
    kapi, kapi_tam = yerel_qc(H, yeni, [a0, a1], t2['maske'])      # maske: serit (a0:a1) boyutu
    return yeni, {'yol': 'B: plate_uret PW referans maskesi', 'hiza': hz, 'serit': [a0, a1],
                  'glif_px': t2.get('glif_px'), 'dolgu_esik': t2.get('dolgu_esik'),
                  'temizlik_kapisi': kapi, 'temizlik_kapisi_tam_en': kapi_tam}


def yaz_qc(ed, boy, yol, kapi, rap, cik, t0):
    # QC 2: siparis plate slogan kapisi, 3 cift
    renk = ED_RENK[ed]
    sk = {}
    for cift in CIFTLER:
        try:
            kay = sd.pod_kaynak(cift, renk, boy)
            sk[cift] = sd.plate_slogan_kapisi(kay, yol, sd.RENK_ED[renk])
            kay.unlink(missing_ok=True)
        except Exception as e:                                    # noqa: BLE001
            sk[cift] = {'gecti': False, 'sebep': f'{type(e).__name__}: {e}'}
    rap['plate_slogan_kapisi'] = {c: {q: v.get(q) for q in ('gecti', 'glif_farkli_payi', 'sebep')}
                                  for c, v in sk.items()}
    gecti = bool(kapi['gecti']) and all(v.get('gecti') for v in sk.values())
    rap['durum'] = 'PASS' if gecti else 'KALDI'
    if gecti:
        mevcut = {x.strip() for x in sd.rc('lsf', PLATES, '--files-only', '--include', f'{ed}_{boy}.png').split()}
        if f'{ed}_{boy}.png' in mevcut:
            sd.rc('copyto', f'{PLATES}/{ed}_{boy}.png', f'{YEDEK}/{ed}_{boy}.png', timeout=2400)
            rap['yedek'] = f'YEDEK_20260928/{ed}_{boy}.png'
        sd.rc('copyto', str(yol), f'{PLATES}/{ed}_{boy}.png', timeout=2400)
        rap['yazildi'] = f'PLATES/{ed}_{boy}.png'
    for f in (cik / 'ham.png', cik / 'canva.png', yol):
        f.unlink(missing_ok=True)
    rap['sure_sn'] = round(time.time() - t0, 1)
    return rap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--isler', required=True, help='VINTAGE:8x10,11x14;MODERN:12x16')
    ap.add_argument('--kok', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    cik = sd.W / '_plate_yenile'; cik.mkdir(parents=True, exist_ok=True)
    isler = [(p.split(':')[0], b) for p in a.isler.split(';') for b in p.split(':')[1].split(',')]
    rapor, T0 = {}, time.time()
    for n, (ed, boy) in enumerate(isler, 1):
        try:
            r = yenile(ed, boy, a.kok, cik)
        except Exception as e:                                    # noqa: BLE001
            import traceback
            r = {'plate': f'{ed}_{boy}.png', 'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}',
                 'iz': traceback.format_exc()[-800:]}
        rapor[f'{ed}_{boy}'] = r
        k = r.get('temizlik_kapisi') or {}
        g = time.time() - T0
        print(f"[{n}/{len(isler)}] {ed}_{boy}: {r['durum']} [{r.get('yol')}] {r.get('sebep') or r.get('hata') or ''} "
              f"hayalet {k.get('hayalet')}/{k.get('hayalet_siniri')} iyilesme {k.get('iyilesme_orani')} "
              f"murekkep {k.get('murekkep_bant')}/{k.get('murekkep_siniri')} doku {k.get('doku_kat')} "
              f"ton {k.get('ton_fark')} slogan {[v.get('glif_farkli_payi') for v in (r.get('plate_slogan_kapisi') or {}).values()]} "
              f"| gecen {g:.0f}s | kalan ~{g / n * (len(isler) - n):.0f}s | %{100 * n // len(isler)}", flush=True)
        (cik / 'PLATE_YENILE.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(cik), f'{a.kok}/PLATE_YENILE', timeout=2400)
    kalan = [k for k, v in rapor.items() if v['durum'] != 'PASS']
    print('KALAN:', kalan)
    wp = [k.split('_', 1)[1] for k, v in rapor.items() if k.startswith('VINTAGE_') and v.get('yazildi')]
    if wp:
        damga = a.kok.rstrip('/').split('/')[-1].replace('BASKI_DUZELT_', '')
        yayin_durum(f"WP hazır: {damga}, {', '.join(wp)} (PLATES/VINTAGE_<boy>.png)", cik)


YAYIN_DURUM = 'gdrive:ASTROLOVE/TEMP/YAYIN_DURUM.md'


def yayin_durum(satir, cik):
    """TEMP/YAYIN_DURUM.md'ye tek satir ekler (gorsel oturumu WP plate'lerini bekliyor)."""
    try:
        eski = sd.rc('cat', YAYIN_DURUM)
    except RuntimeError:
        eski = ''
    f = cik / 'YAYIN_DURUM.md'
    f.write_text(eski + ('' if not eski or eski.endswith('\n') else '\n') + satir + '\n')
    sd.rc('copyto', str(f), YAYIN_DURUM)
    f.unlink(missing_ok=True)
    print('YAYIN_DURUM:', satir, flush=True)


if __name__ == '__main__':
    main()
