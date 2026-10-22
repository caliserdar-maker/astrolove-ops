#!/usr/bin/env python3
"""Etsy kota teshisi (Serdar 23 Eki, SIRA 1): Actions job loglarindan YALNIZ sayilar cikar (metin yok, musteri verisi yok).
Girdi: log dosyalari dizini (<run>_<job>.txt) + meta JSON (run/job/workflow/zaman). Cikti: KOTA_TESHIS.csv + ozet (stdout).
Sayilar: 'istek N' (betigin kendi sayaci; en buyugu), 'kota N' / x-remaining-today N (ilk, son, en kucuk), etsy-kota
/openapi-ping CSV satiri yok. Kaynak etiketi: 'sayac' (istek N var) ya da 'kota_farki' (ilk - son kota; esz amanli kosular
karisabilir, TAHMIN) ya da 'yok'."""
import csv
import json
import pathlib
import re
import sys

ISTEK = re.compile(r"\bistek[ =:]+(\d+)")
KOTA = re.compile(r"(?:\bkota|x-remaining-today|remaining)[\"' =:]+(\d+)")
LIMIT = re.compile(r"x-limit-per-day[\"' =:]+(\d+)")


def say(metin):
    ist = [int(x) for x in ISTEK.findall(metin)]
    kot = [int(x) for x in KOTA.findall(metin)]
    lim = sorted({int(x) for x in LIMIT.findall(metin)})
    r = dict(istek=max(ist) if ist else None, kota_ilk=kot[0] if kot else None, kota_son=kot[-1] if kot else None,
             kota_min=min(kot) if kot else None, kota_n=len(kot), limit=lim)
    if r["istek"] is not None:
        r["tahmin"], r["kaynak"] = r["istek"], "sayac"
    elif len(kot) >= 2 and kot[0] >= kot[-1]:
        r["tahmin"], r["kaynak"] = kot[0] - kot[-1], "kota_farki"
    else:
        r["tahmin"], r["kaynak"] = None, "yok"
    return r


def main():
    d, meta_p, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    meta = json.loads(meta_p.read_text())
    satir = []
    for m in meta:
        p = d / f"{m['run']}_{m['job']}.txt"
        r = say(p.read_text(errors="replace")) if p.exists() else dict(kaynak="log_yok", tahmin=None)
        satir.append({**m, **{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()}})
    alan = ["run", "job", "workflow", "olay", "baslangic", "bitis", "sonuc", "istek", "kota_ilk", "kota_son", "kota_min",
            "kota_n", "limit", "tahmin", "kaynak"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore"); w.writeheader(); w.writerows(satir)
    top = {}
    for s in satir:
        t = top.setdefault(s["workflow"], [0, 0, 0])
        t[0] += 1
        if s.get("tahmin") is not None:
            t[1] += int(s["tahmin"])
        else:
            t[2] += 1
        print(f"{s['run']} {s['workflow']} {s['baslangic']} istek={s.get('istek')} kota {s.get('kota_ilk')}->{s.get('kota_son')} "
              f"min {s.get('kota_min')} limit {s.get('limit')} | {s.get('tahmin')} ({s.get('kaynak')})")
    for wf, (n, ist, bil) in sorted(top.items(), key=lambda z: -z[1][1]):
        print(f"TOPLAM {wf}: kosu {n}, istek {ist}, sayisiz {bil}")


if __name__ == "__main__":
    main()
