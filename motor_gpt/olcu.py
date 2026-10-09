# Olcu basina musteri dosyasi (9 Eki 2026, Serdar teslim kurali): 2:3 ana goruntu (7200x10800) -> secilen olcunun TAM pikseli @300 dpi.
# Iki yontem (Serdar goz ile secer):
#   A kirpma        : tam genislik korunur, ust/alt kirpilir; pencere icerik kutusunun ortasina hizalanir; sonra hedef piksele.
#   B yeniden yerlesim: tum poster yukseklige sigacak kadar kucultulur (oranlar ve bosluklar korunur), yanlara zemin eklenir
#                     (zemin_profil.json radyal profili + ana goruntunun oge disi bolgelerinden yildiz/doku fazlaligi); sonra hedef piksele.
# Kapi g: < 20 MB, piksel tam, 4:4:4, 300 dpi; halka (sigma 8, ayni olcunun yuzer kaynagina gore) <= 0.10 HER OLCUDE
#   (Serdar 9 Eki aksam; Test 11 goz FAIL, ders 263-266. "yalniz 7200 genislik" karari IPTAL).
# Gren (Serdar 9 Eki aksam): kucultme zemin grenini ortaliyor, JPEG q97 zayif greni silip gradyani kademeliyor (halka). Kucultmeden SONRA
#   yalniz koyu zemine kanal basina Gauss gren eklenir: 10 olcude toplam gren GREN_HEDEF (16x20'de sigma 1.6), 20x30 ve 24x30'da
#   (AZ_GREN) ayni posterin 24x36 kaynak greni (MB < 20). 24x36 DEGISMEZ (teslim_jpg yolu, gren eklenmez).
# Serdar 9 Eki: YONTEM B (2:3 olculer A ile ayni, degisiklik yok). B'de dikis kapisi (kapi_dikis) her ciktida.
# Kapi h: tum ogeler cerceve icinde, her yanda >= 300 px bosluk (7200 genislik olceginde), piksel tam.
import os, sys, json, numpy as np, cv2
from PIL import Image, JpegImagePlugin
Image.MAX_IMAGE_PIXELS = None
B = os.environ.get('MOTOR_KOK', '/home/claude/blender')
OLCU = {'8x10': (2400, 3000), '16x20': (4800, 6000), '24x30': (7200, 9000), '11x14': (3300, 4200),
        '12x16': (3600, 4800), '18x24': (5400, 7200), '12x18': (3600, 5400), '16x24': (4800, 7200), '20x30': (6000, 9000),
        '24x36': (7200, 10800), 'A4': (2480, 3508), 'A3': (3508, 4961), 'A2': (4961, 7016)}
AILE = {'8x10': '4:5', '16x20': '4:5', '24x30': '4:5', '11x14': '11:14', '12x16': '3:4', '18x24': '3:4',
        '12x18': '2:3', '16x24': '2:3', '20x30': '2:3', '24x36': '2:3', 'A4': 'A', 'A3': 'A', 'A2': 'A'}
W0, H0 = 7200, 10800
KUTU = [(200, 5600, 1400, 6800), (5800, 5600, 7000, 6800), (300, 300, 1500, 1500), (2400, 10000, 4800, 10600)]   # teslim_jpg ile ayni
BOSLUK = 300
SIGMA_HALKA, ESIK_HALKA = 8, 0.10        # 300 dpi piksel; esik: bilinen FAIL (Test 11 16x20, prova 12 olcu) / PASS (Test 10 24x36, gren 16x20)
GREN_HEDEF = 1.49                         # toplam zemin greni (HP sigma 1, kanal MAD ortancasi): 16x20'de Serdar onayli sigma 1.6'yi veren duzey
#   (= 24x36 onayli kaynagin HP std'si 1.49, ders 266 olcusu); her olcude ayni toplam gren, eklenen sigma olcuye gore hesaplanir
GREN_K = 0.8716                           # beyaz Gauss gurultunun HP(sigma 1) / sigma orani
AZ_GREN = {'20x30', '24x30'}              # Serdar 9 Eki aksam: bu iki olcude hedef = 24x36'nin kendi gren duzeyi (MB < 20)
GREN_HEDEF_AZ = 1.055                     # = Serdar'a gosterilen ve onaylanan olcum (24x36 q100 ana kopya, kutularda MAD ortancasi; 24x30 18.8 MB /
                                          #   halka 0.078). Kosu ici P'den olcmek (deneme 1) daha dusuk cikti (yuzer P, q100 gurultusu yok): 0.103 FAIL


def gren_olc(I, bg, kutular):
    """Zemin greni: kutularda (yalniz oge disi) HP = I - G1(I), kanal basina 1.4826*MAD, kutular ortancasi."""
    v = []
    for (x0, y0, x1, y1) in kutular:
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(I.shape[1], x1), min(I.shape[0], y1)
        if x1 - x0 < 120 or y1 - y0 < 120 or not bg[y0:y1, x0:x1].all(): continue
        K = I[y0:y1, x0:x1].astype(np.float32); Hh = K - cv2.GaussianBlur(K, (0, 0), 1.0)
        v.append(float(np.median([1.4826 * np.median(np.abs(Hh[..., c] - np.median(Hh[..., c]))) for c in range(3)])))
    return float(np.median(v)) if v else None


def halka_olc(dec, ideal, bg, kutular):
    """Halka: std(G8(cozulmus - ayni olcunun yuzer kaynagi)), kanal ortalamasi, oge disi kutularda; en kotu kutu."""
    v = {}; kk = 3 * SIGMA_HALKA
    for (x0, y0, x1, y1) in kutular:
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(dec.shape[1], x1), min(dec.shape[0], y1)
        if x1 - x0 < 120 or y1 - y0 < 120 or not bg[y0:y1, x0:x1].all(): continue
        E = (dec[y0:y1, x0:x1].astype(np.float32) - ideal[y0:y1, x0:x1]).mean(2)
        v[f'{x0},{y0}'] = round(float(cv2.GaussianBlur(E, (0, 0), SIGMA_HALKA)[kk:-kk, kk:-kk].std()), 4)
    return (max(v.values()) if v else None), v


def hc(olcu):
    w, h = OLCU[olcu]; return int(round(W0 * h / w))


def oge_maskesi(z, ekler=()):
    M = np.zeros((H0, W0), np.uint8)
    for (x, y), ad in zip(z['_konum'], z['_ad']):
        a = (z[str(ad)] > 0).astype(np.uint8); x, y = int(x), int(y); M[y:y + a.shape[0], x:x + a.shape[1]] |= a
    for (x, y, a) in ekler: M[y:y + a.shape[0], x:x + a.shape[1]] |= (a > 0).astype(np.uint8)
    return M


def _profil(Wc, Hc_, s, ox):
    """zemin_profil.json radyal profili (uret_tam ile ayni), kuculmus poster koordinatinda; sRGB 0-255."""
    sys.path.insert(0, B); from golge_motor import srgb
    Z = json.load(open(f'{B}/zemin_profil.json')); k = W0 / Z['olcek']
    rr = np.array(Z['r'], np.float32) * k; cx, cy, e = Z['cx'] * k, Z['cy'] * k, Z['e']
    LIN = [np.array(Z['lin'][c], np.float32) for c in range(3)]
    out = np.empty((Hc_, Wc, 3), np.float32); u = (np.arange(Wc, dtype=np.float32) - ox) / s
    for y0 in range(0, Hc_, 600):
        v = np.arange(y0, min(Hc_, y0 + 600), dtype=np.float32)[:, None] / s
        r = np.hypot(u[None] - cx, (v - cy) * e)
        out[y0:y0 + len(v)] = srgb(np.stack([np.interp(r, rr, LIN[c]) for c in range(3)], -1)) * 255
    return out


def donustur(P, M, olcu, yontem):
    """P: HxWx3 float (0-255), M: oge maskesi (uint8). -> (P2 hedef piksel, oge maskesi hedefte, bilgi)."""
    w, h = OLCU[olcu]; Hc_ = hc(olcu)
    ys, xs = np.nonzero(M); iy0, iy1, ix0, ix1 = ys.min(), ys.max(), xs.min(), xs.max()
    d1 = yontem == 'B1'                                                 # yalniz dikis kapisi dogrulamasi (deneme 1 kusuru)
    if yontem == 'A' or Hc_ >= H0:
        y0 = int(round((iy0 + iy1) / 2 - Hc_ / 2)); y0 = max(0, min(H0 - Hc_, y0))
        C, Mc = P[y0:y0 + Hc_], M[y0:y0 + Hc_]
        T = lambda x, y: (x, y - y0)                                   # ana -> 7200 olcekli tuval
        bilgi = dict(yontem='A' if yontem == 'A' else 'A (2:3, ayni)', pencere_y=[y0, y0 + Hc_])
    else:
        s = Hc_ / H0; Wp = int(round(W0 * s)); ox = (W0 - Wp) // 2
        Ps = cv2.resize(P, (Wp, Hc_), interpolation=cv2.INTER_AREA)
        C = _profil(W0, Hc_, s, ox)
        # yan seritler: ana goruntunun oge disi kenar bolgelerinden fazlalik (yildiz + doku), ayni s ile kucultulmus; ayna YOK
        D = cv2.dilate(M, np.ones((121, 121), np.uint8))
        bos = np.where(~D.any(0))[0]; sol = bos[bos < W0 // 2]; sag = bos[bos >= W0 // 2]
        def fazla(a, b):                                                                        # ana goruntu - profil, yalniz [a, b) sutunlari
            return P[:, a:b] - _profil(b - a, H0, 1.0, -float(a))
        kaynak = np.concatenate([fazla(int(sag.min()), W0), fazla(0, int(sol.max()) + 1)], 1)   # sag kenar + sol kenar (yan yana, ayna degil)
        kaynak_s = cv2.resize(kaynak, (max(1, int(round(kaynak.shape[1] * s))), Hc_), interpolation=cv2.INTER_AREA)
        F = 24                                                                                  # dikis yumusatma (poster kenari zemin)
        sw = W0 - ox - Wp
        if kaynak_s.shape[1] < max(ox, sw) + F: raise ValueError(f'serit kaynagi dar: {kaynak_s.shape[1]} < {max(ox, sw) + F}')
        k2 = np.roll(kaynak_s, Hc_ // 2, axis=0)                                                # sag serit: ayni kaynak, yarim boy kaydirma
        if d1:
            C[:, :ox] += kaynak_s[:, :ox]; C[:, ox + Wp:] += k2[:, -sw:]
        else:
            C[:, :ox + F] += kaynak_s[:, :ox + F]                                               # sol serit (+ yumusatma bolgesi)
            C[:, ox + Wp - F:] += k2[:, -(sw + F):]
        # dikis seviye eslemesi (9 Eki, deneme 2): serit ile poster kenari arasindaki dusuk frekans farki satir boyunca (sigma 150)
        # serite sabit ofset olarak eklenir (profil modeli kenarda ana goruntuden ~1-4 seviye sapiyor; deneme 1'de mavi kanalda cizgi)
        for xs_, xe_, sl in (() if d1 else ((ox, ox + F, np.s_[:, :ox + F]), (ox + Wp - F, ox + Wp, np.s_[:, ox + Wp - F:]))):
            d = (Ps[:, xs_ - ox:xe_ - ox] - C[:, xs_:xe_]).mean(1)
            d = cv2.GaussianBlur(d.reshape(-1, 1, 3).astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=150).reshape(-1, 3)
            C[sl] += d[:, None, :]
        a = np.ones(Wp, np.float32); a[:F] = np.linspace(0, 1, F + 2)[1:-1]; a[-F:] = a[:F][::-1]
        C[:, ox:ox + Wp] = Ps * a[None, :, None] + C[:, ox:ox + Wp] * (1 - a[None, :, None])
        Mc = np.zeros((Hc_, W0), np.uint8); Mc[:, ox:ox + Wp] = cv2.resize(M, (Wp, Hc_), interpolation=cv2.INTER_NEAREST)
        T = lambda x, y: (ox + x * s, y * s)
        bilgi = dict(yontem='B1' if d1 else 'B', olcek=round(s, 4), yan_serit_px=[ox, W0 - ox - Wp])
    C = np.clip(C, 0, 255)
    P2 = cv2.resize(C, (w, h), interpolation=cv2.INTER_AREA) if (C.shape[1], C.shape[0]) != (w, h) else C
    M2 = cv2.resize(Mc, (w, h), interpolation=cv2.INTER_NEAREST) if (Mc.shape[1], Mc.shape[0]) != (w, h) else Mc
    # kapi h: icerik kutusu 7200 olcekli tuvalde
    (ax0, ay0), (ax1, ay1) = T(ix0, iy0), T(ix1, iy1); Wc = W0
    pay = dict(sol=round(ax0), ust=round(ay0), sag=round(Wc - 1 - ax1), alt=round(Hc_ - 1 - ay1))
    bilgi.update(olcu=olcu, aile=AILE[olcu], hedef_px=[w, h], tuval_7200=[Wc, Hc_], bosluk_7200=pay,
                 h=dict(bosluk_min=min(pay.values()), icerik_tam=bool(min(pay.values()) >= 0), piksel_tam=list(P2.shape[1::-1]) == [w, h]))
    bilgi['h']['PASS'] = bool(bilgi['h']['bosluk_min'] >= BOSLUK and bilgi['h']['icerik_tam'] and bilgi['h']['piksel_tam'])
    kutular = []
    for (x0, y0_, x1, y1) in KUTU:
        (u0, v0), (u1, v1) = T(x0, y0_), T(x1, y1); f = w / Wc
        kutular.append(tuple(int(round(q * f)) for q in (u0, v0, u1, v1)))
    bilgi['_kutu'] = kutular
    bilgi['gren_24x36'] = gren_olc(P, M == 0, KUTU)                  # ayni posterin 24x36 (kucultmesiz) kaynak greni
    return P2.astype(np.float32), M2, bilgi


def yaz(P2, M2, bilgi, yol, cjpeg, q=97, seed=11):
    """Kucultulmus olcu: gren (Gauss, kanal basina, yalniz zemin; duzey GREN_HEDEF) + TPDF 0.5 yalniz zeminde, mozjpeg q97 4:4:4,
    JFIF 300 dpi. Ogeler (M2 > 0) kodlama oncesi AYNEN (gurultu zemin maskesiyle carpilir)."""
    sys.path.insert(0, B); import teslim_jpg
    H, W = P2.shape[:2]; bg = M2 == 0
    g0 = gren_olc(P2, bg, bilgi['_kutu'])
    hedef = GREN_HEDEF_AZ if bilgi['olcu'] in AZ_GREN else GREN_HEDEF
    sn = float(np.sqrt(max(0.0, hedef ** 2 - g0 ** 2)) / GREN_K) if g0 is not None else 0.0
    U = np.empty(P2.shape, np.uint8)
    for y0 in range(0, H, 1200):
        r = np.random.default_rng([seed, y0]); s = P2[y0:y0 + 1200]
        n = (r.random(s.shape, dtype=np.float32) - r.random(s.shape, dtype=np.float32)) * 0.5
        if sn > 0: n += r.standard_normal(s.shape, dtype=np.float32) * sn
        U[y0:y0 + 1200] = np.clip(np.round(s + n * bg[y0:y0 + 1200, :, None]), 0, 255).astype(np.uint8)
    g1 = gren_olc(U, bg, bilgi['_kutu'])
    ppm = yol + '.ppm'; Image.fromarray(U).save(ppm); del U
    import subprocess
    subprocess.run([cjpeg, '-quality', str(q), '-sample', '1x1', '-optimize', '-progressive', '-outfile', yol, ppm], check=True)
    os.remove(ppm); teslim_jpg.dpi_yaz(yol)
    g = kapi_g(yol, P2, bg, bilgi)
    g['gren'] = dict(kaynak=round(g0, 3) if g0 is not None else None, sigma=round(sn, 3), kodlama_oncesi=round(g1, 3) if g1 is not None else None,
                     hedef=round(hedef, 3))
    return g


def kapi_g(yol, P2, bg, bilgi):
    it = Image.open(yol); w, h = bilgi['hedef_px']
    dec = np.asarray(it.convert('RGB'))
    hk, v = halka_olc(dec, P2, bg, bilgi['_kutu'])
    g = dict(dosya=os.path.basename(yol), bayt=os.path.getsize(yol), mb=round(os.path.getsize(yol) / 1e6, 2), boyut=list(it.size),
             ornekleme_444=JpegImagePlugin.get_sampling(it) == 0, dpi=[round(float(q)) for q in it.info.get('dpi', (0, 0))], halka=hk, halka_kutular=v,
             halka_sigma=SIGMA_HALKA, halka_esik=ESIK_HALKA)
    g['PASS'] = bool(g['bayt'] < 20_000_000 and g['boyut'] == [w, h] and g['ornekleme_444'] and g['dpi'] == [300, 300]
                     and hk is not None and hk <= ESIK_HALKA)
    return g


def kapi_dikis(Y, M2, bilgi):
    """B dikis kapisi (9 Eki, Serdar; kapi e mantigi): eklenen yan serit ile poster birlesim cizgisinde sutun ortalamasi profili
    (oge olmayan satirlar). Cizgi cevresi (cekirdek) disaridaki dogrusal egilimden ne kadar sapiyor; ayni olcu poster ici ve serit
    ici referans pencerelerinde. PASS: sapma <= 1.5 * referans + 0.6 (her kanal, her iki dikis)."""
    if not bilgi['yontem'].startswith('B'):
        return dict(uygulanmaz=True, PASS=True)
    w = bilgi['hedef_px'][0]; f = w / W0; ox, sw = bilgi['yan_serit_px']
    hw = max(16, int(round(90 * f))); core = max(6, int(round(30 * f)))
    def sapma(xc):
        x0, x1 = int(round(xc)) - hw, int(round(xc)) + hw
        if x0 < 0 or x1 > w: return None
        satir = ~M2[:, x0:x1].astype(bool).any(1)
        pr = Y[satir, x0:x1].mean(0)                                     # (2hw, 3)
        i = np.arange(2 * hw); dis = (i < hw - core) | (i >= hw + core)
        en = 0.0
        for c in range(3):
            k = np.polyfit(i[dis], pr[dis, c], 1); en = max(en, float(np.abs(pr[~dis, c] - np.polyval(k, i[~dis])).max()))
        return en
    R = {}
    for ad, xc in (('sol', ox * f), ('sag', (W0 - sw) * f)):
        d = sapma(xc); ref = [v for v in (sapma(xc - 3 * hw), sapma(xc + 3 * hw)) if v is not None]
        rf = max(ref) if ref else 0.0
        R[ad] = dict(sapma=round(d, 3), referans=round(rf, 3), PASS=bool(d <= 1.5 * rf + 0.6))
    R['PASS'] = all(v['PASS'] for v in R.values() if isinstance(v, dict))
    return R
