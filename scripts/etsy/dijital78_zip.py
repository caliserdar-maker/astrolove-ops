#!/usr/bin/env python3
"""
DIJITAL 78 - ADIM 3: ZIP KONTROLU (Drive, Etsy cagrisi YOK).

Yontem:
  1) rclone lsjson ile klasordeki tum ZIP'lerin ad / bayt / degisiklik tarihi.
  2) Her ZIP'in ICERIGI, dosyanin tamami indirilmeden okunur: son 64 KB cekilir,
     EOCD (0x06054b50) bulunur, merkezi dizin ayristirilir. Merkezi dizin
     kuyrugun disindaysa ikinci bir aralik istegi yapilir.
  3) Canli Etsy anlik goruntusu (DIGITAL_FILES_ALL.csv) ile ad + bayt
     karsilastirmasi: ayni surum mu.
  4) Tesekkur PDF'i eklendiginde olusacak boyut ve 19.8 MB guvenlik esigi.
  5) Dosya adi <= 70 karakter kontrolu; asanlara kisa ad onerisi.
  6) --tam-ornek ile secilen ciftlerin 5 edisyonu TAM indirilip JPG pikselleri
     olculur (yapi ayniligi kaniti).

YENI ZIP URETILMEZ. Drive'a yazma yoktur.
"""
import argparse
import concurrent.futures as cf
import csv
import io
import json
import os
import re
import struct
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PDF_BAYT = 160153            # ASTROLOVE_DIGITAL_THANKYOU_EN.pdf (Drive 1YtpIdNZ...)
SINIR_MB = 20.0              # Etsy dijital dosya siniri
GUVENLI_BAYT = 19_800_000    # Serdar'in guvenlik payi: 19.8 MB
AD_SINIR = 70
KUYRUK = 65536

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
EDISYONLAR = ["Champagne_Ivory", "Pure_White", "Warm_Parchment", "Midnight_Blue", "Deep_Black"]
ED_KISA = {"Champagne_Ivory": "CI", "Pure_White": "PW", "Warm_Parchment": "WP",
           "Midnight_Blue": "MB", "Deep_Black": "DB"}
BURC_KISA = {b: b[:3].upper() for b in BURCLAR}
ORANLAR = {"2:3": 2 / 3, "3:4": 3 / 4, "4:5": 4 / 5, "11:14": 11 / 14, "A": 1 / (2 ** 0.5)}

SUTUN = ["zip_adi", "cift", "edisyon", "ad_karakter", "ad_70_asiyor", "ad_onerisi",
         "drive_bayt", "drive_mb", "drive_tarih", "pdf_ekli_bayt", "pdf_ekli_mb",
         "sinir_19_8mb", "etsy_bayt", "etsy_ad", "surum_ayni", "ic_dosya_sayisi",
         "ic_dosyalar", "oranlar", "pdf_icinde", "yapi_imzasi", "olculen_pikseller", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rclone(args, ikili=False):
    r = subprocess.run(["rclone"] + args, capture_output=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {' '.join(args[:3])} -> {r.returncode}: "
                           f"{r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout if ikili else r.stdout.decode("utf-8", "replace")


def parca(remote, kok, ad, offset, count):
    """Dosyanin bir araligini indirir (negatif offset = sondan)."""
    return rclone(["cat", f"--drive-root-folder-id={kok}", f"{remote}:{ad}",
                   "--offset", str(offset)] + (["--count", str(count)] if count else []),
                  ikili=True)


# ------------------------------------------------------------ merkezi dizin
def eocd_bul(buf):
    """Kuyruk icinde EOCD imzasini sondan arar -> (cd_offset, cd_bayt, girdi)."""
    imza = b"PK\x05\x06"
    i = buf.rfind(imza)
    if i < 0 or len(buf) - i < 22:
        return None
    girdi, cd_bayt, cd_off = struct.unpack("<HII", buf[i + 10:i + 20])
    return cd_off, cd_bayt, girdi


def cd_ayristir(cd, girdi):
    """Merkezi dizin kayitlari -> [(ad, sikistirilmamis_bayt, sikistirilmis_bayt)]"""
    out, p = [], 0
    for _ in range(girdi):
        if p + 46 > len(cd) or cd[p:p + 4] != b"PK\x01\x02":
            break
        csize, usize = struct.unpack("<II", cd[p + 20:p + 28])
        n, m, k = struct.unpack("<HHH", cd[p + 28:p + 34])
        ad = cd[p + 46:p + 46 + n].decode("utf-8", "replace")
        out.append((ad, usize, csize))
        p += 46 + n + m + k
    return out


def zip_icerik(remote, kok, ad, boyut):
    kuyruk = parca(remote, kok, ad, -min(KUYRUK, boyut), None)
    e = eocd_bul(kuyruk)
    if not e:
        raise RuntimeError("EOCD bulunamadi")
    cd_off, cd_bayt, girdi = e
    kuyruk_bas = boyut - len(kuyruk)
    if cd_off >= kuyruk_bas and cd_off - kuyruk_bas + cd_bayt <= len(kuyruk):
        cd = kuyruk[cd_off - kuyruk_bas: cd_off - kuyruk_bas + cd_bayt]
    else:
        cd = parca(remote, kok, ad, cd_off, cd_bayt)
    return cd_ayristir(cd, girdi)


# ------------------------------------------------------------ ad / oran
def ad_coz(zad):
    m = re.match(r"AstroLove_([A-Za-z]+)_([A-Za-z]+)_(" + "|".join(EDISYONLAR) + r")_ALL_SIZES\.zip$",
                 zad)
    if not m:
        return "", "", ""
    a, b, e = m.group(1), m.group(2), m.group(3)
    if a.capitalize() not in BURCLAR or b.capitalize() not in BURCLAR:
        return "", "", ""
    return "_".join(sorted([a.upper(), b.upper()])), e.replace("_", " "), e


def ad_onerisi(zad, cift, ed_raw):
    if not cift:
        return ""
    a, b = cift.split("_")
    return (f"AstroLove_{BURC_KISA.get(a.capitalize(), a[:3])}_"
            f"{BURC_KISA.get(b.capitalize(), b[:3])}_{ED_KISA.get(ed_raw, ed_raw)}_5SIZES.zip")


def oran_adi(ad):
    """Dosya adindan oran cikarimi (or. ..._2x3.jpg, ..._11x14.jpg, ..._A.jpg)."""
    m = re.search(r"(\d{1,2})[xX_](\d{1,2})", ad)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    if re.search(r"\bA[-_ ]?series\b|_A\.jpg$|_A4|ISO", ad, re.I):
        return "A"
    return "?"


def oran_pikselden(w, h):
    r = (w / h) if w <= h else (h / w)
    en, fark = "?", 9.0
    for ad, d in ORANLAR.items():
        f = abs(r - d) / d
        if f < fark:
            en, fark = ad, f
    return en if fark < 0.01 else f"?({r:.4f})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--kok", required=True, help="ZIP klasorunun Drive folder id'si")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dfiles", default="", help="DIGITAL_FILES_ALL.csv (canli Etsy anlik goruntusu)")
    ap.add_argument("--envanter", default="", help="ENVANTER.csv (cift/edisyon dogrulamasi)")
    ap.add_argument("--is-parca", type=int, default=8)
    ap.add_argument("--tam-ornek", default="ARIES_LEO,CANCER_SCORPIO,GEMINI_GEMINI",
                    help="Tam indirilip piksel olculecek ciftler")
    ap.add_argument("--tam-ornek-dizin", default="", help="Indirilen ornek ZIP'lerin birakilacagi dizin")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"1) rclone lsjson (kok {a.kok})", flush=True)
    dosyalar = json.loads(rclone(["lsjson", f"--drive-root-folder-id={a.kok}", f"{a.remote}:",
                                  "--files-only"]))
    zipler = sorted([d for d in dosyalar if d["Name"].lower().endswith(".zip")],
                    key=lambda d: d["Name"])
    print(f"   {len(dosyalar)} dosya, {len(zipler)} ZIP", flush=True)

    # canli Etsy anlik goruntusu: zip adi -> bayt
    etsy_ad_bayt, etsy_kaynak = {}, "yok"
    if a.dfiles and Path(a.dfiles).exists():
        with open(a.dfiles, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                adlar = (r.get("adlar") or "").split("|")
                boy = (r.get("boyutlar") or "").split("|")
                for ad, b in zip(adlar, boy):
                    if ad.lower().endswith(".zip"):
                        try:
                            etsy_ad_bayt[ad] = int(b)
                        except (TypeError, ValueError):
                            pass
        etsy_kaynak = f"{a.dfiles} ({len(etsy_ad_bayt)} ZIP kaydi)"
    print(f"   canli anlik goruntu: {etsy_kaynak}", flush=True)

    # ------------------------------------------------ merkezi dizin (paralel)
    sonuc, hatalar = {}, {}
    islenen = [0]

    def isle(d):
        try:
            return d["Name"], zip_icerik(a.remote, a.kok, d["Name"], d["Size"]), None
        except Exception as ex:                                  # noqa: BLE001
            return d["Name"], None, str(ex)[:160]

    print(f"2) Merkezi dizin okumasi ({len(zipler)} ZIP, {a.is_parca} parca)", flush=True)
    son_rapor = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.is_parca) as ex:
        for ad, icerik, hata in ex.map(isle, zipler):
            islenen[0] += 1
            if hata:
                hatalar[ad] = hata
            else:
                sonuc[ad] = icerik
            if time.time() - son_rapor >= 60 or islenen[0] == len(zipler):
                gecen = time.time() - t0
                yuzde = 100.0 * islenen[0] / max(1, len(zipler))
                kalan = gecen / max(1, islenen[0]) * (len(zipler) - islenen[0])
                print(f"   ETA {islenen[0]}/{len(zipler)} | gecen {gecen:.0f}s | "
                      f"kalan ~{kalan:.0f}s | %{yuzde:.1f} | hata {len(hatalar)}", flush=True)
                son_rapor = time.time()

    # ------------------------------------------------ tam ornek (piksel olcumu)
    piksel = {}
    hedef_ciftler = [x.strip().upper() for x in a.tam_ornek.split(",") if x.strip()]
    ornek_zip = [d for d in zipler if ad_coz(d["Name"])[0] in hedef_ciftler]
    if ornek_zip:
        tmp = Path(a.tam_ornek_dizin or (out / "_ornek"))
        tmp.mkdir(parents=True, exist_ok=True)
        print(f"3) Tam indirme + piksel olcumu ({len(ornek_zip)} ZIP)", flush=True)
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
        except ImportError:
            Image = None
            print("   UYARI: Pillow yok, piksel olculmedi", flush=True)
        for i, d in enumerate(ornek_zip, 1):
            yerel = tmp / d["Name"]
            if not yerel.exists():
                rclone(["copyto", f"--drive-root-folder-id={a.kok}", f"{a.remote}:{d['Name']}",
                        str(yerel)])
            olcum = []
            with zipfile.ZipFile(yerel) as z:
                for zi in z.infolist():
                    if zi.filename.lower().endswith((".jpg", ".jpeg", ".png")) and Image:
                        with z.open(zi) as fh:
                            im = Image.open(io.BytesIO(fh.read()))
                            w, h = im.size
                            dpi = (im.info.get("dpi") or ("", ""))[0]
                        olcum.append(f"{Path(zi.filename).name}={w}x{h}@{oran_pikselden(w, h)}"
                                     f"/{dpi or '?'}dpi")
            piksel[d["Name"]] = "; ".join(olcum)
            print(f"   {i}/{len(ornek_zip)} {d['Name']} -> {len(olcum)} gorsel", flush=True)

    # ------------------------------------------------ satirlar
    satirlar, asan_boyut, asan_ad, surum_farkli, yapi = [], [], [], [], Counter()
    for d in zipler:
        ad, boyut = d["Name"], int(d["Size"])
        cift, ed, ed_raw = ad_coz(ad)
        icerik = sonuc.get(ad)
        ic_ad = [Path(x[0]).name for x in icerik] if icerik else []
        pdf_ici = any(x.lower().endswith(".pdf") for x in ic_ad)
        oranlar = sorted({oran_adi(x) for x in ic_ad if x.lower().endswith((".jpg", ".jpeg"))})
        imza = f"{len([x for x in ic_ad if x.lower().endswith(('.jpg','.jpeg'))])}jpg+" \
               f"{len([x for x in ic_ad if x.lower().endswith('.pdf')])}pdf"
        if icerik:
            yapi[imza] += 1
        yeni = boyut + PDF_BAYT
        asiyor = yeni > GUVENLI_BAYT
        e_bayt = etsy_ad_bayt.get(ad)
        ayni = "" if e_bayt is None else ("EVET" if e_bayt == boyut else "HAYIR")
        onay_ad = ad_onerisi(ad, cift, ed_raw) if len(ad) > AD_SINIR else ""
        r = {
            "zip_adi": ad, "cift": cift, "edisyon": ed, "ad_karakter": len(ad),
            "ad_70_asiyor": "EVET" if len(ad) > AD_SINIR else "HAYIR", "ad_onerisi": onay_ad,
            "drive_bayt": boyut, "drive_mb": round(boyut / 1e6, 2),
            "drive_tarih": (d.get("ModTime") or "")[:19],
            "pdf_ekli_bayt": yeni, "pdf_ekli_mb": round(yeni / 1e6, 2),
            "sinir_19_8mb": "ASIYOR" if asiyor else "TAMAM",
            "etsy_bayt": e_bayt if e_bayt is not None else "", "etsy_ad": ad if e_bayt else "",
            "surum_ayni": ayni, "ic_dosya_sayisi": len(ic_ad) if icerik else "",
            "ic_dosyalar": "|".join(ic_ad), "oranlar": ",".join(oranlar),
            "pdf_icinde": ("EVET" if pdf_ici else "HAYIR") if icerik else "",
            "yapi_imzasi": imza if icerik else "", "olculen_pikseller": piksel.get(ad, ""),
            "not": hatalar.get(ad, "") or ("cift/edisyon ad kalibindan cozulemedi" if not cift else ""),
        }
        satirlar.append(r)
        if asiyor:
            asan_boyut.append(r)
        if len(ad) > AD_SINIR:
            asan_ad.append(r)
        if ayni == "HAYIR":
            surum_farkli.append(r)

    with open(out / "ZIP_KONTROL.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)

    # ------------------------------------------------ envanter capraz kontrolu
    env_eksik, zip_fazla, env_sayi = [], [], 0
    if a.envanter and Path(a.envanter).exists():
        zip_kume = {(r["cift"], r["edisyon"]) for r in satirlar if r["cift"]}
        env_kume = set()
        with open(a.envanter, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                env_sayi += 1
                if r.get("cift") and r.get("edisyon"):
                    env_kume.add((r["cift"], r["edisyon"]))
        env_eksik = sorted(env_kume - zip_kume)   # canli ilan var, ZIP yok
        zip_fazla = sorted(zip_kume - env_kume)   # ZIP var, canli ilan yok

    # ------------------------------------------------ ozet
    cift_ed = defaultdict(set)
    for r in satirlar:
        if r["cift"]:
            cift_ed[r["cift"]].add(r["edisyon"])
    eksik = {c: sorted({e.replace("_", " ") for e in EDISYONLAR} - v) for c, v in cift_ed.items()
             if len(v) != 5}
    md = [f"# ZIP KONTROL OZETI ({simdi()} UTC)", "",
          f"- Klasor: Drive folder id `{a.kok}` (ALL_312_ZIPS)",
          f"- ZIP sayisi: {len(zipler)} | merkezi dizin okunan: {len(sonuc)} | hata: {len(hatalar)}",
          f"- Cift sayisi: {len(cift_ed)} | 5 edisyonu eksiksiz olmayan cift: {len(eksik)}",
          f"- Canli Etsy karsilastirmasi: {etsy_kaynak}",
          f"- Surum FARKLI (ad ayni, bayt farkli): {len(surum_farkli)}",
          f"- Etsy anlik goruntusunde bulunmayan ZIP: {sum(1 for r in satirlar if r['surum_ayni'] == '')}",
          f"- PDF eklendikten sonra 19.8 MB guvenlik esigini ASAN: {len(asan_boyut)}",
          f"- 20 MB ham siniri asan (PDF dahil): {sum(1 for r in satirlar if r['pdf_ekli_bayt'] > 20_000_000)}",
          f"- Dosya adi 70 karakteri asan: {len(asan_ad)}",
          f"- En uzun ZIP adi: {max((len(r['zip_adi']) for r in satirlar), default=0)} karakter",
          f"- En buyuk ZIP (PDF ekli): {max((r['pdf_ekli_mb'] for r in satirlar), default=0)} MB",
          f"- Canli ilanla capraz kontrol: envanter {env_sayi} ilan | ZIP'i olmayan ilan "
          f"{len(env_eksik)} | ilani olmayan ZIP {len(zip_fazla)}",
          "", "## Ic yapi imzasi dagilimi", "", "| imza | ZIP |", "|---|---:|"]
    for k, v in yapi.most_common():
        md.append(f"| {k} | {v} |")
    if asan_boyut:
        md += ["", "## 19.8 MB esigini asan ZIP'ler", "",
               "| ZIP | mevcut MB | PDF ekli MB |", "|---|---:|---:|"]
        for r in sorted(asan_boyut, key=lambda x: -x["pdf_ekli_bayt"]):
            md.append(f"| {r['zip_adi']} | {r['drive_mb']} | {r['pdf_ekli_mb']} |")
    else:
        md += ["", "## 19.8 MB esigini asan ZIP yok.", ""]
    if asan_ad:
        md += ["", "## 70 karakteri asan adlar", "", "| ZIP | karakter | oneri |", "|---|---:|---|"]
        for r in asan_ad:
            md.append(f"| {r['zip_adi']} | {r['ad_karakter']} | {r['ad_onerisi']} |")
    if eksik:
        md += ["", "## 5 edisyonu eksik ciftler", ""]
        for c, e in sorted(eksik.items()):
            md.append(f"- {c}: eksik {', '.join(e) or '(fazla edisyon)'}")
    if surum_farkli:
        md += ["", "## Canli ilandan FARKLI surumdeki ZIP'ler", "",
               "| ZIP | Drive bayt | Etsy bayt |", "|---|---:|---:|"]
        for r in surum_farkli[:60]:
            md.append(f"| {r['zip_adi']} | {r['drive_bayt']} | {r['etsy_bayt']} |")
    if hatalar:
        md += ["", "## Okunamayan ZIP'ler", ""]
        for k, v in list(hatalar.items())[:40]:
            md.append(f"- {k}: {v}")
    if env_eksik:
        md += ["", "## Canli ilani olup ZIP'i bulunamayan (cift, edisyon)", ""]
        for c, e in env_eksik[:60]:
            md.append(f"- {c} / {e}")
    if zip_fazla:
        md += ["", "## ZIP'i olup canli ilanda bulunmayan (cift, edisyon)", ""]
        for c, e in zip_fazla[:60]:
            md.append(f"- {c} / {e}")
    if piksel:
        md += ["", "## Tam indirilip olculen ornek ZIP'ler", ""]
        for k in sorted(piksel):
            md.append(f"- **{k}**: {piksel[k]}")
    md += ["", f"- Sure: {time.time()-t0:.0f}s. Yeni ZIP URETILMEDI, Drive'a yazilmadi."]
    (out / "ZIP_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BITTI | {len(satirlar)} satir | asan boyut {len(asan_boyut)} | asan ad {len(asan_ad)} "
          f"| sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
