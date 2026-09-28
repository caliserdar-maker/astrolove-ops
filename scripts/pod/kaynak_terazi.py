#!/usr/bin/env python3
"""POD_PRINT kaynak duzeltmesi: CAPRICORN_LIBRA kucuk Terazi -> CANCER_LIBRA olcusu (Serdar karari A, 28 Eyl). Etsy YOK.
Kaynakta (POD_PRINT/CAPRICORN_LIBRA/<RENK>/<BOY>.jpg) Terazi 381x291 (11x14 MB), CANCER_LIBRA 332x255; hat birebir tasidigi
icin musteri baskisi da buyuk cikiyordu. Duzeltme her renk x boy dosyasinda ayri olculur:
  - konum: CANCER_LIBRA 11x14 MB Terazi murekkep sablonu, dosyanin sag yarisinda cok olcekli NCC (oran/boydan bagimsiz),
    sonra kutu murekkep bilesenlerinden kesinlestirilir.
  - olcek: ayni renk/boy CANCER_LIBRA dosyasindaki Terazi yayi / CAPRICORN yayi (iki eksende AYNI oran).
  - yer: yay orta x korunur, ust = CANCER_LIBRA Terazi ustu.
  - zemin: eski Terazi alani ayni renk/boy CANCER_LIBRA dosyasindan (ayni Canva sablonu; murekkepsiz pikseller), CL
    murekkebinin kalan yerleri inpaint; yeni Terazi yumusak alfa ile oturur. Kutu disi pikseller degismez.
  - kayit: JPEG ozgun nicemleme tablolari + ornekleme + dpi + ICC ile (qtables keep).
QC (dosya basina PASS/FAIL): yeni Terazi yay en/boy CL'ye +-1% ; cubuk orta x - yay orta x <= 2 px (olcek); iz yok: eski
Terazi halkasinda (eski murekkep - yeni murekkep, genisletilmis) zemin ortalamasi cevre zeminden <= 3 (kanal) ve eski murekkep kalinti orani
<= 0.5% ; kutu disi degisim (yeniden kodlama sonrasi) ortalama <= 0.5.
Tarama (tara): 78 cift MB 11x14 kaynaginda sol/sag kucuk sembol kutusu; Cancer/Libra CANCER_LIBRA'ya, diger burclar kendi
medyanina gore; %5'ten fazla sapan liste.
Kullanim: kaynak_terazi.py tara POD_DIZIN OUT          (POD_DIZIN/<CIFT>/MIDNIGHT_BLUE/11x14.jpg)
          kaynak_terazi.py duzelt CAP_DIZIN CL_DIZIN OUT CL_MB_11x14.jpg (<DIZIN>/<RENK>/<BOY>.jpg; OUT/<RENK>/<BOY>.jpg + QC)
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, JpegImagePlugin
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None
REF_W = 3307                                 # 11x14 genislik
BANT = (2550, 3075)                          # 11x14 kucuk sembol bandi (tara)
ESIK = 0.05


def murekkep(a):
    """Altin murekkep derecesi 0-1: (R-B) - zemin(R-B medyani); lacivert, siyah, beyaz, fildisi, parsomen zeminde calisir."""
    d = a[..., 0].astype(np.float32) - a[..., 2].astype(np.float32)
    return np.clip((d - np.median(d) - 12) / 50, 0, 1)


def bilesenler(m, en_az_oran=0.05, kenar=True):
    lab, n = ndi.label(m)
    if not n:
        return []
    al = ndi.sum(m, lab, range(1, n + 1)); sl = ndi.find_objects(lab); P = []
    for i in range(n):
        ys, xs = sl[i]
        if al[i] < en_az_oran * al.max():
            continue
        if kenar and (ys.start == 0 or xs.start == 0 or ys.stop >= m.shape[0] or xs.stop >= m.shape[1]):
            continue
        P.append({'y': [ys.start, ys.stop - 1], 'x': [xs.start, xs.stop - 1], 'alan': int(al[i]),
                  'orta_x': (xs.start + xs.stop - 1) / 2, 'lab': i + 1})
    return P


def olc(a, kutu, pay=0.25):
    """kutu cevresinde (pay) Terazi: yay (en buyuk) + cubuklar -> kesin kutu."""
    x0, y0, x1, y1 = kutu; w, h = x1 - x0, y1 - y0
    X0, Y0 = max(int(x0 - pay * w), 0), max(int(y0 - pay * h), 0)
    X1, Y1 = min(int(x1 + pay * w), a.shape[1]), min(int(y1 + pay * h * 0.6), a.shape[0])
    m = murekkep(a[Y0:Y1, X0:X1]) > 0.5
    P = bilesenler(m)
    if not P:
        return None
    yay = max(P, key=lambda p: p['alan'])
    P = [p for p in P if p['x'][0] >= yay['x'][0] - 0.2 * w and p['x'][1] <= yay['x'][1] + 0.2 * w]
    alt = max(P, key=lambda p: p['y'][1])
    k = [X0 + min(p['x'][0] for p in P), Y0 + min(p['y'][0] for p in P), X0 + max(p['x'][1] for p in P), Y0 + max(p['y'][1] for p in P)]
    return {'kutu': k, 'en': k[2] - k[0] + 1, 'boy': k[3] - k[1] + 1,
            'yay_en': yay['x'][1] - yay['x'][0] + 1, 'yay_boy': yay['y'][1] - yay['y'][0] + 1,
            'yay_orta_x': X0 + yay['orta_x'], 'cubuk_kayma': round(alt['orta_x'] - yay['orta_x'], 1)}


def bul(a, sablon):
    """sag yarida cok olcekli sablon (Terazi murekkebi) -> yaklasik kutu (tam cozunurluk)."""
    H, W = a.shape[:2]; f = 1200 / W
    g = murekkep(cv2.resize(np.ascontiguousarray(a), (1200, round(H * f)), interpolation=cv2.INTER_AREA)).astype(np.float32)
    g[:, :600] = 0
    en = None
    for s in np.geomspace(0.55, 1.8, 40):
        tw = max(int(round(sablon.shape[1] * (W / REF_W) * s * f)), 8); th = max(int(round(sablon.shape[0] * (W / REF_W) * s * f)), 8)
        if th >= g.shape[0] or tw >= g.shape[1]:
            continue
        t = cv2.resize(sablon, (tw, th), interpolation=cv2.INTER_AREA)
        r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
        e = cv2.boxFilter(g, -1, (tw, th), normalize=False, anchor=(0, 0))[:r.shape[0], :r.shape[1]]
        r[(e < 0.5 * t.sum()) | ~np.isfinite(r)] = -1           # bos/duz pencere (NCC dejenere) elenir
        _, v, _, l = cv2.minMaxLoc(r)
        if en is None or v > en[0]:
            en = (v, l, tw, th)
    v, (x, y), tw, th = en
    return [x / f, y / f, (x + tw) / f, (y + th) / f], round(float(v), 3)


def sablon_kur(cl_mb_11x14):
    """Terazi sablonu CANCER_LIBRA MB 11x14 KAYNAGINDAN olculur (sag yari, kucuk sembol bandi; tara ile ayni olcum).
    (3. iterasyon: sabit REF_KUTU EJ baskisindan olculmustu; baskida sembol isme ortalandigi icin kaynakta yeri farkli.)"""
    a = np.asarray(Image.open(cl_mb_11x14).convert('RGB'))
    y0, y1 = BANT; x0 = a.shape[1] // 2
    P = bilesenler(murekkep(a[y0:y1, x0:]) > 0.5)
    ana = max(P, key=lambda q: q['alan']); w = ana['x'][1] - ana['x'][0]
    P = [q for q in P if q['x'][1] >= ana['x'][0] - 0.6 * w and q['x'][0] <= ana['x'][1] + 0.6 * w]
    k = (x0 + min(q['x'][0] for q in P), y0 + min(q['y'][0] for q in P), x0 + max(q['x'][1] for q in P), y0 + max(q['y'][1] for q in P))
    print(f'sablon kutusu (CL MB 11x14 kaynak): {k} = {k[2] - k[0] + 1}x{k[3] - k[1] + 1}', flush=True)
    return murekkep(a[k[1]:k[3] + 1, k[0]:k[2] + 1]).astype(np.float32)


def duzelt_dosya(cap_yol, cl_yol, sablon, cikis):
    """Tam goruntu uint8 (5x7 = 10962x15175 bellege sigsin), hesap yalniz Terazi bolgesinde float."""
    im = Image.open(cap_yol); a = np.asarray(im.convert('RGB'))
    b = np.asarray(Image.open(cl_yol).convert('RGB'))
    r = {'dosya': str(cap_yol), 'px': [a.shape[1], a.shape[0]]}
    if a.shape != b.shape:
        r.update({'pass': False, 'sebep': f'boyut farkli CL {b.shape[1]}x{b.shape[0]}'}); return r
    kc, vc = bul(a, sablon); kr, vr = bul(b, sablon)
    tc, tr = olc(a, kc), olc(b, kr)
    r.update({'eslesme': [vc, vr], 'once': tc, 'ref': tr})
    if not tc or not tr:
        r.update({'pass': False, 'sebep': 'Terazi bulunamadi'}); return r
    k = tr['yay_en'] / tc['yay_en']                       # iki eksende ayni oran
    r['olcek'] = round(k, 4); r['olcek_boy_kontrol'] = round(tr['yay_boy'] / tc['yay_boy'], 4)
    x0, y0, x1, y1 = tc['kutu']; P = max(12, int(0.06 * tc['en']))
    X0, Y0, X1, Y1 = x0 - P, y0 - P, x1 + 1 + P, y1 + 1 + P
    ex0, ey0 = min(X0, tr['kutu'][0] - P), min(Y0, tr['kutu'][1] - P)
    ex1, ey1 = max(X1, tr['kutu'][2] + 1 + P), max(Y1, tr['kutu'][3] + 1 + P)
    A = a[ey0:ey1, ex0:ex1].astype(np.float32); B = b[ey0:ey1, ex0:ex1].astype(np.float32)
    px0, py0 = X0 - ex0, Y0 - ey0
    parca = A[py0:py0 + (Y1 - Y0), px0:px0 + (X1 - X0)].copy(); alfa = murekkep(parca)
    # zemin: eski Terazi + CL Terazi alanlari, CL dosyasindan; CL murekkebi inpaint
    cl_m = cv2.dilate((murekkep(B) > 0.02).astype(np.uint8), np.ones((7, 7), np.uint8))
    zem = cv2.inpaint(np.clip(B, 0, 255).astype(np.uint8), cl_m, 9, cv2.INPAINT_TELEA).astype(np.float32)
    eski_m = cv2.dilate((murekkep(A) > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    O = A.copy(); O[eski_m] = zem[eski_m]
    yw, yh = round(parca.shape[1] * k), round(parca.shape[0] * k)
    p2 = cv2.resize(parca, (yw, yh), interpolation=cv2.INTER_AREA)
    a2 = cv2.resize(alfa, (yw, yh), interpolation=cv2.INTER_AREA)[..., None]
    nx0 = round(tc['yay_orta_x'] - (tc['yay_orta_x'] - X0) * k) - ex0
    ny0 = round(tr['kutu'][1] - (tc['kutu'][1] - Y0) * k) - ey0          # ust = CANCER_LIBRA Terazi ustu
    z = O[ny0:ny0 + yh, nx0:nx0 + yw]
    O[ny0:ny0 + yh, nx0:nx0 + yw] = z * (1 - a2) + p2 * a2
    out = a.copy(); out[ey0:ey1, ex0:ex1] = np.clip(np.rint(O), 0, 255).astype(np.uint8)
    cikis.parent.mkdir(parents=True, exist_ok=True)
    kw = {'qtables': im.quantization, 'subsampling': JpegImagePlugin.get_sampling(im), 'dpi': im.info.get('dpi', (300, 300))}
    if im.info.get('icc_profile'):
        kw['icc_profile'] = im.info['icc_profile']
    Image.fromarray(out).save(cikis, 'JPEG', **kw)
    del out
    c = np.asarray(Image.open(cikis).convert('RGB'))
    t2 = olc(c, [ex0 + nx0, ey0 + ny0, ex0 + nx0 + yw, ey0 + ny0 + yh], pay=0.1)
    top, n = 0.0, 0                                       # kutu disi degisim (yeniden kodlama), satir parcalariyla
    for s0 in range(0, a.shape[0], 1024):
        d = np.abs(c[s0:s0 + 1024].astype(np.int16) - a[s0:s0 + 1024].astype(np.int16)).mean(2)
        if s0 < ey1 and s0 + 1024 > ey0:
            d[max(ey0 - s0, 0):ey1 - s0, ex0:ex1] = np.nan
        top += np.nansum(d); n += np.count_nonzero(~np.isnan(d))
    dis_fark = top / max(n, 1)
    C = c[ey0:ey1, ex0:ex1].astype(np.float32)
    yeni_m = cv2.dilate((murekkep(C) > 0.02).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    halka = eski_m & ~yeni_m
    cevre = cv2.dilate(eski_m.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & ~eski_m & ~yeni_m
    cc = C                         # halka zemini cevredeki gercek zeminle ayni tonda mi (kanal basina)
    iz_fark = float(np.abs(cc[halka].mean(0) - cc[cevre].mean(0)).max()) if halka.any() and cevre.any() else 0.0
    kalinti = float((murekkep(C)[halka] > 0.5).mean()) if halka.any() else 0.0
    r.update({'sonra': t2, 'kutu_disi_fark': round(dis_fark, 3), 'iz_fark': round(iz_fark, 2), 'kalinti_orani': round(kalinti, 4),
              'bolge': [int(ex0), int(ey0), int(ex1), int(ey1)]})
    ok = bool(t2 and abs(t2['yay_en'] / tr['yay_en'] - 1) <= 0.01 and abs(t2['yay_boy'] / tr['yay_boy'] - 1) <= 0.01
              and abs(t2['cubuk_kayma']) <= max(2, 2 * a.shape[1] / REF_W) and iz_fark <= 3 and kalinti <= 0.005 and dis_fark <= 0.5)
    r['pass'] = ok
    return r


def duzelt(cap_dizin, cl_dizin, out, sablon_yol):
    cap_dizin, cl_dizin, out = Path(cap_dizin), Path(cl_dizin), Path(out)
    sablon = sablon_kur(sablon_yol)
    dosyalar = sorted(cap_dizin.glob('*/*.jpg')); R = []; t0 = time.time()
    for i, p in enumerate(dosyalar, 1):
        renk, boy = p.parent.name, p.stem
        clp = cl_dizin / renk / p.name
        if not clp.exists():
            r = {'dosya': str(p), 'pass': False, 'sebep': 'CL karsiligi yok'}
        else:
            try:
                r = duzelt_dosya(p, clp, sablon, out / renk / p.name)
            except Exception as e:                                       # noqa: BLE001
                r = {'dosya': str(p), 'pass': False, 'sebep': f'{type(e).__name__}: {e}'[:200]}
        r.update({'renk': renk, 'boy': boy}); R.append(r)
        g = time.time() - t0
        print(f'[{i}/{len(dosyalar)}] {renk}/{boy} {"PASS" if r["pass"] else "FAIL"} olcek {r.get("olcek")} '
              f'once {r.get("once", {}) and (r["once"]["en"], r["once"]["boy"])} sonra {r.get("sonra") and (r["sonra"]["en"], r["sonra"]["boy"])} '
              f'ref {r.get("ref") and (r["ref"]["en"], r["ref"]["boy"])} iz {r.get("iz_fark")} dis {r.get("kutu_disi_fark")} {r.get("sebep", "")} | '
              f'gecen {g:.0f}s kalan ~{g / i * (len(dosyalar) - i):.0f}s %{i * 100 // len(dosyalar)}', flush=True)
    (out / 'KAYNAK_QC.json').write_text(json.dumps(R, indent=1, default=float))
    kirpimlar(cap_dizin, cl_dizin, out, R)
    ok = all(r['pass'] for r in R) and len(R) > 0
    print(f'KAYNAK: {sum(r["pass"] for r in R)}/{len(R)} PASS -> {"PASS" if ok else "FAIL"}', flush=True)
    return 0 if ok else 1


def kirpimlar(cap_dizin, cl_dizin, out, R):
    """11x14 her renk: CANCER_LIBRA | CAPRICORN eski | CAPRICORN yeni, Terazi 2x buyutulmus (KAYNAK_KARSILASTIRMA.jpg)."""
    from PIL import ImageDraw
    satir = []
    for r in R:
        if r.get('boy') != '11x14' or not r.get('once') or not r.get('ref'):
            continue
        t = Image.new('RGB', (3 * 720 + 20, 560), (255, 255, 255)); d = ImageDraw.Draw(t)
        for i, (p, kt, ad) in enumerate(((cl_dizin / r['renk'] / '11x14.jpg', r['ref'], 'CANCER_LIBRA'),
                                          (cap_dizin / r['renk'] / '11x14.jpg', r['once'], 'CAPRICORN eski'),
                                          (out / r['renk'] / '11x14.jpg', r.get('sonra') or r['once'], 'CAPRICORN yeni'))):
            if not p.exists():
                continue
            k = kt['kutu']; cx, cy = (k[0] + k[2]) // 2, (k[1] + k[3]) // 2
            t.paste(Image.open(p).convert('RGB').crop((cx - 180, cy - 125, cx + 180, cy + 125)).resize((720, 500), Image.LANCZOS), (i * 730, 50))
            d.text((i * 730 + 8, 12), f'{r["renk"]} 11x14 {ad}: Terazi {kt["en"]}x{kt["boy"]} (yay {kt["yay_en"]}x{kt["yay_boy"]})', fill=(0, 0, 0))
        satir.append(t)
    if satir:
        S = Image.new('RGB', (satir[0].width, sum(x.height + 10 for x in satir)), (255, 255, 255)); y = 0
        for x in satir:
            S.paste(x, (0, y)); y += x.height + 10
        S.save(out / 'KAYNAK_KARSILASTIRMA.jpg', quality=90)


def tara(pod, out):
    pod, out = Path(pod), Path(out); out.mkdir(parents=True, exist_ok=True)
    O = []
    for p in sorted(pod.glob('*/MIDNIGHT_BLUE/11x14.jpg')):
        c = p.parent.parent.name; a, b = c.split('_')
        im = np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
        y0, y1 = BANT
        for taraf, burc, (x0, x1) in (('sol', a, (0, 1653)), ('sag', b, (1653, 3307))):
            m = murekkep(im[y0:y1, x0:x1]) > 0.5
            P = bilesenler(m)
            if not P:
                O.append({'cift': c, 'taraf': taraf, 'burc': burc, 'en': 0, 'boy': 0}); continue
            ana = max(P, key=lambda q: q['alan']); w = ana['x'][1] - ana['x'][0]      # sembolun parcalari (yildiz kirintisi haric)
            P = [q for q in P if q['x'][1] >= ana['x'][0] - 0.6 * w and q['x'][0] <= ana['x'][1] + 0.6 * w]
            O.append({'cift': c, 'taraf': taraf, 'burc': burc, 'en': max(q['x'][1] for q in P) - min(q['x'][0] for q in P) + 1,
                      'boy': max(q['y'][1] for q in P) - min(q['y'][0] for q in P) + 1})
    cl = {o['burc']: o for o in O if o['cift'] == 'CANCER_LIBRA'}
    med = {}
    for o in O:
        med.setdefault(o['burc'], []).append((o['en'], o['boy']))
    med = {k: (float(np.median([x[0] for x in v])), float(np.median([x[1] for x in v]))) for k, v in med.items()}
    sat, sapan = [], []
    for o in O:
        ref, kaynak = ((cl[o['burc']]['en'], cl[o['burc']]['boy']), 'CANCER_LIBRA') if o['burc'] in cl else (med[o['burc']], 'burc medyani')
        se, sb = o['en'] / ref[0] - 1 if ref[0] else 9, o['boy'] / ref[1] - 1 if ref[1] else 9
        o.update({'ref': [round(ref[0], 1), round(ref[1], 1)], 'ref_kaynak': kaynak, 'sapma_en': round(se, 3), 'sapma_boy': round(sb, 3)})
        if max(abs(se), abs(sb)) > ESIK:
            sapan.append(o)
    sat = ['# 78 KAYNAK KUCUK SEMBOL OLCUSU (POD_PRINT MB 11x14, salt okur)', '',
           f'- Olculen {len(O)} sembol ({len(O) // 2} cift). Referans: Cancer/Libra = CANCER_LIBRA; diger burclar = kendi medyani.',
           f'- %{ESIK * 100:.0f}\'ten fazla sapan: {len(sapan)}', '', '| cift | taraf | burc | en x boy | referans | sapma en / boy |', '|---|---|---|---|---|---|']
    sat += [f'| {o["cift"]} | {o["taraf"]} | {o["burc"]} | {o["en"]}x{o["boy"]} | {o["ref"][0]:.0f}x{o["ref"][1]:.0f} ({o["ref_kaynak"]}) | '
            f'{o["sapma_en"]:+.1%} / {o["sapma_boy"]:+.1%} |' for o in sapan]
    sat += ['', '## Burc medyanlari (en x boy)', ''] + [f'- {k}: {v[0]:.0f}x{v[1]:.0f}' for k, v in sorted(med.items())]
    (out / 'SEMBOL_OLCU_78.md').write_text('\n'.join(sat) + '\n')
    (out / 'SEMBOL_OLCU_78.json').write_text(json.dumps(O, indent=1))
    print('\n'.join(sat[:4] + sat[6:8 + len(sapan)]), flush=True)
    return 0


if __name__ == '__main__':
    if sys.argv[1] == 'tara':
        sys.exit(tara(sys.argv[2], sys.argv[3]))
    if sys.argv[1] == 'duzelt':
        sys.exit(duzelt(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))
    raise SystemExit(__doc__)
