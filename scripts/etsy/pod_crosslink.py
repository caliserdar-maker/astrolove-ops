#!/usr/bin/env python3
"""
POD ilanlarina DIJITAL SURUM LINKLERI ekler (Mo 7 Eyl 2026; ADIM 0 tek ilan, sonra 78 ilan).

Her ilan icin:
  1. PLEASE NOTE (RU: ОБРАТИТЕ ВНИМАНИЕ) blogundaki "- Prefer an instant download? ..." satiri KALDIRILIR.
  2. Dijital surum bolumu "✦ 5 COLOR EDITIONS" / "✦ 5 ЦВЕТОВЫХ ИЗДАНИЙ" bolumunun HEMEN ARDINA,
     "✦ 13 SIZES" / "✦ 13 РАЗМЕРОВ" oncesine konur (Mo 7 Eyl, yer degisikligi):
       ✦ PREFER AN INSTANT DOWNLOAD? / ✦ ХОТИТЕ МГНОВЕННУЮ ЗАГРУЗКУ?
       + "<Renk> — https://www.etsy.com/listing/<id>" (5 satir, kisa URL, slug yok).
     Bolum baska bir yerdeyse (ADIM 0'daki gibi PLEASE NOTE altinda) oradan alinip yeni yere TASINIR.
  3. Diger bolumler BIREBIR korunur; bolum bolum karsilastirilir, baska fark varsa ilan YAZILMAZ.

Dijital ilan id'leri Etsy'den bulunur (tahmin yok): aktif ilanlar bir kez taranir; basliginda ciftin iki
burcu ve renk adi gecen, POD bolumu disindaki ilan aranir. Bir renk icin tam bir eslesme yoksa O ILAN
ATLANIR ve raporlanir. Kota --quota-min altina inince durur, kalanlar raporlanir. ETA sayaci her ilanda.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim:
  pod_crosslink.py --state STATE.csv --out OUT --dry-run|--apply [--limit N] [--quota-min 400]
  pod_crosslink.py --listing-id 4570031205 --pair ARIES_LEO --out OUT --apply      # tek ilan
"""
import argparse
import csv
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
from pod_listing_create import DIGITAL_HEAD, DIGITAL_LEAD, DIGITAL_ORDER, digital_lines  # noqa: E402
from wp_listing_update import norm  # noqa: E402

POD_SECTION = 60204164
URL = "https://www.etsy.com/listing/{lid}"
NOTE_HEAD = {"en": "✦ PLEASE NOTE", "ru": "✦ ОБРАТИТЕ ВНИМАНИЕ"}
COLOR_HEAD = {"en": "✦ 5 COLOR EDITIONS", "ru": "✦ 5 ЦВЕТОВЫХ ИЗДАНИЙ"}      # bolum bunun hemen ardina girer
OLD_LINE = {"en": re.compile(r"^-\s*Prefer an instant download\?.*$\n?", re.M),
            "ru": re.compile(r"^-\s*Предпочитаете мгновенное скачивание\?.*$\n?", re.M)}


def read_state(path):
    rows = []
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                    rows.append((r["pair"], r["listing_id"]))
    return sorted(rows)


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
    """-> ({renk: (id, baslik)}, {renk: [aday]}) - renk basina TAM BIR eslesme sart."""
    s1, s2 = [s.capitalize() for s in pair.split("_", 1)]
    # Ayni burclu ciftlerde (or. LEO_LEO) tek burc adi baska ciftlerin basligina da uyuyor:
    # baslikta CIFT IFADESI aranir ("<S1> and <S2>", iki siralama da kabul).
    rx = re.compile(rf"\b{s1}\s+and\s+{s2}\b|\b{s2}\s+and\s+{s1}\b", re.I)
    base = [x for x in listings if x["listing_id"] != str(skip_id) and x["section"] != pod_section
            and rx.search(x["title"])]
    found, cand = {}, {}
    for c in DIGITAL_ORDER:
        hits = [x for x in base if re.search(re.escape(c), x["title"], re.I)]
        cand[c] = hits
        if len(hits) == 1:
            found[c] = (hits[0]["listing_id"], hits[0]["title"])
    return found, cand


def block_body(lang, found):
    links = {c: URL.format(lid=found[c][0]) for c in DIGITAL_ORDER}
    return DIGITAL_LEAD[lang] + "\n" + digital_lines(links)


def block(lang, found):
    return DIGITAL_HEAD[lang] + "\n" + block_body(lang, found)


def cut_section(t, head):
    """Bolumu (baslik + govde) metinden cikarir -> (metin, vardi_mi)."""
    if head not in t:
        return t, False
    i = t.index(head)
    rest = t[i + len(head):]
    m = re.search(r"\n✦ ", rest)
    end = i + len(head) + (m.start() if m else len(rest))
    return (t[:i].rstrip("\n") + "\n\n" + t[end:].lstrip("\n")).strip(), True


def insert_after(t, head, blok):
    """Bolumu 'head' bolumunun hemen ardina (bir sonraki '✦ ' basligindan once) koyar."""
    i = t.index(head)
    rest = t[i + len(head):]
    m = re.search(r"\n✦ ", rest)
    pos = i + len(head) + (m.start() if m else len(rest))
    kuyruk = t[pos:].lstrip("\n")
    return t[:pos].rstrip("\n") + "\n\n" + blok + (("\n\n" + kuyruk) if kuyruk else "")


def base(t, lang):
    """Karsilastirma tabani: dijital bolum ve eski 'instant download' satiri cikarilmis metin."""
    x, _ = cut_section(norm(t), DIGITAL_HEAD[lang])
    x = OLD_LINE[lang].sub("", x)
    return re.sub(r"\n{3,}", "\n\n", x).strip()


def transform(text, lang, found):
    """(yeni_metin, ne_yapildi, hata). ne: 'eklendi' | 'tasindi' | 'esitlendi' | 'ayni'."""
    t = norm(text)
    dig, note, color = DIGITAL_HEAD[lang], NOTE_HEAD[lang], COLOR_HEAD[lang]
    if color not in t:
        return None, "", f"{lang}: '{color}' bolumu bulunamadi"
    if note not in t:
        return None, "", f"{lang}: '{note}' bolumu bulunamadi"
    if t.count(dig) > 1 or t.count(color) > 1:
        return None, "", f"{lang}: bolum basligi birden fazla kez geciyor"
    govde, vardi = cut_section(t, dig)
    eski_yer = t.index(dig) if vardi else -1
    govde = re.sub(r"\n{3,}", "\n\n", OLD_LINE[lang].sub("", govde)).strip()
    new = insert_after(govde, color, block(lang, found))
    if new == t:
        return new, "ayni", ""
    ne = "eklendi" if not vardi else ("esitlendi" if eski_yer == new.index(dig) else "tasindi")
    return new, ne, ""


def check(old, new, lang, found):
    """Bagimsiz dogrulama: (1) dijital bolum + eski satir disinda metin BIREBIR ayni,
    (2) bolum sirasi dogru (renk bolumunun hemen ardi), (3) dijital govde beklenen."""
    dig, color = DIGITAL_HEAD[lang], COLOR_HEAD[lang]
    sorun = []
    if base(old, lang) != base(new, lang):
        sorun.append("dijital bolum/eski satir disinda metin degismis")
    sn = list(sections(norm(new)))
    if dig not in sn:
        sorun.append("dijital bolum yok")
    elif color not in sn or sn.index(dig) != sn.index(color) + 1:
        sorun.append(f"bolum sirasi yanlis: {sn}")
    if sections(norm(new)).get(dig) != block_body(lang, found):
        sorun.append("dijital bolum govdesi beklenen degil")
    if OLD_LINE[lang].search(norm(new)):
        sorun.append("eski 'instant download' satiri duruyor")
    return not sorun, sorun


def diff_text(old, new):
    return "\n".join(difflib.unified_diff(norm(old).split("\n"), norm(new).split("\n"), "eski", "yeni", lineterm="", n=1))


def one(api, shop, pair, lid, listings, a, ornek):
    """-> (durum, not, diff_ciftti) ; Etsy yazmasi yalniz --apply ile."""
    found, cand = find_digitals(listings, pair, lid, a.pod_section)
    if len(found) != len(DIGITAL_ORDER):
        eksik = [f"{c}({len(cand[c])} aday)" for c in DIGITAL_ORDER if c not in found]
        return "ATLANDI", "dijital ilan eslesmedi: " + ", ".join(eksik), None
    L = api.get(f"/listings/{lid}") or {}
    tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    new_en, ne_en, err_en = transform(L.get("description") or "", "en", found)
    new_ru, ne_ru, err_ru = transform(tru.get("description") or "", "ru", found)
    if err_en or err_ru:
        return "ATLANDI", f"{err_en} {err_ru}".strip(), None
    ok_en, d_en = check(L.get("description"), new_en, "en", found)
    ok_ru, d_ru = check(tru.get("description"), new_ru, "ru", found)
    if not (ok_en and ok_ru):
        return "SIRA DISI", f"beklenmeyen bolum farki EN {d_en} RU {d_ru}", None
    ids = ", ".join(found[c][0] for c in DIGITAL_ORDER)
    if ne_en == "ayni" and ne_ru == "ayni":
        return "DEGISIM YOK", ids, None
    d = (diff_text(L.get("description"), new_en), diff_text(tru.get("description"), new_ru)) if ornek else None
    if a.dry_run:
        return "HAZIR", f"{ne_en}/{ne_ru} | {ids}", d
    r = api.patch(f"/shops/{shop}/listings/{lid}", {"description": new_en})
    back_en = r if isinstance(r, dict) and r.get("description") else (api.get(f"/listings/{lid}") or {})
    body = {"title": tru.get("title") or "", "description": new_ru, "tags": ",".join(tru.get("tags") or [])}
    r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru", body)
    back_ru = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
    p_en = norm(back_en.get("description")) == norm(new_en)
    p_ru = (norm(back_ru.get("description")) == norm(new_ru) and back_ru.get("title") == tru.get("title")
            and [t.strip() for t in (back_ru.get("tags") or [])] == [t.strip() for t in (tru.get("tags") or [])])
    return ("PASS" if (p_en and p_ru) else "FAIL"), f"EN {'PASS' if p_en else 'FAIL'}, RU {'PASS' if p_ru else 'FAIL'} | {ids}", d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default="", help="cift,listing_id,stage CSV (verified olanlar)")
    ap.add_argument("--listing-id", default="")
    ap.add_argument("--pair", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--quota-min", type=int, default=400)
    ap.add_argument("--pod-section", type=int, default=POD_SECTION)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.state:
        rows = read_state(a.state)
    elif a.listing_id and a.pair:
        rows = [(a.pair, str(a.listing_id))]
    else:
        raise SystemExit("HATA: --state ya da --listing-id + --pair gerekir")
    if not rows:
        raise SystemExit(f"HATA: islenecek ilan yok: {a.state}")
    todo = rows[:a.limit] if a.limit else rows

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    t0 = time.time()
    listings = shop_listings(api, shop)
    q0 = api.remaining
    log(f"aktif ilan: {len(listings)} | kota {q0} | gecen {time.time() - t0:.0f}s")

    res, ornek, stopped = [], None, None
    for n, (pair, lid) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = pair
            log(f"KOTA {rem} < {a.quota_min}: {pair} ve sonrasi islenmedi")
            break
        durum, notu, d = one(api, shop, pair, lid, listings, a, ornek is None)
        if d and ornek is None:
            ornek = (pair, d[0], d[1])
        res.append((pair, lid, durum, notu))
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {pair} {lid} {durum} {notu[:80]} | gecen {el:.0f}s "
            f"kalan~{el / n * (len(todo) - n):.0f}s %{100 * n // len(todo)} | kota {api.remaining}")

    islenen = [r for r in res if r[2] in ("PASS", "HAZIR")]
    bad = [r for r in res if r[2] in ("FAIL", "ATLANDI", "SIRA DISI")]
    kalan = [p for p, _ in todo[len(res):]] + [p for p, _ in rows[len(todo):]]
    md = [f"## POD capraz satis linkleri ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- Ilan {len(rows)}; islenen {len(res)}; guncellenen {len(islenen)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; atlanan/sorunlu {len(bad)}; kalan {len(kalan)}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""), ""]
    if ornek:
        md += [f"### Ornek diff ({ornek[0]})", "", "```diff", ornek[1], "```", "```diff", ornek[2], "```", ""]
    if bad:
        md += ["### Atlanan / sorunlu", "", "| cift | listing_id | durum | neden |", "|---|---|---|---|"]
        md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in bad] + [""]
    md += ["| cift | listing_id | durum | not |", "|---|---|---|---|"]
    md += [f"| {p} | {l} | {s} | {d} |" for p, l, s, d in res]
    if kalan:
        md += ["", f"Kalan: {', '.join(kalan)}"]
    md += ["", f"**Kota once {q0} / sonra {api.remaining}**"]
    text = "\n".join(md)
    log(text)
    (out / "CROSSLINK_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / "crosslink_result.json").write_text(json.dumps(
        {"rows": res, "kalan": kalan, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
