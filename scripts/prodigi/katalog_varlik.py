#!/usr/bin/env python3
"""GOREV 0040 md.2 - Prodigi site varliklari (SALT OKUMA): sitemap'ten kagit/cerceve urun sayfalari; her sayfadan
og:image, urun gorselleri ve .pdf (urun foyu) linkleri indirilir -> out/KATALOG/<sayfa>/. Erisilemezse durum yazilir.
Cikti: out/KATALOG/VARLIK_DURUM.md (sayfa, http, indirilen dosya sayisi)."""
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
KOK = "https://www.prodigi.com"
ANAHTAR = re.compile(r"(fine-art|photo-rag|hahnemuhle|etching|baryta|watercolou?r|smooth-art|lustre|enhanced-matte|"
                     r"framed|frame|mount|poster)", re.I)
OUT = Path("out/KATALOG")


def al(url, timeout=30):
    try:
        return requests.get(url, headers=UA, timeout=timeout)
    except requests.RequestException as e:
        return type("R", (), {"status_code": type(e).__name__, "text": "", "content": b""})()


def sayfalar():
    r = al(f"{KOK}/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", r.text or "")
    alt = [u for u in urls if u.endswith(".xml")]
    for s in alt[:10]:
        urls += re.findall(r"<loc>([^<]+)</loc>", al(s).text or "")
    urun = sorted({u for u in urls if not u.endswith(".xml") and ANAHTAR.search(urlparse(u).path)})
    return r.status_code, urun


def main(azami=40):
    OUT.mkdir(parents=True, exist_ok=True)
    kod, urls = sayfalar()
    satir, t0 = [f"# VARLIK_DURUM {time.strftime('%Y-%m-%d %H:%M')} UTC", "", f"- sitemap http {kod}, eslesen sayfa {len(urls)} (ilk {azami})", "",
                 "| sayfa | http | gorsel | pdf |", "|---|---|---|---|"], time.time()
    for i, u in enumerate(urls[:azami], 1):
        r = al(u)
        ad = re.sub(r"[^a-z0-9-]+", "-", urlparse(u).path.strip("/").lower())[:80] or "kok"
        h = r.text or ""
        img = set(re.findall(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', h))
        img |= {x for x in re.findall(r'<img[^>]+src="([^"]+\.(?:jpe?g|png|webp)[^"]*)"', h, re.I) if "logo" not in x.lower()}
        pdf = set(re.findall(r'href="([^"]+\.pdf[^"]*)"', h, re.I))
        n_img = n_pdf = 0
        for j, x in enumerate(sorted(img)[:6]):
            rr = al(urljoin(u, x))
            if getattr(rr, "status_code", 0) == 200 and rr.content:
                (OUT / ad).mkdir(exist_ok=True)
                (OUT / ad / f"gorsel_{j}{Path(urlparse(x).path).suffix or '.jpg'}").write_bytes(rr.content); n_img += 1
        for j, x in enumerate(sorted(pdf)[:3]):
            rr = al(urljoin(u, x))
            if getattr(rr, "status_code", 0) == 200 and rr.content:
                (OUT / ad).mkdir(exist_ok=True)
                (OUT / ad / f"foy_{j}.pdf").write_bytes(rr.content); n_pdf += 1
        satir.append(f"| {urlparse(u).path} | {r.status_code} | {n_img} | {n_pdf} |")
        g = time.time() - t0
        print(f"[{i}/{min(len(urls), azami)}] gecen {g:.0f}s kalan ~{g / i * (min(len(urls), azami) - i):.0f}s {u} {r.status_code}", flush=True)
    (OUT / "VARLIK_DURUM.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    print("\n".join(satir[:3]), flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
