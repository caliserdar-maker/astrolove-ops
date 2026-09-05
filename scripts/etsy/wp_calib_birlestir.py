#!/usr/bin/env python3
"""
KALICILASTIRMA - calib birlestirme (5 Eyl 2026, Mo).

uretim calib.json + calib_set07.json (SET07/1 saat: quad + frame_top delik=quad)
+ calib_kasa.json (SET03/3, SET04/1: frame_top delik=maske) -> yeni calib.json.
Diger 11 ekranin (SET01 x2, SET03 0-2, SET04/0, SET06 x3, SET07/0, SET10Y/0)
quad/H/mode alanlari uretimle BIREBIR ayni olmali; degilse HATA.
"""
import argparse
import json
from pathlib import Path

DEGISEN = {("SET07", 1): "set07", ("SET03", 3): "kasa", ("SET04", 1): "kasa"}


def ekran(c, sahne, eid):
    return next(s for s in c["scenes"][sahne]["screens"] if int(s["id"]) == eid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uretim", required=True)
    ap.add_argument("--set07", required=True)
    ap.add_argument("--kasa", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    u = json.loads(Path(a.uretim).read_text())
    kay = {"set07": json.loads(Path(a.set07).read_text()), "kasa": json.loads(Path(a.kasa).read_text())}
    yeni = json.loads(json.dumps(u))
    n_ayni = 0
    for sahne, sc in u["scenes"].items():
        for s in sc["screens"]:
            eid = int(s["id"])
            k = DEGISEN.get((sahne, eid))
            if k is None:
                for kk, c in kay.items():
                    o = ekran(c, sahne, eid)
                    for alan in ("quad", "H", "mode", "device", "edition"):
                        if json.dumps(o.get(alan)) != json.dumps(s.get(alan)):
                            raise SystemExit(f"HATA: {sahne}/{eid} {alan} {kk} kaynaginda uretimden farkli")
                    if o.get("frame_top"):
                        raise SystemExit(f"HATA: {sahne}/{eid} {kk} kaynaginda beklenmeyen frame_top")
                n_ayni += 1
                continue
            o = ekran(kay[k], sahne, eid)
            if not o.get("frame_top"):
                raise SystemExit(f"HATA: {sahne}/{eid} {k} kaynaginda frame_top yok")
            h = ekran(yeni, sahne, eid)
            eski_q = h["quad"]
            h["quad"] = o["quad"]
            h["frame_top"] = o["frame_top"]
            print(f"{sahne}/{eid} <- {k}: quad {[[round(x, 1) for x in p] for p in eski_q]} -> "
                  f"{[[round(x, 1) for x in p] for p in o['quad']]} | frame_top {o['frame_top']}")
    if n_ayni != 11:
        raise SystemExit(f"HATA: degismeyen ekran sayisi {n_ayni} != 11")
    Path(a.out).write_text(json.dumps(yeni, indent=1))
    print(f"{a.out}: 3 ekran degisti, {n_ayni} ekran birebir ayni")


if __name__ == "__main__":
    main()
