#!/usr/bin/env python3
"""SADE KUPA (tek burc) Etsy YENI TASLAK (Gorev 20261101G, Serdar 1 Kas 2026). YAYIN YOK.

Kurallar (Serdar 1 Kas):
- Ayarlar YALNIZ sablon taslak 4607523667'den OKUNUR; sablona yazma / silme YOK.
- Yeni ilan createDraftListing ile acilir. updateListing / PATCH HIC YOK (yeni taslakta da); PATCH ile yazilabilen alanlar
  rapora "Serdar elle girecek" + deger olarak yazilir. DELETE yok.
- Her adimdan sonra state okunur; draft degilse DUR (duzeltme denemesi yok) ve rapor.
- Kota: kosu basinda okunur; ilan basina pay kapisi: kalan < PAY + KOTA_SINIRI ise o ilan baslamaz (rc 4). KOTA_SINIRI 10.
- Ikinci kosu ikinci ilan acmaz: DURUM.json (burc -> listing_id) + ayni baslikli taslak aramasi.

Metin: SEO_CSV (kupa_orchard/ilan/SADE12_SEO_ONERI.csv: kod, baslik, etiketler, aciklama, alt) +
       METIN_CSV (kupa_orchard/ilan/SADE12_METIN.csv: kod, kisisellestirme_talimati).
Medya: IMG_ROOT/<BURC>/ 01-14 (asagidaki dosya adlari) + SADE_VIDEO_<BURC>.mp4; MANIFEST (SADE12_MANIFEST.tsv) sha256 kapisi
       (kapak, 8 stil, video); manifestte olmayan kartlar boyut / cozunurluk olarak rapora.
Cikti: OUT/SABLON_<id>.json (sablon yedegi), OUT/SADE_TASLAK_<BURC>.json, OUT/DURUM.json
Cikis kodu: 0 tamam, 1 FAIL/DUR, 4 kota payi yetmedi (o burc ve sonrasi baslamadi).
"""
import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
from etsy_common import API, KOTA_SINIRI, Etsy, TokenStore, ai_beyan_kapisi, beyan_var, mask  # noqa: E402

SABLON = 4607523667                 # Serdar'in kopyaladigi taslak: YALNIZ OKUNUR
YAZMA_YASAK = {SABLON, 4597843405, 4598525642}
BOLUM_AD = "Zodiac Sign Mugs"
BURCLAR = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN",
           "AQUARIUS", "PISCES"]
# (menu adi, dosya eki, galeri sirasi); Orange -> 07 ... Loquat -> 14 (Gorev G madde 3)
STILLER = [("Orange Blossom", "07_ORANGE", 7), ("Purple Fig", "08_FIG", 8), ("Olive Breeze", "09_OLIVE", 9),
           ("Pomegranate Bloom", "10_POMEGRANATE", 10), ("Almond Blossom", "11_ALMOND", 11), ("Lemon Grove", "12_LEMON", 12),
           ("Blue Grape", "13_GRAPE", 13), ("Golden Loquat", "14_LOQUAT", 14)]
BOYLAR = [("11 oz", 12.90), ("15 oz", 16.90)]
N_URUN = len(STILLER) * len(BOYLAR)
N_GORSEL = 14
STOK = 999
SORU_METNI = "Personalization"
SORU_MAX = 256
TALIMAT_MAX = 120                   # Etsy paneli talimat siniri (kupa_taslak 19 Eki olcumu)
ALT_MAX = 250
PAY = 75                            # ilan basina istek payi (kuru sayim + yeniden okuma payi); kalan < PAY + KOTA_SINIRI -> baslamaz
AI_EN = "We use AI tools to help create the artwork"
TIRE = re.compile("[–—]")
# sablondan yeni ilana tasinan createDraftListing alanlari (deger sablondan; None/bos ise gonderilmez)
KOPYA = ["who_made", "when_made", "taxonomy_id", "shipping_profile_id", "return_policy_id", "is_supply", "should_auto_renew",
         "is_taxable", "is_customizable"]
# olcu alanlari yalniz sablonda dolu ise (birim + deger birlikte); processing_* gonderilmez (readiness_state_id kullanilir)
OLCU = [(("item_weight",), "item_weight_unit"), (("item_length", "item_width", "item_height"), "item_dimensions_unit")]
# PATCH-yalniz alan karsilastirmasinda yok sayilan (beklenen fark / kimlik / zaman / sayac) anahtarlar
FARK_DISI = {"listing_id", "user_id", "shop_id", "title", "description", "tags", "state", "creation_timestamp", "created_timestamp",
             "ending_timestamp", "original_creation_timestamp", "last_modified_timestamp", "updated_timestamp",
             "state_timestamp", "url", "views", "num_favorers", "price", "quantity", "skus", "featured_rank", "shop_section_id",
             "has_variations", "file_data", "non_taxable", "images", "videos", "inventory", "production_partners",
             "personalization_instructions", "personalization_is_required", "personalization_char_count_max", "is_personalizable",
             "translations", "views_count", "image_ids", "user", "shop", "shipping_profile", "shipping_upgrades"}


def dosyalar(b):
    return ([f"SADE_KAPAK_{b}.jpg", f"SADE_{b}_K02_SEMBOL.jpg", f"SADE_{b}_K03_KISISEL.jpg", f"SADE_{b}_K05_BOYUT.jpg",
             f"SADE_{b}_K07_SUREC.jpg", f"SADE_{b}_K04_STIL.jpg"] + [f"SADE_STIL_{b}_{ek}.jpg" for _, ek, _ in STILLER],
            f"SADE_VIDEO_{b}.mp4")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blok in iter(lambda: fh.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def para(p):
    if isinstance(p, dict) and p.get("divisor"):
        return round(p["amount"] / p["divisor"], 2)
    return p


def satir(yol, b):
    r = [x for x in csv.DictReader(open(yol, encoding="utf-8")) if x.get("kod") == b]
    if len(r) != 1:
        raise SystemExit(f"DUR: {yol} icinde {b} satiri {len(r)} (1 olmali)")
    return r[0]


def metin(b):
    s, m = satir(os.environ["SEO_CSV"], b), satir(os.environ["METIN_CSV"], b)
    title, desc = s["baslik"], s["aciklama"]
    tags = [t.strip() for t in s["etiketler"].split(",")]
    inst = m["kisisellestirme_talimati"]
    altlar = {}
    for l in [x for x in s["alt"].split("\n") if x.strip()]:
        mm = re.match(r"^(\d\d) [^:]+: (.+)$", l.strip())
        if mm:
            altlar[int(mm.group(1))] = mm.group(2).strip()
    hata = []
    if sorted(altlar) != list(range(1, N_GORSEL + 1)):
        hata.append(f"alt metin sirasi {sorted(altlar)}")
    if any(len(a) > ALT_MAX for a in altlar.values()):
        hata.append(f"alt metin > {ALT_MAX}")
    if TIRE.search(title + desc + " ".join(tags) + inst + " ".join(altlar.values())):
        hata.append("uzun/orta tire var")
    if len(title) > 140:
        hata.append(f"baslik {len(title)} > 140")
    if len(tags) != 13 or len(set(tags)) != 13 or any(len(t) > 20 for t in tags):
        hata.append(f"etiket {len(tags)} / tekil {len(set(tags))} / max {max(len(t) for t in tags)}")
    if not re.fullmatch(r"[A-Za-z0-9 ]+", "".join(tags)):
        hata.append("etikette harf/rakam/bosluk disi karakter")
    if len(inst) > TALIMAT_MAX:
        hata.append(f"talimat {len(inst)} > {TALIMAT_MAX}")
    if not beyan_var(desc, "en") or AI_EN not in desc:
        hata.append("aciklamada AI beyani yok")
    if "AstroLove " in desc.replace("AstroLoveArt", ""):
        hata.append("aciklamada yalniz 'AstroLove'")
    yok = [ad for ad, *_ in STILLER if ad not in desc]
    if yok:
        hata.append(f"aciklamada gecmeyen stil {yok}")
    return dict(title=title, desc=desc, tags=tags, inst=inst, alt=altlar, hata=hata)


def medya(b):
    kok = Path(os.environ["IMG_ROOT"]) / b
    gl, vid = dosyalar(b)
    galeri = [kok / g for g in gl]
    video = kok / vid
    eksik = [p.name for p in galeri + [video] if not p.is_file()]
    if eksik:
        return galeri, video, [f"eksik dosya {eksik}"], {}
    man = {}
    for l in Path(os.environ["MANIFEST"]).read_text().splitlines():
        if "\t" in l:
            h, ad = l.split("\t", 1)
            man[ad.strip()] = h.strip()
    hata, bilgi = [], {}
    for p in galeri + [video]:
        anahtar = f"{b}/{p.name}"
        s_ = sha(p)
        if anahtar in man:
            bilgi[p.name] = dict(sha=s_[:16], manifest="ESIT" if man[anahtar] == s_ else "FARKLI")
            if man[anahtar] != s_:
                hata.append(f"sha manifestle farkli {p.name}")
        else:
            d = dict(sha=s_[:16], manifest="YOK", bayt=p.stat().st_size)
            try:
                from PIL import Image
                with Image.open(p) as im:
                    d["boyut"] = im.size
            except Exception as e:  # noqa: BLE001
                d["boyut"] = f"okunamadi {type(e).__name__}"
            bilgi[p.name] = d
    return galeri, video, hata, bilgi


class Kilitli(Etsy):
    """Izinli yazmalar: createDraftListing, (yoksa) createShopSection BOLUM_AD, ve YALNIZ yeni taslagin alt uclari.
    PATCH ve DELETE hic yok. Sablon / yasak ilanlara yazma yok. Her istekten once kota sert tabani (etsy_common)."""
    lid = None

    def _izin(self, method, path, data=None):
        if method in ("PATCH", "DELETE"):
            raise SystemExit(f"YASAK: {method} {path} (Gorev G: PATCH / DELETE yok)")
        if any(re.search(rf"/listings/{e}(/|$)", path) for e in YAZMA_YASAK):
            raise SystemExit(f"YASAK yazma (sablon / dokunulmaz ilan): {method} {path}")
        ok = [("POST", r"^/shops/\d+/listings$")]
        if re.match(r"^/shops/\d+/sections$", path):
            if method == "POST" and (data or {}).get("title") == BOLUM_AD:
                return
            raise SystemExit(f"YASAK: bolum yazimi yalniz '{BOLUM_AD}' olusturma: {method} {path} {data}")
        if self.lid:
            L = self.lid
            ok += [("PUT", rf"^/listings/{L}/inventory$"), ("POST", rf"^/shops/\d+/listings/{L}/images$"),
                   ("POST", rf"^/shops/\d+/listings/{L}/videos$"), ("POST", rf"^/shops/\d+/listings/{L}/variation-images$"),
                   ("POST", rf"^/shops/\d+/listings/{L}/personalization$"), ("PUT", rf"^/shops/\d+/listings/{L}/properties/\d+$")]
        if not any(m == method and re.match(p, path) for m, p in ok):
            raise SystemExit(f"YASAK yazma: {method} {path}")

    def _call(self, method, path, params=None, data=None, ok404=False, json_body=None):
        if method != "GET":
            self._izin(method, path, data)
        return super()._call(method, path, params=params, data=data, ok404=ok404, json_body=json_body)

    def post_file(self, path, files, data=None, tekrar=1):
        self._izin("POST", path)
        return super().post_file(path, files, data, tekrar=1)   # tekrar yok: cift yukleme riski; cagiran galeriyi okur

    def patch(self, *a, **k):
        raise SystemExit("YASAK: PATCH (Gorev G)")

    def delete(self, *a, **k):
        raise SystemExit("YASAK: DELETE (Gorev G)")

    def taslak_olustur(self, shop, body):
        """createDraftListing: TEK gonderim (tekrar ikinci ilan acabilir). -> (status, json|None, metin)."""
        self._izin("POST", f"/shops/{shop}/listings")
        ai_beyan_kapisi("POST", f"/shops/{shop}/listings", data=body)
        self._istek_oncesi()
        self.calls += 1
        r_ = requests.post(API + f"/shops/{shop}/listings", data=body, headers=self._headers(), timeout=120)
        self.remaining = r_.headers.get("x-remaining-today", self.remaining)
        return r_.status_code, (r_.json() if r_.status_code in (200, 201) else None), r_.text[:400]


def sablon_oku(api, shop, out):
    """Sablon 4607523667: YALNIZ GET. Yedek OUT/SABLON_<id>.json (Drive TEMP altina kopyalanir)."""
    S = SABLON
    L = api.get(f"/listings/{S}", params={"includes": "Images,Videos,Inventory"}) or {}
    inv = L.get("inventory") or api.get(f"/listings/{S}/inventory") or {}
    props = (api.get(f"/shops/{shop}/listings/{S}/properties") or {}).get("results") or []
    per = (api.get(f"/listings/{S}/personalization", ok404=True) or {})
    Y = dict(okuma_zamani=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), listing=L, inventory=inv, properties=props,
             personalization=per)
    json.dump(Y, open(out / f"SABLON_{S}.json", "w"), indent=1, ensure_ascii=False, default=str)
    ps = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            ps.setdefault((v.get("property_id"), v.get("property_name")), set()).update(v.get("values") or [])
    stil = [k for k in ps if (k[1] or "").strip().lower() == "style"]
    boy = [k for k in ps if (k[1] or "").strip().lower() == "size"]
    rs = sorted({o.get("readiness_state_id") for p in inv.get("products") or [] for o in p.get("offerings") or []
                 if o.get("readiness_state_id")})
    hata = []
    if len(stil) != 1 or len(boy) != 1:
        hata.append(f"sablon envanterinde Style/Size ozelligi {list(ps)}")
    if len(rs) != 1:
        hata.append(f"sablon readiness_state_id {rs} (tek olmali)")
    if L.get("taxonomy_id") is None or L.get("shipping_profile_id") is None:
        hata.append("sablonda taxonomy / kargo profili yok")
    ai_anahtar = {k: v for k, v in L.items() if re.search(r"(^|_)ai(_|$)|ai_generated|how_it|made_by|creation_method", k, re.I)}
    return dict(L=L, props=props, per=per, P_STYLE=stil[0][0] if stil else None, P_SIZE=boy[0][0] if boy else None,
                stil_degerleri=sorted(ps.get(stil[0], [])) if stil else [], boy_degerleri=sorted(ps.get(boy[0], [])) if boy else [],
                readiness=rs[0] if len(rs) == 1 else None, hata=hata, ai_anahtar=ai_anahtar,
                ozet=dict(state=L.get("state"), taxonomy_id=L.get("taxonomy_id"), shipping_profile_id=L.get("shipping_profile_id"),
                          return_policy_id=L.get("return_policy_id"), who_made=L.get("who_made"), when_made=L.get("when_made"),
                          materials=L.get("materials"), production_partners=L.get("production_partners"),
                          shop_section_id=L.get("shop_section_id"), readiness=rs, urun=len(inv.get("products") or []),
                          nitelik=[(p.get("property_name"), p.get("values")) for p in props],
                          kisisellestirme=per.get("personalization_questions") if isinstance(per, dict) else None))


def bolum_bul(api, shop, olustur):
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    v = [x for x in secs if (x.get("title") or "").strip() == BOLUM_AD]
    if v:
        return v[0]["shop_section_id"], "VAR"
    if not olustur:
        return None, "YOK"
    api.post(f"/shops/{shop}/sections", {"title": BOLUM_AD})
    secs = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    v = [x for x in secs if (x.get("title") or "").strip() == BOLUM_AD]
    if not v:
        raise SystemExit(f"DUR: '{BOLUM_AD}' bolumu olusturuldu ama okunamadi")
    return v[0]["shop_section_id"], "OLUSTURULDU"


def taslaklar(api, shop):
    out, off = [], 0
    while off < 1000:
        r = (api.get(f"/shops/{shop}/listings", params={"state": "draft", "limit": 100, "offset": off}) or {}).get("results") or []
        out += r
        if len(r) < 100:
            break
        off += 100
    return out


def yaz(api, shop, out, b, SB, bolum_id, D):
    R = {"burc": b, "adimlar": [], "olusturma": None}
    rapor_f = out / f"SADE_TASLAK_{b}.json"
    durum_f = out / "DURUM.json"

    def kaydet():
        json.dump(D, open(durum_f, "w"), indent=1)
        json.dump(R, open(rapor_f, "w"), indent=1, ensure_ascii=False, default=str)

    M = metin(b)
    R["metin"] = dict(baslik_kr=len(M["title"]), etiket=len(M["tags"]), talimat_kr=len(M["inst"]),
                      alt_max=max(len(a) for a in M["alt"].values()) if M["alt"] else None, hata=M["hata"])
    galeri, video, mhata, bilgi = medya(b)
    R["medya"] = bilgi
    if M["hata"] or mhata:
        kaydet(); raise SystemExit(f"DUR: {b} metin {M['hata']} medya {mhata}")
    R["kota_bas"] = api.remaining
    P_STYLE, P_SIZE, READY = SB["P_STYLE"], SB["P_SIZE"], SB["readiness"]
    L0 = SB["L"]

    def state_oku(adim):
        L = None
        for i in range(6):
            L = api.get(f"/listings/{api.lid}", ok404=True)
            if L:
                break
            time.sleep(5 * (i + 1))
        if not L:
            kaydet(); raise SystemExit(f"DUR: /listings/{api.lid} okunamadi ({adim})")
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining))
        print(f"{b} {adim}: state={st} kota={api.remaining}", flush=True)
        if st != "draft":
            kaydet()
            print(f"::error::{b} {adim} sonrasi state={st} (draft degil). DUR; duzeltme yazimi yapilmadi (PATCH yok).")
            raise SystemExit(2)
        return L

    lid = D["burclar"].get(b)
    if lid in YAZMA_YASAK:
        kaydet(); raise SystemExit(f"DUR: DURUM.json {b} = yasak ilan {lid}")
    if not lid:
        ayni = [x["listing_id"] for x in taslaklar(api, shop) if x.get("title") == M["title"] and x["listing_id"] not in YAZMA_YASAK]
        if len(ayni) > 1:
            kaydet(); raise SystemExit(f"DUR: ayni baslikli {len(ayni)} taslak {ayni}; hangisine yazilacagi belirsiz")
        lid = ayni[0] if ayni else None
    if lid:
        R["olusturma"] = f"VAR OLAN TASLAK {lid} (ikinci ilan acilmadi)"
    else:
        body = {"quantity": STOK, "title": M["title"], "description": M["desc"], "price": BOYLAR[0][1], "type": "physical",
                "readiness_state_id": READY, "shop_section_id": bolum_id, "tags": ",".join(M["tags"]),
                "materials": ",".join(L0.get("materials") or []),
                "production_partner_ids": ",".join(str(p.get("production_partner_id")) for p in L0.get("production_partners") or [])}
        for k in KOPYA:
            v = L0.get(k)
            if v is None or v == "":
                continue
            body[k] = str(v).lower() if isinstance(v, bool) else v
        for degerler, birim in OLCU:
            if all(L0.get(x) for x in degerler) and L0.get(birim):
                body.update({x: L0[x] for x in degerler}); body[birim] = L0[birim]
        body = {k: v for k, v in body.items() if v not in (None, "")}
        R["olusturma_govde_anahtar"] = sorted(body)
        kod, js, mt = api.taslak_olustur(shop, body)
        if kod not in (200, 201):
            ayni = [x["listing_id"] for x in taslaklar(api, shop) if x.get("title") == M["title"] and x["listing_id"] not in YAZMA_YASAK]
            if ayni:
                D["burclar"][b] = ayni[0]
            kaydet()
            raise SystemExit(f"DUR: createDraftListing {kod}: {mt} | ayni baslikli taslak: {ayni}")
        lid = js.get("listing_id")
        R["olusturma"] = "yeni taslak (createDraftListing, tek POST)"
    api.lid = lid
    D["burclar"][b] = lid; kaydet()
    print(f"::warning::{b} listing_id {lid}")
    state_oku("1 olusturma")

    # 2) envanter: Style x Size = 16, fiyat yalniz boya gore, SKU BOS, stok 999
    def urunler():
        return [dict(sku="", property_values=[dict(property_id=P_STYLE, property_name="Style", values=[ad]),
                                              dict(property_id=P_SIZE, property_name="Size", values=[bad])],
                     offerings=[dict(price=fiyat, quantity=STOK, is_enabled=True, readiness_state_id=READY)])
                for ad, *_ in STILLER for bad, fiyat in BOYLAR]
    inv = api.get(f"/listings/{lid}/inventory") or {}
    if len(inv.get("products") or []) != N_URUN:
        api.put_json(f"/listings/{lid}/inventory", dict(products=urunler(), price_on_property=[P_STYLE, P_SIZE],
                                                        quantity_on_property=[], sku_on_property=[], readiness_state_on_property=[]))
    state_oku("2 envanter")

    # 3) 14 gorsel (sirayla, alt metinli)
    have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images") or {}).get("results") or [])}
    t0 = time.time()
    for rk, p in enumerate(galeri, 1):
        if rk in have:
            continue
        with open(p, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, "image/jpeg")},
                          data={"rank": str(rk), "alt_text": M["alt"][rk]})
        g = time.time() - t0
        print(f"{b} gorsel [{rk}/{N_GORSEL}] {p.name} | gecen {g:.0f} sn | kalan ~{g / rk * (N_GORSEL - rk):.0f} sn | "
              f"%{100 * rk // N_GORSEL}", flush=True)
    state_oku("3 gorseller")

    # 4) video
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    if not vids:
        with open(video, "rb") as fh:
            api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": ("video.mp4", fh, "video/mp4")},
                          data={"name": f"AstroLoveArt_{b}_mug_video.mp4"})
    state_oku("4 video")

    # 5) stil -> stil gorseli (07-14)
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    rank_id = {x.get("rank"): x.get("listing_image_id") for x in ims}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vid = {v["values"][0]: v["value_ids"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
           if v.get("property_id") == P_STYLE and v.get("value_ids")}
    if sorted(vid) != sorted(a for a, *_ in STILLER) or any(rank_id.get(rk) is None for *_, rk in STILLER):
        kaydet(); raise SystemExit(f"DUR: Style value_id {sorted(vid)} / rank {sorted(rank_id)}")
    vi = [dict(property_id=P_STYLE, value_id=vid[ad], image_id=rank_id[rk]) for ad, _, rk in STILLER]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
    state_oku("5 stil gorselleri")

    # 6) kisisellestirme: tek kutu, zorunlu, 256, talimat
    Q = [dict(question_text=SORU_METNI, question_type="text_input", required=True, max_allowed_characters=SORU_MAX,
              instructions=M["inst"])]
    api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": Q})
    state_oku("6 kisisellestirme")

    # 7) nitelikler: sablondaki her nitelik aynen
    for p_ in SB["props"]:
        ids = [str(i) for i in p_.get("value_ids") or []]
        vals = p_.get("values") or []
        if not ids and not vals:
            continue
        d = {"values": ",".join(vals)}
        if ids:
            d["value_ids"] = ",".join(ids)
        if p_.get("scale_id"):
            d["scale_id"] = str(p_["scale_id"])
        api.put(f"/shops/{shop}/listings/{lid}/properties/{p_['property_id']}", d)
    state_oku("7 nitelikler")

    # 8) geri okuma
    for _ in range(4):
        ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
        vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
        if all(x.get("full_width") for x in ims) and vids:
            break
        time.sleep(10)
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images") or {}).get("results") or []
    tablo = []
    for p in inv.get("products") or []:
        pv = {v.get("property_id"): (v.get("values") or [None])[0] for v in p.get("property_values") or []}
        o = (p.get("offerings") or [{}])[0]
        tablo.append((pv.get(P_STYLE), pv.get(P_SIZE), para(o.get("price")), o.get("quantity"), p.get("sku") or "",
                      o.get("is_enabled"), o.get("readiness_state_id")))
    bek_tablo = [(ad, bad, fiyat, STOK, "", True, READY) for ad, *_ in STILLER for bad, fiyat in BOYLAR]
    id_rank = {x.get("listing_image_id"): x.get("rank") for x in ims}
    vid2 = {v["value_ids"][0]: v["values"][0] for p in inv.get("products") or [] for v in p.get("property_values") or []
            if v.get("property_id") == P_STYLE and v.get("value_ids")}
    bag = {vid2.get(v.get("value_id")): id_rank.get(v.get("image_id")) for v in vis if v.get("property_id") == P_STYLE}
    alt_bek = {rk: M["alt"][rk] for rk in range(1, N_GORSEL + 1)}
    alt_can = {x.get("rank"): (x.get("alt_text") or "") for x in ims}
    pp = lambda X: sorted(p_.get("production_partner_id") for p_ in X.get("production_partners") or [])  # noqa: E731
    K = {
        "state draft": L.get("state") == "draft",
        "baslik CSV ile birebir": L.get("title") == M["title"],
        "aciklama CSV ile birebir (AI beyanli)": html.unescape(L.get("description") or "").strip() == M["desc"].strip()
        and beyan_var(L.get("description"), "en"),
        "13 etiket CSV ile birebir": sorted(L.get("tags") or []) == sorted(M["tags"]) and len(L.get("tags") or []) == 13,
        f"{N_URUN} secenek: fiyat 12.90/16.90, stok {STOK}, SKU bos": sorted(tablo) == sorted(bek_tablo) and len(tablo) == N_URUN,
        f"{N_GORSEL} gorsel 1-{N_GORSEL} sirada": [x.get("rank") for x in ims] == list(range(1, N_GORSEL + 1)),
        "alt metinler CSV ile birebir": alt_can == alt_bek,
        "video 1": len(vids) == 1,
        "8 stil kendi gorseline (07-14)": bag == {ad: rk for ad, _, rk in STILLER},
        "kisisellestirme zorunlu, 256, talimat": len(per) == 1 and per[0].get("required") is True
        and per[0].get("max_allowed_characters") == SORU_MAX and (per[0].get("instructions") or "") == M["inst"]
        and per[0].get("question_type") == "text_input",
        f"bolum {BOLUM_AD}": L.get("shop_section_id") == bolum_id,
        "kargo / iade / uretim ortagi sablonla ayni": (L.get("shipping_profile_id"), L.get("return_policy_id"), pp(L))
        == (L0.get("shipping_profile_id"), L0.get("return_policy_id"), pp(L0)),
        "who_made / when_made / kategori / malzeme sablonla ayni": (L.get("who_made"), L.get("when_made"), L.get("taxonomy_id"),
                                                                     sorted(L.get("materials") or []))
        == (L0.get("who_made"), L0.get("when_made"), L0.get("taxonomy_id"), sorted(L0.get("materials") or [])),
        "nitelikler sablonla ayni": sorted((p_.get("property_id"), tuple(p_.get("value_ids") or []), tuple(p_.get("values") or []))
                                          for p_ in props)
        == sorted((p_.get("property_id"), tuple(p_.get("value_ids") or []), tuple(p_.get("values") or []))
                  for p_ in SB["props"] if p_.get("value_ids") or p_.get("values")),
    }
    elle = {k: dict(sablon=v, yeni=L.get(k)) for k, v in L0.items() if k not in FARK_DISI and L.get(k) != v}
    R["kontrol"] = K
    R["serdar_elle_girecek"] = elle
    R["ai_how_its_made"] = dict(sablon={k: L0.get(k) for k in SB["ai_anahtar"]},
                                yeni={k: L.get(k) for k in L if re.search(r"(^|_)ai(_|$)|ai_generated|how_it|creation_method", k, re.I)},
                                not_="Etsy API v3 'How it's made' alanini dondurmuyorsa burasi bos kalir; panelden kontrol")
    R["son"] = dict(listing_id=lid, state=L.get("state"), link=f"https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}",
                    tablo=tablo, bag=bag, gorsel=[(x.get("rank"), x.get("full_width"), x.get("full_height")) for x in ims],
                    video=[(v.get("video_id"), v.get("video_state")) for v in vids], kisisellestirme=per,
                    nitelik=[(p_.get("property_name"), p_.get("values")) for p_ in props], bolum=L.get("shop_section_id"))
    R["kota_son"] = api.remaining
    R["istek"] = api.calls
    kaydet()
    kotu = [k_ for k_, v_ in K.items() if not v_]
    print(f"::warning::{b} TASLAK {lid} state={L.get('state')} | kontrol {len(K) - len(kotu)}/{len(K)} PASS | FAIL {kotu} | "
          f"elle {sorted(elle)} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        raise SystemExit(f"FAIL kontrol {b}: {kotu}")
    if b not in D.setdefault("tamam", []):
        D["tamam"].append(b); kaydet()
    return R


def kos(api, shop, out, burclar):
    durum_f = out / "DURUM.json"
    D = json.load(open(durum_f)) if durum_f.exists() else {}
    D.setdefault("burclar", {}); D.setdefault("tamam", [])
    api.get(f"/shops/{shop}")
    print(f"kota basta {api.remaining} | pay ilan basina {PAY} + taban {KOTA_SINIRI}")
    SB = sablon_oku(api, shop, out)
    print(f"sablon {SABLON}: {json.dumps(SB['ozet'], ensure_ascii=False, default=str)[:1500]}")
    if SB["hata"]:
        raise SystemExit(f"DUR: sablon {SB['hata']}")
    bolum_id, bolum_durum = bolum_bul(api, shop, olustur=True)
    print(f"bolum {BOLUM_AD}: {bolum_id} ({bolum_durum})")
    t0 = time.time()
    ozet = dict(sablon=SB["ozet"], bolum=(bolum_id, bolum_durum), sablon_stil=SB["stil_degerleri"], sablon_boy=SB["boy_degerleri"],
                burclar={})
    for i, b in enumerate(burclar, 1):
        api.lid = None
        if b in D["tamam"]:
            ozet["burclar"][b] = f"ATLANDI: tamam ({D['burclar'].get(b)})"; continue
        if api.remaining is not None and int(api.remaining) < PAY + KOTA_SINIRI:
            ozet["burclar"][b] = f"BASLAMADI: kota {api.remaining} < pay {PAY} + {KOTA_SINIRI}"
            json.dump(ozet, open(out / "OZET.json", "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::warning::KOTA: {b} ve sonrasi baslamadi (kalan {api.remaining})")
            return 4
        try:
            R = yaz(api, shop, out, b, SB, bolum_id, D)
            ozet["burclar"][b] = dict(listing_id=R["son"]["listing_id"], kontrol=f"{sum(R['kontrol'].values())}/{len(R['kontrol'])}",
                                      elle=sorted(R["serdar_elle_girecek"]))
        except BaseException as e:  # noqa: BLE001
            ozet["burclar"][b] = f"HATA {type(e).__name__}: {e}"[:800]
            json.dump(ozet, open(out / "OZET.json", "w"), indent=1, ensure_ascii=False, default=str)
            print(f"::error::{b} {ozet['burclar'][b]}")
            raise
        g = time.time() - t0
        print(f"ETA [{i}/{len(burclar)}] {b} | gecen {g / 60:.1f} dk | kalan ~{g / i * (len(burclar) - i) / 60:.1f} dk | "
              f"%{100 * i // len(burclar)} | kota {api.remaining}", flush=True)
    ozet["kota_son"], ozet["istek"] = api.remaining, api.calls
    json.dump(ozet, open(out / "OZET.json", "w"), indent=1, ensure_ascii=False, default=str)
    return 0


def burc_listesi(g):
    s = BURCLAR if g.strip().upper() == "TUMU" else [x.strip().upper() for x in re.split(r"[,\s]+", g) if x.strip()]
    bad = [x for x in s if x not in BURCLAR]
    if bad or not s:
        raise SystemExit(f"DUR: bilinmeyen burc {bad}")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--burclar", default="ARIES")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--liste", help="indirme listesi yaz (Etsy yok): <dizin>/a.txt (kapak, 8 stil, video) + k.txt (5 kart)")
    ap.add_argument("--liste-dizin", default="_w")
    a = ap.parse_args()
    if a.liste:
        b = burc_listesi(a.liste)[0]
        g, v = dosyalar(b)
        kart = [x for x in g if "_K0" in x]
        Path(a.liste_dizin, "a.txt").write_text("".join(x + "\n" for x in g if x not in kart) + v + "\n")
        Path(a.liste_dizin, "k.txt").write_text("".join(x + "\n" for x in kart))
        return
    if a.confirm != "SADE_TASLAK":
        raise SystemExit("DUR: --confirm SADE_TASLAK yok (Etsy'ye yazar)")
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    bl = burc_listesi(a.burclar)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    sys.exit(kos(Kilitli(store), os.environ["ETSY_SHOP_ID"], out, bl))


if __name__ == "__main__":
    main()
