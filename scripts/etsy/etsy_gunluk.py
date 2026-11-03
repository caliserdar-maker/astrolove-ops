#!/usr/bin/env python3
"""Etsy gunluk ilan verisi (Serdar 3 Kas "sen gir, api den hersey sen bul"; Merkez 3 Kas). SALT OKUMA: yalniz GET; Etsy'ye yazma yok.
Etsy Stats ilan tablosunun API karsiligi (trafik_oncesi.py 14 Eki yontemi: listing views + num_favorers):
1) GET /shops/{shop}/listings/active (100'luk sayfa): listing_id, baslik, durum, views (ilan sayfasi goruntulenmesi, BIRIKIMLI;
   arama gosterimi DEGIL; Etsy gunde bir hesaplar), num_favorers. Grup: poster (data/pod/pod78_ids.csv), YD (yd78_ids.csv),
   kupa (baslikta mug + iki burc), sade kupa (mug, tek burc), diger.
2) GET /shops/{shop}/receipts (was_paid=true, was_canceled=false; min_created/max_created = okumadan ONCEKI Istanbul takvim gunu
   00:00-24:00, 100'luk sayfa; sabit pencere: gunluk dosyalar toplanabilir, cakisma/bosluk yok): transaction bazinda listing_id, adet,
   satir geliri (price x quantity; kargo, vergi, indirim ve iade DUSULMEZ; tam iade makbuzlar haric). Etsy Stats "revenue" ile birebir
   olmayabilir (tanim farki OZET'te). MUSTERI BILGISI OKUNUR AMA HICBIR DOSYAYA/LOGA YAZILMAZ: yalniz listing_id, adet, tutar, para birimi.
3) Goruntulenme farki: onceki kayittaki views ile fark; aralik_saat (onceki okuma -> bu okuma) BIRIKIM'e yazilir (Etsy views gunde bir
   hesaplanir; 24 saatten farkli aralikta "gunluk" degildir). Onceki yoksa bos.
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
ALAN = ["tarih", "listing_id", "baslik", "grup", "durum", "views", "gunluk_goruntulenme", "aralik_saat", "num_favorers", "satis_gunu",
        "siparis_adet", "gelir", "para_birimi", "okuma_utc"]
BEKLENEN = {"poster": 78, "YD": 78}   # data/pod id listeleri; farkliysa uyari (grup kaymasi)


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
            toplam = int(j.get("count") or 0)
            n = int(j.get("count") or len(r))
            tah = (n // 100) + 2   # kalan ilan sayfalari + en az 1 makbuz sayfasi
            if api.remaining is not None and int(api.remaining) < tah + E.KOTA_SINIRI:
                raise SystemExit(f"DUR: kota {api.remaining} < tahmin {tah} + {E.KOTA_SINIRI}")
        if len(r) < 100:
            if toplam and len(out) != toplam:
                raise SystemExit(f"DUR: okunan ilan {len(out)} != API toplami {toplam} (sayfalama)")
            if len({str(x.get('listing_id')) for x in out}) != len(out):
                raise SystemExit("DUR: tekrarlanan listing_id (sayfalama)")
            return out
        off += 100


def satislar(api, shop, bas_epoch, son_epoch):
    """-> ({listing_id: [adet, gelir]}, para_birimleri, makbuz_sayisi, iptal_sayisi). Musteri alani okunmaz/yazilmaz."""
    s, para, n, iptal, off = defaultdict(lambda: [0, 0.0]), set(), 0, 0, 0
    while True:
        j = api.get(f"/shops/{shop}/receipts", params={"min_created": bas_epoch, "max_created": son_epoch, "was_paid": "true",
                                                        "was_canceled": "false", "limit": 100, "offset": off}) or {}
        r = j.get("results") or []
        for rc in r:
            st = str(rc.get("status") or "").lower()
            if st in ("canceled", "cancelled", "fully refunded") or rc.get("is_canceled"):
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
    gun0 = datetime.combine(simdi.astimezone(IST).date() - timedelta(days=1), datetime.min.time(), IST)   # onceki Istanbul gunu
    satis_gunu = gun0.strftime("%Y-%m-%d")
    poster, yd = ids(KOK.parents[1] / "data/pod/pod78_ids.csv"), ids(KOK.parents[1] / "data/pod/yd78_ids.csv")
    L = ilanlar(api, shop)
    s, para, makbuz, iptal = satislar(api, shop, int(gun0.timestamp()), int((gun0 + timedelta(days=1)).timestamp()) - 1)
    eski = birikim_oku(birikim_yol) if birikim_yol else []
    onceki, onceki_okuma = {}, {}
    for r in sorted((r for r in eski if r.get("tarih", "") < tarih), key=lambda r: r["tarih"]):
        onceki[r["listing_id"]] = r.get("views"); onceki_okuma[r["listing_id"]] = r.get("okuma_utc") or ""
    okuma = simdi.strftime("%Y-%m-%dT%H:%M:%SZ")
    satir = []
    for x in L:
        lid = str(x.get("listing_id"))
        v = x.get("views")
        o = onceki.get(lid)
        fark = (int(v) - int(o)) if (isinstance(v, int) and str(o or "").lstrip("-").isdigit()) else ""
        oo = onceki_okuma.get(lid)
        try:
            aralik = round((simdi - datetime.strptime(oo, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 3600, 1) if oo and fark != "" else ""
        except ValueError:
            aralik = ""
        q, g = s.get(lid, [0, 0.0])
        satir.append(dict(tarih=tarih, listing_id=lid, baslik=x.get("title") or "", grup=grup(lid, x.get("title"), poster, yd),
                          durum=x.get("state") or "", views=v if v is not None else "", gunluk_goruntulenme=fark, aralik_saat=aralik,
                          num_favorers=x.get("num_favorers") if x.get("num_favorers") is not None else "", satis_gunu=satis_gunu,
                          siparis_adet=q, gelir=round(g, 2), para_birimi="/".join(sorted(para)) if q else "", okuma_utc=okuma))
    aktif = {r["listing_id"] for r in satir}
    disari = sorted(set(s) - aktif)   # 24 saatte satilan ama artik aktif olmayan ilan (tukenmis / kapanmis)
    for lid in disari:
        q, g = s[lid]
        satir.append(dict(tarih=tarih, listing_id=lid, baslik="", grup="aktif degil", durum="", views="", gunluk_goruntulenme="",
                          aralik_saat="", num_favorers="", satis_gunu=satis_gunu, siparis_adet=q, gelir=round(g, 2),
                          para_birimi="/".join(sorted(para)), okuma_utc=okuma))
    gun = Path(cikti) / "gunluk"; gun.mkdir(parents=True, exist_ok=True)
    with open(gun / f"{tarih.replace('-', '')}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALAN, lineterminator="\n"); w.writeheader(); w.writerows(satir)
    yeni = [r for r in eski if r.get("tarih") != tarih] + [
        dict(tarih=r["tarih"], listing_id=r["listing_id"], grup=r["grup"], views=r["views"], gunluk_fark=r["gunluk_goruntulenme"],
             aralik_saat=r["aralik_saat"], num_favorers=r["num_favorers"], okuma_utc=r["okuma_utc"]) for r in satir if r["grup"] != "aktif degil"]
    with open(Path(cikti) / "BIRIKIM.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tarih", "listing_id", "grup", "views", "gunluk_fark", "aralik_saat", "num_favorers", "okuma_utc"],
                           lineterminator="\n", extrasaction="ignore", restval="")
        w.writeheader(); w.writerows(sorted(yeni, key=lambda r: (r["tarih"], r["listing_id"])))
    gs = defaultdict(int)
    for r in satir:
        gs[r["grup"]] += 1
    uyari = [f"{g}: {gs.get(g, 0)} (beklenen {n})" for g, n in BEKLENEN.items() if gs.get(g, 0) != n]
    for u in uyari:
        print(f"::warning title=ETSY-GUNLUK::grup sayisi {u}", flush=True)
    oz = dict(tarih=tarih, okuma_utc=okuma, ilan=len(L), grup=dict(gs), grup_uyari=uyari, satis_gunu=satis_gunu, makbuz=makbuz,
              haric_iptal_iade=iptal, siparis_adet=sum(v[0] for v in s.values()), gelir=round(sum(v[1] for v in s.values()), 2),
              gelir_tanimi="price x quantity, odenmis + iptalsiz + tam iadesiz makbuz; kargo/vergi/indirim/kismi iade dusulmez (Etsy Stats revenue ile birebir degil)",
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
