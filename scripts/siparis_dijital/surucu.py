#!/usr/bin/env python3
"""DIJITAL siparis surucusu (Serdar 1 Eki 2026, siparis-dijital.yml). Kod bu dosyada DEGIL: --kod ile verilen
checkout'taki scripts/medya_v1 (renk: siparis-baski-v1 8a8b370; wp: wp-katman adfb2b9, kilitli BAKIR WP).

Isim / mesaj loga YAZILMAZ: workflow_dispatch girdileri GITHUB_EVENT_PATH'ten okunur, yalniz kod adi (receipt)
basilir. Etsy'ye yazma / musteriye gonderim YOK; cikti yerel klasor, Drive'a workflow yukler.

--asama renk  --renk R : dijital_uret, tek renk (5 oran, 1 PDF + pdf_kapisi)
--asama wp    --boy B  : wp_bakir_uret, tek dijital boy (BAKIR WP sayfasi, sayfa butcesi icinde JPEG)
--asama pdf            : WP sayfalarindan PDF (ayni pdf_yap / pdf_kapisi) + OZET + 11x14 kesit / onizleme
"""
import argparse, base64, json, os, sys
from pathlib import Path

RENK4 = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY')
KESIT_Y = (0.66, 0.93)          # 11x14 sayfasinda isim + mesaj bandi (sayfa yuksekligi orani), 1:1


def girdi():
    """workflow_dispatch girdileri (yerel deneme: SIPARIS_GIRDI_JSON)."""
    yol = os.environ.get('SIPARIS_GIRDI_JSON') or os.environ['GITHUB_EVENT_PATH']
    g = json.loads(Path(yol).read_text())
    g = g.get('inputs', g)
    mesaj = base64.b64decode(g['mesaj_b64']).decode('utf-8')
    return {'receipt': g['receipt'], 'cift': g['cift'], 'isim1': g['isim1'].strip().upper(),
            'isim2': g['isim2'].strip().upper(), 'mesaj': mesaj}


def kod_yukle(kod):
    sys.path.insert(0, str(Path(kod).resolve() / 'scripts' / 'medya_v1'))
    import siparis_dosyasi as sd
    return sd


def renk_asamasi(a, g):
    sd = kod_yukle(a.kod)
    no, _ = sd.sayfa_no_tablosu()
    x = sd.normalize({'receipt': g['receipt'], 'cift': g['cift'], 'renk': a.renk, 'boy': None, 'urun': 'dijital',
                      'yalniz_renk': True, 'isim1': g['isim1'], 'isim2': g['isim2'], 'mesaj': g['mesaj']})
    x['sayfa'] = no[x['cift']]
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    r = sd.dijital_uret(x, P_blue, P_ed, cik)
    rk = r['renkler'][a.renk]
    oz = {'renk': a.renk, 'durum': rk.get('durum'), 'pdf': rk.get('pdf'), 'pdf_kapisi': rk.get('pdf_kapisi'),
          'sayfa_kapilar': {o: {'durum': v.get('durum'), 'kapilar_gecti': v.get('kapilar_gecti'),
                                'kalan': sorted(k for k, d in (v.get('kapilar') or {}).items() if d is False),
                                'baski_px': v.get('baski_px'), 'hata': v.get('hata')}
                            for o, v in rk['oranlar'].items()},
          'kapilar_gecti': r.get('kapilar_gecti'), 'kod': a.kod_ref}
    (cik / f'OZET_{a.renk}.json').write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str))
    (cik / f'KAPI_RAPORU_{a.renk}.json').write_text(json.dumps(
        {q: v for q, v in r.items() if q not in ('isim1', 'isim2', 'mesaj')}, ensure_ascii=False, indent=1, default=str))
    print('RENK', a.renk, json.dumps({q: oz[q] for q in ('durum', 'pdf', 'kapilar_gecti')}),
          'PDF', (oz['pdf_kapisi'] or {}).get('MB'), 'MB', 'PASS' if (oz['pdf_kapisi'] or {}).get('gecti') else 'FAIL',
          {o: (v['kapilar_gecti'], v['kalan']) for o, v in oz['sayfa_kapilar'].items()}, flush=True)
    return 0 if oz['durum'] == 'URETILDI' and (oz['pdf_kapisi'] or {}).get('gecti') else 1


def wp_asamasi(a, g):
    sd = kod_yukle(a.kod)
    sys.path.insert(0, str(Path(a.kod).resolve() / 'scripts' / 'medya_v1'))
    import wp_kilit
    f = wp_kilit.fark()
    if f:
        print('WP KILIT BOZUK', f, flush=True)
        return 2
    import wp_ornek as wo
    from PIL import Image
    butce = int(sd.PDF_AZAMI_MB * 1e6 * 0.92 / len(sd.DIJITAL_ORANLAR))   # renk hattindaki sayfa butcesiyle ayni
    asil = wo.kaydet_jpg
    kalite = {}

    def kaydet(arr, yol, q=95):                     # tam sayfa JPEG: butceyi asarsa kalite 95 -> 80
        asil(arr, yol, q)
        while Path(yol).stat().st_size > butce and q > 80:
            q -= 3
            asil(arr, yol, q)
        kalite[Path(yol).name] = q
    wo.kaydet_jpg = kaydet
    no, _ = sd.sayfa_no_tablosu()
    x = sd.normalize({'receipt': g['receipt'], 'cift': g['cift'], 'renk': 'WARM_PARCHMENT', 'boy': a.boy,
                      'urun': 'pod', 'isim1': g['isim1'], 'isim2': g['isim2'], 'mesaj': g['mesaj']})
    x['sayfa'] = no[x['cift']]
    yol = sd.pod_kaynak(x['cift'], 'WARM_PARCHMENT', a.boy)
    with Image.open(yol) as im:
        x['hedef_px'] = list(im.size)
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    ara = cik / 'ara'; ara.mkdir(exist_ok=True)
    r = sd.wp_bakir_uret(x, P_blue, P_ed, ara)
    oz = {'boy': a.boy, 'durum': r.get('durum'), 'yontem': r.get('yontem'), 'baski_px': r.get('baski_px'),
          'kapilar': r.get('kapilar'), 'kapilar_gecti': r.get('kapilar_gecti'), 'dosya_MB': r.get('dosya_MB'),
          'jpeg_kalite': kalite.get(f'BASKI_{a.boy}.jpg'), 'wp_bakir': r.get('wp_bakir'), 'kod': a.kod_ref,
          'wp_kilit': 'TAMAM'}
    jpg = ara / f'BASKI_{a.boy}.jpg'
    if jpg.exists():
        jpg.replace(cik / f'WP_{a.boy}.jpg')
    (cik / f'OZET_WP_{a.boy}.json').write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str))
    print('WP', a.boy, json.dumps({q: oz[q] for q in ('durum', 'kapilar_gecti', 'baski_px', 'dosya_MB', 'jpeg_kalite')}),
          json.dumps(oz['kapilar']), flush=True)
    return 0 if oz['durum'] == 'URETILDI' and oz['kapilar_gecti'] else 1


def kesit(jpg, hedef_kesit, hedef_onizleme):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(jpg) as im:
        w, h = im.size
        im.crop((0, int(h * KESIT_Y[0]), w, int(h * KESIT_Y[1]))).save(hedef_kesit, 'JPEG', quality=95, subsampling=0)
        im.convert('RGB').resize((1100, round(1100 * h / w)), Image.LANCZOS).save(hedef_onizleme, 'JPEG', quality=90)
    return [w, h]


def pdf_asamasi(a, g):
    """WP PDF + tum renklerin ozeti + 11x14 kesitleri. a.cikti altinda renk/<RENK>/ ve wp/<boy>/ beklenir."""
    sd = kod_yukle(a.kod)
    kok = Path(a.cikti).resolve()
    paket = kok / 'paket'; paket.mkdir(exist_ok=True)
    inc = kok / 'inceleme'; inc.mkdir(exist_ok=True)
    OZ = {'receipt': g['receipt'], 'cift': g['cift'], 'renkler': {}}
    # WP PDF
    wp = {}
    sayfalar = []
    for oran in sd.DIJITAL_ORANLAR:
        boy = sd.DIJITAL_BOY[oran]
        o = kok / 'wp' / boy
        z = json.loads((o / f'OZET_WP_{boy}.json').read_text()) if (o / f'OZET_WP_{boy}.json').exists() else None
        wp[oran] = z
        if z and (o / f'WP_{boy}.jpg').exists():
            sayfalar.append((o / f'WP_{boy}.jpg', boy))
    wk = {'durum': 'EKSIK', 'sayfa_kapilar': {o: (z or {}).get('kapilar_gecti') for o, z in wp.items()}}
    if len(sayfalar) == len(sd.DIJITAL_ORANLAR):
        pdf = sd.pdf_yap(sayfalar, paket / sd.pdf_adi(g['cift'], 'WARM_PARCHMENT'))
        wk.update({'durum': 'URETILDI', 'pdf': pdf.name, 'pdf_kapisi': sd.pdf_kapisi(pdf, sayfalar)})
        wk['kapilar_gecti'] = all(v for v in wk['sayfa_kapilar'].values())
        kesit(dict((b, j) for j, b in sayfalar)['11x14'], inc / 'KESIT_WARM_PARCHMENT_11x14.jpg',
              inc / 'ONIZLEME_WARM_PARCHMENT_11x14.jpg')
    OZ['renkler']['WARM_PARCHMENT'] = {**wk, 'kod': 'claude/wp-katman-baski-60sk0s adfb2b9 (BAKIR, wp_kilit TAMAM)',
                                       'sayfa': wp}
    for renk in RENK4:
        d = kok / 'renk' / renk
        f = d / f'OZET_{renk}.json'
        if not f.exists():
            OZ['renkler'][renk] = {'durum': 'EKSIK'}
            continue
        z = json.loads(f.read_text())
        OZ['renkler'][renk] = z
        if z.get('pdf') and (d / renk / z['pdf']).exists():
            (d / renk / z['pdf']).replace(paket / z['pdf'])
        j = sorted((d / renk).glob(f'*_{renk}_11x14_*.jpg'))
        if j:
            kesit(j[0], inc / f'KESIT_{renk}_11x14.jpg', inc / f'ONIZLEME_{renk}_11x14.jpg')
    sat = [f"# DIJITAL {g['receipt']} {g['cift']}", '', '| renk | PDF | MB | sayfa | dpi | pdf_kapisi | sayfa kapilari |',
           '|---|---|---|---|---|---|---|']
    hepsi = True
    for renk in ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT'):
        z = OZ['renkler'].get(renk) or {}
        k = z.get('pdf_kapisi') or {}
        dpi = sorted({d for s in k.get('sayfalar', []) for d in s['dpi']})
        sk = z.get('sayfa_kapilar') or {}
        skg = {o: (v.get('kapilar_gecti') if isinstance(v, dict) else v) for o, v in sk.items()}
        ok = bool(k.get('gecti')) and len(skg) == 5 and all(skg.values())
        hepsi &= ok
        sat.append(f"| {renk} | {z.get('pdf')} | {k.get('MB')} | {k.get('sayfa_sayisi')} | {dpi} | "
                   f"{'PASS' if k.get('gecti') else 'FAIL'} | {'PASS' if ok else 'FAIL ' + str(skg)} |")
    OZ['gecti'] = hepsi
    sat += ['', f"SONUC: {'PASS' if hepsi else 'FAIL'}"]
    (paket / 'OZET.md').write_text('\n'.join(sat) + '\n')
    (paket / 'OZET.json').write_text(json.dumps(OZ, ensure_ascii=False, indent=1, default=str))
    (inc / 'OZET.md').write_text('\n'.join(sat) + '\n')
    print('\n'.join(sat), flush=True)
    return 0 if hepsi else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asama', required=True, choices=('renk', 'wp', 'pdf'))
    ap.add_argument('--kod', required=True)
    ap.add_argument('--kod-ref', default='')
    ap.add_argument('--renk'); ap.add_argument('--boy')
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    a.cikti = str(Path(a.cikti).resolve()); a.kod = str(Path(a.kod).resolve())
    g = girdi()
    os.chdir(Path(a.kod).resolve())               # siparis_dosyasi: _siparis / kisisel yollari cwd'ye gore
    f = {'renk': renk_asamasi, 'wp': wp_asamasi, 'pdf': pdf_asamasi}[a.asama]
    sys.exit(f(a, g))


if __name__ == '__main__':
    main()
