#!/usr/bin/env python3
"""77 cift galerisi: WP (Warm Parchment) EJ baskisi TUM kapilardan gecmezse tani (Serdar 28 Eyl, WP plani 4. madde).
KAPI_RAPORU.json'dan basarisiz kapilar + olcumler (esiklerle) -> WP_TANI.md; karsilastirma gorseli:
  ust satir: WP baskisi | ayni ciftin MB EJ baskisi (tam poster, kucultulmus)
  alt satir: basarisiz kapinin bolgesi (sol/sag sembol kutusu, temiz ara zemin blogu), WP ve MB yan yana, 2x
Koordinatlar KAPI_RAPORU'nda 2400 birimde; baskiya olcek.k ile tasinir.
Kullanim: galeri77_wptani.py CIFT KAPI_RAPORU.json WP_BASKI.jpg MB_BASKI.jpg KOD_DALI CIKIS_DIR
"""
import json
import os
import sys
import time

from PIL import Image, ImageDraw, ImageFont

C, KAPI, WP, MB, KOD, OUT = sys.argv[1:7]
os.makedirs(OUT, exist_ok=True)
r = json.load(open(KAPI))
k = float((r.get('olcek') or {}).get('k') or 1.3779)
kap = r.get('kapilar') or {}
kalan = [a for a, v in kap.items() if v is False]
satir = [f'# WP_TANI {C} ({time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())})', '',
         f'- kod: {KOD}', f'- durum: {r.get("durum")} | kapilar_gecti: {r.get("kapilar_gecti")}',
         f'- basarisiz kapilar: {", ".join(kalan) or "-"}', f'- tum kapilar: {json.dumps(kap, ensure_ascii=False)}', '']
bolgeler = []                                                   # (ad, (x0,y0,x1,y1) baski px)
t = r.get('temiz_ara_kapisi') or {}
if t.get('gecti') is False:
    satir += ['## temiz_ara_zemin', f'- en_ort {t.get("en_ort")} (esik {t.get("esik", {}).get("ort")}) | en_tepe {t.get("en_tepe")} '
              f'(esik {t.get("esik", {}).get("tepe")}) | kotu blok {t.get("kotu_blok")}/{t.get("blok")}']
    for o in t.get('ornek', []):
        satir.append(f'- blok x {o.get("x")} y {o.get("y")} (2400 birim): ort {o.get("ort")} tepe {o.get("tepe")} px {o.get("px")}')
        x, y = o['x'] * k, o['y'] * k
        bolgeler.append((f'temiz_ara x{o["x"]} y{o["y"]}', (x - 120, y - 120, x + 150, y + 150)))
    satir.append('')
s = r.get('sembol_kapisi') or {}
if s.get('gecti') is False:
    satir += ['## sembol', f'- esik: {json.dumps(s.get("esik"), ensure_ascii=False)}']
    for yan in ('sol', 'sag'):
        v = s.get(yan) or {}
        satir.append(f'- {yan}: iou {v.get("iou")} fark {v.get("fark")} dx {v.get("dx")} dy {v.get("dy")} murekkep {v.get("murekkep_px")} '
                     f'| {"GECTI" if v.get("gecti") else "KALDI"}')
        if v.get('gecti') is False and v.get('kaynak_kutu'):
            x0, y0, x1, y1 = (c * k for c in v['kaynak_kutu'])
            bolgeler.append((f'sembol {yan} iou {v.get("iou")}', (x0 - 30, y0 - 30, x1 + 30, y1 + 30)))
    satir.append('')
o = r.get('olcek_kapisi') or {}
if o.get('gecti') is False:
    satir += ['## olcek', f'- konum_fark_px {o.get("konum_fark_px")} (esik {o.get("esik", {}).get("konum")}) | kenar_fark_px '
              f'{o.get("kenar_fark_px")} (esik {o.get("esik", {}).get("harf_kenari")})',
              f'- farklar (2400 px): {json.dumps(o.get("fark"), ensure_ascii=False)}', f'- olcum: {o.get("olcum")}', '']
for ad in kalan:
    if ad not in ('temiz_ara_zemin', 'sembol', 'olcek'):
        d = r.get(f'{ad}_kapisi') or r.get(ad) or {}
        satir += [f'## {ad}', f'- {json.dumps(d, ensure_ascii=False)[:600]}', '']

W, M = Image.open(WP).convert('RGB'), Image.open(MB).convert('RGB')
PW = 700; PH = round(PW * W.height / W.width)
satir_h = [PH + 40] + [420] * len(bolgeler)
out = Image.new('RGB', (2 * PW + 60, sum(satir_h) + 20), (245, 243, 238))
d = ImageDraw.Draw(out)
try:
    F = ImageFont.truetype(os.path.join(os.environ.get('FD', 'fonts'), 'Montserrat[wght].ttf'), 22)
except OSError:
    F = ImageFont.load_default()
out.paste(W.resize((PW, PH), Image.LANCZOS), (20, 40)); out.paste(M.resize((PW, PH), Image.LANCZOS), (PW + 40, 40))
d.text((20, 8), f'{C} WP baskisi ({KOD})', font=F, fill=(20, 20, 20)); d.text((PW + 40, 8), 'MB EJ baskisi (referans)', font=F, fill=(20, 20, 20))
y = PH + 60
for ad, kutu in bolgeler:
    kutu = tuple(int(round(v)) for v in kutu)
    for i, im in enumerate((W, M)):
        cr = im.crop(kutu); s_ = min((PW - 10) / cr.width, 370 / cr.height)
        out.paste(cr.resize((round(cr.width * s_), round(cr.height * s_)), Image.LANCZOS), (20 + i * (PW + 20), y + 30))
    d.text((20, y), f'{ad}: WP | MB (baski px {kutu})', font=F, fill=(160, 30, 30))
    y += 420
gor = f'WP_TANI_{C}.jpg'
out.save(os.path.join(OUT, gor), quality=88)
satir += ['## karsilastirma', f'- {gor}: ust WP | MB tam poster; alt basarisiz kapi bolgeleri (WP | MB)']
open(os.path.join(OUT, 'WP_TANI.md'), 'w').write('\n'.join(satir) + '\n')
print(f'WP_TANI: {C} | basarisiz {", ".join(kalan) or "-"} | {len(bolgeler)} bolge')
