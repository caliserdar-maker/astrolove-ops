#!/usr/bin/env python3
"""WP PASS notu (Serdar 1 Eki: BAKIR Warm Parchment ONAYLANDI) -> Drive TEMP/YAYIN_DURUM.md. Satir, ust gunluk
listesinin sonuna ('## ' basligindan once) eklenir; ayni not varsa tekrar yazilmaz. Etsy/musteri YOK."""
import subprocess, sys, tempfile, time
from pathlib import Path

YOL = 'gdrive:ASTROLOVE/TEMP/YAYIN_DURUM.md'
NOT = ('WP PASS: wp_dal=claude/wp-katman-baski-60sk0s, commit={commit} (referans e4f65cd, kosu 36848215749, '
       'TEMP/WP_ORNEK/CANCER_LIBRA/WP_CANCER_LIBRA_11x14_YANYANA.jpg), renk=BAKIR, onay=Serdar 1 Eki. Kod kilitli '
       '(scripts/medya_v1/wp_kilit.json). Siparis: siparis_dosyasi WARM_PARCHMENT POD -> wp_bakir_uret (bu dal); '
       'siparis-baski-v1 merge baski-duzelt regresyonu bittikten sonra.')


def rc(*a):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a], capture_output=True, text=True,
                       timeout=600)
    if r.returncode:
        raise SystemExit(f'rclone {a[:1]}: {r.stderr[-300:]}')
    return r.stdout


def main():
    commit = sys.argv[1][:7]
    eski = rc('cat', YOL)
    if 'WP PASS: wp_dal=claude/wp-katman-baski-60sk0s' in eski:
        print('YAYIN_DURUM: not zaten var, yazilmadi'); return
    satir = f"- {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC | wp-katman -> galeri | " + NOT.format(commit=commit)
    i = eski.find('\n## ')
    yeni = (eski.rstrip('\n') + '\n' + satir + '\n') if i < 0 else (eski[:i].rstrip('\n') + '\n' + satir + '\n' + eski[i:])
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'YAYIN_DURUM.md'
        f.write_text(yeni)
        rc('copyto', str(f), YOL)
    kontrol = rc('cat', YOL)
    assert satir in kontrol and len(kontrol) >= len(eski), 'yazim dogrulanamadi'
    print('YAYIN_DURUM:', satir)


if __name__ == '__main__':
    main()
