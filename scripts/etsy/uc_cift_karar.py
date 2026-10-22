#!/usr/bin/env python3
"""uc-cift-yukle karar/rapor yardimcisi (Serdar genel onayi 28 Eyl: AQUARIUS_LIBRA, ARIES_LIBRA, CAPRICORN_LIBRA
kapak + video; kuru kosu PASS ise otomatik apply). Etsy'ye dokunmaz; yalniz PLAN.json okur.

  uc_cift_karar.py kapak PLAN.json      -> stdout: APPLY <haric listing_id'ler> | ATLA | FAIL <neden>
      APPLY: hedef 3 ilan PLAN/ZATEN, planda hic BLOK yok (kapak_yukle_78 apply BLOK'lu plani reddeder), en az bir PLAN.
      AQUARIUS_LIBRA / CAPRICORN_LIBRA ZATEN beklenmez (eski v9 kapak hatali olurdu) -> FAIL.
  uc_cift_karar.py video PLAN.json      -> stdout: APPLY | FAIL <neden>   (3 satir, hepsi YUKLE/DEGISTIR)
  uc_cift_karar.py haric-cift           -> stdout: hedef disi 75 cift (virgullu; video_yukle_78 --haric)
  uc_cift_karar.py rapor OUT            -> OUT/report.md (kapak + video: YUKLENDI / ATLANDI / FAIL)
"""
import csv
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
HEDEF = ("AQUARIUS_LIBRA", "ARIES_LIBRA", "CAPRICORN_LIBRA")
ZATEN_OLMAZ = ("AQUARIUS_LIBRA", "CAPRICORN_LIBRA")


def ilanlar():
    return list(csv.DictReader(open(KOK / "data/pod/pod78_ids.csv", encoding="utf-8")))


def kapak(plan):
    rows = json.loads(Path(plan).read_text(encoding="utf-8"))["satirlar"]
    hedef = {r["cift"]: r for r in rows if r["cift"] in HEDEF}
    if len(hedef) != 3:
        return f"FAIL planda hedef {len(hedef)}/3"
    blok = [f"{r['cift']}: {r['neden']}" for r in rows if r["durum"] == "BLOK"]
    if blok:
        return "FAIL planda BLOK var (apply reddeder): " + " | ".join(blok)[:400]
    zaten = [c for c in ZATEN_OLMAZ if hedef[c]["durum"] == "ZATEN"]
    if zaten:
        return "FAIL beklenmeyen ZATEN (canli 1. sira zaten v9 alt metni/boyutu): " + ", ".join(zaten)
    if not any(r["durum"] == "PLAN" for r in hedef.values()):
        return "ATLA"
    haric = sorted(str(r["listing_id"]) for r in rows if r["cift"] not in HEDEF)
    return "APPLY " + ",".join(haric)


def video(plan):
    rows = json.loads(Path(plan).read_text(encoding="utf-8"))["satirlar"]
    if sorted(r["cift"] for r in rows) != sorted(HEDEF):
        return f"FAIL plan ciftleri {sorted(r['cift'] for r in rows)}"
    kotu = [f"{r['cift']}: {r['durum']} {r['neden']}" for r in rows if r["durum"] not in ("YUKLE", "DEGISTIR")]
    return ("FAIL " + " | ".join(kotu)) if kotu else "APPLY"


def rapor(out):
    out = Path(out)
    sat = ["# UC CIFT YUKLEME (AQUARIUS_LIBRA, ARIES_LIBRA, CAPRICORN_LIBRA)", ""]
    karar = {k: (out / f"{k}_karar.txt").read_text().strip() if (out / f"{k}_karar.txt").exists() else "kosmadi"
             for k in ("kapak", "video")}
    kapak_son = out / "kapak_apply" / "SONUC.json"
    ks = {}
    if kapak_son.exists():
        j = json.loads(kapak_son.read_text())
        for r in (j if isinstance(j, list) else j.get("sonuc", [])):   # 2. tur kaydi sonradir, son kayit gecerli
            ks[r.get("cift")] = r.get("sonuc")
    kplan = out / "kapak_kuru" / "PLAN.json"
    kp = {r["cift"]: r["durum"] for r in json.loads(kplan.read_text())["satirlar"]} if kplan.exists() else {}
    vson = out / "video_apply" / "SONUC.json"
    vs = {r["cift"]: r for r in json.loads(vson.read_text())["sonuc"]} if vson.exists() else {}
    sat += [f"- Kapak karari: {karar['kapak'][:300]}", f"- Video karari: {karar['video'][:300]}", "",
            "| cift | kapak | video |", "|---|---|---|"]
    for c in HEDEF:
        k = ks.get(c) or ("ZATEN (1. sirada dogru v9)" if kp.get(c) == "ZATEN" else "ATLANDI" if not karar["kapak"].startswith("FAIL") else "FAIL")
        k = {"PASS": "YUKLENDI"}.get(k, k)
        v = vs.get(c, {}).get("sonuc") or ("ATLANDI" if not karar["video"].startswith("FAIL") else "FAIL")
        sat.append(f"| {c} | {k} | {v} |")
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    print("\n".join(sat))


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "kapak":
        print(kapak(sys.argv[2]))
    elif m == "video":
        print(video(sys.argv[2]))
    elif m == "haric-cift":
        print(",".join(s["cift"] for s in ilanlar() if s["cift"] not in HEDEF))
    elif m == "rapor":
        rapor(sys.argv[2])
    else:
        raise SystemExit(__doc__)
