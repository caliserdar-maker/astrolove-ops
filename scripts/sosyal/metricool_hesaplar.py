#!/usr/bin/env python3
"""SALT OKUMA (yalniz GET): Metricool bagli hesaplar + Instagram yayin ozellikleri.
GET /admin/simpleProfiles, GET /v2/settings/brands/{blogId}, GET /v2/scheduler/posts/instagram-properties.
Cikti: CIKTI/HAM_*.json (Drive'a) + CIKTI/HESAPLAR.json (ozet: ag -> bagli mi, hesap adi). Token yazilmaz.
Kullanim: metricool_hesaplar.py TOKEN.json CIKTI"""
import importlib.util, json, os, sys

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
mc = mpb.MC(json.load(open(sys.argv[1]))); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
ham = {}
for ad, yol, p in (('simpleProfiles', '/admin/simpleProfiles', None), ('brand', f'/v2/settings/brands/{mc.b}', None),
                   ('instagram_properties', '/v2/scheduler/posts/instagram-properties', None)):
    try:
        ham[ad] = mc.istek('GET', yol, p)
    except SystemExit as e:
        ham[ad] = {'HATA': str(e)}
    json.dump(ham[ad], open(os.path.join(out, f'HAM_{ad}.json'), 'w'), ensure_ascii=False, indent=1)
blog = next((b for b in (ham['simpleProfiles'] if isinstance(ham['simpleProfiles'], list) else [])
             if str(b.get('id')) == mc.b), {})
ag = {
    'instagram': (blog.get('instagram'), blog.get('instagramConnectionType')),
    'facebook': (blog.get('facebook'), blog.get('facebookPageId')),
    'threads': (blog.get('threads'), blog.get('threadsAccountName')),
    'tiktok': (blog.get('tiktok'), blog.get('tiktokAccountType')),
    'youtube': (blog.get('youtube'), blog.get('youtubeChannelName')),
    'pinterest': (blog.get('pinterest'), blog.get('pinterestBusiness')),
}
ozet = {'blogId': mc.b, 'label': blog.get('label'), 'aglar': {k: {'bagli': bool(v[0]), 'hesap': v[0], 'ek': v[1]} for k, v in ag.items()},
        'instagram_properties': mpb.veri(ham['instagram_properties']) if isinstance(ham['instagram_properties'], dict) else ham['instagram_properties'],
        'brand_networksData_anahtarlar': sorted((mpb.veri(ham['brand']) or {}).get('networksData', {}) or {}) if isinstance(ham['brand'], dict) else None}
json.dump(ozet, open(os.path.join(out, 'HESAPLAR.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False, indent=1))
