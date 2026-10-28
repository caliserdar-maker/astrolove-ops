#!/usr/bin/env python3
"""v7 silme artigi: 78 mevcut video olcumu + ornek secimi + silme seridi (Merkez 28 Eki; Etsy yok).
olc   <poster_video_v7.py> <kapak_dir KAPAK_<CIFT>.jpg> <video_dir <CIFT>.mp4> <out>  -> OLCUM.csv, OLCUM.json, SECIM.txt
      (secim: AQUARIUS_AQUARIUS + en genis sembol + medyan genislikteki cift)
serit <video.mp4> <out.jpg>   -> 0 / 0,1 / 0,2 / 0,3 / 0,4 / 0,5 / 1,0 sn kareleri (gercek oran, 360x270), poster merkez bolgesi buyutmesiyle
Esik turetme: OLCUM.json'da zemin_max (silinmis bolgenin hemen cevresi, 78 video) dagilimi; artik esigi ESIK > en buyuk zemin."""
import csv
import json
import os
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v7_silme_artik as SA  # noqa: E402


def olc(pv, kdir, vdir, out):
    os.makedirs(out, exist_ok=True)
    ciftler = sorted(r["cift"] for r in csv.DictReader(open("data/pod/pod78_ids.csv")))
    R, t0 = [], time.time()
    for i, c in enumerate(ciftler, 1):
        k, v = os.path.join(kdir, f"KAPAK_{c}.jpg"), os.path.join(vdir, f"{c}.mp4")
        try:
            m, b = SA.hedef_maske(pv, k)
            r = dict(cift=c, **b, **SA.artik(SA.kare_oku(v, SA.KARE_SN), m))
        except Exception as e:  # noqa: BLE001 olcum satiri hatayla kalir
            r = dict(cift=c, hata=str(e)[:200])
        R.append(r)
        g = time.time() - t0
        print(f"[{i}/{len(ciftler)}] {c} artik {r.get('artik')} fazla_max {r.get('fazla_max')} zemin_max {r.get('zemin_max')} "
              f"genislik {r.get('sembol_genislik')} d {r.get('silme_d')} | gecen {g:.0f}s kalan ~{g / i * (len(ciftler) - i):.0f}s %{100 * i // len(ciftler)}",
              flush=True)
    alan = ["cift", "artik", "fazla_max", "fazla_p999", "zemin_max", "zemin_p999", "sembol_genislik", "sembol_parca", "silme_d", "maske_px", "hata"]
    with open(os.path.join(out, "OLCUM.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore"); w.writeheader(); w.writerows(R)
    json.dump(R, open(os.path.join(out, "OLCUM.json"), "w"), indent=1)
    ok = [r for r in R if "hata" not in r]
    gen = max(ok, key=lambda r: r["sembol_genislik"])["cift"]
    srt = sorted(ok, key=lambda r: r["sembol_genislik"])
    med = srt[len(srt) // 2]["cift"]
    if med in ("AQUARIUS_AQUARIUS", gen):
        med = srt[len(srt) // 2 + 1]["cift"]
    open(os.path.join(out, "SECIM.txt"), "w").write(f"AQUARIUS_AQUARIUS {gen} {med}\n")
    z = [r["zemin_max"] for r in ok]
    etk = [r for r in ok if r["artik"] > 0]
    md = ["# v7 silme artigi: 78 mevcut video (BIRLESIK) olcumu", "",
          f"- olculen {len(ok)}/78, hata {len(R) - len(ok)}; kare {SA.KARE_SN} sn; esik R-B fazlasi > {SA.ESIK}",
          f"- zemin (silinmis bolgenin hemen cevresi) en buyuk: {max(z) if z else '-'}; p95 {np.percentile(z, 95):.1f}" if z else "- zemin yok",
          f"- etkilenen (artik > 0): {len(etk)} cift",
          f"- secim: AQUARIUS_AQUARIUS, en genis sembol {gen}, medyan {med}", "",
          "| cift | artik | fazla_max | zemin_max | sembol genislik | silme_d |", "|---|---|---|---|---|---|"]
    md += [f"| {r['cift']} | {r['artik']} | {r['fazla_max']} | {r['zemin_max']} | {r['sembol_genislik']} | {r['silme_d']} |"
           for r in sorted(ok, key=lambda r: -r["artik"])]
    md += [f"| {r['cift']} | HATA {r['hata']} | | | | |" for r in R if "hata" in r]
    open(os.path.join(out, "OLCUM.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md[:6]), flush=True)


def serit(video, out):
    c = cv2.VideoCapture(video); F = []
    while True:
        ok, f = c.read()
        if not ok:
            break
        F.append(f[..., ::-1])
    sn = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
    tw, th, ust = 480, 360, 34
    t = Image.new("RGB", (len(sn) * (tw + 6), 2 * (th + ust)), (245, 245, 245)); d = ImageDraw.Draw(t)
    try:
        fn = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        fn = ImageFont.load_default()
    for i, s in enumerate(sn):
        k = F[min(len(F) - 1, int(round(s * 30)))]
        x = i * (tw + 6)
        d.text((x + 6, 6), f"{s:g} sn".replace(".", ","), fill=(0, 0, 0), font=fn)
        t.paste(Image.fromarray(k).resize((tw, th), Image.LANCZOS), (x, ust))                     # tam kare (gercek oran 4:3)
        h, w = k.shape[:2]; kk = k[int(h * 0.32):int(h * 0.72), int(w * 0.30):int(w * 0.70)]       # poster merkezi (sembol), 4:3
        d.text((x + 6, th + ust + 6), "merkez", fill=(0, 0, 0), font=fn)
        t.paste(Image.fromarray(kk).resize((tw, th), Image.LANCZOS), (x, th + 2 * ust))
    t.save(out, quality=88)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "olc":
        olc(*sys.argv[2:6])
    elif len(sys.argv) >= 2 and sys.argv[1] == "serit":
        serit(*sys.argv[2:4])
    else:
        raise SystemExit(__doc__)
