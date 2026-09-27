#!/usr/bin/env python3
"""POD kapak v3 (Serdar onayi 27 Eyl 2026, ADIM 2, yontem 2). Etsy'ye erisim YOK; yalniz Drive (rclone).

Sablon = onayli CL kapagi (data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg). Duvar ve cerceve
sabittir; yalniz cerceve acikligi (ACIKLIK, onayli dosyadan olculdu) degisir.
Poster = siparis_dosyasi.py'nin (siparis-baski-v1 dali, degistirilmeden) 11x14 Midnight Blue ciktisi,
EMILY / JAMES / "It Began With a Kiss in the Rain". Sembol ve yazi yeniden cizilmez.

Yontem 2 (Serdar, 27 Eyl): onayli kapaktaki poster = hattin 11x14 EJ dosyasi, yatayda %1.7 sikistirilmis
(1560x1981 -> 1534x1988). Yeni kapakta sikistirma YOK: dosya oran korunarak aciklik yuksekligine
(1988) olceklenir (~1565 genis), ortalanir, sag/soldan esit kirpilir (1534). Renk/filtre degisikligi yok.
Kapilar (PASS/FAIL):
  - serit: kirpilan sag/sol seritte altin bilesen yok (yalniz zemin; yildiz noktasi < SERIT_AZAMI px)
  - ncc: NCC(aciklik, olceklenmis gercek dosya) >= 0.99 (kaydedilen JPEG geri okunarak)
  - boyut 3000x2250, aciklik disi sablonla birebir
Onayli kapakla NCC yalniz bilgi olarak raporlanir (esik degil).
--mod ornek: CANCER_LIBRA + ARIES_LEO, CAPRICORN_SAGITTARIUS, LEO_LEO -> TEMP/POD_KAPAK_V3/ORNEK/
             + yan yana (onayli | yeni CL) + onizleme.
--mod 77:    kalan 77 cift -> TEMP/POD_KAPAK_V3/77/ (Serdar 4 ornegi onayladi, 27 Eyl). --parca i --toplam n ile
             n paralel isin i'ncisi (cift listesi [i::n]); her parca OLCUM_p<i>.json yazar.
--mod onizleme77: Drive 77/'yi okur; 77 dosya 3000x2250 + tum parcalar PASS kapisi, ONIZLEME.jpg + OZET_77.json.
Hat ciktisi Drive'da (TEMP/POD_KAPAK_V3/SIPARIS/<cift>_MIDNIGHT_BLUE_11x14/) varsa yeniden uretilmez.
"""
import argparse, base64, csv, json, subprocess, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KOK = Path(__file__).resolve().parents[2]
SABLON = KOK / 'data/pod/cl_referans/CL_kapak_onayli_3000x2250.jpg'
LISTE = KOK / 'data/pod/pod78_ids.csv'
HEDEF = 'gdrive:ASTROLOVE/TEMP/POD_KAPAK_V3'
SIP_HEDEF = f'{HEDEF}/SIPARIS'            # siparis_dosyasi ciktisi buraya (TEMP/SIPARIS_ISIM'e dokunulmaz)
RENK = 'MIDNIGHT_BLUE'; BOY = '11x14'
ISIM = ('EMILY', 'JAMES'); MESAJ = 'It Began With a Kiss in the Rain'
REF = 'CANCER_LIBRA'
ORNEK = ('ARIES_LEO', 'CAPRICORN_SAGITTARIUS', 'LEO_LEO')
NCC_ESIK = 0.99
SERIT_AZAMI = 20      # kirpilan seritte izin verilen en buyuk altin bilesen (px); yildiz noktasi alti
# Onayli kapakta poster acikligi (olculdu 27 Eyl: lacivert doluluk > %90 satir/sutun, egim yok).
# Koseler: SolUst (734,130)  SagUst (2267,130)  SagAlt (2267,2117)  SolAlt (734,2117). Yari acik kutu:
ACIKLIK = (734, 130, 2268, 2118)
AW, AH = ACIKLIK[2] - ACIKLIK[0], ACIKLIK[3] - ACIKLIK[1]      # 1534 x 1988

W = Path('_kapak').resolve(); W.mkdir(exist_ok=True)


def log(*a): print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def rc(*a, timeout=1800, kontrol=True):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode and kontrol:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-400:]}')
    return r


def gri(a): return a.astype(np.float32).mean(2)


def ncc(a, b):
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def eta(i, n, ad):
    g = time.time() - T0; k = g / i * (n - i) if i else 0
    log(f'ETA {i}/{n} ({100 * i / n:.0f}%) gecen {g / 60:.1f} dk kalan {k / 60:.1f} dk | {ad}')


# ------------------------------------------------------------------ hat
def hat(sb, cift):
    """siparis_dosyasi.py (degistirilmeden) 11x14 EJ -> BASKI_11x14.jpg. Drive'da varsa indirilir."""
    rec = f'{cift}_{RENK}_{BOY}'; yol = W / 'baski' / rec / f'BASKI_{BOY}.jpg'
    if rc('copyto', f'{SIP_HEDEF}/{rec}/BASKI_{BOY}.jpg', str(yol), kontrol=False).returncode == 0 and yol.exists():
        log(cift, 'hat ciktisi Drive\'da var, yeniden uretilmedi')
        return yol, 'drive'
    args = ['--cift', cift, '--renk', RENK, '--boy', BOY, '--isim1', ISIM[0], '--isim2', ISIM[1],
            '--mesaj-b64', base64.b64encode(MESAJ.encode()).decode()]
    kod = ("import sys; sys.path.insert(0, 'scripts/medya_v1'); import siparis_dosyasi as s; "
           f"s.SIP = {SIP_HEDEF!r}; sys.argv = ['siparis_dosyasi.py'] + {args!r}; s.main()")
    subprocess.run([sys.executable, '-c', kod], cwd=sb, check=True)
    yol = Path(sb) / '_siparis' / rec / f'BASKI_{BOY}.jpg'
    if not yol.exists():
        raise SystemExit(f'HATA: hat ciktisi yok: {yol}. DUR.')
    return yol, 'hat'


# ------------------------------------------------------------------ yerlestirme + kapilar
def poster_hazirla(baski_yol):
    """Oran korunarak aciklik yuksekligine olcekle, ortala, sag/soldan esit kirp."""
    with Image.open(baski_yol) as im:
        src = list(im.size)
        w = round(AH * im.size[0] / im.size[1])
        p = np.asarray(im.convert('RGB').resize((w, AH), Image.LANCZOS))
    if w < AW:
        raise SystemExit(f'HATA: olcekli poster {w} < aciklik {AW}. DUR.')
    sol = (w - AW) // 2
    parca = p[:, sol:sol + AW]
    seritler = [p[:, :sol], p[:, sol + AW:]]
    return parca, seritler, {'kaynak_px': src, 'olcekli_px': [w, AH], 'kirp_sol': sol, 'kirp_sag': w - AW - sol}


def serit_kapisi(seritler):
    en_buyuk, toplam = 0, 0
    for s in seritler:
        if s.size == 0:
            continue
        a = s.astype(np.int16)
        m = ((a[..., 0] > 120) & (a[..., 0] > a[..., 2] + 40)).astype(np.uint8)
        toplam += int(m.sum())
        n, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n > 1:
            en_buyuk = max(en_buyuk, int(st[1:, cv2.CC_STAT_AREA].max()))
    return {'altin_px': toplam, 'en_buyuk_bilesen': en_buyuk, 'gecti': en_buyuk < SERIT_AZAMI}


def kapak_uret(S, baski_yol, cikti):
    X0, Y0, X1, Y1 = ACIKLIK
    parca, seritler, geo = poster_hazirla(baski_yol)
    a = S.copy(); a[Y0:Y1, X0:X1] = parca                     # cerceve ve duvar sablondan aynen
    Image.fromarray(a).save(cikti, 'JPEG', quality=95, subsampling=0, optimize=True)
    with Image.open(cikti) as im:
        K = np.asarray(im.convert('RGB')); boyut = list(im.size)
    n = ncc(gri(K)[Y0:Y1, X0:X1], gri(parca))
    dis = a.copy(); dis[Y0:Y1, X0:X1] = S[Y0:Y1, X0:X1]
    r = {**geo, 'boyut': boyut, 'serit': serit_kapisi(seritler),
         'ncc_dosya': round(n, 5), 'ncc_onayli_bilgi': round(ncc(gri(S)[Y0:Y1, X0:X1], gri(K)[Y0:Y1, X0:X1]), 5),
         'aciklik_disi_ayni': bool((dis == S).all())}
    r['gecti'] = bool(r['serit']['gecti'] and n >= NCC_ESIK and boyut == [3000, 2250] and r['aciklik_disi_ayni'])
    return r


def yan_yana(sol_yol, sag_yol, yol):
    t = Image.new('RGB', (3000, 1125), 'white')
    for i, p in enumerate((sol_yol, sag_yol)):
        with Image.open(p) as im:
            t.paste(im.convert('RGB').resize((1500, 1125), Image.LANCZOS), (i * 1500, 0))
    t.save(yol, quality=92)


def onizleme(yollar, yol, sut=4, w=600):
    h = w * 3 // 4; n = len(yollar); sat = -(-n // sut)
    t = Image.new('RGB', (sut * w, sat * h), 'white')
    for i, p in enumerate(yollar):
        with Image.open(p) as im:
            t.paste(im.resize((w, h), Image.BOX), ((i % sut) * w, (i // sut) * h))
    t.save(yol, quality=88)


def onizleme77():
    cik = W / '77'; cik.mkdir(exist_ok=True)
    rc('copy', f'{HEDEF}/77', str(cik), '--include', '*.jpg', '--include', 'OLCUM_p*.json', '--transfers', '16')
    with open(LISTE, newline='') as f:
        ciftler = [r['cift'] for r in csv.DictReader(f) if r['cift'] != REF]
    parcalar = [json.loads(p.read_text()) for p in sorted(cik.glob('OLCUM_p*.json'))]
    kayit = {x['cift']: x for P in parcalar for x in P.get('ciftler', [])}
    eksik = [c for c in ciftler if not (cik / f'{c}.jpg').exists()]
    boyut = [c for c in ciftler if c not in eksik and list(Image.open(cik / f'{c}.jpg').size) != [3000, 2250]]
    kapi = [c for c in ciftler if not kayit.get(c, {}).get('gecti')]
    Z = {'toplam': len(ciftler), 'dosya': len(ciftler) - len(eksik), 'eksik': eksik, 'boyut_hata': boyut,
         'kapi_fail': kapi, 'parca': len(parcalar),
         'ncc_dosya_min': min((kayit[c]['ncc_dosya'] for c in kayit if 'ncc_dosya' in kayit[c]), default=None),
         'serit_en_buyuk': max((kayit[c]['serit']['en_buyuk_bilesen'] for c in kayit if 'serit' in kayit[c]), default=None)}
    Z['gecti'] = not (eksik or boyut or kapi)
    var = [cik / f'{c}.jpg' for c in ciftler if c not in eksik]
    if var:
        onizleme(var, cik / 'ONIZLEME.jpg', sut=11, w=300)
    (cik / 'OZET_77.json').write_text(json.dumps(Z, ensure_ascii=False, indent=1))
    for f in ('ONIZLEME.jpg', 'OZET_77.json'):
        if (cik / f).exists(): rc('copyto', str(cik / f), f'{HEDEF}/77/{f}')
    log('OZET_77', {k: (v if not isinstance(v, list) else len(v)) for k, v in Z.items()})
    if not Z['gecti']:
        raise SystemExit(f'FAIL: eksik {eksik[:5]} boyut {boyut[:5]} kapi {kapi[:5]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mod', default='ornek', choices=('ornek', '77', 'onizleme77'))
    ap.add_argument('--sb', default='', help='siparis-baski-v1 checkout dizini (ornek/77)')
    ap.add_argument('--parca', type=int, default=0); ap.add_argument('--toplam', type=int, default=1)
    ap.add_argument('--ciftler', default='', help='77: yalniz bu ciftler (virgullu; ek kosu), OLCUM_p<parca>_ek.json')
    a = ap.parse_args()
    if a.mod == 'onizleme77':
        return onizleme77()
    if not a.sb:
        raise SystemExit('HATA: --sb gerekir')
    S = np.asarray(Image.open(SABLON).convert('RGB'))
    assert S.shape[:2] == (2250, 3000), S.shape
    X0, Y0, X1, Y1 = ACIKLIK
    cik = W / ('ORNEK' if a.mod == 'ornek' else '77'); cik.mkdir(exist_ok=True)
    R = {'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'mod': a.mod, 'yontem': 2,
         'boy': BOY, 'aciklik': ACIKLIK,
         'koseler': {'sol_ust': [X0, Y0], 'sag_ust': [X1 - 1, Y0], 'sag_alt': [X1 - 1, Y1 - 1],
                     'sol_alt': [X0, Y1 - 1]}, 'isim': ISIM, 'mesaj': MESAJ,
         'esik': {'ncc_dosya': NCC_ESIK, 'serit_azami_bilesen_px': SERIT_AZAMI}}
    if a.mod == 'ornek':
        ciftler = [REF, *ORNEK]
    else:
        with open(LISTE, newline='') as f:
            ciftler = [r['cift'] for r in csv.DictReader(f) if r['cift'] != REF]
        assert len(ciftler) == 77, len(ciftler)
        if a.ciftler.strip():
            secili = [x.strip() for x in a.ciftler.split(',') if x.strip()]
            if set(secili) - set(ciftler):
                raise SystemExit(f'HATA: 77 listesinde yok: {sorted(set(secili) - set(ciftler))}. DUR.')
            ciftler = secili
        else:
            ciftler = ciftler[a.parca::a.toplam]
        log(f'parca {a.parca}/{a.toplam}: {len(ciftler)} cift {"(ek kosu)" if a.ciftler.strip() else ""}')
    olcum = cik / ('OLCUM.json' if a.mod == 'ornek' else
                   f'OLCUM_p{a.parca}{"_ek" if a.ciftler.strip() else ""}.json')

    R['ciftler'] = []; yollar = []
    for i, c in enumerate(ciftler):
        eta(i, len(ciftler), c)
        try:
            baski, kaynak = hat(a.sb, c)
            yol = cik / f'{c}.jpg'
            r = {'cift': c, 'hat': kaynak, **kapak_uret(S, baski, yol)}
        except BaseException as e:                               # noqa: BLE001
            r = {'cift': c, 'gecti': False, 'hata': f'{type(e).__name__}: {e}'[:300]}
        R['ciftler'].append(r); log(c, r)
        olcum.write_text(json.dumps(R, ensure_ascii=False, indent=1))
        if not r['gecti']:
            log(f'FAIL {c}: DUR (ilk hatada dur)')
            break
        yollar.append(yol)
    eta(len(R['ciftler']), len(ciftler), 'bitti')
    if a.mod == 'ornek' and (cik / f'{REF}.jpg').exists():
        yan_yana(SABLON, cik / f'{REF}.jpg', cik / 'YAN_YANA_onayli_vs_yeni_CL.jpg')
    if yollar and a.mod == 'ornek':
        onizleme(yollar, cik / 'ONIZLEME.jpg')
    rc('copy', str(cik), f'{HEDEF}/{cik.name}', '--exclude', '*.png')
    kotu = [x['cift'] for x in R['ciftler'] if not x['gecti']]
    eksik = len(ciftler) - len(R['ciftler'])
    log('Cikti', f'TEMP/POD_KAPAK_V3/{cik.name}/', f'PASS {len(yollar)}/{len(ciftler)}',
        '| FAIL', kotu, '| islenmedi', eksik)
    if kotu or eksik:
        raise SystemExit(f'FAIL: {kotu}, islenmedi {eksik}')


if __name__ == '__main__':
    main()
