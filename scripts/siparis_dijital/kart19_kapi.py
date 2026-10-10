#!/usr/bin/env python3
"""WP 19 ILAN KARTI KAPILARI (Serdar 10 Eki, C / adim 5). Etsy'ye yazmaz; yalniz olcer.

Kart = renk_varyasyon_kur.py ciktisi (3000x2250; poster kutusu CIKIS.json 'poster' [x, y, w, h], yoksa 810,150,1379,1755).
Kapilar (her biri esik + olculen deger):
  yay   : yay_tara (ikinci / yabanci cember yayi) poster kesitinde; plaka = VINTAGE_11x14 (asil cember). Isimli istisna
          (SAGITTARIUS_VIRGO 11x14) olcege gore (yay_tara.istisna_mi s).
  ocr   : alt yazi bolgesi OCR'i beklenen iki satirla ayni ("Warm Parchment", "Poster color. Format selected separately.");
          tum kart OCR'inde dijital vaat sozcukleri YOK (pdf, digital, download, instant, all five, five colors,
          print-ready, etsy messages, you receive, 24 hours).
  amp   : tagline'da '&' varsa amp_eski.kapi_amp (WP sayfasinda); yoksa 'uygulanmaz'.
Kullanim: kart19_kapi.py KART.jpg PLAKA.png CIFT --json CIKTI.json [--kart-json CIKIS.json] [--sayfa WP_11x14.jpg --mesaj METIN]
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


def ocr(im, psm):
    with tempfile.NamedTemporaryFile(suffix='.png') as f:
        im.save(f.name)
        return subprocess.run(['tesseract', f.name, '-', '--psm', str(psm)], capture_output=True, text=True).stdout


def norm(t):
    return re.sub(r'\s+', ' ', t.strip().lower())


def kapilar(kart, plaka_ac, cift, kutu=KUTU_VARSAYILAN, sayfa=None, mesaj=''):
    K = Image.open(kart).convert('RGB')
    x, y, w, h = kutu
    P = np.asarray(K.crop((x, y, x + w, y + h)))
    yay = yay_tara.tara(P, plaka_ac, cift=cift, boy='11x14')
    yay = {k: v for k, v in yay.items() if k != 'asil'}
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
    r['PASS'] = bool(yay['PASS'] and o['PASS'] and r['amp'].get('PASS') is not False)
    return r


if __name__ == '__main__':
    a = sys.argv[1:]
    def ops(k):
        return a[a.index(k) + 1] if k in a else None
    js, kj, sy, ms = ops('--json'), ops('--kart-json'), ops('--sayfa'), ops('--mesaj')
    kart, plaka, cift = [q for q in a if not q.startswith('--') and q not in (js, kj, sy, ms)][:3]
    kutu = tuple(json.load(open(kj))['poster'][0]) if kj and os.path.exists(kj) else KUTU_VARSAYILAN
    ac = yay_tara.asil_cember(np.asarray(Image.open(plaka).convert('RGB')))
    r = kapilar(kart, ac, cift, kutu, sy, ms or '')
    r['plaka_cember'] = ac
    print('KART19', cift, 'PASS' if r['PASS'] else 'FAIL', '| yay', 'PASS' if r['yay']['PASS'] else 'FAIL',
          [(q['aci'], q['merkez_fark'], q['px']) for q in r['yay']['yabanci']], 'istisna', len(r['yay']['istisna']),
          '| ocr', 'PASS' if r['ocr']['PASS'] else 'FAIL', r['ocr']['yasak_sozcukler'], '| amp', r['amp'].get('PASS'), flush=True)
    if js:
        json.dump(r, open(js, 'w'), indent=1, ensure_ascii=False, default=float)
    sys.exit(0 if r['PASS'] else 1)
