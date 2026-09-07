#!/usr/bin/env python3
"""
Prodigi branded insert (8 tip) fiyat + ozellik okuma (salt okur; siparis vermez).

Yontem (tahmin yok, her sey kaynaktan):
 1) SEMA KESFI: once makine okunur sema adaylari (OpenAPI/swagger), sonra Print API
    dokumani ve prodigi.com sitemap'inde "insert" gecen sayfalar indirilir. Quote
    govdesinde "inserts" alani ANCAK bu kaynaklarda bulunursa kullanilir; hicbir
    alan uydurulmaz.
 2) FIYAT: referans urun GLOBAL-HPR-8x10, adet 1, Budget kargo, hedef US ve DE.
    Once insert'siz BAZ teklif, sonra her insert tipi icin ayri teklif; birim
    maliyet = teklif - baz. Sema bulunamazsa ya da API insert'i fiyatlandirmazsa
    ilgili hucreye "API fiyat donmuyor" yazilir.
 3) OZELLIK: her tipin olcusu (mm), dosya formati ve tesis uygunlugu (US Charlotte /
    GB / EU) indirilen sayfa metninden alintiyla cikarilir; bulunamayan alan bos
    kalir ve "kaynak yok" notu dusulur. 300 dpi piksel = mm / 25.4 * 300.

Cikti: PRODIGI_INSERTS_QUOTE.csv + .md -> gdrive:ASTROLOVE/TEMP/PRODIGI/
Anahtar: prodigi_pilot_quote.load_key (rclone + ::add-mask::, loga yazilmaz).

Kullanim:
  python prodigi_inserts_quote.py [--out-dir DIR] [--no-drive] [--self-test]
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prodigi_pilot_quote import Api, OUT_REMOTE, leak_check, load_key, log, money  # noqa: E402

REF_SKU = "GLOBAL-HPR-8x10"
SHIPPING = "Budget"
DESTS = [("US", "US_maliyet"), ("DE", "EU_maliyet")]
CURRENCY = "USD"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126 Safari/537.36"}

# Makine okunur sema adaylari (200 doneni kullanilir)
SCHEMA_URLS = [
    "https://api.prodigi.com/v4.0/swagger/v1/swagger.json",
    "https://api.prodigi.com/swagger/v1/swagger.json",
    "https://api.prodigi.com/v4.0/openapi.json",
    "https://api.prodigi.com/v4.0/swagger.json",
    "https://www.prodigi.com/print-api/docs/swagger.json",
]
DOC_URLS = [
    "https://www.prodigi.com/print-api/docs/reference/",
    "https://www.prodigi.com/print-api/docs/",
    "https://www.prodigi.com/print-api/",
]
SITEMAPS = ["https://www.prodigi.com/sitemap.xml", "https://www.prodigi.com/sitemap_index.xml"]

# Mo'nun listesi: rapor satirlari bu sirada; olcu/format/tesis kaynaktan doldurulur.
TYPES = [
    ("Postcard (A6)", ["postcard", "a6"]),
    ("Flyer (A5)", ["flyer", "a5"]),
    ("Packing slip (colour)", ["packing slip", "colour", "color"]),
    ("Packing slip (b&w)", ["packing slip", "b&w", "black and white", "mono"]),
    ("Round packaging sticker (65 mm)", ["round", "packaging sticker", "65"]),
    ("Rectangular packaging sticker (105x74 mm)", ["rectangular", "packaging sticker", "105"]),
    ("Round product sticker (25 mm)", ["round", "product sticker", "25"]),
    ("Rectangular product sticker (105x74 mm)", ["rectangular", "product sticker", "105"]),
]
FIELDS = ["tip", "olcu_mm", "olcu_px_300dpi", "US_maliyet", "EU_maliyet",
          "tesis_uygunluk", "dosya_formati", "kaynak"]
NOPRICE = "API fiyat donmuyor"


# ------------------------------------------------------------------ yardimci
def px300(mm_txt):
    """'148 x 105' -> '1748 x 1240' (300 dpi). Bos/anlasilmazsa '' doner."""
    n = re.findall(r"(\d+(?:[.,]\d+)?)", mm_txt or "")
    if len(n) < 2:
        return ""
    return " x ".join(str(int(round(float(v.replace(",", ".")) / 25.4 * 300))) for v in n[:2])


def text_of(html):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", t).strip()


def fetch(sess, url):
    try:
        r = sess.get(url, headers=UA, timeout=40)
        return (r.status_code, r.text) if r.status_code == 200 else (r.status_code, "")
    except Exception as e:                                  # ag hatasi kaynak yoklugudur
        return (0, f"__ERR__ {e}")


# ------------------------------------------------------------------ 1) sema kesfi
def sitemap_urls(sess):
    out = []
    for sm in SITEMAPS:
        st, body = fetch(sess, sm)
        if st != 200:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        out += [u for u in locs if re.search(r"insert|packing|sticker|postcard|flyer", u, re.I)]
        sub = [u for u in locs if u.endswith(".xml")][:6]
        for s in sub:
            st2, b2 = fetch(sess, s)
            if st2 == 200:
                out += [v for v in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", b2)
                        if re.search(r"insert|packing|sticker|postcard|flyer", v, re.I)]
    return list(dict.fromkeys(out))[:12]


def discover(sess):
    """Kaynaklari indirir; {url: (kind, raw)} ve sema icindeki inserts tanimini dondurur."""
    sources, schema = {}, None
    for u in SCHEMA_URLS:
        st, body = fetch(sess, u)
        log(f"  sema {u} -> {st}")
        if st != 200 or not body:
            continue
        try:
            doc = json.loads(body)
        except ValueError:
            continue
        sources[u] = ("openapi", body)
        found = find_in_schema(doc)
        if found and schema is None:
            schema = {"url": u, "tanim": found}
    pages = list(DOC_URLS) + sitemap_urls(sess)
    for u in pages:
        st, body = fetch(sess, u)
        log(f"  sayfa {u} -> {st} ({len(body)} B)")
        if st == 200 and body:
            sources[u] = ("html", body)
    if schema is None:
        schema = find_in_pages(sources)
    return sources, schema


def find_in_schema(doc):
    """OpenAPI icinde 'inserts' property'si arar; bulursa tanimini dondurur."""
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() == "inserts":
                    hits.append({"yol": "/".join(path + [k]), "tanim": v})
                walk(v, path + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])

    walk(doc, [])
    return hits or None


def find_in_pages(sources):
    """Doküman sayfalarinda '"inserts"' gecen JSON parcasini arar."""
    for u, (kind, raw) in sources.items():
        for m in re.finditer(r'"inserts"\s*:', raw):
            s = max(0, m.start() - 400)
            return {"url": u, "tanim": [{"yol": "sayfa metni",
                                         "tanim": raw[s:m.start() + 600]}]}
    return None


# ------------------------------------------------------------------ 2) ozellikler
def spec_from_sources(sources, name, keys):
    """Tip icin olcu/format/tesis satirini kaynak metinden alintiyla cikarir."""
    best = None
    for u, (kind, raw) in sources.items():
        txt = text_of(raw) if kind == "html" else raw
        for sent in re.split(r"(?<=[.!?])\s+|\n", txt):
            low = sent.lower()
            if all(k.split()[0] in low for k in keys[:2]) and len(sent) < 400:
                score = sum(1 for k in keys if k in low)
                if best is None or score > best[0]:
                    best = (score, sent.strip(), u)
    if not best:
        return {"olcu_mm": "", "dosya_formati": "", "tesis_uygunluk": "", "kaynak": ""}
    _, sent, url = best
    mm = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mm)?\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*mm", sent, re.I)
    rnd = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", sent, re.I)
    fmt = ", ".join(dict.fromkeys(re.findall(r"\b(PDF|PNG|JPE?G|TIFF|AI|EPS|SVG)\b", sent, re.I)))
    fac = ", ".join(dict.fromkeys(re.findall(r"\b(Charlotte|United States|USA|US|GB|United Kingdom|UK|EU|Europe|Netherlands|Germany)\b", sent)))
    return {"olcu_mm": (f"{mm.group(1)} x {mm.group(2)}" if mm else (rnd.group(1) if rnd else "")),
            "dosya_formati": fmt, "tesis_uygunluk": fac, "kaynak": url}


# ------------------------------------------------------------------ 3) teklifler
def quote_body(dest, inserts=None):
    item = {"sku": REF_SKU, "copies": 1, "assets": [{"printArea": "default"}]}
    body = {"destinationCountryCode": dest, "currencyCode": CURRENCY,
            "shippingMethod": SHIPPING, "items": [item]}
    if inserts is not None:
        body["inserts"] = inserts
    return body


def quote_total(api, body):
    """(toplam, ham) - toplam = items + shipping (Budget teklifi)."""
    r = api._call("POST", "/quotes", body)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    qs = d.get("quotes") or []
    if not qs:
        iss = "; ".join(f"{i.get('errorCode')}: {i.get('description')}" for i in d.get("issues") or [])
        return None, f"outcome={d.get('outcome')} {iss}".strip()
    q = qs[0]
    cs = q.get("costSummary") or {}
    items, ship = money(cs.get("items")), money(cs.get("shipping"))
    try:
        return round(float(items) + float(ship), 2), q
    except (TypeError, ValueError):
        return None, f"maliyet okunamadi: {cs}"


def insert_ids(schema):
    """Semada insert tanimlayicilari (enum) varsa dondurur."""
    if not schema:
        return []
    blob = json.dumps(schema, ensure_ascii=False)
    return list(dict.fromkeys(re.findall(r'"(?:enum|values)"\s*:\s*\[([^\]]+)\]', blob)))


# ------------------------------------------------------------------ rapor
def write_out(rows, notes, out_dir, drive):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_p, md_p = out_dir / "PRODIGI_INSERTS_QUOTE.csv", out_dir / "PRODIGI_INSERTS_QUOTE.md"
    with csv_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Prodigi branded insert fiyat/ozellik ({ts})", "",
             f"Referans urun: {REF_SKU}, adet 1, {SHIPPING} kargo, para birimi {CURRENCY}.",
             "Birim maliyet = insert'li teklif - insert'siz baz teklif.", ""]
    lines += ["| " + " | ".join(FIELDS) + " |", "|" + "---|" * len(FIELDS)]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(k, "")) for k in FIELDS) + " |")
    lines += ["", "## Notlar"] + [f"- {n}" for n in notes]
    md_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for p in (csv_p, md_p):
        leak_check(p)
        log(f"yazildi: {p}")
        if drive:
            subprocess.run(["rclone", "copyto", str(p), f"{OUT_REMOTE}/{p.name}", "-q"], check=True)
    return csv_p, md_p


# ------------------------------------------------------------------ self-test
def self_test():
    """Ag olmadan parse/rapor akisi (yerel onizleme)."""
    assert px300("148 x 105") == "1748 x 1240", px300("148 x 105")
    assert px300("65") == ""
    assert px300("65 x 65") == "768 x 768"
    src = {"https://x/insert": ("html", "<p>Our A6 postcard inserts are 148 x 105 mm, "
                                        "supplied as a PDF, printed in Charlotte US and GB.</p>")}
    s = spec_from_sources(src, "Postcard (A6)", ["postcard", "a6"])
    assert s["olcu_mm"] == "148 x 105" and "PDF" in s["dosya_formati"], s
    assert find_in_pages({"u": ("html", '{"inserts": [{"type": "postcard"}]}')})
    rows = [{"tip": t, "olcu_mm": "", "olcu_px_300dpi": "", "US_maliyet": NOPRICE,
             "EU_maliyet": NOPRICE, "tesis_uygunluk": "", "dosya_formati": "", "kaynak": ""}
            for t, _ in TYPES]
    d = Path("/tmp/prodigi_selftest")
    write_out(rows, ["self-test"], d, drive=False)
    assert (d / "PRODIGI_INSERTS_QUOTE.csv").exists()
    log("self-test: PASS (px300, spec parse, sema arama, rapor yazimi)")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--no-drive", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    sess = requests.Session()
    log("1) sema/dokuman kesfi")
    sources, schema = discover(sess)
    notes = [f"indirilen kaynak: {len(sources)}"]
    if schema:
        notes.append(f"quote semasinda 'inserts' bulundu: {schema.get('url', '')}")
        log(f"  inserts tanimi bulundu: {str(schema)[:400]}")
    else:
        notes.append("quote semasinda/dokumaninda 'inserts' alani BULUNAMADI "
                     "(sema adaylari ve prodigi.com sayfalari tarandi)")
        log("  inserts tanimi bulunamadi")

    log("2) teklifler")
    api = Api(load_key())
    base = {}
    for dest, _ in DESTS:
        t, raw = quote_total(api, quote_body(dest))
        base[dest] = t
        log(f"  baz {dest}: {t if t is not None else raw}")
        if t is None:
            notes.append(f"baz teklif {dest} alinamadi: {raw}")

    ids = insert_ids(schema)
    if ids:
        notes.append(f"sema insert tanimlayicilari: {ids}")

    rows = []
    for name, keys in TYPES:
        r = {"tip": name}
        r.update(spec_from_sources(sources, name, keys))
        r["olcu_px_300dpi"] = px300(r["olcu_mm"])
        for dest, col in DESTS:
            r[col] = NOPRICE
        if schema:
            for dest, col in DESTS:
                body = quote_body(dest, inserts=[{"type": name}])
                t, raw = quote_total(api, body)
                if t is not None and base.get(dest) is not None:
                    r[col] = f"{round(t - base[dest], 2)} {CURRENCY}"
                else:
                    log(f"  {name} {dest}: {raw}")
        if not r["kaynak"]:
            r["kaynak"] = "kaynak yok"
        rows.append(r)
        log(f"  {name}: olcu {r['olcu_mm'] or '-'} US {r['US_maliyet']} EU {r['EU_maliyet']}")

    if all(r["US_maliyet"] == NOPRICE for r in rows):
        notes.append(f"SONUC: {NOPRICE} - insert'ler quote ucundan fiyatlandirilamadi.")
    write_out(rows, notes, Path(a.out_dir), drive=not a.no_drive)


if __name__ == "__main__":
    main()
