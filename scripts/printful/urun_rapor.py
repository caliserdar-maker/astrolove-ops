#!/usr/bin/env python3
"""Printful urun taramasi RAPOR.md uretici (API yok; TUM_LISTE.csv + SECILEN25.csv + ham'dan). Kullanim: urun_rapor.py <cikti_klasoru>
Uyarlama notu hesabi: ornament gorunen dairesi 70 mm'de isim buyuk harfi 2.39 mm (STIL3_V3). Daire capi D mm olan urunde ayni duzenle
isim buyuk harfi = 2.39 x D / 70 (hesap). D (temsil varyant = en ucuz uygun varyant): aciklamada fiziksel cap / boyut varsa o; yoksa
varyant boyutu tek olcu ise o; yoksa baski alani kisa kenari (tasma payi dahil olabilir, isaretlenir). B sinifinda D'nin %90'i (kenar payi)."""
import csv
import collections
import re
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
         'TUM_LISTE / SECILEN25 / RAPOR bu ham veriden YEREL yeniden uretildi (API yok; betik scripts/printful/urun_katalog.py tablo / secilen).',
         'Sinif sayilari bu yuzden KOSU_LOG_1 ("A 3, B 144, C 42", ilk kural) ile farkli: kurallar bagimsiz inceleme bulgulariyla duzeltildi.',
         'Ek kosu (urun3, Serdar onayi, tek seferlik): https://github.com/caliserdar-maker/astrolove-ops/actions/runs/41476618387',
         '(64 GET + 30 POST /v2/shipping-rates; log KOSU_LOG_3.txt).',
         '', '## Ek kosu (urun3) sonucu', '',
         '- v2 /prices kalan sayfalari okundu (50 GET). Fiyat kapsami artik tam; yalniz 938 ve 1716 fiyat yanitinda 0/1 (API fiyat vermiyor).',
         '  Degisen en ucuz WW: 2 21.25 -> 20.76, 172 24.25 -> 23.93, 614 32.25 -> 31.95, 1708 48.48 -> 32.95 (NA de 32.95).',
         '- Kargo: en ucuz 6 varyanti degisen secilen urunler 1 ve 2; yeni varyantlar icin 30 POST /v2/shipping-rates.',
         '- 534 Jigsaw Puzzle eklendi (v1 / v2 kategori Collections > New products): B, en ucuz 15.25 USD WW.',
         '- 900 Ceramic Ornament 2-Side baski sablonu: printfile 845 = 954 x 954 px, 300 dpi (80.8 mm). v2 mockup sablonu (Circle.png)',
         '  900 ve 881 icin bayt bayt AYNI (sha256 5fe4a06f...). Sablonda: kesikli guvenli daire r 380 px (64.4 mm), duz kenar r 475 px',
         '  (baski alani kenari). Urun kenari (70 ya da 76 mm) sablonda CIZILI DEGIL. Aciklama: 900 "Circle-shaped diameter 2.99 inc (7.6 cm)",',
         '  881 "2.76 inc (7 cm)". v1 sablon gorselleri (900: 907652, 881: 905495) farkli URL, indirilmedi (yalniz "circle" adli URL alindi).',
         '  v2 / v1 sizes: 900 icin olcu tablosu yok (400 / bos).',
         '- Uretim / cikis ulkesi yalniz secilen 25 icin (kargo yanitindan). Kalan urunlerde yok; v1 bolgeleri uretim ulkesi DEGIL.',
         '- Malzeme: v1 material alani cogu varyantta bos (API); malzeme_v1 sutunu dolu olanlar.',
         '', '## Kapsam ve yontem', '',
         f'- Kok kategori Home & living ve Accessories: {len(tum)} urun (v1 + v2 katalog). Giyim kokleri (Men\'s, Women\'s, Kids\' clothing, Hats) ve',
         '  giyim sayilan alt kategoriler (Shoes, Socks, Flip flops) haric. Katalogda ayri "takı / jewelry" kategorisi YOK (v1 /categories).',
         '- Sinif kurali (varyant bazinda, urun en uygun varyantinin sinifini alir; olcu v2 placement_dimensions inc, yoksa printfile / dpi):',
         '  - C: giyilebilir aksesuar (gaiter, bandana, scrunchie, headband, pet hoodie / sweater), nakis (ad / v2 ya da v1 teknik),',
         '    sarma (ad: mug, tumbler, bottle, pint / wine / rocks / can-shaped glass; ya da en/boy > 2.2), varyant kesim sekli daire degil',
         '    (heart, star, bell, snowflake, stocking, tree, paw, scalloped), ortada yarik (aciklama),',
         '    kisa kenar < 2.0 inc (esik DEGERLENDIRME; 2.0 inc = 51 mm dairede isim harfi 2.39 x 51 / 70 = 1.74 mm, hesap).',
         '  - A: yuvarlak kaniti (varyant / urun adinda round / circle, aciklamada diameter, die-cut urun adi, varyant boyutu tek olcu) ve kare baski alani.',
         '    Kesim sekli daire olmayan varyant kanit almaz (aciklamadaki diameter o varyanta uygulanmaz).',
         '  - Fiziksel boyut: varyant boyutu tek olcu ise o (or. 660 pin 1.25 / 2.25 inc; baski alani 2.62 inc kenar sarma dahil).',
         '  - B: kalan kare / dikdortgen.',
         '  - Kanit turu her satirda "gerekce" sutununda. Sekil API\'de dogrudan alan olarak YOK; kanit ad / aciklama / boyut metninden.',
         f'- Sonuc: A {say["A"]}, B {say["B"]}, C {say["C"]} (TUM_LISTE.csv).',
         '- Fiyat: v2 /prices (USD) worldwide (WW) ve north_america (NA); v1 variants.price ayrica. En ucuz = katalog varyant listesindeki varyantlar',
         '  (fiyat yanitinda listede olmayan ek kimlikler 11 urunde var; disarida birakildi).',
         '- Uretim yeri: TUM_LISTE\'de v1 availability_status bolgeleri (URETIM ULKESI DEGIL; onceki olcumde 881 v1 "US" ama cikis LV).',
         '  Kesin cikis ulkesi yalniz secilen 25\'te kargo yanitindan (shipments.departure_country).',
         '- Kargo: urun basina en ucuz (v2 WW) 6 varyant x US, DE, GB, CA, AU x 1 ve 2 adet; en ucuz yontem. Ek urun = 2 adet - 1 adet ucreti (ayni yontem).',
         '  Ornek adres: merkez posta kodu. Gumruk: customs_fees_possible (anlami Printful dokumaninda bulunamadi; bkz. ornament raporu).',
         '  Kargo hucresi: ilk ucreti en dusuk varyant ve AYNI varyantin ek ucreti.',
         '- Satis kisiti (TUM_LISTE satis_kisiti): aciklamada "US only" (743, 786, 793, 794, 805) ve v2 worldwide urun 404 (635, 716, 743;',
         '  bunlarda WW fiyat yaniti yine geldi, yazildi). uygunluk_v2 yalniz worldwide sorgusu.',
         '', '## Secilen 25 (SECILEN25.csv: tum varyantlar)', '',
         '| urun | sinif | en ucuz USD WW / NA (fiyat kapsami) | temsil varyant USD WW | kargo ilk / ek USD: US | DE | GB | CA | AU | cikis US / DE / GB / CA / AU | gumruk olasi | kisit | uyarlama |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
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
                rr = min((r for r in q if f(r[f'{u}_ilk']) is not None), key=lambda r: (f(r[f'{u}_ilk']), f(r.get(f'{u}_ek')) if f(r.get(f'{u}_ek')) is not None else 9e9))
                i_, e_ = f(rr[f'{u}_ilk']), f(rr.get(f'{u}_ek'))
                hucre.append(f'{i_:.2f} / {e_:.2f}' if e_ is not None else f'{i_:.2f} / -')
                cik[u] = ','.join(sorted({r.get(f'{u}_cikis') for r in q if r.get(f'{u}_cikis')}))
                if any('True' in (r.get(f'{u}_gumruk') or '') for r in q):
                    gum.add(u)
            else:
                m = sorted({r[f'{u}_ilk'] for r in q if r[f'{u}_ilk'].startswith('HATA')})
                hucre.append('gonderilmez')
                kisit.add('kargo: yalniz ABD' if any('United States only' in x or 'ships to' in x for x in m) else ('kargo ABD disi 400: ' + (m[0][9:50].strip() if m else '?')))
        # uyarlama: daire capi (temsil varyant)
        g = t['gerekce']
        mm = re.search(r'([\d.]+)x([\d.]+) inc', g)
        fz = re.search(r'fiziksel kisa ([\d.]+) inc|varyant boyutu ([\d.]+) inc fiziksel', g)
        ao = re.search(r'([\d.]+)\s*(?:″|"|in)', t.get('aciklama_olcu') or '')
        if mm:
            kisa = min(float(mm.group(1)), float(mm.group(2))) * 25.4
            kay = 'baski alani (tasma payi dahil olabilir)'
            if fz and fz.group(2):
                kisa, kay = float(fz.group(2)) * 25.4, 'varyant boyutu'
            if ao and t['sinif'] == 'A' and float(ao.group(1)) * 25.4 < kisa:
                kisa, kay = float(ao.group(1)) * 25.4, f'aciklama "{t["aciklama_olcu"][:30]}"'
            D = kisa if t['sinif'] == 'A' else kisa * 0.9
            cap = 2.39 * D / 70
            ek_not = ('delik kalkar' if 'Ornament' not in t['ad'] else 'delik / asma noktasi urune gore yeniden olculmeli')
            if t['sinif'] == 'A':
                uy = f'varyant {t["temsil_varyant"]}: daire {D:.0f} mm ({kay}), oldugu gibi oturur; {ek_not}; isim harfi yaklasik {cap:.1f} mm (hesap)'
            else:
                uy = f'varyant {t["temsil_varyant"]}: daire {D:.0f} mm ortada ({kay} %90), zemin {"koselere" if " kare " in g else "uzun kenara"} uzar; isim harfi yaklasik {cap:.1f} mm (hesap)'
            if cap < 2.0:
                uy += '; 2 mm alti, yazi kucuk kalir (ornament duzeni 70 mm icin)'
        else:
            uy = 'baski olcusu yok'
        cs = ' / '.join(cik.get(u, '-') for u in U)
        paket = ' (paket fiyati: ' + ', '.join(sorted({r['boyut'] or r['varyant_ad'] for r in rs if re.search(r'\bpieces?\b|\bpcs\b|\bpack of\b|\bset of\b', (r['varyant_ad'] or '') + ' ' + (r['boyut'] or ''), re.I)}))[:60] + ')' \
            if 'puzzle' not in t['ad'].lower() and any(re.search(r'\bpieces?\b|\bpcs\b|\bpack of\b|\bset of\b', (r['varyant_ad'] or '') + ' ' + (r['boyut'] or ''), re.I) for r in rs) else ''
        kisit |= set(x for x in (t.get('satis_kisiti') or '').split(';') if x)
        L.append(f"| {pid} {t['ad'][:34]}{paket} | {t['sinif']} | {t['en_ucuz_usd_v2_WW']} / {t['en_ucuz_usd_v2_NA']} ({t['fiyat_kapsam_WW']}) | {t['temsil_usd_v2_WW'] or '-'} | " + ' | '.join(hucre) +
                 f" | {cs} | {','.join(u for u in U if u in gum) or '-'} | {', '.join(sorted(kisit)) or '-'} | {uy} |")
    L += ['', 'Secim gerekcesi: ' + SECIM_GEREKCE['A'] + '; ' + SECIM_GEREKCE['B'] + '.', '',
          '- Kargo hucreleri: sorgulanan varyantlar icinde ilk ucreti en dusuk varyantin ilk / ek ucreti (USD, Printful API). Tum varyant ve gun bilgisi SECILEN25.csv.',
          '- Fiyat kapsami: okunan / toplam varyant (v2 prices paging). Kapsam eksikse en ucuz WW degeri eksik okumadan.',
          '- B secimi (16 urun) DEGERLENDIRMEDIR; urun basina olculmus Etsy talep verisi yok.',
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
