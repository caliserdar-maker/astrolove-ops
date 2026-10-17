#!/usr/bin/env python3
"""ESKI 78 POSTER: framed durumu SALT OKUMA taramasi (Serdar 17 Eki, ACIL adim 1). Etsy'ye yalniz GET; yazma metodu YOK.
Istek: toplu oku (1) + ilan basina envanter GET (78) = ~79.
Ilan basina: state, envanter urun sayisi, format menusu adi, framed urun sayisi (format degeri 4 cerceve degerinden biri),
  framed deger sayisi, aciklamada frame/framed/unframed/framing gecis sayisi, C yeni satiri var mi, kagit sozu (Hahnemuhle/
  Photo Rag/gsm/cotton/giclee) sayisi, materials.
Cikti (OUT): ESKI78_FRAME_TARA.csv + OZET.md; ozet satirlari ::warning:: (job logu proxy'de okunamiyor).
Kullanim: eski78_frame_tara.py --ids data/pod/pod78_ids.csv --out DIR"""
import argparse
import csv
import html
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
P_FORMAT = 514
CERCEVE = {"Antique Gold Frame", "Black Frame", "White Frame", "Natural Frame"}
FRAME = re.compile(r"\b(frames?|framed|unframed|framing)\b", re.I)
KAGIT = re.compile(r"hahnem|photo rag|\bgsm\b|cotton|gicl", re.I)
YENI_SATIR = "Frames shown in photos are for display only and are not included. Prints ship unframed."


class SaltOkur:
    """Etsy istemcisi: yalniz GET."""

    def __init__(self, api):
        self.api = api

    def get(self, *a, **k):
        r = self.api.get(*a, **k)
        try:
            if int(self.api.remaining) < KOTA_MIN:
                raise SystemExit(f"KOTA {self.api.remaining} < {KOTA_MIN}")
        except (TypeError, ValueError):
            pass
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="data/pod/pod78_ids.csv")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    ham = Etsy(store); api = SaltOkur(ham)
    rows = list(csv.DictReader(open(a.ids)))
    ids = [r["listing_id"].strip() for r in rows]
    L = {}
    for i in range(0, len(ids), 100):
        for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
            L[str(x["listing_id"])] = x
    tab, t0 = [], time.time()
    for i, r in enumerate(rows, 1):
        lid = r["listing_id"].strip(); x = L.get(lid) or {}
        d = html.unescape(x.get("description") or "")
        inv = api.get(f"/listings/{lid}/inventory") or {}
        prods = inv.get("products") or []
        fmt, adlar = [], set()
        for p in prods:
            for v in p.get("property_values") or []:
                if v.get("property_id") == P_FORMAT:
                    fmt.append((v.get("values") or [""])[0]); adlar.add(v.get("property_name"))
        fr = [f for f in fmt if f in CERCEVE]
        tab.append(dict(cift=r["cift"], listing_id=lid, state=x.get("state"), urun=len(prods), format_menu="|".join(sorted(a_ for a_ in adlar if a_)),
                        framed_urun=len(fr), framed_deger=len(set(fr)), aciklama_frame=len(FRAME.findall(d)),
                        yeni_satir=YENI_SATIR in d, kagit_sozu=len(KAGIT.findall(d)), materials=";".join(x.get("materials") or [])))
        if i % 10 == 0 or i == len(rows):
            g = time.time() - t0
            print(f"[{i}/{len(rows)}] %{i * 100 // len(rows)} gecen {g:.0f}s kalan ~{g / i * (len(rows) - i):.0f}s kota {ham.remaining}", flush=True)
    alan = list(tab[0])
    with open(out / "ESKI78_FRAME_TARA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(tab)
    md = ["| " + " | ".join(alan) + " |", "|" + "---|" * len(alan)] + ["| " + " | ".join(str(t[c]) for c in alan) + " |" for t in tab]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    from collections import Counter
    oz = lambda c: dict(Counter(str(t[c]) for t in tab))  # noqa: E731
    for c in ("state", "urun", "format_menu", "framed_urun", "framed_deger", "aciklama_frame", "yeni_satir", "kagit_sozu", "materials"):
        print(f"::warning::{c}: {oz(c)}")
    sap = [t for t in tab if t["framed_urun"] == 0 or t["yeni_satir"] or t["urun"] != 390]
    print(f"::warning::sapan ilan ({len(sap)}): " + "; ".join(f"{t['cift']} urun {t['urun']} framed {t['framed_urun']} frame_soz {t['aciklama_frame']}" for t in sap)[:900])
    aries = next((t for t in tab if t["listing_id"] == "4570031205"), None)
    print(f"::warning::4570031205: {aries}")
    print(f"::warning::BITTI | istek {ham.calls} | kota {ham.remaining}")


if __name__ == "__main__":
    main()
