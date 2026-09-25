"""Kisiye ozel A6 kartpostal ORNEGI (uretim akisina bagli DEGIL).
Kaynak kart: Drive BRAND/INSERTS/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg (B99: Prodigi Branding panelindeki kart;
order_router kart dosyasi secmez, ek hesap ayarindan gelir).
Sembol: medya onayli POSTER_AM.png (A1_77/<CIFT>), birlesik sembol katmani ayristirilir (alfa + renk, zemin inpaint).
Isim: Cinzel wght 500, harf araligi posterdeki isimden olculur, altin = poster isminin satir profili (kisisel altin() mantigi).
Degisen: yalniz ust blok (sembol + Thank you) yukari kayar, isim satiri araya girer; alt baslik ve altindaki her piksel AYNEN.
argv: KAYNAK.jpg POSTER_AM.png Cinzel.ttf CIKTI_DIR"""
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

kaynak, poster, font, out = sys.argv[1:5]
out = Path(out); out.mkdir(parents=True, exist_ok=True)
K = np.asarray(Image.open(kaynak).convert('RGB')).astype(np.float64)
H, W = K.shape[:2]
ZEMIN = np.array([6., 20., 46.])                       # olculen, std 0
CERCEVE = (76, 76, 1163, 1671)                         # olculen altin cerceve (x0, y0, x1, y1)
SUTUN = (169, 1066)                                    # govde metni sutunu (olculen) -> isim satiri azami eni
SONSUZ = (519, 244, 720, 305)                          # olculen ∞ kutusu
TY = (361, 423)                                        # Thank you bandi
ALT_BAS = 456                                          # alt baslik ust siniri: buradan asagisi DOKUNULMAZ
IS_CAP = 32                                            # isim cap yuksekligi (px)
G_TY_IS, G_IS_ALT = 32, 44                             # Thank you alti -> isim cap ustu, isim tabani -> alt baslik
G_SEM_TY = 44                                          # sembol alti -> Thank you ustu (orijinal ∞ boslugu 56; cerceve payi icin)

def murekkep(a, z, esik=40):
    return np.abs(a - z).max(2) > esik

# ---------------------------------------------------------------- poster: birlesik sembol + isim altin profili
P = np.asarray(Image.open(poster).convert('RGB')).astype(np.float64)
pz = np.median(P[2150:2350, 1300:1500].reshape(-1, 3), 0)
bx = (700, 640, 1700, 1700)
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
F, A = F[kb[1]:kb[3], kb[0]:kb[2]], A[kb[1]:kb[3], kb[0]:kb[2]]
sem_poster_wh = (A.shape[1], A.shape[0])

nb = (450, 2150, 1250, 2350)
nk = P[nb[1]:nb[3], nb[0]:nb[2]]; nm = murekkep(nk, pz, 60)
ys, xs = np.where(nm); ist = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
prof = []
for r in range(ist[1], ist[3]):
    px = nk[r][nm[r]]
    prof.append(np.median(px, 0) if len(px) else [np.nan] * 3)
prof = np.array(prof, float)
ok = ~np.isnan(prof[:, 0]); idx = np.arange(len(prof))
prof = np.stack([np.interp(idx, idx[ok], prof[ok, c]) for c in range(3)], 1)
poster_isim_cap = ist[3] - ist[1]                      # ALEXANDER: inen harf yok -> ink yuksekligi = cap

def font_yukle(boy):
    f = ImageFont.truetype(font, boy); f.set_variation_by_axes([500]); return f

def ciz(metin, boy, tr):
    f = font_yukle(boy); gen = sum(f.getlength(c) for c in metin) + abs(tr) * len(metin)
    im = Image.new('L', (int(gen) + 4 * boy, 3 * boy), 0); dr = ImageDraw.Draw(im); x = 2 * boy
    for c in metin:
        dr.text((x, boy), c, font=f, fill=255, anchor='ls'); x += f.getlength(c) + (0 if c == ' ' else tr)   # bosluk daraltilmaz
    return np.asarray(im).astype(np.float64) / 255, boy        # taban cizgisi satiri = boy

def cap_boy(hedef):
    for boy in range(8, 400):
        f = font_yukle(boy); b = f.getbbox('H', anchor='ls')
        if -b[1] >= hedef: return boy
    raise RuntimeError

# harf araligi: posterdeki ALEXANDER genisligine esle (kisisel tracking_icin mantigi)
pb = cap_boy(poster_isim_cap)
def gen_olc(a):
    xs = np.where(a.max(0) > 0.5)[0]; return xs.max() - xs.min() + 1
lo, hi = -0.2 * pb, 0.6 * pb
for _ in range(40):
    mid = (lo + hi) / 2
    if gen_olc(ciz('ALEXANDER', pb, mid)[0]) < ist[2] - ist[0]: lo = mid
    else: hi = mid
TR_ORAN = mid / pb

def isim_katman(metin):
    boy = cap_boy(IS_CAP); tam = boy; olcek = 1.0
    maks = SUTUN[1] - SUTUN[0] + 1
    while True:
        a, taban = ciz(metin, boy, boy * TR_ORAN)
        w = gen_olc(a)
        if w <= maks: break
        boy -= 1; olcek = boy / tam
    cap = -font_yukle(boy).getbbox('H', anchor='ls')[1]
    ys, xs = np.where(a > 0.01); a = a[:, xs.min():xs.max() + 1]
    # altin: poster isim profili, cap kutusuna gerilir (cap ustu -> taban); inen kisim son satir rengi
    rgb = np.zeros(a.shape + (3,))
    for r in range(a.shape[0]):
        t = (r - (taban - cap)) / max(cap - 1, 1)
        k = int(round(np.clip(t, 0, 1) * (len(prof) - 1))); rgb[r] = prof[k]
    return a, rgb, taban, cap, boy, olcek, w

# ---------------------------------------------------------------- kart
def kart(metin):
    C = K.copy()
    # isim satiri yerlesimi -> ust blok kaymasi
    is_ust = ALT_BAS - G_IS_ALT - IS_CAP
    D = is_ust - G_TY_IS - TY[1]                        # negatif = yukari
    blok = C[TY[0] - 2:TY[1] + 2, CERCEVE[0] + 4:CERCEVE[2] - 3].copy()
    C[SONSUZ[1] - 4:TY[1] + 2, CERCEVE[0] + 4:CERCEVE[2] - 3] = ZEMIN   # ∞ + Thank you silinir (alt baslik ustu)
    C[TY[0] - 2 + D:TY[1] + 2 + D, CERCEVE[0] + 4:CERCEVE[2] - 3] = blok
    # sembol: ∞ kutusu ALANI kadar (en-boy orani korunur), yatay merkez ayni, alt kenar ∞ alt kenari + D
    alan = (SONSUZ[2] - SONSUZ[0]) * (SONSUZ[3] - SONSUZ[1])
    sw, sh = sem_poster_wh; s = (alan / (sw * sh)) ** 0.5
    nw, nh = round(sw * s), round(sh * s)
    Fi = np.asarray(Image.fromarray(F.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)
    Ai = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)[..., None] / 255
    cx = (SONSUZ[0] + SONSUZ[2]) / 2; sx = int(round(cx - nw / 2)); sy = TY[0] + D - G_SEM_TY - nh
    C[sy:sy + nh, sx:sx + nw] = C[sy:sy + nh, sx:sx + nw] * (1 - Ai) + Fi * Ai
    # isim
    a, rgb, taban, cap, boy, olcek, w = isim_katman(metin)
    ix = int(round(W / 2 - a.shape[1] / 2)); iy = is_ust + cap - taban   # cap ustu = is_ust
    Aa = a[..., None]
    y0, y1 = max(iy, 0), iy + a.shape[0]
    C[y0:y1, ix:ix + a.shape[1]] = C[y0:y1, ix:ix + a.shape[1]] * (1 - Aa[y0 - iy:]) + rgb[y0 - iy:] * Aa[y0 - iy:]
    bilgi = {'metin': metin, 'punto': boy, 'olcek': round(olcek, 3), 'isim_en_px': int(w), 'isim_azami_en_px': SUTUN[1] - SUTUN[0] + 1,
             'isim_x': [ix, ix + a.shape[1]], 'isim_cap_ust_taban': [is_ust, is_ust + cap], 'ust_blok_kayma_px': D,
             'sembol_kutu': [sx, sy, sx + nw, sy + nh], 'sembol_alan_px2': nw * nh, 'sonsuz_alan_px2': alan}
    return C, bilgi

def bantlar(a):
    m = murekkep(a, ZEMIN)[CERCEVE[1] + 4:CERCEVE[3] - 3, CERCEVE[0] + 4:CERCEVE[2] - 3]
    r = np.where(m.any(1))[0] + CERCEVE[1] + 4; b = []; s = p = r[0]
    for x in r[1:]:
        if x > p + 1: b.append((int(s), int(p))); s = x
        p = x
    return b + [(int(s), int(p))]

rapor = {'tr_orani': round(TR_ORAN, 4), 'poster_sembol_px': list(map(int, sem_poster_wh)), 'kart': {}}
ciktilar = {}
for ad, metin in (('EMILY_JAMES', 'EMILY & JAMES'), ('UZUN_ISIM', 'MAXIMILIANA & CHRISTOPHER')):
    C, b = kart(metin)
    C8 = np.clip(np.round(C), 0, 255).astype(np.uint8)
    yol = out / f'KARTPOSTAL_A6_{ad}_1240x1748.jpg'
    Image.fromarray(C8).save(yol, quality=95, subsampling=0, dpi=(300, 300))
    J = np.asarray(Image.open(yol)).astype(np.float64)
    alt_fark_ham = float(np.abs(C8[ALT_BAS - 2:].astype(np.float64) - K[ALT_BAS - 2:]).max())
    alt_fark_jpg = float(np.abs(J[ALT_BAS - 2:] - K[ALT_BAS - 2:]).mean())
    bn = bantlar(C8.astype(np.float64)); yb = [x for x in bn if x[0] < ALT_BAS] + [x for x in bn if x[0] >= ALT_BAS][:1]
    bosluk = min(yb[i + 1][0] - yb[i][1] - 1 for i in range(len(yb) - 1))   # sembol, Thank you, isim, alt baslik
    ic = b['isim_x'][0] >= SUTUN[0] and b['isim_x'][1] <= SUTUN[1] + 1
    kapilar = {
        'olcu_1240x1748_300dpi': Image.open(yol).size == (1240, 1748) and Image.open(yol).info.get('dpi', (0,))[0] == 300,
        'isim_tek_satir_sutun_ici': ic and b['isim_en_px'] <= b['isim_azami_en_px'],
        'sembol_alan_orani_%5': abs(b['sembol_alan_px2'] / b['sonsuz_alan_px2'] - 1) <= 0.05,
        'sembol_cerceve_payi>=40': b['sembol_kutu'][1] - CERCEVE[1] >= 40,
        'yeni_bantlar_arasi_bosluk>=20': bosluk >= 20,
        'alt_bolge_ham_fark=0': alt_fark_ham == 0,
        'alt_bolge_jpg_ort_fark<1': alt_fark_jpg < 1.0,
    }
    b.update({'bantlar_ust5': bn[:5], 'min_bant_boslugu': int(bosluk), 'alt_fark_ham_max': alt_fark_ham,
              'alt_fark_jpg_ort': round(alt_fark_jpg, 3), 'kapilar': kapilar, 'PASS': all(kapilar.values())})
    rapor['kart'][ad] = b; ciktilar[ad] = C8

# yan yana: mevcut | EMILY & JAMES | uzun isim
ol = 0.5; w, h = int(W * ol), int(H * ol); g = 40; ust = 70
S = Image.new('RGB', (3 * w + 4 * g, h + ust + g), (236, 233, 226)); dr = ImageDraw.Draw(S)
lf = ImageFont.truetype(font, 30); lf.set_variation_by_axes([500])
for i, (et, a) in enumerate((('MEVCUT (V1)', K.astype(np.uint8)), ('EMILY & JAMES', ciktilar['EMILY_JAMES']),
                             ('UZUN ISIM', ciktilar['UZUN_ISIM']))):
    x = g + i * (w + g); S.paste(Image.fromarray(a).resize((w, h), Image.LANCZOS), (x, ust))
    dr.text((x + w / 2, ust / 2), et, font=lf, fill=(40, 40, 40), anchor='mm')
S.save(out / 'KARTPOSTAL_KARSILASTIRMA.jpg', quality=92)
rapor['PASS'] = all(k['PASS'] for k in rapor['kart'].values())
(out / 'KARTPOSTAL_qc.json').write_text(json.dumps(rapor, indent=1, ensure_ascii=False))
print(json.dumps(rapor, ensure_ascii=False))
