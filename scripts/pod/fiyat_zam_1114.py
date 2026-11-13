#!/usr/bin/env python3
"""Poster (78) ve 1st Anniversary (78) ilanlarinda fiyat zammi (Serdar 13-14 Kas 2026, Genel Merkez).

Kararlar (birebir): "Her iki kategorideki dijital urunler 9.90 olacak"; "fiyat 9.90 olarak kalacak sabit";
"Baski fiyatlari da degisecek" + zam "+ 5 USD".
  Format "Digital File" : 3.90 -> 9.90 (her boy)
  Format "Print"        : her boy 25 Eki tablosu + 5.00 (BASKI_ESKI; 5x7 19.90 -> 24.90 ... 24x36 64.90 -> 69.90)
Baska Format degeri olan ilan (or. 1st Anniversary eski yapisi "Digital card 5x7") yazilmaz: FAIL_KAPI.
Fiyat disi her alan (SKU, adet, gorunurluk, ozellik degerleri, sira) BIREBIR ayni kalir. updateListing CAGRILMAZ
(taslagi yayina alir); yalniz PUT /listings/{id}/inventory?max_variations_supported=3. Renk -> gorsel baglari PUT
oncesi okunur; PUT sonrasi degistiyse ayni degerlerle geri yazilir ve yeniden okunur. Ilan basina tek PUT.
Kaynak: scripts/pod/dijital_fiyat_390.py (24 Eki) yapisi; baski tablosu scripts/pod/print_fiyat_v2.py:32-34 HEDEF
(yeni degerler) + 5x7 19.90 (scripts/etsy/pod_5x7_kuru.py:40).

Modlar:
  oku  : salt okuma; ilan basina plan + kapilar. Yazma yok. ATLA uygulanmaz (tum ilanlar okunur).
  yaz  : --confirm FIYAT_1114 (poster) / FIYAT_1114_YD (yd), --hepsi icin sonuna _HEPSI; ilan basina tek PUT + geri okuma.
         Ilk FAIL'de DUR. yd yazimi ancak 'oku --aile yd' olcumu Serdar'a gosterildikten sonra (ayri onay sozcugu).
Cikis: 0 PASS, 1 FAIL/DUR.
Kullanim: fiyat_zam_1114.py <oku|yaz> --aile poster|yd (--ilanlar ID[,ID...] | --hepsi) [--confirm ...]
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

ONAY = {"poster": "FIYAT_1114", "yd": "FIYAT_1114_YD"}          # yd ayri sozcuk: once 'oku --aile yd' olcumu
ONAY_HEPSI = {k: v + "_HEPSI" for k, v in ONAY.items()}
INV_YOL = "/listings/{lid}/inventory?max_variations_supported=3"   # 3 menulu ilan; parametresiz PUT 409 (REFERANS_ILAN_CL.md:49)
IDS = {"poster": KOK.parents[1] / "data" / "pod" / "pod78_ids.csv",
       "yd": KOK.parents[1] / "data" / "pod" / "yd78_ids.csv"}
YD_BOLUM = 60895624                 # "1st Anniversary Gifts"; yd78_ids.csv ile karsilastirilir

DIJITAL_ESKI, DIJITAL_YENI = 3.90, 9.90
ZAM = 5.00
BASKI_ESKI = {"5x7": 19.90, "8x10": 24.90, "A4": 24.90, "11x14": 29.90, "12x16": 32.90, "A3": 32.90, "12x18": 34.90,
              "16x20": 39.90, "16x24": 42.90, "A2": 42.90, "18x24": 44.90, "20x30": 54.90, "24x30": 59.90, "24x36": 64.90}
BASKI_YENI = {k: round(v + ZAM, 2) for k, v in BASKI_ESKI.items()}
DIJITAL, BASKI = "Digital File", "Print"

# Kota: ilan basina en kotu 10 istek: inv GET + 3 GET (anlik) + PUT + 3 GET + POST + GET (renk onarimi).
ISTEK_TAHMIN = 10
PUT_SONRASI = 6                      # PUT + 3 GET + POST + GET; PUT'tan hemen once kalan >= PUT_SONRASI + 10 olmali
KOTA_TABAN = 10                      # CLAUDE.md: tahmini istek + 10
METIN_FIYAT = re.compile(r"\$\s?\d+(?:\.\d+)?|\b\d+\.\d{2}\s?USD\b")   # aciklamada fiyat yazisi (yalniz rapor)
OUT = Path("out")


def para(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def log(m):
    print(m, flush=True)


def deger(pr, ad):
    """Ozellik adina gore (buyuk/kucuk harf duyarsiz) tek deger; yoksa ya da birden fazlaysa None."""
    for pv in pr.get("property_values") or []:
        if (pv.get("property_name") or "").lower() == ad and len(pv.get("values") or []) == 1:
            return pv["values"][0]
    return None


def boy_kodu(etiket):
    """"8×10″ (20×25cm)" -> "8x10"; "A4 (21×29.7cm)" -> "A4" (print_fiyat_v2.boy_kodu ile ayni)."""
    if not etiket:
        return None
    return etiket.split(" (")[0].strip().replace("×", "x").replace("″", "").replace('"', "").replace(" ", "")


def canli(pr):
    return [o for o in pr.get("offerings") or [] if not o.get("is_deleted")]


def fiyatlar(pr):
    return [para(o.get("price")) for o in canli(pr)]


def hedef(pr):
    """-> (eski, yeni) ya da None (bilinmeyen format/boy)."""
    f, k = deger(pr, "format"), boy_kodu(deger(pr, "size"))
    if k not in BASKI_ESKI:                      # boy her iki formatta bilinen tabloda olmali
        return None
    if f == DIJITAL:
        return DIJITAL_ESKI, DIJITAL_YENI
    if f == BASKI:
        return BASKI_ESKI[k], BASKI_YENI[k]
    return None


def yeni_fiyat(pr):
    h = hedef(pr)
    return h[1] if h else None


def anahtar(pr):
    return tuple((pv.get("property_id"), tuple(pv.get("values") or [])) for pv in pr.get("property_values") or [])


def imza(pr):
    """Fiyat disindaki her alan (karsilastirma icin)."""
    pvs = tuple((pv.get("property_id"), tuple(pv.get("values") or [])) for pv in pr.get("property_values") or [])
    offs = tuple((o.get("quantity"), bool(o.get("is_enabled")), o.get("readiness_state_id")) for o in canli(pr))
    return (pr.get("sku") or "", pvs, offs)


def plan(inv):
    """-> (urunler, hatalar, zaten). Her urun Digital File ya da bilinen boyda Print olmali."""
    h = []
    urunler = [p for p in inv.get("products") or [] if not p.get("is_deleted")]
    if not urunler:
        h.append("envanter bos")
    if len({anahtar(p) for p in urunler}) != len(urunler):
        h.append("tekrar eden ozellik kombinasyonu var")
    n_dij = n_bas = 0
    for p in urunler:
        f = deger(p, "format")
        sku = (p.get("sku") or "").upper()
        if not sku:
            h.append(f"SKU'su bos urun ({f}, {deger(p, 'size')}): yapi olculmedi")
        elif sku.endswith("-DIGITAL") != (f == DIJITAL):
            h.append(f"dijital tanimlari uyusmuyor: {p.get('sku')} (format={f})")
        if len(fiyatlar(p)) != 1:
            h.append(f"{p.get('sku')}: canli teklif sayisi {len(fiyatlar(p))} (1 bekleniyordu)")
            continue
        t = hedef(p)
        if t is None:
            h.append(f"bilinmeyen format/boy: {p.get('sku')} format={f} size={deger(p, 'size')}")
            continue
        n_dij += f == DIJITAL
        n_bas += f == BASKI
        if fiyatlar(p)[0] not in t:
            h.append(f"{p.get('sku')} {deger(p, 'size')}: fiyat {fiyatlar(p)[0]} (izinli eski {t[0]} ya da hedef {t[1]})")
    if urunler and (not n_dij or not n_bas):
        h.append(f"dijital {n_dij}, baski {n_bas}: ikisi de olmali")
    zaten = bool(urunler) and not h and all(fiyatlar(p) == [yeni_fiyat(p)] for p in urunler)
    return urunler, h, zaten


def govde(inv):
    """Mevcut envanterin birebir kopyasi; yalniz fiyatlar YENI."""
    urunler = []
    for pr in inv.get("products") or []:
        if pr.get("is_deleted"):
            continue
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            for k in ("property_name", "scale_id"):
                if pv.get(k):
                    d[k] = pv[k]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            pvs.append(d)
        offs = []
        for o in canli(pr):
            off = {"price": yeni_fiyat(pr), "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
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


def ozet_fiyat(urunler):
    return sorted({(deger(p, "format"), f) for p in urunler for f in fiyatlar(p)})


def ilan_isle(api, shop, lid, yaz):
    d = OUT / lid
    d.mkdir(parents=True, exist_ok=True)
    inv0 = api.get(INV_YOL.format(lid=lid)) or {}             # once yalniz envanter: zaten hedefteyse 1 istekle gec
    u0, h0, zaten0 = plan(inv0)
    if zaten0:
        return {"ilan": lid, "durum": "ZATEN", "urun_n": len(u0), "fiyatlar": ozet_fiyat(u0), "kota": api.remaining}
    sn = anlik(api, shop, lid)
    L, inv = sn["listing"], sn["inventory"]
    (d / "ONCE.json").write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
    urunler, h, zaten = plan(inv)
    metin = [m.group(0) for alan in ("description", "personalization_instructions")
             for m in METIN_FIYAT.finditer(L.get(alan) or "")]
    sonuc = {"ilan": lid, "state": L.get("state"), "urun_n": len(urunler), "fiyatlar": ozet_fiyat(urunler),
             "kapi": h, "aciklamada_fiyat": metin, "renk_bag_once": renk_haritasi(inv, sn["vimg"]), "kota": api.remaining}
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
    if api.remaining is None or int(api.remaining) < PUT_SONRASI + KOTA_TABAN:      # PUT'tan sonra ilan yarim kalmasin
        sonuc["durum"] = f"DUR_KOTA kalan {api.remaining} < {PUT_SONRASI + KOTA_TABAN} (PUT oncesi)"
        return sonuc

    body = govde(inv)
    (d / "PUT.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        api.put_json(INV_YOL.format(lid=lid), body)
    except SystemExit as e:                       # Etsy hata metni rapora (job logu proxy'de okunamiyor)
        sonuc["put_hata"] = str(e)[:600]
        try:
            sn2 = anlik(api, shop, lid)
            (d / "SONRA.json").write_text(json.dumps(sn2, ensure_ascii=False, indent=1), encoding="utf-8")
            sonuc["put_sonrasi_fiyatlar"] = ozet_fiyat([p for p in sn2["inventory"].get("products") or []
                                                        if not p.get("is_deleted")])
        except SystemExit as e2:
            sonuc["put_sonrasi_okuma_hata"] = str(e2)[:300]
        sonuc["durum"] = "FAIL_PUT"
        return sonuc

    sn2 = anlik(api, shop, lid)
    L2, inv2 = sn2["listing"], sn2["inventory"]
    f = []
    once = {anahtar(p): p for p in urunler}
    u2 = [p for p in inv2.get("products") or [] if not p.get("is_deleted")]
    sonra = {anahtar(p): p for p in u2}
    if set(once) != set(sonra) or len(sonra) != len(u2):
        f.append(f"urun kumesi degisti: once {len(once)} sonra {len(u2)}")
    for k, p in once.items():
        q = sonra.get(k)
        if q is None:
            continue
        if fiyatlar(q) != [yeni_fiyat(p)]:
            f.append(f"fiyat {p.get('sku')} {k[1:]}: {fiyatlar(q)} != {[yeni_fiyat(p)]}")
        if imza(q) != imza(p):
            f.append(f"fiyat disi alan degisti: {p.get('sku')}")
    if [anahtar(p) for p in urunler] != [anahtar(p) for p in u2]:
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
        for pr in u2:
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
    sonuc.update({"fiyatlar_sonra": ozet_fiyat(u2), "renk_bag_sonra": v_sonra, "renk_onarim": onarim, "hatalar": f,
                  "kota": api.remaining, "durum": "PASS" if not f else "FAIL"})
    return sonuc


def ids_oku(aile):
    ids = [r["listing_id"].strip() for r in csv.DictReader(open(IDS[aile], encoding="utf-8")) if r.get("listing_id")]
    if len(ids) != 78 or len(set(ids)) != 78:
        raise SystemExit(f"DUR: {IDS[aile].name} {len(ids)} satir (78 bekleniyordu)")
    return ids


def bolum_ids(api, shop, bolum):
    ids, off = [], 0
    while True:
        d = api.get(f"/shops/{shop}/shop-sections/listings", params={"shop_section_ids": bolum, "limit": 100,
                                                                     "offset": off}) or {}
        r = d.get("results") or []
        ids += [str(x.get("listing_id")) for x in r if x.get("listing_id")]
        if len(r) < 100:
            break
        off += 100
    return list(dict.fromkeys(ids))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--aile", choices=sorted(IDS), required=True)
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    bek = (ONAY_HEPSI if a.hepsi else ONAY)[a.aile]
    if yaz and a.confirm != bek:
        raise SystemExit(f"DUR: yaz icin --confirm {bek} gerekir")
    if bool(a.hepsi) == bool(a.ilanlar.strip()):
        raise SystemExit("DUR: --hepsi ya da --ilanlar (yalniz biri)")

    from etsy_common import Etsy, TokenStore, mask
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k_); mask(s_)
    store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)
    tum = ids_oku(a.aile)
    if a.aile == "yd":                           # sabit liste bolumle ayni olmali
        b = bolum_ids(api, shop, YD_BOLUM)
        if set(b) != set(tum):
            raise SystemExit(f"DUR: yd78_ids.csv ile bolum {YD_BOLUM} farkli (bolum {len(b)}, "
                             f"yalniz csv {len(set(tum) - set(b))}, yalniz bolum {len(set(b) - set(tum))})")
    if a.hepsi:
        atla = {x.strip() for x in os.environ.get("ATLA", "").split(",") if x.strip()} if yaz else set()
        ids = [x for x in tum if x not in atla]
    else:
        ids = [x.strip() for x in a.ilanlar.split(",") if x.strip()]
        dis = [x for x in ids if x not in tum]
        if not ids or dis:
            raise SystemExit(f"DUR: ilan listesi bos ya da aile disinda: {dis[:5]}")

    sonuclar, t0 = [], time.time()
    for i, lid in enumerate(ids, 1):
        if yaz and (api.remaining is not None and int(api.remaining) < ISTEK_TAHMIN + KOTA_TABAN):
            sonuclar.append({"ilan": lid, "durum": f"DUR_KOTA kalan {api.remaining} < {ISTEK_TAHMIN + KOTA_TABAN}",
                             "urun_n": None, "fiyatlar": None, "kota": api.remaining})
            log(f"DUR_KOTA {lid}: kalan {api.remaining}; kalan ilanlar sonraki kosuda (yazilanlar ZATEN atlanir)")
            break
        try:
            api.kota_kapisi(f"ilan {lid}")
            s = ilan_isle(api, shop, lid, yaz)
        except SystemExit as e:
            s = {"ilan": lid, "durum": "FAIL_ISTISNA", "hata": str(e)[:600], "urun_n": None, "fiyatlar": None,
                 "kota": api.remaining}
        sonuclar.append(s)
        g = time.time() - t0
        log(f"[{i}/{len(ids)}] {100 * i // len(ids)}% gecen {g:.0f}s kalan ~{g / i * (len(ids) - i):.0f}s | "
            f"{lid} {s['durum']} urun={s['urun_n']} kota={s['kota']}")
        if s["durum"].startswith(("FAIL", "DUR")):
            break
    say = {}
    for s in sonuclar:
        say[s["durum"].split(" ")[0]] = say.get(s["durum"].split(" ")[0], 0) + 1
    tamam = len(sonuclar) == len(ids) and not any(s["durum"].startswith(("FAIL", "DUR", "ATLANDI")) for s in sonuclar)
    ozet = {"mod": a.mod, "aile": a.aile, "istenen": len(ids), "islenen": len(sonuclar), "sayim": say,
            "aciklamada_fiyat_ilan": [s["ilan"] for s in sonuclar if s.get("aciklamada_fiyat")],
            "kota_son": api.remaining, "durum": "PASS" if tamam else "FAIL", "ilanlar": sonuclar}
    (OUT / f"FIYAT_1114_{a.mod.upper()}.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "TAMAM_EK.txt").write_text("\n".join(s["ilan"] for s in sonuclar if s["durum"] in ("PASS", "ZATEN")) + "\n",
                                      encoding="utf-8")
    log("OZET " + json.dumps({k: v for k, v in ozet.items() if k != "ilanlar"}, ensure_ascii=False))
    sys.exit(0 if tamam else 1)


if __name__ == "__main__":
    main()
