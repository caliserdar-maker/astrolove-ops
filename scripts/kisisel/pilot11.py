#!/usr/bin/env python3
"""
Bes oranda (Blue 2/3, 3/4, 4/5, 11/14, A) SECENEK D olcumu ve uretimi.

Asama "olcum": Canva sayfalarini indirir, Drive'a ORANLAR/ham/ altina arsivler,
her oranin yerlesim sabitlerini olcer (OLCUM.json).
Asama "uret" : ham sayfalardan D kuralina gore poster ve sinir ornegi uretir.

DEGISEN OGELER: bu dosya yalniz olcum/ornek uretir.
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

from kisisel_pilot import DEST, rc
from pilot6 import LUMA, MUREKKEP, kumeler

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
HAM = OUT / "ham"
ORAN_YOL = OUT / "ORANLAR"
DEST_O = DEST + "/ORANLAR"
NORM_W = 2400                       # olcumler bu genislige normalize edilir
SAYFA_AD = {20: "ARIES_SAGITTARIUS", 28: "CANCER_LIBRA",
            36: "CAPRICORN_LEO", 72: "SAGITTARIUS_VIRGO"}
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def indir(kaynaklar):
    """kaynaklar: [(oran, sayfa, url)] -> {(oran,sayfa): path}"""
    HAM.mkdir(parents=True, exist_ok=True)
    yol = {}
    for i, (oran, sayfa, url) in enumerate(kaynaklar, 1):
        p = HAM / f"{oran}_p{sayfa:02d}.jpg"
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(p, "wb") as f:
                f.write(r.read())
            yol[(oran, sayfa)] = p
            log(f"({i}/{len(kaynaklar)}) {p.name} {p.stat().st_size / 1e6:.1f} MB")
        except Exception as e:
            log(f"({i}/{len(kaynaklar)}) {p.name} INDIRILEMEDI: {str(e)[:120]}")
    return yol


def norm(im):
    k = NORM_W / im.width
    return im.resize((NORM_W, int(round(im.height * k))), Image.LANCZOS), k


def bantlar(mask, en_az=3, en_ince=6):
    sat = mask.sum(axis=1)
    out, y, h = [], 0, mask.shape[0]
    while y < h:
        if sat[y] > en_az:
            b = y
            while y < h and sat[y] > en_az:
                y += 1
            if y - b > en_ince:
                out.append((b, y))
        y += 1
    return out


def sayfa_olc(path):
    """Isim satiri, semboller ve tagline'i oranlardan bagimsiz olcer."""
    ham = Image.open(path).convert("RGB")
    im, k = norm(ham)
    A = np.asarray(im).astype(np.float32)
    L = A @ LUMA
    # Maske yonu zemine gore: koyu zeminde parlak yazi (Blue/Black), acik
    # zeminde koyu yazi (Pure White, Modern, Vintage).
    acik_zemin = float(np.median(L)) > 128
    if acik_zemin:
        # Acik zeminde yazi koyu; esik zemin ile en koyu piksel arasinda
        # olculur (Modern/Vintage'da kontrast dusuk).
        z = float(np.median(L))
        alt = float(np.percentile(L, 0.5))
        m = L < z - max(12.0, (z - alt) * 0.35)
    else:
        m = L > MUREKKEP
    H = im.height
    bl = bantlar(m)
    aday = []
    for b in bl:
        km = [c for c in kumeler(m[b[0]:b[1]], 20) if c[1] - c[0] > 40]
        if len(km) == 3 and b[0] > H * 0.55:
            orta = km[1][1] - km[1][0]
            yan = min(km[0][1] - km[0][0], km[2][1] - km[2][0])
            if orta < yan * 1.3:                 # ortadaki sonsuzluk, yanlar isim
                aday.append((b, km))
    if not aday:
        raise SystemExit(f"{path.name}: isim satiri bulunamadi ({len(bl)} bant)")
    isim_b, km = max(aday, key=lambda t: t[1][2][1] - t[1][0][0])
    sol, inf, sag = km
    d = {"kaynak_boyut": list(ham.size), "olcek": round(k, 5),
         "acik_zemin": bool(acik_zemin),
         "norm_boyut": [im.width, im.height],
         "isim_bant": list(isim_b), "sol_isim": list(sol), "sonsuz": list(inf),
         "sag_isim": list(sag),
         "bosluk": [inf[0] - sol[1], sag[0] - inf[1]],
         "satir": [sol[0], sag[1]], "satir_genislik": sag[1] - sol[0],
         "satir_merkez": round((sol[0] + sag[1]) / 2, 1),
         "poster_merkez": im.width / 2,
         "isim_merkez": [round((sol[0] + sol[1]) / 2, 1), round((sag[0] + sag[1]) / 2, 1)],
         "isim_yuksekligi": isim_b[1] - isim_b[0],
         "kenar_payi": [sol[0], im.width - sag[1]]}
    d["satir_kaymasi"] = round(d["satir_merkez"] - d["poster_merkez"], 1)
    # sembol bandi: isim bandinin hemen ustunde, 2 kume
    ust = [b for b in bl if b[1] <= isim_b[0]]
    for b in sorted(ust, key=lambda b: -b[1])[:3]:
        sk = [c for c in kumeler(m[b[0]:b[1]], 20) if c[1] - c[0] > 30]
        if len(sk) == 2:
            d["sembol_bant"] = list(b)
            d["sembol"] = [list(sk[0]), list(sk[1])]
            d["sembol_merkez"] = [round((sk[0][0] + sk[0][1]) / 2, 1),
                                  round((sk[1][0] + sk[1][1]) / 2, 1)]
            d["sembol_isim_kaymasi"] = [round(d["sembol_merkez"][i] - d["isim_merkez"][i], 1)
                                        for i in (0, 1)]
            break
    # tagline bandi: isim bandinin altinda, tek genis kume
    alt = [b for b in bl if b[0] >= isim_b[1]]
    for b in alt:
        tk = [c for c in kumeler(m[b[0]:b[1]], 60) if c[1] - c[0] > 200]
        if len(tk) == 1 and b[1] - b[0] > 30:
            d["tag_bant"] = list(b)
            d["tag_x"] = list(tk[0])
            d["tag_genislik"] = tk[0][1] - tk[0][0]
            d["tag_yuksekligi"] = b[1] - b[0]
            d["tag_merkez"] = round((tk[0][0] + tk[0][1]) / 2, 1)
            break
    # halka / en genis oge (tagline guvenli alani icin)
    ustler = [b for b in bl if b[1] < isim_b[0]]
    if ustler:
        gen = 0
        for b in ustler:
            km2 = kumeler(m[b[0]:b[1]], 40)
            if km2:
                gen = max(gen, km2[-1][1] - km2[0][0])
        d["ust_en_genis"] = gen
    return d


def bg_hizasi(ref_norm, bg):
    """bg.png'yi bu orana uydurmaya calis; en iyi (olcek, dy) ve medyan fark."""
    A = np.asarray(ref_norm).astype(np.float32)
    L = A @ LUMA
    bos = L < MUREKKEP                      # yalniz murekkepsiz alanlar
    en_iyi = None
    for s in np.arange(1.00, 1.45, 0.05):
        w = int(round(NORM_W * s))
        b = bg.convert("RGB").resize((w, int(round(bg.height * w / bg.width))),
                                     Image.LANCZOS)
        bx = (w - NORM_W) // 2
        for dy in range(-160, 161, 40):
            y0 = (b.height - ref_norm.height) // 2 + dy
            if y0 < 0 or y0 + ref_norm.height > b.height:
                continue
            c = np.asarray(b.crop((bx, y0, bx + NORM_W,
                                   y0 + ref_norm.height))).astype(np.float32)
            f = float(np.median(np.abs(A - c).max(axis=2)[bos][::7]))
            if en_iyi is None or f < en_iyi[0]:
                en_iyi = (f, round(float(s), 2), dy)
    return {"medyan_fark": round(en_iyi[0], 2), "olcek": en_iyi[1], "dy": en_iyi[2]} \
        if en_iyi else {"medyan_fark": None}


def olcum(yol, bg_path=None):
    bg = Image.open(bg_path) if bg_path and Path(bg_path).exists() else None
    d = {}
    oranlar = sorted({o for o, _ in yol})
    for oran in oranlar:
        d[oran] = {"sayfalar": {}}
        for sayfa in sorted({s for o, s in yol if o == oran}):
            p = yol[(oran, sayfa)]
            try:
                o = sayfa_olc(p)
                o["ad"] = SAYFA_AD.get(sayfa, str(sayfa))
                d[oran]["sayfalar"][str(sayfa)] = o
                log(f"{oran} s{sayfa} {o['ad']}: tuval {o['kaynak_boyut']} "
                    f"bosluk {o['bosluk']} merkez sapma {o['satir_kaymasi']} "
                    f"sembol-isim {o.get('sembol_isim_kaymasi')} "
                    f"satir {o['satir_genislik']} kenar {o['kenar_payi']} "
                    f"tag {o.get('tag_genislik')} h{o.get('tag_yuksekligi')}")
            except Exception as e:
                d[oran]["sayfalar"][str(sayfa)] = {"hata": str(e)[:200]}
                log(f"{oran} s{sayfa} OLCULEMEDI: {str(e)[:160]}")
        ok = [o for o in d[oran]["sayfalar"].values() if "hata" not in o]
        if ok:
            bosluklar = [b for o in ok for b in o["bosluk"]]
            d[oran]["ozet"] = {
                "tuval": ok[0]["kaynak_boyut"],
                "bosluk_ort": round(float(np.mean(bosluklar)), 1),
                "bosluk_araligi": [int(min(bosluklar)), int(max(bosluklar))],
                "merkez_sapma_maks": max(abs(o["satir_kaymasi"]) for o in ok),
                "sembol_isim_maks": max((max(abs(x) for x in o["sembol_isim_kaymasi"])
                                         for o in ok if "sembol_isim_kaymasi" in o),
                                        default=None),
                "en_genis_satir": max(o["satir_genislik"] for o in ok),
                "en_dar_kenar": min(min(o["kenar_payi"]) for o in ok),
                "isim_yuksekligi": round(float(np.mean([o["isim_yuksekligi"] for o in ok])), 1),
                "tag_genislik_maks": max((o["tag_genislik"] for o in ok if "tag_genislik" in o),
                                         default=None),
                "tag_yukseklik": round(float(np.mean([o["tag_yuksekligi"] for o in ok
                                                      if "tag_yuksekligi" in o])), 1),
                "ust_en_genis": max((o.get("ust_en_genis", 0) for o in ok), default=0),
            }
            if bg is not None and ("28", ok) and str(28) in d[oran]["sayfalar"]:
                p28 = yol.get((oran, 28))
                if p28:
                    rn, _ = norm(Image.open(p28).convert("RGB"))
                    d[oran]["bg"] = bg_hizasi(rn, bg)
                    log(f"{oran} bg hizasi: {d[oran]['bg']}")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asama", default="olcum")
    ap.add_argument("--kaynak", nargs="*", default=[],
                    help="oran:sayfa:url ucluleri")
    ap.add_argument("--yerel", action="store_true")
    a = ap.parse_args()
    ORAN_YOL.mkdir(parents=True, exist_ok=True)

    kaynaklar = []
    for s in a.kaynak:
        oran, sayfa, url = s.split(":", 2)
        kaynaklar.append((oran, int(sayfa), url))
    yol = indir(kaynaklar) if kaynaklar else {}
    if not yol:                                   # ham sayfalar Drive'da olabilir
        if not a.yerel:
            HAM.mkdir(parents=True, exist_ok=True)
            rc("copy", f"{DEST_O}/ham", str(HAM))
        for p in sorted(HAM.glob("*_p*.jpg")):
            oran, sayfa = p.stem.split("_p")
            yol[(oran, int(sayfa))] = p
        log(f"ham sayfalar yerelden/Drive'dan: {len(yol)}")

    if not a.yerel and kaynaklar:
        rc("copy", str(HAM), f"{DEST_O}/ham")
        log(f"Drive <- ham ({len(yol)} sayfa)")

    bgp = OUT / "hazir" / "bg.png"
    if not bgp.exists() and not a.yerel:
        (OUT / "hazir").mkdir(parents=True, exist_ok=True)
        try:
            rc("copy", f"{DEST}/HAZIR/bg.png", str(OUT / "hazir"))
        except Exception as e:
            log(f"bg.png alinamadi: {str(e)[:100]}")
    d = olcum(yol, bgp)
    (ORAN_YOL / "OLCUM.json").write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    if not a.yerel:
        rc("copy", str(ORAN_YOL / "OLCUM.json"), DEST_O)
        log(f"Drive <- OLCUM.json")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
