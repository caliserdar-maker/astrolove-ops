#!/usr/bin/env python3
"""Sade kupa 12 burc ciktisi dogrulamasi (Serdar 31 Eki ek is; Merkez 3a). ETSY YOK.
ozet  : <burc dir> -> her dosyanin bayt sha256'si; PNG icin cozulmus piksel (RGB/RGBA dizi) sha256'si; MP4 icin ffmpeg framemd5 (kare kare,
        cozulmus goruntu) listesi ve onun sha256'si; manifest (kupa_orchard/ilan/SADE12_MANIFEST.tsv) ile bayt kiyasi.
kiyas : iki ya da daha cok ozet JSON -> PNG piksel ve video kare esitligi (bayt farkli olsa da icerik ayni mi).
Kullanim: sade12_dogrula.py ozet --dir CANCER --manifest SADE12_MANIFEST.tsv --json V_CANCER.json
          sade12_dogrula.py kiyas V_a.json V_b.json"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(b):
    return hashlib.sha256(b).hexdigest()


def piksel_sha(p):
    import numpy as np
    from PIL import Image
    im = Image.open(p)
    a = np.asarray(im)
    return sha(f"{im.mode}{a.shape}".encode() + a.tobytes())


def kare_md5(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:v", "-f", "framemd5", "-"], capture_output=True, text=True)
    if r.returncode:
        return None
    return [ln.split(",")[-1].strip() for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]


def ozet(a):
    d = Path(a.dir)
    b = d.name
    man = {}
    for ln in Path(a.manifest).read_text().splitlines():
        if ln.strip():
            h, yol = ln.split("\t")
            if yol.startswith(b + "/"):
                man[yol] = h
    dos = {}
    for yol, h in sorted(man.items()):
        p = d.parent / yol
        k = dict(manifest=h)
        if not p.is_file():
            k["durum"] = "YOK"
        else:
            k["bayt"] = sha(p.read_bytes())
            k["bayt_esit"] = k["bayt"] == h
            if p.suffix == ".png":
                k["piksel"] = piksel_sha(p)
            if p.suffix == ".mp4":
                km = kare_md5(p)
                k["kare_sayisi"] = len(km) if km else None
                k["kareler_sha"] = sha("\n".join(km).encode()) if km else None
                k["ilk_son_kare_md5"] = [km[0], km[-1]] if km else None
                r_ = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                     "-of", "csv=p=0", str(p)], capture_output=True, text=True)
                k["cozunurluk_fps"] = r_.stdout.strip()
        dos[yol] = k
    tur = lambda s: [k for y, k in dos.items() if y.endswith(s)]
    r = dict(burc=b, dosya=dos,
             sayim=dict(manifest=len(man), jpg_esit=sum(k.get("bayt_esit", False) for k in tur(".jpg")), jpg=len(tur(".jpg")),
                        png_bayt_esit=sum(k.get("bayt_esit", False) for k in tur(".png")), png=len(tur(".png")),
                        mp4_bayt_esit=sum(k.get("bayt_esit", False) for k in tur(".mp4")), eksik=sum(k.get("durum") == "YOK" for k in dos.values())))
    Path(a.json).write_text(json.dumps(r, indent=1))
    print(b, r["sayim"])
    tam = r["sayim"]["manifest"] == 18 and r["sayim"]["jpg"] == 9        # inceleme 31 Eki: manifest satiri yoksa PASS vermesin
    return 0 if tam and r["sayim"]["eksik"] == 0 and r["sayim"]["jpg_esit"] == r["sayim"]["jpg"] else 1


def kiyas(dosyalar):
    R = [json.loads(Path(f).read_text()) for f in dosyalar]
    ilk, sonuc = R[0], []
    for r in R[1:]:
        for yol, k in ilk["dosya"].items():
            o = r["dosya"].get(yol, {})
            for alan in ("bayt", "piksel", "kareler_sha"):
                if alan in k:
                    sonuc.append(dict(dosya=yol, alan=alan, esit=k[alan] == o.get(alan)))
    ozet_ = {a: f"{sum(s['esit'] for s in sonuc if s['alan'] == a)}/{sum(1 for s in sonuc if s['alan'] == a)}" for a in ("bayt", "piksel", "kareler_sha")}
    farkli = [s for s in sonuc if not s["esit"]]
    print(json.dumps(dict(ozet=ozet_, farkli=farkli), indent=1))
    print("KIYAS", "PASS" if sonuc and not farkli else "FAIL")
    return 0 if sonuc and not farkli else 1      # inceleme 31 Eki: kiyas da PASS / FAIL verir (her zaman 0 donuyordu)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mod", required=True)
    o = sp.add_parser("ozet")
    o.add_argument("--dir", required=True)
    o.add_argument("--manifest", required=True)
    o.add_argument("--json", required=True)
    k = sp.add_parser("kiyas")
    k.add_argument("dosyalar", nargs="+")
    a = ap.parse_args(argv)
    return ozet(a) if a.mod == "ozet" else kiyas(a.dosyalar)


if __name__ == "__main__":
    sys.exit(main())
