#!/usr/bin/env python3
"""78 kupa videosu (video_el43.py) paralel uretim. Girdi: kapak klasoru (KUPA_KAPAK_<CIFT>.jpg). Cikti: KUPA_VIDEO_<CIFT>.mp4.
Her video once gecici adla yazilir, bitince yerine konur. Hata olursa o cift raporlanir, digerleri devam eder.
Var olan video atlanir (kesintiden devam). Kapak ya da kod degistiyse YENIDEN=1 ile tum set silinip yeniden uretilir.
Kullanim: python3 -I video78.py <kapak_klasoru> <cikti_klasoru> [isci]"""
import os, pathlib, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BURASI = pathlib.Path(__file__).resolve().parent
KAP, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
ISCI = int(sys.argv[3]) if len(sys.argv) > 3 else 2
OUT.mkdir(parents=True, exist_ok=True)
ciftler = sorted(p.stem.replace('KUPA_KAPAK_', '') for p in KAP.glob('KUPA_KAPAK_*.jpg'))
if len(ciftler) != 78:
    sys.exit(f'HATA: 78 kapak bekleniyordu, {len(ciftler)} bulundu')
if os.environ.get('YENIDEN') == '1':          # tum seti bastan uret (kapak ya da kod degistiyse zorunlu)
    for f in list(OUT.glob('KUPA_VIDEO_*')) + list(OUT.glob('.gecici_*')):
        f.unlink()
yap = [c for c in ciftler if not (OUT / f'KUPA_VIDEO_{c}.mp4').exists()]
ENV = dict(os.environ, KAYIT=str(KAP / 'KAYIT.tsv'))
if not (KAP / 'KAYIT.tsv').exists():
    sys.exit('HATA: kapak klasorunde KAYIT.tsv yok (sembol surumu dogrulanamaz)')
print(f'{len(ciftler)} cift, {len(ciftler) - len(yap)} hazir, {len(yap)} uretilecek, isci {ISCI}', flush=True)


def tek(c):
    gecici = OUT / f'.gecici_{c}.mp4'
    r = subprocess.run(['python3', '-I', str(BURASI / 'video_el43.py'), c, str(KAP / f'KUPA_KAPAK_{c}.jpg'), str(gecici)],
                       capture_output=True, text=True, env=ENV)
    if r.returncode:
        gecici.unlink(missing_ok=True)
        return c, False, r.stderr[-400:]
    for j in OUT.glob(f'.gecici_{c}_*.jpg'):
        j.rename(OUT / j.name.replace('.gecici_', 'KUPA_VIDEO_'))
    os.replace(gecici, OUT / f'KUPA_VIDEO_{c}.mp4')
    bilgi = [l for l in r.stdout.splitlines() if 'maske' in l]
    return c, True, (bilgi[-1][-90:] if bilgi else '')


t0, bitti, hata = time.time(), 0, []
with ThreadPoolExecutor(ISCI) as ex:
    for fut in as_completed([ex.submit(tek, c) for c in yap]):
        c, ok, bilgi = fut.result()
        bitti += 1
        if not ok:
            hata.append(c)
        g = time.time() - t0
        print(f'{bitti}/{len(yap)} {c} {"OK" if ok else "HATA"} | {g:.0f} sn, kalan ~{g / bitti * (len(yap) - bitti):.0f} sn, '
              f'%{100 * bitti // len(yap)} | {bilgi}', flush=True)
print('HATA:', hata if hata else 'yok')
print('tamam', OUT, len(list(OUT.glob('KUPA_VIDEO_*.mp4'))), 'video')
