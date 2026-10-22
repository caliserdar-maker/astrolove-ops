#!/usr/bin/env python3
"""GOREV 0019 - CANLI gorsel/video BAGIMSIZ QC (SALT OKUMA, Etsy'ye yazma YOK).
Galeri yuklemesi PASS olan POD ilanlari (A1_77/_galeri/GALERI_TAMSET*.json) canli halinden olculur;
referans: canli Cancer-Libra 4570143815 (foto rank n = CL n).
 K1 DOGRU FOTO : 13 foto; rank i canli foto ile A1_77/<CIFT>/TAM_SET/SET.json sira i dosyasi 256px gri ort. fark <= 0.001.
 K2 YAZI       : kapak/kart fotolarinda tesseract OCR (TSV, kelime guveni); referans = onayli CL TAM_SET ayni karesi
                 (Cancer/Libra -> ciftin burclari). Kelime farki: bir tarafta guvenle (conf >= 80) okunan >= 3 harfli
                 kelime diger tarafin HAM okumasinda hic yok -> FAIL (sembol/suslemenin OCR copu bu yuzden sayilmaz);
                 "ASTROLOVE / A + B" satiri ciftin burclari mi; uzun/orta tire yok mu. CL canli ile CL TAM_SET arasi
                 kelime farki ayrica raporlanir (sablon farki, bilgi).
 K3 RENK       : 5 renk gorseli (+kapak MB) orta bolge medyan Lab, referansin ayni renk gorseline delta E76 <= 3.
 K4 IZ/LEKE    : onayli CL TAM_SET ayni karesiyle fark haritasi; esik = CL TAM_SET ile CL canlinin ICERIGI AYNI
                 (256px fark <= 0.001) karelerinde p99.9 x1.5, [8, 60] araliginda (Etsy yeniden sikistirma gurultusu); cifte ozel bolgeler = ilanlarin >= %30'unda farkli
                 pikseller (sembol, burc adlari). Kalan bilesen >= ALAN_MIN -> supheli, 3x kirpim. n < 5 ise OLCULEMEDI.
 K5 VIDEO      : video 1; A1_77 cift videosu, baska cift tuzagi ve poster ile video_dogrula 10 kare denetimi.
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
import video_dogrula  # noqa: E402

REF_ID, REF_A, REF_B = "4570143815", "Cancer", "Libra"
A77 = "gdrive:ASTROLOVE/TEMP/POD_KISISEL/A1_77"
KOTA_TABAN, CAGRI_SINIR = 230, 300
ESIK_FOTO, ESIK_DE = 0.001, 3.0
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


KONF = 80


def ocr_tsv(im):
    """(ham metin, [(KELIME, conf)])"""
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        k = im.convert("L")
        if k.width < 2000:
            k = k.resize((2000, round(k.height * 2000 / k.width)), Image.LANCZOS)
        k.save(f.name)
        out = subprocess.run(["tesseract", f.name, "-", "--psm", "3", "-l", "eng", "tsv"], capture_output=True, text=True).stdout
    kel = []
    for sat in out.splitlines()[1:]:
        p = sat.split("\t")
        if len(p) == 12 and p[11].strip():
            try:
                kel.append((p[11].strip(), float(p[10])))
            except ValueError:
                pass
    return " ".join(w for w, _ in kel), kel


def kelimeler(kel, konf=0.0):
    """>= 3 harfli, burc adi olmayan kelimeler (burc satiri ayrica 'baslik' ile denetlenir)."""
    burc = {x.upper() for x in BURC}
    s = set()
    for w, c in kel:
        if c < konf:
            continue
        for t in re.findall(r"[A-Z]{3,}", w.upper()):
            if t not in burc:
                s.add(t)
    return s


def kel_fark(ref, can):
    eksik = kelimeler(ref, KONF) - kelimeler(can)
    fazla = kelimeler(can, KONF) - kelimeler(ref)
    return sorted(eksik), sorted(fazla)


def norm(t):
    t = t.upper().replace("—", " <UZUNTIRE> ").replace("–", " <ORTATIRE> ")
    return " ".join(re.sub(r"[^A-Z0-9&+/<> ]", " ", t).split())


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


def ort_kare_farki(kare_fark_list):
    """video_dogrula sonucundaki genel/burc farklarinin tek ortalamasini verir."""
    if not kare_fark_list:
        return None
    return round(float(np.mean([(x["genel"] + x["burc"]) / 2 for x in kare_fark_list])), 4)


def k5_dogrula(vids, cift, tuzak_cift, dizin, poster):
    """Canli/referans/tuzak videolarini indirip ortak dogrulayiciyi calistirir."""
    bos = {
        "pass": False, "sure_fark": None, "kare_fark_list": [],
        "tuzak_orani": None, "eski_slogan": False, "neden": "",
    }
    if len(vids) != 1:
        return {**bos, "neden": f"video sayisi {len(vids)}"}
    if not tuzak_cift:
        return {**bos, "neden": "tuzak video icin baska cift yok"}
    try:
        canli, beklenen, tuzak = dizin / "CANLI.mp4", dizin / "BEKLENEN.mp4", dizin / "TUZAK.mp4"
        canli.write_bytes(indir(vids[0].get("video_url")))
        rc("copyto", f"{A77}/{cift}/VIDEO.mp4", str(beklenen))
        rc("copyto", f"{A77}/{tuzak_cift}/VIDEO.mp4", str(tuzak))
        return video_dogrula.dogrula(canli, beklenen, tuzak_mp4=tuzak, poster_png=poster)
    except Exception as e:  # noqa: BLE001
        return {**bos, "neden": f"video olculemedi {type(e).__name__}"}


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
    cl_dir = isdir / "CANCER_LIBRA"
    esik, CLT, sablon = None, {}, {}
    try:
        rc("copy", f"{A77}/CANCER_LIBRA/TAM_SET", str(cl_dir), "--include", "[01][0-9]_*.jpg", "--include", "SET.json")
        CL = json.loads((cl_dir / "SET.json").read_text())
        CLT = {g["cl_karsiligi"]: Image.open(cl_dir / g["dosya"]).convert("RGB") for g in CL["galeri"]}
        gur = {}
        for n, im in CLT.items():
            if n not in R:
                continue
            f = fark256(im, R[n])
            p = round(float(np.percentile(np.abs(kucuk(im) - kucuk(R[n])), 99.9)), 1)
            print(f"  CL #{n}: TAM_SET/canli fark {f}, p99.9 {p}" + ("" if f <= ESIK_FOTO else " (icerik farkli, esige girmez)"), flush=True)
            if f <= ESIK_FOTO:
                gur[n] = p
        esik = min(60.0, max(8.0, max(gur.values()) * 1.5)) if gur else None
        for g in CL["galeri"]:
            n = g["cl_karsiligi"]
            if g.get("tur") in ("kapak", "kart") and n in R:
                e, z = kel_fark(ocr_tsv(R[n])[1], ocr_tsv(CLT[n])[1])
                if e or z:
                    sablon[n] = {"canli_CL_de_var": e, "TAM_SET_te_var": z}
    except Exception as e:  # noqa: BLE001
        print(f"CL TAM_SET olculemedi: {type(e).__name__} {str(e)[:120]}", flush=True)
    print(f"K4 piksel esigi (CL ayni-icerik karelerinde p99.9 x1.5, [8,60]): {esik}", flush=True)
    print(f"CL canli ile CL TAM_SET sablon kelime farki: {json.dumps(sablon, ensure_ascii=False)}", flush=True)
    REF = {n: CLT.get(n, im) for n, im in R.items()}
    ref_ocr = {n: ocr_tsv(im) for n, im in REF.items()}

    satir, fark4, serit = {}, {}, []
    ciftler = sorted(hedef)
    tuzak = {c: ciftler[(i + 1) % len(ciftler)] for i, c in enumerate(ciftler)} if len(ciftler) > 1 else {}
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
            ham, kel = ocr_tsv(L[i])
            rham, rkel = ref_ocr[g["cl_karsiligi"]]
            t = norm(ham)
            if any(("—" in w or "–" in w) and c >= KONF for w, c in kel):
                hat.append(f"#{i} tire")
            m = re.search(r"ASTROLOVE\s*/\s*([A-Z]+)\s*\+\s*([A-Z]+)", t)
            if "ASTROLOVE /" in norm(rham) and (not m or sorted(m.groups()) != sorted([a.upper(), b.upper()])):
                hat.append(f"#{i} baslik {m.groups() if m else 'OKUNAMADI'}")
            e, z = kel_fark(rkel, kel)
            if e or z:
                hat.append(f"#{i} eksik {e[:6]} fazla {z[:6]}")
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
                if i in L and g["cl_karsiligi"] in REF:
                    ref4 = kucuk(REF[g["cl_karsiligi"]])
                    can4 = kucuk(L[i].resize(REF[g["cl_karsiligi"]].size, Image.BILINEAR))
                    fark4[(c, i)] = (np.abs(can4 - ref4) > esik)
        # K5
        poster = d / gal[min(gal)]["dosya"]
        sonuc = k5_dogrula(vids, c, tuzak.get(c), d, poster)
        r.update(
            K5_video="PASS" if sonuc["pass"] else "FAIL",
            K5_deger=sonuc["neden"],
            sure_fark=sonuc["sure_fark"],
            ort_kare_farki=ort_kare_farki(sonuc["kare_fark_list"]),
            tuzak_orani=sonuc["tuzak_orani"],
            eski_slogan=sonuc["eski_slogan"],
            neden=sonuc["neden"],
        )
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
            "K5_video", "K5_deger", "sure_fark", "ort_kare_farki", "tuzak_orani", "eski_slogan", "neden", "hata"]
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
    print("OZET " + json.dumps({**oz, "cagri": api.calls, "kota_son": api.remaining, "k4_esik": esik,
                                "cl_sablon_fark": sablon}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
