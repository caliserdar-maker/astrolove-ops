#!/usr/bin/env python3
"""F6 (Denetim, 2 Kas): 1st Anniversary 5 stil x 14 boy KONTAK + icerik kutusu dikey denge kapisi. ETSY YOK, uretim yok (yalniz kontrol).
Turetme (firstpage_boylar ile ayni kural; uretim hattinda 14 boy icin baska tanim YOK): 12x18 ana dosya (3600x5400) boy oranina DIKEY ORTALI
kirpilir (yukseklik = 3600 x boy orani; 2:3 boylarda kirpma yok), hedef piksele (inc x 300; A mm; by_boy.BOY) LANCZOS. Kontak kucuk
gorselleri ayni kirpimdan dogrudan kucultulur (tam cozunurluk boy dosyasi yazilmaz).
KAPI (gorev F6 madde 1-2): oge maskesi (by_stil4 / by_ornek3 OGE_<stil>.png) ayni kirpimla; ust bosluk = ilk oge satiri, alt = son oge
satirindan alta; oran = alt / ust. Referans: ESKI 8x10 (Baski_2400x3000 zemin + by_poster ogeleri, olcek 1) ayni tanim. PASS: kirpimda oge
pikseli kaybi 0 VE |oran / eski oran - 1| <= 0,10.
Kullanim: yd_f6_boy_kontak.py --kod <bizim-yilimiz kopyasi> --dizin <12x18 + OGE dizini> --out <dir> [--pair --n1 --n2]"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_boy as BB  # noqa: E402  (BOY)

TOL = 0.10
# stil: (12x18 dosyasi, oge maskesi, eski 8x10 zemin adi, by_poster fonksiyonu)
STIL = {"Starlit": ("ORNEK3_12x18_v3.jpg", "OGE_Starlit.png", "1_Starlit", "starlit"),
        "Timeless": ("Timeless_12x18.jpg", "OGE_Timeless.png", "2_Timeless", "timeless"),
        "FirstPage": ("FirstPage_12x18.jpg", "OGE_FirstPage.png", "3_FirstPage", "first_page"),
        "Layers_B": ("Layers_B_12x18.jpg", "OGE_Layers_B.png", "4_Layers", "layers"),
        "Botanical": ("Botanical_12x18.jpg", "OGE_Botanical.png", "5_Botanical", "botanical")}
SIRA = ["5x7", "8x10", "11x14", "12x16", "12x18", "16x20", "16x24", "18x24", "20x30", "24x30", "24x36", "A4", "A3", "A2"]


def bosluk(m):
    r = np.where(m.any(1))[0]
    if not r.size:
        return dict(ust=None, alt=None, oran=None)
    u, a_ = int(r.min()), int(m.shape[0] - 1 - r.max())
    return dict(ust=u, alt=a_, oran=round(a_ / max(u, 1), 4))


def kirp(H, W, boy):
    wi, hi = BB.BOY[boy]
    Wt, Ht = round(wi * 300), round(hi * 300)
    Hc = min(H, round(W * Ht / Wt))
    return (H - Hc) // 2, Hc, Wt, Ht


def eski_oran(kod, zemin, fn, pair, n1, n2):
    import by_ornek3 as B3
    bp = B3.by_poster(kod, 1, pair, n1, n2)
    e = np.asarray(Image.open(Path(kod, "z/Baski_2400x3000_Buyutulmus", f"{zemin}_8x10_300ppi.png")).convert("RGB"))
    bp.bgimg = lambda name: Image.fromarray(e)
    s = np.asarray(getattr(bp, fn)().convert("RGB"))
    return bosluk(np.abs(s.astype(np.int16) - e.astype(np.int16)).max(2) > 2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True); ap.add_argument("--dizin", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--pair", default="CANCER_LIBRA"); ap.add_argument("--n1", default="EMMA"); ap.add_argument("--n2", default="JAMES")
    ap.add_argument("--kucuk", type=int, default=420)
    a = ap.parse_args(argv)
    d, out = Path(a.dizin), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if sorted(BB.BOY) != sorted(SIRA):
        raise SystemExit(f"DUR: by_boy.BOY {sorted(BB.BOY)} != F6 listesi")
    font = ImageFont.load_default(size=26)
    rap = dict(turetme="12x18 -> boy oranina dikey ortali kirpma -> hedef px LANCZOS (firstpage_boylar kurali)", tolerans=TOL, stil={})
    satirlar = ["stil,boy,hedef_px,kirpim_satir,kirpilan_oge_px,ust,alt,oran,eski_8x10_oran,oran_bagil,kapi"]
    for ad, (dosya, mdosya, zemin, fn) in STIL.items():
        img = Image.open(d / dosya).convert("RGB"); m = np.asarray(Image.open(d / mdosya)) > 0
        if img.size != (3600, 5400) or m.shape != (5400, 3600):
            raise SystemExit(f"DUR: {ad} boyut {img.size} / maske {m.shape}")
        ref = eski_oran(a.kod, zemin, fn, a.pair, a.n1, a.n2)
        r12 = bosluk(m)
        sonuc = {}; kucukler = []
        for boy in SIRA:
            y0, Hc, Wt, Ht = kirp(5400, 3600, boy)
            mk = m[y0:y0 + Hc]
            kayip = int(m.sum() - mk.sum())
            b = bosluk(mk)
            bag = round(b["oran"] / ref["oran"], 4) if b["oran"] is not None and ref["oran"] and kayip == 0 else None   # kesikse oran anlamsiz
            ok = bool(kayip == 0 and bag is not None and abs(bag - 1) <= TOL)
            sonuc[boy] = dict(hedef_px=[Wt, Ht], kirpim=[y0, y0 + Hc], kirpilan_oge_px=kayip, **b, oran_bagil=bag, pass_=ok)
            satirlar.append(f"{ad},{boy},{Wt}x{Ht},{y0}-{y0 + Hc},{kayip},{b['ust']},{b['alt']},{b['oran']},{ref['oran']},{bag},{'PASS' if ok else 'FAIL'}")
            k = img.crop((0, y0, 3600, y0 + Hc)).resize((round(a.kucuk * Wt / Ht), a.kucuk), Image.LANCZOS)
            kucukler.append((boy, k, ok, bag, kayip))
        rap["stil"][ad] = dict(eski_8x10=ref, ana_12x18=r12, boylar=sonuc, fail=[b_ for b_, v in sonuc.items() if not v["pass_"]])
        # kontak: 2 satir x 7, gercek oran, ust bantta boy adi + kapi
        pad, ust_ = 16, 64
        sat = [kucukler[:7], kucukler[7:]]
        W_ = max(sum(k.width for _, k, *_ in s) + pad * (len(s) + 1) for s in sat)
        K_ = Image.new("RGB", (W_, 70 + len(sat) * (a.kucuk + ust_ + pad)), (235, 235, 235)); dr = ImageDraw.Draw(K_)
        dr.text((pad, 18), f"F6 14 boy (12x18 dikey ortali kirpma) - {ad} - eski 8x10 alt/ust oran {ref['oran']} (+-%10)", fill=(0, 0, 0), font=font)
        for i, s in enumerate(sat):
            x = pad; y = 70 + i * (a.kucuk + ust_ + pad)
            for boy, k, ok, bag, kayip in s:
                renk = (0, 110, 0) if ok else (180, 0, 0)
                dr.text((x, y + 2), boy, fill=(0, 0, 0), font=font)
                et = f"FAIL KESIK {kayip} px" if kayip else ("PASS " if ok else "FAIL ") + (f"x{bag}" if bag is not None else "-")
                dr.text((x, y + 30), et, fill=renk, font=ImageFont.load_default(size=20))
                K_.paste(k, (x, y + ust_)); x += k.width + pad
        K_.save(out / f"F6_KONTAK_{ad}.jpg", quality=82)
        print(f"{ad}: eski {ref['oran']} 12x18 {r12['oran']} FAIL {rap['stil'][ad]['fail']}", flush=True)
    (out / "F6_BOSLUK.json").write_text(json.dumps(rap, indent=1), encoding="utf-8")
    (out / "F6_BOSLUK.csv").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    n_fail = sum(len(v["fail"]) for v in rap["stil"].values())
    print(f"F6 bosluk kapisi: {70 - n_fail}/70 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
