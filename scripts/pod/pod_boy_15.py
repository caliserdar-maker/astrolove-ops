#!/usr/bin/env python3
"""POD 15 BOY: menu sirasi (fiyata gore artan) + fiyat duzeltmesi + Size Guide + aciklama.

Serdar onayi 21 Eyl 2026: (1) boy menusu fiyata gore kucukten buyuge siralanir,
(2) dort boyun fiyati psikolojik esigin altina cekilir, (3) pilot gecerse kalan 77 ilana
ayni degisiklik uygulanir.

MENU SIRASI NEYE GORE? Etsy menuyu envanterdeki `products` dizisinin sirasina gore gosterir;
value_id olusturma sirasina gore DEGIL. Kanit (pilot 4570110641, 21 Eyl): 5x7'nin value_id'si
(1517848425163) tum boylarin en yenisi oldugu halde, dizide basa konuldugu icin geri okumada
1. sirada dondu. Bu betik de sirayi yalniz dizi sirasiyla kurar ve geri okumada dogrular.

Modlar:
  oku   : tek ilan, salt okuma. Plan (sira + fiyat farklari + aciklama diff) yazdirilir.
  yaz   : tek ilan yazar (--confirm BOY_15).
  toplu : pod_changes_v2.json'daki tum ilanlar (--atla ile pilot haric). state.json ile
          yeniden baslatilabilir; kota --kota-alt altina duserse durur.

Her ilanda kapilar: ilan 'active', bilinmeyen boy yok, 5 edisyon tam, geri okumada
15/15 hedef sira + 75 urun + fiyatlar tablo ile birebir + varyasyon-gorsel 5/5 +
galeri 13 (sira 1..13) + aciklama yalniz beklenen bolumde degismis.
Yazmadan once kapi tutmazsa ilan ATLANIR; yazdiktan sonra tutmazsa TUM KOSU DURUR.
"""
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore  # noqa: E402
from pod_sku import SKU_RE  # noqa: E402
import pod_pilot_15 as P  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
ILAN_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
SG_RANK = P.SG_RANK

# Hedef menu sirasi ve fiyatlar (5 edisyonun hepsinde ayni). Sira = bu listenin sirasi;
# esit fiyatta (16x24 / A2) sira burada yazildigi gibidir.
HEDEF = [
    ("5x7", 19.99), ("8x10", 29.99), ("A4", 32.99), ("11x14", 36.99), ("12x16", 39.99),
    ("A3", 42.99), ("12x18", 43.99), ("16x20", 47.99), ("16x24", 49.99), ("A2", 49.99),
    ("18x24", 56.99), ("20x30", 79.99), ("A1", 89.99), ("24x36", 99.99), ("30x40", 124.99),
]
HEDEF_FIYAT = dict(HEDEF)
HEDEF_SIRA = [k for k, _ in HEDEF]
FIYAT_DESE = re.compile(r"(?:US\s*)?\$\s*\d|\b\d{1,3}[.,]\d{2}\s*(?:USD|\$)")
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def anahtar_of(etiket):
    """'4:5 · 8x10 in (20×25 cm)' -> '8x10' ; 'A-series · A4 (21×30 cm)' -> 'A4'."""
    m = re.match(r"^.*? · (\S+?)(?: in)? \(", etiket or "")
    return m.group(1) if m else None


def hedef_etiketler(inv):
    """Hedef sirayla canli/yeni boy etiketleri (menu sirasinin dogrulanacagi liste)."""
    etiket_of, a_grup = {}, None
    for pr in inv.get("products") or []:
        lab = P.deger(pr, "size") or ""
        k = anahtar_of(lab)
        if k:
            etiket_of.setdefault(k, lab)
        m = re.match(r"^(.*?) · (A[0-9]) \(", lab)
        if m:
            a_grup = m.group(1)
    out = []
    for k, _f in HEDEF:
        if k in etiket_of:
            out.append(etiket_of[k])
        else:
            y = next(y for y in P.YENI if y["anahtar"] == k)
            grup = a_grup if y["konum"] == "a_sonu" else y["grup"]
            out.append(P.etiket_uret(grup, y["inc"], y["cm"]))
    return out, etiket_of, a_grup


def govde_hedef(inv):
    """Hedef sira + hedef fiyatlarla envanter govdesi. Donus: (body, hedef_etiket, notlar)."""
    urunler_eski = inv.get("products") or []
    if not urunler_eski:
        raise ValueError("envanter bos")
    renk_pv_adi = "primary color" if P.pv_of(urunler_eski[0], "primary color") else "color"
    if not P.pv_of(urunler_eski[0], "size"):
        raise ValueError("Size ozelligi yok")
    etiketler, etiket_of, a_grup = hedef_etiketler(inv)
    if a_grup is None:
        raise ValueError("A serisi etiketi okunamadi")
    bilinmeyen = sorted(k for k in etiket_of if k not in HEDEF_FIYAT)
    if bilinmeyen:
        raise ValueError(f"tabloda olmayan boy: {bilinmeyen}")

    renkler, gor = [], set()
    for pr in urunler_eski:
        r = P.deger(pr, renk_pv_adi)
        if r and r not in gor:
            gor.add(r)
            renkler.append(r)
    if len(renkler) != 5:
        raise ValueError(f"edisyon sayisi {len(renkler)} != 5")
    mevcut = {(anahtar_of(P.deger(pr, "size")), P.deger(pr, renk_pv_adi)): pr for pr in urunler_eski}
    ornek = {r: next(pr for pr in urunler_eski if P.deger(pr, renk_pv_adi) == r) for r in renkler}

    def pv_kopya(pr, yeni_etiket=None):
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            if yeni_etiket and (pv.get("property_name") or "").lower() == "size":
                d["values"] = [yeni_etiket]
                d.pop("value_ids", None)          # yeni deger: id'yi Etsy uretir
            pvs.append(d)
        return pvs

    def urun(pr, fiyat, yeni_etiket=None, yeni_sku=None):
        offs = []
        for o in pr.get("offerings") or []:
            off = {"price": fiyat, "quantity": o.get("quantity"),
                   "is_enabled": True if yeni_etiket else bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        return {"sku": yeni_sku if yeni_sku is not None else (pr.get("sku") or ""),
                "property_values": pv_kopya(pr, yeni_etiket), "offerings": offs or
                [{"price": fiyat, "quantity": 999, "is_enabled": True}]}

    urunler, notlar, eklenen = [], [], []
    for (k, fiyat), et in zip(HEDEF, etiketler):
        if k in etiket_of:
            for r in renkler:
                pr = mevcut.get((k, r))
                if pr is None:
                    raise ValueError(f"{k}: '{r}' edisyonu yok")
                urunler.append(urun(pr, fiyat))
            eski = P.para(((mevcut[(k, renkler[0])].get("offerings") or [{}])[0]).get("price"))
            if abs(eski - fiyat) > 1e-9:
                notlar.append(f"fiyat {k}: {eski:.2f} -> {fiyat:.2f}")
        else:
            eklenen.append(k)
            for r in renkler:
                pr = ornek[r]
                yeni_sku = re.sub(r"-[^-]+$", f"-{k}", pr.get("sku") or "")
                if not SKU_RE.match(yeni_sku):
                    raise ValueError(f"SKU kalibi tutmadi: {pr.get('sku')} -> {yeni_sku}")
                urunler.append(urun(pr, fiyat, yeni_etiket=et, yeni_sku=yeni_sku))
            notlar.append(f"eklendi {k}: '{et}' @ {fiyat:.2f} x5")
    b = {"products": urunler,
         "price_on_property": inv.get("price_on_property") or [],
         "quantity_on_property": inv.get("quantity_on_property") or [],
         "sku_on_property": inv.get("sku_on_property") or []}
    if inv.get("readiness_state_on_property"):
        b["readiness_state_on_property"] = inv["readiness_state_on_property"]
    return b, etiketler, notlar, eklenen


def aciklama_yeni(metin, dil):
    """15 boya cevirir; metin zaten 15 boyluksa dokunmaz."""
    if not metin:
        return metin, ["(bos)"]
    if ("✦ 15 SIZES" if dil == "en" else "✦ 15 РАЗМЕРОВ") in metin:
        return metin, ["(zaten 15 boy)"]
    return P.aciklama_15(metin, dil)


def fiyat_kontrol(inv, etiketler):
    """Geri okumada fiyatlar tablo ile birebir mi? Donus: hata listesi."""
    h = P.fiyat_haritasi(inv)
    hata = []
    for (k, fiyat), et in zip(HEDEF, etiketler):
        satir = [v for kk, v in h.items() if kk[1] == et]
        if len(satir) != 5:
            hata.append(f"{k}: {len(satir)} urun (5 bekleniyor)")
        kotu = [v[0] for v in satir if abs(v[0] - fiyat) > 1e-9]
        if kotu:
            hata.append(f"{k} fiyat {sorted(set(kotu))} != {fiyat:.2f}")
    return hata


def yedek_hizli(sn, isd, lid, etiket):
    """Anlik goruntuyu tek rclone cagrisiyla Drive'a yazar (6 ayri copyto yerine)."""
    d = isd / f"yedek_{etiket}"
    d.mkdir(parents=True, exist_ok=True)
    for k, v in sn.items():
        if k == "zaman_utc":
            continue
        (d / f"{k}_{etiket}.json").write_text(json.dumps(v, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    P.rclone("copy", str(d), f"{DRV}/YEDEK/{lid}", "-q")


# ------------------------------------------------------------------ tek ilan
def isle(api, shop, lid, cift, isd, yaz, kota_alt):
    """Tek ilani isler. Donus: (durum, neden, ayrinti). durum: TAMAM | ATLANDI | HATA."""
    ayrinti = {"listing_id": lid, "cift": cift}
    sn = P.anlik(api, shop, lid)
    L, inv = sn["listing"], sn["inventory"]
    ayrinti["baslik"] = (L.get("title") or "")[:60]
    if L.get("state") != "active":
        return "ATLANDI", f"durum {L.get('state')} (active degil)", ayrinti
    try:
        b, etiketler, notlar, eklenen = govde_hedef(inv)
    except ValueError as e:
        return "ATLANDI", f"envanter: {e}", ayrinti
    ayrinti["notlar"] = notlar
    ayrinti["urun_once"] = len(inv.get("products") or [])
    if len(b["products"]) != 75:
        return "ATLANDI", f"plan {len(b['products'])} urun (75 bekleniyor)", ayrinti

    # aciklama plani
    try:
        en_yeni, en_dgs = aciklama_yeni(L.get("description") or "", "en")
    except SystemExit as e:
        return "ATLANDI", f"EN aciklama: {str(e)[:120]}", ayrinti
    ru_eski = sn["ru"].get("description") or ""
    try:
        ru_yeni, ru_dgs = aciklama_yeni(ru_eski, "ru")
    except SystemExit as e:
        return "ATLANDI", f"RU aciklama: {str(e)[:120]}", ayrinti
    ayrinti["aciklama"] = {"en": en_dgs, "ru": ru_dgs}
    fiyatli = [s for s in (L.get("description") or "").split("\n") if FIYAT_DESE.search(s)]
    if fiyatli:
        ayrinti["aciklamada_fiyat"] = fiyatli[:3]      # raporlanir, DEGISTIRILMEZ

    # Size Guide karesi
    sg_gerek = True
    try:
        sg, sg_ed, fark, fark2, yeni_kart = P.size_guide_bul(sn["images"], cift, isd)
    except SystemExit as e:
        return "ATLANDI", f"Size Guide: {str(e)[:120]}", ayrinti
    ayirt = fark2 is None or (fark2 - fark) >= 5
    ayrinti["size_guide"] = {"rank": sg.get("rank"), "image_id": sg.get("listing_image_id"),
                             "edisyon": sg_ed, "fark": fark, "fark2": fark2}
    if fark <= 0.5 and sg.get("rank") == SG_RANK:
        sg_gerek = False                       # kart zaten yeni 15 boyluk kart
    elif fark > 12 or not (ayirt or sg.get("rank") == SG_RANK):
        return "ATLANDI", (f"Size Guide karesi kesin degil (fark {fark}, ikinci {fark2}, "
                           f"rank {sg.get('rank')})"), ayrinti

    if not yaz:
        ayrinti["plan_sira"] = etiketler
        return "PLAN", "; ".join(notlar) or "degisiklik yok", ayrinti

    v_once = P.v_renk_haritasi(inv, sn["variation_images"])
    g_once = P.galeri_imza(sn["images"])
    yedek_hizli(sn, isd, lid, "ONCE")

    # --- ADIM 1: envanter (sira + fiyat)
    try:
        api.put_json(f"/listings/{lid}/inventory", b)
    except SystemExit as e:
        return "HATA", f"envanter PUT: {str(e)[:160]}", ayrinti
    sn1 = P.anlik(api, shop, lid)
    inv1 = sn1["inventory"]
    hata = fiyat_kontrol(inv1, etiketler)
    if P.boy_sirasi(inv1) != etiketler:
        hata.append(f"menu sirasi hedefle ayni degil: {P.boy_sirasi(inv1)}")
    if len(inv1.get("products") or []) != 75:
        hata.append(f"urun {len(inv1.get('products') or [])} != 75")
    v1 = P.v_renk_haritasi(inv1, sn1["variation_images"])
    if v1 != v_once:
        pid = (sn["variation_images"][0] or {}).get("property_id")
        ad_to_vid = {}
        for pr in inv1.get("products") or []:
            pv = P.pv_of(pr, "primary color") or P.pv_of(pr, "color")
            if pv and pv.get("value_ids"):
                ad_to_vid[(pv.get("values") or [""])[0]] = pv["value_ids"][0]
        vi = [{"property_id": pid, "value_id": ad_to_vid[ad], "image_id": int(img)}
              for ad, img in v_once.items() if ad in ad_to_vid]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        sn1 = P.anlik(api, shop, lid)
        v1 = P.v_renk_haritasi(sn1["inventory"], sn1["variation_images"])
        if v1 != v_once:
            hata.append(f"varyasyon baglantisi onarilamadi: {v1}")
        else:
            log(f"  {lid}: varyasyon baglantilari geri yazildi (5/5)")
    if hata:
        return "HATA", "ADIM 1: " + "; ".join(hata)[:300], ayrinti
    ayrinti["adim1"] = {"urun": 75, "sira": P.boy_sirasi(sn1["inventory"])}

    # --- ADIM 2: Size Guide karesi
    if sg_gerek:
        rank, eski_id = sg.get("rank"), sg.get("listing_image_id")
        veri = {"rank": str(rank)}
        if sg.get("alt_text"):
            veri["alt_text"] = sg["alt_text"]
        api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
        with open(yeni_kart, "rb") as fh:
            r = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                              files={"image": (yeni_kart.name, fh, "image/jpeg")}, data=veri)
        yeni_id = r.get("listing_image_id")
        sn2 = P.anlik(api, shop, lid)
        g_sonra = P.galeri_imza(sn2["images"])
        bekle = [(str(yeni_id), rk) if i == str(eski_id) else (i, rk) for i, rk in g_once]
        hata = []
        if sorted(g_sonra) != sorted(bekle):
            hata.append(f"galeri imzasi farkli: {g_sonra}")
        if [rk for _i, rk in g_sonra] != list(range(1, len(g_sonra) + 1)):
            hata.append(f"galeri siralari bozuk: {g_sonra}")
        if hata:
            return "HATA", "ADIM 2: " + "; ".join(hata)[:300], ayrinti
        ayrinti["adim2"] = {"rank": rank, "eski": eski_id, "yeni": yeni_id, "galeri": len(g_sonra)}
    else:
        sn2 = sn1
        g_sonra = P.galeri_imza(sn1["images"])
        ayrinti["adim2"] = {"atlandi": "kart zaten 15 boyluk", "galeri": len(g_sonra)}

    # --- ADIM 3: aciklama
    if en_yeni != (L.get("description") or ""):
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": en_yeni})
    if ru_eski and ru_yeni != ru_eski:
        api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                {"title": sn["ru"].get("title") or "", "description": ru_yeni,
                 "tags": ",".join(sn["ru"].get("tags") or [])})
    sn3 = P.anlik(api, shop, lid)
    hata = []
    if (sn3["listing"].get("description") or "") != en_yeni:
        hata.append("EN aciklama geri okuma farkli")
    if ru_eski and (sn3["ru"].get("description") or "") != ru_yeni:
        hata.append("RU aciklama geri okuma farkli")
    if sn3["listing"].get("state") != "active":
        hata.append(f"durum {sn3['listing'].get('state')}")
    if P.galeri_imza(sn3["images"]) != g_sonra:
        hata.append("galeri ADIM 3'te degisti")
    if P.boy_sirasi(sn3["inventory"]) != etiketler:
        hata.append("menu sirasi ADIM 3'te degisti")
    hata += fiyat_kontrol(sn3["inventory"], etiketler)
    if P.v_renk_haritasi(sn3["inventory"], sn3["variation_images"]) != v_once:
        hata.append("varyasyon baglantisi ADIM 3'te bozuldu")
    if hata:
        return "HATA", "ADIM 3: " + "; ".join(hata)[:300], ayrinti
    yedek_hizli(sn3, isd, lid, "SONRA")
    ayrinti["adim3"] = {"en": en_dgs, "ru": ru_dgs}
    ayrinti["kota"] = api.remaining
    return "TAMAM", "; ".join(notlar) or "yalniz sira/aciklama", ayrinti


# ------------------------------------------------------------------ ana akis
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz", "toplu"])
    ap.add_argument("--listing", default="4570110641")
    ap.add_argument("--cift", default="")
    ap.add_argument("--atla", default="", help="toplu: atlanacak ilan id'leri (virgullu)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--is-dizin", default="_work/boy15")
    ap.add_argument("--kota-alt", type=int, default=400)
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.mod in ("yaz", "toplu") and a.confirm != "BOY_15":
        raise SystemExit("DUR: yazma icin --confirm BOY_15 gerekir")
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota0 = api.remaining
    log(f"kota (once): {kota0} | mod {a.mod}")
    if kota0 is not None and int(kota0) < a.kota_alt:
        raise SystemExit(f"DUR: kota {kota0} < {a.kota_alt}")
    log("hedef sira/fiyat: " + ", ".join(f"{k} {f:.2f}" for k, f in HEDEF))

    katalog = {str(x["id"]): x for x in json.loads(ILAN_JSON.read_text(encoding="utf-8"))}

    def cift_of(lid, kayit):
        if a.cift and a.mod != "toplu":
            return a.cift
        return re.sub(r"[^A-Z]+", "_", (kayit.get("pair") or "").upper()).strip("_")

    if a.mod in ("oku", "yaz"):
        lid = str(a.listing)
        cift = cift_of(lid, katalog.get(lid, {}))
        durum, neden, ayrinti = isle(api, shop, lid, cift, isd, a.mod == "yaz", a.kota_alt)
        log(f"{lid} ({cift}): {durum} | {neden}")
        for k in ("notlar", "plan_sira", "adim1", "adim2", "adim3", "aciklama",
                  "aciklamada_fiyat", "size_guide"):
            if k in ayrinti:
                log(f"  {k}: {json.dumps(ayrinti[k], ensure_ascii=False)[:600]}")
        p = isd / f"BOY15_{lid}.json"
        p.write_text(json.dumps(ayrinti, ensure_ascii=False, indent=1), encoding="utf-8")
        P.rclone("copyto", str(p), f"{DRV}/BOY15_{lid}.json")
        log(f"kota (sonra): {api.remaining} | {DRV}/BOY15_{lid}.json")
        return 0 if durum in ("TAMAM", "PLAN") else 1

    # ---------------------------------------------------------------- toplu
    atla = {s.strip() for s in a.atla.split(",") if s.strip()}
    sp = isd / "state.json"
    durumlar = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    r = P.rclone("cat", f"{DRV}/BOY15_STATE.json", sert=False)
    if r.returncode == 0 and r.stdout.strip() and not durumlar:
        durumlar = json.loads(r.stdout)
        log(f"STATE Drive'dan alindi: {len(durumlar)} ilan")
    hedefler = [lid for lid in katalog if lid not in atla
                and durumlar.get(lid, {}).get("durum") != "TAMAM"]
    if a.limit:
        hedefler = hedefler[:a.limit]
    toplam = len(hedefler)
    log(f"toplu: {toplam} ilan (atlanan {len(atla)}, daha once TAMAM "
        f"{sum(1 for v in durumlar.values() if v.get('durum') == 'TAMAM')})")
    t_bas, son_rapor = time.time(), 0.0

    def state_yaz():
        sp.write_text(json.dumps(durumlar, ensure_ascii=False, indent=1), encoding="utf-8")
        P.rclone("copyto", str(sp), f"{DRV}/BOY15_STATE.json", sert=False)

    dur_sebep = ""
    for n, lid in enumerate(hedefler, 1):
        if api.remaining is not None and int(api.remaining) < a.kota_alt:
            dur_sebep = f"kota {api.remaining} < {a.kota_alt}"
            log(f"DUR: {dur_sebep}")
            break
        cift = cift_of(lid, katalog[lid])
        t1 = time.time()
        try:
            durum, neden, ayrinti = isle(api, shop, lid, cift, isd, True, a.kota_alt)
        except SystemExit as e:
            durum, neden, ayrinti = "HATA", f"beklenmeyen: {str(e)[:200]}", {"cift": cift}
        except Exception as e:                                        # noqa: BLE001
            durum, neden, ayrinti = "HATA", f"{type(e).__name__}: {str(e)[:200]}", {"cift": cift}
        durumlar[lid] = {"durum": durum, "neden": neden, "cift": cift,
                         "sure": round(time.time() - t1, 1),
                         "fiyatli_satir": ayrinti.get("aciklamada_fiyat"),
                         "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        state_yaz()
        gecen = time.time() - t_bas
        kalan = gecen / n * (toplam - n)
        if durum != "TAMAM" or time.time() - son_rapor >= 60 or n == toplam:
            son_rapor = time.time()
            log(f"{n}/{toplam} ({n / toplam * 100:.0f}%) {lid} {cift}: {durum} | {neden[:110]} | "
                f"gecen {gecen / 60:.1f} dk, kalan ~{kalan / 60:.1f} dk | kota {api.remaining}")
        if durum == "HATA":
            dur_sebep = f"{lid}: {neden}"
            log(f"DUR (yazdiktan sonra kapi tutmadi): {dur_sebep}")
            break

    # SONUC_15.csv
    p = isd / "SONUC_15.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ilan", "cift", "durum", "neden", "sure_sn", "aciklamada_fiyat", "zaman_utc"])
        for lid in katalog:
            d = durumlar.get(lid)
            if not d:
                w.writerow([lid, "", "ATLANDI" if lid in atla else "ISLENMEDI",
                            "pilot/haric" if lid in atla else "", "", "", ""])
                continue
            w.writerow([lid, d.get("cift", ""), d["durum"], d["neden"][:300], d.get("sure", ""),
                        "; ".join(d.get("fiyatli_satir") or []), d.get("zaman_utc", "")])
    P.rclone("copyto", str(p), f"{DRV}/SONUC_15.csv")
    sayim = {}
    for d in durumlar.values():
        sayim[d["durum"]] = sayim.get(d["durum"], 0) + 1
    log(f"OZET: {sayim} | kota {kota0} -> {api.remaining} | sure {(time.time() - t_bas) / 60:.1f} dk "
        f"| {DRV}/SONUC_15.csv")
    for lid, d in durumlar.items():
        if d["durum"] != "TAMAM":
            log(f"  {d['durum']} {lid} ({d.get('cift')}): {d['neden'][:200]}")
    if dur_sebep:
        raise SystemExit(f"DUR: {dur_sebep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
