#!/usr/bin/env python3
"""terim_tarama sahte testi. AG KAPALI (emsal scripts/sosyal/test_metricool_yedek.py:19-25): socket ve urllib bastan engellenir;
Etsy istekleri etsy_common.requests.request uzerinden sahte Etsy'ye gider.
Bilinen PASS: tam akis (3 terim + ek sayfa + tekillestirme + magaza onbellegi), olcut degerleri elle hesaplanan beklenenle,
kota kapisinda temiz durma + kaldigi terimden devam (ayni sonuc), terim ortasinda 429 (terim yazilmaz) + devam, yol verme,
sure dolmasi, --yeniden, istek sayaci = sahte Etsy'nin saydigi istek, log'da terim / baslik / kimlik yok.
Bilinen FAIL: kota baslangicta < 1.200 (terim istegi yok), listede olmayan terim, PATCH yasak, ardisik 3 terim hatasi (kod 1),
mutasyonlar (DL_MIN 0 -> ek sayfa yok; GENC_GUN buyuk -> genc sayisi degisir; tekillestirme bozuk -> ilan sayisi degisir)."""
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
import terim_tarama as T  # noqa: E402

E.requests.post = E.requests.get = _ag_yok
E.time.sleep = lambda *_: None
D.YOL_VER_SN = 0
SIMDI = 1790000000
GUN = 86400

# ------------------------------------------------------------------ sahte veri
# magazalar: (yas gun, toplam satis)
MAGAZA = {70000001: (200, 150), 70000002: (100, 40), 70000003: (1000, 500), 70000004: (900, 10), 70000005: (30, 300),
          70000006: (2000, 0), 70000007: (50, 120), 70000008: (400, 5), 70000009: (None, 20)}
ILAN = {}
TERIM_ILAN = {}


def ilan(lid, sid, tip, para="USD", fiyat=500, fav=3, yas_gun=60):
    ILAN[lid] = {"listing_id": lid, "shop_id": sid, "title": f"Baslik {lid}", "url": f"https://etsy/{lid}", "listing_type": tip,
                 "is_personalizable": False, "taxonomy_id": 1, "num_favorers": fav,
                 "price": {"amount": fiyat, "divisor": 100, "currency_code": para},
                 "original_creation_timestamp": SIMDI - yas_gun * GUN, "created_timestamp": SIMDI - 5 * GUN}
    return lid


# alfa: 100 sonuc, 60 download (A 30, B 15, C 5, D 5, E 3, F 2); 15'i EUR; ek sayfa YOK
_alfa, lid = [], 900100000
for sid, n in ((70000001, 30), (70000002, 15), (70000003, 5), (70000004, 5), (70000005, 3), (70000006, 2)):
    for k in range(n):
        lid += 1
        _alfa.append(ilan(lid, sid, "download", "EUR" if len(_alfa) % 4 == 0 else "USD", 400 + len(_alfa), len(_alfa), 30 + len(_alfa)))
lid += 1
_alfa.append(ilan(lid, 70000009, "download", "USD", 1000, 1000, 30))     # I: kurulus tarihi yok (yas bilinmiyor)
lid += 1
_alfa.append(ilan(lid, 70000009, "download", "", 0, 2, 40))              # fiyati okunamayan ilan (fiyat_yok)
ILAN[lid]["price"] = {}
for k in range(38):
    lid += 1
    _alfa.append(ilan(lid, 70000008, "physical", fav=7, yas_gun=5000))
TERIM_ILAN["alfa terim"] = _alfa
ALFA_DL = [ILAN[i] for i in _alfa if ILAN[i]["listing_type"] == "download"]
# beta: 3 sayfa x 100; sayfa basina 10/10/15 download (sayfa 2'de sayfa 1'den bir tekrar); 4. sayfa var ama okunmaz (EK_SAYFA 2)
_beta, lid = [], 900200000
for sayfa, ndl in ((1, 10), (2, 10), (3, 15), (4, 50)):
    for k in range(100):
        lid += 1
        tip = "download" if k < ndl else "physical"
        _beta.append(ilan(lid, 70000007 if k % 2 else 70000001, tip))
TEKRAR = _beta[0]
_beta[100] = TEKRAR          # sayfa 2'nin ilk ilani = sayfa 1'in ilk ilani (score sirasi kayar)
TERIM_ILAN["beta terim"] = _beta
# gama: 40 sonuc (dolu sayfa degil), 5 download -> ek sayfa YOK. Ilk download'in magazasi (H) yeni; temsilci ilan batch'te
# donmez (ilan arada kalkti) -> H bilinmeyen; diger 4 download E (alfa'da okundu, onbellek)
_gama, lid = [], 900300000
for k in range(40):
    lid += 1
    _gama.append(ilan(lid, 70000008 if k == 0 else 70000005, "download" if k < 5 else "both"))
TERIM_ILAN["gama terim"] = _gama
SILINMIS = _gama[0]
TERIMLER = ["alfa terim", "beta terim", "gama terim"]


class Yanit:
    def __init__(self, kod, j, kalan, ek=None):
        self.status_code = kod
        self._j = j
        self.headers = {"x-remaining-today": str(kalan), "x-limit-per-day": "5000"} | (ek or {})
        self.text = json.dumps(j)[:300]

    def json(self):
        return self._j


class Sahte:
    def __init__(self, kalan=5000):
        self.kalan = kalan
        self.istek = 0
        self.yazma = 0
        self.batch_ids = []
        self.terim_istek = {}
        self.hata_terim = set()
        self.k429 = None          # bu istek sirasinda 429 (uzun retry-after)
        self.basliksiz = False    # True: x-remaining-today basligi yok

    def __call__(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):  # noqa: A002
        assert "x-api-key" in (headers or {}) and "Authorization" not in headers, "OAuth basligi"
        if method != "GET":
            self.yazma += 1
        self.istek += 1
        self.kalan -= 1
        p = urlparse(url).path.replace("/v3/application", "")
        params = params or {}
        if self.k429 is not None and self.istek == self.k429:
            return Yanit(429, {"error": "kota"}, self.kalan, {"retry-after": "3600"})
        if p == "/openapi-ping":
            y = Yanit(200, {"application_id": 1}, self.kalan)
            if self.basliksiz:
                y.headers.pop("x-remaining-today")
            return y
        if p == "/listings/active":
            t = params.get("keywords")
            self.terim_istek[t] = self.terim_istek.get(t, 0) + 1
            if t in self.hata_terim:
                return Yanit(500, {"error": "x"}, self.kalan)
            assert params.get("sort_on") == "score" and int(params.get("limit")) == 100
            off = int(params.get("offset", 0))
            L = [ILAN[i] for i in TERIM_ILAN.get(t, [])]
            return Yanit(200, {"count": len(L), "results": L[off:off + 100]}, self.kalan)
        if p == "/listings/batch":
            assert params.get("includes") == "Shop"
            ids = [int(x) for x in params["listing_ids"].split(",")]
            assert len(ids) <= 100
            self.batch_ids += ids
            res = []
            for i in ids:
                if i == SILINMIS:
                    continue
                sid = ILAN[i]["shop_id"]
                yas, sat = MAGAZA[sid]
                sh = {"shop_id": sid, "shop_name": f"Magaza{sid}", "transaction_sold_count": sat, "review_count": 1, "url": "u"}
                if yas is not None:
                    sh["create_date"] = SIMDI - yas * GUN
                res.append(dict(ILAN[i], shop=sh))
            return Yanit(200, {"count": len(res), "results": res}, self.kalan)
        return Yanit(404, {"error": "yok"}, self.kalan)


def api_kur(s):
    E.requests.request = s
    api = D.SaltOkur(E.APIKeyStore("anahtar-sahte-12", "sir-sahte-12345"))
    api.pace = 0
    return api


def kos(s, d, terimler=TERIMLER, dk=60, yv=None, yeniden=False, kota_alt=T.KOTA_ALT, simdi=SIMDI):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        kod = T.calis(d, dk, api_kur(s), terimler, yeniden, yv, simdi_fn=lambda: simdi, kota_alt=kota_alt)
    return kod, log.getvalue()


def oku(d, ad):
    with open(Path(d) / ad, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def durum(d):
    return json.loads((Path(d) / "terim_durum.json").read_text())


HATA = []


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def satirlar(d, haric=("olcum_utc",)):
    return {r["terim"]: {k: v for k, v in r.items() if k not in haric} for r in oku(d, "TERIM_TARAMA.csv")}


def alfa_beklenen(r):
    """Elle hesap (sahte veri tanimindan): 62 download / 100; A 30 B 15 C 5 D 5 E 3 F 2 I 2; I'nin kurulus tarihi yok (yasi bilinen
    6 magaza); genc A B E -> pay 3/6 (payda yasi bilinen); genc>=100 satis A(150) E(300); satis medyani 7 magaza [0,10,20,40,150,300,500]
    = 40; USD 46, USD disi (EUR) 15, fiyat yok 1. Ilan yasi original_creation (created_timestamp hep 5 gun: ayirt eder), favori dl
    kumesinde (fiziksel ilanlar fav 7: ayirt eder)."""
    import statistics
    yas = statistics.median((SIMDI - L["original_creation_timestamp"]) / T.AY_SN for L in ALFA_DL)
    fav = statistics.median(L["num_favorers"] for L in ALFA_DL)
    return (r["ilk100_download_n"] == "62" and r["ilk100_download_oran"] == "0.62" and r["sayfa"] == "1" and r["download_n"] == "62"
            and r["farkli_magaza"] == "7" and r["en_buyuk_magaza_payi"] == "0.484" and r["ilk3_magaza_payi"] == "0.806"
            and r["ilk100_farkli_magaza"] == "7" and r["ilk100_en_buyuk_magaza_payi"] == "0.484"
            and r["magaza_bilinen_n"] == "7" and r["genc_magaza_n"] == "3" and r["genc_magaza_payi"] == "0.5"
            and r["genc_satis100_n"] == "2" and r["genc_satis100_satis_medyan"] == "225.0" and r["magaza_satis_medyan"] == "40.0"
            and r["fiyat_usd_n"] == "46" and r["fiyat_usd_disi_n"] == "15" and r["fiyat_yok_n"] == "1" and r["az_veri"] == ""
            and r["magaza_yasi_medyan_ay"] == str(round(((200 + 900) / 2) * GUN / T.AY_SN, 1))
            and r["ilan_yasi_medyan_ay"] == str(round(yas, 1)) and r["favori_medyan"] == str(round(float(fav), 1)))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="terim_"))
    try:
        # 1) tam akis
        s = Sahte()
        d1 = tmp / "a"
        kod, lg = kos(s, d1)
        st = durum(d1)
        kontrol("tam akis kod 0", kod == 0)
        kontrol("tam akis bitti", st["durum"] == "bitti" and st["kalan_terim"] is None)
        kontrol("yazma yok", s.yazma == 0)
        r = satirlar(d1)
        kontrol("terim basina tek satir", sorted(r) == sorted(TERIMLER) and len(oku(d1, "TERIM_TARAMA.csv")) == 3)
        kontrol("alfa olcutleri elle hesapla ayni", alfa_beklenen(r["alfa terim"]))
        import statistics
        usd = [round((400 + i) / 100, 2) for i in range(60) if i % 4] + [10.0]
        kontrol("alfa fiyat medyani yalniz USD", float(r["alfa terim"]["fiyat_medyan_usd"]) == round(statistics.median(usd), 2))
        kontrol("ek sayfa: beta 3 sayfa (10+9+15 < 30 sonra durur)", r["beta terim"]["sayfa"] == "3" and s.terim_istek["beta terim"] == 3)
        kontrol("ek sayfa yok: alfa >= 30 download", s.terim_istek["alfa terim"] == 1)
        kontrol("ek sayfa yok: gama sayfa dolu degil", s.terim_istek["gama terim"] == 1 and r["gama terim"]["sayfa"] == "1")
        kontrol("tekillestirme: beta download 34 (tekrar bir kez)", r["beta terim"]["download_n"] == "34")
        bi = [x for x in oku(d1, "TERIM_ILAN.csv") if x["terim"] == "beta terim"]
        kontrol("TERIM_ILAN beta tekil", len(bi) == len({x["listing_id"] for x in bi}) == 299)
        kontrol("ilk100 yalniz 1. sayfa", r["beta terim"]["ilk100_download_n"] == "10" and r["beta terim"]["ilk100_ilan"] == "100")
        kontrol("az veri isareti (gama 5 download)", r["gama terim"]["az_veri"] == "evet" and r["beta terim"]["az_veri"] == "")
        kontrol("terim basina en cok 6 cagri", all(int(x["cagri"]) <= 6 and int(x["istek"]) <= 6 for x in r.values()))
        kontrol("magaza onbellegi: her magaza bir kez batch", len(s.batch_ids) == len({ILAN[i]["shop_id"] for i in s.batch_ids}))
        kontrol("beta magazalari onbellekten (A alfa'da okundu)", r["beta terim"]["magaza_bilinen_n"] == "2")
        kontrol("gama: batch'te donmeyen ilanin magazasi bilinmeyen", r["gama terim"]["farkli_magaza"] == "2"
                and r["gama terim"]["magaza_bilinen_n"] == "1")
        kontrol("istek sayaci = sahte Etsy istegi", st["istek_toplam"] == s.istek and st["kosular"][-1]["istek"] == s.istek)
        kontrol("durum zaman damgasi", bool(st.get("son_guncelleme_utc")) and st["kosular"][-1].get("bit_utc"))
        kontrol("TERIM_MAGAZA tekil", len(oku(d1, "TERIM_MAGAZA.csv")) == len({r_["shop_id"] for r_ in oku(d1, "TERIM_MAGAZA.csv")}))
        # log
        kontrol("log: terim adi yok", not any(t in lg for t in TERIMLER))
        kontrol("log: baslik / magaza adi / kimlik / fiyat yok", "Baslik" not in lg and "Magaza" not in lg and not re.search(r"\d{6,}", lg)
                and "USD" not in lg and "EUR" not in lg)
        kontrol("log: sayim var", "terim tamam 3" in lg and "kota" in lg)
        # 2) kota: baslangicta < 1.200 -> yalniz ping
        kontrol("varsayilan kota esigi = KOTA_SINIRI 10 (CLAUDE.md)", T.KOTA_ALT == E.KOTA_SINIRI == 10)
        sv = Sahte(kalan=1150)
        kodv, _ = kos(sv, tmp / "b0")
        kontrol("varsayilan esikte 1.150 kalanla tam akis", kodv == 0 and durum(tmp / "b0")["durum"] == "bitti")
        s2 = Sahte(kalan=1150)
        d2 = tmp / "b"
        kod2, _ = kos(s2, d2, kota_alt=1200)
        kontrol("bilinen FAIL: kota < 1200 basta -> kod 3", kod2 == 3)
        kontrol("kota basta: terim istegi yok", s2.terim_istek == {} and s2.istek == 1)
        kontrol("kota basta: durum devam + kalan terim", durum(d2)["durum"] == "devam" and durum(d2)["kalan_terim"] == "alfa terim")
        # 3) kota terimler arasinda: alfa biter, beta'dan once DUR; sonra devam -> ayni sonuc
        s3 = Sahte(kalan=1200 + 4)     # ping 1 + alfa 2 istek -> kalan 1201; beta basinda 1201 >= 1200 -> beta (4) -> 1197 -> DUR
        d3 = tmp / "c"
        kod3, _ = kos(s3, d3, kota_alt=1200)
        kontrol("kota DUR kod 3", kod3 == 3)
        kontrol("kota DUR: 2 terim tamam, gama bekliyor", sorted(satirlar(d3)) == ["alfa terim", "beta terim"]
                and durum(d3)["kalan_terim"] == "gama terim")
        s3.kalan = 5000
        kod3b, _ = kos(s3, d3, kota_alt=1200)
        kontrol("kota sonrasi devam bitti", kod3b == 0 and durum(d3)["durum"] == "bitti")
        kontrol("devam sonucu tam akisla ayni", satirlar(d3) == r)
        kontrol("devam: bitmis terim yeniden okunmaz", s3.terim_istek["alfa terim"] == 1)
        kontrol("devam: istek sayaci iki kosunun toplami", durum(d3)["istek_toplam"] == s3.istek)
        # 4) terim ortasinda 429: terim yazilmaz, devam eden kosu bastan okur
        for k in (3, 4, 5, 6):
            s4 = Sahte()
            s4.k429 = k
            d4 = tmp / f"d{k}"
            kod4, _ = kos(s4, d4)
            ara = satirlar(d4)
            kontrol(f"429 istek {k}: kod 3, yarim terim yok", kod4 == 3 and all(x["durum"] == "tamam" for x in ara.values()))
            s4.k429 = None
            kos(s4, d4)
            kontrol(f"429 istek {k}: devam sonucu ayni", satirlar(d4) == r and durum(d4)["istek_toplam"] == s4.istek)
            bi4 = [x for x in oku(d4, "TERIM_ILAN.csv")]
            kontrol(f"429 istek {k}: TERIM_ILAN tekrar yok", len(bi4) == len({(x["terim"], x["listing_id"]) for x in bi4}))
        # 5) yol verme + devam
        s5 = Sahte()
        d5 = tmp / "e"
        n = {"i": 0}

        def yv():
            n["i"] += 1
            return n["i"] == 4
        kod5, _ = kos(s5, d5, yv=yv)
        kontrol("yol ver kod 4", kod5 == 4 and durum(d5)["durum"] == "devam")
        kos(s5, d5)
        kontrol("yol ver sonrasi ayni", satirlar(d5) == r)
        # 6) sure 0
        d6 = tmp / "f"
        kod6, _ = kos(Sahte(), d6, dk=0)
        kontrol("sure 0: kod 0, devam", kod6 == 0 and durum(d6)["durum"] == "devam")
        # 7) --yeniden yalniz secili terim
        s7 = Sahte()
        kod7, _ = kos(s7, d1, terimler=["beta terim"], yeniden=True)
        hr = ("olcum_utc", "istek", "cagri")
        kontrol("yeniden: yalniz beta okunur, olcutler ayni", kod7 == 0 and set(s7.terim_istek) == {"beta terim"}
                and satirlar(d1, hr) == {k: {a: b for a, b in v.items() if a not in hr} for k, v in r.items()})
        kontrol("yeniden: magaza onbellekten (batch yok)", s7.batch_ids == [])
        kontrol("yeniden: TERIM_ILAN beta cift satir yok", len([x for x in oku(d1, "TERIM_ILAN.csv") if x["terim"] == "beta terim"]) == 299)
        s7b = Sahte()
        kos(s7b, d1)
        kontrol("yeniden bittikten sonra normal kosu tekrar okumaz", s7b.terim_istek == {} and durum(d1)["yeniden_bekleyen"] == [])
        # 7b) bayat magaza (7 gunden eski okuma) yeniden okunur, taze okunmaz
        s7c = Sahte()
        kos(s7c, d1, terimler=["alfa terim"], yeniden=True, simdi=SIMDI + 8 * GUN)
        kontrol("bayat magaza yeniden okunur (8 gun)", len(s7c.batch_ids) == 7)
        s7d = Sahte()
        kos(s7d, d1, terimler=["alfa terim"], yeniden=True, simdi=SIMDI + 10 * GUN)
        kontrol("taze magaza okunmaz (2 gun once okundu)", s7d.batch_ids == [])
        # 7c) baslik yok -> DUR, terim istegi yok
        s7e = Sahte()
        s7e.basliksiz = True
        kod7e, _ = kos(s7e, tmp / "bb")
        kontrol("bilinen FAIL: kota basligi yok -> kod 3, terim istegi yok", kod7e == 3 and s7e.terim_istek == {})
        # 8) terim hatasi: tek terim 500 -> atlanir; ardisik 3 -> kod 1
        s8 = Sahte()
        s8.hata_terim = {"beta terim"}
        d8 = tmp / "g"
        kod8, _ = kos(s8, d8)
        kontrol("tek terim hatasi: diger terimler tamam, kod 0, durum devam", kod8 == 0 and sorted(satirlar(d8)) == ["alfa terim", "gama terim"]
                and durum(d8)["durum"] == "devam")
        kontrol("5xx yeniden denemesi istek sayacinda", durum(d8)["istek_toplam"] == s8.istek)
        dh = durum(d8)
        kontrol("okunamayan terim durumda sayilir", dh["terim_hata"] == {"beta terim": 1})
        s8.hata_terim = set()
        kos(s8, d8)
        kontrol("okunamayan terim sonraki kosuda okunur", durum(d8)["durum"] == "bitti" and durum(d8)["terim_hata"] == {})
        s9 = Sahte()
        s9.hata_terim = set(TERIMLER)
        kod9, _ = kos(s9, tmp / "h")
        kontrol("bilinen FAIL: ardisik 3 terim hatasi kod 1", kod9 == 1)
        # kalici hatali 3 terim listenin basinda: sonraki kosular takilmaz (sona alinir, 2. kosuda 'hata' kapanir)
        sh = Sahte()
        sh.hata_terim = {"h1", "h2", "h3"}
        dh2 = tmp / "h2"
        sira = ["h1", "h2", "h3"] + TERIMLER
        k1, _ = kos(sh, dh2, terimler=sira)
        k2, _ = kos(sh, dh2, terimler=sira)
        st2 = durum(dh2)
        kontrol("kalici hata: 1. kosu kod 1 (hatalilar basta), 2. kosuda hatalilar sona alinir, diger terimler tamam",
                k1 == 1 and k2 == 1 and all(satirlar(dh2)[t]["durum"] == "tamam" for t in TERIMLER))
        kontrol("kalici hata: 2 kosudan sonra 'hata' kapanir, durum bitti", all(satirlar(dh2)[t]["durum"] == "hata" for t in ("h1", "h2", "h3"))
                and st2["durum"] == "bitti" and st2["hata_terim_n"] == 3)
        k3, _ = kos(sh, dh2, terimler=sira)
        kontrol("kalici hata kapandiktan sonra yeniden denenmez", k3 == 0 and sh.terim_istek["h1"] == 2 * 3)
        # 9) secim
        try:
            T.secim_coz(TERIMLER, "alfa terim; yok boyle")
            kontrol("bilinen FAIL: listede olmayan terim", False)
        except SystemExit:
            kontrol("bilinen FAIL: listede olmayan terim", True)
        kontrol("secim: bos = hepsi, buyuk/kucuk harf", T.secim_coz(TERIMLER, "") == TERIMLER
                and T.secim_coz(TERIMLER, " GAMA  terim;alfa terim") == ["gama terim", "alfa terim"])
        liste = T.terimler_oku(T.VARSAYILAN_LISTE)
        kontrol("depodaki terim listesi 153 tekil", len(liste) == 153 and len({x.lower() for x in liste}) == 153)
        # 10) PATCH yasak
        try:
            api_kur(Sahte()).patch("/shops/1/listings/2", {"title": "x"})
            kontrol("bilinen FAIL: PATCH yasak", False)
        except SystemExit as e:
            kontrol("bilinen FAIL: PATCH yasak", "yasak" in str(e))
        # 11) gercek main(): ham stdout'ta terim / kimlik / baslik yok
        s11 = Sahte()
        d11 = tmp / "m"
        buf = io.StringIO()
        eski = sys.argv, sys.stdout, sys.stderr
        E.requests.request = s11
        liste_yol = tmp / "liste.txt"
        liste_yol.write_text("\n".join(TERIMLER) + "\n", encoding="utf-8")
        sys.argv = ["x", "--out", str(d11), "--dk", "60", "--liste", str(liste_yol)]
        os.environ["ETSY_API_KEY"], os.environ["ETSY_SHARED_SECRET"] = "anahtar-sahte-12", "sir-sahte-12345"
        os.environ.pop("GH_TOKEN", None)
        sys.stdout = sys.stderr = buf
        try:
            km = T.main()
        finally:
            sys.argv, sys.stdout, sys.stderr = eski
        ham = buf.getvalue()
        kontrol("main kod 0 + bitti", km == 0 and durum(d11)["durum"] == "bitti")
        kontrol("main ham log: 6+ haneli kimlik yok", not re.search(r"\d{6,}", ham))
        kontrol("main ham log: terim / baslik / magaza / url yok", not any(t in ham for t in TERIMLER) and "Baslik" not in ham
                and "Magaza" not in ham and "etsy/" not in ham)
        # 12) mutasyonlar: test kodu bozuldugunda yakalar
        eski_dl = T.DL_MIN
        T.DL_MIN = 0
        sm = Sahte()
        kos(sm, tmp / "x1")
        kontrol("mutasyon DL_MIN 0 yakalanir (beta ek sayfa yok)", sm.terim_istek["beta terim"] == 1)
        T.DL_MIN = eski_dl
        eski_g = T.GENC_GUN
        T.GENC_GUN = 10 ** 5
        kos(Sahte(), tmp / "x2")
        kontrol("mutasyon GENC_GUN yakalanir", not alfa_beklenen(satirlar(tmp / "x2")["alfa terim"]))
        T.GENC_GUN = eski_g
        eski_te = T.tekil_ekle

        def tekilsiz(tum, gorulen, res, sayfa):
            tum.extend((sayfa, i + 1, L) for i, L in enumerate(res))
        T.tekil_ekle = tekilsiz
        kos(Sahte(), tmp / "x3")
        T.tekil_ekle = eski_te
        kontrol("mutasyon tekil_ekle bozuk yakalanir (beta download 35)", satirlar(tmp / "x3")["beta terim"]["download_n"] != "34")
        # kaydet sirasi: TERIM_TARAMA en son (arada kesilirse terim tamam gorunmez)
        sira_yaz = []
        eski_yc = D.yaz_csv
        D.yaz_csv = lambda p_, a_, s_: (sira_yaz.append(Path(p_).name), eski_yc(p_, a_, s_))
        kos(Sahte(), tmp / "x4", terimler=["gama terim"])
        D.yaz_csv = eski_yc
        kontrol("kaydet: TERIM_TARAMA en son yazilir", sira_yaz and sira_yaz[-1] == "TERIM_TARAMA.csv"
                and all(sira_yaz[i] == "TERIM_TARAMA.csv" for i in range(2, len(sira_yaz), 3)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"SONUC: {'FAIL ' + str(len(HATA)) if HATA else 'PASS'}")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
