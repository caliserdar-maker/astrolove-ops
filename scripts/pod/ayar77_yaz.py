#!/usr/bin/env python3
"""AYAR77 YAZMA (Serdar onayi 28 Eyl 2026): 77 POD ilanina CL (4570143815) canli envanteri + v3 aciklama.

Yalniz iki yazma: PUT envanter (?max_variations_supported=3) ve PATCH description.
Renk -> gorsel baglari envanter degisiminde kaybolursa ayni gorsellere yeniden baglanir (POST variation-images).
DOKUNULMAZ ve geri okumada DOGRULANIR: baslik, 13 etiket, gorseller (id + sira), video, state, kisisellestirme
sorulari, nitelikler, kargo/iade/bolum/hazirlik alanlari.
Modlar:
  --mod yedek : SALT OKUMA. Hedef ilanlarin tam yedegi <out>/YEDEK/<id>.json (workflow Drive'a kopyalar,
                sayiyi dogrular, ancak ondan sonra yaz modu kosar).
  --mod yaz   : ETSY'YE YAZAR (--confirm AYAR77 gerekir). Her ilanda: canli state (active degilse dokunulmaz,
                raporlanir) -> canli okuma yedekle ayni mi -> PUT -> tam geri okuma -> renk-gorsel -> PATCH ->
                tam geri okuma. ILK HATADA DUR.
Kullanim: ayar77_yaz.py --mod yedek|yaz --out OUT [--yalniz id,id] [--confirm AYAR77]
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK / "scripts/pod"), str(KOK / "scripts/etsy")]
import ayar77_kuru as K  # noqa: E402
import metin_78_uret as M  # noqa: E402

CL_ID = K.CL_ID
RENK_PID = 200
KOTA_TABAN = 150  # router rezervi (Serdar 28 Eyl)
BEKLE, TEKRAR = 5, 4


def log(m):
    print(m, flush=True)


def kararli(fn, kosul):
    son = None
    for _ in range(TEKRAR):
        time.sleep(BEKLE)
        son = fn()
        if kosul(son):
            return son
    return son


def oku(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    vimg = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    imgs = (api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results") or []
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    q = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions")
    if q is None:
        q = K.sorular_of(L) or []
    props = (api.get(f"/shops/{shop}/listings/{lid}/properties", ok404=True) or {}).get("results") or []
    return {"listing": L, "inventory": inv, "variation_images": vimg, "images": imgs, "videos": vids,
            "questions": q, "properties": props}


def renk_gorsel(inv, vimg):
    """{renk adi: image_id} - envanterdeki renk value_id -> ad."""
    ad = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            if v.get("property_id") == RENK_PID:
                for vid, val in zip(v.get("value_ids") or [], v.get("values") or []):
                    ad[vid] = val
    return {ad.get(r.get("value_id"), f"?{r.get('value_id')}"): r.get("image_id") for r in vimg}


def renk_propu(inv):
    """{renk adi: property_value (value_ids dahil)} - ilanin kendi canli renk degerleri."""
    out = {}
    for p in inv.get("products") or []:
        for v in p.get("property_values") or []:
            if v.get("property_id") == RENK_PID and v.get("values"):
                out.setdefault(v["values"][0], v)
    return out


def plan_kur(cl_inv, inv, a, b):
    plan, sorun = K.hedef_envanter(cl_inv, a, b)
    if sorun:
        raise SystemExit(f"HATA: CL envanterinden plan kurulamadi: {sorun[:3]}. DUR.")
    rp = renk_propu(inv)
    for p in plan["products"]:
        for v in p["property_values"]:
            if v["property_id"] == RENK_PID:
                src = rp.get(v["values"][0])
                if src and src.get("value_ids"):
                    v["value_ids"] = list(src["value_ids"])
    return plan


def sabit_imza(S):
    """Yazmadan once/sonra AYNI kalmasi gereken her sey."""
    L = S["listing"]
    alan = {k: L.get(k) for k in K.AYAR_ALAN + K.PERS_ALAN if k in L}
    return {"title": L.get("title"), "tags": L.get("tags"), "state": L.get("state"),
            "images": [(x.get("listing_image_id"), x.get("rank")) for x in sorted(S["images"], key=lambda x: x.get("rank") or 0)],
            "videos": sorted(v.get("video_id") for v in S["videos"]),
            "questions": K.soru_imza(S["questions"]), "properties": K.nitelik_imza(S["properties"]),
            "alanlar": json.dumps(alan, sort_keys=True, default=str)}


def ilan_yaz(api, shop, lid, cift, a, b, cl_inv, yedek, out):
    S0 = oku(api, shop, lid)
    L0 = S0["listing"]
    if L0.get("state") != "active":
        return "ATLANDI", f"state={L0.get('state')} (active degil, dokunulmadi)"
    if K.imza(S0["inventory"]) != K.imza(yedek["inventory"]) or K.normalize(L0.get("description")) != K.normalize(yedek["listing"].get("description")):
        raise SystemExit(f"HATA: {lid} yedekten sonra degismis (envanter/aciklama). Yazilmadi. DUR.")
    sabit0, rg0 = sabit_imza(S0), renk_gorsel(S0["inventory"], S0["variation_images"])
    plan = plan_kur(cl_inv, S0["inventory"], a, b)
    aciklama = K.normalize(M.uret(cift))
    if M.qc(cift, aciklama):
        raise SystemExit(f"HATA: {lid} aciklama QC {M.qc(cift, aciklama)}. DUR.")
    # 1 envanter
    try:
        api.put_json(f"/listings/{lid}/inventory?max_variations_supported=3", plan)
    except SystemExit as e:
        raise SystemExit(f"HATA: {lid} envanter PUT reddedildi (ilan degismedi): {e}. DUR.")
    inv1 = kararli(lambda: api.get(f"/listings/{lid}/inventory") or {}, lambda x: K.imza(x) == K.imza(plan))
    if K.imza(inv1) != K.imza(plan) or K.on_prop(inv1) != {k: plan.get(k) for k in K.on_prop(inv1)}:
        raise SystemExit(f"HATA: {lid} envanter geri okuma plan ile ayni degil. DUR.")
    # 2 renk -> gorsel (degistiyse ayni gorsellere yeniden bagla)
    rg1 = renk_gorsel(inv1, (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [])
    yeniden = rg1 != rg0
    if yeniden:
        rp = renk_propu(inv1)
        istek = [{"property_id": RENK_PID, "value_id": rp[r]["value_ids"][0], "image_id": int(img)}
                 for r, img in rg0.items() if r in rp]
        if len(istek) != len(rg0):
            raise SystemExit(f"HATA: {lid} renk-gorsel eslemesi kurulamadi ({len(istek)}/{len(rg0)}). DUR.")
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": istek})
        rg1 = renk_gorsel(inv1, kararli(
            lambda: (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
            lambda x: renk_gorsel(inv1, x) == rg0))
        if rg1 != rg0:
            raise SystemExit(f"HATA: {lid} renk-gorsel baglari geri gelmedi: {rg1} != {rg0}. DUR.")
    # 3 aciklama
    if K.normalize(L0.get("description")) != aciklama:
        api.patch(f"/shops/{shop}/listings/{lid}", {"description": aciklama})
    # 4 tam geri okuma
    S2 = kararli(lambda: oku(api, shop, lid), lambda s: K.normalize(s["listing"].get("description")) == aciklama)
    sorun = []
    if K.normalize(S2["listing"].get("description")) != aciklama:
        sorun.append("aciklama")
    if K.imza(S2["inventory"]) != K.imza(plan):
        sorun.append("envanter")
    if renk_gorsel(S2["inventory"], S2["variation_images"]) != rg0:
        sorun.append("renk-gorsel")
    s2 = sabit_imza(S2)
    sorun += [f"degisti:{k}" for k in sabit0 if sabit0[k] != s2[k]]
    (Path(out) / "SONRA").mkdir(parents=True, exist_ok=True)
    (Path(out) / "SONRA" / f"{lid}.json").write_text(json.dumps(S2, ensure_ascii=False, indent=1, default=str))
    if sorun:
        raise SystemExit(f"HATA: {lid} geri okuma FAIL: {sorun}. DUR.")
    return "YAZILDI", (f"{len(S0['inventory'].get('products') or [])}->{len(plan['products'])} urun, aciklama, "
                       f"renk-gorsel {'yeniden baglandi' if yeniden else 'korundu'}, state active, sabitler ayni")


def hedefler(ids_csv, yalniz):
    rows = [r for r in csv.DictReader(open(ids_csv, encoding="utf-8")) if r["listing_id"] != CL_ID]
    if len(rows) != 77:
        raise SystemExit(f"HATA: 77 hedef bekleniyordu ({len(rows)}). DUR.")
    sec = {x.strip() for x in (yalniz or "").split(",") if x.strip()}
    if sec - {r["listing_id"] for r in rows}:
        raise SystemExit(f"HATA: --yalniz listede olmayan id: {sorted(sec - {r['listing_id'] for r in rows})}. DUR.")
    return [r for r in rows if not sec or r["listing_id"] in sec]


def calis(api, shop, mod, out, ids_csv, yalniz="", confirm=""):
    out = Path(out); (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    rows = hedefler(ids_csv, yalniz)
    t0 = time.time()
    if mod == "yedek":
        for n, r in enumerate(rows, 1):
            S = oku(api, shop, r["listing_id"])
            (out / "YEDEK" / f"{r['listing_id']}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=str))
            g = time.time() - t0
            log(f"[{n}/{len(rows)} %{n / len(rows) * 100:.0f}] yedek {r['listing_id']} {r['cift']} state={S['listing'].get('state')} "
                f"| gecen {g:.0f}s kalan ~{g / n * (len(rows) - n):.0f}s | kota {api.remaining}")
        S = oku(api, shop, CL_ID)
        (out / "YEDEK" / f"CL_{CL_ID}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=str))
        log(f"YEDEK TAMAM: {len(rows)} ilan + CL referansi")
        return []
    if confirm != "AYAR77":
        raise SystemExit("HATA: yaz icin --confirm AYAR77 gerekir. DUR.")
    cl = json.loads((out / "YEDEK" / f"CL_{CL_ID}.json").read_text())
    cl_canli = api.get(f"/listings/{CL_ID}/inventory") or {}
    if K.imza(cl_canli) != K.imza(cl["inventory"]) or len(cl_canli.get("products") or []) != 390:
        raise SystemExit("HATA: CL envanteri yedekten sonra degismis ya da 390 degil. DUR.")
    sonuc = []
    for n, r in enumerate(rows, 1):
        lid = r["listing_id"]
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < KOTA_TABAN:
            raise SystemExit(f"DUR: kota {api.remaining} < {KOTA_TABAN}; {n - 1}/{len(rows)} ilandan sonra.")
        yp = out / "YEDEK" / f"{lid}.json"
        if not yp.exists():
            raise SystemExit(f"HATA: {lid} yedegi yok. DUR.")
        durum, not_ = ilan_yaz(api, shop, lid, r["cift"], r["a"], r["b"], cl_canli, json.loads(yp.read_text()), out)
        sonuc.append({"listing_id": lid, "cift": r["cift"], "durum": durum, "not": not_})
        g = time.time() - t0
        log(f"[{n}/{len(rows)} %{n / len(rows) * 100:.0f}] {lid} {r['cift']} {durum}: {not_} | gecen {g:.0f}s "
            f"kalan ~{g / n * (len(rows) - n):.0f}s | kota {api.remaining}")
        with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["listing_id", "cift", "durum", "not"]); w.writeheader(); w.writerows(sonuc)
    log(f"SONUC: yazildi {sum(s['durum'] == 'YAZILDI' for s in sonuc)} | atlandi {sum(s['durum'] == 'ATLANDI' for s in sonuc)} "
        f"| toplam {len(sonuc)} | kota {api.remaining}")
    return sonuc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod", required=True, choices=["yedek", "yaz"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=str(KOK / "data/pod/pod78_ids.csv"))
    ap.add_argument("--yalniz", default="")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.verbose_quota = False
    calis(api, os.environ["ETSY_SHOP_ID"], a.mod, a.out, a.ids, a.yalniz, a.confirm)


if __name__ == "__main__":
    main()
