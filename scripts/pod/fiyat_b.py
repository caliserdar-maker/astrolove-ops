#!/usr/bin/env python3
"""B PLANI FIYAT: tek ilanin 80 varyantinin YALNIZ fiyatini gunceller.

Serdar onayi 24 Eyl 2026: referans ilan (Cancer-Libra) 16 boy x 5 renk = 80 varyant.
Fiyat disinda HICBIR sey degismez: SKU, boy/renk etiketleri ve value_id'leri,
adet, gorunurluk (is_enabled), hazirlik suresi (readiness_state_id), kisisellestirme
alanlari ve renk->gorsel baglari AYNEN korunur.

Modlar:
  oku : salt okuma. Yedek (inventory + variation-images + listing) alinir,
        80 varyant icin (sku, boy, renk, eski fiyat, yeni fiyat) tablosu yazilir.
  yaz : envanter PUT (--confirm FIYAT_B). PUT sonrasi variation-images yeniden
        okunur, eksik renk-gorsel bagi POST ile geri yazilir (pod_inventory_update
        mantigi), sonra 80 fiyat + kisisellestirme + renk bagi geri okunarak dogrulanir.

NEDEN updateListing DEGIL: updateListing bir taslagi otomatik yayina alir (7 Eyl olcumu).
Burada yalniz updateListingInventory (PUT /listings/{id}/inventory) kullanilir; ilan
state'i once ve sonra okunup rapora yazilir.
"""
import argparse
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
import pod_pilot_15 as P  # noqa: E402

# B plani fiyatlari (5 rengin hepsinde ayni) — Serdar, 24 Eyl 2026.
FIYAT = {
    "8x10": 34.99, "A4": 37.99, "11x14": 42.99, "12x16": 46.99, "A3": 47.99,
    "12x18": 49.99, "16x20": 54.99, "16x24": 57.99, "A2": 57.99, "18x24": 64.99,
    "20x30": 84.99, "24x30": 94.99, "24x32": 99.99, "A1": 99.99, "24x36": 109.99,
    "30x40": 139.99,
}
KISISEL = ("is_personalizable", "personalization_is_required",
           "personalization_char_count_max", "personalization_instructions")


def anahtar_of(etiket):
    """'4:5 · 8x10 in (20×25 cm)' / '8x10 in (20×25 cm)' / 'A4 (21×30 cm)' -> '8x10' / 'A4'."""
    t = (etiket or "").strip()
    t = re.sub(r"^.*?·\s*", "", t)                       # varsa oran oneki
    m = re.match(r"\s*(A[1-4]|\d{1,2}\s*[xX×]\s*\d{1,2})\b", t)
    if not m:
        return None
    a = m.group(1).replace(" ", "").replace("×", "x").replace("X", "x")
    return a.upper() if a.upper().startswith("A") else a


def renk_of(pr):
    pv = P.pv_of(pr, "primary color") or P.pv_of(pr, "color")
    return (pv.get("values") or [None])[0] if pv else None


def satirlar(inv):
    """[(sku, boy_etiketi, anahtar, renk, eski_fiyat, yeni_fiyat, adet, acik)] + taninmayan boylar."""
    out, bilinmeyen = [], []
    for pr in inv.get("products") or []:
        etiket = P.deger(pr, "size")
        anahtar = anahtar_of(etiket)
        o = (pr.get("offerings") or [{}])[0]
        eski = P.para(o.get("price"))
        yeni = FIYAT.get(anahtar)
        if yeni is None:
            bilinmeyen.append(etiket)
        out.append((pr.get("sku") or "", etiket, anahtar, renk_of(pr), eski, yeni,
                    o.get("quantity"), bool(o.get("is_enabled"))))
    return out, bilinmeyen


def govde(inv):
    """Mevcut envanterin BIREBIR kopyasi; yalniz offering fiyatlari FIYAT tablosundan."""
    urunler = []
    for pr in inv.get("products") or []:
        anahtar = anahtar_of(P.deger(pr, "size"))
        yeni = FIYAT[anahtar]                             # kapi: bilinmeyen boy varsa buraya gelinmez
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])    # etiket degismiyor -> id korunur (renk-gorsel bagi)
            pvs.append(d)
        offs = []
        for o in pr.get("offerings") or []:
            off = {"price": yeni, "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        urunler.append({"sku": pr.get("sku") or "", "property_values": pvs, "offerings": offs})
    body = {"products": urunler}
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        v = inv.get(k)
        if v:
            body[k] = list(v)
    return body


def kapilar(inv, rows, bilinmeyen, beklenen):
    h = []
    if len(rows) != beklenen:
        h.append(f"urun sayisi {len(rows)} != {beklenen}")
    if bilinmeyen:
        h.append(f"fiyat tablosunda olmayan boy: {sorted(set(bilinmeyen))[:6]}")
    boylar = {r[2] for r in rows if r[2]}
    renkler = {r[3] for r in rows if r[3]}
    if len(boylar) != 16:
        h.append(f"boy sayisi {len(boylar)} != 16 ({sorted(boylar)})")
    if len(renkler) != 5:
        h.append(f"renk sayisi {len(renkler)} != 5 ({sorted(renkler)})")
    if len({r[0] for r in rows}) != len(rows):
        h.append("tekrar eden SKU var")
    if any(not r[0] for r in rows):
        h.append("SKU'su bos urun var")
    for pr in inv.get("products") or []:
        if len(pr.get("offerings") or []) != 1:
            h.append(f"{pr.get('sku')}: offering sayisi 1 degil")
            break
    return h


def ozellikler(inv):
    ad = []
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            n = pv.get("property_name") or str(pv.get("property_id"))
            if n not in ad:
                ad.append(n)
    return ad


def tablo(rows):
    md = ["| # | sku | renk | boy | eski fiyat | yeni fiyat | fark | adet | acik |",
          "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        fark = "" if r[5] is None or r[4] is None else f"{r[5] - r[4]:+.2f}"
        md.append(f"| {i} | {r[0]} | {r[3]} | {r[1]} | {r[4]:.2f} | "
                  f"{'YOK' if r[5] is None else f'{r[5]:.2f}'} | {fark} | {r[6]} | {'E' if r[7] else 'H'} |")
    return md


def kisisel_of(L):
    return {k: L.get(k) for k in KISISEL}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--listing", required=True)
    ap.add_argument("--out", default="_out/fiyat_b")
    ap.add_argument("--beklenen-urun", type=int, default=80)
    ap.add_argument("--kota-alt", type=int, default=200)
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    lid = str(a.listing)

    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""),
                       os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]

    # ---- 1) yedek (inventory + variation-images + listing + galeri)
    sn = P.anlik(api, shop, lid)
    inv = sn["inventory"]
    for ad, veri in (("inventory_ONCE", inv), ("variation_images_ONCE", sn["variation_images"]),
                     ("listing_ONCE", sn["listing"])):
        (out / "YEDEK" / f"{lid}_{ad}.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    kota_once = api.remaining
    L = sn["listing"]
    v_once = P.v_renk_haritasi(inv, sn["variation_images"])
    kis_once = kisisel_of(L)

    rows, bilinmeyen = satirlar(inv)
    hata = kapilar(inv, rows, bilinmeyen, a.beklenen_urun)
    degisen = [r for r in rows if r[5] is not None and abs(r[5] - r[4]) >= 0.005]

    md = [f"# B plani fiyat — ilan {lid} ({a.mod.upper()})", "",
          f"- urun: {len(rows)} (beklenen {a.beklenen_urun}) | boy {len({r[2] for r in rows if r[2]})} | "
          f"renk {len({r[3] for r in rows if r[3]})}",
          f"- fiyati degisecek varyant: {len(degisen)} | ayni kalan: {len(rows) - len(degisen)}",
          f"- ilan state (once): {L.get('state')} | kota once: {kota_once}",
          f"- kisisellestirme (once): {kis_once}",
          f"- renk -> gorsel (once): {v_once}",
          f"- ozellik adlari: {ozellikler(inv)}",
          f"- fiyat/adet/sku ozellik bagi: price_on_property={inv.get('price_on_property')} "
          f"quantity_on_property={inv.get('quantity_on_property')} sku_on_property={inv.get('sku_on_property')}", "",
          "## 80 varyant (fiyat disinda hicbir alan degismez)", ""] + tablo(rows)
    if hata:
        md += ["", "**KAPI TUTMADI — yazma yok:** " + "; ".join(hata)]

    if a.mod == "oku":
        md += ["", f"**Durum: KURU (yazma yok)** | kota {api.remaining}"]
    else:
        if a.confirm != "FIYAT_B":
            raise SystemExit("HATA: yaz icin --confirm FIYAT_B gerekir. DUR.")
        if hata:
            raise SystemExit("HATA: kapi tutmadi, yazma yok: " + "; ".join(hata))
        try:
            kalan = int(kota_once or 0)
        except (TypeError, ValueError):
            kalan = 0
        if kalan and kalan < a.kota_alt:
            raise SystemExit(f"HATA: kota {kalan} < {a.kota_alt}. DUR.")

        body = govde(inv)
        (out / "inventory_PUT.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"PUT /listings/{lid}/inventory — {len(body['products'])} urun, yalniz fiyat degisiyor")
        api.put_json(f"/listings/{lid}/inventory", body)

        # ---- geri okuma
        sn2 = P.anlik(api, shop, lid)
        inv2, L2 = sn2["inventory"], sn2["listing"]
        rows2, bilinmeyen2 = satirlar(inv2)
        (out / "YEDEK" / f"{lid}_inventory_SONRA.json").write_text(
            json.dumps(inv2, ensure_ascii=False, indent=1), encoding="utf-8")

        fails = []
        hedef = {r[0]: FIYAT.get(r[2]) for r in rows}
        okunan = {r[0]: r[4] for r in rows2}
        yanlis = [(s, hedef[s], okunan.get(s)) for s in hedef if okunan.get(s) != hedef[s]]
        if len(rows2) != len(rows):
            fails.append(f"urun sayisi {len(rows2)} != {len(rows)}")
        if yanlis:
            fails.append(f"fiyat {len(yanlis)} varyantta tutmadi: {yanlis[:5]}")
        # fiyat disinda degisen alan var mi?
        eski_d = {r[0]: (r[1], r[3], r[6], r[7]) for r in rows}
        yeni_d = {r[0]: (r[1], r[3], r[6], r[7]) for r in rows2}
        sapma = [(s, eski_d[s], yeni_d.get(s)) for s in eski_d if yeni_d.get(s) != eski_d[s]]
        if sapma:
            fails.append(f"fiyat disinda {len(sapma)} sapma: {sapma[:3]}")

        # ---- renk -> gorsel: PUT sonrasi yeniden oku, eksikse geri yaz
        v_sonra = P.v_renk_haritasi(inv2, sn2["variation_images"])
        onarim = "gerekmedi"
        if v_sonra != v_once:
            pid, vid = None, {}
            for pr in inv2.get("products") or []:
                pv = P.pv_of(pr, "primary color") or P.pv_of(pr, "color")
                if pv and pv.get("value_ids"):
                    pid = pid or pv.get("property_id")
                    vid.setdefault((pv.get("values") or [""])[0], pv["value_ids"][0])
            eksik = [c for c in v_once if c not in vid]
            if pid is None or eksik:
                fails.append(f"renk->gorsel value_id yok: {eksik}")
                onarim = "YAPILAMADI"
            else:
                api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                              {"variation_images": [{"property_id": pid, "value_id": vid[c], "image_id": int(img)}
                                                    for c, img in v_once.items()]})
                v3 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
                v_sonra = P.v_renk_haritasi(inv2, v3)
                onarim = "POST ile geri yazildi"
                if v_sonra != v_once:
                    fails.append(f"renk->gorsel onarilamadi: {v_sonra}")
        kis_sonra = kisisel_of(L2)
        if kis_sonra != kis_once:
            fails.append(f"kisisellestirme degisti: {kis_once} -> {kis_sonra}")
        if L2.get("state") != L.get("state"):
            fails.append(f"state degisti: {L.get('state')} -> {L2.get('state')}")
        (out / "YEDEK" / f"{lid}_variation_images_SONRA.json").write_text(
            json.dumps(sn2["variation_images"], ensure_ascii=False, indent=1), encoding="utf-8")

        md += ["", "## Geri okuma (Etsy'den)", "",
               f"- fiyat: {len(hedef) - len(yanlis)}/{len(hedef)} hedefte",
               f"- fiyat disi alanlar (boy, renk, adet, gorunurluk): {len(eski_d) - len(sapma)}/{len(eski_d)} ayni",
               f"- renk -> gorsel: {v_sonra} ({onarim})",
               f"- kisisellestirme: {kis_sonra}",
               f"- state: {L.get('state')} -> {L2.get('state')} | kota sonra: {api.remaining}", ""]
        md += ["**Durum: " + ("PASS" if not fails else "FAIL — " + "; ".join(fails)) + "**"]
        if bilinmeyen2:
            md += [f"- uyari: geri okumada taninmayan boy: {sorted(set(bilinmeyen2))[:6]}"]

    metin = "\n".join(md)
    (out / f"FIYAT_B_{a.mod.upper()}.md").write_text(metin + "\n", encoding="utf-8")
    okunan_son = {r[0]: r[4] for r in rows2} if a.mod == "yaz" else {}
    with (out / f"FIYAT_B_{a.mod.upper()}.csv").open("w", encoding="utf-8") as fh:
        fh.write("sku,renk,boy,anahtar,eski_fiyat,hedef_fiyat,okunan_fiyat,adet,acik\n")
        for r in rows:
            fh.write(f"{r[0]},{r[3]},{r[1]},{r[2]},{r[4]},{'' if r[5] is None else r[5]},"
                     f"{okunan_son.get(r[0], '')},{r[6]},{int(r[7])}\n")
    log(metin)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(metin + "\n")
    if a.mod == "yaz" and "FAIL" in md[-1]:
        sys.exit(1)
    if a.mod == "oku" and hata:
        sys.exit(1)


if __name__ == "__main__":
    main()
