#!/usr/bin/env python3
"""A1 (Serdar 25 Eyl): isimli poster + kapak, 2 ornek cift. Actions (kisisel-pilot kosucusu). Etsy'ye erisim YOK.

SARMALAYICI poster(cift_sayfa, renk, oran, isimler, tagline): kisisel-v1 render kodu DEGISTIRILMEDEN kullanilir
(dal arsivden cikarilir). Degisen yalniz girdiler:
  - pilot16.REF_SAYFA = ciftin sayfasi (modul degiskeni, kod degil)
  - olcum kaydi: o sayfanin KENDI olcumu (pilot11.sayfa_olc); ozet/bg OLCUM.json'dan
  - bg hizasi o sayfadan olculur (kalibre=True); sonuc yalniz calisma kopyasina yazilir, Drive'daki kilit degismez
  - kalinti kapisi (blok_kapisi) ve temiz ara zemin kapisi acik; sonuc raporlanir
Kapak / kart 09: Cancer-Libra posteri ayni sarmalayiciyla uretilir, canli ilan gorseline sablon eslestirmeyle
oturtulur (olcek + konum olculur), sonra o alanin TAMAMI ciftin posteriyle degisir; sahnenin geri kalani ayni.
Girdi: Drive KISISEL_PILOT/A1_LISTE.json {"sayfa": {"1": url, ...}} (imzali URL'ler, loga maskeli, kosu sonunda silinir)
Cikti: Drive .../AQUARIUS_AQUARIUS_v1/REVIEW/A_ORNEK/"""
import io, json, re, subprocess, sys, time, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KP = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
DR = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/AQUARIUS_AQUARIUS_v1'
W = Path('_a1').resolve(); W.mkdir(exist_ok=True)
CIK = W / 'A_ORNEK'; CIK.mkdir(exist_ok=True)
K = W / 'kisisel'                                   # kisisel-v1 dal arsivi (degistirilmez)
ORNEK = [('AQUARIUS_AQUARIUS', 4570110121), ('ARIES_LEO', 4570031205)]
REF_CIFT = 'CANCER_LIBRA'
ISIM = ('EMILY', 'JAMES'); TAG = 'It Began With a Kiss in the Rain'
RENK = 'MIDNIGHT_BLUE'; ORAN = '4x5'
# canli ilan gorsellerinde poster alaninin kaba yeri (goreli); kesin yer eslestirmeyle olculur
SAHNE = {'kapak': (0, (0.10, 0.09, 0.90, 0.91)), 'kart09': (8, (0.04, 0.24, 0.42, 0.86))}

def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)
def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a], capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r.stdout
def sh(*a): subprocess.run(list(a), check=True)
def maskele(u):
    print(f'::add-mask::{u}', flush=True)
    for p in u.split('&'):
        if p.startswith('X-Amz-Signature='): print(f'::add-mask::{p.split("=", 1)[1]}', flush=True)
def indir(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=180) as r: return r.read()
        except Exception as e:                                    # noqa: BLE001
            son = e; time.sleep(2 ** i)
    raise RuntimeError(f'indirilemedi: {son}')

def kisisel_hazirla():
    sh('git', 'fetch', '--depth', '1', 'origin', 'kisisel-v1')
    K.mkdir(exist_ok=True)
    arc = subprocess.run(['git', 'archive', 'FETCH_HEAD', 'scripts/kisisel', 'assets'], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-C', str(K)], input=arc, check=True)
    sys.path.insert(0, str(K / 'scripts' / 'kisisel'))

def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum()); return float((a * b).sum() / d) if d else 0.0

# ------------------------------------------------------------------ SARMALAYICI
SEMBOL_BIRLES = 40      # px: ayni sembolun ust/alt parcalari (orn. Kova'nin iki dalgasi) arasindaki en buyuk bosluk
GOVDE_ORAN = 0.25       # isim bandinda govde satiri: murekkep >= medyan satirin %25'i (Q kuyrugu gibi inenler haric)
SEMBOL_KAYMA = 8        # sembol kapisi arama penceresi (px)
SEMBOL_UST = 80         # sembol kapisi bolgesi: olculen sembol bandinin bu kadar ustunden baslar (banda bagimsiz)

def murekkep(ref_norm):
    from pilot6 import LUMA, MUREKKEP
    return (np.asarray(ref_norm).astype(np.float32) @ LUMA) > MUREKKEP

def olcum_duzelt(o, m):
    """sayfa_olc sonucunu sayfanin kendisinden duzeltir (render kodu degismez, yalniz girdisi).
    1) Sembol bandi: olculen bandin USTUNDE veya ALTINDA (isim bandindan once) <= SEMBOL_BIRLES px bosluklu komsu
       bantlar, butun kumeleri bir sembolun x araliginda ise ayni sembolun parcasidir (Kova'nin ust dalgasi, Terazi'nin
       alt cizgisi); banda ve o sembolun x araligina katilir.
    2) Isim govde bandi: inen kuyruklar (Q) haric satirlar; isim_y ve punto tavani icin."""
    import pilot11
    from pilot6 import kumeler
    d = dict(o); ek = []
    sb = list(d['sembol_bant']); sx = [list(x) for x in d['sembol']]
    ib0 = d['isim_bant'][0]
    def ortusur(c, x): return min(c[1], x[1]) - max(c[0], x[0]) > 0.5 * (c[1] - c[0])
    bl = pilot11.bantlar(m); degisti = True
    while degisti:                                   # ust VE alt komsu bantlar (Kova'nin ust dalgasi, Terazi'nin alt cizgisi)
        degisti = False
        for b in bl:
            if b[0] >= sb[0] and b[1] <= sb[1]: continue
            ust = b[1] <= sb[0] and sb[0] - b[1] <= SEMBOL_BIRLES
            alt = b[0] >= sb[1] and b[0] - sb[1] <= SEMBOL_BIRLES and b[1] <= ib0 - 10
            if not (ust or alt): continue
            k = [c for c in kumeler(m[b[0]:b[1]], 20) if c[1] - c[0] > 30]
            if not k or not all(any(ortusur(c, x) for x in sx) for c in k): continue
            for c in k:
                i = next(i for i in (0, 1) if ortusur(c, sx[i])); sx[i] = [min(c[0], sx[i][0]), max(c[1], sx[i][1])]
            sb = [min(sb[0], b[0]), max(sb[1], b[1])]; ek.append(list(b)); degisti = True
    d['sembol_bant'], d['sembol'] = sb, sx
    d['sembol_merkez'] = [round((x[0] + x[1]) / 2, 1) for x in sx]
    b0, b1 = d['isim_bant']; satir = np.zeros(b1 - b0)
    for k in ('sol_isim', 'sag_isim'):
        satir += m[b0:b1, d[k][0]:d[k][1]].sum(1)
    ok = satir >= GOVDE_ORAN * np.median(satir[satir > 0]); kos, en, i = None, 0, 0
    while i < len(ok):                                          # en uzun kesintisiz govde kosusu
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]: j += 1
            if j - i > en: en, kos = j - i, (i, j)
            i = j
        else: i += 1
    d['isim_govde'] = [int(b0 + kos[0]), int(b0 + kos[1])]
    return d, {'sembol_ek_bant': ek, 'sembol_bant_ilk': o['sembol_bant'], 'isim_govde': d['isim_govde'], 'isim_bant': o['isim_bant']}

def sembol_kapisi(poster, S, s, merkez, m_src, esik, ink=None):
    """YENI KAPI: kucuk sembol bolgesi kaynak sayfadakiyle birebir mi? (olcek/aynalama/parca kaymasi yok)
    Bolge olculen banda BAGLI DEGIL: sembol x araligi (+pay) x [sembol bandi ustu - SEMBOL_UST, isim bandi ustu - 5].
    Bolgeye tamamen sigan murekkep bilesenleri (daire yayi gibi disari tasanlar haric) sembolun tamamidir.
    Yeni posterde ayni bilesenler TEK bir yatay kaymayla (|dx| <= 1 yuvarlama, dy = 0) aranir;
    murekkep piksellerinde ortalama mutlak fark <= esik['fark'] ve murekkep IoU >= esik['iou'] olmali."""
    import cv2
    from pilot6 import LUMA, MUREKKEP
    ref = np.asarray(S['ref']).astype(np.float32); P = np.asarray(poster.convert('RGB')).astype(np.float32)
    Pm = ink(P) if ink else (P @ LUMA) > MUREKKEP; sonuc, kirp = {}, {}
    def ic(mk):                                                 # bolgeye tamamen sigan bilesenler
        n, lab, st, _ = cv2.connectedComponentsWithStats(mk.astype(np.uint8), 8); h, w = mk.shape; out = np.zeros_like(mk)
        for i in range(1, n):
            x, y, bw, bh, a = st[i]
            if a >= 20 and x > 0 and y > 0 and x + bw < w and y + bh < h: out |= lab == i
        return out
    for y in ('sol', 'sag'):
        o = S['oge'][f'sembol_{y}']; g = o['gorsel']; pay = 14
        x0, x1 = g[0] - pay, g[2] + pay
        y0, y1 = s['sembol_bant'][0] - SEMBOL_UST, s['isim_bant'][0] - 5
        src = ref[y0:y1, x0:x1]; mk = ic(m_src[y0:y1, x0:x1])
        ex = int(round(merkez[y] - o['w'] / 2)) - (g[0] - x0) + (g[0] - o['gorsel'][0])
        en = None
        for dy in range(-SEMBOL_KAYMA, SEMBOL_KAYMA + 1):
            for dx in range(-SEMBOL_KAYMA, SEMBOL_KAYMA + 1):
                q = P[y0 + dy:y1 + dy, ex + dx:ex + dx + (x1 - x0)]
                f = float(np.abs(q - src).max(2)[mk].mean())
                if en is None or f < en[0]: en = (f, dx, dy)
        f, dx, dy = en
        q = P[y0 + dy:y1 + dy, ex + dx:ex + dx + (x1 - x0)]; qm = ic(Pm[y0 + dy:y1 + dy, ex + dx:ex + dx + (x1 - x0)])
        iou = float((qm & mk).sum() / max((qm | mk).sum(), 1))
        sonuc[y] = {'fark': round(f, 2), 'dx': dx, 'dy': dy, 'iou': round(iou, 4), 'kaynak_kutu': [x0, y0, x1, y1],
                    'murekkep_px': int(mk.sum()), 'gecti': abs(dx) <= 1 and dy == 0 and f <= esik['fark'] and iou >= esik['iou']}
        kirp[y] = (Image.fromarray(src.astype(np.uint8)), Image.fromarray(q.astype(np.uint8)))
    return {'gecti': all(v['gecti'] for v in sonuc.values()), 'esik': esik, **sonuc}, kirp

def sembol_gorseli(kirp, ad, buyut=3):
    """'kaynak | yeni' buyutulmus gorsel (sol ve sag sembol alt alta)."""
    satir = []
    for y in ('sol', 'sag'):
        a, b = [im.resize((im.width * buyut, im.height * buyut), Image.NEAREST) for im in kirp[y]]
        c = Image.new('RGB', (a.width + b.width + 24, a.height), 'white'); c.paste(a, (0, 0)); c.paste(b, (a.width + 24, 0)); satir.append(c)
    t = Image.new('RGB', (max(r.width for r in satir), sum(r.height for r in satir) + 24), 'white'); yy = 0
    for r in satir: t.paste(r, (0, yy)); yy += r.height + 24
    t.save(CIK / ad, quality=95)

# ------------------------------------------------------------------ tagline taban cizgisi (Serdar 25 Eyl)
TAG_TABAN_ESIK = {'taban_px': 0, 'renk': 6.0}

def tag_plaka_taban(s, S, metin):
    """kisisel-v1 tagline_plaka ile ayni plaka; plakadaki taban cizgisi (T harfinin alti) ve plaka yuksekligi."""
    import pilot12, pilot6
    pl, info = pilot12.tagline_plaka(s, {'prof': S['prof']}, metin)
    cr, cu, ct = pilot6.ciz_cap(pilot12.FONT_DIR / pilot12.TAG_FONT, pilot12.TAG_W, info['punto'], metin)
    a = np.asarray(pl)[..., 3] > 40; ust = int(np.where(a.any(1))[0][0])
    return pl.height, ust + ct

def taban_hizala(s, S, metin, ref=TAG):
    """Render kodu plakayi kutu merkezine koyar (ty = tag_y - h/2); inen harfi olmayan slogan asagi kayar.
    Sarmalayici tag_y'yi, metnin taban cizgisi referans sloganin (EJ) taban cizgisine denk gelecek sekilde verir."""
    if metin == ref: return s
    h_r, b_r = tag_plaka_taban(s, S, ref); h_m, b_m = tag_plaka_taban(s, S, metin)
    hedef = int(round(s['tag_y'] - h_r / 2)) + b_r              # EJ taban cizgisi (poster y)
    s2 = dict(s); s2['tag_y'] = hedef - b_m + h_m / 2
    if int(round(s2['tag_y'] - h_m / 2)) + b_m != hedef:          # yuvarlama: yarim piksel duzelt
        s2['tag_y'] += 0.5
    return s2

def tag_olc(poster, s, zemin_a, S=None, metin=None):
    """Pikselden olculen taban cizgisi: ayni plaka (tagline_plaka) posterin tagline bandinda sablon eslestirmeyle bulunur
    (metin icerigine bagli degil); taban = bulunan y + plakadaki T taban cizgisi. Altin rengi: cekirdek murekkep ortancasi."""
    import cv2, pilot12
    a = np.asarray(poster.convert('RGB')).astype(np.float32); y0, y1 = s['tag_bant'][0] - 80, s['tag_bant'][1] + 80
    d = np.abs(a[y0:y1] - zemin_a[y0:y1]).max(2)
    pl, _ = pilot12.tagline_plaka(s, {'prof': S['prof']}, metin); _, b = tag_plaka_taban(s, S, metin)
    t = np.asarray(pl)[..., 3].astype(np.float32)
    r = cv2.matchTemplate((d / max(d.max(), 1) * 255).astype(np.float32), t, cv2.TM_CCOEFF_NORMED); _, v, _, (lx, ly) = cv2.minMaxLoc(r)
    cek = d > 0.8 * d.max()
    return {'taban_y': int(y0 + ly + b), 'eslesme': round(float(v), 4), 'renk': [round(float(x), 1) for x in np.median(a[y0:y1][cek], 0)]}

def tag_kapisi(olcumler, ref='EJ'):
    r = olcumler[ref]; out = {}
    for k, o in olcumler.items():
        dt = o['taban_y'] - r['taban_y']; dr = max(abs(x - y) for x, y in zip(o['renk'], r['renk']))
        out[k] = {'taban_y': o['taban_y'], 'taban_fark': dt, 'renk': o['renk'], 'renk_fark': round(dr, 1),
                  'gecti': abs(dt) <= TAG_TABAN_ESIK['taban_px'] and dr <= TAG_TABAN_ESIK['renk']}
    return {'gecti': all(v['gecti'] for v in out.values()), 'esik': TAG_TABAN_ESIK, **out}

SEMBOL_ESIK = {'fark': 6.0, 'iou': 0.97}

class Poster:
    def __init__(self, yerel=False):
        import pilot11, pilot12, pilot16
        from kisisel_pilot import FOLDERS, fetch
        self.p11, self.p12, self.p16 = pilot11, pilot12, pilot16
        OUT = pilot16.OUT; self.HAM = pilot16.HAM; self.HAM.mkdir(parents=True, exist_ok=True)
        (OUT / 'hazir').mkdir(parents=True, exist_ok=True)
        olcum_yol = OUT / 'ORANLAR' / 'OLCUM.json'
        if not yerel:
            rc('copy', f'{KP}/HAZIR/bg.png', str(OUT / 'hazir'))
            rc('copy', f'{KP}/ORANLAR/OLCUM.json', str(olcum_yol.parent))
            for f in ('cancer_name_gold.png', 'libra_name_gold.png'):
                fetch(FOLDERS['names'], f, OUT / 'ref' / 'names')
        pilot12.profil_yukle(OUT / 'ref' / 'names')
        self.olcum = json.loads(olcum_yol.read_text())
        self.bg = Image.open(OUT / 'hazir' / 'bg.png')
        self.tavan = None                                       # Cancer-Libra referans boylari (ilk cagri)

    def sayfa_kur(self, sayfa_png, sayfa_no, renk, oran, referans=False):
        """cift_sayfa (Canva sayfa PNG, bayt) + sayfa no, renk, oran -> sayfa baglami (olcum + temiz zemin)."""
        assert renk == 'blue' and oran == ORAN, 'bu adim yalniz Blue 4x5'
        assert referans or self.tavan, 'once Cancer-Libra referansi uretilmeli (boy tavani)'
        t0 = time.time()
        yol = self.HAM / f'{oran}_p{sayfa_no}.jpg'            # render kodu bu adi okur; icerik kayipsiz PNG
        Image.open(io.BytesIO(sayfa_png)).convert('RGB').save(yol, 'PNG')
        m = murekkep(self.p11.norm(Image.open(yol).convert('RGB'))[0])
        o, duz = olcum_duzelt(self.p11.sayfa_olc(yol), m)   # o sayfanin KENDI olcumu + duzeltme
        kayit = dict(self.olcum[oran]); kayit['sayfalar'] = {str(sayfa_no): o}
        self.p16.REF_SAYFA = sayfa_no
        s, S = self.p16.oran_kur(oran, kayit, self.bg, kalibre=True)
        g0, g1 = o['isim_govde']; s['isim_y'] = (g0 + g1) / 2  # dikey merkez: govde (inen kuyruk haric)
        if referans:
            self.tavan = {'cap': dict(s['cap']), 'tag_cap': s['tag_cap'], 'tag_sinir': s['tag_sinir']}
        ilk = {'cap': dict(s['cap']), 'tag_cap': s['tag_cap']}
        s['cap'] = {y: min(s['cap'][y], self.tavan['cap'][y]) for y in ('sol', 'sag')}   # ust sinir: Cancer-Libra; sigmazsa D kurali kucultur
        s['tag_cap'] = min(s['tag_cap'], self.tavan['tag_cap']); s['tag_sinir'] = min(s['tag_sinir'], self.tavan['tag_sinir'])
        return {'sayfa': sayfa_no, 's': s, 'S': S, 'm': m, 'o': o, 'duz': duz, 'ilk': ilk, 'sn': round(time.time() - t0, 1)}

    def uret(self, B, isimler, tagline):
        """sayfa baglami + isimler + tagline -> (poster, bilgi, sembol kirpimlari)."""
        import giris_dogrula as gd
        t0 = time.time(); s, S, o = B['s'], B['S'], B['o']
        r = gd.siparis_dogrula(isimler[0], isimler[1], tagline, None)
        sol, sag = r['sol']['deger'], r['sag']['deger']
        s = taban_hizala(s, S, tagline)                            # taban cizgisi EJ ile ayni (render kodu degismez)
        p, bilgi, merkez, x, yeni = self.p16.poster_kur(s, S, {'sol': sol, 'sag': sag}, tagline)
        kapi = self.p16.blok_kapisi(p, S, s, yeni)
        sk, kirp = sembol_kapisi(p, S, s, merkez, B['m'], SEMBOL_ESIK)
        return p, {'sayfa': B['sayfa'], 'olcum': {k: o.get(k) for k in ('isim_bant', 'isim_govde', 'sembol_bant', 'sembol', 'tag_bant')},
                   'olcum_duzeltme': B['duz'], 'cap_ilk': B['ilk'], 'cap_son': {'cap': s['cap'], 'tag_cap': s['tag_cap']},
                   'bg_hiza': s['bg_hiza'], 'temiz_ara_kapisi': s['temiz_ara_kapisi'], 'kalinti_kapisi': kapi, 'sembol_kapisi': sk,
                   'olcek': bilgi['olcek'], 'punto': bilgi['punto'], 'poster_px': list(p.size), 'tag_olcum': tag_olc(p, s, S['zemin_a'], S, tagline),
                   'sure_sn': round(B['sn'] + time.time() - t0, 1)}, kirp

    def __call__(self, sayfa_png, sayfa_no, renk, oran, isimler, tagline, referans=False):
        """cift_sayfa (Canva sayfa PNG, bayt) + sayfa no, renk, oran, isimler, tagline -> (poster, bilgi, sembol kirpimlari)."""
        return self.uret(self.sayfa_kur(sayfa_png, sayfa_no, renk, oran, referans), isimler, tagline)

# ------------------------------------------------------------------ sahneye oturtma
def yer_olc(sahne, poster, kaba):
    import cv2
    Sg = np.asarray(sahne.convert('L')).astype(np.float32); H, Wd = Sg.shape
    x0, y0, x1, y1 = int(kaba[0] * Wd), int(kaba[1] * H), int(kaba[2] * Wd), int(kaba[3] * H)
    bolge = Sg[y0:y1, x0:x1]; en_iyi = None
    for w in range(int((x1 - x0) * 0.55), int((x1 - x0) * 1.0), 4):       # kaba
        t = np.asarray(poster.convert('L').resize((w, round(w * 1.25)), Image.BOX)).astype(np.float32)
        if t.shape[0] >= bolge.shape[0] or t.shape[1] >= bolge.shape[1]: continue
        r = cv2.matchTemplate(bolge, t, cv2.TM_CCOEFF_NORMED); _, v, _, l = cv2.minMaxLoc(r)
        if en_iyi is None or v > en_iyi[0]: en_iyi = (v, w, l[0] + x0, l[1] + y0)
    v, w0, xa, ya = en_iyi
    for w in np.arange(w0 - 5, w0 + 5.01, 0.5):                           # ince (yarim piksel olcek)
        wi = int(round(w)); hi = int(round(w * 1.25))
        t = np.asarray(poster.convert('L').resize((wi, hi), Image.LANCZOS)).astype(np.float32)
        xs, ys = max(xa - 8, 0), max(ya - 8, 0)
        b = Sg[ys:ys + hi + 16, xs:xs + wi + 16]
        if b.shape[0] <= hi or b.shape[1] <= wi: continue
        r = cv2.matchTemplate(b, t, cv2.TM_CCOEFF_NORMED); _, vv, _, l = cv2.minMaxLoc(r)
        if vv > en_iyi[0]: en_iyi = (vv, wi, l[0] + xs, l[1] + ys)
    v, w, x, y = en_iyi
    return {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(round(w * 1.25)), 'eslesme': round(float(v), 4)}

def aciklik_olc(sahne):
    """Cercevenin ic acikligi: lacivert poster zemininin satir/sutun doluluk >%90 siniri (olculur)."""
    a = np.asarray(sahne.convert('RGB')).astype(np.float32); H, Wd = a.shape[:2]
    d = (a.mean(2) < 70) & (a[..., 2] > a[..., 0])
    xs = np.where(d[int(H * .22):int(H * .74)].mean(0) > .9)[0]; ys = np.where(d[:, int(Wd * .28):int(Wd * .74)].mean(1) > .9)[0]
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

def kapak_yer(sahne, poster, ac):
    """Acikligi tam kaplayan 4:5 poster yeri; isim/tagline disindaki ust bolgede gri fark en kucuk (olculur)."""
    x0, y0, x1, y1 = ac; Rg = np.asarray(sahne.convert('L')).astype(np.float32); g = poster.convert('L'); en = None
    ust = int((y1 - y0) * 0.55)
    for w in range(int((y1 - y0) / 1.25) - 6, int((y1 - y0) / 1.25) + 8):
        h = round(w * 1.25); q = np.asarray(g.resize((w, h), Image.BOX)).astype(np.float32)
        for x in range(x1 - w, x0 + 1):
            for y in range(y1 - h, y0 + 1):
                f = float(np.abs(q[y0 - y:y0 - y + ust, x0 - x:x1 - x] - Rg[y0:y0 + ust, x0:x1]).mean())
                if en is None or f < en[0]: en = (f, x, y, w, h)
    f, x, y, w, h = en
    return {'x': x, 'y': y, 'w': w, 'h': h, 'aciklik': list(ac), 'ust_gri_fark': round(f, 2)}

def yerlestir(sahne, poster, yer):
    a = np.asarray(sahne.convert('RGB')).copy()
    p = np.asarray(poster.convert('RGB').resize((yer['w'], yer['h']), Image.LANCZOS))
    x0, y0, x1, y1 = yer.get('aciklik') or (yer['x'], yer['y'], yer['x'] + yer['w'], yer['y'] + yer['h'])
    x0, y0 = max(x0, yer['x'], 0), max(y0, yer['y'], 0)                                  # aciklik ile poster kesisimi
    x1, y1 = min(x1, yer['x'] + yer['w'], a.shape[1]), min(y1, yer['y'] + yer['h'], a.shape[0])
    a[y0:y1, x0:x1] = p[y0 - yer['y']:y1 - yer['y'], x0 - yer['x']:x1 - yer['x']]   # cerceve korunur
    return Image.fromarray(a)

def kapak_modu():
    """Iterasyon 2: yalniz kapak; posterler A_ORNEK'ten (yeniden render yok)."""
    t0 = time.time(); src = W / 'src'
    rc('copy', f'{DR}/REVIEW/A_ORNEK', str(src), '--include', 'POSTER_*.png')
    rc('copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'ref'), '--include', '*.jpg')
    sahne = Image.open(sorted((W / 'ref').glob('[01]*.jpg'))[0]).convert('RGB')
    P = {c: Image.open(src / f'POSTER_{c}_MB_4x5.png') for c in [REF_CIFT] + [c for c, _ in ORNEK]}
    ac = aciklik_olc(sahne); yer = kapak_yer(sahne, P[REF_CIFT], ac)
    R = {'kapak_yer': yer}
    for c, im in P.items():
        t = time.time(); y = yerlestir(sahne, im, yer)
        d = np.abs(np.asarray(y).astype(np.int16) - np.asarray(sahne).astype(np.int16)).max(2)
        m = np.ones(d.shape, bool); m[ac[1]:ac[3], ac[0]:ac[2]] = False
        ad = f'KAPAK_{c}_yeniden.jpg' if c == REF_CIFT else f'KAPAK_{c}.jpg'
        y.save(CIK / ad, quality=95); R[c] = {'aciklik_disi_maks_fark': int(d[m].max()), 'sn': round(time.time() - t, 2)}
    for c, _ in ORNEK:
        yanyana(Image.open(CIK / f'KAPAK_{REF_CIFT}_yeniden.jpg'), Image.open(CIK / f'KAPAK_{c}.jpg'), f'YANYANA_KAPAK_{c}_vs_CANCER_LIBRA.jpg')
    R['toplam_sn'] = round(time.time() - t0, 1)
    (CIK / 'A1_KAPAK_v2.json').write_text(json.dumps(R, indent=1))
    rc('copy', str(CIK), f'{DR}/REVIEW/A_ORNEK')
    print(json.dumps(R, indent=1), flush=True)

def yanyana(sol, sag, ad):
    H = 1100
    a = sol.resize((round(sol.width * H / sol.height), H), Image.LANCZOS); b = sag.resize((round(sag.width * H / sag.height), H), Image.LANCZOS)
    c = Image.new('RGB', (a.width + b.width + 30, H), 'white'); c.paste(a, (0, 0)); c.paste(b, (a.width + 30, 0))
    c.save(CIK / ad, quality=92)

# ------------------------------------------------------------------ KART09 ust etiketi (Serdar 25 Eyl: "ASTROLOVE / {A} + {B}")
BURCLAR = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
ETIKET_KAYNAK = Path(__file__).resolve().parents[1] / 'etsy' / 'seo' / 'pod_changes_v2.json'   # onayli ilan basliklari (pair)
K9_ETIKET_KUTU = (420, 80, 760, 135)       # canli kart09'da (3000x2250) cift adi bolumu; on ek "ASTROLOVE / " x < 415
K9_ON_EK_X = 415
K9_BANT = (70, 145)                         # etiket satiri (kapi ve serit icin)
K9_ETIKET_X1 = 1300                         # en uzun etiket (CAPRICORN + SAGITTARIUS) bu x'ten once biter

def etiketler():
    """cift klasor adi -> kart etiketi (ilan basligindaki burc sirasi, buyuk harf)."""
    d = json.loads(ETIKET_KAYNAK.read_text(encoding='utf-8'))
    return {'_'.join(sorted(x['pair'].upper().split(' + '))): x['pair'].upper() for x in d}

def k9_hazirla(sahne_k9, eski=REF_CIFT.replace('_', ' + ')):
    """Etiket parametreleri canli karttan olculur (font, agirlik, boy, izleme, renk, taban cizgisi)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'uretim'))
    import textlayer as tl
    tl.FONTS['mont'] = str(K / 'assets' / 'fonts' / 'Montserrat.ttf') if (K / 'assets' / 'fonts' / 'Montserrat.ttf').exists() else tl.FONTS['mont']
    c = np.asarray(sahne_k9.convert('RGB')).astype(np.float64)
    bg = np.median(c[20:60, 100:1500].reshape(-1, 3), 0)
    p = tl.fit(c, K9_ETIKET_KUTU, eski, 'mont', bg, sub=True)
    return {'tl': tl, 'c': c, 'bg': bg, 'p': p, 'base': p['oy'] + p['base0'], 'eski': eski}

def k9_etiket_ciz(X, etiket):
    c = X['c'].copy(); bx0, by0, bx1, by1 = X['p']['box']; W = c.shape[1]
    c[by0 - 6:by1 + 6, bx0 - 6:W - 60] = X['bg']
    return X['tl'].draw_with(c, X['p'], etiket, x=X['p']['ox'], base=X['base'])

def kart09_uret(X, poster, yer, etiket):
    zemin = Image.fromarray(np.clip(k9_etiket_ciz(X, etiket), 0, 255).astype(np.uint8))
    return yerlestir(zemin, poster, yer)

def ocr(im, psm='7'):
    r = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', psm], input=_png(im), capture_output=True)
    return ' '.join(r.stdout.decode('utf-8', 'ignore').split())

def _png(im):
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

def k9_kapisi(kart, X, beklenen, tum, yer):
    """YENI KAPI: (1) OCR etiket satiri == 'ASTROLOVE / beklenen'; (2) sablon: 78 etiket arasinda en iyi eslesme beklenen,
    fark payi yeterli; (3) on ek 'ASTROLOVE /' piksel ayni; (4) kartin geri kalaninda (poster haric) burc adi yok."""
    a = np.asarray(kart.convert('RGB')).astype(np.float64); y0, y1 = K9_BANT; W = a.shape[1]
    bant = Image.fromarray(a[y0:y1, 100:W - 60].astype(np.uint8)).convert('L')
    okunan = ocr(bant.resize((bant.width * 2, bant.height * 2), Image.LANCZOS))
    ocr_ok = okunan.replace(' ', '') == f'ASTROLOVE/{beklenen}'.replace(' ', '')
    skor = {}
    for e in tum:
        r = k9_etiket_ciz(X, e)
        skor[e] = float(np.abs(r[y0:y1, K9_ON_EK_X:K9_ETIKET_X1] - a[y0:y1, K9_ON_EK_X:K9_ETIKET_X1]).mean())
    sira = sorted(skor, key=skor.get); pay = skor[sira[1]] - skor[sira[0]]
    on_ek = float(np.abs(a[y0:y1, 100:K9_ON_EK_X] - X['c'][y0:y1, 100:K9_ON_EK_X]).max())
    g = a.copy(); g[yer['y']:yer['y'] + yer['h'], yer['x']:yer['x'] + yer['w']] = X['bg']; g[y0:y1] = X['bg']
    geri = ocr(Image.fromarray(g.astype(np.uint8)).convert('L'), '3').upper()
    diger = [b for b in BURCLAR if re.search(rf'\b{b}\b', geri)]          # tam kelime ('VARIES' ARIES degil)
    return {'gecti': ocr_ok and sira[0] == beklenen and pay >= 1.0 and on_ek <= 12 and not diger,
            'ocr': okunan, 'ocr_ok': ocr_ok, 'sablon_en_iyi': sira[0], 'sablon_fark': round(skor[sira[0]], 2),
            'sablon_pay': round(pay, 2), 'on_ek_maks_fark': round(on_ek, 1), 'diger_burc_metni': diger}

def k9_kontrol_gorseli(kart, yol):
    a = kart.convert('RGB'); y0, y1 = K9_BANT
    a.crop((100, y0, a.width - 900, y1)).save(yol, quality=92)

# ------------------------------------------------------------------ 77 CIFT (Serdar onayi 25 Eyl: 08ceb2f kurallari)
IN = ('ISABELLA', 'NOAH'); TAG_IN = "I'd Choose You in Every Lifetime"
AM = ('ALEXANDER', 'MIA'); AM_TAG_YOL = f'{KP}/A1_77_AM_TAGLINE.txt'   # video oturumunun raporladigi metin (tek satir)

def am_tagline():
    try:
        rc('copy', AM_TAG_YOL, str(W)); t = (W / 'A1_77_AM_TAGLINE.txt').read_text(encoding='utf-8').strip()
        return t or None
    except Exception:                                           # noqa: BLE001
        return None
A77 = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77'
LISTE77 = f'{KP}/A1_77_LISTE.json'          # {"sayfa": {"1": imzali_url, ...}}; serit isi sonunda siler
NCC_ESIK = 0.95                             # sayfa -> cift dogrulamasi (POD MB 8x10)

def kapilar(b):
    return {'kalinti': b['kalinti_kapisi']['gecti'], 'temiz_zemin': b['temiz_ara_kapisi']['gecti'], 'sembol': b['sembol_kapisi']['gecti']}

def liste_ac(L):
    """Kompakt imzali liste -> {sayfa: tam URL}. {"did","job","s":[[AmzDate, Expires, Signature, HHMMSS(response-expires)], ...]} (sayfa sirasi)
    ya da duz {"sayfa": {n: url}}. Canva'nin verdigi URL bicimi birebir kurulur."""
    if 'sayfa' in L: return L['sayfa']
    out = {}
    for n, (ad, ex, sig, re_) in enumerate(L['s'], 1):
        out[str(n)] = (f"https://export-download.canva.com/{L['did'][-5:]}/{L['did']}/-1/0/{n:04d}-{L['job']}.png"
                       f"?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAQYCGKMUH5AO7UJ26%2F{ad[:8]}%2Fus-east-1%2Fs3%2Faws4_request"
                       f"&X-Amz-Date={ad}&X-Amz-Expires={ex}&X-Amz-Signature={sig}"
                       f"&X-Amz-SignedHeaders=host%3Bx-amz-expected-bucket-owner&response-expires=Fri%2C%2025%20Sep%202026%20{re_[:2]}%3A{re_[2:4]}%3A{re_[4:]}%20GMT")
    return out

def uret77(parca, toplam, mod='tam', filtre=None, ham=()):
    """mod 'tam': EJ + IN (+ AM, metin Drive'da varsa) + kapak + kart09. mod 'am': yalniz AM, onceki kosuda PASS olan ciftler."""
    O = W / 'A1_77'; O.mkdir(exist_ok=True); R = {'parca': parca, 'toplam_is': toplam, 'mod': mod, 'cift': {}}
    tag_am = am_tagline(); R['am_tagline'] = tag_am
    assert mod == 'tam' or tag_am, 'AM tagline metni Drive\'da yok: ' + AM_TAG_YOL
    # ham: imzali liste yerine Drive kopyalari (KP/<klasor>/blue_<n>.png), yalniz filtreli kosu
    if ham:
        assert filtre, 'ham klasoru yalniz filtreli kosuda'
        for h in ham: rc('copy', f'{KP}/{h}', str(W / 'ham77'), '--include', 'blue_*.png')
        L = {p.stem.split('_')[1]: p for p in (W / 'ham77').glob('blue_*.png')}
    else:
        rc('copy', LISTE77, str(W)); L = liste_ac(json.loads((W / 'A1_77_LISTE.json').read_text()))
    ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
    assert len(ciftler) == 78 and (ham or len(L) == 78), (len(ciftler), len(L))
    no = {c: i + 1 for i, c in enumerate(ciftler)}
    benim = [c for c in ciftler if c != REF_CIFT][parca::toplam]
    if filtre: benim = [c for c in ciftler if c in filtre]      # ornek kosu (yalniz belirtilen ciftler)
    if mod in ('am', 'tag'):                                     # yalniz onceki kosuda uretilmis (PASS) ciftler
        uretilmis = set(x.strip('/') for x in rc('lsf', A77, '--dirs-only').split())
        benim = [c for c in benim if c in uretilmis]
    sayfa_b = {}
    for c in [REF_CIFT] + benim:
        u = L[str(no[c])]
        if ham: sayfa_b[c] = u.read_bytes(); continue
        maskele(u)
        try: sayfa_b[c] = indir(u)
        except Exception as e:                                    # noqa: BLE001  cift FAIL olur, is durmaz
            if c == REF_CIFT: raise
            sayfa_b[c] = None; log(f'{c}: sayfa indirilemedi {repr(e)[:120]}')
    log(f'parca {parca}/{toplam}: {len(benim)} cift, sayfalar indi')
    kisisel_hazirla(); P = Poster()
    B = P.sayfa_kur(sayfa_b[REF_CIFT], no[REF_CIFT], 'blue', ORAN, referans=True)
    cl, clb, _ = P.uret(B, ISIM, TAG)
    assert all(kapilar(clb).values()), ('Cancer-Libra referansi kapidan gecmedi', kapilar(clb))
    rc('copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'ref'), '--include', '*.jpg')
    REF = sorted((W / 'ref').glob('[01]*.jpg'))
    sahne = {ad: Image.open(REF[i]).convert('RGB') for ad, (i, _) in SAHNE.items()}
    yer = {'kapak': kapak_yer(sahne['kapak'], cl, aciklik_olc(sahne['kapak'])), 'kart09': yer_olc(sahne['kart09'], cl, SAHNE['kart09'][1])}
    R['yer'] = yer; R['referans_sn'] = round(time.time() - T0, 1); log('referans + yer hazir', yer)
    X9 = k9_hazirla(sahne['kart09']); ET = etiketler()
    g = lambda im: np.asarray(im.convert('L').resize((160, 200), Image.BOX)).astype(np.float64)
    t_bas = time.time()
    for i, c in enumerate(benim):
        ti = time.time(); r = {'sayfa': no[c]}
        try:
            if sayfa_b[c] is None: raise RuntimeError('Canva sayfasi indirilemedi')
            rc('copy', f'{POD}/{c}/{RENK}/8x10.jpg', str(W / 'pod' / c))
            r['sayfa_pod_ncc'] = round(ncc(g(Image.open(io.BytesIO(sayfa_b[c]))), g(Image.open(W / 'pod' / c / '8x10.jpg'))), 4)
            B = P.sayfa_kur(sayfa_b[c], no[c], 'blue', ORAN)
            isler = ([('AM', AM, tag_am)] if mod == 'am' else [('EJ', ISIM, TAG), ('IN', IN, TAG_IN)] + ([('AM', AM, tag_am)] if tag_am else []))
            if mod == 'am': isler = [('EJ', ISIM, TAG)] + isler     # EJ taban cizgisi referansi (kaydedilmez)
            if mod == 'tag': isler = [('EJ', ISIM, TAG), ('IN', IN, TAG_IN), ('AM', AM, tag_am)]
            cikti = {k: P.uret(B, isim, tag) for k, isim, tag in isler}
            r['kapi'] = {k: kapilar(b) for k, (_, b, _) in cikti.items()}; r['kapi']['sayfa_eslesme'] = r['sayfa_pod_ncc'] >= NCC_ESIK
            r['tag_kapisi'] = tag_kapisi({k: b['tag_olcum'] for k, (_, b, _) in cikti.items()})
            r['gecti'] = r['kapi']['sayfa_eslesme'] and all(all(r['kapi'][k].values()) for k in cikti) and r['tag_kapisi']['gecti']
            r['olcum'] = {k: {x: b[x] for x in ('punto', 'olcek', 'olcum_duzeltme', 'sembol_kapisi', 'temiz_ara_kapisi', 'kalinti_kapisi')} for k, (_, b, _) in cikti.items()}
            if r['gecti']:
                d = O / c; d.mkdir(exist_ok=True)
                for k, (p, _, kk) in cikti.items():
                    if mod in ('am', 'tag') and k == 'EJ': continue     # EJ onayli; yalniz referans
                    p.save(d / f'POSTER_{k}.png'); sembol_gorseli(kk, f'../A1_77/{c}/SEMBOL_{k}.jpg')
                if 'EJ' in cikti and mod == 'tam':
                    ej = cikti['EJ'][0]
                    yerlestir(sahne['kapak'], ej, yer['kapak']).save(d / 'KAPAK.jpg', quality=95)
                    kart09_uret(X9, ej, yer['kart09'], ET[c]).save(d / 'KART09.jpg', quality=95)
                    r['kart09_kapisi'] = k9_kapisi(Image.open(d / 'KART09.jpg'), X9, ET[c], list(ET.values()), yer['kart09'])
                    k9_kontrol_gorseli(Image.open(d / 'KART09.jpg'), d / 'ETIKET.jpg')
                (d / f'RAPOR_{mod}.json').write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
                rc('copy', str(d), f'{A77}/{c}')
        except Exception as e:                                    # noqa: BLE001
            r['gecti'] = False; r['hata'] = repr(e)[:400]
        r['sn'] = round(time.time() - ti, 1); R['cift'][c] = r
        n = i + 1; gecen = time.time() - t_bas; kalan = gecen / n * (len(benim) - n)
        log(f'[{n}/{len(benim)}] {c} {"PASS" if r["gecti"] else "FAIL"} {r["sn"]}s | gecen {gecen / 60:.1f} dk, kalan {kalan / 60:.1f} dk, %{100 * n / len(benim):.0f}')
    R['toplam_sn'] = round(time.time() - T0, 1)
    ek = '_ornek' if filtre else ''
    (O / f'parca_{mod}{ek}_{parca}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(O / f'parca_{mod}{ek}_{parca}.json'), f'{A77}/_rapor')

def kart77(parca, toplam):
    """Yalniz KART09 yeniden uretimi (poster/kapak render yok): onayli POSTER_EJ + dogru ust etiket + kart kapisi."""
    O = W / 'A1_77'; O.mkdir(exist_ok=True); R = {'parca': parca, 'toplam_is': toplam, 'mod': 'kart', 'cift': {}}
    kisisel_hazirla()                                           # Montserrat (kisisel-v1 assets) icin
    ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
    uretilmis = set(x.strip('/') for x in rc('lsf', A77, '--dirs-only').split())
    benim = [c for c in [c for c in ciftler if c != REF_CIFT][parca::toplam] if c in uretilmis]
    rc('copy', f'{A77}/_rapor', str(O / '_rapor'), '--include', 'parca_tam_*.json')
    yer = json.loads(sorted((O / '_rapor').glob('parca_tam_*.json'))[0].read_text())['yer']['kart09']
    rc('copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'ref'), '--include', '*.jpg')
    sahne = Image.open(sorted((W / 'ref').glob('[01]*.jpg'))[SAHNE['kart09'][0]]).convert('RGB')
    X9 = k9_hazirla(sahne); ET = etiketler(); tum = list(ET.values())
    R['etiket_olcum'] = {k: X9['p'][k] for k in ('w', 'size', 'track', 'box', 'ink')}
    R['canli_kart_kapisi'] = k9_kapisi(sahne, X9, REF_CIFT.replace('_', ' + '), tum, yer)   # kalibrasyon: canli CL karti PASS olmali
    log('etiket olcumu', R['etiket_olcum'], 'canli CL karti kapisi', R['canli_kart_kapisi'])
    t_bas = time.time()
    for i, c in enumerate(benim):
        ti = time.time(); r = {'etiket': ET[c]}; d = O / c; d.mkdir(exist_ok=True)
        try:
            rc('copy', f'{A77}/{c}', str(d), '--include', 'POSTER_EJ.png', '--include', 'KART09.jpg')
            eski = Image.open(d / 'KART09.jpg'); y0, y1 = K9_BANT
            b = eski.convert('L').crop((100, y0, eski.width - 60, y1)); r['eski_ocr'] = ocr(b.resize((b.width * 2, b.height * 2), Image.LANCZOS))
            r['eski_hatali'] = r['eski_ocr'].replace(' ', '') != f'ASTROLOVE/{ET[c]}'.replace(' ', '')
            kart09_uret(X9, Image.open(d / 'POSTER_EJ.png'), yer, ET[c]).save(d / 'KART09.jpg', quality=95)
            r['kapi'] = k9_kapisi(Image.open(d / 'KART09.jpg'), X9, ET[c], tum, yer); r['gecti'] = r['kapi']['gecti']
            k9_kontrol_gorseli(Image.open(d / 'KART09.jpg'), d / 'ETIKET.jpg')
            (d / 'POSTER_EJ.png').unlink()
            if r['gecti']:
                (d / 'RAPOR_kart.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
                rc('copy', str(d), f'{A77}/{c}')
            else:                                                # hatali kart yuklenmez; eski kart da kaldirilir
                rc('deletefile', f'{A77}/{c}/KART09.jpg')
        except Exception as e:                                    # noqa: BLE001
            r['gecti'] = False; r['hata'] = repr(e)[:400]
        r['sn'] = round(time.time() - ti, 1); R['cift'][c] = r
        n = i + 1; gecen = time.time() - t_bas
        log(f'[{n}/{len(benim)}] {c} {"PASS" if r["gecti"] else "FAIL"} eski: {r.get("eski_ocr")} | gecen {gecen / 60:.1f} dk, kalan {gecen / n * (len(benim) - n) / 60:.1f} dk, %{100 * n / len(benim):.0f}')
    R['toplam_sn'] = round(time.time() - T0, 1)
    (O / f'parca_kart_{parca}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(O / f'parca_kart_{parca}.json'), f'{A77}/_rapor')


def serit77():
    from PIL import ImageDraw
    t0 = time.time(); O = W / 'serit'; O.mkdir(exist_ok=True)
    try:
        rc('copy', f'{A77}/_rapor', str(O / '_rapor'))
        R = {}; parca = []
        RA = {}
        for f in sorted((O / '_rapor').glob('parca_tam_*.json')):
            d = json.loads(f.read_text()); parca.append({'parca': d['parca'], 'toplam_sn': d['toplam_sn'], 'referans_sn': d.get('referans_sn')}); R.update(d['cift'])
        for f in sorted((O / '_rapor').glob('parca_am_*.json')):
            RA.update(json.loads(f.read_text())['cift'])
        RT = {}
        for f in sorted((O / '_rapor').glob('parca_tag_[0-9]*.json')):
            RT.update(json.loads(f.read_text())['cift'])
        RK = {}
        for f in sorted((O / '_rapor').glob('parca_kart_*.json')):
            RK.update(json.loads(f.read_text())['cift'])
        rc('copy', A77, str(O / 'c'), '--include', '*/KAPAK.jpg', '--include', '*/POSTER_IN.png', '--include', '*/POSTER_AM.png', '--include', '*/SEMBOL_EJ.jpg', '--include', '*/ETIKET.jpg', '--transfers', '16')
        ad = sorted(R); gec = [c for c in ad if R[c]['gecti']]; kal = [c for c in ad if not R[c]['gecti']]
        def izgara(dosya, w, h, sut, cikti):
            sat = -(-len(ad) // sut); E = 26; T = Image.new('RGB', (sut * (w + 8) + 8, sat * (h + E + 8) + 8), 'white'); dr = ImageDraw.Draw(T)
            for k, c in enumerate(ad):
                x, y = 8 + (k % sut) * (w + 8), 8 + (k // sut) * (h + E + 8); yol = O / 'c' / c / dosya
                if R[c]['gecti'] and yol.exists():
                    im = Image.open(yol).convert('RGB'); im.thumbnail((w, h), Image.LANCZOS); T.paste(im, (x + (w - im.width) // 2, y))
                else:
                    dr.rectangle([x, y, x + w, y + h], fill=(200, 200, 200)); dr.text((x + 10, y + h // 2), 'FAIL', fill=(180, 0, 0))
                dr.text((x, y + h + 6), f'{R[c]["sayfa"]:02d} {c}', fill=(0, 0, 0))
            T.save(O / cikti, quality=90); return cikti
        cik = [izgara('KAPAK.jpg', 270, 338, 11, 'SERIT_a_KAPAK_77.jpg'), izgara('POSTER_IN.png', 240, 300, 11, 'SERIT_b_POSTER_IN_77.jpg'),
               izgara('SEMBOL_EJ.jpg', 380, 432, 7, 'SERIT_c_SEMBOL_kaynak_vs_yeni_77.jpg')]
        am_var = [c for c in ad if (O / 'c' / c / 'POSTER_AM.png').exists()]
        if am_var: cik.append(izgara('POSTER_AM.png', 240, 300, 11, 'SERIT_d_POSTER_AM_77.jpg'))
        if any((O / 'c' / c / 'ETIKET.jpg').exists() for c in ad): cik.append(izgara('ETIKET.jpg', 1000, 36, 2, 'SERIT_e_KART09_ETIKET_77.jpg'))
        sure = [R[c]['sn'] for c in gec]                         # olculmus sure: uretilen (PASS) ciftler
        for c in RK:
            R.setdefault(c, {})['KART09'] = RK[c]
        for c in RA:                                            # AM ayri kosuda uretildiyse kapisi da cift raporuna girer
            R[c]['AM'] = {k: RA[c].get(k) for k in ('gecti', 'kapi', 'hata', 'sn')}
        am_kal = [c for c in RA if not RA[c]['gecti']]
        kart = {'uretilen': len(RK), 'eski_hatali': sum(1 for c in RK if RK[c].get('eski_hatali')),
                'pass': sum(1 for c in RK if RK[c]['gecti']), 'fail': {c: RK[c].get('hata') or RK[c].get('kapi') for c in RK if not RK[c]['gecti']}}
        tag = {'uretilen': len(RT), 'pass': sum(1 for c in RT if RT[c]['gecti']),
               'fail': {c: RT[c].get('hata') or RT[c].get('tag_kapisi') or RT[c].get('kapi') for c in RT if not RT[c]['gecti']}}
        OZ = {'pass': len(gec), 'fail': len(kal), 'kart09': kart, 'tag_duzeltme': tag, 'am_uretilen': len(am_var), 'am_fail': {c: RA[c].get('hata') or RA[c].get('kapi') for c in am_kal}, 'fail_liste': {c: R[c].get('hata') or R[c].get('kapi') for c in kal},
              'cift_sn_ort': round(float(np.mean(sure)), 1), 'cift_sn_maks': max(sure), 'parca': parca,
              'is_sn_maks': max(p['toplam_sn'] for p in parca), 'serit_sn': round(time.time() - t0, 1), 'seritler': cik}
        (O / 'RAPOR_77.json').write_text(json.dumps({'ozet': OZ, 'cift': R}, ensure_ascii=False, indent=1, default=str))
        for f in cik + ['RAPOR_77.json']: rc('copy', str(O / f), A77)
        print(json.dumps(OZ, ensure_ascii=False, indent=1, default=str), flush=True)
    finally:
        am_bekliyor = am_tagline() and not list((O / '_rapor').glob('parca_am_*.json'))
        if am_bekliyor:
            print('AM tagline var, AM kosusu henuz yok: imzali liste AM kosusu icin korunur', flush=True)
        else:
            try: rc('deletefile', LISTE77)
            except Exception: pass                                # noqa: BLE001

if __name__ == '__main__' and sys.argv[1:2] == ['uret77']:
    m = sys.argv[4] if len(sys.argv) > 4 else 'tam'
    f = set(sys.argv[5].split(',')) if len(sys.argv) > 5 else None
    h = sys.argv[6].split(',') if len(sys.argv) > 6 else ()
    (kart77(int(sys.argv[2]), int(sys.argv[3])) if m == 'kart' else uret77(int(sys.argv[2]), int(sys.argv[3]), m, f, h)); sys.exit(0)

if __name__ == '__main__' and sys.argv[1:2] == ['serit77']:
    serit77(); sys.exit(0)


if __name__ == '__main__' and sys.argv[1:] == ['ham']:
    # yerel teshis icin: Canva sayfalarini ozel Drive klasorune kopyala (liste sonra silinir)
    try:
        rc('copy', f'{KP}/A1_LISTE.json', str(W)); L = json.loads((W / 'A1_LISTE.json').read_text())
        (W / 'ham').mkdir(exist_ok=True)
        for n, u in L['sayfa'].items():
            maskele(u); (W / 'ham' / f'4x5_p{n}.png').write_bytes(indir(u))
        rc('copy', str(W / 'ham'), f'{KP}/A1_HAM'); print(sorted(p.name for p in (W / 'ham').iterdir()))
    finally:
        rc('deletefile', f'{KP}/A1_LISTE.json')
    sys.exit(0)

if __name__ == '__main__' and sys.argv[1:2] == ['ham2']:
    # adli imzali liste {"u": {ad: url}} -> Drive KISISEL_PILOT/<hedef>/<ad>.png (liste sonra silinir)
    liste, hedef = sys.argv[2], sys.argv[3]
    try:
        rc('copy', f'{KP}/{liste}', str(W)); L = json.loads((W / liste).read_text())['u']
        (W / 'ham2').mkdir(exist_ok=True)
        for ad, u in L.items():
            maskele(u); (W / 'ham2' / f'{ad}.png').write_bytes(indir(u))
        rc('copy', str(W / 'ham2'), f'{KP}/{hedef}'); print(sorted(p.name for p in (W / 'ham2').iterdir()), flush=True)
    finally:
        rc('deletefile', f'{KP}/{liste}')
    sys.exit(0)

if __name__ == '__main__' and sys.argv[1:] == ['kapak']:
    kapak_modu(); sys.exit(0)

if __name__ == '__main__':
    R = {'renk': 'Cancer-Libra kapagi Midnight Blue (renk esleme: blue p28 -> MIDNIGHT_BLUE fark 1.35; kaynak Canva Blue 4/5)',
         'isimler': ISIM, 'tagline': TAG}
    try:
        rc('copy', f'{KP}/A1_LISTE.json', str(W)); L = json.loads((W / 'A1_LISTE.json').read_text())
        sayfa_b = {}
        for n, u in L['sayfa'].items():
            maskele(u); sayfa_b[int(n)] = indir(u)
        log('sayfalar indi', {n: len(b) for n, b in sayfa_b.items()})
        kisisel_hazirla(); P = Poster(); log('kisisel-v1 hazir')
        ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
        no = {c: i + 1 for i, c in enumerate(ciftler)}
        rc('copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'ref'), '--include', '*.jpg')
        REF = sorted((W / 'ref').glob('[01]*.jpg'))
        sahne = {ad: Image.open(REF[i]).convert('RGB') for ad, (i, _) in SAHNE.items()}
        R['sahne_boyut'] = {ad: list(im.size) for ad, im in sahne.items()}
        # Cancer-Libra karsiligi: ayni sarmalayici; canli gorsele oturtma olcumu
        t0 = time.time()
        cl, cli, ck = P(sayfa_b[no[REF_CIFT]], no[REF_CIFT], 'blue', ORAN, ISIM, TAG, referans=True)
        sembol_gorseli(ck, f'SEMBOL_{REF_CIFT}_kaynak_vs_yeni.jpg')
        cl.save(CIK / f'POSTER_{REF_CIFT}_MB_4x5.png')
        yer = {}
        for ad, (_, kaba) in SAHNE.items():
            yer[ad] = kapak_yer(sahne[ad], cl, aciklik_olc(sahne[ad])) if ad == 'kapak' else yer_olc(sahne[ad], cl, kaba)
            yeni = yerlestir(sahne[ad], cl, yer[ad])
            a = np.asarray(sahne[ad]).astype(np.int16); b = np.asarray(yeni).astype(np.int16)
            y = yer[ad]; d = np.abs(a - b).max(2)
            yer[ad]['cl_alan_ort_fark'] = round(float(d[y['y']:y['y'] + y['h'], y['x']:y['x'] + y['w']].mean()), 2)
            ax0, ay0, ax1, ay1 = y.get('aciklik') or (y['x'], y['y'], y['x'] + y['w'], y['y'] + y['h'])
            dis = np.ones(d.shape, bool); dis[ay0:ay1, ax0:ax1] = False
            yer[ad]['alan_disi_maks_fark'] = int(d[dis].max())
            yeni.save(CIK / f'{ad.upper()}_{REF_CIFT}_yeniden.jpg', quality=95)
        R[REF_CIFT] = {**cli, 'sayfa_eslesme': None, 'toplam_sn': round(time.time() - t0, 1)}
        R['yer'] = yer; log('Cancer-Libra karsiligi', R[REF_CIFT], yer)
        for cift, ilan in ORNEK:
            t0 = time.time()
            # sayfa -> cift dogrulamasi (POD MB 8x10)
            rc('copy', f'{POD}/{cift}/{RENK}/8x10.jpg', str(W / 'pod' / cift))
            g = lambda im: np.asarray(im.convert('L').resize((160, 200), Image.BOX)).astype(np.float64)
            es = ncc(g(Image.open(io.BytesIO(sayfa_b[no[cift]]))), g(Image.open(W / 'pod' / cift / '8x10.jpg')))
            p, bi, kk = P(sayfa_b[no[cift]], no[cift], 'blue', ORAN, ISIM, TAG)
            sembol_gorseli(kk, f'SEMBOL_{cift}_kaynak_vs_yeni.jpg')
            p.save(CIK / f'POSTER_{cift}_MB_4x5.png')
            for ad in SAHNE:
                yerlestir(sahne[ad], p, yer[ad]).save(CIK / f'{ad.upper()}_{cift}.jpg', quality=95)
                yanyana(sahne[ad], Image.open(CIK / f'{ad.upper()}_{cift}.jpg'), f'YANYANA_{ad.upper()}_{cift}_vs_CANCER_LIBRA.jpg')
            yanyana(cl, p, f'YANYANA_POSTER_{cift}_vs_CANCER_LIBRA.jpg')
            R[cift] = {**bi, 'ilan': ilan, 'sayfa_pod_ncc': round(es, 4), 'toplam_sn': round(time.time() - t0, 1)}
            log(cift, R[cift])
        n_sure = [R[c]['toplam_sn'] for c, _ in ORNEK]
        R['tahmin_77'] = {'ornek_sn': n_sure, 'tek_is_dk': round(77 * np.mean(n_sure) / 60, 1),
                          '8_paralel_is_dk': round(77 * np.mean(n_sure) / 60 / 8, 1),
                          'not': 'kurulum (kisisel-v1 + girdiler) is basina bir kez; kalibrasyon sayfa basina olculdu'}
        R['kurulum_sn'] = round(time.time() - T0 - sum(n_sure) - R[REF_CIFT]['toplam_sn'], 1)
    finally:
        (CIK / 'A1_RAPOR.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
        rc('copy', str(CIK), f'{DR}/REVIEW/A_ORNEK')
        try: rc('deletefile', f'{KP}/A1_LISTE.json')
        except Exception: pass                                    # noqa: BLE001
        print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:8000], flush=True)
