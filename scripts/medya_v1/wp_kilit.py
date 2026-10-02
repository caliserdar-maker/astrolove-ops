#!/usr/bin/env python3
"""WP BAKIR KILIDI (Serdar 1 Eki 2026: BAKIR Warm Parchment ONAYLANDI, WP PASS; referans e4f65cd / kosu 36848215749).

Renk, kabartma, kontrast, serit onarimi ve dikis dedektoru KILITLI: parametre degismez. Kilitli kaynak = wp_bakir.py
ve wp_katman.py dosyalarinin tamami + wp_ornek.py'deki hat fonksiyonlari ve sabitleri (asagida). Ozetler
wp_kilit.json'da; test_wp_kilit.py her Actions kosusunda dogrular. Degisiklik yalniz Serdar'in yeni karariyla,
wp_kilit.json yeniden yazilarak (python wp_kilit.py --yaz) ve kararin tarihi notla yapilir."""
import hashlib, inspect, json, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
JSON = KOK / 'wp_kilit.json'
DOSYALAR = ('wp_bakir.py', 'wp_katman.py')
ORNEK_FONK = ('etiketle', 'yanyana', 'yanyana_baski', 'sutun_profili', 'koyu_sutun', '_yazi_maskesi',
              'yanyana_dedektor', 'serdar_dikis', 'cift_boy', 'plate_adi', 'serit_uygula', 'plate_serit_onar')
ORNEK_SABIT = ('DUZ_RENK', 'SERDAR_YAN', 'SERDAR_SERIT', 'PLATE_SERITLER', 'PLATE_B_11x14')
EK_KARARLAR = ['Serdar 1 Eki ~15:50: 24x36 plate acik dikey cizgi (x 1937, y 4376-4440) onarimi; serit x 1935-1940, '
               'y 4370-4446 (PLATE_SERITLER), yontem 11x14 ile ayni',
               'Serdar 2 Eki: SECENEK A, sayfa 45-78 ciftleri ikinci plate VINTAGE_B_<boy>.png (cift_boy plate secimi); '
               'kapi ve esikler ayni',
               'Serdar 2 Eki (11x14 ek deneme): 11x14 sayfa 45-78 uc alt kume, cift bazli VINTAGE_B<k>_11x14.png '
               '(PLATE_B_11x14, plate_adi); diger boylar VINTAGE_B_<boy>.png; kapi ve esikler ayni']
BAKIR_SABIT = ('BAKIR_KOYU', 'T0', 'KENAR_PX', 'KOYU_ALT', 'KOYU_SIKISTIR', 'ESIK_DE', 'MIN_ALAN_BAKIR', 'DOLU',
               'DIKIS_DUZLE', 'KABARTMA_SIGMA', 'KABARTMA_ESIK', 'DIKIS_BOY', 'DIKIS_T', 'DIKIS_KOMSU')


def _h(b):
    return hashlib.sha256(b).hexdigest()


def olc():
    sys.path.insert(0, str(KOK))
    import wp_bakir as wb
    import wp_ornek as wo
    v = lambda x: json.loads(json.dumps(x.tolist() if hasattr(x, 'tolist') else x))     # tuple -> liste
    return {'dosya': {d: _h((KOK / d).read_bytes()) for d in DOSYALAR},
            'wp_ornek_fonksiyon': {f: _h(inspect.getsource(getattr(wo, f)).encode()) for f in ORNEK_FONK},
            'wp_ornek_sabit': {s: v(getattr(wo, s)) for s in ORNEK_SABIT},
            'wp_bakir_parametre': {s: v(getattr(wb, s)) for s in BAKIR_SABIT}}


def fark():
    k = json.loads(JSON.read_text())
    o = olc()
    return [f'{b}.{a}' for b in o for a in o[b] if k['ozet'].get(b, {}).get(a) != o[b][a]]


if __name__ == '__main__':
    if '--yaz' in sys.argv:
        JSON.write_text(json.dumps({'karar': 'Serdar 1 Eki 2026: BAKIR Warm Parchment ONAYLANDI (WP PASS)',
                                    'referans': {'commit': 'e4f65cd', 'kosu': 36848215749,
                                                 'cikti': 'TEMP/WP_ORNEK/CANCER_LIBRA/WP_CANCER_LIBRA_11x14_YANYANA.jpg'},
                                    'ek_kararlar': EK_KARARLAR, 'ozet': olc()}, ensure_ascii=False, indent=1) + '\n')
    print('KILIT', 'BOZUK: ' + ', '.join(fark()) if fark() else 'TAMAM')
