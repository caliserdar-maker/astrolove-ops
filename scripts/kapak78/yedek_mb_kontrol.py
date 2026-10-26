#!/usr/bin/env python3
"""Poster 78 kapak plan adim 1-2 (Merkez 26 Eki; Serdar onayi). ETSY API YOK, ETSY'YE YAZMA YOK.
A) YEDEK: POSTER_GORSEL.json'daki 78 ilanin tum gorselleri url_fullxfull'dan indirilir:
   <out>/YEDEK/<listing_id>_<CIFT>/r<rank>_<image_id>.jpg + GALERI.json (o ilanin gorseller + baglar kaydi aynen).
   Kontrol: ilan basina 17 dosya, her dosyanin boyutu JSON'daki full_width x full_height. YEDEK/OZET.md: 78 satir PASS/FAIL.
B) MB KART ON KONTROLU: KAPAK_KAYNAK.csv'deki Midnight Blue kartinda (rank 13) poster kutusu olculur.
   Yontem: gri ton, Gauss sigma 1; her kenar icin referans kutunun +-80 px penceresinde, kenar boyunca (uclardan 200 px iceride)
   ortalama |gradyan| profili; tepe = kenar. x0/y0 = ilk poster pikseli, x1/y1 = posterden sonraki ilk piksel.
   Once iki referans kart (8650688109 SAG_SAG, 8651329026 CL) referans kutuya +-2 px icinde olmali; degilse olcum gecersiz (DUR).
   Herhangi bir kenarda > 5 px sapma: BLOK. Cikti MB_KONTROL.csv (listing_id, cift, x0, y0, x1, y1, sapma, durum) + REF_*.jpg (cizimli)."""
import argparse
import csv
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

REF_KUTU = (814, 154, 2184, 1900)
REF_KART = {"8650688109": "SAGITTARIUS_SAGITTARIUS", "8651329026": "CANCER_LIBRA"}
PENCERE, ICERI, REF_TOL, BLOK_TOL, BEKLENEN = 80, 200, 2, 5, 17


def indir(u, p, tekrar=4):
    for i in range(tekrar):
        try:
            r = requests.get(u, timeout=90); r.raise_for_status(); p.write_bytes(r.content); return None
        except Exception as e:  # noqa: BLE001
            if i == tekrar - 1:
                return f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(2 ** i)


def yedek(ilanlar, kok):
    isler, satir = [], []
    for k in ilanlar:
        d = kok / f"{k['listing_id']}_{k['cift']}"; d.mkdir(parents=True, exist_ok=True)
        (d / "GALERI.json").write_text(json.dumps(dict(gorseller=k["gorseller"], baglar=k["baglar"]), ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        for g in k["gorseller"]:
            isler.append((g["url_fullxfull"], d / f"r{g['rank']}_{g['listing_image_id']}.jpg"))
    t0, hata = time.time(), {}
    with ThreadPoolExecutor(8) as ex:
        for n, (p, h) in enumerate(zip([i[1] for i in isler], ex.map(lambda a: indir(*a), isler)), 1):
            if h:
                hata[str(p)] = h
            if n % 100 == 0 or n == len(isler):
                g = time.time() - t0
                print(f"YEDEK {n}/{len(isler)} %{100 * n // len(isler)} gecen {g:.0f} sn kalan {g / n * (len(isler) - n):.0f} sn", flush=True)
    toplam = 0
    for k in ilanlar:
        d = kok / f"{k['listing_id']}_{k['cift']}"
        neden = []
        if len(k["gorseller"]) != BEKLENEN:
            neden.append(f"JSON'da {len(k['gorseller'])} gorsel (beklenen {BEKLENEN})")
        say = 0
        for g in k["gorseller"]:
            p = d / f"r{g['rank']}_{g['listing_image_id']}.jpg"
            if str(p) in hata or not p.exists():
                neden.append(f"r{g['rank']} indirilemedi ({hata.get(str(p), 'yok')})"); continue
            try:
                with Image.open(p) as im:
                    bt = im.size
            except Exception:  # noqa: BLE001
                neden.append(f"r{g['rank']} okunamadi"); continue
            say += 1
            if bt != (g["full_width"], g["full_height"]):
                neden.append(f"r{g['rank']} boyut {bt[0]}x{bt[1]} != {g['full_width']}x{g['full_height']}")
        toplam += say
        satir.append([k["listing_id"], k["cift"], say, "PASS" if not neden and say == BEKLENEN else "FAIL", "; ".join(neden)])
    gecti = sum(1 for s in satir if s[3] == "PASS")
    with open(kok / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Poster 78 galeri yedegi\n\nilan PASS {gecti}/{len(satir)} | dosya {toplam} (beklenen {BEKLENEN * len(satir)})\n\n"
                "| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n")
        f.writelines(f"| {' | '.join(map(str, s))} |\n" for s in satir)
    print(f"YEDEK OZET: ilan PASS {gecti}/{len(satir)} | dosya {toplam}")
    return gecti, len(satir), toplam


def kenar(L, eksen, merkez, a, b):
    """eksen 'x': dikey kenar, sutun profili (satir a..b); 'y': yatay kenar, satir profili (sutun a..b). Tepe konumu + guc."""
    lo = max(1, merkez - PENCERE); hi = min((L.shape[1] if eksen == "x" else L.shape[0]) - 1, merkez + PENCERE)
    if eksen == "x":
        g = np.abs(L[a:b, lo:hi + 1] - L[a:b, lo - 1:hi]).mean(axis=0)
    else:
        g = np.abs(L[lo:hi + 1, a:b] - L[lo - 1:hi, a:b]).mean(axis=1)
    i = int(np.argmax(g)); s = np.sort(g)
    return lo + i, round(float(g[i]), 2), round(float(g[i] / max(np.median(g), 1e-6)), 1)


def olc(p):
    im = Image.open(p).convert("L").filter(ImageFilter.GaussianBlur(1))
    L = np.asarray(im, dtype=np.float32)
    x0r, y0r, x1r, y1r = REF_KUTU
    x0, gx0, _ = kenar(L, "x", x0r, y0r + ICERI, y1r - ICERI)
    x1, gx1, _ = kenar(L, "x", x1r, y0r + ICERI, y1r - ICERI)
    y0, gy0, _ = kenar(L, "y", y0r, x0r + ICERI, x1r - ICERI)
    y1, gy1, _ = kenar(L, "y", y1r, x0r + ICERI, x1r - ICERI)
    return (x0, y0, x1, y1), min(gx0, gx1, gy0, gy1), im.size


def mb_kontrol(kaynak_csv, yedek_kok, out):
    rows = [r for r in csv.DictReader(open(kaynak_csv, encoding="utf-8")) if r["tur"] == "poster"]
    kart = {}
    for r in rows:
        bul = list(yedek_kok.glob(f"{r['listing_id']}_*/r*_{r['kaynak_image_id']}.jpg"))
        kart[r["listing_id"]] = (r, bul[0] if bul else None)
    ref_ok, ref_not = True, []
    for r, p in kart.values():
        if r["kaynak_image_id"] in REF_KART:
            if not p:
                ref_ok = False; ref_not.append(f"{r['kaynak_image_id']} indirilemedi"); continue
            k, guc, _ = olc(p)
            sap = max(abs(a - b) for a, b in zip(k, REF_KUTU))
            ref_not.append(f"{REF_KART[r['kaynak_image_id']]} {r['kaynak_image_id']}: {k} sapma {sap} guc {guc}")
            ref_ok &= sap <= REF_TOL
            im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
            d.rectangle(REF_KUTU, outline=(0, 255, 0), width=3); d.rectangle((k[0], k[1], k[2] - 1, k[3] - 1), outline=(255, 0, 0), width=2)
            im.resize((1500, 1125)).save(out / f"REF_{REF_KART[r['kaynak_image_id']]}.jpg", quality=90)
    if sum(1 for r, _ in kart.values() if r["kaynak_image_id"] in REF_KART) != 2:
        ref_ok = False; ref_not.append("iki referans kart KAPAK_KAYNAK.csv'de bulunamadi")
    print("REFERANS:", "PASS" if ref_ok else "FAIL", "|", " ; ".join(ref_not), flush=True)
    satir = []
    for lid, (r, p) in kart.items():
        if not p:
            satir.append([lid, r["cift"], "", "", "", "", "", "FAIL indirilemedi"]); continue
        k, guc, bt = olc(p)
        sap = max(abs(a - b) for a, b in zip(k, REF_KUTU))
        if not ref_ok:
            durum = "OLCUM_GECERSIZ"
        elif bt != (3000, 2250):
            durum = f"BLOK boyut {bt[0]}x{bt[1]}"
        else:
            durum = "BLOK" if sap > BLOK_TOL else "PASS"
        satir.append([lid, r["cift"], *k, sap, durum])
    with open(out / "MB_KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "x0", "y0", "x1", "y1", "sapma", "durum"]); w.writerows(satir)
    (out / "MB_REFERANS.txt").write_text(("PASS" if ref_ok else "FAIL") + "\n" + "\n".join(ref_not) + "\n", encoding="utf-8")
    blok = [s for s in satir if s[7] != "PASS"]
    print(f"MB OZET: kart {len(satir)} | PASS {len(satir) - len(blok)} | BLOK/FAIL {len(blok)}: "
          + ", ".join(f"{s[1]}({s[6]})" for s in blok[:20]))
    return ref_ok, len(satir) - len(blok), blok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster-json", required=True)
    ap.add_argument("--kaynak-csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--yalniz-mb", default="", help="mevcut YEDEK klasoru (yalniz B; yerel test)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.yalniz_mb:
        yk = pathlib.Path(a.yalniz_mb); ga = gt = dos = None
    else:
        ilanlar = json.load(open(a.poster_json, encoding="utf-8"))["ilanlar"]
        yk = out / "YEDEK"; yk.mkdir(exist_ok=True)
        ga, gt, dos = yedek(ilanlar, yk)
    ref_ok, mb_pass, blok = mb_kontrol(a.kaynak_csv, yk, out)
    print(f"SONUC: A {ga}/{gt} dosya {dos} | B referans {'PASS' if ref_ok else 'FAIL'} PASS {mb_pass} BLOK {len(blok)}")
    return 0 if ref_ok and (ga is None or ga == gt) else 1


if __name__ == "__main__":
    sys.exit(main())
