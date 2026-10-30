#!/usr/bin/env python3
"""Poster 78 galeri v11b: Champagne Ivory (CI) gorseli 11. sira + CI renk bagi (Serdar 30 Eki karari). KOSTURMA AYRI ONAYLA.
Sorun: v11b galeri 10 gorsel (1 kapak, 2-6 bilgi kartlari, 7-10 MB / DB / PW / WP renk kartlari), renk baglari 4 (property 200:
MB 7, DB 8, PW 9, WP 10); CI karti 29 Eki uretilmedi, renk menusunde CI secilince gorsel yok. Cozum: her ilanin mevcut CI W01 dosyasi
(TEMP/POSTER_GALERI_V11/<damga>/<CIFT>_W01_KAPAK.jpg, B3 KAPI PASS) rank 11'e yuklenir, CI degeri ona baglanir. 1-10 ve 4 bag DEGISMEZ.
Modlar:
  --kuru : ETSY SALT OKUMA (yd_envanter_oku.salt_okur; yazma yontemleri kapali). Ilan basina 4 GET (ilan, galeri, renk baglari,
           envanter). Kapilar asagida; HAZIR ilanlar PLAN_CI11.json'a girer, plan sha256 -> plan_damga (<kosu>_<sha12>).
  yazim  : --confirm GALERI_CI11 + --plan PLAN_CI11.json + --plan-damga + alt metin sablonu ONAYLI + dosya (sha256 = plan). Ilan basina:
           kota (kalan - en kotu istek >= KOTA_SINIRI 10, ilan baslamadan) -> 4 GET -> canli == plan kapisi (ilan bazinda; farkliysa
           yazma yok) -> yedek (YEDEK_<ilan>.json, ilk yazimdan once; plan zaten Drive'da) -> rank 11 yukleme (eski78 yukle_guvenli: cift
           yukleme yok) -> galeri geri okuma (stabil_galeri: 1-10 kimlik / sira / alt metin ayni, 11 = yeni) -> TEK variation-images
           POST'u (4 eski bag aynen + CI -> yeni) -> bag geri okuma (kararli) -> son geri okuma (galeri, baglar, state active).
           Herhangi bir adim tutmazsa GERI ALMA: baglar eski 4'e (POST + kararli okuma), yeni gorsel silinir (yalniz bu kosunun yukledigi
           kimlik), galeri 1-10 ve baglar dogrulanir. Ilk PASS olmayan ilanda kosu durur (sonrakiler KALAN).
Kapilar (ilan basina, canli okumayla; BLOK = yazma yok):
  dosya kapisi (ci11_dosya_kapi.py CI_KAPI.csv): satir var, durum PASS, ilan / cift ayni; yazimda yerel dosya sha256 = plan.
  state active; galeri tam 10 gorsel, rank 1..10; v11b beklenen durum: rank 2-10 alt metinleri data/pod/galeri_v11_alt.csv (ONAYLI
  satirlar) ile ayni, rank 1 alt metninde "Champagne Ivory" yok; renk baglari tam 4, property 200, MB->7 DB->8 PW->9 WP->10 kimlikleri,
  CI bagi YOK; envanter property 200'de "Champagne Ivory" degeri (value_id) var, 4 bag value_id'leri envanterle ayni;
  --canli-dir verilirse (galeri-v11-yedek-oku GALERI.json) canli 1-10 kimlikleri ve baglar o okumayla ayni; CI alt metni gecerli.
  ZATEN: 11 gorsel, 1-10 v11b, rank 11 alt metni CI metni, 5 bag (CI -> rank 11). YARIM: rank 11 CI metinli ama bag eksik -> BLOK.
Istek (kod okumasi, istek_tahmini()): kuru ilan basina 4; yazim en az 13, en kotu (geri alma dahil) istek_tahmini()["yaz_en_kotu"].
GET okumalarinin etsy_common 5xx / 429 kisa tekrarlari dahil degil (eski78 sozlesmesi; sert taban 10 her istekten once durdurur).
Cikti --out: PLAN_CI11.json (kuru), RAPOR.json, RAPOR.md, SONUC.csv, ilanlar/YEDEK_<ilan>.json, ilanlar/SONRA_<ilan>.json.
updateListing / listing PATCH YOK (taslak yayina alma riski, CLAUDE.md 7 Eyl)."""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
from etsy_common import KOTA_SINIRI  # noqa: E402  (Serdar 15 ve 24 Eki: 10; degistirilmez)

ONAY = "GALERI_CI11"
PLAN_AD = "PLAN_CI11.json"
RENK_PID = 200
CI = "Champagne Ivory"
BAG_SIRA = {"Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}   # v11b (Serdar 29 Eki)
N0, HEDEF_RANK = 10, 11
KAPI_OKUMA = 4      # ilan, galeri, variation-images, envanter
VARSAYILAN_ALT_V11 = KOK.parents[0] / "data" / "pod" / "galeri_v11_alt.csv"
VARSAYILAN_ALT_CI = KOK.parents[0] / "data" / "pod" / "galeri_ci11_alt.csv"


def log(m):
    print(m, flush=True)


def jdump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256(yol):
    return Y.sha256(yol)


class Geri(Exception):
    """yazim sonrasi tutarsizlik: geri alma gerekir"""


# ---------------------------------------------------------------- istek tahmini
def istek_tahmini():
    """Kod yollarindan sayim (O = cl_galeri_degistir.OKUMA_TEKRAR). Yazim istekleri (POST / DELETE) en kotu 3 gonderim (etsy_common
    5xx tekrari) + 1 (401 token yenilemesi); post_file tekrar=1 + 401 = 2 gonderim / deneme. GET 5xx / 429 kisa tekrarlari dahil degil.
      kuru            : 4 GET (ilan, galeri, var_img, envanter).
      yaz en az       : 4 GET + yukleme 1 + yeni gorsel gorunur 1 + stabil galeri 2 + bag POST 1 + var_img 1 + son stabil galeri 2 + son var_img 1 + ilan 1 = 13.
      yaz en kotu     : 4 + yukleme (2 + 1 [429 okumasi]) + (2 + O) + gorunur O + stabil O + bag POST 4 + kararli var_img O + son stabil O + 1 + 1.
      geri alma       : var_img 1 + bag POST 4 + kararli var_img O + DELETE 4 + kararli galeri O + son var_img 1.
    """
    O = G.OKUMA_TEKRAR
    yukle = (2 + 1) + (2 + O)
    basari_kotu = KAPI_OKUMA + yukle + O + O + 4 + O + O + 1 + 1   # +O: yeni gorsel gorunur bekleme (inceleme 30 Eki 3)
    geri = 1 + 4 + O + 4 + O + 1
    return dict(kuru=KAPI_OKUMA, yaz_en_az=KAPI_OKUMA + 1 + 1 + 2 + 1 + 1 + 2 + 1 + 1, yaz_en_kotu_geri_almasiz=basari_kotu,
                geri_alma=geri, yaz_en_kotu=basari_kotu + geri, okuma_tekrar=O)


# ---------------------------------------------------------------- alt metin
def sablon_oku(yol, siralar):
    rows = list(csv.DictReader(open(yol, encoding="utf-8-sig")))
    sab = {int(r["sira"]): r for r in rows}
    if not set(siralar) <= set(sab):
        raise SystemExit(f"DUR: alt metin sablonu {yol}: {sorted(siralar)} satirlari yok")
    return {s: sab[s] for s in siralar}


def alt_metin(r, a, b):
    """galeri_v10_liste.alt_metin ile ayni kural: ayni burcta alt_ayni_burc doluysa o."""
    ayni = a.strip().lower() == b.strip().lower()
    t = (r.get("alt_ayni_burc") or "").strip() if ayni else ""
    return " ".join((t or r["alt"]).replace("<A>", a.strip()).replace("<B>", b.strip()).split())


def alt_gecerli(t):
    return 0 < len(t or "") <= 250 and not Y.YASAK_ALT.search(t) and "<" not in t


# ---------------------------------------------------------------- canli okuma ve kapilar
def canli_durum(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    g = G.galeri(api, lid)
    vi = G.var_img(api, shop, lid)
    inv = api.get(f"/listings/{lid}/inventory") or {}
    renk = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            if pv.get("property_id") != RENK_PID:
                continue
            for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                renk.setdefault(val, vid)
    return dict(state=L.get("state"), galeri=g, baglar=vi, renk=renk)


def bag_imza(b):
    return sorted((int(x.get("property_id") or 0), int(x.get("value_id") or 0), int(x.get("image_id") or 0)) for x in b or [])


def v11b_sorun(g, baglar, renk, alt_bek):
    """g: ilk 10 gorsel; baglar: CI disi baglar. -> sorun listesi (bos = v11b beklenen durum)"""
    s = []
    if len(g) != N0 or [x.get("rank") for x in g] != list(range(1, N0 + 1)):
        return [f"galeri {len(g)} gorsel / rank {[x.get('rank') for x in g]} (v11b: tam 10, rank 1..10)"]
    if CI.lower() in (g[0].get("alt_text") or "").lower():
        s.append("rank 1 alt metninde Champagne Ivory var (v11b: canli MB kapak; v11 CI kapak durumu)")
    for x in g[1:]:
        if Y.alt_norm(x.get("alt_text")) != Y.alt_norm(alt_bek[x["rank"]]):
            s.append(f"rank {x['rank']} alt metni v11b sablonundan farkli")
    rid = {x["rank"]: x.get("listing_image_id") for x in g}
    ad = {v: k for k, v in renk.items()}
    if len(baglar) != len(BAG_SIRA):
        s.append(f"renk bagi {len(baglar)} kayit (v11b: 4)")
    if any(int(x.get("property_id") or 0) != RENK_PID for x in baglar):
        s.append("renk bagi property 200 degil")
    gor = {}
    for x in baglar:
        n = ad.get(x.get("value_id"))
        if n is None:
            s.append(f"bag value_id {x.get('value_id')} envanter renk degerlerinde yok")
            continue
        if n in gor:
            s.append(f"{n} birden fazla bagda")
        gor[n] = x.get("image_id")
    for n, r in BAG_SIRA.items():
        if n not in renk:
            s.append(f"envanterde {n} degeri yok")
        elif gor.get(n) != rid.get(r):
            s.append(f"{n} bagi rank {r} gorseline degil ({gor.get(n)} != {rid.get(r)})")
    return s


def kapilar(c, alt_bek, alt_ci, ref=None):
    neden = []
    if c["state"] != "active":
        neden.append(f"state {c['state']} (active degil)")
    ci_vid = c["renk"].get(CI)
    if ci_vid is None:
        neden.append("envanter property 200'de Champagne Ivory degeri yok")
    ci_bag = [x for x in c["baglar"] if ci_vid is not None and x.get("value_id") == ci_vid]
    if ci_bag:
        neden.append("CI bagi zaten var (v11b: CI bagsiz)")
    neden += v11b_sorun(c["galeri"], [x for x in c["baglar"] if x not in ci_bag], c["renk"], alt_bek)
    if not alt_gecerli(alt_ci):
        neden.append("CI alt metni gecersiz (bos / >250 / yasak ifade / tire)")
    if ref is not None:
        ids = [[x.get("rank"), x.get("listing_image_id")] for x in c["galeri"]]
        rids = [[x.get("rank"), x.get("listing_image_id")] for x in sorted(ref.get("gorseller") or [], key=lambda y: y.get("rank") or 0)]
        if ids != rids:
            neden.append("canli galeri kimlikleri canli okumadan (canli_damga GALERI.json) farkli")
        if bag_imza(c["baglar"]) != bag_imza(ref.get("baglar")):
            neden.append("canli renk baglari canli okumadan (canli_damga GALERI.json) farkli")
    return neden


def durum_tur(c, alt_bek, alt_ci):
    """ZATEN (11 gorsel, CI rank 11 + bag), YARIM (rank 11 CI metinli ama bag yok / farkli) ya da None"""
    g = c["galeri"]
    if len(g) != HEDEF_RANK or [x.get("rank") for x in g] != list(range(1, HEDEF_RANK + 1)):
        return None
    if Y.alt_norm(g[-1].get("alt_text")) != Y.alt_norm(alt_ci):
        return None
    ci_vid = c["renk"].get(CI)
    ci_bag = [x for x in c["baglar"] if ci_vid is not None and x.get("value_id") == ci_vid]
    diger = [x for x in c["baglar"] if x not in ci_bag]
    ok = (len(ci_bag) == 1 and ci_bag[0].get("image_id") == g[-1].get("listing_image_id") and int(ci_bag[0].get("property_id") or 0) == RENK_PID
          and not v11b_sorun(g[:N0], diger, c["renk"], alt_bek))
    return "ZATEN" if ok else "YARIM"


ISTEK_ALAN = ("en_az", "en_kotu")   # bilgi: kod surumuyle degisir; canli = plan karsilastirmasina girmez (galeri, bag, dosya, alt girer)


def plan_girdisi(lid, cift, c, dosya, sha, alt_ci):
    t = istek_tahmini()
    ad = {v: k for k, v in c["renk"].items()}
    return dict(ilan=lid, cift=cift,
                canli_galeri=[[x.get("rank"), x.get("listing_image_id"), Y.alt_norm(x.get("alt_text"))] for x in c["galeri"]],
                canli_baglar=sorted([ad.get(x.get("value_id")), x.get("value_id"), x.get("image_id")] for x in c["baglar"]),
                ci_value_id=c["renk"].get(CI), dosya=dosya, sha256=sha, alt=alt_ci, rank=HEDEF_RANK,
                en_az=t["yaz_en_az"], en_kotu=t["yaz_en_kotu"])


def plan_sha(girdiler):
    return hashlib.sha256(jdump(girdiler).encode()).hexdigest()


def plan_yukle(yol, damga):
    p = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+_[0-9a-f]{12}", damga or ""):
        raise SystemExit("DUR: plan_damga bicimi <kuru_kosu>_<sha256 ilk 12>")
    if p.get("plan_damga") != damga or plan_sha(p.get("girdiler") or {})[:12] != damga.split("_", 1)[1]:
        raise SystemExit(f"DUR: {PLAN_AD} plan_damga / sha256 ile ayni degil; yazma yok")
    return p


# ---------------------------------------------------------------- yazim
def galeri_sorun(g, gd, yid):
    s = []
    bek = [(r, i, a) for r, i, a in gd["canli_galeri"]] + [(HEDEF_RANK, yid, Y.alt_norm(gd["alt"]))]
    simdi = [(x.get("rank"), x.get("listing_image_id"), Y.alt_norm(x.get("alt_text"))) for x in g]
    if len(g) != HEDEF_RANK:
        s.append(f"geri okuma {len(g)} gorsel (11 beklenir)")
    if simdi[:N0] != [tuple(x) for x in bek[:N0]]:
        s.append("geri okuma: rank 1-10 kimlik / sira / alt metin plandan farkli")
    if simdi[N0:] != [tuple(x) for x in bek[N0:]]:
        s.append(f"geri okuma: rank 11 yeni gorsel {yid} degil ({simdi[N0:]})")
    return s


def hedef_baglar(gd, yid):
    b = [dict(property_id=RENK_PID, value_id=v, image_id=i) for _, v, i in gd["canli_baglar"]]
    return b + [dict(property_id=RENK_PID, value_id=gd["ci_value_id"], image_id=yid)]


def eski_baglar(gd):
    return [dict(property_id=RENK_PID, value_id=v, image_id=i) for _, v, i in gd["canli_baglar"]]


def geri_al(api, shop, lid, gd, yid, bag_yazildi):
    """Baglar eski 4'e, yeni gorsel silinir (yalniz bu kosunun kimligi), sonra dogrulama. -> sorun listesi (bos = geri alindi)"""
    sorun, ids0 = [], [i for _, i, _ in gd["canli_galeri"]]
    b0 = eski_baglar(gd)
    try:
        vi = G.var_img(api, shop, lid)
        if bag_yazildi or bag_imza(vi) != bag_imza(b0):
            api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": b0})
            vi = G.kararli(lambda: G.var_img(api, shop, lid), lambda v: bag_imza(v) == bag_imza(b0))
            if bag_imza(vi) != bag_imza(b0):
                sorun.append("geri alma: baglar eski 4'e donmedi")
        if yid:
            api.delete(f"/shops/{shop}/listings/{lid}/images/{yid}", ok404=True)
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == ids0)
        if [x.get("listing_image_id") for x in g] != ids0 or [x.get("rank") for x in g] != list(range(1, N0 + 1)):
            sorun.append("geri alma: galeri 1-10 eski haline donmedi")
        if bag_imza(G.var_img(api, shop, lid)) != bag_imza(b0):
            sorun.append("geri alma: silme sonrasi baglar eski 4 degil")
    except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        sorun.append(f"geri alma hatasi: {str(getattr(e, 'code', None) or e)[:200]}")
    return sorun


def yaz_ilan(api, shop, lid, gd, yol, out):
    """-> dict(sonuc PASS | FAIL (geri alindi) | DUR (elle bakilmali), sorun, yeni_id)"""
    ids0 = [i for _, i, _ in gd["canli_galeri"]]
    (out / f"YEDEK_{lid}.json").write_text(json.dumps(dict(gd, ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())),
                                                      indent=1, ensure_ascii=False), encoding="utf-8")
    yid, bag_yazildi = None, False
    try:
        yid, _ = Y.yukle_guvenli(api, shop, lid, yol, gd["dosya"], gd["alt"], set(ids0), rank=HEDEF_RANK)
        log(f"    {lid} yuklendi: {yid} (rank {HEDEF_RANK})")
        G.kararli(lambda: G.galeri(api, lid), lambda g: any(x.get("listing_image_id") == yid for x in g))   # inceleme 30 Eki 3: yeni gorsel gorunsun
        g = Y.stabil_galeri(api, lid)
        s = galeri_sorun(g, gd, yid)
        if s:
            raise Geri("; ".join(s))
        hb = hedef_baglar(gd, yid)
        bag_yazildi = True
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": hb})
        vi = G.kararli(lambda: G.var_img(api, shop, lid), lambda v: bag_imza(v) == bag_imza(hb))
        if bag_imza(vi) != bag_imza(hb):
            raise Geri(f"bag geri okumasi {len(vi)} kayit, hedef 5 ile ayni degil")
        g = Y.stabil_galeri(api, lid)
        vi = G.var_img(api, shop, lid)
        L = api.get(f"/listings/{lid}") or {}
        s = galeri_sorun(g, gd, yid)
        if bag_imza(vi) != bag_imza(hb):
            s.append("son geri okuma: baglar 5 hedefle ayni degil")
        if L.get("state") != "active":
            s.append(f"son geri okuma: state {L.get('state')}")
        if s:
            raise Geri("; ".join(s))
        (out / f"SONRA_{lid}.json").write_text(json.dumps(dict(galeri=[[x.get("rank"), x.get("listing_image_id"), x.get("url_fullxfull")]
                                                                       for x in g], baglar=bag_imza(vi)), indent=1), encoding="utf-8")
        return dict(sonuc="PASS", sorun=[], yeni_id=yid)
    except (Geri, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        if yid is None and not bag_yazildi and (m.startswith("DUR: kota") or "galeride yeni gorsel yok" in m):
            return dict(sonuc="DUR", sorun=[m + " (yukleme olmadi, ilan degismedi)"], yeni_id=None)
        log(f"    {lid} HATA: {m[:160]} -> geri alma")
        gs = geri_al(api, shop, lid, gd, yid, bag_yazildi)
        if gs or yid is None:
            return dict(sonuc="DUR", sorun=[m] + gs + ([] if yid else ["yeni gorsel kimligi bilinmiyor; elle bakilmali"]), yeni_id=yid)
        return dict(sonuc="FAIL", sorun=[m, "GERI ALINDI (1-10 ve 4 bag eski hali)"], yeni_id=yid)


# ---------------------------------------------------------------- kosu
def kapsam(ciftler, sadece, haric):
    sa = {x for x in (sadece or "").split(",") if x}; ha = {x for x in (haric or "").split(",") if x}
    R = [r for r in csv.DictReader(open(ciftler, encoding="utf-8"))]
    bilinmeyen = (sa | ha) - {r["listing_id"] for r in R}
    if bilinmeyen:
        raise SystemExit(f"DUR: sadece / haric listesinde 78 disi ilan: {sorted(bilinmeyen)}")
    return [r for r in R if (not sa or r["listing_id"] in sa) and r["listing_id"] not in ha]


def dosya_kapi_oku(yol):
    return {r["listing_id"]: r for r in csv.DictReader(open(yol, encoding="utf-8"))}


def calistir(api, shop, a):
    out = Path(a.out); ilan_out = out / "ilanlar"; ilan_out.mkdir(parents=True, exist_ok=True)
    yazim = not a.kuru
    v11 = sablon_oku(a.alt_v11, range(2, N0 + 1))
    if any((r.get("durum") or "").strip() != "ONAYLI" for r in v11.values()):
        raise SystemExit("DUR: galeri_v11_alt.csv 2-10 satirlari ONAYLI degil (v11b beklenen durum kurulamaz)")
    ci_r = sablon_oku(a.alt_ci, [HEDEF_RANK])[HEDEF_RANK]
    ci_onay = (ci_r.get("durum") or "").strip()
    if yazim and ci_onay != "ONAYLI":
        raise SystemExit(f"DUR: CI alt metin sablonu {ci_onay} (ONAYLI degil); yazim yok")
    plan = plan_yukle(a.plan, a.plan_damga) if yazim else None
    dk = dosya_kapi_oku(a.dosya_kapi)
    t = istek_tahmini()
    satir, girdiler, dur = [], {}, None
    R = kapsam(a.ciftler, a.sadece, a.haric)
    t0, baslayan = time.time(), 0
    for n, r in enumerate(R, 1):
        lid, cift = r["listing_id"], r["cift"]
        s = dict(ilan=lid, cift=cift, durum="", neden=[], en_az=None, en_kotu=None, istek=None, ocr_frame="", yeni_id="")
        satir.append(s)
        c0 = api.calls
        try:
            if dur:
                s.update(durum="KALAN", neden=[dur]); continue
            if yazim and a.azami_ilan and baslayan >= a.azami_ilan:
                s.update(durum="KALAN", neden=[f"parca siniri {a.azami_ilan} ilan"]); continue
            d = dk.get(lid)
            s["ocr_frame"] = (d or {}).get("ocr_frame", "")
            if not d or d.get("durum") != "PASS" or d.get("cift") != cift or d.get("dosya") != f"{cift}_{a.kart}.jpg":
                s.update(durum="BLOK", neden=[f"dosya kapisi: {('satir yok' if not d else d.get('durum') + ' ' + (d.get('neden') or ''))[:160]}"])
                continue
            alt_bek = {k: alt_metin(v, r["a"], r["b"]) for k, v in v11.items()}
            alt_ci = alt_metin(ci_r, r["a"], r["b"])
            ref = None
            if a.canli_dir:
                p = Path(a.canli_dir) / f"{lid}_{cift}" / "GALERI.json"
                if not p.exists():
                    s.update(durum="BLOK", neden=[f"canli okuma yok ({p.parent.name}/GALERI.json)"]); continue
                ref = json.loads(p.read_text(encoding="utf-8"))
            yol = Path(a.dosya_dir) / d["dosya"] if a.dosya_dir else None
            if yazim and (yol is None or not yol.exists() or sha256(yol) != d["sha256"]):
                s.update(durum="BLOK", neden=["yerel CI dosyasi yok ya da sha256 dosya kapisindan farkli"]); continue
            if api.remaining is not None and int(api.remaining) - KAPI_OKUMA < KOTA_SINIRI:
                dur = f"kota: kalan {api.remaining} - {KAPI_OKUMA} okuma < {KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            api.kota_kapisi(f"ilan {lid}")
            c = canli_durum(api, shop, lid)
            tur = durum_tur(c, alt_bek, alt_ci)
            if tur == "ZATEN":
                s.update(durum="ZATEN", neden=["rank 11 CI + CI bagi zaten var"]); continue
            if tur == "YARIM":
                s.update(durum="BLOK", neden=["YARIM: rank 11 CI metinli gorsel var ama bag / 1-10 beklenen degil; elle bakilmali"]); continue
            neden = kapilar(c, alt_bek, alt_ci, ref)
            if neden:
                s.update(durum="BLOK", neden=neden); continue
            gd = plan_girdisi(lid, cift, c, d["dosya"], d["sha256"], alt_ci)
            s.update(en_az=gd["en_az"], en_kotu=gd["en_kotu"])
            if not yazim:
                girdiler[lid] = gd
                s.update(durum="PLAN", neden=([f"CI alt metni {ci_onay} (yazimdan once ONAYLI olmali)"] if ci_onay != "ONAYLI" else [])
                         + ([f"OCR Frame not included: {s['ocr_frame']}"] if s["ocr_frame"] == "VAR" else []))
                continue
            pg = (plan.get("girdiler") or {}).get(lid)
            if pg is None:
                s.update(durum="BLOK", neden=["ilan kuru planda yok; yazma yok"]); continue
            if {k: v for k, v in pg.items() if k not in ISTEK_ALAN} != {k: v for k, v in gd.items() if k not in ISTEK_ALAN}:
                s.update(durum="BLOK", neden=["canli durum / dosya / alt metin kuru plandan farkli (canli != plan); yazma yok"]); continue
            gerek = t["yaz_en_kotu"] - KAPI_OKUMA + KOTA_SINIRI
            if api.remaining is not None and int(api.remaining) < gerek:
                dur = f"kota: kalan {api.remaining} < en kotu {gerek - KOTA_SINIRI} + {KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            baslayan += 1
            Rz = yaz_ilan(api, shop, lid, gd, yol, ilan_out)
            s.update(durum=Rz["sonuc"], neden=Rz["sorun"], yeni_id=Rz.get("yeni_id") or "")
            if Rz["sonuc"] != "PASS":
                dur = f"ilan {lid} {Rz['sonuc']}; kosu durdu"
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani / Etsy / ag hatasi (yazim oncesi okuma)
            m = str(getattr(e, "code", None) or e)[:300]
            s.update(durum="KALAN" if m.startswith("DUR: kota") else "DUR", neden=[m])
            dur = f"ilan {lid} {s['durum']}; kosu durdu"
        finally:
            if s["istek"] is None:
                s["istek"] = api.calls - c0
            e = time.time() - t0
            log(f"{lid} {cift} {s['durum']} | istek {s['istek']}" + (f" | {s['neden'][0][:140]}" if s["neden"] else "")
                + f" | kota {api.remaining}")
            log(f"ETA: {n}/{len(R)} ilan | gecen {e / 60:.1f} dk | kalan {e / n * (len(R) - n) / 60:.1f} dk | %{100 * n // len(R)}")
    return satir, girdiler


def rapor(satir, girdiler, a, api, out):
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    t = istek_tahmini()
    n_plan = sum(1 for s in satir if s["durum"] == "PLAN")
    R = dict(mod="kuru" if a.kuru else "yazim", kosu=a.kosu, sayilar=say, istek_tahmini=t,
             plan_yaz_en_az=n_plan * t["yaz_en_az"], plan_yaz_en_kotu=n_plan * t["yaz_en_kotu_geri_almasiz"] + (t["geri_alma"] if n_plan else 0),
             istek=api.calls, kalan_kota=api.remaining, ilanlar=satir)
    if a.kuru:
        R["plan_damga"] = f"{a.kosu}_{plan_sha(girdiler)[:12]}"
        (out / PLAN_AD).write_text(json.dumps(dict(plan_damga=R["plan_damga"], kosu=a.kosu, girdiler=girdiler), indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    (out / "RAPOR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# Galeri CI rank 11 {R['mod']} ({a.kosu})\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                + f"\n\nIstek (kod okumasi): kuru ilan basina {t['kuru']}; yazim ilan basina en az {t['yaz_en_az']} / en kotu "
                  f"{t['yaz_en_kotu_geri_almasiz']} (geri alma +{t['geri_alma']}); PLAN {n_plan} ilan yazim toplam en az {R['plan_yaz_en_az']} / "
                  f"en kotu {R['plan_yaz_en_kotu']} | bu kosu istek {api.calls}, kalan kota {api.remaining}\n"
                + (f"plan_damga: {R.get('plan_damga')}\n" if a.kuru else "") + "\n## Ilanlar\n"
                + "".join(f"- {s['ilan']} {s['cift']} {s['durum']} istek {s['istek']} OCR-frame {s['ocr_frame'] or '-'}"
                          + (f": {'; '.join(s['neden'])[:220]}" if s["neden"] else "") + "\n" for s in satir))
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "durum", "neden", "istek", "yeni_id", "ocr_frame"], extrasaction="ignore")
        w.writeheader()
        w.writerows(dict(s, neden="; ".join(s["neden"])[:300]) for s in satir)
    log(f"GALERI_CI11 {R['mod']}: " + " ".join(f"{k}={v}" for k, v in sorted(say.items()))
        + f" | istek {api.calls} kalan kota {api.remaining}" + (f" | plan_damga {R['plan_damga']}" if a.kuru else ""))
    return R


def arg(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ciftler", default=str(KOK.parents[0] / "data" / "pod" / "pod78_ids.csv"))
    ap.add_argument("--alt-v11", default=str(VARSAYILAN_ALT_V11)); ap.add_argument("--alt-ci", default=str(VARSAYILAN_ALT_CI))
    ap.add_argument("--dosya-kapi", required=True, help="ci11_dosya_kapi.py CI_KAPI.csv")
    ap.add_argument("--kart", default="W01_KAPAK", choices=("W01_KAPAK", "W11_CI"), help="CI dosyasi turu (W11_CI: renk karti, Serdar 30 Eki)")
    ap.add_argument("--dosya-dir", default="", help="yazim: <CIFT>_W01_KAPAK.jpg dosyalari")
    ap.add_argument("--canli-dir", default="", help="istege bagli: galeri-v11-yedek-oku <ilan>_<cift>/GALERI.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--kuru", action="store_true"); ap.add_argument("--confirm", default="")
    ap.add_argument("--plan", default=""); ap.add_argument("--plan-damga", default="")
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--azami-ilan", type=int, default=0, help="yazim: kosu basina en fazla N ilan (0 = sinirsiz)")
    ap.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    a = ap.parse_args(argv)
    if not a.kuru and (a.confirm != ONAY or not a.plan or not a.plan_damga or not a.dosya_dir):
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY} + --plan + --plan-damga + --dosya-dir")
    return a


def sonlandir(api, shop, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir, girdiler = calistir(api, shop, a)
    rapor(satir, girdiler, a, api, out)
    if not a.kuru:   # inceleme 30 Eki 1: yazimda PASS / ZATEN disi her satir (BLOK, KALAN dahil) kirmizi
        return 1 if any(s["durum"] not in ("PASS", "ZATEN") for s in satir) else 0
    return 1 if any(s["durum"] in ("DUR", "FAIL") for s in satir) else 0


def main(argv=None):
    a = arg(argv)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    if a.kuru:   # kuru: yazma yontemleri kapali
        from yd_envanter_oku import salt_okur
        salt_okur(api)
    return sonlandir(api, shop, a)


if __name__ == "__main__":
    sys.exit(main())
