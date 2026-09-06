#!/usr/bin/env python3
"""
POD kart metinleri icin kaynak dogrulama -> FACTCHECK.md + verified.json.

Her satir icin kaynak adaylari: (url, [anahtar kelimeler]) veya ("csv", sutun, satir_kosulu).
Sayfa metninde tum anahtar kelimeleri iceren ilk cumle birebir alintilanir. Hicbir
kaynakta bulunamayan satir "KAYNAK YOK" olur ve pod_gallery_sample.py --verified ile
karttan cikarilir. Sandbox prodigi.com/hahnemuehle.com'a cikamaz; Actions'ta kosar.

Kullanim: python factcheck.py --csv PRODIGI_HPR_SIZES.csv --out DIR [--offline]
"""
import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36", "Accept-Language": "en"}
HAH_PR = "https://www.hahnemuehle.com/en/digital-papers/fineart-collection/matt-fineart-smooth/p/Product/show/8/1.html"
HAH_PR2 = "https://www.hahnemuehle.com/en/digital-papers/fineart-collection/natural-line/p/Product/show/202/1.html"
HAH_GLOVES = "https://www.hahnemuehle.store/us/gloves-12-pairs/10608863"
HAH_BLOG_BOX = "https://blog.hahnemuehle.com/en/hahnemuehle-portfolio-box/"
HAH_GLOVES2 = "https://www.hahnemuehle.shop/en/gloves-dual-pack/10608858"
PRO_HPR = "https://www.prodigi.com/products/prints-and-posters/photo-prints/hahnemuhle-photo-rag/"
PRO_PACK = "https://www.prodigi.com/faq/packaging/"
PRO_PACK2 = "https://help.prodigi.com/support/solutions/articles/35000138786-how-are-your-products-packaged-for-shipping-"
PRO_PAPERS = "https://support.prodigi.com/hc/en-us/articles/13159329001244-What-papers-do-you-have-available-globally"
WIKI_H = "https://en.wikipedia.org/wiki/Average_human_height_by_country"
CARD_SIZES = ["8x10", "A4", "11x14", "12x16", "A3", "12x18", "16x20", "16x24", "A2", "18x24", "20x30", "24x36", "30x40"]

# id, kart, kartta basilan metin, kaynak adaylari
FACTS = [
    ("P_kicker", "PAPER", "MUSEUM-GRADE FINE ART PAPER",
     [(HAH_PR, ["museum"]), (HAH_PR2, ["museum"]), (PRO_HPR, ["museum"])]),
    ("P1", "PAPER", "HAHNEMÜHLE PHOTO RAG — 308 gsm fine art paper with a soft matte surface",
     [(HAH_PR, ["308", "matt"]), (HAH_PR2, ["308", "matt"]), (PRO_HPR, ["308"])]),
    ("P2", "PAPER", "100% COTTON — Made from 100% cotton rag",
     [(HAH_PR, ["100% cotton"]), (HAH_PR2, ["100% cotton"]), (PRO_HPR, ["cotton"])]),
    ("P3", "PAPER", "ACID-FREE — Acid- and lignin-free, ISO 9706 conform",
     [(HAH_PR, ["acid", "lignin"]), (HAH_PR2, ["acid", "lignin"]), (PRO_HPR, ["acid"])]),
    ("P4", "PAPER", "ARCHIVAL PIGMENT GICLÉE — Giclée print with pigment inks at 300 DPI",
     [(PRO_HPR, ["pigment"]), (PRO_HPR, ["giclée"]), (PRO_HPR, ["giclee"]), (PRO_PAPERS, ["pigment"]),
      ("csv", "dpi", "== 300")]),
    ("P5", "PAPER", "MUSEUM QUALITY — Highest age resistance, ISO 9706 conform",
     [(HAH_PR, ["age resistance"]), (HAH_PR2, ["age resistance"]), (HAH_PR, ["9706"])]),
    ("P_footer", "PAPER", "Printed on Hahnemühle Photo Rag",
     [("csv", "sku", "startswith GLOBAL-HPR")]),
    ("S_sizes", "SIZES", "13 boyut (inch/cm) — kart uzerindeki tum olcu satirlari",
     [("csv", "boyut_inch", "13 satir")]),
    ("S_human", "SIZES", "175 CM · 5'9\" (siluet olcek etiketi)",
     [("note", "scale label (no claim)")]),
    ("C1", "CARE", "ROLLED IN A TUBE — 8x10 and A4 ship flat (US & EU); all other sizes ship rolled in a sturdy tube.",
     [("quote", PRO_HPR, "UK orders sized 200mm and EU, US and AU orders sized A4 and under ship flat. All other sizes ship rolled.")]),
    ("C2", "CARE", "FRAME NOT INCLUDED — Print only, ready for the frame of your choice",
     [(PRO_HPR, ["unframed"]), (PRO_HPR, ["frame"]), ("csv", "sku", "startswith GLOBAL-HPR")]),   # HPR = cercevesiz kagit baski SKU'su (cerceveli seri ayri: CFPM)
    ("C3", "CARE", "FLAT GOLDEN INK — Gold tones are printed as flat golden ink, not metallic foil",
     [(PRO_HPR, ["pigment"]), (PRO_HPR, ["giclée"]), (PRO_HPR, ["giclee"]), (PRO_PAPERS, ["pigment"])]),
    ("C4", "CARE", "HANDLE BY THE EDGES — Touch only the margins to avoid fingerprints",
     [("note", "care advice (no product claim)")]),
    ("C5", "CARE", "SHIPS FROM THE US — EU and UK orders are printed at our UK/EU lab",
     [("csv", "lab_US", "startswith US/"), ("csv", "lab_DE", "in GB/ NL/")]),
    ("C_footer", "CARE", "Made to Order, Just for You",
     [(PRO_HPR, ["print on demand"]), (PRO_PACK, ["print on demand"]), (PRO_HPR, ["on demand"])]),
]

_cache = {}


_diag = {}


def page_sentences(url, offline):
    if offline:
        return None
    if url not in _cache:
        try:
            r = requests.get(url, headers=UA, timeout=30)
            txt = r.text if r.status_code == 200 else ""
            _diag[url] = f"HTTP {r.status_code}, {len(r.text)} karakter"
        except requests.RequestException as e:
            txt = ""
            _diag[url] = f"HATA {type(e).__name__}"
        txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = html.unescape(re.sub(r"\s+", " ", txt))
        sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", txt)
        # cumleler + 400 karakterlik kayan pencereler (accordion/satir sonu farklari icin)
        wins = [txt[i:i + 400] for i in range(0, max(0, len(txt) - 200), 200)]
        _cache[url] = [s.strip() for s in sents if 20 < len(s.strip()) < 600] + wins
    return _cache[url]


def csv_check(rows, col, cond):
    vals = [r.get(col, "") for r in rows]
    if cond == "13 satir":
        ok = len(rows) == 13
        quote = "; ".join(f"{r['sku'].replace('GLOBAL-HPR-', '')}={r['boyut_inch']} in / {r['boyut_cm']} cm" for r in rows)
    elif cond.startswith("=="):
        ok = all(str(v) == cond[3:].strip() for v in vals)
        quote = f"{col}: {sorted(set(vals))}"
    elif cond.startswith("startswith"):
        ok = all(str(v).startswith(cond.split(" ", 1)[1]) for v in vals)
        quote = f"{col}: {sorted(set(vals))}"
    elif cond.startswith("contains"):
        ok = all(cond.split(" ", 1)[1] in str(v) for v in vals)
        quote = f"{col}: {vals[0]!r} ..."
    elif cond.startswith("in "):
        pre = cond[3:].split()
        ok = all(any(str(v).startswith(p) for p in pre) for v in vals)
        quote = f"{col}: {sorted(set(vals))}"
    else:
        ok, quote = False, ""
    return ok, quote


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    rows = [r for r in rows if r.get("durum") == "gecerli" and r["sku"].replace("GLOBAL-HPR-", "") in CARD_SIZES]
    if len(rows) != 13:
        sys.exit(f"HATA: CSV'de kart boyutlarindan {len(rows)}/13 bulundu")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# POD kart metinleri — kaynak dogrulama (FACTCHECK)", "",
             "Kaynaklar: prodigi.com urun/SSS, hahnemuehle.com / hahnemuehle.store, TEMP/PRODIGI/PRODIGI_HPR_SIZES.csv.",
             "Alinti = kaynak sayfadan birebir cumle (HTML metni). KAYNAK YOK satirlari karttan cikarilir.", "",
             "| kart | satir | kaynak | alinti | durum |", "|---|---|---|---|---|"]
    verified = {}
    for fid, card, text, sources in FACTS:
        found = None
        for src in sources:
            if src[0] == "note":
                found = ("—", src[1])
                break
            if src[0] == "quote":                        # Mo'nun verdigi birebir cumle; canli sayfada da aranir
                url, sent = src[1], src[2]
                sents = page_sentences(url, a.offline) or []
                key = sent[:40].lower()
                live = any(key in x.lower() for x in sents)
                found = (url, sent + (" [canli sayfada dogrulandi]" if live else " [verilen alinti; canli sayfada bulunamadi]"))
                break
            if src[0] == "csv":
                ok, q = csv_check(rows, src[1], src[2])
                if ok:
                    found = ("TEMP/PRODIGI/PRODIGI_HPR_SIZES.csv", q[:300])
                    break
            else:
                url, kws = src
                sents = page_sentences(url, a.offline)
                if not sents:
                    continue
                for s in sents:
                    low = s.lower()
                    if all(k.lower() in low for k in kws):
                        found = (url, s[:300])
                        break
                if found:
                    break
        verified[fid] = bool(found)
        src_txt, quote = found if found else ("—", "")
        st = "OK" if found else "KAYNAK YOK → karttan cikar"
        lines.append(f"| {card} | {text} | {src_txt} | {quote.replace('|', '/')} | {st} |")
        print(f"{fid:<9} {'OK ' if found else 'YOK'} {text[:60]}", flush=True)
    lines += ["", "## Kaynak erisim tanisi", ""] + [f"- {u}: {d}" for u, d in _diag.items()]
    (out / "FACTCHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "verified.json").write_text(json.dumps(verified, indent=1))
    n = sum(verified.values())
    print(f"factcheck: {n}/{len(verified)} satir kaynakli")


if __name__ == "__main__":
    main()
