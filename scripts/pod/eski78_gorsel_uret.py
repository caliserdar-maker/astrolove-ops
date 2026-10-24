#!/usr/bin/env python3
"""ESKI 78 galeri, cerceve temizligi: 78 cift icin yeni kartlar (Serdar 17 Eki onayi). Etsy'ye YAZMAZ.
Kaynak: CANLI galeri (eski78_gorsel_indir.py: CANLI/<CIFT>/rNN.jpg + galeri.json), 3000x2250 olmali.
Canli rank -> islem (onayli CL ornegi 17 Eki ile ayni kural):
  r1  kapak            "Frame not included" etiketi (cerceve_etiket.py)
  r2  Choose format    iki sutun yeniden kurulum (kart02_iki_sutun.py; ciftin krem 02'si galeri77_kur ile)
  r3  konsept          gorsel AYNI (yalniz alt metin degisir; canli dosya byte'i aynen yuklenir)
  r5  hediye sahne     etiket
  r6  Four frames      SILINIR (kart uretilmez)
  r7  boylar           alt satir metni
  r8  yatak sahne      alt satir metni + etiket
  r9  calisma sahne    alt satir metni + etiket
  r10 yemek sahne      alt satir metni + etiket
  r12 kagit            genel kagit karti (kart12_kagit_genel.py)
  r13 surec            alt baslik + 04 maddesi
Ust etiket (ASTROLOVE / ASTROLOVEART) olduğu gibi (Serdar 17 Eki: ayri is).
QC (cift basina PASS/FAIL): her metin degisikligi kutu disi fark p99.9 <= 12 ve max <= 45 (canli Etsy JPEG yeniden kodlama gurultusu; yanlis yere yazi >= 100), olcum hatasi < 40, yasak sozcuk yok; etiket kontrast PASS;
  r12 betigi PASS; r2 betigi PASS + baski posteri canli r2 posteriyle NCC >= 0.97 (dogru cift); tum ciktilar 3000x2250.
Cikti: OUT/<CIFT>/rNN_*.jpg + OUT/<CIFT>/ONCE_SONRA.jpg + OUT/TABLO.csv
Kullanim: eski78_gorsel_uret.py --canli CANLI --kaynak K --duvar DUVAR.png --fd FONTS --out OUT [--ciftler ...] [--is 4]"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import PIL  # noqa: E402
if PIL.__version__ != "11.0.0" and os.environ.get("PILLOW_SERBEST") != "1":   # Serdar 24 Eki: yerel = Actions (requirements.txt)
    raise SystemExit(f"DUR: Pillow {PIL.__version__}; uretim ve test Actions ile ayni Pillow 11.0.0 ile kosar (glif yerlesimi farki)")

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
from kart_metin_degis import degistir  # noqa: E402

M5 = dict(aile="mont", hiza="merkez", agirliklar=(500,))
ALT_SATIR = (300, 1970, 2700, 2020)
METIN = {
    7: [dict(kutu=(300, 1950, 2700, 2000), eski="Every size is available as a print and in all 4 frame colors.",
             yeni="Every size is available as a print and as a digital file.", **M5)],
    8: [dict(kutu=ALT_SATIR, eski="Five colors, thirteen sizes, four frame finishes.", yeni="Five colors and thirteen sizes.", **M5)],
    9: [dict(kutu=ALT_SATIR, eski="Every color comes in all four frame finishes.", yeni="Every color comes in all thirteen sizes.", **M5)],
    10: [dict(kutu=ALT_SATIR, eski="Framed prints arrive ready to hang.", yeni="Prints ship unframed, ready for your frame.", **M5)],
    13: [dict(kutu=(130, 330, 1500, 395), eski="Prints and framed prints, made to order.", yeni="Every print is made to order.",
              aile="mont", hiza="sol", agirliklar=(500,)),
         dict(kutu=(1780, 1460, 2900, 1520), eski="size. Framed prints come boxed with corner", yeni="size. US orders are tracked.",
              aile="mont", hiza="sol", agirliklar=(500,)),
         dict(kutu=(1780, 1528, 2900, 1590), eski="guards. US orders are tracked.", yeni="", aile="mont", hiza="sol", agirliklar=(500,))],
}
ETIKET = {1, 5, 8, 9, 10}
YUKLE = [1, 2, 3, 5, 7, 8, 9, 10, 12, 13]            # yeniden yuklenecek canli rank'ler (6 silinir)
YASAK = ("frame finish", "frame color", "framed print", "wood frame", "acrylic", "gsm", "hahnem", "photo rag", "cotton", "—", "–")
PW, PH = 586, 760


def py(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()


def gri(a):
    a = np.asarray(a.convert("L").resize((200, 260)), np.float32); a -= a.mean(); return a / (np.linalg.norm(a) + 1e-9)


def cift_isle(arg):
    c, a, b, A = arg
    t0 = time.time(); kay = os.path.join(A.canli, c); o = os.path.join(A.out, c); os.makedirs(o, exist_ok=True)
    R = dict(cift=c, notlar=[]); ok = True
    try:
        man = json.load(open(os.path.join(kay, "galeri.json")))
        if man.get("gorsel_sayisi") != 18:
            raise RuntimeError(f"canli gorsel sayisi {man.get('gorsel_sayisi')} (18 bekleniyor)")
        src = {r: os.path.join(kay, f"r{r:02d}.jpg") for r in YUKLE}
        for r, p in src.items():
            if Image.open(p).size != (3000, 2250):
                raise RuntimeError(f"r{r} boyut {Image.open(p).size}")
        D = Image.open(A.duvar).convert("RGB")
        # r3: aynen
        shutil.copyfile(src[3], os.path.join(o, "r03.jpg"))
        # metin degisiklikleri
        for r, isler in METIN.items():
            K = Image.open(src[r]).convert("RGB")
            y, rp = degistir(K, D, A.fd, isler)
            hedef = os.path.join(o, f"r{r:02d}.jpg"); y.save(hedef, quality=95, subsampling=0)
            Ka = np.asarray(K).astype(int); B = np.asarray(Image.open(hedef).convert("RGB")).astype(int)
            m = np.ones(Ka.shape[:2], bool)
            for i in isler:
                x0, y0, x1, y1 = i["kutu"]; m[y0:y1, x0:x1] = False
            _d = np.abs(Ka - B).max(2)[m]; dis = int(_d.max()); p999 = float(np.percentile(_d, 99.9)); hata = max(x["hata"] for x in rp)
            yazi = " ".join(t for x in rp for t in x["yeni"]).lower(); yas = [s for s in YASAK if s in yazi]
            R[f"r{r}"] = dict(kutu_disi=dis, kutu_disi_p999=round(p999, 1), olcum_hata=hata, yasak=yas)
            if p999 > 12 or dis > 45 or hata >= 40 or yas:
                ok = False; R["notlar"].append(f"r{r} metin FAIL dis={dis} p99.9={p999:.1f} hata={hata} yasak={yas}")
        # etiketler (metinli kartlarda metin sonrasi)
        for r in sorted(ETIKET):
            g = os.path.join(o, f"r{r:02d}.jpg") if r in METIN else src[r]
            kod, out = py(os.path.join(HERE, "cerceve_etiket.py"), g, os.path.join(o, f"r{r:02d}.jpg"), A.fd)
            R[f"r{r}_etiket"] = out[-2] if len(out) > 1 else out
            if not out or out[-1] != "PASS":
                ok = False; R["notlar"].append(f"r{r} etiket FAIL {out[-2:]}")
        # r12 genel kagit
        kod, out = py(os.path.join(HERE, "kart12_kagit_genel.py"), src[12], D_PATH(A), A.fd, os.path.join(o, "r12.jpg"), a, b)
        R["r12"] = out[-2] if len(out) > 1 else out
        if kod != 0:
            ok = False; R["notlar"].append(f"r12 FAIL {out[-2:]}")
        # r2 iki sutun: ciftin krem 02'si (kart02_yeni78 ile ayni yol)
        import galeri77_kur as GK
        if c == "CANCER_LIBRA":
            krem = os.path.join(ROOT, "data/pod/cl_galeri_krem_kaynak/02_format.jpg")
        else:
            mb = Image.open(os.path.join(A.kaynak, c, "BASKI_MIDNIGHT_BLUE.jpg")).convert("RGB")
            cl_mb = Image.open(os.path.join(A.kaynak, "CANCER_LIBRA", "BASKI_MIDNIGHT_BLUE.jpg")).convert("RGB")
            V, _ = GK.sanal_kapak(mb, cl_mb)
            im = Image.open(os.path.join(GK.KREM_CL, "02_format.jpg")).convert("RGB"); GK.kart02(im, V)
            krem = os.path.join(o, "_krem02.jpg"); im.save(krem, quality=95, subsampling=0)
        kod, out = py(os.path.join(HERE, "kart02_iki_sutun.py"), krem, D_PATH(A), A.fd, os.path.join(o, "r02.jpg"), a, b)
        if os.path.exists(os.path.join(o, "_krem02.jpg")):
            os.remove(os.path.join(o, "_krem02.jpg"))
        for jf in ("r02.json", "r12.json", "r12_ocr.png"):
            if os.path.exists(os.path.join(o, jf)):
                os.replace(os.path.join(o, jf), os.path.join(o, "_" + jf))
        R["r2"] = out[-2] if len(out) > 1 else out
        if kod != 0:
            ok = False; R["notlar"].append(f"r2 FAIL {out[-2:]}")
        else:
            # dogru cift: yeni r2'deki baski posteri (x 2012 merkez) ~ canli r2'deki baski posteri (x 1500 merkez)
            yeni = Image.open(os.path.join(o, "r02.jpg")).crop((2012 - PW // 2, 534, 2012 + PW // 2, 1294))
            eski = Image.open(src[2]).crop((1500 - PW // 2, 534, 1500 + PW // 2, 1294))
            ncc = float((gri(yeni) * gri(eski)).sum()); R["r2_poster_ncc"] = round(ncc, 4)
            if ncc < 0.97:
                ok = False; R["notlar"].append(f"r2 poster NCC {ncc:.3f} < 0.97")
        # boyut
        for r in YUKLE:
            p = os.path.join(o, f"r{r:02d}.jpg")
            if not os.path.exists(p) or Image.open(p).size != (3000, 2250):
                ok = False; R["notlar"].append(f"r{r} cikti yok/boyut")
        # once/sonra sayfasi
        sayfa(c, src, o)
    except Exception as e:                                      # noqa: BLE001
        ok = False; R["notlar"].append(f"HATA {type(e).__name__}: {e}")
    R["PASS"] = ok; R["sure_sn"] = round(time.time() - t0, 1)
    json.dump(R, open(os.path.join(o, "_QC.json"), "w"), ensure_ascii=False, indent=1, default=str)
    return R


def D_PATH(A):
    return A.duvar


def sayfa(c, src, o):
    tw, th = 600, 450; deg = [r for r in YUKLE if r != 3]
    S = Image.new("RGB", (2 * (2 * tw + 20), ((len(deg) + 1) // 2) * (th + 44) + 60), "white"); d = ImageDraw.Draw(S)
    f = ImageFont.truetype(os.path.join(ROOT, "assets/fonts/Montserrat[wght].ttf"), 24)
    d.text((10, 10), f"{c}: ONCE (canli) | SONRA. r6 silinir, r3 yalniz alt metin.", font=f, fill=(0, 0, 0))
    for i, r in enumerate(deg):
        x = (i % 2) * (2 * tw + 20); y = 50 + (i // 2) * (th + 44)
        d.text((x + 4, y), f"r{r}", font=f, fill=(0, 0, 0))
        S.paste(Image.open(src[r]).convert("RGB").resize((tw, th)), (x, y + 30))
        S.paste(Image.open(os.path.join(o, f"r{r:02d}.jpg")).convert("RGB").resize((tw, th)), (x + tw, y + 30))
    S.save(os.path.join(o, "ONCE_SONRA.jpg"), quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canli", required=True); ap.add_argument("--kaynak", required=True); ap.add_argument("--duvar", required=True)
    ap.add_argument("--fd", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=os.path.join(ROOT, "data/pod/pod78_ids.csv")); ap.add_argument("--ciftler", default="HEPSI")
    ap.add_argument("--is", dest="isler", type=int, default=4)
    A = ap.parse_args()
    rows = list(csv.DictReader(open(A.ids)))
    if A.ciftler != "HEPSI":
        sec = set(A.ciftler.split()); rows = [r for r in rows if r["cift"] in sec]
    os.makedirs(A.out, exist_ok=True)
    tab, t0 = [], time.time()
    with ProcessPoolExecutor(A.isler) as ex:
        for i, R in enumerate(ex.map(cift_isle, [(r["cift"], r["a"], r["b"], A) for r in rows]), 1):
            tab.append(R); g = time.time() - t0
            print(f"[{i}/{len(rows)}] {R['cift']} {'PASS' if R['PASS'] else 'FAIL ' + '; '.join(R['notlar'])[:300]} | gecen {g:.0f}s | "
                  f"kalan ~{g / i * (len(rows) - i):.0f}s | %{100 * i // len(rows)}", flush=True)
    with open(os.path.join(A.out, "TABLO.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "PASS", "r2_poster_ncc", "notlar", "sure_sn"], extrasaction="ignore")
        w.writeheader(); [w.writerow({**R, "notlar": " | ".join(R["notlar"])}) for R in tab]
    n = sum(1 for R in tab if R["PASS"])
    print(f"::warning::ESKI78 GORSEL URET PASS {n}/{len(tab)} | FAIL: " + "; ".join(f"{R['cift']} ({' | '.join(R['notlar'])[:150]})" for R in tab if not R["PASS"])[:900])
    sys.exit(0 if n == len(tab) else 1)


if __name__ == "__main__":
    main()
