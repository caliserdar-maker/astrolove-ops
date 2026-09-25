"""Kisiye ozel A6 kartpostal (siparis onay akisi, Serdar 25 Eyl 2026).

Kaynak: video-v1 scripts/video_v1/kartpostal_ornek.py (2d94393, QC PASS). Oradaki ornek script cagrilabilir
fonksiyona tasindi; olculen sabitler, cizim ve QC kapilari AYNEN korunur (esdegerlik: ayni girdide piksel ayni cikti).
Girdi: kaynak kart (Drive BRAND/INSERTS/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg), ciftin medya
onayli POSTER_AM.png'si (TEMP/POD_KISISEL/A1_77/<CIFT>), Cinzel.ttf (kisisel-v1 assets/fonts).
Cikti: 1240 x 1748 px, 300 dpi JPEG (A6 105 x 148 mm). Isim metni loga YAZILMAZ; QC raporunda da tutulmaz.

kartpostal_uret(kaynak, poster, font, metin, cikti) -> qc dict ({'PASS', 'kapilar', ...}).
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ZEMIN = np.array([6., 20., 46.])                       # olculen, std 0
CERCEVE = (76, 76, 1163, 1671)                         # olculen altin cerceve (x0, y0, x1, y1)
SUTUN = (169, 1066)                                    # govde metni sutunu (olculen) -> isim satiri azami eni
SONSUZ = (519, 244, 720, 305)                          # olculen sonsuz kutusu
TY = (361, 423)                                        # Thank you bandi
ALT_BAS = 456                                          # alt baslik ust siniri: buradan asagisi DOKUNULMAZ
IS_CAP = 32                                            # isim cap yuksekligi (px)
G_TY_IS, G_IS_ALT = 32, 44                             # Thank you alti -> isim cap ustu, isim tabani -> alt baslik
G_SEM_TY = 44                                          # sembol alti -> Thank you ustu
OLCU = (1240, 1748)                                    # A6 @ 300 dpi


def murekkep(a, z, esik=40):
    return np.abs(a - z).max(2) > esik


def sembol_kutusu(P, pay=60):
    """Birlesik sembolun poster kutusu (x0, y0, x1, y1), sabit kutu yerine OLCULUR (25 Eyl, video bulgusu:
    sabit x 700-1700 genis sembollerde, or. SAGITTARIUS_SAGITTARIUS, kirpiyordu). Yontem video referans
    olcumuyle ayni: halka (en genis bilesen) cembere oturtulur; halka ici + halka tabaninin ustundeki
    buyuk bilesenler (>= %5) = sembol maskesi; kutu = maske sinirlari + pay."""
    pz = np.median(P[60:260, 1100:1300].reshape(-1, 3), 0)
    m = np.abs(P - pz).max(2) > 60
    m[:200] = False; m[2100:] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0).astype(np.uint8))
    h = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_WIDTH])
    ys, xs = np.where((lab == h) & m)
    cx, cy, c = np.linalg.lstsq(np.c_[2 * xs, 2 * ys, np.ones(len(xs))], xs ** 2 + ys ** 2, rcond=None)[0]
    R = np.sqrt(c + cx ** 2 + cy ** 2); alt = ys.max()
    yy, xx = np.mgrid[0:P.shape[0], 0:P.shape[1]]
    ic = m & (np.hypot(xx - cx, yy - cy) < R - 25)
    n, lab, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(ic.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0).astype(np.uint8))
    ad = [i for i in range(1, n) if st[i, cv2.CC_STAT_TOP] < alt - 100]
    if not ad:
        raise RuntimeError('sembol bulunamadi (halka ici bos)')
    enb = max(st[i, cv2.CC_STAT_AREA] for i in ad)
    sm = np.isin(lab, [i for i in ad if st[i, cv2.CC_STAT_AREA] >= 0.05 * enb]) & m
    ys, xs = np.where(sm)
    H, W = P.shape[:2]
    return (max(int(xs.min()) - pay, 0), max(int(ys.min()) - pay, 0), min(int(xs.max()) + 1 + pay, W), min(int(ys.max()) + 1 + pay, H))


class Kartpostal:
    """Kaynak kart + poster bir kez hazirlanir; uret() her isim icin kart cizer."""

    def __init__(self, kaynak, poster, font):
        self.font = str(font)
        self.K = np.asarray(Image.open(kaynak).convert('RGB')).astype(np.float64)
        self.H, self.W = self.K.shape[:2]
        # ------------------------------------------------ poster: birlesik sembol + isim altin profili
        P = np.asarray(Image.open(poster).convert('RGB')).astype(np.float64)
        pz = np.median(P[2150:2350, 1300:1500].reshape(-1, 3), 0)
        bx = sembol_kutusu(P)                          # sabit (700,640,1700,1700) degil: halka ici sembol maskesinden
        self.sembol_kutu_poster = list(bx)
        kes = P[bx[1]:bx[3], bx[0]:bx[2]]
        m = murekkep(kes, pz, 60)
        lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=3))
        al = np.bincount(lab.ravel()); al[0] = 0
        buyuk = al.argmax(); tut = [i for i in range(1, n + 1) if al[i] >= 0.05 * al[buyuk]]
        sm = np.isin(lab, tut) & m
        ys, xs = np.where(sm); sb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        pad = 24
        x0, y0, x1, y1 = sb[0] - pad, sb[1] - pad, sb[2] + pad, sb[3] + pad
        I = kes[y0:y1, x0:x1]
        mk = ndimage.binary_dilation(sm[y0:y1, x0:x1], iterations=8)
        zem = cv2.inpaint(np.clip(I, 0, 255).astype(np.uint8), mk.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA).astype(np.float64)
        d = np.abs(I - zem).max(2)
        cek = np.percentile(d[sm[y0:y1, x0:x1]], 95)
        A = np.clip(d / cek, 0, 1) * ndimage.binary_dilation(sm[y0:y1, x0:x1], iterations=4)
        F = np.where(A[..., None] > 0.02, (I - zem * (1 - A[..., None])) / np.maximum(A[..., None], 0.02), I)
        F = np.clip(F, 0, 255)
        ys, xs = np.where(A > 0.3); kb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        self.F, self.A = F[kb[1]:kb[3], kb[0]:kb[2]], A[kb[1]:kb[3], kb[0]:kb[2]]
        self.sem_poster_wh = (self.A.shape[1], self.A.shape[0])

        nb = (450, 2150, 1250, 2350)
        nk = P[nb[1]:nb[3], nb[0]:nb[2]]; nm = murekkep(nk, pz, 60)
        ys, xs = np.where(nm); ist = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        prof = []
        for r in range(ist[1], ist[3]):
            px = nk[r][nm[r]]
            prof.append(np.median(px, 0) if len(px) else [np.nan] * 3)
        prof = np.array(prof, float)
        ok = ~np.isnan(prof[:, 0]); idx = np.arange(len(prof))
        self.prof = np.stack([np.interp(idx, idx[ok], prof[ok, c]) for c in range(3)], 1)
        poster_isim_cap = ist[3] - ist[1]                  # poster ismi: inen harf yok -> ink yuksekligi = cap
        # harf araligi: posterdeki isim genisligine esle (kisisel tracking mantigi; ornekteki ALEXANDER olcumu)
        pb = self.cap_boy(poster_isim_cap)
        lo, hi = -0.2 * pb, 0.6 * pb
        for _ in range(40):
            mid = (lo + hi) / 2
            if self.gen_olc(self.ciz('ALEXANDER', pb, mid)[0]) < ist[2] - ist[0]:
                lo = mid
            else:
                hi = mid
        self.TR_ORAN = mid / pb

    # ------------------------------------------------ yazi
    def font_yukle(self, boy):
        f = ImageFont.truetype(self.font, boy); f.set_variation_by_axes([500]); return f

    def ciz(self, metin, boy, tr):
        f = self.font_yukle(boy); gen = sum(f.getlength(c) for c in metin) + abs(tr) * len(metin)
        im = Image.new('L', (int(gen) + 4 * boy, 3 * boy), 0); dr = ImageDraw.Draw(im); x = 2 * boy
        for c in metin:
            dr.text((x, boy), c, font=f, fill=255, anchor='ls'); x += f.getlength(c) + (0 if c == ' ' else tr)
        return np.asarray(im).astype(np.float64) / 255, boy

    def cap_boy(self, hedef):
        for boy in range(8, 400):
            f = self.font_yukle(boy); b = f.getbbox('H', anchor='ls')
            if -b[1] >= hedef:
                return boy
        raise RuntimeError('cap boyu bulunamadi')

    @staticmethod
    def gen_olc(a):
        xs = np.where(a.max(0) > 0.5)[0]; return xs.max() - xs.min() + 1

    def isim_katman(self, metin):
        boy = self.cap_boy(IS_CAP); tam = boy; olcek = 1.0
        maks = SUTUN[1] - SUTUN[0] + 1
        while True:
            a, taban = self.ciz(metin, boy, boy * self.TR_ORAN)
            w = self.gen_olc(a)
            if w <= maks:
                break
            boy -= 1; olcek = boy / tam
        cap = -self.font_yukle(boy).getbbox('H', anchor='ls')[1]
        ys, xs = np.where(a > 0.01); a = a[:, xs.min():xs.max() + 1]
        rgb = np.zeros(a.shape + (3,))
        for r in range(a.shape[0]):
            t = (r - (taban - cap)) / max(cap - 1, 1)
            k = int(round(np.clip(t, 0, 1) * (len(self.prof) - 1))); rgb[r] = self.prof[k]
        return a, rgb, taban, cap, boy, olcek, w

    # ------------------------------------------------ kart
    def kart(self, metin):
        C = self.K.copy()
        is_ust = ALT_BAS - G_IS_ALT - IS_CAP
        D = is_ust - G_TY_IS - TY[1]
        blok = C[TY[0] - 2:TY[1] + 2, CERCEVE[0] + 4:CERCEVE[2] - 3].copy()
        C[SONSUZ[1] - 4:TY[1] + 2, CERCEVE[0] + 4:CERCEVE[2] - 3] = ZEMIN
        C[TY[0] - 2 + D:TY[1] + 2 + D, CERCEVE[0] + 4:CERCEVE[2] - 3] = blok
        alan = (SONSUZ[2] - SONSUZ[0]) * (SONSUZ[3] - SONSUZ[1])
        sw, sh = self.sem_poster_wh; s = (alan / (sw * sh)) ** 0.5
        nw, nh = round(sw * s), round(sh * s)
        Fi = np.asarray(Image.fromarray(self.F.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)
        Ai = np.asarray(Image.fromarray((self.A * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)[..., None] / 255
        cx = (SONSUZ[0] + SONSUZ[2]) / 2; sx = int(round(cx - nw / 2)); sy = TY[0] + D - G_SEM_TY - nh
        C[sy:sy + nh, sx:sx + nw] = C[sy:sy + nh, sx:sx + nw] * (1 - Ai) + Fi * Ai
        a, rgb, taban, cap, boy, olcek, w = self.isim_katman(metin)
        ix = int(round(self.W / 2 - a.shape[1] / 2)); iy = is_ust + cap - taban
        Aa = a[..., None]
        y0, y1 = max(iy, 0), iy + a.shape[0]
        C[y0:y1, ix:ix + a.shape[1]] = C[y0:y1, ix:ix + a.shape[1]] * (1 - Aa[y0 - iy:]) + rgb[y0 - iy:] * Aa[y0 - iy:]
        bilgi = {'punto': boy, 'olcek': round(olcek, 3), 'isim_en_px': int(w), 'isim_azami_en_px': SUTUN[1] - SUTUN[0] + 1,
                 'isim_x': [ix, ix + a.shape[1]], 'isim_cap_ust_taban': [is_ust, is_ust + cap], 'ust_blok_kayma_px': D,
                 'sembol_kutu': [sx, sy, sx + nw, sy + nh], 'sembol_alan_px2': nw * nh, 'sonsuz_alan_px2': alan}
        return C, bilgi

    @staticmethod
    def bantlar(a):
        m = murekkep(a, ZEMIN)[CERCEVE[1] + 4:CERCEVE[3] - 3, CERCEVE[0] + 4:CERCEVE[2] - 3]
        r = np.where(m.any(1))[0] + CERCEVE[1] + 4; b = []; s = p = r[0]
        for x in r[1:]:
            if x > p + 1:
                b.append((int(s), int(p))); s = x
            p = x
        return b + [(int(s), int(p))]

    def uret(self, metin, cikti):
        """Karti cizer, JPEG yazar, QC kapilarini olcer. Donen dict isim metnini ICERMEZ."""
        C, b = self.kart(metin)
        C8 = np.clip(np.round(C), 0, 255).astype(np.uint8)
        yol = Path(cikti); yol.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(C8).save(yol, quality=95, subsampling=0, dpi=(300, 300))
        J = np.asarray(Image.open(yol)).astype(np.float64)
        alt_fark_ham = float(np.abs(C8[ALT_BAS - 2:].astype(np.float64) - self.K[ALT_BAS - 2:]).max())
        alt_fark_jpg = float(np.abs(J[ALT_BAS - 2:] - self.K[ALT_BAS - 2:]).mean())
        bn = self.bantlar(C8.astype(np.float64)); yb = [x for x in bn if x[0] < ALT_BAS] + [x for x in bn if x[0] >= ALT_BAS][:1]
        bosluk = min(yb[i + 1][0] - yb[i][1] - 1 for i in range(len(yb) - 1))
        ic = b['isim_x'][0] >= SUTUN[0] and b['isim_x'][1] <= SUTUN[1] + 1
        im = Image.open(yol)
        kapilar = {
            'olcu_1240x1748_300dpi': im.size == OLCU and round(im.info.get('dpi', (0,))[0]) == 300,
            'isim_tek_satir_sutun_ici': ic and b['isim_en_px'] <= b['isim_azami_en_px'],
            'sembol_alan_orani_%5': abs(b['sembol_alan_px2'] / b['sonsuz_alan_px2'] - 1) <= 0.05,
            'sembol_cerceve_payi>=40': b['sembol_kutu'][1] - CERCEVE[1] >= 40,
            'yeni_bantlar_arasi_bosluk>=20': bosluk >= 20,
            'alt_bolge_ham_fark=0': alt_fark_ham == 0,
            'alt_bolge_jpg_ort_fark<1': alt_fark_jpg < 1.0,
        }
        kapilar = {k: bool(v) for k, v in kapilar.items()}
        b.update({'min_bant_boslugu': int(bosluk), 'alt_fark_ham_max': alt_fark_ham, 'alt_fark_jpg_ort': round(alt_fark_jpg, 3),
                  'kapilar': kapilar, 'PASS': all(kapilar.values())})
        return b


def kart_metni(isim1, isim2):
    """Kartta tek satir: 'ISIM1 & ISIM2' (basilacak buyuk harfli bicim, kisisel_siparis ciktisi)."""
    return f"{isim1} & {isim2}" if isim2 else f"{isim1}"


def kartpostal_uret(kaynak, poster, font, metin, cikti):
    return Kartpostal(kaynak, poster, font).uret(metin, cikti)
