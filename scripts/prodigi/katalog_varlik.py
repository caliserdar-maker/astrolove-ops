#!/usr/bin/env python3
"""GOREV 0040 md.2 / 0041 - Prodigi site varliklari (SALT OKUMA).
Sitemap'ten YALNIZ Ingilizce /products/ sayfalari (dil onekli /de/ /fr/ ... disarida), --desen ile yol filtresi.
Her sayfadan: urun gorselleri (og:image + img/srcset; 15 KB alti ikon/logo atlanir), .pdf linkleri, ve sayfa metninden
kagit/cerceve olgu satirlari (gsm, cotton, acid, finish, matte, lustre, glaze, perspex, glass, mount, mm, depth, oak, laminate).
--pdf ile verilen dogrudan PDF'ler de indirilir. Cikti: out/<kok>/<sayfa>/ + out/<kok>/VARLIK_DURUM.md + OLGU_METIN.md
Kullanim: katalog_varlik.py --kok GORSEL --desen "classic-frame|framed-prints" --azami 40 --pdf URL ..."""
import argparse
import html as H
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
KOK = "https://www.prodigi.com"
DIL = re.compile(r"^/(de|fr|es|it|nl|pt|pl|sv|da|fi|nb|ja|zh|ko)(/|$)")
OLGU = re.compile(r"\b(\d{2,3}\s?gsm|cotton|acid[- ]free|finish|matte|matt\b|lustre|gloss|satin|texture|alpha.cellulose|"
                  r"archival|glaze|perspex|acrylic|glass|moth.?eye|mount|mat\b|mm\b|depth|profile|oak|laminate|moulding|hanging)",
                  re.I)


def al(url, timeout=40):
    try:
        return requests.get(url, headers=UA, timeout=timeout)
    except requests.RequestException as e:
        return type("R", (), {"status_code": type(e).__name__, "text": "", "content": b"", "headers": {}})()


def sayfalar(desen):
    r = al(f"{KOK}/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", r.text or "")
    for s in [u for u in urls if u.endswith(".xml")][:15]:
        urls += re.findall(r"<loc>([^<]+)</loc>", al(s).text or "")
    rx = re.compile(desen, re.I)
    sec = sorted({u for u in urls if not u.endswith(".xml") and "/products/" in urlparse(u).path
                  and not DIL.match(urlparse(u).path) and rx.search(urlparse(u).path)})
    return r.status_code, sec


def metin(h):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    t = H.unescape(re.sub(r"<[^>]+>", "\n", h))
    satir = [re.sub(r"\s+", " ", s).strip() for s in t.split("\n")]
    return list(dict.fromkeys(s for s in satir if 12 <= len(s) <= 300 and OLGU.search(s)))


def gorseller(u, h):
    img = set(re.findall(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', h))
    img |= set(re.findall(r'<img[^>]+src="([^"]+\.(?:jpe?g|png|webp)[^"]*)"', h, re.I))
    for ss in re.findall(r'srcset="([^"]+)"', h):
        img |= {p.strip().split(" ")[0] for p in ss.split(",") if re.search(r"\.(jpe?g|png|webp)", p, re.I)}
    return sorted(urljoin(u, x) for x in img if not re.search(r"logo|icon|sprite|flag|payment|avatar", x, re.I))


def kaydet(dizin, ad, rr, min_bayt):
    if getattr(rr, "status_code", 0) == 200 and len(rr.content or b"") >= min_bayt:
        dizin.mkdir(parents=True, exist_ok=True)
        (dizin / ad).write_bytes(rr.content)
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default="KATALOG")
    ap.add_argument("--desen", default=".")
    ap.add_argument("--azami", type=int, default=40)
    ap.add_argument("--gorsel-azami", type=int, default=30)
    ap.add_argument("--pdf", nargs="*", default=[])
    a = ap.parse_args()
    out = Path("out") / a.kok
    out.mkdir(parents=True, exist_ok=True)
    kod, urls = sayfalar(a.desen)
    durum = [f"# VARLIK_DURUM {time.strftime('%Y-%m-%d %H:%M')} UTC", "", f"- sitemap http {kod}, desen '{a.desen}', "
             f"Ingilizce /products/ eslesen {len(urls)} (ilk {a.azami})", "", "| sayfa | http | gorsel | pdf | olgu satiri |", "|---|---|---|---|---|"]
    olgu, t0, n = [f"# OLGU_METIN (sayfa metninden, kelimesi kelimesine) {time.strftime('%Y-%m-%d %H:%M')} UTC", ""], time.time(), min(len(urls), a.azami)
    for i, u in enumerate(urls[:a.azami], 1):
        r = al(u)
        h, yol = r.text or "", urlparse(u).path
        ad = re.sub(r"[^a-z0-9-]+", "-", yol.strip("/").lower())[:80] or "kok"
        ni = sum(kaydet(out / ad, f"gorsel_{j:02d}{Path(urlparse(x).path).suffix or '.jpg'}", al(x), 15000)
                 for j, x in enumerate(gorseller(u, h)[:a.gorsel_azami]))
        np_ = sum(kaydet(out / ad, f"foy_{j}.pdf", al(urljoin(u, x)), 1000)
                  for j, x in enumerate(sorted(set(re.findall(r'href="([^"]+\.pdf[^"]*)"', h, re.I)))[:4]))
        sat = metin(h)
        olgu += [f"## {yol}", ""] + [f"- {s}" for s in sat[:40]] + [""]
        durum.append(f"| {yol} | {r.status_code} | {ni} | {np_} | {len(sat)} |")
        g = time.time() - t0
        print(f"[{i}/{n}] {100 * i // max(n, 1)}% gecen {g:.0f}s kalan ~{g / i * (n - i):.0f}s {yol} {r.status_code} img {ni} pdf {np_}", flush=True)
    for j, p in enumerate(a.pdf):
        rr = al(p, 90)
        ok = kaydet(out / "_pdf", f"{j}_{Path(urlparse(p).path).name.replace('%20', '_')}", rr, 1000)
        durum.append(f"| PDF {p} | {getattr(rr, 'status_code', '?')} | - | {int(ok)} | - |")
    (out / "VARLIK_DURUM.md").write_text("\n".join(durum) + "\n", encoding="utf-8")
    (out / "OLGU_METIN.md").write_text("\n".join(olgu) + "\n", encoding="utf-8")
    print("\n".join(durum[:3]), flush=True)


if __name__ == "__main__":
    main()
