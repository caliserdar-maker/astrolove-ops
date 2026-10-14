#!/usr/bin/env python3
"""BY78 78 ILAN YAYINI (14 Eki 2026). YALNIZ Serdar'in acik onayiyla, Takip calistirir.
Hedef: YALNIZ taslak CSV'deki (Drive TEMP/BY78_TASLAK_20261014/BY78_TASLAKLAR.csv) 78 listing_id.
Kara liste: canli 78 kisisel cift ilani (data/pod/pod78_ids.csv) hedefte varsa HIC istek yapilmadan FAIL.
Her ilan: GET (ilan + envanter) -> state "active" ise ATLA; "draft" degilse ATLA + raporla;
  draft ise TEK yazma: updateListing PATCH /shops/{shop}/listings/{id} govde yalniz state=active (tek istek, yeniden deneme YOK)
  -> GET: state active + url var + baslik/etiket/fiyat yayin oncesiyle ayni; degilse FAIL ve DUR.
Her sonuc aninda YAYIN.csv'ye (cift, listing_id, once, sonra, url, saat, sonuc, not). Hata -> DUR. Kota < 500 -> DUR.
--adet N: en fazla N YENI yayin (1 = yalniz ilk; 0 = kalan hepsi).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE
Tekrar kosu: canli GET ile active olanlar atlanir (yeniden yazilmaz).
Kullanim: by78_yayinla.py --taslak T.csv --kara data/pod/pod78_ids.csv --out DIR --adet 1"""
import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

KOTA_MIN = 500
ALAN = ["cift", "listing_id", "once", "sonra", "url", "saat", "sonuc", "not"]


class Dur(Exception):
    pass


def ozet(api, lid):
    """Yayin oncesi/sonrasi karsilastirma: state, url, shop_id, baslik, etiketler, fiyat tablosu."""
    L = api.get(f"/listings/{lid}", ok404=True)
    if not L:
        raise Dur(f"{lid}: ilan okunamadi (404)")
    inv = api.get(f"/listings/{lid}/inventory") or {}
    fiyat = []
    for p in inv.get("products") or []:
        ad = " / ".join((v.get("values") or ["?"])[0] for v in p.get("property_values") or [])
        o = (p.get("offerings") or [{}])[0]
        pr = o.get("price")
        fiyat.append((ad, round(pr["amount"] / pr["divisor"], 2) if isinstance(pr, dict) and pr.get("divisor") else pr))
    return dict(state=L.get("state"), url=L.get("url") or "", shop_id=L.get("shop_id"), title=L.get("title"),
                tags=list(L.get("tags") or []), fiyat=sorted(fiyat))


def hedef_kontrol(taslak, kara):
    h = []
    ids = [r.get("listing_id", "").strip() for r in taslak]
    cift = [r.get("cift", "").strip() for r in taslak]
    if len(taslak) != 78 or len(set(ids)) != 78 or len(set(cift)) != 78:
        h.append(f"taslak CSV {len(taslak)} satir, {len(set(ids))} farkli id, {len(set(cift))} farkli cift (78 olmali)")
    if any(not i.isdigit() for i in ids):
        h.append(f"rakam olmayan listing_id: {[i for i in ids if not i.isdigit()][:3]}")
    canli = sorted(set(ids) & kara)
    if canli:
        h.append(f"KARA LISTE: canli 78 ilandan {len(canli)} ID hedefte: {canli[:5]}")
    return h


def calistir(api, shop, taslak, kara, out, adet, yayinla):
    """yayinla(lid) -> TEK PATCH state=active (yeniden deneme yok). Donus: cikis kodu."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    h = hedef_kontrol(taslak, kara)
    if h:
        print("::error::HEDEF KONTROL FAIL (Etsy'ye hic istek yapilmadi): " + " | ".join(h))
        return 3
    print("HEDEF KONTROL PASS: 78 farkli taslak ID, canli 78 ilanla kesisim 0", flush=True)
    yeni, t0 = 0, time.time()
    satirlar = []
    f = open(out / "YAYIN.csv", "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=ALAN, lineterminator="\n"); w.writeheader()

    def yaz(**s):
        s.setdefault("saat", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " UTC")
        w.writerow({k: s.get(k, "") for k in ALAN}); f.flush(); satirlar.append(s)

    kod = 0
    try:
        for i, r in enumerate(taslak, 1):
            c, lid = r["cift"].strip(), r["listing_id"].strip()
            kalan = int(api.remaining) if str(api.remaining or "").isdigit() else None
            if kalan is not None and kalan < KOTA_MIN:
                raise Dur(f"kota {kalan} < {KOTA_MIN}")
            if adet and yeni >= adet:
                yaz(cift=c, listing_id=lid, sonuc="BEKLIYOR", **{"not": f"adet {adet} siniri"}); continue
            o = ozet(api, lid)
            if str(o["shop_id"]) != str(shop):
                raise Dur(f"{c} {lid}: baska magazanin ilani (shop_id {o['shop_id']})")
            if o["state"] == "active":
                yaz(cift=c, listing_id=lid, once="active", sonra="active", url=o["url"], sonuc="ATLANDI_ZATEN_ACTIVE"); continue
            if o["state"] != "draft":
                yaz(cift=c, listing_id=lid, once=o["state"], sonra=o["state"], sonuc="ATLANDI_DRAFT_DEGIL",
                    **{"not": f"state {o['state']}; yazilmadi"}); continue
            try:
                yayinla(lid)
            except Exception as e:                       # tek deneme: hata -> DUR
                yaz(cift=c, listing_id=lid, once="draft", sonra="?", sonuc="HATA", **{"not": str(e)[:300]})
                raise Dur(f"{c} {lid}: updateListing hatasi: {str(e)[:200]}")
            yeni += 1
            s = ozet(api, lid)
            fark = [k for k in ("title", "tags", "fiyat") if s[k] != o[k]]
            ok = s["state"] == "active" and bool(s["url"]) and not fark
            yaz(cift=c, listing_id=lid, once="draft", sonra=s["state"], url=s["url"], sonuc="YAYINLANDI" if ok else "FAIL",
                **{"not": "" if ok else f"state {s['state']}, url {'var' if s['url'] else 'yok'}, degisen {fark}"})
            if not ok:
                raise Dur(f"{c} {lid}: yayin sonrasi dogrulama FAIL (state {s['state']}, degisen {fark})")
            g = time.time() - t0
            print(f"[{i}/{len(taslak)}] {c} {lid} YAYINLANDI {s['url']} | yeni {yeni} | gecen {g:.0f} sn | kota {api.remaining}", flush=True)
    except Dur as e:
        print(f"::error::DURDU: {e}")
        kod = 4
    finally:
        f.close()
    say = {}
    for s in satirlar:
        say[s["sonuc"]] = say.get(s["sonuc"], 0) + 1
    ozet_md = [f"# BY78 yayin", "", f"- sonuc: {say}", f"- yeni yayin {yeni}, Etsy cagrisi {getattr(api, 'calls', '?')}, kalan kota {api.remaining}",
               f"- durum: {'DURDU' if kod else 'tamam'}"]
    (out / "OZET.md").write_text("\n".join(ozet_md) + "\n", encoding="utf-8")
    print("\n".join(ozet_md), flush=True)
    return kod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taslak", required=True); ap.add_argument("--kara", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--adet", type=int, required=True)
    a = ap.parse_args()
    taslak = list(csv.DictReader(open(a.taslak, encoding="utf-8-sig")))
    kara = {r["listing_id"].strip() for r in csv.DictReader(open(a.kara, encoding="utf-8-sig"))}
    if len(kara) != 78:
        raise SystemExit(f"HATA: kara liste {len(kara)} ID (78 olmali)")
    h = hedef_kontrol(taslak, kara)
    if h:                                                # Etsy'ye baglanmadan once
        print("::error::HEDEF KONTROL FAIL (Etsy'ye hic istek yapilmadi): " + " | ".join(h))
        sys.exit(3)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import requests
    from etsy_common import API, Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    hedef = {r["listing_id"].strip() for r in taslak}

    def yayinla(lid):
        if lid not in hedef or lid in kara or not re.fullmatch(r"\d+", lid):
            raise SystemExit(f"YASAK: {lid} hedef listede degil")
        r = requests.patch(f"{API}/shops/{shop}/listings/{lid}", data={"state": "active"}, headers=api._headers(), timeout=60)
        api.calls += 1
        if r.headers.get("x-remaining-today") is not None:
            api.remaining = r.headers.get("x-remaining-today")
        if r.status_code != 200:
            raise RuntimeError(f"PATCH {r.status_code}: {r.text[:200]}")

    sys.exit(calistir(api, shop, taslak, kara, a.out, a.adet, yayinla))


if __name__ == "__main__":
    main()
