#!/usr/bin/env python3
"""Resmi Etsy kaynak sayfalarini (help.etsy.com, Seller Handbook, kurallar) metin olarak indirir.
Etsy API'ye dokunmaz; yalniz herkese acik sayfa GET. Cikti: <out>/<ad>.txt + kaynak_ozet.json (etsy-arama, 10 Eki 2026)."""
import html, json, re, sys, time, urllib.request
from html.parser import HTMLParser
from pathlib import Path

URLS = {
    "help_how_etsy_search_works": "https://help.etsy.com/hc/en-us/articles/115015745428-How-Etsy-Search-Works",
    "help_tags": "https://help.etsy.com/hc/en-us/articles/360000336307-How-to-Use-Tags-to-Get-Found-in-Search",
    "help_attributes": "https://help.etsy.com/hc/en-us/articles/115014502508-How-to-Use-Attributes-When-Listing-an-Item",
    "hb_how_etsy_search_works": "https://www.etsy.com/seller-handbook/article/how-etsy-search-works/375461474487",
    "hb_keywords_101": "https://www.etsy.com/seller-handbook/article/keywords-101-everything-you-need-to-know/382774281517",
    "hb_title_guidance": "https://www.etsy.com/seller-handbook/article/1399426136697",
    "hb_search_visibility_page": "https://www.etsy.com/seller-handbook/article/1289139008351",
    "hb_ultimate_guide_search": "https://www.etsy.com/seller-handbook/article/the-ultimate-guide-to-etsy-search/366469415790",
    "legal_search_ranking_disclosures": "https://www.etsy.com/legal/policy/search-advertisement-recommendation/899478564529",
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


class Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "tr", "br", "div", "section"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag == "li":
            self.out.append("- ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ozet = {}
    for name, url in URLS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read().decode("utf-8", "replace")
                code = r.status
        except Exception as e:  # noqa: BLE001
            ozet[name] = {"url": url, "durum": f"HATA {getattr(e, 'code', '')} {type(e).__name__}"}
            print(f"{name}: HATA {e}", flush=True)
            continue
        p = Text()
        p.feed(raw)
        txt = re.sub(r"\n\s*\n+", "\n\n", html.unescape("".join(p.out)))
        txt = "\n".join(x.strip() for x in txt.splitlines())
        (out / f"{name}.txt").write_text(f"KAYNAK: {url}\nINDIRME: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n{txt}", encoding="utf-8")
        ozet[name] = {"url": url, "durum": code, "karakter": len(txt)}
        print(f"{name}: {code} {len(txt)} kr", flush=True)
        time.sleep(1)
    (out / "kaynak_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
