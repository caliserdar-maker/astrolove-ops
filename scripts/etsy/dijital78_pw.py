#!/usr/bin/env python3
"""
DIJITAL 78 v2 - ADIM 4: PURE WHITE SURUM FARKI (Etsy salt okur).

77 PW ZIP'i Drive'da canli ilandakinden ~%3 buyuk. Bu adim:
  1) 78 PW ilaninin canli dosya metaverisini okur (getListingFiles; bu adimda
     ilan bazinda okuma Serdar tarafindan acikca izinli, ~78 cagri).
  2) Drive'daki guncel ZIP boyutu/tarihi ile karsilastirir.
  3) Drive'in TAMAMINDA ayni adli baska PW ZIP kopyasi arar; boyutu canliyla
     BIREBIR eslesen bir surum var mi bakar.
  4) Eslesen surum bulunursa iki surumun JPG'lerini piksel bazinda karsilastirir
     (once 1 cift, sonra --ornek-cift kadar cift ile dogrular).
  5) START_HERE metnini tarayip PW yeniden uretimine dair kayit arar.

Oneri yazilir, KARAR VERILMEZ. Etsy'ye yazma yoktur.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

EDISYON = "Pure White"
SUTUN = ["listing_id", "cift", "canli_ad", "canli_bayt", "canli_yuklenme", "canli_dosya_sayisi",
         "drive_ad", "drive_bayt", "drive_degisiklik", "fark_bayt", "fark_yuzde", "eslesme",
         "alternatif_surum", "alternatif_bayt", "alternatif_eslesiyor", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ts(v):
    try:
        return datetime.fromtimestamp(int(v), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return ""


def kos(cmd, timeout=900):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def piksel_hash(path):
    p = subprocess.Popen(["djpeg", "-pnm", str(path)], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    h = hashlib.sha256()
    try:
        for parca in iter(lambda: p.stdout.read(1 << 20), b""):
            h.update(parca)
    finally:
        p.stdout.close()
        p.wait(timeout=900)
    return h.hexdigest() if p.returncode == 0 else f"HATA{p.returncode}"


def jpg_bilgi(path):
    """Boyut, nicemleme tablosu imzasi, ICC varligi."""
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(path) as im:
            q = getattr(im, "quantization", {}) or {}
            imza = hashlib.sha1(json.dumps({k: list(v) for k, v in sorted(q.items())},
                                           sort_keys=True).encode()).hexdigest()[:10]
            return {"boyut": f"{im.size[0]}x{im.size[1]}", "q_imza": imza,
                    "icc": "VAR" if im.info.get("icc_profile") else "YOK",
                    "prog": "EVET" if im.info.get("progression") else "HAYIR"}
    except Exception as ex:                                   # noqa: BLE001
        return {"boyut": "?", "q_imza": f"HATA:{str(ex)[:30]}", "icc": "?", "prog": "?"}


def zip_ac(yol, hedef):
    hedef.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(yol) as z:
        z.extractall(hedef)
    return sorted(p for p in hedef.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg"))


def surum_karsilastir(a_yol, b_yol, calisma, etiket_a, etiket_b):
    """Iki ZIP'in JPG'lerini piksel + metaveri duzeyinde karsilastirir."""
    da, db = calisma / "A", calisma / "B"
    shutil.rmtree(da, ignore_errors=True); shutil.rmtree(db, ignore_errors=True)
    ja, jb = zip_ac(a_yol, da), zip_ac(b_yol, db)
    ad_a = {p.name: p for p in ja}
    ad_b = {p.name: p for p in jb}
    satirlar = []
    for ad in sorted(set(ad_a) | set(ad_b)):
        pa, pb = ad_a.get(ad), ad_b.get(ad)
        if not pa or not pb:
            satirlar.append({"dosya": ad, "durum": "YALNIZ " + (etiket_a if pa else etiket_b)})
            continue
        ha, hb = piksel_hash(pa), piksel_hash(pb)
        ia, ib = jpg_bilgi(pa), jpg_bilgi(pb)
        satirlar.append({
            "dosya": ad, "durum": "PIKSEL AYNI" if ha == hb else "PIKSEL FARKLI",
            f"{etiket_a}_bayt": pa.stat().st_size, f"{etiket_b}_bayt": pb.stat().st_size,
            f"{etiket_a}_boyut": ia["boyut"], f"{etiket_b}_boyut": ib["boyut"],
            f"{etiket_a}_q": ia["q_imza"], f"{etiket_b}_q": ib["q_imza"],
            f"{etiket_a}_icc": ia["icc"], f"{etiket_b}_icc": ib["icc"],
            f"{etiket_a}_prog": ia["prog"], f"{etiket_b}_prog": ib["prog"],
        })
    shutil.rmtree(da, ignore_errors=True); shutil.rmtree(db, ignore_errors=True)
    return satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envanter", required=True)
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--kok", required=True, help="guncel ZIP klasoru (ALL_312_ZIPS) folder id")
    ap.add_argument("--ara-kok", default="gdrive:ASTROLOVE", help="alternatif surum aramasi kok yolu")
    ap.add_argument("--start-here", default="", help="START_HERE duz metin dosyasi (varsa)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--calisma", default="_work/pw")
    ap.add_argument("--ornek-cift", type=int, default=5)
    ap.add_argument("--max-calls", type=int, default=85)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    calisma = Path(a.calisma); calisma.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    pw = []
    with open(a.envanter, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("edisyon") == EDISYON:
                pw.append({"listing_id": r["listing_id"], "cift": r["cift"]})
    pw.sort(key=lambda x: x["cift"])
    print(f"1) Pure White ilani: {len(pw)}", flush=True)

    # --------------------------------------------------------------- Drive guncel
    r = kos(["rclone", "lsjson", f"--drive-root-folder-id={a.kok}", f"{a.remote}:", "--files-only"])
    if r.returncode != 0:
        raise SystemExit(f"HATA: lsjson {r.stderr.decode('utf-8','replace')[:200]}")
    guncel = {d["Name"]: d for d in json.loads(r.stdout) if "_Pure_White_" in d["Name"]}
    print(f"2) Drive guncel PW ZIP: {len(guncel)}", flush=True)

    # --------------------------------------------------------------- alternatif surumler
    print("3) Drive genelinde alternatif PW ZIP aramasi", flush=True)
    r = kos(["rclone", "lsjson", a.ara_kok, "-R", "--files-only", "--fast-list",
             "--include", "*Pure_White*ALL_SIZES.zip"], timeout=1800)
    alt = {}
    if r.returncode == 0:
        for d in json.loads(r.stdout):
            alt.setdefault(Path(d["Path"]).name, []).append(
                {"yol": d["Path"], "bayt": int(d["Size"]), "mtime": (d.get("ModTime") or "")[:19]})
    else:
        print(f"   UYARI: alternatif arama basarisiz: {r.stderr.decode('utf-8','replace')[:160]}",
              flush=True)
    kopya_sayisi = Counter(len(v) for v in alt.values())
    print(f"   {len(alt)} ad, kopya dagilimi {dict(kopya_sayisi)}", flush=True)

    # --------------------------------------------------------------- Etsy canli metaveri
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]; mask(shop)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    print(f"4) Canli dosya metaverisi ({len(pw)} ilan, tavan {a.max_calls} cagri)", flush=True)

    satirlar, son = [], time.time()
    for i, p in enumerate(pw, 1):
        if api.calls >= a.max_calls:
            print(f"   BUTCE: {i-1}/{len(pw)} okundu, durduruldu", flush=True)
            break
        fr = api.get(f"/shops/{shop}/listings/{p['listing_id']}/files", ok404=True) or {}
        dosyalar = fr.get("results") or []
        zipler = [f for f in dosyalar if (f.get("filename") or "").lower().endswith(".zip")]
        c_ad = zipler[0].get("filename") if zipler else ""
        c_bayt = zipler[0].get("size_bytes") if zipler else None
        c_ts = ts(zipler[0].get("create_timestamp")) if zipler else ""
        g = guncel.get(c_ad)
        d_bayt = int(g["Size"]) if g else None
        fark = (d_bayt - c_bayt) if (g and c_bayt) else None
        alt_liste = [x for x in alt.get(c_ad, []) if x["bayt"] != d_bayt]
        alt_eslesen = [x for x in alt_liste if c_bayt and x["bayt"] == c_bayt]
        satirlar.append({
            "listing_id": p["listing_id"], "cift": p["cift"], "canli_ad": c_ad,
            "canli_bayt": c_bayt, "canli_yuklenme": c_ts, "canli_dosya_sayisi": len(dosyalar),
            "drive_ad": c_ad if g else "", "drive_bayt": d_bayt,
            "drive_degisiklik": (g.get("ModTime") or "")[:19] if g else "",
            "fark_bayt": fark, "fark_yuzde": (round(100.0 * fark / c_bayt, 2)
                                              if fark is not None and c_bayt else ""),
            "eslesme": ("AYNI" if fark == 0 else "FARKLI") if fark is not None else "OKUNAMADI",
            "alternatif_surum": len(alt_liste),
            "alternatif_bayt": ";".join(str(x["bayt"]) for x in alt_liste[:3]),
            "alternatif_eslesiyor": (alt_eslesen[0]["yol"] if alt_eslesen else ""),
            "not": "" if zipler else "canli ilanda ZIP bulunamadi",
        })
        if time.time() - son >= 60 or i == len(pw):
            print(f"   ETA {i}/{len(pw)} | cagri {api.calls} | gecen {time.time()-t0:.0f}s", flush=True)
            son = time.time()

    with open(out / "PW_SURUM.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for r2 in satirlar:
            w.writerow(r2)

    ayni = [r2 for r2 in satirlar if r2["eslesme"] == "AYNI"]
    farkli = [r2 for r2 in satirlar if r2["eslesme"] == "FARKLI"]
    esleyen_alt = [r2 for r2 in satirlar if r2["alternatif_eslesiyor"]]

    # --------------------------------------------------------------- piksel karsilastirmasi
    kars, kars_not = [], ""
    hedefler = esleyen_alt[:max(1, a.ornek_cift)]
    if hedefler:
        print(f"5) Piksel karsilastirmasi ({len(hedefler)} cift)", flush=True)
        for r2 in hedefler:
            ga = calisma / f"guncel_{r2['canli_ad']}"
            gb = calisma / f"canli_{r2['canli_ad']}"
            kos(["rclone", "copyto", f"--drive-root-folder-id={a.kok}",
                 f"{a.remote}:{r2['canli_ad']}", str(ga)])
            kos(["rclone", "copyto", f"{a.remote}:{r2['alternatif_eslesiyor']}", str(gb)])
            if ga.exists() and gb.exists():
                for x in surum_karsilastir(ga, gb, calisma, "drive", "canli"):
                    x["cift"] = r2["cift"]
                    kars.append(x)
            ga.unlink(missing_ok=True); gb.unlink(missing_ok=True)
    else:
        kars_not = ("Drive'da canli dosyayla BIREBIR ayni baytta baska bir PW surumu bulunamadi. "
                    "Etsy API dijital dosyanin indirme baglantisini vermedigi icin canli dosyanin "
                    "ICERIGI ile piksel karsilastirmasi YAPILAMADI; karsilastirma yalniz ad, bayt "
                    "ve yuklenme zamani duzeyinde.")
        print(f"5) {kars_not}", flush=True)

    if kars:
        with open(out / "PW_PIKSEL.csv", "w", newline="", encoding="utf-8") as fh:
            alanlar = sorted({k2 for x in kars for k2 in x})
            w = csv.DictWriter(fh, fieldnames=alanlar, extrasaction="ignore")
            w.writeheader()
            for x in kars:
                w.writerow(x)

    # --------------------------------------------------------------- START_HERE taramasi
    sh_bulgu = []
    if a.start_here and Path(a.start_here).exists():
        metin = Path(a.start_here).read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"[^\n]*(Pure White|PURE WHITE|Pure_White)[^\n]*", metin):
            sat = m.group(0).strip()
            if re.search(r"zip|yeniden|uret|regen|15 A[gğ]|16 A[gğ]|agustos|ağustos|boyut|surum|sürüm",
                         sat, re.I):
                sh_bulgu.append(sat[:200])
        sh_bulgu = sh_bulgu[:25]

    # --------------------------------------------------------------- rapor
    d_tarih = Counter(r2["drive_degisiklik"][:10] for r2 in satirlar if r2["drive_degisiklik"])
    c_tarih = Counter(r2["canli_yuklenme"][:10] for r2 in satirlar if r2["canli_yuklenme"])
    ort_fark = [r2["fark_yuzde"] for r2 in farkli if isinstance(r2["fark_yuzde"], float)]
    md = [f"# PURE WHITE SURUM FARKI ({simdi()} UTC)", "",
          f"Etsy cagrisi: {api.calls} (salt okur, yalniz `getListingFiles`). Yazma yok.", "",
          "## Sayimlar", "",
          f"- Incelenen PW ilani: {len(satirlar)} / {len(pw)}",
          f"- Drive ile canli BIREBIR AYNI: **{len(ayni)}**",
          f"- FARKLI: **{len(farkli)}**",
          f"- Drive'da canliyla ayni baytta alternatif surum bulunan ilan: {len(esleyen_alt)}",
          f"- Fark yuzdesi (Drive - canli): min {min(ort_fark):.2f}%, ort "
          f"{sum(ort_fark)/max(1,len(ort_fark)):.2f}%, maks {max(ort_fark):.2f}%"
          if ort_fark else "- Fark yuzdesi olculemedi", "",
          "## Tarihler (hangisi yeni)", "",
          f"- Canli dosyalarin Etsy'ye yuklenme tarihi: {dict(c_tarih)}",
          f"- Drive dosyalarinin son degisiklik tarihi: {dict(d_tarih)}", ""]
    if c_tarih and d_tarih:
        en_canli, en_drive = max(c_tarih), max(d_tarih)
        md.append(f"- **Drive surumu {'YENI' if en_drive > en_canli else 'ESKI'}**: "
                  f"Drive son degisiklik {en_drive}, Etsy'ye yuklenme {en_canli}.")
        if en_drive > en_canli:
            md.append("  Yani PW ZIP'leri Etsy'ye yuklendikten SONRA Drive'da yeniden uretilmis; "
                      "yeni surum canli ilanlara hic yuklenmemis.")
    md += ["", "## Alternatif surum aramasi", "",
           f"- Drive `{a.ara_kok}` altinda `*Pure_White*ALL_SIZES.zip` adiyla bulunan farkli ad: {len(alt)}",
           f"- Ad basina kopya sayisi dagilimi: {dict(kopya_sayisi)}",
           f"- Canli baytla BIREBIR eslesen kopya bulunan ilan: {len(esleyen_alt)}", ""]
    if kars:
        ayni_px = sum(1 for x in kars if x["durum"] == "PIKSEL AYNI")
        md += ["## Piksel karsilastirmasi (iki Drive surumu)", "",
               f"- Karsilastirilan JPG: {len(kars)} | PIKSEL AYNI: {ayni_px} | "
               f"FARKLI: {len(kars) - ayni_px}", "",
               "| cift | dosya | durum | drive bayt | canli bayt | drive q | canli q | "
               "drive ICC | canli ICC | drive prog | canli prog |", "|---|---|---|---:|---:|---|---|---|---|---|---|"]
        for x in kars[:40]:
            md.append(f"| {x.get('cift','')} | {x['dosya']} | {x['durum']} | "
                      f"{x.get('drive_bayt','')} | {x.get('canli_bayt','')} | "
                      f"{x.get('drive_q','')} | {x.get('canli_q','')} | "
                      f"{x.get('drive_icc','')} | {x.get('canli_icc','')} | "
                      f"{x.get('drive_prog','')} | {x.get('canli_prog','')} |")
    else:
        md += ["## Piksel karsilastirmasi", "", kars_not]
    md += ["", "## START_HERE kaydi", ""]
    md += ([f"- {x}" for x in sh_bulgu] if sh_bulgu else
           ["- START_HERE metninde PW ZIP yeniden uretimine dair bir kayit BULUNAMADI.",
            "- Repo icindeki B94-B99 oturum gunluklerinde de boyle bir kayit yok "
            "(yalniz PW **RU cevirisi** isi gecer, ZIP yeniden uretimi degil)."])
    md += ["", "## ONERI (karar Serdar'in)", "",
           "1. Canli 78 PW ilanindaki dosya, Drive'daki guncel surumden farkliysa alici SU AN",
           "   eski surumu indiriyor. Birlestirmede 5 ZIP yeniden yuklenecegi icin bu fark",
           "   kendiliginden kapanir: yukleme Drive'daki GUNCEL surumle yapilirsa tum",
           "   edisyonlar ayni uretim turundan gelir.",
           "2. Yuklemeden once tek bir PW ZIP'i gozle dogrulanmali (or. Aries+Leo): Drive",
           "   surumunun gorsel olarak bozulmadigi, oranlarin ve piksellerin v1'de olculen",
           "   degerlerde oldugu ZIP_KONTROL.csv ile zaten dogrulandi.",
           ("3. OLCULDU: iki surumun JPG'leri piksel duzeyinde karsilastirildi; sonuclar "
            "yukaridaki tabloda. Nicemleme tablosu (q imzasi) farkliysa iki surum farkli "
            "kalite ayariyla uretilmistir." if kars else
            "3. Fark yalniz PW'de oldugu icin, PW uretim adiminin digerlerinden farkli bir "
            "ayarla (or. farkli kalite/optimize bayragi) kosulmus olmasi en olasi aciklamadir; "
            "piksel karsilastirmasi yapilamadigi surece bu KANITLANMAMIS bir varsayimdir."),
           "4. Karar gerekiyor: (A) Drive guncel surumu yuklensin, (B) once bir ilanda",
           "   deneme yapilsin, (C) PW yeniden uretilsin. Bu betik karar vermez."]
    (out / "PW_SURUM.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BITTI | ayni {len(ayni)} | farkli {len(farkli)} | cagri {api.calls} | "
          f"kota {api.remaining} | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
