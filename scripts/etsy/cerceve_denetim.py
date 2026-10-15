#!/usr/bin/env python3
"""CERCEVE KALDIRMA + BY ACIKLAMA PLANI icin SALT OKUMA denetimi (15 Eki 2026, Serdar). Etsy'ye yalniz GET; yazma metodu YOK.
Istek (~8): toplu oku eski 78 (images,videos) + toplu oku BY 78 + 2 ornek envanter + 1 ozellik (properties) + kargo profili(leri)
  + acik siparisler (odenmis, gonderilmemis, iptal degil; 100'luk sayfa). Kota tabani 500 (altindaysa baslamaz).
Gorseller: Etsy CDN'den (kota harcamaz) url_570xN indirilir; her gorsel CL kesin galeri kartlarina (data/pod/cl_galeri_final19)
  NCC ile eslenip kart adi verilir; cerceve iceren kartlar (gorsel ya da yazi) CERCEVE_KART ile isaretlenir.
Musteri verisi: yalniz receipt_id, tarih, listing_id, varyasyon; isim/adres/e-posta YAZILMAZ.
Cikti (OUT): ESKI78_ILAN.csv, ESKI78_GORSEL.csv, ESKI78_ACIKLAMA_FRAME.md, ESKI_CL_ACIKLAMA.txt, ESKI_ORNEK_ENVANTER.json,
  ESKI_OZELLIK.json, ESKI_KARGO.json, ACIK_SIPARIS.csv, BY78_FRAME.md, BY_CL_ACIKLAMA.txt, KONTAK_<CIFT>.jpg, OZET.md
Kullanim: cerceve_denetim.py --eski data/pod/pod78_ids.csv --by BY78_TASLAKLAR.csv --kart data/pod/cl_galeri_final19 --out DIR"""
import argparse
import csv
import html
import io
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

KOTA_MIN = 500
CL_ESKI = "4570143815"
FRAME = re.compile(r"\b(frames?|framed|unframed|framing)\b", re.I)
# Kart -> cerceve iceriyor mu (gorsel ya da yazi): CL kesin 19 kart incelemesi (15 Eki)
CERCEVE_KART = {
    "01_kapak": "gorsel: cilali altin cerceve", "02_format": "gorsel+yazi: Framed sutunu", "05_renk_ve_dijital": "yazi: 'Print or Framed'",
    "06_hediye_sahne": "gorsel: altin cerceve", "07_cerceveler": "gorsel+yazi: 4 cerceve karti", "08_boylar": "yazi: 'all 4 frame colors'",
    "09_yatak_sahne": "gorsel+yazi: cerceve + 'four frame finishes'", "10_calisma_sahne": "gorsel+yazi: cerceve + 'four frame finishes'",
    "11_yemek_sahne": "gorsel+yazi: cerceve + 'Framed prints arrive ready to hang'", "13_kagit": "yazi: 'unframed fine art print'",
    "14_surec": "yazi: 'framed prints' (baslik + 04)",
}


def gri(im, w=96, h=72):
    a = np.asarray(im.convert("L").resize((w, h), Image.BILINEAR)).astype(np.float32)
    a -= a.mean()
    return a / (np.sqrt((a * a).sum()) + 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eski", required=True)
    ap.add_argument("--by", required=True)
    ap.add_argument("--kart", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    G = {}

    eski = list(csv.DictReader(open(a.eski)))
    by = [r for r in csv.DictReader(open(a.by)) if r.get("listing_id")]
    ad = {r["listing_id"]: r["cift"] for r in eski}

    def toplu(ids, inc):
        res = []
        for i in range(0, len(ids), 100):
            p = {"listing_ids": ",".join(ids[i:i + 100])}
            if inc:
                p["includes"] = inc
            res += (api.get("/listings/batch", params=p) or {}).get("results") or []
        return {str(x["listing_id"]): x for x in res}

    E = toplu([r["listing_id"] for r in eski], "images,videos")
    kota_bas = int(api.remaining or 0)
    G["kota_bas"] = kota_bas
    if kota_bas and kota_bas < KOTA_MIN:
        raise SystemExit(f"KOTA {kota_bas} < {KOTA_MIN}: DUR")
    B = toplu([r["listing_id"] for r in by], "")

    # --- eski 78: ilan alanlari + aciklama frame satirlari
    ilan_sat, satir_say, ilk = [], Counter(), {}
    for r in eski:
        x = E.get(r["listing_id"]) or {}
        A_, B_ = r["a"], r["b"]
        t = html.unescape(x.get("title") or "")
        d = html.unescape(x.get("description") or "")
        tags = x.get("tags") or []
        mats = x.get("materials") or []
        fl = [ln.strip() for ln in d.splitlines() if FRAME.search(ln)]
        for ln in fl:
            n = ln.replace(A_, "{A}").replace(B_, "{B}")
            satir_say[n] += 1
            ilk.setdefault(n, r["cift"])
        ims = x.get("images") or []
        ilan_sat.append(dict(cift=r["cift"], listing_id=r["listing_id"], state=x.get("state"), baslik=t,
                             baslik_frame=bool(FRAME.search(t)), etiket_frame=";".join(g for g in tags if FRAME.search(g)),
                             materials=";".join(mats), materials_frame=";".join(m for m in mats if FRAME.search(m)),
                             aciklama_frame_satir=len(fl), gorsel=len(ims), video=len(x.get("videos") or []),
                             kargo_profil=x.get("shipping_profile_id"), iade=x.get("return_policy_id"),
                             islem=f"{x.get('processing_min')}-{x.get('processing_max')}",
                             partner=";".join(str(p.get("production_partner_id")) for p in x.get("production_partners") or []),
                             bulunamadi=not x))
    with open(out / "ESKI78_ILAN.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ilan_sat[0])); w.writeheader(); w.writerows(ilan_sat)
    md = ["# Eski 78: aciklamada frame gecen satirlar ({A}/{B} normallestirilmis)", "",
          f"- ilan: {len(E)}/{len(eski)} okundu; frame satiri olan ilan: {sum(1 for x in ilan_sat if x['aciklama_frame_satir'])}", "",
          "| adet | ornek cift | satir |", "|---|---|---|"]
    md += [f"| {n} | {ilk[s_]} | {s_.replace('|', '/')} |" for s_, n in satir_say.most_common()]
    (out / "ESKI78_ACIKLAMA_FRAME.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "ESKI_CL_ACIKLAMA.txt").write_text(html.unescape((E.get(CL_ESKI) or {}).get("description") or ""), encoding="utf-8")

    # --- ornek envanter (CL + ilk satir), ozellikler, kargo profili
    ornek = {}
    for lid in [CL_ESKI, eski[0]["listing_id"]]:
        inv = api.get(f"/listings/{lid}/inventory") or {}
        prods = inv.get("products") or []
        deger = Counter()
        fiyat = {}
        for p in prods:
            pv = {v.get("property_name"): (v.get("values") or [""])[0] for v in p.get("property_values") or []}
            for kk, vv in pv.items():
                deger[(kk, vv)] += 1
            of = (p.get("offerings") or [{}])[0]
            pr = of.get("price") or {}
            fmt = next((vv for kk, vv in pv.items() if "frame" in (kk or "").lower() or "format" in (kk or "").lower()), "")
            fiyat.setdefault(fmt, set()).add((round(pr.get("amount", 0) / (pr.get("divisor") or 1), 2), of.get("quantity"),
                                              of.get("is_enabled"), of.get("readiness_state_id")))
        ornek[ad.get(lid, lid)] = dict(listing_id=lid, urun=len(prods), price_on=inv.get("price_on_property"),
                                       quantity_on=inv.get("quantity_on_property"), sku_on=inv.get("sku_on_property"),
                                       readiness_on=inv.get("readiness_state_on_property"),
                                       degerler=[f"{kk}={vv} x{n}" for (kk, vv), n in sorted(deger.items())],
                                       format_fiyat={kk: sorted(map(list, vv)) for kk, vv in fiyat.items()},
                                       sku_ornek=[p.get("sku") for p in prods[:3]] + [p.get("sku") for p in prods[-3:]])
    (out / "ESKI_ORNEK_ENVANTER.json").write_text(json.dumps(ornek, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    pr = api.get(f"/shops/{shop}/listings/{CL_ESKI}/properties") or {}
    (out / "ESKI_OZELLIK.json").write_text(json.dumps(pr.get("results") or pr, indent=1, ensure_ascii=False), encoding="utf-8")
    kargo = {}
    for sp in sorted({x["kargo_profil"] for x in ilan_sat if x["kargo_profil"]}):
        d = api.get(f"/shops/{shop}/shipping-profiles/{sp}", ok404=True) or {}
        kargo[str(sp)] = dict(baslik=d.get("title"), hedefler=[dict(ulke=h.get("destination_country_iso"), bolge=h.get("destination_region"),
                                                                   ilk=h.get("primary_cost"), ek=h.get("secondary_cost"),
                                                                   teslim=[h.get("min_delivery_days"), h.get("max_delivery_days")])
                                                              for h in d.get("shipping_profile_destinations") or []],
                              ust_secenek=[u.get("upgrade_name") for u in d.get("shipping_profile_upgrades") or []])
    (out / "ESKI_KARGO.json").write_text(json.dumps(kargo, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    # --- acik siparisler (musteri kisisel verisi yazilmaz)
    acik, off = [], 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"was_paid": "true", "was_shipped": "false", "was_canceled": "false",
                                                       "limit": 100, "offset": off}) or {}
        res = d.get("results") or []
        for rc in res:
            for tx in rc.get("transactions") or []:
                var = "; ".join(f"{v.get('formatted_name')}={v.get('formatted_value')}" for v in tx.get("variations") or [])
                acik.append(dict(receipt_id=rc.get("receipt_id"), tarih=rc.get("created_timestamp"), durum=rc.get("status"),
                                 listing_id=tx.get("listing_id"), cift=ad.get(str(tx.get("listing_id")), ""),
                                 eski78=str(tx.get("listing_id")) in ad, varyasyon=var, frame=bool(FRAME.search(var)),
                                 sku=tx.get("sku")))
        off += 100
        if len(res) < 100 or off >= (d.get("count") or 0):
            break
    with open(out / "ACIK_SIPARIS.csv", "w", newline="", encoding="utf-8") as f:
        alan = ["receipt_id", "tarih", "durum", "listing_id", "cift", "eski78", "varyasyon", "frame", "sku"]
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(acik)

    # --- BY 78: frame kelimesi + ornek aciklama
    bmd, bf = ["# BY 78: frame/framed/unframed ve ABOUT OUR DESIGNS", "", "| cift | baslik | etiket | aciklama satiri | ABOUT | FORMATS satiri (Shipped) |", "|---|---|---|---|---|---|"], 0
    for r in by:
        x = B.get(str(r["listing_id"])) or {}
        t = html.unescape(x.get("title") or ""); d = html.unescape(x.get("description") or "")
        n_d = sum(1 for ln in d.splitlines() if FRAME.search(ln))
        tg = [g for g in x.get("tags") or [] if FRAME.search(g)]
        ship = next((ln.strip() for ln in d.splitlines() if ln.strip().lower().startswith("- shipped print")), "")
        if FRAME.search(t) or tg or n_d:
            bf += 1
        bmd.append(f"| {r['cift']} | {bool(FRAME.search(t))} | {';'.join(tg)} | {n_d} | {'ABOUT OUR DESIGNS' in d} | {ship} |")
        if r["cift"] == "CANCER_LIBRA":
            (out / "BY_CL_ACIKLAMA.txt").write_text(d, encoding="utf-8")
    bmd.insert(2, f"- BY ilan okundu {len(B)}/{len(by)}; frame gecen ilan: {bf}")
    (out / "BY78_FRAME.md").write_text("\n".join(bmd) + "\n", encoding="utf-8")
    G["istek"] = api.calls
    G["kota_son"] = api.remaining

    # --- gorseller: CDN indir (kota yok) + kart eslemesi
    kartlar = {p.stem: gri(Image.open(p)) for p in sorted(Path(a.kart).glob("*.jpg"))}
    isler = []
    for r in eski:
        x = E.get(r["listing_id"]) or {}
        for im in sorted(x.get("images") or [], key=lambda y: y.get("rank") or 0):
            isler.append((r["cift"], im.get("rank"), im.get("listing_image_id"), im.get("url_570xN"), im.get("full_width"), im.get("full_height")))
    ses = requests.Session()

    def indir(it):
        try:
            rr = ses.get(it[3], timeout=60); rr.raise_for_status()
            return it, Image.open(io.BytesIO(rr.content)).convert("RGB")
        except Exception as e:                                   # noqa: BLE001
            return it, str(e)[:120]
    gor, kucuk = [], {}
    kontak = {"CANCER_LIBRA", eski[0]["cift"], "SCORPIO_TAURUS"}
    with ThreadPoolExecutor(16) as ex:
        for i, (it, im) in enumerate(ex.map(indir, isler), 1):
            cift, rank, iid, url, fw, fh = it
            if isinstance(im, str):
                gor.append(dict(cift=cift, rank=rank, image_id=iid, boyut=f"{fw}x{fh}", kart="INDIRILEMEDI", skor="", cerceve=im)); continue
            g = gri(im)
            sk = {kk: float((g * v).sum()) for kk, v in kartlar.items()}
            en = max(sk, key=sk.get)
            gor.append(dict(cift=cift, rank=rank, image_id=iid, boyut=f"{fw}x{fh}", kart=en, skor=round(sk[en], 3),
                            cerceve=CERCEVE_KART.get(en, "")))
            if cift in kontak:
                t = im.copy(); t.thumbnail((380, 380)); kucuk.setdefault(cift, []).append((rank, en, sk[en], t))
            if i % 200 == 0:
                print(f"gorsel {i}/{len(isler)} | %{i / len(isler) * 100:.0f}", flush=True)
    with open(out / "ESKI78_GORSEL.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cift", "rank", "image_id", "boyut", "kart", "skor", "cerceve"]); w.writeheader(); w.writerows(gor)
    for cift, lst in kucuk.items():
        lst.sort(key=lambda z: z[0]); cols = 5; W, H = 380, 310
        sh = Image.new("RGB", (cols * W, ((len(lst) + cols - 1) // cols) * H), "white"); dr = ImageDraw.Draw(sh)
        for j, (rank, en, sc, t) in enumerate(lst):
            x0, y0 = (j % cols) * W, (j // cols) * H
            sh.paste(t, (x0, y0 + 20)); dr.text((x0 + 4, y0 + 4), f"rank {rank}: {en} ({sc:.2f}) {'CERCEVE' if en in CERCEVE_KART else ''}", fill="black")
        sh.save(out / f"KONTAK_{cift}.jpg", quality=85)

    # --- ozet
    rk = Counter((g_["rank"], g_["kart"]) for g_ in gor)
    dusuk = [g_ for g_ in gor if g_["skor"] != "" and g_["skor"] < 0.6]
    cerceveli = Counter(g_["kart"] for g_ in gor if g_["cerceve"] and g_["kart"] in CERCEVE_KART)
    gs = Counter(x["gorsel"] for x in ilan_sat)
    o = ["# Cerceve kaldirma denetimi (salt okuma, 15 Eki)", "",
         f"- istek {G['istek']} | kota {kota_bas} -> {G['kota_son']}",
         f"- eski 78 okundu {len(E)}; state {dict(Counter(x['state'] for x in ilan_sat))}; gorsel sayisi {dict(gs)}; video {dict(Counter(x['video'] for x in ilan_sat))}",
         f"- baslikta frame {sum(x['baslik_frame'] for x in ilan_sat)}; etikette frame {sum(1 for x in ilan_sat if x['etiket_frame'])}; materials frame {sum(1 for x in ilan_sat if x['materials_frame'])}",
         f"- aciklamada frame satiri olan ilan {sum(1 for x in ilan_sat if x['aciklama_frame_satir'])} (benzersiz satir {len(satir_say)})",
         f"- kargo profilleri {kargo and list(kargo)} | islem {dict(Counter(x['islem'] for x in ilan_sat))} | partner {dict(Counter(x['partner'] for x in ilan_sat))}",
         f"- gorsel indirildi {sum(1 for g_ in gor if g_['kart'] != 'INDIRILEMEDI')}/{len(gor)}; eslesme skoru < 0.6: {len(dusuk)}",
         f"- cerceveli kart gorselleri (toplam) {dict(cerceveli)}",
         f"- acik siparis kalemi {len(acik)}; eski78 {sum(1 for z in acik if z['eski78'])}; frame secilmis {sum(1 for z in acik if z['frame'])}",
         "", "## rank -> kart (78 ilan dagilimi)", "", "| rank | kart | ilan |", "|---|---|---|"]
    o += [f"| {r_} | {k_} | {n} |" for (r_, k_), n in sorted(rk.items(), key=lambda z: (z[0][0] or 0, -z[1]))]
    (out / "OZET.md").write_text("\n".join(o) + "\n", encoding="utf-8")
    print("\n".join(o[:12]))
    print(f"::warning::CERCEVE DENETIM | istek {G['istek']} | kota {kota_bas}->{G['kota_son']} | gorsel {len(gor)} | "
          f"acik siparis {len(acik)} (frame {sum(1 for z in acik if z['frame'])}) | dusuk eslesme {len(dusuk)}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
    except Exception as e:                                       # noqa: BLE001
        import traceback
        print(f"::error::{type(e).__name__}: {str(e)[:500]} | {traceback.format_exc()[-700:]}".replace("\n", " / "))
        raise SystemExit(1)
