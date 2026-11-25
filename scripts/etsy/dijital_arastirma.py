#!/usr/bin/env python3
"""DIJITAL URUN ARASTIRMASI: DERIN TOPLAYICI (huni Asama 2; Serdar 26 Kas "Evet derhal basla", KARARLAR_20261126_2).
SALT OKUMA, Etsy'ye yazma YOK. Yalniz API anahtari (APIKeyStore; OAuth token yok), yalniz GET (SaltOkur: GET disi her istek SystemExit).

Girdi: Serdar'in isaretledigi 1-8 terim (config/dijital_terimler.txt icinden, --terimler "a;b;..."). Taksonomi agaci YOK (26 Kas
analizi: 198 turun 161'inde kategori sayimi Etsy genelini dondurdu). Durum dosyasi terim kumesine baglidir: baska kume -> HATA.

Asamalar (durum out/durum.json; her kosu kaldigi yerden devam eder):
  ornek : her terimde iki grup, grup basina GRUP_N (15) aninda indirilen (listing_type download) + kisisellestirmesiz ilan:
          relevans = keywords + sort_on score; yeni = keywords + sort_on created, YALNIZ original_creation_timestamp son YENI_GUN
          (365) gun icinde olanlar (yenilenmis eski ilan "yeni" sayilmaz). Ilan kimligiyle TEKIL: ILANLAR.csv ilan basina tek satir,
          terim / grup baglari ILAN_TERIM.csv. Magazalar /listings/batch includes=Shop (magaza basina tek temsilci) -> MAGAZALAR.csv
  yorum : yorum onbellegi YALNIZ ilan kimligiyle (ayni ilan iki terimde bir kez okunur). Once her ilanin ilk sayfasi (sayim + ilk
          100 yorum); sonra her terimde en cok yorumlu YORUM_TAM_N (5) ilanin kalan sayfalari (ilan basina en cok YORUM_SAYFA_AZAMI
          sayfa; asilirsa 'kesik'). Hedef (50 sikayet + 50 ovgu) YOK: dusuk yildizlilar (3 ve alti) kac tane ise raporlanir.
          -> YORUMLAR.csv (buyer_user_id / transaction_id / gorsel YAZILMAZ)
  ozet  : ag yok: TERIM_OZET.csv (terim x grup) + YORUMLAR_ETIKETLI.csv + EKSIK_ALAN.csv. "kanitli satis" YOK: sutun adi
          son_12ay_yorum_sayisi, siralamada kullanilmaz (satir sirasi = girdi terim sirasi). Fiyat yalniz USD; USD disi ayri sayilir.
Durma: --dk sure butcesi; kota: kalan < %20 * gunluk sinir ya da etsy_common sert tabani; baska Etsy kilit kumesi kosusu aktif olursa
yol verir (kaydeder, cikar). Durum dosyasinda toplam istek sayaci, zaman damgasi ve kosu kayitlari.
Log: yalniz sayilar (KimlikSuz: 6+ haneli sayi '<id>'). Terim / ilan basligi / metin / magaza adi loga yazilmaz.
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

GRUP_N = 15            # grup basina ilan
GRUP_SAYFA = 4         # grup basina en cok sayfa (100'luk)
YENI_GUN = 365         # "yeni" grubu: original_creation_timestamp bu kadar gunden yeni
YORUM_TAM_N = 5        # terim basina tum yorumlari okunan en cok yorumlu ilan
YORUM_SAYFA_AZAMI = 10  # ilan basina en cok yorum sayfasi (100'luk)
TERIM_AZAMI = 8
KOTA_PAY = 0.20        # kalan < KOTA_PAY * gunluk sinir -> dur
YOL_VER_SN = 60        # baska Etsy kosusu kontrol araligi
DK_AZAMI = 45          # kosu basina Etsy okuma suresi tavani (kilit tutma)
AY_SN = 30.4375 * 86400
VARSAYILAN_LISTE = Path(__file__).resolve().parents[2] / "config" / "dijital_terimler.txt"


class KotaDur(Exception):
    pass


class YolVer(Exception):
    pass


class SureDoldu(Exception):
    pass


class KimlikSuz:
    """stdout/stderr suzgeci: 6+ haneli sayilar '<id>' (ilan / magaza kimlikleri loga girmez)."""
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


def utc(ts=None):
    return datetime.fromtimestamp(ts if ts is not None else time.time(), timezone.utc).isoformat(timespec="seconds")


class SaltOkur(E.Etsy):
    def _call(self, method, path, **kw):
        if str(method).upper() != "GET":
            raise SystemExit(f"DUR: salt okuma kosusu, {method} yasak")
        return super()._call(method, path, **kw)


# ------------------------------------------------------------------ terimler (terim_tarama ile ortak)
def terimler_oku(yol):
    out, gor = [], set()
    for s in Path(yol).read_text(encoding="utf-8").splitlines():
        s = " ".join(s.split())
        if not s or s.startswith("#"):
            continue
        if len(s) > 100:
            raise SystemExit("HATA: terim listesinde 100 karakterden uzun satir")
        if s.lower() not in gor:
            gor.add(s.lower())
            out.append(s)
    if not out:
        raise SystemExit("HATA: terim listesi bos")
    return out


def secim_coz(liste, yalniz, bos_hepsi=True):
    """yalniz: ';' ile ayrilmis terimler. Listede olmayan terim -> HATA (yazim hatasi sessiz gecmez)."""
    if not (yalniz or "").strip():
        if bos_hepsi:
            return list(liste)
        raise SystemExit("HATA: terim girdisi bos")
    idx = {t.lower(): t for t in liste}
    sec, bilinmeyen = [], 0
    for s in yalniz.split(";"):
        s = " ".join(s.split()).lower()
        if not s:
            continue
        if s not in idx:
            bilinmeyen += 1
            continue
        if idx[s] not in sec:
            sec.append(idx[s])
    if bilinmeyen:
        raise SystemExit(f"HATA: terim girdisinde listede olmayan {bilinmeyen} terim (config/dijital_terimler.txt)")
    if not sec:
        raise SystemExit("HATA: terim girdisi bos")
    return sec


# ------------------------------------------------------------------ istemci sarmali
class Okuyucu:
    def __init__(self, api, dk, yol_ver_fn=None, saat=time.monotonic, ham_get=None):
        self.api = api
        self.bitis = saat() + dk * 60
        self.saat = saat
        self.yol_ver_fn = yol_ver_fn
        self._son_kontrol = saat()
        self.limit_gun = None
        self.ham_get = ham_get
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
ILAN_ALAN = ["listing_id", "url", "shop_id", "title", "price", "currency", "num_favorers", "views", "tags", "created_timestamp",
             "updated_timestamp", "original_creation_timestamp", "listing_type", "is_personalizable", "taxonomy_id", "quantity",
             "has_variations", "review_count_api"]
UYELIK_ALAN = ["terim", "grup", "sira", "listing_id"]
YORUM_ALAN = ["listing_id", "url", "shop_id", "rating", "created_timestamp", "tarih", "language", "review", "yorum_sira"]
MAGAZA_ALAN = ["shop_id", "shop_name", "url", "transaction_sold_count", "review_count", "review_average", "create_date",
               "created_timestamp", "listing_active_count", "digital_listing_count", "num_favorers",
               "shop_location_country_iso", "is_vacation"]


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
        self.d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"asama": "ornek", "kosu": 0, "istek_toplam": 0}
        self.ilan = {r["listing_id"]: r for r in oku_csv(self.out / "ILANLAR.csv")}
        self.uyelik = oku_csv(self.out / "ILAN_TERIM.csv")
        self.magaza = {r["shop_id"]: r for r in oku_csv(self.out / "MAGAZALAR.csv")}
        self.yorum = {}
        for r in oku_csv(self.out / "YORUMLAR.csv"):
            self.yorum[self.yorum_anahtar(r)] = r

    @staticmethod
    def yorum_anahtar(r):
        return (str(r["listing_id"]), str(r.get("yorum_sira", "")), str(r["created_timestamp"]))

    def kaydet(self):
        yaz_csv(self.out / "ILANLAR.csv", ILAN_ALAN, self.ilan.values())
        yaz_csv(self.out / "ILAN_TERIM.csv", UYELIK_ALAN, self.uyelik)
        yaz_csv(self.out / "MAGAZALAR.csv", MAGAZA_ALAN, self.magaza.values())
        yaz_csv(self.out / "YORUMLAR.csv", YORUM_ALAN, self.yorum.values())
        self.d["son_guncelleme_utc"] = utc()
        tmp = self.out / "durum.json.tmp"
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.out / "durum.json")

    def terim_ilanlari(self, terim, grup=None):
        """terim (ve grup) baglarindan tekil ilan kimlikleri, ilk gorulme sirasiyla."""
        out, gor = [], set()
        for u in self.uyelik:
            if u["terim"] == terim and (grup is None or u["grup"] == grup) and u["listing_id"] not in gor:
                gor.add(u["listing_id"])
                out.append(u["listing_id"])
        return out


# ------------------------------------------------------------------ yardimcilar
def fiyat(p):
    try:
        return round(int(p["amount"]) / int(p["divisor"]), 2), p.get("currency_code", "")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return "", ""


def ilan_satiri(L):
    f, c = fiyat(L.get("price") or {})
    return {"listing_id": str(L.get("listing_id")), "url": L.get("url", ""), "shop_id": str(L.get("shop_id")),
            "title": L.get("title", ""), "price": f, "currency": c,
            "num_favorers": L.get("num_favorers", ""), "views": L.get("views", ""), "tags": "|".join(L.get("tags") or []),
            "created_timestamp": L.get("created_timestamp", L.get("creation_timestamp", "")),
            "updated_timestamp": L.get("updated_timestamp", L.get("last_modified_timestamp", "")),
            "original_creation_timestamp": L.get("original_creation_timestamp", ""),
            "listing_type": L.get("listing_type", ""), "is_personalizable": L.get("is_personalizable", ""),
            "taxonomy_id": L.get("taxonomy_id", ""), "quantity": L.get("quantity", ""),
            "has_variations": L.get("has_variations", ""), "review_count_api": ""}


def uygun(L):
    return L.get("listing_type") == "download" and not L.get("is_personalizable") and not L.get("personalization_is_required")


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def yeni_mi(L, simdi):
    t = _int(L.get("original_creation_timestamp"))
    return t is not None and t >= simdi - YENI_GUN * 86400


# ------------------------------------------------------------------ asama: ornek
def grup_topla(ok, terim, grup, mevcut, n_ek, offset0, simdi):
    params = {"keywords": terim, "limit": 100}
    if grup == "relevans":
        params["sort_on"] = "score"
    else:
        params.update({"sort_on": "created", "sort_order": "desc"})
    secilen, offset, gorulen = [], offset0, set()
    for _ in range(GRUP_SAYFA):
        params["offset"] = offset
        j = ok.get("/listings/active", dict(params), hata_bos=True)
        res = (j or {}).get("results") or []
        for L in res:
            lid = str(L["listing_id"])
            if not uygun(L) or lid in mevcut or lid in gorulen:
                continue
            if grup == "yeni" and not yeni_mi(L, simdi):
                continue
            secilen.append(L)
            gorulen.add(lid)
            if len(secilen) >= n_ek:
                return secilen, offset + 100
        offset += 100
        if len(res) < 100:
            break
    return secilen, offset


def asama_ornek(dp, ok, terimler, simdi):
    yap = dp.d.setdefault("ornek_bitti", [])
    ofs = dp.d.setdefault("ornek_offset", {})
    for k, t in enumerate(terimler):
        mevcut = set(dp.terim_ilanlari(t))
        for grup in ("relevans", "yeni"):
            anahtar = f"{t}\t{grup}"
            if anahtar in yap:
                continue
            sec, o1 = grup_topla(ok, t, grup, mevcut, GRUP_N, ofs.get(anahtar, 0), simdi)
            # ayni adimda (arada istek yok): satirlar + baglar + offset + bitti
            ofs[anahtar] = o1
            for i, L in enumerate(sec):
                lid = str(L["listing_id"])
                if lid not in dp.ilan:
                    dp.ilan[lid] = ilan_satiri(L)
                dp.uyelik.append({"terim": t, "grup": grup, "sira": i + 1, "listing_id": lid})
                mevcut.add(lid)
            yap.append(anahtar)
        dp.kaydet()
        log(f"ornek: terim {k + 1}/{len(terimler)} | tekil ilan {len(dp.ilan)} | bag {len(dp.uyelik)} | kota {ok.api.remaining}")
    magaza_topla(dp, ok)
    dp.d["asama"] = "yorum"
    log(f"ORNEK: terim {len(terimler)} | tekil ilan {len(dp.ilan)} | bag {len(dp.uyelik)} | magaza {len(dp.magaza)}")


def magaza_topla(dp, ok):
    tekil, gorulen = [], set()
    for s in dp.ilan.values():
        sid = str(s["shop_id"])
        if sid not in dp.magaza and sid not in gorulen:
            gorulen.add(sid)
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
        r = {"listing_id": str(s["listing_id"]), "url": s["url"], "shop_id": s["shop_id"],
             "rating": y.get("rating", ""), "created_timestamp": ts,
             "tarih": datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d") if str(ts).isdigit() else "",
             "language": y.get("language", ""), "review": (y.get("review") or "").replace("\r", " "), "yorum_sira": offset + i}
        dp.yorum[dp.yorum_anahtar(r)] = r


def sayfa_al(dp, ok, lid, yd):
    s = dp.ilan[lid]
    st = yd.setdefault(lid, {"count": None, "offset": 0, "bitti": False})
    j = ok.get(f"/listings/{lid}/reviews", {"limit": 100, "offset": st["offset"]}, hata_bos=True)
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
    elif st["offset"] >= YORUM_SAYFA_AZAMI * 100:
        st["bitti"] = True
        st["kesik"] = True
    s["review_count_api"] = st["count"]


def asama_yorum(dp, ok, terimler):
    yd = dp.d.setdefault("yorum", {})
    t0 = time.monotonic()
    # 1) her tekil ilanin ilk sayfasi
    bekleyen = [lid for lid in dp.ilan if lid not in yd or (yd[lid]["count"] is None and not yd[lid]["bitti"])]
    for i, lid in enumerate(bekleyen):
        sayfa_al(dp, ok, lid, yd)
        if i % 100 == 0:
            dp.kaydet()
            log(f"yorum ilk sayfa: {i}/{len(bekleyen)} | yorum {len(dp.yorum)} | {time.monotonic() - t0:.0f} sn | kota {ok.api.remaining}")
    for lid, s in dp.ilan.items():
        st = yd.get(lid)
        if st:
            s["review_count_api"] = st.get("count") or 0
    # 2) terim basina en cok yorumlu YORUM_TAM_N ilanin kalan sayfalari (sabit secim: durum dosyasinda)
    tam = dp.d.setdefault("yorum_tam", {})
    for t in terimler:
        if t not in tam:
            ids = [lid for lid in dp.terim_ilanlari(t) if (yd.get(lid) or {}).get("count")]
            ids.sort(key=lambda lid: (-int(yd[lid]["count"] or 0), lid))
            tam[t] = ids[:YORUM_TAM_N]
    for t in terimler:
        for lid in tam[t]:
            while not yd[lid]["bitti"]:
                sayfa_al(dp, ok, lid, yd)
        dp.kaydet()
        log(f"yorum tam: terim {terimler.index(t) + 1}/{len(terimler)} | yorum {len(dp.yorum)} | kota {ok.api.remaining}")
    dp.d["asama"] = "ozet"
    log(f"YORUM: bitti | yorum {len(dp.yorum)} | tekil ilan {len(dp.ilan)}")


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


def son12_tam(st, yorumlar, yil_once):
    """Ilanin son 12 ay yorum sayisi tam mi: tum sayfalar okunduysa (kesik / hata degil) evet; degilse okunan yorumlar yorum_sira
    sirasinda yeniden eskiye diziliyse ve en eski okunan 12 aydan eskiyse evet; aksi halde alt sinir."""
    if st and st.get("bitti") and not st.get("hata") and not st.get("kesik"):
        return True
    ts = [int(y["created_timestamp"]) for y in sorted(yorumlar, key=lambda y: int(y["yorum_sira"]))
          if str(y["created_timestamp"]).isdigit()]
    return bool(ts) and all(a >= b for a, b in zip(ts, ts[1:])) and ts[-1] < yil_once


def asama_ozet(dp, terimler, simdi=None):
    simdi = simdi or simdi_ts()
    yil_once = simdi - 365 * 86400
    yd = dp.d.get("yorum", {})
    etiketli = []
    yor_by = {}
    for r in dp.yorum.values():
        r = dict(r)
        r["duygu"] = duygu(r["rating"])
        r["temalar"] = "|".join(k for k, rx in TEMA_RX.items() if rx.search(r.get("review") or ""))
        etiketli.append(r)
        yor_by.setdefault(str(r["listing_id"]), []).append(r)
    yaz_csv(dp.out / "YORUMLAR_ETIKETLI.csv", YORUM_ALAN + ["duygu", "temalar"], etiketli)
    tam_sec = dp.d.get("yorum_tam", {})
    ozet = []
    for t in terimler:
        for grup in ("hepsi", "relevans", "yeni"):
            lids = dp.terim_ilanlari(t, None if grup == "hepsi" else grup)
            ilanlar = [dp.ilan[x] for x in lids if x in dp.ilan]
            yorumlar = [y for x in lids for y in yor_by.get(x, [])]
            api_top = sum(int(s.get("review_count_api") or 0) for s in ilanlar)
            y12 = [y for y in yorumlar if str(y["created_timestamp"]).isdigit() and int(y["created_timestamp"]) >= yil_once]
            tam12 = all(son12_tam(yd.get(x), yor_by.get(x, []), yil_once) for x in lids)
            neg = [y for y in yorumlar if y["duygu"] == "olumsuz"]
            pos = [y for y in yorumlar if y["duygu"] == "olumlu"]

            def ilk3(ys):
                c = {}
                for y in ys:
                    for k in filter(None, y["temalar"].split("|")):
                        c[k] = c.get(k, 0) + 1
                return "; ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0]))[:3])

            usd = [float(s["price"]) for s in ilanlar if s.get("currency") == "USD" and s.get("price") not in ("", None)]
            # bellek (int) ve CSV'den okunan (str) deger ayni sonucu vermeli: 0 da sayilir (_int)
            yas = [(simdi - v) / AY_SN for v in (_int(s.get("original_creation_timestamp")) for s in ilanlar) if v]
            fav = [v for v in (_int(s.get("num_favorers")) for s in ilanlar) if v is not None]
            ozet.append({
                "terim": t, "grup": grup, "ilan_sayisi": len(ilanlar),
                "magaza_sayisi": len({s["shop_id"] for s in ilanlar}),
                "yorum_toplami_api": api_top, "yorum_okunan": len(yorumlar),
                "yorumu_tam_okunan_ilan": sum(1 for x in lids if (yd.get(x) or {}).get("bitti") and not (yd.get(x) or {}).get("hata")
                                              and not (yd.get(x) or {}).get("kesik")),
                "yorum_kesik_ilan": sum(1 for x in lids if (yd.get(x) or {}).get("kesik")),
                "yorum_hatali_ilan": sum(1 for x in lids if (yd.get(x) or {}).get("hata")),
                "tum_yorumu_okunan_secim": len([x for x in tam_sec.get(t, []) if x in lids]),
                "son_12ay_yorum_sayisi": len(y12), "son_12ay_yorum_tam": "evet" if tam12 else "alt_sinir",
                "dusuk_yildiz_n": len(neg), "dusuk_yildiz_payi": round(len(neg) / len(yorumlar), 3) if yorumlar else "",
                "yildiz4_n": sum(1 for y in yorumlar if y["duygu"] == "notr"), "yildiz5_n": len(pos),
                "dusuk_yildiz_ilk3_tema": ilk3(neg), "yildiz5_ilk3_tema": ilk3(pos),
                "fiyat_p25_usd": yuzdelik(usd, .25), "fiyat_medyan_usd": yuzdelik(usd, .5), "fiyat_p75_usd": yuzdelik(usd, .75),
                "fiyat_usd_n": len(usd), "fiyat_usd_disi_n": len(ilanlar) - len(usd),
                "ilan_yasi_medyan_ay": round(statistics.median(yas), 1) if yas else "",
                "favori_medyan": statistics.median(fav) if fav else "",
                "not": ("yorum sayisi satis degildir; son_12ay_yorum_sayisi siralamada kullanilmaz"
                        + (f"; yeni = original_creation son {YENI_GUN} gun" if grup == "yeni" else "")),
            })
    alanlar = list(ozet[0].keys()) if ozet else ["terim"]
    yaz_csv(dp.out / "TERIM_OZET.csv", alanlar, ozet)
    eksik = []
    for ad, satirlar, kolonlar in (("ILANLAR", list(dp.ilan.values()), ILAN_ALAN), ("MAGAZALAR", list(dp.magaza.values()), MAGAZA_ALAN),
                                   ("YORUMLAR", list(dp.yorum.values()), YORUM_ALAN)):
        n = len(satirlar)
        for k in kolonlar:
            bos = sum(1 for s in satirlar if s.get(k) in ("", None))
            eksik.append({"dosya": ad, "alan": k, "satir": n, "bos": bos, "bos_oran": round(bos / n, 3) if n else ""})
    yaz_csv(dp.out / "EKSIK_ALAN.csv", ["dosya", "alan", "satir", "bos", "bos_oran"], eksik)
    hepsi = [o for o in ozet if o["grup"] == "hepsi"]
    log(f"OZET: terim {len(hepsi)} | yorum {len(etiketli)} | dusuk yildiz {sum(o['dusuk_yildiz_n'] for o in hepsi)}"
        f" | tekil ilan {len(dp.ilan)} | magaza {len(dp.magaza)}")


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


def calis(out, dk, api, terimler, yol_ver_fn=None, ham_get=None, simdi=None):
    dk = max(0.0, min(float(dk), DK_AZAMI))
    if not terimler or len(terimler) > TERIM_AZAMI:
        log(f"HATA: terim sayisi 1-{TERIM_AZAMI} olmali ({len(terimler or [])})")
        return 1
    try:
        dp = Depo(out)
    except Exception as e:  # noqa: BLE001 icerik loga girmez
        log(f"HATA: durum okunamadi ({type(e).__name__})")
        return 1
    if dp.d.get("terimler") not in (None, list(terimler)):
        log("HATA: durum dosyasi baska terim kumesine ait (yeni kume icin yeni etiket / klasor)")
        return 1
    dp.d["terimler"] = list(terimler)
    dp.d["kosu"] = dp.d.get("kosu", 0) + 1
    simdi = simdi or simdi_ts()
    ok = Okuyucu(api, dk, yol_ver_fn)
    istek_bas = int(dp.d.get("istek_toplam") or 0)
    ping = 0
    kayit = {"kosu": dp.d["kosu"], "bas_utc": utc()}
    dp.d.setdefault("kosular", []).append(kayit)
    kod = 0
    try:
        if not dp.d.get("limit_gun"):
            if ham_get is None:
                raise SystemExit("HATA: gunluk sinir okunamadi (ping yok)")
            ping += 1
            h = ham_get("/openapi-ping")
            lim = _int(h.get("x-limit-per-day"))
            if not lim:
                raise SystemExit("HATA: x-limit-per-day basligi okunamadi")
            dp.d["limit_gun"] = lim
        ok.limit_gun = int(dp.d["limit_gun"])
        if dp.d["asama"] == "ornek":
            asama_ornek(dp, ok, terimler, simdi)
            dp.kaydet()
        if dp.d["asama"] == "yorum":
            asama_yorum(dp, ok, terimler)
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
        asama_ozet(dp, terimler, simdi)      # her kosu sonunda ara ozet (ag yok)
        if dp.d["asama"] == "ozet":
            dp.d["asama"] = "bitti"
    except Exception as e:  # noqa: BLE001
        kod = kod or 1
        log(f"HATA (ozet): {type(e).__name__}")
    dp.d["istek_toplam"] = istek_bas + api.calls + ping
    kayit.update({"bit_utc": utc(), "istek": api.calls + ping, "kota_son": api.remaining, "kod": kod, "asama": dp.d["asama"]})
    try:
        dp.kaydet()
    except Exception as e:  # noqa: BLE001
        log(f"HATA (kaydet): {type(e).__name__}")
        return 1
    log(f"KOSU {dp.d['kosu']}: asama {dp.d['asama']} | istek {api.calls + ping} (toplam {dp.d['istek_toplam']}) | hata {ok.hata}"
        f" | kota {api.remaining} | tekil ilan {len(dp.ilan)} | yorum {len(dp.yorum)} | magaza {len(dp.magaza)}")
    return kod


def main():
    sys.stdout = KimlikSuz(sys.stdout)
    sys.stderr = KimlikSuz(sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dk", type=float, default=40)
    ap.add_argument("--terimler", required=True, help="';' ile ayrilmis 1-8 terim (config/dijital_terimler.txt icinden)")
    ap.add_argument("--liste", default=str(VARSAYILAN_LISTE))
    a = ap.parse_args()
    try:
        terimler = secim_coz(terimler_oku(a.liste), a.terimler, bos_hepsi=False)
    except SystemExit as e:
        log(str(e))
        return 1
    st = E.APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""))
    api = SaltOkur(st)
    yv = yol_ver_gh if os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_RUN_ID") else None
    return calis(a.out, a.dk, api, terimler, yv, ham_ping(st))


if __name__ == "__main__":
    sys.exit(main())
