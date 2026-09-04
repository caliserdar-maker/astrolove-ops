#!/usr/bin/env python3
"""
MADDE 4 TAM TABLOSU + SET06 METIN KIRPMA KANITI + FAZLA DOSYA DOKUMU.
Salt okur; tek cikti olcum tablolari ve gorsel kanit kirpmalaridir.

  1) WP_AUDIT_M04.csv'den 14 ekranin tekillestirilmis tablosu. Kirpma
     geometrisi quad + cihaz tuvalinden turedigi icin ciftler arasi
     degismez; her (sahne, ekran) bir kez yazilir.
  2) SET06'nin 1.536 oranli Desktop ekraninda metin blogunun sagdan
     kirpildigi bolge: KAYNAK ile EKRANA GIDEN yan yana, kesme cizgisi
     kirmizi. Tam cozunurluk (yeniden ornekleme YOK).
  3) FINAL_V2 / DELIVERY / MOCKUP_V2 klasorlerindeki dosyalarin ad ve
     tarih dokumu; beklenen ad kalibinin disinda kalanlar ayrica listelenir.
     ZIP'lerin gercek icerigi (namelist) okunarak hangi 16 wallpaper'in
     teslimata girdigi teyit edilir.
"""
import argparse
import collections
import csv
import json
import os
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import DEVICES, EDITIONS, imread, log  # noqa: E402
from wp_audit_crop import ELEMENTS, crop_geometry  # noqa: E402

TEXT_BOX_DESKTOP = ELEMENTS["Desktop"]["metin"]      # 285,1245,3603,2154
LABEL_H = 54
PAD_LEFT = 760          # kesme cizgisinin solunda gosterilecek baglam (px)
PAD_RIGHT = 60


# ------------------------------------------------------------------ 1) tablo
def tablo(m04_path, out_csv):
    seen, rows = set(), []
    with open(m04_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (r.get("scene"), r.get("screen"))
            if key in seen or not r.get("scene"):
                continue
            seen.add(key)
            rows.append(r)
    rows.sort(key=lambda r: (r["scene"], str(r["screen"])))
    log(f"\n=== MADDE 4: 14 ekranin tam tablosu ({len(rows)} satir) ===")
    hdr = ("| sahne/ekran | cihaz | edisyon | oran | kaynak orani | kirpma % | "
           "hangi kenardan kac px | KIRPILAN OGE |")
    log(hdr); log("|" + "---|" * 8)
    for r in rows:
        log(f"| {r['scene']}/{r['screen']} | {r['device']} | {r.get('edition','')} | "
            f"{r['quad_aspect']} | {r['src_aspect']} | {r['crop_pct']} | "
            f"{r['crop_edges']} | {r['clipped']} |")
    if out_csv:
        cols = ["scene", "screen", "device", "edition", "quad_aspect", "src_aspect",
                "crop_pct", "crop_edges", "clipped"]
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        log(f"yazildi: {out_csv}")
    return rows


# ------------------------------------------------------------------ 2) kanit
def etiket(img, metin, renk=(30, 30, 30)):
    """Gorselin ustune beyaz seritte etiket ekler (icerik yeniden orneklenmez)."""
    bar = np.full((LABEL_H, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, metin, (12, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, renk, 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def kanit(wp_path, kept_x1, out_path):
    """Kaynak ile ekrana gideni yan yana koyar; kesme cizgisi kirmizi.
    Tam cozunurluk: hicbir yeniden olceklendirme yok."""
    img = imread(wp_path)
    H0, W0 = img.shape[:2]
    if (W0, H0) != DEVICES["Desktop"]:
        raise SystemExit(f"HATA: {wp_path.name} olcusu {W0}x{H0}, beklenen {DEVICES['Desktop']}")
    tl, tt, tr, tb = TEXT_BOX_DESKTOP
    x1 = int(round(kept_x1))
    l = max(0, x1 - PAD_LEFT)
    r = min(W0, tr + PAD_RIGHT)
    once = img[tt:tb, l:r].copy()
    sonra = img[tt:tb, l:r].copy()
    sonra[:, x1 - l:] = 0                      # cover disinda kalan surtun: ekrana gitmez
    cx = x1 - l
    for k in (once, sonra):
        cv2.line(k, (cx, 0), (cx, k.shape[0] - 1), (0, 0, 255), 3, cv2.LINE_AA)
    kayip = tr - x1
    once = etiket(once, f"KAYNAK (kirpma oncesi) - metin blogu sag kenar x={tr}")
    sonra = etiket(sonra, f"EKRANA GIDEN (kirpma sonrasi) - kesme x={x1}, kayip {kayip} px")
    ayirici = np.full((once.shape[0], 8, 3), 255, np.uint8)
    out = np.hstack([once, ayirici, sonra])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), out, [int(cv2.IMWRITE_JPEG_QUALITY), 97])
    log(f"  {Path(out_path).name}: {out.shape[1]}x{out.shape[0]} "
        f"(panel {once.shape[1]}x{once.shape[0]}, kesme x={x1}, kayip {kayip} px)")
    return out.shape


# ------------------------------------------------------------------ 3) dosyalar
def lsjson_grup(path):
    out = collections.defaultdict(list)
    for r in json.loads(Path(path).read_text()):
        if r.get("IsDir"):
            continue
        rel = r.get("Path", "")
        if "/" not in rel:
            continue
        out[rel.split("/", 1)[0].upper()].append(
            (r.get("Name", ""), int(r.get("Size") or 0), r.get("ModTime", "")[:19]))
    return out


def beklenen_adlar(kume, pair):
    if kume == "wp":
        return {f"AstroLove_{pair}_{ed}_{dev}.jpg" for ed in EDITIONS for dev in DEVICES}
    if kume == "zip":
        return {f"AstroLove_{pair}_{ed}.zip" for ed in EDITIONS}
    return set()          # mock: ad kalibi sahneye gore degisir, hepsi listelenir


def dosya_dokumu(kume, js_path, pairs, ornek):
    grup = lsjson_grup(js_path)
    log(f"\n=== {kume.upper()}: klasor dokumu ({len(grup)} klasor) ===")
    # 1) tum ciftlerde adet dagilimi
    dag = collections.Counter(len(v) for v in grup.values())
    log(f"adet dagilimi: " + ", ".join(f"{n} dosya x {k} klasor" for n, k in sorted(dag.items())))
    # 2) beklenen kalip disinda kalanlar - tum ciftlerde
    fazla_ad = collections.Counter()
    for pair in pairs:
        up = pair.upper()
        bek = beklenen_adlar(kume, pair)
        for name, _, _ in grup.get(up, []):
            if bek and name not in bek:
                fazla_ad[name.replace(pair, "<CIFT>")] += 1
    if fazla_ad:
        log("beklenen ad kalibinin DISINDA kalan dosyalar (ad kalibi -> kac ciftte):")
        for name, n in fazla_ad.most_common():
            log(f"  {name}  ->  {n} cift")
    elif kume != "mock":
        log("beklenen ad kalibinin disinda dosya yok")
    # 3) ornek ciftin tam listesi (ad + boyut + tarih)
    up = ornek.upper()
    log(f"ornek klasor {up} ({len(grup.get(up, []))} dosya):")
    for name, size, mt in sorted(grup.get(up, [])):
        log(f"  {mt}  {size:>10}  {name}")
    return grup


def zip_icerik(zip_dir, pair):
    log(f"\n=== ZIP icerigi (teslimata giren dosyalar) - {pair} ===")
    toplam = []
    for ed in EDITIONS:
        p = Path(zip_dir) / pair.upper() / f"AstroLove_{pair}_{ed}.zip"
        if not p.exists():
            log(f"  {p.name}: YOK"); continue
        with zipfile.ZipFile(p) as zf:
            names = sorted(zf.namelist())
        wp = [n for n in names if n.lower().endswith(".jpg")]
        toplam += wp
        log(f"  {p.name} ({p.stat().st_size} B): {len(names)} girdi -> {names}")
    log(f"  ZIP'lere giren wallpaper toplami: {len(toplam)} dosya "
        f"({len(set(toplam))} tekil)")
    return toplam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m04", required=True)
    ap.add_argument("--out-geo", default="")
    ap.add_argument("--calib", required=True)
    ap.add_argument("--wp-dir", required=True, help="kanit icin Desktop wallpaper'lar (duz klasor)")
    ap.add_argument("--kanit-pairs", required=True, help="virgullu 3 cift")
    ap.add_argument("--crop-dir", default="_crops")
    ap.add_argument("--wp-json", default="")
    ap.add_argument("--zip-json", default="")
    ap.add_argument("--mock-json", default="")
    ap.add_argument("--pairs-file", default="")
    ap.add_argument("--ornek-pair", default="Aries_Aries")
    ap.add_argument("--zip-dir", default="")
    a = ap.parse_args()

    tablo(a.m04, a.out_geo)

    # --- 2) SET06'nin 1.536 oranli Desktop ekranini kalibrasyondan bul
    calib = json.loads((Path(a.calib) / "calib.json").read_text())
    hedef = None
    for s in calib["scenes"]["SET06"]["screens"]:
        if s["device"] != "Desktop":
            continue
        g = crop_geometry("Desktop", s["quad"])
        log(f"\nSET06/{s['id']} Desktop: oran {g['quad_aspect']:.4f}, kirpma %{g['crop_pct']:.2f}, "
            f"[{g['edges']}], OGE {g['clipped']}")
        if g["clipped_any"]:
            hedef = (s, g)
    if hedef is None:
        raise SystemExit("HATA: SET06'da oge kirpan Desktop ekrani bulunamadi")
    s, g = hedef
    kept_x1 = g["kept"][2]
    log(f"\n=== MADDE 4 KANITI: SET06/{s['id']} Desktop, kesme x={kept_x1:.0f}, "
        f"metin blogu sag kenar x={TEXT_BOX_DESKTOP[2]} ===")
    for pair in [p.strip() for p in a.kanit_pairs.split(",") if p.strip()]:
        wp = Path(a.wp_dir) / f"AstroLove_{pair}_Midnight_Blue_Desktop.jpg"
        if not wp.exists():
            log(f"  {wp.name}: YOK, atlandi"); continue
        kanit(wp, kept_x1, Path(a.crop_dir) / f"M04_SET06_{pair}_METIN_KESIT.jpg")

    # --- 3) fazladan dosyalar
    pairs = ([p.strip() for p in Path(a.pairs_file).read_text().split() if p.strip()]
             if a.pairs_file else [])
    for kume, js in (("wp", a.wp_json), ("zip", a.zip_json), ("mock", a.mock_json)):
        if js and Path(js).exists():
            dosya_dokumu(kume, js, pairs, a.ornek_pair)
    if a.zip_dir:
        zip_icerik(a.zip_dir, a.ornek_pair)
    return 0


if __name__ == "__main__":
    sys.exit(main())
