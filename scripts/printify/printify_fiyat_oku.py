#!/usr/bin/env python3
"""Printify FIYAT OKUMA (13 Eki 2026, Serdar onayi). SIPARIS / PUBLISH YOK.

Yalniz su uclar cagrilabilir (IZIN listesi, regex ile kilitli):
  katalog (blueprints, print_providers, variants, shipping), shops.json,
  uploads (gorsel yukle + arsivle), urun olustur / sil / listele.
Urun: taslak olusturulur, variant cost okunur, ayni anda SILINIR. Publish YOK.

Kullanim:
  PRINTIFY_API_KEY=... printify_fiyat_oku.py <cikis_dizini>            # okuma
  PRINTIFY_API_KEY=... printify_fiyat_oku.py <cikis_dizini> --temizle  # artik taslak sil + dogrula
"""
import base64
import csv
import json
import os
import re
import struct
import sys
import time
import zlib

import requests

API = "https://api.printify.com"
ETIKET = "PRINTIFY_FIYAT_TEST_SILINECEK"
FIYAT_CENT = 30000  # taslak satis fiyati (yalniz zorunlu alan; urun yayinlanmaz)
BEKLE = 0.65        # katalog hiz limiti icin istekler arasi bekleme (sn)
ULKELER = ("US", "DE", "GB", "AU")
HEDEF_IN = {"8x10": (8, 10), "11x14": (11, 14), "12x16": (12, 16), "12x18": (12, 18), "16x20": (16, 20),
            "16x24": (16, 24), "18x24": (18, 24), "20x30": (20, 30), "24x36": (24, 36)}
HEDEF_A_MM = {"A4": (210, 297), "A3": (297, 420), "A2": (420, 594)}
BOYLAR = list(HEDEF_IN) + list(HEDEF_A_MM)

IZIN = [
    ("GET", r"/v1/catalog/blueprints\.json"),
    ("GET", r"/v1/catalog/blueprints/\d+/print_providers\.json"),
    ("GET", r"/v1/catalog/blueprints/\d+/print_providers/\d+/(variants|shipping)\.json"),
    ("GET", r"/v1/catalog/print_providers/\d+\.json"),
    ("GET", r"/v1/shops\.json"),
    ("GET", r"/v1/shops/\d+/products\.json"),
    ("POST", r"/v1/uploads/images\.json"),
    ("POST", r"/v1/uploads/[0-9a-f]+/archive\.json"),
    ("POST", r"/v1/shops/\d+/products\.json"),
    ("DELETE", r"/v1/shops/\d+/products/[0-9a-f]+\.json"),
]
SAYAC = {"istek": 0}


class ApiHata(Exception):
    def __init__(self, kod, metin):
        super().__init__(f"{kod} {metin}")
        self.kod = kod


def oturum():
    k = os.environ.get("PRINTIFY_API_KEY", "").strip()
    if not k:
        sys.exit("HATA anahtar yok")
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + k, "User-Agent": "AstroLoveArt-fiyat-oku",
                      "Content-Type": "application/json"})
    return s


def istek(S, y, yol, params=None, js=None, yok404=False):
    dusuk = yol.lower()
    if "order" in dusuk or "publish" in dusuk:
        raise SystemExit(f"YASAK uc: {y} {yol}")
    if not any(y == a and re.fullmatch(b, yol) for a, b in IZIN):
        raise SystemExit(f"izinsiz uc: {y} {yol}")
    for den in range(6):
        time.sleep(BEKLE)
        r = S.request(y, API + yol, params=params, json=js, timeout=120)
        SAYAC["istek"] += 1
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After") or ""
            time.sleep(min(int(ra) if ra.isdigit() else 15 * (den + 1), 90))
            continue
        if r.status_code == 404 and yok404:
            return None
        if r.status_code >= 400:
            raise ApiHata(r.status_code, r.text[:300].replace("\n", " "))
        return r.json() if r.text.strip() else {}
    raise ApiHata(429, "tekrar limiti asildi")


# ---------- boy / kagit / cerceve ----------
def _norm(t):
    return (t.replace("″", '"').replace("”", '"').replace("“", '"').replace("''", '"')
            .replace("×", "x").replace("X", "x"))


def boy_bul(metin):
    """Metinden hedef boyu bul: (boy, yon) ya da (None, None)."""
    t = _norm(metin)
    m = re.search(r"(?<![A-Za-z0-9])A([2-4])(?![0-9])", t)
    if m:
        return "A" + m.group(1), ""
    for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*(?:"|in(?:ch(?:es)?)?\b)?\s*x\s*(\d+(?:[.,]\d+)?)\s*("|in(?:ch(?:es)?)?\b|cm\b|mm\b)?', t, re.I):
        a, b = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
        birim = (m.group(3) or "").lower()
        yon = "dikey" if a < b else ("yatay" if a > b else "kare")
        lo, hi = sorted((a, b))
        if birim in ("cm", "mm"):
            f = 10 if birim == "cm" else 1
            for ad, (w, h) in HEDEF_A_MM.items():
                if abs(lo * f - w) <= 3 and abs(hi * f - h) <= 3:
                    return ad, yon
            continue
        for ad, (w, h) in HEDEF_IN.items():
            if abs(lo - w) < 0.01 and abs(hi - h) < 0.01:
                return ad, yon
        for ad, (w, h) in HEDEF_A_MM.items():
            if abs(lo * 25.4 - w) <= 4 and abs(hi * 25.4 - h) <= 4:
                return ad, yon
    return None, None


KAGIT_SOZ = ("matte", "matt", "glossy", "gloss", "satin", "semi", "luster", "lustre", "fine art", "archival",
             "premium", "photo", "museum", "velvet", "cotton", "uncoated", "silk", "pearl", "gsm", "lb")


def kagit_ve_cerceve(bp_baslik, secenek):
    kagit, cerceve = [], []
    for k, v in (secenek or {}).items():
        kl, vs = k.lower(), str(v)
        if kl == "size":
            continue
        if "frame" in kl or kl in ("color", "colour", "frame_color"):
            cerceve.append(vs)
        else:
            kagit.append(f"{k}={vs}")
    if not kagit:
        b = bp_baslik.lower()
        bulunan = [s for s in KAGIT_SOZ if s in b]
        kagit = ["baslik:" + "/".join(bulunan)] if bulunan else []
    return "; ".join(kagit), "/".join(cerceve)


def kargo_bul(ship, vid, ulke):
    prof = (ship or {}).get("profiles") or []
    for p in prof:
        if vid in (p.get("variant_ids") or []) and ulke in (p.get("countries") or []):
            return p, ""
    for p in prof:
        if vid in (p.get("variant_ids") or []) and "REST_OF_THE_WORLD" in (p.get("countries") or []):
            return p, f"{ulke}=ROW"
    return None, f"{ulke}=YOK"


def tutar(d):
    if not d or d.get("cost") is None:
        return "YOK", ""
    return f"{int(d['cost']) / 100:.2f}", (d.get("currency") or "").upper()


def png_duz(w=3000, h=4000, renk=(214, 206, 196)):
    satir = b"\x00" + bytes(renk) * w
    ham = zlib.compress(satir * h, 9)

    def parca(tip, veri):
        return struct.pack(">I", len(veri)) + tip + veri + struct.pack(">I", zlib.crc32(tip + veri) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + parca(b"IDAT", ham) + parca(b"IEND", b""))


# ---------- magaza ----------
def magaza_sec(S):
    shops = istek(S, "GET", "/v1/shops.json") or []
    for sh in shops:
        print(f"magaza: id={sh.get('id')} kanal={sh.get('sales_channel')}")
    if not shops:
        return None
    oncelik = [sh for sh in shops if str(sh.get("sales_channel", "")).lower() in ("custom_integration", "disconnected")]
    return (oncelik or shops)[0]


def urunleri_listele(S, shop):
    tum, sayfa = [], 1
    while True:
        r = istek(S, "GET", f"/v1/shops/{shop}/products.json", params={"limit": 50, "page": sayfa}) or {}
        veri = r.get("data") or []
        tum += veri
        if not veri or sayfa >= int(r.get("last_page") or 1):
            return tum
        sayfa += 1


def temizle(S, cikis):
    sh = magaza_sec(S)
    if not sh:
        print("TEMIZLE magaza yok, taslak olusturulmadi")
        return 0
    shop = sh["id"]
    kalan = [p for p in urunleri_listele(S, shop) if str(p.get("title", "")).startswith(ETIKET)]
    for p in kalan:
        istek(S, "DELETE", f"/v1/shops/{shop}/products/{p['id']}.json")
        print(f"TEMIZLE artik taslak silindi {p['id']}")
    son = [p for p in urunleri_listele(S, shop) if str(p.get("title", "")).startswith(ETIKET)]
    ozet_yol = os.path.join(cikis, "PRINTIFY_OZET.json")
    oz = json.load(open(ozet_yol)) if os.path.exists(ozet_yol) else {}
    olusan = set(oz.get("olusturulan", []))
    hepsi = {p["id"] for p in urunleri_listele(S, shop)}
    kalan_olusan = sorted(olusan & hepsi)
    oz.update({"temizle_silinen": [p["id"] for p in kalan], "dogrulama_etiketli_kalan": len(son),
               "dogrulama_olusturulan_kalan": kalan_olusan, "dogrulama_urun_sayisi": len(hepsi)})
    json.dump(oz, open(ozet_yol, "w"), indent=1)
    durum = "PASS" if not son and not kalan_olusan else "FAIL"
    print(f"OZET taslak dogrulama {durum}: olusturulan={len(olusan)} kalan={len(kalan_olusan)} "
          f"etiketli_kalan={len(son)} magazadaki_urun={len(hepsi)}")
    return 0 if durum == "PASS" else 1


# ---------- ana okuma ----------
def oku(S, cikis):
    oz = {"olusturulan": [], "silinen": [], "hatalar": [], "yuklenen_gorsel": None}
    ozet_yol = os.path.join(cikis, "PRINTIFY_OZET.json")

    def kaydet():
        json.dump(oz, open(ozet_yol, "w"), indent=1)

    kaydet()
    bps = istek(S, "GET", "/v1/catalog/blueprints.json") or []
    secili = []
    for b in bps:
        t = str(b.get("title", ""))
        tl = t.lower()
        if "poster" in tl:
            secili.append((b["id"], t, "cerceveli" if "fram" in tl else "poster"))
        elif "fram" in tl and "canvas" not in tl and any(s in tl for s in ("print", "paper", "art")):
            secili.append((b["id"], t, "cerceveli"))
    print(f"katalog: {len(bps)} blueprint, secilen {len(secili)}")

    sh = magaza_sec(S)
    shop = sh["id"] if sh else None
    if not shop:
        print("UYARI magaza yok: urun maliyeti adimi atlandi")
    gorsel = None

    pp_cache = {}
    satirlar, cerceve_satir = [], []
    sayac_cift = 0
    t0 = time.time()
    for i, (bp, bpt, kat) in enumerate(secili, 1):
        try:
            pps = istek(S, "GET", f"/v1/catalog/blueprints/{bp}/print_providers.json", yok404=True) or []
        except ApiHata as e:
            oz["hatalar"].append(f"bp{bp} providers {e.kod}")
            pps = []
        if not pps:
            for boy in BOYLAR:
                satirlar.append({"blueprint_id": bp, "blueprint": bpt, "kategori": kat, "boy": boy, "durum": "YOK (provider yok)"})
            continue
        for pp in pps:
            ppid, ppt = pp["id"], pp.get("title", "")
            sayac_cift += 1
            if ppid not in pp_cache:
                try:
                    d = istek(S, "GET", f"/v1/catalog/print_providers/{ppid}.json", yok404=True) or {}
                except ApiHata:
                    d = {}
                loc = d.get("location") or {}
                pp_cache[ppid] = (loc.get("country") or "?", ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x))
            ulke, konum = pp_cache[ppid]
            taban = {"blueprint_id": bp, "blueprint": bpt, "kategori": kat, "provider_id": ppid, "provider": ppt,
                     "ulke": ulke, "konum": konum}
            try:
                vr = istek(S, "GET", f"/v1/catalog/blueprints/{bp}/print_providers/{ppid}/variants.json",
                           params={"show-out-of-stock": 1}, yok404=True) or {}
                varyant = vr.get("variants") or []
            except ApiHata as e:
                oz["hatalar"].append(f"bp{bp} pp{ppid} variants {e.kod}")
                varyant = []
            try:
                ship = istek(S, "GET", f"/v1/catalog/blueprints/{bp}/print_providers/{ppid}/shipping.json", yok404=True) or {}
            except ApiHata as e:
                oz["hatalar"].append(f"bp{bp} pp{ppid} shipping {e.kod}")
                ship = {}
            ht = ship.get("handling_time") or {}
            handling = f"{ht.get('value')} {ht.get('unit')}" if ht else "YOK"

            # cerceve renkleri
            if kat == "cerceveli" or any(("frame" in k.lower()) for v in varyant for k in (v.get("options") or {})):
                renkler = sorted({kagit_ve_cerceve(bpt, v.get("options"))[1] for v in varyant} - {""})
                cerceve_satir.append({**{k: taban[k] for k in ("blueprint_id", "blueprint", "provider", "ulke", "konum")},
                                      "cerceve_renkleri": " | ".join(renkler) or "YOK",
                                      "altin": "EVET" if any("gold" in r.lower() for r in renkler) else "HAYIR"})

            hedef = {}
            for v in varyant:
                boy, yon = boy_bul(str(v.get("title", "")) + " " + " ".join(str(x) for x in (v.get("options") or {}).values()))
                if boy:
                    hedef[v["id"]] = (boy, yon, v)

            # maliyet: taslak urun -> cost oku -> sil
            maliyet, mdurum = {}, ""
            if hedef and shop:
                try:
                    if gorsel is None:
                        up = istek(S, "POST", "/v1/uploads/images.json",
                                   js={"file_name": "printify_fiyat_test.png",
                                       "contents": base64.b64encode(png_duz()).decode()})
                        gorsel = up["id"]
                        oz["yuklenen_gorsel"] = gorsel
                        kaydet()
                    maliyet, mdurum = urun_maliyet(S, shop, bp, ppid, varyant, set(hedef), gorsel, oz, kaydet)
                except ApiHata as e:
                    mdurum = f"YOK (urun {e.kod})"
                    oz["hatalar"].append(f"bp{bp} pp{ppid} urun {e}")
            elif hedef and not shop:
                mdurum = "YOK (magaza yok)"

            bulunan = set()
            for vid, (boy, yon, v) in hedef.items():
                bulunan.add(boy)
                kagit, cer = kagit_ve_cerceve(bpt, v.get("options"))
                sat = {**taban, "boy": boy, "yon": yon, "variant_id": vid, "variant": v.get("title", ""),
                       "kagit": kagit, "cerceve": cer, "maliyet_usd": maliyet.get(vid, mdurum or "YOK"),
                       "handling": handling, "durum": "OK"}
                para, notlar = set(), []
                for u in ULKELER:
                    p, nt = kargo_bul(ship, vid, u)
                    a, pa = tutar((p or {}).get("first_item"))
                    b, pb = tutar((p or {}).get("additional_items"))
                    sat[f"kargo_{u}_ilk"], sat[f"kargo_{u}_ek"] = a, b
                    para |= {x for x in (pa, pb) if x}
                    if nt:
                        notlar.append(nt)
                sat["kargo_para"] = "/".join(sorted(para))
                sat["kargo_not"] = " ".join(notlar)
                satirlar.append(sat)
            for boy in BOYLAR:
                if boy not in bulunan:
                    satirlar.append({**taban, "boy": boy, "handling": handling, "durum": "YOK"})
        gecen = time.time() - t0
        kalan = gecen / i * (len(secili) - i)
        print(f"ETA {i}/{len(secili)} blueprint (%{100 * i // len(secili)}) gecen {gecen / 60:.1f} dk kalan ~{kalan / 60:.1f} dk "
              f"istek {SAYAC['istek']} taslak {len(oz['olusturulan'])}/{len(oz['silinen'])} silindi", flush=True)

    if gorsel:
        try:
            istek(S, "POST", f"/v1/uploads/{gorsel}/archive.json")
            oz["gorsel_arsiv"] = "OK"
        except ApiHata as e:
            oz["gorsel_arsiv"] = f"HATA {e.kod}"
    kaydet()

    alanlar = ["blueprint_id", "blueprint", "kategori", "provider_id", "provider", "ulke", "konum", "boy", "yon",
               "variant_id", "variant", "kagit", "cerceve", "maliyet_usd"] + \
              [f"kargo_{u}_{t}" for u in ULKELER for t in ("ilk", "ek")] + ["kargo_para", "kargo_not", "handling", "durum"]
    with open(os.path.join(cikis, "PRINTIFY_FIYAT.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow({k: s.get(k, "YOK" if k == "maliyet_usd" else "") for k in alanlar})
    with open(os.path.join(cikis, "PRINTIFY_CERCEVE.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["blueprint_id", "blueprint", "provider", "ulke", "konum", "cerceve_renkleri", "altin"])
        w.writeheader()
        w.writerows(cerceve_satir)
    ok = sum(1 for s in satirlar if s.get("durum") == "OK")
    print(f"OZET {len(satirlar)} satir, OK {ok}, YOK {len(satirlar) - ok}, blueprint {len(secili)}, cift {sayac_cift}, "
          f"taslak olusturulan {len(oz['olusturulan'])} silinen {len(oz['silinen'])}, istek {SAYAC['istek']}, hata {len(oz['hatalar'])}")
    for h in oz["hatalar"][:6]:
        print("HATA", h)
    print("cerceve renkleri: altin EVET olan", sum(1 for c in cerceve_satir if c["altin"] == "EVET"), "/", len(cerceve_satir))
    return 0


def urun_maliyet(S, shop, bp, ppid, varyant, hedef_ids, gorsel, oz, kaydet):
    def govde(liste):
        gruplar = {}
        for v in liste:
            poz = tuple(sorted({p.get("position") for p in (v.get("placeholders") or []) if p.get("position")})) or ("front",)
            gruplar.setdefault(poz, []).append(v["id"])
        return {"title": f"{ETIKET} bp{bp} pp{ppid}", "description": "Fiyat okuma testi. Otomatik silinir.",
                "blueprint_id": bp, "print_provider_id": ppid,
                "variants": [{"id": v["id"], "price": FIYAT_CENT, "is_enabled": v["id"] in hedef_ids} for v in liste],
                "print_areas": [{"variant_ids": ids, "placeholders": [
                    {"position": p, "images": [{"id": gorsel, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]} for p in poz]}
                    for poz, ids in gruplar.items()]}

    yanit, son_hata = None, None
    for liste in (varyant, [v for v in varyant if v["id"] in hedef_ids]):
        try:
            yanit = istek(S, "POST", f"/v1/shops/{shop}/products.json", js=govde(liste))
            break
        except ApiHata as e:
            son_hata = e
            if e.kod not in (400, 422):
                raise
    if yanit is None:
        raise son_hata
    pid = yanit.get("id")
    oz["olusturulan"].append(pid)
    kaydet()
    try:
        maliyet = {v["id"]: f"{int(v['cost']) / 100:.2f}" for v in (yanit.get("variants") or []) if v.get("cost") is not None}
    finally:
        istek(S, "DELETE", f"/v1/shops/{shop}/products/{pid}.json")
        oz["silinen"].append(pid)
        kaydet()
    return maliyet, ("" if maliyet else "YOK (cost yok)")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cikis = sys.argv[1]
    os.makedirs(cikis, exist_ok=True)
    S = oturum()
    if "--temizle" in sys.argv:
        return temizle(S, cikis)
    return oku(S, cikis)


if __name__ == "__main__":
    sys.exit(main())
