#!/usr/bin/env python3
"""Satilan urunlerin varyasyon dagilimi (SALT OKUMA) - Serdar, 27 Eyl 2026 (tek renk mi, 5 renk mi arastirmasi).

getShopReceipts (was_paid=true, son N fis, transactions dahil). Her islem icin: tur (dijital/fiziksel),
Primary color, Size, SKU ve fiyat; musteri adi/adresi/fis no OKUNMAZ, YAZILMAZ.
Cikti: out/VARYASYON_SATIS.md + .json (renk, boy, tur sayimlari + islem satirlari anonim).
Etsy'ye YAZMA YOK. Cagri: ceil(N/100)."""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

N = int(os.environ.get("ADET", "100"))
OUT = Path("out")


def main():
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    fisler, offset = [], 0
    while len(fisler) < N:
        d = api.get(f"/shops/{shop}/receipts", {"limit": min(100, N - len(fisler)), "offset": offset,
                                                 "was_paid": "true", "sort_on": "created", "sort_order": "desc"})
        r = d.get("results") or []
        fisler += r
        if len(r) < 100:
            break
        offset += 100
    satir = []
    for f in fisler:
        tarih = datetime.fromtimestamp(int(f["created_timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
        for t in f.get("transactions") or []:
            v = {str(x.get("formatted_name") or "").lower(): str(x.get("formatted_value") or "")
                 for x in t.get("variations") or []}
            renk = next((val for k, val in v.items() if "color" in k), "")
            boy = next((val for k, val in v.items() if "size" in k), "")
            fiyat = t.get("price") or {}
            satir.append({"tarih": tarih, "dijital": bool(t.get("is_digital")), "renk": renk, "boy": boy,
                          "sku": t.get("sku") or "", "baslik": (t.get("title") or "")[:60],
                          "fiyat": round(int(fiyat.get("amount") or 0) / int(fiyat.get("divisor") or 100), 2),
                          "ulke": f.get("country_iso") or ""})
    fiz = [s for s in satir if not s["dijital"]]
    ozet = {"islem": len(satir), "fis": len(fisler), "fiziksel": len(fiz), "dijital": len(satir) - len(fiz),
            "fiziksel_renk": Counter(s["renk"] or "-" for s in fiz), "fiziksel_boy": Counter(s["boy"] or "-" for s in fiz),
            "dijital_baslik_renk": Counter((s["baslik"].split(",")[0][:40]) for s in satir if s["dijital"])}
    OUT.mkdir(exist_ok=True)
    (OUT / "VARYASYON_SATIS.json").write_text(json.dumps({"ozet": ozet, "islemler": satir}, ensure_ascii=False, indent=1))
    md = [f"# Varyasyon satis dagilimi (salt okuma, {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
          f"Fis {ozet['fis']}, islem {ozet['islem']}: fiziksel {ozet['fiziksel']}, dijital {ozet['dijital']}", "",
          "## Fiziksel: renk", *[f"- {k}: {v}" for k, v in ozet["fiziksel_renk"].most_common()], "",
          "## Fiziksel: boy", *[f"- {k}: {v}" for k, v in ozet["fiziksel_boy"].most_common()], "",
          "## Islemler (anonim)", "| tarih | tur | renk | boy | sku | fiyat | ulke |", "|---|---|---|---|---|---|---|",
          *[f"| {s['tarih']} | {'dijital' if s['dijital'] else 'fiziksel'} | {s['renk']} | {s['boy']} | {s['sku']} | "
            f"{s['fiyat']} | {s['ulke']} |" for s in satir]]
    (OUT / "VARYASYON_SATIS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"fis {len(fisler)}, islem {len(satir)}; Etsy cagri {api.calls}, kota {api.remaining}")


if __name__ == "__main__":
    main()
