# stil_yazi.py (7 Kas) - K06 "Choose Your Style": baslik, stil adlari, alt not (ornament_kart.py:18, 78-80 birebir)
# Tipografi yd_kart_ornek.py:140-143. Disk konumlari stil_zincir.sh olcumlerinden (SET_kart_stil_d*.json).
import json, sys, os
from PIL import Image, ImageDraw, ImageFont

FD = os.environ.get("FONT_DIR", str(__import__("pathlib").Path(__file__).resolve().parents[2] / "kapak78" / "yd_kart" / "fonts")) + "/"
RENK = (43, 34, 32)


def font(dosya, boy, agirlik):
    f = ImageFont.truetype(FD + dosya, boy)
    f.set_variation_by_axes([agirlik])
    return f


BAS, ETK, NOT = font("CormorantGaramond.ttf", 170, 500), font("Manrope.ttf", 68, 600), font("Manrope.ttf", 58, 400)
ADLAR = ["Ruby", "Sapphire", "Emerald", "White", "Ivory"]
img = Image.open(sys.argv[1]).convert("RGB"); W, H = img.size
# inceleme t3-4: sahne %92 (ust ortada), ustte 40 px duz bant, yanlar ve alt yansitmali keten -> baslik bantta rahat, alt not kenardan uzak
import numpy as np, cv2
OL, UST = 0.92, 40
_a = np.asarray(img)
_s = cv2.resize(_a, (round(W * OL), round(H * OL)), interpolation=cv2.INTER_AREA)
_sol = (W - _s.shape[1]) // 2
_bant = np.median(_s[5:60, :, :].reshape(-1, 3), 0).astype(np.uint8)
_t = cv2.copyMakeBorder(_s, 0, H - UST - _s.shape[0], _sol, W - _s.shape[1] - _sol, cv2.BORDER_REFLECT)   # onayli gorunum (Serdar "Hepsi guzel")
_a = np.concatenate([np.tile(_bant, (UST, W, 1)), _t], 0)
img = Image.fromarray(_a)
DON = lambda x, y: (_sol + OL * x, UST + OL * y)
BANT_ALT = UST + OL * 280
d = ImageDraw.Draw(img)
diskler = [json.load(open(f"SET_kart_stil_d{i}.json")) for i in range(5)]
ozet = []
# baslik: ust bos bantta ortali
bb = d.textbbox((0, 0), "Choose Your Style", font=BAS)
yb = (BANT_ALT - (bb[3] - bb[1])) / 2 - bb[1]           # baslik bantta dikey ortali
d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], yb), "Choose Your Style", font=BAS, fill=RENK)
ozet.append(("baslik", yb + bb[1], yb + bb[3]))
for ad, o in zip(ADLAR, diskler):
    hx, hy, hr = o["delik_bizim"]; R = o["R"]
    cx, cy = DON(hx, hy + 0.699 * R); R = OL * R
    sira = 0 if cy < H / 2 else 1
    alt_kenar = max(DON(0, q["delik_bizim"][1] + 1.699 * q["R"])[1] for q in diskler
                    if (DON(0, q["delik_bizim"][1])[1] < H / 2) == (sira == 0))   # t3-6: satirda ortak taban
    b2 = d.textbbox((0, 0), ad, font=ETK)
    y = alt_kenar + 45 - b2[1]                    # secim_kart: etiket 45 px alt (kart_sablon.py:337)
    # t3-6: etiket ile ip arasi >= 40 px; gerekirse ipten uzaga en fazla 60 px yatay kaydir
    _ar = np.asarray(img).astype(np.int32); _r, _g, _b = _ar[..., 0], _ar[..., 1], _ar[..., 2]
    _alt = ((_g - _b) > 22) & ((_r - _b) > 50)
    _yy, _xx = np.mgrid[0:H, 0:W]
    for q in diskler:                                # disk icindeki baski altini ip degil
        _qx, _qy = DON(q["delik_bizim"][0], q["delik_bizim"][1] + 0.699 * q["R"])
        _alt &= np.hypot(_xx - _qx, _yy - _qy) > OL * q["R"] * 1.08   # disk kenar parlamasi da haric
    xs = cx - (b2[2] - b2[0]) / 2 - b2[0]
    def _yakin(dx):
        x0_, x1_ = int(xs + b2[0] + dx - 40), int(xs + b2[2] + dx + 40)
        return _alt[int(y + b2[1] - 40):int(y + b2[3] + 40), max(x0_, 0):x1_]
    kay = 0
    if _yakin(0).any():
        _m = _yakin(0); _sol_ip = np.where(_m.any(0))[0].mean() < _m.shape[1] / 2
        for kay in (range(4, 61, 4) if _sol_ip else range(-4, -61, -4)):
            if not _yakin(kay).any():
                break
        assert not _yakin(kay).any(), (ad, kay)
    d.text((xs + kay, y), ad, font=ETK, fill=RENK)
    print(ad, "kaydirma", kay)
    ozet.append((ad, round(y + b2[1]), round(y + b2[3])))
alt = "Every style printed on both sides"
b3 = d.textbbox((0, 0), alt, font=NOT)
_alt_et = max(v[2] for v in ozet[-2:])           # alt sira etiketlerinin bitisi
y3 = _alt_et + 40 - b3[1]                         # ayri blok arasi >= 40 px (kart_sablon.py:14)
assert y3 + b3[3] <= H - 70, y3 + b3[3]
d.text(((W - (b3[2] - b3[0])) / 2 - b3[0], y3), alt, font=NOT, fill=RENK)
ozet.append(("not", round(y3 + b3[1]), round(y3 + b3[3])))
img.save(sys.argv[2], quality=95, subsampling=0)
print(ozet)
