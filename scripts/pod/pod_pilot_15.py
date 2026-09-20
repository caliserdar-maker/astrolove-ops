#!/usr/bin/env python3
"""POD PILOT ilani 15 boy (5x7 @ 19.99 + A1 @ 89.99) - Serdar onayi 20 Eyl 2026.

YALNIZ verilen tek ilan (varsayilan 4570110641 Aquarius+Aries). Digerlerine dokunulmaz.

  oku : salt okuma. Anlik goruntu -> Drive POD_5X7/YEDEK/<lid>/ (listing, envanter, galeri,
        varyasyon gorselleri, video, RU). Size Guide karesi piksel karsilastirmasiyla bulunur
        (POD_SIZE_GUIDE_15 kartlari). Planlanan envanter + aciklama diff'i yazdirilir. YAZMA YOK.
  yaz : ADIM 1 envanter (75 urun), ADIM 2 Size Guide gorseli, ADIM 3 aciklama (EN + RU).
        Her adimda geri okuma kapisi; uyusmazlikta DURUR. Sonuc -> POD_5X7/PILOT_15.json

Kapilar: kota >= --kota-alt, ilan 'active' (taslak degil), eski fiyat/urunler aynen,
galeri sayisi ve sirasi ayni, varyasyon baglantilari yerinde (koparsa geri yazilir).
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE.
"""
import argparse
import difflib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
import requests
from PIL import Image

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import Etsy, TokenStore  # noqa: E402
from pod_sku import SKU_RE  # noqa: E402

DRV = "gdrive:ASTROLOVE/TEMP/POD_5X7"
SG15 = "gdrive:ASTROLOVE/TEMP/POD_SIZE_GUIDE_15"
EDISYONLAR = ["MIDNIGHT_BLUE", "DEEP_BLACK", "WARM_PARCHMENT", "CHAMPAGNE_IVORY", "PURE_WHITE"]
# (anahtar, grup, inc metni, cm metni, fiyat, konum, aciklama satiri)
YENI = [
    {"anahtar": "5x7", "grup": "5:7", "inc": "5x7 in", "cm": "13×18", "fiyat": 19.99, "konum": "bas"},
    {"anahtar": "A1", "grup": "A", "inc": "A1", "cm": "59×84", "fiyat": 89.99, "konum": "a_sonu"},
]
EN_KARGO_ESKI = "8x10 and A4 ship flat; all other sizes ship rolled in a sturdy tube."
EN_KARGO_YENI = ("5x7, 8x10 and A4 ship flat; all other sizes, including A1, "
                 "ship rolled in a sturdy tube.")
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def rclone(*a, sert=True):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True)
    if sert and r.returncode != 0:
        raise SystemExit(f"HATA: rclone {a[0]}: {r.stderr.strip()[-200:]}")
    return r


def para(p):
    if isinstance(p, dict):
        return round(float(p.get("amount") or 0) / float(p.get("divisor") or 100), 2)
    return round(float(p or 0), 2)


def pv_of(pr, ad):
    for pv in pr.get("property_values") or []:
        if (pv.get("property_name") or "").lower() == ad:
            return pv
    return None


def deger(pr, ad):
    pv = pv_of(pr, ad)
    return (pv.get("values") or [None])[0] if pv else None


# ------------------------------------------------------------------ anlik goruntu
def anlik(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    return {
        "listing": L,
        "inventory": api.get(f"/listings/{lid}/inventory") or {},
        "images": sorted((api.get(f"/shops/{shop}/listings/{lid}/images") or {}).get("results") or [],
                         key=lambda x: x.get("rank") or 0),
        "variation_images": (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or [],
        "videos": (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or [],
        "ru": api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {},
        "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def yedekle(sn, isd, lid, etiket="ONCE"):
    d = isd / "yedek"
    d.mkdir(parents=True, exist_ok=True)
    for k, v in sn.items():
        if k == "zaman_utc":
            continue
        p = d / f"{k}_{etiket}.json"
        p.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(p), f"{DRV}/YEDEK/{lid}/{p.name}")
    log(f"yedek Drive'a yazildi: {DRV}/YEDEK/{lid}/ ({etiket})")


# ------------------------------------------------------------------ olculer
def galeri_imza(imgs):
    return [(str(i.get("listing_image_id")), i.get("rank")) for i in imgs]


def vimza(rows):
    return sorted((str(r.get("property_id")), str(r.get("value_id")), str(r.get("image_id"))) for r in rows)


def renk_adi(inv, vid):
    for pr in inv.get("products") or []:
        pv = pv_of(pr, "primary color") or pv_of(pr, "color")
        if pv and vid in (pv.get("value_ids") or []):
            return (pv.get("values") or [""])[0]
    return ""


def v_renk_haritasi(inv, rows):
    return {renk_adi(inv, r.get("value_id")) or str(r.get("value_id")): str(r.get("image_id")) for r in rows}


def fiyat_haritasi(inv):
    h = {}
    for pr in inv.get("products") or []:
        k = (deger(pr, "primary color") or deger(pr, "color"), deger(pr, "size"))
        o = (pr.get("offerings") or [{}])[0]
        h[k] = (para(o.get("price")), o.get("quantity"), bool(o.get("is_enabled")), pr.get("sku") or "")
    return h


def boy_sirasi(inv):
    s, gor = [], set()
    for pr in inv.get("products") or []:
        b = deger(pr, "size")
        if b and b not in gor:
            gor.add(b)
            s.append(b)
    return s


# ------------------------------------------------------------------ envanter govdesi
def etiket_uret(grup, inc, cm):
    return f"{grup} · {inc} ({cm} cm)"


def govde_15(inv):
    """Mevcut 65 urun AYNEN + 10 yeni urun. Donus: (body, yeni_etiketler, notlar)."""
    urunler_eski = inv.get("products") or []
    if not urunler_eski:
        raise SystemExit("HATA: envanter bos")
    size_pv = pv_of(urunler_eski[0], "size")
    renk_pv_adi = "primary color" if pv_of(urunler_eski[0], "primary color") else "color"
    if not size_pv:
        raise SystemExit("HATA: Size ozelligi yok")
    # A serisi grup adi canli etiketten okunur ("A-series · A2 (42×59 cm)")
    a_grup = None
    for pr in urunler_eski:
        v = deger(pr, "size") or ""
        m = re.match(r"^(.*?) · (A[0-9]) \(", v)
        if m:
            a_grup = m.group(1)
    if not a_grup:
        raise SystemExit("HATA: A serisi etiketi bulunamadi (kalip okunamadi)")

    def kopya(pr, yeni_size_etiket, yeni_fiyat, yeni_sku):
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            if (pv.get("property_name") or "").lower() == "size":
                d["values"] = [yeni_size_etiket]
                d.pop("value_ids", None)          # yeni deger: id'yi Etsy uretir
            pvs.append(d)
        o0 = (pr.get("offerings") or [{}])[0]
        off = {"price": yeni_fiyat, "quantity": o0.get("quantity"), "is_enabled": True}
        if o0.get("readiness_state_id"):
            off["readiness_state_id"] = o0["readiness_state_id"]
        return {"sku": yeni_sku, "property_values": pvs, "offerings": [off]}

    def aynen(pr):
        pvs = []
        for pv in pr.get("property_values") or []:
            d = {"property_id": pv.get("property_id"), "values": list(pv.get("values") or [])}
            if pv.get("property_name"):
                d["property_name"] = pv["property_name"]
            if pv.get("scale_id"):
                d["scale_id"] = pv["scale_id"]
            if pv.get("value_ids"):
                d["value_ids"] = list(pv["value_ids"])
            pvs.append(d)
        offs = []
        for o in pr.get("offerings") or []:
            off = {"price": para(o.get("price")), "quantity": o.get("quantity"),
                   "is_enabled": bool(o.get("is_enabled"))}
            if o.get("readiness_state_id"):
                off["readiness_state_id"] = o["readiness_state_id"]
            offs.append(off)
        return {"sku": pr.get("sku") or "", "property_values": pvs, "offerings": offs}

    # renk sirasi: ilk gorunum
    renkler, gor = [], set()
    for pr in urunler_eski:
        r = deger(pr, renk_pv_adi)
        if r and r not in gor:
            gor.add(r)
            renkler.append(r)
    ornek = {r: next(pr for pr in urunler_eski if deger(pr, renk_pv_adi) == r) for r in renkler}

    yeni_etiket, notlar, yeni_urun = {}, [], {"bas": [], "a_sonu": []}
    for y in YENI:
        grup = a_grup if y["konum"] == "a_sonu" else y["grup"]
        et = etiket_uret(grup, y["inc"], y["cm"])
        yeni_etiket[y["anahtar"]] = et
        for r in renkler:
            pr = ornek[r]
            eski_sku = pr.get("sku") or ""
            yeni_sku = re.sub(r"-[^-]+$", f"-{y['anahtar']}", eski_sku)
            if not SKU_RE.match(yeni_sku):
                raise SystemExit(f"HATA: SKU kalibi tutmadi: {eski_sku} -> {yeni_sku}")
            yeni_urun[y["konum"]].append(kopya(pr, et, y["fiyat"], yeni_sku))
        notlar.append(f"{y['anahtar']}: '{et}' @ {y['fiyat']:.2f} x{len(renkler)}")

    # yerlesim: 5x7 en basa, A1 A serisinin son urununden sonra
    son_a = max((i for i, pr in enumerate(urunler_eski)
                 if (deger(pr, "size") or "").startswith(a_grup + " · ")), default=len(urunler_eski) - 1)
    urunler = list(yeni_urun["bas"])
    for i, pr in enumerate(urunler_eski):
        urunler.append(aynen(pr))
        if i == son_a:
            urunler += yeni_urun["a_sonu"]
    b = {"products": urunler,
         "price_on_property": inv.get("price_on_property") or [],
         "quantity_on_property": inv.get("quantity_on_property") or [],
         "sku_on_property": inv.get("sku_on_property") or []}
    return b, yeni_etiket, notlar


# ------------------------------------------------------------------ aciklama
def _blok_sinirlari(satirlar, bas_dese):
    i = next((n for n, s in enumerate(satirlar) if bas_dese.match(s)), None)
    if i is None:
        return None, None
    j = next((n for n in range(i + 1, len(satirlar)) if satirlar[n].startswith("✦")), len(satirlar))
    return i, j


def aciklama_15(metin, dil="en"):
    """13 boy blogunu 15 boya cevirir. Donus: (yeni_metin, degisiklikler)."""
    if not metin:
        return metin, ["(bos)"]
    satirlar = metin.split("\n")
    bas = re.compile(r"^✦ 13 (SIZES|РАЗМЕРОВ)\b")
    i, j = _blok_sinirlari(satirlar, bas)
    if i is None:
        raise SystemExit(f"HATA: {dil}: '✦ 13 SIZES' blogu bulunamadi")
    blok = satirlar[i:j]
    dgs = []
    blok[0] = blok[0].replace("✦ 13 SIZES", "✦ 15 SIZES").replace("✦ 13 РАЗМЕРОВ", "✦ 15 РАЗМЕРОВ")
    dgs.append(f"baslik: {satirlar[i]!r} -> {blok[0]!r}")

    # 1) ayirici: boy satirlarinda ' — ' / ' – ' -> ' / '
    n_ayirici = 0
    for k in range(1, len(blok)):
        if re.search(r"[—–]", blok[k]) and re.search(r"\d", blok[k]):
            blok[k] = re.sub(r"\s*[—–]\s*", " / ", blok[k])
            n_ayirici += 1
    dgs.append(f"ayirici '/' : {n_ayirici} satir")

    # 2) 5:7 grubu en basa (basliktan sonraki bos satirin ardina)
    grup_basligi = "Ratio 5:7" if dil == "en" else "Соотношение 5:7"
    cm = "cm" if dil == "en" else "см"
    y5 = YENI[0]
    satir5 = f"{y5['inc']} / {y5['cm']} {cm}"
    if grup_basligi not in blok:
        yerlestir = 1
        while yerlestir < len(blok) and not blok[yerlestir].strip():
            yerlestir += 1
        blok[yerlestir:yerlestir] = [grup_basligi, satir5, ""]
        dgs.append(f"5:7 grubu eklendi: {grup_basligi!r} + {satir5!r}")

    # 3) A serisinin sonuna A1
    yA = YENI[1]
    satirA = f"{yA['inc']} / {yA['cm']} {cm}"
    if satirA not in blok:
        son_a = max((k for k, s in enumerate(blok) if re.match(r"^A[0-9]\s*/", s.strip())), default=None)
        if son_a is None:
            raise SystemExit(f"HATA: {dil}: A serisi satirlari bulunamadi")
        blok[son_a + 1:son_a + 1] = [satirA]
        dgs.append(f"A1 satiri eklendi: {satirA!r}")

    satirlar[i:j] = blok
    yeni = "\n".join(satirlar)

    # 4) kargo cumlesi (yalniz EN)
    if dil == "en":
        if EN_KARGO_ESKI in yeni:
            yeni = yeni.replace(EN_KARGO_ESKI, EN_KARGO_YENI)
            dgs.append("kargo cumlesi guncellendi")
        elif EN_KARGO_YENI not in yeni:
            raise SystemExit("HATA: EN kargo cumlesi bulunamadi (metin beklenenden farkli)")
    return yeni, dgs


def diff_ozet(eski, yeni):
    d = list(difflib.unified_diff(eski.split("\n"), yeni.split("\n"), lineterm="", n=0))
    return [s for s in d if s and s[0] in "+-" and not s.startswith(("---", "+++"))]


# ------------------------------------------------------------------ Size Guide karesi
def _kucult(b):
    im = Image.open(io.BytesIO(b)).convert("RGB").resize((240, 180), Image.LANCZOS)
    return np.asarray(im, dtype=np.int16)


def size_guide_bul(imgs, cift, isd):
    """Galerideki Size Guide karesini yeni SG15 kartlariyla piksel karsilastirarak bulur.
    Donus: (image, edisyon, en_iyi_fark, ikinci_fark, yerel_yeni_kart)."""
    kartlar = {}
    d = isd / "sg15"
    d.mkdir(parents=True, exist_ok=True)
    for ed in EDISYONLAR:
        p = d / f"{ed}.jpg"
        r = rclone("copyto", f"{SG15}/{cift}/{ed}/08_SIZES_{cift}_{ed}.jpg", str(p), sert=False)
        if r.returncode == 0 and p.exists():
            kartlar[ed] = (_kucult(p.read_bytes()), p)
    if not kartlar:
        raise SystemExit(f"HATA: SG15 karti yok: {SG15}/{cift}/<ED>/")
    skor = []
    for im in imgs:
        u = im.get("url_fullxfull") or im.get("url_570xN")
        b = requests.get(u, timeout=60).content
        a = _kucult(b)
        for ed, (k, p) in kartlar.items():
            skor.append((float(np.abs(a - k).mean()), im, ed, p))
    skor.sort(key=lambda x: x[0])
    en_iyi = skor[0]
    ikinci = next((s for s in skor if s[1] is not en_iyi[1]), (None,))[0]
    return en_iyi[1], en_iyi[2], round(en_iyi[0], 2), (round(ikinci, 2) if ikinci else None), en_iyi[3]


# ------------------------------------------------------------------ ana akis
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["oku", "yaz"])
    ap.add_argument("--listing", default="4570110641")
    ap.add_argument("--cift", default="AQUARIUS_ARIES")
    ap.add_argument("--is-dizin", default="_work/pilot15")
    ap.add_argument("--kota-alt", type=int, default=400)
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.mod == "yaz" and a.confirm != "PILOT_15":
        raise SystemExit("DUR: yaz icin --confirm PILOT_15 gerekir")
    isd = pathlib.Path(a.is_dizin)
    isd.mkdir(parents=True, exist_ok=True)
    lid, shop = a.listing, os.environ["ETSY_SHOP_ID"]
    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    api.get(f"/shops/{shop}", ok404=True)
    kota0 = api.remaining
    log(f"kota (once): {kota0} | mod {a.mod} | ilan {lid}")
    if kota0 is not None and int(kota0) < a.kota_alt:
        raise SystemExit(f"DUR: kota {kota0} < {a.kota_alt}")

    sn = anlik(api, shop, lid)
    yedekle(sn, isd, lid, "ONCE")
    L, inv = sn["listing"], sn["inventory"]
    durum = L.get("state")
    log(f"ilan: {L.get('title', '')[:60]!r} | durum {durum} | urun {len(inv.get('products') or [])} | "
        f"gorsel {len(sn['images'])} | video {len(sn['videos'])} | varyasyon-gorsel {len(sn['variation_images'])}")
    if durum != "active":
        raise SystemExit(f"DUR: ilan durumu {durum} (aktif degil; updateListing taslagi yayina alir)")
    log(f"boy sirasi (once): {boy_sirasi(inv)}")

    b, yeni_etiket, notlar = govde_15(inv)
    log(f"plan envanter: {len(inv.get('products') or [])} -> {len(b['products'])} urun | " + " | ".join(notlar))
    log(f"yeni boy sirasi (plan): {boy_sirasi({'products': b['products']})}")

    en_yeni, en_dgs = aciklama_15(L.get("description") or "", "en")
    ru_eski = sn["ru"].get("description") or ""
    ru_yeni, ru_dgs = aciklama_15(ru_eski, "ru") if ru_eski else (ru_eski, ["(RU yok)"])
    en_diff, ru_diff = diff_ozet(L.get("description") or "", en_yeni), diff_ozet(ru_eski, ru_yeni)
    log("aciklama EN degisiklikleri: " + " ; ".join(en_dgs))
    for s in en_diff:
        log(f"  EN {s}")
    log("aciklama RU degisiklikleri: " + " ; ".join(ru_dgs))
    for s in ru_diff:
        log(f"  RU {s}")

    sg, sg_ed, fark, fark2, yeni_kart = size_guide_bul(sn["images"], a.cift, isd)
    log(f"Size Guide karesi: rank {sg.get('rank')} id {sg.get('listing_image_id')} | edisyon {sg_ed} "
        f"| fark {fark} (ikinci en iyi {fark2}) | yeni kart {yeni_kart}")
    if fark > 12 or (fark2 is not None and fark2 - fark < 5):
        raise SystemExit(f"DUR: Size Guide karesi kesin degil (fark {fark}, ikinci {fark2})")

    sonuc = {"listing_id": lid, "cift": a.cift, "mod": a.mod, "kota_once": kota0,
             "urun_once": len(inv.get("products") or []), "urun_plan": len(b["products"]),
             "yeni_etiket": yeni_etiket, "size_guide": {"rank": sg.get("rank"),
             "eski_image_id": sg.get("listing_image_id"), "edisyon": sg_ed, "fark": fark},
             "aciklama": {"en": en_dgs, "ru": ru_dgs, "en_diff": en_diff, "ru_diff": ru_diff},
             "galeri_once": galeri_imza(sn["images"]),
             "zaman_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    if a.mod == "oku":
        p = isd / "PILOT_15_PLAN.json"
        p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
        rclone("copyto", str(p), f"{DRV}/PILOT_15_PLAN.json")
        log(f"PLAN yazildi: {DRV}/PILOT_15_PLAN.json | kota {api.remaining}")
        return 0

    # ---------------------------------------------------------- ADIM 1: envanter
    v_once = v_renk_haritasi(inv, sn["variation_images"])
    f_once = fiyat_haritasi(inv)
    log(f"ADIM 1: envanter PUT ({len(b['products'])} urun)")
    try:
        api.put_json(f"/listings/{lid}/inventory", b)
    except SystemExit as e:
        log(f"  PUT (value_ids ile) basarisiz: {str(e)[:160]} -> value_ids'siz tekrar")
        for pr in b["products"]:
            for pv in pr["property_values"]:
                if (pv.get("property_name") or "").lower() == "size":
                    pv.pop("value_ids", None)
        api.put_json(f"/listings/{lid}/inventory", b)
    sn1 = anlik(api, shop, lid)
    inv1 = sn1["inventory"]
    f_sonra = fiyat_haritasi(inv1)
    hatalar = []
    if len(inv1.get("products") or []) != 75:
        hatalar.append(f"urun {len(inv1.get('products') or [])} != 75")
    for k, v in f_once.items():
        if f_sonra.get(k) != v:
            hatalar.append(f"eski fiyat degisti {k}: {v} -> {f_sonra.get(k)}")
    for y in YENI:
        et = yeni_etiket[y["anahtar"]]
        yeni_k = [k for k in f_sonra if k[1] == et]
        if len(yeni_k) != 5:
            hatalar.append(f"{y['anahtar']}: {len(yeni_k)} urun (5 bekleniyor)")
        kotu = [k for k in yeni_k if abs(f_sonra[k][0] - y["fiyat"]) > 1e-9]
        if kotu:
            hatalar.append(f"{y['anahtar']} fiyat: {[(k, f_sonra[k][0]) for k in kotu][:3]}")
    v_sonra = v_renk_haritasi(inv1, sn1["variation_images"])
    if v_sonra != v_once:
        log(f"  varyasyon baglantisi degisti: {v_once} -> {v_sonra}; geri yaziliyor")
        pid = (sn["variation_images"][0] or {}).get("property_id")
        ad_to_vid = {}
        for pr in inv1.get("products") or []:
            pv = pv_of(pr, "primary color") or pv_of(pr, "color")
            if pv and pv.get("value_ids"):
                ad_to_vid[(pv.get("values") or [""])[0]] = pv["value_ids"][0]
        vi = [{"property_id": pid, "value_id": ad_to_vid[ad], "image_id": int(img)}
              for ad, img in v_once.items() if ad in ad_to_vid]
        api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": vi})
        sn1 = anlik(api, shop, lid)
        v_sonra = v_renk_haritasi(sn1["inventory"], sn1["variation_images"])
        if v_sonra != v_once:
            hatalar.append(f"varyasyon baglantisi onarilamadi: {v_sonra}")
        else:
            log("  varyasyon baglantilari geri yazildi (5/5)")
    if galeri_imza(sn1["images"]) != galeri_imza(sn["images"]):
        hatalar.append("galeri degisti")
    if [v.get("video_id") for v in sn1["videos"]] != [v.get("video_id") for v in sn["videos"]]:
        hatalar.append("video degisti")
    if sn1["listing"].get("state") != durum:
        hatalar.append(f"durum {sn1['listing'].get('state')}")
    sonuc["adim1"] = {"urun": len(inv1.get("products") or []), "hatalar": hatalar,
                      "boy_sirasi": boy_sirasi(inv1), "varyasyon": v_sonra}
    log(f"ADIM 1 {'PASS' if not hatalar else 'FAIL'}: urun {len(inv1.get('products') or [])} | "
        f"boy sirasi {boy_sirasi(inv1)}")
    if hatalar:
        raise SystemExit("DUR (ADIM 1): " + "; ".join(hatalar)[:400])

    # ---------------------------------------------------------- ADIM 2: Size Guide gorseli
    rank, eski_id = sg.get("rank"), sg.get("listing_image_id")
    alt = sg.get("alt_text") or ""
    sinirda = len(sn1["images"]) >= 10
    log(f"ADIM 2: Size Guide rank {rank} (eski {eski_id}) -> {yeni_kart.name} "
        f"({'once sil' if sinirda else 'once yukle'})")
    if sinirda:
        api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
    veri = {"rank": str(rank)}
    if alt:
        veri["alt_text"] = alt
    with open(yeni_kart, "rb") as fh:
        r = api.post_file(f"/shops/{shop}/listings/{lid}/images",
                          files={"image": (yeni_kart.name, fh, "image/jpeg")}, data=veri)
    yeni_id = r.get("listing_image_id")
    if not sinirda:
        api.delete(f"/shops/{shop}/listings/{lid}/images/{eski_id}")
    sn2 = anlik(api, shop, lid)
    g_once, g_sonra = galeri_imza(sn1["images"]), galeri_imza(sn2["images"])
    hatalar = []
    if len(g_sonra) != len(g_once):
        hatalar.append(f"galeri {len(g_sonra)} != {len(g_once)}")
    bekle = [(str(yeni_id), rk) if i == str(eski_id) else (i, rk) for i, rk in g_once]
    if sorted(g_sonra) != sorted(bekle):
        hatalar.append(f"galeri imzasi farkli: {g_sonra} != {bekle}")
    v2 = v_renk_haritasi(sn2["inventory"], sn2["variation_images"])
    if v2 != v_once:
        hatalar.append(f"varyasyon baglantisi bozuldu: {v2}")
    sonuc["adim2"] = {"rank": rank, "eski_image_id": eski_id, "yeni_image_id": yeni_id,
                      "galeri": g_sonra, "hatalar": hatalar}
    log(f"ADIM 2 {'PASS' if not hatalar else 'FAIL'}: yeni id {yeni_id}, galeri {len(g_sonra)} gorsel")
    if hatalar:
        raise SystemExit("DUR (ADIM 2): " + "; ".join(hatalar)[:400])

    # ---------------------------------------------------------- ADIM 3: aciklama
    log("ADIM 3: aciklama EN PATCH + RU PUT")
    api.patch(f"/shops/{shop}/listings/{lid}", {"description": en_yeni})
    if ru_eski:
        api.put(f"/shops/{shop}/listings/{lid}/translations/ru",
                {"title": sn["ru"].get("title") or "", "description": ru_yeni,
                 "tags": ",".join(sn["ru"].get("tags") or [])})
    sn3 = anlik(api, shop, lid)
    hatalar = []
    if (sn3["listing"].get("description") or "") != en_yeni:
        hatalar.append("EN aciklama geri okuma farkli")
    if ru_eski and (sn3["ru"].get("description") or "") != ru_yeni:
        hatalar.append("RU aciklama geri okuma farkli")
    if sn3["listing"].get("state") != durum:
        hatalar.append(f"durum {sn3['listing'].get('state')}")
    if galeri_imza(sn3["images"]) != g_sonra:
        hatalar.append("galeri degisti (ADIM 3)")
    sonuc["adim3"] = {"en_diff": en_diff, "ru_diff": ru_diff, "hatalar": hatalar}
    sonuc["kota_sonra"] = api.remaining
    sonuc["galeri_sonra"] = galeri_imza(sn3["images"])
    sonuc["varyasyon_sonra"] = v_renk_haritasi(sn3["inventory"], sn3["variation_images"])
    sonuc["url"] = f"https://www.etsy.com/listing/{lid}"
    yedekle(sn3, isd, lid, "SONRA")
    p = isd / "PILOT_15.json"
    p.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    rclone("copyto", str(p), f"{DRV}/PILOT_15.json")
    log(f"ADIM 3 {'PASS' if not hatalar else 'FAIL'} | kota (sonra) {api.remaining} | {DRV}/PILOT_15.json")
    if hatalar:
        raise SystemExit("DUR (ADIM 3): " + "; ".join(hatalar)[:400])
    log("PILOT 15 TAMAM: 75 urun, Size Guide yeni, aciklama 15 boy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
