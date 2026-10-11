#!/usr/bin/env python3
"""78 POD ilani: yeni baslik, 13 etiket, aciklamanin ilk 2 cumlesi ve 3 nitelik (Serdar onayi, Merkez karari 11 Eki).

Kaynak: data/seo/50_KARAR_YAZIM_20261011.csv (proje claude/50_KARAR_YAZIM_20261011.csv, birebir).
Nitelikler (kategori 121): Subject = Zodiac + Love & friendship; Room = Bedroom + Living room; Holiday = Christmas.
  property_id ve value_id: getPropertiesByTaxonomyId(121) (isim eslemesi) + 46_NITELIK_SECENEK.csv property_id capraz kontrol.
DEGISMEZ: fotograflar, video, fiyat/envanter, varyasyonlar, kisisellestirme, kargo, kategori, Occasion ve diger nitelikler,
  aciklamanin ilk 2 cumlesinden sonrasi (yalniz eski_aciklama_ilk2 metni birebir ve TEK kez bulunursa degistirilir).

Mod yedek (SALT OKUMA): 78 ilan baslik, etiket, tam aciklama, tum nitelikler, state, taksonomi, korunanlar -> OUT/51_YEDEK_ONCE.json
  + on denetim (metin sinirlari, eski 2 cumle bulunuyor mu, active mi) -> OUT/51_ON_DENETIM.csv.
Mod yaz (ETSY'YE YAZAR, --confirm SEO51): --cift ile secilen ilanlar (bos = kalan hepsi). Ilan basina: on kosul -> PATCH
  title + tags + description -> 3 x updateListingProperty -> geri okuma (dosyayla birebir) + korunan alanlar ayni.
  Ilk FAIL'de DURUR (geri alma elle, mod geri ile).
  Denetim FAIL ilan yazilmaz, listelenir, digerlerine devam edilir; yazim sonrasi geri okuma FAIL'de DURUR.
Mod ham (SALT OKUMA): 78 ilan API'den geldigi gibi (title, tags, description ilk 400, Subject/Room/Holiday/Occasion) -> 53_GERI_OKUMA_HAM.json.
Mod geri (ETSY'YE YAZAR, --confirm GERIAL): yedekten baslik, etiket, aciklama ve 3 niteligi eski haline dondurur. CALISTIRILMAZ
  (yalniz Serdar onayiyla).
Kullanim: seo51_yaz.py yedek --karar K.csv --nitelik N.csv --out OUT
          seo51_yaz.py yaz --karar K.csv --yedek 51_YEDEK_ONCE.json --out OUT --confirm SEO51 [--cift A,B]
          seo51_yaz.py geri --yedek 51_YEDEK_ONCE.json --out OUT --confirm GERIAL [--cift A,B]
"""
import argparse, csv, hashlib, html, json, os, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

TAKSONOMI = 121
NITELIK = {"Subject": ["Zodiac", "Love & friendship"], "Room": ["Bedroom", "Living room"], "Holiday": ["Christmas"]}
TIRE = re.compile("[–—]")
ETIKET_KAR = re.compile(r"[^A-Za-z0-9 '\-]")


def log(m): print(m, flush=True)


def un(t): return html.unescape(t or "").replace("\r\n", "\n")


def karar_oku(yol):
    R = list(csv.DictReader(open(yol, encoding="utf-8")))
    out = {}
    for r in R:
        tg = [x.strip() for x in r["yeni_etiketler"].split("|")]
        out[r["cift"]] = dict(listing_id=r["listing_id"].strip(), cift=r["cift"], title=r["yeni_baslik"], tags=tg,
                              yeni2=r["yeni_aciklama_ilk2"], eski2=r["eski_aciklama_ilk2"])
    return out


def metin_denetim(k):
    h = []
    if len(k["title"]) > 140: h.append(f"baslik {len(k['title'])} > 140")
    if len(k["tags"]) != 13 or len(set(k["tags"])) != 13: h.append(f"etiket sayisi {len(k['tags'])} / benzersiz {len(set(k['tags']))}")
    if any(not t or len(t) > 20 for t in k["tags"]): h.append("etiket > 20 karakter ya da bos")
    if any(ETIKET_KAR.search(t) for t in k["tags"]): h.append("etikette izinsiz karakter")
    if any(TIRE.search(x) for x in (k["title"], k["yeni2"], " ".join(k["tags"]))): h.append("uzun/orta tire")
    return h


def nitelik_plan(api, nit_csv):
    P = (api.get(f"/seller-taxonomy/nodes/{TAKSONOMI}/properties") or {}).get("results") or []
    csv_pid = {}
    if nit_csv and os.path.exists(nit_csv):
        for r in csv.DictReader(open(nit_csv, encoding="utf-8-sig")):
            csv_pid.setdefault(r["nitelik_adi"].strip(), r["property_id"].strip())
    plan = {}
    for ad, degerler in NITELIK.items():
        p = [x for x in P if ad.lower() in ((x.get("display_name") or "").lower(), (x.get("name") or "").lower())]
        if len(p) != 1: raise SystemExit(f"DUR: nitelik '{ad}' kategori {TAKSONOMI}'de {len(p)} kez bulundu")
        p = p[0]; pid = str(p["property_id"])
        if csv_pid and csv_pid.get(ad) and csv_pid[ad] != pid: raise SystemExit(f"DUR: '{ad}' property_id API {pid} != 46 CSV {csv_pid[ad]}")
        pv = {v.get("name"): v.get("value_id") for v in (p.get("possible_values") or [])}
        eksik = [d for d in degerler if d not in pv]
        if eksik: raise SystemExit(f"DUR: '{ad}' degerleri yok: {eksik}")
        if len(degerler) > 1 and not p.get("is_multivalued", True): raise SystemExit(f"DUR: '{ad}' coklu deger almiyor")
        plan[ad] = dict(property_id=pid, value_ids=[pv[d] for d in degerler], values=degerler)
    return plan


def ozellikler(api, shop, lid):
    r = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
    return {str(x.get("property_id")): dict(name=x.get("property_name"), value_ids=sorted(x.get("value_ids") or []),
                                            values=x.get("values") or [], scale_id=x.get("scale_id")) for x in r}


def durum(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    g = G.galeri(api, lid)
    kis = {k: L.get(k) for k in ("is_personalizable", "personalization_is_required", "personalization_char_count_max",
                                 "personalization_instructions")}
    kor = G.korunanlar(api, shop, lid)
    return dict(listing_id=lid, state=L.get("state"), taxonomy_id=L.get("taxonomy_id"), title=un(L.get("title")),
                tags=[un(t) for t in (L.get("tags") or [])], description=un(L.get("description")),
                shipping_profile_id=L.get("shipping_profile_id"), shop_section_id=L.get("shop_section_id"),
                price=L.get("price"), ozellik=ozellikler(api, shop, lid), kisi=kis,
                inv_sha=kor["inv_sha"], n_urun=kor["n_urun"], video_ids=kor["video_ids"],
                galeri=[x.get("listing_image_id") for x in g], bag=sorted((v.get("value"), v.get("image_id")) for v in G.var_img(api, shop, lid)))


KORUNAN = ("state", "taxonomy_id", "shipping_profile_id", "shop_section_id", "price", "kisi", "inv_sha", "n_urun", "video_ids", "galeri", "bag")


def beklenen_aciklama(once_desc, k):
    n = once_desc.count(k["eski2"])
    if n != 1: return None, f"eski 2 cumle aciklamada {n} kez (1 bekleniyordu)"
    return once_desc.replace(k["eski2"], k["yeni2"], 1), ""


def karsilastir(son, k, bek_desc, plan, once):
    r = dict(baslik_ok=son["title"] == k["title"], etiket_ok=son["tags"] == k["tags"], aciklama_ok=son["description"] == bek_desc)
    nok, h = True, []
    for ad, p in plan.items():
        o = son["ozellik"].get(p["property_id"]) or {}
        if o.get("value_ids") != sorted(p["value_ids"]): nok = False; h.append(f"{ad} {o.get('values')}")
    diger_once = {pid: v for pid, v in once["ozellik"].items() if pid not in {p["property_id"] for p in plan.values()}}
    diger_son = {pid: v for pid, v in son["ozellik"].items() if pid not in {p["property_id"] for p in plan.values()}}
    if diger_once != diger_son: nok = False; h.append("diger nitelikler degisti")
    r["nitelik_ok"] = nok
    deg = [x for x in KORUNAN if son.get(x) != once.get(x)]
    if deg: h.append(f"korunan degisti {deg}")
    if not r["baslik_ok"]: h.append("baslik")
    if not r["etiket_ok"]: h.append(f"etiket {son['tags']}")
    if not r["aciklama_ok"]: h.append("aciklama")
    r["hata"] = "; ".join(h)
    r["PASS"] = all(r[x] for x in ("baslik_ok", "etiket_ok", "aciklama_ok", "nitelik_ok")) and not deg
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["yedek", "yaz", "geri", "ham"]); ap.add_argument("--karar"); ap.add_argument("--nitelik", default="")
    ap.add_argument("--yedek"); ap.add_argument("--out", required=True); ap.add_argument("--confirm", default="")
    ap.add_argument("--cift", default=""); ap.add_argument("--kota-taban", type=int, default=300)
    a = ap.parse_args()
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k_); mask(s_)
    st = TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if st.needs_refresh(): st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]; out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); c0 = api.calls
    secim = [c for c in a.cift.split(",") if c]

    if a.mod == "yedek":
        K = karar_oku(a.karar)
        if len(K) != 78: raise SystemExit(f"DUR: karar dosyasi {len(K)} satir")
        plan = nitelik_plan(api, a.nitelik)
        Y, D = {"_nitelik_plan": plan, "_ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}, []
        for i, (c, k) in enumerate(sorted(K.items()), 1):
            d = durum(api, shop, k["listing_id"]); Y[c] = d
            _, ah = beklenen_aciklama(d["description"], k)
            h = metin_denetim(k) + ([ah] if ah else []) + ([f"state {d['state']}"] if d["state"] != "active" else []) \
                + ([f"taksonomi {d['taxonomy_id']}"] if d["taxonomy_id"] != TAKSONOMI else [])
            D.append([k["listing_id"], c, "PASS" if not h else "FAIL", "; ".join(h)])
            g = time.time() - t0
            log(f"[{i}/78] {c} {'PASS' if not h else 'FAIL ' + '; '.join(h)} | gecen {g:.0f}s | kalan ~{g/i*(78-i):.0f}s | %{100*i//78}")
        (out / "51_YEDEK_ONCE.json").write_text(json.dumps(Y, indent=1, ensure_ascii=False), encoding="utf-8")
        with open(out / "51_ON_DENETIM.csv", "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([["listing_id", "cift", "on_denetim", "hata"]] + D)
        n = sum(1 for x in D if x[2] == "PASS")
        log(f"OZET yedek: 78 ilan | on denetim PASS {n}/78 | nitelik plan {json.dumps(plan, ensure_ascii=False)} | API {api.calls - c0} | kota {api.remaining}")
        return 0 if n == 78 else 1

    if a.mod == "ham":
        # Merkez bagimsiz kontrolu (11 Eki): 78 ilan API'den GELDIGI GIBI, karsilastirma yok
        ids = [(r["listing_id"].strip(), r["cift"].strip()) for r in csv.DictReader(open(a.karar, encoding="utf-8"))]
        H = []
        for i, (lid, c) in enumerate(ids, 1):
            L = api.get(f"/listings/{lid}") or {}
            P = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
            nit = {x.get("property_name"): {"property_id": x.get("property_id"), "value_ids": x.get("value_ids"), "values": x.get("values")}
                   for x in P if x.get("property_name") in ("Subject", "Room", "Holiday", "Occasion")}
            H.append({"listing_id": L.get("listing_id"), "cift": c, "title": L.get("title"), "tags": L.get("tags"),
                      "description_ilk400": (L.get("description") or "")[:400], "nitelikler": nit})
            g = time.time() - t0
            log(f"[{i}/{len(ids)}] {c} | gecen {g:.0f}s | kalan ~{g/i*(len(ids)-i):.0f}s | %{100*i//len(ids)}")
        (out / "53_GERI_OKUMA_HAM.json").write_text(json.dumps({"_ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                                                               "ilanlar": H}, indent=1, ensure_ascii=False), encoding="utf-8")
        log(f"OZET ham: {len(H)} ilan | API {api.calls - c0} | kota {api.remaining}")
        return 0 if len(H) == 78 else 1

    Y = json.loads(Path(a.yedek).read_text(encoding="utf-8")); plan = Y["_nitelik_plan"]
    if a.mod == "geri":
        if a.confirm != "GERIAL": raise SystemExit("HATA: --confirm GERIAL gerekir.")
        for c in (secim or [x for x in Y if not x.startswith("_")]):
            o = Y[c]; lid = o["listing_id"]
            api.patch(f"/shops/{shop}/listings/{lid}", {"title": o["title"], "tags": ",".join(o["tags"]), "description": o["description"]})
            for ad, p in plan.items():
                e = o["ozellik"].get(p["property_id"])
                if e and e["value_ids"]:
                    b = {"value_ids": ",".join(str(v) for v in e["value_ids"]), "values": ",".join(e["values"])}
                    if e.get("scale_id"): b["scale_id"] = e["scale_id"]
                    api.put(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}", b)
                else:
                    api.delete(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}")
            s = durum(api, shop, lid)
            ok = s["title"] == o["title"] and s["tags"] == o["tags"] and s["description"] == o["description"] and s["ozellik"] == o["ozellik"]
            log(f"GERI {c} {'PASS' if ok else 'FAIL'}")
        return 0

    if a.confirm != "SEO51": raise SystemExit("HATA: --confirm SEO51 gerekir.")
    K = karar_oku(a.karar)
    rap_yol = out / "rapor"; rap_yol.mkdir(exist_ok=True)
    tamam = {p.stem for p in rap_yol.glob("*.json") if not p.stem.endswith("_sonra") and json.loads(p.read_text())["PASS"]}
    is_ = [c for c in sorted(K) if c not in tamam and (not secim or c in secim)]
    if secim and set(secim) - set(K): raise SystemExit(f"DUR: bilinmeyen cift {set(secim) - set(K)}")
    log(f"onceki PASS (atlanir): {len(tamam)} | bu kosu: {len(is_)}")
    for i, c in enumerate(is_, 1):
        k = K[c]; lid = k["listing_id"]; c1 = api.calls
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < a.kota_taban:
            log(f"DUR: kota {api.remaining} < {a.kota_taban}"); break
        once = durum(api, shop, lid)
        h = metin_denetim(k)
        if once["state"] != "active": h.append(f"state {once['state']}")
        if once["taxonomy_id"] != TAKSONOMI: h.append(f"taksonomi {once['taxonomy_id']}")
        y = Y.get(c) or {}
        if once["title"] != y.get("title") or once["description"] != y.get("description") or once["tags"] != y.get("tags"):
            h.append("canli ilan yedekten sonra degismis")
        bek, ah = beklenen_aciklama(once["description"], k)
        if ah: h.append(ah)
        if h:
            r = dict(listing_id=lid, cift=c, baslik_ok=False, etiket_ok=False, aciklama_ok=False, nitelik_ok=False,
                     hata="YAZILMADI: " + "; ".join(h), PASS=False, api=api.calls - c1)
        else:
            api.patch(f"/shops/{shop}/listings/{lid}", {"title": k["title"], "tags": ",".join(k["tags"]), "description": bek})
            for ad, p in plan.items():
                api.put(f"/shops/{shop}/listings/{lid}/properties/{p['property_id']}",
                        {"value_ids": ",".join(str(v) for v in p["value_ids"]), "values": ",".join(p["values"])})
            son = None
            for d in range(4):
                time.sleep(6)
                son = durum(api, shop, lid); r = karsilastir(son, k, bek, plan, once)
                if r["PASS"]: break
                log(f"   geri okuma {d + 1}/4 henuz birebir degil: {r['hata']}")
            r.update(listing_id=lid, cift=c, api=api.calls - c1, link=f"https://www.etsy.com/listing/{lid}")
            (rap_yol / f"{c}_sonra.json").write_text(json.dumps(son, indent=1, ensure_ascii=False), encoding="utf-8")
        (rap_yol / f"{c}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        g = time.time() - t0
        log(f"[{i}/{len(is_)}] {c} {'PASS' if r['PASS'] else 'FAIL'} {r['hata']} | API {r['api']} | gecen {g/60:.1f} dk | "
            f"kalan ~{g/i*(len(is_)-i)/60:.1f} dk | %{100*i//len(is_)} | kota {api.remaining} | https://www.etsy.com/listing/{lid}")
        if not r["PASS"]:
            if r["hata"].startswith("YAZILMADI"):          # denetim FAIL: o ilana yazilmadi, listelenir, digerlerine devam (Merkez 11 Eki)
                log(f"ATLANDI (denetim FAIL, yazilmadi): {c} {r['hata']}"); continue
            log(f"DUR: {c} yazim sonrasi geri okuma FAIL"); break
    rows = [json.loads(p.read_text()) for p in sorted(rap_yol.glob("*.json")) if not p.stem.endswith("_sonra")]
    with open(out / "52_YAZIM_RAPORU.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "baslik_ok", "etiket_ok", "aciklama_ok", "nitelik_ok", "hata"])
        for r in sorted(rows, key=lambda x: x["cift"]):
            w.writerow([r["listing_id"], r["cift"], r["baslik_ok"], r["etiket_ok"], r["aciklama_ok"], r["nitelik_ok"], r["hata"]])
    n = sum(1 for r in rows if r["PASS"])
    atla = [r["cift"] for r in rows if not r["PASS"] and r["hata"].startswith("YAZILMADI")]
    log(f"OZET yaz: toplam rapor {len(rows)} | PASS {n} | yazilmadi (denetim FAIL) {len(atla)} {atla} | bu kosu API {api.calls - c0} | kota {api.remaining}")
    return 0 if all(r["PASS"] for r in rows) and rows else 1


if __name__ == "__main__":
    sys.exit(main())
