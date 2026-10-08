# ChatGPT ogeler atlasi (8 Eki 2026): kucuk burc sembolleri, sonsuz, isim harfleri (Cinzel 500), tagline harfleri
# (EB Garamond Italic). Motorla posterdeki AYNI boyda cizilir, ChatGPT'ye gidecek paftalar kesilir.
# Cikti: atlas/<tur>_alfa.npz (motor girdisi), atlas/atlas.json (glif/sembol konumlari, pafta kutulari)
# Kullanim: python atlas_yap.py
import os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
B = '/home/claude/blender/'; G = B + 'girdi/'; FONT = '/home/claude/motor_klon/motor/font/'
O = B + 'atlas/'; os.makedirs(O, exist_ok=True)
W, H = 7200, 10800
KUCUK = {'AQUARIUS': ('KUCUK_1', [1095, 219, 2010, 600]), 'ARIES': ('KUCUK_1', [2257, 102, 2917, 717]),
         'CANCER': ('KUCUK_1', [175, 933, 859, 1527]), 'CAPRICORN': ('KUCUK_1', [1200, 880, 1905, 1580]),
         'GEMINI': ('KUCUK_1', [2285, 923, 2889, 1537]), 'LEO': ('KUCUK_1', [254, 1743, 781, 2357]),
         'LIBRA': ('KUCUK_2', [1001, 94, 1822, 709]), 'PISCES': ('KUCUK_2', [2023, 95, 2682, 708]),
         'SAGITTARIUS': ('KUCUK_2', [217, 875, 723, 1533]), 'SCORPIO': ('KUCUK_2', [1038, 897, 1784, 1512]),
         'TAURUS': ('KUCUK_2', [2045, 898, 2659, 1510]), 'VIRGO': ('KUCUK_2', [130, 1666, 811, 2349])}
import sys; sys.path.insert(0, B)
from alfa_temizle import temizle
def kirp(a):
    ys, xs = np.nonzero(a > 8); return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

BUYUK = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜÄÅÆÉÈÊËÁÀÂÃÍÌÎÏÑÓÒÔÕØÚÙÛÝŸ&'
ITALIK = ('abcdefghijklmnopqrstuvwxyz' 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' "çğıöşüéèêëáàâãíìîïñóòôõøúùûåæœß" ",.'’!?&:;\"“”()")
J = dict(paftalar=[], glif={}, sembol={})

def sayfa(tur, ogeler, paftalar):
    """ogeler: [(ad, x, y, alfa)], paftalar: [(ad, x0, y0, x1, y1)]"""
    np.savez_compressed(f'{O}{tur}_alfa.npz', **{a: al for a, _, _, al in ogeler},
                        _konum=np.array([[x, y] for _, x, y, _ in ogeler]), _ad=np.array([a for a, *_ in ogeler]))
    for p in paftalar: J['paftalar'].append(dict(tur=tur, ad=p[0], kutu=list(map(int, p[1:]))))

def glif_sayfasi(tur, karakterler, fontad, punto, hucre_w, satir_h, sutun, satir_pafta, x0=300, y0=500):
    F = ImageFont.truetype(FONT + fontad, punto)
    try: F.set_variation_by_axes([500 if 'Cinzel' in fontad else 400])
    except Exception: pass
    ogeler, paftalar = [], []
    satirlar = [karakterler[i:i + sutun] for i in range(0, len(karakterler), sutun)]
    for si, s in enumerate(satirlar):
        taban = y0 + si * satir_h + int(satir_h * 0.72)
        al = Image.new('L', (W, satir_h), 0); d = ImageDraw.Draw(al)
        for ci, ch in enumerate(s):
            cx = x0 + ci * hucre_w + hucre_w // 2
            w = F.getlength(ch); px = cx - w / 2                               # kalem baslangici
            d.text((px, taban - (y0 + si * satir_h)), ch, font=F, fill=255, anchor='ls')
            J['glif'][f'{tur}|{ch}'] = dict(tur=tur, font=fontad, punto=punto, kalem_x=px, taban_y=taban,
                                           kutu=[int(cx - hucre_w / 2), y0 + si * satir_h, int(cx + hucre_w / 2), y0 + (si + 1) * satir_h])
        a = np.asarray(al)
        ad = 'ana' if si == 0 else f'r{si}'                                     # motor olcumu 'ana' adini bekliyor
        ogeler.append((ad, 0, y0 + si * satir_h, a))
    for pi in range(0, len(satirlar), satir_pafta):
        n = min(satir_pafta, len(satirlar) - pi)
        paftalar.append((f'{tur}_{pi // satir_pafta + 1}', x0 - 60, y0 + pi * satir_h, x0 + sutun * hucre_w + 60, y0 + (pi + n) * satir_h))
    sayfa(tur, ogeler, paftalar)

# --- isim harfleri (posterde Cinzel 500, punto 405) ---
glif_sayfasi('buyuk', BUYUK, 'Cinzel.ttf', 405, 470, 560, 7, 5)
# --- tagline harfleri (EB Garamond Italic 372) ---
glif_sayfasi('italik', ITALIK, 'EBGaramond-Italic.ttf', 372, 380, 520, 8, 5)

# --- kucuk semboller + sonsuz (posterdeki kaynakla AYNI piksel boyu, ayni temizlik) ---
ogeler, paftalar = [], []
hucre = 900; x0, y0 = 300, 400
burclar = list(KUCUK)
for i, b in enumerate(burclar):
    s_, kk = KUCUK[b]
    k = kirp(np.asarray(Image.open(G + s_ + '.png').convert('L')).astype(np.float32)[kk[1]:kk[3], kk[0]:kk[2]])
    k8, _ = temizle(np.pad(np.clip(k, 0, 255).astype(np.uint8), 40))
    pi, j = divmod(i, 4); r, c = divmod(j, 2)
    bx = x0 + (pi % 3) * 2 * hucre + c * hucre + (hucre - k8.shape[1]) // 2
    by = y0 + r * hucre + (hucre - k8.shape[0]) // 2 + (0 if pi < 3 else 0)
    by += 0
    ad = 'ana' if i == 0 else f's_{b}'
    ogeler.append((ad, bx, by, k8))
    J['sembol'][b] = dict(oge=ad, x=int(bx), y=int(by), h=int(k8.shape[0]), w=int(k8.shape[1]))
for pi in range(3):
    paftalar.append((f'sembol_{pi + 1}', x0 + pi * 2 * hucre - 30, y0 - 30, x0 + pi * 2 * hucre + 2 * hucre + 30, y0 + 2 * hucre + 30))
# sonsuz: posterdeki LOGO_1 kirpimi, olcek 0.994
lg = kirp(np.asarray(Image.open(G + 'LOGO_1.png').convert('L'))[192:388, 760:1396].astype(np.float32))
lg = cv2.resize(lg, None, fx=0.994, fy=0.994, interpolation=cv2.INTER_AREA)
lg8, _ = temizle(np.pad(np.clip(lg, 0, 255).astype(np.uint8), 40))
sx, sy = 300 + (900 - lg8.shape[1]) // 2 + 600, y0 + 2 * hucre + 600
ogeler.append(('s_SONSUZ', sx, sy, lg8))
J['sembol']['SONSUZ'] = dict(oge='s_SONSUZ', x=int(sx), y=int(sy), h=int(lg8.shape[0]), w=int(lg8.shape[1]))
paftalar.append(('sonsuz', sx - 250, sy - 330, sx + lg8.shape[1] + 250, sy + lg8.shape[0] + 330))
sayfa('sembol', ogeler, paftalar)
json.dump(J, open(O + 'atlas.json', 'w'), ensure_ascii=False, indent=1)
print('paftalar', [(p['ad'], p['kutu']) for p in J['paftalar']])
print('glif', len(J['glif']), 'sembol', len(J['sembol']))
