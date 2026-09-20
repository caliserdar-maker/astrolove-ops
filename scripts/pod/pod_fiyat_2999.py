#!/usr/bin/env python3
"""POD 78 ilan: 30.99 USD olan TUM secenekler -> 29.99 USD.

Diger fiyatlar, stok, SKU, secenek yapisi, varyasyon-gorsel baglantilari,
baslik ve durum AYNEN kalir.

  kuru   : 78 ilanin envanteri salt okunur -> FIYAT_PLANI.csv (+ORNEK_ENVANTER.json).
           KAPI: 30.99 yoksa / 8x10 disinda da varsa / para birimi USD degilse /
           ilanlar arasinda yapi farki varsa -> YAZMA YOK.
  pilot  : tek ilan (4570110641) yazilir, sonra canli geri okuma (fiyatlar, 5
           varyasyon baglantisi, 13 gorsel, video, baslik, durum).
  toplu  : kalan ilanlar; ilan basina YEDEK/{ilan}.json, state.json, kota tabani.

Yazma sonrasi herhangi bir kapi duserse TUM KOSU DURUR.
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_FIYAT_2999"
ILAN_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
PILOT = "4570110641"
ESKI, YENI = 30.99, 29.99
BOYUT_3099 = "8x10"
KOTA_ALT = 400
PLAN_SUTUN = ["listing_id", "cift", "urun", "teklif", "para", "adet_3099", "boyut_3099",
              "fiyatlar", "yapi", "durum", "neden"]
SONUC_SUTUN = ["listing_id", "cift", "durum", "degisen", "eski_fiyat", "yeni_fiyat",
               "kota", "sn", "neden"]
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def yukle(yerel, uzak):
    if rclone("copyto", str(yerel), f"{DRV}/{uzak}").returncode != 0:
        raise RuntimeError(f"Drive'a yuklenemedi: {uzak}")


def ilanlar():
    kayitlar = json.loads(ILAN_JSON.read_text(encoding="utf-8"))
    if isinstance(kayitlar, dict):
        kayitlar = kayitlar.get("listings") or kayitlar.get("items") or []
    return [(str(k["id"]), k.get("pair") or k.get("cift") or "") for k in kayitlar]


def para(p):
    """{amount,divisor} -> (float fiyat, para_birimi)."""
    if isinstance(p, dict):
        return (round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2),
                p.get("currency_code") or "")
    return (round(float(p or 0), 2), "")


def boyut_of(pr):
    for pv in pr.get("property_values") or []:
        if (pv.get("property_name") or "").lower() == "size" and pv.get("values"):
            return pv["values"][0]
    return ""


def envanter(api, lid):
    return api.get(f"/listings/{lid}/inventory") or {}


def denetle(inv):
    """(satir_sozlugu, hatalar[]). Salt okuma; yazma karari cagiranda."""
    urunler = inv.get("products") or []
    teklif, paralar, vur_3099, boyutlar, fiyatlar = 0, set(), [], set(), set()
    etiketler = []
    for pr in urunler:
        b = boyut_of(pr)
        if b not in etiketler:
            etiketler.append(b)
        for o in pr.get("offerings") or []:
            teklif += 1
            f, pb = para(o.get("price"))
            fiyatlar.add(f)
            if pb:
                paralar.add(pb)
            if abs(f - ESKI) < 1e-9:
                vur_3099.append((pr.get("sku"), b))
                boyutlar.add(b)
    def _liste(ad):
        return ",".join(sorted(str(x) for x in (inv.get(ad) or [])))

    yapi = "|".join([str(len(urunler)), str(teklif),
                     ";".join(sorted(str(e) for e in etiketler)),
                     _liste("price_on_property"), _liste("quantity_on_property"),
                     _liste("sku_on_property")])
    hatalar = []
    if not vur_3099:
        hatalar.append(f"{ESKI} yok")
    kotu = sorted({b for b in boyutlar if not str(b).startswith(BOYUT_3099)})
    if kotu:
        hatalar.append(f"{ESKI} {BOYUT_3099} disinda: {kotu}")
    if paralar - {"USD"}:
        hatalar.append(f"para birimi {sorted(paralar)}")
    satir = {"urun": len(urunler), "teklif": teklif, "para": ",".join(sorted(paralar)),
             "adet_3099": len(vur_3099), "boyut_3099": ";".join(sorted(boyutlar)),
             "fiyatlar": ";".join(f"{x:.2f}" for x in sorted(fiyatlar)), "yapi": yapi,
             "neden": " / ".join(hatalar)}
    return satir, hatalar


def govde(inv, value_ids=True):
    """Envanterin BIREBIR PUT govdesi; yalniz 30.99 -> 29.99. (govde, degisen_adet)."""
    urunler, degisen = [], 0
    for pr in inv.get("products") or []:
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if value_ids and pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            pvs.append(d)
        offs = []
        for o in pr.get("offerings") or []:
            f, _ = para(o.get("price"))
            if abs(f - ESKI) < 1e-9:
                f, degisen = YENI, degisen + 1
            off = {"price": f, "quantity": o.get("quantity"),
                   "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        urunler.append({"sku": pr.get("sku") or "", "property_values": pvs, "offerings": offs})
    b = {"products": urunler,
         "price_on_property": inv.get("price_on_property") or [],
         "quantity_on_property": inv.get("quantity_on_property") or [],
         "sku_on_property": inv.get("sku_on_property") or []}
    return b, degisen


def fiyat_haritasi(inv):
    """(sku, boyut) -> (fiyat, adet, acik) ; geri okuma karsilastirmasi icin."""
    h = {}
    for pr in inv.get("products") or []:
        for i, o in enumerate(pr.get("offerings") or []):
            f, pb = para(o.get("price"))
            h[(pr.get("sku"), boyut_of(pr), i)] = (f, o.get("quantity"),
                                                   bool(o.get("is_enabled")), pb)
    return h


def deger_adi(inv):
    """(property_id, value_id) -> deger adi."""
    h = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                h[(pv.get("property_id"), vid)] = val
    return h


def vimg(api, shop, lid):
    r = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {})
    return r.get("results") or []


def vmap(rows):
    return sorted((str(r.get("property_id")), str(r.get("value_id")), str(r.get("image_id")))
                  for r in rows)


def vadmap(rows, adlar):
    """(property_id, deger_adi) -> image_id  (deger id'si degisirse de karsilastirilir)."""
    return {(str(r.get("property_id")),
             r.get("value") or adlar.get((r.get("property_id"), r.get("value_id"))) or ""):
            str(r.get("image_id")) for r in rows}


def yaz_envanter(api, lid, inv):
    """PUT; value_ids reddedilirse bir kez value_ids'siz dener. (degisen,)"""
    b, degisen = govde(inv, value_ids=True)
    if degisen == 0:
        return 0
    try:
        api.put_json(f"/listings/{lid}/inventory", b)
    except SystemExit as e:
        ilerle(f"  {lid}: PUT (value_ids ile) basarisiz -> value_ids'siz tekrar [{str(e)[:120]}]")
        b2, _ = govde(inv, value_ids=False)
        api.put_json(f"/listings/{lid}/inventory", b2)
    return degisen


def onar_varyasyon(api, shop, lid, once_rows, once_adlar, yeni_inv):
    """Varyasyon baglantilari PUT sonrasi bozulduysa ayni gorselleri geri yaz."""
    ad_to_new = {}
    for pid_vid, ad in deger_adi(yeni_inv).items():
        ad_to_new[(str(pid_vid[0]), ad)] = pid_vid[1]
    govde_v = []
    for r in once_rows:
        pid = r.get("property_id")
        ad = r.get("value") or once_adlar.get((pid, r.get("value_id"))) or ""
        vid = ad_to_new.get((str(pid), ad), r.get("value_id"))
        govde_v.append({"property_id": pid, "value_id": vid, "image_id": int(r.get("image_id"))})
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": govde_v})
    return govde_v


def tek_ilan(api, shop, lid, cift, isd, tam_dogrulama=False):
    """Tek ilanin fiyat yazimi. Donus: (durum, degisen, neden)."""
    inv0 = envanter(api, lid)
    satir, hatalar = denetle(inv0)
    if hatalar:
        return "ATLANDI", 0, satir["neden"], satir
    v0 = vimg(api, shop, lid)
    adlar0 = deger_adi(inv0)
    L0 = api.get(f"/listings/{lid}") or {} if tam_dogrulama else {}
    g0 = (api.get(f"/listings/{lid}/images") or {}).get("results") or [] if tam_dogrulama else []
    vid0 = sorted(str(v.get("video_id")) for v in
                  ((api.get(f"/listings/{lid}/videos") or {}).get("results") or [])) if tam_dogrulama else []
    yedek = isd / f"{lid}.json"
    yedek.write_text(json.dumps(
        {"listing": lid, "cift": cift,
         "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "envanter": inv0, "varyasyon": v0,
         "baslik": L0.get("title"), "durum_ilan": L0.get("state")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    yukle(yedek, f"YEDEK/{lid}.json")

    degisen = yaz_envanter(api, lid, inv0)

    inv1 = envanter(api, lid)
    v1 = vimg(api, shop, lid)
    beklenen = {k: ((YENI if abs(v[0] - ESKI) < 1e-9 else v[0]), v[1], v[2], v[3])
                for k, v in fiyat_haritasi(inv0).items()}
    canli = fiyat_haritasi(inv1)
    if canli != beklenen:
        fark = [f"{k}: {beklenen.get(k)} -> {canli.get(k)}"
                for k in set(beklenen) | set(canli) if beklenen.get(k) != canli.get(k)]
        raise RuntimeError(f"FIYAT GERI OKUMA FARKI ({len(fark)}): {fark[:4]}")
    hedef_v = vadmap(v0, adlar0)
    if vadmap(v1, deger_adi(inv1)) != hedef_v:
        ilerle(f"  {lid}: varyasyon baglantisi bozuldu ({len(v0)} -> {len(v1)}), geri yaziliyor")
        onar_varyasyon(api, shop, lid, v0, adlar0, inv1)
        inv1 = envanter(api, lid)
        v1 = vimg(api, shop, lid)
        if vadmap(v1, deger_adi(inv1)) != hedef_v:
            raise RuntimeError(f"VARYASYON KAPISI: {len(v1)} baglanti, hedef {len(v0)}")
    kapilar = {"varyasyon": len(v1) == len(v0), "urun_sayisi":
               len(inv1.get("products") or []) == len(inv0.get("products") or [])}
    if tam_dogrulama:
        L1 = api.get(f"/listings/{lid}") or {}
        g1 = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
        vid1 = sorted(str(v.get("video_id")) for v in
                      ((api.get(f"/listings/{lid}/videos") or {}).get("results") or []))
        kapilar.update({
            "baslik": L0.get("title") == L1.get("title"),
            "durum": L0.get("state") == L1.get("state"),
            "gorsel_13": len(g1) == len(g0) == 13,
            "gorsel_sira": [(str(x.get("listing_image_id")), x.get("rank")) for x in g0]
                           == [(str(x.get("listing_image_id")), x.get("rank")) for x in g1],
            "video": vid0 == vid1})
    if not all(kapilar.values()):
        raise RuntimeError(f"YAZMA SONRASI KAPI {kapilar}")
    return "TAMAM", degisen, "", satir


def kuru(api, shop, isd, limit):
    liste = ilanlar()
    if limit:
        liste = liste[:limit]
    yol = isd / "FIYAT_PLANI.csv"
    with yol.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PLAN_SUTUN, extrasaction="ignore")
        w.writeheader()
        yapilar, kotu, ornek = {}, [], None
        t0 = time.time()
        for j, (lid, cift) in enumerate(liste, start=1):
            inv = envanter(api, lid)
            if ornek is None:
                ornek = inv
            satir, hatalar = denetle(inv)
            satir.update({"listing_id": lid, "cift": cift,
                          "durum": "OK" if not hatalar else "KAPI"})
            yapilar.setdefault(satir["yapi"], []).append(lid)
            if hatalar:
                kotu.append((lid, satir["neden"]))
            w.writerow(satir)
            fh.flush()
            if j % 5 == 0 or j == len(liste):
                gec = time.time() - t0
                ilerle(f"{j}/{len(liste)} (%{100 * j / len(liste):.1f}) | gecen {sure_yaz(gec)} "
                       f"| kalan ~{sure_yaz(gec / j * (len(liste) - j))} | kota {api.remaining}")
    yukle(yol, "FIYAT_PLANI.csv")
    orn = isd / "ORNEK_ENVANTER.json"
    orn.write_text(json.dumps(ornek, ensure_ascii=False, indent=1), encoding="utf-8")
    yukle(orn, "ORNEK_ENVANTER.json")
    ozet = {"ilan": len(liste), "kapi_dusen": len(kotu), "ilk_kapilar": kotu[:5],
            "yapi_cesidi": len(yapilar),
            "yapilar": {k[:80]: len(v) for k, v in yapilar.items()},
            "kota": api.remaining}
    print(json.dumps(ozet, ensure_ascii=False))
    (isd / "KURU_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    yukle(isd / "KURU_OZET.json", "KURU_OZET.json")
    if kotu or len(yapilar) != 1:
        ilerle("DUR: KAPI dustu -> yazmaya gecilmez")
        return 3
    ilerle(f"KAPI GECTI: {len(liste)} ilan, tek yapi, tumunde {ESKI} yalniz {BOYUT_3099}")
    return 0


def toplu(api, shop, isd, sadece, limit, apply_):
    liste = [(l, c) for l, c in ilanlar() if (not sadece or l in sadece)]
    if limit:
        liste = liste[:limit]
    durum_yerel = isd / "state.json"
    durum = {"tamam": {}, "atlandi": {}, "hata": {}}
    if rclone("copyto", f"{DRV}/state.json", str(durum_yerel)).returncode == 0:
        try:
            durum = json.loads(durum_yerel.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    for k in ("tamam", "atlandi", "hata"):
        durum.setdefault(k, {})
    kalan = [(l, c) for l, c in liste if l not in durum["tamam"]]
    ilerle(f"kota {api.remaining} | {len(liste)} ilan | tamam {len(durum['tamam'])} "
           f"| kosulacak {len(kalan)} | mod {'YAZMA' if apply_ else 'KURU'}")

    sonuc = isd / "SONUC_FIYAT.csv"
    if rclone("copyto", f"{DRV}/SONUC_FIYAT.csv", str(sonuc)).returncode != 0:
        with sonuc.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(SONUC_SUTUN)

    def yaz(satir):
        with sonuc.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=SONUC_SUTUN, extrasaction="ignore").writerow(satir)
        yukle(sonuc, "SONUC_FIYAT.csv")
        durum_yerel.write_text(json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
        yukle(durum_yerel, "state.json")

    t0 = time.time()
    for j, (lid, cift) in enumerate(kalan, start=1):
        ts = time.time()
        kota = int(api.remaining or 0)
        if kota and kota < KOTA_ALT:
            ilerle(f"DUR: kota {kota} < {KOTA_ALT}")
            break
        satir = {"listing_id": lid, "cift": cift, "durum": "ATLANDI", "degisen": 0,
                 "eski_fiyat": f"{ESKI:.2f}", "yeni_fiyat": f"{YENI:.2f}", "kota": kota,
                 "neden": ""}
        try:
            d, degisen, neden, den = tek_ilan(api, shop, lid, cift, isd,
                                              tam_dogrulama=(lid == PILOT or len(kalan) == 1))
            satir.update({"durum": d, "degisen": degisen, "neden": neden})
            if d == "TAMAM":
                durum["tamam"][lid] = {"cift": cift, "degisen": degisen}
                durum["atlandi"].pop(lid, None)
            else:
                durum["atlandi"][lid] = neden
        except Exception as e:
            satir.update({"durum": "HATA", "neden": f"{type(e).__name__}: {e}"[:220]})
            durum["hata"][lid] = satir["neden"]
            satir["sn"] = round(time.time() - ts, 1)
            yaz(satir)
            ilerle(f"DUR: {lid} {cift}: {satir['neden']}")
            print(json.dumps({"durdu": lid, "neden": satir["neden"],
                              "tamam": len(durum["tamam"])}, ensure_ascii=False))
            return 3
        satir["sn"] = round(time.time() - ts, 1)
        yaz(satir)
        gec = time.time() - t0
        ilerle(f"{j}/{len(kalan)} (%{100 * j / len(kalan):.1f}) {lid} {cift} {satir['durum']} "
               f"{satir['degisen']} secenek {satir['neden'][:40]} | gecen {sure_yaz(gec)} "
               f"| kalan ~{sure_yaz(gec / j * (len(kalan) - j))} | kota {api.remaining}")
    print(json.dumps({"tamam": len(durum["tamam"]), "atlandi": len(durum["atlandi"]),
                      "hata": len(durum["hata"]), "kota": api.remaining}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["kuru", "pilot", "toplu"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--listing", default=PILOT)
    ap.add_argument("--is-dizin", default="_work/fiyat")
    a = ap.parse_args()
    if a.mod in ("pilot", "toplu") and a.apply and a.confirm != "FIYAT_2999":
        raise SystemExit("DUR: apply icin confirm 'FIYAT_2999' olmali")
    if a.mod in ("pilot", "toplu") and not a.apply:
        raise SystemExit("DUR: pilot/toplu yalniz --apply ile kosar (kuru icin mod=kuru)")
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    ilerle(f"baslangic kotasi {api.remaining} | mod {a.mod}")
    if a.mod == "kuru":
        return kuru(api, shop, isd, a.limit)
    if a.mod == "pilot":
        return toplu(api, shop, isd, {a.listing}, 0, True)
    return toplu(api, shop, isd, None, a.limit, True)


if __name__ == "__main__":
    sys.exit(main())
