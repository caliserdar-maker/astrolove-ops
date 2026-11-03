#!/usr/bin/env python3
"""DENEME 3 TESHIS ARACI (4 Kas): kapi payi Serdar talimatiyla 24 px'e dondu (kanit olcutu totolojik bulundu; bagimsiz inceleme). Is akisinda degil.
Kova kaynak leke kapisi testi (Serdar 4 Kas, A maddesi). Kapi gevsetme yasagi (Serdar 1 Kas): kapi iki bilinen ornekle denenir.
Kapi = ornament_motor.py ile ayni yol: kirp (pad 2) -> delik_kapat (onarim) -> leke_ic_kaynak(olcum=True) ic & alfa < 0.9 piksel sayisi.
  bilinen PASS: mevcut kaynak (onarim sonrasi) -> 0 beklenir.
  bilinen FAIL: ayni goruntuye (onarim sonrasi, motorun olctugu goruntu) yapay leke eklenir -> > 0 beklenir.
    leke_ic: en kalin murekkep noktasinda yaricap r disk, alfa 0.5
    leke_kenar: kenara degen murekkepte ust kenardan 40 px icerde ayni disk (kenar payi buyudu; kenar yakini kacirilmiyor mu)
  kiyas: eski kenar payi (24 px) ile ayni olcum (445 px tekrar uretilir mi).
Ayrica bilgi: ham kaynakta (onarim oncesi) yeni payla olcum.
Kullanim: kova_kapi_testi.py --kaynak aquarius_symbol_gold.png --cikti DIR   |   --sahte (yerel sahte kaynak, gercek olcude)"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o1 = al.o5, al.o1


def olc(alfa, olcum):
    ic, t = o5.leke_ic_kaynak(alfa, olcum=olcum)
    m = ic & (alfa < 0.9)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    return dict(leke_px=int(m.sum()), bilesen=[dict(x=int(s[0]), y=int(s[1]), w=int(s[2]), h=int(s[3]), alan=int(s[4])) for s in st[1:]][:12],
                tanim=t)


def disk(alfa, cx, cy, r):
    a = alfa.copy(); yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]
    a[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = 0.5
    return a


def sahte():
    """gercek olcu (kirpim 10817 x 4501), iki dalga seridi; serit ust ve alt kenara deger (kenar satirlari AA)."""
    W, H, ss = 10817, 4501, 2
    im = Image.new('L', (W // ss, H // ss), 0); d = ImageDraw.Draw(im)
    x = np.linspace(-200, W // ss + 200, 400)
    for y0 in (520, 1730):
        y = y0 + 520 * np.sin(x / (W // ss) * 4 * np.pi)
        d.line(list(zip(x, y)), fill=255, width=560, joint='curve')
    a = np.asarray(im.resize((W, H), Image.BILINEAR), np.float32) / 255.0
    rgb = np.zeros((H, W, 3), np.float32); rgb[:] = (212, 170, 90)
    return np.dstack([rgb, a * 255.0])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--kaynak'); ap.add_argument('--sahte', action='store_true'); ap.add_argument('--cikti', required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    g = sahte() if a.sahte else np.asarray(Image.open(a.kaynak).convert('RGBA'), np.float32)
    g[..., 3] /= 255.0
    ham = o1.kirp(g, g[..., 3], pad=2)
    onar, _ = o5.delik_kapat(ham)
    A = onar[..., 3]
    R = dict(kaynak='sahte (yerel, gercek olcu)' if a.sahte else a.kaynak, boyut=list(A.shape),
             kenara_degen_murekkep=dict(ust=bool((A[0] > 0.5).any()), alt=bool((A[-1] > 0.5).any())))
    R['ham_onarim_oncesi_yeni_pay_bilgi'] = olc(ham[..., 3], True)['leke_px']
    R['bilinen_pass_mevcut_kaynak'] = dict(yeni_pay=olc(A, True), eski_pay_24=olc(A, False))
    # yapay leke: en kalin murekkep noktasi (mesafe donusumu en buyuk) ve ust kenara degen murekkepte kenardan 40 px icerde
    dt = cv2.distanceTransform((A > 0.9).astype(np.uint8), cv2.DIST_L2, 5)
    cy, cx = np.unravel_index(int(dt.argmax()), dt.shape); r = max(6, int(round(A.shape[1] / 600)))
    sut = np.nonzero((A[:40 + 2 * r + 10] > 0.99).all(0))[0]            # ust kenardan itibaren murekkebi dolu sutunlar
    ex = int(sut[np.argmax(dt[40 + r, sut])]) if len(sut) else None      # en kalin yer (disk murekkebin icinde kalsin)
    L1 = disk(A, cx, cy, r)
    R['bilinen_fail_leke_ic'] = dict(merkez=[int(cx), int(cy)], yaricap=r, yeni_pay=olc(L1, True))
    if ex is not None:
        L2 = disk(A, ex, 40, r)
        R['bilinen_fail_leke_kenar_40px'] = dict(merkez=[ex, 40], yaricap=r, yeni_pay=olc(L2, True))
    p = R['bilinen_pass_mevcut_kaynak']['yeni_pay']['leke_px'] == 0
    f1 = R['bilinen_fail_leke_ic']['yeni_pay']['leke_px'] > 0
    f2 = R.get('bilinen_fail_leke_kenar_40px', {}).get('yeni_pay', {}).get('leke_px', 1) > 0
    R['sonuc'] = dict(bilinen_pass_PASS_verdi=bool(p), bilinen_fail_ic_FAIL_verdi=bool(f1), bilinen_fail_kenar_FAIL_verdi=bool(f2),
                      test_gecti=bool(p and f1 and f2),
                      not_='kapi sert degeri onarim (delik_kapat) sonrasi olculur; ham kaynaktaki ic leke onarimla kapanir (V5 davranisi, degismedi)')
    (O / 'KOVA_KAPI_TESTI.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(dict(boyut=R['boyut'], pass_yeni=R['bilinen_pass_mevcut_kaynak']['yeni_pay']['leke_px'],
                          pass_eski24=R['bilinen_pass_mevcut_kaynak']['eski_pay_24']['leke_px'], fail_ic=R['bilinen_fail_leke_ic']['yeni_pay']['leke_px'],
                          fail_kenar=R.get('bilinen_fail_leke_kenar_40px', {}).get('yeni_pay', {}).get('leke_px'), ham_bilgi=R['ham_onarim_oncesi_yeni_pay_bilgi'],
                          sonuc=R['sonuc']['test_gecti'])), flush=True)
    return 0 if R['sonuc']['test_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
