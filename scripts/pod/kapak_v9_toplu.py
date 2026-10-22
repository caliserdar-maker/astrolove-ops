#!/usr/bin/env python3
"""78 cift icin kapak v9 toplu uretim (Serdar 28 Eyl onayi: 3 ornek PASS).
Girdi: _work/baski/<CIFT>/BASKI_11x14.jpg + KAPI_RAPORU.json (TEMP/POD_KAPAK_V3/SIPARIS onbelleginden rclone ile).
Hat kapisi (28 Eyl): KAPI_RAPORU.json yoksa ya da kapilar_gecti degilse o baskidan kapak URETILMEZ (FAIL; AQUARIUS_LIBRA
EJ baskisi sembol kapisi FAIL iken kapaga girmisti).
Sahne: data/pod/kapak_sahne_v9.png 1213x910'a sikistirilir (iki huzme 4:3 pencerede), cerceve ortada.
Her cift: kapak_v8_kur.py cagrisi; PASS/FAIL toplanir; _out/KAPAK_<CIFT>.jpg + OZET.md + ONIZLEME.jpg.
ETA sayaci: islenen/toplam, gecen, kalan, yuzde. Herhangi bir FAIL -> cikis kodu 1.
Kullanim: kapak_v9_toplu.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
BASKI = Path('_work/baski')
OUT = Path('_out'); OUT.mkdir(exist_ok=True)
SAHNE = Path('_work/sahne_1213.png')
Image.open(KOK / 'data/pod/kapak_sahne_v9.png').convert('RGB').resize((1213, 910), Image.LANCZOS).save(SAHNE)

ciftler = sorted(p.name for p in BASKI.iterdir() if (p / 'BASKI_11x14.jpg').is_file())
N = len(ciftler)
print(f'cift sayisi: {N}')
sat = ['# KAPAK V9 TOPLU ' + time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), f'Toplam: {N}', '']
fail = 0
t0 = time.time()
def kapi_gecti(d):
    try:
        return bool(json.loads((d / 'KAPI_RAPORU.json').read_text()).get('kapilar_gecti'))
    except (OSError, ValueError):
        return False


for i, c in enumerate(ciftler, 1):
    if not kapi_gecti(BASKI / c):
        fail += 1
        sat.append(f'- {c}: FAIL | hat kapisi FAIL ya da KAPI_RAPORU yok: kapak uretilmedi')
        print(f'[{i}/{N}] {c} FAIL (hat kapisi) | %{i / N * 100:.0f}', flush=True)
        continue
    r = subprocess.run([sys.executable, str(KOK / 'scripts/pod/kapak_v8_kur.py'), str(SAHNE),
                        str(BASKI / c / 'BASKI_11x14.jpg'), str(KOK / 'data/pod/cila_cerceve_kaynak.png'),
                        str(OUT / f'KAPAK_{c}.jpg'), '295', '30', '919', '880'],
                       capture_output=True, text=True)
    son = (r.stdout.strip().splitlines() or ['?'])[-1]
    olcum = (r.stdout.strip().splitlines() or ['?'])[0]
    sat.append(f'- {c}: {son} | {olcum}')
    if son != 'PASS':
        fail += 1
        print(f'FAIL {c}\n{r.stdout}\n{r.stderr}')
    g = time.time() - t0
    print(f'[{i}/{N}] {c} {son} | gecen {g:.0f}s | kalan ~{g / i * (N - i):.0f}s | %{i / N * 100:.0f}', flush=True)

sat += ['', f'PASS: {N - fail} / {N}', 'SONUC ' + ('PASS' if fail == 0 else 'FAIL')]
Path(OUT / 'OZET.md').write_text('\n'.join(sat) + '\n')

# onizleme: 78 kapak kucuk izgara (13 sutun x 6 satir)
kucuk = [Image.open(OUT / f'KAPAK_{c}.jpg').resize((300, 225)) for c in ciftler if (OUT / f'KAPAK_{c}.jpg').is_file()]
if kucuk:
    su, sa = 13, (len(kucuk) + 12) // 13
    grid = Image.new('RGB', (su * 302, sa * 227), (250, 248, 245))
    for j, im in enumerate(kucuk):
        grid.paste(im, ((j % su) * 302 + 1, (j // su) * 227 + 1))
    grid.save(OUT / 'ONIZLEME.jpg', quality=88)
print('SONUC ' + ('PASS' if fail == 0 else 'FAIL'))
sys.exit(1 if fail else 0)
