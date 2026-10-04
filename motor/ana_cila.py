#!/usr/bin/env python3
"""ANA SEMBOL CILA HATTI (Serdar 4 Eki): her ana sembol Canva ciktisi icin sabit sira.

1 vurgu_altin (cila ONCESI): ham Canva ciktisina Serdar onayli leke giderme kurali (parametreler degismez).
2 cila: doku_cila.hizala (sekil bizim maskeden, doku Canva'dan) + esleme (hedef orijinal AQUARIUS_ARIES, s17 ile ayni ayar).
3 vurgu_altin (cila SONRASI): cila renk eslemesi solgun lekeyi kismen geri getiriyor (4 Eki olcumu ANA_DENEME: cila
  sonrasi 41 / 41 / 19 / 31 binde), ayni kural bir kez daha uygulanir.
4 leke_kapi: her ana sembol olculur; esik disi (> ESIK) varsa cikis kodu 1 (FAIL), sembol Canva'da yeniden uretilir.

Cikti: <cikti>/<ad>.npz (t1, O; doku_poster --ana-sayfa ile kullanilir) + <ad>_CILA.json (hizalama, esleme, leke tablosu).
Kullanim: ana_cila.py --girdi DOKU_AI_<SAYFA>.png --json DOKU_AI_<SAYFA>.json --canva CANVA.jpg
          --referans main_aquarius_aries_gold.png --ad ANA_X --cikti DIR
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import doku_cila as dc                                               # noqa: E402
import leke_kapi as lk                                               # noqa: E402
import vurgu_altin as va                                             # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    for k in ('girdi', 'json', 'canva', 'referans', 'ad', 'cikti'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    C = Path(a.cikti); C.mkdir(parents=True, exist_ok=True)
    # 1 cila oncesi vurgu
    vf = C / f'{a.ad}_CANVA_VURGU.png'
    Image.fromarray(va.vurgu_altin(np.asarray(Image.open(a.canva).convert('RGB')))).save(vf)
    # 2 cila
    rr, rA, ric = dc.referans(a.referans)
    t, O, ic, h = dc.hizala(a.girdi, a.json, str(vf))
    E = dc.esleme_olc(t, ic, rr, ric)
    t1 = np.clip(np.round(dc.esleme_uygula(t, E)), 0, 255).astype(np.uint8)
    O8 = np.round(O * 255).astype(np.uint8)
    # 3 cila sonrasi vurgu
    t2 = va.vurgu_altin(t1)
    np.savez_compressed(C / f'{a.ad}.npz', t1=t2, O=O8)
    # 4 leke kapisi
    j = json.loads(Path(a.json).read_text())
    tab = {}
    for o in j['ogeler']:
        x0, y0, x1, y1 = o['kutu']
        Oc = O8[y0:y1, x0:x1].astype(np.float32) / 255
        tab[o['oge']] = {'cila_sonrasi': lk.olc(t1[y0:y1, x0:x1], Oc)[0], 'son': lk.olc(t2[y0:y1, x0:x1], Oc)[0]}
    disi = [k for k, v in tab.items() if v['son'] > lk.ESIK]
    rap = {'ad': a.ad, 'canva': Path(a.canva).name, 'hizalama_ecc': h['ecc_cc'], 'oran_farki_px': h['oran_farki_px'],
           'leke_esik': lk.ESIK, 'leke': tab, 'esik_disi': disi, 'sonuc': 'FAIL' if disi else 'PASS'}
    (C / f'{a.ad}_CILA.json').write_text(json.dumps(rap | {'hizalama': h, 'esleme': E}, indent=1, ensure_ascii=False,
                                                    default=float))
    print(json.dumps(rap, ensure_ascii=False))
    sys.exit(1 if disi else 0)


if __name__ == '__main__':
    main()
