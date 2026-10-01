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


SURE_FONK = ('rc', 'pod_kaynak', 'kisisel_hazirla', 'bant_dogrulama', 'render_et', 'tek_dosya', 'dijital_leke',
             'olcek_kapisi_baski', 'olcek_ikinci_deneme', 'isim_kalinti_kapisi', '_iz_kapisi', 'kontrol_paketi',
             'pdf_yap', 'pdf_kapisi', 'renk_onizleme', 'plate_slogan_kapisi', 'zemin_uyumu', 'pod_uret')


def sure_olc(sd):
    """Hiz olcumu (Serdar 1 Eki: siparis 12 dk alti): agir fonksiyonlarin her cagrisi 'SURE ad sn pid' satiri.
    Cikti / kapi degismez; yalniz sarmalayici. rc (rclone) icin ilk arguman (copy / lsf ...) de yazilir."""
    import functools, os, time
    for ad in SURE_FONK:
        f = getattr(sd, ad, None)
        if f is None or getattr(f, '_sure', False):
            continue

        def sar(f=f, ad=ad):
            @functools.wraps(f)
            def g(*q, **k):
                t0 = time.time()
                try:
                    return f(*q, **k)
                finally:
                    ek = f' {q[0]}' if ad == 'rc' and q else ''
                    print(f'SURE {ad}{ek} {time.time() - t0:.1f} pid{os.getpid()}', flush=True)
            g._sure = True
            return g
        setattr(sd, ad, sar())


def kod_yukle(kod):
    sys.path.insert(0, str(Path(kod).resolve() / 'scripts' / 'medya_v1'))
    import siparis_dosyasi as sd
    sure_olc(sd)
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
    import shutil
    asil_rm = shutil.rmtree
    shutil.rmtree = lambda *q, **k: None              # EKSIK renkte sayfalar silinmesin (inceleme kesiti icin)
    try:
        r = sd.dijital_uret(x, P_blue, P_ed, cik)
    finally:
        shutil.rmtree = asil_rm
    rk = r['renkler'][a.renk]
    inc = cik / 'inceleme'; inc.mkdir(exist_ok=True)
    j = sorted((cik / a.renk).glob(f'*_{a.renk}_11x14_*.jpg'))
    if j:
        kesit(j[0], inc / f'KESIT_{a.renk}_11x14.jpg', inc / f'ONIZLEME_{a.renk}_11x14.jpg')
    for o, v in rk['oranlar'].items():                # plate kapisinda duran sayfa: kaynak / plate / fark 1:1
        if 'PLATE' in str(v.get('hata') or ''):
            try:
                boy = sd.DIJITAL_BOY[o]; ed = sd.RENK_ED[a.renk]
                src = sd.pod_kaynak(x['cift'], a.renk, boy)
                pl = P_ed.plate(ed, 'A' if o == 'a_series' else o, boy)
                pk = v.get('plate_slogan_kapisi') or {}
                plate_kesit(src, pl, inc / f'PLATE_KESIT_{a.renk}_{o}.jpg', pk.get('tag_bant'))
            except Exception as e:                    # noqa: BLE001
                print('PLATE_KESIT hata', type(e).__name__, str(e)[:120], flush=True)
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
    for o, v in rk['oranlar'].items():               # olcek FAIL: denemelerin olculeri (isim yok; yalniz px)
        if (v.get('kapilar') or {}).get('olcek') is False:
            ok = v.get('olcek_kapisi') or {}
            print('OLCEK_AYRINTI', a.renk, o, json.dumps({q: ok.get(q) for q in (
                'konum_fark_px', 'kenar_fark_px', 'fark', 'k', 'yerlesim', 'ilk_yerlesim', 'denemeler')},
                default=str), flush=True)
    sayfa_ok = len(oz['sayfa_kapilar']) == 5 and all(v['kapilar_gecti'] for v in oz['sayfa_kapilar'].values())
    return 0 if oz['durum'] == 'URETILDI' and (oz['pdf_kapisi'] or {}).get('gecti') and sayfa_ok else 1


WP_KAPILAR = ('a_renk', 'b_tasma', 'c_iz', 'e_kagit', 'f_kabartma', 'g_kontrast')


def wp_bakir_uret_v1(sd, sip, P_blue, P_ed, cik):
    """wp-katman dali (adfb2b9) siparis_dosyasi.wp_bakir_uret'in AYNISI; --kod v1 (renk_ref + kilitli WP dosyalari)
    iken v1'de bu fonksiyon yok. 1 Eki (siparis 4188621967 WP A2): duz renk baskisi uretimdeki POD koduyla."""
    import wp_ornek as wo
    R, WP = wo.cift_boy(sip['cift'], sip['boy'], P_ed, P_blue, {sip['cift']: sip['sayfa']}, cik,
                        isim=(sip['isim1'], sip['isim2']), mesaj=sip.get('mesaj') or '', siparis=True)
    ozet = {a: R.get(a) for a in ('durum', 'duz_renk', 'plate_gecti', 'zemin_birebir', 'eski_iz', 'serdar_dikis')}
    if WP is None:
        return {**sip, 'durum': R.get('durum'), 'wp_bakir': ozet, 'kapilar_gecti': False}
    ad = f'BASKI_{sip["boy"]}.jpg'
    wo.kaydet_jpg(WP, cik / ad, 95)
    q = R['qc']
    bpx = [int(WP.shape[1]), int(WP.shape[0])]
    kapilar = {'duz_renk_siparis': bool(R['siparis_duz_renk_kapilar'].get('kapilar_gecti')),
               **{a: bool(q[a]['gecti']) for a in WP_KAPILAR},
               'plate': bool(R['plate_gecti']), 'zemin_birebir': bool(R['zemin_birebir']['gecti']),
               'eski_iz': bool(R['eski_iz']['gecti']), 'boy': bpx == list(sip['hedef_px'])}
    return {**sip, 'durum': 'URETILDI', 'yontem': 'WP_BAKIR', 'baski_px': bpx,
            'dosya_MB': round((cik / ad).stat().st_size / 1e6, 2), 'kapilar': kapilar,
            'kapilar_gecti': all(kapilar.values()), 'bilgi_d_dikis': q['d_dikis'], 'wp_bakir': ozet}


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
    r = sd.wp_bakir_uret(x, P_blue, P_ed, ara) if hasattr(sd, 'wp_bakir_uret') else wp_bakir_uret_v1(sd, x, P_blue, P_ed, ara)
    oz = {'boy': a.boy, 'durum': r.get('durum'), 'yontem': r.get('yontem'), 'baski_px': r.get('baski_px'),
          'kapilar': r.get('kapilar'), 'kapilar_gecti': r.get('kapilar_gecti'), 'dosya_MB': r.get('dosya_MB'),
          'jpeg_kalite': kalite.get(f'BASKI_{a.boy}.jpg'), 'wp_bakir': r.get('wp_bakir'), 'kod': a.kod_ref,
          'wp_kilit': 'TAMAM'}
    jpg = ara / f'BASKI_{a.boy}.jpg'
    if jpg.exists():
        try:                                              # Serdar 1 Eki: eski metin izi kapisi WP sayfasinda da (sayi)
            pl = P_ed.plate('vintage', sd.BOY[a.boy][0], a.boy)
            pk = sd.plate_slogan_kapisi(yol.read_bytes(), pl, 'vintage')
            oz['eski_metin_izi'] = (iz_olc(Image.open(jpg), yol.read_bytes(), pk['tag_bant'], pk['tag_x'], sd)
                                    if pk.get('tag_bant') else {'gecti': None, 'sebep': 'mesaj bandi olculemedi'})
        except Exception as e:                            # noqa: BLE001
            oz['eski_metin_izi'] = {'gecti': False, 'hata': f'{type(e).__name__}: {e}'}
        print('WP_IZ', a.boy, json.dumps(oz['eski_metin_izi']), flush=True)
        jpg.replace(cik / f'WP_{a.boy}.jpg')
    (cik / f'OZET_WP_{a.boy}.json').write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str))
    print('WP', a.boy, json.dumps({q: oz[q] for q in ('durum', 'kapilar_gecti', 'baski_px', 'dosya_MB', 'jpeg_kalite')}),
          json.dumps(oz['kapilar']), flush=True)
    return 0 if oz['durum'] == 'URETILDI' and oz['kapilar_gecti'] else 1


def iz_olc(cikti, kaynak, tag_bant, tag_x, sd, esik=0.6):
    """siparis-baski-v1 eski_metin_izi_kapisi (6343550) ile ayni olcum; WP kodu (adfb2b9) kilitli oldugu icin burada.
    Yeni metin maskesi: ciktinin kendi yerel kontrast maskesi (+3 px)."""
    import io, cv2
    import numpy as np
    from PIL import Image
    from pilot6 import LUMA
    eu = sd._mod('edisyon_uret'); sd.olcek_kur(2400)

    def n24(im):
        im = im if isinstance(im, Image.Image) else Image.open(io.BytesIO(im))
        im = im.convert('RGB')
        return np.asarray(im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)).astype(np.float32) @ LUMA
    Ls, Lo = n24(kaynak), n24(cikti)
    h = min(Ls.shape[0], Lo.shape[0])
    y0, y1 = max(int(tag_bant[0]) - 12, 0), min(int(tag_bant[1]) + 12, h)
    x0, x1 = max(int(tag_x[0]) - 40, 0), min(int(tag_x[1]) + 40, 2400)
    G = eu.edisyon_maske(Ls, float(np.median(Ls)) > 128)[y0:y1, x0:x1]
    N = eu.edisyon_maske(Lo, float(np.median(Lo)) > 128)[y0:y1, x0:x1]
    N = cv2.dilate(N.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0

    def sapma(L):
        return L - cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 21).astype(np.float32)
    ds, do = sapma(Ls[y0:y1, x0:x1]), sapma(Lo[y0:y1, x0:x1])
    R = G & ~N
    B = ~cv2.dilate(G.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~N
    if R.sum() < 200 or B.sum() < 200:
        return {'gecti': None, 'sebep': 'olculecek eski glif pikseli yok', 'eski_glif_px': int(R.sum())}
    yon = 1.0 if float(np.median(ds[G])) >= 0 else -1.0
    iz, taban = float(np.mean(yon * do[R])), float(np.mean(yon * do[B]))
    return {'gecti': bool(iz - taban <= esik), 'fazla': round(iz - taban, 2), 'iz_ort': round(iz, 2),
            'taban_ort': round(taban, 2), 'eski_glif_px': int(R.sum()), 'esik': esik}


def kesit(jpg, hedef_kesit, hedef_onizleme):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(jpg) as im:
        w, h = im.size
        kes = im.crop((0, int(h * KESIT_Y[0]), w, int(h * KESIT_Y[1])))
        kes.save(hedef_kesit, 'JPEG', quality=95, subsampling=0)
        from PIL import ImageOps                          # kontrast artirilmis (iz kontrolu): %2 / %98 germe
        ImageOps.autocontrast(kes.convert('L'), cutoff=2).save(str(hedef_kesit).replace('KESIT_', 'KONTRAST_'), 'JPEG', quality=92)
        im.convert('RGB').resize((1100, round(1100 * h / w)), Image.LANCZOS).save(hedef_onizleme, 'JPEG', quality=90)
    return [w, h]


def _bantlar(jpg):
    """Sayfanin alt bolgesinde (0.62-0.95) murekkep satir kumeleri: [(ad, x0, x1, y0, y1)] - isim satiri, mesaj."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(jpg) as im:
        L = np.asarray(im.convert('L')).astype(np.float32)
    H, W = L.shape
    a0, a1 = int(H * 0.62), int(H * 0.95)
    b = L[a0:a1]
    m = np.abs(b - np.median(b)) > 45
    sat = m.sum(1) > max(W * 0.002, 3)
    kume, y = [], 0
    while y < len(sat):
        if sat[y]:
            s0 = y
            while y < len(sat) and (sat[y] or (y + 8 < len(sat) and sat[y:y + 8].any())):
                y += 1
            if y - s0 > H * 0.004:
                kume.append((s0, y))
        y += 1
    out = []
    for i, (s0, s1) in enumerate(kume[-2:]):
        cols = np.nonzero(m[s0:s1].any(0))[0]
        out.append(('isim_satiri' if i == 0 and len(kume) >= 2 else 'mesaj', int(cols.min()), int(cols.max()),
                    a0 + s0, a0 + s1, W))
    return out


def mb_olcu_tablosu(eski_dizin, yeni_dizin):
    sat = ['# MB eski (2400 buyutme) / yeni (hedef cozunurluk) olculeri', '',
           '| sayfa | oge | genislik eski / yeni (%) | yukseklik eski / yeni (%) | merkez x fark (% en) | merkez y fark (% boy) |',
           '|---|---|---|---|---|---|']
    var = False
    for y in sorted(Path(yeni_dizin).glob('*_MIDNIGHT_BLUE_*.jpg')):
        e = Path(eski_dizin) / y.name
        if not e.exists():
            continue
        var = True
        E, Y = {b[0]: b for b in _bantlar(e)}, {b[0]: b for b in _bantlar(y)}
        for ad in ('isim_satiri', 'mesaj'):
            if ad not in E or ad not in Y:
                sat.append(f'| {y.stem} | {ad} | olculemedi | | | |'); continue
            _, ex0, ex1, ey0, ey1, W = E[ad]; _, yx0, yx1, yy0, yy1, _ = Y[ad]
            ew, yw, eh, yh = ex1 - ex0, yx1 - yx0, ey1 - ey0, yy1 - yy0
            sat.append(f'| {y.stem} | {ad} | {ew} / {yw} ({100 * (yw - ew) / max(ew, 1):+.2f}) | '
                       f'{eh} / {yh} ({100 * (yh - eh) / max(eh, 1):+.2f}) | {100 * ((yx0 + yx1) - (ex0 + ex1)) / 2 / W:+.2f} | '
                       f'{100 * ((yy0 + yy1) - (ey0 + ey1)) / 2 / W:+.2f} |')
    return '\n'.join(sat) + '\n' if var else None


def mesaj_bandi_x8(jpg, hedef_1e1, hedef_x8, y=(0.815, 0.88)):
    """Mesaj bandi tam genislik 1:1 + kontrast x8 (|L - bant medyani| * 8 + 128): eski motto izi icin (Serdar 1 Eki)."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(jpg) as im:
        w, h = im.size
        kes = im.convert('RGB').crop((0, int(h * y[0]), w, int(h * y[1])))
    kes.save(hedef_1e1, 'JPEG', quality=95, subsampling=0)
    L = np.asarray(kes.convert('L')).astype(np.float32)
    Image.fromarray(np.clip((L - np.median(L)) * 8 + 128, 0, 255).astype(np.uint8)).save(hedef_x8, 'JPEG', quality=92)


def mb_karsilastir(eski, yeni, hedef, y=(0.69, 0.86), x=(0.12, 0.88)):
    """Ayni sayfanin isim + mesaj bandi 1:1: ust = eski (2400 cizim, buyutulmus), alt = yeni (hedef cozunurluk)."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    parca = []
    for yol in (eski, yeni):
        with Image.open(yol) as im:
            w, h = im.size
            parca.append(np.asarray(im.convert('RGB').crop((int(w * x[0]), int(h * y[0]), int(w * x[1]), int(h * y[1])))))
    ara = np.full((12, parca[0].shape[1], 3), 255, np.uint8)
    Image.fromarray(np.concatenate([parca[0], ara, parca[1]], 0)).save(hedef, 'JPEG', quality=95, subsampling=0)


def plate_kesit(src, plate, hedef, tag_bant=None):
    """Plate kapisinda duran sayfa: kaynak / plate / |kaynak - plate| x4, slogan + isim bolgesi 1:1 (alt alta)."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    A = Image.open(src).convert('RGB'); P = Image.open(plate).convert('RGB')
    if P.size != A.size:
        P = P.resize(A.size, Image.LANCZOS)
    k = A.width / 2400.0
    y0, y1 = (int((tag_bant[0] - 260) * k), int((tag_bant[1] + 80) * k)) if tag_bant else \
        (int(A.height * KESIT_Y[0]), int(A.height * KESIT_Y[1]))
    y0, y1 = max(0, y0), min(A.height, y1)
    a = np.asarray(A.crop((0, y0, A.width, y1))).astype(np.int16)
    p = np.asarray(P.crop((0, y0, A.width, y1))).astype(np.int16)
    f = np.clip(np.abs(a - p) * 4, 0, 255)
    Image.fromarray(np.concatenate([a, p, f], 0).astype(np.uint8)).save(hedef, 'JPEG', quality=95, subsampling=0)


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
    # 24x36 mesaj bandi 1:1 + x8 (5 renk; Serdar 1 Eki, MB 24x36 iz kontrolu)
    for renk in ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY'):
        j = sorted((kok / 'renk' / renk / renk).glob(f'*_{renk}_2x3_24x36.jpg'))
        if j:
            mesaj_bandi_x8(j[0], inc / f'MESAJ_24x36_{renk}_1e1.jpg', inc / f'MESAJ_24x36_{renk}_x8.jpg')
    if (kok / 'wp' / '24x36' / 'WP_24x36.jpg').exists():
        mesaj_bandi_x8(kok / 'wp' / '24x36' / 'WP_24x36.jpg', inc / 'MESAJ_24x36_WARM_PARCHMENT_1e1.jpg',
                       inc / 'MESAJ_24x36_WARM_PARCHMENT_x8.jpg')
    # MB eski / yeni olcu tablosu (isimler + mesaj: genislik, yukseklik, merkez; % fark) - Serdar 1 Eki: <= %1
    tab = mb_olcu_tablosu(kok / 'eski' / 'MIDNIGHT_BLUE' / 'MIDNIGHT_BLUE', kok / 'renk' / 'MIDNIGHT_BLUE' / 'MIDNIGHT_BLUE')
    if tab:
        (inc / 'MB_OLCU.md').write_text(tab)
        print(tab, flush=True)
    # MB eski (2400 buyutme) / yeni (hedef cozunurluk) isim bandi 1:1 kesiti (Serdar 1 Eki)
    for boy in ('24x36', '16x20'):
        e = sorted((kok / 'eski' / 'MIDNIGHT_BLUE' / 'MIDNIGHT_BLUE').glob(f'*_MIDNIGHT_BLUE_*_{boy}.jpg'))
        y = sorted((kok / 'renk' / 'MIDNIGHT_BLUE' / 'MIDNIGHT_BLUE').glob(f'*_MIDNIGHT_BLUE_*_{boy}.jpg'))
        if e and y:
            mb_karsilastir(e[0], y[0], inc / f'MB_ESKI_YENI_{boy}_ISIM_BANDI.jpg')
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
