#!/usr/bin/env python3
"""ADIM 1 (3 Eki 2026, Serdar onayi): TAM SIPARIS SETI, motor ile katmanlardan. Bir cift x 5 renk x 5 boy.
Her hucre: motor.py (sabitler motor/sabitler/<CIFT>_<KI>_<boy>.json, satistaki orijinalden olculmus) + qc.py (a-e,
orijinal + Test 5 ayni olcumle). Renk basina 5 sayfalik PDF (Test 5 sirasi: 16x20, 18x24, 24x36, 11x14, A2),
5 sayfayi TAM SAYFA gosteren temas JPG (< 10 MB), OLCUM.md (hucre bazinda tablo), ETA sayaci.

Kullanim: siparis_seti.py --kaynak DIR --isim1 MAXWELL --isim2 QUINN --mesaj "..." --cikti DIR [--is 3]
Kaynak dizini: orijinal/<RENK>_<boy>.jpg, test5/<RENK>_<boy>.jpeg, plates/, main_/sym_/name_ katmanlari
(inceleme/motor-kaynak-siparis paketi).
"""
import argparse, hashlib, json, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent
Image.MAX_IMAGE_PIXELS = None
RENKLER = [('MIDNIGHT_BLUE', 'MB'), ('DEEP_BLACK', 'DB'), ('PURE_WHITE', 'PW'), ('CHAMPAGNE_IVORY', 'CI'),
           ('WARM_PARCHMENT', 'WP')]
BOYLAR = ['16x20', '18x24', '24x36', '11x14', 'A2']                    # Test 5 PDF sayfa sirasi
ORIJINAL_METIN = 'SCORPIO|VIRGO|Two Souls · One Bond'
T0 = time.time()


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def hucre(K, cift, renk, ki, boy, a, C):
    """Bir sayfa: motor + QC. Doner: ozet sozluk."""
    t = time.time()
    S = KOK / 'sabitler' / f'{cift}_{ki}_{boy}.json'
    Z = json.loads(S.read_text())
    O = C / 'hucre' / f'{renk}_{boy}'
    O.mkdir(parents=True, exist_ok=True)
    orj, t5 = K / 'orijinal' / f'{renk}_{boy}.jpg', K / 'test5' / f'{renk}_{boy}.jpeg'
    pl = K / 'plates' / f"{Z['plate']}.png"
    kom = [sys.executable, str(KOK / 'motor.py'), '--kaynak', str(K), '--sabit', str(S), '--isim1', a.isim1,
           '--isim2', a.isim2, '--mesaj', a.mesaj, '--orijinal', str(orj), '--cikti', str(O)]
    if Z.get('mod') == 'altin':
        kom += ['--plate-dosya', str(pl)]
    r1 = subprocess.run(kom, capture_output=True, text=True)
    (O / 'motor.log').write_text(r1.stdout + r1.stderr)
    if r1.returncode:
        return {'renk': renk, 'boy': boy, 'gecti': False, 'hata': 'motor rc %d' % r1.returncode,
                'sure_sn': round(time.time() - t, 1)}
    kom = [sys.executable, str(KOK / 'qc.py'), '--kaynak', str(K), '--sabit', str(S), '--motor', str(O / 'MOTOR.png'),
           '--isim1', a.isim1, '--isim2', a.isim2, '--mesaj', a.mesaj, '--cikti', str(O / 'QC.json'),
           '--orijinal', str(orj), '--orijinal-metin', ORIJINAL_METIN, '--plate-dosya', str(pl), '--test5', str(t5),
           '--e-esik', str(json.loads((KOK / 'sabitler' / 'E_ESIK.json').read_text())[renk]['esik'])]
    r2 = subprocess.run(kom, capture_output=True, text=True)
    (O / 'qc.log').write_text(r2.stdout + r2.stderr)
    q = json.loads((O / 'QC.json').read_text()) if (O / 'QC.json').exists() else {}
    m = q.get('motor', {})
    return {'renk': renk, 'boy': boy, 'gecti': r2.returncode == 0, 'qc_rc': r2.returncode,
            'motor': {k: m.get(k, {}).get('gecti') for k in ('a_tagline', 'b_hat', 'c_kagit', 'd_isim', 'e_bant')},
            'e': m.get('e_bant', {}).get('en_buyuk'), 'e_orijinal': q.get('orijinal', {}).get('e_bant', {}).get('en_buyuk'),
            'e_test5': (q.get('test5') or {}).get('e_bant', {}).get('en_buyuk'),
            'c_dE': m.get('c_kagit', {}).get('dE_ort'), 'd': [m.get('d_isim', {}).get('sol'), m.get('d_isim', {}).get('sag')],
            'a_ocr': m.get('a_tagline', {}).get('ocr'), 'b_cizgi': len(m.get('b_hat', {}).get('orijinalde_olmayan', [])),
            'orijinal_gecti': q.get('orijinal', {}).get('gecti'), 'test5_gecti': (q.get('test5') or {}).get('gecti'),
            'renk_dE': {k: v.get('dE_orijinal') for k, v in m.get('bilgi_renk', {}).items()},
            'bakir_dE_test5': {k: v.get('dE_test5') for k, v in m.get('bilgi_renk', {}).items() if 'dE_test5' in v},
            'sabit': S.name, 'sabit_sha256': sha(S), 'png_sha256': sha(O / 'MOTOR.png'),
            'sure_sn': round(time.time() - t, 1)}


def temas(sayfalar, etiket, cikti):
    """5 sayfa yan yana, TAM SAYFA (kesit yok), ortak yukseklik; JPG < 10 MB."""
    Hh = 3000
    ims = []
    for b, f in sayfalar:
        im = Image.open(f).convert('RGB')
        ims.append((b, im.resize((round(im.width * Hh / im.height), Hh), Image.LANCZOS)))
    ara, ust = 60, 170
    c = Image.new('RGB', (sum(im.width for _, im in ims) + ara * (len(ims) + 1), Hh + ust + ara), 'white')
    d = ImageDraw.Draw(c)
    f = ImageFont.truetype(str(KOK / 'font' / 'EBGaramond-Italic.ttf'), 64)
    d.text((ara, 20), etiket, font=f, fill=(40, 30, 20))
    x = ara
    for b, im in ims:
        d.text((x, 100), b, font=f, fill=(40, 30, 20))
        c.paste(im, (x, ust))
        x += im.width + ara
    sinir = 10 * 1024 * 1024
    olcek = 1.0
    while True:
        im = c if olcek == 1.0 else c.resize((int(c.width * olcek), int(c.height * olcek)), Image.LANCZOS)
        for q in (90, 85, 80, 75, 70):
            im.save(cikti, 'JPEG', quality=q)
            if Path(cikti).stat().st_size < sinir:
                return {'px': list(im.size), 'kalite': q, 'bayt': Path(cikti).stat().st_size}
        olcek *= 0.85


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak')
    ap.add_argument('--cift', default='SCORPIO_VIRGO')
    ap.add_argument('--isim1')
    ap.add_argument('--isim2')
    ap.add_argument('--mesaj')
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--is', type=int, default=3, dest='isler')
    ap.add_argument('--renk', nargs='*')
    ap.add_argument('--boy', nargs='*')
    ap.add_argument('--birlestir', nargs='*', help='SONUC.json dosyalari -> tek OLCUM.md (--cikti dosya)')
    ap.add_argument('--sure', type=float, default=0, help='--birlestir: toplam sure (sn)')
    a = ap.parse_args()
    if a.birlestir:
        sys.exit(0 if birlestir(a.birlestir, a.sure, a.cikti) else 1)
    K, C = Path(a.kaynak).resolve(), Path(a.cikti).resolve()
    C.mkdir(parents=True, exist_ok=True)
    rk = [x for x in RENKLER if not a.renk or x[0] in a.renk]
    by = [b for b in BOYLAR if not a.boy or b in a.boy]
    isler = [(r, ki, b) for r, ki in rk for b in by]
    # buyuk boy once (en uzun is), bellek icin ayni anda en fazla 1 adet 24x36
    isler.sort(key=lambda x: (x[2] != '24x36', x[2] != 'A2'))
    sonuc, n = [], len(isler)
    with ProcessPoolExecutor(a.isler) as ex:
        fs = {ex.submit(hucre, K, a.cift, r, ki, b, a, C): (r, b) for r, ki, b in isler}
        for f in as_completed(fs):
            s = f.result()
            sonuc.append(s)
            g = time.time() - T0
            k = len(sonuc)
            print(f"[ETA] {k}/{n} ({100 * k / n:.0f}%) gecen {g / 60:.1f} dk, kalan ~{g / k * (n - k) / 60:.1f} dk | "
                  f"{s['renk']} {s['boy']} {'PASS' if s['gecti'] else 'FAIL'} e {s.get('e')} ({s['sure_sn']} s)",
                  flush=True)
    sonuc.sort(key=lambda s: ([x[0] for x in RENKLER].index(s['renk']), BOYLAR.index(s['boy'])))
    # renk basina PDF + temas
    import fitz
    ciktilar = {}
    for r, ki in rk:
        sat = [s for s in sonuc if s['renk'] == r]
        ad = 'AstroLoveArt_' + '_'.join(w.capitalize() for w in a.cift.split('_')) + '_' + \
             '_'.join(w.capitalize() for w in r.split('_'))
        d = fitz.open()
        for b in by:
            p = C / 'hucre' / f'{r}_{b}' / 'MOTOR.pdf'
            if p.exists():
                d.insert_pdf(fitz.open(p))
        d.save(C / f'{ad}.pdf')
        tm = temas([(b, C / 'hucre' / f'{r}_{b}' / 'MOTOR.png') for b in by
                    if (C / 'hucre' / f'{r}_{b}' / 'MOTOR.png').exists()],
                   f'{ad}  ({a.isim1} / {a.isim2}, "{a.mesaj}")  5 sayfa, tam sayfa', C / f'TEMAS_{ad}.jpg')
        ciktilar[r] = {'pdf': f'{ad}.pdf', 'pdf_sha256': sha(C / f'{ad}.pdf'), 'sayfa': len(d),
                       'temas': f'TEMAS_{ad}.jpg', 'temas_sha256': sha(C / f'TEMAS_{ad}.jpg'), **tm,
                       'gecti': all(s['gecti'] for s in sat) and len(sat) == len(by)}
    sure = round(time.time() - T0, 1)
    (C / 'SONUC.json').write_text(json.dumps({'cift': a.cift, 'isimler': [a.isim1, a.isim2], 'mesaj': a.mesaj,
                                             'hucreler': sonuc, 'ciktilar': ciktilar, 'sure_sn': sure},
                                            indent=1, ensure_ascii=False))
    md = md_yaz(a.cift, a.isim1, a.isim2, a.mesaj, sonuc, ciktilar, sure)
    (C / 'OLCUM.md').write_text(md)
    print(md)
    sys.exit(0 if all(s['gecti'] for s in sonuc) else 1)


def md_yaz(cift, isim1, isim2, mesaj, sonuc, ciktilar, sure, not_=''):
    ok = lambda v: '-' if v is None else ('PASS' if v else 'FAIL')
    md = [f'# OLCUM: {cift} {isim1} / {isim2}, "{mesaj}"', '',
          f'Toplam sure: {sure / 60:.1f} dk ({len(sonuc)} sayfa). {not_}'
          'Kapilar 3307 px QC olceginde (qc.py QC_W; esikler 11x14 onayli sayfada olculdu).', '',
          '| renk | boy | a tagline | b hat | c kagit dE | d isim OCR | e bant (motor / orijinal / Test 5) | renk dE orijinale '
          '| SONUC | orijinal | Test 5 | sure |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for s in sonuc:
        m = s.get('motor', {})
        md.append(f"| {s['renk']} | {s['boy']} | {ok(m.get('a_tagline'))} | {ok(m.get('b_hat'))} ({s.get('b_cizgi')}) | "
                  f"{ok(m.get('c_kagit'))} ({s.get('c_dE')}) | {ok(m.get('d_isim'))} ({' / '.join(map(str, s.get('d', [])))}) | "
                  f"{ok(m.get('e_bant'))} ({s.get('e')} / {s.get('e_orijinal')} / {s.get('e_test5')}) | "
                  + ', '.join(f'{k} {v}' for k, v in s.get('renk_dE', {}).items()) +
                  f" | {ok(s['gecti'])} | {ok(s.get('orijinal_gecti'))} | {ok(s.get('test5_gecti'))} | {s['sure_sn']} s |")
    md += ['', 'WARM_PARCHMENT bakir farki, motor vs Test 5 bakiri (dE): ' + '; '.join(
        f"{s['boy']}: " + ', '.join(f'{k} {v}' for k, v in s['bakir_dE_test5'].items())
        for s in sonuc if s.get('bakir_dE_test5')), '', '| renk | PDF | sayfa | temas JPG | SONUC |', '|---|---|---|---|---|']
    for r, v in ciktilar.items():
        md.append(f"| {r} | {v['pdf']} | {v['sayfa']} | {v['temas']} ({v['bayt'] / 1e6:.1f} MB) | {ok(v['gecti'])} |")
    return '\n'.join(md) + '\n'


def birlestir(dosyalar, sure, cikti):
    """Renk basina SONUC.json'lari (Actions matrisi) tek OLCUM.md'de birlestirir."""
    R = [json.loads(Path(f).read_text()) for f in dosyalar]
    sira = [x[0] for x in RENKLER]
    sonuc = sorted([s for r in R for s in r['hucreler']], key=lambda s: (sira.index(s['renk']), BOYLAR.index(s['boy'])))
    ciktilar = {k: v for r in R for k, v in r['ciktilar'].items()}
    ciktilar = {k: ciktilar[k] for k in sira if k in ciktilar}
    md = md_yaz(R[0]['cift'], *R[0]['isimler'], R[0]['mesaj'], sonuc, ciktilar, sure,
                not_='Renk basina is suresi: ' + ', '.join(f"{list(r['ciktilar'])[0]} {r['sure_sn'] / 60:.1f} dk" for r in R) + '. ')
    Path(cikti).write_text(md)
    print(md)
    return all(s['gecti'] for s in sonuc) and len(sonuc) == 25


if __name__ == '__main__':
    main()
