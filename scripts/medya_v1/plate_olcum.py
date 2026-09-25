#!/usr/bin/env python3
"""PLATE (medyan zemin) FIZIBILITE OLCUMU - Serdar 25 Eyl 2026, Olcum 0.

SALT OKUR. Uretim yok, render kodu cagrilmaz, hicbir siparis dosyasi uretilmez.
POD_PRINT'e ve Etsy/Prodigi'ye YAZMA yok. Yalnizca Drive TEMP/KISISEL_PILOT/PLATE_OLCUM
altina rapor ve x3 kirpimlar yazilir.

FIKIR (Serdar): her (renk, boy) icin 78 ciftin POD_PRINT dosyasinin PIKSEL ORTANCASI
= yazisiz temiz zemin (plate). Cift basina degisen ogeler (sembol, isim, tagline)
78 dosyada farkli yerlerde/sekillerde oldugu icin ortancada yok olur; degismeyen
zemin (doku, gradyan, yildiz deseni, cerceve) ayakta kalir.

OLCULENLER
  a) plate uretimi: WARM_PARCHMENT 30x40, WARM_PARCHMENT A3, CHAMPAGNE_IVORY A3,
     MIDNIGHT_BLUE A3. Bellek icin karo karo (satir dilimleri) medyan.
  b) uc farkli ciftte, MUREKKEP DISI bolgede |dosya - plate| p50 / p99 / max.
     Hem 2400 normalize uzayda hem de isim bandinin TAM COZUNURLUKLU seridinde.
  c) ayni farktan cikan murekkep maskesiyle AQUARIUS^2 A3'te CI ve WP bant
     konumlari MB'ye gore kac px farkli.
  d) medyan plate'te isim bandinin x3 buyutmesi (yazi izi kalmis mi).
  + 16 boy x 5 renk plate uretimi icin sure ve bellek ekstrapolasyonu.

BELLEK YONTEMI
  Dosya basina TEK cozme. Her dosyadan iki sey saklanir:
    - sayfanin 2400 px genislige normalize hali (butun kilitli sabitlerin uzayi)
    - isim bandinin TAM COZUNURLUKLU serit hali (JPEG gurultusunu gercek olcekte
      olcebilmek icin)
  Medyan satir dilimlerinde `np.partition` ile uint8 uzerinde alinir; np.median
  float64'e yukseltip belleği ~8 katina cikardigi icin kullanilmaz.
"""
import json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KP = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
CIK = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT/PLATE_OLCUM'
W = Path('_plate').resolve(); W.mkdir(exist_ok=True)
NORM_W = 2400
BUYUT = 3

# Olculecek plate'ler (Serdar 0-a; (c) icin MB ve CI A3 de gerekiyor)
HEDEF = [('WARM_PARCHMENT', '30x40'), ('MIDNIGHT_BLUE', 'A3'),
         ('CHAMPAGNE_IVORY', 'A3'), ('WARM_PARCHMENT', 'A3')]
# Onceki kosuda MB'den olculen bantlar (2400 uzayi) - serit penceresi icin
BANT = {'30x40': {'isim': [2355, 2446], 'sembol': [2037, 2231], 'tag': [2742, 2818]},
        'A3':    {'isim': [2456, 2568], 'sembol': [2174, 2295], 'tag': [2839, 2915]}}
SERIT_PAY = 40            # isim bandinin ustune/altina 2400 uzayinda eklenen pay
FARK_ESIK = 30            # murekkep cekirdegi (gurultu p99'unun cok ustu)
FARK_GENIS = 12           # murekkep maskesi genisletme (pilot16.GENISLET ile ayni)
ORNEK_CIFT = 3            # (b) icin kac cift olculecek


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:7.1f}s]",
          *a, flush=True)


def rc(*a, timeout=1800):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout


def ciftler():
    return sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())


def indir(renk, boy, cs):
    """78 dosyayi tek rclone kosusuyla indirir (salt okur)."""
    hed = W / f'{renk}_{boy}'
    hed.mkdir(exist_ok=True)
    var = {p.stem for p in hed.glob('*.jpg')}
    eksik = [c for c in cs if c not in var]
    if eksik:
        f = W / f'liste_{renk}_{boy}.txt'
        f.write_text('\n'.join(f'{c}/{renk}/{boy}.jpg' for c in eksik), encoding='utf-8')
        rc('copy', POD, str(hed / '_ham'), '--files-from', str(f), '--transfers', '8')
        for c in eksik:
            src = hed / '_ham' / c / renk / f'{boy}.jpg'
            if src.exists():
                src.replace(hed / f'{c}.jpg')
    return sorted(hed.glob('*.jpg'))


def medyan(yigin, dilim=200):
    """uint8 yigin (N,H,W,3) -> medyan (H,W,3). np.median float64'e yukseltir,
    bellegi ~8 katina cikarir; np.partition uint8'de kalir."""
    n = yigin.shape[0]
    k = n // 2
    out = np.empty(yigin.shape[1:], np.uint8)
    for y in range(0, yigin.shape[1], dilim):
        y1 = min(y + dilim, yigin.shape[1])
        p = np.partition(yigin[:, y:y1], k, axis=0)
        out[y:y1] = p[k] if n % 2 else ((p[k].astype(np.uint16)
                                         + np.partition(yigin[:, y:y1], k - 1, axis=0)[k - 1]) // 2
                                        ).astype(np.uint8)
    return out


def plate_kur(renk, boy, yollar):
    """Tek gecis: her dosyayi BIR kez coz, 2400 sayfayi ve tam cozunurluklu isim
    seridini yiginlara yaz, sonra satir dilimlerinde medyan al."""
    t0 = time.time()
    # On tarama (yalniz JPEG basligi okunur, cozme yok): aykiri boyutlu dosya
    # butun plate'i dusurmesin. POD_PRINT'te en az bir aykiri dosya oldugu
    # biliniyor (5x7 10962x15175, 24 Eyl olcumu).
    boyutlar = {}
    for y in yollar:
        with Image.open(y) as im:
            boyutlar.setdefault(im.size, []).append(y)
    tam_px = max(boyutlar, key=lambda s_: len(boyutlar[s_]))
    aykiri = [y.stem for s_, ys in boyutlar.items() if s_ != tam_px for y in ys]
    yollar = sorted(boyutlar[tam_px])
    k = NORM_W / tam_px[0]
    nh = round(tam_px[1] * k)
    ib = BANT[boy]['isim']
    sy0 = max(int((ib[0] - SERIT_PAY) / k), 0)
    sy1 = min(int((ib[1] + SERIT_PAY) / k), tam_px[1])
    n = len(yollar)
    kucuk = np.empty((n, nh, NORM_W, 3), np.uint8)
    serit = np.empty((n, sy1 - sy0, tam_px[0], 3), np.uint8)
    coz_sn = []
    for i, y in enumerate(yollar):
        t1 = time.time()
        with Image.open(y) as im:
            a = np.asarray(im.convert('RGB'))
        coz_sn.append(time.time() - t1)
        serit[i] = a[sy0:sy1]
        kucuk[i] = np.asarray(Image.fromarray(a).resize((NORM_W, nh), Image.LANCZOS))
        del a
        if (i + 1) % 20 == 0:
            gec = time.time() - t0
            log(f'  {renk}/{boy} {i + 1}/{n} gecen {gec:.0f}s kalan ~{gec / (i + 1) * (n - i - 1):.0f}s')
    pl_k = medyan(kucuk)
    pl_s = medyan(serit, dilim=60)
    bellek = {'kucuk_yigin_MB': round(kucuk.nbytes / 1e6, 1),
              'serit_yigin_MB': round(serit.nbytes / 1e6, 1),
              'tam_sayfa_yigin_MB_KURAMSAL': round(n * tam_px[0] * tam_px[1] * 3 / 1e6, 1)}
    return {'renk': renk, 'boy': boy, 'n': n, 'aykiri_boyut': aykiri,
            'tam_px': list(tam_px), 'k': round(k, 4),
            'norm_px': [NORM_W, nh], 'serit_tam': [sy0, sy1], 'bellek': bellek,
            'coz_ort_sn': round(float(np.mean(coz_sn)), 2),
            'coz_toplam_sn': round(float(np.sum(coz_sn)), 1),
            'gecis_sn': round(time.time() - t0, 1)}, pl_k, pl_s, kucuk, serit, (sy0, sy1)


def fark_olc(a, plate):
    """|dosya - plate| ve murekkep maskesi. Murekkep DISI bolgede yuzdelikler."""
    import cv2
    f = np.abs(a.astype(np.int16) - plate.astype(np.int16)).max(axis=2).astype(np.uint8)
    cek = (f > FARK_ESIK).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * FARK_GENIS + 1,) * 2)
    maske = cv2.dilate(cek, ker) > 0
    dis = f[~maske]
    return {'murekkep_px': int(maske.sum()), 'murekkep_orani': round(float(maske.mean()), 4),
            'disi_px': int(dis.size),
            'p50': float(np.percentile(dis, 50)), 'p99': float(np.percentile(dis, 99)),
            'max': int(dis.max()), 'ort': round(float(dis.mean()), 2)}, maske


def bantlar(maske, satir_esik=3, satir_bosluk=8, asgari_yukseklik=10,
            x_bosluk=60, x_asgari=20):
    """Murekkep maskesinden satir bantlari ve her bandin x kumeleri."""
    sat = maske.sum(axis=1) > satir_esik
    bs, cur = [], None
    bos = 0
    for y, v in enumerate(sat):
        if v:
            cur = [y, y + 1] if cur is None else [cur[0], y + 1]
            bos = 0
        elif cur is not None:
            bos += 1
            if bos > satir_bosluk:
                bs.append(cur); cur = None
    if cur is not None:
        bs.append(cur)
    bs = [b for b in bs if b[1] - b[0] >= asgari_yukseklik]
    out = []
    for y0, y1 in bs:
        sut = maske[y0:y1].sum(axis=0) > 0
        ks, c, g = [], None, 0
        for x, v in enumerate(sut):
            if v:
                c = [x, x + 1] if c is None else [c[0], x + 1]
                g = 0
            elif c is not None:
                g += 1
                if g > x_bosluk:
                    ks.append(c); c = None
        if c is not None:
            ks.append(c)
        ks = [x for x in ks if x[1] - x[0] >= x_asgari]
        out.append({'y': [y0, y1], 'kume': ks, 'kume_sayisi': len(ks)})
    return out


def sayfa_kaydet(im_a, ad, yukseklik=1600):
    """Plate sayfasinin kucultulmus hali (yazi izi genel bakis)."""
    im = Image.fromarray(im_a)
    im = im.resize((round(im.width * yukseklik / im.height), yukseklik), Image.LANCZOS)
    im.save(W / ad, quality=92)
    return {'dosya': ad, 'px': list(im.size)}


def x3(im_a, ad, kutu=None):
    im = Image.fromarray(im_a)
    if kutu:
        im = im.crop(kutu)
    im = im.resize((im.width * BUYUT, im.height * BUYUT), Image.LANCZOS)
    if im.width > 3600:
        im = im.resize((3600, round(im.height * 3600 / im.width)), Image.LANCZOS)
    p = W / ad
    im.save(p, quality=95)
    return {'dosya': ad, 'px': list(im.size)}


def main():
    cs = ciftler()
    log(f'POD_PRINT cift sayisi: {len(cs)}')
    rapor = {'tarih': datetime.now(timezone.utc).isoformat(), 'cift_sayisi': len(cs),
             'yontem': 'medyan plate (78 dosya), salt okur, uretim yok',
             'esikler': {'FARK_ESIK': FARK_ESIK, 'FARK_GENIS': FARK_GENIS,
                         'NORM_W': NORM_W, 'SERIT_PAY': SERIT_PAY},
             'plateler': {}, 'kirpimlar': [], 'hata': {}}
    orn_ix = [0, len(cs) // 2, len(cs) - 1][:ORNEK_CIFT]
    maskeler = {}                       # (c) icin AQUARIUS^2 A3 bantlari
    aq = 'AQUARIUS_AQUARIUS'
    for renk, boy in HEDEF:
        anahtar = f'{renk}/{boy}'
        try:
            t0 = time.time()
            yollar = indir(renk, boy, cs)
            ind_sn = time.time() - t0
            log(f'{anahtar}: {len(yollar)} dosya indi ({ind_sn:.0f}s)')
            if len(yollar) < 40:
                rapor['hata'][anahtar] = f'yalniz {len(yollar)} dosya var, medyan guvenilmez'
                continue
            bilgi, pl_k, pl_s, kucuk, serit, (sy0, sy1) = plate_kur(renk, boy, yollar)
            bilgi['indirme_sn'] = round(ind_sn, 1)
            ay = set(bilgi['aykiri_boyut'])
            adlar = [p.stem for p in sorted(yollar) if p.stem not in ay]

            # (b) uc farkli ciftte murekkep disi fark
            bilgi['b_murekkep_disi_fark'] = {}
            for ix in orn_ix:
                if ix >= len(yollar):
                    continue
                d2400, m2400 = fark_olc(kucuk[ix], pl_k)
                dtam, _ = fark_olc(serit[ix], pl_s)
                bilgi['b_murekkep_disi_fark'][adlar[ix]] = {
                    'norm2400_tam_sayfa': d2400, 'tam_cozunurluk_isim_seridi': dtam}
                if renk in ('MIDNIGHT_BLUE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT') \
                        and boy == 'A3' and adlar[ix] == aq:
                    maskeler[renk] = bantlar(m2400)

            # (c) AQUARIUS^2 bant konumu (ornek listesinde yoksa ayrica olc)
            if boy == 'A3' and aq in adlar and renk not in maskeler:
                _d, m = fark_olc(kucuk[adlar.index(aq)], pl_k)
                maskeler[renk] = bantlar(m)

            # (d) plate'te isim bandinin x3 buyutmesi
            ib = BANT[boy]['isim']
            bilgi['d_kirpim'] = [
                x3(pl_k, f'PLATE_{renk}_{boy}_ISIM_x3_norm2400.jpg',
                   (0, max(ib[0] - 30, 0), NORM_W, min(ib[1] + 30, pl_k.shape[0]))),
                x3(pl_s, f'PLATE_{renk}_{boy}_ISIM_x3_tam.jpg'),
                sayfa_kaydet(pl_k, f'PLATE_{renk}_{boy}_SAYFA.jpg')]
            del kucuk, serit
            rapor['plateler'][anahtar] = bilgi
            log(f'{anahtar} bitti: {json.dumps(bilgi["b_murekkep_disi_fark"])[:400]}')
        except BaseException as e:                                # noqa: BLE001
            rapor['hata'][anahtar] = f'{type(e).__name__}: {e}'
            log(f'{anahtar} HATA: {type(e).__name__}: {e}')

    # (c) MB'ye gore fark
    if 'MIDNIGHT_BLUE' in maskeler:
        mb = maskeler['MIDNIGHT_BLUE']
        c = {'referans': 'MIDNIGHT_BLUE', 'cift': aq, 'boy': 'A3',
             'MIDNIGHT_BLUE_bantlar': mb}
        for renk in ('CHAMPAGNE_IVORY', 'WARM_PARCHMENT'):
            if renk not in maskeler:
                c[renk] = 'olculemedi'
                continue
            o = maskeler[renk]
            es = []
            for i in range(min(len(mb), len(o))):
                es.append({'mb_y': mb[i]['y'], 'y': o[i]['y'],
                           'dy': [o[i]['y'][j] - mb[i]['y'][j] for j in (0, 1)],
                           'mb_kume': mb[i]['kume'], 'kume': o[i]['kume']})
            dy = [abs(v) for e in es for v in e['dy']]
            c[renk] = {'bant_sayisi': [len(mb), len(o)], 'eslesme': es,
                       'en_buyuk_dy_px': max(dy) if dy else None}
        rapor['c_aquarius_a3'] = c

    # ekstrapolasyon
    p = [v for v in rapor['plateler'].values()]
    if p:
        rapor['ekstrapolasyon'] = {
            'olculen': {f"{v['renk']}/{v['boy']}": {
                'n': v['n'], 'tam_px': v['tam_px'], 'indirme_sn': v['indirme_sn'],
                'coz_ort_sn': v['coz_ort_sn'], 'gecis_sn': v['gecis_sn'],
                'bellek': v['bellek']} for v in p},
            'not': ('16 boy x 5 renk = 80 plate. Bir plate = 78 indirme + 78 cozme + '
                    'medyan. Asagidaki tahmin olculen gecis_sn ve indirme_sn ile '
                    'her boyun piksel sayisina gore olceklenir.')}

    (W / 'PLATE_OLCUM.json').write_text(json.dumps(rapor, indent=1, ensure_ascii=False),
                                        encoding='utf-8')
    for f in list(W.glob('*.jpg')) + [W / 'PLATE_OLCUM.json']:
        rc('copy', str(f), CIK, timeout=600)
    print(json.dumps({k: rapor[k] for k in ('cift_sayisi', 'hata')}, indent=1))
    log('bitti')


if __name__ == '__main__':
    main()
