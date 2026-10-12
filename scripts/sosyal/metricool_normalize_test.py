#!/usr/bin/env python3
"""Metricool normalize testi (gonderi OLUSTURMAZ): GET /actions/normalize/image/url?url=<herkese acik URL>.
Yanit: URL'nin Metricool deposundaki karsiligi (dogrulama: yanit URL'si ve HTTP durumu). Kullanim: TOKEN.json URL CIKTI.json"""
import importlib.util, json, os, sys

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
mc = mpb.MC(json.load(open(sys.argv[1])))
try:
    y = mc.istek('GET', '/actions/normalize/image/url', {'url': sys.argv[2]})
    sonuc = {'url': sys.argv[2], 'sonuc': 'OK', 'yanit': y}
except SystemExit as e:
    sonuc = {'url': sys.argv[2], 'sonuc': 'HATA', 'hata': str(e)}
json.dump(sonuc, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
print('NORMALIZE', json.dumps(sonuc, ensure_ascii=False)[:600])
