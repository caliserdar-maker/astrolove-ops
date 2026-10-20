#!/usr/bin/env python3
"""78 ilan videosu raporu: satir/<CIFT>.json -> KONTROL.csv, OZET.txt (tutmayanlar), kontak sayfalari (her video 3 sn + son kare).
Kullanim: ilan78_rapor.py <satir_dir> <kare_dir> <cikti_dir>"""
import csv, glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont

SAT, KARE, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
Z = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
TUM = sorted('_'.join(sorted((a, b))) for i, a in enumerate(Z) for b in Z[i:])
R = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(SAT, '*.json'))}


def font(n):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', n)
    except OSError:
        return ImageFont.load_default()


KARAR = {'toz': 'yalniz 4,0 sn yogunluk sapmasi (Serdar 20 Eki, karar a)',
         'kod': 'kupa ilk/son kare crf 17 kodlama farki <= 0,008 (Serdar 20 Eki, karar b)'}


def kabul(r, d):
    """dusen kapilardan kararla kabul edilenler: [(kapi, karar)]; kalan dusenler ayri"""
    k, p = r['kupa'], r['poster']; ok, kal = [], []
    for x in d:
        tz = [p['toz_2_4sn'][t]['fark_yuzde'] for t in ('2', '2.5', '3', '3.5')]
        if x == 'poster.toz_2_4sn_10yuzde' and all(abs(v) <= 10 for v in tz):
            ok.append((x, KARAR['toz']))
        elif x == 'kupa.ilk_kare_kapak' and k['ilk_kare_fark'] - k['ilk_kare_kabul_esigi'] <= 0.008 + 1e-9:
            ok.append((x, KARAR['kod']))
        elif x == 'kupa.son_kare_kapak' and k['son_kare_fark'] - (k['taban_420'] + 0.2) <= 0.008 + 1e-9:
            ok.append((x, KARAR['kod']))
        else:
            kal.append(x)
    return ok, kal


sutun = ['cift', 'sonuc', 'sonuc_kabul', 'kabul', 'kalan_kapilar', 'dusen_kapilar', 'kupa_video', 'kupa_kapak', 'kupa_ilk_kare_fark', 'kupa_ilk_kare_kabul_esigi',
         'kupa_ilk_taban_02_icinde', 'kupa_son_kare_fark', 'kupa_taban_420', 'kupa_kapak_katman_fark', 'kupa_gorunen_5sn', 'kupa_olcu_kare_ses',
         'poster_video', 'poster_kapak', 'poster_kapak_klasoru', 'poster_N', 'poster_bolge_px', 'toz_2sn_yuzde', 'toz_2.5sn_yuzde',
         'toz_3sn_yuzde', 'toz_3.5sn_yuzde', 'toz_4sn_yuzde', 'murekkep_ihlal', 'poster_ilk_kare_fark', 'poster_son_kare_fark',
         'poster_taban_420', 'poster_gorunen_5sn', 'poster_olcu_kare_ses', 'ayni_burc', 'glif_benzerlik', 'glif_sonsuz_ok']
satirlar, eksik, dus, kalan = [], [], {}, {}
for c in TUM:
    r = R.get(c)
    if not r:
        eksik.append(c); satirlar.append({'cift': c, 'sonuc': 'EKSIK'}); continue
    k, p = r['kupa'], r['poster']
    d = [f'kupa.{a}' for a, v in k['kapi'].items() if not v] + [f'poster.{a}' for a, v in p['kapi'].items() if not v]
    if d:
        dus[c] = d
    kb, kal = kabul(r, d)
    if kal:
        kalan[c] = kal
    pr = lambda x: f"{x['probe']['olcu']}/{x['probe']['kare']}/{'ses' if x['probe']['ses_akisi'] else 'sessiz'}"
    satirlar.append({'cift': c, 'sonuc': r['sonuc'], 'sonuc_kabul': 'PASS' if not d else ('KABUL' if not kal else 'FAIL'),
                     'kabul': '; '.join(f'{x}: {y}' for x, y in kb), 'kalan_kapilar': ' '.join(kal), 'dusen_kapilar': ' '.join(d), 'kupa_video': k['video'], 'kupa_kapak': k['kapak'],
                     'kupa_ilk_kare_fark': k['ilk_kare_fark'], 'kupa_ilk_kare_kabul_esigi': k['ilk_kare_kabul_esigi'],
                     'kupa_ilk_taban_02_icinde': k['ilk_kare_taban_02_icinde'], 'kupa_son_kare_fark': k['son_kare_fark'],
                     'kupa_taban_420': k['taban_420'], 'kupa_kapak_katman_fark': k['kapak_katman_kupa_bolgesi_fark'],
                     'kupa_gorunen_5sn': k['gorunen_5sn'], 'kupa_olcu_kare_ses': pr(k), 'poster_video': p['video'], 'poster_kapak': p['kapak'],
                     'poster_kapak_klasoru': p['kapak_klasoru'], 'poster_N': p['N'], 'poster_bolge_px': p['bolge_px'],
                     **{f'toz_{t}sn_yuzde': v['fark_yuzde'] for t, v in p['toz_2_4sn'].items()}, 'murekkep_ihlal': p['ihlal_en_buyuk'],
                     'poster_ilk_kare_fark': p['ilk_kare_fark'], 'poster_son_kare_fark': p['son_kare_fark'], 'poster_taban_420': p['taban_420'],
                     'poster_gorunen_5sn': p['gorunen_5sn'], 'poster_olcu_kare_ses': pr(p), 'ayni_burc': p['ayni_burc'],
                     'glif_benzerlik': p['glif']['benzerlik'], 'glif_sonsuz_ok': p['kapi']['glif_sonsuz']})
with open(os.path.join(OUT, 'KONTROL.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, sutun); w.writeheader(); w.writerows(satirlar)
gec = sum(1 for s in satirlar if s['sonuc'] == 'PASS')
liste = lambda anahtar: [c for c, d in dus.items() if any(anahtar in x for x in d)]
kab = sum(1 for s in satirlar if s.get('sonuc_kabul') == 'KABUL')
oz = [f'PASS {gec}/78, FAIL {len(dus)}, EKSIK {len(eksik)}',
      f'kararlarla (Serdar 20 Eki a + b): PASS {gec} + KABUL {kab} = {gec + kab}/78; kalan FAIL {len(kalan)}, EKSIK {len(eksik)}',
      f'kalan FAIL (kabul disi): ' + ('; '.join(f'{c}: {" ".join(d)}' for c, d in kalan.items()) or '-'),
      f'eksik: {" ".join(eksik)}',
      f'toz 2-4 sn +-%10 tutmayan: {" ".join(liste("toz_2_4sn")) or "-"}',
      f'kupa ilk kare kabul esigini asan: {" ".join(liste("kupa.ilk_kare_kapak")) or "-"}',
      f'glif/sonsuz: {" ".join(liste("glif_sonsuz")) or "-"}',
      f'diger: ' + '; '.join(f'{c}: {" ".join(x for x in d if "toz_2_4sn" not in x and "kupa.ilk_kare" not in x and "glif" not in x)}'
                             for c, d in dus.items() if any("toz_2_4sn" not in x and "kupa.ilk_kare" not in x and "glif" not in x for x in d))]
open(os.path.join(OUT, 'OZET.txt'), 'w').write('\n'.join(oz) + '\n')
print('\n'.join(oz))
# kontak: sayfa basina 13 cift; satir = ad + 3 sn + son kare
for tur in ('kupa', 'poster'):
    cs = [c for c in TUM if os.path.exists(os.path.join(KARE, f'{c}_{tur}_3sn.jpg'))]
    for s in range(0, len(cs), 13):
        sec = cs[s:s + 13]
        im0 = Image.open(os.path.join(KARE, f'{sec[0]}_{tur}_3sn.jpg')); tw, th = (im0.width // 2, im0.height // 2)
        K = Image.new('RGB', (300 + 2 * (tw + 8), 34 + len(sec) * (th + 6)), (245, 245, 245)); dr = ImageDraw.Draw(K)
        dr.text((300, 6), '3 sn', fill=(0, 0, 0), font=font(20)); dr.text((300 + tw + 8, 6), 'son kare', fill=(0, 0, 0), font=font(20))
        for j, c in enumerate(sec):
            y = 34 + j * (th + 6)
            dr.text((8, y + th // 2 - 22), c, fill=(0, 0, 0), font=font(18))
            dr.text((8, y + th // 2 + 2), R[c]['sonuc'] if c in R else '', fill=(0, 120, 0) if R.get(c, {}).get('sonuc') == 'PASS' else (180, 0, 0), font=font(18))
            for i, ek in enumerate(('3sn', 'son')):
                K.paste(Image.open(os.path.join(KARE, f'{c}_{tur}_{ek}.jpg')).resize((tw, th), Image.LANCZOS), (300 + i * (tw + 8), y))
        K.save(os.path.join(OUT, f'KONTAK_{tur.upper()}_{s // 13 + 1}.jpg'), quality=88)
sys.exit(0 if gec + kab == 78 else 1)
