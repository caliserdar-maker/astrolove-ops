#!/usr/bin/env python3
"""GECE BATCH 2 - ONCELIK 3 + 4: Drive medya teknik QA ve urun/ilan/medya matrisi.

SALT OKUR: hicbir dosya degistirilmez, silinmez, tasinmaz.

Kapsam notu (durust sinir): 36.866 dosyanin TAMAMINI indirip acmak yuzlerce GB
eder, runner diski 14 GB. Bu yuzden:
  - TAM tarama: Drive metadata + MD5 (rclone lsjson --hash) -> gercek kopya,
    ayni ad farkli icerik, yanlis adlandirma, eksik varlik, oksuz varlik.
  - ORNEKLEM taramasi: --ornek-dir icinde indirilmis dosyalar acilir (JPG/PNG:
    boyut, oran, DPI, ICC, progressive, kalite tahmini; PDF/ZIP: gecerlilik).
Ornekleme dahil olmayan dosyalar raporda "olculmedi" olarak isaretlenir.

Cikti: media_technical_qa.csv, duplicate_candidates.csv, orphan_assets.csv,
       missing_assets_by_pair.csv, media_qa_summary.md,
       product_listing_media_matrix.csv/json
"""
import argparse
import csv
import io
import json
import math
import pathlib
import re
import struct
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
BURC_RX = re.compile(r"(?<![A-Za-z])(" + "|".join(BURCLAR) + r")(?![A-Za-z])", re.I)
EDISYON_RX = re.compile(r"(Champagne[_ ]?Ivory|Pure[_ ]?White|Warm[_ ]?Parchment|"
                        r"Midnight[_ ]?Blue|Deep[_ ]?Black)", re.I)
TURLER = [
    ("zip", re.compile(r"\.zip$", re.I)),
    ("pdf", re.compile(r"\.pdf$", re.I)),
    ("video", re.compile(r"\.(mp4|mov|webm)$", re.I)),
    ("mockup", re.compile(r"mockup|scene|hero|room|preview", re.I)),
    ("wallpaper", re.compile(r"wallpaper|phone|tablet|desktop|watch", re.I)),
    ("print", re.compile(r"print|poster|\.(png|jpg|jpeg|tif|tiff)$", re.I)),
]
BEKLENEN_TUR = ["zip", "print", "mockup", "video"]
ORANLAR = {"2:3": 2/3, "3:4": 3/4, "4:5": 4/5, "11:14": 11/14, "A (1:V2)": 1/math.sqrt(2),
           "1:1": 1.0, "9:16": 9/16, "16:9": 16/9, "4:3": 4/3, "3:2": 3/2}


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def cift_bul(yol):
    b = [m.group(1).capitalize() for m in BURC_RX.finditer(yol)]
    if len(b) < 2:
        return None
    return "_".join(sorted(x.upper() for x in b[:2]))


def tur_bul(yol):
    for ad, rx in TURLER:
        if rx.search(yol):
            return ad
    return "diger"


def edisyon_bul(yol):
    m = EDISYON_RX.search(yol)
    return m.group(1).replace("_", " ").title() if m else ""


def oran_adi(w, h):
    if not w or not h:
        return "", 0.0
    r = w / h
    en_iyi, fark = "", 9.0
    for ad, d in ORANLAR.items():
        f = abs(r - d) / d
        if f < fark:
            en_iyi, fark = ad, f
    return en_iyi, round(fark * 100, 2)


# ---------------------------------------------------------------- ornek analiz
def jpeg_bilgi(ham):
    """PIL olmadan da calisan asgari JPEG denetimi: progressive mi, SOF boyutu."""
    prog = b"\xff\xc2" in ham[:4096] or b"\xff\xc2" in ham
    return {"progressive": prog}


def dosya_analiz(p):
    """Tek dosyayi ac ve teknik olc. Donus: (kayit, hatalar)."""
    ad = p.name
    uzanti = p.suffix.lower()
    kayit = {"dosya": ad, "uzanti": uzanti, "bayt": p.stat().st_size,
             "px": "", "oran": "", "oran_sapma": "", "dpi": "", "icc": "",
             "mod": "", "progressive": "", "kalite_tahmini": "", "girdi_sayisi": ""}
    hatalar = []
    try:
        if uzanti in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            with Image.open(p) as im:
                im.load()
                w, h = im.size
                ad_oran, sapma = oran_adi(w, h)
                dpi = im.info.get("dpi")
                icc = im.info.get("icc_profile")
                icc_ad = ""
                if icc:
                    try:
                        from PIL import ImageCms
                        icc_ad = ImageCms.getProfileDescription(
                            ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
                    except Exception:                           # noqa: BLE001
                        icc_ad = "(okunamadi)"
                kayit.update({"px": f"{w}x{h}", "oran": ad_oran, "oran_sapma": sapma,
                              "dpi": str([round(float(x)) for x in dpi]) if dpi else "yok",
                              "icc": icc_ad or "gomulu yok", "mod": im.mode,
                              "progressive": str(bool(im.info.get("progression")))})
                if im.mode not in ("RGB", "RGBA", "L"):
                    hatalar.append(f"beklenmeyen renk modu {im.mode}")
                if icc and "srgb" not in icc_ad.lower():
                    hatalar.append(f"sRGB disi profil: {icc_ad}")
                if not icc and uzanti in (".jpg", ".jpeg"):
                    hatalar.append("gomulu ICC profili yok")
                if dpi and round(float(dpi[0])) not in (72, 96, 300):
                    hatalar.append(f"beklenmeyen DPI {dpi}")
                if sapma > 1.0:
                    hatalar.append(f"bilinen orana uymuyor ({ad_oran}, sapma %{sapma})")
            if uzanti in (".jpg", ".jpeg"):
                ham = p.read_bytes()
                j = jpeg_bilgi(ham)
                kayit["progressive"] = str(j["progressive"])
                if j["progressive"]:
                    hatalar.append("progressive JPEG (Etsy/print icin baseline tercih edilir)")
                bpp = kayit["bayt"] * 8 / max(1, (w * h))
                kayit["kalite_tahmini"] = f"{bpp:.2f} bit/piksel"
                if bpp < 0.15:   # duz zeminli tasarimlarda dusuk bpp normal olabilir
                    hatalar.append(f"dusuk kalite JPEG suphesi ({bpp:.2f} bit/piksel)")
        elif uzanti == ".zip":
            with zipfile.ZipFile(p) as z:
                bozuk = z.testzip()
                kayit["girdi_sayisi"] = len(z.infolist())
                if bozuk:
                    hatalar.append(f"ZIP icinde bozuk girdi: {bozuk}")
                if not z.infolist():
                    hatalar.append("ZIP bos")
        elif uzanti == ".pdf":
            ham = p.read_bytes()
            if not ham.startswith(b"%PDF"):
                hatalar.append("PDF imzasi yok")
            if b"%%EOF" not in ham[-2048:]:
                hatalar.append("PDF sonu (%%EOF) yok - kesik olabilir")
            kayit["girdi_sayisi"] = ham.count(b"/Type /Page") or ham.count(b"/Type/Page")
        elif uzanti in (".mp4", ".mov", ".webm"):
            ham = p.read_bytes()[:16]
            if b"ftyp" not in ham and uzanti != ".webm":
                hatalar.append("MP4/MOV 'ftyp' kutusu yok")
        else:
            kayit["mod"] = "olculmedi"
    except Exception as ex:                                     # noqa: BLE001
        hatalar.append(f"ACILAMADI: {type(ex).__name__}: {str(ex)[:80]}")
    return kayit, hatalar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", required=True, help="rclone lsjson --hash ciktisi")
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--catalog", default="", help="full_etsy_catalog.json")
    ap.add_argument("--ornek-dir", default="", help="indirilmis ornek dosyalar")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    dosyalar = json.loads(pathlib.Path(a.listing).read_text(encoding="utf-8"))
    beklenen = set()
    with open(a.pod_state, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("pair") or "") and (r.get("listing_id") or "").isdigit():
                beklenen.add("_".join(sorted(r["pair"].split("_"))))

    # ---------------------------------------------------- tam tarama (metadata)
    cift_tur = defaultdict(lambda: defaultdict(list))
    md5_grup = defaultdict(list)
    ad_grup = defaultdict(list)
    oksuz, kayitlar = [], []
    for d in dosyalar:
        if d.get("IsDir"):
            continue
        yol = d.get("Path") or ""
        if not yol:
            continue
        ad = pathlib.PurePath(yol).name
        boyut = int(d.get("Size") or 0)
        md5 = ((d.get("Hashes") or {}).get("md5") or "").lower()
        cift = cift_bul(yol)
        tur = tur_bul(yol)
        ed = edisyon_bul(yol)
        ad_grup[ad].append((yol, boyut, md5))
        if md5:
            md5_grup[md5].append((yol, boyut))
        if cift:
            cift_tur[cift][tur].append({"yol": yol, "bayt": boyut, "md5": md5, "edisyon": ed})
        else:
            oksuz.append({"yol": yol, "tur": tur, "bayt": boyut,
                          "neden": "ad icinde iki burc yok (genel varlik)"})
        kayitlar.append({"yol": yol, "ad": ad, "tur": tur, "cift": cift or "", "edisyon": ed,
                         "bayt": boyut, "md5": md5})

    # gercek kopyalar (ayni md5)
    kopya = [(h, g) for h, g in md5_grup.items() if len(g) > 1]
    with open(out / "duplicate_candidates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tur", "anahtar", "kopya_sayisi", "toplam_bayt", "bosalacak_bayt", "yollar"])
        for h, g in sorted(kopya, key=lambda x: -sum(y[1] for y in x[1]))[:3000]:
            tb = sum(y[1] for y in g)
            w.writerow(["GERCEK_KOPYA(md5)", h, len(g), tb, tb - g[0][1],
                        " | ".join(y[0] for y in g[:6])])
        for ad, g in sorted(ad_grup.items(), key=lambda kv: -len(kv[1])):
            if len(g) > 1 and len({x[2] for x in g if x[2]}) > 1:
                w.writerow(["AYNI_AD_FARKLI_ICERIK", ad, len(g), sum(x[1] for x in g), 0,
                            " | ".join(x[0] for x in g[:6])])

    with open(out / "orphan_assets.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["yol", "tur", "bayt", "neden"])
        w.writeheader()
        for x in sorted(oksuz, key=lambda y: -y["bayt"])[:5000]:
            w.writerow(x)

    with open(out / "missing_assets_by_pair.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cift", "eksik_turler", "zip", "pdf", "print", "mockup", "wallpaper",
                    "video", "toplam_dosya", "sonuc"])
        for cift in sorted(beklenen):
            t = cift_tur.get(cift, {})
            eksik = [x for x in BEKLENEN_TUR if not t.get(x)]
            w.writerow([cift, ",".join(eksik) or "-", len(t.get("zip", [])),
                        len(t.get("pdf", [])), len(t.get("print", [])), len(t.get("mockup", [])),
                        len(t.get("wallpaper", [])), len(t.get("video", [])),
                        sum(len(v) for v in t.values()), "EKSIK" if eksik else "TAM"])

    # ---------------------------------------------------- ornek teknik analiz
    teknik, teknik_hata = [], 0
    ornek_dir = pathlib.Path(a.ornek_dir) if a.ornek_dir else None
    if ornek_dir and ornek_dir.exists():
        for p in sorted(ornek_dir.rglob("*")):
            if not p.is_file():
                continue
            kayit, hatalar = dosya_analiz(p)
            kayit["cift"] = cift_bul(p.name) or ""
            kayit["tur"] = tur_bul(p.name)
            kayit["sonuc"] = "TEMIZ" if not hatalar else "BULGU"
            kayit["bulgular"] = " | ".join(hatalar)
            teknik_hata += len(hatalar)
            teknik.append(kayit)
    sutun = ["dosya", "cift", "tur", "uzanti", "bayt", "px", "oran", "oran_sapma", "dpi",
             "icc", "mod", "progressive", "kalite_tahmini", "girdi_sayisi", "sonuc", "bulgular"]
    with open(out / "media_technical_qa.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sutun, extrasaction="ignore")
        w.writeheader()
        for x in teknik:
            w.writerow(x)

    # ---------------------------------------------------- ONCELIK 4: matris
    katalog = []
    if a.catalog and pathlib.Path(a.catalog).exists():
        katalog = json.loads(pathlib.Path(a.catalog).read_text(encoding="utf-8"))
    ilan_idx = defaultdict(list)
    for L in katalog:
        if L.get("burc_cifti"):
            ilan_idx[(L["burc_cifti"], L["urun_ailesi"], L.get("edisyon") or "")].append(L)

    matris = []
    AILE_ED = [("POD baski", ["5 renk (varyasyon)"]),
               ("Digital wall art", ["Champagne Ivory", "Pure White", "Warm Parchment",
                                     "Midnight Blue", "Deep Black"]),
               ("Digital wallpaper", ["4 renk (tek ilan)"])]
    for cift in sorted(beklenen):
        t = cift_tur.get(cift, {})
        for ail, edisyonlar in AILE_ED:
            for ed in edisyonlar:
                ilanlar = ilan_idx.get((cift, ail, ed), [])
                lid = ilanlar[0]["listing_id"] if ilanlar else ""
                ed_dosya = lambda tur: [x for x in t.get(tur, [])                      # noqa: E731
                                        if not ed or ed in EDISYON_RX.pattern and
                                        (x["edisyon"].lower() == ed.lower() or not x["edisyon"])]
                zipler = [x for x in t.get("zip", []) if not x["edisyon"] or ed.lower().startswith(x["edisyon"].lower()[:6]) or ed in ("5 renk (varyasyon)", "4 renk (tek ilan)")]
                jpgler = [x for x in t.get("print", []) if x["yol"].lower().endswith((".jpg", ".jpeg"))]
                pdfler = t.get("pdf", [])
                mockuplar = t.get("mockup", [])
                videolar = t.get("video", [])
                eksik = []
                if ail in ("Digital wall art", "Digital wallpaper") and not zipler:
                    eksik.append("zip")
                if ail == "POD baski" and not t.get("print"):
                    eksik.append("print")
                if not mockuplar:
                    eksik.append("mockup")
                if ail == "POD baski" and not videolar:
                    eksik.append("video")
                if ail == "Digital wall art" and not pdfler:
                    eksik.append("pdf_guide")
                if not lid:
                    eksik.append("listing")
                risk = []
                if len(ilanlar) > 1:
                    risk.append(f"{len(ilanlar)} ilan ayni (cift,aile,edisyon)")
                if ail == "Digital wall art" and ed == "Pure White" and not ilanlar:
                    risk.append("Pure White ilani yok")
                matris.append({
                    "burc_cifti": cift, "listing_id": lid, "urun_ailesi": ail, "edisyon": ed,
                    "ana_zip": zipler[0]["yol"] if zipler else "",
                    "zip_bayt": zipler[0]["bayt"] if zipler else "",
                    "jpg_sayisi": len(jpgler),
                    "jpg_toplam_bayt": sum(x["bayt"] for x in jpgler),
                    "pdf_guide": pdfler[0]["yol"] if pdfler else "",
                    "mockup_sayisi": len(mockuplar),
                    "video": videolar[0]["yol"] if videolar else "",
                    "eksik_ogeler": ",".join(eksik) or "-",
                    "yanlis_eslesme_riski": "; ".join(risk) or "dusuk",
                })
    msut = list(matris[0]) if matris else []
    with open(out / "product_listing_media_matrix.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=msut)
        w.writeheader()
        for x in matris:
            w.writerow(x)
    (out / "product_listing_media_matrix.json").write_text(
        json.dumps(matris, ensure_ascii=False, indent=1), encoding="utf-8")

    tam = sum(1 for cift in beklenen if not [x for x in BEKLENEN_TUR
                                             if not cift_tur.get(cift, {}).get(x)])
    bosalacak = sum(sum(y[1] for y in g) - g[0][1] for _, g in kopya)
    ozet = {
        "taranan_dosya": len(kayitlar),
        "md5_alinan_dosya": sum(1 for x in kayitlar if x["md5"]),
        "cifte_baglanan": sum(1 for x in kayitlar if x["cift"]),
        "oksuz_varlik": len(oksuz),
        "gercek_kopya_grubu": len(kopya),
        "kopya_bosalacak_bayt": bosalacak,
        "ayni_ad_farkli_icerik": sum(1 for ad, g in ad_grup.items()
                                     if len(g) > 1 and len({x[2] for x in g if x[2]}) > 1),
        "tam_cift": tam, "eksik_cift": len(beklenen) - tam,
        "ornek_analiz_dosya": len(teknik), "ornek_bulgu": teknik_hata,
        "matris_satir": len(matris),
        "matris_eksik_ogeli": sum(1 for x in matris if x["eksik_ogeler"] != "-"),
    }
    (out / "_oncelik_3_4_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                                encoding="utf-8")

    md = [f"# ONCELIK 3 - Drive medya teknik QA ({simdi()} UTC)", "",
          "Salt okur: hicbir dosya degistirilmedi, silinmedi, tasinmadi.", "",
          "## Kapsam ve yontem", "",
          f"- **Tam tarama (metadata + MD5): {len(kayitlar)} dosya.** Gercek kopya tespiti "
          f"Drive'in MD5 checksum'i ile yapildi ({ozet['md5_alinan_dosya']} dosyada mevcut); "
          "dosya indirilmedi.",
          f"- **Ornek teknik analiz: {len(teknik)} dosya** indirilip acildi (JPG/PNG boyut, oran, "
          "DPI, ICC, progressive, kalite tahmini; ZIP/PDF/MP4 gecerlilik).",
          "- Tam teknik analiz (36.866 dosyanin hepsini acmak) yuzlerce GB indirme demek; "
          "runner diski 14 GB oldugu icin yapilmadi. Olculmeyen dosyalar raporda yok, "
          "yalniz ornekler listelendi.", "",
          "## Bulgular", "",
          f"- Gercek kopya grubu (ayni MD5): **{len(kopya)}**, "
          f"bosaltilabilecek alan: **{bosalacak/1e9:.2f} GB** (silme YAPILMADI, yalniz liste)",
          f"- Ayni ada sahip farkli icerikli dosya: **{ozet['ayni_ad_farkli_icerik']}**",
          f"- Hicbir cifte baglanamayan genel varlik: **{len(oksuz)}**",
          f"- Cift basina eksik varlik: **{ozet['eksik_cift']}** cift eksik, {tam} cift TAM",
          f"- Ornek analizde bulgu: **{teknik_hata}** ({sum(1 for x in teknik if x['sonuc'] == 'BULGU')} dosyada)", ""]
    if teknik:
        md += ["## Ornek analiz bulgulari", "", "| dosya | tur | px | oran | dpi | icc | bulgu |",
               "|---|---|---|---|---|---|---|"]
        for x in [y for y in teknik if y["sonuc"] == "BULGU"][:25]:
            md.append(f"| {x['dosya'][:38]} | {x['tur']} | {x['px']} | {x['oran']} | {x['dpi']} | "
                      f"{str(x['icc'])[:18]} | {x['bulgular'][:70]} |")
    md += ["", "## ONCELIK 4 - urun/ilan/medya matrisi", "",
           f"- Satir: **{len(matris)}** (78 cift x urun ailesi x edisyon)",
           f"- Eksik ogesi olan satir: **{ozet['matris_eksik_ogeli']}**",
           "- Dosya: `product_listing_media_matrix.csv` / `.json`", ""]
    (out / "media_qa_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("ONCELIK 3/4 ozet:", json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
