#!/usr/bin/env python3
"""CL (4570143815) galerisini 19'luk final setle degistirir (Serdar onayi 28 Eyl 2026).

Kaynak: <kaynak>/NN_*.jpg (NN = hedef sira 1-19); alt metin data/pod/cl_galeri_alt_metin.csv.
Etsy siniri ilan basina 20 gorsel (N eski + 19 yeni sigmaz), bu yuzden sira (Serdar onayi 28 Eyl):
  yedek -> N-1 eski silinir (1 eski CAPA olarak kalir, ilan bos kalmaz)
  -> 19 yeni sira 2-20'ye alt metinle yuklenir -> 5 renk bagi yeni 15-19'a POST edilir
  -> capa silinir (siralar 1-19'a oturur) -> tam geri okuma.
Modlar (ilk hatada DUR, her yazma tek deneme):
  --mod dry-run : SALT OKUMA; plan + mevcut galeri dokumu.
  --mod yedek   : SALT OKUMA + CDN indirme; galeri/baglar/video/korunanlar <out>/yedek/ altina
                  (workflow bunu Drive'a kopyalar, sonra uygula kosulur).
  --mod uygula  : ETSY'YE YAZAR. Once yedek manifestiyle canli galeri karsilastirilir; uyusmazsa DUR.
N ve image_id'ler her kosuda CANLI okunur (kapak-yukle ayni ilanda kapak degistirir; sabit sayi yok).
Video ve active AYNEN kalir; updateListing cagrisi YOK (taslagi yayina alma riski, 7 Eyl olcumu).
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

RENK_SIRA = {"Midnight Blue": 15, "Deep Black": 16, "Pure White": 17, "Champagne Ivory": 18, "Warm Parchment": 19}
IMG_LIMIT = 20
OKUMA_TEKRAR, OKUMA_BEKLE = 8, 4
QUOTA_MIN = 400


def kararli(fn, kosul, tekrar=OKUMA_TEKRAR, bekle=OKUMA_BEKLE):
    son = None
    for _ in range(tekrar):
        time.sleep(bekle)
        son = fn()
        if kosul(son):
            return son
    return son


def galeri(api, lid):
    r = api.get(f"/listings/{lid}/images", ok404=True) or {}
    return sorted(r.get("results") or [], key=lambda x: x.get("rank") or 0)


def var_img(api, shop, lid):
    return (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []


def videolar(api, lid):
    return (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []


def renk_degerleri(api, lid):
    """Envanterden Primary color: {renk adi: (property_id, value_id)} (var_img'e guvenilmez, GOREV 0024)."""
    inv = api.get(f"/listings/{lid}/inventory") or {}
    out = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                if val in RENK_SIRA:
                    out.setdefault(val, (pv.get("property_id"), vid))
    return out


def envanter_ozeti(api, lid):
    inv = api.get(f"/listings/{lid}/inventory") or {}
    ozet = sorted((pr.get("sku"), json.dumps(pr.get("offerings"), sort_keys=True, default=str))
                  for pr in inv.get("products") or [])
    return hashlib.sha256(json.dumps(ozet).encode()).hexdigest(), len(ozet)


def korunanlar(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    inv_sha, n_urun = envanter_ozeti(api, lid)
    return {"state": L.get("state"), "title": L.get("title"), "tags": L.get("tags"),
            "desc_sha": hashlib.sha256((L.get("description") or "").encode()).hexdigest(),
            "inv_sha": inv_sha, "n_urun": n_urun,
            "video_ids": sorted(v.get("video_id") for v in videolar(api, lid))}


def kaynak_dosyalar(kaynak):
    yol = {}
    for p in sorted(Path(kaynak).glob("*.jpg")):
        n = int(p.name.split("_", 1)[0])
        if n in yol:
            raise SystemExit(f"HATA: kaynak sira {n} iki dosyada. DUR.")
        yol[n] = p
    if sorted(yol) != list(range(1, 20)):
        raise SystemExit(f"HATA: kaynak 1-19 degil: {sorted(yol)}. DUR.")
    return yol


def alt_metinler(csv_yol):
    rows = {int(r["sira"]): r["metin"].strip() for r in csv.DictReader(open(csv_yol, encoding="utf-8"))}
    if sorted(rows) != list(range(1, 20)) or not all(0 < len(v) <= 250 for v in rows.values()):
        raise SystemExit("HATA: alt metin CSV 19 satir/250 sinirina uymuyor. DUR.")
    return rows


def indir(url, hedef):
    r = requests.get(url, timeout=120)
    if r.status_code != 200 or not r.content:
        raise SystemExit(f"HATA: yedek indirme {r.status_code}. DUR.")
    Path(hedef).write_bytes(r.content)


def yedek_al(api, shop, lid, out, cdn_indir=True):
    yd = Path(out) / "yedek"
    yd.mkdir(parents=True, exist_ok=True)
    g = galeri(api, lid)
    vi = var_img(api, shop, lid)
    vids = videolar(api, lid)
    kor = korunanlar(api, shop, lid)
    man = {"listing_id": lid, "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
           "galeri": [{"rank": x.get("rank"), "listing_image_id": x.get("listing_image_id"),
                       "alt_text": x.get("alt_text"), "url": x.get("url_fullxfull")} for x in g],
           "variation_images": vi, "videolar": vids, "korunan": kor}
    (yd / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False))
    if cdn_indir:
        for x in g:
            indir(x.get("url_fullxfull"), yd / f"{x.get('rank'):02d}_{x.get('listing_image_id')}.jpg")
    log(f"yedek: {len(g)} gorsel, {len(vi)} renk bagi, {len(vids)} video, state={kor['state']} -> {yd}")
    return man


def uygula(api, shop, lid, kaynak, altcsv, out, qmin):
    out = Path(out)
    yol, alt = kaynak_dosyalar(kaynak), alt_metinler(altcsv)
    man = json.loads((out / "yedek" / "manifest.json").read_text())
    if man.get("listing_id") != lid:
        raise SystemExit("HATA: yedek manifesti baska ilana ait. DUR.")
    if man["korunan"]["state"] != "active":
        raise SystemExit(f"HATA: ilan active degil ({man['korunan']['state']}). DUR.")
    if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < qmin:
        raise SystemExit(f"HATA: kota {api.remaining} < {qmin}. YAZMA YOK.")
    g0 = galeri(api, lid)
    canli = {x.get("listing_image_id") for x in g0}
    yedekli = {x["listing_image_id"] for x in man["galeri"]}
    if canli != yedekli:
        raise SystemExit(f"HATA: canli galeri yedekten farkli (yedek sonrasi degisim?): "
                         f"+{sorted(canli - yedekli)} -{sorted(yedekli - canli)}. DUR.")
    rv = renk_degerleri(api, lid)
    if sorted(rv) != sorted(RENK_SIRA):
        raise SystemExit(f"HATA: envanterde 5 renk bulunamadi: {sorted(rv)}. DUR.")

    bagli = {v.get("image_id") for v in man["variation_images"]}
    eski = [x["listing_image_id"] for x in man["galeri"]]
    capa = next((i for i in eski if i not in bagli), eski[0])   # tercihen baglantisiz kapak/ilk gorsel
    sil1 = [i for i in eski if i != capa]
    log(f"faz1: {len(sil1)} eski silinecek, capa {capa} kalacak (bagli {len(bagli & set(sil1))} tanesi gecici cozulur)")
    for i in sil1:
        api.delete(f"/listings/{lid}/images/{i}")
    g1 = kararli(lambda: galeri(api, lid), lambda g: len(g) == 1)
    if len(g1) != 1 or g1[0].get("listing_image_id") != capa:
        raise SystemExit(f"HATA: faz1 sonrasi galeri {[(x.get('rank'), x.get('listing_image_id')) for x in g1]}. DUR.")

    yeni = {}
    for n in range(1, 20):
        with open(yol[n], "rb") as fh:
            r = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                              files={"image": (yol[n].name, fh, "image/jpeg")},
                              data={"rank": str(n + 1), "alt_text": alt[n]})
        yeni[n] = r.get("listing_image_id")
        if not yeni[n] or yeni[n] in eski:
            raise SystemExit(f"HATA: faz2 sira {n} yukleme id {yeni[n]} (eski id'yle catisti mi?). DUR.")
        log(f"faz2 [{n}/19] {yol[n].name} -> {yeni[n]} | kota {api.remaining}")
    g2 = kararli(lambda: galeri(api, lid), lambda g: len(g) == 20)
    sira2 = [x.get("listing_image_id") for x in g2]
    if len(g2) != 20 or sira2[0] != capa or sira2[1:] != [yeni[n] for n in range(1, 20)]:
        raise SystemExit(f"HATA: faz2 sonrasi sira beklenen degil: {sira2}. DUR.")

    vi = [{"property_id": rv[r][0], "value_id": rv[r][1], "image_id": yeni[RENK_SIRA[r]]} for r in RENK_SIRA]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
    hedef = {r: yeni[RENK_SIRA[r]] for r in RENK_SIRA}

    def bag_ok(vm):
        vm = {v.get("value"): v.get("image_id") for v in vm}
        return len(vm) == 5 and all(vm.get(r) == hedef[r] for r in hedef)
    v3 = kararli(lambda: var_img(api, shop, lid), bag_ok)
    if not bag_ok(v3):
        raise SystemExit(f"HATA: faz3 renk baglari dogrulanamadi: {v3}. DUR.")
    log("faz3: 5 renk bagi yeni gorsellerde dogrulandi")

    api.delete(f"/listings/{lid}/images/{capa}")
    g4 = kararli(lambda: galeri(api, lid),
                 lambda g: [x.get("listing_image_id") for x in g] == [yeni[n] for n in range(1, 20)]
                 and [x.get("rank") for x in g] == list(range(1, 20)))
    if [x.get("listing_image_id") for x in g4] != [yeni[n] for n in range(1, 20)] \
            or [x.get("rank") for x in g4] != list(range(1, 20)):
        raise SystemExit(f"HATA: faz4 son galeri 1-19'a oturmadi: {[(x.get('rank'), x.get('listing_image_id')) for x in g4]}. DUR.")

    sorun = []
    for x in g4:
        n = x.get("rank")
        if (x.get("alt_text") or "").strip() != alt[n]:
            sorun.append(f"alt {n}")
    kor = korunanlar(api, shop, lid)
    ref = man["korunan"]
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if kor.get(k) != ref.get(k):
            sorun.append(f"korunan {k}")
    if not bag_ok(var_img(api, shop, lid)):
        sorun.append("renk baglari (son okuma)")
    rapor = {"sonuc": "PASS" if not sorun else "FAIL", "sorun": sorun, "yeni_idler": yeni,
             "renk_baglari": hedef, "silinen_eski": sil1 + [capa], "kota_son": api.remaining,
             "korunan_once": ref, "korunan_sonra": kor}
    (out / "rapor.json").write_text(json.dumps(rapor, indent=1, ensure_ascii=False))
    log(f"SONUC: {rapor['sonuc']} {('- ' + '; '.join(sorun)) if sorun else ''} | kota {api.remaining}")
    if sorun:
        raise SystemExit(2)
    return rapor


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", default="4570143815")
    ap.add_argument("--kaynak", required=True)
    ap.add_argument("--alt-csv", default=str(Path(__file__).resolve().parents[2] / "data/pod/cl_galeri_alt_metin.csv"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--mod", required=True, choices=["dry-run", "yedek", "uygula"])
    ap.add_argument("--quota-min", type=int, default=QUOTA_MIN)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    api.verbose_quota = True
    if a.mod == "dry-run":
        yol, alt = kaynak_dosyalar(a.kaynak), alt_metinler(a.alt_csv)
        man = yedek_al(api, shop, a.listing_id, a.out, cdn_indir=False)
        log(f"dry-run: kaynak 19 dosya OK, alt 19 OK; mevcut {len(man['galeri'])} gorsel, "
            f"{len(man['variation_images'])} bag; plan: {len(man['galeri']) - 1} sil + capa, 19 yukle, 5 bagla, capa sil")
        for x in man["galeri"]:
            log(f"  canli sira {x['rank']}: image_id {x['listing_image_id']}")
    elif a.mod == "yedek":
        kaynak_dosyalar(a.kaynak); alt_metinler(a.alt_csv)
        yedek_al(api, shop, a.listing_id, a.out)
    else:
        uygula(api, shop, a.listing_id, a.kaynak, a.alt_csv, a.out, a.quota_min)


if __name__ == "__main__":
    main()
