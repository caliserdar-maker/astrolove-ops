#!/usr/bin/env python3
"""Tek siparis icin ELDEN Prodigi gonderimi (panel yuklemesi takildiginda; Serdar onayi).

  hazirla : baski dosyasina gecici 'anyone:reader' izni verir, dogrudan indirme URL'sini
            uretir, dosyayi indirip PIKSEL dogrular (beklenen olcu, Drive md5, oran),
            onizleme kareyi Drive'a yazar ve Prodigi TEKLIFINI alir. SIPARIS YOK.
  gonder  : ayni adimlar + CANLI Prodigi siparisi (idempotencyKey) + siparisi geri okur.
            --confirm <merchantReference> zorunlu.

Ornek:
  manuel_siparis.py gonder --file-id 1oEk... --remote "gdrive:ASTROLOVE/TEMP/POD_PRINT/AQUARIUS_LIBRA/MIDNIGHT_BLUE/8x10.jpg" \
    --sku GLOBAL-HPR-8x10 --adet 1 --ref etsy-1000000001-8x10 --alici "MUSTERI_ADI" \
    --adres1 "ADRES" --sehir SEHIR --eyalet NH --posta POSTAKODU --ulke US \
    --olcu 2400x3000 --confirm etsy-1000000001-8x10
Ortam: rclone.conf (Drive), PRODIGI_API_KEY ya da Drive TEMP/PRODIGI_TOKEN.json.
"""
import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import requests
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "pinterest"))
from order_router import Prodigi, load_prodigi_key  # noqa: E402
from pin_media_perms import Drive, access_token  # noqa: E402

Image.MAX_IMAGE_PIXELS = None   # master dosyalari 12500x15625 (PIL bomba esigi asiliyor)
DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.1f}s] {m}", flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["onizleme", "hazirla", "gonder"])
    ap.add_argument("--file-id", required=True)
    ap.add_argument("--remote", required=True, help="dosyanin Drive yolu (cift/edisyon/boy kaniti)")
    ap.add_argument("--sku", required=True)
    ap.add_argument("--adet", type=int, default=1)
    ap.add_argument("--ref", required=True, help="merchantReference = idempotencyKey")
    ap.add_argument("--alici", required=True)
    ap.add_argument("--adres1", required=True)
    ap.add_argument("--adres2", default="")
    ap.add_argument("--sehir", required=True)
    ap.add_argument("--eyalet", default="")
    ap.add_argument("--posta", required=True)
    ap.add_argument("--ulke", default="US")
    ap.add_argument("--kargo", default="Budget")
    ap.add_argument("--olcu", default="2400x3000")
    ap.add_argument("--master", default="", help="dogrulama icin ORIGINAL_HIGH_RES master yolu")
    ap.add_argument("--kontrol", default="", help="ayni yapida BASKA cift master (ayirt edicilik kanti)")
    ap.add_argument("--env", default="live", choices=["live", "sandbox"])
    ap.add_argument("--confirm", default="")
    ap.add_argument("--is-dizin", default="_work/manuel")
    a = ap.parse_args()
    if a.mod == "gonder" and a.confirm != a.ref:
        raise SystemExit(f"DUR: gonder icin --confirm {a.ref} gerekir")
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    bek_w, bek_h = (int(x) for x in a.olcu.lower().split("x"))

    if a.mod == "onizleme":       # yalniz gozle dogrulama karesi; API cagrisi yok
        yerel = isd / "kaynak.jpg"
        rclone("copyto", a.remote, str(yerel))
        im = Image.open(yerel)
        im.load()
        hedef = isd / "ONIZLEME_SIPARIS.jpg"
        kucuk = im.convert("RGB").resize((600, round(600 * im.size[1] / im.size[0])), Image.LANCZOS)
        for kal in (88, 82, 76, 70, 62):
            kucuk.save(hedef, "JPEG", quality=kal, optimize=True)
            if hedef.stat().st_size <= 150_000:
                break
        rclone("copyto", str(hedef), f"{DRV}/ONIZLEME_SIPARIS.jpg")
        log(f"kaynak {a.remote} | {im.size[0]}x{im.size[1]} -> onizleme {kucuk.size[0]}x{kucuk.size[1]} "
            f"{hedef.stat().st_size / 1024:.0f} KB (kalite {kal}) -> {DRV}/ONIZLEME_SIPARIS.jpg")
        return 0

    # ---------------------------------------------------------- 1) dosya kimligi (Drive)
    kayit = json.loads(rclone("lsjson", a.remote).stdout)
    if len(kayit) != 1:
        raise SystemExit(f"HATA: {a.remote}: {len(kayit)} kayit")
    k = kayit[0]
    if k["ID"] != a.file_id:
        raise SystemExit(f"DUR: dosya kimligi uyusmuyor: Drive {k['ID']} != verilen {a.file_id}")
    log(f"dosya: {a.remote} | id {k['ID']} | {k['Size'] / 1e6:.2f} MB | md5 {k.get('Hashes', {}).get('md5', '-')}")

    # ---------------------------------------------------------- 2) gecici genel okuma izni + URL
    d = Drive(access_token())
    izin = d.create_anyone(a.file_id, "reader")
    url = f"https://drive.google.com/uc?export=download&id={a.file_id}&confirm=t"
    log(f"gecici izin verildi (anyone:reader, id {izin['id']}) -> URL hazir")

    # ---------------------------------------------------------- 3) URL'den indir + piksel dogrulama
    r = requests.get(url, timeout=180)
    if r.status_code != 200 or not r.content[:2] == b"\xff\xd8":
        raise SystemExit(f"DUR: URL indirilemedi (HTTP {r.status_code}, {len(r.content)} bayt)")
    md5 = hashlib.md5(r.content).hexdigest()
    im = Image.open(io.BytesIO(r.content))
    im.load()
    drive_md5 = (k.get("Hashes") or {}).get("md5")
    hata = []
    if im.size != (bek_w, bek_h):
        hata.append(f"olcu {im.size} != ({bek_w}, {bek_h})")
    if drive_md5 and md5 != drive_md5:
        hata.append(f"md5 {md5} != Drive {drive_md5}")
    if len(r.content) != int(k["Size"]):
        hata.append(f"bayt {len(r.content)} != {k['Size']}")
    if hata:
        raise SystemExit("DUR: dosya dogrulama: " + "; ".join(hata))
    onizleme = isd / "SIPARIS_ONIZLEME.jpg"
    im.convert("RGB").resize((480, round(480 * im.size[1] / im.size[0]))).save(onizleme, "JPEG", quality=85)
    rclone("copyto", str(onizleme), f"{DRV}/SIPARIS_ONIZLEME.jpg")
    log(f"URL dogrulandi: {im.size[0]}x{im.size[1]} JPEG, md5 Drive ile ayni, {len(r.content) / 1e6:.2f} MB "
        f"| onizleme {DRV}/SIPARIS_ONIZLEME.jpg")

    # ---------------------------------------------------------- 3b) icerik kaniti: master ile piksel karsilastirmasi
    olcumler = {}
    if a.master:
        def kucult(p):
            g = Image.open(p)
            g.draft("RGB", (320, 400))          # buyuk master'i JPEG cozerken kucult
            g = g.convert("RGB").resize((160, 200), Image.LANCZOS)
            return np.asarray(g, dtype=np.int16)

        hedef = kucult(io.BytesIO(r.content))
        for ad, yol in (("master", a.master), ("kontrol", a.kontrol)):
            if not yol:
                continue
            yerel = isd / f"{ad}.jpg"
            rclone("copyto", yol, str(yerel))
            olcumler[ad] = round(float(np.abs(hedef - kucult(yerel)).mean()), 2)
            yerel.unlink(missing_ok=True)
        log(f"icerik karsilastirmasi (ortalama mutlak fark, 0-255): {olcumler}")
        if olcumler.get("master") is None or olcumler["master"] > 12:
            raise SystemExit(f"DUR: baski dosyasi master ile eslesmiyor: {olcumler}")
        if "kontrol" in olcumler and olcumler["kontrol"] - olcumler["master"] < 10:
            raise SystemExit(f"DUR: karsilastirma ayirt edici degil: {olcumler}")

    # ---------------------------------------------------------- 4) teklif
    key = load_prodigi_key(a.env)
    prod = Prodigi(key, a.env)
    st, q = prod.call("POST", "/quotes", {"shippingMethod": a.kargo, "destinationCountryCode": a.ulke,
                                          "currencyCode": "USD",
                                          "items": [{"sku": a.sku, "copies": a.adet,
                                                     "attributes": {}, "assets": [{"printArea": "default"}]}]})
    if st != 200 or not q.get("quotes"):
        raise SystemExit(f"DUR: teklif HTTP {st}: {json.dumps(q)[:400]}")
    qq = next((x for x in q["quotes"] if (x.get("shipmentMethod") or "").lower() == a.kargo.lower()), q["quotes"][0])
    cs = qq.get("costSummary") or {}
    kalem = float((cs.get("items") or {}).get("amount") or 0)
    kargo_tut = float((cs.get("shipping") or {}).get("amount") or 0)
    log(f"teklif: kalem {kalem:.2f} + kargo {kargo_tut:.2f} = {kalem + kargo_tut:.2f} USD "
        f"({qq.get('shipmentMethod')}, {a.ulke})")

    govde = {"merchantReference": a.ref, "shippingMethod": a.kargo, "idempotencyKey": a.ref,
             "recipient": {"name": a.alici,
                           "address": {"line1": a.adres1, "line2": a.adres2 or None,
                                       "postalOrZipCode": a.posta, "countryCode": a.ulke,
                                       "townOrCity": a.sehir, "stateOrCounty": a.eyalet or None}},
             "items": [{"merchantReference": f"{a.ref}-1", "sku": a.sku, "copies": a.adet,
                        "sizing": "fillPrintArea",
                        "assets": [{"printArea": "default", "url": url}]}]}
    sonuc = {"ref": a.ref, "sku": a.sku, "adet": a.adet, "env": a.env, "kargo": a.kargo,
             "dosya": {"remote": a.remote, "id": a.file_id, "olcu": list(im.size), "md5": md5,
                       "bayt": len(r.content), "url": url, "izin_id": izin["id"],
                       "icerik_fark": olcumler},
             "teklif": {"kalem": round(kalem, 2), "kargo": round(kargo_tut, 2),
                        "toplam": round(kalem + kargo_tut, 2)},
             "order_body": {**govde, "items": [{**govde["items"][0], "assets": [{"printArea": "default", "url": "(URL)"}]}]},
             "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    if a.mod == "hazirla":
        p = isd / f"MANUEL_{a.ref}_PLAN.json"
        p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(p), f"{DRV}/{p.name}")
        log(f"PLAN yazildi: {DRV}/{p.name} (SIPARIS YOK)")
        return 0

    # ---------------------------------------------------------- 5) CANLI siparis
    log(f"CANLI SIPARIS: {a.sku} x{a.adet} -> {a.alici}, {a.sehir} {a.eyalet} {a.posta} {a.ulke} "
        f"(ref/idempotencyKey {a.ref})")
    st, d2 = prod.create_order(govde)
    sonuc["create_http"] = st
    sonuc["create_outcome"] = d2.get("outcome")
    if st not in (200, 201) or not (d2.get("order") or {}).get("id"):
        sonuc["create_hata"] = json.dumps(d2)[:800]
        p = isd / f"MANUEL_{a.ref}_HATA.json"
        p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(p), f"{DRV}/{p.name}")
        raise SystemExit(f"DUR: siparis HTTP {st} outcome={d2.get('outcome')}: {json.dumps(d2)[:600]}")
    oid = d2["order"]["id"]
    log(f"siparis olusturuldu: id {oid} | outcome {d2.get('outcome')}")

    st2, d3 = prod.get_order(oid)
    o = (d3.get("order") or {}) if st2 == 200 else {}
    durum = (o.get("status") or {})
    sonuc["order_id"] = oid
    sonuc["get_http"] = st2
    sonuc["durum"] = {"stage": durum.get("stage"), "details": durum.get("details"),
                      "issues": durum.get("issues")}
    sonuc["charges"] = o.get("charges")
    sonuc["created"] = o.get("created")
    log(f"geri okuma: stage {durum.get('stage')} | details {json.dumps(durum.get('details') or {})[:200]} "
        f"| issues {durum.get('issues')}")
    p = isd / f"MANUEL_{a.ref}.json"
    p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(p), f"{DRV}/{p.name}")
    log(f"sonuc: {DRV}/{p.name} | NOT: baski dosyasinin gecici izni ACIK birakildi "
        f"(Prodigi assetleri indirene kadar).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
