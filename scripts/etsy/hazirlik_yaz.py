#!/usr/bin/env python3
"""Hazirlik suresi uygulamasi (Serdar genel onayi 28 Eyl 2026; Yol A). ETSY'YE YAZAR (--mod yaz + --confirm HAZIRLIK).

1) readiness_state_definition 1517641240112 (yalniz 78 POD'a bagli; HAZIRLIK_KURU 28 Eyl) -> min 4, max 7.
   Once tanim yedegi, PUT, geri okuma (min/max/tur/birim).
2) 78 POD aciklamasi: "within 5 business days" -> "within 7 business days" (tam 1 kez; RU'da karsilik yok).
   Ilan basina: canli okuma -> yedek (tam aciklama) -> state 'active' degilse DOKUNULMAZ (updateListing taslagi
   yayina alir) -> PATCH yalniz description -> geri okuma: aciklama beklenen, baslik/etiket/state ayni.
   Ifade yoksa ve yeni ifade zaten varsa: ZATEN (yazma yok).
Ilk FAIL'de DUR (sonraki ilanlara gecilmez). Kota tabani altinda temiz DUR; ILERLEME.json ile kaldigi yerden devam.
Cikti: <out>/YEDEK/ (tanim + ilan aciklamalari; yazmadan ONCE), <out>/ILERLEME.json, <out>/RAPOR.md
Kullanim: hazirlik_yaz.py --mod yedek|yaz --out OUT [--ilerleme ONCEKI.json] [--confirm HAZIRLIK] [--yalniz id,id]
"""
import argparse
import csv
import html
import json
import os
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy"))

READINESS_ID = 1517641240112
HEDEF_MIN, HEDEF_MAX = 4, 7
ESKI, YENI = "within 5 business days", "within 7 business days"
KOTA_TABAN = 150
BEKLE, TEKRAR = 4, 4


def log(m):
    print(m, flush=True)


def normalize(t):
    t = html.unescape(t or "").replace("\r\n", "\n")
    return "\n".join(s.rstrip() for s in t.split("\n")).strip()


def kararli(fn, kosul):
    son = None
    for _ in range(TEKRAR):
        time.sleep(BEKLE)
        son = fn()
        if kosul(son):
            return son
    return son


def kota(api):
    r = api.remaining
    return int(r) if r is not None and str(r).isdigit() else None


def tanim_oku(api, shop):
    return api.get(f"/shops/{shop}/readiness-state-definitions/{READINESS_ID}") or {}


def tanim_ok(t):
    return int(t.get("min_processing_time") or -1) == HEDEF_MIN and int(t.get("max_processing_time") or -1) == HEDEF_MAX


def readiness_yaz(api, shop, out, R):
    t0 = tanim_oku(api, shop)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    (out / "YEDEK" / f"readiness_{READINESS_ID}.json").write_text(json.dumps(t0, indent=1))
    if tanim_ok(t0):
        R["readiness"] = "ZATEN"; log(f"readiness {READINESS_ID}: zaten {HEDEF_MIN}-{HEDEF_MAX}"); return
    govde = {"readiness_state": t0.get("readiness_state") or "made_to_order",
             "min_processing_time": HEDEF_MIN, "max_processing_time": HEDEF_MAX}
    if t0.get("processing_time_unit"):
        govde["processing_time_unit"] = t0["processing_time_unit"]
    api.put(f"/shops/{shop}/readiness-state-definitions/{READINESS_ID}", govde)
    t1 = kararli(lambda: tanim_oku(api, shop), tanim_ok)
    (out / "SONRA").mkdir(parents=True, exist_ok=True)
    (out / "SONRA" / f"readiness_{READINESS_ID}.json").write_text(json.dumps(t1, indent=1))
    sorun = [] if tanim_ok(t1) else [f"min/max {t1.get('min_processing_time')}-{t1.get('max_processing_time')}"]
    sorun += [f"degisti:{k}" for k in ("readiness_state", "processing_time_unit") if t1.get(k) != t0.get(k)]
    if sorun:
        R["readiness"] = f"FAIL {sorun}"
        raise SystemExit(f"HATA: readiness geri okuma FAIL: {sorun}. DUR.")
    R["readiness"] = "YAZILDI"
    log(f"readiness {READINESS_ID}: {t0.get('min_processing_time')}-{t0.get('max_processing_time')} -> {HEDEF_MIN}-{HEDEF_MAX} (geri okuma PASS)")


def imza(L):
    return {"title": L.get("title"), "tags": L.get("tags"), "state": L.get("state")}


def ilan_yaz(api, shop, lid, out, yaz):
    L0 = api.get(f"/listings/{lid}") or {}
    d0 = normalize(L0.get("description"))
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    (out / "YEDEK" / f"{lid}.json").write_text(json.dumps({"listing_id": lid, "state": L0.get("state"), "title": L0.get("title"),
                                                            "tags": L0.get("tags"), "description": L0.get("description")},
                                                           ensure_ascii=False, indent=1))
    n = d0.count(ESKI)
    if n == 0 and YENI in d0:
        return "ZATEN", "yeni ifade zaten var"
    if n != 1:
        return "FAIL", f"'{ESKI}' {n} kez (1 bekleniyordu)"
    if L0.get("state") != "active":
        return "ATLANDI", f"state={L0.get('state')} (active degil, dokunulmadi)"
    if not yaz:
        return "PLAN", "1 degisiklik"
    hedef = d0.replace(ESKI, YENI)
    api.patch(f"/shops/{shop}/listings/{lid}", {"description": hedef})
    L1 = kararli(lambda: api.get(f"/listings/{lid}") or {}, lambda L: normalize(L.get("description")) == hedef)
    sorun = [] if normalize(L1.get("description")) == hedef else ["aciklama"]
    s0, s1 = imza(L0), imza(L1)
    sorun += [f"degisti:{k}" for k in s0 if s0[k] != s1[k]]
    if sorun:
        return "FAIL", f"geri okuma: {sorun}"
    return "YAZILDI", "aciklama 5 -> 7 business days; baslik/etiket/state ayni"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["yedek", "yaz"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--ilerleme", default="")
    ap.add_argument("--yalniz", default="")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--kota-taban", type=int, default=KOTA_TABAN)
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    if yaz and a.confirm != "HAZIRLIK":
        raise SystemExit("HATA: --mod yaz icin --confirm HAZIRLIK gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = json.loads(Path(a.ilerleme).read_text()) if a.ilerleme and Path(a.ilerleme).exists() else {}
    R.setdefault("ilanlar", {})
    rows = list(csv.DictReader(open(a.ids, encoding="utf-8")))
    if len(rows) != 78:
        raise SystemExit(f"HATA: 78 hedef bekleniyordu ({len(rows)}). DUR.")
    if a.yalniz:
        rows = [r for r in rows if r["listing_id"] in a.yalniz.split(",")]
    kalan = [r for r in rows if R["ilanlar"].get(r["listing_id"], {}).get("durum") not in ("YAZILDI", "ZATEN")]
    t0 = time.time(); durdu = ""

    def kaydet():
        (out / "ILERLEME.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))
    try:
        if yaz and R.get("readiness") not in ("YAZILDI", "ZATEN"):
            readiness_yaz(api, shop, out, R); kaydet()
        elif not yaz:
            t = tanim_oku(api, shop)
            (out / "YEDEK").mkdir(parents=True, exist_ok=True)
            (out / "YEDEK" / f"readiness_{READINESS_ID}.json").write_text(json.dumps(t, indent=1))
            R["readiness_plan"] = f"{t.get('min_processing_time')}-{t.get('max_processing_time')} -> {HEDEF_MIN}-{HEDEF_MAX}"
        for n, r in enumerate(kalan, 1):
            q = kota(api)
            if q is not None and q < a.kota_taban:
                durdu = f"kota {q} < {a.kota_taban}; {n - 1}/{len(kalan)} ilandan sonra (ILERLEME.json ile devam)"; break
            lid = r["listing_id"]
            durum, not_ = ilan_yaz(api, shop, lid, out, yaz)
            R["ilanlar"][lid] = {"cift": r["cift"], "durum": durum, "not": not_}
            kaydet()
            g = time.time() - t0
            log(f"[{n}/{len(kalan)} %{n * 100 // len(kalan)}] {lid} {r['cift']}: {durum} ({not_}) | gecen {g:.0f}s "
                f"kalan ~{g / n * (len(kalan) - n):.0f}s | kota {api.remaining}")
            if durum == "FAIL":
                durdu = f"ilk FAIL {lid} {r['cift']}: {not_}"; break
    finally:
        kaydet()
        say = {}
        for v in R["ilanlar"].values():
            say[v["durum"]] = say.get(v["durum"], 0) + 1
        md = [f"# HAZIRLIK UYGULAMA ({a.mod}) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", "",
              f"- readiness {READINESS_ID}: {R.get('readiness') or R.get('readiness_plan')}",
              f"- aciklama ('{ESKI}' -> '{YENI}'): {say} / 78", f"- durdu: {durdu or 'hayir'}",
              f"- API cagrisi {api.calls} | kota son {api.remaining}", "", "| listing_id | cift | durum | not |", "|---|---|---|---|"]
        md += [f"| {k} | {v['cift']} | {v['durum']} | {v['not']} |" for k, v in R["ilanlar"].items() if v["durum"] not in ("YAZILDI", "ZATEN", "PLAN")]
        (out / "RAPOR.md").write_text("\n".join(md) + "\n")
        log("\n".join(md[:6]))
    if durdu.startswith("ilk FAIL"):
        raise SystemExit(f"DUR: {durdu}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
