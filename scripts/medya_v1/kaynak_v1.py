#!/usr/bin/env python3
"""medya-v1 YENI YONTEM ADIM 1: Canva kaynak aktarimi + dogrulama (Actions, kisisel-pilot kosucusu).
Etsy'ye erisim YOK. Canva'ya erisim YOK: imzali disa aktarma URL'lerini Canva MCP'si olan oturum uretir ve
Drive TEMP/KISISEL_PILOT/KAYNAK_LISTE_v1.json olarak yazar (URL'ler depoya girmez, loga maskelenir).

Adimlar (arguman: hepsi | dogrula | aktar):
 1. Esleme: 25 tasarimin tek-goruntu (as_single_image) kucuk disa aktarimi 78 karoya bolunur.
    a) Blue 4/5 karolari, her ciftin TEMP/POD_PRINT/<CIFT>/MIDNIGHT_BLUE/8x10.jpg baski dosyasina NCC ile
       eslenir -> sayfa -> cift adi (kod ile, ad varsayimi yok).
    b) Diger 24 tasarimin her karosu, Blue 4/5'in 78 karosuna halka-normalize "murekkep" tanimlayicisi ile eslenir
       (renkten bagimsiz: |gri - karo medyani|). Sira ayni ise en iyi eslesme kosegendir.
 2. CI = Modern: 5 edisyonun sayfa 28 karosu, POD_PRINT/CANCER_LIBRA/<5 renk>/8x10.jpg ile renk+yapi farkina gore.
 3. Sayfa 28 farki: yeni disa aktarim (tam boy) ile kilitlerin olculdugu ham sayfa
    (ORANLAR/ham/<oran>_p28.jpg, EDISYONLAR/<ed>/ham/<oran>_p28.jpg): ortalama/p99 fark, degisen alan kutusu.
 4. Boyut testi: test URL'lerinden inen dosyalarin gercek pikseli ve baytlari.
 5. Aktarim: 4/5 x 5 edisyon x 78 sayfa -> KAYNAK/<ed>/4x5/pNN.png, kisisel-v1 dalindaki kaynak_aktar.py ile
    (ham indirilir, degistirilmez).
Cikti: Drive TEMP/KISISEL_PILOT/KAYNAK_RAPOR_v1/{ESLEME.csv, RAPOR.json, RAPOR.md}"""
import csv, io, json, subprocess, sys, time, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
DEST = 'gdrive:ASTROLOVE/TEMP/KISISEL_PILOT'
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
W = Path('_kaynak').resolve(); W.mkdir(exist_ok=True)
RAP = W / 'KAYNAK_RAPOR_v1'; RAP.mkdir(exist_ok=True)
T0 = time.time()
EDIS = ['blue', 'black', 'pure_white', 'modern', 'vintage']
ORAN = ['4x5', '3x4', '2x3', '11x14', 'A']
POD_RENK = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'CHAMPAGNE_IVORY': 'CI', 'PURE_WHITE': 'PW', 'WARM_PARCHMENT': 'WP'}
KARO = (160, 200)          # 4:5 karo olcusu (karsilastirma)

def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)

def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a], capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-500:]}')
    return r.stdout

def maskele(u):
    print(f'::add-mask::{u}', flush=True)
    for p in u.split('&'):
        if p.startswith('X-Amz-Signature='): print(f'::add-mask::{p.split("=", 1)[1]}', flush=True)

def indir(url, deneme=4):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(url, timeout=180) as r: return r.read()
        except Exception as e:                                   # noqa: BLE001
            son = e; time.sleep(2 ** i)
    raise RuntimeError(f'indirilemedi: {son}')

def url_ac(k):
    """Kompakt kayit -> tam imzali URL (Canva'nin verdigi bicim birebir)."""
    if isinstance(k, str): return k
    d = k
    return (f"https://export-download.canva.com/{d['did'][-5:]}/{d['did']}/-1/0/{d['n']:04d}-{d['job']}.{d['ext']}"
            f"?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential={d['cred']}%2F{d['ad'][:8]}%2Fus-east-1%2Fs3%2Faws4_request"
            f"&X-Amz-Date={d['ad']}&X-Amz-Expires={d['ex']}&X-Amz-Signature={d['sig']}"
            f"&X-Amz-SignedHeaders=host%3Bx-amz-expected-bucket-owner&response-expires={d['re']}")

def murekkep(t):
    """Renkten bagimsiz yapi: |gri - medyan| (acik ve koyu zeminde ayni), 0-1."""
    g = np.asarray(t.convert('L')).astype(np.float64)
    m = np.abs(g - np.median(g)); return m / max(m.max(), 1)

def halka_kirp(t):
    """Karoda halka + birlesik sembol bolgesi: murekkep satir/sutun profili ust %65'te; oran bagimsiz normalize."""
    m = murekkep(t); H, Wd = m.shape
    ust = m[:int(H * 0.62)]
    ys, xs = np.where(ust > 0.35)
    if len(ys) < 20: return np.zeros((64, 64))
    k = ust[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.asarray(Image.fromarray((k * 255).astype(np.uint8)).resize((64, 64), Image.BILINEAR)).astype(np.float64)

def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum()); return float((a * b).sum() / d) if d else 0.0

def karolar(png):
    im = Image.open(io.BytesIO(png)).convert('RGB'); w, h = im.size
    n = 78; th = h / n
    if h >= w:   # dikey
        return [im.crop((0, round(i * th), w, round((i + 1) * th))) for i in range(n)], im.size
    tw = w / n
    return [im.crop((round(i * tw), 0, round((i + 1) * tw), h)) for i in range(n)], im.size

def esleme(L, R):
    kar = {}
    for ad, u in L['birlesik'].items():
        maskele(url_ac(u)); b = indir(url_ac(u)); kar[ad], boy = karolar(b)
        log(f'birlesik {ad}: {boy} -> 78 karo, karo {kar[ad][0].size}')
    # a) Blue 4/5 -> cift adi: POD_PRINT MB 8x10
    ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
    ref = {}
    for i, c in enumerate(ciftler, 1):
        p = W / 'pod' / c; p.mkdir(parents=True, exist_ok=True)
        try:
            rc('copy', f'{POD}/{c}/MIDNIGHT_BLUE/8x10.jpg', str(p))
            ref[c] = Image.open(p / '8x10.jpg').convert('RGB').resize(KARO, Image.BOX)
        except Exception as e:                                   # noqa: BLE001
            log(f'POD ref yok {c}: {e}')
        if i % 20 == 0: log(f'POD ref {i}/{len(ciftler)}')
    bl = [t.resize(KARO, Image.BOX) for t in kar['blue_4x5']]
    rg = {c: np.asarray(im.convert('L')).astype(np.float64) for c, im in ref.items()}
    satirlar = []
    for s, t in enumerate(bl, 1):
        g = np.asarray(t.convert('L')).astype(np.float64)
        sk = sorted(((ncc(g, v), c) for c, v in rg.items()), reverse=True)
        satirlar.append({'sayfa': s, 'cift': sk[0][1], 'ncc': round(sk[0][0], 4), 'ikinci': sk[1][1], 'ikinci_ncc': round(sk[1][0], 4)})
    alfabetik = sorted(ciftler)
    R['esleme_blue45'] = {'benzersiz': len({r['cift'] for r in satirlar}) == 78,
                          'alfabetik_sira_ile_ayni': [r['cift'] for r in satirlar] == alfabetik[:78],
                          'min_ncc': min(r['ncc'] for r in satirlar), 'min_fark_ikinciye': round(min(r['ncc'] - r['ikinci_ncc'] for r in satirlar), 4),
                          'sayfa28': satirlar[27]['cift']}
    # b) 24 tasarim -> Blue 4/5 karolari
    ref_d = [halka_kirp(t) for t in kar['blue_4x5']]
    R['sira'] = {}
    for ad, ts in kar.items():
        d = [halka_kirp(t) for t in ts]
        M = np.array([[ncc(a, b) for b in ref_d] for a in d])
        arg = M.argmax(1)
        kose = float(np.mean(arg == np.arange(78)))
        ayrim = float(np.min(np.diag(M) - np.where(np.eye(78, dtype=bool), -9, M).max(1)))
        R['sira'][ad] = {'kosegen_orani': kose, 'kosegen_min_ncc': round(float(np.diag(M).min()), 4),
                         'min_ayrim': round(ayrim, 4), 'uyusmayan_sayfa': [int(i + 1) for i in np.where(arg != np.arange(78))[0]]}
        for r, s in zip(satirlar, range(78)): r[ad] = int(arg[s] + 1)
        log(f'sira {ad}: kosegen {kose:.3f} min_ayrim {ayrim:.3f}')
    with open(RAP / 'ESLEME.csv', 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(satirlar[0].keys())); wr.writeheader(); wr.writerows(satirlar)
    # 2) CI = Modern: sayfa 28 karolari vs CANCER_LIBRA 5 renk 8x10
    renk = {}
    for rk in POD_RENK:
        p = W / 'pod_cl' / rk; p.mkdir(parents=True, exist_ok=True)
        rc('copy', f'{POD}/CANCER_LIBRA/{rk}/8x10.jpg', str(p))
        renk[rk] = np.asarray(Image.open(p / '8x10.jpg').convert('RGB').resize(KARO, Image.BOX)).astype(np.float64)
    R['renk_esleme'] = {}
    for ed in EDIS:
        t = np.asarray(kar[f'{ed}_4x5'][27].resize(KARO, Image.BOX)).astype(np.float64)
        f = {rk: round(float(np.abs(t - v).mean()), 2) for rk, v in renk.items()}
        R['renk_esleme'][ed] = {'fark': f, 'en_yakin': min(f, key=f.get)}
    log('renk esleme', {e: v['en_yakin'] for e, v in R['renk_esleme'].items()})

def boyut_ve_p28(L, R):
    R['boyut_test'] = {}
    for ad, u in L.get('boyut_test', {}).items():
        maskele(url_ac(u)); b = indir(url_ac(u)); im = Image.open(io.BytesIO(b))
        R['boyut_test'][ad] = {'piksel': list(im.size), 'bayt': len(b), 'bicim': im.format}
        log('boyut', ad, im.size, len(b))
        if ad.startswith('blue_4x5_p28_'):
            (W / 'p28').mkdir(exist_ok=True); (W / 'p28' / f'{ad}.png').write_bytes(b)
    # sayfa 28: yeni tam boy disa aktarim vs kilit ham sayfasi
    R['p28_fark'] = {}
    for anah, u in L.get('p28', {}).items():                   # 'blue/3x4' gibi
        ed, oran = anah.split('/')
        maskele(url_ac(u)); yeni = Image.open(io.BytesIO(indir(url_ac(u)))).convert('RGB')
        yol = f'{DEST}/ORANLAR/ham/{oran}_p28.jpg' if ed == 'blue' else f'{DEST}/EDISYONLAR/{ed}/ham/{oran}_p28.jpg'
        h = W / 'ham' / ed; h.mkdir(parents=True, exist_ok=True)
        try: rc('copy', yol, str(h))
        except Exception as e:                                   # noqa: BLE001
            R['p28_fark'][anah] = {'hata': f'ham yok: {yol}'}; continue
        eski = Image.open(h / f'{oran}_p28.jpg').convert('RGB')
        if eski.size != yeni.size:
            R['p28_fark'][anah] = {'hata': f'boyut farkli: yeni {yeni.size}, ham {eski.size}', 'kapi': 'FAIL'}; continue
        a = np.asarray(yeni).astype(np.int16); b = np.asarray(eski).astype(np.int16); d = np.abs(a - b).max(2)
        m = d > 24; ys, xs = np.where(m)
        Hh, Ww = d.shape; bl = d[:Hh // 16 * 16, :Ww // 16 * 16].reshape(Hh // 16, 16, Ww // 16, 16).mean((1, 3))
        kapi = bool(bl.max() <= 2 and d.max() <= 6)
        R['p28_fark'][anah] = {'kapi_blok_ort_maks': round(float(bl.max()), 2), 'kapi_tek_px_maks': int(d.max()),
                               'blok_ort_gt2_sayisi': int((bl > 2).sum()), 'kapi': 'PASS' if kapi else 'FAIL',
                               'ham_bicim': 'jpg', 'boyut_yeni': list(yeni.size), 'ort_fark': round(float(d.mean()), 3), 'p99': float(np.percentile(d, 99)),
                               'maks': int(d.max()), 'degisen_px_24': int(m.sum()),
                               'degisen_kutu': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(ys) else None}
        log('p28', anah, R['p28_fark'][anah])

def aktar(L, R):
    """4/5 x 5 edisyon: kisisel-v1 kaynak_aktar.py (degistirilmeden) ile KAYNAK/<ed>/4x5/pNN.png."""
    liste = {yol: url_ac(k) for yol, k in L['aktar'].items()}
    ad = 'KAYNAK_LISTE_v1_acik.json'
    (W / ad).write_text(json.dumps(liste))
    rc('copy', str(W / ad), DEST)
    raw = 'https://raw.githubusercontent.com/caliserdar-maker/astrolove-ops/kisisel-v1/scripts/kisisel/kaynak_aktar.py'
    (W / 'kaynak_aktar.py').write_bytes(indir(raw))
    r = subprocess.run([sys.executable, '-u', str(W / 'kaynak_aktar.py'), '--liste', ad], cwd=W)
    try: rc('deletefile', f'{DEST}/{ad}')                       # imzali URL listesi Drive'da kalmaz
    except Exception: pass                                       # noqa: BLE001
    R['aktarim_cikis'] = r.returncode
    try:
        rc('copy', f'{DEST}/KAYNAK_DURUM.json', str(W))
        d = json.loads((W / 'KAYNAK_DURUM.json').read_text())
        olc = {tuple(v['olcu']) for k, v in d['bitti'].items() if '/4x5/' in k}
        R['aktarim_tuval_4000x5000'] = olc == {(4000, 5000)}
        R['aktarim'] = {'bitti_4x5': sum(1 for k in d['bitti'] if '/4x5/' in k), 'hata': len(d.get('hata', {})),
                        'olcu_ornek': next(iter(d['bitti'].values()))['olcu'] if d['bitti'] else None}
    except Exception as e:                                       # noqa: BLE001
        R['aktarim'] = {'hata': str(e)}
    log('aktarim', R['aktarim'])

# ---------------- dogrula2 (Serdar 25 Eyl): adil kapi (ayni JPG nicelemesi), fark haritasi, 25/25 esleme --------
RENK_KLASOR = {'blue': 'MIDNIGHT_BLUE', 'black': 'DEEP_BLACK', 'pure_white': 'PURE_WHITE',
               'modern': 'CHAMPAGNE_IVORY', 'vintage': 'WARM_PARCHMENT'}
ORAN_BOY = {'4x5': '8x10.jpg', '3x4': '12x16.jpg', '2x3': '12x18.jpg', '11x14': '11x14.jpg', 'A': 'A4.jpg'}
FARK_GORSEL = ('blue/4x5', 'blue/3x4', 'black/4x5', 'pure_white/4x5')

def jpg_ayni_nicelemle(yeni, ham_yol):
    """Yeni sayfayi kilitli ham JPG'nin KENDI niceleme tablolari ve alt ornekleme ile JPG'ye kaydedip geri okur."""
    from PIL import JpegImagePlugin
    ham = Image.open(ham_yol)
    q = ham.quantization; ss = JpegImagePlugin.get_sampling(ham)
    b = io.BytesIO(); yeni.save(b, 'JPEG', qtables=q, subsampling=ss if ss != -1 else 0)
    return Image.open(io.BytesIO(b.getvalue())).convert('RGB'), {'qtablo_sayisi': len(q), 'alt_ornekleme': ss,
                                                                  'q0_ort': round(float(np.mean(q[0])), 2)}

def kapi(a, b):
    d = np.abs(np.asarray(a).astype(np.int16) - np.asarray(b).astype(np.int16)).max(2)
    Hh, Ww = d.shape; bl = d[:Hh // 16 * 16, :Ww // 16 * 16].reshape(Hh // 16, 16, Ww // 16, 16).mean((1, 3))
    m = d > 24; ys, xs = np.where(m)
    return d, {'blok_ort_maks': round(float(bl.max()), 2), 'tek_px_maks': int(d.max()), 'blok_ort_gt2': int((bl > 2).sum()),
               'ort_fark': round(float(d.mean()), 3), 'p99': float(np.percentile(d, 99)), 'degisen_px_24': int(m.sum()),
               'degisen_kutu': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(ys) else None,
               'kapi': 'PASS' if (bl.max() <= 2 and d.max() <= 6) else 'FAIL'}

def fark_gorseli(eski, yeni, d, ad):
    import cv2
    Wp = 1000; Hp = round(Wp * eski.height / eski.width)
    e = np.asarray(eski.resize((Wp, Hp), Image.LANCZOS)); y = np.asarray(yeni.resize((Wp, Hp), Image.LANCZOS))
    dk = cv2.resize(d.astype(np.float32), (Wp, Hp), interpolation=cv2.INTER_AREA)   # ortalama (alan)
    dm = cv2.resize(d.astype(np.float32), (Wp, Hp), interpolation=cv2.INTER_NEAREST)
    h = np.clip(np.maximum(dk * 8, dm * 2), 0, 255).astype(np.uint8)
    isi = cv2.cvtColor(cv2.applyColorMap(h, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    pano = np.concatenate([e, y, isi], 1).copy()
    for i, t in enumerate(('ESKI (kilitli ham JPG)', 'YENI (ayni niceleme JPG)', 'FARK x8 (ort) / x2 (tepe)')):
        cv2.putText(pano, f'{ad}  {t}', (10 + i * Wp, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
    (RAP / 'FARK').mkdir(exist_ok=True)
    Image.fromarray(pano).save(RAP / 'FARK' / f"FARK_p28_{ad.replace('/', '_')}.jpg", quality=90)

def dogrula2(L, R):
    # 1) tum imzali URL'ler en basta iner (kisa omur)
    ham_b, p28_b = {}, {}
    for ad, u in L['birlesik'].items():
        maskele(url_ac(u)); ham_b[ad] = indir(url_ac(u))
    for ad, u in L['p28'].items():
        maskele(url_ac(u)); p28_b[ad] = indir(url_ac(u))
    log(f'indirildi: {len(ham_b)} birlesik, {len(p28_b)} p28')
    # 2) adil kapi + fark haritasi
    R['p28_adil'] = {}
    for anah, b in p28_b.items():
        ed, oran = anah.split('/')
        yeni = Image.open(io.BytesIO(b)).convert('RGB')
        yol = f'{DEST}/ORANLAR/ham/{oran}_p28.jpg' if ed == 'blue' else f'{DEST}/EDISYONLAR/{ed}/ham/{oran}_p28.jpg'
        h = W / 'ham' / ed; h.mkdir(parents=True, exist_ok=True); rc('copy', yol, str(h))
        hp = h / f'{oran}_p28.jpg'; eski = Image.open(hp).convert('RGB')
        if eski.size != yeni.size:
            R['p28_adil'][anah] = {'hata': f'boyut: yeni {yeni.size} ham {eski.size}', 'kapi': 'FAIL'}; continue
        yj, nic = jpg_ayni_nicelemle(yeni, hp)
        d, k = kapi(yj, eski)
        R['p28_adil'][anah] = {**k, 'niceleme': nic}
        log('p28 adil', anah, k)
        if anah in FARK_GORSEL: fark_gorseli(eski, yj, d, anah)
    # 3) 25/25 esleme: her tasarim kendi renk + oranindaki POD_PRINT baskisiyla
    ciftler = sorted(x.strip('/') for x in rc('lsf', POD, '--dirs-only').split())
    satir = [{'sayfa': s} for s in range(1, 79)]
    R['esleme25'] = {}
    for n, (ad, b) in enumerate(sorted(ham_b.items()), 1):
        ed, oran = ad.rsplit('_', 1) if not ad.endswith('_11x14') else (ad[:-6], '11x14')
        ts, _ = karolar(b); tw, th = ts[0].size
        hedef = W / 'podref'; subprocess.run(['rm', '-rf', str(hedef)])
        rc('copy', POD, str(hedef), '--include', f'*/{RENK_KLASOR[ed]}/{ORAN_BOY[oran]}', '--transfers', '16', timeout=1800)
        ref = {}
        for c in ciftler:
            p = hedef / c / RENK_KLASOR[ed] / ORAN_BOY[oran]
            if p.exists(): ref[c] = np.asarray(Image.open(p).convert('L').resize((tw, th), Image.BOX)).astype(np.float64)
        eslesen = []
        for s, t in enumerate(ts):
            g = np.asarray(t.convert('L')).astype(np.float64)
            sk = sorted(((ncc(g, v), c) for c, v in ref.items()), reverse=True)
            eslesen.append((sk[0][1], sk[0][0], sk[0][0] - sk[1][0]))
            satir[s][ad] = sk[0][1]
        R['esleme25'][ad] = {'ref_sayisi': len(ref), 'alfabetik_ile_ayni': [e[0] for e in eslesen] == ciftler[:78],
                             'benzersiz': len({e[0] for e in eslesen}) == 78, 'min_ncc': round(min(e[1] for e in eslesen), 4),
                             'min_fark_ikinciye': round(min(e[2] for e in eslesen), 4), 'sayfa28': eslesen[27][0],
                             'eksik_ref': [c for c in ciftler if c not in ref]}
        log(f'[{n}/{len(ham_b)}] %{100 * n // len(ham_b)} gecen {time.time() - T0:.0f}s esleme {ad}', R['esleme25'][ad])
    R['esleme25_ozet'] = {'ayni_sira_tasarim': sum(v['alfabetik_ile_ayni'] for v in R['esleme25'].values()), 'toplam': len(R['esleme25'])}
    alan = ['sayfa'] + sorted(ham_b)
    with open(RAP / 'ESLEME.csv', 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=alan); wr.writeheader(); wr.writerows(satir)


if __name__ == '__main__':
    mod = sys.argv[1] if len(sys.argv) > 1 else 'hepsi'
    rc('copy', f'{DEST}/KAYNAK_LISTE_v1.json', str(W))
    L = json.loads((W / 'KAYNAK_LISTE_v1.json').read_text())
    R = {'mod': mod}
    try:
        if mod == 'dogrula2':
            dogrula2(L, R)
        if mod in ('hepsi', 'dogrula'):
            boyut_ve_p28(L, R)
            if L.get('birlesik'): esleme(L, R)
        p28_ok = mod != 'dogrula2' and all(v.get('kapi') == 'PASS' for k, v in R.get('p28_fark', {}).items() if k.endswith('/4x5'))
        R['aktarim_karari'] = 'AKTAR' if p28_ok else 'DUR: sayfa 28 kalinti kapisi tutmadi'
        if mod in ('hepsi', 'aktar') and L.get('aktar') and p28_ok: aktar(L, R)
        if mod == 'dogrula2': R['aktarim_karari'] = 'YOK (Serdar karari: bu adimda aktarim yok)'
    finally:
        (RAP / 'RAPOR.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
        rc('copy', str(RAP), f'{DEST}/KAYNAK_RAPOR_v1')
        try: rc('deletefile', f'{DEST}/KAYNAK_LISTE_v1.json')
        except Exception: pass                                   # noqa: BLE001
        print(json.dumps({k: v for k, v in R.items() if k != 'sira'}, ensure_ascii=False, indent=1)[:6000], flush=True)
        print(json.dumps(R.get('sira', {}), indent=0)[:4000], flush=True)


