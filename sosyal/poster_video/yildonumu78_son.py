#!/usr/bin/env python3
"""78 yil donumu son kararlar (Serdar, 21 Eki): yalniz rapor dosyalari, uretim yok.
1) GOZ_KONTROLU 12 cift KABUL; 2) ARIES_SAGITTARIUS yeni video (KONTROL_GOZ, tek duzeltme turu) KABUL, YILDONUMU/'deki eski
dosyanin yerine; KONTROL_YD satiri OLCUM_ARIES_SAGITTARIUS.txt degerleriyle; 3) YUKLEME_LISTESI: yildonumu ARIES_SAGITTARIUS satiri
yeni dosyanin ffprobe/boyutuyla, tum satirlara Drive md5 (saglama); satir sayisi degismez.
Kullanim: yildonumu78_son.py <KONTROL_YD.csv> <OZET_YD.txt> <OLCUM.txt> <YUKLEME_LISTESI.csv> <yeni.mp4> <md5_listesi.txt> <cikti_dir>"""
import csv, json, os, re, subprocess, sys
from collections import Counter

KC, OZ, OL, YL, MP4, MD5, OUT = sys.argv[1:8]
os.makedirs(OUT, exist_ok=True)
C = 'ARIES_SAGITTARIUS'
K_GOZ = 'karar 21 Eki: goz kontrolu (KONTROL_GOZ/KONTAK_DOKU) sonrasi KABUL'
K_YENI = 'karar 21 Eki: yeni video (tek duzeltme turu, 2,0 sn +%14,2) KABUL; YILDONUMU/ dosyasinin yerine'
ol = open(OL, encoding='utf-8').read()
yeni = re.search(r'^yeni\s+N (\d+) \((.*?)\): toz % (.*)$', ol, re.M)
toz = dict(re.findall(r'([\d.]+)s ([+-]?[\d.]+)', yeni.group(3)))
ik = re.search(r'ilk kare ([\d.]+) / son kare ([\d.]+) \(taban ([\d.]+)', ol); gr = re.search(r'gorunen 5 sn ([\d.]+)', ol)
ih = re.search(r'murekkep ihlal ([\d.]+)', ol); iz = eval(re.search(r'silme izi (\{.*?\})', ol).group(1), {})   # kendi yazdigimiz dict

rows = list(csv.DictReader(open(KC, encoding='utf-8'))); alan = list(rows[0].keys())
for r in rows:
    if r['cift'] == C:
        r.update({'sonuc': 'FAIL', 'dusen_kapilar': 'toz_2_4sn_10yuzde silme_izi_yok', 'video': f'{C}_yd_video.mp4', 'N': yeni.group(1),
                  'N_turu': '3', **{f'toz_{t}sn_yuzde': toz[t] for t in ('2', '2.5', '3', '3.5', '4')}, 'murekkep_ihlal': ih.group(1),
                  'gorunen_5sn': gr.group(1), 'ilk_kare_fark': ik.group(1), 'son_kare_fark': ik.group(2), 'taban_420': ik.group(3),
                  'iz_parlaklik_farki': iz['parlaklik_farki'], 'iz_doku_std_orani': iz['doku_std_orani'],
                  'iz_sapma8_silinen': iz['sapma8_orani_silinen'], 'iz_sapma8_cevre': iz['sapma8_orani_cevre'],
                  'glif_bos_hal_farki': iz['glif_bos_hal_farki'], 'sonuc_kabul': 'KABUL', 'kalan_kapilar': '',
                  'kabul': K_YENI, 'goz_kontrolu': 'silme_izi_yok: ' + K_GOZ})
    elif r.get('sonuc_kabul') == 'GOZ_KONTROLU':
        r['sonuc_kabul'] = 'KABUL'; r['goz_kontrolu'] = (r['goz_kontrolu'] + '; ' if r['goz_kontrolu'] else '') + K_GOZ
with open(os.path.join(OUT, 'KONTROL_YD.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, alan); w.writeheader(); w.writerows(rows)
sk = Counter(r['sonuc_kabul'] for r in rows)
# YUKLEME_LISTESI
md5 = {}
for l in open(MD5, encoding='utf-8'):
    if l.strip():
        h, yol = l.strip().split(None, 1); md5[yol.strip()] = h
j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', MP4],
                              capture_output=True, text=True, check=True).stdout)
vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
yl = list(csv.DictReader(open(YL, encoding='utf-8'))); n0 = len(yl); ya = list(yl[0].keys()) + (['md5'] if 'md5' not in yl[0] else [])
for r in yl:
    if r['aile'] == 'yildonumu' and r['cift'] == C:
        r.update({'sure_sn': round(float(j['format']['duration']), 3), 'boyut_bayt': os.path.getsize(MP4), 'boyut_mb': round(os.path.getsize(MP4) / 1e6, 2),
                  'olcu': f"{vs['width']}x{vs['height']}", 'kare': int(vs['nb_read_frames']),
                  'ses': any(s['codec_type'] == 'audio' for s in j['streams']), 'kontrol': 'KABUL'})
    elif r['aile'] == 'yildonumu':
        r['kontrol'] = next(x['sonuc_kabul'] for x in rows if x['cift'] == r['cift'])
    r['md5'] = md5.get(r['video_yolu'].split('ILAN_VIDEO_78_20261020/', 1)[1], '')
assert len(yl) == n0 == 234, len(yl)
with open(os.path.join(OUT, 'YUKLEME_LISTESI.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, ya); w.writeheader(); w.writerows(yl)
yr = next(r for r in yl if r['aile'] == 'yildonumu' and r['cift'] == C)
eski = [l for l in open(OZ, encoding='utf-8').read().splitlines() if not l.startswith('kararlarla')]
ozet = [eski[0], f"kararlarla (21 Eki a + b + goz kontrolu + ARIES_SAGITTARIUS yeni video): PASS {sk['PASS']}, KABUL {sk['KABUL']}, "
                 f"FAIL {sk.get('FAIL', 0)}, GOZ_KONTROLU {sk.get('GOZ_KONTROLU', 0)} -> {sk['PASS'] + sk['KABUL']}/78",
        f"{C}: yeni video N {yeni.group(1)}, toz % {' '.join(toz[t] for t in ('2', '2.5', '3', '3.5', '4'))}; "
        f"YUKLEME satiri {yr['boyut_bayt']} bayt, md5 {yr['md5'] or '-'}"] + eski[1:]
open(os.path.join(OUT, 'OZET_YD.txt'), 'w', encoding='utf-8').write('\n'.join(ozet) + '\n')
bos = sum(1 for r in yl if not r['md5'])
print('\n'.join(ozet[:3])); print(f'YUKLEME_LISTESI {len(yl)} satir, md5 eksik {bos}')
sys.exit(0 if sk.get('FAIL', 0) == 0 and sk.get('GOZ_KONTROLU', 0) == 0 and bos == 0 and yr['md5'] else 1)
