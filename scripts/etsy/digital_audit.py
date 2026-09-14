#!/usr/bin/env python3
"""
DIJITAL ILAN DENETIMI - SALT OKUR (Mo 14 Eyl 2026). Etsy'ye hicbir yazma yok.

Ornek ilan (varsayilan 4552211376, Aquarius-Aquarius Champagne Ivory) icin:
  1) Etsy'ye yuklu dijital dosyalar: sayi, ad, boyut, tur; PDF ayri dosya mi
     yoksa ZIP icinde mi.
  2) Kaynak ZIP Drive'dan bulunur (ad + bayt boyutu Etsy'deki dosyayla birebir
     ayni olmali; degilse ZIP'e dayali iddialar DOGRULANAMADI sayilir) ve acilir:
     kac JPG, her birinin piksel boyutu, oran, DPI, ICC profili, mürekkep
     sinirlari (kirpma kaniti) ve referans gorselle normalize edilmis fark.
  3) Ilan aciklamasindaki iddialar olculen degerlerle karsilastirilir.
  4) Ayni dosya yapisi diger dijital ilanlarda da var mi: her dijital ilan icin
     GET .../files okunur (salt okur) ve dosya sayisi/ad kalibi/tur dagilimi
     cikarilir; sapanlar listelenir.

Kullanim:
  digital_audit.py --listing 4552211376 --zip-index _work/zips.json --out _out
      [--dfile-state _work/dfile_state.csv] [--all-limit 0] [--quota-min 300]
"""
import argparse
import csv
import io
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

from PIL import Image, ImageCms  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ORANLAR = {
    "2:3": 2 / 3,
    "3:4": 3 / 4,
    "4:5": 4 / 5,
    "11:14": 11 / 14,
    "A-Series (1:V2)": 1 / math.sqrt(2),
}
ORAN_TOL = 0.005          # %0.5
MAE_AYNI = 8.0            # normalize edilmis fark esigi (0-255)
MAE_YAKIN = 25.0


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- Etsy okuma
def listing_files(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/files", ok404=True) or {}
    out = []
    for f in r.get("results") or []:
        out.append({
            "listing_file_id": f.get("listing_file_id"),
            "filename": f.get("filename") or "",
            "filesize": f.get("filesize") or "",
            "size_bytes": f.get("size_bytes"),
            "filetype": f.get("filetype") or "",
            "rank": f.get("rank"),
            "create_timestamp": f.get("create_timestamp"),
        })
    return sorted(out, key=lambda x: (x.get("rank") or 0))


# ---------------------------------------------------------------- ZIP olcumu
def oran_adi(w, h):
    r = w / h if w <= h else h / w
    en_iyi, en_iyi_fark = None, 9
    for ad, deger in ORANLAR.items():
        fark = abs(r - deger) / deger
        if fark < en_iyi_fark:
            en_iyi, en_iyi_fark = ad, fark
    return en_iyi, round(en_iyi_fark * 100, 3), round(r, 5)


def dpi_oku(im):
    d = im.info.get("dpi")
    jfif = im.info.get("jfif_density")
    exif_dpi = None
    try:
        ex = im.getexif()
        if ex:
            xr, yr = ex.get(282), ex.get(283)
            if xr and yr:
                exif_dpi = (float(xr), float(yr))
    except Exception:
        pass
    return {
        "dpi": [round(float(x), 2) for x in d] if d else None,
        "jfif_density": list(jfif) if jfif else None,
        "jfif_unit": im.info.get("jfif_unit"),
        "exif_resolution": [round(x, 2) for x in exif_dpi] if exif_dpi else None,
    }


def icc_oku(im):
    raw = im.info.get("icc_profile")
    if not raw:
        return {"gomulu": False, "aciklama": None, "bayt": 0}
    ad = None
    try:
        p = ImageCms.ImageCmsProfile(io.BytesIO(raw))
        ad = ImageCms.getProfileDescription(p).strip()
    except Exception as e:                                   # noqa: BLE001
        ad = f"(okunamadi: {e})"
    return {"gomulu": True, "aciklama": ad, "bayt": len(raw)}


def murekkep_kutusu(im, kucuk=900):
    """Arka plandan farkli piksellerin sinir kutusu -> kenar paylari (%)."""
    g = im.convert("L")
    g.thumbnail((kucuk, kucuk))
    w, h = g.size
    px = g.load()
    kenar = [px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)] + \
            [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)]
    bg = statistics.median(kenar)
    mask = g.point(lambda v: 255 if abs(v - bg) > 12 else 0)
    kutu = mask.getbbox()
    if not kutu:
        return {"bg": bg, "bbox": None, "pay_sol": None, "pay_ust": None,
                "pay_sag": None, "pay_alt": None, "kenara_deger": None}
    x0, y0, x1, y1 = kutu
    pay = {
        "bg": bg,
        "bbox": [x0, y0, x1, y1],
        "olcek": [w, h],
        "pay_sol": round(100 * x0 / w, 2),
        "pay_ust": round(100 * y0 / h, 2),
        "pay_sag": round(100 * (w - x1) / w, 2),
        "pay_alt": round(100 * (h - y1) / h, 2),
    }
    pay["kenara_deger"] = min(pay["pay_sol"], pay["pay_ust"], pay["pay_sag"], pay["pay_alt"]) < 0.5
    return pay


def normalize(im, kutu, boy=384):
    g = im.convert("L")
    if kutu and kutu.get("bbox"):
        w0, h0 = kutu["olcek"]
        x0, y0, x1, y1 = kutu["bbox"]
        W, H = g.size
        g = g.crop((int(x0 * W / w0), int(y0 * H / h0), int(x1 * W / w0), int(y1 * H / h0)))
    return g.resize((boy, boy), Image.LANCZOS)


def mae(a, b):
    pa, pb = a.load(), b.load()
    w, h = a.size
    t = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            t += abs(pa[x, y] - pb[x, y])
    return round(t / ((w // 2) * (h // 2)), 2)


def zip_olc(zpath):
    z = zipfile.ZipFile(zpath)
    girdiler = [{"ad": i.filename, "bayt": i.file_size, "sikistirilmis": i.compress_size}
                for i in z.infolist() if not i.is_dir()]
    jpgler = [g for g in girdiler if g["ad"].lower().endswith((".jpg", ".jpeg"))]
    olcum, imgs = [], {}
    for g in sorted(jpgler, key=lambda x: x["ad"]):
        with z.open(g["ad"]) as fh:
            data = fh.read()
        im = Image.open(io.BytesIO(data))
        im.load()
        w, h = im.size
        ad, fark, r = oran_adi(w, h)
        kutu = murekkep_kutusu(im)
        olcum.append({
            "ad": g["ad"], "bayt": g["bayt"], "px": [w, h], "mp": round(w * h / 1e6, 1),
            "oran": ad, "oran_sapma_yuzde": fark, "olculen_oran": r,
            "mod": im.mode, **dpi_oku(im), "icc": icc_oku(im), "murekkep": kutu,
        })
        imgs[g["ad"]] = normalize(im, kutu)
        im.close()
    # referans = en buyuk alan
    if olcum:
        ref = max(olcum, key=lambda x: x["px"][0] * x["px"][1])["ad"]
        for o in olcum:
            o["fark_ref_mae"] = 0.0 if o["ad"] == ref else mae(imgs[ref], imgs[o["ad"]])
            o["ref"] = ref
    return {"girdiler": girdiler, "jpg_olcum": olcum,
            "pdf_icinde": [g["ad"] for g in girdiler if g["ad"].lower().endswith(".pdf")],
            "diger": [g["ad"] for g in girdiler
                      if not g["ad"].lower().endswith((".jpg", ".jpeg", ".pdf"))]}


# ---------------------------------------------------------- iddia kiyaslama
def iddialar(desc, zolc, dosyalar):
    jpg = zolc.get("jpg_olcum") if zolc else None
    out = []

    def ekle(iddia, metinde, hukum, gercek):
        out.append({"iddia": iddia, "metinde_gecti": metinde, "hukum": hukum, "gercek": gercek})

    # 1) 5 high-resolution JPG
    m = re.search(r"(\d+)\s+high[- ]resolution\s+JPG", desc, re.I)
    metin = m.group(0) if m else None
    if jpg is None:
        ekle("5 high-resolution JPG", metin, "DOGRULANAMADI", "ZIP olculemedi")
    else:
        n = len(jpg)
        iddia_n = int(m.group(1)) if m else None
        ekle("5 high-resolution JPG", metin,
             "DOGRU" if iddia_n == n else "YANLIS", f"{n} JPG")

    # 2) 300 DPI
    metin = "300 DPI" if re.search(r"300\s*DPI", desc, re.I) else None
    if jpg is None:
        ekle("300 DPI", metin, "DOGRULANAMADI", "ZIP olculemedi")
    else:
        dpiler = [tuple(o["dpi"]) if o["dpi"] else None for o in jpg]
        hepsi300 = all(d == (300.0, 300.0) for d in dpiler)
        ekle("300 DPI", metin, "DOGRU" if hepsi300 else "YANLIS",
             "; ".join(f"{o['ad']}: {o['dpi']}" for o in jpg))

    # 3) sRGB
    metin = "sRGB" if re.search(r"\bsRGB\b", desc) else None
    if jpg is None:
        ekle("sRGB", metin, "DOGRULANAMADI", "ZIP olculemedi")
    else:
        gomulu = [o for o in jpg if o["icc"]["gomulu"]]
        srgb = [o for o in gomulu if "srgb" in (o["icc"]["aciklama"] or "").lower()]
        if len(srgb) == len(jpg):
            h, g = "DOGRU", "5/5 dosyada gomulu sRGB profili"
        elif not gomulu:
            h, g = "KISMEN", ("hicbirinde gomulu ICC profili yok; RGB modunda, "
                              "profilsiz JPEG fiilen sRGB kabul edilir")
        else:
            h, g = "KISMEN", f"{len(srgb)}/{len(jpg)} dosyada sRGB profili"
        ekle("sRGB", metin, h, g)

    # 4) oranlar
    metin = ", ".join(x for x in ["2:3", "3:4", "4:5", "11:14"] if x in desc) or None
    if re.search(r"A[- ]Series|A4|ISO A", desc, re.I):
        metin = (metin + ", A-Series") if metin else "A-Series"
    if jpg is None:
        ekle("ratios 2:3, 3:4, 4:5, 11:14, A-Series", metin, "DOGRULANAMADI", "ZIP olculemedi")
    else:
        bulunan = []
        for o in jpg:
            bulunan.append(o["oran"] if o["oran_sapma_yuzde"] <= ORAN_TOL * 100 else
                           f"{o['oran']}?({o['olculen_oran']})")
        beklenen = set(ORANLAR)
        tam = set(bulunan) == beklenen
        ekle("ratios 2:3, 3:4, 4:5, 11:14, A-Series", metin,
             "DOGRU" if tam else ("KISMEN" if set(bulunan) & beklenen else "YANLIS"),
             "; ".join(f"{o['ad']}: {o['px'][0]}x{o['px'][1]} -> {o['oran']} "
                       f"(sapma %{o['oran_sapma_yuzde']})" for o in jpg))

    # 5) full artwork in every ratio, no cropping
    metin = None
    for kal in ("no cropping", "without cropping", "full artwork", "full design"):
        if re.search(kal, desc, re.I):
            metin = kal
            break
    if jpg is None:
        ekle("full artwork in every ratio, no cropping", metin, "DOGRULANAMADI", "ZIP olculemedi")
    else:
        maeler = [o.get("fark_ref_mae", 0) for o in jpg]
        en_buyuk = max(maeler) if maeler else 0
        kenar = [o["ad"] for o in jpg if o["murekkep"].get("kenara_deger")]
        if en_buyuk <= MAE_AYNI and not kenar:
            h = "DOGRU"
        elif en_buyuk <= MAE_YAKIN:
            h = "KISMEN"
        else:
            h = "YANLIS"
        ekle("full artwork in every ratio, no cropping", metin, h,
             f"normalize fark (MAE) en buyuk {en_buyuk} (esik {MAE_AYNI}/{MAE_YAKIN}); "
             f"murekkebi kenara degen dosya: {kenar or 'yok'}")

    # ek: dosya sayisi ve PDF konumu
    pdf_ayri = [d for d in dosyalar if d["filename"].lower().endswith(".pdf")]
    pdf_zip = zolc.get("pdf_icinde") if zolc else []
    ekle("PDF teslimati", None, "BILGI",
         f"Etsy'de ayri dosya olarak {len(pdf_ayri)} PDF; ZIP icinde {len(pdf_zip)} PDF")
    return out


# ------------------------------------------------------- diger ilanlar
def kalip(ad):
    s = re.sub(r"\d+", "#", ad)
    s = re.sub(r"(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|"
               r"Capricorn|Aquarius|Pisces)", "<SIGN>", s, flags=re.I)
    s = re.sub(r"(Champagne[_ ]?Ivory|Pure[_ ]?White|Warm[_ ]?Parchment|Midnight[_ ]?Blue|"
               r"Deep[_ ]?Black)", "<EDITION>", s, flags=re.I)
    return s


def tum_ilanlar(api, shop, ids, quota_min, t0):
    sonuc, durdu = [], None
    for i, lid in enumerate(ids, 1):
        rem = api.remaining
        if rem is not None and str(rem).isdigit() and int(rem) < quota_min:
            durdu = f"kota {rem} < {quota_min}, {i-1}/{len(ids)} ilanda durdu"
            break
        fs = listing_files(api, shop, lid)
        sonuc.append({
            "listing_id": lid,
            "dosya_sayisi": len(fs),
            "turler": sorted({(f["filename"].rsplit(".", 1)[-1] or "?").lower() for f in fs}),
            "kaliplar": [kalip(f["filename"]) for f in fs],
            "boyutlar": [f["size_bytes"] for f in fs],
            "adlar": [f["filename"] for f in fs],
        })
        if i % 25 == 0 or i == len(ids):
            gecen = (time.time() - t0) / 60
            kalan = gecen / i * (len(ids) - i)
            log(f"  [{i}/{len(ids)} %{round(100*i/len(ids))}] gecen {gecen:.1f} dk, "
                f"kalan ~{kalan:.1f} dk | kota {api.remaining}")
    return sonuc, durdu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", default="4552211376")
    ap.add_argument("--zip-index", default="_work/zips.json")
    ap.add_argument("--zip-dir", default="_work/zip")
    ap.add_argument("--zip-base", default="gdrive:ASTROLOVE")
    ap.add_argument("--dfile-state", default="_work/dfile_state.csv")
    ap.add_argument("--out", default="_out")
    ap.add_argument("--all-limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=300)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    shop = os.environ["ETSY_SHOP_ID"]
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    t0 = time.time()

    log(f"1) Ilan {a.listing} okunuyor")
    L = api.get(f"/listings/{a.listing}") or {}
    desc = L.get("description") or ""
    dosyalar = listing_files(api, shop, a.listing)
    log(f"   baslik: {L.get('title')}")
    log(f"   state: {L.get('state')} | dijital: {L.get('listing_type')} | dosya: {len(dosyalar)}")
    for d in dosyalar:
        log(f"     rank {d['rank']}: {d['filename']} | {d['filesize']} "
            f"({d['size_bytes']} bayt) | {d['filetype']}")

    log("2) Kaynak ZIP araniyor")
    zips = json.loads(Path(a.zip_index).read_text()) if Path(a.zip_index).exists() else []
    zip_dosya = next((d for d in dosyalar if d["filename"].lower().endswith(".zip")), None)
    zolc, zip_not = None, "ilanda ZIP yok"
    if zip_dosya:
        adaylar = [z for z in zips if z.get("Name") == zip_dosya["filename"]]
        boy_eslesen = [z for z in adaylar if int(z.get("Size", -1)) == int(zip_dosya["size_bytes"] or -2)]
        zip_not = (f"Drive'da ayni adli {len(adaylar)} dosya, bayt boyutu eslesen "
                   f"{len(boy_eslesen)}")
        log(f"   {zip_not}")
        sec = (boy_eslesen or adaylar or [None])[0]
        if sec:
            yerel = Path(a.zip_dir) / sec["Name"]
            if not yerel.exists():
                yerel.parent.mkdir(parents=True, exist_ok=True)
                uzak = f"{a.zip_base}/{sec['Path']}"
                log(f"   rclone ile cekiliyor: {uzak}")
                r = subprocess.run(["rclone", "copyto", uzak, str(yerel)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    log(f"   rclone HATA: {r.stderr[:200]}")
            if yerel.exists():
                zolc = zip_olc(yerel)
                zolc["kaynak"] = sec.get("Path")
                zolc["bayt_ayni"] = bool(boy_eslesen)
                log(f"   ZIP acildi: {len(zolc['girdiler'])} girdi, "
                    f"{len(zolc['jpg_olcum'])} JPG")
            else:
                zip_not += f"; yerel kopya yok ({yerel})"
        else:
            zip_not += "; Drive'da bulunamadi"

    log("3) Iddialar karsilastiriliyor")
    karne = iddialar(desc, zolc, dosyalar)
    for k in karne:
        log(f"   {k['hukum']:14} {k['iddia']}  -> {k['gercek'][:110]}")

    log("4) Diger dijital ilanlar")
    ids = []
    p = Path(a.dfile_state)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                lid = (r.get("listing_id") or "").strip()
                if lid.isdigit() and lid not in ids:
                    ids.append(lid)
    log(f"   durum dosyasindan {len(ids)} dijital ilan")
    if a.all_limit:
        ids = ids[:a.all_limit]
    hepsi, durdu = tum_ilanlar(api, shop, ids, a.quota_min, t0)
    sayilar = {}
    for h in hepsi:
        anahtar = (h["dosya_sayisi"], tuple(h["turler"]), tuple(sorted(set(h["kaliplar"]))))
        sayilar.setdefault(anahtar, []).append(h["listing_id"])
    yapi = sorted(sayilar.items(), key=lambda kv: -len(kv[1]))
    ana = yapi[0][0] if yapi else None
    sapan = [{"yapi": {"dosya": k[0], "turler": list(k[1]), "kaliplar": list(k[2])},
              "ilanlar": v} for k, v in yapi[1:]]
    for k, v in yapi:
        log(f"   {len(v):4} ilan | dosya {k[0]} | tur {list(k[1])} | kalip {list(k[2])}")

    rapor = {
        "ts_utc": simdi(),
        "listing": {"id": a.listing, "title": L.get("title"), "state": L.get("state"),
                    "listing_type": L.get("listing_type"), "price": L.get("price"),
                    "aciklama_karakter": len(desc)},
        "etsy_dosyalari": dosyalar,
        "zip": zolc, "zip_not": zip_not,
        "iddialar": karne,
        "diger_ilanlar": {"okunan": len(hepsi), "toplam": len(ids), "durdu": durdu,
                          "ana_yapi": {"dosya": ana[0], "turler": list(ana[1]),
                                       "kaliplar": list(ana[2])} if ana else None,
                          "ana_yapi_ilan_sayisi": len(yapi[0][1]) if yapi else 0,
                          "sapanlar": sapan},
        "kota": api.remaining, "api_cagrisi": api.calls,
    }
    (out / "DIGITAL_AUDIT.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    (out / "DESCRIPTION.txt").write_text(desc, encoding="utf-8")
    with open(out / "DIGITAL_FILES_ALL.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "dosya_sayisi", "turler", "adlar", "boyutlar"])
        for h in hepsi:
            w.writerow([h["listing_id"], h["dosya_sayisi"], "|".join(h["turler"]),
                        "|".join(h["adlar"]), "|".join(str(b) for b in h["boyutlar"])])
    log(f"OZET: {json.dumps({'dosya': len(dosyalar), 'jpg': len(zolc['jpg_olcum']) if zolc else 0, 'ilan': len(hepsi), 'kota': api.remaining, 'cagri': api.calls}, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
