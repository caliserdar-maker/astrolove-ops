#!/usr/bin/env python3
"""BY78 78 ILAN YAYINI (14 Eki 2026; az istekli surum 15 Eki). YALNIZ Serdar'in acik onayiyla, Takip calistirir.
Hedef: YALNIZ taslak CSV'deki (Drive TEMP/BY78_TASLAK_20261014/BY78_TASLAKLAR.csv) 78 listing_id.
Kara liste: canli 78 kisisel cift ilani (data/pod/pod78_ids.csv) hedefte varsa HIC istek yapilmadan FAIL.
Az istek (kota tabani 500, Serdar 15 Eki):
  1) Basta 1 toplu okuma (getListingsByListingIds, 100'luk paket): state, shop_id, baslik, etiket. Baska magaza -> yazmadan DUR.
  2) Ilan basina YALNIZ updateListing PATCH govde state=active (tek istek, yeniden deneme YOK). Ek okuma yok:
     PATCH yaniti (guncel ilan) -> state=active, baslik ve etiketler toplu okumayla ayni mi.
  3) 10 yeni yayinda bir ve en sonda toplu okuma: o gruptaki ilanlar state=active + url var mi.
  Beklenmeyen durum (yanit ya da toplu dogrulama) -> o ilan HEMEN state=inactive (tek istek), YAYIN.csv sonuc=geri_alindi, is DURUR.
  Draft olmayan ilan ATLANIR (active: ATLANDI_ZATEN_ACTIVE). Hata ya da kota < 500 -> DUR.
  Betikte tek yazma yolu var: durum(lid, state), state yalniz active ya da inactive; PATCH yanitini dondurur.
Her sonuc aninda YAYIN.csv'ye (cift, listing_id, once, sonra, url, saat, sonuc, not).
--adet N: en fazla N YENI yayin (1 = yalniz ilk; 0 = kalan hepsi).
Istek: adet=1 -> 1 toplu + 1 PATCH + 1 toplu dogrulama = 3. Kalan 77 -> 1 + 77 + ceil(77/10)=8 -> 86.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE
Kullanim: by78_yayinla.py --taslak T.csv --kara data/pod/pod78_ids.csv --out DIR --adet 1"""
import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

KOTA_MIN = 500
GRUP = 10
ALAN = ["cift", "listing_id", "once", "sonra", "url", "saat", "sonuc", "not"]


class Dur(Exception):
    pass


def toplu(api, ids):
    """getListingsByListingIds (100'luk paketler). Donus {listing_id(str): ilan}."""
    L = {}
    for i in range(0, len(ids), 100):
        d = api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}
        for x in d.get("results") or []:
            L[str(x.get("listing_id"))] = x
    return L


def ozet(x):
    x = x or {}
    return dict(state=x.get("state"), url=x.get("url") or "", shop_id=x.get("shop_id"), title=x.get("title"),
                tags=list(x.get("tags") or []))


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


def calistir(api, shop, taslak, kara, out, adet, durum):
    """durum(lid, 'active'|'inactive') -> TEK PATCH (yeniden deneme yok), PATCH yanitini (ilan) dondurur. Donus: cikis kodu."""
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

    def geri_al(c, lid, neden):
        """Beklenmeyen durum: tek inactive PATCH, yanittan state; is DURUR."""
        try:
            y = ozet(durum(lid, "inactive"))                   # tek istek, yeniden deneme yok
        except Exception as e:
            yaz(cift=c, listing_id=lid, once="active", sonra="?", sonuc="GERI_ALMA_HATASI", **{"not": f"{neden} | {str(e)[:200]}"})
            raise Dur(f"{c} {lid}: {neden}; inactive yapilamadi: {str(e)[:200]} -> ELLE PASIF YAPIN")
        yaz(cift=c, listing_id=lid, once="active", sonra=y["state"], url=y["url"],
            sonuc="geri_alindi" if y["state"] == "inactive" else "GERI_ALMA_DOGRULANAMADI", **{"not": neden})
        raise Dur(f"{c} {lid}: {neden}; state=inactive yapildi, simdi {y['state']}")

    def dogrula(grup):
        """Toplu okuma: gruptaki her ilan active + url. Ilk sorunlu ilan geri alinir ve DUR."""
        if not grup:
            return
        T = toplu(api, [lid for _, lid in grup])
        for c, lid in grup:
            s = ozet(T.get(lid))
            if s["state"] != "active" or not s["url"]:
                yaz(cift=c, listing_id=lid, once="draft", sonra=s["state"], url=s["url"], sonuc="FAIL",
                    **{"not": f"toplu dogrulama: state {s['state']}, url {'var' if s['url'] else 'yok'}"})
                if s["state"] == "active":
                    geri_al(c, lid, "toplu dogrulama: url yok")
                raise Dur(f"{c} {lid}: toplu dogrulama FAIL (state {s['state']}); ilan active degil, geri alma gerekmedi")
        print(f"TOPLU DOGRULAMA PASS: {len(grup)} ilan active + url | kota {api.remaining}", flush=True)

    kod = 0
    bekleyen = []                                             # dogrulanmayi bekleyen yeni yayinlar
    dogrulanan = 0
    try:
        ids = [r["listing_id"].strip() for r in taslak]
        O = toplu(api, ids)                                   # 1) tek toplu okuma
        eksik = [i for i in ids if i not in O]
        if eksik:
            raise Dur(f"toplu okumada olmayan ilan {len(eksik)}: {eksik[:3]} (yazma yapilmadi)")
        baska = [i for i in ids if str(O[i].get("shop_id")) != str(shop)]
        if baska:
            raise Dur(f"baska magazanin ilani {len(baska)}: {baska[:3]} (yazma yapilmadi)")
        for i, r in enumerate(taslak, 1):
            c, lid = r["cift"].strip(), r["listing_id"].strip()
            kalan = int(api.remaining) if str(api.remaining or "").isdigit() else None
            if kalan is not None and kalan < KOTA_MIN:
                raise Dur(f"kota {kalan} < {KOTA_MIN}")
            o = ozet(O[lid])
            if o["state"] == "active":
                yaz(cift=c, listing_id=lid, once="active", sonra="active", url=o["url"], sonuc="ATLANDI_ZATEN_ACTIVE"); continue
            if adet and yeni >= adet:
                yaz(cift=c, listing_id=lid, once=o["state"], sonuc="BEKLIYOR", **{"not": f"adet {adet} siniri"}); continue
            if o["state"] != "draft":
                yaz(cift=c, listing_id=lid, once=o["state"], sonra=o["state"], sonuc="ATLANDI_DRAFT_DEGIL",
                    **{"not": f"state {o['state']}; yazilmadi"}); continue
            try:
                s = ozet(durum(lid, "active"))                # 2) tek yazma; yanit = guncel ilan
            except Exception as e:                            # tek deneme: hata -> DUR
                yaz(cift=c, listing_id=lid, once="draft", sonra="?", sonuc="HATA", **{"not": str(e)[:300]})
                raise Dur(f"{c} {lid}: updateListing hatasi: {str(e)[:200]}")
            yeni += 1
            fark = [k for k in ("title", "tags") if s[k] != o[k]]
            ok = s["state"] == "active" and not fark
            yaz(cift=c, listing_id=lid, once="draft", sonra=s["state"], url=s["url"], sonuc="YAYINLANDI" if ok else "FAIL",
                **{"not": "" if ok else f"PATCH yaniti: state {s['state']}, degisen {fark}"})
            if not ok:
                neden = f"PATCH yaniti: state {s['state']}, degisen {fark}"
                if s["state"] != "active":
                    raise Dur(f"{c} {lid}: {neden}; ilan active degil, geri alma gerekmedi")
                geri_al(c, lid, neden)
            bekleyen.append((c, lid))
            if len(bekleyen) >= GRUP:                         # 3) 10 yeni yayinda bir toplu dogrulama
                dogrula(bekleyen); dogrulanan += len(bekleyen); bekleyen = []
            g = time.time() - t0
            print(f"[{i}/{len(taslak)}] {c} {lid} YAYINLANDI | yeni {yeni} | gecen {g:.0f} sn | kota {api.remaining}", flush=True)
        dogrula(bekleyen); dogrulanan += len(bekleyen); bekleyen = []    # en sonda
    except Dur as e:
        print(f"::error::DURDU: {e}")
        kod = 4
    finally:
        f.close()
    say = {}
    for s in satirlar:
        say[s["sonuc"]] = say.get(s["sonuc"], 0) + 1
    ozet_md = [f"# BY78 yayin", "", f"- sonuc: {say}",
               f"- yeni yayin {yeni}, toplu dogrulanan {dogrulanan}, Etsy cagrisi {getattr(api, 'calls', '?')}, kalan kota {api.remaining}",
               f"- durum: {'DURDU' if kod else 'tamam'}"]
    (out / "OZET.md").write_text("\n".join(ozet_md) + "\n", encoding="utf-8")
    print("\n".join(ozet_md), flush=True)
    print(f"::warning::YAYIN {'DURDU' if kod else 'tamam'} | {say} | yeni {yeni} dogrulanan {dogrulanan} | "
          f"Etsy cagrisi {getattr(api, 'calls', '?')} | kota {api.remaining}")
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

    def durum(lid, state):
        if lid not in hedef or lid in kara or not re.fullmatch(r"\d+", lid):
            raise SystemExit(f"YASAK: {lid} hedef listede degil")
        if state not in ("active", "inactive"):
            raise SystemExit(f"YASAK: state {state!r}")
        r = requests.patch(f"{API}/shops/{shop}/listings/{lid}", data={"state": state}, headers=api._headers(), timeout=60)
        api.calls += 1
        if r.headers.get("x-remaining-today") is not None:
            api.remaining = r.headers.get("x-remaining-today")
        if r.status_code != 200:
            raise RuntimeError(f"PATCH {r.status_code}: {r.text[:200]}")
        return r.json()

    sys.exit(calistir(api, shop, taslak, kara, a.out, a.adet, durum))


if __name__ == "__main__":
    main()
