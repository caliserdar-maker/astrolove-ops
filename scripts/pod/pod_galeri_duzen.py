#!/usr/bin/env python3
"""Galeri duzeni: 1 kapak | 2-3 oda | 4-8 bilgi | 9-13 edisyon (MB,DB,WP,CI,PW).

Kural (canli veriden): kapak = rank 1; edisyonlar = varyasyona bagli 5 gorsel;
kalan 7 gorsel (oda 2 + bilgi 5) orijinal goreli sirasiyla 2-8'e gelir.
Oda kontrolu: 2. ve 3. sira 3000x2250 (4:3 fotograf) olmali; degilse ATLA.

Alt komutlar:
  pilot : tek ilan icin yazma (rank atamalari + EN SONDA variation-images PUT)
  kuru  : 78 ilan icin salt okuma plani + HEDEF_TABLOSU.jpg / HEDEF_PLAN.csv
"""
import argparse
import csv
import io
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
from pod_cover_from_video import (gallery, variation_images,  # noqa: E402
                                  variation_map, video_ids, videos)

DRV = "gdrive:ASTROLOVE/TEMP/POD_RANK3_TO_11"
CIFT_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
EDISYON_SIRA = ["Midnight Blue", "Deep Black", "Warm Parchment",
                "Champagne Ivory", "Pure White"]
ODA_BOYUT = (3000, 2250)
T0 = time.time()


def ilerle(m):
    log(f"[{time.time() - T0:7.1f}s] {m}")


def sure_yaz(sn):
    sn = int(max(0, sn))
    return f"{sn // 60}d {sn % 60:02d}sn"


def rclone(*a):
    return subprocess.run(["rclone", *a], capture_output=True, text=True)


def ciftler():
    veri = json.loads(CIFT_JSON.read_text(encoding="utf-8"))
    return sorted({(str(r["id"]), r["pair"].replace(" + ", "_").replace(" ", "_").upper())
                   for r in veri if r.get("id") and r.get("pair")})


def anlik(api, shop, lid):
    return {"listing": api.get(f"/listings/{lid}") or {},
            "images": gallery(api, lid),
            "videos": videos(api, lid),
            "variations": variation_images(api, shop, lid)}


def sira(s):
    return [(str(x.get("listing_image_id")), int(x.get("rank") or 0))
            for x in s["images"]]


def hedef_hesapla(s):
    """Donus: (hedef_id_listesi, edisyon_kayitlari, sorun_metni)."""
    imgs = s["images"]
    vmap = {str(r.get("image_id")): (r.get("property_id"), r.get("value_id"),
                                     r.get("value")) for r in s["variations"]}
    if len(imgs) != 13:
        return None, None, f"galeri {len(imgs)} gorsel"
    if len(vmap) != 5:
        return None, None, f"varyasyon baglantisi {len(vmap)}"
    deger_id = {v[2]: k for k, v in vmap.items()}
    eksik = [d for d in EDISYON_SIRA if d not in deger_id]
    if eksik:
        return None, None, f"edisyon baglantisi eksik: {eksik}"
    idler = [str(x.get("listing_image_id")) for x in imgs]
    kapak = idler[0]
    if kapak in vmap:
        return None, None, "kapak varyasyona bagli"
    disi = [i for i in idler[1:] if i not in vmap]
    if len(disi) != 7:
        return None, None, f"edisyon disi gorsel {len(disi)} (7 bekleniyor)"
    boyut = {str(x.get("listing_image_id")): (x.get("full_width"), x.get("full_height"))
             for x in imgs}
    oda = [i for i in disi[:2] if boyut.get(i) == ODA_BOYUT]
    if len(oda) != 2:
        return None, None, (f"ilk iki edisyon disi gorsel oda degil: "
                            f"{[boyut.get(i) for i in disi[:2]]}")
    hedef = [kapak] + disi + [deger_id[d] for d in EDISYON_SIRA]
    kayit = [{"property_id": vmap[deger_id[d]][0], "value_id": vmap[deger_id[d]][1],
              "deger": d, "image_id": int(deger_id[d])} for d in EDISYON_SIRA]
    return hedef, kayit, ""


def yedekle(isd, lid, s, hedef):
    y = isd / "snapshot.json"
    y.write_text(json.dumps(
        {"listing": lid, "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "sira": sira(s), "varyasyon": [list(x) for x in variation_map(s["variations"])],
         "video": [str(v) for v in video_ids(s["videos"])],
         "baslik": s["listing"].get("title"), "durum": s["listing"].get("state"),
         "hedef": hedef}, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(y), f"{DRV}/YEDEK/{lid}/snapshot_galeri.json")


def pilot(a, api, shop):
    lid = a.listing
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    once = anlik(api, shop, lid)
    hedef, edisyon, sorun = hedef_hesapla(once)
    canli = sira(once)
    ilerle(f"{lid} canli {canli}")
    if sorun:
        raise SystemExit(f"DUR: {sorun}")
    if a.hedef:
        elle = [x for x in a.hedef.split(",") if x]
        ilerle(f"kural hedefi: {hedef}")
        ilerle(f"verilen hedef: {elle}")
        if sorted(elle) != sorted([i for i, _ in canli]):
            raise SystemExit("DUR: verilen hedef id kumesi galeriyle ayni degil")
        hedef = elle
    ilerle(f"edisyon baglantilari: {[(e['deger'], e['image_id']) for e in edisyon]}")
    yedekle(isd, lid, once, hedef)
    simdiki = dict(canli)
    yapilacak = [(iid, i + 1) for i, iid in enumerate(hedef)
                 if simdiki.get(iid) != i + 1]
    ilerle(f"gonderilecek rank cagrisi: {len(yapilacak)} {yapilacak}")
    if not a.apply:
        print(json.dumps({"kuru": True, "hedef": hedef, "cagri": len(yapilacak),
                          "plan": yapilacak}, ensure_ascii=False))
        return 0

    for n, (iid, r) in enumerate(yapilacak, start=1):
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, iid), "rank": (None, str(r))})
        ilerle(f"  rank {n}/{len(yapilacak)} {iid} -> {r} | kota {api.remaining}")
    govde = [{"property_id": e["property_id"], "value_id": e["value_id"],
              "image_id": e["image_id"]} for e in edisyon]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images",
                  {"variation_images": govde})
    ilerle(f"  variation-images yazildi: {len(govde)} baglanti")

    hedef_vmap = sorted((e["property_id"], e["value_id"], e["deger"], e["image_id"])
                        for e in edisyon)
    son, bitis = None, time.time() + 90
    while True:
        son = anlik(api, shop, lid)
        s_sira = sira(son)
        if ([i for i, _ in s_sira] == hedef
                and [r for _, r in s_sira] == list(range(1, 14))
                and sorted(variation_map(son["variations"])) == hedef_vmap):
            break
        if time.time() >= bitis:
            break
        ilerle(f"  bekleniyor: rank {[r for _, r in s_sira]}")
        time.sleep(10)
    s_sira = sira(son)
    kapilar = {
        "rank_1_13_temiz": [r for _, r in s_sira] == list(range(1, 14)),
        "sira_hedef": [i for i, _ in s_sira] == hedef,
        "varyasyon_5_birebir": sorted(variation_map(son["variations"])) == hedef_vmap,
        "gorsel_13": len(son["images"]) == 13,
        "video_ayni": video_ids(once["videos"]) == video_ids(son["videos"]),
        "baslik_ayni": once["listing"].get("title") == son["listing"].get("title"),
        "durum_ayni": once["listing"].get("state") == son["listing"].get("state")}
    sonuc = {"listing": lid, "cagri": len(yapilacak) + 1, "hedef": hedef,
             "canli_sonra": s_sira,
             "varyasyon": [list(x) for x in variation_map(son["variations"])],
             "kapilar": kapilar, "hepsi_gecti": all(kapilar.values()),
             "kota_sonra": api.remaining,
             "link": f"https://www.etsy.com/listing/{lid}"}
    (isd / "DUZEN.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    rclone("copyto", str(isd / "DUZEN.json"), f"{DRV}/DUZEN_{lid}.json")
    ilerle(f"SONUC {kapilar}")
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0 if all(kapilar.values()) else 3


def indir(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read(4_000_000)


def kuru(a, api, shop):
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    hepsi = ciftler()
    if a.limit:
        hepsi = hepsi[:a.limit]
    SUTUN = (["listing_id", "cift", "durum", "neden", "rank_cagrisi"]
             + [f"once_{i}" for i in range(1, 14)]
             + [f"hedef_{i}" for i in range(1, 14)])
    satirlar, satir_gorsel, atla = [], [], []
    t0 = time.time()
    HW, HH = 110, 138
    for j, (lid, cift) in enumerate(hepsi, start=1):
        s = anlik(api, shop, lid)
        canli = sira(s)
        hedef, edisyon, sorun = hedef_hesapla(s)
        r = {"listing_id": lid, "cift": cift,
             "durum": "ATLA" if sorun else "OK", "neden": sorun}
        for i, (iid, _) in enumerate(canli[:13], start=1):
            r[f"once_{i}"] = iid
        if hedef:
            simdiki = dict(canli)
            r["rank_cagrisi"] = sum(1 for i, iid in enumerate(hedef)
                                    if simdiki.get(iid) != i + 1)
            for i, iid in enumerate(hedef, start=1):
                r[f"hedef_{i}"] = iid
            url = {str(x.get("listing_image_id")):
                   (x.get("url_170x135") or x.get("url_75x75") or x.get("url_570xN"))
                   for x in s["images"]}
            hucre = []
            for iid in hedef:
                try:
                    im = Image.open(io.BytesIO(indir(url[iid]))).convert("RGB")
                except Exception:
                    im = Image.new("RGB", (HW, HH), (220, 60, 60))
                kut = Image.new("RGB", (HW, HH), (245, 245, 245))
                im.thumbnail((HW, HH), Image.LANCZOS)
                kut.paste(im, ((HW - im.width) // 2, (HH - im.height) // 2))
                hucre.append(kut)
            satir_gorsel.append((f"{cift}", hucre))
        else:
            atla.append((lid, cift, sorun))
        satirlar.append(r)
        gec = time.time() - t0
        if j % 5 == 0 or j == len(hepsi):
            ilerle(f"{j}/{len(hepsi)} (%{100 * j / len(hepsi):.0f}) gecen "
                   f"{sure_yaz(gec)} kalan ~{sure_yaz(gec / j * (len(hepsi) - j))} "
                   f"| atla {len(atla)} | kota {api.remaining}")

    plan = isd / "HEDEF_PLAN.csv"
    with plan.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    basl = 18
    tuval = Image.new("RGB", (13 * HW + 190, len(satir_gorsel) * (HH + basl) + 8),
                      (250, 250, 250))
    ciz = ImageDraw.Draw(tuval)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for i, (ad, hucre) in enumerate(satir_gorsel):
        y = i * (HH + basl) + 4
        ciz.text((6, y + HH // 2 - 8), ad.replace("_", "+").title(), fill=(15, 15, 15),
                 font=font)
        for k, im in enumerate(hucre):
            tuval.paste(im, (190 + k * HW, y))
    hedef_yol = isd / "HEDEF_TABLOSU.jpg"
    for q in (85, 80, 72, 65, 58, 50, 45, 40, 35, 30):
        tuval.save(hedef_yol, quality=q, optimize=True)
        if hedef_yol.stat().st_size <= 3e6:
            break
    (isd / "HEDEF_OZET.json").write_text(json.dumps(
        {"ilan": len(hepsi), "ok": sum(1 for r in satirlar if r["durum"] == "OK"),
         "atla": [list(x) for x in atla],
         "toplam_rank_cagrisi": sum(int(r.get("rank_cagrisi") or 0) for r in satirlar),
         "kota_sonra": api.remaining}, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in ("HEDEF_PLAN.csv", "HEDEF_TABLOSU.jpg", "HEDEF_OZET.json"):
        rclone("copyto", str(isd / f), f"{DRV}/{f}")
    ilerle(f"BITTI | OK {sum(1 for r in satirlar if r['durum'] == 'OK')} | ATLA "
           f"{len(atla)} | tablo {hedef_yol.stat().st_size / 1e6:.2f} MB")
    print(json.dumps({"ok": sum(1 for r in satirlar if r["durum"] == "OK"),
                      "atla": atla, "tablo_mb": round(hedef_yol.stat().st_size / 1e6, 2),
                      "kota": api.remaining}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("pilot")
    p.add_argument("--listing", required=True)
    p.add_argument("--hedef", default="")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    p.add_argument("--is-dizin", default="_work/duzen")
    k = alt.add_parser("kuru")
    k.add_argument("--limit", type=int, default=0)
    k.add_argument("--is-dizin", default="_work/duzen")
    a = ap.parse_args()
    if a.komut == "pilot" and a.apply and a.confirm != "GALERI_DUZEN":
        raise SystemExit("DUR: apply icin confirm 'GALERI_DUZEN' olmali")
    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    ilerle(f"kota once: {api.remaining} | komut {a.komut}")
    return pilot(a, api, shop) if a.komut == "pilot" else kuru(a, api, shop)


if __name__ == "__main__":
    sys.exit(main())
