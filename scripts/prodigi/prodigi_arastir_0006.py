#!/usr/bin/env python3
"""GOREV 0006/0007 arastirmasi (SALT OKUMA; Prodigi'ye POST/iptal YOK, Etsy yok).

 1) DOKUMAN: Prodigi Print API reference sayfasi indirilir; branding / sticker / insert / set / paused /
    stage / GET orders gecen yerler alintilanir (kanit), tam metin Drive TEMP/PRODIGI'ye yazilir.
 2) SIPARIS: test siparisi GET /orders/{id} (ord_ onekli + oneksiz), GET /orders?top=100 ve status filtreleri.
    Yalniz id / stage / sayi yazilir; alici yazilmaz.
 3) LINK: musteri verisi icermeyen marka dosyalari (A6 kartpostal kaynagi + 2 sticker) icin canli akistaki
    ayni link bicimi (Drive uc?export=download) acilir, kimliksiz istekle zincir (durum, alan adi, Content-Type),
    gorsel olcusu/dpi okunur; izin kapatilinca ayni link tekrar denenir. Link / dosya id loga yazilmaz.
Kullanim: prodigi_arastir_0006.py <order_id>
"""
import html
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pinterest"))

DOC_URL = "https://www.prodigi.com/print-api/docs/reference/"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
ANAHTAR = [r"branding", r"sticker_", r"insert", r"\bsets?\b", r"paus", r"on ?hold", r"\bstage\b",
           r"GET /v4\.0/orders", r"\btop\b", r"status="]
DOSYALAR = {  # musteri verisi yok (marka dosyalari)
    "postcard_A6_kaynak": "gdrive:ASTROLOVE/BRAND/INSERTS/ASTROLOVE_INSERT_POSTCARD_A6_EN_LACIVERT_1240x1748_V1.jpg",
    "sticker_65mm": "gdrive:ASTROLOVE/BRAND/INSERTS/ASTROLOVE_INSERT_STICKER_65MM_LACIVERT_V2.png",
    "sticker_25mm_tissue": "gdrive:ASTROLOVE/BRAND/INSERTS/ASTROLOVE_INSERT_TISSUE_25MM_LACIVERT_331x331_V1.png",
}
OUT = Path("out")


def log(m):
    print(m, flush=True)


def doc_metni(ham):
    ham = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", ham)
    ham = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|pre|code)>", "\n", ham)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", ham)))


def dokuman():
    log("== 1) DOKUMAN")
    try:
        r = requests.get(DOC_URL, headers=UA, timeout=60)
    except requests.RequestException as e:
        log(f"  indirilemedi: {str(e)[:120]}")
        return
    log(f"  GET {DOC_URL}: HTTP {r.status_code}, {len(r.text)} karakter")
    metin = doc_metni(r.text)
    OUT.mkdir(exist_ok=True)
    (OUT / "PRODIGI_API_REFERENCE_0006.txt").write_text(metin, encoding="utf-8")
    satirlar = [s.strip() for s in metin.splitlines() if s.strip()]
    for k in ANAHTAR:
        hit = [i for i, s in enumerate(satirlar) if re.search(k, s, re.I)]
        log(f"  [{k}] {len(hit)} satir")
        goster, son = 0, -99
        for i in hit:
            if i - son < 3:
                continue
            son = i
            parca = " | ".join(satirlar[max(0, i - 1):i + 3])
            log(f"    L{i}: {parca[:400]}")
            goster += 1
            if goster >= 12:
                break


def ozet(o):
    """Alici YAZILMAZ: yalniz durum, tesis, kalem SKU, branding alan adlari, ucretler."""
    st = o.get("status") or {}
    return json.dumps({
        "id": o.get("id"), "stage": st.get("stage"), "details": st.get("details"),
        "issues": [f"{i.get('errorCode')}:{str(i.get('description') or '')[:120]}" for i in st.get("issues") or []],
        "shippingMethod": o.get("shippingMethod"), "kalem": [i.get("sku") for i in o.get("items") or []],
        "branding": sorted(o.get("branding") or {}),
        "tesis": sorted({f"{(s.get('fulfillmentLocation') or {}).get('countryCode')}/{(s.get('fulfillmentLocation') or {}).get('labCode')}"
                         for s in o.get("shipments") or [] if s.get("fulfillmentLocation")}),
        "charges": [{"tip": c.get("chargeType"), "toplam": (c.get("totalCost") or {}).get("amount"),
                     "para": (c.get("totalCost") or {}).get("currency"), "fatura_no_var": bool(c.get("prodigiInvoiceNumber")),
                     "kalemler": [[x.get("description") or "", x.get("itemSku") or "", bool(x.get("itemId")),
                                   (x.get("cost") or {}).get("amount")] for x in c.get("items") or []]}
                    for c in o.get("charges") or []]}, ensure_ascii=False)


def siparis(oid):
    from prodigi_pilot_quote import Api, load_key
    log("== 2) SIPARIS (yalniz GET)")
    api = Api(load_key())

    def oku(yol):
        r = api._call("GET", yol)
        try:
            d = r.json()
        except ValueError:
            d = {}
        return r.status_code, d

    for yol in (f"/orders/{oid}", f"/orders/{oid.replace('ord_', '')}"):
        st, d = oku(yol)
        o = d.get("order") or {}
        log(f"  GET {yol}: HTTP {st} outcome={d.get('outcome')} stage={(o.get('status') or {}).get('stage')} "
            f"details={(o.get('status') or {}).get('details')}")
        if o:
            log("    " + ozet(o))
    st, d = oku("/orders?top=100")
    L = d.get("orders") or []
    log(f"  GET /orders?top=100: HTTP {st}, {len(L)} siparis, test var={any(o.get('id') == oid for o in L)}, "
        f"hasMore={d.get('hasMore')}, nextUrl={'var' if d.get('nextUrl') else 'yok'}")
    for s in ("draft", "awaitingPayment", "inProgress", "complete", "cancelled", "paused", "onHold", "Paused"):
        st, d = oku(f"/orders?top=100&status={s}")
        L = d.get("orders") or []
        log(f"  GET /orders?status={s}: HTTP {st}, {len(L)} siparis, test var={any(o.get('id') == oid for o in L)}"
            + (f", hata={str(d.get('failures') or d.get('statusText') or '')[:120]}" if st != 200 else ""))
        for o in L:
            if o.get("id") == oid:
                log("    " + ozet(o))
    st, d = oku(f"/orders?top=10&orderIds={oid}")
    log(f"  GET /orders?orderIds=<test>: HTTP {st}, {len(d.get('orders') or [])} siparis")


def zincir(url, n=8):
    adimlar = []
    for _ in range(n):
        try:
            r = requests.get(url, headers=UA, timeout=60, allow_redirects=False, stream=True)
        except requests.RequestException as e:
            adimlar.append(("HATA", str(e)[:80], ""))
            return adimlar, None
        adimlar.append((r.status_code, urlparse(url).netloc, r.headers.get("content-type", "")))
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
            url = requests.compat.urljoin(url, r.headers["location"])
            continue
        return adimlar, r
    return adimlar, None


def gorsel_ozet(r):
    veri = r.content[:30_000_000]
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(veri))
        return f"{len(veri)} bayt, {im.format} {im.size[0]}x{im.size[1]} {im.mode}, dpi={im.info.get('dpi')}"
    except Exception as e:  # HTML sayfa vb.
        bas = re.sub(r"\s+", " ", veri[:200].decode("utf-8", "replace"))[:100]
        return f"{len(veri)} bayt, gorsel DEGIL ({type(e).__name__}); bas: {bas}"


def linkler():
    from order_router import DriveLinks
    log("== 3) LINK (canli akistaki bicim: drive.google.com/uc?export=download; link/id loga yazilmaz)")
    dl = DriveLinks()
    for ad, remote in DOSYALAR.items():
        fid, pid, url = dl.open(remote)
        try:
            time.sleep(3)
            adim, r = zincir(url)
            log(f"  {ad} ACIK: " + " -> ".join(f"{s} {h} [{c}]" for s, h, c in adim))
            if r is not None and r.status_code == 200:
                log(f"    icerik: {gorsel_ozet(r)}")
            onizleme = f"https://drive.google.com/file/d/{fid}/view"
            adim, r = zincir(onizleme)
            log(f"  {ad} onizleme sayfasi: " + " -> ".join(f"{s} {h} [{c}]" for s, h, c in adim))
        finally:
            dl.close(fid, pid)
        time.sleep(5)
        adim, r = zincir(url)
        log(f"  {ad} izin KAPALI: " + " -> ".join(f"{s} {h} [{c}]" for s, h, c in adim))
        if r is not None and r.status_code == 200:
            log(f"    icerik: {gorsel_ozet(r)}")


def main():
    oid, _, mod = (sys.argv[1] if len(sys.argv) > 1 else "ord_72692295730813440").partition(",")
    if mod == "siparis":                             # GOREV 0009: yalniz siparis okuma
        siparis(oid)
        return
    dokuman()
    siparis(oid)
    linkler()
    if (OUT / "PRODIGI_API_REFERENCE_0006.txt").exists():
        subprocess.run(["rclone", "copyto", str(OUT / "PRODIGI_API_REFERENCE_0006.txt"),
                        "gdrive:ASTROLOVE/TEMP/PRODIGI/PRODIGI_API_REFERENCE_0006.txt", "-q"])
        log("  tam dokuman metni: Drive TEMP/PRODIGI/PRODIGI_API_REFERENCE_0006.txt")


if __name__ == "__main__":
    main()
