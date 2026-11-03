#!/usr/bin/env python3
"""poster_metin_yaz testleri (sahte Etsy; ag yok). Her kapi bilinen PASS + bilinen FAIL ile (Merkez 4 Kas dersi).
Canli metin: CANCER_LIBRA 3 Kas canli okumasi (testdata_poster_cancer_libra.json). Kuru plan poster_metin_kuru.plan_ilan ile ayni
canli veriden kurulur (Serdar onayli kuru kosuyla ayni yol); FAIL durumlari sahte canlinin bozulmasiyla uretilir.
Kullanim: python3 scripts/etsy/test_poster_metin_yaz.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import copy
import csv
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import poster_metin_kuru as P  # noqa: E402
import poster_metin_yaz as Y  # noqa: E402

Y.BEKLE_SN = 0
D = json.loads(pathlib.Path(__file__).with_name("testdata_poster_cancer_libra.json").read_text())
LID, SHOP = "4570143815", "1"
BOY = ["5×7″ (13×18cm)"] + list(P.K.BOYLAR)
sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"))


class Sahte:
    """Durumlu sahte Etsy: ilan (EN), RU ceviri, envanter. Yazmalar saklanir; bozuk_* bayraklari hata uretir."""

    def __init__(self, kalan=500):
        self.calls, self.remaining, self.yaz = 0, kalan, []
        self.L = dict(listing_id=int(LID), state="active", title=D["title"], description=D["description"], tags=list(D["tags"]),
                      materials=["matte art paper", "ink"], last_modified_timestamp=1)
        self.ru = dict(title=D["ru"]["title"], description=D["ru"]["description"], tags=list(D["ru"]["tags"]))
        self.inv = {"products": [{"property_values": [{"property_id": 513, "values": [b]}], "offerings": [{"price": {"amount": 1990, "divisor": 100}}]} for b in BOY]}
        self.ru_put_hata = self.patch_bozuk = self.ru_bozuk = self.put_islenip_hata = False
        self.patch_timeout = False
        self.put_n = 0

    def kota_kapisi(self, ne=""):
        if self.remaining is not None and self.remaining < E.KOTA_SINIRI:
            raise SystemExit("DUR: kota esigi")

    def _say(self):
        self.calls += 1
        if self.remaining is not None:
            self.remaining -= 1

    def get(self, path, params=None, ok404=False):
        self._say()
        if path == f"/listings/{LID}":
            return copy.deepcopy(self.L)
        if path == f"/listings/{LID}/inventory":
            return copy.deepcopy(self.inv)
        if path == f"/shops/{SHOP}/listings/{LID}/translations/ru":
            return copy.deepcopy(self.ru)
        raise AssertionError(path)

    def patch(self, path, data):
        self._say(); self.yaz.append(("PATCH", path, dict(data)))
        assert set(data) == {"description"}, data
        if self.patch_timeout:
            raise TimeoutError("read timeout")
        if getattr(self, "patch_islenip_hata", False):
            self.L["description"] = data["description"]; self.L["last_modified_timestamp"] += 1
            raise SystemExit("HTTP 503 PATCH (islendi)")
        self.L["description"] = data["description"] + (" X" if self.patch_bozuk else "")
        self.L["last_modified_timestamp"] += 1

    def put(self, path, data):
        self._say(); self.yaz.append(("PUT", path, dict(data)))
        self.put_n += 1
        if self.ru_put_hata:
            raise SystemExit("HTTP 500 PUT translations")
        self.ru = dict(title=data["title"], description=data["description"] + (" X" if self.ru_bozuk and self.put_n == 1 else ""),
                       tags=data["tags"].split(","))
        if self.put_islenip_hata:
            raise SystemExit("HTTP 503 PUT translations (islendi)")


def kuru_plan():
    a = Sahte()
    x = a.get(f"/listings/{LID}"); ru = a.get(f"/shops/{SHOP}/listings/{LID}/translations/ru"); inv = a.get(f"/listings/{LID}/inventory")
    kp, h = P.plan_ilan(LID, x, ru, inv, SHOP)
    assert not h, h
    y = dict(title=x["title"], tags=x["tags"], materials=x["materials"], ru=dict(title=ru["title"], tags=ru["tags"]))
    return {LID: kp}, {LID: y}


KURU, YEDEK = kuru_plan()


def kos(api, kuru=None, yedek=None, uygula=True, geri=False):
    with tempfile.TemporaryDirectory() as d:
        try:
            s = Y.calis(api, SHOP, [LID], kuru or KURU, yedek or YEDEK, d, uygula, geri); dur = None
        except SystemExit as e:
            s, dur = None, str(e)
        rows = list(csv.DictReader(open(pathlib.Path(d) / "DEGISIKLIK.csv")))
    return s, dur, rows


# 1 normal akis PASS
a = Sahte(); s, dur, rows = kos(a)
k("normal: PASS, EN + RU yeni metin, DEGISIKLIK satiri (EN/RU UTC, last_modified)", dur is None and s[0]["sonuc"] == "PASS"
  and Y.norm(a.L["description"]) == Y.norm(KURU[LID]["en_sonra"]) and Y.norm(a.ru["description"]) == Y.norm(KURU[LID]["ru_sonra"])
  and rows[0]["en_utc"] and rows[0]["ru_utc"] and rows[0]["last_modified_timestamp"] == "2", (dur, rows))
k("normal: yalniz aciklama yazildi (PATCH govdesi yalniz description; RU baslik + etiket canli AYNEN)",
  a.yaz[0][2].keys() == {"description"} and a.yaz[1][2]["title"] == D["ru"]["title"] and a.yaz[1][2]["tags"] == ",".join(D["ru"]["tags"])
  and a.L["title"] == D["title"] and a.L["tags"] == D["tags"])
k("normal: premium / long-lasting / free preview yok, 300 dpi var", not any(x in a.L["description"].lower() for x in ("premium", "long-lasting", "free preview"))
  and "300 dpi" in a.L["description"] and "преми" not in a.ru["description"])
k("normal: istek <= butce (20)", a.calls <= Y.ISTEK_ILAN, a.calls)
# 2 kuru (uygula yok): yazim yok
b = Sahte(); s, dur, _ = kos(b, uygula=False)
k("kuru: KURU, yazim yok", dur is None and s[0]["sonuc"] == "KURU" and not b.yaz)
# 3 ZATEN_YENI
c = Sahte(); kos(c); n0 = len(c.yaz); s, dur, _ = kos(c)
k("ZATEN_YENI: ikinci kosuda POST/PUT/PATCH yok", dur is None and s[0]["sonuc"] == "ZATEN_YENI" and len(c.yaz) == n0)
# 4 bayat
d = Sahte(); d.L["description"] = D["description"].replace("Our original design", "Our new design"); s, dur, _ = kos(d)
k("FAIL bayat (ne once ne sonra): DUR, yazim yok", dur and "bayat" in dur and not d.yaz, dur)
d2 = Sahte(); d2.ru["description"] = D["ru"]["description"] + " "; d2.ru["description"] = d2.ru["description"].replace("Овен", "Овен!") if "Овен" in D["ru"]["description"] else d2.ru["description"] + "!"
s, dur, _ = kos(d2)
k("FAIL bayat RU: DUR, yazim yok", dur and "bayat" in dur and not d2.yaz, dur)
# 5 onay ozeti farki
kb = copy.deepcopy(KURU); kb[LID]["onay_ozet"] = "0" * 64
e = Sahte(); s, dur, _ = kos(e, kuru=kb)
k("FAIL onay ozeti farkli: DUR, yazim yok", dur and "onay ozeti" in dur and not e.yaz, dur)
# 6 state
f = Sahte(); f.L["state"] = "draft"; s, dur, _ = kos(f)
k("FAIL state draft: DUR, yazim yok", dur and "state" in dur and not f.yaz, dur)
# 7 baslik / etiket / malzeme / RU baslik / RU etiket yedekten farkli
for ad, boz in (("EN baslik", lambda z: z.L.update(title=z.L["title"] + " x")), ("EN etiket", lambda z: z.L["tags"].append("yeni")),
                ("EN malzeme", lambda z: z.L.update(materials=["paper"])), ("RU baslik", lambda z: z.ru.update(title=z.ru["title"] + " x")),
                ("RU etiket", lambda z: z.ru["tags"].append("новый"))):
    g = Sahte(); boz(g); s, dur, _ = kos(g)
    k(f"FAIL {ad} yedekten farkli: DUR, yazim yok", dur and ad in dur and not g.yaz, dur)
# 8 RU yazimi basarisiz -> EN yedekten geri yazilir, DUR
h = Sahte(); h.ru_put_hata = True; s, dur, rows = kos(h)
k("FAIL RU PUT hatasi: EN eski metne geri yazildi, RU eski, DUR, DEGISIKLIK FAIL satiri",
  dur and Y.norm(h.L["description"]) == Y.norm(D["description"]) and Y.norm(h.ru["description"]) == Y.norm(D["ru"]["description"])
  and [w[0] for w in h.yaz] == ["PATCH", "PUT", "PATCH"] and rows[0]["sonuc"] == "FAIL" and "EN yazimdan onceki metne geri yazildi" in rows[0]["neden"]
  and rows[0]["geri_utc"] and rows[0]["last_modified_timestamp"] == "3", (dur, rows))
h2 = Sahte(); h2.ru_bozuk = True; s, dur, rows = kos(h2)
k("FAIL RU geri okuma farki (RU ne yeni ne eski): yalniz EN geri yazildi (plan 3.9), RU'ya ek yazim yok, ELLE BAKILMALI, DUR",
  dur and Y.norm(h2.L["description"]) == Y.norm(D["description"]) and [w[0] for w in h2.yaz] == ["PATCH", "PUT", "PATCH"]
  and rows[0]["sonuc"] == "FAIL" and "ELLE BAKILMALI" in rows[0]["neden"] and rows[0]["geri_utc"] and rows[0]["last_modified_timestamp"], (dur, rows))
h3 = Sahte(); h3.put_islenip_hata = True; s, dur, rows = kos(h3)
k("FAIL PUT islendi + 5xx: canli RU yeni -> EN'ye dokunulmaz (EN + RU yeni), TAMAM_HATALI, DUR",
  dur and Y.norm(h3.L["description"]) == Y.norm(KURU[LID]["en_sonra"]) and Y.norm(h3.ru["description"]) == Y.norm(KURU[LID]["ru_sonra"])
  and [w[0] for w in h3.yaz] == ["PATCH", "PUT"] and rows[0]["sonuc"] == "TAMAM_HATALI" and rows[0]["last_modified_timestamp"] == "2", (dur, rows))
t = Sahte(); t.patch_timeout = True; s, dur, rows = kos(t)
k("FAIL ag hatasi (Timeout) PATCH sirasinda: DUR, DEGISIKLIK satirinda ilan + en_utc + ELLE BAKILMALI", dur and len(rows) == 1
  and rows[0]["listing_id"] == LID and rows[0]["en_utc"] and "ELLE BAKILMALI" in rows[0]["neden"] and not [w for w in t.yaz if w[0] == "PUT"], (dur, rows))
t2 = Sahte(); t2.patch_islenip_hata = True; s, dur, rows = kos(t2)
k("FAIL PATCH islendi + 5xx: DUR, RU yazilmadi, kayitta ilan + 'EN yazilmis olabilir'", dur and rows[0]["listing_id"] == LID
  and "EN yazilmis olabilir" in rows[0]["neden"] and not [w for w in t2.yaz if w[0] == "PUT"], (dur, rows))
yr = Sahte(); kos(yr); yr.ru["description"] = D["ru"]["description"]; s, dur, _ = kos(yr)
k("FAIL yarim durum (EN yeni, RU eski): YARIM DUR, yazim yok", dur and "YARIM" in dur, dur)
bt = Sahte(); bt.ru["tags"] = []; s, dur, _ = kos(bt, yedek={LID: dict(YEDEK[LID], ru=dict(YEDEK[LID]["ru"], tags=[]))})
k("FAIL RU etiket bos: DUR (PUT etiketleri silebilir), yazim yok", dur and "bos" in dur and not bt.yaz, dur)
# 9 EN geri okuma farki
i = Sahte(); i.patch_bozuk = True; s, dur, _ = kos(i)
k("FAIL EN geri okuma farki: DUR, RU yazilmadi", dur and "EN geri okuma" in dur and [w[0] for w in i.yaz] == ["PATCH"], dur)
# 10 kota
j = Sahte(kalan=Y.ISTEK_ILAN + E.KOTA_SINIRI - 1); s, dur, _ = kos(j)
k("FAIL kota < 20 + 10: ilan baslamaz (istek yok)", dur and "kota" in dur and j.calls == 0, (dur, j.calls))
j2 = Sahte(kalan=Y.ISTEK_ILAN + E.KOTA_SINIRI); s, dur, _ = kos(j2)
k("PASS kota = 20 + 10: ilan yazilir", dur is None and s[0]["sonuc"] == "PASS", dur)
j3 = Sahte(kalan=None); s, dur, _ = kos(j3)
k("FAIL kalan kota okunamiyor (None): ilk okumadan sonra DUR, yazim yok", dur and "x-remaining-today" in dur and not j3.yaz, dur)
# 11 geri al
m = Sahte(); kos(m); s, dur, _ = kos(m, geri=True)
k("geri-al: EN once + RU ru_geri yazildi (GERI_ALINDI)", dur is None and s[0]["sonuc"] == "GERI_ALINDI"
  and Y.norm(m.L["description"]) == Y.norm(KURU[LID]["en_once"]) and Y.norm(m.ru["description"]) == Y.norm(KURU[LID]["ru_geri"]), dur)
k("geri-al: ru_geri = canli eski RU", Y.norm(KURU[LID]["ru_geri"]) == Y.norm(D["ru"]["description"]))
s, dur, _ = kos(m, geri=True)
k("geri-al ikinci kez: ZATEN_ESKI, yazim yok", dur is None and s[0]["sonuc"] == "ZATEN_ESKI")
o = Sahte(); s, dur, _ = kos(o, geri=True)
k("geri-al canli zaten eski: ZATEN_ESKI (yazim yok)", dur is None and s[0]["sonuc"] == "ZATEN_ESKI" and not o.yaz)
# 12 RU kapisi gercek: izin verilmeyen RU metni -> yazim yok
E.RU_POSTER_IZIN.clear()
try:
    E.ru_yazim_kapisi("PUT", f"/shops/1/listings/{LID}/translations/ru", data={"title": "x", "description": "baska metin", "tags": ""}); kapi = False
except SystemExit:
    kapi = True
k("RU kapisi: izinsiz poster RU metni DUR (gercek kapi)", kapi)
# 13 GERCEK Etsy._call yolu (sahte requests): html_coz, ru_yazim_kapisi, ai_beyan, metin kapisi, KOTA_SINIRI tabani
import requests  # noqa: E402


class Yanit:
    def __init__(self, kod, govde, kalan):
        self.status_code, self._g, self.headers, self.text = kod, govde, {"x-remaining-today": str(kalan)}, json.dumps(govde)

    def json(self):
        return self._g


def gercek_api(sahte):
    def istek(method, url, params=None, data=None, json=None, headers=None, timeout=None):
        path = url.split("/v3/application", 1)[1]
        try:
            if method == "GET":
                g = sahte.get(path)
            elif method == "PATCH":
                sahte.patch(path, data); g = {}
            elif method == "PUT":
                sahte.put(path, data); g = {}
            else:
                raise AssertionError(method)
        except SystemExit:
            return Yanit(503, {}, sahte.remaining)
        return Yanit(200, g, sahte.remaining)
    requests.request = istek
    api = E.Etsy.__new__(E.Etsy)
    E.Etsy.__init__(api, type("S", (), {"access_token": "x", "api_key_header": "k", "needs_refresh": lambda self: False})())
    api._headers = lambda tok=None: {}
    api.pace = 0
    api._erken_yenile = lambda: None
    return api


gercek_req = requests.request
try:
    g1 = Sahte(); api = gercek_api(g1); E.METIN_UYARI.clear(); E.RU_POSTER_IZIN.clear()
    s, dur, rows = kos(api)
    k("gercek _call: normal akis PASS (gercek kapilar), metin kapisi uyari 0", dur is None and s[0]["sonuc"] == "PASS"
      and Y.norm(g1.ru["description"]) == Y.norm(KURU[LID]["ru_sonra"]) and not E.METIN_UYARI, (dur, E.METIN_UYARI[:2]))
    k("gercek _call: gonderilen EN HTML varliksiz (&#39; yok)", "&#39;" not in g1.yaz[0][2]["description"] and "'" in g1.yaz[0][2]["description"])
    g2 = Sahte(); api = gercek_api(g2); E.RU_POSTER_IZIN.clear()
    kb2 = copy.deepcopy(KURU); kb2[LID]["ru_sonra"] = kb2[LID]["ru_sonra"] + "\nEK SATIR"
    s, dur, _ = kos(api, kuru=kb2)
    k("gercek _call FAIL: kuru RU degistirilmis -> yazim yok (bayat/onay)", dur and not g2.yaz, dur)
finally:
    requests.request = gercek_req
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
