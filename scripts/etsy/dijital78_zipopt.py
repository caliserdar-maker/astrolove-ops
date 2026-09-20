#!/usr/bin/env python3
"""
DIJITAL 78 v2 - ADIM 3: KAYIPSIZ JPEG OPTIMIZASYONU (Etsy cagrisi YOK).

Yontem: `jpegtran -copy none -optimize` (gerekirse `-progressive`). Bu islem
JPEG katsayilarini YENIDEN KODLAMAZ; yalniz Huffman tablolarini optimize eder ve
istege bagli olarak progressive tarama duzenine gecirir. Kanit olarak her
donusturulen dosyanin cozulmus pikselleri `djpeg -pnm | sha256` ile karsilastirilir;
hash farkliysa o dosya ESKI HALIYLE birakilir.

Iki is:
  1) 19.8 MB esigini asan ZIP'ler: optimize edilir, tesekkur PDF'i eklenir, yeni
     boyut olculur. ICC korunan (-copy icc) surumun boyut farki da raporlanir.
  2) Tum 390 ZIP: yalniz `-copy none -optimize` kazanci OLCULUR (uygulama yok).

Yeni ZIP'ler --opt-dizin altinda birakilir; Drive'a yazma cagiranin isidir.
"""
import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PDF_ADI = "ASTROLOVE_DIGITAL_THANKYOU_EN.pdf"
ESIK = 19_800_000
JPEG_UZANTI = (".jpg", ".jpeg")
SUTUN = ["zip_adi", "cift", "edisyon", "grup", "jpg_sayisi", "orijinal_zip", "orijinal_mb",
         "jpg_orijinal_toplam", "opt_none", "opt_none_kazanc", "opt_none_yuzde",
         "opt_none_prog", "opt_icc", "opt_icc_prog", "secilen_varyant", "secilen_jpg_toplam",
         "yeni_zip", "yeni_zip_pdf_ekli", "yeni_mb_pdf_ekli", "sinir_19_8mb",
         "icc_korunursa_pdf_ekli", "icc_korunursa_mb", "icc_korunursa_sinir",
         "piksel_dogrulama", "dogrulanan_jpg", "geri_alinan_jpg", "icc_profil", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def kos(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=900, **kw)


def rclone_indir(remote, kok, ad, hedef):
    r = kos(["rclone", "copyto", f"--drive-root-folder-id={kok}", f"{remote}:{ad}", str(hedef)])
    if r.returncode != 0:
        raise RuntimeError(f"rclone copyto {ad}: {r.stderr.decode('utf-8', 'replace')[:160]}")


def jpegtran(src, dst, copy_mode, progressive):
    cmd = ["jpegtran", "-copy", copy_mode, "-optimize"]
    if progressive:
        cmd.append("-progressive")
    cmd += ["-outfile", str(dst), str(src)]
    r = kos(cmd)
    if r.returncode != 0 or not Path(dst).exists():
        raise RuntimeError(f"jpegtran({copy_mode},{progressive}) {Path(src).name}: "
                           f"{r.stderr.decode('utf-8', 'replace')[:120]}")
    return Path(dst).stat().st_size


def piksel_hash(path):
    """djpeg ile cozup ham piksel akisinin sha256'si. Bellek dostu (boru hatti)."""
    p1 = subprocess.Popen(["djpeg", "-pnm", str(path)], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL)
    h = hashlib.sha256()
    try:
        for parca in iter(lambda: p1.stdout.read(1 << 20), b""):
            h.update(parca)
    finally:
        p1.stdout.close()
        p1.wait(timeout=900)
    if p1.returncode != 0:
        raise RuntimeError(f"djpeg {Path(path).name} -> {p1.returncode}")
    return h.hexdigest()


def icc_oku(path):
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(path) as im:
            raw = im.info.get("icc_profile")
        if not raw:
            return "YOK"
        try:
            from PIL import ImageCms
            import io
            return ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(raw))).strip()
        except Exception:                                    # noqa: BLE001
            return f"VAR ({len(raw)} bayt)"
    except Exception as ex:                                  # noqa: BLE001
        return f"OKUNAMADI ({str(ex)[:40]})"


def ad_coz(zad):
    m = re.match(r"AstroLove_([A-Za-z]+)_([A-Za-z]+)_(.+)_ALL_SIZES\.zip$", zad)
    if not m:
        return "", ""
    return "_".join(sorted([m.group(1).upper(), m.group(2).upper()])), m.group(3).replace("_", " ")


def zip_isle(gorev):
    """Tek ZIP: indir, ac, optimize et, (gerekirse) dogrula ve yeniden paketle."""
    (remote, kok, d, tam_is, dogrula, pdf, opt_dizin, calisma, esik) = gorev
    ad, boyut = d["Name"], int(d["Size"])
    cift, edisyon = ad_coz(ad)
    is_dizin = Path(calisma) / hashlib.sha1(ad.encode()).hexdigest()[:12]
    satir = {"zip_adi": ad, "cift": cift, "edisyon": edisyon,
             "grup": "ASAN" if tam_is else "OLCUM", "orijinal_zip": boyut,
             "orijinal_mb": round(boyut / 1e6, 2), "piksel_dogrulama": "-",
             "dogrulanan_jpg": 0, "geri_alinan_jpg": 0, "not": ""}
    try:
        is_dizin.mkdir(parents=True, exist_ok=True)
        yerel = is_dizin / ad
        rclone_indir(remote, kok, ad, yerel)
        ac = is_dizin / "x"; ac.mkdir(exist_ok=True)
        with zipfile.ZipFile(yerel) as z:
            bilgi = z.infolist()
            z.extractall(ac)
        jpgler = [zi for zi in bilgi if zi.filename.lower().endswith(JPEG_UZANTI)]
        satir["jpg_sayisi"] = len(jpgler)
        satir["jpg_orijinal_toplam"] = sum(zi.file_size for zi in jpgler)
        satir["icc_profil"] = icc_oku(ac / jpgler[0].filename) if jpgler else "-"

        varyant = {}
        for mod, prog, anahtar in (("none", False, "opt_none"), ("none", True, "opt_none_prog"),
                                   ("icc", False, "opt_icc"), ("icc", True, "opt_icc_prog")):
            if not tam_is and anahtar != "opt_none":
                continue
            top, yollar = 0, {}
            for zi in jpgler:
                src = ac / zi.filename
                dst = ac / f"{zi.filename}.{anahtar}"
                top += jpegtran(src, dst, mod, prog)
                yollar[zi.filename] = dst
            varyant[anahtar] = (top, yollar)
            satir[anahtar] = top
        if not tam_is:
            for k in ("opt_none_prog", "opt_icc", "opt_icc_prog"):
                satir[k] = ""
        satir["opt_none_kazanc"] = satir["jpg_orijinal_toplam"] - satir["opt_none"]
        satir["opt_none_yuzde"] = (round(100.0 * satir["opt_none_kazanc"]
                                         / max(1, satir["jpg_orijinal_toplam"]), 2))

        if tam_is:
            # Varyant secimi: once -copy none -optimize; esigi hala asiyorsa progressive.
            sira = ["opt_none", "opt_none_prog"]
            secilen = sira[0]
            for k in sira:
                if boyut - satir["jpg_orijinal_toplam"] + satir[k] + pdf["bayt"] <= esik:
                    secilen = k
                    break
                secilen = k
            satir["secilen_varyant"] = {"opt_none": "-copy none -optimize",
                                        "opt_none_prog": "-copy none -optimize -progressive"}[secilen]
            satir["secilen_jpg_toplam"] = satir[secilen]

            # Piksel birebirligi: her JPG icin eski/yeni cozulmus hash
            geri_alinan = []
            sec_yollar = varyant[secilen][1]
            for zi in jpgler:
                src = ac / zi.filename
                dst = sec_yollar[zi.filename]
                if piksel_hash(src) != piksel_hash(dst):
                    geri_alinan.append(zi.filename)
                    shutil.copyfile(src, dst)
                satir["dogrulanan_jpg"] += 1
            satir["geri_alinan_jpg"] = len(geri_alinan)
            satir["piksel_dogrulama"] = "BIREBIR" if not geri_alinan else f"FARK: {len(geri_alinan)}"
            if geri_alinan:
                satir["not"] = "geri alinan: " + ",".join(geri_alinan[:3])

            # Yeniden paketle: orijinal sikistirma turu korunur, PDF eklenir
            hedef = Path(opt_dizin) / ad
            hedef.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(hedef, "w") as z:
                for zi in bilgi:
                    kaynak = sec_yollar.get(zi.filename) or (ac / zi.filename)
                    yeni = zipfile.ZipInfo(zi.filename, date_time=zi.date_time)
                    yeni.compress_type = zi.compress_type
                    yeni.external_attr = zi.external_attr
                    z.writestr(yeni, Path(kaynak).read_bytes())
            satir["yeni_zip"] = hedef.stat().st_size
            with zipfile.ZipFile(hedef, "a", zipfile.ZIP_DEFLATED) as z:
                z.write(pdf["yol"], PDF_ADI)
            satir["yeni_zip_pdf_ekli"] = hedef.stat().st_size
            satir["yeni_mb_pdf_ekli"] = round(satir["yeni_zip_pdf_ekli"] / 1e6, 2)
            satir["sinir_19_8mb"] = ("TAMAM" if satir["yeni_zip_pdf_ekli"] <= esik else "HALA ASIYOR")
            # ICC profili korunursa (ayni yolla, yalniz JPG toplami degisir) tahmini boyut
            icc_anahtar = "opt_icc_prog" if secilen == "opt_none_prog" else "opt_icc"
            icc_boyut = (satir["yeni_zip_pdf_ekli"] - satir["secilen_jpg_toplam"]
                         + satir[icc_anahtar])
            satir["icc_korunursa_pdf_ekli"] = icc_boyut
            satir["icc_korunursa_mb"] = round(icc_boyut / 1e6, 2)
            satir["icc_korunursa_sinir"] = "TAMAM" if icc_boyut <= esik else "HALA ASIYOR"
        else:
            satir["secilen_varyant"] = "(olculdu, uygulanmadi)"
            if dogrula:
                zi = jpgler[0]
                src, dst = ac / zi.filename, varyant["opt_none"][1][zi.filename]
                ayni = piksel_hash(src) == piksel_hash(dst)
                satir["dogrulanan_jpg"] = 1
                satir["piksel_dogrulama"] = "BIREBIR" if ayni else "FARK"
            tahmini = boyut - satir["jpg_orijinal_toplam"] + satir["opt_none"] + pdf["bayt"]
            satir["yeni_zip_pdf_ekli"] = tahmini
            satir["yeni_mb_pdf_ekli"] = round(tahmini / 1e6, 2)
            satir["sinir_19_8mb"] = "TAMAM" if tahmini <= esik else "HALA ASIYOR"
    except Exception as ex:                                  # noqa: BLE001
        satir["not"] = f"HATA: {str(ex)[:150]}"
    finally:
        shutil.rmtree(is_dizin, ignore_errors=True)
    return satir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--kok", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--opt-dizin", required=True)
    ap.add_argument("--calisma", default="_work/zipopt")
    ap.add_argument("--esik", type=int, default=ESIK)
    ap.add_argument("--is-parca", type=int, default=6)
    ap.add_argument("--ornek-dogrula", type=int, default=25,
                    help="Esigi asmayan ZIP'lerden kac tanesinde piksel dogrulamasi yapilsin")
    ap.add_argument("--limit", type=int, default=0, help="test icin ZIP sayisi siniri")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    Path(a.calisma).mkdir(parents=True, exist_ok=True)
    Path(a.opt_dizin).mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    pdf = {"yol": str(Path(a.pdf).resolve()), "bayt": Path(a.pdf).stat().st_size}
    print(f"tesekkur PDF: {pdf['bayt']} bayt", flush=True)

    r = kos(["rclone", "lsjson", f"--drive-root-folder-id={a.kok}", f"{a.remote}:", "--files-only"])
    if r.returncode != 0:
        raise SystemExit(f"HATA: lsjson {r.stderr.decode('utf-8', 'replace')[:200]}")
    zipler = sorted([d for d in json.loads(r.stdout) if d["Name"].lower().endswith(".zip")],
                    key=lambda d: -int(d["Size"]))
    if a.limit:
        zipler = zipler[:a.limit]
    asan = [d for d in zipler if int(d["Size"]) + pdf["bayt"] > a.esik]
    asan_ad = {d["Name"] for d in asan}
    digerleri = [d for d in zipler if d["Name"] not in asan_ad]
    random.seed(20260920)
    ornek = {d["Name"] for d in random.sample(digerleri, min(a.ornek_dogrula, len(digerleri)))}
    print(f"{len(zipler)} ZIP | esigi asan {len(asan)} | ornek dogrulama {len(ornek)}", flush=True)

    gorevler = [(a.remote, a.kok, d, d["Name"] in asan_ad, d["Name"] in ornek, pdf,
                 a.opt_dizin, a.calisma, a.esik) for d in zipler]
    satirlar, islenen, son = [], 0, time.time()
    with cf.ThreadPoolExecutor(max_workers=a.is_parca) as ex:
        for s in ex.map(zip_isle, gorevler):
            satirlar.append(s)
            islenen += 1
            if time.time() - son >= 60 or islenen == len(gorevler):
                gecen = time.time() - t0
                kalan = gecen / max(1, islenen) * (len(gorevler) - islenen)
                hata = sum(1 for x in satirlar if x["not"].startswith("HATA"))
                print(f"   ETA {islenen}/{len(gorevler)} | gecen {gecen:.0f}s | kalan ~{kalan:.0f}s "
                      f"| %{100*islenen/len(gorevler):.1f} | hata {hata}", flush=True)
                son = time.time()

    satirlar.sort(key=lambda s: (s["grup"] != "ASAN", -int(s["orijinal_zip"])))
    with open(out / "ZIP_OPT.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow(s)

    iyi = [s for s in satirlar if not s["not"].startswith("HATA")]
    asan_s = [s for s in iyi if s["grup"] == "ASAN"]
    kalan_asim = [s for s in asan_s if s["sinir_19_8mb"] != "TAMAM"]
    toplam_orj = sum(s["jpg_orijinal_toplam"] for s in iyi)
    toplam_opt = sum(s["opt_none"] for s in iyi)
    zip_orj = sum(s["orijinal_zip"] for s in iyi)
    dogrulanan = sum(s["dogrulanan_jpg"] for s in iyi)
    geri = sum(s["geri_alinan_jpg"] for s in iyi)
    fark_yok = [s for s in iyi if s["piksel_dogrulama"] == "BIREBIR"]

    md = [f"# KAYIPSIZ JPEG OPTIMIZASYONU ({simdi()} UTC)", "",
          "Yontem: `jpegtran -copy none -optimize` (gerekirse `-progressive`). Yeniden kodlama YOK.",
          "Kanit: `djpeg -pnm | sha256` ile cozulmus piksel akisi karsilastirmasi.", "",
          "## Ozet", "",
          f"- Islenen ZIP: {len(iyi)} / {len(satirlar)} (hata {len(satirlar) - len(iyi)})",
          f"- Piksel dogrulamasi yapilan JPG: {dogrulanan}, BIREBIR olmayan: {geri}",
          f"- Piksel dogrulamasi BIREBIR cikan ZIP: {len(fark_yok)}", "",
          "## 1) 19.8 MB esigini asan ZIP'ler", "",
          f"- Sayi: {len(asan_s)}",
          f"- Optimizasyon + PDF sonrasi HALA asan: **{len(kalan_asim)}**", ""]
    if asan_s:
        md += ["| ZIP | eski MB | JPG kazanc | secilen | yeni MB (PDF ekli) | durum | "
               "ICC korunursa MB | ICC durum | ICC profil |",
               "|---|---:|---:|---|---:|---|---:|---|---|"]
        for s in asan_s:
            kz = s["jpg_orijinal_toplam"] - s["secilen_jpg_toplam"]
            md.append(f"| {s['zip_adi']} | {s['orijinal_mb']} | {kz/1e6:.2f} MB "
                      f"({100*kz/max(1,s['jpg_orijinal_toplam']):.1f}%) | "
                      f"`{s['secilen_varyant']}` | {s['yeni_mb_pdf_ekli']} | "
                      f"{s['sinir_19_8mb']} | {s.get('icc_korunursa_mb','')} | "
                      f"{s.get('icc_korunursa_sinir','')} | {s['icc_profil']} |")
    if kalan_asim:
        md += ["", "### HALA 19.8 MB'i asanlar (baska islem YAPILMADI)", ""]
        for s in kalan_asim:
            md.append(f"- {s['zip_adi']}: {s['yeni_mb_pdf_ekli']} MB")
    else:
        md += ["", "### Esigi asan kalmadi.", ""]
    if asan_s:
        icc_kz = sum(s["opt_icc"] - s["opt_none"] for s in asan_s if s.get("opt_icc"))
        prog_kz = sum(s["opt_none"] - s["opt_none_prog"] for s in asan_s if s.get("opt_none_prog"))
        md += ["", "## ICC ve progressive farki (asan 23 uzerinde)", "",
               f"- `-copy icc` surumu `-copy none`'dan **{icc_kz/1e6:.3f} MB daha buyuk** "
               f"(ICC profili korunursa odenen bedel).",
               f"- `-progressive` eklemek `-copy none`'a gore **{prog_kz/1e6:.3f} MB daha kazandirir**.",
               f"- Olculen ICC profilleri: {dict(Counter(s['icc_profil'] for s in asan_s))}",
               f"- ICC korunan surumle 19.8 MB'i asan: "
               f"{sum(1 for s in asan_s if s.get('icc_korunursa_sinir') == 'HALA ASIYOR')}",
               "- NOT: ICC profilini korumanin bedeli ZIP basina cok kucuktur; baski dosyasinda",
               "  renk yonetimi acisindan `-copy icc` daha guvenlidir. Karar Serdar'in."]
    md += ["", "## 2) Tum ZIP'ler icin olasi kazanc (uygulama YOK)", "",
           f"- Olculen ZIP: {len(iyi)}",
           f"- JPG toplami: {toplam_orj/1e6:.1f} MB -> {toplam_opt/1e6:.1f} MB",
           f"- **Kazanc: {(toplam_orj-toplam_opt)/1e6:.1f} MB "
           f"(%{100*(toplam_orj-toplam_opt)/max(1,toplam_orj):.2f})**",
           f"- ZIP toplami (referans): {zip_orj/1e6:.1f} MB",
           f"- ZIP basina ortalama kazanc: {(toplam_orj-toplam_opt)/max(1,len(iyi))/1e6:.3f} MB", ""]
    hatalar = [s for s in satirlar if s["not"].startswith("HATA")]
    if hatalar:
        md += ["## Hatalar", ""] + [f"- {s['zip_adi']}: {s['not']}" for s in hatalar[:30]]
    md += ["", f"- Sure: {time.time()-t0:.0f}s. Yeni ZIP'ler: `{a.opt_dizin}` "
           f"({len(list(Path(a.opt_dizin).glob('*.zip')))} dosya)."]
    (out / "ZIP_OPT_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BITTI | asan {len(asan_s)} | hala asan {len(kalan_asim)} | "
          f"390 kazanc {(toplam_orj-toplam_opt)/1e6:.1f} MB | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
