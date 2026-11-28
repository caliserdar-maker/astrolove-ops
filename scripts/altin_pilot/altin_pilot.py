"""Poster galeri altin pilotu (CANCER_LIBRA 4570143815; Merkez gorevi 28 Kas 2026). ETSY'YE YAZMAZ.
Girdi: canli galerinin Etsy CDN kopyalari (eski/rNN_<image_id>.jpg; Drive GALERI.json 25 Kas yedegindeki url_fullxfull).
Yontem (logo_cikti/logo_orijinal/logo_orijinal_altin.py ile ayni ilke; sosyal/pin_v6/lib.py Poster ayrismasi):
  1. Poster kutusu icinde altin cekirdek maskesi (koyu zemin: R-B > 40 ve R > 70; beyaz zemin: R-B > 30 ve B < 235).
  2. Zemin = altin alaninin inpaint'i (pin_v6 Poster.bg). Karisim agirligi w = koyu zeminde kirmizi fazlasi, beyaz zeminde mavi eksigi
     (10..90 rampa); bolme yok (JPEG gurultusu buyumez); kenar yumusakligi w ile korunur.
  3. Parlaklik SIRASI: her grubun (A = en buyuk bilesen, birlesik sembol; B = halka, kucuk burc isaretleri, sonsuz, isimler,
     mesaj, yildizlar) cekirdek piksellerindeki parlaklik sirasi pin altini dagilimina eslenir; ust %10 kesik (parlak leke yok).
     A -> pin birlesik sembol tablosu, B -> pin alt satir (kucuk isaretler + isimler) tablosu.
  4. Ince halka (daire) bandi DEGISMEZ (soluk sampanya ton; karar Serdar'in).
  5. Kutu disi (duvar, cerceve, vazo, Canva basliklari) piksel piksel ayni.
Kullanim: python altin_pilot.py   (klasor: bu dosyanin yani)
"""
import os, json
import numpy as np, cv2
from PIL import Image

KOK = os.path.dirname(os.path.abspath(__file__))
PIN = os.path.join(KOK, '..', 'logo_girdi', 'PIN_ALTIN_CANCER_LEO.jpg')
LW = np.array([0.299, 0.587, 0.114], np.float32)
UST_KESIK = 90          # pin dagiliminin en ust %10'u kullanilmaz

# canli galeri: dosya -> [(kutu x0, y0, x1, y1), zemin]   (kutular olculdu: koyu bilesen bbox; PW = ayni cerceve ici)
IS = {
    'r01_8749216062.jpg': [((984, 680, 2023, 2031), 'koyu')],                 # kapak, MB poster siyah cerceve + paspartu
    'r03_8812062435.jpg': [((441, 498, 1581, 1923), 'koyu')],                 # W03 kisisellestirme, MB poster
    'r06_8812065289.jpg': [((523, 497, 950, 1052), 'koyu'), ((1283, 497, 1710, 1052), 'koyu'),
                           ((2043, 497, 2470, 1052), 'acik')],                # W06 renk secimi: MB, DB, PW (CI / WP kahve, dokunulmaz)
    'r07_8812066177.jpg': [((984, 680, 2023, 2031), 'koyu')],                 # MB
    'r08_8812066995.jpg': [((984, 680, 2023, 2031), 'koyu')],                 # DB
    'r09_8812067931.jpg': [((984, 680, 2023, 2031), 'acik')],                 # PW
}


def pin_tablo():
    p = np.asarray(Image.open(PIN).convert('RGB')).astype(np.float32)
    out = {}
    for ad, (y0, y1, x0, x1) in {'A': (300, 1060, 150, 860), 'B': (1100, 1260, 150, 860)}.items():
        s = p[y0:y1, x0:x1]
        m = (s[..., 0] > 110) & (s[..., 0] > s[..., 2] + 50)
        L = s @ LW
        q = np.percentile(L[m], np.linspace(2, 97, 41))
        tab = np.array([s[m & (L >= q[i]) & (L < q[i + 1])].mean(0) for i in range(40)])
        out[ad] = dict(Ls=np.sort(L[m]), q=q, tab=tab, tl=(q[:-1] + q[1:]) / 2,
                       med=np.median(s[m], 0).round().tolist())
    return out


def renk(T, L):
    L = np.clip(L, T['q'][0], T['q'][-1])
    return np.stack([np.interp(L, T['tl'], T['tab'][:, c]) for c in range(3)], -1)


def halka_bul(m, W, H):
    """ince altin halka (daire): merkez (0.47-0.53 W, 0.36-0.44 H) ve yaricap (0.30-0.48 W) taramasi; m maskesindeki piksellerin
    merkeze uzaklik histogrami en yuksek tepe (Hough PW'de yanlis yaricap verdi, 28 Kas olcumu)."""
    ys, xs = np.nonzero(m[::2, ::2]); ys = ys * 2.0; xs = xs * 2.0
    best = (0, None)
    lo, hi = int(0.3 * W), int(0.48 * W)
    for cy in np.arange(0.36 * H, 0.44 * H, 2):
        for cx in np.arange(0.47 * W, 0.53 * W, 2):
            d = np.hypot(xs - cx, ys - cy)
            hst = np.bincount(np.clip(d, 0, 10000).astype(int), minlength=hi + 3)
            s = hst[lo:hi] + hst[lo + 1:hi + 1] + hst[lo - 1:hi - 1]
            k = int(np.argmax(s))
            if s[k] > best[0]:
                best = (s[k], (cx, cy, lo + k))
    return best[1]


def poster_isle(P, zemin, T):
    P = P.astype(np.float32)
    R, B = P[..., 0], P[..., 2]
    if zemin == 'koyu':
        tohum = ((R - B) > 40) & (R > 70)
    else:
        tohum = ((R - B) > 30) & (B < 235)
    h, w = tohum.shape
    KEN = 10                                                         # poster kenari / paspartu gecisi islenmez
    ic = np.zeros((h, w), bool); ic[KEN:h - KEN, KEN:w - KEN] = True
    tohum &= ic
    s = 0.5 if max(h, w) > 800 else 1.0

    def zemin_tahmin(maske8):
        """pin_v6 Poster.bg: genisletilmis altin alani inpaint (yarim olcekte)"""
        dil = cv2.dilate(maske8, np.ones((9, 9), np.uint8))
        sm = cv2.resize(P, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        mm = cv2.dilate(cv2.resize(dil, (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        bgs = cv2.inpaint(np.clip(sm, 0, 255).astype(np.uint8), mm, 6, cv2.INPAINT_TELEA)
        return cv2.resize(bgs.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)

    def fazla(bg):
        return (R - bg[..., 0]) if zemin == 'koyu' else (bg[..., 2] - B)

    bg = zemin_tahmin(tohum.astype(np.uint8))
    # cekirdek = zeminden belirgin ayrilan ve bir altin tohumuna DOKUNAN bilesenler (beyaza yakin parlak tepeler dahil; yoksa
    # eski parlak tepe yeni altinin icinde beyaz cizgi olarak kalir)
    E = ((fazla(bg) > 30) & ic).astype(np.uint8)
    n, lab, _, _ = cv2.connectedComponentsWithStats(E, 8)
    tut = np.zeros(n, bool); tut[np.unique(lab[tohum & (E > 0)])] = True; tut[0] = False
    core = tut[lab] | tohum
    # HALKA (ince daire cizgisi) DEGISTIRILMEZ (28 Kas olcumu): halka canli gorsellerde soluk sampanya / gumus tonda
    # (medyan r01 113,105,96; r07 187,168,136; r03 203,177,122), eski sembol altinindan zaten ayri. Kismi tohum esigiyle
    # r01'de halkada iki turuncu leke cikti, r07 / r08 ayni halkada esigin iki yanina dustu (0.48 / 0.53). Tutarlilik icin
    # halka bandi (|d - r| <= max(4, 0.016 r)) tum posterlerde aynen korunur; yeni altina alinmasi Serdar karari.
    hm = (R > 60) if zemin == 'koyu' else (B < 225)
    cx, cy, rr = halka_bul(hm & ic, w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    bant = np.abs(np.hypot(xx - cx, yy - cy) - rr) <= max(4.0, 0.016 * rr)
    core &= ~bant
    core8 = core.astype(np.uint8)
    bg = zemin_tahmin(core8)
    # Iki zemin, iki karisim yolu (28 Kas gozle kontrol, 3x buyutme):
    #  - unmix + bolme (c = zemin + (P - zemin) / alfa) JPEG gurultusunu buyuttu, kenarda turuncu sacak -> kullanilmaz.
    #  KOYU zemin: agirlikli esleme. Kenarin eski koyu golgesi kendi parlaklik sirasiyla pin'in koyu ucuna gider (golge korunur);
    #    w = kirmizi fazlasi rampasi 10..90. (Fark yayma yontemi koyu zeminde kenarda siyah benek verdi.)
    #  ACIK zemin: fark yayma. Yeni renk yalniz DOLU altinda (fazla > 90) sira eslemesiyle; fark (yeni - eski) kenara yayilir,
    #    kenar pikseli kendi altin payi kadar (a) kayar: P = a*altin + (1-a)*beyaz ise yeni = P + a*fark (dogrusal karisim, bolme yok).
    #    (Agirlikli esleme beyaz zeminde harfleri kalinlastirdi.)
    fz = fazla(bg)
    bolge = cv2.dilate(core8, np.ones((5, 5), np.uint8)) > 0       # yalniz altin cevresi; zemin gurultusu degismez
    bolge &= ~cv2.dilate(bant.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    L = cv2.GaussianBlur(P @ LW, (0, 0), 0.7)                    # JPEG blok gurultusu siraya tasinmasin
    dolu = core if zemin == 'koyu' else (core & (fz > 90.0))
    esle = bolge if zemin == 'koyu' else dolu                      # yeni rengin hesaplandigi pikseller
    # gruplar: A = birlesik sembol parcalari (alan >= en buyugun %30'u; CL'de 3 parca), B = digerleri (halka, isaretler, yazilar)
    n, lab, st, _ = cv2.connectedComponentsWithStats(core8, 8)
    buyuk = st[1:, 4].max()
    sec = np.zeros(n, bool); sec[1:] = st[1:, 4] >= 0.3 * buyuk
    A = cv2.dilate(sec[lab].astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    yeni = P.copy()
    olcum = {'halka': dict(merkez=[round(cx), round(cy)], r=int(rr), degisti=False)}
    for ad, grup in (('A', A), ('B', ~A)):
        ref_px, g = grup & dolu, grup & esle
        if ref_px.sum() < 30:
            continue
        Ls = np.sort(L[ref_px])
        sira = np.interp(L[g], Ls, np.linspace(0, 1, Ls.size))                # eski altindaki parlaklik sirasi
        hedefL = np.percentile(T[ad]['Ls'], np.clip(sira * 100, 0, UST_KESIK))  # pin dagilimi, ust %10 yok
        yeni[g] = renk(T[ad], hedefL)
        olcum[ad] = dict(parca=int(sec[1:].sum()) if ad == 'A' else int(n - 1 - sec[1:].sum()), dolu_px=int(ref_px.sum()),
                         eski_medyan=np.median(P[ref_px], 0).round().tolist())
    if zemin == 'koyu':
        w = np.where(bolge, np.clip((fz - 10.0) / 80.0, 0, 1), 0).astype(np.float32)
        w = np.maximum(w, core.astype(np.float32))
        w = cv2.GaussianBlur(w, (0, 0), 0.6) * bolge
        out = P + w[..., None] * (yeni - P)
    else:
        d = dolu.astype(np.float32)
        nrm = cv2.GaussianBlur(d, (0, 0), 2.0)
        ok = nrm > 1e-3
        fark = np.zeros_like(P); ref = np.zeros_like(P)
        for c in range(3):
            fark[..., c] = np.where(ok, cv2.GaussianBlur((yeni[..., c] - P[..., c]) * d, (0, 0), 2.0) / np.maximum(nrm, 1e-3), 0)
            ref[..., c] = np.where(ok, cv2.GaussianBlur(P[..., c] * d, (0, 0), 2.0) / np.maximum(nrm, 1e-3), 0)
        a = np.where(ok & bolge, np.clip(fz / np.maximum(bg[..., 2] - ref[..., 2], 1.0), 0, 1), 0)
        out = P + a[..., None] * fark
        out[dolu] = yeni[dolu]
    for ad, grup in (('A', A), ('B', ~A)):
        g = grup & dolu
        if ad in olcum:
            olcum[ad]['yeni_medyan'] = np.median(out[g], 0).round().tolist()
            olcum[ad]['yeni_L_max'] = round(float((out[g] @ LW).max()), 1)
            olcum[ad]['eski_L_max'] = round(float((P[g] @ LW).max()), 1)
    return np.clip(out, 0, 255), olcum


def main():
    T = pin_tablo()
    os.makedirs(os.path.join(KOK, 'yeni'), exist_ok=True)
    rap = {'pin_medyan': {k: v['med'] for k, v in T.items()},
           'pin_L_p90': {k: round(float(np.percentile(v['Ls'], 90)), 1) for k, v in T.items()}, 'gorseller': {}}
    for f, kutular in IS.items():
        im = np.asarray(Image.open(os.path.join(KOK, 'eski', f)).convert('RGB')).astype(np.float32)
        out = im.copy()
        r = []
        for (x0, y0, x1, y1), z in kutular:
            o, ol = poster_isle(im[y0:y1, x0:x1], z, T)
            out[y0:y1, x0:x1] = o
            r.append(dict(kutu=[x0, y0, x1, y1], zemin=z, **ol))
        # kutu disi birebir ayni mi
        dis = np.ones(im.shape[:2], bool)
        for (x0, y0, x1, y1), _ in kutular:
            dis[y0:y1, x0:x1] = False
        assert np.array_equal(out[dis], im[dis])
        Image.fromarray(out.round().astype(np.uint8)).save(os.path.join(KOK, 'yeni', f.replace('.jpg', '_YENI_ALTIN.jpg')),
                                                         quality=95, subsampling=0)
        rap['gorseller'][f] = r
        print(f, json.dumps(r))
    json.dump(rap, open(os.path.join(KOK, 'yeni', 'OLCUM.json'), 'w'), indent=1)
    print('pin', rap['pin_medyan'], rap['pin_L_p90'])


if __name__ == '__main__':
    main()
