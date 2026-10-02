#!/usr/bin/env python3
"""YAYINDAKI dijital dosyalarda tagline DIKIS olcumu (salt okur; Serdar 2 Eki). Yeniden uretim YOK.
Bant: surucu._bantlar (siparis yolunun bant bulucusu; 2400 genislikte), olcu: dikis_kapisi.dikis (ornek kosusu ile ayni,
esik 13). Kopya olcum yazilmaz (ders 33). Dosyalar tek tek indirilir, olculur, silinir.
  --tur zip    : Drive'daki <SIGN>_<SIGN>_<EDISYON>_ALL_SIZES.zip (Etsy dijital ilan dosyasi), icindeki 5 JPG
  --tur galeri : TEMP/GALERI_77/_KAYNAK/<CIFT>/BASKI_{MIDNIGHT_BLUE,DEEP_BLACK}.jpg (galeri kart 15 / 16 kaynagi)
Cikti: JSON satirlari (urun, dosya, renk, boy, dikis, ust/alt/govde, PASS/FAIL). Isim / mesaj loga yazilmaz.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / 'ornek')); sys.path.insert(0, str(KOK / 'siparis_dijital'))
import dikis_kapisi as dk  # noqa: E402
import surucu  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ESIK = 13.0
BOY_ADI = {'2x3': '24x36', '3x4': '18x24', '4x5': '16x20', '11x14': '11x14', 'A': 'A2'}


def rc(*a):
    return subprocess.run(['rclone', '--tpslimit', '4', '--retries', '5', '--low-level-retries', '20', *a], check=True, capture_output=True, text=True).stdout


def olc(yol, tmp):
    """Tagline bandi (surucu._bantlar 'mesaj') -> tam cozunurlukte kirp -> dk.dikis."""
    with Image.open(yol) as im:
        W, H = im.size
        im.draft('RGB', (2400, int(2400 * H / W)))
        k = im.convert('RGB')
        if k.width != 2400:
            k = k.resize((2400, round(2400 * H / W)), Image.BILINEAR)
    kucuk = Path(tmp) / 'k.jpg'; k.save(kucuk, quality=95)
    b = {x[0]: x for x in surucu._bantlar(kucuk)}
    if 'mesaj' not in b:
        return {'hata': f'mesaj bandi yok ({list(b)})', 'px': [W, H]}
    _, x0, x1, y0, y1, _w = b['mesaj']
    s = W / 2400.0
    X0, X1, Y0, Y1 = int(x0 * s), int(x1 * s), int(y0 * s), int(y1 * s)
    p = int(0.12 * (Y1 - Y0))
    with Image.open(yol) as im:
        tag = im.convert('RGB').crop((max(X0 - p, 0), max(Y0 - p, 0), min(X1 + p, W), min(Y1 + p, H)))
    d = dk.dikis(tag)
    d.update({'px': [W, H], 'tag_kutu': [X0, Y0, X1, Y1]})
    return d


def satir(f, kayit, n, toplam, t0):
    f.write(json.dumps(kayit) + '\n'); f.flush()
    g = time.time() - t0
    print(f"DIKIS {n}/{toplam} {kayit['urun']} {kayit['boy']} {kayit.get('dikis')} {kayit['sonuc']} "
          f"| gecen {g:.0f} sn kalan ~{g / n * (toplam - n):.0f} sn %{100 * n // max(toplam, 1)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tur', choices=('zip', 'galeri'), required=True)
    ap.add_argument('--edisyon', default='')
    ap.add_argument('--zip-index', default='')        # rclone lsjson ciktisi (zip)
    ap.add_argument('--cik', required=True)
    a = ap.parse_args()
    t0 = time.time()
    with open(a.cik, 'w') as f, tempfile.TemporaryDirectory() as tmp:
        if a.tur == 'zip':
            ed = '_'.join(w.capitalize() for w in a.edisyon.split('_'))     # MIDNIGHT_BLUE -> Midnight_Blue (Drive ZIP adi)
            idx = [z for z in json.load(open(a.zip_index)) if z['Name'].endswith(f'_{ed}_ALL_SIZES.zip')]
            if not idx:                                                       # 0 ZIP basari sayilmaz (ders 48)
                print(f'HATA: {ed} icin ZIP yok', flush=True); sys.exit(2)
            ad_say = {}
            for z in idx:
                ad_say.setdefault(z['Name'], []).append(z)
            toplam, n = len(ad_say) * 5, 0
            for ad, liste in sorted(ad_say.items()):
                z = max(liste, key=lambda q: q.get('ModTime', ''))      # ayni ad birden fazla: en yeni (raporlanir)
                yol = Path(tmp) / ad
                rc('copyto', f"gdrive:ASTROLOVE/{z['Path']}", str(yol))
                with zipfile.ZipFile(yol) as zf:
                    for zi in sorted(x for x in zf.namelist() if x.lower().endswith('.jpg')):
                        j = Path(tmp) / Path(zi).name
                        j.write_bytes(zf.read(zi))
                        boy = Path(zi).stem.rsplit('_', 1)[-1]
                        try:
                            d = olc(j, tmp)
                        except Exception as e:                    # noqa: BLE001
                            d = {'hata': f'{type(e).__name__}: {e}'}
                        n += 1
                        sonuc = 'HATA' if 'hata' in d else ('PASS' if d['dikis'] <= ESIK else 'FAIL')
                        satir(f, {'urun': ad.replace('_ALL_SIZES.zip', ''), 'dosya': Path(zi).name, 'renk': a.edisyon,
                                  'boy': BOY_ADI.get(boy, boy), 'zip_yol': z['Path'], 'ayni_ad_sayisi': len(liste),
                                  **d, 'esik': ESIK, 'sonuc': sonuc}, n, toplam, t0)
                        j.unlink()
                yol.unlink()
        else:
            K = 'gdrive:ASTROLOVE/TEMP/GALERI_77/_KAYNAK'
            ciftler = sorted(x.strip('/') for x in rc('lsf', K, '--dirs-only').split())
            toplam, n = len(ciftler) * 2, 0
            for c in ciftler:
                for renk, kart in (('MIDNIGHT_BLUE', '15'), ('DEEP_BLACK', '16')):
                    j = Path(tmp) / f'{c}_{renk}.jpg'
                    try:
                        rc('copyto', f'{K}/{c}/BASKI_{renk}.jpg', str(j))
                        d = olc(j, tmp)
                    except Exception as e:                        # noqa: BLE001
                        d = {'hata': f'{type(e).__name__}: {str(e)[:200]}'}
                    n += 1
                    sonuc = 'HATA' if 'hata' in d else ('PASS' if d['dikis'] <= ESIK else 'FAIL')
                    satir(f, {'urun': f'GALERI_{c}_kart{kart}', 'dosya': f'BASKI_{renk}.jpg', 'renk': renk, 'boy': '11x14',
                              **d, 'esik': ESIK, 'sonuc': sonuc}, n, toplam, t0)
                    j.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
