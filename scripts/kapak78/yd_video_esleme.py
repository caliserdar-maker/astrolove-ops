#!/usr/bin/env python3
"""YD (1st Anniversary) 1. asama video esleme (Serdar 1 Kas karari 2). ETSY YOK, kilit YOK, yalniz Drive + GitHub okuma.

Kural: her cift icin TEMP/YD_VIDEO_ORNEK43 altindaki EN SON basarili cikti (yd-video-ornek43 is akisi <CIFT>_yd_video_43.mp4
dosyasini _o'ya YALNIZ uretim + tozsuz + ffprobe adimlari gectikten sonra kopyalar: klasorde mp4 varsa o cift o kosuda basarili).
EN SON = en buyuk damga (YYYYMMDD_HHMMSS). ISTISNA: 3 yeni kapakli cift (ARIES_LEO, CAPRICORN_SAGITTARIUS, SAGITTARIUS_SAGITTARIUS)
MUTLAKA kosu 41292904564'un klasorunden (--zorunlu CIFT=DAMGA).

Adimlar:
  sec   <lsjson> <ids_csv> <out_dir> [--zorunlu C=D ...]  -> SECIM.json + INDIR.txt (rclone --files-from)
  olc   <secim_json> <video_kok> <kosu_json> <out_dir>     -> VIDEO_ESLEME.csv + VIDEO_ESLEME.md (sha256, bayt, kare, boyut, sure)
Kapi: 78 satir, tekrar 0, eksik 0, her video 1440x1080; aksi halde cikis 1 (tablo yine yazilir)."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DAMGA = re.compile(r"^\d{8}_\d{6}$")
AD = re.compile(r"^([A-Z]+_[A-Z]+)_yd_video_43\.mp4$")


def sec(a):
    ids = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    ciftler = [r["cift"] for r in ids]
    aday = {}
    for f in json.load(open(a.lsjson)):
        p = f["Path"].split("/")
        if len(p) != 2 or not DAMGA.match(p[0]):
            continue
        m = AD.match(p[1])
        if m:
            aday.setdefault(m.group(1), []).append(dict(damga=p[0], dosya=f["Path"], bayt=f.get("Size")))
    zor = dict(z.split("=", 1) for z in a.zorunlu)
    sec_, hata = {}, []
    for c in ciftler:
        ad = sorted(aday.get(c, []), key=lambda x: x["damga"])
        if not ad:
            hata.append(f"{c}: hic cikti yok"); continue
        if c in zor:
            s = [x for x in ad if x["damga"] == zor[c]]
            if not s:
                hata.append(f"{c}: zorunlu klasor {zor[c]} icinde video yok (adaylar {[x['damga'] for x in ad]})"); continue
            s = s[0]
        else:
            s = ad[-1]
        sec_[c] = dict(s, adaylar=[x["damga"] for x in ad], zorunlu=c in zor)
    yabanci = sorted(set(aday) - set(ciftler))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    json.dump(dict(secim=sec_, hata=hata, listede_olmayan=yabanci, cift_sayisi=len(ciftler)), open(out / "SECIM.json", "w"), indent=1)
    (out / "INDIR.txt").write_text("".join(s["dosya"] + "\n" for s in sec_.values()))
    print(f"secim {len(sec_)}/{len(ciftler)} | hata {len(hata)} | listede olmayan {len(yabanci)}")
    for h in hata:
        print("::error::" + h)
    return 1 if hata or len(sec_) != len(ciftler) else 0


def ffprobe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,nb_read_frames,r_frame_rate:format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True, timeout=300)
    j = json.loads(r.stdout or "{}")
    s = (j.get("streams") or [{}])[0]
    return dict(genislik=s.get("width"), yukseklik=s.get("height"), kare=int(s.get("nb_read_frames") or 0),
                fps=s.get("r_frame_rate"), sure=round(float((j.get("format") or {}).get("duration") or 0), 3))


def olc(a):
    S = json.load(open(a.secim))
    kosu = json.load(open(a.kosu)) if Path(a.kosu).exists() else {}
    ids = {r["cift"]: r["listing_id"] for r in csv.DictReader(open(a.ids, encoding="utf-8"))}
    satir, hata = [], list(S["hata"])
    for c in ids:
        s = S["secim"].get(c)
        if not s:
            satir.append(dict(cift=c, listing_id=ids[c], durum="EKSIK")); continue
        p = Path(a.kok) / s["dosya"]
        if not p.exists():
            hata.append(f"{c}: indirilemedi {s['dosya']}"); satir.append(dict(cift=c, listing_id=ids[c], durum="INDIRILEMEDI")); continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        f = ffprobe(p)
        ok = f["genislik"] == 1440 and f["yukseklik"] == 1080 and f["kare"] > 0
        if not ok:
            hata.append(f"{c}: video {f}")
        satir.append(dict(cift=c, listing_id=ids[c], damga=s["damga"], kosu=kosu.get(s["damga"], ""), dosya=s["dosya"],
                          bayt=p.stat().st_size, sha256=h, kare=f["kare"], fps=f["fps"], sure=f["sure"],
                          boyut=f"{f['genislik']}x{f['yukseklik']}", zorunlu="evet" if s["zorunlu"] else "",
                          adaylar=" ".join(s["adaylar"]), durum="OK" if ok else "HATA"))
    tekrar = len(satir) - len({r["cift"] for r in satir})
    eksik = sum(1 for r in satir if r["durum"] != "OK")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    alan = ["cift", "listing_id", "damga", "kosu", "dosya", "bayt", "sha256", "kare", "fps", "sure", "boyut", "zorunlu", "adaylar", "durum"]
    with open(out / "VIDEO_ESLEME.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alan); w.writeheader(); w.writerows(satir)
    dag = {}
    for r in satir:
        dag[r.get("damga", "-")] = dag.get(r.get("damga", "-"), 0) + 1
    md = [f"# YD video esleme ({len(satir)} satir, tekrar {tekrar}, eksik/hatali {eksik})", "",
          "Kural: cift basina en son damga; 3 yeni kapakli cift zorunlu klasorden. Kaynak: Drive TEMP/YD_VIDEO_ORNEK43 (rclone lsjson).", "",
          "| damga | kosu | cift sayisi |", "|---|---|---|"] + [f"| {d} | {kosu.get(d, '')} | {n} |" for d, n in sorted(dag.items())]
    md += ["", "| cift | damga | dosya | bayt | sha256 | kare |", "|---|---|---|---|---|---|"]
    md += [f"| {r['cift']} | {r.get('damga', '')} | {r.get('dosya', '')} | {r.get('bayt', '')} | {r.get('sha256', '')} | {r.get('kare', '')} |"
           for r in satir]
    if hata:
        md += ["", "## Hata"] + [f"- {h}" for h in hata]
    (out / "VIDEO_ESLEME.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"VIDEO_ESLEME: {len(satir)} satir | tekrar {tekrar} | eksik/hatali {eksik} | damga dagilimi {dag}")
    for h in hata:
        print("::error::" + h)
    return 1 if (len(satir) != 78 or tekrar or eksik or hata) else 0


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="adim", required=True)
    s1 = sp.add_parser("sec"); s1.add_argument("lsjson"); s1.add_argument("ids"); s1.add_argument("out")
    s1.add_argument("--zorunlu", action="append", default=[])
    s2 = sp.add_parser("olc"); s2.add_argument("secim"); s2.add_argument("kok"); s2.add_argument("kosu"); s2.add_argument("ids")
    s2.add_argument("out")
    a = ap.parse_args()
    sys.exit(sec(a) if a.adim == "sec" else olc(a))


if __name__ == "__main__":
    main()
