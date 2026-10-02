#!/usr/bin/env python3
"""ORNEK DERLE: ONCE / SONRA sayfalarindan tagline kesitleri (1:1) + dikis olcusu + tam sayfa onizleme.
Tagline bolgesi = ONCE ile SONRA sayfalarinin farki (duzeltme yalniz tagline boyasini degistirir).
Girdi: <giris>/<durum>_<etiket>/ (ornek_is ciktilari). Cikti: <cikti>/ KESIT_*, ONIZLEME_*, OLCUM.md, OLCUM.json"""
import json, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dikis_kapisi as dk                                           # noqa: E402
Image.MAX_IMAGE_PIXELS = None


def sayfa(d):
    j = sorted(d.glob('SAYFA_*.jpg')) + sorted(d.glob('WP_*.jpg'))
    return Image.open(j[0]).convert('RGB') if j else None


def etiketli(im, yazi):
    b = Image.new('RGB', (im.width, im.height + 28), (255, 255, 255)); b.paste(im, (0, 28))
    ImageDraw.Draw(b).text((6, 6), yazi, fill=(0, 0, 0)); return b


def kesit_ve_olcu(A, B, et, cikti):
    """Tagline bandi = ONCE/SONRA fark satirlarinin en yogun kesintisiz bandi (dagilmis doku farki disarida)."""
    a, b = np.asarray(A).astype(np.int16), np.asarray(B).astype(np.int16)
    fm = np.abs(a - b).max(2) > 8
    sr = fm.sum(1)
    if sr.max() < 20:
        return {'hata': f'ONCE/SONRA farki yok ({int(fm.sum())} px)'}
    yc = int(np.argmax(sr)); var = sr >= 2; bosluk = max(15, int(0.004 * A.height))   # seyrek ust uzantilar dahil
    y0 = yc
    while y0 > 0 and var[max(y0 - bosluk, 0):y0].any():
        y0 = max(y0 - bosluk, 0) + int(np.nonzero(var[max(y0 - bosluk, 0):y0])[0][0])
    y1 = yc
    while y1 < len(sr) - 1 and var[y1 + 1:y1 + 1 + bosluk].any():
        y1 = y1 + 1 + int(np.nonzero(var[y1 + 1:y1 + 1 + bosluk])[0][-1])
    xs = np.nonzero(fm[y0:y1 + 1].any(0))[0]
    x0, x1 = np.percentile(xs, 0.1), np.percentile(xs, 99.9)
    H = max(y1 - y0, 10); p = int(0.12 * H)
    kut = (max(int(x0) - p, 0), max(int(y0) - p, 0), min(int(x1) + p, A.width), min(int(y1) + p, A.height))
    TA, TB = A.crop(kut), B.crop(kut)
    da, db = dk.dikis(TA), dk.dikis(TB)
    out = {'tagline_kutu': kut, 'ONCE': da, 'SONRA': db, 'tani': f'bant {y0}-{y1} fark px {int(fm.sum())}'}
    taban = da.get('taban', db.get('taban', y1 - kut[1] - int(0.25 * H)))
    ust0 = y0 - kut[1]
    for ad, (r0, r1) in (('UST', (ust0 - int(0.06 * H), ust0 + int(0.30 * H))),
                         ('ALT', (taban - int(0.16 * H), taban + int(0.16 * H)))):
        r0, r1 = max(r0, 0), min(r1, TA.height)
        ka, kb = TA.crop((0, r0, TA.width, r1)), TB.crop((0, r0, TB.width, r1))
        t = Image.new('RGB', (ka.width, ka.height * 2 + 64), (255, 255, 255))
        t.paste(etiketli(ka, f'ONCE {et} {ad} 1:1 dikis_{ad.lower()} {da.get("dikis_" + ad.lower(), da.get("hata"))}'), (0, 0))
        t.paste(etiketli(kb, f'SONRA {et} {ad} 1:1 dikis_{ad.lower()} {db.get("dikis_" + ad.lower(), db.get("hata"))}'), (0, ka.height + 34))
        t.save(cikti / f'KESIT_{et}_{ad}_1e1.jpg', quality=95)
    on = B.resize((int(B.width * 1800 / B.height), 1800), Image.LANCZOS)
    on.save(cikti / f'ONIZLEME_SONRA_{et}.jpg', quality=90)
    A.resize(on.size, Image.LANCZOS).save(cikti / f'ONIZLEME_ONCE_{et}.jpg', quality=90)
    return out


def main(giris, cikti):
    giris, cikti = Path(giris), Path(cikti); cikti.mkdir(parents=True, exist_ok=True)
    etiketler = sorted({p.name.split('_', 1)[1] for p in giris.iterdir() if p.is_dir() and p.name.startswith(('ONCE_', 'SONRA_')) and 'SEMBOL_' not in p.name})
    tablo, t0 = [], time.time()
    for n, et in enumerate(etiketler, 1):
        A, B = sayfa(giris / f'ONCE_{et}'), sayfa(giris / f'SONRA_{et}')
        sat = {'etiket': et}
        if A is None or B is None or A.size != B.size:
            sat['hata'] = f'sayfa eksik (ONCE {A is not None}, SONRA {B is not None})'; tablo.append(sat); continue
        try:
            sat.update(kesit_ve_olcu(A, B, et, cikti))
        except Exception as e:                                  # noqa: BLE001  (tek etiket kosuyu durdurmaz)
            sat['hata'] = f'{type(e).__name__}: {e}'
        da, db = sat.get('ONCE') or {}, sat.get('SONRA') or {}
        tablo.append(sat)
        g = time.time() - t0
        print(f'DERLE {n}/{len(etiketler)} {et} gecen {g:.0f} sn kalan ~{g / n * (len(etiketler) - n):.0f} sn '
              f'(%{100 * n // len(etiketler)}) ONCE ust/alt {da.get("dikis_ust")}/{da.get("dikis_alt")} '
              f'SONRA {db.get("dikis_ust")}/{db.get("dikis_alt")} {sat.get("hata", "")} {sat.get("tani", "")}', flush=True)
    sat = ['# ORNEK DIKIS (tagline) - ONCE / SONRA', '', 'olcu: scripts/ornek/dikis_kapisi.py (murekkep ici satir medyani RGB, '
           '11 satirlik medyan trendden en buyuk sapma); kapi onerisi ust ve alt <= 13', '',
           '| etiket | ONCE ust | ONCE alt | SONRA ust | SONRA alt | SONRA govde |', '|---|---|---|---|---|---|']
    for t in tablo:
        if 'hata' in t:
            sat.append(f"| {t['etiket']} | HATA {t['hata']} | | | | |"); continue
        o, s = t['ONCE'], t['SONRA']
        if 'hata' in o or 'hata' in s:
            sat.append(f"| {t['etiket']} | {o.get('hata', o.get('dikis_ust'))} | | {s.get('hata', s.get('dikis_ust'))} | | |"); continue
        sat.append(f"| {t['etiket']} | {o['dikis_ust']} | {o['dikis_alt']} | {s['dikis_ust']} | {s['dikis_alt']} | {s['dikis_govde']} |")
    (cikti / 'OLCUM.md').write_text('\n'.join(sat) + '\n'); (cikti / 'OLCUM.json').write_text(json.dumps(tablo, default=str, indent=1))
    print('\n'.join(sat))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
