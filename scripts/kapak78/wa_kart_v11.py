#!/usr/bin/env python3
"""Galeri v11 W02-W06 bilgi kartlari (Merkez 29 Eki, Serdar kararlari; 28 Eki kart sablonu, wa_kupa_kart_ornek.py kartlari ve kapilari).
ETSY API YOK, Canva yok. Kart cizimi / metin / yerlesim / renk kapilari wa_kupa_kart_ornek.kart_isle (28 Eki onayli kod, aynen).
Dosyalar (docs/kart_sablon/ONERI_W02_W06_29EKI.md, Merkez 29 Eki uygun):
  <CIFT>_W02_SEMBOL.jpg   S1 sembol karti: kupa-printful-sonuc kupa_uretim/sembol/<CIFT> (sol / sag / ana)
  <CIFT>_W03_KISISEL.jpg  S2: MB kisisellestirilmis poster TEMP/MOTOR/SOSYAL/78/<CIFT>.png (isim / tagline IG_78_ORNEK_ISIM_TAGLINE.csv)
  ORTAK_W04_FORMAT.jpg    S3 tablo, "14 Sizes" (format_boy_sayisi 14, Serdar 29 Eki); yalniz --ortak
  <CIFT>_W05_SUREC.jpg    S4: CI poster = ref/kapak_ci CI_<CIFT>.png (A kesimi 901,601-2107,2118)
  <CIFT>_W06_GENEL.jpg    S5 "Choose Your Color" (28 Eki sirasi MB, DB, PW, CI, WP): CI / PW = A kesimleri; MB / DB / WP = v11 W07 / W08 /
                          W10 poster kutusu PASPARTU_IC (paspartu disarida; 29 Eki olcumu asagida)
W03 KAYNAK KAPISI (Merkez 29 Eki "once olc; tutmazsa DUR"; oran Serdar 29 Eki: 4:5, SOSYAL/78 4800x6000): oran 4:5 (|g/y - 4/5| <= ORAN_TOL), renk = MB (poster medyan CIELAB en yakin
  renk MB ve uzaklik < esik; referanslar ayni ciftin bes v11 posteri, esik = en kucuk ikili uzakligin yarisi, galeri_v11_kapi yontemi),
  isimler = CSV (tesseract: iki isim de okunur ve sol isim solda). Biri tutmazsa DUR (olcum OZET'e yazilir, kart yazilmaz).
PASPARTU_IC: onayli CANCER_LIBRA W07 / W08 / W10 kenar olcumu 29 Eki (Pillow 11.0.0, satir 900-1800 / sutun 1200-1800 ortalamasi):
  paspartu L 240-242, gecis pikseli x 983 / x 2023 / y 679 / y 2031, poster x 984-2022, y 680-2030. Merkez'in 971-2035 x 667-2043
  kutusu her kenarda 12-13 px paspartu icerir (beyaz serit), kullanilmaz. KENAR KAPISI: kirpimin dis satir / sutun ortalamasi ile 3 px
  icerisinin farki <= KENAR_ESIK (olcum: poster ici komsu fark <= 3, gecis pikseli >= 95).
Cikti <out>/: kartlar, MANIFEST_W02_W06.csv (cift, ad, dosya, sha256, boyut, kaynak, durum), KART_OZET_V11_<CIFT>.json. Cikis 0 / DUR."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wa_kupa_kart_ornek as WA  # noqa: E402
import kart_sablon as S  # noqa: E402
import yd_kart_ornek as K  # noqa: E402

PASPARTU_IC = (984, 680, 2023, 2031)        # PIL crop (sag / alt haric)
KENAR_ESIK = 20
ORAN = 4 / 5                 # Serdar 29 Eki (W03 kaynagi 4:5; S2 karti 1140x1425, kapilar PASS yerel olcumu)
ORAN_TOL = 0.002
ALAN = ["cift", "ad", "dosya", "sha256", "boyut", "kaynak", "durum"]


def kenar_kapisi(im, ad):
    """kirpim kenarinda paspartu / beyaz serit yok: dis satir / sutun ortalamasi ile 3 px icerisi arasindaki fark <= KENAR_ESIK"""
    a = np.asarray(im.convert("L"), np.float32)
    f = dict(sol=abs(a[:, 0].mean() - a[:, 3].mean()), sag=abs(a[:, -1].mean() - a[:, -4].mean()),
             ust=abs(a[0].mean() - a[3].mean()), alt=abs(a[-1].mean() - a[-4].mean()))
    kotu = {k: round(float(v), 1) for k, v in f.items() if v > KENAR_ESIK}
    if kotu:
        raise SystemExit(f"DUR: {ad} kirpim kenarinda serit (fark > {KENAR_ESIK}): {kotu}")
    return {k: round(float(v), 1) for k, v in f.items()}


def renk_mb(poster, refs):
    """poster (W03 kaynagi) medyan CIELAB: en yakin v11 renk MB ve uzaklik < esik"""
    import galeri_v10_liste as L
    tam = (0, 0, poster.width, poster.height)
    v = L.renk_ozet(poster.convert("RGB"), tam)
    ref = {k: L.renk_ozet(im, (0, 0, im.width, im.height)) for k, im in refs.items()}
    d = {k: round(float(np.linalg.norm(v - x)), 1) for k, x in ref.items()}
    ks = list(ref)
    esik = min(float(np.linalg.norm(ref[x] - ref[y])) for i, x in enumerate(ks) for y in ks[i + 1:]) / 2
    yakin = min(d, key=d.get)
    return dict(uzaklik=d, esik=round(esik, 1), en_yakin=yakin, PASS=yakin == "MB" and d["MB"] < esik)


def _ocr_tsv(im, psm):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        im.save(f.name)
        r = subprocess.run(["tesseract", f.name, "stdout", "--psm", str(psm), "tsv"], capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(f"DUR: tesseract hata {r.stderr[-300:]}")
    out = []
    for sat in r.stdout.splitlines()[1:]:
        s = sat.split("\t")
        if len(s) == 12 and s[11].strip():
            out.append((re.sub(r"[^A-Z]", "", s[11].upper()), int(s[6])))
    return out


def isim_ocr(p, sol, sag):
    """tesseract tsv: iki isim AYNI goruntu varyantinda okunur (buyuk harf, sozcuk esitligi) ve sol isim solda.
    29 Eki CI 40877328600: tam sayfa (4800x6000, psm 11) iki ciftte birer ismi okuyamadi (koyu zemin, altin yazi). Varyantlar
    (sirayla, ilk tutan): tam sayfa; isim bandi (poster yuksekliginin %50-90'i, 2400 px genislige) gri / ters / esikli, psm 11 ve 6."""
    from PIL import ImageOps
    im = Image.open(p).convert("RGB")
    g, y = im.size
    bant = im.crop((0, int(y * 0.50), g, int(y * 0.90))).convert("L")
    bant = bant.resize((2400, round(2400 * bant.height / bant.width)))
    ters = ImageOps.invert(bant)
    esik = ters.point(lambda v: 0 if v < 150 else 255)
    deneme = [("tam", im, 11), ("bant", bant, 11), ("ters", ters, 11), ("esik", esik, 11), ("ters6", ters, 6), ("esik6", esik, 6)]
    son = {}
    for ad, gr, psm in deneme:
        x = {}
        for w, xx in _ocr_tsv(gr, psm):
            if w in (sol, sag) and w not in x:
                x[w] = xx
        son[ad] = x
        if sol in x and sag in x and (sol == sag or x[sol] < x[sag]):
            return dict(okunan=x, varyant=ad, PASS=True)
    return dict(okunan=son, PASS=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("--cift", "--a", "--b", "--sembol", "--mb-poster", "--isim-csv", "--kesim", "--galeri", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--ortak", action="store_true", help="ORTAK_W04_FORMAT de uret")
    ap.add_argument("--kaynak", default="", help="MANIFEST kaynak sutunu (kart_sablon@<commit>)")
    a = ap.parse_args(argv)
    c, out = a.cift, Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sem, kes, gal = Path(a.sembol), Path(a.kesim), Path(a.galeri)
    sat = next((r for r in csv.DictReader(open(a.isim_csv, encoding="utf-8")) if r["cift"] == c), None)
    if not sat:
        raise SystemExit(f"DUR: {c} isim CSV'de yok")
    gerek = [sem / f"{x}.png" for x in ("sol", "sag", "ana")] + [kes / f"CI_{c}.png", kes / f"PW_{c}.png", Path(a.mb_poster)] + \
        [gal / f"{c}_{w}.jpg" for w in ("W07_MB", "W08_DB", "W10_WP")]
    eksik = [str(p) for p in gerek if not p.exists()]
    if eksik:
        raise SystemExit(f"DUR: girdi eksik: {eksik}")
    kenar, ozet = {}, dict(cift=c, isim=[sat["sol_isim"], sat["sag_isim"]], tagline=sat["tagline"])
    paspartu = {}
    for w, r in (("W07_MB", "MB"), ("W08_DB", "DB"), ("W10_WP", "WP")):
        im = Image.open(gal / f"{c}_{w}.jpg").convert("RGB")
        if im.size != (3000, 2250):
            raise SystemExit(f"DUR: {c}_{w}.jpg {im.size} (3000x2250 beklenir)")
        paspartu[r] = im.crop(PASPARTU_IC); kenar[r] = kenar_kapisi(paspartu[r], f"{c}_{w} poster kirpimi")
    ci = Image.open(kes / f"CI_{c}.png").convert("RGB"); pw = Image.open(kes / f"PW_{c}.png").convert("RGB")
    kenar["CI"] = kenar_kapisi(ci, f"CI_{c}.png"); kenar["PW"] = kenar_kapisi(pw, f"PW_{c}.png")
    mb = Image.open(a.mb_poster)
    g, y = mb.size
    w03 = dict(boyut=[g, y], oran=round(g / y, 4), oran_PASS=abs(g / y - ORAN) <= ORAN_TOL,
               renk=renk_mb(mb, dict(MB=paspartu["MB"], DB=paspartu["DB"], PW=pw, CI=ci, WP=paspartu["WP"])),
               isim=isim_ocr(Path(a.mb_poster), sat["sol_isim"].upper(), sat["sag_isim"].upper()))
    ozet.update(w03_kaynak=w03, kenar=kenar)
    if not (w03["oran_PASS"] and w03["renk"]["PASS"] and w03["isim"]["PASS"]):
        (out / f"KART_OZET_V11_{c}.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False), encoding="utf-8")
        raise SystemExit(f"DUR: {c} W03 kaynak kapisi: {json.dumps(w03, ensure_ascii=False)}")
    renkler = [("Midnight Blue", paspartu["MB"]), ("Deep Black", paspartu["DB"]), ("Pure White", pw),
               ("Champagne Ivory", ci), ("Warm Parchment", paspartu["WP"])]
    if [r for r, _ in renkler] != [r for r, _ in WA.RENKLER]:
        raise SystemExit("DUR: renk sirasi 28 Eki sablonundan farkli")
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()
    yok = lambda f: (lambda: (*f(), ()))
    islem = [(f"{c}_W02_SEMBOL.jpg", "S1_SEMBOL", lambda: S.sembol_kart(a.a, a.b, sem, "Personalized with your two names and your message")),
             (f"{c}_W03_KISISEL.jpg", "S2_KISISEL", yok(lambda: WA.wa_s2(a.a, a.b, mb.convert("RGB"))))]
    if a.ortak:
        islem.append(("ORTAK_W04_FORMAT.jpg", "S3_FORMAT", yok(WA.wa_s3)))
    islem += [(f"{c}_W05_SUREC.jpg", "S4_SUREC", yok(lambda: WA.wa_s4(ci))),
              (f"{c}_W06_GENEL.jpg", "S5_GENEL", yok(lambda: WA.wa_s5(renkler)))]
    sonuc, rapor, jb = WA.kart_isle(islem, WA.beklenen(a.a, a.b))
    satirlar = []
    for ad, b in jb.items():
        (out / ad).write_bytes(b)
        sahip = "ORTAK" if ad.startswith("ORTAK_") else c
        satirlar.append(dict(cift=sahip, ad=ad[len(sahip) + 1:-4], dosya=ad, sha256=hashlib.sha256(b).hexdigest(), boyut=len(b),
                             kaynak=a.kaynak, durum="PASS"))
    girdi = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in gerek}
    ozet.update(kartlar=rapor, girdi_sha256=girdi, surum=K.SURUM)
    (out / f"KART_OZET_V11_{c}.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    m = out / "MANIFEST_W02_W06.csv"; yeni = not m.exists()
    with open(m, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN)
        if yeni:
            w.writeheader()
        w.writerows(satirlar)
    print(f"KART V11 {c}: {len(jb)} kart PASS (metin, Title Case, yasak, renk, yerlesim; W03 kaynak oran / MB / isim; kenar) -> {out}")
    return 0


def kontak(galeri, kart, cift, out):
    """10 gorsel galeri sirasi W01-W10 (W01 / W07-W10 v11 tasima, W02-W06 bu betik) -> KONTAK_V11_<CIFT>.jpg"""
    g, k = Path(galeri), Path(kart)
    ad = ["W01_KAPAK", "W02_SEMBOL", "W03_KISISEL", "W04_FORMAT", "W05_SUREC", "W06_GENEL", "W07_MB", "W08_DB", "W09_PW", "W10_WP"]
    yol = [(k if 2 <= i <= 6 else g) / (f"ORTAK_{n}.jpg" if i == 4 else f"{cift}_{n}.jpg") for i, n in enumerate(ad, 1)]
    eksik = [p.name for p in yol if not p.exists()]
    if eksik:
        raise SystemExit(f"DUR: kontak icin eksik: {eksik}")
    sat = [[(i, n, Image.open(p)) for i, (n, p) in enumerate(zip(ad[:5], yol[:5]), 1)],
           [(i, n, Image.open(p)) for i, (n, p) in enumerate(zip(ad[5:], yol[5:]), 6)]]
    b, q = S.kontak_sayfa(sat, [cift, ""], kb_sinir=400)
    Path(out).write_bytes(b)
    print(f"{Path(out).name} {len(b) / 1024:.0f} KB q{q} (10 gorsel, galeri sirasi W01-W10)")
    return 0


if __name__ == "__main__":
    import wa_kart_v11 as _M
    if sys.argv[1:2] == ["kontak"]:
        sys.exit(_M.kontak(*sys.argv[2:6]))
    sys.exit(_M.main())
