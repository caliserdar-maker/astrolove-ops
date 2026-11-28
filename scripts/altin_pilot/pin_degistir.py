"""CL galerisinde eski altin ogeleri, 25 Kas "altin" pininin kaynagi olan yeni altin katmanlarla DEGISTIRIR (Merkez 28 Kas, 2. gorev).
ETSY YOK. Girdi: eski/rNN_<id>.jpg (canli CDN kopyasi), pin_kaynak/KATMAN_*.png (pin_katman.py, PosterR.layer).
Poster kutusu icinde, oge oge:
  1. eski altin maskesi (altin_pilot.py ile ayni tohum + parlak tepe; ince halka bandi ve yildizlar haric),
     ogeler: birlesik sembol (alan >= en buyugun %30'u), sembolun altindaki satirlar: 1. satir sol / sag kucuk burc,
     2. satir isimler + sonsuz, kalan satirlar mesaj;
  2. olcek: birlesik sembolun eski / yeni kutu oraninin ortalamasi; kucuk ogeler AYNI olcekle (yeni poster oranlari korunur).
     Konum: eski cekirdek kutusu merkezi + (+-6 px) IoU en yuksek kaydirma; IoU (yeni alfa > 0.5 ile eski cekirdek) yazilir.
     Silme maskesi ayrica oge kutusu icinde zeminden ayrilan her pikseli (fz > 12; soluk / gumus parlak tepeler) kapsar;
  3. eski altin (2 px genisletilmis) poster zemininden silinir: cv2.inpaint TELEA + zeminin olculen ince gurultusu;
  4. yeni katman premultiplied LANCZOS ile kucultulup alfa ile bindirilir. Alfa temizligi: a' = (a - e) / (1 - e), e koyu 0.12 / acik 0.35
     (lib.Poster alfasindaki gurultu ve posterin sicak koyu parlama halesi beyaz zemine tasinmaz). ACIK zeminde (PW) kenar rengi cekirdekten (a > 0.85) yayilir: lacivert / koyu hale ve koyu
     kontur beyaz zemine tasinmaz.
Kutu disi piksel piksel aynidir (assert). Halka (ince daire) degistirilmez (1. pilotla ayni karar; Serdar'a soruldu).
"""
import os, sys, json
import numpy as np, cv2
from PIL import Image

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from altin_pilot import IS, halka_bul  # noqa: E402  (ayni kutular, ayni halka bulucu)

KATMAN = {ad: Image.open(os.path.join(KOK, 'pin_kaynak', f'KATMAN_{ad}.png')).convert('RGBA')
          for ad in ('sembol', 'burc_a', 'burc_b', 'isimler', 'mesaj', 'halka')}
# TUM modu (Serdar 28 Kas: "Altin doku olan tum gorsellerdeki tum ogeler de yeni altin doku olmali"): halka da yeni katmanla
# degisir, poster disindaki Canva hardal basligi yeni altin dokusuna boyanir. Cikti yeni_tum/. Varsayilan mod = 2. gorev (yeni_pin/).
TUM = 'tum' in sys.argv[1:]


def halka_daire():
    """KATMAN_halka daire uydurmasi (cebirsel en kucuk kareler): merkez + yaricap, katman koordinatinda"""
    a = np.asarray(KATMAN['halka'])[..., 3] > 127
    yy, xx = np.nonzero(a)
    c = np.linalg.lstsq(np.c_[xx, yy, np.ones_like(xx)], (xx ** 2 + yy ** 2).astype(np.float64), rcond=None)[0]
    cx, cy = c[0] / 2, c[1] / 2
    return cx, cy, float(np.sqrt(c[2] + cx ** 2 + cy ** 2))


HALKA_YENI = halka_daire()


def katman_kutu(L):
    a = np.asarray(L)[..., 3] > 127
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def eski_maske(P, zemin):
    R, B = P[..., 0], P[..., 2]
    tohum = (((R - B) > 40) & (R > 70)) if zemin == 'koyu' else (((R - B) > 30) & (B < 235))
    h, w = tohum.shape
    KEN = 10
    ic = np.zeros((h, w), bool); ic[KEN:h - KEN, KEN:w - KEN] = True
    tohum &= ic
    s = 0.5 if max(h, w) > 800 else 1.0
    sm = cv2.resize(P, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    mm = cv2.resize(cv2.dilate(tohum.astype(np.uint8), np.ones((9, 9), np.uint8)), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST)
    bg = cv2.resize(cv2.inpaint(np.clip(sm, 0, 255).astype(np.uint8), cv2.dilate(mm, np.ones((3, 3), np.uint8)), 6, cv2.INPAINT_TELEA).astype(np.float32),
                    (w, h), interpolation=cv2.INTER_CUBIC)
    fz = (R - bg[..., 0]) if zemin == 'koyu' else (bg[..., 2] - B)
    E = ((fz > 30) & ic).astype(np.uint8)
    n, lab, _, _ = cv2.connectedComponentsWithStats(E, 8)
    tut = np.zeros(n, bool); tut[np.unique(lab[tohum & (E > 0)])] = True; tut[0] = False
    core = tut[lab] | tohum
    hm = (R > 60) if zemin == 'koyu' else (B < 225)
    cx, cy, rr = halka_bul(hm & ic, w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    bant = np.abs(np.hypot(xx - cx, yy - cy) - rr) <= max(4.0, 0.016 * rr)
    core &= ~bant
    return core, bant, (cx, cy, rr), fz


def ogeler(core, h, w):
    n, lab, st, cen = cv2.connectedComponentsWithStats(core.astype(np.uint8), 8)
    buyuk = st[1:, 4].max()
    A = [i for i in range(1, n) if st[i, 4] >= 0.3 * buyuk]
    sy1 = max(st[i, 1] + st[i, 3] for i in A)
    sx0 = min(st[i, 0] for i in A); sx1 = max(st[i, 0] + st[i, 2] for i in A)
    alt = [i for i in range(1, n) if i not in A and st[i, 1] > sy1 and st[i, 4] >= 3
           and sx0 - 0.05 * w < cen[i, 0] < sx1 + 0.05 * w]
    alt.sort(key=lambda i: st[i, 1])
    satir = []
    for i in alt:
        if satir and st[i, 1] <= satir[-1]['y1'] + 0.012 * h:
            satir[-1]['i'].append(i); satir[-1]['y1'] = max(satir[-1]['y1'], st[i, 1] + st[i, 3])
        else:
            satir.append({'i': [i], 'y1': st[i, 1] + st[i, 3]})
    alan = lambda s_: sum(st[i, 4] for i in s_['i'])
    satir = [s_ for s_ in satir if alan(s_) >= 0.004 * sum(st[i, 4] for i in A)]   # yildiz satirlari elenir
    if len(satir) < 3:
        raise SystemExit(f'DUR: sembol altinda 3 satir yok ({len(satir)})')
    mx = (sx0 + sx1) / 2
    O = {'sembol': A,
         'burc_a': [i for i in satir[0]['i'] if cen[i, 0] < mx], 'burc_b': [i for i in satir[0]['i'] if cen[i, 0] >= mx],
         'isimler': satir[1]['i'], 'mesaj': [i for s_ in satir[2:] for i in s_['i']]}
    return O, lab, st


def kutu(st, ids):
    return (min(st[i, 0] for i in ids), min(st[i, 1] for i in ids),
            max(st[i, 0] + st[i, 2] for i in ids), max(st[i, 1] + st[i, 3] for i in ids))


def kucult(L, sx, sy):
    """premultiplied LANCZOS (saydam piksellerin gurultulu rengi kenara karismaz)"""
    nw, nh = max(1, round(L.width * sx)), max(1, round(L.height * sy))
    return L.convert('RGBa').resize((nw, nh), Image.LANCZOS).convert('RGBA')


def hazirla(L, zemin, ince=False):
    """katmani KAYNAK cozunurlukte temizler (kucultmeden once):
    alfa a' = (a - e) / (1 - e), e koyu 0.12 / acik 0.35 (lib.Poster alfa gurultusu; acikta posterin sicak koyu parlama halesi);
    ACIK zeminde ayrica kenar halkasi (a > 0.9 bolgesinin 2 px asindirilmis icinin disi) icten yayilan renkle boyanir: posterin
    lacivert zemine gore koyu kenar konturu beyaz zeminde koyu nokta dizisi veriyordu (28 Kas 5x kontrol)."""
    A = np.asarray(L).astype(np.float32)
    a = A[..., 3] / 255
    e = 0.12 if zemin == 'koyu' else 0.35
    a2 = np.clip((a - e) / (1 - e), 0, 1)
    rgb = A[..., :3]
    if zemin == 'acik':
        # ince halka (kaynakta 4-5 px): asindirma tum ici siler, solan kuyruk koyu kalir (PW'de koyu cizik, 28 Kas 5x kontrol)
        if ince:
            # halkanin solan kuyrugu kaynakta alfa ile degil KARARARAK lacivertte kayboluyor; beyazda koyu cizik olmasin diye
            # kararma alfaya cevrilir (a *= L / 0.8 Lref) ve renk parlak halka pikselinden yayilir
            Lh = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
            Lref = float(np.percentile(Lh[a > 0.9], 70))
            a2 = a2 * np.clip(Lh / (0.8 * Lref), 0, 1)
            ic = ((a > 0.9) & (Lh > 0.6 * Lref)).astype(np.float32)
        else:
            ic = cv2.erode((a > 0.9).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        sg = 6.0 if ince else 2.0
        nrm = cv2.GaussianBlur(ic, (0, 0), sg)
        yay = np.stack([cv2.GaussianBlur(rgb[..., c] * ic, (0, 0), sg) / np.maximum(nrm, 1e-4) for c in range(3)], -1)
        if ince:                                         # yayilimin ulasmadigi kuyruk: halkanin medyan rengi
            yay = np.where((nrm > 1e-3)[..., None], yay, np.median(rgb[ic > 0], 0))
            nrm = np.maximum(nrm, 1.0)
        rgb = np.where((ic > 0)[..., None], rgb, np.where((nrm > 1e-3)[..., None], yay, rgb))
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a2 * 255]).astype(np.uint8), 'RGBA')


def buyut(ids, lab, st, fz, bant, h, w, pay, ad):
    """oge maskesi: cekirdek bilesenleri + ayni satir bandinda zeminden ayrilan (fz > 12) ve ogeye zincirle yakin (yatay <= 0.04 w)
    bilesenler. Soluk / kucuk harfler ("It Began" gibi) cekirdege girmiyordu; kutu eksik kaldi, eski yazi silinmedi ve yeni yazi
    kaydi (r06 ve r03, 28 Kas kontrol). Uzak yildizlar zincire girmez."""
    x0, y0, x1, y1 = kutu(st, ids)
    yb0, yb1 = max(0, y0 - pay), min(h, y1 + pay)
    if ad == 'sembol':
        xb0, xb1 = max(0, x0 - pay), min(w, x1 + pay)
    else:
        xb0, xb1 = int(0.06 * w), int(0.94 * w)
    bant_m = np.zeros((h, w), bool); bant_m[yb0:yb1, xb0:xb1] = True
    F = ((fz > 12) & bant_m & ~bant).astype(np.uint8)
    n, lb, s2, _ = cv2.connectedComponentsWithStats(F, 8)
    cek = np.isin(lab, ids)
    secili = set(np.unique(lb[cek & (F > 0)])) - {0}
    g = 0.04 * w
    degisti = True
    while degisti:
        degisti = False
        if not secili:
            break
        sx0 = min(s2[i, 0] for i in secili); sx1 = max(s2[i, 0] + s2[i, 2] for i in secili)
        for i in range(1, n):
            if i in secili or s2[i, 4] < 2:
                continue
            if ad in ('burc_a', 'burc_b') and not (sx0 - g <= s2[i, 0] + s2[i, 2] / 2 <= sx1 + g):
                continue
            if s2[i, 0] <= sx1 + g and s2[i, 0] + s2[i, 2] >= sx0 - g:
                secili.add(i); degisti = True
    return (np.isin(lb, list(secili)) | cek) & ~bant


def isle(P, zemin):
    h, w = P.shape[:2]
    core, bant, halka, fz = eski_maske(P, zemin)
    O, lab, st = ogeler(core, h, w)
    # oge maskesi: cekirdek bilesenleri + oge kutusu (6 px pay) icinde zeminden ayrilan HER piksel (fz > 12). Soluk / gumus
    # parlak tepeler (sonsuz, S harfi ustu) cekirdege girmiyordu ve ilk denemede eski parca olarak kaldi (28 Kas gozle kontrol).
    pay = max(3, int(0.006 * w))
    # oge maskesi icin zemin: morfolojik acma (koyu) / kapama (acik), cekirdek 0.03 w > en kalin cizgi. eski_maske zemini yalniz
    # altin tohumunun cevresini inpaint ediyordu; tohuma girmeyen soluk harfler zeminde kaliyor, fz ~ 0 cikiyordu (r06 hata ayiklama).
    k = int(0.03 * w) | 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bgm = cv2.morphologyEx(P, cv2.MORPH_OPEN if zemin == 'koyu' else cv2.MORPH_CLOSE, ker)
    bgm = cv2.GaussianBlur(bgm, (0, 0), k / 3)
    fz = (P[..., 0] - bgm[..., 0]) if zemin == 'koyu' else (bgm[..., 2] - P[..., 2])
    M = {}
    for ad, ids in O.items():
        if not ids:
            continue
        M[ad] = buyut(ids, lab, st, fz, bant, h, w, pay, ad)
    # 3. eski altini sil
    sil = np.zeros((h, w), bool)
    for m in M.values():
        sil |= m
    # silme: maske 2 px genisletilir; delik, deligin 9 px DISINDAN (eski altinin koyu kenari / parlamasi karismasin) yarim olcekte
    # inpaint edilen yumusak zeminle doldurulur (ilk denemede TELEA delik kenarindan kahverengi leke tasidi, 28 Kas 8x kontrol).
    sil = cv2.dilate(sil.astype(np.uint8), np.ones((5, 5), np.uint8))
    sil[bant] = 0
    if TUM:
        halka_eski = bant & (fz > 8)                                # eski halka: bant icinde zeminden ayrilan pikseller
        sil |= (cv2.dilate(halka_eski.astype(np.uint8), np.ones((5, 5), np.uint8))
                & cv2.dilate(bant.astype(np.uint8), np.ones((5, 5), np.uint8)))
    gen = cv2.dilate(sil, np.ones((9, 9), np.uint8))
    sc = 0.5 if max(h, w) > 800 else 1.0
    smP = cv2.resize(P, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    smM = cv2.dilate(cv2.resize(gen, (smP.shape[1], smP.shape[0]), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
    bg2 = cv2.resize(cv2.inpaint(np.clip(smP, 0, 255).astype(np.uint8), smM, 8, cv2.INPAINT_TELEA).astype(np.float32), (w, h),
                     interpolation=cv2.INTER_CUBIC)
    temiz = P.copy()
    yum = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 1.0)[..., None]       # delik kenari yumusak gecis
    yum = np.maximum(yum, (sil > 0)[..., None].astype(np.float32))
    temiz = temiz * (1 - yum) + bg2 * yum
    zem = ~cv2.dilate(core.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    gur = float(np.std((P - cv2.GaussianBlur(P, (0, 0), 1.5))[zem]))
    rng = np.random.default_rng(7)
    temiz[sil > 0] += rng.normal(0, gur, (int((sil > 0).sum()), 3))
    out = temiz
    rap = {'halka': [round(halka[0]), round(halka[1]), int(halka[2])], 'zemin_gurultu_std': round(gur, 2), 'silinen_px': int((sil > 0).sum()), 'ogeler': {}}
    for ad, ids in O.items():
        if not ids:
            rap['ogeler'][ad] = 'YOK'; continue
        L = KATMAN[ad]
        kx0, ky0, kx1, ky1 = katman_kutu(L)
        # olcek: birlesik sembolde eski / yeni kutu (genislik ve yukseklik oraninin ortalamasi); kucuk ogelerde AYNI sembol olcegi
        # (yeni posterin oge oranlari korunur; ince yazida kutu orani hale / gurultuyle +-%10 oynuyor, 28 Kas olcumu).
        # konum: cekirdek kutusu merkezi, sonra +-6 px IoU (yeni alfa > 0.5 ile eski cekirdek) en yuksek kaydirma.
        eski = np.isin(lab, ids)                                   # IoU: eski CEKIRDEK (soluk kenar / hale haric)
        if ad == 'sembol':
            ex0, ey0, ex1, ey1 = kutu(st, ids)                      # olcek + merkez: cekirdek kutusu
        else:
            ys_, xs_ = np.where(M[ad])                              # yazi / kucuk isaret: soluk harfler dahil kutu
            ex0, ey0, ex1, ey1 = xs_.min(), ys_.min(), xs_.max() + 1, ys_.max() + 1
        oran = ((ex1 - ex0) / (kx1 - kx0), (ey1 - ey0) / (ky1 - ky0))
        if ad == 'sembol':
            s0 = float(np.mean(oran))
        s = s0
        Ls = kucult(hazirla(L, zemin), s, s)
        La = np.asarray(Ls).astype(np.float32)
        bx = (ex0 + ex1) / 2 - (kx0 + kx1) / 2 * s
        by = (ey0 + ey1) / 2 - (ky0 + ky1) / 2 * s
        best = (-1, 0, 0)
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                x0, y0 = int(round(bx)) + dx, int(round(by)) + dy
                m = np.zeros((h, w), bool)
                ya, xa = max(0, y0), max(0, x0); yb, xb = min(h, y0 + Ls.height), min(w, x0 + Ls.width)
                m[ya:yb, xa:xb] = La[ya - y0:yb - y0, xa - x0:xb - x0, 3] > 127
                iou = (m & eski).sum() / max(1, (m | eski).sum())
                if iou > best[0]:
                    best = (iou, x0, y0)
        iou, x0, y0 = best
        a = La[..., 3] / 255
        rgb = La[..., :3]
        ya, xa = max(0, y0), max(0, x0); yb, xb = min(h, y0 + Ls.height), min(w, x0 + Ls.width)
        aa = a[ya - y0:yb - y0, xa - x0:xb - x0, None]
        out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - aa) + rgb[ya - y0:yb - y0, xa - x0:xb - x0] * aa
        rap['ogeler'][ad] = dict(eski_kutu=[int(ex0), int(ey0), int(ex1), int(ey1)], olcek=round(s, 4),
                                 en_boy_orani=[round(oran[0], 4), round(oran[1], 4)], konum=[x0, y0], IoU=round(float(iou), 3),
                                 kaynak_px=[int(kx1 - kx0), int(ky1 - ky0)], cikti_px=[int(ex1 - ex0), int(ey1 - ey0)])
    if TUM:
        # HALKA: olcek = eski halka yaricapi (halka_bul) / yeni katman daire yaricapi; merkez hizasi; +-3 px IoU (eski halka maskesi)
        hcx, hcy, hr = HALKA_YENI
        sh = halka[2] / hr
        Ls = kucult(hazirla(KATMAN['halka'], zemin, ince=True), sh, sh)
        La = np.asarray(Ls).astype(np.float32)
        bx, by = halka[0] - hcx * sh, halka[1] - hcy * sh
        best = (-1, 0, 0)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x0, y0 = int(round(bx)) + dx, int(round(by)) + dy
                m = np.zeros((h, w), bool)
                ya, xa = max(0, y0), max(0, x0); yb, xb = min(h, y0 + Ls.height), min(w, x0 + Ls.width)
                m[ya:yb, xa:xb] = La[ya - y0:yb - y0, xa - x0:xb - x0, 3] > 127
                iou = (m & halka_eski).sum() / max(1, (m | halka_eski).sum())
                if iou > best[0]:
                    best = (iou, x0, y0)
        iou, x0, y0 = best
        a = La[..., 3] / 255; rgb = La[..., :3]
        ya, xa = max(0, y0), max(0, x0); yb, xb = min(h, y0 + Ls.height), min(w, x0 + Ls.width)
        aa = a[ya - y0:yb - y0, xa - x0:xb - x0, None]
        out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - aa) + rgb[ya - y0:yb - y0, xa - x0:xb - x0] * aa
        # IoU ince cizgide 1 px kaymaya cok duyarli; yeni halkanin 3 px genisletilmis eski halkaya dusen orani da yazilir
        m = np.zeros((h, w), bool)
        m[ya:yb, xa:xb] = La[ya - y0:yb - y0, xa - x0:xb - x0, 3] > 127
        kap = (m & cv2.dilate(halka_eski.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)).sum() / max(1, m.sum())
        rap['ogeler']['halka'] = dict(eski_r=int(halka[2]), yeni_r_kaynak=round(hr, 1), olcek=round(sh, 4), konum=[x0, y0],
                                      IoU=round(float(iou), 3), eski_banda_dusen_oran=round(float(kap), 3))
    return np.clip(out, 0, 255), rap


# ------------------------------------------------------------------ poster disi: Canva hardal basligi
BASLIK_BOLGE = (900, 300, 2100, 470)          # x0, y0, x1, y1 (r01, r07-r11 olculdu: yazi 1091-1910 x 352-421)


def isim_degrade():
    """KATMAN_isimler (yeni poster isim satiri) harflerinin satir ortalama rengi, ustten alta (sonsuz icin orta %30 atilir;
    harf pikseli en cok satirin %40'indan az olan kenar satirlari atilir). Yeni posterdeki isimlerle ayni yonlu isik."""
    A = np.asarray(KATMAN['isimler']).astype(np.float32)
    a = A[..., 3] / 255; w_ = A.shape[1]
    m = a > 0.9; m[:, int(0.35 * w_):int(0.65 * w_)] = False
    say = m.sum(1)
    ys = [y for y in range(A.shape[0]) if say[y] >= 0.4 * say.max()]
    d = np.array([A[y][m[y]][:, :3].mean(0) for y in ys])
    # satir ortalamasi harf dokusundan oturu satirdan satira oynuyor; 1. denemede baslikta yatay serit verdi (28 Kas 4x kontrol)
    from scipy.ndimage import gaussian_filter1d
    return np.stack([gaussian_filter1d(d[:, c], max(1.0, len(d) / 15), mode='nearest') for c in range(3)], -1)


DEG = isim_degrade()


def baslik_isle(im):
    """duz hardal Canva yazisi -> yeni altin. Duvar W = morfolojik kapama (koyu yazi silinir) + bulaniklik; yazi rengi C = en
    belirgin hardal piksellerin medyani; alfa a = (W - P).(W - C) / |W - C|^2 (yalniz hardal yonundeki pikseller, kosinus > 0.9).
    Yeni renk G(y) = isim degradesi yazinin kendi ust-alt kutusuna gerilir. Cikti = P + a * (G - C): kenar yumusatmasi ve
    kalinlik (a) aynen kalir, yalniz renk degisir."""
    x0, y0, x1, y1 = BASLIK_BOLGE
    P = im[y0:y1, x0:x1].astype(np.float32)
    W = cv2.morphologyEx(P, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    W = cv2.GaussianBlur(W, (0, 0), 6)
    D = W - P
    n = np.linalg.norm(D, axis=2)
    hardal = (P[..., 0] - P[..., 2] > 60) & (n > 0.8 * np.percentile(n, 99.5))
    if hardal.sum() < 500:
        return im, None
    C = np.median(P[hardal], 0)
    v = W - C
    a = (D * v).sum(2) / np.maximum((v * v).sum(2), 1e-3)
    cos = (D * v).sum(2) / np.maximum(n * np.linalg.norm(v, axis=2), 1e-3)
    a = np.where((cos > 0.9) & (n > 4), np.clip(a, 0, 1), 0)
    ys, xs = np.where(a > 0.5)
    ty0, ty1 = ys.min(), ys.max()
    t = np.clip((np.arange(P.shape[0]) - ty0) / max(1, ty1 - ty0), 0, 1)
    idx = np.linspace(0, 1, len(DEG))
    G = np.stack([np.interp(t, idx, DEG[:, c]) for c in range(3)], -1)[:, None, :]
    out = im.copy()
    out[y0:y1, x0:x1] = np.clip(P + a[..., None] * (G - C), 0, 255)
    LW = [0.299, 0.587, 0.114]
    rap = dict(bolge=[x0, y0, x1, y1], yazi_kutu=[int(xs.min() + x0), int(ty0 + y0), int(xs.max() + x0), int(ty1 + y0)],
               eski_renk=C.round().tolist(),
               yeni_degrade_ust_orta_alt=[DEG[0].round().tolist(), DEG[len(DEG) // 2].round().tolist(), DEG[-1].round().tolist()],
               duvar_L=round(float(np.median(W[a > 0.5] @ LW)), 1), eski_L=round(float(C @ LW), 1),
               yeni_L_ort=round(float(DEG.mean(0) @ LW), 1), yazi_px=int((a > 0.5).sum()))
    return out, rap


def main():
    cdir = os.path.join(KOK, 'yeni_tum' if TUM else 'yeni_pin')
    ek = '_YENI_TUM_ALTIN.jpg' if TUM else '_YENI_PIN_ALTIN.jpg'
    os.makedirs(cdir, exist_ok=True)
    isler = dict(IS)
    if TUM:                                    # poster altini kahve (CI / WP); yalniz Canva basligi hardal
        isler['r10_8764250162.jpg'] = []; isler['r11_8822288409.jpg'] = []
    R = {}
    for f, kutular in isler.items():
        im = np.asarray(Image.open(os.path.join(KOK, 'eski', f)).convert('RGB')).astype(np.float32)
        out = im.copy(); r = []
        for (x0, y0, x1, y1), z in kutular:
            o, rp = isle(im[y0:y1, x0:x1], z)
            out[y0:y1, x0:x1] = o
            r.append(dict(kutu=[x0, y0, x1, y1], zemin=z, **rp))
        dis = np.ones(im.shape[:2], bool)
        for (x0, y0, x1, y1), _ in kutular:
            dis[y0:y1, x0:x1] = False
        bas = None
        if TUM:
            out, bas = baslik_isle(out)
            if bas:
                bx0, by0, bx1, by1 = BASLIK_BOLGE
                dis[by0:by1, bx0:bx1] = False
        assert np.array_equal(out[dis], im[dis])
        Image.fromarray(out.round().astype(np.uint8)).save(os.path.join(cdir, f.replace('.jpg', ek)), quality=95, subsampling=0)
        R[f] = {'posterler': r, 'baslik': bas}
        for k in r:
            print(f, k['zemin'], {a: (v['IoU'], v['olcek']) if isinstance(v, dict) else v for a, v in k['ogeler'].items()})
        if TUM:
            print(f, 'baslik', bas)
    json.dump(R, open(os.path.join(cdir, 'OLCUM_TUM.json' if TUM else 'OLCUM_PIN.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
