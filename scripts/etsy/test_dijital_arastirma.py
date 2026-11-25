#!/usr/bin/env python3
"""dijital_arastirma (derin toplayici, terim modu) sahte testi. AG KAPALI (emsal scripts/sosyal/test_metricool_yedek.py:19-25):
socket ve urllib bastan engellenir; Etsy istekleri etsy_common.requests.request uzerinden sahte Etsy'ye gider.
Bilinen PASS: tam akis (ornek -> yorum -> ozet), ilan kimligiyle tekillestirme (iki terimde ayni ilan tek satir, yorumlari bir kez
okunur), "yeni" grubu original_creation_timestamp ile, en cok yorumlu 5 ilanin tum yorumlari (sayfa siniri -> kesik), dusuk yildiz
sayimi, fiyat yalniz USD, ozet sutunlarinda kanitli satis / ilk10 / hedef yok, istek sayaci + zaman damgasi, kota durdurma ve
her noktada kesinti + devam (ayni sonuc), yol verme, sure dolmasi.
Bilinen FAIL: GET disi istek (SaltOkur), baska terim kumesinin durumu, 8'den fazla terim, listede olmayan terim, loga kimlik /
baslik / terim, mutasyonlar (uygun() bozuk, yeni_mi() kaldirildi, yorum onbellegi terim anahtarli)."""
import contextlib
import csv
import io
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import dijital_arastirma as D  # noqa: E402

E.requests.post = E.requests.get = _ag_yok
E.time.sleep = lambda *_: None
D.YOL_VER_SN = 0
SIMDI = 1790000000
GUN = 86400
TERIMLER = ["planner terim", "clipart terim"]

# ------------------------------------------------------------------ sahte Etsy
ILAN = {}
SIRA = {}          # terim -> ilan kimlikleri (score sirasi)
for ti, t in enumerate(TERIMLER):
    ids = []
    for k in range(200):
        lid = 900000000 + ti * 100000 + k
        ILAN[lid] = {"listing_id": lid, "shop_id": 70000000 + (k % 11), "title": f"Ilan {k}", "url": f"https://etsy/{lid}",
                     "listing_type": "download" if k % 3 != 2 else "physical", "is_personalizable": (k % 7 == 3),
                     "taxonomy_id": 5, "num_favorers": k, "views": 0,
                     "price": {"amount": 100 + k * 10, "divisor": 100, "currency_code": "EUR" if k % 4 == 0 else "USD"},
                     "tags": ["a"], "created_timestamp": SIMDI - k * 1000 - ti,
                     "original_creation_timestamp": SIMDI - (800 if k % 5 == 0 else k) * GUN}
        ids.append(lid)
    SIRA[t] = ids
ORTAK = SIRA["planner terim"][1]          # iki terimde de ilk sirada (tekillestirme + yorum onbellegi)
SIRA["clipart terim"].insert(0, ORTAK)
COK = SIRA["planner terim"][4]            # 1.500 yorum -> sayfa siniri (10 sayfa) -> kesik


def yorum_n(lid):
    return 1500 if lid == COK else lid % 230


def yorumlar(lid):
    return [{"shop_id": ILAN[lid]["shop_id"], "listing_id": lid, "transaction_id": 5550000000 + i, "buyer_user_id": 4440000000 + i,
             "rating": (2 if i % 6 == 0 else (4 if i % 6 == 1 else 5)), "review": f"love it great quality print {i}" if i % 3 else "",
             "language": "en", "image_url_fullxfull": "x", "created_timestamp": SIMDI - i * GUN * 3,
             "create_timestamp": SIMDI - i * GUN * 3} for i in range(yorum_n(lid))]


class Yanit:
    def __init__(self, kod, j, kalan):
        self.status_code = kod
        self._j = j
        self.headers = {"x-remaining-today": str(kalan), "x-limit-per-day": "5000"}
        self.text = json.dumps(j)[:300]

    def json(self):
        return self._j


class Sahte:
    def __init__(self, kalan=4900):
        self.kalan = kalan
        self.istek = 0
        self.ping_n = 0
        self.yazma = 0
        self.yorum_istek = {}
        self.hata_grup = {}       # (terim, sort_on) -> kalan hata sayisi (503)
        self.batch_hata = False
        self.shop_hata = False
        self.yorum_hata = {}      # ilan -> kalan hata sayisi

    def ping(self, path):
        self.ping_n += 1
        return {"x-limit-per-day": "5000", "x-remaining-today": str(self.kalan), "x-limit-per-second": "5", "http": 200}

    def __call__(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):  # noqa: A002
        assert "x-api-key" in (headers or {}) and "Authorization" not in headers, "OAuth basligi"
        if method != "GET":
            self.yazma += 1
        self.istek += 1
        self.kalan -= 1
        p = urlparse(url).path.replace("/v3/application", "")
        params = params or {}
        if self.kalan < 0:
            return Yanit(429, {"error": "kota"}, 0)
        if p == "/listings/active":
            assert "taxonomy_id" not in params, "terim modunda taksonomi suzgeci yok"
            k = (params["keywords"], params.get("sort_on"))
            if self.hata_grup.get(k, 0) > 0:
                self.hata_grup[k] -= 1
                return Yanit(503, {"error": "x"}, self.kalan)
            L = [ILAN[i] for i in SIRA[params["keywords"]]]
            if params.get("sort_on") == "created":
                L = sorted(L, key=lambda x: -x["created_timestamp"])
            off, lim = int(params.get("offset", 0)), int(params.get("limit", 25))
            return Yanit(200, {"count": len(L), "results": L[off:off + lim]}, self.kalan)
        if p.startswith("/shops/"):
            if self.shop_hata:
                return Yanit(503, {"error": "x"}, self.kalan)
            return Yanit(200, {"shop_id": int(p.split("/")[2]), "shop_name": "S", "transaction_sold_count": 50}, self.kalan)
        if p == "/listings/batch":
            if self.batch_hata:
                return Yanit(503, {"error": "x"}, self.kalan)
            ids = [int(x) for x in params["listing_ids"].split(",")]
            assert len(ids) <= 100
            res = [dict(ILAN[i], shop={"shop_id": ILAN[i]["shop_id"], "shop_name": "S", "transaction_sold_count": 50,
                                       "create_date": 1600000000, "url": "u"}) for i in ids]
            return Yanit(200, {"count": len(res), "results": res}, self.kalan)
        if p.endswith("/reviews"):
            lid = int(p.split("/")[2])
            off, lim = int(params.get("offset", 0)), int(params.get("limit", 25))
            self.yorum_istek[(lid, off)] = self.yorum_istek.get((lid, off), 0) + 1
            if self.yorum_hata.get(lid, 0) > 0:
                self.yorum_hata[lid] -= 1
                return Yanit(404, {"error": "x"}, self.kalan)
            y = yorumlar(lid)
            return Yanit(200, {"count": len(y), "results": y[off:off + lim]}, self.kalan)
        return Yanit(404, {"error": "yok"}, self.kalan)


def api_kur(s):
    E.requests.request = s
    api = D.SaltOkur(E.APIKeyStore("anahtar-sahte-12", "sir-sahte-12345"))
    api.pace = 0
    return api


def kos(s, d, dk=60, yv=None, terimler=TERIMLER):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        kod = D.calis(d, dk, api_kur(s), terimler, yv, s.ping, simdi=SIMDI)
    return kod, log.getvalue()


def oku(d, ad):
    with open(Path(d) / ad, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


HATA = []


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def durum(d):
    return json.loads((Path(d) / "durum.json").read_text())


def imza(d):
    return (sorted((r["terim"], r["grup"], r["sira"], r["listing_id"]) for r in oku(d, "ILAN_TERIM.csv")),
            len(oku(d, "YORUMLAR.csv")), [{k: v for k, v in r.items()} for r in oku(d, "TERIM_OZET.csv")])


def main():
    tmp = Path(tempfile.mkdtemp(prefix="dij_"))
    try:
        # 1) tam akis
        s = Sahte()
        d1 = tmp / "a"
        kod, lg = kos(s, d1)
        st = durum(d1)
        kontrol("tam akis kod 0", kod == 0)
        kontrol("tam akis bitti", st["asama"] == "bitti")
        kontrol("yazma yok", s.yazma == 0)
        il = oku(d1, "ILANLAR.csv")
        bag = oku(d1, "ILAN_TERIM.csv")
        kontrol("ILANLAR ilan kimligiyle tekil", len(il) == len({r["listing_id"] for r in il}))
        kontrol("ortak ilan iki terimde bagli, tek satir", sum(1 for r in il if int(r["listing_id"]) == ORTAK) == 1
                and {r["terim"] for r in bag if int(r["listing_id"]) == ORTAK} == set(TERIMLER))
        kontrol("ILANLAR'da tur_id / grup yok (bag ayri dosyada)", "tur_id" not in il[0] and "grup" not in il[0])
        kontrol("orneklem yalniz download + kisisellestirmesiz", all(ILAN[int(r["listing_id"])]["listing_type"] == "download"
                                                                    and not ILAN[int(r["listing_id"])]["is_personalizable"] for r in il))
        kontrol("grup basina 15", all(sum(1 for r in bag if r["terim"] == t and r["grup"] == g) == 15
                                      for t in TERIMLER for g in ("relevans", "yeni")))
        yeni = [ILAN[int(r["listing_id"])] for r in bag if r["grup"] == "yeni"]
        kontrol("yeni grup: original_creation son 365 gun", all(L["original_creation_timestamp"] >= SIMDI - 365 * GUN for L in yeni))
        kontrol("ayni terimde relevans ve yeni kesismez", all(
            not ({r["listing_id"] for r in bag if r["terim"] == t and r["grup"] == "relevans"}
                 & {r["listing_id"] for r in bag if r["terim"] == t and r["grup"] == "yeni"}) for t in TERIMLER))
        kontrol("yorum onbellegi: her (ilan, sayfa) bir kez okundu", all(v == 1 for v in s.yorum_istek.values()))
        kontrol("ortak ilanin ilk sayfasi bir kez", s.yorum_istek.get((ORTAK, 0)) == 1)
        y = oku(d1, "YORUMLAR.csv")
        kontrol("YORUMLAR'da tur_id yok", "tur_id" not in y[0])
        ham = (d1 / "YORUMLAR.csv").read_text(encoding="utf-8")
        kontrol("yorumcu kimligi yok", "buyer_user_id" not in ham and "444000" not in ham and "555000" not in ham)
        tam = st["yorum_tam"]
        kontrol("terim basina 5 tam okunan ilan", all(len(tam[t]) == 5 for t in TERIMLER))
        kontrol("en cok yorumlu ilan secimde", str(COK) in tam["planner terim"])
        yd = st["yorum"]
        kontrol("1.500 yorumlu ilan 10 sayfada kesik", yd[str(COK)].get("kesik") is True
                and sum(1 for r in y if int(r["listing_id"]) == COK) == 1000)
        tam_ok = all(sum(1 for r in y if r["listing_id"] == lid) == min(yorum_n(int(lid)), 1000) for t in TERIMLER for lid in tam[t])
        kontrol("secilen ilanlarin tum yorumlari (sinira kadar)", tam_ok)
        sec_disi = [lid for lid in {r["listing_id"] for r in il} if not any(lid in tam[t] for t in TERIMLER)]
        kontrol("secim disi ilanlar yalniz ilk sayfa", all(sum(1 for r in y if r["listing_id"] == lid) == min(yorum_n(int(lid)), 100)
                                                          for lid in sec_disi))
        oz = oku(d1, "TERIM_OZET.csv")
        kontrol("ozet 2 terim x 3 grup, girdi sirasinda", [(o["terim"], o["grup"]) for o in oz]
                == [(t, g) for t in TERIMLER for g in ("hepsi", "relevans", "yeni")])
        kontrol("ozet: kanitli satis / ilk10 / hedef sutunu yok", not any(re.search("kanitli|ilk10|hedef", k) for k in oz[0]))
        kontrol("ozet: son_12ay_yorum_sayisi sutunu var", "son_12ay_yorum_sayisi" in oz[0])
        h = {o["terim"]: o for o in oz if o["grup"] == "hepsi"}
        for t in TERIMLER:
            lids = {r["listing_id"] for r in bag if r["terim"] == t}
            neg = sum(1 for r in y if r["listing_id"] in lids and int(r["rating"]) <= 3)
            kontrol(f"ozet dusuk yildiz sayimi ({t})", int(h[t]["dusuk_yildiz_n"]) == neg)
            usd = [ILAN[int(x)] for x in lids if ILAN[int(x)]["price"]["currency_code"] == "USD"]
            kontrol(f"ozet fiyat yalniz USD ({t})", int(h[t]["fiyat_usd_n"]) == len(usd) and int(h[t]["fiyat_usd_disi_n"]) == len(lids) - len(usd)
                    and abs(float(h[t]["fiyat_medyan_usd"]) - D.yuzdelik([L["price"]["amount"] / 100 for L in usd], .5)) < 1e-9)
            y12 = sum(1 for r in y if r["listing_id"] in lids and int(r["created_timestamp"]) >= SIMDI - 365 * GUN)
            kontrol(f"ozet son 12 ay yorum ({t})", int(h[t]["son_12ay_yorum_sayisi"]) == y12)
        kontrol("ozet: kesik ilan sayilir", int(h["planner terim"]["yorum_kesik_ilan"]) == 1)
        import statistics
        for t in TERIMLER:
            lids = {r["listing_id"] for r in bag if r["terim"] == t}
            yas = statistics.median((SIMDI - ILAN[int(x)]["original_creation_timestamp"]) / D.AY_SN for x in lids)
            kontrol(f"ozet ilan yasi original_creation ile ({t})", float(h[t]["ilan_yasi_medyan_ay"]) == round(yas, 1))
        kontrol("istek sayaci = sahte istek + ping", st["istek_toplam"] == s.istek + s.ping_n and s.ping_n == 1)
        kontrol("durum zaman damgasi + kosu kaydi", bool(st.get("son_guncelleme_utc")) and st["kosular"][-1].get("bit_utc")
                and st["kosular"][-1]["istek"] == s.istek + 1)
        for f in ("MAGAZALAR.csv", "EKSIK_ALAN.csv", "YORUMLAR_ETIKETLI.csv"):
            kontrol(f"dosya {f}", (d1 / f).exists())
        kontrol("magaza tablosu = tekil magaza", len(oku(d1, "MAGAZALAR.csv")) == len({r["shop_id"] for r in il}))
        kontrol("log: terim / baslik / yorum yok", not any(t in lg for t in TERIMLER) and "Ilan " not in lg and "love it" not in lg)
        buf2 = io.StringIO()
        D.KimlikSuz(buf2).write("ilan 900111001 hata")
        kontrol("bilinen FAIL: suzgec kimligi yakalar", "<id>" in buf2.getvalue())
        # 2) kota durdurma + devam
        s2 = Sahte(kalan=1000 + 40)       # %20 esigi 1000
        d2 = tmp / "b"
        kod2, _ = kos(s2, d2)
        kontrol("kota DUR kod 3", kod2 == 3 and durum(d2)["asama"] != "bitti")
        s2.kalan = 4900
        for _ in range(5):
            kos(s2, d2)
            if durum(d2)["asama"] == "bitti":
                break
        kontrol("kota sonrasi devam: ayni sonuc", durum(d2)["asama"] == "bitti" and imza(d2) == imza(d1))
        kontrol("kota sonrasi: istek sayaci toplam", durum(d2)["istek_toplam"] == s2.istek + s2.ping_n)
        # 2b) her noktada kesinti
        for k_ in (3, 7, 29):
            s5 = Sahte()
            d5 = tmp / f"k{k_}"
            for _ in range(3000):
                s5.kalan = 1000 + k_
                kos(s5, d5)
                if durum(d5)["asama"] == "bitti":
                    break
            kontrol(f"kesinti her {k_} istekte: bitti + ayni sonuc", durum(d5)["asama"] == "bitti" and imza(d5) == imza(d1))
        # 2c) okuma hatasi "bitti" sayilmaz: grup ilk sayfasi 503 (3 deneme x 2 = 6 yanit), batch + shops 503
        s6 = Sahte()
        s6.hata_grup = {("planner terim", "score"): 6}
        s6.batch_hata = s6.shop_hata = True
        d6 = tmp / "hg"
        kod6a, _ = kos(s6, d6)
        st6 = durum(d6)
        kontrol("bilinen FAIL: okunamayan grup + magaza -> kod 1, asama ornek", kod6a == 1 and st6["asama"] == "ornek"
                and "planner terim\trelevans" not in st6["ornek_bitti"])
        kontrol("okunamayan magaza bos satir olarak yazilmaz", len(oku(d6, "MAGAZALAR.csv")) == 0)
        s6.batch_hata = s6.shop_hata = False
        for _ in range(3):
            kos(s6, d6)
            if durum(d6)["asama"] == "bitti":
                break
        kontrol("hata sonrasi devam: ayni sonuc", durum(d6)["asama"] == "bitti" and imza(d6) == imza(d1)
                and all(r["transaction_sold_count"] for r in oku(d6, "MAGAZALAR.csv")))
        # kalici grup hatasi: 2 kosuda okunamazsa kapanir, ozette sayilir
        s6b = Sahte()
        s6b.hata_grup = {("planner terim", "score"): 10 ** 6}
        d6b = tmp / "hg2"
        kos(s6b, d6b)
        kos(s6b, d6b)
        for _ in range(3):
            kos(s6b, d6b)
            if durum(d6b)["asama"] == "bitti":
                break
        hb = {o["terim"]: o for o in oku(d6b, "TERIM_OZET.csv") if o["grup"] == "hepsi"}
        kontrol("kalici grup hatasi kapanir, ozette grup_okuma_hatasi 1", durum(d6b)["asama"] == "bitti"
                and hb["planner terim"]["grup_okuma_hatasi"] == "1" and hb["clipart terim"]["grup_okuma_hatasi"] == "0")
        # yorum ilk sayfasi bir kez 404: ayni kosuda yeniden denenir, secim etkilenmez
        s6c = Sahte()
        s6c.yorum_hata = {COK: 1}
        d6c = tmp / "hg3"
        kos(s6c, d6c)
        kontrol("yorum ilk sayfa hatasi ayni kosuda yeniden denenir", durum(d6c)["asama"] == "bitti" and imza(d6c) == imza(d1)
                and str(COK) in durum(d6c)["yorum_tam"]["planner terim"])
        # 3) yol verme
        s3 = Sahte()
        d3 = tmp / "c"
        n = {"i": 0}

        def yv():
            n["i"] += 1
            return n["i"] == 3
        kod3, _ = kos(s3, d3, yv=yv)
        kontrol("yol ver kod 4", kod3 == 4)
        kos(s3, d3)
        kontrol("yol ver sonrasi ayni", durum(d3)["asama"] == "bitti" and imza(d3) == imza(d1))
        # 4) sure doldu
        d4 = tmp / "d"
        kod4, _ = kos(Sahte(), d4, dk=0)
        kontrol("sure 0 kod 0 bitmedi", kod4 == 0 and durum(d4)["asama"] != "bitti")
        # 5) bilinen FAIL: baska terim kumesi, 8+ terim, listede olmayan terim
        kod5, _ = kos(Sahte(), d1, terimler=["planner terim"])
        kontrol("bilinen FAIL: baska terim kumesinin durumu kod 1", kod5 == 1)
        kod6, _ = kos(Sahte(), tmp / "e", terimler=[f"t{i}" for i in range(9)])
        kontrol("bilinen FAIL: 9 terim kod 1", kod6 == 1)
        try:
            D.secim_coz(TERIMLER, "planner terim;yok", bos_hepsi=False)
            kontrol("bilinen FAIL: listede olmayan terim", False)
        except SystemExit:
            kontrol("bilinen FAIL: listede olmayan terim", True)
        try:
            D.secim_coz(TERIMLER, "", bos_hepsi=False)
            kontrol("bilinen FAIL: bos terim girdisi", False)
        except SystemExit:
            kontrol("bilinen FAIL: bos terim girdisi", True)
        # 6) GET disi yasak
        try:
            api_kur(Sahte()).patch("/shops/1/listings/2", {"title": "x"})
            kontrol("bilinen FAIL: PATCH yasak", False)
        except SystemExit as e:
            kontrol("bilinen FAIL: PATCH yasak", "yasak" in str(e))
        # 7) gercek main(): ham stdout'ta kimlik / metin / terim yok
        s7 = Sahte()
        d7 = tmp / "m"
        buf = io.StringIO()
        liste = tmp / "liste.txt"
        liste.write_text("\n".join(TERIMLER) + "\n", encoding="utf-8")
        eski_ping, eski = D.ham_ping, (sys.argv, sys.stdout, sys.stderr)
        D.ham_ping = lambda st: s7.ping
        E.requests.request = s7
        sys.argv = ["x", "--out", str(d7), "--dk", "60", "--liste", str(liste), "--terimler", "; ".join(TERIMLER)]
        os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"] = "anahtar-sahte-12", "sir-sahte-12345"
        os.environ.pop("GH_TOKEN", None)
        sys.stdout = sys.stderr = buf
        try:
            km = D.main()
            print("ilan x:900111001 ve 942900001")
        finally:
            (sys.argv, sys.stdout, sys.stderr), D.ham_ping = eski, eski_ping
        ham_log = buf.getvalue()
        kontrol("main kod 0 + bitti", km == 0 and durum(d7)["asama"] == "bitti")
        kontrol("main ham log: 6+ haneli kimlik yok", not re.search(r"\d{6,}", ham_log))
        kontrol("main ham log: baslik / yorum / terim / url yok", "Ilan " not in ham_log and "love it" not in ham_log
                and "etsy/" not in ham_log and not any(t in ham_log for t in TERIMLER))
        # 8) mutasyonlar
        eski_u = D.uygun
        D.uygun = lambda L: L.get("listing_type") in ("download", "both", "physical")
        kos(Sahte(), tmp / "x1")
        il6 = oku(tmp / "x1", "ILANLAR.csv")
        kontrol("mutasyon uygun() yakalanir", not all(ILAN[int(r["listing_id"])]["listing_type"] == "download"
                                                     and not ILAN[int(r["listing_id"])]["is_personalizable"] for r in il6))
        D.uygun = eski_u
        eski_y = D.yeni_mi
        D.yeni_mi = lambda L, simdi: True
        kos(Sahte(), tmp / "x2")
        yeni2 = [ILAN[int(r["listing_id"])] for r in oku(tmp / "x2", "ILAN_TERIM.csv") if r["grup"] == "yeni"]
        kontrol("mutasyon yeni_mi() kaldirildi yakalanir", not all(L["original_creation_timestamp"] >= SIMDI - 365 * GUN for L in yeni2))
        D.yeni_mi = eski_y
        eski_sa = D.sayfa_al

        def terim_anahtarli(dp, ok, lid, yd):   # eski kusur (tur:ilan anahtari): ayni ilan ikinci terimde bastan okunur
            if lid == str(ORTAK) and yd.get(lid) is None:
                eski_sa(dp, ok, lid, {})
            return eski_sa(dp, ok, lid, yd)
        D.sayfa_al = terim_anahtarli
        s8 = Sahte()
        try:
            kos(s8, tmp / "x3")
        finally:
            D.sayfa_al = eski_sa
        kontrol("mutasyon yorum onbellegi bozuk yakalanir", s8.yorum_istek.get((ORTAK, 0)) == 2
                and not all(v == 1 for v in s8.yorum_istek.values()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"SONUC: {'FAIL ' + str(len(HATA)) if HATA else 'PASS'}")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
