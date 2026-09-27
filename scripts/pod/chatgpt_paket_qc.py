#!/usr/bin/env python3
"""ChatGPT CL paketi kalite kapisi (Serdar 27 Eyl 2026). Tek script, PASS/FAIL. Etsy/Prodigi cagrisi YOK.

Kullanim: chatgpt_paket_qc.py <paket.zip|klasor> <referans_klasoru> [--out out]
  paket    : /images/*.jpg, MANIFEST.csv (sira,dosya,tur,alt_metin), TEXTS.md, CHECKLIST.md
  referans : gercek baski dosyalari (renk basina 4x5 JPEG; ad icinde renk adi)
Kapilar:
  G1 gorsel: JPEG; yeni/guncel kart 3000x2250 (canli kart DNA, yatay 4:3); galeri <= 20 (MANIFEST satiri)
  G2 tasarim birebir: yeni/guncel gorselde referans tasarim aranir (cok olcekli NCC, gri, 500 px).
     NCC >= 0.90 -> birebir (PASS); 0.55-0.90 -> tasarim var ama birebir degil (FAIL, yeniden cizim suphesi);
     < 0.55 -> tasarim yok (BILGI). Esikler: yapistirilan tasarim olcekte ~0.97+, AI yeniden cizim 0.6-0.85 bandi.
  M1 metin kurali (metin_kurali.py ile ayni): OBA-free, bright white, omur yili, 12-colour, uzun/orta tire
  M2 ek yasak: instant download; cerceveli bolumde Hahnemuhle/cotton iddiasi
  M3 sinirlar: baslik <= 140, 13 etiket ve her biri <= 20, kisisellestirme <= 256 karakter
Cikti: out/QC_RAPOR.md + out/QC_TEMAS.jpg (her gorsel kucuk + skor). Cikis 0 PASS, 1 FAIL."""
import csv
import re
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np

YASAK = {
    "OBA-free": r"\bOBA[\s-]*free\b", "bright white": r"\bbright[\s-]+white\b",
    "omur yili": r"\b\d{2,4}\s*(?:[-–—]|to)?\s*(?:\d{2,4}\s*)?\+?\s*years?\b",
    "12-colour": r"\b12[\s-]*colou?rs?\b", "uzun/orta tire": r"[—–]", "instant download": r"\binstant\s+download",
}
NCC_BIREBIR, NCC_VAR = 0.90, 0.55


def ac(paket, hedef):
    p = Path(paket)
    if p.is_dir():
        return p
    with zipfile.ZipFile(p) as z:
        z.extractall(hedef)
    kok = [d for d in Path(hedef).rglob("MANIFEST.csv")]
    return kok[0].parent if kok else Path(hedef)


def gri(path, w):
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    h = round(im.shape[0] * w / im.shape[1])
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)


def _ara(img, ref, oranlar):
    best = (-1.0, 0, (0, 0))
    H, W = img.shape
    for oran in oranlar:
        th = int(round(H * oran)); tw = int(round(th * ref.shape[1] / ref.shape[0]))
        if tw >= W or th >= H or tw < 16:
            continue
        r = cv2.matchTemplate(img, cv2.resize(ref, (tw, th), interpolation=cv2.INTER_AREA), cv2.TM_CCOEFF_NORMED)
        _, v, _, loc = cv2.minMaxLoc(r)
        if v > best[0]:
            best = (float(v), th, loc)
    return best


def en_iyi_ncc(path, refs):
    """1) bulanik 300 px'te konum/olcek (yeniden cizime dayanikli bulma), 2) 1000 px'te ince olcek + sadakat NCC."""
    kaba = cv2.GaussianBlur(gri(path, 300), (5, 5), 0)
    ince_img = gri(path, 1000)
    sonuc = (0.0, None, 0.0)
    for ad, (ref_k, ref_i) in refs.items():
        v, th, _ = _ara(kaba, cv2.GaussianBlur(ref_k, (5, 5), 0), np.arange(0.10, 0.98, 0.01))
        if v < 0:
            continue
        oran = th / kaba.shape[0]
        fv, _, _ = _ara(ince_img, ref_i, np.arange(max(0.05, oran - 0.02), oran + 0.02, 0.001))
        if fv > sonuc[0] or (sonuc[1] is None):
            sonuc = (fv, ad, v)
    return sonuc


def bolum(md, anahtar):
    """'# ... anahtar ...' basligindan sonraki metin (bir sonraki basliga kadar)."""
    m = re.search(rf"^#+[^\n]*{anahtar}[^\n]*\n(.*?)(?=^#+ |\Z)", md, re.I | re.M | re.S)
    return m.group(1).strip() if m else None


def main():
    paket, refdir = sys.argv[1], Path(sys.argv[2])
    out = Path(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "out"); out.mkdir(exist_ok=True)
    kok = ac(paket, out / "_paket")
    satir, fail = [], 0

    def kayit(kapi, ok, ayrinti):
        nonlocal fail
        fail += 0 if ok else 1
        satir.append(f"| {kapi} | {'PASS' if ok else 'FAIL'} | {ayrinti} |")

    man = list(csv.DictReader(open(kok / "MANIFEST.csv", encoding="utf-8-sig")))
    kayit("G1 galeri <= 20", len(man) <= 20, f"{len(man)} satir")
    def merkez(a):
        # Referansin ORTA bolgesi (birlesik sembol + isimler): duz baski ya da poster gorseli fark etmez.
        h, w = a.shape
        return a[int(h * 0.22):int(h * 0.78), int(w * 0.18):int(w * 0.82)]
    refs = {p.stem: (merkez(gri(p, 300)), merkez(gri(p, 1000))) for p in sorted(refdir.rglob("*.jpg"))}
    kucukler = []
    for r in man:
        f = kok / "images" / Path(r["dosya"]).name
        if not f.exists():
            f = kok / r["dosya"]
        if not f.exists():
            kayit(f"G1 {r['dosya']}", False, "dosya yok"); continue
        im = cv2.imread(str(f))
        # 27 Eyl: canli kart DNA'si yatay 4:3 = 3000x2250 (yeni/guncel kart); mevcut gorseller oldugu gibi kalir.
        tur_on = (r.get("tur") or "").strip().lower()
        boyut_ok = im is not None and ((im.shape[1], im.shape[0]) == (3000, 2250) if tur_on in ("yeni", "guncel") else True)
        ok = im is not None and boyut_ok and f.suffix.lower() in (".jpg", ".jpeg")
        kayit(f"G1 {f.name}", ok, f"{None if im is None else (im.shape[1], im.shape[0])}")
        tur = (r.get("tur") or "").strip().lower()
        if tur in ("yeni", "guncel") and refs and im is not None:
            v, ad, kaba = en_iyi_ncc(f, refs)
            if kaba < NCC_VAR:
                satir.append(f"| G2 {f.name} | BILGI | tasarim bulunmadi (konum NCC {kaba:.3f}) |")
            elif v >= NCC_BIREBIR:
                kayit(f"G2 {f.name}", True, f"birebir NCC {v:.3f} (konum {kaba:.3f}, {ad})")
            else:
                kayit(f"G2 {f.name}", False, f"tasarim var ama birebir degil NCC {v:.3f} (konum {kaba:.3f}, {ad})")
            kucukler.append((cv2.resize(im, (320, 400)), f"{r.get('sira')} {v:.2f}"))
    md = (kok / "TEXTS.md").read_text(encoding="utf-8")
    ek = "\n".join((kok / n).read_text(encoding="utf-8") for n in ("CHECKLIST.md",) if (kok / n).exists())
    for ad, rx in YASAK.items():
        bul = [m.group(0) for m in re.finditer(rx, md + "\n" + "\n".join(r.get("alt_metin", "") for r in man), re.I)]
        kayit(f"M1/M2 {ad}", not bul, ", ".join(map(repr, bul[:5])) or "yok")
    cer = bolum(md, "FRAMED") or ""
    iddia = re.findall(r"hahnem|cotton|photo rag", cer, re.I)
    kayit("M2 cerceveli kagit iddiasi", not iddia, ", ".join(iddia) or "yok")
    # 27 Eyl: baslik/etiket/aciklama Claude'da onaylandi; paket yalniz gorsel metinlerini tasir.
    # M3 yalniz ilgili bolum pakette varsa denetlenir.
    if bolum(md, "title") is not None:
        baslik = (bolum(md, "title") or "").splitlines()[0:1]
        kayit("M3 baslik <= 140", bool(baslik) and len(baslik[0]) <= 140, f"{len(baslik[0]) if baslik else 'yok'} karakter")
    if bolum(md, "tag") is not None:
        et = [t.strip(" -*`\t") for t in re.split(r"[,\n]", bolum(md, "tag") or "") if t.strip(" -*`\t")]
        kayit("M3 13 etiket <= 20", len(et) == 13 and all(len(t) <= 20 for t in et),
              f"{len(et)} etiket; uzun: {[t for t in et if len(t) > 20]}")
    if bolum(md, "personali") is not None:
        kis = bolum(md, "personali") or ""
        kayit("M3 kisisellestirme <= 256", 0 < len(kis) <= 256, f"{len(kis)} karakter")
    uzun_alt = [r.get("dosya") for r in man if len(r.get("alt_metin") or "") > 500]
    kayit("M3 alt metin <= 500", not uzun_alt, ", ".join(uzun_alt) or "yok")
    if kucukler:
        satirlar = [kucukler[i:i + 5] for i in range(0, len(kucukler), 5)]
        tuval = np.full((len(satirlar) * 440, 5 * 330, 3), 255, np.uint8)
        for i, s in enumerate(satirlar):
            for j, (k, yazi) in enumerate(s):
                tuval[i * 440:i * 440 + 400, j * 330:j * 330 + 320] = k
                cv2.putText(tuval, yazi, (j * 330 + 5, i * 440 + 430), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.imwrite(str(out / "QC_TEMAS.jpg"), tuval, [cv2.IMWRITE_JPEG_QUALITY, 85])
    genel = "PASS" if fail == 0 else f"FAIL ({fail})"
    (out / "QC_RAPOR.md").write_text("# ChatGPT CL paketi QC\n\n| kapi | sonuc | ayrinti |\n|---|---|---|\n"
                                     + "\n".join(satir) + f"\n\nGENEL: {genel}\n", encoding="utf-8")
    print("GENEL", genel)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
