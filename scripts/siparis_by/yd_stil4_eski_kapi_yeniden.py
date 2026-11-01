"""F raporu: kosu 2 ciktisi (JPEG) uzerinde Timeless / Botanical susleme parcalari icin ESKI ve YENI tanimla
(a) 255 kirpma orani: ESKI d2a38e47 = ciktida >=254 olan maske pikseli (eskide de doygun olanlar dahil); YENI 3081e4ad = yalniz eskide <250 olanlar
(b) maske disi susleme kutlesi: ESKI d2a38e47 = yakin halka koyuluk kutlesi / maske ici (taban cikarmasiz); YENI = (yakin - uzak taban) alan oranli.
(b) yalniz ESKI 8x10'dan hesaplanir (cikti kullanilmaz) -> OLCUM.json ile birebir olmali; (a) JPEG'den (cikti dizisi degil) -> yaklasik.
Kullanim: eski_kapi_yeniden.py <kosu2 dizini (OLCUM.json + *_12x18.jpg)> <eski 8x10 dizini> <cikti.json>"""
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import by_stil4 as BS
K = BS.K
d, src, cik = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
O = json.load(open(d / "OLCUM.json"))
sonuc = {}
for stil, fn, parca in (("Timeless", "2_Timeless", BS.timeless_parcalar), ("Botanical", "5_Botanical", lambda e: BS.botanical_parcalar(e)[0])):
    if stil not in O:
        continue
    e = np.asarray(Image.open(src / f"{fn}_8x10_300ppi.png").convert("RGB"))
    out = np.asarray(Image.open(d / f"{stil}_12x18.jpg").convert("RGB"))
    p = parca(e); sonuc[stil] = {}
    for ad, y in O[stil]["yerlesim"].items():
        maske_e = p[ad]; x0, y0, x1, y1 = y["kutu_eski"]; X, Y = y["X"], y["Y"]; w, h = x1 - x0, y1 - y0
        if X < 0 or Y < 0 or X + round(w * K) > out.shape[1] or Y + round(h * K) > out.shape[0]:   # susleme_kapi ile ayni tuval ici kirpim
            a0, b0 = max(0, -X), max(0, -Y); a1, b1 = min(round(w * K), out.shape[1] - X), min(round(h * K), out.shape[0] - Y)
            ex0, ey0 = x0 + int(np.ceil(a0 / K)), y0 + int(np.ceil(b0 / K)); ex1, ey1 = x0 + int(a1 // K), y0 + int(b1 // K)
            X, Y = X + round((ex0 - x0) * K), Y + round((ey0 - y0) * K); x0, y0, x1, y1, w, h = ex0, ey0, ex1, ey1, ex1 - ex0, ey1 - ey0
        har_e = cv2.dilate(maske_e.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
        De = BS.koyuluk(e, har_e)[y0:y1, x0:x1]
        mt = cv2.resize(maske_e[y0:y1, x0:x1].astype(np.uint8), (round(w * K), round(h * K)), interpolation=cv2.INTER_NEAREST) > 0
        eski_b = cv2.resize(e[y0:y1, x0:x1], (round(w * K), round(h * K)), interpolation=cv2.INTER_LANCZOS4)
        ok = out[Y:Y + round(h * K), X:X + round(w * K)]
        k_eski = int(((ok >= 254).any(2) & mt).sum()); k_yeni = int(((ok >= 254).any(2) & ~(eski_b >= 250).any(2) & mt).sum())
        me = maske_e[y0:y1, x0:x1]
        yak = (cv2.dilate(me.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0) & ~(cv2.dilate(me.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
        uzak = (cv2.dilate(me.astype(np.uint8), np.ones((361, 361), np.uint8)) > 0) & ~(cv2.dilate(me.astype(np.uint8), np.ones((241, 241), np.uint8)) > 0)
        dis_eski = float(De[yak & (De > 0.08)].sum() / max(De[me].sum(), 1e-6))
        yog = lambda b: float(De[b & (De > 0.08)].sum() / max(b.sum(), 1))
        dis_yeni = max(0.0, yog(yak) - (yog(uzak) if uzak.any() else 0.0)) * float(yak.sum()) / max(float(De[me].sum()), 1e-6)
        kj = O[stil]["kapi"][ad]
        sonuc[stil][ad] = dict(kirp_oran_ESKI_jpeg=round(k_eski / max(int(mt.sum()), 1), 5), kirp_oran_YENI_jpeg=round(k_yeni / max(int(mt.sum()), 1), 5),
                               kirp_oran_YENI_olcum_json=kj["kirpilan_255_oran"], dis_ESKI=round(dis_eski, 4), dis_YENI=round(dis_yeni, 4),
                               dis_YENI_olcum_json=kj["maske_disi_susleme_kutle_orani"])
json.dump(sonuc, open(cik, "w"), indent=1)
print(json.dumps(sonuc, indent=1))
