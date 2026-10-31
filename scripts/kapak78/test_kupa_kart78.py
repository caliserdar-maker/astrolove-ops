#!/usr/bin/env python3
"""kupa_kart78 topla sentetik testi (Etsy yok, cizim yok): Serdar 31 Eki 1a/2b.
T1 ayni burc K02 metni = galeri alt metni sira 2 (tek kaynak)
T2 gece MANIFEST'iyle sha kaniti: ayni burc K02 degisir, digerleri ayni -> PASS; DEGISIM.csv, KONTAK_K02_AYNI_BURC
T3 ayni burc disi bir kart degisirse: gece dosyasi yoksa IZINSIZ_DEGISIM FAIL; varsa GECE_DOSYASI (MANIFEST sha = gece) PASS
T4 ayni burc K02 degismediyse -> FAIL
T5 istisna MANIFEST ve OZET'te gorunur; gece FAIL cift (GEMINI_SCORPIO) izinli
Calistir: python3 scripts/kapak78/test_kupa_kart78.py"""
import csv
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kupa_kart78 as M  # noqa: E402
from PIL import Image  # noqa: E402

sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


CIFT = [("CANCER_LIBRA", "Cancer", "Libra"), ("LEO_LEO", "Leo", "Leo"), ("GEMINI_SCORPIO", "Gemini", "Scorpio")]


def jpg(p, renk):
    Image.new("RGB", (40, 30), renk).save(p, quality=90)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kur(t, degis=(), istisna=True, gece=False):
    """t/_d: yeni kosu SONUC + jpg; t/once.csv: gece MANIFEST (GEMINI_SCORPIO FAIL)."""
    d = t / "_d"; d.mkdir(parents=True)
    with open(t / "ciftler.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "a", "b"]); w.writerows([[str(i), c, a, b] for i, (c, a, b) in enumerate(CIFT)])
    (t / "secim.txt").write_text("\n".join(c for c, _, _ in CIFT))
    once = []
    for n, (c, a, b) in enumerate(CIFT):
        kartlar = []
        for j, (kk, g, _) in enumerate(M.KARTLAR):
            renk_once = (10 * n, 10 * j, 50)
            renk = (10 * n, 10 * j, 99) if (c, kk) in degis else renk_once
            s = jpg(d / f"{c}_{kk}.jpg", renk)
            ist = ("kopuk_ton 3 px max 4/255 (Serdar 31 Eki karar 1a)" if (c, kk) == ("GEMINI_SCORPIO", "K05") and istisna else "")
            kartlar.append(dict(kart=kk, galeri_no=g, dosya=f"{c}_{kk}.jpg", sha256=s, istisna=ist))
            tmp = t / (f"{c}_{kk}.jpg" if gece else "tmp.jpg")       # gece=True: gece dosyasi once.csv klasorunde
            so = jpg(tmp, renk_once)
            once.append(dict(cift=c, kart=kk, galeri_no=g, dosya=f"{c}_{kk}.jpg", sha256=so if c != "GEMINI_SCORPIO" else "",
                             durum="PASS" if c != "GEMINI_SCORPIO" else "FAIL", neden=""))
        kay = dict(cift=c, durum="PASS", kartlar=kartlar)
        if a == b:
            kay["k02_ayni_burc"] = dict(metin=M.k02_ayni_metin(a), genislik_px=900, izin_px=1800, satir=1)
        (d / f"SONUC_{c}.json").write_text(json.dumps(kay))
    with open(t / "once.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "kart", "galeri_no", "dosya", "sha256", "durum", "neden"]); w.writeheader(); w.writerows(once)
    return t


def topla(t, yeni=None, ref=None):
    if yeni is not None:
        (t / "yeni.txt").write_text("\n".join(yeni))
    rc = M.main(["topla", "--dir", str(t / "_d"), "--secim", str(t / "secim.txt"), "--out", str(t / "o"), "--ciftler-csv",
                 str(t / "ciftler.csv"), "--onceki", str(t / "once.csv"), "--onceki-ad", "GECE", "--yeni",
                 str(t / ("yeni.txt" if yeni is not None else "secim.txt"))] + (["--ref", str(ref), "--ref-ad", "TEMP/KUPA_KART78/REF"] if ref else []))
    deg = list(csv.DictReader(open(t / "o" / "DEGISIM.csv")))
    return rc, deg, (t / "o" / "OZET.md").read_text(), list(csv.DictReader(open(t / "o" / "MANIFEST.csv")))


W0 = Path(tempfile.mkdtemp(prefix="kk78_"))
try:
    k("T1 ayni burc K02 metni galeri alt metni", M.k02_ayni_metin("Leo") == "Two Leo signs joined into one shared symbol on the mug",
      M.k02_ayni_metin("Leo"))
    izin = {("LEO_LEO", "K02")} | {("GEMINI_SCORPIO", kk) for kk, _, _ in M.KARTLAR}
    rc, deg, oz, man = topla(kur(W0 / "a", degis=izin))
    tur = {(x["cift"], x["kart"]): x["tur"] for x in deg}
    k("T2 izinli degisim PASS, digerleri AYNI", rc == 0 and tur[("LEO_LEO", "K02")] == "IZINLI_DEGISIM"
      and all(v == "AYNI" for (c, kk), v in tur.items() if (c, kk) not in izin), tur)
    k("T2b KONTAK_K02_AYNI_BURC + OZET metin satiri", (W0 / "a" / "o" / "KONTAK_K02_AYNI_BURC.jpg").is_file()
      and "Two Leo signs joined into one shared symbol on the mug" in oz)
    k("T5 istisna MANIFEST + OZET", any(r["cift"] == "GEMINI_SCORPIO" and r["kart"] == "K05" and "3 px" in r["istisna"] for r in man)
      and "GEMINI_SCORPIO K05: kopuk_ton 3 px" in oz)
    rc, deg, oz, _ = topla(kur(W0 / "b", degis=izin | {("CANCER_LIBRA", "K03")}))
    k("T3 izinsiz degisim, gece dosyasi yok -> FAIL", rc == 1 and "gece dosyasi yok" in oz, rc)
    rc, deg, oz, man = topla(kur(W0 / "b2", degis=izin | {("CANCER_LIBRA", "K03")}, gece=True))
    gs = next(x for x in csv.DictReader(open(W0 / "b2" / "once.csv")) if x["cift"] == "CANCER_LIBRA" and x["kart"] == "K03")["sha256"]
    ms = next(r for r in man if r["cift"] == "CANCER_LIBRA" and r["kart"] == "K03")
    k("T3b izinsiz fark + gece dosyasi -> GECE_DOSYASI, MANIFEST sha = gece, PASS", rc == 0 and ms["sha256"] == gs
      and hashlib.sha256((W0 / "b2" / "o" / "CANCER_LIBRA_K03.jpg").read_bytes()).hexdigest() == gs and "GECE_DOSYASI" in oz, (rc, ms))
    so = next(x for x in json.loads((W0 / "b2" / "o" / "SONUC_CANCER_LIBRA.json").read_text())["kartlar"] if x["kart"] == "K03")
    k("T3c SONUC sevk edilen gece dosyasinin sha'si + yeniden_sha256 + isaret (inceleme 31 Eki)", so["sha256"] == gs
      and so.get("gece_dosyasi") is True and so.get("yeniden_sha256") not in (None, gs), so)
    k("T3d OZET yeniden uretilen cift listesi", "Bu kosuda yeniden uretilen ciftler (3): CANCER_LIBRA, LEO_LEO, GEMINI_SCORPIO" in oz)
    rc, deg, oz, _ = topla(kur(W0 / "c", degis=izin - {("LEO_LEO", "K02")}))
    k("T4 ayni burc K02 degismedi -> FAIL", rc == 1 and "LEO_LEO K02 degismedi" in oz, rc)
    rc, deg, oz, _ = topla(kur(W0 / "c2", degis=izin - {("LEO_LEO", "K02")}), yeni=["CANCER_LIBRA", "GEMINI_SCORPIO"])
    k("T4b ayni burc cift bu kosuda yeniden uretilmediyse (tabandan) K02 ayni -> FAIL degil (31 Eki kosu 41220599136)",
      rc == 0 and "degismedi" not in oz.split("## Ayni burc")[0].replace("ortak kod degismedi", ""), (rc, [l for l in oz.splitlines() if "FAIL" in l][:3]))
    # Serdar 31 Eki 2a: CANCER_LIBRA kiyas referansi F-A sonrasi uretim (KUPA_KART78/<damga>/CANCER_LIBRA_K0*.jpg), esik ayni
    tr = kur(W0 / "r1", degis=izin); ref = W0 / "r1" / "ref"; ref.mkdir()
    for kk, _, _ in M.KARTLAR:
        shutil.copy(tr / "_d" / f"CANCER_LIBRA_{kk}.jpg", ref / f"CANCER_LIBRA_{kk}.jpg")
    rc, deg, oz, _ = topla(tr, ref=ref)
    k("T6 referans KUPA_KART78 adlandirmasi (CANCER_LIBRA_K0x.jpg), ayni dosya -> kiyas PASS, OZET referans adi", rc == 0
      and "CANCER_LIBRA kiyasi (referans TEMP/KUPA_KART78/REF;" in oz and "| K03 | True |" in oz, rc)
    tr2 = kur(W0 / "r2", degis=izin); ref2 = W0 / "r2" / "ref"; ref2.mkdir()
    for j, (kk, _, _) in enumerate(M.KARTLAR):
        jpg(ref2 / f"CANCER_LIBRA_{kk}.jpg", (250, 250, 250))
    rc, deg, oz, _ = topla(tr2, ref=ref2)
    k("T6b referanstan buyuk fark -> kiyas FAIL (esik ayni: ort <= 1,0, max <= 16)", rc == 1 and "| FAIL |" in oz.split("CANCER_LIBRA kiyasi")[1], rc)
    y = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "kupa-kart78.yml").read_text()
    k("T6c is akisi: kiyas_damga varsayilani 20261031_161948, kaynak TEMP/KUPA_KART78, CANCER_LIBRA_K0*.jpg", 'default: "20261031_161948"' in y
      and 'TEMP/KUPA_KART78/$R" _ref --include "CANCER_LIBRA_K0*.jpg"' in y and "KART_SABLON_ORNEK" not in y)
finally:
    shutil.rmtree(W0, ignore_errors=True)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
