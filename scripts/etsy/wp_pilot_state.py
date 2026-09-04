#!/usr/bin/env python3
"""
PILOT DURUM OKUMASI (SALT OKUR) - 4 Eyl 2026.

Tek ilanin gercek durumunu Etsy'den okur ve olcum icin ilgili tum alanlari
yazar. HICBIR SEY DEGISTIRMEZ: yalniz GET; tek yazma OAuth token yenilemesidir
(TokenStore, Drive'a geri yazilir).

Amac: madde 11'de "state edit (beklenen active)" bulgusunun gercek karsiligini
saptamak. Mo pilotu taslaga aldigi icin beklenen deger artik "draft"tir;
"edit" ile "draft" ayni sey degildir, bu yuzden ham deger ve zaman damgalari
oldugu gibi raporlanir.

Kullanim:
  ETSY_API_KEY=... ETSY_SHARED_SECRET=... TOKEN_FILE=... \
  wp_pilot_state.py --listing-id 4565911475
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

# Durum ve "kaydedilmemis duzenleme" sorusunu ilgilendiren alanlar.
FIELDS = ["listing_id", "state", "state_timestamp", "creation_timestamp",
          "last_modified_timestamp", "updated_timestamp", "ending_timestamp",
          "original_creation_timestamp", "is_supply", "should_auto_renew",
          "has_variations", "quantity", "num_favorers", "featured_rank",
          "url", "title", "shop_section_id", "who_made", "when_made",
          "is_customizable", "is_personalizable", "listing_type"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    keystring = os.environ.get("ETSY_API_KEY", "")
    shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    lid = a.listing_id
    out = {}

    # 1) Magaza kapsaminda (satici gorunumu): taslak/edit durumlari burada gorunur.
    shop_view = api.get(f"/shops/{shop_id}/listings/{lid}", ok404=True) if shop_id else None
    # 2) Genel uc nokta (alici gorunumu): yayinda olmayan ilan 404 dondurur.
    public_view = api.get(f"/listings/{lid}", ok404=True)

    for label, obj in (("magaza_gorunumu", shop_view), ("genel_gorunum", public_view)):
        log(f"\n=== {label} ===")
        if obj is None:
            log("  404 - kayit donmedi (bu uc nokta bu ilan icin sonuc vermiyor)")
            out[label] = None
            continue
        d = {k: obj.get(k) for k in FIELDS if k in obj}
        out[label] = d
        for k, v in d.items():
            log(f"  {k}: {v}")
        eksik = [k for k in FIELDS if k not in obj]
        if eksik:
            log(f"  (yanitta olmayan alanlar: {', '.join(eksik)})")

    # 3) Medya sayimlari - "kaydedilmemis duzenleme" varsa neyin bekledigini gormek icin.
    for name, path in (("gorsel", f"/shops/{shop_id}/listings/{lid}/images"),
                       ("dosya", f"/shops/{shop_id}/listings/{lid}/files"),
                       ("video", f"/shops/{shop_id}/listings/{lid}/videos")):
        r = api.get(path, ok404=True) if shop_id else None
        n = len(r.get("results", [])) if isinstance(r, dict) else 0
        out[f"{name}_sayisi"] = n
        log(f"{name} sayisi: {n}")

    log(f"\nAPI cagrisi: {api.calls}, gunluk kalan: {api.remaining}")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        log(f"yazildi: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
