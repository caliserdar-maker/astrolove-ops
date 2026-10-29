#!/usr/bin/env python3
"""Galeri v11 B1 yedek, KILITSIZ indirme asamasi (Merkez 29 Eki). ETSY API YOK (yalniz etsystatic CDN; Etsy kilidi gerekmez).
Girdi --in: galeri_v11_yedek_oku.py ciktisi (<ilan>_<CIFT>/GALERI.json, OKUMA.csv; Drive TEMP/POSTER_GALERI_V11_YEDEK/<damga>).
Ilan basina: her gorsel url_fullxfull -> r<rank>_<listing_image_id>.jpg (boyut = JSON full_width x full_height), her video
video_url -> video_<video_id>.mp4 (bayt > 0). OZET.md galeri_v10_liste.ozet_oku bicimi: | listing_id | cift | dosya | durum | not |
(dosya = gorsel dosyasi sayisi; PASS = 9 gorsel dosyasi tam + video dosyalari tam). ETA sayaci (islenen/toplam, gecen, kalan).
Cikti ayni klasore (--in) yazilir; is akisi yalniz yeni dosyalari Drive'a --immutable ile ekler. Cikis 0 = 78/78 PASS."""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

BEKLENEN = 9
CDN = ("https://i.etsystatic.com/", "https://v.etsystatic.com/")


def indir(u, p, tekrar=4):
    if not str(u or "").startswith(CDN):
        return f"CDN disi adres ({str(u)[:40]})"
    for i in range(tekrar):
        try:
            r = requests.get(u, timeout=120); r.raise_for_status(); p.write_bytes(r.content); return None
        except Exception as e:  # noqa: BLE001
            if i == tekrar - 1:
                return f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(2 ** i)


def isler_kur(kok):
    ilanlar, isler = [], []
    for gj in sorted(kok.glob("*_*/GALERI.json")):
        j = json.loads(gj.read_text(encoding="utf-8")); d = gj.parent
        ilanlar.append((d, j))
        isler += [(g["url_fullxfull"], d / f"r{g['rank']}_{g['listing_image_id']}.jpg") for g in j.get("gorseller") or []]
        isler += [(v.get("video_url"), d / f"video_{v['video_id']}.mp4") for v in j.get("videolar") or []]
    return ilanlar, isler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="kok", required=True); ap.add_argument("--is", dest="is_", type=int, default=8)
    a = ap.parse_args(argv)
    kok = Path(a.kok)
    ilanlar, isler = isler_kur(kok)
    if not ilanlar:
        print("::error::GALERI.json yok"); return 1
    t0, hata = time.time(), {}
    with ThreadPoolExecutor(a.is_) as ex:
        for n, ((_, p), h) in enumerate(zip(isler, ex.map(lambda x: indir(*x), isler)), 1):
            if h:
                hata[str(p)] = h
            if n % 50 == 0 or n == len(isler):
                g = time.time() - t0
                print(f"INDIR {n}/{len(isler)} %{100 * n // len(isler)} gecen {g:.0f} sn kalan {g / n * (len(isler) - n):.0f} sn", flush=True)
    satir = []
    for d, j in ilanlar:
        neden, say = [], 0
        g = j.get("gorseller") or []
        if len(g) != BEKLENEN:
            neden.append(f"JSON'da {len(g)} gorsel (beklenen {BEKLENEN})")
        for x in g:
            p = d / f"r{x['rank']}_{x['listing_image_id']}.jpg"
            if str(p) in hata or not p.exists():
                neden.append(f"r{x['rank']} indirilemedi ({hata.get(str(p), 'yok')})"); continue
            try:
                with Image.open(p) as im:
                    bt = im.size
            except Exception:  # noqa: BLE001
                neden.append(f"r{x['rank']} okunamadi"); continue
            if bt != (x["full_width"], x["full_height"]):
                neden.append(f"r{x['rank']} boyut {bt[0]}x{bt[1]} != {x['full_width']}x{x['full_height']}"); continue
            say += 1
        for v in j.get("videolar") or []:
            p = d / f"video_{v['video_id']}.mp4"
            if str(p) in hata or not p.exists() or p.stat().st_size == 0:
                neden.append(f"video {v['video_id']} indirilemedi ({hata.get(str(p), 'yok')})")
        satir.append([j["listing_id"], j["cift"], say, "PASS" if not neden and say == BEKLENEN else "FAIL", "; ".join(neden)])
    gecti = sum(1 for s in satir if s[3] == "PASS")
    with open(kok / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Poster 78 galeri v11 yedegi (dosyalar)\n\nilan PASS {gecti}/{len(satir)} | gorsel dosyasi {sum(s[2] for s in satir)} "
                f"(beklenen {BEKLENEN * len(satir)}) | indirme hatasi {len(hata)}\n\n"
                "| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n")
        f.writelines(f"| {' | '.join(map(str, s))} |\n" for s in satir)
    print(f"YEDEK OZET: ilan PASS {gecti}/{len(satir)} | hata {len(hata)}", flush=True)
    return 0 if gecti == len(satir) == 78 else 1


if __name__ == "__main__":
    sys.exit(main())
