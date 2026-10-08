# Tagline dizgisi, ChatGPT "&" ile (8 Eki 2026, Serdar onayli ornek: Test 6 "Quietly Yours, Forever & Always").
# Kurallar (onayli ornekten):
#   - her "&" yerine ChatGPT & (amp/AMP_ALFA.png + AMP_YUZEY.png); murekkep yuksekligi = ayni puntoda "A" buyuk harf yuksekligi
#   - & ile komsu kelime arasi murekkep boslugu: onayli ornegin olcum yontemi. & yerinde "and" olsaydi komsu kelimelerle
#     olacak murekkep bosluklari ("<onceki kelime> and <sonraki kelime>" cizilir, iki bosluk olculur), ortalamasi her iki yana.
#     Test 6'da 58 / 51 -> 54 px (onayli ornek). Komsu kelime yoksa (satir basi/sonu) yalniz olan yan; hic yoksa "Forever and Always".
#     NOT: tagline'in kendi kelime bosluklari murekkep olcusuyle harf bicimine cok bagli (Test 6: 115 / 105 px), & cok acik kaliyordu.
#   - taban cizgisi diger harflerle ayni (& murekkep alti = taban); birden cok & olabilir
#   - satir genisligi W - 2*KENAR'i asarsa punto 4'er kuculur (sablon ile ayni kural)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
W_POSTER, KENAR, TAG_PUNTO, TABAN_TAG, ORTA = 7200, 700, 372, 9271, 3600

def amp_yukle(B):
    A = np.asarray(Image.open(B + 'amp/AMP_ALFA.png')).astype(np.float32) / 65535
    G = np.asarray(Image.open(B + 'amp/AMP_YUZEY.png').convert('RGB')).astype(np.float32) / 255
    return A, G

def _font(FONT, tp):
    F = ImageFont.truetype(FONT + 'EBGaramond-Italic.ttf', tp); F.set_variation_by_axes([400]); return F

def _yaz(F, m):
    b = F.getbbox(m, anchor='ls'); im = Image.new('L', (b[2] - b[0] + 40, b[3] - b[1] + 40), 0)
    ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), m, font=F, fill=255, anchor='ls'); a = np.asarray(im)
    ys, xs = np.nonzero(a > 127); return a, int(xs.min()), int(xs.max()) + 1, 20 - b[1], int(ys.min())

def _bos_kosular(a):
    kol = (a > 127).any(0); k = np.r_[False, ~kol, False].astype(np.int8); d = np.diff(k)
    s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    ys, xs = np.nonzero(a > 127); x0, x1 = xs.min(), xs.max() + 1
    return [int(b - a_) for a_, b in zip(s, e) if a_ > x0 and b < x1]          # yalniz murekkep ARASI bosluklar

def kelime_bosluklari(F, parca):
    n = parca.count(' ')
    if n == 0: return []
    r = sorted(_bos_kosular(_yaz(F, parca)[0]), reverse=True)[:n]
    return [x for x in r if x >= 0.05 * F.size]

def amp_olcekli(A, G, cap):
    ys, xs = np.nonzero(A > 0.5); h = ys.max() + 1 - ys.min(); s = cap / h
    hh, ww = int(round(A.shape[0] * s)), int(round(A.shape[1] * s))
    As = cv2.resize(A, (ww, hh), interpolation=cv2.INTER_AREA)
    Gs = cv2.resize(G * A[..., None], (ww, hh), interpolation=cv2.INTER_AREA) / np.maximum(As, 1e-4)[..., None]
    A8 = np.round(As * 255).astype(np.uint8); G8 = np.clip(np.round(Gs * 255), 0, 255).astype(np.uint8)
    ys, xs = np.nonzero(A8 > 127)
    return A8, G8, (int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1), round(float(s), 4), int(h)

def dizgi(tag, FONT, A, G):
    """-> dict(alfa, x, y, ampler=[dict(x, y, alfa, yuzey)], olcu) ; x, y poster koordinati (alfa sol-ust)."""
    parcalar = [p.strip() for p in tag.split('&')]
    tp = TAG_PUNTO
    while True:
        F = _font(FONT, tp)
        a_A = _yaz(F, 'A'); cap = a_A[3] - a_A[4]
        gaps, bos_kay = [], []
        for i in range(len(parcalar) - 1):
            once = parcalar[i].split()[-1] if parcalar[i] else ''; sonra = parcalar[i + 1].split()[0] if parcalar[i + 1] else ''
            if not once and not sonra: once, sonra = 'Forever', 'Always'
            m = ' '.join(x for x in (once, 'and', sonra) if x)
            r = sorted(_bos_kosular(_yaz(F, m)[0]), reverse=True)[:int(bool(once)) + int(bool(sonra))]
            gaps.append(int(round(float(np.mean(r))))); bos_kay.append(dict(metin=m, bosluklar=[int(x) for x in r]))
        A8, G8, ink, s, h_src = amp_olcekli(A, G, cap)
        dizi = []                                                   # ('metin', yaz) | ('amp', None), bos parca atlanir
        for i, p in enumerate(parcalar):
            if p: dizi.append(('metin', _yaz(F, p)))
            if i < len(parcalar) - 1: dizi.append(('amp', None))
        gen = [(r[2] - r[1]) if t == 'metin' else (ink[1] - ink[0]) for t, r in dizi]
        ara, k = [], 0                                              # her eleman arasi bosluk: & komsulugunda o &'in boslugu
        for j in range(len(dizi) - 1):
            if dizi[j][0] == 'amp': ara.append(gaps[k]); k += 1
            elif dizi[j + 1][0] == 'amp': ara.append(gaps[k])
            else: ara.append(gaps[k])
        top = sum(gen) + sum(ara)
        if top <= W_POSTER - 2 * KENAR or tp <= 200: break
        tp -= 4
    x = int(round(ORTA - top / 2))
    yuk = max([r[0].shape[0] for t, r in dizi if t == 'metin'] + [A8.shape[0]]) + 400
    tuval = np.zeros((yuk, top + 400), np.uint8); taban = yuk - 150
    ampler, xi = [], 0
    for j, ((t, r), w_) in enumerate(zip(dizi, gen)):
        if t == 'metin':
            a, il, ir, tb, _ = r; y0, x0 = taban - tb, xi - il + 200
        else:
            a = A8; y0, x0 = taban - ink[3], xi - ink[0] + 200
            ampler.append(dict(tx=x0, ty=y0))
        sl = tuval[y0:y0 + a.shape[0], x0:x0 + a.shape[1]]; np.maximum(sl, a, out=sl)
        xi += w_ + (ara[j] if j < len(ara) else 0)
    yy, xx = np.nonzero(tuval > 0); ty0, tx0 = yy.min() - 8, xx.min() - 8
    alfa = tuval[ty0:yy.max() + 9, tx0:xx.max() + 9].copy()
    px, py = x - 200 + tx0, TABAN_TAG - taban + ty0                # tuval (u, v) -> poster (x - 200 + u, TABAN - taban + v)
    for a_ in ampler:
        a_.update(x=int(x - 200 + a_['tx']), y=int(TABAN_TAG - taban + a_['ty']), alfa=A8, yuzey=G8)
    olcu = dict(punto=tp, buyuk_harf_yuksekligi_px=int(cap), amp_yukseklik_px=ink[3] - ink[2], amp_genislik_px=ink[1] - ink[0],
                amp_olcek=s, amp_kaynak_yukseklik_px=h_src, amp_bosluklari_px=gaps, bosluk_olcumu=bos_kay, amp_sayisi=len(ampler), satir_genisligi_px=int(top))
    return dict(alfa=alfa, x=int(px), y=int(py), ampler=ampler, olcu=olcu)
