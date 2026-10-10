#!/usr/bin/env python3
"""3 ornek ilanin canli kapak gorselini (rank 1) SALT OKUR alir ve arama kucuk resmi boyutunda onizleme uretir.

Etsy API: yalniz GET /listings/{id}/images. Cikti (out/): <CIFT>_kapak_570.jpg, <CIFT>_kucuk_340x270.jpg
(Etsy CDN il_340x270 surumu; alinamazsa 570 gorselden merkez kirpma), KAPAK_UCLU_340x270.png (yan yana), kapak_ozet.json.
etsy-arama oturumu, 10 Eki 2026.
"""
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

ORNEK = [("CANCER_LEO", "4570143387", "satis alan"), ("CANCER_LIBRA", "4570143815", "en cok goruntulenen, satis yok"),
         ("ARIES_LEO", "4570031205", "53 goruntulenme, 0 favori")]
W, H = 340, 270


def indir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def kirp(img):
    sw, sh = img.size
    hedef = W / H
    if sw / sh > hedef:
        nw = int(sh * hedef)
        img = img.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    else:
        nh = int(sw / hedef)
        img = img.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
    return img.resize((W, H), Image.LANCZOS)


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    key, secret = os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"]
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    ozet, kucukler = [], []
    for cift, lid, neden in ORNEK:
        imgs = sorted((api.get(f"/listings/{lid}/images") or {}).get("results") or [], key=lambda x: x.get("rank") or 99)
        if not imgs:
            ozet.append({"cift": cift, "listing_id": lid, "durum": "gorsel yok"})
            continue
        i0 = imgs[0]
        u570 = i0.get("url_570xN") or i0.get("url_fullxfull")
        b570 = indir(u570)
        (out / f"{cift}_kapak_570.jpg").write_bytes(b570)
        kaynak = "CDN il_340x270"
        try:
            k = Image.open(io.BytesIO(indir(u570.replace("il_570xN", "il_340x270")))).convert("RGB")
            if k.size != (W, H):
                raise ValueError(k.size)
        except Exception as e:  # noqa: BLE001
            kaynak = f"570 gorselden merkez kirpma ({type(e).__name__})"
            k = kirp(Image.open(io.BytesIO(b570)).convert("RGB"))
        k.save(out / f"{cift}_kucuk_340x270.jpg", quality=92)
        kucukler.append(k)
        ozet.append({"cift": cift, "listing_id": lid, "neden": neden, "rank1_image_id": i0.get("listing_image_id"),
                     "gorsel_sayisi": len(imgs), "kucuk_kaynak": kaynak, "orijinal": f"{i0.get('full_width')}x{i0.get('full_height')}"})
        log(f"{cift}: {kaynak}")
    if kucukler:
        pay = 16
        sheet = Image.new("RGB", (len(kucukler) * W + (len(kucukler) + 1) * pay, H + 2 * pay), "white")
        for n, k in enumerate(kucukler):
            sheet.paste(k, (pay + n * (W + pay), pay))
        sheet.save(out / "KAPAK_UCLU_340x270.png")
    (out / "kapak_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"SONUC: {len(kucukler)}/3 kucuk resim; Etsy yazma cagrisi 0; API cagri {api.calls}")
    if len(kucukler) != 3:
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1])
