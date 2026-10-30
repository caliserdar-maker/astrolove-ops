#!/usr/bin/env python3
"""Galeri v11b gorsellerinde boy sayisi yazisi taramasi (Serdar 30 Eki, 5x7 isi madde 4). ETSY API YOK, ag yok.
Girdi: galeri-v11-yedek-oku + indir klasoru (<lid>_<CIFT>/r<rank>_<image_id>.jpg). Her gorsel tesseract ile okunur; boy sayisi
ifadeleri aranir: "<sayi> sizes", "thirteen / fourteen sizes", "13 / 14 boy". 13 boy ifadesi = 5x7 eklenince yanlis kalacak gorsel.
Cikti: TARAMA.csv (listing_id, cift, rank, image_id, eslesme, boy_sayisi, satir) + OZET.md (rank basina sayim, 13 / 14 ilan listesi).
Cikis 0 her zaman (bulgu raporudur, kapi degil); okunamayan dosya OZET'te ayrica sayilir."""
import argparse
import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AD = re.compile(r"^r(\d+)_(\d+)\.jpe?g$", re.I)
KLASOR = re.compile(r"^(\d+)_([A-Z]+_[A-Z]+)$")
SAYI_SOZ = {"twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16}
DESEN = re.compile(r"\b(\d{1,2}|twelve|thirteen|fourteen|fifteen|sixteen)\s*(sizes|size|boy)\b", re.I)
BOY = re.compile(r"\b(5|8|11|12|16|18|20|24)\s*[x×X]\s*(7|10|14|16|18|20|24|30|36)\b|\bA[234]\b")


def ocr(p):
    r = subprocess.run(["tesseract", str(p), "-", "--psm", "11"], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:120])
    return r.stdout


def bul(metin):
    out = []
    boylar = {re.sub(r"\s|×|X", "x", m.group(0)) for m in BOY.finditer(metin)}
    if len(boylar) >= 6:   # boy listesi (sayi yazilmadan): 5x7 var mi
        out.append((f"boy listesi {len(boylar)} ({'5x7 var' if '5x7' in boylar else '5x7 YOK'})", f"liste{len(boylar)}{'_5x7' if '5x7' in boylar else ''}",
                    " ".join(sorted(boylar))))
    for satir in metin.splitlines():
        for m in DESEN.finditer(satir):
            s = m.group(1).lower()
            out.append((m.group(0), SAYI_SOZ.get(s, int(s) if s.isdigit() else None), satir.strip()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--is", type=int, default=4, dest="isci")
    a = ap.parse_args(argv)
    isler = []
    for d in sorted(Path(a.dir).iterdir()):
        k = KLASOR.match(d.name) if d.is_dir() else None
        if not k:
            continue
        for f in sorted(d.iterdir()):
            m = AD.match(f.name)
            if m:
                isler.append((k.group(1), k.group(2), int(m.group(1)), m.group(2), f))
    print(f"gorsel {len(isler)}", flush=True)

    def tek(i):
        try:
            return i, bul(ocr(i[4])), ""
        except Exception as e:  # noqa: BLE001
            return i, [], str(e)

    satir, hata, n = [], [], 0
    with ThreadPoolExecutor(a.isci) as ex:
        for i, es, h in ex.map(tek, isler):
            n += 1
            if h:
                hata.append((i[0], i[1], i[2], h))
            for e in es:
                satir.append(dict(listing_id=i[0], cift=i[1], rank=i[2], image_id=i[3], eslesme=e[0], boy_sayisi=e[1], satir=e[2]))
            if n % 50 == 0 or n == len(isler):
                print(f"[{n}/{len(isler)}] %{100 * n // max(1, len(isler))}", flush=True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "TARAMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "cift", "rank", "image_id", "eslesme", "boy_sayisi", "satir"])
        w.writeheader(); w.writerows(satir)
    ilan = {(i[0], i[1]) for i in isler}
    rank_sayi = defaultdict(Counter)
    ilanlar = defaultdict(set)
    for s in satir:
        rank_sayi[s["rank"]][s["boy_sayisi"]] += 1
        ilanlar[(s["rank"], s["boy_sayisi"])].add(s["cift"])
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Galeri boy sayisi yazisi taramasi (OCR)\n\nilan {len(ilan)} | gorsel {len(isler)} | eslesme {len(satir)} | "
                f"okunamayan {len(hata)}\nkaynak: {a.dir}\n\n| rank | boy sayisi | eslesme | ilan |\n|---|---|---|---|\n")
        for r in sorted(rank_sayi):
            for b, c in sorted(rank_sayi[r].items(), key=lambda x: str(x[0])):
                f.write(f"| {r} | {b} | {c} | {len(ilanlar[(r, b)])} |\n")
        f.write("\n## 13 boy yazan gorseller (ilan listesi)\n")
        for r in sorted(rank_sayi):
            for b in sorted(rank_sayi[r], key=str):
                if b == 13 or (isinstance(b, str) and b.startswith("liste") and not b.endswith("_5x7")):
                    f.write(f"- rank {r} ({b}): {len(ilanlar[(r, b)])} ilan: {', '.join(sorted(ilanlar[(r, b)]))}\n")
        f.write("\n## Okunamayan\n" + ("".join(f"- {h[1]} r{h[2]}: {h[3]}\n" for h in hata) or "- yok\n"))
    print(f"OZET: gorsel {len(isler)} eslesme {len(satir)} okunamayan {len(hata)} | "
          + " ".join(f"r{r}:{dict(c)}" for r, c in sorted(rank_sayi.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
