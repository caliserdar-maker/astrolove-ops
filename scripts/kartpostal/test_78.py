"""kartpostal_uret testi (kisisel-pilot kosucusu, yalniz Drive): 78 cift x EMILY & JAMES + 3 cift uzun isim.
Drive'a YALNIZ: TEMP/KARTPOSTAL_ORNEK/KARTPOSTAL_SERIT_78.jpg (78 kucuk kart) + KARTPOSTAL_FAIL.csv. Etsy/Prodigi erisimi yok."""
import csv, json, subprocess, sys, tempfile, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kartpostal_uret import kartpostal_uret, poster_getir, FONT

POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
HEDEF = 'gdrive:ASTROLOVE/TEMP/KARTPOSTAL_ORNEK'
UZUN = [('ARIES_LEO', 'Maximiliana', 'Christopher'),
        ('CANCER_LIBRA', 'Anastasia-Victoria', 'Maximilian-Alexander'),
        ('SAGITTARIUS_SAGITTARIUS', 'Guinevere Elizabeth', 'Bartholomew Jonathan')]
W = Path(tempfile.mkdtemp(prefix='kp78_')); OUT = Path('out_kp'); OUT.mkdir(exist_ok=True)
ciftler = sorted(x.strip('/') for x in subprocess.run(['rclone', 'lsf', POD, '--dirs-only'], capture_output=True, text=True,
                                                       check=True).stdout.split())
import os
if os.environ.get('KP_YEREL_TEST'): ciftler = ciftler[:6]                   # yerel duman testi (sahte rclone)
else: assert len(ciftler) == 78 and 'CANCER_LIBRA' in ciftler, len(ciftler)
isler = [(c, 'Emily', 'James', 'EJ') for c in ciftler] + [(c, a, b, 'UZUN') for c, a, b in UZUN]
onb, satir, kucuk = {}, [], {}
t0 = time.time()
for i, (c, a, b, tur) in enumerate(isler, 1):
    try:
        poster = onb.get(('p', c)) or poster_getir(c, W)[0]; onb[('p', c)] = poster
        yol, q = kartpostal_uret(c, a, b, W / f'{c}_{tur}.jpg', poster=poster, kati=False, _sembol_onbellek=onb)
        fail = [k for k, v in q['kapilar'].items() if not v]
        satir.append({'cift': c, 'tur': tur, 'metin': q['yerlesim']['metin'], 'PASS': q['PASS'], 'fail_kapilar': ';'.join(fail),
                      'isim_cap_px': q['yerlesim']['isim_cap_px'], 'isim_en_px': q['yerlesim']['isim_en_px'],
                      'sembol_kutu': q['yerlesim']['sembol_kutu'], 'poster': q['poster'], 'hata': ''})
        if tur == 'EJ': kucuk[c] = (Image.open(yol).convert('RGB').resize((186, 262), Image.LANCZOS), q['PASS'])
    except Exception as e:                                         # noqa: BLE001  cift FAIL olur, is durmaz
        satir.append({'cift': c, 'tur': tur, 'metin': '', 'PASS': False, 'fail_kapilar': 'istisna', 'isim_cap_px': '',
                      'isim_en_px': '', 'sembol_kutu': '', 'poster': '', 'hata': repr(e)[:200]})
    g = time.time() - t0; kal = g / i * (len(isler) - i)
    r = satir[-1]
    print(f'[{i}/{len(isler)}] %{100 * i / len(isler):.0f} gecen {g:.0f}s kalan ~{kal:.0f}s | {c} {tur} '
          f'{"PASS" if r["PASS"] else "FAIL " + r["fail_kapilar"] + " " + r["hata"]} cap={r["isim_cap_px"]} en={r["isim_en_px"]}', flush=True)

# serit: 78 kucuk kart, 13 x 6, FAIL kirmizi cerceve
tw, th, et, g = 186, 262, 26, 10; kol = 13; sat = (len(ciftler) + kol - 1) // kol
S = Image.new('RGB', (kol * (tw + g) + g, sat * (th + et + g) + g + 50), (236, 233, 226)); dr = ImageDraw.Draw(S)
f = ImageFont.truetype(str(FONT), 13); fb = ImageFont.truetype(str(FONT), 24)
npass = sum(1 for r in satir if r['tur'] == 'EJ' and r['PASS']); upass = sum(1 for r in satir if r['tur'] == 'UZUN' and r['PASS'])
dr.text((g, 12), f'KARTPOSTAL 78 CIFT  EMILY & JAMES  PASS {npass}/78   UZUN ISIM PASS {upass}/3', font=fb, fill=(30, 30, 30))
for i, c in enumerate(ciftler):
    x, y = g + (i % kol) * (tw + g), 50 + g + (i // kol) * (th + et + g)
    if c in kucuk:
        im, ok = kucuk[c]; S.paste(im, (x, y))
        if not ok: dr.rectangle((x - 3, y - 3, x + tw + 2, y + th + 2), outline=(200, 0, 0), width=4)
    else:
        dr.rectangle((x, y, x + tw, y + th), outline=(200, 0, 0), width=4); dr.text((x + 10, y + th / 2), 'URETILEMEDI', font=f, fill=(200, 0, 0))
    dr.text((x + tw / 2, y + th + 4), c, font=f, fill=(40, 40, 40), anchor='ma')
S.save(OUT / 'KARTPOSTAL_SERIT_78.jpg', quality=90)
alan = list(satir[0].keys())
with open(OUT / 'KARTPOSTAL_FAIL.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=alan); w.writeheader()
    fails = [r for r in satir if not r['PASS']]
    for r in fails: w.writerow(r)
    if not fails:
        w.writerow({k: '' for k in alan} | {'cift': f'FAIL YOK: EMILY & JAMES {npass}/78 PASS, uzun isim {upass}/3 PASS'})
for r in satir:
    if r['tur'] == 'UZUN': print('UZUN', json.dumps(r, ensure_ascii=False))
caps = [r['isim_cap_px'] for r in satir if r['tur'] == 'EJ' and r['PASS']]
print(json.dumps({'EJ_PASS': npass, 'UZUN_PASS': upass, 'FAIL': len([r for r in satir if not r['PASS']]),
                  'sure_s': round(time.time() - t0)}), flush=True)
subprocess.run(['rclone', 'copy', str(OUT), HEDEF], check=True)
subprocess.run(['rclone', 'lsl', HEDEF, '--include', 'KARTPOSTAL_SERIT_78.jpg', '--include', 'KARTPOSTAL_FAIL.csv'], check=True)
