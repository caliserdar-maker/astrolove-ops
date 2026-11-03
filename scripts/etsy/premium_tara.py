#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazim YOK): "premium" / "long-lasting" taramasi (Serdar 3 Kas karari; Merkez 3 Kas adim 2 + YD ek).
Kapsam: magazanin tum AKTIF ilanlari; gruplar: poster78 (data/pod/pod78_ids.csv), yd78 (data/pod/yd78_ids.csv),
kupa_cift / kupa_sade (baslikta "mug"; iki burc adi = cift), diger.
Okunan alanlar: baslik, aciklama, etiket, malzeme, kisisellestirme talimati (EN) + RU ceviri (baslik, aciklama, etiket) +
gorsel alt metinleri. YD78 icin ayrica kisisellestirme sorulari (/listings/{id}/personalization).
Istek: aktif ilan sayfalari (100'luk) + /listings/batch (100'luk, includes=Images,Translations); batch RU cevirisi vermezse
ilan basina /translations/ru; YD 78 x personalization. Baslangic kapisi: kalan >= tahmin + KOTA_SINIRI; her istekte sert taban.
Cikti (--out): TABLO.csv (ilan, grup, cift, alan, dil, ifade, adet, gorsel_id), POSTER_GORSEL.csv (poster gorselleri: rank, id,
alt metin), YD_KISISEL.json, HAM/<ilan>.json, OZET.json."""
import argparse
import csv
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402

DESEN = [("premium", "en", re.compile(r"\bpremium\b", re.I)),
         ("long-lasting", "en", re.compile(r"\blong[\s-]?lasting\b", re.I)),
         ("премиал/премиум", "ru", re.compile(r"преми(?:ал|ум)\w*", re.I)),
         ("стойк", "ru", re.compile(r"стойк\w*", re.I)),
         ("долговеч", "ru", re.compile(r"долговеч\w*", re.I)),
         ("free preview", "en", re.compile(r"\bfree\s+preview", re.I)),
         ("бесплатный макет/превью", "ru", re.compile(r"бесплатн\w*\s+(?:макет|предпросмотр|превью|просмотр)\w*", re.I))]
TUM_KISISEL = os.environ.get("TUM_KISISEL") == "1"   # kuru-poster-yd dali (Merkez 3 Kas): tum aktif ilanlarda kisisellestirme sorulari
BURC = re.compile(r"\b(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)\b", re.I)


class SaltOku(E.Etsy):
    """Yalniz GET; her yazma cagrisi kosuyu durdurur."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)


def eslesmeler(metin):
    out = []
    for ad, dil, rx in DESEN:
        n = len(rx.findall(metin or ""))
        if n:
            out.append((ad, dil, n))
    return out


def ids_oku(yol):
    return {r["listing_id"].strip(): r.get("cift", "") for r in csv.DictReader(open(yol, encoding="utf-8-sig"))}


def grup(lid, L, poster, yd):
    if lid in poster:
        return "poster78", poster[lid]
    if lid in yd:
        return "yd78", yd[lid]
    t = L.get("title") or ""
    if re.search(r"\bmugs?\b", t, re.I):
        b = {m.group(1).title() for m in BURC.finditer(t)}
        cift = re.search(r"\b(and|&)\b", t, re.I) is not None and len(BURC.findall(t)) >= 2
        return ("kupa_cift" if cift else "kupa_sade"), "_".join(sorted(b))
    return "diger", ""


def calis(api, shop, out, poster, yd, tahmin_kapi=True):
    (out / "HAM").mkdir(parents=True, exist_ok=True)
    ids, off = [], 0
    while True:
        j = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": off}) or {}
        r = j.get("results") or []
        ids += [str(x["listing_id"]) for x in r]
        if tahmin_kapi and off == 0:
            tah = 2 + (len(ids) and (int(j.get("count") or len(ids)) // 100 + 1)) * 2 + len(yd) + int(j.get("count") or 0)
            if api.remaining is not None and int(api.remaining) < tah + E.KOTA_SINIRI:
                raise SystemExit(f"DUR: kota {api.remaining} < tahmin {tah} + {E.KOTA_SINIRI}")
        if len(r) < 100:
            break
        off += 100
    L = {}
    for i in range(0, len(ids), 100):
        j = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "Images,Translations"}) or {}
        for x in j.get("results") or []:
            L[str(x["listing_id"])] = x
    satir, poster_g, yd_k, ru_kaynak, tr_bicim, birlesik = [], [], {}, {"batch": 0, "tekil": 0, "yok": 0}, {}, {}
    for lid in ids:
        x = L.get(lid) or {}
        g, cift = grup(lid, x, poster, yd)
        ru = None
        tr = x.get("translations")
        adaylar = []
        if isinstance(tr, dict):            # {"ru": {...}} ya da tek ceviri nesnesi
            adaylar = [dict(v, language=v.get("language", k)) for k, v in tr.items() if isinstance(v, dict)] or [tr]
        elif isinstance(tr, list):
            adaylar = [t for t in tr if isinstance(t, dict)]
        tr_bicim[type(tr).__name__] = tr_bicim.get(type(tr).__name__, 0) + 1
        for t in adaylar:
            if str(t.get("language", "")).lower().startswith("ru"):
                ru = t
        if ru is not None:
            ru_kaynak["batch"] += 1
        else:
            ru = api.get(f"/listings/{lid}/translations/ru", ok404=True)
            ru_kaynak["tekil" if ru else "yok"] += 1
        ru = ru or {}
        alanlar = [("baslik", "EN", x.get("title")), ("aciklama", "EN", x.get("description")),
                   ("etiket", "EN", " | ".join(x.get("tags") or [])), ("malzeme", "EN", " | ".join(x.get("materials") or [])),
                   ("kisisellestirme_talimati", "EN", x.get("personalization_instructions")),
                   ("baslik", "RU", ru.get("title")), ("aciklama", "RU", ru.get("description")),
                   ("etiket", "RU", " | ".join(ru.get("tags") or []))]
        for alan, dil, metin in alanlar:
            for ad, _, n in eslesmeler(metin):
                satir.append(dict(listing_id=lid, grup=g, cift=cift, alan=alan, dil=dil, ifade=ad, adet=n, gorsel_id=""))
        gor = sorted(x.get("images") or [], key=lambda k: k.get("rank") or 0)
        for k in gor:
            for ad, _, n in eslesmeler(k.get("alt_text")):
                satir.append(dict(listing_id=lid, grup=g, cift=cift, alan="gorsel_alt_metin", dil="EN", ifade=ad, adet=n,
                                  gorsel_id=k.get("listing_image_id")))
            if g == "poster78":
                poster_g.append(dict(listing_id=lid, cift=cift, rank=k.get("rank"), listing_image_id=k.get("listing_image_id"),
                                     alt_text=k.get("alt_text") or ""))
        pers = None
        if g == "yd78" or TUM_KISISEL:
            pers = api.get(f"/listings/{lid}/personalization", ok404=True)
        if g == "yd78":
            yd_k[lid] = dict(cift=cift, is_personalizable=x.get("is_personalizable"),
                             personalization_is_required=x.get("personalization_is_required"),
                             personalization_char_count_max=x.get("personalization_char_count_max"),
                             personalization_instructions=x.get("personalization_instructions"), sorular=pers,
                             ru_personalization=ru.get("personalization_instructions") if ru else None)
        for metin in (json.dumps(pers, ensure_ascii=False) if pers else "",):
            for ad, _, n in eslesmeler(metin):
                satir.append(dict(listing_id=lid, grup=g, cift=cift, alan="kisisellestirme_sorulari", dil="EN/RU", ifade=ad,
                                  adet=n, gorsel_id=""))
        if g in ("poster78", "yd78"):
            birlesik.setdefault(g, {})[lid] = dict(cift=cift, state=x.get("state"), title=x.get("title"), description=x.get("description"),
                                                   tags=x.get("tags"), ru=dict(title=ru.get("title"), description=ru.get("description"),
                                                   tags=ru.get("tags")), personalization=pers, last_modified_timestamp=x.get("last_modified_timestamp"))
        (out / "HAM" / f"{lid}.json").write_text(json.dumps(dict(
            listing_id=lid, grup=g, cift=cift, state=x.get("state"), title=x.get("title"), description=x.get("description"),
            tags=x.get("tags"), materials=x.get("materials"), personalization_instructions=x.get("personalization_instructions"),
            ru=dict(title=ru.get("title"), description=ru.get("description"), tags=ru.get("tags")),
            gorseller=[dict(rank=k.get("rank"), listing_image_id=k.get("listing_image_id"), alt_text=k.get("alt_text")) for k in gor],
            personalization=pers), ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "TABLO.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "grup", "cift", "alan", "dil", "ifade", "adet", "gorsel_id"])
        w.writeheader(); w.writerows(satir)
    with open(out / "POSTER_GORSEL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "cift", "rank", "listing_image_id", "alt_text"])
        w.writeheader(); w.writerows(poster_g)
    for g_, d_ in birlesik.items():   # yedek: canli EN + RU aciklama / baslik / etiket / kisisellestirme (grup basina tek dosya)
        (out / f"YEDEK_{g_.upper()}.json").write_text(json.dumps(d_, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "YD_KISISEL.json").write_text(json.dumps(yd_k, ensure_ascii=False, indent=1), encoding="utf-8")
    gs = {}
    for lid in ids:
        gs.setdefault(grup(lid, L.get(lid) or {}, poster, yd)[0], 0)
        gs[grup(lid, L.get(lid) or {}, poster, yd)[0]] += 1
    ilan_es = {}
    for s in satir:
        ilan_es.setdefault(s["grup"], set()).add(s["listing_id"])
    oz = dict(aktif=len(ids), grup=gs, ru_kaynak=ru_kaynak, ceviri_bicim=tr_bicim, eslesme_satiri=len(satir),
              eslesen_ilan={k: len(v) for k, v in ilan_es.items()}, istek=api.calls, kota_son=api.remaining)
    (out / "OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"::notice::PREMIUM TARA: aktif {len(ids)} {gs} | eslesen ilan {oz['eslesen_ilan']} | ru {ru_kaynak} | "
          f"istek {api.calls} kota {api.remaining}", flush=True)
    return oz


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    kok = KOK.parents[1]
    poster, yd = ids_oku(kok / "data/pod/pod78_ids.csv"), ids_oku(kok / "data/pod/yd78_ids.csv")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    calis(SaltOku(store), os.environ["ETSY_SHOP_ID"], pathlib.Path(a.out), poster, yd)


if __name__ == "__main__":
    main()
