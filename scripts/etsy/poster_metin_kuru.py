#!/usr/bin/env python3
"""POSTER aciklama KURU kosusu (SALT OKUMA; Etsy'ye yazim YOK). Serdar 3 Kas Soru 3 A + Soru 11 + 300 dpi a + Soru 13 A; RU Lena onayli.
78 poster (data/pod/pod78_ids.csv): canli EN + RU aciklama -> yalniz 2 satir degisir:
  EN "- Printed on premium matte art paper with long-lasting inks" -> "- Printed on matte art paper"
  EN "- We send a free preview via Etsy Messages within 24 hours." -> "- We send a preview via Etsy Messages within 24 hours." (Soru 11)
  RU = ru_poster.kur(EN sonra, canli envanter boylari)  (Lena onayli satirlar; eski anahtarlar geri alma icin korunur)
Baslik, etiket, malzeme, fiyat, gorsel DEGISMEZ (yedege yazilir; yazicinin geri okuma karsilastirmasi icin).
Kapilar (gercek yazim govdesiyle): html_coz -> metin_yasak_kapisi (UYARI sayisi 0 olmali) + ai_beyan (beyan_var EN/RU) + RU:
ru_poster.izin_ver -> ru_yazim_kapisi(PUT /shops/{shop}/listings/{id}/translations/ru, canli RU baslik + etiket AYNEN).
Istek: 1 batch (Images, Translations) + ilan basina envanter GET (+ RU batch'te yoksa GET) ; ilan basina kota_kapisi.
Cikti (--out): YEDEK.json, ONCE_SONRA.json, FARK.csv, KAPI.json, OZET.json, PILOT_<id>.txt.
Kullanim: poster_metin_kuru.py --out DIR [--ids a,b]"""
import argparse
import csv
import difflib
import html
import json
import os
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
import pod_5x7_kuru as K  # noqa: E402

DEG = [("- Printed on premium matte art paper with long-lasting inks\n", "- Printed on matte art paper\n"),
       ("- We send a free preview via Etsy Messages within 24 hours.", "- We send a preview via Etsy Messages within 24 hours.")]
PILOT = "4570143815"
BOY_ADI = dict(K.BOYLAR)


def boy_kodu(ad):
    if ad in BOY_ADI:
        return BOY_ADI[ad]
    m = re.match(r"^\s*(\d+)\s*[×x]\s*(\d+)\s*[″\"]", ad or "")
    return f"{m.group(1)}x{m.group(2)}" if m else None


def boylar(inv):
    """Canli envanterden boy listesi (property 513 = boyut; pod_5x7_kuru.pv)."""
    out = []
    for p in (inv or {}).get("products") or []:
        v = (K.pv(p, 513).get("values") or [None])[0]
        b = boy_kodu(v)
        if b and b not in out:
            out.append(b)
    return out


def norm(t):
    return html.unescape(t or "").replace("\r\n", "\n")


def fark(a, b):
    return [l for l in difflib.unified_diff(a.split("\n"), b.split("\n"), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]


def plan_ilan(lid, x, ru, inv, shop):
    """-> (kayit, hata listesi). Yazim yok; kapilar gercek govdeyle (UYARI modu; eslesme sayilir)."""
    hata = []
    en0, ru0 = norm(x.get("description")), norm(ru.get("description"))
    en1 = en0
    for a, b in DEG:
        if en1.count(a) != 1:
            hata.append(f"EN satir eslesmesi {en1.count(a)} (1 beklenir): {a.strip()[:45]}")
        en1 = en1.replace(a, b)
    by = boylar(inv)
    ru_kur0, k0 = R.kur(en0, {"boy": by})
    if not k0.get("pass_") or ru_kur0.strip() != ru0.strip():
        hata.append("sablon canli RU ile ayni degil (kur(EN once) != canli RU)")
    ru1, k1 = R.kur(en1, {"boy": by})
    if not k1.get("pass_"):
        hata.append(f"ru_poster.kur FAIL: {k1.get('hata')}")
    E.METIN_UYARI.clear()
    en_govde = E.html_coz({"description": en1})
    ru_govde = E.html_coz({"title": norm(ru.get("title")), "description": ru1, "tags": ",".join(ru.get("tags") or [])})
    kapi = E.metin_yasak_kapisi("PATCH", f"/shops/{shop}/listings/{lid}", data=en_govde)
    kapi += E.metin_yasak_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru", data=ru_govde)
    if kapi:
        hata.append(f"metin kapisi uyari {len(kapi)}: {sorted({(z[0], z[1]) for z in kapi})}")
    if not (E.beyan_var(en1, "en") and E.beyan_var(ru1, "ru")):
        hata.append("AI beyani eksik")
    if not ru.get("title"):
        hata.append("RU baslik okunamadi (yazimda title zorunlu, canli korunur)")
    if k1.get("pass_"):
        try:
            R.izin_ver(lid, ru1, dict(k1, sorunlar=""))
            E.ru_yazim_kapisi("PUT", f"/shops/{shop}/listings/{lid}/translations/ru", data=ru_govde)
        except SystemExit as e:
            hata.append(f"RU kapisi: {e}")
    if x.get("state") != "active":
        hata.append(f"state {x.get('state')} (aktif degil: updateListing taslagi yayina alir; yazilmaz)")
    if re.search(r"[{}]", en1 + ru1):
        hata.append("suslu parantez kaldi")
    k = dict(listing_id=lid, state=x.get("state"), boylar=by, en_once=en0, en_sonra=en1, ru_once=ru0, ru_sonra=ru1,
             en_fark=fark(en0, en1), ru_fark=fark(ru0, ru1), kapi_uyari=len(kapi), hata=hata)
    return k, hata


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--ids", default="")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k_, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k_); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k_, s_)
    if store.needs_refresh():
        store.refresh()
    api, shop = E.Etsy(store), os.environ["ETSY_SHOP_ID"]
    K.salt_okur(api)
    cift = {r["listing_id"].strip(): r["cift"].strip() for r in csv.DictReader(open(KOK.parents[1] / "data/pod/pod78_ids.csv", encoding="utf-8-sig"))}
    ids = [x.strip() for x in a.ids.split(",") if x.strip()] or list(cift)
    calis(api, shop, ids, cift, out)


def calis(api, shop, ids, cift, out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    L = {}
    for i in range(0, len(ids), 100):
        j = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100]), "includes": "Images,Translations"}) or {}
        for x in j.get("results") or []:
            L[str(x["listing_id"])] = x
    yedek, plan, satir, toplam_hata = {}, {}, [], 0
    for n, lid in enumerate(ids, 1):
        api.kota_kapisi(f"ilan {lid}")
        x = L.get(lid) or {}
        tr = x.get("translations") or {}
        ru = tr.get("ru") if isinstance(tr, dict) else next((t for t in tr if str(t.get("language", "")).startswith("ru")), None)
        if not ru or not ru.get("description"):
            ru = api.get(f"/listings/{lid}/translations/ru", ok404=True) or {}
        inv = api.get(f"/listings/{lid}/inventory") or {}
        fiyat = sorted({K.para((o or {}).get("price")) for p in inv.get("products") or [] for o in p.get("offerings") or []})
        yedek[lid] = dict(cift=cift.get(lid, ""), state=x.get("state"), title=x.get("title"), description=x.get("description"),
                          tags=x.get("tags"), materials=x.get("materials"), last_modified_timestamp=x.get("last_modified_timestamp"),
                          gorsel=[im.get("listing_image_id") for im in sorted(x.get("images") or [], key=lambda i: i.get("rank") or 0)],
                          fiyatlar=fiyat, ru=dict(title=ru.get("title"), description=ru.get("description"), tags=ru.get("tags")))
        k, hata = plan_ilan(lid, x, ru, inv, shop)
        plan[lid] = k
        toplam_hata += bool(hata)
        satir.append(dict(listing_id=lid, cift=cift.get(lid, ""), state=x.get("state"), en_degisen=len(k["en_fark"]) // 2,
                          ru_degisen=len(k["ru_fark"]) // 2, en_kar_once=len(k["en_once"]), en_kar_sonra=len(k["en_sonra"]),
                          ru_kar_once=len(k["ru_once"]), ru_kar_sonra=len(k["ru_sonra"]), boy_sayisi=len(k["boylar"]),
                          kapi_uyari=k["kapi_uyari"], baslik_etiket_degisir=False, hata="; ".join(hata)))
        print(f"[{n}/{len(ids)}] {lid} {'PASS' if not hata else 'FAIL ' + '; '.join(hata)[:150]} | kota {api.remaining}", flush=True)
    (out / "YEDEK.json").write_text(json.dumps(yedek, ensure_ascii=False, indent=1))
    (out / "ONCE_SONRA.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    with open(out / "FARK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0]), lineterminator="\n"); w.writeheader(); w.writerows(satir)
    kapi = dict(ilan=len(ids), pass_=len(ids) - toplam_hata, fail=toplam_hata, kapi_uyari_toplam=sum(s["kapi_uyari"] for s in satir),
                degisen_satir={f"{s['en_degisen']}+{s['ru_degisen']}": sum(1 for t in satir if (t['en_degisen'], t['ru_degisen']) == (s['en_degisen'], s['ru_degisen'])) for s in satir})
    (out / "KAPI.json").write_text(json.dumps(kapi, ensure_ascii=False, indent=1))
    (out / "OZET.json").write_text(json.dumps(dict(kapi, istek=api.calls, kota_son=api.remaining), ensure_ascii=False, indent=1))
    if PILOT in plan:
        p = plan[PILOT]
        (out / f"PILOT_{PILOT}.txt").write_text(f"PILOT {PILOT} {cift.get(PILOT, '')}: yalniz aciklama (EN + RU)\n\n== EN\n" + "\n".join(p["en_fark"])
                                               + "\n\n== RU\n" + "\n".join(p["ru_fark"]) + "\n")
    print(f"::notice title=POSTER-KURU::ilan {len(ids)} PASS {kapi['pass_']} FAIL {toplam_hata} | kapi uyari {kapi['kapi_uyari_toplam']} | "
          f"istek {api.calls} kota {api.remaining}", flush=True)
    if toplam_hata:
        raise SystemExit(f"DUR: {toplam_hata} ilan FAIL (FARK.csv hata sutunu)")


if __name__ == "__main__":
    main()
