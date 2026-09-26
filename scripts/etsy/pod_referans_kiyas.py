#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazma YOK) - GOREV 0017: 77 POD ilani referansla (canli Cancer-Libra POD) ayni mi?
Karsilastirma, burc adlari {A}/{B} yer tutucusuyla sablonlanarak yapilir (EN; RU'da hal ekleri nedeniyle burc kokleri).
 1 METIN: baslik sablonu, 13 tag (ortak 8 + cifte ozel 5), EN aciklama, RU aciklama (+ 2. gecis isaretleri).
 2 KISISEL: personalization sorulari (sayi, zorunlu, metin sablonu).
 3 ENVANTER: urun sayisi (16 boy x 5 renk = 80), boy/renk basina fiyat referansla ayni, stok 999, isleme suresi.
 4 GORSEL: foto sayisi, alt_text sirasi (sablonlu), video sayisi.
Toplu okuma includes=images,videos,translations,personalization; envanter ilan basina GET /listings/{id}/inventory.
Cikti: out/POD_REFERANS_KIYAS.csv. Kota tabani 230.
Kullanim: pod_referans_kiyas.py <referans_ilan_id> <metin78_csv>"""
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_TABAN = 230
OUT = Path("out")
BURC_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
           "Aquarius", "Pisces"]
BURC_RU = {"Aries": "Овн|Овен", "Taurus": "Тел[её]ц|Тельц", "Gemini": "Близнец", "Cancer": "Рак", "Leo": "Л[её]в|Льв",
           "Virgo": "Дев", "Libra": "Вес", "Scorpio": "Скорпион", "Sagittarius": "Стрел[её]ц|Стрельц",
           "Capricorn": "Козерог", "Aquarius": "Водоле", "Pisces": "Рыб"}
ISARET = {"en_no_emoji": ("en", "No emoji"), "en_couples": ("en", "couples"), "ru_ingilizce": ("ru", "английскими буквами")}


def kota(api):
    try:
        k = int(api.remaining) if api.remaining is not None else None
    except ValueError:
        k = None
    if k is not None and k < KOTA_TABAN:
        print(f"::warning::DUR: kota {k} < {KOTA_TABAN}", flush=True)
        sys.exit(2)
    return k


def cift_burclari(cift):
    b = [x.strip() for x in re.split(r"\+|&|/", cift or "") if x.strip()]
    return (b + b)[:2] if b else ["", ""]


def sablon(metin, a, b, ru=False):
    """Burc adlarini yer tutucuya cevirir. Ayni burc cifti (Leo + Leo) icin ikisi de {A}."""
    s = metin or ""
    for ad, yer in ((a, "{A}"), (b, "{B}")):
        if not ad:
            continue
        if ru:
            s = re.sub(rf"(?:{BURC_RU.get(ad, ad)})[а-яё]*", yer, s, flags=re.I)
        else:
            s = re.sub(rf"\b{re.escape(ad)}\b", yer, s, flags=re.I)
    return s.replace("{B}", "{A}") if a == b else s


def fark(x, y):
    if x == y:
        return ""
    i = next((k for k, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
    return f"@{i}: ref '{x[max(0, i - 15):i + 25]}' / ilan '{y[max(0, i - 15):i + 25]}' (uzunluk {len(x)}/{len(y)})"


def sorular(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/personalization", ok404=True) or {}
    q = r.get("personalization_questions") if isinstance(r, dict) else None
    return q if isinstance(q, list) else []


def soru_imza(qs, a, b):
    return [f"{sablon(q.get('question_text'), a, b)}|{q.get('question_type')}|zorunlu={bool(q.get('required'))}"
            f"|max={q.get('max_allowed_characters')}" for q in qs if isinstance(q, dict)]


def envanter(L):
    inv = L.get("inventory") or {}
    fiyat, stok, hazir = {}, set(), set()
    for p in inv.get("products") or []:
        anahtar = tuple(sorted((v.get("property_name") or str(v.get("property_id")), "/".join(map(str, v.get("values") or [])))
                               for v in p.get("property_values") or []))
        for o in p.get("offerings") or []:
            pr = o.get("price") or {}
            fiyat[anahtar] = round(pr.get("amount", 0) / (pr.get("divisor") or 100), 2)
            stok.add(o.get("quantity"))
            hazir.add(o.get("readiness_state_id"))
    return len(inv.get("products") or []), fiyat, stok, hazir


def main():
    ref_id, metin78 = sys.argv[1], sys.argv[2]
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    OUT.mkdir(exist_ok=True)
    satirlar = list(csv.DictReader(open(metin78, encoding="utf-8")))
    cift = {r["ilan_id"]: r.get("cift", "") for r in satirlar}
    ids = [r["ilan_id"] for r in satirlar]
    if ref_id not in ids:
        ids.append(ref_id)
    L = {}
    for i in range(0, len(ids), 100):
        # batch includes: images, videos, translations, personalization (inventory DESTEKLENMEZ, 26 Eyl 400 olcumu)
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]),
                                               "includes": "images,videos,translations,personalization"}) or {}
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    print(f"okunan ilan {len(L)}/{len(ids)} | kota {kota(api)}", flush=True)
    ru, soru = {}, {}
    for n, lid in enumerate(ids, 1):
        X = L.get(lid) or {}
        tr = [t for t in X.get("translations") or [] if isinstance(t, dict) and t.get("language") == "ru"]
        ru[lid] = tr[0] if tr else (api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {})
        q = X.get("personalization_questions")
        if not isinstance(q, list) and isinstance(X.get("personalization"), dict):
            q = X["personalization"].get("personalization_questions")
        soru[lid] = q if isinstance(q, list) else sorular(api, shop, lid)
        if X:
            X["inventory"] = api.get(f"/listings/{lid}/inventory", ok404=True) or {}
        if n % 20 == 0:
            print(f"[{n}/{len(ids)}] envanter (+eksik ceviri/soru) | kota {kota(api)}", flush=True)

    R = L[ref_id]
    ra, rb = cift_burclari(cift.get(ref_id) or "Cancer + Libra")
    ref = {
        "baslik": sablon(R.get("title"), ra, rb), "aciklama": sablon(R.get("description"), ra, rb),
        "ru": sablon(ru[ref_id].get("description"), ra, rb, ru=True), "ru_baslik": sablon(ru[ref_id].get("title"), ra, rb, ru=True),
        "soru": soru_imza(soru[ref_id], ra, rb), "env": envanter(R),
        "alt": [sablon(im.get("alt_text"), ra, rb) for im in R.get("images") or []],
        "video": len(R.get("videos") or []),
    }
    ref_etiket = R.get("tags") or []
    ortak = [t for t in ref_etiket if not re.search("|".join(filter(None, [ra, rb])), t, re.I)]
    print("REFERANS " + json.dumps({"ilan": ref_id, "etiket": len(ref_etiket), "ortak_etiket": len(ortak),
                                    "soru": len(ref["soru"]), "urun": ref["env"][0], "stok": sorted(map(str, ref["env"][2])),
                                    "hazirlik": sorted(map(str, ref["env"][3])), "foto": len(ref["alt"]), "video": ref["video"],
                                    "isaret": {k2: (v[1] in (R.get("description") if v[0] == "en" else ru[ref_id].get("description") or ""))
                                               for k2, v in ISARET.items()}}, ensure_ascii=False), flush=True)

    alanlar = ["ilan_id", "cift", "M1_metin", "M1_fark", "M2_kisisel", "M2_fark", "M3_envanter", "M3_fark",
               "M4_gorsel", "M4_fark", "foto", "video", "etiket", "isaret_eksik"]
    sonuc = {"M1_metin": 0, "M2_kisisel": 0, "M3_envanter": 0, "M4_gorsel": 0}
    farkli = {k2: [] for k2 in sonuc}
    with open(OUT / "POD_REFERANS_KIYAS.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar)
        w.writeheader()
        for lid in ids:
            if lid == ref_id:
                continue
            X = L.get(lid)
            if not X:
                w.writerow({"ilan_id": lid, "cift": cift.get(lid), "M1_metin": "OKUNAMADI"})
                for k2 in farkli:
                    farkli[k2].append(lid)
                continue
            a, b = cift_burclari(cift.get(lid))
            e = (lambda t: t.replace("{B}", "{A}")) if a == b else (lambda t: t)   # ayni burc: ref'te de {B} -> {A}
            f1 = []
            if sablon(X.get("title"), a, b) != e(ref["baslik"]):
                f1.append("baslik " + fark(e(ref["baslik"]), sablon(X.get("title"), a, b)))
            et = X.get("tags") or []
            if len(et) != 13 or not set(ortak) <= set(et) or len(set(et) - set(ortak)) != 5:
                f1.append(f"tag {len(et)} (ortak eksik: {sorted(set(ortak) - set(et))}, ozel {len(set(et) - set(ortak))})")
            if sablon(X.get("description"), a, b) != e(ref["aciklama"]):
                f1.append("EN " + fark(e(ref["aciklama"]), sablon(X.get("description"), a, b)))
            xru = sablon(ru[lid].get("description"), a, b, ru=True)
            if xru != e(ref["ru"]):
                f1.append("RU " + fark(e(ref["ru"]), xru))
            if sablon(ru[lid].get("title"), a, b, ru=True) != e(ref["ru_baslik"]):
                f1.append("RU baslik " + fark(e(ref["ru_baslik"]), sablon(ru[lid].get("title"), a, b, ru=True)))
            isaret_eksik = [k2 for k2, v in ISARET.items()
                            if v[1] not in ((X.get("description") or "") if v[0] == "en" else (ru[lid].get("description") or ""))]
            if isaret_eksik:
                f1.append(f"isaret eksik {isaret_eksik}")
            xs = soru_imza(soru[lid], a, b)
            if a == b:                                   # ayni burc: isim sorulari Left/Right name olmali (GOREV 0017)
                ok2 = (len(xs) == len(ref["soru"]) and [x.split("|", 1)[1] for x in xs] == [x.split("|", 1)[1] for x in ref["soru"]]
                       and "left" in xs[0].lower() and "right" in xs[1].lower() and xs[2:] == ref["soru"][2:])
            else:
                ok2 = xs == ref["soru"]
            f2 = [] if ok2 else [f"soru ref {ref['soru']} / ilan {xs}"]
            n, fy, st, hz = envanter(X)
            f3 = []
            if n != ref["env"][0]:
                f3.append(f"urun {n}/{ref['env'][0]}")
            fy_fark = sorted(str(k2) for k2 in set(fy) | set(ref["env"][1]) if fy.get(k2) != ref["env"][1].get(k2))
            if fy_fark:
                f3.append(f"fiyat/varyant farki {len(fy_fark)}: {fy_fark[:3]}")
            if st != ref["env"][2]:
                f3.append(f"stok {sorted(map(str, st))}")
            if hz != ref["env"][3]:
                f3.append(f"hazirlik {sorted(map(str, hz))} / ref {sorted(map(str, ref['env'][3]))}")
            alt = [sablon(im.get("alt_text"), a, b) for im in X.get("images") or []]
            vid = len(X.get("videos") or [])
            f4 = []
            if len(alt) != len(ref["alt"]):
                f4.append(f"foto {len(alt)}/{len(ref['alt'])}")
            elif alt != [e(t) for t in ref["alt"]]:
                f4.append("sira/alt_text " + next(f"#{i + 1}: '{e(p)[:40]}' / '{q[:40]}'" for i, (p, q) in enumerate(zip(ref["alt"], alt)) if e(p) != q))
            if vid != ref["video"]:
                f4.append(f"video {vid}/{ref['video']}")
            satir = {"ilan_id": lid, "cift": cift.get(lid), "foto": len(alt), "video": vid, "etiket": len(et),
                     "isaret_eksik": ",".join(isaret_eksik)}
            for kol, fl, fk in (("M1_metin", f1, "M1_fark"), ("M2_kisisel", f2, "M2_fark"), ("M3_envanter", f3, "M3_fark"),
                                ("M4_gorsel", f4, "M4_fark")):
                satir[kol] = "AYNI" if not fl else "FARKLI"
                satir[fk] = " || ".join(fl)[:900]
                if fl:
                    farkli[kol].append(lid)
                else:
                    sonuc[kol] += 1
            w.writerow(satir)
    toplam = len([x for x in ids if x != ref_id])
    print("OZET " + json.dumps({"toplam": toplam, **{k2: f"{v}/{toplam} ayni" for k2, v in sonuc.items()},
                                "farkli": farkli, "cagri": api.calls, "kota_son": api.remaining}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
