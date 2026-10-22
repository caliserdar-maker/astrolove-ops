#!/usr/bin/env python3
"""BY78 78 TASLAK BAGIMSIZ KONTROL (14 Eki 2026, Takip gorevi). SALT OKUR: Etsy API'ye yalniz GET; yazma metodu YOK.
Her listing_id icin satir basina PASS/FAIL + neden:
  state=draft; baslik, 13 etiket, aciklama = BIZIM_YILIMIZ_78_ILAN_METIN.csv (HTML kacislari cozulur); uzun/orta tire yok;
  13 gorsel: 1 = bordo kare kapak 2400x2400 (15 Eki), 2-8 yatay 3200x2400, 9-13 dikey 2400x3000 (stil vitrinleri + rank 13 Layers);
  1 video (15 Eki);
  envanter 15 urun (5 stil x 3 format), fiyat yalniz formata gore (Digital card 5x7 5, Digital file 8x10 9, Shipped print 8x10 29), hepsi acik;
  Style'a bagli gorsel: Starlit=9, Timeless=10, First Page=11, Botanical=12, Layers=13 (15 Eki, Serdar);
  kisisellestirme 5 kutu (adlar, Your special date, Heading, Optional short line), zorunluluk ve sinirlar (11, 11, 20, 20, 20);
  bolum, kargo, iade, kategori, islem 4-7, production partner, who_made, when_made; Holiday niteligi YOK.
Taslak CSV'de 78 farkli cift ve 78 farkli listing_id.
Cikti: <OUT>/KONTROL.csv, <OUT>/OZET.md. Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: by78_taslak_kontrol.py --taslak BY78_TASLAKLAR.csv --metin BIZIM_YILIMIZ_78_ILAN_METIN.csv --out DIR
HAFIF MOD (15 Eki, kota tabani 500): --hafif --bag-csv BY78_KAPAK_VIDEO.csv --cl-json BY78_VIDEO_ETSY.json
  getListingsByListingIds (100'luk paket, includes=images,videos): 78 ilan icin 1 istek. Her ilan: state=draft, 13 gorsel,
  rank 1 2400x2400, 2-8 3200x2400, 9-13 2400x3000, 1 video. 5 stil bagi istek atmadan: bag CSV (77 satir TAMAM) + CL kaydi
  (yazma aninda Etsy'den okunup dogrulandi); 78 cift, hepsinde Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=13."""
import argparse
import csv
import html
import os
import re
import sys
from pathlib import Path

SECTION, SHIP, RET, TAX, PARTNER = 60895624, 314711751541, 1513990287785, 121, 5817638
WHO, WHEN, PROC = "i_did", "made_to_order", (4, 7)
STYLES = ["Starlit", "Timeless", "First Page", "Layers", "Botanical"]
FIYAT = {"Digital card 5x7": 5.0, "Digital file 8x10": 9.0, "Shipped print 8x10": 29.0}
P_STYLE, P_FORMAT = 513, 514
YATAY = (3200, 2400)
DIKEY = (2400, 3000)
KARE = (2400, 2400)
STIL_RANK = {"Starlit": 9, "Timeless": 10, "First Page": 11, "Botanical": 12, "Layers": 13}
TIRE = re.compile("[–—]")


def norm(s):
    s = html.unescape(html.unescape(s or "")).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(x.rstrip() for x in s.strip().split("\n"))


def beklenen_kutular(cift):
    a, b = (p.capitalize() for p in cift.split("_", 1))
    l1, l2 = ("Name on the left", "Name on the right") if a == b else (f"Name under {a}", f"Name under {b}")
    return [(l1, True, 11), (l2, True, 11), ("Your special date", True, 20), ("Heading", True, 20), ("Optional short line", False, 20)]


def fiyat(o):
    p = (o or {}).get("price")
    if isinstance(p, dict) and p.get("divisor"):
        return round(p["amount"] / p["divisor"], 2)
    return p


def ilan_kontrol(api, shop, cift, lid, m):
    """m: ilan metni satiri. Donus: (nedenler listesi, ayrinti sozlugu)."""
    n = []
    L = api.get(f"/listings/{lid}", ok404=True)
    if not L:
        return ["ilan okunamadi (404)"], {}
    if L.get("state") != "draft":
        n.append(f"state {L.get('state')}")
    if norm(L.get("title")) != norm(m["baslik"]):
        n.append("baslik farkli")
    tags = L.get("tags") or []
    bek_tags = [m[f"etiket_{i}"] for i in range(1, 14)]
    if len(tags) != 13:
        n.append(f"etiket {len(tags)}")
    if sorted(norm(t).lower() for t in tags) != sorted(norm(t).lower() for t in bek_tags):
        n.append("etiketler farkli")
    if norm(L.get("description")) != norm(m["aciklama"]):
        a, b = norm(L.get("description")), norm(m["aciklama"])
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        n.append(f"aciklama farkli (ilk fark {i}: {a[i:i + 25]!r} / {b[i:i + 25]!r})")
    if TIRE.search(norm(L.get("title")) + norm(L.get("description")) + "".join(tags)):
        n.append("uzun/orta tire")
    for ad, okunan, bek in (("bolum", L.get("shop_section_id"), SECTION), ("kargo", L.get("shipping_profile_id"), SHIP),
                            ("iade", L.get("return_policy_id"), RET), ("kategori", L.get("taxonomy_id"), TAX),
                            ("islem", (L.get("processing_min"), L.get("processing_max")), PROC),
                            ("partner", sorted(p.get("production_partner_id") for p in L.get("production_partners") or []), [PARTNER]),
                            ("who_made", L.get("who_made"), WHO), ("when_made", L.get("when_made"), WHEN)):
        if okunan != bek:
            n.append(f"{ad} {okunan} (beklenen {bek})")

    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    if len(ims) != 13:
        n.append(f"gorsel {len(ims)} (13 olmali)")
    kapak = None
    if ims:
        w, h = ims[0].get("full_width"), ims[0].get("full_height")
        kapak = "kare" if (w, h) == KARE else ("dikey" if (w, h) == DIKEY else f"{w}x{h}")
        if kapak != "kare":
            n.append(f"1. gorsel 2400x2400 (kare kapak) degil {w}x{h}")
        boy = [(i + 1, x.get("full_width"), x.get("full_height")) for i, x in enumerate(ims)]
        yanlis = [b for b in boy if 2 <= b[0] <= 8 and (b[1], b[2]) != YATAY]
        if yanlis:
            n.append(f"2-8 3200x2400 olmayan {len(yanlis)}: {yanlis[:3]}")
        yanlis = [b for b in boy if b[0] >= 9 and (b[1], b[2]) != DIKEY]
        if yanlis:
            n.append(f"9+ 2400x3000 olmayan {len(yanlis)}: {yanlis[:3]}")
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    if len(vids) != 1:
        n.append(f"video {len(vids)} (1 olmali)")
    img_ids = {x.get("listing_image_id") for x in ims}
    id_rank = {x.get("listing_image_id"): i + 1 for i, x in enumerate(ims)}

    inv = api.get(f"/listings/{lid}/inventory") or {}
    prods = inv.get("products") or []
    kombi, fiyat_hata, kapali = set(), [], 0
    for p in prods:
        pv = {v.get("property_id"): (v.get("values") or [None])[0] for v in p.get("property_values") or []}
        st, fm = pv.get(P_STYLE), pv.get(P_FORMAT)
        kombi.add((st, fm))
        offs = p.get("offerings") or []
        o = offs[0] if offs else {}
        if not o.get("is_enabled", False) or (o.get("quantity") or 0) <= 0:
            kapali += 1
        if FIYAT.get(fm) != fiyat(o):
            fiyat_hata.append(f"{st}/{fm}={fiyat(o)}")
    if len(prods) != 15 or kombi != {(s, f) for s in STYLES for f in FIYAT}:
        n.append(f"envanter {len(prods)} urun, kombinasyon {len(kombi)} (15 olmali)")
    if fiyat_hata:
        n.append(f"fiyat {fiyat_hata[:3]}")
    if kapali:
        n.append(f"kapali urun {kapali}")

    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    vname = {v["value_ids"][0]: v["values"][0] for p in prods for v in p.get("property_values") or []
             if v.get("property_id") == P_STYLE and v.get("value_ids") and v.get("values")}
    stil_img = {}
    for v in vis:
        if v.get("property_id") == P_STYLE:
            stil_img[v.get("value") or vname.get(v.get("value_id"))] = v.get("image_id")
    eksik = [s for s in STYLES if not stil_img.get(s)]
    if eksik:
        n.append(f"stil gorseli yok: {eksik}")
    secili = [stil_img.get(s) for s in STYLES if stil_img.get(s)]
    if len(set(secili)) != len(secili):
        n.append("stil gorselleri ayni degil (tekrar var)")
    if any(i not in img_ids for i in secili):
        n.append("stil gorseli ilan gorsellerinde yok")
    rank_hata = [f"{s}={id_rank.get(stil_img.get(s))}" for s in STYLES if stil_img.get(s) and id_rank.get(stil_img.get(s)) != STIL_RANK[s]]
    if rank_hata:
        n.append(f"stil bag sirasi {rank_hata} (beklenen Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=13)")

    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    kut = [(q.get("question_text"), bool(q.get("required")), q.get("max_allowed_characters")) for q in per]
    if kut != beklenen_kutular(cift):
        n.append(f"kisisellestirme {kut}")

    props = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    if any(p.get("property_name") == "Holiday" for p in props):
        n.append("Holiday niteligi var")
    return n, dict(state=L.get("state"), gorsel=len(ims), kapak=kapak, video=len(vids), urun=len(prods), stil_gorsel=len(set(secili)), kutu=len(per))


def calistir(api, shop, taslak, metin, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    M = {r["cift"]: r for r in metin}
    genel = []
    cift_say = [r.get("cift", "").strip().upper() for r in taslak]
    id_say = [r.get("listing_id", "").strip() for r in taslak]
    if len(set(cift_say)) != 78 or len(cift_say) != 78:
        genel.append(f"taslak CSV: {len(cift_say)} satir, {len(set(cift_say))} farkli cift (78 olmali)")
    if len(set(id_say)) != 78 or len(id_say) != 78:
        genel.append(f"taslak CSV: {len(set(id_say))} farkli listing_id (78 olmali)")
    sonuc = []
    for i, r in enumerate(taslak, 1):
        c, lid = r.get("cift", "").strip().upper(), r.get("listing_id", "").strip()
        if not lid.isdigit():
            nd, ay = [f"listing_id rakam degil {lid!r}"], {}
        elif c not in M:
            nd, ay = ["cift ilan metni CSV'sinde yok"], {}
        else:
            nd, ay = ilan_kontrol(api, shop, c, lid, M[c])
        sonuc.append(dict(cift=c, listing_id=lid, sonuc="PASS" if not nd else "FAIL", neden="; ".join(nd), **ay))
        if i % 10 == 0 or i == len(taslak):
            print(f"[{i}/{len(taslak)}] PASS {sum(s['sonuc'] == 'PASS' for s in sonuc)} | kota {getattr(api, 'remaining', None)}", flush=True)
    alan = ["cift", "listing_id", "sonuc", "neden", "state", "gorsel", "kapak", "video", "urun", "stil_gorsel", "kutu"]
    with open(out / "KONTROL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(sonuc)
    n_pass = sum(s["sonuc"] == "PASS" for s in sonuc)
    md = [f"# BY78 taslak kontrol", "", f"- PASS {n_pass}/{len(sonuc)}", f"- Genel: {'; '.join(genel) if genel else 'PASS (78 farkli cift, 78 farkli listing_id)'}",
          f"- Etsy GET cagrisi {getattr(api, 'calls', '?')}, kalan gunluk kota {getattr(api, 'remaining', '?')}, Etsy yazma 0", "", "## FAIL"]
    md += [f"- {s['cift']} {s['listing_id']}: {s['neden']}" for s in sonuc if s["sonuc"] == "FAIL"] or ["- yok"]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return n_pass == len(sonuc) == 78 and not genel


BAG_METIN = "Starlit=9 Timeless=10 First Page=11 Botanical=12 Layers=13"


def hafif_calistir(api, taslak, bag_satir, cl_kayit, out):
    """Toplu okuma (getListingsByListingIds) + istek atmadan bag kaydi. Donus: (ok, sonuc listesi)."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    kota_bas = None
    ids = [r["listing_id"].strip() for r in taslak]
    L = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "images,videos"}) or {}
        kota_bas = kota_bas or getattr(api, "remaining", None)
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    bag = {r["cift"]: r for r in bag_satir}
    cl = (cl_kayit.get("ilan") or {}).get("CANCER_LIBRA") or {}
    if cl:
        bag["CANCER_LIBRA"] = dict(cift="CANCER_LIBRA", listing_id=str(cl.get("listing_id")), sonuc=cl.get("sonuc") and "TAMAM",
                                   bag=" ".join(f"{a}={v[1]}" for a, v in sorted((cl.get("bag_sonra") or {}).items(), key=lambda x: x[1][1])))
    genel = []
    if len(taslak) != 78 or len(set(ids)) != 78:
        genel.append(f"taslak {len(taslak)} satir / {len(set(ids))} farkli id (78 olmali)")
    if len(bag) != 78:
        genel.append(f"bag kaydi {len(bag)} cift (78 olmali)")
    sonuc = []
    for r in taslak:
        c, lid = r["cift"].strip().upper(), r["listing_id"].strip()
        n = []
        x = L.get(lid)
        if not x:
            n.append("toplu okumada yok")
        else:
            if x.get("state") != "draft":
                n.append(f"state {x.get('state')}")
            ims = sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0)
            if len(ims) != 13:
                n.append(f"gorsel {len(ims)} (13 olmali)")
            boy = [(i + 1, y.get("full_width"), y.get("full_height")) for i, y in enumerate(ims)]
            if boy and (boy[0][1], boy[0][2]) != KARE:
                n.append(f"rank 1 {boy[0][1]}x{boy[0][2]} (2400x2400 olmali)")
            yanlis = [b for b in boy if 2 <= b[0] <= 8 and (b[1], b[2]) != YATAY]
            if yanlis:
                n.append(f"2-8 3200x2400 olmayan {yanlis[:3]}")
            yanlis = [b for b in boy if b[0] >= 9 and (b[1], b[2]) != DIKEY]
            if yanlis:
                n.append(f"9-13 2400x3000 olmayan {yanlis[:3]}")
            if len(x.get("videos") or []) != 1:
                n.append(f"video {len(x.get('videos') or [])} (1 olmali)")
        b = bag.get(c)
        if not b:
            n.append("bag kaydi yok")
        elif str(b.get("listing_id")) != lid or b.get("sonuc") != "TAMAM" or b.get("bag") != BAG_METIN:
            n.append(f"bag kaydi {b.get('listing_id')} {b.get('sonuc')} {b.get('bag')}")
        sonuc.append(dict(cift=c, listing_id=lid, sonuc="FAIL" if n else "PASS", neden="; ".join(n),
                          state=(x or {}).get("state"), gorsel=len((x or {}).get("images") or []),
                          video=len((x or {}).get("videos") or [])))
    alan = ["cift", "listing_id", "sonuc", "neden", "state", "gorsel", "video"]
    with open(out / "KONTROL_HAFIF.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(sonuc)
    n_pass = sum(x["sonuc"] == "PASS" for x in sonuc)
    md = ["# BY78 hafif kontrol", "", f"- PASS {n_pass}/{len(sonuc)}", f"- Genel: {'; '.join(genel) if genel else 'PASS'}",
          f"- Etsy GET {getattr(api, 'calls', '?')} | kota bas {kota_bas} son {getattr(api, 'remaining', '?')} | yazma 0", "", "## FAIL"]
    md += [f"- {x['cift']} {x['listing_id']}: {x['neden']}" for x in sonuc if x["sonuc"] == "FAIL"] or ["- yok"]
    (out / "OZET_HAFIF.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"::warning::HAFIF KONTROL PASS {n_pass}/{len(sonuc)} | genel {'; '.join(genel) if genel else 'PASS'} | Etsy GET {getattr(api, 'calls', '?')} | "
          f"kota bas {kota_bas} son {getattr(api, 'remaining', '?')} | FAIL {[(x['cift'], x['neden'][:80]) for x in sonuc if x['sonuc'] == 'FAIL'][:5]}")
    return n_pass == len(sonuc) == 78 and not genel, sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taslak", required=True); ap.add_argument("--metin", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--hafif", action="store_true"); ap.add_argument("--bag-csv"); ap.add_argument("--cl-json")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    taslak = list(csv.DictReader(open(a.taslak, encoding="utf-8-sig")))
    if a.hafif:
        import json
        ok, _ = hafif_calistir(api, taslak, list(csv.DictReader(open(a.bag_csv, encoding="utf-8-sig"))), json.load(open(a.cl_json)), a.out)
        sys.exit(0 if ok else 1)
    metin = list(csv.DictReader(open(a.metin, encoding="utf-8-sig")))
    ok = calistir(api, os.environ["ETSY_SHOP_ID"], taslak, metin, a.out)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
