#!/usr/bin/env python3
"""YD (1st Anniversary, 78 ilan) YENI ILAN YAPISI: KURU KOSU (ETSY'YE YAZMA YOK; Serdar / Merkez 30 Eki gece isi 6, hazirlik).

Yalniz GET; yazma yontemleri kapali (pod_5x7_kuru.salt_okur: put/patch/post/delete + _call GET disi DUR).
Hedef yapi (ilan basina 3 varyasyon: Style x Format x Size = 5 x 2 x 14 = 140 urun):
  Style  (513, canli): Starlit, Timeless, First Page, Layers, Botanical (value_id canlidan; stil-gorsel baglari bu degerlere bagli kalir)
  Format (514, canli): FORMATLAR = "Digital File", "Print" (eski: Digital card 5x7, Digital file 8x10, Shipped print 8x10)
  Size   (--boy-pid, varsayilan BOY_PID 516 = taksonomi 121 Custom3, menu adi "Size"; 31 Eki salt okuma): 14 boy, poster ile ayni liste/sira:
         5x7 (pod_5x7_kuru.ETIKET_5X7) + pod_5x7_kuru.BOYLAR (8x10 ... 24x36, A4, A3, A2).
Fiyat (hicbiri burada uydurulmadi; FIYAT_KAYNAK):
  Digital File: her boyda 3.90  (pod_5x7_kuru.FIYAT_5X7["Digital File"] = print_fiyat_v2.DIJITAL = 3.90, Serdar 25 Eki)
  Print 5x7   : 19.90           (pod_5x7_kuru.FIYAT_5X7["Print"], Serdar 26 Eki)
  Print diger : print_fiyat_v2.HEDEF (Serdar 25 Eki wall art tablosu: 8x10 24.90 ... 24x36 64.90)
  Canli kapi: --poster-ref ilaninin (wall art) canli envanterinde her boyun Print fiyati ve Digital File fiyati bu tabloyla ayni olmali;
  14 boyun (5x7 dahil; 30 Eki yazimi sonrasi poster 5x7 canli) her biri hem Digital File hem Print olarak posterde bulunmali, tanimsiz
  boy etiketi / format olmamali; degilse KOSU BLOK (bos envanter ya da etiket degisikligi sessiz gecmez; inceleme 30 Eki madde 2).
Diger urun alanlari: adet = ilandaki tek adet (999); readiness: Digital File = canli dijital urunlerin readiness'i, Print = canli
  "Shipped print 8x10" urunlerinin readiness'i (her biri tek deger olmali); SKU BY-<AAA_BBB>-<ST|TL|FP|LY|BO>-<boy> (Print) ve
  ...-<boy>-DIGITAL (Serdar 31 Eki 1a kisa stil kodu, en cok 27 karakter; scripts/siparis_by/by_sku.py, eski uzun kodu da cozer). price_on_property [514, boy], sku_on_property [513, 514, boy], readiness_on [514],
  quantity_on []. Envanter PUT ?max_variations_supported=3 ile (yazim betigi yd_yapi_yaz.py).
Kapilar (ilan basina; biri tutmazsa BLOK, yazim yok):
  state active (CLAUDE.md 7 Eyl: updateListing taslagi yayina alir; bu is updateListing CAGIRMAZ, yine de taslak/pasif ilan ATLANIR);
  taksonomi kosudaki ilk ilanla ayni; canli envanter eski yapi: 15 urun = 5 stil x 3 eski format, SKU kalibi, tek adet, readiness
  grup basina tek; 5 Style bagi (property 513, 5 ad, value_id envanterle ayni); plan govdesi 140 urun, (stil, format, boy) tekil,
  menu sirasi (stil, format, boy) hedef sirada; boy ozelligi taksonomide supports_variations, possible_values doluysa etiketler
  icinde, scales doluysa --boy-scale-id o olcekler icinde. Canli zaten hedef yapida -> ZATEN (yazim yok).
  Aciklamada eski format satirlari (Digital card / Shipped print / 8x10 / 5x7) yalniz RAPOR (metin_celiski; metin ayri is, Serdar).
Kargo (her ulkeye ucretsiz + takipli): ilanlarin kargo profili (tek profil olmali) okunur. Her hedef primary = secondary = 0 ve
  "her yer" (EVERYWHERE) hedefi var -> UCRETSIZ. Degilse PROFIL_PLAN yazim listesi (yalniz ucret 0, teslim gunleri ayni;
  profil_ucretsiz.py kalibi); profili YD 78 disinda kullanan ilan varsa (active/draft/inactive/expired/sold_out) profil BLOK.
  "Takipli": API alani yok (dogrulanmadi); hedeflerin shipping_carrier_id / mail_class degerleri rapora yazilir, karar Serdar.
Istek (kod sayimi): ilan basina 3 GET (listing, inventory, variation-images); kosu basina taksonomi 1 + poster ref 1 + profil 1 +
  profil kullanan taramasi (5 durum x sayfa). Yazim tahmini ISTEK_TAHMINI.json (yd_yapi_yaz.ILAN_UST).
Cikti --out (Drive klasoru KURU_<plan_damga>): KURU_<lid>.json, PLAN.csv, PROFIL_PLAN.json, TAKSONOMI.json, ISTEK_TAHMINI.json, OZET.md."""
import argparse
import csv
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK)); sys.path.insert(1, str(KOK.parent / "pod"))
import etsy_common as E  # noqa: E402
import pod_5x7_kuru as K  # noqa: E402
import print_fiyat_v2 as PF  # noqa: E402
sys.path.insert(0, str(KOK.parent / "siparis_by"))
import by_sku as BS  # noqa: E402  YD SKU (kisa stil kodu ST/TL/FP/LY/BO + eski uzun kod cozumu)

STIL_PID, FORMAT_PID = 513, 514
# Size (Serdar 31 Eki karar 5a): taksonomi 121'de "Size" adli ozellik yok (21 ozellik; boy adayi 0). Varyasyon destekleyen 3. ozel
# ozellik 516 (name Custom3, display "Custom Property", olceksiz, sabit deger yok). Kaynak: kupa-yd-oku kosu 41180774733 YD_BOY.json
# (pilot 4595350971, salt okuma 4 istek). Etsy'nin 513 + 514 + 516 ucluzunu kabul ettigi YAZIMLA dogrulanmadi (ilk pilot yazimda olculur).
BOY_PID = 516
OZEL_PID = (513, 514, 516)   # taksonomi 121 ozel (Custom1-3) ozellikleri (YD_BOY.json; 515 yok): menu adi property_name ile verilir
SKU_MAX = 32   # Etsy SKU siniri (pod_sku.MAX_LEN; 34 karakter -> 400, kupa_taslak.py)
STILLER = ("Starlit", "Timeless", "First Page", "Layers", "Botanical")          # canli sira (yd_kapak_yukle.STILLER)
ESKI_FORMAT = {"Digital card 5x7": "dijital", "Digital file 8x10": "dijital", "Shipped print 8x10": "baski"}   # by_baski_ekle
ESKI_SKU_EK = {"Digital card 5x7": "CARD5X7", "Digital file 8x10": "FILE8X10", "Shipped print 8x10": "PRINT8X10"}
DIJITAL, BASKI = "Digital File", "Print"                                         # poster Format adlari (canli 78 poster)
FORMATLAR = (DIJITAL, BASKI)
BOYLAR = [(K.ETIKET_5X7, "5x7")] + list(K.BOYLAR.items())                         # 14 boy, poster menu sirasi
DIJITAL_FIYAT = K.FIYAT_5X7["Digital File"]
PRINT_FIYAT = {"5x7": K.FIYAT_5X7["Print"], **{k: v[0] for k, v in PF.HEDEF.items()}}
FIYAT_KAYNAK = {"Digital File (her boy)": "scripts/etsy/pod_5x7_kuru.py FIYAT_5X7['Digital File'] = scripts/pod/print_fiyat_v2.py DIJITAL (Serdar 25 Eki)",
                "Print 5x7": "scripts/etsy/pod_5x7_kuru.py FIYAT_5X7['Print'] (Serdar 26 Eki)",
                "Print 8x10..A2": "scripts/pod/print_fiyat_v2.py HEDEF[boy][0] (Serdar 25 Eki wall art tablosu)"}
SKU_RX = re.compile(r"^(BY-[A-Z]{3}_[A-Z]{3}-([A-Z]+))-(CARD5X7|FILE8X10|PRINT8X10)$")
METIN_RX = re.compile(r"Digital card|Digital file 8x10|Shipped print|\b8 ?x ?10\b|\b5 ?x ?7\b", re.I)
KOSU_OKUMA = 3            # ilan basina GET
DURUMLAR = ("active", "draft", "inactive", "expired", "sold_out")

assert len(BOYLAR) == 14 and all(k in PRINT_FIYAT for _, k in BOYLAR), "boy / fiyat tablosu eksik"
assert DIJITAL_FIYAT == PF.DIJITAL == 3.90, "dijital fiyat kaynaklari celisiyor"


def para(p):
    return K.para(p)


def pv(p, pid):
    return K.pv(p, pid)


def deger(p, pid):
    v = pv(p, pid).get("values") or [None]
    return v[0]


def ilk(xs):
    return xs[0] if xs else None


# ------------------------------------------------------------------ envanter
def boy_ozellik(tax, boy_pid, boy_scale=None):
    """-> (property_values sablonu {property_id, property_name[, scale_id]}, hata[]). tax: taksonomi ozellik listesi."""
    if not boy_pid:
        return None, ["boy ozelligi secilmedi (--boy-pid; adaylar TAKSONOMI.json, Serdar / Merkez karari)"]
    if boy_pid in (STIL_PID, FORMAT_PID):
        return None, [f"boy ozelligi {boy_pid} Style / Format ile ayni"]
    p = next((x for x in tax if x.get("property_id") == boy_pid), None)
    if not p:
        return None, [f"boy ozelligi {boy_pid} ilanin taksonomisinde yok"]
    h = []
    if not p.get("supports_variations"):
        h.append(f"ozellik {boy_pid} varyasyon desteklemiyor")
    olasi = {str(v.get("name")) for v in p.get("possible_values") or []}
    if olasi and not {e for e, _ in BOYLAR} <= olasi:
        h.append(f"ozellik {boy_pid} sabit degerli; boy etiketleri degerlerde yok ({sorted({e for e, _ in BOYLAR} - olasi)[:3]})")
    olcek = {s.get("scale_id") for s in p.get("scales") or []}
    if olcek and boy_scale not in olcek:
        h.append(f"ozellik {boy_pid} olcekli ({sorted(olcek)}); --boy-scale-id gerekli")
    ozel = boy_pid in OZEL_PID or str(p.get("name") or "").lower().startswith("custom")
    sab = {"property_id": boy_pid, "property_name": "Size" if ozel else (p.get("display_name") or p.get("name") or "Size")}
    if boy_scale is not None:
        sab["scale_id"] = boy_scale
    return sab, h


def eski_yapi(inv):
    """Canli eski yapi kapisi. -> (stil {ad: value_id}, sku_on {stil: prefix}, adet, hazirlik {dijital, baski}, hata[])."""
    pr, h = inv.get("products") or [], []
    stil, pre, hz, ad = {}, {}, {"dijital": set(), "baski": set()}, set()
    kombi = []
    for p in pr:
        s, f = deger(p, STIL_PID), deger(p, FORMAT_PID)
        kombi.append((s, f))
        if s not in STILLER or f not in ESKI_FORMAT:
            h.append(f"bilinmeyen urun {s}/{f}"); continue
        vid = ilk(pv(p, STIL_PID).get("value_ids") or [])
        if stil.setdefault(s, vid) != vid:
            h.append(f"Style {s} iki farkli value_id")
        m = SKU_RX.match(p.get("sku") or "")
        if not m or m.group(3) != ESKI_SKU_EK[f] or m.group(2) != s.upper().replace(" ", ""):
            h.append(f"SKU kalibi {p.get('sku')} ({s}/{f})")
        elif pre.setdefault(s, m.group(1)) != m.group(1):
            h.append(f"SKU on eki stil icinde farkli {p.get('sku')}")
        for o in p.get("offerings") or []:
            ad.add(o.get("quantity")); hz[ESKI_FORMAT[f]].add(o.get("readiness_state_id"))
        if len(p.get("property_values") or []) != 2:
            h.append(f"urun {p.get('sku')} {len(p.get('property_values') or [])} ozellik (2 beklenir)")
    if len(pr) != 15 or sorted(kombi) != sorted((s, f) for s in STILLER for f in ESKI_FORMAT):
        h.append(f"eski yapi degil: {len(pr)} urun (15 = 5 stil x 3 format beklenir)")
    if len(ad) != 1:
        h.append(f"adet tek deger degil {sorted(ad, key=str)}")
    for k, v in hz.items():
        if len(v) != 1 or None in v:
            h.append(f"{k} readiness tek deger degil {sorted(v, key=str)}")
    return stil, pre, ilk(sorted(ad, key=str)), {k: ilk(sorted(v, key=str)) for k, v in hz.items()}, h


def envanter_plani(inv, boy_sab):
    """(yuk, hata[]). yuk = updateListingInventory govdesi (gonderilmez). Saf fonksiyon (yazim betigi ayni kodla yeniden kurar)."""
    stil, pre, adet, hz, h = eski_yapi(inv)
    if h or boy_sab is None:
        return None, h
    pid = boy_sab["property_id"]
    urun = []
    for s in STILLER:
        for f in FORMATLAR:
            for etiket, kod in BOYLAR:
                urun.append({
                    "sku": BS.sku(pre[s].split("-")[1], s, kod, f == DIJITAL),   # kisa stil kodu (Serdar 31 Eki 1a; <= 27 kr.)
                    "property_values": [{"property_id": STIL_PID, "property_name": "Style", "value_ids": [stil[s]], "values": [s]},
                                        {"property_id": FORMAT_PID, "property_name": "Format", "values": [f]},   # value_ids: Etsy
                                        {**boy_sab, "values": [etiket]}],
                    "offerings": [{"price": DIJITAL_FIYAT if f == DIJITAL else PRINT_FIYAT[kod], "quantity": adet, "is_enabled": True,
                                   "readiness_state_id": hz["dijital" if f == DIJITAL else "baski"]}]})
    yuk = {"products": urun, "price_on_property": [FORMAT_PID, pid], "quantity_on_property": [],
           "sku_on_property": [STIL_PID, FORMAT_PID, pid], "readiness_state_on_property": [FORMAT_PID]}
    return yuk, hedef_kapisi(yuk, pid)


def hedef_kapisi(yuk, pid):
    """Hedef govde kendi icinde tutarli mi (plan ve yazim sonrasi geri okuma ayni kurali kullanir)."""
    h, pr = [], yuk.get("products") or []
    kombi = [(deger(p, STIL_PID), deger(p, FORMAT_PID), deger(p, pid)) for p in pr]
    uzun = sorted({p.get("sku") or "" for p in pr if len(p.get("sku") or "") > SKU_MAX}, key=len)
    if uzun:   # inceleme 31 Eki: yeni SKU kalibi (on ek + boy + -DIGITAL) 32'yi asabiliyor; SKU bicimi karari Serdar / Merkez
        h.append(f"SKU {len(uzun)} urunde {SKU_MAX} karakteri asiyor (en uzun {len(uzun[-1])}: {uzun[-1]})")
    if len(pr) != 140 or len(set(kombi)) != 140:
        h.append(f"urun {len(pr)} / tekil {len(set(kombi))} (5 x 2 x 14 = 140)")
    if kombi != [(s, f, e) for s in STILLER for f in FORMATLAR for e, _ in BOYLAR]:
        h.append("urun / menu sirasi hedef degil (stil, format, boy)")
    kod = dict(BOYLAR)
    for p in pr:
        f, e = deger(p, FORMAT_PID), deger(p, pid)
        bek = DIJITAL_FIYAT if f == DIJITAL else PRINT_FIYAT.get(kod.get(e))
        if [para(o.get("price")) for o in p.get("offerings") or []] != [bek]:
            h.append(f"fiyat {p.get('sku')} {[para(o.get('price')) for o in p.get('offerings') or []]} != {bek}"); break
    skus = [p.get("sku") for p in pr]
    if len(set(skus)) != len(skus):
        h.append("SKU tekil degil")
    return h


def menu(inv, pid):
    """(stil, format, boy) menu sirasi (dizide ilk gorunus)."""
    pr = inv.get("products") or []
    return [list(dict.fromkeys(deger(p, x) for p in pr)) for x in (STIL_PID, FORMAT_PID, pid)]


def hedefte_mi(inv, pid):
    """Canli envanter zaten hedef yapida mi (yeniden kosu: ZATEN)."""
    return len(inv.get("products") or []) == 140 and not hedef_kapisi(inv, pid)


def baglar(inv, vi):
    """Style baglari ada gore: [(property_id, ad, image_id)] + hata[]."""
    ad = {(v.get("property_id"), i): a for p in inv.get("products") or [] for v in p.get("property_values") or []
          for i, a in zip(v.get("value_ids") or [], v.get("values") or [])}
    b = sorted((x.get("property_id"), ad.get((x.get("property_id"), x.get("value_id")), f"?{x.get('value_id')}"), x.get("image_id"))
               for x in vi or [])
    h = []
    if len(b) != 5 or sorted(x[1] for x in b) != sorted(STILLER) or any(x[0] != STIL_PID for x in b):
        h.append(f"Style bagi {len(b)} / {sorted(str(x[1]) for x in b)} (5 stil, property 513 beklenir)")
    return b, h


def metin_celiski(desc):
    return [s.strip()[:160] for s in (desc or "").split("\n") if METIN_RX.search(s)]


# ------------------------------------------------------------------ poster ref + profil
def poster_fiyat_kapisi(inv):
    """Wall art (poster) canli envanteri: Print boy fiyatlari ve Digital File fiyati tabloyla ayni mi; 14 boyun her biri iki formatta
    posterde var mi (5x7 dahil). Bos envanter, tanimsiz boy etiketi ya da eksik boy -> hata (sessiz gecis yok). -> (rapor, hata[])"""
    canli, h, tanimsiz = {}, [], set()
    for p in inv.get("products") or []:
        f, e = deger(p, 514), deger(p, 513)
        kod = dict(BOYLAR).get(e)
        if kod is None:
            tanimsiz.add(str(e)); continue
        canli.setdefault((f, kod), set()).update(para(o.get("price")) for o in p.get("offerings") or [])
    for (f, kod), v in sorted(canli.items()):
        bek = DIJITAL_FIYAT if f == DIJITAL else PRINT_FIYAT[kod] if f == BASKI else None
        if bek is None or v != {bek}:
            h.append(f"poster {f} {kod} canli {sorted(v)} != tablo {bek}")
    tum = [k for _, k in BOYLAR]
    eksik = {f: [k for k in tum if (f, k) not in canli] for f in FORMATLAR}
    if any(eksik.values()):
        h.append(f"poster boy sayisi {DIJITAL} {len(tum) - len(eksik[DIJITAL])}/{len(tum)}, {BASKI} {len(tum) - len(eksik[BASKI])}/{len(tum)} "
                 f"(eksik {DIJITAL} {eksik[DIJITAL][:4]}, {BASKI} {eksik[BASKI][:4]}); fiyat karsilastirmasi tam degil")
    if tanimsiz:
        h.append(f"poster tanimsiz boy etiketi {sorted(tanimsiz)[:3]} (BOYLAR disi; etiket degismis olabilir)")
    return {"canli": {f"{f} {k}": sorted(v) for (f, k), v in sorted(canli.items())}, "posterde_yok": eksik[BASKI],
            "posterde_yok_dijital": eksik[DIJITAL], "tanimsiz_etiket": sorted(tanimsiz)}, h


def hedefler(sp):
    out = {}
    for x in sp.get("shipping_profile_destinations") or []:
        cc = (x.get("destination_country_iso") or "").upper()
        rg = (x.get("destination_region") or "none").lower()
        out[cc or ("EVERYWHERE" if rg == "none" else rg.upper())] = x
    return out


def profil_plani(sp, kullanan, yd_ids):
    """-> PROFIL_PLAN (once tum hedefler, yazim listesi, kapilar)."""
    hd = hedefler(sp)
    yaz, h = [], []
    if "EVERYWHERE" not in hd:
        h.append("profilde 'her yer' (EVERYWHERE) hedefi yok: her ulkeye gonderim yok (hedef ekleme bu betikte yok, Serdar)")
    for k, d in sorted(hd.items()):
        if para(d.get("primary_cost")) != 0 or para(d.get("secondary_cost")) != 0:
            alan = {"destination_country_iso": d["destination_country_iso"]} if d.get("destination_country_iso") \
                else {"destination_region": d.get("destination_region") or "none"}
            yaz.append({"hedef": k, "destination_id": d.get("shipping_profile_destination_id"),
                        "once": {"primary_cost": para(d.get("primary_cost")), "secondary_cost": para(d.get("secondary_cost"))},
                        "govde": {"primary_cost": 0, "secondary_cost": 0, "min_delivery_days": d.get("min_delivery_days"),
                                  "max_delivery_days": d.get("max_delivery_days"), **alan}})
    disari = sorted({lid for lid, _ in kullanan} - set(yd_ids))
    if yaz and disari:
        h.append(f"profili YD 78 disinda {len(disari)} ilan kullaniyor ({disari[:5]}): ucret yazimi BLOK")
    return {"profil": sp.get("shipping_profile_id"), "baslik": sp.get("title"), "once_tum_hedefler": sp.get("shipping_profile_destinations") or [],
            "durum": "UCRETSIZ" if not yaz and not h else "BLOK" if h else "YAZILACAK", "yazim": yaz, "hata": h,
            "profili_kullanan": len(kullanan), "yd78_disi_kullanan": disari,
            "takip": {k: {"shipping_carrier_id": d.get("shipping_carrier_id"), "mail_class": d.get("mail_class"),
                          "teslim": [d.get("min_delivery_days"), d.get("max_delivery_days")]} for k, d in sorted(hd.items())},
            "takip_notu": "Etsy API'de 'takipli' alani yok; tasiyici / mail_class bilgi icin (dogrulanmadi, Serdar karari)"}


def kullananlar(api, shop, profil):
    kim = []
    for st in DURUMLAR:
        off = 0
        while True:
            d = api.get(f"/shops/{shop}/listings", params={"state": st, "limit": 100, "offset": off}) or {}
            r = d.get("results") or []
            kim += [(str(x.get("listing_id")), st) for x in r if int(x.get("shipping_profile_id") or 0) == int(profil or -1)]
            off += len(r)
            if len(r) < 100:
                break
    return kim


# ------------------------------------------------------------------ ana
def calistir(api, shop, a, out):
    K.salt_okur(api)
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(open(a.liste, encoding="utf-8-sig")) if (r.get("listing_id") or "").strip()]
    cift = {r["listing_id"].strip(): r["cift"].strip() for r in rows}
    sec = [x.strip() for x in (a.sadece or "").split(",") if x.strip()]
    if set(sec) - set(cift):
        print(f"::error::--sadece listede olmayan ilan {sorted(set(sec) - set(cift))[:5]}"); return 2
    ids = sorted(sec or list(cift), key=lambda x: (x != a.pilot, list(cift).index(x)))
    plan, md, tax, tid, boy_sab, kosu_h = [], [], None, None, None, []
    # poster referansi (fiyat merdiveni canli kapisi)
    pref, ph = poster_fiyat_kapisi(api.get(f"/listings/{a.poster_ref}/inventory") or {})
    kosu_h += ph
    profiller = {}
    for i, lid in enumerate(ids, 1):
        api.kota_kapisi(f"ilan {lid}")
        L = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        if tax is None:   # ilk ilanin taksonomisi (kosu basina 1 GET)
            tid = L.get("taxonomy_id")
            tax = (api.get(f"/seller-taxonomy/nodes/{tid}/properties", ok404=True) or {}).get("results") or []
            (out / "TAKSONOMI.json").write_text(json.dumps({"taxonomy_id": tid, "ozellikler": [
                {k: p.get(k) for k in ("property_id", "name", "display_name", "supports_variations", "is_multivalued", "scales")}
                | {"possible_values_say": len(p.get("possible_values") or [])} for p in tax]}, ensure_ascii=False, indent=1), encoding="utf-8")
            boy_sab, bh = boy_ozellik(tax, a.boy_pid, a.boy_scale_id)
            kosu_h += bh
        hata = list(kosu_h)
        if L.get("state") != "active":
            hata.append(f"state {L.get('state')} (active degil; taslak / pasif ilan atlanir)")
        if L.get("taxonomy_id") != tid:
            hata.append(f"taksonomi {L.get('taxonomy_id')} != {tid}")
        profiller.setdefault(L.get("shipping_profile_id"), []).append(lid)
        pid = (boy_sab or {}).get("property_id")
        zaten = bool(pid) and hedefte_mi(inv, pid)
        bag, bh = baglar(inv, vi)
        yuk = None
        if not zaten:
            yuk, eh = envanter_plani(inv, boy_sab); hata += eh
            hata += bh
        durum = "ZATEN" if zaten and not hata else "BLOK" if hata else "PLAN"
        kayit = {"listing_id": lid, "cift": cift[lid], "pilot": lid == a.pilot, "state": L.get("state"), "title": L.get("title"),
                 "taxonomy_id": L.get("taxonomy_id"), "shipping_profile_id": L.get("shipping_profile_id"), "boy_ozellik": boy_sab,
                 "envanter_ham_yedek": inv, "renk_bagi_ham": vi, "bag_ad": bag, "envanter_yuk": yuk,
                 "metin_celiski": metin_celiski(L.get("description")), "hata": hata, "durum": durum, "PASS": durum == "PLAN"}
        (out / f"KURU_{lid}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
        plan.append([lid, cift[lid], kayit["pilot"], L.get("state"), len(inv.get("products") or []), len((yuk or {}).get("products") or []),
                     len(bag), len(kayit["metin_celiski"]), durum, " | ".join(hata)])
        print(f"[{i}/{len(ids)}] {lid} {cift[lid]} {durum} istek {api.calls} kota {api.remaining}", flush=True)
    # kargo profili
    pkeys = sorted(profiller, key=str)
    pplan = {"durum": "BLOK", "hata": [f"ilanlar tek kargo profilinde degil: {pkeys}"], "profiller": {str(k): len(v) for k, v in profiller.items()}}
    if len(pkeys) == 1 and pkeys[0]:
        sp = api.get(f"/shops/{shop}/shipping-profiles/{pkeys[0]}") or {}
        sp.setdefault("shipping_profile_id", pkeys[0])
        pplan = profil_plani(sp, kullananlar(api, shop, pkeys[0]), list(cift))
    (out / "PROFIL_PLAN.json").write_text(json.dumps(pplan, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "cift", "pilot", "state", "urun_once", "urun_sonra", "stil_bagi", "metin_celiski", "sonuc", "hata"])
        w.writerows(plan)
    import yd_yapi_yaz as YZ   # istek tahmini tek kaynak (yazim betigi sayimi)
    n_plan = sum(1 for p in plan if p[8] == "PLAN")
    tahmin = {"kuru_istek_bu_kosu": api.calls, "kota_kalan": api.remaining, "kuru_ilan_basina": KOSU_OKUMA,
              "yazim": {"ilan_basina_tipik": YZ.ILAN_TIPIK, "ilan_basina_bag_onarimi": YZ.ILAN_BAG, "ilan_basina_en_kotu": YZ.ILAN_UST,
                        "ilan": n_plan, "toplam_tipik": YZ.ILAN_TIPIK * n_plan, "toplam_en_kotu": YZ.ILAN_UST * n_plan,
                        "profil": 2 + len(DURUMLAR) + len(pplan.get("yazim") or []),   # profil GET 2 + kullanan taramasi (en az 5) + PUT
                        "not": "kod sayimi (yd_yapi_yaz.py); 5xx / 429 tekrarlari ve token yenileme dahil degil; esik: kalan >= ILAN_UST + KOTA_SINIRI 10"}}
    (out / "ISTEK_TAHMINI.json").write_text(json.dumps(tahmin, ensure_ascii=False, indent=1), encoding="utf-8")
    say = {}
    for p in plan:
        say[p[8]] = say.get(p[8], 0) + 1
    md = ["# YD yeni ilan yapisi KURU KOSU (Etsy'ye yazma yok)", "",
          f"- ilan {len(plan)}: {say}; pilot {a.pilot}; boy ozelligi {boy_sab}",
          f"- fiyat: Digital File {DIJITAL_FIYAT} (her boy); Print " + ", ".join(f"{k} {v}" for k, v in PRINT_FIYAT.items()),
          f"- fiyat kaynagi: {FIYAT_KAYNAK}",
          f"- poster ref {a.poster_ref}: posterde olmayan Print boyu {pref['posterde_yok']}; fark {ph or 'yok'}",
          f"- kargo profili: {pplan.get('profil')} {pplan.get('durum')}; yazim {len(pplan.get('yazim') or [])} hedef; hata {pplan.get('hata')}",
          f"- takip: {pplan.get('takip_notu', '-')}",
          f"- istek: bu kosu {api.calls}, kota {api.remaining}; yazim tahmini ilan basina {YZ.ILAN_TIPIK} (en kotu {YZ.ILAN_UST}), "
          f"toplam {tahmin['yazim']['toplam_tipik']} (en kotu {tahmin['yazim']['toplam_en_kotu']})", ""]
    md += [f"- {p[0]} {p[1]}: {p[8]} {p[9]}" for p in plan if p[8] != "PLAN"]
    cel = sum(1 for p in plan if p[7])
    md += ["", f"- aciklamada eski format satiri olan ilan: {cel} (metin degismez; ayri is, Serdar)"]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:9]), flush=True)
    return 0 if say.get("BLOK", 0) == 0 and pplan.get("durum") != "BLOK" else 1


def argumanlar(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--liste", default=str(KOK.parents[1] / "data/pod/yd78_ids.csv"))
    ap.add_argument("--sadece", default="")
    ap.add_argument("--pilot", default="4595350971")
    ap.add_argument("--poster-ref", default="4570110121", help="wall art fiyat merdiveni canli kapisi (pod78 pilot)")
    ap.add_argument("--boy-pid", type=int, default=BOY_PID, help="Size ozelligi (varsayilan 516 Custom3, Serdar 31 Eki 5a; 0 = secilmedi, BLOK)")
    ap.add_argument("--boy-scale-id", type=int, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if not re.fullmatch(r"(\d+(,\d+)*)?", a.sadece) or not a.pilot.isdigit() or not a.poster_ref.isdigit():
        raise SystemExit("DUR: --sadece / --pilot / --poster-ref rakam olmali")
    return a


def main(argv=None):
    a = argumanlar(argv)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    return calistir(E.Etsy(store), os.environ["ETSY_SHOP_ID"], a, a.out)


if __name__ == "__main__":
    sys.exit(main())
