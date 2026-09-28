#!/usr/bin/env python3
"""RANK3 -> RANK11 kuru deneme (SALT OKUMA). Etsy'ye yazma YOK.

78 POD ilaninin galerisi okunur; 3. siradaki gorsel 11. siraya tasinsa olusacak
beklenen sira hesaplanir. Cikti: PLAN.csv, RANK3_TABLOSU.jpg (13x6 izgara).
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
from pod_cover_from_video import gallery, variation_images, videos  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_RANK3_TO_11"
CIFT_JSON = KOK.parent / "etsy" / "seo" / "pod_changes_v2.json"
KAYNAK, HEDEF = 3, 11
SUTUN = (["listing_id", "cift", "rank3_image_id", "rank3_boyut", "rank3_created",
          "rank3_varyasyona_bagli", "gorsel_sayisi", "video_sayisi", "durum", "not"]
         + [f"once_{i}" for i in range(1, 14)] + [f"sonra_{i}" for i in range(1, 14)])
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


def tasi(sira, kaynak=KAYNAK, hedef=HEDEF):
    """1-tabanli kaynak sirasindaki ogeyi hedef siraya tasir (araya ekleme)."""
    y = list(sira)
    oge = y.pop(kaynak - 1)
    y.insert(hedef - 1, oge)
    return y


def indir(url, en_cok=8_000_000):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read(en_cok)


def tablo(hucreler, hedef_yol, sutun=13, en_cok_mb=3.0):
    hw, hh = hucreler[0][1].size
    basl = 34
    satir = (len(hucreler) + sutun - 1) // sutun
    tuval = Image.new("RGB", (sutun * hw, satir * (hh + basl)), (250, 250, 250))
    ciz = ImageDraw.Draw(tuval)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (ad, im) in enumerate(hucreler):
        x, y = (i % sutun) * hw, (i // sutun) * (hh + basl)
        ciz.text((x + 6, y + 6), ad.replace("_", " + ").title(), fill=(15, 15, 15),
                 font=font)
        tuval.paste(im, (x, y + basl))
    for q in (92, 88, 84, 80, 75, 70, 65, 60, 55, 50, 45, 40):
        tuval.save(hedef_yol, quality=q, optimize=True)
        if hedef_yol.stat().st_size <= en_cok_mb * 1e6:
            break
    return hedef_yol.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-dizin", default="_work/rank3")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)

    shop = os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota_once = api.remaining
    ilerle(f"kota once: {kota_once}")

    hepsi = ciftler()
    if a.limit:
        hepsi = hepsi[:a.limit]
    ilerle(f"ilan sayisi: {len(hepsi)} (referans dahil)")
    satirlar, hucre, farkli, bagli_sayi = [], [], [], 0
    t0 = time.time()
    for j, (lid, cift) in enumerate(hepsi, start=1):
        s = {"listing_id": lid, "cift": cift, "durum": "OK", "not": ""}
        imgs = gallery(api, lid)
        vids = videos(api, lid)
        vimg = variation_images(api, shop, lid)
        bagli = {str(r.get("image_id")) for r in vimg}
        idler = [str(x.get("listing_image_id")) for x in imgs]
        s["gorsel_sayisi"] = len(imgs)
        s["video_sayisi"] = len(vids)
        for i, iid in enumerate(idler[:13], start=1):
            s[f"once_{i}"] = iid
        if len(imgs) < HEDEF:
            s.update({"durum": "UYGUN_DEGIL", "not": f"galeri {len(imgs)} gorsel"})
        else:
            r3 = imgs[KAYNAK - 1]
            r3id = str(r3.get("listing_image_id"))
            s.update({"rank3_image_id": r3id,
                      "rank3_boyut": f"{r3.get('full_width')}x{r3.get('full_height')}",
                      "rank3_created": r3.get("created_timestamp"),
                      "rank3_varyasyona_bagli": r3id in bagli})
            bagli_sayi += 1 if r3id in bagli else 0
            for i, iid in enumerate(tasi(idler)[:13], start=1):
                s[f"sonra_{i}"] = iid
            url = r3.get("url_570xN") or r3.get("url_fullxfull")
            try:
                im = Image.open(io.BytesIO(indir(url))).convert("RGB")
                hucre.append((cift, im.resize((300, 375), Image.LANCZOS)))
                oran = round(r3.get("full_width", 0) / max(r3.get("full_height", 1), 1), 3)
                if oran != 4 / 3 and abs(oran - 1.3333) > 0.02:
                    farkli.append((lid, cift, s["rank3_boyut"]))
            except Exception as e:
                s["not"] = f"gorsel inmedi: {type(e).__name__}"
        satirlar.append(s)
        gec = time.time() - t0
        if j % 5 == 0 or j == len(hepsi):
            ilerle(f"{j}/{len(hepsi)} (%{100 * j / len(hepsi):.0f}) gecen "
                   f"{sure_yaz(gec)} kalan ~{sure_yaz(gec / j * (len(hepsi) - j))} "
                   f"| kota {api.remaining}")

    plan = isd / "PLAN.csv"
    with plan.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow(s)
    boy = tablo(hucre, isd / "RANK3_TABLOSU.jpg") if hucre else 0
    (isd / "OZET.json").write_text(json.dumps(
        {"ilan": len(hepsi), "uygun": sum(1 for s in satirlar if s["durum"] == "OK"),
         "uygun_degil": [(s["listing_id"], s["not"]) for s in satirlar
                         if s["durum"] != "OK"],
         "rank3_varyasyona_bagli": bagli_sayi,
         "farkli_oranli_rank3": farkli,
         "boyut_dagilimi": {},
         "kota_once": kota_once, "kota_sonra": api.remaining},
        ensure_ascii=False, indent=1), encoding="utf-8")
    for f in ("PLAN.csv", "RANK3_TABLOSU.jpg", "OZET.json"):
        if (isd / f).is_file():
            rclone("copyto", str(isd / f), f"{DRV}/{f}")
    ilerle(f"BITTI | tablo {boy / 1e6:.2f} MB | varyasyona bagli rank3 {bagli_sayi} "
           f"| farkli oran {len(farkli)} | kota {kota_once} -> {api.remaining}")
    print(json.dumps({"ilan": len(hepsi), "varyasyon_bagli": bagli_sayi,
                      "farkli": farkli, "kota_sonra": api.remaining},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
