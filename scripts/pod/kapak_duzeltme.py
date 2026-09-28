#!/usr/bin/env python3
"""POD_KAPAK_78 duzeltme (Serdar onayi 28 Eyl, hata-kontrol bulgusu): AQUARIUS_LIBRA + CAPRICORN_LIBRA. Etsy YOK.

Kok nedenler (olculdu, 11x14 baski pikseli):
  AQUARIUS_LIBRA: hat (a1_poster.olcum_duzelt) sembol bandini yalniz yukari genisletir; Terazi alt cubugu bant disinda
    kalir, sembol isme ortalanirken cubuk kayar (EJ baskisi: yay orta x 2212, cubuk 2398 = +186 px). Sembol kapisi
    bolgeye tamamen sigmayan bileseni saymadigi icin kacirdi. Duzeltme: yamali hatla (hat_yama) yeniden baski.
  CAPRICORN_LIBRA: kaynak POD_PRINT/CAPRICORN_LIBRA/MIDNIGHT_BLUE/11x14.jpg'de Terazi 381x291 (CANCER_LIBRA 332x255);
    hat kaynagi birebir tasir (hat hatasi degil, kaynak tasarim farki). Duzeltme (yalniz kapak baskisi): Terazi
    bileseni CANCER_LIBRA kutusuna olceklenir (orta x korunur, ust/alt CANCER_LIBRA ile ayni), zemin cevreden doldurulur.
Kapak: scripts/pod/kapak_v8_kur.py (v9 sahnesi, 295 30 919 880); sahneye dokunulmaz.
QC (PASS/FAIL): Terazi kutusu CANCER_LIBRA ile +-2 px (baski), cubuk orta x - yay orta x <= 2 px, kapak_v8 PASS.
Kullanim: kapak_duzeltme.py GIRDI OUT
  GIRDI: EJ_CANCER_LIBRA.jpg, EJ_AQUARIUS_LIBRA.jpg (yamali), EJ_CAPRICORN_LIBRA.jpg (yamali),
         ESKI_KAPAK_<CIFT>.jpg (mevcut POD_KAPAK_78 kapaklari, karsilastirma icin)
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

KOK = Path(__file__).resolve().parents[2]
BOLGE = (2550, 3075, 1800, 2800)          # 11x14 baskida sag kucuk sembol bolgesi (y0, y1, x0, x1), isim bandi ustu
KAP_BOLGE = (1330, 1580, 1510, 1990)      # 3000x2250 kapakta sag kucuk sembol (kapak_sembol_qc KUTU'nun sag yarisi)
TOL = 2


def terazi(a, bolge):
    """Altin (R-B > 60) bilesenleri: yay (en buyuk, ustte) + cubuklar. -> kutu, yay/cubuk orta x."""
    y0, y1, x0, x1 = bolge
    m = (a[y0:y1, x0:x1, 0] - a[y0:y1, x0:x1, 2]) > 60
    lab, n = ndi.label(m)
    al = ndi.sum(m, lab, range(1, n + 1))
    P = []
    for i in range(n):
        ys, xs = np.where(lab == i + 1)
        if al[i] < 0.05 * al.max() or ys.max() >= y1 - y0 - 1 or ys.min() == 0:   # kirinti / bolge kenarina degen (isim harfi)
            continue
        P.append({'y': [int(y0 + ys.min()), int(y0 + ys.max())], 'x': [int(x0 + xs.min()), int(x0 + xs.max())],
                  'alan': int(al[i]), 'orta_x': round(x0 + (xs.min() + xs.max()) / 2, 1)})
    P.sort(key=lambda p: p['y'][0])
    kutu = [min(p['x'][0] for p in P), min(p['y'][0] for p in P), max(p['x'][1] for p in P), max(p['y'][1] for p in P)]
    yay = max(P, key=lambda p: p['alan'])
    alt = P[-1]
    return {'kutu': kutu, 'en': kutu[2] - kutu[0] + 1, 'boy': kutu[3] - kutu[1] + 1, 'yay_orta_x': yay['orta_x'],
            'yay_en': yay['x'][1] - yay['x'][0] + 1, 'yay_boy': yay['y'][1] - yay['y'][0] + 1,
            'alt_cubuk_orta_x': alt['orta_x'], 'cubuk_kayma': round(alt['orta_x'] - yay['orta_x'], 1), 'parca': P}


def olcekle(a, ref):
    """Terazi'yi (mevcut kutu) ref kutusuna olcekler; murekkep yumusak alfa ile, zemin cevreden (inpaint) doldurulur."""
    t = terazi(a, BOLGE)
    x0, y0, x1, y1 = t['kutu']; P = 14
    X0, Y0, X1, Y1 = x0 - P, y0 - P, x1 + 1 + P, y1 + 1 + P
    parca = a[Y0:Y1, X0:X1]
    alfa = np.clip((parca[..., 0] - parca[..., 2] - 15) / 60, 0, 1)
    maske = cv2.dilate((alfa > 0).astype(np.uint8), np.ones((9, 9), np.uint8))
    zemin = cv2.inpaint(np.clip(a[Y0:Y1, X0:X1], 0, 255).astype(np.uint8), maske, 7, cv2.INPAINT_TELEA).astype(np.float32)
    zemin = cv2.GaussianBlur(zemin, (0, 0), 2) * (maske[..., None] > 0) + a[Y0:Y1, X0:X1] * (maske[..., None] == 0)
    out = a.copy(); out[Y0:Y1, X0:X1] = zemin
    k = ref['en'] / t['en'], ref['boy'] / t['boy']
    yw, yh = round(parca.shape[1] * k[0]), round(parca.shape[0] * k[1])
    p2 = cv2.resize(parca, (yw, yh), interpolation=cv2.INTER_AREA)
    a2 = cv2.resize(alfa, (yw, yh), interpolation=cv2.INTER_AREA)[..., None]
    cx = t['yay_orta_x']                                  # orta x korunur
    nx0 = round(cx - (t['yay_orta_x'] - X0) * k[0])
    ny0 = round(ref['kutu'][1] - P * k[1])                # ust = CANCER_LIBRA ustu
    bolge = out[ny0:ny0 + yh, nx0:nx0 + yw]
    out[ny0:ny0 + yh, nx0:nx0 + yw] = bolge * (1 - a2) + p2 * a2
    return out, {'once': {k_: t[k_] for k_ in ('kutu', 'en', 'boy')}, 'olcek': [round(k[0], 4), round(k[1], 4)]}


def kapak(baski, cikis, sahne):
    r = subprocess.run([sys.executable, str(KOK / 'scripts/pod/kapak_v8_kur.py'), str(sahne), str(baski),
                        str(KOK / 'data/pod/cila_cerceve_kaynak.png'), str(cikis), '295', '30', '919', '880'],
                       capture_output=True, text=True)
    s = r.stdout.strip().splitlines()
    return (s[-1] if s else '?') == 'PASS', (s[0] if s else r.stderr[-200:])


def main(girdi, out):
    girdi, out = Path(girdi), Path(out); out.mkdir(parents=True, exist_ok=True)
    sahne = out / '_sahne_1213.png'
    Image.open(KOK / 'data/pod/kapak_sahne_v9.png').convert('RGB').resize((1213, 910), Image.LANCZOS).save(sahne)
    rgb = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
    ref = terazi(rgb(girdi / 'EJ_CANCER_LIBRA.jpg'), BOLGE)
    R = {'referans_CANCER_LIBRA': {k: ref[k] for k in ('kutu', 'en', 'boy', 'yay_orta_x', 'alt_cubuk_orta_x')}, 'ciftler': {}}
    ok_hepsi = True
    for c in ('AQUARIUS_LIBRA', 'CAPRICORN_LIBRA'):
        a = rgb(girdi / f'EJ_{c}.jpg'); r = {'baski_once': {k: v for k, v in terazi(a, BOLGE).items() if k != 'parca'}}
        if abs(r['baski_once']['yay_en'] - ref['yay_en']) > TOL or abs(r['baski_once']['yay_boy'] - ref['yay_boy']) > TOL:   # olcek yaydan (kayik cubuk kutuyu buyutur)
            a, r['olcekleme'] = olcekle(a, ref)
        baski = out / f'BASKI_{c}.png'
        Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8)).save(baski)
        t = terazi(a, BOLGE); r['baski_sonra'] = {k: v for k, v in t.items() if k != 'parca'}
        kp, satir = kapak(baski, out / f'KAPAK_{c}.jpg', sahne)
        r['kapak_v8'] = {'pass': kp, 'olcum': satir}
        kk = terazi(rgb(out / f'KAPAK_{c}.jpg'), KAP_BOLGE)
        r['kapak_terazi'] = {k: kk[k] for k in ('en', 'boy', 'cubuk_kayma')}
        r['qc'] = {'boyut': bool(abs(t['en'] - ref['en']) <= TOL and abs(t['boy'] - ref['boy']) <= TOL),
                   'cubuk_ortada': bool(abs(t['cubuk_kayma']) <= TOL), 'kapak_v8': bool(kp)}
        r['pass'] = all(r['qc'].values()); ok_hepsi &= r['pass']
        R['ciftler'][c] = r
        print(c, 'PASS' if r['pass'] else 'FAIL', json.dumps(r['qc']), 'baski', t['en'], 'x', t['boy'], 'kayma', t['cubuk_kayma'],
              '| kapak', r['kapak_terazi'], flush=True)
    kr = terazi(rgb(girdi / 'ESKI_KAPAK_CANCER_LIBRA.jpg'), KAP_BOLGE) if (girdi / 'ESKI_KAPAK_CANCER_LIBRA.jpg').exists() else None
    if kr:
        R['referans_CANCER_LIBRA']['kapak'] = {k: kr[k] for k in ('en', 'boy', 'cubuk_kayma')}
    for c in ('AQUARIUS_LIBRA', 'CAPRICORN_LIBRA'):
        e = girdi / f'ESKI_KAPAK_{c}.jpg'
        if e.exists():
            ke = terazi(rgb(e), KAP_BOLGE); R['ciftler'][c]['eski_kapak_terazi'] = {k: ke[k] for k in ('en', 'boy', 'cubuk_kayma')}
    (out / 'OLCUM.json').write_text(json.dumps(R, indent=1))
    karsilastirma(girdi, out, R)
    sahne.unlink(missing_ok=True)
    sat = ['# POD_KAPAK_78 DUZELTME (Etsy YOK; yukleme Serdar onayindan sonra kapak-yukle oturumunda)', '',
           f'- Referans CANCER_LIBRA Terazi: baski {ref["en"]}x{ref["boy"]}, kapak {kr and (kr["en"], kr["boy"])}']
    for c, r in R['ciftler'].items():
        sat.append(f'- {c}: {"PASS" if r["pass"] else "FAIL"} | baski once {r["baski_once"]["en"]}x{r["baski_once"]["boy"]} '
                   f'kayma {r["baski_once"]["cubuk_kayma"]} -> sonra {r["baski_sonra"]["en"]}x{r["baski_sonra"]["boy"]} '
                   f'kayma {r["baski_sonra"]["cubuk_kayma"]} | kapak eski {r.get("eski_kapak_terazi")} -> yeni {r["kapak_terazi"]} | '
                   f'kapak_v8 {r["kapak_v8"]["olcum"]}')
    sat.append('SONUC ' + ('PASS' if ok_hepsi else 'FAIL'))
    (out / 'RAPOR.md').write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    return 0 if ok_hepsi else 1


def karsilastirma(girdi, out, R):
    """Satir basina: kapak kucuk (900) + sag sembol 4x buyutulmus kirpim. CANCER_LIBRA referans, eski ve yeni."""
    y0, y1, x0, x1 = KAP_BOLGE
    satirlar = [('CANCER_LIBRA (referans)', girdi / 'ESKI_KAPAK_CANCER_LIBRA.jpg')]
    for c in ('AQUARIUS_LIBRA', 'CAPRICORN_LIBRA'):
        satirlar += [(f'{c} ESKI', girdi / f'ESKI_KAPAK_{c}.jpg'), (f'{c} YENI', out / f'KAPAK_{c}.jpg')]
    tiles = []
    for ad, p in satirlar:
        if not p.exists():
            continue
        k = Image.open(p).convert('RGB')
        kir = k.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.LANCZOS)
        kucuk = k.resize((kir.height * 4 // 3, kir.height), Image.LANCZOS)
        t = Image.new('RGB', (kucuk.width + kir.width + 20, kir.height + 50), (255, 255, 255))
        t.paste(kucuk, (0, 50)); t.paste(kir, (kucuk.width + 20, 50))
        c = ad.split()[0]; olc = R['ciftler'].get(c, {})
        m = olc.get('kapak_terazi') if ad.endswith('YENI') else olc.get('eski_kapak_terazi') if 'ESKI' in ad else R['referans_CANCER_LIBRA'].get('kapak')
        ImageDraw.Draw(t).text((10, 15), f'{ad} | Terazi (kapak px) {m}', fill=(0, 0, 0))
        tiles.append(t)
    W = max(t.width for t in tiles); H = sum(t.height + 10 for t in tiles)
    S = Image.new('RGB', (W, H), (255, 255, 255)); y = 0
    for t in tiles:
        S.paste(t, (0, y)); y += t.height + 10
    S.save(out / 'KARSILASTIRMA.jpg', quality=90)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
