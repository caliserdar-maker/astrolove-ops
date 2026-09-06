#!/usr/bin/env python3
"""
POD taslaklarini YAYINA alir (Mo 6 Eyl 2026: ornek parti 5 ilan; kalan taslaklar Mo onayini bekler).

Her ilan icin ONCE ON KONTROL (salt okur), sonra yayin:
  - state draft mi (active ise atlanir, "zaten yayinda"),
  - 12 gorsel, 1 video, 65 varyant (EDITIONS x SIZES),
  - shop_section_id / shipping_profile_id / return_policy_id beklenen degerlerde,
  - baslik ve 13 etiket dolu.
Eksik olan ilan YAYINLANMAZ, raporlanir; kosu devam eder. Yayin: updateListing state=active;
geri okuma cevaptaki state (yoksa GET). Kota --quota-min altina inince durur, kalanlar raporlanir.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_publish.py --state STATE.csv --out OUT --limit 5 --dry-run|--apply [--quota-min 400]
          [--section-id 60204164 --shipping-profile-id 314711751541 --return-policy-id 1513990287785]
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
from pod_listing_create import EDITIONS, SIZES  # noqa: E402

N_IMAGES, N_VIDEOS, N_TAGS = 12, 1, 13
N_PRODUCTS = len(EDITIONS) * len(SIZES)
SECTION_ID, SHIPPING_ID, RETURN_ID = 60204164, 314711751541, 1513990287785


def read_state(path):
    rows = []
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                    rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


def precheck(api, shop, lid, a):
    """(hazir_mi, durum_metni, ayrinti_dict) - salt okur."""
    L = api.get(f"/listings/{lid}") or {}
    imgs = (api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or []
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    inv = api.get(f"/listings/{lid}/inventory") or {}
    d = {"state": L.get("state"), "images": len(imgs), "videos": len(vids),
         "products": len(inv.get("products") or []), "section": L.get("shop_section_id"),
         "shipping": L.get("shipping_profile_id"), "return": L.get("return_policy_id"),
         "title": bool(L.get("title")), "tags": len(L.get("tags") or [])}
    bad = []
    if d["images"] != N_IMAGES:
        bad.append(f"gorsel {d['images']}/{N_IMAGES}")
    if d["videos"] != N_VIDEOS:
        bad.append(f"video {d['videos']}/{N_VIDEOS}")
    if d["products"] != N_PRODUCTS:
        bad.append(f"varyant {d['products']}/{N_PRODUCTS}")
    if d["section"] != a.section_id:
        bad.append(f"bolum {d['section']}")
    if d["shipping"] != a.shipping_profile_id:
        bad.append(f"kargo {d['shipping']}")
    if a.return_policy_id and d["return"] != a.return_policy_id:
        bad.append(f"iade {d['return']}")
    if not d["title"] or d["tags"] != N_TAGS:
        bad.append(f"baslik/tag {d['title']}/{d['tags']}")
    return (not bad), ("; ".join(bad) or "hazir"), d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=5, help="en fazla N ilan yayinlanir (0 = hepsi)")
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--section-id", type=int, default=SECTION_ID)
    ap.add_argument("--shipping-profile-id", type=int, default=SHIPPING_ID)
    ap.add_argument("--return-policy-id", type=int, default=RETURN_ID)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows = read_state(a.state)
    if not rows:
        raise SystemExit(f"HATA: STATE'te verified ilan yok: {a.state}")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    res, q0, t0, stopped, published = [], None, time.time(), None, 0
    hedef = a.limit or len(rows)
    for n, (pair, lid) in enumerate(rows, 1):
        if published >= hedef:
            break
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = pair
            log(f"KOTA {rem} < {a.quota_min}: {pair} ve sonrasi islenmedi")
            break
        ok, note, d = precheck(api, shop, lid, a)
        if q0 is None:
            q0 = api.remaining
        if d["state"] == "active":
            res.append((pair, lid, "ZATEN YAYINDA", "-"))
            log(f"[{n}] {pair} {lid} zaten yayinda, atlandi")
            continue
        if not ok:
            res.append((pair, lid, "EKSIK", note))
            log(f"[{n}] {pair} {lid} EKSIK: {note} -> yayinlanmadi")
            continue
        if a.dry_run:
            published += 1
            res.append((pair, lid, "HAZIR", f"gorsel {d['images']}, video {d['videos']}, varyant {d['products']}"))
            log(f"[{published}/{hedef}] {pair} {lid} HAZIR (dry-run)")
            continue
        r = api.patch(f"/shops/{shop}/listings/{lid}", {"state": "active"})
        back = r if isinstance(r, dict) and r.get("state") else (api.get(f"/listings/{lid}") or {})
        st = back.get("state")
        published += 1
        res.append((pair, lid, "PASS" if st == "active" else "FAIL", f"state {st}"))
        el = time.time() - t0
        log(f"[{published}/{hedef}] {pair} {lid} {'PASS' if st == 'active' else 'FAIL'} state={st} | "
            f"gecen {el:.0f}s kalan~{el / published * (hedef - published):.0f}s %{100 * published // hedef} | kota {api.remaining}")

    done = [r for r in res if r[2] == "PASS"]
    bad = [r for r in res if r[2] == "FAIL"]
    eksik = [r for r in res if r[2] == "EKSIK"]
    md = [f"## POD yayin ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- STATE {len(rows)} verified; hedef {hedef}; yayinlanan {len(done)}; FAIL {len(bad)}; eksik {len(eksik)}; "
          f"zaten yayinda {sum(1 for r in res if r[2] == 'ZATEN YAYINDA')}"
          + (f"; KOTA {api.remaining} < {a.quota_min} ({stopped} ve sonrasi islenmedi)" if stopped else ""), "",
          "| cift | listing_id | durum | not |", "|---|---|---|---|"]
    md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in res]
    md += ["", f"**Kota once {q0} / sonra {api.remaining}**"]
    text = "\n".join(md)
    log(text)
    (out / "PUBLISH_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "publish_result.json").write_text(json.dumps({"rows": res, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False))
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
