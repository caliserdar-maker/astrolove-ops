#!/usr/bin/env python3
"""HIZ PROFILI (Serdar 1 Eki: MB ~10x yavas, WP 24x36 16+ dk): tek sayfanin TAM siparis hatti cProfile altinda.
--tur renk: sd._dijital_is (renk, oran) ayni surecte; --tur wp: surucu.wp_asamasi (boy). Cikti: en cok sure alan
fonksiyonlar (kumulatif + kendi), yalniz fonksiyon adi / sure. Isim / mesaj loga yazilmaz (girdi maskeli)."""
import cProfile, io, os, pstats, sys, time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surucu                                                     # noqa: E402


def main():
    tur, anahtar, kod = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
    g = surucu.girdi()
    os.chdir(kod)
    sd = surucu.kod_yukle(str(kod))
    sd.kisisel_hazirla()
    no, _ = sd.sayfa_no_tablosu()
    pr = cProfile.Profile()
    t0 = time.time()
    if tur == 'renk':
        renk, oran = anahtar.split(':')
        sip = sd.normalize({'receipt': g['receipt'], 'cift': g['cift'], 'renk': renk, 'boy': None, 'urun': 'dijital',
                            'yalniz_renk': True, 'isim1': g['isim1'], 'isim2': g['isim2'], 'mesaj': g['mesaj']})
        sip['sayfa'] = no[sip['cift']]
        klas = Path('_profil') / renk; klas.mkdir(parents=True, exist_ok=True)
        sd.pod_kaynak(g['cift'], renk, sd.DIJITAL_BOY[sd.dijital_oran(oran)])     # indirme profile girmesin
        pr.enable()
        r = sd._dijital_is((renk, oran, sip, klas, klas.parent))
        pr.disable()
        print('PROFIL_SONUC', renk, oran, r[2].get('durum'), r[2].get('kapilar_gecti'), r[2].get('sure_sn'), flush=True)
    else:
        a = SimpleNamespace(kod=str(kod), kod_ref='profil', boy=anahtar, cikti=str(Path('_profil_wp').resolve()))
        pr.enable()
        rc = surucu.wp_asamasi(a, g)
        pr.disable()
        print('PROFIL_SONUC wp', anahtar, rc, flush=True)
    print('PROFIL_TOPLAM', round(time.time() - t0, 1), 'sn', flush=True)
    for sirala, n in (('cumulative', 45), ('tottime', 30)):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats(sirala).print_stats(n)
        for satir in s.getvalue().splitlines():
            if satir.strip():
                print('PROFIL', sirala[:3], satir, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
