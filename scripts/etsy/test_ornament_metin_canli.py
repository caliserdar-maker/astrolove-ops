#!/usr/bin/env python3
"""ornament_metin_canli.py testleri (S13, 13 Kas). Ag BASTAN kapali (CLAUDE.md test agi; emsal scripts/sosyal/test_metricool_yedek.py).
Uctan uca: main() GERCEK Etsy istemcisi (etsy_common.Etsy._call + SaltOkur) uzerinden kosar; yalniz ag katmani
(etsy_common.requests.request) ve token dosyasi sahte. Sahte yanit alanlari depodaki olcum kaydindan (test_yayina_hazir.py:8-11, :44;
olc 42486805159): batch results[] icinde listing_id, state, title, tags, description; x-remaining-today basligi.
OLCULMEDI: canli description'in HTML varligi ("&#39;", "&amp;") ve \\r\\n bicimi; testte iki bicim de denenir.
Bilinen PASS + bilinen FAIL (her DUR kosulu); mutasyon icin ORN_METIN_CANLI_YOL ortam degiskeni betigin baska kopyasini yukler.
Kullanim: python3 scripts/etsy/test_ornament_metin_canli.py -> 'SONUC n/n PASS' (cikis 1 = FAIL)."""
import contextlib
import copy
import csv
import importlib.util
import io
import json
import os
import re
import socket
import sys
import tempfile
import urllib.request
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok
# TEST AGI denetim kancasi: ad yamalari _socket ile ya da yamalanmamis adla (getnameinfo vb.) delinebilir; kanca surec icindeki Python soket yollarini yakalar (alt surec: sitecustomize; -I / Popen / Python disi araclar acik).
import sys as _ag_sys
def _ag_kanca(olay, arg):
    if olay in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        if getattr(arg[0], "family", None) == getattr(socket, "AF_UNIX", -1):
            return
        raise AssertionError("gercek ag acilmaya calisildi: " + olay)
    if olay in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"):
        raise AssertionError("gercek ag acilmaya calisildi: " + olay)
_ag_sys.addaudithook(_ag_kanca)

BURA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURA))
import etsy_common  # noqa: E402

KOK = BURA.parents[1]
YOL = Path(os.environ.get("ORN_METIN_CANLI_YOL") or BURA / "ornament_metin_canli.py")
_sp = importlib.util.spec_from_file_location("ornament_metin_canli", YOL)
M = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(M)

CSV_YOL = KOK / "data/pod/ORNAMENT78_METIN.csv"
SPEC_YOL = KOK / "docs/ornament/ORN_YAYIN_SPEC.json"
SPEC = json.loads(SPEC_YOL.read_text(encoding="utf-8"))
ESKI_KARGO = ("[ SHIPPING ]\nMade and shipped by our production partner, with free shipping. You can see the estimated delivery "
              "time for your country at checkout.")
YENI_KARGO = ("[ SHIPPING ]\nMade and shipped by our production partner. You can see the shipping cost and estimated delivery "
              "time for your country on this page and at checkout.")
DEPO_BAYT = CSV_YOL.read_bytes()
DEPO = list(csv.DictReader(io.StringIO(DEPO_BAYT.decode("utf-8"), newline="")))


def _eski_hal(a):
    """Test girdisi depo CSV'sinin bugunku durumuna bagli olmasin (inceleme bulgusu 13 Kas): fikstur her zaman ESKI kargo bloklu."""
    if ESKI_KARGO in a:
        return a
    if YENI_KARGO in a:
        return a.replace(YENI_KARGO, ESKI_KARGO)
    return a + "\n\n" + ESKI_KARGO


ROWS = [dict(r, aciklama=_eski_hal(r["aciklama"])) for r in DEPO]
IDS = {r["kod"]: 9000000001 + i for i, r in enumerate(ROWS)}          # sahte ilan kimligi 900000000N
SONUC = []


def k(ad, kosul):
    SONUC.append(bool(kosul))
    print(("PASS " if kosul else "FAIL ") + ad, flush=True)


def canli_aciklama(r, bicim="html_crlf"):
    a = r["aciklama"].replace(ESKI_KARGO, YENI_KARGO)
    assert a != r["aciklama"], "CSV kargo bloku beklenen bicimde degil"
    if bicim in ("html_crlf", "html"):
        a = a.replace("'", "&#39;").replace("&", "&amp;").replace("&amp;#39;", "&#39;")
    if bicim in ("html_crlf", "crlf"):
        a = a.replace("\n", "\r\n")
    return a


def ilanlar(bicim="html_crlf"):
    return {IDS[r["kod"]]: {"listing_id": IDS[r["kod"]], "state": "active", "title": r["baslik"],
                            "tags": [t.strip() for t in r["etiketler"].split(",")], "description": canli_aciklama(r, bicim)}
            for r in ROWS}


class Yanit:
    def __init__(self, kod, j, kalan):
        self.status_code, self._j, self.text = kod, j, json.dumps(j)[:300]
        self.headers = {"x-remaining-today": str(kalan)} if kalan is not None else {}

    def json(self):
        return self._j


class SahteAg:
    def __init__(self, ilan, kalan=5000):
        self.ilan, self.kalan, self.istek = ilan, kalan, []

    def __call__(self, method, url, params=None, **kw):
        self.istek.append((method, url.split("/v3/application")[-1], dict(params or {})))
        assert method == "GET", method
        path = url.split("/v3/application")[-1]
        self.kalan -= 1
        if path == "/listings/batch":
            ids = [int(x) for x in params["listing_ids"].split(",")]
            return Yanit(200, {"count": len(ids), "results": [copy.deepcopy(self.ilan[i]) for i in ids if i in self.ilan]}, self.kalan)
        if path.startswith("/shops/"):
            return Yanit(200, {"shop_id": 1}, self.kalan)
        return Yanit(404, {"error": path}, self.kalan)


class SahteStore:
    api_key_header = "k:s"
    access_token = "t"

    def __init__(self, *a):
        pass

    def needs_refresh(self, *a):
        return False


class SayacStore(SahteStore):
    """Kac kez kuruldugunu sayar (URUN_AYAR korumasi token oncesi mi)."""
    n = 0

    def __init__(self, *a):
        SayacStore.n += 1


def csv_metni(rows, sutun=None):
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=sutun or M.SUTUN, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode("utf-8")


def kos(ag=None, ilan_json=None, csv_bayt=None, ilan_ham=None, ortam=None, store=None):
    d = Path(tempfile.mkdtemp(prefix="s13_test_"))
    (d / "I.json").write_text(ilan_ham if ilan_ham is not None else json.dumps(
        ilan_json if ilan_json is not None else {kod: {"listing_id": lid} for kod, lid in IDS.items()}))
    (d / "M.csv").write_bytes(csv_bayt if csv_bayt is not None else csv_metni(ROWS))
    ag = ag or SahteAg(ilanlar())
    eski = (etsy_common.requests.request, M.TokenStore, dict(os.environ), etsy_common.Etsy.__init__)
    etsy_common.requests.request, M.TokenStore = ag, (store or SahteStore)
    ilk = eski[3]

    def hizli(self, store):
        ilk(self, store); self.pace = 0
    etsy_common.Etsy.__init__ = hizli
    os.environ.update(TOKEN_FILE="x", ETSY_API_KEY="k", ETSY_SHARED_SECRET="s", ETSY_SHOP_ID="39729443")
    os.environ.pop("URUN_AYAR", None)
    os.environ.update(ortam or {})                # yalniz bu kosu icin; finally'de onceki ortam geri yuklenir
    try:
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = -1
            rc = M.main(["--ilanlar", str(d / "I.json"), "--csv", str(d / "M.csv"), "--spec", str(SPEC_YOL), "--out", str(d / "o")])
    finally:
        etsy_common.requests.request, M.TokenStore = eski[0], eski[1]
        os.environ.clear(); os.environ.update(eski[2])
        etsy_common.Etsy.__init__ = eski[3]
    O = json.loads((d / "o/OZET.json").read_text())
    yeni = d / "o/ORNAMENT78_METIN.csv"
    return rc, O, (yeni.read_bytes() if yeni.exists() else None), ag, o.getvalue(), d


def satirlar(b):
    return list(csv.DictReader(io.StringIO(b.decode("utf-8"), newline="")))


def dur(ad, rc, O, yeni, parca):
    k(f"bilinen FAIL: {ad} -> DUR, CSV yazilmaz", rc == 1 and yeni is None and parca in O["durum"] and not O["durum"].startswith("HATA"))


def main():
    _ua_once = os.environ.get("URUN_AYAR")       # dis ortamdaki deger (yoksa None), ilk kos() ONCESI; URUN_AYAR kontrolu buna esit olmali
    # ---- bilinen PASS: canli HTML varlikli + \r\n (olculmedi; iki bicim de denenir)
    rc, O, yeni, ag, log, d = kos()
    R = satirlar(yeni) if yeni else []
    k("PASS: cikis 0, durum PASS, 78 satir", rc == 0 and O["durum"] == "PASS" and len(R) == 78)
    k("PASS: kod sirasi ayni", [r["kod"] for r in R] == [r["kod"] for r in ROWS])
    k("PASS: aciklama disindaki 19 sutun birebir", all(a[c] == b[c] for a, b in zip(ROWS, R) for c in M.SUTUN if c != "aciklama"))
    k("PASS: 78/78 aciklama degisti (free shipping -> SPEC kargo cumlesi)", O["degisen"] == 78 and O["degismeyen"] == 0)
    k("PASS: yeni aciklama = beklenen metin (&#39; / &amp; cozuldu, \\r\\n -> \\n)",
      all(r["aciklama"] == ESKI_r["aciklama"].replace(ESKI_KARGO, YENI_KARGO) for r, ESKI_r in zip(R, ROWS)))
    k("PASS: yeni aciklamada \\r yok, HTML varligi yok", all("\r" not in r["aciklama"] and "&#39;" not in r["aciklama"] for r in R))
    k("PASS: zorunlu cumle satir sonuyla bolunmus aciklamada bulundu (78)", O["yeni_zorunlu_cumle"] == 78)
    k("PASS: kapilar: yasak 0, metin_kontrol 0, AI beyan 78, tire 0", O["yeni_yasak_desen"] == 0 and O["yeni_metin_kontrol_hata"] == 0
      and O["yeni_ai_beyan"] == 78 and O["yeni_tire"] == 0)
    k("PASS: once yasak desen 78, ham \\r sayisi > 0", O["yasak_once"] == 78 and O["ham_cr"] > 0)
    k("PASS: istek 2 (shop + 1 batch), yalniz GET", O["istek"] == 2 and all(m == "GET" for m, *_ in ag.istek))
    k("PASS: sha256 / blob sha OZET'te", len(O.get("csv_sha256_yeni", "")) == 64 and len(O.get("csv_blob_yeni", "")) == 40)
    k("PASS: ciktilarda (CSV, OZET, FARK) sahte ilan kimligi yok",
      all(str(9000000001 + i) not in (d / "o" / f).read_text() for i in range(78) for f in ("ORNAMENT78_METIN.csv", "OZET.json", "FARK.md")))
    for bicim in ("html", "crlf", "duz"):
        rc2, O2, y2, *_ = kos(SahteAg(ilanlar(bicim)))
        k(f"PASS: canli bicim {bicim} -> ayni CSV", rc2 == 0 and y2 == yeni)
    # ---- bilinen PASS: degisiklik yok -> bayt bayt ayni
    rc, O, y3, *_ = kos(SahteAg(ilanlar("duz")), csv_bayt=yeni)
    k("PASS: degisiklik yokken cikti CSV girdiyle bayt bayt ayni", rc == 0 and O["degisen"] == 0 and y3 == yeni)
    k("PASS: depo CSV'si yazim ayariyla (csv_yaz) bayt bayt ayni yeniden yazilir", M.csv_yaz(DEPO) == DEPO_BAYT)
    rc, O, y4, *_ = kos(SahteAg(ilanlar("crlf")), csv_bayt=yeni)
    k("PASS: yalniz \\r\\n farki degisiklik sayilmaz (degisen 0, bayt ayni)", rc == 0 and O["degisen"] == 0 and y4 == yeni)
    B5 = csv_metni([dict(r, aciklama=r["aciklama"] + " ") for r in satirlar(yeni)])
    rc, O, y5, *_ = kos(SahteAg(ilanlar("duz")), csv_bayt=B5)
    k("PASS: ornament_taslak.py:593 olcutu (unescape + strip esit) -> eski deger kalir", rc == 0 and O["degisen"] == 0 and y5 == B5)
    # ---- bilinen FAIL
    J = {kod: {"listing_id": lid} for kod, lid in IDS.items()}
    j = dict(J); j.pop(ROWS[0]["kod"])
    dur("kod eksik", *kos(ilan_json=j)[:3], "kod kumesi farkli")
    j = dict(J); j["ZZZ_ZZZ"] = {"listing_id": 9000000000}
    dur("kod fazla", *kos(ilan_json=j)[:3], "kod kumesi farkli")
    j = copy.deepcopy(J); j[ROWS[5]["kod"]] = {"hata": "x"}
    dur("listing_id yok", *kos(ilan_json=j)[:3], "listing_id yok")
    ham = json.dumps(J)[:-1] + f', "{ROWS[0]["kod"]}": {{"listing_id": 9000000001}}}}'
    dur("tekrar eden kod (ilan listesi)", *kos(ilan_ham=ham)[:3], "tekrar eden kod")
    I = ilanlar(); I[IDS[ROWS[3]["kod"]]]["state"] = "inactive"
    dur("inactive ilan", *kos(SahteAg(I))[:3], "active degil")
    I = ilanlar(); I[IDS[ROWS[3]["kod"]]].pop("description")
    dur("description yok", *kos(SahteAg(I))[:3], "description yok")
    I = ilanlar(); x = I[IDS[ROWS[4]["kod"]]]; x["description"] = x["description"].replace("\r\n", "\r\r\n", 1)
    dur("yeni aciklamada tek CR kaldi", *kos(SahteAg(I))[:3], "CR kaldi")
    gercek_yaz = M.csv_yaz

    def bozuk_yaz(rows):                                   # yazilan bayt bellekteki satirlardan farkli -> yeniden okuma kapisi
        rr = [dict(r) for r in rows]; rr[0]["baslik"] += " X"
        return gercek_yaz(rr)
    M.csv_yaz = bozuk_yaz
    try:
        dur("yazilacak baytta aciklama disi sutun farki", *kos()[:3], "yeniden okunan")
    finally:
        M.csv_yaz = gercek_yaz
    I = ilanlar(); I.pop(IDS[ROWS[7]["kod"]])
    dur("batch yanitinda ilan yok", *kos(SahteAg(I))[:3], "batch yanitinda")
    dur("kota tabani alti (kalan 11 < 2 + 10)", *kos(SahteAg(ilanlar(), kalan=12))[:3], "kota")
    # URUN_AYAR korumasi (Serdar 14 Kas): ortam degiskeni doluysa token ve agdan ONCE DUR; yoksa normal akis
    SayacStore.n = 0
    rc, O, y, ag_u, *_ = kos(SahteAg(ilanlar()), store=SayacStore)
    k("PASS: URUN_AYAR yok -> calis normal (cikis 0, token 1 kez kuruldu)", rc == 0 and O["durum"] == "PASS" and SayacStore.n == 1 and ag_u.istek)
    SayacStore.n = 0
    rc, O, y, ag_u, *_ = kos(SahteAg(ilanlar()), store=SayacStore, ortam={"URUN_AYAR": "/sahte/URUN_AYAR.json"})
    k("bilinen FAIL: URUN_AYAR dolu -> DUR (OZET durum), CSV yok, Etsy istegi 0, TokenStore kurulmadi",
      rc == 1 and "URUN_AYAR ortam degiskeni dolu" in O["durum"] and y is None and ag_u.istek == [] and SayacStore.n == 0
      and O["istek"] == 0)
    k("PASS: URUN_AYAR kos sonrasi kos oncesiyle ayni (yoksa yok; dis ortam degeri korunur)", os.environ.get("URUN_AYAR") == _ua_once)
    dur("CSV sutun farki", *kos(csv_bayt=csv_metni(ROWS, M.SUTUN[:-1]))[:3], "sutun")
    dur("CSV 77 satir", *kos(csv_bayt=csv_metni(ROWS[:-1]))[:3], "77 satir")
    dur("CSV tekrar eden kod", *kos(csv_bayt=csv_metni(ROWS[:-1] + [ROWS[0]]))[:3], "tekil kod")
    for ad, boz, parca in (("yeni aciklamada yasak desen", lambda a: a + "\nShips  FREE today.", "kapi FAIL"),
                           ("zorunlu cumle yok", lambda a: a.replace("on this page and at checkout", "at checkout"), "kapi FAIL"),
                           ("metin_kontrol hatasi (uzun tire)", lambda a: a + " — x", "kapi FAIL"),
                           ("AI beyani yok", lambda a: a.replace(etsy_common.AI_BEYAN["en"], "We make art"), "kapi FAIL")):
        I = ilanlar(); x = I[IDS[ROWS[10]["kod"]]]; x["description"] = boz(x["description"])
        rc, O, y, *_ = kos(SahteAg(I))
        dur(ad, rc, O, y, parca)
        k(f"bilinen FAIL: {ad} -> OZET'te kod {ROWS[10]['kod']} kapi hatasi", ROWS[10]["kod"] in (O.get("kapi_hata") or {}))
    # GET disi istek: SaltOkur calisma aninda durdurur (ag katmanina istek gitmez)
    ag = SahteAg(ilanlar())
    gercek = etsy_common.requests.request
    etsy_common.requests.request = ag
    try:
        api = M.SaltOkur(SahteStore()); api.pace = 0
        try:
            api.patch("/shops/1/listings/9000000001", {"description": "x"}); ok = False
        except SystemExit as e:
            ok = "YASAK" in str(e.code)
    finally:
        etsy_common.requests.request = gercek
    k("bilinen FAIL: GET disi istek (PATCH) -> SaltOkur SystemExit, aga istek yok", ok and not ag.istek)
    # ---- test agi denetim kancasi (CLAUDE.md:124; emsal test_urun_ayar): ad yamalarini atlayan yollar da kapali
    def ag_dene(f):
        try:
            f(); return False
        except AssertionError as e:
            return "gercek ag" in str(e)
        except Exception:
            return False
    import _socket as _ham
    _u = _ham.socket(_ham.AF_INET, _ham.SOCK_DGRAM)
    _t = _ham.socket(_ham.AF_INET, _ham.SOCK_STREAM)
    try:
        k("TEST AGI (kanca): _socket connect / UDP sendto / sendmsg AssertionError verir",
          ag_dene(lambda: _t.connect(("192.0.2.1", 9))) and ag_dene(lambda: _u.sendto(b"x", ("192.0.2.1", 9)))
          and ag_dene(lambda: _u.sendmsg([b"x"], [], 0, ("192.0.2.1", 9))))
    finally:
        _u.close(); _t.close()
    k("TEST AGI (kanca): getnameinfo / gethostbyname / gethostbyaddr / _socket.getaddrinfo AssertionError verir",
      ag_dene(lambda: socket.getnameinfo(("192.0.2.1", 9), 0)) and ag_dene(lambda: _ham.gethostbyname("example.invalid"))
      and ag_dene(lambda: _ham.gethostbyaddr("192.0.2.1")) and ag_dene(lambda: _ham.getaddrinfo("example.invalid", 80)))
    # ---- tarama: betikte dogrudan HTTP istemcisi yok
    kaynak = YOL.read_text(encoding="utf-8")
    k("tarama: betikte requests / urllib / http.client / curl cagrisi yok",
      not any(x in kaynak for x in ("requests.", "import requests", "urllib", "http.client", "curl")))
    # ---- sir sayimi (Genel Merkez eki): bos deger -> 4, sayi > 0 -> 3, temiz -> 0
    d = Path(tempfile.mkdtemp(prefix="s13_sir_")); (d / "a.txt").write_text("temiz metin")
    eski = dict(os.environ)
    try:
        os.environ.update(ETSY_SHARED_SECRET="QzS3cr7x", ETSY_API_KEY="Kk3yStr1ngQ7w8e9")
        with contextlib.redirect_stdout(io.StringIO()):
            r0 = M.main(["sir-say", str(d)])
        (d / "b.log").write_text("x QzS3cr7x y Kk3yStr1ngQ7w8e9 QzS3cr7x")
        with contextlib.redirect_stdout(io.StringIO()) as o:
            r3 = M.main(["sir-say", str(d)])
        os.environ["ETSY_SHARED_SECRET"] = ""
        with contextlib.redirect_stdout(io.StringIO()):
            r4 = M.main(["sir-say", str(d)])
    finally:
        os.environ.clear(); os.environ.update(eski)
    k("PASS: sir sayimi temiz -> 0", r0 == 0)
    k("bilinen FAIL: sir sayimi sayi > 0 -> 3 (yalniz dosya adi + sayi; deger basilmaz)",
      r3 == 3 and "b.log: 3" in o.getvalue() and "QzS3cr7x" not in o.getvalue() and "Kk3y" not in o.getvalue())
    k("bilinen FAIL: sir sayimi ortam degeri bos -> 4 (kontrol yapilamadi)", r4 == 4)
    # ---- is akisi sozlesmesi
    import yaml
    wf_yol = KOK / ".github/workflows/ornament-metin-canli.yml"
    W = yaml.safe_load(wf_yol.read_text(encoding="utf-8")); wf = wf_yol.read_text(encoding="utf-8")
    oku, dal = W["jobs"]["oku"], W["jobs"]["dal"]
    k("is akisi: oku izinleri actions: read + contents: read; dal yalniz contents: write",
      oku["permissions"] == {"actions": "read", "contents": "read"} and dal["permissions"] == {"contents": "write"})
    sirli = [s.get("name") for jb in (oku, dal) for s in jb["steps"] if "secrets.ETSY_" in json.dumps(s.get("env") or {})]
    k("is akisi: Etsy sirlari yalniz 'Kos' adiminda", sirli == ["Kos"] and "secrets.ETSY_" not in json.dumps(dal))
    adlar = [s.get("name") or s.get("uses") for s in oku["steps"]]
    k("is akisi: kilit token indirmeden once", adlar.index("Etsy kilidi") < adlar.index("Token + ilan listesi") < adlar.index("Kos"))
    k("is akisi: SIPARIS_KOD_ANAHTARI yok, git add -A yok, --force yok",
      "SIPARIS_KOD_ANAHTARI" not in wf and "git add -A" not in wf and not re.search(r"git push[^\n]*(--force|\s-f\b)", wf))
    k("is akisi: ls-remote ve diff ayri adimda (hata yutulmaz)", 'R=$(git ls-remote origin "refs/heads/$B")' in wf
      and "git diff --cached -U0 > _fark.txt" in wf and "|| true" not in json.dumps(dal))
    k("is akisi: push yalniz s13/metin-canli dalina, yalniz dal isinde",
      "git push origin HEAD:refs/heads/s13/metin-canli" in json.dumps(dal) and "git push" not in json.dumps(oku))
    # ---- dal isi sizinti kapisi (Serdar 19 Kas, Merkez DERSLER_20261119; CLAUDE.md KALITE 9): satir yml'den okunur, gercek kod kosar
    # (alt surec yok: exec, ag kapali surecte). Rakam siniri (?<!\d)...(?!\d): alt cizgi bitisik sizinti yakalanir; 900000000N izni aynen.
    dal_run = next(s["run"] for s in dal["steps"] if s.get("name") == "Dal s13/metin-canli (yalniz CSV)")
    kapi_m = re.search(r'python3 -c "(.*?)" \\\n', dal_run, re.S)
    k("is akisi: dal sizinti kapisi satiri bulundu (python3 -c)", kapi_m is not None)
    kapi_kod = kapi_m.group(1) if kapi_m else "import sys; sys.exit(0)"
    k("is akisi: sizinti deseni rakam sinirli, \\b yok", r"(?<!\d)\d{10}(?!\d)" in kapi_kod and r"(?<!\d)42\d{8}(?!\d)" in kapi_kod
      and r"\b" not in kapi_kod)

    def kapi_dene(eklenen):
        with tempfile.TemporaryDirectory() as td:
            eski_cwd = os.getcwd(); os.chdir(td)
            try:
                Path("_fark.txt").write_text("+++ b/data/pod/ORNAMENT78_METIN.csv\n" + "".join(f"+{s}\n" for s in eklenen), encoding="utf-8")
                try:
                    exec(compile(kapi_kod, "<dal-kapi>", "exec"), {"__name__": "__main__"})
                    return 0
                except SystemExit as e:
                    return int(e.code or 0)
            finally:
                os.chdir(eski_cwd)
    on = lambda b: b + "12345678"                                  # ornek no kaynakta duz yazilmaz (depo sizinti taramasi)
    for ad, eklenen, bek in (("alt cizgi bitisik 42 onekli siparis no (x_42..._y)", [f"listing,x_{on('42')}_y,metin"], 1),
                             ("alt cizgi bitisik 43 onekli 10 hane (x_43..._y; sabit onek yok)", [f"x_{on('43')}_y"], 1),
                             ("bosluklu 10 hane (40 onek)", [f"kimlik {on('40')} metin"], 1),
                             ("sizintisiz fark", ["slug,Merry Christmas ornament gift"], 0),
                             ("izinli test no 900000001", ["test 900000001 satir"], 0),
                             ("11 hane (kosu id gibi) 10 hane sayilmaz", ["kosu 44545840206"], 0),
                             ("eklenen satir yok", [], 1)):
        rc_k = kapi_dene(eklenen)
        k(f"dal sizinti kapisi: {ad} -> cikis {bek}", rc_k == bek)
    n, t = sum(SONUC), len(SONUC)
    print(f"SONUC {n}/{t} PASS")
    return 0 if n == t else 1


if __name__ == "__main__":
    sys.exit(main())
