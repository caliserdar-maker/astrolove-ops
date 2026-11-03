#!/usr/bin/env python3
"""etsy_gunluk testleri (sahte Etsy; ag yok). Kullanim: python3 scripts/etsy/test_etsy_gunluk.py -> SONUC n/n PASS."""
import csv
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_gunluk as G  # noqa: E402

sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"))


POSTER, YD = "4570143815", "4595350971"


class Sahte:
    def __init__(self, n=150, kalan=500):
        self.calls, self.remaining, self.yol = 0, kalan, []
        self.L = [dict(listing_id=POSTER, title="Cancer and Libra Personalized Zodiac Couple Wall Art", state="active", views=100, num_favorers=3),
                  dict(listing_id=YD, title="Cancer and Libra 1st Anniversary Gift", state="active", views=50, num_favorers=1),
                  dict(listing_id="7", title="Cancer and Libra Zodiac Couple Mug", state="active", views=9, num_favorers=0),
                  dict(listing_id="8", title="Leo Zodiac Mug Personalized", state="active", views=4, num_favorers=0)]
        self.L += [dict(listing_id=str(1000 + i), title="Other", state="active", views=i, num_favorers=0) for i in range(n - 4)]
        self.R = [{"receipt_id": 1, "status": "Paid", "name": "GIZLI MUSTERI", "buyer_email": "x@y", "first_line": "Adres 1",
                   "message_from_buyer": "gizli mesaj",
                   "transactions": [{"listing_id": int(POSTER), "quantity": 2, "price": {"amount": 2500, "divisor": 100, "currency_code": "USD"}}]},
                  {"receipt_id": 2, "status": "Canceled", "name": "IPTAL", "transactions": [{"listing_id": 7, "quantity": 1,
                   "price": {"amount": 900, "divisor": 100, "currency_code": "USD"}}]},
                  {"receipt_id": 3, "status": "Completed", "transactions": [{"listing_id": 999, "quantity": 1,
                   "price": {"amount": 1000, "divisor": 100, "currency_code": "USD"}}]}]

    def _call(self, method, path, params=None, **kw):
        self.calls += 1; self.yol.append((method, path, dict(params or {})))
        if path.endswith("/listings/active"):
            o = params["offset"]; return {"count": len(self.L), "results": self.L[o:o + params["limit"]]}
        if path.endswith("/receipts"):
            assert params.get("was_paid") == "true" and params.get("was_canceled") == "false"
            return {"count": len(self.R), "results": self.R if params["offset"] == 0 else []}
        raise AssertionError(path)

    def get(self, path, params=None, ok404=False):
        return self._call("GET", path, params)


SIMDI = datetime(2026, 11, 4, 3, 15, tzinfo=timezone.utc)
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    a = Sahte(); oz = G.calis(a, "1", d / "o1", None, SIMDI)
    rows = list(csv.DictReader(open(d / "o1/gunluk/20261104.csv")))
    by = {r["listing_id"]: r for r in rows}
    k("tum aktif ilanlar (150) + aktif olmayan satis satiri", len(rows) == 151 and oz["ilan"] == 150, len(rows))
    k("istek: 2 ilan sayfasi + 1 makbuz = 3, hepsi GET", a.calls == 3 and all(m == "GET" for m, _, _ in a.yol), a.yol)
    k("gruplar: poster / YD / kupa / sade kupa / diger", (by[POSTER]["grup"], by[YD]["grup"], by["7"]["grup"], by["8"]["grup"], by["1000"]["grup"])
      == ("poster", "YD", "kupa", "sade kupa", "diger"))
    k("onceki gun satis: adet 2, gelir 50.0, USD", by[POSTER]["siparis_adet"] == "2" and by[POSTER]["gelir"] == "50.0" and by[POSTER]["para_birimi"] == "USD")
    k("iptal makbuz sayilmaz", by["7"]["siparis_adet"] == "0" and oz["haric_iptal_iade"] == 1 and oz["makbuz"] == 2)
    k("aktif olmayan satilan ilan ayri satir", by["999"]["grup"] == "aktif degil" and by["999"]["siparis_adet"] == "1")
    tum = "".join(p.read_text() for p in (d / "o1").rglob("*") if p.is_file())
    k("musteri adi / e-posta / adres / mesaj hicbir dosyada yok", not any(x in tum for x in ("GIZLI", "x@y", "Adres 1", "gizli mesaj", "IPTAL")))
    g0 = int(datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc).timestamp())   # 3 Kas 00:00 Istanbul
    k("makbuz araligi: onceki Istanbul gunu (3 Kas 00:00-23:59:59), odenmis + iptalsiz", a.yol[-1][2]["min_created"] == g0
      and a.yol[-1][2]["max_created"] == g0 + 86399 and a.yol[-1][2]["was_paid"] == "true" and a.yol[-1][2]["was_canceled"] == "false"
      and by[POSTER]["satis_gunu"] == "2026-11-03", a.yol[-1][2])
    k("ilk gun: gunluk fark bos", by[POSTER]["gunluk_goruntulenme"] == "" and oz["onceki_gun_var"] is False)
    # 2. gun: birikimden fark
    b = Sahte(); b.L[0]["views"] = 130
    oz2 = G.calis(b, "1", d / "o2", d / "o1/BIRIKIM.csv", datetime(2026, 11, 5, 3, 15, tzinfo=timezone.utc))
    by2 = {r["listing_id"]: r for r in csv.DictReader(open(d / "o2/gunluk/20261105.csv"))}
    k("2. gun: gunluk fark = 130 - 100 = 30, aralik 24 saat", by2[POSTER]["gunluk_goruntulenme"] == "30" and by2[YD]["gunluk_goruntulenme"] == "0"
      and by2[POSTER]["aralik_saat"] == "24.0", by2[POSTER])
    bir = list(csv.DictReader(open(d / "o2/BIRIKIM.csv")))
    k("BIRIKIM: 2 gun x 150 ilan", len(bir) == 300 and {r["tarih"] for r in bir} == {"2026-11-04", "2026-11-05"}, len(bir))
    # ayni gun yeniden kosu: o gun yenilenir, cift kayit yok
    c = Sahte(); c.L[0]["views"] = 140
    G.calis(c, "1", d / "o3", d / "o2/BIRIKIM.csv", datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc))
    bir3 = list(csv.DictReader(open(d / "o3/BIRIKIM.csv")))
    k("ayni gun ikinci kosu: cift kayit yok, fark 4 Kas'a gore (40)", len(bir3) == 300 and
      [r["gunluk_fark"] for r in bir3 if r["tarih"] == "2026-11-05" and r["listing_id"] == POSTER] == ["40"])
    s_ = Sahte(); s_.L = s_.L[:120]; s_.L += s_.L[100:101]   # sayfalama tekrari: 121 kayit, count 121, tekrarlanan id
    try:
        G.calis(s_, "1", d / "o5", None, SIMDI); dur = False
    except SystemExit as e:
        dur = "listing_id" in str(e)
    k("sayfalama: tekrarlanan listing_id -> DUR", dur)
    try:
        G.calis(Sahte(kalan=11), "1", d / "o4", None, SIMDI); dur = False
    except SystemExit as e:
        dur = "kota" in str(e)
    k("kota kapisi: kalan 11 < 3 + 10 -> DUR", dur)
    try:
        G.SaltOku.__new__(G.SaltOku)._call("POST", "/x"); yaz = False
    except SystemExit:
        yaz = True
    k("SaltOku: yazma cagrisi kosuyu durdurur", yaz)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
