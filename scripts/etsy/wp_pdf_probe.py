#!/usr/bin/env python3
"""
KURULUM PDF'I - EKSIK OLCUMU (SALT OKUR) - 4 Eyl 2026 Mo gorevi.

Hicbir yazma, uretim veya ZIP degisikligi yok. Uc soruyu olcer:

  1) PDF NEREDE      Drive agacinda (.pdf) ne var: ad, tarih, boyut, konum.
  2) ZIP ICERIGI     78 ciftin 4'er ZIP'i acilir, namelist cikarilir; kacinda
                     PDF var, kacinda yok; "4 wallpaper + LICENSE.txt" deseni
                     78'in tamaminda ayni mi.
  3) ILAN METNI      EN aciklama ve RU cevirisinde PDF vaadi geciyor mu;
                     hangi cumle, kac ilanda. (Yalniz GET.)

Cikti: tek tablo (cift basina) + ozet.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_mockup_common import DEVICES, EDITIONS  # noqa: E402

# docs/WP_LISTING_TEMPLATE.md sat. 49 (EN) ve 106 (RU): sablonun PDF vaadi.
VAAT = {
    "en": [re.compile(r"step-?by-?step setup guide", re.I),
           re.compile(r"setup guide", re.I),
           re.compile(r"\bPDF\b")],
    "ru": [re.compile(r"инструкц\w*\s+по\s+установке", re.I),
           re.compile(r"\bPDF\b")],
}
ZIP_DEVICES = [d for d in DEVICES]          # ZIP'e giren cihazlar (wp_zip ile ayni kume)


def cumleler(metin):
    return [c.strip() for c in re.split(r"[\r\n]+|(?<=[.!?])\s+", metin or "") if c.strip()]


def vaat_ara(metin, dil):
    """Eslesen kaliplari ve gectigi cumleleri dondurur."""
    hit, cum = [], []
    for rx in VAAT[dil]:
        if rx.search(metin or ""):
            hit.append(rx.pattern)
    if hit:
        for c in cumleler(metin):
            if any(rx.search(c) for rx in VAAT[dil]):
                cum.append(c[:200])
    return hit, cum


# ------------------------------------------------------------------ 1) PDF nerede
def pdf_tara(js_paths):
    log("=== 1) PDF NEREDE (Drive) ===")
    bulunan = []
    for etiket, p in js_paths:
        if not p or not Path(p).exists():
            log(f"  {etiket}: liste yok")
            continue
        try:
            kayitlar = json.loads(Path(p).read_text())
        except json.JSONDecodeError:
            log(f"  {etiket}: liste okunamadi")
            continue
        pdfs = [r for r in kayitlar
                if not r.get("IsDir") and str(r.get("Name", "")).lower().endswith(".pdf")]
        log(f"  {etiket}: {len(kayitlar)} dosya tarandi, {len(pdfs)} PDF")
        for r in pdfs:
            log(f"    {r.get('ModTime','')[:19]}  {r.get('Size'):>10}  {etiket}/{r.get('Path')}")
            bulunan.append((etiket, r.get("Path"), r.get("Size"), r.get("ModTime", "")[:19]))
    if not bulunan:
        log("  SONUC: taranan agaclarda HIC PDF YOK")
    return bulunan


# ------------------------------------------------------------------ 2) ZIP icerigi
def zip_tara(zip_dir, pairs):
    log("\n=== 2) ZIP ICERIGI (78 cift x 4 ZIP) ===")
    satirlar, desenler = [], collections.Counter()
    n_zip = n_pdf = n_eksik = 0
    for pair in pairs:
        up = pair.upper()
        row = dict(pair=pair, zip_adet=0, pdf_iceren=0, desen="")
        icerikler = []
        for ed in EDITIONS:
            p = Path(zip_dir) / up / f"AstroLove_{pair}_{ed}.zip"
            if not p.exists():
                n_eksik += 1
                icerikler.append(f"{ed}:YOK")
                continue
            n_zip += 1
            row["zip_adet"] += 1
            try:
                with zipfile.ZipFile(p) as zf:
                    names = sorted(zf.namelist())
            except zipfile.BadZipFile:
                icerikler.append(f"{ed}:BOZUK")
                continue
            if any(n.lower().endswith(".pdf") for n in names):
                row["pdf_iceren"] += 1
                n_pdf += 1
            sablon = sorted(n.replace(pair, "<CIFT>").replace(ed, "<EDISYON>") for n in names)
            icerikler.append(f"{ed}:{len(names)}")
            desenler["|".join(sablon)] += 1
        row["desen"] = "; ".join(icerikler)
        satirlar.append(row)
    log(f"  acilan ZIP: {n_zip}, eksik: {n_eksik}")
    log(f"  PDF iceren ZIP: {n_pdf}, PDF icermeyen: {n_zip - n_pdf}")
    log("  icerik desenleri (sablon -> kac ZIP):")
    for d, n in desenler.most_common():
        log(f"    {n:>4} x  {d}")
    return satirlar, dict(zip_acilan=n_zip, zip_eksik=n_eksik, zip_pdfli=n_pdf,
                          zip_pdfsiz=n_zip - n_pdf, desen_sayisi=len(desenler))


# ------------------------------------------------------------------ 3) ilan metni
def metin_tara(api, shop_id, rows, satirlar):
    log("\n=== 3) ILAN METNI (EN + RU, yalniz GET) ===")
    idx = {r["pair"]: r for r in satirlar}
    n_en = n_ru = 0
    ornek_en = ornek_ru = ""
    for i, (pair, lid) in enumerate(rows):
        lst = api.get(f"/listings/{lid}", ok404=True) or {}
        ru = api.get(f"/shops/{shop_id}/listings/{lid}/translations/ru", ok404=True) or {}
        h_en, c_en = vaat_ara(lst.get("description") or "", "en")
        h_ru, c_ru = vaat_ara(ru.get("description") or "", "ru")
        r = idx.setdefault(pair, dict(pair=pair))
        r["listing_id"] = lid
        r["en_pdf_vaadi"] = "VAR" if h_en else "yok"
        r["ru_pdf_vaadi"] = "VAR" if h_ru else "yok"
        r["en_cumle"] = " / ".join(c_en)[:300]
        r["ru_cumle"] = " / ".join(c_ru)[:300]
        n_en += bool(h_en); n_ru += bool(h_ru)
        if h_en and not ornek_en:
            ornek_en = " / ".join(c_en)
        if h_ru and not ornek_ru:
            ornek_ru = " / ".join(c_ru)
        if (i + 1) % 10 == 0 or i + 1 == len(rows):
            log(f"  [{i+1}/{len(rows)}] EN vaat {n_en}, RU vaat {n_ru}, kota {api.remaining}")
    log(f"  EN aciklamada PDF vaadi: {n_en}/{len(rows)} ilan")
    log(f"  RU aciklamada PDF vaadi: {n_ru}/{len(rows)} ilan")
    if ornek_en:
        log(f"  EN ornek cumle: {ornek_en[:240]}")
    if ornek_ru:
        log(f"  RU ornek cumle: {ornek_ru[:240]}")
    return dict(en_vaat=n_en, ru_vaat=n_ru, ilan=len(rows),
                en_ornek=ornek_en[:240], ru_ornek=ornek_ru[:240])


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.reader(fh):
            if len(r) >= 2 and r[1].strip().isdigit():
                rows.append((r[0].strip(), r[1].strip()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--zip-dir", required=True)
    ap.add_argument("--pdf-json", default="", help="etiket=yol,etiket=yol (rclone lsjson -R)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-etsy", action="store_true")
    a = ap.parse_args()

    js = []
    for item in a.pdf_json.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            js.append((k.strip(), v.strip()))
    pdfler = pdf_tara(js)

    rows = read_state(a.state)
    satirlar, zip_ozet = zip_tara(a.zip_dir, [p for p, _ in rows])

    metin_ozet = {}
    if not a.skip_etsy:
        keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
        mask(keystring); mask(shared)
        store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
        if store.needs_refresh():
            store.refresh()
        api = Etsy(store)
        metin_ozet = metin_tara(api, os.environ.get("ETSY_SHOP_ID", ""), rows, satirlar)

    cols = list(dict.fromkeys(k for r in satirlar for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in satirlar:
            w.writerow(r)
    log(f"\n{a.out}: {len(satirlar)} satir")

    lines = ["## kurulum PDF'i - tek tablo", "",
             "| soru | olcum |", "|---|---|",
             f"| PDF Drive'da uretilmis mi | {'EVET, ' + str(len(pdfler)) + ' dosya' if pdfler else 'HAYIR - taranan agaclarda hic PDF yok'} |",
             f"| acilan ZIP | {zip_ozet['zip_acilan']} (eksik {zip_ozet['zip_eksik']}) |",
             f"| PDF iceren ZIP | {zip_ozet['zip_pdfli']} |",
             f"| PDF icermeyen ZIP | {zip_ozet['zip_pdfsiz']} |",
             f"| farkli ZIP icerik deseni | {zip_ozet['desen_sayisi']} |"]
    if metin_ozet:
        lines += [f"| EN aciklamada PDF vaadi | {metin_ozet['en_vaat']}/{metin_ozet['ilan']} ilan |",
                  f"| RU aciklamada PDF vaadi | {metin_ozet['ru_vaat']}/{metin_ozet['ilan']} ilan |"]
        if metin_ozet.get("en_ornek"):
            lines += ["", f"EN cumle: `{metin_ozet['en_ornek']}`"]
        if metin_ozet.get("ru_ornek"):
            lines += ["", f"RU cumle: `{metin_ozet['ru_ornek']}`"]
    if pdfler:
        lines += ["", "### bulunan PDF dosyalari", "", "| agac | yol | boyut | tarih |", "|---|---|---|---|"]
        for t, yol, boyut, tarih in pdfler[:50]:
            lines.append(f"| {t} | {yol} | {boyut} | {tarih} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
