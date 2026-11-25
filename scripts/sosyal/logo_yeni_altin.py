#!/usr/bin/env python3
"""Magaza logosu, yeni altin (Serdar 25 Kas 2026 18:43): sekil ve kompozisyon canli logoyla AYNI, yalniz altin doku yenilenir.

Yontem (uydurma yok, depodaki yontem): sosyal/pin_v6/pin_uret.py PosterR._gold_ramp -> altin pikselleri parlakliga gore
siralanir, 256 kantil = altin rampasi. Burada:
  - KAYNAK sekil: canli Etsy dukkan ikonu (ICON_LIVE_CAPTURE_1254; ETSY_CANLI_LOGO_180 ile ayni gorsel, QC'de olculur);
  - YENI altin rampasi: Serdar onayli PIN_ALTIN_CANCER_LEO.jpg birlesik sembolunun altin piksellerinden (_gold_ramp ile ayni);
  - eski altinin her pikseli, eski altin icindeki parlaklik SIRASINA (kantil) gore yeni rampadaki ayni kantilin rengini alir
    (sira korunur -> kurdele burgusu, golge ve kenar isigi ayni yerde kalir; yalniz renk/doku yeni altina doner);
  - kenar pikselleri altin alfasi ile zemine karisir; zemin ve golge pikselleri AYNEN kalir;
  - canli yakalamadaki beyaz yuvarlak kose (Etsy ekran kirpmasi) kare zemine tamamlanir: koseler, ayni yaricaptaki
    zemin halkasinin olculen medyan rengiyle doldurulur (radyal profil, pin78_altin_pin.profil yontemi).
Cikti: LOGO_YENI_ALTIN_3000.png (kaynak, 3000x3000) + kiyas ve QC JSON.
Kullanim: logo_yeni_altin.py --logo ICON_LIVE_CAPTURE_1254.png --logo180 ETSY_CANLI_LOGO_180.png --pin PIN_ALTIN_CANCER_LEO.jpg --out DIR
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageFilter

PIN_PANEL = (104, 258, 897, 1312)       # pin78_altin_pin PX0, PY0, PX1, PY1
PIN_SEMBOL_Y = (34, 830)                # panel ici sembol bandi (pin78_altin_pin.kutular)
LUM = np.array([0.299, 0.587, 0.114])


def altin_maske(p):                      # pin78_altin_pin.altin_maske ile ayni
    return (p[..., 0] > 110) & (p[..., 0] > p[..., 2] + 50)


def ramp(px):
    """PosterR._gold_ramp: parlakliga gore sirala, 256 kantil, dikey 9'luk yumusatma."""
    px = px[np.argsort(px @ LUM)]
    q = np.linspace(0, len(px) - 1, 256).astype(int)
    r = px[q].astype(float)
    k = np.array([1, 8, 28, 56, 70, 56, 28, 8, 1], float); k /= k.sum()   # 9'luk Gauss yaklasigi
    pad = np.pad(r, ((4, 4), (0, 0)), mode='edge')
    return np.stack([np.convolve(pad[:, c], k, 'valid') for c in range(3)], -1)


def pin_rampasi(pin):
    a = np.asarray(Image.open(pin).convert('RGB')).astype(int)
    p = a[PIN_PANEL[1]:PIN_PANEL[3], PIN_PANEL[0]:PIN_PANEL[2]][PIN_SEMBOL_Y[0]:PIN_SEMBOL_Y[1]]
    m = altin_maske(p)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 0   # ic altin (alpha ~1)
    return ramp(p[m].astype(float)), int(m.sum())


def alfa(a):
    """altin alfasi: R-B farkina gore yumusak (zemin lacivert R-B < 0; tam altin R-B >= 70)."""
    d = a[..., 0] - a[..., 2]
    return np.clip((d - 20) / 50.0, 0, 1) * (a[..., 0] > 60)


def kose_doldur(a):
    """canli yakalamadaki beyaz kose disini kare zemine tamamla (ayni yaricap halkasinin medyan rengi)."""
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    kose = (np.minimum(xx, W - 1 - xx) < 0.08 * W) & (np.minimum(yy, H - 1 - yy) < 0.08 * H)   # yalniz 4 kose bolgesi
    beyaz = (a.min(2) > 60) & kose      # beyaz + gri kenar yumusatmasi; altin parlamalari (kose disi) korunur
    r = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2)
    kenar = (np.minimum(xx, W - 1 - xx) < 0.01 * W) | (np.minimum(yy, H - 1 - yy) < 0.01 * H)
    kose_genis = (np.minimum(xx, W - 1 - xx) < 0.12 * W) & (np.minimum(yy, H - 1 - yy) < 0.12 * H)
    zemin = (~kose_genis) & (~kenar) & (alfa(a) == 0) & (a.sum(2) < 200)   # kose ve kenar cizgisi olcume girmez
    out = a.copy()
    kut = np.arange(0, r.max() + 4, 4)
    rr = r[zemin]; zz = a[zemin]
    med = []
    for i in range(len(kut) - 1):
        m = (rr >= kut[i]) & (rr < kut[i + 1])
        med.append(np.median(zz[m], 0) if m.sum() > 30 else None)
    son = None
    for i in range(len(med)):            # bos halkalar komsudan (pin78_altin_pin.profil gibi)
        if med[i] is None:
            med[i] = son
        son = med[i]
    for i in range(len(med) - 2, -1, -1):
        if med[i] is None:
            med[i] = med[i + 1]
    med = np.array(med, float)
    kb = np.asarray(Image.fromarray((beyaz * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))) > 0   # kenar hale de
    idx = np.clip((r[kb] / 4).astype(int), 0, len(med) - 1)
    out[kb] = med[idx]
    # sinir dikisini kapatmak icin: radyal dolgu taban, ustune OpenCV Telea inpaint (sinirdaki komsu zeminden surekli gecis)
    import cv2
    out = cv2.inpaint(np.clip(out, 0, 255).astype(np.uint8), (kb * 255).astype(np.uint8), 25, cv2.INPAINT_TELEA).astype(float)
    return out, int(kb.sum())


def uret(logo, pin, boy=3000):
    src = Image.open(logo).convert('RGB')
    a = np.asarray(src.resize((boy, boy), Image.LANCZOS)).astype(float)
    a, kose_px = kose_doldur(a)
    al = alfa(a)
    ic = al >= 0.98
    L = a @ LUM
    yeni, n_pin = pin_rampasi(pin)
    eski_r = ramp(a[ic])
    # 1) parlaklik egrisi (surekli, monoton): eski ic altinin parlaklik kantili -> pin altininda ayni kantilin parlakligi
    Lc = eski_r @ LUM; Lc = np.maximum.accumulate(Lc)
    Lp = yeni @ LUM; Lp = np.maximum.accumulate(Lp)
    x = np.arange(256, dtype=float)
    q = np.interp(x, Lc + np.arange(256) * 1e-6, np.arange(256))            # x'in eski rampadaki kantil konumu
    f = np.interp(q, np.arange(256), Lp)
    alt = x < Lc[0]; f[alt] = x[alt] * Lp[0] / max(Lc[0], 1)                 # en koyu golgeler oranla (0 -> 0)
    ust = x > Lc[-1]; f[ust] = np.minimum(255, Lp[-1] + (x[ust] - Lc[-1]))
    hedef = np.interp(L, x, f)
    # 2) renk: pin rampasinda hedef parlakliktaki renk (rampa altindaysa ilk rengin olceklenmesi)
    renk = np.stack([np.interp(hedef, Lp + np.arange(256) * 1e-6, yeni[:, c]) for c in range(3)], -1)
    olc = np.clip(hedef / max(Lp[0], 1), 0, 1)[..., None]
    renk = np.where((hedef < Lp[0])[..., None], yeni[0] * olc, renk)
    # 3) karisim: sicak (altin) pay R-B ile surekli; lacivert zemin (R-B < 10) degismez
    al = np.clip((a[..., 0] - a[..., 2] - 10) / 40.0, 0, 1)
    # 1254 kaynak 2.4x buyutuldu; piksel gurultusunu tasimamak icin degisim (delta) 1.5 px Gauss ile yumusatilir
    from scipy.ndimage import gaussian_filter
    delta = np.stack([gaussian_filter(al * (renk[..., c] - a[..., c]), 1.5) for c in range(3)], -1)
    out = a + delta
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    bilgi = {'kaynak_boyut': list(src.size), 'cikti_boyut': [boy, boy], 'kose_doldurulan_px': kose_px,
             'altin_ic_px': int(ic.sum()), 'pin_altin_px': n_pin,
             'yeni_ramp_ort': yeni.mean(0).round(1).tolist(), 'eski_ramp_ort': eski_r.mean(0).round(1).tolist()}
    return Image.fromarray(out), bilgi, yeni, eski_r


def qc(out_im, logo, logo180, pin, yeni):
    S = []
    k = lambda ad, ok, d='': S.append({'kapi': ad, 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': str(d)})
    o = np.asarray(out_im).astype(float)
    k('boyut >= 3000', min(out_im.size) >= 3000, out_im.size)
    # 1) canli 180 ile ayni gorsel mi (kaynak dogrulama)
    c180 = np.asarray(Image.open(logo).convert('RGB').resize((180, 180), Image.LANCZOS)).astype(float)
    l180 = np.asarray(Image.open(logo180).convert('RGB').resize((180, 180), Image.LANCZOS)).astype(float)
    m = np.ones((180, 180), bool); m[:14, :14] = m[:14, -14:] = m[-14:, :14] = m[-14:, -14:] = False   # koseler haric
    f = np.abs(c180 - l180)[m].mean()
    k('kaynak 1254 yakalama = canli 180 logo (ort. fark <= 12)', f <= 12, round(f, 2))
    # 2) sekil ayni: altin maskesi eski ile yeni IoU
    a0 = np.asarray(Image.open(logo).convert('RGB').resize(out_im.size, Image.LANCZOS)).astype(float)
    m0 = (a0[..., 0] - a0[..., 2]) > 10; m1 = (o[..., 0] - o[..., 2]) > 10   # sicak (altin) / lacivert ayrimi, renkten bagimsiz
    iou = (m0 & m1).sum() / max(1, (m0 | m1).sum())
    k('sekil ayni (altin maske IoU >= 0.97)', iou >= 0.97, round(iou, 4))
    # 3) zemin ayni (altin + 25 px hale disi, koseler haric)
    hal = np.asarray(Image.fromarray((m0 | m1).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(51))) > 0
    beyaz = np.asarray(Image.fromarray(((a0.min(2) > 200) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31))) > 0
    z = (~hal) & (~beyaz)
    fz = np.percentile(np.abs(o - a0)[z], 99.9)
    k('zemin degismedi (p99.9 <= 2)', fz <= 2, round(float(fz), 2))
    kz = int(sum((c.min(2) > 60).sum() for c in (o[:240, :240], o[:240, -240:], o[-240:, :240], o[-240:, -240:])))
    # dikis: kose dolgusu siniri (beyaz maske 15 px genisletme) icindeki ve hemen disindaki 6 px seritlerin ortalama farki
    bw = (a0.min(2) > 60); bw[240:-240, :] = False; bw[:, 240:-240] = False
    def gen(m, n):
        return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(n))) > 0
    i1 = gen(bw, 15) & ~gen(bw, 3); d1 = gen(bw, 27) & ~gen(bw, 15)
    kf = float(np.abs(o[i1].mean(0) - o[d1].mean(0)).max())
    k('kose dolgusu dikissiz (sinir ici/disi 6 px serit ortalama kanal farki <= 3)', kf <= 3, round(kf, 2))
    k('kose beyazi/grisi kalmadi (4 kose 240 px, min kanal > 60 piksel = 0)', kz == 0, kz)
    hl = int(((a0.min(2) > 200) & (o.min(2) < 120) & (alfa(a0) > 0.5)).sum())
    k('altin parlamalari korundu (parlak altin -> koyu piksel = 0)', hl == 0, hl)
    # 4) yeni altin = pin altini: ic altin ortalama rengi ve parlaklik dagilimi
    ic = alfa(o) >= 0.98
    p = np.asarray(Image.open(pin).convert('RGB')).astype(float)[PIN_PANEL[1]:PIN_PANEL[3], PIN_PANEL[0]:PIN_PANEL[2]][PIN_SEMBOL_Y[0]:PIN_SEMBOL_Y[1]]
    pm = np.asarray(Image.fromarray((altin_maske(p.astype(int)) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 0
    c1, c2 = o[ic].mean(0), p[pm].mean(0)
    k('logo ic altin ortalamasi pin altiniyla kanal farki <= 8', np.abs(c1 - c2).max() <= 8, f'{c1.round()} / {c2.round()}')
    q1 = np.percentile(o[ic] @ LUM, [5, 50, 95]); q2 = np.percentile(p[pm] @ LUM, [5, 50, 95])
    k('parlaklik p5/p50/p95 pin ile farki <= 10', np.abs(q1 - q2).max() <= 10, f'{q1.round()} / {q2.round()}')
    c0 = a0[alfa(a0) >= 0.98].mean(0)
    k('eski altindan farkli (en az bir kanal >= 6)', np.abs(c0 - c1).max() >= 6, f'eski {c0.round()} yeni {c1.round()}')
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logo', required=True); ap.add_argument('--logo180', required=True)
    ap.add_argument('--pin', required=True); ap.add_argument('--out', required=True)
    g = ap.parse_args(); os.makedirs(g.out, exist_ok=True)
    im, bilgi, yeni, eski = uret(g.logo, g.pin)
    yol = os.path.join(g.out, 'LOGO_YENI_ALTIN_3000.png'); im.save(yol, optimize=True)
    S = qc(Image.open(yol).convert('RGB'), g.logo, g.logo180, g.pin, yeni)
    for s in S:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}")
    np.save(os.path.join(g.out, 'ramp_yeni.npy'), yeni); np.save(os.path.join(g.out, 'ramp_eski.npy'), eski)
    json.dump({'kapilar': S, 'bilgi': bilgi}, open(os.path.join(g.out, 'QC_LOGO.json'), 'w'), indent=1, default=str)
    raise SystemExit(0 if all(s['sonuc'] == 'PASS' for s in S) else 1)


if __name__ == '__main__':
    main()
