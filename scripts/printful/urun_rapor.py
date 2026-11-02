#!/usr/bin/env python3
"""Printful urun taramasi RAPOR.md uretici (API yok; TUM_LISTE.csv + SECILEN25.csv + ham'dan). Kullanim: urun_rapor.py <cikti_klasoru>
Uyarlama notu hesabi: ornament gorunen dairesi 70 mm'de isim buyuk harfi 2.39 mm (STIL3_V3). Daire capi D mm olan urunde ayni duzenle
isim buyuk harfi = 2.39 x D / 70 (hesap). D: A sinifinda baski alani kisa kenari, B sinifinda kisa kenarin %90'i (kenar payi)."""
import csv
import collections
import sys
from pathlib import Path

U = ['US', 'DE', 'GB', 'CA', 'AU']
SECIM_GEREKCE = {
    'A': 'A sinifi (yuvarlak baski alani): hepsi alindi',
    'B': 'B sinifi: Etsy hediye kategorisinde yaygin urun turu (DEGERLENDIRME; olculmus Etsy verisi yok)'}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main(c):
    c = Path(c)
    tum = {r['urun_id']: r for r in csv.DictReader(open(c / 'TUM_LISTE.csv', encoding='utf-8'))}
    sec = list(csv.DictReader(open(c / 'SECILEN25.csv', encoding='utf-8')))
    by = collections.OrderedDict()
    for r in sec:
        by.setdefault(r['urun_id'], []).append(r)
    say = collections.Counter(r['sinif'] for r in tum.values())
    L = ['# Printful urun taramasi: ornament tasarimi hangi urunlere uyarlanir (2 Kas 2026)', '',
         'Kaynak: Printful API (yalniz okuma; GET + POST /v2/shipping-rates fiyat sorgusu). Siparis / urun / magaza kaydi olusturulmadi, Etsy yok.',
         'Kosular: liste https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41465886451 (1142 GET),',
         'kargo https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41469469402 (25 GET + 990 POST /v2/shipping-rates). Ham JSON: ham/.',
         '', '## Kapsam ve yontem', '',
         f'- Kok kategori Home & living ve Accessories: {len(tum)} urun (v1 + v2 katalog). Giyim kokleri (Men\'s, Women\'s, Kids\' clothing, Hats) ve',
         '  giyim sayilan alt kategoriler (Shoes, Socks, Flip flops) haric. Katalogda ayri "takı / jewelry" kategorisi YOK (v1 /categories).',
         '- Sinif kurali (varyant bazinda, urun en uygun varyantinin sinifini alir; olcu v2 placement_dimensions inc, yoksa printfile / dpi):',
         '  - C: nakis (ad / teknik), sarma (ad: mug, tumbler, bottle, pint / wine / rocks / can-shaped glass, can cooler, candle; ya da en/boy > 2.2),',
         '    ortada yarik (aciklama), kisa kenar < 2.0 inc (51 mm: isim 2.38 mm sigmaz).',
         '  - A: yuvarlak kaniti (adda round / circle, aciklamada diameter, die-cut urun adi, varyant boyutu tek olcu) ve kare baski alani.',
         '  - B: kalan kare / dikdortgen.',
         '  - Kanit turu her satirda "gerekce" sutununda. Sekil API\'de dogrudan alan olarak YOK; kanit ad / aciklama / boyut metninden.',
         f'- Sonuc: A {say["A"]}, B {say["B"]}, C {say["C"]} (TUM_LISTE.csv).',
         '- Fiyat: v2 /prices (USD) worldwide (WW) ve north_america (NA); v1 variants.price ayrica. En ucuz = katalog varyant listesindeki varyantlar',
         '  (fiyat yanitinda listede olmayan ek kimlikler 11 urunde var; disarida birakildi).',
         '- Uretim yeri: TUM_LISTE\'de v1 availability_status bolgeleri (URETIM ULKESI DEGIL; onceki olcumde 881 v1 "US" ama cikis LV).',
         '  Kesin cikis ulkesi yalniz secilen 25\'te kargo yanitindan (shipments.departure_country).',
         '- Kargo: urun basina en ucuz (v2 WW) 6 varyant x US, DE, GB, CA, AU x 1 ve 2 adet; en ucuz yontem. Ek urun = 2 adet - 1 adet ucreti (ayni yontem).',
         '  Ornek adres: merkez posta kodu. Gumruk: customs_fees_possible (anlami Printful dokumaninda bulunamadi; bkz. ornament raporu).',
         '', '## Secilen 25 (SECILEN25.csv: tum varyantlar)', '',
         '| urun | sinif | en ucuz USD WW / NA | kargo ilk / ek USD: US | DE | GB | CA | AU | cikis (US / DE / GB) | gumruk (DE GB CA) | kisit | uyarlama |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for pid, rs in by.items():
        t = tum[pid]
        q = [r for r in rs if r.get('US_ilk') and not r['US_ilk'].startswith('sorgulanmadi')]
        ww = [f(r['fiyat_usd_v2_WW']) for r in rs if f(r['fiyat_usd_v2_WW']) is not None]
        na = [f(r['fiyat_usd_v2_NA']) for r in rs if f(r['fiyat_usd_v2_NA']) is not None]
        hucre, cik, gum, kisit = [], {}, set(), set()
        for u in U:
            ilk = [f(r[f'{u}_ilk']) for r in q if f(r[f'{u}_ilk']) is not None]
            ek = [f(r.get(f'{u}_ek')) for r in q if f(r.get(f'{u}_ek')) is not None]
            if ilk:
                i_ = min(ilk); e_ = min(ek) if ek else None
                hucre.append(f'{i_:.2f} / {e_:.2f}' if e_ is not None else f'{i_:.2f} / -')
                cik[u] = ','.join(sorted({r.get(f'{u}_cikis') for r in q if r.get(f'{u}_cikis')}))
                if any('True' in (r.get(f'{u}_gumruk') or '') for r in q):
                    gum.add(u)
            else:
                m = sorted({r[f'{u}_ilk'] for r in q if r[f'{u}_ilk'].startswith('HATA')})
                hucre.append('gonderilmez')
                kisit.add('yalniz ABD' if any('United States only' in x or 'ships to' in x for x in m) else ('ABD disi: ' + (m[0][9:50] if m else '?')))
        # uyarlama: daire capi
        g = t['gerekce']
        import re
        mm = re.search(r'([\d.]+)x([\d.]+) inc', g)
        if mm:
            kisa = min(float(mm.group(1)), float(mm.group(2))) * 25.4
            D = kisa if t['sinif'] == 'A' else kisa * 0.9
            cap = 2.39 * D / 70
            ek_not = ('delik kalkar' if 'Ornament' not in t['ad'] else 'delik / asma noktasi urune gore yeniden olculmeli')
            if t['sinif'] == 'A':
                uy = f'daire {D:.0f} mm, oldugu gibi oturur; {ek_not}; isim harfi yaklasik {cap:.1f} mm (hesap)'
            else:
                uy = f'daire {D:.0f} mm ortada, zemin {"koselere" if "kare" in g else "uzun kenara"} uzar; isim harfi yaklasik {cap:.1f} mm (hesap)'
            if cap < 2.0:
                uy += '; 2 mm alti, yazi kucuk kalir (ornament duzeni 70 mm icin)'
        else:
            uy = 'baski olcusu yok'
        cs = ' / '.join(cik.get(u, '-') for u in ('US', 'DE', 'GB'))
        L.append(f"| {pid} {t['ad'][:34]} | {t['sinif']} | {min(ww) if ww else ''} / {min(na) if na else ''} | " + ' | '.join(hucre) +
                 f" | {cs} | {','.join(sorted(gum & {'DE', 'GB', 'CA'})) or '-'} | {', '.join(sorted(kisit)) or '-'} | {uy} |")
    L += ['', 'Secim gerekcesi: ' + SECIM_GEREKCE['A'] + '; ' + SECIM_GEREKCE['B'] + '.', '',
          '- Kargo hucreleri: sorgulanan varyantlar icinde en ucuz ilk urun / ek urun (USD, Printful API). Tum varyant ve gun bilgisi SECILEN25.csv.',
          '- "gonderilmez": API 400 (ornek "ships to United States only", "Unavailable variant id used").',
          '- Uyarlama notundaki isim harfi boyu HESAPTIR (ornament duzeninin esit olcegi); urun basina tasarim yapilmadi.',
          '', '## A sinifi (tumu)', '']
    for r in tum.values():
        if r['sinif'] == 'A':
            L.append(f"- {r['urun_id']} {r['ad']}: {r['gerekce']}")
    L += ['', '## C sinifi gerekce dagilimi', '']
    cc = collections.Counter(re.sub(r'\(.*', '', r['gerekce']).split(':')[0].strip() for r in tum.values() if r['sinif'] == 'C')
    for k, v in cc.most_common():
        L.append(f'- {k}: {v}')
    (c / 'RAPOR.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('RAPOR', len(by), 'urun', flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
