#!/usr/bin/env python3
"""Pinterest Sevgililer ornek pinleri (Serdar "ok" 25 Kas 2026, KARARLAR_20261125_31; RAPOR_PINTEREST_STRATEJI_20261122 bolum 6).

Kaynak: onayli pin v6 gorselleri (KARARLAR_20261122_45 + 20261123_1). Yeni tasarim dili YOK: zemin, baslik, poster, sembol
pikselleri onayli dosyadan aynen gelir; yalniz yazi satiri degisir ve (B2) onayli A pinindeki poster KUCULTULUP eklenir.
  K1 (A2, poster + Sevgililer cumlesi): PIN_01 A_POSTER v6; alt baslik "Combined Zodiac Symbol" -> SUBTITLE_A2.
  K3 (B2, birlesme karti + kucuk poster + CTA): PIN_02 B_SYMBOL v6; sagda kucuk poster (PIN_01'deki poster, golgesiyle,
     yalniz kucultme), alt satir "Add your names" -> CTA_B2.
Yazi: TeX Gyre Pagella Italic (Palatino Linotype klonu; onayli pinler Palatino ile Windows'ta yazildi, bu makinede yok).
Boy olculdu: onayli "Add your names" 88 px, "Combined Zodiac Symbol" 72 px (murekkep genisligi esitlenerek). Renk #162641.
Zemin duz (244,239,233), 4 kosede olculdu; silinen bant bu renkle doldurulur.

QC (PASS/FAIL, olculur): 1000x1500; degisen bantlar disinda kaynakla piksel farki 0 (sembol ve baslik dokunulmamis);
yazi kenar payi >= 60 px; yazi boyu 168 px akista >= 11 CSS px (boy x 0.168); B2 posteri sembol/etiket bantlarina degmez;
gorsel metninde uzun/orta tire, "free", "premium" yok.
Kullanim: sevgililer_pin.py --girdi DIR --out DIR [--font PAGELLA_ITALIC.otf]   |   sevgililer_pin.py --oz-test --girdi DIR
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG = (244, 239, 233)
RENK = (22, 38, 65)            # #162641 (onayli baslik rengi)
FONT = '/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-italic.otf'
SUBTITLE_A2 = 'A Valentine’s Day Gift'
CTA_B2 = 'See it with your names'
ALT_BOY, CTA_BOY = 72, 88
# onayli v6 bantlari (olculdu 25 Kas: murekkep satirlari, PIN_01/PIN_02 ayni)
ALT_BANT = (160, 256)          # alt baslik (murekkep 172-244)
CTA_BANT = (1365, 1475)        # alt satir (murekkep 1377-1463)
B_SEMBOL_X1 = 690              # PIN_02 birlesik sembol murekkebi x 341-658 (+ pay)
B_ETIKET_Y1 = 800              # PIN_02 burc etiketleri ve egri murekkebi y <= 793
KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'scripts', 'etsy'))
from etsy_common import METIN_KESIN  # noqa: E402
import re  # noqa: E402
PAY = 60                       # yazi ve kucuk poster icin kenar payi (px)
MUREKKEP_ORAN = 87 / 88        # onayli "Add your names": 88 px yazi -> 87 px murekkep yuksekligi (olculdu 25 Kas)


def yasak(metin):
    bul = [ad for ad, rx in METIN_KESIN if re.search(rx, metin, re.I)]
    return bul + (['free'] if re.search(r'\bfree\b', metin, re.I) else [])


def murekkep(a, esik=60):
    d = np.abs(a.astype(int) - np.array(BG)).sum(2) > esik
    ys, xs = np.where(d)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None


def taban(font, metin, y_bant, kaynak_metin, kaynak):
    """Yeni yazinin taban cizgisi = onayli yazinin taban cizgisi (kaynak murekkep ust kenari + font yukselimi)."""
    a = np.asarray(kaynak.convert('RGB'))[y_bant[0]:y_bant[1]]
    k = murekkep(a)
    bb = font.getbbox(kaynak_metin, anchor='ls')     # (x0, y0, x1, y1), y0 < 0 = taban ustu
    return y_bant[0] + k[1] - bb[1]


def yaz(im, metin, boy, y_bant, kaynak_metin, font_yol):
    f = ImageFont.truetype(font_yol, boy)
    tb = taban(f, metin, y_bant, kaynak_metin, im)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, y_bant[0], im.size[0] - 1, y_bant[1] - 1], fill=BG)
    dr.text((im.size[0] / 2, tb), metin, font=f, fill=RENK, anchor='ms')
    return f


def poster_kirp(pin01):
    """PIN_01'deki poster + golgesi: zeminden farkli en dis kutu (y 258-1323 bandi)."""
    a = np.asarray(pin01.convert('RGB'))
    d = np.abs(a.astype(int) - np.array(BG)).sum(2) > 6
    d[:258] = False; d[1340:] = False
    ys, xs = np.where(d)
    return pin01.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def uret(girdi, out, font_yol=FONT):
    os.makedirs(out, exist_ok=True)
    p1 = Image.open(os.path.join(girdi, 'PIN_01_CANCER_LEO_A_POSTER_v6.jpg')).convert('RGB')
    p2 = Image.open(os.path.join(girdi, 'PIN_02_CANCER_LEO_B_SYMBOL_v6.jpg')).convert('RGB')
    bilgi = {}
    # K1 / A2
    a2 = p1.copy()
    yaz(a2, SUBTITLE_A2, ALT_BOY, ALT_BANT, 'Combined Zodiac Symbol', font_yol)
    # K3 / B2
    b2 = p2.copy()
    yaz(b2, CTA_B2, CTA_BOY, CTA_BANT, 'Add your names', font_yol)
    pk = poster_kirp(p1)
    olcek = 0.30
    kp = pk.resize((round(pk.size[0] * olcek), round(pk.size[1] * olcek)), Image.LANCZOS)
    px = 1000 - PAY - kp.size[0]; py = 840
    b2.paste(kp, (px, py))
    bilgi['B2_poster'] = {'kaynak': list(pk.size), 'olcek': olcek, 'kutu': [px, py, px + kp.size[0], py + kp.size[1]]}
    yol = {'K1_A2': os.path.join(out, 'SEVGILILER_K1_A2_CANCER_LEO_POSTER.jpg'),
           'K3_B2': os.path.join(out, 'SEVGILILER_K3_B2_CANCER_LEO_KART.jpg')}
    a2.save(yol['K1_A2'], quality=95, subsampling=0)
    # 168 px telefon akisi benzetimi (1x, bicubic; en kotu durum, PINLER_ORNEK 6.2 yontemi)
    ok = Image.new('RGB', (2 * 168 + 30, 252 + 20), (255, 255, 255))
    ok.paste(a2.resize((168, 252), Image.BICUBIC), (10, 10)); ok.paste(b2.resize((168, 252), Image.BICUBIC), (188, 10))
    ok.save(os.path.join(out, 'OKUNURLUK_168PX.png'))
    b2.save(yol['K3_B2'], quality=95, subsampling=0)
    return {'A2': a2, 'B2': b2, 'P1': p1, 'P2': p2}, bilgi, yol


def qc(g, bilgi, font_yol=FONT):
    S = []

    def kontrol(ad, ok, det=''):
        S.append({'kapi': ad, 'sonuc': 'PASS' if ok else 'FAIL', 'ayrinti': det})

    for k in ('A2', 'B2'):
        kontrol(f'{k} boyut 1000x1500', g[k].size == (1000, 1500), str(g[k].size))
    A2, P1 = np.asarray(g['A2']).astype(int), np.asarray(g['P1']).astype(int)
    B2, P2 = np.asarray(g['B2']).astype(int), np.asarray(g['P2']).astype(int)
    m = np.ones(A2.shape[:2], bool); m[ALT_BANT[0]:ALT_BANT[1]] = False
    kontrol('A2 bant disi fark 0 (baslik, poster, alt satir onayli)', int(np.abs(A2 - P1)[m].max()) == 0,
            f'max {int(np.abs(A2 - P1)[m].max())}')
    kx = bilgi['B2_poster']['kutu']
    m = np.ones(B2.shape[:2], bool); m[CTA_BANT[0]:CTA_BANT[1]] = False; m[kx[1]:kx[3], kx[0]:kx[2]] = False
    kontrol('B2 bant/poster disi fark 0 (sembol, etiket, baslik onayli)', int(np.abs(B2 - P2)[m].max()) == 0,
            f'max {int(np.abs(B2 - P2)[m].max())}')
    kontrol('B2 poster sembol bandina degmez', kx[0] >= B_SEMBOL_X1 and kx[1] >= B_ETIKET_Y1, f'kutu {kx}')
    kontrol('B2 poster kenar payi >= 60 px', kx[2] <= 1000 - PAY, f'sag kenar {kx[2]}')
    kontrol('B2 poster alt satira degmez', kx[3] <= CTA_BANT[0] - 40, f'alt {kx[3]}')
    kontrol('B2 poster yalniz kucultme', bilgi['B2_poster']['olcek'] <= 1.0, str(bilgi['B2_poster']['olcek']))
    for k, ban, boy, metin in (('A2', ALT_BANT, ALT_BOY, SUBTITLE_A2), ('B2', CTA_BANT, CTA_BOY, CTA_B2)):
        arr = np.asarray(g[k])[ban[0]:ban[1]]
        mk = murekkep(arr)
        kontrol(f'{k} yazi kenar payi >= 60 px', mk is not None and mk[0] >= PAY and mk[2] <= 1000 - PAY, f'murekkep {mk}')
        # okunurluk CIKTIDAN: murekkep yuksekligi -> esdeger yazi boyu (onayli oran) -> 168 px akista CSS px
        es = (mk[3] - mk[1] + 1) / MUREKKEP_ORAN if mk else 0
        kontrol(f'{k} yazi 168 px akista >= 11 CSS px (olculen)', es * 0.168 >= 11, f'murekkep h {mk[3] - mk[1] + 1 if mk else 0} -> {es * 0.168:.1f}')
        y = yasak(metin)
        kontrol(f'{k} yazi yasak ifade yok (METIN_KESIN + free)', not y, f'{metin} {y}')
    return S


def oz_test(girdi):
    """Bilinen PASS (gercek uretim) + bilinen FAIL ornekleri: kapilar FAIL verebilmeli."""
    import tempfile
    g, bilgi, _ = uret(girdi, tempfile.mkdtemp())
    ok = all(s['sonuc'] == 'PASS' for s in qc(g, bilgi))
    sonuc = [('bilinen PASS', ok)]
    # FAIL 1: sembol bandina dokunan B2
    g1 = dict(g); b = g['B2'].copy(); ImageDraw.Draw(b).rectangle([400, 900, 420, 920], fill=(0, 0, 0)); g1['B2'] = b
    sonuc.append(('FAIL: sembole dokunma', any(s['sonuc'] == 'FAIL' for s in qc(g1, bilgi))))
    # FAIL 2: posteri sembol bandina tasiyan yerlesim
    b2 = dict(bilgi); b2['B2_poster'] = dict(bilgi['B2_poster']); b2['B2_poster']['kutu'] = [500, 840, 711, 1160]
    sonuc.append(('FAIL: poster sembol bandinda', any(s['sonuc'] == 'FAIL' for s in qc(g, b2))))
    # FAIL 4: kenara tasan ve kucuk yazi (gercek qc() olcer)
    g4 = dict(g); a = g['A2'].copy(); ImageDraw.Draw(a).rectangle([0, ALT_BANT[0], 999, ALT_BANT[1] - 1], fill=BG)
    ImageDraw.Draw(a).text((10, ALT_BANT[0] + 40), 'tiny', font=ImageFont.truetype(FONT, 30), fill=RENK); g4['A2'] = a
    s4 = {x['kapi']: x['sonuc'] for x in qc(g4, bilgi)}
    sonuc.append(('FAIL: kenar payi', s4.get('A2 yazi kenar payi >= 60 px') == 'FAIL'))
    sonuc.append(('FAIL: kucuk yazi', s4.get('A2 yazi 168 px akista >= 11 CSS px (olculen)') == 'FAIL'))
    # FAIL 5: poster kenara tasiyor
    b5 = dict(bilgi); b5['B2_poster'] = dict(bilgi['B2_poster']); b5['B2_poster']['kutu'] = [750, 840, 990, 1160]
    sonuc.append(('FAIL: poster kenar payi', any(x['sonuc'] == 'FAIL' and 'poster kenar' in x['kapi'] for x in qc(g, b5))))
    sonuc.append(('FAIL: yasak metin', bool(yasak('Free premium gift \u2014 long-lasting'))))
    # FAIL 3: baslik bandi degismis A2
    g3 = dict(g); a = g['A2'].copy(); ImageDraw.Draw(a).rectangle([480, 60, 500, 80], fill=BG); g3['A2'] = a
    sonuc.append(('FAIL: baslik degisti', any(s['sonuc'] == 'FAIL' for s in qc(g3, bilgi))))
    for ad, v in sonuc:
        print(('PASS ' if v else 'FAIL ') + ad)
    return all(v for _, v in sonuc)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--girdi', required=True)
    ap.add_argument('--out')
    ap.add_argument('--font', default=FONT)
    ap.add_argument('--oz-test', action='store_true')
    a = ap.parse_args()
    if a.oz_test:
        sys.exit(0 if oz_test(a.girdi) else 1)
    g, bilgi, yol = uret(a.girdi, a.out, a.font)
    S = qc(g, bilgi, a.font)
    for s in S:
        print(f"{s['sonuc']} {s['kapi']} | {s['ayrinti']}")
    json.dump({'kapilar': S, 'bilgi': bilgi, 'dosyalar': yol}, open(os.path.join(a.out, 'QC_PIN.json'), 'w'), ensure_ascii=False, indent=1)
    sys.exit(0 if all(s['sonuc'] == 'PASS' for s in S) else 1)
