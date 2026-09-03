#!/usr/bin/env python3
"""
DENETIM (SALT OKUR): yuklenmis ilanlarin rank=1 (SET01) galeri gorselinin
GERCEKTE hangi cifte ait oldugunu, Etsy'den indirip 78 ciftin kendi SET01
referanslariyla imza eslestirerek (verify_listing.py'deki B68 yontemi,
degistirilmeden) bulur ve STATE'teki beklenen ciftle karsilastirir.

Etsy dosya adini geri VERMEZ (GET /listings/{id}/images alaninda filename
yok); bu yuzden goruntu icerigi karsilastirilir. Etsy'ye hicbir yazma
cagrisi yapilmaz (token yenileme haric, digerleriyle ayni kural).

Kullanim:
  wp_audit_pair_id.py --state uploaded.csv --refs _work/refs --out audit.csv
"""
import csv
import io
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, TIMEOUT, log, mask  # noqa: E402
from verify_listing import signature  # noqa: E402


def load_refs(refs_dir):
    """_work/refs/<PAIR>/WA_MOCKUP_V2_SET01_..._FINAL.jpg -> {PAIR: sig}."""
    out = {}
    for d in sorted(Path(refs_dir).iterdir()):
        if not d.is_dir():
            continue
        files = list(d.glob("WA_MOCKUP_V2_SET01_*_FINAL.jpg"))
        if not files:
            continue
        out[d.name] = signature(files[0].read_bytes())
    return out


def best_match(sig, refs):
    import numpy as np
    scores = sorted(((float(np.sum(sig * s)), pair) for pair, s in refs.items()), reverse=True)
    return scores[0], (scores[1] if len(scores) > 1 else (0.0, ""))


def read_uploaded(path):
    """pair,listing_id,... CSV (WP_UPLOAD_STATE.csv basligi) -> [(pair, listing_id, status)]."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.reader(fh):
            if len(r) >= 6 and r[0] != "pair" and r[1].strip().isdigit():
                rows.append((r[0].strip(), r[1].strip(), r[5].strip()))
    return rows


def main():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--state", required=True, help="WP_UPLOAD_STATE.csv (yuklenen ciftler)")
    ap.add_argument("--refs", required=True, help="_work/refs/<PAIR>/WA_MOCKUP_V2_SET01_*_FINAL.jpg")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    refs = load_refs(a.refs)
    log(f"referans: {len(refs)} cift ({a.refs})")
    uploaded = read_uploaded(a.state)
    log(f"kontrol edilecek: {len(uploaded)} ilan (yukleme STATE'inde gorunen tumu)")

    out = []
    t0 = time.time()
    for i, (pair, lid, up_status) in enumerate(uploaded):
        r = api.get(f"/listings/{lid}/images", ok404=True) or {}
        imgs = sorted(r.get("results", []), key=lambda x: x.get("rank") or 999)
        rank1 = next((im for im in imgs if im.get("rank") == 1), None)
        row = dict(pair=pair, listing_id=lid, upload_status=up_status, images=len(imgs))
        if not rank1:
            row.update(sonuc="FAIL", detay="rank=1 gorsel yok")
            out.append(row); log(f"[{i+1}/{len(uploaded)}] {pair} {lid}: FAIL (rank=1 gorsel yok)")
            continue
        url = rank1.get("url_570xN") or rank1.get("url_fullxfull")
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            row.update(sonuc="FAIL", detay=f"gorsel indirilemedi {resp.status_code}")
            out.append(row); log(f"[{i+1}/{len(uploaded)}] {pair} {lid}: FAIL (indirme {resp.status_code})")
            continue
        sig = signature(resp.content)
        (score, matched_pair), (score2, matched2) = best_match(sig, refs)
        dogru = matched_pair.strip().lower() == pair.strip().lower()
        row.update(matched_pair=matched_pair, score=f"{score:.4f}",
                    second_pair=matched2, second_score=f"{score2:.4f}",
                    sonuc="DOGRU" if dogru else "YANLIS", detay="")
        out.append(row)
        el = time.time() - t0
        log(f"[{i+1}/{len(uploaded)}] {pair} {lid}: {'DOGRU' if dogru else 'YANLIS -> ' + matched_pair} "
            f"(skor {score:.3f}) | gecen {el/60:.1f} dk kalan {el/(i+1)*(len(uploaded)-i-1)/60:.1f} dk")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pair", "listing_id", "upload_status", "images", "matched_pair", "score",
                     "second_pair", "second_score", "sonuc", "detay"])
        for r in out:
            w.writerow([r.get(k, "") for k in ("pair", "listing_id", "upload_status", "images",
                        "matched_pair", "score", "second_pair", "second_score", "sonuc", "detay")])

    dogru = sum(1 for r in out if r.get("sonuc") == "DOGRU")
    yanlis = [r for r in out if r.get("sonuc") in ("YANLIS", "FAIL")]
    log(f"SONUC denetim: {dogru}/{len(out)} DOGRU | {len(yanlis)} SORUNLU")
    for r in yanlis:
        log(f"  SORUNLU: ilan {r['listing_id']} | STATE cifti {r['pair']} | "
            f"gercek eslesme {r.get('matched_pair', '?')} (skor {r.get('score', '?')}) | {r.get('detay', '')}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## cift-kimlik denetimi: {dogru}/{len(out)} DOGRU\n\n")
            if yanlis:
                fh.write("| ilan_id | STATE cifti | gercek eslesme | skor | detay |\n|---|---|---|---|---|\n")
                for r in yanlis:
                    fh.write(f"| {r['listing_id']} | {r['pair']} | {r.get('matched_pair', '?')} | "
                             f"{r.get('score', '?')} | {r.get('detay', '')} |\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
