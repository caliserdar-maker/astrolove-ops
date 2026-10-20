#!/usr/bin/env python3
"""78 yil donumu ilan videosu raporu: satir/<CIFT>.json -> KONTROL_YD.csv, OZET_YD.txt, KONTAK_YD_n.jpg (3 sn + son kare);
YUKLEME_LISTESI.csv'ye 78 yildonumu satiri (varsa eski yildonumu satirlari cikarilir). listing_id: Drive ETSY_ILK_GORSEL
ILANLAR.csv'de basliginda 'Anniversary' gecen ve iki burc adi ayiklanan ilanlar (cift basina tam 1 ilan yoksa bos + not).
Kullanim: yildonumu78_rapor.py <satir_dir> <kare_dir> <video_dir> <ILANLAR.csv> <YUKLEME_LISTESI.csv> <cikti_dir>"""
import csv, glob, json, os, re, subprocess, sys
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

SAT, KARE, VID, ILN, YL, OUT = sys.argv[1:7]
os.makedirs(OUT, exist_ok=True)
Z = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
TUM = sorted('_'.join(sorted((a, b))) for i, a in enumerate(Z) for b in Z[i:])
R = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(SAT, '*.json'))}


def font(n):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', n)
    except OSError:
        return ImageFont.load_default()


# listing_id eslemesi
lid, lnot = defaultdict(list), ''
for r in csv.DictReader(open(ILN, encoding='utf-8-sig')):
    b = r.get('baslik', '')
    if 'anniversary' not in b.lower():
        continue
    bul = [z for z in Z if re.search(rf'\b{z}\b', b.upper())]
    if len(bul) == 1 and re.search(rf'\b{bul[0]}\b.*\b{bul[0]}\b', b.upper()):
        bul = bul * 2
    if len(bul) == 2:
        lid['_'.join(sorted(bul))].append(r['listing_id'])
# poster ilanlarinin basliginda da 'anniversary' gecebilir: diger ailelerin (YUKLEME_LISTESI kupa/poster) listing_id'leri cikarilir
diger = {r['listing_id'] for r in csv.DictReader(open(YL, encoding='utf-8')) if r.get('aile') != 'yildonumu'} if os.path.exists(YL) else set()
lid = defaultdict(list, {c: [x for x in v if x not in diger] for c, v in lid.items()})
coklu = {c: v for c, v in lid.items() if len(v) > 1}
def kabul(r, d):
    """Serdar kararlari (21 Eki): toz 2-4 sn sapmasi <= %13,2 KABUL (a); silme izi -> goz kontrolu (b, KONTROL_GOZ)"""
    ok, goz, kal = [], [], []
    for x in d:
        if x == 'toz_2_4sn_10yuzde' and max(abs(v['fark_yuzde']) for v in r['toz_2_4sn'].values()) <= 13.2 + 1e-9:
            ok.append('toz_2_4sn_10yuzde: karar a (21 Eki) sapma <= %13,2')
        elif x == 'silme_izi_yok':
            goz.append('silme_izi_yok: karar b (21 Eki) goz kontrolu KONTROL_GOZ/KONTAK_DOKU')
        else:
            kal.append(x)
    return ok, goz, kal


sutun = ['cift', 'sonuc', 'sonuc_kabul', 'kabul', 'goz_kontrolu', 'kalan_kapilar', 'dusen_kapilar', 'video', 'kapak', 'N', 'N_turu', 'bolge_px', 'toz_2sn_yuzde', 'toz_2.5sn_yuzde', 'toz_3sn_yuzde',
         'toz_3.5sn_yuzde', 'toz_4sn_yuzde', 'murekkep_ihlal', 'gorunen_5sn', 'ilk_kare_fark', 'son_kare_fark', 'taban_420',
         'sembol_bolgesi_4_97sn_fark', 'sembol_bolgesi_son_kare_fark', 'iz_parlaklik_farki', 'iz_doku_std_orani', 'iz_sapma8_silinen',
         'iz_sapma8_cevre', 'glif_bos_hal_farki', 'murekkep_rengi', 'ayni_burc', 'glif_benzerlik', 'glif_sol', 'glif_sag', 'olcu_kare_ses']
satirlar, eksik, dus = [], [], {}
for c in TUM:
    r = R.get(c)
    if not r:
        eksik.append(c); satirlar.append({'cift': c, 'sonuc': 'EKSIK'}); continue
    d = [k for k, v in r['kapi'].items() if not v]
    if d:
        dus[c] = d
    iz, t4, p = r['silme_izi'], r['toz_2_4sn'], r['probe']
    kb, gz, kl = kabul(r, d)
    satirlar.append({'cift': c, 'sonuc': r['sonuc'], 'sonuc_kabul': 'PASS' if not d else ('FAIL' if kl else ('GOZ_KONTROLU' if gz else 'KABUL')),
                     'kabul': '; '.join(kb), 'goz_kontrolu': '; '.join(gz), 'kalan_kapilar': ' '.join(kl), 'dusen_kapilar': ' '.join(d), 'video': r['video'], 'kapak': r['kapak'], 'N': r['N'],
                     'N_turu': len(r['N_turlari']), 'bolge_px': r['bolge_px'], **{f'toz_{t}sn_yuzde': v['fark_yuzde'] for t, v in t4.items()},
                     'murekkep_ihlal': r['ihlal_en_buyuk'], 'gorunen_5sn': r['gorunen_5sn'], 'ilk_kare_fark': r['ilk_kare_fark'],
                     'son_kare_fark': r['son_kare_fark'], 'taban_420': r['taban_420'], 'sembol_bolgesi_4_97sn_fark': r['sembol_bolgesi_4_97sn_fark'],
                     'sembol_bolgesi_son_kare_fark': r['sembol_bolgesi_son_kare_fark'], 'iz_parlaklik_farki': iz['parlaklik_farki'],
                     'iz_doku_std_orani': iz['doku_std_orani'], 'iz_sapma8_silinen': iz['sapma8_orani_silinen'],
                     'iz_sapma8_cevre': iz['sapma8_orani_cevre'], 'glif_bos_hal_farki': iz['glif_bos_hal_farki'],
                     'murekkep_rengi': ' '.join(str(int(x)) for x in r['glif']['murekkep_rengi']), 'ayni_burc': r['ayni_burc'],
                     'glif_benzerlik': r['glif']['benzerlik'], 'glif_sol': r['glif']['sign_a'], 'glif_sag': r['glif']['sign_b'],
                     'olcu_kare_ses': f"{p['olcu']}/{p['kare']}/{'ses' if p['ses_akisi'] else 'sessiz'}"})
with open(os.path.join(OUT, 'KONTROL_YD.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, sutun); w.writeheader(); w.writerows(satirlar)
gec = sum(1 for s in satirlar if s['sonuc'] == 'PASS')
liste = lambda k: [c for c, d in dus.items() if k in d]
ayni = [s for s in satirlar if s.get('ayni_burc') is True]
from collections import Counter as _C
_sk = _C(s.get('sonuc_kabul', 'EKSIK') for s in satirlar)
oz = [f'YIL DONUMU: PASS {gec}/78, FAIL {len(dus)}, EKSIK {len(eksik)}',
      f'kararlarla (21 Eki a + b): PASS {_sk["PASS"]}, KABUL {_sk["KABUL"]}, GOZ_KONTROLU {_sk["GOZ_KONTROLU"]}, FAIL {_sk["FAIL"]}, EKSIK {_sk["EKSIK"]}; '
      f'FAIL: {" ".join(s["cift"] + " (" + s["kalan_kapilar"] + ")" for s in satirlar if s.get("sonuc_kabul") == "FAIL") or "-"}',
      f'eksik: {" ".join(eksik) or "-"}',
      f'toz 2-4 sn +-%10 tutmayan (duzeltme turundan sonra; Serdar karar verir): ' +
      ('; '.join(f'{c} {[s["toz_" + t + "sn_yuzde"] for t in ("2", "2.5", "3", "3.5", "4")]}' for c in liste('toz_2_4sn_10yuzde')
                 for s in satirlar if s['cift'] == c) or '-'),
      f'diger dusen: ' + ('; '.join(f'{c}: {" ".join(x for x in d if x != "toz_2_4sn_10yuzde")}' for c, d in dus.items()
                                    if any(x != 'toz_2_4sn_10yuzde' for x in d)) or '-'),
      f'ayni burclu {len(ayni)} cift, glif kapisi: ' + ' '.join(f'{s["cift"]}={s["glif_benzerlik"]}' for s in ayni),
      f'duzeltme turu kullanilan: {sum(1 for s in satirlar if s.get("N_turu") == 2)}; N araligi '
      f'{min((s["N"] for s in satirlar if "N" in s), default=0)}-{max((s["N"] for s in satirlar if "N" in s), default=0)}',
      f'listing_id eslesen: {sum(1 for c in TUM if len(lid.get(c, [])) == 1)}/78; coklu: {coklu or "-"}']
# yukleme listesi: yildonumu satirlari (ffprobe)
eski = list(csv.DictReader(open(YL, encoding='utf-8'))) if os.path.exists(YL) else []
alan = list(eski[0].keys()) if eski else ['aile', 'cift', 'listing_id', 'video_yolu', 'sure_sn', 'boyut_bayt', 'boyut_mb', 'olcu', 'kare', 'ses', 'kontrol']
yeni = []
for c in TUM:
    f = os.path.join(VID, f'{c}_yd_video.mp4')
    if not os.path.exists(f):
        continue
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', f],
                                  capture_output=True, text=True, check=True).stdout)
    vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    yeni.append({'aile': 'yildonumu', 'cift': c, 'listing_id': lid[c][0] if len(lid.get(c, [])) == 1 else '',
                 'video_yolu': f'ASTROLOVE/TEMP/ILAN_VIDEO_78_20261020/YILDONUMU/{os.path.basename(f)}',
                 'sure_sn': round(float(j['format']['duration']), 3), 'boyut_bayt': os.path.getsize(f),
                 'boyut_mb': round(os.path.getsize(f) / 1e6, 2), 'olcu': f"{vs['width']}x{vs['height']}", 'kare': int(vs['nb_read_frames']),
                 'ses': any(s['codec_type'] == 'audio' for s in j['streams']), 'kontrol': R[c]['sonuc'] if c in R else 'EKSIK'})
tum_y = [r for r in eski if r.get('aile') != 'yildonumu'] + yeni
with open(os.path.join(OUT, 'YUKLEME_LISTESI.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, alan); w.writeheader(); w.writerows(tum_y)
oz.append(f'YUKLEME_LISTESI: {len(tum_y)} satir (kupa {sum(r["aile"] == "kupa" for r in tum_y)}, poster '
          f'{sum(r["aile"] == "poster" for r in tum_y)}, yildonumu {len(yeni)}); yildonumu sure '
          f'{min((r["sure_sn"] for r in yeni), default=0)}-{max((r["sure_sn"] for r in yeni), default=0)} sn, '
          f'{sum(r["boyut_bayt"] for r in yeni) / 1e6:.1f} MB')
open(os.path.join(OUT, 'OZET_YD.txt'), 'w').write('\n'.join(oz) + '\n')
print('\n'.join(oz))
# kontak: sayfa basina 13 cift; satir = ad + 3 sn + son kare
cs = [c for c in TUM if os.path.exists(os.path.join(KARE, f'{c}_yd_3sn.jpg'))]
for s in range(0, len(cs), 13):
    sec = cs[s:s + 13]; tw = th = 270
    K = Image.new('RGB', (300 + 2 * (tw + 8), 34 + len(sec) * (th + 6)), (245, 245, 245)); dr = ImageDraw.Draw(K)
    dr.text((300, 6), '3 sn', fill=(0, 0, 0), font=font(20)); dr.text((300 + tw + 8, 6), 'son kare', fill=(0, 0, 0), font=font(20))
    for j, c in enumerate(sec):
        y = 34 + j * (th + 6)
        dr.text((8, y + th // 2 - 22), c, fill=(0, 0, 0), font=font(18))
        ok = R.get(c, {}).get('sonuc') == 'PASS'
        dr.text((8, y + th // 2 + 2), R.get(c, {}).get('sonuc', ''), fill=(0, 120, 0) if ok else (180, 0, 0), font=font(18))
        for i, ek in enumerate(('3sn', 'son')):
            K.paste(Image.open(os.path.join(KARE, f'{c}_yd_{ek}.jpg')).resize((tw, th), Image.LANCZOS), (300 + i * (tw + 8), y))
    K.save(os.path.join(OUT, f'KONTAK_YD_{s // 13 + 1}.jpg'), quality=88)
sys.exit(0 if gec == 78 else 1)
