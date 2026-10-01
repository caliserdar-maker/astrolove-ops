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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kaynak', required=True)
    ap.add_argument('--kisisel', required=True)
    ap.add_argument('--medya', required=True)
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.kisisel)
    sys.path.insert(0, a.medya)
    import pilot11
    from PIL import Image
    import a1_poster
    t0 = time.time()
    sonuc = []
    dosyalar = sorted(Path(a.kaynak).glob('*/*/*.jpg'))
    for i, f in enumerate(dosyalar, 1):
        cift, renk, boy = f.parent.parent.name, f.parent.name, f.stem
        r = {'cift': cift, 'renk': renk, 'boy': boy, 'gecti': False, 'eksik': [], 'hata': None}
        try:
            o = pilot11.sayfa_olc(f)
            m = a1_poster.murekkep(pilot11.norm(Image.open(f).convert('RGB'))[0])
            o2, duz = a1_poster.olcum_duzelt(dict(o), m)
            r['eksik_ham'] = [k for k in GEREK if k not in o]
            r['eksik'] = [k for k in GEREK if k not in o2]
            r['gecti'] = not r['eksik']
            r['tag'] = {k: o2.get(k) for k in ('tag_bant', 'tag_x', 'tag_kumeleri')}
            r['isim_bant'] = o2.get('isim_bant')
            r['norm_boyut'] = o2.get('norm_boyut')
        except SystemExit as e:
            r['hata'] = f'SystemExit: {e}'
        except Exception as e:                                    # noqa: BLE001
            r['hata'] = f'{type(e).__name__}: {e}'
        sonuc.append(r)
        gecen = time.time() - t0
        print(f'[{i}/{len(dosyalar)}] {cift} {renk} {boy}: {"PASS" if r["gecti"] else "FAIL"} '
              f'{r["eksik"] or r["hata"] or ""} | {gecen:.0f} sn, kalan ~{gecen / i * (len(dosyalar) - i):.0f} sn',
              flush=True)
    fail = [x for x in sonuc if not x['gecti']]
    oz = {'toplam': len(sonuc), 'pass': len(sonuc) - len(fail), 'fail': len(fail),
          'fail_liste': [f"{x['cift']}/{x['renk']}/{x['boy']}" for x in fail], 'sure_sn': round(time.time() - t0, 1)}
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(a.cikti).write_text(json.dumps({'ozet': oz, 'sonuc': sonuc}, ensure_ascii=False, indent=1))
    print(json.dumps(oz, ensure_ascii=False))


if __name__ == '__main__':
    main()
