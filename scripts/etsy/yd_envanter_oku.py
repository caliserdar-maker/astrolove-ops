#!/usr/bin/env python3
"""YD (1st Anniversary / Bizim Yilimiz) SALT OKUMA envanteri (Merkez 26 Eki; galeri plani icin). ETSY'YE YAZMA YOK.

Ilan listesi: --liste (BY78_TASLAKLAR.csv; Drive TEMP/BY78_TASLAK_20261014, by78-denetim.yml:47 ile ayni kaynak; sutun listing_id, cift).
Ilan basina 5 GET: listing, images, inventory, variation-images, videos (+ pilotta personalization 1 GET). Ilan basina kota kapisi.
Yazma yontemleri kapali (put/patch/post/delete + _call GET disi DUR).
Cikti: <out>/PILOT_<id>.json (tam), YD_OZET.csv, FARKLI.csv (pilotla ayni yapida olmayanlar), HAM/<id>.json (ham yanitlar)."""
import argparse
import csv
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402

SATIR_RX = re.compile(r"\b(style|styles|photo|photos|image|images|picture|pictures|shown|gallery|preview|colou?rs?|looks?|effects?)\b", re.I)


def para(p):
    return round(p["amount"] / p["divisor"], 2) if isinstance(p, dict) else p


def salt_okur(api):
    def yok(*a, **k):
        raise SystemExit("DUR: salt okuma kosusunda Etsy yazma cagrisi")
    for ad in ("put", "patch", "post", "put_json", "post_json", "post_file", "delete"):
        setattr(api, ad, yok)
    asil = api._call

    def yalniz_get(method, path, *a, **k):
        if str(method).upper() != "GET":
            raise SystemExit(f"DUR: salt okuma kosusunda {method} {path}")
        return asil(method, path, *a, **k)
    api._call = yalniz_get


def oku(api, shop, lid, pilot=False):
    x = api.get(f"/listings/{lid}") or {}
    img = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [], key=lambda y: y.get("rank") or 0)
    inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
    vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    vid = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    pers = api.get(f"/listings/{lid}/personalization", ok404=True) if pilot else None
    return dict(listing=x, images=img, inventory=inv, variation_images=vi, videos=vid, personalization=pers)


def yapi(h):
    x, img, inv, vi, vid = h["listing"], h["images"], h["inventory"], h["variation_images"], h["videos"]
    pr = inv.get("products") or []
    ozellik = {}                                   # property_id -> {ad, secenekler (sirali, birebir), value_ids}
    fiyat = {}                                     # (property ad, secenek) -> [fiyatlar]
    for p in pr:
        for v in p.get("property_values") or []:
            o = ozellik.setdefault(v.get("property_id"), dict(ad=v.get("property_name"), secenekler=[], value_ids={}))
            for val, vid_ in zip(v.get("values") or [], (v.get("value_ids") or []) + [None] * 9):
                if val not in o["secenekler"]:
                    o["secenekler"].append(val); o["value_ids"][val] = vid_
                for off in p.get("offerings") or []:
                    fiyat.setdefault((v.get("property_name"), val), []).append(para(off.get("price")))
    bag = {}                                       # property_id -> {secenek: image_id}
    for b in vi:
        bag.setdefault(b.get("property_id"), {})[b.get("value")] = b.get("image_id")
    gids = {g.get("listing_image_id") for g in img}
    stil_pid = next(iter(bag), None)
    if stil_pid is None:                           # bag yoksa: 'Style' adli ozellik
        stil_pid = next((k for k, o in ozellik.items() if (o["ad"] or "").lower() in ("style", "stil", "design")), None)
    stil = ozellik.get(stil_pid) or {}
    adlar = [a_ for o in ozellik.values() for a_ in o["secenekler"] if a_]
    satir = [s_ for s_ in (x.get("description") or "").replace("\r\n", "\n").split("\n")
             if SATIR_RX.search(s_) or any(a_ in s_ for a_ in adlar)]
    return dict(
        listing_id=x.get("listing_id"), state=x.get("state"), title=x.get("title"), urun=len(pr),
        fiyat_aralik=[min(f for v in fiyat.values() for f in v), max(f for v in fiyat.values() for f in v)] if fiyat else None,
        fiyat_secenek={f"{k[0]}: {k[1]}": [min(v), max(v)] for k, v in fiyat.items()},
        gorseller=[{k: g.get(k) for k in ("rank", "listing_image_id", "full_width", "full_height", "alt_text", "url_fullxfull")} for g in img],
        gorsel_sayisi=len(img), kapak=({k: img[0].get(k) for k in ("listing_image_id", "full_width", "full_height")} if img else None),
        ozellikler=[dict(property_id=k, ad=o["ad"], secenekler=o["secenekler"], value_ids=o["value_ids"]) for k, o in ozellik.items()],
        foto_bag_ozelligi=[dict(property_id=k, ad=(ozellik.get(k) or {}).get("ad")) for k in bag],
        stil_ozelligi=stil.get("ad"), stil_secenekleri=stil.get("secenekler") or [],
        stil_bag={s_: (bag.get(stil_pid) or {}).get(s_) for s_ in stil.get("secenekler") or []},
        bagli_secenek=sum(1 for s_ in stil.get("secenekler") or [] if (bag.get(stil_pid) or {}).get(s_)),
        bagli_gorsel_galeride=sum(1 for i in (bag.get(stil_pid) or {}).values() if i in gids),
        video=[v.get("video_id") for v in vid],
        kisisellestirme=dict(is_personalizable=x.get("is_personalizable"), personalization_is_required=x.get("personalization_is_required"),
                             personalization_char_count_max=x.get("personalization_char_count_max"),
                             personalization_instructions=x.get("personalization_instructions"), soru=h.get("personalization")),
        aciklama_stil_gorsel_satirlari=satir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", required=True)
    ap.add_argument("--pilot", default="4595350971")
    ap.add_argument("--out", required=True)
    ap.add_argument("--yalniz-pilot", action="store_true", help="yalniz pilotu oku; FARKLI'yi --ozet'ten yeniden hesapla")
    ap.add_argument("--ozet", default="", help="mevcut YD_OZET.csv (--yalniz-pilot ile)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); (out / "HAM").mkdir(parents=True, exist_ok=True)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = E.Etsy(store), os.environ["ETSY_SHOP_ID"]
    salt_okur(api)
    satirlar = list(csv.DictReader(open(a.liste, encoding="utf-8-sig")))
    ids = [r["listing_id"].strip() for r in satirlar if r.get("listing_id", "").strip()]
    cift = {r["listing_id"].strip(): r.get("cift", "").strip() for r in satirlar}
    if a.pilot not in ids:
        ids = [a.pilot] + ids
    ids = sorted(dict.fromkeys(ids), key=lambda i: i != a.pilot)
    if a.yalniz_pilot:
        ids = [a.pilot]
    ozet, P = [], None
    for n, lid in enumerate(ids, 1):
        api.kota_kapisi(f"ilan {lid}")
        h = oku(api, shop, lid, pilot=lid == a.pilot)
        (out / "HAM" / f"{lid}.json").write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
        y = yapi(h); y["cift"] = cift.get(lid, "")
        if lid == a.pilot:
            P = y
            (out / f"PILOT_{lid}.json").write_text(json.dumps(dict(**y, kaynak="Etsy API GET (yd-envanter-oku)", istek_su_ana=api.calls,
                                                                  kota=api.remaining), ensure_ascii=False, indent=1), encoding="utf-8")
        ozet.append(y)
        print(f"[{n}/{len(ids)}] {lid} {y['state']} gorsel {y['gorsel_sayisi']} stil {y['stil_ozelligi']} {len(y['stil_secenekleri'])} "
              f"bag {y['bagli_secenek']} video {len(y['video'])} istek {api.calls} kota {api.remaining}", flush=True)
    if a.yalniz_pilot:
        if a.ozet:
            satirlar_o = list(csv.DictReader(open(a.ozet, encoding="utf-8")))
            print(f"FARKLI (mevcut ozet {len(satirlar_o)} satir): {len(farkli_yaz(out, satirlar_o, a.pilot))} | istek {api.calls} | kota {api.remaining}")
        return 0
    alan = ["listing_id", "cift", "state", "gorsel_sayisi", "kapak_image_id", "kapak_boyut", "stil_ozelligi", "stil_secenekleri",
            "bagli_secenek", "bagli_gorsel_galeride", "video", "urun", "fiyat_aralik"]
    def satir(y):
        k = y["kapak"] or {}
        return [y["listing_id"], y["cift"], y["state"], y["gorsel_sayisi"], k.get("listing_image_id"),
                f"{k.get('full_width')}x{k.get('full_height')}" if k else "", y["stil_ozelligi"], " | ".join(y["stil_secenekleri"]),
                y["bagli_secenek"], y["bagli_gorsel_galeride"], "var " + ",".join(map(str, y["video"])) if y["video"] else "yok", y["urun"],
                "-".join(map(str, y["fiyat_aralik"] or []))]
    with open(out / "YD_OZET.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(alan); w.writerows(satir(y) for y in ozet)
    farkli = farkli_yaz(out, [dict(zip(alan, map(str, satir(y)))) for y in ozet], a.pilot)
    print(f"ILAN {len(ozet)} | FARKLI {len(farkli)} | istek {api.calls} | kota {api.remaining}")
    return 0


def farkli_yaz(out, satirlar, pilot):
    """YD_OZET satirlarini pilotla kiyaslar (gorsel, stil, bag, video, state, urun, fiyat)."""
    P = next((r for r in satirlar if r["listing_id"] == str(pilot)), None)
    farkli = []
    for r in satirlar:
        if P is None or r is P:
            continue
        neden = [f"{k} {r[k]} (pilot {P[k]})" for k in ("gorsel_sayisi", "stil_ozelligi", "stil_secenekleri", "urun", "fiyat_aralik")
                 if r[k] != P[k]]
        n = len([v for v in r["stil_secenekleri"].split(" | ") if v])
        if int(r["bagli_secenek"]) < n or int(r["bagli_gorsel_galeride"]) < int(r["bagli_secenek"]):
            neden.append(f"bag eksigi {r['bagli_secenek']}/{n}, galeride {r['bagli_gorsel_galeride']}")
        if (r["video"] == "yok") != (P["video"] == "yok"):
            neden.append(f"video {r['video']} (pilot {P['video']})")
        if r["state"] != "active":
            neden.append(f"state {r['state']}")
        if neden:
            farkli.append([r["listing_id"], r["cift"], " ; ".join(neden)])
    with open(out / "FARKLI.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "fark"]); w.writerows(farkli)
    return farkli


if __name__ == "__main__":
    sys.exit(main())
