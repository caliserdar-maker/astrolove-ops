#!/usr/bin/env python3
"""78 POD ilanina magazadaki TEK production partner kaydini baglar (Serdar 30 Eyl: eski iki kayit silindi,
yeni gizli kayit 'Fine art print studio' acildi, 0 ilanda). Ayrica ilan/magaza metinlerinde 'prodigi' gecisini SAYAR.
  --mod kuru : SALT OKUMA. Partner listesi (tam 1 kayit beklenir), 78 ilanin state + mevcut partner'i,
               'prodigi' gecen ilan (baslik/aciklama/etiket) ve magaza metin alanlari. Hicbir yazma yok.
  --mod yaz  : ETSY'YE YAZAR (--confirm PARTNER). Ilan basina: state 'active' degilse ATLA (updateListing taslagi
               yayina alir, CLAUDE.md) -> onceki durum ONCE.csv'ye -> updateListing production_partner_ids -> geri okuma:
               partner bagli + state/baslik/aciklama/etiket/fiyat alanlari degismemis. Ilk FAIL'de DUR.
               --limit N: yalniz ilk N ilan (ilk kosu 1 ile yapilir, UI'da 'Used in 1 listings' gorulur).
Kullanim: pod_partner_bagla.py --mod kuru|yaz --out OUT [--confirm PARTNER] [--limit N]
"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy"))
BEKLE, TEKRAR = 3, 5
SABIT = ("state", "title", "description", "tags", "price", "who_made", "when_made", "is_supply", "shipping_profile_id",
         "return_policy_id", "taxonomy_id", "materials", "shop_section_id")
MAGAZA_ALAN = ("title", "announcement", "sale_message", "digital_sale_message", "policy_additional", "vacation_message")


def log(m):
    print(m, flush=True)


def partner_ids(L):
    x = L.get("production_partner_ids")
    if x is None:
        x = [p.get("production_partner_id") for p in (L.get("production_partners") or [])]
    return sorted(str(i) for i in x or [])


def alan_var(L):
    return "production_partner_ids" in L or "production_partners" in L


def imza(L):
    return {k: json.dumps(L.get(k), sort_keys=True, ensure_ascii=False) for k in SABIT}


def prodigi_say(L):
    yer = []
    if "prodigi" in (L.get("title") or "").lower():
        yer.append("baslik")
    if "prodigi" in (L.get("description") or "").lower():
        yer.append("aciklama")
    if any("prodigi" in (t or "").lower() for t in L.get("tags") or []):
        yer.append("etiket")
    return yer


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["kuru", "yaz"]); ap.add_argument("--out", required=True)
    ap.add_argument("--confirm", default=""); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    a = ap.parse_args()
    yaz = a.mod == "yaz"
    if yaz and a.confirm != "PARTNER":
        raise SystemExit("HATA: --mod yaz icin --confirm PARTNER gerekir.")
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ids = [r["listing_id"] for r in csv.DictReader(open(a.ids, encoding="utf-8"))]
    if len(ids) != 78:
        raise SystemExit(f"HATA: 78 ilan bekleniyordu ({len(ids)}). DUR.")
    md = [f"# POD PARTNER BAGLAMA ({a.mod}) {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", ""]
    blok = []

    P = (api.get(f"/shops/{shop}/production-partners") or {}).get("results") or []
    (out / "PARTNERLER.json").write_text(json.dumps(P, ensure_ascii=False, indent=1))
    for p in P:
        md.append(f"- Partner {p.get('production_partner_id')}: ad='{p.get('partner_name')}' konum='{p.get('location')}'")
    if len(P) != 1:
        blok.append(f"magazada {len(P)} partner kaydi var, tam 1 bekleniyordu")
    pid = str(P[0].get("production_partner_id")) if len(P) == 1 else ""

    def oku():
        L = {}
        for i in range(0, len(ids), 100):
            for x in (api.get("/listings/batch", params={"listing_ids": ",".join(ids[i:i + 100])}) or {}).get("results") or []:
                L[str(x["listing_id"])] = x
        return L

    L = oku()
    eksik = [i for i in ids if i not in L]
    if eksik:
        blok.append(f"{len(eksik)} ilan okunamadi: {eksik[:5]}")
    ornek = L.get(ids[0]) or {}
    (out / "ORNEK_ILAN_ALANLARI.json").write_text(json.dumps(sorted(ornek.keys()), indent=1))
    md.append(f"- Ilan nesnesinde partner alani var mi: {alan_var(ornek)} "
              f"(production_partner_ids={'production_partner_ids' in ornek}, production_partners={'production_partners' in ornek})")
    states, bagli, prod = {}, 0, []
    with open(out / "ONCE.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "state", "partner_ids", "prodigi_gecen"])
        for i in ids:
            x = L.get(i) or {}
            states[x.get("state")] = states.get(x.get("state"), 0) + 1
            if pid and pid in partner_ids(x):
                bagli += 1
            y = prodigi_say(x)
            if y:
                prod.append((i, y))
            w.writerow([i, x.get("state"), ";".join(partner_ids(x)), ";".join(y)])
    md.append(f"- 78 ilan state: {states} | yeni partner'a bagli: {bagli}")
    ysay = {}
    for _, y in prod:
        for z in y:
            ysay[z] = ysay.get(z, 0) + 1
    md.append(f"- 'Prodigi' gecen ilan: {len(prod)} / 78 | yer dagilimi: {ysay or '-'}")
    S = api.get(f"/shops/{shop}") or {}
    sm = [al for al in MAGAZA_ALAN if "prodigi" in str(S.get(al) or "").lower()]
    md.append(f"- Magaza metin alanlarinda 'Prodigi': {sm or 'yok'}")
    if prod:
        x = L[prod[0][0]]
        d = x.get("description") or ""
        j = d.lower().find("prodigi")
        if j >= 0:
            md.append(f"- Ornek aciklama cumlesi ({prod[0][0]}): ...{d[max(0, j - 120):j + 60]}...")

    sonuc = {"YAZILDI": 0, "ZATEN": 0, "ATLA_TASLAK": 0}
    if yaz and not blok:
        hedef = ids[: a.limit] if a.limit else ids
        t0 = time.time()
        for n, lid in enumerate(hedef, 1):
            x0 = api.get(f"/listings/{lid}") or {}
            if x0.get("state") != "active":
                sonuc["ATLA_TASLAK"] += 1
                md.append(f"- {lid}: ATLA state={x0.get('state')} (updateListing taslagi yayina alir)")
                continue
            if pid in partner_ids(x0):
                sonuc["ZATEN"] += 1
                continue
            s0 = imza(x0)
            api.patch(f"/shops/{shop}/listings/{lid}", {"production_partner_ids": pid})
            x1, sorun = {}, []
            for _ in range(TEKRAR):
                time.sleep(BEKLE)
                x1 = api.get(f"/listings/{lid}") or {}
                if pid in partner_ids(x1):
                    break
            if not alan_var(x1):
                sorun.append("geri okumada partner alani yok (dogrulanamadi)")
            elif pid not in partner_ids(x1):
                sorun.append(f"partner bagli degil: {partner_ids(x1)}")
            s1 = imza(x1)
            sorun += [f"degisti:{k2}" for k2 in SABIT if s0[k2] != s1[k2]]
            if sorun:
                md.append(f"- {lid}: FAIL {sorun}")
                sonuc["FAIL"] = lid
                break
            sonuc["YAZILDI"] += 1
            gec = time.time() - t0
            log(f"  {n}/{len(hedef)} %{100 * n // len(hedef)} | gecen {gec:.0f}s | kalan ~{gec / n * (len(hedef) - n):.0f}s | {lid} OK")
        if "FAIL" not in sonuc:
            L2 = oku()
            son = sum(1 for i in ids if pid in partner_ids(L2.get(i) or {}))
            md.append(f"- Son okuma: yeni partner'a bagli {son} / 78")
    md += ["", f"- Sonuc: {sonuc}", f"- BLOK: {blok or 'yok'}", f"- Etsy cagrisi {api.calls} | kota son {api.remaining}"]
    (out / "RAPOR.md").write_text("\n".join(md) + "\n")
    log("\n".join(md))
    if blok or "FAIL" in sonuc:
        raise SystemExit("DUR: BLOK/FAIL (RAPOR.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
