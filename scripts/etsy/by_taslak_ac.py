#!/usr/bin/env python3
"""BIZIM YILIMIZ: CANCER_LIBRA TEK TASLAK (14 Eki 2026, Takip gorevi). YAYIN YOK.

Akis (her yazmadan sonra state okunur; "active" gorulurse aninda state=inactive ve DUR):
  0) canli 4570143815 OKUNUR (kargo, iade, kategori, nitelikler, readiness, uretim ortagi)
  1) createDraftListing (tek POST; tum alanlar govdede; PATCH yok)
  2) updateListingInventory: Style(513) x Format(514), fiyat yalniz Format'a gore
  3) 10 gorsel (rank 1..10)
  4) kisisellestirme: TEK text_input kutu, zorunlu, karakter siniri Etsy'nin kabul ettigi en buyuk deger
  5) nitelikler (canli ilanla ayni)
  6) son dogrulama -> <OUT>/BY_TASLAK_CANCER_LIBRA.json
Yeniden kosuda ikinci ilan ACILMAZ: <OUT>/DURUM.json (Drive'dan indirilir) veya ayni baslikli taslak varsa o kullanilir.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, CSV, IMG_DIR, OUT
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
GALERI = ["01_Cover_A.jpg", "02_Shared_Symbol_A.jpg", "03_Five_Styles_A.jpg", "04_Personalization_A.jpg", "05_Starlit_Timeless_A.jpg",
          "06_FirstPage_Botanical_A.jpg", "07_Layers_Material_A.jpg", "08_Formats_A.jpg", "09_Size_Gift_Scene_A.jpg", "10_Free_Preview_A.jpg"]
Q_TEXT = "Names, date and lines"
Q_INSTR = ("Please write: 1) Name under Cancer 2) Name under Libra (up to 11 letters each) 3) Your special date "
           "4) Top line: Paper Anniversary or Our First Year 5) Optional short line, up to 20 characters (otherwise Year One)")
CHAR_DENE = [1024, 1000, 512, 500, 256, 255]   # Etsy'nin kabul ettigi en buyugu bulunur (red edilen sonraki degere gecer)


class Kilitli(Etsy):
    """Izinli yazmalar yalniz bu taslak icin; canli ilana (REF) ve baska yola yazma programi durdurur."""
    lid = None

    def _izin(self, method, path):
        lid = str(self.lid or "")
        ok = [("POST", rf"^/shops/\d+/listings$")]
        if lid:
            ok += [("PUT", rf"^/listings/{lid}/inventory$"), ("POST", rf"^/shops/\d+/listings/{lid}/images$"),
                   ("POST", rf"^/shops/\d+/listings/{lid}/personalization$"), ("PUT", rf"^/shops/\d+/listings/{lid}/personalization$"),
                   ("PUT", rf"^/shops/\d+/listings/{lid}/properties/\d+$"), ("PATCH", rf"^/shops/\d+/listings/{lid}$")]
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
        raise SystemExit("YASAK: DELETE")


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Kilitli(store)
    shop = os.environ["ETSY_SHOP_ID"]
    R = {"adimlar": []}
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
        if st not in ("draft",):
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
    R["canli"] = dict(state=L0.get("state"), shipping_profile=(L0.get("shipping_profile_id"), sp.get("title")),
                      return_policy_id=L0.get("return_policy_id"), taxonomy_id=L0.get("taxonomy_id"), who_made=L0.get("who_made"),
                      when_made=L0.get("when_made"), readiness_state_id=rs[0], processing=(L0.get("processing_min"), L0.get("processing_max")),
                      production_partners=[p.get("production_partner_id") for p in L0.get("production_partners") or []],
                      nitelikler=[(p.get("property_id"), p.get("property_name"), p.get("values")) for p in props0])

    row = next(r for r in csv.DictReader(open(os.environ["CSV"], encoding="utf-8")) if r["cift"] == PAIR)
    title, desc = row["baslik"], row["aciklama"]
    tags = [row[f"etiket_{i}"] for i in range(1, 14)]
    if re.search("[–—]", title + desc + "".join(tags) + Q_INSTR):
        raise SystemExit("HATA: metinde uzun/orta tire var")

    # 1) taslak (tek POST); yeniden kosuda ikinci ilan acilmaz
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
                "production_partner_ids": ",".join(str(p) for p in R["canli"]["production_partners"])}
        api._izin("POST", f"/shops/{shop}/listings")
        r_ = requests.post(API + f"/shops/{shop}/listings", data=body, headers=api._headers(), timeout=120)   # TEK deneme (5xx'te tekrar YOK)
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

    # 2) envanter
    inv = api.get(f"/listings/{lid}/inventory") or {}
    mevcut = {(tuple(v.get("values", [""])[0] for v in p.get("property_values") or [])): p for p in inv.get("products") or []}
    if len(mevcut) != 15:
        prods = [dict(sku="", property_values=[dict(property_id=513, property_name="Style", values=[st]),
                                               dict(property_id=514, property_name="Format", values=[fm])],
                      offerings=[dict(price=pr, quantity=999, is_enabled=True, readiness_state_id=rs[0])])
                 for st in STYLES for fm, pr in FORMATS]
        api.put_json(f"/listings/{lid}/inventory", dict(products=prods, price_on_property=[514], quantity_on_property=[], sku_on_property=[]))
    state_oku("2 envanter")

    # 3) gorseller
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

    # 4) kisisellestirme: tek kutu, zorunlu, en buyuk kabul edilen karakter siniri
    R["kisisellestirme_denemeleri"] = []
    kabul = None
    for n in CHAR_DENE:
        q = dict(personalization_questions=[dict(question_text=Q_TEXT, instructions=Q_INSTR, question_type="text_input",
                                                 required=True, max_allowed_characters=n)])
        try:
            api.post_json(f"/shops/{shop}/listings/{lid}/personalization", q)
            kabul = n; R["kisisellestirme_denemeleri"].append((n, "KABUL")); break
        except SystemExit as e:
            R["kisisellestirme_denemeleri"].append((n, str(e)[:300]))
    if kabul is None:
        kaydet(); raise SystemExit("HATA: kisisellestirme hicbir karakter sinirinda kabul edilmedi")
    state_oku("4 kisisellestirme")

    # 5) nitelikler (canli ilanla ayni)
    for p in props0:
        if not p.get("value_ids"):
            continue
        b = {"value_ids": ",".join(str(v) for v in p["value_ids"]), "values": ",".join(p.get("values") or [])}
        if p.get("scale_id"):
            b["scale_id"] = p["scale_id"]
        api.put(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}", b)
    state_oku("5 nitelikler")

    # 6) son dogrulama
    L = api.get(f"/listings/{lid}") or {}
    imgs = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    inv = api.get(f"/listings/{lid}/inventory") or {}
    per = api.get(f"/listings/{lid}/personalization", ok404=True) or {}
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    tablo = [(" / ".join(v["values"][0] for v in p["property_values"]), (p["offerings"][0].get("price") or {}), p["offerings"][0].get("is_enabled"))
             for p in inv.get("products") or []]
    tablo = [(a, round(pr["amount"] / pr["divisor"], 2) if isinstance(pr, dict) and pr.get("divisor") else pr, e) for a, pr, e in tablo]
    beklenen = {f"{st} / {fm}": pr for st in STYLES for fm, pr in FORMATS}
    R["son"] = dict(listing_id=lid, state=L.get("state"), link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    baslik=L.get("title"), baslik_ayni=L.get("title") == title, etiket=len(L.get("tags") or []),
                    etiket_ayni=[t.lower() for t in (L.get("tags") or [])] == [t.lower() for t in tags],
                    aciklama_ayni=(L.get("description") or "").strip() == desc.strip(),
                    gorsel=len(imgs), gorsel_sira=[i.get("rank") for i in imgs],
                    gorsel_boyut=[(i.get("rank"), i.get("full_width"), i.get("full_height")) for i in imgs],
                    varyasyon=tablo, varyasyon_dogru=len(tablo) == 15 and all(beklenen.get(a) == pr for a, pr, _ in tablo),
                    price_on_property=inv.get("price_on_property"),
                    kisisellestirme=per.get("personalization_questions"), karakter_siniri=kabul,
                    kargo=(L.get("shipping_profile_id"), sp.get("title")), bolum=L.get("shop_section_id"),
                    iade=L.get("return_policy_id"), kategori=L.get("taxonomy_id"), islem=(L.get("processing_min"), L.get("processing_max")),
                    malzeme=L.get("materials"), nitelik=[(p.get("property_name"), p.get("values")) for p in props],
                    is_personalizable=L.get("is_personalizable"))
    R["kota_kalan"] = api.remaining
    kaydet()
    s_ = R["son"]
    print(f"::warning::TASLAK {lid} state={s_['state']} | gorsel {s_['gorsel']} {s_['gorsel_sira']} | varyasyon {len(tablo)} dogru={s_['varyasyon_dogru']} | "
          f"kisisel siniri {kabul} | baslik={s_['baslik_ayni']} etiket={s_['etiket']}/{s_['etiket_ayni']} aciklama={s_['aciklama_ayni']} | bolum {s_['bolum']}")
    if s_["state"] != "draft":
        raise SystemExit(f"HATA: son state {s_['state']}")


if __name__ == "__main__":
    main()
