#!/usr/bin/env python3
"""Etsy gunluk ilan verisi (Serdar 3 Kas "sen gir, api den hersey sen bul"; Merkez 3 Kas). SALT OKUMA: yalniz GET; Etsy'ye yazma yok.
Etsy Stats ilan tablosunun API karsiligi (trafik_oncesi.py 14 Eki yontemi: listing views + num_favorers):
1) GET /shops/{shop}/listings/active (100'luk sayfa): listing_id, baslik, durum, views (ilan sayfasi goruntulenmesi, BIRIKIMLI;
   arama gosterimi DEGIL; Etsy gunde bir hesaplar), num_favorers. Grup: poster (data/pod/pod78_ids.csv), YD (yd78_ids.csv),
   kupa (baslikta mug + iki burc), sade kupa (mug, tek burc), diger.
2) GET /shops/{shop}/receipts (min_created = okuma - 24 saat, 100'luk sayfa): transaction bazinda listing_id, adet, satir geliri
   (price x quantity; kargo, vergi, indirim haric; iptal makbuzlar haric). MUSTERI BILGISI OKUNUR AMA HICBIR DOSYAYA/LOGA YAZILMAZ:
   yalniz listing_id, adet, tutar, para birimi kullanilir.
3) Gunluk goruntulenme farki: onceki gunun views degeri (BIRIKIM.csv'deki son kayit) ile fark; onceki yoksa bos.
Cikti: <cikti>/gunluk/<AAAAGG>.csv (Istanbul tarihi), BIRIKIM.csv (uzun bicim: tarih, listing_id, grup, views, gunluk_fark,
num_favorers; her kosu ayni tarih varsa o tarihi yeniler), OZET.json (istek, kota, grup sayilari).
Kota kapisi: ilk sayfadan sonra kalan >= tahmini kalan istek + KOTA_SINIRI; her istekte sert taban (etsy_common).
Kullanim: etsy_gunluk.py --cikti _out [--birikim _in/BIRIKIM.csv]"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402

IST = ZoneInfo("Europe/Istanbul")
BURC = re.compile(r"\b(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)\b", re.I)
ALAN = ["tarih", "listing_id", "baslik", "grup", "durum", "views", "gunluk_goruntulenme", "num_favorers", "siparis_adet_24s",
        "gelir_24s", "para_birimi", "okuma_utc"]


class SaltOku(E.Etsy):
    """Yalniz GET; her yazma cagrisi kosuyu durdurur."""

    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)


def ids(yol):
    try:
        return {r["listing_id"].strip() for r in csv.DictReader(open(yol, encoding="utf-8-sig"))}
    except OSError:
        return set()


def grup(lid, baslik, poster, yd):
    if lid in poster:
        return "poster"
    if lid in yd:
        return "YD"
    if re.search(r"\bmugs?\b", baslik or "", re.I):
        return "kupa" if len(BURC.findall(baslik or "")) >= 2 and re.search(r"\b(and|&)\b", baslik, re.I) else "sade kupa"
    return "diger"


def tutar(p):
    """Etsy Money {amount, divisor, currency_code} -> (float, para)"""
    p = p or {}
    try:
        return int(p.get("amount") or 0) / int(p.get("divisor") or 100), p.get("currency_code") or ""
    except (TypeError, ValueError):
        return 0.0, p.get("currency_code") or ""


def ilanlar(api, shop):
    out, off = [], 0
    while True:
        j = api.get(f"/shops/{shop}/listings/active", params={"limit": 100, "offset": off}) or {}
        r = j.get("results") or []
        out += r
        if off == 0:
            n = int(j.get("count") or len(r))
            tah = (n // 100) + 2   # kalan ilan sayfalari + en az 1 makbuz sayfasi
            if api.remaining is not None and int(api.remaining) < tah + E.KOTA_SINIRI:
                raise SystemExit(f"DUR: kota {api.remaining} < tahmin {tah} + {E.KOTA_SINIRI}")
        if len(r) < 100:
            return out
        off += 100


def satislar(api, shop, bas_epoch, son_epoch):
    """-> ({listing_id: [adet, gelir]}, para_birimleri, makbuz_sayisi, iptal_sayisi). Musteri alani okunmaz/yazilmaz."""
    s, para, n, iptal, off = defaultdict(lambda: [0, 0.0]), set(), 0, 0, 0
    while True:
        j = api.get(f"/shops/{shop}/receipts", params={"min_created": bas_epoch, "max_created": son_epoch, "limit": 100,
                                                        "offset": off}) or {}
        r = j.get("results") or []
        for rc in r:
            if str(rc.get("status") or "").lower() in ("canceled", "cancelled") or rc.get("is_canceled"):
                iptal += 1; continue
            n += 1
            for t in rc.get("transactions") or []:
                lid = str(t.get("listing_id") or "")
                if not lid:
                    continue
                q = int(t.get("quantity") or 1)
                v, c = tutar(t.get("price"))
                s[lid][0] += q; s[lid][1] += round(v * q, 2); para.add(c)
        if len(r) < 100:
            return s, para, n, iptal
        off += 100


def birikim_oku(yol):
    try:
        return list(csv.DictReader(open(yol, encoding="utf-8")))
    except OSError:
        return []


def calis(api, shop, cikti, birikim_yol=None, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    tarih = simdi.astimezone(IST).strftime("%Y-%m-%d")
    poster, yd = ids(KOK.parents[1] / "data/pod/pod78_ids.csv"), ids(KOK.parents[1] / "data/pod/yd78_ids.csv")
    L = ilanlar(api, shop)
    s, para, makbuz, iptal = satislar(api, shop, int((simdi - timedelta(hours=24)).timestamp()), int(simdi.timestamp()))
    eski = birikim_oku(birikim_yol) if birikim_yol else []
    onceki = {}
    for r in sorted((r for r in eski if r.get("tarih", "") < tarih), key=lambda r: r["tarih"]):
        onceki[r["listing_id"]] = r.get("views")
    okuma = simdi.strftime("%Y-%m-%dT%H:%M:%SZ")
    satir = []
    for x in L:
        lid = str(x.get("listing_id"))
        v = x.get("views")
        o = onceki.get(lid)
        fark = (int(v) - int(o)) if (isinstance(v, int) and str(o or "").lstrip("-").isdigit()) else ""
        q, g = s.get(lid, [0, 0.0])
        satir.append(dict(tarih=tarih, listing_id=lid, baslik=x.get("title") or "", grup=grup(lid, x.get("title"), poster, yd),
                          durum=x.get("state") or "", views=v if v is not None else "", gunluk_goruntulenme=fark,
                          num_favorers=x.get("num_favorers") if x.get("num_favorers") is not None else "", siparis_adet_24s=q,
                          gelir_24s=round(g, 2), para_birimi="/".join(sorted(para)) if q else "", okuma_utc=okuma))
    aktif = {r["listing_id"] for r in satir}
    disari = sorted(set(s) - aktif)   # 24 saatte satilan ama artik aktif olmayan ilan (tukenmis / kapanmis)
    for lid in disari:
        q, g = s[lid]
        satir.append(dict(tarih=tarih, listing_id=lid, baslik="", grup="aktif degil", durum="", views="", gunluk_goruntulenme="",
                          num_favorers="", siparis_adet_24s=q, gelir_24s=round(g, 2), para_birimi="/".join(sorted(para)), okuma_utc=okuma))
    gun = Path(cikti) / "gunluk"; gun.mkdir(parents=True, exist_ok=True)
    with open(gun / f"{tarih.replace('-', '')}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN, lineterminator="\n"); w.writeheader(); w.writerows(satir)
    yeni = [r for r in eski if r.get("tarih") != tarih] + [
        dict(tarih=r["tarih"], listing_id=r["listing_id"], grup=r["grup"], views=r["views"], gunluk_fark=r["gunluk_goruntulenme"],
             num_favorers=r["num_favorers"]) for r in satir if r["grup"] != "aktif degil"]
    with open(Path(cikti) / "BIRIKIM.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tarih", "listing_id", "grup", "views", "gunluk_fark", "num_favorers"], lineterminator="\n")
        w.writeheader(); w.writerows(sorted(yeni, key=lambda r: (r["tarih"], r["listing_id"])))
    gs = defaultdict(int)
    for r in satir:
        gs[r["grup"]] += 1
    oz = dict(tarih=tarih, okuma_utc=okuma, ilan=len(L), grup=dict(gs), makbuz_24s=makbuz, iptal_24s=iptal,
              siparis_adet_24s=sum(v[0] for v in s.values()), gelir_24s=round(sum(v[1] for v in s.values()), 2),
              para_birimi=sorted(para), istek=api.calls, kota_son=api.remaining, onceki_gun_var=bool(onceki))
    (Path(cikti) / "OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"::notice title=ETSY-GUNLUK::{tarih} ilan {len(L)} {dict(gs)} | makbuz {makbuz} | istek {api.calls} kota {api.remaining}", flush=True)
    return oz


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", required=True); ap.add_argument("--birikim", default="")
    a = ap.parse_args(argv)
    k, s_ = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s_)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s_)
    if store.needs_refresh():
        store.refresh()
    calis(SaltOku(store), os.environ["ETSY_SHOP_ID"], a.cikti, a.birikim or None)


if __name__ == "__main__":
    main()
