#!/usr/bin/env python3
"""ORNAMENT KARGO + FIYAT (Serdar 7 Kas "Evet", KARARLAR_20261107 Karar 3). YAYIN YOK, PATCH YOK, DELETE YOK, Etsy Ads YOK.

Onayli yapi: urun 19.90 $ (5 stil); kargo ABD 9.90 $ (ek adet 0.90), Printful'un 9.89 $ ile gonderdigi diger ulkeler 13.90 $
(ek adet 2.90); profil ULKE ULKE (EU bolgesi ve "diger tum ulkeler" YOK). Printful kargo verisi: docs/ornament/kargo/KARGO_TUM_20261107.json
(kosu 42355236502, salt okuma; US 5.89/6.59, 126 ulke 9.89/11.88, 118 ulke gonderim yok).
updateListing (PATCH) taslagi yayina aldigi icin (CLAUDE.md, ANA_1) aciklama ve shipping_profile_id bu betikte DEGISMEZ; yayin adiminda.
UYARI: fiyat adimindan sonra taslaklar 19.90 + eski ucretsiz profilde kalir; yayin kapisi "shipping_profile_id == Ornament Shipping" olmali.

--mod oku       : SALT OKUMA (yedek). DURUM.json'daki taslaklar: state, ham envanter, shipping_profile_id, metinde "free shipping";
                  magaza profilleri. Cikti OUT/KARGO_OKU.json + .md
--mod profil_kuru: SALT OKUMA. Profil plani: mevcut profil / hedefler okunur, gonderilecek tum POST govdeleri OUT/KARGO_PROFIL_PLAN.json
--mod profil    : "Ornament Shipping" profili (cikis LV, hazirlik 3-5 is gunu) + ulke hedefleri. Ilan YAZMAZ. Her POST TEK gonderim
                  (5xx / kopmada yeniden gonderilmez; geri okunur). Yalniz HTTP 400 + beklenen ret listesi (Etsy'nin tanimadigi bolgeler)
                  atlanir; baska her hata DUR. Kota butcesi yazimdan ONCE. Cikti OUT/KARGO_PROFIL.json (finally)
--mod fiyat_kuru: SALT OKUMA. Gercek envanter okunur, PUT govdesi kurulur, OUT/fiyat_kuru/<CIFT>.json; PUT YOK.
--mod fiyat     : --ciftler taslaklari: state "draft" degilse DUR; envanter PUT (yalniz fiyat 19.90); once/sonra dosyaya; PUT sonrasi
                  state + envanter + *_on_property geri okunur. TUMU icin PILOT_CIFT zorunlu ve once onun 19.90 oldugu dogrulanir.
--mod kuru      : AG YOK: fiyat + profil yollari taklit ag ile (gercek izin siniflarindan gecerek).
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402
import ornament_taslak as OT  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
KARGO_F = KOK / "docs" / "ornament" / "kargo" / "KARGO_TUM_20261107.json"
YENI_FIYAT = 19.90
PROFIL_AD = "Ornament Shipping"
ABD = ("US", 9.90, 0.90)                 # ulke, ilk adet, ek adet (Serdar 7 Kas)
DIGER = (13.90, 2.90)
PF_ABD, PF_DIGER = 5.89, 9.89            # Printful 1 adet kargo; farkli ucretli ulke profile GIRMEZ (Serdar'a sorulur)
CIKIS = ("LV", "LV-1004")
KOTA_MIN = 10
ILAN_ISTEK = 5                           # fiyat: GET listing, GET inv, PUT, GET listing, GET inv
RET_IZINLI = {"BV", "HM", "TF", "UM", "CC", "CX", "NF", "SJ", "TK", "XK"}   # Etsy'nin tanimayabilecegi bolgeler (400 ise atlanir)
FREE = re.compile(r"free\s+shipping|ships?\s+free|free\s+delivery", re.I)


def durum_oku(out):
    f = out / "DURUM.json"
    if not f.exists():
        raise SystemExit("DUR: DURUM.json yok (ornament-taslak ciktisi)")
    D = json.load(open(f))
    lids = {c: str(l) for c, l in (D.get("ciftler") or {}).items() if str(l).isdigit()}
    eksik = [c for c in OT.CIFTLER if c not in lids or c not in (D.get("tamam") or [])]
    if eksik:
        raise SystemExit(f"DUR: DURUM'da tamam olmayan cift {eksik[:5]} ({len(eksik)})")
    return lids


def hedef_listesi():
    """KARGO_TUM'dan profil hedefleri: [(iso, ilk, ek, min_gun, max_gun)], disarida kalanlar (Printful ucreti farkli)."""
    R = json.load(open(KARGO_F))
    hedef, disari = [], []
    for s in R["satir"]:
        cc, u1, u2 = s.get("ulke"), s.get("ucret_1"), s.get("ucret_2")
        if not u1:
            continue
        u1 = float(u1)
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
    for h in hedef:
        if not (h[3] and h[4] and 1 <= h[3] <= h[4] <= 45):
            raise SystemExit(f"DUR: teslim gunu gecersiz {h}")
    return hedef, disari


def kota(api, esik=KOTA_MIN):
    if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < esik:
        raise SystemExit(f"DUR: kota {api.remaining} < {esik}")


class Ag(Etsy):
    """Ag katmani tek yerde (_ag, _tek): testler yalniz bunu taklit eder; izin kontrolleri gercek siniflardan gecer."""
    def _ag(self, method, path, **kw):
        return Etsy._call(self, method, path, **kw)

    def _tek(self, path, body):
        """TEK gonderim POST (form). -> (kod, json|None, metin). kod 'BELIRSIZ': istek gitti mi bilinmiyor."""
        self._istek_oncesi()
        sira = self._bekle()
        try:
            r = requests.post(API + path, data=body, headers=self._headers(), timeout=90)
        except requests.RequestException as e:
            return "BELIRSIZ", None, f"{type(e).__name__}: {str(e)[:200]}"
        self._kalan_yaz(r.headers.get("x-remaining-today"), sira)
        try:
            js = r.json() if r.status_code in (200, 201) else None
        except ValueError:
            return "BELIRSIZ", None, f"{r.status_code} json okunamadi"
        return r.status_code, js, r.text[:300]

    def post_file(self, *a, **k):
        raise SystemExit("YASAK: POST file")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE")


class SaltOkur(Ag):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        r = self._ag(method, path, **kw)
        kota(self)
        return r

    def tek_post(self, path, body):
        raise SystemExit(f"YASAK (salt okuma): POST {path}")


class ProfilIzin(Ag):
    IZIN = (r"^/shops/\d+/shipping-profiles$", r"^/shops/\d+/shipping-profiles/\d+/destinations$")

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (profil): {method} {path} (yazim yalniz tek_post)")
        return self._ag(method, path, **kw)

    def tek_post(self, path, body):
        if not any(re.match(p, path) for p in self.IZIN):
            raise SystemExit(f"YASAK (profil): POST {path}")
        kota(self)                          # yazimdan ONCE (sert taban)
        return self._tek(path, body)


class FiyatIzin(Ag):
    """Yalniz izinli taslaklarin envanter PUT'u. PATCH / DELETE / POST yok. Kota butcesi cagiranda (ilan basinda)."""
    izinli = frozenset()

    def _call(self, method, path, **kw):
        if method != "GET":
            m = re.match(r"^/listings/(\d+)/inventory$", path)
            if not (method == "PUT" and m and m.group(1) in self.izinli):
                raise SystemExit(f"YASAK (fiyat): {method} {path}")
        return self._ag(method, path, **kw)

    def tek_post(self, path, body):
        raise SystemExit(f"YASAK (fiyat): POST {path}")


def magaza_kapisi(api, shop):
    S = api.get(f"/shops/{shop}") or {}
    if (S.get("currency_code") or "").upper() != "USD":
        raise SystemExit(f"DUR: magaza para birimi {S.get('currency_code')} (USD degil; kargo/fiyat USD)")
    return S


def urun_ozet(inv):
    out = []
    for p in inv.get("products") or []:
        o = (p.get("offerings") or [{}])[0]
        stil = [v for pv in p.get("property_values") or [] for v in (pv.get("values") or [])]
        out.append(dict(sku=p.get("sku"), stil=stil, fiyat=OT.para(o.get("price")), stok=o.get("quantity"),
                        acik=o.get("is_enabled"), hazirlik=o.get("readiness_state_id")))
    return out


def on_property(inv):
    return {k: sorted(inv.get(k) or []) for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property")}


def oku(api, shop, out, lids):
    R = dict(ilan={}, profiller=[])
    magaza_kapisi(api, shop)
    R["kota_bas"] = api.remaining
    sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    R["profiller"] = [OT.profil_ozet(x) for x in sps]
    for c, lid in sorted(lids.items()):
        L = api.get(f"/listings/{lid}") or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}     # getListing includes "inventory" kabul etmiyor (kosu 42356001503: 400)
        metin = " ".join([L.get("title") or "", L.get("description") or "", " ".join(L.get("tags") or [])])
        R["ilan"][c] = dict(lid=lid, state=L.get("state"), profil=L.get("shipping_profile_id"), urun=urun_ozet(inv), ham_envanter=inv,
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


def _hedef_haritasi(prof):
    """Profil hedefleri -> {ulke: hedef}; ayni ulke iki kez ya da ulke disi (bolge / everywhere) hedef -> DUR listesi."""
    harita, sorun = {}, []
    for d in prof.get("shipping_profile_destinations") or []:
        cc = (d.get("destination_country_iso") or "").upper()
        if not cc:
            sorun.append(f"ulke disi hedef ({d.get('destination_region')})"); continue
        if cc in harita:
            sorun.append(f"kopya hedef {cc}"); continue
        harita[cc] = d
    return harita, sorun


def _profil_dogrula(sp):
    """Var olan 'Ornament Shipping' profili onayli yapida mi (cikis, hazirlik)."""
    s = []
    if (sp.get("origin_country_iso") or "").upper() != CIKIS[0]:
        s.append(f"cikis ulkesi {sp.get('origin_country_iso')}")
    if (sp.get("min_processing_days"), sp.get("max_processing_days")) not in ((None, None), OT.HAZIRLIK):
        s.append(f"hazirlik {sp.get('min_processing_days')}-{sp.get('max_processing_days')}")
    return s


def profil(api, shop, out, kuru=False):
    hedef, disari = hedef_listesi()
    beklenen = {h[0]: h for h in hedef}
    R = dict(olaylar=[], reddedilen=[], disari_printful_ucret_farkli=disari, hedef_sayisi=len(hedef), kuru=kuru, plan=[])
    try:
        magaza_kapisi(api, shop)
        sps = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
        var = [x for x in sps if x.get("title") == PROFIL_AD]
        if len(var) > 1:
            raise SystemExit(f"DUR: ayni adla {len(var)} profil (elle temizlik gerekir)")
        pid, have = None, {}
        if var:
            pid = var[0]["shipping_profile_id"]; R["olaylar"].append(f"profil var {pid}")
            s = _profil_dogrula(var[0])
            prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
            have, s2 = _hedef_haritasi(prof)
            if s or s2:
                raise SystemExit(f"DUR: var olan profil onayli yapida degil: {s + s2}")
        eksik = [h for h in hedef if h[0] not in have]
        butce = len(eksik) + (0 if pid else 1) + 4 + KOTA_MIN + 5     # yazimlar + geri okumalar + taban + pay
        R["butce"] = dict(gerekli=butce, kalan=api.remaining, eksik_hedef=len(eksik))
        if not kuru and api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < butce:
            raise SystemExit(f"DUR: kota {api.remaining} < profil butcesi {butce} (hic yazilmadi)")
        if not pid:
            us = beklenen["US"]
            body = {"title": PROFIL_AD, "origin_country_iso": CIKIS[0], "origin_postal_code": CIKIS[1],
                    "primary_cost": us[1], "secondary_cost": us[2], "min_processing_time": OT.HAZIRLIK[0],
                    "max_processing_time": OT.HAZIRLIK[1], "processing_time_unit": "business_days", "destination_country_iso": "US",
                    "min_delivery_days": us[3], "max_delivery_days": us[4]}
            R["plan"].append(("profil", body))
            if kuru:
                pid, have = "KURU", {"US": {}}          # profil olusturma ABD hedefini de kurar
            else:
                kod, js, metin = api.tek_post(f"/shops/{shop}/shipping-profiles", body)
                if kod not in (200, 201) or not (js or {}).get("shipping_profile_id"):
                    sps2 = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
                    v2 = [x for x in sps2 if x.get("title") == PROFIL_AD]
                    raise SystemExit(f"DUR: profil olusturma {kod} {metin[:200]} | geri okuma ayni adla {len(v2)} profil "
                                     f"(1 ise yeniden kosu devam eder)")
                pid = js["shipping_profile_id"]; R["olaylar"].append(f"profil olusturuldu {pid}")
                prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
                have, s2 = _hedef_haritasi(prof)
                if s2:
                    raise SystemExit(f"DUR: yeni profil hedefleri {s2}")
        R["shipping_profile_id"] = pid
        t0 = time.time()
        eksik = [h for h in hedef if h[0] not in have]
        for i, (cc, ilk, ek, a, b) in enumerate(eksik, 1):
            body = {"destination_country_iso": cc, "primary_cost": ilk, "secondary_cost": ek, "min_delivery_days": a, "max_delivery_days": b}
            R["plan"].append(("hedef", body))
            if kuru:
                continue
            kod, js, metin = api.tek_post(f"/shops/{shop}/shipping-profiles/{pid}/destinations", body)
            if kod in (200, 201):
                R["olaylar"].append(f"hedef {cc}")
            elif kod == 400 and cc in RET_IZINLI:
                R["reddedilen"].append((cc, metin[:200]))
            else:
                raise SystemExit(f"DUR: hedef {cc} -> {kod} {metin[:200]} (yeniden kosu geri okuyup devam eder)")
            if i % 20 == 0 or i == len(eksik):
                g = time.time() - t0
                print(f"hedef [{i}/{len(eksik)}] | gecen {g:.0f} sn | kalan ~{g / i * (len(eksik) - i):.0f} sn | %{100 * i // len(eksik)} | "
                      f"kota {api.remaining}", flush=True)
        if kuru:
            R["kontrol"] = dict(plan_istek=len(R["plan"]), hedef=len(hedef))
            return R
        prof = api.get(f"/shops/{shop}/shipping-profiles/{pid}") or {}
        have, sorun = _hedef_haritasi(prof)
        yanlis = list(sorun) + _profil_dogrula(prof)
        for k, d in have.items():
            h = beklenen.get(k)
            if not h:
                yanlis.append(f"{k}: beklenmeyen hedef"); continue
            gercek = (OT.para(d.get("primary_cost")), OT.para(d.get("secondary_cost")), d.get("min_delivery_days"), d.get("max_delivery_days"))
            if gercek != h[1:]:
                yanlis.append(f"{k}: {gercek} != {h[1:]}")
        ret = {c for c, _ in R["reddedilen"]}
        eksik_son = sorted(set(beklenen) - set(have) - ret)
        if eksik_son:
            yanlis.append(f"eksik hedef {eksik_son[:10]} ({len(eksik_son)})")
        R["profil"] = OT.profil_ozet(prof)
        R["yanlis"] = yanlis
        R["kontrol"] = dict(hedef_beklenen=len(hedef), profilde=len(have), reddedilen=len(ret))
        print(json.dumps(R["kontrol"]), "reddedilen", R["reddedilen"], "yanlis", yanlis[:10])
        if yanlis:
            raise SystemExit(f"DUR: profil kontrolu {yanlis[:5]}")
        return R
    finally:
        ad = "KARGO_PROFIL_PLAN.json" if kuru else "KARGO_PROFIL.json"
        json.dump(R, open(out / ad, "w"), indent=1, ensure_ascii=False, default=str)


def put_govdesi(inv):
    yeni = []
    for p in inv.get("products") or []:
        o = (p.get("offerings") or [{}])[0]
        pv = [dict(property_id=v.get("property_id"), property_name=v.get("property_name"), value_ids=v.get("value_ids"),
                   values=v.get("values")) for v in p.get("property_values") or []]
        yeni.append(dict(sku=p.get("sku"), property_values=pv,
                         offerings=[dict(price=YENI_FIYAT, quantity=o.get("quantity"), is_enabled=o.get("is_enabled"),
                                         readiness_state_id=o.get("readiness_state_id"))]))
    return dict(products=yeni, **{k: list(inv.get(k) or []) for k in ("price_on_property", "quantity_on_property", "sku_on_property",
                                                                       "readiness_state_on_property")})


def fiyat_tek(api, pair, lid, out, kuru=False):
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
    govde = put_govdesi(inv)
    d = out / ("fiyat_kuru" if kuru else "fiyat_once")
    d.mkdir(exist_ok=True)
    json.dump(dict(cift=pair, lid=lid, ham_envanter=inv, put=govde), open(d / f"{pair}.json", "w"), indent=1, ensure_ascii=False)
    if kuru:
        return dict(cift=pair, lid=lid, sonuc="KURU", once=once)
    api.put_json(f"/listings/{lid}/inventory", govde)
    L2 = api.get(f"/listings/{lid}") or {}
    inv2 = api.get(f"/listings/{lid}/inventory") or {}
    sonra = urun_ozet(inv2)
    hatalar = []
    if L2.get("state") != "draft":
        hatalar.append(f"state {L2.get('state')} (ACIL: panelden ilan {lid} inactive yapilmali)")
    if sorted((u["sku"], u["fiyat"], u["stok"], u["acik"], u["hazirlik"], tuple(u["stil"])) for u in sonra) != \
            sorted((u["sku"], YENI_FIYAT, u["stok"], u["acik"], u["hazirlik"], tuple(u["stil"])) for u in once):
        hatalar.append("envanter geri okuma farkli")
    if on_property(inv2) != on_property(inv):
        hatalar.append(f"on_property farkli {on_property(inv)} -> {on_property(inv2)}")
    if hatalar:
        raise SystemExit(f"DUR: {pair} {lid} PUT sonrasi: {hatalar} | sonra {sonra}")
    return dict(cift=pair, lid=lid, sonuc="PASS", once=once, sonra=sonra)


def fiyat(api, shop, out, lids, ciftler, kuru=False, pilot=None):
    hepsi = len(ciftler) > 1
    if hepsi and not kuru:
        if not pilot or pilot not in lids:
            raise SystemExit("DUR: birden fazla cift icin PILOT_CIFT gerekli (pilot once yazilir, Serdar bakar)")
        ciftler = [pilot] + [c for c in ciftler if c != pilot]
    api.izinli = frozenset(str(lids[c]) for c in ciftler)
    magaza_kapisi(api, shop)
    R = dict(sonuc=[], kota_bas=api.remaining, uyari="Taslaklar eski ucretsiz profilde; yayin kapisi: shipping_profile_id == Ornament Shipping")
    t0 = time.time()
    try:
        for i, c in enumerate(ciftler, 1):
            kota(api, KOTA_MIN + ILAN_ISTEK + 1)       # ilan butcesi yazimdan ONCE: ilan yarim kalmaz
            s = fiyat_tek(api, c, lids[c], out, kuru=kuru)
            if hepsi and not kuru and i == 1 and s["sonuc"] != "ZATEN":
                raise SystemExit(f"DUR: pilot {c} once 19.90 olmali (sonuc {s['sonuc']}; pilot ayri kosuda yazilir ve Serdar bakar)")
            R["sonuc"].append(s)
            g = time.time() - t0
            print(f"fiyat [{i}/{len(ciftler)}] {c} {s['sonuc']} | gecen {g:.0f} sn | kalan ~{g / i * (len(ciftler) - i):.0f} sn | "
                  f"%{100 * i // len(ciftler)} | kota {api.remaining}", flush=True)
    finally:
        say = {}
        for s in R["sonuc"]:
            say[s["sonuc"]] = say.get(s["sonuc"], 0) + 1
        R["ozet"] = say
        R["kota_son"] = api.remaining
        json.dump(R, open(out / ("KARGO_FIYAT_KURU.json" if kuru else "KARGO_FIYAT.json"), "w"), indent=1, ensure_ascii=False, default=str)
    print(f"::warning::FIYAT {say} | kota {api.remaining} | {R['uyari']}")
    return R


class KuruAg:
    """Yalniz ag katmani taklidi (_ag, _tek); izin kontrolleri gercek siniflardan (FiyatIzin / ProfilIzin) gecer."""
    def kuru_kur(self, lids):
        self.remaining, self.calls, self.istek, self._kapi_bakildi = "5000", 0, [], False
        self.sert_taban = None
        self.db, self.profiller, self.ret = {}, {}, {}
        for c, lid in lids.items():
            self.db[str(lid)] = dict(state="draft", inv=dict(products=[dict(
                sku=OT.sku(c, kd), property_values=[dict(property_id=OT.P_STYLE, property_name="Style", value_ids=[1000 + n], values=[ad])],
                offerings=[dict(price=dict(amount=2990, divisor=100), quantity=OT.STOK, is_enabled=True, readiness_state_id=111)])
                for n, (ad, kd, _, _) in enumerate(OT.STILLER)], price_on_property=[], quantity_on_property=[],
                sku_on_property=[OT.P_STYLE], readiness_state_on_property=[]))
        return self

    def _ag(self, method, path, **kw):
        self.calls += 1
        self.remaining = str(int(self.remaining) - 1)
        self.istek.append((method, path, kw.get("json_body")))
        if re.match(r"^/shops/\d+$", path):
            return {"currency_code": "USD"}
        if re.match(r"^/shops/\d+/shipping-profiles$", path):
            return {"results": list(self.profiller.values())}
        m = re.match(r"^/shops/\d+/shipping-profiles/(\d+)$", path)
        if m:
            return self.profiller[m.group(1)]
        m = re.match(r"^/listings/(\d+)(/inventory)?$", path)
        d = self.db[m.group(1)]
        if method == "GET":
            return {"state": d["state"]} if not m.group(2) else json.loads(json.dumps(d["inv"]))
        body = json.loads(json.dumps(kw.get("json_body")))
        for p in body["products"]:
            o = p["offerings"][0]
            o["price"] = dict(amount=round(o["price"] * 100), divisor=100)
        d["inv"] = body
        return {}

    def _tek(self, path, body):
        self.calls += 1
        self.remaining = str(int(self.remaining) - 1)
        self.istek.append(("POST", path, dict(body)))
        if path.endswith("/shipping-profiles"):
            pid = str(9000 + len(self.profiller))
            self.profiller[pid] = dict(shipping_profile_id=int(pid), title=body["title"], origin_country_iso=body["origin_country_iso"],
                                       min_processing_days=body["min_processing_time"], max_processing_days=body["max_processing_time"],
                                       shipping_profile_destinations=[self._hedef(body)])
            return 201, {"shipping_profile_id": int(pid)}, ""
        pid = path.split("/")[-2]
        cc = body["destination_country_iso"]
        if cc in self.ret:
            return self.ret[cc], None, f"{self.ret[cc]} reddedildi"
        self.profiller[pid]["shipping_profile_destinations"].append(self._hedef(body))
        return 201, {}, ""

    @staticmethod
    def _hedef(b):
        return dict(destination_country_iso=b["destination_country_iso"], destination_region="none",
                    primary_cost=dict(amount=round(b["primary_cost"] * 100), divisor=100),
                    secondary_cost=dict(amount=round(b["secondary_cost"] * 100), divisor=100),
                    min_delivery_days=b["min_delivery_days"], max_delivery_days=b["max_delivery_days"])


class KuruFiyat(KuruAg, FiyatIzin):
    def __init__(self, lids):  # noqa: D401  (Etsy.__init__ yok: token yok)
        self.kuru_kur(lids)


class KuruProfil(KuruAg, ProfilIzin):
    def __init__(self, lids=None):
        self.kuru_kur(lids or {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "profil_kuru", "profil", "fiyat_kuru", "fiyat", "kuru"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    if a.mod == "kuru":
        lids = {c: str(4600000000 + i) for i, c in enumerate(OT.CIFTLER)}
        (out / "kuru").mkdir(exist_ok=True)
        apif = KuruFiyat(lids)
        fiyat(apif, "1", out / "kuru", {"CANCER_LIBRA": lids["CANCER_LIBRA"]}, ["CANCER_LIBRA"])
        Rf = fiyat(apif, "1", out / "kuru", lids, OT.cift_listesi("TUMU"), pilot="CANCER_LIBRA")
        apip = KuruProfil()
        Rp = profil(apip, "1", out / "kuru")
        json.dump(apif.istek + apip.istek, open(out / "kuru" / "KURU_ISTEK.json", "w"), indent=1, default=str)
        print(f"KURU fiyat {Rf['ozet']} | profil {Rp['kontrol']} | istek fiyat {apif.calls} profil {apip.calls}")
        return
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    shop = os.environ["ETSY_SHOP_ID"]
    if a.mod == "profil_kuru":
        profil(SaltOkur(store), shop, out, kuru=True); return
    if a.mod == "profil":
        profil(ProfilIzin(store), shop, out); return
    lids = durum_oku(out)
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out, lids); return
    ciftler = OT.cift_listesi(a.ciftler)
    if a.mod == "fiyat_kuru":
        api = SaltOkur(store); api.izinli = frozenset()
        fiyat(api, shop, out, lids, ciftler, kuru=True); return
    fiyat(FiyatIzin(store), shop, out, lids, ciftler, pilot=(os.environ.get("PILOT_CIFT") or "").strip() or None)


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
