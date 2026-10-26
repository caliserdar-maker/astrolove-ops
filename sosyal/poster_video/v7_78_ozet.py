#!/usr/bin/env python3
"""poster-video-v7-78 raporu: cift satirlarindan (uret islerinin satir/<CIFT>.json) OZET.md + OZET.csv + KONTAK_GENEL_<n>.jpg.
OZET.md ucuncu satiri: "PASS x / istenen y | FAIL z | eksik w" (eksik = satiri hic gelmeyen cift; is dustu ya da zaman asimi).
Maske V10 kapagin kendisinden (Serdar 26 Eki); ayristirma satiri (halkasiz sembol kutusu) ve silinme_hayalet R-B OZET.csv'de.
Kullanim: v7_78_ozet.py --satir DIR --kontak DIR --ciftler TUMU|A_B,... --out DIR"""
import argparse
import csv
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ALAN = ["cift", "ilan", "sonuc", "neden", "ayristirma", "hayalet", "sure_sn"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--satir", required=True); ap.add_argument("--kontak", required=True)
    ap.add_argument("--ciftler", default="TUMU"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    kok = Path(__file__).resolve().parents[2]
    tum = sorted(r["cift"] for r in csv.DictReader(open(kok / "data/pod/pod78_ids.csv")))
    istenen = tum if a.ciftler.strip().upper() in ("", "TUMU") else [c.strip().upper() for c in re.split(r"[,\s]+", a.ciftler) if c.strip()]
    S = {}
    for p in sorted(Path(a.satir).glob("*.json")) if Path(a.satir).is_dir() else []:
        s = json.loads(p.read_text()); S[s["cift"]] = s
    rows = []
    for c in istenen:
        s = S.get(c)
        if not s:
            rows.append(dict(cift=c, sonuc="EKSIK", neden="satir yok (is dustu / zaman asimi)")); continue
        rows.append(dict(cift=c, ilan=s.get("ilan"), sonuc=s["sonuc"], neden=s.get("neden") or "", ayristirma=s.get("ayristirma") or "",
                         hayalet=s.get("hayalet"), sure_sn=s.get("sure_sn")))
    with open(out / "OZET.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN); w.writeheader(); w.writerows({k: r.get(k, "") for k in ALAN} for r in rows)
    say = {k: sum(1 for r in rows if r["sonuc"] == k) for k in ("PASS", "FAIL", "EKSIK")}
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write("# Poster video v7b toplu\n\n")
        f.write(f"PASS {say['PASS']} / istenen {len(rows)} | FAIL {say['FAIL']} | eksik {say['EKSIK']}\n")
        f.write(f"FAIL {say['FAIL'] + say['EKSIK']} (FAIL + eksik)\n\n")
        bad = [r for r in rows if r["sonuc"] != "PASS"]
        if bad:
            f.write("## PASS olmayan\n" + "".join(f"- {r['cift']}: {r['sonuc']} {r['neden']}\n" for r in bad) + "\n")
        f.write("## Ciftler\n| cift | sonuc | hayalet R-B | sure sn | ayristirma |\n|---|---|---|---|---|\n")
        f.writelines(f"| {r['cift']} | {r['sonuc']} | {r.get('hayalet', '')} | {r.get('sure_sn', '')} | {r.get('ayristirma', '')} |\n"
                     for r in rows)
    kd = Path(a.kontak)
    ks = [(r["cift"], r["sonuc"], kd / f"{r['cift']}.jpg") for r in rows if (kd / f"{r['cift']}.jpg").exists()]
    tw, th, ust = 720, 300, 30
    try:
        fn = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        fn = ImageFont.load_default()
    for sayfa in range(0, len(ks), 12):
        grup = ks[sayfa:sayfa + 12]
        im = Image.new("RGB", (3 * tw, 4 * (th + ust)), (245, 245, 245)); d = ImageDraw.Draw(im)
        for i, (c, sn, p) in enumerate(grup):
            x, y = (i % 3) * tw, (i // 3) * (th + ust)
            d.text((x + 8, y + 4), f"{c} {sn}", fill=(0, 0, 0) if sn == "PASS" else (200, 0, 0), font=fn)
            k = Image.open(p).convert("RGB"); k.thumbnail((tw - 10, th)); im.paste(k, (x + 5, y + ust))
        im.save(out / f"KONTAK_GENEL_{sayfa // 12 + 1}.jpg", quality=88)
    print(open(out / "OZET.md", encoding="utf-8").read().splitlines()[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
