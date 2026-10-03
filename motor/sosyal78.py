#!/usr/bin/env python3
"""ADIM 3 (3 Eki 2026, Serdar onayi): SOSYAL MEDYA POSTERLERI, 78 cift. Her cift MIDNIGHT_BLUE 4x5 (16x20,
4800x6000, 300 dpi PNG), isim ve tagline Serdar onayli listeden harfi harfine (TEMP/SOSYAL/INSTAGRAM/
IG_78_ORNEK_ISIM_TAGLINE.csv); sol isim = sol burc. Her cift: olc.py --altin (satistaki orijinal posterden sabitler),
motor.py, qc.py (a-e). FAIL olan cift listelenir, uretilmez sayilir (PNG cikmaz). Cikti: <CIFT>.png, OLCUM_78.md
(hucre bazinda), SONUC_78.json, 78'i tek sayfada gosteren temas JPG (< 10 MB). ETA sayaci.

Kullanim: sosyal78.py --kaynak DIR --cikti DIR [--is 3] [--cift A_B ...]
Kaynak: liste.csv, orijinal/<CIFT>.jpg, plates/BLUE_16x20.png, main_<a>_<b>_gold.png, sym_<burc>_gold.png
"""
import argparse, csv, hashlib, json, shutil, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None
ORIJINAL_TAGLINE = 'Two Souls · One Bond'
T0 = time.time()


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def cift_isle(K, r, C):
    t = time.time()
    c = r['cift']
    O = C / 'hucre' / c
    O.mkdir(parents=True, exist_ok=True)
    S = O / f'SABITLER_{c}_MB_16x20.json'
    orj, pl = K / 'orijinal' / f'{c}.jpg', K / 'plates' / 'BLUE_16x20.png'
    E = json.loads((KOK / 'sabitler' / 'E_ESIK.json').read_text())['MIDNIGHT_BLUE']['esik']
    sonuc = {'cift': c, 'sol': [r['sol_burc'], r['sol_isim']], 'sag': [r['sag_burc'], r['sag_isim']],
             'tagline': r['tagline'], 'gecti': False}

    def kos(ad, kom):
        p = subprocess.run(kom, capture_output=True, text=True)
        (O / f'{ad}.log').write_text(p.stdout + p.stderr)
        return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:] if p.returncode else []

    rc, son = kos('olc', [sys.executable, str(KOK / 'olc.py'), '--kaynak', str(K), '--cift', c, '--renk', 'MIDNIGHT_BLUE',
                         '--boy', '16x20', '--plate', 'BLUE_16x20', '--orijinal', str(orj), '--plate-dosya', str(pl),
                         '--altin', '--govde-profil', '0.15', '--cikti', str(S)])
    if rc:
        return {**sonuc, 'hata': 'olc: ' + ' '.join(son), 'sure_sn': round(time.time() - t, 1)}
    rc, son = kos('motor', [sys.executable, str(KOK / 'motor.py'), '--kaynak', str(K), '--sabit', str(S),
                            '--isim1', r['sol_isim'], '--isim2', r['sag_isim'], '--mesaj', r['tagline'],
                            '--orijinal', str(orj), '--plate-dosya', str(pl), '--cikti', str(O)])
    if rc:
        return {**sonuc, 'hata': 'motor: ' + ' '.join(son), 'sure_sn': round(time.time() - t, 1)}
    om = f"{c.split('_')[0]}|{c.split('_')[1]}|{ORIJINAL_TAGLINE}"
    rc, _ = kos('qc', [sys.executable, str(KOK / 'qc.py'), '--kaynak', str(K), '--sabit', str(S), '--motor',
                       str(O / 'MOTOR.png'), '--isim1', r['sol_isim'], '--isim2', r['sag_isim'], '--mesaj', r['tagline'],
                       '--cikti', str(O / 'QC.json'), '--orijinal', str(orj), '--orijinal-metin', om,
                       '--plate-dosya', str(pl), '--test5', 'yok', '--e-esik', str(E)])
    q = json.loads((O / 'QC.json').read_text()) if (O / 'QC.json').exists() else {}
    m, o = q.get('motor', {}), q.get('orijinal', {})
    sonuc.update({
        'gecti': rc == 0, 'qc_rc': rc,
        'motor': {k: m.get(k, {}).get('gecti') for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'e_bant')},
        'orijinal': {k: o.get(k, {}).get('gecti') for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'e_bant')},
        'a_ocr': m.get('a_tagline', {}).get('ocr'), 'b_cizgi': len(m.get('b_hat', {}).get('orijinalde_olmayan', [])),
        'c_dE': m.get('c_kagit', {}).get('dE_ort'), 'd': [m.get('d_isim', {}).get('sol'), m.get('d_isim', {}).get('sag')],
        'e': m.get('e_bant', {}).get('en_buyuk'), 'e_orijinal': o.get('e_bant', {}).get('en_buyuk'),
        'orijinal_ocr': [o.get('d_isim', {}).get('sol'), o.get('d_isim', {}).get('sag'), o.get('a_tagline', {}).get('ocr')],
        'renk_dE': {k: v.get('dE_orijinal') for k, v in m.get('bilgi_renk', {}).items()},
        'sabit_sha256': sha(S), 'sure_sn': round(time.time() - t, 1)})
    if rc == 0:
        hedef = C / f'{c}.png'
        shutil.copyfile(O / 'MOTOR.png', hedef)
        sonuc['png'] = hedef.name
        sonuc['png_sha256'] = sha(hedef)
    return sonuc


def temas(sonuc, C, cikti):
    """78 posterin tamami tek sayfada (13 x 6), tam poster kucultulmus; FAIL olan hucre etiketli bos kutu."""
    w, h, ara, ust = 360, 450, 16, 60
    sut = 13
    satir = (len(sonuc) + sut - 1) // sut
    f = ImageFont.truetype(str(KOK / 'font' / 'EBGaramond-Italic.ttf'), 22)
    c = Image.new('RGB', (sut * (w + ara) + ara, satir * (h + ust) + ara + 60), 'white')
    d = ImageDraw.Draw(c)
    d.text((ara, 15), 'AstroLoveArt sosyal medya, 78 cift, MIDNIGHT_BLUE 4x5 (motor)', font=f, fill=(30, 30, 30))
    for i, s in enumerate(sonuc):
        x, y = ara + (i % sut) * (w + ara), 60 + (i // sut) * (h + ust)
        d.text((x, y + 4), f"{i + 1}. {s['cift']}", font=f, fill=(30, 30, 30))
        d.text((x, y + 28), f"{s['sol'][1]} / {s['sag'][1]}  {'PASS' if s['gecti'] else 'FAIL'}", font=f,
               fill=(30, 30, 30) if s['gecti'] else (200, 0, 0))
        if s.get('png'):
            c.paste(Image.open(C / s['png']).convert('RGB').resize((w, h), Image.LANCZOS), (x, y + ust - 4))
        else:
            d.rectangle([x, y + ust - 4, x + w, y + ust - 4 + h], outline=(200, 0, 0), width=4)
    for q in (90, 85, 80, 70):
        c.save(cikti, 'JPEG', quality=q)
        if Path(cikti).stat().st_size < 10 * 1024 * 1024:
            return {'px': list(c.size), 'kalite': q, 'bayt': Path(cikti).stat().st_size}
    raise SystemExit('FAIL: temas JPG 10 MB ustu')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--is', type=int, default=3, dest='isler')
    ap.add_argument('--cift', nargs='*')
    ap.add_argument('--parca', type=int, help='Actions matrisi: bu parca (0..N-1), liste sirasi i %% N')
    ap.add_argument('--parca-sayisi', type=int, default=1)
    ap.add_argument('--birlestir', nargs='*', help='parca SONUC json dosyalari -> OLCUM_78.md + TEMAS_78.jpg '
                                                   '(PNG\'ler --cikti dizininde)')
    ap.add_argument('--sure', type=float, help='--birlestir: toplam sure (sn)')
    a = ap.parse_args()
    K, C = Path(a.kaynak).resolve(), Path(a.cikti).resolve()
    C.mkdir(parents=True, exist_ok=True)
    liste = list(csv.DictReader(open(K / 'liste.csv', encoding='utf-8')))
    if a.birlestir:
        sonuc = [s for f in a.birlestir for s in json.loads(Path(f).read_text())['hucreler']]
        sira = [r['cift'] for r in liste]
        sonuc.sort(key=lambda s: sira.index(s['cift']))
        return rapor(sonuc, C, a.sure)
    if a.cift:
        liste = [r for r in liste if r['cift'] in a.cift]
    if a.parca is not None:
        liste = [r for i, r in enumerate(liste) if i % a.parca_sayisi == a.parca]
    sonuc, n = [], len(liste)
    with ProcessPoolExecutor(a.isler) as ex:
        fs = [ex.submit(cift_isle, K, r, C) for r in liste]
        for f in as_completed(fs):
            s = f.result()
            sonuc.append(s)
            g, k = time.time() - T0, len(sonuc)
            print(f"[ETA] {k}/{n} ({100 * k / n:.0f}%) gecen {g / 60:.1f} dk, kalan ~{g / k * (n - k) / 60:.1f} dk | "
                  f"{s['cift']} {'PASS' if s['gecti'] else 'FAIL'} e {s.get('e')} {s.get('hata', '')}", flush=True)
    sira = [r['cift'] for r in liste]
    sonuc.sort(key=lambda s: sira.index(s['cift']))
    if a.parca is not None:
        (C / f'SONUC_parca{a.parca}.json').write_text(json.dumps({'hucreler': sonuc, 'sure_sn': round(time.time() - T0, 1)},
                                                                 indent=1, ensure_ascii=False))
        sys.exit(0)
    rapor(sonuc, C, None)


def rapor(sonuc, C, sure):
    tm = temas(sonuc, C, C / 'TEMAS_78.jpg')
    ok = lambda v: '-' if v is None else ('PASS' if v else 'FAIL')
    gec = [s for s in sonuc if s['gecti']]
    md = ['# OLCUM_78: sosyal medya posterleri, MIDNIGHT_BLUE 4x5 (16x20, 4800x6000, 300 dpi)', '',
          f"Toplam sure: {(sure if sure is not None else time.time() - T0) / 60:.1f} dk. PASS {len(gec)} / {len(sonuc)}. Kapilar 3307 px QC olceginde; "
          f"e esigi MIDNIGHT_BLUE {json.loads((KOK / 'sabitler' / 'E_ESIK.json').read_text())['MIDNIGHT_BLUE']['esik']}.",
          '', 'FAIL (uretilmedi): ' + (', '.join(f"{s['cift']} ({s.get('hata') or ', '.join(k for k, v in s.get('motor', {}).items() if not v) or 'orijinal oz testi: ' + ', '.join(k for k, v in s.get('orijinal', {}).items() if not v)})" for s in sonuc if not s['gecti']) or 'yok'),
          '', '| no | cift | sol / sag | tagline | a | b | c dE | d OCR | e (motor / orijinal) | renk dE orijinale | SONUC | sure |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for i, s in enumerate(sonuc):
        m = s.get('motor', {})
        md.append(f"| {i + 1} | {s['cift']} | {s['sol'][1]} / {s['sag'][1]} | {s['tagline']} | {ok(m.get('a_tagline'))} | "
                  f"{ok(m.get('b_hat'))} ({s.get('b_cizgi')}) | {ok(m.get('c_kagit'))} ({s.get('c_dE')}) | "
                  f"{ok(m.get('d_isim'))} ({' / '.join(map(str, s.get('d', [])))}) | "
                  f"{ok(m.get('e_bant'))} ({s.get('e')} / {s.get('e_orijinal')}) | "
                  + ', '.join(f'{k} {v}' for k, v in s.get('renk_dE', {}).items()) +
                  f" | {ok(s['gecti'])}{' ' + s['hata'] if s.get('hata') else ''} | {s['sure_sn']} s |")
    md += ['', f"Temas: TEMAS_78.jpg ({tm['px'][0]}x{tm['px'][1]}, {tm['bayt'] / 1e6:.1f} MB)"]
    (C / 'OLCUM_78.md').write_text('\n'.join(md) + '\n')
    (C / 'SONUC_78.json').write_text(json.dumps({'hucreler': sonuc, 'temas': tm, 'sure_sn': sure or round(time.time() - T0, 1)},
                                                indent=1, ensure_ascii=False))
    print('\n'.join(md[:6]))
    sys.exit(0)


if __name__ == '__main__':
    main()
