#!/usr/bin/env python3
"""
Edisyon on olcumu: zemin kaynagi, zemin hizasi ve yazi dokusu.

Her edisyonun 4:5 sayfa 28'i indirilir; sayfa dogrulanir (CANCER/LIBRA satiri),
zemin adayi varsa hizalanir, yazi dokusu Blue altiniyla karsilastirilir.
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from kisisel_pilot import DEST, FOLDERS, fetch, rc
from pilot6 import LUMA, MUREKKEP, kumeler, met_al
from pilot11 import NORM_W, norm, sayfa_olc
from pilot12 import ince_hiza, fark_haritasi

OUT = Path(__file__).resolve().parents[2] / "out"
YOL = OUT / "EDISYONLAR"
DEST_E = DEST + "/EDISYONLAR"
ZEMIN = {"black": ("klasor", "deep_black_bg.jpg", "1AMdYwBXUVa8GfZ4i1Q4_rji2Y5i9yz7o"),
         "blue": ("hazir", "bg.png", None)}
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def yazi_dokusu(im, o28):
    """Isim ve tagline yazisinin dokusu: ortalama RGB, parlaklik std, dikey profil."""
    a = np.asarray(im).astype(np.float32)
    L = a @ LUMA
    out = {}
    for ad, (x0, x1), (y0, y1) in (
            ("isim_sol", o28["sol_isim"], o28["isim_bant"]),
            ("isim_sag", o28["sag_isim"], o28["isim_bant"]),
            ("tagline", o28["tag_x"], o28["tag_bant"])):
        kes = a[y0:y1, x0:x1]
        kesL = L[y0:y1, x0:x1]
        zemin_ort = float(np.median(kesL))
        m = kesL > zemin_ort + 25 if kesL.mean() < 128 else kesL < zemin_ort - 25
        if m.sum() < 200:
            m = np.abs(kesL - zemin_ort) > 20
        px = kes[m]
        prof = []
        for y in range(kes.shape[0]):
            if m[y].sum() >= 3:
                prof.append(np.median(kes[y, m[y]], axis=0))
        out[ad] = {"px": int(m.sum()),
                   "ort_rgb": [round(float(v), 1) for v in px.mean(axis=0)],
                   "parlaklik_std": round(float((px @ LUMA).std()), 2),
                   "profil": [[round(float(v), 1) for v in p] for p in prof[::4]],
                   "profil_n": len(prof)}
    return out


def profil_farki(p1, p2):
    """Iki dikey profilin ortalama farki (ayni uzunluga getirilerek)."""
    a, b = np.asarray(p1, np.float32), np.asarray(p2, np.float32)
    if not len(a) or not len(b):
        return None
    n = min(len(a), len(b))
    ai = np.stack([np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a)), a[:, k])
                   for k in range(3)], axis=1)
    bi = np.stack([np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(b)), b[:, k])
                   for k in range(3)], axis=1)
    return round(float(np.abs(ai - bi).mean()), 2)


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    kaynak = dict(x.split("=", 1) for x in a.kaynak)
    d = {"edisyon": {}}
    for ed, url in kaynak.items():
        p = YOL / f"{ed}_4x5_p28.jpg"
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(p, "wb") as f:
                f.write(r.read())
            log(f"{ed}: indi {p.stat().st_size / 1e6:.1f} MB")
        except Exception as e:
            d["edisyon"][ed] = {"hata": f"indirilemedi: {str(e)[:120]}"}
            log(f"{ed} INDIRILEMEDI: {str(e)[:120]}")
            continue
        kayit = {"dosya": p.name, "boyut": list(Image.open(p).size)}
        try:
            o = sayfa_olc(p)
            kayit["olcum"] = {k: o[k] for k in
                              ("kaynak_boyut", "bosluk", "satir_kaymasi", "isim_bant",
                               "sembol_isim_kaymasi", "tag_bant", "tag_genislik")
                              if k in o}
            kayit["dogrulama"] = ("3 kume + tagline bulundu"
                                  if "tag_bant" in o else "tagline bulunamadi")
            im, _ = norm(Image.open(p).convert("RGB"))
            kayit["doku"] = yazi_dokusu(im, o)
            log(f"{ed}: bosluk {o['bosluk']} satir sapma {o['satir_kaymasi']} "
                f"sembol-isim {o.get('sembol_isim_kaymasi')} "
                f"isim_sol rgb {kayit['doku']['isim_sol']['ort_rgb']} "
                f"std {kayit['doku']['isim_sol']['parlaklik_std']}")
        except BaseException as e:            # SystemExit dahil: digerleri devam etsin
            kayit["olcum_hata"] = f"{type(e).__name__}: {str(e)[:180]}"
            log(f"{ed} OLCULEMEDI: {str(e)[:160]}")
        d["edisyon"][ed] = kayit

    # zemin hizasi (kaynagi olan edisyonlar)
    for ed, (tur, ad, fid) in ZEMIN.items():
        if ed not in d["edisyon"] or "olcum" not in d["edisyon"][ed]:
            continue
        try:
            if tur == "klasor":
                rc("--drive-root-folder-id", fid, "copy", f"gdrive:{ad}", str(YOL),
                   timeout=600)
                zp = YOL / ad
            else:
                (OUT / "hazir").mkdir(parents=True, exist_ok=True)
                rc("copy", f"{DEST}/HAZIR/{ad}", str(OUT / "hazir"))
                zp = OUT / "hazir" / ad
            if not zp.exists():
                raise FileNotFoundError(ad)
            ref, _ = norm(Image.open(YOL / f"{ed}_4x5_p28.jpg").convert("RGB"))
            bg = Image.open(zp)
            h = ince_hiza(ref, bg, {"olcek": 1.0, "dy": 0})
            f, _ = fark_haritasi(ref, bg, h["olcek"], h["dy"], h["dx"])
            A = np.asarray(ref).astype(np.float32)
            bos = (A @ LUMA) < MUREKKEP if (A @ LUMA).mean() < 128 else (A @ LUMA) > 200
            d["edisyon"][ed]["zemin"] = {
                "kaynak": ad, "hiza": h,
                "bos_ort": round(float(f[bos].mean()), 2),
                "bos_p99": round(float(np.percentile(f[bos], 99)), 1),
                "gecti": bool(f[bos].mean() <= 1.5 and np.percentile(f[bos], 99) <= 5)}
            log(f"{ed} ZEMIN: {json.dumps(d['edisyon'][ed]['zemin'])}")
        except BaseException as e:
            d["edisyon"][ed]["zemin"] = {"hata": f"{type(e).__name__}: {str(e)[:150]}"}
            log(f"{ed} ZEMIN HATA: {str(e)[:160]}")

    # Pure White: zemin dosyasi yok - sayfanin bos bolgesi duz mu?
    for ed in ("pure_white", "modern", "vintage"):
        k = d["edisyon"].get(ed)
        if not k or "olcum" not in k:
            continue
        im, _ = norm(Image.open(YOL / f"{ed}_4x5_p28.jpg").convert("RGB"))
        A = np.asarray(im).astype(np.float32)
        o = k["olcum"]
        serit = A[o["tag_bant"][1] + 40:o["tag_bant"][1] + 140]
        k["zemin_duzlugu"] = {"serit_std": round(float((serit @ LUMA).std()), 2),
                              "serit_ort_rgb": [round(float(v), 1)
                                                for v in serit.reshape(-1, 3).mean(axis=0)]}
        log(f"{ed} zemin duzlugu: {k['zemin_duzlugu']}")

    # Blue altin dokusu ile karsilastirma
    try:
        refd = OUT / "ref" / "names"
        for f in ("cancer_name_gold.png", "libra_name_gold.png"):
            fetch(FOLDERS["names"], f, refd)
        met = met_al(refd / "cancer_name_gold.png")
        bp = [[round(float(v), 1) for v in p] for p in np.asarray(met["prof"])[::4]]
        d["blue_profil_n"] = len(met["prof"])
        for ed, k in d["edisyon"].items():
            if "doku" not in k:
                continue
            k["blue_fark"] = {a: profil_farki(bp, k["doku"][a]["profil"])
                              for a in ("isim_sol", "isim_sag", "tagline")}
            log(f"{ed} Blue altinina profil farki: {k['blue_fark']}")
    except Exception as e:
        d["blue_hata"] = str(e)[:160]

    (YOL / "EDISYON_ONOLCUM.json").write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    if not a.yerel:
        rc("copy", str(YOL / "EDISYON_ONOLCUM.json"), DEST_E)
        for ed in d["edisyon"]:
            p = YOL / f"{ed}_4x5_p28.jpg"
            if p.exists():
                rc("copy", str(p), DEST_E + "/ham")
        log(f"Drive <- {DEST_E}")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--kaynak", nargs="*", default=[], help="edisyon=url")
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
