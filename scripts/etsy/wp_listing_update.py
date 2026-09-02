#!/usr/bin/env python3
"""
Wallpaper ilanlari: baslik + tag + aciklama guncellemesi, EN ve RU katmani.

Kaynak sablon: docs/WP_LISTING_TEMPLATE.md (EN/RU aciklama bloklari oradan
okunur; baslik sablonu ve tag setleri asagida sabittir ve dokumanla aynidir).

Kullanim:
  wp_listing_update.py --state state.csv --out out.csv --layer all --lang en --dry-run
  wp_listing_update.py --state state.csv --out out.csv --layer all --lang en --apply   # ONAY SONRASI
  --layer  title | tags | description | all
  --lang   en | ru | both

EN katmani: updateListing (PATCH /shops/{shop}/listings/{id}).
RU katmani: listing translation (GET/PUT/POST .../translations/ru).
Dry-run hicbir yazma cagrisi yapmaz. Apply idempotenttir: alan zaten
hedef degerdeyse gonderilmez; her yazmadan sonra geri okuma dogrulamasi.

Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE,
GITHUB_STEP_SUMMARY (istege bagli).
"""
import argparse
import csv
import html
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_MD = REPO_ROOT / "docs" / "WP_LISTING_TEMPLATE.md"

MAX_TITLE = 140
MAX_TAG = 20
N_TAGS = 13

TITLE_EN = ("{Sign1} {Sign2} Matching Couple Wallpaper, 4 Colors, "
            "Phone Tablet Desktop Watch, Zodiac Digital Download")
TAGS_EN = ["{pair}", "matching wallpaper", "couple wallpaper", "zodiac wallpaper",
           "zodiac compatibility", "couple lock screen", "phone wallpaper set",
           "desktop wallpaper", "tablet wallpaper", "watch wallpaper",
           "astrology couple", "long distance couple", "gift for couple"]

TITLE_RU = ("{Sign1RU} {Sign2RU} парные обои для пары, 4 цвета, "
            "телефон планшет компьютер часы, зодиак цифровое скачивание")
TAGS_RU = ["{pair}", "парные обои", "обои для пары", "обои зодиак",
           "совместимость знаков", "экран блокировки", "обои на телефон",
           "обои на компьютер", "обои на планшет", "обои на часы",
           "астрология пара", "любовь на расстоянии", "подарок паре"]

SIGN_RU = {"Aquarius": "Водолей", "Aries": "Овен", "Taurus": "Телец",
           "Gemini": "Близнецы", "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
           "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
           "Capricorn": "Козерог", "Pisces": "Рыбы"}


# ------------------------------------------------------------------ sablon
def load_block(md_text, name):
    m = re.search(rf"<!-- {name}_BEGIN -->\n(.*?)\n<!-- {name}_END -->", md_text, re.S)
    if not m:
        raise SystemExit(f"HATA: {TEMPLATE_MD} icinde {name} blogu yok.")
    return m.group(1).strip()


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                rows.append((raw[0].strip(), raw[1].strip()))
    return rows


def pair_tag(s1, s2, lang):
    """Cift tag'i; 20'yi asarsa '<sign1> love' (EN) / '<sign1> любовь' (RU)."""
    t = f"{s1} {s2}".lower()
    if len(t) <= MAX_TAG:
        return t, ""
    short = f"{s1} love".lower() if lang == "en" else f"{s1} любовь".lower()
    return short, f"{t} ({len(t)}) -> {short}"


def build(pair, lang, desc_tpl):
    s1, s2 = pair.split("_", 1)
    S1, S2 = s1.capitalize(), s2.capitalize()
    if lang == "en":
        title = TITLE_EN.format(Sign1=S1, Sign2=S2)
        ptag, note = pair_tag(S1, S2, "en")
        tags = [t.format(pair=ptag) for t in TAGS_EN]
        desc = desc_tpl.format(Sign1=S1, Sign2=S2)
    else:
        R1, R2 = SIGN_RU[S1], SIGN_RU[S2]
        title = TITLE_RU.format(Sign1RU=R1, Sign2RU=R2)
        ptag, note = pair_tag(R1, R2, "ru")
        tags = [t.format(pair=ptag) for t in TAGS_RU]
        desc = desc_tpl.format(Sign1RU=R1, Sign2RU=R2)
    return title, tags, desc, note


def validate(title, tags):
    """Kural ihlallerini metin olarak dondurur (bos = temiz)."""
    issues = []
    if len(title) > MAX_TITLE:
        issues.append(f"baslik {len(title)}>{MAX_TITLE}")
    if len(tags) != N_TAGS:
        issues.append(f"tag sayisi {len(tags)}")
    if len(set(tags)) != len(tags):
        issues.append("yinelenen tag")
    over = [t for t in tags if len(t) > MAX_TAG]
    if over:
        issues.append("tag>20: " + ",".join(over))
    return "; ".join(issues)


def norm(s):
    """Etsy aciklamayi HTML kacisli dondurur (&quot; &#39; &amp;); karsilastirma
    oncesi cozulur, satir sonu bosluklari atilir."""
    s = html.unescape(s or "").replace("\r\n", "\n")
    return "\n".join(line.rstrip() for line in s.split("\n")).strip()


def tags_of(obj):
    return [t.strip().lower() for t in (obj.get("tags") or []) if t and t.strip()]


def readback(api, path, expect, tries=3, wait=10):
    """Yazma sonrasi geri okuma; bayat okumaya karsi (B68) esitlik saglanana
    kadar en fazla `tries` kez, `wait` sn arayla tekrar okur. Donus:
    (son_kayit, {alan: bool})."""
    back, ok = {}, {}
    for i in range(tries):
        back = api.get(path) or {}
        ok = {}
        if "title" in expect:
            ok["title"] = (back.get("title") == expect["title"])
        if "tags" in expect:
            ok["tags"] = (tags_of(back) == expect["tags"])
        if "description" in expect:
            ok["description"] = (norm(back.get("description")) == norm(expect["description"]))
        if all(ok.values()):
            break
        if i < tries - 1:
            time.sleep(wait)
    return back, ok


# ------------------------------------------------------------------ katmanlar
def process_en(api, shop_id, pair, lid, layers, desc_tpl, apply):
    cur = api.get(f"/listings/{lid}")
    title, tags, desc, note = build(pair, "en", desc_tpl)
    old_title, old_tags, old_desc = cur.get("title") or "", tags_of(cur), cur.get("description") or ""
    payload = {}
    if "title" in layers and old_title != title:
        payload["title"] = title
    if "tags" in layers and old_tags != tags:
        payload["tags"] = tags
    if "description" in layers and norm(old_desc) != norm(desc):
        payload["description"] = desc
    status = "DEGISIM_YOK" if not payload else "PLANLANDI"
    if apply and payload:
        body = dict(payload)
        if "tags" in body:
            # Etsy v3 updateListing: tags VIRGULLU TEK METIN. Tekrar eden form
            # anahtari gonderilirse yalniz sonuncusu kalir (2 Eyl 2026 dersi).
            body["tags"] = ",".join(body["tags"])
        api.patch(f"/shops/{shop_id}/listings/{lid}", body)
        _, ok = readback(api, f"/listings/{lid}", payload)
        status = "PASS" if all(ok.values()) else "FAIL(" + ",".join(k for k, v in ok.items() if not v) + ")"
    return dict(lang="en", pair=pair, listing_id=lid, state=cur.get("state"),
                old_title_len=len(old_title), new_title=title, new_title_len=len(title),
                n_tags=len(tags), tag_issue=validate(title, tags), pair_tag_note=note,
                title_change="title" in payload, tags_change="tags" in payload,
                desc_change="description" in payload, desc_len=len(desc),
                old_title=old_title, old_tags="|".join(old_tags), new_tags="|".join(tags),
                status=status)


def process_ru(api, shop_id, pair, lid, layers, desc_tpl, apply):
    path = f"/shops/{shop_id}/listings/{lid}/translations/ru"
    cur = api.get(path, ok404=True)
    exists = cur is not None
    cur = cur or {}
    title, tags, desc, note = build(pair, "ru", desc_tpl)
    old_title, old_tags, old_desc = cur.get("title") or "", tags_of(cur), cur.get("description") or ""
    changed = {}
    if "title" in layers and old_title != title:
        changed["title"] = title
    if "tags" in layers and old_tags != tags:
        changed["tags"] = tags
    if "description" in layers and norm(old_desc) != norm(desc):
        changed["description"] = desc
    status = "DEGISIM_YOK" if not changed else ("PLANLANDI" if exists else "PLANLANDI_YENI")
    if apply and changed:
        # Ceviri kaydi butun olarak yazilir: degismeyen alanlar mevcut degerle,
        # mevcut deger yoksa yeni degerle doldurulur.
        full = dict(title=changed.get("title", old_title or title),
                    description=changed.get("description", old_desc or desc),
                    tags=changed.get("tags", old_tags or tags))
        body = dict(full, tags=",".join(full["tags"]))
        if exists:
            api.put(path, body)
        else:
            api.post(path, body)
        _, ok = readback(api, path, full)
        status = "PASS" if all(ok.values()) else "FAIL(" + ",".join(k for k, v in ok.items() if not v) + ")"
    return dict(lang="ru", pair=pair, listing_id=lid, state="translation" if exists else "yok",
                old_title_len=len(old_title), new_title=title, new_title_len=len(title),
                n_tags=len(tags), tag_issue=validate(title, tags), pair_tag_note=note,
                title_change="title" in changed, tags_change="tags" in changed,
                desc_change="description" in changed, desc_len=len(desc),
                old_title=old_title, old_tags="|".join(old_tags), new_tags="|".join(tags),
                status=status)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layer", choices=["title", "tags", "description", "all"], default="all")
    ap.add_argument("--lang", choices=["en", "ru", "both"], default="en")
    ap.add_argument("--template", default=str(TEMPLATE_MD))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    layers = {"title", "tags", "description"} if a.layer == "all" else {a.layer}
    langs = ["en", "ru"] if a.lang == "both" else [a.lang]

    md = Path(a.template).read_text(encoding="utf-8")
    desc_en = load_block(md, "EN_DESCRIPTION")
    desc_ru = load_block(md, "RU_DESCRIPTION")

    keystring = os.environ.get("ETSY_API_KEY", "")
    shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    if not shop_id:
        raise SystemExit("HATA: ETSY_SHOP_ID tanimli degil.")
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    rows = read_state(a.state)
    mode = "APPLY" if a.apply else "DRY-RUN"
    log(f"{len(rows)} ilan | katman {sorted(layers)} | dil {langs} | mod {mode}")
    results = []
    for pair, lid in rows:
        for lang in langs:
            fn = process_en if lang == "en" else process_ru
            r = fn(api, shop_id, pair, lid, layers, desc_en if lang == "en" else desc_ru, a.apply)
            results.append(r)
            log(f"{lang} {pair} {lid}: {r['status']} "
                f"T={int(r['title_change'])} G={int(r['tags_change'])} D={int(r['desc_change'])}"
                f"{' | ' + r['tag_issue'] if r['tag_issue'] else ''}"
                f"{' | ' + r['pair_tag_note'] if r['pair_tag_note'] else ''}")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)

    md_out = [f"## Wallpaper ilan guncelleme ({mode}, katman={a.layer}, dil={a.lang})", "",
              f"satir {len(results)} | baslik degisecek {sum(r['title_change'] for r in results)} | "
              f"tag degisecek {sum(r['tags_change'] for r in results)} | aciklama degisecek "
              f"{sum(r['desc_change'] for r in results)} | ihlal {sum(1 for r in results if r['tag_issue'])} | "
              f"api cagri {api.calls} | kalan kota {api.remaining}", "",
              "| # | dil | id | cift | eski baslik uz. | yeni baslik | tag | ihlal | cift tag notu | T/G/D | durum |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        md_out.append(f"| {i} | {r['lang']} | {r['listing_id']} | {r['pair']} | {r['old_title_len']} | "
                      f"{r['new_title']} | {r['n_tags']} | {r['tag_issue'] or '-'} | {r['pair_tag_note'] or '-'} | "
                      f"{int(r['title_change'])}/{int(r['tags_change'])}/{int(r['desc_change'])} | {r['status']} |")
    text = "\n".join(md_out)
    log(text)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if any(r["status"].startswith("FAIL") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
