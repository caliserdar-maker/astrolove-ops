#!/usr/bin/env python3
"""DENEME 3 TESHIS ARACI (4 Kas): kapi payi Serdar talimatiyla 24 px'e dondu (kanit olcutu totolojik bulundu; bagimsiz inceleme). Is akisinda degil.
Kova kaynak leke kaniti (Serdar 4 Kas, EK 1 b-c ve EK 2). Uretimden SONRA kosar (ornek78 is klasoru + 954 PNG'ler).
EK 1b: eski payin (24 px) saydigi kaynak pikselleri maske gorseli + ayni yerlerin 954 son dosyalardan (5 stil) 4x yakin plani.
EK 1c: bu piksellerin son goruntude leke olmadiginin olcumu (ayni yerde):
   - cikti leke tanimi (ornament_ornek5.leke_ic: kapali maske 2 px ice, alfa < 0.9) bolgede piksel sayisi
   - oge kenarina uzaklik (954 px; murekkep disina en kisa mesafe): kenar yumusatmasi mi, ic delik mi
   - kaynak alfa (oge kutusuna yeniden orneklenmis) ile son oge alfasi farki (ortalama / en buyuk)
   - 5 stil: bolgedeki alfa >= 0.9 murekkep pikseli lumasi, ayni ogenin murekkep luma p1-p99 araligina gore (bilgi)
   kanit_var = bolgede cikti leke 0 VE tum noktalar oge kenarinda (uzaklik <= 2 px). Yeni esik degil: cikti leke kapisinin (leke_a_0) bolgesel okumasi;
   2 px = leke_ic'in ice asindirma payi (LEKE_ICE) ile ayni.
EK 2: kor bant: yeni payla ice asindirma (ice px) kadar kenar bandi kaynakta sayilmaz; bandin 954 px ve 76 mm karsiligi, oge basina.
Kullanim: kova_kanit.py --kaynak DIR(/tmp/kay) --png DIR(/tmp/png) --cikti DIR --cift AQUARIUS_PISCES"""
import argparse
import importlib.util
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o4, o1 = al.o5, al.o4, al.o1
STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
MM_PX = 76 / 954


def kaynak(K, burc):
    g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32); g[..., 3] /= 255.0
    g = o1.kirp(g, g[..., 3], pad=2)
    g, _ = o5.delik_kapat(g)
    return g


def main():
    ap = argparse.ArgumentParser()
    for k in ('kaynak', 'png', 'cikti', 'cift'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args(); K, P, O = Path(a.kaynak), Path(a.png), Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    cift = a.cift; b1, b2 = cift.lower().split('_')
    yer = 'kucuk_sol' if b1 == 'aquarius' else 'kucuk_sag'
    g = kaynak(K, 'aquarius'); A = g[..., 3]
    ic24, t24 = o5.leke_ic_kaynak(A, olcum=False); ic66, t66 = o5.leke_ic_kaynak(A, olcum=True)
    eski, yeni = ic24 & (A < 0.9), ic66 & (A < 0.9)
    R = dict(cift=cift, oge=yer, kaynak_boyut=list(A.shape), eski_pay=dict(tanim=t24, leke_px=int(eski.sum())),
             yeni_pay=dict(tanim=t66, leke_px=int(yeni.sum())))
    ys, xs = np.nonzero(eski)
    n, lab, st, cen = cv2.connectedComponentsWithStats(eski.astype(np.uint8), 8)
    R['eski_pay']['bilesen'] = [dict(x=int(s[0]), y=int(s[1]), w=int(s[2]), h=int(s[3]), alan=int(s[4])) for s in st[1:]]
    R['eski_pay']['kenar_satirinda'] = dict(ust_y_le_2=int((ys <= 2).sum()), alt_y_ge_H_3=int((ys >= A.shape[0] - 3).sum()), toplam=int(len(ys)))
    # EK 1b: kaynak maske gorseli (tum kaynak kucultulmus, eski pay pikselleri kirmizi kalin; ust/alt kenar 1:1 kirpimlari)
    zem = np.array([60, 60, 66], np.float32)
    rgb = g[..., :3] * A[..., None] + zem * (1 - A[..., None])
    s_ = 2400 / A.shape[1]
    kucuk = cv2.resize(rgb, (2400, int(round(A.shape[0] * s_))), interpolation=cv2.INTER_AREA)
    mk = cv2.resize(cv2.dilate(eski.astype(np.uint8), np.ones((25, 25), np.uint8)), (kucuk.shape[1], kucuk.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    kucuk[mk] = [255, 0, 0]
    parcalar = [Image.fromarray(np.clip(kucuk, 0, 255).astype(np.uint8))]
    for i in np.argsort(-st[1:, 4])[:4] + 1:
        x, y, w, h = st[i, :4]; p = 40
        x0, y0, x1, y1 = max(0, x - p), max(0, y - p), min(A.shape[1], x + w + p), min(A.shape[0], y + h + p)
        c1 = np.clip(rgb[y0:y1, x0:x1], 0, 255).astype(np.uint8); c2 = c1.copy(); c2[eski[y0:y1, x0:x1]] = [255, 0, 0]
        im = np.concatenate([c1, np.full((c1.shape[0], 6, 3), 255, np.uint8), c2], 1)
        f = max(1, int(1200 / max(im.shape[:2])))
        parcalar.append(Image.fromarray(im).resize((im.shape[1] * f, im.shape[0] * f), Image.NEAREST))
    Wd = max(p_.width for p_ in parcalar); H = sum(p_.height + 10 for p_ in parcalar)
    tuv = Image.new('RGB', (Wd, H), 'white'); y = 0
    for p_ in parcalar:
        tuv.paste(p_, (0, y)); y += p_.height + 10
    tuv.save(O / 'KOVA_ESKI_PAY_MASKE.png')
    # esleme kaynak -> 954 (oge kutusu, dogrusal; teshis ile ayni)
    w = P / '_is' / cift
    MO = json.loads((w / 'motor' / 'OLCUM.json').read_text()); kb = MO['kutu'][yer]
    D = pickle.load(open(w / 'katman.pkl', 'rb')); M = D['M'][yer]
    sb = o1.bbox(A, 0.5)
    fx = (kb[2] - kb[0]) / (sb[2] - sb[0]); fy = (kb[3] - kb[1]) / (sb[3] - sb[1])
    px = np.clip(np.round(kb[0] + (xs + 0.5 - sb[0]) * fx - 0.5).astype(int), 0, 953)
    py = np.clip(np.round(kb[1] + (ys + 0.5 - sb[1]) * fy - 0.5).astype(int), 0, 953)
    Pm = np.zeros((954, 954), bool); Pm[py, px] = True
    Rg = cv2.dilate(Pm.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    lic = o5.leke_ic(M) & (M < 0.9)
    uz = cv2.distanceTransform((M > 0.05).astype(np.uint8), cv2.DIST_L2, 5)
    # kaynak alfa oge kutusuna yeniden orneklenmis (alan ortalamasi) vs son oge alfasi
    Ak = np.zeros((954, 954), np.float32)
    kw, kh = int(kb[2] - kb[0]), int(kb[3] - kb[1])
    Ak[kb[1]:kb[1] + kh, kb[0]:kb[0] + kw] = cv2.resize(A[sb[1]:sb[3], sb[0]:sb[2]], (kw, kh), interpolation=cv2.INTER_AREA)
    fark = np.abs(Ak - M)[Rg]
    R['esleme_954'] = dict(oge_kutu=kb, kaynak_murekkep_kutu=list(map(int, sb)), olcek=[round(fx, 6), round(fy, 6)],
                           benzersiz_954_piksel=int(Pm.sum()), bolge_piksel_3x3=int(Rg.sum()))
    stil_olc = {}
    for s in STIL:
        f_ = P / f'{cift}_{s}_954.png'
        if not f_.exists():
            continue
        im = Image.open(f_)
        if im.mode == 'RGBA':
            bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, (0, 0), im); im = bg
        rgb9 = np.asarray(im.convert('RGB')).astype(np.float32); L = o4.lum(rgb9)
        ink = M >= 0.9
        p1, p99 = np.percentile(L[ink], [1, 99])
        b = Rg & ink
        stil_olc[s] = dict(bolge_murekkep_px=int(b.sum()), oge_luma_p1_p99=[round(float(p1), 1), round(float(p99), 1)],
                           bolge_luma_min_max=[round(float(L[b].min()), 1), round(float(L[b].max()), 1)] if b.any() else None,
                           aralik_disi_px=int(((L < p1) | (L > p99))[b].sum()))
    R['kanit'] = dict(cikti_leke_bolgede=int((lic & Rg).sum()), cikti_leke_oge_toplam=int(lic.sum()),
                      oge_kenarina_uzaklik_px=dict(en_buyuk=round(float(uz[Pm].max()), 2), ortanca=round(float(np.median(uz[Pm])), 2)),
                      kaynak_son_alfa_farki_bolge=dict(ortalama=round(float(fark.mean()), 3), en_buyuk=round(float(fark.max()), 3)),
                      stil_luma_bilgi=stil_olc)
    R['kanit']['kanit_var'] = bool(R['kanit']['cikti_leke_bolgede'] == 0 and R['kanit']['oge_kenarina_uzaklik_px']['en_buyuk'] <= 2.0)
    R['kanit']['tanim'] = ('kanit_var = bolgede cikti leke (leke_ic, alfa < 0.9) 0 VE tum eslenen noktalar oge kenarinda (murekkep disina uzaklik <= 2 px '
                           '= leke_ic ice payi). Uzaklik kucukse piksel kenar yumusatmasidir, ic delik degil.')
    # EK 1b: 954 yakin plan (5 stil, 4x), camgobegi = eski payin saydigi yerler
    X0, Y0, X1, Y1 = kb[0] - 8, kb[1] - 8, kb[2] + 8, kb[3] + 8
    tiles = []
    for s in STIL:
        f_ = P / f'{cift}_{s}_954.png'
        if not f_.exists():
            continue
        im = Image.open(f_)
        if im.mode == 'RGBA':
            bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, (0, 0), im); im = bg
        cr = im.convert('RGB').crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * 4, (Y1 - Y0) * 4), Image.NEAREST)
        dr = ImageDraw.Draw(cr)
        for yy, xx in zip(*np.nonzero(Pm)):
            dr.rectangle(((xx - X0) * 4, (yy - Y0) * 4, (xx - X0) * 4 + 3, (yy - Y0) * 4 + 3), outline=(0, 255, 255))
        tiles.append(cr)
    if tiles:
        T = Image.new('RGB', (max(t.width for t in tiles), sum(t.height + 8 for t in tiles)), 'white'); y = 0
        for t in tiles:
            T.paste(t, (0, y)); y += t.height + 8
        T.save(O / 'KOVA_954_YAKIN_4x.png')
    # EK 2: kor bant (yeni payla kaynak kenarindan ice px sayilmaz), oge basina 954 px ve mm
    kb_ = {}
    for c in sorted(p.name for p in (P / '_is').iterdir() if (p / 'motor' / 'OLCUM.json').exists()):
        mo = json.loads((P / '_is' / c / 'motor' / 'OLCUM.json').read_text())
        for yer_, burc in (('kucuk_sol', c.split('_')[0]), ('kucuk_sag', c.split('_')[1])):
            gg = kaynak(K, burc.lower()); _, t = o5.leke_ic_kaynak(gg[..., 3], olcum=True)
            k_ = mo['kutu'][yer_]; s_b = o1.bbox(gg[..., 3], 0.5)
            olc = max((k_[2] - k_[0]) / (s_b[2] - s_b[0]), (k_[3] - k_[1]) / (s_b[3] - s_b[1]))
            bant = t['ice_px'] * olc
            kb_[f'{c}/{yer_}/{burc}'] = dict(kaynak_W=int(gg.shape[1]), kenar_payi=t['kenar_payi'], pay_degisti=bool(t['kenar_payi'] > 24),
                                             ice_px_kaynak=t['ice_px'], bant_954_px=round(bant, 3), bant_mm=round(bant * MM_PX, 4),
                                             murekkep_kenara_degiyor=bool((gg[0, :, 3] > 0.5).any() or (gg[-1, :, 3] > 0.5).any()
                                                                          or (gg[:, 0, 3] > 0.5).any() or (gg[:, -1, 3] > 0.5).any()))
    yeni_bant = [v['bant_954_px'] for v in kb_.values() if v['pay_degisti']]
    R['kor_bant'] = dict(oge=kb_, pay_degisen_en_buyuk_954_px=max(yeni_bant) if yeni_bant else None,
                         pay_degisen_en_buyuk_mm=round(max(yeni_bant) * MM_PX, 4) if yeni_bant else None,
                         ek_kontrol_gerekli=bool(yeni_bant and max(yeni_bant) > 1.0),
                         not_='ana sembol kaynagi 1600 px (motor) -> pay 24 degismedi; yalniz pay degisen kaynaklar yeni kor bant')
    (O / 'KOVA_KANIT.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(dict(eski=R['eski_pay']['leke_px'], yeni=R['yeni_pay']['leke_px'], kanit=R['kanit']['kanit_var'],
                          leke_bolge=R['kanit']['cikti_leke_bolgede'], uzaklik=R['kanit']['oge_kenarina_uzaklik_px'],
                          alfa_fark=R['kanit']['kaynak_son_alfa_farki_bolge'], kor_bant_px=R['kor_bant']['pay_degisen_en_buyuk_954_px'],
                          kor_bant_mm=R['kor_bant']['pay_degisen_en_buyuk_mm'], ek_kontrol=R['kor_bant']['ek_kontrol_gerekli'])), flush=True)
    return 0 if R['kanit']['kanit_var'] and not R['kor_bant']['ek_kontrol_gerekli'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
