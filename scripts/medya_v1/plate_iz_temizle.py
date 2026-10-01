#!/usr/bin/env python3
"""PLATE MESAJ BANDI IZ TEMIZLIGI (Serdar 1 Eki 2026, siparis 4188621967 hayalet yazi).

Bulgu: medyan plate'lerin mesaj bandinda eski motto ("Two Souls One Bond") silik izi kaldi (78 ciftte ayni yerde
oldugu icin ortancada kayboldu sanildi; zayif kopyasi kaldi). Siparis ciktisinda eski slogan silinen yere plate
gelir -> yeni mesajin arkasinda iz. plate_slogan_kapisi glif PAYINA baktigi icin zayif izi kacirdi.

Yontem (yalniz mesaj bandi, yalniz eski glif pikselleri): eski glif maskesi = 3 cift kaynaginin bantta yerel
kontrast maskelerinin birlesimi (+IZ_PAY); bu pikseller bandin KENDI glifsiz pikselinden normalize dusuk frekans
tonla doldurulur (sentetik doku YOK). Bant / maske disi BIREBIR ayni. Sembol, halka, isim bandi degismez.
QC (hepsi PASS olmadan PLATES'e yazilmaz): (1) eski_metin_izi_kapisi 3 ciftte PASS, (2) plate_slogan_kapisi 3 ciftte
PASS, (3) maske disi piksel farki 0. Yazmadan once PLATES/<ED>_<boy>.png -> PLATES_YEDEK_IZ_<damga>/, yazdiktan sonra
geri okunup sha256 karsilastirilir. --yaz verilmezse yalniz olcer ve kesit uretir (salt okur)."""
import argparse, hashlib, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
CIFTLER = ('CANCER_LEO', 'CANCER_LIBRA', 'ARIES_LEO')
MASKE_PAY = 4                 # 2400 px: eski glif maskesi genisletmesi (iz glifin yumusak kenarini da kapsar)
KAYMA = 60                    # 2400 px: plate'te iz / maske hiza aramasi


def bayt_png(a):
    import io
    b = io.BytesIO(); Image.fromarray(a).save(b, 'PNG'); return b.getvalue()


def temizle(plate_a, kaynaklar, ed):
    """plate_a: HxWx3 uint8 (tam cozunurluk). kaynaklar: [bayt]. Doner: yeni plate, maske, bilgi."""
    from pilot6 import LUMA
    eu = sd._mod('edisyon_uret')
    H, Wd = plate_a.shape[:2]
    k = Wd / 2400.0
    pl_png = sd.W / f'_iz_plate_{time.time_ns()}.png'
    Image.fromarray(plate_a).save(pl_png)
    bantlar, M24 = [], None
    for kb in kaynaklar:
        pk = sd.plate_slogan_kapisi(kb, pl_png, ed)
        if not pk.get('tag_bant'):
            continue
        sd.olcek_kur(2400)
        im = Image.open(__import__('io').BytesIO(kb)).convert('RGB')
        L = np.asarray(im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)).astype(np.float32) @ LUMA
        y0, y1 = pk['tag_bant'][0] - 12, pk['tag_bant'][1] + 12
        x0, x1 = max(pk['tag_x'][0] - 40, 0), min(pk['tag_x'][1] + 40, 2400)
        g = np.zeros(L.shape, bool)
        g[y0:y1, x0:x1] = eu.edisyon_maske(L, float(np.median(L)) > 128)[y0:y1, x0:x1]
        M24 = g if M24 is None else (M24[:min(len(M24), len(g))] | g[:min(len(M24), len(g))])
        bantlar.append([y0, y1, x0, x1])
    pl_png.unlink(missing_ok=True)
    if M24 is None:
        return None, None, {'sebep': 'mesaj bandi olculemedi'}
    # 1 Eki (MB 16x20 / 11x14 QC FAIL): Blue plate sayfaya bg hizasiyla (olcek, dx, dy) oturur; plate koordinatinda
    # iz, sayfa koordinatindaki eski glif maskesinden kayik olabilir. Kayma, plate bandinin yerel sapmasi ile maskenin
    # korelasyonundan (+-KAYMA px, 2400) bulunur; diger edisyonlarda ~0.
    Lp = np.asarray(Image.fromarray(plate_a).resize((2400, round(H * 2400 / Wd)), Image.LANCZOS)).astype(np.float32) @ LUMA
    ys = np.nonzero(M24.any(1))[0]; xs = np.nonzero(M24.any(0))[0]
    ty0, ty1, tx0, tx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    K = KAYMA
    r0, r1 = max(ty0 - K, 0), min(ty1 + K, Lp.shape[0]); c0, c1 = max(tx0 - K, 0), min(tx1 + K, 2400)
    reg = Lp[r0:r1, c0:c1]
    D = np.abs(reg - cv2.medianBlur(np.clip(reg, 0, 255).astype(np.uint8), 21).astype(np.float32))
    T = M24[ty0:ty1, tx0:tx1].astype(np.float32)
    kay = (0, 0)
    if D.shape[0] > T.shape[0] and D.shape[1] > T.shape[1]:
        sk = cv2.matchTemplate(D.astype(np.float32), T.astype(np.float32), cv2.TM_CCORR)
        _, _, _, mx = cv2.minMaxLoc(sk)
        kay = (int(mx[0] + c0 - tx0), int(mx[1] + r0 - ty0))
        M24 = np.roll(np.roll(M24, kay[1], 0), kay[0], 1)
    M24 = cv2.dilate(M24.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * MASKE_PAY + 1,) * 2))
    M = cv2.resize(M24, (Wd, H), interpolation=cv2.INTER_NEAREST) > 0
    y0 = int((min(b[0] for b in bantlar) - K) * k) - int(40 * k); y1 = int((max(b[1] for b in bantlar) + K) * k) + int(40 * k)
    y0, y1 = max(y0, 0), min(y1, H)
    P = plate_a.astype(np.float32)
    kes = P[y0:y1]; Mb = M[y0:y1]
    tw = (~Mb).astype(np.float32)
    sg = max(14.0 * k, 3.0)
    den = cv2.GaussianBlur(tw, (0, 0), sg)
    lf = np.dstack([cv2.GaussianBlur(kes[..., c] * tw, (0, 0), sg) / np.maximum(den, 1e-3) for c in range(3)])
    yeni = kes.copy()
    yeni[Mb] = lf[Mb]
    out = plate_a.copy()
    out[y0:y1] = np.clip(np.round(yeni), 0, 255).astype(np.uint8)
    return out, M, {'bant_satir': [y0, y1], 'maske_px': int(M.sum()), 'bantlar_2400': bantlar, 'kayma_2400': list(kay)}


def kesit(once, sonra, M, hedef, satir):
    y0, y1 = satir
    a, b = once[y0:y1], sonra[y0:y1]
    def ger(x):
        L = x.astype(np.float32).mean(2)
        lo, hi = np.percentile(L, 1), np.percentile(L, 99)
        return np.clip((L - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    ara = np.full((10, a.shape[1], 3), 128, np.uint8)
    g = np.concatenate([a, ara, b, ara, np.dstack([ger(a)] * 3), ara, np.dstack([ger(b)] * 3)], 0)
    Image.fromarray(g).save(hedef, 'JPEG', quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--renkler', default='MIDNIGHT_BLUE,DEEP_BLACK,PURE_WHITE,CHAMPAGNE_IVORY')
    ap.add_argument('--boylar', default='16x20,18x24,24x36,11x14,A2')
    ap.add_argument('--yaz', action='store_true', help='QC PASS ise PLATES\'e yaz (yedekli)')
    ap.add_argument('--atla_yazilmis', default='', help='bu yedek klasorunde yedegi olan plate atlanir (yazilmis)')
    ap.add_argument('--cikti', default='plate_iz')
    a = ap.parse_args()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    sd.kisisel_hazirla()
    P_ed = sd.EdisyonPoster()
    damga = time.strftime('%Y%m%d_%H%M', time.gmtime())
    R = []
    for renk in a.renkler.split(','):
        for boy in a.boylar.split(','):
            ed = sd.RENK_ED[renk]; oran = sd.BOY[boy][0]
            r = {'renk': renk, 'boy': boy}
            try:
                yol = Path(P_ed.plate(ed, oran, boy))
                ad = f'{ed.upper()}{sd.PLATE_EK}_{boy}.png'
                r['plate'] = ad
                yd = f'{sd.PLATES.rsplit("/", 1)[0]}/{a.atla_yazilmis}'
                if a.atla_yazilmis and sd.rc('lsf', yd, '--include', ad).strip() and \
                        sd.rc('md5sum', f'{yd}/{ad}').split()[:1] != sd.rc('md5sum', f'{sd.PLATES}/{ad}').split()[:1]:
                    r['atlandi'] = f'zaten yazilmis ({a.atla_yazilmis})'; r['qc'] = {'gecti': True}; r['yazildi'] = True
                    R.append(r); print('PLATE_IZ', json.dumps(r), flush=True); continue
                once = np.asarray(Image.open(yol).convert('RGB'))
                kb = [sd.pod_kaynak(c, renk, boy).read_bytes() for c in CIFTLER]
                sonra, M, bil = temizle(once, kb, ed)
                r.update(bil)
                if sonra is None:
                    raise RuntimeError(bil.get('sebep'))
                sonra_png = cik / f'{renk}_{boy}_{ad}'
                Image.fromarray(sonra).save(sonra_png)
                qc = {'iz_once': [], 'iz_sonra': [], 'slogan': []}
                dx, dy = bil.get('kayma_2400') or (0, 0)
                for c, b in zip(CIFTLER, kb):
                    pk = sd.plate_slogan_kapisi(b, sonra_png, ed)
                    qc['slogan'].append(pk.get('gecti'))
                    bos = np.zeros(sonra.shape[:2], bool)
                    bk, tb, tx = b, pk['tag_bant'], pk['tag_x']
                    if (dx, dy) != (0, 0):                # iz plate koordinatinda: kaynak maskesi bulunan kaymayla olculur
                        from PIL import ImageChops
                        kk = sonra.shape[1] / 2400.0
                        im_ = Image.open(__import__('io').BytesIO(b)).convert('RGB')
                        bk = bayt_png(np.asarray(ImageChops.offset(im_, int(round(dx * kk)), int(round(dy * kk)))))
                        tb, tx = [tb[0] + dy, tb[1] + dy], [tx[0] + dx, tx[1] + dx]
                    for ad_, pl in (('iz_once', once), ('iz_sonra', sonra)):
                        iz = sd.eski_metin_izi_kapisi(Image.fromarray(pl), bk, tb, tx, bos)
                        qc[ad_].append(iz.get('fazla'))
                fark = np.abs(sonra.astype(np.int16) - once.astype(np.int16)).max(2) > 0
                qc['maske_disi_degisen_px'] = int((fark & ~M).sum())
                qc['gecti'] = bool(all(qc['slogan']) and all(f is not None and f <= sd.IZ_ESIK for f in qc['iz_sonra'])
                                   and qc['maske_disi_degisen_px'] == 0)
                r['qc'] = qc
                kesit(once, sonra, M, cik / f'KESIT_{renk}_{boy}.jpg', bil['bant_satir'])
                if a.yaz and qc['gecti']:
                    sd.rc('copyto', f'{sd.PLATES}/{ad}', f'{sd.PLATES}_YEDEK_IZ_{damga}/{ad}', timeout=1800)
                    sd.rc('copyto', str(sonra_png), f'{sd.PLATES}/{ad}', timeout=1800)
                    geri = cik / f'_geri_{ad}'
                    sd.rc('copyto', f'{sd.PLATES}/{ad}', str(geri), timeout=1800)
                    r['yazildi'] = hashlib.sha256(geri.read_bytes()).hexdigest() == hashlib.sha256(sonra_png.read_bytes()).hexdigest()
                    r['yedek'] = f'PLATES_YEDEK_IZ_{damga}/{ad}'
                    geri.unlink(missing_ok=True)
                for c in CIFTLER:
                    (sd.W / 'pod' / c / renk / f'{boy}.jpg').unlink(missing_ok=True)
            except BaseException as e:                            # noqa: BLE001
                r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
            R.append(r)
            print('PLATE_IZ', json.dumps({q: r.get(q) for q in ('renk', 'boy', 'plate', 'maske_px', 'kayma_2400', 'qc', 'yazildi', 'hata')}), flush=True)
    (cik / 'PLATE_IZ.json').write_text(json.dumps(R, indent=1, default=str))
    kotu = [f"{r['renk']} {r['boy']}" for r in R if not (r.get('qc') or {}).get('gecti') or (a.yaz and not r.get('yazildi'))]
    print('SONUC', 'PASS' if not kotu else f'FAIL {kotu}', flush=True)
    sys.exit(1 if kotu else 0)


if __name__ == '__main__':
    main()
