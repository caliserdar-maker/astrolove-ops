# Ikinci tur kesik (8 Eki 2026, ders 191-194): ham ChatGPT altini (payli esleme) ile son katman karsilastirilir.
# Kaynaga DEGEN ChatGPT parcasindan katmanda atilmis altin, son katmanin altinina bitisikse (temas cizgisi >= MIN_TEMAS px) KESIK.
# Hem kutu kesigini (tur 1) hem eski "kaynak + 30 px" yakinlik kesigini yakalar. Poster siniri disi sayilmaz.
# Kullanim: python kesik_tur2.py [CIFT,CIFT,...] [--katman KLASOR] -> kesik_tur2/SONUC.json (+ ilerleme), log satiri sayacli
import os, sys, csv, json, time, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender'
_s = open(f'{B}/kesik_tara.py').read(); _argv = sys.argv; sys.argv = ['x', '__yok__']
exec(_s[:_s.index('cs = [r')]); sys.argv = _argv
MIN_TEMAS = 8
KAT = sys.argv[sys.argv.index('--katman') + 1] if '--katman' in sys.argv else f'{B}/katman78'
OD = f'{B}/kesik_tur2'; os.makedirs(OD, exist_ok=True)
def tur2(c, katman_dir=KAT):
    z, K, H, W, Ap, Gp, gpt_kenar, gyol = esle(c)
    ka = np.asarray(Image.open(f'{katman_dir}/{c}_ana.png'))[..., 3]; kj = json.load(open(f'{katman_dir}/{c}_ana.png.json'))
    X0_, Y0_ = K['ana']; ox, oy = kj['x'] - X0_ + P2, kj['y'] - Y0_ + P2           # katmanin payli haritadaki kosesi
    Fm = np.zeros(Ap.shape, bool); Hk, Wk = ka.shape
    ya, xa = max(0, oy), max(0, ox); yb, xb = min(Ap.shape[0], oy + Hk), min(Ap.shape[1], ox + Wk)
    Fm[ya:yb, xa:xb] = ka[ya - oy:yb - oy, xa - ox:xb - ox] > 127
    S = np.zeros(Ap.shape, np.uint8); S[P2:P2 + H, P2:P2 + W] = z['ana'] > 127
    yak = cv2.dilate(S, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))) > 0
    am = Ap > 0.5
    n, lb, st, _ = cv2.connectedComponentsWithStats(am.astype(np.uint8), 8)
    degen = np.unique(lb[yak & (lb > 0)]); degen = degen[degen > 0]
    parca = np.isin(lb, degen)
    # poster siniri: payli harita koordinati -> poster (x = X0_ - P2 + u)
    yy0, xx0 = Y0_ - P2, X0_ - P2
    ic = np.zeros(Ap.shape, bool); ic[max(0, -yy0):min(Ap.shape[0], 10800 - yy0), max(0, -xx0):min(Ap.shape[1], 7200 - xx0)] = True
    atilan = parca & ~Fm & ic
    temas = atilan & (cv2.dilate(Fm.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    nt, lt, stt, cen = cv2.connectedComponentsWithStats(temas.astype(np.uint8), 8)
    na, la, sta, _ = cv2.connectedComponentsWithStats(atilan.astype(np.uint8), 8)
    yerler = []
    for i in range(1, nt):
        L = int(stt[i, cv2.CC_STAT_AREA])
        if L < MIN_TEMAS: continue
        cx, cy = cen[i]; ids = np.unique(la[lt == i]); alan = int(sta[ids[ids > 0], cv2.CC_STAT_AREA].sum())
        yerler.append(dict(poster_x=int(cx + xx0), poster_y=int(cy + yy0), temas_px=L, atilan_altin_px=alan))
    return dict(kesik=len(yerler), yerler=sorted(yerler, key=lambda q: -q['atilan_altin_px']), payli='kaynak_x' in kj, gpt_resim_kenari_px=gpt_kenar)
if __name__ == '__main__':
    cs = [r['cift'] for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv'))]
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'): cs = sys.argv[1].split(',')
    IL = f'{OD}/ilerleme.json'; il = json.load(open(IL)) if os.path.exists(IL) else {}
    T0 = time.time(); n0 = sum(1 for c in cs if c in il)
    for c in cs:
        if c in il: continue
        try: il[c] = tur2(c)
        except Exception as e: il[c] = dict(hata=repr(e)[:300])
        json.dump(il, open(IL, 'w'), indent=1)
        k = sum(1 for x in cs if x in il); g = time.time() - T0
        print(f'[{k}/{len(cs)}] {c} kesik={il[c].get("kesik")} | gecen {g/60:.1f} dk | kalan ~{g/max(k-n0,1)*(len(cs)-k)/60:.1f} dk | %{100*k//len(cs)}', flush=True)
    json.dump({c: il[c] for c in cs}, open(f'{OD}/SONUC.json', 'w'), indent=1)
