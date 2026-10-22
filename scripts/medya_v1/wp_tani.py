#!/usr/bin/env python3
"""WP katman TANI (1 Eki 2026, salt olcum). Etsy/Prodigi/musteri YOK; PLATES / POD_PRINT salt okunur.

Soru 1: UCTAN UCA isim/mesaj IoU ~0.13 -> metinler mi farkli, yoksa konum / olcek / font mu?
  Duz renk (CI) hat KIMLIK baskisi (kaynagin burc adlari + slogani) ile onayli CI kaynagi, isim ve mesaj
  bandinda: OCR metni, kelime kumesi kutulari (konum, yukseklik, genislik), ham IoU, kume bazinda afin
  hizalama sonrasi IoU (yuksekse fark yerlesim, dusukse font / metin).
Soru 2: plate onarimi neden etkisiz, iz gercek mi?
  Eski olcut (WP kaynaginda yerel kontrast > 26 = glif) ile yeni olcut (CI'dan, dokusuz glif maskesi)
  karsilastirilir; ikisi de yazisiz kontrol seridinde ayrica olculur (olcumun kendi tabani).
  Glif maskeli onarim (plate_onar_glif) sonrasi iz orani.
Cikti: log (TANI satirlari) + Drive TEMP/WP_ORNEK/TANI/<CIFT>/ (JSON + bant goruntuleri).
"""
import argparse, json, re, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import wp_katman as wk                                           # noqa: E402
import wp_ornek as wo                                            # noqa: E402

Image.MAX_IMAGE_PIXELS = None
HEDEF = 'gdrive:ASTROLOVE/TEMP/WP_ORNEK/TANI'
T0 = time.time()


def ocr(m):
    """Murekkep maskesi -> metin (tesseract varsa)."""
    try:
        import pytesseract
    except ImportError:
        return None
    ys, xs = np.nonzero(m)
    if not len(ys):
        return ''
    c = m[max(ys.min() - 10, 0):ys.max() + 11, max(xs.min() - 10, 0):xs.max() + 11]
    im = Image.fromarray(np.where(c, 0, 255).astype(np.uint8))
    h = 60.0 / max(c.shape[0], 1)
    im = im.resize((max(int(im.width * h), 1), 60), Image.LANCZOS)
    t = pytesseract.image_to_string(im, config='--psm 7')
    return t.strip()


def norm_metin(t):
    return re.sub(r'[^A-Z]', '', (t or '').upper())


def kumeler(m, bosluk):
    kol = np.nonzero(m.sum(0) > 0)[0]
    if not len(kol):
        return []
    out, a, b = [], kol[0], kol[0]
    for x in kol[1:]:
        if x - b > bosluk:
            out.append((int(a), int(b) + 1)); a = x
        b = x
    out.append((int(a), int(b) + 1))
    return out


def kutu(m):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def iou(a, b):
    u = (a | b).sum()
    return round(float((a & b).sum() / u), 4) if u else None


def hizali_iou(ms, mg):
    """mg'yi ms'ye afin hizala (faz korelasyonu + ECC); (iou, dx, dy, sx, sy)."""
    Fs = cv2.GaussianBlur(ms.astype(np.float32), (0, 0), 1.5)
    Fg = cv2.GaussianBlur(mg.astype(np.float32), (0, 0), 1.5)
    (sx, sy), _ = cv2.phaseCorrelate(Fs.astype(np.float64), Fg.astype(np.float64))
    M = np.array([[1, 0, sx], [0, 1, sy]], np.float32)
    try:
        _, M = cv2.findTransformECC(Fs, Fg, M, cv2.MOTION_AFFINE,
                                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error:
        pass
    w = cv2.warpAffine(mg.astype(np.float32), M, (ms.shape[1], ms.shape[0]),
                       flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP) > 0.5
    return {'iou': iou(ms, w), 'dx': round(float(M[0, 2]), 2), 'dy': round(float(M[1, 2]), 2),
            'sx': round(float(M[0, 0]), 4), 'sy': round(float(M[1, 1]), 4)}


def bant_tanisi(S_c, B, P_c, y0, y1, k, ad, cik, etiket):
    H, Wd = S_c.shape[:2]
    pad = int(20 * k)
    a, b = max(0, y0 - pad), min(H, y1 + pad)
    x0, x1 = int(Wd * 0.05), int(Wd * 0.95)
    ms = wk.murekkep_maskesi((S_c - P_c)[a:b, x0:x1], kenar=0)
    mg = wk.murekkep_maskesi((B - P_c)[a:b, x0:x1], kenar=0)
    h = max((kutu(ms) or [0, 0, 0, 1])[3] - (kutu(ms) or [0, 0, 0, 0])[1], 1)
    bosluk = max(int(0.45 * h), 6)
    ks, kg = kumeler(ms, bosluk), kumeler(mg, bosluk)
    r = {'satir': [a, b], 'ham_iou': iou(ms, mg), 'bant_hizali': hizali_iou(ms, mg),
         'ocr_kaynak': ocr(ms), 'ocr_hat': ocr(mg), 'kume_kaynak': len(ks), 'kume_hat': len(kg)}
    r['metin_ayni'] = (r['ocr_kaynak'] is not None and
                       norm_metin(r['ocr_kaynak']) == norm_metin(r['ocr_hat']))
    kum = []
    for i in range(min(len(ks), len(kg))):
        c0, c1 = min(ks[i][0], kg[i][0]) - bosluk // 2, max(ks[i][1], kg[i][1]) + bosluk // 2
        c0, c1 = max(c0, 0), min(c1, ms.shape[1])
        s_, g_ = ms[:, c0:c1], mg[:, c0:c1]
        bs, bg = kutu(s_), kutu(g_)
        if not bs or not bg:
            continue
        kum.append({'kaynak_kutu': [bs[0] + c0 + x0, bs[1] + a, bs[2] + c0 + x0, bs[3] + a],
                    'hat_kutu': [bg[0] + c0 + x0, bg[1] + a, bg[2] + c0 + x0, bg[3] + a],
                    'merkez_dx': round((bg[0] + bg[2] - bs[0] - bs[2]) / 2, 1),
                    'ust_dy': bg[1] - bs[1], 'alt_dy': bg[3] - bs[3],
                    'yukseklik_oran': round((bg[3] - bg[1]) / max(bs[3] - bs[1], 1), 4),
                    'genislik_oran': round((bg[2] - bg[0]) / max(bs[2] - bs[0], 1), 4),
                    'ham_iou': iou(s_, g_), 'hizali': hizali_iou(s_, g_)})
    r['kumeler'] = kum
    # goruntu: kaynak / hat / ust uste (kirmizi kaynak, yesil hat)
    ov = np.zeros(ms.shape + (3,), np.uint8)
    ov[..., 0] = ms * 255; ov[..., 1] = mg * 255
    def gri(A):
        return np.repeat(np.clip(A[a:b, x0:x1] @ wk.LUMA, 0, 255).astype(np.uint8)[..., None], 3, 2)
    t = np.concatenate([gri(S_c), np.full((6, ms.shape[1], 3), 255, np.uint8), gri(B),
                        np.full((6, ms.shape[1], 3), 255, np.uint8), ov], 0)
    im = Image.fromarray(t)
    if im.width > 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    im.save(cik / f'TANI_{etiket}_{ad}.png')
    return r


def _metin_ciz(fp, metin, boy, iz, agirlik=None):
    """Metni harf harf (izleme = iz * boy px) ciz; murekkep maskesi (bool)."""
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype(str(fp), boy)
    if agirlik:
        try:
            f.set_variation_by_axes([agirlik])
        except Exception:                                        # noqa: BLE001
            pass
    en = int(sum(f.getlength(c) for c in metin) + abs(iz) * boy * len(metin) + boy * 2)
    im = Image.new('L', (en, int(boy * 2)), 0)
    d = ImageDraw.Draw(im)
    x = boy * 0.5
    for c in metin:
        d.text((x, boy * 0.4), c, font=f, fill=255)
        x += f.getlength(c) + iz * boy
    a = np.asarray(im) > 110
    b = kutu(a)
    return a[b[1]:b[3], b[0]:b[2]] if b else a


def font_tanisi(ms, metin, fontlar):
    """Kaynak glif maskesine (ms, kirpilmis) her fontu en iyi punto + izleme ile uydur; hizali IoU."""
    b = kutu(ms)
    ms = ms[b[1]:b[3], b[0]:b[2]]
    h, w = ms.shape
    sonuc = []
    for fp, ag in fontlar:
        try:
            r0 = _metin_ciz(fp, metin, 200, 0.0, ag)
            boy = max(int(round(200 * h / r0.shape[0])), 8)
            en_iyi = None
            for iz in np.linspace(-0.12, 0.2, 17):
                r = _metin_ciz(fp, metin, boy, float(iz), ag)
                if abs(r.shape[1] - w) > 0.25 * w:
                    continue
                pad = np.zeros((max(h, r.shape[0]) + 20, max(w, r.shape[1]) + 20), bool)
                A = pad.copy(); A[10:10 + h, 10:10 + w] = ms
                B = pad.copy(); B[10:10 + r.shape[0], 10:10 + r.shape[1]] = r
                v = hizali_iou(A, B)
                if en_iyi is None or (v['iou'] or 0) > en_iyi['iou']:
                    en_iyi = {**v, 'punto_px': boy, 'izleme_em': round(float(iz), 3),
                              'en_oran': round(r.shape[1] / w, 3)}
            if en_iyi:
                sonuc.append({'font': Path(fp).name + (f'@{ag}' if ag else ''), **en_iyi})
        except Exception as e:                                   # noqa: BLE001
            sonuc.append({'font': Path(fp).name, 'hata': str(e)[:80]})
    sonuc.sort(key=lambda z: -(z.get('iou') or 0))
    return sonuc[:4]


def fontlar():
    kok = sd.K / 'assets' / 'fonts'
    out = []
    for f in sorted(kok.glob('*.ttf')):
        out.append((f, None))
        if f.name == 'Cinzel.ttf':
            out += [(f, 400), (f, 500), (f, 600), (f, 700)]
    return out


def bos_kayma(ink, y0, y1, H):
    h = y1 - y0
    for d in (h + 40, -(h + 40), 2 * h + 40, -(2 * h + 40), 3 * h + 40, -(3 * h + 40)):
        if 0 <= y0 + d and y1 + d <= H and not ink[y0 + d:y1 + d].any():
            return d
    return None


def cift_boy(cift, boy, P_ed, P_blue, no, cik):
    R = {'cift': cift, 'boy': boy}
    oran = sd.BOY[boy][0]
    renk = 'CHAMPAGNE_IVORY'; ed = sd.RENK_ED[renk]
    S_wp = wk.dizi(sd.pod_kaynak(cift, 'WARM_PARCHMENT', boy)); H, Wd = S_wp.shape[:2]
    S_c_yol = sd.pod_kaynak(cift, renk, boy)
    S_c = wk.boyutla(wk.dizi(S_c_yol), (Wd, H))
    P_c = wk.boyutla(wk.dizi(P_ed.plate(ed, oran, boy)), (Wd, H))
    s1, s2 = cift.split('_', 1)
    x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod',
                      'isim1': s1, 'isim2': s2, 'mesaj': wo.SLOGAN})
    x['receipt'] = f'TANI_{cift}_{boy}'; x['sayfa'] = no[cift]
    with Image.open(S_c_yol) as im:
        x['hedef_px'] = list(im.size)
    d = sd.W / x['receipt']; d.mkdir(parents=True, exist_ok=True)
    r, t = wo.baski(x, S_c_yol, P_ed, P_blue, d)
    R['hat'] = wo.kapi_ozet(r)
    R['hat_metin'] = {'isim1': s1, 'isim2': s2, 'mesaj': wo.SLOGAN}
    if t.get('baski') is None:
        R['durum'] = 'hat baskisi yok'
        return R
    B = wk.boyutla(wk.dizi(t['baski']), (Wd, H))
    k = Wd / 2400.0
    o = r.get('olcum') or {}
    R['olcum'] = {a: o.get(a) for a in ('isim_bant', 'tag_bant', 'sembol_bant', 'sol_isim', 'sag_isim')}
    R['bi'] = {a: r.get(a) for a in ('punto_2400', 'punto_hedef', 'kilit')}
    etiket = f'{cift}_{boy}'
    for ad, alan in (('isim', 'isim_bant'), ('mesaj', 'tag_bant')):
        if o.get(alan):
            R[ad] = bant_tanisi(S_c, B, P_c, int(o[alan][0] * k), int(o[alan][1] * k), k, ad, cik, etiket)

    # ---- font tanisi: kaynak isim / slogan hangi fonta, puntoya, izlemeye uyuyor (hat: Cinzel 500 / EBGaramond-Italic)
    try:
        F = fontlar()
        ft = {}
        if R.get('isim') and len(R['isim'].get('kumeler', [])) >= 3:
            for i, mt in ((0, s1), (2, s2)):
                kk = R['isim']['kumeler'][i]['kaynak_kutu']
                m = wk.murekkep_maskesi((S_c - P_c)[kk[1]:kk[3], kk[0]:kk[2]], kenar=0)
                ft[f'isim_{mt}'] = font_tanisi(m, mt, F)
        if o.get('tag_bant'):
            a0, a1 = int(o['tag_bant'][0] * k) - 10, int(o['tag_bant'][1] * k) + 30
            m = wk.murekkep_maskesi((S_c - P_c)[a0:a1, int(Wd * 0.2):int(Wd * 0.8)], kenar=0)
            n_, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
            m = np.isin(lab, [i for i in range(1, n_) if st[i, 4] >= 30])
            ft['mesaj'] = font_tanisi(m, wo.SLOGAN, F)
        R['font_tanisi'] = ft
    except Exception as e:                                        # noqa: BLE001
        R['font_tanisi'] = {'hata': f'{type(e).__name__}: {e}'}

    # ---- plate: eski olcut vs CI glif olcutu, kontrol seridi, glif maskeli onarim
    y = wo.plate_indir(f'VINTAGE_{boy}.png')
    P_wp0 = wk.boyutla(wk.dizi(y), (Wd, H))
    D_wp = S_wp - P_wp0
    hiz = wk.hizala(S_c - P_c, D_wp, wk.bantlar(wk.murekkep_maskesi(D_wp)))
    et = wo.etiketle(hiz, o, k, H)
    R['hizalama'] = [(h['bant'], h['dx'], h['dy'], h['ecc']) for h in hiz]
    G = wk.glif_maskesi(wk.katman_tasi(S_c - P_c, hiz, (Wd, H)))
    ink = G | wk.murekkep_maskesi(D_wp, kenar=0)
    pb = {a: et[a] for a in ('isim', 'mesaj') if a in et}
    kont = {a: bos_kayma(cv2.dilate(ink.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool),
                         *pb[a], H) for a in pb}
    R['plate_eski_olcut'] = wk.plate_temizlik(P_wp0, S_wp, pb)
    kb = {a: [pb[a][0] + kont[a], pb[a][1] + kont[a]] for a in pb if kont[a] is not None}
    # eski olcut yazisiz kontrol seridinde: S_wp'nin o seridi yazisiz; glif yok -> ayni seridin maskesi
    R['plate_eski_olcut_kontrol'] = {
        a: wk.plate_temizlik(np.roll(P_wp0, -kont[a], axis=0), np.roll(S_wp, -kont[a], axis=0), {a: pb[a]}).get(a)
        for a in kb}
    R['plate_glif_olcut'] = wk.plate_iz(P_wp0, G, pb, kontrol_kayma=kont)
    R['plate_wp_kaynak_glif_olcut'] = wk.plate_iz(S_wp, G, pb)          # kaynakta glif VAR: ust sinir
    ob = {a: et[a] for a in ('kucuk_sembol', 'isim', 'mesaj') if a in et}
    P_on, onr = wk.plate_onar_glif(P_wp0, G, ink, ob)
    R['plate_onarim'] = onr
    R['plate_onarim_sonrasi'] = wk.plate_iz(P_on, G, pb, kontrol_kayma=kont)
    R['durum'] = 'OLCULDU'
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cift', required=True)
    ap.add_argument('--boylar', default='11x14,8x10')
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    cik = sd.W / 'TANI' / a.cift; cik.mkdir(parents=True, exist_ok=True)
    boylar = [b for b in a.boylar.split(',') if b]
    for n, boy in enumerate(boylar, 1):
        try:
            R = cift_boy(a.cift, boy, P_ed, P_blue, no, cik)
        except BaseException as e:                                # noqa: BLE001
            import traceback
            R = {'cift': a.cift, 'boy': boy, 'durum': f'HATA {type(e).__name__}: {e}',
                 'iz': traceback.format_exc()[-2000:]}
        (cik / f'TANI_{boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
        print('TANI', json.dumps(R, ensure_ascii=False, default=str), flush=True)
        g = time.time() - T0
        print(f'[{n}/{len(boylar)}] {a.cift} {boy} {R.get("durum")} | gecen {g:.0f}s | '
              f'kalan ~{g / n * (len(boylar) - n):.0f}s | %{100 * n // len(boylar)}', flush=True)
    sd.rc('copy', str(cik), f'{HEDEF}/{a.cift}', timeout=900)


if __name__ == '__main__':
    main()
