#!/usr/bin/env python3
"""Galeri v11b gorsellerinde boy sayisi yazisi taramasi (Serdar 30 Eki, 5x7 isi madde 4). ETSY API YOK, ag yok.
Girdi: galeri-v11-yedek-oku + indir klasoru (<lid>_<CIFT>/r<rank>_<image_id>.jpg). Her gorsel tesseract ile okunur; boy sayisi
ifadeleri aranir: "<sayi> sizes", "thirteen / fourteen sizes", "13 / 14 boy". 13 boy ifadesi = 5x7 eklenince yanlis kalacak gorsel.
Cikti: TARAMA.csv (listing_id, cift, rank, image_id, eslesme, boy_sayisi, satir) + OZET.md (rank basina sayim, 13 / 14 ilan listesi).
Cikis 0 her zaman (bulgu raporudur, kapi degil); okunamayan dosya OZET'te ayrica sayilir.
Hiz (30 Eki): gorsel OCR oncesi Pillow ile --genislik px'e kucultulur (gri), isci = os.cpu_count(), tesseract tek is parcacigi
(OMP_THREAD_LIMIT=1), gorsel basina --sure sn zaman asimi. TARAMA.csv satirlari gorsel bittikce yazilir; OZET.md her 50 gorselde
ara surum olarak yenilenir (kesilen kosuda da kismi sonuc kalir). --rank 1,3 yalniz o rank'lar."""
import argparse
import csv
import io
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

AD = re.compile(r"^r(\d+)_(\d+)\.jpe?g$", re.I)
KLASOR = re.compile(r"^(\d+)_([A-Z]+_[A-Z]+)$")
SAYI_SOZ = {"twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16}
DESEN = re.compile(r"\b(\d{1,2}|twelve|thirteen|fourteen|fifteen|sixteen)\s*(sizes|size|boy)\b", re.I)
GENISLIK = 2000  # 30 Eki olcum: 2000 px sentetik 40-58 px yazinin hepsini okur, 1600 px "14 Sizes" (58 px serif) kaciriyor
BOY = re.compile(r"\b(5|8|11|12|16|18|20|24)\s*[x×X]\s*(7|10|14|16|18|20|24|30|36)\b|\bA[234]\b")


ALAN = ["listing_id", "cift", "rank", "image_id", "eslesme", "boy_sayisi", "satir"]
ORTAM = {**os.environ, "OMP_THREAD_LIMIT": "1"}   # paralel surecte tesseract'in kendi is parcaciklari yavaslatir


def kucult(p, genislik):
    """gri + genislik px (0 = kucultme yok); PNG bayt"""
    with Image.open(p) as im:
        if genislik and im.width > genislik:
            im.draft("L", (genislik, round(im.height * genislik / im.width)))   # JPEG DCT olcekleme (>= hedef)
        im = im.convert("L")
        if genislik and im.width > genislik:
            im = im.resize((genislik, round(im.height * genislik / im.width)), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, "PNG", compress_level=1)
        return b.getvalue()


def ocr(p, genislik=0, sure=90):
    r = subprocess.run(["tesseract", "stdin", "-", "--psm", "11"], input=kucult(p, genislik), capture_output=True,
                       timeout=sure, env=ORTAM)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip()[:120])
    return r.stdout.decode("utf-8", "replace")


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


def ozet_yaz(out, a, isler, satir, hata, n, tam):
    ilan = {(i[0], i[1]) for i in isler}
    rank_sayi = defaultdict(Counter)
    ilanlar = defaultdict(set)
    for s in satir:
        rank_sayi[s["rank"]][s["boy_sayisi"]] += 1
        ilanlar[(s["rank"], s["boy_sayisi"])].add(s["cift"])
    gecici = out / "OZET.md.tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(f"# Galeri boy sayisi yazisi taramasi (OCR)\n\nilan {len(ilan)} | gorsel {len(isler)} | eslesme {len(satir)} | "
                f"okunamayan {len(hata)}\nkaynak: {a.dir}\n"
                f"taranan {n}/{len(isler)} ({'TAM' if tam else 'KISMI'}) | rank {a.rank or 'hepsi'} | genislik {a.genislik or 'tam'} px\n"
                "\n| rank | boy sayisi | eslesme | ilan |\n|---|---|---|---|\n")
        for r in sorted(rank_sayi):
            for b, c in sorted(rank_sayi[r].items(), key=lambda x: str(x[0])):
                f.write(f"| {r} | {b} | {c} | {len(ilanlar[(r, b)])} |\n")
        f.write("\n## 13 boy yazan gorseller (ilan listesi)\n")
        for r in sorted(rank_sayi):
            for b in sorted(rank_sayi[r], key=str):
                if b == 13 or (isinstance(b, str) and b.startswith("liste") and not b.endswith("_5x7")):
                    f.write(f"- rank {r} ({b}): {len(ilanlar[(r, b)])} ilan: {', '.join(sorted(ilanlar[(r, b)]))}\n")
        f.write("\n## Okunamayan\n" + ("".join(f"- {h[1]} r{h[2]}: {h[3]}\n" for h in hata) or "- yok\n"))
    os.replace(gecici, out / "OZET.md")
    return rank_sayi


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--is", type=int, default=os.cpu_count() or 4, dest="isci")
    ap.add_argument("--genislik", type=int, default=GENISLIK, help="OCR oncesi genislik px (0 = tam boy)")
    ap.add_argument("--sure", type=int, default=90, help="gorsel basina OCR zaman asimi sn")
    ap.add_argument("--rank", default="", help="virgullu rank listesi (bos = hepsi), orn. 1,3")
    a = ap.parse_args(argv)
    ranklar = {int(x) for x in a.rank.split(",") if x.strip()}
    isler = []
    for d in sorted(Path(a.dir).iterdir()):
        k = KLASOR.match(d.name) if d.is_dir() else None
        if not k:
            continue
        for f in sorted(d.iterdir()):
            m = AD.match(f.name)
            if m and (not ranklar or int(m.group(1)) in ranklar):
                isler.append((k.group(1), k.group(2), int(m.group(1)), m.group(2), f))
    print(f"gorsel {len(isler)} | isci {a.isci} | genislik {a.genislik or 'tam'} px | sure {a.sure} sn | rank {a.rank or 'hepsi'}",
          flush=True)

    def tek(i):
        try:
            return i, bul(ocr(i[4], a.genislik, a.sure)), ""
        except subprocess.TimeoutExpired:
            return i, [], f"zaman asimi {a.sure} sn"
        except Exception as e:  # noqa: BLE001
            return i, [], str(e)[:160]

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir, hata, n, t0 = [], [], 0, time.monotonic()
    with open(out / "TARAMA.csv", "w", newline="", encoding="utf-8") as fc, ThreadPoolExecutor(max(1, a.isci)) as ex:
        w = csv.DictWriter(fc, fieldnames=ALAN)
        w.writeheader(); fc.flush()
        for fut in as_completed([ex.submit(tek, i) for i in isler]):
            i, es, h = fut.result()
            n += 1
            if h:
                hata.append((i[0], i[1], i[2], h))
            for e in es:
                d = dict(listing_id=i[0], cift=i[1], rank=i[2], image_id=i[3], eslesme=e[0], boy_sayisi=e[1], satir=e[2])
                satir.append(d); w.writerow(d)
            fc.flush()
            if n % 50 == 0 or n == len(isler):
                g = time.monotonic() - t0
                kalan = g / n * (len(isler) - n)
                print(f"[{n}/{len(isler)}] %{100 * n // max(1, len(isler))} | gecen {g / 60:.1f} dk | kalan ~{kalan / 60:.1f} dk | "
                      f"{g / n:.2f} sn/gorsel | eslesme {len(satir)} | okunamayan {len(hata)}", flush=True)
                if n < len(isler):
                    ozet_yaz(out, a, isler, satir, hata, n, False)
    # son: sirali yeniden yaz (ayni sutunlar)
    satir.sort(key=lambda d: (d["listing_id"], d["rank"], d["image_id"]))
    hata.sort()
    with open(out / "TARAMA.csv.tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN)
        w.writeheader(); w.writerows(satir)
    os.replace(out / "TARAMA.csv.tmp", out / "TARAMA.csv")
    rank_sayi = ozet_yaz(out, a, isler, satir, hata, n, True)
    print(f"OZET: gorsel {len(isler)} eslesme {len(satir)} okunamayan {len(hata)} | sure {(time.monotonic() - t0) / 60:.1f} dk | "
          + " ".join(f"r{r}:{dict(c)}" for r, c in sorted(rank_sayi.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
