#!/usr/bin/env python3
"""
POD ilanlarinin RU ETIKETLERINI yeni kurala esitler (Mo 7 Eyl 2026).

Kural: "<burc1> <burc2> постер" 20 karaktere sigiyorsa aynen kalir; sigmiyorsa "постер" DUSER
("<burc1> <burc2>"). Bu da sigmiyorsa ilan GUNCELLENMEZ, raporlanir (kendi basimiza kisaltma yok).

Her ilan icin: GET translations/ru -> sablondan uretilen etiketlerle karsilastir.
  - Fark yalnizca CIFT ETIKETINDE (2. etiket) olmali; baska etiket/baslik/aciklama farkliysa ilan
    ATLANIR ("SIRA DISI").
  - Yazma: PUT translations/ru; baslik ve aciklama Etsy'den okunan degerle BIREBIR geri gonderilir,
    yalnizca tags degisir.
  - Geri okuma: 13 etiket, hepsi <= 20 karakter, yalnizca hedef etiket degismis, baslik/aciklama ayni.
RU yazim denetimi (spylls/hunspell) yeni etiketler icin kosuda bir kez yapilir (--ru-dict).
Kota --quota-min altina inince durur, kalan ilanlar raporlanir. ETA sayaci her ilanda.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_ru_tags.py --state STATE.csv --out OUT --dry-run|--apply [--limit N] [--quota-min 400] [--ru-dict dict/ru_RU]
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import MAX_TAG_RU, build_ru, load_ru_template, spellcheck_ru  # noqa: E402
from wp_listing_update import norm  # noqa: E402

N_TAGS = 13
PAIR_TAG_INDEX = 1                # sablonda 2. etiket cift etiketidir


def read_state(path):
    rows = []
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                    rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


def tags_of(obj):
    return [str(t).strip() for t in (obj.get("tags") or []) if str(t).strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--ru-dict", default="")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = read_state(a.state)
    if not rows:
        raise SystemExit(f"HATA: STATE'te verified ilan yok: {a.state}")
    ru_tpl = load_ru_template()
    todo = rows[:a.limit] if a.limit else rows
    exp = {pair: build_ru(pair, ru_tpl) for pair, _ in todo}          # (title, tags, desc, note)
    if a.ru_dict:                                                     # yeni etiketlerin yazimi (bir kez, offline)
        spellcheck_ru(a.ru_dict, sorted({t[1][PAIR_TAG_INDEX] for t in exp.values()}))

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    res, q0, t0, stopped = [], None, time.time(), None

    for n, (pair, lid) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = pair
            log(f"KOTA {rem} < {a.quota_min}: {pair} ve sonrasi islenmedi")
            break
        cur = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        if q0 is None:
            q0 = api.remaining
        e_title, e_tags, e_desc, note = exp[pair]
        cur_tags = tags_of(cur)
        over = [t for t in e_tags if len(t) > MAX_TAG_RU]
        if over:                                                      # kural: kisaltma yapma, raporla
            res.append((pair, lid, "SIGMIYOR", f"{over[0]} ({len(over[0])} karakter) - elle karar gerekir"))
            log(f"[{n}/{len(todo)}] {pair} {lid} SIGMIYOR: {over}")
            continue
        diff = [i for i in range(max(len(cur_tags), len(e_tags))) if cur_tags[i:i + 1] != e_tags[i:i + 1]]
        same_text = cur.get("title") == e_title and norm(cur.get("description")) == norm(e_desc)
        if not diff:
            res.append((pair, lid, "DEGISIM YOK", cur_tags[PAIR_TAG_INDEX] if len(cur_tags) > PAIR_TAG_INDEX else "-"))
            log(f"[{n}/{len(todo)}] {pair} {lid} degisim yok")
            continue
        if diff != [PAIR_TAG_INDEX] or len(cur_tags) != N_TAGS or not same_text:
            res.append((pair, lid, "SIRA DISI",
                        f"farkli alan(lar): etiket {diff}, etiket sayisi {len(cur_tags)}, "
                        f"baslik/aciklama {'ayni' if same_text else 'FARKLI'} - atlandi"))
            log(f"[{n}/{len(todo)}] {pair} {lid} SIRA DISI (beklenmeyen fark, atlandi)")
            continue
        eski, yeni = cur_tags[PAIR_TAG_INDEX], e_tags[PAIR_TAG_INDEX]
        if a.dry_run:
            res.append((pair, lid, "HAZIR", f"{eski} ({len(eski)}) -> {yeni} ({len(yeni)})"))
            log(f"[{n}/{len(todo)}] {pair} {lid} HAZIR: {eski} -> {yeni}")
            continue
        body = {"title": cur.get("title") or "", "description": cur.get("description") or "", "tags": ",".join(e_tags)}
        r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru", body)
        back = r if isinstance(r, dict) and r.get("tags") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
        b_tags = tags_of(back)
        ok = (b_tags == e_tags and len(b_tags) == N_TAGS and all(len(t) <= MAX_TAG_RU for t in b_tags)
              and back.get("title") == cur.get("title") and norm(back.get("description")) == norm(cur.get("description")))
        res.append((pair, lid, "PASS" if ok else "FAIL", f"{eski} ({len(eski)}) -> {yeni} ({len(yeni)})"))
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {pair} {lid} {'PASS' if ok else 'FAIL'} {eski} -> {yeni} | "
            f"gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s %{100 * n // len(todo)} | kota {api.remaining}")

    done = [r for r in res if r[2] == "PASS"]
    hazir = [r for r in res if r[2] == "HAZIR"]
    bad = [r for r in res if r[2] in ("FAIL", "SIRA DISI", "SIGMIYOR")]
    kalan = [p for p, _ in todo[len(res):]] + [p for p, _ in rows[len(todo):]]
    md = [f"## POD RU etiket duzeltmesi ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- STATE {len(rows)} ilan; islenen {len(res)}; degisecek/degisen {len(done) or len(hazir)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; sorunlu {len(bad)}; kalan {len(kalan)}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    degisen = [r for r in res if r[2] in ("PASS", "HAZIR", "FAIL")]
    if degisen:
        md += ["| cift | listing_id | durum | eski -> yeni |", "|---|---|---|---|"]
        md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in degisen]
    if bad:
        md += ["", "### Sorunlu", "", "| cift | listing_id | durum | not |", "|---|---|---|---|"]
        md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in bad]
    if kalan:
        md += ["", f"Kalan ilanlar: {', '.join(kalan)}"]
    md += ["", f"**Kota once {q0} / sonra {api.remaining}**"]
    text = "\n".join(md)
    log(text)
    (out / "RU_TAGS_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "ru_tags_result.json").write_text(json.dumps({"rows": res, "kalan": kalan, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False))
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
