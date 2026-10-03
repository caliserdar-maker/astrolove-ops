#!/usr/bin/env python3
"""
DIJITAL 78 - GALERI KAYNAK ESLEMESI + ORNEK GALERI (Etsy SALT OKUR).

1) Canli POD ilaninin galerisi okunur (1 Etsy cagrisi: includes=Images,Videos).
2) Her gorsel indirilir, tesseract ile OCR edilir ve rolu belirlenir
   (kapak / oda / Symbol Story / Crafted / Paper & Quality / Size Guide /
   Shipping & Care / edisyon posteri).
3) "Crafted in Every Detail" kartinin metni CRAFTED_METIN.md'ye yazilir ve
   fiziksel vaat sozcukleri (paper, gsm, cotton, giclee, ink, archival, ...)
   taranir; eslesme varsa kart DIJITALDE KULLANILAMAZ isaretlenir.
4) Ciktilar: GALERI_KAYNAK.csv, CRAFTED_METIN.md, DIJITAL_KARTLAR_ORNEK.jpg,
   GALERI_DIZILIM.jpg (14 kutu, Etsy duzenleme ekrani sirasi).

Etsy'ye YAZMA YOKTUR.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pod"))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402
from dijital_kartlar import CIZ  # noqa: E402
from pod_gallery_sample import Fonts, palette  # noqa: E402

# rol -> (OCR anahtar kelimeleri, dijital karar)
ROL_ANAHTAR = [
    ("SYMBOL_STORY", ("symbol story",)),
    ("CRAFTED", ("crafted in every", "crafted in eve")),
    ("PAPER_QUALITY", ("paper & quality", "paper and quality", "hahnem", "gsm")),
    ("SIZE_GUIDE", ("size guide",)),
    ("SHIPPING_CARE", ("shipping & care", "shipping and care")),
]
DIJITAL_KARAR = {
    "KAPAK": "ETIKETLI SURUM (gorev 3)", "ODA": "AYNEN KULLANILIR",
    "SYMBOL_STORY": "AYNEN KULLANILIR", "CRAFTED": "OCR sonucuna gore",
    "PAPER_QUALITY": "DEGISTIRILIR -> WHAT'S INCLUDED", "SIZE_GUIDE": "DEGISTIRILIR -> PRINT SIZES",
    "SHIPPING_CARE": "DEGISTIRILIR -> HOW TO DOWNLOAD & PRINT",
    "EDISYON": "AYNEN KULLANILIR", "VIDEO": "AYNEN KULLANILIR (V11)", "BILINMIYOR": "ELLE BAKILIR",
}
# fiziksel vaat sozcukleri (dijital ilanda yanlis beklenti yaratir)
FIZIKSEL = re.compile(r"hahnem|giclee|giclée|\bgsm\b|cotton|acid[- ]free|archival|pigment|"
                      r"museum[- ]quality|\bink\b|\bpaper\b|canvas|framed?\b|shipping|ships?\b|"
                      r"deckle|matte\b|lustre|satin\b|\bmailer\b|\btube\b", re.I)
BILGI = re.compile(r"\bprint\b|\bprinted\b", re.I)
SUTUN = ["sira", "tip", "rol", "listing_image_id", "olcu", "url", "ocr_ozet", "dijital_karar"]
KUTU = ["1 KAPAK (etiketli)", "2 VIDEO (V11)", "3 ODA 1", "4 ODA 2", "5 SYMBOL STORY",
        "6 CRAFTED / INCLUDED", "7 WHAT'S INCLUDED", "8 PRINT SIZES", "9 HOW TO DOWNLOAD",
        "10 MIDNIGHT BLUE", "11 DEEP BLACK", "12 WARM PARCHMENT", "13 CHAMPAGNE IVORY",
        "14 PURE WHITE"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def indir(url, hedef):
    req = urllib.request.Request(url, headers={"User-Agent": "astrolove-ops/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(hedef, "wb") as fh:
        shutil.copyfileobj(r, fh)
    return Path(hedef).stat().st_size


def ocr(path):
    if not shutil.which("tesseract"):
        return None
    r = subprocess.run(["tesseract", str(path), "-", "--psm", "3"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return ""
    return r.stdout


def rol_bul(metin, sira, toplam):
    d = (metin or "").lower()
    for rol, anahtarlar in ROL_ANAHTAR:
        if any(k in d for k in anahtarlar):
            return rol
    if sira == 1:
        return "KAPAK"
    if sira in (2, 3):
        return "ODA"
    if sira > toplam - 5:
        return "EDISYON"
    return "BILINMIYOR"


def ozet(metin, n=90):
    t = " ".join((metin or "").split())
    return t[:n]


def kutu_ciz(sayfa, d, im, kutu, etiket, kaynak, F):
    x, y, w, h = kutu
    if im is not None:
        k = im.copy()
        k.thumbnail((w - 8, h - 8), Image.LANCZOS)
        sayfa.paste(k, (x + (w - k.width) // 2, y + (h - k.height) // 2))
    else:
        d.text((x + 16, y + h // 2), "(yok)", font=F.f('sans', 26, 400), fill=(150, 150, 150))
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=(200, 198, 192), width=2)
    d.text((x, y + h + 10), etiket, font=F.f('sans', 26, 600), fill=(30, 34, 46))
    d.text((x, y + h + 46), kaynak, font=F.f('sans', 24, 400), fill=(120, 120, 126))


def oynat_isareti(im):
    d = ImageDraw.Draw(im, "RGBA")
    r = int(min(im.size) * 0.13)
    cx, cy = im.width // 2, im.height // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 120), outline=(255, 255, 255, 230),
              width=max(2, r // 12))
    ok = int(r * 0.5)
    d.polygon([(cx - ok // 2, cy - ok), (cx - ok // 2, cy + ok), (cx + ok, cy)],
              fill=(255, 255, 255, 235))
    return im


def kaydet_sinirli(im, yol, sinir):
    for q in (95, 92, 88, 84, 80, 74):
        im.save(yol, "JPEG", quality=q, optimize=True, subsampling=0 if q >= 88 else 1)
        if yol.stat().st_size <= sinir:
            return q
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crosslink", required=True)
    ap.add_argument("--cift", default="ARIES_LEO")
    ap.add_argument("--out", required=True)
    ap.add_argument("--medya", default="_work/galeri_medya")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--palet-karti", default="", help="bos ise canli CRAFTED karti kullanilir")
    ap.add_argument("--kapak-etiketli", default="", help="etiketli kapak (gorev 3 cikti)")
    ap.add_argument("--kapak-uret", default="", help="etiket betigi; canli kapaktan 3 varyant uretir")
    ap.add_argument("--kapak-varyant", default="V2_ALT_BANT", help="dizilimde kullanilacak varyant")
    ap.add_argument("--video", default="", help="yerel V11 mp4 (kare 0 icin)")
    ap.add_argument("--max-calls", type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    medya = Path(a.medya); medya.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    cl = json.loads(Path(a.crosslink).read_text(encoding="utf-8"))
    pod_id = ""
    for row in cl.get("rows") or []:
        if str(row[0]).upper() == a.cift.upper():
            pod_id = str(row[1])
            break
    if not pod_id:
        raise SystemExit(f"HATA: {a.cift} icin POD ilan id bulunamadi")
    print(f"POD ilan: {pod_id} ({a.cift})", flush=True)

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ.get("TOKEN_FILE", "_work/ETSY_TOKEN.json"), k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    r = api.get(f"/listings/{pod_id}", params={"includes": "Images,Videos"}) or {}
    gorseller = r.get("images") or []
    videolar = r.get("videos") or []
    print(f"canli galeri: {len(gorseller)} gorsel + {len(videolar)} video "
          f"| Etsy cagrisi {api.calls}/{a.max_calls}", flush=True)

    satirlar, resim = [], {}
    son = time.time()
    for i, g in enumerate(gorseller, 1):
        url = g.get("url_fullxfull") or g.get("url_570xN") or ""
        yol = medya / f"{i:02d}.jpg"
        try:
            indir(url, yol)
            with Image.open(yol) as im:
                olcu = f"{im.width}x{im.height}"
                resim[i] = im.copy()
            metin = ocr(yol)
        except Exception as ex:                              # noqa: BLE001
            olcu, metin = "INDIRILEMEDI", f"HATA: {ex}"
        rol = rol_bul(metin, i, len(gorseller))
        satirlar.append({"sira": i, "tip": "gorsel", "rol": rol,
                         "listing_image_id": g.get("listing_image_id"), "olcu": olcu, "url": url,
                         "ocr_ozet": ozet(metin), "dijital_karar": DIJITAL_KARAR[rol]})
        (medya / f"{i:02d}.txt").write_text(metin or "", encoding="utf-8")
        if time.time() - son >= 60:
            print(f"   ETA {i}/{len(gorseller)} | gecen {time.time()-t0:.0f}s", flush=True)
            son = time.time()

    kare0 = None
    if videolar:
        vurl = videolar[0].get("video_url") or ""
        satirlar.append({"sira": 0, "tip": "video", "rol": "VIDEO",
                         "listing_image_id": videolar[0].get("video_id"),
                         "olcu": "", "url": vurl, "ocr_ozet": "",
                         "dijital_karar": DIJITAL_KARAR["VIDEO"]})
    vyol = Path(a.video) if a.video and Path(a.video).exists() else None
    if not vyol and videolar and (videolar[0].get("video_url") or ""):
        try:
            vyol = medya / "video.mp4"
            indir(videolar[0]["video_url"], vyol)
        except Exception as ex:                              # noqa: BLE001
            print(f"   video indirilemedi: {str(ex)[:80]}", flush=True)
            vyol = None
    if vyol and shutil.which("ffmpeg"):
        kp = medya / "video_kare0.jpg"
        subprocess.run(["ffmpeg", "-y", "-i", str(vyol), "-frames:v", "1", "-q:v", "2", str(kp)],
                       capture_output=True, timeout=600)
        if kp.exists():
            kare0 = oynat_isareti(Image.open(kp).convert("RGB"))

    # ------------------------------------------------- etiketli kapak (canli POD kapagindan)
    if a.kapak_uret and 1 in resim:
        r2 = subprocess.run([sys.executable, a.kapak_uret, "--kapak", str(medya / "01.jpg"),
                             "--fonts", a.fonts, "--out", str(out)],
                            capture_output=True, text=True, timeout=1200)
        print((r2.stdout or "").strip()[-600:], flush=True)
        if r2.returncode != 0:
            print(f"   kapak etiketi HATA: {(r2.stderr or '')[-300:]}", flush=True)
        elif not a.kapak_etiketli:
            a.kapak_etiketli = str(out / f"KAPAK_{a.kapak_varyant}.jpg")

    # ------------------------------------------------------------ CRAFTED_METIN.md
    craft = next((x for x in satirlar if x["rol"] == "CRAFTED"), None)
    md = [f"# CRAFTED IN EVERY DETAIL - KART METNI ({simdi()} UTC)", "",
          f"Kaynak: canli POD ilani {pod_id} ({a.cift}), galeri sirasi "
          f"{craft['sira'] if craft else '-'}.", ""]
    if craft:
        ham = (medya / f"{craft['sira']:02d}.txt").read_text(encoding="utf-8")
        satir_metin = [x.strip() for x in ham.splitlines() if x.strip()]
        fiz = sorted({m.group(0).lower() for m in FIZIKSEL.finditer(ham)})
        bilgi = sorted({m.group(0).lower() for m in BILGI.finditer(ham)})
        md += ["## Karttaki metin (OCR)", ""] + [f"- {x}" for x in satir_metin]
        md += ["", "## Fiziksel vaat taramasi", "",
               f"- Taranan sozcukler: kagit/gsm/pamuk/giclee/murekkep/arsiv/muze/canvas/cerceve/kargo",
               f"- **Eslesme: {', '.join(fiz) if fiz else 'YOK'}**",
               f"- Bilgi amacli (fiziksel vaat degil): {', '.join(bilgi) if bilgi else 'yok'}", "",
               "## Karar", ""]
        md += ([f"- **KULLANILAMAZ**: kart fiziksel vaat iceriyor ({', '.join(fiz)}). "
                f"Yerine WHAT'S INCLUDED konur."] if fiz else
               ["- **KULLANILABILIR**: kart yalniz cizim/detay anlatir, fiziksel vaat yoktur.",
                "- Dijital galeride 6. sirada aynen kalir."])
        craft["dijital_karar"] = "KULLANILAMAZ -> WHAT'S INCLUDED" if fiz else "AYNEN KULLANILIR"
    else:
        md += ["- Kart bulunamadi (OCR eslesmedi). Elle bakilmali."]
    (out / "CRAFTED_METIN.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ 3 yeni kart
    palet_yol = a.palet_karti
    if not palet_yol:
        kaynak = craft or next((x for x in satirlar if x["rol"] == "SYMBOL_STORY"), None)
        if not kaynak:
            raise SystemExit("HATA: palet icin kart bulunamadi (--palet-karti verin)")
        palet_yol = str(medya / f"{kaynak['sira']:02d}.jpg")
    print(f"palet kaynagi: {palet_yol}", flush=True)
    pal = palette(palet_yol)
    F = Fonts(a.fonts)
    a1, b1 = a.cift.split("_")[0], a.cift.split("_")[-1]
    pair_txt = f"{a1} • {b1}"
    edisyon_sira = [x for x in satirlar if x["rol"] == "EDISYON"]
    posterler = [resim[x["sira"]] for x in edisyon_sira if x["sira"] in resim]
    kartlar = []
    for ad, fn in CIZ:
        im = fn(pal, F, pair_txt, posterler)
        p = out / f"{ad}_{a.cift}.jpg"
        im.save(p, "JPEG", quality=95, optimize=True, subsampling=0)
        kartlar.append(im)
        print(f"  {p.name} {im.size} {p.stat().st_size/1e3:.0f} KB", flush=True)

    kw, kh, bosluk = 1000, 750, 40
    sayfa = Image.new("RGB", (3 * kw + 4 * bosluk, kh + 2 * bosluk + 90), (250, 250, 248))
    d = ImageDraw.Draw(sayfa)
    for i, (im, ad) in enumerate(zip(kartlar, ["WHAT'S INCLUDED", "PRINT SIZES",
                                               "HOW TO DOWNLOAD & PRINT"])):
        x = bosluk + i * (kw + bosluk)
        sayfa.paste(im.resize((kw, kh), Image.LANCZOS), (x, bosluk))
        d.rectangle([x, bosluk, x + kw - 1, bosluk + kh - 1], outline=(210, 208, 202), width=2)
        d.text((x, bosluk + kh + 16), f"{7+i}. {ad}", font=F.f('sans', 30, 600), fill=(30, 34, 46))
    q = kaydet_sinirli(sayfa, out / "DIJITAL_KARTLAR_ORNEK.jpg", 800_000)
    print(f"DIJITAL_KARTLAR_ORNEK.jpg {sayfa.size} q{q} "
          f"{(out/'DIJITAL_KARTLAR_ORNEK.jpg').stat().st_size/1e3:.0f} KB", flush=True)

    # ------------------------------------------------------------ 14 kutuluk dizilim
    oda = [x["sira"] for x in satirlar if x["rol"] == "ODA"][:2]
    symbol = next((x["sira"] for x in satirlar if x["rol"] == "SYMBOL_STORY"), None)
    craft_sira = craft["sira"] if craft else None
    craft_kullan = bool(craft) and craft["dijital_karar"] == "AYNEN KULLANILIR"
    kapak_im = (Image.open(a.kapak_etiketli).convert("RGB")
                if a.kapak_etiketli and Path(a.kapak_etiketli).exists() else resim.get(1))
    kutular = [
        (kapak_im, "POD kapak + etiket" if a.kapak_etiketli else "POD kapagi (etiketsiz)"),
        (kare0, "V11 video, kare 0"),
        (resim.get(oda[0]) if len(oda) > 0 else None, f"POD gorsel {oda[0] if oda else '-'}"),
        (resim.get(oda[1]) if len(oda) > 1 else None, f"POD gorsel {oda[1] if len(oda) > 1 else '-'}"),
        (resim.get(symbol), f"POD gorsel {symbol}"),
        (resim.get(craft_sira) if craft_kullan else kartlar[0],
         f"POD gorsel {craft_sira}" if craft_kullan else "YENI kart (Crafted uygun degil)"),
        (kartlar[0], "YENI kart"), (kartlar[1], "YENI kart"), (kartlar[2], "YENI kart"),
    ]
    for j in range(5):
        sr = edisyon_sira[j]["sira"] if j < len(edisyon_sira) else None
        kutular.append((resim.get(sr), f"POD gorsel {sr}" if sr else "-"))

    kw2, kh2, bo = 380, 380, 34
    sut, sat = 5, 3
    sayfa2 = Image.new("RGB", (sut * kw2 + (sut + 1) * bo, 130 + sat * (kh2 + 100) + bo),
                       (250, 250, 248))
    d2 = ImageDraw.Draw(sayfa2)
    d2.text((bo, 34), f"DIJITAL GALERI DIZILIMI - {a.cift.replace('_', ' + ')} "
            f"(Etsy duzenleme ekrani sirasi)", font=F.f('sans', 34, 700), fill=(28, 38, 62))
    d2.text((bo, 82), "POD galerisinden aynen alinanlar 'POD' etiketlidir; 'YENI' olanlar bu "
            "oturumda uretildi.", font=F.f('sans', 26, 400), fill=(110, 110, 116))
    for i, (im, kaynak) in enumerate(kutular):
        r_, c_ = divmod(i, sut)
        x = bo + c_ * (kw2 + bo)
        y = 130 + r_ * (kh2 + 100)
        kutu_ciz(sayfa2, d2, im, (x, y, kw2, kh2), KUTU[i], kaynak, F)
    q2 = kaydet_sinirli(sayfa2, out / "GALERI_DIZILIM.jpg", 800_000)
    print(f"GALERI_DIZILIM.jpg {sayfa2.size} q{q2} "
          f"{(out/'GALERI_DIZILIM.jpg').stat().st_size/1e3:.0f} KB", flush=True)

    with open(out / "GALERI_KAYNAK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)
    print(f"BITTI | Etsy cagrisi {api.calls} | sure {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
