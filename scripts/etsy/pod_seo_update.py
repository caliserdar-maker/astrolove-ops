#!/usr/bin/env python3
"""POD SEO v2: 78 POD ilaninda YALNIZ title, description ve 13 tag (Mo 15 Eyl 2026).

Varsayilan KURU DENEME (dry-run): Etsy'ye hicbir yazma cagrisi yapilmaz.
Yazma yolu yalniz `--apply --confirm CANLI` ile acilir ve ILK HATADA DURUR
(pod_desc_batch'teki "atla, devam et" davranisi burada YOK).

Akis:
  1. pod_changes_v2.json okunur; 78 id ve cift adlari POD_LISTINGS_STATE.csv ile
     birebir eslesmeli, yoksa DUR. Metin siniri kontrolleri (13 tag, tag <= 20
     karakter, baslik <= 140, uzun tire yok) burada da dogrulanir.
  2. OAuth: TokenStore (gerekirse yenile) + 1 salt okur GET /users/me; donen
     shop_id ETSY_SHOP_ID ile karsilastirilir (olmazsa GET /shops/{shop}/listings
     ?limit=1). Token dosyasindaki scope'ta listings_w var mi raporlanir.
     Token/secret degeri ASLA loglanmaz.
  3. Okuma: tek cagri GET /listings/batch?listing_ids=<78 id>. Donmeyen ya da
     title/description/tags eksik gelen ilan icin yalniz o ilana GET /listings/{id}.
     Batch hic calismazsa tekli GET'e gecilir.
  4. Karsilastirma: title/description html kacislari cozulerek birebir
     (pod_desc_set.esit), tags liste olarak birebir.
     ATLA (ucu de ayni) / GUNCELLENECEK (farkli alanlar) / SORUN (state active
     degil, okunamadi).

Kullanim:
  pod_seo_update.py --changes C.json --pod-state P.csv --out OUT [--limit N]
                    [--apply --confirm CANLI] [--quota-min 60]
"""
import argparse
import csv
import html
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
import pod_desc_set as DS  # noqa: E402

ALAN = ("title", "description", "tags")
# Yazmadan once/sonra AYNI kalmasi gereken alanlar (alan varsa karsilastirilir).
# quantity, url ve zaman damgalari haric.
KORUNAN = ["price", "state", "shop_section_id", "taxonomy_id", "shipping_profile_id",
           "return_policy_id", "materials", "who_made", "when_made", "is_supply",
           "has_variations", "should_auto_renew"]
TAG_MAX, BASLIK_MAX, TAG_SAYISI = 20, 140, 13
SUTUN = ["id", "cift", "sonuc", "alanlar", "not"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def burc_kumesi(metin):
    return frozenset(re.findall(r"[A-Za-z]+", (metin or "").upper()))


# ------------------------------------------------------------------ 1) girdi
def degisiklikleri_oku(yol):
    recs = json.loads(pathlib.Path(yol).read_text(encoding="utf-8"))
    if len(recs) != 78 or len({r["id"] for r in recs}) != 78:
        raise SystemExit(f"HATA: {len(recs)} kayit / benzersiz id uyusmuyor. DUR.")
    for r in recs:
        t = r["tags"]
        if len(t) != TAG_SAYISI or len(set(t)) != TAG_SAYISI:
            raise SystemExit(f"HATA: {r['id']} tag sayisi {len(t)} (benzersiz {len(set(t))}). DUR.")
        uzun = [x for x in t if len(x) > TAG_MAX]
        if uzun:
            raise SystemExit(f"HATA: {r['id']} 20 karakteri asan tag: {uzun}. DUR.")
        if len(r["title"]) > BASLIK_MAX:
            raise SystemExit(f"HATA: {r['id']} baslik {len(r['title'])} karakter. DUR.")
        tire = {DS.UZUN_TIRE[c] for c in DS.UZUN_TIRE if c in r["title"] + r["description"]}
        if tire:
            raise SystemExit(f"HATA: {r['id']} uzun tire: {sorted(tire)}. DUR.")
    return recs


def pod_state_oku(yol):
    out = {}
    with open(yol, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lid = (r.get("listing_id") or "").strip()
            if (r.get("stage") or "") == "verified" and lid.isdigit():
                out[lid] = r.get("pair") or ""
    return out


def eslesme_dogrula(recs, pod):
    d_ids, p_ids = {r["id"] for r in recs}, set(pod)
    if d_ids != p_ids:
        raise SystemExit(
            f"HATA: id kumeleri farkli. Yalniz degisiklik dosyasinda: "
            f"{sorted(d_ids - p_ids)[:10]} | yalniz POD state'te: {sorted(p_ids - d_ids)[:10]}. DUR.")
    kotu = [(r["id"], r["pair"], pod[r["id"]]) for r in recs
            if burc_kumesi(r["pair"]) != burc_kumesi(pod[r["id"]])]
    if kotu:
        raise SystemExit(f"HATA: cift adi uyusmayan {len(kotu)} ilan: {kotu[:5]}. DUR.")
    return len(d_ids)


# ------------------------------------------------------------------ 2) OAuth
def oauth_dogrula(api, store, shop):
    """1 salt okur cagri. Donus: (durum_metni, scope_listings_w)."""
    scope = str(store.data.get("scope") or "")
    listings_w = "listings_w" in scope
    try:
        me = api.get("/users/me", ok404=True) or {}
    except SystemExit as ex:
        me, hata = {}, str(ex)[:120]
        log(f"   /users/me basarisiz: {hata}")
    sid = str(me.get("shop_id") or "")
    if sid:
        durum = "OK" if sid == str(shop) else f"FAIL (shop_id {sid} != ETSY_SHOP_ID)"
        return f"/users/me -> {durum}", listings_w
    r = api.get(f"/shops/{shop}/listings", params={"limit": 1}, ok404=True)
    if r is None:
        return "FAIL (/users/me shop_id yok, /shops/{id}/listings okunamadi)", listings_w
    return "OK (yedek: /shops/{shop}/listings?limit=1)", listings_w


# ------------------------------------------------------------------ 3) okuma
def tam_mi(L):
    return bool(L) and all(L.get(k) is not None for k in ALAN)


def toplu_oku(api, ids):
    """GET /listings/batch tek cagri. Donus: ({id: listing}, batch_calisti)."""
    try:
        r = api.get("/listings/batch", params={"listing_ids": ",".join(ids)}) or {}
    except SystemExit as ex:
        log(f"   batch calismadi ({str(ex)[:100]}), tekli GET'e geciliyor")
        return {}, False
    return {str(x.get("listing_id")): x for x in (r.get("results") or []) if x.get("listing_id")}, True


# ------------------------------------------------------------- karsilastirma
def fark_alanlari(L, rec):
    """Farkli olan alan adlari (title/description/tags)."""
    fark = []
    if DS.esit(L.get("title") or "", rec["title"]) == "farkli":
        fark.append("title")
    if DS.esit(L.get("description") or "", rec["description"]) == "farkli":
        fark.append("description")
    if [html.unescape(t) for t in (L.get("tags") or [])] != rec["tags"]:
        fark.append("tags")
    return fark


def yedekle(out, lid, L, sonek="before"):
    p = out / "backups" / f"{lid}.{sonek}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")
    return p.name


def medya_ozet(api, shop, lid):
    return {"galeri": DS.galeri(api, lid), "varyasyon": DS.var_img(api, shop, lid),
            "video": DS.videolar(api, lid), "envanter_fiyat": DS.envanter(api, lid)}


# ------------------------------------------------------------------ 4) yazma
def yaz_ve_dogrula(api, shop, lid, rec, once, out, ilk_ilan):
    """Tek ilani yazar ve dogrular. Basarisizlikta SystemExit (ilk hatada DUR)."""
    if once.get("state") != "active":
        raise SystemExit(f"{lid}: state={once.get('state')} (active degil) - DUR")
    ilk_medya = medya_ozet(api, shop, lid) if ilk_ilan else None
    govde = {"title": rec["title"], "description": rec["description"],
             "tags": ",".join(rec["tags"])}
    api.patch(f"/shops/{shop}/listings/{lid}", govde)
    sonra = None
    for deneme in range(3):
        time.sleep(10)
        sonra = api.get(f"/listings/{lid}") or {}
        if not fark_alanlari(sonra, rec):
            break
        log(f"    geri okuma {deneme + 1}/3 henuz eslesmedi: {fark_alanlari(sonra, rec)}")
    kalan_fark = fark_alanlari(sonra or {}, rec)
    if kalan_fark:
        yedekle(out, lid, sonra or {}, "after_FAIL")
        raise SystemExit(f"{lid}: geri okuma birebir degil ({kalan_fark}) - DUR")
    degisen = [k for k in KORUNAN if k in once and k in sonra and once[k] != sonra[k]]
    if degisen:
        yedekle(out, lid, sonra, "after_FAIL")
        raise SystemExit(f"{lid}: korunmasi gereken alan degisti: {degisen} - DUR")
    if ilk_ilan:
        sonra_medya = medya_ozet(api, shop, lid)
        medya_fark = [k for k in ilk_medya if ilk_medya[k] != sonra_medya[k]]
        if medya_fark:
            yedekle(out, lid, {"once": ilk_medya, "sonra": sonra_medya}, "media_FAIL")
            raise SystemExit(f"{lid}: ilk ilanda medya/envanter farki: {medya_fark} - DUR")
        log("    ilk ilan medya kontrolu: gorseller, varyasyon, video, envanter fiyatlari AYNI")
    yedekle(out, lid, sonra, "after")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changes", required=True)
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--quota-min", type=int, default=60)
    a = ap.parse_args()
    yaz = bool(a.apply)
    if yaz and a.confirm != "CANLI":
        raise SystemExit("HATA: --apply icin --confirm CANLI gerekli. DUR.")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    log("1) Girdi ve POD state eslemesi")
    recs = degisiklikleri_oku(a.changes)
    pod = pod_state_oku(a.pod_state)
    n = eslesme_dogrula(recs, pod)
    log(f"   {n} id ve cift adi POD_LISTINGS_STATE ile birebir eslesti")
    (out / "pod_changes_v2.json").write_text(
        pathlib.Path(a.changes).read_text(encoding="utf-8"), encoding="utf-8")
    if a.limit:
        recs = recs[:a.limit]

    log("2) OAuth")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    shop = os.environ["ETSY_SHOP_ID"]
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    oauth, listings_w = oauth_dogrula(api, store, shop)
    kota_bas = api.remaining
    log(f"   OAuth {oauth} | scope'ta listings_w: {'VAR' if listings_w else 'YOK'} | kota {kota_bas}")

    log("3) Okuma")
    ids = [r["id"] for r in recs]
    kayitlar, batch_ok = toplu_oku(api, ids)
    log(f"   batch: {'calisti' if batch_ok else 'CALISMADI'}, {len(kayitlar)}/{len(ids)} ilan dondu")
    eksik = [i for i in ids if not tam_mi(kayitlar.get(i))]
    if eksik:
        log(f"   tekli GET gerekecek: {len(eksik)} ilan")
    for i, lid in enumerate(eksik, 1):
        if api.remaining is not None and str(api.remaining).isdigit() \
                and int(api.remaining) < a.quota_min:
            raise SystemExit(f"HATA: kota {api.remaining} < {a.quota_min}; "
                             f"{i - 1}/{len(eksik)} tekli okumadan sonra DUR.")
        try:
            kayitlar[lid] = api.get(f"/listings/{lid}", ok404=True) or {}
        except SystemExit as ex:
            kayitlar[lid] = {"_hata": str(ex)[:150]}

    satirlar, guncellenecek, atlanacak, sorunlu = [], [], [], []
    for r in recs:
        lid = r["id"]
        L = kayitlar.get(lid) or {}
        if not tam_mi(L):
            neden = L.get("_hata") or ("ilan donmedi" if not L else "title/description/tags eksik")
            satirlar.append({"id": lid, "cift": r["pair"], "sonuc": "SORUN", "alanlar": "",
                             "not": neden})
            sorunlu.append((lid, neden))
            continue
        yedekle(out, lid, L)
        if L.get("state") != "active":
            satirlar.append({"id": lid, "cift": r["pair"], "sonuc": "SORUN", "alanlar": "",
                             "not": f"state={L.get('state')}"})
            sorunlu.append((lid, f"state={L.get('state')}"))
            continue
        fark = fark_alanlari(L, r)
        if not fark:
            satirlar.append({"id": lid, "cift": r["pair"], "sonuc": "ATLA", "alanlar": "",
                             "not": "title/description/tags zaten ayni"})
            atlanacak.append(lid)
        else:
            satirlar.append({"id": lid, "cift": r["pair"], "sonuc": "GUNCELLENECEK",
                             "alanlar": "+".join(fark), "not": ""})
            guncellenecek.append(lid)
    log(f"   GUNCELLENECEK {len(guncellenecek)} | ATLA {len(atlanacak)} | SORUN {len(sorunlu)}")

    yazildi, hatali, islenmedi, durdu = [], [], [], None
    if yaz:
        log("4) YAZMA (--apply --confirm CANLI)")
        if sorunlu:
            raise SystemExit(f"HATA: {len(sorunlu)} ilan SORUN durumunda ({sorunlu[:3]}). DUR.")
        gerek = 2 * len(guncellenecek) + 60
        if api.remaining is not None and str(api.remaining).isdigit() \
                and int(api.remaining) < gerek:
            raise SystemExit(f"HATA: kota {api.remaining} < gereken {gerek} "
                             f"(2 x {len(guncellenecek)} + 60). HIC YAZILMADI. DUR.")
        t0 = time.time()
        islenmedi = list(guncellenecek)
        for i, lid in enumerate(guncellenecek, 1):
            rec = next(x for x in recs if x["id"] == lid)
            gecen = time.time() - t0
            kalan_sure = gecen / (i - 1) * (len(guncellenecek) - i + 1) if i > 1 else 0
            log(f"[{i}/{len(guncellenecek)} %{(i - 1) / len(guncellenecek) * 100:.0f}] {lid} "
                f"{rec['pair']} | gecen {gecen / 60:.1f} dk, kalan ~{kalan_sure / 60:.1f} dk "
                f"| kota {api.remaining}")
            if api.remaining is not None and str(api.remaining).isdigit() \
                    and int(api.remaining) < 60:
                durdu = f"kota {api.remaining} < 60; {i - 1}/{len(guncellenecek)} ilandan sonra DUR"
                log(f"DUR: {durdu}")
                break
            try:
                taze = api.get(f"/listings/{lid}") or {}
                yedekle(out, lid, taze, "before_apply")
                yaz_ve_dogrula(api, shop, lid, rec, taze, out, ilk_ilan=(len(yazildi) == 0))
            except SystemExit as ex:
                hatali.append((lid, str(ex)[:200]))
                for s in satirlar:
                    if s["id"] == lid:
                        s["sonuc"], s["not"] = "HATA", str(ex)[:150]
                log(f"    HATA: {ex}")
                break
            yazildi.append(lid)
            islenmedi.remove(lid)
            for s in satirlar:
                if s["id"] == lid:
                    s["sonuc"], s["not"] = "YAZILDI", "geri okuma birebir, korunan alanlar ayni"
            log("    YAZILDI + dogrulandi")

    with open(out / "report.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN)
        w.writeheader()
        for s in satirlar:
            w.writerow(s)
    alan_dagilim = {k: sum(1 for s in satirlar if k in (s["alanlar"] or "")) for k in ALAN}
    md = [f"# POD SEO v2 - {'APPLY' if yaz else 'KURU DENEME (dry-run)'} ({simdi()} UTC)", "",
          f"- OAuth: **{oauth}** | token scope'ta `listings_w`: **{'VAR' if listings_w else 'YOK'}**",
          f"- 78 id + cift adi POD_LISTINGS_STATE eslemesi: **OK** ({n} ilan)",
          f"- Okuma: batch {'calisti' if batch_ok else 'CALISMADI'}, tekli GET {len(eksik)} ilan",
          f"- GUNCELLENECEK **{len(guncellenecek)}** | ATLA **{len(atlanacak)}** | SORUN **{len(sorunlu)}**",
          f"- Alan dagilimi: title {alan_dagilim['title']}, description {alan_dagilim['description']}, "
          f"tags {alan_dagilim['tags']}",
          f"- Kota basta {kota_bas} -> sonda {api.remaining} | API cagrisi {api.calls}", ""]
    if yaz:
        md += [f"## Yazma sonucu", "",
               f"- Basarili + dogrulandi: **{len(yazildi)}** {yazildi}",
               f"- Atlandi (zaten ayni): **{len(atlanacak)}**",
               f"- Hatali: **{len(hatali)}** {hatali}",
               f"- Islenmedi: **{len(islenmedi)}** {islenmedi}",
               f"- Durus: {durdu or 'yok'}", ""]
    if atlanacak:
        md += ["## ATLA (id)", "", ", ".join(atlanacak), ""]
    if sorunlu:
        md += ["## SORUN", ""] + [f"- {lid}: {neden}" for lid, neden in sorunlu] + [""]
    md += ["## GUNCELLENECEK", "", "| id | cift | alanlar |", "|---|---|---|"]
    md += [f"| {s['id']} | {s['cift']} | {s['alanlar']} |"
           for s in satirlar if s["sonuc"] in ("GUNCELLENECEK", "YAZILDI", "HATA")]
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    ozet = {"mod": "apply" if yaz else "dry-run", "oauth": oauth, "listings_w": listings_w,
            "eslesme": n, "guncellenecek": len(guncellenecek), "atla": len(atlanacak),
            "sorun": len(sorunlu), "alan": alan_dagilim, "yazildi": len(yazildi),
            "hatali": len(hatali), "islenmedi": len(islenmedi), "durdu": durdu,
            "kota_bas": kota_bas, "kota_son": api.remaining, "cagri": api.calls}
    (out / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"OZET: {json.dumps(ozet, ensure_ascii=False)}")
    if hatali:
        raise SystemExit(f"HATA: {len(hatali)} ilanda yazma/dogrulama basarisiz. DUR.")


if __name__ == "__main__":
    main()
