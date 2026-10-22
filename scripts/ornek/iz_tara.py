#!/usr/bin/env python3
"""ESKI METIN IZI taramasi (salt okur; Serdar 2 Eki IZ TANISI). Duzeltme / yeniden uretim YOK.
Olcu: surucu.iz_olc (uretimin kendi iz olcusu = siparis-baski-v1 eski_metin_izi_kapisi, esik 0.6), kopya yazilmaz.
Eski slogan kaynagi: POD_PRINT/<CIFT>/<RENK>/<boy>.jpg. Bant (tag_bant / tag_x): sd.plate_slogan_kapisi(kaynak,
PLATES/<ED>_<boy>.png) - siparis yolu ile ayni.
  --tur galeri : TEMP/GALERI_77/_KAYNAK/<CIFT>/BASKI_{MIDNIGHT_BLUE,DEEP_BLACK}.jpg (kart 15 / 16), 11x14 kaynak;
                 --parca i --parca-say n -> ciftler[i::n] (paralel parca)
  --tur cift   : --cift X --renk R: Etsy dijital ZIP JPG'leri (5 boy) kaynak POD boyuna karsi + 1:1 kesitler
Cikti: JSON satirlari; iz FAIL olan her dosya icin bant 1:1 kesiti (KESIT_*.jpg). Isim / mesaj loga yazilmaz.
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
sys.path.insert(0, str(KOK / 'siparis_dijital'))
import surucu  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
POD = 'gdrive:ASTROLOVE/TEMP/POD_PRINT'
GAL = 'gdrive:ASTROLOVE/TEMP/GALERI_77/_KAYNAK'
ZIP_BOY = {'2x3': '24x36', '3x4': '18x24', '4x5': '16x20', '11x14': '11x14', 'A': 'A2'}


def rc(*a):
    return subprocess.run(['rclone', '--tpslimit', '4', '--retries', '5', '--low-level-retries', '20', *a],
                          check=True, capture_output=True, text=True).stdout


class Olcer:
    def __init__(self, kod):
        self.sd = surucu.kod_yukle(kod)
        self.sd.kisisel_hazirla()
        self.P = self.sd.EdisyonPoster()

    def bant(self, kaynak_yol, renk, boy):
        sd = self.sd
        pl = self.P.plate(sd.RENK_ED[renk], sd.BOY[boy][0], boy)
        return sd.plate_slogan_kapisi(Path(kaynak_yol).read_bytes(), pl, sd.RENK_ED[renk])

    def olc(self, cikti_yol, kaynak_yol, renk, boy):
        pk = self.bant(kaynak_yol, renk, boy)
        if not pk.get('tag_bant'):
            return {'gecti': None, 'sebep': 'mesaj bandi olculemedi', 'plate_gecti': pk.get('gecti')}, None
        with Image.open(cikti_yol) as im:
            r = surucu.iz_olc(im, Path(kaynak_yol).read_bytes(), pk['tag_bant'], pk['tag_x'], self.sd)
        r['tag_bant'], r['tag_x'] = list(pk['tag_bant']), list(pk['tag_x'])
        return r, pk


def kesit(yol, r, hedef, kalite=90):
    """iz bandi 1:1 (tam cozunurluk): tag_bant / tag_x 2400 biriminden olceklenir, +%15 pay."""
    with Image.open(yol) as im:
        W, H = im.size
        s = W / 2400.0
        (y0, y1), (x0, x1) = r['tag_bant'], r['tag_x']
        py = int(0.15 * (y1 - y0) * s)
        im.convert('RGB').crop((max(int(x0 * s) - 40, 0), max(int(y0 * s) - py, 0),
                                min(int(x1 * s) + 40, W), min(int(y1 * s) + py, H))).save(hedef, 'JPEG', quality=kalite)


def sonuc(r):
    return 'HATA' if 'hata' in r else ('OLCULEMEDI' if r.get('gecti') is None else ('PASS' if r['gecti'] else 'IZ_VAR'))


def yaz(f, k, n, toplam, t0):
    f.write(json.dumps(k) + '\n'); f.flush()
    g = time.time() - t0
    print(f"IZ {n}/{toplam} {k['urun']} {k['boy']} fazla={k.get('fazla')} {k['sonuc']} "
          f"| gecen {g:.0f} sn kalan ~{g / n * (toplam - n):.0f} sn %{100 * n // max(toplam, 1)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tur', choices=('galeri', 'cift'), required=True)
    ap.add_argument('--kod', required=True)                 # siparis-baski-v1 checkout
    ap.add_argument('--parca', type=int, default=0)
    ap.add_argument('--parca-say', type=int, default=1)
    ap.add_argument('--cift', default='')
    ap.add_argument('--renk', default='DEEP_BLACK')
    ap.add_argument('--zip-index', default='')
    ap.add_argument('--cik', required=True)                 # klasor
    ap.add_argument('--yerel', nargs=2, metavar=('CIKTI', 'KAYNAK'))   # yerel deneme: tek dosya, Drive yok
    a = ap.parse_args()
    t0 = time.time()
    cik = Path(a.cik); cik.mkdir(parents=True, exist_ok=True)
    O = Olcer(a.kod)
    print(f'HAZIR {time.time() - t0:.0f} sn', flush=True)
    with open(cik / f'IZ_{a.tur.upper()}_{a.parca}.jsonl', 'w') as f, tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if a.yerel:
            r, _ = O.olc(a.yerel[0], a.yerel[1], a.renk, '11x14')
            r = {'urun': 'YEREL', 'boy': '11x14', **r, 'sonuc': sonuc(r)}
            yaz(f, r, 1, 1, t0)
            if 'tag_bant' in r:
                kesit(a.yerel[0], r, cik / 'KESIT_YEREL.jpg')
            return
        if a.tur == 'galeri':
            ciftler = sorted(x.strip('/') for x in rc('lsf', GAL, '--dirs-only').split())[a.parca::a.parca_say]
            toplam, n = len(ciftler) * 2, 0
            for c in ciftler:
                for renk, kart in (('MIDNIGHT_BLUE', '15'), ('DEEP_BLACK', '16')):
                    g, s = tmp / f'{c}_{renk}_galeri.jpg', tmp / f'{c}_{renk}_pod.jpg'
                    try:
                        rc('copyto', f'{GAL}/{c}/BASKI_{renk}.jpg', str(g))
                        rc('copyto', f'{POD}/{c}/{renk}/11x14.jpg', str(s))
                        r, _ = O.olc(g, s, renk, '11x14')
                    except Exception as e:                    # noqa: BLE001
                        r = {'hata': f'{type(e).__name__}: {str(e)[:200]}'}
                    n += 1
                    k = {'urun': f'GALERI_{c}_kart{kart}', 'cift': c, 'renk': renk, 'boy': '11x14', **r, 'sonuc': sonuc(r)}
                    if k['sonuc'] == 'IZ_VAR':
                        kesit(g, r, cik / f'KESIT_{c}_{renk}_kart{kart}.jpg')
                    yaz(f, k, n, toplam, t0)
                    g.unlink(missing_ok=True); s.unlink(missing_ok=True)
        else:
            ed = '_'.join(w.capitalize() for w in a.renk.split('_'))
            ca, cb = (w.capitalize() for w in a.cift.split('_', 1))
            zips = [z for z in json.load(open(a.zip_index)) if z['Name'] == f'{ca}_{cb}_{ed}_ALL_SIZES.zip']
            if not zips:                                           # 0 ZIP basari sayilmaz (ders 48)
                print('HATA: ZIP yok', flush=True); sys.exit(2)
            toplam, n = len(zips) * 5 + 5, 0
            for b in ('16x20', '18x24', '24x36', '11x14', 'A2'):   # POD baski dosyasi: kendisi 1:1 kesit (gozle)
                s = tmp / f'pod_{b}.jpg'
                rc('copyto', f'{POD}/{a.cift}/{a.renk}/{b}.jpg', str(s))
                pk = O.bant(s, a.renk, b)
                n += 1
                k = {'urun': f'POD_{a.cift}', 'renk': a.renk, 'boy': b, 'gecti': None, 'sebep': 'kaynak (eski slogan burada)',
                     'tag_bant': pk.get('tag_bant'), 'tag_x': pk.get('tag_x'), 'sonuc': 'KAYNAK'}
                if pk.get('tag_bant'):
                    kesit(s, k, cik / f'KESIT_POD_{a.cift}_{a.renk}_{b}.jpg')
                yaz(f, k, n, toplam, t0)
            for zi, z in enumerate(sorted(zips, key=lambda q: q.get('ModTime', ''))):
                zy = tmp / f'z{zi}.zip'
                rc('copyto', f"gdrive:ASTROLOVE/{z['Path']}", str(zy))
                with zipfile.ZipFile(zy) as zf:
                    for ad in sorted(x for x in zf.namelist() if x.lower().endswith('.jpg')):
                        b = ZIP_BOY.get(Path(ad).stem.rsplit('_', 1)[-1], '?')
                        j = tmp / Path(ad).name
                        j.write_bytes(zf.read(ad))
                        try:
                            r, _ = O.olc(j, tmp / f'pod_{b}.jpg', a.renk, b) if b != '?' else ({'hata': 'boy?'}, None)
                        except Exception as e:                # noqa: BLE001
                            r = {'hata': f'{type(e).__name__}: {str(e)[:200]}'}
                        n += 1
                        k = {'urun': f'ZIP_{a.cift}', 'dosya': Path(ad).name, 'zip_yol': z['Path'], 'zip_mod': z.get('ModTime'),
                             'renk': a.renk, 'boy': b, **r, 'sonuc': sonuc(r)}
                        if 'tag_bant' in r:
                            kesit(j, r, cik / f'KESIT_ZIP{zi}_{a.cift}_{a.renk}_{b}.jpg')
                        yaz(f, k, n, toplam, t0)
                        j.unlink()
                zy.unlink()


if __name__ == '__main__':
    main()
