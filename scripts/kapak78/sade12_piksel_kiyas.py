#!/usr/bin/env python3
"""Sade v2 PNG piksel + video kare karsilastirmasi (Merkez / Serdar 31 Eki, gorev F-C). ETSY YOK.
Referans: kupa-orchard e235d342 kupa_orchard/ilan/SADE12_PIKSEL.tsv (96 baski PNG: sha256(RGB piksel baytlari), boyut, dosya) ve
SADE12_KARE.json (12 video: kare, fps, boyut, her karenin 4x3 RGB ozeti, 36 deger).
Olcut (Merkez 31 Eki): PNG piksel sha256 BIREBIR; video kare sayisi + fps + boyut ayni ve her karede 4x3 ozet farki ortalama <= 2,
en buyuk <= 8 (kodlayici surum farki icin; esik Merkez onerisi).
4x3 ozet yontemi referansta yazili degil: iki yontem hesaplanir ve ikisi de raporlanir:
  blok : kare 4 x 3 esit bloga bolunur (1440x1080 -> 360x360), blok RGB ortalamasi yuvarlanir (numpy);
  ffarea: ffmpeg scale=4:3:flags=area (rgb24).
Karar: iki yontemden referansa en yakin olan (ortalama farki kucuk) kullanilir; secilen yontem ve digerinin sonucu raporda.
Kullanim: sade12_piksel_kiyas.py --kok <dir: <BURC>/is/b_*_baski_11oz.png, <BURC>/SADE_VIDEO_<BURC>.mp4> --piksel SADE12_PIKSEL.tsv
          --kare SADE12_KARE.json --json SONUC.json   (cikis 0 = PASS)"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ORT_ESIK, MAX_ESIK = 2.0, 8


def rgb_sha(p):
    return hashlib.sha256(np.asarray(Image.open(p).convert("RGB")).tobytes()).hexdigest()


def video_bilgi(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(p)], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return int(s["nb_read_frames"]), round(float(a) / float(b), 3), [int(s["width"]), int(s["height"])]


def kareler_blok(p, w, h):
    pr = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3
    out = []
    while True:
        b = pr.stdout.read(n)
        if len(b) < n:
            break
        a = np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float64)
        out.append(np.round(a.reshape(3, h // 3, 4, w // 4, 3).mean(axis=(1, 3))).astype(int).reshape(-1).tolist())
    pr.wait()
    return out


def kareler_ffarea(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", "scale=4:3:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.uint8).reshape(-1, 36)
    return a.astype(int).tolist()


def fark(k, ref):
    if len(k) != len(ref):
        return None
    d = np.abs(np.array(k) - np.array(ref))
    kare_ort = d.mean(axis=1)
    return dict(ort_en_kotu_kare=round(float(kare_ort.max()), 3), max=int(d.max()), ort_tum=round(float(d.mean()), 3))


def main(argv=None):
    ap = argparse.ArgumentParser()
    for x in ("--kok", "--piksel", "--kare", "--json"):
        ap.add_argument(x, required=True)
    a = ap.parse_args(argv)
    kok = Path(a.kok)
    P, V = [], []
    for ln in Path(a.piksel).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        h, boyut, yol = ln.split("\t")
        p = kok / yol
        if not p.is_file():
            P.append(dict(dosya=yol, durum="YOK")); continue
        im = Image.open(p)
        s = rgb_sha(p)
        P.append(dict(dosya=yol, durum="ESIT" if s == h and f"{im.width}x{im.height}" == boyut else "FARKLI", ref=h, olculen=s,
                      boyut=f"{im.width}x{im.height}"))
    ref_kare = json.loads(Path(a.kare).read_text(encoding="utf-8"))
    for yol, r in sorted(ref_kare.items()):
        p = kok / yol
        if not p.is_file():
            V.append(dict(dosya=yol, durum="YOK")); continue
        n, fps, boyut = video_bilgi(p)
        kb, kf = kareler_blok(p, *boyut), kareler_ffarea(p)
        fb, ff = fark(kb, r["ozet_4x3"]), fark(kf, r["ozet_4x3"])
        ayni = n == r["kare"] and abs(fps - float(r["fps"])) < 1e-3 and boyut == list(r["boyut"])
        V.append(dict(dosya=yol, kare=n, fps=fps, boyut=boyut, ref=dict(kare=r["kare"], fps=r["fps"], boyut=r["boyut"]), sayi_ayni=ayni,
                      blok=fb, ffarea=ff))
    # yontem secimi: tum videolarda ortalama farki kucuk olan
    def top(k):
        x = [v[k]["ort_tum"] for v in V if v.get(k)]
        return sum(x) / len(x) if x else 9e9
    yontem = "blok" if top("blok") <= top("ffarea") else "ffarea"
    for v in V:
        f = v.get(yontem)
        v["durum"] = v.get("durum") or ("PASS" if v["sayi_ayni"] and f and f["ort_en_kotu_kare"] <= ORT_ESIK and f["max"] <= MAX_ESIK else "FAIL")
    png_ok = sum(x["durum"] == "ESIT" for x in P)
    vid_ok = sum(x["durum"] == "PASS" for x in V)
    R = dict(png=f"{png_ok}/{len(P)} piksel sha256 esit", video=f"{vid_ok}/{len(V)} PASS (kare / fps / boyut ayni, 4x3 ozet ort <= {ORT_ESIK}, "
             f"max <= {MAX_ESIK})", yontem=yontem, yontem_ort=dict(blok=round(top("blok"), 3), ffarea=round(top("ffarea"), 3)),
             png_ayrinti=[x for x in P if x["durum"] != "ESIT"], video_ayrinti=V)
    Path(a.json).write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    print(R["png"]); print(R["video"]); print("yontem", yontem, R["yontem_ort"])
    for v in V:
        print(v["dosya"], v.get("durum"), v.get("kare"), v.get("fps"), v.get("boyut"), "blok", v.get("blok"), "ffarea", v.get("ffarea"))
    return 0 if png_ok == len(P) == 96 and vid_ok == len(V) == 12 else 1


if __name__ == "__main__":
    sys.exit(main())
