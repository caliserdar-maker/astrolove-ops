#!/usr/bin/env python3
"""GOREV 0020 - 78 TAM_SET'in YUKLEMEDEN ONCE kalite denetimi (SALT OKUMA; Etsy'ye yazma YOK).
Kaynak: Drive A1_77/<CIFT>/TAM_SET (77 cift + CANCER_LIBRA). Referans: onayli CL TAM_SET (ayni cl_karsiligi karesi).
 YAZI : kapak/kart karelerinde OCR (gri, 3x buyutme, psm 3 TSV). Beklenen = CL TAM_SET ayni karesinin OCR'i
        (Cancer/Libra -> ciftin burclari). Kelime farki (>= 3 harf, conf >= 80): eksik = CL'de guvenle okunup ciftte
        hic okunmayan; fazla = ciftte guvenle okunup CL'de hic okunmayan. Fark, ikinci bagimsiz OCR gecisinde
        (autocontrast, psm 11) de suruyorsa kesin sayilir. Ciftlerin >= %30'unda (ayni-burc ciftleri kendi grubunda)
        gorulen fark SISTEMATIK sayilir (sablon/Left-Right kurali) ve ayrica raporlanir. Ayrica: yanlis burc adi,
        "ASTROLOVE / A + B" basligi, uzun/orta tire, yasak ifadeler (metin kurali 25 Eyl).
 CIFT : cifte ozel bolge (ciftlerin >= %30'unun CL'den farkli oldugu pikseller) icinde her ciftin en yakin baska
        cifte uzakligi; esik = CL TAM_SET/CL canli ayni-icerik karelerinde ayni bolgedeki ortalama fark x1.5
        (yeniden sikistirma gurultusu). Altindaysa KOPYA/KARISMA -> FAIL. En yakin komsunun ortak burcu bilgi olarak.
 RENK : 5 renk gorseli (kapak MB + 4 cerceve) orta bolge medyan Lab, CL TAM_SET karsiligina dE76 <= 3.
 IZ   : (a) fark: |cift - CL| > esik (canli_qc K4 yontemi: CL TAM_SET/CL canli ayni-icerik karelerinde p99.9 x1.5,
        [8, 60]); cifte ozel bolge (bir-disarida: ciftin kendisi haric herhangi bir ciftin CL'den farkli oldugu
        pikseller, 8 px + yatayda %15 genislik genisletme: yazi satiri) disinda alan >= 40 px bilesen -> FAIL. (b) Sobel: CL'nin duz zemininde
        (CL Sobel < Ts, cifte ozel bolge disi) ciftte Ts'yi asan kenar; Ts = ayni-icerik karelerinde
        Sobel farkinin p99.9 x1.5, [4, 40]; alan >= 40 px -> FAIL.
 VIDEO: VIDEO.mp4 var, sure 12.6 +- 0.3 sn, cozunurluk (bilgi).
Cikti: out/TAMSET_QC.csv (cift x kare x kontrol, deger, esik, PASS/FAIL), out/TAMSET_SISTEMATIK.csv, out/kirpim/*.jpg (x3),
       out/TAMSET_SERIT.jpg (en kotu 12 kare), out/TAMSET_OZET.json.
Kullanim:
  tamset_qc.py etsy <cl_canli_dir> <metin78_csv>         (Etsy salt okuma, <= 5 cagri; CL canli gorseller + kargo profili)
  tamset_qc.py qc <a77_dir> <cl_canli_dir> [cift,cift]   (Etsy'siz; ikinci arguman verilirse yalniz o ciftler + CL)"""
import csv
import difflib
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
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canli_qc import BURC, KONF, W4, fark256, kucuk, lab, orta_lab  # noqa: E402,F401

REF = "CANCER_LIBRA"
ESIK_DE, VIDEO_SN, ALAN_MIN, SIKLIK, SISTEM = 3.0, 12.6, 40, 0.30, 0.30
YATAY = int(W4 * 0.15) | 1   # bolgenin yatay genisletmesi (px, 500 genislikte)
YASAK = [r"OBA[\s-]*FREE", r"BRIGHT WHITE", r"\d+\s*-\s*\d+\s*YEARS", r"12[\s-]*COLOU?R"]
OUT = Path("out")
os.environ["OMP_THREAD_LIMIT"] = "1"   # paralel iscilerde tesseract'in kendi OpenMP'si CPU'yu asiri yukler
BURC_UP = {b.upper() for b in BURC}


def log(m):
    print(m, flush=True)


# ---------------------------------------------------------------- Etsy (salt okuma)
def etsy(cl_dir, metin78):
    import requests
    from etsy_common import Etsy, TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    Path(cl_dir).mkdir(parents=True, exist_ok=True)
    for x in api.get("/listings/4570143815/images").get("results") or []:           # cagri 1
        r = requests.get(x["url_fullxfull"], timeout=120)
        r.raise_for_status()
        (Path(cl_dir) / f"{x['rank']:02d}.jpg").write_bytes(r.content)
    ilk = next(r["ilan_id"] for r in csv.DictReader(open(metin78, encoding="utf-8")) if r.get("ilan_id"))
    L = api.get(f"/listings/{ilk}", ok404=True) or {}                                 # cagri 2
    pid = L.get("shipping_profile_id")
    P = api.get(f"/shops/{shop}/shipping-profiles/{pid}", ok404=True) or {} if pid else {}   # cagri 3
    kargo = {"ornek_ilan": ilk, "shipping_profile_id": pid, "profil_adi": P.get("title"),
             "profil_min_processing_days": P.get("min_processing_days"),
             "profil_max_processing_days": P.get("max_processing_days"),
             "profil_processing_days_display_label": P.get("processing_days_display_label"),
             "ilan_processing_min": L.get("processing_min", "ALAN YOK"),
             "ilan_processing_max": L.get("processing_max", "ALAN YOK"),
             "cagri": api.calls, "kota_son": api.remaining}
    OUT.mkdir(exist_ok=True)
    (OUT / "TAMSET_KARGO.json").write_text(json.dumps(kargo, ensure_ascii=False, indent=1))
    log("KARGO " + json.dumps(kargo, ensure_ascii=False))


# ---------------------------------------------------------------- OCR
def ocr(im, gecis):
    """gecis 1: gri 3x, psm 3 | gecis 2: autocontrast 3x, psm 11 (bagimsiz ikinci okuma). -> (metin, [(kelime, conf)])"""
    k = im.convert("L")
    k = k.resize((k.width * 3, k.height * 3), Image.LANCZOS)
    if gecis == 2:
        k = ImageOps.autocontrast(k, cutoff=1)
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        k.save(f.name)
        out = subprocess.run(["tesseract", f.name, "-", "--psm", "3" if gecis == 1 else "11", "-l", "eng", "tsv"],
                             capture_output=True, text=True).stdout
    kel = []
    for sat in out.splitlines()[1:]:
        p = sat.split("\t")
        if len(p) == 12 and p[11].strip():
            try:
                kel.append((p[11].strip(), float(p[10])))
            except ValueError:
                pass
    return " ".join(w for w, _ in kel), kel


def burc_adi(t):
    """OCR'in 1 harf kaybettigi/ekledigi burc adini (LIBR, CANCERS) burca esler; degilse None."""
    if t in BURC_UP:
        return t
    if len(t) >= 4:
        for x in BURC_UP:
            if abs(len(x) - len(t)) <= 1 and difflib.SequenceMatcher(None, x, t).ratio() >= 0.85:
                return x
    return None


def kelime(kel, konf=0.0, burc=False):
    s = set()
    for w, c in kel:
        if c >= konf:
            for t in re.findall(r"[A-Z]{3,}", w.upper()):
                bt = burc_adi(t)
                if burc and bt:
                    s.add(bt)
                elif not burc and not bt:
                    s.add(t)
    return s


def norm(t):
    return " ".join(re.sub(r"[^A-Z0-9&+/ ]", " ", t.upper()).split())


def yazi_denetle(im, ref, a, b):
    """ref: {1: (metin, kel), 2: (...)} CL karesi. -> dict (fark listeleri + kural kontrolleri)."""
    p1 = ocr(im, 1)
    rk1 = ref[1][1]
    eksik = kelime(rk1, KONF) - kelime(p1[1])
    fazla = kelime(p1[1], KONF) - kelime(rk1)
    p2 = None
    if eksik or fazla:                                   # ikinci bagimsiz gecisle dogrula
        p2 = ocr(im, 2)
        rk2 = ref[2][1]
        eksik = {w for w in eksik if w not in kelime(p2[1])}
        fazla = {w for w in fazla if w in kelime(p2[1]) and w not in kelime(rk2)}
    tum = [p1] + ([p2] if p2 else [])
    ab = {a.upper(), b.upper()}
    ref_burc = kelime(rk1, burc=True) | kelime(ref[2][1], burc=True)
    izinli = ab | (ref_burc - {"CANCER", "LIBRA"})
    yanlis = sorted(kelime(p1[1], KONF, burc=True) - izinli)
    if yanlis and p2 is None:
        p2 = ocr(im, 2)
        tum.append(p2)
    yanlis = [w for w in yanlis if all(w in kelime(p[1], burc=True) for p in tum)]
    gerekli = set()
    if "CANCER" in ref_burc:
        gerekli.add(a.upper())
    if "LIBRA" in ref_burc:
        gerekli.add(b.upper())
    eksik_burc = sorted(w for w in gerekli if not any(w in kelime(p[1], burc=True) for p in tum))
    baslik = None
    if "ASTROLOVE /" in norm(ref[1][0]):
        ok = False
        for p in tum:
            m = re.search(r"ASTROLOVE\s*/\s*([A-Z]+)\s*\+\s*([A-Z]+)", norm(p[0]))
            if m and sorted(m.groups()) == sorted([a.upper(), b.upper()]):
                ok = True
        baslik = "PASS" if ok else "FAIL"
    tire = [w for w, c in p1[1] if ("—" in w or "–" in w) and c >= KONF]
    yasak = [y for y in YASAK if re.search(y, norm(p1[0]))]
    return {"eksik": sorted(eksik), "fazla": sorted(fazla), "yanlis_burc": yanlis, "eksik_burc": eksik_burc,
            "baslik": baslik, "tire": tire, "yasak": yasak, "gecis2": p2 is not None}


# ---------------------------------------------------------------- cift isleyici (paralel)
def isle(arg):
    c, d, ref_ocr, cl_set = arg
    a, b = (c.split("_") + [c])[:2]
    S = json.loads((d / "SET.json").read_text())
    gal = {g["cl_karsiligi"]: g for g in S["galeri"]}
    r = {"cift": c, "a": a, "b": b, "yazi": {}, "k4": {}, "lab": {}, "eksik_dosya": [], "video": None}
    for n, g in sorted(gal.items()):
        yol = d / g["dosya"]
        if not yol.exists():
            r["eksik_dosya"].append(g["dosya"]); continue
        im = Image.open(yol).convert("RGB")
        r["k4"][n] = np.clip(kucuk(im), 0, 255).astype(np.uint8)
        if g.get("renk"):
            r["lab"][n] = orta_lab(im).tolist()
        if g.get("tur") in ("kapak", "kart") and n in ref_ocr and c != REF:
            r["yazi"][n] = yazi_denetle(im, ref_ocr[n], a, b)
    v = d.parent / "VIDEO.mp4"
    if v.exists():
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height:format=duration", "-of", "json", str(v)], capture_output=True, text=True)
        j = json.loads(p.stdout or "{}")
        s = (j.get("streams") or [{}])[0]
        r["video"] = [float((j.get("format") or {}).get("duration") or 0), s.get("width"), s.get("height")]
    return r


def sobel(a):
    a = a.astype(float)
    return np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1)) / 8.0


def kirp(yol, sl, hedef, etiket, ref_yol=None):
    src = Image.open(yol).convert("RGB")
    sx = src.width / W4
    x0, x1 = max(0, int(sl[1].start * sx) - 40), min(src.width, int(sl[1].stop * sx) + 40)
    y0, y1 = max(0, int(sl[0].start * sx) - 40), min(src.height, int(sl[0].stop * sx) + 40)
    parca = [src.crop((x0, y0, x1, y1))]
    if ref_yol:
        rs = Image.open(ref_yol).convert("RGB").resize(src.size, Image.BILINEAR)
        parca.append(rs.crop((x0, y0, x1, y1)))
    w, h = sum(p.width for p in parca) * 3, parca[0].height * 3
    if w * h > 3600 * 3600:                              # cok buyuk bolge: x3 yerine sigdir
        k = (3600 * 3600 / (w * h)) ** 0.5
    else:
        k = 1.0
    tuval = Image.new("RGB", (int(w * k) + 8 * (len(parca) - 1), int(h * k) + 30), "white")
    x = 0
    for p in parca:
        p = p.resize((max(1, int(p.width * 3 * k)), max(1, int(p.height * 3 * k))), Image.LANCZOS)
        tuval.paste(p, (x, 30)); x += p.width + 8
    ImageDraw.Draw(tuval).text((6, 8), etiket + ("  (sol: cift | sag: CL)" if ref_yol else ""), fill="black")
    tuval.save(hedef, quality=90)
    return hedef


# ---------------------------------------------------------------- ana QC
def qc(a77, cl_canli, sadece=None):
    t0 = time.time()
    a77, cl_canli = Path(a77), Path(cl_canli)
    (OUT / "kirpim").mkdir(parents=True, exist_ok=True)
    ciftler = sorted(p.parent.parent.name for p in a77.glob("*/TAM_SET/SET.json"))
    if sadece:
        ciftler = [c for c in ciftler if c in set(sadece) | {REF}]
    assert REF in ciftler, "CL TAM_SET yok"
    cl_d = a77 / REF / "TAM_SET"
    CLS = json.loads((cl_d / "SET.json").read_text())
    clg = {g["cl_karsiligi"]: g for g in CLS["galeri"]}
    CLT = {n: Image.open(cl_d / g["dosya"]).convert("RGB") for n, g in clg.items()}
    log(f"TAM_SET: {len(ciftler)} (CL dahil); CL kare {len(CLT)}")

    # esikler: CL TAM_SET / CL canli ayni-icerik kareleri (Etsy yeniden sikistirma gurultusu)
    canli = {int(p.stem): Image.open(p).convert("RGB") for p in cl_canli.glob("*.jpg")}
    ayni, gur_p, gur_s = [], [], []
    for n, im in CLT.items():
        if n in canli:
            f = fark256(im, canli[n])
            if f <= 0.001:
                A, B = kucuk(im), kucuk(canli[n].resize(im.size, Image.BILINEAR))
                ayni.append(n)
                gur_p.append(float(np.percentile(np.abs(A - B), 99.9)))
                gur_s.append(float(np.percentile(np.abs(sobel(A) - sobel(B)), 99.9)))
    esik = min(60.0, max(8.0, max(gur_p) * 1.5)) if gur_p else None
    ts = min(40.0, max(4.0, max(gur_s) * 1.5)) if gur_s else None
    log(f"ayni-icerik CL kareleri {ayni}; fark esigi {esik}; Sobel esigi {ts}")
    if esik is None:
        sys.exit("DUR: CL canli ile ayni-icerik kare yok, esik olculemedi")

    # CL OCR (iki gecis), bir kez
    ref_ocr = {n: {1: ocr(CLT[n], 1), 2: ocr(CLT[n], 2)} for n, g in clg.items() if g.get("tur") in ("kapak", "kart")}
    log(f"CL OCR bitti ({time.time() - t0:.0f} sn)")

    # paralel cift isleme + ETA
    R, isler = {}, [(c, a77 / c / "TAM_SET", ref_ocr, None) for c in ciftler]
    with Pool(os.cpu_count() or 2) as pool:
        for i, r in enumerate(pool.imap_unordered(isle, isler), 1):
            R[r["cift"]] = r
            gec = time.time() - t0
            kalan = gec / i * (len(isler) - i)
            log(f"[{i}/{len(isler)}] %{100 * i // len(isler)} gecen {gec / 60:.1f} dk, kalan ~{kalan / 60:.1f} dk ({r['cift']})")

    satir, sist, kotu = [], [], []
    ciftler_x = [c for c in ciftler if c != REF]
    ayni_burc = {c for c in ciftler_x if R[c]["a"] == R[c]["b"]}

    def ekle(c, n, kontrol, deger, es, ok):
        satir.append({"cift": c, "cl_kare": n, "sira": (clg.get(n) or {}).get("sira", ""), "kontrol": kontrol,
                      "deger": deger, "esik": es, "sonuc": "PASS" if ok else "FAIL"})

    # --- YAZI: sistematik farklar (grup frekansi)
    for n in sorted(ref_ocr):
        for grup, uyeler in (("ayni_burc", sorted(ayni_burc)), ("farkli_burc", sorted(set(ciftler_x) - ayni_burc))):
            if not uyeler:
                continue
            for yon in ("eksik", "fazla"):
                say = {}
                for c in uyeler:
                    for w in (R[c]["yazi"].get(n) or {}).get(yon, []):
                        say[w] = say.get(w, 0) + 1
                for w, k in say.items():
                    if k / len(uyeler) >= SISTEM and k >= 2:
                        sist.append({"cl_kare": n, "grup": grup, "yon": yon, "kelime": w, "cift_sayisi": k, "grup_n": len(uyeler)})
    sis = {(s["cl_kare"], s["grup"], s["yon"], s["kelime"]) for s in sist}
    for c in ciftler_x:
        grup = "ayni_burc" if c in ayni_burc else "farkli_burc"
        for n, y in sorted(R[c]["yazi"].items()):
            e = [w for w in y["eksik"] if (n, grup, "eksik", w) not in sis]
            z = [w for w in y["fazla"] if (n, grup, "fazla", w) not in sis]
            ekle(c, n, "YAZI_KELIME", f"eksik {e} fazla {z}" + (" (2 gecis)" if y["gecis2"] else ""), "0 kelime", not e and not z)
            ekle(c, n, "YAZI_BURC", f"yanlis {y['yanlis_burc']} eksik {y['eksik_burc']}", "yanlis/eksik yok",
                 not y["yanlis_burc"] and not y["eksik_burc"])
            if y["baslik"]:
                ekle(c, n, "YAZI_BASLIK", y["baslik"], "ASTROLOVE / A + B", y["baslik"] == "PASS")
            ekle(c, n, "YAZI_KURAL", f"tire {y['tire']} yasak {y['yasak']}", "tire/yasak yok", not y["tire"] and not y["yasak"])
            if e or z or y["yanlis_burc"] or y["eksik_burc"] or y["baslik"] == "FAIL":
                kotu.append((len(e) + len(z) + 5 * len(y["yanlis_burc"] + y["eksik_burc"]), c, n, "YAZI", None))
        for f in R[c]["eksik_dosya"]:
            ekle(c, "", "DOSYA", f"eksik {f}", "13 dosya", False)

    # --- RENK
    for c in ciftler_x:
        for n, L in sorted(R[c]["lab"].items()):
            de = round(float(np.linalg.norm(np.array(L) - np.array(R[REF]["lab"][n]))), 2) if n in R[REF]["lab"] else None
            ekle(c, n, "RENK", de, ESIK_DE, de is not None and de <= ESIK_DE)

    # --- CIFT + IZ (kare bazli, tum ciftler birlikte)
    ref4 = R[REF]["k4"]
    cift_esik = {}
    for n in sorted(ref4):
        S = {c: R[c]["k4"][n].astype(float) for c in ciftler_x if n in R[c]["k4"] and R[c]["k4"][n].shape == ref4[n].shape}
        if not S:
            continue
        cl = ref4[n].astype(float)
        fm = np.mean([np.abs(v - cl) > esik for v in S.values()], axis=0) >= SIKLIK
        M = ndimage.binary_dilation(fm, iterations=8)
        # CIFT: ayni-icerik CL karelerinde bolge ici ortalama gurultu
        if M.mean() >= 0.002:
            gm = []
            for m in ayni:
                if m in canli and ref4.get(m) is not None:
                    A = ref4[m].astype(float)
                    B = kucuk(canli[m].resize(CLT[m].size, Image.BILINEAR))
                    if A.shape == M.shape:
                        gm.append(float(np.abs(A - B)[M].mean()))
            ce = round(max(gm) * 1.5, 2) if gm else None
            cift_esik[n] = ce
            ks = sorted(S)
            for c in ks:
                dist = {x: float(np.abs(S[c] - S[x])[M].mean()) for x in ks if x != c}
                if not dist:
                    continue
                x = min(dist, key=dist.get)
                ortak = bool({R[c]["a"], R[c]["b"]} & {R[x]["a"], R[x]["b"]})
                ok = ce is None or dist[x] > ce
                ekle(c, n, "CIFT", f"en yakin {x} {dist[x]:.2f} (ortak burc {'var' if ortak else 'YOK'}); bolge %{100 * M.mean():.1f}",
                     ce, ok)
                if not ok:
                    lb = ndimage.find_objects(M.astype(int))[0]
                    kotu.append((1000, c, n, "CIFT", lb))
        # IZ (a) fark + (b) Sobel. Cifte ozel bolge bir-disarida: ciftin KENDISI HARIC herhangi bir ciftin CL'den
        # farkli oldugu pikseller (uzun burc adlari %30 sikligi asar; yalniz bu cifte ait leke maskelenmez)
        cls = sobel(cl)
        fark = {c: np.abs(v - cl) > esik for c, v in S.items()}
        say = np.sum(list(fark.values()), axis=0)
        for c, v in S.items():
            Mc = ndimage.binary_dilation((say - fark[c]) >= 1, iterations=8)
            Mc = ndimage.binary_dilation(Mc, structure=np.ones((1, YATAY)))   # yazi satiri: uzun burc adi tasmasi
            duz = ndimage.binary_erosion((cls < ts) & ~Mc, iterations=2) if ts else None
            for tur, harita, es in (("IZ_FARK", fark[c] & ~Mc, esik),
                                    ("IZ_SOBEL", (sobel(v) > ts) & duz if duz is not None else None, ts)):
                if harita is None:
                    continue
                lb, _ = ndimage.label(harita)
                sup = []
                for j, sl in enumerate(ndimage.find_objects(lb), 1):
                    al = int((lb[sl] == j).sum())
                    if al >= ALAN_MIN:
                        sup.append((al, sl))
                sup.sort(key=lambda s: -s[0])
                ekle(c, n, tur, f"bilesen {len(sup)}, en buyuk {sup[0][0] if sup else 0} px", f"piksel {es:.1f}, alan >= {ALAN_MIN}", not sup)
                for al, sl in sup[:3]:
                    kotu.append((al, c, n, tur, sl))

    # --- VIDEO
    for c in ciftler_x:
        v = R[c]["video"]
        ekle(c, "", "VIDEO", f"{v[0]:.2f} sn {v[1]}x{v[2]}" if v else "YOK", f"{VIDEO_SN} +- 0.3 sn",
             bool(v) and abs(v[0] - VIDEO_SN) <= 0.3)

    # --- kirpimlar (FAIL) + serit (en kotu 12)
    kotu.sort(key=lambda k: -k[0])
    kirpimlar = []
    for i, (skor, c, n, tur, sl) in enumerate(kotu):
        yol = a77 / c / "TAM_SET" / next(g["dosya"] for g in json.loads((a77 / c / "TAM_SET" / "SET.json").read_text())["galeri"]
                                         if g["cl_karsiligi"] == n)
        if sl is None:                                    # YAZI: tum kare kucuk + CL
            sl = (slice(0, R[c]["k4"][n].shape[0]), slice(0, W4))
        if i < 60:
            kirpimlar.append(kirp(yol, sl, OUT / "kirpim" / f"{c}_k{n:02d}_{tur}_{i}.jpg", f"{c} kare{n} {tur} skor {skor}",
                                  cl_d / clg[n]["dosya"]))
    if kirpimlar:
        ks = [Image.open(p) for p in kirpimlar[:12]]
        for k in ks:
            k.thumbnail((640, 420))
        tuval = Image.new("RGB", (3 * 650, 4 * 430), "white")
        for i, k in enumerate(ks):
            tuval.paste(k, ((i % 3) * 650, (i // 3) * 430))
        tuval.save(OUT / "TAMSET_SERIT.jpg", quality=88)

    alan = ["cift", "cl_kare", "sira", "kontrol", "deger", "esik", "sonuc"]
    with open(OUT / "TAMSET_QC.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(satir)
    with open(OUT / "TAMSET_SISTEMATIK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cl_kare", "grup", "yon", "kelime", "cift_sayisi", "grup_n"])
        w.writeheader(); w.writerows(sist)
    oz = {}
    for k in sorted({s["kontrol"] for s in satir}):
        ss = [s for s in satir if s["kontrol"] == k]
        fc = sorted({s["cift"] for s in ss if s["sonuc"] == "FAIL"})
        oz[k] = {"kare_PASS": f"{sum(s['sonuc'] == 'PASS' for s in ss)}/{len(ss)}", "FAIL_cift": len(fc), "cift": fc[:20]}
    tum_fail = sorted({s["cift"] for s in satir if s["sonuc"] == "FAIL"})
    ozet = {"cift": len(ciftler_x), "temiz_cift": len(ciftler_x) - len(tum_fail), "kontrol": oz,
            "esik": {"fark": esik, "sobel": ts, "cift": cift_esik, "ayni_icerik_CL": ayni},
            "sistematik": len(sist), "kirpim": len(kirpimlar), "sure_dk": round((time.time() - t0) / 60, 1)}
    (OUT / "TAMSET_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    log("OZET " + json.dumps(ozet, ensure_ascii=False))
    log("SISTEMATIK " + json.dumps(sist[:40], ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "etsy":
        etsy(sys.argv[2], sys.argv[3])
    else:
        qc(sys.argv[2], sys.argv[3], sys.argv[4].split(",") if len(sys.argv) > 4 else None)
