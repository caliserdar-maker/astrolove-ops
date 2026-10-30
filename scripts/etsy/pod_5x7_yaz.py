#!/usr/bin/env python3
"""78 POSTER 5x7 + ACIKLAMA YAZIMI (Serdar 30 Eki): onayli KURU plana kilitli (pod_5x7_kuru.py ciktisi, Drive
TEMP/5X7_HAZIRLIK_20261026/KURU_<plan_damga>/). Plan disi hicbir sey yazilmaz.

Modlar:
  kontrol        : SALT OKUMA (yazma yontemleri kapali). Ilan basina 4 GET, canli = plan kapisi; ne yazilacagini raporlar.
  yaz            : ETSY'YE YAZAR (--onay SERDAR_5X7_YAZ). Ilan basina sira: envanter PUT (5x7 x 10) -> geri okuma -> renk bagi
                   (bozulduysa POST ile yeniden kur) -> EN PATCH -> geri okuma -> RU PUT (ru_poster izni) -> geri okuma.
  geri-al        : ETSY'YE YAZAR (--onay SERDAR_5X7_GERI_AL). Plandaki ham yedege doner (130 urun, eski EN, eski RU).
  profil         : ETSY'YE YAZAR (--onay SERDAR_5X7_PROFIL). Kargo profili 314711751541 yalniz AU hedefi teslim 7-22 (PROFIL_PLAN).
  profil-geri-al : ETSY'YE YAZAR (--onay SERDAR_5X7_PROFIL_GERI_AL). AU hedefi plandaki eski degerlere.

Ilan secimi: plandaki ilanlar; --sadece (pilot: tek ilan) ve --haric. Haric ilan plandan ATLANIR (HARIC, hata degil; 30 Eki video
yaziminda 78 satirlik plan + haric 77 reddedilmisti, burada olmaz). --sadece / --haric plan disi kimlik verirse DUR (yazim girisi).
Secilen ilanin plan kaydi PASS olmali; FAIL plan satiri yalniz haric tutularak gecilir.

Plan butunlugu (Etsy isteginden ONCE, secilen her ilan): KURU_<lid>.json listing_id, PASS, hata bos; plan ham verisinden (envanter,
aciklama) bu kodla yeniden kurulan envanter govdesi / EN / RU plandakiyle birebir (elle degistirilmis ya da baska kodla kurulmus plan
yazilmaz).

Canli = plan kapisi (her ilan, yazmadan once; adim basina): yaz = canli plandaki ONCE ile ayni; atla = canli zaten SONRA; aksi halde
KAYMA -> o ilana HIC yazilmaz (ATLANDI_KAYMA), kosu sonraki ilanla surer, cikis 1. Ayrica: state active (CLAUDE.md 7 Eyl: updateListing
taslagi yayina alir), renk bagi (deger adi + gorsel) plandakiyle ayni, canli envanterden yeniden kurulan govde plandakiyle ayni.

Yazim sonrasi geri okuma FAIL ya da yazim sirasinda istisna: kosu DURUR (sonraki ilana gecilmez), ilan FAIL, geri-al ile geri donulur.
Yedek: plan klasoru (Drive, kuru ham verisi) + ilan basina YEDEK_<lid>.json (yazmadan once canli okuma).

Kota: KOTA_SINIRI 10 (etsy_common, Serdar 15 ve 24 Eki; her istekten once sert taban). Ilan basina istek esigi: ilana baslamadan ve
yazmadan once kalan >= ILAN_UST + KOTA_SINIRI; tutmazsa ilana baslanmaz / yazilmaz (KOTA, yarim ilan birakilmaz).
ILAN_UST = 19: okuma 4 + envanter PUT 1 + GET 1 + renk bagi GET 1 (+ POST 1 + GET 3) + EN PATCH 1 + GET en cok 3 + RU PUT 1 + GET en
cok 3. Tipik 11 (kuru ISTEK_TAHMINI ile ayni). 5xx tekrarlari (_call, en cok 3 gonderim) dahil degil.
Cikti: <out>/SONUC.json, SONUC.csv, OZET.md, YEDEK_<lid>.json."""
import argparse
import csv
import json
import os
import pathlib
import re
import sys
import time
import traceback

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import pod_5x7_kuru as K  # noqa: E402
import ru_poster as R  # noqa: E402
from beyan_marka_yaz import norm  # noqa: E402

ONAY = {"yaz": "SERDAR_5X7_YAZ", "geri-al": "SERDAR_5X7_GERI_AL", "profil": "SERDAR_5X7_PROFIL",
        "profil-geri-al": "SERDAR_5X7_PROFIL_GERI_AL"}
ILAN_UST = 19
BEKLE_SN = 3
ON_PROP = ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property")


class Kayma(Exception):
    """Canli plandan farkli: bu ilana yazilmaz."""


class Fail(Exception):
    """Yazim sonrasi dogrulama tutmadi: kosu durur."""


def j(x):
    return json.loads(json.dumps(x, ensure_ascii=False))


def boy(p):
    return K.pv(p, 513).get("values", [None])[0]


def urun_imza(p):
    """Urun imzasi; ADET HARIC (satis adedi dusurur: kuru sonrasi satis kayma sayilmaz, yazim canli adetle). 5x7 urununun Size
    value_ids / scale_id'si yok sayilir (Etsy uretir)."""
    yeni = boy(p) == K.ETIKET_5X7
    props = sorted((v.get("property_id"), v.get("property_name"),
                    None if yeni and v.get("property_id") == 513 else v.get("scale_id"), tuple(v.get("values") or []),
                    () if yeni and v.get("property_id") == 513 else tuple(v.get("value_ids") or []))
                   for v in p.get("property_values") or [])
    return (p.get("sku") or "", tuple(props),
            tuple((K.para(o.get("price")), bool(o.get("is_enabled")), o.get("readiness_state_id")) for o in p.get("offerings") or []))


def imza(inv, yalniz_eski=False):
    """Envanter imzasi SIRASIZ (Etsy GET urun sirasini degistirse de durum tespiti kilitlenmez; inceleme 30 Eki 3). Menu sirasi
    ayrica menu() ile denetlenir. yalniz_eski: 5x7 urunleri disarida."""
    pr = sorted(urun_imza(p) for p in inv.get("products") or [] if not (yalniz_eski and boy(p) == K.ETIKET_5X7))
    return pr, tuple(tuple(sorted(inv.get(k) or [])) for k in ON_PROP)


def menu(inv):
    """Boy menusu sirasi (urun dizisindeki ilk gorunus; pod_boy_15.py: Etsy menuyu dizi sirasiyla gosterir)."""
    return list(dict.fromkeys(boy(p) for p in inv.get("products") or []))


def adetler(inv):
    return {o.get("quantity") for p in inv.get("products") or [] for o in p.get("offerings") or []}


def adet_uygula(govde, q):
    g = j(govde)
    for p in g["products"]:
        for o in p["offerings"]:
            o["quantity"] = q
    return g


def geri_govde(ham):
    return {"products": [K.kopya(p) for p in ham.get("products") or []], **{k: ham.get(k) for k in ON_PROP}}


def boylar_of(inv):
    return [K.BOYLAR[b] for b in dict.fromkeys(boy(p) for p in inv.get("products") or []) if b in K.BOYLAR]


def renk_ad(inv, vi):
    """Renk bagi: (property_id, deger adi, image_id) sirali. value_id adi envanterden (envanter yazimi value_id'yi korur)."""
    ad = {}
    for p in (inv or {}).get("products") or []:
        for v in p.get("property_values") or []:
            for i, a in zip(v.get("value_ids") or [], v.get("values") or []):
                ad[(v.get("property_id"), i)] = a
    return sorted((x.get("property_id"), ad.get((x.get("property_id"), x.get("value_id")), f"?{x.get('value_id')}"), x.get("image_id"))
                  for x in vi or [])


def ru_geri_kur(k):
    """Eski RU, ru_poster ile eski EN + 13 boydan yeniden kurulabiliyor mu (RU kapisi yalniz bu yoldan yazdirir). -> (ru, kontrol) | None"""
    ru, kr = R.kur(k["en_eski"], {"boy": boylar_of(k["envanter_ham_yedek"])})
    return (ru, kr) if kr.get("pass_") and norm(ru) == norm(k["ru_simdi"]) else None


# ------------------------------------------------------------------ plan
def plan_yukle(d, sec, haric):
    """-> (plan {lid: kayit}, secilen [lid], haric [lid]). Hata -> SystemExit (Etsy istegi yok)."""
    d = pathlib.Path(d)
    dosya = {p.name[5:-5]: p for p in d.glob("KURU_*.json")}
    if not dosya:
        raise SystemExit(f"DUR: plan klasorunde KURU_*.json yok ({d})")
    csvd = d / "PLAN.csv"
    if not csvd.is_file():
        raise SystemExit("DUR: plan klasorunde PLAN.csv yok")
    satir = {r["listing_id"]: r for r in csv.DictReader(open(csvd, encoding="utf-8"))}
    if set(satir) != set(dosya):
        raise SystemExit(f"DUR: PLAN.csv ilanlari ile KURU_*.json ayni degil ({len(satir)} / {len(dosya)})")
    sec, haric = list(dict.fromkeys(sec)), list(dict.fromkeys(haric))
    yabanci = sorted((set(sec) | set(haric)) - set(dosya))
    if yabanci:
        raise SystemExit(f"DUR: --sadece / --haric plan disi ilan: {yabanci}")
    if set(sec) & set(haric):
        raise SystemExit(f"DUR: ayni ilan hem --sadece hem --haric: {sorted(set(sec) & set(haric))}")
    secilen = [x for x in (sec or sorted(dosya)) if x not in haric]
    if not secilen:
        raise SystemExit("DUR: secilen ilan yok (hepsi haric)")
    plan = {}
    for lid in secilen:
        k = json.loads(dosya[lid].read_text(encoding="utf-8"))
        h = []
        if str(k.get("listing_id")) != lid:
            h.append(f"listing_id {k.get('listing_id')}")
        if not k.get("PASS") or k.get("hata") or satir[lid].get("sonuc") != "PASS":
            h.append(f"plan FAIL {k.get('hata')}")
        if not h:   # butunluk: ham veriden bu kodla yeniden kur
            ham = k["envanter_ham_yedek"]
            yuk, _, he = K.envanter_plani(ham)
            if he or j(yuk) != k["envanter_yuk"]:
                h.append(f"envanter govdesi yeniden kurulamadi / farkli {he[:2]}")
            en0, en, ru, kr, _, _, ha = K.aciklama_plani(k["aciklama_ham"], boylar_of(ham))
            if ha or en0 != k["en_eski"] or en != k["en_yeni"] or ru != k["ru_yeni"]:
                h.append(f"aciklama plani yeniden kurulamadi / farkli {ha[:2]}")
            if norm(k["ru_yazim_govdesi"]["description"]) != norm(k["ru_yeni"]) or k["ru_yazim_govdesi"]["tags"] != k["ru_etiket"]:
                h.append("ru_yazim_govdesi plan RU ile ayni degil")
        if h:
            raise SystemExit(f"DUR: plan {lid}: {'; '.join(h)} (haric ile atlanabilir)")
        k["_ru_geri"] = ru_geri_kur(k) is not None   # inceleme 30 Eki 4: yazimdan ONCE geri alinabilirlik
        plan[lid] = k
    return plan, secilen, sorted(haric)


# ------------------------------------------------------------------ canli = plan
def oku(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    ru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    return L, inv, vi, ru


def ru_imza(ru):
    return norm(ru.get("description")), norm(ru.get("title")), sorted(ru.get("tags") or [])


def bizim(canli, eski, yeni):
    """Canli metin = plandaki yeni metin, plan satirlari (eski / yeni arasinda degisen) disinda BIREBIR; ve en az bir yeni plan
    satiri canlida. Baska bir elle degisiklik varsa False (geri alma o bileseni yazmaz; inceleme 30 Eki B)."""
    sat = lambda t: [x.strip() for x in t.split("\n") if x.strip()]  # noqa: E731
    e, y, c = sat(eski), sat(yeni), sat(canli)
    plan = (set(y) - set(e)) | (set(e) - set(y))
    return any(x in set(y) - set(e) for x in c) and [x for x in c if x not in plan] == [x for x in y if x not in plan]


def kapi(k, L, inv, vi, ru, geri=False):
    """-> {"envanter", "renk", "en", "ru": yaz|atla|onar|kayma: ...}, "adet": q.
    yaz: hepsi ya da hic (herhangi bir kayma -> Kayma, yazim yok). geri: bilesen basina (kayan bilesen atlanir, digerleri geri alinir;
    inceleme 30 Eki 1). Ilan duzeyi Kayma: state active degil, adet tek deger degil."""
    if L.get("state") != "active":
        raise Kayma(f"state {L.get('state')} (active degil; updateListing taslagi yayina alir)")
    q = adetler(inv)
    if len(q) != 1:
        raise Kayma(f"adet tek deger degil {sorted(q, key=str)}")
    ham, yuk = k["envanter_ham_yedek"], k["envanter_yuk"]
    s = {"adet": next(iter(q))}
    canli, h_imza, y_imza = imza(inv), imza(ham), imza(yuk)
    vi_ok = renk_ad(inv, vi) == renk_ad(ham, k["renk_bagi_ham"])
    en_c, ru_c = norm(L.get("description")), ru_imza(ru)
    ru_eski = (norm(k["ru_simdi"]), norm(k["ru_baslik"]), sorted(k["ru_etiket"]))
    ru_yeni = (norm(k["ru_yeni"]), norm(k["ru_baslik"]), sorted(k["ru_etiket"]))
    if not geri:
        if not k.get("_ru_geri"):
            raise Kayma("RU geri alinamaz (ru_poster eski EN'den canli eski RU'yu kurmuyor); yazilmaz")
        if canli == h_imza:
            y2, _, he = K.envanter_plani(inv)
            if he or adet_uygula(y2, 0) != adet_uygula(yuk, 0):
                raise Kayma(f"canli envanterden kurulan govde plandan farkli {he[:2]}")
            s["envanter"] = "yaz"
        elif canli == y_imza:
            if menu(inv) != menu(yuk):   # inceleme 30 Eki A: menu bozuk ilan yeniden koşuda TAMAM sayilmaz
                raise Kayma(f"envanter yazilmis ama boy menusu sirasi plandan farkli ({menu(inv)[:2]}); geri-al")
            s["envanter"] = "atla"
        else:
            raise Kayma(f"envanter plandan farkli (urun {len(inv.get('products') or [])})")
        if not vi_ok and s["envanter"] == "yaz":
            raise Kayma(f"renk bagi plandan farkli: {renk_ad(inv, vi)}")
        s["renk"] = "atla" if vi_ok else "onar"     # envanter onceden yazilmis + bag bozuk: plan bagi geri kurulur
        s["en"] = "yaz" if en_c == k["en_eski"] else "atla" if en_c == k["en_yeni"] else None
        if s["en"] is None:
            raise Kayma("EN aciklama plandan farkli")
        s["ru"] = "yaz" if ru_c == ru_eski else "atla" if ru_c == ru_yeni else None
        if s["ru"] is None:
            raise Kayma("RU ceviri (aciklama / baslik / etiket) plandan farkli")
        return s
    # geri: bilesen basina
    if canli == h_imza and menu(inv) == menu(ham):
        s["envanter"] = "atla"
    elif imza(inv, yalniz_eski=True) == h_imza:
        s["envanter"] = "yaz"      # 5x7 disi urunler ham ile ayni (5x7 eklenmis ya da sira bozuk)
    else:
        s["envanter"] = "kayma: 5x7 disi urunler ham yedekten farkli"
    s["renk"] = "atla" if vi_ok else "kayma: renk bagi (envanter kaydi)" if s["envanter"].startswith("kayma") else "onar"
    if en_c == k["en_eski"]:
        s["en"] = "atla"
    elif bizim(en_c, k["en_eski"], k["en_yeni"]):
        s["en"] = "yaz"
    else:
        s["en"] = "kayma: EN plandaki yeni metne ait degil"
    if ru_c == ru_eski:
        s["ru"] = "atla"
    elif ru_c[1:] == ru_eski[1:] and bizim(ru_c[0], ru_eski[0], ru_yeni[0]):
        s["ru"] = "yaz" if k.get("_ru_geri") else "kayma: RU geri kurulamiyor (ru_poster eski RU'yu kurmuyor), elle"
    else:
        s["ru"] = "kayma: RU plandaki yeni metne ait degil / baslik-etiket farkli"
    return s


def ru_izin(lid, k, geri):
    """RU yazimindan once izin + kapi denemesi (istek yok)."""
    if geri:
        x = ru_geri_kur(k)
        if x is None:
            raise Kayma("RU: ru_poster eski EN'den eski RU'yu kurmuyor")
        ru, kr = x
    else:
        ru, kr = R.kur(k["en_yeni"], {"boy": ["5x7"] + boylar_of(k["envanter_ham_yedek"])})
        if ru != k["ru_yeni"]:
            raise Kayma("RU: ru_poster.kur yeni EN'den plan RU'sunu kurmuyor")
    R.izin_ver(lid, ru, kr)
    govde = {"title": norm(k["ru_baslik"]), "description": ru, "tags": ",".join(k["ru_etiket"])}
    E.ru_yazim_kapisi("PUT", f"/shops/0/listings/{lid}/translations/ru", data=govde)
    return govde


def kota_yeter(api, gerek):
    """Ilan basina esik: kalan >= gerek + KOTA_SINIRI (kalan henuz bilinmiyorsa ilk istekte _istek_oncesi tabani bakar)."""
    try:
        api.kota_kapisi("ilan")   # CLAUDE.md: toplu islerde ilan basina kota kapisi
    except SystemExit:
        return False
    return api.remaining is None or int(api.remaining) >= gerek + E.KOTA_SINIRI


def tekrar_oku(fn, kosul, n=3):
    x = None
    for i in range(n):
        x = fn()
        if kosul(x):
            return x, True
        if i < n - 1:
            time.sleep(BEKLE_SN)
    return x, False


def renk_onar(api, shop, lid, inv1, hedef_vi, R_):
    """Renk bagini deger ADINA gore yeniden kurar (burc_gift_yaz.sg_bagla yolu); geri okuma 3 deneme."""
    vi1 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    if renk_ad(inv1, vi1) == hedef_vi:
        return
    vid = {(v.get("property_id"), a): i for p in inv1.get("products") or [] for v in p.get("property_values") or []
           for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
    istek = [{"property_id": pid, "value_id": vid[(pid, a)], "image_id": img} for pid, a, img in hedef_vi if (pid, a) in vid]
    if len(istek) != len(hedef_vi):
        raise Fail(f"renk bagi eslesmesi kurulamadi {len(istek)}/{len(hedef_vi)}")
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
    R_["yazilan"].append("renk_bagi")
    _, ok = tekrar_oku(lambda: (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
                       lambda v: renk_ad(inv1, v) == hedef_vi)
    if not ok:
        raise Fail("renk bagi yeniden kurulamadi (geri okuma)")


def ilan_yaz(api, shop, lid, k, geri, out, kontrol):
    R_ = {"listing_id": lid, "pilot": k.get("pilot"), "istek_once": api.calls, "kota_once": api.remaining}
    if not kota_yeter(api, ILAN_UST):
        R_["sonuc"] = "KOTA"
        R_["neden"] = f"kalan {api.remaining} < ilan esigi {ILAN_UST} + {E.KOTA_SINIRI} (ilana baslanmadi)"
        return R_
    try:
        L, inv, vi, ru = oku(api, shop, lid)
    except (Exception, SystemExit) as e:   # noqa: BLE001  okuma hatasi: yazim yok, kosu durur
        R_.update(sonuc="HATA_OKUMA", neden=f"{type(e).__name__}: {str(e)[:300]}", istek=api.calls - R_["istek_once"])
        return R_
    try:
        s = kapi(k, L, inv, vi, ru, geri)
        govde_ru = ru_izin(lid, k, geri) if s["ru"] == "yaz" else None
    except (Kayma, SystemExit) as e:   # SystemExit: ru_poster izni / RU yazim kapisi (istek yok)
        R_.update(sonuc="ATLANDI_KAYMA", neden=str(e), istek=api.calls - R_["istek_once"])
        return R_
    R_["adim"] = s
    adim = [v for kk, v in s.items() if kk != "adet"]
    kayan = [f"{kk} {v}" for kk, v in s.items() if kk != "adet" and str(v).startswith("kayma")]
    zaten = all(v in ("atla",) or str(v).startswith("kayma") for v in adim)
    if kontrol or zaten:
        sonuc = ("KONTROL_ZATEN" if zaten else "KONTROL_YAZILACAK") if kontrol else "ZATEN"
        R_.update(sonuc=sonuc + ("_KISMI" if kayan else ""), neden="; ".join(kayan), istek=api.calls - R_["istek_once"])
        return R_
    if not kota_yeter(api, ILAN_UST - 4):
        R_.update(sonuc="KOTA", neden=f"okuma sonrasi kalan {api.remaining} < {ILAN_UST - 4} + {E.KOTA_SINIRI} (yazim yok)")
        return R_
    (out / f"YEDEK_{lid}.json").write_text(json.dumps({"listing_id": lid, "mod": "geri-al" if geri else "yaz", "listing": L,
                                                       "inventory": inv, "variation_images": vi, "ru": ru},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    R_["yazilan"] = []
    ham = k["envanter_ham_yedek"]
    hedef_vi = renk_ad(ham, k["renk_bagi_ham"])
    try:
        inv1 = inv
        if s["envanter"] == "yaz":
            kaynak = ham if geri else k["envanter_yuk"]
            govde = adet_uygula(geri_govde(ham) if geri else kaynak, s["adet"])   # adet: canli (kuru sonrasi satis korunur)
            api.put_json(f"/listings/{lid}/inventory?max_variations_supported=3", govde)   # 3 menu (Format, Renk, Boy); yoksa 409 (pilot 30 Eki 41105387368)
            R_["yazilan"].append("envanter")
            inv1 = api.get(f"/listings/{lid}/inventory") or {}
            if imza(inv1) != imza(kaynak) or adetler(inv1) != {s["adet"]}:
                raise Fail(f"envanter geri okuma plandan farkli (urun {len(inv1.get('products') or [])}, adet {sorted(adetler(inv1), key=str)})")
            if menu(inv1) != menu(kaynak):
                raise Fail(f"boy menusu sirasi plandan farkli: {menu(inv1)[:3]}")
        if s["envanter"] == "yaz" or s["renk"] == "onar":   # envanter yazimi value_id'yi korur; yine de bag her zaman denetlenir
            renk_onar(api, shop, lid, inv1, hedef_vi, R_)
        if s["en"] == "yaz":
            en = k["en_eski"] if geri else k["en_yeni"]
            api.patch(f"/shops/{shop}/listings/{lid}", {"description": en})
            R_["yazilan"].append("en")
            L1, ok = tekrar_oku(lambda: api.get(f"/listings/{lid}") or {},
                                lambda x: norm(x.get("description")) == en)
            if not ok:
                raise Fail("EN geri okuma plandan farkli")
            if L1.get("state") != "active" or L1.get("title") != L.get("title"):
                raise Fail(f"EN yazimi sonrasi state {L1.get('state')} / baslik degisti")
        if s["ru"] == "yaz":
            api.put(f"/shops/{shop}/listings/{lid}/translations/ru", govde_ru)
            R_["yazilan"].append("ru")
            hedef_ru = (norm(govde_ru["description"]), govde_ru["title"], sorted(k["ru_etiket"]))
            _, ok = tekrar_oku(lambda: api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {},
                               lambda x: ru_imza(x) == hedef_ru)
            if not ok:
                raise Fail("RU geri okuma plandan farkli")
        R_.update(sonuc="TAMAM_KISMI" if kayan else "TAMAM", neden="; ".join(kayan))
    except (Exception, SystemExit) as e:   # noqa: BLE001  (SystemExit: HTTP hatasi / kota tabani)
        R_.update(sonuc="FAIL", neden=f"{type(e).__name__}: {str(e)[:300]}", iz=traceback.format_exc()[-800:])
    R_.update(istek=api.calls - (R_["istek_once"] or 0), kota_sonra=api.remaining)
    return R_


# ------------------------------------------------------------------ profil
def profil(api, shop, pplan, geri):
    PROFIL = pplan["profil"]
    if PROFIL != K.PROFIL or len(pplan.get("au_once") or []) != 1 or pplan.get("hata"):
        raise SystemExit(f"DUR: PROFIL_PLAN beklenen degil (profil {PROFIL}, AU {len(pplan.get('au_once') or [])}, hata {pplan.get('hata')})")
    au0 = pplan["au_once"][0]
    if pplan.get("pod78_disi_kullanan") or pplan.get("profili_kullanan") is None:   # profil_ucretsiz.py:115-116 kurali
        raise SystemExit(f"DUR: profili 78 poster disinda kullanan ilan var / bilinmiyor: {pplan.get('pod78_disi_kullanan')}")
    if au0.get("shipping_carrier_id") not in (0, None) or au0.get("mail_class") is not None:
        raise SystemExit(f"DUR: AU hedefinde tasiyici/sinif tanimli ({au0.get('shipping_carrier_id')}, {au0.get('mail_class')}); govde bunu korumaz")
    did = au0["shipping_profile_destination_id"]
    eski = (au0["min_delivery_days"], au0["max_delivery_days"])
    yeni = (pplan["au_sonra"]["min_delivery_days"], pplan["au_sonra"]["max_delivery_days"])
    if yeni != K.AU_YENI:
        raise SystemExit(f"DUR: plan AU {yeni} != {K.AU_YENI}")
    once, sonra = (yeni, eski) if geri else (eski, yeni)

    def hedefler(sp):
        return {d.get("shipping_profile_destination_id"): d for d in sp.get("shipping_profile_destinations") or []}

    def anahtar(d):   # AU disi her alan + AU'nun teslim disi alanlari
        return {k: v for k, v in d.items() if k not in ("min_delivery_days", "max_delivery_days")}
    ref = {d["shipping_profile_destination_id"]: d for d in pplan["once_tum_hedefler"]}
    h0 = hedefler(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {})
    if set(h0) != set(ref) or any(anahtar(h0[i]) != anahtar(ref[i]) for i in ref) or \
            any((h0[i]["min_delivery_days"], h0[i]["max_delivery_days"]) != (ref[i]["min_delivery_days"], ref[i]["max_delivery_days"])
                for i in ref if i != did):
        return {"sonuc": "ATLANDI_KAYMA", "neden": "profil hedefleri plandan farkli"}
    au = (h0[did]["min_delivery_days"], h0[did]["max_delivery_days"])
    if au == sonra:
        return {"sonuc": "ZATEN", "au": au}
    if au != once:
        return {"sonuc": "ATLANDI_KAYMA", "neden": f"AU {au} plan {once} degil"}
    if not kota_yeter(api, 3):
        return {"sonuc": "KOTA", "neden": f"kalan {api.remaining}"}
    pc = K.para(h0[did]["primary_cost"]), K.para(h0[did]["secondary_cost"])
    api.put(f"/shops/{shop}/shipping-profiles/{PROFIL}/destinations/{did}",
            {"primary_cost": pc[0], "secondary_cost": pc[1], "min_delivery_days": sonra[0], "max_delivery_days": sonra[1],
             "destination_country_iso": "AU"})   # profil_ucretsiz.py:124-126 kalibi
    h1 = hedefler(api.get(f"/shops/{shop}/shipping-profiles/{PROFIL}") or {})
    bek = {i: (anahtar(ref[i]), (sonra if i == did else (ref[i]["min_delivery_days"], ref[i]["max_delivery_days"]))) for i in ref}
    gel = {i: (anahtar(d), (d["min_delivery_days"], d["max_delivery_days"])) for i, d in h1.items()}
    if gel != bek:
        return {"sonuc": "FAIL", "neden": "profil geri okuma beklenen degil", "gelen": {i: g[1] for i, g in gel.items()}}
    return {"sonuc": "TAMAM", "au": f"{once} -> {sonra}"}


# ------------------------------------------------------------------ ana
def calis(api, shop, a, out):
    sec = [x for x in (a.sadece or "").split(",") if x]
    haric = [x for x in (a.haric or "").split(",") if x]
    kontrol = a.mod == "kontrol"
    if kontrol:
        K.salt_okur(api)
    if a.mod in ("profil", "profil-geri-al"):
        pplan = json.loads((pathlib.Path(a.plan) / "PROFIL_PLAN.json").read_text(encoding="utf-8"))
        r = profil(api, shop, pplan, a.mod == "profil-geri-al")
        r.update(mod=a.mod, plan_damga=a.plan_damga, istek=api.calls, kota=api.remaining)
        (out / "SONUC.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"::notice::SONUC {r['sonuc']} {a.mod} istek {api.calls} kota {api.remaining}", flush=True)
        return 0 if r["sonuc"] in ("TAMAM", "ZATEN") else 1
    plan, secilen, haric = plan_yukle(a.plan, sec, haric)
    geri = a.mod == "geri-al"
    sonuc, t0 = [], time.time()
    print(f"plan {a.plan_damga}: secilen {len(secilen)}, haric {len(haric)}, mod {a.mod}", flush=True)
    for i, lid in enumerate(secilen, 1):
        r = ilan_yaz(api, shop, lid, plan[lid], geri, out, kontrol)
        sonuc.append(r)
        gec = time.time() - t0
        print(f"[{i}/{len(secilen)}] %{100 * i // len(secilen)} {lid} {r['sonuc']} {r.get('neden', '')} | istek {api.calls} kota "
              f"{api.remaining} | gecen {gec:.0f} sn kalan ~{gec / i * (len(secilen) - i):.0f} sn", flush=True)
        if r["sonuc"] in ("FAIL", "KOTA", "HATA_OKUMA"):
            break
    yapilmadi = [x for x in secilen if x not in {r["listing_id"] for r in sonuc}]
    say = {}
    for r in sonuc:
        say[r["sonuc"]] = say.get(r["sonuc"], 0) + 1
    ozet = {"mod": a.mod, "plan_damga": a.plan_damga, "secilen": len(secilen), "haric": haric, "sayim": say,
            "yapilmadi": yapilmadi, "istek": api.calls, "kota_son": api.remaining, "ilan_ust": ILAN_UST, "kota_siniri": E.KOTA_SINIRI}
    (out / "SONUC.json").write_text(json.dumps({"ozet": ozet, "ilanlar": sonuc}, ensure_ascii=False, indent=1, default=str),
                                    encoding="utf-8")
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "sonuc", "envanter", "en", "ru", "yazilan", "istek", "kota_sonra", "neden"])
        for r in sonuc:
            ad = r.get("adim") or {}
            w.writerow([r["listing_id"], r["sonuc"], ad.get("envanter", ""), ad.get("en", ""), ad.get("ru", ""),
                        "+".join(r.get("yazilan") or []), r.get("istek", ""), r.get("kota_sonra", ""), r.get("neden", "")])
        for x in haric:
            w.writerow([x, "HARIC", "", "", "", "", "", "", "--haric"])
        for x in yapilmadi:
            w.writerow([x, "YAPILMADI", "", "", "", "", "", "", "kosu onceki ilanda durdu"])
    (out / "OZET.md").write_text(
        f"# 5x7 + aciklama {a.mod} (plan KURU_{a.plan_damga})\n\n- secilen {len(secilen)}, haric {len(haric)}, sayim {say}\n"
        f"- yapilmadi {len(yapilmadi)}; istek {api.calls}; kota son {api.remaining}\n"
        + "".join(f"- {r['listing_id']}: {r['sonuc']} {r.get('adim', '')} {r.get('neden', '')}\n" for r in sonuc), encoding="utf-8")
    print(f"::notice::SONUC {a.mod} {say} yapilmadi {len(yapilmadi)} istek {api.calls} kota {api.remaining}", flush=True)
    iyi = ("KONTROL_YAZILACAK", "KONTROL_ZATEN") if kontrol else ("TAMAM", "ZATEN")   # _KISMI (geri-al) rc 1
    return 0 if all(r["sonuc"] in iyi for r in sonuc) and not yapilmadi else 1


def argumanlar(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["kontrol", "yaz", "geri-al", "profil", "profil-geri-al"])
    ap.add_argument("--plan", required=True, help="KURU_<plan_damga> klasoru (KURU_*.json, PLAN.csv, PROFIL_PLAN.json)")
    ap.add_argument("--plan-damga", required=True)
    ap.add_argument("--sadece", default="")
    ap.add_argument("--haric", default="")
    ap.add_argument("--onay", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d+", a.plan_damga) or pathlib.Path(a.plan).name != f"KURU_{a.plan_damga}":
        raise SystemExit(f"DUR: plan klasoru KURU_{a.plan_damga} degil ({pathlib.Path(a.plan).name})")
    for x in (a.sadece, a.haric):
        if not re.fullmatch(r"(\d+(,\d+)*)?", x):
            raise SystemExit("DUR: --sadece / --haric virgullu listing_id olmali")
    if a.mod != "kontrol" and a.onay != ONAY[a.mod]:
        raise SystemExit(f"DUR: {a.mod} icin onay sozcugu yok / yanlis (yazim yok)")
    return a


def main(argv=None):
    a = argumanlar(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.mod not in ("profil", "profil-geri-al"):
        plan_yukle(a.plan, [x for x in a.sadece.split(",") if x], [x for x in a.haric.split(",") if x])   # Etsy isteginden ONCE
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    return calis(E.Etsy(store), os.environ["ETSY_SHOP_ID"], a, out)


if __name__ == "__main__":
    sys.exit(main())
