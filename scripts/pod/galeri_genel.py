#!/usr/bin/env python3
"""GALERIYE 4 GENEL KART (Serdar, 25 Eyl 2026). Kapsam: 77 ilan (Cancer-Libra 4570143815 HARIC).

Hedef sira: 1 mevcut kapak | 2 GENEL_1 kisisellestirme | 3.. mevcut gorseller (renk bagli olanlara
DOKUNULMAZ) | son 3: GENEL_2 olcu, GENEL_3 kagit, GENEL_4 siparis. Eski olcu / kagit / teslimat kartlari
silinir. Toplam <= 20.

Modlar:
  oku : SALT OKUMA, Etsy API KOTASI HARCAMAZ. Drive YEDEK (<ilan>_ONCE.json: images + variation_images)
        okunur; Etsy CDN kucuk resimlerinden fark-hash (dHash) cikarilir. Ilanlar arasinda ORTAK olan
        (cogu ilanda ayni) kartlar "genel eski kart" kumeleridir; hangi kumenin olcu/kagit/teslimat oldugu
        rank + ortaklik ile olculur. Yapi karsilastirmasi + silme plani (PLAN.json) + 3 ornek serit.
  yaz : --listing X (pilot) ya da --hepsi (PLAN'daki kalanlar). --confirm GALERI_GENEL. Her ilan: guncel
        gorseller PLAN ile ayni degilse DOKUNULMAZ; renk bagli gorsel silinmez; sonra tam geri okuma.
"""
import argparse
import csv
import io
import json
import os
import pathlib
import sys
import time

import requests

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))

REF = "4570143815"
PILOT = "4570110641"
ONAY = "GALERI_GENEL"
# Eski genel kartlar sablon sirasiyla (docs/POD_LISTING_TEMPLATE.md EK 3): 6 Paper & Quality (kagit),
# 7 Size Guide (olcu, 5x7/15 boy), 8 Shipping & Care (teslimat). 25 Eyl oku #1: hash tek basina ayirt edemedi
# (ayni tasarim sablonundaki kartlar/sahneler kucuk resimde benzer), 3 ornek seritte gozle dogrulandi.
ESKI_KART_RANK = [6, 7, 8]
BEKLENEN_SAYI = 13
BEKLENEN_BAGLI = (9, 10, 11, 12, 13)
GENEL = ["GENEL_1_kisisellestirme.jpg", "GENEL_2_olcu.jpg", "GENEL_3_kagit.jpg", "GENEL_4_siparis.jpg"]
csv.field_size_limit(10 ** 8)


def log(m):
    print(m, flush=True)


def dhash(img_bytes, n=8):
    from PIL import Image
    im = Image.open(io.BytesIO(img_bytes)).convert("L").resize((n + 1, n))
    px = list(im.getdata())
    bits = 0
    for r in range(n):
        for c in range(n):
            bits = (bits << 1) | (px[r * (n + 1) + c] > px[r * (n + 1) + c + 1])
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def yedek_oku(yol):
    d = json.loads(pathlib.Path(yol).read_text(encoding="utf-8"))
    imgs = sorted(d.get("images") or [], key=lambda x: x.get("rank") or 0)
    bagli = {}
    renk_ad = {}
    for pr in (d.get("inventory") or {}).get("products") or []:
        for pv in pr.get("property_values") or []:
            if (pv.get("property_name") or "").lower() in ("primary color", "color"):
                for vid, ad in zip(pv.get("value_ids") or [], pv.get("values") or []):
                    renk_ad[vid] = ad
    for v in d.get("variation_images") or []:
        bagli[v.get("image_id")] = renk_ad.get(v.get("value_id"), str(v.get("value_id")))
    return imgs, bagli, d.get("listing") or {}


# ------------------------------------------------------------------ oku
def oku(a):
    from PIL import Image, ImageDraw
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(a.csv, encoding="utf-8") as fh:
        cift = {r["ilan_id"]: r["cift"] for r in csv.DictReader(fh)}
    ilanlar = [k for k in cift if k != REF]
    kayit, onbellek = {}, {}
    t0 = time.time()
    for i, lid in enumerate(ilanlar, 1):
        yol = pathlib.Path(a.yedek) / f"{lid}_ONCE.json"
        if not yol.exists():
            kayit[lid] = {"hata": "yedek yok"}
            continue
        imgs, bagli, L = yedek_oku(yol)
        satir = []
        for im in imgs:
            url = im.get("url_170x135") or im.get("url_570xN")
            h = None
            if url:
                try:
                    b = onbellek.get(url) or requests.get(url, timeout=30).content
                    onbellek[url] = b
                    h = dhash(b)
                except Exception as e:
                    log(f"  {lid} r{im.get('rank')}: resim alinamadi {type(e).__name__}")
            satir.append({"rank": im.get("rank"), "id": im.get("listing_image_id"),
                          "w": im.get("full_width"), "h": im.get("full_height"),
                          "bagli": bagli.get(im.get("listing_image_id"), ""), "hash": h,
                          "url": im.get("url_570xN"), "alt": im.get("alt_text") or ""})
        kayit[lid] = {"cift": cift[lid], "state": L.get("state"), "gorseller": satir}
        if i % 10 == 0 or i == len(ilanlar):
            g = time.time() - t0
            log(f"  {i}/{len(ilanlar)} (%{i * 100 // len(ilanlar)}) | gecen {g / 60:.1f} dk | kalan {g / i * (len(ilanlar) - i) / 60:.1f} dk")

    # ortak kartlar: rank basina, ilanlarin cogunda (>= %60) ayni hash (hamming <= 6) -> genel eski kart
    gecerli = {k: v for k, v in kayit.items() if "gorseller" in v}
    yapi = {}
    for lid, v in gecerli.items():
        imz = (len(v["gorseller"]), tuple(g["rank"] for g in v["gorseller"] if g["bagli"]))
        yapi.setdefault(imz, []).append(lid)
    rank_ortak = {}
    maks_rank = max((len(v["gorseller"]) for v in gecerli.values()), default=0)
    for r in range(1, maks_rank + 1):
        hs = [g["hash"] for v in gecerli.values() for g in v["gorseller"] if g["rank"] == r and g["hash"] is not None and not g["bagli"]]
        if not hs:
            continue
        en_iyi = max(hs, key=lambda x: sum(1 for y in hs if hamming(x, y) <= 6))
        oran = sum(1 for y in hs if hamming(en_iyi, y) <= 6) / len(gecerli)
        rank_ortak[r] = round(oran, 2)
    ortak_ranklar = list(ESKI_KART_RANK)

    plan, riskler = {}, []
    for lid, v in gecerli.items():
        bagli_r = tuple(g["rank"] for g in v["gorseller"] if g["bagli"])
        if len(v["gorseller"]) != BEKLENEN_SAYI or bagli_r != BEKLENEN_BAGLI:
            riskler.append(f"{lid}: yapi farkli ({len(v['gorseller'])} gorsel, bagli {bagli_r})")
        sil = [g for g in v["gorseller"] if g["rank"] in ortak_ranklar]
        if any((g["w"] or 0) <= (g["h"] or 0) for g in sil):
            riskler.append(f"{lid}: silinecek kartlardan biri yatay degil (kart olmayabilir)")
        if any(g["bagli"] for g in sil):
            riskler.append(f"{lid}: silinecek gorselde renk bagi var")
        kalan = len(v["gorseller"]) - len(sil) + 4
        if kalan > 20:
            riskler.append(f"{lid}: sonuc {kalan} gorsel > 20")
        if v["state"] != "active":
            riskler.append(f"{lid}: state={v['state']}")
        plan[lid] = {"cift": v["cift"], "once_ids": [g["id"] for g in v["gorseller"]],
                     "sil_ids": [g["id"] for g in sil], "sil_rank": [g["rank"] for g in sil],
                     "bagli_ids": [g["id"] for g in v["gorseller"] if g["bagli"]], "sonuc_sayi": kalan}
    if len(yapi) != 1:
        riskler.append(f"yapi farkli: {len(yapi)} desen -> " + "; ".join(f"{k}: {len(v)} ilan" for k, v in yapi.items()))
    zayif = [r for r in ESKI_KART_RANK if rank_ortak.get(r, 0) < 0.9]
    if zayif:
        riskler.append(f"eski kart ranklarinda ilanlar arasi ortaklik < %90: {zayif} ({rank_ortak})")
    eksik = [k for k, v in kayit.items() if "hata" in v]
    if eksik:
        riskler.append(f"yedegi olmayan ilan: {eksik}")

    (out / "GALERI_PLAN.json").write_text(json.dumps({"ortak_ranklar": ortak_ranklar, "rank_ortaklik": rank_ortak,
                                                       "yapi": {str(k): v for k, v in yapi.items()}, "riskler": riskler,
                                                       "plan": plan}, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "GALERI_LISTE.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ilan", "cift", "rank", "image_id", "boyut", "renk_bagi", "genel_eski_kart", "alt_text"])
        for lid, v in gecerli.items():
            for g in v["gorseller"]:
                w.writerow([lid, v["cift"], g["rank"], g["id"], f"{g['w']}x{g['h']}", g["bagli"] or "-",
                            "SIL" if g["rank"] in ortak_ranklar else "-", g["alt"][:80]])

    # 3 ornek serit: pilot + ilk iki farkli ilan
    ornek = [PILOT] + [k for k in gecerli if k != PILOT][:2]
    for lid in ornek:
        v = gecerli.get(lid)
        if not v:
            continue
        kutu, sut = 300, 6
        n = len(v["gorseller"])
        sat = (n + sut - 1) // sut
        tuval = Image.new("RGB", (sut * kutu, sat * (kutu + 44)), "white")
        d = ImageDraw.Draw(tuval)
        for j, g in enumerate(v["gorseller"]):
            x, y = (j % sut) * kutu, (j // sut) * (kutu + 44)
            try:
                b = requests.get(g["url"], timeout=30).content
                im = Image.open(io.BytesIO(b)).convert("RGB")
                im.thumbnail((kutu - 8, kutu - 8))
                tuval.paste(im, (x + 4, y + 4))
            except Exception:
                d.text((x + 10, y + 10), "resim yok", fill="red")
            etiket = f"#{g['rank']} {g['id']}"
            etiket2 = (f"RENK: {g['bagli']}" if g["bagli"] else "") + ("  SIL (genel eski)" if g["rank"] in ortak_ranklar else "")
            d.text((x + 6, y + kutu + 2), etiket, fill="black")
            d.text((x + 6, y + kutu + 20), etiket2 or f"{g['w']}x{g['h']}", fill="red" if "SIL" in etiket2 else "blue")
        tuval.save(out / f"SERIT_{lid}.jpg", quality=85)

    rapor = [f"# Galeri genel kart — OKU (salt okuma, Etsy API kotasi harcanmadi) — {time.strftime('%Y-%m-%d %H:%M')} UTC", "",
             f"- ilan: {len(ilanlar)} (Cancer-Libra haric) | yedegi okunan: {len(gecerli)}",
             f"- yapi desenleri (gorsel sayisi, renk bagli ranklar): " + "; ".join(f"{k} -> {len(v)} ilan" for k, v in yapi.items()),
             f"- rank basina ilanlar arasi ortaklik: {rank_ortak}",
             f"- genel eski kart ranklari (>= %60 ortak): {ortak_ranklar}",
             f"- ilan basina sonuc gorsel sayisi: {sorted({p['sonuc_sayi'] for p in plan.values()})}",
             f"- renk bagli gorsel silinen ilan: {sum(1 for p in plan.values() if set(p['sil_ids']) & set(p['bagli_ids']))}",
             "", "## Riskler / farkliliklar", ""] + ([f"- {r}" for r in riskler] or ["- YOK: 77 ilan ayni yapida, renk bagli gorsel silinmiyor"])
    metin = "\n".join(rapor)
    (out / "RAPOR_galeri_oku.md").write_text(metin + "\n", encoding="utf-8")
    log(metin)
    return 1 if riskler else 0


# ------------------------------------------------------------------ yaz
def yaz(a):
    from etsy_common import Etsy, TokenStore
    if a.confirm != ONAY:
        sys.exit(f"HATA: yaz --confirm {ONAY} ister")
    out = pathlib.Path(a.out)
    (out / "YEDEK").mkdir(parents=True, exist_ok=True)
    P = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))
    if P.get("riskler"):
        sys.exit(f"HATA: planda risk var, yazilmaz: {P['riskler'][:3]}")
    plan = P["plan"]
    kart = pathlib.Path(a.kartlar)
    for f in GENEL:
        if not (kart / f).exists():
            sys.exit(f"HATA: kart yok: {f}")
    store = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    shop = os.environ["ETSY_SHOP_ID"]
    hedef = [x.strip() for x in a.listing.split(",") if x.strip()] if a.listing else [k for k in plan if k != PILOT]
    sonuc, t0 = [], time.time()

    def anlik(lid):
        imgs = sorted((api.get(f"/listings/{lid}/images") or {}).get("results") or [], key=lambda x: x.get("rank") or 0)
        vi = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
        L = api.get(f"/listings/{lid}") or {}
        return imgs, {v.get("value_id"): v.get("image_id") for v in vi}, L.get("state")

    for i, lid in enumerate(hedef, 1):
        try:
            kalan_kota = int(api.remaining or 99999)
        except ValueError:
            kalan_kota = 99999
        if kalan_kota < a.kota_alt:
            sonuc.append((lid, "DURDU", f"kota {api.remaining} < {a.kota_alt}", "", ""))
            break
        p = plan.get(lid)
        if not p:
            sonuc.append((lid, "ATLANDI", "planda yok", "", ""))
            continue
        imgs0, vb0, st0 = anlik(lid)
        (out / "YEDEK" / f"{lid}_GALERI_ONCE.json").write_text(json.dumps({"images": imgs0, "var": vb0, "state": st0}, indent=1), encoding="utf-8")
        ids0 = [x.get("listing_image_id") for x in imgs0]
        once = ",".join(str(x) for x in ids0)
        kalanlar = [x for x in p["once_ids"] if x not in p["sil_ids"]]
        fazla = sorted(x for x in ids0 if x not in p["once_ids"])
        yarim = (ids0 != p["once_ids"] and not set(p["sil_ids"]) & set(ids0)
                 and [x for x in ids0 if x in p["once_ids"]] == kalanlar and len(fazla) == 4)
        if ids0 != p["once_ids"] and not yarim:
            sonuc.append((lid, "ATLANDI", "gorseller plandan farkli (dokunulmadi)", once, ""))
            continue
        if st0 != "active" or set(p["sil_ids"]) & set(vb0.values()):
            sonuc.append((lid, "ATLANDI", f"kapi: state={st0} / renk bagli silinecek", once, ""))
            continue
        try:
          if yarim:
            yeni = fazla                      # onceki kosuda yuklenmis 4 kart; id sirasi = yukleme sirasi (G1..G4)
          else:
            for iid in p["sil_ids"]:
                api.delete(f"/shops/{shop}/listings/{lid}/images/{iid}")
            yeni = []
            kalan_sayi = len(ids0) - len(p["sil_ids"])
            for j, f in enumerate(GENEL):
                rank = 2 if j == 0 else kalan_sayi + 1 + j          # GENEL_1 -> 2; 2,3,4 -> sona
                with open(kart / f, "rb") as fh:
                    r = api.post_file(f"/shops/{shop}/listings/{lid}/images", {"image": (f, fh, "image/jpeg")}, {"rank": str(rank)})
                yeni.append(r.get("listing_image_id"))
          # Etsy yuklemede rank'i kaydirmiyor (pilot: GENEL_1 3. siraya dustu) -> sira image_ids ile acikca yazilir.
          hedef_sira = [kalanlar[0], yeni[0]] + kalanlar[1:] + yeni[1:]
          api.patch(f"/shops/{shop}/listings/{lid}", {"image_ids": ",".join(str(x) for x in hedef_sira)})
        except SystemExit as e:
            sonuc.append((lid, "FAIL", f"yazma hatasi: {str(e)[:200]}", once, ""))
            if a.listing:
                break
            continue
        imgs1, vb1, st1 = anlik(lid)
        ids1 = [x.get("listing_image_id") for x in imgs1]
        bek = [kalanlar[0], yeni[0]] + kalanlar[1:] + yeni[1:]
        h = []
        if ids1 != bek:
            h.append("sira beklenenden farkli")
        if len(ids1) > 20:
            h.append(f"{len(ids1)} gorsel > 20")
        if vb1 != vb0:
            h.append(f"renk baglari degisti ({len(vb1)}/{len(vb0)})")
        if st1 != st0:
            h.append(f"state {st0} -> {st1}")
        sonra = ",".join(str(x) for x in ids1)
        sonuc.append((lid, "PASS" if not h else "FAIL", "geri okuma temiz" if not h else "; ".join(h), once, sonra))
        g = time.time() - t0
        log(f"  [{i}/{len(hedef)}] {lid} {sonuc[-1][1]} | gecen {g / 60:.1f} dk | kalan {g / i * (len(hedef) - i) / 60:.1f} dk "
            f"| %{i * 100 // len(hedef)} | kota {api.remaining}")
        if a.listing and h:
            break
    with (out / "SONUC_GALERI.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ilan", "sonuc", "not", "once_sira", "sonra_sira"])
        w.writerows(sonuc)
    ok = sum(1 for s in sonuc if s[1] == "PASS")
    metin = "\n".join([f"# Galeri genel kart — YAZ — {time.strftime('%Y-%m-%d %H:%M')} UTC", "",
                       f"- PASS {ok}/{len(hedef)} | islenmeyen {len(hedef) - len(sonuc)} | kota sonda {api.remaining}", ""]
                      + [f"- {s[0]} {s[1]}: {s[2]}" for s in sonuc])
    (out / "RAPOR_galeri_yaz.md").write_text(metin + "\n", encoding="utf-8")
    log(metin)
    return 0 if ok == len(hedef) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--csv", default="_work/METIN_78.csv")
    ap.add_argument("--yedek", default="_work/yedek")
    ap.add_argument("--plan", default="_out/galeri/GALERI_PLAN.json")
    ap.add_argument("--kartlar", default="_work/kartlar")
    ap.add_argument("--out", default="_out/galeri")
    ap.add_argument("--listing", default="")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--kota-alt", type=int, default=400)
    a = ap.parse_args()
    sys.exit(oku(a) if a.mod == "oku" else yaz(a))


if __name__ == "__main__":
    main()
