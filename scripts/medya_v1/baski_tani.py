#!/usr/bin/env python3
"""baski-duzelt tani kosusu (28 Eyl 2026). YALNIZ Drive TEMP; Etsy/Prodigi yok, siparis hatti yok.

Her (cift, renk, boy) icin siparis_dosyasi.pod_uret ile TEST baski dosyasi uretilir (kapi
sonucundan bagimsiz), ayrica:
  - tag tanisi (Blue disi): plate farki maskesinde isim bandinin altindaki bantlar, satir
    murekkep sayilari, beklenen slogan kutusunda |dosya - plate| yuzdelikleri, kirpimlar;
  - olcek: yeni kapi (BASKI vs onayli 2400, alt piksel) + eski kapi (p1 vs p0) yan yana;
  - gorsel: ayni bolge (MB olcumu) her renkte; 2400 render (buyutulmus, kirmizi) ile BASKI
    (camgobegi) ust uste - geometri farki renkli sacak olarak gorunur;
  - onceki kosuyla (--onceki) BASKI bayt/piksel karsilastirmasi.
Cikti: <kok>/<CIFT>_<RENK>_<BOY>/ + <kok>/_TANI/TANI_<CIFT>.json + TEMAS_<CIFT>_<BOY>.jpg
"""
import argparse, hashlib, json, sys, time, traceback
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

SAHTE = {'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'}
KISA = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'PURE_WHITE': 'PW',
        'CHAMPAGNE_IVORY': 'CI', 'WARM_PARCHMENT': 'WP'}


def yazi(boy=26):
    try:
        return ImageFont.load_default(size=boy)
    except TypeError:                                             # eski Pillow
        return ImageFont.load_default()


def md5(yol):
    return hashlib.md5(Path(yol).read_bytes()).hexdigest()


def tag_tanisi(P_ed, yol, plate_yol, cik):
    """Plate farki maskesi slogan bandini neden vermiyor? Olcer, kod degistirmez."""
    import pilot11
    from pilot6 import LUMA, kumeler
    sd.olcek_kur(2400)
    d = {}
    im = pilot11.norm(Image.open(yol).convert('RGB'))[0]
    L = np.asarray(im).astype(np.float32) @ LUMA
    acik = float(np.median(L)) > 128
    pl = P_ed.p11.norm(Image.open(plate_yol).convert('RGB'))[0]
    Lp = np.asarray(pl).astype(np.float32) @ LUMA
    h = min(L.shape[0], Lp.shape[0])
    d['boyut'] = {'dosya': list(im.size), 'plate': list(pl.size)}
    m = P_ed.plate_maske(plate_yol)(L, acik)
    try:
        o = pilot11.sayfa_olc(yol, maske=P_ed.plate_maske(plate_yol))
    except SystemExit as e:
        return {**d, 'plate_olcum': f'isim satiri yok: {e}'}
    d['plate_olcum_tag_var'] = 'tag_bant' in o
    ib = o['isim_bant']
    alt = []
    for b in [b for b in pilot11.bantlar(m) if b[0] >= ib[1]][:10]:
        tk = [c for c in kumeler(m[b[0]:b[1]], 60) if c[1] - c[0] > pilot11.TAG_GURULTU]
        alt.append({'bant': list(b), 'yukseklik': b[1] - b[0], 'kume': len(tk),
                    'uzanim': (tk[-1][1] - tk[0][0]) if tk else 0,
                    'kabul': bool(tk) and b[1] - b[0] > 30 and tk[-1][1] - tk[0][0] > 200})
    d['isim_bant'] = ib
    d['alt_bantlar'] = alt
    y0, y1 = ib[1], min(ib[1] + 450, h)
    d['satir_murekkep'] = [int(v) for v in m[y0:y1].sum(axis=1)]
    # yedek (edisyon_maske) olcumunun slogan kutusunda plate farki
    try:
        o2 = pilot11.sayfa_olc(yol, maske=lambda LL, a: P_ed.eu.edisyon_maske(LL, a))
        tb, tx = o2.get('tag_bant'), o2.get('tag_x')
    except SystemExit:
        tb = tx = None
    d['yerel_kontrast_tag'] = {'tag_bant': tb, 'tag_x': tx}
    if tb and tx:
        f = np.abs(L[:h] - Lp[:h])
        kutu = f[tb[0]:tb[1], tx[0]:tx[1]]
        zemin = f[tb[1] + 40:tb[1] + 40 + (tb[1] - tb[0]), tx[0]:tx[1]]
        d['slogan_kutusu_fark'] = {f'p{q}': round(float(np.percentile(kutu, q)), 1) for q in (50, 90, 99)}
        d['slogan_kutusu_esik_ustu'] = round(float((kutu > sd.PLATE_ESIK).mean()), 4)
        if zemin.size:
            d['bos_zemin_fark'] = {f'p{q}': round(float(np.percentile(zemin, q)), 1) for q in (50, 90, 99)}
    # kirpim: dosya | plate | |fark|x4 | maske  (isim bandinin altindan 450 satir)
    x0, x1 = 250, 2150
    parca = [np.clip(L[y0:y1, x0:x1], 0, 255), np.clip(Lp[y0:y1, x0:x1], 0, 255),
             np.clip(np.abs(L[y0:y1, x0:x1] - Lp[y0:y1, x0:x1]) * 4, 0, 255),
             m[y0:y1, x0:x1].astype(np.float32) * 255]
    g = np.concatenate([np.pad(p, ((0, 8), (0, 0)), constant_values=128) for p in parca], axis=0)
    Image.fromarray(g.astype(np.uint8)).save(cik / 'TAG_TANI_dosya_plate_fark_maske.jpg', quality=90)
    return d


def bolge(o, k, pay=18):
    """Sembol bandi ustunden slogan alti: hedef piksel kutusu."""
    y0 = o['sembol_bant'][0] - pay
    y1 = (o.get('tag_bant') or o['isim_bant'])[1] + pay
    return [int(300 * k), int(y0 * k), int(2100 * k), int(y1 * k)]


def ust_uste(baski, p0, kutu):
    """R = 2400 render (baski boyuna buyutulmus), G/B = BASKI. Ayni geometri -> gri."""
    k = baski.width / p0.width
    kb = [int(v / k) for v in kutu]
    a = np.asarray(p0.convert('L').crop(kb).resize((kutu[2] - kutu[0], kutu[3] - kutu[1]),
                                                     Image.LANCZOS))
    b = np.asarray(baski.convert('L').crop(kutu))
    return Image.fromarray(np.dstack([a, b, b]).astype(np.uint8))


def satir(r):
    k = r.get('kapilar') or {}
    return ' '.join(f"{a[:5]}:{'P' if v else ('-' if v is None else 'F')}" for a, v in k.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cift', required=True)
    ap.add_argument('--isler', required=True, help="'11x14:MIDNIGHT_BLUE,DEEP_BLACK;12x16:CHAMPAGNE_IVORY'")
    ap.add_argument('--kok', required=True)
    ap.add_argument('--onceki', default='')
    a = ap.parse_args()
    sd.SIP = a.kok
    no, _ = sd.sayfa_no_tablosu()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    isler = [(b.split(':')[0], b.split(':')[1].split(',')) for b in a.isler.split(';')]
    toplam = sum(len(r) for _, r in isler)
    tani_dir = sd.W / '_TANI'; tani_dir.mkdir(exist_ok=True)
    satirlar, n, T0 = [], 0, time.time()
    for boy, renkler in isler:
        gorsel = []
        ref_o = None
        for renk in renkler:
            n += 1
            x = sd.normalize({'cift': a.cift, 'renk': renk, 'boy': boy, 'urun': 'pod', **SAHTE})
            x['receipt'] = f'{a.cift}_{renk}_{boy}'
            x['sayfa'] = no[a.cift]
            cik = sd.W / x['receipt']; cik.mkdir(parents=True, exist_ok=True)
            yol = sd.pod_kaynak(a.cift, renk, boy)
            with Image.open(yol) as im:
                x['hedef_px'] = list(im.size)
            kb = yol.read_bytes()
            kayit = {'cift': a.cift, 'renk': renk, 'boy': boy}
            if x['edisyon'] != 'blue':
                try:
                    kayit['tag_tanisi'] = tag_tanisi(P_ed, yol, P_ed.plate(x['edisyon'], x['oran'], boy), cik)
                except Exception as e:                            # noqa: BLE001
                    kayit['tag_tanisi'] = {'hata': f'{type(e).__name__}: {e}'}
            sd._TANI = {}
            try:
                r = sd.pod_uret(x, kb, P_blue, P_ed, cik)
            except BaseException as e:                            # noqa: BLE001
                r = {**x, 'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}',
                     'iz': traceback.format_exc()[-1500:]}
            (cik / 'KAPI_RAPORU.json').write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
            kayit.update({'durum': r.get('durum'), 'hata': r.get('hata'),
                          'kapilar': r.get('kapilar'), 'kapilar_gecti': r.get('kapilar_gecti'),
                          'olcek_yeni': {q: (r.get('olcek_kapisi') or {}).get(q)
                                         for q in ('gecti', 'konum_fark_px', 'kenar_fark_px', 'fark', 'sebep')},
                          'olcek_eski': {q: (r.get('olcek_kapisi_eski') or {}).get(q)
                                         for q in ('gecti', 'konum_fark_px', 'kenar_fark_px', 'fark', 'sebep')},
                          'tag_yedek': r.get('tag_yedek'),
                          'sembol_kapisi': r.get('sembol_kapisi'), 'leke_kapisi': r.get('leke_kapisi'),
                          'kalinti_kapisi': r.get('kalinti_kapisi'),
                          'temiz_ara_kapisi': r.get('temiz_ara_kapisi'),
                          'mesaj_kapisi': r.get('mesaj_kapisi'), 'olcum': r.get('olcum')})
            baski_yol = cik / f'BASKI_{boy}.jpg'
            if baski_yol.exists():
                kayit['md5'] = md5(baski_yol)
                if a.onceki:
                    try:
                        eski_dir = sd.W / '_onceki' / x['receipt']; eski_dir.mkdir(parents=True, exist_ok=True)
                        sd.rc('copy', f"{a.onceki}/{x['receipt']}/BASKI_{boy}.jpg", str(eski_dir))
                        e = eski_dir / f'BASKI_{boy}.jpg'
                        if e.exists():
                            A = np.asarray(Image.open(e).convert('RGB')).astype(np.int16)
                            B = np.asarray(Image.open(baski_yol).convert('RGB')).astype(np.int16)
                            kayit['onceki'] = {'md5': md5(e), 'bayt_ayni': md5(e) == kayit['md5'],
                                               'piksel_ayni': bool(A.shape == B.shape and (A == B).all()),
                                               'fark_px': int((np.abs(A - B).max(axis=2) > 0).sum())
                                               if A.shape == B.shape else None}
                        else:
                            kayit['onceki'] = {'yok': True}
                    except Exception as e:                        # noqa: BLE001
                        kayit['onceki'] = {'hata': f'{type(e).__name__}: {e}'}
            T = sd._TANI or {}
            if T.get('baski') is not None and r.get('olcum'):
                ref_o = ref_o or r['olcum']
                k = T['baski'].width / 2400.0
                kutu = bolge(ref_o, k)
                kir = T['baski'].crop(kutu)
                uu = ust_uste(T['baski'], T['p0'], kutu)
                kir.save(cik / 'BOLGE_MB_ile_ayni.jpg', quality=92)
                uu.save(cik / 'UST_USTE_2400kirmizi_baski_camgobegi.jpg', quality=92)
                gorsel.append((renk, kir, uu, r))
            else:
                gorsel.append((renk, None, None, r))
            sd.rc('copy', str(cik), f"{a.kok}/{x['receipt']}", timeout=1800)
            satirlar.append(kayit)
            g = time.time() - T0
            print(f"[{n}/{toplam}] {x['receipt']} {kayit['durum']} gecti={kayit['kapilar_gecti']} "
                  f"olcek yeni={kayit['olcek_yeni'].get('gecti')} eski={kayit['olcek_eski'].get('gecti')} | "
                  f"gecen {g:.0f}s | kalan ~{g / n * (toplam - n):.0f}s | %{100 * n // toplam}", flush=True)
        # temas sayfasi: her renk bir satir: [ayni bolge | ust uste]
        en = 1300
        parcalar = []
        f = yazi(26)
        for renk, kir, uu, r in gorsel:
            if kir is None:
                t = Image.new('RGB', (2 * en + 30, 120), 'white')
                ImageDraw.Draw(t).text((10, 10), f"{KISA[renk]} {boy}: {r.get('durum')} {r.get('hata') or ''}"[:160],
                                       fill='red', font=f)
                parcalar.append(t); continue
            h = int(kir.height * en / kir.width)
            t = Image.new('RGB', (2 * en + 30, h + 50), 'white')
            t.paste(kir.resize((en, h), Image.LANCZOS), (10, 45))
            t.paste(uu.resize((en, h), Image.LANCZOS), (en + 20, 45))
            ok = r.get('olcek_kapisi') or {}
            ImageDraw.Draw(t).text((10, 8), f"{KISA[renk]} {boy} | {satir(r)} | olcek konum "
                                             f"{ok.get('konum_fark_px')} kenar {ok.get('kenar_fark_px')}",
                                   fill='black', font=f)
            parcalar.append(t)
        if parcalar:
            H = sum(p.height for p in parcalar) + 10 * len(parcalar)
            s = Image.new('RGB', (max(p.width for p in parcalar), H), (200, 200, 200))
            y = 0
            for p in parcalar:
                s.paste(p, (0, y)); y += p.height + 10
            s.save(tani_dir / f'TEMAS_{a.cift}_{boy}.jpg', quality=88)
    (tani_dir / f'TANI_{a.cift}.json').write_text(json.dumps(satirlar, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(tani_dir), f'{a.kok}/_TANI', timeout=1800)
    print(json.dumps([{q: s.get(q) for q in ('renk', 'boy', 'durum', 'kapilar_gecti')} for s in satirlar]))


if __name__ == '__main__':
    main()
