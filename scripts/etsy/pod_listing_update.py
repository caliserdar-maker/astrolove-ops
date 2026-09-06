#!/usr/bin/env python3
"""
POD (Prodigi poster) ilani: tag + aciklama guncellemesi (EN) - 6 Eyl 2026.

Kaynak sablon: docs/POD_LISTING_TEMPLATE.md (EN aciklama blogu oradan okunur;
tag seti asagida sabittir ve dokumanla aynidir). Basliga DOKUNULMAZ.

Kullanim:
  pod_listing_update.py --pair ARIES_LEO --out out.csv --dry-run            # listing id yok:
                                                                            #   magazadaki taslaklari listeler (salt okur)
  pod_listing_update.py --pair ARIES_LEO --listing-id 123 --out out.csv --dry-run
  pod_listing_update.py --pair ARIES_LEO --listing-id 123 --out out.csv --apply   # ONAY SONRASI

Dry-run hicbir yazma cagrisi yapmaz. Apply idempotenttir: alan zaten hedef
degerdeyse gonderilmez; yazmadan sonra geri okuma dogrulamasi (PASS/FAIL).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE,
GITHUB_STEP_SUMMARY (istege bagli). Kota 400 altinda yazma yapilmaz.
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_listing_update import load_block, norm, readback, tags_of, validate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_MD = REPO_ROOT / "docs" / "POD_LISTING_TEMPLATE.md"
MAX_TAG = 20
QUOTA_MIN = 400

TAGS_EN = ["zodiac wall art", "{pair}", "couple compatibility", "astrology wall art",
           "zodiac couple gift", "anniversary gift", "star sign poster", "couples wall decor",
           "astrology lover gift", "minimalist wall art", "fine art print", "wedding gift couple",
           "celestial home decor"]

SIGNS = ["Aquarius", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Pisces"]


# ------------------------------------------------------------------ sablon
def pair_tag(S1, S2):
    """'{s1} {s2} print'; 20'yi asarsa '{s1} print'."""
    t = f"{S1} {S2} print".lower()
    if len(t) <= MAX_TAG:
        return t, ""
    short = f"{S1} print".lower()
    return short, f"{t} ({len(t)}) -> {short}"


def build(pair, desc_tpl):
    s1, s2 = pair.split("_", 1)
    S1, S2 = s1.capitalize(), s2.capitalize()
    if S1 not in SIGNS or S2 not in SIGNS:
        raise SystemExit(f"HATA: bilinmeyen burc: {pair}")
    ptag, note = pair_tag(S1, S2)
    tags = [t.format(pair=ptag) for t in TAGS_EN]
    desc = desc_tpl.replace("{PAIR}", f"{S1} & {S2}").replace("{S1}", S1).replace("{S2}", S2)
    left = re.findall(r"\{[A-Za-z0-9_]+\}", desc)
    if left:
        raise SystemExit(f"HATA: aciklamada doldurulmamis yer tutucu: {left}")
    return tags, desc, note


def load_template():
    return load_block(TEMPLATE_MD.read_text(encoding="utf-8"), "EN_DESCRIPTION")


# ------------------------------------------------------------------ taslak kesfi
def list_drafts(api, shop_id, exclude):
    rows, offset = [], 0
    while True:
        r = api.get(f"/shops/{shop_id}/listings", params={"state": "draft", "limit": 100, "offset": offset}) or {}
        res = r.get("results") or []
        for L in res:
            lid = str(L.get("listing_id"))
            if lid in exclude:
                continue
            rows.append(dict(listing_id=lid, title=(L.get("title") or "")[:90], state=L.get("state"),
                             type=L.get("listing_type"), quantity=L.get("quantity"),
                             price=((L.get("price") or {}).get("amount") or 0) / 100,
                             has_variations=L.get("has_variations"), n_tags=len(L.get("tags") or []),
                             taxonomy_id=L.get("taxonomy_id"), shipping_profile_id=L.get("shipping_profile_id")))
        if len(res) < 100:
            break
        offset += 100
    return rows


def read_wp_ids(path):
    ids = set()
    if not path or not Path(path).exists():
        return ids
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                ids.add(raw[1].strip())
    return ids


# ------------------------------------------------------------------ ilan
def process(api, shop_id, pair, lid, tags, desc, note, apply):
    cur = api.get(f"/listings/{lid}")
    old_title, old_tags, old_desc = cur.get("title") or "", tags_of(cur), cur.get("description") or ""
    S1, S2 = [s.capitalize() for s in pair.split("_", 1)]
    title_ok = S1.lower() in old_title.lower() and S2.lower() in old_title.lower()
    payload = {}
    if old_tags != tags:
        payload["tags"] = tags
    if norm(old_desc) != norm(desc):
        payload["description"] = desc
    status = "DEGISIM_YOK" if not payload else "PLANLANDI"
    if apply and payload:
        try:
            rem = int(api.remaining or 0)
        except ValueError:
            rem = 0
        if api.remaining is not None and rem < QUOTA_MIN:
            status = f"KOTA({rem})"
        else:
            body = dict(payload)
            if "tags" in body:
                body["tags"] = ",".join(body["tags"])   # Etsy v3: virgullu tek metin (2 Eyl dersi)
            api.patch(f"/shops/{shop_id}/listings/{lid}", body)
            _, ok = readback(api, f"/listings/{lid}", payload)
            status = "PASS" if all(ok.values()) else "FAIL(" + ",".join(k for k, v in ok.items() if not v) + ")"
    return dict(pair=pair, listing_id=lid, state=cur.get("state"), type=cur.get("listing_type"),
                title=old_title, title_pair_ok=title_ok, has_variations=cur.get("has_variations"),
                n_tags=len(tags), tag_issue=validate(old_title, tags), pair_tag_note=note,
                tags_change="tags" in payload, desc_change="description" in payload,
                old_desc_len=len(old_desc), desc_len=len(desc),
                old_tags="|".join(old_tags), new_tags="|".join(tags), status=status)


def write_csv(rows, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out.write_text("", encoding="utf-8")
        return
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |")
    return "\n".join(out)


def summary(text):
    log(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", required=True, help="or. ARIES_LEO")
    ap.add_argument("--listing-id", default="")
    ap.add_argument("--wp-state", default="", help="WP cift,listing_id CSV'si; taslak kesfinde haric tutulur")
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    tags, desc, note = build(a.pair, load_template())
    issue = validate("", tags)
    log(f"sablon: {len(tags)} tag, aciklama {len(desc)} karakter, tag sorunu: {issue or 'yok'}"
        + (f", cift tag notu: {note}" if note else ""))
    if issue:
        raise SystemExit(f"HATA: tag kurali: {issue}")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    if not a.listing_id:
        if a.apply:
            raise SystemExit("HATA: --apply icin --listing-id gerekir.")
        rows = list_drafts(api, shop_id, read_wp_ids(a.wp_state))
        write_csv(rows, a.out)
        summary(f"## Taslak ilanlar (WP haric): {len(rows)} | kota {api.remaining}\n\n"
                + md_table(rows, ["listing_id", "title", "type", "quantity", "price", "has_variations",
                                  "n_tags", "taxonomy_id", "shipping_profile_id"]))
        log("DRY-RUN: listing_id verilmedi; yalniz kesif. Yazma yok.")
        return

    row = process(api, shop_id, a.pair, a.listing_id, tags, desc, note, a.apply)
    write_csv([row], a.out)
    summary(f"## POD ilan {a.listing_id} ({'APPLY' if a.apply else 'DRY-RUN'}) | kota {api.remaining}\n\n"
            + md_table([row], ["listing_id", "state", "type", "title", "title_pair_ok", "has_variations",
                               "tags_change", "desc_change", "old_desc_len", "desc_len", "status"])
            + "\n\nYeni tagler: " + ", ".join(tags)
            + ("\n\nEski tagler: " + row["old_tags"].replace("|", ", ") if row["old_tags"] else "\n\nEski tagler: (bos)"))
    if not row["title_pair_ok"]:
        summary(f"UYARI: ilan basliginda '{a.pair}' burclari yok: {row['title']!r}")
    if a.apply and not row["status"].startswith("PASS") and row["status"] != "DEGISIM_YOK":
        raise SystemExit(f"FAIL: {row['status']}")


if __name__ == "__main__":
    main()
