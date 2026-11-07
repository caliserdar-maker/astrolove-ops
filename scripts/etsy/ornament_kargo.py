#!/usr/bin/env python3
"""ORNAMENT KARGO + FIYAT (Serdar 7 Kas "Evet", KARARLAR_20261107 Karar 3). YAYIN YOK, PATCH YOK, DELETE YOK, Etsy Ads YOK.

Onayli yapi: urun 19.90 $ (5 stil); kargo ABD 9.90 $ (ek adet 0.90), Printful'un gonderdigi diger ulkeler 13.90 $ (ek adet 2.90);
profil ULKE ULKE (EU bolgesi ve "diger tum ulkeler" YOK). Printful kargo verisi: docs/ornament/kargo/KARGO_TUM_20261107.json
(koşu 42355236502, salt okuma; US 5.89/6.59, 126 ulke 9.89/11.88, 118 ulke gonderim yok).
updateListing (PATCH) taslagi yayina aldigi icin (ANA_1) aciklama ve shipping_profile_id bu betikte DEGISMEZ; yayin adiminda yapilir.

--mod oku   : SALT OKUMA. DURUM.json'daki taslaklar: state, 5 urun fiyati / sku / stok, shipping_profile_id, metinde "free shipping";
              magaza kargo profilleri. Cikti OUT/KARGO_OKU.json + .md
--mod profil: Magaza kaydi (ada gore idempotent): "Ornament Shipping" profili (cikis LV, hazirlik 3-5 is gunu) + ulke hedefleri.
              Ilan YAZMAZ. Hedef reddedilirse (Etsy ulkeyi tanimiyor) kaydedilir, atlanir; ABD reddi DUR. Cikti OUT/KARGO_PROFIL.json
--mod fiyat : --ciftler taslaklari: state "draft" degilse DUR; envanter PUT (yalniz fiyat 19.90; sku, stok, acik, hazirlik aynen);
              PUT sonrasi state ve fiyat geri okunur. state draft degilse DUR. Cikti OUT/KARGO_FIYAT.json
--mod kuru  : AG YOK, TOKEN YOK: fiyat yolu taklit Etsy ile (tum ciftler), istekler OUT/kuru/KURU_FIYAT.json
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
import ornament_taslak as OT  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KARGO_F = KOK / "docs" / "ornament" / "kargo" / "KARGO_TUM_20261107.json"
YENI_FIYAT = 19.90
PROFIL_AD = "Ornament Shipping"
ABD = ("US", 9.90, 0.90)                 # ulke, ilk adet, ek adet (Serdar 7 Kas)
DIGER = (13.90, 2.90)
PF_ABD, PF_DIGER = 5.89, 9.89            # Printful 1 adet kargo (KARGO_TUM); bu ucretten farkli ulke profile GIRMEZ (Serdar'a sorulur)
KOTA_MIN = 10
FREE = re.compile(r"free\s+shipping|ships?\s+free|free\s+delivery", re.I)


def durum_oku(out):
    f = out / "DURUM.json"
    if not f.exists():
        raise SystemExit("DUR: DURUM.json yok (ornament-taslak ciktisi)")
    D = json.load(open(f))
    lids = {c: l for c, l in (D.get("ciftler") or {}).items() if str(l).isdigit()}
    eksik = [c for c in OT.CIFTLER if c not in lids or c not in (D.get("tamam") or [])]
    if eksik:
        raise SystemExit(f"DUR: DURUM'da tamam olmayan cift {eksik[:5]} ({len(eksik)})")
    return lids


def hedef_listesi():
    """KARGO_TUM'dan profil hedefleri: [(iso, ilk, ek, min_gun, max_gun)], disarida kalanlar."""
    R = json.load(open(KARGO_F))
    hedef, disari = [], []
    for s in R["satir"]:
        cc, u1, u2 = s.get("ulke"), s.get("ucret_1"), s.get("ucret_2")
        if not u1:
            continue
        u1, u2 = float(u1), float(u2) if u2 else None
        g = s.get("gun_1") or [None, None]
        if cc == "US":
            if u1 != PF_ABD:
                raise SystemExit(f"DUR: ABD Printful kargo {u1} != {PF_ABD} (veri degisti, Serdar'a sor)")
            hedef.append((cc, ABD[1], ABD[2], g[0], g[1]))
        elif u1 == PF_DIGER:
            hedef.append((cc, DIGER[0], DIGER[1], g[0], g[1]))
        else:
            disari.append((cc, u1, u2))
    if not any(h[0] == "US" for h in hedef):
        raise SystemExit("DUR: veride ABD yok")
    return hedef, disari


class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = super()._call(method, path, **kw)
        kota(self)
        return r

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


class ProfilIzin(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            ok = [("POST", r"^/shops/\d+/shipping-profiles$"), ("POST", r"^/shops/\d+/shipping-profiles/\d+/destinations$")]
            if not any(m == method and re.match(p, path) for m, p in ok):
                raise SystemExit(f"YASAK (profil): {method} {path}")
        r = super()._call(method, path, **kw)
        kota(self)
        return r

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


class FiyatIzin(Etsy):
    """Yalniz izinli taslaklarin envanter PUT'u. PATCH / DELETE / POST yok."""
    izinli = frozenset()

    def _call(self, method, path, **kw):
        if method != "GET":
            m = re.match(r"^/listings/(\d+)/inventory$", path)
            if not (method == "PUT" and m and m.group(1) in self.izinli):
                raise SystemExit(f"YASAK (fiyat): {method} {path}")
        r = super()._call(method, path, **kw)
        kota(self)
        return r

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")


def kota(api, esik=KOTA_MIN):
    if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < esik:
        raise SystemExit(f"DUR: kota {api.remaining} < {esik}")


def urun_ozet(inv):
    out = []
    for p in inv.get("products") or []:
        o = (p.get("offerings") or [{}])[0]
        stil = [v for pv in p.get("property_values") or [] for v in (pv.get("values") or [])]
        out.append(dict(sku=p.get("sku"), stil=stil, fiyat=OT.para(o.get("price")), stok=o.get("quantity"),
                        acik=o.get("is_enabled"), hazirlik=o.get("readiness_state_id")))
    return out


def oku(api, shop, out, lids):
    R = dict(kota_bas=None, ilan={}, profiller=[])
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    R["profiller"] = [OT.profil_ozet(x) for x in sps]
    for c, lid in sorted(lids.items()):
        L = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}     # getListing includes "inventory" kabul etmiyor (kosu 42356001503: 400)
        metin = " ".join([L.get("title") or "", L.get("description") or "", " ".join(L.get("tags") or [])])
        R["ilan"][c] = dict(lid=lid, state=L.get("state"), profil=L.get("shipping_profile_id"), urun=urun_ozet(inv),
                            free_shipping=[m.group(0) for m in FREE.finditer(metin)])
    R["kota_son"] = api.remaining
    json.dump(R, open(out / "KARGO_OKU.json", "w"), indent=1, ensure_ascii=False, default=str)
    st = {}
    for v in R["ilan"].values():
        st[v["state"]] = st.get(v["state"], 0) + 1
    fiyatlar = sorted({u["fiyat"] for v in R["ilan"].values() for u in v["urun"]}, key=str)
    md = [f"# KARGO OKU | kota {R['kota_bas']} -> {R['kota_son']} | ilan {len(R['ilan'])}", f"state {st}", f"fiyatlar {fiyatlar}",
          f"free shipping gecen ilan {sum(1 for v in R['ilan'].values() if v['free_shipping'])}",
          f"profil (ilan) {sorted({str(v['profil']) for v in R['ilan'].values()})}", f"profiller {R['profiller']}"]
    (out / "KARGO_OKU.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return R


def profil(api, shop, out):
    hedef, disari = hedef_listesi()
    R = dict(olaylar=[], reddedilen=[], disari_printful_ucret_farkli=disari, hedef_sayisi=len(hedef))
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    var = [x for x in sps if x.get("title") == PROFIL_AD]
    if len(var) > 1:
        raise SystemExit(f"DUR: ayni adla {len(var)} profil")
    if var:
        pid = var[0]["shipping_profile_id"]; R["olaylar"].append(f"profil var {pid}")
    else:
        us = next(h for h in hedef if h[0] == "US")
        body = {"title": PROFIL_AD, "origin_country_iso": "LV", "origin_postal_code": os.environ.get("LV_POSTA", "LV-1004"),
                "primary_cost": us[1], "secondary_cost": us[2], "min_processing_time": OT.HAZIRLIK[0], "max_processing_time": OT.HAZIRLIK[1],
                "processing_time_unit": "business_days", "destination_country_iso": "US",
                "min_delivery_days": us[3], "max_delivery_days": us[4]}
        try:
            x = api.post(f"/shops/{shop}/shipping-profiles", body) or {}
        except SystemExit as e:
            raise SystemExit(f"DUR: profil olusturma: {str(e)[:300]}")
        pid = x.get("shipping_profile_id")
        if not pid:
            raise SystemExit(f"DUR: profil olusmadi {str(x)[:300]}")
        R["olaylar"].append(f"profil olusturuldu {pid}")
    R["shipping_profile_id"] = pid

    def mevcut():
        prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
        return {(d.get("destination_country_iso") or (d.get("destination_region") or "none")).upper(): d
                for d in prof.get("shipping_profile_destinations") or []}
    have = mevcut()
    for cc, ilk, ek, a, b in hedef:
        if cc in have:
            continue
        body = {"destination_country_iso": cc, "primary_cost": ilk, "secondary_cost": ek, "min_delivery_days": a, "max_delivery_days": b}
        try:
            api.post(f"/shops/{shop}/shipping-profiles/{pid}/destinations", body)
            R["olaylar"].append(f"hedef {cc}")
        except SystemExit as e:
            if cc == "US":
                raise
            R["reddedilen"].append((cc, str(e)[:200]))
        time.sleep(0.25)
    have = mevcut()
    yanlis = []
    beklenen = {h[0]: h for h in hedef}
    for k, d in have.items():
        h = beklenen.get(k)
        if not h:
            yanlis.append((k, "beklenmeyen hedef (EU / EVERYWHERE / fazla)"))
            continue
        if (OT.para(d.get("primary_cost")), OT.para(d.get("secondary_cost"))) != (h[1], h[2]):
            yanlis.append((k, f"ucret {OT.para(d.get('primary_cost'))}/{OT.para(d.get('secondary_cost'))} != {h[1]}/{h[2]}"))
    R["profil"] = OT.profil_ozet(api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {})
    R["yanlis"] = yanlis
    R["kontrol"] = dict(hedef_beklenen=len(hedef), profilde=len(have), reddedilen=len(R["reddedilen"]))
    json.dump(R, open(out / "KARGO_PROFIL.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(R["kontrol"]), "reddedilen", R["reddedilen"], "yanlis", yanlis)
    if yanlis:
        raise SystemExit(f"DUR: profilde yanlis hedef {yanlis[:5]}")
    if len(have) + len(R["reddedilen"]) != len(hedef):
        raise SystemExit(f"DUR: hedef sayisi tutmuyor {R['kontrol']}")
    return R


def fiyat_tek(api, pair, lid):
    """Tek taslak: draft kontrol, envanter PUT (yalniz fiyat), geri okuma. -> dict"""
    L = api.get(f"/listings/{lid}") or {}
    if L.get("state") != "draft":
        raise SystemExit(f"DUR: {pair} {lid} state {L.get('state')} (draft degil)")
    inv = api.get(f"/listings/{lid}/inventory") or {}
    prods = inv.get("products") or []
    if len(prods) != len(OT.STILLER):
        raise SystemExit(f"DUR: {pair} urun sayisi {len(prods)} != {len(OT.STILLER)}")
    once = urun_ozet(inv)
    beklenen_sku = {OT.sku(pair, kd) for _, kd, _, _ in OT.STILLER}
    if {u["sku"] for u in once} != beklenen_sku:
        raise SystemExit(f"DUR: {pair} sku farkli {sorted(u['sku'] for u in once)}")
    if all(u["fiyat"] == YENI_FIYAT for u in once):
        return dict(cift=pair, lid=lid, sonuc="ZATEN", once=once)
    yeni = []
    for p in prods:
        o = (p.get("offerings") or [{}])[0]
        pv = [dict(property_id=v.get("property_id"), property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                   values=v.get("values")) for v in p.get("property_values") or []]
        yeni.append(dict(sku=p.get("sku"), property_values=pv,
                         offerings=[dict(price=YENI_FIYAT, quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                         readiness_state_id=o.get("readiness_state_id"))]))
    govde = dict(products=yeni, price_on_property=inv.get("price_on_property") or [],
                 quantity_on_property=inv.get("quantity_on_property") or [], sku_on_property=inv.get("sku_on_property") or [],
                 readiness_state_on_property=inv.get("readiness_state_on_property") or [])
    api.put_json(f"/listings/{lid}/inventory", govde)
    L2 = api.get(f"/listings/{lid}") or {}
    sonra = urun_ozet(api.get(f"/listings/{lid}/inventory") or {})
    hatalar = []
    if L2.get("state") != "draft":
        hatalar.append(f"state {L2.get('state')}")
    if sorted((u["sku"], u["fiyat"], u["stok"], u["acik"], u["hazirlik"], tuple(u["stil"])) for u in sonra) != \
            sorted((u["sku"], YENI_FIYAT, u["stok"], u["acik"], u["hazirlik"], tuple(u["stil"])) for u in once):
        hatalar.append("envanter geri okuma farkli")
    if hatalar:
        raise SystemExit(f"DUR: {pair} {lid} PUT sonrasi: {hatalar} | sonra {sonra}")
    return dict(cift=pair, lid=lid, sonuc="PASS", once=once, sonra=sonra)


def fiyat(api, out, lids, ciftler):
    api.izinli = frozenset(str(lids[c]) for c in ciftler)
    R = dict(sonuc=[], kota_bas=None)
    t0 = time.time()
    for i, c in enumerate(ciftler, 1):
        kota(api, KOTA_MIN + 6)       # ilan basina en fazla 5 istek + taban: ilan yarim kalmaz
        try:
            R["sonuc"].append(fiyat_tek(api, c, lids[c]))
        finally:
            json.dump(R, open(out / "KARGO_FIYAT.json", "w"), indent=1, ensure_ascii=False, default=str)
        g = time.time() - t0
        print(f"fiyat [{i}/{len(ciftler)}] {c} {R['sonuc'][-1]['sonuc']} | gecen {g:.0f} sn | kalan ~{g / i * (len(ciftler) - i):.0f} sn | "
              f"%{100 * i // len(ciftler)} | kota {api.remaining}", flush=True)
    say = {}
    for s in R["sonuc"]:
        say[s["sonuc"]] = say.get(s["sonuc"], 0) + 1
    R["ozet"] = say
    json.dump(R, open(out / "KARGO_FIYAT.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(f"::warning::FIYAT {say} | kota {api.remaining}")
    return R


class KuruEtsy(FiyatIzin):
    """Ag yok: taslak durumunu bellekte taklit eder, fiyat yolunu ayni kodla kosar."""
    def __init__(self, lids):  # noqa: D401
        self.remaining, self.calls, self.istek = "5000", 0, []
        self.db = {}
        for c, lid in lids.items():
            self.db[str(lid)] = dict(state="draft", inv=dict(products=[dict(
                sku=OT.sku(c, kd), property_values=[dict(property_id=OT.P_STYLE, property_name="Style", value_ids=[1000 + n], values=[ad])],
                offerings=[dict(price=dict(amount=2990, divisor=100), quantity=OT.STOK, is_enabled=True, readiness_state_id=111)])
                for n, (ad, kd, _, _) in enumerate(OT.STILLER)], price_on_property=[], quantity_on_property=[],
                sku_on_property=[OT.P_STYLE], readiness_state_on_property=[]))

    def _call(self, method, path, **kw):
        if method != "GET":
            m = re.match(r"^/listings/(\d+)/inventory$", path)
            if not (method == "PUT" and m and m.group(1) in self.izinli):
                raise SystemExit(f"YASAK (fiyat): {method} {path}")
        self.calls += 1
        self.istek.append((method, path, kw.get("json_body")))
        m = re.match(r"^/listings/(\d+)(/inventory)?$", path)
        d = self.db[m.group(1)]
        if method == "GET":
            return {"state": d["state"]} if not m.group(2) else json.loads(json.dumps(d["inv"]))
        body = kw.get("json_body")
        for p in body["products"]:
            o = p["offerings"][0]
            o["price"] = dict(amount=round(o["price"] * 100), divisor=100)
        d["inv"] = body
        return {}

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params=params)

    def put_json(self, path, body):
        return self._call("PUT", path, json_body=json.loads(json.dumps(body)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "profil", "fiyat", "kuru"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    if a.mod == "kuru":
        lids = {c: str(4600000000 + i) for i, c in enumerate(OT.CIFTLER)}
        api = KuruEtsy(lids)
        (out / "kuru").mkdir(exist_ok=True)
        R = fiyat(api, out / "kuru", lids, OT.cift_listesi("TUMU"))
        json.dump(api.istek, open(out / "kuru" / "KURU_FIYAT.json", "w"), indent=1, default=str)
        hedef, disari = hedef_listesi()
        print(f"KURU fiyat {R['ozet']} | istek {api.calls} | profil hedef {len(hedef)} disari {len(disari)}")
        return
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "profil":
        profil(ProfilIzin(store), shop, out); return
    lids = durum_oku(out)
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out, lids); return
    fiyat(FiyatIzin(store), out, lids, OT.cift_listesi(a.ciftler))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
