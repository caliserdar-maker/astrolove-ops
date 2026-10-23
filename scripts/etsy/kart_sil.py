#!/usr/bin/env python3
"""Eski "Fine Art Paper" kartini (Hahnemuhle / Photo Rag / 308 / giclee / cotton yazili gorsel) ilandan kaldirir (Serdar 23 Eki
madde 2). Yerine gorsel konmaz; diger gorsellerin sirasi ve alt metinleri degismez.

Girdi: --ilan, --gorsel (listing_image_id, kagit taramasi GORSEL_OCR.csv bulgusundan), --rank (beklenen sira, orn. 12).
Kapilar (yazimdan once): ilan active; gorsel bu ilanda ve beklenen sirada; renk-gorsel baglarinda (variation-images) yok;
--onay SERDAR_KART_SIL. --kuru: yalniz yedek + plan, silme yok.
Silme: DELETE /shops/{shop}/listings/{ilan}/images/{gorsel} (deleteListingImage).
Geri okuma (PASS/FAIL): gorsel sayisi bir eksik; silinen kimlik yok; kalan kimlikler ayni goreli sirada; her birinin alt metni
ayni; variation-images ayni; state ayni.
Cikti: <out>/YEDEK_<ilan>.json (gorsel listesi + variation-images, silmeden once), PLAN_<ilan>.json, SONUC_<ilan>.json."""
import argparse
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore  # noqa: E402

ONAY = "SERDAR_KART_SIL"
ALAN = ("listing_image_id", "rank", "alt_text", "url_fullxfull", "url_570xN", "full_width", "full_height")


def gorseller(api, lid):
    r = (api.get(f"/listings/{lid}/images") or {}).get("results") or []
    return sorted(({k: x.get(k) for k in ALAN} for x in r), key=lambda x: int(x.get("rank") or 0))


def renk_baglari(api, shop, lid):
    r = api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}
    return sorted(((x.get("property_id"), x.get("value_id"), x.get("image_id")) for x in r.get("results") or []), key=str)


def kapilar(L, once, baglar, gid, rank):
    h = []
    if L.get("state") != "active":
        h.append(f"state {L.get('state')} (active degil)")
    hedef = [x for x in once if str(x["listing_image_id"]) == str(gid)]
    if len(hedef) != 1:
        h.append(f"gorsel {gid} bu ilanda yok")
    elif int(hedef[0]["rank"] or 0) != int(rank):
        h.append(f"gorsel {gid} sira {hedef[0]['rank']} (beklenen {rank})")
    if any(str(b[2]) == str(gid) for b in baglar):
        h.append(f"gorsel {gid} renk-gorsel baginda; silinmez")
    return h


def dogrula(once, sonra, baglar0, baglar1, L0, L1, gid):
    h = []
    kalan0 = [x for x in once if str(x["listing_image_id"]) != str(gid)]
    if len(sonra) != len(once) - 1:
        h.append(f"gorsel sayisi {len(once)} -> {len(sonra)} (beklenen {len(once) - 1})")
    if any(str(x["listing_image_id"]) == str(gid) for x in sonra):
        h.append("silinen gorsel hala var")
    if [x["listing_image_id"] for x in kalan0] != [x["listing_image_id"] for x in sonra]:
        h.append("kalan gorsellerin sirasi degisti")
    alt0 = {x["listing_image_id"]: x.get("alt_text") for x in kalan0}
    fark = [x["listing_image_id"] for x in sonra if alt0.get(x["listing_image_id"]) != x.get("alt_text")]
    if fark:
        h.append(f"alt metni degisen gorsel {fark}")
    if baglar0 != baglar1:
        h.append("renk-gorsel baglari degisti")
    if L0.get("state") != L1.get("state"):
        h.append(f"state {L0.get('state')} -> {L1.get('state')}")
    return h


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ilan", required=True)
    ap.add_argument("--gorsel", required=True)
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--onay", default="")
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not (a.ilan.isdigit() and a.gorsel.isdigit()):
        raise SystemExit("DUR: --ilan ve --gorsel yalniz rakam")
    if not a.kuru and a.onay != ONAY:
        raise SystemExit(f"DUR: silme icin --onay {ONAY}")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop, lid, gid = os.environ["ETSY_SHOP_ID"], a.ilan, a.gorsel
    L0 = api.get(f"/listings/{lid}") or {}
    once, baglar0 = gorseller(api, lid), renk_baglari(api, shop, lid)
    (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(ilan_state=L0.get("state"), gorseller=once, renk_baglari=baglar0),
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    h = kapilar(L0, once, baglar0, gid, a.rank)
    plan = dict(ilan=lid, gorsel=gid, rank=a.rank, gorsel_sayisi=len(once), kapi_hata=h, kuru=a.kuru)
    (out / f"PLAN_{lid}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print("PLAN", json.dumps(plan, ensure_ascii=False), flush=True)
    if h:
        raise SystemExit(f"DUR: {lid}: {'; '.join(h)}; silme yok")
    if a.kuru:
        print(f"KURU: silme yok | istek {api.calls} | kota {api.remaining}", flush=True)
        return
    api.kota_kapisi(f"ilan {lid}")
    api.delete(f"/shops/{shop}/listings/{lid}/images/{gid}")
    for _ in range(3):
        sonra = gorseller(api, lid)
        if len(sonra) == len(once) - 1:
            break
        time.sleep(5)
    L1, baglar1 = api.get(f"/listings/{lid}") or {}, renk_baglari(api, shop, lid)
    h = dogrula(once, sonra, baglar0, baglar1, L0, L1, gid)
    R = dict(ilan=lid, silinen=gid, once=len(once), sonra=len(sonra), hata=h, sonuc="FAIL" if h else "PASS",
             kalan_sira=[x["listing_image_id"] for x in sonra], istek=api.calls, kota=api.remaining)
    (out / f"SONUC_{lid}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SONUC", json.dumps(R, ensure_ascii=False), flush=True)
    store.write()
    sys.exit(0 if not h else 2)


if __name__ == "__main__":
    main()
