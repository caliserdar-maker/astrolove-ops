#!/usr/bin/env python3
"""
Iki denetim CSV'sini 78 satirlik TEK tabloda birlestirir (11 madde).

  1-6   Drive tabanli  (wp_audit_drive.py --out)   : c1..c6
  7-11  Etsy GET       (wp_audit_full.py --out)    : c5_title..c9_meta

Madde numaralari Mo'nun 4 Eyl 2026 kapsam listesine gore sabittir.
VIDEO MADDELERI KAPSAM DISI (ayni karar): drive denetimi --no-video ile,
Etsy denetimi --skip-media ile kosar; bu yuzden c2/c3/c4'un video kismi ve
Etsy tarafinin c1-c4'u olculmez.

Deger sozlugu: PASS / FAIL / NA (olculmedi ya da kapsam disi).
Genel hukum: hicbir madde FAIL degilse PASS.

Kullanim:
  wp_audit_merge.py --drive AUDIT_DRIVE.csv --etsy AUDIT_FULL.csv --out AUDIT_11.csv
"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wp_mockup_common import log  # noqa: E402

# (cikti kolonu, kaynak dosya, kaynak kolon)
ITEMS = [
    ("m01_wallpaper_ocr", "drive", "c1_wp_sample"),
    ("m02_galeri_imza", "drive", "c2_pair_match"),
    ("m03_kalinti_metin", "drive", "c3_text"),
    ("m04_oran_sikisma", "drive", "c4_aspect"),
    ("m05_zip", "drive", "c5_zip"),
    ("m06_saglamlik", "drive", "c6_integrity"),
    ("m07_baslik_en", "etsy", "c5_title"),
    ("m08_etiket_en", "etsy", "c6_tags"),
    ("m09_aciklama_en", "etsy", "c7_desc"),
    ("m10_ru", "etsy", "c8_ru"),
    ("m11_meta", "etsy", "c9_meta"),
]


def read_csv(path):
    if not path or not Path(path).exists():
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["pair"]: r for r in csv.DictReader(fh)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", default="", help="wp_audit_drive.py ciktisi (1-6)")
    ap.add_argument("--etsy", default="", help="wp_audit_full.py ciktisi (7-11)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    src = {"drive": read_csv(a.drive), "etsy": read_csv(a.etsy)}
    log(f"drive denetimi {len(src['drive'])} satir, etsy denetimi {len(src['etsy'])} satir")
    pairs = sorted(set(src["drive"]) | set(src["etsy"]))
    if not pairs:
        raise SystemExit("HATA: iki CSV de bos/okunamadi")

    cols = ["pair", "listing_id"] + [c for c, _, _ in ITEMS] + ["overall", "detail"]
    rows = []
    for pair in pairs:
        row = {"pair": pair, "listing_id": src["etsy"].get(pair, {}).get("listing_id", "")}
        for out_col, which, in_col in ITEMS:
            # Kaynak satir yoksa "NA": olculmedi demektir, FAIL demek DEGIL.
            row[out_col] = (src[which].get(pair) or {}).get(in_col, "NA") or "NA"
        row["overall"] = "FAIL" if any(row[c] == "FAIL" for c, _, _ in ITEMS) else "PASS"
        det = [(src[w].get(pair) or {}).get("detail", "") for w in ("drive", "etsy")]
        row["detail"] = "; ".join(d for d in det if d)
        rows.append(row)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])

    n_fail = sum(1 for r in rows if r["overall"] == "FAIL")
    log(f"SONUC 11 maddelik denetim: {len(rows) - n_fail}/{len(rows)} PASS")
    lines = [f"## kapsamli denetim (11 madde, video kapsam disi): "
             f"{len(rows) - n_fail}/{len(rows)} PASS", ""]
    lines.append("| madde | PASS | FAIL | NA |")
    lines.append("|---|---|---|---|")
    for out_col, _, _ in ITEMS:
        c = {v: sum(1 for r in rows if r[out_col] == v) for v in ("PASS", "FAIL", "NA")}
        log(f"  {out_col}: {c['PASS']} PASS / {c['FAIL']} FAIL / {c['NA']} NA")
        lines.append(f"| {out_col} | {c['PASS']} | {c['FAIL']} | {c['NA']} |")
    if n_fail:
        lines += ["", "### FAIL olan ciftler", "", "| pair | " + " | ".join(c for c, _, _ in ITEMS) + " | detail |",
                  "|" + "---|" * (len(ITEMS) + 2)]
        for r in rows:
            if r["overall"] == "FAIL":
                lines.append("| " + r["pair"] + " | " + " | ".join(r[c] for c, _, _ in ITEMS)
                             + f" | {r['detail'][:300]} |")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
