#!/usr/bin/env python3
"""Musteri jesti oncesi SALT OKUMA kontrolu: POD_PRINT baski dosyasi, siparisteki tasarimla ayni mi?
Karsilastirilan: (1) Prodigi siparisinin gercek baski asset'i (GET /orders/{id}; kanal siparisi), (2) Etsy islemindeki
ilan gorseli (receipt -> transaction.listing_image_id; silinmisse yok). Etsy/Prodigi'ye YAZMA YOK; kisisel veri yazilmaz
(receipt yalniz son 4 hane, alici bilgisi okunmaz/yazilmaz).
Olcum: POD_PRINT vs Prodigi asset gri NCC (ayni oran, 600 px) >= ESIK; OCR (tesseract) ile slogan ve burc adlari.
Cikti: OUT/KONTROL.json + OUT/KARSILASTIRMA.jpg. Karar AYNI | FARKLI | OLCULEMEDI.
Kullanim: dijital_jest_kontrol.py --baski F.jpg --receipt ID --sku SKU --prodigi-oid ord_.. --out OUT [--slogan "Two Souls"]
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy")); sys.path.insert(0, str(KOK / "scripts/prodigi"))
ESIK = 0.95


def gri(im, w=600):
    im = im.convert("L")
    return np.asarray(im.resize((w, round(w * im.height / im.width)), Image.LANCZOS), dtype=np.float32)


def ncc(a, b):
    h = min(a.shape[0], b.shape[0]); a, b = a[:h], b[:h]
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def ocr(im):
    buf = io.BytesIO(); im.convert("L").save(buf, "PNG")
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11"], input=buf.getvalue(), capture_output=True)
    return re.sub(r"\s+", " ", r.stdout.decode("utf-8", "ignore")).upper()


def indir(url):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baski", required=True); ap.add_argument("--receipt", required=True); ap.add_argument("--sku", required=True)
    ap.add_argument("--prodigi-oid", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--slogan", default="SOULS|ONE BOND"); ap.add_argument("--adlar", default="AQUARIUS,SCORPIO")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    son4 = a.receipt[-4:]
    B = Image.open(a.baski); sonuc = {"receipt_son4": son4, "sku": a.sku, "baski_boyut": list(B.size)}
    goruntu = [("POD_PRINT baski dosyasi", B)]
    # (1) Prodigi gercek baski asset'i
    P = None
    if a.prodigi_oid:
        import order_router as R
        prod = R.Prodigi(R.load_prodigi_key("live"), "live")
        st, d = prod.get_order(a.prodigi_oid)
        urls = [x.get("url") for k in ((d.get("order") or {}).get("items") or []) for x in (k.get("assets") or []) if x.get("url")]
        sonuc["prodigi"] = {"http": st, "asset_sayisi": len(urls)}
        if urls:
            try:
                P = indir(urls[0]); goruntu.append(("Prodigi'nin bastigi asset", P))
                sonuc["prodigi"].update(boyut=list(P.size), ncc=round(ncc(gri(B), gri(P)), 4),
                                        oran_baski=round(B.width / B.height, 4), oran_asset=round(P.width / P.height, 4))
            except Exception as e:  # noqa: BLE001
                sonuc["prodigi"]["hata"] = f"{type(e).__name__}: {str(e)[:120]}"
    # (2) Etsy islemindeki ilan gorseli
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    rc = api.get(f"/shops/{shop}/receipts/{a.receipt}") or {}
    tx = [t for t in rc.get("transactions") or [] if (t.get("sku") or "").startswith(a.sku.rsplit("-", 1)[0])]
    sonuc["etsy"] = {"islem": len(tx)}
    if tx:
        t = tx[0]
        sonuc["etsy"].update(sku=t.get("sku"), varyasyon=[f"{v.get('formatted_name')}: {v.get('formatted_value')}" for v in t.get("variations") or []])
        sonuc["etsy"].update(listing_id=t.get("listing_id"), listing_image_id=t.get("listing_image_id"))
        img = api.get(f"/listings/{t.get('listing_id')}/images/{t.get('listing_image_id')}", ok404=True) if t.get("listing_image_id") else None
        if img and img.get("url_fullxfull"):
            E = indir(img["url_fullxfull"]); goruntu.append(("Siparisteki ilan gorseli", E))
            sonuc["etsy"]["gorsel"] = list(E.size)
        else:
            # Etsy'den silinmis: kapak/galeri yedeklerinde (<listing>_<image>.jpg) ara
            yd = out.parent / "_yedek_ara"
            subprocess.run(["rclone", "copy", "gdrive:ASTROLOVE/TEMP", str(yd), "--include", f"*YEDEK*/**{t.get('listing_image_id')}*.jpg", "-q"])
            bul = sorted(yd.rglob(f"*{t.get('listing_image_id')}*.jpg"))
            if bul:
                E = Image.open(bul[0]); goruntu.append(("Siparisteki ilan gorseli (Drive yedegi)", E))
                sonuc["etsy"]["gorsel"] = f"yedekten: {bul[0].relative_to(yd)} {list(E.size)}"
            else:
                sonuc["etsy"]["gorsel"] = "Etsy'de silinmis, yedekte yok"
    # OCR
    for ad, im in goruntu:
        t = ocr(im)
        sonuc.setdefault("ocr", {})[ad] = {"slogan": all(w in t for w in a.slogan.upper().split("|")), **{x: x in t for x in a.adlar.split(",")},
                                           "metin": t[:300]}
    # karar
    pn = (sonuc.get("prodigi") or {}).get("ncc")
    slog = {ad: v["slogan"] for ad, v in sonuc["ocr"].items()}
    if pn is None and len(goruntu) < 2:
        karar = "OLCULEMEDI"
    elif (pn is not None and pn < ESIK) or not slog.get("POD_PRINT baski dosyasi"):
        karar = "FARKLI"
    else:
        karar = "AYNI"
    sonuc["karar"], sonuc["esik_ncc"] = karar, ESIK
    # karsilastirma gorseli
    H = 900
    ks = [im.convert("RGB").resize((round(H * im.width / im.height), H), Image.LANCZOS) for _, im in goruntu]
    T = Image.new("RGB", (sum(x.width for x in ks) + 20 * (len(ks) + 1), H + 90), (255, 255, 255)); d = ImageDraw.Draw(T); x = 20
    for (ad, _), im in zip(goruntu, ks):
        T.paste(im, (x, 70)); d.text((x, 45), ad, fill=(0, 0, 0)); x += im.width + 20
    d.text((20, 12), f"...{son4} {a.sku} | karar {karar} | NCC(baski, Prodigi) {pn} | slogan {slog}", fill=(0, 0, 0))
    T.save(out / "KARSILASTIRMA.jpg", quality=88)
    (out / "KONTROL.json").write_text(json.dumps(sonuc, indent=1, ensure_ascii=False))
    print(f"KARAR {karar} | NCC {pn} | slogan {slog} | etsy {sonuc['etsy'].get('gorsel')} | kota {api.remaining}", flush=True)
    return 0 if karar != "OLCULEMEDI" else 2


if __name__ == "__main__":
    sys.exit(main())
