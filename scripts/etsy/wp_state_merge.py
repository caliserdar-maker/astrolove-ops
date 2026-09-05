#!/usr/bin/env python3
"""WP_NIGHT_STATE parcalarini birlestir: (cift, asama) icin EN YENI ts_utc kazanir (5 Eyl 2026).
Onceki birlestirme dosya sirasina gore 'son okunan kazanir' idi; parca dosyalari eski
satirlarin kopyasini da tasidigi icin yeni kosunun satirlari kayboluyordu."""
import collections
import csv
import glob
import sys


def main(klasor, cikti):
    rows = {}
    for f in sorted(glob.glob(f"{klasor}/WP_NIGHT_STATE*.csv")):
        for r in csv.reader(open(f, encoding="utf-8")):
            if len(r) >= 5 and r[0] != "pair":
                k = (r[0], r[1])
                if k not in rows or r[3] > rows[k][3]:
                    rows[k] = r
    with open(cikti, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["pair", "stage", "status", "ts_utc", "detail"])
        for k in sorted(rows):
            w.writerow(rows[k])
    c = collections.Counter((r[1], r[2]) for r in rows.values())
    print("## gece STATE ozeti (en yeni ts kazanir)\n")
    for (stage, status), n in sorted(c.items()):
        print(f"- asama {stage}: {status} {n}")
    for stage in sorted({r[1] for r in rows.values()}):
        ts = sorted(r[3] for r in rows.values() if r[1] == stage)
        print(f"- asama {stage} ts araligi: {ts[0]} .. {ts[-1]}")
    fails = [r[0] for r in rows.values() if r[2] != "PASS"]
    if fails:
        print("\nFAIL ciftler: " + ", ".join(sorted(set(fails))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
