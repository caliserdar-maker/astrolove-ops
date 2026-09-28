#!/usr/bin/env python3
"""78 POD ilaninda kapak degisimi: v9 kapagi 1. siraya yukle, eski 1. sira kapagi yedekleyip sil
(Serdar acik onayi 28 Eyl: eski kapaklar silinecek; "Silme YOK" yalniz bu adim icin kalkar).
Kapak kaynagi TEK: Drive TEMP/POD_KAPAK_78/<en son damga>/KAPAK_<CIFT>.jpg (3000x2250, OZET 78/78 PASS).
updateListing CAGRILMAZ.

KURU (varsayilan, Etsy'ye yazma yok):
  1. on kontrol: 78 ilan state, gorsel sayisi, rank 1 image_id; eslesmeyen cift, 20 gorseli dolu,
     active disi, varyasyona bagli eski kapak -> BLOK
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
  3. yalniz 2. adim PASS ise plandaki eski image_id deleteListingImage ile silinir (baska gorsel silinmez)
  4. geri okuma: sayi = onceki, 1. sira = yeni, eski id yok, kalanlar ayni sira, varyasyon baglari,
     videolar, state active
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
CAGRI_ILAN = 12  # apply'da ilan basina tahmini Etsy cagrisi (okuma + yukleme + silme + geri okuma)
OKUMA_BEKLE = 3


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
        vmap = variation_map(variation_images(api, shop, lid))
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
        elif k and (r1.get("alt_text") == k["alt"]
                    and (r1.get("full_width"), r1.get("full_height")) == (k["w"], k["h"])):
            row["durum"] = "ZATEN"
        else:
            if int(r1.get("rank") or 0) != 1:
                neden.append(f"ilk gorsel rank {r1.get('rank')}")
            if any(str(eski_id) == str(v[3]) for v in vmap):
                neden.append(f"{eski_id} varyasyon gorseline bagli")
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
    return ok


# ------------------------------------------------------------------ apply
def ilan_uygula(a, api, shop, out, p, kapak_yol, drive_var):
    """Tek ilan. Donus: (sonuc_dict, hata_metni). hata_metni bos degilse DUR."""
    lid, eski = p["listing_id"], int(p["eski_rank1_id"])
    r = {"listing_id": lid, "cift": p["cift"], "eski_id": eski, "yeni_id": None, "adimlar": {}}

    # 0. canli durum = plan
    once = durum(api, shop, lid)
    oids = ids_of(once["galeri"])
    (out / "ilan" / f"{lid}_ONCE.json").write_text(json.dumps(once, ensure_ascii=False, indent=1, default=str))
    k0 = {"state active": once["state"] == "active",
          f"1. sira = plandaki {eski}": bool(oids) and oids[0] == eski,
          "galeri id sirasi plandaki ile ayni": oids == [int(x) for x in p["galeri_ids"]],
          "eski id varyasyona bagli degil": not any(str(eski) == str(v[3]) for v in once["varyasyon"]),
          f"galeri {len(oids)} + 1 <= {ETSY_MAX}": len(oids) + 1 <= ETSY_MAX}
    r["adimlar"]["0_on_kontrol"] = k0
    if not all(k0.values()):
        return r, "on kontrol FAIL: " + ", ".join(k for k, v in k0.items() if not v)

    # 1. eski kapagin DOSYASI Drive yedeginde mi; yoksa indir + yaz + geri oku
    ad = f"{lid}_{eski}.jpg"
    if p.get("eski_dosya_bayt") and drive_var.get(ad) == p["eski_dosya_bayt"]:
        r["yedek"] = f"{a.yedek_drive}/{ad}"
        r["adimlar"]["1_yedek"] = {f"yedek Drive'da ({drive_var[ad]} bayt = kuru kosu)": True}
    else:
        r1 = once["galeri"][0]
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

    # 2. yeni kapak rank 1 + geri okuma
    if api.remaining is not None and int(api.remaining) < a.quota_min:
        return r, f"kota {api.remaining} < {a.quota_min}"
    with open(kapak_yol, "rb") as fh:
        up = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                           files={"image": (kapak_yol.name, fh, "image/jpeg")},
                           data={"rank": "1", "alt_text": p["yeni_alt"]})
    yeni = int(up.get("listing_image_id") or 0)
    r["yeni_id"] = yeni
    if not yeni:
        return r, "yukleme: yeni listing_image_id donmedi"
    g = eventually(lambda: gallery(api, lid), lambda rows: yeni in ids_of(rows), attempts=10, pause=OKUMA_BEKLE)
    if ids_of(g)[:1] != [yeni]:
        log(f"  {lid}: yeni gorsel 1. sirada degil; sira tek cagriyla 1'e aliniyor")
        api.post_file(f"/shops/{shop}/listings/{lid}/images",
                      files={"listing_image_id": (None, str(yeni)), "rank": (None, "1")})
        g = eventually(lambda: gallery(api, lid), lambda rows: ids_of(rows)[:1] == [yeni],
                       attempts=10, pause=OKUMA_BEKLE)
    gi = ids_of(g)
    k2 = {"1. sira yeni kapak": gi[:1] == [yeni],
          "yeni kapak alt metni": bool(g) and g[0].get("alt_text") == p["yeni_alt"],
          f"gorsel sayisi {len(oids)} + 1": len(gi) == len(oids) + 1,
          "eski gorseller ayni id + sira (2..n+1)": gi[1:] == oids}
    r["adimlar"]["2_yukle_geri_oku"] = k2
    (out / "ilan" / f"{lid}_YUKLEME_SONRASI.json").write_text(json.dumps(g, ensure_ascii=False, indent=1, default=str))
    if not all(k2.values()):
        return r, "yukleme geri okuma FAIL (eski kapak SILINMEDI): " + ", ".join(k for k, v in k2.items() if not v)

    # 3. yalniz plandaki eski image_id silinir
    api.delete(f"/shops/{shop}/listings/{lid}/images/{eski}")

    # 4. geri okuma
    beklenen = [yeni] + oids[1:]

    def k4_of(st):
        s = ids_of(st["galeri"])
        return {f"gorsel sayisi = onceki ({len(oids)})": len(s) == len(oids),
                "1. sira = yeni kapak": s[:1] == [yeni],
                f"{eski} silindi": eski not in s,
                "kalan gorseller ayni id + sira": s == beklenen,
                "varyasyon gorsel baglari ayni": st["varyasyon"] == once["varyasyon"],
                "videolar ayni": st["video"] == once["video"],
                "ilan active": st["state"] == "active"}

    sonra = eventually(lambda: durum(api, shop, lid), lambda st: all(k4_of(st).values()),
                       attempts=10, pause=OKUMA_BEKLE * 2)
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
    is_ = [r for r in rows if r["durum"] == "PLAN"]
    (out / "yedek").mkdir(parents=True, exist_ok=True)
    (out / "ilan").mkdir(parents=True, exist_ok=True)
    drive_var = drive_liste(a.yedek_drive)
    log(f"yedek klasoru {a.yedek_drive}: {len(drive_var)} dosya | islenecek {len(is_)} ilan | kota {api.remaining}")
    sonuc, hata = [], ""
    t0 = time.time()
    for i, p in enumerate(is_, 1):
        if getattr(api, "store", None) is not None and api.store.needs_refresh():
            api.store.refresh()
        r, hata = ilan_uygula(a, api, shop, out, p, pathlib.Path(a.kapak_dir) / p["yeni_kapak"], drive_var)
        r["sonuc"] = "FAIL" if hata else "PASS"
        r["hata"] = hata
        sonuc.append(r)
        (out / "SONUC.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
        gec = time.time() - t0
        log(f"[{i}/{len(is_)}] {p['listing_id']} {p['cift']} {r['sonuc']} | eski {r['eski_id']} -> yeni {r['yeni_id']} | "
            f"gecen {gec:.0f}s | kalan ~{gec / i * (len(is_) - i):.0f}s | %{i * 100 // len(is_)} | kota {api.remaining}"
            + (f" | {hata}" if hata else ""))
        if hata:
            break
    pas = sum(r["sonuc"] == "PASS" for r in sonuc)
    ok = not hata and pas == len(is_)
    sat = [f"# KAPAK78 yukle + eski kapak sil: APPLY ({simdi()})", "",
           f"- PASS {pas} / {len(is_)} (ZATEN atlanan {len(rows) - len(is_)}) | kota {api.remaining}",
           f"- Yedek: {a.yedek_drive}/<listing_id>_<image_id>.jpg ({sum(1 for r in sonuc if r.get('yedek'))} dosya)",
           f"- SONUC: {'PASS' if ok else 'FAIL - DURDU: ' + (sonuc[-1]['listing_id'] + ' ' + hata if hata else 'eksik')}", "",
           "| listing_id | cift | silinen eski | yeni kapak | sonuc |", "|---|---|---|---|---|"]
    sat += [f"| {r['listing_id']} | {r['cift']} | {r['eski_id']} | {r['yeni_id']} | {r['sonuc']} |" for r in sonuc]
    (out / "report.md").write_text("\n".join(sat) + "\n", encoding="utf-8")
    for x in sat[2:5]:
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
    ap.add_argument("--quota-min", type=int, default=60)
    a = ap.parse_args()
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
