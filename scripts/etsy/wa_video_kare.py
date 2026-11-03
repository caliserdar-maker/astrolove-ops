#!/usr/bin/env python3
"""ETSY API YOK, KILITSIZ: wa_video_oku.py kaydindan canli video ilk/son kare <-> canli kapak (1. gorsel) ve <-> v7d kaynak dosyasi
(Drive VIDEO_V7D_YUKLE_KAYNAK) kare farki. Esik YOK; degerler raporlanir (Merkez 3 Kas). Indirme Etsy CDN'den (API istegi degil).
Olcu: iki goruntu 4:3'e merkez kirpilir, 720x540'a olceklenir; RGB mutlak fark ortalamasi (ort) ve 99. yuzdelik (p99), 0-255.
Kullanim: wa_video_kare.py --kayit VIDEO_KAYIT.json --v7d-dir DIR --out DIR"""
import argparse, csv, json, pathlib, subprocess, sys, tempfile, urllib.request
import numpy as np
from PIL import Image


def indir(url, yol):
    if str(url).startswith("/"):
        pathlib.Path(yol).write_bytes(pathlib.Path(url).read_bytes()); return yol
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-ops-kontrol"})
    with urllib.request.urlopen(req, timeout=120) as r:
        pathlib.Path(yol).write_bytes(r.read())
    return yol


def kare(video, son, yol):
    arg = ["ffmpeg", "-v", "error", "-y"] + (["-sseof", "-0.5"] if son else []) + ["-i", str(video)] + \
          (["-update", "1"] if son else ["-frames:v", "1"]) + [str(yol)]
    subprocess.run(arg, check=True)
    return yol


def norm(p):
    im = Image.open(p).convert("RGB"); w, h = im.size
    if w * 3 > h * 4:
        nw = h * 4 // 3; im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w * 3 < h * 4:
        nh = w * 3 // 4; im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return np.asarray(im.resize((720, 540), Image.LANCZOS), dtype=np.int16)


def fark(a, b):
    d = np.abs(norm(a) - norm(b))
    return round(float(d.mean()), 2), round(float(np.percentile(d, 99)), 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kayit", required=True); ap.add_argument("--v7d-dir", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    K = json.load(open(a.kayit, encoding="utf-8")); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir = []
    for i, (lid, v) in enumerate(K.items(), 1):
        r = dict(listing_id=lid, cift=v["cift"], onar18=v.get("onar18"), video_sayisi=len(v["videolar"]), video_id="", video_state="",
                 yukleme_tarihi="", ilk_kapak_ort="", ilk_kapak_p99="", son_kapak_ort="", son_kapak_p99="", ilk_v7d_ort="", son_v7d_ort="",
                 v7d_ilk_kapak_ort="", kapak_id=(v.get("kapak") or {}).get("listing_image_id"), not_="")
        try:
            if not v["videolar"]:
                r["not_"] = "canli video yok"; satir.append(r); continue
            vd = v["videolar"][0]
            r.update(video_id=vd.get("video_id"), video_state=vd.get("video_state"),
                     yukleme_tarihi=next((str(vd[k]) for k in vd if "time" in k or "date" in k or "creat" in k), "API'de yok"))
            with tempfile.TemporaryDirectory() as t:
                t = pathlib.Path(t)
                mp4 = indir(vd.get("video_url"), t / "canli.mp4")
                kp = indir(v["kapak"]["url_fullxfull"], t / "kapak.jpg")
                ilk, son = kare(mp4, False, t / "ilk.png"), kare(mp4, True, t / "son.png")
                r["ilk_kapak_ort"], r["ilk_kapak_p99"] = fark(ilk, kp)
                r["son_kapak_ort"], r["son_kapak_p99"] = fark(son, kp)
                v7 = pathlib.Path(a.v7d_dir) / f"{v['cift']}.mp4"
                if v7.exists():
                    vi, vs = kare(v7, False, t / "v7i.png"), kare(v7, True, t / "v7s.png")
                    r["ilk_v7d_ort"] = fark(ilk, vi)[0]; r["son_v7d_ort"] = fark(son, vs)[0]; r["v7d_ilk_kapak_ort"] = fark(vi, kp)[0]
                else:
                    r["not_"] = "v7d dosyasi yok"
                if i <= 3 or v.get("onar18"):
                    for ad, p in (("ilk", ilk), ("son", son), ("kapak", kp)):
                        Image.open(p).convert("RGB").resize((360, 270)).save(out / f"KARE_{lid}_{ad}.jpg", quality=85)
        except Exception as e:  # noqa: BLE001
            r["not_"] = f"HATA {type(e).__name__}: {str(e)[:120]}"
        satir.append(r)
        print(f"[{i}/{len(K)}] {lid} {r['cift']} ilk/kapak {r['ilk_kapak_ort']} son/kapak {r['son_kapak_ort']} v7d {r['ilk_v7d_ort']}/{r['son_v7d_ort']} {r['not_']}", flush=True)
    with open(out / "TABLO.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0].keys())); w.writeheader(); w.writerows(satir)
    print(f"::notice::WA VIDEO KARE: {len(satir)} ilan, video yok {sum(1 for s in satir if not s['video_sayisi'])}, hata {sum(1 for s in satir if str(s['not_']).startswith('HATA'))}")


if __name__ == "__main__":
    sys.exit(main())
