#!/usr/bin/env python3
"""GOREV 0028 - kart 03 (ortak sembol) butunluk kapisi. SALT OKUMA: Etsy'ye yazma yok.

canli <METIN_78.csv> <cikti>            : 78 ilanin canli rank 3 gorseli (1 batch cagrisi, API anahtari; indirme CDN)
kapi  <canli> <a77> <poster> <out> [cl_ref.jpg]: kapi -> out/SEMBOL_KART03.csv, FAIL kirpimlari, KART03_DUZELTME

Kapi (PASS/FAIL, esik OLCULEREK turetildi, 27 Eyl): kart 03 panelinin alt bolgesindeki birlesik sembol, ciftin onayli
POD posterindeki (POD_PRINT/<CIFT>/MIDNIGHT_BLUE/30x40.jpg) halka ici birlesik sembolle kiyaslanir.
  dogru ornekler (22): 13 canli kart 03 + 9 YANYANA sag (26 Eyl) + CL04 orijinal (YANYANA sol): IoU 0.845-0.960, boy 0.98-1.005
  bozuk ornek: CL canli 8629360573 (= TAM_SET 03): IoU 0.067, boy 0.470
  esik = iki kume arasi orta nokta: IoU >= 0.45 ve |1 - boy| <= 0.25
"""
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import APIKeyStore, Etsy  # noqa: E402
from pod_galeri_tamset import cift_anahtar  # noqa: E402


def ilanlar(metin):
    L = {}
    for r in csv.DictReader(open(metin, encoding="utf-8")):
        c = cift_anahtar(r.get("cift"))
        if c and r.get("ilan_id"):
            L[str(r["ilan_id"]).strip()] = c
    return L


def canli(metin, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    api = Etsy(APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    L = ilanlar(metin); ids = list(L); ozet = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images"}) or {}
        for x in d.get("results") or []:
            lid = str(x["listing_id"]); im = sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0)
            ozet[lid] = {"cift": L[lid], "state": x.get("state"), "foto": len(im),
                         "ranklar": [[y.get("rank"), y.get("listing_image_id")] for y in im]}
            r3 = next((y for y in im if y.get("rank") == 3), None)
            if r3:
                b = requests.get(r3["url_fullxfull"], timeout=60).content
                (out / f"{lid}_{L[lid]}_03_{r3['listing_image_id']}.jpg").write_bytes(b)
                ozet[lid]["r3"] = r3["listing_image_id"]
    (out / "_canli.json").write_text(json.dumps(ozet, indent=1))
    print(f"ilan {len(L)} okunan {len(ozet)} rank3 {sum('r3' in v for v in ozet.values())} kota {api.remaining}")


PANEL04 = (1320, 480, 2831, 2011)      # kart 03 (CL 04) sembol paneli, 3000x2250 kartta (tam_set.py ile ayni)
KART = (3000, 2250)


def kart_sembol(im):
    """Kart panelinin alt bolgesindeki (%55-98) birlesik sembol maskesi (tam_set.kart04 ile ayni bolge ve murekkep esigi)."""
    im = im.convert("RGB")
    if im.size != KART:
        im = im.resize(KART, Image.LANCZOS)
    a = np.asarray(im).astype(np.float32); x0, y0, x1, y1 = PANEL04; P = a[y0:y1, x0:x1]; H, W = P.shape[:2]
    flat = np.median(P[5:40, 5:40].reshape(-1, 3), 0)
    ink = np.abs(P - flat).max(2) > 40
    low = np.zeros((H, W), bool); low[int(0.55 * H):int(0.98 * H), 12:W - 12] = True   # panel kenari (olcekli kopyada 1-2 px kayma) disarida
    lab, n = ndimage.label(ink & low); al = np.bincount(lab.ravel())
    return np.isin(lab, [i for i in range(1, n + 1) if al[i] >= 200]), flat


def poster_sembol(im):
    """Onayli POD posterinde (2400 px en) halka ici birlesik sembol: altin murekkep (R-B > 60), halka = ust %60'ta en genis
    bilesen, cember oturtulur; halka ici (r < R-25) ve halka bileseni disi, en buyugun %5'inden buyuk bilesenler."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    ink = (a[..., 0] - a[..., 2]) > 60
    ust = ink.copy(); ust[int(0.6 * ust.shape[0]):] = False
    lab, n = ndimage.label(ndimage.binary_dilation(ust, iterations=2))
    sl = ndimage.find_objects(lab)
    h = 1 + max(range(n), key=lambda i: sl[i][1].stop - sl[i][1].start)
    ys, xs = np.where((lab == h) & ust)
    for _ in range(3):
        cx, cy, c = np.linalg.lstsq(np.c_[2 * xs, 2 * ys, np.ones(len(xs))], xs ** 2 + ys ** 2, rcond=None)[0]
        R = np.sqrt(c + cx ** 2 + cy ** 2); d = np.abs(np.hypot(xs - cx, ys - cy) - R); k = d < np.percentile(d, 60) + 3
        xs, ys = xs[k], ys[k]
    yy, xx = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
    ic = ust & (lab != h) & (np.hypot(xx - cx, yy - cy) < R - 25)
    lab2, n2 = ndimage.label(ndimage.binary_dilation(ic, iterations=3)); al = np.bincount(lab2.ravel()); al[0] = 0
    return ic & np.isin(lab2, [i for i in range(1, n2 + 1) if al[i] >= 0.05 * al.max()])


def kutu(m):
    ys, xs = np.where(m)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def olc(kart_m, poster_m, kaydir=10):
    """Poster sembolu kart sembolunun enine olceklenir (kart04 ile ayni kural), kutu sol-ustleri hizalanip +-kaydir px
    aranir; oran = en iyi IoU (2 px genisletilmis maskelerle). Boy orani (kart boy / poster boy, ayni olcekte) ayrica."""
    kb, pb = kutu(kart_m), kutu(poster_m)
    K = kart_m[kb[1]:kb[3], kb[0]:kb[2]]; Pm = poster_m[pb[1]:pb[3], pb[0]:pb[2]]
    s = K.shape[1] / Pm.shape[1]
    Pi = np.asarray(Image.fromarray(Pm.astype(np.uint8) * 255).resize((K.shape[1], max(1, round(Pm.shape[0] * s))), Image.LANCZOS)) > 127
    Kd, Pd = ndimage.binary_dilation(K, iterations=2), ndimage.binary_dilation(Pi, iterations=2)
    H = max(Kd.shape[0], Pd.shape[0]) + 2 * kaydir; W = Kd.shape[1] + 2 * kaydir
    A = np.zeros((H, W), bool); A[kaydir:kaydir + Kd.shape[0], kaydir:kaydir + Kd.shape[1]] = Kd
    en = 0.0
    for dy in range(0, 2 * kaydir + 1, 2):
        for dx in range(0, 2 * kaydir + 1, 2):
            B = np.zeros((H, W), bool); B[dy:dy + Pd.shape[0], dx:dx + Pd.shape[1]] = Pd
            en = max(en, (A & B).sum() / max(1, (A | B).sum()))
    return round(float(en), 4), round(K.shape[0] / Pi.shape[0], 4)


IOU_ESIK, BOY_ESIK = 0.45, 0.25
CL_KUTU = (442, 890, 1058, 1469)      # CL 04 panelinde birlesik sembol kutusu (RAPOR_TAM_SET kart04.birlesik_kutu)


def karar(oran, boy):
    return "PASS" if oran >= IOU_ESIK and abs(1 - boy) <= BOY_ESIK else "FAIL"


ZEMIN, PANEL_RENK, DUZEN_ESIK = (237, 232, 226), (6, 17, 37), 12   # kart 03 duzeni: 43 kart 0.0, 35 eski rank 3 (oda sahnesi) >= 213


def kart03_mu(im):
    """Gorsel kart 03 duzeninde mi: 4 kose zemini ve panel koseleri olculur (eski galerilerde rank 3 oda sahnesi)."""
    a = np.asarray(im.convert("RGB").resize(KART, Image.LANCZOS)).astype(np.float32)
    pan = np.abs(np.median(a[485:520, 1325:1360].reshape(-1, 3), 0) - PANEL_RENK).max()
    zem = max(np.abs(np.median(a[y:y + 40, x:x + 40].reshape(-1, 3), 0) - ZEMIN).max() for x, y in ((40, 40), (2900, 40), (40, 2150), (2900, 2150)))
    return pan < DUZEN_ESIK and zem < DUZEN_ESIK


def denetle(im, pm):
    if not kart03_mu(im):
        return "KART03_DEGIL", "", ""
    m, _ = kart_sembol(im)
    if m.sum() < 500:
        return "FAIL", 0.0, 0.0
    o, b = olc(m, pm)
    return karar(o, b), o, b


def duzelt(kart, poster):
    """Kodla onarim (AI yok): kart panelindeki birlesik sembol alani duz panel rengine boyanir; posterin halka ici birlesik
    sembolu (renk + alfa = altin murekkep yogunlugu) CL kutusunun enine olceklenip kutu merkezine konur (kart04 kurali)."""
    k = kart.convert("RGB").resize(KART, Image.LANCZOS) if kart.size != KART else kart.convert("RGB")
    a = np.asarray(k).astype(np.float32); x0, y0, x1, y1 = PANEL04; P = a[y0:y1, x0:x1].copy()
    m, flat = kart_sembol(k)
    P[ndimage.binary_dilation(m, iterations=14)] = flat
    pa = np.asarray(poster.convert("RGB")).astype(np.float32); pm = poster_sembol(poster)
    bx0, by0, bx1, by1 = kutu(pm); pad = 12
    F = pa[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad]
    g = (F[..., 0] - F[..., 2])
    cek = np.percentile(g[pm[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad]], 95)
    al = np.clip((g - 20) / max(cek - 20, 1), 0, 1) * ndimage.binary_dilation(pm[by0 - pad:by1 + pad, bx0 - pad:bx1 + pad], iterations=4)
    s = (CL_KUTU[2] - CL_KUTU[0]) / (bx1 - bx0)
    nw, nh = round(F.shape[1] * s), round(F.shape[0] * s)
    Fi = np.asarray(Image.fromarray(np.clip(F, 0, 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float32)
    ai = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)).astype(np.float32)[..., None] / 255
    cx, cy = (CL_KUTU[0] + CL_KUTU[2]) / 2, (CL_KUTU[1] + CL_KUTU[3]) / 2
    px, py = int(round(cx - nw / 2)), int(round(cy - nh / 2))
    Hh, Ww = P.shape[:2]; px, py = min(max(px, 0), Ww - nw), min(max(py, 0), Hh - nh)
    P[py:py + nh, px:px + nw] = P[py:py + nh, px:px + nw] * (1 - ai) + Fi * ai
    a[y0:y1, x0:x1] = P
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def kirpim(im, poster, yol):
    k = im.convert("RGB").resize(KART, Image.LANCZOS) if im.size != KART else im.convert("RGB")
    x0, y0, x1, y1 = PANEL04; a = k.crop((x0, y0 + int(0.5 * (y1 - y0)), x1, y1))
    pm = poster_sembol(poster); b = poster.crop(tuple(int(v) for v in kutu(pm)))
    b = b.resize((round(b.width * a.height / b.height), a.height))
    c = Image.new("RGB", (a.width + b.width + 20, a.height), "white"); c.paste(a, (0, 0)); c.paste(b, (a.width + 20, 0))
    c.thumbnail((1400, 1400)); c.save(yol, quality=85)


def kapi(canli_d, a77, poster_d, out, cl_ref=None):
    import time
    canli_d, a77, poster_d, out = Path(canli_d), Path(a77), Path(poster_d), Path(out)
    (out / "kirpim").mkdir(parents=True, exist_ok=True); (out / "duzeltme").mkdir(parents=True, exist_ok=True)
    oz = json.loads((canli_d / "_canli.json").read_text())
    satir, t0 = [], time.time()
    sira = sorted(oz, key=lambda l: (oz[l]["cift"] != "CANCER_LIBRA", oz[l]["cift"]))      # CL once
    for i, lid in enumerate(sira, 1):
        c = oz[lid]["cift"]; r = {"ilan": lid, "cift": c, "canli_image_id": oz[lid].get("r3", "")}
        pf = poster_d / f"{c}.jpg"
        if not pf.exists():
            r.update(canli="POSTER_YOK", tamset="POSTER_YOK"); satir.append(r); continue
        poster = Image.open(pf); pm = poster_sembol(poster)
        cf = next(iter(canli_d.glob(f"{lid}_*_03_*.jpg")), None)
        if cf:
            r["canli"], r["canli_oran"], r["canli_boy"] = denetle(Image.open(cf), pm)
            if r["canli"] == "FAIL": kirpim(Image.open(cf), poster, out / "kirpim" / f"{c}_canli.jpg")
        else:
            r["canli"] = "RANK3_YOK"
        tf = next(iter(sorted((a77 / c / "TAM_SET").glob("03_*.jpg"))), None) if (a77 / c / "TAM_SET").exists() else None
        if tf:
            r["tamset"], r["tamset_oran"], r["tamset_boy"] = denetle(Image.open(tf), pm)
            if r["tamset"] == "FAIL": kirpim(Image.open(tf), poster, out / "kirpim" / f"{c}_tamset.jpg")
        else:
            r["tamset"] = "TAMSET_YOK"
        if r["canli"] != "PASS" or r["tamset"] == "FAIL":
            taban = next((x for x, k in ((tf, r["tamset"]), (cf, r["canli"])) if x and k in ("PASS", "FAIL")), None)
            if c == "CANCER_LIBRA" and cl_ref and Path(cl_ref).exists():
                d, yontem = Image.open(cl_ref).convert("RGB"), "CL04 orijinal (Serdar onayli referans kart)"
            elif taban:
                d, yontem = duzelt(Image.open(taban), poster), "kod: poster birlesik sembolu CL kutusuna"
            else:
                d, yontem = None, "kart 03 tabani yok: TAM_SET gerekli (GOREV 0021)"
            r["duzeltme_yontem"] = yontem
            if d is not None:
                r["duzeltme"], r["duzeltme_oran"], r["duzeltme_boy"] = denetle(d, pm)
                if r["duzeltme"] == "PASS":
                    d.save(out / "duzeltme" / f"{c}_03_ortak_sembol.jpg", quality=95)
        satir.append(r)
        g = time.time() - t0
        print(f"[{i}/{len(sira)}] %{100 * i // len(sira)} gecen {g:.0f}s kalan {g / i * (len(sira) - i):.0f}s {c} canli {r['canli']} "
              f"{r.get('canli_oran', '')} tamset {r['tamset']} {r.get('tamset_oran', '')}", flush=True)
    alan = ["ilan", "cift", "canli", "tamset", "canli_oran", "canli_boy", "tamset_oran", "tamset_boy", "canli_image_id",
            "duzeltme", "duzeltme_oran", "duzeltme_boy", "duzeltme_yontem"]
    with open(out / "SEMBOL_KART03.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(satir)
    bozuk = [x for x in satir if x["canli"] == "FAIL"]
    ozet = {"canli_bozuk": len(bozuk), "toplam": len(satir), "canli_kart03_degil": [x["cift"] for x in satir if x["canli"] == "KART03_DEGIL"],
            "tamset_fail": sum(x["tamset"] == "FAIL" for x in satir),
            "tamset_yok": sum(x["tamset"] == "TAMSET_YOK" for x in satir), "bozuk": [x["cift"] for x in bozuk],
            "duzeltme_pass": sum(x.get("duzeltme") == "PASS" for x in satir), "esik": {"iou": IOU_ESIK, "boy": BOY_ESIK}}
    (out / "SEMBOL_KART03_OZET.json").write_text(json.dumps(ozet, indent=1))
    print(json.dumps(ozet))


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "canli":
        canli(sys.argv[2], sys.argv[3])
    elif m == "kapi":
        kapi(*sys.argv[2:7])
    elif m == "kucult":                     # POD poster (9000 px) -> 2400 px en (Canva sayfa normu)
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(sys.argv[2]).convert("RGB")
        im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS).save(sys.argv[3], quality=92)
    else:
        raise SystemExit(f"bilinmeyen mod {m}")
