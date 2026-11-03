#!/usr/bin/env python3
"""YD (1st Anniversary) Heading talimati duzeltmesi (Serdar 3 Kas: Soru 7 + Soru 14 A plan onayi; Merkez 3 Kas A pilotu).
Tek degisiklik: "Heading" sorusunun instructions alani
  ESKI "Paper Anniversary or Our First Year. Poster only; the card says Happy First Anniversary."
  YENI "Paper Anniversary or Our First Year."
Heading zorunlu kalir; diger 4 soru, question_text, required, max_allowed_characters ve question_id'ler aynen gonderilir.
Sira (ilan basina): kota kapisi -> GET ilan (state active) -> GET kisisellestirme (5 soru, Heading talimati ESKI ya da zaten YENI)
-> yedek -> POST /shops/{shop}/listings/{id}/personalization (tum set, question_id korunur) -> GET geri okuma:
talimat birebir YENI, soru kimlikleri ayni sirada ayni, diger alanlar ayni, state active. Herhangi biri tutmazsa DUR (sonraki ilan yok).
Kullanim: yd_talimat_yaz.py --ids 4595350971 --out _out [--uygula]   (--uygula yoksa kuru: POST yok)"""
import argparse
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
ISTEK_ILAN = 5   # GET ilan + GET kisisellestirme + POST + GET geri okuma + GET ilan (state)


def govde(sorular):
    """Canli setten POST govdesi: yalniz SORU_ALAN + question_id; None alanlar gonderilmez; Heading talimati YENI."""
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
    """geri okuma -> sorun listesi (bos = PASS)"""
    s = []
    if [q.get("question_id") for q in once] != [q.get("question_id") for q in sonra]:
        s.append(f"question_id degisti: {[q.get('question_id') for q in once]} -> {[q.get('question_id') for q in sonra]}")
    if len(once) != len(sonra):
        return s + [f"soru sayisi {len(once)} -> {len(sonra)}"]
    for a, b in zip(once, sonra):
        for k in ALAN:
            beklenen = YENI if (k == "instructions" and a.get("question_text") == SORU) else a.get(k)
            if (b.get(k) or None) != (beklenen or None):
                s.append(f"{a.get('question_text')}.{k}: {b.get(k)!r} (beklenen {beklenen!r})")
    return s


def oku(api, lid):
    return (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []


def isle(api, shop, lid, out, uygula):
    r = {"listing_id": lid, "url": f"https://www.etsy.com/listing/{lid}"}
    if api.remaining is not None and int(api.remaining) < ISTEK_ILAN + E.KOTA_SINIRI:
        raise SystemExit(f"DUR: kota {api.remaining} < {ISTEK_ILAN} + {E.KOTA_SINIRI}")
    L = api.get(f"/listings/{lid}") or {}
    r["state"] = L.get("state")
    if api.remaining is not None and int(api.remaining) < ISTEK_ILAN - 1 + E.KOTA_SINIRI:
        raise SystemExit(f"DUR: kota {api.remaining} < {ISTEK_ILAN - 1} + {E.KOTA_SINIRI}")
    if L.get("state") != "active":
        raise SystemExit(f"DUR {lid}: state {L.get('state')} (active degil); yazim yok")
    once = oku(api, lid)
    (out / f"YEDEK_{lid}.json").write_text(json.dumps({"listing_id": lid, "personalization_questions": once}, ensure_ascii=False, indent=1))
    h = [q for q in once if q.get("question_text") == SORU]
    if len(once) != 5 or len(h) != 1 or h[0].get("required") is not True:
        raise SystemExit(f"DUR {lid}: beklenen 5 soru + zorunlu tek Heading; okunan {len(once)} soru, Heading {len(h)}")
    r["once"] = h[0].get("instructions")
    if h[0].get("instructions") == YENI:
        r["sonuc"] = "ZATEN_YENI"; return r
    if h[0].get("instructions") != ESKI:
        raise SystemExit(f"DUR {lid}: Heading talimati beklenen ESKI metin degil: {h[0].get('instructions')!r}")
    g = govde(once)
    (out / f"GOVDE_{lid}.json").write_text(json.dumps({"personalization_questions": g}, ensure_ascii=False, indent=1))
    if not uygula:
        r["sonuc"] = "KURU"; return r
    api.post_json(f"/shops/{shop}/listings/{lid}/personalization", {"personalization_questions": g})
    sonra = oku(api, lid)
    L2 = api.get(f"/listings/{lid}") or {}
    (out / f"SONRA_{lid}.json").write_text(json.dumps({"listing_id": lid, "personalization_questions": sonra}, ensure_ascii=False, indent=1))
    s = karsilastir(once, sonra)
    if L2.get("state") != "active":
        s.append(f"state {L2.get('state')}")
    hs = [q for q in sonra if q.get("question_text") == SORU]
    r.update(sonra=hs[0].get("instructions") if hs else None, kimlik_korundu=not any(x.startswith("question_id") for x in s),
             sorun=s, sonuc="PASS" if not s else "FAIL")
    if s:
        (out / "SONUC.json").write_text(json.dumps([r], ensure_ascii=False, indent=1))
        raise SystemExit(f"DUR {lid}: geri okuma FAIL: {s}")
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True); ap.add_argument("--out", required=True); ap.add_argument("--uygula", action="store_true")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    k, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s_)
    if store.needs_refresh():
        store.refresh()
    api = E.Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    sonuc = []
    for lid in ids:
        r = isle(api, shop, lid, out, a.uygula)
        sonuc.append(r)
        print(f"::notice title=YD-TALIMAT::{lid} {r['sonuc']} | {r.get('once')!r} -> {r.get('sonra', YENI)!r} | kota {api.remaining}", flush=True)
    (out / "SONUC.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1))
    print(f"istek {api.calls} kota {api.remaining}", flush=True)


if __name__ == "__main__":
    main()
