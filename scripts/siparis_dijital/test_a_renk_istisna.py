"""a_renk isimli istisna dogrulamasi (Serdar 10 Eki, is A). Girdi: 360cbef siparis yolunda olculen gercek a_renk ayrintilari
(test_veri/a_renk_11x14_20261010.json: 10 istisnali cift + GEMINI_LEO referans). Calistir: python test_a_renk_istisna.py"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import surucu as s

V = json.loads((Path(__file__).resolve().parent / 'test_veri' / 'a_renk_11x14_20261010.json').read_text())
ISTISNALI = sorted(c for c, b in s.WP_A_RENK_ISTISNA)
hata = []


def bekle(ad, cift, boy, a, beklenen):
    g, r = s.a_renk_karar(cift, boy, a)
    print(('PASS' if g == beklenen else 'HATA'), ad, cift, boy, 'gecti=%s beklenen=%s ara=%s sinir=%s' % (g, beklenen, r['ogeler_arasi_max_dE'], r['istisna_sinir']))
    if g != beklenen:
        hata.append(ad)


# 1) istisnali 10 cift, 11x14, gercek olcum -> PASS (genel kural FAIL)
assert len(ISTISNALI) == 10 and all(b == '11x14' for _, b in s.WP_A_RENK_ISTISNA)
for c in ISTISNALI:
    assert V[c]['gecti'] is False
    bekle('istisna', c, '11x14', V[c], True)
# 2) GEMINI_LEO (istisnasiz, genel kural PASS) degismez
g, r = s.a_renk_karar('GEMINI_LEO', '11x14', V['GEMINI_LEO'])
bekle('referans', 'GEMINI_LEO', '11x14', V['GEMINI_LEO'], True); assert r['genel_gecti'] and r['istisna_sinir'] is None
# 3) istisnasiz ciftte renk sapmasi (ogeler arasi 5.30, genel FAIL) -> FAIL
a = copy.deepcopy(V['GEMINI_LEO']); a['ogeler_arasi_max_dE'] = 5.30; a['gecti'] = False
bekle('istisnasiz_sapma', 'GEMINI_LEO', '11x14', a, False)
# 4) istisnali cift, istisnasiz oran (16x20) ayni sapma -> FAIL
a = copy.deepcopy(V['LEO_VIRGO']); bekle('istisnasiz_oran', 'LEO_VIRGO', '16x20', a, False)
# 5) istisnali cift 11x14 sinirin ustu (olculen + 0.11) -> FAIL
a = copy.deepcopy(V['LEO_VIRGO']); a['ogeler_arasi_max_dE'] = round(V['LEO_VIRGO']['ogeler_arasi_max_dE'] + 0.11, 2)
bekle('sinir_ustu', 'LEO_VIRGO', '11x14', a, False)
# 6) istisna hedefe dE ve kahve oranini GEVSETMEZ
a = copy.deepcopy(V['LEO_VIRGO']); a['hedefe_dE'] = dict(a['hedefe_dE'], sonsuz=5.2); bekle('hedefe_dE', 'LEO_VIRGO', '11x14', a, False)
a = copy.deepcopy(V['LEO_VIRGO']); a['kahve_orani'] = 0.05; bekle('kahve', 'LEO_VIRGO', '11x14', a, False)
print('SONUC', 'PASS' if not hata else 'FAIL ' + str(hata))
sys.exit(1 if hata else 0)
