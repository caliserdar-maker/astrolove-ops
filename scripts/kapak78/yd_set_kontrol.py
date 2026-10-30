#!/usr/bin/env python3
"""YD 10'lu set dosya kontrolu (Serdar onayi 30 Eki, Is C madde 3). ETSY API YOK, ag yok; yalniz yerel klasor okunur.
Beklenen: data/pod/yd78_ids.csv ciftleri x (Y01-Y03, Y05-Y10) + ORTAK_Y04 = 703 dosya.
Kapilar (dosya basina): ad kalibi + cift listede, bos degil, JPEG tam acilir (load), 3000x2250 (Serdar 27 Eki standardi).
Set kapilari: eksik / fazla dosya, sha256 tekrari (ORTAK_Y04 tek dosya oldugu icin HICBIR tekrar izinli degil).
Cikti: SET_KONTROL.csv (dosya, cift, kart, bayt, genislik, yukseklik, sha256, durum, neden) + OZET.md. Cikis 0 = PASS, 1 = FAIL."""
import argparse
import csv
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

BOYUT = (3000, 2250)
KARTLAR = (1, 2, 3, 5, 6, 7, 8, 9, 10)
ORTAK = "ORTAK_Y04.jpg"
AD = re.compile(r"^([A-Z]+_[A-Z]+)_Y(\d{2})\.jpg$")


def beklenen(ciftler):
    return {f"{c}_Y{k:02d}.jpg" for c in ciftler for k in KARTLAR} | {ORTAK}


def dosya_kontrol(p, ciftler):
    s = dict(dosya=p.name, cift="", kart="", bayt=p.stat().st_size, genislik="", yukseklik="", sha256="", neden=[])
    if p.name == ORTAK:
        s.update(cift="ORTAK", kart=4)
    else:
        m = AD.match(p.name)
        if not m:
            s["neden"].append("ad kalibi <CIFT>_Y<NN>.jpg degil")
        else:
            s.update(cift=m.group(1), kart=int(m.group(2)))
            if m.group(1) not in ciftler:
                s["neden"].append("cift yd78_ids.csv'de yok")
            if int(m.group(2)) not in KARTLAR:
                s["neden"].append(f"kart Y{m.group(2)} beklenmiyor")
    if s["bayt"] == 0:
        s["neden"].append("bos dosya")
        return s
    b = p.read_bytes()
    s["sha256"] = hashlib.sha256(b).hexdigest()
    try:
        with Image.open(p) as im:
            fmt, (w, h) = im.format, im.size
            im.load()
        s.update(genislik=w, yukseklik=h)
        if fmt != "JPEG" or b[:3] != b"\xff\xd8\xff":
            s["neden"].append(f"JPEG degil ({fmt})")
        if (w, h) != BOYUT:
            s["neden"].append(f"boyut {w}x{h} != {BOYUT[0]}x{BOYUT[1]}")
    except Exception as e:  # noqa: BLE001
        s["neden"].append(f"bozuk ({type(e).__name__})")
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--ciftler", default="data/pod/yd78_ids.csv")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ciftler = [r["cift"].strip() for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if (r.get("cift") or "").strip()]
    if len(ciftler) != 78 or len(set(ciftler)) != 78:
        print(f"::error::cift listesi 78 tekil degil ({len(ciftler)} / {len(set(ciftler))})"); return 1
    bek = beklenen(ciftler)
    d = Path(a.dir)
    dosyalar = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg"))
    satir = []
    for n, p in enumerate(dosyalar, 1):
        satir.append(dosya_kontrol(p, set(ciftler)))
        if n % 100 == 0 or n == len(dosyalar):
            print(f"[{n}/{len(dosyalar)}] {100 * n // max(1, len(dosyalar))}%", flush=True)
    adlar = {s["dosya"] for s in satir}
    for s in satir:
        if s["dosya"] not in bek and not s["neden"]:
            s["neden"].append("beklenen listede yok (fazla)")
    shad = defaultdict(list)
    for s in satir:
        if s["sha256"]:
            shad[s["sha256"]].append(s["dosya"])
    tekrar = {h: v for h, v in shad.items() if len(v) > 1}
    for s in satir:
        if s["sha256"] in tekrar:
            s["neden"].append("ayni sha256: " + " ".join(x for x in tekrar[s["sha256"]] if x != s["dosya"]))
    eksik = sorted(bek - adlar)
    for s in satir:
        s["durum"] = "FAIL" if s["neden"] else "PASS"
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "SET_KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dosya", "cift", "kart", "bayt", "genislik", "yukseklik", "sha256", "durum", "neden"])
        for s in satir:
            w.writerow([s["dosya"], s["cift"], s["kart"], s["bayt"], s["genislik"], s["yukseklik"], s["sha256"], s["durum"], "; ".join(s["neden"])])
        for x in eksik:
            w.writerow([x, "", "", "", "", "", "", "FAIL", "dosya yok (eksik)"])
    fail = [s for s in satir if s["durum"] == "FAIL"]
    boyut_disi = [s["dosya"] for s in satir if any(n.startswith("boyut") for n in s["neden"])]
    ok = not fail and not eksik and len(satir) == len(bek)
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# YD set kontrolu\n\n{'PASS' if ok else 'FAIL'} | dosya {len(satir)} / beklenen {len(bek)} | PASS {len(satir) - len(fail)} | "
                f"FAIL {len(fail)} | eksik {len(eksik)} | sha tekrari {len(tekrar)} grup | boyut disi {len(boyut_disi)}\n"
                f"kaynak: klasor {a.dir}, cift listesi {a.ciftler} ({len(ciftler)} cift); boyut {BOYUT[0]}x{BOYUT[1]} (Serdar 27 Eki)\n\n")
        f.write("## Eksik\n" + ("".join(f"- {x}\n" for x in eksik) or "- yok\n"))
        f.write("\n## Boyut disi\n" + ("".join(f"- {x}\n" for x in boyut_disi) or "- yok\n"))
        f.write("\n## sha256 tekrari\n" + ("".join(f"- {' = '.join(v)}\n" for v in tekrar.values()) or "- yok\n"))
        f.write("\n## FAIL\n" + ("".join(f"- {s['dosya']}: {'; '.join(s['neden'])}\n" for s in fail) or "- yok\n"))
    print(f"SET OZET: {'PASS' if ok else 'FAIL'} dosya {len(satir)}/{len(bek)} FAIL {len(fail)} eksik {len(eksik)} sha tekrari {len(tekrar)} "
          f"boyut disi {len(boyut_disi)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
