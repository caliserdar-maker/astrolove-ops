#!/usr/bin/env python3
"""Kupa fiyat zammi (Serdar 13-14 Kas 2026, Genel Merkez): Size fiyatlari 11 oz 12.90 -> 24.90, 15 oz 16.90 -> 29.90.
Kargo (ulke basina ucretli profil) DEGISMEZ. Iki aile:
  cift = bolum 60980873 "Zodiac Couple Mugs" (78 ilan), sade = bolum "Zodiac Sign Mugs" (12 ilan, tek burc; id bolum adindan okunur).
  SADE: Serdar 14 Kas teyidi ("Evet": sade kupalar da 24.90 / 29.90). Olcum kosu 43518188944: bolum 61221710, 12 ilan, 12 PLAN_OK,
  SKU bos, sku_on_property bos (gercek fixture testdata_kupa_sade_4607613712.json).
Yapi (ikisinde de, 31 Eki karari): Style 513 (8) x Size 514 (2) = 16 urun. Yontem kupa_fiyat.py'nin aynisi: ilan basina tek
PUT /listings/{id}/inventory, fiyat disi her alan birebir; stil-gorsel baglari once/sonra ada gore. updateListing YOK.
kupa_fiyat.py'den farklar: hedef/eski fiyat ters yonde; aile secimi; bolum ilan sayisi kontrolu; ATLA yalniz yaz modunda;
ilan basinda ve PUT oncesi kota "tahmini istek + 10" (okunamazsa KOTA_BEKLE); kisisellestirme sorulari once/sonra karsilastirilir;
PUT hata verirse yazmadan tek geri okuma kaydedilir; geri okuma tutmazsa stil bagi onarimi yapilmaz; ayri onay sozcukleri.
DOKUNMA: 4597843405 (eski taslak) yazilmaz.
Modlar: oku | yaz (--confirm KUPA_ZAM_1114 / KUPA_ZAM_1114_SADE; --hepsi: sonuna _HEPSI). Kapi: tahmini istek + 10, ilk FAIL'de DUR.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path[:0] = [str(KOK), str(KOK.parent / "etsy")]
from by_baski_ekle import kota_mi, sonuc_etiketi  # noqa: E402

ONAY = {"cift": "KUPA_ZAM_1114", "sade": "KUPA_ZAM_1114_SADE"}
ONAY_HEPSI = {k: v + "_HEPSI" for k, v in ONAY.items()}
BOLUM_ID = {"cift": 60980873}
BOLUM_AD = {"cift": "Zodiac Couple Mugs", "sade": "Zodiac Sign Mugs"}
BEKLENEN = {"cift": 78, "sade": 12}   # sade: olculdu 12 (kosu 43518188944; canli_yapi_olc.py:40'taki 11 eski)
SADE_YAZ_ACIK = True   # Serdar 14 Kas teyidi
INV_YOL = "/listings/{lid}/inventory"
DOKUNMA = {"4597843405"}
P_RENK, P_BOY = 513, 514
HEDEF = {"11 oz": (24.90, 12.90), "15 oz": (29.90, 16.90)}   # boy -> (yeni, eski canli)
ISTEK_TAHMIN = 20   # ilan basi en kotu: 4 oku + PUT + 3x4 geri okuma + 2 bag (19) + 1 pay
METIN = re.compile(r"\$\s?\d|\bUSD\b|free shipping|shipping to", re.I)
OUT = Path("out")


def log(m):
    print(m, flush=True)


def para(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def pvd(pr):
    return {pv.get("property_id"): pv for pv in pr.get("property_values") or []}


def deger(pr, pid):
    v = (pvd(pr).get(pid) or {}).get("values") or []
    return v[0] if len(v) == 1 else None


def boy_kodu(etiket):
    return (etiket or "").strip() or None


def anahtar(pr):
    return tuple((pv.get("property_id"), tuple(pv.get("values") or [])) for pv in pr.get("property_values") or [])


def fiyatlar(pr):
    return [para(o.get("price")) for o in pr.get("offerings") or [] if not o.get("is_deleted")]


def imza(pr):
    """value_id HARIC (Etsy PUT'ta yenileyebilir; ayrica not edilir)."""
    pvs = tuple((pv.get("property_id"), pv.get("property_name"), tuple(pv.get("values") or []))
                for pv in pr.get("property_values") or [])
    offs = tuple((o.get("quantity"), bool(o.get("is_enabled")), o.get("readiness_state_id"))
                 for o in pr.get("offerings") or [] if not o.get("is_deleted"))
    return (pr.get("sku") or "", pvs, offs)


def plan(inv):
    """-> (urunler, hatalar, zaten)"""
    h, pr_list = [], []
    urunler = [p for p in inv.get("products") or [] if not p.get("is_deleted")]
    if len(urunler) != 16:
        h.append(f"urun sayisi {len(urunler)} (16 bekleniyordu: 8 stil x 2 boy)")
    if len({anahtar(p) for p in urunler}) != len(urunler):
        h.append("tekrar eden ozellik kombinasyonu")
    boy_say = {}
    for p in urunler:
        if len(fiyatlar(p)) != 1:
            h.append(f"{p.get('sku')}: canli teklif sayisi {len(fiyatlar(p))}")
            continue
        if deger(p, P_RENK) is None:
            h.append(f"{p.get('sku')}: stil (513) yok")
            continue
        k = boy_kodu(deger(p, P_BOY))
        if k not in HEDEF:
            h.append(f"bilinmeyen boy: {deger(p, P_BOY)}")
            continue
        yeni, eski = HEDEF[k]
        if fiyatlar(p)[0] not in (yeni, eski):
            h.append(f"{p.get('sku')} {k}: fiyat {fiyatlar(p)[0]} (beklenen eski {eski} ya da hedef {yeni})")
        boy_say[k] = boy_say.get(k, 0) + 1
        pr_list.append(p)
    if boy_say != {"11 oz": 8, "15 oz": 8}:
        h.append(f"boy dagilimi beklenmedik: {boy_say}")
    zaten = bool(pr_list) and all(fiyatlar(p) == [HEDEF[boy_kodu(deger(p, P_BOY))][0]] for p in pr_list)
    return pr_list, h, zaten


def yeni_fiyat(pr):
    k = boy_kodu(deger(pr, P_BOY))
    return HEDEF[k][0] if k in HEDEF else None


def govde(inv):
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
        yf = yeni_fiyat(pr)
        offs = []
        for o in pr.get("offerings") or []:
            if o.get("is_deleted"):
                continue
            off = {"price": yf if yf is not None else para(o.get("price")), "quantity": o.get("quantity"),
                   "is_enabled": bool(o.get("is_enabled"))}
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


def bag_gecerli(inv, vimg):
    """8 stil-gorsel baginin hepsi bugunku stil value_id'lerine denk mi."""
    stil = {i for pr in inv.get("products") or [] for pv in pr.get("property_values") or []
            if pv.get("property_id") == P_RENK for i in pv.get("value_ids") or []}
    bag = {r.get("value_id") for r in vimg if r.get("property_id") == P_RENK}
    return len(vimg) == 8 and len(stil) == 8 and bag == stil


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "inventory": api.get(INV_YOL.format(lid=lid)) or {},
            "vimg": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
            "per": (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []}


def kisisel(L):
    return {k: L.get(k) for k in ("is_personalizable", "personalization_is_required", "personalization_char_count_max",
                                   "personalization_instructions")}


def soru_imza(per):
    """kisisellestirme sorulari (kupa_taslak.py:546-548 POST ucu); kimlik alanlari haric."""
    return sorted(json.dumps({k: v for k, v in (q or {}).items() if k not in ("question_id",)}, sort_keys=True) for q in per or [])


def kota_yeter(kalan, sinir):
    """PUT'tan hemen once: kalan okunamadiysa (None) ya da tahmini istek + sinir altindaysa False."""
    return kalan is not None and int(kalan) >= ISTEK_TAHMIN + sinir


def ilan_isle(api, shop, lid, yaz, R):
    from etsy_common import KOTA_SINIRI
    d = OUT / lid
    d.mkdir(parents=True, exist_ok=True)
    if yaz and not kota_yeter(api.remaining, KOTA_SINIRI):   # ilan basinda (okumalar dahil tahmin)
        R["durum"] = f"KOTA_BEKLE kalan {api.remaining} < {ISTEK_TAHMIN} + {KOTA_SINIRI} ya da okunamadi (ilan baslamadi)"
        return R
    sn = anlik(api, shop, lid)
    L, inv = sn["listing"], sn["inventory"]
    (d / "ONCE.json").write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
    prs, h, zaten = plan(inv)
    metin = sorted({m.group(0) for alan in ("description", "personalization_instructions") for m in METIN.finditer(L.get(alan) or "")})
    R.update(state=L.get("state"), urun_n=len(prs), kapi=h, renk_bag_once=renk_haritasi(inv, sn["vimg"]), metinde_fiyat_kargo=metin,
             fiyatlar_once=sorted({(boy_kodu(deger(p, P_BOY)), fiyatlar(p)[0]) for p in prs}))
    R["stil_bag_sayi"] = len(sn["vimg"])
    if not bag_gecerli(inv, sn["vimg"]):
        h.append(f"stil-gorsel bagi gecersiz ya da eksik ({len(sn['vimg'])}/8, value_id eslesmesi) (once onarilmali)")
    if L.get("state") != "active":
        R["durum"] = "ATLANDI_STATE"
        return R
    if h:
        R["durum"] = "FAIL_KAPI"
        return R
    if zaten:
        R["durum"] = "ZATEN"
        return R
    if not yaz:
        R["durum"] = "PLAN_OK"
        return R
    if not kota_yeter(api.remaining, KOTA_SINIRI):   # PUT'tan HEMEN once
        R["durum"] = f"KOTA_BEKLE kalan {api.remaining} < {ISTEK_TAHMIN} + {KOTA_SINIRI} ya da okunamadi (yazma yok)"
        return R
    body = govde(inv)
    (d / "PUT.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    R["put_gonderildi"] = True
    try:
        api.put_json(INV_YOL.format(lid=lid), body)
    except BaseException:
        try:   # yazmadan tek geri okuma: PUT islenmis olabilir (fiyat ve stil bagi rapora)
            snx = anlik(api, shop, lid)
            (d / "SONRA_HATA.json").write_text(json.dumps(snx, ensure_ascii=False, indent=1), encoding="utf-8")
            R["hata_sonrasi"] = {"fiyatlar": sorted({(boy_kodu(deger(p, P_BOY)), (fiyatlar(p) or [None])[0])
                                                    for p in snx["inventory"].get("products") or [] if not p.get("is_deleted")}, key=str),
                                 "stil_bag_gecerli": bag_gecerli(snx["inventory"], snx["vimg"])}
        except BaseException as e2:  # noqa: BLE001
            R["hata_sonrasi"] = f"okunamadi: {type(e2).__name__}"
        raise
    R["yazildi"] = "envanter"
    f = ["okunmadi"]
    sn2 = {"listing": {}, "inventory": {}, "vimg": []}
    for _ in range(3):
        sn2 = anlik(api, shop, lid)
        L2, inv2 = sn2["listing"], sn2["inventory"]
        f = []
        once = {anahtar(p): p for p in inv.get("products") or [] if not p.get("is_deleted")}
        sonra = {anahtar(p): p for p in inv2.get("products") or [] if not p.get("is_deleted")}
        if set(once) != set(sonra):
            f.append(f"urun kumesi degisti: {len(once)} -> {len(sonra)}")
        for k, p in once.items():
            q = sonra.get(k)
            if q is None:
                continue
            yf = yeni_fiyat(p)
            hedef = [yf] if yf is not None else fiyatlar(p)
            if fiyatlar(q) != hedef:
                f.append(f"fiyat {p.get('sku')} {k[1:]}: {fiyatlar(q)} != {hedef}")
            if imza(q) != imza(p):
                f.append(f"fiyat disi alan degisti: {p.get('sku')} {k[1:]}")
        for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
            if sorted(inv.get(k) or []) != sorted(inv2.get(k) or []):
                f.append(f"{k} degisti")
        if [anahtar(p) for p in inv.get("products") or [] if not p.get("is_deleted")] != \
                [anahtar(p) for p in inv2.get("products") or [] if not p.get("is_deleted")]:
            f.append("urun sirasi degisti")
        if L2.get("state") != L.get("state"):
            f.append(f"state {L.get('state')} -> {L2.get('state')}")
        if kisisel(L2) != kisisel(L):
            f.append("kisisellestirme degisti")
        if soru_imza(sn2["per"]) != soru_imza(sn["per"]):
            f.append("kisisellestirme sorulari degisti")
        if not f:
            break
        time.sleep(10)
    inv2 = sn2["inventory"]
    v_once, v_sonra = renk_haritasi(inv, sn["vimg"]), renk_haritasi(inv2, sn2["vimg"])
    R["renk_onarim"] = "gerekmedi"
    if v_sonra != v_once and f:
        R["renk_onarim"] = "yapilmadi (geri okuma tutmadi)"
        f.append("stil bagi degisti, onarim yapilmadi")
    elif v_sonra != v_once:
        vid, pid = {}, None
        for pr in inv2.get("products") or []:
            for pv in pr.get("property_values") or []:
                if pv.get("property_id") != P_RENK:
                    continue
                for v, i in zip(pv.get("values") or [], pv.get("value_ids") or []):
                    if v in v_once:
                        vid.setdefault(v, i)
                        pid = pid or pv.get("property_id")
        eksik = [c for c in v_once if c not in vid]
        if pid is None or eksik:
            f.append(f"stil bagi onarilamaz: {eksik}")
        else:
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                          {"variation_images": [{"property_id": pid, "value_id": vid[c], "image_id": int(i)} for c, i in v_once.items()]})
            R["renk_onarim"] = "ada gore geri yazildi"
            v3 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
            if renk_haritasi(inv2, v3) != v_once:
                f.append("stil bagi geri yazilamadi")
    vid_l = lambda i: sorted((pv.get("property_id"), v, tuple(pv.get("value_ids") or [])) for p in i.get("products") or []
                             for pv in p.get("property_values") or [] for v in pv.get("values") or [])
    if vid_l(inv) != vid_l(inv2):
        R["not_vid"] = "value_id degisti (fiyat/sku/teklif ayni; stil baglari ada gore kontrol edildi)"
    (d / "SONRA.json").write_text(json.dumps(sn2, ensure_ascii=False, indent=1), encoding="utf-8")
    R["fiyatlar_sonra"] = sorted({(boy_kodu(deger(p, P_BOY)), (fiyatlar(p) or [None])[0])
                                  for p in inv2.get("products") or [] if not p.get("is_deleted")}, key=str)
    R.update(hatalar=f, durum="PASS" if not f else "FAIL", kota=api.remaining)
    return R


def bolum_id(api, shop, aile):
    """cift: sabit id (bolum adiyla da dogrulanir); sade: bolum adindan tek eslesme, yoksa ya da birden coksa DUR."""
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    es = [s for s in secs if (s.get("title") or "").strip() == BOLUM_AD[aile]]
    if len(es) != 1:
        raise SystemExit(f"DUR: '{BOLUM_AD[aile]}' bolumu {len(es)} kez bulundu (1 bekleniyordu)")
    sid = int(es[0].get("shop_section_id"))
    if aile in BOLUM_ID and sid != BOLUM_ID[aile]:
        raise SystemExit(f"DUR: {aile} bolum id {sid} != {BOLUM_ID[aile]}")
    return sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--aile", choices=sorted(ONAY), required=True)
    ap.add_argument("--ilanlar", default="")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    OUT.mkdir(exist_ok=True)
    sonuc, oz_hata, api, ids, tamam, bolum_n, sid, kapsam = [], None, None, [], False, None, None, None
    t0 = time.time()
    try:
        bek = (ONAY_HEPSI if a.hepsi else ONAY)[a.aile]
        if yaz and a.aile == "sade" and not SADE_YAZ_ACIK:
            raise SystemExit("DUR: sade yazimi kapali (Serdar teyidi ve sade olcumu bekleniyor)")
        if yaz and a.confirm != bek:
            raise SystemExit(f"DUR: yaz icin --confirm {bek}")
        if a.hepsi == bool(a.ilanlar.strip()):
            raise SystemExit("DUR: ya --ilanlar ya --hepsi")
        from etsy_common import Etsy, TokenStore, mask
        k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
        mask(k_); mask(s_)
        store = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
        if store.needs_refresh():
            store.refresh()
        api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
        sid = bolum_id(api, shop, a.aile)
        tum, off = [], 0
        while True:
            dd = api.get(f"/shops/{shop}/shop-sections/listings", params={"shop_section_ids": sid, "limit": 100, "offset": off}) or {}
            rr = dd.get("results") or []
            tum += [str(x.get("listing_id")) for x in rr if x.get("listing_id")]
            if len(rr) < 100:
                break
            off += 100
        tum = [x for x in dict.fromkeys(tum) if x not in DOKUNMA]
        bolum_n = len(tum)
        log(f"{a.aile} bolumu {sid}: {bolum_n} ilan (DOKUNMA haric; beklenen {BEKLENEN[a.aile]})")
        if a.hepsi:
            if yaz and bolum_n != BEKLENEN[a.aile]:
                raise SystemExit(f"DUR: bolumde {bolum_n} ilan, beklenen {BEKLENEN[a.aile]} (yazma yok)")
            atla = {x.strip() for x in os.environ.get("ATLA", "").split(",") if x.strip()} if yaz else set()
            ids = [x for x in tum if x not in atla]
            onceki = {x.strip() for x in os.environ.get("TAMAM_LISTE", "").split(",") if x.strip()}   # onceki kosularin TAMAM'i
            kapsam = (tum, onceki)   # elle ATLA'ya yazilip TAMAM'da olmayan ilan kapsam_eksik sayilir
        else:
            ids = [x.strip() for x in a.ilanlar.split(",") if x.strip()]
            if [x for x in ids if x not in tum]:
                raise SystemExit("DUR: ilan bu bolumde degil ya da DOKUNMA listesinde")
        for i, lid in enumerate(ids, 1):
            R = {"ilan": lid}
            try:
                api.kota_kapisi(f"ilan {lid}")
                ilan_isle(api, shop, lid, yaz, R)
            except SystemExit as e:
                R["durum"] = f"DUR: {str(e)[:400]}"
                if R.get("yazildi") or R.get("put_gonderildi"):
                    R["durum"] = f"FAIL_YAZILDI_DOGRULANMADI: {str(e)[:300]}"
            except Exception as e:  # noqa: BLE001
                R["durum"] = f"FAIL_ISTISNA: {type(e).__name__}: {str(e)[:300]}"
                if R.get("yazildi") or R.get("put_gonderildi"):
                    R["durum"] = "FAIL_YAZILDI_DOGRULANMADI: " + R["durum"]
            sonuc.append(R)
            g = time.time() - t0
            log(f"[{i}/{len(ids)}] {100 * i // len(ids)}% gecen {g:.0f}s kalan ~{g / i * (len(ids) - i):.0f}s | {lid} {R['durum'][:150]} kota={api.remaining}")
            if R["durum"].startswith(("FAIL", "DUR", "KOTA_BEKLE")) and (yaz or kota_mi(R["durum"])):
                break
    except BaseException as e:  # noqa: BLE001
        oz_hata = f"{type(e).__name__}: {str(e)[:400]}"
        log("GENEL HATA " + oz_hata)
    finally:
        say = {}
        for r in sonuc:
            k = r["durum"].split(" ")[0].rstrip(":")
            say[k] = say.get(k, 0) + 1
        iyi = ("PASS", "ZATEN") if yaz else ("PLAN_OK", "ZATEN")
        tamam = oz_hata is None and len(sonuc) == len(ids) and all(r["durum"].split(" ")[0] in iyi for r in sonuc)
        et = sonuc_etiketi(sonuc, oz_hata, tamam)
        if any(r["durum"].startswith("FAIL_YAZILDI") for r in sonuc) or (yaz and any(r["durum"] == "ATLANDI_STATE" for r in sonuc)):
            et = "HATA"
        kapsam_eksik = None
        if yaz and kapsam:   # hepsi + yaz: bolumdeki her ilan ya onceki TAMAM'da ya bu kosuda PASS/ZATEN mi
            bitti = kapsam[1] | {r["ilan"] for r in sonuc if r["durum"] in ("PASS", "ZATEN")}
            kapsam_eksik = [x for x in kapsam[0] if x not in bitti]
            if kapsam_eksik and tamam:   # yalniz elle atlanan ilan varsa (kota yarimi zaten tamam=False)
                tamam, et = False, "HATA"
        oz = {"mod": a.mod, "aile": a.aile, "bolum": sid, "bolum_ilan": bolum_n, "beklenen": BEKLENEN[a.aile], "kapsam_eksik": kapsam_eksik,
              "istenen": len(ids), "islenen": len(sonuc), "sayim": say, "kota_son": api.remaining if api else None,
              "genel_hata": oz_hata, "sonuc": et, "ilanlar": sonuc}
        (OUT / f"KUPA_ZAM_1114_{a.mod.upper()}.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        if yaz:
            (OUT / "TAMAM_EK.txt").write_text("".join(r["ilan"] + "\n" for r in sonuc if r["durum"] in ("PASS", "ZATEN")))
        log("OZET " + json.dumps({k: v for k, v in oz.items() if k != "ilanlar"}, ensure_ascii=False))
        print(f"::notice::SONUC {et} {a.mod} {a.aile} islenen {len(sonuc)}/{len(ids)} sayim {say} kota {oz['kota_son']}", flush=True)
    sys.exit(0 if (tamam or et == "KOTA") else 1)


if __name__ == "__main__":
    main()
