#!/usr/bin/env python3
"""Pinterest panosu ac (Metricool POST /v2/scheduler/boards/pinterest?brandId, createPinterestBoard). Serdar onayi 14 Eki 2026.
Yalniz pano acilir; pin gonderme/zamanlama YOK. Ayni adli pano varsa ACILMAZ (tekrar yok). POST yeniden denenmez.
Sonra pano listesi yeniden okunup dogrulanir. Cikti: PANO_AC.json. Kullanim: metricool_pano_ac.py TOKEN.json AD ACIKLAMA CIKTI_DIR"""
import importlib.util, json, os, re, sys

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)


def panolar(mc):
    liste = mpb.veri(mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b}))
    if isinstance(liste, dict):
        liste = next((v for v in liste.values() if isinstance(v, list)), [])
    return liste or []


def main():
    tok, ad, aciklama, cikti = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(cikti, exist_ok=True)
    if '—' in ad + aciklama or '–' in ad + aciklama:
        sys.exit('DUR: uzun/orta tire')
    mc = mpb.MC(json.load(open(tok)))
    once = panolar(mc)
    print(f'PANO once {len(once)}: ' + '; '.join(b.get('name', '') for b in once))
    var = [b for b in once if (b.get('name') or '').strip().lower() == ad.strip().lower()]
    if var:
        sonuc, pano = 'ZATEN_VAR', var[0]
    else:
        y = mpb.veri(mc.istek('POST', '/v2/scheduler/boards/pinterest', {'brandId': mc.b},
                              govde={'name': ad, 'description': aciklama, 'privacy': 'PUBLIC'}))
        print('POST yaniti alanlari:', sorted(y) if isinstance(y, dict) else type(y).__name__)
        sonuc, pano = 'ACILDI', y if isinstance(y, dict) else {}
    sonra = panolar(mc)
    bul = [b for b in sonra if (b.get('name') or '').strip().lower() == ad.strip().lower()]
    if not bul:
        sys.exit(f'DUR: pano listede yok ({sonuc})')
    b = bul[0]
    kullanici = ((b.get('owner') or {}).get('username') or (pano.get('owner') or {}).get('username') or '')
    slug = re.sub(r'[^a-z0-9]+', '-', ad.lower()).strip('-')
    link = f'https://www.pinterest.com/{kullanici}/{slug}/' if kullanici else ''
    rapor = {'sonuc': sonuc, 'id': b.get('id'), 'name': b.get('name'), 'description': b.get('description'),
             'privacy': b.get('privacy'), 'owner': kullanici, 'link_tahmini': link, 'pano_sayisi_once': len(once),
             'pano_sayisi_sonra': len(sonra)}
    json.dump(rapor, open(os.path.join(cikti, 'PANO_AC.json'), 'w'), ensure_ascii=False, indent=1)
    print('PANO', json.dumps(rapor, ensure_ascii=False))


if __name__ == '__main__':
    main()
