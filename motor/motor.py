#!/usr/bin/env python3
"""AstroLoveArt kisisel poster MOTORU, prototip (3 Eki 2026, Serdar onayi). Eski poster ustune yama YOK:
sayfa bos kagittan (PLATES) katmanlarla sifirdan kurulur. Yapay zeka gorsel uretimi YOK.

Katmanlar (sabitler: motor/olc.py ciktisi, orijinal satis posterinden olculur):
  1 kagit         temiz ana zemin motor/varlik/plates/<plate>_temiz.png (PLATES/<plate>.png, bir kez onarilmis,
                  sha sabitlerde; render sirasinda zemin rotusu YOK; halka zeminde)
  2 buyuk sembol  main_symbols/<a>_<b>_gold.png   (olculen olcek + konum)
  3 kucuk sembol  zodiac_symbols_gold/<burc>_symbol_gold.png (olculen olcek, y; x = isim merkezi + olculen dx)
  4 isimler       Cinzel wght 500, olculen govde/punto, taban, bosluk; satir poster ortasinda (SECENEK D)
  5 sonsuz        orijinal posterden olculen murekkep gucu (yuksek cozunurluklu kaynak yok), satirla kayar
  6 tagline       EB Garamond Italic 400, olculen punto/taban, ortali, genislik siniri asilirsa yalniz o kuculur
Renk: once murekkep gucu haritasi kurulur: m = alfa x Lk(oge) x s, Lk = orijinalde olculen oge murekkep gucu,
s = altin katmanin golgelenmesi (luma), genligi orijinalin olculen cv'sine (std/ortanca) esitlenir; isim/tagline
golgesi burc adi altin plakasinin satir profili (ONAYLI.json). WARM_PARCHMENT'ta harita kilitli wp_bakir.bakir_bas
ile bakira basilir. Serdar 3 Eki: bakir = eski sistem wp_bakir rengi ve dokusu -> sabitlerde 'bakir' varsa (bakir_olc.py,
Test 5 WP 11x14 olcumu) her oge grubu kendi hedef rengi, golge genligi (cv) ve isim/mesajda kilitli kabartma ile
basilir; yoksa orijinal posterin olculen rengi (prototip 1).

Kullanim: motor.py --kaynak DIR --sabit motor/sabitler/X.json --isim1 MAXWELL --isim2 QUINN --mesaj "..." --cikti DIR
"""
import argparse, hashlib, json, sys, time, unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / 'kilitli'))
import wp_katman as wk                                                # noqa: E402 (kilitli)
import wp_bakir as wb                                                 # noqa: E402 (kilitli)

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def rgba(f):
    return np.asarray(Image.open(f).convert('RGBA'), np.float32) / 255.0


def murekkep_katmani(katman, Lk, cv_hedef):
    """RGBA katman (0-1) -> murekkep gucu (luma birimi). s = 1 + k (med - g) / med, g = katman lumasi (koyu altin =
    guclu murekkep); k, cekirdekte (alfa > 0.9) std(s) / ort(s) orijinalin olculen cv'sine esit olacak sekilde."""
    a = katman[..., 3]
    g = katman[..., :3] @ wk.LUMA
    ce = a > 0.9
    med = float(np.median(g[ce]))
    u = (med - g) / max(med, 1e-3)
    k = cv_hedef / max(float(u[ce].std()), 1e-4)
    s = np.clip(1 + k * u, 0.4, 1.6)
    return a * Lk * s, {'k': round(k, 3), 'cv_katman': round(float(u[ce].std()), 4)}


def yapistir(M, A, m, a, x, y):
    """murekkep gucu m (h, w) ve alfa a sayfa haritalarina (max) yazilir."""
    h, w = m.shape
    H, W = M.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    M[y0:y1, x0:x1] = np.maximum(M[y0:y1, x0:x1], m[y0 - y:y1 - y, x0 - x:x1 - x])
    A[y0:y1, x0:x1] = np.maximum(A[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])


def olcekle(f, w, h):
    im = Image.open(f).convert('RGBA').resize((w, h), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def profil(f):
    """Altin plakanin satir profili: her satirda alfa > 0.5 piksellerin ortalama RGB'si, murekkep satirlari."""
    a = rgba(f)
    m = a[..., 3] > 0.5
    sat = np.nonzero(m.sum(1) > 0.02 * m.shape[1])[0]
    pr = np.array([a[y][m[y]][:, :3].mean(0) for y in sat], np.float32)
    return pr


def buyuk(s, tr=False):
    if tr:
        s = s.replace('i', 'İ').replace('ı', 'I')
    return s.upper()


def font(dosya, punto, wght):
    f = ImageFont.truetype(str(KOK / 'font' / dosya), int(round(punto)))
    if wght:
        f.set_variation_by_axes([wght])
    return f


def metin_katmani(metin, f, pr, govde_ust):
    """Metni (alfa) cizer ve dokuyu verir: profil, buyuk harf govdesi (govde_ust..taban) satirlarina gerilir.
    Doner: RGBA (0-1), taban y (katman ici), murekkep kutusu (katman ici)."""
    b = f.getbbox(metin, anchor='ls')
    pad = 8
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), metin, font=f, fill=255, anchor='ls')
    A = np.asarray(im, np.float32) / 255.0
    taban = pad - b[1]
    ust = taban - govde_ust
    # profil govde satirlarina gerilir; govde disi satirlar (aksan, inen harf) en yakin uc rengini alir
    n = max(1, taban - ust)
    idx = np.clip(np.arange(h) - ust, 0, n - 1) * (len(pr) - 1) / max(n - 1, 1)
    renk = np.stack([np.interp(idx, np.arange(len(pr)), pr[:, c]) for c in range(3)], 1)
    K = np.concatenate([np.repeat(renk[:, None, :], w, 1), A[..., None]], 2)
    ys, xs = np.nonzero(A > 0.5)
    return K, taban, [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def pdf_yaz(im, C, W, H):
    """PDF: sayfa W/300 x H/300 inc, 300 dpi goruntu (JPEG 95, eski sistemle ayni)."""
    import fitz
    jp = C / '_sayfa.jpg'
    im.save(jp, 'JPEG', quality=95, subsampling=0, dpi=(300, 300))
    d = fitz.open()
    pg = d.new_page(width=W / 300 * 72, height=H / 300 * 72)
    pg.insert_image(pg.rect, filename=str(jp))
    d.save(C / 'MOTOR.pdf')
    jp.unlink()


def altin_bas(a, Z, K, C, i1, i2, mesaj, rap):
    """ALTIN edisyonlar (MIDNIGHT_BLUE, DEEP_BLACK, PURE_WHITE, CHAMPAGNE_IVORY): orijinal, altin katmanlarin plate
    ustune normal (alfa) bindirmesi (olculdu: oge disinda isilti yok, S - P p99 0.9). Sayfa = plate x (1 - A) + renk:
      semboller : altin katman, rengi orijinalden olculen kanal tablosuyla (LUT, katman -> orijinal)
      isim/mesaj: Cinzel / EB Garamond alfa, renk = orijinal kelimenin harf cekirdegi satir profili (olculen)
      sonsuz    : orijinal posterden fark (S - P), satirla kayar (yuksek cozunurluklu kaynak yok)"""
    W, H = Z['tuval']
    sol, sag = (x.lower() for x in Z['cift'].split('_'))
    pf = Path(a.plate_dosya) if a.plate_dosya else K / 'plates' / f"{Z['plate']}.png"
    rap['zemin'] = {'dosya': pf.name, 'sha256': hashlib.sha256(pf.read_bytes()).hexdigest()}
    P = np.asarray(Image.open(pf).convert('RGB'), np.float32)
    if P.shape[:2] != (H, W):
        sys.exit(f'FAIL: plate boyu {P.shape[:2]} != tuval {(H, W)}')
    td = getattr(a, 'tek_doku', False)
    P_ham = P
    if td:
        # Serdar 3 Eki TEK DOKU: cember plate'ten bir kez ayrildi (halka_altin.py, sha kayitli); burada halkasiz
        # zemin + cember katmani, ana sembol modeliyle boyanir
        import tek_doku as tdk
        kay = json.loads((KOK / 'varlik' / 'plates' / f'{pf.stem}_halkasiz.json').read_text())
        zf, hf = KOK.parent / kay['halkasiz_zemin']['dosya'], KOK.parent / kay['halka']['dosya']
        for f_, h_ in ((zf, kay['halkasiz_zemin']['sha256']), (hf, kay['halka']['sha256'])):
            if hashlib.sha256(f_.read_bytes()).hexdigest() != h_:
                sys.exit(f'FAIL: {f_.name} sha uyusmuyor')
        if kay['kaynak_plate']['sha256'] != rap['zemin']['sha256']:
            sys.exit('FAIL: halkasiz zemin bu plate'"'"'ten degil')
        P = np.asarray(Image.open(zf).convert('RGB'), np.float32)
        a_halka = np.asarray(Image.open(hf), np.float32) / 255.0
        rap['zemin']['halkasiz'] = {'dosya': kay['halkasiz_zemin']['dosya'], 'sha256': kay['halkasiz_zemin']['sha256']}
    Cp = np.zeros((H, W, 3), np.float32)                               # on carpilmis renk
    A = np.zeros((H, W), np.float32)
    maske = {}
    AL = Z['altin']

    def bindir(ad, renk, al, x, y):
        h, w = al.shape
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        aa = al[y0 - y:y1 - y, x0 - x:x1 - x]
        cc = renk[y0 - y:y1 - y, x0 - x:x1 - x]
        Cp[y0:y1, x0:x1] = Cp[y0:y1, x0:x1] * (1 - aa[..., None]) + cc * aa[..., None]
        A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - aa) + aa
        mm = np.zeros((H, W), bool); mm[y0:y1, x0:x1] = aa > 0.02
        maske[ad] = mm

    def plate_bolge(x, y, h, w):
        """katman yerlesimi altindaki zemin (sayfa disi kenar kopyasi)."""
        ys = np.clip(np.arange(y, y + h), 0, H - 1); xs = np.clip(np.arange(x, x + w), 0, W - 1)
        return P[np.ix_(ys, xs)]

    def lut_uygula(rgb01, lut):
        g = rgb01 * 255
        return np.stack([np.interp(g[..., c], np.arange(256), np.asarray(lut[c], np.float32)) for c in range(3)], -1)

    b = Z['buyuk_sembol']
    d_bs = None
    if b.get('kaynak') == 'orijinal':
        # ana sembol orijinal posterden plate farki (yerinde; LEGACY katman cizimi orijinalden farkli). Maske: kutu
        # +-pad icinde murekkep (> wk.ESIK) 7 px genisletilmis, gurultu tabani (wb.T0) ustu, plate halkasi disi.
        from olc import halka_maskesi
        x0, y0, x1, y1 = b['kutu']
        pd = 12
        kk = (x0 - pd, y0 - pd, x1 + pd, y1 + pd)
        so_b = np.asarray(Image.open(a.orijinal).convert('RGB').crop(kk), np.float32)
        pb = P_ham[y0 - pd:y1 + pd, x0 - pd:x1 + pd]
        d_bs = so_b - pb
        mb = np.clip(-(d_bs @ wk.LUMA) * Z.get('isaret', 1.0), 0, None)
        mk_bs = cv2.dilate((mb > wk.ESIK).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & (mb >= wb.T0)
        mk_bs &= ~halka_maskesi(P_ham)[y0 - pd:y1 + pd, x0 - pd:x1 + pd]
        d_bs = d_bs * mk_bs[..., None]
        if td:
            # kaplama alfasi: murekkep maskesi (> wk.ESIK), 1 px yumusatma (parlakliktan bagimsiz; altin dokusu
            # parlakliga girmesin). Referans renkler: 5x5 asindirilmis cekirdek (tum ton araligi)
            ink_b = (mb > wk.ESIK).astype(np.float32)
            al_b = cv2.GaussianBlur(ink_b, (0, 0), 1.0) * mk_bs
            rgb_ref_b = pb + d_bs
            ce_b = cv2.erode(ink_b.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            ref_rgb, kb_al, kb_L = rgb_ref_b[ce_b], al_b, rgb_ref_b @ wk.LUMA
            Lmed_q = tdk.qc_cekirdek_L(rgb_ref_b, mk_bs.astype(np.float32), pb, W, Z.get('isaret', 1.0))
        log('buyuk sembol (orijinal fark)', b['kutu'], int(mk_bs.sum()))
    else:
        k = olcekle(K / f'main_{sol}_{sag}_gold.png', b['w'], b['h'])
        rgb_b = lut_uygula(k[..., :3], AL['buyuk_sembol']['lut'])
        if td:
            ref_rgb, kb_al, kb_L = rgb_b[k[..., 3] > 0.98], k[..., 3], rgb_b @ wk.LUMA
            Lmed_q = tdk.qc_cekirdek_L(rgb_b, k[..., 3], plate_bolge(b['x'], b['y'], *k.shape[:2]), W, Z.get('isaret', 1.0))
    if td:
        # ana sembol modeli: renk egrisi, parlaklik, kabartma (tum ogelere ayni, kabartma tek kez)
        # Lmed: qc ile ayni olcum (QC olcegi, murekkep cekirdegi ortancasi); doku: boru profili x kabartma
        model = {'egri': tdk.egri_olc(ref_rgb.astype(np.float32)), 'Lmed': Lmed_q, 'doku': tdk.doku_olc(kb_al, kb_L, W)}
        rap['tek_doku'] = {'Lmed': round(model['Lmed'], 2), 'doku': model['doku'], 'k': {},
                           'egri_ornek': {str(l): [round(float(v), 1) for v in model['egri'][l]] for l in (100, 150, 200, 240)}}
        log('tek doku modeli', rap['tek_doku'])
        isr = Z.get('isaret', 1.0)

        def td_boya(ad, l, Aa, Pb):
            c_, k_ = tdk.boya(l, Aa, Pb, W, isr, model)
            rap['tek_doku']['k'][ad] = k_
            return c_
        bindir('daire', td_boya('daire', tdk.duz_l(a_halka, model), a_halka, P), a_halka, 0, 0)   # cember
    if b.get('kaynak') != 'orijinal':
        bindir('buyuk_sembol', rgb_b, k[..., 3], b['x'], b['y'])
        del k, rgb_b
        log('buyuk sembol', b['w'], b['h'], b['x'], b['y'])

    # isim satiri (SECENEK D, WP ile ayni kural)
    I = Z['isim']
    p = I['punto']['kullanilan']
    kenar = I['kenar_payi']
    g_bosluk = (I['bosluk_sol'] + I['bosluk_sag']) / 2
    son = Z['sonsuz']
    so = np.asarray(Image.open(a.orijinal).convert('RGB'), np.float32)
    x0, y0, x1, y1 = son['kutu']
    pad = 6
    d_inf = (so - P_ham)[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
    if td:
        L_s = so[y0 - pad:y1 + pad, x0 - pad:x1 + pad] @ wk.LUMA
        L_p = P_ham[y0 - pad:y1 + pad, x0 - pad:x1 + pad] @ wk.LUMA
    del so
    sgn = Z.get('isaret', 1.0)
    m_inf = np.clip(-(d_inf @ wk.LUMA) * sgn, 0, None)
    a_inf = (m_inf >= wb.T0).astype(np.float32)                         # wp_bakir.T0 gurultu tabani
    d_inf = d_inf * a_inf[..., None]
    if td:
        # sonsuz: alfa = fark / cekirdek ortancasi; altin luma dokusu = (S - P(1 - a)) / a; ana sembol modeliyle
        Lk_i = float(np.median(m_inf[m_inf > wk.ESIK]))
        al_i = np.clip(m_inf / Lk_i, 0, 1) * (m_inf >= wb.T0)
        lg = np.clip((L_s - L_p * (1 - al_i)) / np.maximum(al_i, 0.25), 0, 255)
        rgb_i = td_boya('sonsuz', lg, al_i, P[y0 - pad:y1 + pad, x0 - pad:x1 + pad])
    pr1, pr2 = np.asarray(AL['isim_sol'], np.float32) / 255, np.asarray(AL['isim_sag'], np.float32) / 255
    olcek = 1.0
    for _ in range(20):
        f = font(I['font'], p * olcek, I['wght'])
        gov = -f.getbbox('H', anchor='ls')[1]
        k1, t1, kk1 = metin_katmani(i1, f, pr1, gov)
        k2, t2, kk2 = metin_katmani(i2, f, pr2, gov)
        w1, w2 = kk1[2] - kk1[0], kk2[2] - kk2[0]
        winf = son['genislik'] * olcek
        top = w1 + g_bosluk * olcek + winf + g_bosluk * olcek + w2
        if top <= W - 2 * kenar:
            break
        olcek *= (W - 2 * kenar) / top * 0.999
    sx = W / 2 - top / 2
    taban = I['taban_y']
    xy1 = (int(round(sx - kk1[0])), int(round(taban - t1)))
    bindir('isim1', td_boya('isim1', tdk.duz_l(k1[..., 3], model), k1[..., 3], plate_bolge(*xy1, *k1.shape[:2]))
           if td else k1[..., :3] * 255, k1[..., 3], *xy1)
    inf_x = sx + w1 + g_bosluk * olcek
    if olcek != 1:
        d_inf = cv2.resize(d_inf, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA)
        a_inf = cv2.resize(a_inf, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA)
        if td:
            rgb_i = cv2.resize(rgb_i, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA)
            al_i = cv2.resize(al_i, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA)
    inf_y = int(round(y0 - pad + (son['kutu'][3] - son['kutu'][1]) * (1 - olcek) / 2))
    inf_x0 = int(round(inf_x - pad * olcek))
    x2 = inf_x + winf + g_bosluk * olcek
    xy2 = (int(round(x2 - kk2[0])), int(round(taban - t2)))
    bindir('isim2', td_boya('isim2', tdk.duz_l(k2[..., 3], model), k2[..., 3], plate_bolge(*xy2, *k2.shape[:2]))
           if td else k2[..., :3] * 255, k2[..., 3], *xy2)
    if td:
        bindir('sonsuz', rgb_i, al_i, inf_x0, inf_y)
    merk = {'sol': sx + w1 / 2, 'sag': x2 + w2 / 2}
    rap['isim_satiri'] = {'olcek': round(olcek, 4), 'punto': round(p * olcek, 1), 'baslangic_x': round(sx, 1),
                          'genislik': round(top, 1), 'merkez_x': round(sx + top / 2, 1), 'isim_merkez': merk}
    log('isim satiri', rap['isim_satiri'])

    for t, burc in (('sol', sol), ('sag', sag)):
        s = Z[f'kucuk_sembol_{t}']
        kx = (s['kutu'][0] + s['kutu'][2]) / 2
        ix = (I[f'kutu_{t}'][0] + I[f'kutu_{t}'][2]) / 2
        dx = merk[t] - ix
        k = olcekle(K / f'sym_{burc}_gold.png', s['w'], s['h'])
        rgb_k = lut_uygula(k[..., :3], AL['kucuk_sembol']['lut'])
        xyk = (int(round(s['x'] + dx)), s['y'])
        if td:
            rgb_k = td_boya(f'kucuk_sembol_{t}', rgb_k @ wk.LUMA, k[..., 3], plate_bolge(*xyk, *k.shape[:2]))
        bindir(f'kucuk_sembol_{t}', rgb_k, k[..., 3], *xyk)
        rap.setdefault('kucuk_sembol', {})[t] = {'merkez_x': round(kx + dx, 1), 'isim_merkez_x': round(merk[t], 1)}

    MS = Z['mesaj']
    prm = np.asarray(AL[AL.get('mesaj_profili', 'mesaj')], np.float32) / 255
    pm = MS['punto']
    for _ in range(20):
        f = font(MS['font'], pm, MS['wght'])
        gov = -f.getbbox('T', anchor='ls')[1]
        km, tm, kkm = metin_katmani(mesaj, f, prm, gov)
        wm = kkm[2] - kkm[0]
        if wm <= MS['genislik_siniri']:
            break
        pm *= MS['genislik_siniri'] / wm * 0.999
    xym = (int(round(W / 2 - wm / 2 - kkm[0])), int(round(MS['taban_y'] - tm)))
    bindir('mesaj', td_boya('mesaj', tdk.duz_l(km[..., 3], model), km[..., 3], plate_bolge(*xym, *km.shape[:2]))
           if td else km[..., :3] * 255, km[..., 3], *xym)
    rap['mesaj'] = {'punto': round(pm, 1), 'genislik': wm, 'kuculme': round(pm / MS['punto'], 4),
                    'profil': AL.get('mesaj_profili', 'mesaj')}
    log('tagline', rap['mesaj'])

    if td:
        # Serdar 3 Eki B: isim / sonsuz / tagline kutusu + pay icindeki plate yildizlari (yalniz bu payda)
        kut = []
        for ad in ('isim1', 'isim2', 'sonsuz', 'mesaj'):
            ys, xs = np.nonzero(maske[ad])
            kut.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
        P, rap['yildiz'] = tdk.yildiz_temizle(P, kut, W)
        log('yildiz', rap['yildiz'])
    out = P * (1 - A[..., None]) + Cp
    del Cp
    if not td:
        h, w = a_inf.shape
        out[inf_y:inf_y + h, inf_x0:inf_x0 + w] += d_inf
        mm = np.zeros((H, W), bool); mm[inf_y:inf_y + h, inf_x0:inf_x0 + w] = a_inf > 0.02
        maske['sonsuz'] = mm
        A[mm] = np.maximum(A[mm], a_inf[a_inf > 0.02])
    if d_bs is not None:
        x0, y0, x1, y1 = b['kutu']
        out[y0 - 12:y1 + 12, x0 - 12:x1 + 12] += d_bs
        mm = np.zeros((H, W), bool); mm[y0 - 12:y1 + 12, x0 - 12:x1 + 12] = mk_bs
        maske['buyuk_sembol'] = mm
        A[mm] = 1.0
    u8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
    del out
    im = Image.fromarray(u8)
    im.save(C / 'MOTOR.png', dpi=(300, 300))
    np.save(C / '_beklenen_maske.npy', np.packbits(A > 0.02))
    json.dump({k: [int(x) for x in np.nonzero(v.any(1))[0][[0, -1]]] + [int(x) for x in np.nonzero(v.any(0))[0][[0, -1]]]
               for k, v in maske.items()}, open(C / '_oge_kutulari.json', 'w'))
    pdf_yaz(im, C, W, H)
    rap['sure_sn'] = round(time.time() - T0, 1)
    (C / 'MOTOR_RAPOR.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    log('bitti', C)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--sabit', required=True)
    ap.add_argument('--isim1', required=True)
    ap.add_argument('--isim2', required=True)
    ap.add_argument('--mesaj', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--tr', action='store_true', help='Turkce buyuk harf kurali (i -> İ)')
    ap.add_argument('--orijinal', help='orijinal satis posteri (varsayilan: KAYNAK/orijinal_WP_11x14.jpg)')
    ap.add_argument('--plate-dosya', help='altin edisyon plate dosyasi (varsayilan: KAYNAK/plates/<plate>.png)')
    ap.add_argument('--tek-doku', action='store_true', help='altin: tum ogeler ana sembol modeliyle + yazi cevresi '
                                                              'yildiz temizligi (Serdar 3 Eki)')
    a = ap.parse_args()
    K, C = Path(a.kaynak), Path(a.cikti)
    C.mkdir(parents=True, exist_ok=True)
    Z = json.loads(Path(a.sabit).read_text())
    W, H = Z['tuval']
    sol, sag = (x.lower() for x in Z['cift'].split('_'))
    i1, i2 = buyuk(unicodedata.normalize('NFC', a.isim1), a.tr), buyuk(unicodedata.normalize('NFC', a.isim2), a.tr)
    mesaj = unicodedata.normalize('NFC', a.mesaj)
    rap = {'girdi': {'isim1': i1, 'isim2': i2, 'mesaj': mesaj}}
    if Z.get('mod') == 'altin':
        a.orijinal = a.orijinal or str(K / 'orijinal_WP_11x14.jpg')
        return altin_bas(a, Z, K, C, i1, i2, mesaj, rap)

    # ---- murekkep gucu haritasi (katmanlar)
    P_c = np.asarray(Image.open(K / 'plates' / f"MODERN_{Z['boy']}.png").convert('RGB'))
    Lc = np.empty(P_c.shape[:2], np.float32)                           # satir parcalari (bellek; sonuc ayni)
    for i in range(0, len(Lc), 512):
        Lc[i:i + 512] = P_c[i:i + 512].astype(np.float32) @ wk.LUMA
    Lp = float(np.median(Lc))                                          # wp_ornek ile ayni (duz renk kagidi)
    del P_c, Lc
    M = np.zeros((H, W), np.float32)
    A = np.zeros((H, W), np.float32)
    maske, golge = {}, {}
    RO = Z['bakir']['ogeler'] if 'bakir' in Z else Z['renk']['ogeler']
    BANT = {'buyuk_sembol': 'buyuk_sembol', 'kucuk_sembol_sol': 'kucuk_sembol', 'kucuk_sembol_sag': 'kucuk_sembol',
            'isim1': 'isim', 'isim2': 'isim', 'sonsuz': 'isim', 'mesaj': 'mesaj', 'daire': 'daire'}

    METIN = ('isim1', 'isim2', 'mesaj')

    def ekle(ad, katman, x, y, ham=None):
        a0 = A.copy()
        if ham is None:
            o = RO[BANT[ad]]
            # Serdar 3 Eki (deneme 3): isim/mesajda altin plaka satir profili golgesi YOK (ufuk cizgisi harf ici
            # yatay renk bandi uretiyordu, qc e). WP'de yazi dokusu = kilitli kabartma (eski hattaki gibi).
            cv_h = 0.0 if (ad in METIN and 'bakir' in Z) else o['cv']
            m, golge[ad] = murekkep_katmani(katman, o['Lk'], cv_h)
            a = katman[..., 3]
        else:
            m, a = ham, katman
        yapistir(M, A, m, a, x, y)
        maske[ad] = (A - a0) > 0.02

    if 'halka' in Z:                                                   # halka katmani (zemin halkasiz)
        hf = KOK.parent / Z['halka']['dosya']
        if hashlib.sha256(hf.read_bytes()).hexdigest() != Z['halka']['sha256']:
            sys.exit('FAIL: halka katmani sha uyusmuyor')
        ah = np.asarray(Image.open(hf), np.float32) / 255.0
        ekle('daire', ah, 0, 0, ham=ah * RO['daire']['Lk'])
        log('halka', Z['halka']['dosya'])
    b = Z['buyuk_sembol']
    ekle('buyuk_sembol', olcekle(K / f'main_{sol}_{sag}_gold.png', b['w'], b['h']), b['x'], b['y'])
    log('buyuk sembol', b['w'], b['h'], b['x'], b['y'])

    # isim satiri
    I = Z['isim']
    p = I['punto']['kullanilan']
    kenar = I['kenar_payi']
    g_bosluk = (I['bosluk_sol'] + I['bosluk_sag']) / 2
    son = Z['sonsuz']
    x0, y0, x1, y1 = son['kutu']
    pad = 6
    kk = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)                      # yalniz sonsuz kutusu okunur (bellek)
    so = np.asarray(Image.open(a.orijinal or K / 'orijinal_WP_11x14.jpg').convert('RGB').crop(kk), np.float32)
    pl = np.asarray(Image.open(K / 'plates' / f"{Z['plate']}.png").convert('RGB').crop(kk), np.float32)
    m_inf = np.clip((pl - so) @ wk.LUMA, 0, None)
    del so, pl
    Lk_inf = float(np.median(m_inf[m_inf > wk.ESIK]))
    a_inf = np.clip((m_inf - wk.ESIK * 0.0) / Lk_inf, 0, 1)
    a_inf[m_inf < 4] = 0                                               # wp_bakir.T0 gurultu tabani
    pr1, pr2 = profil(K / f'name_{sol}_gold.png'), profil(K / f'name_{sag}_gold.png')
    olcek = 1.0
    for _ in range(20):
        f = font(I['font'], p * olcek, I['wght'])
        gov = -f.getbbox('H', anchor='ls')[1]
        k1, t1, kk1 = metin_katmani(i1, f, pr1, gov)
        k2, t2, kk2 = metin_katmani(i2, f, pr2, gov)
        w1, w2 = kk1[2] - kk1[0], kk2[2] - kk2[0]
        winf = son['genislik'] * olcek
        top = w1 + g_bosluk * olcek + winf + g_bosluk * olcek + w2
        if top <= W - 2 * kenar:
            break
        olcek *= (W - 2 * kenar) / top * 0.999
    sx = W / 2 - top / 2
    taban = I['taban_y']
    ekle('isim1', k1, int(round(sx - kk1[0])), int(round(taban - t1)))
    inf_x = sx + w1 + g_bosluk * olcek
    ai = cv2.resize(a_inf, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA) if olcek != 1 else a_inf
    mi = cv2.resize(m_inf, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA) if olcek != 1 else m_inf
    mi = np.where(ai > 0, mi, 0).astype(np.float32)
    inf_y = y0 - pad + (son['kutu'][3] - son['kutu'][1]) * (1 - olcek) / 2
    ekle('sonsuz', ai, int(round(inf_x - pad * olcek)), int(round(inf_y)), ham=mi)
    x2 = inf_x + winf + g_bosluk * olcek
    ekle('isim2', k2, int(round(x2 - kk2[0])), int(round(taban - t2)))
    merk = {'sol': sx + w1 / 2, 'sag': x2 + w2 / 2}
    rap['isim_satiri'] = {'olcek': round(olcek, 4), 'punto': round(p * olcek, 1), 'baslangic_x': round(sx, 1),
                          'genislik': round(top, 1), 'merkez_x': round(sx + top / 2, 1), 'isim_merkez': merk}
    log('isim satiri', rap['isim_satiri'])

    # kucuk semboller: x isim merkezine (olculen dx), y ve olcek olculen
    for t, burc in (('sol', sol), ('sag', sag)):
        s = Z[f'kucuk_sembol_{t}']
        kx = (s['kutu'][0] + s['kutu'][2]) / 2
        ix = (I[f'kutu_{t}'][0] + I[f'kutu_{t}'][2]) / 2
        dx = merk[t] - ix
        ekle(f'kucuk_sembol_{t}', olcekle(K / f'sym_{burc}_gold.png', s['w'], s['h']), int(round(s['x'] + dx)), s['y'])
        rap.setdefault('kucuk_sembol', {})[t] = {'merkez_x': round(kx + dx, 1), 'isim_merkez_x': round(merk[t], 1)}

    # tagline
    MS = Z['mesaj']
    prm = profil(K / 'name_cancer_gold.png')                           # ONAYLI: tagline dokusu cancer profili
    pm = MS['punto']
    for _ in range(20):
        f = font(MS['font'], pm, MS['wght'])
        gov = -f.getbbox('T', anchor='ls')[1]
        km, tm, kkm = metin_katmani(mesaj, f, prm, gov)
        wm = kkm[2] - kkm[0]
        if wm <= MS['genislik_siniri']:
            break
        pm *= MS['genislik_siniri'] / wm * 0.999
    ekle('mesaj', km, int(round(W / 2 - wm / 2 - kkm[0])), int(round(MS['taban_y'] - tm)))
    rap['mesaj'] = {'punto': round(pm, 1), 'genislik': wm, 'kuculme': round(pm / MS['punto'], 4)}
    log('tagline', rap['mesaj'])

    # ---- bakir (WARM_PARCHMENT): kilitli model, hedef = orijinalin olculen dolu murekkep rengi
    zf = KOK.parent / Z['zemin']['dosya']
    sha = hashlib.sha256(zf.read_bytes()).hexdigest()
    if sha != Z['zemin']['sha256']:
        sys.exit(f"FAIL: temiz zemin sha uyusmuyor {sha} != {Z['zemin']['sha256']}")
    rap['zemin'] = {'dosya': Z['zemin']['dosya'], 'sha256': sha}
    P = np.asarray(Image.open(zf).convert('RGB'), np.float32)
    D = None if 'bakir' in Z else -np.repeat(M[..., None], 3, 2)       # D @ LUMA = -m (LUMA toplami 1)
    rap['golge'] = golge
    if 'bakir' not in Z:
        hedef = Z['renk']['hepsi']['rgb']
        bant = {ad: tuple(v) for ad, v in Z['bantlar'].items()}
        out, bb = wb.bakir_bas(D, P, hedef, Lp, bant, None)
        rap['bakir'] = {k: v for k, v in bb.items() if k not in ('core', 'ce', 'M', 'dolu', 'te')}
        rap['bakir']['hedef'] = hedef
    else:
        # oge grubu basina kilitli bakir_bas: hedef = Test 5 grubunun olculen rengi; isim + mesajda kabartma
        out, rap['bakir'] = P, {}
        kb = Z['bakir']['kabartma']
        for g in (('daire',) if 'halka' in Z else ()) + ('buyuk_sembol', 'kucuk_sembol', 'isim', 'mesaj'):
            mg = np.zeros((H, W), bool)
            for ad, v in maske.items():
                if BANT[ad] == g:
                    mg |= v
            mg = cv2.dilate(mg.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
            ys = np.nonzero(mg.any(1))[0]
            # bellek (3 Eki, 24x36 WP): kilitli bakir_bas grubun satir bandinda (+-100 px) kosar; tum islemleri yerel
            # (bilesen, medyan yalniz grup murekkebinde, genisletme / bulaniklik < 100 px), 11x14 ciktisi birebir ayni
            c0, c1 = max(0, int(ys[0]) - 100), min(H, int(ys[-1]) + 101)
            satir = np.zeros(c1 - c0, bool); satir[ys[0] - c0:ys[-1] + 1 - c0] = True
            kab = {'satirlar': satir, **kb} if g in ('isim', 'mesaj') else None
            hedef = Z['bakir']['ogeler'][g]['rgb']
            Dg = -np.repeat((M[c0:c1] * mg[c0:c1])[..., None], 3, 2)     # = D * mg, yalniz bant (bellek)
            o2, bb = wb.bakir_bas(Dg, out[c0:c1], hedef, Lp,
                                  {g: (int(ys[0]) - c0, int(ys[-1]) + 1 - c0)}, None, kabartma=kab)
            out[c0:c1] = o2                                            # P yerinde (P bundan sonra okunmaz)
            rap['bakir'][g] = {**{k: v for k, v in bb.items() if k not in ('core', 'ce', 'M', 'dolu', 'te')},
                               'hedef': hedef, 'kabartma': bool(kab)}
    log('bakir', rap['bakir'])
    np.round(out, out=out); np.clip(out, 0, 255, out=out)               # yerinde (bellek); sonuc ayni
    u8 = out.astype(np.uint8)
    del out, D
    im = Image.fromarray(u8)
    im.save(C / 'MOTOR.png', dpi=(300, 300))
    np.save(C / '_beklenen_maske.npy', np.packbits(A > 0.02))
    json.dump({k: [int(x) for x in np.nonzero(v.any(1))[0][[0, -1]]] + [int(x) for x in np.nonzero(v.any(0))[0][[0, -1]]]
               for k, v in maske.items()}, open(C / '_oge_kutulari.json', 'w'))
    pdf_yaz(im, C, W, H)
    rap['sure_sn'] = round(time.time() - T0, 1)
    (C / 'MOTOR_RAPOR.json').write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    log('bitti', C)


if __name__ == '__main__':
    main()
