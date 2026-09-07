#!/usr/bin/env python3
"""
POD ilanina DIJITAL SURUM LINKLERI ekler (Mo 7 Eyl 2026, ADIM 0: yalniz ARIES_LEO 4570031205).

Yapilan:
  1. PLEASE NOTE (RU: ОБРАТИТЕ ВНИМАНИЕ) blogundaki "- Prefer an instant download? ..." satiri KALDIRILIR.
  2. Bu blogun HEMEN ARDINA yeni bolum eklenir:
       ✦ PREFER AN INSTANT DOWNLOAD?  /  ✦ ХОТИТЕ МГНОВЕННУЮ ЗАГРУЗКУ?
       ardindan 5 renk icin "<Renk> — <url>" satirlari (renk adlari iki dilde de Ingilizce).
  3. Diger tum bolumler BIREBIR korunur (bolum bolum karsilastirilir; baska fark varsa YAZILMAZ).

Dijital ilan id'leri Etsy'den BULUNUR (tahmin yok): aktif ilanlar taranir, basliginda her iki burc ve
renk adi gecen, POD bolumu DISINDAKI ilan aranir. Bir renk icin tam bir eslesme yoksa kosu DURUR ve
adaylari raporlar. Yazma: updateListing (EN) + translations/ru PUT (baslik/tag Etsy'deki gibi).
Geri okuma: yazilan metin beklenenle birebir; degisen bolumler yalniz PLEASE NOTE + yeni bolum.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: pod_crosslink.py --listing-id 4570031205 --pair ARIES_LEO --out OUT --dry-run|--apply
"""
import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_inventory_update import sections  # noqa: E402
from wp_listing_update import norm  # noqa: E402

POD_SECTION = 60204164
COLORS = ["Champagne Ivory", "Pure White", "Warm Parchment", "Midnight Blue", "Deep Black"]
SEC = {"en": ("✦ PLEASE NOTE", "✦ PREFER AN INSTANT DOWNLOAD?", "The same design is available as a digital edition:",
              re.compile(r"^-\s*Prefer an instant download\?.*$", re.M)),
       "ru": ("✦ ОБРАТИТЕ ВНИМАНИЕ", "✦ ХОТИТЕ МГНОВЕННУЮ ЗАГРУЗКУ?", "Тот же дизайн доступен как цифровое издание:",
              re.compile(r"^-\s*Предпочитаете мгновенное скачивание\?.*$", re.M))}
URL = "https://www.etsy.com/listing/{lid}"


def shop_listings(api, shop, state="active", max_pages=12):
    out, offset = [], 0
    for _ in range(max_pages):
        r = api.get(f"/shops/{shop}/listings", params={"state": state, "limit": 100, "offset": offset}) or {}
        res = r.get("results") or []
        out += [{"listing_id": str(x.get("listing_id")), "title": x.get("title") or "",
                 "section": x.get("shop_section_id")} for x in res]
        if len(res) < 100:
            break
        offset += 100
    return out


def find_digitals(listings, pair, skip_id, pod_section=POD_SECTION):
    """-> ({renk: (id, baslik)}, {renk: [adaylar]}) - renk basina TAM BIR eslesme sart."""
    s1, s2 = [s.capitalize() for s in pair.split("_", 1)]
    rx = [re.compile(rf"\b{s}\b", re.I) for s in {s1, s2}]
    base = [x for x in listings if x["listing_id"] != str(skip_id) and x["section"] != pod_section
            and all(r.search(x["title"]) for r in rx)]
    found, cand = {}, {}
    for c in COLORS:
        hits = [x for x in base if re.search(re.escape(c), x["title"], re.I)]
        cand[c] = hits
        if len(hits) == 1:
            found[c] = (hits[0]["listing_id"], hits[0]["title"])
    return found, cand


def new_block(lang, found):
    head, title, lead, _ = SEC[lang]
    return "\n".join([title, lead] + [f"{c} — {URL.format(lid=found[c][0])}" for c in COLORS])


def transform(text, lang, found):
    """(yeni_metin, hata). Satiri kaldirir, PLEASE NOTE blogundan sonra yeni bolumu ekler."""
    head, title, lead, line_rx = SEC[lang]
    t = norm(text)
    if title in t:
        return None, f"{lang}: '{title}' bolumu zaten var"
    if head not in t:
        return None, f"{lang}: '{head}' bolumu bulunamadi"
    parts = t.split("\n" + head + "\n")
    if len(parts) != 2:
        return None, f"{lang}: '{head}' bolumu {len(parts) - 1} kez gecti"
    before, rest = parts
    m = re.search(r"\n✦ ", rest)
    blok, kalan = (rest[:m.start()], rest[m.start():]) if m else (rest, "")
    yeni_blok = line_rx.sub("", blok).rstrip("\n")
    yeni_blok = re.sub(r"\n{3,}", "\n\n", yeni_blok)
    if yeni_blok == blok.rstrip("\n"):
        return None, f"{lang}: kaldirilacak 'instant download' satiri bulunamadi"
    kuyruk = ("\n" + kalan) if kalan else ""          # bolum basliklarindan once bos satir korunur
    return f"{before}\n{head}\n{yeni_blok}\n\n{new_block(lang, found)}{kuyruk}", ""


def check(old, new, lang):
    """Bolum bolum: yalniz PLEASE NOTE degismis + yeni bolum eklenmis olmali."""
    head, title, _, _ = SEC[lang]
    so, sn = sections(old), sections(new)
    eklenen = [k for k in sn if k not in so]
    silinen = [k for k in so if k not in sn]
    degisen = [k for k in so if k in sn and so[k] != sn[k]]
    ok = eklenen == [title] and not silinen and degisen == [head]
    return ok, {"eklenen": eklenen, "silinen": silinen, "degisen": degisen}


def diff_text(old, new):
    return "\n".join(difflib.unified_diff(norm(old).split("\n"), norm(new).split("\n"), "eski", "yeni", lineterm="", n=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing-id", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--pod-section", type=int, default=POD_SECTION)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    t0 = time.time()
    lst = shop_listings(api, shop)
    q0 = api.remaining
    log(f"aktif ilan: {len(lst)} | kota {q0} | gecen {time.time() - t0:.0f}s")
    try:
        rem = int(api.remaining) if api.remaining is not None else None
    except ValueError:
        rem = None
    if rem is not None and rem < a.quota_min:
        raise SystemExit(f"DUR: kota {rem} < {a.quota_min}")

    found, cand = find_digitals(lst, a.pair, a.listing_id, a.pod_section)
    md = [f"## Capraz satis linkleri — {a.pair} {a.listing_id} ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          "| renk | dijital listing_id | baslik |", "|---|---|---|"]
    md += [f"| {c} | {found[c][0] if c in found else '**BULUNAMADI**'} | {found[c][1] if c in found else ', '.join(x['title'] for x in cand[c]) or '-'} |"
           for c in COLORS]
    if len(found) != len(COLORS):
        eksik = [c for c in COLORS if c not in found]
        md += ["", f"**DUR: {len(eksik)} renk icin tek eslesme yok: {', '.join(eksik)}**",
               "", "Aday ilanlar (her iki burc + POD disi bolum):", ""]
        md += [f"- {x['listing_id']} | bolum {x['section']} | {x['title']}"
               for x in sorted({x['listing_id']: x for c in COLORS for x in cand[c]}.values(), key=lambda y: y["listing_id"])] or ["- (aday yok)"]
        text = "\n".join(md + ["", f"**Kota once {q0} / sonra {api.remaining}**"])
        log(text); (out / "CROSSLINK_REPORT.md").write_text(text + "\n", encoding="utf-8")
        p = os.environ.get("GITHUB_STEP_SUMMARY")
        if p:
            open(p, "a", encoding="utf-8").write(text + "\n")
        sys.exit("DUR: dijital ilan eslesmesi eksik")

    L = api.get(f"/listings/{a.listing_id}") or {}
    tru = api.get(f"/shops/{shop}/listings/{a.listing_id}/translations/ru", ok404=True) or {}
    new_en, err_en = transform(L.get("description") or "", "en", found)
    new_ru, err_ru = transform(tru.get("description") or "", "ru", found)
    if err_en or err_ru:
        raise SystemExit(f"DUR: {err_en or ''} {err_ru or ''}".strip())
    ok_en, d_en = check(norm(L.get("description")), new_en, "en")
    ok_ru, d_ru = check(norm(tru.get("description")), new_ru, "ru")
    if not (ok_en and ok_ru):
        raise SystemExit(f"DUR: beklenmeyen bolum farki EN {d_en} RU {d_ru}")
    md += ["", "### Diff (EN)", "", "```diff", diff_text(L.get("description"), new_en), "```",
           "", "### Diff (RU)", "", "```diff", diff_text(tru.get("description"), new_ru), "```"]
    (out / "new_en.txt").write_text(new_en + "\n", encoding="utf-8")
    (out / "new_ru.txt").write_text(new_ru + "\n", encoding="utf-8")

    if a.apply:
        r = api.patch(f"/shops/{shop}/listings/{a.listing_id}", {"description": new_en})
        back_en = r if isinstance(r, dict) and r.get("description") else (api.get(f"/listings/{a.listing_id}") or {})
        body = {"title": tru.get("title") or "", "description": new_ru, "tags": ",".join(tru.get("tags") or [])}
        r = api.put(f"/shops/{shop}/listings/{a.listing_id}/translations/ru", body)
        back_ru = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{a.listing_id}/translations/ru", ok404=True) or {})
        p_en = norm(back_en.get("description")) == norm(new_en)
        p_ru = norm(back_ru.get("description")) == norm(new_ru) and back_ru.get("title") == tru.get("title") \
            and [t.strip() for t in (back_ru.get("tags") or [])] == [t.strip() for t in (tru.get("tags") or [])]
        md += ["", f"- Geri okuma: EN {'PASS' if p_en else 'FAIL'}, RU {'PASS' if p_ru else 'FAIL'} "
                   f"(RU baslik/etiket degismedi: {'evet' if p_ru else 'HAYIR'})"]
        durum = p_en and p_ru
    else:
        md += ["", "- DRY-RUN: Etsy'ye yazilmadi"]
        durum = True
    md += ["", f"**Kota once {q0} / sonra {api.remaining}**"]
    text = "\n".join(md)
    log(text)
    (out / "CROSSLINK_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "crosslink_result.json").write_text(json.dumps(
        {"listing_id": a.listing_id, "pair": a.pair, "digital": {c: found[c][0] for c in COLORS},
         "quota": [q0, api.remaining], "ok": durum}, indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if not durum:
        sys.exit(1)


if __name__ == "__main__":
    main()
