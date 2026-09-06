#!/usr/bin/env python3
"""
POD ilanina 2 teknik kart + 1 video ekleme (EK 3, Mo 6 Eyl 2026). Mevcut ilan (or. 4570031205).

Akis:
  1. ON KONTROL: iki kart OCR (tesseract) -> dijitale ozgu ifade (download, instant, print at home,
     JPG/PDF, file) varsa kart YUKLENMEZ, raporlanir. Video 1080x1350 degilse yuklenmez.
  2. Mevcut galeri okunur (rank, id, url); her kare kaynak dosyasiyla PIKSEL karsilastirilir
     (gri 48x48 ortalama fark <= ESIK ve en yakin kaynak beklenen olmali). Beklenmeyen galeri -> DUR.
  3. Apply: 2 kart yuklenir (rank 4/5; galeride zaten varsa -piksel- id yeniden kullanilir),
     hedef sira id ile kurulur (uploadListingImage listing_image_id + rank), geri okuma 12/12
     id + piksel; video yoksa yuklenir, geri okuma 1.
  Mevcut gorsel SILINMEZ. Kota < --quota-min ise yazma yok.
Kullanim:
  pod_media_add.py --listing-id 4570031205 --pair ARIES_LEO --edition MIDNIGHT_BLUE
                   --images IMG --media MEDIA --out OUT --dry-run|--apply [--quota-min 400]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_create import DEFAULT_FRAMES, image_plan, media_plan, quota_ok  # noqa: E402
from pod_media import VIDEO_WH, img_sig, mp4_dims, sig_diff  # noqa: E402

PIX_MAX = 6.0          # gri 48x48 ortalama fark esigi (ayni gorsel yeniden kodlanmis: olculen en fazla 0.08)
READ_TRIES, READ_WAIT = 6, 4


def gallery(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    rows = [(x.get("rank") or 0, x.get("listing_image_id"), x.get("url_fullxfull") or x.get("url_570xN")) for x in r.get("results") or []]
    return sorted(rows, key=lambda t: t[0])


def videos(api, lid):
    r = api.get(f"/listings/{lid}/videos", ok404=True) or {}
    return [(v.get("video_id"), v.get("video_state")) for v in r.get("results") or []]


def stable(fn, want=None):
    prev = None
    for _ in range(READ_TRIES):
        cur = fn()
        if prev is not None and cur == prev and (want is None or want(cur)):
            return cur
        prev = cur
        time.sleep(READ_WAIT)
    return prev


def fetch_sig(url, cache):
    if url not in cache:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        cache[url] = img_sig(r.content)
    return cache[url]


def pixel_table(rows, sources, cache):
    """rows: [(rank, id, url)], sources: {rank: (path, sig)}. -> [(rank, id, kaynak, fark, en_yakin_rank, PASS)]"""
    out = []
    for rank, iid, url in rows:
        s = fetch_sig(url, cache)
        diffs = {rk: sig_diff(s, sg) for rk, (_, sg) in sources.items()}
        near = min(diffs, key=diffs.get) if diffs else None
        exp = sources.get(rank)
        d = diffs.get(rank)
        ok = exp is not None and d is not None and d <= PIX_MAX and near == rank
        out.append((rank, iid, exp[0].name if exp else "-", None if d is None else round(d, 2), near, ok))
    return out


def rerank(api, shop, lid, desired):
    """desired: {rank: image_id}. Ranklar artan sirada listing_image_id ile yeniden atanir."""
    cur = {r: i for r, i, _ in gallery(api, lid)}
    for r in sorted(desired):
        if cur.get(r) == desired[r]:
            continue
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, str(desired[r])), "rank": (None, str(r))})
        cur = {rr: i for rr, i, _ in gallery(api, lid)}
    return cur


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--edition", default="MIDNIGHT_BLUE")
    ap.add_argument("--images", required=True, help="<images>/<PAIR>/<ED>/NN_*.jpg (POD_GALLERY)")
    ap.add_argument("--media", required=True, help="<media>/<PAIR>/ kart + video")
    ap.add_argument("--frames", default=DEFAULT_FRAMES)
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=400)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    lid, pair, ed = a.listing_id, a.pair.upper(), a.edition
    frames = [f.strip() for f in a.frames.split(",") if f.strip()]
    md = [f"## EK 3 medya: {pair} {lid} ({'APPLY' if a.apply else 'DRY-RUN'})", ""]

    # 1. on kontrol
    media = media_plan(a.media, pair, ed)
    md += ["### On kontrol (kart OCR, video boyut)", "", "| oge | dosya | sonuc |", "|---|---|---|"]
    cards_ok = True
    for k in ("SYMBOL", "CRAFTED"):
        n, hits, note = media[k + "_words"], media[k + "_hits"], media[k + "_note"]
        p = media[k]
        if media.get(k + "_file") is None:
            md.append(f"| {k} | - | EKSIK (dosya yok) |"); cards_ok = False
        elif hits:
            md.append(f"| {k} | {media[k + '_file'].name} | FAIL: yasakli ifade {hits} ({n} kelime) -> YUKLENMEZ |"); cards_ok = False
        elif n is None:
            md.append(f"| {k} | {media[k + '_file'].name} | FAIL: OCR yok (tesseract kurulu degil) -> YUKLENMEZ |"); cards_ok = False
        else:
            md.append(f"| {k} | {p.name} | PASS ({n} kelime, yasakli ifade yok) |")
    vp = media["VIDEO"]
    vdims = mp4_dims(vp) if vp else None
    video_ok = bool(vp) and vdims == VIDEO_WH
    md.append(f"| VIDEO | {vp.name if vp else '-'} | {'PASS ' + str(vdims) if video_ok else ('EKSIK' if not vp else 'FAIL boyut ' + str(vdims) + ' != ' + str(VIDEO_WH))} |")
    md.append("")

    old_plan = image_plan(a.images, pair, ed, frames)             # mevcut 10'lu duzen
    new_plan = image_plan(a.images, pair, ed, frames, media if cards_ok else None)
    miss = [f"{e}/{k}" for _, e, p, _, k in old_plan if p is None]
    if miss:
        raise SystemExit(f"HATA: galeri kaynagi eksik: {miss}")
    src_old = {rk: (p, img_sig(p)) for rk, _, p, _, _ in old_plan}
    src_new = {rk: (p, img_sig(p)) for rk, _, p, _, _ in new_plan}

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    cache = {}

    # 2. mevcut galeri + piksel dogrulama
    before = gallery(api, lid)
    q_before = api.remaining
    (out / "gallery_before.json").write_text(json.dumps(before, indent=1))
    md += [f"### Mevcut galeri ({len(before)} gorsel, kota {q_before})", "", "| rank | image_id | beklenen kaynak | fark | en yakin | sonuc |", "|---|---|---|---|---|---|"]
    # kartlar zaten galeride mi (piksel)?
    card_sig = {k: img_sig(media[k]) for k in ("SYMBOL", "CRAFTED") if cards_ok}
    have_card = {}
    for k, sg in card_sig.items():
        cand = [(sig_diff(fetch_sig(url, cache), sg), iid) for rank, iid, url in before]
        if cand and min(cand)[0] <= PIX_MAX:
            have_card[k] = min(cand)[1]
    tbl = pixel_table(before, src_old if not have_card else src_new, cache)
    md += [f"| {r} | {i} | {src} | {d} | {n} | {'PASS' if ok else 'FAIL'} |" for r, i, src, d, n, ok in tbl]
    before_ok = all(t[5] for t in tbl) and len(before) == (len(old_plan) if not have_card else len(new_plan))
    md.append("")
    if have_card:
        md.append(f"Not: kart(lar) galeride zaten var (piksel): {have_card}; yeniden yuklenmez.")
    if not before_ok and not have_card:
        md.append("**HATA: mevcut galeri beklenen 10'lu duzenle eslesmiyor; yazma yok.**")
        finish(md, out, api, q_before); raise SystemExit(1)

    cur_vids = videos(api, lid)
    md.append(f"Mevcut video: {cur_vids or 'yok'}")
    md.append("")

    # hedef sira
    old_by_path = {p: i for (rk, _, p, _, _), (r2, i, _) in zip(old_plan, before)} if not have_card else {}
    plan_rows = []
    for rk, e, p, c, k in new_plan:
        plan_rows.append((rk, e, k, p.name, "YENI" if k in ("SYMBOL", "CRAFTED") and k not in have_card else "mevcut"))
    md += ["### Hedef sira (12 + video 1)", "", "| rank | edisyon | kare | dosya | islem |", "|---|---|---|---|---|"]
    md += [f"| {r} | {e} | {k} | {f} | {op} |" for r, e, k, f, op in plan_rows]
    md.append("")

    if a.dry_run:
        md.append("DRY-RUN: yazma yok.")
        finish(md, out, api, q_before); return
    if not quota_ok(api, a.quota_min):
        md.append(f"**KOTA {api.remaining} < {a.quota_min}: yazma yok.**")
        finish(md, out, api, q_before); raise SystemExit(1)

    # 3. yukleme + siralama
    new_ids = dict(have_card)
    if cards_ok:
        for k in ("SYMBOL", "CRAFTED"):
            if k in new_ids:
                continue
            p = media[k]
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            with open(p, "rb") as fh:
                r = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, mime)},
                                  data={"rank": str(next(rk for rk, _, _, _, kk in new_plan if kk == k))})
            new_ids[k] = r.get("listing_image_id")
            log(f"  yuklendi {k}: image_id {new_ids[k]}")
        md.append(f"Yukleme id'leri: {new_ids}")
        desired = {}
        for rk, e, p, c, k in new_plan:
            desired[rk] = new_ids[k] if k in new_ids else old_by_path.get(p)
            if desired[rk] is None:      # kartlar zaten vardi: mevcut id'yi piksel ile bul (en yakin, esik altinda)
                cand = [(sig_diff(fetch_sig(u, cache), src_new[rk][1]), i) for r2, i, u in before]
                d, i = min(cand) if cand else (None, None)
                desired[rk] = i if d is not None and d <= PIX_MAX else None
        if any(v is None for v in desired.values()):
            md.append(f"**HATA: hedef id eslemesi eksik: {desired}**"); finish(md, out, api, q_before); raise SystemExit(1)
        cur = rerank(api, shop, lid, desired)
        if any(cur.get(r) != i for r, i in desired.items()):
            cur = rerank(api, shop, lid, desired)      # ikinci ve son gecis
        after = stable(lambda: gallery(api, lid), want=lambda g: len(g) == len(desired))
        (out / "gallery_after.json").write_text(json.dumps(after, indent=1))
        tbl2 = pixel_table(after, src_new, cache)
        id_ok = {r: (i == desired.get(r)) for r, i, _ in after}
        md += ["### Geri okuma (id + piksel)", "", "| rank | image_id | id beklenen | kaynak | fark | en yakin | sonuc |", "|---|---|---|---|---|---|---|"]
        md += [f"| {r} | {i} | {'PASS' if id_ok.get(r) else 'FAIL'} | {src} | {d} | {n} | {'PASS' if ok and id_ok.get(r) else 'FAIL'} |" for r, i, src, d, n, ok in tbl2]
        gal_ok = len(after) == len(desired) and all(t[5] for t in tbl2) and all(id_ok.values())
        md.append(f"\nGaleri: {sum(1 for t in tbl2 if t[5])}/{len(desired)} {'PASS' if gal_ok else 'FAIL'}")
    else:
        gal_ok = False
        md.append("Kartlar yuklenmedi (on kontrol); sira degismedi.")

    # 4. video
    vid_ok = None
    if video_ok:
        if not cur_vids:
            with open(vp, "rb") as fh:
                r = api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (vp.name, fh, "video/mp4")}, data={"name": vp.name})
            log(f"  video yuklendi: {r.get('video_id')} {r.get('video_state')}")
        vids = stable(lambda: videos(api, lid), want=lambda v: len(v) == 1)
        vid_ok = len(vids) == 1
        md.append(f"Video: {vids} -> {'PASS' if vid_ok else 'FAIL'} (beklenen 1)")
    else:
        md.append("Video yuklenmedi (on kontrol/eksik).")
    finish(md, out, api, q_before)
    if not (gal_ok and vid_ok):
        raise SystemExit(1)


def finish(md, out, api, q_before):
    md.append(f"\nKota once {q_before} / sonra {api.remaining}")
    text = "\n".join(md)
    log(text)
    (out / "MEDIA_REPORT.md").write_text(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


if __name__ == "__main__":
    main()
