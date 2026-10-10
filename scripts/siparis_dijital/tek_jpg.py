#!/usr/bin/env python3
"""TEK JPG (Serdar 10 Eki, adim 4): Champagne Ivory ve Warm Parchment siparisinde PDF yerine tek teslim JPG.

Yontem (durum dosyasi plan a): eski yol tasarimi AYNEN. Siparisin AILE oranindaki tek sayfa (CI: sayfa_asamasi,
WP: wp_asamasi; ayni kod, ayni kapilar) uretilir; sayfa siparis olcusune getirilir. Aile sayfasi ile siparis olcusu ayni
en-boy oraninda (BOY tablosu), bu yuzden yan serit gerekmez: yalniz yeniden orneklenir (24x30 tek buyutme: 16x20 sayfasindan
x1.5). Kucultmeden sonra kagit greni kaynak sayfanin greni duzeyine getirilir (yalniz murekkep disi; MB ders 265-270 ile
ayni ilke), mozjpeg q97 4:4:4, JFIF 300 dpi.

Kapilar (g): boyut = hedef px, < 20 MB, 4:4:4, 300 dpi, halka sigma 8 <= 0.10 (cozulmus - ayni olcunun yuzer kaynagi,
murekkep disi kutularda). Sayfa kapilari aile sayfasinin kendi OZET'inden gelir.

Kullanim: tek_jpg.py SAYFA.jpg OLCU CIKTI.jpg --cjpeg BIN [--json KAPI.json]
"""
import json, os, subprocess, sys, tempfile
import numpy as np, cv2
from PIL import Image, JpegImagePlugin

Image.MAX_IMAGE_PIXELS = None
DPI = 300
# 13 siparis olcusu -> (aile sayfa boyu, genislik inc, yukseklik inc). Aile sayfalari: siparis_dosyasi.DIJITAL_BOY.
OLCU = {'8x10': ('16x20', 8, 10), '16x20': ('16x20', 16, 20), '24x30': ('16x20', 24, 30),
        '11x14': ('11x14', 11, 14),
        '12x16': ('18x24', 12, 16), '18x24': ('18x24', 18, 24),
        '12x18': ('24x36', 12, 18), '16x24': ('24x36', 16, 24), '20x30': ('24x36', 20, 30), '24x36': ('24x36', 24, 36),
        'A4': ('A2', 8.268, 11.693), 'A3': ('A2', 11.693, 16.535), 'A2': ('A2', 16.535, 23.386)}
MB_SINIR = 20.0
SIGMA_HALKA, ESIK_HALKA = 8, 0.10
Q = 97
KAGIT_MIN = 0.6     # kutunun en az bu kadari kagit (murekkep disi) ise olculur


def hedef_px(olcu):
    _, w, h = OLCU[olcu]
    return int(round(w * DPI)), int(round(h * DPI))


def murekkep_disi(P):
    """Kagit maskesi: yerel kagittan (G25) belirgin koyu olmayan pikseller, 6 px genisletilmis murekkep disi."""
    L = cv2.cvtColor((P / 255).astype(np.float32), cv2.COLOR_RGB2Lab)[..., 0]
    ink = (cv2.GaussianBlur(L, (0, 0), 25) - L) > 6
    ink = cv2.dilate(ink.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    return ~ink


def kutular(w, h, n=6):
    """Esit aralikli olcum kutulari (sayfanin ic %80'i)."""
    s = int(min(w, h) * 0.12); xs = np.linspace(w * 0.1, w * 0.9 - s, n).astype(int); ys = np.linspace(h * 0.1, h * 0.9 - s, n).astype(int)
    return [(int(x), int(y), int(x) + s, int(y) + s) for x in xs for y in ys]


def gren_olc(I, bg, kk):
    v = []
    for (x0, y0, x1, y1) in kk:
        m = bg[y0:y1, x0:x1]
        if m.mean() < KAGIT_MIN:
            continue
        K = I[y0:y1, x0:x1].astype(np.float32); Hh = K - cv2.GaussianBlur(K, (0, 0), 1.0)
        v.append(float(np.median([1.4826 * np.median(np.abs(Hh[..., c][m] - np.median(Hh[..., c][m]))) for c in range(3)])))
    return float(np.median(v)) if v else None


def halka_olc(dec, ideal, bg, kk):
    v = {}; k3 = 3 * SIGMA_HALKA
    for (x0, y0, x1, y1) in kk:
        m = bg[y0:y1, x0:x1]
        if m.mean() < KAGIT_MIN:
            continue
        E = (dec[y0:y1, x0:x1].astype(np.float32) - ideal[y0:y1, x0:x1]).mean(2) * m   # murekkep pikseli olcume girmez
        v[f'{x0},{y0}'] = round(float(cv2.GaussianBlur(E, (0, 0), SIGMA_HALKA)[k3:-k3, k3:-k3].std()), 4)
    return (max(v.values()) if v else None), v


def dpi_yaz(yol, dpi=DPI):
    b = bytearray(open(yol, 'rb').read())
    assert b[0:2] == b'\xff\xd8' and b[2:4] == b'\xff\xe0' and b[6:11] == b'JFIF\x00', 'JFIF APP0 yok'
    b[13] = 1; b[14:16] = dpi.to_bytes(2, 'big'); b[16:18] = dpi.to_bytes(2, 'big')
    open(yol, 'wb').write(bytes(b))


def uret(sayfa, olcu, cikti, cjpeg, seed=11):
    S = np.asarray(Image.open(sayfa).convert('RGB')).astype(np.float32)
    W, H = hedef_px(olcu)
    oran_s, oran_h = S.shape[1] / S.shape[0], W / H
    if abs(oran_s - oran_h) / oran_h > 0.004:
        raise SystemExit(f'HATA en-boy farkli: sayfa {S.shape[1]}x{S.shape[0]} hedef {W}x{H}')
    kucult = W <= S.shape[1]
    P = cv2.resize(S, (W, H), interpolation=cv2.INTER_AREA if kucult else cv2.INTER_CUBIC)
    P = np.clip(P, 0, 255)
    bg_s, bg = murekkep_disi(S), murekkep_disi(P)
    g_kay, g_once = gren_olc(S, bg_s, kutular(S.shape[1], S.shape[0])), gren_olc(P, bg, kutular(W, H))
    ek = 0.0
    if g_kay and g_once and g_kay > g_once:
        ek = float(np.sqrt(g_kay ** 2 - g_once ** 2))
        rs = np.random.default_rng(seed)
        bgf = cv2.GaussianBlur(bg.astype(np.float32), (0, 0), 2)[..., None]
        P = np.clip(P + rs.normal(0, ek, P.shape).astype(np.float32) * bgf, 0, 255)
    Y8 = np.round(P).astype(np.uint8)
    with tempfile.TemporaryDirectory() as td:
        ppm = os.path.join(td, 'g.ppm'); Image.fromarray(Y8).save(ppm)
        subprocess.run([cjpeg, '-quality', str(Q), '-sample', '1x1', '-optimize', '-progressive', '-outfile', cikti, ppm], check=True)
    dpi_yaz(cikti)
    return P, bg, dict(sayfa_px=[S.shape[1], S.shape[0]], hedef_px=[W, H], kucultme=kucult,
                      gren=dict(kaynak=round(g_kay or 0, 3), once=round(g_once or 0, 3), ek_sigma=round(ek, 3)))


def kapi_g(cikti, olcu, P, bg):
    W, H = hedef_px(olcu)
    im = Image.open(cikti)
    dec = np.asarray(im.convert('RGB'))
    hal, kut = halka_olc(dec, P, bg, kutular(W, H))
    mb = os.path.getsize(cikti) / 1e6
    r = dict(boyut=list(im.size), hedef=[W, H], mb=round(mb, 2), ornekleme_444=JpegImagePlugin.get_sampling(im) == 0,
             dpi=[round(float(x)) for x in im.info.get('dpi', (0, 0))], halka=hal, halka_kutular=kut, halka_esik=ESIK_HALKA)
    r['PASS'] = bool(r['boyut'] == [W, H] and mb < MB_SINIR and r['ornekleme_444'] and r['dpi'] == [DPI, DPI]
                     and hal is not None and hal <= ESIK_HALKA)
    return r


if __name__ == '__main__':
    a = sys.argv[1:]
    cj = a[a.index('--cjpeg') + 1]
    js = a[a.index('--json') + 1] if '--json' in a else None
    sayfa, olcu, cikti = [x for x in a if not x.startswith('--') and x not in (cj, js)][:3]
    P, bg, bilgi = uret(sayfa, olcu, cikti, cj)
    g = kapi_g(cikti, olcu, P, bg)
    out = dict(olcu=olcu, aile=OLCU[olcu][0], **bilgi, g=g, PASS=g['PASS'])
    print('TEK_JPG', olcu, json.dumps({k: out[k] for k in ('aile', 'hedef_px', 'gren', 'PASS')}), 'MB', g['mb'], 'halka', g['halka'], flush=True)
    if js:
        json.dump(out, open(js, 'w'), indent=1)
    sys.exit(0 if out['PASS'] else 1)
