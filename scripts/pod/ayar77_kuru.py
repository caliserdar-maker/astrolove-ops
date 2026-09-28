#!/usr/bin/env python3
"""AYAR77 KURU KOSU (SALT OKUMA, Etsy'ye yazma YOK) - 28 Eyl 2026.

77 POD ilaninin ayarlarini CANLI CL (4570143815) ile karsilastirir; CL tek dogru kaynaktir.
Kapsam (cift adlari degisir):
  1 ENVANTER   : CL'nin 3 menusu + urunleri; SKU on eki POD-CAN_LIB -> POD-<S1>_<S2>; fiyat, adet, aktiflik,
                 hazirlik (readiness_state_id), *_on_property birebir CL.
  2 ACIKLAMA   : scripts/pod/metin_78_uret.py ciktisi. Kontrol: CL icin uretilen == CL canli; her ilanda
                 uretilen metin CL canli metinden yalniz cift adlari ve tarihlerle ayrilir.
  3 KISISEL    : is_personalizable / zorunlu / sinir / talimat + personalization_questions CL'den;
                 "Name under {A}" / "Name under {B}", ayni burc "Left name" / "Right name".
  4 ALANLAR    : kargo profili, iade politikasi, bolum, taxonomy, who/when_made, materials ... (CL'de ne varsa);
                 nitelikler (properties) CL'den.
  5 RU         : CL'de ru ceviri var mi; varsa yapisi ve sign adlarinin yalin halde olup olmadigi raporlanir
                 (cekimli form varsa uretim karar bekler; uydurma yok).
DOKUNULMAZ (karsilastirilmaz, planlanmaz): baslik, 13 etiket, gorseller, video, state.
Cikti (<out>): FARK.csv (77 satir), OZET.md, CL_REFERANS.json, ONCE/<id>.json (tam okuma), ACIKLAMA/<CIFT>.txt.
Kullanim: ayar77_kuru.py --ids data/pod/pod78_ids.csv --out OUT [--oas oas.json]
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK / "scripts/pod"), str(KOK / "scripts/etsy")]
import metin_78_uret as M  # noqa: E402
from pod_sku import SIGN3  # noqa: E402

CL_ID = "4570143815"
CL_A, CL_B = "Cancer", "Libra"
KOTA_TABAN = 300
RU_YALIN = {"Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы", "Cancer": "Рак", "Leo": "Лев",
            "Virgo": "Дева", "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
            "Capricorn": "Козерог", "Aquarius": "Водолей", "Pisces": "Рыбы"}
RU_KOK = {"Aries": "Ов[её]?н|Овн", "Taurus": "Тел[её]?ц|Тельц", "Gemini": "Близнец", "Cancer": "Рак", "Leo": "Л[её]в|Льв",
          "Virgo": "Дев", "Libra": "Вес", "Scorpio": "Скорпион", "Sagittarius": "Стрел[её]?ц|Стрельц",
          "Capricorn": "Козерог", "Aquarius": "Водоле", "Pisces": "Рыб"}
PERS_ALAN = ["is_personalizable", "personalization_is_required", "personalization_char_count_max",
             "personalization_instructions"]
AYAR_ALAN = ["shipping_profile_id", "return_policy_id", "shop_section_id", "taxonomy_id", "who_made", "when_made",
             "is_supply", "materials", "should_auto_renew", "is_taxable", "type", "listing_type", "production_partner_ids",
             "production_partners", "processing_min", "processing_max", "item_weight", "item_weight_unit",
             "item_length", "item_width", "item_height", "item_dimensions_unit", "is_customizable", "style",
             "readiness_state_id", "language"]
# Karsilastirma disi: dokunulmazlar, kimlikler, zaman damgalari, istatistikler, envanterden turetilenler
HARIC = {"listing_id", "user_id", "shop_id", "title", "tags", "description", "state", "url", "num_favorers", "views",
         "featured_rank", "images", "videos", "translations", "personalization", "personalization_questions",
         "inventory", "price", "quantity", "has_variations", "skus", "sku", "file_data", "shipping_profile", "user",
         "shop", "rich_description", "non_taxable", "is_private", "used_manufacturer", "ending_timestamp"}


def log(m):
    print(m, flush=True)


def normalize(t):
    t = html.unescape(t or "").replace("\r\n", "\n")
    return "\n".join(s.rstrip() for s in t.split("\n")).strip()


def money(v):
    if isinstance(v, dict):
        return round(float(v.get("amount", 0)) / float(v.get("divisor") or 100), 2)
    return round(float(v or 0), 2)


# ------------------------------------------------------------ 1 envanter
def cl_onek():
    return f"POD-{SIGN3[CL_A.upper()]}_{SIGN3[CL_B.upper()]}-"


def hedef_envanter(cl_inv, a, b):
    """CL canli envanterinden hedef: SKU on eki degisir, digeri birebir. Doner (plan, sorunlar)."""
    onek, yeni = cl_onek(), f"POD-{SIGN3[a.upper()]}_{SIGN3[b.upper()]}-"
    sorun, urunler = [], []
    for p in cl_inv.get("products") or []:
        sku = p.get("sku") or ""
        if not sku.startswith(onek):
            sorun.append(f"CL SKU on eki beklenmedik: {sku}")
            continue
        pvs = []
        for pv in p.get("property_values") or []:
            x = {"property_id": pv.get("property_id"), "property_name": pv.get("property_name"),
                 "values": list(pv.get("values") or [])}
            if pv.get("scale_id") is not None:
                x["scale_id"] = pv["scale_id"]
            pvs.append(x)
        offs = []
        for o in p.get("offerings") or []:
            if o.get("is_deleted"):
                continue
            y = {"price": money(o.get("price")), "quantity": o.get("quantity"), "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id") is not None:
                y["readiness_state_id"] = o["readiness_state_id"]
            offs.append(y)
        urunler.append({"sku": yeni + sku[len(onek):], "property_values": pvs, "offerings": offs})
    plan = {"products": urunler}
    for k in ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property"):
        if cl_inv.get(k) is not None:
            plan[k] = list(cl_inv[k])
    return plan, sorun


def imza(inv):
    s = []
    for p in inv.get("products") or []:
        pv = tuple((v.get("property_id"), (v.get("values") or [""])[0]) for v in p.get("property_values") or [])
        for o in [o for o in p.get("offerings") or [] if not o.get("is_deleted")][:1]:
            s.append((p.get("sku") or "", pv, money(o.get("price")), o.get("quantity"), bool(o.get("is_enabled")),
                      o.get("readiness_state_id")))
    return sorted(s, key=repr)


def menu_ozet(inv):
    m = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            m.setdefault(v.get("property_name") or str(v.get("property_id")), set()).add((v.get("values") or [""])[0])
    return {k: len(v) for k, v in m.items()}


def on_prop(inv):
    return {k: inv.get(k) for k in ("price_on_property", "quantity_on_property", "sku_on_property",
                                    "readiness_state_on_property")}


# ------------------------------------------------------------ 2 aciklama
def yer_tutucu(metin, a, b):
    ta, tb = M.TARIH[a.upper()], M.TARIH[b.upper()]
    s = normalize(metin).replace(ta, "{A_TARIH}").replace(tb, "{B_TARIH}")
    s = re.sub(rf"\b{re.escape(a)}\b", "{A}", s)
    s = re.sub(rf"\b{re.escape(b)}\b", "{B}", s)
    if a == b:
        s = s.replace("{B_TARIH}", "{A_TARIH}").replace("{B}", "{A}")
    return s


def ilk_fark(x, y):
    if x == y:
        return ""
    i = next((k for k, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
    return f"@{i}: '{x[max(0, i - 20):i + 30]}' / '{y[max(0, i - 20):i + 30]}'"


# ------------------------------------------------------------ 3 kisisellestirme
def sorular_of(L):
    q = L.get("personalization_questions")
    p = L.get("personalization")
    if not isinstance(q, list) and isinstance(p, dict):
        q = p.get("personalization_questions")
    if not isinstance(q, list) and isinstance(p, list):
        q = p
    return q if isinstance(q, list) else None


def hedef_sorular(cl_q, a, b):
    out = []
    for q in cl_q:
        x = dict(q)
        t = x.get("question_text") or ""
        for k in ("question_id", "listing_id", "rank_on_listing", "personalization_question_id"):
            x.pop(k, None)
        if t == f"Name under {CL_A}":
            x["question_text"] = "Left name" if a == b else f"Name under {a}"
        elif t == f"Name under {CL_B}":
            x["question_text"] = "Right name" if a == b else f"Name under {b}"
        out.append(x)
    return out


def soru_imza(qs):
    return [(q.get("question_text"), q.get("question_type"), bool(q.get("required")), q.get("max_allowed_characters"),
             q.get("instruction"), json.dumps(q.get("options"), sort_keys=True)) for q in (qs or [])]


def pers_hedef(cl_L, a, b):
    d = {}
    for k in PERS_ALAN:
        if k in cl_L:
            v = cl_L[k]
            if isinstance(v, str):
                v = re.sub(rf"\b{CL_A}\b", "{A}", v)
                v = re.sub(rf"\b{CL_B}\b", "{B}", v).replace("{A}", a).replace("{B}", b)
            d[k] = v
    return d


# ------------------------------------------------------------ 4 alanlar + nitelikler
def alan_farki(cl_L, L):
    fark, bilinmeyen = {}, {}
    for k in AYAR_ALAN:
        if k in cl_L or k in L:
            if json.dumps(cl_L.get(k), sort_keys=True) != json.dumps(L.get(k), sort_keys=True):
                fark[k] = (L.get(k), cl_L.get(k))
    for k in set(cl_L) | set(L):
        if k in HARIC or k in AYAR_ALAN or k in PERS_ALAN or "timestamp" in k:
            continue
        if json.dumps(cl_L.get(k), sort_keys=True) != json.dumps(L.get(k), sort_keys=True):
            bilinmeyen[k] = (L.get(k), cl_L.get(k))
    return fark, bilinmeyen


def nitelik_imza(props):
    return sorted((p.get("property_id"), p.get("property_name"), tuple(p.get("value_ids") or []),
                   tuple(p.get("values") or []), p.get("scale_id")) for p in props or [])


# ------------------------------------------------------------ 5 RU
def ru_of(L, api, shop, lid):
    tr = [t for t in L.get("translations") or [] if isinstance(t, dict) and t.get("language") == "ru"]
    if tr:
        return tr[0]
    return api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}


def ru_sablon(metin, a, b):
    """RU metinde burc adlarini (her cekimiyle) {A}/{B} yapar; ayni burcta ikisi de {A}."""
    t = normalize(metin)
    t = re.sub(rf"(?:{RU_KOK[a]})[а-яё]*", "{A}", t, flags=re.I)
    if b != a:
        t = re.sub(rf"(?:{RU_KOK[b]})[а-яё]*", "{B}", t, flags=re.I)
    return t


def ru_kiyas(cl_ru, xru, a, b):
    """CL RU (Cancer/Libra) ile ilan RU'su: aciklama/baslik/etiket ayri ayri; fark yoksa AYNI."""
    fark = []
    for alan in ("description", "title"):
        ref = ru_sablon(cl_ru.get(alan), CL_A, CL_B)
        if a == b:
            ref = ref.replace("{B}", "{A}")
        if ru_sablon(xru.get(alan), a, b) != ref:
            fark.append(f"{alan} " + ilk_fark(ref, ru_sablon(xru.get(alan), a, b)))
    rt = [ru_sablon(t, CL_A, CL_B) for t in cl_ru.get("tags") or []]
    if a == b:
        rt = [t.replace("{B}", "{A}") for t in rt]
    if [ru_sablon(t, a, b) for t in xru.get("tags") or []] != rt:
        fark.append("tags")
    return fark


def ru_cekim(metin, a, b):
    """CL RU metninde burc adlarinin yalin disi (cekimli) formlarini say."""
    bulgu = {}
    for ad in {a, b}:
        for m in re.finditer(rf"(?:{RU_KOK[ad]})[а-яё]*", metin or "", re.I):
            if m.group(0).lower() != RU_YALIN[ad].lower():
                bulgu.setdefault(ad, set()).add(m.group(0))
    return {k: sorted(v) for k, v in bulgu.items()}


# ------------------------------------------------------------ ana akis
def kota(api):
    try:
        k = int(api.remaining) if api.remaining is not None else None
    except ValueError:
        k = None
    if k is not None and k < KOTA_TABAN:
        raise SystemExit(f"DUR: kota {k} < {KOTA_TABAN}")
    return k


def calis(api, shop, ids_csv, out, oas_yol=""):
    t0 = time.time()
    out = Path(out); (out / "ONCE").mkdir(parents=True, exist_ok=True); (out / "ACIKLAMA").mkdir(exist_ok=True)
    satir = list(csv.DictReader(open(ids_csv, encoding="utf-8")))
    if len(satir) != 78 or CL_ID not in {r["listing_id"] for r in satir}:
        raise SystemExit(f"HATA: {ids_csv} 78 satir ve CL icermeli ({len(satir)}). DUR.")
    ids = [r["listing_id"] for r in satir]
    bilgi = {r["listing_id"]: r for r in satir}

    L = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]),
                                               "includes": "translations,personalization"}) or {}
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    log(f"batch: {len(L)}/{len(ids)} ilan | kota {kota(api)}")
    ek = {}
    for n, lid in enumerate(ids, 1):
        X = L.get(lid)
        if not X:
            X = api.get(f"/listings/{lid}", ok404=True) or {}
            L[lid] = X
        inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
        props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
        q = sorular_of(X)
        if q is None:
            q = (api.get(f"/shops/{shop}/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
        ru = ru_of(X, api, shop, lid)
        ek[lid] = {"inventory": inv, "properties": props, "questions": q, "ru": ru}
        (out / "ONCE" / f"{lid}.json").write_text(json.dumps({"listing": X, **ek[lid]}, ensure_ascii=False, indent=1))
        if n % 10 == 0 or n == len(ids):
            g = time.time() - t0
            log(f"[{n}/{len(ids)} %{n / len(ids) * 100:.0f}] okuma | gecen {g:.0f}s kalan ~{g / n * (len(ids) - n):.0f}s | kota {kota(api)}")

    cl, cle = L[CL_ID], ek[CL_ID]
    if cl.get("state") != "active":
        raise SystemExit(f"HATA: CL state={cl.get('state')}; referans active degil. DUR.")
    cl_bulgu = []
    cl_uret = normalize(M.uret("CANCER_LIBRA"))
    if cl_uret != normalize(cl.get("description")):
        cl_bulgu.append("CL canli aciklama != metin_78_uret(CANCER_LIBRA) " + ilk_fark(normalize(cl.get("description")), cl_uret))
    cl_tpl = yer_tutucu(cl.get("description"), CL_A, CL_B)
    cl_ru = cle["ru"] or {}
    ru_durum = "CL'de yok" if not cl_ru.get("description") and not cl_ru.get("title") else \
        ("CL'de var, yalin form" if not ru_cekim((cl_ru.get("title") or "") + "\n" + (cl_ru.get("description") or "") + "\n"
                                                    + " ".join(cl_ru.get("tags") or []), CL_A, CL_B)
         else f"CL'de var, CEKIMLI form {ru_cekim((cl_ru.get('description') or '') + ' ' + (cl_ru.get('title') or ''), CL_A, CL_B)}")
    cl_q = cle["questions"] or []
    ref = {"listing": {k: cl.get(k) for k in AYAR_ALAN + PERS_ALAN if k in cl}, "questions": cl_q,
           "properties": cle["properties"], "menu": menu_ozet(cle["inventory"]), "urun": len(cle["inventory"].get("products") or []),
           "on_property": on_prop(cle["inventory"]), "ru": {"durum": ru_durum, "alanlar": sorted(cl_ru)},
           "bulgu": cl_bulgu}
    (out / "CL_REFERANS.json").write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str))
    log(f"CL: urun {ref['urun']} menu {ref['menu']} | soru {len(cl_q)} | nitelik {len(cle['properties'])} | RU {ru_durum}")

    alanlar = ["listing_id", "cift", "state", "yazilabilir", "envanter", "envanter_fark", "aciklama", "aciklama_not",
               "kisisel", "kisisel_fark", "ayar", "ayar_fark", "nitelik", "nitelik_fark", "ru", "cl_den_farkli_kalan",
               "tahmini_yazma"]
    satirlar, sayac = [], {k: 0 for k in ("envanter", "aciklama", "kisisel", "ayar", "nitelik", "ru", "pasif", "ayni_burc_tarih")}
    for lid in ids:
        if lid == CL_ID:
            continue
        r = bilgi[lid]; a, b = r["a"], r["b"]; cift = r["cift"]; X = L[lid]; E = ek[lid]
        st = X.get("state")
        yaz = st == "active"
        if not yaz:
            sayac["pasif"] += 1
        # 1 envanter
        plan, s1 = hedef_envanter(cle["inventory"], a, b)
        e_ayni = imza(plan) == imza(E["inventory"]) and on_prop(plan) == {k: E["inventory"].get(k) for k in on_prop(plan)}
        env = "AYNI" if e_ayni else f"{len(E['inventory'].get('products') or [])} -> {len(plan['products'])} urun"
        env_fark = "" if e_ayni else f"menu {menu_ozet(E['inventory'])} -> {menu_ozet(plan)}" + (f" | {s1[:2]}" if s1 else "")
        # 2 aciklama
        yeni = normalize(M.uret(cift))
        (out / "ACIKLAMA" / f"{cift}.txt").write_text(yeni + "\n", encoding="utf-8")
        not_ = []
        if M.qc(cift, yeni):
            not_.append(f"QC {M.qc(cift, yeni)}")
        ref_tpl = cl_tpl.replace("{B_TARIH}", "{A_TARIH}").replace("{B}", "{A}") if a == b else cl_tpl
        if yer_tutucu(yeni, a, b) != ref_tpl:
            not_.append("CL'den ad/tarih disi fark " + ilk_fark(ref_tpl, yer_tutucu(yeni, a, b)))
        if a == b and yeni.count(f"{a}: {M.TARIH[a.upper()]}.") > 1:
            not_.append("ayni burc: tarih satiri iki kez")
            sayac["ayni_burc_tarih"] += 1
        acik = "AYNI" if yeni == normalize(X.get("description")) else "DEGISECEK"
        # 3 kisisel
        hq = hedef_sorular(cl_q, a, b)
        hp = pers_hedef(cl, a, b)
        kf = []
        if soru_imza(hq) != soru_imza(E["questions"]):
            kf.append(f"sorular {[q.get('question_text') for q in E['questions']]} -> {[q.get('question_text') for q in hq]}"
                      + ("" if [x[1:] for x in soru_imza(hq)] == [x[1:] for x in soru_imza(E['questions'])] else " (+tip/sinir/talimat)"))
        for k, v in hp.items():
            if X.get(k) != v:
                kf.append(f"{k}: {str(X.get(k))[:40]!r} -> {str(v)[:40]!r}")
        # 4 ayar + nitelik
        af, bil = alan_farki(cl, X)
        nf = nitelik_imza(E["properties"]) != nitelik_imza(cle["properties"])
        nfark = ""
        if nf:
            simdi = {p.get("property_name"): p.get("values") for p in E["properties"]}
            hedef = {p.get("property_name"): p.get("values") for p in cle["properties"]}
            nfark = "; ".join(f"{k}: {simdi.get(k)} -> {hedef.get(k)}" for k in sorted(set(simdi) | set(hedef))
                              if simdi.get(k) != hedef.get(k))
        # 5 RU
        xru = E["ru"] or {}
        if ru_durum == "CL'de yok":
            ru = "CL'de yok" + (" (ilanda var, dokunulmaz)" if xru.get("description") else "")
        elif not xru.get("description"):
            ru = "ilanda YOK"
        else:
            rf = ru_kiyas(cl_ru, xru, a, b)
            ru = "AYNI (ad disi)" if not rf else "FARKLI: " + " | ".join(rf)[:300]
            if rf:
                sayac["ru"] += 1
        kalan = ["baslik/etiket/gorsel/video/state (kapsam disi)"]
        if bil:
            kalan.append("bilinmeyen alan farki: " + ", ".join(sorted(bil)))
        if ru_durum.startswith("CL'de var, CEKIMLI"):
            kalan.append("RU: cekimli form, uretim karar bekliyor")
        soru_fark = soru_imza(hq) != soru_imza(E["questions"])
        pers_fark = any(X.get(k) != v for k, v in hp.items())
        n_nitelik = len(nfark.split("; ")) if nfark else 0
        # PUT envanter + geri okuma; PATCH ilan + geri okuma; PUT kisisel + geri okuma; nitelik basina PUT + geri okuma
        tahmin = (0 if e_ayni else 2) + (2 if (acik != "AYNI" or af or pers_fark) else 0) \
            + (2 if soru_fark else 0) + 2 * n_nitelik
        for k, v in (("envanter", not e_ayni), ("aciklama", acik != "AYNI"), ("kisisel", bool(kf)), ("ayar", bool(af)),
                     ("nitelik", nf)):
            sayac[k] += int(v)
        satirlar.append({"listing_id": lid, "cift": cift, "state": st, "yazilabilir": "EVET" if yaz else "HAYIR (active degil)",
                         "envanter": env, "envanter_fark": env_fark, "aciklama": acik, "aciklama_not": "; ".join(not_),
                         "kisisel": "AYNI" if not kf else "DEGISECEK", "kisisel_fark": " | ".join(kf),
                         "ayar": "AYNI" if not af else "DEGISECEK",
                         "ayar_fark": "; ".join(f"{k}: {json.dumps(v[0], default=str)[:40]} -> {json.dumps(v[1], default=str)[:40]}"
                                                for k, v in af.items()),
                         "nitelik": "AYNI" if not nf else "DEGISECEK", "nitelik_fark": nfark, "ru": ru,
                         "cl_den_farkli_kalan": " | ".join(kalan), "tahmini_yazma": tahmin})
    with open(out / "FARK.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar); w.writeheader(); w.writerows(satirlar)
    md = [f"# AYAR77 KURU KOSU ({time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}) - Etsy'ye yazma YOK", "",
          f"- CL {CL_ID}: {ref['urun']} urun, menu {ref['menu']}, {len(cl_q)} soru, {len(cle['properties'])} nitelik, RU: {ru_durum}",
          f"- CL bulgulari: {cl_bulgu or 'yok'}",
          f"- 77 ilan: envanter degisecek {sayac['envanter']} | aciklama {sayac['aciklama']} | kisisel {sayac['kisisel']} | "
          f"ayar {sayac['ayar']} | nitelik {sayac['nitelik']} | RU farkli {sayac['ru']} | active degil {sayac['pasif']}",
          f"- Ayni burc cifti tarih satiri iki kez: {sayac['ayni_burc_tarih']} (metin_78_uret; pod_seo_v3_build tek satira indirir)",
          f"- Tahmini yazma cagrisi: {sum(s['tahmini_yazma'] for s in satirlar)} | kota son {api.remaining} | gecen {time.time() - t0:.0f}s",
          "", "| id | cift | state | envanter | aciklama | kisisel | ayar | nitelik | RU |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {s['listing_id']} | {s['cift']} | {s['state']} | {s['envanter']} | {s['aciklama']} | {s['kisisel']} | "
           f"{s['ayar']} | {s['nitelik']} | {s['ru']} |" for s in satirlar]
    (out / "OZET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log("\n".join(md[:8]))
    if oas_yol and Path(oas_yol).exists():
        d = json.loads(Path(oas_yol).read_text())
        yollar = [f"{m.upper()} {p}" for p, ops in d.get("paths", {}).items() if "personaliz" in p for m in ops]
        (out / "OAS_PERSONALIZATION.txt").write_text("\n".join(yollar) + "\n")
        log(f"OAS personalization uclari: {yollar}")
    return satirlar, ref, sayac


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--oas", default="")
    a = ap.parse_args()
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    calis(api, os.environ["ETSY_SHOP_ID"], a.ids, a.out, a.oas)


if __name__ == "__main__":
    main()
