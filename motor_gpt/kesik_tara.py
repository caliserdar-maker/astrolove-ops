# 78 ana sembol kesik uc taramasi (8 Eki 2026). Ilerleme: kesik_tara/ilerleme.json, sonuc kesik_tara/SONUC.json + kesitler.
# Oge basina asamalar: kaynak alfa (motor, ana kutusu) | ChatGPT ciktisi PAYLI eslenmis (kutu disi dahil) | katman alfa | poster.
# Kesik: katman alfasi kutu kenarina duz kesikle degiyor (kesik_uc.kesikler). Asama:
#   - birlestirme (kutu kirpmasi): ayni yerde ChatGPT altini kutu DISINA tasiyor (payli eslemede kutu disi altin > 0)
#   - kaynak: kaynak alfa ayni kenarda ayni yerde de duz kesik
#   - ChatGPT: ne kutu disi altin ne kaynak kesigi var (ChatGPT ucu kendisi duz cizmis)
import os, sys, csv, glob, json, time, numpy as np, cv2
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender'; sys.path.insert(0, B)
from kesik_uc import kesikler, kenar_temas
O = f'{B}/kesik_tara'; os.makedirs(f'{O}/kesit', exist_ok=True)
src = open(f'{B}/katman_cikar.py').read(); exec(src[src.index('GS ='):src.index('cs = [')].replace("O = f'{B}/katman78'", "_ = 0"))
src2 = open(f'{B}/gpt_birlestir2.py').read(); exec(src2[src2.index('def altinlik'):src2.index('z = dict(np.load')])
PAY = 150; P2 = 300                                                  # eslemede kutu disi pay (kutu disi altini gormek icin)
def esle(c):
    g, t, kd = kaynak(c)
    z = np.load(f'{B}/{kd}/{c}_alfa.npz'); K = {str(a): (int(x), int(y)) for (x, y), a in zip(z['_konum'], z['_ad'])}
    H, W = z['ana'].shape
    G0 = np.asarray(Image.open(g).convert('RGB')); Ti = np.asarray(Image.open(t).convert('RGB'))
    s = Ti.shape[1] / (W + 2 * PAY)
    ag = altinlik(G0); at = altinlik(Ti); mg = ag > 0.5; mt = at > 0.5
    ys, xs = np.nonzero(mg); yt, xt = np.nonzero(mt)
    sx = (xt.max() - xt.min()) / (xs.max() - xs.min()); sy = (yt.max() - yt.min()) / (ys.max() - ys.min())
    M1 = np.array([[sx, 0, xt.min() - xs.min() * sx], [0, sy, yt.min() - ys.min() * sy], [0, 0, 1]])
    w = cv2.warpAffine(ag, M1[:2].astype(np.float32), (Ti.shape[1], Ti.shape[0]))
    wm = np.eye(2, 3, dtype=np.float32)
    _, wm = cv2.findTransformECC(cv2.GaussianBlur(at, (0, 0), 2), cv2.GaussianBlur(w, (0, 0), 2), wm, cv2.MOTION_AFFINE,
                                 (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
    E = np.vstack([wm, [0, 0, 1]]).astype(np.float64)
    M = np.array([[1 / s, 0, -PAY + P2], [0, 1 / s, -PAY + P2], [0, 0, 1]]) @ np.linalg.inv(E) @ M1   # ChatGPT -> PAYLI kutu
    F = float(np.sqrt(abs(np.linalg.det(M[:2, :2]))))
    aw = cv2.warpAffine(cv2.GaussianBlur(ag, (0, 0), 1.0), M[:2].astype(np.float32), (W + 2 * P2, H + 2 * P2), flags=cv2.INTER_CUBIC)
    Ap = np.clip((aw - 0.5) * F / 2.0 + 0.5, 0, 1)
    Gp = cv2.warpAffine(G0, M[:2].astype(np.float32), (W + 2 * P2, H + 2 * P2), flags=cv2.INTER_CUBIC)
    gpt_kenar = int((mg[:3].sum() + mg[-3:].sum() + mg[:, :3].sum() + mg[:, -3:].sum()))   # ChatGPT altini kendi resim kenarinda
    return z, K, H, W, Ap, Gp, gpt_kenar, g
cs = [r['cift'] for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv'))]
if len(sys.argv) > 1: cs = sys.argv[1].split(',')
IL = f'{O}/ilerleme.json'; il = json.load(open(IL)) if os.path.exists(IL) and len(sys.argv) == 1 else {}
T0 = time.time(); n0 = len(il)
for i, c in enumerate(cs, 1):
    if c in il: continue
    try:
        z, K, H, W, Ap, Gp, gpt_kenar, gyol = esle(c)
        ka = np.asarray(Image.open(f'{B}/katman78/{c}_ana.png'))[..., 3]; kj = json.load(open(f'{B}/katman78/{c}_ana.png.json'))
        sa = z['ana']
        X0_, Y0_ = K['ana']; ox_, oy_ = kj['x'] - X0_, kj['y'] - Y0_       # katman kutusu kaynak kutusuna gore (payli: -150)
        Hk, Wk = ka.shape
        kk = [q for q in kesikler(ka) if not ((q['kenar'] == 'ust' and kj['y'] == 0) or (q['kenar'] == 'sol' and kj['x'] == 0)
                                              or (q['kenar'] == 'alt' and kj['y'] + Hk >= 10800) or (q['kenar'] == 'sag' and kj['x'] + Wk >= 7200))]
        for q in kk: q['x'] += ox_; q['y'] += oy_                        # kaynak kutusu koordinatina
        ks = kesikler(sa)
        # ikinci olcu (sekilden bagimsiz): katman kenarda altin VE hemen disinda (2 px) ChatGPT altini -> kutu kesigi
        from kesik_uc import _kosular
        Am = Ap > 0.5
        bx, by = P2 + ox_, P2 + oy_                                      # katman kutusunun payli haritadaki kosesi
        def am_(y, x0, x1): return Am[y, x0:x1] if 0 <= y < Am.shape[0] else np.zeros(x1 - x0, bool)
        def amc(x, y0, y1): return Am[y0:y1, x] if 0 <= x < Am.shape[1] else np.zeros(y1 - y0, bool)
        hatlar = {'ust': (ka[0] > 127, am_(by - 2, bx, bx + Wk)) if kj['y'] > 0 else (np.zeros(Wk, bool),) * 2,
                  'alt': (ka[-1] > 127, am_(by + Hk + 1, bx, bx + Wk)) if kj['y'] + Hk < 10800 else (np.zeros(Wk, bool),) * 2,
                  'sol': (ka[:, 0] > 127, amc(bx - 2, by, by + Hk)) if kj['x'] > 0 else (np.zeros(Hk, bool),) * 2,
                  'sag': (ka[:, -1] > 127, amc(bx + Wk + 1, by, by + Hk)) if kj['x'] + Wk < 7200 else (np.zeros(Hk, bool),) * 2}
        for ad_, (ic_, dis_) in hatlar.items():
            for a0, a1 in _kosular(ic_ & dis_):
                if a1 - a0 + 1 < 3: continue
                orta = (a0 + a1) // 2; xy = {'ust': (orta, 0), 'alt': (orta, Hk - 1), 'sol': (0, orta), 'sag': (Wk - 1, orta)}[ad_]
                xy = (xy[0] + ox_, xy[1] + oy_)
                if not any(q['kenar'] == ad_ and abs(q['x'] - xy[0]) + abs(q['y'] - xy[1]) < 80 for q in kk):
                    kk.append(dict(kenar=ad_, x=int(xy[0]), y=int(xy[1]), w0=int(a1 - a0 + 1), wD=None, oran=None, olcu='kutu_disi_temas'))
        dis = (Ap > 0.5).copy(); dis[max(0, P2 + oy_):P2 + oy_ + Hk, max(0, P2 + ox_):P2 + ox_ + Wk] = False   # KATMAN kutusu disi ChatGPT altini
        kayit = []
        X0, Y0 = K['ana']
        P = None
        for j, k in enumerate(kk):
            x, y = k['x'] + P2, k['y'] + P2
            r = 60; yak = dis[max(0, y - r):y + r, max(0, x - r):x + r]
            kutu_disi = int(yak.sum())
            kay = any(q['kenar'] == k['kenar'] and abs(q['x'] - k['x']) + abs(q['y'] - k['y']) < 80 for q in ks)
            asama = 'birlestirme (kutu kirpmasi)' if kutu_disi > 0 else ('kaynak' if kay else 'ChatGPT')
            k.update(kutu_disi_altin_px=kutu_disi, kaynakta_da_kesik=kay, asama=asama, poster_x=X0 + k['x'], poster_y=Y0 + k['y'])
            kayit.append(k)
            # kesit: kaynak alfa | ChatGPT payli (olmasi gereken) | katman | poster ; 400x400 tam cozunurluk
            if P is None: P = Image.open(f'{B}/renkli78/{c}/{c}_7200x10800.jpg')
            R = 200; px, py = k['x'], k['y']
            def kes(arr, cx, cy, ofs=0):
                h, w = arr.shape[:2]; out = np.full((2 * R, 2 * R, 3), (60, 0, 0), np.uint8)
                x0, y0 = cx - R + ofs, cy - R + ofs; xa, ya = max(0, x0), max(0, y0); xb, yb = min(w, x0 + 2 * R), min(h, y0 + 2 * R)
                v = arr[ya:yb, xa:xb]; v = np.dstack([v] * 3) if v.ndim == 2 else v
                out[ya - y0:yb - y0, xa - x0:xb - x0] = v; return Image.fromarray(out)
            parc = [kes(sa, px, py), kes((Gp * (Ap[..., None] > 0.5)).astype(np.uint8), px, py, P2), kes(ka, px - ox_, py - oy_),
                    P.crop((X0 + px - R, Y0 + py - R, X0 + px + R, Y0 + py + R))]
            S = Image.new('RGB', (4 * 2 * R + 3 * 20, 2 * R + 50), 'white'); d = ImageDraw.Draw(S)
            for q, (im, et) in enumerate(zip(parc, ('kaynak alfa', 'ChatGPT (kutu disi dahil)', 'katman alfa', 'poster'))):
                S.paste(im, (q * (2 * R + 20), 50)); d.text((q * (2 * R + 20) + 5, 15), et, fill='black')
            S.save(f'{O}/kesit/{c}_{j + 1}_{k["kenar"]}.png')
        il[c] = dict(katman_kutu=[kj['x'], kj['y'], Wk, Hk], kesik=len(kayit), yerler=kayit, gpt_resim_kenari_altin_px=gpt_kenar, kaynak_kesik=ks, katman_kenar=kenar_temas(ka), gpt=os.path.basename(gyol))
    except Exception as e:
        il[c] = dict(hata=repr(e)[:300])
    json.dump(il, open(IL, 'w'), indent=1)
    k_ = len(il); g_ = time.time() - T0
    print(f'[{k_}/{len(cs)}] {c} kesik={il[c].get("kesik")} | gecen {g_/60:.1f} dk | kalan ~{g_/max(k_-n0,1)*(len(cs)-k_)/60:.1f} dk | %{100*k_//len(cs)}', flush=True)
json.dump(il, open(f'{O}/SONUC.json', 'w'), indent=1)
