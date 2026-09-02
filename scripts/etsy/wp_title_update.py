#!/usr/bin/env python3
"""
Wallpaper ilanlarinda baslik sablonu guncellemesi + tag kontrolu.

Sablon (14 kelime, 2 Eyl 2026 karari; Etsy'nin AI onerisi reddedildi):
  <SIGN1> <SIGN2> Matching Couple Wallpaper, 4 Colors, Phone Tablet Desktop Watch, Zodiac Digital Download

Basliktan cikan "Compatibility" ve "Set" kelimeleri tag'lerde bulunmali:
  "zodiac compatibility" ve "wallpaper set" yoksa eklenir (13 tag siniri
  icinde; yer yoksa asagidaki kurala gore bir tag dusurulur ve raporlanir).

RU cevirilerine DOKUNULMAZ (ayri endpoint, cagrilmaz).

Kullanim:
  wp_title_update.py --state TEMP_kopyasi/WA_WP_DRAFTS_STATE.csv --out _out/title.csv --dry-run
  wp_title_update.py --state ... --out ... --apply        # ONAY SONRASI

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE,
GITHUB_STEP_SUMMARY (istege bagli).
"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

TEMPLATE = ("{s1} {s2} Matching Couple Wallpaper, 4 Colors, "
            "Phone Tablet Desktop Watch, Zodiac Digital Download")
REQUIRED_TAGS = ["zodiac compatibility", "wallpaper set"]
MAX_TAGS = 13
MAX_TAG_LEN = 20
MAX_TITLE_LEN = 140


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if not raw or not raw[0].strip():
                continue
            pair, lid = raw[0].strip(), raw[1].strip()
            if not lid.isdigit():
                continue  # baslik satiri vb.
            rows.append((pair, lid))
    return rows


def new_title(pair):
    s1, s2 = pair.split("_", 1)
    t = TEMPLATE.format(s1=s1.capitalize(), s2=s2.capitalize())
    if len(t) > MAX_TITLE_LEN:
        raise SystemExit(f"HATA: {pair} basligi {len(t)} karakter (> {MAX_TITLE_LEN}).")
    return t


def plan_tags(tags, title):
    """Eksik zorunlu tag'leri ekler. 13 doluysa dusurulecek tag:
    (1) tum kelimeleri yeni baslikta zaten gecen tag'lerden ilki,
    (2) yoksa listenin sonuncusu. Donus: (yeni_liste, eklenen, dusurulen)."""
    tags = [t.strip().lower() for t in tags if t and t.strip()]
    title_words = set(w.strip(",").lower() for w in title.split())
    added, dropped = [], []
    for req in REQUIRED_TAGS:
        if req in tags:
            continue
        if len(tags) >= MAX_TAGS:
            cand = [t for t in tags if t not in REQUIRED_TAGS
                    and all(w in title_words for w in t.split())]
            victim = cand[0] if cand else tags[-1]
            tags.remove(victim)
            dropped.append(victim)
        tags.append(req)
        added.append(req)
    for t in added:
        if len(t) > MAX_TAG_LEN:
            raise SystemExit(f"HATA: tag {t!r} {len(t)} karakter (> {MAX_TAG_LEN}).")
    return tags, added, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    keystring = os.environ.get("ETSY_API_KEY", "")
    shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    if not shop_id:
        raise SystemExit("HATA: ETSY_SHOP_ID tanimli degil.")
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    rows = read_state(a.state)
    log(f"{len(rows)} ilan okunacak; mod = {'DRY-RUN' if a.dry_run else 'APPLY'}")
    results = []
    for pair, lid in rows:
        cur = api.get(f"/listings/{lid}")
        old_title = cur.get("title") or ""
        old_tags = list(cur.get("tags") or [])
        nt = new_title(pair)
        tags, added, dropped = plan_tags(old_tags, nt)
        title_change = old_title != nt
        tag_change = tags != [t.lower() for t in old_tags]
        status = "DEGISIM_YOK" if not (title_change or tag_change) else "PLANLANDI"
        if a.apply and status == "PLANLANDI":
            payload = {}
            if title_change:
                payload["title"] = nt
            if tag_change:
                payload["tags"] = ",".join(tags)
            api.patch(f"/shops/{shop_id}/listings/{lid}", payload)
            back = api.get(f"/listings/{lid}")
            ok_t = (back.get("title") == nt)
            ok_g = ([t.lower() for t in (back.get("tags") or [])] == tags)
            status = "PASS" if (ok_t and ok_g) else f"FAIL(title={ok_t},tags={ok_g})"
        results.append(dict(pair=pair, listing_id=lid, state=cur.get("state"),
                            old_title=old_title, new_title=nt,
                            title_change=title_change,
                            old_tags="|".join(old_tags), new_tags="|".join(tags),
                            added="|".join(added), dropped="|".join(dropped),
                            n_tags=len(tags), status=status))
        log(f"{pair} {lid}: {status}"
            f"{' baslik' if title_change else ''}{' tag+' + ','.join(added) if added else ''}"
            f"{' tag-' + ','.join(dropped) if dropped else ''}")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)

    n_title = sum(r["title_change"] for r in results)
    n_add = sum(1 for r in results if r["added"])
    n_drop = sum(1 for r in results if r["dropped"])
    md = [f"## Baslik guncelleme ({'DRY-RUN' if a.dry_run else 'APPLY'})", "",
          f"ilan {len(results)} | baslik degisecek {n_title} | tag eklenecek {n_add} | "
          f"tag dusecek {n_drop} | api cagri {api.calls} | kalan kota {api.remaining}", "",
          "| # | cift | id | eski baslik | yeni baslik | tag + | tag - | n | durum |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        md.append(f"| {i} | {r['pair']} | {r['listing_id']} | {r['old_title']} | {r['new_title']} | "
                  f"{r['added']} | {r['dropped']} | {r['n_tags']} | {r['status']} |")
    text = "\n".join(md)
    log(text)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    fails = [r for r in results if r["status"].startswith("FAIL")]
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
