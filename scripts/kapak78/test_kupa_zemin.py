#!/usr/bin/env python3
"""kupa_zemin govde korumasi testi (Serdar 31 Eki, K05 15 oz kenar kusuru). Kart ortami (pillow 11.0.0, numpy 2.1.3, opencv 4.10.0.84).
Girdi: temiz/kupa-orchard 0196e37a varlik/gorunum (git ile okunur; --ko <kupa_orchard klasoru> verilirse oradan).
T1 GEO sabitleri = 0196e37a geo_tek_on / geo_tek_arka / geo15 json (sol / sag degeri).
T2 her sahnede (11 oz tek_on, tek_arka; 15 oz sahne15): (a) GrabCut'in kupa saydigi pikselden govde icinde oyulan = 0 (kenar oyulmasi
   0 px; eski kural m15 sag kenarda oyuyordu); (b) govde icinde, son kupa maskesinin 4 px icindeki piksellerde cikti = girdi (kupa
   pikseli degismez; geometrinin kupanin yuvarlak koselerinden tasan zemin pikselleri ve 1-3 px kenar yumusatmasi olcu disi).
T3 her sahnede govde DISINDA zemin esitlenir: kirpim kenar seridi zeminden en fazla 3 (olc kenar_max), masa golgesi oyulur (govde disi
   oyulan > 0); yani duzeltme golge temizligini bozmaz.
T4 SAHNE_GEO tanimsiz sahne -> DUR (sessiz gecis yok).
Kullanim: test_kupa_zemin.py [--ko <kupa_orchard>]   (cikis 0 = PASS)"""
import argparse
import io
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REF = "0196e37a0447d61eab42b84778a56d9261b0b201"
SAHNE = {"tek_on": ("ORCHARD_OrangeBlossom_sahne_tek_on.png", "geo_tek_on.json", "sol"),
         "tek_arka": ("ORCHARD_OrangeBlossom_sahne_tek_arka.png", "geo_tek_arka.json", "sag"),
         "m15": ("sahne15.png", "geo15.json", "sol")}
IC_PX = 4


def oku(ko, ad):
    if ko:
        return (Path(ko) / "varlik" / "gorunum" / ad).read_bytes()
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", REF], check=True, cwd=HERE)
    return subprocess.run(["git", "show", f"{REF}:kupa_orchard/varlik/gorunum/{ad}"], check=True, capture_output=True, cwd=HERE).stdout


def sahne_olc(arg):
    ad, png = arg
    import numpy as np
    import cv2
    from PIL import Image
    import kupa_zemin as Z
    im = Image.open(io.BytesIO(png)).convert("RGB")
    a = np.asarray(im)
    k0 = Z.maske(a.astype(np.float32))
    z, k = Z.esitle(im, Z.GEO[ad])
    gv = Z.govde(a.shape, Z.GEO[ad], pay=0)
    ic = gv.astype(bool) & cv2.erode(k, np.ones((2 * IC_PX + 1, 2 * IC_PX + 1), np.uint8)).astype(bool)
    fark = (np.asarray(z) != a).any(2)
    oyulan = (k0 == 1) & (k == 0)
    return ad, dict(kupa_ic_degisen_px=int((fark & ic).sum()), govde_oyulan_px=int((oyulan & gv.astype(bool)).sum()),
                    govde_disi_oyulan_px=int((oyulan & ~gv.astype(bool)).sum()), **Z.olc(z, k))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ko", default="")
    a = ap.parse_args(argv)
    import kupa_zemin as Z
    s = []
    for ad, (_, gj, yuz) in SAHNE.items():
        g = tuple(float(x) for x in json.loads(oku(a.ko, gj))[yuz])
        s.append((f"T1 GEO {ad} = 0196e37a {gj}", g == Z.GEO[ad]))
    with ProcessPoolExecutor(max_workers=3) as ex:
        R = dict(ex.map(sahne_olc, [(ad, oku(a.ko, v[0])) for ad, v in SAHNE.items()]))
    for ad, r in R.items():
        print(ad, json.dumps(r))
        s.append((f"T2a {ad}: govdede oyulan kupa pikseli 0", r["govde_oyulan_px"] == 0))
        s.append((f"T2b {ad}: govdede kupa ici (4 px) degisen piksel 0", r["kupa_ic_degisen_px"] == 0))
        s.append((f"T3 {ad}: govde disi zemin esit (kenar_max {r['kenar_max']:.0f} <= 3)", r["kenar_max"] <= 3))
    s.append(("T3 tek_on: masa golgesi hala oyuluyor (govde disi oyulan > 0)", R["tek_on"]["govde_disi_oyulan_px"] > 0))
    try:
        Z._isle(Path("/nonexistent"), Path("/tmp"), "yakin_plan")
        s.append(("T4 tanimsiz sahne DUR", False))
    except SystemExit as e:
        s.append(("T4 tanimsiz sahne DUR", "geometrisi tanimsiz" in str(e)))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"kupa_zemin testleri: {n}/{len(s)} PASS")
    return 0 if n == len(s) else 1


if __name__ == "__main__":
    sys.exit(main())
