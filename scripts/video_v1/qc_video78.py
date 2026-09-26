#!/usr/bin/env python3
"""78 ilan videosu tam kalite denetimi (video GOREV 0012, 26 Eyl 2026). SALT OKUMA: Etsy'ye erisim yok.

Kaynak kart = onayli uretim kodunun (video_cift.py) beklenen kareleri: ayni referans maket (ref kare 150), ayni afin/ton/aydinlatma,
ayni AM tagline duzeltmesi ve altin esitlemesi, ayni zamanlama plani. Her video karesi bu beklenen kareyle karsilastirilir.
Esikler Cancer-Libra v5 videosundan olculur: CL'nin E durumu referans kare 150'nin AYNISI oldugundan CL E sabit kareleri - kare 150
farki = saf sikistirma gurultusu.
Kontroller (cift basina): teknik (sure, cozunurluk, fps, codec, piksel, boyut <= 100 MB, ses yok, kare sayisi);
cift dogrulugu (sembol bandi farki); OCR (poster tam cozunurluk + video karesi 3x buyutme: isimler, slogan);
renk (duvar ve poster zemini, CL'ye dE76); iz/leke (medyan suzulmus fark lekesi), Sobel kenar orani, siyah kare, donma, yirtilma.
Kullanim: qc_video78.py --a1 A1_DIR --cl CL_v5.mp4 --ref REF_DIR --out OUT [--ciftler A,B]"""
import argparse, csv, json, os, re, subprocess, sys, time
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy import ndimage

FF = os.environ.get('FFMPEG', 'ffmpeg')
W_, H_ = 1080, 1350
FPS, BAS, GECIS, SABIT, TUR, SIRA = 30, 4, 12, 30, 3, ['EJ', 'IN', 'AM']
X0, Y0, X1, Y1 = 151, 171, 927, 1177                       # poster acikligi (video_cift.py)
AP = (slice(Y0 + 3, Y1 - 3), slice(X0 + 3, X1 - 3))
SEMBOL = (slice(785, 885), slice(X0 + 3, X1 - 3))          # kucuk semboller (poster y ~1840-2130 -> kare)
ISIM = (slice(885, 965), slice(X0 + 3, X1 - 3))            # isim satiri
TAG = (slice(995, 1090), slice(X0 + 3, X1 - 3))            # slogan
DUVAR = (slice(1220, 1330), slice(40, 1040))               # maket duvari (aciklik disi)
ZEMIN = (slice(185, 245), slice(170, 330))                 # poster zemini (sol ust, murekkepsiz)
BEKLENEN = {'EJ': ('EMILY', 'JAMES', 'It Began With a Kiss in the Rain'),
            'IN': ('ISABELLA', 'NOAH', "I'd Choose You in Every Lifetime"),
            'AM': ('ALEXANDER', 'MIA', 'You Feel Like Home')}
P_ISIM, P_TAG = (slice(2150, 2350), slice(300, 2100)), (slice(2480, 2720), slice(300, 2100))  # poster koordinatlari
ETSY_MAX_MB = 100


def kareler(v):
    p = subprocess.Popen([FF, '-v', 'quiet', '-i', str(v), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    n = W_ * H_ * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n: break
            yield np.frombuffer(b, np.uint8).reshape(H_, W_, 3)
    finally:
        p.kill(); p.wait()


def teknik(v):
    s = subprocess.run([FF, '-hide_banner', '-i', str(v)], capture_output=True, text=True).stderr
    d = re.search(r'Duration: (\d+):(\d+):([\d.]+)', s); vi = re.search(r'Video: (.*)', s)
    sure = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else None
    vi = vi.group(1) if vi else ''
    fps = re.search(r'([\d.]+) fps', vi); wh = re.search(r'(\d{3,4})x(\d{3,4})', vi)
    return {'sure_sn': sure, 'wh': f'{wh.group(1)}x{wh.group(2)}' if wh else None, 'fps': float(fps.group(1)) if fps else None,
            'codec': 'h264 (High)' in vi, 'yuv420p': 'yuv420p' in vi, 'ses': 'Audio:' in s,
            'mb': round(Path(v).stat().st_size / 1e6, 3)}


def lab(a):
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8).reshape(1, -1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]


def de76(a, b):
    return float(np.linalg.norm(np.median(lab(a), 0) - np.median(lab(b), 0)))


def sobel_e(g):
    g = cv2.cvtColor(np.clip(g, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    return float(np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)).mean())


def luma(a):
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def fark_harita(a, b):
    """luma farki, 3x3 medyan (yuv420p renk alt ornekleme kenar farki luma'da yok)."""
    return cv2.medianBlur(np.clip(np.abs(luma(a) - luma(b)), 0, 255).astype(np.uint8), 3)


def kenar_maske(E, esik=12.0, genis=3):
    """beklenen karedeki murekkep/cerceve kenarlari (+genis px): sikistirma kenar farki leke sayilmaz."""
    g = luma(E); m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) > esik
    return cv2.dilate(m.astype(np.uint8), np.ones((2 * genis + 1, 2 * genis + 1), np.uint8)) > 0


def ocr(img, olcek=3):
    import pytesseract
    g = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_CUBIC) if olcek != 1 else g
    g = 255 - g                                             # acik yazi koyu zemin -> koyu yazi acik zemin
    return pytesseract.image_to_string(g, config='--psm 7').strip()


def norm(t):
    return re.sub(r'[^a-z ]', '', t.lower().replace('’', "'").replace("'", '')).split()


def plan_kur(v2):
    Wc = np.array(list(v2['agirlik'].values())).mean(0); Wc = (Wc - Wc[0]) / (Wc[-1] - Wc[0])
    egri = np.interp(np.arange(GECIS + 1) * (len(Wc) - 1) / GECIS, np.arange(len(Wc)), Wc)
    n = TUR * len(SIRA) * (SABIT + GECIS); plan, k = [('EJ', 'EJ', 0.0)] * BAS, 0
    while len(plan) < n:
        x, y = SIRA[k % 3], SIRA[(k + 1) % 3]; k += 1
        plan += [(x, y, float(egri[j])) for j in range(1, GECIS + 1)] + [(y, y, 0.0)] * SABIT
    return plan[:n]


class Ref:
    """video_cift.py ile ayni sabitler (referans maket, afin, ton, aydinlatma, aciklik alfasi)."""
    def __init__(self, rd):
        rd = Path(rd)
        F = None
        for i, f in enumerate(kareler(rd / 'AstroLove_Centered_Immediate_12s.mp4')):
            if i == 150: F = f.astype(np.float32); break
        self.F = F
        self.v2 = json.load(open(rd / 'v2_meta.json')); self.Maf = np.array(self.v2['M'], np.float32)
        reg = np.zeros((H_, W_), bool); reg[Y0:Y1, X0:X1] = True
        Wr = self.warp(np.asarray(Image.open(rd / 'P_emily_james.png').convert('RGB')).astype(np.float32))
        self.ton = [np.polyfit(Wr[..., c][reg], F[..., c][reg], 1) for c in range(3)]
        m = reg.astype(np.float32)[..., None]; Tr = self.tf(Wr)
        self.G = np.clip(cv2.GaussianBlur(F * m, (0, 0), 30) / np.maximum(cv2.GaussianBlur(Tr * m, (0, 0), 30), 1), 0.6, 1.6)
        al = np.zeros((H_, W_), np.float32); al[Y0 + 3:Y1 - 3, X0 + 3:X1 - 3] = 1
        self.al = cv2.GaussianBlur(al, (0, 0), 1.0)[..., None]
        self.plan = plan_kur(self.v2)

    def warp(self, P):
        return cv2.warpAffine(P, self.Maf, (W_, H_), flags=cv2.INTER_AREA)

    def tf(self, W):
        return np.stack([np.polyval(self.ton[c], W[..., c]) for c in range(3)], 2)

    def durumlar(self, cdir):
        """video_cift.py'deki ST hesabinin aynisi (AM tagline kaydirma + altin esitleme dahil)."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from tagline_olc import olc
        TB0, TB1 = 2480, 2720
        def taban(P):
            b = P[TB0:TB1, 300:2100]; m = (b[..., 0] - b[..., 2]) > 40
            lab_, nn = ndimage.label(ndimage.binary_dilation(m, structure=np.ones((5, 101))))
            m &= lab_ == (np.argmax(ndimage.sum(m, lab_, range(1, nn + 1))) + 1)
            pr = m.sum(1).astype(float); return TB0 + int(np.where(pr > 0.5 * pr.max())[0][-1])
        POS = {k: np.asarray(Image.open(cdir / f'POSTER_{k}.png').convert('RGB')).astype(np.float32) for k in SIRA}
        ham = {k: v.copy() for k, v in POS.items()}
        dy = taban(POS['AM']) - taban(POS['EJ'])
        if abs(dy) > 1:
            bant = {k: POS[k][TB0 - 40:TB1 + 40] for k in SIRA}
            rb = np.stack([bant[k][..., 0] - bant[k][..., 2] for k in SIRA]); sec = np.argmin(rb, 0)
            zemin = np.choose(sec[..., None], [bant[k] for k in SIRA])
            w = np.clip((rb[2] - 20) / 60, 0, 1)[..., None]; ks = lambda X: np.roll(X, -dy, axis=0)
            POS['AM'] = POS['AM'].copy(); POS['AM'][TB0 - 40:TB1 + 40] = zemin * (1 - ks(w)) + ks(bant['AM']) * ks(w)
        ST = {k: self.F * (1 - self.al) + np.clip(self.G * self.tf(self.warp(POS[k])), 0, 255) * self.al for k in SIRA}
        hedef = (np.array(olc(ST['EJ'])['altin_ort']) + np.array(olc(ST['IN'])['altin_ort'])) / 2
        kaz = hedef / np.array(olc(ST['AM'])['altin_ort'])
        b_ = np.zeros((H_, W_), np.float32); b_[995:1075, X0 + 8:X1 - 8] = 1; b_ = cv2.GaussianBlur(b_, (0, 0), 3)[..., None]
        wi = np.clip(((ST['AM'][..., 0] - ST['AM'][..., 2]) - 20) / 60, 0, 1)[..., None] * b_
        ST['AM'] = ST['AM'] * (1 - wi) + np.clip(ST['AM'] * kaz, 0, 255) * wi
        return {k: np.clip(np.rint(v), 0, 255) for k, v in ST.items()}, ham, int(dy)


def kalibre(ref, cl):
    """CL v5: E sabit kareleri - ref kare 150 = saf sikistirma farki -> esikler."""
    ort, p, sob, cl_mid = [], [], [], {}
    global KM_CL
    KM_CL = kenar_maske(ref.F)
    for j, f in enumerate(kareler(cl)):
        x, y, w = ref.plan[j]
        if x == y == 'EJ' and j >= BAS:
            d = fark_harita(f, ref.F)[AP][~KM_CL[AP]]
            ort.append(float(np.abs(f.astype(np.float32) - ref.F)[AP].mean())); p.append(float(np.percentile(d, 99.99)))
            sob.append(abs(1 - sobel_e(f[AP]) / sobel_e(ref.F[AP])))
            cl_mid.setdefault('EJ', f.copy())
    e = {'kare_ort': round(1.5 * max(ort), 3), 'leke_px': round(1.5 * max(p), 1), 'leke_alan': 16,
         'sobel_populasyon': 'median + 5*MAD ve > 0.02 (tum videolar)', 'siyah_luma': 16.0, 'dE76': 3.0,
         'olcum': {'cl_ort_max': round(max(ort), 3), 'cl_p9999_max': round(max(p), 2), 'cl_sobel_max': round(max(sob), 4), 'n': len(ort)}}
    return e, cl_mid['EJ']


def denetle(ref, esik, cl_E, cift, cdir, vpath, out):
    r = {'cift': cift}; kont = {}
    t = teknik(vpath); r.update({f'tek_{k}': v for k, v in t.items()})
    kont['teknik'] = (t['sure_sn'] is not None and abs(t['sure_sn'] - 12.6) <= 0.05 and t['wh'] == '1080x1350' and t['fps'] == 30
                      and t['codec'] and t['yuv420p'] and not t['ses'] and t['mb'] <= ETSY_MAX_MB)
    ST, POS, dy = ref.durumlar(cdir); r['am_dy'] = dy
    n = 0; ort_max = 0.0; leke = []; siyah = 0; yirt = 0; sembol_max = 0.0; donma = 0; onceki = None; mid = {}
    gec_j = {j for j, (x, y, w) in enumerate(ref.plan) if x != y}
    en_kotu = (0, None, None)
    KM = {k: kenar_maske(ST[k]) for k in SIRA}; onceki_E = None
    for j, f in enumerate(kareler(vpath)):
        n += 1
        if j >= len(ref.plan): break
        x, y, w = ref.plan[j]
        E = ST[x] * (1 - w) + ST[y] * w
        ff = f.astype(np.float32)
        o = float(np.abs(ff - E)[AP].mean()); ort_max = max(ort_max, o)
        if o > en_kotu[0]: en_kotu = (o, j, f.copy())
        sembol_max = max(sembol_max, float(np.abs(ff - E)[SEMBOL].mean()))
        d = fark_harita(f, E); km = KM[x] | KM[y]
        lab_, nn = ndimage.label((d > esik['leke_px'])[AP] & ~km[AP])
        if nn:
            al = ndimage.sum(np.ones_like(lab_), lab_, range(1, nn + 1))
            obj = ndimage.find_objects(lab_)
            for i in np.where(al >= esik['leke_alan'])[0]:
                sl = obj[i]
                leke.append({'kare': j, 'alan': int(al[i]), 'y': int(sl[0].start + Y0 + 3), 'x': int(sl[1].start + X0 + 3)})
        if float(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).mean()) < esik['siyah_luma']: siyah += 1
        satir = np.abs(ff - E)[AP].mean((1, 2))
        if satir.max() > 6 * esik['kare_ort']: yirt += 1
        if onceki is not None:                                   # donma: beklenen kare degisiyorsa video da degismeli
            e_adim = float(np.abs(E - onceki_E)[AP].mean()); v_adim = float(np.abs(ff - onceki)[AP].mean())
            if e_adim > 1.0 and v_adim < 0.2 * e_adim: donma += 1
        onceki, onceki_E = ff, E
        if x == y and j >= BAS and x not in mid and ref.plan[j - 15][0] == x and ref.plan[j - 15][1] == x:
            mid[x] = (j, f.copy())
    r.update({'kare_sayisi': n, 'kare_fark_ort_max': round(ort_max, 3), 'sembol_fark_max': round(sembol_max, 3),
              'leke_sayisi': len(leke), 'siyah_kare': siyah, 'yirtilma_kare': yirt, 'donma_gecis': donma})
    kont['kare_sayisi'] = n == len(ref.plan)
    kont['cift_dogrulugu'] = sembol_max <= esik['kare_ort'] * 2
    kont['iz_leke'] = len(leke) == 0
    kont['kare_fark'] = ort_max <= esik['kare_ort'] * 2
    kont['siyah_donma_yirtilma'] = siyah == 0 and yirt == 0 and donma == 0
    sob = [abs(1 - sobel_e(mid[k][1][AP]) / sobel_e(ST[k][AP])) for k in SIRA if k in mid]
    r['sobel_sapma_max'] = round(max(sob), 4) if sob else None
    kont['sobel'] = bool(sob)                                     # esik popuasyondan: main() sonunda
    de_d = de76(mid['EJ'][1][DUVAR], cl_E[DUVAR]); de_z = max(de76(mid[k][1][ZEMIN], cl_E[ZEMIN]) for k in SIRA if k in mid)
    r.update({'dE76_duvar': round(de_d, 2), 'dE76_poster_zemin_max': round(de_z, 2)})
    kont['renk'] = de_d <= esik['dE76'] and de_z <= esik['dE76']
    ocr_ok = True; ocr_not = []
    for k in SIRA:
        a, b, tg = BEKLENEN[k]
        p_isim = ocr(POS[k][P_ISIM], 1); p_tag = ocr(POS[k][P_TAG], 1)
        v_isim = ocr(mid[k][1][ISIM]) if k in mid else ''; v_tag = ocr(mid[k][1][TAG]) if k in mid else ''
        r[f'ocr_{k}_poster'] = f'{p_isim} | {p_tag}'; r[f'ocr_{k}_video'] = f'{v_isim} | {v_tag}'
        poster_ok = a in p_isim.upper() and b in p_isim.upper() and norm(p_tag) == norm(tg)
        v_benz = SequenceMatcher(None, ' '.join(norm(v_tag)), ' '.join(norm(tg))).ratio()
        video_ok = a in v_isim.upper() and b in v_isim.upper() and v_benz >= 0.9
        r[f'ocr_{k}_tag_benzerlik'] = round(v_benz, 3)
        if not (poster_ok and video_ok):
            ocr_ok = False; ocr_not.append(f'{k}:{"poster" if not poster_ok else ""}{"video" if not video_ok else ""}')
    kont['yazi_ocr'] = ocr_ok; r['ocr_fail'] = ';'.join(ocr_not)
    r['PASS'] = all(kont.values()); r['fail_kontroller'] = ';'.join(k for k, v in kont.items() if not v)
    r.update({f'k_{k}': v for k, v in kont.items()})
    fd = out / 'FAIL_KARELER'
    if not r['PASS']:
        fd.mkdir(exist_ok=True)
        Image.fromarray(en_kotu[2]).save(fd / f'{cift}_kare{en_kotu[1]:03d}.jpg', quality=90)
        for l in leke[:3]:
            pass
    r['_en_kotu'] = (en_kotu[0], en_kotu[1], en_kotu[2], leke[:5])
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a1', required=True); ap.add_argument('--cl', required=True); ap.add_argument('--ref', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--ciftler', default='')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ref = Ref(a.ref); esik, cl_E = kalibre(ref, a.cl)
    print('ESIK', json.dumps(esik), flush=True)
    cl_t = teknik(a.cl)
    ciftler = sorted(p.name for p in Path(a.a1).iterdir() if (p / 'VIDEO.mp4').exists())
    if a.ciftler: ciftler = [c for c in ciftler if c in a.ciftler.split(',')]
    satirlar, kotu = [], []
    cl_row = {'cift': 'CANCER_LIBRA (REFERANS v5)', **{f'tek_{k}': v for k, v in cl_t.items()}}
    cl_row['k_teknik'] = abs(cl_t['sure_sn'] - 12.6) <= 0.05 and cl_t['wh'] == '1080x1350' and cl_t['fps'] == 30 and cl_t['codec'] \
        and cl_t['yuv420p'] and not cl_t['ses'] and cl_t['mb'] <= ETSY_MAX_MB
    cl_row['PASS'] = cl_row['k_teknik']; cl_row['fail_kontroller'] = '' if cl_row['PASS'] else 'teknik'
    cl_row['not'] = 'esik kaynagi; E durumu = ref kare 150 (saf sikistirma), diger kontroller bu videoya gore'
    satirlar.append(cl_row)
    for i, c in enumerate(ciftler, 1):
        try:
            r = denetle(ref, esik, cl_E, c, Path(a.a1) / c, Path(a.a1) / c / 'VIDEO.mp4', out)
            o, j, f, lk = r.pop('_en_kotu'); kotu.append((o, c, j, f, lk))
        except Exception as e:                                          # noqa: BLE001  cift FAIL olur, is durmaz
            r = {'cift': c, 'PASS': False, 'fail_kontroller': 'istisna', 'hata': repr(e)[:200]}
        satirlar.append(r)
        g = time.time() - t0
        print(f'[{i}/{len(ciftler)}] %{100 * i / len(ciftler):.0f} gecen {g:.0f}s kalan ~{g / i * (len(ciftler) - i):.0f}s | {c} '
              f'{"PASS" if r["PASS"] else "FAIL " + r.get("fail_kontroller", "")} fark={r.get("kare_fark_ort_max")} '
              f'leke={r.get("leke_sayisi")} dE={r.get("dE76_poster_zemin_max")}', flush=True)
    sd = np.array([r['sobel_sapma_max'] for r in satirlar if r.get('sobel_sapma_max') is not None], float)
    if len(sd):
        med = float(np.median(sd)); mad = float(np.median(np.abs(sd - med))) or 1e-4
        esik['sobel'] = round(max(med + 5 * mad, 0.02), 4); esik['sobel_olcum'] = {'median': round(med, 4), 'mad': round(mad, 5)}
        for r in satirlar:
            if r.get('sobel_sapma_max') is not None and r['sobel_sapma_max'] > esik['sobel']:
                r['k_sobel'] = False; r['PASS'] = False
                r['fail_kontroller'] = ';'.join(x for x in (r.get('fail_kontroller') or '').split(';') + ['sobel'] if x)
    alan = []
    for r in satirlar:
        for k in r:
            if k not in alan: alan.append(k)
    with open(out / 'VIDEO_QC.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); [w.writerow(r) for r in satirlar]
    # kontak sayfasi: en kotu 12 kare (kare farki ortalamasina gore), lekeler kirmizi kutu
    kotu.sort(key=lambda z: -z[0]); kotu = kotu[:12]
    tw, th = 360, 450; S = Image.new('RGB', (4 * tw + 50, 3 * (th + 40) + 70), (236, 233, 226)); dr = ImageDraw.Draw(S)
    dr.text((10, 10), f'VIDEO QC en kotu 12 kare (kare farki ort; esik {esik["kare_ort"] * 2}) - kirmizi kutu = leke', fill=(20, 20, 20))
    for i, (o, c, j, f, lk) in enumerate(kotu):
        im = Image.fromarray(f); d = ImageDraw.Draw(im)
        for l in lk: d.rectangle((l['x'] - 12, l['y'] - 12, l['x'] + 24, l['y'] + 24), outline=(255, 0, 0), width=4)
        x, y = 10 + (i % 4) * (tw + 10), 40 + (i // 4) * (th + 40)
        S.paste(im.resize((tw, th)), (x, y)); dr.text((x, y + th + 4), f'{c} kare {j} fark {o:.2f}', fill=(20, 20, 20))
    S.save(out / 'VIDEO_QC_KONTAK_12.jpg', quality=88)
    ozet = {'toplam': len(satirlar), 'PASS': sum(1 for r in satirlar if r.get('PASS')), 'esik': esik,
            'FAIL': {r['cift']: r.get('fail_kontroller') for r in satirlar if not r.get('PASS')}, 'sure_s': round(time.time() - t0)}
    (out / 'VIDEO_QC_OZET.json').write_text(json.dumps(ozet, indent=1, ensure_ascii=False))
    print('OZET', json.dumps(ozet, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
