#!/usr/bin/env python3
"""78 POD ilaninda kapak degisimi: v9 kapagi 1. siraya yukle, eski 1. sira kapagi yedekleyip sil
(Serdar acik onayi 28 Eyl: eski kapaklar silinecek; "Silme YOK" yalniz bu adim icin kalkar).
Kapak kaynagi TEK: Drive TEMP/POD_KAPAK_78/<en son damga>/KAPAK_<CIFT>.jpg (3000x2250, OZET 78/78 PASS).
updateListing CAGRILMAZ.

KURU (varsayilan, Etsy'ye yazma yok):
  1. on kontrol: 78 ilan state, gorsel sayisi, rank 1 image_id; eslesmeyen cift, 20 gorseli dolu,
     active disi -> BLOK. Eski kapaga bagli varyasyon (renk) degerleri "bag tasi" olarak planlanir.
  2. yedek: tum galeri listesi GALERI_ONCE.json + eski rank 1 dosyalarinin KENDISI
     --out/yedek/<listing_id>_<image_id>.jpg (workflow Drive TEMP/KAPAK78_YEDEK_<damga>/'ya yazar)
  3. PLAN.json (apply bu dosyaya kilitli) + PLAN.csv + report.md (silinecek image_id listesi)
  Durum: PLAN | ZATEN (1. sirada zaten bu kapak: alt metin + boyut) | BLOK (neden yazilir).

APPLY (--apply --confirm KAPAK78_YUKLE_SIL --plan PLAN.json --yedek-drive HEDEF): planda BLOK varsa ya da
kapak sha256/alt metni plandan farkliysa hicbir yazma yapilmaz. Ilan basina (ilk hatada DUR):
  0. canli durum = plan (state active, 1. sira = plandaki eski id, galeri id sirasi ayni)
  1. eski rank 1 dosyasi HEDEF/<listing_id>_<image_id>.jpg olarak Drive'da mi (boyut = plandaki);
     yoksa indirilir, dogrulanir, yazilir ve hedefte boyutu geri okunur
  2. yeni kapak rank=1 yuklenir; geri okuma: 1. sira yeni, sayi +1, eski gorseller 2..n+1
  2b. (yalniz bagli ilanlar; Serdar karari 28 Eyl) varyasyon baglarinin TAMAMI okunur, Drive'a yedeklenir
     (<listing_id>_VARYASYON_ONCE.json); updateVariationImages ile yalniz eski kapaga bagli deger(ler)
     yeni kapaga tasinir, tam liste geri gonderilir; geri okuma: bag yeni kapakta, diger baglar ayni
  3. yalniz onceki adimlar PASS ise plandaki eski image_id deleteListingImage ile silinir
  4. geri okuma: sayi = onceki, 1. sira = yeni, eski id yok, kalanlar ayni sira, varyasyon baglari,
     videolar, state active (bagli ilanda varyasyon = tasinmis beklenen liste)
Her ilandan sonra SONUC.json yazilir. ETA sayaci: islenen/toplam, gecen, kalan, yuzde.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim:
  kapak_yukle_78.py --kapak-dir K --kaynak-bilgi K.json --out OUT                      (kuru)
  kapak_yukle_78.py --kapak-dir K --out OUT --plan PLAN.json \\
      --yedek-drive gdrive:ASTROLOVE/TEMP/KAPAK78_YEDEK_<damga> --apply --confirm KAPAK78_YUKLE_SIL
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_cover_from_video import (  # noqa: E402
    eventually, gallery, variation_images, variation_map, video_ids, videos,
)

KOK = pathlib.Path(__file__).resolve().parents[2]
ONAY = "KAPAK78_YUKLE_SIL"
ETSY_MAX = 20
BEKLENEN = 78
KAPAK_BOYUT = (3000, 2250)
CAGRI_ILAN = 14  # apply'da ilan basina tahmini Etsy cagrisi (okuma + yukleme + silme + geri okuma)
OKUMA_BEKLE = 3
SIRA_DENEME, SIRA_BEKLE = 5, 5  # siralar tekillesene kadar en fazla 5 x 5 sn (Serdar 28 Eyl)
YUKLEME_BEKLE = 5  # yuklemeden sonra rank cagrisina kadar (Serdar 28 Eyl)
KOTA_TABAN = 150  # altina dusunce yeni ilana baslanmaz (router rezervi 150, Serdar 28 Eyl)


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def alt_metin(a, b):
    return f"{a} and {b} personalized zodiac couple wall art, Midnight Blue print in a polished gold frame"


def indir(url, yol):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    pathlib.Path(yol).write_bytes(r.content)


def dosya_dogrula(yol, w, h):
    """Indirilen gorsel: >=10 KB, acilir, boyut Etsy'nin full_width/full_height'i ile ayni."""
    p = pathlib.Path(yol)
    if not p.is_file() or p.stat().st_size < 10000:
        return f"dosya yok ya da kucuk ({p.stat().st_size if p.is_file() else 0} bayt)"
    try:
        with Image.open(p) as im:
            im.load()
            boy = im.size
    except Exception as e:  # noqa: BLE001
        return f"acilmadi: {e}"
    if w and h and boy != (int(w), int(h)):
        return f"boyut {boy[0]}x{boy[1]} != Etsy {w}x{h}"
    return ""


def drive_liste(hedef_dizin):
    """Hedef yedek dizinindeki {ad: boyut}. gdrive: -> rclone lsjson; aksi halde yerel dizin (test)."""
    if hedef_dizin.startswith("gdrive:"):
        r = subprocess.run(["rclone", "lsjson", hedef_dizin, "--files-only"], capture_output=True, text=True)
        if r.returncode != 0:
            return {}
        return {x["Name"]: x.get("Size") for x in json.loads(r.stdout or "[]")}
    d = pathlib.Path(hedef_dizin)
    return {p.name: p.stat().st_size for p in d.iterdir()} if d.is_dir() else {}


def drive_yaz(yerel, hedef_dizin, ad):
    """Yedegi hedefe yazar ve hedefteki boyutu geri okur."""
    boyut = pathlib.Path(yerel).stat().st_size
    if hedef_dizin.startswith("gdrive:"):
        hedef = f"{hedef_dizin.rstrip('/')}/{ad}"
        subprocess.run(["rclone", "copyto", str(yerel), hedef, "-q"], check=True)
        r = subprocess.run(["rclone", "lsjson", hedef], check=True, capture_output=True, text=True)
        liste = json.loads(r.stdout or "[]")
        uzak = liste[0].get("Size") if liste else None
    else:
        hedef = pathlib.Path(hedef_dizin) / ad
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(yerel, hedef)
        uzak = hedef.stat().st_size
    return str(hedef), uzak == boyut, boyut, uzak


def kapaklar_oku(ids_csv, kapak_dir):
    """Donus: (ilan satirlari, {cift: kapak}, {cift: sorun}, ilanda olmayan kapak dosyalari)."""
    satirlar = list(csv.DictReader(open(ids_csv, encoding="utf-8")))
    ciftler = {s["cift"] for s in satirlar}
    kapak, sorun = {}, {}
    for s in satirlar:
        c = s["cift"]
        p = pathlib.Path(kapak_dir) / f"KAPAK_{c}.jpg"
        if not p.is_file():
            sorun[c] = f"kapak yok ({p.name})"; continue
        with Image.open(p) as im:
            w, h = im.size
        if (w, h) != KAPAK_BOYUT:
            sorun[c] = f"kapak {w}x{h} != {KAPAK_BOYUT[0]}x{KAPAK_BOYUT[1]}"; continue
        kapak[c] = {"dosya": p.name, "sha256": sha(p), "bayt": p.stat().st_size, "w": w, "h": h,
                    "alt": alt_metin(s["a"], s["b"])}
    fazla = sorted(p.name for p in pathlib.Path(kapak_dir).glob("KAPAK_*.jpg")
                   if p.name[len("KAPAK_"):-len(".jpg")] not in ciftler)
    return satirlar, kapak, sorun, fazla


def durum(api, shop, lid):
    return {"state": (api.get(f"/listings/{lid}") or {}).get("state"),
            "galeri": gallery(api, lid),
            "varyasyon": variation_map(variation_images(api, shop, lid)),
            "video": video_ids(videos(api, lid))}


def ids_of(g):
    return [int(x["listing_image_id"]) for x in g]


# ------------------------------------------------------------------ kuru
def kuru(a, api, shop, out, satirlar, kapak, sorun, fazla):
    plan, galeri_once = [], {}
    t0 = time.time()
    yedek_dir = out / "yedek"
    yedek_dir.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(satirlar, 1):
        lid, c = str(s["listing_id"]), s["cift"]
        k = kapak.get(c) or {}
        st = (api.get(f"/listings/{lid}", ok404=True) or {}).get("state")
        g = gallery(api, lid)
        vham = variation_images(api, shop, lid)
        vmap = variation_map(vham)
        galeri_once[lid] = {"cift": c, "state": st, "galeri": g, "varyasyon": vmap}
        r1 = g[0] if g else {}
        eski_id = int(r1["listing_image_id"]) if r1 else None
        row = {"listing_id": lid, "cift": c, "state": st, "galeri_sayisi": len(g), "galeri_ids": ids_of(g),
               "eski_rank1_id": eski_id, "eski_rank1_alt": r1.get("alt_text"),
               "eski_rank1_boyut": [r1.get("full_width"), r1.get("full_height")],
               "eski_rank1_url": r1.get("url_fullxfull"),
               "yeni_kapak": k.get("dosya"), "yeni_sha256": k.get("sha256"), "yeni_boyut": [k.get("w"), k.get("h")],
               "yeni_alt": k.get("alt"), "durum": "PLAN", "neden": ""}
        neden = []
        if c in sorun:
            neden.append(f"eslesmeyen cift: {sorun[c]}")
        if st != "active":
            neden.append(f"state {st}")
        if not g:
            neden.append("galeri bos")
        elif k and c not in getattr(a, "yenile", set()) and (r1.get("alt_text") == k["alt"]
                                          and (r1.get("full_width"), r1.get("full_height")) == (k["w"], k["h"])):
            row["durum"] = "ZATEN"
        else:
            if c in getattr(a, "yenile", set()):
                row["yenile"] = True           # ayni alt+boyutta DUZELTILMIS kapak (28 Eyl Terazi): yine de degistir
            if int(r1.get("rank") or 0) != 1:
                neden.append(f"ilk gorsel rank {r1.get('rank')}")
            row["varyasyon_once"] = [list(v) for v in vmap]
            row["bag_tasi"] = [{"property_id": v.get("property_id"), "value_id": v.get("value_id"),
                                "value": v.get("value")} for v in vham if str(v.get("image_id")) == str(eski_id)]
            if len(g) + 1 > ETSY_MAX:
                neden.append(f"galeri {len(g)} dolu (+1 > {ETSY_MAX})")
            yol = yedek_dir / f"{lid}_{eski_id}.jpg"
            try:
                indir(r1["url_fullxfull"], yol)
                sorun_d = dosya_dogrula(yol, r1.get("full_width"), r1.get("full_height"))
            except Exception as e:  # noqa: BLE001
                sorun_d = f"indirilemedi: {e}"
            if sorun_d:
                neden.append(f"eski kapak dosyasi: {sorun_d}")
                yol.unlink(missing_ok=True)
            else:
                row["eski_dosya"] = yol.name
                row["eski_dosya_bayt"] = yol.stat().st_size
                row["eski_dosya_sha256"] = sha(yol)
        if neden:
            row["durum"], row["neden"] = "BLOK", "; ".join(neden)
        plan.append(row)
        gec = time.time() - t0
        log(f"[{i}/{len(satirlar)}] {lid} {c} {row['durum']} {row['neden']} | eski {eski_id} | galeri {len(g)} | "
            f"gecen {gec:.0f}s | kalan ~{gec / i * (len(satirlar) - i):.0f}s | %{i * 100 // len(satirlar)} | kota {api.remaining}")

    (yedek_dir / "GALERI_ONCE.json").write_text(
        json.dumps({"olusturma": simdi(), "ilanlar": galeri_once}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    say = {d: sum(r["durum"] == d for r in plan) for d in ("PLAN", "ZATEN", "BLOK")}
    ok = say["PLAN"] + say["ZATEN"] == BEKLENEN and say["BLOK"] == 0 and not fazla
    (out / "PLAN.json").write_text(json.dumps({"olusturma": simdi(), "onay": ONAY, "kaynak": a.kaynak,
                                               "satirlar": plan}, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["listing_id", "cift", "durum", "neden", "state", "galeri_sayisi", "eski_rank1_id",
                     "eski_rank1_boyut", "yeni_kapak", "yeni_alt"])
        for r in plan:
            wr.writerow([r["listing_id"], r["cift"], r["durum"], r["neden"], r["state"], r["galeri_sayisi"],
                         r["eski_rank1_id"], "x".join(map(str, r["eski_rank1_boyut"])), r["yeni_kapak"], r["yeni_alt"]])
    silinecek = [r for r in plan if r["durum"] == "PLAN"]
    kota = int(api.remaining) if api.remaining is not None else None
    gerek = len(silinecek) * CAGRI_ILAN
    kb = a.kaynak or {}
    cl = kb.get("cancer_libra") or {}
    ornek = sorted(k["dosya"] for k in kapak.values())[:3]
    sat = [f"# KAPAK78 yukle + eski kapak sil: KURU KOSU ({simdi()})", "",
           f"- PLAN {say['PLAN']} | ZATEN {say['ZATEN']} | BLOK {say['BLOK']} | toplam {len(plan)} | "
           f"ilanda olmayan kapak {len(fazla)} | SONUC: {'PASS' if ok else 'FAIL'}",
           f"- Kaynak: {kb.get('klasor')} ({len(kapak)} kapak, {kb.get('ozet')}) | ornek: {', '.join(ornek)}",
           f"- KAPAK_CANCER_LIBRA.jpg: {kapak.get('CANCER_LIBRA', {}).get('w')}x{kapak.get('CANCER_LIBRA', {}).get('h')}, "
           f"{cl.get('Size')} bayt, Drive tarihi {cl.get('ModTime')}",
           f"- Etsy kota kalan {kota} | apply tahmini ~{gerek} cagri ({CAGRI_ILAN}/ilan) | "
           f"{'yeterli' if kota is None or kota - gerek >= a.quota_min else 'YETERSIZ'}",
           f"- Yedek: {a.yedek_drive or 'out/yedek'}/ ({sum(1 for r in plan if r.get('eski_dosya'))} eski kapak dosyasi + GALERI_ONCE.json)",
           f"- Yeni alt metin ornegi: {plan[0]['yeni_alt'] if plan else ''}", ""]
    engel = [r for r in plan if r["durum"] != "PLAN"]
    if engel or fazla:
        sat += ["## BLOK / ZATEN / eslesmeyen", ""]
        sat += [f"- {r['listing_id']} {r['cift']}: {r['durum']} {r['neden']}" for r in engel]
        sat += [f"- ilanda olmayan kapak dosyasi: {f}" for f in fazla] + [""]
    tasi = [r for r in silinecek if r.get("bag_tasi")]
    sat += [f"## Bag tasinacak {len(tasi)} ilan (updateVariationImages; eski -> yeni, yeni id yuklemede belli olur)", "",
            "| # | listing_id | cift | renk degeri | eski image_id -> yeni |", "|---|---|---|---|---|"]
    sat += [f"| {j} | {r['listing_id']} | {r['cift']} | {', '.join(str(b['value']) for b in r['bag_tasi'])} | "
            f"{r['eski_rank1_id']} -> YENI KAPAK |" for j, r in enumerate(tasi, 1)] + [""]
    sat += [f"## Silinecek {len(silinecek)} image_id (eski rank 1)", "",
            "| # | listing_id | cift | state | galeri | silinecek image_id | boyut | yedek |",
            "|---|---|---|---|---|---|---|---|"]
    sat += [f"| {j} | {r['listing_id']} | {r['cift']} | {r['state']} | {r['galeri_sayisi']} | {r['eski_rank1_id']} | "
            f"{'x'.join(map(str, r['eski_rank1_boyut']))} | {r.get('eski_dosya', '-')} |"
            for j, r in enumerate(silinecek, 1)]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    (out / "SILINECEK_IMAGE_ID.txt").write_text(
        "".join(f"{r['listing_id']},{r['eski_rank1_id']}\n" for r in silinecek), encoding="utf-8")
    for x in sat[2:8]:
        log(x)
    log(f"- bag tasinacak {len(tasi)} ilan | bagsiz {len(silinecek) - len(tasi)} ilan")
    return ok


# ------------------------------------------------------------------ apply
def sira_tekil(g):
    """Siralar tekil (ayni rank'ta iki gorsel yok). Ardisiklik aranmaz: Etsy silmeden sonra
    siralari sikistirmayabilir (28 Eyl 4570110641: 1, 3, 4..14)."""
    r = [int(x.get("rank") or 0) for x in g]
    return len(set(r)) == len(r) and all(v >= 1 for v in r)


def img(g, iid):
    return next((x for x in g if int(x["listing_image_id"]) == int(iid)), None)


def sira_bekle(api, lid):
    """Siralar tekil olana kadar en fazla SIRA_DENEME x SIRA_BEKLE sn (Serdar 28 Eyl)."""
    return eventually(lambda: gallery(api, lid), sira_tekil, attempts=SIRA_DENEME, pause=SIRA_BEKLE)


def zaten_mi(p, once, base):
    """Ilan onceki kosuda tamamlanmis mi: eski yok, sayi ayni, 1. sira plandaki yeni alt + boyut, bag yeni kapakta."""
    g, eski = once["galeri"], int(p["eski_rank1_id"])
    if not g or eski in ids_of(g) or len(g) != len(base) or not sira_tekil(g):
        return False
    r1 = g[0]
    if int(r1["listing_image_id"]) in base or r1.get("alt_text") != p["yeni_alt"] \
            or [r1.get("full_width"), r1.get("full_height")] != list(p["yeni_boyut"]):
        return False
    if ids_of(g)[1:] != base[1:]:
        return False
    bag = {(b["property_id"], b["value_id"]) for b in p.get("bag_tasi") or []}
    return all(str(v[3]) == str(r1["listing_image_id"]) for v in once["varyasyon"] if (v[0], v[1]) in bag)


def ilan_uygula(a, api, shop, out, p, kapak_yol, drive_var):
    """Tek ilan. Donus: (sonuc_dict, hata_metni). hata_metni bos degilse DUR.
    Eski kapak = plandaki image_id, yeni kapak = yukleme yanitindaki (ya da --devam ile verilen) image_id;
    Etsy siralamasindan tahmin edilmez."""
    lid, eski = p["listing_id"], int(p["eski_rank1_id"])
    base = [int(x) for x in p["galeri_ids"]]
    devam = a.devam.get(str(lid))
    r = {"listing_id": lid, "cift": p["cift"], "eski_id": eski, "yeni_id": devam, "adimlar": {}}

    # 0. canli durum = plan (ya da onceki kosuda tamamlanmis / --devam ile verilen yarim durum)
    once = durum(api, shop, lid)
    oids = ids_of(once["galeri"])
    (out / "ilan" / f"{lid}_ONCE.json").write_text(json.dumps(once, ensure_ascii=False, indent=1, default=str))
    if not devam and zaten_mi(p, once, base):
        r["zaten"] = True
        r["yeni_id"] = oids[0]
        return r, ""
    k0 = {"state active": once["state"] == "active",
          "varyasyon baglari plandaki ile ayni": [list(v) for v in once["varyasyon"]] == p.get("varyasyon_once"),
          f"galeri {len(base)} + 1 <= {ETSY_MAX}": len(base) + 1 <= ETSY_MAX,
          f"plandaki eski {eski} galeride": eski in oids}
    if devam:
        k0[f"--devam eski = plandaki {eski}"] = getattr(a, "devam_eski", {}).get(str(lid), eski) == eski
        k0[f"galeri = plan + yalniz {devam}"] = sorted(oids) == sorted(base + [devam]) and devam not in base
        dv = img(once["galeri"], devam) or {}
        k0[f"{devam} boyutu {p['yeni_boyut']}"] = [dv.get("full_width"), dv.get("full_height")] == list(p["yeni_boyut"])
    else:
        k0["siralar tekil"] = sira_tekil(once["galeri"])
        k0[f"1. sira = plandaki {eski}"] = oids[:1] == [eski]
        k0["galeri id sirasi plandaki ile ayni"] = oids == base
    r["adimlar"]["0_on_kontrol"] = k0
    if not all(k0.values()):
        return r, "on kontrol FAIL: " + ", ".join(k for k, v in k0.items() if not v)

    # 1. eski kapagin DOSYASI Drive yedeginde mi; yoksa indir + yaz + geri oku
    ad = f"{lid}_{eski}.jpg"
    if p.get("eski_dosya_bayt") and drive_var.get(ad) == p["eski_dosya_bayt"]:
        r["yedek"] = f"{a.yedek_drive}/{ad}"
        r["adimlar"]["1_yedek"] = {f"yedek Drive'da ({drive_var[ad]} bayt = kuru kosu)": True}
    else:
        r1 = img(once["galeri"], eski)
        yol = out / "yedek" / ad
        try:
            indir(r1["url_fullxfull"], yol)
            sorun = dosya_dogrula(yol, r1.get("full_width"), r1.get("full_height"))
        except Exception as e:  # noqa: BLE001
            sorun = f"indirilemedi: {e}"
        if sorun:
            return r, f"yedek FAIL: {sorun}"
        try:
            hedef, esit, yb, ub = drive_yaz(yol, a.yedek_drive, ad)
        except Exception as e:  # noqa: BLE001
            return r, f"yedek Drive'a yazilamadi: {e}"
        r["yedek"] = hedef
        r["adimlar"]["1_yedek"] = {f"yedek Drive'a yazildi ({yb} bayt)": esit}
        if not esit:
            return r, f"yedek FAIL: hedef boyutu {ub} != {yb}"

    # 2. yeni kapak rank 1 (ya da --devam: verilen id'ye alt metin + rank 1) + geri okuma
    if api.remaining is not None and int(api.remaining) < a.quota_min:
        return r, f"kota {api.remaining} < {a.quota_min}"

    def rank1_alt(iid):
        """Rank duzeltme HER ZAMAN alt metinle birlikte gonderilir."""
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, str(iid)), "rank": (None, "1"),
                             "alt_text": (None, p["yeni_alt"])})

    if devam:
        yeni = int(devam)
    else:
        with open(kapak_yol, "rb") as fh:
            up = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                               files={"image": (kapak_yol.name, fh, "image/jpeg")},
                               data={"rank": "1", "alt_text": p["yeni_alt"]})
        yeni = int(up.get("listing_image_id") or 0)
    r["yeni_id"] = yeni
    if not yeni or yeni in base:
        return r, f"yukleme: yeni listing_image_id gecersiz ({yeni})"
    # Serdar 28 Eyl: yuklemeden 5 sn sonra alt metinli rank 1 cagrisi -> 5 x 5 sn tekillik; tekil degilse
    # cagri 1 kez daha -> 5 x 5 sn. Hala tekil degilse ilan YARIM (yeni kapak var; eski kapak + bag yerinde).
    if not devam:
        time.sleep(YUKLEME_BEKLE)
    g = []
    for deneme in (1, 2):
        log(f"  {lid}: {yeni} alt metin + rank 1 ({deneme}. cagri{', devam' if devam else ''})")
        rank1_alt(yeni)
        g = sira_bekle(api, lid)
        if sira_tekil(g):
            break
    if not sira_tekil(g):
        r["yarim"] = True
        (out / "ilan" / f"{lid}_YARIM.json").write_text(json.dumps(g, ensure_ascii=False, indent=1, default=str))
        return r, ""
    yg = img(g, yeni) or {}
    gi = ids_of(g)
    k2 = {"siralar tekil": sira_tekil(g),
          f"{yeni} rank 1": int(yg.get("rank") or 0) == 1,
          "yeni kapak alt metni dolu + plandaki": bool(yg.get("alt_text")) and yg.get("alt_text") == p["yeni_alt"],
          f"gorsel sayisi {len(base)} + 1": len(gi) == len(base) + 1,
          "plandaki gorseller ayni id + sira (2..n+1)": gi[1:] == base}
    r["adimlar"]["2_yukle_geri_oku"] = k2
    (out / "ilan" / f"{lid}_YUKLEME_SONRASI.json").write_text(json.dumps(g, ensure_ascii=False, indent=1, default=str))
    if not all(k2.values()):
        return r, "yukleme geri okuma FAIL (eski kapak SILINMEDI): " + ", ".join(k for k, v in k2.items() if not v)

    # 2b. bagli ilan: tum baglar yedeklenir, yalniz eski kapaga bagli deger(ler) yeni kapaga tasinir
    bek_var = once["varyasyon"]
    if p.get("bag_tasi"):
        ham = variation_images(api, shop, lid)
        if variation_map(ham) != once["varyasyon"]:
            return r, "bag tasima: varyasyon baglari yuklemeden sonra degismis (eski kapak SILINMEDI)"
        vad = f"{lid}_VARYASYON_ONCE.json"
        vyol = out / "yedek" / vad
        vyol.write_text(json.dumps({"listing_id": lid, "eski_kapak": eski, "yeni_kapak": yeni,
                                    "variation_images": ham}, ensure_ascii=False, indent=1, default=str))
        try:
            _, esit, yb, ub = drive_yaz(vyol, a.yedek_drive, vad)
        except Exception as e:  # noqa: BLE001
            return r, f"varyasyon yedegi Drive'a yazilamadi: {e}"
        if not esit:
            return r, f"varyasyon yedegi FAIL: hedef boyutu {ub} != {yb}"
        yeni_liste = [{"property_id": v.get("property_id"), "value_id": v.get("value_id"),
                       "image_id": yeni if str(v.get("image_id")) == str(eski) else v.get("image_id")} for v in ham]
        bek_var = sorted((v[0], v[1], v[2], yeni if str(v[3]) == str(eski) else v[3]) for v in once["varyasyon"])
        tasinan = [v for v in ham if str(v.get("image_id")) == str(eski)]
        r["bag_tasi"] = [{"value": v.get("value"), "eski": eski, "yeni": yeni} for v in tasinan]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": yeni_liste})
        vs = eventually(lambda: variation_map(variation_images(api, shop, lid)), lambda m: m == bek_var,
                        attempts=10, pause=OKUMA_BEKLE)
        k2b = {f"varyasyon yedegi Drive'da ({yb} bayt)": esit,
               f"{len(tasinan)} bag yeni kapakta": all(any(x[1] == v.get("value_id") and str(x[3]) == str(yeni)
                                                          for x in vs) for v in tasinan),
               "diger baglar ayni": [x for x in vs if str(x[3]) != str(yeni)]
               == [x for x in once["varyasyon"] if str(x[3]) != str(eski)],
               "eski kapaga bag kalmadi": not any(str(x[3]) == str(eski) for x in vs)}
        r["adimlar"]["2b_bag_tasi"] = k2b
        if not all(k2b.values()):
            return r, "bag tasima geri okuma FAIL (eski kapak SILINMEDI): " + ", ".join(k for k, v in k2b.items() if not v)

    # 3. yalniz plandaki eski image_id silinir
    api.delete(f"/shops/{shop}/listings/{lid}/images/{eski}")

    # 4. geri okuma
    beklenen = [yeni] + base[1:]

    def k4_of(st):
        s = ids_of(st["galeri"])
        yg4 = img(st["galeri"], yeni) or {}
        return {f"gorsel sayisi = onceki ({len(base)})": len(s) == len(base),
                "siralar tekil": sira_tekil(st["galeri"]),
                f"{yeni} rank 1": int(yg4.get("rank") or 0) == 1,
                "yeni kapak alt metni dolu + plandaki": bool(yg4.get("alt_text")) and yg4.get("alt_text") == p["yeni_alt"],
                f"{eski} silindi": eski not in s,
                "kalan gorseller ayni id + sira": s == beklenen,
                "varyasyon gorsel baglari beklenen": st["varyasyon"] == bek_var,
                "videolar ayni": st["video"] == once["video"],
                "ilan active": st["state"] == "active"}

    sonra = eventually(lambda: durum(api, shop, lid), lambda st: all(k4_of(st).values()),
                       attempts=SIRA_DENEME, pause=SIRA_BEKLE)
    (out / "ilan" / f"{lid}_SONRA.json").write_text(json.dumps(sonra, ensure_ascii=False, indent=1, default=str))
    k4 = k4_of(sonra)
    r["adimlar"]["4_son_geri_oku"] = k4
    if not all(k4.values()):
        return r, "son geri okuma FAIL: " + ", ".join(k for k, v in k4.items() if not v)
    return r, ""


def apply(a, api, shop, out, kapak):
    plan = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))
    rows = plan["satirlar"]
    blok = [r for r in rows if r["durum"] == "BLOK"]
    if blok or len(rows) != BEKLENEN:
        raise SystemExit(f"HATA: plan {len(rows)} satir, BLOK {len(blok)}; yazma yok. DUR.")
    for r in rows:
        k = kapak.get(r["cift"])
        if not k or k["sha256"] != r["yeni_sha256"] or k["alt"] != r["yeni_alt"]:
            raise SystemExit(f"HATA: {r['cift']} kapak dosyasi/alt metni plandakiyle ayni degil; yazma yok. DUR.")
    haric = set(getattr(a, "haric", set()))
    is_ = [r for r in rows if r["durum"] == "PLAN" and str(r["listing_id"]) not in haric]
    if haric:
        log(f"HARIC (bu kosuda dokunulmaz): {', '.join(sorted(haric))}")
    (out / "yedek").mkdir(parents=True, exist_ok=True)
    (out / "ilan").mkdir(parents=True, exist_ok=True)
    drive_var = drive_liste(a.yedek_drive)
    log(f"yedek klasoru {a.yedek_drive}: {len(drive_var)} dosya | islenecek {len(is_)} ilan | kota {api.remaining}")
    sonuc, hata, kota_dur = [], "", False
    t0 = time.time()

    def tur(liste, ad):
        nonlocal hata, kota_dur
        for i, p in enumerate(liste, 1):
            if api.remaining is not None and int(api.remaining) < KOTA_TABAN:
                kota_dur = True
                log(f"KOTA {api.remaining} < {KOTA_TABAN}: yeni ilana baslanmadi ({ad}, {len(liste) - i + 1} ilan kaldi)")
                return
            if getattr(api, "store", None) is not None and api.store.needs_refresh():
                api.store.refresh()
            r, hata = ilan_uygula(a, api, shop, out, p, pathlib.Path(a.kapak_dir) / p["yeni_kapak"], drive_var)
            r["sonuc"] = "FAIL" if hata else ("ZATEN" if r.get("zaten") else ("YARIM" if r.get("yarim") else "PASS"))
            r["hata"], r["tur"] = hata, ad
            sonuc.append(r)
            (out / "SONUC.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
            gec = time.time() - t0
            log(f"[{ad} {i}/{len(liste)}] {p['listing_id']} {p['cift']} {r['sonuc']} | eski {r['eski_id']} -> yeni "
                f"{r['yeni_id']} | gecen {gec:.0f}s | kalan ~{gec / i * (len(liste) - i):.0f}s | %{i * 100 // len(liste)} | "
                f"kota {api.remaining}" + (f" | {hata}" if hata else ""))
            if hata:
                return

    tur(is_, "1. tur")
    yarim = [r for r in sonuc if r["sonuc"] == "YARIM"]
    if yarim and not hata and not kota_dur:
        # 2. tur: YARIM ilanlar kesin image_id'lerle (devam mantigi) tamamlanir
        for r in yarim:
            a.devam[str(r["listing_id"])], a.devam_eski[str(r["listing_id"])] = int(r["yeni_id"]), int(r["eski_id"])
        ids2 = {str(r["listing_id"]) for r in yarim}
        log(f"2. tur: {len(ids2)} YARIM ilan kesin id ile: " + ", ".join(f"{r['listing_id']}:{r['yeni_id']}:{r['eski_id']}"
                                                                         for r in yarim))
        tur([p for p in is_ if str(p["listing_id"]) in ids2], "2. tur")
    # ilan basina son durum (2. turda tamamlanan YARIM -> PASS)
    son = {}
    for r in sonuc:
        son[str(r["listing_id"])] = r
    sonuc_son = list(son.values())
    say = {d: sum(r["sonuc"] == d for r in sonuc_son) for d in ("PASS", "ZATEN", "YARIM", "FAIL")}
    bag = sum(1 for r in sonuc_son if r["sonuc"] == "PASS" and r.get("bag_tasi"))
    ok = not hata and not kota_dur and say["PASS"] + say["ZATEN"] == len(is_)
    sat = [f"# KAPAK78 yukle + eski kapak sil: APPLY ({simdi()})", "",
           f"- PASS {say['PASS']} (bag tasinan {bag}, 2. turda {sum(1 for r in sonuc_son if r['tur'] == '2. tur' and r['sonuc'] == 'PASS')}) | "
           f"ZATEN {say['ZATEN']} | YARIM {say['YARIM']} | FAIL {say['FAIL']} | islenmeyen {len(is_) - len(sonuc_son)} | "
           f"toplam {len(is_)} | kota {api.remaining}" + (f" | KOTA < {KOTA_TABAN} DURDU" if kota_dur else ""),
           f"- Yedek: {a.yedek_drive}/<listing_id>_<image_id>.jpg ({sum(1 for r in sonuc if r.get('yedek'))} dosya)",
           f"- SONUC: {'PASS' if ok else 'FAIL - DURDU: ' + (sonuc[-1]['listing_id'] + ' ' + hata if hata else 'eksik (YARIM/kota)')}",
           f"- HARIC (dokunulmadi): {', '.join(sorted(haric)) or '-'}",
           f"- YARIM (yeni kapak var, eski kapak + bag yerinde): "
           f"{', '.join(str(r['listing_id']) + ':' + str(r['yeni_id']) + ':' + str(r['eski_id']) for r in sonuc_son if r['sonuc'] == 'YARIM') or '-'}", "",
           "| listing_id | cift | eski | yeni kapak | tasinan bag | tur | sonuc |", "|---|---|---|---|---|---|---|"]
    sat += [f"| {r['listing_id']} | {r['cift']} | {r['eski_id']} | {r['yeni_id']} | "
            f"{', '.join(str(b['value']) for b in r.get('bag_tasi') or []) or '-'} | {r['tur']} | {r['sonuc']} |"
            for r in sonuc_son]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat[2:6]:
        log(x)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--kapak-dir", required=True)
    ap.add_argument("--kaynak-bilgi", help="JSON: klasor, ozet, cancer_libra (rclone lsjson satiri)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--yedek-drive")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-min", type=int, default=150)
    ap.add_argument("--devam", default="",
                    help="LISTING_ID:YENI_IMAGE_ID:ESKI_IMAGE_ID[,..] yarim kalmis ilan, kesin id ile")
    ap.add_argument("--haric", default="", help="LISTING_ID[,..] bu kosuda dokunulmayacak ilanlar")
    ap.add_argument("--yenile", default="", help="CIFT[,..] kuru: 1. sirada ayni alt+boyutta kapak olsa da PLAN (duzeltilmis kapak)")
    a = ap.parse_args()
    a.yenile = {t.strip().upper() for t in a.yenile.split(",") if t.strip()}
    a.haric = {t.strip() for t in a.haric.split(",") if t.strip()}
    devam_str, a.devam, a.devam_eski = a.devam, {}, {}
    for t in [t.strip() for t in devam_str.split(",") if t.strip()]:
        lid, yeni, eski = t.split(":")
        a.devam[lid], a.devam_eski[lid] = int(yeni), int(eski)
    if a.apply and (a.confirm != ONAY or not a.plan or not a.yedek_drive):
        raise SystemExit(f"HATA: --apply icin --confirm {ONAY} + --plan + --yedek-drive gerekli. DUR.")
    a.kaynak = json.loads(pathlib.Path(a.kaynak_bilgi).read_text()) if a.kaynak_bilgi else {}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    satirlar, kapak, sorun, fazla = kapaklar_oku(a.ids, a.kapak_dir)
    log(f"ilan {len(satirlar)} | kapak {len(kapak)} | eslesmeyen {len(sorun)} | ilanda olmayan kapak {len(fazla)}")
    if len(satirlar) != BEKLENEN:
        raise SystemExit(f"HATA: ilan listesi {len(satirlar)} != {BEKLENEN}. DUR.")

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    if a.apply:
        ok = apply(a, api, shop, out, kapak)
    else:
        ok = kuru(a, api, shop, out, satirlar, kapak, sorun, fazla)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
