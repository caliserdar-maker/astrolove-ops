#!/usr/bin/env python3
"""SALT OKUMA: Metricool Pinterest pano listesi (GET /v2/scheduler/boards/pinterest?brandId=<blogId>).
Cikti: PANOLAR_HAM.json (yanit) + PANOLAR.json ([{id, name}]). Kullanim: metricool_panolar.py TOKEN.json CIKTI_DIR"""
import importlib.util, json, os, sys

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
tok = json.load(open(sys.argv[1])); os.makedirs(sys.argv[2], exist_ok=True)
mc = mpb.MC(tok)
ham = mc.istek('GET', '/v2/scheduler/boards/pinterest', {'brandId': mc.b})
json.dump(ham, open(os.path.join(sys.argv[2], 'PANOLAR_HAM.json'), 'w'), ensure_ascii=False, indent=1)
liste = mpb.veri(ham)
if isinstance(liste, dict):
    liste = next((v for v in liste.values() if isinstance(v, list)), [])
out = [{'id': str(b.get('id') or b.get('boardId') or ''), 'name': b.get('name') or b.get('title') or ''} for b in liste]
json.dump(out, open(os.path.join(sys.argv[2], 'PANOLAR.json'), 'w'), ensure_ascii=False, indent=1)
print(f'PANO {len(out)}: ' + '; '.join(f"{b['name']}={b['id']}" for b in out))
