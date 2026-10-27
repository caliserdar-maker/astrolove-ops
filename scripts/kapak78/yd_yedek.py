#!/usr/bin/env python3
"""YD (1st Anniversary) 78 ilan galeri yedegi (plan v3 adim 5; Merkez 27 Eki). ETSY API YOK, Etsy'ye yazma yok, kilit yok.
Girdi: TEMP/YD_ENVANTER_20261026/HAM/<listing_id>.json (yd_envanter_oku.py ciktisi; images = Etsy gorsel kayitlari, url_fullxfull,
full_width / full_height; variation_images = Style bagi) + data/pod/yd78_ids.csv (78 ilan).
Islem: yedek_mb_kontrol.yedek (A kismi, beklenen 13): <out>/<listing_id>_<CIFT>/r<rank>_<image_id>.jpg + GALERI.json (gorseller +
baglar aynen) + <out>/OZET.md (ilan basina 13 dosya, boyut = JSON) + <out>/BAGLAR.csv (listing_id, cift, stil, value_id, image_id,
rank). Indirme etsystatic CDN'den (Etsy API degil).
Kapilar: yd78 listesindeki her ilanin HAM dosyasi var ve listing_id ayni; yoksa o ilan FAIL (OZET'e yazilir). Cikis: 78/78 PASS ise 0."""
import argparse
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yedek_mb_kontrol as Y  # noqa: E402

BEKLENEN = 13


def ilanlar_oku(ham_dir, ciftler):
    rows = [r for r in csv.DictReader(open(ciftler, encoding="utf-8-sig")) if r.get("listing_id")]
    ilan, eksik = [], []
    for r in rows:
        p = pathlib.Path(ham_dir) / f"{r['listing_id']}.json"
        if not p.exists():
            eksik.append((r["listing_id"], r["cift"], "HAM dosyasi yok")); continue
        h = json.loads(p.read_text(encoding="utf-8"))
        if str((h.get("listing") or {}).get("listing_id")) != r["listing_id"]:
            eksik.append((r["listing_id"], r["cift"], "HAM listing_id farkli")); continue
        g = sorted(h.get("images") or [], key=lambda x: x.get("rank") or 0)
        ilan.append(dict(listing_id=r["listing_id"], cift=r["cift"], gorseller=g, baglar=h.get("variation_images") or []))
    return rows, ilan, eksik


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ham-dir", required=True); ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows, ilan, eksik = ilanlar_oku(a.ham_dir, a.ciftler)
    gecti, n, dosya = Y.yedek(ilan, out, beklenen=BEKLENEN, baslik="YD 78 galeri yedegi (plan v3 adim 5)") if ilan else (0, 0, 0)
    if eksik:
        with open(out / "OZET.md", "a", encoding="utf-8") as f:
            f.writelines(f"| {lid} | {c} | 0 | FAIL | {neden} |\n" for lid, c, neden in eksik)
    with open(out / "BAGLAR.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "stil", "value_id", "image_id", "rank"])
        for k in ilan:
            rk = {x.get("listing_image_id"): x.get("rank") for x in k["gorseller"]}
            for b in k["baglar"]:
                w.writerow([k["listing_id"], k["cift"], b.get("value"), b.get("value_id"), b.get("image_id"), rk.get(b.get("image_id"), "")])
    print(f"YD YEDEK: ilan PASS {gecti}/{len(rows)} | dosya {dosya} (beklenen {BEKLENEN * len(rows)}) | HAM eksik {len(eksik)}")
    return 0 if gecti == len(rows) and not eksik else 1


if __name__ == "__main__":
    sys.exit(main())
