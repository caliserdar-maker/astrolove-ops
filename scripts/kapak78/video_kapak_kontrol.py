#!/usr/bin/env python3
"""Video kapak kontrolu (Merkez 30 Eki A; ETSY YOK, Drive yalniz okunur): 78 poster videosunun kapagi canli rank 1 kapakla ayni mi?
Canli kapak: B1 yedegi (TEMP/POSTER_GALERI_V11_YEDEK/20261029_121704/<ilan>_<CIFT>/r1_<id>.jpg; Etsy url_fullxfull, CDN JPEG).
  Wall art kapagi canli eski Midnight Blue kapak (29 Eki karari); v11b galeri rank 1'e dokunmaz, ONAR 18 ilanda B1 r1 geri yuklenir.
Video tarafi: video girdisi V10 kapak (TEMP/POSTER_KAPAK_V10/20261026_153710/KAPAK_<CIFT>.jpg) + videonun ilk ve son karesi
  (TEMP/VIDEO_V7_DUZELTME/20261028_134859/TAM78/<CIFT>.mp4; 1440x1080, ilk / son kare = kapak).
Olcum (cift basina; hepsi 1440x1080'e INTER_AREA, RGB): en buyuk kanal farki p99.9 / max / ortalama; canli kapaga karsi
  (a) V10 kapak, (b) ilk kare, (c) son kare. Kimlik (esiksiz): ilk karenin 160x120 gri NCC'si 78 canli kapak icinde en yuksek
  kendi ciftinde olmali. Ayirt edicilik: ilk karenin EN YAKIN BASKA cift canli kapagina p99.9'u (esik onerisi bu iki dagilimin
  arasindan: ayni cift degerleri + en kucuk baska cift degerinin siralamasindaki en buyuk boslugun ortasi; boslugun altinda
  ayni ciftlerin cogunlugu olmali, yoksa esik yok = FAIL). PASS = kimlik + a / b / c p99.9 <= onerilen esik.
Cikti --out: KONTROL.csv (78 satir), KONTROL.md (dagilim + esik onerisi + FAIL listesi), YANYANA/<CIFT>.jpg (yalniz FAIL:
  canli | V10 kapak | ilk kare | son kare, 360x270)."""
import argparse
import csv
import glob
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BOY = (1440, 1080)


def oku(p):
    return cv2.resize(np.asarray(Image.open(p).convert("RGB")), BOY, interpolation=cv2.INTER_AREA).astype(np.int16)


def kareler(mp4):
    v = cv2.VideoCapture(str(mp4)); n = int(v.get(cv2.CAP_PROP_FRAME_COUNT)); ilk = son = None; i = 0
    while True:
        ok, f = v.read()
        if not ok:
            break
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        if i == 0:
            ilk = f
        son = f; i += 1
    v.release()
    if ilk is None:
        return None, None, 0
    r = lambda f: cv2.resize(f, BOY, interpolation=cv2.INTER_AREA).astype(np.int16) if f.shape[1::-1] != BOY else f.astype(np.int16)
    return r(ilk), r(son), i


def fark(a, b):
    d = np.abs(a - b).max(2)
    return dict(p999=round(float(np.percentile(d, 99.9)), 1), max=int(d.max()), ort=round(float(d.mean()), 3))


def vek(a):
    g = cv2.resize(cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY), (160, 120), interpolation=cv2.INTER_AREA).astype(np.float64).ravel()
    g -= g.mean(); return g / (np.linalg.norm(g) or 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--b1", required=True); ap.add_argument("--kapak", required=True); ap.add_argument("--video", required=True)
    ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); (out / "YANYANA").mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(a.ciftler, encoding="utf-8-sig")))
    canli, R = {}, []
    for r in rows:
        lid, c = r["listing_id"], r["cift"]
        js = Path(a.b1) / f"{lid}_{c}" / "GALERI.json"
        r1 = None
        if js.exists():
            g = sorted(json.loads(js.read_text()).get("gorseller") or [], key=lambda x: x.get("rank") or 0)
            if g:
                p = Path(a.b1) / f"{lid}_{c}" / f"r1_{g[0]['listing_image_id']}.jpg"
                r1 = p if p.exists() else None
        canli[c] = oku(r1) if r1 else None
        R.append(dict(ilan=lid, cift=c, canli=r1.name if r1 else ""))
    cv_ = {c: vek(x) for c, x in canli.items() if x is not None}
    for s in R:
        c, n = s["cift"], []
        cl = canli.get(c)
        kp, mp4 = Path(a.kapak) / f"KAPAK_{c}.jpg", Path(a.video) / f"{c}.mp4"
        if cl is None:
            n.append("canli kapak (B1 r1) yok")
        if not kp.exists():
            n.append("V10 kapak yok")
        ilk = son = None; nk = 0
        if mp4.exists():
            ilk, son, nk = kareler(mp4)
            if ilk is None:
                n.append("video okunamadi")
        else:
            n.append("video yok")
        s["kare"] = nk
        if cl is not None:
            if kp.exists():
                s["kapak"] = fark(oku(kp), cl)
            if ilk is not None:
                s["ilk"], s["son"] = fark(ilk, cl), fark(son, cl)
                m = {k: float(vek(ilk) @ v) for k, v in cv_.items()}
                en = max(m, key=m.get); s["kimlik"] = en; s["ncc"] = round(m.get(c, -1), 4)
                if en != c:
                    n.append(f"ilk kare en cok {en} canli kapagina benziyor")
                diger = sorted((k for k in m if k != c), key=lambda k: -m[k])[:3]   # en benzer 3 baska cift, p99.9 en kucugu
                s["baska"] = min((fark(ilk, canli[k])["p999"], k) for k in diger)
        s["neden"] = n
    ayni = [max(s[k]["p999"] for k in ("kapak", "ilk", "son") if k in s) for s in R if all(k in s for k in ("kapak", "ilk", "son"))]
    baska = [s["baska"][0] for s in R if "baska" in s]
    esik = None
    if ayni and baska:   # ayni cift degerleri + en kucuk baska cift degeri siralanir; en buyuk bosluk, altinda ayni ciftlerin
        v = sorted(ayni + [min(baska)])   # cogunlugu kalirsa esik o boslugun ortasi (tek tuk bozuk cift esigi kaydirmaz)
        g = max(range(len(v) - 1), key=lambda i: v[i + 1] - v[i]) if len(v) > 1 else None
        if g is not None and sum(x <= v[g] for x in ayni) > len(ayni) / 2 and v[g] < min(baska):
            esik = round((v[g] + v[g + 1]) / 2, 1)
    for s in R:
        if esik is None:
            s["neden"].append("esik onerilemedi (ayni / baska dagilimlari ayrisik degil)")
        else:
            for k in ("kapak", "ilk", "son"):
                if k in s and s[k]["p999"] > esik:
                    s["neden"].append(f"{k} p99.9 {s[k]['p999']} > esik {esik}")
        s["durum"] = "FAIL" if s["neden"] else "PASS"
        if s["durum"] == "FAIL":
            parca = []
            for p in ([Path(a.b1) / f"{s['ilan']}_{s['cift']}" / s["canli"]] if s["canli"] else []) + [Path(a.kapak) / f"KAPAK_{s['cift']}.jpg"]:
                parca.append(Image.open(p).convert("RGB").resize((360, 270)) if p.exists() else Image.new("RGB", (360, 270), (200, 0, 0)))
            mp4 = Path(a.video) / f"{s['cift']}.mp4"
            i_, s_, _ = kareler(mp4) if mp4.exists() else (None, None, 0)
            for f in (i_, s_):
                parca.append(Image.fromarray(f.astype(np.uint8)).resize((360, 270)) if f is not None else Image.new("RGB", (360, 270), (200, 0, 0)))
            yy = Image.new("RGB", (4 * 360 + 30, 270), (255, 255, 255))
            for i, p in enumerate(parca[:4]):
                yy.paste(p, (i * 370, 0))
            yy.save(out / "YANYANA" / f"{s['cift']}.jpg", quality=88)
    with open(out / "KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ilan", "cift", "durum", "kapak_p999", "kapak_max", "ilk_p999", "ilk_max", "son_p999", "son_max", "kimlik_ncc",
                    "baska_cift_p999", "baska_cift", "kare", "neden"])
        for s in R:
            g = lambda k, x: s.get(k, {}).get(x, "")
            w.writerow([s["ilan"], s["cift"], s["durum"], g("kapak", "p999"), g("kapak", "max"), g("ilk", "p999"), g("ilk", "max"),
                        g("son", "p999"), g("son", "max"), s.get("ncc", ""), (s.get("baska") or ("", ""))[0], (s.get("baska") or ("", ""))[1],
                        s.get("kare", ""), "; ".join(s["neden"])])
    nf = sum(s["durum"] != "PASS" for s in R)
    q = lambda v: f"min {min(v)} medyan {float(np.median(v))} en buyuk {max(v)}" if v else "-"
    md = ["# Video kapak kontrolu (canli rank 1 = B1 r1)\n", f"cift {len(R)} | PASS {len(R) - nf} | FAIL {nf}",
          f"ayni cift p99.9 (V10 kapak / ilk / son kare, en buyugu): {q(ayni)}",
          f"baska cift p99.9 (ilk kare, en yakin baska cift): {q(baska)}",
          f"onerilen esik (olcumden, iki dagilimin ortasi): {esik}\n"]
    for k in ("kapak", "ilk", "son"):
        v = [s[k]["p999"] for s in R if k in s]; m = [s[k]["max"] for s in R if k in s]
        md.append(f"- {k}: p99.9 {q(v)} | max {q(m)}")
    md += ["\n## FAIL"] + [f"- {s['cift']} ({s['ilan']}): {'; '.join(s['neden'])}" for s in R if s["durum"] != "PASS"]
    (out / "KONTROL.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
