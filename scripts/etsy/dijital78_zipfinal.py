#!/usr/bin/env python3
"""
DIJITAL 78 - ZIP URETIMI (Etsy cagrisi YOK).

390 ZIP'in hepsine kayipsiz JPEG optimizasyonu (`jpegtran -copy icc -optimize`)
uygulanir, her ZIP'e tesekkur PDF'i eklenir ve ciktilar cift bazinda toplanir.

Kayipsizlik kaniti: her JPG icin `djpeg -pnm | sha256` ile cozulmus piksel akisi
karsilastirilir. Fark varsa o JPG ORIJINAL haliyle paketlenir.

Kapilar (her ZIP icin):
  1) boyut < 19.8 MB
  2) dosya adi <= 70 karakter
  3) icerik = 5 JPG + "Print and Care Guide" PDF + tesekkur PDF

Cikti: <out-dizin>/<CIFT>/<zip> (istege bagli olarak Drive'a yuklenip yerelden
silinir) + ZIP_FINAL.csv + ZIP_FINAL_OZET.md
"""
import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import re
import shutil
import subprocess
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PDF_ADI = "ASTROLOVE_DIGITAL_THANKYOU_EN.pdf"
ESIK = 19_800_000
AD_SINIR = 70
JPG_SAYISI = 5
JPEG_UZANTI = (".jpg", ".jpeg")
SUTUN = ["zip_adi", "cift", "edisyon", "ad_uzunluk", "orijinal_zip", "orijinal_mb",
         "jpg_sayisi", "jpg_orijinal_toplam", "jpg_opt_icc", "jpg_kazanc", "jpg_kazanc_yuzde",
         "yeni_zip", "yeni_mb", "kapi_boyut", "kapi_ad", "kapi_icerik",
         "icerik_jpg", "icerik_kilavuz_pdf", "icerik_tesekkur_pdf",
         "piksel_dogrulama", "dogrulanan_jpg", "geri_alinan_jpg", "icc_profil",
         "drive_yolu", "sonuc", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def kos(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=1800, **kw)


def rclone_indir(remote, kok, ad, hedef):
    r = kos(["rclone", "copyto", f"--drive-root-folder-id={kok}", f"{remote}:{ad}", str(hedef)])
    if r.returncode != 0:
        raise RuntimeError(f"rclone copyto {ad}: {r.stderr.decode('utf-8', 'replace')[:160]}")


def rclone_yukle(remote, kok, yerel, uzak_yol):
    r = kos(["rclone", "copyto", f"--drive-root-folder-id={kok}",
             "--drive-chunk-size=32M", str(yerel), f"{remote}:{uzak_yol}"])
    if r.returncode != 0:
        raise RuntimeError(f"rclone yukleme {uzak_yol}: {r.stderr.decode('utf-8', 'replace')[:160]}")


def jpegtran_icc(src, dst):
    r = kos(["jpegtran", "-copy", "icc", "-optimize", "-outfile", str(dst), str(src)])
    if r.returncode != 0 or not Path(dst).exists():
        raise RuntimeError(f"jpegtran {Path(src).name}: {r.stderr.decode('utf-8', 'replace')[:120]}")
    return Path(dst).stat().st_size


def piksel_hash(path):
    """djpeg ile cozup ham piksel akisinin sha256'si (boru hatti, bellek dostu)."""
    p1 = subprocess.Popen(["djpeg", "-pnm", str(path)], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL)
    h = hashlib.sha256()
    try:
        for parca in iter(lambda: p1.stdout.read(1 << 20), b""):
            h.update(parca)
    finally:
        p1.stdout.close()
        p1.wait(timeout=1800)
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
            import io
            from PIL import ImageCms
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
    (remote, kok, d, pdf, out_dizin, calisma, esik, yukle_kok, yukle_yol) = gorev
    ad, boyut = d["Name"], int(d["Size"])
    cift, edisyon = ad_coz(ad)
    is_dizin = Path(calisma) / hashlib.sha1(ad.encode()).hexdigest()[:12]
    satir = {"zip_adi": ad, "cift": cift, "edisyon": edisyon, "ad_uzunluk": len(ad),
             "orijinal_zip": boyut, "orijinal_mb": round(boyut / 1e6, 2),
             "dogrulanan_jpg": 0, "geri_alinan_jpg": 0, "drive_yolu": "", "not": ""}
    try:
        if not cift:
            raise RuntimeError("dosya adi kalibi taninmadi")
        is_dizin.mkdir(parents=True, exist_ok=True)
        yerel = is_dizin / ad
        rclone_indir(remote, kok, ad, yerel)
        ac = is_dizin / "x"
        ac.mkdir(exist_ok=True)
        with zipfile.ZipFile(yerel) as z:
            bilgi = z.infolist()
            z.extractall(ac)
        jpgler = [zi for zi in bilgi if zi.filename.lower().endswith(JPEG_UZANTI)]
        pdfler = [zi for zi in bilgi if zi.filename.lower().endswith(".pdf")]
        satir["jpg_sayisi"] = len(jpgler)
        satir["jpg_orijinal_toplam"] = sum(zi.file_size for zi in jpgler)
        satir["icc_profil"] = icc_oku(ac / jpgler[0].filename) if jpgler else "-"

        # 1) kayipsiz optimizasyon (ICC korunur) + piksel birebirlik kaniti
        toplam, geri_alinan = 0, []
        for zi in jpgler:
            src = ac / zi.filename
            dst = ac / f"{zi.filename}.opt"
            jpegtran_icc(src, dst)
            if piksel_hash(src) != piksel_hash(dst):
                geri_alinan.append(zi.filename)
                shutil.copyfile(src, dst)
            satir["dogrulanan_jpg"] += 1
            toplam += dst.stat().st_size
        satir["jpg_opt_icc"] = toplam
        satir["jpg_kazanc"] = satir["jpg_orijinal_toplam"] - toplam
        satir["jpg_kazanc_yuzde"] = round(100.0 * satir["jpg_kazanc"]
                                          / max(1, satir["jpg_orijinal_toplam"]), 2)
        satir["geri_alinan_jpg"] = len(geri_alinan)
        satir["piksel_dogrulama"] = "BIREBIR" if not geri_alinan else f"FARK: {len(geri_alinan)}"
        if geri_alinan:
            satir["not"] = "orijinal birakilan: " + ",".join(geri_alinan[:3])

        # 2) yeniden paketle + tesekkur PDF
        hedef = Path(out_dizin) / cift / ad
        hedef.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(hedef, "w") as z:
            for zi in [x for x in bilgi if not x.is_dir()]:
                if zi.filename.lower().endswith(JPEG_UZANTI):
                    veri = (ac / f"{zi.filename}.opt").read_bytes()
                else:
                    veri = (ac / zi.filename).read_bytes()
                yeni = zipfile.ZipInfo(zi.filename, date_time=zi.date_time)
                yeni.compress_type = zi.compress_type
                yeni.external_attr = zi.external_attr
                z.writestr(yeni, veri)
        if PDF_ADI not in [zi.filename for zi in bilgi]:
            with zipfile.ZipFile(hedef, "a", zipfile.ZIP_DEFLATED) as z:
                z.write(pdf["yol"], PDF_ADI)
        else:
            satir["not"] = (satir["not"] + " | tesekkur PDF kaynakta zaten vardi").strip(" |")

        # 3) kapilar: dogrudan URETILEN dosyadan olculur
        satir["yeni_zip"] = hedef.stat().st_size
        satir["yeni_mb"] = round(satir["yeni_zip"] / 1e6, 2)
        with zipfile.ZipFile(hedef) as z:
            adlar = [zi.filename for zi in z.infolist() if not zi.is_dir()]
            bozuk = z.testzip()
        if bozuk:
            raise RuntimeError(f"ZIP dogrulamasi basarisiz: {bozuk}")
        s_jpg = [n for n in adlar if n.lower().endswith(JPEG_UZANTI)]
        s_pdf = [n for n in adlar if n.lower().endswith(".pdf")]
        kilavuz = [n for n in s_pdf if "print" in n.lower() and "care" in n.lower()]
        tesekkur = [n for n in s_pdf if n == PDF_ADI]
        satir["icerik_jpg"] = len(s_jpg)
        satir["icerik_kilavuz_pdf"] = kilavuz[0] if kilavuz else "YOK"
        satir["icerik_tesekkur_pdf"] = "VAR" if tesekkur else "YOK"
        satir["kapi_boyut"] = "GECTI" if satir["yeni_zip"] < esik else "KALDI"
        satir["kapi_ad"] = "GECTI" if len(ad) <= AD_SINIR else "KALDI"
        satir["kapi_icerik"] = ("GECTI" if (len(s_jpg) == JPG_SAYISI and kilavuz and tesekkur
                                           and len(adlar) == JPG_SAYISI + 2) else "KALDI")
        satir["sonuc"] = ("GECTI" if all(satir[k] == "GECTI"
                                         for k in ("kapi_boyut", "kapi_ad", "kapi_icerik"))
                          else "KALDI")
        if len(pdfler) != 1:
            satir["not"] = (satir["not"] + f" | kaynakta {len(pdfler)} PDF").strip(" |")

        # 4) Drive'a yukle ve yerelden sil (disk icin)
        if yukle_kok:
            uzak = f"{yukle_yol}/{cift}/{ad}"
            rclone_yukle(remote, yukle_kok, hedef, uzak)
            satir["drive_yolu"] = uzak
            hedef.unlink()
    except Exception as ex:                                  # noqa: BLE001
        satir["not"] = f"HATA: {str(ex)[:150]}"
        satir["sonuc"] = "HATA"
    finally:
        shutil.rmtree(is_dizin, ignore_errors=True)
    return satir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", default="gdrive")
    ap.add_argument("--kok", required=True, help="kaynak ZIP klasoru (Drive folder id)")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True, help="rapor dizini")
    ap.add_argument("--out-dizin", required=True, help="uretilen ZIP dizini")
    ap.add_argument("--calisma", default="_work/zipfinal")
    ap.add_argument("--esik", type=int, default=ESIK)
    ap.add_argument("--is-parca", type=int, default=6)
    ap.add_argument("--yukle-kok", default="", help="hedef Drive folder id (DIJITAL_78)")
    ap.add_argument("--yukle-yol", default="ZIP_FINAL")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    Path(a.calisma).mkdir(parents=True, exist_ok=True)
    Path(a.out_dizin).mkdir(parents=True, exist_ok=True)
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
    print(f"{len(zipler)} ZIP islenecek | hedef {a.yukle_yol if a.yukle_kok else a.out_dizin}",
          flush=True)

    gorevler = [(a.remote, a.kok, d, pdf, a.out_dizin, a.calisma, a.esik,
                 a.yukle_kok, a.yukle_yol) for d in zipler]
    satirlar, islenen, son = [], 0, time.time()
    with cf.ThreadPoolExecutor(max_workers=a.is_parca) as ex:
        for s in ex.map(zip_isle, gorevler):
            satirlar.append(s)
            islenen += 1
            if time.time() - son >= 60 or islenen == len(gorevler):
                gecen = time.time() - t0
                kalan = gecen / max(1, islenen) * (len(gorevler) - islenen)
                kotu = sum(1 for x in satirlar if x.get("sonuc") != "GECTI")
                print(f"   ETA {islenen}/{len(gorevler)} | gecen {gecen:.0f}s | kalan ~{kalan:.0f}s "
                      f"| %{100*islenen/len(gorevler):.1f} | gecmeyen {kotu}", flush=True)
                son = time.time()

    satirlar.sort(key=lambda s: (s["cift"], s["zip_adi"]))
    with open(out / "ZIP_FINAL.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow(s)

    gecti = [s for s in satirlar if s.get("sonuc") == "GECTI"]
    kaldi = [s for s in satirlar if s.get("sonuc") != "GECTI"]
    ciftler = Counter(s["cift"] for s in gecti)
    eksik_cift = {c: n for c, n in ciftler.items() if n != 5}
    en_buyuk = max(gecti, key=lambda s: s["yeni_zip"]) if gecti else None
    orj = sum(s.get("jpg_orijinal_toplam", 0) for s in satirlar if s.get("jpg_opt_icc"))
    opt = sum(s.get("jpg_opt_icc", 0) for s in satirlar if s.get("jpg_opt_icc"))
    birebir = sum(1 for s in satirlar if s.get("piksel_dogrulama") == "BIREBIR")
    geri = sum(s.get("geri_alinan_jpg", 0) for s in satirlar)

    md = [f"# ZIP_FINAL ({simdi()} UTC)", "",
          "Yontem: `jpegtran -copy icc -optimize` (yeniden kodlama YOK, ICC profili korunur).",
          "Kanit: her JPG icin `djpeg -pnm | sha256`; fark cikarsa JPG orijinal birakilir.", "",
          "## Ozet", "",
          f"- ZIP: {len(satirlar)} islendi, **{len(gecti)} GECTI**, {len(kaldi)} gecemedi",
          f"- Cift sayisi: {len(ciftler)} (5 ZIP'i tam olmayan: {len(eksik_cift)})",
          f"- Piksel dogrulamasi BIREBIR ZIP: {birebir} | orijinal birakilan JPG: {geri}",
          f"- JPG toplami: {orj/1e6:.1f} MB -> {opt/1e6:.1f} MB "
          f"(kazanc {(orj-opt)/1e6:.1f} MB, %{100*(orj-opt)/max(1,orj):.2f})", ""]
    if en_buyuk:
        md += [f"- **En buyuk ZIP: {en_buyuk['yeni_mb']} MB** ({en_buyuk['zip_adi']}) "
               f"- esik 19.8 MB", ""]
    md += ["## Kapilar", "",
           f"- boyut < 19.8 MB: {sum(1 for s in satirlar if s.get('kapi_boyut') == 'GECTI')}"
           f"/{len(satirlar)}",
           f"- dosya adi <= 70 karakter: {sum(1 for s in satirlar if s.get('kapi_ad') == 'GECTI')}"
           f"/{len(satirlar)} (en uzun: {max((s['ad_uzunluk'] for s in satirlar), default=0)})",
           f"- icerik 5 JPG + kilavuz PDF + tesekkur PDF: "
           f"{sum(1 for s in satirlar if s.get('kapi_icerik') == 'GECTI')}/{len(satirlar)}", ""]
    if kaldi:
        md += ["## Gecemeyenler", "", "| ZIP | MB | boyut | ad | icerik | not |", "|---|---:|---|---|---|---|"]
        for s in kaldi[:60]:
            md.append(f"| {s['zip_adi']} | {s.get('yeni_mb','')} | {s.get('kapi_boyut','')} | "
                      f"{s.get('kapi_ad','')} | {s.get('kapi_icerik','')} | {s['not'][:80]} |")
    if eksik_cift:
        md += ["", "## 5 ZIP'i tam olmayan ciftler", ""]
        md += [f"- {c}: {n} ZIP" for c, n in sorted(eksik_cift.items())]
    md += ["", f"- Sure: {time.time()-t0:.0f}s | CSV: `ZIP_FINAL.csv`",
           f"- ICC profilleri: {dict(Counter(s.get('icc_profil', '-') for s in satirlar))}"]
    (out / "ZIP_FINAL_OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BITTI | gecti {len(gecti)}/{len(satirlar)} | en buyuk "
          f"{en_buyuk['yeni_mb'] if en_buyuk else 0} MB | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
