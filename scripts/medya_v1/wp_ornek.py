#!/usr/bin/env python3
"""WP KATMAN ORNEKLERI + KIMLIK TESTI (30 Eyl 2026, Serdar). Etsy/Prodigi/musteri YOK.

Cift x boy basina:
  1) Ogrenme (onayli kaynaklardan): CI kaynak - CI plate  <->  WP kaynak - WP plate
     bant bazli afin hizalama + renk modeli (wp_katman).
  2) WP plate temizligi (slogan / eski iz); medyan plate kalirsa Canva plate denenir.
  3) Duz renkte (CI, olmazsa MB) mevcut hatla iki baski: KIMLIK (kaynagin burc adlari + slogani)
     ve SIPARIS (EMILY / JAMES / mesaj). Kapilar o renkte.
  4) Katman: baski - plate -> WP geometrisi -> WP murekkebi -> WP plate uzerine.
  5) Kimlik farki (dE) tabloya; ornek dosyalar Drive TEMP/WP_ORNEK/<CIFT>/.
"""
import argparse, io, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import wp_katman as wk                                           # noqa: E402
import wp_bakir as wb                                            # noqa: E402

Image.MAX_IMAGE_PIXELS = None
HEDEF = 'gdrive:ASTROLOVE/TEMP/WP_ORNEK'
SLOGAN = 'Two Souls · One Bond'                                 # kisisel_pilot.ORIG_TAGLINE
ISIM = ('EMILY', 'JAMES')
MESAJ = 'It Began With a Kiss in the Rain'
DUZ_RENK = ('CHAMPAGNE_IVORY', 'MIDNIGHT_BLUE')
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def plate_indir(ad):
    yol = sd.W / 'plates' / ad
    yol.parent.mkdir(parents=True, exist_ok=True)
    if not yol.exists():
        try:
            sd.rc('copy', f'{sd.PLATES}/{ad}', str(yol.parent), timeout=1800)
        except RuntimeError:
            return None
    return yol if yol.exists() else None


def baski(x, kaynak_yol, P_ed, P_blue, cik):
    sd._TANI = {}
    try:
        r = sd.pod_uret(x, kaynak_yol.read_bytes(), P_blue, P_ed, cik)
        t = sd._TANI
    finally:
        sd._TANI = None
    return r, t


def etiketle(hiz, olcum, k, H):
    """Hat olcumu (CI, 2400 birimi) -> WP satirlari: y_wp = y_ci - dy (bolgenin kaymasi)."""
    et = {}
    for ad, alan in (('isim', 'isim_bant'), ('mesaj', 'tag_bant'), ('kucuk_sembol', 'sembol_bant')):
        v = (olcum or {}).get(alan)
        if not v:
            continue
        y0, y1 = v[0] * k, v[1] * k
        yc = (y0 + y1) / 2
        s = min(hiz, key=lambda h: 0 if h['bolge'][0] <= yc - h['dy'] < h['bolge'][1]
                else min(abs(yc - h['dy'] - h['bolge'][0]), abs(yc - h['dy'] - h['bolge'][1])))
        et[ad] = [int(max(0, y0 - s['dy'] - 6)), int(min(H, y1 - s['dy'] + 6))]
    kul = [b for b in hiz if not any(a <= (b['bant'][0] + b['bant'][1]) / 2 < z for a, z in et.values())]
    if kul:
        b = max(kul, key=lambda h: h['bant'][1] - h['bant'][0])
        et['buyuk_sembol'] = list(b['bant'])
    return et


def kaydet_jpg(a, yol, q=95):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(yol, 'JPEG', quality=q, subsampling=0)


def yanyana(sol, sag, yol, H=1800, bant=None, etiket=('YENI (katman)', 'ONAYLI WP')):
    from PIL import ImageDraw
    def k(a, h):
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    A, B = k(sol, H), k(sag, H)
    parca = []
    if bant:
        y0, y1 = bant
        x0, x1 = int(sol.shape[1] * 0.08), int(sol.shape[1] * 0.92)
        ca = Image.fromarray(np.clip(sol[y0:y1, x0:x1], 0, 255).astype(np.uint8))
        cb = Image.fromarray(np.clip(sag[y0:y1, x0:x1], 0, 255).astype(np.uint8))
        en = A.width + B.width + 30
        if ca.width > en:
            ca = ca.resize((en, round(ca.height * en / ca.width)), Image.LANCZOS)
            cb = cb.resize(ca.size, Image.LANCZOS)
        parca = [ca, cb]
    geo = {'x0': int(sol.shape[1] * 0.08) if bant else 0, 'y0': bant[0] if bant else 0,
           'olcek': (parca[0].width / (int(sol.shape[1] * 0.92) - int(sol.shape[1] * 0.08))) if parca else 1.0,
           'panel_y': []}
    tH = H + 60 + sum(p.height + 50 for p in parca)
    t = Image.new('RGB', (A.width + B.width + 30, tH), 'white')
    d = ImageDraw.Draw(t)
    t.paste(A, (0, 50)); t.paste(B, (A.width + 30, 50))
    d.text((10, 15), etiket[0], fill='black'); d.text((A.width + 40, 15), etiket[1], fill='black')
    y = H + 60
    for p, e in zip(parca, (etiket[0] + ' isim bandi 1:1', etiket[1] + ' isim bandi 1:1')):
        d.text((10, y), e, fill='black'); t.paste(p, (0, y + 20)); geo['panel_y'].append(y + 20); y += p.height + 50
    if yol is not None:
        t.save(yol, 'JPEG', quality=90)
    return t, geo


def yanyana_baski(geo, x, y, panel=1):
    """Yanyana gorsel koordinati -> baski dosyasi koordinati (alt panel = 1, yeni baski)."""
    return (geo['x0'] + x / geo['olcek'], geo['y0'] + (y - geo['panel_y'][panel]) / geo['olcek'])


def sutun_profili(img_u8, x0, x1, y0, y1):
    L = np.asarray(img_u8.convert('L') if hasattr(img_u8, 'convert') else img_u8, np.float32)
    return [round(float(v), 1) for v in L[y0:y1 + 1, x0:x1 + 1].mean(0)]


def koyu_sutun(pr):
    """Her sutun: cevresi (+-2 sutun disindaki profil ortancasi) - kendisi. En buyugu (gri seviye)."""
    pr = np.asarray(pr, np.float32)
    en = 0.0
    for i in range(len(pr)):
        cev = np.r_[pr[:max(0, i - 2)], pr[i + 3:]]
        en = max(en, float(np.median(cev) - pr[i]))
    return round(en, 1)


def _kume(m, bosluk):
    kol = np.nonzero(m.sum(0) > 0)[0]
    if not len(kol):
        return []
    out, a, b = [], kol[0], kol[0]
    for x in kol[1:]:
        if x - b > bosluk:
            out.append([int(a), int(b) + 1]); a = x
        b = x
    out.append([int(a), int(b) + 1])
    return out


def sonsuz_olc(S_c, B, P_c, isim_bant, k):
    """Isim satiri: [isim1] bosluk [sonsuz] bosluk [isim2] (sutun kumeleri). Kaynak ve hat icin kutular,
    iki bosluk, sonsuz merkez farki ve isim1 genislik farki. Kural: iki bosluk esit, satir ortali."""
    H, Wd = S_c.shape[:2]
    y0, y1 = int(isim_bant[0] * k) - int(20 * k), int(isim_bant[1] * k) + int(20 * k)
    x0 = int(Wd * 0.05)
    def bir(A):
        m = wk.murekkep_maskesi((A - P_c)[y0:y1, x0:Wd - x0], kenar=0)
        ys = np.nonzero(m.any(1))[0]
        h = (ys[-1] - ys[0] + 1) if len(ys) else 1
        kk = [[a + x0, b + x0] for a, b in _kume(m, max(int(0.45 * h), 6))]
        if len(kk) != 3:
            return {'kume': kk, 'hata': f'{len(kk)} kume'}
        return {'isim1': kk[0], 'sonsuz': kk[1], 'isim2': kk[2],
                'bosluk': [kk[1][0] - kk[0][1], kk[2][0] - kk[1][1]],
                'satir_merkez': round((kk[0][0] + kk[2][1]) / 2, 1),
                'sonsuz_merkez': round((kk[1][0] + kk[1][1]) / 2, 1)}
    a, b = bir(S_c), bir(B)
    r = {'kaynak': a, 'hat': b}
    if 'hata' not in a and 'hata' not in b:
        r['sonsuz_dx'] = round(b['sonsuz_merkez'] - a['sonsuz_merkez'], 1)
        r['isim1_en_farki'] = (b['isim1'][1] - b['isim1'][0]) - (a['isim1'][1] - a['isim1'][0])
        r['bosluk_farki'] = [b['bosluk'][0] - a['bosluk'][0], b['bosluk'][1] - a['bosluk'][1]]
        r['satir_merkez_farki'] = round(b['satir_merkez'] - a['satir_merkez'], 1)
    return r


SERDAR_YAN = (1290, 1311, 3975, 4234)      # v2 YANYANA (2864x4286) olcum penceresi; cizgi x 1298-1301
V2_YANYANA = sd.W / 'v2_yanyana.jpg'


SERDAR_SERIT = (1561, 1567, 3490, 3750)   # Serdar 1 Eki onayi: plate'te YALNIZ x 1561-1566 / y 3490-3749


def _yazi_maskesi(rgb, ince=False):
    """Yazi maskesi (yerel ortancadan 25 luma koyu, 5x5 genisletme). ince=True: genisligi <= 8 px ve boyu >= 50 px
    olan bilesenler (dikey kil cizgi; v2 YANYANA 'With'/'a' arasi, 1 Eki) yazi SAYILMAZ."""
    L = rgb @ wk.LUMA
    z = cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 31).astype(np.float32)
    m = ((z - L) > 25).astype(np.uint8)
    if ince:                                   # parcali cizgi: once dikeyde 15 px kapat, sonra bilesen olc
        mk = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 1), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(mk, 8)
        cizgi = np.zeros(n, bool)
        cizgi[1:] = (st[1:, cv2.CC_STAT_WIDTH] <= 8) & (st[1:, cv2.CC_STAT_HEIGHT] >= 50)
        m[cizgi[lab] & (m > 0)] = 0
    return cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(bool)


def yanyana_dedektor(img, geo, h, ofset=(0, 0)):
    """wb.dikis'i yanyana gorselinin alt panelinde calistirir; Serdar penceresiyle kesisen dikey cizgiler.
    Yazi maskesi ince-uzun bilesenleri yazi saymaz ve kontrast ust siniri 120 (v2 cizgisi 35-45 luma; 30 ust
    sinir ve yazi maskesi onu yaziya sayiyordu -> v2'de yanlis PASS). Cizgi kesikli (v2: ~85 px + 22 px bosluk
    + 15 px): ayni sutunda 30 satira kadar bosluk kapatilir. ofset: img bir kesitse sol-ust koordinati."""
    x0, x1, y0, y1 = SERDAR_YAN
    # yerel pencere (x +-60, y0-75..panel sonu): tam gorsel ve kesit ayni sonucu verir, uzak sutunlar gruplanmaz
    kx0, ky0 = x0 - 60 - ofset[0], y0 - 75 - ofset[1]
    A = np.asarray(img.convert('RGB')).astype(np.float32)[ky0:, kx0:x1 + 61 - ofset[0]]
    ox, oy = x0 - 60, y0 - 75
    sm = np.zeros(A.shape[0], bool)
    p0 = geo['panel_y'][1] - oy; sm[max(0, p0):max(0, p0 + h)] = True
    c = wb.dikis(A, sm, T=(3.0, 120.0), murekkep=_yazi_maskesi(A, ince=True), bosluk=30,
                 temsil='isabet')
    hit = [{**d, 'x': d['x'] + ox, 'y': [d['y'][0] + oy, d['y'][1] + oy]} for d in c if d['yon'] == 'dikey']
    # Serdar olcutu koyu cizgi: tur koyu ve kosu boyunca ortalama kontrast >= 3 (tek tek isabet esigi kadar)
    hit = [d for d in hit if d['tur'] == 'koyu' and d['kontrast'] >= 3.0
           and x0 + 4 <= d['x'] <= x1 - 6 and d['y'][1] >= y0 and d['y'][0] <= y1]
    return {'cizgi': hit[:5], 'sonuc': 'FAIL (cizgi var)' if hit else 'PASS (cizgi yok)'}


def serdar_dikis(cift, boy, S_wp, P_wp0, B_cu, WP_cu, P_k, w, geo, h, zorla=False):
    """Serdar'in v2 YANYANA'da isaretledigi dikey cizgi: esleme, katman profilleri, yalniz o katmani yalniz o
    seritte (SERDAR_SERIT) plate sutunlarini serit disi temiz komsularin ortalamasina cekme.
    zorla (siparis hatti): cizgi VINTAGE_11x14 plate'inin kendisinde (cifte bagli degil); siparis metni pencereye
    dusebildigi icin katman karari beklenmez, serit her 11x14 sipariste onarilir (ayni islem, ayni serit).
    Donus: (yeni cikti, yeni kagit, rapor)."""
    x0y, x1y, y0y, y1y = SERDAR_YAN
    bx0, by0 = yanyana_baski(geo, x0y, y0y); bx1, by1 = yanyana_baski(geo, x1y, y1y)
    xc = yanyana_baski(geo, 1299.5, y0y)[0]
    bx0, bx1, by0, by1 = int(round(bx0)), int(round(bx1)), int(round(by0)), int(round(by1))
    r = {'esleme': f'yanyana ({x0y}-{x1y}, {y0y}-{y1y}) -> baski ({bx0}-{bx1}, {by0}-{by1}), cizgi x {xc:.1f}'}
    print('ESLEME', cift, boy, r['esleme'], flush=True)
    # katman profilleri (Serdar penceresi, satir ortalamasi)
    pr = {ad: sutun_profili(np.clip(A_ @ wk.LUMA, 0, 255), bx0, bx1, by0, by1)
          for ad, A_ in (('baski', WP_cu), ('plate', P_wp0), ('kagit_kullanilan', P_k), ('onayli', S_wp),
                         ('duz_renk', B_cu))}
    r['profil'] = pr
    r['koyu_sutun'] = {ad: koyu_sutun(v) for ad, v in pr.items()}
    print('KATMAN_PROFIL', cift, boy, json.dumps({'x': [bx0, bx1], 'y': [by0, by1], **pr, 'koyu': r['koyu_sutun']}),
          flush=True)
    kk = r['koyu_sutun']
    # 1 Eki olcumu: baski = plate = kullanilan kagit (13.8), duz renk 0.3 -> cizgi kagit katmaninda. Onayli WP o yerde
    # eski sloganin harfini tasir (6.9), karar onayliya bakmaz.
    if zorla or (kk['kagit_kullanilan'] > 4 and kk['duz_renk'] <= 4):
        r['katman'] = 'plate (kagit)'
    elif kk['duz_renk'] > 4:
        r['katman'] = 'duz renk baskisi'
    elif kk['baski'] > 4:
        r['katman'] = 'bakir render'
    else:
        r['katman'] = 'yok (bu boyda cizgi olculmedi)'
    sx0, sx1, sy0, sy1 = SERDAR_SERIT
    if r['katman'] != 'plate (kagit)' or not (sx0 <= xc < sx1):
        return WP_cu, P_k, r
    # Serdar onayi: yalniz bu seritte, plate sutunlari serit disindaki temiz komsu sutunlarin ortalamasi
    P_new, so = wb.serit_onar(P_k, sx0, sx1, sy0, sy1)
    out = WP_cu + (1 - w[..., None]) * (P_new - P_k)
    degisen = np.abs(out - WP_cu).max(-1) > 0
    disari = degisen.copy(); disari[sy0:sy1, sx0:sx1] = False
    r['onarim'] = {**so, 'degisen_px': int(degisen.sum()), 'serit_disi_degisen_px': int(disari.sum())}
    return np.clip(out, 0, 255), P_new, r


# Serdar 1 Eki ~15:50: 24x36 WP plate'indeki acik dikey cizgi (x 1937, y 4376-4440, sapma 12.2) onarilir; yontem 11x14
# ile ayni (serit, serit disi temiz komsu sutun ortalamasi, yazi haric). Serit cizgiyi (x 1936-1940 acik) ve +-6 satir
# ucu kapsar. Koordinat: baski pikseli (plate baski boyuna olcekli; tarama ile ayni).
PLATE_SERITLER = {'24x36': [(1935, 1941, 4370, 4447)]}
SERIT_KESIT = {'24x36': (1837, 2037, 4276, 4540)}       # inceleme/wp_dikis_24x36 ile ayni 1:1 kesit


def serit_uygula(WP_cu, P_k, w, serit, pay=100):
    """Kagit seridi onarimi, yalniz serit cevresi penceresinde (buyuk boyda tam kopya yok). out = WP + (1-w)(P_yeni - P);
    serit disi degismez (pencerede olculur, pencere disina yazilmaz). WP_cu ve P_k yerinde guncellenir."""
    x0, x1, y0, y1 = serit
    H, W = P_k.shape[:2]
    wx0, wx1, wy0, wy1 = max(0, x0 - pay), min(W, x1 + pay), max(0, y0 - pay), min(H, y1 + pay)
    Pw = P_k[wy0:wy1, wx0:wx1]
    Pn, so = wb.serit_onar(Pw, x0 - wx0, x1 - wx0, y0 - wy0, y1 - wy0)
    once = WP_cu[wy0:wy1, wx0:wx1].copy()
    sonra = np.clip(once + (1 - w[wy0:wy1, wx0:wx1, None]) * (Pn - Pw), 0, 255)
    degisen = np.abs(sonra - once).max(-1) > 0
    disari = degisen.copy(); disari[y0 - wy0:y1 - wy0, x0 - wx0:x1 - wx0] = False
    WP_cu[wy0:wy1, wx0:wx1] = sonra
    P_k[wy0:wy1, wx0:wx1] = Pn
    return {**so, 'serit': {'x': [x0, x1 - 1], 'y': [y0, y1 - 1]}, 'degisen_px': int(degisen.sum()),
            'serit_disi_degisen_px': int(disari.sum())}


def plate_serit_onar(cift, boy, S_wp, WP_cu, P_k, w, og_k, hn_k, cik):
    """PLATE_SERITLER[boy] seritlerini onarir; once/sonra: kapi sapmasi (onayliya gore), seritteki sutun profili,
    kontrast (g ile ayni olcum), 1:1 kesit PNG (Drive TEMP/WP_ORNEK/<CIFT>/)."""
    import wp_dikis_kapisi as dk
    r = {'kontrast_once': {a: v['kontrast'] for a, v in wb.kontrast_olc(WP_cu, P_k, og_k, hn_k).items()}, 'seritler': []}
    k = SERIT_KESIT.get(boy)
    if k:
        Image.fromarray(np.clip(WP_cu[k[2]:k[3], k[0]:k[1]], 0, 255).astype(np.uint8)).save(
            cik / f'WP_{cift}_{boy}_SERIT_ONCE_1e1.png')
    for x0, x1, y0, y1 in PLATE_SERITLER[boy]:
        wx0, wx1, wy0, wy1 = x0 - 100, x1 + 100, y0 - 100, y1 + 100
        sat = np.ones(wy1 - wy0, bool)
        pr = lambda A: [round(float(v), 1) for v in (A[y0:y1, x0 - 12:x1 + 12] @ wk.LUMA).mean(0)]
        o = {'profil_once': pr(WP_cu), 'kapi_once': dk.kapi(WP_cu[wy0:wy1, wx0:wx1], S_wp[wy0:wy1, wx0:wx1], sat)}
        o.update(serit_uygula(WP_cu, P_k, w, (x0, x1, y0, y1)))
        o['profil_sonra'] = pr(WP_cu)
        o['kapi_sonra'] = dk.kapi(WP_cu[wy0:wy1, wx0:wx1], S_wp[wy0:wy1, wx0:wx1], sat)
        r['seritler'].append(o)
    if k:
        Image.fromarray(np.clip(WP_cu[k[2]:k[3], k[0]:k[1]], 0, 255).astype(np.uint8)).save(
            cik / f'WP_{cift}_{boy}_SERIT_SONRA_1e1.png')
    r['kontrast_sonra'] = {a: v['kontrast'] for a, v in wb.kontrast_olc(WP_cu, P_k, og_k, hn_k).items()}
    r['gecti'] = bool(all(s['kapi_sonra']['gecti'] and s['serit_disi_degisen_px'] == 0 for s in r['seritler'])
                      and all(abs(r['kontrast_sonra'].get(a, 0) - v) <= 0.02 for a, v in r['kontrast_once'].items()))
    return WP_cu, P_k, r


def kapi_ozet(r):
    k = r.get('kapilar') or {}
    return {'durum': r.get('durum'), 'hata': r.get('hata'), 'kapilar_gecti': r.get('kapilar_gecti'),
            'kalan': sorted(g for g, v in k.items() if v is False), 'kapilar': k}


def cift_boy(cift, boy, P_ed, P_blue, no, cik, isim=ISIM, mesaj=MESAJ, siparis=False):
    R = {'cift': cift, 'boy': boy}
    oran = sd.BOY[boy][0]
    S_wp_yol = sd.pod_kaynak(cift, 'WARM_PARCHMENT', boy)
    S_wp = wk.dizi(S_wp_yol); H, Wd = S_wp.shape[:2]
    R['wp_px'] = [Wd, H]
    x0 = None
    for renk in DUZ_RENK:
        ed = sd.RENK_ED[renk]
        t0 = time.time()
        S_c_yol = sd.pod_kaynak(cift, renk, boy)
        P_c = wk.boyutla(wk.dizi(P_ed.plate(ed, oran, boy)), (Wd, H))
        S_c = wk.boyutla(wk.dizi(S_c_yol), (Wd, H))
        # ---- 3) duz renkte hat baskilari (kapilar bu renkte)
        s1, s2 = cift.split('_', 1)
        uret = {}
        for tur, (i1, i2, m) in (('kimlik', (s1, s2, SLOGAN)), ('siparis', (*isim, mesaj))):
            x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod',
                              'isim1': i1, 'isim2': i2, 'mesaj': m})
            x['receipt'] = f'WPK_{cift}_{boy}_{renk}_{tur}'; x['sayfa'] = no[cift]
            with Image.open(S_c_yol) as im:
                x['hedef_px'] = list(im.size)
            d = sd.W / x['receipt']; d.mkdir(parents=True, exist_ok=True)
            r, t = baski(x, S_c_yol, P_ed, P_blue, d)
            uret[tur] = (r, t)
            log(cift, boy, renk, tur, kapi_ozet(r)['kalan'], r.get('hata') or '')
        R.setdefault('duz_renk_denemeleri', []).append(
            {'renk': renk, 'kimlik': kapi_ozet(uret['kimlik'][0]), 'siparis': kapi_ozet(uret['siparis'][0]),
             'sn': round(time.time() - t0, 1)})
        if uret['siparis'][0].get('kapilar_gecti') and uret['siparis'][1].get('baski') is not None \
                and uret['kimlik'][1].get('baski') is not None:
            x0 = (renk, ed, S_c, P_c, uret)
            break
    if x0 is None:
        R['durum'] = 'FAIL: duz renk baskisi kapilari gecmedi (CI ve MB)'
        return R, None
    renk, ed, S_c, P_c, uret = x0
    R['duz_renk'] = renk

    # ---- 1) ogrenme: ayni ciftin onayli kaynaklari
    # Serdar 2 Eki (SECENEK A): Canva sayfa 45-78 (GEMINI_LIBRA..VIRGO_VIRGO) onayli WP kagidi farkli doku (TANI 2/3:
    # e_kagit ~2.1, 5 boy, sinir GEMINI_LEO | GEMINI_LIBRA); bu ciftler kendi onayli kaynaklarindan uretilen ikinci
    # plate'i kullanir. Kapilar ve esikler ayni. Sayfa = sayfa_no_tablosu (alfabetik POD_PRINT sirasi).
    ad = f'VINTAGE_B_{boy}.png' if no[cift] >= 45 else f'VINTAGE_{boy}.png'
    y = plate_indir(ad)
    if y is None:                        # 1. kosu: VINTAGE_CANVA 11x14 dokusu kaynakla hizasiz (zemin dE 2.98)
        R['durum'] = f'FAIL: {ad} yok'
        return R, None
    P_wp0 = wk.boyutla(wk.dizi(y), (Wd, H))          # medyan plate: ogrenme + maske (doku kaynakla ayni)
    D_wp = S_wp - P_wp0
    bl = wk.bantlar(wk.murekkep_maskesi(D_wp))
    hiz = wk.hizala(S_c - P_c, D_wp, bl)
    R['hizalama'] = hiz
    k = Wd / 2400.0
    et = etiketle(hiz, uret['kimlik'][0].get('olcum'), k, H)
    R['bantlar'] = et
    # ---- 2) plate: iz olcumu (CI glif maskesi) -> onarim -> yeniden olcum
    # 1 Eki tanisi (36777921388): eski olcut (WP kaynaginda yerel kontrast > 26) parsomen beneklerini glif
    # sayiyor; yazisiz kontrol seridinde bile 7.2-9.7 veriyor -> yanli. Glif maskesi dokusuz CI'dan tasinir.
    Dw_src = wk.katman_tasi(S_c - P_c, hiz, (Wd, H))
    G = wk.glif_maskesi(Dw_src)
    ink = G | wk.murekkep_maskesi(D_wp, kenar=0)
    pt_bant = {a: et[a] for a in ('isim', 'mesaj') if a in et}
    onar_bant = {a: et[a] for a in ('kucuk_sembol', 'isim', 'mesaj') if a in et}
    once = wk.plate_iz(P_wp0, G, pt_bant)
    if once['gecti']:                  # 1 Eki: onarim temiz plate'te harf kenari dokusunu bozuyordu (mesaj dE 5 -> 6)
        P_wp, onarim = P_wp0, {'uygulandi': False, 'sebep': 'iz testi onarimsiz gecti'}
    else:
        P_wp, onarim = wk.plate_onar_glif(P_wp0, G, ink, onar_bant)
    sonra = wk.plate_iz(P_wp, G, pt_bant)
    mk0 = wk.murekkep_maskesi(D_wp, kenar=0)
    zt = wk.ozet(wk.dE(P_wp0, S_wp), ~mk0)
    R['plate'] = {'ad': ad, 'temizlik_once': once, 'onarim': onarim, 'temizlik': sonra,
                  'eski_olcut_once': wk.plate_temizlik(P_wp0, S_wp, pt_bant),
                  'zemin_uyumu': {**zt, 'esik_ort': 0.5, 'gecti': zt.get('ort', 99) <= 0.5}}
    R['plate_gecti'] = bool(sonra['gecti'] and R['plate']['zemin_uyumu']['gecti'])
    # ---- 3) BAKIR (Serdar 1 Eki, 2. karar): tum ogeler (daire dahil) bakir 140/72/28 ve onayli kontrastindan
    # dusuk degil, isim/mesaj onayli kabartmasiyla; kagit = plate (yalniz daire cizgisi altinda inpaint, onayli
    # kagitta olmayan plate dikisleri onayli kagittan onarilir)
    del Dw_src
    daire_c = wb.daire_maskesi(P_c)
    daire = wk.katman_tasi(np.repeat(daire_c[..., None].astype(np.float32), 3, 2), hiz, (Wd, H))[..., 0] > 0.5
    Lp = float(np.median(P_c @ wk.LUMA))
    P_ck, _ = wb.kagit_tabani(P_c, daire_c)
    D_src = wk.katman_tasi(S_c - P_ck, hiz, (Wd, H))
    B_id = wk.boyutla(wk.dizi(uret['kimlik'][1]['baski']), (Wd, H))
    o_id = uret['kimlik'][0].get('olcum') or {}
    if o_id.get('isim_bant'):
        R['sonsuz'] = sonsuz_olc(S_c, B_id, P_c, o_id['isim_bant'], k)
    del B_id

    # ---- 4) siparis (EMILY / JAMES) -> bakir
    r_cu, t_cu = uret['siparis']
    B_cu = wk.boyutla(wk.dizi(t_cu['baski']), (Wd, H))
    D_cu = wk.katman_tasi(B_cu - P_ck, hiz, (Wd, H))
    WP_cu, P_k, rb = wb.bakir_hatti(D_cu, D_src, P_wp, S_wp, daire, et, Lp, k, plate_iz=sonra)
    del D_src
    w_te = rb.pop('_te')
    og_k, hn_k = rb.pop('_kontrast_olc')
    # Serdar 1 Eki (3): v2 YANYANA'daki dikey cizgi -> baski koordinati, katman, yalniz o seritte onarim
    if boy == '11x14' and et:
        yb0 = max(0, min(v[0] for a, v in et.items() if a != 'buyuk_sembol') - 60)
        yb1 = max(v[1] for a, v in et.items() if a != 'buyuk_sembol') + 60
        img0, geo = yanyana(S_wp, WP_cu, None, bant=[yb0, yb1],
                            etiket=('ONAYLI WP (gri-kahve)', f'YENI BAKIR ({isim[0]} / {isim[1]})'))
        hpan = yb1 - yb0
        sdk = {'geo': geo}
        if cift == 'CANCER_LIBRA' and V2_YANYANA.exists():
            v2 = Image.open(V2_YANYANA)
            sdk['v2_boyut'] = list(v2.size)
            sdk['v2_profil'] = sutun_profili(v2, *SERDAR_YAN)
            sdk['v2_koyu'] = koyu_sutun(sdk['v2_profil'])
            sdk['v2_dedektor'] = yanyana_dedektor(v2, geo, hpan)
        rt = io.BytesIO(); img0.save(rt, 'JPEG', quality=90); img0j = Image.open(io.BytesIO(rt.getvalue()))
        sdk['once_profil'] = sutun_profili(img0j, *SERDAR_YAN)
        sdk['once_koyu'] = koyu_sutun(sdk['once_profil'])
        sdk['once_dedektor'] = yanyana_dedektor(img0j, geo, hpan)
        WP_cu, P_k, sr = serdar_dikis(cift, boy, S_wp, P_wp, B_cu, WP_cu, P_k, w_te, geo, hpan, zorla=siparis)
        sdk.update(sr)
        img1, _ = yanyana(S_wp, WP_cu, None, bant=[yb0, yb1],
                          etiket=('ONAYLI WP (gri-kahve)', f'YENI BAKIR ({isim[0]} / {isim[1]})'))
        rt = io.BytesIO(); img1.save(rt, 'JPEG', quality=90); img1j = Image.open(io.BytesIO(rt.getvalue()))
        sdk['sonra_profil'] = sutun_profili(img1j, *SERDAR_YAN)
        sdk['sonra_koyu'] = koyu_sutun(sdk['sonra_profil'])
        sdk['sonra_dedektor'] = yanyana_dedektor(img1j, geo, hpan)
        c_son = wb.kontrast_olc(WP_cu, P_k, og_k, hn_k)            # g ile ayni olcum, onarim sonrasi
        sdk['kontrast_sonra'] = {a: v['kontrast'] for a, v in c_son.items()}
        sdk['kontrast_once'] = rb['qc']['g_kontrast']['yeni']
        sdk['bitti'] = bool(sdk['sonra_koyu'] <= 4 and sdk['sonra_dedektor']['sonuc'].startswith('PASS')
                            and sdk.get('onarim', {}).get('serit_disi_degisen_px', 1) == 0)
        R['serdar_dikis'] = sdk
        print('SERDAR_DIKIS', cift, boy, json.dumps({a: v for a, v in sdk.items() if a not in ('profil',)},
                                                     default=str), flush=True)
    if boy in PLATE_SERITLER:                      # Serdar 1 Eki ~15:50 (24x36 plate seridi)
        WP_cu, P_k, ps = plate_serit_onar(cift, boy, S_wp, WP_cu, P_k, w_te, og_k, hn_k, cik)
        R['plate_serit'] = ps
        print('PLATE_SERIT', cift, boy, json.dumps(ps, default=str), flush=True)
    R['bakir'] = {a: rb[a] for a in ('bakir', 'hedef', 'hedef_gecmis', 'kabartma_onayli', 'plate_dikis',
                                     'onarimsiz_d') if a in rb}
    R['qc'] = rb['qc']
    R['zemin_birebir'] = {'fark_max': round(float(np.abs(WP_cu - P_k)[np.abs(D_cu).max(-1) < 1].max()), 3)}
    R['zemin_birebir']['gecti'] = R['zemin_birebir']['fark_max'] < 0.5
    # dikis kaniti: her plate dikisinde ve Serdar'in isaretledigi yerde (CANCER_LIBRA 11x14, x~1563, y 3482-3590)
    # plate / onayli / duz renk baskisi / yeni cikti luma profili (cizgi boyunca ortalama, x-6..x+6)
    yerler = [(c['x'], c['y'][0], c['y'][1]) for c in rb['plate_dikis']['onaylida_olmayan'] if c['yon'] == 'dikey']
    if cift == 'CANCER_LIBRA' and boy == '11x14':
        yerler.append((1563, 3482, 3590))
    R['dikis_kanit'] = []
    for x, y0_, y1_ in yerler[:4]:
        x0_, x1_ = max(0, x - 6), min(Wd, x + 7)
        pr = {ad: [round(float(v), 1) for v in (A_[y0_:y1_, x0_:x1_] @ wk.LUMA).mean(0)]
              for ad, A_ in (('plate', P_wp0), ('onayli', S_wp), ('duz_renk', B_cu), ('yeni', WP_cu))}
        R['dikis_kanit'].append({'x': x, 'y': [y0_, y1_], **pr})
        print('DIKIS_KANIT', cift, boy, json.dumps({'x': x, 'y': [y0_, y1_], **pr}), flush=True)
    # eski iz (CI baskisinda silinen eski yazidan kalan; bilgi)
    Y, ham = t_cu['koruma']
    Wc, Hc = t_cu['baski'].size
    Yt = sd._yeni_tam(Y, (Wc, Hc), 0 if ham else 1, ham=ham)
    if (Wc, Hc) != (Wd, H):
        Yt = np.asarray(Image.fromarray(Yt.astype(np.uint8) * 255).resize((Wd, H), Image.NEAREST)) > 0
    bolge = np.zeros((H, Wd), bool)
    if 'isim' in et:
        y0, y1 = et['isim']
        bolge[max(0, y0 - 20):y1 + 20] = True
    R['eski_iz'] = wk.eski_iz(S_c - P_c, B_cu - P_c, Yt, bolge)
    if 'buyuk_sembol' in et:
        R['siparis_buyuk_sembol'] = wk.fark_tablosu(WP_cu, S_wp, P_wp0, {'buyuk_sembol': et['buyuk_sembol']}, P_wp)['buyuk_sembol']
    kaydet_jpg(WP_cu, cik / f'WP_{cift}_{boy}_BASKI.jpg', 95)
    if et:
        y0 = min(v[0] for a, v in et.items() if a != 'buyuk_sembol') - 60
        y1 = max(v[1] for a, v in et.items() if a != 'buyuk_sembol') + 60
        x0, x1 = int(Wd * 0.06), int(Wd * 0.94)
        kaydet_jpg(WP_cu[max(0, y0):y1, x0:x1], cik / f'WP_{cift}_{boy}_ISIM_BANDI.jpg', 95)
        yanyana(S_wp, WP_cu, cik / f'WP_{cift}_{boy}_YANYANA.jpg', bant=[max(0, y0), y1],
                etiket=('ONAYLI WP (gri-kahve)', f'YENI BAKIR ({isim[0]} / {isim[1]})'))
        kaydet_jpg(np.concatenate([S_wp[max(0, y0):y1, x0:x1], WP_cu[max(0, y0):y1, x0:x1]], 0),
                   cik / f'WP_{cift}_{boy}_BANT_1e1.jpg', 95)
    o_cu = r_cu.get('olcum') or {}
    if o_cu.get('isim_bant'):
        R['sonsuz_siparis'] = sonsuz_olc(S_c, B_cu, P_c, o_cu['isim_bant'], k)['hat']
    R['siparis_duz_renk_kapilar'] = kapi_ozet(r_cu)
    R['gecti'] = bool(R['plate_gecti'] and R['zemin_birebir']['gecti'] and R['qc']['gecti'] and r_cu.get('kapilar_gecti'))
    R['durum'] = 'URETILDI'
    return R, WP_cu


def tablo(hedef):
    """TEMP/WP_ORNEK/*/RAPOR_*.json -> BAKIR_QC.md (+ .json)."""
    yer = sd.W / 'tablo'; yer.mkdir(parents=True, exist_ok=True)
    sd.rc('copy', hedef, str(yer), '--include', '*/RAPOR_*.json', timeout=900)
    rs = [json.loads(p.read_text()) for p in sorted(yer.glob('*/RAPOR_*.json'))]
    def f(d, a='ort'):
        return '-' if not d or d.get(a) is None else d[a]
    sat = ['# WP BAKIR QC (1 Eki 2026, Serdar 2. karar: koyu bakir 140/72/28, onayli kontrast, kabartma, dikis)', '',
           'a) oge ortalamalari hedefe ve birbirine dE <= 5, ton onayli gri-kahveye yakin piksel <= %2; b) cizgi maskesinin '
           '3-8 px disi = kagit (p99 <= 1); c) eski glif izi (iz orani <= 1.25); d) bantlarda >= 100 px ince duz cizgi: onayli '
           'kagitta olmayan yok + maskede ince cizgi yok; e) cizgi disi kagit vs onayli (ort <= 0.5, p99 <= 3); f) isim/mesaj '
           'kenar isik-golge kontrasti yeni/onayli 0.7-1.43; g) her oge WCAG murekkep/kagit kontrasti >= onayli.', '',
           '| cift | boy | bakir | a) max dE / ara / kahve% | b | c iz | d plate dikisi (onarildi) / yeni | e kagit | f kabartma orani | '
           'g kontrast yeni (onayli): isim / mesaj / buyuk / kucuk / sonsuz | QC |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for R in rs:
        q = R.get('qc') or {}
        a_, b_, c_, d_, e_, f_, g_ = (q.get(x) or {} for x in ('a_renk', 'b_tasma', 'c_iz', 'd_dikis', 'e_kagit',
                                                               'f_kabartma', 'g_kontrast'))
        bk = R.get('bakir') or {}
        hd = (bk.get('hedef') or {}).get('rgb')
        hm = max((a_.get('hedefe_dE') or {'-': 0}).values())
        gk = lambda x: 'PASS' if x.get('gecti') else 'FAIL'
        pd = bk.get('plate_dikis') or {}
        gy, go = g_.get('yeni') or {}, g_.get('onayli') or {}
        gs = ' / '.join(f"{gy.get(e, '-')} ({go.get(e, '-')})" for e in ('isim', 'mesaj', 'buyuk_sembol', 'kucuk_sembol', 'sonsuz'))
        sat.append(f"| {R['cift']} | {R['boy']} | {hd} | {hm} / {a_.get('ogeler_arasi_max_dE')} / "
                   f"{round(100 * (a_.get('kahve_orani') or 0), 2)} {gk(a_)} | {b_.get('p99')} {gk(b_)} | "
                   f"{(c_.get('isim') or {}).get('iz_orani')}/{(c_.get('mesaj') or {}).get('iz_orani')} {gk(c_)} | "
                   f"{len(pd.get('onaylida_olmayan') or [])} ({'evet' if pd.get('onarildi') else '-'}) / "
                   f"{len(d_.get('onaylida_olmayan') or [])}+{len(d_.get('maskede_ince_bilesen') or [])} {gk(d_)} | "
                   f"{e_.get('ort')}/{e_.get('p99')} {gk(e_)} | {f_.get('oran')} {gk(f_)} | {gs} {gk(g_)} | "
                   f"{'PASS' if q.get('gecti') else 'FAIL'} |")
    (yer / 'BAKIR_QC.md').write_text('\n'.join(sat) + '\n')
    (yer / 'BAKIR_QC.json').write_text(json.dumps(rs, ensure_ascii=False, indent=1, default=str))
    print('\n'.join(sat), flush=True)
    for a in ('BAKIR_QC.md', 'BAKIR_QC.json'):
        sd.rc('copy', str(yer / a), hedef)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tablo', action='store_true')
    ap.add_argument('--cift', default='')
    ap.add_argument('--boylar', default='11x14,8x10')
    ap.add_argument('--hedef', default=HEDEF)
    a = ap.parse_args()
    if a.tablo:
        return tablo(a.hedef)
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    cik = sd.W / 'WP_ORNEK' / a.cift; cik.mkdir(parents=True, exist_ok=True)
    if a.cift == 'CANCER_LIBRA':                    # Serdar'in olctugu v2 dosyasi (bu kosu uzerine yazmadan once)
        try:
            sd.rc('copyto', f'{a.hedef}/CANCER_LIBRA/WP_CANCER_LIBRA_11x14_YANYANA.jpg', str(V2_YANYANA), timeout=600)
        except RuntimeError as e:
            log('v2 yanyana indirilemedi', e)
    boylar = [b.strip() for b in a.boylar.split(',') if b.strip()]
    tum = []
    for n, boy in enumerate(boylar, 1):
        try:
            R, _ = cift_boy(a.cift, boy, P_ed, P_blue, no, cik)
        except BaseException as e:                                # noqa: BLE001
            import traceback
            R = {'cift': a.cift, 'boy': boy, 'durum': f'HATA {type(e).__name__}: {e}',
                 'iz': traceback.format_exc()[-2000:]}
        tum.append(R)
        (cik / f'RAPOR_{boy}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
        g = time.time() - T0
        print('WPK', json.dumps({'cift': a.cift, 'boy': boy, 'durum': R.get('durum'), 'gecti': R.get('gecti'),
                                 'duz_renk': R.get('duz_renk'), 'plate_gecti': R.get('plate_gecti'),
                                 'hedef': R.get('bakir_hedef'), 'bakir': R.get('bakir'), 'qc': R.get('qc'),
                                 'zemin': R.get('zemin_birebir'), 'eski_iz': R.get('eski_iz'),
                                 'duz': [(d['renk'], d['siparis']['kalan']) for d in R.get('duz_renk_denemeleri', [])]},
                                ensure_ascii=False, default=str), flush=True)
        print(f'[{n}/{len(boylar)}] {a.cift} {boy} {R.get("durum")} | gecen {g:.0f}s | '
              f'kalan ~{g / n * (len(boylar) - n):.0f}s | %{100 * n // len(boylar)}', flush=True)
    sd.rc('copy', str(cik), f'{a.hedef}/{a.cift}', timeout=1800)
    log('Drive:', f'{a.hedef}/{a.cift}')


if __name__ == '__main__':
    main()
