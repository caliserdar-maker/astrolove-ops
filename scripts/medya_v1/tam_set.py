#!/usr/bin/env python3
"""TAM SET (Serdar karari 25 Eyl): bir ciftin Etsy galerisi, Cancer-Libra 4570143815 galerisiyle birebir ayni yapida.

Envanter (canli CL galerisi, 14 foto + video; video bu isin disinda):
  CL 01 kapak MB 1080x1350 ........ isimli MB poster, canli sahnede CL posterinin yerine (a1_poster kapak kurali)
  CL 02 "Your names. Your own message." (GENEL_1 karsiligi) .... KULLANILMAZ (Serdar)
  CL 03 kart 3 .................... video oturumunun KART3'u (A1_77/<CIFT>/KART3.jpg)
  CL 04 ortak sembol .............. panelde ciftin kucuk sembolleri + birlesik sembolu (Canva MB sayfasi), etiketler
  CL 05 bes palet ................. 5 renk isimli poster (CL posterleriyle olculen yerlere)
  CL 06 kagit ..................... GENEL_3
  CL 07 yakin detay ............... isimli MB poster + birlesik sembol detayi (POD baski dosyasi 30x40, buyutme <= 1.5)
  CL 08 boy rehberi ............... GENEL_2
  CL 09 eser/isim/mesaj ........... KART09 (a1_poster: dogru ust etiket + isimli MB poster)
  CL 10 siparise uretim ........... GENEL_4
  CL 11-14 cerceveli DB/CI/PW/WP .. o rengin isimli posteri, canli sahnede CL posterinin yerine
Cift-ozgu metin: ust etiket (03-10), kart 04 alt satir ve sembol etiketleri. Kapi: OCR ile kartta baska burc adi yok.
Poster kurallari a1_poster (08ceb2f) ile ayni; Blue disi renkler kisisel-v1 edisyon kodu (edisyon_uret.oran_kur) ile,
her rengin kendi Canva 4/5 sayfasi ve kendi kilidiyle (ORAN_SABITLERI edisyonlar). Kapilar her renkte:
kalinti + temiz zemin + sembol. Etsy'ye erisim YOK."""
import io, json, re, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_poster as A
from a1_poster import rc, log, W, KP, DR, REF_CIFT, ISIM, TAG

Image.MAX_IMAGE_PIXELS = None
CIFT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'ARIES_LEO'
YEREL = '--yerel' in sys.argv
YALNIZ06 = '--kart06' in sys.argv                      # yalniz galeri 06 (yakin detay) + onizleme yeniden (Serdar 25 Eyl)
SAYFA_HAM = f'{KP}/TAMSET_HAM'                      # <renk>_<sayfa>.png (Canva 4/5, ham2 ile kopyalandi)
A77MOD = '--a77' in sys.argv                          # 77 cift uretimi: A1_77/<CIFT>/TAM_SET, yalniz kapilar gecerse yuklenir
HAM_HAZIR = '--ham-hazir' in sys.argv                  # sayfalar surucu (tam77.py) tarafindan W/ham'a kondu
def _arg(ad):
    return sys.argv[sys.argv.index(ad) + 1] if ad in sys.argv else None
VIDEO_YOL, KART3_YOL = _arg('--video'), _arg('--kart3')   # Drive yolu (orn. onayli CL v5 videosu)
HEDEF = f'{DR}/REVIEW/TAM_SET_{CIFT}' if not A77MOD else f'{A.A77}/{CIFT}/TAM_SET'
RENKLER = ['blue', 'black', 'modern', 'pure_white', 'vintage']
import os
if os.environ.get('TS_RENKLER'): RENKLER = os.environ['TS_RENKLER'].split(',')   # yalniz yerel deneme
if YALNIZ06: RENKLER = ['blue']
DUZELT = '--duzelt' in sys.argv                         # Serdar 25 Eyl duzeltmeleri: yalniz etkilenen kartlar
KORU = {1, 3, 4, 9} if DUZELT else set()               # CL no: kapak, kart 3 (Serdar onayli, DOKUNMA), ortak sembol, KART09
DOKULU = {'vintage'}                                  # parsomen dokusu: sembol kapisi doku-dengeli (Serdar 25 Eyl)
RENK_AD = {'blue': 'MIDNIGHT_BLUE', 'black': 'DEEP_BLACK', 'modern': 'CHAMPAGNE_IVORY', 'pure_white': 'PURE_WHITE', 'vintage': 'WARM_PARCHMENT'}
REF_DOSYA = {1: '01_8568298334', 2: '02_8567954544', 3: '03_8615800647', 4: '04_8567954548', 5: '05_8567954574', 6: '06_8567954580',
             7: '07_8615800641', 8: '08_8616354969', 9: '09_8615800661', 10: '10_8615800655', 11: '11_8616144677',
             12: '12_8616144673', 13: '13_8616144691', 14: '14_8616144683'}
SAHNE_RENK = {11: 'black', 12: 'modern', 13: 'pure_white', 14: 'vintage'}
BG = np.array([237., 232., 226.])
CIK = W / 'TAM_SET'; CIK.mkdir(parents=True, exist_ok=True)
R = {'cift': CIFT, 'renk_kaynagi': {r: RENK_AD[r] for r in RENKLER}}

def gri(im): return np.asarray(im.convert('L')).astype(np.float32)

# ------------------------------------------------------------------ renk posterleri
class EdPoster:
    """Blue disi renkler: kisisel-v1 edisyon kodu degismeden (oran_kur + poster_kur + blok_kapisi)."""
    def __init__(self, ed):
        import edisyon_uret as E, pilot11, pilot16
        self.E, self.p11, self.p16, self.ed = E, pilot11, pilot16, ed
        d = json.loads(E.SABIT_YOL.read_text(encoding='utf-8'))
        self.kilit = d['edisyonlar'][ed]['4x5']
        (E.YOL / ed / 'ham').mkdir(parents=True, exist_ok=True)

    def sayfa_kur(self, sayfa_png, n, referans=False, ust=None):
        """referans (CL 28): o edisyonun mesaj boyu tavani. Cift: mesaj boyu <= CL (ayni edisyon) ve <= Blue (5 renkte ayni oran)."""
        E = self.E; t0 = time.time()
        yol = E.YOL / self.ed / 'ham' / f'4x5_p{n}.jpg'
        Image.open(io.BytesIO(sayfa_png)).convert('RGB').save(yol, 'PNG')
        ref, _ = self.p11.norm(Image.open(yol).convert('RGB'))
        m = E.murekkep(np.asarray(ref).astype(np.float32))
        o, duz = A.olcum_duzelt(self.p11.sayfa_olc(yol, maske=E.edisyon_maske), m)
        E.REF_SAYFA = n
        s, S = E.oran_kur(self.ed, '4x5', self.kilit, o)
        g0, g1 = o['isim_govde']; s['isim_y'] = (g0 + g1) / 2
        ilk = {'tag_cap': s['tag_cap'], 'tag_sinir': s['tag_sinir']}
        if referans: self.tavan = dict(ilk)
        else:
            s['tag_cap'] = min(s['tag_cap'], self.tavan['tag_cap'], *([ust['tag_cap']] if ust else []))
            s['tag_sinir'] = min(s['tag_sinir'], self.tavan['tag_sinir'], *([ust['tag_sinir']] if ust else []))
        return {'ilk': ilk, 'tag_son': {'tag_cap': s['tag_cap'], 'tag_sinir': s['tag_sinir']}, 'sayfa': n, 's': s, 'S': S, 'm': m, 'o': o, 'duz': duz, 'sn': round(time.time() - t0, 1)}

    def uret(self, B, isimler, tagline):
        import giris_dogrula as gd
        s, S = B['s'], B['S']
        r = gd.siparis_dogrula(isimler[0], isimler[1], tagline, None)
        p, bilgi, merkez, x, yeni = self.p16.poster_kur(s, S, {'sol': r['sol']['deger'], 'sag': r['sag']['deger']}, tagline)
        kapi = self.p16.blok_kapisi(p, S, s, yeni)
        sk, kirp = A.sembol_kapisi(p, S, s, merkez, B['m'], A.SEMBOL_ESIK, ink=lambda P: self.E.murekkep(P, kenar=0),
                                   zemin=S['zemin_a'] if self.ed in DOKULU else None)
        return p, {'kalinti_kapisi': kapi, 'temiz_ara_kapisi': s['temiz_ara_kapisi'], 'sembol_kapisi': sk,
                   'punto': bilgi['punto'], 'olcek': bilgi['olcek'], 'olcum_duzeltme': B['duz']}, kirp

def posterler(sayfa):
    """Her renk: CL (28) ve cift (no) isimli EJ posteri + kapilar."""
    P, K, M = {}, {}, {}
    for renk in RENKLER:
        t0 = time.time()
        if renk == 'blue':
            PB = A.Poster(yerel=YEREL)
            Bc = PB.sayfa_kur(sayfa[f'blue_28'], 28, 'blue', A.ORAN, referans=True); cl, clb, _ = PB.uret(Bc, ISIM, TAG)
            Ba = PB.sayfa_kur(sayfa[f'blue_{NO}'], NO, 'blue', A.ORAN); al, alb, kk = PB.uret(Ba, ISIM, TAG)
            M['blue'] = {'B': Ba, 'X': PB, 'Bc': Bc}
        else:
            EP = EdPoster(renk)
            ust = {k: M['blue']['B']['s'][k] for k in ('tag_cap', 'tag_sinir')} if 'blue' in M else None
            Bc = EP.sayfa_kur(sayfa[f'{renk}_28'], 28, referans=True); cl, clb, _ = EP.uret(Bc, ISIM, TAG)
            Ba = EP.sayfa_kur(sayfa[f'{renk}_{NO}'], NO, ust=ust); al, alb, kk = EP.uret(Ba, ISIM, TAG)
            M[renk] = {'o': {k: Ba['s'].get(k) for k in ('sembol_bant', 'isim_bant')}, 'tag_bant': Ba['s'].get('tag_bant'),
                       'B': Ba, 'Bc': Bc, 'tag': {'ilk': Ba['ilk'], 'son': Ba['tag_son'], 'CL': Bc['ilk'], 'blue': ust}}
        kap = {'kalinti': alb['kalinti_kapisi']['gecti'], 'temiz_zemin': alb['temiz_ara_kapisi']['gecti'], 'sembol': alb['sembol_kapisi']['gecti']}
        P[renk] = {'CL': cl, 'AL': al}; K[renk] = kap
        M[renk]['mesaj_px'] = {'AL': mesaj_boy(al, M[renk]['B']), 'CL': mesaj_boy(cl, M[renk]['Bc'])}
        R.setdefault('poster', {})[renk] = {'kapi': kap, 'gecti': all(kap.values()), 'punto': alb['punto'], 'olcek': alb['olcek'],
                                            'sembol': {y: alb['sembol_kapisi'][y] for y in ('sol', 'sag')},
                                            'CL_kapi': {'kalinti': clb['kalinti_kapisi']['gecti'], 'sembol': clb['sembol_kapisi']['gecti']},
                                            'sn': round(time.time() - t0, 1)}
        al.save(CIK / f'POSTER_{RENK_AD[renk]}_EJ.png'); A.sembol_gorseli(kk, f'../TAM_SET/SEMBOL_{RENK_AD[renk]}.jpg')
        log(renk, R['poster'][renk])
    return P, M

# ------------------------------------------------------------------ sahneye oturtma (CL posteriyle olculur)
def sahne_yer(sahne, cl, kaba):
    """Kaba kutuda CL posterinin olcek + konumu (TM_CCOEFF), sonra ust %55'te (isim/tagline disi) gri fark en kucuk
    ince arama; gorunen aciklik = yerlestirilmis CL posteriyle fark < 14 olan satir/sutunlar (cerceve, golge haric)."""
    import cv2
    Sg = gri(sahne); H, Wd = Sg.shape; x0, y0, x1, y1 = kaba
    bol = Sg[y0:y1, x0:x1]; g = cl.convert('L'); en = None
    for w in range(int((x1 - x0) * 0.5), int((x1 - x0) * 1.0) + 1, 3):
        h = round(w * 1.25)
        if h >= bol.shape[0] or w >= bol.shape[1]: continue
        t = np.asarray(g.resize((w, h), Image.BOX)).astype(np.float32)
        r = cv2.matchTemplate(bol, t, cv2.TM_CCOEFF_NORMED); _, v, _, l = cv2.minMaxLoc(r)
        if en is None or v > en[0]: en = (v, w, l[0] + x0, l[1] + y0)
    v, w0, xa, ya = en; ince = None
    for w in range(w0 - 4, w0 + 5):
        h = round(w * 1.25); q = np.asarray(g.resize((w, h), Image.BOX)).astype(np.float32); ust = int(h * 0.55)
        for x in range(xa - 5, xa + 6):
            for y in range(ya - 5, ya + 6):
                if x < 0 or y < 0 or x + w > Wd or y + ust > H: continue
                f = float(np.abs(q[:ust] - Sg[y:y + ust, x:x + w]).mean())
                if ince is None or f < ince[0]: ince = (f, x, y, w, h)
    f, x, y, w, h = ince
    q = np.asarray(g.resize((w, h), Image.LANCZOS)).astype(np.float32)
    xs0, ys0, xs1, ys1 = max(x, 0), max(y, 0), min(x + w, Wd), min(y + h, H)
    d = np.abs(q[ys0 - y:ys1 - y, xs0 - x:xs1 - x] - Sg[ys0:ys1, xs0:xs1]) < 14
    rows = np.where(d.mean(1) > 0.8)[0]; cols = np.where(d.mean(0) > 0.8)[0]
    ac = [int(xs0 + cols.min()), int(ys0 + rows.min()), int(xs0 + cols.max() + 1), int(ys0 + rows.max() + 1)]
    return {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h), 'aciklik': ac, 'eslesme': round(float(v), 4), 'ust_gri_fark': round(f, 2)}

def dis_fark(a, b, yer):
    d = np.abs(np.asarray(a).astype(np.int16) - np.asarray(b).astype(np.int16)).max(2)
    x0, y0, x1, y1 = yer['aciklik']; m = np.ones(d.shape, bool); m[y0:y1, x0:x1] = False
    return int(d[m].max())

# ------------------------------------------------------------------ mesaj boyu kapisi (Serdar 25 Eyl)
MESAJ_ESIK = {'renkler_arasi': 0.02, 'CL_ustu_px': 1}

def mesaj_boy(p, B):
    """Mesaj (tagline) harf yuksekligi: tag bandi +-80 satirda |poster - temiz zemin| > 40 olan satirlarin yuksekligi (px)."""
    tb = B['o']['tag_bant']; Z = B['S']['zemin_a']; P = np.asarray(p.convert('RGB')).astype(np.float32)
    y0, y1 = max(tb[0] - 80, 0), min(tb[1] + 80, P.shape[0]); x0, x1 = int(P.shape[1] * 0.1), int(P.shape[1] * 0.9)
    d = (np.abs(P[y0:y1, x0:x1] - Z[y0:y1, x0:x1]).max(2) > 40).sum(1) >= 3
    ys = np.where(d)[0]
    return int(ys[-1] - ys[0] + 1) if len(ys) else 0

def mesaj_kapisi(M):
    h = {r: M[r]['mesaj_px'] for r in M if 'mesaj_px' in M[r]}; al = [v['AL'] for v in h.values()]
    fark = max(al) / max(min(al), 1) - 1
    cl_ok = {r: v['AL'] <= v['CL'] + MESAJ_ESIK['CL_ustu_px'] for r, v in h.items()}
    return {'px': h, 'renkler_arasi_fark': round(fark, 4), 'CL_ustu_degil': cl_ok, 'esik': MESAJ_ESIK,
            'tag_cap': {r: M[r].get('tag') for r in M if r != 'blue'},
            'gecti': fark <= MESAJ_ESIK['renkler_arasi'] and all(cl_ok.values())}

# ------------------------------------------------------------------ kart metinleri
def etiket_yaz(kart, etiket):
    X = A.k9_hazirla(kart); return Image.fromarray(np.clip(A.k9_etiket_ciz(X, etiket), 0, 255).astype(np.uint8))

def baslik_ekle(genel, cl_kart, etiket):
    """GENEL kartta yalniz 'ASTROLOVE' var: ust satir CL karsiligindan olculen font/konumla 'ASTROLOVE / <ETIKET>' olur
    (CL kartinda yeniden yazilan etiket satirinin zeminden farki, GENEL kartin temizlenmis ust bandina eklenir)."""
    X = A.k9_hazirla(cl_kart); lab = A.k9_etiket_ciz(X, etiket)
    g = np.asarray(genel.convert('RGB')).astype(np.float64).copy(); y0, y1 = A.K9_BANT; W = g.shape[1]
    a0, a1 = y0 - 25, y1 + 10
    bgG = np.median(g[a0:a1, 60:W - 60].reshape(-1, 3), 0)
    g[a0:a1, 60:W - 60] = bgG + (lab[a0:a1, 60:W - 60] - X['bg'])
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))

def baslik_kapisi(kart, etiket):
    y0, y1 = A.K9_BANT; a = kart.convert('L'); b = a.crop((100, y0, a.width - 60, y1))
    okunan = A.ocr(b.resize((b.width * 2, b.height * 2), Image.LANCZOS))
    return {'ocr': okunan, 'gecti': okunan.replace(' ', '') == f'ASTROLOVE/{etiket}'.replace(' ', '')}

KAGIT06 = (150, 550, 1230, 1880)                                    # CL 06 kagit kartinda poster kaba kutusu (3000x2250)

def kart_kagit(ref6, cl_mb, al_mb, etiket):
    """Galeri 05 = CL 06 ile birebir duzen: canli CL kartinda CL posterinin yeri olculur, ciftin isimli MB posteri oraya."""
    y = sahne_yer(ref6, cl_mb, KAGIT06); k = A.yerlestir(ref6, al_mb, y)
    return etiket_yaz(k, etiket), {'yer': y, 'aciklik_disi_maks_fark': dis_fark(ref6, k, y)}

def metin(kart, kutu, eski, yeni, align='left', bg=BG):
    tl = _tl()
    c = np.asarray(kart.convert('RGB')).astype(np.float64)
    out, p = tl.replace(c, kutu, eski, yeni, 'mont', align=align, bg=bg)
    R.setdefault('metin', []).append({'eski': eski, 'yeni': yeni, **{k: p[k] for k in ('size', 'w', 'mse')}})
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def _tl():
    sys.path.insert(0, str(Path(A.__file__).resolve().parent / 'uretim'))
    import textlayer as tl
    f = A.K / 'assets' / 'fonts' / 'Montserrat.ttf'
    if f.exists(): tl.FONTS['mont'] = str(f)
    return tl

# ------------------------------------------------------------------ kart 04 (ortak sembol paneli)
PANEL04 = (1320, 480, 2831, 2011)

def birlesik_maske(B):
    """Sayfada birlesik sembol: sembol bandinin ustunde, halka (genis yay) haric murekkep bilesenleri."""
    from scipy import ndimage
    m = B['m'].copy(); m[B['o']['sembol_bant'][0] - 40:] = False
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=2)); ob = ndimage.find_objects(lab)
    tut = [i + 1 for i, sl in enumerate(ob) if sl and (sl[1].stop - sl[1].start) < 1000 and (sl[0].stop - sl[0].start) < 1000
           and (lab[sl] == i + 1).sum() > 400]
    return np.isin(lab, tut) & m

def glif_katman(B, kutu, maske=None):
    """Canva sayfasindan (norm 2400) glif: alfa = |sayfa - hizali zemin| / cekirdek; renk = (sayfa - zemin(1-a)) / a."""
    x0, y0, x1, y1 = kutu
    ref = np.asarray(B['S']['ref']).astype(np.float32)[y0:y1, x0:x1]; z = B['S']['zemin_a'][y0:y1, x0:x1]
    d = np.abs(ref - z).max(2); m = (B['m'] if maske is None else maske)[y0:y1, x0:x1]
    from scipy import ndimage
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=2))
    if n:
        buyuk = np.argmax(np.bincount(lab.ravel())[1:]) + 1; m2 = lab == buyuk
        alanlar = np.bincount(lab.ravel()); tut = [i for i in range(1, n + 1) if alanlar[i] >= 0.05 * alanlar[buyuk]]
        m2 = np.isin(lab, tut)
    else: m2 = m
    cek = np.percentile(d[m & m2], 95) if (m & m2).any() else 1.0
    a = np.clip(d / max(cek, 1), 0, 1) * ndimage.binary_dilation(m2, iterations=6)
    F = np.where(a[..., None] > 0.02, (ref - z * (1 - a[..., None])) / np.maximum(a[..., None], 0.02), ref)
    ys, xs = np.where(a > 0.3)
    return np.clip(F, 0, 255), a, (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)

def kart04(kart, M, sahne_cl_B):
    """CL panelindeki kucuk semboller + birlesik sembol silinir (duz panel rengi), ciftinkiler ayni merkez ve olcekle konur.
    Olcek: CL sayfasindaki ayni oge genisligi / paneldeki genislik (olculur)."""
    from scipy import ndimage
    a = np.asarray(kart.convert('RGB')).astype(np.float64); x0, y0, x1, y1 = PANEL04; P = a[y0:y1, x0:x1].copy(); H, Wd = P.shape[:2]
    flat = np.median(P[5:40, 5:40].reshape(-1, 3), 0)
    ink = np.abs(P - flat).max(2) > 40
    top = np.zeros((H, Wd), bool); top[int(0.03 * H):int(0.25 * H)] = True
    low = np.zeros((H, Wd), bool); low[int(0.55 * H):int(0.98 * H)] = True
    def bilesen(mm, amin=200):
        lab, n = ndimage.label(mm); al = np.bincount(lab.ravel()); return np.isin(lab, [i for i in range(1, n + 1) if al[i] >= amin])
    gly = bilesen(ink & top); fus = bilesen(ink & low)
    kutular = []
    for side in (0, 1):
        mm = gly.copy(); mm[:, (Wd // 2 if side == 0 else 0):(Wd if side == 0 else Wd // 2)] = False
        ys, xs = np.where(mm); kutular.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    ys, xs = np.where(fus); fk = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    rem = ndimage.binary_dilation(gly | fus, iterations=14)
    P[rem] = flat
    # CL sayfasindaki olculer (olcek icin) ve cift katmanlari
    Bc, Ba = sahne_cl_B, M['blue']['B']
    def sayfa_ogeleri(B):
        o = B['o']; sb = o['sembol_bant']; out = []
        for sx in o['sembol']:
            out.append(glif_katman(B, (sx[0] - 12, sb[0] - 12, sx[1] + 12, sb[1] + 12)))
        # birlesik sembol: halka icindeki ust bolge (sembol bandinin ustu), halka cizgisi haric (en buyuk bilesen secimi)
        bm = birlesik_maske(B); ys, xs = np.where(bm)
        out.append(glif_katman(B, (xs.min() - 20, ys.min() - 20, xs.max() + 21, ys.max() + 21), bm))
        return out
    ogeler_cl, ogeler_al = sayfa_ogeleri(Bc), sayfa_ogeleri(Ba)
    olc = []
    for i, (hk) in enumerate(kutular + [fk]):
        wc = ogeler_cl[i][2][2] - ogeler_cl[i][2][0]; olc.append((hk[2] - hk[0]) / wc)
    for i, hk in enumerate(kutular + [fk]):
        F, al, bb = ogeler_al[i]; s = olc[i]
        F = F[bb[1]:bb[3], bb[0]:bb[2]]; al = al[bb[1]:bb[3], bb[0]:bb[2]]
        nw, nh = max(1, round(F.shape[1] * s)), max(1, round(F.shape[0] * s))
        Fi = np.asarray(Image.fromarray(F.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)
        ai = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float64)[..., None] / 255
        cx, cy = (hk[0] + hk[2]) / 2, (hk[1] + hk[3]) / 2; px, py = int(round(cx - nw / 2)), int(round(cy - nh / 2))
        P[py:py + nh, px:px + nw] = P[py:py + nh, px:px + nw] * (1 - ai) + Fi * ai
    a[y0:y1, x0:x1] = P
    R['kart04'] = {'olcek': [round(v, 4) for v in olc], 'kucuk_kutu': [list(map(int, k)) for k in kutular], 'birlesik_kutu': list(map(int, fk))}
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), flat

# ------------------------------------------------------------------ kart 07 (yakin detay)
INSET07 = (170, 717, 952, 1692); PANEL07 = (1169, 569, 2821, 1854); CIZGI = (147, 118, 73)

DETAY_ESIK = {'murekkep_oran': 0.15, 'halka_px': 0}               # Serdar 25 Eyl: buyutec = sembolun birlesim bolgesi
DETAY_KUTU_ORAN = 0.224     # buyutec kutusu / poster eni: canli CL kart 07'de olculdu (kutu 175 px / inset poster 781 px)

def detay(al_mb, hi, B):
    """Buyutec: birlesik sembolun BIRLESIM bolgesi (Serdar 25 Eyl, CL kart 06 mantigi). Aday kutular (panel en/boy):
    sembol murekkebi >= %15 ve dis halka pikseli 0; aralarindan kenarini en cok cizginin kestigi kutu
    (en cok vurusun bulustugu yer), esitlikte sembol merkezine en yakin. Baski dosyasindan (buyutme <= 1.5)."""
    import cv2
    from scipy import ndimage
    tw, th = PANEL07[2] - PANEL07[0], PANEL07[3] - PANEL07[1]
    f = hi.width / al_mb.width; kw = round(DETAY_KUTU_ORAN * al_mb.width); kh = round(kw * th / tw)
    ust = birlesik_maske(B)
    tum = B['m'].copy(); tum[B['o']['sembol_bant'][0] - 40:] = False
    halka = tum & ~ndimage.binary_dilation(ust, iterations=4)
    ii = ust.astype(np.float64).cumsum(0).cumsum(1); ih = halka.astype(np.float64).cumsum(0).cumsum(1)
    top = lambda I, x, y: I[y + kh - 1, x + kw - 1] - I[y, x + kw - 1] - I[y + kh - 1, x] + I[y, x]
    def kesen(x, y):
        c = np.concatenate([ust[y, x:x + kw], ust[y:y + kh, x + kw - 1], ust[y + kh - 1, x:x + kw][::-1], ust[y:y + kh, x][::-1]]).astype(int)
        return int((np.diff(c) == 1).sum())
    ys, xs = np.where(ust); cx, cy = xs.mean(), ys.mean(); en = None
    for y in range(0, ust.shape[0] - kh, 8):
        for x in range(0, ust.shape[1] - kw, 8):
            if top(ii, x, y) / (kw * kh) < DETAY_ESIK['murekkep_oran'] or top(ih, x, y) > DETAY_ESIK['halka_px']: continue
            a = (kesen(x, y), -np.hypot(x + kw / 2 - cx, y + kh / 2 - cy), x, y)
            if en is None or a > en: en = a
    if en is None: raise SystemExit('HATA: kart 06 buyutec kapisi: uygun birlesim kutusu yok')
    kesis, _, bx, by = en
    kapi = {'murekkep_oran': round(float(top(ii, bx, by) / (kw * kh)), 3), 'halka_px': int(top(ih, bx, by)), 'kesen_cizgi': kesis, 'esik': DETAY_ESIK}
    kapi['gecti'] = kapi['murekkep_oran'] >= DETAY_ESIK['murekkep_oran'] and kapi['halka_px'] <= DETAY_ESIK['halka_px']
    kutu = (bx, by, bx + kw, by + kh)
    Hk = np.asarray(hi.convert('L').resize((al_mb.width, round(hi.height / f)), Image.LANCZOS)).astype(np.uint8)
    pad = 60; Pt = np.asarray(al_mb.convert('L')).astype(np.uint8)[by - pad:by + kh + pad, bx - pad:bx + kw + pad]
    r = cv2.matchTemplate(Hk, Pt, cv2.TM_CCOEFF_NORMED); _, sk, _, (lx, ly) = cv2.minMaxLoc(r)
    dx, dy = lx - (bx - pad), ly - (by - pad)
    hb = tuple(round((v + d) * f) for v, d in zip(kutu, (dx, dy, dx, dy))); buy = tw / (hb[2] - hb[0])
    if buy > 1.5: raise SystemExit(f'HATA: detay buyutmesi {buy:.2f} > 1.5')
    return hi.crop(hb).resize((tw, th), Image.LANCZOS), kutu, {'baski_boyut': [hi.width, hi.height], 'eslesme': round(float(sk), 4),
                                                            'ofset': [int(dx), int(dy)], 'buyutme': round(buy, 3), 'poster_kutu': list(map(int, kutu)),
                                                            'kapi': kapi}

def kart07(kart, cl_mb, al_mb, hi, B):
    a = np.asarray(kart.convert('RGB')).copy()
    a[1040:1060, 952:1169] = BG.astype(np.uint8)                   # eski baglanti cizgisi
    k = Image.fromarray(a)
    yer = sahne_yer(k, cl_mb, (INSET07[0] - 30, INSET07[1] - 30, INSET07[2] + 30, INSET07[3] + 30))
    iw = INSET07[2] - INSET07[0]                                    # inset tam poster: genislik insete esit, oran 4:5 (tek olcek)
    yer.update({'x': INSET07[0], 'y': INSET07[1], 'w': iw, 'h': round(iw * 1.25), 'aciklik': list(INSET07)})
    k = A.yerlestir(k, al_mb, yer)
    crop, kutu, bilgi = detay(al_mb, hi, B)
    a = np.asarray(k).copy(); a[PANEL07[1]:PANEL07[3], PANEL07[0]:PANEL07[2]] = np.asarray(crop.convert('RGB')); k = Image.fromarray(a)
    s = yer['w'] / al_mb.width
    bx0, by0 = yer['x'] + kutu[0] * s, yer['y'] + kutu[1] * s; bx1, by1 = yer['x'] + kutu[2] * s, yer['y'] + kutu[3] * s
    d = ImageDraw.Draw(k); d.rectangle([bx0, by0, bx1, by1], outline=CIZGI, width=4); yc = (by0 + by1) / 2
    d.line([(bx1, yc), (PANEL07[0], yc)], fill=CIZGI, width=4)
    R['kart07'] = {'inset': yer, 'detay': bilgi}
    return k

# ------------------------------------------------------------------ kapi: kartta baska burc adi
def burc_tarama(kart, beklenen):
    t = A.ocr(kart.convert('L'), '3').upper()
    bulunan = sorted({b for b in A.BURCLAR if re.search(rf'\b{b}\b', t)})
    return {'bulunan': bulunan, 'gecti': set(bulunan) <= set(beklenen)}

def yanyana(sol, sag, yol, H=900):
    a = sol.resize((round(sol.width * H / sol.height), H), Image.LANCZOS); b = sag.resize((round(sag.width * H / sag.height), H), Image.LANCZOS)
    c = Image.new('RGB', (a.width + b.width + 30, H + 40), 'white'); c.paste(a, (0, 40)); c.paste(b, (a.width + 30, 40))
    d = ImageDraw.Draw(c); d.text((10, 10), 'CANCER + LIBRA (canli referans)', fill=(0, 0, 0)); d.text((a.width + 40, 10), CIFT.replace('_', ' + '), fill=(0, 0, 0))
    c.save(yol, quality=90)

def wp_buyutme(im, yer, psize, M, ad, k=3):
    """Warm Parchment x3 (Serdar incelemesi): sembol bolgesi + isim/mesaj bandi; poster koordinatlari sahneye olceklenir."""
    PW, PH = psize; x, y, w, h = yer; sx, sy = w / PW, h / PH
    sb, ib = M['o']['sembol_bant'], M['o']['isim_bant']; tb = M['tag_bant'] or [ib[1] + 200, ib[1] + 330]
    bolge = {'sembol': (0, sb[0] - 120, PW, sb[1] + 40), 'isim_mesaj': (0, ib[0] - 60, PW, tb[1] + 60)}
    for b, (a0, b0, a1, b1) in bolge.items():
        kutu = (round(x + a0 * sx), round(y + b0 * sy), round(x + a1 * sx), round(y + b1 * sy))
        c = im.crop(kutu)
        if c.width * k > 6000: c = c.resize((6000 // k, round(c.height * 6000 / k / c.width)), Image.LANCZOS)
        c.resize((c.width * k, c.height * k), Image.LANCZOS).save(CIK / f'WP_x3_{ad}_{b}.jpg', quality=93)

def onizleme(S, SIRA, yol, H=900, gen=4200, bosluk=30):
    """Galeri sirasiyla tum gorseller, gercek oranda (ayni yukseklik, en/boy korunur), tek sayfa."""
    ims = [(i, ad, S[n].resize((round(S[n].width * H / S[n].height), H), Image.LANCZOS)) for i, (n, ad) in enumerate(SIRA, 1)]
    satir, cur, gx = [], [], 0
    for t in ims:
        if cur and gx + t[2].width > gen: satir.append(cur); cur, gx = [], 0
        cur.append(t); gx += t[2].width + bosluk
    satir.append(cur)
    Wt = max(sum(t[2].width + bosluk for t in r) for r in satir) + bosluk
    T = Image.new('RGB', (Wt, len(satir) * (H + 70) + bosluk), 'white'); d = ImageDraw.Draw(T)
    for j, r in enumerate(satir):
        xx = bosluk; yy = bosluk + j * (H + 70)
        for i, ad, t in r:
            T.paste(t, (xx, yy + 50)); d.text((xx, yy + 10), f'{i:02d} {ad} ({S[SIRA[i - 1][0]].width}x{S[SIRA[i - 1][0]].height})', fill=(0, 0, 0)); xx += t.width + bosluk
    T.save(yol, quality=88)

def kart04_tam(ref, M, etk, A_, B_):
    k4, flat = kart04(ref[4], M, M['blue']['Bc'])
    k4 = etiket_yaz(k4, etk)
    k4 = metin(k4, (130, 325, 1700, 395), 'Cancer and Libra, united in an original AstroLove design.',
               f'{A_.title()} and {B_.title()}, united in an original AstroLove design.')
    k4 = metin(k4, (1540, 860, 1790, 945), 'CANCER', A_, align='center', bg=flat)
    return metin(k4, (2380, 860, 2580, 945), 'LIBRA', B_, align='center', bg=flat)

# ------------------------------------------------------------------ ana akis
if __name__ == '__main__':
    t_bas = time.time()
    try:
        if not YEREL:
            A.kisisel_hazirla()
            import edisyon_uret as E
            for ed in RENKLER[1:]:
                (E.YOL / ed / 'zemin').mkdir(parents=True, exist_ok=True)
                rc('copy', f'{KP}/HAZIR/zemin_{ed}_4x5.png', str(E.YOL / ed / 'zemin'))
                (E.YOL / ed / 'zemin' / f'zemin_{ed}_4x5.png').rename(E.YOL / ed / 'zemin' / '4x5.png')
            if not HAM_HAZIR: rc('copy', SAYFA_HAM, str(W / 'ham'))
            rc('copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'ref'), '--include', '*.jpg')
            rc('copy', f'{DR}/REVIEW/GENEL', str(W / 'genel'), '--include', 'GENEL_[234]_*.png')
            rc('copy', f'{A.POD}/{CIFT}/MIDNIGHT_BLUE/30x40.jpg', str(W / 'hi'))
            if KART3_YOL: rc('copyto', KART3_YOL, str(W / 'k3' / 'KART3.jpg'))
            else:
                try: rc('copy', f'{A.A77}/{CIFT}/KART3.jpg', str(W / 'k3'))
                except Exception: rc('copy', f'{DR}/REVIEW/A_ORNEK/VIDEO_KART3/KART3_{CIFT}.jpg', str(W / 'k3'))
            if not list((W / 'k3').glob('*.jpg')): raise SystemExit(f'HATA: kart 3 yok ({CIFT})')
        ciftler = sorted(x.strip('/') for x in rc('lsf', A.POD, '--dirs-only').split()) if not YEREL else json.loads((W / 'ciftler.json').read_text())
        NO = ciftler.index(CIFT) + 1; assert ciftler.index(REF_CIFT) + 1 == 28
        R['sayfa'] = NO
        sayfa = {p.stem: p.read_bytes() for p in (W / 'ham').glob('*.png')}
        log('girdiler', sorted(sayfa), 'sayfa', NO)
        onbellek = W / 'poster_onbellek.pkl'
        if YEREL and onbellek.exists():                          # yalniz yerel yineleme: posterler yeniden render edilmez
            import pickle; P, M, R['poster'] = pickle.loads(onbellek.read_bytes())
        else:
            P, M = posterler(sayfa)
            if YEREL:
                import pickle; M2 = {'blue': {k: v for k, v in M['blue'].items() if k != 'X'}}
                onbellek.write_bytes(pickle.dumps((P, M2, R['poster'])))
        ref = {n: Image.open(W / 'ref' / f'{f}.jpg').convert('RGB') for n, f in REF_DOSYA.items()}
        etk = A.etiketler()[CIFT]; A_, B_ = etk.split(' + ')
        if YALNIZ06:
            SIRA6 = [(1, 'kapak_MB'), (3, 'kart3_isimler'), (4, 'ortak_sembol'), (5, 'bes_palet'), (6, 'GENEL_3_kagit'), (7, 'yakin_detay'),
                     (8, 'GENEL_2_olcu'), (9, 'eser_isim_mesaj'), (10, 'GENEL_4_siparis'), (11, 'cerceve_DEEP_BLACK'),
                     (12, 'cerceve_CHAMPAGNE_IVORY'), (13, 'cerceve_PURE_WHITE'), (14, 'cerceve_WARM_PARCHMENT')]
            if not YEREL: rc('copy', HEDEF, str(CIK), '--include', '[01][0-9]_*.jpg')
            S = {n: Image.open(CIK / f'{i:02d}_{ad}.jpg').convert('RGB') for i, (n, ad) in enumerate(SIRA6, 1) if n != 7}
            S[7] = etiket_yaz(kart07(ref[7], P['blue']['CL'], P['blue']['AL'], Image.open(W / 'hi' / '30x40.jpg').convert('RGB'), M['blue']['B']), etk)
            bt = burc_tarama(S[7], sorted({A_, B_}))
            S[7].save(CIK / '06_yakin_detay.jpg', quality=95); yanyana(ref[7], S[7], CIK / 'YANYANA_06_yakin_detay_vs_CL07.jpg')
            onizleme(S, SIRA6, CIK / f'ONIZLEME_TAM_SET_{CIFT}.jpg')
            R['ozet'] = {'yalniz': 'kart 06', 'buyutec_kapisi': R['kart07']['detay']['kapi'], 'burc_kapisi': bt['gecti'],
                         'poster_kapisi': R['poster']['blue']['gecti'], 'sure_sn': round(time.time() - t_bas, 1)}
            if not YEREL:
                for f in ('06_yakin_detay.jpg', 'YANYANA_06_yakin_detay_vs_CL07.jpg', f'ONIZLEME_TAM_SET_{CIFT}.jpg'): rc('copy', str(CIK / f), HEDEF)
                (CIK / 'RAPOR_KART06.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str)); rc('copy', str(CIK / 'RAPOR_KART06.json'), HEDEF)
            print(json.dumps(R['ozet'], ensure_ascii=False, indent=1, default=str), flush=True); sys.exit(0)
        beklenen = sorted({A_, B_})
        S = {}; K = {}
        if DUZELT:                                               # korunan kartlar Drive'daki dosyalarindan (yeniden kodlanmaz)
            if not YEREL: rc('copy', HEDEF, str(CIK), '--include', '0[1-4]_*.jpg', '--include', '08_*.jpg')
            for n, dosya in ((1, '01_kapak_MB.jpg'), (3, '02_kart3_isimler.jpg'), (4, '03_ortak_sembol.jpg'), (9, '08_eser_isim_mesaj.jpg')):
                S[n] = Image.open(CIK / dosya).convert('RGB')
        # 01 kapak (onayli a1 kurali)
        if 1 not in KORU:
            yk = A.kapak_yer(ref[1], P['blue']['CL'], A.aciklik_olc(ref[1])); S[1] = A.yerlestir(ref[1], P['blue']['AL'], yk)
            K[1] = {'yer': yk, 'aciklik_disi_maks_fark': dis_fark(ref[1], S[1], yk)}
        # 03 kart 3 (video oturumu)
        if 3 not in KORU: S[3] = Image.open(next((W / 'k3').glob('*.jpg'))).convert('RGB')
        # 04 ortak sembol
        if 4 not in KORU: S[4] = kart04_tam(ref, M, etk, A_, B_)
        # 05 bes palet
        k5 = ref[5]; K[5] = {}
        for rect, renk in (((269, 499, 791, 1151), 'blue'), ((1240, 500, 1760, 1150), 'black'), ((2208, 497, 2734, 1152), 'modern'),
                           ((755, 1310, 1275, 1960), 'pure_white'), ((1722, 1306, 2248, 1963), 'vintage')):
            if renk not in P: continue                             # yalniz yerel deneme
            y = sahne_yer(k5, P[renk]['CL'], (rect[0] - 30, rect[1] - 30, rect[2] + 30, rect[3] + 30))
            y['aciklik'] = [max(y['x'], rect[0] - 4), max(y['y'], rect[1] - 4), min(y['x'] + y['w'], rect[2] + 4), min(y['y'] + y['h'], rect[3] + 4)]
            k5 = A.yerlestir(k5, P[renk]['AL'], y); K[5][renk] = y
        S[5] = etiket_yaz(k5, etk)
        # 07 yakin detay
        S[7] = etiket_yaz(kart07(ref[7], P['blue']['CL'], P['blue']['AL'], Image.open(W / 'hi' / '30x40.jpg').convert('RGB'), M['blue']['B']), etk)
        # 09 KART09
        if 9 not in KORU:
            X9 = A.k9_hazirla(ref[9]); y9 = A.yer_olc(ref[9], P['blue']['CL'], A.SAHNE['kart09'][1])
            S[9] = A.kart09_uret(X9, P['blue']['AL'], y9, etk)
            K[9] = A.k9_kapisi(S[9], X9, etk, list(A.etiketler().values()), y9)
        # 06 kagit: CL 06 ile birebir duzen + ciftin posteri (Serdar 25 Eyl); 08/10 GENEL + ust satirda cift adi
        S[6], K[6] = kart_kagit(ref[6], P['blue']['CL'], P['blue']['AL'], etk)
        S[8] = baslik_ekle(Image.open(W / 'genel' / 'GENEL_2_olcu.png').convert('RGB'), ref[8], etk)
        S[10] = baslik_ekle(Image.open(W / 'genel' / 'GENEL_4_siparis.png').convert('RGB'), ref[10], etk)
        R['baslik_kapisi'] = {n: baslik_kapisi(S[n], etk) for n in (5, 6, 7, 8, 10)}
        R['mesaj_kapisi'] = mesaj_kapisi(M)
        # 11-14 renk sahneleri
        for n, renk in SAHNE_RENK.items():
            if renk not in P: S[n] = ref[n]; continue           # yalniz yerel deneme
            y = sahne_yer(ref[n], P[renk]['CL'], (60, 60, ref[n].width - 60, ref[n].height - 60))
            S[n] = A.yerlestir(ref[n], P[renk]['AL'], y); K[n] = {'yer': y, 'aciklik_disi_maks_fark': dis_fark(ref[n], S[n], y)}
        R['sahne'] = K
        # Etsy sirasi (CL 02 cikar): 13 foto
        SIRA = [(1, 'kapak_MB'), (3, 'kart3_isimler'), (4, 'ortak_sembol'), (5, 'bes_palet'), (6, 'GENEL_3_kagit'), (7, 'yakin_detay'),
                (8, 'GENEL_2_olcu'), (9, 'eser_isim_mesaj'), (10, 'GENEL_4_siparis'), (11, 'cerceve_DEEP_BLACK'),
                (12, 'cerceve_CHAMPAGNE_IVORY'), (13, 'cerceve_PURE_WHITE'), (14, 'cerceve_WARM_PARCHMENT')]
        R['galeri'] = []; kucuk = []
        for i, (n, ad) in enumerate(SIRA, 1):
            im = S[n]; dosya = f'{i:02d}_{ad}.jpg'
            if n == 3 and A77MOD:                                # kart 3 onayli dosya: bayt bayt kopya (yeniden kodlanmaz)
                import shutil; shutil.copyfile(next((W / 'k3').glob('*.jpg')), CIK / dosya)
            elif n not in KORU: im.save(CIK / dosya, quality=95)
            bt = burc_tarama(im, beklenen)
            R['galeri'].append({'sira': i, 'dosya': dosya, 'cl_karsiligi': f'CL {n:02d} ({REF_DOSYA[n]})', 'boyut': list(im.size),
                                'ref_boyut': list(ref[n].size), 'burc_kapisi': bt})
            if n not in KORU: yanyana(ref[n], im, CIK / f'YANYANA_{i:02d}_{ad}_vs_CL{n:02d}.jpg')
            t = im.copy(); t.thumbnail((600, 600)); kucuk.append((i, ad, t))
        sw = 620; T = Image.new('RGB', (sw * 7, 2 * 640), 'white'); d = ImageDraw.Draw(T)
        for j, (i, ad, t) in enumerate(kucuk):
            x, y = (j % 7) * sw, (j // 7) * 640; T.paste(t, (x + (600 - t.width) // 2, y)); d.text((x, y + 610), f'{i:02d} {ad}', fill=(0, 0, 0))
        T.save(CIK / f'SERIT_TAM_SET_{CIFT}.jpg', quality=90)
        onizleme(S, SIRA, CIK / f'ONIZLEME_TAM_SET_{CIFT}.jpg')
        if 'vintage' in P:                                       # Warm Parchment x3 (poster, kart 05, kart 14)
            pv = P['vintage']['AL']; wp_buyutme(pv, (0, 0, pv.width, pv.height), pv.size, M['vintage'], 'POSTER')
            v5 = K[5]['vintage']; wp_buyutme(S[5], (v5['x'], v5['y'], v5['w'], v5['h']), pv.size, M['vintage'], 'KART05')
            v14 = K[14]['yer']; wp_buyutme(S[14], (v14['x'], v14['y'], v14['w'], v14['h']), pv.size, M['vintage'], 'KART14')
        # SET.json (pod galeri_tek.py okur): galeri sirasi, renk baglari, video yolu
        RENK_BAGI = {1: 'Midnight Blue', 11: 'Deep Black', 12: 'Champagne Ivory', 13: 'Pure White', 14: 'Warm Parchment'}
        TUR = {1: 'kapak', 3: 'kart', 4: 'kart', 5: 'kart', 6: 'kart', 7: 'kart', 8: 'kart', 9: 'kart', 10: 'kart',
               11: 'renk', 12: 'renk', 13: 'renk', 14: 'renk'}
        video = None
        if VIDEO_YOL: video = VIDEO_YOL
        elif not YEREL:
            try: video = next((f'{A.A77}/{CIFT}/{x}' for x in rc('lsf', f'{A.A77}/{CIFT}', '--include', '*.mp4').split() if x), None)
            except Exception: video = None
            if not video:
                yedek = f'{DR}/REVIEW/A_ORNEK/VIDEO_KART3/YENI_AstroLove_{CIFT}_12.6s.mp4'
                try: video = yedek if rc('lsf', yedek).strip() else None
                except Exception: video = None
        SET = {'cift': CIFT, 'etiket': etk, 'surum': 'tam_set_v1', 'referans_ilan': 4570143815,
               'klasor': HEDEF, 'foto_sayisi': len(SIRA),
               'galeri': [{'sira': i, 'dosya': f'{i:02d}_{ad}.jpg', 'tur': TUR[n], 'renk': RENK_BAGI.get(n),
                           'cl_karsiligi': n, 'boyut': list(S[n].size)} for i, (n, ad) in enumerate(SIRA, 1)],
               'renk_gorselleri': {RENK_BAGI[n]: f'{i:02d}_{ad}.jpg' for i, (n, ad) in enumerate(SIRA, 1) if n in RENK_BAGI},
               'video': {'yol': video, 'durum': 'bulundu' if video else 'yok (video oturumu)'},
               'onay': 'BEKLIYOR (Serdar)'}
        (CIK / 'SET.json').write_text(json.dumps(SET, ensure_ascii=False, indent=1))
        kapilar_ok = (all(R['poster'][r]['gecti'] for r in RENKLER) and all(g['burc_kapisi']['gecti'] for g in R['galeri'])
                      and (K[9]['gecti'] if 9 in K else True) and R['mesaj_kapisi']['gecti']
                      and all(v['gecti'] for v in R['baslik_kapisi'].values()) and R['kart07']['detay']['kapi']['gecti'])
        R['gecti'] = bool(kapilar_ok)
        if not YEREL and R['gecti']: rc('copy', str(CIK / 'SET.json'), f'{A.A77}/{CIFT}')
        R['ozet'] = {'foto': len(SIRA), 'poster_kapilari': {r: R['poster'][r]['gecti'] for r in RENKLER},
                     'burc_kapisi': all(g['burc_kapisi']['gecti'] for g in R['galeri']), 'kart09_kapisi': K[9]['gecti'] if 9 in K else 'korundu',
                     'mesaj_kapisi': {k: R['mesaj_kapisi'][k] for k in ('px', 'renkler_arasi_fark', 'CL_ustu_degil', 'gecti')},
                     'baslik_kapisi': R['baslik_kapisi'], 'kagit_kart_dis_fark': K[6]['aciklik_disi_maks_fark'],
                     'kart06_buyutec_kapisi': R['kart07']['detay']['kapi']['gecti'], 'gecti': R['gecti'], 'video': video,
                     'sure_sn': round(time.time() - t_bas, 1)}
    finally:
        if not YALNIZ06:                                         # kart 06 kosusu tam set raporunu/klasorunu ezmez
            (CIK / 'RAPOR_TAM_SET.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
            if not YEREL and not A77MOD: rc('copy', str(CIK), HEDEF)
            elif not YEREL and R.get('gecti'):                   # 77: yalniz kapidan gecen set; buyuk ara dosyalar yuklenmez
                rc('copy', str(CIK), HEDEF, '--include', '[01][0-9]_*.jpg', '--include', 'SET.json', '--include', 'RAPOR_TAM_SET.json',
                   '--include', 'ONIZLEME_*.jpg', '--include', 'SEMBOL_*.jpg')
        print(json.dumps(R.get('ozet'), ensure_ascii=False, indent=1, default=str), flush=True)
