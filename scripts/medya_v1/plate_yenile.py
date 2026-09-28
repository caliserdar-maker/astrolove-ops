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
    # QC 1: onayli temizlik kapilari (plate_uret)
    bilgi = {'serit': [a0, a1], 'maske': genis.astype(bool)}
    kapi = pu.temizlik_kapilari(H, yeni, {'y': [y0, y1]}, bilgi)
    rap['temizlik_kapisi'] = kapi
    rap['serit'] = [a0, a1]
    return yeni, rap


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
        print(f"[{n}/{len(isler)}] {ed}_{boy}: {r['durum']} {r.get('sebep') or r.get('hata') or ''} "
              f"hayalet {k.get('hayalet')}/{k.get('hayalet_siniri')} iyilesme {k.get('iyilesme_orani')} "
              f"murekkep {k.get('murekkep_bant')}/{k.get('murekkep_siniri')} doku {k.get('doku_kat')} "
              f"ton {k.get('ton_fark')} slogan {[v.get('glif_farkli_payi') for v in (r.get('plate_slogan_kapisi') or {}).values()]} "
              f"| gecen {g:.0f}s | kalan ~{g / n * (len(isler) - n):.0f}s | %{100 * n // len(isler)}", flush=True)
        (cik / 'PLATE_YENILE.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(cik), f'{a.kok}/PLATE_YENILE', timeout=2400)
    kalan = [k for k, v in rapor.items() if v['durum'] != 'PASS']
    print('KALAN:', kalan)


if __name__ == '__main__':
    main()
