#!/usr/bin/env python3
"""YD (1st Anniversary) YENI ILAN YAPISI YAZIMI: onayli KURU plana kilitli (yd_yapi_kuru.py ciktisi, Drive KURU_<plan_damga>/).
Plan disi hicbir sey yazilmaz. updateListing / listing PATCH YOK (CLAUDE.md 7 Eyl: taslagi yayina alir); yalniz
PUT /listings/{id}/inventory?max_variations_supported=3 (3 varyasyon: Style, Format, Size; parametresiz PUT 409) ve Style bagi
onarimi (POST variation-images, ada gore). KOSTURMA AYRI SERDAR ONAYIYLA.

Modlar:
  kontrol        : SALT OKUMA (yazma yontemleri kapali). Ilan basina 3 GET; canli = plan kapisi; ne yazilacagini raporlar.
  yaz            : ETSY'YE YAZAR (--onay SERDAR_YD_YAPI_YAZ). Ilan: kota -> 3 GET -> kapi -> YEDEK_<lid>.json -> envanter PUT ->
                   geri okuma (140 urun, imza, menu sirasi, adet) -> Style bagi (bozulduysa ada gore POST) -> ilan geri okuma (state active).
                   Herhangi bir adim tutmazsa ya da istek hata verirse (5xx / zaman asimi: PUT Etsy'de uygulanmis olabilir; adim PUT'tan
                   ONCE yazilan'a girer) OTOMATIK GERI ALMA: canli envanter okunur; ham yedekten farkliysa ham envanter PUT, sonra bag
                   (ada gore) denetlenir / onarilir; kosu durur. --sadece yoksa --tum zorunlu (pilot once; inceleme 30 Eki madde 7).
  geri-al        : ETSY'YE YAZAR (--onay SERDAR_YD_YAPI_GERI_AL). Plandaki ham yedege doner (15 urun, eski format, baglar).
  profil         : ETSY'YE YAZAR (--onay SERDAR_YD_PROFIL). PROFIL_PLAN yazim listesi: yalniz ucret 0. PUT govdesi CANLI hedeften
                   kurulur (tasiyici / mail_class / teslim gunleri / hedef aynen; yalniz ucret alanlari degisir). Yazim aninda profili
                   kullanan ilanlar yeniden taranir (5 durum); YD listesi (--liste) disinda kullanan varsa DUR. Hata -> SONUC.json HATA.
  profil-geri-al : ETSY'YE YAZAR (--onay SERDAR_YD_PROFIL_GERI_AL). Ucretler plandaki eski degerlere.
Ilan secimi: plandaki ilanlar; --sadece (pilot) ve --haric (plan disi kimlik -> DUR). Secilen ilan plan durumu PLAN ya da ZATEN olmali.
Plan butunlugu (Etsy isteginden ONCE): KURU_<lid>.json + PLAN.csv ayni; ham envanterden bu kodla (yd_yapi_kuru.envanter_plani)
  kurulan govde plandakiyle birebir.
Canli = plan kapisi (her ilan, yazmadan once): state active; adet tek; envanter imzasi ham ile ayni -> yaz; plan govdesiyle ayni ->
  atla (ZATEN; menu sirasi da ayni olmali); aksi halde KAYMA (o ilana yazilmaz, kosu surer, cikis 1). Style bagi (ad + gorsel) plandakiyle
  ayni olmali (yaz); atla durumunda bozuksa onarilir.
Kota: KOTA_SINIRI 10 (etsy_common; her istekten once sert taban). Ilan esigi: ilana baslamadan ve yazmadan once
  kalan >= ILAN_UST + KOTA_SINIRI; tutmazsa ilana baslanmaz (KOTA, yarim ilan yok).
Istek (kod sayimi; 5xx / 429 tekrarlari dahil degil): ILAN_TIPIK 7 = okuma 3 + PUT 1 + envanter GET 1 + bag GET 1 + ilan GET 1;
  ILAN_BAG 9 (bag POST 1 + GET 1); ILAN_UST 23 = okuma 3 + PUT 1 + envanter GET 3 + bag GET 1 + POST 1 + GET 3 + ilan GET 1
  + otomatik geri alma (canli envanter GET 1 + PUT 1 + GET 3 + bag GET 1 + POST 1 + GET 3) = 23; kontrol 3.
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
import yd_yapi_kuru as K  # noqa: E402

ONAY = {"yaz": "SERDAR_YD_YAPI_YAZ", "geri-al": "SERDAR_YD_YAPI_GERI_AL", "profil": "SERDAR_YD_PROFIL",
        "profil-geri-al": "SERDAR_YD_PROFIL_GERI_AL"}
OKUMA, TEKRAR = 3, 3
ILAN_TIPIK = OKUMA + 1 + 1 + 1 + 1
ILAN_BAG = ILAN_TIPIK + 2
GERI_UST = 1 + 1 + TEKRAR + 1 + 1 + TEKRAR     # canli envanter okuma + PUT + GET + bag
ILAN_UST = OKUMA + 1 + TEKRAR + 1 + 1 + TEKRAR + 1 + GERI_UST
BEKLE_SN = 3
INV_PUT = "/listings/{lid}/inventory?max_variations_supported=3"
ON_PROP = ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property")
assert (ILAN_TIPIK, ILAN_BAG, ILAN_UST) == (7, 9, 23)
VARSAYILAN_LISTE = KOK.parents[1] / "data/pod/yd78_ids.csv"     # yd_yapi_kuru --liste varsayilani (profil kullanan taramasi)


class Kayma(Exception):
    """Canli plandan farkli: bu ilana yazilmaz."""


class Fail(Exception):
    """Yazim sonrasi dogrulama tutmadi: geri alinir, kosu durur."""


def j(x):
    return json.loads(json.dumps(x, ensure_ascii=False))


# ------------------------------------------------------------------ imza
def urun_imza(p, sabit_id):
    """ADET HARIC (satis adedi dusurur); value_ids yalniz sabit_id ozelliklerinde sayilir (varsayilan hicbiri: Format / Size kimliklerini
    Etsy uretir, Style kimligi korunmasa da bag ADA gore denetlenir ve onarilir)."""
    props = tuple(sorted((v.get("property_id"),
                          # ad yalniz ozel ozelliklerde (513 / 514; bizim verdigimiz ad); taksonomi ozelliginin adini Etsy kendisi dondurur
                          v.get("property_name") if v.get("property_id") in (K.STIL_PID, K.FORMAT_PID) else None,
                          tuple(v.get("values") or []),
                          tuple(v.get("value_ids") or []) if v.get("property_id") in sabit_id else ())
                         for v in p.get("property_values") or []))
    return (p.get("sku") or "", props,
            tuple((K.para(o.get("price")), bool(o.get("is_enabled")), o.get("readiness_state_id")) for o in p.get("offerings") or []))


def imza(inv, sabit_id=()):
    return (tuple(sorted(urun_imza(p, sabit_id) for p in inv.get("products") or [])),
            tuple(tuple(sorted(inv.get(k) or [])) for k in ON_PROP))


def adetler(inv):
    return {o.get("quantity") for p in inv.get("products") or [] for o in p.get("offerings") or []}


def adet_uygula(govde, q):
    g = j(govde)
    for p in g["products"]:
        for o in p["offerings"]:
            o["quantity"] = q
    return g


def geri_govde(ham):
    """Ham (eski) envanterin PUT govdesi: urun / deger kimlikleri ve *_on_property aynen."""
    return {"products": [K.K.kopya(p) for p in ham.get("products") or []], **{k: ham.get(k) or [] for k in ON_PROP}}


def menu_ham(inv):
    pr = inv.get("products") or []
    return [list(dict.fromkeys(K.deger(p, x) for p in pr)) for x in (K.STIL_PID, K.FORMAT_PID)]


# ------------------------------------------------------------------ plan
def plan_yukle(d, sec, haric):
    """-> (plan {lid: kayit}, secilen [lid], haric [lid]). Hata -> SystemExit (Etsy istegi yok)."""
    d = pathlib.Path(d)
    dosya = {p.name[5:-5]: p for p in d.glob("KURU_*.json")}
    if not dosya:
        raise SystemExit(f"DUR: plan klasorunde KURU_*.json yok ({d})")
    if not (d / "PLAN.csv").is_file():
        raise SystemExit("DUR: plan klasorunde PLAN.csv yok")
    with open(d / "PLAN.csv", encoding="utf-8") as f:
        satir = {r["listing_id"]: r for r in csv.DictReader(f)}
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
        if k.get("durum") not in ("PLAN", "ZATEN") or k.get("hata") or satir[lid].get("sonuc") != k.get("durum"):
            h.append(f"plan {k.get('durum')} {k.get('hata')}")
        elif k["durum"] == "PLAN":   # butunluk: ham veriden bu kodla yeniden kur
            yuk, he = K.envanter_plani(k["envanter_ham_yedek"], k.get("boy_ozellik"))
            if he or yuk is None or j(yuk) != k["envanter_yuk"]:
                h.append(f"envanter govdesi yeniden kurulamadi / farkli {he[:2]}")
            if K.baglar(k["envanter_ham_yedek"], k["renk_bagi_ham"])[1]:
                h.append("plan Style baglari 5 degil")
        if h:
            raise SystemExit(f"DUR: plan {lid}: {'; '.join(h)} (haric ile atlanabilir)")
        plan[lid] = k
    return plan, secilen, sorted(haric)


# ------------------------------------------------------------------ canli
def oku(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    return L, inv, vi


def kapi(k, L, inv, vi, geri=False):
    """-> {"envanter": yaz|atla, "bag": atla|onar, "adet": q}. Kayma -> yazim yok."""
    if L.get("state") != "active":
        raise Kayma(f"state {L.get('state')} (active degil; taslak / pasif ilana yazilmaz)")
    q = adetler(inv)
    if len(q) != 1:
        raise Kayma(f"adet tek deger degil {sorted(q, key=str)}")
    if k["durum"] == "ZATEN":
        raise Kayma("PLAN_ZATEN")
    ham, yuk = k["envanter_ham_yedek"], k["envanter_yuk"]
    pid = k["boy_ozellik"]["property_id"]
    hedef_bag = k["bag_ad"] and [tuple(x) for x in k["bag_ad"]]
    canli_bag = K.baglar(inv, vi)[0]
    s = {"adet": next(iter(q))}
    c = imza(inv)
    if c == imza(ham):
        s["envanter"] = "atla" if geri else "yaz"
        if not geri and canli_bag != hedef_bag:
            raise Kayma(f"Style bagi plandan farkli: {canli_bag}")
        if geri and menu_ham(inv) != menu_ham(ham):
            s["envanter"] = "yaz"
    elif c == imza(yuk):
        if K.menu(inv, pid) != K.menu(yuk, pid):
            raise Kayma("envanter hedefte ama menu sirasi plandan farkli (geri-al ile duzeltilir)")
        s["envanter"] = "yaz" if geri else "atla"
    else:
        raise Kayma(f"envanter plandan farkli (urun {len(inv.get('products') or [])})")
    s["bag"] = "atla" if canli_bag == hedef_bag else "onar"
    return s


def kota_yeter(api, gerek):
    try:
        api.kota_kapisi("ilan")   # CLAUDE.md: toplu islerde ilan basina kota kapisi
    except SystemExit:
        return False
    return api.remaining is None or int(api.remaining) >= gerek + E.KOTA_SINIRI


def tekrar_oku(fn, kosul, n=TEKRAR):
    x = None
    for i in range(n):
        x = fn()
        if kosul(x):
            return x, True
        if i < n - 1:
            time.sleep(BEKLE_SN)
    return x, False


def bag_kur(api, shop, lid, inv1, hedef_bag, R_):
    """Style bagini deger ADINA gore kurar (pod_5x7_yaz.renk_onar yolu): GET 1 (+ POST 1 + GET en cok 3)."""
    vi1 = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    if K.baglar(inv1, vi1)[0] == hedef_bag:
        return
    vid = {(v.get("property_id"), a): i for p in inv1.get("products") or [] for v in p.get("property_values") or []
           for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
    istek = [{"property_id": pid, "value_id": vid[(pid, a)], "image_id": img} for pid, a, img in hedef_bag if (pid, a) in vid]
    if len(istek) != len(hedef_bag):
        raise Fail(f"Style bagi eslesmesi kurulamadi {len(istek)}/{len(hedef_bag)}")
    R_["yazilan"].append("bag")     # istekten ONCE (envanter_yaz ile ayni)
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
    _, ok = tekrar_oku(lambda: (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
                       lambda v: K.baglar(inv1, v)[0] == hedef_bag)
    if not ok:
        raise Fail("Style bagi kurulamadi (geri okuma)")


def envanter_yaz(api, lid, govde, kaynak, pid, R_, ad):
    """PUT (?max_variations_supported=3) + geri okuma (imza, adet, menu). -> canli envanter.
    Adim PUT'tan ONCE yazilan'a girer: Etsy PUT'u uygulayip 5xx / zaman asimi dondurse de otomatik geri alma kosar (inceleme 30 Eki 1)."""
    R_["yazilan"].append(ad)
    api.put_json(INV_PUT.format(lid=lid), govde)
    q = adetler(govde)
    inv1, ok = tekrar_oku(lambda: api.get(f"/listings/{lid}/inventory") or {},
                          lambda x: imza(x) == imza(kaynak) and adetler(x) == q)
    if not ok:
        raise Fail(f"{ad} geri okuma plandan farkli (urun {len(inv1.get('products') or [])}, adet {sorted(adetler(inv1), key=str)})")
    if (pid and K.menu(inv1, pid) != K.menu(kaynak, pid)) or (not pid and menu_ham(inv1) != menu_ham(kaynak)):
        raise Fail(f"{ad} menu sirasi plandan farkli")
    return inv1


def geri_al_ilan(api, shop, lid, k, q, R_):
    """Ham envanter (adet canli) + Style baglari. -> None | Fail."""
    ham = k["envanter_ham_yedek"]
    inv1 = envanter_yaz(api, lid, adet_uygula(geri_govde(ham), q), ham, None, R_, "geri_envanter")
    bag_kur(api, shop, lid, inv1, [tuple(x) for x in k["bag_ad"]], R_)


def geri_al_gerekirse(api, shop, lid, k, q, R_):
    """Otomatik geri alma: canli envanter okunur (GET 1). Ham yedekle ayni (imza + menu) ise envanter PUT yok, yalniz bag denetlenir /
    onarilir; farkliysa ham envanter PUT + bag (geri_al_ilan). -> sonuc metni | Fail."""
    ham = k["envanter_ham_yedek"]
    inv_c = api.get(f"/listings/{lid}/inventory") or {}
    if imza(inv_c) == imza(ham) and menu_ham(inv_c) == menu_ham(ham):
        bag_kur(api, shop, lid, inv_c, [tuple(x) for x in k["bag_ad"]], R_)
        return "TAMAM (canli envanter ham yedekle ayni; envanter PUT yok, bag denetlendi)"
    geri_al_ilan(api, shop, lid, k, q, R_)
    return "TAMAM"


def ilan_yaz(api, shop, lid, k, geri, out, kontrol):
    R_ = {"listing_id": lid, "pilot": k.get("pilot"), "istek_once": api.calls, "kota_once": api.remaining}
    if not kota_yeter(api, OKUMA if kontrol else ILAN_UST):
        R_.update(sonuc="KOTA", neden=f"kalan {api.remaining} < ilan esigi {ILAN_UST} + {E.KOTA_SINIRI} (ilana baslanmadi)")
        return R_
    try:
        L, inv, vi = oku(api, shop, lid)
    except (Exception, SystemExit) as e:   # noqa: BLE001
        R_.update(sonuc="HATA_OKUMA", neden=f"{type(e).__name__}: {str(e)[:300]}", istek=api.calls - R_["istek_once"])
        return R_
    try:
        s = kapi(k, L, inv, vi, geri)
    except Kayma as e:
        z = str(e) == "PLAN_ZATEN"   # kuru kosuda hedef yapidaydi: yazim / geri alma yok (ham eski yapi yok)
        R_.update(sonuc="PLAN_ZATEN" if z else "ATLANDI_KAYMA", neden="kuru kosuda hedef yapida" if z else str(e),
                  istek=api.calls - R_["istek_once"])
        return R_
    R_["adim"] = s
    zaten = s["envanter"] == "atla" and s["bag"] == "atla"
    if kontrol or zaten:
        R_.update(sonuc=("KONTROL_ZATEN" if zaten else "KONTROL_YAZILACAK") if kontrol else "ZATEN", istek=api.calls - R_["istek_once"])
        return R_
    if not kota_yeter(api, ILAN_UST - OKUMA):
        R_.update(sonuc="KOTA", neden=f"okuma sonrasi kalan {api.remaining} < {ILAN_UST - OKUMA} + {E.KOTA_SINIRI} (yazim yok)")
        return R_
    (out / f"YEDEK_{lid}.json").write_text(json.dumps({"listing_id": lid, "mod": "geri-al" if geri else "yaz", "listing": L,
                                                       "inventory": inv, "variation_images": vi}, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    R_["yazilan"] = []
    pid = k["boy_ozellik"]["property_id"]
    hedef_bag = [tuple(x) for x in k["bag_ad"]]
    try:
        if geri:
            if s["envanter"] == "yaz":
                geri_al_ilan(api, shop, lid, k, s["adet"], R_)
            else:
                bag_kur(api, shop, lid, inv, hedef_bag, R_)
        else:
            inv1 = inv
            if s["envanter"] == "yaz":
                inv1 = envanter_yaz(api, lid, adet_uygula(k["envanter_yuk"], s["adet"]), k["envanter_yuk"], pid, R_, "envanter")
            bag_kur(api, shop, lid, inv1, hedef_bag, R_)
            L1 = api.get(f"/listings/{lid}") or {}
            if L1.get("state") != "active":
                raise Fail(f"yazim sonrasi state {L1.get('state')}")
        R_.update(sonuc="TAMAM")
    except (Exception, SystemExit) as e:   # noqa: BLE001  (SystemExit: HTTP hatasi / kota tabani)
        R_.update(sonuc="FAIL", neden=f"{type(e).__name__}: {str(e)[:300]}", iz=traceback.format_exc()[-800:])
        if not geri and R_["yazilan"]:     # otomatik geri alma: canli ham'dan farkliysa ham envanter + baglar
            try:
                R_["geri_alma"] = geri_al_gerekirse(api, shop, lid, k, s["adet"], R_)
            except (Exception, SystemExit) as e2:   # noqa: BLE001
                R_["geri_alma"] = f"FAIL {type(e2).__name__}: {str(e2)[:200]} (YEDEK_{lid}.json ile geri-al)"
    R_.update(istek=api.calls - R_["istek_once"], kota_sonra=api.remaining)
    return R_


# ------------------------------------------------------------------ profil
GOVDE_SABIT = ("min_delivery_days", "max_delivery_days")


def hedef_govde(d, primary, secondary):
    """updateShippingProfileDestination govdesi CANLI hedeften: ucret disi alanlar aynen (inceleme 30 Eki 4).
    shipping_carrier_id 0 / bos = Etsy varsayilani (tasiyici secilmemis): gonderilmez; doluysa mail_class ile birlikte gonderilir."""
    g = {"primary_cost": primary, "secondary_cost": secondary}
    g.update({x: d[x] for x in GOVDE_SABIT if d.get(x) is not None})
    if d.get("shipping_carrier_id"):
        g.update(shipping_carrier_id=d["shipping_carrier_id"], mail_class=d.get("mail_class"))
    if d.get("destination_country_iso"):
        g["destination_country_iso"] = d["destination_country_iso"]
    else:
        g["destination_region"] = d.get("destination_region") or "none"
    return g


def liste_ids(yol):
    with open(yol, encoding="utf-8-sig") as f:
        return {r["listing_id"].strip() for r in csv.DictReader(f) if (r.get("listing_id") or "").strip()}


def profil(api, shop, pplan, geri, yd_ids):
    """PROFIL_PLAN yazim listesi: yalniz ucret (0 / eski); teslim gunleri, tasiyici ve diger hedefler ayni kalir.
    yd_ids: YD ilan listesi; yazim aninda profili bu liste disinda kullanan ilan varsa DUR (kuru plandan sonra eklenmis olabilir)."""
    if pplan.get("durum") == "UCRETSIZ":
        return {"sonuc": "ZATEN", "neden": "plan: tum hedefler ucretsiz"}
    if pplan.get("durum") != "YAZILACAK" or pplan.get("hata") or pplan.get("yd78_disi_kullanan"):
        raise SystemExit(f"DUR: PROFIL_PLAN yazilamaz (durum {pplan.get('durum')}, hata {pplan.get('hata')}, "
                         f"78 disi {pplan.get('yd78_disi_kullanan')})")
    P = pplan["profil"]
    ref = {d["shipping_profile_destination_id"]: d for d in pplan["once_tum_hedefler"]}

    def hd(sp):
        return {d.get("shipping_profile_destination_id"): d for d in sp.get("shipping_profile_destinations") or []}

    def ucret(d):
        return K.para(d.get("primary_cost")), K.para(d.get("secondary_cost"))

    def sabit(d):
        return {x: v for x, v in d.items() if x not in ("primary_cost", "secondary_cost")}
    h0 = hd(api.get(f"/shops/{shop}/shipping-profiles/{P}") or {})
    if set(h0) != set(ref) or any(sabit(h0[i]) != sabit(ref[i]) for i in ref):
        return {"sonuc": "ATLANDI_KAYMA", "neden": "profil hedefleri plandan farkli"}
    yaz = {y["destination_id"]: y for y in pplan["yazim"]}
    once = {i: ((y["once"]["primary_cost"], y["once"]["secondary_cost"]) if not geri else (0, 0)) for i, y in yaz.items()}
    sonra = {i: ((0, 0) if not geri else (y["once"]["primary_cost"], y["once"]["secondary_cost"])) for i, y in yaz.items()}
    if any(ucret(ref[i]) != ucret(h0[i]) for i in ref if i not in yaz):
        return {"sonuc": "ATLANDI_KAYMA", "neden": "yazim disi hedefin ucreti plandan farkli"}
    if all(ucret(h0[i]) == sonra[i] for i in yaz):
        return {"sonuc": "ZATEN"}
    if any(ucret(h0[i]) not in (once[i], sonra[i]) for i in yaz):
        return {"sonuc": "ATLANDI_KAYMA", "neden": "ucret plan once / sonra degil"}
    if not kota_yeter(api, len(K.DURUMLAR) + len(yaz) + 1):
        return {"sonuc": "KOTA", "neden": f"kalan {api.remaining}"}
    kim = K.kullananlar(api, shop, P)          # yazim aninda yeniden tarama (kuru plan eski olabilir; inceleme 30 Eki 4)
    disari = sorted({x for x, _ in kim} - set(yd_ids))
    if disari:
        return {"sonuc": "DUR", "neden": f"profili YD listesi disinda {len(disari)} ilan kullaniyor ({disari[:5]}); yazim yok",
                "yd_disi_kullanan": disari}
    if not kota_yeter(api, len(yaz) + 1):
        return {"sonuc": "KOTA", "neden": f"kalan {api.remaining}"}
    for i in yaz:
        if ucret(h0[i]) == sonra[i]:
            continue
        api.put(f"/shops/{shop}/shipping-profiles/{P}/destinations/{i}", hedef_govde(h0[i], *sonra[i]))
    h1 = hd(api.get(f"/shops/{shop}/shipping-profiles/{P}") or {})
    bek = {i: (sabit(ref[i]), sonra[i] if i in yaz else ucret(ref[i])) for i in ref}
    gel = {i: (sabit(d), ucret(d)) for i, d in h1.items()}
    if gel != bek:
        return {"sonuc": "FAIL", "neden": "profil geri okuma beklenen degil"}
    return {"sonuc": "TAMAM", "yazilan": len(yaz)}


# ------------------------------------------------------------------ ana
def calis(api, shop, a, out):
    sec = [x for x in (a.sadece or "").split(",") if x]
    haric = [x for x in (a.haric or "").split(",") if x]
    kontrol = a.mod == "kontrol"
    if kontrol:
        K.K.salt_okur(api)
    if a.mod in ("profil", "profil-geri-al"):
        try:
            pplan = json.loads((pathlib.Path(a.plan) / "PROFIL_PLAN.json").read_text(encoding="utf-8"))
            r = profil(api, shop, pplan, a.mod == "profil-geri-al", liste_ids(a.liste))
        except (Exception, SystemExit) as e:   # noqa: BLE001  (HTTP hatasi / kota tabani / plan DUR): SONUC.json yine yazilir
            r = {"sonuc": "HATA", "neden": f"{type(e).__name__}: {str(getattr(e, 'code', None) or e)[:300]}",
                 "iz": traceback.format_exc()[-800:]}
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
    ozet = {"mod": a.mod, "plan_damga": a.plan_damga, "secilen": len(secilen), "haric": haric, "sayim": say, "yapilmadi": yapilmadi,
            "istek": api.calls, "kota_son": api.remaining, "ilan_ust": ILAN_UST, "kota_siniri": E.KOTA_SINIRI}
    (out / "SONUC.json").write_text(json.dumps({"ozet": ozet, "ilanlar": sonuc}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "sonuc", "envanter", "bag", "yazilan", "geri_alma", "istek", "kota_sonra", "neden"])
        for r in sonuc:
            ad = r.get("adim") or {}
            w.writerow([r["listing_id"], r["sonuc"], ad.get("envanter", ""), ad.get("bag", ""), "+".join(r.get("yazilan") or []),
                        r.get("geri_alma", ""), r.get("istek", ""), r.get("kota_sonra", ""), r.get("neden", "")])
        w.writerows([x, "HARIC", "", "", "", "", "", "", "--haric"] for x in haric)
        w.writerows([x, "YAPILMADI", "", "", "", "", "", "", "kosu onceki ilanda durdu"] for x in yapilmadi)
    (out / "OZET.md").write_text(
        f"# YD yapi {a.mod} (plan KURU_{a.plan_damga})\n\n- secilen {len(secilen)}, haric {len(haric)}, sayim {say}\n"
        f"- yapilmadi {len(yapilmadi)}; istek {api.calls}; kota son {api.remaining}\n"
        + "".join(f"- {r['listing_id']}: {r['sonuc']} {r.get('adim', '')} {r.get('neden', '')} {r.get('geri_alma', '')}\n" for r in sonuc),
        encoding="utf-8")
    print(f"::notice::SONUC {a.mod} {say} yapilmadi {len(yapilmadi)} istek {api.calls} kota {api.remaining}", flush=True)
    iyi = ("KONTROL_YAZILACAK", "KONTROL_ZATEN", "PLAN_ZATEN") if kontrol else ("TAMAM", "ZATEN", "PLAN_ZATEN")
    return 0 if all(r["sonuc"] in iyi for r in sonuc) and not yapilmadi else 1


def argumanlar(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["kontrol", "yaz", "geri-al", "profil", "profil-geri-al"])
    ap.add_argument("--plan", required=True, help="KURU_<plan_damga> klasoru (KURU_*.json, PLAN.csv, PROFIL_PLAN.json)")
    ap.add_argument("--plan-damga", required=True)
    ap.add_argument("--sadece", default="")
    ap.add_argument("--haric", default="")
    ap.add_argument("--onay", default="")
    ap.add_argument("--tum", action="store_true", help="yaz: --sadece olmadan plandaki tum ilanlar (pilot sonrasi, acik secim)")
    ap.add_argument("--liste", default=str(VARSAYILAN_LISTE), help="profil: YD ilan listesi (kullanan taramasi)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d+", a.plan_damga) or pathlib.Path(a.plan).name != f"KURU_{a.plan_damga}":
        raise SystemExit(f"DUR: plan klasoru KURU_{a.plan_damga} degil ({pathlib.Path(a.plan).name})")
    for x in (a.sadece, a.haric):
        if not re.fullmatch(r"(\d+(,\d+)*)?", x):
            raise SystemExit("DUR: --sadece / --haric virgullu listing_id olmali")
    if a.mod != "kontrol" and a.onay != ONAY[a.mod]:
        raise SystemExit(f"DUR: {a.mod} icin onay sozcugu yok / yanlis (yazim yok)")
    if a.mod == "yaz" and not a.sadece and not a.tum:
        raise SystemExit("DUR: yaz icin --sadece (pilot) ya da acik --tum gerekli (yazim yok)")
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
