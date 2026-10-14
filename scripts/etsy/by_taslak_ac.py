#!/usr/bin/env python3
"""BIZIM YILIMIZ: CANCER_LIBRA TEK TASLAK (14 Eki 2026, Takip gorevi). YAYIN YOK.

MOD=ac (varsayilan): yeni taslak.
  0) canli 4570143815 OKUNUR  1) createDraftListing (tek POST, tek deneme)  2) envanter  3) 10 gorsel
  4) kisisellestirme (5 kutu)  5) nitelikler (canliyla ayni, Holiday HARIC)  6) son dogrulama
MOD=duzelt (14 Eki Serdar kararlari): ESKI_ID taslagi okunur.
  production partner + who_made + when_made canliyla ayniysa -> DUZENLEME (PATCH yok):
      kisisellestirme POST (5 kutu) + Holiday niteligi DELETE.
  degilse (duzeltmesi PATCH ister) -> taslak SILINIR (yalniz state=draft ise) ve MOD=ac akisi tek seferde yeniden acar.
Her yazmadan sonra state okunur; "active" -> aninda state=inactive ve DUR. Canli ilana (REF) yazma kilitli.
Ciktilar: <OUT>/BY_TASLAK_CANCER_LIBRA.json, <OUT>/DURUM.json

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, CSV, IMG_DIR, OUT, MOD, ESKI_ID
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import requests  # noqa: E402
from etsy_common import API, Etsy, TokenStore, mask  # noqa: E402

PAIR = "CANCER_LIBRA"
REF = 4570143815
SECTION_ID = 60895624
STYLES = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]
FORMATS = [("Printable card 5x7", 5.00), ("Digital file 8x10", 9.00), ("Print 8x10", 29.00)]
MATERIALS = ["matte paper", "ink"]
HARIC_NITELIK = {"Holiday"}                       # Serdar 14 Eki: Holiday: Christmas kaldirilir
GALERI = ["01_Cover_A.jpg", "02_Shared_Symbol_A.jpg", "03_Five_Styles_A.jpg", "04_Personalization_A.jpg", "05_Starlit_Timeless_A.jpg",
          "06_FirstPage_Botanical_A.jpg", "07_Layers_Material_A.jpg", "08_Formats_A.jpg", "09_Size_Gift_Scene_A.jpg", "10_Free_Preview_A.jpg"]


def sorular(pair):
    """Serdar 14 Eki: 5 ayri kutu. Burc adlari cifte gore."""
    s1, s2 = (p.capitalize() for p in pair.split("_", 1))
    def q(t, req, n, ins=None):
        d = dict(question_text=t, question_type="text_input", required=req, max_allowed_characters=n)
        if ins:
            d["instructions"] = ins
        return d
    return [q(f"Name under {s1}", True, 11), q(f"Name under {s2}", True, 11),
            q("Your special date", True, 20, "Example: 14 June 2025"),
            q("Top line", True, 20, "Paper Anniversary or Our First Year"),
            q("Optional short line", False, 20, "Leave empty for Year One")]


class Kilitli(Etsy):
    """Izinli yazmalar yalniz bu taslak icin; canli ilana (REF) ve baska yola yazma programi durdurur."""
    lid = None
    silinebilir = None        # MOD=duzelt: yalniz bu eski taslak silinebilir

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings$")]
        if lid:
            ok += [("PUT", rf"^/listings/{lid}/inventory$"), ("POST", rf"^/shops/\d+/listings/{lid}/images$"),
                   ("POST", rf"^/shops/\d+/listings/{lid}/personalization$"),
                   ("PUT", rf"^/shops/\d+/listings/{lid}/properties/\d+$"), ("DELETE", rf"^/shops/\d+/listings/{lid}/properties/\d+$"),
                   ("PATCH", rf"^/shops/\d+/listings/{lid}$")]
        if self.silinebilir:
            ok += [("DELETE", rf"^/listings/{self.silinebilir}$")]
        if str(REF) in path or not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def post(self, path, data):
        self._izin("POST", path); return super().post(path, data)

    def put(self, path, data):
        self._izin("PUT", path); return super().put(path, data)

    def put_json(self, path, body):
        self._izin("PUT", path); return super().put_json(path, body)

    def post_json(self, path, body):
        self._izin("POST", path); return super().post_json(path, body)

    def post_file(self, path, files, data=None):
        self._izin("POST", path); return super().post_file(path, files, data)

    def patch(self, path, data):
        self._izin("PATCH", path)
        if data != {"state": "inactive"}:
            raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        return super().patch(path, data)

    def delete(self, path):
        self._izin("DELETE", path); return super().delete(path)


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Kilitli(store)
    shop = os.environ["ETSY_SHOP_ID"]
    mod = os.environ.get("MOD", "ac")
    R = {"mod": mod, "adimlar": []}
    durum_f = out / "DURUM.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(out / "BY_TASLAK_CANCER_LIBRA.json", "w"), indent=1, ensure_ascii=False, default=str)

    def state_oku(adim):
        L = api.get(f"/listings/{api.lid}") or {}
        st = L.get("state")
        R["adimlar"].append((adim, st))
        print(f"{adim}: state={st}")
        if st == "active":
            api.patch(f"/shops/{shop}/listings/{api.lid}", {"state": "inactive"})
            st2 = (api.get(f"/listings/{api.lid}") or {}).get("state")
            R["adimlar"].append((adim + " ACIL inactive", st2)); kaydet()
            print(f"::error::ACIL: {adim} sonrasi active goruldu -> inactive yapildi (simdi {st2}). DURULDU.")
            raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"HATA: beklenmeyen state {st} ({adim})")
        return L

    # 0) canli ilan (salt okuma)
    L0 = api.get(f"/listings/{REF}") or {}
    props0 = (api.get(f"/shops/{shop}/listings/{REF}/properties") or {}).get("results") or []
    inv0 = api.get(f"/listings/{REF}/inventory") or {}
    rs = sorted({o.get("readiness_state_id") for p in inv0.get("products") or [] for o in p.get("offerings") or [] if o.get("readiness_state_id")})
    if len(rs) != 1:
        raise SystemExit(f"HATA: canli ilanda readiness_state_id tek degil: {rs}")
    sp = api.get(f"/shops/{shop}/shipping-profiles/{L0['shipping_profile_id']}") or {}
    partner0 = sorted(p.get("production_partner_id") for p in L0.get("production_partners") or [])
    R["canli"] = dict(state=L0.get("state"), shipping_profile=(L0.get("shipping_profile_id"), sp.get("title")),
                      return_policy_id=L0.get("return_policy_id"), taxonomy_id=L0.get("taxonomy_id"), who_made=L0.get("who_made"),
                      when_made=L0.get("when_made"), readiness_state_id=rs[0], processing=(L0.get("processing_min"), L0.get("processing_max")),
                      production_partners=partner0, nitelikler=[(p.get("property_id"), p.get("property_name"), p.get("values")) for p in props0])
    props_hedef = [p for p in props0 if p.get("value_ids") and p.get("property_name") not in HARIC_NITELIK]
    haric_ids = [p["property_id"] for p in props0 if p.get("property_name") in HARIC_NITELIK]

    row = next(r for r in csv.DictReader(open(os.environ["CSV"], encoding="utf-8")) if r["cift"] == PAIR)
    title, desc = row["baslik"], row["aciklama"]
    tags = [row[f"etiket_{i}"] for i in range(1, 14)]
    Q = sorular(PAIR)
    if re.search("[–—]", title + desc + "".join(tags) + json.dumps(Q, ensure_ascii=False)):
        raise SystemExit("HATA: metinde uzun/orta tire var")

    def kisisel_ve_nitelik(lid, mevcut_props):
        api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": Q})
        state_oku("kisisellestirme (5 kutu)")
        var = {p.get("property_id") for p in mevcut_props}
        for p in props_hedef:
            if p["property_id"] in var:
                continue
            b = {"value_ids": ",".join(str(v) for v in p["value_ids"]), "values": ",".join(p.get("values") or [])}
            if p.get("scale_id"):
                b["scale_id"] = p["scale_id"]
            api.put(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}", b)
        for pid in haric_ids:
            if pid in var:
                api.delete(f"/shops/{shop}/listings/{lid}/properties/{pid}")
        state_oku("nitelikler (Holiday haric)")

    yontem = None
    if mod == "duzelt":
        eski = int(os.environ["ESKI_ID"])
        api.lid = eski
        LE = state_oku("duzelt 0 okuma")
        pE = sorted(p.get("production_partner_id") for p in LE.get("production_partners") or [])
        R["eski_taslak"] = dict(id=eski, production_partners=pE, who_made=LE.get("who_made"), when_made=LE.get("when_made"))
        uygun = pE == partner0 and LE.get("who_made") == L0.get("who_made") and LE.get("when_made") == L0.get("when_made")
        if uygun:
            yontem = "DUZENLEME (PATCH yok): kisisellestirme POST + nitelik DELETE"
            R["yontem"] = yontem; kaydet()
            propsE = (api.get(f"/shops/{shop}/listings/{eski}/properties") or {}).get("results") or []
            kisisel_ve_nitelik(eski, propsE)
            lid = eski
        else:
            yontem = (f"YENIDEN ACMA: eski taslakta partner {pE} / who_made {LE.get('who_made')} / when_made {LE.get('when_made')} "
                      f"canlidan farkli (partner {partner0}); duzeltmesi PATCH ister -> eski taslak silindi")
            R["yontem"] = yontem
            api.silinebilir = eski
            api.delete(f"/listings/{eski}")
            gone = api.get(f"/listings/{eski}", ok404=True)
            R["eski_silindi"] = gone is None or gone.get("state") in (None, "removed")
            print(f"eski taslak {eski} silindi: {R['eski_silindi']} ({(gone or {}).get('state')})")
            if not R["eski_silindi"]:
                kaydet(); raise SystemExit("HATA: eski taslak silinmedi; yeni acilmadi")
            api.silinebilir = None
            D = {}
            mod = "ac"
            kaydet()

    if mod == "ac":
        lid = D.get("listing_id")
        if not lid:
            drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
            lid = next((x["listing_id"] for x in drafts if x.get("title") == title), None)
        if lid:
            api.lid = lid
            R["olusturma"] = "VAR OLAN TASLAK kullanildi (ikinci ilan acilmadi)"
        else:
            body = {"quantity": 999, "title": title, "description": desc, "price": FORMATS[0][1], "who_made": L0["who_made"],
                    "when_made": L0["when_made"], "is_supply": "false", "taxonomy_id": L0["taxonomy_id"], "type": "physical",
                    "shipping_profile_id": L0["shipping_profile_id"], "return_policy_id": L0["return_policy_id"],
                    "readiness_state_id": rs[0], "shop_section_id": SECTION_ID, "tags": ",".join(tags),
                    "materials": ",".join(MATERIALS), "should_auto_renew": "true", "is_personalizable": "true",
                    "production_partner_ids": ",".join(str(p) for p in partner0)}
            api._izin("POST", f"/shops/{shop}/listings")
            r_ = requests.post(API + f"/shops/{shop}/listings", data=body, headers=api._headers(), timeout=120)   # TEK deneme
            if r_.status_code not in (200, 201):
                drafts = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100}) or {}).get("results") or []
                lid = next((x["listing_id"] for x in drafts if x.get("title") == title), None)
                if lid:
                    D["listing_id"] = lid; kaydet()
                raise SystemExit(f"HATA: createDraftListing {r_.status_code}: {r_.text[:300]} | ayni baslikli taslak: {lid}")
            lid = r_.json().get("listing_id")
            if not lid:
                raise SystemExit("HATA: createDraftListing listing_id donmedi")
            api.lid = lid
            R["olusturma"] = "yeni taslak (tek POST)"
        D["listing_id"] = lid; kaydet()
        print(f"::warning::listing_id {lid}")
        state_oku("1 olusturma")

        inv = api.get(f"/listings/{lid}/inventory") or {}
        if len(inv.get("products") or []) != 15:
            prods = [dict(sku="", property_values=[dict(property_id=513, property_name="Style", values=[st]),
                                                   dict(property_id=514, property_name="Format", values=[fm])],
                          offerings=[dict(price=pr, quantity=999, is_enabled=True, readiness_state_id=rs[0])])
                     for st in STYLES for fm, pr in FORMATS]
            api.put_json(f"/listings/{lid}/inventory", dict(products=prods, price_on_property=[514], quantity_on_property=[], sku_on_property=[]))
        state_oku("2 envanter")

        img_dir = Path(os.environ["IMG_DIR"])
        have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
        for rk, n in enumerate(GALERI, 1):
            if rk in have:
                continue
            p = img_dir / n
            if not p.exists():
                raise SystemExit(f"HATA: gorsel yok {n}")
            with open(p, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (n, fh, "image/jpeg")}, data={"rank": str(rk)})
        state_oku("3 gorseller")

        propsN = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
        kisisel_ve_nitelik(lid, propsN)
        if not yontem:
            yontem = "yeni taslak"

    # son dogrulama
    L = api.get(f"/listings/{lid}") or {}
    imgs = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    inv = api.get(f"/listings/{lid}/inventory") or {}
    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    tablo = []
    for p in inv.get("products") or []:
        pr = p["offerings"][0].get("price") or {}
        tablo.append((" / ".join(v["values"][0] for v in p["property_values"]),
                      round(pr["amount"] / pr["divisor"], 2) if isinstance(pr, dict) and pr.get("divisor") else pr, p["offerings"][0].get("is_enabled")))
    beklenen = {f"{st} / {fm}": pr for st in STYLES for fm, pr in FORMATS}
    q_ok = [(q.get("question_text"), q.get("required"), q.get("max_allowed_characters"), q.get("instructions") or "") for q in per] == \
           [(q["question_text"], q["required"], q["max_allowed_characters"], q.get("instructions", "")) for q in Q]
    pN = sorted(p.get("production_partner_id") for p in L.get("production_partners") or [])
    R["son"] = dict(listing_id=lid, state=L.get("state"), yontem=yontem, link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    baslik_ayni=L.get("title") == title, etiket=len(L.get("tags") or []),
                    gorsel=len(imgs), gorsel_sira=[i.get("rank") for i in imgs],
                    varyasyon=len(tablo), varyasyon_dogru=len(tablo) == 15 and all(beklenen.get(a) == pr for a, pr, _ in tablo),
                    kisisellestirme=[(q.get("question_text"), q.get("required"), q.get("max_allowed_characters"), q.get("instructions")) for q in per],
                    kisisellestirme_dogru=q_ok, nitelik=[(p.get("property_name"), p.get("values")) for p in props],
                    holiday_yok=not any(p.get("property_name") in HARIC_NITELIK for p in props),
                    production_partners=pN, partner_ayni=pN == partner0,
                    who_made=(L.get("who_made"), L0.get("who_made")), when_made=(L.get("when_made"), L0.get("when_made")),
                    malzeme=L.get("materials"), islem=(L.get("processing_min"), L.get("processing_max")),
                    kargo=L.get("shipping_profile_id"), bolum=L.get("shop_section_id"), is_personalizable=L.get("is_personalizable"))
    R["kota_kalan"] = api.remaining
    kaydet()
    s_ = R["son"]
    print(f"::warning::TASLAK {lid} state={s_['state']} | {yontem[:60]} | kutu {len(per)} dogru={q_ok} | holiday_yok={s_['holiday_yok']} | "
          f"partner {pN} ayni={s_['partner_ayni']} | who {s_['who_made']} when {s_['when_made']} | gorsel {s_['gorsel']} | varyasyon {len(tablo)} {s_['varyasyon_dogru']}")
    if s_["state"] != "draft":
        raise SystemExit(f"HATA: son state {s_['state']}")


if __name__ == "__main__":
    main()
