#!/usr/bin/env python3
"""URUN GORSELI CL (21 Eki 2026): canli ilanlarda stil/renk adlarini dogrular. SALT OKUR: Etsy'ye yalniz GET (6 istek).
CL poster 4570143815 (5 renk), kupa 4598525642 (8 Orchard stili), yil donumu 4595350971 (5 stil).
Envanterdeki property_values degerleri beklenen adlarla karsilastirilir (buyuk/kucuk harf ve bosluk duyarsiz).
Cikti: <out>/ILAN_DOGRULAMA.txt; eksik ad varsa cikis 1. Kota tabani 10 (CLAUDE.md).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, TOKEN_FILE. Kullanim: urun_ilan_dogrula.py OUT_DIR"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_MIN = 10
BEKLENEN = {
    '4570143815': ('poster', ['Midnight Blue', 'Deep Black', 'Pure White', 'Champagne Ivory', 'Warm Parchment']),
    '4598525642': ('kupa', ['Orange Blossom', 'Purple Fig', 'Olive Breeze', 'Pomegranate Bloom', 'Almond Blossom',
                            'Lemon Grove', 'Blue Grape', 'Golden Loquat']),
    '4595350971': ('yil donumu', ['Starlit', 'Timeless', 'First Page', 'Layers', 'Botanical']),
}


def norm(s):
    return ''.join(str(s).lower().split())


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get('ETSY_API_KEY', ''), os.environ.get('ETSY_SHARED_SECRET', '')
    mask(k); mask(s)
    store = TokenStore(os.environ['TOKEN_FILE'], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    sat, ok = [], True
    for lid, (urun, bek) in BEKLENEN.items():
        x = api.get(f'/listings/{lid}') or {}
        if api.remaining is not None and int(api.remaining) < KOTA_MIN:
            raise SystemExit(f'DUR: kota {api.remaining} < {KOTA_MIN}')
        inv = api.get(f'/listings/{lid}/inventory') or {}
        deg = {}
        for p in inv.get('products') or []:
            for pv in p.get('property_values') or []:
                for v in pv.get('values') or []:
                    deg.setdefault(pv.get('property_name'), set()).add(v)
        tum = {norm(v) for vs in deg.values() for v in vs}
        eksik = [b for b in bek if norm(b) not in tum]
        ok &= not eksik
        sat.append(f'{urun} {lid} state={x.get("state")} baslik="{x.get("title", "")[:90]}"')
        for ad, vs in deg.items():
            sat.append(f'  {ad}: {sorted(vs)}')
        sat.append(f'  beklenen {len(bek)}: {"PASS" if not eksik else "FAIL eksik " + str(eksik)}')
    sat.append(f'istek {api.calls}, kota {api.remaining}; SONUC {"PASS" if ok else "FAIL"}')
    (out / 'ILAN_DOGRULAMA.txt').write_text('\n'.join(sat) + '\n', encoding='utf-8')
    print('\n'.join(sat))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
