#!/usr/bin/env python3
"""WP SIPARIS YOLU DOGRULAMASI (Serdar 3 Eki, Test 5 WP tagline cift baski). Etsy / musteri YOK.

Uretim = siparis yolunun kendisi: main'deki scripts/siparis_dijital/surucu.py wp_bakir_uret_v1 (duz renk
CHAMPAGNE_IVORY, kilitli WP dosyalari renk_ref checkout'unun ustunde). Bu script yalniz dongu + olcum + kesit.

calis   : hucre listesi (cift x boy) uretilir; kapilar (c_iz icinde ikinci metin kapisi), e_kagit (istisna dahil),
          ikinci metin olcumu, sure -> HUCRE satiri + DOGRULA_<etiket>.json. --onizleme: tam sayfa JPEG kaydedilir.
          --teslim BOY=dosya: ayni siparisin teslim edilmis sayfasi (Test 4/5 PDF sayfasi, kesit JPEG) ayni kapidan
          gecirilir (siparisin duz renk baskisi ve kagit bu kosudan); 1:1 kesit (teslim | yeni) yazilir.
pdf     : PDF'teki sayfa goruntuleri (img2pdf JPEG) boy adiyla cikarilir (piksel boyutundan).
toplam  : DOGRULA_*.json -> 390 hucre ozeti (TOPLAM satiri, rc 0 yalniz hepsi PASS)."""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
BOY_PX = {(3307, 4200): '11x14', (4800, 6000): '16x20', (5400, 7200): '18x24', (7200, 10800): '24x36',
          (4960, 7015): 'A2'}


def log(*a):
    print(*a, flush=True)


def surucu_yukle(yol):
    sp = importlib.util.spec_from_file_location('surucu_main', yol)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def calis(a):
    import os
    su = surucu_yukle(Path(a.surucu).resolve())
    kod = Path(a.kod).resolve()
    cikti = Path(a.cikti).resolve(); cikti.mkdir(parents=True, exist_ok=True)
    teslim = {}                                        # ad|boy|dosya|plate (plate bos: bu kosunun kagidi)
    for t in a.teslim or []:
        ad, b, y, pl = (t.split('|') + [''])[:4]
        teslim.setdefault(b, []).append((ad, str(Path(y).resolve()), str(Path(pl).resolve()) if pl else ''))
    os.chdir(kod)                                     # siparis_dosyasi: _siparis / kisisel yollari cwd'ye gore
    sd = su.kod_yukle(str(kod))
    sys.path.insert(0, str(kod / 'scripts' / 'medya_v1'))
    import wp_kilit
    f = wp_kilit.fark()
    if f:
        raise SystemExit(f'WP KILIT BOZUK {f}')
    import wp_ornek as wo
    import wp_bakir as wb
    import wp_katman as wk
    asil_kaydet = wo.kaydet_jpg
    wo.kaydet_jpg = lambda arr, yol, q=95: asil_kaydet(arr, yol, 95)
    zula = {}
    asil_im = wb.ikinci_metin

    def im_sar(out, P_kagit, B_ci, P_ci, k):           # siparis yolundaki cagriyi aynen yapar, girdileri saklar
        zula.update(out=out, P_kagit=P_kagit, B_ci=B_ci, P_ci=P_ci, k=k)
        return asil_im(out, P_kagit, B_ci, P_ci, k)
    wb.ikinci_metin = im_sar
    no, ciftler = sd.sayfa_no_tablosu()
    if a.hucreler:
        hucreler = [tuple(h.split(':')) for h in a.hucreler.split(',')]
    else:
        i, n = (int(v) for v in a.parca.split('/'))
        hucreler = [(c, a.boy) for j, c in enumerate(sorted(ciftler)) if j % n == i]
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    satir = []
    for j, (cift, boy) in enumerate(hucreler, 1):
        t0 = time.time()
        x = sd.normalize({'receipt': a.receipt, 'cift': cift, 'renk': 'WARM_PARCHMENT', 'boy': boy, 'urun': 'pod',
                          'isim1': a.isim1, 'isim2': a.isim2, 'mesaj': a.mesaj})
        x['sayfa'] = no[x['cift']]
        with Image.open(sd.pod_kaynak(x['cift'], 'WARM_PARCHMENT', boy)) as im:
            x['hedef_px'] = list(im.size)
        ara = cikti / 'ara' / f'{cift}_{boy}'; ara.mkdir(parents=True, exist_ok=True)
        zula.clear()
        hata = None
        try:
            r = su.wp_bakir_uret_v1(sd, x, P_blue, P_ed, ara)
        except BaseException as e:                        # noqa: BLE001
            import traceback
            r, hata = {'durum': f'HATA {type(e).__name__}: {e}'}, traceback.format_exc()[-1500:]
        h = {'cift': cift, 'boy': boy, 'sayfa': x['sayfa'], 'plate': wo.plate_adi(cift, x['sayfa'], boy),
             'durum': r.get('durum'), 'kapilar_gecti': bool(r.get('kapilar_gecti')), 'kapilar': r.get('kapilar'),
             'e_kagit': (r.get('kapi_sayilari') or {}).get('e_kagit'), 'sure_sn': round(time.time() - t0, 1)}
        if hata:
            h['hata'] = hata
        jpg = ara / f'BASKI_{boy}.jpg'
        if zula:
            im = asil_im(zula['out'], zula['P_kagit'], zula['B_ci'], zula['P_ci'], zula['k'])
            h['ikinci_metin'] = im
            if boy in teslim:
                h['teslim'] = {ad: teslim_olc(y, pl, zula, asil_im, cift, boy, ad, cikti, jpg) for ad, y, pl in teslim[boy]}
            if a.onizleme and jpg.exists():
                hedef = cikti / f'ONIZLEME_{cift}_{boy}.jpg'
                jpg.replace(hedef)
                h['onizleme'] = hedef.name
        import shutil
        shutil.rmtree(ara, ignore_errors=True)                # disk: hucre basina ara dosyalar (onizleme tasindi)
        zula.clear()
        satir.append(h)
        log('HUCRE', json.dumps(h, ensure_ascii=False, default=str))
        g = time.time() - T0
        log(f'[{j}/{len(hucreler)}] {cift} {boy} | gecen {g:.0f}s | kalan ~{g / j * (len(hucreler) - j):.0f}s '
            f'| %{100 * j // len(hucreler)}')
    oz = {'etiket': a.etiket, 'hucre': len(satir), 'pass': sum(h['kapilar_gecti'] for h in satir),
          'ikinci_metin_fail': sum(not (h.get('ikinci_metin') or {}).get('gecti', False) for h in satir),
          'ikinci_metin_en_buyuk_max': max([(h.get('ikinci_metin') or {}).get('en_buyuk', -1) for h in satir] or [-1]),
          'sure_sn': round(time.time() - T0, 1)}
    (cikti / f'DOGRULA_{a.etiket}.json').write_text(json.dumps({'ozet': oz, 'hucreler': satir}, ensure_ascii=False,
                                                               indent=1, default=str))
    log('OZET', json.dumps(oz, ensure_ascii=False))
    return 0


def teslim_olc(yol, plate, z, im_f, cift, boy, ad, cikti, jpg):
    """Teslim edilmis sayfa ayni kapidan (siparisin duz renk baskisi bu kosudan; kagit = bu kosunun kagidi ya da
    teslimin uretildigi plate). 1:1 kesit: en buyuk yabanci bilesen +-200 px (yoksa mesaj bandi), teslim | yeni."""
    T = np.asarray(Image.open(yol).convert('RGB')).astype(np.float32)
    H, W = z['out'].shape[:2]
    if T.shape[:2] != (H, W):
        return {'hata': f'boyut {T.shape[:2]} != {(H, W)}'}
    if plate:
        im = Image.open(plate).convert('RGB')
        Pk = np.asarray(im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)).astype(np.float32)
    else:
        Pk = z['P_kagit']
    r = im_f(T, Pk, z['B_ci'], z['P_ci'], z['k'])
    Y = np.asarray(Image.open(jpg).convert('RGB')) if jpg.exists() else np.clip(z['out'], 0, 255).astype(np.uint8)
    if 'kutu' in r and r['en_buyuk'] >= r['esik_alan']:
        x0, y0, x1, y1 = r['kutu']
    else:
        x0, y0, x1, y1 = W // 4, int(H * 0.80), 3 * W // 4, int(H * 0.86)
    p = int(round(200 * z['k']))
    y0, y1 = max(0, y0 - p), min(H, y1 + p)
    x0, x1 = max(0, min(x0 - p, W // 2 - 900)), min(W, max(x1 + p, W // 2 + 900))
    Tk = np.clip(T[y0:y1, x0:x1], 0, 255).astype(np.uint8)
    Yk = Y[y0:y1, x0:x1]
    dosya = f'KESIT_{ad}_{cift}_{boy}_TESLIM_YENI_1e1.png'
    Image.fromarray(np.concatenate([Tk, np.full((8, Tk.shape[1], 3), 255, np.uint8), Yk], 0)).save(cikti / dosya)
    r['kesit'] = dosya
    r['pencere'] = {'x': [x0, x1], 'y': [y0, y1]}
    r['var'] = not r['gecti']
    return r


def pdf(a):
    import pikepdf
    from pikepdf import PdfImage
    cik = Path(a.cikti); cik.mkdir(parents=True, exist_ok=True)
    bulunan = {}
    with pikepdf.open(a.pdf) as p:
        for n, sf in enumerate(p.pages, 1):
            for ad, raw in sf.images.items():
                im = PdfImage(raw)
                boy = BOY_PX.get((im.width, im.height))
                if not boy:
                    continue
                yol = im.extract_to(fileprefix=str(cik / f'{a.etiket}_{boy}'))
                bulunan[boy] = {'sayfa': n, 'dosya': Path(yol).name, 'px': [im.width, im.height]}
    log('PDF', a.etiket, json.dumps(bulunan))
    return 0 if bulunan else 1


def toplam(a):
    sat, oz = [], []
    for p in sorted(Path(a.cikti).glob('**/DOGRULA_*.json')):
        d = json.loads(p.read_text())
        if not d['ozet']['etiket'].startswith(a.etiket):
            continue
        oz.append(d['ozet']); sat += d['hucreler']
    hucre = {(h['cift'], h['boy']): h for h in sat}
    T = {'hucre': len(hucre), 'pass': sum(h['kapilar_gecti'] for h in hucre.values()),
         'ikinci_metin_fail': [f"{c} {b}" for (c, b), h in hucre.items() if not (h.get('ikinci_metin') or {}).get('gecti')],
         'fail': {f"{c} {b}": {k: v for k, v in (h.get('kapilar') or {}).items() if v is False} or h.get('durum')
                  for (c, b), h in hucre.items() if not h['kapilar_gecti']},
         'istisna_hucre': {f"{c} {b}": (h.get('e_kagit') or {}).get('p99') for (c, b), h in hucre.items()
                           if (h.get('e_kagit') or {}).get('p99', 0) > 3.0},
         'ikinci_metin_en_buyuk_max': max([(h.get('ikinci_metin') or {}).get('en_buyuk', -1) for h in hucre.values()] or [-1]),
         'e_kagit_p99_max_genel': max([(h.get('e_kagit') or {}).get('p99', 0) for h in hucre.values()
                                       if (h.get('e_kagit') or {}).get('p99', 0) <= 3.0] or [0])}
    sure = {}
    for h in hucre.values():
        sure.setdefault(h['boy'], []).append(h['sure_sn'])
    T['sure_ort_sn'] = {b: round(sum(v) / len(v), 1) for b, v in sure.items()}
    md = ['| cift | ' + ' | '.join(sorted(sure)) + ' |', '|---|' + '---|' * len(sure)]
    for c in sorted({c for c, _ in hucre}):
        r = []
        for b in sorted(sure):
            h = hucre.get((c, b))
            r.append('-' if not h else f"{'PASS' if h['kapilar_gecti'] else 'FAIL'} p99 {(h.get('e_kagit') or {}).get('p99')}"
                     f" im {(h.get('ikinci_metin') or {}).get('en_buyuk')}")
        md.append(f'| {c} | ' + ' | '.join(r) + ' |')
    Path(a.cikti, f'TOPLAM_{a.etiket}.md').write_text('\n'.join(md) + '\n')
    Path(a.cikti, f'TOPLAM_{a.etiket}.json').write_text(json.dumps(T, ensure_ascii=False, indent=1))
    log('TOPLAM', json.dumps({k: T[k] for k in ('hucre', 'pass', 'ikinci_metin_fail', 'fail', 'istisna_hucre',
                                               'ikinci_metin_en_buyuk_max', 'e_kagit_p99_max_genel', 'sure_ort_sn')},
                             ensure_ascii=False))
    return 0 if T['hucre'] == a.beklenen and T['pass'] == T['hucre'] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('is_', choices=('calis', 'pdf', 'toplam'))
    ap.add_argument('--surucu', default='scripts/siparis_dijital/surucu.py')
    ap.add_argument('--kod', default='_v1')
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--etiket', default='dogrula')
    ap.add_argument('--hucreler', default='', help='CIFT:BOY,... (bos ise --boy + --parca)')
    ap.add_argument('--boy', default='11x14')
    ap.add_argument('--parca', default='0/1')
    ap.add_argument('--receipt', default='9000000005')
    ap.add_argument('--isim1', default='MAXWELL')
    ap.add_argument('--isim2', default='QUINN')
    ap.add_argument('--mesaj', default='Written in the Stars, Always Yours')
    ap.add_argument('--teslim', nargs='*', default=None, help='ad|boy|dosya|plate (teslim edilmis sayfa; plate bos ise bu kosunun kagidi)')
    ap.add_argument('--onizleme', action='store_true')
    ap.add_argument('--pdf', default='')
    ap.add_argument('--beklenen', type=int, default=390)
    a = ap.parse_args()
    sys.exit({'calis': calis, 'pdf': pdf, 'toplam': toplam}[a.is_](a) or 0)


if __name__ == '__main__':
    main()
