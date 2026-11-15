#!/usr/bin/env python3
"""magaza_parca_yaz sahte API testi (ag yok). duyuru_marka senaryolari: PASS, parca yok -> DUR, parca 2 kez -> DUR, kota dusuk -> DUR,
izinsiz HTML varligi -> DUR, geri okumada baska alan degisti -> FAIL, &#39; -> PASS_GORUNUR, yanlis onay -> HATA.
duyuru_noel (Serdar 15 Kas, tam degisim): PASS; \\r\\n donen Etsy -> PASS; \\n'siz donen -> SATIR_SONU; tek \\r -> SATIR_SONU; <br> -> FAIL;
zaten yazili -> DUR; tire / Art'siz / HTML / kota / yasak sozlu metin (--metin) -> DUR ve neden raporda; geri okuma farkli -> FAIL;
dosya sha256 onayli metinle ayni. metin_yasak_kapisi taklit EDILMEZ (gercek etsy_common fonksiyonu)."""
import hashlib
import os
import pathlib
import sys
import tempfile
import socket
import ssl  # noqa: F401  (ag kapatmadan once yuklenir: ssl/requests socket sinifini alt sinif yapar)
import urllib.request


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


# TEST AGI (CLAUDE.md:124; plan URUN_AYAR_MAIN_PLAN 10-G4): gercek dis ag bastan kapali; emsal scripts/sosyal/test_metricool_yedek.py:19-25
socket.socket.connect = _ag_yok
socket.socket.connect_ex = _ag_yok
socket.socket.sendto = _ag_yok
socket.create_connection = _ag_yok
socket.getaddrinfo = _ag_yok      # DNS de kapali (inceleme 1. tur)
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import magaza_parca_yaz as m  # noqa: E402
import etsy_common as E  # noqa: E402

DUYURU = "Welcome! Each original AstroLove design is made to order. Thank you."
NOEL_YOL = pathlib.Path(__file__).resolve().parents[2] / "docs" / "magaza" / "DUYURU_NOEL_20261115.txt"
NOEL_SHA = "99c8738a2e3e5f05cbe2e23d91eaebe24eda1a6255be664e1c9d4c7fc4cc9f7e"
ESKI_NOEL = "Every original AstroLoveArt couple design joins two zodiac signs into one shared symbol. We don&#39;t stop."


class SahteEtsy:
    def __init__(self, shop, kota=500, bozan=False, donus=None):
        self.shop, self.remaining, self.calls, self.bozan, self.puts = dict(shop), kota, 0, bozan, []
        self.donus = donus or (lambda v: v)
        if donus in ("PUT_HATA", "PUT_ZAMAN", "GET_HATA"):
            self.donus = donus

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        return dict(self.shop)

    def put(self, path, data):
        self.calls += 1
        if self.donus == "PUT_HATA":
            raise SystemExit("HATA: PUT /shops/1 -> 500")
        if self.donus == "PUT_ZAMAN":
            raise TimeoutError("read timed out")
        if self.donus == "GET_HATA":
            self.get = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("baglanti koptu"))
        self.puts.append(dict(data))
        if self.donus == "GET_HATA":
            self.shop.update(data)
            return
        self.shop.update({k: self.donus(v) for k, v in data.items()})
        if self.bozan:
            self.shop["sale_message"] = "degisti"


class SahteStore:
    def __init__(self, *a):
        pass

    def needs_refresh(self):
        return False


def kos(shop, kota=500, bozan=False, onay="DUYURU_MARKA", is_="duyuru_marka", metin=None, donus=None):
    api = SahteEtsy(shop, kota, bozan, donus)
    m.Etsy, m.TokenStore = (lambda store: api), SahteStore
    out = tempfile.mkdtemp()
    sys.argv = ["x", "--is", is_, "--out", out, "--confirm", onay] + (["--metin", str(metin)] if metin else [])
    try:
        m.main(); kod = 0
    except SystemExit as e:
        kod = e.code if isinstance(e.code, int) else ("HATA" if e.code else 0)
    rapor = (pathlib.Path(out) / "DUYURU_GERI_OKUMA.txt")
    yedek = sorted(p.name for p in pathlib.Path(out).glob("DUYURU_YEDEK*.json"))
    return kod, api, rapor.read_text(encoding="utf-8") if rapor.exists() else "", yedek


def metin_dosya(t):
    p = pathlib.Path(tempfile.mkdtemp()) / "m.txt"
    p.write_text(t + "\n", encoding="utf-8")
    return p


def noel(shop=None, **k):
    return kos(shop or {"title": "t", "announcement": ESKI_NOEL, "sale_message": "s"}, onay="DUYURU_NOEL", is_="duyuru_noel", **k)


def main():
    os.environ.update(ETSY_SHOP_ID="1", TOKEN_FILE="/dev/null")
    taban = {"title": "t", "announcement": DUYURU, "sale_message": "s"}
    sonuc = []

    # ---- duyuru_marka (bozulmamali)
    kod, api, r, _ = kos(taban)
    sonuc.append(("PASS", kod == 0 and len(api.puts) == 1 and api.puts[0] == {"announcement": DUYURU.replace("AstroLove design", "AstroLoveArt design")}
                  and "SONUC: PASS" in r and "yeni parca 1" in r and "eski parca (Art'siz) 0" in r))
    kod, api, r, _ = kos({**taban, "announcement": "Each original AstroLoveArt design."})
    sonuc.append(("zaten duzeltilmis -> DUR", kod == 3 and not api.puts))
    kod, api, r, _ = kos({**taban, "announcement": DUYURU + " " + DUYURU})
    sonuc.append(("parca 2 kez -> DUR", kod == 3 and not api.puts))
    kod, api, r, _ = kos(taban, kota=9)
    sonuc.append(("kota 9 -> DUR", kod == 3 and not api.puts))
    kod, api, r, _ = kos(taban, kota=11)
    sonuc.append(("marka: kota 11 -> DUR (on kosul 12)", kod == 3 and not api.puts and "kota 11 < 12" in r))
    kod, api, r, _ = kos({**taban, "announcement": DUYURU + " A &amp; B"})
    sonuc.append(("&amp; -> DUR", kod == 3 and not api.puts))
    kod, api, r, _ = kos(taban, bozan=True)
    sonuc.append(("baska alan degisti -> FAIL", kod == 2 and "SONUC: FAIL" in r))
    kod, api, r, _ = kos({**taban, "announcement": DUYURU + " We don&#39;t stop."})
    sonuc.append(("&#39; -> gonderilen unescape", len(api.puts) == 1 and "don't" in api.puts[0]["announcement"]))
    kod, api, r, _ = kos(taban, onay="YANLIS")
    sonuc.append(("yanlis onay -> yazma yok", kod == "HATA" and not api.puts))

    # ---- duyuru_noel (tam degisim)
    b = NOEL_YOL.read_bytes()
    sonuc.append(("noel: dosya sha256 onayli metinle ayni (1080 bayt, tek \\n sonda)",
                  hashlib.sha256(b).hexdigest() == NOEL_SHA and len(b) == 1080 and b.endswith(b".\n") and not b.endswith(b"\n\n")))
    YENI = b.decode("utf-8").rstrip("\n")
    kod, api, r, y = noel()
    sonuc.append(("noel: PASS (tek PUT, yalniz announcement, dosya metni, yedek zaman damgali, eski metin raporda tam)",
                  kod == 0 and api.puts == [{"announcement": YENI}] and "SONUC: PASS" in r and ESKI_NOEL in r
                  and len(y) == 1 and y[0].startswith("DUYURU_YEDEK_") and y[0] != "DUYURU_YEDEK.json"))
    kod, api, r, _ = noel(donus=lambda v: v.replace("\n", "\r\n").replace("'", "&#39;"))
    sonuc.append(("noel: \\r\\n ve &#39; donen Etsy -> PASS", kod == 0 and "SONUC: PASS" in r and len(api.puts) == 1))
    kod, api, r, _ = noel(donus=lambda v: v.replace("\n", " "))
    sonuc.append(("noel: \\n'siz donen -> SATIR_SONU (cikis 2)", kod == 2 and "SONUC: SATIR_SONU" in r and "tek \\r 0" in r))
    kod, api, r, _ = noel(donus=lambda v: v.replace("\n", "\r"))
    sonuc.append(("noel: tek \\r donen -> SATIR_SONU, tek \\r sayisi raporda", kod == 2 and "SONUC: SATIR_SONU" in r and "tek \\r 2" in r))
    kod, api, r, _ = noel(donus=lambda v: v.replace("\n\n", "<br><br>"))
    sonuc.append(("noel: <br> donen -> FAIL", kod == 2 and "SONUC: FAIL" in r and "<br> 2" in r))
    kod, api, r, _ = noel(donus=lambda v: v[:-1])
    sonuc.append(("noel: geri okuma farkli -> FAIL", kod == 2 and "SONUC: FAIL" in r))
    kod, api, r, _ = noel(bozan=True)
    sonuc.append(("noel: baska alan degisti -> FAIL", kod == 2 and "SONUC: FAIL" in r and "sale_message" in r))
    kod, api, r, _ = noel({"title": "t", "announcement": YENI.replace("\n", "\r\n").replace("'", "&#39;"), "sale_message": "s"})
    sonuc.append(("noel: zaten yazili (\\r\\n + &#39;) -> DUR", kod == 3 and not api.puts and "zaten yazili" in r))
    kod, api, r, _ = noel({"title": "t", "announcement": YENI.replace("\n", " "), "sale_message": "s"})
    sonuc.append(("noel: zaten yazili (satir sonu farkli) -> DUR, ikinci yazim yok", kod == 3 and not api.puts and "satir sonu farkli" in r))
    # neden on kosuldan gelmeli (ENGEL kapisi da tireyi yakalar, etsy_common METIN_KESIN "uzun/orta tire"; on kosul onden calisir)
    for ad, t, neden, kapi in (("tire", YENI.replace(" so a quick", " — a quick"), "yeni metinde uzun/orta tire", False),
                               ("orta tire", YENI.replace(" so a quick", " – a quick"), "yeni metinde uzun/orta tire", False),
                               ("Art'siz", YENI.replace("AstroLoveArt couple", "AstroLove couple"), "yeni metinde 'AstroLove' (Art'siz) 1 kez", False),
                               ("HTML", YENI.replace("you're", "you&#39;re"), "yeni metinde HTML varligi", False),
                               ("yasak soz", YENI + " Printed by Printful.", "metin yasak kapisi", True)):
        kod, api, r, _ = noel(metin=metin_dosya(t))
        sonuc.append((f"noel: {ad} -> DUR, neden raporda ({'ENGEL kapisi' if kapi else 'on kosul'})",
                      kod == 3 and not api.puts and neden in r and "SONUC: DUR" in r and (("metin yasak kapisi" in r) == kapi)))
    kod, api, r, y = noel(kota=11)
    sonuc.append(("noel: kota 11 -> DUR, yedek on kosuldan once yazildi", kod == 3 and not api.puts and "kota 11 < 12" in r and len(y) == 1))
    kod, api, r, _ = noel({"title": "t", "announcement": YENI, "sale_message": "s"})
    sonuc.append(("noel: zaten yazili (birebir) -> DUR, birebir nedeni", kod == 3 and not api.puts and "canli metin yeni metne esit" in r))
    for ad, canli in (("kesik", YENI[:-1]), ("<br>", YENI.replace("\n\n", "<br><br>")), ("&rsquo;", YENI.replace("'", "&rsquo;")),
                      ("cift kacis &amp;#39;", YENI.replace("'", "&amp;#39;")), ("U+02BC", YENI.replace("'", "\u02bc"))):
        # BILINEN SINIR: ilk 60 harf/rakam icinde elle duzeltilmis canli metin iz sayilmaz (yazim gider)
        kod, api, r, _ = noel({"title": "t", "announcement": canli, "sale_message": "s"})
        sonuc.append((f"noel: FAIL sonrasi ikinci kosu ({ad} canli) -> DUR, PUT yok", kod == 3 and not api.puts and "onceki yazim izi" in r))
    kod, api, r, _ = noel(metin=metin_dosya(""))
    sonuc.append(("noel: bos metin -> DUR", kod == 3 and not api.puts and "yeni metin bos" in r))
    kod, api, r, _ = noel(donus="PUT_HATA")
    sonuc.append(("noel: PUT hatasi -> cikis 1, rapor (eski metin tam) yazildi", kod == 1 and "SONUC: HATA" in r and ESKI_NOEL in r))
    kod, api, r, _ = noel(donus="PUT_ZAMAN")
    sonuc.append(("noel: PUT zaman asimi (requests istisnasi) -> cikis 1, rapor yazildi", kod == 1 and "TimeoutError" in r and ESKI_NOEL in r))
    kod, api, r, _ = noel(donus="GET_HATA")
    sonuc.append(("noel: PUT sonrasi GET hatasi -> cikis 1, rapor yazildi", kod == 1 and len(api.puts) == 1 and "ConnectionError" in r))
    kod2, api2, r2, _ = noel(dict(api.shop))
    sonuc.append(("noel: GET hatasi sonrasi ikinci kosu -> DUR (zaten yazili), PUT yok", kod2 == 3 and not api2.puts and "zaten yazili" in r2))
    _sakla = m.TAM_ISLER["duyuru_noel"]
    m.TAM_ISLER["duyuru_noel"] = _sakla[:3] + ("0" * 64,)
    try:
        kod, api, r, _ = noel()
    finally:
        m.TAM_ISLER["duyuru_noel"] = _sakla
    sonuc.append(("noel: varsayilan dosya sha256 onayliyla farkli -> DUR, Etsy istegi yok", kod == "HATA" and api.calls == 0 and not api.puts))
    sonuc.append(("noel: betikteki onayli sha256 = onayli deger", m.TAM_ISLER["duyuru_noel"][3] == NOEL_SHA))
    kod, api, r, _ = noel(kota=None)
    sonuc.append(("noel: kota okunamadi -> DUR", kod == 3 and not api.puts and "kota okunamadi" in r))
    kod, api, r, _ = noel(kota=12)
    sonuc.append(("noel: kota 12 -> PASS (sinir)", kod == 0 and len(api.puts) == 1))
    kod, api, r, _ = kos({"title": "t", "announcement": ESKI_NOEL}, onay="DUYURU_MARKA", is_="duyuru_noel")
    sonuc.append(("noel: yanlis onay -> yazma yok", kod == "HATA" and not api.puts))
    kod, api, r, _ = kos(taban, metin=NOEL_YOL)
    sonuc.append(("marka: --metin -> HATA", kod == "HATA" and not api.puts))
    sonuc.append(("noel: kapi gercek fonksiyon (taklit yok)", m.metin_yasak_kapisi is E.metin_yasak_kapisi
                  and E.METIN_KAPI_MOD == "UYARI"))
    import _socket as _ham
    try:
        _ham.getaddrinfo("192.0.2.1", 9, 0, 0, 0, _ham.AI_NUMERICHOST); ag_ok = False
    except AssertionError as e:
        ag_ok = "gercek ag" in str(e)
    sonuc.append(("TEST AGI (kanca): _socket.getaddrinfo AssertionError verir", ag_ok))

    for ad, ok in sonuc:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(ok for _, ok in sonuc)
    print(f"magaza_parca_yaz testleri: {n}/{len(sonuc)} PASS")
    sys.exit(0 if n == len(sonuc) else 1)


if __name__ == "__main__":
    main()
