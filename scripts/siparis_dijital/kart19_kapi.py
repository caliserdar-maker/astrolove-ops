#!/usr/bin/env python3
"""WP 19 ILAN KARTI KAPILARI (Serdar 10 Eki, C / C2). Etsy'ye yazmaz; yalniz olcer.

Kart = renk_varyasyon_kur.py ciktisi (3000x2250; poster kutusu CIKIS.json 'poster' [x, y, w, h], yoksa 810,150,1379,1755).
Kapilar (her biri esik + olculen deger):
  yay   : yay_tara (ikinci / yabanci cember yayi) poster kesitinde; plaka = VINTAGE_11x14 (asil cember). Isimli istisna
          (SAGITTARIUS_VIRGO 11x14) olcege gore (yay_tara.istisna_mi s). KART OLCEGI ISTISNASI (Serdar 10 Eki goz onayi,
          C: yay okunun kalin govde kenari): ISTISNA_KART, degerler kart olceginde (aci +-1, merkez farki +-5 px, px +-%2).
  ocr   : alt yazi bolgesi OCR'i beklenen iki satirla ayni ("Warm Parchment", "Poster color. Format selected separately.");
          tum kart OCR'inde dijital vaat sozcukleri YOK (pdf, digital, download, instant, all five, five colors,
          print-ready, etsy messages, you receive, 24 hours).
  amp   : tagline'da '&' varsa amp_eski.kapi_amp (WP sayfasinda); yoksa 'uygulanmaz'.
  p4    : (--referans verilirse; C2 eski bakir kartlari) TAGLINE CIFT BASKI / IKINCI METIN KAPISI = wp-katman P4
          (360cbef wp_bakir.ikinci_metin) kart olceginde: eski kart murekkebinin, ayni ciftin 360cbef karti (sayfa
          kapilari + c_iz/ikinci_metin PASS) murekkebinde karsiligi olmayan en buyuk bileseni < esik. Kagit = ayni plaka
          renk_varyasyon_kur ile kart geometrisine (--plaka-kart). Sabitler 360cbef ile ayni (ESIK 12, MIN_ALAN 40,
          TOL 12 px ve ALAN 100 px^2 2400 olceginde; k = poster eni / 2400).
Kullanim: kart19_kapi.py KART.jpg PLAKA.png CIFT --json CIKTI.json [--kart-json CIKIS.json] [--sayfa WP_11x14.jpg --mesaj METIN]
          [--referans YENI_KART.jpg --plaka-kart PLAKA_KART.jpg]
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yay_tara

KUTU_VARSAYILAN = (810, 150, 1379, 1755)
BEKLENEN = ['warm parchment', 'poster color. format selected separately.']
YASAK = r'\b(pdf|pdfs|digital|download|downloads|instant|all five|five colou?rs|print[- ]ready|etsy messages|you receive|24 hours)\b'
# Serdar 10 Eki goz onayi (C): kart olcegindeki yay alarmi = yay okunun kalin govde kenari. (aci, merkez_fark, px) kart olceginde.
ISTISNA_KART = {'LEO_SAGITTARIUS': (36.6, 246.1, 532), 'SAGITTARIUS_VIRGO': (24.1, 538.5, 424)}
# wp-katman P4 (360cbef wp_katman / wp_bakir) sabitleri, aynen
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
P4_ESIK, P4_MIN_ALAN, P4_TOL, P4_ALAN = 12.0, 40, 12, 100


def kart_istisna_mi(cift, y):
    t = ISTISNA_KART.get(cift)
    return bool(t and abs(y['aci'] - t[0]) <= 1.0 and abs(y['merkez_fark'] - t[1]) <= 5.0 and abs(y['px'] - t[2]) <= 0.02 * t[2])


def ocr(im, psm):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        im.save(f.name)
        return subprocess.run(['tesseract', f.name, '-', '--psm', str(psm)], capture_output=True, text=True).stdout


def norm(t):
    return re.sub(r'\s+', ' ', t.strip().lower())


def murekkep(D):
    import cv2
    m = np.abs(D @ LUMA) > P4_ESIK
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= P4_MIN_ALAN
    return tut[lab]


def p4_kapi(eski, yeni, kagit, kutu):
    """wp_bakir.ikinci_metin (360cbef) kart olceginde: out = eski kart, D_beklenen = yeni kart - kagit."""
    import cv2
    x, y, w, h = kutu
    def kes(p):
        return np.asarray(Image.open(p).convert('RGB').crop((x, y, x + w, y + h))).astype(np.float32)
    E, Y, K = kes(eski), kes(yeni), kes(kagit)
    k = w / 2400.0
    m_out, m_ref = murekkep(E - K), murekkep(Y - K)
    t = max(1, int(round(P4_TOL * k)))
    m_ref = cv2.dilate(m_ref.astype(np.uint8), np.ones((2 * t + 1, 2 * t + 1), np.uint8)).astype(bool)
    yb = (m_out & ~m_ref).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(yb, 8)
    alan = st[1:, cv2.CC_STAT_AREA] if n > 1 else np.zeros(0, int)
    sinir = int(round(P4_ALAN * k * k))
    r = {'yabanci_px': int(yb.sum()), 'bilesen': int((alan >= sinir).sum()), 'en_buyuk': int(alan.max()) if alan.size else 0,
         'tol_px': t, 'esik_alan': sinir, 'k': round(k, 4), 'murekkep_px_eski': int(m_out.sum())}
    if alan.size:
        i = int(alan.argmax()) + 1
        x0, y0, ww, hh = (int(v) for v in st[i, :4])
        r['kutu'] = [x0, y0, x0 + ww, y0 + hh]
    r['PASS'] = bool(r['en_buyuk'] < sinir)
    return r


def kapilar(kart, plaka_ac, cift, kutu=KUTU_VARSAYILAN, sayfa=None, mesaj='', referans=None, plaka_kart=None):
    K = Image.open(kart).convert('RGB')
    x, y, w, h = kutu
    P = np.asarray(K.crop((x, y, x + w, y + h)))
    yay = yay_tara.tara(P, plaka_ac, cift=cift, boy='11x14')
    yay = {k: v for k, v in yay.items() if k != 'asil'}
    kist = [q for q in yay['yabanci'] if kart_istisna_mi(cift, q)]
    if kist:
        yay['yabanci'] = [q for q in yay['yabanci'] if not kart_istisna_mi(cift, q)]
        yay['istisna'] = list(yay.get('istisna') or []) + [dict(q, kart_istisnasi='Serdar 10 Eki goz onayi') for q in kist]
        yay['PASS'] = not yay['yabanci']
    alt = norm(ocr(K.crop((0, y + h + 30, K.width, K.height)), 6))
    satir = [s for s in (norm(q) for q in alt.split('\n')) if s] if '\n' in alt else [alt]
    alt_tek = ' '.join(satir)
    tum = norm(ocr(K, 11))
    yasak = sorted(set(m.group(0) for m in re.finditer(YASAK, tum + ' ' + alt_tek)))
    o = {'alt_yazi': alt_tek, 'beklenen': BEKLENEN, 'beklenen_var': all(b in alt_tek for b in BEKLENEN),
         'yasak_sozcukler': yasak, 'yasak_listesi': YASAK}
    o['PASS'] = bool(o['beklenen_var'] and not yasak)
    r = {'kart': os.path.basename(kart), 'boyut': list(K.size), 'poster_kutusu': list(kutu), 'yay': yay, 'ocr': o}
    if '&' in (mesaj or ''):
        import amp_eski
        sys.path.insert(0, os.environ.get('KISISEL_YOL', ''))
        import pilot12
        ciz = getattr(pilot12.ciz_cap, 'eski', pilot12.ciz_cap)
        r['amp'] = amp_eski.kapi_amp(np.asarray(Image.open(sayfa).convert('RGB')), mesaj, ciz,
                                     pilot12.FONT_DIR / pilot12.TAG_FONT, pilot12.TAG_W, y_bant=(0.70, 0.97))
    else:
        r['amp'] = {'PASS': None, 'not': "uygulanmaz: tagline'da & yok"}
    if referans:
        r['p4'] = p4_kapi(kart, referans, plaka_kart, kutu)
    r['PASS'] = bool(yay['PASS'] and o['PASS'] and r['amp'].get('PASS') is not False and (r.get('p4') or {}).get('PASS', True))
    return r


if __name__ == '__main__':
    a = sys.argv[1:]
    def ops(k):
        return a[a.index(k) + 1] if k in a else None
    js, kj, sy, ms, rf, pk = (ops(q) for q in ('--json', '--kart-json', '--sayfa', '--mesaj', '--referans', '--plaka-kart'))
    if rf and not pk:
        raise SystemExit('HATA: --referans icin --plaka-kart gerekir')
    deger = {i + 1 for i, q in enumerate(a) if q in ('--json', '--kart-json', '--sayfa', '--mesaj', '--referans', '--plaka-kart')}
    kart, plaka, cift = [q for i, q in enumerate(a) if not q.startswith('--') and i not in deger][:3]
    kutu = tuple(json.load(open(kj))['poster'][0]) if kj and os.path.exists(kj) else KUTU_VARSAYILAN
    ac = yay_tara.asil_cember(np.asarray(Image.open(plaka).convert('RGB')))
    r = kapilar(kart, ac, cift, kutu, sy, ms or '', rf, pk)
    r['plaka_cember'] = ac
    p4 = r.get('p4')
    print('KART19', cift, 'PASS' if r['PASS'] else 'FAIL', '| yay', 'PASS' if r['yay']['PASS'] else 'FAIL',
          [(q['aci'], q['merkez_fark'], q['px']) for q in r['yay']['yabanci']], 'istisna', len(r['yay']['istisna']),
          '| ocr', 'PASS' if r['ocr']['PASS'] else 'FAIL', r['ocr']['yasak_sozcukler'], '| amp', r['amp'].get('PASS'),
          '| p4', ('PASS' if p4['PASS'] else 'FAIL') + f" en_buyuk {p4['en_buyuk']} esik {p4['esik_alan']} kutu {p4.get('kutu')}" if p4 else '-',
          flush=True)
    if js:
        json.dump(r, open(js, 'w'), indent=1, ensure_ascii=False, default=float)
    sys.exit(0 if r['PASS'] else 1)
