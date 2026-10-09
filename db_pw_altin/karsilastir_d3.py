# d3 (Serdar 9 Eki aksam): onayli d2 16x20 | yeni d3 16x20 karsilastirmasi. Yalniz DB/PW 16x20.
# Kullanim: python karsilastir_d3.py D2_KLASOR IS CIKTI SONUC
#   D2_KLASOR: d2 16x20 teslim dosyalari (AstroLoveArt_<B1>_<B2>_<Renk>_16x20.jpg), IS: db_pw_uret ciktisi (d3),
#   CIKTI: Drive'a giden klasor, SONUC: dala yazilan ozet. Cikis 1: DB bant > 0.5 seviye ya da dosya eksik.
# Olculer: (1) yan serit bandi = satir basina ortalama(teslim - temiz 16x20 plaka) [serit sutunlari, dikis yumusatma bolgesi haric],
#          en buyuk |deger| (hedef <= 0.5 seviye); (2) d3 - d2 piksel farki (adet, en buyuk, kutu, serit/poster ayrimi).
import sys, os, json, subprocess, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
D2, IS, O, S = sys.argv[1:5]; os.makedirs(O, exist_ok=True); os.makedirs(S, exist_ok=True)
K = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
s = json.load(open(f'{IS}/siparis.json')); b1, b2 = (w.capitalize() for w in s['cift'].split('_'))
W0, H0 = 7200, 10800; Hc = 9000; ox7 = (W0 - int(round(W0 * Hc / H0))) // 2; F7 = 24      # olcu.donustur ile ayni (16x20)
sonuc = {}; hata = False
for r, pl in (('DEEP_BLACK', 'BLACK'), ('PURE_WHITE', 'PURE_WHITE')):
    rn = '_'.join(w.capitalize() for w in r.split('_')); ad = f'AstroLoveArt_{b1}_{b2}_{rn}_16x20.jpg'
    y2, y3 = f'{D2}/{ad}', f'{IS}/{r}/{ad}'
    if not (os.path.exists(y2) and os.path.exists(y3)): sonuc[r] = dict(hata='dosya yok', d2=os.path.exists(y2), d3=os.path.exists(y3)); hata = True; continue
    A2 = np.asarray(Image.open(y2).convert('RGB')).astype(np.float32); A3 = np.asarray(Image.open(y3).convert('RGB')).astype(np.float32)
    P = np.asarray(Image.open(f'{IS}/plaka/{pl}_16x20_temiz.png').convert('RGB')).astype(np.float32)
    h, w = A3.shape[:2]; f = w / W0; ox, F = int(round(ox7 * f)), int(round(F7 * f))
    serit = {'sol': np.s_[:, :ox - F], 'sag': np.s_[:, w - ox + F:]}
    def bant(A):
        out = {}
        for k, sl in serit.items():
            d = (A[sl] - P[sl]).mean((1, 2)); out[k] = dict(max_abs=round(float(np.abs(d).max()), 3), satir_05_ustu=int((np.abs(d) > 0.5).sum()),
                                                             satir_1_ustu=int((np.abs(d) > 1).sum()), ort=round(float(d.mean()), 3))
        return out
    D = np.abs(A3 - A2).max(2); ys, xs = np.nonzero(D > 0)
    ser = np.zeros((h, w), bool); ser[:, :ox] = True; ser[:, w - ox:] = True
    fark = dict(px=int(len(ys)), max=float(D.max()), kutu=None if not len(ys) else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                seritte_px=int((D[ser] > 0).sum()), poster_icinde_px=int((D[~ser] > 0).sum()),
                poster_icinde_max=float(D[~ser].max()), ort_mutlak=round(float(D.mean()), 4))
    sonuc[r] = dict(boyut=[w, h], serit_px=[ox - F, F], bant_d2=bant(A2), bant_d3=bant(A3), fark_d3_d2=fark)
    if r == 'DEEP_BLACK' and max(v['max_abs'] for v in sonuc[r]['bant_d3'].values()) > 0.5: hata = True
    # yan yana (d2 solda | d3 sagda), tam cozunurluk
    subprocess.run([PY, f'{K}/yanyana.py', y2, y3, f'{O}/YANYANA_{rn}_16x20_D2_D3.jpg', f'{S}/ONIZLEME_{rn}_16x20_D2_D3.jpg', 'D2', 'D3'], check=True)
    # sol serit 1:1 kesit (x 0..2*ox, tam yukseklik): d2 | d3 ; ayrica x8 kontrast (zemine gore fark x8) ayni yerden
    gx = 2 * ox; ara = 20
    for ek, fn in (('1x1', lambda a: a), ('x8', (lambda a: np.clip(a * 8, 0, 255)) if r == 'DEEP_BLACK' else (lambda a: np.clip(255 - (255 - a) * 8, 0, 255)))):
        T = np.full((h, 2 * gx + ara, 3), 128, np.float32); T[:, :gx] = fn(A2[:, :gx]); T[:, gx + ara:] = fn(A3[:, :gx])
        Image.fromarray(T.astype(np.uint8)).save(f'{O}/KESIT_SOL_SERIT_{rn}_16x20_D2_D3_{ek}.jpg', quality=95, subsampling=0)
    Image.fromarray(np.clip(T, 0, 255).astype(np.uint8)).resize(((2 * gx + ara) // 4, h // 4)).save(f'{S}/KESIT_SOL_SERIT_{rn}_x8_kucuk.jpg', quality=88)
json.dump(sonuc, open(f'{S}/KARSILASTIR_D3.json', 'w'), indent=1); json.dump(sonuc, open(f'{O}/KARSILASTIR_D3.json', 'w'), indent=1)
print(json.dumps(sonuc))
sys.exit(1 if hata else 0)
