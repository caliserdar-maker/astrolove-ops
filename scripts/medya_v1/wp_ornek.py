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
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
import wp_katman as wk                                           # noqa: E402

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
    tH = H + 60 + sum(p.height + 50 for p in parca)
    t = Image.new('RGB', (A.width + B.width + 30, tH), 'white')
    d = ImageDraw.Draw(t)
    t.paste(A, (0, 50)); t.paste(B, (A.width + 30, 50))
    d.text((10, 15), etiket[0], fill='black'); d.text((A.width + 40, 15), etiket[1], fill='black')
    y = H + 60
    for p, e in zip(parca, (etiket[0] + ' isim bandi 1:1', etiket[1] + ' isim bandi 1:1')):
        d.text((10, y), e, fill='black'); t.paste(p, (0, y + 20)); y += p.height + 50
    t.save(yol, 'JPEG', quality=90)


def kapi_ozet(r):
    k = r.get('kapilar') or {}
    return {'durum': r.get('durum'), 'hata': r.get('hata'), 'kapilar_gecti': r.get('kapilar_gecti'),
            'kalan': sorted(g for g, v in k.items() if v is False), 'kapilar': k}


def cift_boy(cift, boy, P_ed, P_blue, no, cik):
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
        for tur, (i1, i2, m) in (('kimlik', (s1, s2, SLOGAN)), ('siparis', (*ISIM, MESAJ))):
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
    ad = f'VINTAGE_{boy}.png'
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
    P_wp, onarim = wk.plate_onar_glif(P_wp0, G, ink, onar_bant)
    sonra = wk.plate_iz(P_wp, G, pt_bant)
    mk0 = wk.murekkep_maskesi(D_wp, kenar=0)
    zt = wk.ozet(wk.dE(P_wp0, S_wp), ~mk0)
    R['plate'] = {'ad': ad, 'temizlik_once': once, 'onarim': onarim, 'temizlik': sonra,
                  'eski_olcut_once': wk.plate_temizlik(P_wp0, S_wp, pt_bant),
                  'zemin_uyumu': {**zt, 'esik_ort': 0.5, 'gecti': zt.get('ort', 99) <= 0.5}}
    R['plate_gecti'] = bool(sonra['gecti'] and R['plate']['zemin_uyumu']['gecti'])
    model = wk.renk_ogren(Dw_src, P_wp0, S_wp)
    R['renk_modeli'] = {a: model[a] for a in ('derece', 'egitim_px', 'murekkep_px', 'egitim_rmse')}

    # ---- 5) kimlik farklari
    # (a) KATMAN kimligi: onayli CI kaynagi -> katman -> onarilmis WP plate  vs  onayli WP
    taban = wk.renk_uygula(Dw_src, P_wp, model)
    del Dw_src
    R['kimlik_kaynak_tabani'] = wk.fark_tablosu(taban, S_wp, P_wp0, et, P_wp)
    # (b) CI hattinin kendi kimligi: hat baskisi (kaynagin yazisi) vs onayli CI (bant bazinda)
    B_id = wk.boyutla(wk.dizi(uret['kimlik'][1]['baski']), (Wd, H))
    R['kimlik_duz_renk'] = wk.fark_tablosu(B_id, S_c, P_c, et)
    R['kimlik_duz_renk']['ozet'] = R['kimlik_duz_renk']['tum']
    # (c) UCTAN UCA: CI hat baskisi -> katman -> WP  vs  onayli WP
    WP_id, _ = wk.katman_bas(B_id, P_c, P_wp, hiz, model)
    R['kimlik'] = wk.fark_tablosu(WP_id, S_wp, P_wp0, et, P_wp)
    kaydet_jpg(WP_id, cik / f'KIMLIK_{boy}_WP.jpg', 90)
    yanyana(WP_id, S_wp, cik / f'KIMLIK_{boy}_YANYANA.jpg', H=1400,
            bant=[min(v[0] for v in et.values() if v) - 40, max(v[1] for v in et.values() if v) + 40]
            if et else None, etiket=('KIMLIK (hat + katman)', 'ONAYLI WP'))
    yanyana(taban, S_wp, cik / f'KIMLIK_KATMAN_{boy}_YANYANA.jpg', H=1400,
            bant=[min(v[0] for v in et.values() if v) - 40, max(v[1] for v in et.values() if v) + 40]
            if et else None, etiket=('KIMLIK (onayli CI -> katman)', 'ONAYLI WP'))
    del B_id, taban

    # ---- 4) siparis (EMILY / JAMES)
    r_cu, t_cu = uret['siparis']
    B_cu = wk.boyutla(wk.dizi(t_cu['baski']), (Wd, H))
    WP_cu, D_cu = wk.katman_bas(B_cu, P_c, P_wp, hiz, model)
    # zemin birebir: tasinan murekkep yoksa piksel = WP plate (silme / leke yapisal olarak yok)
    bos = np.abs(D_cu).max(-1) <= wk.RAMPA[0]
    R['zemin_birebir'] = {'fark_max': round(float(np.abs(WP_cu - P_wp)[bos].max()), 3),
                          'gecti': bool(np.abs(WP_cu - P_wp)[bos].max() < 0.5)}
    # eski iz (CI baskisinda silinen eski yazidan kalan)
    Y, ham = t_cu['koruma']
    Wc, Hc = t_cu['baski'].size
    Yt = sd._yeni_tam(Y, (Wc, Hc), 0 if ham else 1, ham=ham)
    if (Wc, Hc) != (Wd, H):
        Yt = np.asarray(Image.fromarray(Yt.astype(np.uint8) * 255).resize((Wd, H), Image.NEAREST)) > 0
    bolge = np.zeros((H, Wd), bool)
    for a in ('isim',):                  # yalniz isim bandi (bilgi; kapi CI hattinin isim_kalinti'si)
        if a in et:
            y0, y1 = et[a]
            dy = min(hiz, key=lambda h: abs((y0 + y1) / 2 - (h['bant'][0] + h['bant'][1]) / 2))['dy']
            bolge[max(0, int(y0 + dy) - 20):int(y1 + dy) + 20] = True
    R['eski_iz'] = wk.eski_iz(S_c - P_c, B_cu - P_c, Yt, bolge)
    # buyuk sembol siparis baskisinda onayli WP ile ayni mi (sembol kaymasi)
    if 'buyuk_sembol' in et:
        R['siparis_buyuk_sembol'] = wk.fark_tablosu(WP_cu, S_wp, P_wp0, {'buyuk_sembol': et['buyuk_sembol']}, P_wp)['buyuk_sembol']
    kaydet_jpg(WP_cu, cik / f'WP_{cift}_{boy}_BASKI.jpg', 95)
    if et:
        y0 = min(v[0] for a, v in et.items() if a != 'buyuk_sembol') - 60
        y1 = max(v[1] for a, v in et.items() if a != 'buyuk_sembol') + 60
        x0, x1 = int(Wd * 0.06), int(Wd * 0.94)
        kaydet_jpg(WP_cu[max(0, y0):y1, x0:x1], cik / f'WP_{cift}_{boy}_ISIM_BANDI.jpg', 95)
        yanyana(WP_cu, S_wp, cik / f'WP_{cift}_{boy}_YANYANA.jpg', bant=[max(0, y0), y1])
    R['siparis_duz_renk_kapilar'] = kapi_ozet(r_cu)
    R['gecti'] = bool(R['plate_gecti'] and R['zemin_birebir']['gecti'] and r_cu.get('kapilar_gecti'))
    R['durum'] = 'URETILDI'
    return R, WP_cu


def tablo(hedef):
    """TEMP/WP_ORNEK/*/RAPOR_*.json -> KIMLIK_TABLOSU.md (+ .json)."""
    yer = sd.W / 'tablo'; yer.mkdir(parents=True, exist_ok=True)
    sd.rc('copy', hedef, str(yer), '--include', '*/RAPOR_*.json', timeout=900)
    rs = [json.loads(p.read_text()) for p in sorted(yer.glob('*/RAPOR_*.json'))]
    def f(d, a='ort'):
        return '-' if not d or d.get(a) is None else d[a]
    sat = ['# WP katman yontemi: kimlik testi (30 Eyl 2026)', '',
           'dE = CIE76 (Lab), ort/p99; parantezde murekkep maskesi IoU. KATMAN = onayli CI kaynagi katmanla WP\'ye '
           'tasindi (yontemin kendisi). CI HAT = mevcut hattin kimlik baskisi (kaynagin burc adlari + slogani) vs onayli '
           'CI. UCTAN UCA = CI hat baskisi -> katman -> WP vs onayli WP. Plate: medyan, iz CI glif maskesiyle olculur; eski glif izi kaynagin kendi '
           'dokusuyla onarildi; iz orani once -> sonra (esik 1.25).', '',
           '| cift | boy | plate iz (mesaj) once->sonra | zemin ort | KATMAN isim | KATMAN mesaj | KATMAN sembol (buyuk/kucuk) | '
           'CI HAT isim | CI HAT mesaj | UCTAN UCA isim | UCTAN UCA mesaj | kapilar (CI siparis) |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|']
    def h(d):
        return '-' if not d else f"{f(d)}/{f(d, 'p99')} ({f(d, 'iou')})"
    for R in rs:
        k = R.get('kimlik') or {}; t = R.get('kimlik_kaynak_tabani') or {}; c = R.get('kimlik_duz_renk') or {}
        pl = R.get('plate') or {}
        io = lambda x: ((x or {}).get('mesaj') or {}).get('iz_orani', '-')
        sat.append(f"| {R['cift']} | {R['boy']} | {io(pl.get('temizlik_once'))} -> {io(pl.get('temizlik'))} "
                   f"{'TEMIZ' if R.get('plate_gecti') else 'KIRLI'} | {f(pl.get('zemin_uyumu'))} | "
                   f"{h(t.get('isim'))} | {h(t.get('mesaj'))} | {h(t.get('buyuk_sembol'))} / {h(t.get('kucuk_sembol'))} | "
                   f"{h(c.get('isim'))} | {h(c.get('mesaj'))} | {h(k.get('isim'))} | {h(k.get('mesaj'))} | "
                   f"{'PASS' if (R.get('siparis_duz_renk_kapilar') or {}).get('kapilar_gecti') else 'FAIL ' + str((R.get('siparis_duz_renk_kapilar') or {}).get('kalan') or R.get('durum'))} |")
    (yer / 'KIMLIK_TABLOSU.md').write_text('\n'.join(sat) + '\n')
    (yer / 'KIMLIK_TABLOSU.json').write_text(json.dumps(rs, ensure_ascii=False, indent=1, default=str))
    print('\n'.join(sat), flush=True)
    for a in ('KIMLIK_TABLOSU.md', 'KIMLIK_TABLOSU.json'):
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
        kim = (R.get('kimlik') or {})
        print('WPK', json.dumps({'cift': a.cift, 'boy': boy, 'durum': R.get('durum'), 'gecti': R.get('gecti'),
                                 'duz_renk': R.get('duz_renk'), 'plate': R.get('plate', {}).get('ad'),
                                 'plate_gecti': R.get('plate_gecti'),
                                 'kimlik_murekkep': kim.get('murekkep'), 'kimlik_isim': kim.get('isim'),
                                 'kimlik_mesaj': kim.get('mesaj'), 'kimlik_buyuk': kim.get('buyuk_sembol'),
                                 'taban_murekkep': (R.get('kimlik_kaynak_tabani') or {}).get('murekkep'),
                                 'eski_iz': R.get('eski_iz'), 'zemin': R.get('zemin_birebir'),
                                 'hiz': [(h['bant'], h['dx'], h['dy'], h['olcek'], h['ecc']) for h in R.get('hizalama', [])],
                                 'model': R.get('renk_modeli'),
                                 'duz': [(d['renk'], d['siparis']['kalan'], d['kimlik']['kalan'])
                                         for d in R.get('duz_renk_denemeleri', [])]},
                                ensure_ascii=False, default=str), flush=True)
        print(f'[{n}/{len(boylar)}] {a.cift} {boy} {R.get("durum")} | gecen {g:.0f}s | '
              f'kalan ~{g / n * (len(boylar) - n):.0f}s | %{100 * n // len(boylar)}', flush=True)
    sd.rc('copy', str(cik), f'{a.hedef}/{a.cift}', timeout=1800)
    log('Drive:', f'{a.hedef}/{a.cift}')


if __name__ == '__main__':
    main()
