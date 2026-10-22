#!/usr/bin/env python3
"""78 wallpaper aciklamasinda yalniz uzun tireleri duz tireye cevirir.

Girdi Batch 4 onay CSV'sidir. Yazmadan once 78/78 canli aciklama CSV'deki
mevcut_metin ya da onerilen_metin ile birebir eslesmelidir; baska bir sapmada
hicbir sey yazmadan DURUR. Onerilen metinde olan ilan idempotent olarak atlanir.
Yazma yalniz --apply --confirm CANLI ile acilir. PATCH govdesi yalniz
description alanini icerir. Her yazmadan sonra ve kosu sonunda geri okuma
yapilir; title/tags ve korunan alanlarin degismedigi kanitlanir.
"""
import argparse
import csv
import html
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
import pod_desc_set as DS  # noqa: E402

N = 78
LONG_DASH = "—–"
PROTECTED = ["title", "tags", "price", "state", "shop_section_id", "taxonomy_id",
             "shipping_profile_id", "return_policy_id", "materials", "who_made",
             "when_made", "is_supply", "has_variations", "should_auto_renew"]
COLS = ["listing_id", "pair", "status", "dash_before", "dash_after", "note"]


def norm(value):
    value = html.unescape(value or "").replace("\r\n", "\n")
    return "\n".join(x.rstrip() for x in value.split("\n")).strip()


def read_plan(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("tur") or "").strip() == "description"]
    ids = [(r.get("listing_id") or "").strip() for r in rows]
    if len(rows) != N or len(set(ids)) != N or not all(x.isdigit() for x in ids):
        raise SystemExit(f"HATA: plan {len(rows)} satir / {len(set(ids))} benzersiz id; beklenen 78/78. DUR.")
    for r in rows:
        old, new = r.get("mevcut_metin") or "", r.get("onerilen_metin") or ""
        expected = old.replace("—", "-").replace("–", "-")
        if new != expected:
            raise SystemExit(f"HATA: {r['listing_id']} onerisi yalniz uzun tire degisikligi degil. DUR.")
        if not any(c in old for c in LONG_DASH) or any(c in new for c in LONG_DASH):
            raise SystemExit(f"HATA: {r['listing_id']} uzun tire onkosulu gecmedi. DUR.")
        if (r.get("urun_ailesi") or "").strip() != "Digital wallpaper":
            raise SystemExit(f"HATA: {r['listing_id']} urun ailesi wallpaper degil. DUR.")
    return rows


def get_listing(api, lid):
    return api.get(f"/listings/{lid}", ok404=True) or {}


def batch_listings(api, ids):
    """78 ilani tek GET ile getir; eksik donenleri yalniz tek tek tamamla."""
    try:
        data = api.get("/listings/batch", params={"listing_ids": ",".join(ids)}) or {}
        found = {str(x.get("listing_id")): x for x in data.get("results") or [] if x.get("listing_id")}
    except SystemExit:
        found = {}
    for lid in ids:
        if lid not in found:
            found[lid] = get_listing(api, lid)
    return found


def media(api, shop, lid):
    return {
        "images": DS.galeri(api, lid),
        "variation_images": DS.var_img(api, shop, lid),
        "videos": DS.videolar(api, lid),
        "inventory": DS.envanter(api, lid),
    }


def protected_diff(before, after):
    return [k for k in PROTECTED if before.get(k) != after.get(k)]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-min", type=int, default=20,
                    help="Tahmini zorunlu cagrilar bittikten sonra kalacak guvenlik rezervi")
    args = ap.parse_args()
    if args.apply and args.confirm != "CANLI":
        raise SystemExit("HATA: --apply icin --confirm CANLI gerekli. DUR.")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    backups = out / "backups"; backups.mkdir(exist_ok=True)
    plan = read_plan(args.plan)

    key, secret = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(key); mask(secret)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    # Kapi 1: 78/78 canli durum eski ya da hedef metinle eslesmeden yazma yok.
    ids = [r["listing_id"].strip() for r in plan]
    live = batch_listings(api, ids)
    before, done_ids, pending = {}, set(), []
    for i, r in enumerate(plan, 1):
        lid = r["listing_id"].strip()
        L = live.get(lid) or {}
        if L.get("state") != "active":
            raise SystemExit(f"HATA: {lid} state={L.get('state')}; hicbir sey yazilmadi. DUR.")
        current = norm(L.get("description"))
        if current == norm(r.get("onerilen_metin")):
            done_ids.add(lid)
        elif current == norm(r.get("mevcut_metin")):
            if not any(c in (L.get("description") or "") for c in LONG_DASH):
                raise SystemExit(f"HATA: {lid} eski metinde uzun tire yok; hicbir sey yazilmadi. DUR.")
            pending.append(r)
        else:
            raise SystemExit(f"HATA: {lid} canli aciklama ne eski ne hedef metin; hicbir sey yazilmadi. DUR.")
        before[lid] = L
        (backups / f"{lid}.before.json").write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"On kontrol {N}/{N} | zaten hedef {len(done_ids)} | bekleyen {len(pending)} | kota {api.remaining}")

    if not args.apply:
        result = [{"listing_id": r["listing_id"], "pair": r.get("burc_cifti", ""),
                   "status": "ALREADY_PASS" if r["listing_id"] in done_ids else "READY",
                   "dash_before": sum((r.get("mevcut_metin") or "").count(c) for c in LONG_DASH),
                   "dash_after": 0, "note": "78/78 canli on kontrol gecti"} for r in plan]
        write_csv(out / "result.csv", result)
        return 0

    try:
        remaining = int(api.remaining) if api.remaining is not None else None
    except (TypeError, ValueError):
        remaining = None
    required = len(pending) * 2 + 1 + (8 if pending else 0) + args.quota_min
    if remaining is not None and remaining < required:
        raise SystemExit(f"HATA: kota {remaining}; guvenli devam icin gereken {required}. Hicbir yeni yazma yapilmadi. DUR.")

    first_pending = pending[0]["listing_id"].strip() if pending else None
    first_media_before = media(api, shop, first_pending) if first_pending else None
    result = [{"listing_id": r["listing_id"], "pair": r.get("burc_cifti", ""),
               "status": "ALREADY_PASS", "dash_before": sum((r.get("mevcut_metin") or "").count(c) for c in LONG_DASH),
               "dash_after": 0, "note": "onceki kosuda hedef metin dogrulandi"}
              for r in plan if r["listing_id"] in done_ids]
    write_csv(out / "result.csv", result)
    written_this_run = 0
    for i, r in enumerate(pending, 1):
        lid = r["listing_id"].strip()
        try:
            remaining = int(api.remaining) if api.remaining is not None else None
        except (TypeError, ValueError):
            remaining = None
        still_needed = (len(pending) - i + 1) * 2 + 1 + (4 if i == 1 else 0) + args.quota_min
        if remaining is not None and remaining < still_needed:
            raise SystemExit(f"HATA: kota {remaining}; kalan is icin gereken {still_needed}. "
                             f"Bu kosuda {written_this_run} yazildi. DUR.")
        new = r.get("onerilen_metin") or ""
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": new})
        after = {}
        for attempt in range(3):
            time.sleep(10)
            after = get_listing(api, lid)
            if norm(after.get("description")) == norm(new):
                break
        changed = protected_diff(before[lid], after)
        bad_dash = [c for c in LONG_DASH if c in (after.get("description") or "")]
        if norm(after.get("description")) != norm(new) or changed or bad_dash:
            (backups / f"{lid}.after_FAIL.json").write_text(json.dumps(after, ensure_ascii=False, indent=1), encoding="utf-8")
            raise SystemExit(f"HATA: {lid} geri okuma FAIL; protected={changed}, uzun_tire={bad_dash}. DUR.")
        if lid == first_pending:
            first_media_after = media(api, shop, lid)
            if first_media_after != first_media_before:
                raise SystemExit(f"HATA: {lid} ilk ilan medya/envanter degisti. DUR.")
        (backups / f"{lid}.after.json").write_text(json.dumps(after, ensure_ascii=False, indent=1), encoding="utf-8")
        result.append({"listing_id": lid, "pair": r.get("burc_cifti", ""), "status": "PASS",
                       "dash_before": sum((r.get("mevcut_metin") or "").count(c) for c in LONG_DASH),
                       "dash_after": sum((after.get("description") or "").count(c) for c in LONG_DASH),
                       "note": "yalniz description; korunan alanlar ayni"})
        write_csv(out / "result.csv", result)
        written_this_run += 1
        log(f"[{len(done_ids)+i}/{N}] {lid} PASS | kota {api.remaining}")

    # Kapi 2: kosu sonunda 78/78 tek batch GET ile yeniden oku.
    final_live = batch_listings(api, ids)
    final_fail = []
    for r in plan:
        lid = r["listing_id"].strip(); L = final_live.get(lid) or {}
        if norm(L.get("description")) != norm(r.get("onerilen_metin")) or protected_diff(before[lid], L):
            final_fail.append(lid)
    summary = {"target": N, "written_this_run": written_this_run, "already_pass": len(done_ids),
               "pass": N - len(final_fail),
               "final_fail": final_fail, "fields_written": ["description"],
               "protected_fields_unchanged": not final_fail, "quota_remaining": api.remaining}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(
        "# Wallpaper aciklama uygulamasi\n\n"
        f"- Hedef: {N}\n- Bu kosuda yazilan: {written_this_run}\n- Onceden PASS: {len(done_ids)}\n"
        f"- Final PASS: {N-len(final_fail)}/{N}\n"
        f"- Degisen alan: yalniz description\n- Basarisiz: {final_fail or 'yok'}\n"
        f"- Kalan kota: {api.remaining}\n", encoding="utf-8")
    if final_fail or len(result) != N:
        raise SystemExit(f"HATA: final dogrulama {N-len(final_fail)}/{N}. DUR.")
    log(f"TAMAMLANDI: {N}/{N} PASS; yalniz description degisti; kota {api.remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
