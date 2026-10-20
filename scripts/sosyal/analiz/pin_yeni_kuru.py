#!/usr/bin/env python3
"""Pinterest takvim v2: 12 yeni yil donumu pini + "Zodiac Couple Mugs" panosu KURU (20 Eki 2026). Metricool'a YAZMA YOK.
Girdi: PLAN_V2.csv (kaynak 'YENI yil donumu' satirlari), YEDEK.json (canli bekleyen Pinterest gonderileri; sablon),
       GET /v2/scheduler/boards/pinterest (1 cagri). Gorsel adresi HEAD ile denetlenir (yazma yok).
Yeni pin metni: canli yil donumu pinlerinden (media .../pinterest/v7/y1/<A>_<B>_PIN.jpg, A != B) burc adlari yer tutucuya cevrilen
  kaliplar (baslik, metin, alt metin); 12 pine sirayla dagitilir. Gorsel: .../astrolove-media/pinterest/v7/y1/<CIFT>_PIN.jpg.
Cikti: OUT/YENI_PIN_KURU.csv, OUT/YENI_PIN_GOVDE.json (POST /v2/scheduler/posts govde onizlemesi), OUT/PANO_NOTU.txt
Kullanim: pin_yeni_kuru.py TOKEN.json --plan PLAN_V2.csv --yedek YEDEK.json --out OUT [--sahte-pano P.json]"""
import argparse
import copy
import csv
import importlib.util
import json
import os
import re
import urllib.request

D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('v1', os.path.join(D, 'pin_takvim_plan.py'))
v1 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v1)
mpb, TZ = v1.mpb, v1.TZ
MEDYA = 'https://caliserdar-maker.github.io/astrolove-media/pinterest/v7/y1/'
KUPA_PANO = 'Zodiac Couple Mugs'
CIKAR = ('id', 'uuid', 'creationDate', 'creatorUserId', 'creatorUserMail', 'hasNotReadNotes', 'brandTags')


def ad(b):
    return b.capitalize()


def kalip(p):
    m = re.search(r'/v7/y1/([A-Z]+)_([A-Z]+)_PIN\.jpg', ' '.join(p.get('media') or []))
    if not m or m.group(1) == m.group(2):
        return None
    A, B = ad(m.group(1)), ad(m.group(2))

    def yt(t):
        return re.sub(rf'\b{B}\b', '{B}', re.sub(rf'\b{A}\b', '{A}', t or ''))
    pd = p.get('pinterestData') or {}
    k = dict(baslik=yt(pd.get('pinTitle')), metin=yt(p.get('text')), alt=[yt(x) for x in p.get('mediaAltText') or []], kaynak=p)
    if '{A}' not in k['baslik'] or '{B}' not in k['baslik'] or '{A}' not in k['metin']:
        return None
    return k


def head(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'astrolove-ops'}), timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f'hata {str(e)[:60]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('--plan', required=True); ap.add_argument('--yedek', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--sahte-pano', default='')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    yedek = json.load(open(a.yedek))
    ps = yedek.get('gonderiler', yedek) if isinstance(yedek, dict) else yedek
    if a.sahte_pano:
        panolar = json.load(open(a.sahte_pano))
    else:
        mc = mpb.MC(json.load(open(a.token)))
        panolar = v1.liste(mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b}))
    pano_id = {(b.get('name') or '').strip(): str(b.get('id')) for b in panolar}

    kal = [k for k in (kalip(p) for p in ps if mpb.pin_durum(p) is not None) if k]
    tekil, gor = [], set()
    for k in kal:
        anahtar = (k['baslik'], k['metin'])
        if anahtar not in gor:
            gor.add(anahtar); tekil.append(k)
    if not tekil:
        raise SystemExit('DUR: canli yil donumu pin sablonu bulunamadi')
    yeni = [r for r in csv.DictReader(open(a.plan, encoding='utf-8')) if r['kaynak'].startswith('YENI yil donumu')]
    satir, govdeler = [], []
    for i, r in enumerate(yeni):
        A, B = (ad(x) for x in r['cift'].split('_'))
        k = tekil[i % len(tekil)]
        url = MEDYA + f"{r['cift']}_PIN.jpg"
        st = head(url)
        pn = r['pano'].replace(' (OLUSTURULACAK)', '')
        baslik, metin = k['baslik'].format(A=A, B=B), k['metin'].format(A=A, B=B)
        alt = [x.format(A=A, B=B) for x in k['alt']]
        yol = ('yayinda' if st == 200 else
               f"YOK ({st}): Drive KAPAK_Y1_78_20261019/PIN/{r['cift']}_PIN.jpg -> Drive ASTROLOVE/TEMP/SOSYAL/PINTEREST/MEDYA/v7/y1/ "
               f"(rclone copy) -> pin-media-sync.yml (klasor=v7/y1) -> astrolove-media pinterest/v7/y1/ (GitHub Pages)")
        g = copy.deepcopy(k['kaynak'])
        for x in CIKAR:
            g.pop(x, None)
        g.update(text=metin, media=[url], mediaAltText=alt,
                 publicationDate={'dateTime': f"{r['yeni_tarih']}T{r['yeni_saat']}:00", 'timezone': TZ},
                 providers=[{'network': 'pinterest'}])
        g['pinterestData'] = dict(g.get('pinterestData') or {}, boardId=pano_id.get(pn, f'PANO_YOK:{pn}'), pinTitle=baslik, pinLink=r['link'])
        govdeler.append(g)
        satir.append([r['yeni_tarih'], r['yeni_saat'], r['cift'], url, st, yol, pn, pano_id.get(pn, 'YOK'), r['link'], baslik, len(baslik),
                      metin, ' | '.join(alt), k['kaynak'].get('uuid', '')])
    with open(os.path.join(a.out, 'YENI_PIN_KURU.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['plan_tarih', 'plan_saat', 'cift', 'gorsel_url', 'gorsel_http', 'gorsel_yayin_yolu', 'pano', 'pano_id', 'link',
                    'baslik', 'baslik_uzunluk', 'metin', 'alt_metin', 'sablon_uuid'])
        w.writerows(satir)
    json.dump(govdeler, open(os.path.join(a.out, 'YENI_PIN_GOVDE.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'YENI_PIN_KURU: {len(satir)} pin; gorsel 200: {sum(1 for s in satir if s[4] == 200)}; sablon {len(tekil)}; '
          f'pano id: {sorted({s[7] for s in satir})}; uzun baslik (>100): {sum(1 for s in satir if s[10] > 100)}')

    var = KUPA_PANO in pano_id
    n = [f'PANO NOTU (20 Eki 2026, KURU; Metricool yazma YOK)',
         f'Metricool Pinterest panolari (GET /v2/scheduler/boards/pinterest?brandId): {len(pano_id)}',
         *[f'  {k}: {v}' for k, v in sorted(pano_id.items())],
         f'"{KUPA_PANO}": ' + ('VAR, id ' + pano_id[KUPA_PANO] if var else 'YOK'),
         '',
         'Metricool API ile acilabilir mi: EVET (belgeli uc).',
         '  POST /v2/scheduler/boards/pinterest?brandId=<blogId>; govde Board semasi {name (zorunlu), description, privacy} '
         '(data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json); yanit JsonOkResponseBoard (id, name, owner).',
         '  Repoda hazir script: scripts/sosyal/metricool_pano_ac.py (14 Eki onayi): ayni adli pano varsa ACMAZ, POST yeniden denenmez,',
         '  sonra pano listesi yeniden okunup dogrulanir, PANO_AC.json yazar. Kullanim ornegi: by78-pin-hazirlik.yml mod=pano',
         '  ("1st Anniversary Gift Ideas" icin). Not: o kosunun PANO_AC.json dosyasi Drive\'da bulunamadi; pano listede var.',
         '  Elle is gerekmez: ayri onayla tek koşu, ornek govde {"name": "Zodiac Couple Mugs", "description": "Personalized zodiac couple',
         '  mugs with your two signs, names and message by AstroLoveArt.", "privacy": "PUBLIC"}. Acildiktan sonra pano id GET ile alinir ve',
         '  kupa pinlerinde pinterestData.boardId olarak kullanilir.',
         'Baska yol (elle is olmadan): Pinterest API v5 POST /v5/boards (Pinterest token gerekir; repoda Pinterest token yok, docs/SECRETS.md);',
         '  Metricool yolu yeterli oldugundan gerekmez.',
         '',
         f'Yeni yil donumu pinleri: {len(satir)}; gorsel yayinda {sum(1 for s in satir if s[4] == 200)}/{len(satir)}; '
         f'pano "1st Anniversary Gift Ideas" id {pano_id.get("1st Anniversary Gift Ideas", "YOK")}. POST ayri adim ve onay '
         '(govde onizlemesi YENI_PIN_GOVDE.json).']
    open(os.path.join(a.out, 'PANO_NOTU.txt'), 'w').write('\n'.join(n) + '\n')
    print('\n'.join(n[:3] + n[-1:]))


if __name__ == '__main__':
    main()
