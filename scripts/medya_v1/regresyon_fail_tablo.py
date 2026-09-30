#!/usr/bin/env python3
"""Regresyon yeni sonuclarinda FAIL hucreler: cift, renk, kalan kapi, kapinin olculen degeri / esigi (salt okur)."""
import json, sys
from pathlib import Path

DEGER = {
    'olcek': lambda r: f"konum {r['olcek'].get('konum_fark_px')} (<=1) / kenar {r['olcek'].get('kenar_fark_px')} (<=2)"
                       + (f" sebep {r['olcek'].get('sebep')}" if r['olcek'].get('sebep') else ''),
    'mesaj_murekkep': lambda r: f"dE {r['mesaj'].get('dE')} (<=9.2)",
    'sembol': lambda r: 'IoU sol/sag ' + '/'.join(str((r['sembol'].get(y) or {}).get('iou')) for y in ('sol', 'sag')) + ' (>=0.97)',
    'temiz_ara_zemin': lambda r: f"ort {r['temiz_ara'].get('en_ort')} (<=2) / tepe {r['temiz_ara'].get('en_tepe')} (<=6)",
    'kalinti': lambda r: f"ort {r['kalinti'].get('en_ort')} / tepe {r['kalinti'].get('en_tepe')}",
    'leke': lambda r: f"en kotu blok p99 {r['leke'].get('en_kotu_blok_p99')}",
    'isim_kalinti': lambda r: f"{r['isim_kalinti'].get('kalinti_sayisi')} kalinti",
    'isim_kenar': lambda r: f"{r['isim_kenar'].get('kesilen_harf_px')} px kesik",
    'plate_slogan': lambda r: f"glif farkli payi {r.get('plate_slogan')}",
}


def main():
    Y = {}
    for f in sorted(Path(sys.argv[1]).rglob('*.jsonl')):
        for s in f.read_text().splitlines():
            if s.strip():
                x = json.loads(s); Y[(x['cift'], x['renk'], x['boy'])] = x
    satir = ['| cift | renk | boy | kapi | deger |', '|---|---|---|---|---|']
    for k, r in sorted(Y.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if r.get('gecti'):
            continue
        if r.get('durum') != 'URETILDI' or not r.get('kalan'):
            satir.append(f"| {k[0]} | {k[1]} | {k[2]} | {r.get('durum')} | {str(r.get('hata'))[:90]} |")
            continue
        for g in r['kalan']:
            try:
                d = DEGER[g](r) if g in DEGER else '-'
            except Exception as e:                                # noqa: BLE001
                d = f'? {e}'
            satir.append(f"| {k[0]} | {k[1]} | {k[2]} | {g} | {d} |")
    Path('FAIL_TABLO.md').write_text('\n'.join(satir) + '\n')
    print('\n'.join(satir))


if __name__ == '__main__':
    main()
