#!/usr/bin/env python3
"""ALTIN SON 2 (Merkez / Serdar 3 Kas): kesit profili aktarimi. RUBY, SAPPHIRE, EMERALD. BEIGE / AGED_PAPYRUS'a dokunulmaz. Yama yontemi IPTAL.
1 Ana sembol (G2 pikselleri ve alfa, 1600 px kaynak): her piksel icin t = kenara uzaklik / yerel yari kalinlik (0 kenar, 1 cizgi ortasi;
  yerel yari kalinlik = orta eksen (mesafe donusumu sirti) degerinin en yakin sirt pikselinden yayilmasi) ve kenar normali acisi
  (mesafe donusumu egimi, ice dogru).
2 Renk tablosu renk(t, aci): TB x AB kutu, kutu basina ortanca. Aci etkisi (t kutusu icinde aci kutulari arasi luma std) kutu ici gurultuden
  (kutu ici luma std ortancasi) kucukse (oran < ACI_ESIK) tablo yalniz t ile kurulur; olcum OLCUM'da.
3 Kucuk burclar, isimler, tarih, logo, halka: t ve aci kendi alfalarindan 4x buyuk hesaplanir, renk tablodan (t dogrusal, aci en yakin), alfa
  agirlikli kucultulur; kenar yumusakligi ozgun alfadan. Ana sembol kendi pikselleri.
4 Butunlesme a114ddb ile ayni (ornament_altin.boya_altin): notr dis golge, notr ic golge, dusus alt 0.92 us 0.25. Zemin rengi yok.
Kapilar: duzgunluk (her ogede t bandi [0.4, 0.6] luma std <= 1.2 x ana sembol), halka surekliligi (orta eksende 3 px pencere ortalamasi
>= 0.70 x halka ortancasi, alfa >= 0.9 kisim), kontrast ortanca >= 4.5 (kati bilgi), leke 0, tasma 0, ton sapmasi, yerlesim a114ddb.
Kullanim: ornament_altin_son2.py --kaynak DIR --cikti DIR --son DIR(a5e3ea2 STIL3_SON)"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
son, o5, o4, o3, o1 = al.son, al.o5, al.o4, al.o3, al.o1
N, MM, P, CX, CY = o5.N, o5.MM, o5.P, o5.CX, o5.CY
lum = o4.lum
TB, AB, SS = 32, 16, 4
ACI_ESIK = 0.5
BANT = (0.4, 0.6)
DUZ_ORAN, SUREK_ORAN = 1.2, 0.70
KUCUK_OGE = ('isim1', 'isim2', 'tarih', 'sonsuz', 'kucuk_sol', 'kucuk_sag')
al.INCE = al.INCE + ('kucuk_sol', 'kucuk_sag')     # deneme 2: kucuk burc cizgisi 3-4 px (yazi gibi ince); ic golge 0.35 yerine 0.15
PROFIL = {}                                   # oge -> tablodan boyanmis tam tuval renk
KAT = {}


def t_aci(a):
    """alfa -> (t, aci, maske). t = dt / yerel yari kalinlik; aci = ice dogru kenar normali (radyan, 0-2pi)."""
    m = (a > 0.5).astype(np.uint8)
    dt = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
    sirt = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)) - 1e-3) & (dt > 0.5)
    if not sirt.any():
        return np.zeros_like(dt), np.zeros_like(dt), m > 0
    inv = (~sirt).astype(np.uint8)
    _, lab = cv2.distanceTransformWithLabels(inv, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    vals = dt[sirt]                                                   # etiketler sifir piksellerine tarama sirasiyla 1..n
    hw = vals[np.clip(lab - 1, 0, len(vals) - 1)]
    t = np.clip(dt / np.maximum(hw, 0.5), 0, 1)
    db = cv2.GaussianBlur(dt, (0, 0), 1.0)
    gx = cv2.Sobel(db, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(db, cv2.CV_32F, 0, 1, ksize=3)
    ang = np.mod(np.arctan2(gy, gx), 2 * np.pi)
    return t.astype(np.float32), ang.astype(np.float32), m > 0


def tablo_kur(rgb, a):
    t, ang, m = t_aci(a)
    sel = m & (a >= 0.98)
    ti = np.minimum((t[sel] * TB).astype(int), TB - 1)
    ai = (ang[sel] / (2 * np.pi) * AB).astype(int) % AB
    c = rgb[sel].astype(np.float32)
    L = lum(c)
    tab = np.full((TB, AB, 3), np.nan, np.float32)
    tab_t = np.zeros((TB, 3), np.float32)
    say = np.zeros((TB, AB), int)
    ic_std = []
    aci_std = []
    for i in range(TB):
        ki = ti == i
        tab_t[i] = np.median(c[ki], 0) if ki.any() else (tab_t[i - 1] if i else np.median(c, 0))
        meds = []
        for j in range(AB):
            k = ki & (ai == j)
            say[i, j] = int(k.sum())
            if k.sum() >= 30:
                tab[i, j] = np.median(c[k], 0)
                ic_std.append(float(L[k].std()))
                meds.append(float(np.median(L[k])))
        if len(meds) >= 4:
            aci_std.append(float(np.std(meds)))
    aci_etki = float(np.mean(aci_std)) if aci_std else 0.0
    gurultu = float(np.median(ic_std)) if ic_std else 1.0
    yalniz_t = aci_etki / max(gurultu, 1e-3) < ACI_ESIK
    for i in range(TB):
        for j in range(AB):
            if np.isnan(tab[i, j, 0]):
                tab[i, j] = tab_t[i]
    return tab, tab_t, dict(tb=TB, ab=AB, yalniz_t=bool(yalniz_t), aci_etkisi_luma_std=round(aci_etki, 2), kutu_ici_gurultu_luma_std=round(gurultu, 2),
                            oran=round(aci_etki / max(gurultu, 1e-3), 3), bos_kutu=int((say < 30).sum()), kaynak_piksel=int(sel.sum()),
                            t_profili_luma=[round(float(lum(tab_t[i][None])[0]), 1) for i in range(TB)])


def profil_boya(a_t, tab, tab_t, yalniz_t):
    """hedef alfa (kutu) -> renk: 4x buyukte t / aci, tablo, alfa agirlikli kucultme."""
    h, w = a_t.shape
    a4 = np.clip(cv2.resize(a_t, (w * SS, h * SS), interpolation=cv2.INTER_CUBIC), 0, 1)
    t, ang, m = t_aci(a4)
    tf = t * TB - 0.5
    i0 = np.clip(np.floor(tf).astype(int), 0, TB - 1); i1 = np.clip(i0 + 1, 0, TB - 1)
    f = np.clip(tf - np.floor(tf), 0, 1)[..., None]
    if yalniz_t:
        col = tab_t[i0] * (1 - f) + tab_t[i1] * f
    else:
        aj = (ang / (2 * np.pi) * AB).astype(int) % AB
        col = tab[i0, aj] * (1 - f) + tab[i1, aj] * f
    wgt = a4[..., None]
    num = cv2.resize(col * wgt, (w, h), interpolation=cv2.INTER_AREA)
    den = cv2.resize(a4, (w, h), interpolation=cv2.INTER_AREA)[..., None]
    out = np.where(den > 1e-4, num / np.maximum(den, 1e-4), tab_t[TB // 2][None, None, :])
    tt = cv2.resize(t * a4, (w, h), interpolation=cv2.INTER_AREA) / np.maximum(den[..., 0], 1e-4)
    return out.astype(np.float32), tt.astype(np.float32)


def lab_ton(rgb):
    lab = cv2.cvtColor((np.clip(rgb, 0, 255) / 255.0).astype(np.float32).reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    return np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360


def ton_kapisi(rgb, M, ref):
    """bagimsiz ton olcusu (a114ddb inceleme bulgu 5): her oge altin cekirdegi (alfa >= 0.98) Lab ton acisi ortancasi ana sembol KAYNAK
    cekirdek ton araligi (p5-p95) icinde mi; B >= R orani."""
    r = {}
    for ad, m in M.items():
        ce = m >= 0.98
        if ce.sum() < 20:
            continue
        h = lab_ton(rgb[ce].astype(np.float32))
        r[ad] = dict(ton_ortanca=round(float(np.median(h)), 1), aralikta=bool(ref[0] - 2 <= np.median(h) <= ref[1] + 2),
                     b_ge_r_yuzde=round(float((rgb[ce][:, 2] >= rgb[ce][:, 0]).mean() * 100), 2))
    return r


def oge_renk_profil(Y, model, td, ad, varyant, kazanc):
    rgb, a, x, y = Y['E'][ad]
    if ad == 'sembol':
        cc = np.zeros((N, N, 3), np.float32)
        h, w = a.shape
        xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
        cc[ya:yb, xa:xb] = rgb[ya - y:yb - y, xa - x:xb - x]
    else:
        cc = PROFIL[ad].copy()
    return np.clip(cc * kazanc * KAT.get(ad, 1.0), 0, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--son', required=True)
    a = ap.parse_args()
    K, O, SON = Path(a.kaynak), Path(a.cikti), Path(a.son)
    O.mkdir(parents=True, exist_ok=True)
    for f, h in son.GERCEK.items():
        if not o1.sha(K / f).startswith(h):
            print('FAIL kaynak sha', f, flush=True); return 1
    o4.YASAK = o4.yasak_m()
    o4.GLOW_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * o4.GLOW_R + 1,) * 2)
    o3.YASAK = o4.YASAK
    spec = importlib.util.spec_from_file_location('tek_doku', K / 'tek_doku.py')
    td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)
    pp = o4.poster_profil(K / 'HALKA_BLUE_16x20.png')
    ana0 = np.asarray(Image.open(K / 'CANCER_LIBRA_ana.png').convert('RGBA'), np.float32)
    ana0[..., 3] /= 255.0
    ana0 = o1.kirp(ana0, ana0[..., 3], pad=2)
    if ana0.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(ana0, 1600 / ana0.shape[1]); ana0 = np.dstack([r_, a_])
    ana5, _ = o5.delik_kapat(ana0)
    ic_, _ = o5.leke_ic_kaynak(ana5[..., 3]); o5.KAYNAK_SONRA['ana'] = int((ic_ & (ana5[..., 3] < 0.9)).sum())
    tab, tab_t, tab_bilgi = tablo_kur(ana5[..., :3], ana5[..., 3])
    hk = lab_ton(ana5[..., :3][ana5[..., 3] >= 0.98].astype(np.float32))
    TON_REF = (float(np.percentile(hk, 5)), float(np.percentile(hk, 95)))
    print('TABLO', json.dumps({k: v for k, v in tab_bilgi.items() if k != 't_profili_luma'}), flush=True)
    lsrc = o4.logo_kaynak(K / 'LOGO_1.png')
    cap = o4.CAP0
    G = int(math.ceil(o5.BOSLUK_ORAN * cap))

    def kucuk(burc, h_ratio):
        g = np.asarray(Image.open(K / f'{burc}_symbol_gold.png').convert('RGBA'), np.float32)
        g[..., 3] /= 255.0
        g = o1.kirp(g, g[..., 3], pad=2)
        g, _ = o5.delik_kapat(g)
        ic2, _ = o5.leke_ic_kaynak(g[..., 3]); o5.KAYNAK_SONRA[burc] = int((ic2 & (g[..., 3] < 0.9)).sum())
        gx0, gy0, gx1, gy1 = o1.bbox(g[..., 3], 0.5)
        rgb_, a_ = o1.rgba_olcek(g, h_ratio * cap / (gy1 - gy0))
        rgb_, a_, _ = o5.hedef_kapat(rgb_, a_)
        return rgb_, a_
    k_ = cap * o4.LOGO_H / lsrc.shape[0]
    la = np.clip(cv2.resize(lsrc, (max(1, int(round(lsrc.shape[1] * k_))), max(1, int(round(cap * o4.LOGO_H)))), interpolation=cv2.INTER_AREA), 0, 1)
    T = dict(isim1=o1.metin_alfa('EMILY', K / 'Cinzel.ttf', cap, 500), isim2=o1.metin_alfa('JAMES', K / 'Cinzel.ttf', cap, 500),
             tarih=o1.metin_alfa('14 JUNE 2025', K / 'EBGaramond-Italic.ttf', P['tagline_T'] / P['cap'] * cap, None, ref='T'), sonsuz=la, cap=cap)
    kc = {'sol': kucuk('cancer', P['kucuk_sol_h'] / P['cap']), 'sag': kucuk('libra', P['kucuk_sag_h'] / P['cap'])}
    ha, hb = o5.halka_T(pp, son.S0)
    Y, bilgi = o5.yerlesim_V5(pp, ana5, T, kc, ha, hb, G)
    if Y is None:
        print('FAIL yerlesim', flush=True); return 1
    model = son.model_kur(td, Y)
    # profil boyama: her oge (sembol haric) kendi alfasindan; t haritalari kapilar icin
    TT = {}
    for ad, (rgb_, a_, x, y) in Y['E'].items():
        if ad == 'sembol':
            continue
        if ad == 'halka':
            ys, xs = np.nonzero(a_ > 0.002)
            y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
            col, tt = profil_boya(a_[y0:y1, x0:x1], tab, tab_t, tab_bilgi['yalniz_t'])
            cc = np.zeros((N, N, 3), np.float32); cc[y0:y1, x0:x1] = col
            T_ = np.zeros((N, N), np.float32); T_[y0:y1, x0:x1] = tt
        else:
            col, tt = profil_boya(a_, tab, tab_t, tab_bilgi['yalniz_t'])
            cc = np.zeros((N, N, 3), np.float32); T_ = np.zeros((N, N), np.float32)
            h, w = a_.shape
            xa, ya, xb, yb = max(0, x), max(0, y), min(N, x + w), min(N, y + h)
            cc[ya:yb, xa:xb] = col[ya - y:yb - y, xa - x:xb - x]; T_[ya:yb, xa:xb] = tt[ya - y:yb - y, xa - x:xb - x]
        PROFIL[ad] = cc
        TT[ad] = T_
    # ana sembol t haritasi (hedef olcek, ayni yontem; duzgunluk referansi)
    rgb_s, a_s, xs_, ys_ = Y['E']['sembol']
    _, tts = profil_boya(a_s, tab, tab_t, True)
    T_ = np.zeros((N, N), np.float32); h, w = a_s.shape
    xa, ya, xb, yb = max(0, xs_), max(0, ys_), min(N, xs_ + w), min(N, ys_ + h)
    T_[ya:yb, xa:xb] = tts[ya - ys_:yb - ys_, xa - xs_:xb - xs_]
    TT['sembol'] = T_
    al.oge_renk = oge_renk_profil
    um = o5.uc_maske(pp, son.S0)

    def duzgunluk(rgb):
        L = lum(rgb.astype(np.float32))
        r = {}
        for ad in TT:
            m = (Y['M'][ad] >= 0.98) & (TT[ad] >= BANT[0]) & (TT[ad] <= BANT[1])
            r[ad] = dict(luma_std=round(float(L[m].std()), 2) if m.sum() >= 10 else None, piksel=int(m.sum()))
        ref = r['sembol']['luma_std']
        for ad in r:
            r[ad]['oran'] = round(r[ad]['luma_std'] / ref, 3) if (r[ad]['luma_std'] is not None and ref) else None
        return r

    def sureklilik(rgb):
        """halka orta ekseni: 0.05 derece adim, merkez cizgi pikseli (alfa >= 0.9) luma; 3 px pencere ortalamasi."""
        L = lum(rgb.astype(np.float32))
        hm = Y['M']['halka']
        ax, by, cy = hb['ax'], hb['by'], hb['cy']
        T_ = np.arange(0, 360, 0.05)
        tr = np.radians(T_)
        px = CX + ax * np.cos(tr); py = cy + by * np.sin(tr)
        al_ = cv2.remap(hm, (px - 0.5).astype(np.float32)[None], (py - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        Lv = cv2.remap(L, (px - 0.5).astype(np.float32)[None], (py - 0.5).astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        ok = al_ >= 0.9
        ds = np.hypot(np.diff(np.r_[px, px[0]]), np.diff(np.r_[py, py[0]]))
        s = np.cumsum(ds)
        # yalniz govde (alfa >= 0.9) parcalari; 3 px pencere
        idx = np.nonzero(ok)[0]
        med = float(np.median(Lv[ok]))
        en_kotu = 1e9; yer = None
        for i in idx[::4]:
            w_ = ok & (np.abs(s - s[i]) <= 1.5)
            v = float(Lv[w_].mean())
            if v < en_kotu:
                en_kotu, yer = v, float(T_[i])
        return dict(ortanca=round(med, 1), en_dusuk_3px=round(en_kotu, 1), oran=round(en_kotu / med, 3), en_dusuk_aci=yer,
                    olculen_yay_px=round(float(ds[ok].sum()), 1), not_='yalniz orta eksende alfa >= 0.9 olan govde (incelen uclarin < 0.9 kismi haric)')

    def olc(rgb, once, z):
        ok = {k: o5.kontrast_yeni(rgb, Y['M'][k], 'koyu') for k in ('isim1', 'isim2', 'tarih', 'kucuk_sol', 'kucuk_sag')}
        ok['halka_uclari'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[0], 'koyu')
        ok['halka_uclari_2px_alti'] = o5.kontrast_yeni(rgb, Y['M']['halka'] * um[1], 'koyu', cekirdek=0.5)
        ok['sonsuz_bilgi'] = o5.kontrast_yeni(rgb, Y['M']['sonsuz'], 'koyu', cekirdek=0.5)
        kk = [v for k, v in ok.items() if k not in ('halka_uclari_2px_alti', 'sonsuz_bilgi') and v.get('deger') is not None]
        gy, gb = o4.goruntu_yasak(rgb, z, Y['M'].get('halka'))
        return dict(kontrast_ortanca_en_kotu=round(min(v['ortanca_bilgi'] for v in kk), 2), kati_en_kotu_bilgi=round(min(v['deger'] for v in kk), 2),
                    kontrast=ok, goruntu_yasak=gy, goruntu=gb, leke=o5.leke_kapisi(Y['M'], rgb, None),
                    renk_sadakati=al.renk_sadakati(rgb, once, Y['M']), bosluk_px=o5.bosluklar(Y['E']), sembol_kutu=list(o5.kutu(Y['E'], 'sembol')),
                    duzgunluk=duzgunluk(rgb), halka_sureklilik=sureklilik(rgb), ton_lab=ton_kapisi(rgb, Y['M'], TON_REF))
    R = {'kaynak_sha256': {f.name: o1.sha(f) for f in sorted(K.iterdir()) if f.is_file()}, 'tablo': tab_bilgi,
         'ayar': dict(dis_golge=al.DIS_GOLGE, ic_golge=al.IC_GOLGE, dusus=al.DUSUS, ss=SS, bant=BANT, duz_oran=DUZ_ORAN, surek_oran=SUREK_ORAN),
         'yerlesim': bilgi, 'sonuc': {}, 'ton_referans_lab_p5_p95': [round(TON_REF[0], 1), round(TON_REF[1], 1)],
         'inceleme_a114ddb_not': ('dusus tabani (0.92) sembol disi ogelerde duz carpan gibi calisiyor; isik tasmasi kaldirildi (gorevde yok); '
                                  'ikisi Merkez ayari / karari; bu iste degistirilmedi')}
    rgbler = {}
    for renk, zf in al.RENKLER:
        z = o1.zemin_canva(K / zf)
        KAT.clear()
        rgb, once = al.boya_altin(Y, model, z, td, 'G2', 1.0)
        r = olc(rgb, once, z)
        artis = 1.0
        if renk == 'RUBY' and r['kontrast_ortanca_en_kotu'] < o4.HEDEF:
            for k100 in range(101, 161):
                artis = k100 / 100
                KAT.clear(); KAT.update({k: artis for k in KUCUK_OGE})
                rgb, once = al.boya_altin(Y, model, z, td, 'G2', 1.0)
                r = olc(rgb, once, z)
                if r['kontrast_ortanca_en_kotu'] >= o4.HEDEF:
                    break
        r['kucuk_oge_parlaklik_artisi'] = round(artis, 2)
        R['sonuc'][renk] = r
        rgbler[renk] = rgb
        o1.kaydet(rgb, O / f'CANCER_LIBRA_{renk}_954.png')
        dz = r['duzgunluk']
        print(renk, 'ortanca', r['kontrast_ortanca_en_kotu'], 'kati', r['kati_en_kotu_bilgi'], 'artis', artis, 'yasak', sum(r['goruntu_yasak'].values()),
              'leke', sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE),
              'dhue', max(v['dhue_ortanca'] for v in r['renk_sadakati'].values()), 'B>=R', max(v['b_ge_r_yuzde'] for v in r['renk_sadakati'].values()),
              'duzgunluk oran max', max(v['oran'] for v in dz.values() if v['oran'] is not None), {k: v['oran'] for k, v in dz.items()},
              'halka', r['halka_sureklilik']['oran'], flush=True)
    font = ImageFont.truetype(str(K / 'EBGaramond-Italic.ttf'), 24)
    liste, et = [], []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD', 'BEIGE', 'AGED_PAPYRUS'):
        if renk in rgbler:
            r = R['sonuc'][renk]
            liste.append(rgbler[renk])
            et.append(f'{renk}: G2 kesit profili\nortanca {r["kontrast_ortanca_en_kotu"]} {"PASS" if r["kontrast_ortanca_en_kotu"] >= 4.5 else "FAIL"}, kati {r["kati_en_kotu_bilgi"]}\n'
                      f'duzgunluk en cok x{max(v["oran"] for v in r["duzgunluk"].values() if v["oran"] is not None)}, halka {r["halka_sureklilik"]["oran"]}\n'
                      f'kucuk oge parlaklik x{r["kucuk_oge_parlaklik_artisi"]}')
        else:
            liste.append(np.asarray(Image.open(SON / f'CANCER_LIBRA_{renk}_954.png').convert('RGB')))
            et.append(f'{renk}: a5e3ea2 (onayli, aynen)')
    son.onizleme_etiketli(liste, et, font, h_et=130).save(O / 'ONIZLEME_76mm_5RENK.png', dpi=(300, 300))
    kut = {k: o5.kutu(Y['E'], k) for k in ('sembol', 'kucuk_sol', 'isim1')}
    s = kut['sembol']; ks = kut['kucuk_sol']; i1 = kut['isim1']
    t45 = math.radians(-35)
    hx, hy = int(CX + hb['ax'] * math.cos(t45)), int(hb['cy'] + hb['by'] * math.sin(t45))
    kesit = {'ana sembol': (s[0] + 20, s[1] + 150, s[0] + 120, s[1] + 230), 'kucuk Yengec': (ks[0] - 4, ks[1] - 4, ks[2] + 4, ks[3] + 4),
             'isim EMILY': (i1[0] - 4, i1[1] - 4, i1[2] + 4, i1[3] + 4), 'halka': (hx - 40, hy - 40, hx + 40, hy + 40)}
    satir = []
    for renk in ('RUBY', 'SAPPHIRE', 'EMERALD'):
        parcalar = []
        for ad, bx in kesit.items():
            im = Image.fromarray(rgbler[renk]).crop(bx)
            im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
            c = Image.new('RGB', (max(im.width, 230), im.height + 36), 'white'); c.paste(im, (0, 0))
            ImageDraw.Draw(c).text((4, im.height + 4), f'{renk} {ad} (3x)', fill=(20, 20, 20), font=font)
            parcalar.append(c)
        W = sum(c.width for c in parcalar) + 24 * 3; H = max(c.height for c in parcalar)
        sr = Image.new('RGB', (W, H), 'white'); x = 0
        for c in parcalar:
            sr.paste(c, (x, 0)); x += c.width + 24
        satir.append(sr)
    u = Image.new('RGB', (max(s_.width for s_ in satir), sum(s_.height for s_ in satir) + 24 * 2), 'white'); y = 0
    for s_ in satir:
        u.paste(s_, (0, y)); y += s_.height + 24
    u.save(O / 'YAKIN_DOKU.png')
    A = list(R['sonuc'].values())
    g = dict(kontrast_ortanca=all(r['kontrast_ortanca_en_kotu'] >= o4.HEDEF for r in A),
             goruntu_yasak_0=all(sum(r['goruntu_yasak'].values()) == 0 for r in A),
             leke_a_0=all(sum(v['alfa_lt_09'] for k2, v in r['leke'].items() if k2 in o5.LEKE_KAPI_OGE) == 0 for r in A),
             leke_a_kaynak_0=all(v == 0 for v in o5.KAYNAK_SONRA.values()),
             renk_sadakati=all(v['dhue_ortanca'] < 1.0 and v['b_ge_r_yuzde'] == 0 for r in A for v in r['renk_sadakati'].values()),
             ton_lab_kaynak_araliginda=all(v['aralikta'] and v['b_ge_r_yuzde'] == 0 for r in A for v in r['ton_lab'].values()),
             yerlesim_ayni=all(r['bosluk_px'] == [20, 20, 20] and r['sembol_kutu'][1] == 246 for r in A),
             duzgunluk=all(v['oran'] is not None and v['oran'] <= DUZ_ORAN for r in A for v in r['duzgunluk'].values()),
             halka_sureklilik=all(r['halka_sureklilik']['oran'] >= SUREK_ORAN for r in A),
             artis_yalniz_ruby=all(R['sonuc'][r]['kucuk_oge_parlaklik_artisi'] == 1.0 for r in ('SAPPHIRE', 'EMERALD')))
    g = {k: bool(v) for k, v in g.items()}
    R['kapi'] = g
    R['kaynak_leke_onarim_sonrasi'] = dict(o5.KAYNAK_SONRA)
    (O / 'OLCUM.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float))
    print('KAPI', json.dumps(g), 'PASS' if all(g.values()) else 'FAIL', flush=True)
    return 0 if all(g.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
