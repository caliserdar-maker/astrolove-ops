#!/usr/bin/env python3
"""Sade kupa 8 dal gorseli (Serdar 30 Eki onayi; Merkez gorevi). ETSY YOK.
Girdi --tsv DAL_URL.tsv (stil, sayfa, bitis_utc, url; Canva imzali disa aktarma linkleri; Drive TEMP/KUPA_SADE_DAL_20261030).
Imzali URL'ler loga / depoya / is akisi girdisine YAZILMAZ: once ::add-mask:: ile maskelenir, ciktida yalniz stil adi.
Satir basina kalan sure = X-Amz-Date + X-Amz-Expires - simdi; < 5 dk ise indirilmez (SURE_AZ). En fazla 2 indirme denemesi.
Kapi (her dosya): JPEG, 1264x1264 (Serdar 30 Eki: Canva kaynak gorseli 1264 px; 3950 indirmede buyutme); 8 dosyanin sha256'si
birbirinden farkli; 8 stil tam. Yeniden boyutlandirma YOK: dosya oldugu gibi.
Cikti --cikti: dal_sade/<stil>.jpg (indirilen bayt aynen), OZET.md (sha256 tablosu).
--betik / --betik-sha: Drive'daki uretim betiginin sha256 ve boyut kapisi (DUR = cikis 2). Cikis 0 = hepsi PASS."""
import argparse
import csv
import hashlib
import io
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

STILLER = ("orange", "fig", "olive", "pomegranate", "almond", "lemon", "grape", "loquat")
BOY, SURE_ALT = (1264, 1264), 300


def kalan_sn(url, simdi):
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    t = datetime.strptime(q["X-Amz-Date"][0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    return t + int(q["X-Amz-Expires"][0]) - simdi


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tsv", required=True); ap.add_argument("--cikti", required=True)
    ap.add_argument("--betik", default=""); ap.add_argument("--betik-sha", default=""); ap.add_argument("--betik-boyut", type=int, default=0)
    a = ap.parse_args(argv)
    if a.betik:
        b = Path(a.betik).read_bytes(); h = hashlib.sha256(b).hexdigest()
        print(f"betik {Path(a.betik).name}: {len(b)} B sha256 {h}")
        if h != a.betik_sha or (a.betik_boyut and len(b) != a.betik_boyut):
            print(f"::error::DUR: betik boyut / sha256 beklenenden farkli (beklenen {a.betik_boyut} B {a.betik_sha})"); return 2
    rows = list(csv.DictReader(open(a.tsv, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        print(f"::add-mask::{r['url']}", flush=True)
        sig = urllib.parse.parse_qs(urllib.parse.urlsplit(r["url"]).query).get("X-Amz-Signature", [""])[0]
        if sig:
            print(f"::add-mask::{sig}", flush=True)
    stiller = [r["stil"] for r in rows]
    out = Path(a.cikti); (out / "dal_sade").mkdir(parents=True, exist_ok=True)
    sonuc, sorun = [], []
    if sorted(stiller) != sorted(STILLER):
        sorun.append(f"TSV stilleri {stiller} (8 stil beklenir)")
    for r in rows:
        st = r["stil"]
        try:
            kal = kalan_sn(r["url"], time.time())
        except (KeyError, ValueError):
            sorun.append(f"{st}: link suresi okunamadi"); continue
        if kal < SURE_ALT:
            sorun.append(f"{st}: SURE_AZ kalan {kal:.0f} sn"); print(f"{st} SURE_AZ kalan {kal:.0f} sn", flush=True); continue
        icerik = None
        for dn in (1, 2):
            try:
                x = requests.get(r["url"], timeout=180)
                if x.status_code == 200:
                    icerik = x.content; break
                print(f"{st} deneme {dn}: HTTP {x.status_code}", flush=True)
            except requests.RequestException as e:
                print(f"{st} deneme {dn}: {type(e).__name__}", flush=True)
        if icerik is None:
            sorun.append(f"{st}: indirilemedi (2 deneme)"); continue
        im = Image.open(io.BytesIO(icerik))
        if im.format != "JPEG" or im.size != BOY:
            sorun.append(f"{st}: {im.format} {im.size} (JPEG {BOY[0]}x{BOY[1]} beklenir)"); continue
        (out / "dal_sade" / f"{st}.jpg").write_bytes(icerik)
        s1 = hashlib.sha256(icerik).hexdigest()
        sonuc.append((st, s1, len(icerik), int(kal // 60)))
        print(f"{st}: JPEG {BOY[0]}x{BOY[1]} {len(icerik)} B sha256 {s1} (link kalan {int(kal // 60)} dk)", flush=True)
    if len({s[1] for s in sonuc}) != len(sonuc):
        sorun.append("dosyalarin sha256'si birbirinden farkli degil")
    if len(sonuc) != len(STILLER):
        sorun.append(f"{len(sonuc)}/8 dosya gecti")
    md = ["# Sade kupa dal gorselleri (8)\n", f"PASS {len(sonuc)}/8 | sorun {len(sorun)}\n",
          "| stil | sha256 | bayt |", "|---|---|---|"]
    md += [f"| {s[0]} | {s[1]} | {s[2]} |" for s in sonuc] + [f"\n- SORUN: {x}" for x in sorun]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
