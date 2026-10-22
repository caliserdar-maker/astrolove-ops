#!/usr/bin/env python3
"""GOREV 0025 (+0028 md.3) - 78 canli POD ilaninin VIDEO + KAPAK denetimi (SALT OKUMA, Etsy'ye yazma YOK).
 etsy    : 1 Etsy okuma cagrisi (getListingsByListingIds, includes=images,videos; yalniz API anahtari, OAuth token
           YOK -> etsy-token kilidi gerekmez) -> ilan basina kapak (rank 1) URL, video URL'leri.
 denetle : Etsy API yok. Canli video + kapak i.etsystatic / v.etsystatic adreslerinden indirilir.
   VIDEO : 8 esit aralikli kare (%6..%94), 256px gri. Beklenen = A1_77/<CIFT>/VIDEO.mp4 (CL icin onayli v5).
           d_beklenen = 8 karenin ortalama farki (0-100 olcek). Tum beklenen videolarla karsilastirilir: en yakini
           baska cift ise YANLIS_CIFT. Esik kalibrasyonu: bilinen ESKI (AQUARIUS_SCORPIO canli) ile bilinen YENI
           (ARIES_LEO canli) d_beklenen degerlerinin ortasi; ESKI <= YENI ise DUR. Eski slogan ("TWO SOULS" /
           "ONE BOND") karelerde OCR ile aranir -> varsa ESKI.
           Sonuc: YENI (d <= esik ve 12.6 +- 0.3 sn) / ESKI (eski slogan ya da d > 10 x esik) / FARKLI (arada) /
           YANLIS_CIFT / YOK (video yok) / BEKLENEN_YOK (A1_77'de VIDEO.mp4 yok).
   KAPAK : canli rank 1 ile TAM_SET/01_kapak_MB.jpg 256px gri fark <= 0.001 -> YENI, degilse ESKI; TAM_SET yoksa
           BEKLENEN_YOK (slogan OCR bilgisiyle).
Cikti: out/CANLI_VIDEO_KAPAK.csv, out/CANLI_VIDEO_KAPAK_OZET.json
Kullanim: canli_video_kapak.py etsy <metin78_csv> <out_json> | denetle <canli_json> <a77_dir> <cl_v5_mp4>"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canli_qc import cift_anahtar, fark256  # noqa: E402

os.environ["OMP_THREAD_LIMIT"] = "1"
REF_ID, REF_CIFT = "4570143815", "CANCER_LIBRA"
KAL_ESKI, KAL_YENI = "AQUARIUS_SCORPIO", "ARIES_LEO"          # GOREV 0028: bilinen eski / yeni canli video
NOKTA = [0.06 + 0.88 * i / 7 for i in range(8)]               # 8 esit aralikli kare
SLOGAN = [r"TWO\s*SOULS", r"ONE\s*BOND"]
OUT = Path("out")


def log(m):
    print(m, flush=True)


def etsy(metin78, out_json):
    """Yalniz API anahtari (x-api-key = keystring:shared_secret), OAuth token YOK: getListingsByListingIds herkese
    acik ilan verisidir; token okunmaz/yenilenmez -> etsy-token kilidi gerekmez."""
    from etsy_common import API, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    oturum = requests.Session()
    oturum.headers["x-api-key"] = f"{k_}:{s_}"
    cagri = [0, None]

    def get(yol, params):
        r = oturum.get(API + yol, params=params, timeout=60)
        cagri[0] += 1
        cagri[1] = r.headers.get("x-remaining-today")
        r.raise_for_status()
        return r.json()
    satir = [r for r in csv.DictReader(open(metin78, encoding="utf-8")) if r.get("ilan_id")]
    cift = {r["ilan_id"]: r.get("cift", "") for r in satir}
    ids = list(cift)
    if REF_ID not in cift:
        ids.append(REF_ID); cift[REF_ID] = "Cancer + Libra"
    sonuc = {}
    for i in range(0, len(ids), 100):
        d = get("/listings/batch", {"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,videos"}) or {}
        for x in d.get("results") or []:
            lid = str(x.get("listing_id"))
            imgs = sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0)
            sonuc[lid] = {"cift": cift_anahtar(cift.get(lid, "")), "state": x.get("state"),
                          "kapak": imgs[0].get("url_fullxfull") if imgs else None, "foto": len(imgs),
                          "video": [v.get("video_url") for v in x.get("videos") or [] if v.get("video_url")]}
    Path(out_json).write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    log(f"etsy: {len(sonuc)} ilan, cagri {cagri[0]}, kota {cagri[1]}")


def indir(url, hedef):
    if Path(url).exists():                                    # yerel test
        Path(hedef).write_bytes(Path(url).read_bytes())
        return hedef
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    Path(hedef).write_bytes(r.content)
    return hedef


def sure(yol):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(yol)],
                       capture_output=True, text=True)
    return float((json.loads(p.stdout or "{}").get("format") or {}).get("duration") or 0)


def kareler(yol):
    """8 kare -> (256px gri dizileri, tam boy PIL kareleri)"""
    sn = sure(yol)
    gri, tam = [], []
    for t in NOKTA:
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t * sn:.2f}", "-i", str(yol), "-frames:v", "1", f.name],
                           check=True)
            im = Image.open(f.name).convert("RGB")
            im.load()
        tam.append(im)
        gri.append(np.asarray(im.convert("L").resize((256, 256), Image.BILINEAR), dtype=np.float32))
    return sn, np.stack(gri), tam


def uzaklik(a, b):
    return round(float(np.abs(a - b).mean() / 255 * 100), 3)


def slogan_var(tam):
    for im in tam:
        k = im.convert("L")
        k = k.resize((k.width * 2, k.height * 2), Image.LANCZOS)
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            k.save(f.name)
            t = subprocess.run(["tesseract", f.name, "-", "--psm", "11", "-l", "eng"], capture_output=True, text=True).stdout
        t = " ".join(re.sub(r"[^A-Z ]", " ", t.upper()).split())
        if any(re.search(s, t) for s in SLOGAN):
            return True
    return False


def canli_isle(arg):
    lid, x, is_dir = arg
    d = Path(is_dir) / lid
    d.mkdir(parents=True, exist_ok=True)
    r = {"ilan": lid, "cift": x["cift"], "foto": x["foto"], "video_sayisi": len(x["video"])}
    try:
        if x.get("kapak"):
            r["kapak_yol"] = str(indir(x["kapak"], d / "kapak.jpg"))
        if x["video"]:
            v = indir(x["video"][0], d / "canli.mp4")
            sn, gri, tam = kareler(v)
            np.save(d / "kare.npy", gri)
            r.update(sure=round(sn, 2), slogan=slogan_var(tam))
    except Exception as e:  # noqa: BLE001
        r["hata"] = f"{type(e).__name__} {str(e)[:120]}"
    return r


def beklenen_isle(arg):
    c, yol = arg
    try:
        sn, gri, tam = kareler(yol)
        return c, gri, round(sn, 2), slogan_var(tam)
    except Exception as e:  # noqa: BLE001
        log(f"  beklenen {c} okunamadi: {type(e).__name__}")
        return c, None, None, None


def esik_bul(kal, dler):
    """Esik: bilinen eski/yeni ciftin ortasi - ANCAK ikisi olculerek ayrisiyorsa (eski >= 2 x yeni). 26 Eyl olcumu:
    'bilinen eski' AQUARIUS_SCORPIO bu arada yenilenmis (0.146 ~ ARIES_LEO 0.144) -> kalibrasyon gecersiz; o zaman
    esik, olculen d dagiliminda alttan ilk >= 3 kat boslugun geometrik ortasi (yeni kume ust siniri; 26 Eyl:
    0.147 -> 0.636, esik ~0.31; medya olcumu 'dogru 0.30' ile tutarli)."""
    e, y = kal.get(KAL_ESKI), kal.get(KAL_YENI)
    if e is not None and y is not None and e >= 2 * max(y, 1e-6):
        return round((e + y) / 2, 3)
    d = sorted(x for x in dler if x is not None and x > 0)
    if len(d) < 2:
        sys.exit(f"DUR: esik kurulamadi {kal}")
    i = next((k for k in range(len(d) - 1) if d[k + 1] >= 3 * d[k]), None)
    if i is None:
        sys.exit(f"DUR: d dagiliminda >= 3 kat bosluk yok, esik kurulamadi {kal}")
    log(f"kalibrasyon ayrismiyor {kal}; en buyuk bosluk {d[i]} -> {d[i + 1]}")
    return round((d[i] * d[i + 1]) ** 0.5, 3)


def denetle(canli_json, a77, cl_v5):
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    C = json.loads(Path(canli_json).read_text())
    a77 = Path(a77)
    # beklenen videolar (A1_77/<CIFT>/VIDEO.mp4; CL icin v5)
    bek_yol = {p.parent.name: p for p in a77.glob("*/VIDEO.mp4")}
    if Path(cl_v5).exists():
        bek_yol[REF_CIFT] = Path(cl_v5)
    with Pool(os.cpu_count() or 2) as pool:
        B = {c: (g, sn, sl) for c, g, sn, sl in pool.map(beklenen_isle, sorted(bek_yol.items())) if g is not None}
        log(f"beklenen video: {len(B)} ({time.time() - t0:.0f} sn); eski slogan iceren beklenen: "
            f"{[c for c, v in B.items() if v[2]]}")
        R = {}
        isler = [(lid, x, "_canli") for lid, x in C.items()]
        for i, r in enumerate(pool.imap_unordered(canli_isle, isler), 1):
            R[r["ilan"]] = r
            gec = time.time() - t0
            log(f"[{i}/{len(isler)}] %{100 * i // len(isler)} gecen {gec / 60:.1f} dk, kalan ~{gec / i * (len(isler) - i) / 60:.1f} dk "
                f"({r['cift']})")

    # uzakliklar
    for lid, r in R.items():
        f = Path("_canli") / lid / "kare.npy"
        if not f.exists():
            continue
        g = np.load(f)
        dist = {c: uzaklik(g, v[0]) for c, v in B.items() if v[0].shape == g.shape}
        r["d_beklenen"] = dist.get(r["cift"])
        if dist:
            en = min(dist, key=dist.get)
            r["en_yakin"], r["d_en_yakin"] = en, dist[en]

    # kalibrasyon (0028 md.3)
    kal = {k: next((r.get("d_beklenen") for r in R.values() if r["cift"] == k), None) for k in (KAL_ESKI, KAL_YENI)}
    log(f"kalibrasyon: {KAL_ESKI} (eski) d={kal[KAL_ESKI]}, {KAL_YENI} (yeni) d={kal[KAL_YENI]}")
    esik = esik_bul(kal, [r["d_beklenen"] for r in R.values() if r.get("d_beklenen") is not None])
    log(f"video esigi: {esik}")

    satir = []
    for lid, r in sorted(R.items(), key=lambda kv: kv[1]["cift"]):
        c = r["cift"]
        if r.get("hata"):
            v = "HATA"
        elif not r["video_sayisi"]:
            v = "YOK"
        elif r.get("slogan"):
            v = "ESKI"
        elif c not in B:
            v = "BEKLENEN_YOK"
        elif r.get("en_yakin") and r["en_yakin"] != c and r["d_en_yakin"] < r["d_beklenen"]:
            v = "YANLIS_CIFT"
        elif r["d_beklenen"] is not None and r["d_beklenen"] <= esik and abs((r.get("sure") or 0) - 12.6) <= 0.3:
            v = "YENI"
        elif r["d_beklenen"] is not None and r["d_beklenen"] > 10 * esik:
            v = "ESKI"
        else:
            v = "FARKLI"                                  # ne beklenen ne eski slogan (or. CL canli 12.0 sn surum)
        kb = a77 / c / "TAM_SET" / "01_kapak_MB.jpg"
        if not r.get("kapak_yol"):
            k, kf = "YOK", None
        elif not kb.exists():
            k, kf = "BEKLENEN_YOK", None
        else:
            kf = fark256(Image.open(r["kapak_yol"]), Image.open(kb))
            k = "YENI" if kf <= 0.001 else "ESKI"
        satir.append({"ilan": lid, "cift": c, "video": v, "d_beklenen": r.get("d_beklenen"), "esik": esik,
                      "en_yakin": r.get("en_yakin"), "d_en_yakin": r.get("d_en_yakin"), "sure": r.get("sure"),
                      "eski_slogan": r.get("slogan"), "video_sayisi": r["video_sayisi"], "kapak": k, "kapak_fark": kf,
                      "foto": r["foto"], "hata": r.get("hata", "")})
    with open(OUT / "CANLI_VIDEO_KAPAK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(satir[0])); w.writeheader(); w.writerows(satir)
    say = lambda k: {v: sum(1 for s in satir if s[k] == v) for v in sorted({s[k] for s in satir})}  # noqa: E731
    oz = {"ilan": len(satir), "video": say("video"), "kapak": say("kapak"), "esik": esik, "kalibrasyon": kal,
          "beklenen_video": len(B), "sure_dk": round((time.time() - t0) / 60, 1),
          "video_yeni_degil": [f"{s['cift']}:{s['video']}" for s in satir if s["video"] != "YENI"][:80]}
    (OUT / "CANLI_VIDEO_KAPAK_OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1))
    log("OZET " + json.dumps(oz, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "etsy":
        etsy(sys.argv[2], sys.argv[3])
    else:
        denetle(sys.argv[2], sys.argv[3], sys.argv[4])
