#!/usr/bin/env python3
"""SALT OKUR dogrulama (30 Eyl 2026, Serdar genel onayi): 10 cift + WP AQUARIUS_CANCER duzeltmeleri.
Sahte isimli (EMILY / JAMES) 11x14 siparisler pod_uret ile uretilir, TUM kapilar olculur. Drive'a, PLATES'e,
musteriye YAZMA YOK; sonuc yalniz loga (DOGRULA satirlari) basilir.
"""
import json, sys, time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
BOY = '11x14'
MESAJ = 'It Began With a Kiss in the Rain'
ISLER = [('AQUARIUS_CANCER', 'WARM_PARCHMENT'),
         ('LEO_LEO', 'DEEP_BLACK'), ('ARIES_LEO', 'DEEP_BLACK'), ('ARIES_LEO', 'PURE_WHITE'),
         ('CANCER_LEO', 'DEEP_BLACK'), ('CAPRICORN_LEO', 'DEEP_BLACK'), ('GEMINI_LEO', 'DEEP_BLACK'),
         ('LEO_LIBRA', 'DEEP_BLACK'), ('LIBRA_SCORPIO', 'DEEP_BLACK'), ('LIBRA_VIRGO', 'DEEP_BLACK'),
         ('LIBRA_LIBRA', 'DEEP_BLACK'), ('LIBRA_LIBRA', 'CHAMPAGNE_IVORY'), ('TAURUS_TAURUS', 'DEEP_BLACK'),
         ('ARIES_SCORPIO', 'MIDNIGHT_BLUE'), ('ARIES_SCORPIO', 'DEEP_BLACK'), ('ARIES_SCORPIO', 'PURE_WHITE'),
         ('ARIES_SCORPIO', 'CHAMPAGNE_IVORY')]


def main():
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, _ = sd.sayfa_no_tablosu()
    T0 = time.time(); ozet = []
    for n, (cift, renk) in enumerate(ISLER, 1):
        r = {'cift': cift, 'renk': renk}
        try:
            x = sd.normalize({'cift': cift, 'renk': renk, 'boy': BOY, 'urun': 'pod',
                              'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': MESAJ})
            x['receipt'] = f'DOGRULA_{cift}_{renk}'
            x['sayfa'] = no[cift]
            yol = sd.pod_kaynak(cift, renk, BOY)
            with Image.open(yol) as im:
                x['hedef_px'] = list(im.size)
            is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
            s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
            k = s.get('kapilar') or {}
            r.update({'durum': s.get('durum'), 'hata': s.get('hata'),
                      'gecti': s.get('durum') == 'URETILDI' and bool(k) and sd.kapi_sonucu(k),
                      'kalan': sorted(g for g, v in k.items() if v is False),
                      'mesaj': {q: (s.get('mesaj_kapisi') or {}).get(q) for q in ('dE', 'isim_rgb', 'mesaj_rgb')},
                      'sembol': {y: {q: ((s.get('sembol_kapisi') or {}).get(y) or {}).get(q) for q in ('iou', 'fark')}
                                 for y in ('sol', 'sag')},
                      'sembol_bant': (s.get('olcum') or {}).get('sembol_bant'),
                      'isim_kalinti': {q: (s.get('isim_kalinti_kapisi') or {}).get(q)
                                       for q in ('kalinti_sayisi', 'esikler')},
                      'isim_bandi': {q: (s.get('isim_bandi_temizligi') or {}).get(q)
                                     for q in ('kalinti_bileseni', 'degisen_px')},
                      'kenar': (s.get('isim_kenar_kapisi') or {}).get('kesilen_harf_px'),
                      'leke': {q: (s.get('leke_kapisi') or {}).get(q) for q in ('p99', 'en_kotu_blok_p99')},
                      'temiz_ara': {q: (s.get('temiz_ara_kapisi') or {}).get(q) for q in ('en_ort', 'en_tepe')},
                      'olcek': {q: (s.get('olcek_kapisi') or {}).get(q) for q in ('konum_fark_px', 'kenar_fark_px', 'sebep')},
                      'zemin_uyumu': s.get('zemin_uyumu')})
            yol.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['durum'] = 'HATA'; r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
        ozet.append(r)
        g = time.time() - T0
        print('DOGRULA', json.dumps(r, ensure_ascii=False, default=str), flush=True)
        print(f"[{n}/{len(ISLER)}] {cift} {renk}: {'PASS' if r.get('gecti') else 'FAIL'} kalan={r.get('kalan')} "
              f"{r.get('hata') or ''} | gecen {g:.0f}s | kalan ~{g / n * (len(ISLER) - n):.0f}s | "
              f"%{100 * n // len(ISLER)}", flush=True)
    print('OZET', json.dumps([(r['cift'], r['renk'], 'PASS' if r.get('gecti') else 'FAIL', r.get('kalan'))
                              for r in ozet]), flush=True)


if __name__ == '__main__':
    main()
