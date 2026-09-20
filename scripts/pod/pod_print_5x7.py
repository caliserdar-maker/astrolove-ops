#!/usr/bin/env python3
"""5x7 (GLOBAL-HPR-5x7, 13x18 cm) baski dosyalari: 78 cift x 5 edisyon = 390 JPEG.

Kaynak: ORIGINAL_HIGH_RES/<ED>/A_SERIES/<PAIR>.jpg (ISO ustasi, 10962x15503).
Yontem: YALNIZ dikey merkez kirpma (usta cozunurlugu korunur, yeniden boyutlandirma yok);
hedef oran Prodigi 5x7 baski alanindan (1535x2125 -> 0.72235). Oran farki toleransi bu
boy icin 0.025 (diger boylar pod_print_build.py'de 0.01 kalir).
Kontrol: kirpilan ust/alt bantlarda zemin disi piksel yoksa GECTI (bant medyani + sapma).
Cikti: <out>/<PAIR>/<ED>/5x7.jpg -> Drive TEMP/POD_PRINT/<PAIR>/<ED>/5x7.jpg, satir satir CSV.
"""
import argparse
import csv
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
RATIO_TOL_5X7 = 0.025
BOY = "5x7"
# Zemin olcutu: kirpilan bandin hemen ICINDEKI ayni yukseklikteki serit "zemin" kabul edilir
# (tasarim bu seride de yok). Bant, bu seridin dagilimiyla karsilastirilir:
#   ink = |piksel - serit_medyani| > INK esigi  -> tasarim/mureккep sayilir
#   parlaklik kaymasi |bant_ort - serit_ort| > KAYMA -> gorunur ton farki
INK, KAYMA = 40, 3.0
BLOK = (32, 128)     # blok ortalamasi (satir, sutun): doku ortalanir, tasarim (yogun mürekkep) kalir
BLOK_K = 4.0         # blok sapmasi esigi = max(2.0, BLOK_K * serit_blok_std)
# KAPI (20 Eyl olcumu): kirpilan bantlar CIFTE OZGU icerik tasimamali. Bantlar tum ciftlerde
# ayni arka plan plakasidir (DEEP_BLACK yildiz dokusu, WARM_PARCHMENT kagit dokusu; tani
# goruntuleri TEMP/POD_5X7/TANI). Tasarim (halka, semboller, isimler, "Two Souls One Bond")
# cifte ozgudur: bant blok haritasi edisyonun REFERANS ciftininkinden saparsa tasarim girmis
# demektir. Esik: blok basina <= 1.0 luma.
# Esik arka plan degiskenligine gore olceklenir: WARM_PARCHMENT dokusu ciftten cifte degisir
# (olculen), MB/DB/CI plakalari birebir ayni. Tasarim girerse blok farki 40+ luma olur.
REF_K, REF_TABAN = 2.0, 2.0
CSV_SUT = ["pair", "edition", "dosya", "usta_px", "kirp_px", "kirpma_px",
           "ust_ink_px", "alt_ink_px", "ust_max_sapma", "alt_max_sapma",
           "ust_kayma", "alt_kayma", "serit_std", "ust_blok_sapma", "alt_blok_sapma",
           "blok_esik", "blok_ustu", "ref_sapma", "ref_esik", "bayt", "sn", "durum", "neden"]
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def sure(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise RuntimeError(f"rclone {a[0]} {a[1] if len(a) > 1 else ''}: {r.stderr.strip()[-200:]}")
    return r


def hedef_oran(sizes_json):
    """Prodigi 5x7 baski alani -> (w_px, h_px, oran)."""
    d = json.loads(pathlib.Path(sizes_json).read_text(encoding="utf-8"))
    v = d.get(BOY) or d.get("5X7")
    if not v:
        raise SystemExit(f"HATA: {sizes_json} icinde {BOY} yok")
    w, h = int(v["w"]), int(v["h"])
    return w, h, w / h


def bloklar(a):
    """Blok ortalamalari (luma) -> doku ortalanir."""
    h, w = a.shape[0] - a.shape[0] % BLOK[0], a.shape[1] - a.shape[1] % BLOK[1]
    luma = a[:h, :w].astype(np.float32).mean(axis=2)
    return luma.reshape(h // BLOK[0], BLOK[0], w // BLOK[1], BLOK[1]).mean(axis=(1, 3))


def yapi_kontrol(bant, serit):
    """Blok duzeyinde tasarim izi -> (max_blok_sapma, esik, blok_ustu_sayi)."""
    if bant.size == 0 or serit.size == 0:
        return 0.0, 0.0, 0
    b, r = bloklar(bant), bloklar(serit)
    ort, std = float(r.mean()), float(r.std())
    esik = max(2.0, BLOK_K * std)
    sap = np.abs(b - ort)
    return round(float(sap.max()), 2), round(esik, 2), int((sap > esik).sum())


def bant_kontrol(bant, serit):
    """Bandi komsu zemin seridiyle kiyasla -> (ink_px, max_sapma, kayma, serit_std)."""
    if bant.size == 0 or serit.size == 0:
        return 0, 0, 0.0, 0.0
    med = np.median(serit.reshape(-1, serit.shape[-1]), axis=0)
    fark = np.abs(bant.astype(np.int16) - med.astype(np.int16)).max(axis=2)
    kayma = float(abs(bant.reshape(-1, bant.shape[-1]).mean(0).mean()
                      - serit.reshape(-1, serit.shape[-1]).mean(0).mean()))
    return int((fark > INK).sum()), int(fark.max()), round(kayma, 2), round(float(serit.std()), 2)


def _germe(arr):
    """Kontrast germe: bandin kendi min-max araligi 0-255'e acilir (yapi gorunur olsun)."""
    a = arr.astype(np.float32)
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    if hi - lo < 1e-3:
        hi = lo + 1
    return Image.fromarray(np.clip((a - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8))


def tani(im, y0, nh, dizin, ad):
    """Tani: ust bant (ham + gerilmis) | ust serit || alt serit | alt bant; sapan bloklar kirmizi."""
    from PIL import ImageDraw
    sw, sh = im.size
    alt_h = sh - (y0 + nh)
    a = np.asarray(im)
    parcalar = [("ust_bant", a[:y0]), ("ust_serit", a[y0:y0 + y0]),
                ("alt_serit", a[y0 + nh - alt_h:y0 + nh]), ("alt_bant", a[y0 + nh:])]
    g = 1400
    katlar = []
    for ad2, arr in parcalar:
        ham = Image.fromarray(arr).resize((g, max(1, round(g * arr.shape[0] / arr.shape[1]))), Image.LANCZOS)
        ger = _germe(arr).resize(ham.size, Image.LANCZOS).convert("RGB")
        katlar.append((ad2, ham, ger))
    yuk = sum(h.size[1] + ge.size[1] + 22 for _, h, ge in katlar) + 20
    tuval = Image.new("RGB", (g, yuk), (250, 250, 250))
    d = ImageDraw.Draw(tuval)
    y = 6
    for ad2, ham, ger in katlar:
        tuval.paste(ham, (0, y)); y += ham.size[1] + 2
        tuval.paste(ger, (0, y)); y += ger.size[1] + 4
        d.text((6, y), f"{ad2} (ust: ham, alt: kontrast gerilmis)", fill=(180, 0, 0)); y += 16
    dizin.mkdir(parents=True, exist_ok=True)
    tuval.save(dizin / f"BANT_{ad}.jpg", "JPEG", quality=90, optimize=True)


def sapan_bloklar(bant, serit, n=3):
    """En cok sapan bloklarin (satir, sutun, sapma) listesi — konum teshisi icin."""
    if bant.size == 0 or serit.size == 0:
        return []
    b, r = bloklar(bant), bloklar(serit)
    sap = np.abs(b - float(r.mean()))
    idx = np.dstack(np.unravel_index(np.argsort(-sap, axis=None), sap.shape))[0][:n]
    return [(int(i), int(j), round(float(sap[i, j]), 1),
             f"px y~{int(i) * BLOK[0]}-{(int(i) + 1) * BLOK[0]}, x~{int(j) * BLOK[1]}-{(int(j) + 1) * BLOK[1]}")
            for i, j in idx]


def uret(usta_yol, cikti_yol, oran, tani_dizin=None, tani_ad="", referans=None):
    """Kirp + kaydet. Donus: satir sozlugu."""
    t0 = time.time()
    im = Image.open(usta_yol)
    im.draft(None, None)
    im = im.convert("RGB")
    sw, sh = im.size
    fark = abs((sw / sh) / oran - 1)
    if fark > RATIO_TOL_5X7:
        raise ValueError(f"oran {sw}x{sh} ({sw / sh:.4f}) hedef {oran:.4f} fark %{fark * 100:.2f}")
    nh = round(sw / oran)
    if nh > sh:
        raise ValueError(f"hedef yukseklik {nh} > usta {sh}")
    y0 = (sh - nh) // 2
    a = np.asarray(im)
    ust_i, ust_s, ust_k, std1 = bant_kontrol(a[:y0], a[y0:y0 + y0])
    alt_h = sh - (y0 + nh)
    alt_i, alt_s, alt_k, std2 = bant_kontrol(a[y0 + nh:], a[y0 + nh - alt_h:y0 + nh])
    ust_b, ust_e, ust_n = yapi_kontrol(a[:y0], a[y0:y0 + y0])
    alt_b, alt_e, alt_n = yapi_kontrol(a[y0 + nh:], a[y0 + nh - alt_h:y0 + nh])
    harita = (bloklar(a[:y0]), bloklar(a[y0 + nh:]))
    ref_sapma = ref_esik = None
    if referans is not None:
        ref_sapma = round(float(max(np.abs(harita[0] - referans[0]).max(),
                                    np.abs(harita[1] - referans[1]).max())), 2)
        ref_esik = round(max(REF_TABAN, REF_K * float(max(referans[0].std(), referans[1].std()))), 2)
    if tani_dizin is not None:
        tani(im, y0, nh, tani_dizin, tani_ad)
        log(f"  {tani_ad} ust bant sapan bloklar: {sapan_bloklar(a[:y0], a[y0:y0 + y0])}")
        log(f"  {tani_ad} alt bant sapan bloklar: "
            f"{sapan_bloklar(a[y0 + nh:], a[y0 + nh - alt_h:y0 + nh])}")
    kirp = im.crop((0, y0, sw, y0 + nh))
    dpi = round(kirp.size[0] / (1535 / 300.0))
    cikti_yol.parent.mkdir(parents=True, exist_ok=True)
    kirp.save(cikti_yol, "JPEG", quality=95, subsampling=0, dpi=(dpi, dpi), optimize=True)
    # GECTI: blok duzeyinde tasarim izi yok (doku/vinyet bloklarda ortalanir) ve ton kaymasi kucuk
    # KAPI: cifte ozgu icerik yok (referans bant haritasina esit) -> GECTI.
    gecti = (ref_sapma is not None and ref_sapma <= ref_esik) if referans is not None else \
            (ust_n == 0 and alt_n == 0 and ust_k <= KAYMA and alt_k <= KAYMA)
    return {"usta_px": f"{sw}x{sh}", "kirp_px": f"{kirp.size[0]}x{kirp.size[1]}",
            "kirpma_px": sh - nh, "ust_ink_px": ust_i, "alt_ink_px": alt_i,
            "ust_max_sapma": ust_s, "alt_max_sapma": alt_s, "ust_kayma": ust_k,
            "alt_kayma": alt_k, "serit_std": max(std1, std2),
            "ust_blok_sapma": ust_b, "alt_blok_sapma": alt_b, "blok_esik": max(ust_e, alt_e),
            "blok_ustu": ust_n + alt_n,
            "ref_sapma": ref_sapma if ref_sapma is not None else "",
            "ref_esik": ref_esik if ref_esik is not None else "",
            "_harita": harita,
            "bayt": cikti_yol.stat().st_size, "sn": round(time.time() - t0, 1),
            "durum": "GECTI" if gecti else "KONTROL", "neden": ""}


def onizleme(dosyalar, yol):
    """5 edisyon yan yana, gercek 5x7 orani, telefonda okunur, <= 1 MB."""
    from PIL import ImageDraw
    pw = 560
    paneller = []
    for ed, p in dosyalar:
        im = Image.open(p)
        im.draft("RGB", (pw * 2, pw * 2))
        im = im.convert("RGB")
        ph = round(pw * im.size[1] / im.size[0])
        paneller.append((ed, im.resize((pw, ph), Image.LANCZOS)))
    bosluk, kenar, alt = 36, 40, 60
    gen = kenar * 2 + len(paneller) * pw + bosluk * (len(paneller) - 1)
    yuk = kenar * 2 + max(p.size[1] for _, p in paneller) + alt
    tuval = Image.new("RGB", (gen, yuk), (247, 246, 243))
    d = ImageDraw.Draw(tuval)
    x = kenar
    for ed, p in paneller:
        tuval.paste(p, (x, kenar))
        d.rectangle([x, kenar, x + p.size[0] - 1, kenar + p.size[1] - 1], outline=(140, 140, 140))
        d.text((x + p.size[0] // 2, kenar + p.size[1] + 18), ed.replace("_", " "),
               fill=(25, 25, 25), anchor="ma")
        x += pw + bosluk
    d.text((kenar, yuk - 26), "5x7 in / 13x18 cm - ISO ustasindan dikey kirpma (164/164 px)",
           fill=(70, 70, 70), anchor="lm")
    for q in (88, 82, 74, 66):
        tuval.save(yol, "JPEG", quality=q, optimize=True)
        if yol.stat().st_size <= 1_000_000:
            break
    log(f"ONIZLEME_5X7.jpg {tuval.size[0]}x{tuval.size[1]} {yol.stat().st_size / 1024:.0f} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--sizes-json", required=True)
    ap.add_argument("--src", default="src")
    ap.add_argument("--out", default="out")
    ap.add_argument("--state", required=True)
    ap.add_argument("--csv", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="")
    ap.add_argument("--rclone-out", default="")
    ap.add_argument("--onizleme-cift", default="")
    ap.add_argument("--onizleme-drv", default="gdrive:ASTROLOVE/TEMP/POD_5X7")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tani", action="store_true", help="kirpilan bant tani goruntusu uret")
    a = ap.parse_args()

    w, h, oran = hedef_oran(a.sizes_json)
    ciftler = [l.strip().upper() for l in pathlib.Path(a.pairs_file).read_text(encoding="utf-8").splitlines()
               if l.strip() and not l.startswith("#")]
    ciftler = sorted(dict.fromkeys(ciftler))
    benim = [p for i, p in enumerate(ciftler) if i % a.shards == a.shard]
    durum_yol = pathlib.Path(a.state)
    durum = {}
    if durum_yol.exists():
        for r in csv.DictReader(durum_yol.open(encoding="utf-8")):
            durum[r["pair"]] = r
    todo = [p for p in benim if a.force or durum.get(p, {}).get("status") != "PASS"]
    log(f"shard {a.shard}/{a.shards}: {len(benim)} cift, {len(todo)} islenecek | hedef oran "
        f"{oran:.5f} ({w}x{h}) | tolerans {RATIO_TOL_5X7}")

    csv_yol = pathlib.Path(a.csv or (durum_yol.parent / f"URETIM_5X7_shard{a.shard}.csv"))
    if not csv_yol.exists():
        with csv_yol.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(CSV_SUT)
    onizleme_dosyalari = []
    referanslar = {}          # edisyon -> (ust_blok_haritasi, alt_blok_haritasi)
    t0, n_ok, n_fail = time.time(), 0, 0
    for i, cift in enumerate(todo, start=1):
        tp = time.time()
        hatalar, satirlar, uretilen = [], [], 0
        for ed in EDITIONS:
            usta = pathlib.Path(a.src) / ed / "A_SERIES" / f"{cift}.jpg"
            if a.rclone_src:
                usta.parent.mkdir(parents=True, exist_ok=True)
                r = rclone("copyto", f"{a.rclone_src}/{ed}/A_SERIES/{cift}.jpg", str(usta), sert=False)
                if r.returncode != 0 or not usta.exists():
                    hatalar.append(f"{ed}: usta inmedi")
                    continue
            if not usta.exists():
                hatalar.append(f"{ed}: usta yok")
                continue
            cikti = pathlib.Path(a.out) / cift / ed / f"{BOY}.jpg"
            try:
                s = uret(usta, cikti, oran,
                         tani_dizin=(pathlib.Path(a.out) / "_tani") if a.tani else None,
                         tani_ad=f"{cift}_{ed}", referans=referanslar.get(ed))
            except Exception as e:  # noqa: BLE001
                hatalar.append(f"{ed}: {type(e).__name__}: {e}")
                usta.unlink(missing_ok=True)
                continue
            if ed not in referanslar:
                referanslar[ed] = s.pop("_harita")
                s["durum"], s["neden"] = "REFERANS", "edisyonun ilk cifti: bant referansi"
            else:
                s.pop("_harita", None)
            s.update({"pair": cift, "edition": ed, "dosya": f"{cift}/{ed}/{BOY}.jpg"})
            if s["durum"] not in ("GECTI", "REFERANS"):
                hatalar.append(f"{ed}: bant referans sapmasi {s.get('ref_sapma')} (esik {s.get('ref_esik')}); blok {s['blok_ustu']} "
                               f"(sapma {s['ust_blok_sapma']}/{s['alt_blok_sapma']} esik {s['blok_esik']}, "
                               f"kayma {s['ust_kayma']}/{s['alt_kayma']})")
            satirlar.append(s)
            if a.onizleme_cift and cift == a.onizleme_cift.upper():
                onizleme_dosyalari.append((ed, cikti))
            if a.rclone_out and not (a.onizleme_cift and cift == a.onizleme_cift.upper()):
                rclone("copyto", str(cikti), f"{a.rclone_out}/{cift}/{ed}/{BOY}.jpg")
                cikti.unlink(missing_ok=True)
            usta.unlink(missing_ok=True)
            uretilen += 1
        with csv_yol.open("a", newline="", encoding="utf-8") as fh:
            wcsv = csv.DictWriter(fh, fieldnames=CSV_SUT, extrasaction="ignore")
            for s in satirlar:
                wcsv.writerow(s)
        ok = uretilen == len(EDITIONS) and not hatalar
        durum[cift] = {"pair": cift, "status": "PASS" if ok else "FAIL", "files": uretilen,
                       "fail": "; ".join(hatalar)[:300], "secs": round(time.time() - tp, 1),
                       "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with durum_yol.open("w", newline="", encoding="utf-8") as fh:
            wcsv = csv.DictWriter(fh, fieldnames=["pair", "status", "files", "fail", "secs", "ts_utc"])
            wcsv.writeheader()
            for k in sorted(durum):
                wcsv.writerow({c: durum[k].get(c, "") for c in
                               ["pair", "status", "files", "fail", "secs", "ts_utc"]})
        n_ok += ok
        n_fail += (not ok)
        gec = time.time() - t0
        log(f"{i}/{len(todo)} (%{100 * i / len(todo):.1f}) {cift} {'PASS' if ok else 'FAIL'} "
            f"{uretilen}/5 dosya {('; '.join(hatalar))[:60]} | gecen {sure(gec)} "
            f"| kalan ~{sure(gec / i * (len(todo) - i))}")

    if a.onizleme_cift and onizleme_dosyalari:
        yol = pathlib.Path(a.out) / "ONIZLEME_5X7.jpg"
        onizleme(sorted(onizleme_dosyalari, key=lambda t: EDITIONS.index(t[0])), yol)
        rclone("copyto", str(yol), f"{a.onizleme_drv}/ONIZLEME_5X7.jpg")
        for ed, p in onizleme_dosyalari:
            if a.rclone_out:
                rclone("copyto", str(p), f"{a.rclone_out}/{a.onizleme_cift.upper()}/{ed}/{BOY}.jpg")
                p.unlink(missing_ok=True)
    if a.tani and (pathlib.Path(a.out) / "_tani").exists():
        rclone("copy", str(pathlib.Path(a.out) / "_tani"), "gdrive:ASTROLOVE/TEMP/POD_5X7/TANI",
               "--include", "*.jpg", sert=False)
    if a.rclone_out:
        rclone("copyto", str(csv_yol), f"gdrive:ASTROLOVE/TEMP/POD_5X7/parca/{csv_yol.name}")
    print(json.dumps({"shard": a.shard, "pass": n_ok, "fail": n_fail,
                      "dosya_csv": str(csv_yol)}, ensure_ascii=False))
    return 0                     # kapi sonuclari CSV/STATE'te; kosu tek cift icin durmaz


if __name__ == "__main__":
    sys.exit(main())
