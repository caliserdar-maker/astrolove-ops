#!/usr/bin/env python3
"""
POD (Prodigi poster) YENI ILAN olusturma: createDraftListing + 10 gorsel +
Color(5) x Size(13) = 65 varyant + renk secenegine edisyon 01 karesi - 6 Eyl 2026.
SKU: POD-<burc3>_<burc3>-<edisyon2>-<boyut> (pod_sku.py; Etsy 32 karakter siniri).

Kaynaklar:
  - baslik/tag/aciklama: docs/POD_LISTING_TEMPLATE.md (+ TITLE sablonu asagida)
  - 13 boyut fiyati: scripts/etsy/pod_prices.csv (size,price; USD, tum edisyonlarda ayni); bos fiyat -> apply reddedilir
  - gorseller: <images>/<PAIR>/<ED>/NN_*.jpg (Drive TEMP/POD_GALLERY/<PAIR>, 78 cift)
  - EK 3 (6 Eyl): <media>/<PAIR>/ teknik kartlar (WA_02 Symbol Story .png, WA_05 Crafted Detail .jpg) + V01 video
    (LISTING_MEDIA/TECHNICAL, VIDEOS; ana edisyon). Galeri 12: 1 hero, 2-3 sahne, 4 Symbol, 5 Crafted,
    6 Paper, 7 Sizes, 8 Care, 9-12 diger edisyon hero; video 1 (1080x1350). Kart OCR on kontrolu
    (dijitale ozgu ifade -> kart atlanir); dosya eksikse cift "eksik" ile raporlanir, kosu durmaz.
  - API'den okunur (tahmin yok): kargo profili, bolum, production partner (Prodigi),
    iade politikasi, taxonomy (Prints > Giclee), varyasyon property id'leri.

Kullanim:
  pod_listing_create.py --pairs ARIES_LEO --images IMG --state STATE.csv --out OUT --dry-run
  pod_listing_create.py --pairs ARIES_LEO --images IMG --state STATE.csv --out OUT --apply   # ONAY SONRASI
  --pairs A_B,C_D | --pairs-file dosya (satir basina cift) ; --limit N (0 = hepsi)

Dry-run HICBIR yazma cagrisi yapmaz: kesif tablosu + ilan basina payload JSON.
Apply: kargo profili / bolum yoksa olusturur; ilan basina asama asama STATE'e yazar
(resume); kota 400 altinda yeni ilana baslamaz. Ortam: ETSY_API_KEY,
ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, GITHUB_STEP_SUMMARY (istege bagli).
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from pod_listing_update import SIGNS, build as build_text, load_template  # noqa: E402
from pod_sku import make_sku  # noqa: E402
from pod_media import CARD_FILES, VIDEO_WH, card_path, mp4_dims, precheck_card, video_path  # noqa: E402
from pod_listing_update import TEMPLATE_MD  # noqa: E402
from wp_listing_update import load_block  # noqa: E402
from wp_listing_update import norm, tags_of, validate  # noqa: E402

HERE = Path(__file__).resolve().parent
PRICES_CSV = HERE / "pod_prices.csv"
MAX_TITLE = 140
QUOTA_MIN = 400
QUANTITY = 999
MAX_IMAGES = 12          # EK 3 (6 Eyl): 10 kare + 2 teknik kart
CARDS_AFTER = 3          # kartlar ana edisyonun ilk 3 karesinden sonra (rank 4-5)

TITLE = "{S1} and {S2} Zodiac Wall Art, Couple Compatibility Giclée Print, Unframed Fine Art Poster, Gift for Couples"
EDITIONS = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
ED_NAME = {"MIDNIGHT_BLUE": "Midnight Blue", "DEEP_BLACK": "Deep Black", "WARM_PARCHMENT": "Warm Parchment",
           "CHAMPAGNE_IVORY": "Champagne Ivory", "PURE_WHITE": "Pure White"}
# Mo 6 Eyl (Size etiketi v3): oran once, cm tam sayi; SIRA oran gruplari 4:5, 3:4, 2:3, 11:14, A-series.
# Tek kaynak: SIZE_SPEC -> SIZES (sira), SIZE_LABEL (varyasyon degeri), size_block() (aciklama blogu EN/RU).
SIZE_SPEC = [  # (anahtar, grup, inc metni, cm metni)
    ("8x10", "4:5", "8x10 in", "20×25"), ("16x20", "4:5", "16x20 in", "41×51"),
    ("12x16", "3:4", "12x16 in", "30×41"), ("18x24", "3:4", "18x24 in", "46×61"), ("30x40", "3:4", "30x40 in", "76×102"),
    ("12x18", "2:3", "12x18 in", "30×46"), ("16x24", "2:3", "16x24 in", "41×61"), ("20x30", "2:3", "20x30 in", "51×76"),
    ("24x36", "2:3", "24x36 in", "61×91"),
    ("11x14", "11:14", "11x14 in", "28×36"),
    ("A4", "A-series", "A4", "21×30"), ("A3", "A-series", "A3", "30×42"), ("A2", "A-series", "A2", "42×59"),
]
SIZES = [k for k, *_ in SIZE_SPEC]
SIZE_LABEL = {k: f"{g} · {inc} ({cm} cm)" for k, g, inc, cm in SIZE_SPEC}     # or. "4:5 · 8x10 in (20×25 cm)"
GROUP_ORDER = ["4:5", "3:4", "2:3", "11:14", "A-series"]
SIZE_BLOCK_TXT = {"en": {"head": "✦ 13 SIZES (choose from the Size menu)", "ratio": "Ratio {g}", "a": "A-series (ISO)", "cm": "cm",
                         "tail": "Not sure? See the size guide photo."},
                  "ru": {"head": "✦ 13 РАЗМЕРОВ (выберите в меню Size)", "ratio": "Соотношение {g}", "a": "Серия A (ISO)", "cm": "см",
                         "tail": "Не уверены? Смотрите фото с таблицей размеров."}}


def size_block(lang="en"):
    """Aciklamadaki '✦ 13 SIZES' blogu (EN/RU); docs/POD_LISTING_TEMPLATE.md ile birebir ayni olmali (test)."""
    t = SIZE_BLOCK_TXT[lang]
    out = [t["head"]]
    for g in GROUP_ORDER:
        out += ["", t["a"] if g == "A-series" else t["ratio"].format(g=g)]
        out += [f"{inc} — {cm} {t['cm']}" for k, gg, inc, cm in SIZE_SPEC if gg == g]
    out += ["", t["tail"]]
    return "\n".join(out)


MATERIALS = ["Hahnemuhle Photo Rag 308 gsm cotton paper", "archival pigment ink"]
WHO_MADE = "i_did"                # Mo 6 Eyl: tasarim bize ait; uretim partneri Prodigi (production_partner_ids)
AUTO_RENEW = True
# Ilan ozellikleri (taxonomy 121 property adi -> deger adi); id'ler API possible_values'tan eslenir, tahmin yok
# Orientation: Etsy secenekleri Horizontal/Round/Square/Vertical (6 Eyl dry-run); "Portrait" karsiligi Vertical.
ATTRS = {"Orientation": "Vertical", "Framing": "Unframed", "Number of pieces included": "1", "Material multi": "Paper"}
# RU katmani (docs/POD_LISTING_TEMPLATE.md ile ayni)
TITLE_RU = "{S1RU} и {S2RU} зодиак постер, совместимость пары, жикле принт без рамы, подарок паре"
TAGS_RU = ["зодиак постер", "{pair}", "совместимость пары", "астрология декор", "подарок паре зодиак", "подарок на годовщину",
           "постер знак зодиака", "декор для пары", "подарок астрологу", "минимализм постер", "арт принт", "свадебный подарок", "небесный декор"]
SIGN_RU = {"Aquarius": "Водолей", "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы", "Cancer": "Рак", "Leo": "Лев",
           "Virgo": "Дева", "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец", "Capricorn": "Козерог", "Pisces": "Рыбы"}
# Hunspell ru_RU disinda kalan gecerli terimler (6 Eyl olcumu): ЕС kisaltma, dizayn cogulu, giclee cevriyazisi,
# minimalistichnyi/neotrazhayushchaya turetilmis sifatlar, print odunc sozcuk
RU_SPELL_OK = {"ес", "дизайны", "жикле", "минималистичный", "неотражающая", "принт"}

SHIPPING_TITLE = "POD Prints – Free Shipping"
SECTION_TITLE = "Zodiac Fine Art Prints"
PARTNER_NAME = "prodigi"
TAXONOMY_PATH = ["prints", "giclée"]           # ust dugum adi 'Prints', yaprak 'Giclée' (giclee de kabul)

# 10 gorsel/ilan siniri: ana edisyonun 6 karesi + diger 4 edisyonun 01 karesi (renk secenegine baglanir)
DEFAULT_FRAMES = "01,02,03,05,08,10"
STAGES = ["created", "images", "video", "fields", "inventory", "variation_images", "verified"]


# ------------------------------------------------------------------ girdi
def read_prices(path=PRICES_CSV):
    prices, missing = {}, []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            s = (r.get("size") or "").strip()
            v = (r.get("price") or r.get("price_usd") or "").strip()
            if not s:
                continue
            if not v:
                missing.append(s)
                continue
            prices[s] = round(float(v), 2)
    for s in SIZES:
        if s not in prices and s not in missing:
            missing.append(s)
    return prices, missing


def find_frame(img_root, pair, ed, no):
    d = Path(img_root) / pair / ed
    hits = sorted(d.glob(f"{no}_*.jpg")) if d.exists() else []
    return hits[0] if hits else None


def media_plan(media_root, pair, ed):
    """Teknik kartlar + video (EK 3): {'SYMBOL','CRAFTED','VIDEO': yol|None, '<K>_file','<K>_words','<K>_hits','<K>_note'}.
    On kontrol: kart OCR'inde dijitale ozgu ifade varsa kart plana girmez (yol None, not yazilir)."""
    m = {}
    for k in CARD_FILES:
        p = card_path(media_root, pair, ed, k) if media_root else None
        m[k + "_file"] = p; m[k + "_words"] = None; m[k + "_hits"] = None; m[k + "_note"] = "" if p else "dosya yok"
        if p is not None:
            n, hits = precheck_card(p)
            m[k + "_words"], m[k + "_hits"] = n, hits
            if hits:
                m[k + "_note"] = f"yasakli ifade {hits}"; p = None
            elif n is None:
                m[k + "_note"] = "OCR yok (tesseract)"; p = None
        m[k] = p
    v = video_path(media_root, pair, ed) if media_root else None
    m["VIDEO_file"] = v; m["VIDEO_note"] = "" if v else "dosya yok"
    if v is not None:
        d = mp4_dims(v)
        if d != VIDEO_WH:
            m["VIDEO_note"] = f"boyut {d} != {VIDEO_WH}"; v = None
    m["VIDEO"] = v
    return m


def media_missing(media):
    return [f"{k}: {media.get(k + '_note') or 'yok'}" for k in ("SYMBOL", "CRAFTED", "VIDEO") if media.get(k) is None]


def image_plan(img_root, pair, primary, frames, media=None):
    """[(rank, edisyon, dosya|None, renk_karesi_mi, kare)] - 12'ye kadar (EK 3 duzeni):
    ana edisyon ilk 3 kare, SYMBOL, CRAFTED, kalan ana kareler (Paper/Sizes/Care), diger edisyon 01'leri.
    Kart yoksa (media None ya da on kontrol FAIL) atlanir, ranklar sikisir (10 kare)."""
    items = []
    for i, no in enumerate(frames):
        if i == CARDS_AFTER:
            for k in ("SYMBOL", "CRAFTED"):
                if media and media.get(k):
                    items.append((primary, media[k], False, k))
        items.append((primary, find_frame(img_root, pair, primary, no), no == "01", f"frame{no}"))
    for ed in EDITIONS:
        if ed == primary:
            continue
        items.append((ed, find_frame(img_root, pair, ed, "01"), True, "frame01"))
    plan = [(i + 1, ed, p, c, k) for i, (ed, p, c, k) in enumerate(items)]
    if len(plan) > MAX_IMAGES:
        raise SystemExit(f"HATA: gorsel plani {len(plan)} > {MAX_IMAGES}")
    return plan


def build_listing(pair, desc_tpl):
    s1, s2 = pair.split("_", 1)
    S1, S2 = s1.capitalize(), s2.capitalize()
    tags, desc, note = build_text(pair, desc_tpl)
    title = TITLE.format(S1=S1, S2=S2)
    issue = validate(title, tags)
    if issue:
        raise SystemExit(f"HATA: {pair}: {issue}")
    return title, tags, desc, note


def load_ru_template():
    return load_block(TEMPLATE_MD.read_text(encoding="utf-8"), "RU_DESCRIPTION")


def build_ru(pair, ru_tpl):
    s1, s2 = pair.split("_", 1)
    R1, R2 = SIGN_RU[s1.capitalize()], SIGN_RU[s2.capitalize()]
    ptag = f"{R1} {R2} постер".lower()
    note = ""
    if len(ptag) > 20:
        note = f"{ptag} ({len(ptag)}) -> {R1.lower()} постер"
        ptag = f"{R1} постер".lower()
    tags = [t.format(pair=ptag) for t in TAGS_RU]
    title = TITLE_RU.format(S1RU=R1, S2RU=R2)
    desc = ru_tpl.replace("{PAIR_RU}", f"{R1} и {R2}").replace("{S1RU}", R1).replace("{S2RU}", R2)
    left = re.findall(r"\{[A-Za-z0-9_]+\}", desc)
    if left:
        raise SystemExit(f"HATA: RU aciklamada doldurulmamis yer tutucu: {left}")
    issue = validate(title, tags)
    if issue:
        raise SystemExit(f"HATA: RU {pair}: {issue}")
    return title, tags, desc, note


def spellcheck_ru(ru_dict, texts):
    """Hunspell ru_RU (spylls). Bilinmeyen kelime (RU_SPELL_OK disinda) -> HATA."""
    try:
        from spylls.hunspell import Dictionary
    except ImportError:
        raise SystemExit("HATA: spylls yok (pip install spylls)")
    d = Dictionary.from_files(str(ru_dict))
    words = sorted({w for t in texts for w in re.findall(r"[А-Яа-яЁё]+", t)})
    bad = [w for w in words if w.lower() not in RU_SPELL_OK and not (d.lookup(w) or d.lookup(w.lower()) or d.lookup(w.capitalize()))]
    if bad:
        raise SystemExit(f"HATA: RU yazim denetimi bilinmeyen kelime: {bad}")
    log(f"RU yazim denetimi: {len(words)} kelime, PASS")


def inventory_body(pair, prices, color_pid, size_pid, color_name, size_name, readiness_state_id=None):
    """Etsy updateListingInventory: her offering'de readiness_state_id zorunlu (6 Eyl 400: "All offerings need readiness state")."""
    products = []
    for ed in EDITIONS:
        for sz in SIZES:
            off = {"price": prices.get(sz, 0), "quantity": QUANTITY, "is_enabled": True}
            if readiness_state_id:
                off["readiness_state_id"] = readiness_state_id
            products.append({
                "sku": make_sku(pair, ed, sz),                 # <= 32 karakter (Etsy; 9. kosu 400)
                "property_values": [
                    {"property_id": color_pid, "property_name": color_name, "values": [ED_NAME[ed]]},
                    {"property_id": size_pid, "property_name": size_name, "values": [SIZE_LABEL[sz]]},
                ],
                "offerings": [off],
            })
    # Etsy (6 Eyl 400): sku_on_property iki ozellige bagliyken price_on_property bos ya da iki ozellik olmali;
    # fiyat boyuta gore degisir, renkler arasi aynidir -> (renk, boyut) ciftine baglanir.
    return {"products": products, "price_on_property": [color_pid, size_pid], "quantity_on_property": [],
            "sku_on_property": [color_pid, size_pid]}


# ------------------------------------------------------------------ kesif (salt okur)
def _walk(nodes, path, out):
    for n in nodes or []:
        p = path + [(n.get("name") or "")]
        out.append((n.get("id"), p))
        _walk(n.get("children") or [], p, out)


def find_taxonomy(tree):
    flat = []
    _walk(tree.get("results") or [], [], flat)
    want_parent, want_leaf = TAXONOMY_PATH
    leafs = {"giclée", "giclee", "giclée prints", "giclee prints"}
    hits = [(i, p) for i, p in flat if p and p[-1].lower() in leafs and any(want_parent == x.lower() for x in p[:-1])]
    if not hits:
        hits = [(i, p) for i, p in flat if p and p[-1].lower() in leafs]
    return hits


def discover(api, shop, return_policy_id=""):
    d = {}
    sp = (api.get(f"/shops/{shop}/shipping-profiles") or {}).get("results") or []
    d["shipping_profiles"] = [(x.get("shipping_profile_id"), x.get("title")) for x in sp]
    d["shipping_profile_id"] = next((x.get("shipping_profile_id") for x in sp if (x.get("title") or "").strip().lower() == SHIPPING_TITLE.lower()), None)
    sec = (api.get(f"/shops/{shop}/sections") or {}).get("results") or []
    d["sections"] = [(x.get("shop_section_id"), x.get("title")) for x in sec]
    d["shop_section_id"] = next((x.get("shop_section_id") for x in sec if (x.get("title") or "").strip().lower() == SECTION_TITLE.lower()), None)
    pp = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    d["partners"] = [(x.get("production_partner_id"), x.get("partner_name"), x.get("location")) for x in pp]
    d["production_partner_id"] = next((x.get("production_partner_id") for x in pp if PARTNER_NAME in (x.get("partner_name") or "").lower()), None)
    rp = (api.get(f"/shops/{shop}/policies/return") or {}).get("results") or []
    d["return_policies"] = [(x.get("return_policy_id"), x.get("accepts_returns"), x.get("accepts_exchanges"), x.get("return_deadline")) for x in rp]
    if return_policy_id:
        d["return_policy_id"] = int(return_policy_id)
    else:
        d["return_policy_id"] = rp[0].get("return_policy_id") if len(rp) == 1 else None
    d["return_policy_spec"] = None
    rs = (api.get(f"/shops/{shop}/readiness-state-definitions") or {}).get("results") or []
    d["readiness_states"] = [(x.get("readiness_state_id"), x.get("readiness_state"), x.get("min_processing_days"), x.get("max_processing_days")) for x in rs]
    d["readiness_state_id"] = next((x.get("readiness_state_id") for x in rs if x.get("readiness_state") == "made_to_order"
                                    and (x.get("min_processing_days"), x.get("max_processing_days")) == (PROC_MIN, PROC_MAX)), None)
    tax = find_taxonomy(api.get("/seller-taxonomy/nodes") or {})
    d["taxonomy_hits"] = [(i, " > ".join(p)) for i, p in tax]
    d["taxonomy_id"] = tax[0][0] if len(tax) == 1 else None
    d["color_pid"] = d["size_pid"] = d["color_name"] = d["size_name"] = None
    if d["taxonomy_id"]:
        props = (api.get(f"/seller-taxonomy/nodes/{d['taxonomy_id']}/properties") or {}).get("results") or []
        d["properties"] = [(p.get("property_id"), p.get("name"), p.get("supports_variations")) for p in props]
        d["attr_plan"], d["attr_missing"] = [], []
        for pname, vname in ATTRS.items():
            prop = next((p for p in props if (p.get("name") or "") == pname), None)
            val = next((v for v in (prop.get("possible_values") or []) if str(v.get("name", "")).strip().lower() == vname.lower()), None) if prop else None
            if prop and val:
                d["attr_plan"].append((prop.get("property_id"), pname, val.get("value_id"), val.get("name"), val.get("scale_id")))
            else:
                opts = [str(v.get("name")) for v in (prop.get("possible_values") or [])] if prop else []
                d["attr_missing"].append(f"{pname}={vname}" + (f" (ozellik yok)" if not prop else f" | secenekler: {opts[:40]}"))
        for p in props:
            nm = (p.get("name") or "").lower()
            if p.get("supports_variations") and "color" in nm and d["color_pid"] is None:
                d["color_pid"], d["color_name"] = p.get("property_id"), p.get("name")
            if p.get("supports_variations") and nm.startswith("size") and d["size_pid"] is None:
                d["size_pid"], d["size_name"] = p.get("property_id"), p.get("name")
        if d["size_pid"] is None:
            # Giclee (121) taxonomy'sinde Size ozelligi yok (6 Eyl kesfi); Etsy panelindeki gibi
            # ozel varyasyon Custom1 (513) "Size" etiketiyle kullanilir.
            cust = next((p for p in props if p.get("supports_variations") and (p.get("name") or "").lower() == "custom1"), None)
            if cust:
                d["size_pid"], d["size_name"] = cust.get("property_id"), "Size"
                d["size_note"] = f"taxonomy'de Size yok; Custom1 ({cust.get('property_id')}) 'Size' olarak kullanilir"
    return d


def parse_rp_spec(spec):
    """'returns=1,exchanges=1,deadline=30' -> createShopReturnPolicy govdesi (yalniz Mo'nun verdigi degerler)."""
    if not spec:
        return None
    kv = dict(x.split("=", 1) for x in spec.split(",") if "=" in x)
    try:
        body = {"accepts_returns": kv["returns"].strip().lower() in ("1", "true", "yes"),
                "accepts_exchanges": kv["exchanges"].strip().lower() in ("1", "true", "yes")}
        if body["accepts_returns"] or body["accepts_exchanges"]:
            body["return_deadline"] = int(kv["deadline"])
    except (KeyError, ValueError) as e:
        raise SystemExit(f"HATA: --return-policy-spec bicimi: returns=1,exchanges=1,deadline=30 ({e})")
    return body


def ensure_return_policy(api, shop, d):
    if d["return_policy_id"]:
        return d["return_policy_id"]
    if not d.get("return_policy_spec"):
        raise SystemExit("HATA: iade politikasi yok ve --return-policy-spec verilmedi")
    r = api.post(f"/shops/{shop}/policies/return", d["return_policy_spec"])
    d["return_policy_id"] = r.get("return_policy_id")
    log(f"  iade politikasi olusturuldu: {d['return_policy_id']} {d['return_policy_spec']}")
    return d["return_policy_id"]


def discovery_issues(d):
    iss = []
    if d["production_partner_id"] is None:
        iss.append("Prodigi production partner yok (Etsy panelinden eklenmeli)")
    if d["return_policy_id"] is None and not d.get("return_policy_spec"):
        iss.append(f"iade politikasi yok/secilemedi ({len(d['return_policies'])} adet; --return-policy-id ya da --return-policy-spec ver)")
    if d["taxonomy_id"] is None:
        iss.append(f"taxonomy Prints > Giclee tek eslesme yok: {d['taxonomy_hits']}")
    if d["color_pid"] is None or d["size_pid"] is None:
        iss.append("varyasyon property (color/size) bulunamadi")
    if d.get("attr_missing"):
        iss.append(f"ozellik degeri eslesmedi: {d['attr_missing']}")
    return iss


# ------------------------------------------------------------------ durum
def read_state(path):
    st = {}
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st[r["pair"]] = r
    return st


def write_state(path, st):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = ["pair", "listing_id", "stage", "ts_utc", "note"]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for k in sorted(st):
            w.writerow({c: st[k].get(c, "") for c in cols})


def set_stage(st, path, pair, lid, stage, note=""):
    st[pair] = dict(pair=pair, listing_id=str(lid or ""), stage=stage,
                    ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), note=note)
    write_state(path, st)
    log(f"  STATE {pair}: {stage} {lid or ''} {note}")


# ------------------------------------------------------------------ apply adimlari
def quota_ok(api, qmin=QUOTA_MIN):
    if api.remaining is None:
        return True
    try:
        return int(api.remaining) >= qmin
    except ValueError:
        return True


# Kargo profili karari (Mo, 6 Eyl 2026): cikis US 28216 (Prodigi Charlotte lab); US 3-8, CA/AU/UK 5-10,
# EU (tum AB) 5-12 is gunu; ucret 0; islem suresi 1-3 is gunu. GPSR/uretici alanlari simdilik bos.
SHIP_ORIGIN_ZIP = "28216"
PROC_MIN, PROC_MAX = 1, 3        # islem suresi 1-3 is gunu (Mo); Etsy "processing profile" (readiness_state_id) zorunlu (6 Eyl 400)
# (tur, kod, min gun, max gun, ucret USD). "Everywhere else": Prodigi 8 ulke Standard ortalamasi 17.91 - Budget US 7.10
# = 10.81 -> 10.99 USD, 7-21 is gunu (Mo kurali, TEMP/PRODIGI/PRODIGI_SHIP_EVERYWHERE.md, 6 Eyl; sapma > %50 yok).
# Etsy'de "everywhere else" hedefi ulke kodsuz destination_region="none" ile denenir; reddedilirse UYARI (kosu surer).
SHIP_DESTS = [("country", "US", 3, 8, 0), ("country", "CA", 5, 10, 0), ("country", "AU", 5, 10, 0), ("country", "GB", 5, 10, 0),
              ("region", "eu", 5, 12, 0), ("region", "none", 7, 21, 10.99)]


def ensure_shipping(api, shop, d, proc_min, proc_max, origin_zip):
    """Etsy: destination_country_iso ya da destination_region zorunlu ('none' reddedilir); origin_postal_code
    zorunlu; her hedef icin min/max_delivery_days zorunlu (6 Eyl 400'leri)."""
    have = set()
    if d["shipping_profile_id"]:
        # idempotent: mevcut hedefler okunur, eksikler eklenir (6 Eyl: 3. kosu CA'dan sonra 201'de durdu)
        prof = api.get(f"/shops/{shop}/shipping-profiles/{d['shipping_profile_id']}") or {}
        for x in prof.get("shipping_profile_destinations") or []:
            cc, rg = x.get("destination_country_iso"), (x.get("destination_region") or "none")
            have.add(cc.upper() if cc else ("EVERYWHERE" if rg == "none" else rg.upper()))
        log(f"  kargo profili mevcut: {d['shipping_profile_id']} hedefler {sorted(have)}")
    else:
        kind, code, dmin, dmax, fee = SHIP_DESTS[0]
        body = {"title": SHIPPING_TITLE, "origin_country_iso": "US", "origin_postal_code": origin_zip,
                "primary_cost": fee, "secondary_cost": fee,
                "min_processing_time": proc_min, "max_processing_time": proc_max, "processing_time_unit": "business_days",
                "destination_country_iso": code, "min_delivery_days": dmin, "max_delivery_days": dmax}
        r = api.post(f"/shops/{shop}/shipping-profiles", body)
        d["shipping_profile_id"] = r.get("shipping_profile_id")
        have.add(code)
        log(f"  kargo profili olusturuldu: {d['shipping_profile_id']} ({code} {dmin}-{dmax} gun, 0 USD, cikis {origin_zip})")
    for kind, code, dmin, dmax, fee in SHIP_DESTS:
        key = "EVERYWHERE" if code == "none" else code.upper()
        if key in have:
            continue
        body = {"primary_cost": fee, "secondary_cost": fee, "min_delivery_days": dmin, "max_delivery_days": dmax}
        body["destination_country_iso" if kind == "country" else "destination_region"] = code
        try:
            api.post(f"/shops/{shop}/shipping-profiles/{d['shipping_profile_id']}/destinations", body)
        except SystemExit as e:
            if code != "none":
                raise
            log(f"  UYARI: 'everywhere else' hedefi eklenemedi (Etsy bolge kodu?): {e}")
            d["shipping_warn"] = str(e)[:200]
            continue
        have.add(key)
        log(f"  hedef eklendi: {code} {dmin}-{dmax} gun {fee} USD")
    d["shipping_destinations"] = sorted(have)
    return d["shipping_profile_id"]


def ensure_readiness(api, shop, d, proc_min, proc_max):
    """Etsy: fiziksel ilanda readiness_state_id zorunlu (createShopReadinessStateDefinition; OAS 6 Eyl)."""
    if d.get("readiness_state_id"):
        return d["readiness_state_id"]
    r = api.post(f"/shops/{shop}/readiness-state-definitions",
                 {"readiness_state": "made_to_order", "min_processing_time": proc_min, "max_processing_time": proc_max, "processing_time_unit": "days"})
    d["readiness_state_id"] = r.get("readiness_state_id")
    log(f"  hazirlik durumu (processing profile) olusturuldu: {d['readiness_state_id']} made_to_order {proc_min}-{proc_max} gun")
    return d["readiness_state_id"]


def ensure_section(api, shop, d):
    if d["shop_section_id"]:
        return d["shop_section_id"]
    r = api.post(f"/shops/{shop}/sections", {"title": SECTION_TITLE})
    d["shop_section_id"] = r.get("shop_section_id")
    log(f"  bolum olusturuldu: {d['shop_section_id']}")
    return d["shop_section_id"]


def listing_body(title, desc, tags, d, base_price):
    return {"quantity": QUANTITY, "title": title, "description": desc, "price": base_price,
            "who_made": WHO_MADE, "when_made": "made_to_order", "taxonomy_id": d["taxonomy_id"], "should_auto_renew": "true",
            "shipping_profile_id": d["shipping_profile_id"], "return_policy_id": d["return_policy_id"],
            "shop_section_id": d["shop_section_id"], "readiness_state_id": d.get("readiness_state_id"),
            "tags": ",".join(tags), "materials": ",".join(MATERIALS),
            "production_partner_ids": str(d["production_partner_id"]), "type": "physical", "is_supply": "false"}


def create_pair(api, shop, pair, d, prices, img_root, primary, frames, st, state_path, out_dir, media_root=None):
    title, tags, desc, note = build_listing(pair, load_template())
    media = media_plan(media_root, pair, primary)
    eksik = media_missing(media)                      # kart/video eksik: kosu durmaz, raporlanir
    plan = image_plan(img_root, pair, primary, frames, media)
    missing_img = [f"{ed}/{k}" for rk, ed, p, _, k in plan if p is None]
    if missing_img:
        raise SystemExit(f"HATA: {pair}: eksik gorsel {missing_img}")
    row = st.get(pair, {})
    lid = row.get("listing_id") or ""
    stage = row.get("stage") or ""
    base_price = prices[SIZES[0]]

    if not lid:
        r = api.post(f"/shops/{shop}/listings", listing_body(title, desc, tags, d, base_price))
        lid = r.get("listing_id")
        if not lid:
            raise SystemExit(f"HATA: {pair}: createDraftListing cevabinda listing_id yok")
        set_stage(st, state_path, pair, lid, "created")
        stage = "created"

    if STAGES.index(stage) < STAGES.index("images"):
        have = {i.get("rank") for i in ((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or [])}
        for rk, ed, p, _, _ in plan:
            if rk in have:
                continue
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            with open(p, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (p.name, fh, mime)},
                              data={"rank": str(rk)})
        set_stage(st, state_path, pair, lid, "images")
        stage = "images"

    if STAGES.index(stage) < STAGES.index("video"):
        # EK 3: ana edisyon V01 videosu (1 adet); dosya yoksa atlanir (eksik raporlanir)
        if media.get("VIDEO") and not ((api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []):
            vp = media["VIDEO"]
            with open(vp, "rb") as fh:
                api.post_file(f"/shops/{shop}/listings/{lid}/videos", files={"video": (vp.name, fh, "video/mp4")}, data={"name": vp.name})
        set_stage(st, state_path, pair, lid, "video")
        stage = "video"

    if STAGES.index(stage) < STAGES.index("fields"):
        # Etsy updateListing (6 Eyl 400): who_made / when_made / is_supply birlikte gonderilir
        api.patch(f"/shops/{shop}/listings/{lid}", {"who_made": WHO_MADE, "when_made": "made_to_order", "is_supply": "false",
                                                    "should_auto_renew": "true" if AUTO_RENEW else "false"})
        for pid, pname, vid, vname, scale in d.get("attr_plan") or []:
            body = {"value_ids": str(vid), "values": vname}
            if scale:
                body["scale_id"] = scale
            api.put(f"/shops/{shop}/listings/{lid}/properties/{pid}", body)
        ru_title, ru_tags, ru_desc, ru_note = build_ru(pair, load_ru_template())
        tpath = f"/shops/{shop}/listings/{lid}/translations/ru"
        cur = api.get(tpath, ok404=True)
        tbody = {"title": ru_title, "description": ru_desc, "tags": ",".join(ru_tags)}
        (api.put if cur is not None else api.post)(tpath, tbody)
        set_stage(st, state_path, pair, lid, "fields", ("RU tag notu: " + ru_note) if ru_note else "")
        stage = "fields"

    if STAGES.index(stage) < STAGES.index("inventory"):
        api.put_json(f"/listings/{lid}/inventory", inventory_body(pair, prices, d["color_pid"], d["size_pid"], d["color_name"], d["size_name"], d.get("readiness_state_id")))
        set_stage(st, state_path, pair, lid, "inventory")
        stage = "inventory"

    if STAGES.index(stage) < STAGES.index("variation_images"):
        inv = api.get(f"/listings/{lid}/inventory") or {}
        value_ids = {}
        for pr in inv.get("products") or []:
            for pv in pr.get("property_values") or []:
                if pv.get("property_id") == d["color_pid"] and pv.get("value_ids") and pv.get("values"):
                    value_ids[pv["values"][0]] = pv["value_ids"][0]
        imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
        by_rank = {i.get("rank"): i.get("listing_image_id") for i in imgs}
        vi = []
        for rk, ed, p, is_color, _ in plan:
            if is_color and ED_NAME[ed] in value_ids and rk in by_rank:
                vi.append({"property_id": d["color_pid"], "value_id": value_ids[ED_NAME[ed]], "image_id": by_rank[rk]})
        if len(vi) != len(EDITIONS):
            raise SystemExit(f"HATA: {pair}: renk-gorsel eslemesi {len(vi)}/{len(EDITIONS)} (value_ids {value_ids}, ranks {sorted(by_rank)})")
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})   # OAS: updateVariationImages = POST (10. kosu 404 PUT)
        set_stage(st, state_path, pair, lid, "variation_images")
        stage = "variation_images"

    # geri okuma
    L = api.get(f"/listings/{lid}") or {}
    imgs = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vimg = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    tru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
    ru_title = build_ru(pair, load_ru_template())[0]
    checks = {"state_draft": L.get("state") == "draft", "title": L.get("title") == title,
              "who_made": L.get("who_made") == WHO_MADE, "auto_renew": bool(L.get("should_auto_renew")) == AUTO_RENEW,
              "ru": tru.get("title") == ru_title,
              "attrs": {p.get("property_id") for p in props} >= {a[0] for a in d.get("attr_plan") or []},
              "tags": tags_of(L) == tags, "desc": norm(L.get("description")) == norm(desc),
              "images": len(imgs) == len(plan), "products": len(inv.get("products") or []) == len(EDITIONS) * len(SIZES),
              "variation_images": len(vimg) == len(EDITIONS), "partner": bool(L.get("production_partner_ids") or L.get("production_partners")),
              "video": (len(vids) == 1) if media.get("VIDEO") else True}
    ok = all(checks.values())
    set_stage(st, state_path, pair, lid, "verified" if ok else stage,
              ("PASS" if ok else "FAIL " + ",".join(k for k, v in checks.items() if not v)) + (f" | eksik: {'; '.join(eksik)}" if eksik else ""))
    (Path(out_dir) / f"{pair}_readback.json").write_text(json.dumps({"listing": L, "checks": checks, "n_images": len(imgs), "n_videos": len(vids), "eksik": eksik,
                                                                     "n_products": len(inv.get("products") or []), "variation_images": vimg}, indent=1, ensure_ascii=False))
    return lid, ok, checks, eksik


# ------------------------------------------------------------------ ana
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="", help="virgullu cift listesi, or. ARIES_LEO,CANCER_LIBRA")
    ap.add_argument("--pairs-file", default="", help="satir basina bir cift")
    ap.add_argument("--limit", type=int, default=0, help="en fazla N cift (0 = hepsi)")
    ap.add_argument("--images", required=True, help="<images>/<PAIR>/<ED>/NN_*.jpg")
    ap.add_argument("--media", default="", help="<media>/<PAIR>/ teknik kartlar + video (EK 3); bos = 10 kare, video yok")
    ap.add_argument("--state", required=True, help="cift,listing_id,stage CSV (resume)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prices", default=str(PRICES_CSV))
    ap.add_argument("--primary", default="MIDNIGHT_BLUE", choices=EDITIONS)
    ap.add_argument("--frames", default=DEFAULT_FRAMES, help="ana edisyondan alinacak kareler")
    ap.add_argument("--return-policy-id", default="")
    ap.add_argument("--return-policy-spec", default="", help="magazada iade politikasi yoksa apply'da olusturulur: returns=1,exchanges=1,deadline=30")
    ap.add_argument("--quota-min", type=int, default=QUOTA_MIN, help="bu degerin altinda yazma yok (varsayilan 400)")
    ap.add_argument("--ru-dict", default="", help="Hunspell ru_RU sozluk on eki (ru_RU.dic/.aff); verilirse RU yazim denetimi")
    ap.add_argument("--origin-postal-code", default=SHIP_ORIGIN_ZIP, help="kargo profili cikis posta kodu (Mo: 28216)")
    ap.add_argument("--processing-min", type=int, default=1)
    ap.add_argument("--processing-max", type=int, default=3)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    pairs = [p.strip().upper() for p in a.pairs.split(",") if p.strip()]
    if a.pairs_file:
        pairs += [l.strip().upper() for l in Path(a.pairs_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    pairs = list(dict.fromkeys(pairs))
    if not pairs:
        raise SystemExit("HATA: --pairs veya --pairs-file gerekli")
    for p in pairs:
        s = p.split("_")
        if len(s) != 2 or any(x.capitalize() not in SIGNS for x in s):
            raise SystemExit(f"HATA: gecersiz cift {p}")
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    frames = [f.strip() for f in a.frames.split(",") if f.strip()]
    prices, missing = read_prices(a.prices)
    ru_tpl = load_ru_template()
    if a.ru_dict:
        t, tg, dsc, _ = build_ru("ARIES_LEO", ru_tpl)
        spellcheck_ru(a.ru_dict, [t, dsc, " ".join(tg), " ".join(SIGN_RU.values())])
    st = read_state(a.state)
    todo = [p for p in pairs if (st.get(p) or {}).get("stage") != "verified"]
    if a.limit:
        todo = todo[:a.limit]
    log(f"ciftler: {len(pairs)} istendi, {len(todo)} islenecek (verified atlanir); fiyat eksik: {missing or 'yok'}")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    d = discover(api, shop, a.return_policy_id)
    if not d["return_policy_id"] and a.return_policy_spec:
        d["return_policy_spec"] = parse_rp_spec(a.return_policy_spec)
    iss = discovery_issues(d)
    md = [f"## Kesif (kota {api.remaining})", "",
          f"- kargo profili '{SHIPPING_TITLE}': {d['shipping_profile_id'] or 'YOK -> apply olusturur'} | mevcut: {d['shipping_profiles']}",
          f"- bolum '{SECTION_TITLE}': {d['shop_section_id'] or 'YOK -> apply olusturur'} | mevcut: {d['sections']}",
          f"- production partner Prodigi: {d['production_partner_id']} | mevcut: {d['partners']}",
          f"- iade politikasi: {d['return_policy_id'] or ('YOK -> apply olusturur ' + str(d['return_policy_spec']) if d['return_policy_spec'] else 'YOK')} | mevcut: {d['return_policies']}",
          f"- taxonomy: {d['taxonomy_id']} | eslesme: {d['taxonomy_hits']}",
          f"- varyasyon property: color {d['color_pid']} ({d['color_name']}), size {d['size_pid']} ({d['size_name']}) {d.get('size_note', '')}",
          f"- hazirlik durumu (made_to_order {PROC_MIN}-{PROC_MAX} gun): {d.get('readiness_state_id') or 'YOK -> apply olusturur'} | mevcut: {d.get('readiness_states')}",
          f"- ozellikler: {[(a_[1], a_[3], a_[2]) for a_ in d.get('attr_plan') or []]} | eslesmeyen: {d.get('attr_missing')}",
          f"- fiyat: {len(prices)}/13 dolu; eksik: {missing or 'yok'}",
          f"- kesif sorunlari: {iss or 'yok'}", ""]
    (out_dir / "discovery.json").write_text(json.dumps(d, indent=1, ensure_ascii=False, default=str))

    rows = []
    if a.dry_run:
        for pair in todo:
            title, tags, desc, note = build_listing(pair, load_template())
            media = media_plan(a.media or None, pair, a.primary)
            eksik = media_missing(media)
            plan = image_plan(a.images, pair, a.primary, frames, media)
            miss_img = [f"{ed}/{k}" for rk, ed, p, _, k in plan if p is None]
            body = listing_body(title, desc, tags, d, prices.get(SIZES[0], 0))
            inv = inventory_body(pair, prices, d["color_pid"], d["size_pid"], d["color_name"], d["size_name"], d.get("readiness_state_id"))
            ru_title, ru_tags, ru_desc, ru_note = build_ru(pair, ru_tpl)
            (out_dir / f"{pair}_payload.json").write_text(json.dumps(
                {"listing": body, "images": [(rk, ed, str(p) if p else None, c, k) for rk, ed, p, c, k in plan], "inventory": inv,
                 "video": str(media["VIDEO"]) if media.get("VIDEO") else None, "eksik": eksik,
                 "attrs": d.get("attr_plan"), "ru": {"title": ru_title, "tags": ru_tags, "description": ru_desc, "note": ru_note}},
                indent=1, ensure_ascii=False))
            status = "HAZIR" if not (missing or miss_img or iss) else "EKSIK: " + "; ".join(
                ([f"fiyat {missing}"] if missing else []) + ([f"gorsel {miss_img}"] if miss_img else []) + iss)
            rows.append(dict(pair=pair, title_len=len(title), n_tags=len(tags), desc_len=len(desc), n_images=len(plan),
                             n_products=len(inv["products"]), pair_tag_note=note, status=status, video=1 if media.get("VIDEO") else 0, eksik="; ".join(eksik) or "-"))
            log(f"[dry-run] {pair}: baslik {len(title)} | gorsel {len(plan)} | video {1 if media.get('VIDEO') else 0} | varyant {len(inv['products'])} | {status} | eksik: {'; '.join(eksik) or '-'}")
        md.append("| cift | baslik | tag | aciklama | gorsel | video | varyant | durum | eksik medya |\n|---|---|---|---|---|---|---|---|---|")
        md += [f"| {r['pair']} | {r['title_len']} | {r['n_tags']} | {r['desc_len']} | {r['n_images']} | {r['video']} | {r['n_products']} | {r['status']} | {r['eksik']} |" for r in rows]
        md.append("\nDRY-RUN: yazma yok. Payload: <out>/<PAIR>_payload.json")
    else:
        if missing or iss:
            raise SystemExit(f"HATA: apply icin eksik: fiyat {missing}; kesif {iss}")
        if not quota_ok(api, a.quota_min):
            raise SystemExit(f"HATA: kota {api.remaining} < {a.quota_min}; yazma yok")
        ensure_shipping(api, shop, d, a.processing_min, a.processing_max, a.origin_postal_code.strip())
        ensure_section(api, shop, d)
        ensure_return_policy(api, shop, d)
        ensure_readiness(api, shop, d, a.processing_min, a.processing_max)
        t0 = time.time()
        for n, pair in enumerate(todo, 1):
            if not quota_ok(api, a.quota_min):
                log(f"KOTA {api.remaining} < {a.quota_min}: {pair} ve sonrasi islenmedi (resume ile devam)")
                break
            lid, ok, checks, eksik = create_pair(api, shop, pair, d, prices, a.images, a.primary, frames, st, a.state, out_dir, a.media or None)
            rows.append(dict(pair=pair, listing_id=lid, status="PASS" if ok else "FAIL", checks=checks, eksik="; ".join(eksik) or "-"))
            el = time.time() - t0
            log(f"[{n}/{len(todo)}] {pair} {lid} {'PASS' if ok else 'FAIL ' + str(checks)} | gecen {el:.0f}s kalan~{el / n * (len(todo) - n):.0f}s | kota {api.remaining}")
        md.append("| cift | listing_id | durum | eksik medya |\n|---|---|---|---|")
        md += [f"| {r['pair']} | {r['listing_id']} | {r['status']} | {r['eksik']} |" for r in rows]
    text = "\n".join(md)
    log(text)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if a.apply and any(r["status"] != "PASS" for r in rows):
        raise SystemExit("FAIL: en az bir ilan PASS degil")


if __name__ == "__main__":
    main()
