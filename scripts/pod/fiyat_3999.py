#!/usr/bin/env python3
"""GOREV 0035 md.1 (Serdar dogrudan onayi, 26 Eyl 2026): 78 POD ilaninda 8x10 34.99 -> 39.99, A4 37.99 -> 39.99, 5 renk.
Ilan basina fiyat_b.py: tek updateListingInventory (fiyat disi alan AYNEN), geri okuma, renk-gorsel onarimi.
updateListing CAGRILMAZ. Aktif olmayan ilana dokunulmaz. Musteriye bildirim gitmez.
Modlar:
  kuru : 78 ilan fiyat_b oku -> out/FIYAT_3999_DIFF.csv (ilan, renk, boy, eski, yeni). Izinli 780 hucre (8x10 34.99->39.99,
         A4 37.99->39.99) disinda degisim ya da kapi hatasi -> FAIL (DUR). Aciklama/kisisellestirmede fiyat metni YALNIZ listelenir.
  tek  : --ilan ile tek ilan canli yaz + geri oku.
  hepsi: 78 ilan; active degil -> ATLANDI_STATE, zaten hedefte -> ZATEN, ilk FAIL'de DUR. Kota tabani 400. ETA sayaci.
Kullanim: fiyat_3999.py <kuru|tek|hepsi> <ilan_csv> [--ilan ID]"""
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
FB = os.environ.get("FIYAT_B_SCRIPT") or str(KOK / "fiyat_b.py")     # test icin degistirilebilir
REF_ID = "4570143815"
IZINLI = {"8x10": (34.99, 39.99), "A4": (37.99, 39.99)}
OUT = Path("out")
METIN_FIYAT = re.compile(r"(?:\$|USD\s?)\s?\d{1,3}(?:\.\d{2})?|\b(?:34|37|39)\.99\b")


def ilanlar(path):
    ids = [str(r.get("ilan_id") or r.get("listing_id") or "").strip() for r in csv.DictReader(open(path, encoding="utf-8-sig"))]
    ids = list(dict.fromkeys(x for x in ids + [REF_ID] if x))
    if len(ids) != 78:
        raise SystemExit(f"HATA: ilan sayisi {len(ids)} != 78. DUR.")
    return ids


def fb(mod, lid, *ek):
    d = OUT / "fb" / lid
    cmd = [sys.executable, FB, mod, "--listing", lid, "--out", str(d), "--izinli-boy", ",".join(IZINLI), "--yalniz-active"] + list(ek)
    r = subprocess.run(cmd, capture_output=True, text=True)
    son = [x for x in (r.stdout + r.stderr).strip().splitlines() if x.strip()][-1:] or [""]
    return r.returncode, d, son[0]


def eta(i, n, t0, ek):
    g = time.time() - t0
    print(f"[{i}/{n}] {100 * i // n}% gecen {g:.0f}s kalan ~{g / i * (n - i):.0f}s | {ek}", flush=True)


def kuru(ids):
    diff, kapi, metin, state, t0 = [], [], [], {}, time.time()
    for i, lid in enumerate(ids, 1):
        rc, d, son = fb("oku", lid)
        lp = d / "YEDEK" / f"{lid}_listing_ONCE.json"
        L = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
        state[lid] = L.get("state")
        for alan in ("description", "personalization_instructions"):
            for m in METIN_FIYAT.finditer(L.get(alan) or ""):
                metin.append({"ilan": lid, "alan": alan, "parca": m.group(0)})
        cp = d / "FIYAT_B_OKU.csv"
        for r in (csv.DictReader(open(cp, encoding="utf-8")) if cp.exists() else []):
            if r["hedef_fiyat"] == "" or abs(float(r["eski_fiyat"]) - float(r["hedef_fiyat"])) >= 0.005:
                diff.append({"ilan": lid, "renk": r["renk"], "boy": r["anahtar"], "eski": float(r["eski_fiyat"]),
                             "yeni": float(r["hedef_fiyat"]) if r["hedef_fiyat"] else None})
        if rc != 0 or not cp.exists():
            kapi.append({"ilan": lid, "rc": rc, "son": son[:200]})
        eta(i, len(ids), t0, f"ilan {lid} state={state[lid]} rc={rc}")
    disari = [x for x in diff if IZINLI.get(x["boy"]) != (x["eski"], x["yeni"])]
    with open(OUT / "FIYAT_3999_DIFF.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ilan", "renk", "boy", "eski", "yeni"]); w.writeheader(); w.writerows(diff)
    ozet = {"ilan": len(ids), "diff_satir": len(diff), "beklenen_en_fazla": 780, "izinli_disi_n": len(disari),
            "izinli_disi": disari[:20], "kapi": kapi, "active_degil": {k: v for k, v in state.items() if v != "active"},
            "metin_fiyat_n": len(metin), "metin_fiyat": metin}
    ozet["durum"] = "PASS" if not disari and not kapi and len(diff) <= 780 else "FAIL"
    return ozet


def yaz(ids):
    sonuc, t0 = {}, time.time()
    for i, lid in enumerate(ids, 1):
        rc, _, son = fb("yaz", lid, "--confirm", "FIYAT_B", "--kota-alt", "400")
        sonuc[lid] = {0: "PASS", 3: "ATLANDI_STATE", 4: "ZATEN"}.get(rc, f"FAIL rc={rc}: {son[:200]}")
        eta(i, len(ids), t0, f"ilan {lid} {sonuc[lid]}")
        if sonuc[lid].startswith("FAIL"):
            break
    n = {k: sum(1 for v in sonuc.values() if v.startswith(k)) for k in ("PASS", "ZATEN", "ATLANDI", "FAIL")}
    return {"sonuc": sonuc, "sayim": n, "islenen": len(sonuc), "toplam": len(ids),
            "durum": "PASS" if not n["FAIL"] and len(sonuc) == len(ids) else "FAIL"}


def main():
    mod, ids = sys.argv[1], ilanlar(sys.argv[2])
    OUT.mkdir(exist_ok=True)
    if mod == "kuru":
        ozet = kuru(ids)
    elif mod == "tek":
        lid = sys.argv[sys.argv.index("--ilan") + 1]
        if lid not in ids:
            raise SystemExit(f"HATA: {lid} 78 listede yok. DUR.")
        ozet = yaz([lid])
    elif mod == "hepsi":
        ozet = yaz(ids)
    else:
        raise SystemExit(f"HATA: bilinmeyen mod {mod}")
    (OUT / f"FIYAT_3999_{mod.upper()}.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    print("OZET " + json.dumps({k: v for k, v in ozet.items() if k not in ("sonuc", "metin_fiyat")}, ensure_ascii=False)[:1500], flush=True)
    sys.exit(0 if ozet["durum"] == "PASS" else 1)


if __name__ == "__main__":
    main()
