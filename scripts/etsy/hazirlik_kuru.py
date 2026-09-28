#!/usr/bin/env python3
"""HAZIRLIK SURESI KURU KOSU (SALT OKUMA, Etsy'ye yazma YOK) - 28 Eyl 2026.

1 Magazadaki hazirlik tanimlari (readiness-state-definitions): id, tur, min/max, birim.
2 Magazadaki TUM ilanlar (active/inactive/draft/expired/sold_out): tur (physical/download), state,
  processing_min/max; fiziksel ilanlarda envanter teklif(offering) readiness_state_id'leri -> tanim basina bagli ilanlar.
3 OAS: readiness uclari (guncelleme ucu var mi, govde alanlari).
4 Metin taramasi: canli 78 POD ilan aciklamasi + RU ceviri icinde sure vaadi (gun/saat ifadeleri).
Cikti: <out>/HAZIRLIK_KURU.md + HAZIRLIK_ILANLAR.csv. Kullanim: hazirlik_kuru.py --out OUT [--oas oas.json]
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
STATES = ["active", "inactive", "draft", "expired", "sold_out"]
SURE_RX = re.compile(r"(?i)(\b\d+\s*(?:-|–|to)\s*\d+\s*(?:business\s+|working\s+)?(?:days?|hours?)\b|"
                     r"\bwithin\s+\d+\s*(?:business\s+|working\s+)?(?:days?|hours?)\b|"
                     r"\b\d+\s*(?:business|working)\s+days?\b|\d+\s*[-–]?\s*\d*\s*(?:рабоч\w*\s+)?(?:дн\w*|час\w*))")


def tum_ilanlar(api, shop):
    out = {}
    for st in STATES:
        off = 0
        while True:
            r = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100, "offset": off}, ok404=True) or {}
            rs = r.get("results") or []
            for x in rs:
                out[str(x["listing_id"])] = x
            off += len(rs)
            if len(rs) < 100 or off >= (r.get("count") or 0):
                break
    return out


def calis(api, shop, out, oas=""):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tan = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    log(f"hazirlik tanimi: {len(tan)} | kota {api.remaining}")
    L = tum_ilanlar(api, shop)
    pod = {r["listing_id"] for r in csv.DictReader(open(KOK / "data/pod/pod78_ids.csv", encoding="utf-8"))}
    log(f"magazadaki ilan: {len(L)} ({dict(Counter(x.get('state') for x in L.values()))}) | kota {api.remaining}")
    satir, bag = [], defaultdict(list)
    fiziksel = [lid for lid, x in L.items() if (x.get("listing_type") or x.get("type")) != "download"]
    for n, lid in enumerate(fiziksel, 1):
        inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
        ids = sorted({o.get("readiness_state_id") for p in inv.get("products") or [] for o in p.get("offerings") or []
                      if not o.get("is_deleted")} - {None})
        x = L[lid]
        for i in ids or [None]:
            bag[i].append((lid, x.get("state"), lid in pod))
        satir.append({"listing_id": lid, "pod78": lid in pod, "state": x.get("state"), "tur": x.get("listing_type") or x.get("type"),
                      "processing": f"{x.get('processing_min')}-{x.get('processing_max')}", "readiness_ids": " ".join(map(str, ids))})
        if n % 20 == 0:
            log(f"[{n}/{len(fiziksel)}] envanter okundu | kota {api.remaining}")
    for lid, x in L.items():
        if lid not in fiziksel:
            satir.append({"listing_id": lid, "pod78": lid in pod, "state": x.get("state"), "tur": x.get("listing_type") or x.get("type"),
                          "processing": f"{x.get('processing_min')}-{x.get('processing_max')}", "readiness_ids": ""})
    with open(out / "HAZIRLIK_ILANLAR.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(satir[0])); w.writeheader(); w.writerows(satir)
    # metin taramasi (78 POD, canli)
    bul = Counter()
    ornek = {}
    for lid in sorted(pod):
        x = L.get(lid) or api.get(f"/listings/{lid}") or {}
        for m in SURE_RX.finditer(x.get("description") or ""):
            s = x["description"][max(0, m.start() - 60):m.end() + 40].replace("\n", " ")
            bul[("EN", m.group(0).lower())] += 1; ornek.setdefault(("EN", m.group(0).lower()), s)
    ru = api.get(f"/shops/{shop}/listings/4570143815/translations/ru", ok404=True) or {}
    for m in SURE_RX.finditer(ru.get("description") or ""):
        s = ru["description"][max(0, m.start() - 60):m.end() + 40].replace("\n", " ")
        bul[("RU (CL)", m.group(0).lower())] += 1; ornek.setdefault(("RU (CL)", m.group(0).lower()), s)
    # OAS
    oas_satir = []
    if oas and Path(oas).exists():
        d = json.loads(Path(oas).read_text())
        for p, ops in d["paths"].items():
            if "readiness" in p:
                for m, op in ops.items():
                    alan = []
                    for ct, c in (op.get("requestBody") or {}).get("content", {}).items():
                        sc = c["schema"]
                        if "$ref" in sc:
                            node = d
                            for k in sc["$ref"].lstrip("#/").split("/"):
                                node = node[k]
                            sc = node
                        alan = sorted(sc.get("properties") or {})
                    oas_satir.append(f"{m.upper()} {p} ({op.get('operationId')}) govde: {alan}")
    md = [f"# HAZIRLIK SURESI KURU KOSU ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}) - Etsy'ye yazma YOK", "",
          "## Hazirlik tanimlari ve bagli ilanlar", "", "| readiness_state_id | tur | min-max | birim | bagli ilan (toplam) | POD78 | diger (state) |",
          "|---|---|---|---|---|---|---|"]
    for t in tan:
        i = t.get("readiness_state_id")
        b = bag.get(i, [])
        diger = Counter(s for _, s, p in b if not p)
        md.append(f"| {i} | {t.get('readiness_state')} | {t.get('min_processing_time', t.get('min_processing_days'))}-"
                  f"{t.get('max_processing_time', t.get('max_processing_days'))} | {t.get('processing_time_unit', '')} | {len(b)} | "
                  f"{sum(p for _, _, p in b)} | {dict(diger) or '-'} |")
    if bag.get(None):
        md.append(f"| (tanimsiz) | | | | {len(bag[None])} | {sum(p for _, _, p in bag[None])} | {dict(Counter(s for _, s, p in bag[None] if not p))} |")
    md += ["", f"- Magazadaki ilan: {len(L)} | fiziksel {len(fiziksel)} | dijital {len(L) - len(fiziksel)} "
           f"(dijital ilanlarda hazirlik tanimi yok) | durum: {dict(Counter(x.get('state') for x in L.values()))}",
           f"- processing (ilan alanlari, POD78): {dict(Counter(s['processing'] for s in satir if s['pod78']))}", "",
           "## OAS readiness uclari", ""] + [f"- {s}" for s in oas_satir or ["(OAS okunamadi)"]]
    md += ["", "## Canli metinde sure ifadeleri (78 POD aciklama + CL RU)", "", "| dil | ifade | adet | ornek |", "|---|---|---|---|"]
    md += [f"| {k[0]} | {k[1]} | {v} | {ornek[k][:120]} |" for k, v in bul.most_common()]
    md += ["", f"- Kota son: {api.remaining} | API cagrisi: {api.calls}"]
    (out / "HAZIRLIK_KURU.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--oas", default="")
    a = ap.parse_args()
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    calis(Etsy(st), os.environ["ETSY_SHOP_ID"], a.out, a.oas)


if __name__ == "__main__":
    main()
