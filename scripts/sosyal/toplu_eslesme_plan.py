#!/usr/bin/env python3
"""Toplu video degistirme icin KURU eslesme plani (uuid ile; Metricool'a erisim YOK, yalniz CSV). Serdar 15 Eki 2026.

PUT gonderiye yeni id verdigi icin (15 Eki olcumu) eslesme anahtari uuid'dir; id yalniz bilgi icin yazilir ve
uygulama aninda bul() ile uuid'den yeniden okunur. Cift adi plandan (tarih_saat) alinir: ayni burclu ciftlerde metin
ayristiricisi '?' verir.
Girdi : BEKLEYEN_VIDEO.csv (sosyal-bekleyen-video-oku; birden fazla verilirse sonraki ayni uuid'yi gunceller),
        PLAN_5_PLATFORM.csv
Cikti : ESLESME_PLANI.csv (sira, saat, platform, uuid, id_simdi, cift, video_dosya, mevcut_video_url, islem)
islem : DOKUNMA (--dokunma gunleri), ZATEN_KAPAKLI (mevcut URL --kapakli-url listesinde), ONAY_BEKLER
Kullanim: toplu_eslesme_plan.py --bekleyen A.csv [B.csv] --plan PLAN.csv --dokunma 2026-10-16 --kapakli-url URL --cikti ESLESME_PLANI.csv"""
import argparse, csv
from collections import Counter


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--bekleyen', nargs='+', required=True); a.add_argument('--plan', required=True)
    a.add_argument('--dokunma', nargs='*', default=[]); a.add_argument('--kapakli-url', nargs='*', default=[])
    a.add_argument('--cikti', required=True)
    o = a.parse_args()
    satir = {}
    for f in o.bekleyen:
        for r in csv.DictReader(open(f, encoding='utf-8')):
            satir[r['uuid']] = r
    plan = {r['tarih_saat']: r['cift'] for r in csv.DictReader(open(o.plan, encoding='utf-8')) if r['medya_url'].startswith('VIDEO:')}
    out = []
    for r in sorted(satir.values(), key=lambda r: (r['saat'], r['platform'])):
        c = plan.get(r['saat'], '?')
        slug = c.lower().replace('_', '-and-', 1)
        islem = ('DOKUNMA' if r['saat'][:10] in o.dokunma else
                 'ZATEN_KAPAKLI' if r['video_url'] in o.kapakli_url else 'ONAY_BEKLER')
        out.append({'saat': r['saat'], 'platform': r['platform'], 'uuid': r['uuid'], 'id_simdi': r['id'], 'cift': c,
                    'cift_metin': r['cift'], 'video_dosya': f'FINAL_KAPAKLI/{slug}-astroloveart-reel.mp4',
                    'mevcut_video_url': r['video_url'], 'kapak_url': r['kapak_url'], 'islem': islem})
    for i, r in enumerate(out, 1):
        r['sira'] = i
    alan = ['sira', 'saat', 'platform', 'uuid', 'id_simdi', 'cift', 'cift_metin', 'video_dosya', 'mevcut_video_url', 'kapak_url', 'islem']
    with open(o.cikti, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, alan); w.writeheader(); [w.writerow(r) for r in out]
    hata = [r['uuid'] for r in out if r['cift'] == '?' or (r['cift_metin'] != '?' and r['cift_metin'] != r['cift'])]
    gun = Counter(r['saat'] for r in out)
    print(f"PLAN {len(out)} gonderi, {len(gun)} gun; islem {dict(Counter(r['islem'] for r in out))}; "
          f"platform {dict(Counter(r['platform'] for r in out))}; gun basi 4: {all(v == 4 for v in gun.values())}; "
          f"yukleme (ONAY_BEKLER cift) {len({r['cift'] for r in out if r['islem'] == 'ONAY_BEKLER'})}; cift hatasi {len(hata)}")
    print('ILK', [(r['saat'][:10], r['platform'], r['islem']) for r in out[:8]])


if __name__ == '__main__':
    main()
