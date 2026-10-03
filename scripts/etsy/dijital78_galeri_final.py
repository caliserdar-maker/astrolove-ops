#!/usr/bin/env python3
"""
DIJITAL 78 - 78 CIFT ICIN GALERI URETIMI (Etsy cagrisi YOK).

Her cift icin 4 gorsel uretilir (BES_RENK, WHAT'S INCLUDED, PRINT SIZES,
HOW TO DOWNLOAD & PRINT); posterler o ciftin ZIP_FINAL arsivlerinden gelen
GERCEK artwork'tur (arka plan yok) ve baski boylari ayni ZIP'te OLCULEN
pikselden turetilir. Diger galeri ogeleri POD'dan birebir alinir (uretim yok).

Ciktilar: GALERI_FINAL/<CIFT>/*.jpg, GALERI_PLAN.csv (cift basina 15 satir),
KONTROL_TABLOSU.jpg (78 cift 5 COLORS, 13x6).
"""
import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pod"))
import dijital_kartlar as K  # noqa: E402
from pod_gallery_sample import Fonts, palette  # noqa: E402

EDISYON_SIRA = ["Midnight_Blue", "Deep_Black", "Warm_Parchment", "Champagne_Ivory", "Pure_White"]
ORANLAR = {"2:3": 2 / 3, "3:4": 3 / 4, "4:5": 4 / 5, "11:14": 11 / 14, "A": 1 / 2 ** 0.5}
# POD galeri standardi (ARIES_LEO canli ilanda dogrulandi) -> dijital galeri sirasi
PLAN = [
    (1, "KAPAK", "POD", "POD galeri 1 (kapak, etiketsiz)"),
    (2, "VIDEO", "POD", "POD video 1 (V11)"),
    (3, "BES_RENK", "URETILEN", "BES_RENK.jpg"),
    (4, "ODA_1", "POD", "POD galeri 2"),
    (5, "ODA_2", "POD", "POD galeri 3"),
    (6, "SYMBOL_STORY", "POD", "POD galeri 4"),
    (7, "CRAFTED", "POD", "POD galeri 5"),
    (8, "WHATS_INCLUDED", "URETILEN", "WHATS_INCLUDED.jpg"),
    (9, "PRINT_SIZES", "URETILEN", "PRINT_SIZES.jpg"),
    (10, "HOW_TO_DOWNLOAD", "URETILEN", "HOW_TO_DOWNLOAD.jpg"),
    (11, "EDISYON_MIDNIGHT_BLUE", "POD", "POD galeri 9"),
    (12, "EDISYON_DEEP_BLACK", "POD", "POD galeri 10"),
    (13, "EDISYON_WARM_PARCHMENT", "POD", "POD galeri 11"),
    (14, "EDISYON_CHAMPAGNE_IVORY", "POD", "POD galeri 12"),
    (15, "EDISYON_PURE_WHITE", "POD", "POD galeri 13"),
]
KART_DOSYA = {"WHATS_INCLUDED": "WHATS_INCLUDED.jpg", "PRINT_SIZES": "PRINT_SIZES.jpg",
              "HOW_TO_DOWNLOAD": "HOW_TO_DOWNLOAD.jpg"}


def kos(cmd, timeout=1800):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def rclone(*args, timeout=1800):
    r = kos(["rclone", *args], timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {args[0]}: {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout.decode("utf-8", "replace")


def indir(url, hedef):
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-ops/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(hedef, "wb") as fh:
        shutil.copyfileobj(r, fh)


def oran_adi(w, h):
    return min(ORANLAR, key=lambda k: abs(ORANLAR[k] - w / h))


def zipten(zip_yolu, hedef_yukseklik=1500):
    """Olcum (tam piksel) + 2:3 posteri (draft ile hizli cozulur, arka plan yok)."""
    olcum, poster = {}, None
    with zipfile.ZipFile(zip_yolu) as z:
        for zi in z.infolist():
            if zi.is_dir() or not zi.filename.lower().endswith((".jpg", ".jpeg")):
                continue
            veri = z.read(zi)
            im = Image.open(io.BytesIO(veri))
            tam = im.size
            olcum[oran_adi(*tam)] = tam
            if oran_adi(*tam) == "2:3":
                im.draft("RGB", (tam[0] // 4, tam[1] // 4))
                im = im.convert("RGB")
                k = hedef_yukseklik / im.height
                poster = im.resize((max(1, int(im.width * k)), hedef_yukseklik), Image.LANCZOS)
    return olcum, poster


def cift_etiketi(cift):
    return " • ".join(p.capitalize().upper() for p in cift.split("_"))


def kaydet_sinirli(im, yol, sinir):
    for q in (94, 90, 86, 82, 78, 72, 66):
        im.save(yol, "JPEG", quality=q, optimize=True, subsampling=0 if q >= 88 else 1)
        if yol.stat().st_size <= sinir:
            return q
    return q


def cift_isle(gorev):
    (cift, uzak, calisma, out, fonts, pal, yukle) = gorev
    t = time.time()
    ic = Path(calisma) / cift
    ic.mkdir(parents=True, exist_ok=True)
    satir = {"cift": cift, "sonuc": "GECTI", "not": "", "sure": 0}
    try:
        rclone("copy", f"{uzak}/{cift}", str(ic), "-q", "--transfers", "4")
        posterler, olcum = [], {}
        for ed in EDISYON_SIRA:
            eslesen = sorted(ic.glob(f"*_{ed}_*.zip"))
            if not eslesen:
                raise RuntimeError(f"{ed} ZIP yok")
            o, p = zipten(eslesen[0])
            olcum.update(o)
            if p is None:
                raise RuntimeError(f"{ed} icinde 2:3 JPG yok")
            posterler.append(p)
        K.OLCUM = olcum
        F = Fonts(fonts)
        etiket = cift_etiketi(cift)
        hedef = Path(out) / cift
        hedef.mkdir(parents=True, exist_ok=True)
        im0 = Image.new("RGB", (10, 10))
        d0 = ImageDraw.Draw(im0)
        hatalar = []
        for ad, rows, en_sinir in (("INCLUDED", K.KART["INCLUDED"]["rows"], 1340),
                                   ("HOWTO", K.KART["HOWTO"]["rows"], 1780)):
            hatalar += K.yetim_kapisi(d0, rows, F, en_sinir)
        hatalar += K.qc(K.KART)
        bes = K.bes_renk(pal, F, etiket, posterler)
        kaydet_sinirli(bes, hedef / "BES_RENK.jpg", 800_000)
        for ad, fn in K.CIZ:
            im, kutular, yasak = fn(pal, F, etiket, posterler)
            hatalar += [f"{ad}: {x}" for x in K.kutu_kapisi(kutular, yasak)]
            kaydet_sinirli(im, hedef / KART_DOSYA[ad], 800_000)
        satir["olcum"] = olcum
        if hatalar:
            satir["sonuc"] = "KALDI"
            satir["not"] = " | ".join(hatalar[:3])
        kucuk = bes.copy()
        kucuk.thumbnail((380, 285), Image.LANCZOS)
        satir["kucuk"] = kucuk
        if yukle:
            rclone("copy", str(hedef), f"{yukle}/{cift}", "-q", "--transfers", "4")
    except Exception as ex:                                  # noqa: BLE001
        satir["sonuc"] = "HATA"
        satir["not"] = str(ex)[:160]
    finally:
        shutil.rmtree(ic, ignore_errors=True)
    satir["sure"] = round(time.time() - t, 1)
    return satir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip-uzak", required=True, help="gdrive:.../ZIP_FINAL")
    ap.add_argument("--kaynak-csv", required=True, help="GALERI_V1/GALERI_KAYNAK.csv (palet + ARIES_LEO id)")
    ap.add_argument("--crosslink", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rapor", required=True)
    ap.add_argument("--calisma", default="_work/galeri_final")
    ap.add_argument("--yukle", default="", help="gdrive:.../GALERI_FINAL")
    ap.add_argument("--is-parca", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out, rapor = Path(a.out), Path(a.rapor)
    out.mkdir(parents=True, exist_ok=True)
    rapor.mkdir(parents=True, exist_ok=True)
    Path(a.calisma).mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # palet: ARIES_LEO canli CRAFTED kartindan bir kez olculur (CDN, Etsy API cagrisi degil)
    kaynak = list(csv.DictReader(open(a.kaynak_csv, encoding="utf-8")))
    craft = next(r for r in kaynak if r["rol"] == "CRAFTED")
    pk = Path(a.calisma) / "palet.jpg"
    if not pk.exists():
        indir(craft["url"], pk)
    pal = palette(str(pk))
    print(f"palet (canli CRAFTED karti): {pal}", flush=True)
    al_id = {int(r["sira"]): r["listing_image_id"] for r in kaynak if r["tip"] == "gorsel"}
    al_video = next((r["listing_image_id"] for r in kaynak if r["tip"] == "video"), "")

    cl = json.loads(Path(a.crosslink).read_text(encoding="utf-8"))
    pod_id = {str(row[0]).upper(): str(row[1]) for row in (cl.get("rows") or [])}

    ciftler = sorted(x.strip("/") for x in rclone("lsf", a.zip_uzak, "--dirs-only").split() if x.strip())
    if a.limit:
        ciftler = ciftler[:a.limit]
    print(f"{len(ciftler)} cift islenecek | hedef {a.yukle or a.out}", flush=True)
    # Paralel isciler ayni uzak yolu ayni anda olusturursa Drive ayni adli iki
    # klasor yaratir (20 Eyl 2026 kosusu: iki GALERI_FINAL). Havuzdan once tek
    # seferde olustur.
    if a.yukle:
        rclone("mkdir", a.yukle)

    gorevler = [(c, a.zip_uzak, a.calisma, a.out, a.fonts, pal, a.yukle) for c in ciftler]
    satirlar, islenen, son = [], 0, time.time()
    with ThreadPoolExecutor(max_workers=a.is_parca) as ex:
        for s in ex.map(cift_isle, gorevler):
            satirlar.append(s)
            islenen += 1
            if time.time() - son >= 60 or islenen == len(gorevler):
                gecen = time.time() - t0
                kalan = gecen / max(1, islenen) * (len(gorevler) - islenen)
                kotu = sum(1 for x in satirlar if x["sonuc"] != "GECTI")
                print(f"   ETA {islenen}/{len(gorevler)} | gecen {gecen:.0f}s | kalan ~{kalan:.0f}s "
                      f"| %{100*islenen/len(gorevler):.1f} | gecmeyen {kotu}", flush=True)
                son = time.time()

    # ------------------------------------------------------------- GALERI_PLAN.csv
    with open(rapor / "GALERI_PLAN.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cift", "sira", "rol", "kaynak_tip", "kaynak", "pod_listing_id",
                    "pod_image_id", "drive_yolu"])
        for s in satirlar:
            c = s["cift"]
            for sira, rol, tip, kaynak_ad in PLAN:
                img_id = ""
                if tip == "POD" and c == "ARIES_LEO":
                    if rol == "VIDEO":
                        img_id = al_video
                    else:
                        m = re.search(r"galeri (\d+)", kaynak_ad)
                        if m:
                            img_id = al_id.get(int(m.group(1)), "")
                w.writerow([c, sira, rol, tip, kaynak_ad, pod_id.get(c, ""), img_id,
                            (f"TEMP/DIJITAL_78/GALERI_FINAL/{c}/{kaynak_ad}"
                             if tip == "URETILEN" else "")])

    # ------------------------------------------------------------- KONTROL_TABLOSU
    sut, kw, kh, bo = 13, 380, 285, 18
    iyi = [s for s in satirlar if s.get("kucuk") is not None]
    sat = (len(iyi) + sut - 1) // sut
    F = Fonts(a.fonts)
    sayfa = Image.new("RGB", (sut * (kw + bo) + bo, 120 + sat * (kh + 56) + bo), (250, 250, 248))
    d = ImageDraw.Draw(sayfa)
    d.text((bo, 40), f"DIJITAL GALERI - 5 COLORS KONTROL TABLOSU ({len(iyi)} cift)",
           font=F.f("sans", 40, 700), fill=(28, 38, 62))
    for i, s in enumerate(sorted(iyi, key=lambda x: x["cift"])):
        r_, c_ = divmod(i, sut)
        x, y = bo + c_ * (kw + bo), 120 + r_ * (kh + 56)
        sayfa.paste(s["kucuk"], (x, y))
        d.rectangle([x, y, x + kw - 1, y + kh - 1], outline=(205, 203, 197), width=2)
        d.text((x, y + kh + 8), s["cift"].replace("_", " + "), font=F.f("sans", 22, 600),
               fill=(40, 44, 58))
    q = kaydet_sinirli(sayfa, rapor / "KONTROL_TABLOSU.jpg", 3_000_000)
    print(f"KONTROL_TABLOSU.jpg {sayfa.size} q{q} "
          f"{(rapor/'KONTROL_TABLOSU.jpg').stat().st_size/1e6:.2f} MB", flush=True)

    kotu = [s for s in satirlar if s["sonuc"] != "GECTI"]
    with open(rapor / "GALERI_FINAL_QC.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cift", "sonuc", "sure", "not"], extrasaction="ignore")
        w.writeheader()
        for s in sorted(satirlar, key=lambda x: x["cift"]):
            w.writerow(s)
    print(f"BITTI | {len(satirlar)-len(kotu)}/{len(satirlar)} GECTI | sure {time.time()-t0:.0f}s",
          flush=True)
    for s in kotu[:10]:
        print(f"   KALDI {s['cift']}: {s['not']}", flush=True)


if __name__ == "__main__":
    main()
