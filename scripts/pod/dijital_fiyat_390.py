#!/usr/bin/env python3
"""78 poster ilaninda YALNIZ dijital secenegin fiyati -> 3.90 USD (Serdar onayi 24 Eki 2026, Genel Merkez).

Dijital urun = SKU '-DIGITAL' ile biter VE bir ozellik degerinde 'digital' gecer (iki tanim ayni kumeyi vermeli).
Dijital disi her urun (fiyat, SKU, adet, gorunurluk, ozellik degerleri) BIREBIR ayni kalir.
updateListing CAGRILMAZ (taslagi yayina alir); yalniz PUT /listings/{id}/inventory.
Renk -> gorsel baglari PUT oncesi okunur; PUT sonrasi degistiyse ayni degerlerle geri yazilir ve yeniden okunur.

Modlar:
  oku  : salt okuma; ilan basina plan + kapilar. Yazma yok.
  yaz  : --confirm DIJITAL_390 ile ilan basina tek PUT + geri okuma. Ilk FAIL'de DUR.
Cikis: 0 PASS, 1 FAIL/DUR.
Kullanim: dijital_fiyat_390.py <oku|yaz> --ilanlar ID[,ID...] | --hepsi [--confirm DIJITAL_390]
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path[:0] = [str(KOK), str(KOK.parent / "etsy")]

YENI = 3.90
ESKI_IZINLI = (9.00,)               # bugunku dijital fiyat (canli 9.00, 24 Eki okuma)
ONAY = "DIJITAL_390"
ONAY_HEPSI = "DIJITAL_390_HEPSI"   # 78 ilan birden yazmak icin ayri onay
INV_YOL = "/listings/{lid}/inventory?max_variations_supported=3"   # 3 menulu ilan; parametresiz PUT 409 (REFERANS_ILAN_CL.md:49)
IDS_YOL = KOK.parents[1] / "data" / "pod" / "pod78_ids.csv"
OUT = Path("out")
METIN_FIYAT = re.compile(r"\$\s?9(?:\.00|\.99)?\b|\b9\.(?:00|99)\s?(?:USD|\$)")


def para(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def log(m):
    print(m, flush=True)


def ids_oku():
    ids = [r["listing_id"].strip() for r in csv.DictReader(open(IDS_YOL, encoding="utf-8")) if r.get("listing_id")]
    if len(ids) != 78 or len(set(ids)) != 78:
        raise SystemExit(f"DUR: pod78_ids.csv {len(ids)} satir (78 bekleniyordu)")
    return ids


def pv_metin(pr):
    return [str(v) for pv in pr.get("property_values") or [] for v in (pv.get("values") or [])]


def dijital_mi(pr):
    sku = (pr.get("sku") or "").upper()
    a = sku.endswith("-DIGITAL")
    b = any((pv.get("property_name") or "").lower() == "format" and list(pv.get("values") or []) == ["Digital File"]
            for pv in pr.get("property_values") or [])
    return a, b


def anahtar(pr):
    return tuple((pv.get("property_id"), tuple(pv.get("values") or [])) for pv in pr.get("property_values") or [])


def imza(pr):
    """Fiyat disindaki her alan (karsilastirma icin)."""
    pvs = tuple((pv.get("property_id"), tuple(pv.get("values") or []), tuple(pv.get("value_ids") or []))
                for pv in pr.get("property_values") or [])
    offs = tuple((o.get("quantity"), bool(o.get("is_enabled")), o.get("readiness_state_id"))
                 for o in pr.get("offerings") or [])
    return (pr.get("sku") or "", pvs, offs)


def fiyatlar(pr):
    return [para(o.get("price")) for o in pr.get("offerings") or []]


def plan(inv):
    """-> (dijital_sku listesi, dijital_disi_sku listesi, hatalar, zaten_hedefte)"""
    h, dig, diger = [], [], []
    urunler = inv.get("products") or []
    if not urunler:
        h.append("envanter bos")
    if any(not (p.get("sku") or "") for p in urunler):
        h.append("SKU'su bos urun var")
    anahtarlar = [anahtar(p) for p in urunler]          # SKU renkler arasinda tekrar eder (sku_on_property), anahtar = ozellik degerleri
    if len(set(anahtarlar)) != len(anahtarlar):
        h.append("tekrar eden ozellik kombinasyonu var")
    for pr in urunler:
        a, b = dijital_mi(pr)
        if a != b:
            h.append(f"dijital tanimlari uyusmuyor: {pr.get('sku')} (sku={a}, ozellik={b})")
        if len(pr.get("offerings") or []) != 1:
            h.append(f"{pr.get('sku')}: offering sayisi {len(pr.get('offerings') or [])} (1 bekleniyordu)")
        (dig if a and b else diger).append(pr)
    if not dig:
        h.append("dijital urun bulunamadi")
    if not diger:
        h.append("dijital disi urun bulunamadi (beklenmeyen yapi)")
    dfiyat = sorted({f for p in dig for f in fiyatlar(p)})
    zaten = bool(dig) and dfiyat == [YENI]
    if dig and not zaten and any(f not in ESKI_IZINLI for f in dfiyat):
        h.append(f"dijital eski fiyat beklenmeyen: {dfiyat} (izinli {ESKI_IZINLI})")
    if dig and len(dfiyat) > 1 and not zaten:
        h.append(f"dijital urunlerde birden cok fiyat: {dfiyat}")
    if any(f <= YENI for p in diger for f in fiyatlar(p)):
        h.append("dijital disi bir urunun fiyati 3.90 veya alti (beklenmeyen)")
    return dig, diger, h, zaten


def govde(inv):
    """Mevcut envanterin birebir kopyasi; yalniz dijital urunlerin fiyati YENI."""
    urunler = []
    for pr in inv.get("products") or []:
        a, b = dijital_mi(pr)
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            pvs.append(d)
        offs = []
        for o in pr.get("offerings") or []:
            off = {"price": YENI if (a and b) else para(o.get("price")),
                   "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        urunler.append({"sku": pr.get("sku") or "", "property_values": pvs, "offerings": offs})
    body = {"products": urunler}
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if inv.get(k):
            body[k] = list(inv[k])
    return body


def renk_haritasi(inv, rows):
    ad = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            for v, i in zip(pv.get("values") or [], pv.get("value_ids") or []):
                ad[(pv.get("property_id"), i)] = v
    return {ad.get((r.get("property_id"), r.get("value_id")), str(r.get("value_id"))): str(r.get("image_id")) for r in rows}


def kisisel(L):
    return {k: L.get(k) for k in ("is_personalizable", "personalization_is_required",
                                   "personalization_char_count_max", "personalization_instructions")}


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "inventory": api.get(INV_YOL.format(lid=lid)) or {},
            "vimg": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []}


def ilan_isle(api, shop, lid, yaz):
    d = OUT / lid
    d.mkdir(parents=True, exist_ok=True)
    sn = anlik(api, shop, lid)
    L, inv = sn["listing"], sn["inventory"]
    (d / "ONCE.json").write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
    dig, diger, h, zaten = plan(inv)
    metin = [m.group(0) for alan in ("description", "personalization_instructions")
             for m in METIN_FIYAT.finditer(L.get(alan) or "")]
    sonuc = {"ilan": lid, "state": L.get("state"), "dijital_n": len(dig), "diger_n": len(diger),
             "dijital_eski": sorted({f for p in dig for f in fiyatlar(p)}), "kapi": h,
             "aciklamada_fiyat": metin, "renk_bag_once": renk_haritasi(inv, sn["vimg"]), "kota": api.remaining}
    if L.get("state") != "active":
        sonuc["durum"] = "ATLANDI_STATE"
        return sonuc
    if h:
        sonuc["durum"] = "FAIL_KAPI"
        return sonuc
    if zaten:
        sonuc["durum"] = "ZATEN"
        return sonuc
    if not yaz:
        sonuc["durum"] = "PLAN_OK"
        return sonuc

    body = govde(inv)
    (d / "PUT.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        api.put_json(INV_YOL.format(lid=lid), body)
    except SystemExit as e:                       # Etsy hata metni rapora (job logu proxy'de okunamiyor)
        sonuc["put_hata"] = str(e)[:600]
        try:
            sn2 = anlik(api, shop, lid)
            degisti = [p.get("sku") for p, q in zip(inv.get("products") or [], sn2["inventory"].get("products") or [])
                       if fiyatlar(p) != fiyatlar(q)]
            sonuc["put_sonrasi_degisen_n"] = len(degisti)
            (d / "SONRA.json").write_text(json.dumps(sn2, ensure_ascii=False, indent=1), encoding="utf-8")
        except SystemExit as e2:
            sonuc["put_sonrasi_okuma_hata"] = str(e2)[:300]
        sonuc["durum"] = "FAIL_PUT"
        return sonuc

    sn2 = anlik(api, shop, lid)
    L2, inv2 = sn2["listing"], sn2["inventory"]
    f = []
    once = {anahtar(p): p for p in inv.get("products") or []}
    sonra = {anahtar(p): p for p in inv2.get("products") or []}
    if set(once) != set(sonra) or len(sonra) != len(inv2.get("products") or []):
        f.append(f"urun kumesi degisti: once {len(once)} sonra {len(inv2.get('products') or [])}")
    dset = {anahtar(p) for p in dig}
    for k, p in once.items():
        q = sonra.get(k)
        if q is None:
            continue
        hedef = [YENI] if k in dset else fiyatlar(p)
        if fiyatlar(q) != hedef:
            f.append(f"fiyat {p.get('sku')} {k[1:]}: {fiyatlar(q)} != {hedef}")
        if (q.get("sku") or "") != (p.get("sku") or "") or imza(q)[2] != imza(p)[2]:
            f.append(f"fiyat disi alan degisti: {p.get('sku')} {k[1:]}")
    if [anahtar(p) for p in inv.get("products") or []] != [anahtar(p) for p in inv2.get("products") or []]:
        f.append("urun sirasi degisti")
    adlar = lambda i: sorted({(pv.get("property_id"), pv.get("property_name")) for p in i.get("products") or []
                              for pv in p.get("property_values") or []})
    if adlar(inv) != adlar(inv2):
        f.append(f"ozellik adlari degisti: {adlar(inv)} -> {adlar(inv2)}")
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if sorted(inv.get(k) or []) != sorted(inv2.get(k) or []):
            f.append(f"{k} degisti")
    if L2.get("state") != L.get("state"):
        f.append(f"state {L.get('state')} -> {L2.get('state')}")
    if kisisel(L2) != kisisel(L):
        f.append("kisisellestirme degisti")
    v_once, v_sonra, onarim = renk_haritasi(inv, sn["vimg"]), renk_haritasi(inv2, sn2["vimg"]), "gerekmedi"
    if v_sonra != v_once:
        vid, pid = {}, None
        for pr in inv2.get("products") or []:
            for pv in pr.get("property_values") or []:
                for v, i in zip(pv.get("values") or [], pv.get("value_ids") or []):
                    if v in v_once:
                        vid.setdefault(v, i)
                        pid = pid or pv.get("property_id")
        eksik = [c for c in v_once if c not in vid]
        if pid is None or eksik:
            f.append(f"renk bagi onarilamaz, value_id yok: {eksik}")
            onarim = "YAPILAMADI"
        else:
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                          {"variation_images": [{"property_id": pid, "value_id": vid[c], "image_id": int(i)}
                                                for c, i in v_once.items()]})
            v3 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
            v_sonra = renk_haritasi(inv2, v3)
            onarim = "geri yazildi"
            if v_sonra != v_once:
                f.append(f"renk bagi geri yazilamadi: {v_sonra}")
    (d / "SONRA.json").write_text(json.dumps(sn2, ensure_ascii=False, indent=1), encoding="utf-8")
    sonuc.update({"renk_bag_sonra": v_sonra, "renk_onarim": onarim, "hatalar": f, "kota": api.remaining,
                  "durum": "PASS" if not f else "FAIL"})
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    tum = ids_oku()
    if a.hepsi:
        ids = tum
    else:
        ids = [x.strip() for x in a.ilanlar.split(",") if x.strip()]
        dis = [x for x in ids if x not in tum]
        if not ids or dis:
            raise SystemExit(f"DUR: ilan listesi bos ya da 78 disinda: {dis[:5]}")
    yaz = a.mod == "yaz"
    if yaz and a.confirm != (ONAY_HEPSI if a.hepsi else ONAY):
        raise SystemExit(f"DUR: yaz icin --confirm {ONAY_HEPSI if a.hepsi else ONAY} gerekir")

    from etsy_common import Etsy, TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)

    sonuclar, t0 = [], time.time()
    for i, lid in enumerate(ids, 1):
        try:
            api.kota_kapisi(f"ilan {lid}")
            s = ilan_isle(api, shop, lid, yaz)
        except SystemExit as e:
            s = {"ilan": lid, "durum": "FAIL_ISTISNA", "hata": str(e)[:600], "dijital_n": None,
                 "dijital_eski": None, "kota": api.remaining}
        sonuclar.append(s)
        g = time.time() - t0
        log(f"[{i}/{len(ids)}] {100 * i // len(ids)}% gecen {g:.0f}s kalan ~{g / i * (len(ids) - i):.0f}s | "
            f"{lid} {s['durum']} dijital={s['dijital_n']} eski={s['dijital_eski']} kota={s['kota']}")
        if s["durum"].startswith(("FAIL", "DUR")):
            break
    say = {}
    for s in sonuclar:
        say[s["durum"].split(" ")[0]] = say.get(s["durum"].split(" ")[0], 0) + 1
    tamam = len(sonuclar) == len(ids) and not any(s["durum"].startswith(("FAIL", "DUR", "ATLANDI")) for s in sonuclar)
    ozet = {"mod": a.mod, "istenen": len(ids), "islenen": len(sonuclar), "sayim": say,
            "aciklamada_fiyat_ilan": [s["ilan"] for s in sonuclar if s.get("aciklamada_fiyat")],
            "kota_son": api.remaining, "durum": "PASS" if tamam else "FAIL", "ilanlar": sonuclar}
    (OUT / f"DIJITAL_390_{a.mod.upper()}.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    log("OZET " + json.dumps({k: v for k, v in ozet.items() if k != "ilanlar"}, ensure_ascii=False))
    sys.exit(0 if tamam else 1)


if __name__ == "__main__":
    main()
