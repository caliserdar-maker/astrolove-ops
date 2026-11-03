#!/usr/bin/env python3
"""YD (1st Anniversary) Heading talimati duzeltmesi (Serdar 3 Kas Soru 7 + Soru 14 A; pilot 4595350971 onayi 4 Kas "a").
Tek degisiklik: "Heading" sorusunun instructions alani
  ESKI "Paper Anniversary or Our First Year. Poster only; the card says Happy First Anniversary."
  YENI "Paper Anniversary or Our First Year."
KAPI (Serdar 4 Kas, karar 1; "kimlik ayni" kontrolu KALDIRILDI, yerine):
  a) Yazimdan once ve sonraki geri okuma: talimat YENI; diger TUM alanlar (question_text, question_type, required,
     max_allowed_characters, options), soru SIRASI, diger sorular ve ilan basligi / state birebir ayni.
  b) Soru kimlikleri ilan bazinda kaydedilir (KIMLIK.csv: ilan, soru, eski_id, yeni_id, degisti). Kimlik degisimi FAIL degildir.
  c) Siparis hatti eslemesi metinle (formatted_name = question_text); kimlige bagli kod yok. siparis_eslesme_testi() pilotun canli
     soru setiyle kosar; PASS olmadan yazim yok.
Sira (ilan basina): kota kapisi -> GET ilan (state active) -> GET kisisellestirme (5 soru, Heading zorunlu, talimat ESKI ya da zaten YENI)
-> yedek -> POST /shops/{shop}/listings/{id}/personalization (tum set, mevcut question_id'lerle) -> GET geri okuma -> GET ilan.
Herhangi bir FAIL / fark / beklenmeyen durum: DUR (sonraki ilan yok). Ilan yarim birakilmaz (kota ilan basinda kontrol edilir).
Kullanim: yd_talimat_yaz.py --ids a,b,... | --hepsi --out _out [--uygula] [--atla 4595350971]"""
import argparse
import csv
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402

ESKI = "Paper Anniversary or Our First Year. Poster only; the card says Happy First Anniversary."
YENI = "Paper Anniversary or Our First Year."
SORU = "Heading"
ALAN = ("question_text", "question_type", "required", "max_allowed_characters", "instructions", "options")
ISTEK_ILAN = 5   # GET ilan + GET kisisellestirme + POST + GET geri okuma + GET ilan (state/baslik)
KOK = pathlib.Path(__file__).resolve().parents[2]


def govde(sorular):
    """Canli setten POST govdesi: yalniz ALAN + question_id; None alanlar gonderilmez; Heading talimati YENI."""
    out = []
    for q in sorular:
        g = {k: q[k] for k in ALAN if k in q and q[k] is not None}
        if q.get("question_id") is not None:
            g["question_id"] = q["question_id"]
        if q.get("question_text") == SORU:
            g["instructions"] = YENI
        out.append(g)
    return out


def karsilastir(once, sonra):
    """KAPI a: geri okuma -> sorun listesi (bos = PASS). Soru kimligi KARSILASTIRILMAZ (karar 1); sira question_text ile."""
    s = []
    if [q.get("question_text") for q in once] != [q.get("question_text") for q in sonra]:
        return [f"soru sirasi / sayisi degisti: {[q.get('question_text') for q in once]} -> {[q.get('question_text') for q in sonra]}"]
    for a, b in zip(once, sonra):
        for k in ALAN:
            beklenen = YENI if (k == "instructions" and a.get("question_text") == SORU) else a.get(k)
            if (b.get(k) or None) != (beklenen or None):
                s.append(f"{a.get('question_text')}.{k}: {b.get(k)!r} (beklenen {beklenen!r})")
    return s


def kimlik_satir(lid, once, sonra):
    """KAPI b: [(ilan, soru, eski_id, yeni_id, degisti)]"""
    return [dict(listing_id=lid, soru=a.get("question_text"), eski_id=a.get("question_id"), yeni_id=b.get("question_id"),
                 degisti=a.get("question_id") != b.get("question_id")) for a, b in zip(once, sonra)]


def siparis_eslesme_testi(sorular):
    """KAPI c: siparis hatti (siparis_kisisel.ozet + prodigi/kisisel_siparis._kisisel_alanlar) kisisellestirmeyi formatted_name
    (= question_text) ile okur. Pilotun canli soru setinden sahte bir YD kalemi kurulur; ayni kalem iki farkli kimlik setiyle
    (canli ve rastgele) islenir: cikti kimlikten bagimsiz ve 5 cevap soru metniyle eslesmeli. -> (PASS, ayrinti)"""
    import siparis_kisisel as SK
    sys.path.insert(0, str(KOK / "scripts" / "prodigi"))
    import kisisel_siparis as KS
    cevap = {q.get("question_text"): f"TEST{i}" for i, q in enumerate(sorular)}

    def kalem(kimlik):
        return {"listing_id": 1, "sku": "YD-TEST", "variations": [
            {"property_id": kimlik(q), "value_id": None, "formatted_name": q.get("question_text"), "formatted_value": cevap[q.get("question_text")]}
            for q in sorular]}
    a = kalem(lambda q: q.get("question_id"))
    b = kalem(lambda q: 999000000 + sorular.index(q))
    oa, ob = SK.ozet({"receipt_id": 1, "transactions": [a]}), SK.ozet({"receipt_id": 1, "transactions": [b]})
    eslesme = {v["ad"]: v["deger"] for v in oa["kalemler"][0]["varyasyon"]}
    ka, kb = KS._kisisel_alanlar(a), KS._kisisel_alanlar(b)
    sorun = []
    if len(sorular) != 5:
        sorun.append(f"pilot soru sayisi {len(sorular)} (5 beklenir)")
    if oa != ob:
        sorun.append("siparis_kisisel cikti kimlige bagli")
    if ka != kb:
        sorun.append("kisisel_siparis cikti kimlige bagli")
    if eslesme != cevap:
        sorun.append(f"soru metni -> cevap eslesmesi bozuk: {eslesme}")
    if SORU not in eslesme or eslesme.get(SORU) != cevap.get(SORU):
        sorun.append("Heading cevabi okunamadi")
    return not sorun, dict(eslesme_yontemi="formatted_name (soru metni); question_id kullanilmiyor", soru=list(cevap), sorun=sorun)


def oku(api, lid):
    return (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []


def isle(api, shop, lid, out, uygula):
    r = {"listing_id": lid, "url": f"https://www.etsy.com/listing/{lid}"}
    if api.remaining is not None and int(api.remaining) < ISTEK_ILAN + E.KOTA_SINIRI:
        raise SystemExit(f"DUR (kota, ilan baslamadi): {lid} kalan {api.remaining} < {ISTEK_ILAN} + {E.KOTA_SINIRI}")
    L = api.get(f"/listings/{lid}") or {}
    r["state"] = L.get("state")
    if api.remaining is not None and int(api.remaining) < ISTEK_ILAN - 1 + E.KOTA_SINIRI:
        raise SystemExit(f"DUR (kota, ilan baslamadi): {lid} kalan {api.remaining} < {ISTEK_ILAN - 1} + {E.KOTA_SINIRI}")
    if L.get("state") != "active":
        raise SystemExit(f"DUR {lid}: state {L.get('state')} (active degil); yazim yok")
    once = oku(api, lid)
    (out / "YEDEK").mkdir(exist_ok=True)
    (out / "YEDEK" / f"{lid}.json").write_text(json.dumps({"listing_id": lid, "title": L.get("title"), "personalization_questions": once},
                                                          ensure_ascii=False, indent=1))
    h = [q for q in once if q.get("question_text") == SORU]
    if len(once) != 5 or len(h) != 1 or h[0].get("required") is not True:
        raise SystemExit(f"DUR {lid}: beklenen 5 soru + zorunlu tek Heading; okunan {len(once)} soru, Heading {len(h)}")
    r["once"] = h[0].get("instructions")
    if h[0].get("instructions") == YENI:
        r.update(sonuc="ZATEN_YENI", sonra=YENI, sorun=[], kimlik=kimlik_satir(lid, once, once)); return r
    if h[0].get("instructions") != ESKI:
        raise SystemExit(f"DUR {lid}: Heading talimati beklenen ESKI metin degil: {h[0].get('instructions')!r}")
    if not uygula:
        r.update(sonuc="KURU", sorun=[], kimlik=[]); return r
    api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": govde(once)})
    sonra = oku(api, lid)
    L2 = api.get(f"/listings/{lid}") or {}
    (out / "SONRA").mkdir(exist_ok=True)
    (out / "SONRA" / f"{lid}.json").write_text(json.dumps({"listing_id": lid, "personalization_questions": sonra}, ensure_ascii=False, indent=1))
    s = karsilastir(once, sonra)
    if L2.get("state") != "active":
        s.append(f"state {L2.get('state')}")
    if L2.get("title") != L.get("title"):
        s.append("ilan basligi degisti")
    hs = [q for q in sonra if q.get("question_text") == SORU]
    r.update(sonra=hs[0].get("instructions") if hs else None, sorun=s, sonuc="PASS" if not s else "FAIL",
             kimlik=kimlik_satir(lid, once, sonra) if len(once) == len(sonra) else [])
    return r


def yaz_tablolar(out, sonuc):
    with open(out / "GERI_OKUMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "url", "state", "sonuc", "once", "sonra", "sorun"], lineterminator="\n")
        w.writeheader()
        for r in sonuc:
            w.writerow({k: ("; ".join(r.get(k) or []) if k == "sorun" else r.get(k, "")) for k in w.fieldnames})
    with open(out / "KIMLIK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["listing_id", "soru", "eski_id", "yeni_id", "degisti"], lineterminator="\n")
        w.writeheader()
        for r in sonuc:
            w.writerows(r.get("kimlik") or [])
    (out / "SONUC.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=""); ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--atla", default=""); ap.add_argument("--out", required=True); ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--pilot", default="4595350971", help="c testi icin canli soru seti okunan ilan")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.hepsi:
        ids = [r["listing_id"].strip() for r in csv.DictReader(open(KOK / "data/pod/yd78_ids.csv", encoding="utf-8-sig"))]
    else:
        ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    atla = {x.strip() for x in a.atla.split(",") if x.strip()}
    k, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s_)
    if store.needs_refresh():
        store.refresh()
    api = E.Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    calis(api, shop, ids, atla, out, a.uygula, a.pilot)


def calis(api, shop, ids, atla, out, uygula, pilot):
    # KAPI c: pilotun canli soru setiyle siparis eslesme testi (yazimdan ONCE)
    pq = oku(api, pilot)
    ok, ay = siparis_eslesme_testi(pq)
    ay.update(pilot=pilot, pilot_heading_id=[q.get("question_id") for q in pq if q.get("question_text") == SORU],
              pilot_talimat=[q.get("instructions") for q in pq if q.get("question_text") == SORU])
    (out / "C_TESTI.json").write_text(json.dumps(dict(pass_=ok, **ay), ensure_ascii=False, indent=1))
    print(f"::notice title=C-TESTI::{'PASS' if ok else 'FAIL'} | {ay['eslesme_yontemi']} | sorun {ay['sorun']}", flush=True)
    if not ok:
        raise SystemExit("DUR: c testi FAIL; yazim yok")
    tah = len([x for x in ids if x not in atla]) * ISTEK_ILAN
    if api.remaining is not None and int(api.remaining) < tah + E.KOTA_SINIRI:
        print(f"::warning title=YD-TALIMAT::kota {api.remaining} < tahmin {tah} + {E.KOTA_SINIRI}; is bolunur (ilan basi kapi)", flush=True)
    sonuc, hata = [], None
    try:
        for i, lid in enumerate(ids, 1):
            if lid in atla:
                continue
            r = isle(api, shop, lid, out, uygula)
            sonuc.append(r)
            print(f"[{i}/{len(ids)}] {lid} {r['sonuc']} | kota {api.remaining}", flush=True)
            if r["sonuc"] == "FAIL":
                hata = f"DUR {lid}: geri okuma FAIL: {r['sorun']}"; break
    except SystemExit as e:
        hata = str(e)
    yaz_tablolar(out, sonuc)
    print(f"::notice title=YD-TALIMAT::islenen {len(sonuc)} | PASS {sum(r['sonuc'] == 'PASS' for r in sonuc)} | "
          f"ZATEN_YENI {sum(r['sonuc'] == 'ZATEN_YENI' for r in sonuc)} | istek {api.calls} kota {api.remaining}", flush=True)
    if hata:
        raise SystemExit(hata)
    return sonuc


if __name__ == "__main__":
    main()
