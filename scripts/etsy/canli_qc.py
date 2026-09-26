#!/usr/bin/env python3
"""GOREV 0019 - CANLI gorsel/video BAGIMSIZ QC (SALT OKUMA, Etsy'ye yazma YOK).
Galeri yuklemesi PASS olan POD ilanlari (A1_77/_galeri/GALERI_TAMSET*.json) canli halinden olculur;
referans: canli Cancer-Libra 4570143815 (foto rank n = CL n).
 K1 DOGRU FOTO : 13 foto; rank i canli foto ile A1_77/<CIFT>/TAM_SET/SET.json sira i dosyasi 256px gri ort. fark <= 0.001.
 K2 YAZI       : kapak/kart fotolarinda tesseract OCR; referansin ayni CL karesi (Cancer/Libra -> ciftin burclari) ile
                 normalize metin ayni mi; "ASTROLOVE / A + B" satiri ciftin burclari mi; uzun/orta tire yok mu.
 K3 RENK       : 5 renk gorseli (+kapak MB) orta bolge medyan Lab, referansin ayni renk gorseline delta E76 <= 3.
 K4 IZ/LEKE    : referansin ayni CL karesiyle fark haritasi; esik referans CL ilaninin kendi TAM_SET'iyle olculur
                 (Etsy yeniden sikistirma gurultusu, gevsetme yok); cifte ozel bolgeler = ilanlarin >= %30'unda farkli
                 pikseller (sembol, burc adlari). Kalan bilesen >= ALAN_MIN -> supheli, 3x kirpim. n < 5 ise OLCULEMEDI.
 K5 VIDEO      : video 1; sure 12.6 +- 0.3 sn; cozunurluk; A1_77 onayli video ile ilk/orta/son kare 256px gri fark <= 0.02.
Cikti: out/CANLI_QC.csv, out/kirpim/*.jpg, out/CANLI_SERIT.jpg. Kota tabani 230; cagri siniri 300.
Kullanim: canli_qc.py <galeri_json[,galeri_json2]> <metin78_csv> <isdir>"""
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

REF_ID, REF_A, REF_B = "4570143815", "Cancer", "Libra"
A77 = "gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77"
KOTA_TABAN, CAGRI_SINIR = 230, 300
ESIK_FOTO, ESIK_DE, ESIK_VIDEO, VIDEO_SN = 0.001, 3.0, 0.02, 12.6
W4, ALAN_MIN, SIKLIK, N_MIN = 500, 40, 0.30, 5
BURC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
        "Aquarius", "Pisces"]
OUT = Path("out")


def rc(*a):
    return subprocess.run(["rclone", *a], check=True, capture_output=True, text=True).stdout


def indir(url):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def gri256(im):
    return np.asarray(im.convert("L").resize((256, 256), Image.BILINEAR), dtype=float)


def fark256(a, b):
    return round(float(np.abs(gri256(a) - gri256(b)).mean() / 255), 4)


def ocr(im):
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        k = im.convert("L")
        if k.width < 2000:
            k = k.resize((2000, round(k.height * 2000 / k.width)), Image.LANCZOS)
        k.save(f.name)
        return subprocess.run(["tesseract", f.name, "-", "--psm", "3", "-l", "eng"], capture_output=True, text=True).stdout


def norm(t):
    t = t.upper().replace("—", " <UZUNTIRE> ").replace("–", " <ORTATIRE> ")
    return " ".join(re.sub(r"[^A-Z0-9&+/<> ]", " ", t).split())


def burc_degis(t, a, b):
    t = re.sub(r"\bCANCER\b", "\x00A", t)
    t = re.sub(r"\bLIBRA\b", "\x00B", t)
    return t.replace("\x00A", a.upper()).replace("\x00B", b.upper())


def lab(rgb):
    c = np.asarray(rgb, dtype=float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    x, y, z = (np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ c) / \
        np.array([0.95047, 1.0, 1.08883])
    f = lambda v: v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116  # noqa: E731
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def orta_lab(im):
    w, h = im.size
    a = np.asarray(im.convert("RGB").crop((int(w * .3), int(h * .25), int(w * .7), int(h * .75))), dtype=float)
    return lab(np.median(a.reshape(-1, 3), axis=0))


def kucuk(im, w=W4):
    g = im.convert("L").resize((w, round(im.height * w / im.width)), Image.BILINEAR)
    return ndimage.gaussian_filter(np.asarray(g, dtype=float), 1.5)


def kare(yol, t):
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(yol), "-frames:v", "1", f.name], check=True)
        return Image.open(f.name).copy()


def video_bilgi(yol):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(yol)], capture_output=True, text=True)
    d = json.loads(p.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return float((d.get("format") or {}).get("duration") or 0), s.get("width"), s.get("height")


def cift_anahtar(metin):
    ad = [b.upper() for b in re.findall(r"[A-Za-z]+", metin or "") if b.capitalize() in BURC]
    return "_".join(sorted(ad)) if len(ad) == 2 else ("_".join(ad * 2) if len(ad) == 1 else "")


def main():
    galeri_json, metin78, isdir = sys.argv[1].split(","), sys.argv[2], Path(sys.argv[3])
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    (OUT / "kirpim").mkdir(parents=True, exist_ok=True)

    def get(path):
        if api.calls >= CAGRI_SINIR:
            sys.exit(f"DUR: cagri siniri {CAGRI_SINIR}")
        r = api.get(path, ok404=True) or {}
        if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
            sys.exit(f"DUR: kota {api.remaining} < {KOTA_TABAN}")
        return r

    cift_ad = {r["ilan_id"]: r.get("cift", "") for r in csv.DictReader(open(metin78, encoding="utf-8"))}
    hedef = {}
    for g in galeri_json:
        if Path(g).exists():
            for c, x in (json.loads(Path(g).read_text()).get("ilan") or {}).items():
                if x.get("sonuc") == "PASS" and x.get("ilan_id"):
                    hedef[c] = str(x["ilan_id"])
    print(f"galeri PASS ilan: {len(hedef)} {sorted(hedef)}", flush=True)

    # referans (canli CL) + CL TAM_SET (gurultu esigi)
    R = {x["rank"]: Image.open(io.BytesIO(indir(x["url_fullxfull"]))).convert("RGB")
         for x in (get(f"/listings/{REF_ID}/images").get("results") or [])}
    ref_ocr = {n: norm(ocr(im)) for n, im in R.items()}
    cl_dir = isdir / "CANCER_LIBRA"
    esik = None
    try:
        rc("copy", f"{A77}/CANCER_LIBRA/TAM_SET", str(cl_dir), "--include", "[01][0-9]_*.jpg", "--include", "SET.json")
        CL = json.loads((cl_dir / "SET.json").read_text())
        gur = [np.percentile(np.abs(kucuk(Image.open(cl_dir / g["dosya"]).convert("RGB")) - kucuk(R[g["cl_karsiligi"]])), 99.9)
               for g in CL["galeri"] if g["cl_karsiligi"] in R]
        esik = max(8.0, float(max(gur)) * 1.5) if gur else None
    except Exception as e:  # noqa: BLE001
        print(f"CL TAM_SET gurultu olculemedi: {type(e).__name__}", flush=True)
    print(f"K4 piksel esigi (CL kendi gurultusu p99.9 x1.5): {esik}", flush=True)

    satir, fark4, serit = {}, {}, []
    for c, lid in sorted(hedef.items()):
        a, b = (re.findall(r"[A-Za-z]+", cift_ad.get(lid, "")) + c.split("_"))[:2]
        a, b = a.capitalize(), b.capitalize()
        d = isdir / c
        r = {"ilan_id": lid, "cift": f"{a} + {b}"}
        try:
            rc("copy", f"{A77}/{c}/TAM_SET", str(d), "--include", "[01][0-9]_*.jpg", "--include", "SET.json")
            SET = json.loads((d / "SET.json").read_text())
        except Exception as e:  # noqa: BLE001
            r["hata"] = f"TAM_SET indirilemedi {type(e).__name__}"; satir[c] = r; continue
        imgs = sorted(get(f"/listings/{lid}/images").get("results") or [], key=lambda x: x.get("rank") or 0)
        vids = get(f"/listings/{lid}/videos").get("results") or []
        L = {x["rank"]: Image.open(io.BytesIO(indir(x["url_fullxfull"]))).convert("RGB") for x in imgs}
        gal = {g["sira"]: g for g in SET["galeri"]}
        # K1
        f1 = {i: fark256(L[i], Image.open(d / gal[i]["dosya"])) for i in gal if i in L}
        k1 = len(L) == 13 and len(f1) == 13 and all(v <= ESIK_FOTO for v in f1.values())
        r.update(K1_foto="PASS" if k1 else "FAIL", K1_deger=f"foto {len(L)}; max fark {max(f1.values(), default=None)}; "
                 f"asan {[i for i, v in f1.items() if v > ESIK_FOTO]}")
        # K2
        hat = []
        for i, g in gal.items():
            if g.get("tur") not in ("kapak", "kart") or i not in L or g["cl_karsiligi"] not in ref_ocr:
                continue
            t = norm(ocr(L[i]))
            bek = burc_degis(ref_ocr[g["cl_karsiligi"]], a, b)
            bek2 = burc_degis(ref_ocr[g["cl_karsiligi"]], b, a)
            if "<UZUNTIRE>" in t or "<ORTATIRE>" in t:
                hat.append(f"#{i} tire")
            m = re.search(r"ASTROLOVE\s*/\s*([A-Z]+)\s*\+\s*([A-Z]+)", t)
            if "ASTROLOVE /" in ref_ocr[g["cl_karsiligi"]] and (not m or sorted(m.groups()) != sorted([a.upper(), b.upper()])):
                hat.append(f"#{i} baslik {m.groups() if m else 'OKUNAMADI'}")
            if t not in (bek, bek2):
                import difflib
                sm = difflib.SequenceMatcher(None, bek, t)
                op = next((o for o in sm.get_opcodes() if o[0] != "equal"), None)
                hat.append(f"#{i} metin oran {sm.ratio():.3f}" + (f" ref '{bek[op[1]:op[2]][:30]}' / canli '{t[op[3]:op[4]][:30]}'" if op else ""))
        r.update(K2_yazi="PASS" if not hat else "FAIL", K2_deger=" | ".join(hat)[:700])
        # K3
        de = {}
        for i, g in gal.items():
            if g.get("renk") and i in L and g["cl_karsiligi"] in R:
                de[g["renk"]] = round(float(np.linalg.norm(orta_lab(L[i]) - orta_lab(R[g["cl_karsiligi"]]))), 2)
        r.update(K3_renk="PASS" if len(de) == 5 and all(v <= ESIK_DE for v in de.values()) else "FAIL", K3_deger=json.dumps(de))
        # K4 (fark haritalari; karar tum ilanlar okununca)
        if esik is not None:
            for i, g in gal.items():
                if i in L and g["cl_karsiligi"] in R:
                    ref4 = kucuk(R[g["cl_karsiligi"]])
                    can4 = kucuk(L[i].resize(R[g["cl_karsiligi"]].size, Image.BILINEAR))
                    fark4[(c, i)] = (np.abs(can4 - ref4) > esik)
        # K5
        v = []
        if len(vids) != 1:
            v.append(f"video sayisi {len(vids)}")
        if vids and (SET.get("video") or {}).get("yol"):
            try:
                cv, sv = d / "CANLI.mp4", d / "ONAYLI.mp4"
                cv.write_bytes(indir(vids[0].get("video_url")))
                rc("copyto", SET["video"]["yol"], str(sv))
                sn, w, h = video_bilgi(cv)
                sn2, _, _ = video_bilgi(sv)
                fk = [fark256(kare(cv, t * sn), kare(sv, t * sn2)) for t in (0.05, 0.5, 0.95)]
                if abs(sn - VIDEO_SN) > 0.3:
                    v.append(f"sure {sn:.2f}")
                if max(fk) > ESIK_VIDEO:
                    v.append(f"kare fark {fk}")
                r["K5_bilgi"] = f"{sn:.2f} sn {w}x{h}; kare fark {fk}"
            except Exception as e:  # noqa: BLE001
                v.append(f"video olculemedi {type(e).__name__}")
        elif vids:
            v.append("onayli video yolu yok (SET.json)")
        r.update(K5_video="PASS" if not v else "FAIL", K5_deger="; ".join(v) or r.get("K5_bilgi", ""))
        # serit: 1. foto + 5 renk
        kutu = [L[i].copy() for i in [1] + [i for i, g in gal.items() if g.get("renk") and i != 1] if i in L][:6]
        for im in kutu:
            im.thumbnail((220, 220))
        serit.append((c, kutu))
        satir[c] = r
        print(f"{c}: K1 {r['K1_foto']} K2 {r['K2_yazi']} K3 {r['K3_renk']} K5 {r['K5_video']} | cagri {api.calls} kota {api.remaining}", flush=True)

    # K4 karar
    ilanlar = sorted({c for c, _ in fark4})
    for c in satir:
        satir[c].setdefault("K4_leke", "OLCULEMEDI")
        satir[c].setdefault("K4_deger", "")
    if esik is not None and len(ilanlar) >= N_MIN:
        for c in ilanlar:
            sup = []
            for (cc, i), m in fark4.items():
                if cc != c:
                    continue
                es = [fark4[(x, i)] for x in ilanlar if (x, i) in fark4 and fark4[(x, i)].shape == m.shape]
                sik = ndimage.binary_dilation(np.mean(es, axis=0) >= SIKLIK, iterations=8)
                kalan = m & ~sik
                lb, n = ndimage.label(kalan)
                for j, sl in enumerate(ndimage.find_objects(lb), 1):
                    alan = int((lb[sl] == j).sum())
                    if alan >= ALAN_MIN:
                        sup.append((i, sl, alan))
            satir[c]["K4_leke"] = "PASS" if not sup else "FAIL"
            satir[c]["K4_deger"] = f"supheli {len(sup)}: " + ", ".join(f"#{i} alan {al}" for i, _, al in sup[:8])
            for k, (i, sl, _) in enumerate(sup[:10]):
                d = isdir / c
                g = {g["sira"]: g for g in json.loads((d / "SET.json").read_text())["galeri"]}
                src = Image.open(d / g[i]["dosya"]).convert("RGB")
                sx = src.width / W4
                x0, x1 = max(0, int(sl[1].start * sx) - 40), min(src.width, int(sl[1].stop * sx) + 40)
                y0, y1 = max(0, int(sl[0].start * sx) - 40), min(src.height, int(sl[0].stop * sx) + 40)
                kr = src.crop((x0, y0, x1, y1))
                kr.resize((kr.width * 3, kr.height * 3), Image.LANCZOS).save(OUT / "kirpim" / f"{c}_{i:02d}_{k}.jpg", quality=90)
    elif esik is not None:
        for c in satir:
            satir[c]["K4_deger"] = f"n={len(ilanlar)} < {N_MIN}: cifte ozel bolge sikligi olculemez"

    alan = ["ilan_id", "cift", "K1_foto", "K1_deger", "K2_yazi", "K2_deger", "K3_renk", "K3_deger", "K4_leke", "K4_deger",
            "K5_video", "K5_deger", "hata"]
    with open(OUT / "CANLI_QC.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan, extrasaction="ignore")
        w.writeheader()
        for c in sorted(satir):
            w.writerow(satir[c])
    if serit:
        T = Image.new("RGB", (6 * 230 + 260, 240 * len(serit)), "white")
        dr = ImageDraw.Draw(T)
        for y, (c, ims) in enumerate(serit):
            dr.text((8, y * 240 + 100), c, fill=(0, 0, 0))
            for x, im in enumerate(ims):
                T.paste(im, (260 + x * 230, y * 240 + 10))
        T.save(OUT / "CANLI_SERIT.jpg", quality=88)
    oz = {k: f"{sum(1 for r in satir.values() if r.get(k) == 'PASS')}/{len(satir)}" for k in ("K1_foto", "K2_yazi", "K3_renk", "K4_leke", "K5_video")}
    oz["fail"] = {k: [c for c, r in satir.items() if r.get(k) == "FAIL"] for k in ("K1_foto", "K2_yazi", "K3_renk", "K4_leke", "K5_video")}
    print("OZET " + json.dumps({**oz, "cagri": api.calls, "kota_son": api.remaining, "k4_esik": esik}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
