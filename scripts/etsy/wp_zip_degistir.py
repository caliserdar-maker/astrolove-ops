#!/usr/bin/env python3
"""
TEK DIJITAL DOSYAYI DEGISTIR (ETSY'YE YAZAR) - 5 Eyl 2026 Mo gorevi
(pilot Cancer_Libra 4565911475, yalniz AstroLove_Cancer_Libra_Warm_Parchment.zip).

Adimlar: dosya listesi (5 beklenir, hedef ad tam 1 kez) -> hedef dosyayi SIL
-> yeni dosyayi YUKLE (ayni rank) -> kararli geri okuma: 5 dosya, ad kumesi
ayni, yeni dosyanin size_bytes = yerel bayt; Etsy indirme URL'si donerse
sha256 birebir. Diger dosyalara DOKUNMAZ. Varsayilan DRY-RUN.
"""
import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def hedef_sec(files, ad):
    """Donus: (ok, detay, hedef_kayit)"""
    h = [f for f in files if str(f.get("filename") or "") == ad]
    det = []
    if len(files) != 5:
        det.append(f"dosya sayisi {len(files)} != 5")
    if len(h) != 1:
        det.append(f"hedef '{ad}' {len(h)} kez bulundu (1 beklenir)")
    return (not det), "; ".join(det), (h[0] if len(h) == 1 else None)


def indir(url):
    for k in range(3):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--file", required=True, help="yerel yeni ZIP (adi Etsy'deki hedef adla ayni)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    yerel = Path(a.file)
    ad = yerel.name
    veri = yerel.read_bytes()
    yerel_sha, yerel_boy = sha256(veri), len(veri)
    log(f"yerel: {ad} {yerel_boy} bayt sha256 {yerel_sha[:16]}...")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    lid = a.listing_id
    yol = f"/shops/{shop}/listings/{lid}/files"

    def files():
        return (api.get(yol, ok404=True) or {}).get("results", [])

    once = files()
    log("once: " + ", ".join(f"{f.get('filename')}({f.get('size_bytes')}b,r{f.get('rank')})" for f in once))
    ok, det, hedef = hedef_sec(once, ad)
    if not ok:
        log(f"ON-KONTROL FAIL: {det} -> YAZILMADI")
        return 1
    eski_boy = int(hedef.get("size_bytes") or 0)
    eski_url = hedef.get("url") or hedef.get("download_url") or ""
    if eski_boy == yerel_boy and eski_url:
        d = indir(eski_url)
        if d is not None and sha256(d) == yerel_sha:
            log("Etsy'deki dosya zaten yerel ile birebir (sha256 esit) -> YAZILMADI, PASS")
            return 0
    log(f"eski: id {hedef.get('listing_file_id')} {eski_boy} bayt rank {hedef.get('rank')} -> yerel {yerel_boy} bayt")
    if not a.apply:
        log("DRY-RUN: sil + yukle yapilacakti")
        return 0

    rank = hedef.get("rank") or 4
    diger = sorted(str(f.get("filename")) for f in once if f is not hedef)
    log(f"siliniyor: {hedef.get('listing_file_id')}")
    api.delete(f"{yol}/{hedef.get('listing_file_id')}")
    for _ in range(4):
        time.sleep(8)
        cur = files()
        if len(cur) == 4 and ad not in {f.get("filename") for f in cur}:
            break
    else:
        log(f"FAIL: silme sonrasi dosya {len(cur)}")
        return 1
    log(f"yukleniyor: {ad} rank {rank}")
    with open(yerel, "rb") as fh:
        r = api.post_file(yol, files={"file": (ad, fh, "application/zip")}, data={"name": ad, "rank": str(rank)})
    log(f"yuklendi: id {r.get('listing_file_id')} {r.get('size_bytes')} bayt")
    prev = None
    for _ in range(4):
        time.sleep(8)
        cur = files()
        if prev is not None and cur == prev and len(cur) == 5:
            break
        prev = cur
    sonra = files()
    adlar = sorted(str(f.get("filename")) for f in sonra)
    yeni = [f for f in sonra if f.get("filename") == ad]
    det = []
    if len(sonra) != 5:
        det.append(f"dosya {len(sonra)} != 5")
    if adlar != sorted(diger + [ad]):
        det.append(f"ad kumesi degisti {adlar}")
    if len(yeni) != 1:
        det.append(f"yeni dosya {len(yeni)} kez")
    else:
        yb = int(yeni[0].get("size_bytes") or 0)
        if yb != yerel_boy:
            det.append(f"size_bytes {yb} != yerel {yerel_boy}")
        url = yeni[0].get("url") or yeni[0].get("download_url") or ""
        if url:
            d = indir(url)
            if d is None:
                det.append("Etsy'den indirilemedi")
            elif sha256(d) != yerel_sha:
                det.append("sha256 FARKLI")
            else:
                log("sha256 Etsy == Drive: BIREBIR")
        else:
            log("not: Etsy dosya listesinde indirme URL'si yok; bayt kiyasi size_bytes ile")
    log("sonra: " + ", ".join(f"{f.get('filename')}({f.get('size_bytes')}b,r{f.get('rank')})" for f in sonra))
    log(f"SONUC {'PASS' if not det else 'FAIL: ' + '; '.join(det)} | kota {api.remaining}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## ZIP degistir {lid} {ad}: {'PASS' if not det else 'FAIL ' + '; '.join(det)} | dosya {len(sonra)}\n")
    return 0 if not det else 1


if __name__ == "__main__":
    sys.exit(main())
