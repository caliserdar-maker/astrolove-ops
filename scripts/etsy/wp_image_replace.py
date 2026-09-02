#!/usr/bin/env python3
"""
Tek listing gorselini yerel dosyayla DEGISTIRIR (ayni rank).

Guvenli yontem (B68/B70 dersleri): overwrite ASLA kullanilmaz.
  1) mevcut galeriyi oku, hedef rank'taki gorseli bul
  2) yeni dosyayi ayni rank ile YUKLE (Etsy eskisini bir alta kaydirir)
  3) kararlilik: 20 sn arayla iki okuma ayni olana kadar bekle
  4) eski gorseli SIL (image id ile), tekrar kararlilik
  5) son dogrulama: gorsel sayisi ayni, hedef rank'ta yeni id, boyut
Dry-run: yalniz okur, yerel dosyanin boyutunu ve mevcut durumu raporlar.

Kullanim:
  wp_image_replace.py --listing 4565911475 --rank 3 --file _work/new.jpg --min-size 3000x2250 [--apply]
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
"""
import argparse
import os
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402


def gallery(api, lid):
    res = api.get(f"/listings/{lid}/images") or {}
    rows = sorted(res.get("results", []), key=lambda x: x.get("rank", 0))
    return [(r.get("rank"), r.get("listing_image_id"), r.get("full_width"), r.get("full_height")) for r in rows]


def stable_gallery(api, lid, wait=20, tries=6):
    """Iki ardisik okuma ayni olana kadar bekler (B68 kural 5)."""
    prev = None
    for _ in range(tries):
        cur = gallery(api, lid)
        if prev is not None and cur == prev:
            return cur
        prev = cur
        time.sleep(wait)
    return prev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", required=True)
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--min-size", default="3000x2250")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    need_w, need_h = (int(v) for v in a.min_size.lower().split("x"))
    with Image.open(a.file) as im:
        w, h = im.size
        fmt = im.format
    log(f"Yerel dosya: {Path(a.file).name} {w}x{h} {fmt} {Path(a.file).stat().st_size} bayt")
    before = gallery(api, a.listing)
    log("Mevcut galeri (rank, image_id, w, h): " + "; ".join(str(r) for r in before))
    target = [r for r in before if r[0] == a.rank]
    if not target:
        raise SystemExit(f"HATA: rank {a.rank} bulunamadi.")
    old_rank, old_id, old_w, old_h = target[0]
    log(f"Hedef rank {a.rank}: image_id {old_id}, {old_w}x{old_h}")

    if (w, h) != (need_w, need_h):
        log(f"SONUC: yerel dosya {w}x{h}, beklenen {need_w}x{need_h} -> DEGISTIRME YAPILMAZ (yeniden render gerekir).")
        return 2
    if not a.apply:
        log("DRY-RUN: dosya standarda uygun; --apply ile rank "
            f"{a.rank}'e yuklenip eski {old_id} silinecek.")
        return 0

    n0 = len(before)
    log("Yukleniyor (rank ile, overwrite YOK)...")
    with open(a.file, "rb") as fh:
        res = api.post_file(f"/shops/{shop_id}/listings/{a.listing}/images",
                            files={"image": (Path(a.file).name, fh, "image/jpeg")},
                            data={"rank": str(a.rank)})
    new_id = res.get("listing_image_id")
    log(f"Yukleme cevabi image_id={new_id}")
    mid = stable_gallery(api, a.listing)
    log("Yukleme sonrasi galeri: " + "; ".join(str(r) for r in mid))
    ids = [r[1] for r in mid]
    if new_id not in ids or len(mid) != n0 + 1:
        raise SystemExit("HATA: yeni gorsel galeride gorunmedi veya sayi beklenen degil; eski gorsel SILINMEDI.")

    log(f"Eski gorsel siliniyor: {old_id}")
    api.delete(f"/shops/{shop_id}/listings/{a.listing}/images/{old_id}")
    after = stable_gallery(api, a.listing)
    log("Silme sonrasi galeri: " + "; ".join(str(r) for r in after))
    at_rank = [r for r in after if r[0] == a.rank]
    ok = (len(after) == n0 and at_rank and at_rank[0][1] == new_id
          and (at_rank[0][2], at_rank[0][3]) == (w, h) and old_id not in [r[1] for r in after])
    log(f"SONUC: {'PASS' if ok else 'FAIL'} | gorsel {len(after)} | rank {a.rank} id {at_rank[0][1] if at_rank else None} "
        f"{at_rank[0][2] if at_rank else ''}x{at_rank[0][3] if at_rank else ''} | api cagri {api.calls} | kota {api.remaining}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## Gorsel degisimi {a.listing} rank {a.rank}: {'PASS' if ok else 'FAIL'}\n\n"
                     f"- once: {before}\n- sonra: {after}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
