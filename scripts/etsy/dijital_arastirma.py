#!/usr/bin/env python3
"""DIJITAL URUN ARASTIRMASI (Serdar onayi 25 Kas 2026: Etsy resmi API salt okuma). SALT OKUMA, Etsy'ye yazma YOK.
Yalniz API anahtari (APIKeyStore; OAuth token indirilmez / yenilenmez), yalniz GET (SaltOkur: GET disi her istek SystemExit).

Amac: Etsy'de aninda indirilen (listing_type == "download") ve kisisellestirmesiz (is_personalizable false) dijital urun
turlerini, orneklem ilanlarini, yorumlarini ve magazalarini toplamak. Satis tahmini YOK: her yorum en az 1 satis (alt sinir).

Asamalar (durum out/durum.json'da; her kosu kaldigi yerden devam eder):
  olc    : API denemesi (basliklar, uc noktalar, alanlar) -> API_OLCUM.json
  agac   : seller taksonomi agaci (TAKSONOMI.csv) + dugum basina ~100 ilanlik orneklemle download orani (TURLER.csv)
  ornek  : her aday turde 15 relevans (sort score + keywords) + 15 yeni (sort created); download + kisisellestirmesiz
           -> ILANLAR.csv; magazalar /listings/batch includes=Shop -> MAGAZALAR.csv
  yorum  : once her ilanin ilk sayfasi (sayim), sonra hedefi (50 olumsuz + 50 olumlu) tutmayan turlerde sonraki sayfalar,
           sonra kalan tum sayfalar -> YORUMLAR.csv (buyer_user_id / transaction_id / gorsel YAZILMAZ)
  ozet   : ag yok: etiketleme + TUR_OZET.csv + EKSIK_ALAN.csv
Durma: --dk sure butcesi; kota: kalan < %20 * gunluk sinir (gunluk sinirin %80'i kullanildi) ya da etsy_common sert tabani;
baska Etsy kilit kumesi kosusu aktif olursa yol verir (kaydeder, cikar; sonraki kosu devam eder).
Log: yalniz sayilar (KimlikSuz: 6+ haneli sayi '<id>'). Ilan basligi / metin / magaza adi loga yazilmaz.
Cikis: 0 = bu kosu temiz bitti (devam gerekebilir: durum.json 'asama'), 3 = kota durdurdu, 4 = yol verildi, 1 = hata.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402

csv.field_size_limit(10 ** 8)

ORNEK_N = 100          # dugum orneklemi (ilan)
GRUP_N = 15            # grup basina ilan
ADAY_ORAN = 0.30       # download orani esigi (aday tur)
ADAY_MIN_N = 20        # oran icin en az orneklenen ilan
D3_ESIK = 0.05         # (alt dugumleri kapsayan filtrede) derinlik 3'e inmek icin ust dugum orani
D4_AZAMI = 300         # derinlik 4 icin en fazla istek
HEDEF = 50             # tur basina olumsuz ve olumlu hedefi
KOTA_PAY = 0.20        # kalan < KOTA_PAY * gunluk sinir -> dur
YOL_VER_SN = 60        # baska Etsy kosusu kontrol araligi
DK_AZAMI = 45          # kosu basina Etsy okuma suresi tavani (kilit tutma)


class KotaDur(Exception):
    pass


class YolVer(Exception):
    pass


class SureDoldu(Exception):
    pass


class KimlikSuz:
    """stdout/stderr suzgeci: 6+ haneli sayilar '<id>' (ilan / magaza / taksonomi kimlikleri loga girmez)."""
    RX = re.compile(r"(?<!\w)\d{6,}")

    def __init__(self, akis):
        self.akis = akis

    def write(self, s):
        if s.startswith("::add-mask::"):
            return self.akis.write(s)
        return self.akis.write(self.RX.sub("<id>", s))

    def flush(self):
        return self.akis.flush()


def kisa_hata(m):
    """'HATA: GET /yol -> 404: <govde>' -> govdesiz ilk kisim (Etsy hata govdesi loga girmez)."""
    k = str(m).split(": ", 2)
    return ": ".join(k[:2])[:160]


def log(m):
    print(m, flush=True)


def simdi_ts():
    return int(time.time())


class SaltOkur(E.Etsy):
    def _call(self, method, path, **kw):
        if str(method).upper() != "GET":
            raise SystemExit(f"DUR: salt okuma kosusu, {method} yasak")
        return super()._call(method, path, **kw)


# ------------------------------------------------------------------ istemci sarmali
class Okuyucu:
    def __init__(self, api, dk, yol_ver_fn=None, saat=time.monotonic, ham_get=None):
        self.api = api
        self.bitis = saat() + dk * 60
        self.saat = saat
        self.yol_ver_fn = yol_ver_fn
        self._son_kontrol = saat()
        self.limit_gun = None
        self.ham_get = ham_get   # basliklar icin (olc)
        self.hata = 0

    def kontrol(self):
        if self.saat() >= self.bitis:
            raise SureDoldu()
        if self.yol_ver_fn and self.saat() - self._son_kontrol >= YOL_VER_SN:
            self._son_kontrol = self.saat()
            if self.yol_ver_fn():
                raise YolVer()
        if self.limit_gun and self.api.remaining is not None:
            if int(self.api.remaining) < KOTA_PAY * self.limit_gun:
                raise KotaDur()

    def get(self, path, params=None, hata_bos=False):
        self.kontrol()
        try:
            return self.api.get(path, params=params)
        except SystemExit as e:
            m = str(e)
            if m.startswith(("HATA: 429", "DUR: kota")):
                raise KotaDur() from None
            self.hata += 1
            if hata_bos:
                return None
            raise SystemExit(kisa_hata(m)) from None
        except (OSError, ValueError) as e:   # requests Timeout/ConnectionError (OSError), bozuk JSON (ValueError)
            self.hata += 1
            if hata_bos:
                return None
            raise SystemExit(f"HATA: ag {type(e).__name__}") from None


# ------------------------------------------------------------------ dosyalar
ILAN_ALAN = ["tur_id", "grup", "sira", "listing_id", "url", "shop_id", "title", "price", "currency", "num_favorers", "views",
             "tags", "created_timestamp", "updated_timestamp", "original_creation_timestamp", "listing_type",
             "is_personalizable", "taxonomy_id", "quantity", "has_variations", "review_count_api"]
YORUM_ALAN = ["tur_id", "listing_id", "url", "shop_id", "rating", "created_timestamp", "tarih", "language", "review", "yorum_sira"]
MAGAZA_ALAN = ["shop_id", "shop_name", "url", "transaction_sold_count", "review_count", "review_average", "create_date",
               "created_timestamp", "listing_active_count", "digital_listing_count", "num_favorers",
               "shop_location_country_iso", "is_vacation"]
TUR_ALAN = ["tur_id", "derinlik", "ad", "yol", "ust_id", "cocuk_sayisi", "ilan_sayisi_api", "orneklenen", "download_n",
            "download_oran", "both_n", "download_kisisel_n", "uygun_oran", "aday", "tur"]


def oku_csv(p):
    if not Path(p).exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def yaz_csv(p, alanlar, satirlar):
    tmp = str(p) + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow(s)
    os.replace(tmp, p)


class Depo:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        p = self.out / "durum.json"
        self.d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"asama": "olc", "kosu": 0}
        self.dugum = {r["tur_id"]: r for r in oku_csv(self.out / "TURLER.csv")}
        self.ilan = oku_csv(self.out / "ILANLAR.csv")
        self.magaza = {r["shop_id"]: r for r in oku_csv(self.out / "MAGAZALAR.csv")}
        self.yorum = {}
        for r in oku_csv(self.out / "YORUMLAR.csv"):
            self.yorum[self.yorum_anahtar(r)] = r

    @staticmethod
    def yorum_anahtar(r):
        return (str(r["tur_id"]), str(r["listing_id"]), str(r.get("yorum_sira", "")), str(r["created_timestamp"]))

    def kaydet(self):
        yaz_csv(self.out / "TURLER.csv", TUR_ALAN, sorted(self.dugum.values(), key=lambda r: (int(r["derinlik"]), r["yol"])))
        yaz_csv(self.out / "ILANLAR.csv", ILAN_ALAN, self.ilan)
        yaz_csv(self.out / "MAGAZALAR.csv", MAGAZA_ALAN, self.magaza.values())
        yaz_csv(self.out / "YORUMLAR.csv", YORUM_ALAN, self.yorum.values())
        tmp = self.out / "durum.json.tmp"
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.out / "durum.json")


# ------------------------------------------------------------------ yardimcilar
def fiyat(p):
    try:
        return round(int(p["amount"]) / int(p["divisor"]), 2), p.get("currency_code", "")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return "", ""


def ilan_satiri(L, tur_id, grup, sira):
    f, c = fiyat(L.get("price") or {})
    return {"tur_id": tur_id, "grup": grup, "sira": sira, "listing_id": L.get("listing_id"), "url": L.get("url", ""),
            "shop_id": L.get("shop_id"), "title": L.get("title", ""), "price": f, "currency": c,
            "num_favorers": L.get("num_favorers", ""), "views": L.get("views", ""), "tags": "|".join(L.get("tags") or []),
            "created_timestamp": L.get("created_timestamp", L.get("creation_timestamp", "")),
            "updated_timestamp": L.get("updated_timestamp", L.get("last_modified_timestamp", "")),
            "original_creation_timestamp": L.get("original_creation_timestamp", ""),
            "listing_type": L.get("listing_type", ""), "is_personalizable": L.get("is_personalizable", ""),
            "taxonomy_id": L.get("taxonomy_id", ""), "quantity": L.get("quantity", ""),
            "has_variations": L.get("has_variations", ""), "review_count_api": ""}


def uygun(L):
    return L.get("listing_type") == "download" and not L.get("is_personalizable") and not L.get("personalization_is_required")


def agac_duz(sonuc):
    """seller taksonomi -> [(id, derinlik, ad, yol, ust_id, cocuk_sayisi)] (kok derinlik 1)."""
    out = []

    def gez(n, d, ust, yol):
        y = f"{yol} > {n.get('name', '')}" if yol else n.get("name", "")
        ch = n.get("children") or []
        out.append({"tur_id": str(n["id"]), "derinlik": d, "ad": n.get("name", ""), "yol": y, "ust_id": ust or "",
                    "cocuk_sayisi": len(ch)})
        for c in ch:
            gez(c, d + 1, str(n["id"]), y)

    for n in sonuc:
        gez(n, 1, None, "")
    return out


# ------------------------------------------------------------------ asama: olc
def asama_olc(dp, ok, ham_get):
    r = {"zaman_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    h = ham_get("/openapi-ping")
    r["basliklar"] = h
    try:
        ok.limit_gun = int(h.get("x-limit-per-day") or 0) or None
    except ValueError:
        ok.limit_gun = None
    if not ok.limit_gun:
        ok.limit_gun = 10000   # baslik yoksa varsayim (raporda yazilir); %20 = 2000 kalan
        r["limit_varsayim"] = True
    dp.d["limit_gun"] = ok.limit_gun
    lps = h.get("x-limit-per-second")
    try:
        r["onerilen_pace"] = 0.15 if int(lps) >= 10 else 0.25
    except (TypeError, ValueError):
        r["onerilen_pace"] = 0.25
    dp.d["pace"] = r["onerilen_pace"]
    tx = ok.get("/seller-taxonomy/nodes") or {}
    kok = tx.get("results") or []
    duz = agac_duz(kok)
    r["taksonomi"] = {"dugum": len(duz), "derinlik_dagilimi": {str(d): sum(1 for x in duz if x["derinlik"] == d)
                                                               for d in sorted({x["derinlik"] for x in duz})}}
    yaz_csv(dp.out / "TAKSONOMI.csv", ["tur_id", "derinlik", "ad", "yol", "ust_id", "cocuk_sayisi"], duz)
    # findAllListingsActive
    uc = {}
    kok1 = next((x for x in duz if x["derinlik"] == 1 and x["cocuk_sayisi"]), None)
    j = ok.get("/listings/active", {"taxonomy_id": kok1["tur_id"], "limit": 100}, hata_bos=True) if kok1 else None
    res = (j or {}).get("results") or []
    uc["taxonomy_id"] = {"http_ok": j is not None, "count": (j or {}).get("count"), "donen": len(res),
                         "alt_dugum_kapsar": any(str(x.get("taxonomy_id")) != kok1["tur_id"] for x in res) if kok1 else None}
    dp.d["alt_kapsar"] = bool(uc["taxonomy_id"]["alt_dugum_kapsar"])
    j2 = ok.get("/listings/active", {"keywords": "digital download", "sort_on": "score", "limit": 5}, hata_bos=True)
    uc["keywords_score"] = {"http_ok": j2 is not None, "count": (j2 or {}).get("count")}
    j3 = ok.get("/listings/active", {"taxonomy_id": kok1["tur_id"] if kok1 else "", "sort_on": "score", "limit": 5},
                hata_bos=True)
    uc["score_keywordsuz"] = {"http_ok": j3 is not None}
    j4 = ok.get("/listings/active", {"keywords": "digital download", "limit": 1, "offset": 11999}, hata_bos=True)
    j5 = ok.get("/listings/active", {"keywords": "digital download", "limit": 1, "offset": 12000}, hata_bos=True)
    uc["offset_sinir"] = {"offset_11999_ok": j4 is not None, "offset_12000_ok": j5 is not None}
    j6 = ok.get("/listings/active", {"keywords": "digital download", "sort_on": "created", "sort_order": "desc", "limit": 100},
                hata_bos=True)
    ornek = ((j6 or {}).get("results") or []) + res
    alanlar = ["listing_type", "is_personalizable", "num_favorers", "views", "price", "tags", "created_timestamp",
               "updated_timestamp", "original_creation_timestamp", "taxonomy_id", "shop_id", "url"]
    r["ilan_alanlari"] = {a: {"var": sum(1 for L in ornek if a in L), "dolu": sum(1 for L in ornek if L.get(a) not in (None, "", []))}
                          for a in alanlar}
    r["ilan_alanlari_n"] = len(ornek)
    r["listing_type_dagilimi"] = {}
    for L in ornek:
        t = str(L.get("listing_type"))
        r["listing_type_dagilimi"][t] = r["listing_type_dagilimi"].get(t, 0) + 1
    # yorumlar (baska magaza ilani)
    dl = [L for L in ornek if L.get("listing_type") == "download"]
    yr = {}
    for L in dl[:40]:
        jy = ok.get(f"/listings/{L['listing_id']}/reviews", {"limit": 100}, hata_bos=True)
        if jy is None:
            yr["hata"] = yr.get("hata", 0) + 1
            continue
        if (jy.get("count") or 0) > 1:
            jy2 = ok.get(f"/listings/{L['listing_id']}/reviews", {"limit": 1, "offset": 1}, hata_bos=True)
            tsl = [x.get("created_timestamp") or 0 for x in (jy.get("results") or [])]
            yr["yeniden_eskiye"] = all(a >= b for a, b in zip(tsl, tsl[1:]))
            dp.d["yorum_sirali"] = yr["yeniden_eskiye"]
            yr.update({"erisim": True, "count": jy.get("count"), "sayfa1": len(jy.get("results") or []),
                       "offset_calisir": jy2 is not None and len((jy2 or {}).get("results") or []) == 1,
                       "alanlar": sorted((jy.get("results") or [{}])[0].keys())})
            break
    r["yorum_ucu"] = yr
    # magaza
    if ornek:
        sid = ornek[0].get("shop_id")
        js = ok.get(f"/shops/{sid}", hata_bos=True) or {}
        r["magaza_alanlari"] = {a: (a in js and js.get(a) not in (None, "")) for a in MAGAZA_ALAN}
        jb = ok.get("/listings/batch", {"listing_ids": ",".join(str(L["listing_id"]) for L in ornek[:5]), "includes": "Shop"},
                    hata_bos=True) or {}
        bs = [(x.get("shop") or {}) for x in (jb.get("results") or [])]
        r["batch_shop"] = {"donen": len(bs), "shop_dolu": sum(1 for s in bs if s),
                           "transaction_sold_count_var": sum(1 for s in bs if "transaction_sold_count" in s)}
    r["uc_noktalar"] = uc
    r["api_vermiyor"] = sorted([a for a, v in r["ilan_alanlari"].items() if not v["var"]]
                               + [f"shop.{a}" for a, v in (r.get("magaza_alanlari") or {}).items() if not v])
    (dp.out / "API_OLCUM.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    dp.d["asama"] = "agac"
    log(f"OLC: taksonomi {len(duz)} dugum | alt_kapsar {dp.d['alt_kapsar']} | limit/gun {ok.limit_gun} | ornek ilan {len(ornek)}"
        f" | yorum erisim {yr.get('erisim', False)} | api_vermiyor {len(r['api_vermiyor'])}")


# ------------------------------------------------------------------ asama: agac
def dugum_ornekle(dp, ok, n):
    j = ok.get("/listings/active", {"taxonomy_id": n["tur_id"], "limit": ORNEK_N, "sort_on": "created", "sort_order": "desc"},
               hata_bos=True)
    if j is None:
        hs = dp.d.setdefault("dugum_hata", {})
        hs[n["tur_id"]] = hs.get(n["tur_id"], 0) + 1
        if hs[n["tur_id"]] < 2:
            return
    res = (j or {}).get("results") or []
    dl = [L for L in res if L.get("listing_type") == "download"]
    r = dict(n)
    r.update({"ilan_sayisi_api": (j or {}).get("count", ""), "orneklenen": len(res), "download_n": len(dl),
              "download_oran": round(len(dl) / len(res), 3) if res else 0,
              "both_n": sum(1 for L in res if L.get("listing_type") == "both"),
              "download_kisisel_n": sum(1 for L in dl if L.get("is_personalizable")),
              "uygun_oran": round(sum(1 for L in res if uygun(L)) / len(res), 3) if res else 0, "aday": "", "tur": ""})
    dp.dugum[n["tur_id"]] = r


def asama_agac(dp, ok):
    tak = oku_csv(dp.out / "TAKSONOMI.csv")
    cocuk = {}
    for n in tak:
        cocuk.setdefault(n["ust_id"], []).append(n)
    alt = dp.d.get("alt_kapsar", True)
    sira = [n for n in tak if int(n["derinlik"]) <= 2]
    t0, i = time.monotonic(), 0
    for n in sira:
        if n["tur_id"] not in dp.dugum:
            dugum_ornekle(dp, ok, n)
            i += 1
            if i % 50 == 0:
                dp.kaydet()
                log(f"agac d1-2: {len(dp.dugum)}/{len(sira)} | {time.monotonic() - t0:.0f} sn | kota {ok.api.remaining}")
    def oran(tid):
        return float(dp.dugum.get(tid, {}).get("download_oran") or 0)
    d3 = [n for n in tak if int(n["derinlik"]) == 3 and (not alt or oran(n["ust_id"]) >= D3_ESIK)]
    for k, n in enumerate(d3):
        if n["tur_id"] not in dp.dugum:
            dugum_ornekle(dp, ok, n)
            if k % 50 == 0:
                dp.kaydet()
                log(f"agac d3: {k}/{len(d3)} | kota {ok.api.remaining}")
    d3_tum = sum(1 for n in tak if int(n["derinlik"]) == 3)
    d4_tum = [n for p in d3 if oran(p["tur_id"]) >= ADAY_ORAN for n in cocuk.get(p["tur_id"], [])]
    d4 = d4_tum[:D4_AZAMI]
    dp.d["agac_kapsam"] = {"d3_toplam": d3_tum, "d3_orneklenen": len(d3), "d4_aday": len(d4_tum), "d4_orneklenen": len(d4),
                           "d5_ve_alti": sum(1 for n in tak if int(n["derinlik"]) >= 5)}
    log(f"agac kapsam: d3 {len(d3)}/{d3_tum} | d4 {len(d4)}/{len(d4_tum)} | d5+ {dp.d['agac_kapsam']['d5_ve_alti']}")
    for k, n in enumerate(d4):
        if n["tur_id"] not in dp.dugum:
            dugum_ornekle(dp, ok, n)
            if k % 50 == 0:
                dp.kaydet()
                log(f"agac d4: {k}/{len(d4)} | kota {ok.api.remaining}")
    tur_sec(dp)
    dp.d["asama"] = "ornek"
    turler = [t for t, r in dp.dugum.items() if r["tur"] == "1"]
    log(f"AGAC: orneklenen dugum {len(dp.dugum)} (d1-2 {len(sira)}, d3 {len(d3)}, d4 {len(d4)}) | aday {sum(1 for r in dp.dugum.values() if r['aday'] == '1')} | tur {len(turler)}")


def tur_sec(dp):
    for r in dp.dugum.values():
        r["aday"] = "1" if int(r.get("orneklenen") or 0) >= ADAY_MIN_N and float(r.get("uygun_oran") or 0) >= ADAY_ORAN else ""
    aday = {t for t, r in dp.dugum.items() if r["aday"]}
    ust = {t: r["ust_id"] for t, r in dp.dugum.items()}

    def atalar(t):
        while ust.get(t):
            t = ust[t]
            yield t

    atasi_olanlar = {a for t in aday for a in atalar(t)}
    for t, r in dp.dugum.items():
        r["tur"] = "1" if t in aday and t not in atasi_olanlar else ""


# ------------------------------------------------------------------ asama: ornek
def grup_topla(ok, tur, grup, mevcut, n_ek, offset0):
    params = {"taxonomy_id": tur["tur_id"], "limit": 100}
    if grup == "relevans":
        params.update({"keywords": tur["ad"], "sort_on": "score"})
    else:
        params.update({"sort_on": "created", "sort_order": "desc"})
    secilen, offset = [], offset0
    gorulen = set()
    for _ in range(4):
        params["offset"] = offset
        j = ok.get("/listings/active", dict(params), hata_bos=True)
        res = (j or {}).get("results") or []
        for L in res:
            if uygun(L) and str(L["listing_id"]) not in mevcut and str(L["listing_id"]) not in gorulen:
                secilen.append(L)
                gorulen.add(str(L["listing_id"]))
                if len(secilen) >= n_ek:
                    mevcut |= gorulen
                    return secilen, offset + 100
        offset += 100
        if len(res) < 100:
            break
    mevcut |= gorulen
    return secilen, offset


def asama_ornek(dp, ok, ek=False):
    turler = sorted([r for r in dp.dugum.values() if r["tur"] == "1"], key=lambda r: r["yol"])
    var = {}
    for s in dp.ilan:
        var.setdefault(s["tur_id"], set()).add(str(s["listing_id"]))
    yap = dp.d.setdefault("ornek_bitti", [])
    ofs = dp.d.setdefault("ornek_offset", {})
    hedef_ek = dp.d.get("ek_ornek", []) if ek else None
    for k, t in enumerate(turler):
        if ek and t["tur_id"] not in hedef_ek:
            continue
        mevcut = var.setdefault(t["tur_id"], set())
        for grup in ("relevans", "yeni"):
            anahtar = f"{t['tur_id']}:{grup}" + (":ek" if ek else "")
            if anahtar in yap:
                continue
            o0 = ofs.get(f"{t['tur_id']}:{grup}", 0)
            sec, o1 = grup_topla(ok, t, grup, mevcut, GRUP_N, o0)
            # ayni adimda (arada istek yok): satirlar + offset + bitti
            ofs[f"{t['tur_id']}:{grup}"] = o1
            for i, L in enumerate(sec):
                dp.ilan.append(ilan_satiri(L, t["tur_id"], grup + ("_ek" if ek else ""), i + 1))
            yap.append(anahtar)
        if k % 10 == 0:
            dp.kaydet()
            log(f"ornek{' ek' if ek else ''}: tur {k + 1}/{len(turler)} | ilan {len(dp.ilan)} | kota {ok.api.remaining}")
    magaza_topla(dp, ok)
    if not ek:
        dp.d["asama"] = "yorum"
    log(f"ORNEK{' EK' if ek else ''}: tur {len(turler)} | ilan {len(dp.ilan)} | magaza {len(dp.magaza)}")


def magaza_topla(dp, ok):
    eksik_ilan = []
    for s in dp.ilan:
        if str(s["shop_id"]) not in dp.magaza:
            eksik_ilan.append(s)
    gorulen = set()
    tekil = []
    for s in eksik_ilan:
        if str(s["shop_id"]) not in gorulen:
            gorulen.add(str(s["shop_id"]))
            tekil.append(s)
    for i in range(0, len(tekil), 100):
        parti = tekil[i:i + 100]
        jb = ok.get("/listings/batch", {"listing_ids": ",".join(str(s["listing_id"]) for s in parti), "includes": "Shop"},
                    hata_bos=True) or {}
        for x in jb.get("results") or []:
            sh = x.get("shop") or {}
            if sh.get("shop_id"):
                dp.magaza[str(sh["shop_id"])] = {a: sh.get(a, "") for a in MAGAZA_ALAN}
    for s in tekil:   # batch Shop vermediyse tek tek
        sid = str(s["shop_id"])
        if sid not in dp.magaza:
            sh = ok.get(f"/shops/{sid}", hata_bos=True) or {}
            dp.magaza[sid] = {a: sh.get(a, "") for a in MAGAZA_ALAN}
            dp.magaza[sid]["shop_id"] = sid


# ------------------------------------------------------------------ asama: yorum
def yorum_isle(dp, s, res, offset=0):
    for i, y in enumerate(res):
        ts = y.get("created_timestamp") or y.get("create_timestamp") or ""
        r = {"tur_id": s["tur_id"], "listing_id": s["listing_id"], "url": s["url"], "shop_id": s["shop_id"],
             "rating": y.get("rating", ""), "created_timestamp": ts,
             "tarih": datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d") if str(ts).isdigit() else "",
             "language": y.get("language", ""), "review": (y.get("review") or "").replace("\r", " "), "yorum_sira": offset + i}
        dp.yorum[dp.yorum_anahtar(r)] = r


def tur_sayim(dp):
    say = {}
    for r in dp.yorum.values():
        a = say.setdefault(r["tur_id"], [0, 0])
        try:
            v = int(r["rating"])
        except ValueError:
            continue
        if v <= 3:
            a[0] += 1
        elif v == 5:
            a[1] += 1
    return say


def sayfa_al(dp, ok, s, yd):
    k = f"{s['tur_id']}:{s['listing_id']}"
    st = yd.setdefault(k, {"count": None, "offset": 0, "bitti": False})
    j = ok.get(f"/listings/{s['listing_id']}/reviews", {"limit": 100, "offset": st["offset"]}, hata_bos=True)
    if j is None:
        st["hata"] = st.get("hata", 0) + 1
        if st["hata"] >= 2:
            st["bitti"] = True
        return
    res = j.get("results") or []
    st["count"] = j.get("count")
    st.pop("hata", None)
    yorum_isle(dp, s, res, st["offset"])
    st["offset"] += 100
    if not res or st["offset"] >= int(st["count"] or 0):
        st["bitti"] = True
    s["review_count_api"] = st["count"]


def asama_yorum(dp, ok):
    yd = dp.d.setdefault("yorum", {})
    t0 = time.monotonic()
    # 1) her ilanin ilk sayfasi (turler arasinda donusumlu)
    def yeniden(s):
        st = yd.get(f"{s['tur_id']}:{s['listing_id']}")
        return st is None or (st["count"] is None and not st["bitti"])
    bekleyen = [s for s in dp.ilan if yeniden(s)]
    bekleyen.sort(key=lambda s: (int(s["sira"]), s["grup"], s["tur_id"]))
    for i, s in enumerate(bekleyen):
        sayfa_al(dp, ok, s, yd)
        if i % 200 == 0:
            dp.kaydet()
            log(f"yorum ilk sayfa: {i}/{len(bekleyen)} | yorum {len(dp.yorum)} | {time.monotonic() - t0:.0f} sn | kota {ok.api.remaining}")
    for s in dp.ilan:   # sayim alani
        st = yd.get(f"{s['tur_id']}:{s['listing_id']}")
        if st:
            s["review_count_api"] = st.get("count") or 0
    # 2) hedefi tutmayan turler: donusumlu sonraki sayfalar; 3) sonra kalan tum sayfalar
    for mod in ("hedef", "tam"):
        tur = 0
        while True:
            say = tur_sayim(dp)
            adaylar = {}
            for s in dp.ilan:
                st = yd.get(f"{s['tur_id']}:{s['listing_id']}")
                if not st or st["bitti"] or st["count"] is None:
                    continue
                neg, pos = say.get(s["tur_id"], [0, 0])
                if mod == "hedef" and neg >= HEDEF and pos >= HEDEF:
                    continue
                adaylar.setdefault(s["tur_id"], []).append(s)
            if not adaylar:
                break
            for tid, ss in adaylar.items():
                # olumsuz eksikse en cok yorumlu ilandan (en cok olumsuz potansiyeli) ilerle
                ss.sort(key=lambda s: -int(yd[f"{s['tur_id']}:{s['listing_id']}"]["count"] or 0))
                sayfa_al(dp, ok, ss[0], yd)
            tur += 1
            if tur % 5 == 0:
                dp.kaydet()
                log(f"yorum {mod}: tur {tur} | bekleyen tur {len(adaylar)} | yorum {len(dp.yorum)} | kota {ok.api.remaining}")
        if mod == "hedef":
            # ek orneklem: tum yorumlari bitmis ama hedefi tutmayan turler (bir kez)
            say = tur_sayim(dp)
            ek = []
            for t, r in dp.dugum.items():
                if r["tur"] != "1" or t in dp.d.get("ek_ornek", []):
                    continue
                neg, pos = say.get(t, [0, 0])
                if neg < HEDEF or pos < HEDEF:
                    ek.append(t)
            if ek:
                dp.d.setdefault("ek_ornek", []).extend(ek)
                log(f"ek orneklem: {len(ek)} tur")
            bitti = set(dp.d.get("ornek_bitti", []))
            yarim = [t for t in dp.d.get("ek_ornek", []) if f"{t}:relevans:ek" not in bitti or f"{t}:yeni:ek" not in bitti]
            magaza_eksik = any(str(s["shop_id"]) not in dp.magaza for s in dp.ilan)
            ilk_eksik = any(yeniden(s) for s in dp.ilan)
            if yarim or magaza_eksik or ilk_eksik:
                if yarim or magaza_eksik:
                    asama_ornek(dp, ok, ek=True)
                return asama_yorum(dp, ok)
    dp.d["asama"] = "ozet"
    log(f"YORUM: bitti | yorum {len(dp.yorum)} | ilan {len(dp.ilan)}")


# ------------------------------------------------------------------ asama: ozet (ag yok)
TEMALAR = {
    "dosya_kalitesi": r"\b(resolution|pixelat\w*|blurry|blurr\w*|grainy|low quality|high quality|crisp|sharp|dpi|quality)\b",
    "baski_sonucu": r"\b(print(ed|s|ing)?|printer|came out|ink|paper)\b",
    "boyut_oran": r"\b(size|sizes|sizing|ratio|dimension\w*|fit|a4|a3|letter size|8x10|11x14|cropp?\w*|scale)\b",
    "indirme_sorunu": r"\b(download\w*|link|zip|file(s)? (wouldn|won|didn|did not|could not|couldn)\w*|open the file|corrupt\w*|access)\b",
    "aciklamaya_uygunluk": r"\b(as described|as pictured|exactly as|not as described|looks like the (photo|picture)|misleading|expected|different from)\b",
    "satici_iletisimi": r"\b(seller|responsive|communication|replied|response|contacted|helpful|customer service|messag\w*)\b",
    "hiz": r"\b(quick(ly)?|fast|instant(ly)?|immediate(ly)?|right away|speedy|prompt(ly)?)\b",
    "fiyat_deger": r"\b(price|value|worth|cheap|expensive|money|bargain|affordable|overpriced|deal)\b",
    "hediye_amaci": r"\b(gift|present|birthday|christmas|wedding|anniversary|mother'?s day|father'?s day|valentine\w*|baby shower)\b",
    "duygusal_tepki": r"\b(love(d|s)?|beautiful|gorgeous|cute|adorable|amazing|perfect|stunning|disappoint\w*|happy|thrilled|obsessed|lovely)\b",
    "eksik_hatali_icerik": r"\b(missing|incomplete|wrong|error\w*|mistake\w*|typo\w*|broken|not included|only (got|received)|did not include|didn'?t include)\b",
    "kullanim_kolayligi": r"\b(easy to (use|edit|print|follow)|user friendly|instructions|confusing|complicated|hard to)\b",
}
TEMA_RX = {k: re.compile(v, re.I) for k, v in TEMALAR.items()}


def duygu(r):
    try:
        v = int(r)
    except (TypeError, ValueError):
        return ""
    return "olumsuz" if v <= 3 else ("notr" if v == 4 else "olumlu")


def yuzdelik(xs, q):
    xs = sorted(xs)
    if not xs:
        return ""
    i = (len(xs) - 1) * q
    a, b = int(i), min(int(i) + 1, len(xs) - 1)
    return round(xs[a] + (xs[b] - xs[a]) * (i - a), 2)


def asama_ozet(dp, simdi=None):
    simdi = simdi or simdi_ts()
    yil_once = simdi - 365 * 86400
    yd = dp.d.get("yorum", {})
    etiketli = []
    for r in dp.yorum.values():
        r = dict(r)
        r["duygu"] = duygu(r["rating"])
        r["temalar"] = "|".join(k for k, rx in TEMA_RX.items() if rx.search(r.get("review") or ""))
        etiketli.append(r)
    yaz_csv(dp.out / "YORUMLAR_ETIKETLI.csv", YORUM_ALAN + ["duygu", "temalar"], etiketli)
    ilan_by = {}
    for s in dp.ilan:
        ilan_by.setdefault(s["tur_id"], []).append(s)
    yor_by = {}
    for r in etiketli:
        yor_by.setdefault(r["tur_id"], []).append(r)
    ozet = []
    for t, r in sorted(dp.dugum.items(), key=lambda x: x[1]["yol"]):
        if r["tur"] != "1":
            continue
        for grup in ("hepsi", "relevans", "yeni"):
            ilanlar = [s for s in ilan_by.get(t, []) if grup == "hepsi" or s["grup"].startswith(grup)]
            lid = {str(s["listing_id"]) for s in ilanlar}
            yorumlar = [y for y in yor_by.get(t, []) if str(y["listing_id"]) in lid]
            api_top = sum(int(s.get("review_count_api") or 0) for s in ilanlar)
            y12 = [y for y in yorumlar if str(y["created_timestamp"]).isdigit() and int(y["created_timestamp"]) >= yil_once]
            sirali = dp.d.get("yorum_sirali", False)
            tam12 = all((yd.get(f"{t}:{s['listing_id']}", {}).get("bitti") and not yd.get(f"{t}:{s['listing_id']}", {}).get("hata"))
                        or sirali and any(str(y["listing_id"]) == str(s["listing_id"]) and str(y["created_timestamp"]).isdigit()
                            and int(y["created_timestamp"]) < yil_once for y in yorumlar) for s in ilanlar)
            neg = [y for y in yorumlar if y["duygu"] == "olumsuz"]
            pos = [y for y in yorumlar if y["duygu"] == "olumlu"]

            def ilk3(ys):
                c = {}
                for y in ys:
                    for k in filter(None, y["temalar"].split("|")):
                        c[k] = c.get(k, 0) + 1
                return "; ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda x: -x[1])[:3])

            pb = {}
            for s in ilanlar:
                if s.get("price") not in ("", None) and s.get("currency"):
                    pb.setdefault(s["currency"], []).append(float(s["price"]))
            ana_pb = max(pb, key=lambda k: len(pb[k])) if pb else ""
            fiyatlar = pb.get(ana_pb, [])
            magaza_pay = {}
            for s in ilanlar:
                magaza_pay[s["shop_id"]] = magaza_pay.get(s["shop_id"], 0) + int(s.get("review_count_api") or 0)
            ilk10 = sum(sorted(magaza_pay.values(), reverse=True)[:10])
            yorum_tam = sum(1 for s in ilanlar if yd.get(f"{t}:{s['listing_id']}", {}).get("bitti")
                            and not yd.get(f"{t}:{s['listing_id']}", {}).get("hata"))
            yorum_hata = sum(1 for s in ilanlar if yd.get(f"{t}:{s['listing_id']}", {}).get("hata"))
            ozet.append({
                "tur_id": t, "tur_yolu": r["yol"], "grup": grup, "download_oran": r["download_oran"],
                "ilan_sayisi_kategori_api": r["ilan_sayisi_api"], "ilan_sayisi": len(ilanlar),
                "yorum_sayisi_toplanan": len(yorumlar), "yorum_toplami_api": api_top,
                "yorumu_tam_ilan": yorum_tam, "yorum_hatali_ilan": yorum_hata,
                "kanitli_satis_toplam": api_top, "kanitli_satis_12ay": len(y12),
                "kanitli_satis_12ay_tam": "evet" if tam12 else "alt_sinir",
                "kanitli_satis_aylik": round(len(y12) / 12, 1),
                "olumsuz": len(neg), "olumlu": len(pos), "notr": sum(1 for y in yorumlar if y["duygu"] == "notr"),
                "olumsuz_ilk3_tema": ilk3(neg), "olumlu_ilk3_tema": ilk3(pos),
                "hedef_durumu": ("tamam" if len(neg) >= HEDEF and len(pos) >= HEDEF
                                 else f"yetersiz: olumsuz {len(neg)}, olumlu {len(pos)}"),
                "fiyat_p25": yuzdelik(fiyatlar, .25), "fiyat_medyan": yuzdelik(fiyatlar, .5), "fiyat_p75": yuzdelik(fiyatlar, .75),
                "fiyat_para_birimi": ana_pb, "fiyat_n": len(fiyatlar),
                "diger_para_birimi_n": sum(len(v) for k, v in pb.items() if k != ana_pb),
                "magaza_sayisi": len(magaza_pay),
                "ilk10_magaza_kanitli_satis_payi": round(ilk10 / api_top, 3) if api_top else "",
                "not": "ilk10 payi yalniz orneklem ilanlarinin API yorum sayisindan; magaza <= 10 ise 1.0",
            })
    alanlar = list(ozet[0].keys()) if ozet else ["tur_id"]
    yaz_csv(dp.out / "TUR_OZET.csv", alanlar, ozet)
    eksik = []
    for ad, satirlar, kolonlar in (("ILANLAR", dp.ilan, ILAN_ALAN), ("MAGAZALAR", list(dp.magaza.values()), MAGAZA_ALAN),
                                   ("YORUMLAR", list(dp.yorum.values()), YORUM_ALAN)):
        n = len(satirlar)
        for k in kolonlar:
            bos = sum(1 for s in satirlar if s.get(k) in ("", None))
            eksik.append({"dosya": ad, "alan": k, "satir": n, "bos": bos, "bos_oran": round(bos / n, 3) if n else ""})
    yaz_csv(dp.out / "EKSIK_ALAN.csv", ["dosya", "alan", "satir", "bos", "bos_oran"], eksik)
    dp.d["asama"] = "bitti"
    hepsi = [o for o in ozet if o["grup"] == "hepsi"]
    log(f"OZET: tur {len(hepsi)} | hedef tamam {sum(1 for o in hepsi if o['hedef_durumu'] == 'tamam')} | yorum {len(etiketli)}"
        f" | ilan {len(dp.ilan)} | magaza {len(dp.magaza)}")


# ------------------------------------------------------------------ GitHub: baska Etsy kosusu var mi
_GORULEN = {}


def yol_ver_gh():
    """Kilit kumesinde baska aktif kosu 3 ardisik kontrolde (>= 2 dk) gorulurse yol ver (kisa --mod atla turlari beklenir)."""
    import kilit_bekle as K
    kume = K.kilit_kumesi(".", "etsy")
    benim = int(os.environ["GITHUB_RUN_ID"])
    try:
        kosular = K.api_kosular()
    except Exception:   # noqa: BLE001 okunamazsa devam (kilit zaten bizde; yalniz nezaket kontrolu)
        return False
    aktif = {int(k.get("id")) for k in kosular if k.get("path") in kume and k.get("status") in K.AKTIF and int(k.get("id")) != benim}
    for i in list(_GORULEN):
        if i not in aktif:
            del _GORULEN[i]
    for i in aktif:
        _GORULEN[i] = _GORULEN.get(i, 0) + 1
    return any(v >= 3 for v in _GORULEN.values())


def ham_ping(store):
    import requests
    def f(path):
        r = requests.get(E.API + path, headers={"x-api-key": store.api_key_header}, timeout=30)
        return {h: r.headers.get(h, "") for h in ("x-limit-per-day", "x-remaining-today", "x-limit-per-second",
                                                    "x-remaining-this-second")} | {"http": r.status_code}
    return f


def calis(out, dk, api, yol_ver_fn=None, ham_get=None, simdi=None):
    dk = max(0.0, min(float(dk), DK_AZAMI))
    try:
        dp = Depo(out)
    except Exception as e:  # noqa: BLE001 icerik loga girmez
        log(f"HATA: durum okunamadi ({type(e).__name__})")
        return 1
    dp.d["kosu"] = dp.d.get("kosu", 0) + 1
    if dp.d.get("pace"):
        api.pace = float(dp.d["pace"])
    ok = Okuyucu(api, dk, yol_ver_fn)
    ok.limit_gun = dp.d.get("limit_gun")
    bas_kalan = None
    kod = 0
    try:
        if dp.d["asama"] == "olc":
            asama_olc(dp, ok, ham_get)
            api.pace = float(dp.d.get("pace") or api.pace)
            dp.kaydet()
        bas_kalan = api.remaining
        if dp.d["asama"] == "agac":
            asama_agac(dp, ok)
            dp.kaydet()
        if dp.d["asama"] == "ornek":
            asama_ornek(dp, ok)
            dp.kaydet()
        if dp.d["asama"] == "yorum":
            asama_yorum(dp, ok)
            dp.kaydet()
    except KotaDur:
        kod = 3
        log(f"DUR: kota (kalan {api.remaining}, sinir {ok.limit_gun}, esik %{int(KOTA_PAY * 100)})")
    except YolVer:
        kod = 4
        log("YOL VERILDI: baska Etsy kosusu aktif; durum kaydedildi")
    except SureDoldu:
        log("SURE DOLDU: durum kaydedildi")
    except SystemExit as e:
        kod = 1
        log(f"HATA: {kisa_hata(e)}")
    except Exception as e:  # noqa: BLE001 durum yine kaydedilir
        kod = 1
        log(f"HATA: {type(e).__name__}")
    try:
        asama_ozet_guvenli(dp, simdi)
    except Exception as e:  # noqa: BLE001
        kod = kod or 1
        log(f"HATA (ozet): {type(e).__name__}")
    try:
        dp.kaydet()
    except Exception as e:  # noqa: BLE001
        log(f"HATA (kaydet): {type(e).__name__}")
        return 1
    log(f"KOSU {dp.d['kosu']}: asama {dp.d['asama']} | istek {api.calls} | hata {ok.hata} | kota {bas_kalan} -> {api.remaining}"
        f" | ilan {len(dp.ilan)} | yorum {len(dp.yorum)} | magaza {len(dp.magaza)}")
    return kod


def asama_ozet_guvenli(dp, simdi):
    """Her kosu sonunda ara ozet (ag yok). 'bitti' yalniz yorum asamasi bittiyse."""
    asama = dp.d["asama"]
    if not any(r.get("tur") == "1" for r in dp.dugum.values()):
        return
    asama_ozet(dp, simdi)
    if asama != "ozet":
        dp.d["asama"] = asama


def main():
    sys.stdout = KimlikSuz(sys.stdout)
    sys.stderr = KimlikSuz(sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dk", type=float, default=40)
    a = ap.parse_args()
    st = E.APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    api = SaltOkur(st)
    yv = yol_ver_gh if os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_RUN_ID") else None
    return calis(a.out, a.dk, api, yv, ham_ping(st))


if __name__ == "__main__":
    sys.exit(main())
