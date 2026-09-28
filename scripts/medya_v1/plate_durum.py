#!/usr/bin/env python3
"""PLATE DURUMU (baski-duzelt, 28 Eyl 2026). SALT OKUR: PLATES'e / POD_PRINT'e yazma yok.

5 renk x 13 satilan boy icin PLATES/<ED>_<boy>.png:
  YOK    - plate dosyasi yok (siparis SISTEM HATASI: PLATE YOK)
  KIRLI  - plate eski slogani iceriyor (plate_slogan_kapisi FAIL; siparis SISTEM HATASI)
  TEMIZ  - plate_slogan_kapisi PASS
Olcum: siparis_dosyasi.plate_slogan_kapisi, kaynak = POD_PRINT/CANCER_LIBRA/<RENK>/<boy>.jpg.
Ayrica siparis_dosyasi BOY tablosunda olmayan boylar isaretlenir (siparis normalize'da durur).
Cikti: <kok>/PLATE_DURUM.md + PLATE_DURUM.json
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

BOYLAR = ('8x10', '11x14', '12x16', '12x18', '16x20', '16x24', '18x24', '20x30', '24x36',
          '30x40', 'A4', 'A3', 'A2')                  # pod_print_build.RATIO_OF (13 satilan boy)
RENKLER = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY', 'WARM_PARCHMENT')
KISA = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'PURE_WHITE': 'PW',
        'CHAMPAGNE_IVORY': 'CI', 'WARM_PARCHMENT': 'WP'}
KAYNAK_CIFT = 'CANCER_LIBRA'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    liste = {x['Name']: x for x in json.loads(sd.rc('lsjson', sd.PLATES, '--files-only'))}
    d = sd.W / '_plate_durum'; d.mkdir(parents=True, exist_ok=True)
    sonuc, n, T0 = {}, 0, time.time()
    toplam = len(RENKLER) * len(BOYLAR)
    for renk in RENKLER:
        ed = sd.RENK_ED[renk]
        for boy in BOYLAR:
            n += 1
            ad = f'{ed.upper()}_{boy}.png'
            r = {'plate': ad, 'siparis_boy_tablosunda': boy in sd.BOY}
            if ad not in liste:
                r['durum'] = 'YOK'
            else:
                r['tarih'] = liste[ad].get('ModTime', '')[:16]
                r['MB'] = round(liste[ad].get('Size', 0) / 1e6, 1)
                try:
                    sd.rc('copy', f'{sd.PLATES}/{ad}', str(d), timeout=1800)
                    kaynak = sd.pod_kaynak(KAYNAK_CIFT, renk, boy)
                    k = sd.plate_slogan_kapisi(kaynak, d / ad, ed)
                    r['kapi'] = k
                    r['durum'] = 'TEMIZ' if k['gecti'] else (
                        'KIRLI' if 'glif_farkli_payi' in k else 'OLCULEMEDI')
                    kaynak.unlink(missing_ok=True)
                except Exception as e:                            # noqa: BLE001
                    r['durum'] = 'OLCULEMEDI'
                    r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
                (d / ad).unlink(missing_ok=True)
            sonuc[f'{renk}/{boy}'] = r
            g = time.time() - T0
            print(f'[{n}/{toplam}] {renk} {boy}: {r["durum"]} '
                  f'{(r.get("kapi") or {}).get("glif_farkli_payi", "")} | gecen {g:.0f}s | '
                  f'kalan ~{g / n * (toplam - n):.0f}s | %{100 * n // toplam}', flush=True)
    satir = ['# PLATE DURUMU (siparis hatti, 28 Eyl 2026)', '',
             f'Kaynak: `{sd.PLATES}`; olcum `plate_slogan_kapisi` (esik glif farkli payi >= '
             f'{sd.PLATE_SLOGAN_ESIK}), ornek dosya POD_PRINT/{KAYNAK_CIFT}. '
             'TEMIZ = siparis uretilir; KIRLI / YOK = siparis SISTEM HATASI (fail-closed). '
             '`*` = siparis_dosyasi BOY tablosunda yok (siparis "bilinmeyen boy" ile durur).', '',
             '| renk | ' + ' | '.join(f'{b}{"" if b in sd.BOY else "*"}' for b in BOYLAR) + ' |',
             '|---|' + '---|' * len(BOYLAR)]
    for renk in RENKLER:
        hucre = []
        for boy in BOYLAR:
            r = sonuc[f'{renk}/{boy}']
            p = (r.get('kapi') or {}).get('glif_farkli_payi')
            hucre.append(r['durum'] + (f' {p}' if p is not None else ''))
        satir.append(f'| {KISA[renk]} | ' + ' | '.join(hucre) + ' |')
    ozet = {}
    for key, r in sonuc.items():
        ozet.setdefault(r['durum'], []).append(key)
    satir += ['', '## Ozet', ''] + [f'- **{k}** ({len(v)}): ' + ', '.join(v) for k, v in sorted(ozet.items())]
    satir += ['', '## Ayrinti', '', '| plate | durum | tarih | MB | glif payi | not |', '|---|---|---|---|---|---|']
    for key, r in sonuc.items():
        k = r.get('kapi') or {}
        satir.append(f"| {r['plate']} | {r['durum']} | {r.get('tarih', '')} | {r.get('MB', '')} | "
                     f"{k.get('glif_farkli_payi', '')} | {k.get('sebep') or r.get('hata') or ''} |")
    (d / 'PLATE_DURUM.md').write_text('\n'.join(satir) + '\n')
    (d / 'PLATE_DURUM.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(d), a.kok, '--include', 'PLATE_DURUM.*')
    print('\n'.join(satir[:12]))


if __name__ == '__main__':
    main()
