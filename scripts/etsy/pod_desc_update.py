#!/usr/bin/env python3
"""
Mevcut POD ilanlarinin aciklamasini sablona esitler (Mo 6 Eyl 2026: "THE ARTWORK" altina cercevesiz satiri).

Her ilan icin:
  1. GET listing + GET translations/ru; sablondan yeniden uretilen metinle BOLUM BOLUM karsilastirilir.
  2. Yalniz --section ile verilen bolum(ler) degisiyorsa yazilir (EN updateListing PATCH, RU translations/ru PUT);
     baska bolumde fark varsa o ilan ATLANIR (FAIL degil, "SIRA DISI" olarak raporlanir) - yanlislikla ustune yazma yok.
  3. Geri okuma: PATCH/PUT cevabindaki metin sablonla birebir (cevapta yoksa GET ile).
STATE (cift,listing_id,stage) dosyasindaki verified ilanlar islenir; kota --quota-min altina inince durur,
kalan ilanlar raporlanir (sonraki kosu ayni STATE ile devam eder). ETA sayaci her ilanda.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_desc_update.py --state STATE.csv --out OUT --dry-run|--apply [--limit N] [--quota-min 400]
          [--section "✦ THE ARTWORK" --section-ru "✦ АРТ"] [--ru-dict dict/ru_RU]
"""
import argparse
import csv
import difflib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_inventory_update import sections  # noqa: E402
from pod_listing_create import build_listing, build_ru, load_ru_template, spellcheck_ru  # noqa: E402
from pod_listing_update import load_template  # noqa: E402
from wp_listing_update import norm  # noqa: E402

SEC_EN, SEC_RU = "✦ THE ARTWORK", "✦ АРТ"


def diff_of(old, new, sec):
    """(yalniz_sec_degisti, diff_metni, digerleri_ayni). Bolum basliklari da eslesmeli."""
    so, sn = sections(old), sections(new)
    ko = [k for k in so if k != sec]
    kn = [k for k in sn if k != sec]
    others_same = ko == kn and all(so[k] == sn[k] for k in ko)
    o = (sec + "\n" + so[sec]) if sec in so else ""
    n = (sec + "\n" + sn[sec]) if sec in sn else ""
    diff = "\n".join(difflib.unified_diff(o.split("\n"), n.split("\n"), "eski", "yeni", lineterm="", n=0))
    return others_same and sec in sn, diff, others_same


def read_state(path):
    rows = []
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                    rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True, help="cift,listing_id,stage CSV (verified olanlar islenir)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="en fazla N ilan (0 = hepsi)")
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--section", default=SEC_EN)
    ap.add_argument("--section-ru", default=SEC_RU)
    ap.add_argument("--ru-dict", default="")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = read_state(a.state)
    if not rows:
        raise SystemExit(f"HATA: STATE'te verified ilan yok: {a.state}")
    tpl, ru_tpl = load_template(), load_ru_template()
    if a.ru_dict:
        t, tg, dsc, _ = build_ru(rows[0][0], ru_tpl)
        spellcheck_ru(a.ru_dict, [t, dsc, " ".join(tg)])

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    todo = rows[:a.limit] if a.limit else rows
    q0 = None
    res, sample, t0 = [], None, time.time()
    stopped = None

    for n, (pair, lid) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if a.apply and rem is not None and rem < a.quota_min:
            stopped = pair
            log(f"KOTA {rem} < {a.quota_min}: {pair} ve sonrasi islenmedi")
            break
        L = api.get(f"/listings/{lid}") or {}
        if q0 is None:
            q0 = api.remaining
        tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        new_en = build_listing(pair, tpl)[2]
        ru_title, ru_tags, new_ru, _ = build_ru(pair, ru_tpl)
        en_ok, en_diff, en_others = diff_of(L.get("description") or "", new_en, a.section)
        ru_ok, ru_diff, ru_others = diff_of(tru.get("description") or "", new_ru, a.section_ru)
        en_same = norm(L.get("description")) == norm(new_en)
        ru_same = norm(tru.get("description")) == norm(new_ru)
        if sample is None and (en_diff or ru_diff):
            sample = (pair, en_diff, ru_diff)
        if not (en_same or en_ok) or not (ru_same or ru_ok):
            res.append((pair, lid, "SIRA DISI", f"EN digerleri {'ayni' if en_others else 'FARKLI'}, RU digerleri {'ayni' if ru_others else 'FARKLI'}"))
            log(f"[{n}/{len(todo)}] {pair} {lid} SIRA DISI (sablon disi metin, atlandi)")
            continue
        if en_same and ru_same:
            res.append((pair, lid, "DEGISIM YOK", "-"))
            log(f"[{n}/{len(todo)}] {pair} {lid} degisim yok")
            continue
        if a.dry_run:
            res.append((pair, lid, "HAZIR", f"EN {'+' if not en_same else '='} RU {'+' if not ru_same else '='}"))
            log(f"[{n}/{len(todo)}] {pair} {lid} HAZIR (dry-run)")
            continue
        back_en = L
        if not en_same:
            r = api.patch(f"/shops/{shop}/listings/{lid}", {"description": new_en})
            back_en = r if isinstance(r, dict) and r.get("description") else (api.get(f"/listings/{lid}") or {})
        back_ru = tru
        if not ru_same:
            tbody = {"title": ru_title, "description": new_ru, "tags": ",".join(ru_tags)}
            r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru", tbody)
            back_ru = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
        ok_en = norm(back_en.get("description")) == norm(new_en)
        ok_ru = norm(back_ru.get("description")) == norm(new_ru) and back_ru.get("title") == ru_title
        res.append((pair, lid, "PASS" if (ok_en and ok_ru) else "FAIL", f"EN {'PASS' if ok_en else 'FAIL'}, RU {'PASS' if ok_ru else 'FAIL'}"))
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {pair} {lid} {'PASS' if (ok_en and ok_ru) else 'FAIL'} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s %{100 * n // len(todo)} | kota {api.remaining}")

    done = [r for r in res if r[2] == "PASS"]
    bad = [r for r in res if r[2] == "FAIL"]
    odd = [r for r in res if r[2] == "SIRA DISI"]
    kalan = [p for p, _ in todo[len(res):]] + [p for p, _ in rows[len(todo):]]
    md = [f"## POD aciklama guncelleme ({'APPLY' if a.apply else 'DRY-RUN'}) — bolum {a.section} / {a.section_ru}", "",
          f"- STATE: {len(rows)} verified ilan; islenen {len(res)}; PASS {len(done)}; FAIL {len(bad)}; sira disi {len(odd)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; kalan {len(kalan)}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    if sample:
        md += [f"### Diff ornegi ({sample[0]})", "", "```diff", sample[1] or "(EN fark yok)", "```", "```diff", sample[2] or "(RU fark yok)", "```", ""]
    md += ["| cift | listing_id | durum | not |", "|---|---|---|---|"]
    md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in res]
    if kalan:
        md += ["", f"Kalan ilanlar: {', '.join(kalan)}"]
    md += ["", f"**Kota once {q0} / sonra {api.remaining}**"]
    text = "\n".join(md)
    log(text)
    (out / "DESC_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "desc_result.json").write_text(json.dumps({"rows": res, "kalan": kalan, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False))
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
