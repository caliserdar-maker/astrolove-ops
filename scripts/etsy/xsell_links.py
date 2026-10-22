#!/usr/bin/env python3
"""
CAPRAZ SATIS: wallpaper ve dijital ilanlara POD (fiziksel baski) linki (Mo 7 Eyl 2026).

  --mode wallpaper : "HOW IT WORKS" blogundan sonra, "GOOD TO KNOW" oncesine
                     "PREFER IT ON YOUR WALL?" blogu eklenir (RU: КАК ЭТО РАБОТАЕТ -> ПОЛЕЗНО ЗНАТЬ).
  --mode digital   : (a) "AI-ASSISTED CREATION DISCLOSURE" basligi ve paragrafi KALDIRILIR (EN + varsa RU),
                     (b) "WHAT YOU WILL RECEIVE" blogundan sonra, "HOW TO DOWNLOAD" oncesine
                     "PREFER IT READY TO HANG?" blogu eklenir.

POD id ayni cifte ait ilandan gelir (STATE: POD_LISTINGS_STATE.csv). Ilan-cift eslesmesi aktif ilan
basliklarindan yapilir (baslikta iki burc; dijitalde ayrica renk adi). Eslesmeyen ya da beklenen
bloklari bulunmayan ilan ATLANIR ve raporlanir - metin uydurulmaz.

Dogrulama: eklenen blok ve (dijitalde) AI bolumu disinda metin BIREBIR ayni; blok dogru yerde; AI
bolumu kalmamis; PATCH/PUT geri okumasi. RU cevirisi yoksa ya da RU'da bloklar bulunmazsa yalniz EN
guncellenir (raporlanir). Kota --quota-min altina inince durur; islenenler XSELL STATE'ine yazilir
(sonraki kosu kaldigi yerden devam eder). ETA sayaci her ilanda.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
Kullanim: xsell_links.py --mode wallpaper|digital --pod-state STATE.csv --state XSELL.csv --out OUT
          --dry-run|--apply [--limit N] [--quota-min 400]
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
from pod_listing_create import DIGITAL_ORDER  # noqa: E402
from wp_listing_update import norm  # noqa: E402

URL = "https://www.etsy.com/listing/{lid}"
AI_HEAD = {"en": "AI-ASSISTED CREATION DISCLOSURE", "ru": "РАСКРЫТИЕ ОБ ИСПОЛЬЗОВАНИИ ИИ"}
# RU gecisi (Mo 7 Eyl 2026; gercek RU metninden olculdu, ilan 4552211376):
# blok "КАК ЭТО РАБОТАЕТ:" satirinin hemen onune girer; AI beyani ayri bolum degil,
# "ОБРАТИТЕ ВНИМАНИЕ:" listesindeki TEK MADDE silinir (baslik ve diger 3 madde kalir).
RU_ONLY = {
    "anchor": "КАК ЭТО РАБОТАЕТ:",
    "note_head": "ОБРАТИТЕ ВНИМАНИЕ:",
    "note_bullets": 3,
    "head": "ХОТИТЕ ЕГО НА СТЕНЕ?",
    "body": "Тот же дизайн доступен как жикле принт музейного качества на бумаге Hahnemühle Photo Rag 308 г/м² — "
            "печать на заказ, доставка без рамы, 13 размеров:",
    "ai_rx": re.compile(r"^[•\-]\s*Дизайн создан с применением инструментов искусственного интеллекта[^\n]*\n?", re.M),
}

SPEC = {
    "wallpaper": {
        "en": {"after": "HOW IT WORKS", "before": "GOOD TO KNOW", "head": "PREFER IT ON YOUR WALL?",
               "body": "The same design is also available as a museum-quality giclée print, made to order and shipped unframed:"},
        "ru": {"after": "КАК ЭТО РАБОТАЕТ", "before": "ПОЛЕЗНО ЗНАТЬ", "head": "ХОТИТЕ ЕГО НА СТЕНЕ?",
               "body": "Тот же дизайн доступен как жикле принт музейного качества: печать на заказ, доставка без рамы:"},
        "drop_ai": False,
    },
    "digital": {
        "en": {"after": "WHAT YOU WILL RECEIVE", "before": "HOW TO DOWNLOAD", "head": "PREFER IT READY TO HANG?",
               "body": "The same design is also available as a museum-quality giclée print on Hahnemühle Photo Rag 308 gsm — "
                       "made to order, shipped unframed, in 13 sizes:"},
        "ru": {"after": "ЧТО ВЫ ПОЛУЧИТЕ", "before": "КАК СКАЧАТЬ", "head": "ХОТИТЕ ГОТОВЫЙ ПОСТЕР?",
               "body": "Тот же дизайн доступен как жикле принт музейного качества на бумаге Hahnemühle Photo Rag 308 г/м²: "
                       "печать на заказ, доставка без рамы, 13 размеров:"},
        "drop_ai": True,
    },
}


def read_pod_state(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit():
                out[r["pair"]] = r["listing_id"]
    return out


def read_done(path):
    done = {}
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                done[(r.get("mode", ""), r.get("listing_id", ""))] = dict(r)
    return done


def write_done(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        cols = ["mode", "listing_id", "pair", "durum", "not", "ts_utc", "ru_done", "ru_not"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def shop_listings(api, shop, max_pages=12):
    out, offset = [], 0
    for _ in range(max_pages):
        r = api.get(f"/shops/{shop}/listings", params={"state": "active", "limit": 100, "offset": offset}) or {}
        res = r.get("results") or []
        out += [{"listing_id": str(x.get("listing_id")), "title": x.get("title") or "",
                 "section": x.get("shop_section_id")} for x in res]
        if len(res) < 100:
            break
        offset += 100
    return out


def pair_rx(pair):
    s1, s2 = [s.capitalize() for s in pair.split("_", 1)]
    return re.compile(rf"\b{s1}\s+(?:and\s+)?{s2}\b|\b{s2}\s+(?:and\s+)?{s1}\b", re.I)


def targets(listings, pod, mode, pod_ids):
    """-> [(listing_id, pair, baslik)] ; belirsiz eslesmeler atlanir (rapor icin ayrica dondurulur)."""
    hedef, belirsiz = [], []
    for pair, pod_id in sorted(pod.items()):
        rx = pair_rx(pair)
        aday = [x for x in listings if x["listing_id"] not in pod_ids and rx.search(x["title"])]
        if mode == "wallpaper":
            hits = [x for x in aday if re.search(r"wallpaper", x["title"], re.I)]
            if len(hits) == 1:
                hedef.append((hits[0]["listing_id"], pair, hits[0]["title"]))
            else:
                belirsiz.append((pair, f"wallpaper ilani {len(hits)} aday"))
        else:
            for c in DIGITAL_ORDER:
                hits = [x for x in aday if not re.search(r"wallpaper", x["title"], re.I)
                        and re.search(re.escape(c), x["title"], re.I)]
                if len(hits) == 1:
                    hedef.append((hits[0]["listing_id"], pair, hits[0]["title"]))
                else:
                    belirsiz.append((pair, f"{c}: {len(hits)} aday"))
    return hedef, belirsiz


# ------------------------------------------------------------------ metin
def is_head(line):
    t = line.strip()
    return bool(t) and t == t.upper() and len(t) >= 4 and not t.startswith(("•", "-", "http"))


def cut_block(t, head):
    """Basligi ve bir sonraki basliga kadar olan govdesini cikarir -> (metin, vardi_mi)."""
    lines = t.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == head]
    if not idx:
        return t, False
    i = idx[0]
    j = next((k for k in range(i + 1, len(lines)) if is_head(lines[k])), len(lines))
    yeni = lines[:i] + lines[j:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(yeni)).strip(), True


def insert_before(t, head, blok):
    lines = t.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == head]
    if not idx:
        return None
    i = idx[0]
    yeni = lines[:i] + blok.split("\n") + [""] + lines[i:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(yeni)).strip()


def block_text(spec, url):
    return f"{spec['head']}\n{spec['body']}\n{url}"


def transform(text, spec, url, drop_ai, lang):
    """(yeni_metin, hata)."""
    t = norm(text)
    if not t:
        return None, "metin bos"
    for h in (spec["after"], spec["before"]):
        if not any(l.strip() == h for l in t.split("\n")):
            return None, f"'{h}' basligi yok"
    hh = [l.strip() for l in t.split("\n") if is_head(l)]
    if hh.index(spec["before"]) != hh.index(spec["after"]) + 1:
        return None, f"'{spec['after']}' ile '{spec['before']}' ardisik degil"
    x = t
    if drop_ai:
        x, _ = cut_block(x, AI_HEAD[lang])
    x, vardi = cut_block(x, spec["head"])          # bolum zaten varsa yenilenir
    y = insert_before(x, spec["before"], block_text(spec, url))
    if y is None:
        return None, f"'{spec['before']}' basligi kayboldu"
    return y, ""


def base(t, spec, drop_ai, lang):
    x, _ = cut_block(norm(t), spec["head"])
    if drop_ai:
        x, _ = cut_block(x, AI_HEAD[lang])
    return re.sub(r"\n{3,}", "\n\n", x).strip()


def check(old, new, spec, drop_ai, lang):
    sorun = []
    if base(old, spec, drop_ai, lang) != base(new, spec, drop_ai, lang):
        sorun.append("blok/AI bolumu disinda metin degismis")
    hh = [l.strip() for l in norm(new).split("\n") if is_head(l)]
    if hh.count(spec["head"]) != 1:
        sorun.append(f"blok basligi {hh.count(spec['head'])} kez")
    elif hh.index(spec["head"]) != hh.index(spec["before"]):
        pass
    if spec["head"] in hh and spec["before"] in hh and hh.index(spec["head"]) + 1 != hh.index(spec["before"]):
        sorun.append("blok yanlis yerde")
    if drop_ai and AI_HEAD[lang] in hh:
        sorun.append("AI bolumu duruyor")
    return not sorun, sorun


def ru_block(url):
    return [RU_ONLY["head"], RU_ONLY["body"], url]


def ru_cut_block(t):
    """Varsa mevcut capraz satis blogunu (3 satir + izleyen bos satir) cikarir."""
    lines = t.split("\n")
    i = next((k for k, l in enumerate(lines) if l.strip() == RU_ONLY["head"]), None)
    if i is None:
        return t, False
    j = i + 3
    while j < len(lines) and not lines[j].strip():
        j += 1
    yeni = lines[:i] + lines[j:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(yeni)).strip(), True


def ru_base(t):
    """Karsilastirma tabani: blok ve AI maddesi cikarilmis RU metni."""
    x, _ = ru_cut_block(norm(t))
    return re.sub(r"\n{3,}", "\n\n", RU_ONLY["ai_rx"].sub("", x)).strip()


def ru_bullets(t):
    """ОБРАТИТЕ ВНИМАНИЕ: basligindan sonraki madde satirlari."""
    lines = norm(t).split("\n")
    i = next((k for k, l in enumerate(lines) if l.strip() == RU_ONLY["note_head"]), None)
    if i is None:
        return None
    out = []
    for l in lines[i + 1:]:
        if not l.strip():
            break
        out.append(l.strip())
    return out


def ru_transform(text, url):
    """(yeni_metin, hata). Blok capa oncesine girer, AI maddesi silinir; baska hicbir sey degismez."""
    t = norm(text)
    if not t.strip():
        return None, "RU govdesi bos"
    lines = t.split("\n")
    if sum(1 for l in lines if l.strip() == RU_ONLY["anchor"]) != 1:
        return None, f"'{RU_ONLY['anchor']}' capasi bulunamadi/birden fazla"
    if RU_ONLY["note_head"] not in t:
        return None, f"'{RU_ONLY['note_head']}' basligi yok"
    x, _ = ru_cut_block(t)                      # tekrar kosuda blok yenilenir
    x = re.sub(r"\n{3,}", "\n\n", RU_ONLY["ai_rx"].sub("", x)).strip()
    lines = x.split("\n")
    i = next(k for k, l in enumerate(lines) if l.strip() == RU_ONLY["anchor"])
    yeni = lines[:i] + ru_block(url) + [""] + lines[i:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(yeni)).strip(), ""


def ru_check(old, new, url):
    """Bagimsiz dogrulama; -> (ok, sorunlar)."""
    sorun = []
    if ru_base(old) != ru_base(new):
        sorun.append("blok/AI maddesi disinda RU metni degismis")
    lines = norm(new).split("\n")
    idx = [k for k, l in enumerate(lines) if l.strip() == RU_ONLY["head"]]
    if len(idx) != 1:
        sorun.append(f"blok {len(idx)} kez")
    else:
        i = idx[0]
        if lines[i + 1:i + 3] != [RU_ONLY["body"], url]:
            sorun.append("blok govdesi/url beklenen degil")
        elif not (i + 4 < len(lines) and not lines[i + 3].strip() and lines[i + 4].strip() == RU_ONLY["anchor"]):
            sorun.append("blok capanin hemen oncesinde degil")
    if RU_ONLY["ai_rx"].search(norm(new)):
        sorun.append("AI maddesi duruyor")
    b_old, b_new = ru_bullets(old), ru_bullets(new)
    if b_new is None:
        sorun.append("ОБРАТИТЕ ВНИМАНИЕ: basligi kayboldu")
    elif len(b_new) != RU_ONLY["note_bullets"]:
        sorun.append(f"madde sayisi {len(b_new)} (beklenen {RU_ONLY['note_bullets']})")
    elif b_old is not None and [x for x in b_old if not RU_ONLY["ai_rx"].match(x + "\n")] != b_new:
        sorun.append("kalan maddeler degismis")
    return not sorun, sorun


def diff_text(old, new):
    return "\n".join(difflib.unified_diff(norm(old).split("\n"), norm(new).split("\n"), "eski", "yeni", lineterm="", n=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=list(SPEC), required=True)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--state", required=True, help="XSELL STATE (islenen ilanlar; resume)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ru-only", action="store_true",
                    help="yalniz RU gecisi (EN'e dokunulmaz; RU govdesi bos ilan atlanir)")
    ap.add_argument("--quota-min", type=int, default=400)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pod = read_pod_state(a.pod_state)
    done = read_done(a.state)
    spec_en, spec_ru = SPEC[a.mode]["en"], SPEC[a.mode]["ru"]
    drop_ai = SPEC[a.mode]["drop_ai"]

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
    hedef, belirsiz = targets(listings, pod, a.mode, set(pod.values()))
    if a.ru_only:
        kalanlar = [h for h in hedef if (done.get((a.mode, h[0])) or {}).get("ru_done") != "PASS"]
    else:
        kalanlar = [h for h in hedef if (done.get((a.mode, h[0])) or {}).get("durum") not in ("PASS", "DEGISIM YOK")]
    todo = kalanlar[:a.limit] if a.limit else kalanlar
    log(f"aktif ilan {len(listings)} | hedef {len(hedef)} | islenecek {len(todo)} | kota {q0}")

    res, ornek, stopped, rows = [], None, None, []
    for n, (lid, pair, title) in enumerate(todo, 1):
        try:
            rem = int(api.remaining) if api.remaining is not None else None
        except ValueError:
            rem = None
        if rem is not None and rem < a.quota_min:
            stopped = lid
            log(f"KOTA {rem} < {a.quota_min}: {lid} ve sonrasi islenmedi")
            break
        url = URL.format(lid=pod[pair])
        if a.ru_only:
            tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
            eski_desc, eski_title = tru.get("description") or "", tru.get("title") or ""
            eski_tags = [t.strip() for t in (tru.get("tags") or [])]
            if not eski_desc.strip():
                res.append((lid, pair, "ATLANDI", "RU govdesi bos (yazma yok)"))
                rows.append({"mode": a.mode, "listing_id": lid, "pair": pair, "ru_done": "RU YOK",
                             "ru_not": "govde bos", "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
                log(f"[{n}/{len(todo)}] {lid} {pair} ATLANDI (RU govdesi bos)")
                continue
            new_ru, err = ru_transform(eski_desc, url)
            if err:
                res.append((lid, pair, "ATLANDI", f"RU: {err}"))
                log(f"[{n}/{len(todo)}] {lid} {pair} ATLANDI RU: {err}")
                continue
            ok_ru, s_ru = ru_check(eski_desc, new_ru, url)
            if not ok_ru:
                res.append((lid, pair, "SIRA DISI", f"RU: {', '.join(s_ru)}"))
                continue
            if norm(eski_desc) == norm(new_ru):
                res.append((lid, pair, "DEGISIM YOK", "RU zaten guncel"))
                rows.append({"mode": a.mode, "listing_id": lid, "pair": pair, "ru_done": "PASS",
                             "ru_not": "degisim yok", "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
                continue
            if ornek is None:
                ornek = (pair, "(EN'e dokunulmadi)", diff_text(eski_desc, new_ru))
            if a.dry_run:
                res.append((lid, pair, "HAZIR", f"POD {pod[pair]} | RU hazir"))
                log(f"[{n}/{len(todo)}] {lid} {pair} HAZIR (RU dry-run)")
                continue
            body = {"title": eski_title, "description": new_ru, "tags": ",".join(eski_tags)}
            r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru", body)
            back = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
            b_tags = [t.strip() for t in (back.get("tags") or [])]
            ok_back = norm(back.get("description")) == norm(new_ru)
            ok_meta = back.get("title") == eski_title and b_tags == eski_tags
            durum = "PASS" if (ok_back and ok_meta) else "FAIL"
            notu = (f"POD {pod[pair]} | RU {'PASS' if ok_back else 'FAIL'} | "
                    f"baslik/etiket {'korundu' if ok_meta else 'DEGISTI (' + str(len(b_tags)) + ' etiket)'}")
            res.append((lid, pair, durum, notu))
            rows.append({"mode": a.mode, "listing_id": lid, "pair": pair, "ru_done": durum, "ru_not": notu,
                         "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
            el = time.time() - t0
            log(f"[{n}/{len(todo)}] {lid} {pair} {durum} (RU) | gecen {el:.0f}s "
                f"kalan~{el / n * (len(todo) - n):.0f}s %{100 * n // len(todo)} | kota {api.remaining}")
            continue
        L = api.get(f"/listings/{lid}") or {}
        tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        new_en, err = transform(L.get("description") or "", spec_en, url, drop_ai, "en")
        if err:
            res.append((lid, pair, "ATLANDI", f"EN: {err}"))
            log(f"[{n}/{len(todo)}] {lid} {pair} ATLANDI EN: {err}")
            continue
        ok_en, s_en = check(L.get("description"), new_en, spec_en, drop_ai, "en")
        if not ok_en:
            res.append((lid, pair, "SIRA DISI", f"EN: {', '.join(s_en)}"))
            continue
        new_ru, ru_note = None, "RU cevirisi yok"
        if (tru.get("description") or "").strip():
            new_ru, err_ru = transform(tru["description"], spec_ru, url, drop_ai, "ru")
            if err_ru:
                new_ru, ru_note = None, f"RU atlandi ({err_ru})"
            else:
                ok_ru, s_ru = check(tru["description"], new_ru, spec_ru, drop_ai, "ru")
                if not ok_ru:
                    new_ru, ru_note = None, f"RU atlandi ({', '.join(s_ru)})"
                else:
                    ru_note = "RU guncellendi"
        degisim = norm(L.get("description")) != norm(new_en) or (new_ru and norm(tru.get("description")) != norm(new_ru))
        if not degisim:
            res.append((lid, pair, "DEGISIM YOK", ru_note))
            rows.append({"mode": a.mode, "listing_id": lid, "pair": pair, "durum": "DEGISIM YOK", "not": ru_note,
                         "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
            continue
        if ornek is None:
            ornek = (pair, diff_text(L.get("description"), new_en), diff_text(tru.get("description"), new_ru) if new_ru else "(RU yok)")
        if a.dry_run:
            res.append((lid, pair, "HAZIR", f"POD {pod[pair]} | {ru_note}"))
            log(f"[{n}/{len(todo)}] {lid} {pair} HAZIR | {ru_note}")
            continue
        r = api.patch(f"/shops/{shop}/listings/{lid}", {"description": new_en})
        back_en = r if isinstance(r, dict) and r.get("description") else (api.get(f"/listings/{lid}") or {})
        p_en = norm(back_en.get("description")) == norm(new_en)
        p_ru = True
        if new_ru is not None:
            body = {"title": tru.get("title") or "", "description": new_ru, "tags": ",".join(tru.get("tags") or [])}
            r = api.put(f"/shops/{shop}/listings/{lid}/translations/ru", body)
            back_ru = r if isinstance(r, dict) and r.get("description") else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
            p_ru = (norm(back_ru.get("description")) == norm(new_ru) and back_ru.get("title") == tru.get("title")
                    and [t.strip() for t in (back_ru.get("tags") or [])] == [t.strip() for t in (tru.get("tags") or [])])
        durum = "PASS" if (p_en and p_ru) else "FAIL"
        res.append((lid, pair, durum, f"POD {pod[pair]} | EN {'PASS' if p_en else 'FAIL'} | {ru_note}"))
        rows.append({"mode": a.mode, "listing_id": lid, "pair": pair, "durum": durum, "not": ru_note,
                     "ts_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
        el = time.time() - t0
        log(f"[{n}/{len(todo)}] {lid} {pair} {durum} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s "
            f"%{100 * n // len(todo)} | kota {api.remaining}")

    if a.apply:
        birlesik = {k: dict(v) for k, v in done.items()}
        for r in rows:
            k = (r["mode"], r["listing_id"])
            birlesik.setdefault(k, {})
            birlesik[k].update({kk: vv for kk, vv in r.items() if vv != ""})
        write_done(a.state, list(birlesik.values()))
    islenen = [r for r in res if r[2] in ("PASS", "HAZIR")]
    bad = [r for r in res if r[2] in ("FAIL", "ATLANDI", "SIRA DISI")]
    kalan = len(kalanlar) - len(res)
    md = [f"## Capraz satis — {a.mode.upper()}{' / RU' if a.ru_only else ''} ({'APPLY' if a.apply else 'DRY-RUN'})", "",
          f"- hedef {len(hedef)}; islenen {len(res)}; guncellenen {len(islenen)}; "
          f"degisim yok {sum(1 for r in res if r[2] == 'DEGISIM YOK')}; atlanan/sorunlu {len(bad)}; kalan {kalan}"
          + (f" (kota {api.remaining} < {a.quota_min}, {stopped} ve sonrasi)" if stopped else ""),
          f"- cift eslesmeyen: {len(belirsiz)}" + (f" — {', '.join(f'{p}: {n}' for p, n in belirsiz[:8])}" if belirsiz else ""), ""]
    if ornek:
        md += [f"### Ornek diff ({ornek[0]})", "", "```diff", ornek[1], "```", "```diff", ornek[2], "```", ""]
    if bad:
        md += ["### Atlanan / sorunlu", "", "| listing_id | cift | durum | neden |", "|---|---|---|---|"]
        md += [f"| {l} | {p} | {s} | {d} |" for l, p, s, d in bad] + [""]
    md += [f"- Kota once {q0} / sonra {api.remaining}"]
    text = "\n".join(md)
    log(text)
    (out / f"XSELL_{a.mode.upper()}_REPORT.md").write_text(text + "\n", encoding="utf-8")
    (out / f"xsell_{a.mode}_result.json").write_text(json.dumps(
        {"rows": res, "belirsiz": belirsiz, "kalan": kalan, "quota": [q0, api.remaining]}, indent=1, ensure_ascii=False), encoding="utf-8")
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        open(p, "a", encoding="utf-8").write(text + "\n")
    if [r for r in res if r[2] == "FAIL"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
