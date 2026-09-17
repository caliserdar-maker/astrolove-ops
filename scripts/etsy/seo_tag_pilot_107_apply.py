#!/usr/bin/env python3
"""Apply the approved English tag-only pilot to exactly 107 Etsy listings.

The plan contains all 546 active listings so preflight can prove that the
catalog still matches the fresh snapshot before the first PATCH. Only rows
marked YES may be written, and the only PATCH field is tags. Russian
translations for all 107 target listings are hashed before and after.
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

EXPECTED = 546
APPLY_COUNT = 107
PROTECTED = [
    "title", "description", "price", "state", "shop_section_id", "taxonomy_id",
    "shipping_profile_id", "return_policy_id", "materials", "who_made",
    "when_made", "is_supply", "has_variations", "should_auto_renew",
    "listing_type", "quantity",
]


def norm(value):
    value = html.unescape(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(x.rstrip() for x in value.split("\n")).strip()


def digest(value):
    return hashlib.sha256(norm(value).encode("utf-8")).hexdigest()


def tags_of(obj):
    return [html.unescape(str(x)).strip().casefold()
            for x in (obj.get("tags") or []) if str(x).strip()]


def translation_digest(obj):
    payload = {
        "title": norm(obj.get("title")),
        "description": norm(obj.get("description")),
        "tags": tags_of(obj),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_plan(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    expected_stats = {
        "listings": 546, "apply_yes": 107, "apply_no": 439,
        "control_no_change": 102, "protected_or_hold": 337,
        "fields_written": ["tags"],
    }
    if payload.get("schema") != 1 or payload.get("operation") != "seo_tag_pilot_107":
        raise SystemExit("HATA: plan semasi/operasyonu gecersiz. DUR.")
    if payload.get("stats") != expected_stats:
        raise SystemExit("HATA: plan sabit sayimlari gecersiz. DUR.")
    rows = payload.get("rows") or []
    ids = [str(x.get("listing_id") or "") for x in rows]
    if len(rows) != EXPECTED or len(set(ids)) != EXPECTED or not all(x.isdigit() for x in ids):
        raise SystemExit("HATA: plan 546 benzersiz sayisal listing_id icermiyor. DUR.")
    if sum(x.get("application_flag") == "YES" for x in rows) != APPLY_COUNT:
        raise SystemExit("HATA: uygulama kapsami 107 degil. DUR.")
    for row in rows:
        before, after = row.get("tags_before") or [], row.get("tags_after") or []
        if len(before) != 13 or len(after) != 13 or len(set(after)) != 13:
            raise SystemExit(f"HATA: {row['listing_id']} etiket sayisi/benzersizlik FAIL. DUR.")
        if any(not x or len(x) > 20 for x in after):
            raise SystemExit(f"HATA: {row['listing_id']} etiket karakter siniri FAIL. DUR.")
        apply = row.get("application_flag") == "YES"
        if apply and "cancer cancer" in after:
            raise SystemExit(f"HATA: {row['listing_id']} yasakli cancer cancer etiketi. DUR.")
        signs = set(str(row.get("zodiac_pair") or "").casefold().split("_"))
        if apply and (not signs or not all(sign in " ".join(after) for sign in signs)):
            raise SystemExit(f"HATA: {row['listing_id']} iki burc kapsami FAIL. DUR.")
        if apply == (before == after):
            raise SystemExit(f"HATA: {row['listing_id']} uygulama bayragi/hedef celiskisi. DUR.")
    return payload, rows


def protected_diff(before, after):
    def value(obj, key):
        return norm(obj.get(key)) if key in ("title", "description") else obj.get(key)
    return [key for key in PROTECTED if value(before, key) != value(after, key)]


def get_listing(api, listing_id):
    return api.get(f"/listings/{listing_id}", ok404=True) or {}


def get_ru(api, shop, listing_id):
    return api.get(f"/shops/{shop}/listings/{listing_id}/translations/ru", ok404=True) or {}


def remaining_int(api):
    try:
        return int(api.remaining)
    except (TypeError, ValueError):
        return None


def write_outputs(out, results, summary):
    (out / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "summary.md").write_text(
        "# AstroLove 107 ilan İngilizce etiket pilotu\n\n"
        f"- Mod: **{summary['mode']}**\n"
        f"- 546 ilan ön kontrolü: **{summary['preflight_pass']}/546**\n"
        f"- Uygulama kapsamı: **107**\n"
        f"- Bu koşuda yazılan: **{summary['written_this_run']}**\n"
        f"- Zaten hedefte: **{summary['already_target']}**\n"
        f"- Final hedef PASS: **{summary['final_target_pass']}/107**\n"
        f"- Kapsam dışı değişmedi: **{summary['non_target_pass']}/439**\n"
        f"- Rusça çeviri korundu: **{summary['ru_pass']}/107**\n"
        f"- Korunan alan hatası: **{len(summary['protected_failures'])}**\n"
        f"- Etsy yazma alanı: **tags**\n"
        f"- Kalan kota: **{summary.get('quota_remaining')}**\n",
        encoding="utf-8",
    )


def run(api, shop, plan_rows, out, apply=False, quota_buffer=120, sleep_seconds=2):
    out.mkdir(parents=True, exist_ok=True)
    backups = out / "backups"
    backups.mkdir(exist_ok=True)
    rows = {str(x["listing_id"]): x for x in plan_rows}
    live = {str(x.get("listing_id")): x for x in list_active(api, shop)}
    if len(live) != EXPECTED or set(live) != set(rows):
        raise SystemExit("HATA: aktif 546 listing kapsami planla uyusmuyor. Hicbir sey yazilmadi. DUR.")

    pending, already, original = [], [], {}
    for lid in sorted(rows, key=int):
        row, item = rows[lid], live[lid]
        apply_row = row["application_flag"] == "YES"
        if item.get("state") != "active":
            raise SystemExit(f"HATA: {lid} aktif degil. Hicbir sey yazilmadi. DUR.")
        if digest(item.get("title")) != row["title_sha256"]:
            raise SystemExit(f"HATA: {lid} baslik snapshot ile uyusmuyor. Hicbir sey yazilmadi. DUR.")
        if digest(item.get("description")) != row["description_sha256"]:
            raise SystemExit(f"HATA: {lid} aciklama snapshot ile uyusmuyor. Hicbir sey yazilmadi. DUR.")
        current = tags_of(item)
        allowed = [row["tags_before"], row["tags_after"]] if apply_row else [row["tags_before"]]
        if current not in allowed:
            raise SystemExit(f"HATA: {lid} etiketler izinli baz/hedef durumda degil. Hicbir sey yazilmadi. DUR.")
        if not apply_row and row["tags_before"] != row["tags_after"]:
            raise SystemExit(f"HATA: {lid} kapsam disi hedef farkli. DUR.")
        original[lid] = item
        (backups / f"{lid}.before.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if apply_row:
            (already if current == row["tags_after"] else pending).append(lid)

    summary = {
        "mode": "APPLY" if apply else "DRY_RUN", "preflight_pass": EXPECTED,
        "written_this_run": 0, "already_target": len(already),
        "final_target_pass": len(already), "non_target_pass": 439,
        "ru_pass": 0, "protected_failures": [], "final_failures": [],
        "quota_remaining": api.remaining,
    }
    results = [{"listing_id": lid, "status": "READY"} for lid in pending]
    results += [{"listing_id": lid, "status": "ALREADY_PASS"} for lid in already]
    log(f"ON KONTROL 546/546 PASS | yazilacak {len(pending)} | zaten hedef {len(already)}")
    if not apply:
        write_outputs(out, results, summary)
        return summary

    ru_before = {}
    for lid in sorted(pending + already, key=int):
        ru = get_ru(api, shop, lid)
        ru_before[lid] = translation_digest(ru)
        (backups / f"{lid}.ru.before.json").write_text(
            json.dumps(ru, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    remaining = remaining_int(api)
    required = len(pending) * 2 + APPLY_COUNT + 6 + quota_buffer
    if remaining is not None and remaining < required:
        raise SystemExit(f"HATA: kota {remaining}; gerekli en az {required}. Yeni yazma yapilmadi. DUR.")

    results = [{"listing_id": lid, "status": "ALREADY_PASS"} for lid in already]
    for index, lid in enumerate(pending, 1):
        row, before = rows[lid], original[lid]
        remaining = remaining_int(api)
        still_required = (len(pending) - index + 1) * 2 + APPLY_COUNT + 6 + quota_buffer
        if remaining is not None and remaining < still_required:
            write_outputs(out, results, summary)
            raise SystemExit(f"HATA: kota {remaining}; kalan is icin {still_required} gerekli. DUR.")
        api.patch(f"/shops/{shop}/listings/{lid}", {"tags": ",".join(row["tags_after"])})
        after = {}
        for wait in (sleep_seconds, 4, 8):
            time.sleep(wait)
            after = get_listing(api, lid)
            diffs = protected_diff(before, after)
            if tags_of(after) == row["tags_after"] and not diffs:
                break
        else:
            (backups / f"{lid}.after_FAIL.json").write_text(
                json.dumps(after, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            raise SystemExit(f"HATA: {lid} geri okuma FAIL; protected={diffs}. DUR.")
        (backups / f"{lid}.after.json").write_text(
            json.dumps(after, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        results.append({"listing_id": lid, "status": "PASS"})
        summary["written_this_run"] += 1
        summary["final_target_pass"] = len(already) + summary["written_this_run"]
        summary["quota_remaining"] = api.remaining
        write_outputs(out, results, summary)
        log(f"[{summary['final_target_pass']}/107] {lid} tags PASS | kota {api.remaining}")

    final = {str(x.get("listing_id")): x for x in list_active(api, shop)}
    failures, protected, non_target_pass = [], [], 0
    for lid, row in rows.items():
        item = final.get(lid) or {}
        target = row["tags_after"] if row["application_flag"] == "YES" else row["tags_before"]
        ok = (digest(item.get("title")) == row["title_sha256"]
              and digest(item.get("description")) == row["description_sha256"]
              and tags_of(item) == target)
        if not ok:
            failures.append(lid)
        if row["application_flag"] == "NO" and ok:
            non_target_pass += 1
        diffs = protected_diff(original[lid], item)
        if diffs:
            protected.append({"listing_id": lid, "fields": diffs})

    ru_failures = []
    for lid in sorted(pending + already, key=int):
        ru = get_ru(api, shop, lid)
        (backups / f"{lid}.ru.after.json").write_text(
            json.dumps(ru, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        if translation_digest(ru) != ru_before[lid]:
            ru_failures.append(lid)

    target_failures = [x for x in failures if rows[x]["application_flag"] == "YES"]
    summary.update({
        "final_target_pass": APPLY_COUNT - len(target_failures),
        "non_target_pass": non_target_pass,
        "ru_pass": APPLY_COUNT - len(ru_failures),
        "final_failures": failures,
        "ru_failures": ru_failures,
        "protected_failures": protected,
        "quota_remaining": api.remaining,
    })
    write_outputs(out, results, summary)
    if failures or protected or ru_failures:
        raise SystemExit(
            f"HATA: final dogrulama FAIL; hedef={target_failures[:5]}, "
            f"korunan={protected[:3]}, ru={ru_failures[:5]}. DUR.")
    log(f"TAMAMLANDI: 107/107 tags PASS | kapsam disi 439/439 | RU 107/107 | kota {api.remaining}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-buffer", type=int, default=120)
    args = ap.parse_args()
    if args.apply and args.confirm != "CANLI":
        raise SystemExit("HATA: --apply icin --confirm CANLI gerekli. DUR.")
    _, rows = read_plan(args.plan)
    key = os.environ.get("ETSY_API_KEY", "")
    secret = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik. DUR.")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    run(Etsy(store), shop, rows, Path(args.out), apply=args.apply,
        quota_buffer=args.quota_buffer)


if __name__ == "__main__":
    main()
