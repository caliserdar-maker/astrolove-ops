"""kisisel-v1 onayli tagline kodu (pilot12.tagline_plaka: EB Garamond Italic, punto kurali, SECENEK 1 altin doku) ile tagline
katmani; TABAN CIZGISI referans metnin (EMILY & JAMES) kisisel taban cizgisine hizalanir (Serdar, 25 Eyl v5).
kisisel-v1 dalinin scripts/kisisel dizininde kosulur. argv: REF_TAGLINE TAGLINE CIKTI.png"""
import json, sys
sys.path.insert(0, '.')
import numpy as np
from PIL import Image
import pilot12, pilot16
from pilot6 import ciz_cap, TAG_FONT, TAG_W
from kisisel_pilot import FONT_DIR
from pilot11 import OUT
ref_tag, tag, yol = sys.argv[1:4]
pilot12.profil_yukle(OUT / 'ref' / 'names')
olc = json.load(open(OUT / 'ORANLAR' / 'OLCUM_4x5.json'))['4x5']
s, S = pilot16.oran_kur('4x5', olc, Image.open(OUT / 'hazir' / 'bg.png'))
def plaka(t):
    tg, bilgi = pilot12.tagline_plaka(s, {'prof': pilot12.PROFIL}, t)
    _, cu, ct = ciz_cap(FONT_DIR / TAG_FONT, TAG_W, bilgi['punto'], t)
    return tg, bilgi, cu, ct
tgR, bR, cuR, ctR = plaka(ref_tag)
taban = int(round(s['tag_y'] - tgR.height / 2)) + ctR          # referansin poster_kur'daki taban cizgisi
tg, b, cu, ct = plaka(tag)
tx, ty = int(round(pilot12.NORM_W / 2 - tg.width / 2)), taban - ct
t = Image.fromarray(np.clip(S['temiz_a'], 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
t.alpha_composite(tg, (tx, ty)); t.convert('RGB').save(yol)
m = {'ref': ref_tag, 'tag': tag, 'punto': [bR['punto'], b['punto']], 'olcek': [bR['olcek'], b['olcek']], 'genislik': [bR['genislik'], b['genislik']],
     'cap_yuk_px': [ctR - cuR, ct - cu], 'taban_poster': taban, 'merkez_kurali_tabani': int(round(s['tag_y'] - tg.height / 2)) + ct, 'tx_ty': [tx, ty]}
json.dump(m, open(yol + '.json', 'w'), indent=1); print(json.dumps(m))
