#!/usr/bin/env python3
"""SIPARIS PROVASI (Serdar 1 Eki 2026): 78 cift x 5 renk x 5 boy, deneme isimleriyle TAM siparis hatti.

Siparis aninda yalniz yazi katmani ve yazi kapilari kalsin diye, her plate / cift sorunu siparisten ONCE bulunur.
Hat surucu.py'nin AYNI asamalaridir (renk_asamasi / wp_asamasi); yalniz girdi deneme isimleri, cikti JSON.
Etsy / musteri / PLATES yazimi YOK. Sayfa JPEG'leri saklanmaz (yalniz kapi sonucu + sure).

Deneme setleri (giris_dogrula sinirlari: isim <= 11 harf Latin + Turkce, mesaj <= 35 karakter):
  A: sol EN UZUN (Turkce harfli), sag EN KISA, en uzun mesaj (Turkce harfli)
  B: sol EN KISA, sag EN UZUN (genis harfler), en uzun mesaj (virgul / iki nokta)
Cift sirasina gore A / B donusumlu (her cift bir uzun-isim tarafini sinar); --set ile sabitlenebilir.

--tur renk --renk R | --tur wp --boy B ; --ciftler C1,C2,...  -> <cikti>/PROVA_<tur>_<R|B>_<parca>.json
"""
import argparse, json, os, shutil, sys, time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surucu                                                     # noqa: E402

ON_TEST_CIFT = {'TARA': 'CANCER_LEO', 'SERDAR': 'CANCER_LIBRA', 'MAXI': 'CANCER_LIBRA', 'ANNE': 'CANCER_LEO',
                'LIAM': 'ARIES_VIRGO', 'CAGLA': 'CANCER_LEO'}
SETLER = {
    # ISIM ON TESTI (Serdar 1 Eki): olcek kapisi isim bagimli mi - 4 set x 5 renk x 5 boy
    'TARA': {'isim1': 'TARA', 'isim2': 'ROSS', 'mesaj': 'A King and his Crab'},
    'SERDAR': {'isim1': 'SERDAR', 'isim2': 'LENA', 'mesaj': 'To My Adorable Angel'},
    'MAXI': {'isim1': 'MAXIMILIAN', 'isim2': 'JO', 'mesaj': 'Two Souls, One Bond: Forever Ours!!'},
    'ANNE': {'isim1': 'ANNE-MARIE', 'isim2': 'LUCAS', 'mesaj': 'Love You to the Moon and Back'},
    # Test 4 kapisi (1 Eki): Test 3 isimleri + uzun aksanli isim
    'LIAM': {'isim1': 'LIAM', 'isim2': 'CATHERINE', 'mesaj': 'The World is Ours'},
    'CAGLA': {'isim1': 'ÇAĞLAYANGÜL', 'isim2': 'AL', 'mesaj': 'Yağmurda Başlayan Aşkımız Sonsuzdur'},
    'A': {'isim1': 'ÇAĞLAYANGÜL', 'isim2': 'AL', 'mesaj': 'Yağmurda Başlayan Aşkımız Sonsuzdur'},
    'B': {'isim1': 'JO', 'isim2': 'MAXIMILLIAN', 'mesaj': 'Two Souls, One Bond: Forever Ours!!'},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tur', required=True, choices=('renk', 'wp'))
    ap.add_argument('--renk'); ap.add_argument('--boy')
    ap.add_argument('--ciftler', required=True)
    ap.add_argument('--tum_ciftler', default='', help='sira (A/B donusumu icin); bos = --ciftler')
    ap.add_argument('--set', default='', help='A | B; bos = donusumlu')
    ap.add_argument('--kod', required=True); ap.add_argument('--kod-ref', default='')
    ap.add_argument('--parca', default='0')
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    cik = Path(a.cikti).resolve(); cik.mkdir(parents=True, exist_ok=True)
    kod = Path(a.kod).resolve()
    ciftler = [c for c in a.ciftler.split(',') if c]
    sira = [c for c in (a.tum_ciftler or a.ciftler).split(',') if c]
    os.chdir(kod)
    sd = surucu.kod_yukle(str(kod))
    anahtar = a.renk if a.tur == 'renk' else a.boy
    R = {'tur': a.tur, 'anahtar': anahtar, 'kod': a.kod_ref, 'parca': a.parca, 'ciftler': {}}
    yol = cik / f'PROVA_{a.tur}_{anahtar}_{a.parca}.json'
    asil_kaydet = None
    if a.tur == 'wp':                     # wp_asamasi kaydet_jpg'yi her cagrida sarar: her cift onayli fonksiyonla baslar
        import wp_ornek
        asil_kaydet = wp_ornek.kaydet_jpg
    t_tum = time.time()
    for i, cift in enumerate(ciftler):
        s = a.set or ('A' if sira.index(cift) % 2 == 0 else 'B')
        g = {'receipt': 'PROVA', 'cift': cift, **SETLER[s]}
        d = cik / 'is' / cift
        arg = SimpleNamespace(kod=str(kod), kod_ref=a.kod_ref, renk=a.renk, boy=a.boy, cikti=str(d))
        t0 = time.time()
        if asil_kaydet is not None:
            import wp_ornek
            wp_ornek.kaydet_jpg = asil_kaydet
        try:
            rc = (surucu.renk_asamasi if a.tur == 'renk' else surucu.wp_asamasi)(arg, g)
            if a.tur == 'renk':
                oz = json.loads((d / f'OZET_{a.renk}.json').read_text())
                r = {'gecti': rc == 0, 'durum': oz.get('durum'), 'pdf': (oz.get('pdf_kapisi') or {}).get('gecti'),
                     'sayfa': {o: {'gecti': v.get('kapilar_gecti'), 'kalan': v.get('kalan'), 'hata': v.get('hata')}
                               for o, v in oz['sayfa_kapilar'].items()}}
            else:
                oz = json.loads((d / f'OZET_WP_{a.boy}.json').read_text())
                r = {'gecti': rc == 0, 'durum': oz.get('durum'),
                     'kalan': sorted(k for k, v in (oz.get('kapilar') or {}).items() if v is False),
                     'duz_renk': (oz.get('wp_bakir') or {}).get('duz_renk'),
                     'eski_metin_izi': (oz.get('eski_metin_izi') or {}).get('fazla')}
        except BaseException as e:                                # noqa: BLE001
            r = {'gecti': False, 'hata': f'{type(e).__name__}: {str(e)[:300]}'}
        r.update({'set': s, 'sn': round(time.time() - t0, 1)})
        R['ciftler'][f'{cift}:{s}' if a.set else cift] = r
        gecen = time.time() - t_tum
        print(f'PROVA {a.tur} {anahtar} {cift} set {s} {"PASS" if r["gecti"] else "FAIL"} {r["sn"]} sn | '
              f'{i + 1}/{len(ciftler)} gecen {gecen / 60:.1f} dk kalan ~{gecen / (i + 1) * (len(ciftler) - i - 1) / 60:.1f} dk',
              flush=True)
        shutil.rmtree(d, ignore_errors=True)                       # sayfa / PDF saklanmaz
        for p in (sd.W / 'pod' / cift, ):                         # kaynak onbellegi (disk)
            shutil.rmtree(p, ignore_errors=True)
        yol.write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    R['sure_dk'] = round((time.time() - t_tum) / 60, 1)
    yol.write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    kotu = [c for c, v in R['ciftler'].items() if not v['gecti']]
    print('PROVA_SONUC', a.tur, anahtar, a.parca, f'{len(ciftler) - len(kotu)}/{len(ciftler)} PASS', kotu, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
