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
import io, json, subprocess, sys, time, urllib.request
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
    1) Sembol bandi: isimlere en yakin bandin ustunde, <= SEMBOL_BIRLES px bosluklu ve ayni x araliginda
       2 kume veren bantlar ayni sembolun parcasidir; banda ve x araligina katilir.
    2) Isim govde bandi: inen kuyruklar (Q) haric satirlar; isim_y ve punto tavani icin."""
    import pilot11
    from pilot6 import kumeler
    d = dict(o); ek = []
    sb = list(d['sembol_bant']); sx = [list(x) for x in d['sembol']]
    for b in sorted([b for b in pilot11.bantlar(m) if b[1] <= sb[0]], key=lambda b: -b[1]):
        if sb[0] - b[1] > SEMBOL_BIRLES: break
        k = [c for c in kumeler(m[b[0]:b[1]], 20) if c[1] - c[0] > 30]
        if len(k) == 2 and all(min(k[i][1], sx[i][1]) - max(k[i][0], sx[i][0]) > 0.5 * (k[i][1] - k[i][0]) for i in (0, 1)):
            sb[0] = b[0]; sx = [[min(k[i][0], sx[i][0]), max(k[i][1], sx[i][1])] for i in (0, 1)]; ek.append(list(b))
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

def sembol_kapisi(poster, S, s, merkez, m_src, esik):
    """YENI KAPI: kucuk sembol bolgesi kaynak sayfadakiyle birebir mi? (olcek/aynalama/parca kaymasi yok)
    Bolge olculen banda BAGLI DEGIL: sembol x araligi (+pay) x [sembol bandi ustu - SEMBOL_UST, isim bandi ustu - 5].
    Bolgeye tamamen sigan murekkep bilesenleri (daire yayi gibi disari tasanlar haric) sembolun tamamidir.
    Yeni posterde ayni bilesenler TEK bir yatay kaymayla (|dx| <= 1 yuvarlama, dy = 0) aranir;
    murekkep piksellerinde ortalama mutlak fark <= esik['fark'] ve murekkep IoU >= esik['iou'] olmali."""
    import cv2
    from pilot6 import LUMA, MUREKKEP
    ref = np.asarray(S['ref']).astype(np.float32); P = np.asarray(poster.convert('RGB')).astype(np.float32)
    Pm = (P @ LUMA) > MUREKKEP; sonuc, kirp = {}, {}
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

    def __call__(self, sayfa_png, sayfa_no, renk, oran, isimler, tagline, referans=False):
        """cift_sayfa (Canva sayfa PNG, bayt) + sayfa no, renk, oran, isimler, tagline -> (poster, bilgi, sembol kirpimlari)."""
        import giris_dogrula as gd
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
        r = gd.siparis_dogrula(isimler[0], isimler[1], tagline, None)
        sol, sag = r['sol']['deger'], r['sag']['deger']
        p, bilgi, merkez, x, yeni = self.p16.poster_kur(s, S, {'sol': sol, 'sag': sag}, tagline)
        kapi = self.p16.blok_kapisi(p, S, s, yeni)
        sk, kirp = sembol_kapisi(p, S, s, merkez, m, SEMBOL_ESIK)
        return p, {'sayfa': sayfa_no, 'olcum': {k: o.get(k) for k in ('isim_bant', 'isim_govde', 'sembol_bant', 'sembol', 'tag_bant')},
                   'olcum_duzeltme': duz, 'cap_ilk': ilk, 'cap_son': {'cap': s['cap'], 'tag_cap': s['tag_cap']},
                   'bg_hiza': s['bg_hiza'], 'temiz_ara_kapisi': s['temiz_ara_kapisi'], 'kalinti_kapisi': kapi, 'sembol_kapisi': sk,
                   'olcek': bilgi['olcek'], 'punto': bilgi['punto'], 'poster_px': list(p.size), 'sure_sn': round(time.time() - t0, 1)}, kirp

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
