#!/usr/bin/env python3
"""KAYNAK ON TESTI (1 Eki 2026, Test 3 dersi): siparis gelmeden her cift x renk x boy kaynak dosyasinin
olculebildigini denetler. Isim / mesaj yok; yalniz kaynak POD_PRINT dosyasi.

Test 3 (ARIES_VIRGO) MB 24x36: a1_poster.sayfa_kur -> pilot16.oran_kur KeyError 'tag_bant'
(kaynak sayfanin kendi olcumunde tagline bandi bulunamadi). Bu script ayni olcumu (pilot11.sayfa_olc +
a1_poster.olcum_duzelt) kosar ve eksik anahtarlari raporlar.

Kullanim: kaynak_olcum.py --kaynak _src --kisisel <kisisel-v1/scripts/kisisel> --medya <siparis-baski-v1/scripts/medya_v1>
          --cikti out/kaynak_olcum.json
_src yapisi: _src/<CIFT>/<RENK>/<boy>.jpg
Cikti: {"ozet": {...}, "sonuc": [{"cift","renk","boy","gecti","eksik":[...],"hata", "tag": {...}}]}
"""
import argparse, json, sys, time
from pathlib import Path

GEREK = ('isim_bant', 'sol_isim', 'sonsuz', 'sag_isim', 'sembol_bant', 'sembol', 'tag_bant', 'tag_x', 'isim_govde')


_YOL = {}
# uretimdeki edisyon -> plate adi (siparis_dosyasi.EdisyonPoster.plate); MB plate maskesi kullanmaz (a1_poster yolu)
ED_PLATE = {'MIDNIGHT_BLUE': None, 'DEEP_BLACK': 'BLACK', 'PURE_WHITE': 'PURE_WHITE',
            'CHAMPAGNE_IVORY': 'MODERN', 'WARM_PARCHMENT': 'VINTAGE'}


def _hazirla(kisisel, medya, plates=''):
    sys.path.insert(0, kisisel)
    sys.path.insert(0, medya)
    _YOL['plates'] = plates


_MASKE = {}
SLOGAN_PLATE = {'MIDNIGHT_BLUE': 'BLUE', 'DEEP_BLACK': 'BLACK', 'PURE_WHITE': 'PURE_WHITE',
                'CHAMPAGNE_IVORY': 'MODERN', 'WARM_PARCHMENT': 'VINTAGE'}


def _plate_maske(sd, yol):
    """Plate fark maskesi ureticisi surec basina BIR KEZ (20 plate; VINTAGE_A2 ~50 MB her dosyada yeniden aciliyordu)."""
    if yol not in _MASKE:
        _MASKE[yol] = sd.plate_fark_maskesi(yol)
    return _MASKE[yol]


def olc_tek(f):
    """URETIMLE AYNI OLCUM YOLU (Test 4 kapisi): MB -> a1_poster.Poster.sayfa_kur (sayfa_olc_guvenli, duz esik);
    diger renkler -> siparis_dosyasi.EdisyonPoster.olc (plate fark maskesi + sayfa_olc_guvenli, edisyon murekkebi)."""
    import numpy as np
    import pilot11
    from PIL import Image
    import a1_poster
    f = Path(f)
    cift, renk, boy = f.parent.parent.name, f.parent.name, f.stem
    r = {'cift': cift, 'renk': renk, 'boy': boy, 'gecti': False, 'eksik': [], 'hata': None}
    try:
        ref_norm = pilot11.norm(Image.open(f).convert('RGB'))[0]
        if renk == 'WARM_PARCHMENT':
            # WP uretim yolu (surucu.wp_asamasi): kaynak yalniz plate_slogan_kapisi ile olculur (edisyon yerel kontrast
            # maskesi, tagline yoksa plate fark maskesi); isim/sembol bantlari BAKIR hattinda CI'dan hizalanir.
            import siparis_dosyasi as sd
            pl = Path(_YOL.get('plates') or '_plates') / f'VINTAGE_{boy}.png'
            if not pl.exists():
                r['hata'] = f'PLATE YOK: {pl.name}'
                return r
            pk = sd.plate_slogan_kapisi(f, str(pl), 'vintage')
            r['yol'] = f'plate_slogan_kapisi (WP, plate {pl.name})'
            r['eksik'] = [k for k in ('tag_bant', 'tag_x') if not pk.get(k)]
            r['gecti'] = bool(pk.get('gecti')) and not r['eksik']
            r['tag'] = {k: pk.get(k) for k in ('tag_bant', 'tag_x')}
            r['slogan'] = {k: pk.get(k) for k in ('gecti', 'sebep', 'glif_farkli_payi', 'olcum')}
            return r
        if ED_PLATE.get(renk) is None:
            o, yedek = a1_poster.sayfa_olc_guvenli(pilot11, f)
            m = a1_poster.murekkep(ref_norm)
            r['yol'] = 'a1_poster (MB)'
        else:
            import siparis_dosyasi as sd
            pl = Path(_YOL.get('plates') or '_plates') / f'{ED_PLATE[renk]}_{boy}.png'
            if not pl.exists():
                r['hata'] = f'PLATE YOK: {pl.name}'
                return r
            sd.olcek_kur(2400)
            m = sd._mod('edisyon_uret').murekkep(np.asarray(ref_norm).astype(np.float32))
            o, yedek = a1_poster.sayfa_olc_guvenli(pilot11, f, maske=_plate_maske(sd, str(pl)))
            r['yol'] = f'EdisyonPoster.olc (plate {pl.name})'
        r['olcum_yedek'] = yedek
        o2, duz = a1_poster.olcum_duzelt(dict(o), m)
        # uretim render_et PLATE KAPISI: her renkte plate_slogan_kapisi (MB dahil, BLUE plate)
        import siparis_dosyasi as sd
        sp = Path(_YOL.get('plates') or '_plates') / f'{SLOGAN_PLATE[renk]}_{boy}.png'
        if sp.exists():
            pk = sd.plate_slogan_kapisi(f, str(sp), sd.RENK_ED[renk])
            r['slogan'] = {k: pk.get(k) for k in ('gecti', 'sebep', 'glif_farkli_payi', 'olcum')}
        else:
            r['slogan'] = {'gecti': False, 'sebep': f'PLATE YOK: {sp.name}'}
        r['eksik_ham'] = [k for k in GEREK if k not in o]
        r['eksik'] = [k for k in GEREK if k not in o2]
        r['gecti'] = not r['eksik'] and bool(r['slogan'].get('gecti'))
        r['tag'] = {k: o2.get(k) for k in ('tag_bant', 'tag_x', 'tag_kumeleri')}
        r['isim_bant'] = o2.get('isim_bant')
        r['norm_boyut'] = o2.get('norm_boyut')
        if not r['gecti']:                        # AYRINTI (Test 3): alt yari bantlari + kume araliklari (yalniz sayi)
            import numpy as np
            from pilot6 import kumeler, LUMA, MUREKKEP
            im, _k = pilot11.norm(Image.open(f).convert('RGB'))
            mm = (np.asarray(im).astype(np.float32) @ LUMA) > MUREKKEP
            H = im.height
            r['bantlar'] = [{'b': [int(b0), int(b1)], 'oran': round((b0 + b1) / 2 / H, 3),
                             'kume20': [[int(c0), int(c1)] for c0, c1 in kumeler(mm[b0:b1], 20)][:14]}
                            for b0, b1 in pilot11.bantlar(mm) if b1 > 0.5 * H]
            print('AYRINTI', cift, renk, boy, json.dumps(r['bantlar']), flush=True)
    except SystemExit as e:
        r['hata'] = f'SystemExit: {e}'
    except Exception as e:                                        # noqa: BLE001
        r['hata'] = f'{type(e).__name__}: {e}'
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--kisisel', required=True)
    ap.add_argument('--medya', required=True)
    ap.add_argument('--cikti', required=True)
    ap.add_argument('--is', dest='surec', type=int, default=4, help='paralel surec')
    ap.add_argument('--plates', default='_plates', help='PLATES kopyasi (<ED>_<boy>.png)')
    a = ap.parse_args()
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    dosyalar = [str(x) for x in sorted(Path(a.kaynak).glob('*/*/*.jpg'))]
    sonuc = []
    with ProcessPoolExecutor(a.surec, initializer=_hazirla, initargs=(a.kisisel, a.medya, str(Path(a.plates).resolve()))) as ex:
        for i, r in enumerate(ex.map(olc_tek, dosyalar, chunksize=4), 1):
            sonuc.append(r)
            gecen = time.time() - t0
            print(f'[{i}/{len(dosyalar)} %{100 * i // max(len(dosyalar), 1)}] {r["cift"]} {r["renk"]} {r["boy"]}: '
                  f'{"PASS" if r["gecti"] else "FAIL"} {r["eksik"] or r["hata"] or ((r.get("slogan") or {}).get("sebep") or "")} | {gecen:.0f} sn, '
                  f'kalan ~{gecen / i * (len(dosyalar) - i):.0f} sn', flush=True)
    fail = [x for x in sonuc if not x['gecti']]
    oz = {'toplam': len(sonuc), 'pass': len(sonuc) - len(fail), 'fail': len(fail),
          'fail_liste': [f"{x['cift']}/{x['renk']}/{x['boy']}" for x in fail], 'sure_sn': round(time.time() - t0, 1)}
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(a.cikti).write_text(json.dumps({'ozet': oz, 'sonuc': sonuc}, ensure_ascii=False, indent=1))
    print(json.dumps(oz, ensure_ascii=False))


if __name__ == '__main__':
    main()
