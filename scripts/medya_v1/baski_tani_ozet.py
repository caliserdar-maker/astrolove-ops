#!/usr/bin/env python3
"""baski_tani.py ciktilarini tek tabloya toplar: TABLO.md + TABLO.json (cift x renk x boy x kapi)."""
import json, sys
from pathlib import Path

KAPILAR = ('kalinti', 'temiz_ara_zemin', 'sembol', 'olcek', 'leke', 'boy_siniri',
           'font_kapsami', 'mesaj_murekkep')
KISA = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'PURE_WHITE': 'PW',
        'CHAMPAGNE_IVORY': 'CI', 'WARM_PARCHMENT': 'WP'}


def pf(v):
    return 'PASS' if v is True else ('FAIL' if v is False else '-')


def main(dizin):
    d = Path(dizin)
    satirlar = []
    for f in sorted(d.glob('TANI_*.json')):
        satirlar += json.loads(f.read_text())
    bas = ['cift', 'renk', 'boy', 'durum', *KAPILAR, 'olcek eski (konum/kenar)',
           'olcek yeni (konum/kenar)', 'tag', 'onceki BASKI']
    out = ['| ' + ' | '.join(bas) + ' |', '|' + '---|' * len(bas)]
    for s in satirlar:
        k = s.get('kapilar') or {}
        e, y = s.get('olcek_eski') or {}, s.get('olcek_yeni') or {}
        durum = 'SISTEM HATASI' if s.get('durum') in ('SISTEM HATASI', 'HATA') else \
            ('PASS' if s.get('kapilar_gecti') else 'FAIL')
        ty = s.get('tag_yedek') or {}
        tag = 'yedek' if ty.get('kullanildi') else ('plate' if s.get('durum') == 'URETILDI' else '?')
        o = s.get('onceki') or {}
        onc = ('ayni' if o.get('bayt_ayni') else ('piksel ayni' if o.get('piksel_ayni') else
               (f"{o.get('fark_px')} px farkli" if 'fark_px' in o else ('yok' if o.get('yok') or not o else 'hata'))))
        out.append('| ' + ' | '.join(str(v) for v in [
            s['cift'], KISA.get(s['renk'], s['renk']), s['boy'], durum, *[pf(k.get(a)) for a in KAPILAR],
            f"{pf(e.get('gecti'))} {e.get('konum_fark_px')}/{e.get('kenar_fark_px')}",
            f"{pf(y.get('gecti'))} {y.get('konum_fark_px')}/{y.get('kenar_fark_px')}", tag, onc]) + ' |')
    (d / 'TABLO.md').write_text('\n'.join(out) + '\n')
    (d / 'TABLO.json').write_text(json.dumps(satirlar, ensure_ascii=False, indent=1, default=str))
    print('\n'.join(out))
    wp = [(s['cift'], s['renk'], s['boy'], (s.get('tag_tanisi') or {}))
          for s in satirlar if s['renk'] != 'MIDNIGHT_BLUE']
    for c, r, b, t in wp:
        print(f"TAG {c} {KISA[r]} {b}: plate_tag_var={t.get('plate_olcum_tag_var')} "
              f"alt_bant={[(x['bant'], x['yukseklik'], x['uzanim'], x['kabul']) for x in t.get('alt_bantlar', [])][:4]} "
              f"yerel={t.get('yerel_kontrast_tag')} kutu_fark={t.get('slogan_kutusu_fark')} "
              f"esik_ustu={t.get('slogan_kutusu_esik_ustu')} zemin={t.get('bos_zemin_fark')}")


if __name__ == '__main__':
    main(sys.argv[1])
