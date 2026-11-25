"""Pinterest 78 cift: POSTER pini (PIN_01 v6 kalibi) ve KART pini (PIN_02 v6 kalibi) ureticisi + QC (Merkez "BASLA" 25 Kas 2026).
Onayli v6 pinleri yalniz 4 ciftte var; 78 cift icin ayni yerlesim olculerek kurulur (CLAUDE.md: esik/yerlesim olcumle):
  POSTER: PIN_01 v6 sablonu (baslik bandi ve poster kutusu disi onayli piksel, olculdu: PIN_01 ile PIN_07 bu bolgede ayni);
    poster kutusu x148 y258 703x1054 (onayli GPT posterinin v6'ya oturmasi ort. fark 1.2, olcum); baslik "<A> & <B>" BUYUK HARF,
    TeX Gyre Pagella (Palatino klonu) 104 px (v6 genislik/yukseklik eslesmesi, olcum), genislik <= 922 px olana kadar kuculur.
  KART: PIN_02 v6 sablonu; 6 Kas galeri karti (r2, damga 20261106_090016, 3000x2250) 0.5975 olcekle x-396 kaymayla yerlesir
    (gliflar + egri + birlesik sembol; v6'ya ort. fark ~1, olcum); kartin kendi etiketleri silinir, burc adlari v6 gibi glif
    merkezine ortali, buyuk harf yuksekligi ~50 px yeniden yazilir. v6 etiket yazi tipi Segoe UI Semibold (Windows) bu ortamda yok;
    olcumle en yakin Open Sans SemiBold (wght 600, wdth 95; v6 etiketlerine ort. fark 13/255). Baslik "<A> + <B>" Pagella 99 px (poster 104.5; boy/renk/konum taramasi, olcum).
QC (kaydedilen JPEG uzerinde, PASS/FAIL): sablon bolgesi degismedi, kaynak gorsel dogru yerde, baslik kutusu ve yuksekligi,
  etiket kutulari kenar paylari ve aralik, poster rengi Midnight Blue (onayli GPT posterine gore).
Kullanim:
  python3 pin78_poster_kart_pin.py --tur poster --kaynak POSTER2000.jpg --a Cancer --b Leo --sablon PIN_01_v6.jpg --font_dir D --out o.jpg
  python3 pin78_poster_kart_pin.py --tur kart --kaynak r2_kart.jpg --a Cancer --b Leo --sablon PIN_02_v6.jpg --font_dir D --out o.jpg
  python3 pin78_poster_kart_pin.py --oz-test --girdi DIR --font_dir D   (DIR: PIN_01/02/07/08 v6, GPT posterleri, r2 kartlari)
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (244, 239, 233)
PAGELLA = '/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-regular.otf'
LACIVERT = (22, 38, 65)        # baslik rengi (v6 olcumu; kalibrasyon --oz-test ile)
ETIKET_RENK = (39, 32, 29)     # v6 etiket murekkep ortalamasi (olcum)
BASLIK_BANT = (30, 152)        # baslik satiri (altyazi 172-244 sablondan kalir)
BASLIK_MAX_W = 922             # PIN_03 v6 en genis baslik (SCORPIO & TAURUS, olcum)
P_KUTU = (148, 258, 703, 1054)
K_OLCEK, K_DX, K_DY = 0.5975, -396, 0
K_BANT = (290, 1180)           # karttan alinan bolge (pin y)
ETK_BANT = (595, 672)          # etiket satiri (pin y), v6 608-658
ETK_H = 51                     # 'Cancer' murekkep yuksekligi (v6 608-658)
PAY = 63                       # v6 sol kenar payi (etiket/glif x63)
GLIF_PAY = 40                  # glif kenar payi (v6 PIN_08 Libra sag kenar 953 -> pay 47; 40 alt sinir)
MIDNIGHT = (1, 3, 24)          # onayli GPT Midnight Blue poster, pin poster kutusu sol kenar orta ornek bolgesi (olcum)


def ad(s):
    return s.strip().title()


def yazi(dr, metin, font, renk, cx, ust=None, merkez_y=None):
    bb = font.getbbox(metin)
    x = round(cx - (bb[0] + bb[2]) / 2)
    y = round(ust - bb[1]) if ust is not None else round(merkez_y - (bb[1] + bb[3]) / 2)
    dr.text((x, y), metin, font=font, fill=renk)


def baslik(im, metin, boy):
    """Pagella baslik: v6 boyu; genislik BASLIK_MAX_W'yi asarsa kuculur. Murekkep ustu y50 (v6), kuculurse dikey merkez 87.5."""
    s = boy
    while True:
        f = ImageFont.truetype(PAGELLA, s)
        bb = f.getbbox(metin)
        if bb[2] - bb[0] <= BASLIK_MAX_W or s < 40:
            break
        s -= 0.5
    d = ImageDraw.Draw(im)
    d.rectangle((0, BASLIK_BANT[0], im.size[0], BASLIK_BANT[1]), fill=BG)
    if s == boy:
        yazi(d, metin, f, LACIVERT, 500, ust=50)
    else:
        yazi(d, metin, f, LACIVERT, 500, merkez_y=87.5)
    return s


LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'sosyal', 'kapak_v1', 'assets', 'logo_sonsuz.png')
LOGO_ORAN = 0.55               # logo yuksekligi / buyuk harf yuksekligi (altin pinde glif 76 px -> logo 42 px, ayni oran)
LOGO_BOSLUK = 0.30             # kelime ile logo arasi / buyuk harf yuksekligi


def baslik_logo(im, A, B, boy):
    """Kart basligi: "<A> [sonsuz logo] <B>" (Serdar 25 Kas: '+' yerine AstroLoveArt sonsuz logosu, altin pindeki ayni logo).
    Pagella v6 boyu; toplam genislik BASLIK_MAX_W'yi asarsa kuculur. Logo buyuk harf ortasinda."""
    logo0 = Image.open(LOGO).convert('RGBA')
    s = boy
    while True:
        f = ImageFont.truetype(PAGELLA, s)
        H = f.getbbox('H'); cap = H[3] - H[1]
        lh = round(cap * LOGO_ORAN); lw = round(logo0.size[0] * lh / logo0.size[1]); gap = round(cap * LOGO_BOSLUK)
        ba = f.getbbox(A); bb_ = f.getbbox(B)
        wa = ba[2] - ba[0]; wb = bb_[2] - bb_[0]; W = wa + gap + lw + gap + wb
        if W <= BASLIK_MAX_W or s < 40:
            break
        s -= 0.5
    d = ImageDraw.Draw(im)
    d.rectangle((0, BASLIK_BANT[0], im.size[0], BASLIK_BANT[1]), fill=BG)
    ust = 50 if s == boy else round(87.5 - cap / 2)       # buyuk harf ustu (v6 y50); kuculurse dikey merkez 87.5
    x0 = round(500 - W / 2)
    d.text((x0 - ba[0], ust - H[1]), A, font=f, fill=LACIVERT)
    lx = x0 + wa + gap
    logo = logo0.resize((lw, lh), Image.LANCZOS)
    im.paste(logo, (lx, round(ust + cap / 2 - lh / 2)), logo)
    d.text((lx + lw + gap - bb_[0], ust - H[1]), B, font=f, fill=LACIVERT)
    return s, {'logo_kutu': [lx, round(ust + cap / 2 - lh / 2), lx + lw - 1, round(ust + cap / 2 - lh / 2) + lh - 1]}


def poster_pin(kaynak, A, B, sablon):
    im = Image.open(sablon).convert('RGB').copy()
    x, y, w, h = P_KUTU
    im.paste(Image.open(kaynak).convert('RGB').resize((w, h), Image.LANCZOS), (x, y))
    # BUYUK HARF (v6) kalir (Merkez 25 Kas: Title case'e GECMEZ). Uzun adlarda 2:3 pinde tek satir 11 pt'yi gecer (Pinterest 183 pt
    # sutun); 11 pt'nin altina dusen yalniz 4:5 IG profil izgarasi -> iki satirli baslik platform_boy.py 4:5 yerlesiminde.
    metin = f'{A.upper()} & {B.upper()}'
    s = baslik(im, metin, 104.5)
    return im, {'baslik_px': s, 'baslik_metni': metin}


def baslik_cap(metin, boy):
    s = boy
    while True:
        f = ImageFont.truetype(PAGELLA, s); bb = f.getbbox(metin)
        if bb[2] - bb[0] <= BASLIK_MAX_W or s < 40:
            H = f.getbbox('H'); return H[3] - H[1]
        s -= 0.5


def etiket_font(font_dir, boy):
    f = ImageFont.truetype(os.path.join(font_dir, 'OpenSans.ttf'), boy)
    f.set_variation_by_axes([600, 95])
    return f


def etiket_maske(t, font_dir):
    """'Cancer' murekkep yuksekligi ETK_H olacak boy (Open Sans SemiBold); 4x cizip kucultulur."""
    f0 = etiket_font(font_dir, 400); bb = f0.getbbox('Cancer'); boy = 400 * ETK_H / (bb[3] - bb[1])
    f = etiket_font(font_dir, round(boy * 4)); bb = f.getbbox(t)
    m = Image.new('L', (bb[2] - bb[0] + 40, f.getbbox('Cancer')[3] - f.getbbox('Cancer')[1] + 120), 0)
    ust = 20 - f.getbbox('Cancer')[1]
    ImageDraw.Draw(m).text((20 - bb[0], ust), t, font=f, fill=255)
    m = m.resize((round(m.size[0] / 4), round(m.size[1] / 4)), Image.LANCZOS)
    return m, 20 / 4    # maske, 'Cancer' ustunun maske icindeki y'si


def glif_kutulari(a, y0, y1, esik=90):
    m = np.abs(a[y0:y1].astype(int) - np.array(BG)).sum(2) > esik
    cols = np.where(m.any(0))[0]
    if len(cols) == 0:
        return []
    g = np.where(np.diff(cols) > 40)[0]
    parcalar = [(cols[0], cols[g[0]]), (cols[g[0] + 1], cols[-1])] if len(g) == 1 else [(cols[0], cols[-1])]
    out = []
    for x0, x1 in parcalar:
        rr = np.where(m[:, x0:x1 + 1].any(1))[0]
        out.append((int(x0), int(rr[0] + y0), int(x1), int(rr[-1] + y0)))
    return out


def kart_pin(kaynak, A, B, sablon, font_dir):
    im = Image.open(sablon).convert('RGB').copy()
    K = Image.open(kaynak).convert('RGB')
    if K.size != (3000, 2250):
        raise SystemExit(f'DUR: kart boyu {K.size} (beklenen 3000x2250)')
    r = K.resize((round(3000 * K_OLCEK), round(2250 * K_OLCEK)), Image.LANCZOS)
    y0, y1 = K_BANT
    im.paste(r.crop((-K_DX, y0 - K_DY, -K_DX + 1000, y1 - K_DY)), (0, y0))
    # genis glif (or. Aquarius, kartta 718 px) pinde kenardan tasar: o glif merkezi korunarak kuculur, [GLIF_PAY, 1000-GLIF_PAY]'a sigar
    gkart = glif_kutulari(np.asarray(K), 650, 1000)
    if len(gkart) != 2:
        raise SystemExit(f'DUR: kartta iki glif ayrilamadi {gkart}')
    olcek = []
    for (x0, gy0, x1, gy1) in gkart:
        px0 = x0 * K_OLCEK + K_DX; px1 = (x1 + 1) * K_OLCEK + K_DX; c = (px0 + px1) / 2
        izin = 2 * min(c - GLIF_PAY, 1000 - GLIF_PAY - c)
        k = min(1.0, izin / (px1 - px0)); olcek.append(round(k, 3))
        if k < 1.0:
            ImageDraw.Draw(im).rectangle((max(0, int(px0) - 2), 395, min(999, int(px1) + 2), 600), fill=BG)
            g = K.crop((x0 - 4, gy0 - 4, x1 + 5, gy1 + 5))
            w = round(g.size[0] * K_OLCEK * k); h = round(g.size[1] * K_OLCEK * k)
            g = g.resize((w, h), Image.LANCZOS)
            cy = ((gy0 + gy1 + 1) / 2) * K_OLCEK + K_DY
            im.paste(g, (round(c - w / 2), round(cy - h / 2)))
    baslik_s, lb = baslik_logo(im, A, B, 99)
    d = ImageDraw.Draw(im); d.rectangle((0, ETK_BANT[0], 1000, ETK_BANT[1]), fill=BG)
    a = np.asarray(im)
    gk = glif_kutulari(a, 395, 595)
    if len(gk) != 2:
        raise SystemExit(f'DUR: iki glif ayrilamadi {gk}')
    mA, uA = etiket_maske(A, font_dir); mB, uB = etiket_maske(B, font_dir)
    wa = mA.getbbox(); wb = mB.getbbox()
    ca = (gk[0][0] + gk[0][2]) / 2; cb = (gk[1][0] + gk[1][2]) / 2
    # glif merkezine ortali; kenar payini asarsa iceri kaydir (v6 sol pay 63, sag pay ayni)
    def yer(m, bb, c):
        w = bb[2] - bb[0]; x = c - w / 2
        x = max(PAY, min(x, 1000 - PAY - w))
        return round(x - bb[0])
    xa = yer(mA, wa, ca); xb = yer(mB, wb, cb)
    renk = Image.new('RGB', mA.size, ETIKET_RENK)
    im.paste(renk, (xa, round(608 - uA)), mA)
    im.paste(Image.new('RGB', mB.size, ETIKET_RENK), (xb, round(608 - uB)), mB)
    return im, {'baslik_px': baslik_s, 'glif_kutulari': gk, 'glif_olcek': olcek, **lb}


def fark(a, b):
    d = np.abs(a.astype(float) - b.astype(float)).sum(2) / 3
    return float(d.mean()), float(np.percentile(d, 99.9))


def qc(tur, yol, kaynak, sablon, bilgi):
    a = np.asarray(Image.open(yol).convert('RGB')); t = np.asarray(Image.open(sablon).convert('RGB'))
    S = []
    def k(ad_, ok, v=''):
        S.append((ad_, bool(ok), v))
    k('boy 1000x1500', a.shape[:2] == (1500, 1000), a.shape)
    maske = np.ones(a.shape[:2], bool)
    maske[BASLIK_BANT[0]:BASLIK_BANT[1] + 1] = False
    if tur == 'poster':
        x, y, w, h = P_KUTU; maske[y - 2:y + h + 2, x - 2:x + w + 2] = False
    else:
        maske[K_BANT[0]:K_BANT[1]] = False
    d = np.abs(a.astype(float) - t.astype(float)).sum(2)[maske] / 3
    k('sablon bolgesi degismedi (ort <= 1.0, p99.9 <= 8; JPEG gurultusu 4 olculdu)', d.mean() <= 1.0 and np.percentile(d, 99.9) <= 8,
      (round(float(d.mean()), 2), round(float(np.percentile(d, 99.9)), 1)))
    if tur == 'poster':
        x, y, w, h = P_KUTU
        r = np.asarray(Image.open(kaynak).convert('RGB').resize((w, h), Image.LANCZOS))
        m, p = fark(a[y + 3:y + h - 3, x + 3:x + w - 3], r[3:-3, 3:-3])
        k('poster kutusu = kaynak (ort <= 2.0)', m <= 2.0, round(m, 2))
        orta = a[y + h // 2 - 20:y + h // 2 + 20, x + 20:x + 60].reshape(-1, 3).mean(0)
        k('poster Midnight Blue (kenar zemini, kanal farki <= 12)', np.abs(orta - np.array(MIDNIGHT)).max() <= 12, orta.round().tolist())
    else:
        K = Image.open(kaynak).convert('RGB').resize((round(3000 * K_OLCEK), round(2250 * K_OLCEK)), Image.LANCZOS)
        r = np.asarray(K)
        kuc = bilgi.get('glif_olcek', [1, 1]) != [1.0, 1.0] and min(bilgi.get('glif_olcek', [1, 1])) < 1.0
        for ad_, (y0, y1) in (('glif satiri', (400, 590)), ('egri', (675, 800)), ('birlesik sembol', (805, 1175))):
            if ad_ == 'glif satiri' and kuc:
                continue    # kuculen glif kart olcegiyle karsilastirilamaz; kutu kapisi asagida
            m, p = fark(a[y0:y1], r[y0 - K_DY:y1 - K_DY, -K_DX:-K_DX + 1000])
            k(f'{ad_} = kart (ort <= 2.0)', m <= 2.0, round(m, 2))
        lk = bilgi.get('logo_kutu')
        if lk:
            z = a[lk[1]:lk[3] + 1, lk[0]:lk[2] + 1].astype(int)
            altin = (z[..., 0] > 150) & (z[..., 0] - z[..., 2] > 60)
            k('baslikta sonsuz logo (altin piksel >= %15 kutu)', altin.mean() >= 0.15, round(float(altin.mean()), 3))
        elif tur == 'kart':
            k('baslikta sonsuz logo', False, 'logo kutusu yok')
        gk = glif_kutulari(a, 395, 600)
        k('iki glif, kenar payi >= 30 px', len(gk) == 2 and gk[0][0] >= 30 and gk[-1][2] <= 970, gk)
        if kuc:
            k('kuculen glif olcegi >= 0.5', min(bilgi['glif_olcek']) >= 0.5, bilgi['glif_olcek'])
        ek = glif_kutulari(a, ETK_BANT[0], ETK_BANT[1])
        k('iki etiket', len(ek) == 2, ek)
        if len(ek) == 2:
            k('etiket kenar paylari >= 60 px', ek[0][0] >= 60 and ek[1][2] <= 1000 - 60, (ek[0][0], ek[1][2]))
            k('etiketler arasi >= 40 px', ek[1][0] - ek[0][2] >= 40, ek[1][0] - ek[0][2])
            k('etiket ustu y 604-612 (v6 607-609)', all(604 <= e[1] <= 612 for e in ek), [e[1] for e in ek])
            k('etiket alti <= 672 (alt uzantili harf dahil)', all(e[3] <= 672 for e in ek), [e[3] for e in ek])
            if len(gk) == 2:
                k('etiket glif altinda (merkez farki <= 120 px)', all(abs((e[0] + e[2]) / 2 - (g_[0] + g_[2]) / 2) <= 120 for e, g_ in zip(ek, gk)), '')
    bk = glif_kutulari(a, BASLIK_BANT[0], BASLIK_BANT[1] + 1, esik=120)
    if bk:
        x0 = min(b[0] for b in bk); x1 = max(b[2] for b in bk); y0 = min(b[1] for b in bk); y1 = max(b[3] for b in bk)
        k('baslik kutusu x 39-961, y 40-152', x0 >= 39 and x1 <= 961 and y0 >= 40 and y1 <= 152, (x0, y0, x1, y1))
        # baslik v6 boyunda (ust y50; ust uzantili kucuk harf 'b' icin +-4) ya da genislik siniri yuzunden kuculmus (genislik >= 900); en az 40 px (Serdar 25 Kas A emsali:
        # sigmayan ad sigan en buyuk boyda)
        k('baslik v6 boyunda ya da en genis (>= 900 px) ve >= 40 px', (abs(y0 - 50) <= 4 or x1 - x0 + 1 >= 900) and y1 - y0 + 1 >= 40, (y1 - y0 + 1, x1 - x0 + 1))
        k('baslik ortada (+-3 px)', abs((x0 + x1) / 2 - 499.5) <= 3, (x0 + x1) / 2)
    else:
        k('baslik var', False, 'yok')
    ok = all(s[1] for s in S)
    return ok, S


def uret_ve_qc(tur, kaynak, A, B, sablon, font_dir, out):
    if tur == 'poster':
        im, bilgi = poster_pin(kaynak, A, B, sablon)
    else:
        im, bilgi = kart_pin(kaynak, A, B, sablon, font_dir)
    im.save(out, quality=95)
    ok, S = qc(tur, out, kaynak, sablon, bilgi)
    return ok, S, bilgi


def oz_test(girdi, font_dir, tmp):
    """v6 yeniden uretim olcumu (bilinen PASS) + bozuk cikti (bilinen FAIL)."""
    R = []
    P1 = os.path.join(girdi, 'PIN_01_CANCER_LEO_A_POSTER_v6.jpg'); P2 = os.path.join(girdi, 'PIN_02_CANCER_LEO_B_SYMBOL_v6.jpg')
    vakalar = [('poster', 'GPT_9000000041_Cancer_Leo_Midnight_Blue_2000.jpg', 'Cancer', 'Leo', P1, P1),
               ('poster', 'GPT_9000000532_Cancer_Libra_Midnight_Blue_2000.jpg', 'Cancer', 'Libra', P1, os.path.join(girdi, 'PIN_07_CANCER_LIBRA_A_POSTER_v6.jpg')),
               ('kart', 'KART_CANCER_LEO.jpg', 'Cancer', 'Leo', P2, P2),
               ('kart', 'KART_CANCER_LIBRA.jpg', 'Cancer', 'Libra', P2, os.path.join(girdi, 'PIN_08_CANCER_LIBRA_B_SYMBOL_v6.jpg'))]
    for tur, kay, A, B, sab, v6 in vakalar:
        o = os.path.join(tmp, f'oz_{tur}_{A}_{B}.jpg')
        ok, S, _ = uret_ve_qc(tur, os.path.join(girdi, kay), A, B, sab, font_dir, o)
        a = np.asarray(Image.open(o).convert('RGB')); v = np.asarray(Image.open(v6).convert('RGB'))
        mb, pb = fark(a[30:153], v[30:153]); mt, pt = fark(a, v) if tur == 'poster' else fark(a[153:], v[153:])
        # olcum esikleri (25 Kas): baslik bandi farki Palatino -> Pagella glif farkidir (boy/renk/konum taramasinda en iyi: poster 6.4-7.4,
        # kart 12.8-14.8); esik poster <= 8.5, kart <= 16.5; tum pin ort <= 3.0
        # kart basligi Serdar 25 Kas karariyla degisti ('+' yerine logo): v6 baslik bandi kiyasi yalniz posterde; kartta tum pin = baslik bandi alti
        eb = 8.5 if tur == 'poster' else 999
        R.append((f'PASS {tur} {A}+{B}: QC PASS ve v6 farki baslik bandi ort {mb:.2f} (<= {eb}), tum pin ort {mt:.2f} (<= 3.0)', ok and mb <= eb and mt <= 3.0,
                  [s for s in S if not s[1]]))
    # FAIL 1: baslik silinmis poster
    o = os.path.join(tmp, 'oz_fail1.jpg'); im, _ = poster_pin(os.path.join(girdi, vakalar[0][1]), 'Cancer', 'Leo', P1)
    ImageDraw.Draw(im).rectangle((0, 30, 1000, 152), fill=BG); im.save(o, quality=95)
    R.append(('FAIL: baslik yok', not qc('poster', o, os.path.join(girdi, vakalar[0][1]), P1, {})[0], ''))
    # FAIL 2: yanlis poster (kaynak baska cift)
    o = os.path.join(tmp, 'oz_fail2.jpg'); im, _ = poster_pin(os.path.join(girdi, vakalar[1][1]), 'Cancer', 'Leo', P1); im.save(o, quality=95)
    R.append(('FAIL: poster kutusunda baska poster', not qc('poster', o, os.path.join(girdi, vakalar[0][1]), P1, {})[0], ''))
    # FAIL 3: kart etiketi kenardan tasmis
    o = os.path.join(tmp, 'oz_fail3.jpg'); im, _ = kart_pin(os.path.join(girdi, 'KART_CANCER_LEO.jpg'), 'Cancer', 'Leo', P2, font_dir)
    ImageDraw.Draw(im).rectangle((20, 615, 60, 650), fill=ETIKET_RENK); im.save(o, quality=95)
    R.append(('FAIL: etiket kenar payi', not qc('kart', o, os.path.join(girdi, 'KART_CANCER_LEO.jpg'), P2, {})[0], ''))
    # FAIL 4: kart karti baska cift
    o = os.path.join(tmp, 'oz_fail4.jpg'); im, _ = kart_pin(os.path.join(girdi, 'KART_CANCER_LIBRA.jpg'), 'Cancer', 'Leo', P2, font_dir); im.save(o, quality=95)
    R.append(('FAIL: kartta baska cift', not qc('kart', o, os.path.join(girdi, 'KART_CANCER_LEO.jpg'), P2, {})[0], ''))
    for r in R:
        print(('OK  ' if r[1] else 'HATA') + ' ' + r[0] + (f' {r[2]}' if r[2] else ''))
    return all(r[1] for r in R)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tur', choices=('poster', 'kart')); ap.add_argument('--kaynak'); ap.add_argument('--a'); ap.add_argument('--b')
    ap.add_argument('--sablon'); ap.add_argument('--font_dir', required=True); ap.add_argument('--out'); ap.add_argument('--qc_json')
    ap.add_argument('--oz-test', action='store_true'); ap.add_argument('--girdi')
    g = ap.parse_args()
    if g.oz_test:
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ok = oz_test(g.girdi, g.font_dir, t)
        print('OZ-TEST', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
    A, B = ad(g.a), ad(g.b)
    ok, S, bilgi = uret_ve_qc(g.tur, g.kaynak, A, B, g.sablon, g.font_dir, g.out)
    for s in S:
        print(('PASS' if s[1] else 'FAIL') + f' {g.tur} {A}+{B}: {s[0]} {s[2]}')
    if g.qc_json:
        json.dump({'tur': g.tur, 'a': A, 'b': B, 'sonuc': 'PASS' if ok else 'FAIL', 'bilgi': bilgi,
                   'kapilar': [[s[0], s[1], str(s[2])] for s in S]}, open(g.qc_json, 'w'), ensure_ascii=False, indent=1)
    print('SONUC', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
