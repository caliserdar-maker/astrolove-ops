#!/usr/bin/env python3
"""Apply only the pinned factual SEO corrections to all 546 active listings.

No write is possible without ``--apply --confirm CANLI``. Before the first
PATCH, every active listing must match either the audited before-state or the
exact target state. Titles are immutable. Each write is read back and all
unwritten listing fields are compared with the in-run backup.
"""
import argparse
import hashlib
import html
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from seo_live_snapshot import list_active  # noqa: E402

OLD_HEADER = "PREFER IT READY TO HANG?"
NEW_HEADER = "PREFER A PRINTED VERSION?"
EXPECTED = 546
PROTECTED = ["title", "price", "state", "shop_section_id", "taxonomy_id",
             "shipping_profile_id", "return_policy_id", "materials", "who_made",
             "when_made", "is_supply", "has_variations", "should_auto_renew",
             "listing_type", "quantity"]


def norm(value):
    value = html.unescape(value or "").replace("\r\n", "\n")
    return "\n".join(x.rstrip() for x in value.split("\n")).strip()


def digest(value):
    return hashlib.sha256(norm(value).encode("utf-8")).hexdigest()


def tags_of(obj):
    return [html.unescape(str(x)).strip().casefold() for x in (obj.get("tags") or []) if str(x).strip()]


def read_plan(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    ids = [str(x.get("listing_id") or "") for x in rows]
    expected_stats = {"listings": 546, "description_changes": 390, "tag_listing_changes": 161,
                      "wallpaper_false_compatibility": 78, "pod_false_compatibility": 78,
                      "abbreviation_listings": 24}
    if payload.get("schema") != 1 or payload.get("stats") != expected_stats:
        raise SystemExit("HATA: plan semasi veya sabit sayimlari gecersiz. DUR.")
    if len(rows) != EXPECTED or len(set(ids)) != EXPECTED or not all(x.isdigit() for x in ids):
        raise SystemExit("HATA: plan 546 benzersiz sayisal listing_id icermiyor. DUR.")
    for row in rows:
        before, after = row.get("tags_before") or [], row.get("tags_after") or []
        if len(before) != 13 or len(after) != 13 or len(set(after)) != 13 or any(len(x) > 20 for x in after):
            raise SystemExit(f"HATA: {row['listing_id']} hedef etiket QC FAIL. DUR.")
        if row.get("description_replace") not in ("", OLD_HEADER):
            raise SystemExit(f"HATA: {row['listing_id']} izin verilmeyen aciklama islemi. DUR.")
    return rows


def protected_diff(before, after, fields_written):
    fields = list(PROTECTED)
    if "description" not in fields_written:
        fields.append("description")
    if "tags" not in fields_written:
        fields.append("tags")
    def value(obj, key):
        if key == "tags":
            return tags_of(obj)
        if key in ("title", "description"):
            return norm(obj.get(key))
        return obj.get(key)
    return [k for k in fields if value(before, k) != value(after, k)]


def target_description(row, live_description):
    if not row.get("description_replace"):
        return live_description
    if norm(live_description).count(OLD_HEADER) != 1:
        raise SystemExit(f"HATA: {row['listing_id']} eski aciklama basligi birebir bulunamadi. DUR.")
    return live_description.replace(OLD_HEADER, NEW_HEADER, 1)


def get_listing(api, listing_id):
    return api.get(f"/listings/{listing_id}", ok404=True) or {}


def remaining_int(api):
    try:
        return int(api.remaining)
    except (TypeError, ValueError):
        return None


def write_outputs(out, results, summary):
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "summary.md").write_text(
        "# AstroLove 546 doğruluk düzeltmesi\n\n"
        f"- Mod: **{summary['mode']}**\n"
        f"- Ön kontrol: **{summary['preflight_pass']}/546**\n"
        f"- Bu koşuda yazılan: **{summary['written_this_run']}**\n"
        f"- Zaten hedefte: **{summary['already_target']}**\n"
        f"- Final PASS: **{summary['final_pass']}/546**\n"
        f"- Başlık değişikliği: **0**\n"
        f"- Açıklama hedefi: **390**\n"
        f"- Etiket hedefi: **161 ilan**\n"
        f"- Korunan alan hatası: **{len(summary['protected_failures'])}**\n"
        f"- Kalan kota: **{summary.get('quota_remaining')}**\n",
        encoding="utf-8")


def run(api, shop, plan, out, apply=False, quota_buffer=100, sleep_seconds=2):
    out.mkdir(parents=True, exist_ok=True)
    backup = out / "backups"; backup.mkdir(exist_ok=True)
    rows = {str(x["listing_id"]): x for x in plan}
    live_list = list_active(api, shop)
    live = {str(x.get("listing_id")): x for x in live_list}
    if len(live) != EXPECTED or set(live) != set(rows):
        missing = sorted(set(rows) - set(live)); extra = sorted(set(live) - set(rows))
        raise SystemExit(f"HATA: aktif kapsam uyusmuyor; live={len(live)}, eksik={missing[:5]}, fazla={extra[:5]}. DUR.")

    pending, already, before = [], [], {}
    for lid in sorted(rows, key=int):
        row, item = rows[lid], live[lid]
        if item.get("state") != "active" or digest(item.get("title")) != row["title_sha256"]:
            raise SystemExit(f"HATA: {lid} state/title snapshot ile uyusmuyor. Hicbir sey yazilmadi. DUR.")
        desc_sha = digest(item.get("description"))
        if desc_sha not in {row["description_before_sha256"], row["description_after_sha256"]}:
            raise SystemExit(f"HATA: {lid} aciklama ne eski ne hedef durumda. Hicbir sey yazilmadi. DUR.")
        tags = tags_of(item)
        if tags not in (row["tags_before"], row["tags_after"]):
            raise SystemExit(f"HATA: {lid} etiketler ne eski ne hedef durumda. Hicbir sey yazilmadi. DUR.")
        fields = []
        if desc_sha != row["description_after_sha256"]:
            fields.append("description")
        if tags != row["tags_after"]:
            fields.append("tags")
        (backup / f"{lid}.before.json").write_text(json.dumps(item, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        before[lid] = item
        (pending if fields else already).append((lid, fields))
    log(f"ON KONTROL 546/546 PASS | bekleyen {len(pending)} | zaten hedef {len(already)} | kota {api.remaining}")

    summary = {"mode": "APPLY" if apply else "DRY_RUN", "preflight_pass": EXPECTED,
               "written_this_run": 0, "already_target": len(already), "final_pass": len(already),
               "protected_failures": [], "quota_remaining": api.remaining}
    if not apply:
        results = [{"listing_id": lid, "status": "READY", "fields": fields} for lid, fields in pending]
        results += [{"listing_id": lid, "status": "ALREADY_PASS", "fields": []} for lid, _ in already]
        write_outputs(out, results, summary)
        return summary

    remaining = remaining_int(api)
    required = len(pending) * 2 + 6 + quota_buffer
    if remaining is not None and remaining < required:
        raise SystemExit(f"HATA: kota {remaining}; gerekli en az {required}. Yeni yazma yapilmadi. DUR.")

    results = [{"listing_id": lid, "status": "ALREADY_PASS", "fields": []} for lid, _ in already]
    for index, (lid, fields) in enumerate(pending, 1):
        row, item = rows[lid], before[lid]
        remaining = remaining_int(api)
        still_required = (len(pending) - index + 1) * 2 + 6 + quota_buffer
        if remaining is not None and remaining < still_required:
            write_outputs(out, results, summary)
            raise SystemExit(f"HATA: kota {remaining}; kalan is icin {still_required} gerekli. DUR.")
        body = {}
        if "description" in fields:
            body["description"] = target_description(row, item.get("description") or "")
        if "tags" in fields:
            body["tags"] = ",".join(row["tags_after"])
        api.patch(f"/shops/{shop}/listings/{lid}", body)
        after = {}
        for wait in (sleep_seconds, 4, 8):
            time.sleep(wait)
            after = get_listing(api, lid)
            desc_ok = digest(after.get("description")) == row["description_after_sha256"]
            tags_ok = tags_of(after) == row["tags_after"]
            diffs = protected_diff(item, after, fields)
            if desc_ok and tags_ok and not diffs:
                break
        else:
            (backup / f"{lid}.after_FAIL.json").write_text(json.dumps(after, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            raise SystemExit(f"HATA: {lid} geri okuma FAIL; protected={diffs}. DUR.")
        (backup / f"{lid}.after.json").write_text(json.dumps(after, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        results.append({"listing_id": lid, "status": "PASS", "fields": fields})
        summary["written_this_run"] += 1
        summary["final_pass"] = len(already) + summary["written_this_run"]
        summary["quota_remaining"] = api.remaining
        write_outputs(out, results, summary)
        log(f"[{summary['final_pass']}/{EXPECTED}] {lid} PASS {','.join(fields)} | kota {api.remaining}")

    final_list = list_active(api, shop)
    final = {str(x.get("listing_id")): x for x in final_list}
    failures, protected = [], []
    for lid, row in rows.items():
        item = final.get(lid) or {}
        if digest(item.get("title")) != row["title_sha256"] or digest(item.get("description")) != row["description_after_sha256"] or tags_of(item) != row["tags_after"]:
            failures.append(lid)
        changed_fields = []
        if row["description_before_sha256"] != row["description_after_sha256"]:
            changed_fields.append("description")
        if row["tags_before"] != row["tags_after"]:
            changed_fields.append("tags")
        diffs = protected_diff(before[lid], item, changed_fields)
        if diffs:
            protected.append({"listing_id": lid, "fields": diffs})
    summary.update({"final_pass": EXPECTED - len(failures), "final_failures": failures,
                    "protected_failures": protected, "quota_remaining": api.remaining})
    write_outputs(out, results, summary)
    if failures or protected:
        raise SystemExit(f"HATA: final dogrulama FAIL; hedef={failures[:5]}, protected={protected[:3]}. DUR.")
    log(f"TAMAMLANDI: 546/546 PASS | baslik 0 degisiklik | kota {api.remaining}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-buffer", type=int, default=100)
    args = ap.parse_args()
    if args.apply and args.confirm != "CANLI":
        raise SystemExit("HATA: --apply icin --confirm CANLI gerekli. DUR.")
    plan = read_plan(args.plan)
    key, secret, shop = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""), os.environ.get("ETSY_SHOP_ID", "")
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik. DUR.")
    mask(key); mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    run(Etsy(store), shop, plan, Path(args.out), apply=args.apply, quota_buffer=args.quota_buffer)


if __name__ == "__main__":
    main()
